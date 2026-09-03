"""questions/index.html 정적 생성기(읽기 전용 입력, 결정론적 출력).

scripts/archive_export/dryrun_output/question_records.json(Stage 3
export 결과, claims_store.json 11건 그대로)만 읽는다 — 질문·결과
문구를 새로 쓰지 않고 원본 그대로 렌더링한다. JavaScript 없이 전체
본문이 HTML에 그대로 존재한다.
"""
import json
import os

_VERDICT_LABEL = {"hit": "일치", "neutral": "부분일치", "miss": "불일치", "unresolved": "판단보류"}
_DIRECTION_LABEL = {"up": "상승", "down": "하락"}

_PAGE_HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MOO:Q 질문 기록 | 무코노미 경제 질문과 결과</title>
<meta name="description" content="매일 발행한 경제 질문과 다음 거래일 실제 결과를 공개합니다. 발행 당시 기준값, 예상 방향, 확인 결과와 판정 근거를 확인하세요.">
<link rel="canonical" href="https://mooconomy.co.kr/questions/">
<meta name="robots" content="index,follow">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">

<meta property="og:type" content="website">
<meta property="og:title" content="MOO:Q 질문 기록 | 무코노미 경제 질문과 결과">
<meta property="og:description" content="매일 발행한 경제 질문과 다음 거래일 실제 결과를 공개합니다.">
<meta property="og:image" content="https://mooconomy.co.kr/assets/og/og-home-v3.png">
<meta property="og:url" content="https://mooconomy.co.kr/questions/">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="MOO:Q 질문 기록 | 무코노미 경제 질문과 결과">
<meta name="twitter:description" content="매일 발행한 경제 질문과 다음 거래일 실제 결과를 공개합니다.">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "MOO:Q 질문 기록",
  "url": "https://mooconomy.co.kr/questions/",
  "isPartOf": { "@type": "WebSite", "name": "Daily MOO:conomy", "url": "https://mooconomy.co.kr" },
  "description": "매일 발행한 경제 질문과 다음 거래일 실제 결과를 공개합니다."
}
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "홈", "item": "https://mooconomy.co.kr/" },
    { "@type": "ListItem", "position": 2, "name": "MOO:Q 질문 기록", "item": "https://mooconomy.co.kr/questions/" }
  ]
}
</script>

