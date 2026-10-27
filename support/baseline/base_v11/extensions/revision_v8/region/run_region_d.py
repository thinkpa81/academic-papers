from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

PAIR = ["KR031", "KR032"]
MERGED = "KR03M"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(value, path):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def strict_merge(source):
    pair = source[source.region_code.isin(PAIR)].copy()
    if pair.duplicated(["region_code", "year", "industry_code"]).any():
        raise ValueError("Duplicate source rows")
    rows = []
    audit = []
    for (year, industry), group in pair.groupby(["year", "industry_code"], sort=True):
        available = set(group.region_code) == set(PAIR)
        complete = (
            available
            and group.employment_persons.notna().all()
            and group.complete_components.eq(True).all()
        )
        row = group.iloc[0].to_dict()
        row.update(
            region_code=MERGED,
            region_name_ko="대경권(대구+경북 고정 합산)",
            employment_persons=float(group.employment_persons.sum())
            if complete
            else np.nan,
            complete_components=bool(complete),
            missing_components=";".join(
                (
                    f"{v.region_code}:{v.missing_components}"
                    for v in group.itertuples()
                    if pd.isna(v.employment_persons)
                )
            ),
            source_raw_values=";".join(
                (f"{v.region_code}={v.source_raw_values}" for v in group.itertuples())
            ),
            rse_any_star=bool(group.rse_any_star.eq(True).any()),
            source_rse_flags=";".join(
                (f"{v.region_code}={v.source_rse_flags}" for v in group.itertuples())
            ),
            display_rounding_halfwidth_persons=float(
                group.display_rounding_halfwidth_persons.sum()
            )
            if complete
            else np.nan,
        )
        rows.append(row)
        audit.append(
            {
                "year": int(year),
                "industry_code": industry,
                "n_source_regions": len(group),
                "all_components_numeric": bool(complete),
                "daegu_persons": None
                if pd.isna(
                    group.set_index("region_code").employment_persons.get(PAIR[0])
                )
                else float(
                    group.set_index("region_code").employment_persons.get(PAIR[0])
                ),
                "gyeongbuk_persons": None
                if pd.isna(
                    group.set_index("region_code").employment_persons.get(PAIR[1])
                )
                else float(
                    group.set_index("region_code").employment_persons.get(PAIR[1])
                ),
                "merged_persons": float(row["employment_persons"])
                if complete
                else None,
            }
        )
    merged = pd.concat(
        [source[~source.region_code.isin(PAIR)], pd.DataFrame(rows)], ignore_index=True
    )
    return (
        merged.sort_values(["region_code", "year", "industry_code"]).reset_index(
            drop=True
        ),
        pd.DataFrame(audit),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    root = args.package_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    source_path = root / "source_harmonized/kosis_ksic11_H1_2013_2025_panel.csv"
    method_path = root / "analysis_harmonized/run.py"
    source = pd.read_csv(source_path, float_precision="round_trip")
    protocol = {
        "analysis_id": "D_fixed_daegyeong_posthoc",
        "status": "post hoc sensitivity design; not preregistered; finalized before this run",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "motivation": "Review suggestion to recover the within-region administrative transfer via fixed aggregate geography",
        "source_sha256": sha(source_path),
        "reused_method_sha256": sha(method_path),
        "analysis_units": "15 unchanged provincial units plus Daegu+Gyeongbuk fixed aggregate = 16",
        "aggregation_stage": "sum observed industry employment and official totals before growth/lag/peer feature construction",
        "missing_rule": "both constituent regional broad-industry values must be numeric and component-complete; no zero imputation",
        "boundary_filter": {"KR053": [2017]},
        "boundary_interpretation": "Gunwi transfer changes the internal Daegu/Gyeongbuk border, not their combined outer boundary; survey, sample and classification changes remain separate limitations",
        "sejong_chungnam_not_merged": True,
        "train_years": [2016, 2017, 2018, 2019],
        "validation_years": [2020, 2021, 2022],
        "test_years": [2023, 2024, 2025],
        "feature_schema": "same six numerical features and two categorical features as analysis A; all recalculated after geographical merge",
        "selection_rule": "same candidate grid as A; unweighted validation MAE; best baseline is display default; best ridge is ridge comparator",
        "test_refit": "refit selected candidates on training+validation; retain fixed coefficients throughout 2023–2025 evaluation",
        "card_and_matrix_policy": "D is reported separately and never inserted into A as though its analysis unit/model were identical",
        "deviation_signal": "ridge prediction minus validation-selected baseline; labels lower/near/higher with ±0.5 logpoint band",
        "prior_validation_direction": "same-year sign of ridge minus baseline vs actual minus baseline; zeros remain zero; report count and only pooled proportion",
        "evaluation_status": "current-vintage retrospective evaluation, not historical information-set forecasting",
        "no_model_or_threshold_tuning_after_test": True,
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
    }
    dump(protocol, out / "protocol_before_execution.json")
    merged, audit = strict_merge(source)
    merged_path = out / "source_16_fixed_units.csv"
    merged.to_csv(merged_path, index=False, encoding="utf-8-sig")
    audit.to_csv(out / "merge_source_audit.csv", index=False, encoding="utf-8-sig")
    valid = audit.dropna(subset=["merged_persons"])
    invariance = np.allclose(
        valid.daegu_persons + valid.gyeongbuk_persons,
        valid.merged_persons,
        rtol=0,
        atol=1e-08,
    )
    redistribution = np.allclose(
        valid.daegu_persons + 100 + (valid.gyeongbuk_persons - 100),
        valid.merged_persons,
        rtol=0,
        atol=1e-08,
    )
    if not invariance or not redistribution:
        raise AssertionError("Internal geographic sum invariance failed")
    spec = importlib.util.spec_from_file_location("harmonized_method", method_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REGIONS = {
        key: value for key, value in module.REGIONS.items() if key not in PAIR
    }
    module.REGIONS[MERGED] = "대경권(대구+경북 고정 합산)"
    module.SUPERREGION = {
        key: value for key, value in module.SUPERREGION.items() if key not in PAIR
    }
    module.SUPERREGION[MERGED] = "대경권"
    module.BOUNDARIES = {"KR053": [2017]}
    original_metrics = module.metrics

    def qualified_metrics(y, prediction, weights):
        values = original_metrics(y, prediction, weights)
        values["direction_sign_threeway_zero_band_pct"] = values.pop(
            "direction_threeway_pct"
        )
        return values

    module.metrics = qualified_metrics
    original_dump = module.dump

    def enriched_dump(value, path):
        if isinstance(value, dict) and Path(path).name in [
            "selection_before_test.json",
            "summary.json",
        ]:
            value = {
                **value,
                "analysis_id": protocol["analysis_id"],
                "posthoc_protocol_sha256": sha(out / "protocol_before_execution.json"),
                "regional_aggregation_before_feature_construction": True,
                "analysis_unit_count": 16,
            }
        original_dump(value, path)

    module.dump = enriched_dump
    panel, tp, selection = module.run_cohort(
        merged, out / "results", True, sha(merged_path)
    )
    ridge = selection["family_selected"]["ridge"]
    baseline = selection["service_default_baseline"]
    vp = pd.read_csv(
        out / "results/validation_predictions.csv", float_precision="round_trip"
    )
    panel_2025 = tp[(tp.region_code == MERGED) & (tp.target_year == 2025)].copy()
    val = vp[vp.region_code == MERGED].copy()
    val["model_deviation"] = val[ridge] - val[baseline]
    val["actual_deviation"] = val.target_logpoints - val[baseline]
    val["direction_match"] = np.sign(val.model_deviation) == np.sign(
        val.actual_deviation
    )
    val["ridge_absolute_error"] = np.abs(val.target_logpoints - val[ridge])
    val["baseline_absolute_error"] = np.abs(val.target_logpoints - val[baseline])
    val.to_csv(
        out / "daegyeong_prior_validation_rows.csv", index=False, encoding="utf-8-sig"
    )
    service = []
    for industry in module.INDUSTRIES:
        testrow = panel_2025[panel_2025.industry_code == industry]
        vr = val[val.industry_code == industry]
        entry = {
            "analysis": "D",
            "analysis_unit": MERGED,
            "industry_code": industry,
            "test_year": 2025,
            "validation_n": int(len(vr)),
            "validation_correct_n": int(vr.direction_match.sum()),
            "validation_baseline_mae": float(vr.baseline_absolute_error.mean())
            if len(vr)
            else None,
            "validation_ridge_mae": float(vr.ridge_absolute_error.mean())
            if len(vr)
            else None,
            "baseline_model": baseline,
            "ridge_model": ridge,
            "availability": "complete_two_region_aggregate"
            if len(testrow)
            else "not_available_due_to_missing_source",
            "expected_source_regions": 2,
            "prediction_n": int(len(testrow)),
        }
        if len(testrow):
            row = testrow.iloc[0]
            delta = float(row[ridge] - row[baseline])
            entry.update(
                input_employment_persons=float(row.employment_input_persons),
                target_employment_persons=float(row.employment_target_persons),
                baseline_prediction=float(row[baseline]),
                ridge_prediction=float(row[ridge]),
                model_deviation=delta,
                deviation_category="하회"
                if delta < -0.5
                else "상회"
                if delta > 0.5
                else "근접",
                actual_logpoints=float(row.target_logpoints),
            )
        service.append(entry)
    pd.DataFrame(service).to_csv(
        out / "daegyeong_service_2025.csv", index=False, encoding="utf-8-sig"
    )
    metrics = pd.read_csv(
        out / "results/test_metrics.csv", float_precision="round_trip"
    )
    local_metrics = []
    for year in ["pooled", 2023, 2024, 2025]:
        df = tp[tp.region_code == MERGED]
        if year != "pooled":
            df = df[df.target_year == year]
        for model in [baseline, ridge]:
            local_metrics.append(
                {
                    "period": str(year),
                    "model": model,
                    **module.metrics(
                        df.target_logpoints, df[model], df.employment_input_persons
                    ),
                }
            )
    pd.DataFrame(local_metrics).to_csv(
        out / "daegyeong_test_metrics.csv", index=False, encoding="utf-8-sig"
    )
    boot = pd.read_csv(out / "results/region_bootstrap_vs_default.csv")
    subset_metrics = metrics[
        metrics.model.isin([baseline, ridge]) & (metrics.period == "pooled")
    ]
    summary = {
        "analysis_id": protocol["analysis_id"],
        "unit_count": 16,
        "source_rows": len(merged),
        "merge_rows": len(audit),
        "valid_merge_rows": len(valid),
        "sum_invariance_passed": bool(invariance),
        "internal_redistribution_invariance_passed": bool(redistribution),
        "cohort_counts": selection["counts"],
        "test_year_counts": {
            str(k): int(v) for k, v in tp.groupby("target_year").size().items()
        },
        "baseline": baseline,
        "ridge": ridge,
        "learned_companion": selection["learned_companion"],
        "all_unit_pooled_metrics": subset_metrics.to_dict(orient="records"),
        "all_unit_ridge_bootstrap_vs_baseline": boot[boot.model == ridge].to_dict(
            orient="records"
        ),
        "daegyeong_test_year_counts": {
            str(k): int(v)
            for k, v in tp[tp.region_code == MERGED]
            .groupby("target_year")
            .size()
            .items()
        },
        "daegyeong_2025_available_industries": list(panel_2025.industry_code),
        "daegyeong_2025_missing_industries": [
            i for i in module.INDUSTRIES if i not in set(panel_2025.industry_code)
        ],
        "daegyeong_validation_direction_correct": int(val.direction_match.sum()),
        "daegyeong_validation_direction_total": len(val),
        "daegyeong_validation_direction_proportion": float(val.direction_match.mean()),
        "daegyeong_test_metrics": local_metrics,
        "interpretation": "D demonstrates reconstructible fixed aggregate coverage. Different unit composition, weights, features, fitted models and selected baseline mean its scores cannot be read as the causal effect of fixing boundaries or directly substituted into A.",
        "remaining_limits": [
            "classification backcast/direct collection boundary remains",
            "survey errors need not cancel by geographic aggregation",
            "current vintage only",
            "BTE source suppression/missingness retained",
            "validation direction count is not independent Bernoulli evidence",
        ],
        "selection_sha256": sha(out / "results/selection_before_test.json"),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump(summary, out / "summary_for_manuscript.json")
    manifest = [
        {
            "path": str(path.relative_to(out)),
            "sha256": sha(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(out.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    ]
    dump(manifest, out / "manifest.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
