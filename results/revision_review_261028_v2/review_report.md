# 논문 요청사항 검토와 수정 결과

검토일 2026년 10월 28일  
대상 원고 00_최종논문_261027_v4.docx  
수정본 00_최종논문_261028_v2.docx

요청한 문체·방법·그림 관련 19개 항목과 참고문헌 5개를 검토하고 수정본에 반영하였다. 회고적·확장창·해석 범위·버전표기·과학적 수치 표기를 일괄적인 금지어로 판단하지 않았다. 연구 설계와 코드에 맞는 명료한 표현으로 정리하였다. 분석 결과와 수식은 유지했으며, KOSIS 확보일·구분류 추출범위·미국 변수명·절편 규제 대상 및 출처 보존범위는 사실관계에 따라 바로잡았다.

## 최종 산출물과 핵심 변경

- 논문 전문은 48쪽이며 수식 19개, 결과표 24개와 국문요약 표 1개, 그림 4개를 유지하였다. 본문·참고문헌의 108문단에는 URL 정리도 포함된다. 표 5셀의 문구와 그림 1–3을 수정하였다.
- 그림 1의 꺾인 경로에 반복된 화살촉을 제거했다. 그림 2·3의 기존 수치는 정확했고, 검증사례 0개·부분집계·후속 업무의 의미를 더 명확히 표시했다.
- 참고문헌 [5]·[6]의 날짜와 실제 추출기간을 정정했다. [15]의 공표일 13건을 대조했고 PDF 원파일과 추출텍스트를 구분했다. OECD 버전 2.0·2.4의 요청·응답·해시를 확인했다.
- 현재 ZIP과 기준 GitHub 커밋에 없던 근거자료 136개를 이전 재현패키지에서 복원했다. 분석 입력은 덮어쓰지 않았고 복원본은 별도 폴더에 보존했다.
- SHA-256 기반 근거 연결은 유지하면서 배포목록에 SHA-512를 추가했다. 최종 원고 재작성과 그림 생성·수치 검증·해시 검증 코드를 동봉했다.

## 검증의 범위

보존 결과 점검 653개, 기존 소프트웨어 테스트 12개, 그림 수치·집계 검사 97개가 통과했다. 복원 자료 136개는 이전 ZIP과 바이트가 같고 주요 출처 4개의 보존 해시도 일치했다. 미국 계열 예측 234개를 별도 행렬 계산으로 확인한 최대 차이는 4.6241×10⁻¹⁴였다. 원고는 같은 환경에서 다시 작성했을 때 바이트가 일치했다.

이번에 9단계 분석 전체를 재학습하거나 Pandera의 전체 기술시험을 새로 실행한 것은 아니다. 그 실행 기록은 이전 검증 이력으로 보존하고 이번 결과 검산과 구분했다. 실제 참여자와 사용자 관측은 0건이며 사용자 효과를 산출하지 않았다.

## 요청사항별 처리

