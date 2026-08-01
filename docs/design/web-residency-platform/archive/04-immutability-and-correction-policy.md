# 04. Immutability & Correction Policy (FORK_2)

## 불변 필드(Lock 이후 절대 수정 금지)

| 객체 | 불변 필드 |
|---|---|
| QuestionRecord | `issued_at`, `observation_value`, `observation_unit`, `observation_as_of`, `expected_direction`, `locked_at` |
| DailyIssue | `issue_date`, `published_at`, `source_snapshot_id`(발행 시점에 연결된 스냅샷 자체는 안 바뀜) |
| MarketSnapshot | `observed_at`, 지표 원본값(kospi/kosdaq/... raw 숫자) |
| TemperatureObservation | `date`, `observed_at`, `linked_snapshot_id` |

이 필드들은 이미 daily-briefing의 claims.py가 정확히 이 원칙으로
구현돼 있다(`_content_hash()`로 핵심 필드를 해시해 잠금 확인, 잠긴
뒤 수정 필요 시 새 revision만 허용) — 이번 계약은 이 기존 원칙을
그대로 다른 객체에도 일반화한 것이다.

## Append-only 필드

`resolution`(QuestionRecord — 판정 전 null, 판정 후 1회만 채워짐,
이후 재수정 시 CorrectionRecord를 통해서만), `signals`/`reasons`
(TemperatureObservation의 근거 목록 — 새 근거 추가는 가능하나 기존
근거 문장을 삭제/수정하지 않음).

## 정정(Correction) 원칙

1. 어떤 객체든 발행된 값이 틀렸다고 판단되면, **그 값을 직접
   덮어쓰지 않는다.**
2. 대신 `03-archive-data-contract.md`의 `CorrectionRecord`를
   append하고, 대상 레코드에 `correction_status=corrected`(DailyIssue)
   또는 `correctedFrom`(QuestionRecord, 기존 필드 재사용)을 채운다.
3. 공개 아카이브 페이지는 `previous_value`와 `corrected_value`를
   함께 보여준다(숨기지 않음) — `public_note`에 정정 사유의
   독자용 짧은 설명을 남긴다.
4. **정정 이력을 이유로 과거 레코드를 검색 결과에서 제외하거나
   noindex 처리하지 않는다** — 정정 자체가 신뢰성의 증거다.

## formula_version / method_version 규칙

- `TemperatureObservation.formula_version`: 시장온도 5단계 판정
  로직(`signals.py`/`site_narrative.py`)이 바뀌면 증가. 초기값 `v1`
  (이번 계약에서 처음 명명 — 기존 코드에 버전 문자열이 없었음).
- `QuestionRecord.method_version`: `verificationType`+`thresholdRuleId`
  조합. 판정 규칙(예: 중립 밴드 ±0.2%)이 바뀌면 증가.
- 과거 데이터를 새 산식으로 재계산하는 경우(§5-6 요구):
  `original_result`(원본 그대로 보존) + `recalculated_result`(별도
  필드, 새 `formula_version` 명시) 두 값을 함께 저장한다 — 원본을
  덮어쓰지 않는다.

## 결측값 정책

- 값이 없으면 `null` 또는 명시적 `"status": "missing"` — 0, 이전
  값, 추정값으로 대체하지 않는다(기존 `_chg()`/claims.py 원칙과
  동일, 이미 검증된 패턴 재사용).
- 출처(`source`)와 기준시각(`as_of`/`observed_at`)이 없는 숫자는
  공개 export 대상에서 제외한다(§6-9 요구 그대로).

## Public/Private 경계

Export 결과물(정적 JSON, 공개 라우트가 소비할 데이터)에는 다음을
**절대 포함하지 않는다**: API key/토큰, `RESEND_SEGMENT_ID`, 실제
구독자 이메일, 내부 전용 디버그 필드(예: `contentHash`는 무결성
검증용 내부 필드로 유지하고 공개 JSON에는 노출하지 않는 것을
권장 — 검색 크롤러나 일반 독자에게는 불필요한 정보).
