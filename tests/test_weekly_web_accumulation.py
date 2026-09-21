"""(TASK_ID=WEEKLY_WEB_ACCUMULATION, 2026-09-21, CEO 지시) 위클리 발행본이
sitemap.xml/rss.xml/아카이브 타임라인에 daily와 함께 누적되는지 회귀
검증. 합성 fixture가 아니라 이 저장소의 실제 data/weekly/*.json을 그대로
읽는다(_load_weekly_web_entries 자체가 그렇게 설계됨, W31/W32처럼
canonical 페이지가 없는 주가 실제로 섞여 있는 상태를 검증하는 게 이
테스트의 핵심이라 합성 데이터로는 그 부분을 재현하기 애매하다).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "archive_export"))
import publish_issue_archive as pia  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class WeeklyWebEntriesTests(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "data", "weekly", "index.json"), encoding="utf-8") as f:
            self.index = json.load(f)
        self.entries = pia._load_weekly_web_entries()

    def test_only_canonical_weeks_included(self):
        canonical_ids = {w["week_id"] for w in self.index["weeks"] if w.get("has_canonical_page")}
        entry_ids = {e["public_path"].rsplit("/", 1)[-1][:-5] for e in self.entries}
        self.assertEqual(entry_ids, canonical_ids)
        # W31/W32는 파이프라인 이전 fixture(canonical 페이지 없음) -- 반드시 빠져야 한다
        self.assertNotIn("2026-W31", entry_ids)
        self.assertNotIn("2026-W32", entry_ids)

    def test_entries_have_daily_manifest_shape(self):
        for e in self.entries:
            for key in ("issue_date", "public_path", "title", "morning_thesis", "published_at"):
                self.assertIn(key, e)
            self.assertTrue(e["public_path"].startswith("/weekly/"))
            self.assertRegex(e["issue_date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_missing_index_returns_empty_not_raise(self):
        original = pia.WEEKLY_DATA_DIR
        pia.WEEKLY_DATA_DIR = os.path.join(ROOT, "data", "no-such-weekly-dir")
        try:
            self.assertEqual(pia._load_weekly_web_entries(), [])
        finally:
            pia.WEEKLY_DATA_DIR = original


class OrchestratorDryRunIncludesWeeklyTests(unittest.TestCase):
    """실제 스크립트 run()을 dry_run_report_only=True로 돌려, 위클리가
    sitemap/rss/아카이브 산출물에 실제로 섞여 들어가는지 end-to-end 확인.
    dry-run이라 _build_tmp/ 밖의 실제 공개 경로는 건드리지 않는다."""

    @classmethod
    def setUpClass(cls):
        cls.report = pia.run(dry_run_report_only=True)

    def test_no_abort(self):
        self.assertFalse(self.report.get("aborted"), self.report.get("abort_reason"))

    def test_weekly_entry_count_matches_canonical_weeks(self):
        with open(os.path.join(ROOT, "data", "weekly", "index.json"), encoding="utf-8") as f:
            index = json.load(f)
        canonical_count = sum(1 for w in index["weeks"] if w.get("has_canonical_page"))
        self.assertEqual(self.report.get("weekly_web_entry_count"), canonical_count)

    def test_sitemap_and_rss_valid_with_weekly_included(self):
        self.assertEqual(self.report["xml_issues"]["sitemap.xml"], [])
        self.assertEqual(self.report["xml_issues"]["rss.xml"], [])
        with open(os.path.join(pia.BUILD_TMP, "sitemap.xml"), encoding="utf-8") as f:
            sitemap = f.read()
        with open(os.path.join(pia.BUILD_TMP, "rss.xml"), encoding="utf-8") as f:
            rss = f.read()
        self.assertIn("/weekly/2026-W38.html", sitemap)
        self.assertNotIn("2026-W31", sitemap)
        self.assertNotIn("2026-W32", sitemap)
        self.assertIn("/weekly/2026-W38.html", rss)

    def test_daily_manifest_unaffected_by_weekly(self):
        # issues_manifest.json(daily 전용 계약)에는 위클리가 섞이면 안 된다.
        with open(os.path.join(pia.BUILD_TMP, "issues_manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        self.assertTrue(all("/weekly/" not in m["public_path"] for m in manifest))


if __name__ == "__main__":
    unittest.main()
