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
            if href in ("/rss.xml", "/feed.xml"):
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

    def test_weekly_page_is_noindex_and_not_presented_as_published(self):
        html = read("weekly.html")
        self.assertIn('name="robots" content="noindex,nofollow"', html)
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


if __name__ == "__main__":
    unittest.main()
