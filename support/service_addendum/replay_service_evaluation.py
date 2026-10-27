"""Replay frozen service suites into a new directory without changing archived results."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

import audit_tests
import run_technical_evaluation as primary
import workflow_guard as v1
import workflow_guard_v2 as v2

HERE = Path(__file__).resolve().parent


def dump(x, p):
    p.write_text(
        json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists():
        raise RuntimeError(
            "Choose a new output directory; archived results are never overwritten."
        )
    out.mkdir(parents=True)
    modules = v1.load_original(HERE / "source_snapshot")
    oldout = out / "original_comparison"
    oldout.mkdir()
    shutil.copy2(
        HERE / "existing_reproduction/frozen_cases.json", oldout / "frozen_cases.json"
    )
    primary.run(
        argparse.Namespace(
            output_dir=oldout,
            freeze_only=False,
            source_root=HERE / "source_snapshot",
            protocol=HERE / "technical_protocol_v1.json",
        )
    )
    rows = []
    traces = []
    suite_paths = {
        "original55": HERE / "existing_reproduction/frozen_cases.json",
        "extended88": HERE / "extended_audit/protocol_and_cases.json",
    }
    for suite, path in suite_paths.items():
        for case in json.loads(path.read_text())["cases"]:
            expected = case.get(
                "expected",
                "structured_block" if case.get("expected_block") else "permit",
            )
            for version, guard in [("v1", v1), ("v2", v2)]:
                result = None
                exc = None
                try:
                    result = guard.validate(copy.deepcopy(case["fixture"]), modules)
                    observed = (
                        "permit"
                        if result["research_review_permitted"]
                        else "structured_block"
                    )
                except Exception as e:
                    observed = "unhandled_exception"
                    exc = type(e).__name__ + ": " + str(e)
                rows.append(
                    dict(
                        suite=suite,
                        version=version,
                        case_id=case["case_id"],
                        family=case["family"],
                        expected=expected,
                        observed=observed,
                        matches_original_oracle=expected == observed,
                        exception=exc,
                    )
                )
                traces.append(
                    dict(
                        suite=suite,
                        version=version,
                        case_id=case["case_id"],
                        result=result,
                        exception=exc,
                    )
                )
    migrated = json.loads((HERE / "v2_comparison/migration_control.json").read_text())
    r = v2.validate(migrated["fixture"], modules)
    dump(r, out / "migration_result.json")
    dump(traces, out / "all_traces.json")
    with (out / "case_results.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for version, guard in [("v1", v1), ("v2", v2)]:
        audit_tests.validate = guard.validate
        sys.argv = [
            "audit_tests.py",
            "--source-root",
            str(HERE / "source_snapshot"),
            "--frozen-cases",
            str(HERE / "existing_reproduction/frozen_cases.json"),
            "--output",
            str(out / ("audit18_" + version + ".json")),
        ]
        audit_tests.main()
    summary = []
    for suite in suite_paths:
        for version in ["v1", "v2"]:
            g = [r for r in rows if r["suite"] == suite and r["version"] == version]
            summary.append(
                dict(
                    suite=suite,
                    version=version,
                    n=len(g),
                    matching=sum(r["matches_original_oracle"] for r in g),
                    unexpected_permit=sum(
                        r["expected"] == "structured_block"
                        and r["observed"] == "permit"
                        for r in g
                    ),
                    changed_to_block=sum(
                        r["expected"] == "permit"
                        and r["observed"] == "structured_block"
                        for r in g
                    ),
                    exceptions=sum(r["observed"] == "unhandled_exception" for r in g),
                )
            )
    dump(
        dict(
            summary=summary,
            inputs_sha256={
                k: hashlib.sha256(p.read_bytes()).hexdigest()
                for k, p in suite_paths.items()
            },
            explanation="Expected preserved findings: V1 88-case suite has 8 extended-contract permits and 2 numeric exceptions; V2 N09 is blocked due newly required display consistency. These are not silently relabelled.",
            migrated_control_permitted=r["research_review_permitted"],
        ),
        out / "replay_summary.json",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
