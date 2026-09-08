import os
import re
from typing import List, Optional
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="TheAnimeLink Universal Hub",
    description="Universal Donghua streaming & episode extractor with Chrome 124 JA3 impersonation.",
    version="2.0.0",
)

# Enable CORS for local testing/development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BROWSER_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_html(url: str, timeout: int = 15) -> tuple[Optional[str], Optional[str]]:
    """Fetches raw HTML using curl_cffi with Chrome 124 TLS/JA3 impersonation."""
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return None, "Invalid URL format. Please provide a valid HTTP/HTTPS URL."

    try:
        response = requests.get(
            url,
            impersonate="chrome124",
            timeout=timeout,
            headers=BROWSER_HEADERS,
        )
        response.raise_for_status()
        return response.text, None
    except requests.errors.Timeout:
        return None, "Request timed out while connecting to the target webpage (15s timeout)."
    except requests.errors.RequestsError as e:
        return None, f"Network/connection error: {str(e)}"
    except Exception as e:
        return None, f"Failed to fetch webpage: {str(e)}"


# -------------------------------------------------------------
# 1. VIDEO STREAM EXTRACTION LOGIC
# -------------------------------------------------------------

class ExtractRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL to extract video sources from")


class ExtractResponse(BaseModel):
    success: bool
    links: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    error: Optional[str] = None


