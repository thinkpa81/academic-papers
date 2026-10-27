from __future__ import annotations

if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import hashlib
import itertools
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

SEED = 20260918
INDUSTRIES = ["A", "BTE", "F", "GTI", "J", "K", "L", "M_N", "OTQ", "RTU"]
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
CAT = ["region_code", "industry_code"]
FEATURES = NUM + CAT
parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-root", type=Path, default=Path(__file__).resolve().parents[1] / "raw"
)
parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parent)
args = parser.parse_args()
OUT = args.output_root
OUT.mkdir(parents=True, exist_ok=True)


def write_json(path, obj):

    def fallback(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o).__name__)

    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=fallback),
        encoding="utf-8",
    )


def csv(df, name, folder=OUT):
    df.to_csv(folder / name, index=False, encoding="utf-8-sig")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "status": "Analysis specification recorded before validation/model fitting/test evaluation in this execution; not an external preregistration.",
    "seed": SEED,
    "unit": "region × nonoverlapping broad industry × target year",
    "target": "100 * log(E_(t+1)/E_t), measured in log points, not ordinary percent or percentage points",
    "feature_cutoff": "reference year <= t; publication dates/vintages unavailable, so retrospective chronological evaluation, not real-time deployment validation",
    "features": FEATURES,
    "other_regions_rule": "At each industry and t, sum only regions with strictly positive E_t AND E_(t-1); exclude focal region from both sums.",
    "missing": "No imputation. A valid sample requires positive employment at t+1,t,t-1,t-2 and every numerical predictor observed.",
    "selection": "Each model family's hyperparameters selected by pooled validation MAE. Lowest validation MAE selects AI family and separately baseline. Tie broken in listed order.",
    "train_target_years": [2011, 2017],
    "validation_target_years": [2018, 2020],
    "test_target_years": [2021, 2023],
    "baselines": ["zero", "persistence", "industry_mean"],
    "ridge": {"alpha": [1, 10, 100]},
    "random_forest": {
        "n_estimators": 300,
        "max_depth": [4, 8],
        "min_samples_leaf": [10, 25],
    },
    "hist_gradient_boosting": {
        "max_iter": 200,
        "learning_rate": 0.05,
        "max_leaf_nodes": [7, 15],
        "l2_regularization": [1, 10],
        "min_samples_leaf": 20,
    },
    "refit": "After selection, each chosen family and historical baseline refitted once on train+validation. Test predictions frozen.",
    "metrics": [
        "MAE",
        "RMSE",
        "direction_accuracy_negative_vs_nonnegative",
        "R2",
        "mean_prediction",
        "mean_actual",
        "origin_employment_weighted_MAE",
        "region_macro_MAE",
        "industry_macro_MAE",
    ],
    "interval": "Paired region-block bootstrap, 17 regions with replacement, 2000 draws, same draw for both model predictions, percentile 95% interval for test ΔMAE. No model refitting; conditional on fitted models and test years; common year/industry dependence not fully represented.",
    "sensitivity": [
        "annual rolling refit with locked family/hyperparameters, target years 2021-2023",
        "all eight numerical features delayed one further reference year; full same validation grid rerun and test evaluated once",
        "evaluate frozen main test predictions excluding Sejong",
        "evaluate frozen main test predictions excluding target year 2021",
        "evaluate frozen main test predictions excluding industry A",
    ],
    "interpretability": "Raw-column permutation importance of validation-selected AI, test MAE increase, 30 repeats; do not optimise model from test importance; correlated panel predictors and noncausal interpretation.",
    "outliers": "Keep all valid source observations, including large Incheon agriculture changes; no response-driven deletion.",
}
write_json(OUT / "analysis_plan.json", plan)
industry_path = args.input_root / "economic/oecd_korea_regional_industry_raw.csv"
labour_path = args.input_root / "oecd_korea_regional_labour_raw.csv"
regions = pd.read_csv(args.input_root / "korea_region_codes.csv")
ind = pd.read_csv(industry_path)
lab = pd.read_csv(labour_path)
ikey = [
    "FREQ",
    "TERRITORIAL_LEVEL",
    "REF_AREA",
    "TERRITORIAL_TYPE",
    "MEASURE",
    "ACTIVITY",
    "PRICES",
    "UNIT_MEASURE",
    "TIME_PERIOD",
]
lkey = [
    "FREQ",
    "TERRITORIAL_LEVEL",
    "REF_AREA",
    "TERRITORIAL_TYPE",
    "MEASURE",
    "AGE",
    "SEX",
    "UNIT_MEASURE",
    "TIME_PERIOD",
]
assert not ind.duplicated(ikey).any()
assert not lab.duplicated(lkey).any()
for df in (ind, lab):
    assert df.FREQ.eq("A").all() and df.TERRITORIAL_LEVEL.eq("TL3").all()
    assert df.UNIT_MULT.eq(0).all()
    assert set(df.REF_AREA) == set(regions.region_code)
