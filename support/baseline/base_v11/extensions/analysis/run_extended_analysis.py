from __future__ import annotations

if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import hashlib
import itertools
import json
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import HuberRegressor, QuantileRegressor, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--source-root",
    type=Path,
    required=True,
    help="Original reproduction package directory containing analysis/ and raw/. Read-only.",
)
parser.add_argument(
    "--output-root",
    type=Path,
    default=Path(__file__).resolve().parent,
    help="Separate result directory; must not be inside source-root.",
)
args = parser.parse_args()
OUT = args.output_root.resolve()
SOURCE = args.source_root.resolve()
if OUT == SOURCE or SOURCE in OUT.parents:
    parser.error("output-root must be separate from the original source-root")
if not (SOURCE / "analysis/analysis_panel_main.csv").is_file():
    parser.error("source-root does not contain analysis/analysis_panel_main.csv")
OUT.mkdir(parents=True, exist_ok=True)
SEED = 20260918
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
OWN_GROWTH = ["growth_t", "growth_tm1"]
ALL_GROWTH = OWN_GROWTH + ["other_regions_industry_growth", "region_total_growth"]
KEYS = ["region_code", "industry_code", "target_year"]
ALPHAS = np.logspace(0, 4, 9).tolist()
DAMPING = [0, 0.25, 0.5, 0.75, 1]
THREADS = 2


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def csv(path, frame):
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


