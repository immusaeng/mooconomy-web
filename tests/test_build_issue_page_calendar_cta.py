# tests/test_build_issue_page_calendar_cta.py
"""2026-09-05(TASK_TRACK=NEWSLETTER_MOBILE_SHARE_AND_CALENDAR_CTA) —
build_issue_page.render_from_public_safe_email()이 삽입하는 캘린더 CTA
("다음 시장 이벤트가 궁금하다면? MOO:CALENDAR →")와 모바일 밀도 CSS의
영구 회귀 테스트. 실제 daily-mooconomy V8 이메일 템플릿 전체를 필요로
하지 않도록, 이 파일의 함수들이 실제로 찾는 구조적 앵커(.news-wrap,
<!-- MOO:VIEW -->, <table class="brand-wrap">, <title>, <style>, <head>,
<body>)만 담은 최소 fixture HTML을 쓴다(tests/test_build_issue_page_share.py와
같은 패턴). 네트워크·LLM 호출 없음.
실행: python -m unittest tests.test_build_issue_page_calendar_cta
"""
import copy
import os
import sys
import unittest

_ARCHIVE_EXPORT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "archive_export")
)
sys.path.insert(0, _ARCHIVE_EXPORT)

import build_issue_page as bip  # noqa: E402

CTA_TEXT = "다음 시장 이벤트가 궁금하다면? MOO:CALENDAR →"
CTA_HREF = "https://mooconomy.co.kr/calendar/"
CTA_MARKER = 'class="calendar-cta"'

_META = {
    "title": "테스트 발행 제목",
    "morning_thesis": "테스트 발행 제목",
    "published_at": "2026-09-05T06:41:00+09:00",
    "published_at_is_approximate": False,
    "public_path": "/issues/2026-09-05.html",
    "prev_path": "/issues/2026-09-04.html",
    "prev_date": "09-04",
    "next_path": None,
    "next_date": None,
}

# 실제 V8 이메일 템플릿의 구조(뉴스 -> MOO:VIEW -> MOO:Q -> ... -> </body>)만
# 최소로 재현한 fixture. 실 콘텐츠·색상·문구는 이 테스트의 관심사가 아니다.
_FIXTURE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta name="robots" content="noindex,follow">
<meta charset="UTF-8">
<title>Daily MOO:conomy</title>
<style>
  body { margin:0; }
  .sheet { width: 760px; max-width: 760px; min-width: 760px; }
</style>
</head>
<body bgcolor="#EFEAD9">
<div class="news-wrap">
  <table class="news-cols" role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr><td width="50%">DOMESTIC FIXTURE NEWS</td><td width="50%">GLOBAL FIXTURE NEWS</td></tr>
  </table>
</div>

<!-- ===== MOO:VIEW ===== -->
<table class="brand-wrap" role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr><td class="spacer" width="48">&nbsp;</td><td class="body">FIXTURE VIEW CONTENT</td></tr>
</table>

<table class="brand-wrap" role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr><td class="spacer" width="48">&nbsp;</td><td class="body">FIXTURE MOOQ CONTENT</td></tr>
</table>
</body>
</html>
"""


def _render(html=None, meta=None):
    return bip.render_from_public_safe_email(html if html is not None else _FIXTURE_HTML, copy.deepcopy(meta or _META))


class CalendarCtaContentTests(unittest.TestCase):
    """문구/href/출현 횟수/위치."""

    def test_cta_present_exactly_once(self):
        html = _render()
        self.assertEqual(html.count(CTA_MARKER), 1)

    def test_cta_exact_text_and_href(self):
        html = _render()
        expected = f'<div class="calendar-cta"><a href="{CTA_HREF}">{CTA_TEXT}</a></div>'
        self.assertIn(expected, html)

    def test_cta_sits_between_news_section_and_first_moo_view_card(self):
        html = _render()
        news_close_idx = html.index("</div>", html.index('class="news-wrap"'))
        cta_idx = html.index(CTA_MARKER)
        first_brand_wrap_idx = html.index('<table class="brand-wrap"')
        self.assertLess(news_close_idx, cta_idx, "CTA는 news-wrap이 닫힌 뒤에 와야 한다")
        self.assertLess(cta_idx, first_brand_wrap_idx, "CTA는 첫 MOO:VIEW 카드보다 앞에 와야 한다")

    def test_cta_does_not_precede_a_later_brand_wrap_card(self):
        # 두 번째 .brand-wrap(MOO:Q 등)에는 CTA가 붙지 않는다 — 정확히 1곳에만.
        html = _render()
        first_brand_wrap_idx = html.index('<table class="brand-wrap"')
        second_brand_wrap_idx = html.index('<table class="brand-wrap"', first_brand_wrap_idx + 1)
        between = html[first_brand_wrap_idx:second_brand_wrap_idx]
        self.assertNotIn(CTA_MARKER, between)


class WebOnlyRegressionTests(unittest.TestCase):
    """OG/canonical 유지, 원본 이메일 콘텐츠 무변경, 모바일 CSS 포함."""

    def test_og_and_canonical_preserved(self):
        html = _render()
        self.assertIn(
            '<link rel="canonical" href="https://mooconomy.co.kr/issues/2026-09-05.html">', html,
        )
        self.assertIn('<meta property="og:title"', html)
        self.assertIn(
            '<meta property="og:url" content="https://mooconomy.co.kr/issues/2026-09-05.html">', html,
        )

    def test_input_string_not_mutated(self):
        before = _FIXTURE_HTML
        _render()
        # 파이썬 str은 불변이지만, 함수가 전역/모듈 레벨 fixture를 실수로
        # 재바인딩하지 않는지까지 명시적으로 고정한다.
        self.assertEqual(_FIXTURE_HTML, before)

    def test_original_news_markup_survives_unmodified(self):
        html = _render()
        self.assertIn(
            '<table class="news-cols" role="presentation" cellpadding="0" cellspacing="0" width="100%">',
            html,
        )
        self.assertIn("DOMESTIC FIXTURE NEWS", html)
        self.assertIn("GLOBAL FIXTURE NEWS", html)
        self.assertIn("FIXTURE VIEW CONTENT", html)

    def test_mobile_density_css_included(self):
        html = _render()
        self.assertIn("@media (max-width:700px)", html)
        self.assertIn(
            '.news-cols, .news-cols > tbody, .news-cols > tbody > tr { display:block !important;', html,
        )
        self.assertIn(".calendar-cta {", html)


class CalendarCtaIdempotencyAndFailureTests(unittest.TestCase):
    """중복 호출 시 중복 방지 + 앵커 누락 시 명시적 실패."""

    def test_insert_calendar_cta_idempotent_on_repeated_call(self):
        once = bip._insert_calendar_cta(_FIXTURE_HTML)
        twice = bip._insert_calendar_cta(once)
        self.assertEqual(once, twice)
        self.assertEqual(twice.count(CTA_MARKER), 1)

    def test_missing_anchor_raises_explicit_error(self):
        broken_html = _FIXTURE_HTML.replace('class="brand-wrap"', 'class="renamed-wrap"')
        with self.assertRaises(bip.CalendarCtaAnchorMissingError):
            bip._insert_calendar_cta(broken_html)

    def test_render_from_public_safe_email_propagates_missing_anchor_error(self):
        broken_html = _FIXTURE_HTML.replace('class="brand-wrap"', 'class="renamed-wrap"')
        with self.assertRaises(bip.CalendarCtaAnchorMissingError):
            _render(html=broken_html)


if __name__ == "__main__":
    unittest.main()
