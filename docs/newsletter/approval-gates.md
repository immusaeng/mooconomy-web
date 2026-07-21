# 승인 게이트 상세

각 Gate의 입력/검증 항목/완료 기준/중단 조건/승인 주체. 전체 흐름은
`stitch-workflow.md` 참고.

| Gate | 입력 | 검증 항목 | 완료 기준 | 중단 조건 | 승인 주체 |
|---|---|---|---|---|---|
| 0. Rollback Stabilized | daily-briefing 커밋 이력 | 테스트 결과, HEAD/origin 일치 | 201개 테스트 0 failures/0 errors/0 skips | 테스트 실패, HEAD 불일치 | 사용자(이미 확정) |
| 1. Stitch Input Ready | 현재 템플릿 구조, 계약 문서 | 구조·데이터 인벤토리 정확성 | 계약 문서 3종 + 콘텐츠 인벤토리 작성 완료 | 존재하지 않는 필드/파일을 있다고 기록 | 사용자(이번 보고 검토) |
| 2. Stitch 390 Candidate | 사용자 제공 Stitch 390px 자료 | 구조가 데이터 계약과 호환되는지(신규 필드 요구 여부) | Stitch 후보가 `stitch/` 하위에 저장됨 | 자료 미제공, 데이터 계약과 근본적으로 불일치 | 사용자 제공 + Claude 점검 |
| 3. Stitch 320 Candidate | 390px 승인 후 320px 자료 | 수평 스크롤·clipping 유무 | 320px 자료 저장 + 점검 리포트 | 320px에서 핵심 콘텐츠 잘림 | 사용자 제공 + Claude 점검 |
| 4. Browser Preview | 승인된 Stitch 자료 | `preview/newsletter-mobile/` 구현이 계약 문서 준수하는지 | 독립 프리뷰 페이지 동작 | latest.html/index.html 연결 시도 | 사용자 승인 후 착수 |
| 5. Browser Approval | 프리뷰 페이지 | 실제 모바일 브라우저 육안 확인 | 사용자 승인 기록 | 미승인 | 사용자(필수, 자동화 불가) |
| 6. latest.html Candidate | 승인된 프리뷰 | 백업 존재 여부, 콘텐츠 정합성 | 백업 후 후보 갱신 | 백업 없이 진행 시도 | 사용자 승인 |
| 7. Email Translation | 승인된 브라우저 디자인 | table+inline CSS 변환, ADR-001 준수 | daily-briefing `newsletter-release-gate` 스킬 게이트 1~6 통과 | Stitch HTML 직접 복사 발견 | Claude 구현 + 사용자 리뷰 |
| 8. Test_Immusaeng | 변환된 이메일 HTML | 세그먼트 검증(정확히 1명), 콘텐츠 게이트 전체 | 테스트 발송 완료 + 사용자 Gmail 확인 | 세그먼트 검증 실패, 게이트 미통과 | 사용자(발송 전 명시적 승인 필수) |
| 9. Production Approval | Test_Immusaeng 승인 결과 | 운영 세그먼트 ID 확인, 전체 게이트 재확인 | 사용자의 명시적 "운영 발송 승인" | 미승인, 세그먼트 오지정 | 사용자(필수) |

## 공통 원칙
- 각 Gate는 순서대로만 진행한다 — 이전 Gate 미완료 상태에서 다음 Gate를
  시작하지 않는다.
- "완료 기준"이 충족되지 않으면 다음 Gate로 넘어가지 않고 현재 Gate에서 대기한다.
- "중단 조건"에 해당하면 자동으로 되돌리거나 수정하지 않고 Blocked로 보고한다.