| 번호 | 검토 대상 | 판단 및 수정 방향 |
|---|---|---|
| 1 | 본 연구의 구체화와 평가 위치 | 뜻은 통하지만 추상적이다. 표의 내용은 선행지식의 적용과 관련 본문 절이므로 ‘본 연구의 적용 내용과 관련 절’이 정확하다. |
| 2 | 회고적 예측성능과 구현 기능의 작동 | 회고적은 사용 가능한 말이다. 다만 개정자료 기반의 시간순 평가라는 구체적 설계가 보이지 않는다. ‘개정자료를 이용한 과거기간 예측성능과 서비스 기능의 요구사항 충족 여부’로 수정하였다. |
| 3 | 평가 및 점검 내용 | 잘못된 표현은 아니나 의미가 중복된다. ‘평가 항목 및 방법’으로 정리하였다. |
| 4 | 그림 1 화살표 | 꺾인 경로의 반복 화살촉 오류를 확인하여 단일 경로·단일 화살촉으로 수정했다. 등록 근거와 재검토 흐름을 분리했다. |
| 5 | 주분석은 … 회고적 평가 | ‘2026년 9월 확보한 개정자료를 시간순으로 분할하여 과거기간의 예측성능을 평가한 것’으로 설명한다. 과거 공표 당시 이용 가능한 자료로 수행한 실시간 검증과 구분한다. |
| 6 | 확장창 | expanding window의 번역으로 이해할 수 있으나 최초 정의가 부록에 있고 본문에서 먼저 반복된다. 본문 첫 등장에 ‘학습기간 확장 방식(expanding-window evaluation)’으로 정의하고 이후 명칭을 통일하였다. 6개 창은 6회 평가로 표기하였다. |
| 7 | v1, v2, v3 | 소프트웨어·검사 명세 버전으로 정의하면 사용할 수 있다. 최초 등장에 버전 1(v1)~버전 3(v3)을 정의하였다. 코드·원자료 식별자는 유지한다. |
| 8 | 실질 GDP·소비·투자 | 포괄적 약칭이어서 실제 변수 범위가 불명확하다. 공식 macrodata 정의에 따라 실질 국내총생산, 실질 개인소비지출, 실질 민간국내총투자로 구체화하였다. |
| 9 | SHA-256 대신 SHA-512 | SHA-512도 가능하다. 다만 본문 이름만 바꾸면 재현기록과 불일치한다. 과거 SHA-256 참조와 서비스 연결키는 유지하고 신규 배포목록에 SHA-512를 추가하는 방식이 적절하다. |
| 10 | 절편 축소와 소지역 추정 | 문체보다 규제 대상이 모호한 것이 문제이다. 실제 코드는 공통 절편·기울기를 규제하지 않고 시도·산업의 절편 편차에만 L₂ 규제를 적용한다. 인용 문헌의 Fay–Herriot 모형과 입력정보·추정 목적을 구분한다. |
| 11 | 그림 2 | 서울 BTE의 예측·편차·기여도·검증사례 0개를 대조해 일치를 확인했다. 제안된 현장 업무와 실제 수행 결과를 구분하여 다시 작성했다. |
| 12 | 그림 3 | 80개 셀을 재집계하여 일치를 확인했다. 부분집계 4개 셀의 별표·점선과 미산출 15개 셀을 구분하고 예측편차와 고용 증감의 차이를 명시했다. |
| 13 | 해석 범위 | 학술 문체로 적합하다. 해당 표에서는 ‘결과의 해석 범위’가 조금 더 명료하다. |
| 14 | 소급보정·신분류 공표 이력은 메타데이터 | 적합하지만 ‘소급보정 범위와 개정 산업분류의 공표 이력은 자료의 작성 및 변경 과정을 설명하는 메타데이터’로 구체화하였다. |
| 15 | IS에서 식별자로 기록 연결 | 기존 정보시스템 일반의 사실인지 저자의 설계 제안인지 불분명하다. PROV[56,57]의 관계 기록 원리를 근거로 두고 구체적 식별자 구조는 ‘본 연구가 제안하는 기관 적용 방안’으로 명시하였다. |
| 16 | 6.2와 6.3 자기비판 | 현재 근거의 적용조건과 미평가 영역을 공개하는 것은 필요하다. 한계를 삭제하지 않고 6.2는 성취와 적용범위를 먼저 제시하며, 6.3은 이미 준비한 과업·프로그램과 후속 실증계획 중심으로 정리하였다. |
| 17 | DT_1ES3B05S | 통계표 ID이므로 원형 표기가 적합하다. 대소문자와 밑줄을 유지하고 처음에 통계표 ID임을 알린다. |
| 18 | 절대 허용 오차 10⁻⁹ | 과학적 표기로 적합하다. 필요하면 절대차 \|a−b\|≤10⁻⁹라는 판정식을 명시하였다. 통계적 유의수준이나 상대오차와 혼동하지 않게 한다. |
| 19 | 참여자 0, not_evaluated, 재현파일 | 실제 관측이 없음을 밝히는 것은 필수이다. ‘아직 자료수집을 실시하지 않았으며 빈 자료의 분석 상태값은 not_evaluated’로 자연스럽게 쓸 수 있다. 경로는 GitHub 기준 커밋의 파일과 동봉 수정본을 구분한다. .gz는 gzip 무손실 압축으로 설명하며 압축파일 자체와 해제 내용의 해시는 구분한다. |


## 참고문헌 검증 결과

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


## 그림 검증 상세

검토 기준: 지정 원본 DOCX의 삽입 이미지, 동봉 재현패키지의 보존 예측값 및 근거 카드. 분석 결과와 모형은 변경하지 않았다.

## 그림 1

