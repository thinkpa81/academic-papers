#!/usr/bin/env python3
"""Retrospective sensitivity analysis. Never a new independent holdout.

Run from any directory: python code/run_benchmark.py --out results/benchmark
The 38 candidates and selection rules are written before fitting. Original test
results were already known when this extension was designed.
"""

import argparse
import hashlib
import importlib.util
import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import catboost
import lightgbm
import numpy as np
import pandas as pd
import sklearn
import xgboost
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "support"
BASE = REF / "baseline/base_v11"
KEY = ["target_year", "region_code", "industry_code"]
Y = "target_logpoints"
W = "employment_input_persons"
SEED = 20261025


def module(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


orig = module("original", BASE / "analysis_harmonized/run.py")
extra = module("extra", REF / "forecast_addendum/run_addendum.py")


def dump(o, p):
    p.write_text(
        json.dumps(o, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return pd.read_csv(p, float_precision="round_trip")


def save(d, p):
    pd.DataFrame(d).to_csv(p, index=False, encoding="utf-8-sig", float_format="%.17g")


def candidates():
    out = [
        dict(name=n, family="baseline", params={})
        for n in [
            "zero",
            "last_growth",
            "industry_past_mean",
            "global_past_mean",
            "global_past_median",
            "lagged_available_region_industry_growth",
        ]
    ]
    for n, f, p in orig.candidates():
        out.append(dict(name=n, family=f, params=p))
    for fam in ["xgboost", "catboost"]:
        for depth in [2, 3]:
            for l2 in [10, 100]:
                out.append(
                    dict(
                        name=f"{fam}_d{depth}_l2{l2}",
                        family=fam,
                        params=dict(depth=depth, l2=l2),
                    )
                )
    for leaves in [7, 15]:
        for l2 in [1, 10]:
            out.append(
                dict(
                    name=f"lightgbm_l{leaves}_l2{l2}",
                    family="lightgbm",
                    params=dict(leaves=leaves, l2=l2),
                )
            )
    out.append(dict(name="pooled_ar1", family="ar1", params={}))
    for l in [1, 10, 100, 1000, 10000]:
        out.append(dict(name=f"panel_ar1_l{l}", family="panel_ar1", params={"lam": l}))
    assert len(out) == 38
    return out


def fit(c, tr):
    f = c["family"]
    p = c["params"]
    if f == "baseline":
        return None
    if f in ["ridge", "random_forest", "hist_gradient_boosting", "huber"]:
        return orig.fit_candidate(f, p, tr)[0]
    if f == "ar1":
        return LinearRegression().fit(tr[["own_growth"]], tr[Y])
    if f == "panel_ar1":
        return extra.PanelShrinkage(p["lam"]).fit(tr)
    if f == "catboost":
        m = CatBoostRegressor(
            iterations=200,
            learning_rate=0.05,
            depth=p["depth"],
            l2_leaf_reg=p["l2"],
            loss_function="RMSE",
            boosting_type="Ordered",
            has_time=True,
            random_seed=SEED,
            thread_count=1,
            verbose=False,
            allow_writing_files=False,
        )
        m.fit(tr[orig.NUM + orig.CAT], tr[Y], cat_features=orig.CAT)
        return m
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), orig.NUM),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                orig.CAT,
            ),
        ]
    )
    if f == "xgboost":
        m = XGBRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=p["depth"],
            reg_lambda=p["l2"],
            min_child_weight=20,
            objective="reg:squarederror",
            tree_method="hist",
            random_state=SEED,
            n_jobs=1,
        )
    elif f == "lightgbm":
        m = LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            num_leaves=p["leaves"],
            reg_lambda=p["l2"],
            min_child_samples=20,
            objective="regression",
            random_state=SEED,
            n_jobs=1,
            deterministic=True,
            force_col_wise=True,
            verbosity=-1,
        )
    else:
        raise ValueError(f"Unknown model family: {f}")
    return Pipeline([("preprocessor", pre), ("model", m)]).fit(
        tr[orig.NUM + orig.CAT], tr[Y]
    )


