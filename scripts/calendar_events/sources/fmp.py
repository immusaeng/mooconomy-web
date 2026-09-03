"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
Financial Modeling Prep economic calendar.
문서: https://site.financialmodelingprep.com/developer/docs#economic-calendar
sourceTier=commercial. 요금제/권한 문제로 401/403이 나면 예외를 던져
sources/base.py의 fetch_safe()가 잡아 파이프라인은 계속 진행한다
(이 함수 자체는 "중단하지 않는" 책임을 지지 않는다 — 호출부 책임).

주의: 실제 FMP_API_KEY 없이 작성 — 응답 필드명은 공개 문서 기준,
라이브 검증 안 됨.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

BASE_URL = "https://financialmodelingprep.com/api/v3/economic_calendar"

_COUNTRY_MAP = {
    "US": "US", "USA": "US", "United States": "US",
    "KR": "KR", "South Korea": "KR",
    "EU": "EU", "Euro Area": "EU", "Eurozone": "EU",
    "JP": "JP", "Japan": "JP", "CN": "CN", "China": "CN", "GB": "GB", "United Kingdom": "GB",
}

_IMPORTANCE_MAP = {3: "high", 2: "medium", 1: "low", 0: "unknown"}


def parse(rows):
    """rows: FMP economic_calendar 응답을 json.loads()한 list.
    네트워크 없이 단위 테스트할 수 있는 순수 함수."""
    if not isinstance(rows, list):
        return []

    events = []
    for row in rows:
        country = _COUNTRY_MAP.get(row.get("country"), "GLOBAL")
        title = (row.get("event") or "").strip()
        if not title:
            continue
        raw_date = row.get("date")  # 보통 "2026-09-11 12:30:00"
        if not raw_date:
            continue
        date_part, _, time_part = raw_date.partition(" ")
        scheduled_at = None
        precision = "date"
        if time_part and time_part != "00:00:00":
            scheduled_at = f"{date_part}T{time_part}+00:00"
            precision = "datetime"

        importance_raw = row.get("impact")
        importance = _IMPORTANCE_MAP.get(importance_raw, "unknown") if isinstance(importance_raw, int) else "unknown"

        events.append(make_event(
            id=build_event_id("fmp", country, title, date_part),
            title=title,
            country=country,
            category="macro",
            importance=importance,
            scheduledDate=date_part,
            scheduledAt=scheduled_at,
            timezone="UTC" if scheduled_at else None,
            timePrecision=precision,
            status="released" if row.get("actual") not in (None, "") else "scheduled",
            previous=row.get("previous"),
            consensus=row.get("estimate"),
            actual=row.get("actual"),
            unit=row.get("unit"),
            sourceName="FMP",
            sourceTier="commercial",
            sourceUrl="https://financialmodelingprep.com/economic-calendar",
            sourceEventId=str(row.get("id") or ""),
        ))
    return events


def fetch(config):
    api_key = config.get_api_key("fmp")
    if not api_key:
        raise RuntimeError("missing_api_key")

    import requests

    today = date.today()
    params = {
        "from": (today - timedelta(days=config.lookback_days)).isoformat(),
        "to": (today + timedelta(days=config.lookahead_days)).isoformat(),
        "apikey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return parse(resp.json())