SPEC = {
    "design_version": 2,
    "predecessor": "prior_version_v1/analysis_design_before_execution.json; full v1 outputs preserved",
    "change_reason": "Restore omitted original industry-mean baseline, add explicit zero summary, and portable CLI. No model grid, filter or split changed; not performance-driven tuning.",
    "created_utc": now(),
    "status": "Post-hoc robustness design fixed before this extension execution; not preregistered, not independent external validation.",
    "source_original_results": "Original 2011–2017 train / 2018–2020 validation / 2021–2023 test retained as previously reported; no replacement by this extension.",
    "target": "100 ln(E_(t+1)/E_t); log points",
    "primary_split": {
        "train": [2011, 2017],
        "validation": [2018, 2020],
        "test": [2021, 2023],
    },
    "ridge_alpha": ALPHAS,
    "tie_rule": "Lowest validation MAE; ties retain declared order. Ridge grid declared in ascending alpha order.",
    "constants": ["zero", "training_target_mean", "training_target_median"],
    "baselines": [
        "zero",
        "mean",
        "median",
        "industry_mean",
        "persistence",
        "damped_persistence",
        "national_industry_lag",
    ],
    "damped_persistence_grid": DAMPING,
    "national_industry_lag": "100 ln(sum E_t / sum E_(t-1)) over ALL regions in the same industry with strictly positive paired E_t AND E_(t-1); input latest year t < target t+1. Focal region included. Lagged benchmark, NOT realized future growth, NOT full classical shift-share decomposition.",
    "Huber": {
        "epsilon": 1.35,
        "alpha": 0.0001,
        "max_iter": 2000,
        "tol": 1e-05,
        "tuning": "none",
    },
    "QuantileRegressor": {
        "quantile": 0.5,
        "alpha": 0.0,
        "solver": "highs",
        "tuning": "none; unpenalized LAD, numerical covariates standardized; categorical terms one-hot encoded",
    },
    "RF": {
        "n_estimators": 300,
        "max_depth": [4, 8],
        "min_samples_leaf": [10, 25],
        "random_state": SEED,
        "n_jobs": THREADS,
        "scope": "Full fixed-split scenario and every rolling origin; no RF in ablation scenarios to limit redundant computation.",
    },
    "preprocessing": "Each validation candidate fitted on train only; chosen settings refitted on train+validation. StandardScaler for linear models; original one-hot full categories with unknown categories ignored. RF numeric passthrough.",
    "origin_filter": "origin_employment_weight >= 10000, observed at forecast origin. Applied separately to every split for refit; frozen evaluation does not alter training.",
    "scenarios": "2×2×2 refit grid of full vs origin>=10000, all industries vs exclude A, own lags included vs removed; plus full data all growth variables removed; plus Chungnam row exclusion; plus Chungnam exclusion with other-region/national signals recomputed without Chungnam.",
    "frozen_filters": [
        "all",
        "origin_ge10000",
        "exclude_A",
        "origin_ge10000_exclude_A",
        "exclude_chungnam",
    ],
    "ablation_definitions": {
        "drop_own_growth": OWN_GROWTH,
        "drop_all_growth": ALL_GROWTH,
    },
    "rolling": {
        "target_years": list(range(2015, 2024)),
        "train": "2011 <= target_year <= Y-2",
        "validation": "target_year == Y-1",
        "test": "target_year == Y",
        "refit": "train+validation after per-origin selection",
        "candidates": "all baselines, ridge grid, fixed Huber, fixed median regression, RF original four-setting grid",
    },
    "strategies": [
        "validation_best_baseline",
        "validation_best_learned",
        "validation_best_all",
    ],
    "rolling_uncertainty": "Report paired annual MAE differences and equal-origin average. Nine overlapping expanding origins, including years used in original train/validation; not independent replications. No DM p-values or significance claim.",
    "source_jump": "Report Chungnam raw employment (all 10 broad industries, C and _T), 2014–2019, prior year levels, raw status and both log/simple changes; a discontinuity in numbers is not proof of a methodological break.",
    "no_result_adaptation": True,
    "seed": SEED,
    "threads": THREADS,
    "script_sha256": sha(Path(__file__)),
}
write_json(OUT / "analysis_design_before_execution.json", SPEC)
threadpool_limits(THREADS)
START = now()
t0 = time.monotonic()
PANEL = SOURCE / "analysis/analysis_panel_main.csv"
pd0 = pd.read_csv(PANEL).reset_index(drop=True)
assert len(pd0) == 2120 and (not pd0.duplicated(KEYS).any())
assert (pd0.feature_latest_reference_year < pd0.target_year).all()
assert (pd0.origin_year + 1 == pd0.target_year).all()
full = pd.read_csv(SOURCE / "analysis/panel_all_rows_with_flags.csv")
valid = full[full.employment_valid.gt(0) & full.employment_tm1.gt(0)].copy()
assert np.allclose(valid.pair_current, valid.employment_valid)
assert np.allclose(valid.pair_previous, valid.employment_tm1)
pair = (
    valid.groupby(["industry_code", "origin_year"])
    .agg(
        current=("employment_valid", "sum"),
        previous=("employment_tm1", "sum"),
        regions=("region_code", "nunique"),
    )
    .reset_index()
)
pair["national_industry_lag"] = 100 * np.log(pair.current / pair.previous)
pd0 = pd0.merge(
    pair[["industry_code", "origin_year", "national_industry_lag", "regions"]],
    on=["industry_code", "origin_year"],
    how="left",
    validate="many_to_one",
)
assert not pd0.national_industry_lag.isna().any()
assert np.allclose(
    pd0.national_industry_lag,
    100
    * np.log(
        (pd0.other_regions_current + pd0.pair_current)
        / (pd0.other_regions_previous + pd0.pair_previous)
    ),
    atol=1e-10,
)
no_cn = (
    valid[valid.region_code.ne("KR053")]
    .groupby(["industry_code", "origin_year"])
    .agg(
        nocn_current=("employment_valid", "sum"),
        nocn_previous=("employment_tm1", "sum"),
    )
    .reset_index()
)
pd0 = pd0.merge(no_cn, on=["industry_code", "origin_year"], validate="many_to_one")
write_json(
    OUT / "input_provenance.json",
    {
        "original_panel_sha256": sha(PANEL),
        "original_model_sha256": sha(SOURCE / "analysis/main/model_ridge.joblib"),
        "original_raw_industry_sha256": sha(
            SOURCE / "raw/economic/oecd_korea_regional_industry_raw.csv"
        ),
        "rows": len(pd0),
        "latest_covariate_year_less_than_target": True,
        "national_pair_formula_assertion": "PASS",
        "national_signal_has_no_target_year_values": True,
    },
)
csv(OUT / "national_signal_origin_year.csv", pair)
WARNINGS = []


