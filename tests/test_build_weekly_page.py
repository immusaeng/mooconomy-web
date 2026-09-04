# tests/test_build_weekly_page.py
"""2026-09-04(TASK_ID=WEEKLY_PHASE0_RUNTIME_SAFETY, C) — Weekly 웹 아카이브
복구 회귀 테스트.

- build_weekly_page.render_weekly_page()의 AttributeError 회귀(2026-09-03/04
  ARCHIVE_ISSUE_V8_SHELL_UNIFICATION_REBASE가 build_issue_page.py의 심볼을
  바꾼 뒤 build_weekly_page.py가 갱신되지 않아 실행 시 즉시 죽고 있었다).
- publish_weekly_archive.run()의 producer/receiver 계약(week_json이
  data/weekly/{week_id}.json으로 자기 동기화되는지, index.json에
  has_canonical_page가 정확히 채워지는지, 스키마 누락/추가 필드/구버전
  fixture를 만나도 안전하게 동작하는지, canonical/latest/archive 세
  경로가 각자 올바른 역할을 하는지).

실제 이메일 발송·LLM·네트워크 호출은 어디에도 없다 — 전부 로컬 tempfile과
이미 저장소에 있는 실제 스크립트 함수만 사용한다."""
import json
import os
import shutil
import sys
import tempfile
import unittest

_ARCHIVE_EXPORT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "archive_export"),
)
sys.path.insert(0, _ARCHIVE_EXPORT)

import build_issue_page as bip  # noqa: E402
import build_weekly_page as bwp  # noqa: E402
import publish_weekly_archive as pwa  # noqa: E402


def _weekly_meta(week_id="2026-W35", prev_path=None, next_path=None):
    return {
        "week_id": week_id,
        "public_path": f"/weekly/{week_id}.html",
        "title": f"Mooconomy WEEKLY {week_id} 리캡",
        "morning_thesis": "테스트 주간 요약",
        "published_at": None,
        "published_at_is_approximate": True,
        "prev_path": prev_path,
        "prev_week_id": "2026-W34" if prev_path else None,
        "next_path": next_path,
        "next_week_id": None,
    }


_MINIMAL_SAFE_HTML = (
    "<!DOCTYPE html><html><head><title>MOO:conomy WEEKLY</title>"
    "<style>body{margin:0}</style></head>\n"
    "<body><h1>테스트 위클리</h1><p>본문</p></body></html>"
)


class RenderWeeklyPageAttributeErrorRegressionTests(unittest.TestCase):
    """AttributeError 회귀 테스트 — 이 테스트가 실패한다는 것은 build_issue_page.py
    의 심볼이 다시 바뀌었는데 build_weekly_page.py가 갱신되지 않았다는 뜻이다."""

    def test_render_weekly_page_does_not_raise_attribute_error(self):
        try:
            html = bwp.render_weekly_page(_MINIMAL_SAFE_HTML, _weekly_meta())
        except AttributeError as e:
            self.fail(f"render_weekly_page()가 AttributeError로 죽음(심볼 불일치 회귀): {e}")
        self.assertIn("<link rel=\"canonical\"", html)

    def test_uses_current_build_issue_page_symbols_not_renamed_ones(self):
        # 실제 호출부(코드 바디, docstring 제외)가 현재 심볼만 참조하는지
        # 확인한다 — docstring은 이력 설명을 위해 옛 이름을 그대로
        # 인용하므로 검사 대상에서 뺀다.
        import inspect
        fn_src = inspect.getsource(bwp.render_weekly_page)
        body_src = fn_src.split('"""', 2)[-1]  # 함수 docstring 다음부터가 실제 코드
        self.assertNotIn("_og_meta_block", body_src)
        self.assertNotIn("_SHARE_BUTTONS_HTML", body_src)
        self.assertNotIn("bip._SHARE_CSS", body_src)
        self.assertIn("bip._head_meta_block", body_src)
        self.assertIn("bip._action_bar_html", body_src)
        self.assertIn("bip._ACTION_BAR_CSS", body_src)

    def test_missing_public_path_fails_build_not_silent_fallback(self):
        # build_issue_page.py의 §F 계약(canonical 없으면 빌드 실패)이
        # weekly 경로에도 그대로 적용되는지 확인.
        meta = _weekly_meta()
        meta["public_path"] = None
        with self.assertRaises(bip.MissingCanonicalPathError):
            bwp.render_weekly_page(_MINIMAL_SAFE_HTML, meta)


