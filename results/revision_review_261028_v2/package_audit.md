# 재현패키지와 공개 저장소 검증

검증일은 2026년 10월 28일이다. 공개 기준은 `thinkpa81/academic-papers`의 커밋 `e125b2791b955483878439664bc73e5b6cbb88a0`이며, 이번 보완 파일을 해당 커밋에 추가했다는 뜻은 아니다.

## 공개 위치와 기록의 의미

GitHub 연결을 통해 기준 커밋과 전체 재귀 트리를 조회하였다. 트리는 생략 없이 550개 항목과 439개 파일을 반환하였다. 아래 파일들은 커밋별 경로 조회로 실재를 확인하였다.

| 경로 | 내용과 해석 |
| --- | --- |
| `field_study/protocol.md` | 실무자 8명·16과업·표/카드 두 조건의 예비평가 계획과 실행 절차 |
| `field_study/preparation_status.json` | 실제 참여자 0명, 실제 관측 0건, 계획 배정 128행 |
| `field_study/responses_EMPTY.csv` | 헤더만 있는 빈 응답양식. 분석 결과가 아님 |
| `code/prepare_field_study.py` 및 `code/pilot_materials.py` | 과업과 계획자료 생성 |
| `code/collect_field_study.py` | 실제 참여자를 대상으로 사용할 로컬 수집 프로그램 |
| `code/analyze_field_study.py` 및 `code/pilot_analysis.py` | 참여자별 비교 분석. 빈 양식에서는 효과를 추정하지 않음 |
| `results/field_study_status/status.json` | `status=not_evaluated`, `human_participants=0`, `observations=0`, `effects_estimated=false` |
| `results/transfer_evaluation/protocol_before_execution.json` | 추가 기술시험의 명세. 내부 실행 전 기록이며 독립 사전등록은 아님 |
| `results/transfer_evaluation/cases_before_execution.json.gz` | 기술시험 입력 7,590개를 담은 JSON 압축본 |
| `results/transfer_evaluation/reference_context.json.gz` | 호출자 측 등록 참조정보의 JSON 압축본 |
| `results/transfer_evaluation/case_results.csv.gz` | 7,590개 입력 × 4개 구현조건의 판정 30,360행 |
| `results/transfer_evaluation/trust_boundary_results.csv` | 제출정보와 참조정보를 동시에 변경한 별도 506개 사례의 판정 |

실제 파일 링크의 형식은 `https://github.com/thinkpa81/academic-papers/blob/e125b2791b955483878439664bc73e5b6cbb88a0/` 뒤에 위 상대경로를 연결한다. 압축파일은 웹 미리보기가 제한될 수 있으므로 내려받아 gzip으로 해제한다. `cases_before_execution.json.gz`와 `reference_context.json.gz`를 해제한 바이트의 SHA-256은 `execution_start.json`의 보존 해시와 일치했다. 따라서 두 파일은 원내용을 유지하는 압축본이라는 설명을 직접 확인하였다. `case_results.csv.gz`도 정상적으로 해제·파싱되며 기록 수와 판정 합계를 검산하였다.

공개 파일을 단순히 `field_study 및 code`라고 쓰는 것은 경로가 넓다. 부록에는 `field_study/protocol.md`, 수집·분석 코드 및 상태 파일의 정확한 경로를 기재하는 편이 재현에 유용하다. 본문에서는 `현장평가는 아직 실시하지 않았으며, 실제 참여자와 관측자료는 없다. 빈 응답양식에 대한 분석 코드는 미실시 상태(not_evaluated)를 반환한다`로 정리할 수 있다. `관측행은 0`보다 `실제 관측자료는 없다` 또는 `관측 건수는 0건이다`가 자연스럽다.

## SHA-512 추가의 처리

SHA-512를 파일 무결성 확인에 추가할 수 있다. 다만 기존 서비스의 `source_sha256`, `model_sha256`, `input_sha256`, 검토근거 해시 및 64자리 SHA-256 스키마를 일괄 치환하면 기존 고정 시험자료와 연결이 끊어진다. 따라서 기존 출처·검토 연결의 SHA-256은 보존하고 배포 파일 목록에 SHA-512를 병기하였다.

새 코드 `code/add_hash_manifest.py`는 배포 파일별 크기·SHA-256·SHA-512를 생성하고 검증한다. 해시는 파일 동일성을 점검하는 값으로, 원기관 자료의 진위나 확보 시각을 인증하지 않는다. 과거 해시 명세를 현재 파일의 해시로 소급 수정하지 않는다.

최종 파일 편집이 끝난 후 패키지 루트에서 실행한다.

```bash
python code/add_hash_manifest.py --legacy-sha256
python code/add_hash_manifest.py --verify
python verify_package.py
```

첫 명령은 `manifest_sha256_sha512.json`과 기존 검사기와 호환되는 `manifest_sha256.json`을 작성한다. 두 루트 목록은 순환 해시를 피하기 위해 목록 대상에서 제외한다. 과거 목록은 별도 검증 이력으로 유지한다. 새 코드의 생성–검증 왕복 및 같은 크기의 바이트 변경 탐지는 임시 자료에서 확인했다.

