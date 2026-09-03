# tests/test_build_issue_page_share.py
"""2026-09-03(TASK_ID=NEWSLETTER_EDITORIAL_COMPLETION_AND_WEB_SHARE §F)
scripts/archive_export/build_issue_page.py의 공유 위젯 회귀 테스트.
실제 브라우저 클릭은 검증하지 않는다(JS 실행 환경 없음) — 생성된 HTML/
JS 소스에 요구 조건이 실제로 있는지, canonical 누락 시 빌드가 실패하는지
확인한다."""
import os
import sys
import unittest

_ARCHIVE_EXPORT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "archive_export"),
)
sys.path.insert(0, _ARCHIVE_EXPORT)

import build_issue_page as bip  # noqa: E402


def _meta(public_path="/issues/2026-09-03.html", title="테스트 발행", prev_path=None, next_path=None):
    return {
        "public_path": public_path, "title": title,
        "morning_thesis": None, "published_at": "2026-09-03T06:41:00+09:00",
        "published_at_is_approximate": False,
        "prev_path": prev_path, "prev_date": "2026-09-02" if prev_path else None,
        "next_path": next_path, "next_date": None,
    }


_MINIMAL_EMAIL_HTML = (
    "<!DOCTYPE html><html><head><title>Daily MOO:conomy</title>"
    "<style>body{margin:0}</style></head>"
    '<body><h1 class="hero-headline">테스트 헤드라인</h1><p>본문</p></body></html>'
)


class ShareScriptSourceTests(unittest.TestCase):
    """§F 웹 동작 요구사항이 실제 JS 소스에 있는지 확인한다."""

    def test_canonical_link_used_not_window_location_primary(self):
        # canonicalEl.href가 url의 1차 소스여야 한다(window.location은 폴백만).
        self.assertIn("canonicalEl ? canonicalEl.href", bip._SHARE_SCRIPT)

    def test_exact_success_message_present(self):
        self.assertIn("링크를 복사했습니다. 카카오톡에 붙여넣어 공유해 주세요.", bip._SHARE_SCRIPT)

    def test_clipboard_failure_shows_selectable_url_not_just_error_text(self):
        self.assertIn("showSelectableUrl", bip._SHARE_SCRIPT)
        self.assertIn("input.select()", bip._SHARE_SCRIPT)

    def test_buttons_are_type_button_not_anchor(self):
        self.assertIn('<button type="button" data-fx-share', bip._SHARE_BUTTONS_HTML)
        self.assertIn('<button type="button" data-fx-copy', bip._SHARE_BUTTONS_HTML)
        self.assertNotIn("<a ", bip._SHARE_BUTTONS_HTML)

    def test_no_latest_html_href_in_share_buttons(self):
        self.assertNotIn("/latest.html", bip._SHARE_BUTTONS_HTML)
        self.assertNotIn("/latest.html", bip._SHARE_SCRIPT)

    def test_top_and_bottom_widgets_use_same_script_and_data_attrs(self):
        self.assertIn("data-fx-share", bip._TOP_SHARE_HTML)
        self.assertIn("data-fx-share", bip._SHARE_BUTTONS_HTML)
        self.assertIn("data-fx-copy", bip._TOP_SHARE_HTML)
        self.assertIn("data-fx-copy", bip._SHARE_BUTTONS_HTML)


class CanonicalBuildFailureTests(unittest.TestCase):
    """canonical(public_path) 누락 시 런타임 폴백이 아니라 빌드 자체가
    실패해야 한다(§F "canonical이 없으면... 빌드 검증을 실패시킨다")."""

    def test_missing_public_path_raises_in_public_safe_email_path(self):
        meta = _meta(public_path=None)
        with self.assertRaises(bip.MissingCanonicalPathError):
            bip.render_from_public_safe_email(_MINIMAL_EMAIL_HTML, meta)

    def test_missing_public_path_raises_in_json_record_path(self):
        meta = _meta(public_path="")
        record = {"thesis": {}, "main_story": {}, "narratives": {}, "sources": [], "metrics": []}
        with self.assertRaises(bip.MissingCanonicalPathError):
            bip.render_from_json_record(record, {**meta, "issue_date": "2026-09-03"})

    def test_present_public_path_does_not_raise(self):
        meta = _meta(public_path="/issues/2026-09-03.html")
        html = bip.render_from_public_safe_email(_MINIMAL_EMAIL_HTML, meta)
        self.assertIn(
            '<link rel="canonical" href="https://mooconomy.co.kr/issues/2026-09-03.html">', html,
        )


class RenderedPageShareWidgetTests(unittest.TestCase):
    """실제 render_from_public_safe_email() 출력물에 공유 위젯·canonical이
    함께 들어있는지 end-to-end로 확인한다(latest.html이 이 함수의 결과를
    그대로 복사한다는 전제와 일치 — 같은 HTML이면 같은 canonical을 갖고,
    canonical이 항상 날짜별 URL이므로 latest.html도 자동으로 올바른
    공유 URL을 갖는다)."""

    def test_canonical_and_share_widgets_both_present(self):
        meta = _meta(public_path="/issues/2026-09-03.html")
        html = bip.render_from_public_safe_email(_MINIMAL_EMAIL_HTML, meta)
        self.assertIn('rel="canonical"', html)
        self.assertIn("data-fx-share", html)
        self.assertIn("data-fx-copy", html)
        self.assertIn("<script>", html)

    def test_past_issue_canonical_is_self_not_latest(self):
        # /issues/2026-08-28.html 처럼 과거 발행판을 렌더해도 canonical은
        # 자기 자신의 날짜를 가리켜야 한다(최신 뉴스레터로 절대 이동 안 함).
        meta = _meta(public_path="/issues/2026-08-28.html")
        html = bip.render_from_public_safe_email(_MINIMAL_EMAIL_HTML, meta)
        self.assertIn(
            '<link rel="canonical" href="https://mooconomy.co.kr/issues/2026-08-28.html">', html,
        )
        self.assertNotIn("/issues/2026-09-03.html", html)


if __name__ == "__main__":
    unittest.main()