class _TempWebRepoTestCase(unittest.TestCase):
    """publish_weekly_archive.py의 ROOT/WEEKLY_DATA_DIR/WEEKLY_PAGE_DIR/
    WEEKLY_LATEST_ALIAS_PATH를 임시 디렉터리로 monkeypatch해 실제
    저장소를 절대 건드리지 않는다."""

    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix="weekly_archive_test_")
        self._orig = {
            "ROOT": pwa.ROOT,
            "WEEKLY_DATA_DIR": pwa.WEEKLY_DATA_DIR,
            "WEEKLY_PAGE_DIR": pwa.WEEKLY_PAGE_DIR,
            "WEEKLY_LATEST_ALIAS_PATH": pwa.WEEKLY_LATEST_ALIAS_PATH,
        }
        pwa.ROOT = self.tmp_root
        pwa.WEEKLY_DATA_DIR = os.path.join(self.tmp_root, "data", "weekly")
        pwa.WEEKLY_PAGE_DIR = os.path.join(self.tmp_root, "weekly")
        pwa.WEEKLY_LATEST_ALIAS_PATH = os.path.join(self.tmp_root, "weekly-latest.html")
        # _weekly_nav_block()이 항상 "/weekly.html"(아카이브 인덱스)로
        # 링크한다 — check_internal_links()가 site_root 기준 실제 파일
        # 존재를 요구하므로, 실제 저장소 루트에 있는 weekly.html과
        # 동일하게 스텁을 만들어둔다(내용은 무관, 존재 여부만 검사됨).
        with open(os.path.join(self.tmp_root, "weekly.html"), "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><body>stub</body></html>")

    def tearDown(self):
        for k, v in self._orig.items():
            setattr(pwa, k, v)
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _write_week_json(self, week_id, period_start, period_end, weekly_thesis="요약", extra=None):
        rec = {
            "schema_version": "weekly-report/v1",
            "week_id": week_id,
            "period_start_kst": period_start,
            "period_end_kst": period_end,
            "weekly_thesis": weekly_thesis,
        }
        if extra:
            rec.update(extra)
        path = os.path.join(self.tmp_root, f"{week_id}.src.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        return path

    def _write_raw_html(self, name="weekly.src.html"):
        path = os.path.join(self.tmp_root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_MINIMAL_SAFE_HTML)
        return path


class ProducerReceiverSchemaTests(_TempWebRepoTestCase):
    """producer(daily-mooconomy가 넘기는 week_json)/receiver(이 스크립트)
    계약 — 정상 스키마, 누락 필드, 추가 필드, 구버전 fixture."""

    def test_normal_schema_publishes_permalink_and_syncs_data_dir(self):
        week_json = self._write_week_json("2026-W35", "2026-08-31", "2026-09-06")
        html_path = self._write_raw_html()
        report = pwa.run(week_json_path=week_json, weekly_html_path=html_path)
        self.assertFalse(report.get("aborted"), report.get("abort_reason"))
        self.assertTrue(report["permalink_built"])
        self.assertTrue(os.path.exists(os.path.join(pwa.WEEKLY_PAGE_DIR, "2026-W35.html")))
        self.assertTrue(os.path.exists(os.path.join(pwa.WEEKLY_DATA_DIR, "2026-W35.json")))
        self.assertTrue(os.path.exists(pwa.WEEKLY_LATEST_ALIAS_PATH))

    def test_missing_optional_fields_do_not_crash(self):
        # weekly_thesis가 없어도(구 버전 fixture처럼 null) 발행이 되어야 한다.
        week_json = self._write_week_json("2026-W35", "2026-08-31", "2026-09-06", weekly_thesis=None)
        html_path = self._write_raw_html()
        report = pwa.run(week_json_path=week_json, weekly_html_path=html_path)
        self.assertFalse(report.get("aborted"), report.get("abort_reason"))

    def test_extra_unknown_fields_are_ignored_not_rejected(self):
        week_json = self._write_week_json(
            "2026-W35", "2026-08-31", "2026-09-06",
            extra={"an_unexpected_new_field": {"nested": True}, "another_one": [1, 2, 3]})
        html_path = self._write_raw_html()
        report = pwa.run(week_json_path=week_json, weekly_html_path=html_path)
        self.assertFalse(report.get("aborted"), report.get("abort_reason"))

    def test_old_pre_pipeline_fixture_shape_is_readable(self):
        # 실제 data/weekly/2026-W31.json 스키마(narrative 필드 전부 null,
        # top_three_drivers 등 빈 배열)를 그대로 흉내낸다 -- "구버전
        # fixture"가 index 재구성 과정에서 죽지 않아야 한다(그 fixture
        # 자체를 permalink로 승격하지는 않는다 -- 이번 실행 대상이 아님).
        os.makedirs(pwa.WEEKLY_DATA_DIR, exist_ok=True)
        old_fixture = {
            "schema_version": "weekly-report/v1", "week_id": "2026-W31",
            "period_start_kst": "2026-07-27", "period_end_kst": "2026-07-31",
            "weekly_thesis": None, "first_last_metrics": [], "top_three_drivers": [],
            "signal_chain": None, "main_story_summary": None, "moo_q_scorecard": [],
            "weekly_words": [], "next_week_watch": [], "risk_notes": [], "source_manifest": [],
        }
        with open(os.path.join(pwa.WEEKLY_DATA_DIR, "2026-W31.json"), "w", encoding="utf-8") as f:
            json.dump(old_fixture, f, ensure_ascii=False)

        week_json = self._write_week_json("2026-W35", "2026-08-31", "2026-09-06")
        html_path = self._write_raw_html()
        report = pwa.run(week_json_path=week_json, weekly_html_path=html_path)
        self.assertFalse(report.get("aborted"), report.get("abort_reason"))
        self.assertEqual(report["index_entry_count"], 2)  # W31(구) + W35(신규) 둘 다 인덱스에 반영

    def test_missing_week_json_aborts_without_writing_permalink(self):
        report = pwa.run(week_json_path="/no/such/file.json", weekly_html_path=None)
        self.assertTrue(report["aborted"])
        self.assertFalse(os.path.isdir(pwa.WEEKLY_PAGE_DIR))

    def test_no_weekly_output_this_run_is_a_clean_skip(self):
        report = pwa.run(week_json_path=None, weekly_html_path=None)
        self.assertTrue(report.get("skipped"))
        self.assertFalse(report["aborted"])


class CanonicalLatestArchiveLinkingTests(_TempWebRepoTestCase):
    """canonical Weekly URL / archive index(has_canonical_page) / latest
    Weekly alias 세 경로가 각자 다른 역할을 하는지 확인한다."""

    def _publish_week(self, week_id, start, end):
        week_json = self._write_week_json(week_id, start, end)
        html_path = self._write_raw_html(name=f"{week_id}.html")
        return pwa.run(week_json_path=week_json, weekly_html_path=html_path)

    def test_canonical_permalink_is_the_actual_rendered_email(self):
        self._publish_week("2026-W35", "2026-08-31", "2026-09-06")
        with open(os.path.join(pwa.WEEKLY_PAGE_DIR, "2026-W35.html"), encoding="utf-8") as f:
            permalink_html = f.read()
        self.assertIn("테스트 위클리", permalink_html)  # _MINIMAL_SAFE_HTML의 실제 본문이 그대로 담김

    def test_index_json_marks_has_canonical_page_correctly(self):
        # JSON만 있고 HTML은 아직 없는 주(예: 과거 fixture)와, 이번에
        # 실제로 permalink까지 만들어진 주가 index.json에서 구분돼야 한다.
        os.makedirs(pwa.WEEKLY_DATA_DIR, exist_ok=True)
        with open(os.path.join(pwa.WEEKLY_DATA_DIR, "2026-W31.json"), "w", encoding="utf-8") as f:
            json.dump({"week_id": "2026-W31", "period_start_kst": "2026-07-27",
                       "period_end_kst": "2026-07-31"}, f)
        self._publish_week("2026-W35", "2026-08-31", "2026-09-06")
        with open(os.path.join(pwa.WEEKLY_DATA_DIR, "index.json"), encoding="utf-8") as f:
            index = json.load(f)
        by_id = {w["week_id"]: w for w in index["weeks"]}
        self.assertFalse(by_id["2026-W31"]["has_canonical_page"])
        self.assertTrue(by_id["2026-W35"]["has_canonical_page"])

    def test_latest_alias_always_reflects_most_recently_published_week(self):
        self._publish_week("2026-W34", "2026-08-24", "2026-08-30")
        with open(pwa.WEEKLY_LATEST_ALIAS_PATH, encoding="utf-8") as f:
            first_alias = f.read()
        self.assertIn("테스트 위클리", first_alias)
        self._publish_week("2026-W35", "2026-08-31", "2026-09-06")
        with open(os.path.join(pwa.WEEKLY_PAGE_DIR, "2026-W35.html"), encoding="utf-8") as f:
            latest_permalink = f.read()
        with open(pwa.WEEKLY_LATEST_ALIAS_PATH, encoding="utf-8") as f:
            second_alias = f.read()
        self.assertEqual(second_alias, latest_permalink)  # 별칭이 canonical과 다시 동일 콘텐츠로 갱신됨

    def test_broken_fixture_page_never_gets_linked_into_prev_next_chain(self):
        # data/weekly/*.json은 있지만 /weekly/{id}.html이 없는 옛 fixture는
        # prev/next 체인에 끼어들어 깨진 링크를 만들면 안 된다(원본 로직
        # 그대로 유지 — check_internal_links가 이걸 실제로 검사한다).
        os.makedirs(pwa.WEEKLY_DATA_DIR, exist_ok=True)
        with open(os.path.join(pwa.WEEKLY_DATA_DIR, "2026-W31.json"), "w", encoding="utf-8") as f:
            json.dump({"week_id": "2026-W31", "period_start_kst": "2026-07-27",
                       "period_end_kst": "2026-07-31"}, f)
        report = self._publish_week("2026-W35", "2026-08-31", "2026-09-06")
        self.assertFalse(report.get("aborted"), report.get("abort_reason"))
        with open(os.path.join(pwa.WEEKLY_PAGE_DIR, "2026-W35.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertNotIn("2026-W31", html)  # prev/next에 옛 fixture가 안 나타남


class WeeklyHtmlSharedShellAndCanonicalPolicyTests(unittest.TestCase):
    """2026-09-05(TASK_ID=CORRECT_WEEKLY_PHASE0_PRS_BEFORE_MERGE) — weekly.html
    자체(index.json을 소비하는 클라이언트 페이지)에 대한 회귀 가드.
    PR#14가 도입한 공유 셸/noindex 정책을 이 파일이 실수로 되돌리지
    않았는지, has_canonical_page=false인 fixture가 실제 리포트 링크로
    노출되지 않는지 소스 레벨로 확인한다(DOM 실행 환경이 이 저장소에
    없어 문자열 검사로 대체 — tests/test_build_issue_page_share.py의
    ShareScriptSourceTests와 동일한 검증 방식)."""

    @classmethod
    def setUpClass(cls):
        weekly_html_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "weekly.html"))
        with open(weekly_html_path, encoding="utf-8") as f:
            cls.html = f.read()

    def test_pr14_shared_shell_markers_present(self):
        self.assertIn('<header class="slim-header">', self.html)
        self.assertIn('<nav class="breadcrumb"', self.html)
        self.assertIn('<nav class="mob-tabs"', self.html)
        self.assertIn('shared-shell.css', self.html)
        self.assertIn('styles.css', self.html)

    def test_noindex_policy_preserved(self):
        self.assertIn('<meta name="robots" content="noindex,nofollow">', self.html)

    def test_no_leftover_merge_conflict_markers(self):
        for marker in ("<<<<<<<", "=======", ">>>>>>>"):
            self.assertNotIn(marker, self.html)

    def test_old_custom_nav_theme_removed(self):
        # PR#15 원본이 쓰던 독립 navy/gold 테마·GNB가 공유 셸로 완전히
        # 대체됐는지 확인 — 두 네비게이션이 동시에 남아있으면 안 된다.
        self.assertNotIn("--navy:", self.html)
        self.assertNotIn('class="mobile-nav"', self.html)

    def test_client_js_filters_on_has_canonical_page_true(self):
        self.assertIn("has_canonical_page === true", self.html)

    def test_client_js_never_renders_all_entries_unconditionally(self):
        # weeks 배열을 필터링 없이 그대로 .map()하는 코드가 없어야 한다
        # (있으면 W31/W32 같은 fixture도 실제 리포트 링크처럼 노출될 위험).
        self.assertNotIn("(idx.weeks || []).map(", self.html)

    def test_empty_state_fallback_markup_present(self):
        # 실제 발행본이 하나도 없을 때(현재 상태) 보여줄 기존 "개편 준비
        # 중" 안내문이 그대로 있어야 한다 — 완전히 새 문구로 갈아엎지 않음.
        self.assertIn('id="weeklyEmptyState"', self.html)
        self.assertIn("정식 발행물로", self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
