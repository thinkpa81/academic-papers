#!/usr/bin/env python3
"""Retrospective, protocol-recorded forecast diagnostics; see protocol_v1.json.

python run_addendum.py --out /new/output
The default base is the bundled, hash-checked inputs; --base can override it.
No source file is modified. All supplemental candidate and subset results retained.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.linear_model import LinearRegression

KEY = ["target_year", "region_code", "industry_code"]
Y = "target_logpoints"
W = "employment_input_persons"
BASE = "global_past_mean"
RIDGE = "ridge_alpha1000"
MODELS = [BASE, RIDGE, "pooled_ar1", "panel_shrinkage_ar1"]
SEED = 20260926


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(x, p):
    Path(p).write_text(
        json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


def csv(rows, p):
    pd.DataFrame(rows).to_csv(
        p, index=False, encoding="utf-8-sig", float_format="%.17g"
    )


def read(p):
    return pd.read_csv(p, float_precision="round_trip")


class PanelShrinkage:
    """Only categorical deviations penalized; intercept and common slope free."""

    def __init__(self, lam):
        self.lam = lam

    def design(self, d):
        cols = [np.ones(len(d)), d.own_growth.to_numpy(float)]
        cols += [
            (d[c] == v).to_numpy(float)
            for c in ["region_code", "industry_code"]
            for v in self.categories[c]
        ]
        return np.column_stack(cols)

    def fit(self, d):
        self.categories = {
            c: sorted(d[c].unique()) for c in ["region_code", "industry_code"]
        }
        x = self.design(d)
        penalty = np.diag([0.0, 0.0] + [float(self.lam)] * (x.shape[1] - 2))
        self.beta = np.linalg.solve(x.T @ x + penalty, x.T @ d[Y].to_numpy())
        self.feature_names = ["intercept", "own_growth"] + [
            f"{c}={v}"
            for c in ["region_code", "industry_code"]
            for v in self.categories[c]
        ]
        self.edf = float(np.trace(np.linalg.solve(x.T @ x + penalty, x.T @ x)))
        return self

    def predict(self, d):
        return self.design(d) @ self.beta


def metric(d, m):
    y = d[Y].to_numpy()
    p = d[m].to_numpy()
    e = np.abs(y - p)
    return dict(
        n=len(d),
        regions=int(d.region_code.nunique()),
        mae=float(e.mean()),
        median_ae=float(np.median(e)),
        rmse=float(np.sqrt(np.mean((y - p) ** 2))),
        employment_weighted_mae=float(np.average(e, weights=d[W])),
        binary_direction_pct=float(100 * np.mean((y >= 0) == (p >= 0))),
        r2=float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)),
    )


def paired(d, m, ref, permutation=False):
    e = np.abs(d[Y].to_numpy() - d[m].to_numpy())
    r = np.abs(d[Y].to_numpy() - d[ref].to_numpy())
    dif = e - r
    regs = sorted(d.region_code.unique())
    reg = d.region_code.to_numpy()
    sums = np.array([dif[reg == g].sum() for g in regs])
    ns = np.array([(reg == g).sum() for g in regs])
    draws = np.random.default_rng(SEED).integers(0, len(regs), size=(2000, len(regs)))
    boots = sums[draws].sum(axis=1) / ns[draws].sum(axis=1)
    ties = np.isclose(e, r, rtol=0, atol=1e-12)
    result = dict(
        model=m,
        reference=ref,
        n=len(d),
        regions=len(regs),
        delta_mae=float(dif.mean()),
        ci95_lo=float(np.quantile(boots, 0.025)),
        ci95_hi=float(np.quantile(boots, 0.975)),
        strict_win_pct=float(100 * np.mean((e < r) & ~ties)),
        tie_pct=float(100 * np.mean(ties)),
        strict_loss_pct=float(100 * np.mean((e > r) & ~ties)),
        bootstrap_draws=2000,
        seed=SEED,
        conditional_on_observed_years_and_fitted_models=True,
    )
    if permutation:
        signs = (
            2
            * (
                (
                    np.arange(2 ** len(regs), dtype=np.uint32)[:, None]
                    >> np.arange(len(regs))
                )
                & 1
            ).astype(np.int8)
            - 1
        )
        dist = signs @ sums
        result["cluster_sign_flip_two_sided_p"] = float(
            np.mean(np.abs(dist) >= abs(sums.sum()) - 1e-10)
        )
        result["sign_flip_patterns"] = len(dist)
        result["sign_flip_assumptions"] = (
            "independent symmetric region-level paired loss sums; shared shocks may violate; exploratory only"
        )
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--base", type=Path, default=Path(__file__).with_name("bundled_inputs")
    )
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    base = args.base.resolve()
    out = args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Output must be empty")
    out.mkdir(parents=True, exist_ok=True)
    protocol_path = Path(__file__).with_name("protocol_v1.json")
    protocol = json.loads(protocol_path.read_text())
    for name, h in protocol["source_hashes"].items():
        assert sha(base / name) == h, name
    dump(
        dict(
            started_utc=datetime.now(timezone.utc).isoformat(),
            protocol_sha256=sha(protocol_path),
            python=platform.python_version(),
            numpy=np.__version__,
            pandas=pd.__version__,
            scipy=scipy.__version__,
            sklearn=sklearn.__version__,
        ),
        out / "execution_start.json",
    )

    # Original DOM normalization is replayed from byte-identical raw data in isolation.
    src = base / "source_harmonized"
    raw_replay = out / "source_replay"
    raw_replay.mkdir()
    for name in [
        "normalize_harmonized_source.py",
        "kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json",
    ]:
        shutil.copy2(src / name, raw_replay / name)
    norm = subprocess.run(
        [sys.executable, str(raw_replay / "normalize_harmonized_source.py")],
        capture_output=True,
        text=True,
    )
    (out / "normalization_stdout.txt").write_text(
        norm.stdout + norm.stderr, encoding="utf-8"
    )
    raw_check = {
        "exit_code": norm.returncode,
        "raw_dom_sha256": sha(
            raw_replay / "kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json"
        ),
    }
    if norm.returncode:
        raise RuntimeError(norm.stderr)
    checks = []
    for name in [
        "kosis_ksic11_H1_2013_2025_panel.csv",
        "kosis_ksic11_H1_2013_2025_sections.csv",
        "kosis_ksic11_H1_2013_2025_national_panel.csv",
    ]:
        a = read(src / name)
        b = read(raw_replay / name)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        checks.append(
            {
                "file": name,
                "rows": len(a),
                "dataframe_exact_equal": True,
                "byte_equal": sha(src / name) == sha(raw_replay / name),
            }
        )
    raw_check["normalization_checks"] = checks
    spec = importlib.util.spec_from_file_location(
        "original_analysis", base / "analysis_harmonized/run.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    panel_replay = out / "panel_replay"
    panel_replay.mkdir()
    source = read(src / "kosis_ksic11_H1_2013_2025_panel.csv")
    reconstructed, _ = mod.construct_panel(source, panel_replay, True)
    saved = base / "analysis_harmonized/results/main"
    panel = read(saved / "analysis_panel.csv")
    pd.testing.assert_frame_equal(
        panel, reconstructed, check_dtype=False, check_exact=False, rtol=0, atol=1e-12
    )
    tr = panel[panel.split == "train"].copy()
    va = panel[panel.split == "validation"].copy()
    te = panel[panel.split == "test"].copy()
    tv = pd.concat([tr, va], ignore_index=True)
    assert len(tr) == 558 and len(va) == 463 and len(te) == 428
    assert set(tr.target_year) == {2016, 2017, 2018, 2019}
    assert set(va.target_year) == {2020, 2021, 2022} and set(te.target_year) == {
        2023,
        2024,
        2025,
    }
    assert max(tv.target_year) < min(te.target_year)
    tp = read(saved / "test_predictions.csv")
    vp = read(saved / "validation_predictions.csv")
    pd.testing.assert_frame_equal(tp[KEY], te[KEY].reset_index(drop=True))
    fitted, warnings = mod.fit_candidate("ridge", {"alpha": 1000}, tv)
    ridge_replay = fitted.predict(te[mod.NUM + mod.CAT])
    baseline_replay = mod.baseline_predict(BASE, tv, te)
    maxdiff = float(np.max(np.abs(ridge_replay - tp[RIDGE].to_numpy())))
    assert maxdiff < 1e-10 and np.max(np.abs(baseline_replay - tp[BASE])) < 1e-12
    raw_check.update(
        panel_replay_equal_atol=1e-12,
        panel_rows=len(panel),
        split_counts={"train": len(tr), "validation": len(va), "test": len(te)},
        ridge_refit_max_abs_prediction_difference=maxdiff,
        ridge_warnings=warnings,
        baseline_refit_max_abs_prediction_difference=float(
            np.max(np.abs(baseline_replay - tp[BASE]))
        ),
    )
    dump(raw_check, out / "source_replay_checks.json")

    # Validation selection only; additional test predictions are produced afterwards.
    grid = []
    ar = LinearRegression().fit(tr[["own_growth"]], tr[Y])
    vp["pooled_ar1"] = ar.predict(va[["own_growth"]])
    grid.append(dict(model="pooled_ar1", lambda_value=None, **metric(vp, "pooled_ar1")))
    for lam in [1, 10, 100, 1000, 10000]:
        shr = PanelShrinkage(lam).fit(tr)
        col = f"panel_shrinkage_lambda{lam}"
        vp[col] = shr.predict(va)
        grid.append(
            dict(model=col, lambda_value=lam, effective_df=shr.edf, **metric(vp, col))
        )
    best = sorted(
        [g for g in grid if g["lambda_value"] is not None],
        key=lambda g: (g["mae"], g["lambda_value"]),
    )[0]
    selected_lambda = best["lambda_value"]
    selection = dict(
        recorded_utc=datetime.now(timezone.utc).isoformat(),
        validation_counts=len(va),
        selected_lambda=selected_lambda,
        criterion="validation unweighted MAE",
        protocol_sha256=sha(protocol_path),
        new_test_model_losses_inspected_before_selection=False,
        original_test_results_and_external_AR1_estimate_already_known=True,
    )
    dump(selection, out / "selection_before_new_test_predictions.json")
    csv(grid, out / "validation_grid.csv")
    ar = LinearRegression().fit(tv[["own_growth"]], tv[Y])
    shr = PanelShrinkage(selected_lambda).fit(tv)
    tp["pooled_ar1"] = ar.predict(te[["own_growth"]])
    tp["panel_shrinkage_ar1"] = shr.predict(te)
    csv(
        [
            {
                "model": "pooled_ar1",
                "feature": "intercept",
                "coefficient": float(ar.intercept_),
            },
            {
                "model": "pooled_ar1",
                "feature": "own_growth",
                "coefficient": float(ar.coef_[0]),
            },
        ]
        + [
            {"model": "panel_shrinkage_ar1", "feature": f, "coefficient": float(v)}
            for f, v in zip(shr.feature_names, shr.beta)
        ],
        out / "additional_model_coefficients.csv",
    )
    vp["panel_shrinkage_ar1"] = vp[f"panel_shrinkage_lambda{selected_lambda}"]
    csv(vp, out / "validation_predictions.csv")

    lookup = source.set_index(["region_code", "year", "industry_code"]).rse_any_star
    assert lookup.notna().all()
    for yr, label in [("input_year", "input"), ("target_year", "target")]:
        tp[f"component_rse25_flag_{label}"] = [
            bool(lookup.loc[(r, y, i)])
            for r, y, i in tp[["region_code", yr, "industry_code"]].itertuples(
                index=False, name=None
            )
        ]
    tp["component_rse25_flag_either"] = (
        tp.component_rse25_flag_input | tp.component_rse25_flag_target
    )
    csv(tp, out / "test_predictions_additional.csv")

    subsets = {"all": tp}
    for yr in [2023, 2024, 2025]:
        subsets[f"year_{yr}"] = tp[tp.target_year == yr]
    subsets["exclude_2025"] = tp[tp.target_year != 2025]
    subsets["input_ge10000"] = tp[tp[W] >= 10000]
    subsets["input_ge10000_exclude_2025"] = tp[
        (tp[W] >= 10000) & (tp.target_year != 2025)
    ]
    ordered = tp.assign(abs_actual=tp[Y].abs()).sort_values(
        ["abs_actual"] + KEY, ascending=[False, True, True, True], kind="stable"
    )
    trim = []
    for k, label in [
        (1, "top1"),
        (5, "top5"),
        (10, "top10"),
        (math.ceil(0.05 * len(tp)), "top5pct"),
    ]:
        removed = ordered.iloc[:k]
        subsets[f"trim_abs_target_{label}"] = tp.drop(removed.index)
        for row in removed.itertuples():
            trim.append(
                {
                    "rule": label,
                    "removed_n": k,
                    "target_year": row.target_year,
                    "region_code": row.region_code,
                    "industry_code": row.industry_code,
                    "target_logpoints": row.target_logpoints,
                }
            )
    csv(trim, out / "outcome_dependent_trim_ledger.csv")
    for a, b in itertools.product([False, True], repeat=2):
        subsets[f"rse_input_{int(a)}_target_{int(b)}"] = tp[
            (tp.component_rse25_flag_input == a) & (tp.component_rse25_flag_target == b)
        ]
    subsets["rse_either_year_flagged"] = tp[tp.component_rse25_flag_either]
    subsets["rse_neither_year_flagged"] = tp[~tp.component_rse25_flag_either]
    mets = []
    pairs = []
    for name, d in subsets.items():
        if d.empty:
            continue
        for m in MODELS:
            mets.append(dict(subset=name, model=m, **metric(d, m)))
        for m in MODELS[1:]:
            pairs.append(
                dict(subset=name, **paired(d, m, BASE, permutation=name == "all"))
            )
        for m in MODELS[2:]:
            pairs.append(
                dict(subset=name, **paired(d, m, RIDGE, permutation=name == "all"))
            )
    csv(mets, out / "all_metrics.csv")
    csv(pairs, out / "all_paired_comparisons.csv")
    # Identical bootstrap convention reproduces original pooled interval.
    original = (
        read(saved / "region_bootstrap_vs_default.csv").query("model == @RIDGE").iloc[0]
    )
    replay = [
        p
        for p in pairs
        if p["subset"] == "all" and p["model"] == RIDGE and p["reference"] == BASE
    ][0]
    assert abs(replay["delta_mae"] - original.paired_mae_difference) < 1e-12
    assert (
        abs(replay["ci95_lo"] - original.ci_lower) < 1e-12
        and abs(replay["ci95_hi"] - original.ci_upper) < 1e-12
    )
    summary = dict(
        completed_utc=datetime.now(timezone.utc).isoformat(),
        selected_lambda=selected_lambda,
        panel_shrinkage_effective_df=shr.edf,
        source_replay=raw_check,
        overall_metrics=[m for m in mets if m["subset"] == "all"],
        overall_comparisons=[p for p in pairs if p["subset"] == "all"],
        core_sensitivity=[
            p for p in pairs if p["model"] == RIDGE and p["reference"] == BASE
        ],
        interpretation="All new analyses retrospective and exploratory; no model promotion; null intervals are not equivalence proof; no independent future test or human-use evaluation.",
    )
    dump(summary, out / "summary.json")
    manifest = [
        {"path": str(p.relative_to(out)), "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in sorted(out.rglob("*"))
        if p.is_file()
    ]
    dump(manifest, out / "manifest.json")
    print(
        json.dumps(
            {
                "selected_lambda": selected_lambda,
                "source_replay": raw_check,
                "overall_metrics": summary["overall_metrics"],
                "overall_comparisons": summary["overall_comparisons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
