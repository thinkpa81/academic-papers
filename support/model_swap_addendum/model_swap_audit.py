#!/usr/bin/env python3
"""Freeze then execute an internal model-swap contract audit of unchanged v2.

Actual saved forecasts/coefficients are used. Review records remain synthetic.
This is not an independent human evaluation or an untouched empirical holdout.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
NUM = [
    "log_employment",
    "industry_share_pct",
    "own_growth",
    "own_growth_lag1",
    "peer_industry_growth",
    "region_total_growth",
]
CAT = ["region_code", "industry_code"]
MODELS = ["ridge_alpha1000", "pooled_ar1"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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


def dump(o, p):
    Path(p).write_text(
        json.dumps(o, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read(p):
    return pd.read_csv(p, float_precision="round_trip")


def direction(v):
    return "증가" if v > 0.5 else "감소" if v < -0.5 else "유지 범위"


def band(v):
    return "상회" if v > 0.5 else "하회" if v < -0.5 else "근접"


def bind(e):
    c = e["card"]
    h = digest(
        {
            k: v
            for k, v in c.items()
            if k not in {"decision_basis_sha256", "historical_outcome_audit"}
        }
    )
    c["decision_basis_sha256"] = h
    e["review"]["evidence_sha256"] = h
    e["receipt"] = {"card_sha256": h, "request_sha256": digest(e["request"])}
    e["current_state"] = dict(e["receipt"])


def table(rows, p):
    with Path(p).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def validation(v, region, industry, model):
    d = v[(v.region_code == region) & (v.industry_code == industry)].sort_values(
        "target_year"
    )
    assert d.target_year.is_unique and (d.target_year <= 2022).all()
    n = len(d)
    a = float(np.mean(abs(d.target_logpoints - d.global_past_mean))) if n else None
    b = float(np.mean(abs(d.target_logpoints - d[model]))) if n else None
    matches = (
        int(
            (
                np.sign(d[model] - d.global_past_mean)
                == np.sign(d.target_logpoints - d.global_past_mean)
            ).sum()
        )
        if n
        else 0
    )
    return {
        "validation_cell_n": n,
        "validation_year_n": n,
        "validation_years": ";".join(str(y) for y in d.target_year),
        "deviation_sign_matches": matches,
        "deviation_sign_accuracy_pct": 100 * matches / n if n else None,
        "aggregate_baseline_mae": a,
        "aggregate_learned_mae": b,
        "aggregate_mae_difference": b - a if n else None,
        "cell_baseline_mae": a,
        "cell_learned_mae": b,
        "cell_mae_difference": b - a if n else None,
        "validation_composition_rule": "해당 지역·산업의 2020–2022년 가용 관측; 각 연도 한 관측",
        "model": model,
        "prediction_source": "input/validation_predictions.csv",
    }


def build():
    inp = HERE / "input"
    t = read(inp / "test_predictions_additional.csv")
    v = read(inp / "validation_predictions.csv")
    t = (
        t[t.target_year == 2025]
        .sort_values(["region_code", "industry_code"])
        .reset_index(drop=True)
    )
    assert len(t) == 136
    template = json.loads((inp / "template_envelope.json").read_text())
    ridge = joblib.load(inp / "model_ridge_alpha1000.joblib")
    pre = ridge.named_steps["preprocessor"]
    lin = ridge.named_steps["model"]
    design = np.asarray(pre.transform(t[NUM + CAT]))
    names = list(pre.get_feature_names_out())
    coefficients = (
        read(inp / "additional_model_coefficients.csv")
        .query("model == 'pooled_ar1'")
        .set_index("feature")
        .coefficient
    )
    ar_intercept = float(coefficients["intercept"])
    ar_coef = float(coefficients["own_growth"])
    artifacts = {
        "ridge_alpha1000": {
            "model": "ridge_alpha1000",
            "artifact_path": "input/model_ridge_alpha1000.joblib",
            "artifact_sha256": sha(inp / "model_ridge_alpha1000.joblib"),
            "fitted_target_years": "2016–2022",
            "intercept": float(lin.intercept_),
            "parameters": [
                {"feature": str(n), "coefficient": float(b)}
                for n, b in zip(names, lin.coef_)
            ],
        },
        "pooled_ar1": {
            "model": "pooled_ar1",
            "artifact_path": "input/additional_model_coefficients.csv",
            "artifact_sha256": sha(inp / "additional_model_coefficients.csv"),
            "fitted_target_years": "2016–2022",
            "intercept": ar_intercept,
            "parameters": [{"feature": "own_growth", "coefficient": ar_coef}],
        },
    }
    source_manifest = {
        str(p.relative_to(HERE)): sha(p) for p in sorted(inp.iterdir()) if p.is_file()
    }
    envelopes = {}
    checks = []
    for i, r in t.iterrows():
        for model in MODELS:
            e = copy.deepcopy(template)
            c = e["card"]
            pred = float(r[model])
            baseline = float(r.global_past_mean)
            c.update(
                evidence_id=f"{r.region_code}:{r.industry_code}:2025:{model}",
                example_selection_rule="2025년 평가표본 전체 136개 셀; 결과값에 의한 선별 없음",
                region_code=r.region_code,
                region_name=r.region_name_ko,
                industry_code=r.industry_code,
                industry_name=r.industry_code,
                employment_input_persons=float(r.employment_input_persons),
            )
            c["default_estimate"]["logpoints"] = baseline
            c["default_estimate"]["raw_direction_for_statistical_audit"] = direction(
                baseline
            )
            c["learned_comparator"].update(
                model=model,
                model_label="릿지 회귀 비교모형"
                if model == MODELS[0]
                else "통합 일차 자기회귀 비교모형",
                logpoints=pred,
                direction=direction(pred),
            )
            c["relative_deviation"].update(
                definition="표시된 비교모형 예측값 − 전체 과거평균 기준모형 예측값",
                logpoints=pred - baseline,
                **{"class": band(pred - baseline)},
            )
            pv = validation(v, r.region_code, r.industry_code, model)
            c["prior_validation"] = pv
            c["validation_display"].update(
                validation_year_n=pv["validation_year_n"],
                mae_difference=pv["aggregate_mae_difference"],
                model=model,
            )
            if model == MODELS[0]:
                terms = []
                products = design[i] * lin.coef_
                for j, feature in enumerate(NUM):
                    terms.append(
                        {
                            "feature": feature,
                            "input_value": float(r[feature]),
                            "transformed_input_value": float(design[i, j]),
                            "coefficient": float(lin.coef_[j]),
                            "contribution_logpoints": float(products[j]),
                        }
                    )
                for feature in CAT:
                    idx = [
                        j
                        for j, n in enumerate(names)
                        if n.startswith("cat__" + feature + "_")
                    ]
                    terms.append(
                        {
                            "feature": feature,
                            "input_value": str(r[feature]),
                            "contribution_logpoints": float(products[idx].sum()),
                        }
                    )
                intercept = float(lin.intercept_)
            else:
                intercept = ar_intercept
                terms = [
                    {
                        "feature": "own_growth",
                        "input_value": float(r.own_growth),
                        "transformed_input_value": float(r.own_growth),
                        "coefficient": ar_coef,
                        "contribution_logpoints": float(r.own_growth) * ar_coef,
                    }
                ]
            reconstructed = intercept + sum(q["contribution_logpoints"] for q in terms)
            residual = abs(reconstructed - pred)
            assert residual < 1e-10
            c["linear_explanation"].update(
                reference="실제 저장된 모형 계수와 해당 관측의 입력값을 이용한 가산 분해; 인과효과 아님",
                intercept_logpoints=intercept,
                contributions=terms,
                reconstructed_logpoints=reconstructed,
                reconstruction_residual=residual,
                model=model,
            )
            c["model_artifact_snapshot"] = copy.deepcopy(artifacts[model])
            c["source_manifest"] = source_manifest
            c["warnings"] = [
                "현재 개정자료 기반 회고적 기술 시험이며 운영 예측이나 실제 사용자 평가가 아님",
                "동일 지역·산업의 검증연도는 0–3개로 제한적이며 방향일치율을 표시하지 않음",
                "산업·분류·소규모 표본의 비교가능성을 별도 검토해야 함",
            ]
            c["historical_outcome_audit"] = {
                "observed_logpoints": float(r.target_logpoints),
                "observed_employment_persons": float(r.employment_target_persons),
                "role": "사후 결과 기록; 근거 해시·정상/결함 판정에 사용하지 않음",
            }
            e["fixture_status"] = (
                "ACTUAL_NUMERIC_CARD_WITH_SYNTHETIC_REVIEW: source metadata/review receipt/state are test fixtures, not historical operation evidence"
            )
            bind(e)
            key = (str(r.region_code), str(r.industry_code), model)
            envelopes[key] = e
            checks.append(
                {
                    "region_code": r.region_code,
                    "industry_code": r.industry_code,
                    "model": model,
                    "prediction": pred,
                    "reconstructed_prediction": reconstructed,
                    "absolute_residual": residual,
                    "validation_year_n": pv["validation_year_n"],
                    "validation_mae": pv["aggregate_learned_mae"],
                    "validation_delta_mae": pv["aggregate_mae_difference"],
                }
            )
    cases = []
    for key, e in envelopes.items():
        cases.append(
            {
                "case_id": "N:" + ":".join(key),
                "scope": "coherent_control",
                "family": "coherent_model_swap",
                "model": key[2],
                "region_code": key[0],
                "industry_code": key[1],
                "expected": "permit",
                "expected_code": None,
                "description": "모형명·실제 예측·기여도·검증근거·연결기록을 일관되게 교체한 정상 입력",
                "fixture": e,
            }
        )
    # Fixed before any v2 execution: one null-validation example, one positive-validation example.
    chosen = [("KR011", "BTE"), ("KR011", "F")]

    def add(key, cid, scope, description, fn, code=None, rebind=True):
        src = envelopes[key]
        other = envelopes[
            (key[0], key[1], MODELS[1] if key[2] == MODELS[0] else MODELS[0])
        ]
        e = copy.deepcopy(src)
        fn(e, other)
        if rebind:
            bind(e)
        cases.append(
            {
                "case_id": cid + ":" + ":".join(key),
                "scope": scope,
                "family": cid,
                "model": key[2],
                "region_code": key[0],
                "industry_code": key[1],
                "expected": "structured_block",
                "expected_code": code,
                "description": description,
                "fixture": e,
            }
        )

    for region, industry in chosen:
        for model in MODELS:
            key = (region, industry, model)
            add(
                key,
                "D01",
                "existing_contract",
                "반대 모형 예측값만 복사하고 해시는 갱신하지 않음",
                lambda e, o: e["card"]["learned_comparator"].update(
                    logpoints=o["card"]["learned_comparator"]["logpoints"]
                ),
                "card_invalid",
                False,
            )
            add(
                key,
                "D02",
                "existing_contract",
                "반대 모형 가산분해를 복사하고 해시만 갱신",
                lambda e, o: e["card"].update(
                    linear_explanation=copy.deepcopy(o["card"]["linear_explanation"])
                ),
                "linear_explanation_arithmetic",
            )
            add(
                key,
                "D03",
                "existing_contract",
                "상대편차 산술값에 1을 더함",
                lambda e, o: e["card"]["relative_deviation"].update(
                    logpoints=e["card"]["relative_deviation"]["logpoints"] + 1
                ),
                "relative_deviation_arithmetic",
            )
            add(
                key,
                "D04",
                "existing_contract",
                "예측 방향표시를 다른 범주로 변경",
                lambda e, o: e["card"]["learned_comparator"].update(
                    direction="감소"
                    if e["card"]["learned_comparator"]["direction"] != "감소"
                    else "증가"
                ),
                "learned_direction_label",
            )
            add(
                key,
                "D05",
                "existing_contract",
                "반대 모형의 검토 근거해시를 재사용",
                lambda e, o: e["review"].update(
                    evidence_sha256=o["review"]["evidence_sha256"]
                ),
                "review_card_binding",
                False,
            )
            add(
                key,
                "D06",
                "existing_contract",
                "반대 모형의 접수기록을 재사용",
                lambda e, o: e.update(receipt=copy.deepcopy(o["receipt"])),
                "receipt_card_binding",
                False,
            )
            add(
                key,
                "D07",
                "existing_contract",
                "반대 모형의 현재 상태기록을 재사용",
                lambda e, o: e.update(current_state=copy.deepcopy(o["current_state"])),
                "current_card_binding",
                False,
            )
            add(
                key,
                "D08",
                "existing_contract",
                "표시된 검증연도 수를 실제 집계보다 하나 증가",
                lambda e, o: e["card"]["validation_display"].update(
                    validation_year_n=e["card"]["prior_validation"]["validation_year_n"]
                    + 1
                ),
                "validation_display_count_disagrees",
            )
            add(
                key,
                "D09",
                "existing_contract",
                "검증 MAE 차이 표시를 근거 집계와 불일치하게 변경",
                lambda e, o: e["card"]["validation_display"].update(
                    mae_difference=(
                        e["card"]["prior_validation"]["aggregate_mae_difference"] or 0
                    )
                    + 0.25
                ),
                "validation_display_mae_disagrees",
            )

            def horizon(e, o):
                e["card"]["target_year"] = 2026
                e["request"]["target_refperiod"] = "2026-04"

            add(
                key,
                "D10",
                "existing_contract",
                "목표 기준기간을 12개월에서 24개월 후로 변경",
                horizon,
                "forecast_horizon_must_equal_12_months",
            )
            add(
                key,
                "D11",
                "existing_contract",
                "경고 확인을 거짓으로 변경",
                lambda e, o: e["review"].update(warnings_acknowledged=False),
                "warnings_must_be_true_boolean",
            )
            add(
                key,
                "D12",
                "existing_contract",
                "미실시 사용자 평가를 실시로 변경",
                lambda e, o: e["card"].update(human_evaluation_conducted=True),
                "unsubstantiated_human_evaluation_claim",
            )
            add(
                key,
                "X01",
                "extended_model_provenance_probe",
                "숫자와 설명은 유지하고 비교모형 식별자만 반대 모형으로 변경 후 재해시",
                lambda e, o: e["card"]["learned_comparator"].update(
                    model=o["card"]["learned_comparator"]["model"]
                ),
            )

            def coefficient(e, o):
                item = next(
                    x
                    for x in e["card"]["model_artifact_snapshot"]["parameters"]
                    if x["feature"].endswith("own_growth")
                )
                item["coefficient"] += 1

            add(
                key,
                "X02",
                "extended_model_provenance_probe",
                "표시 계수만 1 증가시키고 기여도는 유지한 뒤 재해시",
                coefficient,
            )

            def input_value(e, o):
                item = next(
                    x
                    for x in e["card"]["linear_explanation"]["contributions"]
                    if x["feature"] == "own_growth"
                )
                item["input_value"] += 1

            add(
                key,
                "X03",
                "extended_model_provenance_probe",
                "실제 입력값 대신 직전 변동값에 1을 더한 값을 표시하고 기여도는 유지",
                input_value,
            )
            if industry == "F":

                def borrow(e, o):
                    e["card"]["prior_validation"] = copy.deepcopy(
                        o["card"]["prior_validation"]
                    )
                    e["card"]["validation_display"] = copy.deepcopy(
                        o["card"]["validation_display"]
                    )

                add(
                    key,
                    "X04",
                    "extended_model_provenance_probe",
                    "반대 모형의 실제 검증 근거와 표시를 함께 복사하고 재해시",
                    borrow,
                )
    return cases, checks, artifacts


def freeze():
    dest = HERE / "frozen"
    dest.mkdir(exist_ok=True)
    if (dest / "protocol_and_cases.json").exists():
        raise RuntimeError("Frozen protocol exists; do not overwrite")
    cases, checks, artifacts = build()
    frozen = {
        "protocol_id": "KITS-MODEL-SWAP-20261018-v1",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "design": "Finite, internal metamorphic audit; implementation inspected before authoring. Inputs and expectations frozen before first v2 execution.",
        "scope": "2025 held-out forecast records reused for interface auditing; no newly untouched forecast test set, third-party independence, field evaluation or empirical error-rate inference.",
        "human_participants": 0,
        "production_validator_modified": False,
        "models": MODELS,
        "control_unit": "same 136 observed region-industry rows × 2 fitted model representations = 272 cards",
        "fault_unit": "2 fixed Seoul examples × 2 models × 12 existing-contract faults = 48; 14 separately labelled model-provenance extension probes",
        "selection_rule": "all 2025 valid prediction rows for controls; prior illustrative Seoul BTE with zero validation and Seoul construction F with three validation years for faults; no selection on test error",
        "expected_outcomes": "coherent cards permit research review only; all declared fault/provenance probes should block; extra probes explicitly exceed existing arithmetic/linkage contract",
        "failure_policy": "retain every original outcome; exception is failure; no validator change during audit; extended probes never pooled into old-contract coverage claim",
        "hashes": {
            str(p.relative_to(HERE)): sha(p)
            for folder in ["input", "guard_snapshot"]
            for p in sorted((HERE / folder).rglob("*"))
            if p.is_file()
        },
        "cases": cases,
    }
    dump(artifacts, dest / "model_artifacts.json")
    table(checks, dest / "numeric_linkage.csv")
    dump(frozen, dest / "protocol_and_cases.json")
    print(
        json.dumps(
            {
                "cases": len(cases),
                "protocol_sha256": sha(dest / "protocol_and_cases.json"),
                "controls": sum(c["expected"] == "permit" for c in cases),
                "faults": sum(c["expected"] == "structured_block" for c in cases),
            },
            ensure_ascii=False,
        )
    )


def run(out):
    protocol_path = HERE / "frozen/protocol_and_cases.json"
    p = json.loads(protocol_path.read_text())
    for rel, h in p["hashes"].items():
        assert sha(HERE / rel) == h, rel
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("Use a new output directory to preserve original results")
    out.mkdir(parents=True, exist_ok=True)
    dump(
        {
            "execution_started_utc": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": sha(protocol_path),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        out / "execution_start.json",
    )
    sys.path.insert(0, str(HERE / "guard_snapshot"))
    from workflow_guard import load_original
    from workflow_guard_v2 import validate

    modules = load_original(HERE / "guard_snapshot/source_snapshot")
    rows = []
    traces = []
    for c in p["cases"]:
        result = None
        exc = None
        try:
            result = validate(copy.deepcopy(c["fixture"]), modules)
            observed = (
                "permit" if result["research_review_permitted"] else "structured_block"
            )
        except Exception as e:
            observed = "unhandled_exception"
            exc = f"{type(e).__name__}: {e}"
        codes = [x["code"] for x in (result or {}).get("errors", [])]
        rows.append(
            {
                k: c[k]
                for k in [
                    "case_id",
                    "scope",
                    "family",
                    "model",
                    "region_code",
                    "industry_code",
                    "expected",
                    "expected_code",
                    "description",
                ]
            }
            | {
                "observed": observed,
                "matches_expectation": observed == c["expected"],
                "expected_code_present": c["expected_code"] in codes
                if c["expected_code"]
                else None,
                "error_codes": ";".join(codes),
                "exception": exc,
            }
        )
        traces.append({"case_id": c["case_id"], "result": result, "exception": exc})
    groups = []
    for scope in [
        "coherent_control",
        "existing_contract",
        "extended_model_provenance_probe",
    ]:
        for model in MODELS + ["BOTH"]:
            a = [
                r
                for r in rows
                if r["scope"] == scope and (model == "BOTH" or r["model"] == model)
            ]
            groups.append(
                {
                    "scope": scope,
                    "model": model,
                    "n": len(a),
                    "matches": sum(r["matches_expectation"] for r in a),
                    "permitted": sum(r["observed"] == "permit" for r in a),
                    "structured_blocks": sum(
                        r["observed"] == "structured_block" for r in a
                    ),
                    "exceptions": sum(
                        r["observed"] == "unhandled_exception" for r in a
                    ),
                }
            )
    pairs = []
    paired = {}
    for r in rows:
        paired.setdefault(
            (r["scope"], r["family"], r["region_code"], r["industry_code"]), {}
        )[r["model"]] = r
    for k, m in paired.items():
        a, b = [m[x] for x in MODELS]
        pairs.append(
            {
                "scope": k[0],
                "family": k[1],
                "region_code": k[2],
                "industry_code": k[3],
                "same_disposition": a["observed"] == b["observed"],
                "same_error_code_set": set(a["error_codes"].split(";"))
                == set(b["error_codes"].split(";")),
                "ridge_observed": a["observed"],
                "ar1_observed": b["observed"],
            }
        )
    table(rows, out / "case_results.csv")
    table(groups, out / "summary.csv")
    table(pairs, out / "paired_results.csv")
    dump(traces, out / "all_traces.json")
    summary = {
        "protocol_sha256": sha(protocol_path),
        "human_participants": 0,
        "validator_modified": False,
        "groups": groups,
        "paired_cases": len(pairs),
        "paired_same_disposition": sum(x["same_disposition"] for x in pairs),
        "paired_same_error_code_set": sum(x["same_error_code_set"] for x in pairs),
        "expected_error_code_checks": sum(r["expected_code"] is not None for r in rows),
        "expected_error_code_matches": sum(
            r["expected_code_present"] is True for r in rows
        ),
        "interpretation": "Model-swap consistency demonstrated only for enumerated compatible linear-model representations and existing contracts. Passing controls does not verify source truth or human usefulness. Model-provenance extension failures are preserved.",
    }
    dump(summary, out / "results.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.freeze:
        freeze()
    elif a.out:
        run(a.out)
    else:
        ap.error("Choose --freeze or --out /new/output")
