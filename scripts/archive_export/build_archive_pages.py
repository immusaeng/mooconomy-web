"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
/archive/index.html(전체 목록) + /archive/{YYYY-MM}/index.html(월별 목록)
정적 생성기. build_questions_page.py와 동일한 패턴(순수 문자열 템플릿,
Jinja 없음). 입력은 검증 통과한 issue metadata 리스트만 받는다 — 이
파일 자체는 무엇이 "검증 통과"인지 판단하지 않는다(그건 오케스트레이터
책임, EMPTY_ROUTE_CREATION_PROHIBITED: 항목이 0개인 월은 아예 호출하지
않는다)."""

_PAGE_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__PAGE_TITLE__ | Daily MOO:conomy</title>
<meta name="description" content="__PAGE_DESC__">
<link rel="canonical" href="__CANONICAL__">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="__PAGE_TITLE__ | Daily MOO:conomy">
<meta property="og:description" content="__PAGE_DESC__">
<meta property="og:url" content="__CANONICAL__">
<meta property="og:image" content="https://mooconomy.co.kr/assets/og_mooconomy_v2.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Daily MOO:conomy — 매일 아침 경제를 3줄로">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="__PAGE_TITLE__ | Daily MOO:conomy">
<meta name="twitter:description" content="__PAGE_DESC__">
<meta name="twitter:image" content="https://mooconomy.co.kr/assets/og_mooconomy_v2.png">
<style>
  :root { --bg:#0B1220; --card:#141C2E; --ink:#E8ECF3; --sub:#95A2BA; --gold:#F2C94C; --line:rgba(124,138,165,.18); }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',Arial,sans-serif; line-height:1.6; word-break:keep-all; }
  .wrap { max-width:760px; margin:0 auto; padding:0 20px; }
  header.mh { padding:22px 0; border-bottom:1px solid var(--line); }
  .brand { font-size:18px; font-weight:800; text-decoration:none; color:var(--ink); }
  .brand .g { color:var(--gold); }
  nav.crumb { font-size:12px; color:var(--sub); margin-top:10px; }
  nav.crumb a { color:var(--sub); }
  main { padding:36px 0 60px; }
  .eyebrow { font-size:11px; font-weight:700; letter-spacing:.08em; color:var(--gold); text-transform:uppercase; margin-bottom:10px; }
  h1 { font-size:24px; margin:0 0 24px; }
  .month-list a, .issue-list a { color:var(--gold); text-decoration:none; }
  .month-list { display:flex; flex-direction:column; gap:8px; margin-bottom:32px; }
  .issue-list { display:flex; flex-direction:column; gap:12px; }
  .issue-card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .issue-card .d { font-size:11px; color:var(--sub); }
  .issue-card .t { font-size:15px; font-weight:700; margin-top:4px; }
  .issue-card .m { font-size:12.5px; color:#C7CEDB; margin-top:4px; }
  .issue-card a { color:var(--ink); text-decoration:none; }
  footer { border-top:1px solid var(--line); padding:24px 0; font-size:11.5px; color:var(--sub); }
</style>
</head>
<body>
  <header class="mh"><div class="wrap">
    <a class="brand" href="/">MOO<span class="g">:</span>conomy</a>
    <nav class="crumb">__CRUMB__</nav>
  </div></header>
  <main class="wrap">
    <div class="eyebrow">ARCHIVE</div>
    <h1>__H1__</h1>
__BODY__
  </main>
  <footer><div class="wrap">© 2026 Mooconomy · Daily MOO:conomy 발행 아카이브</div></footer>
</body>
</html>
"""


def _issue_card(m):
    return (
        f'<div class="issue-card"><a href="{m["public_path"]}">'
        f'<div class="d">{m["issue_date"]}</div>'
        f'<div class="t">{m["title"]}</div>'
        f'<div class="m">{m.get("morning_thesis") or ""}</div>'
        f'</a></div>'
    )


def build_full_index(valid_metadata_list):
    """전체 발행 목록(/archive/index.html) — 실제 검증 통과한 issue만,
    월별로 묶어 최신순 표시."""
    by_month = {}
    for m in sorted(valid_metadata_list, key=lambda x: x["issue_date"], reverse=True):
        ym = m["issue_date"][:7]
        by_month.setdefault(ym, []).append(m)

    month_links = "".join(
        f'<div><a href="/archive/{ym}/">{ym} ({len(items)}건)</a></div>'
        for ym, items in sorted(by_month.items(), reverse=True)
    )
    issue_cards = "".join(_issue_card(m) for m in sorted(valid_metadata_list, key=lambda x: x["issue_date"], reverse=True))

    body = f'<div class="month-list">{month_links}</div><div class="issue-list">{issue_cards}</div>'
    html = _PAGE_HEAD
    html = html.replace("__PAGE_TITLE__", "전체 발행 목록")
    html = html.replace("__PAGE_DESC__", "Daily MOO:conomy가 실제로 발행한 뉴스레터 전체 목록입니다.")
    html = html.replace("__CANONICAL__", "https://mooconomy.co.kr/archive/")
    html = html.replace("__CRUMB__", '<a href="/">홈</a> / 전체 발행 목록')
    html = html.replace("__H1__", "전체 발행 목록")
    html = html.replace("__BODY__", body)
    return html


def build_month_index(year_month, month_metadata_list):
    """월별 목록(/archive/{YYYY-MM}/index.html) — 해당 월에 실제 검증
    통과한 issue가 1건 이상일 때만 오케스트레이터가 이 함수를 호출한다
    (0건인 달은 호출 자체를 안 함 — 빈 라우트 금지)."""
    ordered = sorted(month_metadata_list, key=lambda m: m["issue_date"], reverse=True)
    issue_cards = "".join(_issue_card(m) for m in ordered)
    body = f'<div class="issue-list">{issue_cards}</div>'

    html = _PAGE_HEAD
    html = html.replace("__PAGE_TITLE__", f"{year_month} 발행 목록")
    html = html.replace("__PAGE_DESC__", f"Daily MOO:conomy {year_month} 발행 뉴스레터 목록입니다.")
    html = html.replace("__CANONICAL__", f"https://mooconomy.co.kr/archive/{year_month}/")
    html = html.replace("__CRUMB__", f'<a href="/">홈</a> / <a href="/archive/">전체 발행 목록</a> / {year_month}')
    html = html.replace("__H1__", f"{year_month} 발행 목록")
    html = html.replace("__BODY__", body)
    return html
