"""2026-08-21(TASK_ID=TRACK_B10_SITEMAP_RSS) rss.xml 생성기.

issues_manifest.json(발행 검증을 이미 통과한 항목만)에서 최신 N건을
뽑아 RSS 2.0 피드를 만든다. 문장을 새로 쓰지 않고 manifest의 title/
morning_thesis를 그대로 옮긴다. pubDate는 manifest의 published_at
(daily_archive의 archived_at 근사치, published_at_is_approximate=True로
이미 표시돼 있음)을 그대로 RFC 822로 변환한다 -- 확정 발행시각처럼
위장하지 않는다.
"""
import email.utils as _eu
import xml.etree.ElementTree as _ET
from datetime import datetime as _dt, timezone as _tz

FEED_TITLE = "Daily MOO:conomy"
FEED_LINK = "https://mooconomy.co.kr"
FEED_DESCRIPTION = "Daily MOO:conomy가 실제로 발행한 뉴스레터 전체 목록입니다."
MAX_ITEMS = 30


def _escape(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _rfc822(iso_ts):
    try:
        dt = _dt.fromisoformat(iso_ts)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return _eu.format_datetime(dt)


def build_rss(manifest):
    """manifest: publish_issue_archive.py의 issues_manifest.json 리스트.
    최신순 정렬해 상위 MAX_ITEMS건만 담는다."""
    items_meta = sorted(manifest, key=lambda m: m["issue_date"], reverse=True)[:MAX_ITEMS]

    items_xml = []
    for m in items_meta:
        link = f"https://mooconomy.co.kr{m['public_path']}"
        title = _escape(m.get("title") or m["issue_date"])
        description = _escape(m.get("morning_thesis") or "")
        pub_date = _rfc822(m.get("published_at"))
        parts = [
            "    <item>",
            f"      <title>{title}</title>",
            f"      <link>{link}</link>",
            f"      <guid isPermaLink=\"true\">{link}</guid>",
        ]
        if description:
            parts.append(f"      <description>{description}</description>")
        if pub_date:
            parts.append(f"      <pubDate>{pub_date}</pubDate>")
        parts.append("    </item>")
        items_xml.append("\n".join(parts))

    items_block = "\n".join(items_xml)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{_escape(FEED_TITLE)}</title>\n"
        f"    <link>{FEED_LINK}</link>\n"
        f"    <description>{_escape(FEED_DESCRIPTION)}</description>\n"
        f"{items_block}\n"
        "  </channel>\n"
        "</rss>\n"
    )


def validate_rss_xml(xml_text):
    try:
        _ET.fromstring(xml_text)
        return []
    except _ET.ParseError as e:
        return [f"rss_xml_parse_error:{e}"]
