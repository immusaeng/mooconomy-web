import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from importance import classify_importance, cross_check_importance  # noqa: E402


class TestImportance(unittest.TestCase):
    def test_high_keywords(self):
        self.assertEqual(classify_importance("US Nonfarm Payrolls"), "high")
        self.assertEqual(classify_importance("한국은행 금융통화위원회 기준금리 결정"), "high")
        self.assertEqual(classify_importance("Consumer Price Index (CPI) m/m"), "high")

    def test_medium_keywords(self):
        self.assertEqual(classify_importance("US Retail Sales m/m"), "medium")
        self.assertEqual(classify_importance("Manufacturing PMI"), "medium")

    def test_low_default(self):
        self.assertEqual(classify_importance("Some minor regional survey"), "low")

    def test_unknown_for_empty_title(self):
        self.assertEqual(classify_importance(""), "unknown")
        self.assertEqual(classify_importance(None), "unknown")

    def test_cross_check_flags_mismatch(self):
        warning = cross_check_importance("FOMC Rate Decision", "low")
        self.assertIsNotNone(warning)
        self.assertIn("rule=high", warning)

    def test_cross_check_no_warning_when_matching(self):
        self.assertIsNone(cross_check_importance("FOMC Rate Decision", "high"))

    def test_cross_check_none_when_source_unknown(self):
        self.assertIsNone(cross_check_importance("FOMC Rate Decision", "unknown"))
        self.assertIsNone(cross_check_importance("FOMC Rate Decision", None))


if __name__ == "__main__":
    unittest.main()
