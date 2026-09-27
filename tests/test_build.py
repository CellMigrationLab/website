"""Unit tests for the page generator (scripts/cellmig/).

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import unittest
from datetime import date
from unittest.mock import patch

from cellmig import featured, ledger
from cellmig.charts import lag_section
from cellmig.page import Page
from cellmig.people import is_lab_member, lab_names
from cellmig.profile import month_year, recent_talks
from cellmig.text import fmt, is_external, normalize_name, plural, slugify
from cellmig.worldmap import color


def fake_ledger(pubs, lag_pairs=()):
    """A Ledger over in-memory records (skips reading data/things_done/)."""
    led = object.__new__(ledger.Ledger)
    led.pubs = pubs
    led.by_doi = {p["doi"].lower(): p for p in pubs}
    led.software, led.datasets, led.affiliations = [], [], []
    led.dates = {p["published_doi"].lower(): p["published_date"] for p in lag_pairs}
    return led


PRE = {"doi": "10.1101/pre", "year": 2023, "status": "preprint", "title": "Pre", "related_dois": ["10.1/J"]}
JOURNAL = {"doi": "10.1/j", "year": 2024, "status": "published", "title": "Journal", "related_dois": ["10.1101/pre"]}


class TextTests(unittest.TestCase):
    def test_slugify_and_names(self):
        self.assertEqual(slugify("Iván Hidalgo Cenalmor"), "ivan-hidalgo-cenalmor")
        self.assertEqual(normalize_name("Joanna Pylvänäinen"), normalize_name("joanna pylvanainen"))

    def test_small_helpers(self):
        self.assertEqual(fmt(8562), "8 562")
        self.assertEqual(plural(1, "paper"), "1 paper")
        self.assertEqual(plural(2, "paper"), "2 papers")
        self.assertTrue(is_external("mailto:x@y.z"))
        self.assertTrue(is_external("#top"))
        self.assertFalse(is_external("software/"))


class PageTests(unittest.TestCase):
    def test_links_relative_to_file_and_to_final_url(self):
        p = Page("portfolio/cdm.md")
        self.assertEqual(p.u("software/"), "../software/")                   # href/src: from the .md file
        self.assertEqual(p.u("assets/a.jpg", final_url=True), "../../assets/a.jpg")  # srcset: from /portfolio/cdm/
        self.assertEqual(Page("index.md").u("", final_url=True), "")
        self.assertEqual(Page("index.md").u("/"), "./")

    def test_fix_links_leaves_external_and_relative_links(self):
        p = Page("research.md")
        html = '<a href="https://x.org"></a><a href="../y/"></a><img src="a.png" srcset="a.png 1x, b.png 2x">'
        self.assertEqual(p.fix_links(html),
                         '<a href="https://x.org"></a><a href="../y/"></a>'
                         '<img src="a.png" srcset="../a.png 1x, ../b.png 2x">')


class LedgerTests(unittest.TestCase):
    def test_preprint_folded_into_journal_version(self):
        led = fake_ledger([JOURNAL, PRE])
        self.assertEqual([r["doi"] for r in led.grouped()], ["10.1/j"])
        self.assertIs(led.published_version(PRE), JOURNAL)
        self.assertIs(led.preprint_of(JOURNAL), PRE)
        self.assertEqual(led.family_dois("10.1101/PRE"), {"10.1101/pre", "10.1/j"})

    def test_standalone_preprint_is_kept(self):
        led = fake_ledger([JOURNAL, dict(PRE, standalone=True)])
        self.assertEqual(len(led.grouped()), 2)

    def test_unknown_doi_stops_the_build(self):
        with self.assertRaises(SystemExit):
            fake_ledger([JOURNAL]).require("10.9/missing", "test")

    def test_software_id_not_in_ledger_stops_the_build(self):
        led = fake_ledger([])
        led.software = [{"id": "trackmate", "title": "TrackMate"}]
        with patch.object(ledger, "load", return_value=[{"id": "trakmate", "image": "x.png"}]):
            with self.assertRaises(SystemExit):
                ledger.software_list(led)

    def test_software_merges_ledger_and_website_only_entries(self):
        led = fake_ledger([])
        led.software = [{"id": "a", "title": "A", "start_date": "2020-01-01", "related_publication_dois": ["10.1/j"]}]
        with patch.object(ledger, "load", return_value=[{"title": "Web only", "year": 2022}, {"id": "a", "color": "sky"}]):
            out = ledger.software_list(led)
        self.assertEqual([s["title"] for s in out], ["Web only", "A"])
        self.assertEqual(out[1]["color"], "sky")
        self.assertEqual(out[1]["dois"], ["10.1/j"])


class FeaturedTests(unittest.TestCase):
    def run_featured(self, pubs, entries, lag_pairs=()):
        with patch.object(featured, "load", return_value=entries):
            return featured.load_featured(fake_ledger(pubs, lag_pairs))

    def test_corresponding_author_papers_are_featured_newest_first(self):
        a = {"doi": "10.1/a", "year": 2024, "status": "published", "title": "A", "corresponding": True}
        b = {"doi": "10.1/b", "year": 2024, "status": "published", "title": "B", "corresponding": True}
        c = {"doi": "10.1/c", "year": 2025, "status": "published", "title": "C", "corresponding": True}
        d = {"doi": "10.1/d", "year": 2026, "status": "published", "title": "D"}   # not corresponding
        lag = [{"published_doi": "10.1/b", "published_date": "2024-03-01"}]
        items = self.run_featured([a, b, c, d], [{"doi": "10.1/c", "image": "c.png"}], lag)
        # 2025 first; in 2024 the dated paper comes before the undated one
        self.assertEqual([i["title"] for i in items], ["C", "B", "A"])
        self.assertEqual(items[0]["image"], "c.png")
        self.assertIsNone(items[2]["date"])        # no made-up dates

    def test_hidden_paper_is_left_out(self):
        a = {"doi": "10.1/a", "year": 2024, "status": "published", "title": "A", "corresponding": True}
        self.assertEqual(self.run_featured([a], [{"doi": "10.1/a", "hide": True}]), [])

    def test_bad_entries_stop_the_build(self):
        a = {"doi": "10.1/a", "year": 2024, "status": "published", "title": "A", "corresponding": True}
        b = {"doi": "10.1/b", "year": 2024, "status": "published", "title": "B"}
        for entry in ({"doi": "10.1/a", "imgae": "x.png"},          # typo in a key
                      {"doi": "10.9/missing"},                      # not in the ledger
                      {"doi": "10.1/a", "also": ["10.9/missing"]},  # `also` not in the ledger
                      {"doi": "10.1/b", "image": "b.png"},          # not corresponding-author
                      {"doi": "10.1/a", "show": True}):             # `show` no longer exists
            with self.subTest(entry=entry), self.assertRaises(SystemExit):
                self.run_featured([a, b], [entry])


class AffiliationTests(unittest.TestCase):
    def setUp(self):
        self.led = fake_ledger([])
        self.led.affiliations = [{"id": "aau", "organization": "Åbo Akademi", "title": "Professor"},
                                 {"id": "fci", "organization": "Finnish Cancer Institute", "title": "Research Professor"}]

    def test_merged_in_website_order(self):
        out = ledger.affiliation_list([{"id": "fci", "name": "FCI", "logo": "f.png", "relation": "leader"},
                                       {"id": "aau", "name": "ÅA", "logo": "a.png", "relation": "parent"}], self.led)
        self.assertEqual([a["name"] for a in out], ["FCI", "ÅA"])
        self.assertEqual(out[0]["title"], "Research Professor")

    def test_missing_or_stale_entries_stop_the_build(self):
        for presentation in ([{"id": "aau", "relation": "parent"}],          # fci has no logo entry
                             [{"id": "aau", "relation": "parent"}, {"id": "fci", "relation": "leader"},
                              {"id": "old", "relation": "member"}],           # old is not current
                             [{"id": "aau", "relation": "boss"}, {"id": "fci", "relation": "leader"}]):  # bad relation
            with self.subTest(presentation=presentation), self.assertRaises(SystemExit):
                ledger.affiliation_list(presentation, self.led)


class FundingTests(unittest.TestCase):
    def test_current_funders_only_and_strict(self):
        led = fake_ledger([])
        led.grants = [{"funder": "Wellcome Trust", "status": "active", "end_date": "2027-12-31"},
                      {"funder": "EMBO", "status": "completed", "end_date": "2016-12-31"},
                      {"funder": "Old", "status": "active", "end_date": "2020-01-01"}]
        ok = [{"funder": "Wellcome Trust", "name": "Wellcome", "logo": "w.svg"}]
        self.assertEqual(ledger.funding_list(ok, led, "2026-09-27"), ok)
        with self.assertRaises(SystemExit):            # EMBO no longer funds anything
            ledger.funding_list(ok + [{"funder": "EMBO"}], led, "2026-09-27")
        with self.assertRaises(SystemExit):            # Wellcome has no logo entry
            ledger.funding_list([], led, "2026-09-27")


class TalkTests(unittest.TestCase):
    def test_month_year_and_recent_talks(self):
        self.assertEqual(month_year("2026-08"), "Aug 2026")
        self.assertEqual(month_year("2026-09-18"), "Sep 2026")
        led = fake_ledger([])
        led.talks = [{"date": "2026-09-01", "title": "New", "talk_kind": "keynote"},
                     {"date": "2026-06-01", "title": "Panel", "talk_kind": "panel_participation"},
                     {"date": "2020-01-01", "title": "Old", "talk_kind": "invited_talk"}]
        self.assertEqual([t["title"] for t in recent_talks(led, date(2026, 9, 27))], ["New"])


class PeopleTests(unittest.TestCase):
    def test_middle_initial_and_other_spellings(self):
        lab = lab_names([{"name": "Joanna Pylvänäinen"}, {"name": "Ana Popović", "also_known_as": ["Ana Gračanin"]}])
        self.assertTrue(is_lab_member("Joanna W. Pylvänäinen", lab))
        self.assertTrue(is_lab_member("Ana Gracanin", lab))
        self.assertFalse(is_lab_member("Ana Smith", lab))


class ChartTests(unittest.TestCase):
    def test_map_colour_steps(self):
        self.assertEqual(color(1), "#e9ddf7")
        self.assertEqual(color(5), "#b48ae3")
        self.assertEqual(color(1000), "#4f2182")

    def test_lag_section_uses_the_ledger_summary_and_handles_negative_gaps(self):
        pair = {"published_doi": "10.1/j", "published_title": "T", "preprint_date": "2020-01-01",
                "published_date": "2020-03-01", "preprint_date_precision": "day", "published_date_precision": "day"}
        pairs = [dict(pair, gap_days=60), dict(pair, gap_days=-20, published_date="2019-12-12")]
        html = lag_section(pairs, {"pairs": 2, "median_months": 1.3})
        self.assertIn("<strong>1.3</strong>", html)
        self.assertIn(">-6</text>", html)          # axis extended left for the negative gap


if __name__ == "__main__":
    unittest.main()
