"""판정 라벨 통일 회귀 테스트(HOMEPAGE_DATA_REFRESH_AND_CONSOLE_HYGIENE §C).

home-data.js의 VERDICT_LABEL(JS 객체 리터럴, 손으로 유지)과
scripts/archive_export/verdict_labels.py(Python 단일 진실 공급원)가
어긋나면 실패한다 — 두 언어라 import로 공유할 수 없어 이 테스트가
드리프트 감시 역할을 한다. 홈/questions/methodology 세 화면의 실제 배지·
설명 문구가 같은 용어를 쓰는지도 함께 확인한다.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "archive_export"))
import verdict_labels  # noqa: E402


def _read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def _extract_js_verdict_label():
    js = _read("home-data.js")
    m = re.search(r"var VERDICT_LABEL = \{([^}]*)\};", js)
    assert m, "home-data.js에서 VERDICT_LABEL 객체 리터럴을 찾지 못함"
    body = m.group(1)
    pairs = re.findall(r"(\w+):\s*'([^']*)'", body)
    return dict(pairs)


class VerdictLabelConsistencyTests(unittest.TestCase):
    def test_standard_taxonomy_matches_ceo_spec(self):
        self.assertEqual(verdict_labels.DISPLAY_LABEL, {
            "MATCH": "적중",
            "PARTIAL_MATCH": "부분 적중",
            "MISMATCH": "불일치",
            "NEUTRAL": "중립",
            "PENDING": "판정 대기",
        })

    def test_unknown_status_raises_not_silently_mapped(self):
        with self.assertRaises(verdict_labels.UnknownVerdictError):
            verdict_labels.label_for_status("some_future_status_nobody_defined")

    def test_known_statuses_resolve_to_expected_labels(self):
        expected = {
            "hit": "적중", "miss": "불일치", "neutral": "중립",
            "unresolved": "판정 대기", "invalidated": "판정 대기", "error": "판정 대기",
        }
        for status, label in expected.items():
            self.assertEqual(verdict_labels.label_for_status(status), label)

    def test_home_data_js_verdict_label_matches_python_source_of_truth(self):
        js_map = _extract_js_verdict_label()
        for status, py_label in [
            ("hit", verdict_labels.label_for_status("hit")),
            ("miss", verdict_labels.label_for_status("miss")),
            ("neutral", verdict_labels.label_for_status("neutral")),
            ("unresolved", verdict_labels.label_for_status("unresolved")),
            ("invalidated", verdict_labels.label_for_status("invalidated")),
            ("error", verdict_labels.label_for_status("error")),
        ]:
            self.assertIn(status, js_map, f"home-data.js VERDICT_LABEL에 '{status}' 키 없음")
            self.assertEqual(js_map[status], py_label,
                              f"home-data.js와 verdict_labels.py가 '{status}'에서 어긋남: "
                              f"{js_map[status]!r} != {py_label!r}")

    def test_questions_archive_badges_use_unified_labels(self):
        html = _read("questions/index.html")
        # "일치"는 "불일치"(정상 라벨)의 부분 문자열이라 단순 포함 검사로는
        # 오탐한다 — 배지 태그 경계(">...</span>")까지 정확히 맞춰 확인한다.
        for old_wording in (">일치</span>", "부분일치", "판단보류"):
            self.assertNotIn(old_wording, html, f"구 라벨 잔존: {old_wording!r}")
        self.assertIn('class="mc-verdict hit">적중<', html)
        self.assertIn('class="mc-verdict miss">불일치<', html)
        self.assertIn('class="mc-verdict neutral">중립<', html)

    def test_methodology_prose_uses_unified_labels(self):
        html = _read("methodology/index.html")
        self.assertIn("적중/불일치/중립/판정 대기", html)
        self.assertNotIn("부분적중", html)
        self.assertNotIn("판단보류", html)

    def test_generated_question_records_verdicts_are_all_known(self):
        records = json.loads(_read("scripts/archive_export/dryrun_output/question_records.json"))
        for r in records:
            # label_for_status가 UnknownVerdictError 없이 통과해야 함
            verdict_labels.label_for_status(r["verdict"])


if __name__ == "__main__":
    unittest.main()
