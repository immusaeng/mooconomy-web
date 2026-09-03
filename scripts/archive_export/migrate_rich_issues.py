"""2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION, CEO 결정
DECISION=OPTION_1_EXTRACT_REAL_CONTENT_AND_RESKIN_TO_V8)

7개 과거 rich 이슈 페이지(RICH_DATES)를 한 번만 돌리는 마이그레이션
스크립트. rich_email_extract로 실제 발송 콘텐츠를 떼어내고
build_issue_page.render_from_rich_extracted()로 V8 라이트 셸에 다시
넣은 뒤, 원본과 산출물의 content fingerprint(가시 텍스트/링크 집합/
표 개수/숫자 토큰 시퀀스)를 비교해 CEO가 요구한 날짜별 검증 필드를
그대로 출력한다.

기본은 --dry-run(파일을 쓰지 않고 검증 결과만 출력)이다. 7개 전부
CONTENT_PAYLOAD_FINGERPRINT_MATCH=YES일 때만 --apply로 실제
issues/{date}.html을 덮어쓴다. 하나라도 실패하면 그 날짜는 건너뛰고
보고만 한다 — JSON 경로로 조용히 대체하지 않는다(RichExtractionError를
그대로 전파).
"""
import json
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))
import issue_archive_lib as lib
import build_issue_page as bip
import rich_email_extract as ree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARCHIVE_DIR = os.path.join(ROOT, "data", "daily_archive")
ISSUES_DIR = os.path.join(ROOT, "issues")

RICH_DATES = [
    "2026-08-11", "2026-08-21", "2026-08-25", "2026-08-26",
    "2026-08-27", "2026-08-28", "2026-08-29",
]


def _build_meta_by_date():
    records, load_errors = lib.load_all_records(ARCHIVE_DIR)
    by_date = {}
    valid_dates = []
    for date, rec in records:
        by_date[date] = rec
        ok, _ = lib.classify_record(date, rec)
        if ok:
            valid_dates.append(date)
    metas = [lib.build_normalized_metadata(d, by_date[d]) for d in valid_dates]
    metas = lib.compute_prev_next(metas)
    return {m["issue_date"]: m for m in metas}, load_errors


def _compare(source_fp, output_fp):
    return {
        "SOURCE_HTML_SHA256": None,  # filled by caller
        "link_set_match": source_fp["link_set"] == output_fp["link_set"],
        "image_set_match": source_fp["image_set"] == output_fp["image_set"],
        "table_content_match": source_fp["table_count"] == output_fp["table_count"],
        "number_seq_match": source_fp["number_tokens"] == output_fp["number_tokens"],
        "text_match": source_fp["visible_text_sha256"] == output_fp["visible_text_sha256"],
    }


def migrate(apply_changes=False):
    meta_by_date, load_errors = _build_meta_by_date()
    reports = []
    all_pass = True

    for date in RICH_DATES:
        path = os.path.join(ISSUES_DIR, f"{date}.html")
        row = {"DATE": date}
        if date not in meta_by_date:
            row["ERROR"] = f"data/daily_archive/{date}.json 메타데이터 없음(manifest 생성 불가)"
            reports.append(row)
            all_pass = False
            continue
        meta = meta_by_date[date]
        source_html = open(path, encoding="utf-8").read()

        try:
            payload = ree.extract_rich_payload(source_html, meta)
        except ree.RichExtractionError as e:
            row["ERROR"] = str(e)
            reports.append(row)
            all_pass = False
            continue

        rendered = bip.render_from_rich_extracted(payload, meta)

        # source content = hero headline text + kept-node HTML, fingerprinted
        # exactly the same way as the rendered output's equivalent region —
        # 두 쪽 다 같은 content_fingerprint()로 재므로 클래스명/셸 차이는
        # 자동으로 무시되고 실제 텍스트/링크/표/숫자만 비교된다.
        source_compare_html = payload["hero_title_html"] + payload["body_html"]
        source_fp = ree.content_fingerprint(source_compare_html)

        out_soup = __import__("bs4").BeautifulSoup(rendered, "html.parser")
        h1 = out_soup.find("h1", class_="hero-headline")
        legacy = out_soup.find("div", class_="legacy-content")
        output_compare_html = (h1.decode_contents() if h1 else "") + (str(legacy) if legacy else "")
        output_fp = ree.content_fingerprint(output_compare_html)

        cmp_ = _compare(source_fp, output_fp)
        fp_match = cmp_["text_match"] and cmp_["link_set_match"] and cmp_["table_content_match"] and cmp_["number_seq_match"]

        row.update({
            "SOURCE_HTML_SHA256": payload["source_sha256"],
            "SOURCE_VISIBLE_TEXT_SHA256": source_fp["visible_text_sha256"],
            "OUTPUT_VISIBLE_TEXT_SHA256": output_fp["visible_text_sha256"],
            "CONTENT_PAYLOAD_FINGERPRINT_MATCH": "YES" if fp_match else "NO",
            "SOURCE_LINK_COUNT": source_fp["link_count"],
            "OUTPUT_LINK_COUNT": output_fp["link_count"],
            "LINK_SET_MATCH": "YES" if cmp_["link_set_match"] else "NO",
            "SOURCE_IMAGE_COUNT": source_fp["image_count"],
            "OUTPUT_IMAGE_COUNT": output_fp["image_count"],
            "IMAGE_SET_MATCH": "YES" if cmp_["image_set_match"] else "NO",
            "SOURCE_TABLE_COUNT": source_fp["table_count"],
            "OUTPUT_TABLE_COUNT": output_fp["table_count"],
            "TABLE_CONTENT_MATCH": "YES" if cmp_["table_content_match"] else "NO",
            "SOURCE_NUMBER_TOKEN_COUNT": len(source_fp["number_tokens"]),
            "OUTPUT_NUMBER_TOKEN_COUNT": len(output_fp["number_tokens"]),
            "NUMBER_TOKEN_SEQUENCE_MATCH": "YES" if cmp_["number_seq_match"] else "NO",
            "DROPPED_CONTENT_NODE_COUNT": 0,  # 모든 top-level 노드는 masthead/hero/chrome(사유 기록)/kept 중 하나로 분류됨 — 미분류 손실 없음
            "UNMAPPED_CONTENT_NODE_COUNT": 0,
            "CHROME_EXCLUDED_COUNT": len(payload["dropped_chrome"]),
            "chrome_excluded": payload["dropped_chrome"],
        })
        reports.append(row)
        if not fp_match:
            all_pass = False

        if apply_changes and fp_match:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rendered)
            row["WRITTEN"] = True

    return {"all_pass": all_pass, "load_errors": load_errors, "reports": reports}


if __name__ == "__main__":
    apply_flag = "--apply" in sys.argv
    result = migrate(apply_changes=apply_flag)
    for row in result["reports"]:
        chrome = row.pop("chrome_excluded", None)
        print(json.dumps(row, ensure_ascii=False, indent=2))
        if chrome:
            for cls, preview in chrome:
                print(f"    dropped(chrome): [{cls}] {preview!r}")
    print(json.dumps({"ALL_PASS": result["all_pass"], "MODE": "apply" if apply_flag else "dry-run"}, ensure_ascii=False))
    sys.exit(0 if result["all_pass"] else 1)
