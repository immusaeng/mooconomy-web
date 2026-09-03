import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from models import make_event  # noqa: E402
from merge import merge_events  # noqa: E402


def _ev(source, tier, title, date_="2026-09-11", **kw):
    return make_event(
        id=f"{source}-{title}-{date_}",
        title=title, country="US", category="macro", importance="high",
        scheduledDate=date_, sourceName=source, sourceTier=tier,
        sourceUrl=f"https://example.com/{source}", **kw,
    )


class TestMerge(unittest.TestCase):
    def test_dedups_same_event_across_sources(self):
        events = [
            _ev("FRED", "official_aggregator", "Consumer Price Index"),
            _ev("FMP", "commercial", "Consumer Price Index"),
            _ev("Finnhub", "commercial", "Consumer Price Index"),
        ]
        merged = merge_events(events)
        self.assertEqual(len(merged), 1)
        self.assertEqual(len(merged[0]["sourceRefs"]), 3)

    def test_keeps_distinct_events_separate(self):
        events = [
            _ev("FRED", "official_aggregator", "Consumer Price Index"),
            _ev("FRED", "official_aggregator", "Nonfarm Payrolls"),
        ]
        merged = merge_events(events)
        self.assertEqual(len(merged), 2)

    def test_official_source_wins_scheduled_date_fields(self):
        official = _ev("BOK", "official", "Rate Decision", scheduledAt="2026-09-11T03:00:00+00:00", timePrecision="datetime")
        commercial = _ev("FMP", "commercial", "Rate Decision", scheduledAt="2026-09-11T05:00:00+00:00", timePrecision="datetime")
        merged = merge_events([commercial, official])  # 순서 섞여도 우선순위로 정렬됨
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["scheduledAt"], "2026-09-11T03:00:00+00:00")
        self.assertEqual(merged[0]["sourceName"], "BOK")

    def test_fills_missing_time_from_lower_priority_source(self):
        official_no_time = _ev("BOK", "official", "Rate Decision")  # scheduledAt=None by default
        commercial_with_time = _ev("FMP", "commercial", "Rate Decision", scheduledAt="2026-09-11T05:00:00+00:00", timePrecision="datetime")
        merged = merge_events([official_no_time, commercial_with_time])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["scheduledAt"], "2026-09-11T05:00:00+00:00")
        self.assertEqual(merged[0]["confidence"], "cross_checked")

    def test_close_dates_within_one_day_merge(self):
        events = [
            _ev("FRED", "official_aggregator", "Consumer Price Index", date_="2026-09-11"),
            _ev("FMP", "commercial", "Consumer Price Index", date_="2026-09-12"),
        ]
        merged = merge_events(events)
        self.assertEqual(len(merged), 1)

    def test_far_dates_do_not_merge(self):
        events = [
            _ev("FRED", "official_aggregator", "Consumer Price Index", date_="2026-09-11"),
            _ev("FMP", "commercial", "Consumer Price Index", date_="2026-10-11"),
        ]
        merged = merge_events(events)
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
