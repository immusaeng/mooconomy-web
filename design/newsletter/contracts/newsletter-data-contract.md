# 뉴스레터 데이터 계약(현재 코드 기준 실측)

daily-briefing HEAD `a60fa52` 기준, `main.py`/`templates/briefing.html`/
`llm.py`/`site_narrative.py`/`schemas/home.schema.json`을 직접 대조해 작성.
존재하지 않는 필드명을 만들어내지 않았고, home.json/데이터 파일은 수정하지
않았다.

## ⚠️ 가장 중요한 발견: 두 개의 서로 다른 콘텐츠 파이프라인

뉴스레터와 home.json은 **일부 필드만 공유**하고, 나머지(뉴스/리스크/캘린더)는
**서로 다른 별도의 LLM 호출·데이터 소스**를 쓴다. Stitch 디자인이 "홈페이지에
보이는 문구를 뉴스레터에도 똑같이 쓸 수 있다"고 가정하면 안 된다.

| 개념 | home.json(홈페이지)의 필드 | 뉴스레터의 필드 | 같은 소스인가 |
|---|---|---|---|
| 시장 온도 | `marketTemperature` | `data.marketTemperature`(동일 객체) | **예**, 공유 |
| 오늘의 3줄 | `dailyThree` | `c.three_line_summary` | **아니오** — 별도 텍스트(`site_narrative.py` vs `llm.py`의 서로 다른 LLM 호출 결과) |
| 연결고리 | `connection` | `data.connection`(배선은 됨, 템플릿 미사용) | 데이터는 동일 객체, **렌더링은 홈페이지만** |
| 명제(질문/검증) | `claims` | `data.claims`(동일 객체) | **예**, 공유 |
| 뉴스 | `news`(`site_narrative.py`가 RSS 기반으로 생성) | `c.domestic_news`/`c.global_news`(`llm.py`의 별도 뉴스레터 전용 LLM 호출) | **아니오**, 완전히 별개 |
| 리스크 | `risks`(`site_narrative.py`, 규칙 기반 후보+LLM 요약) | `c.risk_factors`(`llm.py`의 뉴스레터 전용 LLM 호출) | **아니오**, 완전히 별개 |
| 일정/캘린더 | `calendar`(`market_calendar.py`, FRED+Finnhub) | `data.미국실적_필터`(같은 `market_calendar.py` 원본을 재사용하지만 필터링된 파생 필드, home.json의 `calendar`와 필드명·구조 다름) | 원본 수집기는 같으나 **가공된 필드는 다름** |

## 필드별 상세

### marketTemperature
- source: `site_narrative.py`(`_judge_temperature` 규칙 + LLM 요약 1회) →
  `main.py`가 `home.get("marketTemperature")`로 뉴스레터에도 동일 객체 주입
- type: `{label, displayLabel, summary, reasons[], watchItems[], status}`
- required/optional: optional — `status != 'ok'`거나 `None`이면 섹션 생략
- empty-state: 완전 생략(가짜 문구 없음)
- 현재 이메일에서 렌더링: **예**(`displayLabel`+`summary`만, `reasons`/`watchItems`는 필드는 오지만 템플릿 미사용)
- 향후 모바일웹에서 사용 가능: 예(이미 홈페이지가 `reasons`/`watchItems`까지 전부 사용 중)

### metrics(뉴스레터의 실제 필드명은 `data.국내`/`data.글로벌`)
- source: `collectors/kr_market.py`, `collectors/global_market.py`(원본 raw 수집,
  home.json의 `indicators`와는 **다른 파이프라인** — 예: 브렌트유는 뉴스레터
  원본에만 있고 home.json `indicators`에는 없음)
- type: dict, 지수명(한국어)이 key
- required/optional: 개별 지수 optional(없으면 스트립 해당 칸만 생략)
- empty-state: 해당 칸 생략(6칸 중 일부만 뜰 수 있음 — 6개 전부 있는 게 정상 케이스)
- 현재 이메일에서 렌더링: 예
- 향후 모바일웹: home.json의 `indicators`(8개, 코스피·코스닥·나스닥·S&P500·
  원달러·미국채10년·WTI·VIX)를 쓸지, 뉴스레터 원본(6개, 브렌트유 포함)을 쓸지
  **결정 필요** — 두 목록이 다르다

