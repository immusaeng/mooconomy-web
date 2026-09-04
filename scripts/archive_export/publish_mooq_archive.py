"""MOO:Q canonical store -> 웹 저장소 파생 파일 오케스트레이터.

순서 고정(CEO 지시):
  data/claims_store.json(canonical, 읽기 전용)
    -> export.build_question_record() / export.build_home_claims()
    -> build_questions_page.build_page()
  전부 임시 디렉터리에서 생성·검증한 뒤에만 실제 경로로 원자적 교체:
    data/home.json  (claims 필드만 갱신 — 다른 필드는 재검증까지 해서 불변을 보장)
    questions/index.html

claims_store.json 전체를 매번 claimId 키로 다시 빌드하므로(append가 아님)
구조적으로 idempotent하다 — 같은 store를 다시 돌려도 바이트 동일 산출물이
나오고, 새 claimId가 store에 추가된 경우에만 결과가 바뀐다. claims_store.json
자체는 이 스크립트가 절대 쓰지 않는다(publish_issue_archive.py와 동일한
all-or-nothing 패턴 — 검증 중 하나라도 실패하면 report["aborted"]=True를
반환하고 실제 경로를 전혀 건드리지 않는다).

새 LLM 호출·네트워크 호출 없음.
"""
import json
import os
import shutil
import sys

import jsonschema

sys.path.insert(0, os.path.dirname(__file__))
import export as archive_export  # noqa: E402
import build_questions_page as bqp  # noqa: E402
import issue_archive_lib as lib  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CLAIMS_STORE_PATH = os.path.join(ROOT, "data", "claims_store.json")
HOME_JSON_PATH = os.path.join(ROOT, "data", "home.json")
QUESTIONS_PATH = os.path.join(ROOT, "questions", "index.html")
SCHEMAS_DIR = os.path.join(ROOT, "schemas")
BUILD_TMP = os.path.join(ROOT, "_build_tmp_mooq")


