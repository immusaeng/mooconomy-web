"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
OpenDART(금융감독원 전자공시) — 최근 등록된 공시 목록. 미래 거시경제
일정 소스로 쓰지 않는다(스펙 §3) — 공시는 이미 등록된 뒤에만 알 수
있으므로 전부 status="published"(과거/현재 이벤트)로 담는다.

문서: https://opendart.fss.or.kr/guide/main.do
주의: 실제 DART_API_KEY 없이 작성 — 라이브 검증 안 됨.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

LIST_URL = "https://opendart.fss.or.kr/api/list.json"


def parse(payload):
    """payload: OpenDART list.json 응답을 json.loads()한 dict.
    네트워크 없이 단위 테스트할 수 있는 순수 함수."""
    if payload.get("status") != "000":
        # DART는 결과 없음도 상태코드로 구분한다(013=조회 결과 없음 등) —
        # 진짜 오류만 예외로 올리고, "결과 없음"은 빈 리스트로 처리.
        if payload.get("status") == "013":
            return []
        raise RuntimeError(f"DART API error: {payload.get('status')} {payload.get('message')}")

    events = []
    for row in payload.get("list", []):
        title = (row.get("report_nm") or "").strip()
        corp = (row.get("corp_name") or "").strip()
        rcept_dt = row.get("rcept_no", "")[:8]
        if not title or not rcept_dt:
            continue
        iso_date = f"{rcept_dt[:4]}-{rcept_dt[4:6]}-{rcept_dt[6:8]}"
        full_title = f"{corp} - {title}" if corp else title
        events.append(make_event(
            id=build_event_id("dart", "KR", row.get("rcept_no", full_title), iso_date),
            title=full_title,
            country="KR",
            category="disclosure",
            importance="unknown",
            scheduledDate=iso_date,
            scheduledAt=None,
            timezone=None,
            timePrecision="date",
            status="published",
            sourceName="OpenDART",
            sourceTier="official_disclosure",
            sourceUrl=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={row.get('rcept_no')}",
            sourceEventId=row.get("rcept_no"),
        ))
    return events


def fetch(config):
    api_key = config.get_api_key("dart")
    if not api_key:
        raise RuntimeError("missing_api_key")

    import requests

    today = date.today()
    params = {
        "crtfc_key": api_key,
        "bgn_de": (today - timedelta(days=config.lookback_days)).strftime("%Y%m%d"),
        "end_de": today.strftime("%Y%m%d"),
        "page_no": 1,
        "page_count": 100,
    }
    resp = requests.get(LIST_URL, params=params, timeout=15)
    resp.raise_for_status()
    return parse(resp.json())
