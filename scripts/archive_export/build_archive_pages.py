"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
2026-09-03(TASK_ID=HOMEPAGE_RENEWAL_V3): presentation layer only — swapped
the inline dark-theme template for the release-v3 "timeline" design
(shared styles.css/shared-shell.css/archive.css). Function signatures,
inputs (valid_metadata_list) and call sites are unchanged; no change to
which issues are considered valid or how metadata is computed — that
stays the orchestrator's job (EMPTY_ROUTE_CREATION_PROHIBITED unchanged).

/archive/index.html(전체 목록) + /archive/{YYYY-MM}/index.html(월별 목록)
정적 생성기. build_questions_page.py와 동일한 패턴(순수 문자열 템플릿,
Jinja 없음). 입력은 검증 통과한 issue metadata 리스트만 받는다 — 이
파일 자체는 무엇이 "검증 통과"인지 판단하지 않는다(그건 오케스트레이터
책임).

Determinism: 현재 시각(datetime.now())을 쓰지 않는다. "오늘의 발행판"
강조는 wall-clock 대신 "전달된 목록 중 가장 최근 issue_date"로 판단한다
— 같은 입력이면 항상 같은 바이트의 출력을 만든다.
"""
import calendar as _cal

_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
_MONTH_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
_DOW_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _dow_en(issue_date):
    y, m, d = (int(x) for x in issue_date.split("-"))
    return _DOW_EN[_cal.weekday(y, m, d)]


def _month_label(ym):
    y, m = ym.split("-")
    return {
        "roman": y + " · " + _ROMAN[int(m) - 1],
        "name": _MONTH_EN[int(m) - 1],
    }


def _page_shell(*, title, desc, canonical, crumb_html, h1, lede, meta_html,
                 tabs_html, body_html, root, archive_css,
                 og_image="https://mooconomy.co.kr/assets/og/og-archive-v3.png",
                 jsonld=""):
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Daily MOO:conomy</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Daily MOO:conomy">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{title} | Daily MOO:conomy">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:secure_url" content="{og_image}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Daily MOO:conomy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title} | Daily MOO:conomy">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{og_image}">
{jsonld}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;0,9..144,800;1,9..144,400;1,9..144,700;1,9..144,800&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}styles.css">
<link rel="stylesheet" href="{root}shared-shell.css">
<link rel="stylesheet" href="{archive_css}">
</head>
<body data-root="{root}">

<div class="ticker-bar" aria-label="실시간 시장 지표"><div class="ticker-inner" id="tickerInner"></div></div>

<header class="slim-header">
  <div class="slim-header-inner">
    <a href="/" class="sh-brand">
      <span class="sh-brand-mark">MOO<span class="colon">:</span>conomy</span>
      <span class="sh-brand-tag">DAILY · EST. 2026</span>
    </a>
    <nav class="sh-nav">
      <a href="/">홈</a>
      <a href="/archive/" class="active" aria-current="page">아카이브</a>
      <a href="/calendar/">캘린더</a>
      <a href="/questions/">MOO<span class="colon">:</span>Q</a>
      <a href="/about/">About</a>
    </nav>
    <a href="/#subscribe" class="sh-cta">구독하기</a>
  </div>
</header>

<nav class="breadcrumb" aria-label="위치">{crumb_html}</nav>

<div class="page-header">
  <div class="ph-eyebrow">MOO<span class="colon" style="color:var(--gold)">:</span>ARCHIVE · 발행 서고</div>
  <h1 class="ph-title">{h1}</h1>
  <p class="ph-lede">{lede}</p>
  <div class="ph-meta">{meta_html}</div>
</div>

<main class="page-wrap">
{tabs_html}
{body_html}
</main>

<footer class="foot">
  <div class="wrap">
    <div class="foot-top">
      <div class="foot-brand">
        <div class="wordmark-sm">MOO<span class="colon">:</span>conomy</div>
        <p class="foot-tagline">— 예측하지 않고 기록하고 검증합니다.</p>
      </div>
      <div class="foot-cols">
        <div><h5>발행판</h5><ul>
          <li><a href="/latest.html">오늘의 발행판</a></li>
          <li><a href="/archive/">아카이브 서고</a></li>
          <li><a href="/weekly.html">주간 리포트</a></li>
        </ul></div>
        <div><h5>데이터</h5><ul>
          <li><a href="/markets.html">마켓 대시보드</a></li>
          <li><a href="/calendar/">이벤트 캘린더</a></li>
          <li><a href="/questions/">MOO:Q 검증</a></li>
        </ul></div>
        <div><h5>브랜드</h5><ul>
          <li><a href="/about/">About</a></li>
          <li><a href="/methodology/">방법론</a></li>
          <li><a href="/privacy.html">개인정보</a></li>
        </ul></div>
      </div>
    </div>
    <div class="foot-bot">
      <span>© 2025–2026 MOO:conomy</span>
      <span>월 Weekly · 화–토 Daily · 오전 7시</span>
    </div>
  </div>
</footer>

<nav class="mob-tabs" aria-label="주요 페이지">
  <div class="mob-tabs-inner">
    <a class="mt-item" href="/"><span class="mt-icon i-home"></span><span class="mt-label">홈</span></a>
    <a class="mt-item active" href="/archive/" aria-current="page"><span class="mt-icon i-archive"></span><span class="mt-label">아카이브</span></a>
    <a class="mt-item" href="/calendar/"><span class="mt-icon i-calendar"></span><span class="mt-label">캘린더</span></a>
    <a class="mt-item" href="/questions/"><span class="mt-icon i-q"></span><span class="mt-label">MOO:Q</span></a>
    <a class="mt-item" href="/about/"><span class="mt-icon i-about"></span><span class="mt-label">About</span></a>
  </div>
</nav>

<script src="{root}app.js"></script>
</body>
</html>
"""


