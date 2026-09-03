"""2026-08-21(TASK_ID=TRACK_B10_SITEMAP_RSS) sitemap.xml 생성기.
2026-09-03(TASK_ID=OG_SEO_CORRECTION): latest.html/latest-email.html은
canonical이 아니라 각 발행판 issue URL을 그대로 가리키는 파생 페이지라
sitemap에서 뺀다(latest-email.html은 별도로 noindex도 적용). 대신 실제
운영 중인 /calendar/, /weekly.html을 추가. STATIC_PAGES의 lastmod는
로컬 파일의 실제 mtime에서만 가져온다(파일이 없으면 생략, 지어내지 않음).

정적 페이지(홈/about/methodology/questions/markets/calendar/weekly) +
아카이브 매니페스트 기반 동적 페이지(archive/, archive/{YYYY-MM}/,
issues/{date}.html)를 하나의 sitemap.xml로 합친다. lastmod는 실제로
아는 날짜(발행일 또는 파일 mtime)만 채운다 -- 모르는 값은 생략하지 지어내지 않는다.
publish_issue_archive.py가 검증 통과한 manifest로만 호출하므로 이
파일 자체는 무엇이 "검증 통과"인지 판단하지 않는다(build_archive_pages.py
와 동일한 책임 분리).
"""
import datetime as _dt
import os
import xml.etree.ElementTree as _ET

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

STATIC_PAGES = [
    ("https://mooconomy.co.kr", "daily", "index.html"),
    ("https://mooconomy.co.kr/about/", "monthly", "about/index.html"),
    ("https://mooconomy.co.kr/methodology/", "monthly", "methodology/index.html"),
    ("https://mooconomy.co.kr/questions/", "daily", "questions/index.html"),
    ("https://mooconomy.co.kr/markets.html", "daily", "markets.html"),
    ("https://mooconomy.co.kr/calendar/", "daily", "calendar/index.html"),
    ("https://mooconomy.co.kr/weekly.html", "daily", "weekly.html"),
]


def _file_lastmod(rel_path):
    full = os.path.join(_ROOT, rel_path)
    if not os.path.exists(full):
        return None
    return _dt.date.fromtimestamp(os.path.getmtime(full)).isoformat()


def _url_entry(loc, lastmod=None, changefreq=None):
    lines = [f"    <loc>{loc}</loc>"]
    if lastmod:
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
    if changefreq:
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
    return "  <url>\n" + "\n".join(lines) + "\n  </url>"


def build_sitemap(manifest):
    """manifest: publish_issue_archive.py가 만드는 issues_manifest.json과
    같은 리스트(각 항목에 issue_date, public_path). 빈 리스트여도 정적
    페이지만으로 유효한 sitemap을 만든다."""
    entries = [
        _url_entry(loc, lastmod=_file_lastmod(rel), changefreq=cf)
        for loc, cf, rel in STATIC_PAGES
    ]

    if manifest:
        latest_date = max(m["issue_date"] for m in manifest)
        entries.append(_url_entry(
            "https://mooconomy.co.kr/archive/", lastmod=latest_date, changefreq="daily",
        ))
        months = {}
        for m in manifest:
            months.setdefault(m["issue_date"][:7], []).append(m["issue_date"])
        for ym, dates in sorted(months.items()):
            entries.append(_url_entry(
                f"https://mooconomy.co.kr/archive/{ym}/", lastmod=max(dates), changefreq="monthly",
            ))
        for m in sorted(manifest, key=lambda x: x["issue_date"]):
            entries.append(_url_entry(
                f"https://mooconomy.co.kr{m['public_path']}",
                lastmod=m["issue_date"], changefreq="never",
            ))

    body = "\n".join(entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def validate_sitemap_xml(xml_text):
    """정상 XML인지만 확인(스키마 검증 아님, 파싱 실패만 잡는다).
    문제 있으면 이슈 문자열 리스트, 없으면 빈 리스트 -- 다른 검증
    함수들과 동일한 인터페이스."""
    try:
        _ET.fromstring(xml_text)
        return []
    except _ET.ParseError as e:
        return [f"sitemap_xml_parse_error:{e}"]
