# 01. Archive Source Inventory (읽기 전용 조사, FORK_1)

원천 데이터는 전혀 수정하지 않았다 — 모두 `mooconomy-web-work`(clean
clone, origin/main `0f8f06b`)의 커밋된 `data/` 폴더를 읽기만 했다.
이 폴더가 실제 "지속되는" 아카이브 원천이다 — `daily-briefing`(파이프라인
저장소)의 로컬 `data/`는 GitHub Actions 실행마다 새로 체크아웃되는
**휘발성 작업공간**이라 그 자체로는 누적되지 않는다(아래 참고).

## 실제 존재하는 원천 6곳

| 원천 | 위치 | 형태 | 누적 여부 |
|---|---|---|---|
| 일별 지표·신호등 스냅샷 | `data/history/YYYY-MM-DD.json` | 날짜별 개별 파일 | ✅ 실제로 누적됨(파일명이 날짜라 CI 재실행에도 안전) |
| MOO:Q/MOO:CHECK 원장 | `data/claims_store.json` | 단일 파일, claimId로 키 | ✅ 실제로 누적됨(웹 저장소를 "잠금 시점 DB"처럼 seed-back 하는 패턴, 아래 참고) |
| 캘린더 결과 원장 | `data/calendar_results.json` | 단일 파일 | 설계는 누적형이나 현재 0건(모두 pending 상태 소진 또는 최근 필터 변경 영향으로 추정) |
| 오늘 홈 스냅샷 | `data/home.json` | 단일 파일, 매일 덮어씀 | ❌ 오늘 하루치만(과거 보존 안 됨) |
| 오늘 신호등 스냅샷 | `data/signals.json` | 단일 파일, 매일 덮어씀 | ❌ 오늘 하루치만 |
| 장단기 금리차 등 매크로 장기 시계열 | `data/macro_history.json` | 단일 파일, `scripts/build_dashboard_data.py`가 수동 생성 | ✅ 522일치(FRED 원본 재계산, 별도 관심사 — 지표 대시보드용) |

## 발견 1(중요) — `data/daily_market.json`은 이름과 달리 누적되지 않는다

`main.py`의 `append_daily_market()`은 로직상 누적 설계(날짜를 키로
기존 파일에 추가)이지만, `daily.yml`을 보면 `claims_store.json`만
실행 전에 `web_repo`(mooconomy-web)에서 **seed-back**한다:

```
if [ -f web_repo/data/claims_store.json ]; then
  cp web_repo/data/claims_store.json data/claims_store.json
fi
```

`daily_market.json`에는 이 seed-back 단계가 없다. GitHub Actions
runner는 매번 완전히 새 체크아웃이라 로컬 `data/daily_market.json`이
존재하지 않는 상태로 시작 → `append_daily_market()`이 그날 1건짜리
새 dict를 만듦 → `cp data/daily_market.json web_repo/data/daily_market.json`
로 **web_repo의 기존 다일치 누적 파일 전체를 오늘 1건으로 덮어씀**.
실측: 현재 커밋된 `data/daily_market.json`은 `"2026-07-29"` 단 1건뿐.

**결론**: `daily_market.json`은 아카이브 원천으로 신뢰하지 않는다.
`data/history/*.json`(파일명이 날짜라 seed-back 없이도 안전하게
누적됨)을 MarketSnapshot의 유일한 신뢰 가능 원천으로 채택한다.
원천 파이프라인 수정은 이번 태스크 범위 밖이라 daily.yml/main.py는
건드리지 않았다 — FORK_2/3 산출물에만 이 사실을 반영한다.

## 발견 2(중요) — 영속화 계층이 실시간 스냅샷보다 훨씬 얇다

`data/home.json`(오늘 스냅샷, 풍부함)과 `data/history/*.json`(영속
계층, 얇음)을 비교하면:

| 필드 | home.json(오늘만) | history/*.json(영속) |
|---|---|---|
| 지표 | `indicators[]`에 `name`/`displayValue`/`changeUnit`/`asOf`/`source` 포함 | `indicators[]`에 `id`/`value`/`change`/`displayMode`/`direction`/`status`만(name/source/asOf 없음) |
| 시장온도 | `marketTemperature`에 `summary`/`reasons[]`/`watchItems[]` 포함 | `marketTemperature` 필드 자체가 이번 targeted-final-release 라운드에서 처음 추가됐고, **label/displayLabel/status만 저장**(reasons/summary 없음) — 그마저 기존 12개 파일 중 실제로 값이 채워진 파일은 0개(기능이 오늘 아침 실행 이후에 추가돼 아직 반영 전) |
| 국내 수급 | `koreaWatch.items[]`(외국인/기관/개인, 억원 단위) 존재 | **전혀 저장 안 됨** — MarketSnapshot의 `foreign_flow`/`institution_flow` 요구 필드가 영속 계층에 없음 |
| 오늘 3줄/연결고리 | `dailyThree[]`, `connection{}` 존재 | **전혀 저장 안 됨** |
| 뉴스레터 본문(제목/요약/MOO:VIEW) | `latest.html`(HTML, 오늘 것만, 매일 덮어씀)에만 존재 | **전혀 저장 안 됨** — DailyIssue급 콘텐츠의 영속 아카이브가 사실상 없음 |

## 발견 3 — MOO:Q/MOO:CHECK는 이미 실제로 잘 누적되고 있다

`claims_store.json`은 11건(2026-07-19~30, 미해결 1건 포함)이 실제
발행 당시 값(`baseline.value`/`asOf`)과 판정 결과(`resolution.*`)를
전부 갖추고 있다. `revision.correctedFrom`/`contentHash` 필드가 이미
존재해 정정 이력을 기록할 자리는 마련돼 있으나, **실제로 이 필드가
채워진 사례는 0건**(정정 메커니즘이 설계만 되고 구현되지 않음,
04번 문서 참고).

## Coverage 요약(실측)

- 날짜 범위: `data/history/`는 2026-07-18~30(13일 구간 중 12일,
  07-26 결측 — 주말/휴장 추정), `claims_store.json`은 2026-07-19~30.
- 결측 필드: MarketSnapshot의 foreign_flow/institution_flow(영속
  계층 전무), TemperatureObservation의 reason_text/reason_codes
  (오늘 이전 12일 전부 marketTemperature 필드 자체 없음), DailyIssue
  전체(영속 아카이브 0건).