def metrics(f, pred):
    y = f.target.to_numpy()
    p = np.asarray(pred)
    ae = np.abs(y - p)
    return {
        "n": len(y),
        "MAE": float(ae.mean()),
        "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
        "R2": float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)),
        "direction_accuracy": float(np.mean((y < 0) == (p < 0))),
        "mean_prediction": float(p.mean()),
        "mean_actual": float(y.mean()),
        "predicted_decline_share": float(np.mean(p < 0)),
        "origin_employment_weighted_MAE": float(
            np.average(ae, weights=f.origin_employment_weight)
        ),
    }


def model(name, params, num):
    pre = ColumnTransformer(
        [
            (
                "numeric",
                "passthrough" if name == "random_forest" else StandardScaler(),
                num,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CAT,
            ),
        ],
        sparse_threshold=0,
    )
    if name == "ridge":
        est = Ridge(alpha=float(params["alpha"]))
    elif name == "huber":
        est = HuberRegressor(epsilon=1.35, alpha=0.0001, max_iter=2000, tol=1e-05)
    elif name == "median_regression":
        est = QuantileRegressor(quantile=0.5, alpha=0, solver="highs")
    elif name == "random_forest":
        est = RandomForestRegressor(
            n_estimators=300,
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=SEED,
            n_jobs=THREADS,
        )
    else:
        raise ValueError(name)
    return Pipeline([("preprocess", pre), ("model", est)])


def fit(m, tr, num, context):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        m.fit(tr[num + CAT], tr.target)
    for w in caught:
        WARNINGS.append(
            {
                "context": context,
                "category": w.category.__name__,
                "message": str(w.message),
            }
        )
    return m


def baseline(name, tr, te, params):
    if name == "zero":
        return np.zeros(len(te))
    if name == "mean":
        return np.repeat(tr.target.mean(), len(te))
    if name == "median":
        return np.repeat(tr.target.median(), len(te))
    if name == "industry_mean":
        mapped = te.industry_code.map(tr.groupby("industry_code").target.mean())
        assert not mapped.isna().any(), (
            "Validation/test industry absent from training for industry-mean benchmark"
        )
        return mapped.to_numpy()
    if name == "persistence":
        return te.growth_t.to_numpy()
    if name == "damped_persistence":
        return params["damping"] * te.growth_t.to_numpy()
    if name == "national_industry_lag":
        return te.national_industry_lag.to_numpy()
    raise ValueError(name)


