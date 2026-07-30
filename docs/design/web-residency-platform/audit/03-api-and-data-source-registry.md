# 03. API & Data Source Registry (읽기 전용, daily-briefing 파이프라인 재확인)

값·키·실제 recipient는 기록하지 않음 — 환경변수 이름과 출처만 기록.

## TIER_1_PRIMARY_OFFICIAL

| Source | Fields | Env Var | Used In |
|---|---|---|---|
| 한국은행 ECOS | 기준금리, 소비자물가 YoY 등 국내 거시 | `ECOS_API_KEY` | 뉴스레터, home.json, methodology 설명 |
| 美 연준 FRED | DGS10/DGS2(장단기 금리차), USREC, BAMLH0A0HYM2(하이일드 스프레드), CPI/PCE/실업률/기준금리 | `FRED_API_KEY` | 뉴스레터, signals.py(신호등), macro_history.json(대시보드) |
| 금융감독원 DART | 국내 공시·실적예고 | `DART_API_KEY` | 뉴스레터 캘린더/공시 |

## TIER_2_MARKET_PROVIDER

| Source | Fields | Env Var | Used In |
|---|---|---|---|
| FinanceDataReader | 코스피/코스닥/다우/나스닥/S&P500/닛케이/상해종합/원달러/WTI/브렌트유/금/VIX/미국채10년(^TNX)/달러인덱스 | 없음(무료, 키 불필요) | MAIN 6 METRICS, OVERNIGHT GLOBAL & MACRO 등 canonical snapshot 대부분 |
| 네이버 금융 | 국내 수급 보조 | 없음 | kr_market.py |
| Finnhub | 美 기업 실적(어닝 서프라이즈) | `FINNHUB_API_KEY` | 뉴스레터 캘린더 |

**알려진 이중 소스 이슈(BLOCKER로 이미 기록된 사실, 재확인만)**:
`data.글로벌.미국채10년`(home.json 04 카드, Yahoo `^TNX` 기반)과
`signals.py`의 경기침체 경보등(FRED `DGS10` 기반)이 서로 다른 소스 —
같은 날 두 값이 미세하게 다를 수 있음(SOL 인계조사에서 이미 발견,
methodology 페이지에는 이 자세한 내부 사정 대신 "공식·1차 데이터를
우선한다"는 원칙만 공개, 완전한 소스 통합은 이번 프로젝트 스코프 밖).

## TIER_3_NEWS_EVIDENCE

연합뉴스·한국경제·매일경제(국내 RSS), MarketWatch·CNBC·YahooFinance
(해외 RSS/HTML) — `collectors/news.py`. 수치 원천이 아니라 해석·맥락
근거로만 사용(뉴스레터 methodology 페이지에 이 구분 명시함).

## 운영 API

| Source | Purpose | Env Var |
|---|---|---|
| Resend | 뉴스레터 발송(Broadcast, 이번 프로젝트에서 전혀 호출하지 않음) | `RESEND_API_KEY`, `RESEND_SEGMENT_ID`, `MAIL_FROM`, `MAIL_TO` |
| Google Analytics 4 | 방문 분석, `index.html`에 이미 연결됨(측정 ID `G-ZXRTZK2KTN`) | 코드 내 하드코딩(공개 측정 ID, 민감정보 아님) |
| Google Search Console | 색인 상태(이번 세션 API 접근 불가, 수동 제출 대상) | — |
| 네이버 서치어드바이저 | 사이트 소유 확인 파일(`naver247522d1c5ebe86602c18a402c47be06.html`)이 이미 루트에 존재 — 소유 확인은 이미 완료된 상태로 추정, 실제 제출 상태는 웹 콘솔에서만 확인 가능 | — |

## API 실패 정책(뉴스레터 파이프라인 기존 원칙, 재확인)

값이 없으면 이전 값을 오늘 값처럼 재사용하지 않고 "데이터 없음"으로
표시(`_chg()`가 실패 시 `None` 반환 → 화면 필드 자체 숨김/"—" 표시).
발행 후 과거 스냅샷을 조용히 덮어쓰지 않음(claims 시스템의 `lockedAt`/
`baseline` 구조, history.py의 날짜별 파일 분리 저장). 이번 웹 프로젝트는
이 기존 데이터·정책을 그대로 소비만 하고 API 재호출 로직을 새로
만들지 않았다.
