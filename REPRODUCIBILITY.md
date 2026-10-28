# 최종 공개본의 재현 검증

기준일은 2026년 10월 28일이며, `261027_v4` 최종 보완본에 대응한다. 원자료 수치, 표본, 후보군, 난수 시드, 손실함수, 선정 규칙과 기존 기술시험의 기대 판정은 유지하였다. 그림 1과 사용자 평가 준비자료를 보완하였다.

## 확인한 결과와 근거

| 점검 | 확인 결과 | 기록 |
|---|---|---|
| 분석·기술평가 실행 | 9개 단계 완료 | `results/revision_verification_20261028/analysis_replay/`, `extended_initial_attempt/`, `transfer_retry/`, `fallback_retry/`의 실행 요약·로그 |
| 결과표 대조 | CSV 및 압축 CSV 156개 일치, rtol=atol=10⁻¹⁰ | `results/revision_verification_20261028/replay_comparison.json` |
| 결과·구조 점검 | 653개 통과 | `results/validation_report.json` |
| 소프트웨어 테스트 | 기존 6개와 사용자 평가 준비자료 6개, 합계 12개 통과 | `tests/`, `results/revision_verification_20261028/unit_tests.log` |
| 원자료 재구성 | KOSIS 산업군 2,431행·구성산업 5,148행·전국 계열 143행 재현 | `results/revision_verification_20261028/source_replay_checks.json` |
| 사용자 평가 | 실제 참여자 0명·관측 0건, 효과 미추정 | `field_study/preparation_status.json`, `results/field_study_status/status.json` |

시험의 합성 입력 수는 실제 참여자 수가 아니다. 128개 배정행은 8명·16과업의 실시 계획이다. 실제 응답은 생성하지 않았다.

최초 외부자료 시험은 실행환경의 추가 의존성 누락으로 중단되어 설치 후 동일 코드로 재실행하였다. 대체규칙의 첫 재표집 CSV는 불완전 저장을 발견하여 동일 코드·설정으로 재실행하였고, 완전한 24,000행이 보존값과 일치하였다. 성공·실패·재시도 기록을 함께 보존하였다. `extended_initial_attempt/run_summary.json`의 실패는 이후 `transfer_retry/run_summary.json`의 성공으로 해소되었으며, 최종 대조에는 재시도 결과를 사용하였다. 상세 범위는 `audit_scope_and_retries.json`에 명시하였다.

## 실행

Python 3.12와 `requirements.txt`의 의존성을 설치하고 저장소 루트에서 실행한다.

```bash
python verify_package.py
python code/verify_results.py
python code/audit_transfer_results.py --source results/transfer_evaluation
python -m unittest discover -s tests -v
python code/run_all.py --out rerun_20261028
```

원자료 확보본에서 계산 결과까지의 재현성을 확인하는 절차이다. 원기관 내부 원기록의 진위, 과거 최초 공표 판본과 실제 사용자 효과를 새로 검증하는 절차는 아니다. 결과를 확인한 뒤 추가한 후보군·확장창·재선정 비교는 탐색적 민감도 분석이다.

## 보완분석의 재적합 범위

기본 실행의 `preserved_audit`는 OECD 원계열, 2024년 고정 모형과 통합지역의 보존 예측·모형·입력을 대조한다. 해당 보완모형 전체를 새로 재학습한 단계로 해석하지 않는다. 다음은 모형 적합까지 수행하는 선택 실행이다. 기존 출력과 다른 새 경로를 사용한다.

```bash
python support/baseline/base_v11/original/analysis/run_analysis.py --input-root support/baseline/base_v11/original/raw --output-root rerun_original
python support/baseline/base_v11/extensions/analysis/run_extended_analysis.py --source-root support/baseline/base_v11/original --output-root rerun_original_expanding
python support/baseline/base_v11/extensions/revision_v8/region/run_region_d.py --package-root support/baseline/base_v11 --output-dir rerun_merged_region
```

2024년 평가는 고정된 모형·예측을 사용한다. `support/baseline/base_v11/extensions/temporal2024/analysis/`에 당시 설계, 예측 고정 코드와 후속 평가 코드를 보존하였다. 새 예측 고정 실행에는 해당 폴더의 `freeze_design_before_new_outcomes.json`과 `.sha256`을 새 출력 폴더에 복사한 뒤 `freeze_predictions_2024.py --source-root support/baseline/base_v11/original --output-root <새 출력 폴더>`를 사용한다. 당시 예측 고정 시점과 재실행 시점은 구분한다.

## 기술시험과 사용자 평가의 구분

등록 근거 시험은 1,006개 합성 사례에 대한 기대 판정과 관측 판정의 일치를 확인한다. 공통 요건의 직접 구현과 Pandera는 7,590개 입력에서 판정이 일치하였고, 정상 1,518개를 수용하고 명세 결함 6,072개를 차단하였다. 참조자료까지 함께 변경한 별도 506개는 통과하였다. 선행 구현의 실패 기록은 `results/service_replay/` 및 `results/model_swap_replay/`에 유지하였다. 최종 구현의 성공으로 선행 구현의 실패를 소급하여 삭제하지 않는다.

`field_study/protocol.md`는 8명·16과업·표/카드 2조건의 실시 계획이다. 과업·배정표·빈 응답양식, 로컬 수집 도구와 참여자별 비교 코드를 제공한다. 다음 명령은 관측이 없다는 상태만 기록하며 효과크기를 만들지 않는다.

```bash
python code/analyze_field_study.py --responses field_study/responses_EMPTY.csv --out rerun_field_status
```

실제 수집자료는 공개 저장소 밖에 보관한다. 현장 모집·실시·분석은 완료하지 않았다.

## 공개본 정리

현재 파일에는 최종 재현자료 한 벌을 둔다. 이전 공개본의 중복 실행·대조 요약 2개는 제거하고 이번 검증 기록과 최신 결과 점검으로 통일하였다. 원고 편집 스크립트와 수정 전 원고, 편집·심사 보고서는 공개본에서 제외하였다. `support/`의 비교 구현과 고정 입력은 현재 9단계 실행에 필요한 의존자료로 유지하였다. 파일별 크기·SHA-256은 `manifest_sha256.json`에 기록하며, 파일 구성 변경 후 다시 검증한다. 과거 공개 내용은 Git 이력에 남는다.
