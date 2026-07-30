# 01. Repository & Deployment Inventory (읽기 전용 조사)

## 저장소 구조(재확인, 이미 CLAUDE.md에 기록된 사실)

- `immusaeng/daily-mooconomy`(파이프라인) — `daily-briefing` 작업 트리,
  `main` 로컬 HEAD `71add43`(다른 세션이 아직 안 올린 로컬 커밋 4개
  앞선 상태, dirty), origin `main`은 `8472109`(newsletter targeted-final-
  release 반영 완료). **이번 웹 프로젝트에서는 이 저장소를 전혀
  수정하지 않는다.**
- `immusaeng/mooconomy-web`(정적 사이트) — `daily-briefing/mooconomy-web`
  경로에 존재하지만 **서브모듈이 아니라 완전히 독립된 git 저장소**.
  로컬 main HEAD가 `dc9b51c`로 origin(`1a32e08`)보다 9커밋 뒤처져
  있었고(자동 daily.yml 티커 갱신 커밋 다수 + `feat: add robots and
  sitemap`/`chore: add Naver site verification file`/`feat: update
  social sharing metadata for OG v2`), 로컬 작업 트리도 dirty(다른
  세션의 뉴스레터 프리뷰/디자인 감사 관련 미완성 변경).

## 다른 세션 미완성 변경(건드리지 않음, 참고용 기록만)

`daily-briefing`(root): `.claude/skills/`의 기존 2개 스킬 수정 +
신규 4개 스킬 폴더(모두 uncommitted), `CLAUDE.md`/타이포 문서 수정.
`mooconomy-web`(nested): `preview/newsletter-mobile/` 신규 파일들,
`design/newsletter/` 감사 문서·Stitch 소스, `promo/og_banner.html` 등
— 전부 뉴스레터 디자인 관련 별도 작업으로 추정, 이번 웹 레지던시
프로젝트와 무관해 그대로 둠.

## 이번 작업 위치

위 두 트리 모두 무관한 미완성 변경으로 dirty해 충돌 위험이 있어(§2
안전 원칙), 완전히 별도인 신규 clean clone
`C:\Users\SS\OneDrive\Desktop\LLM작업\mooconomy-web-work`(origin/main
`1a32e08` 기준)에서 작업했다.

## 배포/트리거 지도

- `mooconomy-web`은 GitHub Pages(커스텀 도메인 `mooconomy.co.kr`,
  `CNAME` 파일 확인)로 정적 배포. 저장소 안에 자체 GitHub Actions
  workflow가 없다(daily.yml은 `daily-mooconomy` 저장소 소관 — 매일
  06:41 KST cron-job.org가 그 저장소의 workflow_dispatch를 호출하고,
  그 워크플로 마지막 단계가 `ticker.json`/`home.json`/`latest.html`
  등을 이 저장소에 별도로 커밋·푸시).
- 따라서 `mooconomy-web`에 대한 push는 뉴스레터 발송과 구조적으로
  무관 — website-only 배포 구조가 이미 기본값이다(재설계 불필요).
- GitHub Pages 설정 자체(Settings > Pages 소스 브랜치 등)는 웹
  UI에서만 확인 가능해 이번 조사에서 직접 확인하지 못함(읽기 전용
  파일 조사로 대체) — `CNAME` 파일 존재로 커스텀 도메인 연결은
  간접 확인됨.

## 현재 페이지/자산 인벤토리(핵심만)

`index.html`(SPA, 홈+About+Markets 뷰가 해시 라우팅으로 전환되는
단일 HTML, 인라인 `<style>` 724줄), `markets.html`(독립 페이지, 외부
Google Fonts+lucide+chart.js CDN 사용 — **CLAUDE.md 보호 대상, 이번
작업에서 미접촉**), `privacy.html`(noindex), `latest.html`(daily.yml이
매일 덮어쓰는 최신 뉴스레터 원문), `ticker.json`/`data/home.json`/
`data/signals.json`/`data/macro_history.json`/`data/calendar_results.json`/
`data/history/*.json`(daily.yml이 채우는 데이터, 이번 작업에서 소비만
하고 생성 로직은 미변경).

## 재사용 가능한 컴포넌트

- 다크 네이비(#0B1220)/골드(#F2C94C) 브랜드 토큰 — 뉴스레터 V2와 이미
  공유 확정된 값, 신규 `/about/`·`/methodology/`·`404.html` 페이지에
  그대로 재사용.
- `index.html`의 `#view-about` 콘텐츠(THE PROBLEM 3항목 + 3C 카드) —
  텍스트를 그대로 재사용해 독립 크롤링 가능한 `/about/`로 승격.
