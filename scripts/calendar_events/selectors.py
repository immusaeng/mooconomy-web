"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
같은 canonical dataset에서 소비자별(home/daily/weekly) view를 뽑아낸다.
셋 다 이 파일만 거치므로, 각 소비자가 따로 수집·분류 로직을 만들
필요가 없다(스펙 §7의 핵심 요구사항).
"""
from datetime import date, timedelta

_IMPORTANCE_RANK = {"high": 0, "medium": 1, "low": 2, "unknown": 3}


def _sort_key(ev):
    return (
        _IMPORTANCE_RANK.get(ev["importance"], 9),
        ev.get("scheduledAt") or (ev["scheduledDate"] + "T99:99:99"),
    )


def _in_range(ev, start, end):
    d = date.fromisoformat(ev["scheduledDate"])
    return start <= d <= end


def _public_event(ev):
    """홈페이지/뉴스레터로 나가는 이벤트에는 원본 API 응답이나 키가
    없어야 한다 — canonical dict는 이미 그 필드들이 없으므로 그대로
    반환. 여기서 필드를 추가로 걸러내진 않지만, 이 함수를 통과한
    것만 view에 넣는 관례로 향후 필드가 늘어나도 안전판이 되게 한다."""
    return ev


def build_home_view(dataset, today, max_items=40):
    """오늘부터 향후 14일. high 우선, 동일 중요도 내 시간순."""
    start = today
    end = today + timedelta(days=14)
    picked = [_public_event(e) for e in dataset["events"] if _in_range(e, start, end)]
    picked.sort(key=_sort_key)
    picked = picked[:max_items]
    return {
        "schemaVersion": "1.0",
        "generatedAt": dataset["generatedAt"],
        "timezone": dataset["timezone"],
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "freshness": dataset["freshness"],
        "events": picked,
    }


def build_daily_view(dataset, today, max_items=12):
    """오늘 + 다음 영업일의 high/medium. actual 발표됨 vs 예정 구분은
    status 필드로 그대로 노출한다(가공하지 않음)."""
    start = today
    end = today + timedelta(days=2)  # 24~48시간
    picked = [
        _public_event(e) for e in dataset["events"]
        if _in_range(e, start, end) and e["importance"] in ("high", "medium")
    ]
    picked.sort(key=_sort_key)
    picked = picked[:max_items]
    return {
        "schemaVersion": "1.0",
        "generatedAt": dataset["generatedAt"],
        "timezone": dataset["timezone"],
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "freshness": dataset["freshness"],
        "events": picked,
    }


def build_weekly_view(dataset, today, max_items=60):
    """향후 7일, high 우선, 날짜별로 그룹. 주요 일정이 없으면 빈
    배열 + freshness를 그대로 반환한다(가짜 이벤트 생성 금지)."""
    start = today
    end = today + timedelta(days=7)
    picked = [_public_event(e) for e in dataset["events"] if _in_range(e, start, end)]
    picked.sort(key=_sort_key)
    picked = picked[:max_items]

    by_date = {}
    for e in picked:
        by_date.setdefault(e["scheduledDate"], []).append(e)

    return {
        "schemaVersion": "1.0",
        "generatedAt": dataset["generatedAt"],
        "timezone": dataset["timezone"],
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "freshness": dataset["freshness"],
        "events": picked,
        "byDate": by_date,
    }