base = ind.loc[
    ind.MEASURE.eq("EMP")
    & ind.ACTIVITY.isin(INDUSTRIES)
    & ind.UNIT_MEASURE.isin(["PS", "PT_EMP"])
].copy()
wide = base.pivot(
    index=["REF_AREA", "ACTIVITY", "TIME_PERIOD"],
    columns="UNIT_MEASURE",
    values="OBS_VALUE",
).reset_index()
wide = wide.rename(
    columns={
        "REF_AREA": "region_code",
        "ACTIVITY": "industry_code",
        "TIME_PERIOD": "year",
        "PS": "employment",
        "PT_EMP": "industry_share_pct",
    }
)
grid = pd.MultiIndex.from_product(
    [regions.region_code, INDUSTRIES, range(2008, 2024)],
    names=["region_code", "industry_code", "year"],
).to_frame(index=False)
wide = grid.merge(wide, how="left", validate="one_to_one")
wide["suspect_sejong_zero"] = (
    wide.region_code.eq("KR054")
    & wide.year.between(2013, 2016)
    & wide.employment.eq(0)
    & wide.industry_share_pct.isna()
)
assert wide.suspect_sejong_zero.sum() == 40
csv(wide.loc[wide.suspect_sejong_zero], "excluded_sejong_zero_source_rows.csv")
wide["employment_valid"] = wide.employment.where(
    wide.employment.gt(0) & ~wide.suspect_sejong_zero
)
wide = wide.sort_values(["region_code", "industry_code", "year"])
group = wide.groupby(["region_code", "industry_code"], sort=False)
wide["employment_tm1"] = group.employment_valid.shift(1)
wide["employment_tm2"] = group.employment_valid.shift(2)
wide["employment_tp1"] = group.employment_valid.shift(-1)
wide["log_employment"] = np.log(wide.employment_valid)
wide["growth_t"] = 100 * np.log(wide.employment_valid / wide.employment_tm1)
wide["growth_tm1"] = 100 * np.log(wide.employment_tm1 / wide.employment_tm2)
wide["target"] = 100 * np.log(wide.employment_tp1 / wide.employment_valid)
wide["pair_valid"] = wide.employment_valid.notna() & wide.employment_tm1.notna()
wide["pair_current"] = wide.employment_valid.where(wide.pair_valid, 0)
wide["pair_previous"] = wide.employment_tm1.where(wide.pair_valid, 0)
ig = wide.groupby(["industry_code", "year"])
wide["other_regions_current"] = ig.pair_current.transform("sum") - wide.pair_current
wide["other_regions_previous"] = ig.pair_previous.transform("sum") - wide.pair_previous
wide["other_regions_count"] = ig.pair_valid.transform("sum") - wide.pair_valid.astype(
    int
)
wide["other_regions_industry_growth"] = 100 * np.log(
    wide.other_regions_current / wide.other_regions_previous
)
tot = ind.loc[
    ind.MEASURE.eq("EMP") & ind.ACTIVITY.eq("_T") & ind.UNIT_MEASURE.eq("PS"),
    ["REF_AREA", "TIME_PERIOD", "OBS_VALUE"],
].rename(
    columns={
        "REF_AREA": "region_code",
        "TIME_PERIOD": "year",
        "OBS_VALUE": "region_total_employment",
    }
)
tot = (
    regions[["region_code"]]
    .merge(pd.DataFrame({"year": range(2008, 2024)}), how="cross")
    .merge(tot, how="left", validate="one_to_one")
    .sort_values(["region_code", "year"])
)
tot["region_total_employment"] = tot.region_total_employment.where(
    tot.region_total_employment.gt(0)
)
tot["region_total_growth"] = 100 * np.log(
    tot.region_total_employment
    / tot.groupby("region_code").region_total_employment.shift(1)
)
wide = wide.merge(tot, how="left", on=["region_code", "year"], validate="many_to_one")
lf = lab.loc[
    lab.AGE.eq("Y15T64")
    & lab.SEX.eq("_T")
    & (
        lab.MEASURE.eq("UNE_RATE") & lab.UNIT_MEASURE.eq("PT_LF_SUB")
        | lab.MEASURE.eq("LF_RATE") & lab.UNIT_MEASURE.eq("PT_POP_SUB")
    )
].copy()
lf = (
    lf.pivot(index=["REF_AREA", "TIME_PERIOD"], columns="MEASURE", values="OBS_VALUE")
    .reset_index()
    .rename(
        columns={
            "REF_AREA": "region_code",
            "TIME_PERIOD": "year",
            "UNE_RATE": "unemployment_rate_pct",
            "LF_RATE": "participation_rate_pct",
        }
    )
)
wide = wide.merge(lf, on=["region_code", "year"], how="left", validate="many_to_one")
wide = wide.merge(regions, on="region_code", how="left", validate="many_to_one")
labels = (
    ind[["ACTIVITY", "Economic activity"]]
    .drop_duplicates()
    .rename(
        columns={"ACTIVITY": "industry_code", "Economic activity": "industry_name_oecd"}
    )
)
wide = wide.merge(labels, on="industry_code", how="left", validate="many_to_one")
wide["origin_year"] = wide.year
wide["target_year"] = wide.year + 1
wide["feature_latest_reference_year"] = wide.year
wide["origin_employment_weight"] = wide.employment_valid
wide["missing_predictors"] = (
    wide[NUM].isna().apply(lambda row: "|".join(row.index[row]), axis=1)
)
wide["usable"] = wide[NUM + ["target"]].notna().all(axis=1)
wide["partition"] = np.select(
    [
        wide.target_year.between(2011, 2017),
        wide.target_year.between(2018, 2020),
        wide.target_year.between(2021, 2023),
    ],
    ["train", "validation", "test"],
    default="outside",
)
csv(wide, "panel_all_rows_with_flags.csv")
data = (
    wide.loc[wide.usable & wide.partition.ne("outside")].copy().reset_index(drop=True)
)
assert data.shape[0] == 2120
assert data.groupby("partition").size().to_dict() == {
    "test": 510,
    "train": 1120,
    "validation": 490,
}
assert data.feature_latest_reference_year.lt(data.target_year).all()
assert not data.duplicated(["region_code", "industry_code", "target_year"]).any()
csv(data, "analysis_panel_main.csv")
quality = {
    "raw_industry_rows": len(ind),
    "raw_labour_rows": len(lab),
    "raw_industry_duplicate_keys": int(ind.duplicated(ikey).sum()),
    "raw_labour_duplicate_keys": int(lab.duplicated(lkey).sum()),
    "industry_raw_sha256": sha(industry_path),
    "labour_raw_sha256": sha(labour_path),
    "industry_original_missing_obs": int(ind.OBS_VALUE.isna().sum()),
    "labour_original_missing_obs": int(lab.OBS_VALUE.isna().sum()),
    "industry_grid_rows": len(wide),
    "industry_available_positive_rows": int(wide.employment_valid.notna().sum()),
    "excluded_sejong_zero_rows": int(wide.suspect_sejong_zero.sum()),
    "valid_forecast_rows": len(data),
    "partition_rows": data.groupby("partition").size().to_dict(),
    "forecast_rows_by_target_year": data.groupby("target_year").size().to_dict(),
    "unique_regions": data.region_code.nunique(),
    "unique_industries": data.industry_code.nunique(),
    "sejong_usable_target_years": sorted(
        data.loc[data.region_code.eq("KR054"), "target_year"].unique().tolist()
    ),
    "raw_industry_status_counts": ind.OBS_STATUS.value_counts(dropna=False).to_dict(),
    "raw_labour_status_counts": lab.OBS_STATUS.value_counts(dropna=False).to_dict(),
    "complete_features_no_imputation": True,
    "observations_not_independent": "shared region, industry, year and overlapping lags; 2120 rows are not 2120 independent temporal experiments",
    "latest_snapshot_not_historical_vintage": True,
}
write_json(OUT / "data_quality.json", quality)
csv(
    data.groupby(["partition", "target_year"])
    .agg(
        n=("target", "size"),
        mean=("target", "mean"),
        std=("target", "std"),
        min=("target", "min"),
        median=("target", "median"),
        max=("target", "max"),
        decline_share=("target", lambda x: float((x < 0).mean())),
    )
    .reset_index(),
    "target_summary.csv",
)
csv(
    data.loc[
        data.target.abs().nlargest(20).index,
        [
            "region_code",
            "region_name_ko",
            "industry_code",
            "origin_year",
            "target_year",
            "employment_valid",
            "employment_tp1",
            "target",
        ],
    ],
    "largest_absolute_targets.csv",
)


