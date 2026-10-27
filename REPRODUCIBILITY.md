# 재현 검증 기록

2026-10-27 공개본에서 실행 경로, 출력 보호, 실패 기록, 모형명 검증 및 등록자료의 예외 처리를 정리하였다. 분석의 표본, 후보군, 난수 시드, 손실함수, 선택 규칙과 사례별 기대결과는 유지하였다.

- 전체 실행: 공통 요건 비교·외부자료 적용을 포함한 9개 단계 완료 (`results/transfer_release_execution.json`).
- 보존 결과와 재실행 CSV 157개 일치, 수치 허용오차 rtol=atol=1e-10 (`results/transfer_release_regression.json`).
- 결과 점검: 653개 통과 (`results/validation_report.json`).
- 등록 근거 시험: 1,006개 사례의 기대 판정과 관측 판정 일치 (`results/registered_service/case_results.csv`).
- 유지보수 회귀 테스트: 6개 통과. 잘못된 등록자료 구조, 비유한 수치, 파일 변경·누락, 기존 출력 보호, 실패 상태 기록을 확인하였다.
- 2024년 고정 모형의 예측 재실행 결과가 보존된 예측과 허용오차 1e-10 이내에서 일치하였다.
- Python 정적 검사와 문법 검사 통과. 개발 점검에는 `ruff==0.17.3`을 사용하였다.

서비스 시험의 정상·오류 사례는 독립 참여자 수가 아니다. 선행 구현에서 발견한 실패는 `results/service_replay/` 및 `results/model_swap_replay/`에 남아 있다. 최종 구현의 기대 판정 일치가 선행 구현의 실패를 소급하여 제거하지 않는다.

코드 정리로 바뀐 체크섬은 실행 명세에 현재 해시와 변경 전 해시를 함께 기록하였다. 기존 명세의 작성 시각은 유지하고 공개본 유지보수 기록을 별도로 추가하였다. 이 기록은 외부 사전등록을 뜻하지 않는다. 원자료 수치와 원자료 해시는 유지하였다.

## 보완분석

기본 실행의 `preserved_audit`는 보존된 예측·모형·입력을 다시 대조한다. 아래 명령은 원계열 및 통합지역의 모형 적합까지 다시 수행하는 선택 실행이다. 새 출력 경로를 사용한다.

```bash
python support/baseline/base_v11/original/analysis/run_analysis.py --input-root support/baseline/base_v11/original/raw --output-root rerun_original
python support/baseline/base_v11/extensions/analysis/run_extended_analysis.py --source-root support/baseline/base_v11/original --output-root rerun_original_expanding
python support/baseline/base_v11/extensions/revision_v8/region/run_region_d.py --package-root support/baseline/base_v11 --output-dir rerun_merged_region
```

2024년 평가는 고정된 모형과 예측을 사용한다. `support/baseline/base_v11/extensions/temporal2024/analysis/`에 당시 설계, 예측 고정 코드와 후속 평가 코드를 포함하였다. 새 예측 고정 실행을 하려면 해당 폴더의 `freeze_design_before_new_outcomes.json`과 `.sha256`을 새 출력 폴더에 복사한 뒤 `freeze_predictions_2024.py --source-root support/baseline/base_v11/original --output-root <새 출력 폴더>`를 실행한다. 당시의 예측 고정 시점과 이후 재실행 시점을 구분하여 기록한다.

## 현장평가 자료

`field_study/`는 계획과 빈 양식이다. 다음 명령은 응답이 없다는 상태를 기록하며 효과크기를 만들어 내지 않는다.

```bash
python code/analyze_field_study.py --responses field_study/responses_EMPTY.csv --out rerun_field_status
```

실제 응답을 수집한 뒤에는 식별 가능한 개별 기록을 공개 저장소와 분리하여 관리한다.

## 공통 요건 비교와 외부자료 적용의 검증
- 외부계열 예측 234개를 별도 NumPy 행렬 계산으로 검산: 최대 절대차 4.6241e-14.
- 직접 구현과 Pandera의 동일 정보 비교 7,590개 판정 일치.
- 정상 1,518개 수용, 명세 결함 6,072개 차단, 별도 참조 동시 변경 506개 통과.
- 단일행·일괄 처리 대조: 자료·유형 조합 30개 일치.
- 초기 실행 이후 사용하지 않는 import와 import 순서를 정리한 뒤 다시 실행하였다. 입력·참조·예측·판정 8개 파일이 초기 실행과 바이트 단위에서 일치하였다 (`results/transfer_evaluation/maintenance_check.json`).

실행환경 준비 중 기존 비교모형의 CatBoost 및 Narwhals 누락으로 실행이 중단된 기록이 있었으며 의존성을 설치한 뒤 9단계가 모두 완료되었다. 결과나 기대 판정을 변경하여 통과시킨 조치는 없다. 실제 사용자 관측을 생성하거나 대체하지 않았다. 추가 비교의 해석 범위는 `TRANSFER_EVALUATION.md`를 따른다.

## 261027_v4 배포 정리

최종 원고의 절 제목과 학술적 표현을 정리하고 표·그림 대응 안내를 갱신하였다. 분석 코드, 원자료, 표의 표시값, 예측값, 시험 판정과 연구의 해석 범위는 유지하였다. 이전 8단계 실행 요약 2개와 중복 생성 SVG 3개를 제거하고, 9단계 전체 실행 기록과 논문에 실제 삽입한 그림을 보존하였다. 파일 정리 후 전체 실행, CSV 157개 대조, 결과 점검 653개, 유지보수 테스트 6개 및 그림 재작성을 다시 확인하였다. 내부 버전명이 있는 비교 구현과 시험 입력은 현재 분석의 의존자료이므로 유지하였다.
