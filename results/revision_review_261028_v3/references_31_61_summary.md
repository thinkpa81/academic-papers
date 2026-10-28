# 참고문헌 31-61 검증 결과

검증일: 2026-10-28 (한국시간). 총31건의 실재와 식별자를 확인하였다. 실재 확인과 전문의 자유로운 열람 가능성은 구분하였다. 일부 출판사 링크는403·브라우저 확인·동적 앱 화면을 반환하므로 모든 링크에서 전문이 바로 열린다고 단정할 수 없다.

| 번호 | 실재 | 접근 상태 | 본문 인용 검토 |
|---|---|---|---|
| [31] | 확인 | metadata_abstract_accessible_fulltext_not_verified | supported_for_stated_scope |
| [32] | 확인 | primary_pdf_accessible | supported_for_stated_scope |
| [33] | 확인 | registry_metadata_verified_publisher_content_unreadable | supported_with_precision_revision |
| [34] | 확인 | publisher_indexed_abstract_live_gateway_unavailable | supported_with_precision_revision |
| [35] | 확인 | open_access_declared_indexed_text_live_challenge | supported_for_stated_scope |
| [36] | 확인 | official_metadata_abstract_accessible_fulltext_restricted | supported_for_stated_scope |
| [37] | 확인 | publisher_abstract_indexed_fulltext_restricted | supported_for_stated_scope |
| [38] | 확인 | publisher_indexed_abstract_live_gateway_unavailable | supported_for_stated_scope |
| [39] | 확인 | author_institution_text_accessible_publisher_declares_free_access | supported_for_stated_scope |
| [40] | 확인 | fulltext_accessible | supported_for_stated_scope |
| [41] | 확인 | official_metadata_indexed_dynamic_app_historical_snapshot_retained | supported_for_stated_scope |
| [42] | 확인 | official_metadata_indexed_dynamic_app_historical_snapshot_retained | supported_for_stated_scope |
| [43] | 확인 | publisher_abstract_accessible_fulltext_restricted | supported_for_stated_scope |
| [44] | 확인 | official_metadata_abstract_accessible | supported_for_stated_scope |
| [45] | 확인 | open_access_declared_publisher_indexed_author_page | supported_for_stated_scope |
| [46] | 확인 | publisher_free_access_text_available | supported_for_stated_scope |
| [47] | 확인 | versioned_official_documentation_accessible | supported_for_stated_scope |
| [48] | 확인 | versioned_official_documentation_accessible | supported_for_stated_scope |
| [49] | 확인 | publisher_indexed_abstract_live_403 | supported_for_stated_scope |
| [50] | 확인 | official_documentation_accessible_dynamic_version | supported_for_stated_scope |
| [51] | 확인 | official_documentation_accessible | supported_for_stated_scope |
| [52] | 확인 | versioned_official_documentation_accessible | supported_for_stated_scope |
| [53] | 확인 | official_metadata_abstract_accessible | supported_for_stated_scope |
| [54] | 확인 | official_metadata_abstract_accessible | supported_for_stated_scope |
| [55] | 확인 | author_accepted_manuscript_available_publisher_live_403 | supported_for_stated_scope |
| [56] | 확인 | official_fulltext_accessible | supported_for_stated_scope |
| [57] | 확인 | official_fulltext_accessible | supported_for_stated_scope |
| [58] | 확인 | publisher_abstract_and_author_fulltext_accessible | supported_for_stated_scope |
| [59] | 확인 | versioned_official_documentation_accessible | supported_for_stated_scope |
| [60] | 확인 | versioned_official_documentation_accessible | supported_with_precision_revision |
| [61] | 확인 | official_documentation_and_pinned_source_accessible | supported_for_stated_scope |

## 반영 권고

- 문단125, 참고문헌[34]: 예측오차 지표는 업무목적과 자료의 특성에 맞게 선택해야 한다[34]. 이에 본 연구에서는 큰 오차와 고용규모 가중 오차를 함께 검토하였다. 문헌의 일반적 지표 선택 논의와 연구자의 고용규모 가중 평가 선택을 구분한다.
- 문단62, 참고문헌[33]: 후버 회귀모형(Huber regression)[33,48] 1964년 원논문은 강건 위치모수 추정의 기초이며 실제 규제 회귀 구현은 scikit-learn 공식 문서[48]가 직접 근거이다.
- 문단388, 참고문헌[60]: 형식 조건은 JSON Schema Draft 2020-12의 스키마 검사와 비유한 수치를 허용하지 않는 JSON 직렬화 검사를 결합하여 필수 항목·자료형·수치 범위·해시 형식을 확인하였다[60]. code/evidence_contract.py의 validate_structure는 canonical(allow_nan=False)과 Draft202012Validator를 함께 사용한다.

## 서지와 링크 정비

- [31] 원래 인쇄본과 JSTOR 호 목차의75-105쪽을 유지한다. 새 MISQ/Crossref 메타데이터의75-106쪽 불일치는 감사 기록에 보존하였다.
- [37] 저자 기관에서 확인되는 Reggiani 표기를 유지한다. 출판사 메타데이터의 Reggianni 표기는 이를 자동 교체할 근거로 삼지 않았다.
- [40] 저자의 공식 인용 지침에서2025년제3판을 확인했다.
- [41][42] 데이터플로와 현재 메타데이터는 확인하였지만9월 확보 판본은 보존 요청·응답·해시 기록을 근거로 삼는다.
- [50] 현재 stable 문서는3.4.2, 코드 사용버전은3.4.1이다. 둘을 구분하여 기록하며 실행환경 버전을 바꾸지 않는다.
- [52] 실행환경과 같은4.7.0의 고정 문서 URL로 교체할 수 있다.
- [58] 최초 출판연도2020을 유지하고1-7쪽을 보충한다. Wiley 자동 인용 위젯의2026은 최초 출판연도로 채택하지 않는다.
- 실제 재확인한 온라인 문헌의 확인일을2026.10.28로 갱신할 수 있다. 역사적 원자료 확보일은 변경하지 않는다.

세부 URL, 근거, 문단별 연결, 직접 HTTP 응답과 Crossref 등록정보는 references_31_61.json 및 인접 crossref/http_checks 파일에 기록하였다.
