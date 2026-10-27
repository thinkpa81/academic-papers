from __future__ import annotations

if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import copy
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

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
SUPERS = {
    "수도권": ["KR011", "KR012", "KR013"],
    "충청권": ["KR051", "KR052", "KR053", "KR054"],
    "호남권": ["KR041", "KR043"],
    "대경권": ["KR031", "KR032"],
    "동남권": ["KR021", "KR022", "KR023"],
    "강원": ["KR061"],
    "전북": ["KR042"],
    "제주": ["KR071"],
}
IND = {
    "A": "농림어업",
    "BTE": "광업·제조업·전기·수도(B–E)",
    "F": "건설업",
    "GTI": "도소매·운수·숙박·음식(G–I)",
    "J": "정보통신업",
    "K": "금융·보험업",
    "L": "부동산업",
    "M_N": "전문·과학·기술·사업지원(M–N)",
    "OTQ": "공공행정·교육·보건(O–Q)",
    "RTU": "예술·기타 서비스(R–U)",
}
NUM = [
    "log_employment",
    "industry_share_pct",
    "own_growth",
    "own_growth_lag1",
    "peer_industry_growth",
    "region_total_growth",
]
FN = {
    "log_employment": "기준고용 로그값",
    "industry_share_pct": "시도 내 산업고용 비중",
    "own_growth": "직전 동일 상반기 고용변동",
    "own_growth_lag1": "1기 전 고용변동",
    "peer_industry_growth": "타지역 동일 산업 고용변동",
    "region_total_growth": "지역 전체 고용변동",
    "region_code": "지역 지시변수",
    "industry_code": "산업 지시변수",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hashobj(obj):
    return hashlib.sha256(
        json.dumps(
            obj,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def dump(obj, path):
    Path(path).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def band(x):
    return "상회" if x > 0.5 else "하회" if x < -0.5 else "근접"


def direction(x):
    return "증가" if x > 0.5 else "감소" if x < -0.5 else "유지 범위"


def classification_transition():
    return {
        "input_basis": "KSIC11_backcast",
        "target_basis": "KSIC11_new_classification_published",
        "classification_code_unchanged": True,
        "status": "verification_required",
        "warning": "소급보정값에서 신분류 적용 공표값으로 전환(동일 KSIC11). 연계 방법과 비교가능성 확인 필요; 통계적 단절 또는 원자료 오류로 확정하지 않음",
        "role": "자료 작성방식 점검; 예측방향의 판정조건이 아님",
    }


def outcome_audit(r):
    change = 100 * (
        float(r.employment_target_persons) / float(r.employment_input_persons) - 1
    )
    flag = abs(change) >= 20
    return {
        "observed_logpoints": float(r.target_logpoints),
        "observed_employment_persons": float(r.employment_target_persons),
        "observed_simple_change_pct": change,
        "large_change_audit": {
            "threshold_absolute_simple_change_pct": 20.0,
            "flagged": flag,
            "status": "verification_required" if flag else "no_large_change_flag",
            "warning": "사후 관측값의 절대 증가율이 20% 이상으로 원표 구성항목과 연계 방법 확인 필요"
            if flag
            else "설정한 사후 점검범위 이내",
            "interpretation": "20%는 투고 전 검토에서 정한 사후 자료점검 시연조건이며 원자료 오류나 실제 변동 부재를 뜻하지 않음",
        },
        "role": "사후 자료점검 전용. 사례선정·예측값·편차·사전 검증·의사결정 근거해시에 사용하지 않음",
    }


def validation_display(v):
    return {
        "validation_year_n": int(v["validation_year_n"]),
        "direction_percentage_displayed": False,
        "suppression_reason": "조합별 검증연도가 0–3개이므로 칸별 방향일치율 표시를 생략; 원시 비율은 재현용 JSON·CSV에 보존",
        "mae_difference": v["aggregate_mae_difference"],
    }


def aggregate(d, col):
    w = d.employment_input_persons.to_numpy(float)
    return float(
        100 * np.log(np.sum(w * np.exp(d[col].to_numpy(float) / 100)) / w.sum())
    )


def validation_stats(v, region_codes, industry, base, learned):
    d = v[v.region_code.isin(region_codes) & (v.industry_code == industry)].copy()
    if d.empty:
        return {
            "validation_cell_n": 0,
            "validation_year_n": 0,
            "validation_years": "",
            "deviation_sign_matches": 0,
            "deviation_sign_accuracy_pct": None,
            "aggregate_baseline_mae": None,
            "aggregate_learned_mae": None,
            "aggregate_mae_difference": None,
            "cell_baseline_mae": None,
            "cell_learned_mae": None,
            "cell_mae_difference": None,
            "validation_composition_rule": "2025 가용지역과 동일한 지역구성의 연도만 집계",
        }
    vals = []
    for year, q in d.groupby("target_year"):
        if set(q.region_code) != set(region_codes):
            continue
        a = aggregate(q, base)
        b = aggregate(q, learned)
        y = aggregate(q, "target_logpoints")
        vals.append((int(year), a, b, y, int(np.sign(b - a) == np.sign(y - a))))
    out = {
        "validation_cell_n": len(d),
        "validation_year_n": len(vals),
        "validation_years": ";".join((str(x[0]) for x in vals)),
        "deviation_sign_matches": sum((x[4] for x in vals)),
        "deviation_sign_accuracy_pct": float(np.mean([x[4] for x in vals]) * 100)
        if vals
        else None,
        "aggregate_baseline_mae": float(np.mean([abs(x[3] - x[1]) for x in vals]))
        if vals
        else None,
        "aggregate_learned_mae": float(np.mean([abs(x[3] - x[2]) for x in vals]))
        if vals
        else None,
        "cell_baseline_mae": float(abs(d.target_logpoints - d[base]).mean()),
        "cell_learned_mae": float(abs(d.target_logpoints - d[learned]).mean()),
        "validation_composition_rule": "2025 가용지역과 동일한 지역구성의 연도만 집계",
    }
    out["aggregate_mae_difference"] = (
        out["aggregate_learned_mae"] - out["aggregate_baseline_mae"] if vals else None
    )
    out["cell_mae_difference"] = out["cell_learned_mae"] - out["cell_baseline_mae"]
    return out


def build_matrix(test, val, selection):
    year = 2025
    base = selection["service_default_baseline"]
    learned = selection["learned_companion"]
    t = test[test.target_year == year]
    rows = []
    for sr, codes in SUPERS.items():
        for ind in IND:
            q = t[(t.superregion == sr) & (t.industry_code == ind)].sort_values(
                "region_code"
            )
            available = list(q.region_code)
            missing = [r for r in codes if r not in available]
            record = {
                "superregion": sr,
                "industry_code": ind,
                "industry_name": IND[ind],
                "target_year": year,
                "input_year": 2024,
                "expected_regions_n": len(codes),
                "available_regions_n": len(available),
                "available_regions": ";".join((REGIONS[x] for x in available)),
                "missing_regions": ";".join((REGIONS[x] for x in missing)),
                "coverage_status": "완전"
                if len(available) == len(codes)
                else "부분"
                if len(available)
                else "자료없음",
                "scope": "2026-09-26 개정자료 기반 회고적 평가표본; 2025 실시간 예측 재현 아님",
            }
            record.update(
                baseline_display_label="전 관측 공통 과거평균",
                direction_percentage_displayed=False,
                direction_percentage_suppression_reason="검증연도 0–3개로 칸별 비율 표시 생략; 원시 비율은 재현용 보존",
            )
            if len(q):
                a = aggregate(q, base)
                b = aggregate(q, learned)
                record.update(
                    baseline_model=base,
                    learned_model=learned,
                    baseline_logpoints=a,
                    learned_logpoints=b,
                    relative_deviation_logpoints=b - a,
                    relative_deviation_class=band(b - a),
                    baseline_original_direction=direction(a),
                    learned_original_direction=direction(b),
                    input_employment_persons=float(q.employment_input_persons.sum()),
                )
                record.update(validation_stats(val, available, ind, base, learned))
            rows.append(record)
    return pd.DataFrame(rows)


def validate_service(test, val, selection, manifest, root):
    for relative, expected in manifest.items():
        if sha(root / relative) != expected:
            raise ValueError("input_integrity_mismatch:" + relative)
    keys = ["target_year", "region_code", "industry_code"]
    if test.duplicated(keys).any() or val.duplicated(keys).any():
        raise ValueError("duplicate_prediction_key")
    if val.target_year.max() >= test.target_year.min():
        raise ValueError("validation_not_prior")
    if (
        selection["service_default_baseline"] != "global_past_mean"
        or selection["learned_companion"] != "ridge_alpha1000"
    ):
        raise ValueError("selection_contract_changed")
    for df in [test, val]:
        if not np.isfinite(
            df[
                ["global_past_mean", "ridge_alpha1000", "employment_input_persons"]
            ].to_numpy(float)
        ).all():
            raise ValueError("nonfinite_prediction")
        if (df.employment_input_persons <= 0).any():
            raise ValueError("nonpositive_input_employment")


def validate_matrix(matrix):
    for r in matrix.to_dict("records"):
        expected = (
            "완전"
            if r["available_regions_n"] == r["expected_regions_n"]
            else "부분"
            if r["available_regions_n"]
            else "자료없음"
        )
        if r["coverage_status"] != expected:
            raise ValueError("coverage_label_mismatch")


def validate_card(card):
    basis = {
        k: v
        for k, v in card.items()
        if k not in {"decision_basis_sha256", "historical_outcome_audit"}
    }
    if hashobj(basis) != card.get("decision_basis_sha256"):
        raise ValueError("decision_basis_hash_mismatch")
    if card.get("automatic_policy_action_allowed") is not False:
        raise ValueError("automatic_action_not_supported")
    return True


def validate_review(record):
    allowed = {
        "status",
        "reviewer_role",
        "reference_materials",
        "reason_for_review",
        "warnings_acknowledged",
        "evidence_sha256",
    }
    if set(record) - allowed:
        raise ValueError("unrecognized_personal_or_extra_field")
    if record.get("status") != "synthetic_review_complete":
        raise ValueError("approval_or_action_not_supported")
    for key in allowed - {"status"}:
        if not record.get(key):
            raise ValueError("required_review_field:" + key)
    return True


def make_card(test, val, selection, model_path, source_manifest):
    base = selection["service_default_baseline"]
    learned = selection["learned_companion"]
    q = (
        test[(test.target_year == 2025) & (test.industry_code == "BTE")]
        .sort_values("region_code")
        .iloc[[0]]
    )
    r = q.iloc[0]
    model = joblib.load(model_path)
    pre = model.named_steps["preprocessor"]
    linear = model.named_steps["model"]
    design = pre.transform(q[NUM + ["region_code", "industry_code"]])
    names = pre.get_feature_names_out()
    products = np.asarray(design)[0] * linear.coef_
    contributions = []
    for i, name in enumerate(NUM):
        contributions.append(
            {
                "feature": name,
                "label": FN[name],
                "input_value": float(r[name]),
                "contribution_logpoints": float(products[i]),
            }
        )
    for cat in ["region_code", "industry_code"]:
        idx = [i for i, n in enumerate(names) if n.startswith("cat__" + cat + "_")]
        contributions.append(
            {
                "feature": cat,
                "label": FN[cat],
                "input_value": r[cat],
                "contribution_logpoints": float(products[idx].sum()),
            }
        )
    reconstructed = float(linear.intercept_) + sum(
        (x["contribution_logpoints"] for x in contributions)
    )
    residual = abs(reconstructed - float(r[learned]))
    assert residual < 1e-10
    card = {
        "schema_version": "1.0.0",
        "scope": "현재 개정자료에 근거한 회고적 고용변동 진단",
        "evidence_id": f"{r.region_code}:BTE:2025",
        "example_selection_rule": "2025년 B–E 산업의 가용 사례를 지역코드 오름차순으로 정렬한 첫 사례; 평가오차 미사용",
        "target_year": 2025,
        "input_year": 2024,
        "reference_period": "상반기(4월)",
        "region_code": r.region_code,
        "region_name": r.region_name_ko,
        "industry_code": "BTE",
        "industry_name": IND["BTE"],
        "employment_input_persons": float(r.employment_input_persons),
        "default_estimate": {
            "model": base,
            "model_label": "전체 과거평균 기준모형",
            "logpoints": float(r[base]),
            "direction": direction(float(r[base])),
        },
        "learned_comparator": {
            "model": learned,
            "model_label": "릿지 회귀 비교모형",
            "logpoints": float(r[learned]),
            "direction": direction(float(r[learned])),
        },
        "relative_deviation": {
            "definition": "릿지 예측값 − 검증에서 선정한 기준모형 예측값",
            "logpoints": float(r[learned] - r[base]),
            "class": band(float(r[learned] - r[base])),
            "tolerance_logpoints": 0.5,
        },
        "prior_validation": validation_stats(
            val, [r.region_code], "BTE", base, learned
        ),
        "linear_explanation": {
            "reference": "학습·검증자료로 적합한 설계행렬의 표준화 숫자변수와 원핫 지시변수; 인과효과가 아님",
            "intercept_logpoints": float(linear.intercept_),
            "contributions": contributions,
            "reconstructed_logpoints": reconstructed,
            "reconstruction_residual": residual,
        },
        "data_timing": {
            "input_source_vintage": "2026-09-26",
            "historical_vintage_verified": False,
            "operational_prediction_permitted": False,
        },
        "warnings": [
            "동일 지역·산업의 2020–2022년 검증자료가 없거나 적음; 검증 사례 수를 함께 확인할 것",
            "편차 방향 적중률은 오차 감소나 추가 예측가치의 검증과 다름",
            "B–E는 제조업 단독 분류가 아니며 산업별 세부 훈련수요를 직접 측정하지 않음",
            "현재 개정자료 기반 평가이므로 2025년 당시 정보집합으로 해석하지 않음",
        ],
        "source_manifest": source_manifest,
        "automatic_policy_action_allowed": False,
        "human_evaluation_conducted": False,
    }
    card["schema_version"] = "1.1.0"
    card["default_estimate"]["raw_direction_for_statistical_audit"] = card[
        "default_estimate"
    ].pop("direction")
    card["default_estimate"]["display_label"] = "전 관측 공통 과거평균"
    card["default_estimate"]["direction_label_displayed"] = False
    card["default_estimate"]["display_reason"] = (
        "모든 관측에 공통인 상수 예측으로 지역·산업별 증가 신호가 아님"
    )
    card["validation_display"] = validation_display(card["prior_validation"])
    card["data_timing"]["classification_transition"] = classification_transition()
    card["linear_explanation"]["rounding_note"] = (
        "각 항과 합계는 각각 소수 둘째 자리까지 반올림하여 표시하므로 표시된 항의 합계와 예측값 사이에 반올림 차이가 생길 수 있음"
    )
    card["warnings"][1] = (
        "조합별 검증연도는 0–3개로 칸별 방향일치율을 표시하지 않음; 통합 비율은 기술통계로만 제시"
    )
    card["decision_basis_sha256"] = hashobj(card)
    card["historical_outcome_audit"] = outcome_audit(r)
    return card


def render_html(card, matrix, path):
    e = html.escape
    v = card["prior_validation"]
    contrib = card["linear_explanation"]
    audit = card["historical_outcome_audit"]
    fmt = lambda x: (
        "자료없음"
        if x is None or (isinstance(x, float) and math.isnan(x))
        else f"{x:.2f}".replace("-", "−")
    )
    bars = "".join(
        (
            f"<tr><td>{e(x['label'])}</td><td>{fmt(x['contribution_logpoints'])}</td></tr>"
            for x in contrib["contributions"]
        )
    )
    rows = []
    for r in matrix.to_dict("records"):
        ready = r["available_regions_n"] > 0
        rows.append(
            "<tr>"
            + "".join(
                (
                    f"<td>{e(str(x))}</td>"
                    for x in [
                        r["superregion"],
                        r["industry_code"],
                        r["coverage_status"],
                        r["available_regions"] or "—",
                        r.get("relative_deviation_class", "—") if ready else "—",
                        fmt(r.get("relative_deviation_logpoints")) if ready else "—",
                        int(r["validation_year_n"]) if ready else "—",
                        fmt(r.get("aggregate_mae_difference")) if ready else "—",
                    ]
                )
            )
            + "</tr>"
        )
    matched = int(matrix.deviation_sign_matches.sum())
    total = int(matrix.validation_year_n.sum())
    style = '*{box-sizing:border-box}body{font-family:"Noto Sans CJK KR","Malgun Gothic",sans-serif;background:#f2f5f8;color:#20364a;margin:0;padding:24px}main{max-width:1060px;margin:auto}.card{background:white;border:1px solid #d8e1e9;border-radius:8px;padding:24px;margin-bottom:20px}h1{font-size:25px}h2{font-size:19px}p{line-height:1.65}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.metric{padding:15px;border:1px solid #ccd9e2}.value{font-size:30px;font-weight:700}.label{font-size:14px}.two{display:grid;grid-template-columns:1fr 1fr;gap:26px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:7px;border-bottom:1px solid #e3e8ed;text-align:left}.note{font-size:13px;color:#526879}.warn{background:#fff6e6;border-left:4px solid #b87520;padding:12px}.foot{font-size:12px;word-break:break-all}@media(max-width:720px){.grid,.two{grid-template-columns:1fr}body{padding:10px}}'
    metrics = "".join(
        (
            f'<div class="metric"><div class="label">{e(label)}</div><div class="value">{fmt(value)}</div><div class="note">{e(desc)}</div></div>'
            for label, value, desc in [
                (
                    "선정 기준모형 · 전체 과거평균",
                    card["default_estimate"]["logpoints"],
                    "로그포인트 · 전 관측 공통 과거평균",
                ),
                (
                    "비교모형 · 릿지 회귀",
                    card["learned_comparator"]["logpoints"],
                    "로그포인트 · " + card["learned_comparator"]["direction"],
                ),
                (
                    "기준모형 대비 예측 편차",
                    card["relative_deviation"]["logpoints"],
                    "로그포인트 · 기준모형 " + card["relative_deviation"]["class"],
                ),
            ]
        )
    )
    doc = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>지역고용 예측근거 카드 — 2025 상반기</title><style>{style}</style><main><section class="card" id="evidence-card"><p class="note">지역고용 의사결정지원서비스 · 회고적 기술 시연</p><h1>서울 · BTE(B+C+D+E)</h1><p>2024년 상반기 → 2025년 상반기 | 자료 개정시점 2026.09.26 | 기준고용 {int(card["employment_input_persons"]):,}명</p><div class="grid">{metrics}</div><p class="note">기준모형은 모든 관측에 공통인 상수 예측입니다. 지역·산업별 증가 신호를 뜻하지 않습니다. 비교모형 방향과 상대편차의 표시범위는 ±0.5 로그포인트입니다.</p><div class="two"><div><h2>과거 검증 근거 · 2020–2022년</h2><table><tr><td>동일 지역·산업 검증연도</td><td>{v["validation_year_n"]}개</td></tr><tr><td>기준모형 MAE</td><td>{fmt(v["aggregate_baseline_mae"])}</td></tr><tr><td>릿지 MAE</td><td>{fmt(v["aggregate_learned_mae"])}</td></tr><tr><td>MAE 차이(릿지 − 기준)</td><td>{fmt(v["aggregate_mae_difference"])}</td></tr></table><p class="note">조합별 검증연도는 0–3개로 칸별 방향일치율을 표시하지 않습니다. 원시 비율은 재현자료에 보존합니다. 음의 MAE 차이는 오차 감소를 뜻합니다.</p><h2>자료 적격성 점검</h2><p class="warn">{e(card["data_timing"]["classification_transition"]["warning"])}</p><p class="note">당시 이용 가능한 자료 개정본이 확인되지 않아 실시간 운영 예측으로 사용할 수 없습니다. 인력부족·훈련수요는 별도 자료와 담당자 검토가 필요합니다.</p></div><div><h2>선형 예측값의 가산 분해</h2><table><tr><td>절편</td><td>{fmt(contrib["intercept_logpoints"])}</td></tr>{bars}<tr><th>합계 · 릿지 예측값</th><th>{fmt(contrib["reconstructed_logpoints"])}</th></tr></table><p class="note">{e(contrib["rounding_note"])}. 산술 분해이며 인과효과를 나타내지 않습니다.</p></div></div><p class="foot">근거 ID {e(card["evidence_id"])} | 의사결정 근거해시 {card["decision_basis_sha256"]}<br>실제 사용자·정책효과 평가: 미실시 | 자동 정책집행: 미지원</p></section><section class="card" id="historical-outcome-audit"><h2>사후 자료점검 · 예측근거와 분리</h2><p>관측 고용: {int(card["employment_input_persons"]):,} → {int(audit["observed_employment_persons"]):,}명. 단순 증가율 {fmt(audit["observed_simple_change_pct"])}%, 로그변동 {fmt(audit["observed_logpoints"])} 로그포인트.</p><p class="warn">{e(audit["large_change_audit"]["warning"])}</p><p class="note">{e(audit["large_change_audit"]["interpretation"])}. 관측값과 이 점검경고는 사례선정·예측·사전검증·의사결정 근거해시에 포함하지 않습니다.</p></section><section class="card"><h2>2025년 권역–산업 검토행렬</h2><p>명목 80개 조합 중 완전 61개, 부분 4개, 자료없음 15개입니다. 상대편차는 ±0.5 로그포인트를 기준으로 상회·근접·하회로 표시합니다. 가용 구성지역에 한정한 집계입니다.</p><p>통합 편차 방향 일치: {matched}/{total}건({100 * matched / total:.2f}%). 검증표본의 기술통계이며 독립 시행의 신뢰구간이나 추가 예측가치의 검증을 뜻하지 않습니다.</p><table><tr><th>권역</th><th>산업</th><th>가용범위</th><th>구성지역</th><th>상대편차</th><th>값</th><th>검증연도 수</th><th>과거 MAE 차이</th></tr>{"".join(rows)}</table></section><section class="card"><h2>후속 검토기록</h2><p>담당 역할, 근거자료, 검토사유, 경고 확인, 근거해시를 기록합니다. 이 정적 시연은 저장·승인 기능을 실행하지 않습니다.</p></section></main></html>"""
    path.write_text(doc, encoding="utf-8")


def classify_inherited(root, out):
    inherited = []
    tneg = set(
        list(range(3, 14)) + list(range(15, 21)) + list(range(22, 26)) + [28, 30]
    )
    tmeta = {26, 33}
    sneg = {9, *range(21, 35), 41, 44}
    smeta = {40}
    for file, prefix, negative, metamorphic in [
        ("source_time_33_observations.csv", "T", tneg, tmeta),
        ("evidence_scenarios_45_observations.csv", "S", sneg, smeta),
    ]:
        df = pd.read_csv(root / "review/v6/service_audit" / file)
        for r in df.to_dict("records"):
            i = int(r["scenario_id"][1:])
            typ = (
                "변성시험"
                if i in metamorphic
                else "결함주입·부적격 입력 차단"
                if i in negative
                else "정상·경계·연결 검증"
            )
            inherited.append(
                {
                    "source_file": file,
                    "test_id": r["scenario_id"],
                    "category": typ,
                    "scenario": r["scenario"],
                    "recorded_result": r["status"],
                    "evidence_status": "v6 실행로그의 사후 분류; v7에서 재실행한 신규 시험 수와 합산하지 않음",
                }
            )
    pd.DataFrame(inherited).to_csv(
        out / "inherited_test_classification.csv", index=False, encoding="utf-8-sig"
    )
    return (
        pd.DataFrame(inherited)
        .groupby(["source_file", "category"])
        .size()
        .rename("count")
        .reset_index()
        .to_dict("records")
    )


def run_tests(root, out, test, val, selection, manifest, matrix, card):
    spec = importlib.util.spec_from_file_location(
        "v7_source_gate", root / "service_time_controls/source_gate.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    request = {
        "role": "operational_prediction",
        "intended_decision_date": "2024-12-31",
        "target_refperiod": "2025-04",
        "fixture_status": "synthetic metadata, not historical archive",
        "sources": [
            {
                "source_id": "synthetic_input",
                "source_refperiod": "2024-04",
                "previous_refperiod": "2023-04",
                "release_date": "2024-10-08",
                "vintage_date": "2024-10-08",
                "classification": "KSIC11",
                "boundary_status": "stable_verified",
                "observation_interval_months": 12,
                "vintage_availability_status": "archived_vintage_verified",
                "vintage_evidence_ref": "SYNTHETIC_TEST_ONLY",
                "release_evidence_ref": "SYNTHETIC_TEST_ONLY",
            }
        ],
    }
    results = []

    def record(id, typ, req, scenario, expected, fn):
        try:
            ok, observed = fn()
        except Exception as exc:
            ok = False
            observed = repr(exc)
        results.append(
            {
                "test_id": id,
                "category": typ,
                "requirements": ";".join(req),
                "scenario": scenario,
                "expected": expected,
                "observed": str(observed),
                "passed": bool(ok),
            }
        )

    def hold(changes, code):
        q = copy.deepcopy(request)
        q["sources"][0].update(changes)
        g = m.evaluate_source_gate(q)
        codes = [r["code"] for r in g["issues"]]
        return (
            g["disposition"] == "hold_operational_prediction" and code in codes,
            codes,
        )

    def rejected(fn):
        try:
            fn()
        except ValueError as exc:
            return (True, str(exc))
        return (False, "unexpected acceptance")

    negative = "결함주입"
    normal = "정상대조"
    meta = "변성시험"
    record(
        "N01",
        negative,
        ["R01"],
        "미래 입력 기준기간 주입",
        "input_not_before_target",
        lambda: hold(
            {"source_refperiod": "2025-04", "previous_refperiod": "2024-04"},
            "input_not_before_target",
        ),
    )
    record(
        "N02",
        negative,
        ["R01"],
        "공표일을 판단일 다음 날로 변경",
        "release_after_decision",
        lambda: hold(
            {"release_date": "2025-01-01", "vintage_date": "2025-01-01"},
            "release_after_decision",
        ),
    )
    record(
        "N03",
        negative,
        ["R02"],
        "판단일 이후 개정본 주입",
        "vintage_after_decision",
        lambda: hold(
            {
                "vintage_date": "2026-09-26",
                "vintage_availability_status": "current_snapshot_only",
                "vintage_evidence_ref": None,
            },
            "vintage_after_decision",
        ),
    )
    record(
        "N04",
        negative,
        ["R03"],
        "6개월 간격 입력 주입",
        "nonannual_observation_interval",
        lambda: hold(
            {"previous_refperiod": "2023-10", "observation_interval_months": 6},
            "nonannual_observation_interval",
        ),
    )

    def mixed():
        q = copy.deepcopy(request)
        s = copy.deepcopy(q["sources"][0])
        s.update(source_id="second", classification="KSIC10")
        q["sources"].append(s)
        g = m.evaluate_source_gate(q)
        return (
            g["disposition"] == "hold_operational_prediction"
            and "mixed_classification" in [x["code"] for x in g["issues"]],
            g["disposition"],
        )

    record(
        "N05", negative, ["R03"], "산업분류 혼합 주입", "mixed_classification", mixed
    )
    record(
        "N06",
        negative,
        ["R04"],
        "경계 비교가능성 미확인 주입",
        "boundary_unresolved",
        lambda: hold({"boundary_status": "unknown"}, "boundary_unresolved"),
    )

    def tamper():
        x = copy.deepcopy(card)
        x["default_estimate"]["logpoints"] += 10
        return rejected(lambda: validate_card(x))

    record(
        "N07",
        negative,
        ["R05", "R06"],
        "근거카드 기준값 변조",
        "decision hash mismatch",
        tamper,
    )

    def futureval():
        x = val.copy()
        x.loc[x.index[0], "target_year"] = 2025
        return rejected(lambda: validate_service(test, x, selection, manifest, root))

    record(
        "N08",
        negative,
        ["R07"],
        "검증표에 평가연도 관측치 주입",
        "validation_not_prior",
        futureval,
    )
    review = {
        "status": "synthetic_review_complete",
        "reviewer_role": "synthetic_research_reviewer",
        "reference_materials": ["synthetic_ref"],
        "reason_for_review": "synthetic test",
        "warnings_acknowledged": True,
        "evidence_sha256": card["decision_basis_sha256"],
    }
    record(
        "N09",
        negative,
        ["R08"],
        "필수 검토사유 누락",
        "required_review_field",
        lambda: rejected(
            lambda: validate_review(
                {k: v for k, v in review.items() if k != "reason_for_review"}
            )
        ),
    )
    record(
        "N10",
        negative,
        ["R09"],
        "식별번호 필드 추가",
        "unrecognized_personal_or_extra_field",
        lambda: rejected(
            lambda: validate_review(
                {**review, "resident_registration_number": "SYNTHETIC_NOT_REAL"}
            )
        ),
    )

    def falsecomplete():
        x = matrix.copy()
        idx = x.index[x.coverage_status != "완전"][0]
        x.loc[idx, "coverage_status"] = "완전"
        return rejected(lambda: validate_matrix(x))

    record(
        "N11",
        negative,
        ["R04"],
        "부분·결측 권역을 완전으로 표시",
        "coverage_label_mismatch",
        falsecomplete,
    )
    record(
        "N12",
        negative,
        ["R10"],
        "기관승인 완료 상태 주입",
        "approval_or_action_not_supported",
        lambda: rejected(
            lambda: validate_review({**review, "status": "institutionally_approved"})
        ),
    )
    record(
        "P01",
        normal,
        ["R01", "R02", "R03", "R04", "R10"],
        "합성 적격 메타데이터",
        "metadata eligible research only",
        lambda: (
            (g := m.evaluate_source_gate(request))["disposition"]
            == "metadata_eligible_research_only"
            and (not g["automatic_policy_action_allowed"]),
            g["disposition"],
        ),
    )
    record(
        "P02",
        normal,
        ["R05", "R06"],
        "실제 저장예측·선정기록·해시",
        "input checks pass",
        lambda: (
            validate_service(test, val, selection, manifest, root) is None,
            "stored input hashes and selection preserved",
        ),
    )
    record(
        "P03",
        normal,
        ["R04", "R08", "R09", "R10"],
        "완전·부분·결측 표시 및 합성 검토기록",
        "checks pass",
        lambda: (
            validate_matrix(matrix) is None and validate_review(review),
            "matrix classifications and synthetic review fields accepted",
        ),
    )

    def perturb_outcomes():
        q = test.copy()
        q["target_logpoints"] = np.arange(len(q)) * 1000.0
        q["employment_target_persons"] = np.arange(len(q)) + 999999999
        newer = build_matrix(q, val, selection)
        newcard = make_card(
            q,
            val,
            selection,
            root / "analysis_harmonized/results/main/model_ridge_alpha1000.joblib",
            manifest,
        )
        a = {k: v for k, v in card.items() if k != "historical_outcome_audit"}
        b = {k: v for k, v in newcard.items() if k != "historical_outcome_audit"}
        return (
            matrix.equals(newer) and a == b,
            f"{len(q)} actual outcome rows perturbed; full matrix and card decision basis invariant",
        )

    record(
        "M01",
        meta,
        ["R05", "R07"],
        "428개 평가 실제값 모두 교란",
        "decision outputs invariant",
        perturb_outcomes,
    )

    def permute():
        newer = build_matrix(
            test.sample(frac=1, random_state=71),
            val.sample(frac=1, random_state=71),
            selection,
        )
        cols = [
            "baseline_logpoints",
            "learned_logpoints",
            "relative_deviation_logpoints",
            "aggregate_mae_difference",
            "cell_mae_difference",
        ]
        close = all(
            (
                np.allclose(matrix[x].fillna(0), newer[x].fillna(0), atol=1e-10, rtol=0)
                for x in cols
            )
        )
        return (
            close and matrix.coverage_status.equals(newer.coverage_status),
            "row permutation preserves values to 1e-10 and all coverage classes",
        )

    record(
        "M02",
        meta,
        ["R04", "R05"],
        "입력행 순서 무작위 변경",
        "order-independent aggregates",
        permute,
    )

    def constant_display():
        doc = (out / "evidence_dashboard_2025.html").read_text(encoding="utf-8")
        first_metric = doc.split('<div class="metric">', 1)[1].split(
            '<div class="metric">', 1
        )[0]
        b = card["default_estimate"]
        return (
            not b["direction_label_displayed"]
            and b["raw_direction_for_statistical_audit"] == "증가"
            and ("전 관측 공통 과거평균" in first_metric)
            and ("증가" not in first_metric),
            "constant default has no directional UI label; raw classification retained",
        )

    record(
        "P04",
        normal,
        ["R05", "R11"],
        "상수 기준모형의 원시 분류 보존과 화면 방향라벨 생략",
        "constant label only",
        constant_display,
    )

    def sparse_display():
        doc = (out / "evidence_dashboard_2025.html").read_text(encoding="utf-8")
        displayed = validation_display(card["prior_validation"])
        raw_retained = "deviation_sign_accuracy_pct" in card["prior_validation"]
        return (
            displayed["direction_percentage_displayed"] is False
            and raw_retained
            and ("검증연도 수" in doc)
            and ("검증 적중/연도" not in doc),
            "cell-level rate suppressed; n and MAE retained; pooled rate descriptive",
        )

    record(
        "P05",
        normal,
        ["R07", "R12"],
        "검증연도 0–3개 조합의 화면 비율 생략",
        "n and MAE displayed, raw rate retained",
        sparse_display,
    )

    def same_class_transition():
        c = card["data_timing"]["classification_transition"]
        return (
            c["classification_code_unchanged"]
            and c["status"] == "verification_required"
            and (c["input_basis"] == "KSIC11_backcast")
            and (c["target_basis"] == "KSIC11_new_classification_published"),
            "same KSIC11 metadata flagged for verification, not asserted discontinuity",
        )

    record(
        "P06",
        normal,
        ["R03"],
        "동일 산업분류의 소급보정·신분류 적용 공표 구분",
        "verification required, no automatic discontinuity judgment",
        same_class_transition,
    )

    def audit_perturbation():
        q = test.copy()
        idx = q.index[
            (q.target_year == 2025)
            & (q.region_code == "KR011")
            & (q.industry_code == "BTE")
        ]
        q.loc[idx, "target_logpoints"] = 0.0
        q.loc[idx, "employment_target_persons"] = q.loc[idx, "employment_input_persons"]
        newer = make_card(
            q,
            val,
            selection,
            root / "analysis_harmonized/results/main/model_ridge_alpha1000.joblib",
            manifest,
        )
        oldaudit = card["historical_outcome_audit"]["large_change_audit"]
        newaudit = newer["historical_outcome_audit"]["large_change_audit"]
        return (
            oldaudit["flagged"]
            and (not newaudit["flagged"])
            and (newer["decision_basis_sha256"] == card["decision_basis_sha256"]),
            "audit flag changes when observed outcome changes; decision basis SHA-256 invariant",
        )

    record(
        "M03",
        meta,
        ["R05", "R07"],
        "서울 사후 실제값을 무증감 값으로 교체",
        "audit warning changes; decision basis invariant",
        audit_perturbation,
    )
    df = pd.DataFrame(results)
    df.to_csv(out / "fault_injection_results.csv", index=False, encoding="utf-8-sig")
    requirements = {
        "R01": "입력 공표·기준기간이 판단시점을 초과하는 경우 운영 사용 보류",
        "R02": "당시 자료 개정본의 이용 가능성 확인",
        "R03": "동일 조사간격과 산업분류 유지",
        "R04": "행정경계 및 가용지역 구성 명시",
        "R05": "검증 선정 기준모형 보존 및 비교값 구분",
        "R06": "자료·모형·근거 해시의 무결성 확인",
        "R07": "평가 실제값과 사전 검증 근거의 분리",
        "R08": "검토기록 필수필드 충족",
        "R09": "정의되지 않은 개인식별 필드 배제",
        "R10": "기관승인·정책집행 상태의 자동 부여 금지",
    }
    requirements.update(
        R03="동일 조사간격·산업분류 및 소급보정·신분류 적용 공표 상태 구분",
        R11="상수 기준모형을 개별 관측의 증가 신호로 표시하지 않음",
        R12="0–3개 검증연도 조합에서 방향일치율을 숨기고 사례수·MAE 제시",
    )
    coverage = []
    for rid, description in requirements.items():
        match = [r for r in results if rid in r["requirements"].split(";")]
        coverage.append(
            {
                "requirement_id": rid,
                "requirement": description,
                "test_ids": ";".join((r["test_id"] for r in match)),
                "tested": bool(match),
                "all_expected_results": all((r["passed"] for r in match)),
                "denominator_scope": "이 v8 서비스 시연에서 명세한 12개 기술 요구사항; 법령 전체·보안 전체의 커버리지가 아님",
            }
        )
    pd.DataFrame(coverage).to_csv(
        out / "requirement_coverage.csv", index=False, encoding="utf-8-sig"
    )
    summary = {
        "fault_injection_detected": int(df[df.category == negative].passed.sum()),
        "fault_injection_total": int((df.category == negative).sum()),
        "positive_control_passed": int(df[df.category == normal].passed.sum()),
        "positive_control_total": int((df.category == normal).sum()),
        "metamorphic_passed": int(df[df.category == meta].passed.sum()),
        "metamorphic_total": int((df.category == meta).sum()),
        "requirements_tested": sum((x["tested"] for x in coverage)),
        "requirements_defined": len(coverage),
        "all_passed": bool(df.passed.all()),
        "scope": "합성 결함과 실제 저장예측에 대한 인공적·형성적 기술평가; 일반 결함 탐지율·현장 효과·사용성·법적 적합성 평가 아님",
        "actual_participants": 0,
    }
    dump(summary, out / "technical_summary.json")
    assert summary["all_passed"]
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-root", type=Path, required=True)
    ap.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent / "outputs"
    )
    args = ap.parse_args()
    root = args.package_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    relative = "analysis_harmonized/results/main/"
    paths = [
        relative + x
        for x in [
            "test_predictions.csv",
            "validation_predictions.csv",
            "selection_before_test.json",
            "model_ridge_alpha1000.joblib",
        ]
    ]
    manifest = json.loads(
        (Path(__file__).parent / "input_contract_sha256.json").read_text(
            encoding="utf-8"
        )
    )
    test = pd.read_csv(root / paths[0])
    val = pd.read_csv(root / paths[1])
    selection = json.loads((root / paths[2]).read_text(encoding="utf-8"))
    validate_service(test, val, selection, manifest, root)
    matrix = build_matrix(test, val, selection)
    validate_matrix(matrix)
    matrix.to_csv(out / "matrix_2025.csv", index=False, encoding="utf-8-sig")
    summary = (
        matrix.groupby("superregion", sort=False)
        .apply(
            lambda x: pd.Series(
                {
                    "nominal_industries": len(x),
                    "available_industries": int((x.available_regions_n > 0).sum()),
                    "complete_industries": int((x.coverage_status == "완전").sum()),
                    "partial_industries": int((x.coverage_status == "부분").sum()),
                    "missing_industries": int((x.coverage_status == "자료없음").sum()),
                    "above_baseline": int((x.relative_deviation_class == "상회").sum()),
                    "near_baseline": int((x.relative_deviation_class == "근접").sum()),
                    "below_baseline": int((x.relative_deviation_class == "하회").sum()),
                    "validation_comparator_worse": int(
                        (x.aggregate_mae_difference > 0).sum()
                    ),
                    "validation_sign_matched": int(x.deviation_sign_matches.sum()),
                    "validation_region_industry_year_n": int(x.validation_year_n.sum()),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    summary.to_csv(out / "matrix_2025_summary.csv", index=False, encoding="utf-8-sig")
    card = make_card(test, val, selection, root / paths[3], manifest)
    validate_card(card)
    dump(card, out / "evidence_card_2025_seoul_BTE.json")
    render_html(card, matrix, out / "evidence_dashboard_2025.html")
    dump(manifest, out / "input_manifest.json")
    inherited = classify_inherited(root, out)
    technical = run_tests(root, out, test, val, selection, manifest, matrix, card)
    claims = {
        "test_2025_source_cells": int((test.target_year == 2025).sum()),
        "matrix_nominal_cells": len(matrix),
        "matrix_available_cells": int((matrix.available_regions_n > 0).sum()),
        "matrix_complete_cells": int((matrix.coverage_status == "완전").sum()),
        "matrix_partial_cells": int((matrix.coverage_status == "부분").sum()),
        "matrix_missing_cells": int((matrix.coverage_status == "자료없음").sum()),
        "relative_deviation_counts": matrix.relative_deviation_class.value_counts().to_dict(),
        "validation_comparator_worse_cells": int(
            (matrix.aggregate_mae_difference > 0).sum()
        ),
        "validation_matching_region_industry_year_n": int(
            matrix.validation_year_n.sum()
        ),
        "validation_sign_matched": int(matrix.deviation_sign_matches.sum()),
        "validation_sign_accuracy_pct": float(
            100 * matrix.deviation_sign_matches.sum() / matrix.validation_year_n.sum()
        ),
        "validation_year_n_range": [
            int(matrix.loc[matrix.available_regions_n > 0, "validation_year_n"].min()),
            int(matrix.validation_year_n.max()),
        ],
        "case": card,
        "inherited_test_classification": inherited,
        "technical": technical,
        "interpretation": [
            "권역 집계는 기준고용에 각 모형의 exp(logpoint/100)를 적용한 수준값을 합산한 후 로그변동으로 환산함",
            "기준모형 대비 편차는 두 권역 집계 예측값의 차이; ±0.5는 기술 시연용 사후 설정 구간이며 최적화하지 않음",
            "검증 적중률은 2025 가용지역과 정확히 같은 구성으로 2020–2022년을 각각 집계한 후 비교함; 완전구성 없는 연도 제외",
            "주검증 지표는 MAE 차이(릿지−기준); 상대편차 방향 적중률 자체는 추가 예측가치의 증거가 아님",
            "과거 검증 행렬은 학습자료 적합 모형; 2025 비교예측은 학습·검증자료 재적합 모형이므로 같은 모형 추정치의 실시간 추적은 아님",
            "2025 평가표본은 사후 가용성과 경계 제외를 적용하여 선택되었으므로 운영 당시 예측가능 대상의 재현이 아님",
            "B–E 산업집계는 제조업 단독 수치로 해석하지 않음",
        ],
    }
    dump(claims, out / "claims_for_manuscript.json")
    print(
        json.dumps(
            {
                k: v
                for k, v in claims.items()
                if k not in ["case", "inherited_test_classification", "interpretation"]
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
