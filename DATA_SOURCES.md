# 분석자료의 확보 범위와 출처

이 문서는 `261028_v3` 배포본의 자료 위치와 확보 기록을 설명한다. 기존 공개 기준 커밋 `e125b2791b955483878439664bc73e5b6cbb88a0`에 없던 보완 출처 136개를 이전 재현패키지에서 복원하였다. 복원은 과거 보존본을 이번 패키지에 다시 포함한 작업이며, 자료를 2026년 10월 28일 새로 조사하거나 당시 기관 응답을 새로 생성한 작업이 아니다.

## 분석용 확보본

| 자료와 분석 범위 | 확보 기록 | 동봉 위치 |
| --- | --- | --- |
| KOSIS `DT_1ES3B05J`, 제11차 산업분류, 2013–2025년 각 상반기 | DOM 기록 `2026-09-26T12:03:19.871Z`; 한국 날짜도 9월 26일 | `raw/kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json`, `raw/source_acquisition_manifest.json`, `raw/table_metadata_and_notes.txt` |
| KOSIS `DT_1ES3B05S`, 제10차 산업분류, 2022년 상·하반기 및 2023·2024년 상반기 대조 추출 | 보존 파일의 확보 기록 2026-09-23; 별도 획득 타임스탬프가 아닌 파일 수정시각 근거 | `raw/supplementary_sources_261028_v2/source_employment/kosis_DT_1ES3B05S_2022H1H2_2023H1_2024H1_precision1_dom.json`, 같은 폴더의 `kosis_oldS_H1H2_audit_precision1_manifest.json` |
| OECD 고용 `DSD_REG_ECO@DF_EMP` 2.0, 한국 TL3 | 2026-09-17 UTC 확보 기록 | `raw/oecd_korea_regional_industry_raw.csv`, `raw/oecd_source_manifest.json` |
| OECD 노동 `DSD_REG_LABOUR@DF_LAB` 2.0, 한국 TL3 | 2026-09-17 UTC 확보 기록 | `raw/oecd_korea_regional_labour_raw.csv`, `raw/oecd_source_manifest.json` |
| OECD 고용 `DSD_REG_ECO@DF_EMP` 2.4 원응답 | 2026-09-23 UTC; 광역조회 응답에서 한국 TL3 분석 부분집합을 사용 | `raw/supplementary_sources_261028_v2/source_employment/oecd_korea_emp_2_4_latest.csv`, 같은 폴더의 `oecd_latest_exact_download.json` |
| OECD 노동 `DSD_REG_LABOUR@DF_LAB` 2.4 원응답 | 2026-09-23 UTC; 한국 17개 TL3·15–64세·성별전체·LF_RATE/UNE_RATE·2022년 이후 조건 | `raw/supplementary_sources_261028_v2/source_covariates/oecd/latest_developer_korea17_y15t64_since2022_raw.csv`, 같은 폴더의 `latest_developer_narrow_retry_log.json` |
| 2013–2025년 상반기 산업·직업 특성 보도자료 13건 | 공식 게시일은 연도별 10월; 2026-10-28 공식 웹 재확인 | `raw/supplementary_sources_261028_v2/source_release/release_calendar_H1_2013_2025.json` 및 같은 폴더의 HTML·PDF 텍스트 추출본 |

KOSIS J 보존 표의 주석에는 제11차 산업분류를 2013년 상반기부터 소급 반영했다고 명시되어 있다. 표 전체 수록기간과 연구자가 선택한 상반기 추출기간을 구분한다. S 표는 대조용 일부 반기만 추출했으므로 2013–2024년 전기간을 확보했다고 서술하지 않는다.

OECD의 데이터플로 버전 번호와 확보시점의 자료판본은 같은 개념이 아니다. 인용할 때 버전·요청조건·확보일을 함께 제시한다. 노동 2.4의 좁은 조회범위를 2.0 전체 지표·기간과 같다고 해석하지 않는다. 중첩기간 대조는 `raw/supplementary_sources_261028_v2/source_covariates/overlap_2022_2023_comparison.csv`에 있다.

보도자료의 공식 URL, 공표일, 조사대상 주간과 PDF 원파일 해시는 목록에 보존한다. **PDF 원본 파일 자체는 이번 복원 자료에 포함하지 않았다.** 동봉된 것은 보존 HTML과 PDF 텍스트 추출본이다. 당시 최초 공표 셀값 전체의 변경 이력을 확보했다는 의미도 아니다. 분석에 포함한 2025년 자료의 게시일은 2025-10-28이며, 2026년 자료가 이미 발표되어 이를 단순히 ‘최근 자료’라고 부르지 않는다.

## 복원과 해시 검증

