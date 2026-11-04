# 5극 3특 지역고용 의사결정지원서비스

「5극 3특 지역고용 의사결정지원서비스의 설계와 기술평가」의 분석 코드와 결과물이다. `261105` 공개본은 제공된 최종 HWP의 표·그림·분석 범위에 맞춰 구성했다. 현재 261105 HWP의 파일명과 SHA-256은 [CODE_RELEASE.json](CODE_RELEASE.json)에, 분석 기준 커밋과의 연결 및 표·그림 대조는 [원고 연결 기록](results/release_261105/manuscript_binding_261105.json)에 기록했다. 최초 추출에 사용한 261029 HWP의 식별정보와 당시 검증 기록도 보존한다.

| 자료 | 위치 |
| --- | --- |
| 실행 방법과 재적합 범위 | [REPRODUCIBILITY.md](REPRODUCIBILITY.md) |
| 논문 표·그림과 코드의 대응 | [PAPER_OUTPUT_MAP.md](PAPER_OUTPUT_MAP.md) |
| 원자료 확보본과 출처 | [DATA_SOURCES.md](DATA_SOURCES.md) |
| 이번 재실행·검증 기록 | [results/release_261105/](results/release_261105/) |
| 표·공표일 목록 | [results/paper_tables/](results/paper_tables/) |
| 기준 그림 4개 | [figures/](figures/) |
| 현장평가 계획·빈 양식 | [field_study/](field_study/) |

## 실행

Python 3.12 환경에서 저장소 루트를 작업 폴더로 사용한다.

```bash
python -m pip install -r requirements.txt
python code/add_hash_manifest.py --verify
python verify_package.py
python code/verify_results.py
python -m unittest discover -s tests -v
python code/run_all.py --out ../rerun_261105
python code/v3_independent_audit.py --out ../independent_check_261105.json --replay ../rerun_261105
```

실행기는 기존 출력 폴더를 덮어쓰지 않는다. 단계별 로그, 종료 상태, 설치 버전과 실행 시작 시 코드·입력 목록의 SHA-256을 남긴다. 독립 검사는 보존 CSV 전체를 기준으로 재실행 결과를 대조하며 누락된 파일을 실패로 처리한다.

## 검증 결과

2026년 11월 5일 9단계 재실행에서 CSV 157개·132,063행이 보존 결과와 허용오차 내 일치했다. 독립 검사 27개, 보존 결과 검사 653개, 단위시험 25개, 그림 수치 97개·표기 18개가 통과했다. [검증 범위와 기록](results/release_261105/AUDIT_SCOPE.md)을 따른다.

추가 확인에서 현재 261105 HWP의 표 25개·836셀은 공백·마이너스 정규화 후 공개 CSV와 일치했고, 삽입 그림 4개는 공개 PNG와 바이트가 같았다. 누락된 정합화 분석 `protocol.md`를 복구한 뒤 통합지역 분석을 새로 적합하여 CSV 18개·6,596행의 일치를 확인했다. 복구 문서는 현재 코드와 보존 기록에 근거한 재실행 명세이며, 과거 프로토콜 원문과 동일한 파일을 뜻하지 않는다. [복구 및 재적합 기록](results/release_261105/protocol_restoration/verification.json)에 새 해시와 과거 해시를 구분했다.

## 재현 범위

9단계는 예측 재분석, 서비스 결함시험, 모형 교체시험, 보존 모형 검산, 지역 대체 규칙, 후보모형 비교, 진단, 등록 근거 대조와 외부자료 공통 요건 시험으로 구성한다. `preserved_audit`는 보존 모형·입력·예측의 검산이며 모든 보완모형을 새로 적합하는 단계가 아니다. 선택 재적합 명령은 실행 안내에 구분했다.

현장평가 자료는 실무자 8명·16과업·두 표시조건의 계획과 빈 양식이다. 실제 참여자와 관측값은 0건이다. 기술시험의 합성 사례와 실제 사용자 평가 결과를 구분한다.

현재 `main`에는 분석에 필요한 코드·입력·보존모형·결과·표·그림·검증 기록을 둔다. 이전 DOCX 원고, 문서 전용 빌더와 과거 편집 검토자료는 정리했다. 과거 이름이 남은 `support/` 자료는 실행 의존성 또는 원결과 확인에 필요하다. 상세 공개 범위는 [PUBLICATION_NOTES.md](PUBLICATION_NOTES.md)를 따른다.

논문에서 인용하는 공개본은 고정된 커밋 링크로 식별할 수 있다. 전체 커밋 SHA와 최신 원고 해시의 연결은 원고 연결 기록에서 확인한다. 해당 공개본을 체크아웃한 뒤 `git rev-parse HEAD`로 커밋을 확인할 수 있다. 루트의 SHA-256·SHA-512 배포목록은 파일 동일성을 확인하며 원자료의 진위나 과거 확보시점을 인증하지 않는다.
