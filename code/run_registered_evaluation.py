#!/usr/bin/env python3
"""Refit independent reference records, then replay known probes and generated
perturbations. All evaluation is internal and formative; no human observations.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from registered_guard import SNAP, load_original, validate
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "support"
BASE = REF / "baseline/base_v11"


def module(name, p):
    s = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


orig = module("reg_orig", BASE / "analysis_harmonized/run.py")


def read(p):
    return pd.read_csv(p, float_precision="round_trip")


def dump(o, p):
    p.write_text(
        json.dumps(o, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest(o):
    return hashlib.sha256(
        json.dumps(
            o,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def bind(e):
    h = digest(
        {
            k: v
            for k, v in e["card"].items()
            if k not in {"decision_basis_sha256", "historical_outcome_audit"}
        }
    )
    e["card"]["decision_basis_sha256"] = h
    e["review"]["evidence_sha256"] = h
    e["receipt"] = {"card_sha256": h, "request_sha256": digest(e["request"])}
    e["current_state"] = dict(e["receipt"])


def registry():
    panel = read(BASE / "analysis_harmonized/results/main/analysis_panel.csv")
    tr = panel[panel.split == "train"]
    va = panel[panel.split == "validation"]
    tv = panel[panel.split != "test"]
    te = panel[panel.target_year == 2025].copy()
    ridge = orig.fit_candidate("ridge", {"alpha": 1000}, tv)[0]
    ar = LinearRegression().fit(tv[["own_growth"]], tv.target_logpoints)
    rv = orig.fit_candidate("ridge", {"alpha": 1000}, tr)[0]
    av = LinearRegression().fit(tr[["own_growth"]], tr.target_logpoints)
    vp = {
        "ridge_alpha1000": rv.predict(va[orig.NUM + orig.CAT]),
        "pooled_ar1": av.predict(va[["own_growth"]]),
    }
    bp = orig.baseline_predict("global_past_mean", tr, va)
    predictions = {
        "ridge_alpha1000": ridge.predict(te[orig.NUM + orig.CAT]),
        "pooled_ar1": ar.predict(te[["own_growth"]]),
    }
    baselines = orig.baseline_predict("global_past_mean", tv, te)
    pre = ridge.named_steps["preprocessor"]
    lin = ridge.named_steps["model"]
    x = pre.transform(te[orig.NUM + orig.CAT])
    names = list(pre.get_feature_names_out())
    inp = REF / "model_swap_addendum/input"
    models = {
        "ridge_alpha1000": {
            "artifact_sha256": sha(inp / "model_ridge_alpha1000.joblib"),
            "intercept": float(lin.intercept_),
            "parameters": dict(zip(names, map(float, lin.coef_))),
        },
        "pooled_ar1": {
            "artifact_sha256": sha(inp / "additional_model_coefficients.csv"),
            "intercept": float(ar.intercept_),
            "parameters": {"own_growth": float(ar.coef_[0])},
        },
    }
    records = {}
    for i, (_, r) in enumerate(te.iterrows()):
        mask = (va.region_code == r.region_code) & (va.industry_code == r.industry_code)
        n = int(mask.sum())
        for m in models:
            a = (
                float(np.mean(abs(va.target_logpoints.to_numpy()[mask] - bp[mask])))
                if n
                else None
            )
            b = (
                float(np.mean(abs(va.target_logpoints.to_numpy()[mask] - vp[m][mask])))
                if n
                else None
            )
            pv = {
                "validation_cell_n": n,
                "validation_year_n": n,
                "validation_years": ";".join(str(y) for y in va[mask].target_year),
                "aggregate_baseline_mae": a,
                "aggregate_learned_mae": b,
                "aggregate_mae_difference": b - a if n else None,
                "model": m,
            }
            if m == "ridge_alpha1000":
                terms = {
                    f: {
                        "input_value": float(r[f]),
                        "transformed_input_value": float(x[i, j]),
                        "coefficient": float(lin.coef_[j]),
                        "contribution_logpoints": float(x[i, j] * lin.coef_[j]),
                    }
                    for j, f in enumerate(orig.NUM)
                }
                for f in orig.CAT:
                    terms[f] = {
                        "input_value": str(r[f]),
                        "contribution_logpoints": float(
                            sum(
                                x[i, j] * lin.coef_[j]
                                for j, k in enumerate(names)
                                if k.startswith("cat__" + f + "_")
                            )
                        ),
                    }
            else:
                terms = {
                    "own_growth": {
                        "input_value": float(r.own_growth),
                        "transformed_input_value": float(r.own_growth),
                        "coefficient": float(ar.coef_[0]),
                        "contribution_logpoints": float(r.own_growth * ar.coef_[0]),
                    }
                }
            records[f"{r.region_code}:{r.industry_code}:2025:{m}"] = {
                "prediction": float(predictions[m][i]),
                "baseline": float(baselines[i]),
                "employment": float(r.employment_input_persons),
                "terms": terms,
                "validation": pv,
            }
    return {
        "registry_id": "KITS-20261025-registered-linear-v3",
        "source_panel_sha256": sha(
            BASE / "analysis_harmonized/results/main/analysis_panel.csv"
        ),
        "construction": "reference records refitted from data; no case expectation labels used",
        "trust_assumption": "registry loaded separately by trusted caller; no issuer authentication implemented",
        "models": models,
        "records": records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/registered_service")
    a = ap.parse_args()
    out = a.out.resolve()
    if out.exists():
        raise RuntimeError("Use a new output directory")
    out.mkdir(parents=True)
    reg = registry()
    dump(reg, out / "trusted_registry.json")
    source = REF / "model_swap_addendum/frozen/protocol_and_cases.json"
    cases = json.loads(source.read_text())["cases"]
    rng = np.random.default_rng(20261025)
    controls = [c for c in cases if c["scope"] == "coherent_control"]
    generated = []
    for i in range(400):
        c = copy.deepcopy(controls[int(rng.integers(len(controls)))])
        e = c["fixture"]
        family = i % 4
        delta = float(rng.uniform(0.01, 10))
        if family == 0:
            e["card"]["model_artifact_snapshot"]["parameters"][0]["coefficient"] += (
                delta
            )
        elif family == 1:
            e["card"]["linear_explanation"]["contributions"][0]["input_value"] += delta
        elif family == 2:
            e["card"]["prior_validation"]["model"] = "unregistered-model"
            e["card"]["validation_display"]["model"] = "unregistered-model"
        else:
            e["card"]["model_artifact_snapshot"]["artifact_sha256"] = "f" * 64
        bind(e)
        c.update(
            case_id=f"G{i:04d}",
            scope="generated_mutations",
            family=f"G{family}",
            expected="structured_block",
        )
        generated.append(c)
    # Benign serialization changes must preserve acceptance.
    for i, c0 in enumerate(controls):
        c = copy.deepcopy(c0)
        c["fixture"] = json.loads(json.dumps(c["fixture"], sort_keys=True))
        c.update(case_id=f"M{i:04d}", scope="serialization_controls", expected="permit")
        generated.append(c)
    allcases = cases + generated
    dump(
        {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "known_failures_used_to_design_repair": True,
            "human_participants": 0,
            "external_evaluator": False,
            "seed": 20261025,
            "cases": allcases,
        },
        out / "cases_before_execution.json",
    )
    modules = load_original(SNAP / "source_snapshot")
    rows = []
    for c in allcases:
        r = validate(copy.deepcopy(c["fixture"]), reg, modules)
        observed = "permit" if r["research_review_permitted"] else "structured_block"
        rows.append(
            {
                "case_id": c["case_id"],
                "scope": c["scope"],
                "family": c["family"],
                "model": c["model"],
                "expected": c["expected"],
                "observed": observed,
                "matches": observed == c["expected"],
                "codes": ";".join(x["code"] for x in r["errors"]),
            }
        )
        assert r["automatic_policy_action_allowed"] is False
    pd.DataFrame(rows).to_csv(
        out / "case_results.csv", index=False, encoding="utf-8-sig"
    )
    groups = [
        {
            "scope": s,
            "n": len(g),
            "matching": int(g.matches.sum()),
            "permit": int((g.observed == "permit").sum()),
            "block": int((g.observed == "structured_block").sum()),
        }
        for s, g in pd.DataFrame(rows).groupby("scope", sort=False)
    ]
    dump(
        {
            "groups": groups,
            "human_participants": 0,
            "registry_records": len(reg["records"]),
            "independent_external_validation": False,
            "known_case_sha256": sha(source),
            "implementation_sha256": sha(
                Path(__file__).with_name("registered_guard.py")
            ),
        },
        out / "summary.json",
    )
    print(json.dumps(groups, indent=2))
    assert all(r["matches"] for r in rows), (
        "Inspect failed cases; do not relabel expectations."
    )


if __name__ == "__main__":
    main()