def clean_episode_number(raw_num: str) -> str:
    """Cleans up cluttered episode labels by removing [4K], [HD], etc."""
    if not raw_num:
        return ""
    # Remove quality / tag brackets like [4K], [HD], [UHD], [FHD], [1080p], [END], [Sub]
    cleaned = re.sub(
        r'\[\s*(?:4k|8k|2k|hd|fhd|uhd|1080p?|720p?|480p?|sub|dub|raw|end)\s*\]',
        '',
        raw_num,
        flags=re.IGNORECASE,
    )
    # Remove redundant "Episode" or "Eps" prefixes if already present
    cleaned = re.sub(r'^(?:episode|eps?\.?)\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or raw_num.strip()


def extract_dailymotion_fallback(html: str) -> List[str]:
    """Finds, filters, and ranks Dailymotion player links (excluding scripts and crawlers)."""
    pattern = r'"([^"]*dailymotion\.com[^"]*)"'
    raw_matches = re.findall(pattern, html)

    cleaned_links: List[str] = []
    for match in raw_matches:
        clean_url = match.replace(r"\/", "/").strip()
        if clean_url.startswith("//"):
            clean_url = f"https:{clean_url}"

        # Discard non-HTTP, static asset files, and crawler links
        if not clean_url.startswith("http"):
            continue
        if re.search(r'\.(?:js|css|json|png|jpg|jpeg|svg|webp)(?:\?|$)', clean_url, re.I):
            continue
        if "/crawler/" in clean_url:
            continue

        cleaned_links.append(clean_url)

    # Rank the links so genuine players with video= or /embed/video/ come first
    def link_priority(url: str) -> int:
        # Priority 0: Geo player with video parameter (exact stream player)
        if re.search(r'[?&]video=', url, re.I):
            return 0
        # Priority 1: Standard /embed/video/
        if "/embed/video/" in url:
            return 1
        # Priority 2: Other HTML player embeds
        if re.search(r'/player/.*\.html', url, re.I):
            return 2
        # Priority 3: Other valid links
        return 3

    # Deduplicate while preserving order of highest priority
    unique_candidates = list(dict.fromkeys(cleaned_links))
    ranked_links = sorted(unique_candidates, key=link_priority)
    return ranked_links


def extract_video_links(target_url: str) -> dict:
    """Extracts embedded iframe or Dailymotion fallback links from episode page."""
    raw_html, error = fetch_html(target_url)
    if error or not raw_html:
        return {
            "success": False,
            "error": error or "Received empty response from the target webpage.",
            "links": [],
            "source": None,
        }

    soup = BeautifulSoup(raw_html, "html.parser")

    # Stage 1: DOM Selector (#pembed div iframe or #pembed iframe)
    iframe = soup.select_one("#pembed div iframe") or soup.select_one("#pembed iframe")
    if iframe and iframe.get("src"):
        src_link = iframe["src"].strip()
        if src_link:
            resolved_url = urljoin(target_url, src_link)
            return {
                "success": True,
                "links": [resolved_url],
                "source": "iframe_selector",
                "error": None,
            }

    # Stage 2: Fallback Regex Search for Dailymotion links
    dm_links = extract_dailymotion_fallback(raw_html)
    if dm_links:
        resolved_dm_links = [urljoin(target_url, link) for link in dm_links]
        return {
            "success": True,
            "links": resolved_dm_links,
            "source": "dailymotion_fallback",
            "error": None,
        }

    # Stage 3: No links found
    return {
        "success": False,
        "error": "No embedded iframe (#pembed) or Dailymotion video source links were found on the page.",
        "links": [],
        "source": None,
    }


@app.post("/api/extract", response_model=ExtractResponse)
def extract_endpoint(payload: ExtractRequest):
    """API endpoint to extract video links from a target URL."""
    result = extract_video_links(payload.url)
    return ExtractResponse(**result)


# -------------------------------------------------------------
# 2. SEARCH ENDPOINT (Universal Donghua Search)
# -------------------------------------------------------------

def search_donghua(query: str) -> dict:
    """Searches luciferdonghua.in for any query and extracts results."""
    query = query.strip()
    if not query:
        return {"success": False, "error": "Search query cannot be empty.", "results": []}

    search_url = f"https://luciferdonghua.in/?s={quote(query)}"
    raw_html, error = fetch_html(search_url)
    if error or not raw_html:
        return {"success": False, "error": error or "Failed to search.", "results": []}

    soup = BeautifulSoup(raw_html, "html.parser")
    results = []
    seen_urls = set()

    for article in soup.select(".listupd article.bs, .listupd .bsx"):
        a_tag = article.select_one("a.tip") or article.select_one("a")
        if not a_tag:
            continue
        href = a_tag.get("href", "").strip()
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        # Title extraction (prefer .tt h2 to avoid duplicate text in .tt)
        h2 = article.select_one(".tt h2")
        title_el = h2 or article.select_one(".tt")
        if h2:
            title_text = h2.get_text(strip=True)
        elif title_el:
            title_text = title_el.get_text(strip=True)
        else:
            title_text = a_tag.get("title", "").strip()

        # Poster image
        img = article.select_one(".limit img") or article.select_one("img")
        poster = ""
        if img:
            poster = img.get("src") or img.get("data-src") or ""

        # Status badge (e.g. Ongoing, Completed)
        epx = article.select_one(".bt .epx") or article.select_one(".status")
        status_text = epx.get_text(strip=True) if epx else ""

        # Type badge (e.g. ONA, Special, DONGHUA)
        typez = article.select_one(".typez")
        type_text = typez.get_text(strip=True) if typez else ""

        if href and title_text:
            results.append({
                "title": title_text,
                "url": href,
                "poster": poster,
                "status": status_text,
                "type": type_text,
            })

    return {
        "success": True,
        "query": query,
        "results_count": len(results),
        "results": results,
    }


@app.get("/api/search")
def search_endpoint(q: str = Query(..., description="Anime name to search")):
    """Search for anime on luciferdonghua.in."""
    return search_donghua(q)


# -------------------------------------------------------------
# 3. SERIES & EPISODES ENDPOINT (Dynamic Episode Count)
# -------------------------------------------------------------

def get_series_details(series_url: str) -> dict:
    """Fetches series details and all available episodes dynamically."""
    series_url = series_url.strip()
    raw_html, error = fetch_html(series_url)
    if error or not raw_html:
        return {"success": False, "error": error or "Failed to load series page.", "episodes": []}

    soup = BeautifulSoup(raw_html, "html.parser")

    # Title
    title_el = soup.select_one("h1.entry-title") or soup.select_one(".entry-title")
    title = title_el.get_text(strip=True) if title_el else "Unknown Title"

    # Poster
    poster_el = (
        soup.select_one(".thumb img")
        or soup.select_one(".thumbook img")
        or soup.select_one(".bigcover img")
    )
    poster = ""
    if poster_el:
        poster = poster_el.get("src") or poster_el.get("data-src") or ""

    # Synopsis
    desc_el = soup.select_one(".entry-content") or soup.select_one(".desc") or soup.select_one(".mindesc")
    synopsis = desc_el.get_text(strip=True) if desc_el else ""

    # Genres
    genres = [a.get_text(strip=True) for a in soup.select(".genxed a")]

    # Status & Studio from .spe span
    status_text = ""
    studio_text = ""
    for span in soup.select(".spe span"):
        text = span.get_text(" ", strip=True)
        if "Status:" in text:
            status_text = text.split("Status:", 1)[1].strip()
        elif "Studio:" in text:
            studio_text = text.split("Studio:", 1)[1].strip()

    # Episodes list from .eplister
    episodes = []
    seen_eps = set()
    for li in soup.select(".eplister ul li"):
        a = li.select_one("a")
        if not a or not a.get("href"):
            continue
        ep_url = urljoin(series_url, a["href"].strip())
        if ep_url in seen_eps:
            continue
        seen_eps.add(ep_url)

        num_el = li.select_one(".epl-num")
        title_el = li.select_one(".epl-title")
        date_el = li.select_one(".epl-date")

        raw_num = num_el.get_text(strip=True) if num_el else ""
        num = clean_episode_number(raw_num)
        ep_title = title_el.get_text(strip=True) if title_el else ""
        date = date_el.get_text(strip=True) if date_el else ""

        episodes.append({
            "num": num,
            "raw_num": raw_num,
            "title": ep_title,
            "url": ep_url,
            "date": date,
        })

    return {
        "success": True,
        "title": title,
        "url": series_url,
        "poster": poster,
        "status": status_text,
        "studio": studio_text,
        "genres": genres,
        "synopsis": synopsis,
        "episodes_count": len(episodes),
        "episodes": episodes,
    }


@app.get("/api/series")
def series_endpoint(url: str = Query(..., description="Series page URL to extract episodes from")):
    """Get anime series details and complete episode list."""
    return get_series_details(url)


# -------------------------------------------------------------
# 4. STATIC FILE SERVING
# -------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    """Serve the single-page frontend application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TheAnimeLink API is running. Frontend index.html not found."}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=False)
