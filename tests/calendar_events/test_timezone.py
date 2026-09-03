import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from normalize import utc_iso_to_kst_date  # noqa: E402


class TestTimezone(unittest.TestCase):
    def test_midnight_crossing_forward(self):
        # UTC 15:30 -> KST(+9) 다음날 00:30
        self.assertEqual(utc_iso_to_kst_date("2026-09-11T15:30:00+00:00"), "2026-09-12")

    def test_same_day_when_early_utc(self):
        # UTC 01:00 -> KST 10:00, 같은 날
        self.assertEqual(utc_iso_to_kst_date("2026-09-11T01:00:00+00:00"), "2026-09-11")

    def test_naive_datetime_assumed_utc(self):
        # tz 정보 없는 입력도 UTC로 간주해 처리한다(크래시하지 않는다).
        self.assertEqual(utc_iso_to_kst_date("2026-09-11T15:30:00"), "2026-09-12")


if __name__ == "__main__":
    unittest.main()
