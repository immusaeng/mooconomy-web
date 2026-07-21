# 이메일 변환 경계

> **원칙(최상단 명시)**: Stitch HTML을 실제 이메일 템플릿(daily-briefing의
> `templates/briefing.html`)에 직접 복사하지 않는다. 두 렌더러는 서로 다른
> 컴포넌트 구현을 갖는다 — 공유하는 것은 토큰·데이터 계약·카피·컴포넌트
> 의미뿐이다(daily-briefing `docs/adr/ADR-001-separate-web-and-email-renderers.md`
> 참고, 이 문서는 그 ADR을 mooconomy-web 쪽 작업자를 위해 다시 정리한 것).

## 브라우저 모바일웹(이 저장소의 `preview/newsletter-mobile/`, 향후 Stitch 구현체)

- 일반 CSS 사용 가능
- `@media` 쿼리 사용 가능(뷰포트 기반 반응형)
- 제한적인 Flex/Grid 사용 가능(브라우저는 지원하므로)
- JavaScript는 필요한 경우 **별도 승인 필요**(현재 이 저장소의 뉴스레터
  프리뷰 계획에는 JS 사용 계획이 없음 — 필요해지면 그 시점에 명시적으로 논의)
- 로컬 asset 사용 가능(이 저장소 내 이미지 등)

## 실제 이메일(daily-briefing `templates/briefing.html`)

- table 기반 레이아웃만
- inline CSS 필수(css_inline이 `<style>` 규칙을 각 요소의 `style=""`로
  인라인화하지만, 핵심 배경·글자색은 처음부터 inline+`bgcolor` 속성으로
  이중화해야 한다 — 2026-07-21 사고 원인이 바로 이 이중화 누락이었음)
- `bgcolor` fallback 필수(핵심 카드류: 시장 온도, MOO:Q 등)
- Flex/Grid **금지**(Outlook 등 주요 클라이언트 미지원)
- JavaScript **금지**
- 외부 폰트 의존 최소화(`@import`로 Pretendard를 시도하되, 실패해도
  레이아웃이 깨지지 않는 폰트 스택 폴백 필수 — 현재
  `'Pretendard','Malgun Gothic','Apple SD Gothic Neo',sans-serif` 스택 사용 중)
- 이메일 클라이언트별 fallback 필요(`<style>` 블록 전체가 제거되는 클라이언트
  존재를 가정 — daily-briefing
  `docs/release/newsletter-release-gates.md` 게이트 6/9 참고)

## 두 환경이 공유하는 것(반복 강조)

- 디자인 토큰(정확한 hex 값 — 단, 이번 요청의 Stitch 색상 지정값과 현재
  이메일 실값이 다르다는 점이
  `../contracts/newsletter-mobile-design-contract.md` 상단에 별도 명시돼
  있음, 확인 필요)
- canonical 데이터 계약(`marketTemperature`/`claims`/`connection` — 단,
  뉴스/리스크/캘린더/Daily3는 공유하지 않음,
  `../contracts/newsletter-data-contract.md` 참고)
- 실제 카피 문구(LLM/규칙템플릿이 만든 텍스트 — 단, 뉴스레터와 홈페이지가
  같은 개념이라도 서로 다른 LLM 호출로 만들어진 별도 텍스트인 경우가 많음)
- 컴포넌트 "의미"(예: 시장 온도 = 상태+핵심문장+근거, MOO:Q = 검증 가능한
  질문 1개)

## 공유하지 않는 것

- 마크업 구현 자체(Flex div vs table)
- CSS 클래스명(`.temp-badge`류 홈페이지 클래스를 이메일에 그대로 쓰지 않음)
- 미디어쿼리 유무(이메일은 있지만 제한적, 브라우저는 자유)
