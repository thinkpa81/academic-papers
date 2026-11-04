"""Runner failure boundaries and reproducibility metadata."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import run_all


class RunnerTests(unittest.TestCase):
    def test_invalid_selections_do_not_create_output(self):
        for selection in ([], ["unknown"], ["benchmark", "benchmark"]):
            with (
                self.subTest(selection=selection),
                tempfile.TemporaryDirectory() as tmp,
            ):
                output = Path(tmp) / "run"
                with self.assertRaises(ValueError):
                    run_all.run(output, selection)
                self.assertFalse(output.exists())

    def test_selections_follow_dependency_order(self):
        jobs = run_all.select_jobs(["transfer_evaluation", "benchmark"])
        self.assertEqual(
            [job.name for job in jobs], ["benchmark", "transfer_evaluation"]
        )

    def test_analysis_directories_cannot_receive_run_outputs(self):
        for directory in run_all.INVENTORY_DIRECTORIES:
            with (
                self.subTest(directory=directory),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                output = root / directory / "rerun"
                with patch.object(run_all, "ROOT", root), self.assertRaises(ValueError):
                    run_all.run(output)
                self.assertFalse(output.exists())

    def test_inventory_changes_with_source_and_excludes_bytecode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            source = root / "raw" / "sample.csv"
            source.write_bytes(b"first")
            cache = root / "code" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "module.pyc").write_bytes(b"cache")
            with patch.object(run_all, "ROOT", root):
                first = run_all.source_inventory()
                source.write_bytes(b"second")
                second = run_all.source_inventory()
            self.assertEqual([row["path"] for row in first], ["raw/sample.csv"])
            self.assertEqual(first[0]["sha256"], hashlib.sha256(b"first").hexdigest())
            self.assertNotEqual(first[0]["sha256"], second[0]["sha256"])

    def test_preparation_failure_is_recorded_before_any_stage_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            with (
                patch.object(
                    run_all, "source_inventory", side_effect=OSError("unreadable")
                ),
                patch.object(run_all.subprocess, "run") as process,
                self.assertRaises(OSError),
            ):
                run_all.run(output)
            process.assert_not_called()
            report = json.loads((output / "run_summary.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertIn("completed_utc", report)
            self.assertEqual(report["jobs"], [])

    def test_interruption_does_not_run_later_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            jobs = (
                run_all.Job("first", Path(__file__), ()),
                run_all.Job("second", Path(__file__), ()),
            )
            with (
                patch.object(run_all, "JOBS", jobs),
                patch.object(run_all, "source_inventory", return_value=[]),
                patch.object(run_all, "dependency_versions", return_value={}),
                patch.object(
                    run_all.subprocess, "run", side_effect=KeyboardInterrupt
                ) as process,
                self.assertRaises(KeyboardInterrupt),
            ):
                run_all.run(output)
            self.assertEqual(process.call_count, 1)
            report = json.loads((output / "run_summary.json").read_text())
            self.assertEqual(report["status"], "interrupted")
            self.assertEqual(len(report["jobs"]), 1)
            self.assertEqual(report["jobs"][0]["error"], "KeyboardInterrupt")

    def test_success_records_inventory_digest_and_controlled_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run"
            job = run_all.Job("stage", Path(__file__), ())
            with (
                patch.object(run_all, "JOBS", (job,)),
                patch.object(run_all, "source_inventory", return_value=[]),
                patch.object(run_all, "dependency_versions", return_value={}),
                patch.object(
                    run_all.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0),
                ) as process,
            ):
                run_all.run(output)
            report = json.loads((output / "run_summary.json").read_text())
            inventory = output / report["source_inventory"]["path"]
            self.assertEqual(
                report["source_inventory"]["sha256"],
                hashlib.sha256(inventory.read_bytes()).hexdigest(),
            )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["selected_jobs"], ["stage"])
            self.assertEqual(report["jobs"][0]["exit_code"], 0)
            self.assertEqual(process.call_args.kwargs["env"]["PYTHONHASHSEED"], "0")
            self.assertNotIn("shell", process.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