원그림에는 연구용 검토 상태에서 현재 근거로 복귀하는 경로를 세 개의 개별 화살표로 작성하여 꺾이는 지점마다 화살촉이 나타났다. 현재 근거에서 완료 요건 확인으로 이어지는 대각선과 복귀 경로가 가까이 배치되어 진행 방향이 모호했다. 이를 네 단계의 위에서 아래로 이어지는 과업 흐름으로 재배치하였다. 별도 등록 근거는 완료 요건 확인에만 진입한다. 상태에서 현재 근거로 돌아가는 재검토 경로는 연속된 단일 경로와 하나의 화살촉으로 작성했다. 후속 현장 업무는 점선으로 표시하고 실제 사용자 효과와 구분했다.

원본의 '공통 식별자'에 혼재했던 예측 식별자와 근거판본을 구분하였다. 예측 식별자는 시도·산업·목표시점이며 자료·모형은 근거판본이다. '회고적 예측평가'는 '과거자료 기반 예측평가'로 바꾸었다.

수정 이미지: `figures/paper_figure_01.png` 및 같은 이름의 PDF/SVG. 크기 147×164 mm. 생성 코드: `code/reviewability_figure.py`.

## 그림 2

원그림의 수치는 맞다. 보존 예측 CSV와 원근거 카드 대조 결과 기준모형 0.6705514379380221, 릿지 −0.398406218401248, 편차 −1.0689576563392702 로그포인트이다. 절편과 여덟 기여분의 합계는 릿지 예측값과 일치한다. 동일 지역·산업의 유효 검증사례 0개도 맞다. 사후 관측 로그변동 −31.70735977984932 및 단순변화율 −27.172284644194754%는 취업자 수 534,000명과 388,900명에서 재계산했다.

수치 설명을 유지하면서 '검증사례 0개'가 칸별 검증성능을 산출할 수 없다는 뜻임을 명시하였다. 후속 검토 과업의 중간 단계를 '현장 수요조사 계획'으로 정리하고 실제 담당자 수행 결과는 미측정이라고 표시하였다. 사후 관측값이 예측·편차 산정에 사용되지 않았다는 설명을 명시했다. 고용변동 표시구간과 기준모형 대비 편차를 구분하는 원래 정의는 유지하였다. 생성 코드의 예측값·편차·사후 관측값 표시는 검증된 수치 또는 원근거 카드에서 읽도록 정리하였다.

수정 이미지: `figures/paper_figure_02.png` 및 PDF/SVG. 크기 147×158 mm. 생성 코드: `code/redraw_figures.py`의 `draw3` 함수(기존 내부 번호 유지).

## 그림 3

원그림의 80개 권역–산업 셀은 모두 보존된 2025년 시도별 예측값에서 직접 재집계한 결과와 일치했다. 예측 취업자 수 합계와 동일 가용지역의 기준 취업자 수 합계에서 로그변동을 계산하고, 릿지와 전체 과거평균의 차이를 구했다. 완전 61개·부분 4개·미산출 15개, 하회 17개·근접 35개·상회 13개이다. 2025년 가용 시도 구성과 동일한 지역을 확보한 2020–2022년 자료의 편차 부호 일치는 91/188=48.40425531914894%였다.

수치와 색상 범주는 유지하였다. 일부 시도만 포함한 네 셀에는 별표와 점선 테두리를 함께 적용하여 적용범위가 더 잘 드러나도록 했다. 미산출은 ×로 유지한다. 하단의 '2026-09-26 개정자료 기반 회고적 평가'는 '2026년 9월 확보한 개정자료 기반 평가'로 정리하고 대경권의 미산출이 경계 조건 때문임을 표시했다. 날짜의 UTC·한국시각 차이를 임의로 단정하지 않았다.

수정 이미지: `figures/paper_figure_03.png` 및 PDF/SVG. 크기 147×132 mm. 생성 코드: `code/redraw_figures.py`의 `draw4` 함수(기존 내부 번호 유지).

## 재현과 검증

다음 명령은 4개 그림을 생성하며 논문 번호 `paper_figure_01/02/03/A1`와 기존 내부 번호 `figure1/3/4/2_final` 파일을 함께 기록한다.

```bash
python code/redraw_figures.py --out generated_figures
python code/verify_figure_data.py
```

