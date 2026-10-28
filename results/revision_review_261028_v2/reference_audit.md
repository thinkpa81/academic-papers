# 참고문헌 검증 결과

검토일 2026년 10월 28일. 대상은 원고의 [5], [6], [15], [41], [42]이다. 공식 웹 자료와 연구자가 보존한 원자료를 구별하여 대조하였다.

## 판단과 수정안

### 참고문헌 5

판정: 보존본 확인 및 확보일 수정

J 표의 보존 DOM 주석에 제11차 한국표준산업분류를 2013년 상반기부터 소급 반영하였음이 명시된다. 표 전체 수록기간은 2013H1–2025H2이나 분석 추출은 각 연도 H1 2013–2025이다. captured_at_utc는 2026-09-26T12:03:19.871Z로 한국 날짜도 9월26일이다. 9월27일 후속 확인은 원고의 저자 기록이며 독립 로그로 재검증하지 못했다.

[5] 국가데이터처, “시도/산업별 취업자”, 국가통계포털(KOSIS), 통계표 ID DT_1ES3B05J, 제11차 한국표준산업분류, 분석대상 2013–2025년 각 상반기, 2026년 보존 추출본. https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B05J (확보일: 2026.9.26).

보존 근거:
- `raw/kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json`
- `raw/table_metadata_and_notes.txt`
- `raw/source_acquisition_manifest.json`

### 참고문헌 6

판정: 복원 보존본 확인 및 추출범위 정정

S 표의 보존 DOM과 manifest를 이전 재현패키지에서 복원했다. 실제 대조 추출기간은 2022년 상·하반기, 2023·2024년 상반기이다. 2013–2024는 본 연구가 모두 추출한 기간으로 쓸 수 없다. 별도 획득 타임스탬프 없이 로컬 보존 파일 수정시각에 근거한 확보 기록이므로 그 한계도 기록한다.

[6] 국가데이터처, “시도/산업별 취업자”, 국가통계포털(KOSIS), 통계표 ID DT_1ES3B05S, 제10차 한국표준산업분류, 보완분석 대조 추출기간: 2022년 상·하반기 및 2023·2024년 상반기, 2026년 보존 추출본. https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B05S (보존 파일의 확보 기록: 2026.9.23).

보존 근거:
- `raw/supplementary_sources_261028_v2/source_employment/kosis_DT_1ES3B05S_2022H1H2_2023H1_2024H1_precision1_dom.json`
- `raw/supplementary_sources_261028_v2/source_employment/kosis_oldS_H1H2_audit_precision1_manifest.json`

### 참고문헌 15

판정: 13개 보도자료 및 공표일 모두 공식 웹 대조 확인

2013–2025 각 연도 상반기 자료 13건의 게시월은 모두 10월이다. 본문 12개월 관측간격과 약6개월 선행기간을 구별하는 근거로 적절하다. 원자료 PDF 파일 자체는 복원 ZIP에 없고 HTML, PDF 텍스트 추출본, 공식 URL 및 원파일 해시 기록이 있다. 최신 자료라는 표현은 2026년 상반기 결과가 2026.10.27 발표되었으므로 분석에 포함한 2025년 자료로 바꾼다. 저자기관 통계청·국가데이터처는 공동 작성이 아니라 연도별 기관명 변경이다.

[15] 통계청(2013–2024)·국가데이터처(2025), “상반기 지역별고용조사 취업자의 산업 및 직업별 특성”, 2013–2025년 연도별 보도자료 13건. 연도별 제목·게시일·조사대상 주간·공식 PDF URL 및 텍스트 추출본은 재현패키지의 공표일 목록과 출처 자료에 수록. 분석에 포함한 2025년 자료: https://mods.go.kr/board.es?act=view&bid=211&list_no=439006&mid=a10301010000 (게시일: 2025.10.28; 재확인일: 2026.10.28).

보존 근거:
- `raw/supplementary_sources_261028_v2/source_release/release_calendar_H1_2013_2025.json`
- `raw/supplementary_sources_261028_v2/source_release/`

### 참고문헌 41

판정: 공식 데이터셋과 2.0·2.4 보존본 확인

