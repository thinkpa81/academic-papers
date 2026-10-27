#!/usr/bin/env python3
"""Independent checks on recorded selections, metrics, time order and claims."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
checks = []


def check(name, ok):
    checks.append({"check": name, "passed": bool(ok)})
    if not ok:
        raise ValueError(f"Result validation failed: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional report path; default is read-only verification.",
    )
    args = parser.parse_args()
    checks.clear()
    b = ROOT / "results/benchmark"
    protocol = json.loads((b / "protocol_before_fit.json").read_text())
    candidates = protocol["candidates"]
    check("38 candidates", len(candidates) == 38)
    metrics = pd.read_csv(b / "all_metrics.csv")
    pan = pd.read_csv(
        ROOT
        / "support/baseline/base_v11/analysis_harmonized/results/main/analysis_panel.csv"
    )
    check(
        "unique panel keys",
        not pan.duplicated(["target_year", "region_code", "industry_code"]).any(),
    )
    check(
        "panel counts",
        pan.groupby("split").size().to_dict()
        == {"test": 428, "train": 558, "validation": 463},
    )
    for label in ["fixed"] + [str(y) for y in range(2020, 2026)]:
        p = pd.read_csv(b / label / "predictions.csv", float_precision="round_trip")
        v = pd.read_csv(
            b / label / "validation_predictions.csv", float_precision="round_trip"
        )
        g = pd.read_csv(b / label / "validation_grid.csv", float_precision="round_trip")
        s = json.loads((b / label / "selection_before_test.json").read_text())
        check(label + " chronological order", v.target_year.max() < p.target_year.min())
        check(label + " complete grid", len(g) == 38)
        for row in g.itertuples():
            check(
                label + " validation " + row.name,
                abs(np.abs(v.target_logpoints - v[row.name]).mean() - row.mae) < 1e-10,
            )
        for row in metrics[metrics.split.astype(str) == label].itertuples():
            check(
                label + " prediction binding " + row.strategy,
                np.allclose(p[row.strategy], p[row.selected_model], rtol=0, atol=1e-12),
            )
            e = np.abs(p.target_logpoints - p[row.strategy])
            check(label + " MAE " + row.strategy, abs(e.mean() - row.mae) < 1e-10)
            check(
                label + " wMAE " + row.strategy,
                abs(np.average(e, weights=p.employment_input_persons) - row.wmae)
                < 1e-10,
            )
        best = g.sort_values("mae", kind="stable").iloc[0]["name"]
        check(label + " all38 validation choice", s["selected"]["all38"] == best)
    reg = pd.read_csv(ROOT / "results/registered_service/case_results.csv")
    check("1006 service cases", len(reg) == 1006)
    check("all declared service expectations", reg.matches.all())
    check(
        "14 known probes blocked",
        len(
            reg[
                (reg.scope == "extended_model_provenance_probe")
                & (reg.observed == "structured_block")
            ]
        )
        == 14,
    )
    empty = pd.read_csv(ROOT / "field_study/responses_EMPTY.csv")
    check("no fabricated observations", len(empty) == 0)
    schedule = pd.read_csv(ROOT / "field_study/counterbalanced_assignment.csv")
    check(
        "planned balance", schedule.groupby(["task_id", "condition"]).size().eq(3).all()
    )
    check(
        "one exposure per participant-task",
        not schedule.duplicated(["participant_code", "task_id"]).any(),
    )
    report = {
        "status": "PASS",
        "checks_passed": len(checks),
        "checks": checks,
        "human_participants": 0,
        "scope": "numeric consistency, recorded validation choices, time ordering, service expectations and empty field records",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("PASS", len(checks))


if __name__ == "__main__":
    main()
