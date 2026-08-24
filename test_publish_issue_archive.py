"""2026-08-24(TASK_ID=W7_ARCHIVE_ABORT_MITIGATION)
publish_issue_archive.py의 "오늘 제외 catch-up" 완화를 검증한다.

이 저장소(mooconomy-web)에는 이제까지 자동화된 테스트가 전혀 없었다
(scripts/archive_export/에 test_*.py 0개, dry-run 실행 결과를 사람이
읽는 방식으로만 검증돼 왔다) — 이 파일이 첫 테스트다. 실제 collectors/
LLM/이메일 발송을 전혀 호출하지 않는다 — 전부 tempfile 기반 fixture와
publish_issue_archive 모듈의 ROOT/ARCHIVE_DIR/BUILD_TMP를 임시
디렉터리로 monkeypatch해서 검증한다.

⚠️ 이 PR은 P0B(daily.yml 웹 푸시 게이트, output/latest_web_candidate.html
관련)와 동시 배포가 조건이다(CEO 지시, 2026-08-24) — 이 코드만 단독으로
merge/배포하지 말 것. 테스트가 전부 통과한다고 곧바로 배포 가능하다는
뜻이 아니다.
"""
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts", "archive_export"))
import publish_issue_archive as pia
import issue_archive_lib as lib

_RICH_MARKER = 'name="x-apple-disable-message-reformatting"'


def _valid_record(subject="테스트 발행"):
    return {
        "production_status": "SEND_CONFIRMED",
        "subject": subject,
        "thesis": {"headline": subject},
        "main_story": {"headline": subject},
        "narratives": ["본문"],
        "archived_at": "2026-08-01T06:41:00+09:00",
    }


def _email_html(date_str, rich=True):
    marker = f'<meta {_RICH_MARKER} content="yes">' if rich else ""
    y, m, d = date_str.split("-")
    return (
        "<!DOCTYPE html><html><head><title>t</title>"
        f"{marker}"
        "</head><body>"
        f"<div>발행 {y}년 {m}월 {d}일</div>"
        "<p>본문 내용입니다.</p>"
        "<a href=\"/archive/\">아카이브</a>"
        "</body></html>\n"
    )


