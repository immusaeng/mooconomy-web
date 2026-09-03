"""2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION, CEO 결정
DECISION=OPTION_1_EXTRACT_REAL_CONTENT_AND_RESKIN_TO_V8)

일부 과거 날짜(issues/2026-08-11.html 등 7개)는 JSON 요약본이 아니라
실제로 발송된 이메일 원문 아카이브다 — 지금은 폐기된 구형 다크 뉴스레터
템플릿(class="fx-mh"/"fx-mt"/"fx-label" 등)으로 만들어졌다. 이 모듈은
그 원문에서 실제 콘텐츠(본문 텍스트·링크·표·숫자)를 손실 없이 그대로
떼어내 V8 라이트 셸에 넣을 수 있는 형태로 돌려준다.

원칙(CEO 승인):
- 콘텐츠 노드는 원본 HTML 바이트를 그대로 보존한다(재작성/요약/재정렬
  금지) — masthead·hero headline처럼 짧은 텍스트만 별도 필드로 뽑아
  새 컴포넌트에 넣고, 그 외 모든 섹션은 원본 태그를 통째로 옮긴다.
- 이메일/사이트 chrome(발행 이후 새로 만든 공유·내비·구독·수신거부·
  카피라이트)만 제외 대상이다 — 그 목록은 _CHROME_TOP_CLASSES에 있고,
  왜 제외됐는지는 extract_rich_payload()의 dropped_chrome 목록으로
  남는다. 그 밖의 모든 top-level 노드는 kept_nodes에 들어간다.
- 알 수 없는 구조(예: .inner 컨테이너를 못 찾음, hero headline을 못
  찾음)를 만나면 조용히 JSON 경로로 대체하지 않고 RichExtractionError를
  던진다 — 호출자가 그 날짜를 중단하고 보고해야 한다.
"""
import hashlib
import re

from bs4 import BeautifulSoup, NavigableString


class RichExtractionError(Exception):
    """구조를 신뢰성 있게 파싱하지 못했을 때 — 절대 JSON 경로로 조용히
    대체하지 않고, 호출자가 이 날짜를 중단·보고하게 한다."""


# 발행 이후 새로 만든(=원문 콘텐츠가 아닌) chrome. 여기 있는 top-level
# 노드는 새 Action Bar/nav/footer가 대신하므로 버려도 콘텐츠 손실이
# 아니다. 왜 버렸는지는 결과의 dropped_chrome에 (class, text_preview)로
# 남는다.
_CHROME_TOP_CLASSES = {
    "fx-view-in-browser",
    "fx-share-row",
    "fx-issue-nav",
    "fx-archive-link",
    "fx-home-pill-wrap",
    "fx-copyright",
    "fx-signoff",
    "fx-mt-rule",  # 장식용 빈 구분선(텍스트 없음)
}

# masthead(.fx-mh)와 hero(.fx-mt)는 별도 필드로 뽑아 새 컴포넌트에
# 넣는다 — 광고문구 없이 발행일·상태 뱃지·헤드라인 같은 짧은 사실
# 문자열만 옮기므로 여기서 직접 처리한다(아래 kept_nodes 루프에서
# continue로 건너뛴다).
_MASTHEAD_CLASS = "fx-mh"
_HERO_CLASS = "fx-mt"


def _text(el, cls):
    node = el.find(class_=cls) if el else None
    return node.get_text(" ", strip=True) if node else None


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _number_tokens(text):
    """숫자 시퀀스 비교용 — 부호(▲▼+-)와 자릿수 구분(,) 포함,
    비교 대상은 원문·산출물 둘 다 같은 함수로 뽑으므로 표기 규칙
    자체는 무관하다(같은 잣대로 재는 것만 중요)."""
    return re.findall(r"[▲▼+\-]?\d[\d,]*\.?\d*%?", text)


def content_fingerprint(html_fragment_or_soup):
    """본문 payload 하나의 지표(가시 텍스트 sha256, 링크 집합, 이미지
    집합, 표 개수, 숫자 토큰 시퀀스)를 계산한다. 원본 조각과 산출물
    조각에 동일하게 적용해 서로 비교하는 용도 — 셸/클래스/공백 차이는
    get_text()가 이미 지워주므로 자동으로 무시된다."""
    if isinstance(html_fragment_or_soup, str):
        soup = BeautifulSoup(html_fragment_or_soup, "html.parser")
    else:
        soup = html_fragment_or_soup
    text = soup.get_text("\n", strip=True)
    links = sorted({a.get("href", "") for a in soup.find_all("a") if a.get("href")})
    images = sorted({img.get("src", "") for img in soup.find_all("img") if img.get("src")})
    tables = soup.find_all("table")
    return {
        "visible_text_sha256": _sha256(text),
        "visible_text_len": len(text),
        "link_set": links,
        "link_count": len(links),
        "image_set": images,
        "image_count": len(images),
        "table_count": len(tables),
        "number_tokens": _number_tokens(text),
    }


