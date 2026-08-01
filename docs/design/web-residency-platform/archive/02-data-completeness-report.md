# 02. Data Completeness Report (FORK_1)

## MarketSnapshot 후보(`data/history/*.json`)

12개 파일(2026-07-18~30, 07-26 결측), 전부 `indicators` 8종
(kospi/kosdaq/nasdaq/sp500/usdkrw/us10y/wti/vix) 채워짐. `signals`는
11개 파일 3종, 1개 파일(2026-07-24) 2종(유동성 스트레스 신호가 그 날
이후 추가된 것으로 추정 — 원천 파이프라인 변경 이력과 일치, 결함
아님). `calendarSnapshot`은 대부분 빈 배열.

**결측(12/12 파일 전부)**: `foreign_flow`/`institution_flow`(국내
수급) — 영속 계층에 필드 자체가 없음. 오늘 시점 `home.json.koreaWatch`
에만 존재.

## TemperatureObservation 후보

**결측(12/12 파일 전부)**: `marketTemperature` 필드가 이번
targeted-final-release 라운드(2026-07-30)에서 처음 저장 로직에
추가됐으나, 기존 12개 파일은 모두 그 이전에 생성됐거나 그 기능이
반영되기 전 아침 실행분이라 값이 없음(`None`). **실제 값이 채워지는
첫 파일은 2026-07-31 정기 실행분이 될 것**(다음 산출물).

## QuestionRecord / CorrectionResult 후보(`data/claims_store.json`)

| claimId | status | 비고 |
|---|---|---|
| 2026-07-19-c1 | miss | resolution 완비 |
| 2026-07-20-c1 | miss | resolution 완비 |
| 2026-07-20-c2 | hit | resolution 완비 |
| 2026-07-22-c1 | neutral | resolution 완비 |
| 2026-07-23-c1 | neutral | resolution 완비 |
| 2026-07-24-c1 | hit | resolution 완비 |
| 2026-07-25-c1 | neutral | resolution 완비 |
| 2026-07-27-c1 | miss | resolution 완비 |
| 2026-07-28-c1 | miss | resolution 완비 |
| 2026-07-29-c1 | hit | resolution 완비 |
| 2026-07-30-c1 | unresolved | 내일(07-31) 판정 예정 |

10/11 resolution 완비(90.9%), 전부 baseline.value/asOf +
resolution.startValue/endValue/changeValue/changeUnit/explanation
갖춤 — QuestionRecord/MooCheckResult는 **이미 MVP 구현 가능한 수준의
완전성**을 갖췄다.

`revision.correctedFrom`: 11건 전부 `null`(정정 이력 0건 — 기능은
설계돼 있으나 실사용 사례가 아직 없음, 결함 아님).

## DailyIssue 후보

**결측 100%**. 제목/요약/Morning Thesis/MOO:VIEW 등 발행물 콘텐츠가
날짜별로 영속 저장되는 곳이 시스템 어디에도 없다. `latest.html`은
매일 덮어써지는 "오늘의 발행물"일 뿐 이름 그대로 아카이브가 아니다.
`/issues/{date}/` 라우트를 지금 만들면 과거 날짜는 전부 빈 페이지가
된다 — 이번 태스크가 공개 라우트를 만들지 않는 핵심 이유.

## CorrectionRecord 후보

**결측 100%**(구현 자체가 없음, `revision.correctedFrom` 필드만
자리 표시).

## MonthlyReport 후보

**결측 100%**(Stage 6 대상, 이번 라운드에서 계약만 정의).

## 수치 요약

```
ArchiveSourceCount=6
DailyIssueCount=0
MarketSnapshotCount=12
TemperatureObservationCount=0(값 채워진 레코드 기준 — 필드는 존재하나 전부 null)
QuestionRecordCount=11
MooCheckResultCount=10
CorrectionRecordCount=0
EarliestArchiveDate=2026-07-18(MarketSnapshot) / 2026-07-19(QuestionRecord)
LatestArchiveDate=2026-07-30
RequiredFieldCoverage=MarketSnapshot 코어필드 100%, foreign/institution_flow 0%;
  QuestionRecord/MooCheckResult 코어필드 100%; TemperatureObservation 0%;
  DailyIssue 0%
MissingCriticalFields=foreign_flow, institution_flow(MarketSnapshot),
  reason_text/reason_codes/score(TemperatureObservation, 값 자체가 없음),
  DailyIssue 전체 필드
```

## 권고(FORK_2/3에 반영)

1. MarketSnapshot 계약에 foreign_flow/institution_flow를 포함하되,
   과거 12일치는 이 필드를 `null`로 명시(추정치로 채우지 않음) —
   `history.py`가 `home.json.koreaWatch`를 함께 저장하도록 확장하는
   것을 다음 파이프라인 라운드의 권고 사항으로 남긴다(이번엔 수정
   안 함, 원천 데이터 수정 금지).
2. TemperatureObservation은 내일(07-31)부터 실제 값이 쌓이기 시작한다
   — 그 전까지는 "관측 시작일 이전" 상태로 명시하고 과거값을 만들지
   않는다.
3. DailyIssue는 이번 단계에서 계약만 정의(§7), 실제 아카이브는
   과거 발행물을 재구성할 방법이 없어(원문 미보존) **오늘 이후부터
   새로 쌓기 시작**하는 것으로 설계(과거 소급 없음, 지어내지 않음
   원칙).
