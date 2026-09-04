"""2026-08-24(TASK_ID=W6_WEEKLY_WEB_WIRING)
/weekly/{week_id}.html 정적 생성기 — build_issue_page.py의 daily 렌더
경로(render_from_public_safe_email)와 같은 원칙(본문은 절대 재작성하지
않고, <head>에 canonical/OG를, </body> 앞에 공유 버튼+prev/next만 삽입)
을 위클리에 적용한다.

build_issue_page._nav_block()을 그대로 재사용하지 않는 이유: 그 함수는
"전체 발행 목록 보기" 링크가 daily 아카이브(/archive/)로 고정돼 있어
위클리에 그대로 쓰면 엉뚱한 곳으로 링크된다. OG 메타(_og_meta_block)·
공유 버튼(_SHARE_BUTTONS_HTML/_SHARE_SCRIPT)·CSS(_SHARE_CSS/_NAV_CSS)는
daily 전용 가정이 없는 순수 유틸이라 그대로 가져다 쓴다 — 이 파일에서
새로 만드는 건 위클리 전용 nav 뿐이다.

daily의 render_from_json_record()(발송 HTML이 없는 과거 날짜용 재구성
경로)에 대응하는 위클리 버전은 없다 — 위클리는 아직 발행 히스토리가
짧고, "실이메일 HTML이 없는 과거 주"를 다시 조립해야 할 일이 아직
없어서 지금은 만들지 않는다(필요해지면 daily와 동일 패턴으로 추가).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import build_issue_page as bip


def _weekly_nav_block(meta):
    prev_link = (f'<a href="{meta["prev_path"]}">← {meta["prev_week_id"]}</a>'
                 if meta.get("prev_path") else '<span></span>')
    next_link = (f'<a href="{meta["next_path"]}">{meta["next_week_id"]} →</a>'
                 if meta.get("next_path") else '<span></span>')
    return (
        f'<div class="fx-issue-nav">{prev_link}{next_link}</div>'
        f'<div class="fx-archive-link"><a href="/weekly.html">전체 위클리 목록 보기</a></div>'
    )


def render_weekly_page(safe_html, meta):
    """safe_html: 이미 개인정보 스크럽을 통과한 위클리 발송 HTML.
    meta: week_id/public_path/title/morning_thesis/published_at/
    published_at_is_approximate/prev_path/prev_week_id/next_path/
    next_week_id 키를 갖는 dict(publish_weekly_archive.py가 구성).

    2026-09-04(TASK_ID=WEEKLY_PHASE0_RUNTIME_SAFETY, C) — build_issue_page.py의
    2026-09-03/04 리팩터(ARCHIVE_ISSUE_V8_SHELL_UNIFICATION_REBASE)가
    _og_meta_block/_SHARE_BUTTONS_HTML/_SHARE_CSS를 _head_meta_block/
    _action_bar_html(meta)/_ACTION_BAR_CSS로 이름을 바꿨는데, 이 파일은
    갱신되지 않아 실행 시 AttributeError로 죽고 있었다(테스트가 이
    경로를 커버하지 않아 발견이 늦음, 감사 docs/weekly-quality-audit.md
    F-3). 아래는 이름만 새 심볼로 맞춘 것 — 동작(주입 위치·순서)은
    이전과 동일하게 유지한다."""
    html = safe_html
    fact = (meta.get("morning_thesis") or meta.get("title") or "")[:150]
    meta_block = bip._head_meta_block(meta, fact)
    html = html.replace("</title>", "</title>\n" + meta_block, 1)
    html = html.replace(
        "</style>\n",
        "</style>\n<style>" + bip._ACTION_BAR_CSS + bip._NAV_CSS + "</style>\n", 1,
    )
    injected = bip._action_bar_html(meta) + _weekly_nav_block(meta) + bip._SHARE_SCRIPT
    if "</body>" in html:
        html = html.replace("</body>", f'<div class="inner">{injected}</div>\n</body>', 1)
    else:
        html += injected
    return html
