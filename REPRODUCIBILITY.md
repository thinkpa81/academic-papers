# 분석 재현 범위와 실행 방법

`261105` 공개본은 `CODE_RELEASE.json`에 식별한 최종 HWP의 분석·표·그림에 대응한다. 실행 기록과 보존 결과 대조는 `results/release_261105/`에 있다.

현재 261105 HWP의 SHA-256과 분석 기준 커밋 `94ad3550b1d503c9a4c6380391940c8de8b1d980`의 연결은 `results/release_261105/manuscript_binding_261105.json`에서 확인한다. 이번 보완에서는 분석 코드·입력·보존 수치를 유지하고 누락된 실행 명세와 원고 연결 기록을 추가했다. 이전 261029 HWP를 대상으로 작성한 검증 기록은 그 당시 이력으로 유지한다.

## 환경 준비

Python 3.12에서 저장소 루트를 작업 폴더로 사용한다.

```bash
python -m venv .venv
```

Windows PowerShell은 `.venv\Scripts\Activate.ps1`, macOS/Linux는 `source .venv/bin/activate`로 활성화한 뒤 설치한다.

```bash
python -m pip install -r requirements.txt
```

## 배포 파일과 보존 결과 검사

배포 해시를 먼저 확인한다. 검사를 통과시키기 위해 manifest를 새로 생성하지 않는다.

```bash
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py --report ../result_checks_261105.json
python -m unittest discover -s tests -v
python code/verify_figure_data.py --out ../figure_check_261105.json
python code/verify_figure_glyphs.py --out ../figure_glyph_check_261105.json
```

## 9단계 재실행

```bash
python code/run_all.py --out ../rerun_261105
python code/v3_independent_audit.py --out ../independent_check_261105.json --replay ../rerun_261105
python code/audit_transfer_results.py --source ../rerun_261105/transfer_evaluation
```

출력 경로는 새 디렉터리여야 한다. 실행기는 코드·입력 폴더로의 출력과 잘못된 단계 선택을 거부한다. `run_summary.json`에는 실행시각·패키지 버전·제어 환경·단계별 명령·스크립트 해시·종료상태가 기록된다. `source_inventory.json`은 시작 시 사용 가능한 코드·입력 목록이며 실제 파일 접근 추적은 아니다.

| 단계 | 범위 |
| --- | --- |
| `forecast_replay` | 보존 원자료 정규화, 주분석 재적합·예측 비교 |
| `service_replay` | 초기·확장 결함시험 재실행 |
| `model_swap_replay` | 모형 교체와 판정 일관성 시험 |
| `preserved_audit` | 보완분석의 보존 모형·입력·예측 검산 |
| `local_fallback` | 지역·산업별 대체 규칙 비교 |
| `benchmark` | 38개 후보와 고정분할·확장학습 비교 |
| `diagnostics` | 표본·입력시점·재선정 불확실성 진단 |
| `registered_service` | 등록 근거 대조와 결함시험 |
| `transfer_evaluation` | 미국 자료 적용, 공통 요건 및 신뢰경계 시험 |

독립 대조는 9단계의 보존 CSV 전체를 기준으로 파일·열·행·값을 검사한다. 누락과 중복 압축 표현은 실패 처리하고, 보존 기준이 없는 추가 CSV는 별도 목록으로 보고한다. 수치 대조에는 절대·상대 허용오차 `1e-10`을 사용한다. 서비스 판정의 절대 허용오차 `1e-9`, 상대 허용오차 `0`과 목적이 다르다.

일부 보완모형은 보존값 검산이며 9단계 전체를 모든 모형의 신규 적합으로 해석하지 않는다. 분석은 현재 개정자료의 후향적 시간순 평가이다.

## 보완모형의 선택 재적합

```bash
python support/baseline/base_v11/original/analysis/run_analysis.py --input-root support/baseline/base_v11/original/raw --output-root ../rerun_original
python support/baseline/base_v11/extensions/analysis/run_extended_analysis.py --source-root support/baseline/base_v11/original --output-root ../rerun_original_expanding
python support/baseline/base_v11/extensions/revision_v8/region/run_region_d.py --package-root support/baseline/base_v11 --output-dir ../rerun_merged_region
```

통합지역 재적합에 필요한 `support/baseline/base_v11/analysis_harmonized/protocol.md`는 2026년 11월 5일 현재 코드와 보존 기록에서 복구한 재실행 명세다. 과거 원문 바이트를 복원한 것은 아니므로 과거 선정기록의 프로토콜 해시를 변경하지 않았다. 새 재적합은 복구한 문서의 해시를 기록한다. 실제 재적합 후 보존 CSV 18개·6,596행이 일치했으며, 명령·선정기록·파일별 대조 결과는 `results/release_261105/protocol_restoration/`에 있다.

2024년 평가는 고정한 모형·예측을 사용한다. `support/baseline/base_v11/extensions/temporal2024/analysis/`에 설계와 예측 고정·후속 평가 코드가 있다. 새로운 예측 고정 실행에는 `freeze_design_before_new_outcomes.json`과 `.sha256`을 새 출력에 복사한 뒤 해당 `freeze_predictions_2024.py`를 사용한다. 원래 고정 시점과 재실행 시점을 구분한다.

## 그림과 현장평가

```bash
python code/redraw_figures.py --out ../figures_261105
python code/prepare_field_study.py --help
python code/analyze_field_study.py --help
```

논문 그림은 `figures/paper_figure_*` 4개이며 PNG·PDF·SVG를 제공한다. 표·그림의 코드 대응은 `PAPER_OUTPUT_MAP.md`를 따른다.

`field_study/`는 실무자 8명·16과업·표/카드 두 조건의 계획과 빈 양식이다. `results/field_study_status/status.json`의 `not_evaluated`는 미실시 상태이다. 기술시험의 합성 사례 수를 실제 참여자 수나 현장 오류율로 해석하지 않는다.

## 새 배포본의 해시

새 배포본의 모든 파일을 확정한 때에만 아래 명령으로 배포목록을 갱신한다.

```bash
python code/add_hash_manifest.py --legacy-sha256
python code/add_hash_manifest.py --verify
```

두 manifest는 순환 해시를 피하기 위해 자신들을 제외한다. 해시는 파일 동일성을 확인하며 자료 진위나 과거 확보시점을 인증하지 않는다. 과거 프로토콜의 설명 문구 정리 전후 해시는 `results/release_261105/cleanup_record.json`에서 구분한다.
