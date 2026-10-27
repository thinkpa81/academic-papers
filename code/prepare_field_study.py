#!/usr/bin/env python3
"""Create real-data-derived synthetic tasks and EMPTY observation templates.
No participant responses, timings, satisfaction scores or study effects created.
"""

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dump(x, p):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    out = ROOT / "field_study"
    out.mkdir(exist_ok=True)
    src = json.loads(
        (
            ROOT / "support/model_swap_addendum/frozen/protocol_and_cases.json"
        ).read_text()
    )
    controls = [
        c
        for c in src["cases"]
        if c["scope"] == "coherent_control" and c["model"] == "ridge_alpha1000"
    ]
    tasks = []
    answers = []
    for i in range(12):
        c = controls[i * 7]
        e = c["fixture"]
        card = e["card"]
        kind = i % 4
        issue = [
            "없음",
            "이전 근거를 참조한 검토기록",
            "화면 검증건수와 근거 집계 불일치",
            "등록 모형 계수와 제출 계수 불일치",
        ][kind]
        tasks.append(
            {
                "task_id": f"T{i + 1:02d}",
                "region": card["region_name"],
                "industry": card["industry_code"],
                "target_year": 2025,
                "model": "ridge_alpha1000",
                "prediction": card["learned_comparator"]["logpoints"],
                "baseline": card["default_estimate"]["logpoints"],
                "validation_n": card["prior_validation"]["validation_year_n"],
                "validation_mae_difference": card["prior_validation"][
                    "aggregate_mae_difference"
                ],
                "input_employment": card["employment_input_persons"],
                "evidence_status": issue,
                "question": "현재 근거에 대한 연구용 검토 완료를 허용할 것인가?",
                "choices": ["완료 허용", "보완 후 재검토"],
                "secondary_question": "판단에 사용한 근거와 필요한 후속 조치를 한 문장으로 작성하시오.",
                "source": "실제 집계 예측값과 합성 검토 상태를 결합한 평가 과업; 실제 업무 기록 아님",
            }
        )
        answers.append(
            {
                "task_id": f"T{i + 1:02d}",
                "correct_action": "allow" if kind == 0 else "revise",
                "critical_issue": issue,
                "rubric": "행동 정답 1점; 핵심 근거 언급 1점; 적절한 후속 조치 1점. 검증사례가 0개여도 자료·표시·기록이 정합하면 연구용 검토 자체는 가능하며 정책 자동조치와 구별한다.",
            }
        )
    dump(tasks, out / "tasks.json")
    with (out / "assessor_answer_key.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=answers[0].keys())
        w.writeheader()
        w.writerows(answers)
    assignments = []
    rng = random.Random(20261025)
    conditions = ["table_warning", "card_warning", "table_block", "card_block"]
    for p in range(12):
        order = list(range(12))
        rng.shuffle(order)
        for n, i in enumerate(order, 1):
            assignments.append(
                {
                    "participant_code": f"P{p + 1:02d}",
                    "order": n,
                    "task_id": tasks[i]["task_id"],
                    "condition": conditions[(i + p) % 4],
                }
            )
    with (out / "counterbalanced_assignment.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=assignments[0].keys())
        w.writeheader()
        w.writerows(assignments)
    fields = [
        "participant_code",
        "task_id",
        "condition",
        "intended_action_before_gate",
        "response_seconds_before_gate",
        "reason_text",
        "evidence_score_0_2",
        "final_system_disposition",
        "rater_id",
        "consent_recorded",
    ]
    with (out / "responses_EMPTY.csv").open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerow(fields)
    protocol = """# 지역고용 예측근거 서비스 현장평가 실행계획

현재 상태: 준비 완료, 참여자 모집 및 평가 미실시. 실제 관측자료는 0행이다.

## 목적과 설계
같은 내용을 제시한 표와 근거 카드가 담당자의 판단 정확도와 검토시간에 미치는 영향을 비교한다. 표시 형식 2수준과 제어 방식 2수준을 교차한다. 모든 조건에 동일한 경고 문구를 제시하고, 차단 조건에서만 시스템이 부적합 검토의 최종 저장을 제한한다. 화면 형식에 따른 정보량 차이를 없앤다.

12개 과업의 수치는 보존된 실제 집계통계 예측에서 가져왔고, 기록 상태는 실험용으로 구성하였다. 현장평가자는 tasks.json의 동일 항목으로 표·카드를 제작하고, 내용 일치를 두 명이 확인한다. 임의의 시각화나 추가 설명을 한 조건에만 넣지 않는다. 이 패키지는 과업과 배정표를 제공하며 실행 화면은 기관 환경에 맞춰 구현한다.

첫 12명은 절차·문항·소요시간을 점검하는 예비평가의 계획 인원이다. 통계적 효과 검출력이 확보된 표본수라는 주장을 하지 않는다. 지역인적자원개발위원회·지자체 관련 실무경험, 직무 및 경력을 비식별 범주로 기록하고, 기관 절차에 따라 연구 안내·동의·윤리 검토 필요 여부를 확인한다. 참여 여부는 고용평가와 분리한다.

## 시행 절차
1. 평가 목적과 연구용 검토 완료의 뜻을 설명한다. 정책 집행 권한이나 훈련수요의 직접 판정과 구별한다.
2. 본 과업과 겹치지 않는 연습문항을 시행한다. 정답 기준과 경고/차단의 차이를 확인한다.
3. 배정표에 따라 같은 참여자에게 각 과업을 한 번씩 제시한다. 12명 전체에서 과업별 네 조건의 배정 횟수는 같다.
4. 참여자가 완료 허용/보완 후 재검토를 선택하고 근거를 기재하면 제어가 개입하기 전의 의도와 시간을 저장한다.
5. 그 이후 해당 조건에 따른 시스템 허용/차단을 제시하고 최종 상태를 별도로 기록한다. 시스템 차단률을 인간 판단 정확도에 합산하지 않는다.
6. 두 평가자가 형식·제어 조건을 가린 상태에서 근거 서술을 독립 채점한다. 불일치는 조정 전 원점수와 함께 보존한다.
7. 종료 후 이해하기 어려운 정보와 업무 적합성에 대한 짧은 면담을 실시한다. 면담 인용은 동의 범위에서 익명화한다.

## 평가 지표와 분석
일차 지표는 제어 개입 이전 판단의 과업별 정답률이다. 이차 지표는 검토시간, 근거 서술 점수, 부적합 입력의 허용 의도 비율, 적합 입력의 불필요한 보류 비율이다. 제어 개입 후의 저장 차단률은 시스템 지표로 별도 보고한다. 12명 예비평가의 차이와 참여자별 분포는 기술통계로 제시한다.

확증평가 전에 주가설, 최소 실무적 차이, 제외기준, 결측처리, 시간 이상값 처리, 다중비교군을 등록한다. 예비평가에서 얻은 참여자 내 차이의 분산과 과업 난이도를 이용해 표본수를 정한다. 본평가에서는 참여자와 과업의 반복을 반영한 혼합효과 모형 또는 설계에 맞는 재표집을 검토한다. 반복행을 독립 참여자로 세지 않는다.

## 자료와 실행
responses_EMPTY.csv는 빈 양식이다. 관측자료를 입력한 뒤 python code/analyze_field_study.py --responses 실제파일.csv --out 결과폴더 명령을 실행한다. 빈 자료에는 효과 추정값을 생성하지 않는다. 배정표의 P01 등은 계획용 코드이며 실제 참여자를 뜻하지 않는다. 정답표는 참여자에게 노출하지 않는다. 연구자가 작성한 과업에 대한 평가이므로 독립적인 외부 사례 검증과 구분한다.

## 독립 외부 기술평가 인계
외부 평가자는 코드 변경 없이 고정된 검증기에 적용할 사례와 기대결과를 독립 작성한다. 기존 합성 사례·정답은 사례 작성 완료 전 제공하지 않는다. 작성 완료 후 해시와 일시를 기록하고 연구팀은 검증기를 수정하지 않은 채 실행한다. 실패 수정과 재실행은 별도의 형성평가로 분리한다. 현재 패키지의 시험은 모두 내부 평가이다.
"""
    (out / "protocol.md").write_text(protocol, encoding="utf-8")
    print("Prepared 12 synthetic tasks; 144 planned assignments; 0 observations.")


if __name__ == "__main__":
    main()