def predict(c, m, tr, te):
    if c["family"] == "baseline":
        return orig.baseline_predict(c["name"], tr, te)
    if c["family"] == "ar1":
        return m.predict(te[["own_growth"]])
    if c["family"] == "panel_ar1":
        return m.predict(te)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return m.predict(te[orig.NUM + orig.CAT])


def metrics(d, p):
    e = abs(d[Y].to_numpy() - np.asarray(p))
    return {
        "mae": float(e.mean()),
        "wmae": float(np.average(e, weights=d[W])),
        "rmse": float(np.sqrt(np.mean(e * e))),
    }


def ci(d, names, ref, equal_year=False):
    """Region cluster percentile and max-standardized centered simultaneous CI.
    Resampling holds forecasts fixed; no universal multiple-testing correction.
    """
    regs = sorted(d.region_code.unique())
    yrs = sorted(d.target_year.unique()) if equal_year else [None]
    rng = np.random.default_rng(SEED)
    draws = rng.integers(len(regs), size=(10000, len(regs)))
    rows = []
    for metric in ["mae", "wmae"]:
        boot = []
        point = []
        for name in names:
            ds = abs(d[Y] - d[name]) - abs(d[Y] - d[ref])
            weight = d[W] if metric == "wmae" else pd.Series(1.0, index=d.index)
            byear = []
            pyear = []
            for y in yrs:
                mask = (
                    pd.Series(True, index=d.index) if y is None else d.target_year == y
                )
                sums = np.array(
                    [(ds * weight)[mask & (d.region_code == r)].sum() for r in regs]
                )
                ns = np.array([weight[mask & (d.region_code == r)].sum() for r in regs])
                b = sums[draws].sum(1) / ns[draws].sum(1)
                byear.append(b)
                pyear.append(float((ds * weight)[mask].sum() / weight[mask].sum()))
            boot.append(np.mean(byear, axis=0))
            point.append(np.mean(pyear))
        boot = np.array(boot).T
        point = np.array(point)
        sd = boot.std(0, ddof=1)
        sd = np.where(sd < 1e-15, 1e-15, sd)
        critical = float(np.quantile(np.max(abs((boot - point) / sd), axis=1), 0.95))
        for i, n in enumerate(names):
            lo, hi = np.quantile(boot[:, i], [0.025, 0.975])
            rows.append(
                dict(
                    model=n,
                    reference=ref,
                    metric=metric,
                    delta=float(point[i]),
                    ci_lo=float(lo),
                    ci_hi=float(hi),
                    sim_lo=float(point[i] - critical * sd[i]),
                    sim_hi=float(point[i] + critical * sd[i]),
                    family_size=len(names),
                    B=10000,
                    equal_year=equal_year,
                )
            )
    return rows


