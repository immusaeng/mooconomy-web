"""load_all_records 회귀 — {date}.moo_view_manifest.json이 본 레코드를 덮어쓰지 않아야 한다."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "archive_export"))
import issue_archive_lib as lib  # noqa: E402


def _write(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f)


class LoadAllRecordsTests(unittest.TestCase):
    def test_sidecar_files_ignored_and_metadata_intact(self):
        rec = {"edition_date_kst": "2026-10-15", "production_status": "SEND_CONFIRMED",
               "subject": "S", "thesis": {"headline": "H"}, "main_story": {"a": 1},
               "narratives": [1], "source_commit_sha": "abc", "archived_at": "t"}
        with tempfile.TemporaryDirectory() as d:
            _write(d, "2026-10-15.json", rec)
            _write(d, "2026-10-15.moo_view_manifest.json", {"edition_date_kst": "2026-10-15", "x": 1})
            _write(d, "index.json", {})
            records, errors = lib.load_all_records(d)
        self.assertEqual(errors, [])
        self.assertEqual(len(records), 1)
        m = lib.build_normalized_metadata(*records[0])
        self.assertEqual((m["title"], m["morning_thesis"], m["source_commit_sha"]), ("S", "H", "abc"))

    def test_duplicate_date_warns_and_prefers_matching_stem(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "2026-10-14.json", {"edition_date_kst": "2026-10-15", "who": "wrong-stem"})
            _write(d, "2026-10-15.json", {"edition_date_kst": "2026-10-15", "who": "stem"})
            records, _ = lib.load_all_records(d)
        self.assertEqual([r[1]["who"] for r in records], ["stem"])


if __name__ == "__main__":
    unittest.main()
