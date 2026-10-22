#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOO:conomy 상태 도출기 (derive_state).
=====================================

존재 이유
  LLM의 기억은 세션이 길어지면 오염된다. 핸드오프 문서는 그 오염된 기억을
  '사실'처럼 기록하기 때문에 오염을 다음 세션으로 전파한다.
  해결책은 '기억하지 않는 것'이다.

  이 스크립트는 저장소와 공개 사이트에서 사실을 매번 다시 도출한다.
  도출된 값과 LLM이 기억하는 값이 다르면 이 스크립트가 맞다.

세 층 분리 원칙
  사실(FACT)      -> 도출한다. 손으로 쓰지 않는다.   <-- 이 스크립트
  결정(DECISION)  -> 사람이 쓴다. 짧고 append-only.  <-- DECISIONS.log
  믿음(BELIEF)    -> 표시하고 만료시킨다.            <-- [미확인] 표

사용
  python3 tools/derive_state.py --repo .                    # 저장소에서 도출
  python3 tools/derive_state.py --repo . --live             # + 공개 사이트 대조
  python3 tools/derive_state.py --repo . --paste            # 붙여넣기용 블록 출력
  python3 tools/derive_state.py --repo . --json state.json
  python3 tools/derive_state.py --repo . --paste > TODAY.md

종료코드
  0 = 도출 성공 / 1 = 치명 불일치 발견 / 2 = 실행 오류
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------- 유틸


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def read_json(path, default=None):
    txt = read(path)
    if not txt:
        return default
    try:
        return json.loads(txt)
    except Exception:
        return default


def sh(args, cwd=None):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def sha8(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:8]


# ---------------------------------------------------------------- 도출기


