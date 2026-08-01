# 05. Export Layer Design (FORK_3)

## 설계 원칙

원천(`data/history/*.json`, `data/claims_store.json`)을 **직접
수정하지 않는다** — read-only adapter가 이 파일들을 읽어 03번 문서의
계약(MarketSnapshot/QuestionRecord/TemperatureObservation)에 맞는
정규화된 JSON을 만들어 별도 위치에 쓴다. 원천 파일 자체는 그대로 두고,
export 결과물만 새로 생성한다.

## 위치

```
scripts/archive_export/
  __init__.py
  export.py          # read-only adapter + normalizer + writer
  validate.py         # schemas/*.schema.json으로 결과 검증
  dryrun_output/      # 이번 라운드 dry-run 산출물(공개 라우트에 연결 안 됨)
```

이 스크립트는 현재 GitHub Pages 정적 배포 구조에 어떤 빌드 훅으로도
연결돼 있지 않다 — 순수 설계/검증 도구다. 실제 배포 파이프라인에
연결하는 것은 `PUBLIC_ROUTE_DEPLOY_AUTHORIZED=False`에 따라 다음
단계(MVP 구현)에서 사용자 승인 후 진행한다.

## 매핑 로직(01/03번 문서 기준)

- `MarketSnapshot`: `data/history/{date}.json`의 `indicators[]`
  (id→kospi/kosdaq/nasdaq/sp500/usdkrw→krw_usd/us10y→treasury_10y/
  wti→oil/vix)를 계약 필드로 변환. `foreign_flow`/`institution_flow`는
  현재 원천에 없어 **명시적으로 `null`**(추정 금지).
- `TemperatureObservation`: `marketTemperature` 필드가 없는 날짜는
  **레코드 자체를 생성하지 않는다**(가짜 관측치를 만들지 않음) —
  값이 있는 날짜부터만 생성.
- `QuestionRecord`: `data/claims_store.json`의 각 claim을 계약 필드로
  1:1 매핑(이미 완전성이 높아 매핑 로직이 단순).

## Determinism 보장

- 입력 파일을 그대로 두고 같은 스크립트를 두 번 실행하면 바이트
  단위로 동일한 출력이 나와야 한다 — 정렬은 항상 `date` 오름차순,
  JSON 직렬화는 `sort_keys=True, ensure_ascii=False, indent=2`로
  고정.
- 현재 시각(`datetime.now()`)을 export 결과에 절대 넣지 않는다
  (원천 파일의 `generatedAt`/`issuedAt` 등 이미 기록된 시각만 사용) —
  그렇지 않으면 재실행마다 값이 달라져 determinism이 깨진다.

## Public/Private 경계

export 결과 JSON에는 `contentHash`, 내부 디버그 필드를 포함하지
않는다. `source_references`는 제공자 이름("FinanceDataReader" 등)만
포함하고 API 엔드포인트/키는 포함하지 않는다.

## 공개 라우트별 최소 데이터 요구사항(§8 순서 대비)

| 라우트 | 필요 최소 데이터 | 현재 준비 상태 |
|---|---|---|
| `/temperature/` | TemperatureObservation 여러 건(최소 5~10일) | ❌ 0건(내일부터 축적 시작) |
| `/questions/`, `/questions/{id}/` | QuestionRecord 전체 | ✅ 11건, 지금 바로 MVP 가능 |
| `/issues/`, `/issues/{date}/` | DailyIssue 여러 건 | ❌ 0건(오늘부터 축적 시작, 최소 며칠분 필요) |
| `/today/` | 오늘 MarketSnapshot + TemperatureObservation | ⚠️ MarketSnapshot은 가능, Temperature는 내일부터 |
| `/monthly/` | 최소 1개월 DailyIssue | ❌ 요원(DailyIssue 축적 후) |

**권고 순서(§8 요구 순서와 다름, 실제 데이터 준비 상태 기준으로
재정렬 제안)**: `/questions/`가 가장 먼저 실사용 가능한 실제
데이터를 갖췄다 — 다음 단계(MVP)에서 `/questions/`부터 시작하는
것을 권고(§06 문서 결론과 동일).

## dry-run 검증 결과

`scripts/archive_export/export.py`를 실제 커밋된 12개
`data/history/*.json` + `data/claims_store.json`(11건)에 대해
2회 연속 실행한 결과:

```
MarketSnapshot 생성: 12건(전부 foreign_flow/institution_flow=null)
TemperatureObservation 생성: 0건(marketTemperature 값 있는 날짜 없음 — 설계대로 생성 안 함)
QuestionRecord 생성: 11건
Schema 검증: 전부 PASS(jsonschema Draft 2020-12)
Determinism: 1차 실행 SHA-256 == 2차 실행 SHA-256(바이트 단위 동일)
```