검증 코드 `code/verify_figure_data.py`는 97개 검사에서 모두 통과하였다. 기본 출력은 `results/figure_data_check_261028_v2.json`이다. 수치 검증은 보존 예측값의 독립 재집계와 원근거 카드 대조이며, 모형 전체를 재학습한 결과는 아니다. 세 이미지 모두 450 dpi PNG와 벡터 PDF/SVG로 재작성하고 실제 렌더링 이미지를 열어 한글 표시·숫자·화살표·셀 표기를 확인하였다. DOCX 반영 시 그림별 원래 비율을 유지하고 그림 1은 새 세로 크기에 맞춰 재배치해야 한다.

원자료 경로:

- `support/baseline/base_v11/analysis_harmonized/results/main/test_predictions.csv`
- `support/baseline/base_v11/analysis_harmonized/results/main/validation_predictions.csv`
- `support/model_swap_addendum/guard_snapshot/source_snapshot/reproduced_service/evidence_card_2025_seoul_BTE.json`

추가로 `figures/fig3_validation.json`의 임시 절대경로는 패키지 내부 상대경로로 정정했다. 원근거 카드의 SHA-256은 그대로 유지했다.

## GitHub의 정확한 파일 위치

아래는 실제 확인한 공개 기준 커밋의 파일이다. 이번 v2에서 수정한 원고·그림·복원 출처는 동봉 ZIP을 기준으로 하며 기존 커밋에 소급하여 공개했다고 설명하지 않았다.

- [field_study/protocol.md](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/field_study/protocol.md)
- [field_study/preparation_status.json](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/field_study/preparation_status.json)
- [results/field_study_status/status.json](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/field_study_status/status.json)
- [code/collect_field_study.py](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/code/collect_field_study.py)
- [code/analyze_field_study.py](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/code/analyze_field_study.py)
- [results/transfer_evaluation/protocol_before_execution.json](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/protocol_before_execution.json)
- [results/transfer_evaluation/cases_before_execution.json.gz](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/cases_before_execution.json.gz)
- [results/transfer_evaluation/reference_context.json.gz](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/reference_context.json.gz)
- [results/transfer_evaluation/case_results.csv.gz](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/case_results.csv.gz)
- [results/transfer_evaluation/trust_boundary_results.csv](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/trust_boundary_results.csv)
- [results/transfer_evaluation/execution_start.json](https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/results/transfer_evaluation/execution_start.json)

`.gz`는 gzip 무손실 압축본이다. 압축파일과 압축 해제 내용의 해시는 서로 다르므로 구분해야 한다. 시험 입력과 참조자료의 해제 내용은 `execution_start.json`의 SHA-256과 일치했다. 상세 결과는 ZIP의 `results/revision_review_261028_v2/`에 있다.

## 재현 방법

ZIP을 해제한 `academic-papers` 폴더에서 Python 3.12와 `requirements.txt`의 환경을 사용한다. 원고는 제공된 나눔명조 글꼴을 설치하면 같은 서체로 확인할 수 있다.

```bash
python verify_package.py
python code/add_hash_manifest.py --verify
python code/verify_results.py
python code/verify_figure_data.py
python -m unittest discover -s tests -v
python code/redraw_figures.py --out generated_figures
python code/build_manuscript.py --output generated/00_최종논문_261028_v2.docx
```

생성파일을 패키지 안에 추가하면 배포목록 작성 당시 파일 집합과 달라진다. 파일 동일성 검사는 새 파일 생성 전에 수행한다. 전체 분석 재실행은 README의 `code/run_all.py` 안내를 따른다.

## 검증에서 구분한 사항

KOSIS 동적 통계표의 현재 웹 화면은 이번 웹 도구에서 직접 열리지 않았다. 해당 두 표는 원문 DOM·주석·요청 명세와 보존 해시로 확인했다. KOSIS S의 9월 23일은 보존 파일의 수정시각에 근거한 확보 기록이다. 2013년 이후 KSIC11 소급반영은 2026년 확보 J 표의 주석에 근거하며, 과거 공표 당시에도 동일 값이 존재했다는 뜻이 아니다. 보도자료 PDF는 공식 주소·추출텍스트·과거 해시를 보존했고 PDF 원파일 자체를 동봉했다고 쓰지 않았다.

수정본은 확인된 연구의 기여와 적용조건을 명확히 한 원고이다. 실제 사용자 효과와 전향적 예측성능은 후속 평가 과제로 남겨 두었다.
