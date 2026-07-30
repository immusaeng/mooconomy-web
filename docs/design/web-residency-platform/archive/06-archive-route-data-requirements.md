# 06. Archive Route Data Requirements (FORK_3)

각 공개 라우트를 만들기 전에 반드시 충족해야 하는 최소 데이터
조건. 조건을 만족하지 못하면 **그 라우트는 만들지 않는다**
(`EMPTY_ROUTE_CREATION_PROHIBITED=True`).

## `/questions/` , `/questions/{question_id}/`

- 최소 조건: QuestionRecord ≥ 1건 — **이미 충족(11건)**.
- 목록 페이지: 전체 질문을 발행일 역순으로. 상세 페이지: 질문 원문,
  질문 시점 기준값(`observation_value`+`observation_as_of`), 확인
  예정일, 결과(있으면), 판정.
- 진행 가능 여부: **✅ 지금 바로 MVP 착수 가능**.

## `/temperature/`

- 최소 조건: TemperatureObservation ≥ 5건(추이를 보여줄 최소 표본).
- 현재: 0건. **내일(2026-07-31)부터 축적 시작** → 5거래일 후(대략
  2026-08-06 전후) 조건 충족 예상.
- 진행 가능 여부: ❌ 보류.

## `/issues/`, `/issues/{date}/`

- 최소 조건: DailyIssue ≥ 1건(목록), 각 상세 페이지는 해당 날짜의
  DailyIssue 1건.
- 현재: 0건. Export 파이프라인이 실제로 매일 DailyIssue를 생성하기
  시작해야 하며(이번 라운드는 계약만 정의, 프로덕션 연동은 다음
  단계), 그 시점부터 쌓임.
- 진행 가능 여부: ❌ 보류(다음 MVP 태스크의 핵심 작업 — 프로덕션
  파이프라인이 DailyIssue export를 실제로 호출하도록 연결해야 함).

## `/today/`

- 최소 조건: 오늘자 MarketSnapshot 1건 + (있으면) 오늘자
  TemperatureObservation 1건.
- 현재: MarketSnapshot은 매일 존재하지만 TemperatureObservation은
  내일부터. `/today/`는 TemperatureObservation이 없는 날엔 "관측
  시작 전" 상태를 표시하고 빈 자리를 지어내지 않아야 한다.
- 진행 가능 여부: ⚠️ MarketSnapshot 기준으로는 가능하나, 페이지의
  핵심 가치(오늘 온도)가 아직 없어 `/questions/` 이후 순번으로 미룸.

## `/monthly/`, `/monthly/{year}/{month}/`

- 최소 조건: 해당 월의 DailyIssue가 대부분의 거래일에 존재.
- 현재: 0건. DailyIssue 축적 후 최소 1개월 소요.
- 진행 가능 여부: ❌ 보류.

## 결론 — 권장 구현 순서(§8 원안과 다름, 근거 명시)

과제 원안 순서(`/issues/ → /temperature/ → /questions/ → /today/ →
/monthly/`) 대신, **실제 데이터 준비 상태**를 기준으로 재정렬을
권고한다:

```
1. /questions/, /questions/{id}/     (데이터 이미 충분, 즉시 가능)
2. /temperature/                      (내일부터 축적, ~1주 후 가능)
3. /issues/, /issues/{date}/         (export 파이프라인 연동 필요)
4. /today/                            (위 3개 완성 후 조합)
5. /monthly/                          (DailyIssue 1개월 축적 후)
```

이 재정렬은 "가짜 콘텐츠로 채우지 않는다"는 최우선 원칙을 지키기
위한 것이며, 사용자가 원안 순서를 명시적으로 원하면 그에 맞춰
`/issues/`용 DailyIssue export 연동을 먼저 시작할 수 있다(다음
태스크에서 결정 필요 사항으로 남김).
