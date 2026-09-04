"""2026-08-24(TASK_ID=W6_WEEKLY_WEB_WIRING)
Weekly(run_weekly()) 산출물을 웹에 연결하는 오케스트레이터.

daily의 publish_issue_archive.py와 의도적으로 완전히 분리했다 — daily
아카이브는 지금 막 정지(W_TRACK_WEB_FULL_AUDIT 2026-08-24)에서 복구
검증 중이라, 여기에 위클리를 얹으면 회귀 리스크가 같이 커진다. 위클리는
"data/weekly/index.json"을 유일한 목록 소스로 쓰고, /weekly/{week_id}.html
퍼머링크만 별도로 만든다. daily의 issues_manifest.json/archive/ 스키마는
전혀 건드리지 않는다.

호출부(daily.yml)는 이 실행 1회당 위클리 산출물이 최대 1쌍(JSON 1개 +
렌더된 HTML 1개)만 있다는 것을 이미 알고 있으므로, 두 경로를 명시
인자로 넘긴다 — 파일명 상관관계(수록 날짜 vs 커버 주차)를 이 스크립트가
추론할 필요가 없다.

2026-09-04(TASK_ID=WEEKLY_PHASE0_RUNTIME_SAFETY, C) — 아래 두 계약을
daily(publish_issue_archive.py)와 동일하게 맞췄다(이전 버전은 이 둘이
daily와 어긋나 있었고, 실제로는 어느 쪽도 배선되지 않아 발견되지 않고
있었다 — 감사 docs/weekly-current-pipeline-audit.md F-3):
  1. 개인정보 스크럽은 호출부가 아니라 이 스크립트 자신이 한다
     (issue_archive_lib.make_public_safe_html() 직접 호출). CLI 인자
     이름도 `--scrubbed-html`(스크럽 완료 전제)에서 `--weekly-html`
     (원본)로 바꿔 계약을 명확히 한다.
  2. `--week-json`으로 받은 파일을 이 스크립트가 스스로
     data/weekly/{week_id}.json으로 복사한다. 이전 버전은 이 복사
     자체가 호출부·이 스크립트 어디에도 없어 _load_index_entries()가
     방금 발행된 주를 영영 못 보는 상태였다.
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
# 2026-09-04(C) — "latest Weekly alias": canonical(/weekly/{week_id}.html)과
# archive index(weekly.html + data/weekly/index.json)와는 역할이 다른
# 세 번째 경로. daily의 latest.html(항상 최신 발행일로 덮어써지는 고정
# 링크)과 같은 개념을 Weekly에 도입한다 — 이전에는 "최신 위클리"를
# 가리키는 안정적인 URL이 아예 없었다.
WEEKLY_LATEST_ALIAS_PATH = os.path.join(ROOT, "weekly-latest.html")


def _load_index_entries():
    """web_repo/data/weekly/*.json(방금 동기화된 새 파일 포함, index.json
    자신은 제외)에서 index.json 재생성에 필요한 필드만 뽑는다 — 별도
    append/병합 로직 없이 매번 소스에서 전체를 다시 만든다(daily 아카이브의
    "매번 유효분 전체 재구성" 철학과 동일, append 누락/중복 걱정이 없다).

    2026-09-04(C) — has_canonical_page 필드 추가: 이 주에 실제
    /weekly/{week_id}.html 페이지가 있는지를 인덱스에 미리 계산해
    넣는다. weekly.html(클라이언트)이 매주마다 파일 존재를 따로 조회할
    방법이 없으므로(정적 사이트, 디렉터리 리스팅 불가) 서버 측(이
    스크립트)이 한 번만 계산해 넘긴다."""
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
            week_id = rec["week_id"]
            entries.append({
                "week_id": week_id,
                "period_start_kst": rec["period_start_kst"],
                "period_end_kst": rec["period_end_kst"],
                "has_canonical_page": os.path.exists(
                    os.path.join(WEEKLY_PAGE_DIR, f"{week_id}.html")),
            })
        except Exception as e:
            load_errors.append({"file": name, "error": str(e)})
    entries.sort(key=lambda e: e["period_start_kst"])
    return entries, load_errors


def _rebuild_index():
    """data/weekly/*.json에서 index.json을 다시 만든다. run()이 두 지점
    (week_json 동기화 직후, permalink 기록 직후)에서 호출한다 — 두 번째
    호출이 필요한 이유: 첫 호출 시점엔 아직 이번 주 /weekly/{week_id}.html
    permalink가 존재하지 않아 has_canonical_page가 False로 계산된다."""
    entries, load_errors = _load_index_entries()
    index_tmp = os.path.join(WEEKLY_DATA_DIR, "index.json.tmp")
    index_path = os.path.join(WEEKLY_DATA_DIR, "index.json")
    with open(index_tmp, "w", encoding="utf-8") as f:
        json.dump({"schemaVersion": 1, "weeks": list(reversed(entries))}, f,
                   ensure_ascii=False, indent=2)
    os.replace(index_tmp, index_path)
    return entries, load_errors


def run(week_json_path=None, weekly_html_path=None):
    report = {"aborted": False, "abort_reason": None}

    if not week_json_path and not weekly_html_path:
        report["skipped"] = True
        report["skip_reason"] = "이번 실행엔 위클리 산출물 없음(평시 Daily) - 정상"
        return report

    if not week_json_path or not os.path.exists(week_json_path):
        report["aborted"] = True
        report["abort_reason"] = f"week-json 경로가 실제로는 없음: {week_json_path}"
        return report

    with open(week_json_path, encoding="utf-8") as f:
        raw_week_json = f.read()
        week_record = json.loads(raw_week_json)
    week_id = week_record["week_id"]
    report["week_id"] = week_id

    # ── week_json을 데이터 디렉터리에 자기 자신이 반영(위 docstring §2) ──
    os.makedirs(WEEKLY_DATA_DIR, exist_ok=True)
    week_data_path = os.path.join(WEEKLY_DATA_DIR, f"{week_id}.json")
    tmp = week_data_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(raw_week_json)
    os.replace(tmp, week_data_path)
    report["week_json_synced_to"] = week_data_path

    # ── index.json 재생성(항상 시도 — 위 동기화 직후라 이번 주도 포함됨) ──
    entries, load_errors = _rebuild_index()
    report["index_entry_count"] = len(entries)
    report["load_errors"] = load_errors
    report["index_updated"] = True

    if not weekly_html_path:
        report["permalink_built"] = False
        report["permalink_skip_reason"] = "위클리 HTML 없음(JSON만 갱신)"
        return report

    if not os.path.exists(weekly_html_path):
        report["aborted"] = True
        report["abort_reason"] = f"weekly-html 경로가 실제로는 없음: {weekly_html_path}"
        return report

    raw_html = open(weekly_html_path, encoding="utf-8").read()
    # 개인정보 스크럽은 이 스크립트가 직접 수행한다(위 docstring §1,
    # daily의 publish_issue_archive.py와 동일 패턴) — 호출부가 이미
    # 스크럽했다는 가정을 두지 않는다.
    pre_audit = lib.audit_privacy(raw_html)
    safe_html = lib.make_public_safe_html(raw_html)
    post_issues = lib.audit_privacy(safe_html)
    report["privacy_pre_strip_issues"] = pre_audit
    report["privacy_post_strip_issues"] = post_issues
    if post_issues:
        report["aborted"] = True
        report["abort_reason"] = f"public-safe 변환 후에도 개인정보 이슈 잔존: {post_issues}"
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
        if e["week_id"] == week_id or e["has_canonical_page"]
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

    # latest Weekly alias(위 docstring/모듈 상수 참고) — canonical/archive
    # index와 별개로 항상 "가장 최근 발행된 Weekly"를 가리키는 고정 경로.
    tmp = WEEKLY_LATEST_ALIAS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page_html)
    os.replace(tmp, WEEKLY_LATEST_ALIAS_PATH)

    # 2026-09-04(C) — 위에서 이미 index.json을 한 번 만들었지만(그 시점엔
    # 아직 이번 주 permalink 파일이 없어 has_canonical_page가 False로
    # 계산됐다), 방금 permalink를 실제로 썼으니 인덱스를 다시 계산해
    # 이번 주도 has_canonical_page=True로 반영한다 — 그렇지 않으면 이번
    # 실행에서 막 발행한 주가 "실제 발행본 보기" 링크 없이 다음 실행까지
    # 하루 지연돼 노출된다.
    entries, load_errors = _rebuild_index()
    report["index_entry_count"] = len(entries)
    report["load_errors"] = load_errors

    report["permalink_built"] = True
    report["permalink_path"] = f"/weekly/{week_id}.html"
    report["latest_alias_path"] = "/weekly-latest.html"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-json", default="")
    parser.add_argument("--weekly-html", default="")
    args = parser.parse_args()
    result = run(
        week_json_path=args.week_json or None,
        weekly_html_path=args.weekly_html or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # D. 상태·관측성 — SEND_SUCCESS(이 스크립트 호출 시점엔 이미 확정된
    # 과거 사실)와 이 스크립트의 성패를 서로 다른 로그 라인으로 분리한다.
    if result.get("skipped"):
        print("ARCHIVE_PUBLISH_ATTEMPTED=false ARCHIVE_PUBLISH_SUCCESS=skipped")
    else:
        print(f"ARCHIVE_PUBLISH_ATTEMPTED=true week_id={result.get('week_id')}")
        print(f"ARCHIVE_PUBLISH_SUCCESS={'false' if result.get('aborted') else 'true'} "
              f"reason={result.get('abort_reason')}")
    sys.exit(1 if result.get("aborted") else 0)