### dailyThree(홈페이지) / three_line_summary(뉴스레터)
- source: 홈페이지=`site_narrative.py`, 뉴스레터=`llm.py`의 별도 호출
- type: 둘 다 문자열 배열이지만 홈페이지는 `{id,title,text,status}` 객체
  배열, 뉴스레터는 순수 문자열 배열(구조 자체가 다름)
- required/optional: optional, 비어있으면 섹션 생략
- 현재 이메일에서 렌더링: 예(`<ul><li>`, GLOBAL/KOREA/WATCH 라벨은 2026-07-22
  롤백으로 제거되고 순서 번호만 사용)
- 향후 모바일웹: 재설계 시 두 텍스트 소스 중 무엇을 쓸지 결정 필요

### claims / MOO:Q·MOO:CHECK
- source: `claims.py`, home.json과 완전히 동일 객체를 `main.py`가 뉴스레터에도 주입
- type: `{status, todayClaims[], previousClaims[], previousPublicationId, totals}`
- required/optional: `None`이면 MOO:Q/MOO:CHECK 둘 다 생략
- empty-state: `todayClaims=[]`면 MOO:Q만 생략(MOO:CHECK는 `claims`가
  `None`이 아닌 한 항상 렌더 — "첫 질문을 확인 중입니다" placeholder 포함)
- **주의**: `docs/issues/P0-claims-store-persistence.md`에 문서화된 대로
  `previousClaims`/`totals`는 자동 발행 파이프라인에서 구조적으로 항상
  비거나 0일 가능성이 높다(claims_store가 실행 간 영속되지 않음) — 이
  문제는 **해결된 것으로 간주하지 않는다.** Stitch 디자인이 "MOO:CHECK에
  과거 이력이 여러 건 쌓여있는" 모습을 기준 화면으로 삼으면 안 된다(현재
  실제로는 나타나지 않는 상태).
- 현재 이메일에서 렌더링: 예
- 향후 모바일웹: 예(홈페이지가 이미 `#claims-scorecard`/`#moo-q-check`로 사용 중)

### connection(오늘의 연결고리)
- source: `site_narrative.py`, home.json과 동일 객체를 `main.py`가 여전히 주입
- type: `{nodes[{label,detail}], summary, counterScenario, status}`
- required/optional: optional
- 현재 이메일에서 렌더링: **아니오**(2026-07-22 제거, ADR-001) — 데이터
  자체는 여전히 존재하고 배선됨
- 향후 모바일웹: 사용 가능(홈페이지가 이미 사용 중), 다만 뉴스레터 재도입
  여부는 사용자 승인 필요

### calendar / news / risks(home.json 전용, 뉴스레터는 별도 필드 사용)
- 위 표 참고 — 이 세 필드는 home.json에서만 쓰이고, 뉴스레터는 각각
  `data.미국실적_필터`(부분 공유)/`c.domestic_news`+`c.global_news`(완전
  별개)/`c.risk_factors`(완전 별개)를 쓴다.
- Stitch 디자인이 홈페이지의 `news`/`risks` 문구를 그대로 뉴스레터 프리뷰에
  가져오면 실제 발송되는 문구와 달라진다 — 향후 모바일웹이 "뉴스레터 미리보기"
  성격이라면 어느 소스를 쓸지 명확히 정해야 한다.

### publishDate/generatedAt에 해당하는 실제 필드
- 뉴스레터: `send_date`(`renderer.py`가 `datetime.now()`로 직접 생성,
  home.json의 `generatedAt`과 다른 방식), `base_date`(`data.국내.기준일`),
  `market_date_us`(`data.글로벌.나스닥/S&P500.날짜`)
- home.json: `publishDate`, `generatedAt`, `marketDateKr`, `marketDateUs`
- 이름과 계산 방식이 다르다 — 화면에 보이는 "발행일/기준일" 표기가 두 곳에서
  근소하게 다를 수 있다(뉴스레터는 렌더 시점의 `datetime.now()`, home.json은
  `main.py` 실행 시점에 한 번 고정).

## 이번 문서 작성 중 지킨 원칙
- 존재하지 않는 필드명을 만들어내지 않았다(전부 실제 코드에서 grep으로 확인).
- home.json/데이터 파일을 수정하지 않았다(읽기만 함).
- MOO:Q 데이터가 없으면(claims 비어있음) 질문을 만들어내지 않는다는 원칙을
  그대로 서술했다.
- claims_store P0 문제를 해결된 것처럼 쓰지 않았다 — 위 "주의" 문단에 명시.