공식 OECD 검색자료에서 데이터셋명과 데이터플로 2.0·2.4가 확인된다. v2.0 CSV 6,942행의 STRUCTURE_ID는 OECD.CFE.EDS:DSD_REG_ECO@DF_EMP(2.0), TERRITORIAL_LEVEL은 TL3이다. v2.4 응답 1,878,576바이트와 요청로그·해시 일치. v2.4 원응답은 KOR/TL2/TL3를 포함한 광역조회이므로 분석에 사용한 한국 TL3 부분집합과 구별한다. 데이터플로 버전과 확보시점 자료판본은 같은 개념이 아니므로 함께 기록한다.

[41] OECD, “Employment by main economic activity – Regions”, OECD Regions, Cities and Local Areas Database, 데이터플로 OECD.CFE.EDS:DSD_REG_ECO@DF_EMP, 한국 TL3 분석자료, 버전 2.0 및 2.4, 2026년 보존 추출본. https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bid%5D=DSD_REG_ECO%40DF_EMP&df%5Bvs%5D=2.4&lc=en (확보일: 버전 2.0은 2026.9.17 UTC, 버전 2.4는 2026.9.23 UTC; 요청조건·응답·해시 보존).

보존 근거:
- `raw/oecd_korea_regional_industry_raw.csv`
- `raw/oecd_source_manifest.json`
- `raw/supplementary_sources_261028_v2/source_employment/oecd_latest_exact_download.json`
- `raw/supplementary_sources_261028_v2/source_employment/oecd_korea_emp_2_4_latest.csv`

### 참고문헌 42

판정: 공식 데이터셋과 2.0·2.4 보존본 확인

공식 OECD 검색자료에서 데이터셋명과 데이터플로 2.0·2.4가 확인된다. v2.0 CSV 19,032행의 STRUCTURE_ID는 OECD.CFE.EDS:DSD_REG_LABOUR@DF_LAB(2.0), TERRITORIAL_LEVEL은 TL3이다. 복원한 v2.4는 한국17개TL3, 15–64세, 성별전체, LF_RATE·UNE_RATE, 2022년이후 조건의 조회이며 응답38,416바이트와 해시가 일치한다. 모든 노동지표를 두 버전 모두 전기간 확보한 것처럼 쓰지 않는다.

[42] OECD, “Labour statistics – Regions (for Developer API)”, OECD Regions, Cities and Local Areas Database, 데이터플로 OECD.CFE.EDS:DSD_REG_LABOUR@DF_LAB, 한국 TL3 분석자료, 버전 2.0 및 2.4, 2026년 보존 추출본. https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bid%5D=DSD_REG_LABOUR%40DF_LAB&df%5Bvs%5D=2.4&lc=en (확보일: 버전 2.0은 2026.9.17 UTC, 버전 2.4는 2026.9.23 UTC; 요청조건·응답·해시 및 중첩기간 대조 보존).

보존 근거:
- `raw/oecd_korea_regional_labour_raw.csv`
- `raw/oecd_source_manifest.json`
- `raw/supplementary_sources_261028_v2/source_covariates/oecd/latest_developer_narrow_retry_log.json`
- `raw/supplementary_sources_261028_v2/source_covariates/oecd/latest_developer_korea17_y15t64_since2022_raw.csv`
- `raw/supplementary_sources_261028_v2/source_covariates/overlap_2022_2023_comparison.csv`

## 공표일 및 관측 주간 대조

13건 모두 공식 웹의 제목·게시일을 이번 검토에서 재확인했다. 관측 주간은 각 PDF의 조사개요를 재확인했고 복원 캘린더와 일치했다. PDF 페이지는 파일의 물리적 페이지를 1부터 센 번호이다.

