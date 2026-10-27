from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import HuberRegressor, Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 20260926
NUM = [
    "log_employment",
    "industry_share_pct",
    "own_growth",
    "own_growth_lag1",
    "peer_industry_growth",
    "region_total_growth",
]
CAT = ["region_code", "industry_code"]
INDUSTRIES = ["A", "BTE", "F", "GTI", "J", "K", "L", "M_N", "OTQ", "RTU"]
BOUNDARIES = {"KR053": [2017], "KR031": [2024], "KR032": [2024]}
REGIONS = {
    "KR011": "서울",
    "KR012": "인천",
    "KR013": "경기",
    "KR021": "부산",
    "KR022": "울산",
    "KR023": "경남",
    "KR031": "대구",
    "KR032": "경북",
    "KR041": "광주",
    "KR042": "전북",
    "KR043": "전남",
    "KR051": "대전",
    "KR052": "충북",
    "KR053": "충남",
    "KR054": "세종",
    "KR061": "강원",
    "KR071": "제주",
}
SUPERREGION = {
    "KR011": "수도권",
    "KR012": "수도권",
    "KR013": "수도권",
    "KR021": "동남권",
    "KR022": "동남권",
    "KR023": "동남권",
    "KR031": "대경권",
    "KR032": "대경권",
    "KR041": "호남권",
    "KR043": "호남권",
    "KR042": "전북",
    "KR051": "충청권",
    "KR052": "충청권",
    "KR053": "충청권",
    "KR054": "충청권",
    "KR061": "강원",
    "KR071": "제주",
}
BASELINES = [
    "zero",
    "last_growth",
    "industry_past_mean",
    "global_past_mean",
    "global_past_median",
    "lagged_available_region_industry_growth",
]


def dump(obj, p):
    Path(p).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def good(v):
    return pd.notna(v) and np.isfinite(v) and (v > 0)


