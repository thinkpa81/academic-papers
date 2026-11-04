#!/usr/bin/env python3
"""Verify figure values against preserved predictions and evidence cards.

Importing this module performs no file I/O. The command writes a report and
returns a nonzero status when a source is unreadable or any figure check fails.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    """Read CSV records while closing the source stream deterministically."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def audit_figures(root: Path = ROOT) -> dict[str, Any]:
    """Recompute displayed aggregates without fitting or editing source models."""
    base = root / "support/baseline/base_v11/analysis_harmonized/results/main"
    test = rows(base / "test_predictions.csv")
    val = rows(base / "validation_predictions.csv")
    fig = json.loads(
        (root / "figures/fig3_validation.json").read_text(encoding="utf-8")
    )
    cardpath = (
        root
        / "support/model_swap_addendum/guard_snapshot/source_snapshot/reproduced_service/evidence_card_2025_seoul_BTE.json"
    )
    card = json.loads(cardpath.read_text(encoding="utf-8"))
    r = next(
        r
        for r in test
        if r["region_code"] == "KR011"
        and r["industry_code"] == "BTE"
        and r["target_year"] == "2025"
    )
    calc = {
        "baseline": float(r["global_past_mean"]),
        "ridge": float(r["ridge_alpha1000"]),
    }
    calc["difference"] = calc["ridge"] - calc["baseline"]
    calc["actual_logpoints"] = 100 * math.log(
        float(r["employment_target_persons"]) / float(r["employment_input_persons"])
    )
    calc["actual_simple_pct"] = 100 * (
        float(r["employment_target_persons"]) / float(r["employment_input_persons"]) - 1
    )
    calc["validation_cell_n"] = sum(
        r["region_code"] == "KR011" and r["industry_code"] == "BTE" for r in val
    )
    calc["intercept"] = card["linear_explanation"]["intercept_logpoints"]
    cont = {
        c["feature"]: c["contribution_logpoints"]
        for c in card["linear_explanation"]["contributions"]
    }
    calc["other_five_sum"] = sum(cont[k] for k in fig["other_five_keys"])
    calc["reconstructed"] = calc["intercept"] + sum(cont.values())
    checks = []

    def check(name, a, b, tol=1e-12):
        ok = (
            abs(a - b) < tol
            if isinstance(a, (int, float)) and isinstance(b, (int, float))
            else a == b
        )
        checks.append({"check": name, "observed": a, "reference": b, "passed": ok})

    for k in [
        "baseline",
        "ridge",
        "difference",
        "validation_cell_n",
        "intercept",
        "other_five_sum",
        "reconstructed",
    ]:
        check("figure2_" + k, calc[k], fig[k])
    for k, v in fig["shown_contributions"].items():
        check("figure2_contribution_" + k, cont[k], v)
    check(
        "figure2_actual_logpoints",
        calc["actual_logpoints"],
        card["historical_outcome_audit"]["observed_logpoints"],
    )
    check(
        "figure2_actual_simple_pct",
        calc["actual_simple_pct"],
        card["historical_outcome_audit"]["observed_simple_change_pct"],
    )
    check(
        "source_card_sha256",
        hashlib.sha256(cardpath.read_bytes()).hexdigest(),
        fig["source_sha256"],
    )
    supers = {
        "수도권": ["KR011", "KR012", "KR013"],
        "충청권": ["KR051", "KR052", "KR053", "KR054"],
        "호남권": ["KR041", "KR043"],
        "대경권": ["KR031", "KR032"],
        "동남권": ["KR021", "KR022", "KR023"],
        "강원": ["KR061"],
        "전북": ["KR042"],
        "제주": ["KR071"],
    }
    inds = ["A", "BTE", "F", "GTI", "J", "K", "L", "M_N", "OTQ", "RTU"]
    mrows = rows(root / "figures/matrix_rendered_cells.csv")
    lookup = {(r["superregion"], r["industry_code"]): r for r in mrows}

    def agg(q, key):
        w = [float(r["employment_input_persons"]) for r in q]
        return 100 * math.log(
            sum(x * math.exp(float(r[key]) / 100) for r, x in zip(q, w)) / sum(w)
        )

    def sign(a):
        return (a > 0) - (a < 0)

    computed = []
    matches = 0
    total = 0
    for sr, codes in supers.items():
        for ind in inds:
            q = [
                r
                for r in test
                if r["target_year"] == "2025"
                and r["region_code"] in codes
                and r["industry_code"] == ind
            ]
            avail = {r["region_code"] for r in q}
            cov = (
                "완전" if len(avail) == len(codes) else "부분" if avail else "자료없음"
            )
            delta = (
                agg(q, "ridge_alpha1000") - agg(q, "global_past_mean") if q else None
            )
            cls = (
                "상회"
                if delta is not None and delta > 0.5
                else "하회"
                if delta is not None and delta < -0.5
                else "근접"
                if delta is not None
                else ""
            )
            label = (
                (f"{delta:+.2f}" + ("*" if cov == "부분" else ""))
                if delta is not None
                else "×"
            )
            record = {
                "superregion": sr,
                "industry_code": ind,
                "label": label,
                "class": cls,
                "coverage": cov,
            }
            computed.append(record)
            check(f"matrix_{sr}_{ind}", record, lookup[(sr, ind)])
            for year in ["2020", "2021", "2022"]:
                v = [
                    r
                    for r in val
                    if r["target_year"] == year
                    and r["region_code"] in avail
                    and r["industry_code"] == ind
                ]
                if not avail or {r["region_code"] for r in v} != avail:
                    continue
                b = agg(v, "global_past_mean")
                pred = agg(v, "ridge_alpha1000")
                actual = agg(v, "target_logpoints")
                matches += sign(pred - b) == sign(actual - b)
                total += 1
    check("validation_sign_matches", matches, 91)
    check("validation_total", total, 188)
    classes = dict(Counter(r["class"] for r in computed))
    coverage = dict(Counter(r["coverage"] for r in computed))
    check("matrix_classes", classes, {"하회": 17, "근접": 35, "상회": 13, "": 15})
    check("matrix_coverage", coverage, {"완전": 61, "부분": 4, "자료없음": 15})
    result = {
        "all_passed": all(c["passed"] for c in checks),
        "checks_passed": sum(c["passed"] for c in checks),
        "checks_total": len(checks),
        "figure2": calc,
        "figure3": {
            "classes": classes,
            "coverage": coverage,
            "validation_matches": matches,
            "validation_total": total,
            "validation_pct": 100 * matches / total,
        },
        "sources": [
            str(p.relative_to(root))
            for p in [
                base / "test_predictions.csv",
                base / "validation_predictions.csv",
                cardpath,
                root / "figures/fig3_validation.json",
                root / "figures/matrix_rendered_cells.csv",
            ]
        ],
        "method": "Recomputed 80 region-industry aggregates from preserved test predictions using identical available regions in numerator and denominator; independently recomputed 2020-2022 validation aggregates using the 2025 available-region composition. Contribution terms verified against the source evidence card, not refitted.",
        "checks": checks,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=ROOT / "results/figure_data_check_261028_v3.json"
    )
    args = parser.parse_args(argv)
    try:
        result = audit_figures()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        parser.exit(1, f"Figure verification failed: {exc}\n")
    summary = {
        key: value for key, value in result.items() if key not in {"checks", "sources"}
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failed = [record for record in result["checks"] if not record["passed"]]
    if failed:
        print(json.dumps(failed, ensure_ascii=False, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