def run(claims_store_path=None, home_json_path=None, questions_path=None, dry_run_report_only=False):
    claims_store_path = claims_store_path or CLAIMS_STORE_PATH
    home_json_path = home_json_path or HOME_JSON_PATH
    questions_path = questions_path or QUESTIONS_PATH
    report = {"aborted": False, "abort_reason": None}

    if not os.path.exists(claims_store_path):
        report["aborted"] = True
        report["abort_reason"] = "data/claims_store.json 없음 — canonical store 없이 발행 불가"
        return report
    with open(claims_store_path, encoding="utf-8") as f:
        claims_store = json.load(f)
    claims = claims_store.get("claims") or {}
    report["claims_store_count"] = len(claims)
    if not claims:
        report["aborted"] = True
        report["abort_reason"] = "claims_store.json에 claim이 0건 — 발행 스킵(기존 파일 보존)"
        return report

    # ── claimId 유일성(구조적 idempotency의 전제) ────────────────────
    claim_ids = list(claims.keys())
    if len(claim_ids) != len(set(claim_ids)):
        report["aborted"] = True
        report["abort_reason"] = "claims_store.json에 claimId 중복 존재"
        return report

    # ── 1. question_records 생성 + 스키마 검증 ───────────────────────
    # 알 수 없는 claim.status는 export._verdict_field()가
    # UnknownVerdictError로 던진다 — 임의 매핑하지 않고 발행 자체를 막는다.
    try:
        records = [archive_export.build_question_record(c) for cid, c in sorted(claims.items())]
    except archive_export.verdict_labels.UnknownVerdictError as e:
        report["aborted"] = True
        report["abort_reason"] = str(e)
        return report
    if len(records) != len(claims):
        report["aborted"] = True
        report["abort_reason"] = f"question_records 개수 불일치: {len(records)} != {len(claims)}"
        return report

    with open(os.path.join(SCHEMAS_DIR, "question-record.schema.json"), encoding="utf-8") as f:
        schema = json.load(f)
    schema_errors = []
    for rec in records:
        try:
            jsonschema.validate(instance=rec, schema=schema)
        except jsonschema.ValidationError as e:
            schema_errors.append(f"{rec.get('question_id')}: {e.message}")
    report["question_record_schema_errors"] = schema_errors
    if schema_errors:
        report["aborted"] = True
        report["abort_reason"] = f"question_records 스키마 검증 실패: {schema_errors}"
        return report

    # ── 2. questions/index.html 렌더 + HTML/링크 검사(임시 디렉터리) ──
    questions_html = bqp.build_page(records)
    html_issues = lib.validate_html(questions_html)
    if html_issues:
        report["aborted"] = True
        report["abort_reason"] = f"questions/index.html HTML 검증 실패: {html_issues}"
        return report

    if os.path.exists(BUILD_TMP):
        shutil.rmtree(BUILD_TMP)
    os.makedirs(BUILD_TMP)
    tmp_questions_path = os.path.join(BUILD_TMP, "questions_index.html")
    with open(tmp_questions_path, "w", encoding="utf-8") as f:
        f.write(questions_html)

    # BUILD_TMP에는 questions/index.html 자체 경로가 없어 /questions/
    # 자기참조 링크가 오탐될 수 있으므로 fallback_root(ROOT)로 실제
    # 저장소를 재확인한다(publish_issue_archive.py와 동일 관례).
    link_issues = lib.check_internal_links(questions_html, BUILD_TMP, fallback_root=ROOT)
    report["questions_link_issues"] = link_issues
    if link_issues:
        report["aborted"] = True
        report["abort_reason"] = f"questions/index.html 내부 링크 깨짐: {link_issues}"
        return report

    # ── 3. home.json.claims 생성 — claims 외 필드는 절대 건드리지 않는다 ─
    home_claims = archive_export.build_home_claims(claims_store)
    if not os.path.exists(home_json_path):
        report["aborted"] = True
        report["abort_reason"] = "data/home.json 없음"
        return report
    with open(home_json_path, encoding="utf-8") as f:
        home = json.load(f)
    home_before_keys = set(home.keys())
    new_home = dict(home)
    new_home["claims"] = home_claims
    if set(new_home.keys()) != home_before_keys:
        report["aborted"] = True
        report["abort_reason"] = "home.json 키 집합이 claims 갱신 중 변경됨(다른 필드 오염 의심)"
        return report

    tmp_home_path = os.path.join(BUILD_TMP, "home.json")
    with open(tmp_home_path, "w", encoding="utf-8") as f:
        json.dump(new_home, f, ensure_ascii=False, indent=2)
        f.write("\n")
    # 재검증: 다시 읽어서 claims 외 필드가 원본과 완전히 동일한지 재확인.
    with open(tmp_home_path, encoding="utf-8") as f:
        reloaded_home = json.load(f)
    for key in home_before_keys - {"claims"}:
        if reloaded_home.get(key) != home.get(key):
            report["aborted"] = True
            report["abort_reason"] = f"home.json 필드 '{key}'가 claims 갱신 중 변경됨"
            return report

    report["question_record_count"] = len(records)
    report["home_claims_previous_count"] = len(home_claims["previousClaims"])
    report["home_claims_today_count"] = len(home_claims["todayClaims"])

    if dry_run_report_only:
        report["swapped_to_real_paths"] = False
        shutil.rmtree(BUILD_TMP, ignore_errors=True)
        return report

    # ── 4. 전체 통과 → 실제 경로로 원자적 교체(os.replace) ────────────
    os.replace(tmp_home_path, home_json_path)
    os.makedirs(os.path.dirname(questions_path), exist_ok=True)
    os.replace(tmp_questions_path, questions_path)
    shutil.rmtree(BUILD_TMP, ignore_errors=True)

    report["swapped_to_real_paths"] = True
    return report


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    result = run(dry_run_report_only=dry)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["aborted"] else 0)
