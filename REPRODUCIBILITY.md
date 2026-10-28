# 최종 논문의 재현 범위와 실행 방법

현재 기준은 `261028_v3` 최종 논문이다. 2026년 10월 28일 분석 실행 경로의 9개 단계를 새 출력 폴더에서 재실행했으며, 상세 기록은 `results/revision_verification_261028_v3/AUDIT_SCOPE.md`에 있다. 최종 원고·수정표시본과 분석의 입력·결과·검증 근거를 유지하고, 이전 원고와 중간 검토·재시도 산출물은 현재 `main`에서 정리했다. 이전 파일은 [검증 코드 커밋](https://github.com/thinkpa81/academic-papers/tree/f4ae5299b2f4382f94e032804568bcd8554ca5fc)에서 확인할 수 있다.

## 환경 준비

Python 3.12에서 저장소 루트를 작업 폴더로 사용한다.

```bash
python -m venv .venv
```

Windows PowerShell은 `.venv\Scripts\Activate.ps1`, macOS/Linux는 `source .venv/bin/activate`로 가상환경을 활성화한 다음 설치한다.

```bash
python -m pip install -r requirements.txt
```

## 무결성과 보존 결과 검사

새 산출물을 만들기 전에 배포 파일의 해시를 확인한다. 검증을 위해 해시 목록을 먼저 다시 생성하지 않는다.

```bash
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py --report ../result_checks_261028_v3.json
python -m unittest discover -s tests -v
python code/verify_figure_data.py --out ../figure_check_261028_v3.json
python code/verify_figure_glyphs.py --out ../figure_glyph_check_261028_v3.json
python code/verify_manuscript_v3.py --manuscript generated/00_최종논문_261028_v3.docx --code-commit f4ae5299b2f4382f94e032804568bcd8554ca5fc --report ../manuscript_check_261028_v3.json
```

## 전체 분석 재실행

보존 결과를 덮어쓰지 않도록 새 출력 경로를 지정한다.

```bash
python code/run_all.py --out ../rerun_261028_v3
python code/v3_independent_audit.py --out ../independent_check_261028_v3.json --replay ../rerun_261028_v3 --manuscript generated/00_최종논문_261028_v3.docx
python code/audit_transfer_results.py --source ../rerun_261028_v3/transfer_evaluation
```

마지막 명령은 지정한 새 결과 폴더의 `numerical_audit.json`을 작성한다. Pandera를 포함한 의존성 설치가 필요하다. 실행 시간과 부동소수점 오차는 운영체제와 수치 라이브러리에 따라 달라질 수 있다.

## 최종 원고 재생성

`support/manuscript/source_before_revision_261028_v3.docx`와 `revision_261028_v3.json`은 최종 문서 생성의 필수 입력이다. 기준 문서는 원래 서식·수식과 수정 전 문자열을 제공하므로, 이전 배포 원고와 별개로 보존한다. 아래 명령은 검토용 사본을 저장소 밖에 생성한다.

```bash
python code/build_manuscript_v3.py --code-commit f4ae5299b2f4382f94e032804568bcd8554ca5fc --output ../rebuilt_261028_v3.docx
python code/build_redline_v3.py --before support/manuscript/source_before_revision_261028_v3.docx --input ../rebuilt_261028_v3.docx --output ../rebuilt_261028_v3_redline.docx
```

수정표시본은 v2 대비 변경 문구·표기와 변경한 그림 제목을 빨간색으로 표시한다. 결과물은 제공된 HWP 양식의 문서 규격을 적용한 DOCX이며, 원본 전용 글꼴은 NanumMyeongjo로 대체했다. 네이티브 HWP 변환은 검증하지 않았다. 문서 구조 검사와 별도로 렌더링된 전체 지면을 확인해야 한다.

## 확인된 결과와 해석 범위

9단계 모두 정상 종료했고 CSV 157개·132,063행이 보존 결과와 일치했다. 독립 검사 51개, 기존 검사 653개, 단위시험 12개, 그림 수치 검사 97개와 문자 검사 18개를 통과했다. 실제 실행과 대조 근거는 `run_summary.json`, `stage_logs/`, `replay_comparison_with_hashes.json`, `environment_final.json`, `analysis_code_sha256.json`에 있다. 이 파일들은 `results/revision_verification_261028_v3/` 아래에 있다.

원자료 정규화, 주분석 적합, 후보군 비교·재선정 및 공통 요건 시험은 실제로 다시 실행했다. `preserved_audit`는 OECD 원계열·2024년 고정 모형·통합지역의 보존 모형·입력·예측 검산이며, 해당 보완모형 전부의 신규 적합을 뜻하지 않는다. 현재 개정자료의 시간순 평가를 과거 최초 공표판본의 실시간 예측평가로 해석하지 않는다.

최종 연구표 24개·780개 셀 대조는 `final_manuscript_table_audit.json`, 문서·인용·약어·지면 검사는 `results/revision_review_261028_v3/`에 있다. 검증 기록의 파일 수와 해시는 각 기록이 작성된 시점의 대상에 관한 것이다. 정리 이후의 현재 파일 목록과 해시는 루트 명세를 따른다. 파일 정리는 원고의 내용이나 분석 수치를 바꾸지 않는다.

## 보완모형의 선택 재적합

다음은 보존값 검산을 넘어 원계열·통합지역 모형을 적합하는 선택 실행이다. 관련 보존 분석 코드는 최종 논문의 보완분석에 필요하므로 유지한다.

```bash
python support/baseline/base_v11/original/analysis/run_analysis.py --input-root support/baseline/base_v11/original/raw --output-root ../rerun_original
python support/baseline/base_v11/extensions/analysis/run_extended_analysis.py --source-root support/baseline/base_v11/original --output-root ../rerun_original_expanding
python support/baseline/base_v11/extensions/revision_v8/region/run_region_d.py --package-root support/baseline/base_v11 --output-dir ../rerun_merged_region
```

2024년 평가는 고정한 모형·예측을 사용한다. `support/baseline/base_v11/extensions/temporal2024/analysis/`에 설계와 예측 고정·후속 평가 코드가 있다. 새로운 예측 고정 실행에는 `freeze_design_before_new_outcomes.json`과 `.sha256`을 새 출력에 복사한 뒤 해당 `freeze_predictions_2024.py`를 사용한다. 원래의 예측 고정 시점과 이후 재실행 시점은 구분한다.

## 해시·허용오차·현장평가

서비스의 출처·모형·입력·검토근거는 기존 SHA-256을 사용한다. 배포 파일 목록에는 SHA-512도 제공한다. 전체 편집이 완료된 새 배포본을 만들 때만 `python code/add_hash_manifest.py --legacy-sha256`으로 두 목록을 갱신한다. 두 목록은 순환 해시를 피하기 위해 자신들을 제외한다. 해시는 파일 동일성의 검사이며 자료의 진위나 과거 확보시점의 인증이 아니다.

서비스의 수치 정합성 판정은 절대 허용오차 `1e-9`, 상대 허용오차 `0`을 사용한다. 이전 결과 재현 대조의 `1e-10`은 다른 목적의 기준이다.

`field_study/`는 실무자 8명·16과업·표/카드 두 조건의 계획과 빈 양식이다. 실제 참여자·관측은 0건이며 효과를 추정하지 않았다. `not_evaluated`는 미실시 상태이다. 기술시험의 합성 사례 수를 실제 참여자 수나 현장 오류율로 해석하지 않는다.
