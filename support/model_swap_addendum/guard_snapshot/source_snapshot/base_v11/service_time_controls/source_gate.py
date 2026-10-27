from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

VERSION = "source-time-controls-5.0.0"
ROLES = {"retrospective_diagnostic", "operational_prediction"}
BOUNDARIES = {"stable_verified", "harmonized_verified", "unresolved", "unknown"}
VINTAGES = {"archived_vintage_verified", "current_snapshot_only", "unknown"}
LABELS = {
    "retrospective_diagnostic": "현재 스냅숏에 근거한 회고적 고용변동 진단·기술 시연",
    "operational_prediction": "정보시점 적격성의 기술 점검 요청(운영 배포·기관승인 아님)",
}


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _date(value: Any, field: str, nullable: bool = False) -> date | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field}: use ISO YYYY-MM-DD or explicit null where allowed")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field}: use ISO YYYY-MM-DD")
    return parsed


def _period(value: Any, field: str) -> tuple[int, int]:
    if not isinstance(value, str) or len(value) != 7 or value[4] != "-":
        raise ValueError(f"{field}: use YYYY-MM reference period")
    try:
        d = date.fromisoformat(value + "-01")
    except ValueError as exc:
        raise ValueError(f"{field}: invalid reference period") from exc
    return (d.year, d.month)


def _month_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return (b[0] - a[0]) * 12 + b[1] - a[1]


