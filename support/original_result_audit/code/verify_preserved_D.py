from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    out = args.output_dir
    raw = pd.read_csv(
        args.package_root / "source_harmonized/kosis_ksic11_H1_2013_2025_panel.csv",
        float_precision="round_trip",
    )
    merged = pd.read_csv(
        out / "source_16_fixed_units.csv", float_precision="round_trip"
    )
    panel = pd.read_csv(
        out / "results/analysis_panel.csv", float_precision="round_trip"
    )
    pred = pd.read_csv(
        out / "results/test_predictions.csv", float_precision="round_trip"
    )
    val = pd.read_csv(
        out / "results/validation_predictions.csv", float_precision="round_trip"
    )
    select = json.loads(
        (out / "results/selection_before_test.json").read_text(encoding="utf-8")
    )
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise AssertionError(name)

    pair = raw[raw.region_code.isin(["KR031", "KR032"])].pivot(
        index=["year", "industry_code"],
        columns="region_code",
        values="employment_persons",
    )
    expect = pair.sum(axis=1, min_count=2)
    actual = (
        merged[merged.region_code == "KR03M"]
        .set_index(["year", "industry_code"])
        .employment_persons
    )
    check(
        "strict_two_region_sum",
        np.allclose(
            expect, actual.reindex(expect.index), equal_nan=True, rtol=0, atol=1e-08
        ),
        f"{len(expect)} source cells; missingness preserved",
    )
    unmerged = (
        raw[~raw.region_code.isin(["KR031", "KR032"])]
        .set_index(["region_code", "year", "industry_code"])
        .employment_persons
    )
    retained = (
        merged[merged.region_code != "KR03M"]
        .set_index(["region_code", "year", "industry_code"])
        .employment_persons
    )
    check(
        "other_regions_unchanged",
        np.allclose(
            unmerged, retained.reindex(unmerged.index), equal_nan=True, rtol=0, atol=0
        ),
        f"{len(unmerged)} source cells",
    )
    wide = merged.pivot(
        index=["year", "industry_code"],
        columns="region_code",
        values="employment_persons",
    )
    feature_errors = {
        v: []
        for v in [
            "target_logpoints",
            "log_employment",
            "industry_share_pct",
            "own_growth",
            "own_growth_lag1",
            "peer_industry_growth",
            "region_total_growth",
        ]
    }
    for row in panel.itertuples():
        y, r, i = (row.target_year, row.region_code, row.industry_code)
        levels = [wide.at[(k, i), r] for k in [y, y - 1, y - 2, y - 3]]
        totals = [wide.at[(k, "_T"), r] for k in [y - 1, y - 2]]
        recent = wide.loc[y - 1, i]
        previous = wide.loc[y - 2, i]
        eligible = (recent > 0) & (previous > 0)
        eligible.loc[r] = False
        if y - 1 == 2017:
            eligible.loc["KR053"] = False
        independent = {
            "target_logpoints": 100 * np.log(levels[0] / levels[1]),
            "log_employment": np.log(levels[1]),
            "industry_share_pct": 100 * levels[1] / totals[0],
            "own_growth": 100 * np.log(levels[1] / levels[2]),
            "own_growth_lag1": 100 * np.log(levels[2] / levels[3]),
            "peer_industry_growth": 100
            * np.log(recent[eligible].sum() / previous[eligible].sum()),
            "region_total_growth": 100 * np.log(totals[0] / totals[1]),
        }
        for key, value in independent.items():
            feature_errors[key].append(abs(getattr(row, key) - value))
    for key, errors in feature_errors.items():
        check(
            "independent_" + key,
            max(errors) < 1e-10,
            {"n": len(errors), "maximum_absolute_error": max(errors)},
        )
    check(
        "chungnam_boundary_gate_preserved",
        not (
            (panel.region_code == "KR053") & panel.target_year.isin([2017, 2018, 2019])
        ).any(),
        "2017 transition and lag-affected rows excluded",
    )
    check(
        "merged_outer_boundary_not_filtered",
        len(
            panel[(panel.region_code == "KR03M") & panel.target_year.isin([2024, 2025])]
        )
        == 18,
        "9 valid industries per year retained",
    )
    grid = pd.read_csv(out / "results/validation_grid.csv")
    best_base = (
        grid[grid.family == "baseline"]
        .sort_values("mae", kind="stable")
        .iloc[0]
        .candidate
    )
    best_ridge = (
        grid[grid.family == "ridge"].sort_values("mae", kind="stable").iloc[0].candidate
    )
    check(
        "validation_only_selection_matches_grid",
        best_base == select["service_default_baseline"]
        and best_ridge == select["family_selected"]["ridge"],
        {"baseline": best_base, "ridge": best_ridge},
    )
    inputs = [
        "log_employment",
        "industry_share_pct",
        "own_growth",
        "own_growth_lag1",
        "peer_industry_growth",
        "region_total_growth",
        "region_code",
        "industry_code",
    ]
    model = joblib.load(out / f"results/model_{best_ridge}.joblib")
    replay = model.predict(pred[inputs])
    check(
        "saved_ridge_replay",
        np.allclose(replay, pred[best_ridge], rtol=0, atol=1e-12),
        {
            "n": len(pred),
            "maximum_absolute_error": float(np.max(np.abs(replay - pred[best_ridge]))),
        },
    )
    tv = panel[panel.split.isin(["train", "validation"])]
    check(
        "refitted_global_mean_baseline",
        np.allclose(pred[best_base], tv.target_logpoints.mean(), rtol=0, atol=1e-12),
        {"refitted_value": float(tv.target_logpoints.mean())},
    )
    train = panel[panel.split == "train"]
    check(
        "validation_baseline_uses_training_only",
        np.allclose(val[best_base], train.target_logpoints.mean(), rtol=0, atol=1e-12),
        {"training_value": float(train.target_logpoints.mean())},
    )
    service = pd.read_csv(out / "daegyeong_service_2025.csv")
    present = service[service.prediction_n == 1]
    absent = service[service.prediction_n == 0]
    check(
        "nine_available_one_missing",
        len(present) == 9 and list(absent.industry_code) == ["BTE"],
        {"available": 9, "unavailable": ["BTE"]},
    )
    check(
        "service_deviation_matches",
        np.allclose(
            present.model_deviation,
            present.ridge_prediction - present.baseline_prediction,
            rtol=0,
            atol=1e-12,
        ),
        "All 9 eligible service cells",
    )
    summary = json.loads(
        (out / "summary_for_manuscript.json").read_text(encoding="utf-8")
    )
    for model_name in [best_base, best_ridge]:
        reported = next(
            (
                v["mae"]
                for v in summary["all_unit_pooled_metrics"]
                if v["model"] == model_name
            )
        )
        value = np.abs(pred.target_logpoints - pred[model_name]).mean()
        check(
            "pooled_mae_" + model_name,
            abs(reported - value) < 1e-12,
            {"independently_calculated": float(value)},
        )
    report = {
        "checks": checks,
        "passed": len(checks),
        "total": len(checks),
        "scope": "Arithmetic, unchanged-source, reconstructed-feature, saved-model replay and selection verification; not field validity evaluation.",
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"passed": len(checks), "total": len(checks)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