class Derived:
    """도출된 사실의 모음. 여기 있는 값만 '사실'로 취급한다."""

    def __init__(self, repo):
        self.repo = os.path.abspath(repo)
        self.f = {}       # 사실
        self.notes = []   # 도출 경로 메모
        self.alarms = []  # 치명 불일치

    # --- 1. 저장소 앵커 ---------------------------------------------
    def anchor(self):
        self.f["repo_head"] = sh(["git", "rev-parse", "HEAD"], self.repo)[:40]
        self.f["repo_head_short"] = sh(["git", "rev-parse", "--short", "HEAD"], self.repo)
        self.f["repo_branch"] = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], self.repo)
        self.f["repo_dirty"] = bool(sh(["git", "status", "--porcelain"], self.repo))
        self.f["derived_at"] = dt.datetime.now().isoformat(timespec="seconds")
        self.f["repo_head_time"] = sh(
            ["git", "log", "-1", "--format=%cI"], self.repo
        )

    # --- 2. 발행 사실 ----------------------------------------------
    def issues(self):
        manifest = read_json(os.path.join(self.repo, "data/archive/issues_manifest.json"), [])
        dates = []
        if isinstance(manifest, list):
            dates = sorted(
                m.get("issue_date", "") for m in manifest if m.get("issue_date")
            )
            self.f["manifest_entries"] = len(manifest)
            self.f["manifest_internal_fields"] = sorted(
                {
                    k
                    for m in manifest
                    if isinstance(m, dict)
                    for k in ("source_commit_sha", "privacy_audit_passed",
                              "published_at_is_approximate", "template_version")
                    if k in m
                }
            )
        # 파일 시스템의 실제 발행판 (manifest와 대조)
        idir = os.path.join(self.repo, "issues")
        fs_dates = []
        if os.path.isdir(idir):
            for n in os.listdir(idir):
                m = re.match(r"(\d{4}-\d{2}-\d{2})\.html$", n)
                if m:
                    fs_dates.append(m.group(1))
        fs_dates.sort()
        self.f["issues_on_disk"] = len(fs_dates)
        self.f["issues_in_manifest"] = len(dates)
        self.f["latest_issue"] = fs_dates[-1] if fs_dates else None
        self.f["first_issue"] = fs_dates[0] if fs_dates else None

        # 주간판
        wdir = os.path.join(self.repo, "weekly")
        weeks = []
        if os.path.isdir(wdir):
            for n in os.listdir(wdir):
                m = re.match(r"(\d{4}-W\d+)\.html$", n)
                if m:
                    weeks.append(m.group(1))
        self.f["weekly_on_disk"] = sorted(weeks)
        self.f["weekly_count"] = len(weeks)

        # 결번 (화~토 발행 기준)
        if fs_dates:
            first = dt.date.fromisoformat(fs_dates[0])
            last = dt.date.fromisoformat(fs_dates[-1])
            have = set(fs_dates)
            gaps = []
            d = first
            while d <= last:
                # 일요일(6) 휴간 — 월요일은 Weekly
                if d.weekday() not in (6,) and d.isoformat() not in have:
                    gaps.append(d.isoformat())
                d += dt.timedelta(days=1)
            self.f["gaps"] = gaps
            self.f["gap_count"] = len(gaps)

        # sitemap 대조
        sm = read(os.path.join(self.repo, "sitemap.xml"))
        sm_issues = sorted(set(re.findall(r"/issues/(\d{4}-\d{2}-\d{2})\.html", sm)))
        self.f["issues_in_sitemap"] = len(sm_issues)
        self.f["latest_in_sitemap"] = sm_issues[-1] if sm_issues else None
        if sm_issues and fs_dates and sm_issues[-1] != fs_dates[-1]:
            self.alarms.append(
                "sitemap 최신(%s) != 디스크 최신(%s)" % (sm_issues[-1], fs_dates[-1])
            )

    # --- 3. 호수 정의 (단일 소스) -----------------------------------
    def count_definition(self):
        n_daily = self.f.get("issues_in_sitemap") or self.f.get("issues_on_disk") or 0
        n_weekly = self.f.get("weekly_count") or 0
        self.f["count_definition"] = "Daily %d호 + Weekly %d호 = 총 %d호" % (
            n_daily, n_weekly, n_daily + n_weekly,
        )
        self.f["total_editions"] = n_daily + n_weekly

        # 홈 카운터 (하드코딩 탐지)
        home = read(os.path.join(self.repo, "index.html"))
        m = re.search(r'id="subProofCount"[^>]*>\s*([0-9]+)\s*<', home)
        if m:
            self.f["home_counter"] = int(m.group(1))
            self.f["home_counter_source"] = "index.html:subProofCount (하드코딩)"
            if self.f["home_counter"] != n_daily:
                self.alarms.append(
                    "홈 카운터(%d) != Daily 발행판 수(%d)" % (self.f["home_counter"], n_daily)
                )
        # 아카이브 메타
        arch = read(os.path.join(self.repo, "archive/index.html"))
        m2 = re.search(r"총\s*(\d+)\s*호", arch)
        if m2:
            self.f["archive_counter"] = int(m2.group(1))
            if self.f["archive_counter"] != self.f["total_editions"]:
                self.alarms.append(
                    "아카이브 카운터(%d) != 총 발행호(%d)"
                    % (self.f["archive_counter"], self.f["total_editions"])
                )

    # --- 4. 메타 결함 실측 ------------------------------------------
    def meta_defects(self):
        idir = os.path.join(self.repo, "issues")
        files = []
        if os.path.isdir(idir):
            files = sorted(f for f in os.listdir(idir) if f.endswith(".html"))[-14:]
        no_desc, no_title, og = 0, 0, {}
        for n in files:
            h = read(os.path.join(idir, n))
            if 'name="description"' not in h:
                no_desc += 1
            if "발행 기록 | MOO:conomy" in h[:2000]:
                no_title += 1
            m = re.search(r'property="og:image"[^>]*content="([^"]+)"', h)
            if m:
                og.setdefault(m.group(1), []).append(n)
        self.f["checked_issues"] = len(files)
        self.f["issues_missing_description"] = no_desc
        self.f["issues_title_fallback"] = no_title
        self.f["og_image_distinct"] = len(og)
        self.f["og_shared_by"] = max((len(v) for v in og.values()), default=0)
        if no_desc:
            self.alarms.append("최근 %d건 중 %d건 meta description 누락" % (len(files), no_desc))
        if len(og) == 1 and len(files) > 1:
            self.alarms.append("최근 %d건이 og:image 하나를 공유" % len(files))

    # --- 5. 내부 필드/운영면 노출 ------------------------------------
    def exposure(self):
        exposed = []
        ops = ["data/llm_quota_ledger.jsonl", "data/sent_editions.jsonl"]
        for p in ops:
            fp = os.path.join(self.repo, p)
            if os.path.exists(fp):
                exposed.append({"path": p, "bytes": os.path.getsize(fp), "class": "운영면"})
        cal = read(os.path.join(self.repo, "data/calendar_events.json"))
        leaks = {
            "financialmodelingprep.com": cal.count("financialmodelingprep.com"),
            "finnhub.io": cal.count("finnhub.io"),
            "had_key": cal.count("had_key"),
        }
        leaks = {k: v for k, v in leaks.items() if v}
        self.f["ops_files_in_repo"] = exposed
        self.f["calendar_leaks"] = leaks
        man = self.f.get("manifest_internal_fields")
        if man:
            self.f["manifest_leak_fields"] = man
        if leaks:
            self.alarms.append("calendar_events.json 에 제공자/키 흔적: %s" % ", ".join(leaks))

    # --- 6. 크론/발행 시각 ------------------------------------------
    def schedule(self):
        wf = os.path.join(self.repo, ".github/workflows")
        crons = {}
        if os.path.isdir(wf):
            for n in os.listdir(wf):
                c = read(os.path.join(wf, n))
                for m in re.finditer(r"cron:\s*['\"]([^'\"]+)['\"]", c):
                    crons[n] = m.group(1)
        self.f["workflows"] = sorted(
            os.listdir(wf) if os.path.isdir(wf) else []
        )
        self.f["crons"] = crons

    # --- 7. 라이브 대조 --------------------------------------------
    def live(self, base="https://mooconomy.co.kr"):
        import urllib.request
        import urllib.error

        def get(u):
            try:
                req = urllib.request.Request(
                    u, headers={"User-Agent": "mooconomy-derive/1.0",
                                "Accept-Encoding": "identity"}
                )
                with urllib.request.urlopen(req, timeout=20) as r:
                    return r.status, r.read().decode("utf-8", "replace")
            except Exception:
                return None, ""

        out = {}
        st, html = get(base + "/")
        m = re.search(r'id="subProofCount"[^>]*>\s*([0-9]+)\s*<', html)
        out["live_home_counter"] = int(m.group(1)) if m else None
        st, man = get(base + "/data/archive/issues_manifest.json")
        out["live_manifest_status"] = st
        out["live_manifest_has_sha"] = "source_commit_sha" in man
        st, ops = get(base + "/data/llm_quota_ledger.jsonl")
        out["live_quota_ledger_status"] = st
        st, cal = get(base + "/calendar_events.json")
        out["live_calendar_provider_leak"] = (
            ("financialmodelingprep.com" in cal) if st == 200 else None
        )
        self.f["live"] = out
        if out.get("live_quota_ledger_status") == 200:
            self.alarms.append("운영면이 라이브 서빙 중: /data/llm_quota_ledger.jsonl")
        if out.get("live_manifest_has_sha"):
            self.alarms.append("라이브 매니페스트에 source_commit_sha 노출")

    # --- 실행 -------------------------------------------------------
    def run(self, do_live=False):
        self.anchor()
        self.issues()
        self.count_definition()
        self.meta_defects()
        self.exposure()
        self.schedule()
        if do_live:
            self.live()
        return self.f, self.alarms


