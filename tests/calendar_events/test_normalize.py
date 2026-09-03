import os
import sys
import unittest
from datetime import datetime, timezone, timedelta

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from normalize import build_event_id, to_utc_iso, now_utc_iso  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_build_event_id_is_deterministic(self):
        id1 = build_event_id("fred", "US", "Consumer Price Index", "2026-09-11")
        id2 = build_event_id("fred", "US", "Consumer Price Index", "2026-09-11")
        self.assertEqual(id1, id2)

    def test_build_event_id_differs_by_date(self):
        id1 = build_event_id("fred", "US", "CPI", "2026-09-11")
        id2 = build_event_id("fred", "US", "CPI", "2026-09-12")
        self.assertNotEqual(id1, id2)

    def test_build_event_id_is_slug_safe(self):
        eid = build_event_id("fmp", "KR", "한국 CPI (%)", "2026-09-11")
        self.assertNotIn(" ", eid)
        self.assertTrue(eid.startswith("fmp-"))

    def test_to_utc_iso_requires_tzaware(self):
        naive = datetime(2026, 9, 11, 12, 0, 0)
        with self.assertRaises(ValueError):
            to_utc_iso(naive)

    def test_to_utc_iso_converts(self):
        kst = datetime(2026, 9, 11, 21, 30, 0, tzinfo=timezone(timedelta(hours=9)))
        result = to_utc_iso(kst)
        self.assertTrue(result.startswith("2026-09-11T12:30:00"))

    def test_now_utc_iso_is_aware(self):
        s = now_utc_iso()
        dt = datetime.fromisoformat(s)
        self.assertIsNotNone(dt.tzinfo)


if __name__ == "__main__":
    unittest.main()
