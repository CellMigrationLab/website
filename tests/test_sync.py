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


if __name__ == "__main__":
    unittest.main()
