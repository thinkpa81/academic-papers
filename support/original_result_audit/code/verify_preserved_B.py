if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import csv
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = None
parser = argparse.ArgumentParser()
parser.add_argument("--package-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
ROOT = args.package_root.resolve() / "original/analysis"
SOURCE = ROOT.parent / "raw"
raw = list(
    csv.DictReader(
        (SOURCE / "economic/oecd_korea_regional_industry_raw.csv").open(
            encoding="utf-8-sig"
        )
    )
)
employment = {
    (r["REF_AREA"], r["ACTIVITY"], int(r["TIME_PERIOD"])): float(r["OBS_VALUE"])
    for r in raw
    if r["UNIT_MEASURE"] == "PS" and r["MEASURE"] == "EMP" and r["OBS_VALUE"]
}
shares = {
    (r["REF_AREA"], r["ACTIVITY"], int(r["TIME_PERIOD"])): float(r["OBS_VALUE"])
    for r in raw
    if r["UNIT_MEASURE"] == "PT_EMP" and r["MEASURE"] == "EMP" and r["OBS_VALUE"]
}
region_codes = sorted({r["REF_AREA"] for r in raw})
panel = pd.read_csv(ROOT / "analysis_panel_main.csv")
feature_errors = []
for row in panel.to_dict("records"):
    reg, act, year = (row["region_code"], row["industry_code"], int(row["origin_year"]))
    e = [employment[reg, act, year + k] for k in [-2, -1, 0, 1]]
    assert min(e) > 0
    shared = [
        r
        for r in region_codes
        if r != reg
        and employment.get((r, act, year), 0) > 0
        and (employment.get((r, act, year - 1), 0) > 0)
    ]
    previous = sum((employment[r, act, year - 1] for r in shared))
    current = sum((employment[r, act, year] for r in shared))
    expected = {
        "target": 100 * math.log(e[3] / e[2]),
        "log_employment": math.log(e[2]),
        "growth_t": 100 * math.log(e[2] / e[1]),
        "growth_tm1": 100 * math.log(e[1] / e[0]),
        "industry_share_pct": shares[reg, act, year],
        "origin_employment_weight": e[2],
        "other_regions_count": len(shared),
        "other_regions_industry_growth": 100 * math.log(current / previous),
        "region_total_growth": 100
        * math.log(employment[reg, "_T", year] / employment[reg, "_T", year - 1]),
    }
    for column, value in expected.items():
        if not math.isclose(row[column], value, rel_tol=1e-12, abs_tol=1e-10):
            feature_errors.append([reg, act, year, column, row[column], value])
results = {
    "source_feature_rows_checked": len(panel),
    "source_feature_checks_per_row": 9,
    "source_feature_errors": feature_errors,
    "partition_counts": panel.groupby("partition").size().to_dict(),
}
NUM = [
    "log_employment",
    "industry_share_pct",
    "growth_t",
    "growth_tm1",
    "other_regions_industry_growth",
    "region_total_growth",
    "unemployment_rate_pct",
    "participation_rate_pct",
]
FEATURES = NUM + ["region_code", "industry_code"]
for experiment in ["main", "delayed_features"]:
    folder = ROOT / experiment
    predictions = pd.read_csv(folder / "test_predictions.csv")
    metrics = pd.read_csv(folder / "test_metrics.csv").set_index("model")
    differences = {}
    for model in metrics.index:
        truth = predictions.target.to_numpy()
        pred = predictions["pred_" + model].to_numpy()
        abs_error = np.abs(truth - pred)
        computed = {
            "MAE": sum(abs_error) / len(abs_error),
            "RMSE": math.sqrt(sum((truth - pred) ** 2) / len(truth)),
            "direction_accuracy": sum((truth < 0) == (pred < 0)) / len(truth),
            "origin_employment_weighted_MAE": sum(
                abs_error * predictions.origin_employment_weight
            )
            / sum(predictions.origin_employment_weight),
        }
        differences[model] = {
            k: float(v - metrics.loc[model, k]) for k, v in computed.items()
        }
        assert max((abs(v) for v in differences[model].values())) < 1e-10
    selection = json.loads(
        (folder / "selection_before_test.json").read_text(encoding="utf-8")
    )
    selected_ai = selection["selected_AI"]
    selected_baseline = selection["selected_baseline"]
    labels = predictions.region_code.to_numpy()
    unique = np.unique(labels)
    mae_deltas = np.abs(
        predictions.target - predictions["pred_" + selected_ai]
    ) - np.abs(predictions.target - predictions["pred_" + selected_baseline])
    rng = np.random.default_rng(20260918)
    sample_draws = rng.integers(0, len(unique), size=(2000, len(unique)))
    bootstrap = []
    for draw in sample_draws:
        sampled = np.concatenate([np.flatnonzero(labels == unique[i]) for i in draw])
        bootstrap.append(float(np.mean(mae_deltas.iloc[sampled])))
    calculated_ci = [
        float(np.mean(mae_deltas)),
        *np.quantile(bootstrap, [0.025, 0.975]).tolist(),
    ]
    saved_ci = json.loads(
        (folder / "bootstrap_intervals.json").read_text(encoding="utf-8")
    )["selected_AI_vs_selected_baseline"]
    assert np.allclose(
        calculated_ci,
        [saved_ci["delta_MAE"], saved_ci["lower95"], saved_ci["upper95"]],
        atol=1e-12,
    )
    model = joblib.load(folder / ("model_" + selected_ai + ".joblib"))
    reproduced = model.predict(predictions[FEATURES])
    max_prediction_difference = float(
        np.max(np.abs(reproduced - predictions["pred_" + selected_ai]))
    )
    assert max_prediction_difference < 1e-10
    train = pd.read_csv(folder / "training_design.csv")
    fitted_scaler = model.named_steps["preprocess"].named_transformers_["numeric"]
    scaling_mean_diff = float(
        np.max(np.abs(fitted_scaler.mean_ - train[NUM].mean().to_numpy()))
    )
    assert scaling_mean_diff < 1e-10
    assert int(train.target_year.max()) == 2020
    results[experiment] = {
        "test_rows": len(predictions),
        "metric_differences": differences,
        "bootstrap_ci_delta_lower_upper": calculated_ci,
        "saved_model_prediction_max_difference": max_prediction_difference,
        "training_only_scaler_mean_max_difference": scaling_mean_diff,
        "training_max_target_year": int(train.target_year.max()),
    }
delayed = pd.read_csv(ROOT / "analysis_panel_delayed.csv")
full = pd.read_csv(ROOT / "panel_all_rows_with_flags.csv")
delayed_errors = []
feature_lookup = full.set_index(["region_code", "industry_code", "origin_year"])
for row in delayed.to_dict("records"):
    source = feature_lookup.loc[
        (row["region_code"], row["industry_code"], row["origin_year"] - 1), NUM
    ]
    if not np.allclose(
        source.astype(float).to_numpy(), [row[c] for c in NUM], atol=1e-10
    ):
        delayed_errors.append(
            [row["region_code"], row["industry_code"], row["origin_year"]]
        )
results["delayed_feature_rows_checked"] = len(delayed)
results["delayed_feature_errors"] = delayed_errors
service_output = ROOT.parent / "service" / "outputs"
if (service_output / "linear_attributions_10_features.csv").exists():
    main_model = joblib.load(ROOT / "main" / "model_ridge.joblib")
    background = pd.read_csv(ROOT / "main" / "training_design.csv")
    test_design = pd.read_csv(ROOT / "main" / "test_design.csv")
    phi = pd.read_csv(service_output / "linear_attributions_10_features.csv")
    coefficient = main_model.named_steps["model"].coef_
    scaler = main_model.named_steps["preprocess"].named_transformers_["numeric"]
    independently_computed = {}
    for j, name in enumerate(NUM):
        slope_original_units = coefficient[j] / scaler.scale_[j]
        independently_computed[name] = slope_original_units * (
            test_design[name].to_numpy() - background[name].mean()
        )
    encoder = main_model.named_steps["preprocess"].named_transformers_["categorical"]
    offset = len(NUM)
    for name, categories in zip(["region_code", "industry_code"], encoder.categories_):
        lookup = dict(zip(categories, coefficient[offset : offset + len(categories)]))
        empirical_reference = sum(
            (
                background[name].value_counts(normalize=True)[c] * lookup[c]
                for c in categories
            )
        )
        independently_computed[name] = (
            test_design[name].map(lookup).to_numpy() - empirical_reference
        )
        offset += len(categories)
    maximum_error = max(
        (
            float(np.max(np.abs(independently_computed[name] - phi["phi_" + name])))
            for name in FEATURES
        )
    )
    assert maximum_error < 1e-10
    results["service_linear_attribution_rows_checked"] = len(phi)
    results["service_linear_attribution_original_feature_count"] = len(FEATURES)
    results["service_linear_attribution_max_difference"] = maximum_error
results["status"] = "PASS" if not feature_errors and (not delayed_errors) else "FAIL"
args.output.write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(results, ensure_ascii=False, indent=2))