def run_split(label, tr, va, te, cs, out):
    dest = out / label
    dest.mkdir()
    grid = []
    vp = va.copy()
    for c in cs:
        m = fit(c, tr)
        p = predict(c, m, tr, va)
        vp[c["name"]] = p
        grid.append({**c, **metrics(va, p)})
    original = [c["name"] for c in cs[:20]]
    extended = [c["name"] for c in cs[:32]]
    allnames = [c["name"] for c in cs]
    pools = {
        "baseline6": original[:6],
        "learned14": original[6:],
        "all20": original,
        "learned26": extended[6:],
        "all32": extended,
        "strong_baseline12": original[:6] + allnames[32:],
        "learned32": allnames[6:],
        "all38": allnames,
    }
    for family in sorted({c["family"] for c in cs if c["family"] != "baseline"}):
        pools["family_" + family] = [c["name"] for c in cs if c["family"] == family]
    scores = {g["name"]: g["mae"] for g in grid}
    selected = {
        name: min(pool, key=lambda n: (scores[n], allnames.index(n)))
        for name, pool in pools.items()
    }
    dump(
        dict(
            label=label,
            train_n=len(tr),
            validation_n=len(va),
            test_n=len(te),
            selected=selected,
            selection_uses="validation MAE only",
            retrospective=True,
        ),
        dest / "selection_before_test.json",
    )
    save(
        [{**g, "params": json.dumps(g["params"])} for g in grid],
        dest / "validation_grid.csv",
    )
    save(vp, dest / "validation_predictions.csv")
    tv = pd.concat([tr, va]).sort_values(KEY)
    tp = te.copy()
    lookup = {c["name"]: c for c in cs}
    needed = set(selected.values()) | {
        "global_past_mean",
        "ridge_alpha1000",
        "pooled_ar1",
    }
    for n in allnames:
        if n in needed:
            c = lookup[n]
            m = fit(c, tv)
            tp[n] = predict(c, m, tv, te)
    for name, n in selected.items():
        tp[name] = tp[n]
    save(tp, dest / "predictions.csv")
    rows = [
        dict(split=label, strategy=k, selected_model=v, n=len(te), **metrics(te, tp[k]))
        for k, v in selected.items()
    ]
    save(rows, dest / "metrics.csv")
    print(label, selected["all38"], flush=True)
    return tp, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/benchmark")
    args = ap.parse_args()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Output must be empty")
    out.mkdir(parents=True, exist_ok=True)
    cs = candidates()
    dump(
        dict(
            created_utc=datetime.now(timezone.utc).isoformat(),
            status="retrospective extension; prior test results known",
            candidates=cs,
            seed=SEED,
            selection="unweighted validation MAE; candidate order breaks exact ties",
            fixed_split=[
                list(range(2016, 2020)),
                [2020, 2021, 2022],
                [2023, 2024, 2025],
            ],
            expanding="Y=2020..2025: train2016..Y-2, validationY-1, testY",
            versions={
                n: m.__version__
                for n, m in [
                    ("numpy", np),
                    ("pandas", pd),
                    ("sklearn", sklearn),
                    ("xgboost", xgboost),
                    ("catboost", catboost),
                    ("lightgbm", lightgbm),
                ]
            },
            python=platform.python_version(),
        ),
        out / "protocol_before_fit.json",
    )
    p = read(BASE / "analysis_harmonized/results/main/analysis_panel.csv")
    assert len(p) == 1449 and not p.duplicated(KEY).any()
    fixed, rows = run_split(
        "fixed",
        p[p.split == "train"],
        p[p.split == "validation"],
        p[p.split == "test"],
        cs,
        out,
    )
    comps = [n for n in fixed if n.startswith("family_")]
    save(ci(fixed, comps, "global_past_mean"), out / "fixed_comparisons.csv")
    preds = []
    for y in range(2020, 2026):
        tp, r = run_split(
            str(y),
            p[p.target_year <= y - 2],
            p[p.target_year == y - 1],
            p[p.target_year == y],
            cs,
            out,
        )
        preds.append(tp)
        rows += r
    combined = pd.concat(preds, ignore_index=True)
    save(combined, out / "expanding_predictions.csv")
    save(rows, out / "all_metrics.csv")
    strategies = list(
        json.loads((out / "2020/selection_before_test.json").read_text())["selected"]
    )
    save(
        ci(combined, [s for s in strategies if s != "baseline6"], "baseline6", True),
        out / "expanding_comparisons.csv",
    )
    summary = (
        pd.DataFrame(rows)
        .query("split != 'fixed'")
        .groupby("strategy")[["mae", "wmae", "rmse"]]
        .mean()
        .reset_index()
    )
    save(summary, out / "expanding_summary.csv")
    dump(
        {
            "status": "completed",
            "source_panel_sha256": sha(
                BASE / "analysis_harmonized/results/main/analysis_panel.csv"
            ),
            "fixed_n": len(fixed),
            "expanding_n": len(combined),
            "sample_years_fixed": True,
            "predictions_fixed_in_intervals": True,
            "no_new_independent_holdout": True,
        },
        out / "completion.json",
    )


if __name__ == "__main__":
    main()
