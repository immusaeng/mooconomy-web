"""LINKED_PAGES_DATA_INTEGRITY_AND_DESIGN_RECOVERY 회귀 방지 테스트.

홈페이지에서 연결되는 하위 페이지들의 (a) 내부 링크가 실제 파일로
연결되는지, (b) 테스트/데모 페이지가 노출되지 않는지, (c) 하위 페이지가
구형 다크 셸 대신 홈페이지 공용 셸을 쓰는지, (d) MOO:Q 데이터에 단위
오류나 결측 레코드가 없는지를 정적으로 검사한다. 네트워크 호출 없음.
"""
import json
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


class InternalLinkTests(unittest.TestCase):
    def test_homepage_internal_links_resolve_to_files(self):
        html = read("index.html")
        hrefs = re.findall(r'href="(/[^"#?]*)"', html)
        missing = []
        for href in set(hrefs):
            if href == "/rss.xml":
                continue
            local = href.lstrip("/")
            candidates = [local, local + ".html", os.path.join(local, "index.html")]
            if not any(os.path.exists(os.path.join(ROOT, c)) for c in candidates if c):
                missing.append(href)
        self.assertEqual(missing, [], f"broken internal links from index.html: {missing}")


class MarketsWeeklyExposureTests(unittest.TestCase):
    def test_markets_page_is_noindex_and_has_no_demo_data(self):
        html = read("markets.html")
        self.assertIn('name="robots" content="noindex,nofollow"', html)
        self.assertNotIn("demoBanner", html)
        self.assertNotIn("투자 방향성", html)

    def test_weekly_page_is_public_and_leaks_no_internal_fields(self):
        # (2026-09-21 정책 변경) PR#14의 noindex 정책은 폐기됐다 — MOO:WEEKLY는
        # 이제 정식 공개 발행물이다. noindex 메타가 다시 생기지 않는지, 내부
        # JSON 필드명 같은 게 실수로 마크업에 새지 않는지만 고정 검증한다.
        html = read("weekly.html")
        self.assertNotIn('name="robots" content="noindex,nofollow"', html)
        self.assertNotIn("canonical_status=production", html)

    def test_homepage_has_no_markets_dashboard_cta(self):
        html = read("index.html")
        self.assertNotIn("마켓 대시보드 전체 보기", html)

    def test_weekly_and_w31_w32_source_data_preserved(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "data", "weekly", "index.json")))
        idx = json.loads(read("data/weekly/index.json"))
        week_ids = {w["week_id"] for w in idx["weeks"]}
        self.assertIn("2026-W31", week_ids)
        self.assertIn("2026-W32", week_ids)


class SharedShellMigrationTests(unittest.TestCase):
    def test_about_and_methodology_use_shared_shell(self):
        for path in ("about/index.html", "methodology/index.html"):
            html = read(path)
            self.assertIn("shared-shell.css", html, f"{path} missing shared-shell.css")
            self.assertIn('class="slim-header"', html, f"{path} missing slim-header shell")
            self.assertIn('class="mob-tabs"', html, f"{path} missing mobile bottom tabs")
            self.assertNotIn("--bg:#0B1220", html, f"{path} still has old dark-navy :root theme")

    def test_questions_archive_uses_shared_shell(self):
        html = read("questions/index.html")
        self.assertIn("shared-shell.css", html)
        self.assertIn('class="slim-header"', html)
        self.assertNotIn("--bg:#0B1220", html)


class MooQDataIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claims_store = json.loads(read("data/claims_store.json"))
        cls.claims = cls.claims_store["claims"]
        cls.records = json.loads(read("scripts/archive_export/dryrun_output/question_records.json"))
        cls.home = json.loads(read("data/home.json"))
        cls.questions_html = read("questions/index.html")

    def test_question_record_count_matches_claims_store(self):
        self.assertEqual(len(self.records), len(self.claims))

    def test_no_percent_unit_on_index_or_fx_results(self):
        """kospi/kosdaq/nasdaq/sp500/usdkrw는 '%'가 붙으면 안 된다
        (원 보고서에서 발견된 719.76%/1,443.80% 류 단위 오류)."""
        bad_units = {"kospi", "kosdaq", "nasdaq", "sp500"}
        for r in self.records:
            metric = self.claims[r["question_id"]]["metricId"]
            if metric in bad_units:
                self.assertEqual(r["observation_unit"], "")
                if r["result_value"] is not None:
                    self.assertEqual(r["result_unit"], "")
            if metric == "usdkrw":
                self.assertNotEqual(r["observation_unit"], "%")
                if r["result_value"] is not None:
                    self.assertNotEqual(r["result_unit"], "%")

    def test_no_missing_records_between_claims_store_and_archive_page(self):
        # claimId 문자열 자체는 렌더되지 않으므로(질문 문구만 표시) 카드 개수로 검증한다.
        self.assertEqual(self.questions_html.count('class="qcard"'), len(self.claims))
        for c in self.claims.values():
            self.assertIn(c["claimText"], self.questions_html, f"claim text missing from questions/index.html: {c['claimText']!r}")

    def test_home_json_claims_populated_from_claims_store(self):
        claims = self.home.get("claims")
        self.assertIsNotNone(claims, "home.json.claims is null — homepage MOO:Q card will stay hidden")
        self.assertTrue(claims["previousClaims"], "no previousClaims — homepage MOO:Q card has nothing to show")
        latest = claims["previousClaims"][0]
        self.assertTrue(latest.get("claimText"))
        resolved = [c for c in self.claims.values() if c.get("status") != "unresolved"]
        newest_resolved = sorted(resolved, key=lambda c: c.get("issuedAt") or "")[-1]
        self.assertEqual(latest["claimText"], newest_resolved["claimText"])


