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
        self.assertNotIn("datePublished", work)                  # no year-only dates in schema.org
        self.assertEqual(work["abstract"], "Line one. Line two.")
        self.assertEqual([i["position"] for i in crumbs["itemListElement"]], [1, 2, 3])

    def test_no_lab_ownership_claim_on_papers(self):
        """Featured papers, including ones from before the lab (2019), name their
        authors but do not claim the current lab as their source (#30)."""
        old = {**STORY, "year": 2016, "pubs": [{**STORY["pubs"][0], "year": 2016}]}
        for story in (STORY, old):
            with self.subTest(year=story["year"]):
                work = article(story, "https://example.org/portfolio/a/", None)["@graph"][0]
                self.assertNotIn("sourceOrganization", work)
                self.assertNotIn("publisher", work)
                self.assertEqual([a["name"] for a in work["author"]], ["Ana B", "Guillaume Jacquemet"])
                self.assertNotIn("#lab", json.dumps(work))

    def test_scholar_tags(self):
        tags = scholar_tags(STORY)
        self.assertIn(["citation_doi", "10.1/x"], tags)
        self.assertEqual([t[1] for t in tags if t[0] == "citation_author"], ["Ana B", "Guillaume Jacquemet"])
        self.assertIn(["citation_publication_date", "2025"], tags)

    def test_dates_known_only_to_the_month_are_not_made_full(self):
        month = {**STORY, "date": "2025-09"}
        work = article(month, "https://example.org/p/", None)["@graph"][0]
        self.assertNotIn("datePublished", work)
        self.assertIn(["citation_publication_date", "2025"], scholar_tags(month))
        day = {**STORY, "date": "2025-09-14"}
        self.assertEqual(article(day, "https://example.org/p/", None)["@graph"][0]["datePublished"], "2025-09-14")
        self.assertIn(["citation_publication_date", "2025/09/14"], scholar_tags(day))


class RightsTests(unittest.TestCase):
    """#28: rights come from data/media.yaml; nothing is inferred or implied."""

    def test_theme_images_are_recorded(self):
        """The favicon and touch icon are named in mkdocs.yml and overrides/, not by images.py."""
        from cellmig import rights
        with patch.object(rights, "_used", set()):
            rights.use_theme_images()
            self.assertIn("apple-touch-icon.png", rights._used)
            self.assertIn("wp-content/uploads/2019/08/cropped-cover4-1.jpg", rights._used)

    def use(self, entries):
        from cellmig import rights
        rights.registry.cache_clear()
        return patch.object(rights, "load", return_value={"media": entries})

    def test_credit_and_image_object(self):
        from cellmig import rights
        with self.use([{"path": "a.jpg", "type": "microscopy", "rights": "all-rights-reserved",
                        "creators": ["Emilia Peuhu", "Guillaume Jacquemet"]},
                       {"path": "c.jpg", "type": "journal-cover", "rights": "third-party", "source": "J Cell Sci"},
                       {"path": "u.jpg", "type": "photo", "rights": "unknown"},
                       {"path": "b.jpg", "type": "microscopy", "rights": "CC-BY-4.0", "creators": ["Ana Popović"]}]):
            self.assertEqual(rights.credit("a.jpg"), "© Emilia Peuhu and Guillaume Jacquemet")
            self.assertEqual(rights.credit("c.jpg"), "Cover © the publisher")
            self.assertEqual(rights.credit("u.jpg"), "")                       # unknown: no credit shown
            for path in ("a.jpg", "c.jpg", "u.jpg"):                            # no open licence on these
                self.assertNotIn("license", rights.image_object(path, "https://x/"))
            self.assertEqual(rights.image_object("a.jpg", "https://x/")["creator"][0]["name"], "Emilia Peuhu")
            # an open licence is named in the credit and linked in the ImageObject
            self.assertEqual(rights.credit("b.jpg"), "© Ana Popović · CC BY 4.0")
            obj = rights.image_object("b.jpg", "https://x/")
            self.assertEqual((obj["license"], obj["creditText"], obj["copyrightNotice"]),
                             ("https://creativecommons.org/licenses/by/4.0/", "Ana Popović", "© Ana Popović"))

    def test_bad_entries_stop_the_build(self):
        from cellmig import rights
        for bad in ({"path": "a", "type": "microscopy", "rights": "CC-BY-4.0"},          # licence without creators
                    {"path": "a", "type": "logo", "rights": "third-party"},              # third-party without source
                    {"path": "a", "type": "logo", "rights": "third-party", "source": "X", "owner": "Lab"},
                    {"path": "a", "type": "microscopy", "rights": "MIT", "creators": ["X"]}):  # not an image licence
            with self.subTest(bad=bad), self.use([bad]), self.assertRaises(SystemExit):
                rights.registry()
        with self.use([]), self.assertRaises(SystemExit):
            rights.entry("missing.jpg")


if __name__ == "__main__":
    unittest.main()
