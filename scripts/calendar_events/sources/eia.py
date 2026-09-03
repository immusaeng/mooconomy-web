"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
EIA(미국 에너지정보청) v2 API — 원유재고 등 최근 발표된 실제값을
"이미 발표됨(status=released)" 이벤트로 담는다. 스펙상 EIA는 미래
일정 출처가 아니라 실제값 보강 소스라, 여기서 미래 scheduledAt을
임의로(예: "매주 수요일 10:30 ET") 만들어 넣지 않는다 — 그 시각이
FMP/Finnhub 쪽에서 별도로 확보되면 merge.py에서 합쳐진다.

문서: https://www.eia.gov/opendata/documentation.php
주의: 실제 EIA_API_KEY 없이 작성 — 라이브 검증 안 됨.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

# 미국 상업 원유재고(주간) 시리즈.
SERIES_URL = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"


def parse(payload):
    """payload: EIA v2 시리즈 응답을 json.loads()한 dict.
    네트워크 없이 단위 테스트할 수 있는 순수 함수."""
    rows = (payload.get("response") or {}).get("data") or []

    events = []
    for row in rows:
        period = row.get("period")
        if not period:
            continue
        events.append(make_event(
            id=build_event_id("eia", "US", "US commercial crude oil stocks", period),
            title="미국 상업 원유재고",
            country="US",
            category="energy",
            importance="medium",
            scheduledDate=period,
            scheduledAt=None,
            timezone=None,
            timePrecision="date",
            status="released",
            actual=row.get("value"),
            unit=row.get("units"),
            sourceName="EIA",
            sourceTier="official",
            sourceUrl="https://www.eia.gov/petroleum/weekly/",
            sourceEventId=str(period),
        ))
    return events


def fetch(config):
    api_key = config.get_api_key("eia")
    if not api_key:
        raise RuntimeError("missing_api_key")

    import requests

    params = {
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": 1,
    }
    resp = requests.get(SERIES_URL, params=params, timeout=15)
    resp.raise_for_status()
    return parse(resp.json())
