#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOO:conomy 공개면 검증 게이트 (Public Surface Check).

역할
  배포된 공개면을 '외부에서 관측 가능한 방식으로만' 검사한다.
  목적은 하나다 — 내부에서 이미 알고 있는 결함이 라이브 사이트에 남아 있는지
  자동으로 잡아내는 것. 현재 게이트는 '코드가 의도대로 동작했는가'만 보고
  '외부에 무엇이 보이는가'를 보지 않는다. 이 스크립트가 그 빈칸이다.

특징
  - 인증·비밀값·저장소 접근이 필요 없다. 표준 라이브러리만 쓴다.
  - 읽기 전용. 사이트에 아무것도 쓰지 않는다.
  - FAIL이 하나라도 있으면 비0 종료코드 -> 게이트로 바로 쓸 수 있다.
  - Accept-Encoding: identity 로 요청한다. (gzip 응답 파싱 문제 회피)

사용
  python3 checks/check_public_surface.py
  python3 checks/check_public_surface.py --issues 12
  python3 checks/check_public_surface.py --json public_surface.json
  python3 checks/check_public_surface.py --site https://staging.example.com

종료코드
  0 = FAIL 없음, 1 = FAIL 있음, 2 = 실행 오류
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; mooconomy-public-surface-check/1.0; +https://mooconomy.co.kr)"
TIMEOUT = 25

FAIL, WARN, INFO = "FAIL", "WARN", "INFO"

# 내부 운영 파일 — 공개 서빙되면 안 되는 것 (검증 목적에 기여하지 않는 순수 운영 데이터)
INTERNAL_OPS_PATHS = [
    "/data/llm_quota_ledger.jsonl",
    "/data/sent_editions.jsonl",
]

# 공개 JSON에서 발견되면 내부 구현이 노출된 것으로 보는 키/문자열
INTERNAL_KEYS = [
    "source_commit_sha",
    "published_at_is_approximate",
    "privacy_audit_passed",
    "template_version",
    "had_key",
    "financialmodelingprep.com",
    "finnhub.io",
]

# HTML 주석/본문에 남으면 안 되는 내부 작업 메모 조각
INTERNAL_NOTE_PATTERNS = [
    "자동화 미배선", "수동 반영", "CEO 재지시", "python3 scripts", "FIXME", "수동 갱신",
]

DATA_JSON_PATHS = [
    "/data/home.json",
    "/ticker.json",
    "/data/archive/issues_manifest.json",
    "/data/calendar_events.json",
    "/data/signals.json",
    "/data/quality/index.json",
]

SITEMAP_NOINDEX_SUSPECTS = ["markets.html"]


def fetch(url):
    """(status, body) 반환. status None이면 접속 실패."""
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Encoding": "identity"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001 - 네트워크 실패는 보고 대상
        return None, "%s" % e


def meta_content(html, key, attr="name"):
    """<meta name=|property="key" content="..."> 값을 찾는다."""
    pat = re.compile(
        r"<meta[^>]*%s\s*=\s*[\"']%s[\"'][^>]*content\s*=\s*[\"']([^\"']*)[\"']"
        % (attr, re.escape(key)),
        re.I,
    )
    m = pat.search(html)
    if m:
        return m.group(1).strip()
    # content가 앞에 오는 형태도 허용
    pat2 = re.compile(
        r"<meta[^>]*content\s*=\s*[\"']([^\"']*)[\"'][^>]*%s\s*=\s*[\"']%s[\"']"
        % (attr, re.escape(key)),
        re.I,
    )
    m2 = pat2.search(html)
    return m2.group(1).strip() if m2 else None


def title_of(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def h1_count(html):
    return len(re.findall(r"<h1[\s>]", html, re.I))


def jsonld_blocks(html):
    out = []
    for m in re.finditer(
        r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I
    ):
        try:
            out.append(json.loads(m.group(1).strip()))
        except Exception:  # noqa: BLE001 - 깨진 JSON-LD도 보고 대상
            out.append({"_parse_error": True})
    return out


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, check, detail):
        self.items.append({"level": level, "check": check, "detail": detail})

    def fails(self):
        return [i for i in self.items if i["level"] == FAIL]

    def warns(self):
        return [i for i in self.items if i["level"] == WARN]

    def infos(self):
        return [i for i in self.items if i["level"] == INFO]


