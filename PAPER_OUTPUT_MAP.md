# 최종 논문과 실행 결과의 대응

기준 논문: 「5극 3특 지역고용 의사결정지원서비스의 설계와 기술평가」, 2026-10-27 `261027_v4` 통합본.
수록 표의 정확한 제목·번호·표시값은 `results/paper_tables/index.json`과 해당 CSV에서 확인한다.

| 최종 논문 항목 | 원자료·코드·계산 결과 |
|---|---|
| 표 1–2 | 선행연구와 설계원칙의 문헌 종합; 실험에서 계산한 효과와 구분 |
| 표 3–7 | `results/forecast_replay/`, `support/baseline/base_v11/analysis_harmonized/results/main/` |
| 표 8 | `results/local_fallback/`의 지역·산업별 대체 규칙과 결과 |
| 표 9 | `figures/matrix_rendered_cells.csv` |
| 표 10 | `results/benchmark/fixed/`, `results/benchmark/fixed_comparisons.csv` |
| 표 11–13 | `results/service_replay/`, `support/service_addendum/` |
| 표 14 | `results/registered_service/`; `code/registered_guard.py`, `code/run_registered_evaluation.py` |
| 표 15 | `results/transfer_evaluation/comparison_summary.csv`; `code/evidence_contract.py`, `code/run_transfer_evaluation.py` |
| 부록표 A1–A3, 부록그림 A1 | `results/preserved_audit/`, `support/baseline/base_v11/`의 원계열·2024 평가·대구경북 통합 분석 |
| 부록표 B1–B2 | `results/diagnostics/panel_reconstruction/`, `results/diagnostics/coverage_by_industry.csv` 및 보존 분석표 |
| 부록표 C1 | `results/diagnostics/reselection_intervals.csv`, `reselection_replicates.csv`, `selection_frequencies.csv` |
| 부록표 D1–D3 | `results/benchmark/protocol_before_fit.json`, `fixed_comparisons.csv`, `expanding_summary.csv` |
| 부록 E | `results/registered_service/`, `results/model_swap_replay/` |
| 부록 F | `field_study/`, `code/prepare_field_study.py`, `code/analyze_field_study.py` |
| 부록 G | `raw/transfer_macrodata/`, `results/transfer_evaluation/`, `code/audit_transfer_results.py`; `TRANSFER_EVALUATION.md` |

## 그림 파일명

| 논문 번호 | 논문 내 이미지와 바이트가 동일한 파일 | 수치 입력에서 재작성하는 파일 |
|---|---|---|
| 그림 1 | `figures/paper_figure_01.png` | `generated_figures/figure1_final.png` 및 PDF/SVG |
| 그림 2 | `figures/paper_figure_02.png` | `generated_figures/figure3_final.png` 및 PDF/SVG |
| 그림 3 | `figures/paper_figure_03.png` | `generated_figures/figure4_final.png` 및 PDF/SVG |
| 부록그림 A1 | `figures/paper_figure_A1.png` | `generated_figures/figure2_final.png`; 원계열 확장창 분석 결과 |

기존 그림 생성기의 내부 번호는 유지하고 최종 논문 번호를 별도로 연결하였다. `code/redraw_figures.py`는 보존 수치에서 그림 4개를 다시 만든다. 재작성 결과는 `generated_figures/`에 저장되며, `paper_figure_*.png`와 구분한다. 저장소에는 논문에 삽입한 PNG와 재작성에 필요한 코드·입력·글꼴을 보존하였다.

현장 참여자 자료는 0건이며, 합성 서비스 시험 1,006건을 독립적인 실제 사용자 관측으로 해석하지 않는다. 후보군별 모형 선택 결과와 과거 화면 예시도 각각의 설계·평가 조건에 따라 해석한다.