# 구형 다크 템플릿 색상 -> 현재 V8 라이트 토큰. 클래스를 하나하나
# 새로 스타일링하지 않고(구형 클래스가 날짜마다 조금씩 다르므로 그건
# 오히려 실수하기 쉽다) 원본 <style> 블록을 그대로 두고 색상값만
# 결정론적으로 치환한다 — 레이아웃·크기·타이포는 원본 그대로 유지되고
# 색만 라이트 팔레트로 바뀐다. 매칭되지 않는 낯선 색이 나와도(리스크:
# 그 색만 원래 다크 값으로 남음) 콘텐츠 자체는 항상 그대로다.
_DARK_TO_LIGHT_HEX = {
    "#F2F3F5": "#EFEAD9",
    "#0B1220": "#FBF7ED",
    "#141C2E": "#FFFCF3",
    "#171F30": "#FFFCF3",
    "#1B2740": "#F5EDD3",
    "#202A3D": "#F5EDD3",
    "#2A3450": "#F2E4C0",
    "#334155": "#E4D8B8",
    "#4A5570": "#C9B98A",
    "#F4F6FA": "#1A1613",
    "#E8ECF3": "#1A1613",
    "#D9DFEA": "#2A2318",
    "#C7CEDB": "#2A2318",
    "#9FACC4": "#6B5B44",
    "#95A2BA": "#6B5B44",
    "#8996AE": "#8A7550",
    "#7C8AA5": "#8A7550",
    "#6B7A99": "#A08A5E",
    "#F2C94C": "#9E6A15",
    "#D8B84A": "#9E6A15",
    "#C9A227": "#6B4B15",
    "#FF6B6B": "#8B2318",
    "#5B8DEF": "#1E3A5F",
}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def relight_legacy_css(css):
    """구형 다크 <style> 블록의 색상값만 라이트 토큰으로 치환한다.
    셀렉터·레이아웃·폰트 크기는 전혀 건드리지 않는다."""

    def _hex_sub(m):
        return _DARK_TO_LIGHT_HEX.get(m.group(0).upper(), m.group(0))

    css = re.sub(r"#[0-9A-Fa-f]{6}", _hex_sub, css)

    def _rgba_sub(m):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hex_key = "#{:02X}{:02X}{:02X}".format(r, g, b)
        light_hex = _DARK_TO_LIGHT_HEX.get(hex_key)
        if not light_hex:
            return m.group(0)
        lr, lg, lb = _hex_to_rgb(light_hex)
        return f"rgba({lr},{lg},{lb},{m.group(4)}"

    css = re.sub(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([^)]+)", _rgba_sub, css)
    return css


def extract_rich_payload(html, meta):
    """issues/{date}.html의 실제 발송 원문(html)에서 masthead/hero
    필드와, chrome을 제외한 나머지 전체 콘텐츠(원본 HTML 바이트 그대로)를
    뽑는다. 실패하면 RichExtractionError."""
    date = meta["issue_date"]
    source_sha256 = _sha256(html)
    soup = BeautifulSoup(html, "html.parser")

    style_tag = soup.find("style")
    original_style_css = style_tag.get_text() if style_tag else ""

    wrap = soup.find("table", class_="wrap")
    inner = wrap.find("div", class_="inner") if wrap else None
    if inner is None:
        raise RichExtractionError(f"{date}: table.wrap > div.inner 컨테이너를 찾지 못함")

    masthead = {
        "tagline": _text(inner.find(class_=_MASTHEAD_CLASS), "fx-mh-tagline"),
        "pubdate": _text(inner.find(class_=_MASTHEAD_CLASS), "fx-mh-pubdate"),
        "sub": _text(inner.find(class_=_MASTHEAD_CLASS), "fx-mh-sub"),
        "status": _text(inner.find(class_=_MASTHEAD_CLASS), "fx-status-chip"),
    }

    hero_title_html = None
    kept_nodes = []
    dropped_chrome = []

    for child in inner.find_all(recursive=False):
        if isinstance(child, NavigableString):
            continue
        if child.name in ("script", "style"):
            dropped_chrome.append((child.name, "script/style — 콘텐츠 아님"))
            continue
        classes = set(child.get("class") or [])

        if _MASTHEAD_CLASS in classes:
            continue  # 위에서 이미 필드로 추출함

        if _HERO_CLASS in classes:
            headline_el = child.find(class_="fx-mt-headline")
            hero_title_html = (
                headline_el.decode_contents().strip() if headline_el else child.get_text(" ", strip=True)
            )
            continue

        if classes & _CHROME_TOP_CLASSES:
            dropped_chrome.append((" ".join(sorted(classes)), child.get_text(" ", strip=True)[:60]))
            continue

        # 발행 후 삽입된 하단 수신거부 안내(클래스 없는 wrapper div) —
        # 새 footer의 unsubscribe 안내로 대체되므로 chrome으로 취급.
        if child.find("span", class_="fx-unsubscribe-link"):
            dropped_chrome.append(("(unsubscribe wrapper)", child.get_text(" ", strip=True)[:60]))
            continue

        if not child.get_text(strip=True) and not child.find(["img", "table"]):
            dropped_chrome.append((" ".join(sorted(classes)) or "(no class)", "(empty decorative node)"))
            continue

        kept_nodes.append(child)

    if hero_title_html is None:
        raise RichExtractionError(f"{date}: hero headline(.fx-mt-headline)을 찾지 못함")
    if not kept_nodes:
        raise RichExtractionError(f"{date}: chrome 제외 후 남은 콘텐츠 노드가 0개")

    body_html = "".join(str(n) for n in kept_nodes)
    kept_soup = BeautifulSoup(body_html, "html.parser")

    return {
        "issue_date": date,
        "source_sha256": source_sha256,
        "masthead": masthead,
        "hero_title_html": hero_title_html,
        "body_html": body_html,
        "original_style_css": original_style_css,
        "dropped_chrome": dropped_chrome,
        "source_fingerprint": content_fingerprint(kept_soup),
    }
