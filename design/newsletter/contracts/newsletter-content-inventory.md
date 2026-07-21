# 뉴스레터 콘텐츠 인벤토리(섹션별 현황)

daily-briefing HEAD `a60fa52`의 `templates/briefing.html` 실측 + 커밋
`3c9124f`(2026-07-20 발행 기준) 실측 대조.

## 상태 축 분리(2026-07-22 보정)

REMOVED/REDESIGN/BLOCKED를 하나의 상태 값으로 뭉뚱그리지 않고 5개 축으로
분리한다 — "디자인상 다시 넣고 싶은가"와 "지금 실제로 렌더링되는가"와
"production에 내보내도 되는가"는 서로 다른 질문이기 때문이다.

- **designStatus**: KEEP / REDESIGN / REDESIGN_OPTIONAL / REDESIGN_CONDITIONAL / OPTIONAL
- **currentRenderStatus**: RENDERED / REMOVED
- **dataStatus**: WIRED(배선됨, 값 유무 무관) / AVAILABLE_ONLY_WHEN_VALID_CLAIM_EXISTS / P0_PERSISTENCE_UNRESOLVED / N/A(정적 콘텐츠)
- **productionReleaseStatus**: RELEASED(이미 프로덕션에 있음) / BLOCKED_PENDING_APPROVAL
- **userApprovalRequired**: YES / NO

Stitch 후보 존재 여부는 별도 열로 유지(전부 UNKNOWN — 자료 미제공).

| 섹션 | designStatus | currentRenderStatus | dataStatus | productionReleaseStatus | userApprovalRequired | Stitch 후보 | 비고 |
|---|---|---|---|---|---|---|---|
| Header | KEEP | RENDERED | N/A | RELEASED | NO | UNKNOWN | 브랜드 자산 재사용 범위만 추후 확인 |
| 발행일 | KEEP | RENDERED | N/A | RELEASED | NO | UNKNOWN | `publishDate` 계산방식 불일치는 data-contract 문서 참고 |
| 오늘의 시장 온도 | KEEP | RENDERED | WIRED | RELEASED | NO(구조) / YES(시각 재설계 시) | UNKNOWN | `reasons`/`watchItems` 필드는 있으나 템플릿 미사용 |
| 핵심 지표 6개 | KEEP | RENDERED | WIRED | RELEASED | NO | UNKNOWN | home.json `indicators`(8개, 브렌트유 없음)와 목록 다름 |
| 오늘의 3줄 | KEEP | RENDERED | WIRED | RELEASED | NO | UNKNOWN | home.json `dailyThree`와 별도 LLM 소스 |
| MOO:Q | REDESIGN_CONDITIONAL | RENDERED(조건부) | AVAILABLE_ONLY_WHEN_VALID_CLAIM_EXISTS | RELEASED | YES | UNKNOWN | **빈 데이터에서 가짜 질문 생성 금지** |
| MOO:CHECK | REDESIGN_CONDITIONAL | RENDERED | P0_PERSISTENCE_UNRESOLVED | RELEASED | YES | UNKNOWN | **claims_store 문제가 해결된 것으로 표현 금지** — 실제로는 "확인 중" placeholder만 보일 가능성 높음 |
| 오늘의 연결고리 | REDESIGN | REMOVED | WIRED | BLOCKED_PENDING_APPROVAL | YES | UNKNOWN | 재도입 여부 자체가 승인 대상 |
| 오늘의 해석 | OPTIONAL | REMOVED | WIRED(`connection.summary`) | BLOCKED_PENDING_APPROVAL | — | UNKNOWN | 연결고리 하위 요소, 독립 승인 불필요(연결고리 결정에 종속) |
| 반대 시나리오 | OPTIONAL | REMOVED | WIRED(`connection.counterScenario`) | BLOCKED_PENDING_APPROVAL | — | UNKNOWN | 연결고리 하위 요소 |
| 일정 | KEEP | RENDERED | WIRED | RELEASED | NO | UNKNOWN | home.json `calendar`와 필드·구조 다름(`data.미국실적_필터`) |
| 뉴스 | KEEP | RENDERED | WIRED | RELEASED | NO | UNKNOWN | home.json `news`와 완전 별개 소스 |
| 리스크 | KEEP | RENDERED | WIRED | RELEASED | NO | UNKNOWN | home.json `risks`와 완전 별개 소스 |
| 대표 CTA | REDESIGN_OPTIONAL | REMOVED | N/A(정적 링크) | BLOCKED_PENDING_APPROVAL | YES | UNKNOWN | 연결고리 재도입과 함께 결정 |
| 구독/공유 CTA(footer) | KEEP | RENDERED | N/A(정적 링크) | RELEASED | NO | UNKNOWN | 대표 CTA(위 행)와 다른 항목 — 컴플라이언스 링크, 3c9124f엔 없었으나 2026-07-20 저녁 추가돼 유지 결정됨 |
| PART 구분 | KEEP | RENDERED | N/A | RELEASED | NO(시각 톤 변경 시 YES) | UNKNOWN | 이번 롤백에서 3c9124f 스타일 그대로 유지 |
| Footer(출처/서명) | KEEP | RENDERED | N/A | RELEASED | NO | UNKNOWN | |

## 확인되지 않은 항목
Stitch 후보 열 전체가 UNKNOWN — 사용자가 Stitch 자료를 제공하기 전까지는
채울 수 없다(가짜로 채우지 않음).

## 이번 보정에서 명시적으로 반영한 사용자 지시
- 오늘의 연결고리: designStatus=REDESIGN, currentRenderStatus=REMOVED,
  dataStatus=WIRED, productionReleaseStatus=BLOCKED_PENDING_APPROVAL,
  userApprovalRequired=YES
- 오늘의 해석 / 반대 시나리오: designStatus=OPTIONAL, currentRenderStatus=REMOVED,
  productionReleaseStatus=BLOCKED_PENDING_APPROVAL
- 대표 CTA: designStatus=REDESIGN_OPTIONAL, currentRenderStatus=REMOVED,
  productionReleaseStatus=BLOCKED_PENDING_APPROVAL
- MOO:Q: designStatus=REDESIGN_CONDITIONAL,
  dataStatus=AVAILABLE_ONLY_WHEN_VALID_CLAIM_EXISTS, 빈 데이터에서 가짜 질문
  생성 금지 원칙 명시
- MOO:CHECK: designStatus=REDESIGN_CONDITIONAL,
  dataStatus=P0_PERSISTENCE_UNRESOLVED, claims_store 문제 미해결 명시
