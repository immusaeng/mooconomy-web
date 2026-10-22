#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOO:conomy core 상태 도출기 (derive_core).
==========================================

존재 이유
  daily-mooconomy 는 비공개라 디렉터가 코드를 볼 수 없었다. GitHub 커넥터
  연결(2026-10-17)로 **상태**는 볼 수 있게 됐다. 이 스크립트가 그걸 도출한다.

무엇을 볼 수 있고 무엇을 못 보는가 (정직하게)
  볼 수 있다: 커밋 SHA, 머지 커밋, PR 목록·상태·head SHA, 기여자, 이슈
  못 본다   : **파일 내용.** gsk github 에 파일 읽기 action 이 없다.
              따라서 daily.yml·run_all_tests.py 의 내용은 여전히 CEO 붙여넣기가 필요하다.
              (파일:행 수준의 지시문은 여전히 붙여넣은 내용에만 근거할 수 있다)

가장 중요한 효용
  시작 가드와 머지 블록에 필요한 **전체 SHA 를 직접 얻는다.**
  §0-7 "자리표시자 금지", §15-3 "출력으로 SHA 확정 전에는 지시문도 블록도 내지 않는다"를
  CEO 왕복 없이 지킬 수 있게 된다.

사용
  python3 tools/derive_core.py --owner immusaeng --repo daily-mooconomy
  python3 tools/derive_core.py --owner immusaeng --repo daily-mooconomy --paste
  python3 tools/derive_core.py --owner immusaeng --repo daily-mooconomy --json core.json

종료코드
  0 = 정상 / 1 = 경보(열린 PR 존재 등) / 2 = 실행 오류
"""

import argparse
import json
import os
import subprocess
import sys

REPO_SHORT = {"daily-mooconomy": "core", "mooconomy-web": "web"}


def gsk(args):
    """gsk github 호출 -> 파싱된 result 반환. 실패하면 (None, 오류문자열)."""
    try:
        r = subprocess.run(["gsk"] + args, capture_output=True, text=True, timeout=90)
    except Exception as e:  # noqa: BLE001
        return None, "실행 실패: %s" % e
    if r.returncode != 0:
        return None, "exit=%d %s" % (r.returncode, (r.stderr or r.stdout)[:200])
    try:
        d = json.loads(r.stdout)
    except Exception as e:  # noqa: BLE001
        return None, "JSON 파싱 실패: %s" % e
    if d.get("status") == "error":
        return None, str(d.get("message"))[:200]
    data = d.get("data")
    if isinstance(data, dict):
        for k in ("result", "repositories", "pullRequests", "commits", "items"):
            if k in data:
                return data[k], None
        return data, None
    return data, None


def norm_list(x):
    """리스트가 아니면 리스트로 감싼다."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("result", "items", "commits", "pull_requests"):
            if isinstance(x.get(k), list):
                return x[k]
        return [x]
    return []


def sha_of(c):
    if not isinstance(c, dict):
        return ""
    return str(c.get("sha") or c.get("oid") or c.get("commit_sha") or "")


def msg_of(c):
    if not isinstance(c, dict):
        return ""
    cm = c.get("commit")
    if isinstance(cm, dict) and cm.get("message"):
        return str(cm["message"])
    return str(c.get("message") or c.get("title") or "")


