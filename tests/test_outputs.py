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

    def test_only_research_outputs(self):
        """Papers, preprints, software and datasets; no talks, events, funding or positions."""
        from unittest.mock import patch

        from test_build import fake_ledger, pub
        led = fake_ledger([pub("10.1/a", 2026, title="Paper A"), pub("10.1101/b", 2025, "preprint", "Preprint B"),
                           pub("10.1/old", 2019, title="Old paper")])
        led.lag_pairs = []
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
