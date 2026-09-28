"""Tests for the research-output feed (#22).

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import unittest

from cellmig import outputs
from cellmig.outputs import _item, build_outputs


class OutputTests(unittest.TestCase):
    def test_dates_are_only_as_precise_as_the_ledger(self):
        self.assertEqual(_item("2026-09-04", "paper", "t", "h", "u")["precision"], "day")
        self.assertEqual(_item("2026-08", "software", "t", "h", "u")["precision"], "month")
        # 1 January comes from year-only (CV-style) records
        self.assertEqual(_item("2026-01-01", "dataset", "t", "h", "u")["precision"], "year")
        self.assertEqual(_item("2026", "software", "t", "h", "u")["precision"], "year")
        # an explicit precision wins: a lag-report day may be 1 January
        self.assertEqual(_item("2026-01-01", "paper", "t", "h", "u", "day")["date"], "2026-01-01")
        self.assertEqual(_item("2026-08-01", "paper", "t", "h", "u", "month")["date"], "2026-08")

    def test_partial_dates_sort_and_filter_as_far_as_known(self):
        from unittest.mock import patch

        from test_build import fake_ledger, pub
        led = fake_ledger([pub("10.1/y", 2024, title="Year"), pub("10.1/m", 2024, title="Jan"),
                           pub("10.1/d", 2024, title="Day"), pub("10.1/old", 2023, title="Old")])
        led.dates = {"10.1/m": "2024-01", "10.1/d": "2024-01-20", "10.1/old": "2023-12"}
        with patch.object(outputs, "software_list", return_value=[]):
            items = build_outputs(led, [])
        # January 2024 is not dropped for being "before" 2024-01-01; the month
        # comes after the day in it, the bare year last
        self.assertEqual([(i["title"], i["date"]) for i in items],
                         [("Day", "2024-01-20"), ("Jan", "2024-01"), ("Year", "2024")])

    def test_preprints_get_their_own_date(self):
        """Dates come from each record's publication_date, not only from preprint-paper pairs."""
        from unittest.mock import patch

        from test_build import fake_ledger, pub
        led = fake_ledger([pub("10.1101/p", 2025, "preprint", "Preprint P", publication_date="2025-03-04")])
        led.datasets = []
        with patch.object(outputs, "software_list", return_value=[]):
            items = build_outputs(led, [])
        self.assertEqual([(i["kind"], i["date"], i["precision"]) for i in items], [("preprint", "2025-03-04", "day")])

    def test_feed_has_pubdates_only_for_days(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from cellmig import site_files
        items = [_item("2026-09-04", "paper", "Day", "h", "u", "day"), _item("2026-08", "paper", "Month", "h", "u", "month"),
                 _item("2026", "software", "Year", "h", "u")]
        with TemporaryDirectory() as tmp, patch.object(site_files, "DOCS", Path(tmp)):
            site_files.write_feed({"name": "Lab"}, items)
            rss = (Path(tmp) / "feed.xml").read_text()
        self.assertEqual(rss.count("<pubDate>"), 1)
        self.assertIn("<pubDate>Fri, 04 Sep 2026 00:00:00 +0000</pubDate>", rss)

    def test_only_research_outputs(self):
        """Papers, preprints, software and datasets; no talks, events, funding or positions."""
        from unittest.mock import patch

        from test_build import fake_ledger, pub
        led = fake_ledger([pub("10.1/a", 2026, title="Paper A"), pub("10.1101/b", 2025, "preprint", "Preprint B"),
                           pub("10.1/old", 2019, title="Old paper")])
        led.datasets = [{"title": "Data D", "start_date": "2025", "repository_url": "https://zenodo.org/x"}]
        led.talks = [{"date": "2026-05-01", "title": "Keynote", "talk_kind": "keynote", "event_name": "E"}]
        led.grants = [{"title": "Grant", "start_date": "2026-01-01", "status": "active", "funders": ["F"]}]
        with patch.object(outputs, "software_list", return_value=[{"title": "Tool T", "year": 2024}]):
            items = build_outputs(led, [])
        self.assertEqual(sorted({i["kind"] for i in items}), ["dataset", "paper", "preprint", "software"])
        self.assertEqual({i["title"] for i in items}, {"Paper A", "Preprint B", "Tool T", "Data D"})   # 2019: too old
        self.assertEqual([i["date"][:4] for i in items], sorted((i["date"][:4] for i in items), reverse=True))


if __name__ == "__main__":
    unittest.main()
