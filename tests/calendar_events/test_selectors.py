import os
import sys
import unittest
from datetime import date

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from models import make_event, make_canonical_dataset  # noqa: E402
from selectors import build_home_view, build_daily_view, build_weekly_view  # noqa: E402


def _ev(title, days_from_today, importance="high", scheduled_at=None):
    d = date(2026, 9, 3)
    from datetime import timedelta
    target = d + timedelta(days=days_from_today)
    return make_event(
        id=f"ev-{title}-{days_from_today}", title=title, country="US", category="macro",
        importance=importance, scheduledDate=target.isoformat(), scheduledAt=scheduled_at,
        sourceName="FRED", sourceTier="official_aggregator", sourceUrl="https://example.com",
    )


def _dataset(events):
    return make_canonical_dataset(
        generatedAt="2026-09-03T00:00:00+00:00", timezone="Asia/Seoul",
        range_from="2026-08-27", range_to="2026-10-18",
        freshness={"status": "fresh", "lastSuccessfulAt": "2026-09-03T00:00:00+00:00", "failedSources": []},
        sources=[], events=events,
    )


class TestSelectors(unittest.TestCase):
    TODAY = date(2026, 9, 3)

    def test_home_view_includes_next_14_days_only(self):
        events = [_ev("in-range", 5), _ev("today", 0), _ev("too-far", 20)]
        dataset = _dataset(events)
        view = build_home_view(dataset, self.TODAY)
        titles = {e["title"] for e in view["events"]}
        self.assertIn("in-range", titles)
        self.assertIn("today", titles)
        self.assertNotIn("too-far", titles)

    def test_home_view_sorts_high_first(self):
        events = [_ev("low-imp", 1, importance="low"), _ev("high-imp", 3, importance="high")]
        dataset = _dataset(events)
        view = build_home_view(dataset, self.TODAY)
        self.assertEqual(view["events"][0]["title"], "high-imp")

    def test_daily_view_limits_to_48h_high_medium(self):
        events = [_ev("soon-high", 1, importance="high"), _ev("soon-low", 1, importance="low"), _ev("far", 5, importance="high")]
        dataset = _dataset(events)
        view = build_daily_view(dataset, self.TODAY)
        titles = {e["title"] for e in view["events"]}
        self.assertIn("soon-high", titles)
        self.assertNotIn("soon-low", titles)  # low importance excluded from daily view
        self.assertNotIn("far", titles)

    def test_weekly_view_groups_by_date(self):
        events = [_ev("d1", 1), _ev("d2", 1), _ev("d3", 3)]
        dataset = _dataset(events)
        view = build_weekly_view(dataset, self.TODAY)
        self.assertEqual(len(view["byDate"]), 2)  # 두 날짜에 걸쳐 그룹

    def test_empty_dataset_returns_empty_events_not_fake_ones(self):
        dataset = _dataset([])
        for builder in (build_home_view, build_daily_view, build_weekly_view):
            view = builder(dataset, self.TODAY)
            self.assertEqual(view["events"], [])

    def test_views_carry_freshness_through(self):
        dataset = _dataset([])
        dataset["freshness"]["status"] = "partial"
        view = build_home_view(dataset, self.TODAY)
        self.assertEqual(view["freshness"]["status"], "partial")


if __name__ == "__main__":
    unittest.main()
