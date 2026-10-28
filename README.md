# 5극 3특 지역고용 의사결정지원서비스의 재현자료

이 저장소는 「5극 3특 지역고용 의사결정지원서비스의 설계와 기술평가」의 `261028_v3` 수정본에 대응한다. 2026년 10월 28일에 분석 실행 경로의 9개 단계를 재실행하고 참고문헌 61개의 실재 근거·접속 상태·인용 위치를 검토하였다. 분석값은 유지했으며, 짧은 마이너스 표기, 초록과 본문의 독립적인 약어 정의, 인용 범위와 학회 양식을 정비하였다.

## 검증 결과와 범위

- 9개 단계 정상 종료. CSV 157개·132,063행이 보존 결과와 일치했다. 156개는 바이트 동일, 1개는 gzip 해제 후 바이트 동일하다.
- 독립 검사 51개, 기존 검사 653개, 소프트웨어 단위시험 12개, 그림 수치 검사 97개와 그림 문자 검사 18개를 통과했다.
- 직접 구현과 등록 대조 Pandera의 7,590개 판정이 일치했다. 전체 30,360개 판정과 공동 변경 506개 사례도 재실행했다.
- 실제 현장 참여자·응답은 0건이다. 8명·16과업·두 표시조건은 계획이며 실제 사용자 효과를 추정한 결과가 아니다.
- 9개 단계 중 `preserved_audit`는 보완분석의 보존 모형·입력·예측 검산이다. 모든 OECD·통합지역 보완모형을 새로 적합한 것은 아니다.
- KOSIS 동적표 2건은 현재 조회 대신 보존 공식 DOM·주석·해시를 검증했다. 일부 출판사 원문은 유료·접속 제한이 있어, 문헌 실재와 모든 전문의 무료 열람 가능성을 구분한다.

## 빠른 시작

Python 3.12 환경에서 실행한다. 사용한 확보본을 포함하므로 재현을 위해 기관 자료를 새로 내려받을 필요는 없다.

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py
python -m unittest discover -s tests -v
python code/verify_figure_data.py --out ../figure_check_261028_v3.json
python code/verify_figure_glyphs.py
python code/v3_independent_audit.py --out ../independent_check_261028_v3.json
```

Windows PowerShell에서는 `.venv\Scripts\Activate.ps1`, macOS/Linux에서는 `source .venv/bin/activate`로 환경을 활성화한 뒤 설치한다.

전체 실행은 새 출력 폴더를 지정한다.

```bash
python code/run_all.py --out ../rerun_261028_v3
python code/v3_independent_audit.py --out ../independent_check_261028_v3.json --replay ../rerun_261028_v3 --manuscript generated/00_최종논문_261028_v3.docx
```

## 주요 경로

| 경로 | 내용 |
| --- | --- |
| `code/` | 분석·근거 검사·그림·문서 생성·현장평가 실행 코드 |
| `raw/` | 분석에 사용한 KOSIS·OECD·미국 거시경제 확보본 |
| `raw/supplementary_sources_261028_v2/` | 이전 배포본에서 복원한 출처 파일 136개와 복원 기록 |
| `results/` | 정밀 수치·예측·선정·사례별 기술시험 판정 |
| `results/revision_verification_261028_v3/` | 이번 9단계 실행·독립 검산·환경·코드 해시·대조 기록 |
| `results/revision_review_261028_v3/` | 참고문헌·약어·문서·그림·표시 수정 검토 |
| `results/paper_tables/` | 연구표 24개 CSV와 표·그림 대응 목록 |
| `figures/` | 삽입용 PNG와 같은 그림의 PDF·SVG, 표시 수치 |
| `support/manuscript/` | 원고 생성용 보존 사본과 변경 명세 |
| `support/template/` | 제공된 HWP 양식에서 확인한 용지·여백·서식 명세 |
| `generated/` | 배포 원고와 빌드 기록 |
| `field_study/` | 계획·빈 양식. 실제 응답자료 없음 |
| `manifest_sha256*.json` | 파일별 크기·SHA-256·SHA-512 |

## 그림과 원고 생성

```bash
python code/redraw_figures.py --out generated_figures
python code/build_manuscript_v3.py --code-commit ACTUAL_40_CHARACTER_CODE_COMMIT --output generated/00_최종논문_261028_v3.docx
python code/build_redline_v3.py --before support/manuscript/source_before_revision_261028_v3.docx --input generated/00_최종논문_261028_v3.docx --output generated/01_최종논문_261028_v3_수정부분_빨간색.docx
python code/verify_manuscript_v3.py --manuscript generated/00_최종논문_261028_v3.docx --code-commit ACTUAL_40_CHARACTER_CODE_COMMIT --report ../manuscript_check_261028_v3.json
```

`ACTUAL_40_CHARACTER_CODE_COMMIT`에는 논문 3.9절에 명시한 실제 코드 커밋의 40자리 식별자를 넣는다. 문서 생성은 제공된 HWP 양식의 190×262mm 용지, 제본 여백, 1단·2단 구성과 글자 크기를 적용한 **DOCX** 출력이다. 원본 전용 글꼴은 동봉한 NanumMyeongjo로 대체한다. 네이티브 HWP 출력이나 한글 프로그램의 수식 변환을 검증한 것으로 해석하지 않는다. 수식 19개는 원래의 편집 가능한 Word 수식으로 보존한다.

저장소의 이전 기준 커밋은 `e125b2791b955483878439664bc73e5b6cbb88a0`이다. 과거 실행 기록은 그대로 유지하고 이번 검증을 새 경로에 기록한다. 원고 생성용 사본의 작성자 메타데이터는 익명 배포를 위해 제거했으며, 본문 XML이 동일함을 `metadata_anonymization.json`에 기록했다.

## 해석과 파일 무결성

현재 개정자료의 시간순 평가를 과거 최초 공표판본에 대한 실시간 예측평가로 해석하지 않는다. 추가 후보군과 학습기간 확장 비교는 사후 탐색적 분석이다. 기술시험의 합성 사례 수는 실제 참여자 수나 현장 오류율이 아니다.

모든 편집이 끝난 배포본에서만 `python code/add_hash_manifest.py --legacy-sha256`으로 두 목록을 갱신한다. 검증 전에 목록을 다시 만들면 변경 탐지의 의미가 사라진다. 해시는 파일 동일성 검사이며 원기관 자료의 진위·과거 확보시점의 인증이 아니다. 코드 라이선스와 기관 자료·글꼴 이용조건은 `PUBLICATION_NOTES.md`, `DATA_SOURCES.md`, `FONT_LICENSE.txt`를 따른다.
