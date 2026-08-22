import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure root directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app import app, extract_dailymotion_fallback, extract_video_links

client = TestClient(app)


class TestTheAnimeLinkExtractor(unittest.TestCase):

    def test_static_index_serving(self):
        """Verify root / serves HTML application."""
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("TheAnimeLink", response.text)
        self.assertIn("Extract Embedded Video Sources", response.text)

    def test_static_assets_serving(self):
        """Verify static CSS and JS are served properly."""
        css_res = client.get("/static/style.css")
        self.assertEqual(css_res.status_code, 200)
        self.assertIn("--bg-base", css_res.text)

        js_res = client.get("/static/script.js")
        self.assertEqual(js_res.status_code, 200)
        self.assertIn("extract-form", js_res.text)

    def test_extract_dailymotion_fallback_regex(self):
        """Verify regex extraction of quoted Dailymotion URLs and deduplication."""
        sample_html = r"""
        <script>
            var player1 = "https://www.dailymotion.com/embed/video/x80xyz";
            var player2 = "https:\/\/www.dailymotion.com\/embed\/video\/x90abc";
            var player3 = "//geo.dailymotion.com/player/x123.html";
            var duplicate = "https://www.dailymotion.com/embed/video/x80xyz";
        </script>
        """
        extracted = extract_dailymotion_fallback(sample_html)
        self.assertEqual(len(extracted), 3)
        self.assertEqual(extracted[0], "https://www.dailymotion.com/embed/video/x80xyz")
        self.assertEqual(extracted[1], "https://www.dailymotion.com/embed/video/x90abc")
        self.assertEqual(extracted[2], "https://geo.dailymotion.com/player/x123.html")

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


if __name__ == "__main__":
    unittest.main()
