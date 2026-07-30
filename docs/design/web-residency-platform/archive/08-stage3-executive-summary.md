# 08. Stage 3 Executive Summary

## 한 줄 요약

MOO:Q/MOO:CHECK(질문 원장)는 이미 아카이브로 쓸 수 있을 만큼
충분하고 정확한 데이터를 갖췄고, 시장 지표(MarketSnapshot)도
핵심 값은 갖췄지만 국내 수급 필드가 빠져 있으며, 시장온도 역사와
발행물(DailyIssue) 아카이브는 사실상 아직 존재하지 않는다 —
그래서 이번 단계는 "가짜로 채우지 않고, 있는 것부터 정확히
계약화"하는 데 집중했다.

## 가장 중요한 발견 3가지

1. **`data/daily_market.json`은 이름과 달리 매일 1일치로
   리셋된다**(seed-back 단계 누락) — 아카이브 원천으로 쓰지 않고
   `data/history/*.json`(실제로 안전하게 누적됨)을 채택했다.
2. **오늘의 실시간 데이터(home.json)가 영속 계층(history.py)보다
   훨씬 풍부하다** — 국내 수급(외국인/기관/개인), 시장온도 근거
   문장, 오늘의 3줄, MOO:VIEW 본문 등은 전부 "오늘 하루"만 존재하고
   내일이면 사라진다. 아카이브를 만들려면 이 격차부터 인지해야
   한다(다음 단계 파이프라인 작업의 핵심 과제).
3. **MOO:Q/MOO:CHECK(claims_store.json)는 이미 11건, 10건 판정
   완료로 실제 서비스 가능한 상태** — `/questions/`가 데이터 준비
   관점에서 가장 먼저 만들 수 있는 페이지다.

## 이번 단계에서 한 일

- 6개 실제 데이터 원천을 읽기 전용으로 전수 조사(원천 무수정).
- DailyIssue/MarketSnapshot/TemperatureObservation/QuestionRecord/
  CorrectionRecord/MonthlyReport 6개 객체 계약 + JSON Schema 6개
  작성.
- 불변성·정정·버전 관리 원칙 문서화(기존 claims.py 원칙을
  일반화).
- 실제 데이터로 export 프로토타입을 만들어 dry-run(12+0+11건
  생성, 스키마 검증 전부 PASS, 2회 실행 결과 바이트 단위 동일 —
  deterministic 확인).
- 공개 라우트별 최소 데이터 조건을 확인해, 과제 원안 순서 대신
  실제 준비 상태 기준의 대안 순서를 제안(`/questions/` 최우선).

## 하지 않은 일(의도적)

공개 페이지·프로덕션 파이프라인 연동·`daily-briefing`/
`daily-briefing/mooconomy-web` 수정 — 전부 스코프 밖 또는 다음
단계 대상.

## 다음 단계로 넘기는 결정 필요 사항

1. `/issues/` 우선 구현을 원하면 DailyIssue export를 실제 발행
   파이프라인에 연동하는 작업이 선행돼야 한다(원안 순서 유지 시).
2. 반대로 실제 데이터 준비 상태를 따르면 `/questions/`부터
   시작한다(이번 라운드 권고안).
3. `history.py`가 `koreaWatch`(수급)/`marketTemperature.reasons`를
   함께 저장하도록 파이프라인을 넓히는 작업은 daily-briefing
   저장소 변경이 필요해 사용자 승인 후 별도 라운드로 진행.
