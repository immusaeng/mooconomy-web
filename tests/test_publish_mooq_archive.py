"""publish_mooq_archive.py 회귀 테스트 — 전부 합성 fixture로만 검증한다
(실제 data/claims_store.json은 읽기만 하고 쓰지 않음, canonical 데이터를
건드리는 테스트는 없다). LLM/네트워크 호출 없음.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "archive_export"))
import publish_mooq_archive as pma  # noqa: E402


def _claim(claim_id, metric_id, status, *, issued="2026-01-01T08:00:00+09:00",
           baseline_value=100.0, baseline_asof="2026-01-01", expected_dir="up",
           resolution_at="2026-01-02", end_value=101.0, explanation="테스트 설명"):
    return {
        "claimId": claim_id,
        "claimText": f"테스트 질문 {claim_id}?",
        "issuedAt": issued,
        "baseline": {"value": baseline_value, "asOf": baseline_asof},
        "expectedDirection": expected_dir,
        "horizon": {"resolutionAt": resolution_at},
        "resolution": ({"endValue": end_value, "changeUnit": "%", "explanation": explanation}
                        if status != "unresolved" else {}),
        "status": status,
        "verificationType": "proxy",
        "thresholdRuleId": "pct_020",
        "lockedAt": issued,
        "metricId": metric_id,
    }


BASE_HOME = {
    "schemaVersion": 1,
    "generatedAt": "2026-01-01T08:00:00+09:00",
    "publishDate": "2026-01-01",
    "status": "ok",
    "indicators": [{"id": "kospi", "name": "코스피"}],
    "unrelatedNested": {"a": [1, 2, 3], "b": None},
    "claims": None,
    "newsletterClaimsTeaser": None,
}


class PublishMooqArchiveTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="mooq_test_")
        self.claims_store_path = os.path.join(self.tmpdir, "claims_store.json")
        self.home_json_path = os.path.join(self.tmpdir, "home.json")
        self.questions_path = os.path.join(self.tmpdir, "questions", "index.html")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_store(self, claims):
        with open(self.claims_store_path, "w", encoding="utf-8") as f:
            json.dump({"claims": claims}, f, ensure_ascii=False, indent=2)

    def _write_home(self, home=None):
        with open(self.home_json_path, "w", encoding="utf-8") as f:
            json.dump(home or BASE_HOME, f, ensure_ascii=False, indent=2)

    def _run(self, dry_run=False):
        return pma.run(
            claims_store_path=self.claims_store_path,
            home_json_path=self.home_json_path,
            questions_path=self.questions_path,
            dry_run_report_only=dry_run,
        )


class NewClaimAndIdempotencyTests(PublishMooqArchiveTestBase):
    def test_new_canonical_claim_is_reflected(self):
        self._write_store({"2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit")})
        self._write_home()
        report = self._run()
        self.assertFalse(report["aborted"])
        self.assertEqual(report["question_record_count"], 1)

        store = json.load(open(self.claims_store_path, encoding="utf-8"))
        store["claims"]["2026-01-02-c1"] = _claim("2026-01-02-c1", "usdkrw", "miss")
        self._write_store(store["claims"])
        report2 = self._run()
        self.assertFalse(report2["aborted"])
        self.assertEqual(report2["question_record_count"], 2)
        html = open(self.questions_path, encoding="utf-8").read()
        self.assertEqual(html.count('class="qcard"'), 2)

    def test_rerun_same_store_is_byte_identical_and_no_duplicates(self):
        self._write_store({
            "2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit"),
            "2026-01-02-c1": _claim("2026-01-02-c1", "usdkrw", "miss"),
        })
        self._write_home()
        self._run()
        home_after_first = open(self.home_json_path, encoding="utf-8").read()
        questions_after_first = open(self.questions_path, encoding="utf-8").read()

        report2 = self._run()
        self.assertFalse(report2["aborted"])
        self.assertEqual(report2["question_record_count"], 2)
        self.assertEqual(open(self.home_json_path, encoding="utf-8").read(), home_after_first)
        self.assertEqual(open(self.questions_path, encoding="utf-8").read(), questions_after_first)
        self.assertEqual(questions_after_first.count('class="qcard"'), 2)

    def test_claim_without_result_shows_as_pending_not_fabricated(self):
        self._write_store({"2026-01-01-c1": _claim("2026-01-01-c1", "usdkrw", "unresolved")})
        self._write_home()
        report = self._run()
        self.assertFalse(report["aborted"])
        html = open(self.questions_path, encoding="utf-8").read()
        self.assertIn("확인 중", html)
        home = json.load(open(self.home_json_path, encoding="utf-8"))
        self.assertEqual(len(home["claims"]["todayClaims"]), 1)
        self.assertEqual(len(home["claims"]["previousClaims"]), 0)


class FailurePreservationTests(PublishMooqArchiveTestBase):
    def _seed_known_good_derived_files(self):
        self._write_store({"2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit")})
        self._write_home()
        report = self._run()
        self.assertFalse(report["aborted"])
        return (open(self.home_json_path, encoding="utf-8").read(),
                open(self.questions_path, encoding="utf-8").read())

    def test_empty_claims_store_aborts_without_touching_derived_files(self):
        home_before, questions_before = self._seed_known_good_derived_files()
        self._write_store({})
        report = self._run()
        self.assertTrue(report["aborted"])
        self.assertEqual(open(self.home_json_path, encoding="utf-8").read(), home_before)
        self.assertEqual(open(self.questions_path, encoding="utf-8").read(), questions_before)

    def test_schema_invalid_claim_aborts_without_touching_derived_files(self):
        home_before, questions_before = self._seed_known_good_derived_files()
        bad_claim = _claim("2026-01-02-c1", "kospi", "hit")
        bad_claim["issuedAt"] = None  # question-record.schema.json: issued_at는 필수 string
        self._write_store({
            "2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit"),
            "2026-01-02-c1": bad_claim,
        })
        report = self._run()
        self.assertTrue(report["aborted"])
        self.assertIn("스키마", report["abort_reason"])
        self.assertEqual(open(self.home_json_path, encoding="utf-8").read(), home_before)
        self.assertEqual(open(self.questions_path, encoding="utf-8").read(), questions_before)

    def test_missing_claims_store_aborts_without_touching_derived_files(self):
        home_before, questions_before = self._seed_known_good_derived_files()
        os.remove(self.claims_store_path)
        report = self._run()
        self.assertTrue(report["aborted"])
        self.assertEqual(open(self.home_json_path, encoding="utf-8").read(), home_before)
        self.assertEqual(open(self.questions_path, encoding="utf-8").read(), questions_before)

    def test_no_leftover_tmp_dir_after_run(self):
        self._write_store({"2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit")})
        self._write_home()
        self._run()
        self.assertFalse(os.path.exists(pma.BUILD_TMP))


class HomeJsonFieldPreservationTests(PublishMooqArchiveTestBase):
    def test_only_claims_field_changes_in_home_json(self):
        home = copy.deepcopy(BASE_HOME)
        home["claims"] = {"previousClaims": [], "todayClaims": [], "totals": {}}
        self._write_home(home)
        self._write_store({"2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit")})
        report = self._run()
        self.assertFalse(report["aborted"])
        new_home = json.load(open(self.home_json_path, encoding="utf-8"))
        for key in home:
            if key == "claims":
                continue
            self.assertEqual(new_home[key], home[key], f"unexpected change in home.json field '{key}'")
        self.assertNotEqual(new_home["claims"], home["claims"])


class CrossFileConsistencyTests(PublishMooqArchiveTestBase):
    def test_questions_archive_count_matches_home_totals(self):
        claims = {
            "2026-01-01-c1": _claim("2026-01-01-c1", "kospi", "hit"),
            "2026-01-02-c1": _claim("2026-01-02-c1", "kosdaq", "miss"),
            "2026-01-03-c1": _claim("2026-01-03-c1", "usdkrw", "neutral"),
            "2026-01-04-c1": _claim("2026-01-04-c1", "wti", "unresolved"),
        }
        self._write_store(claims)
        self._write_home()
        report = self._run()
        self.assertFalse(report["aborted"])

        html = open(self.questions_path, encoding="utf-8").read()
        qcard_count = html.count('class="qcard"')
        home = json.load(open(self.home_json_path, encoding="utf-8"))
        totals = home["claims"]["totals"]
        totals_sum = sum(totals.values())
        self.assertEqual(qcard_count, len(claims))
        self.assertEqual(totals_sum, len(claims))
        self.assertEqual(
            len(home["claims"]["previousClaims"]) + len(home["claims"]["todayClaims"]),
            len(claims),
        )


if __name__ == "__main__":
    unittest.main()
