# 04. SEO Baseline Reconfirmation & Priority 0 Implementation

## Baseline 재확인(주어진 KnownSearchBaseline 대비 실측 차이)

과제에 주어진 `KnownSearchBaseline`을 그대로 믿지 않고 clean clone에서
실제 파일을 직접 열어 재확인했다(중복 전수조사는 안 하되, 구현 직전
변경 여부 재확인은 원칙대로 수행).

| 항목 | 주어진 Baseline | 실측 결과(2026-07-30, origin/main 1a32e08) |
|---|---|---|
| robots.txt | 전체 허용 | 확인, 변경 없음(`Allow: /`, sitemap 링크 있음) |
| sitemap.xml URL 수 | 3개 | 확인, 3개(`/`, `/markets.html`, `/privacy.html`) |
| privacy.html | noindex인데 sitemap 포함 | **확인** — `<meta name="robots" content="noindex">` 있음에도 sitemap에 포함돼 있었음(수정함, 아래 참고) |
| favicon.ico | 404 | **확인** — 파일 자체가 없고 `<link rel="icon">` 태그도 전무(수정함) |
| 루트 메타데이터 | 브랜드/카테고리 검색 발견성 fail | **부분 불일치** — title/description/canonical/OG/Twitter/JSON-LD(WebSite)가 이미 최근 커밋("feat: update social sharing metadata for OG v2")으로 추가돼 있었음. 다만 Organization schema는 없었고, 독립 크롤링 가능한 콘텐츠 페이지가 전무했던 것은 baseline과 일치 |
| markets.html 메타데이터 | 부족 | 확인, 미수정(CLAUDE.md 보호 대상 — 이번 프로젝트 명시적 승인 없이 미접촉) |
| 검색 가능한 독립 페이지 | 0개 | 확인, 0개였음(전부 `#hash` 라우팅) |

## Priority 0 구현 결과

| 항목 | 상태 | 비고 |
|---|---|---|
| favicon.ico/16x16/32x32/apple-touch-icon/android-chrome 192·512 | ✅ 신규 생성 | PIL로 브랜드 토큰(다크 네이비+골드) 기반 심플 레터마크 생성 — 정식 로고 디자인은 아님, 추후 실제 로고로 교체 권장 |
| site.webmanifest | ✅ 신규 | PWA 최소 매니페스트 |
| index.html `<head>` | ✅ favicon/manifest/RSS alternate link + Organization JSON-LD 추가 | live-dot/demo-banner **로직은 무변경**(head 메타만 추가), 실브라우저 콘솔 에러 0건·기존 기능 정상 확인 |
| sitemap.xml | ✅ 수정 | noindex인 `privacy.html` 제거, `/about/`·`/methodology/` 추가 |
| 404.html | ✅ 신규 | noindex, 브랜드 일관 디자인, 홈 링크 |
| feed.xml(RSS) | ✅ 신규, 단일 항목 | **알려진 한계**: 정적 파일이라 자동 갱신 안 됨(daily.yml이 매일 이 파일을 재생성하도록 만드는 것은 파이프라인 저장소 쪽 작업 — 이번 웹 프로젝트 스코프 밖, DeferredItems 참고) |
| /about/ | ✅ 신규 정적 페이지 | index.html `#view-about`의 실제 카피(THE PROBLEM 3항목 + 3C) 재사용, 고유 title/description/canonical/OG/AboutPage+BreadcrumbList JSON-LD |
| /methodology/ | ✅ 신규 정적 페이지 | 데이터 수집/시장온도/MOO:Q/MOO:CHECK/LLM 정정원칙을 기존 문서(CLAUDE.md) 기준 정확하게 설명, 지어낸 내용 없음 |
| markets.html 메타데이터 개선 | ❌ 미착수(의도적) | CLAUDE.md "절대 건드리지 말 것" 목록에 파일 전체가 있어 이번 태스크의 일반적 SEO 지시만으로는 건드리지 않음 — 사용자의 명시적 승인 필요 |
| /today/, /issues/, /questions/, /temperature/, /monthly/ | ❌ 미착수(의도적) | 실제 아카이브 데이터 계약(Stage 3)·MOO:Q 원장 뷰·월간 리포트(Stage 6)가 아직 없어 "실제 데이터를 가진 고유 페이지"라는 §6-2 요구를 지금 채우면 가짜 콘텐츠가 됨 — 데이터 계약이 만들어진 뒤 진행 |
| Google/Naver 실제 제출 | ❌ 미착수(도구 제약) | Search Console/네이버 서치어드바이저 API·CLI 접근 권한 없음 — 아래 수동 체크리스트로 대체 |

## Archive/IA 방향(PRODUCT_ARCHIVE_IA_AUDIT, 문서만 — 구현은 다음 단계)

Stage 3(아카이브 전략자산화)에서 실제로 만들어야 할 데이터 객체는
과제 §7에 정의된 대로: `DailyIssue`/`MarketSnapshot`/
`TemperatureObservation`/`QuestionRecord`/`CheckResult`/`MarketEvent`/
`EvidenceSource`/`MonthlyReport`/`MethodVersion`/`CorrectionRecord`.
이 중 `TemperatureObservation`(marketTemperature)과 `QuestionRecord`/
`CheckResult`(claims)는 **이미 daily-briefing의 `history.py`/
`claims_store.json`에 원시 데이터가 존재**(2026-07-30 targeted-final-
release 라운드에서 `history.py`가 marketTemperature 저장을 새로 시작함)
— 완전히 새로 설계할 필요 없이 기존 저장 포맷을 웹에 노출하는 API/
정적 JSON 내보내기 계층만 추가하면 됨. `MarketSnapshot`도
`data/history/*.json`의 indicators 필드로 이미 존재. 반면 `MarketEvent`
(변곡점)·`MonthlyReport`·`CorrectionRecord`(정정 이력)는 신규 설계가
필요 — 다음 단계 착수 시 이 문서를 출발점으로 사용.

## DeferredItems(P2, 다음 단계로 명시 이월)

1. feed.xml 자동 갱신 파이프라인 연결(daily.yml 쪽 작업 필요).
2. markets.html 메타데이터 개선 — 사용자 명시 승인 필요.
3. /today/, /issues/, /questions/, /temperature/, /monthly/ — Stage 3/6
   데이터 계약 완성 후 진행.
4. Google Search Console/네이버 서치어드바이저 실제 제출 — 수동
   체크리스트(별도 문서) 참고, 사용자 실행 필요.
5. Lighthouse 정량 성능 측정 — 도구 미설치, 실브라우저 콘솔/렌더
   체크로 대체됨.
6. favicon은 임시 레터마크 — 정식 로고 확정 시 교체 권장.
