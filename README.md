# 5극 3특 지역고용 의사결정지원서비스의 설계와 기술평가

논문의 분석과 서비스 기술시험을 재현하기 위한 코드·자료·결과 저장소이다.

- 저장소: https://github.com/thinkpa81/academic-papers
- 공개본 기준일: **2026-10-27**, `261027_v4` 최종 원고 대응본
- 연구 단위: 시도 × 산업 × 결과연도
- 주요 결과의 단위: 로그포인트

## 빠른 시작

Python **3.12**에서 저장소를 내려받은 뒤 다음 명령을 실행한다. 모든 파일은 확보 당시의 통계 자료를 포함하므로 논문 재현을 위한 별도 다운로드나 API 키가 필요하지 않다.

```bash
git clone https://github.com/thinkpa81/academic-papers.git
cd academic-papers
python -m venv .venv
```

가상환경을 활성화한다. Windows PowerShell에서는 `.venv\Scripts\Activate.ps1`, macOS/Linux에서는 `source .venv/bin/activate`를 사용한다.

```bash
python -m pip install -r requirements.txt
python verify_package.py
python code/verify_results.py
python code/audit_transfer_results.py --source results/transfer_evaluation
python -m unittest discover -s tests -v
python code/run_all.py --out rerun_20261027
```

`run_all.py`는 새 출력 폴더에 9개 단계를 순서대로 실행한다. 기존 폴더는 덮어쓰지 않는다. 각 단계의 실행 기록과 성공·실패 상태는 출력 폴더의 `run_summary.json`에 남는다. 실패한 단계의 상세 기록은 같은 이름의 `.log` 파일에서 확인한다. CPU 단일 스레드와 고정 난수 시드를 사용한다. 운영체제와 수치 라이브러리에 따라 미세한 부동소수점 차이는 생길 수 있다.

| 단계 | 계산 및 검증 내용 |
|---|---|
| `forecast_replay` | KOSIS 확보본 정규화, 표본 재구성, 릿지·AR(1) 재적합과 성능 비교 |
| `service_replay` | 선행 서비스 구현의 정상·오류 사례 재실행; 발견된 실패도 보존 |
| `model_swap_replay` | 모형 교체 시 예측·설명·검증 근거의 일관성 시험 |
| `preserved_audit` | OECD 원계열, 2024년 모형 고정 평가, 통합지역 결과의 독립 검산 |
| `local_fallback` | 검증자료에서 고정한 G2·G3 대체 규칙의 평가 |
| `benchmark` | 38개 후보의 고정분할 및 6개 확장창 재학습·선정·평가 |
| `diagnostics` | 1,000회 지역 블록 재선정, 지역 제외 및 표본 포함범위 분석 |
| `registered_service` | 자료에서 재적합한 참조 기록과 1,006개 합성 사례의 대조 |
| `transfer_evaluation` | 직접 구현·Pandera의 동일 정보 비교 및 미국 공개계열 적용 |

특정 단계만 실행할 때는 예를 들어 `python code/run_all.py --out rerun_service --jobs registered_service`를 사용한다.

## 파일 구성

| 경로 | 내용 |
|---|---|
| `code/` | 현재 분석, 등록 근거 검사, 그림 및 현장평가 계획의 실행 코드 |
| `support/` | 실행에 필요한 원계열·비교 구현·고정 입력·시험 명세 |
| `raw/` | KOSIS·OECD 확보본, 조회조건, 확보일, 기관 출처 |
| `results/` | 정밀 수치, 예측값, 선정 기록, 사례별 시험 결과 |
| `results/paper_tables/` | 논문에 표시한 24개 표와 번호·제목 목록 |
| `figures/` | 논문에 수록한 4개 그림과 재작성에 필요한 입력 |
| `field_study/` | 과업, 교차배정, 채점기준, 빈 응답양식 |
| `tests/` | 손상된 입력의 차단, 결과 보존, 실행 실패 기록의 회귀 테스트 |
| `PAPER_OUTPUT_MAP.md` | 논문 표·그림·부록과 계산 결과의 대응 |
| `DATA_SOURCES.md` | 자료 확보 및 이용조건 |
| `TRANSFER_EVALUATION.md` | 공통 요건 비교·외부자료 적용의 설계, 결과 및 한계 |
| `REPRODUCIBILITY.md` | 공개본 검증 결과와 보완분석 실행 방법 |
| `manifest_sha256.json` | 배포 파일별 바이트 수와 SHA-256 |

`support/`의 내부 버전명은 비교한 분석과 서비스 구현의 구분을 보존한다. 재현에 쓰이는 의존자료를 선별했으며, 이전 원고·편집 보고서·심사 대응문서는 포함하지 않았다. 제출용 논문 DOCX는 별도로 관리한다.

## 표와 그림

표 CSV는 논문의 반올림된 표시값이다. 통계 계산에는 각 분석 폴더의 정밀 수치를 사용한다. 다음 명령은 4개 그림을 PNG/PDF/SVG로 다시 작성한다. `paper_figure_*.png`는 논문에 실제 삽입한 이미지이며, 재작성 파일과 구분하여 보존한다.

```bash
python code/redraw_figures.py --out generated_figures
```

## 결과의 해석 범위

주분석의 학습·검증·평가 표본은 각각 558·463·428개이다. 추가 후보군과 재선정 분석은 기존 결과를 확인한 뒤 수행한 민감도 분석이며, 새로운 독립 평가자료를 확보한 실험은 아니다. 재선정의 후보군은 사전에 지정한 선형 계열 17개로, 전체 38개 후보의 반복 재학습과 구분한다.

주요 고정분할 성능 차이의 신뢰구간은 0을 포함한다. 서비스 시험은 합성 사례를 사용한 내부 기술시험이다. **현장 참여자와 실제 응답은 0건**이며, 배정표 144행은 실시 계획이다. 수집 시점의 개정 통계는 과거 공표 시점의 자료 빈티지와 구분한다. 세부 가정과 확인된 실패 사례는 각 분석의 명세 및 결과에 보존하였다.

자료 인용과 코드 이용조건은 [DATA_SOURCES.md](DATA_SOURCES.md)와 [PUBLICATION_NOTES.md](PUBLICATION_NOTES.md)를 따른다. 논문 인용 시 저장소 URL과 사용한 커밋 해시를 함께 기록한다.

추가 비교에서는 지역고용 예측 272개와 미국 거시계열 예측 234개를 이용하였다. 동일 요건·참조정보의 직접 구현과 Pandera는 7,590개 입력에서 판정이 일치하였다. 외부자료 적용도 연구진이 수행한 기술시험이다. 독립 평가자의 검증 및 사용자 효과와 구분한다. 상세 결과와 참조자료 동시 변경의 실패 경계는 `TRANSFER_EVALUATION.md`에 제시하였다.
