"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
한국은행 공식 통계 공표 일정 — 공개 API가 없어 공표 일정 페이지를
스크래핑한다(그래서 fixtures/bok.sample.html이지 .json이 아니다).
sourceTier=official. API 키 불필요.

주의: 이 세션에서 실제 페이지 구조를 확인하지 못했다 — 아래 파서는
"날짜 다음에 지표명이 오는 목록/테이블 행" 패턴을 정규식으로 가정한
최선의 추정이다. 실제 배선 전에 반드시 라이브 페이지로 재검증
필요(MIN_EXPECTED_COUNT 미만이면 구조가 바뀐 것으로 보고 빈 리스트를
반환해 잘못된 소수 데이터가 섞여 들어가지 않게 한다).
"""
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

CALENDAR_URL = "https://www.bok.or.kr/portal/main/contents.do?menuNo=200761"
MIN_EXPECTED_COUNT = 1  # 이 미만이면 구조 변경으로 간주하고 빈 리스트

# "2026.09.25" 또는 "2026-09-25" 뒤에 지표명이 오는 패턴을 찾는다.
# 실제 페이지는 <td>날짜</td><td>제목</td> 처럼 사이에 HTML 태그가 끼므로
# 태그/공백을 얼마든지 건너뛰도록 허용한다.
_ROW_RE = re.compile(
    r"(?P<date>20\d{2}[.\-]\s?\d{1,2}[.\-]\s?\d{1,2})(?:\s|<[^>]+>){0,20}(?P<title>[가-힣A-Za-z0-9()·%,\s]{4,60})"
)


def _parse_date(raw):
    digits = re.findall(r"\d+", raw)
    if len(digits) != 3:
        return None
    y, m, d = digits
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def parse_html(html_text):
    events = []
    for m in _ROW_RE.finditer(html_text):
        iso_date = _parse_date(m.group("date"))
        title = m.group("title").strip()
        if not iso_date or not title:
            continue
        events.append(make_event(
            id=build_event_id("bok", "KR", title, iso_date),
            title=title,
            country="KR",
            category="monetary_policy" if ("금융통화" in title or "기준금리" in title) else "macro",
            importance="unknown",
            scheduledDate=iso_date,
            scheduledAt=None,
            timezone=None,
            timePrecision="date",
            status="scheduled",
            sourceName="BOK",
            sourceTier="official",
            sourceUrl=CALENDAR_URL,
        ))
    return events


def fetch(config):
    import requests

    resp = requests.get(CALENDAR_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    events = parse_html(resp.text)
    if len(events) < MIN_EXPECTED_COUNT:
        # 페이지 구조가 바뀌었을 가능성 — 잘못 긁은 소수 데이터를
        # 섞어 넣느니 빈 리스트가 낫다(스펙 §11 "비정상적으로 0건이면
        # 파서 실패 검증"). 조용히 빈 리스트를 돌려주면 "정상인데 0건"과
        # 구분이 안 되니 명시적으로 실패 처리한다.
        raise RuntimeError(
            f"parsed only {len(events)} events, below MIN_EXPECTED_COUNT={MIN_EXPECTED_COUNT} "
            "- page structure may have changed, needs re-verification"
        )
    return events