| 조사연도 | 조사대상 주간 | 공식 게시일 | PDF 페이지 | 공식 자료 |
|---|---|---|---:|---|
| 2013 | 2013-04-14–2013-04-20 | 2013-10-30 | 27 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=309601&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=309601&seq=1) |
| 2014 | 2014-04-13–2014-04-19 | 2014-10-30 | 51 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=331450&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=331450&seq=2) |
| 2015 | 2015-04-12–2015-04-18 | 2015-10-28 | 51 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=349269&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=349269&seq=8) |
| 2016 | 2016-04-10–2016-04-16 | 2016-10-26 | 61 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=356938&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=356938&seq=3) |
| 2017 | 2017-04-09–2017-04-15 | 2017-10-24 | 61 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=363875&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=363875&seq=1) |
| 2018 | 2018-04-15–2018-04-21 | 2018-10-23 | 44 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=371172&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=371172&seq=3) |
| 2019 | 2019-04-14–2019-04-20 | 2019-10-22 | 45 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=378140&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=378140&seq=1) |
| 2020 | 2020-04-12–2020-04-18 | 2020-10-20 | 45 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=385719&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=385719&seq=1) |
| 2021 | 2021-04-11–2021-04-17 | 2021-10-19 | 45 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=414646&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=414646&seq=2) |
| 2022 | 2022-04-10–2022-04-16 | 2022-10-18 | 49 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=421281&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=421281&seq=10) |
| 2023 | 2023-04-09–2023-04-15 | 2023-10-17 | 81 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=427575&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=427575&seq=1) |
| 2024 | 2024-04-14–2024-04-20 | 2024-10-08 | 81 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=433146&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=433146&seq=1) |
| 2025 | 2025-04-13–2025-04-19 | 2025-10-28 | 75 | [보도자료](https://mods.go.kr/board.es?act=view&bid=211&list_no=439006&mid=a10301010000) · [PDF](https://mods.go.kr/boardDownload.es?bid=211&list_no=439006&seq=3) |

## 해석상 유의점

- 2025년 보도자료가 명시한 당시 KSIC11 소급범위(2017–2024년 상반기)와 2026년 확보 J 표의 주석(2013년 상반기부터 소급)은 자료시점이 다르다. 후자를 근거로 현재 개정계열의 분류 일치를 설명할 수 있지만, 당시에 같은 값이 공개되어 있었다고 해석할 수 없다.
- RSE 25% 이상 별표 표시의 직접 출처는 [5]의 보존 주석이다. Fay–Herriot 논문 [27]은 이 표의 표시 기준을 뒷받침하는 인용으로 부적절하다.
- 2026년 상반기 결과는 2026년 10월 27일 공개되었다. 분석범위를 임의로 확대하지 않고, [15]의 최근 자료를 분석에 포함한 2025년 자료로 정정한다. 공식 URL: https://mods.go.kr/board.es?act=view&bid=211&list_no=447616&mid=a10301030100
- OECD의 2.0·2.4는 데이터플로 버전이다. 확보일과 해시를 함께 적어 실제 사용 자료판본을 식별한다.
- PDF 원문 파일을 보존했다고 쓰지 않는다. 복원된 자료는 공식 게시면 HTML, PDF 텍스트 추출본, URL 및 과거 PDF 해시 기록이다.
- KOSIS J/S의 현재 공개 동적 페이지는 이번 웹 도구에서 직접 로드되지 않았다. 이는 자료가 존재하지 않는다는 뜻이 아니며 보존본 검증과 구별한다.

## 바이트 대조

KOSIS J DOM, KOSIS S DOM, OECD EMP 2.4 CSV, OECD 노동 2.4 CSV의 보존 SHA-256과 현재 파일을 대조한 결과 4/4 일치했다.

## OECD 공식 확인 경로

- [고용 산업별 데이터플로 2.0](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_REG_ECO%40DF_EMP&df%5Bvs%5D=2.0&lc=en)
- [고용 산업별 데이터플로 2.4](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=DisseminateFinalDMZ&df%5Bid%5D=DSD_REG_ECO%40DF_EMP&df%5Bvs%5D=2.4&lc=en)
- [지역 노동 데이터플로 2.0](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=DisseminateFinalDMZ&df%5Bid%5D=DSD_REG_LABOUR%40DF_LAB&df%5Bvs%5D=2.0&lc=en)
- [지역 노동 데이터플로 2.4](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.CFE.EDS&df%5Bds%5D=dsDisseminateFinalDMZ&df%5Bid%5D=DSD_REG_LABOUR%40DF_LAB&df%5Bvs%5D=2.4&lc=en)
