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
# eyebrow 대비 위계가 깨지던 문제. renderCover()가 실측 줄바꿈 여부로
# .is-long을 토글하는 로직 자체는 실제 레이아웃 엔진(scrollHeight)이
# 필요해 이 저장소의 정적 테스트로는 실행할 수 없다(jsdom도 없음, 이미
# 다른 반응형 타이포 라운드에서 확인된 이 저장소의 제약) — 대신
# ShareScriptSourceTests와 동일한 방식(소스 문자열 검사)으로 로직/CSS가
# 실제로 존재하고 각 뷰포트 타이어에서 기본값보다 작은지만 고정한다.
class HeadlineLongTitleHierarchyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read("home-data.js")
        cls.css = read("styles.css")

    def test_render_cover_toggles_is_long_class(self):
        self.assertIn("classList.add('is-long')", self.js)
        self.assertIn("classList.remove('is-long')", self.js)
        self.assertIn("scrollHeight", self.js)

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
