# 재현 검증의 범위와 실행 방법

현재 배포본은 `261028_v3`이며 2026년 10월 28일에 9개 실행 단계를 새로 실행했다. 아래의 v2 기록은 과거 검토 이력으로 유지한다.

이번 검증의 상세 기록은 `results/revision_verification_261028_v3/AUDIT_SCOPE.md`에 있다. 9단계 모두 정상 종료했고 CSV 157개·132,063행이 보존 결과와 일치했다. 독립 51개·기존 653개·단위시험 12개·그림 수치 97개·그림 문자 18개 검사를 통과했다. 원자료 정규화와 주분석 재적합, 후보군 비교·재선정 및 공통 요건 시험은 실제로 다시 실행했다. `preserved_audit`는 보완모형의 보존값 검산으로, 해당 모형 전부의 신규 적합은 아니다. 실제 현장 참여자·응답은 0건이다.

실행 명령은 최상위 `README.md`를 기준으로 한다. `run_summary.json`, `stage_logs/`, `replay_comparison_with_hashes.json`, `environment_final.json`, `analysis_code_sha256.json`에 실제 실행과 대조 근거를 보존했다. 최종 원고의 표·인용·수식·서식 검사는 별도로 기록하며, 문서 서식 변경을 통계분석 변경으로 해석하지 않는다.

# 이전 검증 이력

이 문서는 기존 `261027_v4` 분석의 실행 이력과 이번 `261028_v2` 원고·그림·출처 검토를 구분한다. 기존 공개 기준 커밋은 `e125b2791b955483878439664bc73e5b6cbb88a0`이며 이번 동봉본의 보완 파일을 그 커밋에 추가한 것은 아니다. 분석 표본, 후보군, 난수 시드, 선정 규칙, 예측값과 기존 기술시험의 기대 판정은 유지하였다.

## 261028_v2 당시 검증

| 점검 | 이번 실행 결과 | 근거 |
| --- | --- | --- |
| 보존 결과·구조·표본·시점·선정 검산 | 653개 통과 | `code/verify_results.py`, `results/revision_review_261028_v2/result_verification.json` |
| 기존 소프트웨어 테스트 | 12개 통과 | `tests/`, 이번 검토의 `package_unit_tests.log` |
| 그림 2·3의 수치·기여도·집계·범위 | 97개 통과 | `code/verify_figure_data.py`, `results/figure_data_check_261028_v2.json` 및 이번 검토 기록 |
| 빈 응답양식 분석 | 참여자 0명·관측 0건·효과 미추정 | `field_study/responses_EMPTY.csv`, `results/field_study_status/status.json` |
| 압축 입력·참조 JSON의 원내용 | 해제 후 SHA-256이 `execution_start.json`과 일치 | 이번 검토의 `audit_preserved_transfer.json` |
| 공통 요건 보존 판정 | 직접 구현·Pandera 7,590개 일치; 정상 1,518개 수용·결함 6,072개 차단 | `results/transfer_evaluation/case_results.csv.gz`, 이번 검토 기록 |
| 참조정보 동시 변경 | 별도 506개 모두 두 구현에서 통과 | `results/transfer_evaluation/trust_boundary_results.csv` |
| 미국 3계열 × 2모형 예측 재계산 | 234개 검산; 최대 차이 4.6241×10⁻¹⁴ | 이번 검토의 `audit_preserved_transfer.json` |
| 보완 출처 복원 | 136개 파일 이전 ZIP과 바이트 일치; 주요 원자료 네 해시 일치 | `raw/supplementary_sources_261028_v2/`, 이번 검토의 `reference_audit.json`과 복원 기록 |
| 배포 무결성 코드 | SHA-256·SHA-512 생성–검증과 동일 크기 파일변경 탐지 확인 | `code/add_hash_manifest.py` |

261028_v2 당시에는 9단계 분석 전체와 Pandera 기술시험을 새로 실행하지 않았다. 위 판정 일치는 보존된 결과를 다시 대조한 것이며, 미국 계열 예측은 별도의 NumPy 행렬 계산으로 검산하였다. 주분석 전체를 새로 학습하거나 새로운 실제 사용자 관측을 수집한 검증이 아니다. 세 그림은 보존 수치에 따라 재작성하고 수치 검사와 이미지 확인을 수행하였다.

현재 자료는 원기관의 과거 최초 공표 판본 전체나 변경 이력 전체를 포함하지 않는다. 특히 보도자료 PDF 원본은 복원본에 없고 HTML·PDF 텍스트 추출본·URL·원파일 해시를 포함한다. 파일 해시 일치를 원기관 자료의 진위 인증으로 확대하지 않는다.

## 이전 보완 작업의 실행 이력

