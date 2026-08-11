"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
issues/{date}.html 정적 생성기.

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

_SHARE_SCRIPT = """
<script>
(function () {
  var btn = document.getElementById('shareBtn');
  var copyBtn = document.getElementById('copyLinkBtn');
  var status = document.getElementById('shareStatus');
  var url = window.location.href.split('?')[0].split('#')[0];
  var title = document.title;

  function showStatus(msg) {
    if (status) { status.textContent = msg; status.classList.add('show'); }
  }

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

  function copyLink() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        showStatus('링크가 복사됐습니다');
      }).catch(function () {
        showStatus(fallbackCopy(url) ? '링크가 복사됐습니다' : '복사에 실패했습니다');
      });
    } else {
      showStatus(fallbackCopy(url) ? '링크가 복사됐습니다' : '복사에 실패했습니다');
    }
  }

  if (btn) {
    btn.addEventListener('click', function () {
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function (err) {
          if (err && err.name === 'AbortError') return;  // 사용자가 취소
          copyLink();
        });
      } else {
        copyLink();
      }
    });
  }
  if (copyBtn) copyBtn.addEventListener('click', copyLink);
})();
</script>
"""

_SHARE_BUTTONS_HTML = """
<div class="fx-share-row">
  <button type="button" id="shareBtn" class="fx-share-btn">공유하기</button>
  <button type="button" id="copyLinkBtn" class="fx-share-btn secondary">링크 복사</button>
  <span id="shareStatus" class="fx-share-status" role="status" aria-live="polite"></span>
</div>
"""

_SHARE_CSS = """
.fx-share-row { display:flex; align-items:center; gap:10px; margin-top:16px; flex-wrap:wrap; }
.fx-share-btn { font-size:12.5px; font-weight:700; color:#0B1220; background:#F2C94C; border:none; border-radius:20px; padding:8px 16px; min-height:36px; cursor:pointer; }
.fx-share-btn.secondary { background:transparent; color:#F2C94C; border:1px solid #F2C94C; }
.fx-share-status { font-size:11.5px; color:#95A2BA; }
.fx-share-status.show { color:#F2C94C; }
"""

_NAV_CSS = """
.fx-issue-nav { display:flex; justify-content:space-between; gap:12px; margin-top:22px; padding-top:16px; border-top:1px solid rgba(124,138,165,.18); font-size:12.5px; }
.fx-issue-nav a { color:#95A2BA; text-decoration:none; }
.fx-issue-nav a:hover { color:#F2C94C; }
.fx-archive-link { text-align:center; margin-top:14px; font-size:12.5px; }
.fx-archive-link a { color:#F2C94C; text-decoration:none; }
"""


def _og_meta_block(meta, description):
    canonical = f"https://mooconomy.co.kr{meta['public_path']}"
    title = meta["title"] or "Daily MOO:conomy"
    lines = [
        f'<link rel="canonical" href="{canonical}">',
        '<meta property="og:type" content="article">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{canonical}">',
    ]
    # 검증된 일반 공개 이미지만 사용 — 이 저장소에서 이미 questions 페이지가
    # 쓰는 실제 존재하는 OG 이미지를 재사용한다(가짜/미확인 이미지 금지).
    lines.append(
        '<meta property="og:image" '
        'content="https://raw.githubusercontent.com/immusaeng/mooconomy-assets/main/og_mooconomy_v2.png">'
    )
    if meta.get("published_at") and not meta.get("published_at_is_approximate"):
        lines.append(f'<meta property="article:published_time" content="{meta["published_at"]}">')
    # published_at_is_approximate=True인 경우 article:published_time을 넣지
    # 않는다 — 확정 발행시각처럼 위장하지 않는다(CEO 지시).
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
    본문은 절대 재작성하지 않고, <head> 안에 canonical/OG 메타데이터를,
    </body> 직전에 공유 버튼+이전/다음/아카이브 링크를 삽입만 한다."""
    html = public_safe_html
    fact = ((meta.get("morning_thesis") or meta.get("title") or "")[:150])
    meta_block = _og_meta_block(meta, fact)
    html = html.replace("</title>", "</title>\n" + meta_block, 1)
    html = html.replace("</style>\n", "</style>\n<style>" + _SHARE_CSS + _NAV_CSS + "</style>\n", 1)
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
<title>__TITLE__ | Daily MOO:conomy __DATE__</title>
<meta name="description" content="__DESCRIPTION__">
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
    description = (meta.get("morning_thesis") or meta.get("title") or "")[:150]

    html = _PAGE_HEAD
    html = html.replace("__TITLE__", meta["title"] or "발행 기록")
    html = html.replace("__DATE__", meta["issue_date"])
    html = html.replace("__DESCRIPTION__", description)
    html = html.replace("__OG_META__", _og_meta_block(meta, description))
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
