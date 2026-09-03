"""2026-09-03(TASK_ID=HOMEPAGE_VISIBLE_ACTIVATION_FIX)
index.html의 지정된 정적 fallback 블록(마커 사이)만 data/home.json +
data/archive/issues_manifest.json으로 갱신한다. 전체 index.html을
재작성하지 않는다 — home-data.js가 나중에 같은 데이터로 다시 덮어쓰지만,
JS 비활성 크롤러/브라우저도 최신 발행판 제목·날짜·시그널·canonical
링크를 보게 하려는 것뿐이다.

마커(index.html 안에 이미 있음):
  <!-- STATIC:COVER:START --> ... <!-- STATIC:COVER:END -->
  <!-- STATIC:DAILY_RECENT:START --> ... <!-- STATIC:DAILY_RECENT:END -->
  id="subProofCount" 내용(마커 없이 id로 직접 치환)

결정적(deterministic): 같은 입력이면 항상 같은 바이트를 만든다 —
현재 시각이나 무작위 값을 쓰지 않는다. 두 번 연속 실행해도 diff가
없어야 한다(idempotent).

외부 네트워크·LLM 호출 없음. home.json/manifest는 읽기만 한다.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INDEX_PATH = os.path.join(ROOT, "index.html")
HOME_JSON_PATH = os.path.join(ROOT, "data", "home.json")
MANIFEST_PATH = os.path.join(ROOT, "data", "archive", "issues_manifest.json")


def _esc(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_md(iso_date):
    # "2026-09-03" -> "09.03" — home-data.js의 fmtMD()와 동일 규칙.
    parts = (iso_date or "").split("-")
    if len(parts) != 3:
        return iso_date or ""
    return f"{parts[1]}.{parts[2]}"


def build_cover_block(home, manifest):
    latest = manifest[-1] if manifest else None
    if latest:
        headline = latest["title"]
        href = latest.get("public_path") or f"/issues/{latest['issue_date']}.html"
        flag_r = f"발행 · {_fmt_md(latest['issue_date'])}"
    else:
        headline = "오늘의 발행판을 준비 중입니다"
        href = "/latest.html"
        flag_r = ""

    signals = [
        s for s in (home.get("dailyThree") or []) if s and s.get("status") == "ok" and s.get("text")
    ] if home else []

    sig_items = "\n".join(
        f'            <li><span class="sig-idx">{i + 1:02d}</span><span class="sig-txt">'
        f'<b>{_esc(s["title"])}</b> — {_esc(s["text"])}</span></li>'
        for i, s in enumerate(signals)
    )

    return (
        f'<!-- STATIC:COVER:START -->\n'
        f'          <span class="cs-flag-r" id="csFlagR">{_esc(flag_r)}</span>\n'
        f'        </div>\n'
        f'        <div class="cs-kicker">CH · I  Today\'s Angle</div>\n'
        f'        <h1 class="cs-headline"><a id="csHeadline" href="{_esc(href)}">{_esc(headline)}</a></h1>\n'
        f'        <p class="cs-deck" id="csDeck"></p>\n'
        f'\n'
        f'        <div class="cs-signals" id="csSignalsBlock">\n'
        f'          <div class="sig-title">Today\'s 3 Signals</div>\n'
        f'          <ol class="sig-list" id="sigList">\n'
        f'{sig_items}\n'
        f'          </ol>'
    )


def build_daily_recent_block(manifest):
    recent = list(reversed(manifest[-3:])) if manifest else []
    if not recent:
        items = '            <li class="rc-empty">발행 기록이 없습니다.</li>'
    else:
        items = "\n".join(
            f'            <li><a href="{_esc(m.get("public_path") or f"/issues/{m["issue_date"]}.html")}">'
            f'<span class="date">{_fmt_md(m["issue_date"])}</span><span class="title">{_esc(m["title"])}</span></a></li>'
            for m in recent
        )
    return f'<!-- STATIC:DAILY_RECENT:START -->\n          <ul id="dailyRecent">\n{items}\n          </ul>'


def apply(html, home, manifest):
    cover_html = build_cover_block(home, manifest)
    html = re.sub(
        r"<!-- STATIC:COVER:START -->.*?(?=\s*<!-- STATIC:COVER:END -->)",
        cover_html.replace("\\", "\\\\"),
        html,
        count=1,
        flags=re.S,
    )

    daily_html = build_daily_recent_block(manifest)
    html = re.sub(
        r"<!-- STATIC:DAILY_RECENT:START -->.*?(?=\s*<!-- STATIC:DAILY_RECENT:END -->)",
        daily_html.replace("\\", "\\\\"),
        html,
        count=1,
        flags=re.S,
    )

    count = len(manifest)
    html = re.sub(
        r'(id="subProofCount">)[^<]*(</b>)',
        rf"\g<1>{count}\g<2>",
        html,
        count=1,
    )
    return html


def main():
    with open(HOME_JSON_PATH, encoding="utf-8") as f:
        home = json.load(f)
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    with open(INDEX_PATH, encoding="utf-8") as f:
        html = f.read()

    new_html = apply(html, home, manifest)

    if new_html == html:
        print("no change (already up to date)", file=sys.stderr)
        return
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"updated {INDEX_PATH}: cover headline / {len(manifest)} manifest entries reflected", file=sys.stderr)


if __name__ == "__main__":
    main()
