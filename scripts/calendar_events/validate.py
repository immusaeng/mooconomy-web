"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
canonical dataset의 구조적 유효성 검사. 문제 있으면 이슈 문자열
리스트, 없으면 빈 리스트 — 이 저장소의 다른 validate_* 함수들과
동일한 인터페이스(archive_export/build_sitemap.py 등).
"""
from datetime import datetime

from models import VALID_COUNTRIES, VALID_CATEGORIES, VALID_STATUS


def validate_canonical(dataset):
    issues = []
    events = dataset.get("events", [])

    seen_ids = set()
    for i, ev in enumerate(events):
        prefix = f"event[{i}]"
        if not ev.get("sourceUrl"):
            issues.append(f"{prefix}: missing sourceUrl")
        if not ev.get("scheduledDate"):
            issues.append(f"{prefix}: missing scheduledDate")
        if ev.get("scheduledAt"):
            try:
                dt = datetime.fromisoformat(ev["scheduledAt"])
                if dt.tzinfo is None:
                    issues.append(f"{prefix}: scheduledAt not timezone-aware")
            except ValueError:
                issues.append(f"{prefix}: scheduledAt not valid ISO-8601")
        eid = ev.get("id")
        if not eid:
            issues.append(f"{prefix}: missing id")
        elif eid in seen_ids:
            issues.append(f"{prefix}: duplicate id {eid}")
        else:
            seen_ids.add(eid)
        if ev.get("country") not in VALID_COUNTRIES:
            issues.append(f"{prefix}: invalid country {ev.get('country')!r}")
        if ev.get("category") not in VALID_CATEGORIES:
            issues.append(f"{prefix}: invalid category {ev.get('category')!r}")
        if ev.get("status") not in VALID_STATUS:
            issues.append(f"{prefix}: invalid status {ev.get('status')!r}")

    return issues


def validate_not_sample_data(dataset_or_path):
    """운영 파일(data/calendar_events.json, data/calendar_views/*.json)에
    _meta.sampleData / fixture 표시가 섞여 들어가지 않았는지 확인한다."""
    issues = []
    if isinstance(dataset_or_path, dict):
        meta = dataset_or_path.get("_meta") or {}
        if meta.get("sampleData"):
            issues.append("dataset carries _meta.sampleData=true in a production path")
    return issues


def check_future_events_not_suspiciously_empty(dataset, min_expected=1):
    """향후 일정이 0건이면 "실제로 0건"인지 "수집 실패로 0건"인지
    freshness로 구분해서 신호를 준다 — 여기서 단정하지 않고 경고만."""
    if len(dataset.get("events", [])) == 0:
        freshness = dataset.get("freshness", {})
        if freshness.get("failedSources"):
            return [f"zero events AND failedSources={freshness['failedSources']} — likely collection failure, not a real empty calendar"]
        return ["zero events with no failed sources reported — verify this is genuinely correct"]
    return []
