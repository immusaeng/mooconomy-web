"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
오케스트레이터 — 아래 순서를 강제한다(CEO 지시 순서 그대로):

1. data/daily_archive/*.json 검증(유효/무효/누락 집계)
2. 정규화 metadata 리스트 생성
3. 날짜순 prev/next 계산
4. issue 페이지를 임시 디렉터리(_build_tmp/)에 생성
5. 각 페이지 privacy/link/HTML 검사
6. 검사 통과 항목만 manifest에 기록
7. 월간·전체 아카이브 생성(통과분만)
7.5. sitemap.xml / rss.xml을 같은 manifest로 생성(2026-08-21 추가) --
   XML 파싱 검증까지 통과해야 다음 단계로 진행한다.
8. 전체 검증 통과 후에만 실제 경로로 교체(기존 latest.html은 교체 직전
   .bak로 백업)

실패 시 실제 공개 파일(latest.html/issues/*.html/archive/**/sitemap.xml/
rss.xml)을 절대 건드리지 않고 보고만 한다. 새 LLM 호출·네트워크 호출 없음.
"""
import datetime as _dt
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import issue_archive_lib as lib
import build_issue_page as bip
import build_archive_pages as bap
import build_sitemap as bsm
import build_rss as brss

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARCHIVE_DIR = os.path.join(ROOT, "data", "daily_archive")
BUILD_TMP = os.path.join(ROOT, "_build_tmp")


def _kst_today_str():
    """2026-08-21(TASK_ID=TRACK_B7_ARCHIVE_AUTOMATION): TODAY was a
    hardcoded one-shot value ("이번 라운드 기준 오늘") that made this
    orchestrator a single-use script -- it was run once on 2026-08-11 and
    never again, which is exactly why the archive stopped growing. Compute
    it from wall-clock KST instead so this can run unattended every day.
    Not a determinism violation of the "no LLM/network calls" principle
    that export.py's determinism note refers to -- "what day is it" is an
    unavoidable input for an orchestrator whose whole job is publishing
    *today's* issue."""
    now_utc = _dt.datetime.now(_dt.timezone.utc)
    return (now_utc + _dt.timedelta(hours=9)).strftime("%Y-%m-%d")


def _read_edition_mode(path):
    """2026-08-24(TASK_ID=W7_ARCHIVE_ABORT_MITIGATION): daily-briefing의
    main.py가 라우팅 직후 남기는 신호("daily"/"weekly")를 읽는다. 이
    스크립트가 스스로 요일을 재계산하지 않는다 — WEEKLY_MONDAY_ENABLED
    토글이나 요일 게이트가 나중에 바뀌어도 두 곳의 판단이 어긋날 일이
    없다. 파일이 없거나 읽기 실패하거나 값이 "daily"/"weekly" 둘 다
    아니면 안전측 기본값 "daily"로 처리한다 — 기존의 엄격한 오늘-검증을
    그대로 유지하는 쪽이 기본값이라는 뜻이다(마커가 없다고 완화가 저절로
    켜지지 않는다). 이 함수는 예외를 던지지 않는다."""
    try:
        with open(path, encoding="utf-8") as f:
            mode = f.read().strip()
        if mode in ("daily", "weekly"):
            return mode
    except OSError:
        pass
    return "daily"