# --------------------------------------------------------------------------
# 검사 항목
# --------------------------------------------------------------------------

def check_robots(rep, base):
    st, body = fetch(base + "/robots.txt")
    if st != 200:
        rep.add(FAIL, "robots.txt", "HTTP %s — robots.txt를 읽을 수 없다" % st)
        return
    if "Disallow: /data/" in body or "Disallow:/data/" in body:
        rep.add(INFO, "robots.txt", "Disallow: /data/ 존재")
    else:
        rep.add(
            WARN,
            "robots.txt",
            "/data/ Disallow 없음 — robots는 권고일 뿐이라 1차 방어로만 유효 (근본 조치는 파일 제거)",
        )


def check_sitemap(rep, base):
    st, body = fetch(base + "/sitemap.xml")
    if st != 200:
        rep.add(FAIL, "sitemap", "HTTP %s — sitemap.xml을 읽을 수 없다" % st)
        return [], []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    issues = sorted({u for u in locs if re.search(r"/issues/\d{4}-\d{2}-\d{2}\.html$", u)})
    weekly = sorted({u for u in locs if re.search(r"/weekly/\d{4}-W\d+\.html$", u)})
    rep.add(
        INFO,
        "sitemap",
        "총 %d개 URL — 발행판 %d / 주간판 %d" % (len(locs), len(issues), len(weekly)),
    )
    for suspect in SITEMAP_NOINDEX_SUSPECTS:
        if any(u.endswith("/" + suspect) for u in locs):
            rep.add(
                FAIL,
                "sitemap",
                "noindex 페이지가 sitemap에 등록됨: %s (검색엔진에 상반 신호)" % suspect,
            )
    return issues, weekly


def check_home(rep, base):
    st, html = fetch(base + "/")
    if st != 200:
        rep.add(FAIL, "홈", "HTTP %s" % st)
        return None, None
    for label, val in (
        ("title", title_of(html)),
        ("meta description", meta_content(html, "description")),
    ):
        if not val:
            rep.add(FAIL, "홈", "%s 없음" % label)
    if h1_count(html) == 0:
        rep.add(FAIL, "홈", "H1 없음")
    counter = None
    # 1순위: id="subProofCount">46< 형태 (index.html에 하드코딩된 카운터)
    m = re.search(r'id="subProofCount"[^>]*>\s*([0-9]+)\s*<', html)
    if m:
        counter = int(m.group(1))
        rep.add(INFO, "홈", "누적 발행호 카운터 = %d (index.html 하드코딩)" % counter)
    else:
        # 2순위: "46누적 발행호" 형태 (JS 조립)
        m2 = re.search(r"([0-9][0-9,]*)\s*누적\s*발행", html)
        if m2:
            counter = int(m2.group(1).replace(",", ""))
            rep.add(INFO, "홈", "누적 발행호 표기 = %d" % counter)
        else:
            rep.add(WARN, "홈", "누적 발행호 카운터를 HTML에서 찾지 못함")
    ld_types = []
    for b in jsonld_blocks(html):
        t = b.get("@type")
        if t:
            ld_types.append(t if isinstance(t, str) else str(t))
    rep.add(INFO, "홈", "JSON-LD: %s" % (", ".join(ld_types) or "없음"))
    return counter, html


def check_archive(rep, base):
    st, html = fetch(base + "/archive/")
    if st != 200:
        rep.add(FAIL, "아카이브", "HTTP %s" % st)
        return None
    n_desc = None
    desc = meta_content(html, "description") or ""
    m = re.search(r"총\s*(\d+)\s*호", desc)
    if m:
        n_desc = int(m.group(1))
    n_ld = None
    for b in jsonld_blocks(html):
        me = b.get("mainEntity") or {}
        if isinstance(me, dict) and "numberOfItems" in me:
            n_ld = me["numberOfItems"]
    rep.add(
        INFO,
        "아카이브",
        "meta 설명 '총 %s호' / JSON-LD numberOfItems=%s" % (n_desc, n_ld),
    )
    if n_desc is not None and n_ld is not None and n_desc != n_ld:
        rep.add(
            FAIL,
            "아카이브",
            "meta 설명(%s)과 JSON-LD(%s)의 호수가 다르다" % (n_desc, n_ld),
        )
    return n_desc if n_desc is not None else n_ld


