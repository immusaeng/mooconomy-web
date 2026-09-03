"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
FRED(세인트루이스 연은) release dates API.
문서: https://fred.stlouisfed.org/docs/api/fred/releases_dates.html
sourceTier=official_aggregator (연은이 다른 기관 통계 발표일을 취합).

주의: 이 세션에는 실제 FRED_API_KEY가 없어 라이브 스모크 테스트를
하지 못했다 — 요청 형태는 공식 문서 기준으로 작성했지만, 응답 필드
매핑은 실제 키로 한 번 더 검증이 필요하다(README에 명시).
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

BASE_URL = "https://api.stlouisfed.org/fred/releases/dates"


def parse(payload):
    """payload: FRED /fred/releases/dates 응답을 json.loads()한 dict.
    네트워크 없이 단위 테스트할 수 있는 순수 함수."""
    events = []
    for row in payload.get("release_dates", []):
        release_name = row.get("release_name") or f"FRED Release {row.get('release_id')}"
        release_date = row.get("date")
        if not release_date:
            continue
        events.append(make_event(
            id=build_event_id("fred", "US", release_name, release_date),
            title=release_name,
            country="US",
            category="macro",
            importance="unknown",
            scheduledDate=release_date,
            scheduledAt=None,
            timezone=None,
            timePrecision="date",
            status="scheduled",
            sourceName="FRED",
            sourceTier="official_aggregator",
            sourceUrl=f"https://fred.stlouisfed.org/release?rid={row.get('release_id')}",
            sourceEventId=str(row.get("release_id")),
        ))
    return events


def fetch(config):
    api_key = config.get_api_key("fred")
    if not api_key:
        raise RuntimeError("missing_api_key")

    import requests

    today = date.today()
    params = {
        "api_key": api_key,
        "file_type": "json",
        "realtime_start": (today - timedelta(days=config.lookback_days)).isoformat(),
        "realtime_end": (today + timedelta(days=config.lookahead_days)).isoformat(),
        "include_release_dates_with_no_data": "true",
        "sort_order": "asc",
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return parse(resp.json())
