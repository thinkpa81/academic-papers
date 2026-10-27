#!/usr/bin/env python3
"""Replay preserved B/C/D verifiers and directly check current tables 8 and 12.
No candidate search or forest/boosting refit is performed.
"""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent


def read(p):
    return pd.read_csv(p, float_precision="round_trip")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(x, p):
    p.write_text(
        json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def metric(d, y, p, w):
    errors = [abs(a - b) for a, b in zip(d[y], d[p])]
    return {
        "n": len(d),
        "MAE": math.fsum(errors) / len(d),
        "RMSE": math.sqrt(math.fsum(e * e for e in errors) / len(d)),
        "weighted_MAE": math.fsum(e * wt for e, wt in zip(errors, d[w]))
        / math.fsum(d[w]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, default=HERE / "bundled_inputs")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    base = a.base.resolve()
    out = a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Use a new empty output folder")
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((HERE / "input_manifest.json").read_text())
    for row in manifest:
        assert sha(base / row["path"]) == row["sha256"], row["path"]
    D = base / "extensions/revision_v8/region/output"
    commands = [
        (
            "B",
            [
                "verify_preserved_B.py",
                "--package-root",
                base,
                "--output",
                out / "preserved_B_audit.json",
            ],
        ),
        (
            "C",
            [
                "verify_preserved_C.py",
                "--working-root",
                base / "extensions/temporal2024",
                "--output-root",
                out / "preserved_C",
            ],
        ),
        (
            "D",
            [
                "verify_preserved_D.py",
                "--package-root",
                base,
                "--output-dir",
                D,
                "--report",
                out / "preserved_D_audit.json",
            ],
        ),
    ]
    for label, cmd in commands:
        with (out / f"preserved_{label}.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [sys.executable, str(HERE / "code" / cmd[0])] + list(map(str, cmd[1:])),
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={
                    **os.environ,
                    "OPENBLAS_NUM_THREADS": "1",
                    "OMP_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                },
            )
    checks = []

    def check(label, passed, detail):
        checks.append({"check": label, "passed": bool(passed), "detail": detail})
        assert passed, label

    B = read(base / "original/analysis/main/test_predictions.csv")
    C = read(
        base
        / "extensions/temporal2024/analysis/evaluation_2024_official/locked_future_predictions_and_outcomes.csv"
    )
    table8 = []
    expected = [
        ["8.63", "15.07", "4.72"],
        ["8.28", "14.79", "4.58"],
        ["8.21", "13.84", "4.61"],
        ["7.96", "14.26", "4.64"],
    ]
    for analysis, d, y in [("B", B, "target"), ("C", C, "target_logpoints")]:
        for model in ["zero", "ridge"]:
            values = metric(d, y, "pred_" + model, "origin_employment_weight")
            display = [f"{values[m]:.2f}" for m in ["MAE", "RMSE", "weighted_MAE"]]
            table8.append(
                {"analysis": analysis, "model": model, **values, "display": display}
            )
            check(
                f"table8_{analysis}_{model}",
                display == expected[len(table8) - 1],
                {"actual": display, "manuscript": expected[len(table8) - 1]},
            )
    dp = read(D / "results/test_predictions.csv")
    dv = read(D / "results/validation_predictions.csv")
    ds = read(D / "daegyeong_service_2025.csv")
    panel = read(D / "results/analysis_panel.csv")
    check(
        "D_split_counts",
        panel.groupby("split").size().to_dict()
        == {"train": 518, "validation": 433, "test": 436},
        panel.groupby("split").size().to_dict(),
    )
    dmetrics = [
        {"model": m, **metric(dp, "target_logpoints", m, "employment_input_persons")}
        for m in ["global_past_mean", "ridge_alpha100"]
    ]
    check(
        "D_pooled_MAE_rounding",
        [f"{r['MAE']:.2f}" for r in dmetrics] == ["9.24", "9.09"],
        dmetrics,
    )
    errors = np.abs(dp.target_logpoints - dp.ridge_alpha100) - np.abs(
        dp.target_logpoints - dp.global_past_mean
    )
    regs = sorted(dp.region_code.unique())
    sums = np.array([errors[dp.region_code == r].sum() for r in regs])
    ns = np.array([(dp.region_code == r).sum() for r in regs])
    draws = np.random.default_rng(20260926).integers(0, len(regs), (2000, len(regs)))
    boots = sums[draws].sum(axis=1) / ns[draws].sum(axis=1)
    ci = [float(errors.mean()), *map(float, np.quantile(boots, [0.025, 0.975]))]
    check(
        "D_cluster_ci_display", [f"{v:.3f}" for v in ci[1:]] == ["-0.368", "0.064"], ci
    )
    expected12 = {
        "A": ["-1.77", "-2.53", "하회", 3],
        "BTE": ["—", "—", "자료 부족", 0],
        "F": ["-0.36", "-1.12", "하회", 3],
        "GTI": ["-1.05", "-1.81", "하회", 3],
        "J": ["-2.89", "-3.65", "하회", 3],
        "K": ["-1.80", "-2.56", "하회", 3],
        "L": ["4.49", "3.73", "상회", 3],
        "M_N": ["2.05", "1.28", "상회", 3],
        "OTQ": ["1.61", "0.85", "상회", 3],
        "RTU": ["-0.72", "-1.49", "하회", 3],
    }
    table12 = []
    validation_details = []
    for industry, exp in expected12.items():
        s = ds[ds.industry_code == industry].iloc[0]
        pred = dp[
            (dp.region_code == "KR03M")
            & (dp.target_year == 2025)
            & (dp.industry_code == industry)
        ]
        if pred.empty:
            vals = ["—", "—", "자료 부족", 0]
            check(
                f"table12_{industry}_absence",
                int(s.prediction_n) == 0 and int(s.validation_n) == 0,
                "No test prediction and no displayed validation evidence",
            )
        else:
            assert len(pred) == 1
            r = pred.iloc[0]
            dev = float(r.ridge_alpha100 - r.global_past_mean)
            val = dv[(dv.region_code == "KR03M") & (dv.industry_code == industry)]
            correct = int(
                (
                    (np.sign(val.ridge_alpha100 - val.global_past_mean))
                    == (np.sign(val.target_logpoints - val.global_past_mean))
                ).sum()
            )
            cat = "하회" if dev < -0.5 else "상회" if dev > 0.5 else "근접"
            vals = [f"{r.ridge_alpha100:.2f}", f"{dev:.2f}", cat, len(val)]
            check(
                f"table12_{industry}_saved_exact",
                abs(float(s.ridge_prediction) - float(r.ridge_alpha100)) < 1e-12
                and abs(float(s.model_deviation) - dev) < 1e-12
                and int(s.validation_n) == len(val)
                and int(s.validation_correct_n) == correct,
                {
                    "ridge_prediction": float(r.ridge_alpha100),
                    "baseline_prediction": float(r.global_past_mean),
                    "deviation": dev,
                    "validation_n": len(val),
                    "correct": correct,
                },
            )
            validation_details.append(
                {"industry": industry, "n": len(val), "correct": correct}
            )
        check(
            f"table12_{industry}_display",
            vals == exp,
            {"actual": vals, "manuscript": exp},
        )
        table12.append({"industry": industry, "display": vals})
    check(
        "D_validation_15_of_27",
        sum(v["n"] for v in validation_details) == 27
        and sum(v["correct"] for v in validation_details) == 15,
        validation_details,
    )
    source = read(base / "source_harmonized/kosis_ksic11_H1_2013_2025_panel.csv")
    missing = source[
        (source.region_code == "KR031")
        & (source.industry_code == "BTE")
        & (source.year.isin([2023, 2024, 2025]))
    ]
    check(
        "D_BTE_missing_source",
        missing.employment_persons.isna().all()
        and set(missing.missing_components) == {"B"},
        missing[["year", "missing_components"]].to_dict("records"),
    )
    report = {
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Preserved B/C/D source, feature, arithmetic and saved-model replay; direct current table8/table12 display comparison. No new candidate search and no claim of newly repeated 157 full-refit checks.",
        "table8": table8,
        "D_pooled": dmetrics,
        "D_cluster_bootstrap": {
            "seed": 20260926,
            "B": 2000,
            "regions": len(regs),
            "delta_lower_upper": ci,
        },
        "table12": table12,
        "checks": checks,
        "passed": len(checks),
        "total": len(checks),
    }
    write(report, out / "current_tables_8_12_audit.json")
    pd.DataFrame(
        [{k: v for k, v in r.items() if k != "display"} for r in table8]
    ).to_csv(out / "table8_recalculated.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "industry": r["industry"],
                **dict(
                    zip(
                        [
                            "ridge_display",
                            "deviation_display",
                            "category",
                            "validation_n",
                        ],
                        r["display"],
                    )
                ),
            }
            for r in table12
        ]
    ).to_csv(out / "table12_display_check.csv", index=False, encoding="utf-8-sig")
    print(
        json.dumps(
            {
                "status": "PASS",
                "direct_checks": len(checks),
                "table8": table8,
                "D_cluster_ci": ci,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