def check_consistency(rep, home_counter, archive_count, n_issues, n_weekly):
    total = n_issues + n_weekly
    rep.add(
        INFO,
        "수치 일관성",
        "홈 카운터=%s / 아카이브=%s / sitemap(발행판+주간)=%d+%d=%d"
        % (home_counter, archive_count, n_issues, n_weekly, total),
    )
    if home_counter is not None and n_issues and home_counter != n_issues:
        rep.add(
            FAIL,
            "수치 일관성",
            "홈 카운터(%d)가 sitemap 발행판 수(%d)와 다르다 — '누적 발행호' 정의 불일치"
            % (home_counter, n_issues),
        )
    if archive_count is not None and total and archive_count != total:
        rep.add(
            FAIL,
            "수치 일관성",
            "아카이브 호수(%s)가 sitemap 총 등록수(%d)와 다르다" % (archive_count, total),
        )


def check_data_exposure(rep, base):
    for p in INTERNAL_OPS_PATHS:
        st, body = fetch(base + p)
        if st == 200:
            rep.add(
                FAIL,
                "/data/ 노출",
                "내부 운영 파일이 공개 서빙됨: %s (%d bytes)" % (p, len(body)),
            )
        else:
            rep.add(INFO, "/data/ 노출", "%s -> HTTP %s (비공개)" % (p, st))
    for p in DATA_JSON_PATHS:
        st, body = fetch(base + p)
        if st != 200:
            rep.add(INFO, "/data/ 노출", "%s -> HTTP %s" % (p, st))
            continue
        hits = {}
        for k in INTERNAL_KEYS:
            c = body.count(k)
            if c:
                hits[k] = c
        if hits:
            rep.add(
                FAIL,
                "/data/ 노출",
                "%s 에 내부 필드 노출: %s"
                % (p, ", ".join("%s×%d" % (k, v) for k, v in sorted(hits.items()))),
            )
        else:
            rep.add(INFO, "/data/ 노출", "%s — 내부 필드 없음" % p)


def check_issues(rep, base, issues, limit):
    if not issues:
        rep.add(WARN, "발행판 메타", "sitemap에서 발행판 URL을 찾지 못해 검사 생략")
        return
    sample = issues[-limit:]
    og_seen = {}
    no_title = no_desc = no_h1 = 0
    for url in sample:
        st, html = fetch(url)
        slug = url.rsplit("/", 1)[-1]
        if st != 200:
            rep.add(FAIL, "발행판 메타", "%s HTTP %s" % (slug, st))
            continue
        t = title_of(html)
        if not t or "발행 기록" in t:
            no_title += 1
            rep.add(FAIL, "발행판 메타", "%s title 폴백/누락: %r" % (slug, t))
        d = meta_content(html, "description")
        if not d:
            no_desc += 1
            rep.add(FAIL, "발행판 메타", "%s meta description 없음" % slug)
        if h1_count(html) == 0:
            no_h1 += 1
            rep.add(FAIL, "발행판 메타", "%s H1 없음" % slug)
        og = meta_content(html, "og:image", attr="property")
        if og:
            og_seen.setdefault(og, []).append(slug)
        # NewsArticle 필수 필드
        for b in jsonld_blocks(html):
            if b.get("@type") == "NewsArticle":
                for f in ("datePublished", "author"):
                    if not b.get(f):
                        rep.add(
                            WARN,
                            "구조화 데이터",
                            "%s NewsArticle.%s 없음" % (slug, f),
                        )
    rep.add(
        INFO,
        "발행판 메타",
        "표본 %d건 — title 누락 %d / description 누락 %d / H1 누락 %d"
        % (len(sample), no_title, no_desc, no_h1),
    )
    if len(og_seen) == 1 and len(sample) > 1:
        only = next(iter(og_seen))
        rep.add(
            FAIL,
            "공유 미리보기",
            "표본 %d건이 og:image 하나를 공유: %s (공유 시 전부 같은 썸네일)"
            % (len(sample), only),
        )
    elif og_seen:
        dup = {k: v for k, v in og_seen.items() if len(v) > 1}
        if dup:
            rep.add(WARN, "공유 미리보기", "중복 og:image: %s" % list(dup.values()))


