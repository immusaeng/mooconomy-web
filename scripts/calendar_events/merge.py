"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
여러 소스에서 온 이벤트를 하나의 canonical 리스트로 합친다.

동일 이벤트 판단: 국가 + 정규화된 지표명(제목을 slug화한 것) + 예정
날짜(또는 인접 1일 이내)가 모두 맞으면 같은 이벤트로 본다.

우선순위(스펙 §5): 1) 해당 기관 공식 일정 2) 해당 기관 공식 API
3) FRED 4) FMP 5) Finnhub 6) 기타.
"""
from datetime import date

from normalize import _slug

SOURCE_PRIORITY = {
    # 숫자가 작을수록 우선. official_disclosure(DART)도 그 기관 자체가
    # 공식 소스라 official과 동급으로 취급.
    "bok": 0, "ecos": 0, "kosis": 0, "eia": 0, "dart": 0,
    "fred": 1,
    "fmp": 2,
    "finnhub": 3,
}


def _match_key(event):
    return (event["country"], _slug(event["originalTitle"] or event["title"]))


def _dates_close(d1, d2, max_days=1):
    a = date.fromisoformat(d1)
    b = date.fromisoformat(d2)
    return abs((a - b).days) <= max_days


def merge_events(events):
    """events: 여러 소스에서 온 canonical 이벤트 dict의 flat 리스트.
    반환: 중복 제거된 리스트, 각 이벤트의 sourceRefs에 병합에 참여한
    원본 소스들이 남는다(충돌 원본을 버리지 않는다 — 스펙 §5)."""
    buckets = []  # [(match_key, date, merged_event)]
    for ev in sorted(events, key=lambda e: SOURCE_PRIORITY.get(e["sourceName"].lower(), 9)):
        key = _match_key(ev)
        placed = False
        for bkey, bdate, merged in buckets:
            if bkey == key and _dates_close(bdate, ev["scheduledDate"]):
                _fold_into(merged, ev)
                placed = True
                break
        if not placed:
            ev = dict(ev)
            ev["sourceRefs"] = [{
                "sourceName": ev["sourceName"], "sourceUrl": ev["sourceUrl"],
                "sourceTier": ev["sourceTier"],
            }]
            buckets.append((key, ev["scheduledDate"], ev))
    return [merged for _, _, merged in buckets]


def _fold_into(merged, incoming):
    """incoming(우선순위가 낮은, 즉 이미 정렬돼 나중에 오는 소스)을
    merged에 보조 정보로 접는다 — merged의 날짜/시각/공식 필드는
    덮어쓰지 않고, 없는 필드만 보강한다."""
    merged["sourceRefs"].append({
        "sourceName": incoming["sourceName"], "sourceUrl": incoming["sourceUrl"],
        "sourceTier": incoming["sourceTier"],
    })
    if merged.get("scheduledAt") is None and incoming.get("scheduledAt") is not None:
        merged["scheduledAt"] = incoming["scheduledAt"]
        merged["timePrecision"] = "datetime"
        merged["confidence"] = "cross_checked"
    if merged.get("consensus") is None and incoming.get("consensus") is not None:
        merged["consensus"] = incoming["consensus"]
    if merged.get("previous") is None and incoming.get("previous") is not None:
        merged["previous"] = incoming["previous"]
    if merged.get("actual") is None and incoming.get("actual") is not None:
        if merged["sourceTier"] in ("official", "official_disclosure") or incoming["sourceTier"] in ("official", "official_disclosure"):
            merged["actual"] = incoming["actual"]
    if len(merged["sourceRefs"]) > 1 and merged["confidence"] == "single_source":
        merged["confidence"] = "cross_checked"
