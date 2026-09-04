"""questions/index.html 정적 생성기(읽기 전용 입력, 결정론적 출력).

scripts/archive_export/dryrun_output/question_records.json(export.py의
build_question_record() 출력, claims_store.json 전 건 그대로)만 읽는다 —
질문·결과 문구를 새로 쓰지 않고 원본 그대로 렌더링한다. JavaScript 없이
전체 본문이 HTML에 그대로 존재한다.

셸(헤더·브레드크럼·푸터·모바일 탭)은 홈페이지가 쓰는 shared-shell.css +
styles.css를 그대로 재사용한다(calendar/index.html과 동일 패턴) — 이
페이지만의 다크 테마를 새로 만들지 않는다.
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,700;0,9..144,800;1,9..144,400;1,9..144,700;1,9..144,800&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../styles.css?v=b5d18e1">
<link rel="stylesheet" href="../shared-shell.css?v=b5d18e1">
<link rel="stylesheet" href="questions.css?v=b5d18e1">
</head>
<body data-root="../">

<div class="ticker-bar" aria-label="실시간 시장 지표">
  <div class="ticker-inner" id="tickerInner"></div>
</div>

<header class="slim-header">
  <div class="slim-header-inner">
    <a href="/" class="sh-brand">
      <span class="sh-brand-mark">MOO<span class="colon">:</span>conomy</span>
      <span class="sh-brand-tag">DAILY · EST. 2026</span>
    </a>
    <nav class="sh-nav">
      <a href="/">홈</a>
      <a href="/archive/">아카이브</a>
      <a href="/calendar/">캘린더</a>
      <a href="/questions/" class="active" aria-current="page">MOO<span class="colon">:</span>Q</a>
      <a href="/about/">About</a>
    </nav>
    <a href="/#subscribe" class="sh-cta">구독하기</a>
  </div>
</header>

<nav class="breadcrumb" aria-label="위치">
  <a href="/">Home</a>
  <span class="bc-sep">›</span>
  <span class="bc-current">MOO:Q 질문 기록</span>
</nav>

<div class="page-header">
  <div class="ph-eyebrow">MOO<span class="colon" style="color:var(--gold)">:</span>Q · 질문과 검증의 아카이브</div>
  <h1 class="ph-title">오늘의 <em>질문</em>은 내일의 기록이 됩니다</h1>
  <p class="ph-lede">MOO:Q는 발행 당시의 질문과 기준값을 고정하고, 다음 거래일 실제 결과를 공개하는 무코노미의 시장 질문 기록입니다. 빗나간 질문도 숨기거나 지우지 않습니다.</p>
  <div class="ph-meta">
    <span>전체 <b>__TOTAL__</b>건</span>
    <span class="ph-meta-sep"></span>
    <span>판정 완료 <b>__COMPLETED__</b>건 · 확인 중 <b>__PENDING__</b>건</span>
    <span class="ph-meta-sep"></span>
    <span>일치 <b>__HIT__</b> · 부분일치 <b>__NEUTRAL__</b> · 불일치 <b>__MISS__</b> · 판단보류 <b>__UNRESOLVED__</b></span>
  </div>
</div>

<main class="page-wrap">

__QUESTION_CARDS__

  <p style="font-family:var(--sans);font-size:13px;color:var(--muted);margin-top:8px;">판정 기준과 데이터 처리 원칙은 <a href="/methodology/" style="color:var(--gold-deep);">방법론 페이지</a>에서 확인하세요.</p>

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
      <span>Daily MOO:conomy · EST. 2026</span>
      <span>월 Weekly · 화–토 Daily · 오전 7시</span>
    </div>
  </div>
</footer>

<nav class="mob-tabs" aria-label="주요 페이지">
  <div class="mob-tabs-inner">
    <a class="mt-item" href="/"><span class="mt-icon i-home"></span><span class="mt-label">홈</span></a>
    <a class="mt-item" href="/archive/"><span class="mt-icon i-archive"></span><span class="mt-label">아카이브</span></a>
    <a class="mt-item" href="/calendar/"><span class="mt-icon i-calendar"></span><span class="mt-label">캘린더</span></a>
    <a class="mt-item active" href="/questions/" aria-current="page"><span class="mt-icon i-q"></span><span class="mt-label">MOO:Q</span></a>
    <a class="mt-item" href="/about/"><span class="mt-icon i-about"></span><span class="mt-label">About</span></a>
  </div>
</nav>

<script src="../app.js?v=b5d18e1"></script>
</body>
</html>
"""

_CARD_TEMPLATE = """    <div class="qcard">
      <div class="mc-q">__Q__</div>
      <div class="qmeta">
        <div><b>발행일</b> __ISSUED_AT__</div>
        <div><b>발행 시 기준값</b> __OBS_VALUE__ (__OBS_ASOF__ 기준)</div>
        <div><b>예상 방향</b> __EXPECTED_DIR__</div>
        <div><b>확인 예정일</b> __CHECK_DUE__</div>
      </div>
      <div class="mc-verdict-row">
        <span class="mc-verdict __VERDICT__">__VERDICT_LABEL__</span>
        <span class="mc-values">실제 결과 __RESULT__</span>
      </div>__EVIDENCE_BLOCK__
    </div>
"""


def _fmt_num(v):
    if v is None:
        return "—"
    return f"{v:,}" if isinstance(v, int) else f"{v:,.2f}"


def _fmt_unit_value(value, unit):
    """단위가 '$'면 숫자 앞에, 그 외(원/%p/pt)는 숫자 뒤에 붙인다
    (home-data.js IND_META.absPrefix와 동일 관례 — $만 접두)."""
    n = _fmt_num(value)
    if n == "—" or not unit:
        return n
    return f"{unit}{n}" if unit == "$" else f"{n}{unit}"


def render_question_card(q):
    result_display = "확인 중" if q["result_value"] is None else _fmt_unit_value(q["result_value"], q.get("result_unit"))
    evidence_block = ""
    if q.get("evidence"):
        evidence_block = f'\n      <div class="qevidence">{q["evidence"]}</div>'
    card = _CARD_TEMPLATE
    card = card.replace("__Q__", q["question"] or "—")
    card = card.replace("__ISSUED_AT__", (q.get("issued_at") or "—")[:10])
    card = card.replace("__OBS_VALUE__", _fmt_unit_value(q.get("observation_value"), q.get("observation_unit")))
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
    html = html.replace("__QUESTION_CARDS__", f'  <div class="qlist">\n{cards}  </div>')
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
