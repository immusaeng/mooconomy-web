# Stitch 뉴스레터 모바일웹 디자인 워크플로

이 문서는 Gate 0~9 전체 흐름을 정의한다. **이번 작업(2026-07-22, 워크스페이스
준비 라운드)은 Gate 1 준비까지만 수행한다. Gate 2 이상은 시작하지 않는다.**

## Gate 0 — Rollback Stabilized
- 현재 상태: **Conditional Complete**(사용자 확정)
- 테스트: 201개, failures 0, errors 0, unexpected skips 0
- claims_store 영속성 P0는 별도 세션으로 이관(`daily-briefing/docs/issues/P0-claims-store-persistence.md`)
- daily-briefing HEAD: `a60fa52`(2026-07-22 검증 시점)

## Gate 1 — Stitch Input Ready ← **이번 라운드는 여기까지**
- 기존 뉴스레터 구조 확인 — 완료(`/tmp/mooconomy-newsletter-stitch-context/current-template-structure.md`)
- 디자인 계약 확인 — 초안 작성 완료(`design/newsletter/contracts/newsletter-mobile-design-contract.md`,
  색상 토큰 불일치 발견 및 확인 요청 포함)
- 데이터 계약 확인 — 완료(`design/newsletter/contracts/newsletter-data-contract.md`)
- 390px/320px 기준 자료 확보 — **미완료**(사용자 제공 대기)

## Gate 2 — Stitch 390 Candidate
- 사용자가 Stitch에서 생성
- Claude Code는 구현하지 않고 구조와 데이터 가능성만 점검
  (`newsletter-content-inventory.md`의 "브라우저웹 차용 가능 여부" 갱신)

## Gate 3 — Stitch 320 Candidate
- 320px 축소 화면 검증
- 수평 스크롤 및 clipping 점검

## Gate 4 — Browser Preview
- `preview/newsletter-mobile/`에 독립 구현
- `latest.html` 변경 금지

## Gate 5 — Browser Approval
- 사용자가 실제 모바일 브라우저에서 승인

## Gate 6 — latest.html Candidate
- 백업 후 `latest.html`만 후보로 갱신
- 이메일 발송 없음

## Gate 7 — Email Translation
- table + inline CSS로 별도 변환(`design/newsletter/contracts/email-translation-boundaries.md`
  원칙 적용 — Stitch HTML을 그대로 복사하지 않음)

## Gate 8 — Test_Immusaeng
- 정확히 한 명에게 1회 테스트
- 사용자 명시적 승인 필요
- daily-briefing `.claude/skills/newsletter-release-gate/SKILL.md`의
  10개 게이트를 통과해야 함

## Gate 9 — Production Approval
- 운영 발송은 별도 명시적 승인 후에만 가능

---

**이번 작업 범위: Gate 1 준비까지.** Gate 2 이상은 사용자가 Stitch 자료를
제공하고 명시적으로 다음 단계를 지시할 때 시작한다.
