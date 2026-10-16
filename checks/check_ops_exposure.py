#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOO:conomy 운영면 노출 게이트 (check_ops_exposure).
====================================================

존재 이유
  기존 check_public_surface.py 의 내부파일 검사는 **고정 목록**(INTERNAL_OPS_PATHS)이다.
  그래서 저장소에 새 운영 파일이 추가되면 **게이트가 침묵한다.**
  2026-10-17 실측: data/ops/ops_ledger.jsonl 이 https://mooconomy.co.kr/data/ops/ops_ledger.jsonl
  로 HTTP 200 서빙 중인데, 기존 게이트는 이 파일의 존재 자체를 몰랐다.

무엇을 하는가
  저장소의 data/ 아래 **모든 *.jsonl** 을 열거하고(고정 목록이 아니라 실제 파일에서 도출),
  각각을 라이브로 요청해 하나라도 200이면 FAIL 한다.
  즉 "내부 운영 파일이 공개되면 다음 날 게이트가 반드시 잡는다"를 구조로 보장한다.

  고정 목록 → 도출 로 바꾸는 것이 요점이다. 새 파일을 추가하는 사람이 게이트를 고칠 필요가 없다.

사용
  python3 checks/check_ops_exposure.py --repo .                  # 저장소에서 열거 + 라이브 확인
  python3 checks/check_ops_exposure.py --repo . --json out.json
  python3 checks/check_ops_exposure.py --repo . --paths /data/ops/ops_ledger.jsonl   # 명시 지정

종료코드
  0 = 노출 0건 / 1 = 노출 발견(FAIL) / 2 = 실행 오류(열거 실패 등)
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "https://mooconomy.co.kr"

# 이 키들이 공개 본문에 보이면 "내부 운영면"으로 판정한다.
# ops_ledger 의 실제 필드에서 도출했다 (추정 아님 — 2026-10-17 라이브 응답 기준).
OPS_LEAK_KEYS = [
    "rpd_limit", "rpd_pct", "run_id", "started_at_kst", "sent_at_kst",
    "email_sent", "reverted", "director", "quota", "http_503",
    "gemini-", "숫자_정확성", "DETERMINISTIC_FALLBACK",
]


def discover_jsonl(repo):
    """저장소 data/ 아래의 모든 *.jsonl 을 웹 경로로 변환해 돌려준다."""
    data_dir = os.path.join(repo, "data")
    if not os.path.isdir(data_dir):
        return None
    out = []
    for root, _dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith(".jsonl"):
                rel = os.path.relpath(os.path.join(root, f), repo)
                out.append("/" + rel.replace(os.sep, "/"))
    return sorted(set(out))


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "mooconomy-ops-gate/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:  # noqa: BLE001
        return 0, b""


def main():
    ap = argparse.ArgumentParser(description="운영면 노출 게이트 (data/**/*.jsonl 도출)")
    ap.add_argument("--repo", default=".", help="저장소 루트 (data/ 를 스캔)")
    ap.add_argument("--site", default=DEFAULT_BASE)
    ap.add_argument("--paths", nargs="*", help="검사할 웹 경로를 직접 지정 (열거 대신)")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    base = args.site.rstrip("/")
    if args.paths:
        paths = list(args.paths)
        origin = "지정"
    else:
        paths = discover_jsonl(args.repo)
        origin = "저장소 열거"
        if paths is None:
            print("실행 오류: %s 에 data/ 디렉터리가 없다 (--repo 를 확인)" % args.repo,
                  file=sys.stderr)
            return 2

    print("=" * 72)
    print("MOO:conomy 운영면 노출 게이트 — %s" % base)
    print("검사 대상 %d건 (%s: data/**/*.jsonl)" % (len(paths), origin))
    print("=" * 72)

    fails, oks = [], []
    for p in paths:
        st, body = fetch(base + p)
        if st == 200:
            hits = {}
            text = body.decode("utf-8", "replace")
            for k in OPS_LEAK_KEYS:
                c = text.count(k)
                if c:
                    hits[k] = c
            detail = ", ".join("%s×%d" % (k, v) for k, v in sorted(hits.items())) or "식별키 없음(그래도 노출)"
            fails.append({"path": p, "bytes": len(body), "keys": hits})
            print("[FAIL] %-46s HTTP 200 · %6dB · %s" % (p, len(body), detail))
        else:
            oks.append({"path": p, "status": st})
            print("[OK]   %-46s HTTP %s (비공개)" % (p, st))

    print("-" * 72)
    print("노출 FAIL %d / 비공개 OK %d" % (len(fails), len(oks)))
    print("=> %s" % ("운영면 노출 발견 — 내부 파일 제거 또는 커밋 중단 필요" if fails else "운영면 노출 없음"))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"site": base, "checked": len(paths), "fails": fails, "oks": oks},
                      fh, ensure_ascii=False, indent=2)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
