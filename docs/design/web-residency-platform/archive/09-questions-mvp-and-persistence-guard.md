# 09. Questions MVP & Daily Persistence Guard

## 목적

(A) home.json이 매일 덮어써져 사라지는 아카이브 핵심 필드를
날짜별로 보존, (B) 이미 완전한 MOO:Q 11건을 검색 가능한 `/questions/`
로 공개.

## A. Persistence Guard

`scripts/archive_export/persist_daily_snapshot.py` — home.json에서
Stage 3 계약이 정의한 필드만 allowlist로 뽑아
`data/archive/daily/{date}.json`에 저장. `data/daily_market.json`은
계속 아카이브 원천에서 제외(리셋 버그, Stage 3에서 이미 확인).

저장 필드: issue_date, observed_at, source_snapshot_id,
domestic/us_market_date, indicators(8종), korea_watch(외국인/기관/
개인), market_temperature(status/score=null/reasons), moo_view(null
— home.json에 실제 필드 없음, 지어내지 않음), question_id,
source_references, formula_version, content_version.

정책: 파일 없으면 생성. 같은 날짜 재실행 시 내용 동일하면 no-op.
내용이 다르면 **원본을 덮어쓰지 않고** `{date}.v{n}.json`으로 별도
버전 저장(`CONFLICT_VERSIONED`).

실측 검증(실제 오늘자 `data/home.json` 사용):
- 최초 실행: `WRITTEN data/archive/daily/2026-07-30.json`
- 재실행(동일 입력): `NOOP`(원본 안 건드림)
- 내용 변경 후 실행(synthetic 테스트, 결과 파일은 검증 후 삭제):
  `CONFLICT_VERSIONED data/archive/daily/2026-07-30.v2.json`, 원본
  파일 내용 불변 확인.

daily.yml/main.py는 수정하지 않았다 — 이 스크립트를 실제 파이프라인에
연결하는 것은 다음 단계 과제.

## B. `/questions/` MVP

`scripts/archive_export/build_questions_page.py`가 Stage 3의
`question_records.json`(claims_store.json 11건 원본 그대로) 읽어
`questions/index.html`을 결정론적으로 생성. LLM 재작성 없음, 원본
질문/결과/근거 문구 그대로.

- 요약: 전체 11 · 판정완료 10 · 확인중 1 · 일치3·부분일치3·불일치4·판단보류1
- 목록: 발행일 역순, 11건 전부 노출(불리한 판정 4건도 숨기지 않음)
- Header 내비: TODAY/QUESTIONS/METHODOLOGY/SUBSCRIBE, Footer: 기존
  법적 고지 재사용 + 투자 권유 아님 명시
- methodology/index.html의 기존 "질문과 결과는 홈에서" 문구를
  "`/questions/`에서"로 1줄 수정(부정확해진 안내 교정)

## 테스트 결과(§8 targeted, 16개 중 해당 항목)

```
QuestionRecordCount=11(중복 question_id 없음, 확인 완료)
CompletedVerdictCount=10
SchemaValidation=PASS(Stage 3 스키마 그대로 재사용, 신규 스키마 0개)
DeterministicExport=True(persist/build 스크립트 모두 재실행 시 동일 결과 확인)
HTMLTagBalance=PASS(open stack 0, errors 0)
H1Count=1
NonJsonLdScriptCount=0(JavaScript 없이 본문 존재)
CanonicalCorrect=True(https://mooconomy.co.kr/questions/)
SitemapUpdated=True(/questions/ 1회만 등장)
SecretPatternScanCount=0
SilentOverwritePossible=False(no-op/versioned 분기로 원천 항상 보존)
```

## 알려진 제한

- `market_temperature.score`/`moo_view`는 원본에 값이 없어 계속 null.
- Persistence guard는 아직 daily.yml에 연결되지 않은 독립 스크립트 —
  실제 자동 축적은 다음 단계에서 파이프라인 연동 필요.
- 반응형 렌더는 정적 CSS 검토로만 확인(Playwright 스크린샷은 이번
  단계 범위 밖).

## 다음 단계

Persistence guard를 daily.yml에 연결(매일 자동 축적 시작), 이후
`/issues/`(DailyIssue) 착수 여부 결정.