`raw/supplementary_sources_261028_v2/`의 136개 파일은 이전 ZIP의 바이트와 모두 일치한다. 복원 원본 ZIP의 SHA-256은 `5fae08aea046bec0c54e85d4ea799c7782474217d2bb5687accd477849087cdc`이다. KOSIS J·S와 OECD 2.4 고용·노동 원응답의 네 해시는 각 보존 명세와 대조하여 일치했다. 복원 파일별 크기·해시는 `raw/supplementary_sources_261028_v2/restoration_manifest.json`에 있으며, 최종 논문의 출처 검증은 `results/revision_review_261028_v3/reference_audit_all.json`을 따른다.

배포 파일의 크기·SHA-256은 `manifest_sha256.json`, SHA-256·SHA-512 병기는 `manifest_sha256_sha512.json`에 있다. 과거 명세의 SHA-256과 생성시각은 그대로 유지한다. 파일 해시는 동일성 확인에 쓰이며 자료 진위나 당시 공표 상태를 독립 인증하지 않는다.

## 공식 조회 주소

- KOSIS J: https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B05J
- KOSIS S: https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B05S
- OECD 고용: https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bid%5D=DSD_REG_ECO%40DF_EMP&df%5Bvs%5D=2.4&lc=en
- OECD 노동: https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bid%5D=DSD_REG_LABOUR%40DF_LAB&df%5Bvs%5D=2.4&lc=en
- 분석에 포함한 2025년 보도자료: https://mods.go.kr/board.es?act=view&bid=211&list_no=439006&mid=a10301010000

원 API 주소와 필터는 각 manifest 및 요청 로그를 따른다. 웹에서 새로 받은 값은 통계 개정으로 달라질 수 있으므로 논문 재현용 확보본을 덮어쓰지 않는다. 새로운 분석에는 별도 경로와 확보일·조회조건·해시를 기록한다.

## 미국 거시경제 자료

statsmodels의 `macrodata` 확보본과 제공 문서는 `raw/transfer_macrodata/`에 있다. 사용 변수는 `realgdp`(실질 국내총생산), `realcons`(실질 개인소비지출), `realinv`(실질 민간국내총투자)이다. 1959년 1분기–2009년 3분기의 203개 분기에서 계산한 로그변화율을 공통 검사 요건의 이식시험에 사용했다. 원자료의 계절조정·단위 등 정의는 동봉 제공 문서와 공식 설명을 따른다.

- 공식 설명: https://www.statsmodels.org/stable/datasets/generated/macrodata.html
- 확보 판본: https://github.com/statsmodels/statsmodels/blob/d07a39609cdf57b6898bb9adb87e7821904482aa/statsmodels/datasets/macrodata/macrodata.csv
- 연구 확보일: 2026-10-27. 제공 문서상 최초 확보일: 2009-12-15.
- 원문 SHA-256: `d93c0d3a7a77ef83c3af14e46032bb1d02ae3a512b22ab94159a8ca226fcf708`.

제공 문서는 데이터를 public domain으로 설명하고 FRED·BLS를 출처로 기록한다. 제공 코드와 statsmodels의 라이선스 고지도 동봉하였다. 자료 이식시험은 새로운 거시경제 예측모형의 우월성 평가가 아니다.

## 자료 이용과 출처

KOSIS 국내 통계정보, OECD 데이터, 제공 문서와 글꼴의 이용조건은 각각의 기관 지침을 따른다. 기존 패키지에서 2026-10-27 확인한 안내 주소는 아래와 같다. 개별 자료의 제3자 권리나 추가 제한이 코드의 라이선스로 대체되지는 않는다.

- KOSIS 통계정보 이용지침: https://stat.kosis.kr/nsistN/kosisUseGuide.do
- OECD Terms and Conditions: https://www.oecd.org/en/about/terms-conditions.html

원기관의 확보본과 저자가 정규화·결합·집계한 결과를 구별하고, 기관·자료명·조회범위·버전·URL·확보 기록을 함께 인용한다.


## 2026년 10월 28일 출처 재확인

참고문헌 61개를 전수 검토하였다. 59개는 현재 공식·출판사·기관·출판사 등록 메타데이터를 확인했고 KOSIS J·S 두 동적표는 보존 공식 DOM과 주석·해시를 대조하였다. 2013-2025년 보도자료 13건의 공식 PDF 주소도 개별 열람했다. 일부 DOI 원문은 유료·403·브라우저 확인 등으로 전문 접근이 제한된다. 실재·서지·주장 지지·현재 접근을 각각 기록한 `results/revision_review_261028_v3/reference_audit_all.json`을 참고한다. 이번 작업은 분석용 원자료를 새 판본으로 교체한 작업이 아니다.
