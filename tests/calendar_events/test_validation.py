import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from models import make_event  # noqa: E402
from validate import validate_canonical, validate_not_sample_data, check_future_events_not_suspiciously_empty  # noqa: E402


def _good_event(**overrides):
    base = dict(
        id="ev-1", title="CPI", country="US", category="inflation", importance="high",
        scheduledDate="2026-09-11", sourceName="FRED", sourceTier="official_aggregator",
        sourceUrl="https://example.com",
    )
    base.update(overrides)
    return make_event(**base)


class TestValidation(unittest.TestCase):
    def test_valid_dataset_has_no_issues(self):
        dataset = {"events": [_good_event()]}
        self.assertEqual(validate_canonical(dataset), [])

    def test_missing_source_url_flagged(self):
        ev = _good_event()
        ev["sourceUrl"] = ""
        issues = validate_canonical({"events": [ev]})
        self.assertTrue(any("sourceUrl" in i for i in issues))

    def test_missing_scheduled_date_flagged(self):
        ev = _good_event()
        ev["scheduledDate"] = ""
        issues = validate_canonical({"events": [ev]})
        self.assertTrue(any("scheduledDate" in i for i in issues))

    def test_duplicate_ids_flagged(self):
        ev1 = _good_event(id="dup")
        ev2 = _good_event(id="dup")
        issues = validate_canonical({"events": [ev1, ev2]})
        self.assertTrue(any("duplicate id" in i for i in issues))

    def test_invalid_country_flagged(self):
        ev = _good_event()
        ev["country"] = "XX"
        issues = validate_canonical({"events": [ev]})
        self.assertTrue(any("invalid country" in i for i in issues))

    def test_scheduled_at_must_be_tz_aware(self):
        ev = _good_event()
        ev["scheduledAt"] = "2026-09-11T12:00:00"  # naive, no offset
        issues = validate_canonical({"events": [ev]})
        self.assertTrue(any("not timezone-aware" in i for i in issues))

    def test_construction_rejects_missing_source_url(self):
        with self.assertRaises(ValueError):
            _good_event(sourceUrl="")

    def test_sample_data_flag_detected(self):
        issues = validate_not_sample_data({"_meta": {"sampleData": True}, "events": []})
        self.assertTrue(issues)

    def test_no_sample_flag_passes(self):
        self.assertEqual(validate_not_sample_data({"events": []}), [])

    def test_zero_events_with_failures_warns(self):
        dataset = {"events": [], "freshness": {"failedSources": ["fred"]}}
        issues = check_future_events_not_suspiciously_empty(dataset)
        self.assertTrue(issues)

    def test_nonzero_events_no_warning(self):
        dataset = {"events": [_good_event()], "freshness": {"failedSources": []}}
        self.assertEqual(check_future_events_not_suspiciously_empty(dataset), [])


if __name__ == "__main__":
    unittest.main()
