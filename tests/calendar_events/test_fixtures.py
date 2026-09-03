import json
import os
import sys
import unittest

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
_SOURCES = os.path.join(_CAL, "sources")
_FIXTURES = os.path.join(_CAL, "fixtures")
sys.path.insert(0, _CAL)
sys.path.insert(0, _SOURCES)

import fred, fmp, finnhub, eia, dart  # noqa: E402
import bok  # noqa: E402
from validate import validate_canonical  # noqa: E402


def _load_json(name):
    with open(os.path.join(_FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


class TestSourceFixtureParsing(unittest.TestCase):
    """각 소스 adapter의 parse()를 raw fixture로 돌려본다 — 네트워크 없음."""

    def test_fred_parses_fixture(self):
        events = fred.parse(_load_json("fred.sample.json"))
        self.assertGreater(len(events), 0)
        self.assertEqual(validate_canonical({"events": events}), [])
        for ev in events:
            self.assertEqual(ev["sourceName"], "FRED")
            self.assertEqual(ev["sourceTier"], "official_aggregator")

    def test_fmp_parses_fixture(self):
        events = fmp.parse(_load_json("fmp.sample.json"))
        self.assertGreater(len(events), 0)
        self.assertEqual(validate_canonical({"events": events}), [])
        for ev in events:
            self.assertEqual(ev["sourceTier"], "commercial")

    def test_finnhub_parses_fixture(self):
        events = finnhub.parse(_load_json("finnhub.sample.json"))
        self.assertGreater(len(events), 0)
        self.assertEqual(validate_canonical({"events": events}), [])

    def test_eia_parses_fixture(self):
        events = eia.parse(_load_json("eia.sample.json"))
        self.assertGreater(len(events), 0)
        for ev in events:
            self.assertEqual(ev["status"], "released")  # 미래 예정 아님
            self.assertIsNotNone(ev["actual"])

    def test_dart_parses_fixture(self):
        events = dart.parse(_load_json("dart.sample.json"))
        self.assertGreater(len(events), 0)
        for ev in events:
            self.assertEqual(ev["status"], "published")
            self.assertEqual(ev["category"], "disclosure")

    def test_bok_parses_html_fixture(self):
        with open(os.path.join(_FIXTURES, "bok.sample.html"), encoding="utf-8") as f:
            html = f.read()
        events = bok.parse_html(html)
        self.assertGreaterEqual(len(events), 2)
        for ev in events:
            self.assertEqual(ev["sourceName"], "BOK")
            self.assertEqual(ev["sourceTier"], "official")

    def test_dart_malformed_response_raises_not_crashes_silently(self):
        with self.assertRaises(RuntimeError):
            dart.parse({"status": "800", "message": "unauthorized"})

    def test_dart_no_results_status_returns_empty(self):
        self.assertEqual(dart.parse({"status": "013", "message": "no data"}), [])

    def test_fmp_non_list_payload_returns_empty(self):
        self.assertEqual(fmp.parse({"error": "invalid key"}), [])

    def test_parse_is_idempotent(self):
        payload = _load_json("fred.sample.json")
        first = fred.parse(payload)
        second = fred.parse(payload)
        self.assertEqual([e["id"] for e in first], [e["id"] for e in second])


if __name__ == "__main__":
    unittest.main()