## 수치 허용오차

`code/evidence_contract.py`의 `TOLERANCE = 1e-9`, `math.isclose(..., rel_tol=0.0, abs_tol=TOLERANCE)`와 `code/registered_guard.py`의 동일 조건을 확인하였다. 논문 표현은 `수치 일치 여부는 절대 허용오차 10⁻⁹와 상대 허용오차 0을 적용하여 판정하였다`가 명확하다. 이는 서비스의 수치 정합성 판정 기준이다. 결과 재현 대조의 별도 `10⁻¹⁰`과 혼동하지 않아야 한다.

## 이번에 실행한 검증

| 검증 | 결과 |
| --- | --- |
| 보존 결과 수치·표본·선정·시점·현장평가 상태 점검 | 653개 통과 |
| 기존 소프트웨어 테스트 | 12개 통과 |
| 그림 수치·집계 검증 | 97개 통과; `code/verify_figure_data.py` |
| 출처 복원 | 136개 파일 이전 ZIP과 바이트 일치; 주요 원자료 네 해시 일치 |
| 빈 응답양식 분석 | 미실시, 참여자 0명·관측 0건, 효과 미추정 |
| gzip 해제 후 실행 시점 해시 대조 | 입력·참조 JSON 두 파일 일치 |
| 기술시험 보존 판정 검산 | 직접 구현과 Pandera 7,590개 일치; 정상 1,518개 수용·결함 6,072개 차단 |
| 별도 참조 동시 변경 | 506개 모두 두 구현에서 통과 |
| 미국 3계열 × 2모형 예측 재계산 | 234개 검산; 최대 차이 4.6241×10⁻¹⁴ |

이번 검증은 보존 판정 대조와 미국 계열 예측의 별도 행렬 계산이다. Pandera 전체 기술시험이나 9단계 분석 전체를 새로 실행한 것은 아니다. 실행환경에는 Pandera·jsonschema가 없어 해당 원 검사기의 전체 재실행을 수행하지 않았으며, 보존 판정 검산을 그 재실행으로 표현하지 않는다.

근거 파일은 `result_verification.json`, `package_unit_tests.log`, `field_study_check/status.json`, `audit_preserved_transfer.py`와 `.json`이다.

## 공개 기준본과 이번 동봉본의 출처 복원

공개 트리와 입력 ZIP의 파일을 대조한 결과 공개 파일 439개 중 415개가 바이트 단위로 동일하고, 8개는 문서·목록·로그 편집 차이, 16개는 공개본에 정리된 추가 실행로그·원자료 해시였다. `field_study/protocol.md`의 실험설계는 동일하며 공개본에서는 과거 12명 계획을 대체했다는 문구를 삭제하였다. 세부 목록은 `github_package_comparison.json`에 있다.

기준 공개 커밋에는 KOSIS `DT_1ES3B05S`의 원자료·메타데이터, 2013–2025년 보도자료 13건의 공표일 목록, OECD 2.4 전체 응답 및 노동자료 원본이 없었다. 이번 `261028_v2` 동봉본에는 이전 재현패키지에서 찾은 출처 자료 136개를 `raw/supplementary_sources_261028_v2/`에 복원하였다. 136개 모두 이전 ZIP 보존 바이트와 일치한다. KOSIS J·S 및 OECD 2.4 고용·노동 원응답의 네 SHA-256 대조도 일치하였다. 검증 근거는 `reference_audit.json`과 복원 기록 `recovered_sources/summary.json`이다.

복원된 `source_release/release_calendar_H1_2013_2025.json`에는 13개 연도의 공표일과 공식 URL이 있다. 공식 웹 대조에서도 게시월이 모두 10월임을 확인하였다. 복원 자료에는 HTML과 PDF 텍스트 추출본·원파일 해시가 있으나 PDF 원본 파일 자체는 없다. 따라서 PDF 원본을 전부 동봉했다는 설명은 사용하지 않는다.

KOSIS S의 실제 추출 범위는 2022년 상·하반기와 2023·2024년 상반기이다. 2013–2024년 전기간 추출로 표현하지 않는다. 확보일은 독립 획득 타임스탬프가 아니라 보존 파일의 수정시각에 근거한 기록이다. OECD 2.4 고용 응답은 한국의 TL2·TL3를 포함한 광역조회, 노동 응답은 한국 17개 TL3·15–64세·성별전체·경제활동참가율과 실업률·2022년 이후 조건이므로 분석 부분집합과 원요청 범위를 구별한다.

공개 기준 커밋의 누락과 이번 동봉본의 복원 완료는 서로 다른 상태이다. 기존 커밋은 변경하지 않았으며 복원 자료의 공개 여부를 해당 커밋에 소급하지 않는다.

GitHub 조회는 읽기만 수행하였다. 이번 수정 코드·그림·원고가 기존 공개 커밋에 반영되었다고 기재해서는 안 된다.