def _tabs_html(active):
    def tab(label, href, is_active):
        cls = "arch-tab active" if is_active else "arch-tab"
        current = ' aria-current="page"' if is_active else ""
        return f'<a class="{cls}" href="{href}"{current}>{label}</a>'
    # "발행판" 탭도 실제 경로(/archive/)로 연결한다 — href="#"인 죽은 링크로
    # 두지 않는다(이미 그 페이지에 있어도 유효한 자기참조 링크로 둔다).
    return ('<div class="arch-tabs" role="tablist">'
            + tab("발행판", "/archive/", active == "editions")
            + tab('MOO<span style="color:var(--gold)">:</span>Q 검증 기록', "/questions/", False)
            + tab("방법론 · 정정", "/methodology/", False)
            + "</div>")


def _issue_card(m, is_today):
    dow = _dow_en(m["issue_date"])
    day = m["issue_date"][8:10].lstrip("0") or "0"
    flag_l = "TODAY'S EDITION" if is_today else m["issue_date"]
    thesis = m.get("morning_thesis") or ""
    deck = f'<p class="tlc-deck">{thesis}</p>' if thesis and thesis != m["title"] else ""
    today_cls = " tl-today" if is_today else " tl-past"
    return (
        f'<article class="tl-item{today_cls}">'
        f'<div class="tl-date"><span class="tld-day">{day}</span><span class="tld-dow">{dow}</span></div>'
        f'<div class="tl-node"></div>'
        f'<a class="tl-card" href="{m["public_path"]}">'
        f'<div class="tlc-flag"><span>{flag_l}</span></div>'
        f'<h3 class="tlc-headline">{m["title"]}</h3>'
        f'{deck}'
        f'<div class="tlc-foot"><span></span><span class="tlc-more">전문 읽기 →</span></div>'
        f'</a></article>'
    )


