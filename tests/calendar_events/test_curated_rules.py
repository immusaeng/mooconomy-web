"""curated/rules 일정: 정확한 날짜, FOMC KST 시각(서머타임 전후), 만기일-휴장일 겹침. 외부 호출 없음."""
import os
import sys
import unittest
from datetime import date

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

import build_calendar  # noqa: E402
from config import CalendarConfig  # noqa: E402
from rules import load_curated, rule_events, expiry_date  # noqa: E402
from sources import fred  # noqa: E402
from validate import validate_canonical  # noqa: E402

CUR = {e["id"]: e for e in load_curated()}
HOL = {e["scheduledDate"] for e in CUR.values() if e["sourceName"] == "KRX"}


class TestCurated(unittest.TestCase):
    def test_bok_dates(self):
        got = sorted(e["scheduledDate"] for e in CUR.values() if e["sourceName"] == "BOK")
        self.assertEqual(got, ["2026-01-15", "2026-02-26", "2026-04-10", "2026-05-28",
                               "2026-07-16", "2026-08-27", "2026-10-22", "2026-11-26"])

    def test_fomc_kst_across_dst_end(self):
        # 14:00 ET: 서머타임(EDT) 중 -> KST 03:00, 종료(11-01) 후(EST) -> KST 04:00 (모두 다음 날)
        self.assertEqual(CUR["fomc-2026-09-16"]["scheduledAt"], "2026-09-17T03:00:00+09:00")
        self.assertEqual(CUR["fomc-2026-10-28"]["scheduledAt"], "2026-10-29T03:00:00+09:00")
        self.assertEqual(CUR["fomc-2026-12-09"]["scheduledAt"], "2026-12-10T04:00:00+09:00")
        self.assertEqual(CUR["fomc-2026-01-28"]["scheduledAt"], "2026-01-29T04:00:00+09:00")

    def test_krx_holidays_include_unlisted_ones(self):
        for d in ("2026-06-03", "2026-07-17", "2026-12-31"):
            self.assertIn(d, HOL)


class TestRules(unittest.TestCase):
    def test_expiry_plain_and_quad(self):
        ev = {e["scheduledDate"]: e for e in rule_events(date(2026, 9, 1), date(2026, 12, 31), HOL)
              if "Expiry" in e["title"]}
        self.assertIn("simultaneous", ev["2026-09-10"]["title"].lower())
        self.assertNotIn("simultaneous", ev["2026-10-08"]["title"].lower())
        self.assertIn("2026-12-10", ev)

    def test_expiry_on_holiday_moves_earlier(self):
        self.assertEqual(expiry_date(2026, 10, {"2026-10-08"}), date(2026, 10, 7))
        # 앞날도 휴장이면 계속 앞당김, 주말은 건너뜀
        self.assertEqual(expiry_date(2026, 10, {"2026-10-08", "2026-10-07", "2026-10-06"}), date(2026, 10, 5))
        self.assertEqual(expiry_date(2026, 10, {"2026-10-08", "2026-10-07", "2026-10-06", "2026-10-05"}), date(2026, 10, 2))

    def test_trade_release_first_of_month_incl_weekend(self):
        ev = [e["scheduledDate"] for e in rule_events(date(2026, 8, 1), date(2026, 10, 31), HOL) if e["category"] == "trade"]
        self.assertEqual(ev, ["2026-08-01", "2026-09-01", "2026-10-01"])  # 08-01은 토요일
        # 2026-11-01은 일요일 — 2024-12-01·2025-06-01·2026-02-01(모두 일요일)에 1일 발표 확인
        self.assertEqual([e["scheduledDate"] for e in rule_events(date(2026, 11, 1), date(2026, 11, 1), HOL) if e["category"] == "trade"], ["2026-11-01"])
        self.assertEqual([e for e in rule_events(date(2026, 5, 1), date(2026, 5, 1), HOL) if e["category"] == "trade"], [])


class TestBuild(unittest.TestCase):
    def test_build_merges_and_dedupes(self):
        ds, _ = build_calendar.build(CalendarConfig(env={}), use_fixtures=True)
        ids = [e["id"] for e in ds["events"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(validate_canonical(ds), [])
        self.assertTrue(any(e["id"].startswith("fomc-") or e["id"].startswith("bok-mpb-") for e in ds["events"]))

    def test_fred_time_and_importance(self):
        ev = fred.parse({"release_dates": [
            {"release_id": 10, "release_name": "Consumer Price Index", "date": "2026-10-14"},
            {"release_id": 192, "release_name": "JOLTS", "date": "2026-11-03"}]})
        self.assertEqual((ev[0]["importance"], ev[0]["scheduledAt"]), ("high", "2026-10-14T21:30:00+09:00"))
        self.assertEqual(ev[1]["scheduledAt"], "2026-11-04T00:00:00+09:00")  # 10:00 EST(서머타임 종료 후)
