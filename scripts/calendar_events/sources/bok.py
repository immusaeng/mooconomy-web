"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
2026-09-03(TASK_ID=HOMEPAGE_VISIBLE_ACTIVATION_FIX): 이전 버전은 실제
페이지를 한 번도 못 보고 추정 URL(menuNo=200761, 사실은 금통위
의결사항 페이지였다)로 정규식 파싱을 시도해 항상 0건이었다. 실제
소스는 "월간통계 공표일정" 달력 페이지 — 여기서 확인:
https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do?menuNo=200775
&date=YYYY-MM 파라미터로 월을 바꿀 수 있고, 달력 각 날짜 셀에
<p class="tooltipOp" title="이벤트명">이 실제 이벤트다. BeautifulSoup으로
파싱한다(정규식보다 이 구조에 훨씬 안전 - 이미 이 저장소가 requests를
새로 도입했던 것과 같은 이유로 bs4도 정당화된다: 표준 라이브러리로 이
중첩 테이블을 안전하게 파싱하기 어렵다).
sourceTier=official. API 키 불필요.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from models import make_event  # noqa: E402
from normalize import build_event_id  # noqa: E402

BASE_URL = "https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do"
MENU_NO = "200775"
MIN_EXPECTED_COUNT = 1  # 월 1건 미만이면 구조 변경으로 간주하고 그 달은 버린다


def parse_month_html(html_text, year, month):
    """html_text: listCldr.do?date=YYYY-MM 한 달치 응답 전체.
    year/month: 이 페이지가 어느 달인지(우리가 요청한 date= 파라미터로
    이미 알고 있으므로 페이지 캡션을 다시 파싱하지 않는다)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_text, "html.parser")
    cal = soup.find("div", class_="calendarSet")
    if not cal:
        return []
    table = cal.find("table")
    if not table:
        return []

    events = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        for cell in cells:
            text_nodes = [t for t in cell.find_all(string=True, recursive=False)]
            day_str = "".join(t.strip() for t in text_nodes).strip()
            if not day_str.isdigit():
                continue
            day = int(day_str)
            try:
                iso_date = date(year, month, day).isoformat()
            except ValueError:
                continue
            for p in cell.find_all("p", class_="tooltipOp"):
                title = (p.get("title") or p.get_text() or "").strip()
                if not title:
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
                    sourceUrl=f"{BASE_URL}?menuNo={MENU_NO}&date={year:04d}-{month:02d}",
                ))
    return events


# 하위 호환: build_calendar.py의 fixture 로더가 parse_html(html_text)로
# 부른다 — fixture는 항상 2026-09로 고정해 둔다(픽스처 자체가 그 달로
# 작성됨).
def parse_html(html_text):
    return parse_month_html(html_text, 2026, 9)


def _month_add(year, month, n):
    total = (year * 12 + (month - 1)) + n
    return total // 12, total % 12 + 1


def fetch(config):
    import requests

    today = date.today()
    # lookahead_days만큼 필요한 달 수를 계산(이번 달 포함) - 예: 45일이면
    # 최대 2~3개월치를 넘어갈 수 있어 넉넉히 계산한다.
    months_needed = 1 + (config.lookahead_days // 28) + 1

    all_events = []
    fetched_any = False
    for i in range(months_needed):
        y, m = _month_add(today.year, today.month, i)
        params = {"menuNo": MENU_NO, "date": f"{y:04d}-{m:02d}"}
        resp = requests.get(BASE_URL, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        month_events = parse_month_html(resp.text, y, m)
        if month_events:
            fetched_any = True
        all_events.extend(month_events)

    if not fetched_any or len(all_events) < MIN_EXPECTED_COUNT:
        raise RuntimeError(
            f"parsed only {len(all_events)} events across {months_needed} month(s), "
            f"below MIN_EXPECTED_COUNT={MIN_EXPECTED_COUNT} - page structure may have changed, needs re-verification"
        )
    return all_events
