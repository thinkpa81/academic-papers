"""Failure cases for completeness-aware, read-only numerical audit helpers."""

import gzip
import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import v3_independent_audit as audit
import verify_figure_data


class NumericalAuditContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.reference = root / "reference"
        self.replay = root / "replay"
        for folder in (self.reference, self.replay):
            (folder / "stage").mkdir(parents=True)

    def write_csv(self, root, name, text="value\n1.5\n"):
        path = root / "stage" / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_missing_output_is_not_silently_skipped(self):
        self.write_csv(self.reference, "required.csv")
        comparisons, extras = audit.compare_replay(
            self.replay, self.reference, ("stage",)
        )
        self.assertEqual(len(comparisons), 1)
        self.assertFalse(comparisons[0]["passed"])
        self.assertIn("missing", comparisons[0]["error"])
        self.assertEqual(extras, [])

    def test_extra_output_is_reported_as_uncompared(self):
        self.write_csv(self.reference, "required.csv")
        self.write_csv(self.replay, "required.csv")
        self.write_csv(self.replay, "new.csv")
        comparisons, extras = audit.compare_replay(
            self.replay, self.reference, ("stage",)
        )
        self.assertTrue(comparisons[0]["passed"])
        self.assertEqual(extras, ["stage/new.csv"])

    def test_compressed_reference_matches_plain_replay(self):
        path = self.reference / "stage" / "values.csv.gz"
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            stream.write("value\n1.5\n")
        self.write_csv(self.replay, "values.csv")
        comparisons, extras = audit.compare_replay(
            self.replay, self.reference, ("stage",)
        )
        self.assertTrue(comparisons[0]["passed"])
        self.assertEqual(extras, [])

    def test_numerical_mismatch_is_reported(self):
        self.write_csv(self.reference, "values.csv")
        self.write_csv(self.replay, "values.csv", "value\n2.5\n")
        comparisons, _ = audit.compare_replay(self.replay, self.reference, ("stage",))
        self.assertFalse(comparisons[0]["passed"])

    def test_ambiguous_compression_variants_are_rejected(self):
        self.write_csv(self.reference, "values.csv")
        with gzip.open(self.reference / "stage" / "values.csv.gz", "wt") as stream:
            stream.write("value\n1.5\n")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            audit.csv_inventory(self.reference, ("stage",))

    def test_figure_module_import_performs_no_artifact_io(self):
        with (
            patch.object(
                Path, "open", side_effect=AssertionError("unexpected file I/O")
            ),
            patch.object(
                Path, "read_text", side_effect=AssertionError("unexpected read")
            ),
            patch.object(
                Path, "write_text", side_effect=AssertionError("unexpected write")
            ),
        ):
            importlib.reload(verify_figure_data)


if __name__ == "__main__":
    unittest.main()