def construct_panel(source: pd.DataFrame, out: Path, boundary_filter: bool):
    source = source[source.region_code.isin(REGIONS)].copy()
    source["employment_persons"] = pd.to_numeric(
        source.employment_persons, errors="coerce"
    )
    if source.duplicated(["region_code", "year", "industry_code"]).any():
        raise ValueError("Duplicate source region/year/industry")
    d = source.set_index(
        ["region_code", "year", "industry_code"]
    ).employment_persons.to_dict()

    def E(r, y, i):
        return d.get((r, y, i), np.nan)

    def bad(r, y):
        return boundary_filter and y in BOUNDARIES.get(r, [])

    rows = []
    ledgers = []
    for r in REGIONS:
        for i in INDUSTRIES:
            for y in range(2016, 2026):
                issues = []
                vals = [E(r, k, i) for k in [y, y - 1, y - 2, y - 3]]
                for k, v in zip([y, y - 1, y - 2, y - 3], vals):
                    if not good(v):
                        issues.append(f"own_employment_missing_or_nonpositive:{k}")
                totals = [E(r, y - 1, "_T"), E(r, y - 2, "_T")]
                for k, v in zip([y - 1, y - 2], totals):
                    if not good(v):
                        issues.append(f"official_total_missing_or_nonpositive:{k}")
                hit = [k for k in [y, y - 1, y - 2] if bad(r, k)]
                issues += [f"source_boundary_transition:{k}" for k in hit]
                peer = [
                    rr
                    for rr in REGIONS
                    if rr != r
                    and (not bad(rr, y - 1))
                    and good(E(rr, y - 1, i))
                    and good(E(rr, y - 2, i))
                ]
                common = [
                    rr
                    for rr in REGIONS
                    if not bad(rr, y - 1)
                    and good(E(rr, y - 1, i))
                    and good(E(rr, y - 2, i))
                ]
                if not peer:
                    issues.append("no_valid_peers")
                if not common:
                    issues.append("no_valid_regions_for_aggregate")
                ledgers.append(
                    {
                        "region_code": r,
                        "region_name_ko": REGIONS[r],
                        "industry_code": i,
                        "target_year": y,
                        "eligible": not issues,
                        "exclusion_reasons": ";".join(issues),
                        "peer_region_count": len(peer),
                        "aggregate_region_count": len(common),
                        "source_boundary_transition": ";".join(map(str, hit)),
                    }
                )
                if issues:
                    continue
                target, ei, eii, eiii = vals
                g = 100 * np.log(ei / eii)
                gprev = 100 * np.log(eii / eiii)
                peercur = sum((E(rr, y - 1, i) for rr in peer))
                peerprev = sum((E(rr, y - 2, i) for rr in peer))
                natcur = sum((E(rr, y - 1, i) for rr in common))
                natprev = sum((E(rr, y - 2, i) for rr in common))
                rows.append(
                    {
                        "region_code": r,
                        "region_name_ko": REGIONS[r],
                        "superregion": SUPERREGION[r],
                        "industry_code": i,
                        "target_year": y,
                        "input_year": y - 1,
                        "reference_half": 1,
                        "target_logpoints": 100 * np.log(target / ei),
                        "employment_input_persons": ei,
                        "employment_target_persons": target,
                        "official_total_input_persons": totals[0],
                        "log_employment": np.log(ei),
                        "industry_share_pct": 100 * ei / totals[0],
                        "own_growth": g,
                        "own_growth_lag1": gprev,
                        "peer_industry_growth": 100 * np.log(peercur / peerprev),
                        "region_total_growth": 100 * np.log(totals[0] / totals[1]),
                        "lagged_available_region_industry_growth": 100
                        * np.log(natcur / natprev),
                        "peer_region_count": len(peer),
                        "peer_region_codes": ";".join(peer),
                        "aggregate_region_count": len(common),
                        "split": "train"
                        if y <= 2019
                        else "validation"
                        if y <= 2022
                        else "test",
                    }
                )
    p = (
        pd.DataFrame(rows)
        .sort_values(["target_year", "region_code", "industry_code"])
        .reset_index(drop=True)
    )
    ledger = pd.DataFrame(ledgers).sort_values(
        ["target_year", "region_code", "industry_code"]
    )
    if not np.isfinite(
        p[
            NUM + ["target_logpoints", "lagged_available_region_industry_growth"]
        ].to_numpy()
    ).all():
        raise ValueError("Non-finite model design")
    p.to_csv(out / "analysis_panel.csv", index=False, encoding="utf-8-sig")
    ledger.to_csv(out / "exclusion_ledger.csv", index=False, encoding="utf-8-sig")
    reason = (
        ledger[~ledger.eligible]
        .assign(reason=ledger[~ledger.eligible].exclusion_reasons.str.split(";"))
        .explode("reason")
        .groupby("reason")
        .size()
        .rename("rows")
        .reset_index()
    )
    reason.to_csv(
        out / "exclusion_reason_counts.csv", index=False, encoding="utf-8-sig"
    )
    counts = (
        p.groupby(["split", "target_year"])
        .agg(
            rows=("target_logpoints", "size"),
            regions=("region_code", "nunique"),
            industries=("industry_code", "nunique"),
        )
        .reset_index()
    )
    counts.to_csv(out / "cohort_counts.csv", index=False, encoding="utf-8-sig")
    return (p, ledger)


def baseline_predict(name, tr, ev):
    y = tr.target_logpoints
    if name == "zero":
        return np.zeros(len(ev))
    if name == "last_growth":
        return ev.own_growth.to_numpy()
    if name == "industry_past_mean":
        return (
            ev.industry_code.map(tr.groupby("industry_code").target_logpoints.mean())
            .fillna(y.mean())
            .to_numpy()
        )
    if name == "global_past_mean":
        return np.repeat(y.mean(), len(ev))
    if name == "global_past_median":
        return np.repeat(y.median(), len(ev))
    if name == "lagged_available_region_industry_growth":
        return ev[name].to_numpy()
    raise ValueError(name)