# (TASK_ID=WEEKLY_CH1_REVERT_AND_CARD_REAL_DATA, 2026-09-21, CEO 지시)
# 2026-09-21 오전 커밋(d2a6f10)이 월요일마다 홈 CH·I("Today's Edition")을
# 위클리 커버로 바꾸는 분기를 넣었는데, 같은 날 CEO가 그 전제 자체를
# 폐기했다 — CH·I은 항상 데일리 전용 슬롯이다. 되돌린 뒤 다시 새지
# 않도록 고정.
class ChapterOneStaysDailyOnlyTests(unittest.TestCase):
    def test_home_data_js_has_no_weekly_hero_branch(self):
        js = read("home-data.js")
        for marker in ("isMondayKST", "renderWeeklyHero", "This Week's Edition", "WEEKLY ·"):
            self.assertNotIn(marker, js, f"CH·I hero-swap-to-weekly branch leaked back in: {marker!r}")

    def test_render_cover_only_reads_daily_manifest(self):
        js = read("home-data.js")
        m = re.search(r"function renderCover\(.*?\n  \}\n", js, re.DOTALL)
        self.assertIsNotNone(m, "renderCover() not found")
        body = m.group(0)
        self.assertNotIn("weekly", body.lower())


class WeeklyCardNoPlaceholderTests(unittest.TestCase):
    def test_no_summary_pending_placeholder_string_anywhere(self):
        # (2026-09-21 CEO 지시) 문자열 자체를 코드베이스에 남기지 않는다 --
        # 특정 파일 하나만 검사하면 다른 곳에 재도입돼도 못 잡으므로 추적
        # 대상 텍스트/스크립트 확장자 전체를 훑는다.
        placeholder = "요약 준비 중"
        self_path = os.path.abspath(__file__)
        hits = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "_build_tmp")]
            for fname in filenames:
                if not fname.endswith((".html", ".js", ".py", ".css")):
                    continue
                path = os.path.join(dirpath, fname)
                if os.path.abspath(path) == self_path:
                    continue  # 이 테스트 자신은 검사 대상 문자열을 리터럴로 담고 있다
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if placeholder in content:
                    hits.append(os.path.relpath(path, ROOT))
        self.assertEqual(hits, [], f"placeholder string leaked back into: {hits}")

    def test_weekly_card_renders_no_summary_line(self):
        # (2026-09-23 CEO 지시) 주간 카드는 "데일리 N건 집계 · 코스피 +X%…" 요약
        # 줄을 렌더 코드에서 아예 만들지 않는다(CSS 숨김 아님).
        with open(os.path.join(ROOT, "home-data.js"), encoding="utf-8") as f:
            js = f.read()
        body = js[js.index("async function renderWeeklyRecent"):]
        body = body[:body.index("\n  }\n")]
        self.assertNotIn("source_edition_count", body)
        self.assertNotIn("headline_metrics", body)

    def test_headline_metrics_equal_weekly_level_diff(self):
        # (2026-09-24) 주간 등락률 단일 정의 -- index.json headline_metrics는
        # 각 주 JSON의 weekly_scorecard_level_diff 값 그대로여야 한다.
        with open(os.path.join(ROOT, "data", "weekly", "index.json"), encoding="utf-8") as f:
            idx = json.load(f)
        for w in idx["weeks"]:
            with open(os.path.join(ROOT, "data", "weekly", w["week_id"] + ".json"), encoding="utf-8") as f:
                rec = json.load(f)
            ld = {m["metric_id"]: m["weekly_change_percent"]
                  for m in rec["weekly_scorecard_level_diff"]["metrics"]}
            for m in w["headline_metrics"]:
                self.assertEqual(m["weekly_change_percent"], ld[m["metric_id"]], w["week_id"])

    def test_weekly_card_uses_real_headline_metrics_when_present(self):
        with open(os.path.join(ROOT, "data", "weekly", "index.json"), encoding="utf-8") as f:
            idx = json.load(f)
        canonical = [w for w in idx["weeks"] if w.get("has_canonical_page")]
        self.assertTrue(canonical, "no canonical weeks to check against")
        for w in canonical:
            self.assertIn("headline_metrics", w)
            self.assertIn("source_edition_count", w)
            for m in w["headline_metrics"]:
                self.assertIn(m["metric_id"], ("kospi", "nasdaq"))
                self.assertIsNotNone(m["weekly_change_percent"])


