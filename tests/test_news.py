"""Tests for the generated news feed.

    PYTHONPATH=scripts python -m unittest discover -s tests
"""

import unittest

from cellmig.news import _item, date_label


class NewsTests(unittest.TestCase):
    def test_dates_are_only_as_precise_as_the_ledger(self):
        self.assertEqual(date_label(_item("2026-09-04", "paper", "t", "h", None)), "4 Sep 2026")
        self.assertEqual(date_label(_item("2026-08", "talk", "t", "h", None)), "Aug 2026")
        # 1 January comes from year-only (CV-style) records
        self.assertEqual(_item("2026-01-01", "funding", "t", "h", None)["precision"], "year")
        self.assertEqual(date_label(_item("2026-01-01", "funding", "t", "h", None)), "2026")
        self.assertEqual(_item("2026", "software", "t", "h", None)["precision"], "year")


if __name__ == "__main__":
    unittest.main()
