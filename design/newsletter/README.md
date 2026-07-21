# design/newsletter/

## 폴더 목적
Daily MOO:conomy 뉴스레터의 "Stitch 모바일웹 디자인 단계" 준비를 위한 기준
자료·계약 문서를 보관한다. 이 폴더 자체는 **디자인을 구현하는 곳이 아니라
기준을 문서화하는 곳**이다.

## 입력 파일
- 사용자가 제공할 Stitch 원본(이미지/HTML) — `stitch/`
- 2026-07-20 정상 발행본 기준 자료(HTML/스크린샷, 있다면) — `baseline/july20/`
- 롤백 관련 근거(git 커밋, 이번 세션 조사 결과) — `baseline/rollback/`

## 출력 파일
- `contracts/*.md` — 디자인/데이터/콘텐츠/이메일 변환 경계 계약 문서
- `audits/*` — 향후 감사 결과(`/cross-platform-design-audit` 스킬 실행 결과 등)

## production 여부
아니오 — 이 폴더의 내용은 실제 `latest.html`, `index.html`, 뉴스레터 발송
HTML에 어떤 방식으로도 직접 연결되지 않는다.

## 사용자 승인 필요 여부
예 — Stitch 원본 파일 제공, 섹션별 KEEP/REDESIGN/REMOVED 확정, 각 Gate
통과는 전부 사용자 승인이 필요하다(`docs/newsletter/approval-gates.md` 참고).

## 금지 작업
- 이 폴더의 문서를 근거로 production 템플릿(daily-briefing의
  `templates/briefing.html`)을 직접 수정하는 것
- Stitch HTML을 이메일 템플릿에 그대로 복사하는 것(ADR-001)
- 실제 Stitch 파일이 없는 상태에서 가짜 이미지/HTML/JSON을 만들어 채우는 것

## 아직 없는 파일 목록
- `stitch/source/*`(Stitch 원본 HTML) — 사용자 제공 대기
- `stitch/screenshots/390/*`, `stitch/screenshots/320/*`,
  `stitch/screenshots/components/*` — 사용자 제공 대기
- `stitch/metadata/*` — Stitch 파일이 제공된 이후 작성
- `baseline/july20/*` — 2026-07-20 실제 발행본 HTML/스크린샷이 확보되면 추가
  (현재는 `docs/postmortems/2026-07-21-newsletter-rendering-regression.md`와
  daily-briefing 저장소의 git 커밋 `3c9124f`가 유일한 근거)
- `baseline/rollback/*` — 이번 세션 조사 결과 요약(아래 "다음 단계" 참고)
- `audits/*` — 아직 감사 실행 전

## 다음 단계
Gate 1(Stitch Input Ready) 준비 완료 후 사용자가 Stitch 자료를 제공하면
`stitch/` 하위에 저장하고 Gate 2로 진행한다(`docs/newsletter/stitch-workflow.md`
참고).
