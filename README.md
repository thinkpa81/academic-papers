# 5극 3특 지역고용 의사결정지원서비스

「5극 3특 지역고용 의사결정지원서비스의 설계와 기술평가」의 최종 원고(`261028_v3`)와 재현자료이다.

| 자료 | 파일 |
| --- | --- |
| 최종 논문 | [00_최종논문_261028_v3.docx](generated/00_최종논문_261028_v3.docx) |
| 수정 부분 빨간색 표시본 | [01_최종논문_261028_v3_수정부분_빨간색.docx](generated/01_최종논문_261028_v3_수정부분_빨간색.docx) |
| 최종 검증과 수정 내역 | [FINAL_REVIEW.md](results/revision_review_261028_v3/FINAL_REVIEW.md) |
| 참고문헌·인용 확인 | [REFERENCE_REVIEW.md](results/revision_review_261028_v3/REFERENCE_REVIEW.md) |
| 논문과 자료의 대응 | [PAPER_OUTPUT_MAP.md](PAPER_OUTPUT_MAP.md) |

현재 `main`에는 최종 원고, 분석·문서 생성 코드, 사용 자료, 표·그림, 검증 근거와 실행 안내를 둔다. 이전 원고와 중간 검토·재시도 산출물은 현재 목록에서 정리했다. 과거 버전 이름이 있는 자료라도 최종 분석의 입력·비교 기준·출처 확인 또는 원고 재작성에 필요한 파일은 유지한다. 특히 `support/manuscript/source_before_revision_261028_v3.docx`는 최종 원고와 수정표시본을 생성하는 기준 문서이다.

## 재현 실행

Python 3.12와 `requirements.txt`의 의존성을 준비한 뒤 저장소 루트에서 실행한다. 환경 준비와 선택 재적합은 [REPRODUCIBILITY.md](REPRODUCIBILITY.md)를 따른다.

```bash
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py
python -m unittest discover -s tests -v
python code/run_all.py --out ../rerun_261028_v3
python code/v3_independent_audit.py --out ../independent_check_261028_v3.json --replay ../rerun_261028_v3 --manuscript generated/00_최종논문_261028_v3.docx
```

## 자료 위치

| 경로 | 내용 |
| --- | --- |
| `generated/` | 최종 원고·수정표시본·빌드 기록 |
| `code/`, `tests/` | 분석·검사·그림·문서 생성·현장평가 코드와 시험 |
| `raw/`, `support/` | 사용한 확보본, 보존 모형·입력·비교 기준, 문서·양식 자료 |
| `results/`, `figures/` | 계산 결과, 연구표 24개, 기준 그림 4개와 검증 기록 |
| `field_study/` | 현장평가 계획과 빈 양식 |
| `manifest_sha256*.json` | 현재 파일의 크기·SHA-256·SHA-512 |

자료 출처와 이용조건은 [DATA_SOURCES.md](DATA_SOURCES.md), 공개 범위는 [PUBLICATION_NOTES.md](PUBLICATION_NOTES.md)에 있다.

## 검증 범위

2026년 10월 28일 9개 실행 단계를 재실행하여 CSV 157개·132,063행이 보존 결과와 일치함을 확인했다. 독립 검사 51개, 기존 검사 653개, 단위시험 12개, 그림 수치 검사 97개와 문자 검사 18개를 통과했다. 최종 원고·수정표시본은 각각 48쪽이며, 참고문헌 61개와 인용번호의 대응을 확인했다.

`preserved_audit`는 일부 보완분석의 보존 모형·입력·예측 검산이다. 모든 보완모형의 신규 적합을 뜻하지 않는다. 실제 현장 참여자·응답은 0건이며, 기술시험의 합성 사례를 사용자 효과로 해석하지 않는다. KOSIS 동적표 2개는 보존 공식 기록으로 확인했고 일부 출판사 전문에는 접근 제한이 있다.

원고는 제공된 HWP 양식의 문서 규격을 적용한 DOCX이다. 원본 전용 글꼴은 NanumMyeongjo로 대체했으며, 네이티브 HWP 변환을 검증하지 않았다.

논문 3.9절의 재현 기준은 [코드 커밋 `f4ae5299`](https://github.com/thinkpa81/academic-papers/commit/f4ae5299b2f4382f94e032804568bcd8554ca5fc)이다. 최종 원고를 처음 배포한 커밋은 [`9a87a0c2`](https://github.com/thinkpa81/academic-papers/commit/9a87a0c2965c730d6052b3de2762018b383cb8c0)이며, 현재 파일 정리는 논문의 분석 결과를 변경하지 않는다. 이전 파일은 Git 이력에서 확인할 수 있다.
