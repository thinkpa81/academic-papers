# 수정 논문과 재현자료의 대응

현재 기준은 `CODE_RELEASE.json`에 식별한 최종 HWP와 `261105` 공개본이다. 계산에는 반올림 전 결과를, 표시값에는 `results/paper_tables/`를 사용한다. 그림의 마이너스 표기는 ASCII `-`이며 수치는 유지했다. 그림 생성 및 검증 명령은 README를 따른다.

| 논문 항목 | 원자료·코드·계산 결과 |
| --- | --- |
| 표 1–2 | 선행연구와 설계원칙의 문헌 종합. 실험에서 계산한 효과와 구분 |
| 표 3–7 | `results/forecast_replay/`, `support/baseline/base_v11/analysis_harmonized/results/main/` |
| 표 8 | `results/local_fallback/`의 지역·산업별 대체 규칙과 결과 |
| 표 9 | `figures/matrix_rendered_cells.csv` |
| 표 10 | `results/benchmark/fixed/`, `results/benchmark/fixed_comparisons.csv` |
| 표 11–13 | `results/service_replay/`, `support/service_addendum/` |
| 표 14 | `results/registered_service/`, `code/registered_guard.py`, `code/run_registered_evaluation.py` |
| 표 15 | `results/transfer_evaluation/comparison_summary.csv`, `code/evidence_contract.py`, `code/run_transfer_evaluation.py` |
| 부록표 A1–A3 및 부록그림 A1 | `results/preserved_audit/`, `support/baseline/base_v11/`의 원계열·2024년 평가·대구경북 통합 분석 |
| 부록표 B1–B2 | `results/diagnostics/panel_reconstruction/`, `results/diagnostics/coverage_by_industry.csv`와 보존 분석표 |
| 부록표 C1 | `results/diagnostics/reselection_intervals.csv`, `reselection_replicates.csv`, `selection_frequencies.csv` |
| 부록표 D1–D3 | `results/benchmark/protocol_before_fit.json`, `fixed_comparisons.csv`, `expanding_summary.csv` |
| 부록 E | `results/registered_service/`, `results/model_swap_replay/` |
| 부록 F | `field_study/protocol.md`, `tasks.json`, `task_provenance.json`, `counterbalanced_assignment.csv`, 빈 응답양식; `code/prepare_field_study.py`, `collect_field_study.py`, `analyze_field_study.py`, `pilot_analysis.py` |
| 부록 G | `raw/transfer_macrodata/`, `results/transfer_evaluation/`, `code/audit_transfer_results.py`, `TRANSFER_EVALUATION.md` |
| 부록 H·표 H1 | `results/paper_tables/table_H1.csv`, `raw/supplementary_sources_261028_v2/source_release/release_calendar_H1_2013_2025.json`, `code/export_publication_calendar.py` |
| 참고문헌 [5] | `raw/kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json`, `raw/source_acquisition_manifest.json` |
| 참고문헌 [6] | `raw/supplementary_sources_261028_v2/source_employment/`의 KOSIS S 추출본과 manifest |
| 참고문헌 [15] | `raw/supplementary_sources_261028_v2/source_release/release_calendar_H1_2013_2025.json`, HTML·PDF 텍스트 추출본 |
| 참고문헌 [41–42] | `raw/oecd_*`, 복원 폴더의 `source_employment/`, `source_covariates/` 원응답·요청·대조 기록 |

## 그림의 정확한 파일명

| 논문 번호 | 삽입용 기준 이미지 | 생성 코드 |
| --- | --- | --- |
| 그림 1 | `figures/paper_figure_01.png` | `code/reviewability_figure.py`의 `draw`; `redraw_figures.py`에서 호출 |
| 그림 2 | `figures/paper_figure_02.png` | `code/redraw_figures.py`의 `draw3` |
| 그림 3 | `figures/paper_figure_03.png` | `code/redraw_figures.py`의 `draw4` |
| 부록그림 A1 | `figures/paper_figure_A1.png` | `code/redraw_figures.py`의 `draw2` |

모든 기준 그림에는 같은 이름의 PDF·SVG가 있다. 배포본에는 논문 번호와 일치하는 `paper_figure_*` 기준 파일을 둔다. 아래 재생성 코드는 새 폴더에 기준 파일과 이전 내부 번호의 별칭도 함께 출력한다. 별칭은 같은 그림의 중복 파일이며 현재 배포에는 포함하지 않는다.

```bash
python code/redraw_figures.py --out generated_figures
python code/verify_figure_data.py --out ../rerun_figure_check_261105.json
```

그림 1의 과업 진행과 재검토 화살표를 정리하였다. 그림 2는 서울 BTE의 예측·기여도·검증사례 0개와 후속 검토 과업을 구분한다. 그림 3은 80개 권역–산업 셀의 수치와 완전·부분·미산출 범위를 표시한다. 그림 수치 검사는 보존 예측값과 원근거 카드에서 97개 항목을 검산하며 모형을 새로 학습하지 않는다.

## 최종 원고 대응과 검증 기록

최종 HWP의 표·그림 대조는 `results/release_261105/manuscript_alignment.json`에 기록한다. 원고 파일은 공개본에 포함하지 않는다. 기존 표시표 24개의 수치를 유지하며 부록표 H1의 2013–2025년 공표일 13건을 추가했다. H1은 보존 공표일 목록에서 `code/export_publication_calendar.py`로 생성·검증한다.

실제 현장 참여자·응답은 0건이다. `results/field_study_status/status.json`의 `not_evaluated`는 미실시를 뜻한다. 128개 계획 배정행, 1,006개 등록 근거 시험과 7,590개 공통 요건 시험 입력은 실제 참여자 수가 아니다. 공통 요건의 네 구현조건 결과 30,360행과 별도 신뢰경계 시험 506개는 각각의 분모로 해석한다.
