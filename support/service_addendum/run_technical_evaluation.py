"""Freeze explicit fixtures, then compare old and revised research-only guards.

Usage: run once with --freeze-only, then without it. Never uses validator output
to create expected labels. Case counts describe specifications, not people.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import html
import json
import random
from pathlib import Path

from workflow_guard import canonical_hash, card_hash, load_original, validate

SEED = 20261005


def dump(value, path):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def bind(env, rehash=True):
    if rehash:
        env["card"]["decision_basis_sha256"] = card_hash(env["card"])
    ch = env["card"]["decision_basis_sha256"]
    rh = canonical_hash(env["request"])
    env["review"]["evidence_sha256"] = ch
    env["receipt"] = {"card_sha256": ch, "request_sha256": rh}
    env["current_state"] = dict(env["receipt"])


def prediction(env, value):
    c = env["card"]
    old = c["learned_comparator"]["logpoints"]
    c["learned_comparator"]["logpoints"] = value
    c["learned_comparator"]["direction"] = (
        "증가" if value > 0.5 else "감소" if value < -0.5 else "유지 범위"
    )
    diff = value - c["default_estimate"]["logpoints"]
    c["relative_deviation"]["logpoints"] = diff
    c["relative_deviation"]["class"] = (
        "상회" if diff > 0.5 else "하회" if diff < -0.5 else "근접"
    )
    c["linear_explanation"]["intercept_logpoints"] += value - old
    c["linear_explanation"]["reconstructed_logpoints"] = value


def build_cases(source_root):
    card = json.loads(
        (
            source_root / "reproduced_service/evidence_card_2025_seoul_BTE.json"
        ).read_text(encoding="utf-8")
    )
    card["data_timing"]["input_source_vintage"] = "2024-10-08"
    card["data_timing"]["historical_vintage_verified"] = True
    base = {
        "fixture_status": "SYNTHETIC_RESEARCH_TEST_ONLY: numerical card template from actual stored outputs; metadata/review/state are invented test fixtures, not historical archives",
        "card": card,
        "request": {
            "role": "operational_prediction",
            "intended_decision_date": "2024-12-31",
            "target_refperiod": "2025-04",
            "fixture_status": "SYNTHETIC_TEST_ONLY",
            "sources": [
                {
                    "source_id": "SYNTHETIC_PRIMARY",
                    "source_refperiod": "2024-04",
                    "previous_refperiod": "2023-04",
                    "release_date": "2024-10-08",
                    "vintage_date": "2024-10-08",
                    "classification": "KSIC11",
                    "boundary_status": "stable_verified",
                    "observation_interval_months": 12,
                    "vintage_availability_status": "archived_vintage_verified",
                    "vintage_evidence_ref": "SYNTHETIC_ONLY",
                    "release_evidence_ref": "SYNTHETIC_ONLY",
                }
            ],
        },
        "review": {
            "status": "synthetic_review_complete",
            "reviewer_role": "synthetic_research_reviewer",
            "reference_materials": ["SYNTHETIC_REFERENCE"],
            "reason_for_review": "synthetic consistency test",
            "warnings_acknowledged": True,
        },
    }
    bind(base)
    cases = []

    def add(cid, family, desc, fn, expected=False, refresh=False, compound=False):
        env = copy.deepcopy(base)
        fn(env)
        if refresh:
            bind(env)
        cases.append(
            {
                "case_id": cid,
                "family": family,
                "description": desc,
                "expected_block": expected,
                "secondary_compound": compound,
                "fixture": env,
            }
        )

    def source_update(env, values, sync_vintage=False):
        env["request"]["sources"][0].update(values)
        if sync_vintage and "vintage_date" in values:
            env["card"]["data_timing"]["input_source_vintage"] = values["vintage_date"]

    def retrospective(env):
        env["request"]["role"] = "retrospective_diagnostic"
        source_update(
            env,
            {
                "vintage_date": "2026-09-26",
                "vintage_availability_status": "current_snapshot_only",
                "vintage_evidence_ref": None,
            },
            True,
        )
        env["card"]["data_timing"]["historical_vintage_verified"] = False

    def two_sources(env):
        s = copy.deepcopy(env["request"]["sources"][0])
        s["source_id"] = "SYNTHETIC_SECONDARY"
        env["request"]["sources"].append(s)

    def nonzero_validation(env):
        env["card"]["prior_validation"].update(
            validation_year_n=3,
            aggregate_baseline_mae=2.0,
            aggregate_learned_mae=1.5,
            aggregate_mae_difference=-0.5,
        )

    def past_retrospective(env):
        retrospective(env)
        env["request"]["target_refperiod"] = "2024-04"
        source_update(
            env, {"source_refperiod": "2023-04", "previous_refperiod": "2022-04"}
        )
        env["card"].update(target_year=2024, input_year=2023)

    normal = "normal_boundary"
    add("N01", normal, "Complete synthetic metadata and linked review", lambda x: None)
    add(
        "N02",
        normal,
        "Actual-card vintage retained in retrospective-only fixture",
        retrospective,
        refresh=True,
    )
    add(
        "N03",
        normal,
        "Release and vintage equal decision cutoff",
        lambda x: source_update(
            x, {"release_date": "2024-12-31", "vintage_date": "2024-12-31"}, True
        ),
        refresh=True,
    )
    add(
        "N04",
        normal,
        "Vintage alone equals decision cutoff",
        lambda x: source_update(x, {"vintage_date": "2024-12-31"}, True),
        refresh=True,
    )
    add(
        "N05",
        normal,
        "Outcome audit changes while decision fields and hash stay fixed",
        lambda x: x["card"]["historical_outcome_audit"].update(observed_logpoints=0.0),
    )
    add(
        "N06",
        normal,
        "JSON key order changes only",
        lambda x: x.update(card=dict(reversed(list(x["card"].items())))),
    )
    add(
        "N07",
        normal,
        "Prediction edit with coherent arithmetic and refreshed bindings",
        lambda x: prediction(x, 1.0),
        refresh=True,
    )
    add(
        "N08",
        normal,
        "Two distinct sources with same classification",
        two_sources,
        refresh=True,
    )
    add(
        "N09",
        normal,
        "Positive validation count with coherent MAE",
        nonzero_validation,
        refresh=True,
    )
    add(
        "N10",
        normal,
        "Relative deviation exactly plus 0.5 is near",
        lambda x: prediction(x, x["card"]["default_estimate"]["logpoints"] + 0.5),
        refresh=True,
    )
    add(
        "N11",
        normal,
        "Relative deviation exactly minus 0.5 is near",
        lambda x: prediction(x, x["card"]["default_estimate"]["logpoints"] - 0.5),
        refresh=True,
    )
    add(
        "N12",
        normal,
        "Learned prediction exactly zero",
        lambda x: prediction(x, 0.0),
        refresh=True,
    )

    def reverse_sources(x):
        two_sources(x)
        x["request"]["sources"].reverse()

    add(
        "N13",
        normal,
        "Source ordering edit with newly issued binding",
        reverse_sources,
        refresh=True,
    )
    add(
        "N14",
        normal,
        "Past target permitted only for retrospective review",
        past_retrospective,
        refresh=True,
    )

    tf = "time_metadata"
    time_specs = [
        ("T01", "Unknown release date", {"release_date": None}, False),
        ("T02", "Unknown vintage date", {"vintage_date": None}, True),
        (
            "T03",
            "Release after cutoff",
            {"release_date": "2025-01-01", "vintage_date": "2025-01-01"},
            True,
        ),
        ("T04", "Vintage after cutoff", {"vintage_date": "2025-01-01"}, True),
        (
            "T05",
            "Archived-vintage status unknown",
            {"vintage_availability_status": "unknown"},
            False,
        ),
        (
            "T06",
            "Boundary comparability unknown",
            {"boundary_status": "unknown"},
            False,
        ),
        (
            "T07",
            "Six-month observation interval",
            {"previous_refperiod": "2023-10", "observation_interval_months": 6},
            False,
        ),
        (
            "T10",
            "Archived-vintage evidence reference absent",
            {"vintage_evidence_ref": None},
            False,
        ),
        (
            "T11",
            "Boolean observation interval",
            {"observation_interval_months": True},
            False,
        ),
        (
            "T12",
            "Period interval contradicts metadata",
            {"previous_refperiod": "2023-05"},
            False,
        ),
    ]
    for cid, desc, vals, sync in time_specs:
        add(cid, tf, desc, lambda x, v=vals, s=sync: source_update(x, v, s), True, True)

    def mixed(x):
        two_sources(x)
        x["request"]["sources"][1]["classification"] = "KSIC10"

    add("T08", tf, "Mixed industrial classifications", mixed, True, True)

    def duplicate(x):
        two_sources(x)
        x["request"]["sources"][1]["source_id"] = "SYNTHETIC_PRIMARY"

    add("T09", tf, "Duplicate source identifiers", duplicate, True, True)

    fam = "integrity_schema"
    add(
        "I01",
        fam,
        "Card edited without recomputing hash",
        lambda x: x["card"]["default_estimate"].update(logpoints=99.0),
        True,
    )
    add(
        "I02",
        fam,
        "Automatic-action flag true despite recomputed hash",
        lambda x: x["card"].update(automatic_policy_action_allowed=True),
        True,
        True,
    )
    add(
        "I03",
        fam,
        "Required review reason missing",
        lambda x: x["review"].pop("reason_for_review"),
        True,
    )
    add(
        "I04",
        fam,
        "Undefined identifying review field",
        lambda x: x["review"].update(person_identifier="SYNTHETIC_NOT_REAL"),
        True,
    )
    add(
        "I05",
        fam,
        "Warning acknowledgement is string false",
        lambda x: x["review"].update(warnings_acknowledged="false"),
        True,
    )
    add(
        "I06",
        fam,
        "References supplied as scalar instead of list",
        lambda x: x["review"].update(reference_materials="SYNTHETIC_REFERENCE"),
        True,
    )
    add(
        "I07",
        fam,
        "Whitespace-only review reason",
        lambda x: x["review"].update(reason_for_review="   "),
        True,
    )

    fam = "numeric_semantics"
    add(
        "S01",
        fam,
        "Rehashed relative deviation contradicts predictions",
        lambda x: x["card"]["relative_deviation"].update(logpoints=10.0),
        True,
        True,
    )
    add(
        "S02",
        fam,
        "Rehashed relative-deviation label is reversed",
        lambda x: x["card"]["relative_deviation"].update(**{"class": "상회"}),
        True,
        True,
    )
    add(
        "S03",
        fam,
        "Rehashed learned direction label is wrong",
        lambda x: x["card"]["learned_comparator"].update(direction="증가"),
        True,
        True,
    )
    add(
        "S04",
        fam,
        "Rehashed input employment is negative",
        lambda x: x["card"].update(employment_input_persons=-1),
        True,
        True,
    )
    add(
        "S05",
        fam,
        "Rehashed explanation sum contradicts prediction",
        lambda x: x["card"]["linear_explanation"].update(intercept_logpoints=10.0),
        True,
        True,
    )
    add(
        "S06",
        fam,
        "MAE displayed with zero validation observations",
        lambda x: x["card"]["prior_validation"].update(aggregate_baseline_mae=1.0),
        True,
        True,
    )
    add(
        "S07",
        fam,
        "Boolean validation count",
        lambda x: x["card"]["prior_validation"].update(validation_year_n=False),
        True,
        True,
    )
    add(
        "S08",
        fam,
        "Boolean prediction value",
        lambda x: x["card"]["learned_comparator"].update(logpoints=True),
        True,
        True,
    )

    fam = "record_linkage"
    add(
        "L01",
        fam,
        "Review refers to different card hash",
        lambda x: x["review"].update(evidence_sha256="f" * 64),
        True,
    )
    add(
        "L02",
        fam,
        "Card is stale relative to trusted current-card state",
        lambda x: x["current_state"].update(card_sha256="f" * 64),
        True,
    )
    add(
        "L03",
        fam,
        "Request is stale relative to trusted current-request state",
        lambda x: x["current_state"].update(request_sha256="f" * 64),
        True,
    )
    add(
        "L04",
        fam,
        "Receipt binds another card",
        lambda x: x["receipt"].update(card_sha256="f" * 64),
        True,
    )
    add(
        "L05",
        fam,
        "Still-eligible source metadata edited without refreshing receipt",
        lambda x: x["request"]["sources"][0].update(release_date="2024-10-07"),
        True,
    )
    add(
        "L06",
        fam,
        "Rebound card target year differs from request",
        lambda x: x["card"].update(target_year=2026),
        True,
        True,
    )
    add(
        "L07",
        fam,
        "Rebound card input year differs from request",
        lambda x: x["card"].update(input_year=2023),
        True,
        True,
    )
    add(
        "L08",
        fam,
        "Rebound card vintage differs from request",
        lambda x: x["card"]["data_timing"].update(input_source_vintage="2024-10-09"),
        True,
        True,
    )
    add(
        "L09",
        fam,
        "Card says historical vintage unverified in operational-cutoff request",
        lambda x: x["card"]["data_timing"].update(historical_vintage_verified=False),
        True,
        True,
    )

    # Secondary multi-fault specimens are reported separately; never added to primary denominator.
    mutations = [
        (
            "C01",
            "Unknown release plus stale review",
            lambda x: (
                source_update(x, {"release_date": None}),
                bind(x),
                x["review"].update(evidence_sha256="f" * 64),
            ),
        ),
        (
            "C02",
            "Wrong band plus stale current card",
            lambda x: (
                x["card"]["relative_deviation"].update(**{"class": "상회"}),
                bind(x),
                x["current_state"].update(card_sha256="f" * 64),
            ),
        ),
        (
            "C03",
            "Unknown boundary plus string acknowledgement",
            lambda x: (
                source_update(x, {"boundary_status": "unknown"}),
                bind(x),
                x["review"].update(warnings_acknowledged="false"),
            ),
        ),
        (
            "C04",
            "Rehashed incorrect deviation plus wrong receipt",
            lambda x: (
                x["card"]["relative_deviation"].update(logpoints=10.0),
                bind(x),
                x["receipt"].update(card_sha256="f" * 64),
            ),
        ),
        (
            "C05",
            "Current snapshot only plus inconsistent target year",
            lambda x: (
                source_update(
                    x, {"vintage_availability_status": "current_snapshot_only"}
                ),
                x["card"].update(target_year=2026),
                bind(x),
            ),
        ),
    ]
    for cid, desc, fn in mutations:
        add(cid, "compound_secondary", desc, fn, True, compound=True)
    return sorted(cases, key=lambda c: c["case_id"])


def csvwrite(rows, path):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    frozen = out / "frozen_cases.json"
    if args.freeze_only:
        if frozen.exists():
            raise RuntimeError(
                "Frozen case file already exists; preserve rather than overwrite."
            )
        cases = build_cases(args.source_root)
        dump(
            {
                "seed": SEED,
                "protocol_sha256": hashlib.sha256(
                    args.protocol.read_bytes()
                ).hexdigest(),
                "cases": cases,
            },
            frozen,
        )
        print(
            json.dumps(
                {
                    "frozen_cases": len(cases),
                    "sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
                }
            )
        )
        return
    if not frozen.exists():
        raise RuntimeError("Run --freeze-only before any benchmark execution.")
    spec = json.loads(frozen.read_text(encoding="utf-8"))
    cases = spec["cases"]
    if (
        spec["protocol_sha256"]
        != hashlib.sha256(args.protocol.read_bytes()).hexdigest()
    ):
        raise RuntimeError("Protocol changed after fixture freeze.")
    modules = load_original(args.source_root)
    configs = {
        "original_composed": dict(enabled=("T", "I"), original=True),
        "flat_same_predicates": dict(flat=True),
        "linked_full": {},
        "linked_without_T": dict(enabled=("I", "S", "L")),
        "linked_without_S": dict(enabled=("T", "I", "L")),
        "linked_without_L": dict(enabled=("T", "I", "S")),
    }
    order = list(cases)
    random.Random(SEED).shuffle(order)
    rows = []
    traces = []
    for case in order:
        for name, kwargs in configs.items():
            result = validate(copy.deepcopy(case["fixture"]), modules, **kwargs)
            blocked = not result["research_review_permitted"]
            outcome = (
                "correct_block"
                if blocked and case["expected_block"]
                else "false_block"
                if blocked
                else "miss"
                if case["expected_block"]
                else "correct_permit"
            )
            rows.append(
                {
                    "case_id": case["case_id"],
                    "configuration": name,
                    "family": case["family"],
                    "description": case["description"],
                    "secondary_compound": case["secondary_compound"],
                    "expected_block": case["expected_block"],
                    "observed_block": blocked,
                    "outcome": outcome,
                    "status": result["status"],
                    "codes": ";".join(e["code"] for e in result["errors"]),
                    "operational_prediction_permitted": result[
                        "operational_prediction_permitted"
                    ],
                }
            )
            traces.append(
                {"case_id": case["case_id"], "configuration": name, "result": result}
            )
    rows.sort(key=lambda r: (r["case_id"], r["configuration"]))
    csvwrite(rows, out / "case_results.csv")
    dump(traces, out / "all_traces.json")
    summaries = []
    for name in configs:
        for family in ["all_primary"] + sorted({c["family"] for c in cases}):
            group = [
                r
                for r in rows
                if r["configuration"] == name
                and (
                    (not r["secondary_compound"])
                    if family == "all_primary"
                    else r["family"] == family
                )
            ]
            summaries.append(
                {
                    "configuration": name,
                    "family": family,
                    "fault_n": sum(r["expected_block"] for r in group),
                    "normal_n": sum(not r["expected_block"] for r in group),
                    **{
                        s: sum(r["outcome"] == s for r in group)
                        for s in [
                            "correct_block",
                            "miss",
                            "false_block",
                            "correct_permit",
                        ]
                    },
                }
            )
    csvwrite(summaries, out / "summary_by_family.csv")
    primary = [
        r
        for r in summaries
        if r["family"] == "all_primary" and r["configuration"] != "flat_same_predicates"
    ]
    csvwrite(primary, out / "manuscript_table.csv")
    equivalence = all(
        next(
            r["observed_block"]
            for r in rows
            if r["case_id"] == c["case_id"]
            and r["configuration"] == "flat_same_predicates"
        )
        == next(
            r["observed_block"]
            for r in rows
            if r["case_id"] == c["case_id"] and r["configuration"] == "linked_full"
        )
        for c in cases
    )
    info = {
        "seed": SEED,
        "primary_faults": sum(
            c["expected_block"] and not c["secondary_compound"] for c in cases
        ),
        "primary_controls": sum(
            not c["expected_block"] and not c["secondary_compound"] for c in cases
        ),
        "secondary_compounds": sum(c["secondary_compound"] for c in cases),
        "same_predicate_control_equivalent": equivalence,
        "primary_summary": primary,
        "frozen_cases_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "protocol_sha256": spec["protocol_sha256"],
        "actual_human_participants": 0,
        "scope": "Synthetic formative consistency checking only. No population detection rate, user utility, authenticity or operational validation.",
    }
    dump(info, out / "technical_summary.json")
    for cid, name in [
        ("N02", "demo_retrospective_valid"),
        ("L01", "demo_stale_review_blocked"),
        ("S01", "demo_inconsistent_arithmetic_blocked"),
    ]:
        fixture = next(c["fixture"] for c in cases if c["case_id"] == cid)
        dump(fixture, out / (name + "_input.json"))
        dump(validate(fixture, modules), out / (name + "_output.json"))
    header = "<tr><th>Configuration</th><th>Faults blocked</th><th>Missed</th><th>False blocks</th><th>Valid permitted</th></tr>"
    body = "".join(
        f"<tr><td>{html.escape(r['configuration'])}</td><td>{r['correct_block']}/{r['fault_n']}</td><td>{r['miss']}</td><td>{r['false_block']}/{r['normal_n']}</td><td>{r['correct_permit']}/{r['normal_n']}</td></tr>"
        for r in primary
    )
    case_rows = "".join(
        f"<tr><td>{r['case_id']}</td><td>{html.escape(r['configuration'])}</td><td>{html.escape(r['description'])}</td><td>{r['outcome']}</td><td>{html.escape(r['codes'])}</td></tr>"
        for r in rows
    )
    doc = f"""<!doctype html><html lang="ko"><meta charset="utf-8"><title>연구용 연결 검증 비교 결과</title><style>body{{font:15px system-ui;max-width:1400px;margin:35px auto;padding:20px;color:#193148}}td,th{{padding:10px;border:1px solid #ccd7df;text-align:left}}table{{border-collapse:collapse;width:100%}}p{{line-height:1.8}}input{{padding:12px;width:60%}}.warn{{background:#fff3d8;padding:15px}}</style><h1>연구용 연결 검증 비교 결과</h1><p class="warn">합성 정상·경계·결함 사례의 형성적 기술평가입니다. 실제 사용자 수는 0명이며, 허용 상태는 연구용 검토 완료에 한정됩니다. 기관승인·정책집행·운영 예측을 허용하지 않습니다.</p><p>기존 검증, 신규 전체 검증, 시점·의미정합성·연결 모듈 제거의 5개 구성을 같은 입력에서 비교했습니다. 추가 차단은 명시적 검사조건의 추가 효과이며 인터페이스나 체크리스트 대비 사용자효과가 아닙니다. 해시는 진본성이나 악의적 조작 방지를 보장하지 않습니다.</p><h2>주 평가: 단일 결함 {info["primary_faults"]}건, 정상·경계 {info["primary_controls"]}건</h2><table>{header}{body}</table><p>복합 결함 {info["secondary_compounds"]}건은 아래 원시 결과에 별도 포함되며 위 분모에 합산하지 않습니다. 원시 결과의 flat_same_predicates는 같은 검사함수를 다른 출력 메타데이터로 재호출한 중복 일치 점검입니다. 독립 구현 비교가 아니므로 주 비교표에서 제외했습니다.</p><h2>사례별 실행 결과</h2><input id="search" placeholder="사례, 구성, 오류코드 검색" oninput="for(let r of document.querySelectorAll('#cases tbody tr'))r.hidden=!r.textContent.toLowerCase().includes(this.value.toLowerCase())"><table id="cases"><thead><tr><th>ID</th><th>구성</th><th>사례</th><th>결과</th><th>검출 코드</th></tr></thead><tbody>{case_rows}</tbody></table></html>"""
    (out / "technical_comparison_dashboard.html").write_text(doc, encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--freeze-only", action="store_true")
    run(ap.parse_args())