def model_specifications():
    yield ("ridge", {"alpha": 1})
    yield ("ridge", {"alpha": 10})
    yield ("ridge", {"alpha": 100})
    for depth, leaf in itertools.product([4, 8], [10, 25]):
        yield (
            "random_forest",
            {"n_estimators": 300, "max_depth": depth, "min_samples_leaf": leaf},
        )
    for leaves, l2 in itertools.product([7, 15], [1, 10]):
        yield (
            "hist_gradient_boosting",
            {
                "max_iter": 200,
                "learning_rate": 0.05,
                "max_leaf_nodes": leaves,
                "l2_regularization": l2,
                "min_samples_leaf": 20,
            },
        )


def make_model(name, params):
    num_transform = StandardScaler() if name == "ridge" else "passthrough"
    pre = ColumnTransformer(
        [
            ("numeric", num_transform, NUM),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CAT,
            ),
        ],
        sparse_threshold=0,
    )
    if name == "ridge":
        model = Ridge(**params)
    elif name == "random_forest":
        model = RandomForestRegressor(**params, random_state=SEED, n_jobs=2)
    else:
        model = HistGradientBoostingRegressor(
            **params, random_state=SEED, early_stopping=False
        )
    return Pipeline([("preprocess", pre), ("model", model)])


def baseline_predictions(name, train, test):
    if name == "zero":
        return np.zeros(len(test))
    if name == "persistence":
        return test.growth_t.to_numpy()
    means = train.groupby("industry_code").target.mean()
    return test.industry_code.map(means).to_numpy()


