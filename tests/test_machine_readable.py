"""Tests for link previews, structured data and llms.txt.

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import json
import unittest
from unittest.mock import patch

from cellmig import previews
from cellmig.structured import article, scholar_tags, to_json

STORY = {"pubs": [{"doi": "10.1/x", "title": "A </script> title", "authors": ["Ana B", "Guillaume Jacquemet"],
                   "venue": "J Cell Sci", "year": 2025}],
         "date": None, "year": 2025, "summary": "Line one.\n\nLine two.", "title": "A title", "slug": "a"}


class PreviewTests(unittest.TestCase):
    def use(self, data):
        previews._data.cache_clear()
        previews._used.clear()
        return patch.object(previews, "load", return_value=data)

    def test_entries_are_returned_and_unused_ones_stop_the_build(self):
        data = {"paper_image": "p.jpg", "pages": {"research": {"description": "Our  research.", "image": "r.jpg",
                                                               "title": "Research – Lab"},
                                                  "gone": {"description": "x", "image": "g.jpg"}}}
        with self.use(data):
            self.assertEqual(previews.preview("research"),
                             {"description": "Our research.", "image": "r.jpg", "share_title": "Research – Lab"})
            with self.assertRaises(SystemExit):
                previews.check_all_used()      # 'gone' matched no page

    def test_missing_or_incomplete_entries_stop_the_build(self):
        with self.use({"paper_image": "p.jpg", "pages": {}}), self.assertRaises(SystemExit):
            previews.preview("software")
        with self.use({"paper_image": "p.jpg", "pages": {"software": {"description": "x"}}}), \
                self.assertRaises(SystemExit):
            previews.preview("software")      # no image


class StructuredDataTests(unittest.TestCase):
    def test_article_is_valid_json_ld_and_safe_in_a_script_tag(self):
        text = to_json(article(STORY, "https://example.org/portfolio/a/", None))
        self.assertNotIn("</script>", text)
        data = json.loads(text)
        work, crumbs = data["@graph"]
        self.assertEqual(work["@type"], "ScholarlyArticle")
        self.assertEqual(work["datePublished"], "2025")          # year when no exact date
        self.assertEqual(work["abstract"], "Line one. Line two.")
        self.assertEqual([i["position"] for i in crumbs["itemListElement"]], [1, 2, 3])

    def test_scholar_tags(self):
        tags = scholar_tags(STORY)
        self.assertIn(["citation_doi", "10.1/x"], tags)
        self.assertEqual([t[1] for t in tags if t[0] == "citation_author"], ["Ana B", "Guillaume Jacquemet"])
        self.assertIn(["citation_publication_date", "2025"], tags)


if __name__ == "__main__":
    unittest.main()