def build_full_index(valid_metadata_list):
    """전체 발행 목록(/archive/index.html) — 실제 검증 통과한 issue만,
    월별로 묶어 최신순 표시(v3 타임라인 디자인)."""
    ordered = sorted(valid_metadata_list, key=lambda x: x["issue_date"], reverse=True)
    latest_date = ordered[0]["issue_date"] if ordered else None

    by_month = {}
    for m in ordered:
        by_month.setdefault(m["issue_date"][:7], []).append(m)

    body = []
    if not ordered:
        body.append('<p class="timeline-empty">아직 발행된 판이 없습니다.</p>')
    else:
        body.append('<div class="timeline">')
        for ym, items in sorted(by_month.items(), reverse=True):
            label = _month_label(ym)
            body.append(
                f'<div class="tl-month"><div class="tlm-tag">{label["roman"]}</div>'
                f'<div class="tlm-title">{label["name"]}<span class="tlm-count">{len(items)}호 발행</span></div></div>'
            )
            body.append('<div class="tl-group">')
            for m in items:
                body.append(_issue_card(m, m["issue_date"] == latest_date))
            body.append('</div>')
        body.append('</div>')

    count = len(ordered)
    date_range = f'{ordered[-1]["issue_date"]} – {ordered[0]["issue_date"]}' if ordered else "–"
    meta = (f'<span>총 <b>{count}</b>호 발행</span>'
            f'<span class="ph-meta-sep"></span>'
            f'<span>기간 <b>{date_range}</b></span>')

    # ItemList JSON-LD — 실제 manifest에 있는 issue URL만(가짜 항목 없음),
    # 최신 manifest를 쓰므로 재생성될 때마다 자동으로 최신화된다.
    items_ld = ",\n    ".join(
        f'{{ "@type": "ListItem", "position": {i + 1}, "url": "https://mooconomy.co.kr{m["public_path"]}" }}'
        for i, m in enumerate(ordered)
    )
    jsonld = "" if not ordered else f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "전체 발행 기록",
  "url": "https://mooconomy.co.kr/archive/",
  "isPartOf": {{ "@type": "WebSite", "name": "Daily MOO:conomy", "url": "https://mooconomy.co.kr" }},
  "mainEntity": {{
    "@type": "ItemList",
    "numberOfItems": {count},
    "itemListElement": [
    {items_ld}
    ]
  }}
}}
</script>
"""

    return _page_shell(
        title="전체 발행 기록",
        desc=f"Daily MOO:conomy가 실제로 발행한 뉴스레터 전체 목록입니다. 매일의 발행판이 쌓여 만드는 기록 서고, 총 {count}호.",
        canonical="https://mooconomy.co.kr/archive/",
        crumb_html='<a href="/">Home</a><span class="bc-sep">›</span><span class="bc-current">The Archive</span>',
        h1='The <em>Archive</em>',
        lede="매일의 발행판이 쌓여 만드는 긴 흐름. 실제로 발행된 판만 여기 모입니다.",
        meta_html=meta,
        tabs_html=_tabs_html("editions"),
        body_html="\n".join(body),
        root="../", archive_css="archive.css",
        jsonld=jsonld,
    )


def build_month_index(year_month, month_metadata_list):
    """월별 목록(/archive/{YYYY-MM}/index.html) — 해당 월에 실제 검증
    통과한 issue가 1건 이상일 때만 오케스트레이터가 이 함수를 호출한다
    (0건인 달은 호출 자체를 안 함 — 빈 라우트 금지)."""
    ordered = sorted(month_metadata_list, key=lambda m: m["issue_date"], reverse=True)
    label = _month_label(year_month)

    body = [
        f'<div class="tl-month"><div class="tlm-tag">{label["roman"]}</div>'
        f'<div class="tlm-title">{label["name"]}<span class="tlm-count">{len(ordered)}호 발행</span></div></div>',
        '<div class="tl-group">',
    ]
    for m in ordered:
        body.append(_issue_card(m, False))
    body.append('</div>')

    meta = f'<span>{year_month} · <b>{len(ordered)}</b>호 발행</span>'

    return _page_shell(
        title=f"{year_month} 발행 목록",
        desc=f"Daily MOO:conomy {year_month} 발행 뉴스레터 목록입니다.",
        canonical=f"https://mooconomy.co.kr/archive/{year_month}/",
        crumb_html=(f'<a href="/">Home</a><span class="bc-sep">›</span>'
                    f'<a href="/archive/">The Archive</a><span class="bc-sep">›</span>'
                    f'<span class="bc-current">{year_month}</span>'),
        h1=f'{label["name"]} <em>{year_month[:4]}</em>',
        lede=f'{year_month} 한 달 동안 발행된 판만 모아봅니다.',
        meta_html=meta,
        tabs_html=_tabs_html("editions"),
        body_html="\n".join(body),
        root="../../", archive_css="../archive.css",
    )
