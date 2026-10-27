"""Regression tests for publication integrity and malformed input handling."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT))
import registered_guard
import run_all

from verify_package import verify


class ReleaseContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads(
            (
                ROOT / "support/model_swap_addendum/frozen/protocol_and_cases.json"
            ).read_text()
        )
        cls.envelope = next(
            case["fixture"]
            for case in fixture["cases"]
            if case["scope"] == "coherent_control"
        )
        cls.registry = json.loads(
            (ROOT / "results/registered_service/trusted_registry.json").read_text()
        )
        cls.modules = registered_guard.load_original(
            registered_guard.SNAP / "source_snapshot"
        )

    def test_registry_shapes_fail_closed(self):
        for registry in (
            None,
            [],
            "invalid",
            {},
            {"records": [], "models": {}},
            {"records": {}, "models": None},
        ):
            with self.subTest(registry=registry):
                result = registered_guard.validate(
                    copy.deepcopy(self.envelope), registry, self.modules
                )
                self.assertFalse(result["research_review_permitted"])
                self.assertIn(
                    "registry_contract_schema_invalid",
                    [error["code"] for error in result["errors"]],
                )
                self.assertFalse(result["automatic_policy_action_allowed"])

    def test_valid_control_still_permitted(self):
        result = registered_guard.validate(
            copy.deepcopy(self.envelope), self.registry, self.modules
        )
        self.assertTrue(result["research_review_permitted"])
        self.assertFalse(result["automatic_policy_action_allowed"])

    def test_nonfinite_reference_is_rejected(self):
        registry = copy.deepcopy(self.registry)
        card = self.envelope["card"]
        key = f"{card['region_code']}:{card['industry_code']}:{card['target_year']}:{card['learned_comparator']['model']}"
        registry["records"][key]["prediction"] = float("nan")
        result = registered_guard.validate(
            copy.deepcopy(self.envelope), registry, self.modules
        )
        self.assertFalse(result["research_review_permitted"])
        self.assertIn(
            "registered_prediction_mismatch",
            [error["code"] for error in result["errors"]],
        )

    def test_manifest_detects_missing_corrupt_and_escaping_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "data.txt").write_text("abc")
            rows = [
                {"path": "missing", "bytes": 0, "sha256": "0" * 64},
                {"path": "data.txt", "bytes": 3, "sha256": "0" * 64},
                {"path": "../outside", "bytes": 0, "sha256": "0" * 64},
            ]
            (root / "manifest_sha256.json").write_text(json.dumps(rows))
            count, errors = verify(root)
            self.assertEqual(count, 3)
            self.assertEqual(len(errors), 3)
            self.assertTrue(any("Unsafe" in error for error in errors))

    def test_runner_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / "keep.txt"
            marker.write_text("unchanged")
            with self.assertRaises(FileExistsError):
                run_all.run(root)
            self.assertEqual(marker.read_text(), "unchanged")

    def test_runner_records_failed_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new"
            job = run_all.Job("failed_stage", Path(__file__), ())
            with (
                patch.object(run_all, "JOBS", (job,)),
                patch.object(
                    run_all.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 7),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    run_all.run(output)
            report = json.loads((output / "run_summary.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["jobs"][0]["exit_code"], 7)


if __name__ == "__main__":
    unittest.main()
