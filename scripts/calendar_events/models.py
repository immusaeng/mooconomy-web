"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
canonical 이벤트 계약. dict 기반(이 저장소의 다른 생성기들과 같은 스타일 —
Pydantic 등 새 의존성 도입 안 함). make_event()가 유일한 생성 지점이라
필드 누락을 여기서 한 번에 막는다.
"""

VALID_COUNTRIES = {"KR", "US", "EU", "JP", "CN", "GB", "GLOBAL"}
VALID_CATEGORIES = {
    "macro", "monetary_policy", "employment", "inflation", "growth",
    "trade", "energy", "corporate", "disclosure", "other",
}
VALID_IMPORTANCE = {"high", "medium", "low", "unknown"}
VALID_STATUS = {"scheduled", "released", "revised", "delayed", "cancelled", "published"}
VALID_TIME_PRECISION = {"datetime", "date", "unknown"}
VALID_SOURCE_TIER = {"official", "official_aggregator", "commercial", "official_disclosure"}
VALID_CONFIDENCE = {"confirmed", "cross_checked", "single_source"}


def make_event(
    *, id, title, country, category, importance, scheduledDate,
    sourceName, sourceTier, sourceUrl,
    originalTitle=None, scheduledAt=None, timezone=None, timePrecision="date",
    status="scheduled", previous=None, consensus=None, actual=None, unit=None,
    sourceEventId=None, updatedAt=None, confidence="single_source", sourceRefs=None,
):
    """하나의 canonical 이벤트 dict를 만든다. 값이 없는 필드(예: 실제
    발표 전 actual)는 None으로 명시적으로 남긴다 — 0이나 빈 문자열로
    채우지 않는다(호출자 책임, 여기서는 강제하지 않지만 관례로 통일)."""
    if country not in VALID_COUNTRIES:
        raise ValueError(f"invalid country: {country}")
    if category not in VALID_CATEGORIES:
        raise ValueError(f"invalid category: {category}")
    if importance not in VALID_IMPORTANCE:
        raise ValueError(f"invalid importance: {importance}")
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status: {status}")
    if timePrecision not in VALID_TIME_PRECISION:
        raise ValueError(f"invalid timePrecision: {timePrecision}")
    if sourceTier not in VALID_SOURCE_TIER:
        raise ValueError(f"invalid sourceTier: {sourceTier}")
    if confidence not in VALID_CONFIDENCE:
        raise ValueError(f"invalid confidence: {confidence}")
    if not sourceUrl:
        raise ValueError("sourceUrl is required")
    if not scheduledDate:
        raise ValueError("scheduledDate is required")

    return {
        "id": id,
        "title": title,
        "originalTitle": originalTitle if originalTitle is not None else title,
        "country": country,
        "category": category,
        "importance": importance,
        "scheduledDate": scheduledDate,
        "scheduledAt": scheduledAt,
        "timezone": timezone,
        "timePrecision": timePrecision,
        "status": status,
        "previous": previous,
        "consensus": consensus,
        "actual": actual,
        "unit": unit,
        "sourceName": sourceName,
        "sourceTier": sourceTier,
        "sourceUrl": sourceUrl,
        "sourceEventId": sourceEventId,
        "updatedAt": updatedAt,
        "confidence": confidence,
        "sourceRefs": sourceRefs or [],
    }


def make_canonical_dataset(*, generatedAt, timezone, range_from, range_to,
                            freshness, sources, events):
    return {
        "schemaVersion": "1.0",
        "generatedAt": generatedAt,
        "timezone": timezone,
        "range": {"from": range_from, "to": range_to},
        "freshness": freshness,
        "sources": sources,
        "events": events,
    }
