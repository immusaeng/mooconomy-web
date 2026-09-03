"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
2026-09-03(TASK_ID=HOMEPAGE_V3_CONTENT_CORRECTION + OG_SEO): presentation/
metadata layer only.
- <title> fix: render_from_public_safe_email() used to leave the sent
  email's generic <title>Daily MOO:conomy</title> untouched, so every
  recent issue page shared one title. Now both render paths replace it
  with "{실제 제목} | MOO:conomy".
- OG/Twitter/JSON-LD completeness (site_name, locale, image dimensions,
  NewsArticle) — reuses only real metadata already in `meta`/`record`;
  no invented timestamps, categories, or descriptions.
- Share widget moved near the headline (in addition to the existing
  bottom one, kept as a secondary action) and now shares the canonical
  issue URL, not window.location (matters for latest.html, which is a
  byte-copy of today's issue page but must share the /issues/... URL).
This file only ever adds web-only metadata/UI around content that is
rendered elsewhere (the sent email, or the daily_archive JSON record) —
it never rewrites sentence content, and it has no reach into mailer.py
or the send path.

두 가지 렌더 경로:
- render_from_public_safe_email(): 실제 발송본을 그대로 가진 날짜(오늘)용
  — data/daily_archive의 JSON을 다시 조합하지 않고, 이미 개인정보를
  제거한 실제 이메일 HTML(issue_archive_lib.make_public_safe_html 처리
  완료본)에 웹 전용 요소(canonical/OG/prev-next/아카이브 링크/공유
  버튼)만 삽입한다 — 본문·섹션순서·문구·숫자·V2 디자인은 실발송본과
  동일, 추가되는 것은 웹 전용 metadata·내비게이션·공유 UI뿐이다.
- render_from_json_record(): 실제 발송 HTML이 남아있지 않은 과거 날짜용
  — data/daily_archive/{date}.json(daily-briefing이 이미 정규화해 둔
  실콘텐츠)만으로 새 V2 다크 톤앤매너 페이지를 만든다. 문장을 새로
  쓰지 않고 레코드 값을 그대로 옮긴다.

두 경로 모두 새 LLM 호출 없음, 외부 네트워크 호출 없음.
"""
import re

_METRIC_LABELS = {
    "kospi": "코스피", "kosdaq": "코스닥", "nasdaq": "나스닥", "sp500": "S&P500",
    "usdkrw": "원/달러", "us10y": "미국채10년", "wti": "WTI", "vix": "VIX",
}

_OG_ISSUE_IMAGE = "https://mooconomy.co.kr/assets/og/og-issue-v3.png"
_PUBLISHER_LOGO = "https://mooconomy.co.kr/android-chrome-512x512.png"

# id 접두어를 top/bottom으로 나눠 두 위젯이 공존해도 겹치지 않게 한다.
# 2026-09-03(TASK_ID=NEWSLETTER_EDITORIAL_COMPLETION_AND_WEB_SHARE §F,
# CEO 승인) — 성공 메시지를 지시된 정확한 문구로 통일하고, clipboard API/
# execCommand 둘 다 실패하는 극단적 경우(권한 차단 브라우저 등)에는 에러
# 문구만 보여주고 끝내지 않고 canonical URL을 실제로 선택 가능한 텍스트
# 입력창으로 노출한다("canonical URL을 선택 가능한 형태로 보여준다").
# canonicalEl이 없는 경우의 window.location 폴백은 그대로 유지하되(런타임
# 방어), 실제 발행 시점의 canonical 누락은 render_from_public_safe_email/
# render_from_json_record가 빌드 단계에서 이미 예외로 막는다(아래 참고) —
# 런타임 폴백은 이론상 도달하지 않아야 하는 이중 안전망이다.
_SHARE_SCRIPT = """
<script>
(function () {
  var canonicalEl = document.querySelector('link[rel="canonical"]');
  var url = canonicalEl ? canonicalEl.href : window.location.href.split('?')[0].split('#')[0];
  var title = document.title;

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  function showSelectableUrl(statusEl) {
    if (!statusEl) return;
    statusEl.textContent = '';
    var input = document.createElement('input');
    input.type = 'text';
    input.value = url;
    input.readOnly = true;
    input.className = 'fx-share-fallback-url';
    input.setAttribute('aria-label', '공유 링크(직접 선택해 복사하세요)');
    statusEl.appendChild(input);
    statusEl.classList.add('show');
    input.focus();
    input.select();
  }

  function copyLink(statusEl) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        showStatus(statusEl, '링크를 복사했습니다. 카카오톡에 붙여넣어 공유해 주세요.');
      }).catch(function () {
        if (fallbackCopy(url)) {
          showStatus(statusEl, '링크를 복사했습니다. 카카오톡에 붙여넣어 공유해 주세요.');
        } else {
          showSelectableUrl(statusEl);
        }
      });
    } else if (fallbackCopy(url)) {
      showStatus(statusEl, '링크를 복사했습니다. 카카오톡에 붙여넣어 공유해 주세요.');
    } else {
      showSelectableUrl(statusEl);
    }
  }

  function showStatus(el, msg) {
    if (el) { el.textContent = msg; el.classList.add('show'); }
  }

  document.querySelectorAll('[data-fx-share]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var statusEl = btn.closest('.fx-share-row').querySelector('[data-fx-share-status]');
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function (err) {
          if (err && err.name === 'AbortError') return;
          copyLink(statusEl);
        });
      } else {
        copyLink(statusEl);
      }
    });
  });
  document.querySelectorAll('[data-fx-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      copyLink(btn.closest('.fx-share-row').querySelector('[data-fx-share-status]'));
    });
  });
})();
</script>
"""


def _share_row_html(variant):
    return (
        f'<div class="fx-share-row fx-share-row-{variant}">'
        f'<button type="button" data-fx-share class="fx-share-btn">공유하기</button>'
        f'<button type="button" data-fx-copy class="fx-share-btn secondary">링크 복사</button>'
        f'<span data-fx-share-status class="fx-share-status" role="status" aria-live="polite"></span>'
        f'</div>'
    )


_SHARE_BUTTONS_HTML = _share_row_html("bottom")
_TOP_SHARE_HTML = _share_row_html("top")

_SHARE_CSS = """
.fx-share-row { display:flex; align-items:center; gap:10px; margin-top:16px; flex-wrap:wrap; }
.fx-share-row-top { margin-top:10px; margin-bottom:6px; }
.fx-share-btn { font-size:12.5px; font-weight:700; color:#0B1220; background:#F2C94C; border:none; border-radius:20px; padding:8px 16px; min-height:36px; cursor:pointer; }
.fx-share-btn.secondary { background:transparent; color:#F2C94C; border:1px solid #F2C94C; }
.fx-share-status { font-size:11.5px; color:#95A2BA; display:flex; align-items:center; flex-wrap:wrap; gap:6px; }
.fx-share-status.show { color:#F2C94C; }
.fx-share-fallback-url { font-size:11.5px; color:#E8ECF3; background:#141C2E; border:1px solid rgba(124,138,165,.35); border-radius:6px; padding:6px 8px; min-width:220px; max-width:100%; }
"""

_NAV_CSS = """
.fx-issue-nav { display:flex; justify-content:space-between; gap:12px; margin-top:22px; padding-top:16px; border-top:1px solid rgba(124,138,165,.18); font-size:12.5px; }
.fx-issue-nav a { color:#95A2BA; text-decoration:none; }
.fx-issue-nav a:hover { color:#F2C94C; }
.fx-archive-link { text-align:center; margin-top:14px; font-size:12.5px; }
.fx-archive-link a { color:#F2C94C; text-decoration:none; }
"""


def _clean_description(meta):
    """morning_thesis가 title과 사실상 같으면(현재 manifest 다수가 그렇다)
    "설명"으로서 정보가 없다 — 태그를 생략하고 제목을 복제하지 않는다."""
    desc = (meta.get("morning_thesis") or "").strip()
    title = (meta.get("title") or "").strip()
    if not desc or desc == title:
        return None
    return desc[:150]


def _news_article_jsonld(meta, description, canonical):
    title = meta.get("title") or "Daily MOO:conomy"
    published = meta.get("published_at") if not meta.get("published_at_is_approximate") else None
    fields = [
        '"@context": "https://schema.org"',
        '"@type": "NewsArticle"',
        f'"headline": {title!r}'.replace("'", '"'),
        f'"mainEntityOfPage": {{ "@type": "WebPage", "@id": "{canonical}" }}',
        f'"url": "{canonical}"',
        f'"image": ["{_OG_ISSUE_IMAGE}"]',
        '"publisher": { "@type": "Organization", "name": "Daily MOO:conomy", '
        f'"logo": {{ "@type": "ImageObject", "url": "{_PUBLISHER_LOGO}" }} }}',
    ]
    if description:
        fields.append(f'"description": {description!r}'.replace("'", '"'))
    if published:
        fields.append(f'"datePublished": "{published}"')
    # dateModified: 실제 수정 시각 필드가 데이터에 없어 임의로 채우지 않는다(생략).
    body = ",\n  ".join(fields)
    return f'<script type="application/ld+json">\n{{\n  {body}\n}}\n</script>\n'


class MissingCanonicalPathError(ValueError):
    """meta['public_path']가 없으면 공유 위젯이 window.location으로
    조용히 폴백해(예: latest.html에서 자기 자신을 공유) 날짜별 canonical
    보장이 깨진다 — 2026-09-03(§F, CEO 승인 "canonical이 없으면 공유
    기능을 활성화하지 말고 빌드 검증을 실패시킨다") 빌드 단계에서
    즉시 실패시킨다."""


def _head_meta_block(meta, description):
    """canonical + OG(완전판) + Twitter Card + NewsArticle JSON-LD.
    두 렌더 경로 모두 이 한 함수만 쓰므로, 다음 자동 재생성부터도
    동일하게 적용된다(수동으로 산출물만 고치지 않는다)."""
    if not (meta or {}).get("public_path"):
        raise MissingCanonicalPathError(
            "meta['public_path']가 비어 있음 — canonical URL을 만들 수 없어 "
            "공유 위젯이 window.location으로 잘못 폴백할 위험이 있다. 빌드 중단.",
        )
    canonical = f"https://mooconomy.co.kr{meta['public_path']}"
    title = meta["title"] or "Daily MOO:conomy"
    lines = [
        f'<link rel="canonical" href="{canonical}">',
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="Daily MOO:conomy">',
        '<meta property="og:locale" content="ko_KR">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{_OG_ISSUE_IMAGE}">',
        f'<meta property="og:image:secure_url" content="{_OG_ISSUE_IMAGE}">',
        '<meta property="og:image:type" content="image/png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Daily MOO:conomy">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:image" content="{_OG_ISSUE_IMAGE}">',
    ]
    if description:
        lines.insert(1, f'<meta name="description" content="{description}">')
        lines.append(f'<meta property="og:description" content="{description}">')
        lines.append(f'<meta name="twitter:description" content="{description}">')
    if meta.get("published_at") and not meta.get("published_at_is_approximate"):
        lines.append(f'<meta property="article:published_time" content="{meta["published_at"]}">')
    # article:modified_time / article:section: 실제 데이터에 없어 생략(추정 금지).
    lines.append(_news_article_jsonld(meta, description, canonical))
    return "\n".join(lines)


def _nav_block(meta):
    prev_link = (f'<a href="{meta["prev_path"]}">← {meta["prev_date"]}</a>'
                 if meta.get("prev_path") else '<span></span>')
    next_link = (f'<a href="{meta["next_path"]}">{meta["next_date"]} →</a>'
                 if meta.get("next_path") else '<span></span>')
    return (
        f'<div class="fx-issue-nav">{prev_link}{next_link}</div>'
        f'<div class="fx-archive-link"><a href="/archive/">전체 발행 목록 보기</a></div>'
    )


def render_from_public_safe_email(public_safe_html, meta):
    """오늘자처럼 실제 발송 HTML(개인정보 제거 완료본)이 있는 경우 —
    본문은 절대 재작성하지 않고, <title>을 실제 제목으로 바꾸고 <head>
    안에 canonical/OG/JSON-LD를, 헤드라인 근처와 </body> 직전에 공유
    버튼(+이전/다음/아카이브 링크)을 삽입만 한다."""
    html = public_safe_html
    description = _clean_description(meta)
    title_tag = f'<title>{meta["title"] or "발행 기록"} | MOO:conomy</title>'
    html = re.sub(r"<title>.*?</title>", title_tag, html, count=1, flags=re.S)
    meta_block = _head_meta_block(meta, description)
    html = html.replace("</title>", "</title>\n" + meta_block, 1)
    html = html.replace("</style>\n", "</style>\n<style>" + _SHARE_CSS + _NAV_CSS + "</style>\n", 1)

    # 헤드라인 바로 아래(웹 전용) — 이메일 템플릿마다 클래스명이 다를 수 있어
    # hero-headline을 우선 찾고, 없으면 body 시작 직후로 안전하게 폴백한다.
    headline_match = re.search(r'<h1[^>]*class="[^"]*hero-headline[^"]*"[^>]*>.*?</h1>', html, re.S)
    if headline_match:
        insert_at = headline_match.end()
        html = html[:insert_at] + _TOP_SHARE_HTML + html[insert_at:]
    else:
        body_match = re.search(r"<body[^>]*>", html)
        if body_match:
            insert_at = body_match.end()
            html = html[:insert_at] + _TOP_SHARE_HTML + html[insert_at:]

    injected = _SHARE_BUTTONS_HTML + _nav_block(meta) + _SHARE_SCRIPT
    if "</body>" in html:
        html = html.replace("</body>", f'<div class="inner">{injected}</div>\n</body>', 1)
    else:
        html += injected
    return html


_PAGE_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__ | MOO:conomy</title>
__OG_META__
<meta name="robots" content="index,follow">
<style>
  :root { --bg:#0B1220; --card:#141C2E; --card2:#1B2740; --ink:#E8ECF3; --sub:#95A2BA; --gold:#F2C94C; --line:rgba(124,138,165,.18); --up:#FF6B6B; --down:#5B8DEF; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',Arial,sans-serif; line-height:1.6; word-break:keep-all; }
  .wrap { max-width:760px; margin:0 auto; padding:0 20px; }
  header.mh { padding:22px 0; border-bottom:1px solid var(--line); }
  .brand { font-size:18px; font-weight:800; text-decoration:none; color:var(--ink); }
  .brand .g { color:var(--gold); }
  .pubdate { font-size:11px; color:#6B7A99; margin-top:6px; }
  main { padding:28px 0 60px; }
  .fx-label { font-size:11.5px; font-weight:800; color:var(--gold); letter-spacing:.08em; margin:26px 0 12px; text-transform:uppercase; }
  .fx-label.first { margin-top:4px; }
  h1 { font-size:22px; line-height:1.35; margin:0 0 14px; }
  .t3 { display:flex; flex-direction:column; gap:8px; margin-top:4px; }
  .t3 div { font-size:13.5px; }
  .t3 span.mark { color:var(--gold); font-weight:800; margin-right:6px; }
  .story-h { font-size:18px; font-weight:750; margin-bottom:6px; }
  .story-fact { font-size:13.5px; color:#C7CEDB; }
  .mgrid { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin-top:6px; }
  @media (max-width:640px) { .mgrid { grid-template-columns:repeat(2,1fr); } }
  .mbox { background:var(--card); border-radius:8px; padding:10px; }
  .mbox .l { font-size:9.5px; color:#7C8AA5; }
  .mbox .v { font-size:16px; font-weight:800; margin-top:4px; }
  .mbox .c { font-size:10.5px; font-weight:700; margin-top:4px; }
  .mbox .c.up { color:var(--up); } .mbox .c.down { color:var(--down); }
  .mv-card { background:var(--card2); border-radius:10px; padding:18px 16px; }
  .mv-p { font-size:13px; color:#D9DFEA; margin-top:11px; }
  .mv-p.first { margin-top:0; }
  .watch-card { background:var(--card); border-radius:10px; padding:14px 16px; }
  .watch-item { font-size:12.5px; color:#D9DFEA; margin-top:6px; }
  .q-wrap { margin-top:8px; background:var(--card2); border:1px solid rgba(242,201,76,.3); border-radius:10px; padding:14px 16px; }
  .q-text { font-size:14px; font-weight:650; }
  .check-wrap { margin-top:8px; background:#202A3D; border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .src-row { padding:4px 0; font-size:11.5px; color:#8996AE; }
  .src-row a { color:#8996AE; }
""" + _SHARE_CSS + _NAV_CSS + """
  footer { border-top:1px solid var(--line); padding:24px 0; font-size:11.5px; color:var(--sub); }
</style>
</head>
<body>
  <header class="mh"><div class="wrap">
    <a class="brand" href="/">MOO<span class="g">:</span>conomy</a>
    <div class="pubdate">발행 __DATE__ (아카이브 페이지 — daily-briefing의 발행 원본 JSON을 그대로 옮김, 실제 이메일과 동일 V2 디자인 언어로 재구성)</div>
  </div></header>
  <main class="wrap">
    <div class="fx-label first">TODAY&#39;S 3 SIGNALS</div>
    <div class="t3">__THREE_SIGNALS__</div>

    <div class="fx-label">MAIN STORY</div>
    <div class="story-h">__STORY_HEADLINE__</div>
    <div class="story-fact">__STORY_FACT__</div>
""" + _TOP_SHARE_HTML + """
    <div class="fx-label">MAIN 6 METRICS</div>
    <div class="mgrid">__METRICS__</div>

    <div class="fx-label">MOO:VIEW</div>
    <div class="mv-card">__MOO_VIEW__</div>

    <div class="fx-label">TODAY&#39;S WATCH</div>
    <div class="watch-card">__TODAYS_WATCH__</div>

__MOO_Q_BLOCK__
__MOO_CHECK_BLOCK__

    <div class="fx-label">SOURCES</div>
    <div>__SOURCES__</div>

""" + _SHARE_BUTTONS_HTML + """__NAV_BLOCK__
  </main>
  <footer><div class="wrap">© 2026 Mooconomy · Daily MOO:conomy 발행 아카이브</div></footer>
""" + _SHARE_SCRIPT + """
</body>
</html>
"""


def _fmt_change(m):
    unit = "%" if m.get("displayMode") == "pct" else ""
    sign = "▲" if m.get("direction") == "up" else ("▼" if m.get("direction") == "down" else "―")
    return f"{sign} {abs(m.get('change') or 0):.2f}{unit}"


def render_from_json_record(record, meta):
    """과거 날짜(실발송 HTML 없음)용 — data/daily_archive/{date}.json의
    실콘텐츠만으로 V2 다크 톤앤매너 페이지를 만든다. 문장을 새로 쓰지
    않고 레코드 값을 그대로 옮긴다."""
    thesis = record.get("thesis") or {}
    main_story = record.get("main_story") or {}
    narratives = record.get("narratives") or {}
    moo_q = record.get("moo_q")
    moo_check = record.get("moo_check") or []
    sources = record.get("sources") or []
    metrics = record.get("metrics") or []

    signals_html = "".join(
        f'<div><span class="mark">&#10003;</span>{s}</div>' for s in (thesis.get("three_signals") or [])
    ) or '<div>오늘 확인된 신호가 충분하지 않습니다.</div>'

    metric_html = "".join(
        f'<div class="mbox"><div class="l">{_METRIC_LABELS.get(m["id"], m["id"])}</div>'
        f'<div class="v">{m["value"]:,.2f}</div>'
        f'<div class="c {m.get("direction") or ""}">{_fmt_change(m)}</div></div>'
        for m in metrics
    )

    moo_view_text = narratives.get("moo_view") or ""
    moo_view_html = "".join(
        f'<div class="mv-p{" first" if i == 0 else ""}">{p}</div>'
        for i, p in enumerate(p.strip() for p in moo_view_text.split("\n\n")) if p
    ) or '<div class="mv-p first">오늘은 확인된 근거만 제공됩니다.</div>'

    watch_items = narratives.get("todays_watch") or []
    watch_html = "".join(f'<div class="watch-item">· {w}</div>' for w in watch_items)
    if narratives.get("todays_watch_oneliner"):
        watch_html += f'<div class="watch-item" style="margin-top:10px;font-weight:600;">{narratives["todays_watch_oneliner"]}</div>'
    if not watch_html:
        watch_html = '<div class="watch-item">오늘의 관전 포인트가 충분하지 않습니다.</div>'

    moo_q_block = ""
    if moo_q:
        moo_q_block = (
            '<div class="fx-label">MOO:Q · 오늘의 질문</div>'
            f'<div class="q-wrap"><div class="q-text">{moo_q["claim_text"]}</div>'
            f'<div style="font-size:11.5px;color:#95A2BA;margin-top:8px;">확인 예정일 {moo_q.get("resolution_at", "다음 거래일")}</div></div>'
        )

    moo_check_block = ""
    if moo_check:
        rows = "".join(
            f'<div style="margin-top:8px;"><div style="font-size:13px;">{c["previous_claim"]}</div>'
            f'<div style="font-size:11.5px;color:#95A2BA;margin-top:4px;">판정: {c.get("verdict", "—")}</div></div>'
            for c in moo_check
        )
        moo_check_block = f'<div class="fx-label">MOO:CHECK · 지난 질문의 결과</div><div class="check-wrap">{rows}</div>'

    sources_html = "".join(
        f'<div class="src-row"><a href="{s["source_url"]}" target="_blank" rel="noopener">{s["source_name"]} — {s["source_headline"]}</a></div>'
        for s in sources if s.get("source_url", "").startswith(("http://", "https://"))
    ) or '<div class="src-row">출처 정보가 없습니다.</div>'

    canonical = f"https://mooconomy.co.kr{meta['public_path']}"
    description = _clean_description(meta)

    html = _PAGE_HEAD
    html = html.replace("__TITLE__", meta["title"] or "발행 기록")
    html = html.replace("__DATE__", meta["issue_date"])
    html = html.replace("__OG_META__", _head_meta_block(meta, description))
    html = html.replace("__THREE_SIGNALS__", signals_html)
    html = html.replace("__STORY_HEADLINE__", main_story.get("headline") or meta["title"] or "")
    html = html.replace("__STORY_FACT__", main_story.get("verified_fact") or "")
    html = html.replace("__METRICS__", metric_html)
    html = html.replace("__MOO_VIEW__", moo_view_html)
    html = html.replace("__TODAYS_WATCH__", watch_html)
    html = html.replace("__MOO_Q_BLOCK__", moo_q_block)
    html = html.replace("__MOO_CHECK_BLOCK__", moo_check_block)
    html = html.replace("__SOURCES__", sources_html)
    html = html.replace("__NAV_BLOCK__", _nav_block(meta))
    return html