class Core:
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo
        self.f = {}
        self.alarms = []
        self.errors = []

    def repos(self):
        r, err = gsk(["github", "list_repos"])
        if err:
            self.errors.append("list_repos: %s" % err)
            return
        for x in norm_list(r):
            if not isinstance(x, dict):
                continue
            nm = str(x.get("full_name") or x.get("name") or "")
            if nm.endswith("/" + self.repo) or nm == self.repo:
                self.f["repo_full_name"] = nm
                self.f["repo_private"] = x.get("private")
                self.f["repo_pushed_at"] = x.get("pushed_at")
                self.f["repo_default_branch"] = x.get("default_branch")

    def commits(self, limit=12):
        r, err = gsk(["github", "list_commits",
                      "--owner", self.owner, "--repo", self.repo])
        if err:
            self.errors.append("list_commits: %s" % err)
            return
        cs = norm_list(r)
        self.f["commit_count_fetched"] = len(cs)
        if cs:
            self.f["head_sha"] = sha_of(cs[0])
            self.f["head_sha_short"] = self.f["head_sha"][:7]
            self.f["head_message"] = msg_of(cs[0])[:120]
        merges = []
        for c in cs[:limit]:
            m = msg_of(c)
            if m.startswith("Merge pull request"):
                merges.append({"sha": sha_of(c), "short": sha_of(c)[:7],
                               "message": m.splitlines()[0][:100]})
        self.f["recent_merges"] = merges[:6]

    def prs(self, state="open", per_page=20):
        r, err = gsk(["github", "list_prs",
                      "--owner", self.owner, "--repo", self.repo,
                      "--state", state, "--per_page", str(per_page)])
        if err:
            self.errors.append("list_prs(%s): %s" % (state, err))
            return []
        out = []
        for x in norm_list(r):
            if not isinstance(x, dict):
                continue
            out.append({
                "number": x.get("number"),
                "state": x.get("state"),
                "title": str(x.get("title") or "")[:70],
                "merged_at": str(x.get("merged_at") or "")[:19],
                "draft": bool(x.get("draft")),
                "base": x.get("baseRefName") or x.get("base"),
            })
        return out

    def run(self):
        self.repos()
        self.commits()
        self.f["open_prs"] = self.prs("open")
        if self.f["open_prs"]:
            self.alarms.append(
                "열린 PR %d건 — 머지·합친 게이트 대상 (head SHA 는 미확보)"
                % len(self.f["open_prs"])
            )
        if self.errors:
            self.alarms.append("조회 실패 %d건: %s"
                               % (len(self.errors), "; ".join(self.errors[:3])))
        return self.f, self.alarms


def paste_block(f, alarms):
    L = []
    L.append("## core 저장소 도출 (%s)" % (f.get("repo_full_name") or "?"))
    if not f.get("head_sha"):
        L.append("- **도출 실패** — GitHub 커넥터 상태를 확인할 것")
    else:
        L.append("- origin/main HEAD: `%s` (%s)" % (f.get("head_sha_short"), f.get("head_sha")))
        L.append("- HEAD 메시지: %s" % f.get("head_message"))
        L.append("- 최근 목록 커밋 수: %s" % f.get("commit_count_fetched"))
        L.append("- private: %s / pushed: %s"
                 % (f.get("repo_private"), f.get("repo_pushed_at")))
        mg = f.get("recent_merges") or []
        if mg:
            L.append("- 최근 머지:")
            for m in mg:
                L.append("    - `%s` %s" % (m["short"], m["message"]))
        op = f.get("open_prs") or []
        L.append("- 열린 PR: %d건" % len(op))
        for p in op:
            L.append("    - #%s [%s]%s %s" % (p["number"], p["state"],
                     " (draft)" if p.get("draft") else "", p["title"]))
        L.append("- **PR head SHA 조회 불가**: list_prs 응답에 headRefOid 가 없다. "
                 "머지 블록의 headRefOid 가드는 CEO가 `gh pr view <N> --json headRefOid` 로 제공해야 한다.")
    L.append("")
    L.append("### 볼 수 없는 것 (파일 내용)")
    L.append("gsk github 에 파일 읽기 action 이 없다. `daily.yml`·`run_all_tests.py`·"
             "MOO:Q 모듈의 **내용**은 여전히 CEO 붙여넣기가 필요하다. "
             "파일:행 수준 지시문은 붙여넣은 내용에만 근거한다.")
    if alarms:
        L.append("")
        L.append("### 경보 %d건" % len(alarms))
        for a in alarms:
            L.append("- %s" % a)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="core 저장소 상태 도출기")
    ap.add_argument("--owner", default="immusaeng")
    ap.add_argument("--repo", default="daily-mooconomy")
    ap.add_argument("--paste", action="store_true")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    c = Core(args.owner, args.repo)
    try:
        f, alarms = c.run()
    except Exception as e:  # noqa: BLE001
        print("도출 오류: %s" % e, file=sys.stderr)
        return 2

    block = paste_block(f, alarms)
    if args.paste:
        print(block)
    else:
        print("=" * 72)
        print("core 상태 도출 — %s/%s" % (args.owner, args.repo))
        print("=" * 72)
        print(block)
        print("-" * 72)
        print("경보: %d건" % len(alarms))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"facts": f, "alarms": alarms}, fh,
                      ensure_ascii=False, indent=2, default=str)

    return 1 if alarms else 0


if __name__ == "__main__":
    sys.exit(main())