`results/revision_verification_20261028/`는 이번 `261028_v2` 검토 전 보완 과정의 기록이다. `audit_scope_and_retries.json`에는 9단계 완료, CSV·압축 CSV 156개 대조, 수치·구조 검사 653개와 테스트 12개 통과가 기록되어 있다. `preedit_replay/`, `preedit_extended/`, `preedit_transfer_retry/`, `preedit_fallback_retry/`에는 당시 실행과 재시도 로그가 있다. 수치 대조의 허용오차는 상대·절대 각각 10⁻¹⁰이다.

그 이력에는 전이시험 의존성 누락과 첫 대체규칙 재표집 CSV의 불완전 저장을 발견한 사실도 보존하였다. 같은 코드·설정으로 재시도한 최종 24,000행이 보존값과 일치한 뒤 결과를 대조하였다. 실패 기록을 삭제하거나 기대 판정을 바꾸어 통과시킨 검증으로 설명하지 않는다.

9단계 안의 `preserved_audit`는 OECD 원계열, 2024년 고정 모형과 통합지역의 보존 예측·모형·입력을 대조한다. 따라서 이전 9단계 완료도 해당 보완모형 전부의 신규 재학습을 뜻하지 않는다. 최초 비교·후속 수정의 수치와 실패 사례는 `results/service_replay/`, `results/model_swap_replay/`와 관련 명세에 유지하였다.

## 검증 실행

Python 3.12와 `requirements.txt`의 의존성을 준비한 뒤 패키지 루트에서 실행한다. 무결성 검사는 새 산출물을 만들기 전에 수행한다.

```bash
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py
python -m unittest discover -s tests -v
python code/verify_figure_data.py --out ../rerun_figure_check_261028_v2.json
python code/analyze_field_study.py --responses field_study/responses_EMPTY.csv --out ../rerun_field_status_261028_v2
```

전체 재실행은 새 출력 폴더를 사용한다.

```bash
python code/run_all.py --out ../rerun_261028_v2
```

기존 `code/audit_transfer_results.py --source results/transfer_evaluation`은 Pandera를 포함한 설치가 필요하고 해당 폴더의 `numerical_audit.json`을 다시 작성한다. 검증용으로 별도 복사한 결과 폴더를 지정하면 배포 원본을 유지할 수 있다. 전체 재학습·시험 실행 시간은 환경에 따라 다르며, 운영체제와 수치 라이브러리에 따라 부동소수점 차이가 생길 수 있다.

## 보완모형의 선택 재적합

다음 명령은 보존값 검산을 넘어 원계열·통합지역 모형의 적합까지 수행하는 선택 실행이다. 출력은 기존 결과와 다른 경로로 지정한다.

```bash
python support/baseline/base_v11/original/analysis/run_analysis.py --input-root support/baseline/base_v11/original/raw --output-root ../rerun_original
python support/baseline/base_v11/extensions/analysis/run_extended_analysis.py --source-root support/baseline/base_v11/original --output-root ../rerun_original_expanding
python support/baseline/base_v11/extensions/revision_v8/region/run_region_d.py --package-root support/baseline/base_v11 --output-dir ../rerun_merged_region
```

2024년 평가는 고정한 모형·예측을 사용한다. `support/baseline/base_v11/extensions/temporal2024/analysis/`에 당시 설계와 예측 고정·후속 평가 코드를 보존하였다. 새로운 예측 고정 실행에는 `freeze_design_before_new_outcomes.json`과 `.sha256`을 새 출력에 복사한 뒤 해당 `freeze_predictions_2024.py`를 사용한다. 당시의 예측 고정 시점과 이후 재실행 시점은 구분한다.

## 해시와 수치 허용오차

서비스의 출처·모형·입력·검토근거는 기존 SHA-256을 그대로 사용한다. 배포 파일 목록에는 SHA-512를 추가하였다. 전체 편집을 끝낸 후에만 `python code/add_hash_manifest.py --legacy-sha256`으로 두 목록을 생성한다. 검증 전에 목록을 갱신하면 변경 여부 검사의 의미가 사라진다. 두 루트 목록은 순환 해시를 피하기 위해 자신들을 포함하지 않는다.

서비스의 수치 정합성 판정은 `code/evidence_contract.py`와 `code/registered_guard.py`의 절대 허용오차 10⁻⁹·상대 허용오차 0을 따른다. 이전 결과 재현 대조의 10⁻¹⁰과 서로 다른 목적의 기준이다.

## 실제 현장평가 상태

`field_study/`는 실무자 8명·16과업·표/카드 두 조건의 계획과 빈 양식이다. 실제 참여자·관측은 0건이며 효과를 추정하지 않았다. `not_evaluated`는 분석자료가 없는 미실시 상태를 뜻한다. 소프트웨어 테스트의 임시 입력과 합성 기술시험 사례는 연구 관측자료에 포함하지 않는다. 실제 실시 이후 개인별 기록을 별도 보관하고 참여자 수준의 비교를 수행한다.
