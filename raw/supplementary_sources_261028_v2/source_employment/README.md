# 산업고용 신규자료 확보·정합성 작업

이 폴더는 자료 확보와 중첩연도 검산만을 위한 작업물이다. 모형 추정이나 신규 결과연도 성능평가는 수행하지 않았다.

## 최종 확보 상태

최종 평가용 파일은 `oecd_v2_4_target2024_170.csv`이다. 공식 OECD 2.4 원 CSV `oecd_korea_emp_2_4_latest.csv`에서 EMP·A·TL3·PS·UNIT_MULT=0 및 17시도·10산업·2024년을 필터링한 170행이며, 원자료에 제공된 집계값을 그대로 사용했다. `oecd_2024_target_manifest.json`에 출처·필터·정합성·제한과 SHA-256을 보존한다.

공식 Data Explorer에서 관찰한 CSV URI를 Python 표준 HTTP 요청으로 내려받아 HTTP 200을 확인했다. 파일과 응답 메타데이터는 `oecd_latest_exact_download.json`에 기록했다. 초기 API·브라우저 요청 실패는 `oecd_latest_acquisition_attempt.json`에 별도로 남겼다. 초기 실패를 최종 미확보로 해석하지 않는다. 접속 통제나 브라우저 보안 제한을 우회하지 않았다.

검산 결과는 다음과 같다.

- 기존 OECD 2.0과 최신 2.4의 2022·2023년 값은 각각 187개 산업·총계 셀 모두 일치한다(`oecd_v2_4_vs_old_overlap.csv`).
- OECD 2022는 KOSIS 2022년 하반기의 비교 가능한 177개 셀, OECD 2023은 2023년 상반기의 176개 셀과 정확히 일치한다. 따라서 기존 2022→2023 목표는 10월→4월의 반년 변화이다. 기존 전체 시계열을 동일한 1년 간격으로 해석하지 않는다(`overlap_period_diagnosis.csv`).
- OECD 2024는 KOSIS 구분류 KSIC10의 2024년 상반기와 비교 가능한 175개 셀 모두 일치한다. 2023년 상반기→2024년 상반기는 1년 간격이다(`oecd_v2_4_2024_vs_kosis_H1.csv`).
- KOSIS 하이픈을 결측으로 유지한 보수적 부분집합은 158개 산업 셀이다. 최초 158개 게이트와 키는 보존하며, 공식 OECD 직접 집계값 확보 후 주분석 대상은 170개로 확정되었다. 부분집합은 자료 가용성 민감도용이다. 이 폴더에서는 어느 집합의 예측오차도 계산하지 않았다.
- OECD 2025에는 서울 A 값이 없고 서울 총계가 16,352,800명으로 9개 산업 합계 5,180,400명과 맞지 않는다. KOSIS 신분류 표의 2025년 상반기 서울 총계는 5,180,600명이며 A는 0.0천명(단위 미만)이다. 임의 보정하지 않고 2025년을 보류했다(`oecd_v2_4_2025_source_anomalies.csv`).
- KSIC11 신분류 표 J의 2023·2024년 상반기는 구분류 S와 완전히 같지 않다. 비교 가능한 셀 중 각각 101/176·89/175만 정확히 같고 최대 차이는 6,400명이다. 특히 K·OTQ 간 차이가 있어 2024→2025를 같은 분류 계열로 단순 연결하지 않는다(`ksic11_vs_ksic10_same_H1_bridge.csv`).

## 재현

이 README가 있는 폴더에서 필요한 pandas가 설치된 Python으로 실행한다.

```bash
python normalize_oecd_latest.py
python parse_kosis_employment.py kosis_DT_1ES3B05S_2022H1H2_2023H1_2024H1_precision1_dom.json --prefix kosis_oldS_H1H2_audit_precision1
python parse_kosis_j_vertical.py kosis_DT_1ES3B05J_2023_2025H1_precision1_dom.json --prefix kosis_newJ_H1_2023_2025
```

첫 명령은 공식 원 CSV에서 170개 2024년 타깃을 재생성하고 2025년 완전성·총계 진단을 저장한다. 나머지 명령은 공식 웹 표의 DOM 원본을 파싱한다. DOM 자료는 브라우저에서 읽힌 셀 텍스트·rowspan·colspan을 그대로 보존했으며 CSV/XLS 다운로드라고 표현하지 않는다. 단위는 천명에서 명으로 1,000을 곱했으며, 원문 하이픈과 RSE 별표는 별도 필드에 보존했다. 소수점 0자리 초기 화면과 소수점 1자리 원자료 화면을 모두 남겼다.

## 초기 확보·검토 기록

- `old_oecd_overlap_2022_2023.csv`: 기존 보존 OECD 2.0 원자료에서 추출한 2022·2023년 17시도 × 산업 10개와 전체 합계의 374행. 단위는 명(PS, UNIT_MULT=0)이다. 신규 자료가 아니다.
- `old_schema_profile.json`: 기존 원자료 SHA-256, 차원, 시계열 범위, 중첩검산 대기 사항.
- `oecd_latest_acquisition_attempt.json`: 초기 공식 OECD 2.4 탐색 화면과 CSV 요청 실패 기록. 이후 성공한 직접 공식 URI 요청의 기록은 `oecd_latest_exact_download.json`이다.

한국 원출처 표는 KOSIS `DT_1ES3B05S`(구분류)이다. OECD 출처목록의 October 기재와 일부 기존 수치가 충돌함을 실제 수치 대조로 확인했다. 단일 연간 라벨만으로 조사월을 확정하지 않는다.

KSIC 제11차 개정은 공식 보도자료상 2024년 하반기 공표부터 반영되며, 이전 기간의 소급보정도 있으므로 구빈티지 2023년과 신빈티지 2024·2025년을 임의로 이어 붙이지 않는다. 단위 변환과 산업 묶음은 공식 원코드의 대응을 기록한 뒤 수행한다. 확보하지 못한 값은 보간·대체·추정하지 않는다.
