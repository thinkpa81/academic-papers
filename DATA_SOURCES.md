# 원자료와 다운로드 안내

## 다시 다운로드해야 하는가

이 배포본으로 논문 결과를 재현할 때에는 별도 다운로드가 필요 없다. 분석이 사용한 KOSIS와 OECD 확보본, 정규화 자료, 출처 기록과 해시를 함께 제공한다. 현재 웹사이트에서 새로 받으면 통계 개정이나 제공 버전 변경으로 값이 달라질 수 있으므로 논문 재현용 확보본을 새 자료로 덮어쓰지 않는다. 새로운 시점을 분석할 때에는 별도 폴더에 내려받고 확보일·조회조건·해시를 새로 기록한다.

| 자료 | 확보 기록 | 배포 위치와 쓰임 |
|---|---|---|
| KOSIS 지역별고용조사 `DT_1ES3B05J`, KSIC11, 2013–2025 상반기 | 2026-09-26 12:03:19.871 UTC; 소수점 1자리 공식 표 화면 확보 | `raw/kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json`; 동일 바이트가 `support/forecast_addendum/bundled_inputs/source_harmonized/`에 있으며 주분석 재구성에 사용 |
| OECD Regional Economy, `DSD_REG_ECO@DF_EMP` v2.0 | 2026-09-17 확보 기록 | `raw/oecd_korea_regional_industry_raw.csv`; 원계열 보완분석의 원자료 |
| OECD Regional Labour, `DSD_REG_LABOUR@DF_LAB` v2.0 | 2026-09-17 확보 기록 | `raw/oecd_korea_regional_labour_raw.csv`; 지역 노동시장 보완자료 |
| OECD 2024년 평가 및 관련 비교자료 | 각각의 보존 manifest 참조 | `support/baseline/base_v11/extensions/temporal2024/source_employment/` |

KOSIS 공식 표: https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B05J

OECD의 원래 API 주소·필터·버전은 `raw/oecd_source_manifest.json`, KOSIS 조회 조건과 단위·결측 규칙은 `raw/source_acquisition_manifest.json` 및 `raw/table_metadata_and_notes.txt`에 있다. 모든 배포 파일의 해시는 `manifest_sha256.json`에 기록한다. 현재 API가 과거 버전을 제공하지 않더라도 보관한 확보본을 통해 재현할 수 있다.

## GitHub에 데이터도 포함할 수 있는가

기관의 공개 통계라고 해서 반드시 이용자가 각자 다운로드해야 하는 것은 아니다. 재배포 조건에 따라 원자료 확보본을 함께 제공하거나 출처·조회조건·다운로드 절차만 제공할 수 있다.

2026-10-27 확인한 KOSIS 이용지침은 국내 통계정보의 재사용·재배포를 허용하며 출처를 요구한다. 국제·북한통계, 간행물, 제3자 권리는 예외 규정이 적용된다. 본 주분석은 국내 지역별고용조사이며 OECD 자료는 OECD에서 직접 확보한 기록을 보존하였다.

OECD의 데이터 규정은 추가 제한이 없는 자료의 복사·공유·배포를 허용하며 적절한 출처 표기를 요구한다. 개별 자료의 추가 조건·제3자 권리는 별도로 적용된다. OECD 데이터 전체를 일괄적으로 CC BY 4.0이라고 표시하지 않는다. 배포 자료의 인용 시 기관, 자료명, 버전·조회조건, URL, 확보일을 함께 적는다.

- KOSIS 통계정보 이용지침: https://stat.kosis.kr/nsistN/kosisUseGuide.do
- OECD Terms and Conditions, §3 Data: https://www.oecd.org/en/about/terms-conditions.html

원자료의 수치와 출처를 보존하고, 저자의 정규화·결합·집계 결과는 별도의 분석 산출물로 표시한다. 코드에 붙일 라이선스가 제3자 데이터·글꼴·기관 문서의 이용조건을 대체하지 않는다.

## 외부 공개자료 적용시험

statsmodels가 제공한 미국 거시경제 공개자료의 정확한 저장소 판본과 원문을 `raw/transfer_macrodata/`에 보존하였다. 제공 문서는 데이터가 public domain임을 명시하며, FRED와 BLS를 출처로 기록한다. 세 실질 총량 계열을 이용한 계산과 이용 범위는 `TRANSFER_EVALUATION.md`에 정리하였다. 원문 제공 코드의 BSD 고지와 statsmodels 라이선스도 함께 보존하였다.

- 공식 자료 설명: https://www.statsmodels.org/stable/datasets/generated/macrodata.html
- 확보 판본: https://github.com/statsmodels/statsmodels/blob/d07a39609cdf57b6898bb9adb87e7821904482aa/statsmodels/datasets/macrodata/macrodata.csv
- 본 연구 확보일: 2026-10-27; 제공 문서상 최초 확보일: 2009-12-15
- 원문 SHA-256: `d93c0d3a7a77ef83c3af14e46032bb1d02ae3a512b22ab94159a8ca226fcf708`

이 확보본도 배포 패키지에 포함하므로 기존 결과 재현을 위한 별도 다운로드는 필요 없다.
