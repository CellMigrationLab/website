"""Tests for scripts/write_sitemap.py.

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import tempfile
import unittest
from pathlib import Path

from write_sitemap import page_paths, robots, sitemap


class SitemapTests(unittest.TestCase):
    def test_lists_pages_but_not_redirects_or_the_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            pages = {
                "index.html": "<!doctype html><title>Home</title>",
                "portfolio/cdm/index.html": "<!doctype html><title>CDM</title>",
                "news/index.html": '<!doctype html><meta http-equiv="refresh" content="0; url=../">',
                "feed/index.html": '<?xml version="1.0"?><rss></rss>',
                "404.html": "<!doctype html>",
            }
            for rel, text in pages.items():
                (site / rel).parent.mkdir(parents=True, exist_ok=True)
                (site / rel).write_text(text)
            self.assertEqual(page_paths(site), ["", "portfolio/cdm/"])

    def test_sitemap_and_robots_use_the_base_url(self):
        xml = sitemap("https://cellmig.org/", ["", "a&b/"])
        self.assertIn("<loc>https://cellmig.org/</loc>", xml)
        self.assertIn("<loc>https://cellmig.org/a&amp;b/</loc>", xml)
        self.assertIn("Sitemap: https://cellmig.org/sitemap.xml", robots("https://cellmig.org/"))


if __name__ == "__main__":
    unittest.main()
