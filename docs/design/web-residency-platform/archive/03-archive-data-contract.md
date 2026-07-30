# 03. Archive Data Contract (FORK_2)

이 계약은 01/02 문서에서 실측한 **실제 존재하는 데이터**를 기준으로
설계했다 — 존재하지 않는 값을 가정하지 않는다. 각 객체마다
"지금 채울 수 있는 필드"와 "계약은 정의하되 오늘은 null인 필드"를
명시적으로 구분한다.

## 공통 규칙(§4 요구 그대로)

모든 객체는 다음 공통 필드를 가진다: `id`, `date`, `created_at`,
`updated_at`, `version`. 날짜는 ISO 8601(`YYYY-MM-DD`), 시각은
`YYYY-MM-DDTHH:MM:SS+09:00`(KST 명시)을 기본으로 한다.

## A. DailyIssue

| 필드 | 타입 | 현재 채움 가능? | 소스 |
|---|---|---|---|
| issue_id | string(`YYYY-MM-DD-issue`) | ✅ | 발행일 |
| issue_date | date | ✅ | `data.발행일` |
| published_at | datetime | ✅ | `daily.yml` 실행 시각 |
| title | string | ✅ | 뉴스레터 Morning Thesis 헤드라인 |
| short_summary | string | ✅ | `home.json.dailyThree` 3줄 요약 |
| main_thesis | string | ✅ | Morning Thesis 본문 |
| market_temperature_status | enum | ✅ | `home.json.marketTemperature.label` |
| market_temperature_score | number\|null | ❌(오늘은 null) | 시장온도는 5단계 라벨만 있고 수치 점수(score) 산식이 없음 — 지어내지 않음, 향후 산식 확정 시 채움 |
| moo_view | string | ✅ | MOO:VIEW 본문(뉴스레터 V2) |
| moo_q_id | string\|null | ✅(있으면) | 그날 QuestionRecord.question_id |
| moo_check_id | string\|null | ✅(있으면) | 검증된 이전 질문의 CheckResult id |
| source_snapshot_id | string | ✅ | 연결된 MarketSnapshot.snapshot_id |
| canonical_url | string | ✅(발행 시 결정) | `/issues/{issue_date}/` |
| content_version | integer | ✅(기본 1) | 콘텐츠 정정 시 증가 |
| correction_status | enum(`none`/`corrected`) | ✅(기본 none) | CorrectionRecord 존재 여부로 파생 |
| created_at/updated_at | datetime | ✅ | export 시점 |

**중요**: DailyIssue는 **오늘(첫 export 시행일)부터 새로 쌓기
시작**한다 — 과거 발행물 원문이 보존돼 있지 않아 소급 생성하면
`FabricatedArchiveValueCount`를 위반한다.

## B. MarketSnapshot

| 필드 | 현재 채움 가능? | 소스 |
|---|---|---|
| snapshot_id | ✅ | `{date}-snapshot` |
| observed_at / domestic_market_date / us_market_date | ✅ | `history.json.date`, 지표별 개별 as-of는 일부만(아래) |
| kospi/kosdaq/nasdaq/sp500/krw_usd/treasury_10y/vix/oil | ✅ | `history.json.indicators[]`(id→kospi/kosdaq/nasdaq/sp500/usdkrw/us10y/wti/vix 매핑) |
| foreign_flow / institution_flow | ❌(과거 12일 null) | `home.json.koreaWatch`에만 존재, 영속 계층 미저장 — 02번 문서 권고 1 참고, 향후 파이프라인이 저장하기 시작하면 그 날짜부터 채워짐 |
| source_references | ✅(부분) | FinanceDataReader(indicators 전체) — 개별 필드 단위 URL은 없음 |
| collection_status | ✅ | 지표별 `status` 필드(`ok`) 그대로 사용 |
| snapshot_version | ✅ | `schemaVersion`(현재 1) |

## C. TemperatureObservation

