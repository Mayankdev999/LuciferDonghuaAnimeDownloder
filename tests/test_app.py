import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app import (
    app,
    extract_dailymotion_fallback,
    extract_video_links,
    search_donghua,
    get_series_details,
    parse_weekly_schedule,
    get_weekly_schedule,
    _SCHEDULE_CACHE,
)

client = TestClient(app)


class TestTheAnimeLinkExtractor(unittest.TestCase):

    def test_static_index_serving(self):
        """Verify root / serves HTML application."""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("TheAnimeLink", response.text)
        self.assertIn("Universal Donghua Hub", response.text)

    def test_static_assets_serving(self):
        """Verify static CSS and JS are served properly."""
        css_res = client.get("/static/style.css")
        self.assertEqual(css_res.status_code, 200)
        self.assertIn("--bg-base", css_res.text)

        js_res = client.get("/static/script.js")
        self.assertEqual(js_res.status_code, 200)
        self.assertIn("theanimelink_bookmarks", js_res.text)

    def test_extract_dailymotion_fallback_regex(self):
        """Verify regex extraction of quoted Dailymotion URLs, bad link filtering, and prioritization."""
        sample_html = r"""
        <script>
            var player1 = "https://www.dailymotion.com/embed/video/x80xyz";
            var badScript = "https://geo.dailymotion.com/player/xbj0x.js";
            var badCrawler = "https://www.dailymotion.com/crawler/video/xb43b0y";
            var topPriority = "https://geo.dailymotion.com/player/xbj0x.html?video=k60cyxZWPfcWNSJtE4i";
            var duplicate = "https://www.dailymotion.com/embed/video/x80xyz";
        </script>
        """
        extracted = extract_dailymotion_fallback(sample_html)
        # Should filter out .js and crawler, leaving topPriority and player1
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0], "https://geo.dailymotion.com/player/xbj0x.html?video=k60cyxZWPfcWNSJtE4i")
        self.assertEqual(extracted[1], "https://www.dailymotion.com/embed/video/x80xyz")

    def test_invalid_url_format(self):
        """Verify error response on invalid URL."""
        res = client.post("/api/extract", json={"url": "not-a-valid-url"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid URL format", data["error"])

    @patch("app.requests.get")
    def test_stage1_pembed_div_iframe(self, mock_get):
        """Verify Stage 1 extraction from #pembed div iframe."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div id="pembed">
                    <div>
                        <iframe src="https://www.dailymotion.com/embed/video/k5678" width="100%" height="100%"></iframe>
                    </div>
                </div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.post("/api/extract", json={"url": "https://anime-site.com/watch/ep-1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["source"], "iframe_selector")
        self.assertEqual(data["links"], ["https://www.dailymotion.com/embed/video/k5678"])

    @patch("app.requests.get")
    def test_stage1_pembed_iframe_relative_url(self, mock_get):
        """Verify Stage 1 extraction with relative iframe src resolved to absolute URL."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div id="pembed">
                    <iframe src="/player/stream?id=999"></iframe>
                </div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.post("/api/extract", json={"url": "https://anime-site.com/watch/ep-2"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["source"], "iframe_selector")
        self.assertEqual(data["links"], ["https://anime-site.com/player/stream?id=999"])

    @patch("app.requests.get")
    def test_stage2_dailymotion_fallback(self, mock_get):
        """Verify Stage 2 extraction when #pembed is missing but HTML contains Dailymotion link."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <script>
                    const videoSrc = "https://www.dailymotion.com/embed/video/x998877";
                </script>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.post("/api/extract", json={"url": "https://anime-site.com/watch/ep-3"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["source"], "dailymotion_fallback")
        self.assertEqual(data["links"], ["https://www.dailymotion.com/embed/video/x998877"])

    @patch("app.requests.get")
    def test_no_links_found(self, mock_get):
        """Verify graceful error when neither iframe nor Dailymotion link is present."""
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>No videos here</h1></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.post("/api/extract", json={"url": "https://anime-site.com/empty"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No embedded iframe (#pembed) or Dailymotion video source links", data["error"])
        self.assertEqual(data["links"], [])

    @patch("app.requests.get")
    def test_search_donghua_endpoint(self, mock_get):
        """Verify /api/search dynamically parses search cards."""
        mock_response = MagicMock()
        mock_response.text = """
        <div class="listupd">
            <article class="bs">
                <div class="bsx">
                    <a href="https://luciferdonghua.in/anime/perfect-world-new/" class="tip" title="Perfect World">
                        <div class="limit">
                            <div class="status">Ongoing</div>
                            <div class="typez">ONA</div>
                            <img src="https://example.com/poster.webp" />
                        </div>
                        <div class="tt">
                            <h2>Perfect World [Wanmei Shijie]</h2>
                        </div>
                    </a>
                </div>
            </article>
        </div>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.get("/api/search?q=perfect+world")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["title"], "Perfect World [Wanmei Shijie]")
        self.assertEqual(data["results"][0]["url"], "https://luciferdonghua.in/anime/perfect-world-new/")
        self.assertEqual(data["results"][0]["status"], "Ongoing")
        self.assertEqual(data["results"][0]["type"], "ONA")

    @patch("app.requests.get")
    def test_series_details_endpoint(self, mock_get):
        """Verify /api/series dynamically parses series metadata and episodes."""
        mock_response = MagicMock()
        mock_response.text = """
        <h1 class="entry-title">Renegade Immortal</h1>
        <div class="thumb"><img src="https://example.com/ri.webp" /></div>
        <div class="desc"><p>A story about Wang Lin...</p></div>
        <div class="spe">
            <span><b>Status:</b> Ongoing</span>
            <span><b>Studio:</b> Foch Film</span>
        </div>
        <div class="genxed">
            <a href="/genres/action/">Action</a>
            <a href="/genres/fantasy/">Fantasy</a>
        </div>
        <div class="eplister">
            <ul>
                <li>
                    <a href="/renegade-immortal-episode-52/">
                        <div class="epl-num">52 [4K]</div>
                        <div class="epl-title">Renegade Immortal Episode 52 English Sub</div>
                        <div class="epl-date">September 1, 2026</div>
                    </a>
                </li>
                <li>
                    <a href="/renegade-immortal-episode-01/">
                        <div class="epl-num">01</div>
                        <div class="epl-title">Renegade Immortal Episode 01 English Sub</div>
                        <div class="epl-date">September 1, 2023</div>
                    </a>
                </li>
            </ul>
        </div>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        response = client.get("/api/series?url=https://luciferdonghua.in/anime/renegade-immortal/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["title"], "Renegade Immortal")
        self.assertEqual(data["status"], "Ongoing")
        self.assertEqual(data["studio"], "Foch Film")
        self.assertIn("Action", data["genres"])
        self.assertEqual(data["episodes_count"], 2)
        self.assertEqual(data["episodes"][0]["num"], "52")
        self.assertEqual(data["episodes"][0]["raw_num"], "52 [4K]")
        self.assertEqual(data["episodes"][0]["url"], "https://luciferdonghua.in/renegade-immortal-episode-52/")
        self.assertEqual(data["episodes"][1]["num"], "01")

    def test_parse_weekly_schedule(self):
        """Verify parsing of the weekly release schedule from HTML."""
        sample_html = """
        <div class="bixbox lucifer-sched-box" id="lucifer-schedule">
            <div class="releases lucifer-sched-title"><h3><span>Weekly Schedule</span></h3></div>
            <div class="lucifer-sched">
                <div class="lucifer-day-tabs">
                    <div class="lucifer-day-tab" data-day="mon"><div class="d">Mon</div><div class="n">5 ep</div></div>
                    <div class="lucifer-day-tab" data-day="thu"><div class="d">Today</div><div class="n">6 ep</div></div>
                    <div class="lucifer-day-tab" data-day="sat"><div class="d">Sat</div><div class="n">9 ep</div></div>
                </div>
                <div class="lucifer-swrap">
                    <div class="lucifer-day-list" data-day="mon">
                        <a class="lucifer-sched-item" href="/anime/the-eternal-supreme-li-yunxiao/">
                            <img src="/wp-content/uploads/poster1.webp" alt="">
                            <span class="si-body">
                                <span class="si-t">The Eternal Supreme (2026)</span>
                                <span class="si-s">Episode 20 expected</span>
                            </span>
                            <span class="lucifer-badge out">Monday</span>
                        </a>
                    </div>
                    <div class="lucifer-day-list" data-day="thu">
                        <a class="lucifer-sched-item" href="/anime/jade-dynasty-final-season-4/">
                            <img src="/wp-content/uploads/poster2.webp" alt="">
                            <span class="si-body">
                                <span class="si-t">Jade Dynasty Season 4</span>
                                <span class="si-s">Episode 7 expected</span>
                            </span>
                            <span class="lucifer-badge today">Airing today</span>
                        </a>
                    </div>
                </div>
            </div>
        </div>
        """
        data = parse_weekly_schedule(sample_html, base_url="https://luciferdonghua.in/")
        self.assertTrue(data["success"])
        self.assertEqual(data["today"], "thu")
        self.assertEqual(len(data["days"]), 3)

        # Mon checks
        mon = next(d for d in data["days"] if d["key"] == "mon")
        self.assertEqual(mon["label"], "Mon")
        self.assertEqual(mon["count"], "5 ep")
        self.assertFalse(mon["is_today"])
        self.assertEqual(len(mon["items"]), 1)
        self.assertEqual(mon["items"][0]["title"], "The Eternal Supreme (2026)")
        self.assertEqual(mon["items"][0]["url"], "https://luciferdonghua.in/anime/the-eternal-supreme-li-yunxiao/")
        self.assertEqual(mon["items"][0]["poster"], "https://luciferdonghua.in/wp-content/uploads/poster1.webp")
        self.assertEqual(mon["items"][0]["expected"], "Episode 20 expected")
        self.assertFalse(mon["items"][0]["is_airing_today"])

        # Thu checks (Today)
        thu = next(d for d in data["days"] if d["key"] == "thu")
        self.assertEqual(thu["label"], "Today")
        self.assertTrue(thu["is_today"])
        self.assertEqual(len(thu["items"]), 1)
        self.assertEqual(thu["items"][0]["title"], "Jade Dynasty Season 4")
        self.assertTrue(thu["items"][0]["is_airing_today"])

    @patch("app.fetch_html")
    def test_schedule_api_endpoint(self, mock_fetch):
        """Verify GET /api/schedule returns proper JSON."""
        mock_fetch.return_value = ("""
        <div id="lucifer-schedule">
            <div class="lucifer-day-tabs">
                <div class="lucifer-day-tab" data-day="wed"><div class="d">Today</div><div class="n">2 ep</div></div>
            </div>
            <div class="lucifer-day-list" data-day="wed">
                <a class="lucifer-sched-item" href="https://luciferdonghua.in/anime/spirit-realm-walker/">
                    <img src="https://luciferdonghua.in/poster.webp" alt="">
                    <span class="si-body">
                        <span class="si-t">Spirit Realm Walker</span>
                        <span class="si-s">Episode 5 expected</span>
                    </span>
                    <span class="lucifer-badge today">Airing today</span>
                </a>
            </div>
        </div>
        """, None)

        res = client.get("/api/schedule?refresh=true")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["today"], "wed")
        self.assertEqual(len(data["days"]), 1)
        self.assertEqual(data["days"][0]["items"][0]["title"], "Spirit Realm Walker")

    @patch("app.fetch_html")
    def test_schedule_cache_mechanism(self, mock_fetch):
        """Verify in-memory caching prevents duplicate fetches within TTL."""
        mock_fetch.return_value = ("""
        <div id="lucifer-schedule">
            <div class="lucifer-day-tabs">
                <div class="lucifer-day-tab" data-day="fri"><div class="d">Fri</div><div class="n">1 ep</div></div>
            </div>
            <div class="lucifer-day-list" data-day="fri">
                <a class="lucifer-sched-item" href="/anime/test/">
                    <span class="si-body"><span class="si-t">Test Anime</span></span>
                </a>
            </div>
        </div>
        """, None)

        # Force refresh first
        res1 = client.get("/api/schedule?refresh=true")
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(mock_fetch.call_count, 1)

        # Second call without refresh=true should hit memory cache
        res2 = client.get("/api/schedule")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json().get("cached"))
        # mock_fetch should NOT be called again
        self.assertEqual(mock_fetch.call_count, 1)

    def test_sync_push_and_pull(self):
        """Verify cloud sync push and pull workflow."""
        sync_key = "test-user-sync-1"
        payload = {
            "key": sync_key,
            "bookmarks": [
                {
                    "title": "Battle Through The Heavens",
                    "url": "https://luciferdonghua.in/anime/btth/",
                    "poster": "https://luciferdonghua.in/btth.jpg",
                }
            ],
            "progress": {
                "https://luciferdonghua.in/anime/btth/": {
                    "downloaded_eps": ["1", "2"],
                    "last_ep_num": "2",
                    "last_downloaded_at": 1000,
                }
            },
        }

        # 1. Push data
        push_res = client.post("/api/sync/push", json=payload)
        self.assertEqual(push_res.status_code, 200)
        push_data = push_res.json()
        self.assertTrue(push_data["success"])
        self.assertEqual(push_data["bookmarks_count"], 1)

        # 2. Pull data
        pull_res = client.get(f"/api/sync/pull?key={sync_key}")
        self.assertEqual(pull_res.status_code, 200)
        pull_data = pull_res.json()
        self.assertTrue(pull_data["success"])
        self.assertTrue(pull_data["found"])
        self.assertEqual(len(pull_data["data"]["bookmarks"]), 1)
        self.assertEqual(pull_data["data"]["bookmarks"][0]["title"], "Battle Through The Heavens")
        self.assertIn("1", pull_data["data"]["progress"]["https://luciferdonghua.in/anime/btth/"]["downloaded_eps"])

    def test_sync_merge_logic(self):
        """Verify non-destructive merging across multiple devices."""
        sync_key = "test-merge-devices"

        # Device 1 (Mobile) pushes Anime A & Ep 1, 2
        mobile_payload = {
            "key": sync_key,
            "bookmarks": [{"title": "Anime A", "url": "https://luciferdonghua.in/anime/a/"}],
            "progress": {
                "https://luciferdonghua.in/anime/a/": {
                    "downloaded_eps": ["1", "2"],
                    "last_ep_num": "2",
                    "last_downloaded_at": 1000,
                }
            },
        }
        res1 = client.post("/api/sync/push", json=mobile_payload)
        self.assertEqual(res1.status_code, 200)

        # Device 2 (Laptop) pushes Anime B & Ep 3 for Anime A
        laptop_payload = {
            "key": sync_key,
            "bookmarks": [{"title": "Anime B", "url": "https://luciferdonghua.in/anime/b/"}],
            "progress": {
                "https://luciferdonghua.in/anime/a/": {
                    "downloaded_eps": ["3"],
                    "last_ep_num": "3",
                    "last_downloaded_at": 2000,
                }
            },
        }
        res2 = client.post("/api/sync/push", json=laptop_payload)
        self.assertEqual(res2.status_code, 200)

        # Pull merged vault
        pull_res = client.get(f"/api/sync/pull?key={sync_key}")
        vault = pull_res.json()["data"]

        # Both bookmarks must exist!
        bm_titles = [b["title"] for b in vault["bookmarks"]]
        self.assertIn("Anime A", bm_titles)
        self.assertIn("Anime B", bm_titles)

        # Downloaded episodes for Anime A must be union of 1, 2, 3!
        downloaded = vault["progress"]["https://luciferdonghua.in/anime/a/"]["downloaded_eps"]
        self.assertIn("1", downloaded)
        self.assertIn("2", downloaded)
        self.assertIn("3", downloaded)
        self.assertEqual(vault["progress"]["https://luciferdonghua.in/anime/a/"]["last_ep_num"], "3")

    def test_sync_invalid_key(self):
        """Verify validation errors on invalid sync keys."""
        # Empty/single-char key pull
        res1 = client.get("/api/sync/pull?key=x")
        self.assertFalse(res1.json()["success"])

        # Push with 1-char key
        res2 = client.post("/api/sync/push", json={"key": "x", "bookmarks": [], "progress": {}})
        self.assertEqual(res2.status_code, 422)  # Pydantic validation min_length=2


if __name__ == "__main__":
    unittest.main()