def run(dry_run_report_only=False, today=None, edition_mode_path="output/edition_mode.txt"):
    TODAY = today or _kst_today_str()
    report = {"aborted": False, "abort_reason": None, "today": TODAY}

    # ── 1~3. 검증 + 정규화 + prev/next ──────────────────────────────
    records, load_errors = lib.load_all_records(ARCHIVE_DIR)
    report["total_records_found"] = len(records)
    report["load_errors"] = load_errors

    by_date = {}
    valid_dates, invalid = [], []
    for date, rec in records:
        by_date[date] = rec
        ok, reason = lib.classify_record(date, rec)
        if ok:
            valid_dates.append(date)
        else:
            invalid.append({"date": date, "reason": reason})
    report["valid_dates"] = valid_dates
    report["invalid_records"] = invalid

    # 2026-08-24(TASK_ID=W7_ARCHIVE_ABORT_MITIGATION): 예전에는 오늘이
    # valid_dates에 없으면 여기서 즉시 전체 abort했다 — 이미 유효한 어제
    # 이전 날짜들까지 인질로 잡혀 밀리는 문제가 있었다(월요일 Weekly
    # 전환 이후 매주 재현, W_TRACK_WEB_FULL_AUDIT 2026-08-24). 이제는
    # "오늘"만 이번 실행의 발행 대상에서 빼고, 이미 유효한 나머지 날짜는
    # 아래 로직이 원래도 매번 valid_dates 전체를 다시 렌더/검사/스왑하는
    # 구조라 자동으로 catch-up된다 — 새 누적 로직을 추가한 게 아니라
    # "오늘 하나만 뺄 수 있게" 게이트를 옮긴 것뿐이다.
    today_included = TODAY in valid_dates
    report["today_included"] = today_included
    edition_mode = _read_edition_mode(edition_mode_path)
    report["edition_mode"] = edition_mode
    if not today_included:
        if edition_mode == "weekly":
            report["today_skip_reason"] = (
                f"오늘({TODAY})은 Weekly 전용 실행(edition_mode=weekly) — "
                "daily 레코드가 없는 게 정상, catch-up만 진행"
            )
        else:
            report["today_skip_reason"] = (
                f"오늘({TODAY}) 레코드가 유효하지 않음(edition_mode={edition_mode}) — "
                "오늘만 제외하고 이전 유효분 catch-up 진행"
            )

    metas = [lib.build_normalized_metadata(d, by_date[d]) for d in valid_dates]
    metas = lib.compute_prev_next(metas)
    meta_by_date = {m["issue_date"]: m for m in metas}

    # ── 오늘자 latest-email.html 발행일 검증 + public-safe 변환 ──────
    # today_included가 False면(Weekly 월요일 또는 진짜 daily 실패) 오늘자
    # 콘텐츠 자체가 없다는 뜻이라 이 블록 전체를 건너뛴다 — latest.html은
    # 아래에서도 손대지 않는다(마지막으로 성공한 daily 상태 그대로 유지).
    safe_email = None
    if today_included:
        email_path = os.path.join(ROOT, "latest-email.html")
        if not os.path.exists(email_path):
            report["aborted"] = True
            report["abort_reason"] = "latest-email.html 없음"
            return report
        raw_email = open(email_path, encoding="utf-8").read()
        content_date = lib.extract_kst_date_from_html(raw_email)
        report["latest_email_content_date"] = content_date
        if content_date != TODAY:
            report["aborted"] = True
            report["abort_reason"] = f"latest-email.html 콘텐츠 날짜({content_date}) != 기대값({TODAY})"
            return report

        pre_audit = lib.audit_privacy(raw_email)
        safe_email = lib.make_public_safe_html(raw_email)
        post_audit = lib.audit_privacy(safe_email)
        report["latest_email_privacy_pre_strip_issues"] = pre_audit
        report["latest_email_privacy_post_strip_issues"] = post_audit
        if post_audit:
            report["aborted"] = True
            report["abort_reason"] = f"public-safe 변환 후에도 개인정보 이슈 잔존: {post_audit}"
            return report

    # ── 4. 임시 디렉터리에 페이지 생성 ───────────────────────────────
    # 2026-08-21(TASK_ID=TRACK_B7_ARCHIVE_AUTOMATION): 발견한 회귀 —
    # TODAY는 하루만 유효하다. 다음날 이 오케스트레이터가 다시 돌면 어제의
    # TODAY는 더 이상 TODAY가 아니라서 render_from_json_record()로 다시
    # 렌더되는데, JSON 레코드는 정규화된 요약이라 실제 발송 HTML(오늘
    # 렌더 경로)보다 훨씬 얇다 — 이미 공개된 풍부한 콘텐츠가 조용히
    # 얇은 재구성본으로 강등된다(2026-08-11 페이지에서 935줄→159줄로
    # 실측 확인). 이미 실제 이메일 렌더로 발행된 페이지는 절대 다시
    # 만들지 않고 그대로 보존한다 — 이메일 전용 메타 태그(JSON 재구성
    # 경로에는 없는)로 "실이메일 렌더본"임을 판별한다.
    if os.path.exists(BUILD_TMP):
        shutil.rmtree(BUILD_TMP)
    os.makedirs(os.path.join(BUILD_TMP, "issues"))

    rendered = {}
    preserved_rich_pages = []
    for date in valid_dates:
        meta = meta_by_date[date]
        existing_path = os.path.join(ROOT, "issues", f"{date}.html")
        if date == TODAY:
            page_html = bip.render_from_public_safe_email(safe_email, meta)
        elif os.path.exists(existing_path) and lib.is_rich_email_render(
            open(existing_path, encoding="utf-8").read()
        ):
            page_html = open(existing_path, encoding="utf-8").read()
            preserved_rich_pages.append(date)
        else:
            page_html = bip.render_from_json_record(by_date[date], meta)
        rendered[date] = page_html
        with open(os.path.join(BUILD_TMP, "issues", f"{date}.html"), "w", encoding="utf-8") as f:
            f.write(page_html)
    report["preserved_rich_pages"] = preserved_rich_pages

    # ── 5. 각 페이지 검사 ────────────────────────────────────────────
    page_checks = {}
    passing_dates = []
    for date, page_html in rendered.items():
        privacy_issues = lib.audit_privacy(page_html)
        html_issues = lib.validate_html(page_html)
        page_checks[date] = {"privacy_issues": privacy_issues, "html_issues": html_issues}
        ok = not privacy_issues and not html_issues
        if ok:
            passing_dates.append(date)
            meta_by_date[date]["privacy_audit_passed"] = True
        else:
            meta_by_date[date]["privacy_audit_passed"] = False
    report["page_checks"] = page_checks
    report["passing_dates"] = passing_dates

    if today_included and TODAY not in passing_dates:
        report["aborted"] = True
        report["abort_reason"] = f"오늘({TODAY}) 페이지가 검사 통과하지 못함: {page_checks.get(TODAY)}"
        return report

    # ── 6. 통과 항목만 매니페스트 후보로 ─────────────────────────────
    passing_metas = [meta_by_date[d] for d in passing_dates]

    # ── 7. 월간/전체 아카이브(통과분만, 0건인 달은 생성하지 않음) ────
    months = {}
    for m in passing_metas:
        months.setdefault(m["issue_date"][:7], []).append(m)

    os.makedirs(os.path.join(BUILD_TMP, "archive"), exist_ok=True)
    full_index_html = bap.build_full_index(passing_metas)
    with open(os.path.join(BUILD_TMP, "archive", "index.html"), "w", encoding="utf-8") as f:
        f.write(full_index_html)

    month_pages = {}
    for ym, items in months.items():
        month_html = bap.build_month_index(ym, items)
        month_dir = os.path.join(BUILD_TMP, "archive", ym)
        os.makedirs(month_dir, exist_ok=True)
        with open(os.path.join(month_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(month_html)
        month_pages[ym] = len(items)
    report["month_pages_built"] = month_pages

    # 아카이브 페이지 자체도 검사(태그 밸런스만 — 개인정보는 issue
    # metadata만 쓰므로 원천적으로 없음, 그래도 이중 확인).
    archive_page_checks = {"archive/index.html": lib.validate_html(full_index_html)}
    for ym in month_pages:
        with open(os.path.join(BUILD_TMP, "archive", ym, "index.html"), encoding="utf-8") as f:
            archive_page_checks[f"archive/{ym}/index.html"] = lib.validate_html(f.read())
    report["archive_page_checks"] = archive_page_checks
    if any(v for v in archive_page_checks.values()):
        report["aborted"] = True
        report["abort_reason"] = f"아카이브 페이지 HTML 검사 실패: {archive_page_checks}"
        return report

    # ── latest.html 임시본 = 오늘자 issue 페이지와 동일 산출물 ───────
    # today_included가 False면 오늘자 콘텐츠 자체가 없으므로 latest.html은
    # 만들지도, 아래 8단계에서 교체하지도 않는다(마지막 성공한 daily 상태 유지).
    latest_tmp_path = None
    if today_included:
        latest_tmp_path = os.path.join(BUILD_TMP, "latest.html")
        with open(latest_tmp_path, "w", encoding="utf-8") as f:
            f.write(rendered[TODAY])

    # ── 내부 링크 존재 검사(임시 디렉터리를 site_root로 취급) ────────
    link_issues = {}
    for date in passing_dates:
        with open(os.path.join(BUILD_TMP, "issues", f"{date}.html"), encoding="utf-8") as f:
            issues_ = lib.check_internal_links(f.read(), BUILD_TMP)
        if issues_:
            link_issues[f"issues/{date}.html"] = issues_
    with open(os.path.join(BUILD_TMP, "archive", "index.html"), encoding="utf-8") as f:
        li = lib.check_internal_links(f.read(), BUILD_TMP)
        if li:
            link_issues["archive/index.html"] = li
    report["internal_link_issues"] = link_issues
    if link_issues:
        report["aborted"] = True
        report["abort_reason"] = f"내부 링크 깨짐: {link_issues}"
        return report

    # ── manifest 작성(임시 디렉터리에, 8단계 전까지는 실제 경로 미접촉) ─
    manifest = [
        {k: v for k, v in m.items() if k not in ("prev_date", "next_date")}
        for m in passing_metas
    ]
    manifest_tmp_path = os.path.join(BUILD_TMP, "issues_manifest.json")
    with open(manifest_tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    report["manifest_entry_count"] = len(manifest)

    # 2026-08-24(TASK_ID=W7_ARCHIVE_ABORT_MITIGATION): "오늘만 제외"가
    # 이제 fatal이 아니게 되면서 새로 생긴 위험 — 만약 이번 실행에서
    # ARCHIVE_DIR 복원 자체가 어떤 이유로 비정상적으로 비거나 줄어들면
    # (예: web_repo 복원 스텝 실패), 예전엔 오늘 검증에서 걸려 여기까지
    # 못 왔지만 지금은 여기까지 도달해 실제 라이브 아카이브를 그 얇아진
    # 상태로 덮어쓸 수 있다. manifest 건수가 현재 라이브보다 줄었으면
    # 데이터 유실로 간주하고 실제 경로 교체를 중단한다(단조 증가 불변식).
    live_manifest_path = os.path.join(ROOT, "data", "archive", "issues_manifest.json")
    live_count = 0
    if os.path.exists(live_manifest_path):
        try:
            with open(live_manifest_path, encoding="utf-8") as f:
                live_count = len(json.load(f))
        except Exception:
            live_count = 0
    report["live_manifest_count_before"] = live_count
    if len(manifest) < live_count:
        report["aborted"] = True
        report["abort_reason"] = (
            f"신규 manifest 건수({len(manifest)})가 기존 라이브 건수({live_count})보다 적음 "
            "— 데이터 유실 의심, 실제 경로 교체 중단"
        )
        return report

    # ── sitemap.xml / rss.xml (같은 manifest에서, 같은 원자적 교체에 포함) ─
    sitemap_xml = bsm.build_sitemap(manifest)
    rss_xml = brss.build_rss(manifest)
    xml_issues = {
        "sitemap.xml": bsm.validate_sitemap_xml(sitemap_xml),
        "rss.xml": brss.validate_rss_xml(rss_xml),
    }
    report["xml_issues"] = xml_issues
    if any(xml_issues.values()):
        report["aborted"] = True
        report["abort_reason"] = f"sitemap/rss XML 검증 실패: {xml_issues}"
        return report
    sitemap_tmp_path = os.path.join(BUILD_TMP, "sitemap.xml")
    with open(sitemap_tmp_path, "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    rss_tmp_path = os.path.join(BUILD_TMP, "rss.xml")
    with open(rss_tmp_path, "w", encoding="utf-8") as f:
        f.write(rss_xml)

    if dry_run_report_only:
        report["swapped_to_real_paths"] = False
        return report

    # ── 8. 전체 통과 → 실제 경로로 교체(백업 포함) ───────────────────
    # latest.html은 today_included일 때만 교체한다 — 오늘 것이 없으면
    # (Weekly 월요일/진짜 daily 실패) 마지막으로 성공한 daily를 그대로 둔다.
    if today_included:
        backup_path = os.path.join(ROOT, "latest.html.bak")
        if os.path.exists(os.path.join(ROOT, "latest.html")):
            shutil.copy2(os.path.join(ROOT, "latest.html"), backup_path)
            report["latest_html_backed_up_to"] = backup_path

        shutil.copy2(latest_tmp_path, os.path.join(ROOT, "latest.html"))

    real_issues_dir = os.path.join(ROOT, "issues")
    os.makedirs(real_issues_dir, exist_ok=True)
    for date in passing_dates:
        shutil.copy2(os.path.join(BUILD_TMP, "issues", f"{date}.html"), os.path.join(real_issues_dir, f"{date}.html"))

    real_archive_dir = os.path.join(ROOT, "archive")
    os.makedirs(real_archive_dir, exist_ok=True)
    shutil.copy2(os.path.join(BUILD_TMP, "archive", "index.html"), os.path.join(real_archive_dir, "index.html"))
    for ym in month_pages:
        real_month_dir = os.path.join(real_archive_dir, ym)
        os.makedirs(real_month_dir, exist_ok=True)
        shutil.copy2(os.path.join(BUILD_TMP, "archive", ym, "index.html"), os.path.join(real_month_dir, "index.html"))

    os.makedirs(os.path.join(ROOT, "data", "archive"), exist_ok=True)
    shutil.copy2(manifest_tmp_path, os.path.join(ROOT, "data", "archive", "issues_manifest.json"))

    shutil.copy2(sitemap_tmp_path, os.path.join(ROOT, "sitemap.xml"))
    shutil.copy2(rss_tmp_path, os.path.join(ROOT, "rss.xml"))

    report["swapped_to_real_paths"] = True
    return report


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    today_override = None
    if "--today" in sys.argv:
        today_override = sys.argv[sys.argv.index("--today") + 1]
    edition_mode_path = "output/edition_mode.txt"
    if "--edition-mode-path" in sys.argv:
        edition_mode_path = sys.argv[sys.argv.index("--edition-mode-path") + 1]
    result = run(dry_run_report_only=dry, today=today_override, edition_mode_path=edition_mode_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["aborted"] else 0)