def check_calendar(rep, base):
    st, html = fetch(base + "/calendar/")
    if st != 200:
        rep.add(FAIL, "캘린더", "HTTP %s" % st)
        return
    bad = []
    if "불러오는 중" in html:
        bad.append("'불러오는 중'")
    if re.search(r"총\s*[–\-—]\s*건", html):
        bad.append("'총 –건'")
    if bad:
        rep.add(
            FAIL,
            "캘린더",
            "서버 응답 HTML에 실제 일정이 없다 (%s) — 클라이언트 JS 렌더 의존, 크롤러/AI에게 빈 화면"
            % ", ".join(bad),
        )
    else:
        rep.add(INFO, "캘린더", "HTML에 일정 텍스트 존재")


def check_llms(rep, base):
    st, _ = fetch(base + "/llms.txt")
    if st == 200:
        rep.add(INFO, "llms.txt", "존재")
    else:
        rep.add(WARN, "llms.txt", "HTTP %s — AI 크롤러 안내 채널 비어 있음 (GEO)" % st)


def check_internal_notes(rep, base, issues):
    targets = ["/"]
    if issues:
        targets.append(issues[-1])
    for p in targets:
        url = base + p if p == "/" else p
        st, html = fetch(url)
        if st != 200:
            continue
        comments = re.findall(r"<!--(.*?)-->", html, re.S)
        blob = "\n".join(comments) + "\n" + html
        for pat in INTERNAL_NOTE_PATTERNS:
            if pat in blob:
                where = "주석" if any(pat in c for c in comments) else "본문"
                rep.add(
                    WARN,
                    "내부 메모 노출",
                    "%s 의 %s에 '%s' 발견" % (p, where, pat),
                )
                break


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="MOCO:conomy 공개면 검증 게이트")
    ap.add_argument("--site", default="https://mooconomy.co.kr")
    ap.add_argument("--issues", type=int, default=10, help="검사할 최신 발행판 수")
    ap.add_argument("--json", dest="json_out", default=None, help="결과를 JSON으로 저장")
    args = ap.parse_args()
    base = args.site.rstrip("/")

    rep = Report()
    try:
        check_robots(rep, base)
        issues, weekly = check_sitemap(rep, base)
        home_counter, _ = check_home(rep, base)
        archive_count = check_archive(rep, base)
        check_consistency(rep, home_counter, archive_count, len(issues), len(weekly))
        check_data_exposure(rep, base)
        check_issues(rep, base, issues, args.issues)
        check_calendar(rep, base)
        check_llms(rep, base)
        check_internal_notes(rep, base, issues)
    except Exception as e:  # noqa: BLE001
        print("실행 오류: %s" % e, file=sys.stderr)
        return 2

    order = {FAIL: 0, WARN: 1, INFO: 2}
    items = sorted(rep.items, key=lambda i: order[i["level"]])
    icon = {FAIL: "[FAIL]", WARN: "[WARN]", INFO: "[ OK ]"}
    print("=" * 72)
    print("MOO:conomy 공개면 검증 — %s" % base)
    print("=" * 72)
    for i in items:
        print("%s %-14s %s" % (icon[i["level"]], i["check"], i["detail"]))
    print("-" * 72)
    print(
        "FAIL %d / WARN %d / OK %d"
        % (len(rep.fails()), len(rep.warns()), len(rep.infos()))
    )
    if rep.fails():
        print("=> 공개면 게이트 실패")
    else:
        print("=> 공개면 게이트 통과 (WARN 확인 필요)")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(
                {"site": base, "items": items,
                 "fail": len(rep.fails()), "warn": len(rep.warns())},
                f, ensure_ascii=False, indent=2,
            )
    return 1 if rep.fails() else 0


if __name__ == "__main__":
    sys.exit(main())
