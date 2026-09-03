"""build_calendar.build()의 freshness 판정(fresh/partial/stale) + 부분
실패 시에도 성공한 소스 데이터는 살아남는지 확인한다. 실제 네트워크는
쓰지 않는다 - config를 만들어 fixture 모드로만 돌린다."""
import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from config import CalendarConfig  # noqa: E402
import build_calendar  # noqa: E402


class TestBuildFreshness(unittest.TestCase):
    def test_all_sources_via_fixtures_is_fresh(self):
        config = CalendarConfig(env={})
        dataset, summaries = build_calendar.build(config, use_fixtures=True)
        self.assertEqual(dataset["freshness"]["status"], "fresh")
        self.assertEqual(dataset["freshness"]["failedSources"], [])
        self.assertGreater(len(dataset["events"]), 0)

    def test_partial_when_some_sources_fail(self):
        config = CalendarConfig(env={})
        # fred만 성공하는 소스로 좁히고, 존재하지 않는 소스명을 섞어
        # "요청은 했는데 실패"인 상태를 시뮬레이션한다 — run_sources는
        # unknown_source를 ok=False로 표시하므로 partial 조건을 만든다.
        dataset, summaries = build_calendar.run_sources(
            config, use_fixtures=True, only_sources=["fred", "not-a-real-source"],
        )
        events, summ = dataset, summaries
        failed = [n for n, s in summ.items() if not s["ok"]]
        succeeded = [n for n, s in summ.items() if s["ok"] and s.get("count", 0) > 0]
        self.assertIn("not-a-real-source", failed)
        self.assertIn("fred", succeeded)

    def test_all_fail_yields_zero_events_not_fake_ones(self):
        config = CalendarConfig(env={})
        events, summaries = build_calendar.run_sources(
            config, use_fixtures=True, only_sources=["not-real-1", "not-real-2"],
        )
        self.assertEqual(events, [])
        self.assertTrue(all(not s["ok"] for s in summaries.values()))

    def test_disabled_source_excluded_cleanly(self):
        config = CalendarConfig(env={"CALENDAR_SOURCES": "fred"})
        self.assertFalse(config.is_enabled("fmp"))
        self.assertTrue(config.is_enabled("fred"))


if __name__ == "__main__":
    unittest.main()
