import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app import app, extract_dailymotion_fallback, extract_video_links, search_donghua, get_series_details

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


if __name__ == "__main__":
    unittest.main()