# (TASK_ID=CS_HEADLINE_LONG_TITLE_HIERARCHY, 2026-09-21) CH·I 헤드라인이
# 길어 2줄 이상 줄바꿈될 때 TODAY'S HEADLINE 라벨/CH·I TODAY'S ANGLE
# eyebrow 대비 위계가 깨지던 문제.
#
# **이 테스트가 약한 이유를 정직하게 기록한다**: 최초 구현은 이 소스
# 문자열 검사를 전부 통과했는데도 라이브에서 완전히 무효했다(사용자가
# 스크린샷으로 재현 보고, 2026-09-21) — 실제 버그 둘 다(클래스가
# id="csHeadline"인 <a>에 붙었는데 CSS 선택자 .cs-headline.is-long은
# 부모 <h2>를 요구해 매치 자체가 안 됨; scrollHeight가 인라인 <a>에서
# 0을 반환) 문자열 검사로는 원천적으로 못 잡는 종류였다 -- 헤드리스
# Chrome으로 --dump-dom(렌더 후 DOM)을 직접 읽어서만 발견·확인했다
# (`chrome.exe --headless --disable-gpu --dump-dom --virtual-time-budget=4000
# --window-size=1280,900 <url> | grep 'cs-headline'`, 이 저장소가 jsdom도
# CI의 실브라우저 테스트도 없어 자동화하지 못했다 -- 이전 반응형 타이포
# 라운드들과 같은 제약). 아래는 그래서 "이 두 특정 버그가 다시 나타나면"
# 만이라도 잡도록 최소한으로 강화한 것이지, .is-long이 실제로 렌더에
# 반영된다는 걸 증명하지 않는다 -- 이 로직을 다시 건드릴 때는 반드시
# 위 명령으로 직접 재검증할 것.
class HeadlineLongTitleHierarchyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read("home-data.js")
        cls.css = read("styles.css")

    def test_render_cover_toggles_is_long_class_on_the_element_with_the_css_class(self):
        self.assertIn("classList.add('is-long')", self.js)
        self.assertIn("classList.remove('is-long')", self.js)
        # 버그 1 회귀 방지: .is-long은 반드시 .closest('.cs-headline')로
        # 찾은(또는 그 자신인) 요소에 붙어야 한다 -- #csHeadline(<a>)
        # 자신에 직접 붙이면 CSS .cs-headline.is-long이 매치되지 않는다.
        self.assertIn("closest('.cs-headline')", self.js)

    def test_wrap_detection_uses_offsetheight_not_scrollheight(self):
        # 버그 2 회귀 방지: scrollHeight는 인라인 요소(<a>)에서 0을
        # 반환해(실측 확인) 줄바꿈이 항상 "아니오"로 판정됐다.
        self.assertIn("offsetHeight", self.js)
        # 판정 조건 자체(> headlineLH * 1.5)에 쓰이는 속성이 scrollHeight가
        # 아님을 직접 확인 -- 이 파일에 다른 목적의 scrollHeight가 생기는
        # 것까지 막지는 않되, is-long 판정 조건 줄에는 없어야 한다.
        m = re.search(r"headlineEl\.(scrollHeight|offsetHeight)\s*>\s*headlineLH", self.js)
        self.assertIsNotNone(m, "wrap-detection condition not found")
        self.assertEqual(m.group(1), "offsetHeight")

    def test_css_defines_smaller_size_per_tier(self):
        # 각 (base, is-long) 쌍에서 is-long이 항상 더 작아야 한다 --
        # 하드코딩된 숫자를 바꾸는 다음 사람이 실수로 역전시키면 잡는다.
        pairs = re.findall(
            r'\.cs-headline(?:\.is-long)?\s*\{[^}]*?font-size:\s*(\d+)px', self.css)
        # 소스 순서: base 34, is-long 28, (1279)base 32, is-long 26,
        # (1023)base 30, is-long 24, (767)base 27, is-long 22,
        # (390)base 26, is-long 21 -- 쌍으로 묶어 비교.
        self.assertEqual(len(pairs) % 2, 0, pairs)
        for i in range(0, len(pairs), 2):
            base, long_ = int(pairs[i]), int(pairs[i + 1])
            self.assertLess(long_, base, f"tier {i//2}: is-long({long_}) not smaller than base({base})")


if __name__ == "__main__":
    unittest.main()