def metric_row(frame, pred):
    actual = frame.target.to_numpy()
    errors = np.abs(actual - pred)
    errframe = frame[["region_code", "industry_code"]].assign(ae=errors)
    return {
        "n": len(frame),
        "MAE": float(np.mean(errors)),
        "RMSE": float(np.sqrt(mean_squared_error(actual, pred))),
        "direction_accuracy": float(np.mean((actual < 0) == (pred < 0))),
        "R2": float(r2_score(actual, pred)),
        "mean_prediction": float(np.mean(pred)),
        "mean_actual": float(np.mean(actual)),
        "actual_decline_share": float(np.mean(actual < 0)),
        "predicted_decline_share": float(np.mean(pred < 0)),
        "origin_employment_weighted_MAE": float(
            np.average(errors, weights=frame.origin_employment_weight)
        ),
        "region_macro_MAE": float(errframe.groupby("region_code").ae.mean().mean()),
        "industry_macro_MAE": float(errframe.groupby("industry_code").ae.mean().mean()),
    }


def bootstrap_delta(frame, pred1, pred0, seed=SEED):
    delta = np.abs(frame.target.to_numpy() - pred1) - np.abs(
        frame.target.to_numpy() - pred0
    )
    block = (
        frame[["region_code"]]
        .assign(delta=delta)
        .groupby("region_code")
        .delta.agg(["sum", "size"])
    )
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(block), size=(2000, len(block)))
    reps = block["sum"].to_numpy()[indices].sum(axis=1) / block["size"].to_numpy()[
        indices
    ].sum(axis=1)
    return {
        "delta_MAE": float(delta.mean()),
        "lower95": float(np.quantile(reps, 0.025)),
        "upper95": float(np.quantile(reps, 0.975)),
        "bootstrap_regions": len(block),
        "bootstrap_replicates": 2000,
        "n": len(frame),
        "note": "conditional on fixed models and test years; region block resampling, no refitting",
    }


