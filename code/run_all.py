#!/usr/bin/env python3
"""Run the paper's nine analysis stages in a new output folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "support"
CONTROLLED_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
}
INVENTORY_DIRECTORIES = ("code", "raw", "support")
EXCLUDED_COMPONENTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}


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


def save_status(output: Path, report: dict[str, Any]) -> None:
    """Publish complete status records even if a later stage fails."""
    temporary = output / "run_summary.json.tmp"
    temporary.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(output / "run_summary.json")


def select_jobs(selected: list[str] | None) -> list[Job]:
    """Validate programmatic callers as well as command-line selections."""
    if selected is None:
        return list(JOBS)
    if not selected:
        raise ValueError("Select at least one analysis stage")
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate analysis stages are not permitted")
    unknown = set(selected) - {job.name for job in JOBS}
    if unknown:
        raise ValueError("Unknown analysis stages: " + ", ".join(sorted(unknown)))
    return [job for job in JOBS if job.name in selected]


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def source_inventory() -> list[dict[str, Any]]:
    """Fingerprint available analysis sources; this is not a file-access trace."""
    paths = {ROOT / "requirements.txt", ROOT / "pyproject.toml"}
    for directory in INVENTORY_DIRECTORIES:
        paths.update((ROOT / directory).rglob("*"))
    records = []
    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_COMPONENTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Analysis source must not be a symlink: {relative}")
        if path.is_file() and path.suffix != ".pyc":
            records.append({"path": relative.as_posix(), **file_fingerprint(path)})
    return records


def dependency_versions() -> dict[str, dict[str, str | None]]:
    """Record the installed versions without importing analysis packages."""
    versions = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        requirement = line.partition("#")[0].strip()
        if not requirement:
            continue
        name, separator, expected = requirement.partition("==")
        if not separator:
            raise ValueError(f"Expected a pinned dependency: {requirement}")
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        versions[name] = {"required": expected, "installed": installed}
    return versions


def run(output: Path, selected: list[str] | None = None) -> None:
    output = output.expanduser().resolve()
    jobs = select_jobs(selected)
    for directory in INVENTORY_DIRECTORIES:
        if output.is_relative_to(ROOT / directory):
            raise ValueError(f"Output must be outside analysis sources: {directory}/")
    missing = [str(job.script) for job in jobs if not job.script.is_file()]
    if missing:
        raise FileNotFoundError("Missing analysis scripts: " + ", ".join(missing))
    # Atomic creation prevents concurrent runs from sharing an output directory.
    output.mkdir(parents=True, exist_ok=False)
    environment = {**os.environ, **CONTROLLED_ENVIRONMENT}
    report = {
        "schema_version": 2,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "python": sys.version,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "controlled_environment": CONTROLLED_ENVIRONMENT,
        "selected_jobs": [job.name for job in jobs],
        "jobs": [],
    }
    save_status(output, report)
    try:
        inventory_path = output / "source_inventory.json"
        inventory_path.write_text(
            json.dumps(
                {
                    "scope": "Available code, raw inputs and support files at run start; not a file-access trace",
                    "files": source_inventory(),
                },
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        report["source_inventory"] = {
            "path": inventory_path.name,
            **file_fingerprint(inventory_path),
        }
        report["dependencies"] = dependency_versions()
        save_status(output, report)
    except (OSError, ValueError) as exc:
        report.update(
            status="failed",
            error=f"Run preparation failed: {exc}",
            completed_utc=datetime.now(timezone.utc).isoformat(),
        )
        save_status(output, report)
        raise
    for job in jobs:
        print(f"Running {job.name}", flush=True)
        record = {
            "job": job.name,
            "status": "running",
            "log": job.name + ".log",
            "command": job.command(output),
        }
        report["jobs"].append(record)
        save_status(output, report)
        started = time.monotonic()
        try:
            record["script"] = file_fingerprint(job.script)
            with (output / record["log"]).open("w", encoding="utf-8") as log:
                process = subprocess.run(
                    record["command"],
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
            status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
            record.update(status=status, error=str(exc) or type(exc).__name__)
            report.update(
                status=status, completed_utc=datetime.now(timezone.utc).isoformat()
            )
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
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "Analysis interrupted; inspect run_summary.json\n")


if __name__ == "__main__":
    main()