# ---------------------------------------------------------------- 출력


def paste_block(f, alarms):
    """새 대화 첫 메시지에 붙일 '사실' 블록. 기억을 대체한다."""
    L = []
    L.append("<!-- 도출된 사실 — 기억하지 말 것. 이 블록이 사실이다. -->")
    L.append("## 도출된 사실 (%s 기준)" % f.get("derived_at", "?"))
    L.append("")
    L.append("- 저장소 앵커: HEAD `%s` (%s) · dirty %s"
             % (f.get("repo_head_short") or "?", f.get("repo_branch") or "?",
                "예" if f.get("repo_dirty") else "아니오"))
    L.append("- 발행: %s" % f.get("count_definition", "?"))
    L.append("- 최신 발행판: %s / 최초: %s" % (f.get("latest_issue"), f.get("first_issue")))
    if f.get("gap_count"):
        L.append("- 결번 %d일: %s" % (f["gap_count"], ", ".join(f["gaps"][:12])))
    L.append("- 카운터: 홈 %s / 아카이브 %s / 도출 총계 %s (정의: %s)"
             % (f.get("home_counter"), f.get("archive_counter"),
                f.get("total_editions"), f.get("count_definition")))
    L.append("- 메타 결함(최근 %s건): description 누락 %s / title 폴백 %s / og:image 종류 %s"
             % (f.get("checked_issues"), f.get("issues_missing_description"),
                f.get("issues_title_fallback"), f.get("og_image_distinct")))
    if f.get("ops_files_in_repo"):
        L.append("- 저장소 내 운영면 파일: %s"
                 % ", ".join("%s(%dKB)" % (x["path"], x["bytes"] // 1024)
                             for x in f["ops_files_in_repo"]))
    if f.get("calendar_leaks"):
        L.append("- calendar_events.json 제공자 흔적: %s" % f["calendar_leaks"])
    if f.get("manifest_leak_fields"):
        L.append("- 매니페스트 내부 필드: %s" % ", ".join(f["manifest_leak_fields"]))
    L.append("- 워크플로: %s" % ", ".join(f.get("workflows", [])))
    if alarms:
        L.append("")
        L.append("### 치명 불일치 %d건 (이 상태로 지시문을 쓰지 말 것)" % len(alarms))
        for a in alarms:
            L.append("- %s" % a)
    else:
        L.append("")
        L.append("### 치명 불일치 0건")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="MOO:conomy 상태 도출기")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--live", action="store_true", help="공개 사이트와 대조")
    ap.add_argument("--paste", action="store_true", help="붙여넣기용 블록 출력")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(args.repo, ".git")):
        print("오류: %s 는 git 저장소가 아니다" % args.repo, file=sys.stderr)
        return 2

    d = Derived(args.repo)
    try:
        f, alarms = d.run(do_live=args.live)
    except Exception as e:  # noqa: BLE001
        print("도출 오류: %s" % e, file=sys.stderr)
        return 2

    if args.paste:
        print(paste_block(f, alarms))
    else:
        print("=" * 72)
        print("MOO:conomy 상태 도출 — %s" % args.repo)
        print("=" * 72)
        print(paste_block(f, alarms))
        print("-" * 72)
        print("치명 불일치: %d건" % len(alarms))
        print("=> 이 값들이 사실이다. 기억과 다르면 이 값이 맞다.")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"facts": f, "alarms": alarms}, fh,
                      ensure_ascii=False, indent=2, default=str)

    return 1 if alarms else 0


if __name__ == "__main__":
    sys.exit(main())
