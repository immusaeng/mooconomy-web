# 캘린더 데이터 소스 정책

## 소스별 역할과 우선순위

| 소스 | tier | 역할 | 이번 라운드 상태 |
|---|---|---|---|
| BOK | official | 한국 공표 일정 | 스크래퍼 구현, 실제 페이지 구조 미검증 |
| ECOS | official | 한국 지표 실제값 보강 | 계약만(이벤트 생성 안 함) |
| KOSIS | official | 한국 통계 실제값 보강 | 계약만(이벤트 생성 안 함) |
| EIA | official | 에너지 통계 실제값 | 구현, 라이브 미검증(키 없음) |
| OpenDART | official_disclosure | 국내 기업 공시 | 구현, 라이브 미검증(키 없음) |
| FRED | official_aggregator | 미국 지표 발표일 | 구현, 라이브 미검증(키 없음) |
| FMP | commercial | 글로벌 캘린더(시각/예상/실제) | 구현, 라이브 미검증(키 없음) |
| Finnhub | commercial | 글로벌 캘린더 보완/교차검증 | 구현, 라이브 미검증(키 없음) |

병합 우선순위: 공식 소스(BOK/ECOS/KOSIS/EIA/DART) > FRED > FMP >
Finnhub. 자세한 규칙은 `scripts/calendar_events/merge.py` 참고.

## LLM 사용 금지

Gemini/Anthropic/Groq 등 어떤 LLM도 일정 데이터 수집·정규화·중요도
판정에 쓰지 않는다. 중요도는 `importance.py`의 키워드 규칙으로만
정한다. `LLM_CALL_COUNT=0`을 이 파이프라인의 불변 조건으로 둔다.

## 라이브 검증 상태에 대한 정직한 고지

이 세션에는 위 8개 소스 중 어느 것의 API 키도 없었다(환경변수
미설정, GitHub secrets 접근 없음). 따라서:

- 각 어댑터의 `parse()` 함수(순수 파싱 로직)는 공식 문서 기준으로
  작성한 fixture로 단위 테스트했다(`tests/calendar_events/test_fixtures.py`,
  네트워크 없이 통과 확인됨).
- 실제 라이브 엔드포인트에 대고 응답 스키마가 코드와 정확히 일치하는지는
  **검증하지 못했다.** 특히 BOK(HTML 스크래핑)는 실제 페이지를 한 번도
  보지 못한 채 정규식을 추정으로 작성했다 — 최소 건수 미달이면 파서가
  스스로 실패 처리하도록 만들어 뒀지만(구조 변경/추정 오류 모두 이
  경로로 걸린다), 실제 성공 여부는 실제 키/네트워크로 별도 확인이
  필요하다.
- 키가 등록되고 처음 `--live`를 실행했을 때 특정 소스가 계속
  `ok=False`로 나오면, 그 소스의 `sources/<name>.py` 안 `parse()`
  함수를 실제 응답으로 다시 맞추면 된다 — 나머지 파이프라인(정규화/
  병합/중요도/view 생성)은 그 소스와 무관하게 이미 검증돼 있다.

## 카테고리/중요도 분류 근거

`importance.py`의 키워드 목록은 스펙 §6에 명시된 예시(기준금리,
FOMC, CPI, 고용보고서 등 = high / 산업생산, PMI 등 = medium)를 그대로
옮긴 것이다. 임의로 항목을 추가하거나 뺀 것 없음.