| 필드 | 현재 채움 가능? | 소스 |
|---|---|---|
| observation_id/date/observed_at | ✅(내일부터) | `history.json.marketTemperature`(2026-07-31 실행분부터 실값) |
| status | ✅(내일부터) | `label` |
| score | ❌ | 수치 점수 산식 없음(5단계 라벨만 존재) — 지어내지 않음 |
| previous_status/direction | ✅(내일부터, 전일 값과 비교 가능해지는 시점부터) | 이전 날짜 관측치와 비교 |
| reason_codes | ❌(오늘은 null) | 현재 `reasons`는 자유서술 문장 배열이라 코드화 안 됨 — 문장 그대로는 `reason_text`로 채우고, `reason_codes`는 향후 문장→코드 매핑 규칙이 생기면 채움 |
| reason_text | ✅(내일부터) | `home.json.marketTemperature.reasons[]`를 저장 시점에 함께 보존하도록 파이프라인이 확장돼야 함(현재 history.py는 label/displayLabel/status만 저장 — 이번 계약이 요구하는 필드를 다음 파이프라인 라운드에서 넓혀야 함, 이번 태스크는 계약만 정의) |
| linked_snapshot_id | ✅ | 같은 날짜의 MarketSnapshot |
| formula_version | ✅(값은 상수 "v1") | signals.py/site_narrative.py의 5단계 판정 로직에 아직 버전 문자열이 없음 — 이 계약을 계기로 "v1"을 초기값으로 채택(로직이 바뀌면 v2로 증가) |
| correction_version | ✅(기본 1) | |

## D. QuestionRecord(이미 가장 완전한 데이터)

| 필드 | 매핑 |
|---|---|
| question_id | `claimId`(예: `2026-07-30-c1`) |
| question | `claimText` |
| issued_at | `issuedAt` |
| observation_value/unit/as_of | `baseline.value`/`baseline`(unit은 metricId에서 파생, 예: usdkrw→"원") / `baseline.asOf` |
| expected_direction | `expectedDirection` |
| check_due_at | `horizon.resolutionAt` |
| result_value/unit | `resolution.endValue` / `resolution.changeUnit` |
| actual_direction | `resolution.verdict`에서 파생(hit=예상방향 일치, miss=불일치, neutral=중립) — 별도 방향 필드가 없어 verdict로 대체 표시 |
| verdict | `resolution.verdict`(hit/miss/neutral) → 계약 enum(적중/부분적중/불일치/판단보류)으로 매핑(§QC_VERDICT_MAP, v2_editorial_logic.py에 이미 구현된 매핑 재사용) |
| evidence | `resolution.explanation` + `startValue→endValue` |
| status | `status`(hit/miss/neutral/unresolved) |
| method_version | ✅(값은 "proxy-v1") | `verificationType`("proxy") + `thresholdRuleId`("pct_020")를 조합해 초기 method_version 문자열로 채택 |
| locked_at | `lockedAt` |
| corrected_at/correction_reason | ❌(현재 0건) | `revision.correctedFrom` non-null이 되는 순간 CorrectionRecord와 함께 채워짐 |

## E. CorrectionRecord(신규 설계 — 현재 미구현)

기존 `revision.correctedFrom`/`contentHash` 필드가 "자리"만 있고
실제 correction 로그 엔티티가 없다. 이번 계약에서 최초로 정식
설계한다.

| 필드 | 설명 |
|---|---|
| correction_id | `{target_id}-corr-{n}` |
| target_type | `daily_issue`\|`market_snapshot`\|`temperature_observation`\|`question_record` |
| target_id | 대상 레코드 id |
| field_name | 정정된 필드명 |
| previous_value/corrected_value | 원본값/정정값(둘 다 보존) |
| reason | 정정 사유(자유 서술, 반드시 사람이 작성) |
| corrected_at | 정정 시각 |
| correction_version | 해당 target의 몇 번째 정정인지 |
| public_note | 아카이브 페이지에 노출할 짧은 공개 안내문 |

CorrectionRecord는 **append-only**다 — 기존 레코드를 절대 덮어쓰지
않고 항상 새 항목을 추가한다.

## F. MonthlyReport(계약만, 공개 페이지 없음)

01~10번 필드는 과제 원문 그대로 채택(변경 없음) — `linked_issue_ids`는
DailyIssue가 실제로 쌓이기 시작한 뒤에야 채울 수 있어 첫 MonthlyReport는
DailyIssue 축적 후 최소 1개월 뒤에나 실제로 생성 가능하다는 점을
`publication_status`(`draft`/`insufficient_data`/`published`)로 표현한다.