def candidates():
    c = []
    for a in [1, 10, 100, 1000, 10000]:
        c.append((f"ridge_alpha{a}", "ridge", {"alpha": a}))
    for depth in [4, 8]:
        for leaf in [10, 25]:
            c.append(
                (
                    f"rf_depth{depth}_leaf{leaf}",
                    "random_forest",
                    {
                        "n_estimators": 300,
                        "max_depth": depth,
                        "min_samples_leaf": leaf,
                        "random_state": SEED,
                        "n_jobs": 1,
                    },
                )
            )
    for leaves in [7, 15]:
        for l2 in [1, 10]:
            c.append(
                (
                    f"hgb_leaves{leaves}_l2{l2}",
                    "hist_gradient_boosting",
                    {
                        "max_iter": 200,
                        "learning_rate": 0.05,
                        "max_leaf_nodes": leaves,
                        "l2_regularization": l2,
                        "min_samples_leaf": 20,
                        "early_stopping": False,
                        "random_state": SEED,
                    },
                )
            )
    c.append(
        (
            "huber",
            "huber",
            {"epsilon": 1.35, "alpha": 0.0001, "max_iter": 2000, "tol": 1e-06},
        )
    )
    return c


def fit_candidate(family, params, tr):
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT),
        ],
        sparse_threshold=0,
    )
    model = {
        "ridge": Ridge,
        "random_forest": RandomForestRegressor,
        "hist_gradient_boosting": HistGradientBoostingRegressor,
        "huber": HuberRegressor,
    }[family](**params)
    pipe = Pipeline([("preprocessor", pre), ("model", model)])
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        pipe.fit(tr[NUM + CAT], tr.target_logpoints)
    return (
        pipe,
        [{"category": v.category.__name__, "message": str(v.message)} for v in w],
    )


def metrics(y, p, w):
    y = np.asarray(y)
    p = np.asarray(p)
    w = np.asarray(w)
    return {
        "n": int(len(y)),
        "mae": float(np.mean(np.abs(y - p))),
        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
        "employment_weighted_mae": float(np.average(np.abs(y - p), weights=w)),
        "r2": float(r2_score(y, p)) if len(y) > 1 else None,
        "direction_threeway_pct": float(100 * np.mean(np.sign(y) == np.sign(p))),
        "direction_nonnegative_binary_pct": float(100 * np.mean((y >= 0) == (p >= 0))),
    }


def bootstrap(predictions, reference, models, outfile):
    rng = np.random.default_rng(SEED)
    regions = sorted(predictions.region_code.unique())
    err = {
        m: np.abs(predictions.target_logpoints.to_numpy() - predictions[m].to_numpy())
        for m in [reference] + models
    }
    sums = {
        m: np.array(
            [err[m][predictions.region_code.to_numpy() == r].sum() for r in regions]
        )
        for m in err
    }
    ns = np.array([(predictions.region_code == r).sum() for r in regions])
    draws = rng.integers(0, len(regions), size=(2000, len(regions)))
    out = []
    for m in models:
        dif = (sums[m][draws].sum(axis=1) - sums[reference][draws].sum(axis=1)) / ns[
            draws
        ].sum(axis=1)
        out.append(
            {
                "model": m,
                "reference": reference,
                "n_regions": len(regions),
                "resamples": 2000,
                "paired_mae_difference": float(np.mean(err[m] - err[reference])),
                "ci_lower": float(np.quantile(dif, 0.025)),
                "ci_upper": float(np.quantile(dif, 0.975)),
                "conditional_on_observed_years": True,
            }
        )
    pd.DataFrame(out).to_csv(outfile, index=False, encoding="utf-8-sig")
    return out


