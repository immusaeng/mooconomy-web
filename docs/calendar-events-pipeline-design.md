# 캘린더 공식 소스 수집 파이프라인 — 설계안 (v1)

**2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE) 갱신**: 이 문서가
설계하던 파이프라인이 실제로 구현됐다 —
`scripts/calendar_events/build_calendar.py` 및 `sources/*.py` 8개
어댑터, 홈페이지/캘린더 페이지 연결까지 완료. 실행법은
`docs/calendar-events-operations.md`, 소스별 상태·정직한 미검증
고지는 `docs/calendar-events-source-policy.md` 참고. 이 문서는 원래
설계 근거(공식 소스 후보 조사, 데이터 계약 초안)로 남겨둔다 — 실제
스키마는 구현 과정에서 더 확장됐다(models.py가 최종 계약).

**상태**: 구현 완료, 홈페이지 연결 완료. GitHub Actions 등 자동
스케줄 실행은 아직 배선하지 않았다(운영 가이드 참고) — 지금은 수동
`--live` 실행으로만 데이터가 갱신된다.

## 왜 필요한가

현재 `/calendar/`와 홈 미니 캘린더는 `data/home.json.calendar[]`
(뉴스레터 생성 시 LLM이 그날 언급한 1~2건)와 `data/calendar_results.json`
(그 이벤트들의 결과 판정)만 쓴다. 이건 "오늘자 브리핑이 언급한 이벤트"
지 "이번 달 경제 캘린더"가 아니다 — 데이터가 원래 그 목적으로 만들어진
게 아니라서, 캘린더 페이지가 시안처럼 풍부해지려면 별도의, 캘린더
자체를 목적으로 하는 수집 파이프라인이 필요하다.

## 1차 공식 소스 후보

| 소스 | 범위 | 형식(조사 필요) | 비고 |
|---|---|---|---|
| 한국은행 경제통계 공표 일정 | 한국 · 통화정책/물가 | ECOS API 또는 공표달력 페이지 | API 키 발급 필요 |
| KOSIS 국가통계포털 공표 일정 | 한국 · 물가/고용/성장 | KOSIS Open API | API 키 발급 필요 |
| US BLS Release Calendar | 미국 · 물가/고용 | bls.gov schedule 페이지, iCal 제공 | 스크래핑 또는 iCal 파싱 |
| US BEA Release Schedule | 미국 · 성장(GDP) | bea.gov schedule 페이지 | 스크래핑 |
| Federal Reserve FOMC Calendar | 미국 · 통화정책 | federalreserve.gov calendar 페이지 | 스크래핑, 연 8회 고정 일정이라 캐싱 용이 |

**다음 단계(이 설계 밖)**: 각 소스의 실제 API 계약/이용약관/rate limit을
개별 검토하고, 스크래핑이 필요한 소스는 robots.txt·이용약관을 먼저
확인해야 한다. 이 라운드에서는 이 조사까지 하지 않았다 — 셀렉터를
만들어 실제로 값을 가져오는 코드는 없다.

## 데이터 계약: `data/calendar_events.json`

```json
{
  "_meta": {
    "schemaVersion": 1,
    "sampleData": true,
    "note": "설계 샘플 — 실제 수집기와 연결되지 않았다. 실 배선 전까지 fallback으로 쓰지 말 것.",
    "generatedAt": "<수집 시각, ISO8601>"
  },
  "events": [
    {
      "id": "string, 소스+날짜+제목 기반 안정적 식별자",
      "title": "string, 실제 지표/이벤트명",
      "country": "KR | US | ...",
      "category": "통화정책 | 물가 | 고용 | 성장 | 기타",
      "importance": "high | medium | low",
      "scheduledAt": "ISO8601, 소스가 명시한 실제 예정 시각",
      "timezone": "IANA 타임존, 예: Asia/Seoul, America/New_York",
      "sourceName": "string, 예: 'BLS', '한국은행'",
      "sourceUrl": "string, 원 발표 페이지 URL(추정 금지 — 실제 링크만)",
      "status": "scheduled | released | postponed | cancelled",
      "result": "object|null, 발표 후 채워지는 실제 수치. 발표 전엔 null.",
      "updatedAt": "ISO8601, 이 레코드를 마지막으로 갱신한 시각"
    }
  ]
}
```

원칙(기존 home.json.calendar와 동일 정신):
- `importance`/`result`/`scheduledAt`을 소스에 없는데 추정해서 채우지 않는다.
- `sourceUrl`은 실제로 그 이벤트를 발표하는 페이지만 — 대표 홈페이지로 대체하지 않는다.
- 수집 실패는 그 이벤트를 조용히 빼는 게 아니라 별도 로그로 남긴다(이 라운드엔 로그 스펙만, 구현 없음).

## 홈/캘린더 화면과의 관계

- `data/home.json.calendar`는 **fallback으로 유지**한다 — `calendar_events.json`이
  아직 없거나 비어 있으면 지금처럼 home.json 것만 쓴다.
- 실제 배선 시(승인 후) 렌더 우선순위: `calendar_events.json`이 있으면
  그걸 우선 쓰고, 없는 항목만 `home.json.calendar`로 보완. 이 우선순위
  로직 자체도 이번 라운드에는 구현하지 않았다(홈/캘린더 JS는 여전히
  `home.json.calendar` + `calendar_results.json`만 읽는다 — 변경 없음).

## 수집기 스텁

`scripts/calendar_events/collect_calendar_events.py` — 실제 네트워크
호출 없이, 위 계약대로 **샘플 출력**만 만든다. 출력 경로는 운영
데이터 디렉터리가 아니라 `scripts/calendar_events/fixtures/
calendar_events.sample.json`(테스트 픽스처) — `data/calendar_events.json`은
실제 수집기가 배선된 뒤에만 쓰이는 운영 경로다. 이 스크립트는:
- daily.yml 등 어떤 자동화에도 등록돼 있지 않다.
- 실행해도 외부 API를 호출하지 않는다(수동 실행 시 로컬에서 샘플만 재생성).
- 실 수집 로직을 넣을 자리에 `NotImplementedError` 대신 명시적 TODO
  주석과 각 소스별 함수 스켈레톤만 있다.

## 승인이 필요한 지점

1. 각 공식 소스의 실제 수집 방식(API vs 스크래핑) 확정
2. 수집 주기 및 daily.yml(또는 별도 스케줄) 연결 여부
3. `calendar_events.json`을 홈/캘린더 렌더 로직에 실제로 연결하는 시점
4. 스크래핑이 필요한 소스는 약관/robots.txt 검토 결과
