"""2026-08-24(TASK_ID=W6_WEEKLY_WEB_WIRING)
Weekly(run_weekly()) 산출물을 웹에 연결하는 오케스트레이터.

daily의 publish_issue_archive.py와 의도적으로 완전히 분리했다 — daily
아카이브는 지금 막 정지(W_TRACK_WEB_FULL_AUDIT 2026-08-24)에서 복구
검증 중이라, 여기에 위클리를 얹으면 회귀 리스크가 같이 커진다. 위클리는
"data/weekly/index.json"을 유일한 목록 소스로 쓰고, /weekly/{week_id}.html
퍼머링크만 별도로 만든다. daily의 issues_manifest.json/archive/ 스키마는
전혀 건드리지 않는다.

호출부(daily.yml)는 이 실행 1회당 위클리 산출물이 최대 1쌍(JSON 1개 +
스크럽된 HTML 1개)만 있다는 것을 이미 알고 있으므로, 두 경로를 명시
인자로 넘긴다 — 파일명 상관관계(수록 날짜 vs 커버 주차)를 이 스크립트가
추론할 필요가 없다.

개인정보 스크럽은 호출부(daily.yml)가 이미 issue_archive_lib.
make_public_safe_html()로 끝내고 스크럽을 통과한 결과만 이 스크립트에
넘긴다(원문은 web_repo 근처에도 온 적이 없다). 이 스크립트는 그 전제를
맹신하지 않고 audit_privacy()로 한 번 더 방어적으로 확인한다 — daily
쪽(publish_issue_archive.py)도 같은 이중 확인 패턴을 쓴다.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import issue_archive_lib as lib
import build_weekly_page as bwp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WEEKLY_DATA_DIR = os.path.join(ROOT, "data", "weekly")
WEEKLY_PAGE_DIR = os.path.join(ROOT, "weekly")


def _load_index_entries():
    """web_repo/data/weekly/*.json(방금 동기화된 새 파일 포함, index.json
    자신은 제외)에서 index.json 재생성에 필요한 3필드만 뽑는다 — 별도
    append/병합 로직 없이 매번 소스에서 전체를 다시 만든다(daily 아카이브의
    "매번 유효분 전체 재구성" 철학과 동일, append 누락/중복 걱정이 없다)."""
    entries = []
    load_errors = []
    if not os.path.isdir(WEEKLY_DATA_DIR):
        return entries, load_errors
    for name in sorted(os.listdir(WEEKLY_DATA_DIR)):
        if not name.endswith(".json") or name == "index.json":
            continue
        path = os.path.join(WEEKLY_DATA_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            entries.append({
                "week_id": rec["week_id"],
                "period_start_kst": rec["period_start_kst"],
                "period_end_kst": rec["period_end_kst"],
            })
        except Exception as e:
            load_errors.append({"file": name, "error": str(e)})
    entries.sort(key=lambda e: e["period_start_kst"])
    return entries, load_errors


def run(week_json_path=None, scrubbed_html_path=None):
    report = {"aborted": False, "abort_reason": None}

    if not week_json_path and not scrubbed_html_path:
        report["skipped"] = True
        report["skip_reason"] = "이번 실행엔 위클리 산출물 없음(평시 Daily) - 정상"
        return report

    # ── index.json 재생성(항상 시도 — JSON만 있어도 weekly.html 목록은 갱신) ──
    entries, load_errors = _load_index_entries()
    report["index_entry_count"] = len(entries)
    report["load_errors"] = load_errors
    index_tmp = os.path.join(WEEKLY_DATA_DIR, "index.json.tmp")
    index_path = os.path.join(WEEKLY_DATA_DIR, "index.json")
    with open(index_tmp, "w", encoding="utf-8") as f:
        json.dump({"schemaVersion": 1, "weeks": list(reversed(entries))}, f,
                   ensure_ascii=False, indent=2)
    os.replace(index_tmp, index_path)
    report["index_updated"] = True

    if not scrubbed_html_path:
        report["permalink_built"] = False
        report["permalink_skip_reason"] = "스크럽된 HTML 없음(JSON만 갱신)"
        return report

    if not os.path.exists(scrubbed_html_path):
        report["aborted"] = True
        report["abort_reason"] = f"scrubbed-html 경로가 실제로는 없음: {scrubbed_html_path}"
        return report
    if not week_json_path or not os.path.exists(week_json_path):
        report["aborted"] = True
        report["abort_reason"] = f"week-json 경로가 실제로는 없음: {week_json_path}"
        return report

    with open(week_json_path, encoding="utf-8") as f:
        week_record = json.load(f)
    week_id = week_record["week_id"]
    report["week_id"] = week_id

    safe_html = open(scrubbed_html_path, encoding="utf-8").read()
    # 호출부가 이미 스크럽을 끝냈다는 전제를 맹신하지 않고 한 번 더 확인
    # (daily 쪽 publish_issue_archive.py와 동일한 이중 확인 패턴).
    post_issues = lib.audit_privacy(safe_html)
    report["privacy_recheck_issues"] = post_issues
    if post_issues:
        report["aborted"] = True
        report["abort_reason"] = f"스크럽 재확인 실패(호출부 결과를 신뢰할 수 없음): {post_issues}"
        return report

    # ── prev/next 계산: issue_archive_lib.compute_prev_next()는 issue_date/
    # public_path 키를 기대한다 — 날짜 정렬 키만 period_start_kst로 맞춰
    # 재사용한다(daily 전용 함수가 아니라 그대로 재사용 가능, 새로 안 만든다).
    # entries에는 data/weekly/*.json만 있고 실제 /weekly/{id}.html 페이지가
    # 없는 옛 fixture(2026-W31/W32, 이 파이프라인 이전의 베타 산출물)가
    # 섞여 있을 수 있다 — 그런 항목을 prev/next에 링크하면
    # check_internal_links()가 깨진 링크로 정확히 잡아낸다(실측 확인됨).
    # 실제 페이지가 있는 주(이번에 새로 만드는 주 포함)만 체인 대상으로 삼는다.
    linkable = [
        e for e in entries
        if e["week_id"] == week_id
        or os.path.exists(os.path.join(WEEKLY_PAGE_DIR, f"{e['week_id']}.html"))
    ]
    nav_metas = [
        {"issue_date": e["period_start_kst"], "public_path": f"/weekly/{e['week_id']}.html",
         "week_id": e["week_id"]}
        for e in linkable
    ]
    nav_metas = lib.compute_prev_next(nav_metas)
    this_nav = next((m for m in nav_metas if m["week_id"] == week_id), None)

    meta = {
        "week_id": week_id,
        "public_path": f"/weekly/{week_id}.html",
        "title": f"Mooconomy WEEKLY {week_id} 리캡",
        "morning_thesis": week_record.get("weekly_thesis"),
        "published_at": None,
        "published_at_is_approximate": True,
        "prev_path": (this_nav or {}).get("prev_path"),
        "prev_week_id": (this_nav or {}).get("prev_date"),
        "next_path": (this_nav or {}).get("next_path"),
        "next_week_id": (this_nav or {}).get("next_date"),
    }

    page_html = bwp.render_weekly_page(safe_html, meta)

    html_issues = lib.validate_html(page_html)
    if html_issues:
        report["aborted"] = True
        report["abort_reason"] = f"위클리 페이지 HTML 검사 실패: {html_issues}"
        return report

    # publish_issue_archive.py는 이 검사 전에 _build_tmp/에 파일을 먼저
    # 써두는데, 그 디렉터리는 "다음 실행 시작 시" 정리될 뿐이라 검사 단계
    # (여기, HTML 밸런스 이후)에서 abort하면 web_repo 안에 임시 디렉터리가
    # 그대로 남아 이후 git add -A에 같이 잡힐 수 있는 잠재 결함이 있다
    # (실측: 이 스크립트도 처음엔 같은 패턴으로 만들었다가 로컬 sandbox
    # 테스트에서 실제로 재현됨 — 2026-08-24). validate_html/
    # check_internal_links 둘 다 문자열만 있으면 검사 가능하므로, 아예
    # 디스크에 먼저 쓰지 않고 인메모리 문자열로 전부 검사한 뒤 최종
    # 경로에 "한 번만" 쓴다 — 임시 디렉터리 자체가 없으니 정리 누락도
    # 구조적으로 없다.
    link_issues = lib.check_internal_links(page_html, ROOT)
    report["internal_link_issues"] = link_issues
    if link_issues:
        report["aborted"] = True
        report["abort_reason"] = f"내부 링크 깨짐: {link_issues}"
        return report

    # ── 전부 통과 → 실제 경로에 최초 1회 기록 ──────────────────────────
    os.makedirs(WEEKLY_PAGE_DIR, exist_ok=True)
    with open(os.path.join(WEEKLY_PAGE_DIR, f"{week_id}.html"), "w", encoding="utf-8") as f:
        f.write(page_html)

    report["permalink_built"] = True
    report["permalink_path"] = f"/weekly/{week_id}.html"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-json", default="")
    parser.add_argument("--scrubbed-html", default="")
    args = parser.parse_args()
    result = run(
        week_json_path=args.week_json or None,
        scrubbed_html_path=args.scrubbed_html or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result.get("aborted") else 0)
