# 수정 논문과 재현자료의 대응

현재 기준은 `261028_v3` 수정본이다. 계산에는 반올림 전 결과를, 표시값에는 `results/paper_tables/`를 사용한다. 그림의 마이너스 표기는 ASCII `-`이며 수치는 유지했다. 문서·그림 생성 및 검증 명령은 README를 따른다.

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
python code/verify_figure_data.py --out ../rerun_figure_check_261028_v3.json
```

그림 1의 과업 진행과 재검토 화살표를 정리하였다. 그림 2는 서울 BTE의 예측·기여도·검증사례 0개와 후속 검토 과업을 구분한다. 그림 3은 80개 권역–산업 셀의 수치와 완전·부분·미산출 범위를 표시한다. 그림 수치 검사는 보존 예측값과 원근거 카드에서 97개 항목을 검산하며 모형을 새로 학습하지 않는다.

## 현재 261028_v3 원고 재작성

`code/build_manuscript_v3.py`의 입력은 `support/manuscript/source_before_revision_261028_v3.docx`와 `support/manuscript/revision_261028_v3.json`이다. 첨부 학회 양식의 문서 규격과 v3 수정 명세를 적용하고 `figures/`의 현재 기준 그림을 삽입한다. 원고의 분석 수치와 편집 가능한 수식 19개를 유지한다. 기준 DOCX는 최종 원고의 서식·수식·수정표시를 재생성하는 필수 입력이므로 보존한다.

```bash
python code/build_manuscript_v3.py --code-commit f4ae5299b2f4382f94e032804568bcd8554ca5fc --output generated/00_최종논문_261028_v3.docx
python code/build_redline_v3.py --before support/manuscript/source_before_revision_261028_v3.docx --input generated/00_최종논문_261028_v3.docx --output generated/01_최종논문_261028_v3_수정부분_빨간색.docx
python code/verify_manuscript_v3.py --manuscript generated/00_최종논문_261028_v3.docx --code-commit f4ae5299b2f4382f94e032804568bcd8554ca5fc --report ../manuscript_check_261028_v3.json
```

`f4ae5299b2f4382f94e032804568bcd8554ca5fc`은 최종 논문 3.9절에 기록한 실제 코드 커밋이다. 수정표시본은 v2 대비 변경된 문구·표기와 그림 제목을 빨간색으로 표시한다. 원고 검사기는 인용번호·마이너스·구역·수식·익명 메타데이터를 확인한다. 편집용 산출물은 DOCX이며, 네이티브 HWP 저장을 수행한 것은 아니다. 문서의 배치 검토는 별도의 렌더링 확인을 따른다.

## 현재 검증 기록과 현장평가 상태

현재 v3의 참고문헌·약어·문서·그림 검토는 `results/revision_review_261028_v3/`, 새로 실행한 9단계 분석과 독립 검산은 `results/revision_verification_261028_v3/`에 기록하였다. 참고문헌 61개 근거표는 `results/revision_review_261028_v3/reference_audit_all.json`, 최종 연구표 24개·780개 셀의 표시 대조는 `results/revision_verification_261028_v3/final_manuscript_table_audit.json`이다.

이전 원고·검토·재시도 산출물은 현재 파일 목록에서 정리했다. 과거 기록은 [검증 코드 커밋](https://github.com/thinkpa81/academic-papers/tree/f4ae5299b2f4382f94e032804568bcd8554ca5fc)에서 확인할 수 있다. 현재의 v3 검증 기록에 등장하는 당시 파일 수·경로는 그 검증 시점의 범위이며, 정리 후 파일 목록은 루트의 해시 명세를 따른다. 최종 분석의 입력·비교 기준과 출처 증거는 버전명이 과거여도 유지한다. 공개 범위는 `PUBLICATION_NOTES.md`를 따른다.

실제 현장 참여자·응답은 0건이다. `results/field_study_status/status.json`의 `not_evaluated`는 미실시를 뜻한다. 128개 계획 배정행, 1,006개 등록 근거 시험과 7,590개 공통 요건 시험 입력은 실제 참여자 수가 아니다. 공통 요건의 네 구현조건 결과 30,360행과 별도 신뢰경계 시험 506개도 각각의 분모로 해석한다.
