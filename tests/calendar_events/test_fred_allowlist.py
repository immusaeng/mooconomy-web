"""FRED 허용 목록·페이지네이션·403 본문 마스킹·freshness 상태. 외부 호출 없음(requests.get mock)."""
import os
import sys
import unittest
from datetime import date, timedelta
from unittest import mock

_CAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "calendar_events"))
sys.path.insert(0, _CAL)

from config import CalendarConfig  # noqa: E402
import build_calendar  # noqa: E402
from sources import fred, fmp  # noqa: E402
from sources.base import SourceResult  # noqa: E402

KEY = "SECRETKEY1234567890"


class _Resp:
    def __init__(self, status=200, payload=None, text="", url="https://x/y?api_key=" + KEY):
        self.status_code, self._payload, self.text, self.url = status, payload, text, url
        self.ok = status < 400

    def json(self):
        return self._payload


def _config(**env):
    return CalendarConfig(env={"FRED_API_KEY": KEY, "FMP_API_KEY": KEY, **env})


def _rows(n, start, release_id="10"):
    return [{"release_id": release_id, "release_name": f"R{release_id}", "date": (start + timedelta(days=i % 40)).isoformat()}
            for i in range(n)]


def _pager(rows):
    def get(url, params=None, timeout=None):
        o = params["offset"]
        return _Resp(payload={"release_dates": rows[o:o + params["limit"]]})
    return get


class TestFredFetch(unittest.TestCase):
    def test_offset_loop_collects_1300_through_window_end(self):
        cfg = _config()
        start = date.today()
        end = (start + timedelta(days=cfg.lookahead_days)).isoformat()
        rows = _rows(1299, start) + [{"release_id": "10", "release_name": "CPI", "date": end}]
        with mock.patch("requests.get", side_effect=_pager(rows)) as g:
            events = fred.fetch(cfg)
        self.assertEqual(len(events), 1300)
        self.assertEqual(g.call_count, 2)
        self.assertIn(end, {e["scheduledDate"] for e in events})

    def test_allowlist_drops_noise(self):
        rows = _rows(3, date.today(), "10") + _rows(2, date.today(), "441") + _rows(2, date.today(), "200")
        with mock.patch("requests.get", side_effect=_pager(rows)):
            events = fred.fetch(_config())
        self.assertEqual({e["sourceEventId"] for e in events}, {"10"})

    def test_flag_zero_keeps_everything(self):
        rows = _rows(3, date.today(), "10") + _rows(2, date.today(), "441")
        with mock.patch("requests.get", side_effect=_pager(rows)):
            events = fred.fetch(_config(CAL_FRED_ALLOWLIST_ENABLED="0"))
        self.assertEqual(len(events), 5)

    def test_403_body_logged_and_masked(self):
        body = f"denied for key {KEY} " + "x" * 400
        resp = _Resp(403, text=body, url=f"https://financialmodelingprep.com/a?apikey={KEY}")
        with mock.patch("requests.get", return_value=resp):
            with self.assertRaises(RuntimeError) as cm:
                fmp.fetch(_config())
        msg = str(cm.exception)
        self.assertIn("403", msg)
        self.assertIn("denied for key", msg)
        self.assertNotIn(KEY, msg)
        self.assertLessEqual(len(msg.split("body=")[1]), 205)


class TestFreshness(unittest.TestCase):
    def test_disabled_and_not_implemented_do_not_make_partial(self):
        cfg = _config()
        ev = fred.parse({"release_dates": [{"release_id": 10, "release_name": "Consumer Price Index",
                                            "date": date.today().isoformat()}]})
        ok = lambda n, f, c: SourceResult(n, ev if n == "fred" else [])  # noqa: E731
        with mock.patch.object(build_calendar, "fetch_safe", side_effect=ok):
            dataset, summaries = build_calendar.build(cfg, use_fixtures=False)
        self.assertEqual(dataset["freshness"]["status"], "fresh")
        self.assertEqual(dataset["freshness"]["failedSources"], [])
        self.assertEqual(dataset["freshness"]["sources"]["fmp"], "disabled_plan_403")
        self.assertEqual(summaries["fmp"]["status"], "disabled_plan_403")
        self.assertEqual(summaries["finnhub"]["status"], "disabled_plan_403")
        self.assertEqual(summaries["ecos"]["status"], "not_implemented")
        self.assertEqual(summaries["kosis"]["status"], "not_implemented")
        self.assertTrue(all(s["ok"] for s in summaries.values()))

    def test_default_sources_exclude_fmp_finnhub(self):
        self.assertNotIn("fmp", CalendarConfig(env={}).sources)
        self.assertNotIn("finnhub", CalendarConfig(env={}).sources)


if __name__ == "__main__":
    unittest.main()
