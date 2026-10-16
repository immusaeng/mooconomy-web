"""규칙 기반 일정(공식 발표 관행/거래소 규정에서 확인한 규칙만).
순수 함수 — 네트워크 호출 없음. holidays는 KRX 휴장일 'YYYY-MM-DD' 집합
(curated_events.json의 KRX 항목).

수출입동향(산업통상부): 매월 1일 발표. 2026-08-01(토)·09-01(화)·10-01(목)
보도자료로 확인 — 토요일이어도 1일에 발표(주말 순연 없음). 1일이
공휴일인 경우의 처리는 3개월 이력으로 확인되지 않아 생성하지 않는다.
주가지수선물·옵션(KRX): 최종거래일 = 결제월의 두 번째 목요일, 휴장일이면
"순차적으로 앞당김"(직전 거래일로 소급). 선물 결제월은 3·6·9·12월이라
그 달은 선물·옵션 동시만기.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

TRADE_URL = "https://www.motir.go.kr/kor/article/ATCL3f49a5a8c/172254/view"
FUT_URL = "https://www.krx.co.kr/contents/OPN/01/01040201/OPN01040201.jsp"
OPT_URL = "https://www.krx.co.kr/contents/OPN/01/01040202/OPN01040202.jsp"


def _months(start, end):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def second_thursday(y, m):
    d = date(y, m, 1)
    d += timedelta(days=(3 - d.weekday()) % 7 + 7)
    return d


def expiry_date(y, m, holidays):
    """두 번째 목요일, 휴장일(주말 포함)이면 직전 거래일로 앞당김."""
    d = second_thursday(y, m)
    while d.weekday() >= 5 or d.isoformat() in holidays:
        d -= timedelta(days=1)
    return d


def _ev(key, title, titleKo, category, importance, d, url, name):
    return make_event(
        id=build_event_id("rules", "KR", key, d.isoformat()),
        title=title, titleKo=titleKo, country="KR", category=category,
        importance=importance, scheduledDate=d.isoformat(), timePrecision="date",
        sourceName=name, sourceTier="official", sourceUrl=url, confidence="confirmed",
    )


def rule_events(range_from, range_to, holidays):
    """range_from/range_to(date) 안의 규칙 기반 일정. holidays에 없는 연도의
    만기일은 휴장 여부를 확인할 수 없으므로 만들지 않는다."""
    covered_years = {h[:4] for h in holidays}
    out = []
    for y, m in _months(range_from, range_to):
        first = date(y, m, 1)
        if first.isoformat() not in holidays and not (m == 1):
            out.append(_ev("Korea Exports and Imports", "Korea Exports and Imports (Monthly)",
                           "수출입 동향", "trade", "medium", first, TRADE_URL,
                           "산업통상부 보도자료(발표 관행)"))
        if str(y) in covered_years:
            d = expiry_date(y, m, holidays)
            if m % 3 == 0:
                out.append(_ev("KOSPI200 simultaneous expiry", "KOSPI 200 Futures & Options Simultaneous Expiry",
                               "코스피200 선물·옵션 동시만기", "other", "high", d, FUT_URL, "KRX"))
            else:
                out.append(_ev("KOSPI200 options expiry", "KOSPI 200 Options Expiry",
                               "코스피200 옵션 만기", "other", "medium", d, OPT_URL, "KRX"))
    return [e for e in out if range_from.isoformat() <= e["scheduledDate"] <= range_to.isoformat()]


CURATED_PATH = os.path.join(os.path.dirname(__file__), "curated_events.json")


def load_curated(path=CURATED_PATH):
    """공식 페이지에서 확인한 날짜만 담은 curated_events.json -> canonical 이벤트."""
    import json
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)["events"]
    return [make_event(sourceTier="official", confidence="confirmed",
                       timezone="Asia/Seoul" if r.get("scheduledAt") else None, **r) for r in rows]