def run_experiment(frame, num, label, trainmask, valmask, testmask, include_rf):
    folder = OUT / label
    folder.mkdir(parents=True, exist_ok=True)
    tr = frame.loc[trainmask].copy()
    va = frame.loc[valmask].copy()
    te = frame.loc[testmask].copy()
    assert len(tr) > 0 and len(va) > 0 and (len(te) > 0)
    assert (
        tr.target_year.max() < va.target_year.min()
        and va.target_year.max() < te.target_year.min()
    )
    assert (
        not tr[num + CAT].isna().any().any()
        and (not va[num + CAT].isna().any().any())
        and (not te[num + CAT].isna().any().any())
    )
    candidates = []
    for name in SPEC["baselines"]:
        settings = (
            [{"damping": x} for x in DAMPING] if name == "damped_persistence" else [{}]
        )
        for params in settings:
            vp = baseline(name, tr, va, params)
            candidates.append(
                {
                    "family": name,
                    "kind": "baseline",
                    "parameters": params,
                    **metrics(va, vp),
                }
            )
    learned = [("ridge", {"alpha": a}) for a in ALPHAS] + [
        ("huber", {}),
        ("median_regression", {}),
    ]
    if include_rf:
        learned += [
            ("random_forest", {"max_depth": d, "min_samples_leaf": leaf})
            for d, leaf in itertools.product([4, 8], [10, 25])
        ]
    for name, params in learned:
        m = fit(
            model(name, params, num),
            tr,
            num,
            label + "/validation/" + name + "/" + str(params),
        )
        vp = m.predict(va[num + CAT])
        candidates.append(
            {"family": name, "kind": "learned", "parameters": params, **metrics(va, vp)}
        )
    winners = {}
    for c in candidates:
        if c["family"] not in winners or c["MAE"] < winners[c["family"]]["MAE"]:
            winners[c["family"]] = c
    bestbase = min(
        [c for c in winners.values() if c["kind"] == "baseline"], key=lambda c: c["MAE"]
    )
    bestlearned = min(
        [c for c in winners.values() if c["kind"] == "learned"], key=lambda c: c["MAE"]
    )
    bestall = min(winners.values(), key=lambda c: c["MAE"])
    selection = {
        "selection_frozen_utc": now(),
        "label": label,
        "features": num + CAT,
        "partitions": {"train": len(tr), "validation": len(va), "test": len(te)},
        "years": {
            "train": sorted(tr.target_year.unique().tolist()),
            "validation": sorted(va.target_year.unique().tolist()),
            "test": sorted(te.target_year.unique().tolist()),
        },
        "winners": winners,
        "strategies": {
            "validation_best_baseline": bestbase["family"],
            "validation_best_learned": bestlearned["family"],
            "validation_best_all": bestall["family"],
        },
        "posthoc_sensitivity": True,
    }
    write_json(folder / "selection_before_test.json", selection)
    grid = pd.DataFrame(candidates)
    grid["parameters"] = grid.parameters.map(lambda x: json.dumps(x, sort_keys=True))
    csv(folder / "validation_grid.csv", grid)
    training = pd.concat([tr, va], ignore_index=True)
    cols = KEYS + [
        "origin_year",
        "region_name_ko",
        "policy_region_5plus3",
        "origin_employment_weight",
        "target",
    ]
    preds = te[cols].copy()
    testmetrics = []
    fitted = {}
    for name, c in winners.items():
        if c["kind"] == "baseline":
            yp = baseline(name, training, te, c["parameters"])
        else:
            m = fit(
                model(name, c["parameters"], num),
                training,
                num,
                label + "/refit/" + name,
            )
            yp = m.predict(te[num + CAT])
            fitted[name] = m
        preds["pred_" + name] = yp
        testmetrics.append(
            {
                "label": label,
                "model": name,
                "kind": c["kind"],
                "validation_MAE": c["MAE"],
                "parameters": json.dumps(c["parameters"], sort_keys=True),
                **metrics(te, yp),
            }
        )
    for strategy, family in selection["strategies"].items():
        preds["pred_" + strategy] = preds["pred_" + family]
        testmetrics.append(
            {
                "label": label,
                "model": strategy,
                "kind": "selection_strategy",
                "selected_family": family,
                "validation_MAE": winners[family]["MAE"],
                **metrics(te, preds["pred_" + family]),
            }
        )
    csv(folder / "test_predictions.csv", preds)
    csv(folder / "test_metrics.csv", pd.DataFrame(testmetrics))
    ridge_sensitivity = []
    rpreds = te[cols].copy()
    for alpha in ALPHAS:
        if alpha == winners["ridge"]["parameters"]["alpha"]:
            m = fitted["ridge"]
        else:
            m = fit(
                model("ridge", {"alpha": alpha}, num),
                training,
                num,
                label + "/posthoc_alpha_grid/" + str(alpha),
            )
        yp = m.predict(te[num + CAT])
        rpreds["alpha_" + format(alpha, ".12g")] = yp
        valrow = next(
            (
                c
                for c in candidates
                if c["family"] == "ridge" and c["parameters"]["alpha"] == alpha
            )
        )
        ridge_sensitivity.append(
            {
                "label": label,
                "alpha": alpha,
                "validation_MAE": valrow["MAE"],
                "selected_from_validation": alpha
                == winners["ridge"]["parameters"]["alpha"],
                "test_reporting": "post-hoc sensitivity, never used for selection",
                **metrics(te, yp),
            }
        )
    csv(folder / "ridge_alpha_posthoc_test_grid.csv", pd.DataFrame(ridge_sensitivity))
    csv(folder / "ridge_alpha_test_predictions.csv", rpreds)
    if label == "fixed/full":
        for name, m in fitted.items():
            joblib.dump(m, folder / ("model_" + name + ".joblib"))
        old = pd.read_csv(SOURCE / "analysis/main/test_predictions.csv")[
            KEYS + ["pred_ridge"]
        ]
        reconstructed = rpreds[KEYS + ["alpha_100"]].merge(
            old, on=KEYS, validate="one_to_one"
        )
        error = float(
            np.max(np.abs(reconstructed.alpha_100 - reconstructed.pred_ridge))
        )
        assert error < 1e-10
        write_json(
            folder / "original_alpha100_reproduction.json",
            {"max_absolute_prediction_difference": error, "status": "PASS"},
        )
    print(
        json.dumps(
            {
                "label": label,
                "n": selection["partitions"],
                "ridge_alpha": winners["ridge"]["parameters"]["alpha"],
                "strategies": selection["strategies"],
                "elapsed_seconds": round(time.monotonic() - t0, 1),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return (
        pd.DataFrame(testmetrics),
        pd.DataFrame(ridge_sensitivity),
        selection,
        preds,
    )


orig = joblib.load(SOURCE / "analysis/main/model_ridge.joblib")
pre = orig.named_steps["preprocess"]
est = orig.named_steps["model"]
scaler = pre.named_transformers_["numeric"]
coef = []
for j, name in enumerate(NUM):
    coef.append(
        {
            "feature": name,
            "kind": "numeric",
            "standardized_coefficient": float(est.coef_[j]),
            "original_scale_coefficient": float(est.coef_[j] / scaler.scale_[j]),
            "training_mean": float(scaler.mean_[j]),
            "training_scale": float(scaler.scale_[j]),
            "unit_interpretation": "predicted logpoint change per 1 input unit holding other encoded terms fixed; associational model coefficient, not causal",
        }
    )
for j, name in enumerate(pre.get_feature_names_out()[len(NUM) :], len(NUM)):
    coef.append(
        {
            "feature": name,
            "kind": "dummy",
            "standardized_coefficient": float(est.coef_[j]),
            "original_scale_coefficient": float(est.coef_[j]),
            "unit_interpretation": "penalized dummy coefficient under full one-hot encoding; coefficient origin depends on intercept/penalty; not a causal regional/industrial effect",
        }
    )
csv(OUT / "original_ridge_coefficients.csv", pd.DataFrame(coef))
write_json(
    OUT / "original_ridge_intercept.json",
    {
        "standardized_intercept": float(est.intercept_),
        "original_numeric_scale_intercept": float(
            est.intercept_
            - np.sum(est.coef_[: len(NUM)] * scaler.mean_ / scaler.scale_)
        ),
        "background_prediction": float(
            pd.read_csv(
                SOURCE / "service/outputs/linear_attributions_10_features.csv"
            ).reference_prediction.iloc[0]
        ),
        "own_growth_coefficients_negative": bool(est.coef_[2] < 0 and est.coef_[3] < 0),
    },
)
saved = pd.read_csv(SOURCE / "analysis/main/test_predictions.csv")
frozen = []
filters = {
    "all": np.ones(len(saved), dtype=bool),
    "origin_ge10000": saved.origin_employment_weight.ge(10000),
    "exclude_A": saved.industry_code.ne("A"),
    "origin_ge10000_exclude_A": saved.origin_employment_weight.ge(10000)
    & saved.industry_code.ne("A"),
    "exclude_chungnam": saved.region_code.ne("KR053"),
}
for filt, mask in filters.items():
    f = saved.loc[mask]
    for name in [
        "zero",
        "ridge",
        "random_forest",
        "hist_gradient_boosting",
        "industry_mean",
        "persistence",
    ]:
        frozen.append(
            {
                "filter": filt,
                "model": name,
                "evaluation": "frozen original prediction, no refit",
                **metrics(f, f["pred_" + name]),
            }
        )
csv(OUT / "frozen_subset_metrics.csv", pd.DataFrame(frozen))
scenarios = []
for large, noA, nogrowth in itertools.product(
    [False, True], [False, True], [False, True]
):
    parts = []
    if large:
        parts += ["origin_ge10000"]
    if noA:
        parts += ["exclude_A"]
    if nogrowth:
        parts += ["drop_own_growth"]
    scenarios.append(
        {
            "name": "_".join(parts) if parts else "full",
            "large": large,
            "noA": noA,
            "drop": OWN_GROWTH if nogrowth else [],
            "cn": False,
            "cn_external": False,
        }
    )
scenarios += [
    {
        "name": "drop_all_growth",
        "large": False,
        "noA": False,
        "drop": ALL_GROWTH,
        "cn": False,
        "cn_external": False,
    },
    {
        "name": "exclude_chungnam_rows",
        "large": False,
        "noA": False,
        "drop": [],
        "cn": True,
        "cn_external": False,
    },
    {
        "name": "exclude_chungnam_and_external_source",
        "large": False,
        "noA": False,
        "drop": [],
        "cn": True,
        "cn_external": True,
    },
]
write_json(OUT / "refit_scenario_definitions.json", scenarios)
allmetrics = []
allalpha = []
selections = []
for s in scenarios:
    f = pd0.copy()
    if s["large"]:
        f = f[f.origin_employment_weight.ge(10000)]
    if s["noA"]:
        f = f[f.industry_code.ne("A")]
    if s["cn"]:
        f = f[f.region_code.ne("KR053")]
    if s["cn_external"]:
        f["other_regions_industry_growth"] = 100 * np.log(
            (f.nocn_current - f.pair_current) / (f.nocn_previous - f.pair_previous)
        )
        f["national_industry_lag"] = 100 * np.log(f.nocn_current / f.nocn_previous)
        assert np.isfinite(f.other_regions_industry_growth).all()
    f = f.reset_index(drop=True)
    num = [x for x in NUM if x not in s["drop"]]
    m, a, sel, pr = run_experiment(
        f,
        num,
        "fixed/" + s["name"],
        f.target_year.between(2011, 2017),
        f.target_year.between(2018, 2020),
        f.target_year.between(2021, 2023),
        s["name"] == "full",
    )
    allmetrics.append(m)
    allalpha.append(a)
    selections.append(sel)
csv(OUT / "fixed_all_scenario_metrics.csv", pd.concat(allmetrics, ignore_index=True))
csv(OUT / "fixed_all_alpha_sensitivity.csv", pd.concat(allalpha, ignore_index=True))
write_json(OUT / "fixed_all_selections.json", selections)
rollm = []
rollp = []
rolls = []
for year in range(2015, 2024):
    f = pd0.copy()
    m, a, sel, pr = run_experiment(
        f,
        NUM,
        "rolling/" + str(year),
        f.target_year.between(2011, year - 2),
        f.target_year.eq(year - 1),
        f.target_year.eq(year),
        True,
    )
    m["target_year"] = year
    rollm.append(m)
    rollp.append(pr)
    rolls.append(sel)
rm = pd.concat(rollm, ignore_index=True)
rp = pd.concat(rollp, ignore_index=True)
csv(OUT / "rolling_annual_metrics.csv", rm)
csv(OUT / "rolling_all_predictions.csv", rp)
write_json(OUT / "rolling_selections.json", rolls)
annual = rm.pivot(index="target_year", columns="model", values="MAE")
paired = []
for name in annual.columns:
    for year, row in annual.iterrows():
        paired.append(
            {
                "target_year": int(year),
                "model": name,
                "model_MAE": row[name],
                "zero_MAE": row["zero"],
                "delta_vs_zero": row[name] - row["zero"],
                "best_baseline_MAE": row["validation_best_baseline"],
                "delta_vs_validation_best_baseline": row[name]
                - row["validation_best_baseline"],
            }
        )
paired = pd.DataFrame(paired)
csv(OUT / "rolling_paired_annual_losses.csv", paired)
summary = []
for name, g in paired.groupby("model", sort=False):
    prcol = "pred_" + name
    overall = metrics(rp, rp[prcol])
    summary.append(
        {
            "model": name,
            "origins": len(g),
            "mean_annual_MAE": float(g.model_MAE.mean()),
            "mean_annual_delta_vs_zero": float(g.delta_vs_zero.mean()),
            "origins_better_than_zero": int(g.delta_vs_zero.lt(0).sum()),
            "mean_annual_delta_vs_validation_best_baseline": float(
                g.delta_vs_validation_best_baseline.mean()
            ),
            "origins_better_than_selected_baseline": int(
                g.delta_vs_validation_best_baseline.lt(0).sum()
            ),
            "pooled_n": overall["n"],
            "pooled_MAE": overall["MAE"],
            "inferential_test": "not performed: only 9 overlapping origins; post-hoc historical robustness",
        }
    )
csv(OUT / "rolling_summary.csv", pd.DataFrame(summary))
raw = pd.read_csv(SOURCE / "raw/economic/oecd_korea_regional_industry_raw.csv")
cn = raw[
    raw.REF_AREA.eq("KR053") & raw.MEASURE.eq("EMP") & raw.UNIT_MEASURE.eq("PS")
].copy()
cn = cn.sort_values(["ACTIVITY", "TIME_PERIOD"])
cn["prior_year_employment"] = cn.groupby("ACTIVITY").OBS_VALUE.shift(1)
cn["prior_year"] = cn.groupby("ACTIVITY").TIME_PERIOD.shift(1)
cn["log_change"] = 100 * np.log(cn.OBS_VALUE / cn.prior_year_employment)
cn["simple_change_pct"] = 100 * (cn.OBS_VALUE / cn.prior_year_employment - 1)
cn["level_change"] = cn.OBS_VALUE - cn.prior_year_employment
cn = cn[cn.TIME_PERIOD.between(2014, 2019)]
assert (cn.TIME_PERIOD - cn.prior_year).eq(1).all()
csv(
    OUT / "chungnam_2014_2019_source_movements.csv",
    cn[
        [
            "REF_AREA",
            "ACTIVITY",
            "Economic activity",
            "TIME_PERIOD",
            "OBS_VALUE",
            "prior_year_employment",
            "level_change",
            "log_change",
            "simple_change_pct",
            "OBS_STATUS",
            "UNIT_MEASURE",
            "UNIT_MULT",
        ]
    ],
)
lab = pd.read_csv(SOURCE / "raw/oecd_korea_regional_labour_raw.csv")
cl = lab[
    lab.REF_AREA.eq("KR053")
    & lab.TIME_PERIOD.between(2014, 2019)
    & lab.AGE.eq("Y15T64")
    & lab.SEX.eq("_T")
    & lab.MEASURE.isin(["UNE_RATE", "LF_RATE"])
]
csv(OUT / "chungnam_2014_2019_labour_covariates.csv", cl)
write_json(OUT / "fit_warnings.json", WARNINGS)
ENV = {
    "started_utc": START,
    "completed_utc": now(),
    "wall_seconds": time.monotonic() - t0,
    "python": sys.version,
    "executable": sys.executable,
    "platform": platform.platform(),
    "numpy": np.__version__,
    "pandas": pd.__version__,
    "scipy": scipy.__version__,
    "sklearn": sklearn.__version__,
    "joblib": joblib.__version__,
    "threads": THREADS,
    "seed": SEED,
    "script_sha256": sha(Path(__file__)),
    "model_fit_warnings": len(WARNINGS),
}
write_json(OUT / "environment.json", ENV)
write_json(
    OUT / "completion.json",
    {
        "status": "PASS",
        "fixed_scenarios": len(scenarios),
        "rolling_origins": 9,
        "source_panel_unchanged": sha(PANEL)
        == json.loads((OUT / "input_provenance.json").read_text(encoding="utf-8"))[
            "original_panel_sha256"
        ],
        "no_result_dependent_tuning": True,
        "warnings": len(WARNINGS),
    },
)
print(
    json.dumps(
        {
            "status": "PASS",
            "wall_seconds": ENV["wall_seconds"],
            "warnings": len(WARNINGS),
        },
        ensure_ascii=False,
    ),
    flush=True,
)