def run_cohort(source, out, boundary_filter, source_hash):
    out.mkdir(parents=True, exist_ok=True)
    p, ledger = construct_panel(source, out, boundary_filter)
    tr = p[p.split == "train"].copy()
    va = p[p.split == "validation"].copy()
    te = p[p.split == "test"].copy()
    if min(map(len, [tr, va, te])) == 0:
        raise ValueError("Empty split")
    vp = va.copy()
    validation = []
    warnings_log = []
    for name in BASELINES:
        vp[name] = baseline_predict(name, tr, va)
        validation.append(
            {
                "candidate": name,
                "family": "baseline",
                "params_json": "{}",
                **metrics(va.target_logpoints, vp[name], va.employment_input_persons),
            }
        )
    configs = {}
    for name, family, params in candidates():
        print(f"{out.name}: validate {name}", flush=True)
        pipe, warn = fit_candidate(family, params, tr)
        vp[name] = pipe.predict(va[NUM + CAT])
        configs[name] = (family, params)
        warnings_log.append(
            {
                "stage": "validation",
                "candidate": name,
                "warnings": warn,
                "iterations": int(pipe.named_steps["model"].n_iter_)
                if getattr(pipe.named_steps["model"], "n_iter_", None) is not None
                and np.ndim(pipe.named_steps["model"].n_iter_) == 0
                else None,
            }
        )
        validation.append(
            {
                "candidate": name,
                "family": family,
                "params_json": json.dumps(params, sort_keys=True),
                **metrics(va.target_logpoints, vp[name], va.employment_input_persons),
            }
        )
    vd = pd.DataFrame(validation)
    vd.to_csv(out / "validation_grid.csv", index=False, encoding="utf-8-sig")
    vp.to_csv(out / "validation_predictions.csv", index=False, encoding="utf-8-sig")
    baseline_best = (
        vd[vd.family == "baseline"].sort_values("mae", kind="stable").iloc[0].candidate
    )
    learned_best = (
        vd[vd.family != "baseline"].sort_values("mae", kind="stable").iloc[0].candidate
    )
    families = {
        f: vd[vd.family == f].sort_values("mae", kind="stable").iloc[0].candidate
        for f in ["ridge", "random_forest", "hist_gradient_boosting", "huber"]
    }
    selected = list(
        dict.fromkeys(BASELINES + list(families.values()) + ["ridge_alpha100"])
    )
    selection = {
        "selected_utc": now(),
        "source_sha256": source_hash,
        "protocol_sha256": sha(Path(__file__).with_name("protocol.md")),
        "boundary_filter": boundary_filter,
        "service_default_baseline": baseline_best,
        "learned_companion": learned_best,
        "family_selected": families,
        "test_models": selected,
        "test_evaluation_performed_before_selection_record": False,
        "selection_metric": "validation unweighted MAE",
        "train_years": [2016, 2017, 2018, 2019],
        "validation_years": [2020, 2021, 2022],
        "test_years": [2023, 2024, 2025],
        "counts": {"train": len(tr), "validation": len(va), "test": len(te)},
        "model_default_rule": "best validation baseline, paired learned companion, no automatic promotion",
    }
    dump(selection, out / "selection_before_test.json")
    tv = pd.concat([tr, va]).copy()
    tp = te.copy()
    fitted = {}
    for name in selected:
        if name in BASELINES:
            tp[name] = baseline_predict(name, tv, te)
        else:
            print(f"{out.name}: refit {name}", flush=True)
            family, params = configs[name]
            pipe, warn = fit_candidate(family, params, tv)
            warnings_log.append(
                {
                    "stage": "refit",
                    "candidate": name,
                    "warnings": warn,
                    "iterations": int(pipe.named_steps["model"].n_iter_)
                    if getattr(pipe.named_steps["model"], "n_iter_", None) is not None
                    and np.ndim(pipe.named_steps["model"].n_iter_) == 0
                    else None,
                }
            )
            fitted[name] = pipe
            tp[name] = pipe.predict(te[NUM + CAT])
            joblib.dump(pipe, out / f"model_{name}.joblib")
    tp.to_csv(out / "test_predictions.csv", index=False, encoding="utf-8-sig")
    met = []
    for name in selected:
        for label, df in [("pooled", tp)] + [
            (str(y), tp[tp.target_year == y]) for y in [2023, 2024, 2025]
        ]:
            if len(df):
                met.append(
                    {
                        "model": name,
                        "period": label,
                        **metrics(
                            df.target_logpoints, df[name], df.employment_input_persons
                        ),
                    }
                )
    pd.DataFrame(met).to_csv(
        out / "test_metrics.csv", index=False, encoding="utf-8-sig"
    )
    small = []
    for name in selected:
        for label, df in [
            ("input_employment_ge10000", tp[tp.employment_input_persons >= 10000]),
            ("input_employment_lt10000", tp[tp.employment_input_persons < 10000]),
        ]:
            if len(df):
                small.append(
                    {
                        "model": name,
                        "subset": label,
                        **metrics(
                            df.target_logpoints, df[name], df.employment_input_persons
                        ),
                    }
                )
    pd.DataFrame(small).to_csv(
        out / "small_cell_sensitivity.csv", index=False, encoding="utf-8-sig"
    )
    comp = [m for m in selected if m != baseline_best]
    cis = bootstrap(tp, baseline_best, comp, out / "region_bootstrap_vs_default.csv")
    if baseline_best != "zero":
        bootstrap(
            tp,
            "zero",
            [m for m in selected if m != "zero"],
            out / "region_bootstrap_vs_zero.csv",
        )
    coefficients = []
    for name, pipe in fitted.items():
        model = pipe.named_steps["model"]
        if hasattr(model, "coef_"):
            names = pipe.named_steps["preprocessor"].get_feature_names_out()
            for feature, coef in zip(names, model.coef_):
                coefficients.append(
                    {
                        "model": name,
                        "feature": feature,
                        "standardized_design_coefficient": float(coef),
                        "coefficient_scale": "logpoints per training+validation SD for numeric, indicator logpoints for categories",
                    }
                )
    pd.DataFrame(coefficients).to_csv(
        out / "coefficients.csv", index=False, encoding="utf-8-sig"
    )
    service = []
    for (sr, i), df in vp.groupby(["superregion", "industry_code"]):
        a = np.abs(df.target_logpoints - df[baseline_best]).mean()
        b = np.abs(df.target_logpoints - df[learned_best]).mean()
        service.append(
            {
                "superregion": sr,
                "industry_code": i,
                "validation_n": len(df),
                "validation_start": 2020,
                "validation_end": 2022,
                "baseline_model": baseline_best,
                "learned_model": learned_best,
                "baseline_mae": float(a),
                "learned_mae": float(b),
                "learned_worse_than_default": bool(b > a),
                "warning_source": "training-fitted validation only; no test outcome used",
            }
        )
    pd.DataFrame(service).to_csv(
        out / "service_prior_validation_evidence.csv", index=False, encoding="utf-8-sig"
    )
    dump(warnings_log, out / "fit_warnings.json")
    dump(
        {
            "completed_utc": now(),
            "selection_file_sha256": sha(out / "selection_before_test.json"),
            "cohort_counts": selection["counts"],
            "default": baseline_best,
            "learned_companion": learned_best,
            "pooled_metrics": [m for m in met if m["period"] == "pooled"],
            "bootstrap_vs_default": cis,
            "boundary_filter": boundary_filter,
            "source_vintage": "current KSIC11 backcast, not original information vintage",
        },
        out / "summary.json",
    )
    return (p, tp, selection)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    ap.add_argument("--only", choices=["main", "sensitivity", "both"], default="both")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(args.source, float_precision="round_trip")
    if not set(["region_code", "year", "industry_code", "employment_persons"]).issubset(
        source
    ):
        raise ValueError(f"Unexpected columns {list(source)}")
    if "half" in source and set(source["half"].dropna().unique()) != {1}:
        raise ValueError("Mixed half-year source")
    dump(
        {
            "created_utc": now(),
            "source_path": str(args.source.resolve()),
            "source_sha256": sha(args.source),
            "source_years": sorted(map(int, source.year.unique())),
            "source_rows": len(source),
            "boundaries": BOUNDARIES,
            "boundary_exclusions_are_conservative_unverified_backcast_gate": True,
            "missing_is_never_zero": True,
            "target_reference_interval_months": 12,
            "old_model_coefficients_reused": False,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
        args.out / "source_gate.json",
    )
    if args.only in ["main", "both"]:
        run_cohort(source, args.out / "main", True, sha(args.source))
    if args.only in ["sensitivity", "both"]:
        run_cohort(source, args.out / "no_boundary_exclusion", False, sha(args.source))
    files = [
        {
            "relative_path": str(p.relative_to(args.out)),
            "bytes": p.stat().st_size,
            "sha256": sha(p),
        }
        for p in sorted(args.out.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    ]
    dump(files, args.out / "manifest.json")


if __name__ == "__main__":
    main()