def experiment(frame, label):
    folder = OUT / label
    folder.mkdir(exist_ok=True)
    train = frame.loc[frame.partition.eq("train")].copy()
    valid = frame.loc[frame.partition.eq("validation")].copy()
    test = frame.loc[frame.partition.eq("test")].copy()
    grid = []
    for name in plan["baselines"]:
        vp = baseline_predictions(name, train, valid)
        grid.append(
            {
                "family": name,
                "kind": "baseline",
                "parameters": "{}",
                **metric_row(valid, vp),
            }
        )
    for name, params in model_specifications():
        model = make_model(name, params)
        model.fit(train[FEATURES], train.target)
        vp = model.predict(valid[FEATURES])
        grid.append(
            {
                "family": name,
                "kind": "AI",
                "parameters": json.dumps(params, sort_keys=True),
                **metric_row(valid, vp),
            }
        )
    grid = pd.DataFrame(grid)
    csv(grid, "validation_grid.csv", folder)
    winners = grid.loc[grid.groupby("family", sort=False).MAE.idxmin()].copy()
    ai = winners.loc[winners.kind.eq("AI")].sort_values("MAE", kind="stable").iloc[0]
    baseline = (
        winners.loc[winners.kind.eq("baseline")]
        .sort_values("MAE", kind="stable")
        .iloc[0]
    )
    selection = {
        "selection_frozen_utc": datetime.now(timezone.utc).isoformat(),
        "selected_AI": ai.family,
        "selected_AI_parameters": json.loads(ai.parameters),
        "selected_baseline": baseline.family,
        "validation_MAE_AI": float(ai.MAE),
        "validation_MAE_baseline": float(baseline.MAE),
        "partitions": frame.groupby("partition").size().to_dict(),
        "family_winners": winners.to_dict("records"),
    }
    write_json(folder / "selection_before_test.json", selection)
    training = pd.concat([train, valid], ignore_index=True)
    csv(
        training[FEATURES + ["target", "target_year", "origin_year"]],
        "training_design.csv",
        folder,
    )
    csv(
        test[FEATURES + ["target", "target_year", "origin_year"]],
        "test_design.csv",
        folder,
    )
    preds = test.copy()
    modelmetrics = []
    selected_model = None
    for _, row in winners.iterrows():
        if row.kind == "baseline":
            tp = baseline_predictions(row.family, training, test)
        else:
            model = make_model(row.family, json.loads(row.parameters))
            model.fit(training[FEATURES], training.target)
            tp = model.predict(test[FEATURES])
            joblib.dump(model, folder / f"model_{row.family}.joblib")
            if row.family == ai.family:
                selected_model = model
        preds["pred_" + row.family] = tp
        modelmetrics.append(
            {
                "model": row.family,
                "kind": row.kind,
                "validation_MAE": float(row.MAE),
                "selected_AI": row.family == ai.family,
                "selected_baseline": row.family == baseline.family,
                **metric_row(test, tp),
            }
        )
    csv(pd.DataFrame(modelmetrics), "test_metrics.csv", folder)
    csv(preds, "test_predictions.csv", folder)
    subgroups = []
    for col in ["target_year", "region_code", "industry_code", "policy_region_5plus3"]:
        for key, sub in preds.groupby(col, sort=True):
            for row in modelmetrics:
                subgroups.append(
                    {
                        "grouping": col,
                        "group": str(key),
                        "model": row["model"],
                        **metric_row(sub, sub["pred_" + row["model"]].to_numpy()),
                    }
                )
    csv(pd.DataFrame(subgroups), "test_subgroup_metrics.csv", folder)
    ci = {
        "selected_AI_vs_selected_baseline": bootstrap_delta(
            test,
            preds["pred_" + ai.family].to_numpy(),
            preds["pred_" + baseline.family].to_numpy(),
        ),
        "selected_AI_vs_zero": bootstrap_delta(
            test, preds["pred_" + ai.family].to_numpy(), preds.pred_zero.to_numpy()
        ),
    }
    write_json(folder / "bootstrap_intervals.json", ci)
    importance = permutation_importance(
        selected_model,
        test[FEATURES],
        test.target,
        scoring="neg_mean_absolute_error",
        n_repeats=30,
        random_state=SEED,
        n_jobs=1,
    )
    imp = pd.DataFrame(
        {
            "feature": FEATURES,
            "test_MAE_increase_mean": importance.importances_mean,
            "permutation_std_not_CI": importance.importances_std,
        }
    )
    csv(
        imp.sort_values("test_MAE_increase_mean", ascending=False),
        "permutation_importance.csv",
        folder,
    )
    csv(
        pd.DataFrame(importance.importances, index=FEATURES)
        .rename_axis("feature")
        .reset_index(),
        "permutation_importance_replicates.csv",
        folder,
    )
    overview = {"selection": selection, "test_metrics": modelmetrics, "bootstrap": ci}
    write_json(folder / "results.json", overview)
    print(
        json.dumps(
            {
                "experiment": label,
                "selection": {
                    k: selection[k]
                    for k in [
                        "selected_AI",
                        "selected_AI_parameters",
                        "selected_baseline",
                        "validation_MAE_AI",
                        "validation_MAE_baseline",
                        "partitions",
                    ]
                },
                "test_metrics": modelmetrics,
                "bootstrap": ci,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return (overview, preds, selected_model)


with threadpool_limits(limits=2):
    main, mpreds, mainmodel = experiment(data, "main")
    sensitivities = []
    selected = main["selection"]["selected_AI"]
    baseline = main["selection"]["selected_baseline"]
    for label, mask in [
        ("exclude_sejong_no_refit", mpreds.region_code.ne("KR054")),
        ("exclude_2021_no_refit", mpreds.target_year.ne(2021)),
        ("exclude_A_no_refit", mpreds.industry_code.ne("A")),
    ]:
        sub = mpreds.loc[mask]
        for model in [selected, baseline]:
            sensitivities.append(
                {
                    "sensitivity": label,
                    "model": model,
                    **metric_row(sub, sub["pred_" + model].to_numpy()),
                }
            )
    csv(pd.DataFrame(sensitivities), "sensitivity_subset_metrics.csv")
    rolling = []
    for year in [2021, 2022, 2023]:
        tr = data.loc[data.target_year.lt(year)]
        te = data.loc[data.target_year.eq(year)].copy()
        model = make_model(selected, main["selection"]["selected_AI_parameters"])
        model.fit(tr[FEATURES], tr.target)
        te["pred_AI_rolling"] = model.predict(te[FEATURES])
        te["pred_baseline_rolling"] = baseline_predictions(baseline, tr, te)
        te["training_target_year_max"] = int(tr.target_year.max())
        rolling.append(te)
    roll = pd.concat(rolling, ignore_index=True)
    csv(roll, "rolling_test_predictions.csv")
    rolling_metrics = []
    for name in ["AI", "baseline"]:
        rolling_metrics.append(
            {
                "group": "all",
                "model": name,
                **metric_row(roll, roll["pred_" + name + "_rolling"].to_numpy()),
            }
        )
        for year, sub in roll.groupby("target_year"):
            rolling_metrics.append(
                {
                    "group": str(year),
                    "model": name,
                    **metric_row(sub, sub["pred_" + name + "_rolling"].to_numpy()),
                }
            )
    csv(pd.DataFrame(rolling_metrics), "rolling_test_metrics.csv")
    delayed = wide.sort_values(["region_code", "industry_code", "year"]).copy()
    delayed[NUM] = delayed.groupby(["region_code", "industry_code"])[NUM].shift(1)
    delayed["feature_latest_reference_year"] = delayed.origin_year - 1
    delayed["usable"] = delayed[NUM + ["target"]].notna().all(axis=1)
    delayed = (
        delayed.loc[delayed.usable & delayed.partition.ne("outside")]
        .copy()
        .reset_index(drop=True)
    )
    assert delayed.feature_latest_reference_year.eq(delayed.target_year - 2).all()
    csv(delayed, "analysis_panel_delayed.csv")
    delayed_result, dpreds, dmodel = experiment(delayed, "delayed_features")
environment = {
    "python": sys.version,
    "platform": platform.platform(),
    "numpy": np.__version__,
    "pandas": pd.__version__,
    "scipy": scipy.__version__,
    "scikit_learn": sklearn.__version__,
    "joblib": joblib.__version__,
    "seed": SEED,
    "threads": 2,
    "script_sha256": sha(Path(__file__)),
    "completed_utc": datetime.now(timezone.utc).isoformat(),
}
write_json(OUT / "environment.json", environment)
summary = {
    "quality": quality,
    "main": main,
    "delayed": delayed_result,
    "subset_sensitivity": sensitivities,
    "rolling_metrics": rolling_metrics,
    "environment": environment,
}
write_json(OUT / "all_results.json", summary)
print("COMPLETE", flush=True)