class PublishIssueArchiveTestBase(unittest.TestCase):
    """각 테스트마다 완전히 새 임시 ROOT를 만들고 모듈 상수를 그곳으로
    monkeypatch한다 — 실제 mooconomy-web 체크아웃은 절대 건드리지 않는다."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="pia_test_")
        self._orig_root = pia.ROOT
        self._orig_archive_dir = pia.ARCHIVE_DIR
        self._orig_build_tmp = pia.BUILD_TMP
        pia.ROOT = self._tmp
        pia.ARCHIVE_DIR = os.path.join(self._tmp, "data", "daily_archive")
        pia.BUILD_TMP = os.path.join(self._tmp, "_build_tmp")
        os.makedirs(pia.ARCHIVE_DIR)

    def tearDown(self):
        pia.ROOT = self._orig_root
        pia.ARCHIVE_DIR = self._orig_archive_dir
        pia.BUILD_TMP = self._orig_build_tmp
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _add_record(self, date, rich=True, **overrides):
        rec = _valid_record()
        rec.update(overrides)
        with open(os.path.join(pia.ARCHIVE_DIR, f"{date}.json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        return rec

    def _write_edition_mode(self, mode):
        path = os.path.join(self._tmp, "edition_mode.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(mode)
        return path

    def _write_today_email(self, date, rich=True):
        with open(os.path.join(self._tmp, "latest-email.html"), "w", encoding="utf-8") as f:
            f.write(_email_html(date, rich=rich))

    def _seed_existing_issue_page(self, date, rich=True):
        issues_dir = os.path.join(self._tmp, "issues")
        os.makedirs(issues_dir, exist_ok=True)
        content = _email_html(date, rich=rich)
        with open(os.path.join(issues_dir, f"{date}.html"), "w", encoding="utf-8") as f:
            f.write(content)
        return content

    def _seed_live_manifest(self, dates):
        archive_dir = os.path.join(self._tmp, "data", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        manifest = [{"issue_date": d, "public_path": f"/issues/{d}.html"} for d in dates]
        with open(os.path.join(archive_dir, "issues_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f)

    def _run(self, today, edition_mode_path=None):
        return pia.run(today=today, edition_mode_path=edition_mode_path or "__no_such_file__")


class BaselineUnchangedBehaviorTests(PublishIssueArchiveTestBase):
    """회귀 기준선 — 오늘이 유효한 평시 daily 실행은 이전과 동일하게
    동작해야 한다(오늘 latest.html 교체, aborted=False)."""

    def test_today_valid_publishes_normally(self):
        self._add_record("2026-08-20")
        self._write_today_email("2026-08-20")
        report = self._run(today="2026-08-20")
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertTrue(report["today_included"])
        self.assertEqual(report["manifest_entry_count"], 1)
        self.assertTrue(report["swapped_to_real_paths"])
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "latest.html")))
        self.assertTrue(os.path.exists(os.path.join(self._tmp, "issues", "2026-08-20.html")))

    def test_existing_rich_issue_page_not_downgraded(self):
        """기존 /issues/{date}.html URL이 이번 완화로 깨지거나 얇아지지
        않는다는 회귀 근거(CEO 명시 요구)."""
        self._add_record("2026-08-18")
        rich_content = self._seed_existing_issue_page("2026-08-18", rich=True)
        self._add_record("2026-08-20")
        self._write_today_email("2026-08-20")
        report = self._run(today="2026-08-20")
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertIn("2026-08-18", report["preserved_rich_pages"])
        with open(os.path.join(self._tmp, "issues", "2026-08-18.html"), encoding="utf-8") as f:
            self.assertEqual(f.read(), rich_content)


class TodayExcludedCatchUpTests(PublishIssueArchiveTestBase):
    """W-7 본체 — 오늘이 유효하지 않아도 더 이상 전체 abort하지 않는다."""

    def test_weekly_monday_missing_today_is_not_aborted(self):
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        self._seed_live_manifest(["2026-08-21"])
        mode_path = self._write_edition_mode("weekly")
        report = self._run(today="2026-08-24", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertFalse(report["today_included"])
        self.assertEqual(report["edition_mode"], "weekly")
        self.assertNotIn("aborted_because_today", report)

    def test_weekly_mode_with_stray_invalid_today_record_same_as_absent(self):
        """오늘자에 production_status가 SEND_CONFIRMED가 아닌 레코드가
        실수로 존재해도, 레코드가 아예 없을 때와 동일하게 처리돼야
        한다(레코드 유무로 분기가 갈라지면 안 됨)."""
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        self._seed_live_manifest(["2026-08-21"])
        self._add_record("2026-08-24", production_status="UNKNOWN")
        mode_path = self._write_edition_mode("weekly")
        report = self._run(today="2026-08-24", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertFalse(report["today_included"])

    def test_real_daily_failure_still_catches_up_older_valid_dates(self):
        """평일에 오늘이 진짜 실패해도(edition_mode=daily), 이미 유효한
        과거 날짜는 더 이상 인질로 잡히지 않고 catch-up된다 — 이게 이번
        완화의 핵심 동작 변화."""
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        mode_path = self._write_edition_mode("daily")
        report = self._run(today="2026-08-22", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertFalse(report["today_included"])
        self.assertEqual(report["edition_mode"], "daily")
        self.assertIn("2026-08-21", report["passing_dates"])
        self.assertEqual(report["manifest_entry_count"], 1)

    def test_missing_marker_file_defaults_to_daily_but_still_catches_up(self):
        """마커 파일 자체가 없어도(배포 과도기) edition_mode는 안전측
        기본값 "daily"로 떨어지지만, catch-up 자체는(W-7 본 기능) 여전히
        동작한다 — mode는 사유 텍스트만 바꿀 뿐 abort 여부를 가르지
        않는다."""
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        report = self._run(today="2026-08-24")  # edition_mode_path 기본값 = 존재하지 않는 경로
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertEqual(report["edition_mode"], "daily")
        self.assertIn("2026-08-21", report["passing_dates"])

    def test_multi_day_backlog_catches_up_all_at_once(self):
        """3일 밀린 뒤 4일째 정상 daily가 돌면 밀린 분 전부 한 번에
        catch-up된다."""
        for d in ("2026-08-18", "2026-08-19", "2026-08-20"):
            self._add_record(d)
            self._seed_existing_issue_page(d, rich=True)
        self._add_record("2026-08-21")
        self._write_today_email("2026-08-21")
        report = self._run(today="2026-08-21")
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertTrue(report["today_included"])
        self.assertEqual(report["manifest_entry_count"], 4)

    def test_today_still_not_valid_and_nothing_to_catch_up_is_a_clean_noop(self):
        """오늘도 없고 catch-up 대상도 하나도 없으면(빈 아카이브)
        조용히 정상 종료해야 한다 — 크래시하면 안 됨."""
        mode_path = self._write_edition_mode("weekly")
        report = self._run(today="2026-08-24", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertEqual(report["manifest_entry_count"], 0)


class LatestHtmlNotTouchedWhenTodayExcludedTests(PublishIssueArchiveTestBase):
    def test_latest_html_untouched_on_weekly_monday(self):
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        with open(os.path.join(self._tmp, "latest.html"), "w", encoding="utf-8") as f:
            f.write("LAST_REAL_DAILY_CONTENT")
        mode_path = self._write_edition_mode("weekly")
        report = self._run(today="2026-08-24", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        with open(os.path.join(self._tmp, "latest.html"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "LAST_REAL_DAILY_CONTENT")
        self.assertNotIn("latest_html_backed_up_to", report)


class ManifestShrinkGuardTests(PublishIssueArchiveTestBase):
    """새로 생긴 위험: today_included=False 경로가 실제 경로 교체까지
    도달할 수 있게 되면서, ARCHIVE_DIR 복원이 비정상적으로 비었을 때
    라이브 아카이브를 그대로 덮어써 유실시킬 수 있는 새 위험이 생긴다.
    manifest 건수가 기존 라이브보다 줄면 반드시 abort해야 한다."""

    def test_shrinking_manifest_aborts_instead_of_overwriting(self):
        self._seed_live_manifest(["2026-08-18", "2026-08-19", "2026-08-20"])
        # ARCHIVE_DIR가 실수로 비어있는(복원 실패) 상황을 재현 — 유효
        # 레코드가 하나도 없다.
        mode_path = self._write_edition_mode("weekly")
        report = self._run(today="2026-08-24", edition_mode_path=mode_path)
        self.assertTrue(report["aborted"])
        self.assertIn("데이터 유실 의심", report["abort_reason"])
        self.assertNotIn("swapped_to_real_paths", report)


class DryRunStillWorksTests(PublishIssueArchiveTestBase):
    def test_dry_run_does_not_touch_real_paths_when_today_excluded(self):
        self._add_record("2026-08-21")
        self._seed_existing_issue_page("2026-08-21", rich=True)
        mode_path = self._write_edition_mode("weekly")
        report = pia.run(dry_run_report_only=True, today="2026-08-24", edition_mode_path=mode_path)
        self.assertFalse(report["aborted"], report.get("abort_reason"))
        self.assertFalse(report["swapped_to_real_paths"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
