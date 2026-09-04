"""Market Pulse 404 제거 회귀 테스트(HOMEPAGE_DATA_REFRESH_AND_CONSOLE_HYGIENE §A).

실제 repo를 임시 디렉터리로 복사해 정적 서버로 띄우고 Playwright로
홈페이지를 로드해 검증한다 — 실제 data/history/를 절대 건드리지 않는다.
시나리오별로 임시 사본의 data/history/만 변형한다(주말/연속 휴장일/
데이터 누락/manifest 손상). 외부 네트워크·LLM 호출 없음.
"""
import contextlib
import datetime as dt
import functools
import http.server
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import unittest

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "home_prerender"))
import build_history_index  # noqa: E402


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@contextlib.contextmanager
def _served_site_copy(mutate=None):
    """ROOT 전체를 임시 디렉터리에 복사(약 5MB) 후 정적 서버로 서빙한다.
    mutate(tmp_root)로 사본의 data/history/를 시나리오별로 바꾼다."""
    tmp_root = tempfile.mkdtemp(prefix="mooq_pulse_site_")
    httpd = None
    thread = None
    try:
        shutil.copytree(
            ROOT, tmp_root, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "_build_tmp*", ".pytest_cache"),
        )
        if mutate:
            mutate(tmp_root)
        port = _free_port()
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp_root)
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{port}", tmp_root
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
        shutil.rmtree(tmp_root, ignore_errors=True)


def _ymd_minus(date_str, days):
    return (dt.date.fromisoformat(date_str) - dt.timedelta(days=days)).isoformat()


def _reference_nearest_on_or_before(history_dir, date_str, max_lookback=7):
    """home-data.js의 fetchNearestOnOrBefore()와 동일 알고리즘의 독립
    Python 재구현 — 선택 결과가 그대로인지 교차 검증하는 기준선."""
    for i in range(max_lookback + 1):
        ds = _ymd_minus(date_str, i)
        if os.path.exists(os.path.join(history_dir, f"{ds}.json")):
            return ds
    return None


def _reference_pulse_values(tmp_root, ind_ids):
    history_dir = os.path.join(tmp_root, "data", "history")
    with open(os.path.join(tmp_root, "data", "home.json"), encoding="utf-8") as f:
        publish_date = json.load(f)["publishDate"]
    end_obs = _reference_nearest_on_or_before(history_dir, publish_date)
    start_obs = _reference_nearest_on_or_before(history_dir, _ymd_minus(publish_date, 14))
    if not end_obs or not start_obs:
        return None

    def load_val(date_str, ind_id):
        with open(os.path.join(history_dir, f"{date_str}.json"), encoding="utf-8") as f:
            rec = json.load(f)
        for ind in rec.get("indicators", []):
            if ind.get("id") == ind_id:
                return ind.get("value")
        return None

    return {
        "start_date": start_obs, "end_date": end_obs,
        "values": {i: (load_val(start_obs, i), load_val(end_obs, i)) for i in ind_ids},
    }


class MarketPulseConsoleHygieneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def _load(self, base_url):
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        history_404s = []
        all_requests = {"count": 0}

        def on_response(resp):
            if "/data/history/" in resp.url:
                all_requests["count"] += 1
                if resp.status == 404:
                    history_404s.append(resp.url)

        page.on("response", on_response)
        page.goto(base_url + "/", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(800)
        cards = page.eval_on_selector_all(
            ".pulse-card",
            "els => els.map(el => ({"
            "name: el.querySelector('.pc-name').textContent,"
            "start: el.querySelector('.pulse-start .pulse-value').textContent,"
            "current: el.querySelector('.pulse-current .pulse-value').textContent,"
            "startDate: el.querySelector('.pulse-start .pulse-date').textContent,"
            "endDate: el.querySelector('.pulse-current .pulse-date').textContent"
            "}))",
        )
        pulse_empty_hidden = page.evaluate("document.getElementById('pulseEmpty').hidden")
        pulse_empty_text = page.evaluate("document.getElementById('pulseEmpty').textContent")
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        page.close()
        return {
            "history_404s": history_404s, "history_request_count": all_requests["count"],
            "cards": cards, "pulse_empty_hidden": pulse_empty_hidden,
            "pulse_empty_text": pulse_empty_text, "overflow": overflow,
        }

    # ── 1. 정상(현재 저장소 데이터, 실제 08-24/08-30/08-31 주말·휴장일 갭 포함) ──
    def test_baseline_real_data_zero_404_and_values_match_reference(self):
        with _served_site_copy() as (base_url, tmp_root):
            result = self._load(base_url)
            ref = _reference_pulse_values(tmp_root, ["kospi", "kosdaq", "usdkrw"])
            self.assertEqual(result["history_404s"], [])
            self.assertGreater(len(result["cards"]), 0)
            self.assertIsNotNone(ref)
            card_dates = {(c["startDate"], c["endDate"]) for c in result["cards"]}
            expected_dates = (ref["start_date"][5:].replace("-", "."), ref["end_date"][5:].replace("-", "."))
            self.assertEqual(card_dates, {expected_dates})
            kospi_card = next(c for c in result["cards"] if c["name"] == "코스피")
            self.assertEqual(kospi_card["start"], f"{ref['values']['kospi'][0]:,.2f}")
            self.assertEqual(kospi_card["current"], f"{ref['values']['kospi'][1]:,.2f}")

    # ── 2. 연속 휴장일(장기 연휴 시뮬레이션: endTarget 앞 3일 연속 삭제) ──
    def test_consecutive_holiday_gap_still_resolves_and_zero_404(self):
        def mutate(tmp_root):
            history_dir = os.path.join(tmp_root, "data", "history")
            with open(os.path.join(tmp_root, "data", "home.json"), encoding="utf-8") as f:
                publish_date = json.load(f)["publishDate"]
            for i in range(3):
                ds = _ymd_minus(publish_date, i)
                p = os.path.join(history_dir, f"{ds}.json")
                if os.path.exists(p):
                    os.remove(p)
            build_history_index.write_index(history_dir, os.path.join(history_dir, "index.json"))

        with _served_site_copy(mutate) as (base_url, tmp_root):
            result = self._load(base_url)
            ref = _reference_pulse_values(tmp_root, ["kospi"])
            self.assertEqual(result["history_404s"], [])
            self.assertIsNotNone(ref, "3일 연속 삭제는 maxLookback=7 이내라 여전히 값을 찾아야 함")
            self.assertGreater(len(result["cards"]), 0)
            kospi_card = next(c for c in result["cards"] if c["name"] == "코스피")
            self.assertEqual(kospi_card["endDate"], ref["end_date"][5:].replace("-", "."))

    # ── 3. lookback을 넘는 데이터 누락 -> 크래시 없이 "부족" 안내로 종료 ──
    def test_data_missing_beyond_lookback_shows_unavailable_not_crash(self):
        def mutate(tmp_root):
            history_dir = os.path.join(tmp_root, "data", "history")
            with open(os.path.join(tmp_root, "data", "home.json"), encoding="utf-8") as f:
                publish_date = json.load(f)["publishDate"]
            for i in range(9):  # maxLookback(7)보다 넉넉히 크게 전부 삭제
                ds = _ymd_minus(publish_date, i)
                p = os.path.join(history_dir, f"{ds}.json")
                if os.path.exists(p):
                    os.remove(p)
            build_history_index.write_index(history_dir, os.path.join(history_dir, "index.json"))

        with _served_site_copy(mutate) as (base_url, tmp_root):
            result = self._load(base_url)
            self.assertEqual(result["history_404s"], [])
            self.assertEqual(result["cards"], [])
            self.assertFalse(result["pulse_empty_hidden"])
            self.assertIn("부족", result["pulse_empty_text"])
            # 무한 재시도 방지: index가 건강하면 요청 수가 작게 bound돼야 한다
            # (maxLookback 8회 x 2경계 이내 — 실제로는 index가 전부 스킵해 0에 가깝다).
            self.assertLessEqual(result["history_request_count"], 20)

    # ── 4. index.json 손상 -> 예전 방식(직접 fetch)으로 안전하게 폴백,
    #        값 자체는 baseline과 동일해야 한다(선택 결과 불변) ──
    def test_corrupt_index_json_falls_back_and_keeps_correct_values(self):
        def mutate(tmp_root):
            index_path = os.path.join(tmp_root, "data", "history", "index.json")
            with open(index_path, "w", encoding="utf-8") as f:
                f.write("{ not valid json ]")

        with _served_site_copy(mutate) as (base_url, tmp_root):
            result = self._load(base_url)
            ref = _reference_pulse_values(tmp_root, ["kospi"])
            self.assertGreater(len(result["cards"]), 0)
            kospi_card = next(c for c in result["cards"] if c["name"] == "코스피")
            self.assertEqual(kospi_card["start"], f"{ref['values']['kospi'][0]:,.2f}")
            self.assertEqual(kospi_card["current"], f"{ref['values']['kospi'][1]:,.2f}")
            # 폴백 경로는 요청 수가 유한(무한 재시도 아님)한지만 확인한다 —
            # 이 경로에서는 404가 다시 나올 수 있다(그게 안전한 폴백의 정의).
            self.assertLessEqual(result["history_request_count"], 30)

    # ── 5. index.json 부재 -> 동일하게 안전한 폴백 ──
    def test_missing_index_json_falls_back_and_keeps_correct_values(self):
        def mutate(tmp_root):
            os.remove(os.path.join(tmp_root, "data", "history", "index.json"))

        with _served_site_copy(mutate) as (base_url, tmp_root):
            result = self._load(base_url)
            ref = _reference_pulse_values(tmp_root, ["kospi"])
            self.assertGreater(len(result["cards"]), 0)
            kospi_card = next(c for c in result["cards"] if c["name"] == "코스피")
            self.assertEqual(kospi_card["current"], f"{ref['values']['kospi'][1]:,.2f}")
            self.assertLessEqual(result["history_request_count"], 30)

    # ── 6. 360/390/768/1280px 가로 overflow 0 ──
    def test_responsive_overflow_zero_across_breakpoints(self):
        for width in (360, 390, 768, 1280):
            with _served_site_copy() as (base_url, tmp_root):
                page = self.browser.new_page(viewport={"width": width, "height": 900})
                page.goto(base_url + "/", wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(500)
                overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                page.close()
                self.assertEqual(overflow, 0, f"overflow at {width}px")


if __name__ == "__main__":
    unittest.main()
