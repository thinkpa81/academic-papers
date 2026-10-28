# 2024년 지역 노동시장 공변량: 공식자료 확보 및 연결 검토

확인일: 2026-09-23. **2024년 자료는 확보했으나 기존 표본과의 연결정합성이 확보되지 않아 2025년 예측·평가는 HOLD이다. 자료 부재가 이유는 아니다.** 이 폴더의 작업은 원자료 수집·정의 확인·중첩 비교뿐이며 모형 적합, 기존 예측 변경, 2025년 손실 계산을 하지 않았다.

## 확보 결과와 상태

| 항목 | 결과 |
|---|---|
| 새 공식 자료 | OECD `OECD.CFE.EDS:DSD_REG_LABOUR@DF_LAB(2.4)` CSV 및 SDMX 구조 XML |
| 공간·연령·성별 | 한국 TL3 17시도, `Y15T64`(15~64세), `_T`(성별 전체) |
| 실업률 | `UNE_RATE`, `PT_LF_SUB`: 같은 연령·성별 노동력을 분모로 한 % |
| 경제활동참가율 | `LF_RATE`, `PT_POP_SUB`: 같은 연령·성별 인구를 분모로 한 % |
| 단위·시계열 표시 | `UNIT_MULT=0`, `DECIMALS=1`, `FREQ=A`(Annual), 관측상태 `A` |
| 2024년 완전성 | 17시도×2지표 = 34개 값 확보 |
| 2022~2023년 중첩 | 17시도×2년×2지표 = 68개 값, 누락·중복 없음 |
| 실업률 중첩 | 34/34개 일치 |
| 참가율 중첩 | 34/34개 불일치, 최대 절대차 4.0%p |
| 2025년 제공 여부 | 두 지표 모두 17시도 자료 존재. 제공 여부만 보고하고 2025년 값의 분석은 하지 않음 |

예: 서울 참가율은 원본 2022년 70.6%, 2023년 71.4%에서 새 자료 70.2%, 70.6%로 달라졌다. 충남 2023년은 74.5%에서 70.5%로 달라졌다. **연령·성별·분모·빈도 코드가 같아도 수치 연결은 확인되지 않았다.** 공표 빈티지, 분모 개정, 조사 원천 또는 관측기간 차이 중 무엇이 원인인지 확인하지 못했으며 어느 하나로 단정하지 않는다.

## 원파일·출처·수집 시각

- 주 원파일: `oecd/latest_developer_korea17_y15t64_since2022_raw.csv` (38,416바이트, 136행). API 응답 원문을 수정 없이 보존하였다. `startPeriod=2022` 요청으로 2025년 행도 포함되며, 정규화·중첩 검토 파일은 2022~2024년만 사용한다.
- 요청 UTC: **2026-09-23T14:36:28.208856+00:00**. 저장 완료 UTC: **2026-09-23T14:36:59.431077+00:00**.
- SHA-256: `d9c91feebbfb936726214b01765cacf4cad1d1ab3e0121514eca0ba937853b73`.
- 실제 성공 URL·응답 형식·시각·SHA: `oecd/latest_developer_narrow_retry_log.json`.
- 구조 XML: `oecd/latest_developer_schema.xml`, SHA-256 `12de90144c64e722a3ee4aae5d5b65266b7153f02a682c6776cf057ce0f24e66`. `latest_developer_download_log.json`과 `schema_definition_extract.json`에 취득·구조 기록을 보존하였다.
- 공식 화면: https://data-explorer.oecd.org/vis?lc=en&df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_REG_LABOUR%40DF_LAB&df[ag]=OECD.CFE.EDS&df[vs]=2.4
- 공식 구조 URL: https://sdmx.oecd.org/public/rest/dataflow/OECD.CFE.EDS/DSD_REG_LABOUR@DF_LAB/2.4?references=all
- 원본 패키지 노동시장 CSV의 SHA-256은 `618fe6aa0d38e1e13783276a0c0652122e0ff8af4bab645f4d3361fe0942a511`이다. 원본을 수정하지 않았다.

성공한 CSV 요청은 공식 화면의 Developer API 구조를 따르며 HTTP Accept는 `text/csv;file=true;labels=both`, User-Agent는 `Mozilla/5.0`이다. 실패한 구버전·표시용 flow·일부 기간 제한 요청과 부분 성공한 시도별 CSV도 `oecd/`에 요청 로그와 함께 보존하였다. 이 실패를 자료 미공표로 해석하지 않는다. `oecd/per_region/`의 부분 응답은 주 원파일을 대체하지 않는다.

## 조사·관측기간의 미확인 범위

OECD 새 rates 화면은 ILO 기준의 노동력조사를 사용하고 국가 통계기관·OECD 지역지표 작업반 등을 통해 자료를 수집한다고 설명한다. 그러나 확인한 SDMX 코드와 공통 설명만으로 한국의 모든 연도가 경제활동인구조사인지 지역별고용조사인지, 연평균인지 특정 조사월·반기 대표값인지 확정할 수 없다. `FREQ=A`는 연간 빈도 표시이며 연평균임을 독립적으로 입증하지 않는다.

KOSIS `DT_1DA7015S`는 경제활동인구조사 시도/연령별 표이며 15~64세 참가율과 연간 선택(2000~2025)이 실제 화면에 존재한다. 다만 해당 표에는 실업률 항목이 없다. `DT_1DA7107S` 실업률 표의 연령은 계·15~29·30~59·60세 이상으로 15~64세가 없다. 지역별고용조사 반기 총괄 `DT_1ES3B01J`는 15세 이상이며, `DT_1ES3B03J`의 연령 범주에도 15~64세가 없다. 이들 표로 원변수를 대체하거나 반올림된 인구·비율에서 실업률을 역산하지 않았다. 원본 서울 2023년 참가율 71.4%가 특정 반기의 값이라는 가설도 확인되지 않았다. 공식 표 URL·범주·내보내기 경로는 `kosis/discovery_note.md`에 있다.

## 검토 산출물과 재현

- `normalized_oecd_y15t64_2022_2024.csv`: 코드·라벨 결합형 CSV를 코드 열로 정리한 102행. 관측값의 보정·보간·역산 없음.
- `old_oecd_overlap_2022_2023.csv`: 원본에서 추출한 중첩 68행.
- `overlap_2022_2023_comparison.csv`: 키별 원값·새값·차이·일치 여부. 허용오차는 부동소수 처리용 `atol=1e-8, rtol=1e-10`이다.
- `source_gate_HOLD.json`: 완전성, 정의 코드, 중첩 비교 및 2025 연결 HOLD 판정. 승인·평가 실행 기록이 아니다.
- `verify_covariate_bridge.py`: 네트워크 호출 없이 저장 CSV의 위 검토를 재현한다. 예측 모형을 불러오거나 손실을 계산하는 코드가 없다.

워크스페이스 루트에서 실행하는 예:

```bash
python revision4/source_covariates/verify_covariate_bridge.py \
  --old-file inputs/package/한국IT서비스학회_재현패키지/raw/oecd_korea_regional_labour_raw.csv \
  --new-file revision4/source_covariates/oecd/latest_developer_korea17_y15t64_since2022_raw.csv \
  --output-dir revision4/source_covariates
```

입력·출력 경로는 인자로 지정하므로 패키지 위치를 옮긴 뒤에도 실행할 수 있다. 의존성은 Python, pandas, numpy이다. 원고에는 “2024년 공변량은 확보하였으나, 참가율의 2022~2023년 중첩 34개 값이 모두 달라 연결정합성을 확보하지 못하였다. 따라서 2025년 평가는 수행하지 않았다”로 기술할 수 있다.
