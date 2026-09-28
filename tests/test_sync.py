"""The things_done sync copies only what may be published."""

import tempfile
import unittest
from pathlib import Path

import yaml

import sync_things_done


class PublicRecordsTests(unittest.TestCase):
    def test_internal_and_confidential_records_are_never_copied(self):
        rows = [{"id": "a"}, {"id": "b", "confidentiality": "public"},
                {"id": "c", "confidentiality": "internal"}, {"id": "d", "confidentiality": "confidential"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "talks.yaml"
            path.write_text(yaml.safe_dump({"records": rows}), encoding="utf-8")
            self.assertEqual([r["id"] for r in sync_things_done.public_records(path)], ["a", "b"])



class CleanTextTests(unittest.TestCase):
    def test_inline_tags_leave_no_space_before_punctuation(self):
        text = "Mounting <jats:italic>in vitro</jats:italic>\n , <i>in vivo</i> and clinical evidence."
        self.assertEqual(sync_things_done.clean_text(text, abstract=True), "Mounting in vitro, in vivo and clinical evidence.")

    def test_only_abstracts_lose_a_leading_heading(self):
        self.assertEqual(sync_things_done.clean_text("<jats:title>Abstract</jats:title><jats:p>Cells move.</jats:p>",
                                                     abstract=True), "Cells move.")
        self.assertEqual(sync_things_done.clean_text("Summary statistics of cell migration"),
                         "Summary statistics of cell migration")


if __name__ == "__main__":
    unittest.main()
