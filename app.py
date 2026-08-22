import os
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="TheAnimeLink Extractor",
    description="Extract embedded iframe and Dailymotion video source links using browser impersonation.",
    version="1.0.0",
)

# Enable CORS for local testing/development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    url: str = Field(..., description="Target webpage URL to extract video sources from")


class ExtractResponse(BaseModel):
    success: bool
    links: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    error: Optional[str] = None


def extract_dailymotion_fallback(html: str) -> List[str]:
    """Finds and cleans all quoted strings containing 'dailymotion.com'."""
    pattern = r'"([^"]*dailymotion\.com[^"]*)"'
    raw_matches = re.findall(pattern, html)

    cleaned_links: List[str] = []
    for match in raw_matches:
        # Clean escaped characters like \/ or leading/trailing whitespace
        clean_url = match.replace(r"\/", "/").strip()
        if clean_url.startswith("//"):
            clean_url = f"https:{clean_url}"
        if clean_url:
            cleaned_links.append(clean_url)

    # Return unique results preserving order
    return list(dict.fromkeys(cleaned_links))


def extract_video_links(target_url: str) -> dict:
    """Core extraction pipeline using curl_cffi with chrome124 TLS impersonation."""
    target_url = target_url.strip()
    parsed = urlparse(target_url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        return {
            "success": False,
            "error": "Invalid URL format. Please provide a valid HTTP/HTTPS URL.",
            "links": [],
            "source": None,
        }

    try:
        response = requests.get(
            target_url,
            impersonate="chrome124",
            timeout=15,
            headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        response.raise_for_status()
    except requests.errors.Timeout:
        return {
            "success": False,
            "error": "Request timed out while connecting to the target webpage (15s timeout).",
            "links": [],
            "source": None,
        }
    except requests.errors.RequestsError as e:
        return {
            "success": False,
            "error": f"Network / connection error: {str(e)}",
            "links": [],
            "source": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch webpage: {str(e)}",
            "links": [],
            "source": None,
        }

    raw_html = response.text
    if not raw_html:
        return {
            "success": False,
            "error": "Received empty response from the target webpage.",
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
        # Resolve any relative paths if needed
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


# Mount static directory for frontend assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    """Serve the single-page frontend application."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "TheAnimeLink Extractor API is running. Frontend index.html not found."}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=False)