<style>
  :root { --bg:#0B1220; --card:#141C2E; --ink:#E8ECF3; --sub:#95A2BA; --gold:#F2C94C; --line:rgba(124,138,165,.18); --up:#FF6B6B; --down:#5B8DEF; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',Arial,sans-serif; line-height:1.6; }
  .wrap { max-width:880px; margin:0 auto; padding:0 20px; }
  header.mh { padding:22px 0; border-bottom:1px solid var(--line); }
  .brand { font-size:18px; font-weight:800; text-decoration:none; color:var(--ink); }
  .brand .g { color:var(--gold); }
  nav.topnav { margin-top:12px; font-size:12.5px; }
  nav.topnav a { color:var(--sub); text-decoration:none; margin-right:16px; }
  nav.topnav a.current { color:var(--gold); font-weight:700; }
  nav.crumb { font-size:12px; color:var(--sub); margin-top:10px; }
  nav.crumb a { color:var(--sub); }
  main { padding:40px 0 64px; }
  .eyebrow { font-size:11px; font-weight:700; letter-spacing:.08em; color:var(--gold); text-transform:uppercase; margin-bottom:12px; }
  h1 { font-size:26px; line-height:1.4; margin:0 0 14px; word-break:keep-all; }
  .lead { font-size:14px; color:var(--sub); margin:0 0 32px; word-break:keep-all; max-width:640px; }
  .summary { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:40px; }
  @media (max-width:640px) { .summary { grid-template-columns:repeat(2,1fr); } }
  .stat { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .stat .n { font-size:22px; font-weight:800; color:var(--gold); }
  .stat .l { font-size:11.5px; color:var(--sub); margin-top:4px; }
  .qlist { display:flex; flex-direction:column; gap:12px; }
  .qcard { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px 18px; word-break:keep-all; }
  .qcard .qtext { font-size:14.5px; font-weight:700; margin-bottom:10px; }
  .qmeta { display:grid; grid-template-columns:repeat(2,1fr); gap:6px 16px; font-size:12px; color:#C7CEDB; margin-bottom:10px; }
  @media (max-width:640px) { .qmeta { grid-template-columns:1fr; } }
  .qmeta b { color:var(--sub); font-weight:600; }
  .verdict { display:inline-block; font-size:11px; font-weight:800; padding:3px 10px; border-radius:12px; }
  .verdict.hit { background:rgba(255,107,107,.14); color:var(--up); }
  .verdict.miss { background:rgba(91,141,239,.14); color:var(--down); }
  .verdict.neutral, .verdict.unresolved { background:rgba(149,162,186,.14); color:var(--sub); }
  .evidence { font-size:12.5px; color:#C7CEDB; margin-top:8px; padding-top:8px; border-top:1px solid var(--line); }
  .cta { margin-top:40px; font-size:13px; color:var(--sub); }
  .cta a { color:var(--gold); text-decoration:none; }
  footer { border-top:1px solid var(--line); padding:28px 0; font-size:12px; color:var(--sub); }
  footer a { color:var(--gold); text-decoration:none; }
  .disclaimer { font-size:11px; color:#6B7A99; margin-top:10px; }
</style>
</head>
<body>
  <header class="mh"><div class="wrap">
    <a class="brand" href="/">MOO<span class="g">:</span>conomy</a>
    <nav class="topnav">
      <a href="/">TODAY</a><a href="/questions/" class="current">QUESTIONS</a><a href="/methodology/">METHODOLOGY</a><a href="/#subscribe">SUBSCRIBE</a>
    </nav>
    <nav class="crumb"><a href="/">홈</a> / MOO:Q 질문 기록</nav>
  </div></header>

  <main class="wrap">
    <div class="eyebrow">QUESTIONS · MOO:Q ARCHIVE</div>
    <h1>오늘의 질문은 내일의 기록이 됩니다</h1>
    <p class="lead">MOO:Q는 발행 당시의 질문과 기준값을 고정하고, 다음 거래일 실제 결과를 공개하는 무코노미의 시장 질문 기록입니다.</p>

    <div class="summary">
      <div class="stat"><div class="n">__TOTAL__</div><div class="l">전체 질문</div></div>
      <div class="stat"><div class="n">__COMPLETED__</div><div class="l">판정 완료</div></div>
      <div class="stat"><div class="n">__PENDING__</div><div class="l">확인 중</div></div>
      <div class="stat"><div class="n">__HIT__·__NEUTRAL__·__MISS__·__UNRESOLVED__</div><div class="l">일치·부분일치·불일치·판단보류</div></div>
    </div>

__QUESTION_CARDS__

    <p class="cta">판정 기준과 데이터 처리 원칙은 <a href="/methodology/">방법론 페이지</a>에서 확인하세요.</p>
  </main>

  <footer><div class="wrap">
    Daily MOO:conomy · mooconomy.co.kr<br>
    © 2026 MOO:conomy. All rights reserved.
    <div class="disclaimer">MOO:Q는 투자 권유가 아니며, 발행 시점 데이터를 근거로 한 시장 관찰 기록입니다.</div>
  </div></footer>
</body>
</html>
"""

_CARD_TEMPLATE = """      <div class="qcard">
        <div class="qtext">__Q__</div>
        <div class="qmeta">
          <div><b>발행일</b> __ISSUED_AT__</div>
          <div><b>발행 시 기준값</b> __OBS_VALUE__ __OBS_UNIT__ (__OBS_ASOF__ 기준)</div>
          <div><b>예상 방향</b> __EXPECTED_DIR__</div>
          <div><b>확인 예정일</b> __CHECK_DUE__</div>
          <div><b>실제 결과</b> __RESULT__</div>
          <div><b>상태</b> <span class="verdict __VERDICT__">__VERDICT_LABEL__</span></div>
        </div>__EVIDENCE_BLOCK__
      </div>
"""


def _fmt_num(v):
    if v is None:
        return "—"
    return f"{v:,}" if isinstance(v, int) else f"{v:,.2f}"


def render_question_card(q):
    result_display = "확인 중" if q["result_value"] is None else f"{_fmt_num(q['result_value'])}{q.get('result_unit') or ''}"
    evidence_block = ""
    if q.get("evidence"):
        evidence_block = f'\n        <div class="evidence">{q["evidence"]}</div>'
    card = _CARD_TEMPLATE
    card = card.replace("__Q__", q["question"] or "—")
    card = card.replace("__ISSUED_AT__", (q.get("issued_at") or "—")[:10])
    card = card.replace("__OBS_VALUE__", _fmt_num(q.get("observation_value")))
    card = card.replace("__OBS_UNIT__", q.get("observation_unit") or "")
    card = card.replace("__OBS_ASOF__", q.get("observation_as_of") or "—")
    card = card.replace("__EXPECTED_DIR__", _DIRECTION_LABEL.get(q.get("expected_direction"), "—"))
    card = card.replace("__CHECK_DUE__", q.get("check_due_at") or "—")
    card = card.replace("__RESULT__", result_display)
    card = card.replace("__VERDICT__", q["verdict"])
    card = card.replace("__VERDICT_LABEL__", _VERDICT_LABEL.get(q["verdict"], q["verdict"]))
    card = card.replace("__EVIDENCE_BLOCK__", evidence_block)
    return card


def build_page(questions):
    """questions: question_records.json 내용(list). 발행일 역순 정렬."""
    ordered = sorted(questions, key=lambda q: q.get("issued_at") or "", reverse=True)
    cards = "".join(render_question_card(q) for q in ordered)
    counts = {"hit": 0, "miss": 0, "neutral": 0, "unresolved": 0}
    for q in questions:
        counts[q["verdict"]] = counts.get(q["verdict"], 0) + 1
    completed = counts["hit"] + counts["miss"] + counts["neutral"]

    html = _PAGE_HEAD
    html = html.replace("__TOTAL__", str(len(questions)))
    html = html.replace("__COMPLETED__", str(completed))
    html = html.replace("__PENDING__", str(counts["unresolved"]))
    html = html.replace("__HIT__", str(counts["hit"]))
    html = html.replace("__NEUTRAL__", str(counts["neutral"]))
    html = html.replace("__MISS__", str(counts["miss"]))
    html = html.replace("__UNRESOLVED__", str(counts["unresolved"]))
    html = html.replace("__QUESTION_CARDS__", f'    <div class="qlist">\n{cards}    </div>')
    return html


if __name__ == "__main__":
    import sys
    data_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/archive_export/dryrun_output/question_records.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "questions/index.html"
    with open(data_path, encoding="utf-8") as f:
        questions = json.load(f)
    html = build_page(questions)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(json.dumps({"written": out_path, "record_count": len(questions)}, ensure_ascii=False))