def evaluate_source_gate(request: dict) -> dict:
    role = request.get("role")
    if role not in ROLES:
        raise ValueError(
            "role must be retrospective_diagnostic or operational_prediction"
        )
    intended = _date(request.get("intended_decision_date"), "intended_decision_date")
    target_period = _period(request.get("target_refperiod"), "target_refperiod")
    source_list = request.get("sources")
    if not isinstance(source_list, list) or not source_list:
        raise ValueError("sources must contain at least one input-source record")
    seen = set()
    issues: list[dict] = []
    normalized = []

    def issue(code: str, source_id: str | None, detail: str) -> None:
        issues.append({"code": code, "source_id": source_id, "detail": detail})

    for source in source_list:
        if not isinstance(source, dict):
            raise ValueError("each source record must be an object")
        sid = source.get("source_id")
        if not isinstance(sid, str) or not sid.strip() or sid in seen:
            raise ValueError("source_id must be nonempty and unique")
        seen.add(sid)
        reference = _period(source.get("source_refperiod"), sid + ".source_refperiod")
        previous = _period(
            source.get("previous_refperiod"), sid + ".previous_refperiod"
        )
        release = _date(source.get("release_date"), sid + ".release_date", True)
        vintage = _date(source.get("vintage_date"), sid + ".vintage_date", True)
        interval = source.get("observation_interval_months")
        if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
            raise ValueError(
                sid + ".observation_interval_months must be a positive integer"
            )
        if _month_distance(previous, reference) != interval:
            raise ValueError(sid + ": interval metadata contradicts reference periods")
        classification = source.get("classification")
        if classification is not None and (
            not isinstance(classification, str) or not classification.strip()
        ):
            raise ValueError(sid + ".classification must be nonempty or null")
        boundary = source.get("boundary_status")
        if boundary not in BOUNDARIES:
            raise ValueError(sid + ".boundary_status not recognized")
        vintage_status = source.get("vintage_availability_status")
        if vintage_status not in VINTAGES:
            raise ValueError(sid + ".vintage_availability_status not recognized")
        evidence_ref = source.get("vintage_evidence_ref")
        if vintage_status == "archived_vintage_verified" and (
            not (isinstance(evidence_ref, str) and evidence_ref.strip())
        ):
            raise ValueError(
                sid + ": archived_vintage_verified requires evidence reference"
            )
        clean = {
            "source_id": sid,
            "source_refperiod": source["source_refperiod"],
            "previous_refperiod": source["previous_refperiod"],
            "release_date": source.get("release_date"),
            "vintage_date": source.get("vintage_date"),
            "classification": classification,
            "boundary_status": boundary,
            "observation_interval_months": interval,
            "vintage_availability_status": vintage_status,
            "vintage_evidence_ref": evidence_ref,
            "release_evidence_ref": source.get("release_evidence_ref"),
        }
        normalized.append(clean)
        if release is None:
            issue(
                "release_date_unknown",
                sid,
                "원계열의 해당 회차 공표일을 확인할 수 없음",
            )
        elif release > intended:
            issue("release_after_decision", sid, "원계열 공표일이 의도한 판단시점 뒤임")
        if vintage is None:
            issue(
                "vintage_date_unknown", sid, "사용한 값의 보존 빈티지 일자가 미확인임"
            )
        elif vintage > intended:
            issue(
                "vintage_after_decision",
                sid,
                "사용한 빈티지 일자가 의도한 판단시점 뒤임",
            )
        if vintage_status != "archived_vintage_verified":
            issue(
                "historical_vintage_unverified",
                sid,
                "과거 공표일만으로 현재 소급계열 값의 당시 이용가능성이 증명되지 않음",
            )
        if vintage is not None and release is not None and (vintage < release):
            issue(
                "vintage_precedes_release",
                sid,
                "보존 빈티지 일자가 원계열 공표일보다 앞서므로 출처 대조 필요",
            )
        if interval != 12:
            issue(
                "nonannual_observation_interval",
                sid,
                "12개월 변화 계약과 관측 간격이 다름",
            )
        if reference[1] != target_period[1]:
            issue("reference_month_mismatch", sid, "입력 기준월과 목표 기준월이 다름")
        if reference >= target_period:
            issue(
                "input_not_before_target",
                sid,
                "입력 기준기간이 목표 기준기간보다 앞서지 않음",
            )
        if date(reference[0], reference[1], 1) > intended:
            issue(
                "reference_period_after_decision", sid, "입력 기준기간이 판단시점 뒤임"
            )
        if boundary not in {"stable_verified", "harmonized_verified"}:
            issue(
                "boundary_unresolved", sid, "행정구역 경계의 비교가능성이 확인되지 않음"
            )
        if classification is None:
            issue("classification_unknown", sid, "산업분류 판이 미확인임")
    classes = {
        s["classification"] for s in normalized if s["classification"] is not None
    }
    if len(classes) > 1:
        issue("mixed_classification", None, "동일 요청에 산업분류 판이 혼재함")
    if len({s["observation_interval_months"] for s in normalized}) > 1:
        issue("mixed_observation_intervals", None, "동일 요청에 관측 간격이 혼재함")
    if role == "operational_prediction" and date(*target_period, 1) <= intended:
        issue(
            "target_not_future", None, "운영 예측 목표 기준기간이 판단시점 이후가 아님"
        )
    basis = {
        "version": VERSION,
        "role": role,
        "intended_decision_date": intended.isoformat(),
        "target_refperiod": request["target_refperiod"],
        "sources": normalized,
        "issues": issues,
    }
    eligible = not issues
    disposition = (
        "retrospective_only"
        if role == "retrospective_diagnostic"
        else "metadata_eligible_research_only"
        if eligible
        else "hold_operational_prediction"
    )
    return {
        **basis,
        "disposition": disposition,
        "display_label": LABELS[role],
        "metadata_eligible_for_requested_cutoff": eligible,
        "automatic_policy_action_allowed": False,
        "production_deployment_validated": False,
        "legal_compliance_certified": False,
        "human_or_policy_effect_evaluated": False,
        "source_gate_basis_sha256": canonical_hash(basis),
        "interpretation": "연구자 자료 검토 규칙의 기술 구현이며 특정 법조문의 직접 의무나 준법 인증이 아님",
    }


def decorate_evidence(bundle: dict, request: dict) -> dict:
    gate = evaluate_source_gate(request)
    result = {
        "wrapper_version": VERSION,
        "source_gate": gate,
        "evidence": copy.deepcopy(bundle),
        "baseline_rule": "상위 근거묶음의 검증 선택 기본값과 비교모형을 유지하며 이 게이트는 모형 승격을 수행하지 않음",
        "evidence_scope": "원연구 2021–2023년과 동일 상반기 보완 분석 2023–2025년은 별도 코호트로 관리",
        "can_display_retrospective_evidence": request["role"]
        == "retrospective_diagnostic",
        "can_issue_operational_prediction": False,
        "automatic_policy_action_allowed": False,
    }
    result["wrapper_sha256"] = canonical_hash(result)
    return result


def verify_decorated(result: dict) -> bool:
    return result.get("wrapper_sha256") == canonical_hash(
        {k: v for k, v in result.items() if k != "wrapper_sha256"}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    result = (
        decorate_evidence(json.loads(args.bundle.read_text(encoding="utf-8")), request)
        if args.bundle
        else evaluate_source_gate(request)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "disposition": result.get(
                    "disposition", result.get("source_gate", {}).get("disposition")
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
