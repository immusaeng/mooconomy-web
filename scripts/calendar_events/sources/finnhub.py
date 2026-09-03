"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
Finnhub economic calendar (글로벌 캘린더 보완/교차검증용).
문서: https://finnhub.io/docs/api/economic-calendar
sourceTier=commercial.

주의: 실제 FINNHUB_API_KEY 없이 작성 — 라이브 검증 안 됨.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

_IMPORTANCE_MAP = {3: "high", 2: "medium", 1: "low", 0: "unknown"}


def parse(payload):
    """payload: Finnhub /calendar/economic 응답을 json.loads()한 dict.
    네트워크 없이 단위 테스트할 수 있는 순수 함수."""
    rows = payload.get("economicCalendar", []) if isinstance(payload, dict) else []

    events = []
    for row in rows:
        title = (row.get("event") or "").strip()
        country = (row.get("country") or "GLOBAL").upper()
        if country not in ("KR", "US", "EU", "JP", "CN", "GB"):
            country = "GLOBAL"
        raw_time = row.get("time")  # 보통 "2026-09-11 12:30:00" (UTC)
        if not title or not raw_time:
            continue
        date_part, _, time_part = raw_time.partition(" ")
        scheduled_at = None
        precision = "date"
        if time_part and time_part != "00:00:00":
            scheduled_at = f"{date_part}T{time_part}+00:00"
            precision = "datetime"

        importance_raw = row.get("impact")
        importance = _IMPORTANCE_MAP.get(importance_raw, "unknown") if isinstance(importance_raw, int) else "unknown"

        events.append(make_event(
            id=build_event_id("finnhub", country, title, date_part),
            title=title,
            country=country,
            category="macro",
            importance=importance,
            scheduledDate=date_part,
            scheduledAt=scheduled_at,
            timezone="UTC" if scheduled_at else None,
            timePrecision=precision,
            status="released" if row.get("actual") not in (None, "") else "scheduled",
            previous=row.get("prev"),
            consensus=row.get("estimate"),
            actual=row.get("actual"),
            unit=row.get("unit"),
            sourceName="Finnhub",
            sourceTier="commercial",
            sourceUrl="https://finnhub.io/economic-calendar",
            sourceEventId=str(row.get("eventId") or ""),
        ))
    return events


def fetch(config):
    api_key = config.get_api_key("finnhub")
    if not api_key:
        raise RuntimeError("missing_api_key")

    import requests

    today = date.today()
    params = {
        "from": (today - timedelta(days=config.lookback_days)).isoformat(),
        "to": (today + timedelta(days=config.lookahead_days)).isoformat(),
        "token": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return parse(resp.json())
