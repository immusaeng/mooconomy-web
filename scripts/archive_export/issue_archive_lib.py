"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE) 공용
라이브러리 — data/daily_archive/{date}.json(daily-briefing이 이미 운영
중인 canonical 아카이브)을 읽어 issue 페이지·아카이브 목록에 쓸 정규화
metadata를 만들고, 개인정보 감사·HTML 유효성 검사를 제공한다.

원칙:
- 문장을 요약·재작성하지 않는다 — daily_archive 레코드의 값을 그대로
  옮긴다.
- production_status가 SEND_CONFIRMED이고 실콘텐츠(subject/thesis/
  main_story/narratives)가 전부 있는 레코드만 "유효"로 본다 — 백필
  tombstone(is_approximate=True, UNRECOVERABLE_HISTORICAL_CONTENT)은
  콘텐츠를 지어내지 않고 그대로 제외한다.
- 새 LLM 호출 없음, 외부 네트워크 호출 없음.
"""
import glob
import html.parser as _htmlparser
import json
import os
import re

REQUIRED_CONTENT_FIELDS = ("subject", "thesis", "main_story", "narratives")

# daily-briefing의 renderer.make_web_safe_email_candidate()와 동일한 개념을
# mooconomy-web 쪽에서 독립적으로 재구현한 것 — 두 저장소 간 실행 의존성은
# 만들지 않는다(코드 공유 없음, 로직만 같은 의도로 별도 구현).
_UNSUBSCRIBE_MERGE_TAG = "{{{RESEND_UNSUBSCRIBE_URL}}}"
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")
_TRACKING_QUERY_PARAM_RE = re.compile(
    r"[?&](email|recipient(?:_id)?|subscriber(?:_id)?|uid|user_id|customer_id|"
    r"unsubscribe_token|token|rid|sid|utm_[a-z]+)=[^&\"'\s]*",
    re.IGNORECASE,
)
_HREF_ATTR_RE = re.compile(r'href="([^"]*)"')
_MERGE_TAG_RE = re.compile(r"\{\{\{[A-Z_]+\}\}\}")


def load_all_records(archive_dir):
    """data/daily_archive/*.json(index.json 제외)을 전부 읽어
    (date, record_dict) 리스트로 반환한다(날짜순 정렬). 개별 파일이
    깨져 있으면 건너뛰고 오류를 반환값에 포함한다(전체 실패시키지 않음)."""
    records, errors = [], []
    for fp in sorted(glob.glob(os.path.join(archive_dir, "*.json"))):
        name = os.path.basename(fp)
        if name == "index.json":
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            errors.append({"file": name, "error": str(e)})
            continue
        date = d.get("edition_date_kst") or os.path.splitext(name)[0]
        records.append((date, d))
    records.sort(key=lambda t: t[0])
    return records, errors


def classify_record(date, record):
    """레코드 1건을 검사해 (is_valid, reason) 반환. 유효 조건:
    production_status == 'SEND_CONFIRMED' AND 필수 콘텐츠 필드 전부 존재."""
    production_status = record.get("production_status")
    missing = [k for k in REQUIRED_CONTENT_FIELDS if not record.get(k)]
    if production_status != "SEND_CONFIRMED":
        return False, f"production_status={production_status!r}(SEND_CONFIRMED 아님)"
    if missing:
        return False, f"필수 필드 누락: {missing}"
    return True, None


def build_normalized_metadata(date, record):
    """매니페스트 최소 필드로 정규화(CEO 지정 스키마 그대로). published_at은
    daily_archive에 실제 발행시각 필드가 없어 archived_at을 근사치로
    쓰고, published_at_is_approximate=True로 명시한다(실제 발행시각처럼
    위장하지 않음)."""
    return {
        "issue_date": date,
        "title": record.get("subject") or (record.get("thesis") or {}).get("headline"),
        "morning_thesis": (record.get("thesis") or {}).get("headline"),
        "public_path": f"/issues/{date}.html",
        "source_commit_sha": record.get("source_commit_sha"),
        "published_at": record.get("archived_at"),
        "published_at_is_approximate": True,
        "template_version": "v2-dark",
        "privacy_audit_passed": None,  # 페이지 렌더 후 채움(이 함수는 렌더 이전 단계)
    }


def compute_prev_next(valid_metadata_list):
    """issue_date 오름차순으로 정렬된 리스트를 받아 각 항목에 prev_path/
    next_path(없으면 None)를 채워 반환한다. 입력은 이미 유효성 검사를
    통과한 것만이어야 한다(무효 레코드는 이전/다음 사슬에서 아예 제외)."""
    items = sorted(valid_metadata_list, key=lambda m: m["issue_date"])
    for i, m in enumerate(items):
        m["prev_path"] = items[i - 1]["public_path"] if i > 0 else None
        m["prev_date"] = items[i - 1]["issue_date"] if i > 0 else None
        m["next_path"] = items[i + 1]["public_path"] if i < len(items) - 1 else None
        m["next_date"] = items[i + 1]["issue_date"] if i < len(items) - 1 else None
    return items


def make_public_safe_html(html_text):
    """이메일 전용 개인화 요소만 제거한다(daily-briefing renderer.
    make_web_safe_email_candidate와 동일 개념, 독립 재구현). 공개 기사
    링크·비개인화 구독 링크는 건드리지 않는다."""

    def _strip_href(m):
        href = m.group(1)
        href = _TRACKING_QUERY_PARAM_RE.sub("", href)
        href = _EMAIL_RE.sub("", href)
        href = re.sub(r"\?&", "?", href).rstrip("?&")
        return f'href="{href}"'

    out = html_text
    out = out.replace(
        f'<a class="fx-unsubscribe-link" href="{_UNSUBSCRIBE_MERGE_TAG}">수신거부</a>',
        '<span class="fx-unsubscribe-link">수신거부는 실제 수신한 이메일 하단에서 가능합니다</span>',
    )
    out = _HREF_ATTR_RE.sub(_strip_href, out)
    out = _EMAIL_RE.sub("", out)
    out = _MERGE_TAG_RE.sub("", out)  # 위에서 못 잡은 다른 merge tag가 있으면 방어적으로 제거
    # 실발송 이메일 템플릿에 있던 줄끝 공백을 제거한다(렌더링에는 영향
    # 없음, `git diff --check` 통과 목적 — 내용/문구/숫자는 불변).
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    return out


def audit_privacy(html_text):
    """개인화 흔적 감사 — 문제 있으면 이슈 코드 리스트, 없으면 빈 리스트."""
    issues = []
    if _MERGE_TAG_RE.search(html_text):
        issues.append("merge_tag_present")
    if _EMAIL_RE.search(html_text):
        issues.append("email_address_present")
    if _TRACKING_QUERY_PARAM_RE.search(html_text):
        issues.append("tracking_query_param_present")
    return issues


_PUBDATE_RE = re.compile(r"발행\s*(\d{4})년\s*(\d{2})월\s*(\d{2})일")


def extract_kst_date_from_html(html_text):
    """masthead의 '발행 YYYY년 MM월 DD일' 문구(templates/briefing_email_v2_
    greenfield_dark_editorial.html의 fx-mh-pubdate)에서 실제 발행일을
    뽑는다 — latest-email.html이 정말 기대한 날짜의 발행물인지 콘텐츠
    기준으로 검증하기 위함(파일명이 아니라 본문 기준). 코드 주석에 흔한
    'YYYY-MM-DD(TASK_ID=...)' 같은 날짜와 혼동하지 않도록 이 특정 문구만
    매칭한다(임의 날짜 패턴 전체 검색 금지 — 과거 실측 결과 잘못된 날짜를
    집어낸 적이 있어 이 정밀 패턴으로 교체함)."""
    m = _PUBDATE_RE.search(html_text)
    if not m:
        return None
    year, month, day = m.groups()
    return f"{year}-{month}-{day}"


class _BalanceCheckingParser(_htmlparser.HTMLParser):
    """Python 표준 라이브러리 html.parser 기반 태그 스택 검사 — 정규식
    태그 밸런스 검사와 이중으로 확인한다(신규 의존성 없음)."""

    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self._VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass  # 자체 종료 태그(<br/> 등)는 스택에 넣지 않음

    def handle_endtag(self, tag):
        if tag in self._VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"닫는 태그 불일치: </{tag}> (스택 최상단: {self.stack[-1:] or None})")
            return
        self.stack.pop()


_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?(/?)>")
_VOID_TAGS = _BalanceCheckingParser._VOID_TAGS


def validate_html(html_text):
    """(a) 정규식 기반 태그 밸런스, (b) html.parser 기반 태그 스택 검사
    이중으로 확인한다. 문제 있으면 이슈 문자열 리스트, 없으면 빈 리스트."""
    issues = []

    # (a) 정규식 카운트 기반
    stack = []
    for is_close, tag, self_close in _TAG_RE.findall(html_text):
        tag = tag.lower()
        if tag in _VOID_TAGS or self_close:
            continue
        if not is_close:
            stack.append(tag)
        else:
            if not stack or stack[-1] != tag:
                issues.append(f"regex_tag_mismatch:</{tag}>")
            else:
                stack.pop()
    if stack:
        issues.append(f"regex_unclosed_tags:{stack}")

    # (b) html.parser 기반
    parser = _BalanceCheckingParser()
    try:
        parser.feed(html_text)
    except Exception as e:  # html.parser는 관대해 예외가 드물지만 방어적으로 처리
        issues.append(f"htmlparser_exception:{e}")
    else:
        issues.extend(f"htmlparser:{e}" for e in parser.errors)
        if parser.stack:
            issues.append(f"htmlparser_unclosed_tags:{parser.stack}")

    return issues


_RICH_EMAIL_RENDER_MARKER = 'name="x-apple-disable-message-reformatting"'


def is_rich_email_render(html_text):
    """True if this issue page was rendered from the actual sent email
    (build_issue_page.render_from_public_safe_email) rather than
    reconstructed from the leaner daily_archive JSON summary
    (render_from_json_record). The email-client meta tag only exists in
    the real newsletter template -- the JSON-reconstruction _PAGE_HEAD
    never emits it. Used to keep publish_issue_archive.py from silently
    downgrading an already-published rich page to a thinner rebuild once
    a later run's TODAY moves past it."""
    return _RICH_EMAIL_RENDER_MARKER in html_text


def check_internal_links(html_text, site_root, fallback_root=None):
    """HTML 안의 절대경로(/로 시작) 내부 링크가 site_root 기준 실제
    파일로 존재하는지 확인한다. 외부(http/https) 링크·앵커(#)·mailto는
    검사 대상에서 제외.

    site_root가 스왑 전 임시 빌드 디렉터리(_build_tmp)일 때는 그 안에
    없는 페이지(예: /calendar/, /about/)를 전부 오탐으로 끊어낸다 —
    fallback_root(보통 실제 저장소 ROOT)를 주면 거기서도 찾아본 뒤에만
    진짜로 깨진 링크로 판단한다."""
    issues = []
    for href in re.findall(r'href="([^"]*)"', html_text):
        if not href.startswith("/") or href.startswith("//"):
            continue
        path = href.split("#")[0].split("?")[0]
        if not path or path == "/":
            continue
        local_path = os.path.join(site_root, path.lstrip("/"))
        if os.path.isdir(local_path):
            local_path = os.path.join(local_path, "index.html")
        if os.path.exists(local_path):
            continue
        if fallback_root:
            fb_path = os.path.join(fallback_root, path.lstrip("/"))
            if os.path.isdir(fb_path):
                fb_path = os.path.join(fb_path, "index.html")
            if os.path.exists(fb_path):
                continue
        issues.append(f"broken_internal_link:{href}")
    return issues
