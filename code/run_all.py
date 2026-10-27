#!/usr/bin/env python3
"""Run the paper's nine analysis stages in a new output folder."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "support"


@dataclass(frozen=True)
class Job:
    name: str
    script: Path
    arguments: tuple[str, ...]

    def command(self, output: Path) -> list[str]:
        return [
            sys.executable,
            str(self.script),
            *self.arguments,
            str(output / self.name),
        ]


JOBS = (
    Job("forecast_replay", SUPPORT / "forecast_addendum/run_addendum.py", ("--out",)),
    Job(
        "service_replay",
        SUPPORT / "service_addendum/replay_service_evaluation.py",
        ("--output",),
    ),
    Job(
        "model_swap_replay",
        SUPPORT / "model_swap_addendum/model_swap_audit.py",
        ("--out",),
    ),
    Job(
        "preserved_audit",
        SUPPORT / "original_result_audit/run_audit.py",
        ("--base", str(SUPPORT / "baseline/base_v11"), "--out"),
    ),
    Job(
        "local_fallback",
        SUPPORT / "baseline/code/evaluate_local_fallback.py",
        ("--source-root", str(SUPPORT / "baseline/base_v11"), "--output-dir"),
    ),
    Job("benchmark", ROOT / "code/run_benchmark.py", ("--out",)),
    Job("diagnostics", ROOT / "code/run_diagnostics.py", ("--out",)),
    Job("registered_service", ROOT / "code/run_registered_evaluation.py", ("--out",)),
    Job("transfer_evaluation", ROOT / "code/run_transfer_evaluation.py", ("--out",)),
)


def save_status(output: Path, report: dict) -> None:
    """Publish complete status records even if a later stage fails."""
    temporary = output / "run_summary.json.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output / "run_summary.json")


def run(output: Path, selected: list[str] | None = None) -> None:
    output = output.expanduser().resolve()
    jobs = [job for job in JOBS if selected is None or job.name in selected]
    missing = [str(job.script) for job in jobs if not job.script.is_file()]
    if missing:
        raise FileNotFoundError("Missing analysis scripts: " + ", ".join(missing))
    # Atomic creation prevents concurrent runs from sharing an output directory.
    output.mkdir(parents=True, exist_ok=False)
    environment = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
    }
    report = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "python": sys.version,
        "jobs": [],
    }
    save_status(output, report)
    for job in jobs:
        print(f"Running {job.name}", flush=True)
        record = {"job": job.name, "status": "running", "log": job.name + ".log"}
        report["jobs"].append(record)
        save_status(output, report)
        started = time.monotonic()
        try:
            with (output / record["log"]).open("w", encoding="utf-8") as log:
                process = subprocess.run(
                    job.command(output),
                    cwd=ROOT,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                )
            record["exit_code"] = process.returncode
            if process.returncode:
                raise RuntimeError(
                    f"{job.name} failed; inspect {output / record['log']}"
                )
        except (OSError, RuntimeError, KeyboardInterrupt) as exc:
            record.update(status="failed", error=str(exc))
            report["status"] = "failed"
            raise
        else:
            record["status"] = "passed"
        finally:
            record["seconds"] = round(time.monotonic() - started, 3)
            save_status(output, report)
    report.update(status="passed", completed_utc=datetime.now(timezone.utc).isoformat())
    save_status(output, report)
    print(f"Completed {len(jobs)} stages: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="New output directory; existing directories are rejected.",
    )
    parser.add_argument(
        "--jobs",
        nargs="+",
        choices=[job.name for job in JOBS],
        help="Run selected stages in their declared order.",
    )
    args = parser.parse_args()
    try:
        run(args.out, args.jobs)
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
