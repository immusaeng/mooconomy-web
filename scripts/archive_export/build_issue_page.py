"""2026-08-11(TASK_ID=MERGE_PR14_AND_START_MOOCONOMY_WEB_ARCHIVE_SHARE)
2026-09-03(TASK_ID=HOMEPAGE_V3_CONTENT_CORRECTION + OG_SEO): presentation/
metadata layer only.
- <title> fix: render_from_public_safe_email() used to leave the sent
  email's generic <title>Daily MOO:conomy</title> untouched, so every
  recent issue page shared one title. Now both render paths replace it
  with "{실제 제목} | MOO:conomy".
- OG/Twitter/JSON-LD completeness (site_name, locale, image dimensions,
  NewsArticle) — reuses only real metadata already in `meta`/`record`;
  no invented timestamps, categories, or descriptions.
2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION): 두 렌더 경로가
서로 다른 셸(오늘=V8 라이트 이메일 원문, 과거=V2 다크 자체 재구성)을
써서 아카이브 목록에서 날짜별로 디자인이 갈라지는 문제를 고쳤다.
- render_from_json_record()의 전용 다크 템플릿(_PAGE_HEAD, --bg:#0B1220
  등)을 폐기하고, 실제 발행 중인 V8 라이트 이메일의 실측 디자인
  토큰(#EFEAD9/#FBF7ED 배경, #1A1613 잉크, #9E6A15 골드, Iowan Old
  Style 세리프 + 시스템 산세리프)과 컴포넌트 클래스명(masthead,
  hero-headline, chapter-mark, signals, metrics-grid, view-card 등)을
  그대로 재사용해 V8_LIGHT_CSS로 옮겼다 — 이메일 클라이언트 호환용
  테이블 마크업은 웹페이지에 불필요해 시맨틱 HTML로 단순화했지만 색상·
  타이포·크기 토큰은 실측값과 동일하다.
- 과거 레코드에 없는 섹션(MOO:CHAIN, MOO:WORD, Korea Flow 등)은 새로
  만들지 않는다 — render_from_json_record가 원래 다루던 필드(thesis,
  main_story, narratives, moo_q, moo_check, sources, metrics)만 V8
  컴포넌트에 매핑한다.
- 공유·구독 위젯을 헤드라인 아래 단일 Action Bar(구독하기/공유하기/
  링크 복사)로 통합했다 — 기존에 있던 상단+하단 중복 공유 위젯과
  구독 버튼 부재를 함께 고쳤다. 구독 링크는 실제 발행 이메일 하단
  pill(footer-pill-link)이 쓰는 실제 운영 경로를 그대로 쓴다.
- robots: 두 경로 모두 날짜별 페이지에는 index,follow를 강제한다(발송
  이메일 원문이 가진 noindex를 무조건 덮어쓴다) — latest.html 전용
  noindex는 publish_issue_archive.py가 복사 시점에 별도로 적용한다.

두 가지 렌더 경로:
- render_from_public_safe_email(): 실제 발송본을 그대로 가진 날짜(오늘)용
  — data/daily_archive의 JSON을 다시 조합하지 않고, 이미 개인정보를
  제거한 실제 이메일 HTML(issue_archive_lib.make_public_safe_html 처리
  완료본)에 웹 전용 요소(canonical/OG/prev-next/아카이브 링크/Action
  Bar/robots 강제)만 삽입한다 — 본문·섹션순서·문구·숫자·V8 디자인은
  실발송본과 동일, 추가되는 것은 웹 전용 metadata·내비게이션·공유
  UI뿐이다.
- render_from_json_record(): 실제 발송 HTML이 남아있지 않은 과거 날짜용
  — data/daily_archive/{date}.json(daily-briefing이 이미 정규화해 둔
  실콘텐츠)만으로 V8 라이트 톤앤매너 페이지를 만든다. 문장을 새로
  쓰지 않고 레코드 값을 그대로 옮긴다.

두 경로 모두 새 LLM 호출 없음, 외부 네트워크 호출 없음.
"""
import json
import re

import rich_email_extract as ree

# 이 마커가 있으면 publish_issue_archive.py는 이 페이지를 이미 완성된
# 것으로 보고 다시 만들지 않는다(issue_archive_lib.is_rich_email_render
# 참고) — 원본 이메일의 x-apple-disable-message-reformatting 마커는
# extract_rich_payload()가 콘텐츠만 떼어내는 과정에서 사라지므로,
# 대신 이 마커를 남겨 다음 날 오케스트레이터가 얇은 JSON 재구성본으로
# 되돌리지 않게 한다.
RICH_EXTRACTED_MARKER = "<!-- MOOCONOMY_RICH_EXTRACTED_V8 -->"

_METRIC_LABELS = {
    "kospi": "코스피", "kosdaq": "코스닥", "nasdaq": "나스닥", "sp500": "S&P500",
    "usdkrw": "원/달러", "us10y": "미국채10년", "wti": "WTI", "vix": "VIX",
}

_OG_ISSUE_IMAGE = "https://mooconomy.co.kr/assets/og/og-issue-v3.png"
_PUBLISHER_LOGO = "https://mooconomy.co.kr/android-chrome-512x512.png"

# 실제 발행 이메일 footer-pill-link가 쓰는 것과 동일한, 현재 운영 중인
# 구독 경로(추정/신규 발명 금지 — issues/2026-09-03.html 실측값).
_SUBSCRIBE_URL = "/#home/subscribe"

# ── Action Bar(구독하기/공유하기/링크 복사) — 헤드라인 바로 아래 단일
# 위젯 하나로 통합한다(중복 상단+하단 공유 위젯 금지, 스펙 "DUPLICATE_
# ACTION_REMOVED"). canonical 누락 시 공유 URL이 window.location으로
# 잘못 폴백하는 걸 막기 위해 _head_meta_block()이 빌드 단계에서 이미
# canonical 누락을 예외로 막는다(MissingCanonicalPathError 참고) —
# 아래 런타임 폴백은 이론상 도달하지 않아야 하는 이중 안전망이다.
_SHARE_SCRIPT = """
<script>
(function () {
  var canonicalEl = document.querySelector('link[rel="canonical"]');
  var url = canonicalEl ? canonicalEl.href : window.location.href.split('?')[0].split('#')[0];
  var title = document.title;
  var statusEl = document.querySelector('[data-fx-share-status]');
  var busy = false;

  function withBusyGuard(fn) {
    return function () {
      if (busy) return;
      busy = true;
      fn();
      setTimeout(function () { busy = false; }, 600);
    };
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  function showSelectableUrl() {
    if (!statusEl) return;
    statusEl.textContent = '';
    var input = document.createElement('input');
    input.type = 'text';
    input.value = url;
    input.readOnly = true;
    input.className = 'fx-share-fallback-url';
    input.setAttribute('aria-label', '공유 링크(직접 선택해 복사하세요)');
    statusEl.appendChild(input);
    input.focus();
    input.select();
  }

  function showStatus(msg) {
    if (statusEl) statusEl.textContent = msg;
  }

  function copyLink() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () {
        showStatus('링크를 복사했습니다.');
      }).catch(function () {
        if (fallbackCopy(url)) { showStatus('링크를 복사했습니다.'); } else { showSelectableUrl(); }
      });
    } else if (fallbackCopy(url)) {
      showStatus('링크를 복사했습니다.');
    } else {
      showSelectableUrl();
    }
  }

  document.querySelectorAll('[data-fx-share]').forEach(function (btn) {
    btn.addEventListener('click', withBusyGuard(function () {
      if (navigator.share) {
        navigator.share({ title: title, text: btn.getAttribute('data-fx-share-text') || title, url: url }).catch(function (err) {
          if (err && err.name === 'AbortError') return;
          copyLink();
        });
      } else {
        copyLink();
      }
    }));
  });
  document.querySelectorAll('[data-fx-copy]').forEach(function (btn) {
    btn.addEventListener('click', withBusyGuard(copyLink));
  });
})();
</script>
"""


def _action_bar_html(meta):
    share_text = (meta.get("morning_thesis") or meta.get("title") or "")[:100]
    share_text_attr = share_text.replace('"', "&quot;")
    return (
        '<div class="fx-action-bar" role="group" aria-label="발행판 액션">'
        f'<a class="fx-btn fx-btn-primary" href="{_SUBSCRIBE_URL}">구독하기</a>'
        f'<button type="button" data-fx-share data-fx-share-text="{share_text_attr}" class="fx-btn fx-btn-secondary">'
        '<span aria-hidden="true">↗</span> 공유하기</button>'
        '<button type="button" data-fx-copy class="fx-btn fx-btn-tertiary">'
        '<span aria-hidden="true">⧉</span> 링크 복사</button>'
        '</div>'
        '<p class="fx-action-status" data-fx-share-status role="status" aria-live="polite"></p>'
    )


# 3단 위계(스펙): 구독=최강(잉크 배경+크림 글자) / 공유=보조(연한 골드
# 필) / 복사=3순위(투명+얇은 테두리). 실측 V8 토큰(#1A1613/#F2E4C0/
# #6B4B15/#C9B98A)만 쓴다 — 새 색을 만들지 않는다.
_ACTION_BAR_CSS = """
.fx-action-bar { display:flex; justify-content:center; align-items:center; flex-wrap:wrap; gap:10px; width:100%; margin:17px 0 6px; }
.fx-btn { display:inline-flex; align-items:center; justify-content:center; gap:6px; min-height:42px; padding:0 18px; font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif; font-size:13px; font-weight:700; border-radius:3px; cursor:pointer; text-decoration:none; line-height:1; box-sizing:border-box; }
.fx-btn-primary { background:#1A1613; color:#FBF7ED; border:1px solid #1A1613; }
.fx-btn-secondary { background:#F2E4C0; color:#6B4B15; border:1px solid #E4D8B8; }
.fx-btn-tertiary { background:transparent; color:#6B5B44; border:1px solid #C9B98A; }
.fx-btn:focus-visible { outline:2px solid #9E6A15; outline-offset:2px; }
.fx-action-status { min-height:16px; margin:0 0 12px; text-align:center; font-size:11.5px; color:#8A7550; }
.fx-share-fallback-url { font-size:11.5px; color:#1A1613; background:#FBF3DE; border:1px solid #DDCEA6; border-radius:4px; padding:6px 8px; min-width:220px; max-width:100%; }
@media (max-width:420px) { .fx-btn { flex:1 1 auto; padding:0 12px; font-size:12.5px; } }
"""

_NAV_CSS = """
.fx-issue-nav { display:flex; justify-content:space-between; gap:12px; margin-top:22px; padding-top:16px; border-top:1px solid #E4D8B8; font-size:12.5px; font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif; }
.fx-issue-nav a { color:#6B5B44; text-decoration:none; }
.fx-issue-nav a:hover { color:#9E6A15; }
.fx-archive-link { text-align:center; margin-top:14px; font-size:12.5px; font-family:-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif; }
.fx-archive-link a { color:#9E6A15; text-decoration:none; }
"""

# 2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION_REBASE §7 모바일
# 정책) — 발송 이메일 원문은 이메일 클라이언트 호환을 위해 .sheet
# table에 고정 픽셀 width(속성 + 인라인 style 둘 다)를 박아둔다. 이건
# 이메일에서는 맞는 선택이지만, 그 본문을 그대로 웹페이지에 옮기면
# 390px 같은 좁은 화면에서 가로 스크롤이 생긴다. 뉴스레터 저장소의
# 원본 템플릿은 절대 건드리지 않고, 여기(웹 전용 셸 레이어)에서만
# !important로 덮어써 웹 issue 페이지 한정으로 반응형을 강제한다 —
# 이메일 클라이언트 렌더링 자체는 이 CSS의 영향을 받지 않는다.
_WEB_RESPONSIVE_OVERRIDE_CSS = """
@media (max-width:700px) {
  table.sheet, .sheet { width:100% !important; max-width:100% !important; min-width:0 !important; table-layout:fixed !important; }
  table.sheet > tbody > tr > td, .sheet > tbody > tr > td { width:100% !important; word-break:break-word; }
}
"""

# 2026-09-05(TASK_TRACK=NEWSLETTER_MOBILE_SHARE_AND_CALENDAR_CTA) — 카카오톡
# 공유로 유입되는 이 웹 issue 페이지에서 360/390px 정보 밀도를 높인다.
# 위 _WEB_RESPONSIVE_OVERRIDE_CSS와 동일 원칙(웹 셸 레이어 한정 !important
# 오버라이드, 뉴스레터 저장소 원본 템플릿 무변경, 이메일 클라이언트 렌더링
# 영향 없음)을 확장한다 — 같은 700px 분기점을 재사용해 768/1280px에는
# 전혀 적용되지 않는다. 데스크톱 좌우 여백(48px)만 16px로 줄이고, 색상·
# 타이포·섹션 순서·문구·본문 글자 크기(news-title/news-fact 등)는 손대지
# 않는다 — 2열 뉴스만 좁은 화면에서 헤드라인이 과도하게 줄바꿈되는 걸
# 막기 위해 1열로 세로 적층한다(항목 삭제 없음, 순서 유지).
_WEB_MOBILE_DENSITY_CSS = """
@media (max-width:700px) {
  .pad-l { padding:0 16px !important; }
  .masthead { padding:18px 0 14px !important; }
  .brand-wm { font-size:30px !important; }
  .mast-tagline { font-size:12.5px !important; margin-top:8px !important; }
  .mast-meta { margin-top:12px !important; padding-top:10px !important; }
  .hero { padding:16px 16px 10px !important; }
  .hero-headline { font-size:21px !important; }
  .chapter-mark { padding:14px 16px 8px !important; }
  .chap-title { font-size:18px !important; }
  .signals-strip, .metrics-wrap, .temp-wrap, .flow-wrap, .overnight-wrap,
  .story-wrap, .news-wrap, .watch-wrap { padding-left:16px !important; padding-right:16px !important; }
  .m-value { font-size:21px !important; white-space:normal !important; word-break:break-word !important; }
  .story-h { font-size:19px !important; }
  .news-cols, .news-cols > tbody, .news-cols > tbody > tr { display:block !important; width:100% !important; }
  .news-cols > tbody > tr > td { display:block !important; width:100% !important; padding:0 !important; border-right:none !important; }
  .news-cols > tbody > tr > td:first-child { border-bottom:1px solid #E4D8B8 !important; padding-bottom:14px !important; margin-bottom:14px !important; }
  .brand-wrap > tbody > tr > td.spacer { width:16px !important; }
  .brand-card { padding:16px 18px !important; }
  .doc-card { padding:16px 16px !important; }
  .footer-wrap { padding:18px 16px 28px !important; }
  .calendar-cta { padding:6px 16px 0 !important; }
}
"""

# 뉴스 섹션 종료 지점(다음 섹션인 MOO:VIEW 시작 직전) 인라인 CTA 1개.
# 발송 이메일 본문에는 전혀 없는 웹 전용 컴포넌트 — .spine-cta(MOO:Q →
# CHECK 안의 기존 보조 링크)와 같은 색/굵기(#9E6A15, 이탤릭, 400)를 그대로
# 재사용해 뉴스 제목·MOO:VIEW/MOO:Q 브랜드 플래그보다 강조되지 않게 한다.
_CALENDAR_CTA_CSS = """
.calendar-cta { padding:8px 48px 0; text-align:center; }
.calendar-cta a { display:inline-block; padding:6px 4px; font-family:'Iowan Old Style', Georgia, serif; font-size:12.5px; font-style:italic; color:#9E6A15; text-decoration:none; border-bottom:1px solid #9E6A15; letter-spacing:0.01em; }
"""

_CALENDAR_CTA_HTML = (
    '<div class="calendar-cta"><a href="https://mooconomy.co.kr/calendar/">'
    '다음 시장 이벤트가 궁금하다면? MOO:CALENDAR →</a></div>\n'
)


class CalendarCtaAnchorMissingError(ValueError):
    """뉴스 섹션 다음 첫 <table class="brand-wrap">(MOO:VIEW) 앵커를 찾지
    못했다 — 이메일 템플릿 구조가 바뀌어 CTA를 넣을 자리가 사라졌다는
    뜻이다. CTA 없이 페이지를 조용히 발행하지 않고 빌드를 즉시 실패시켜,
    "CTA가 어느 날 슬그머니 사라진다"는 회귀를 원천 차단한다."""


_CALENDAR_CTA_MARKER = 'class="calendar-cta"'
_CALENDAR_CTA_ANCHOR = '<table class="brand-wrap"'


def _insert_calendar_cta(html):
    """뉴스 섹션(.news-wrap) 바로 다음, MOO:VIEW 카드(첫 번째 .brand-wrap
    테이블) 시작 직전에 정확히 1회 삽입한다. MOO:VIEW는 데이터 유무와
    무관하게 항상 렌더되는 섹션이라(폴백 문구 존재) 이 앵커는 결정론적이다.
    count=1이라 이후 MOO:Q/CHAIN/WORD가 재사용하는 같은 class="brand-wrap"
    테이블에는 영향 없다.

    Idempotent: 이미 CTA가 삽입된 html이 다시 들어오면(예: 파이프라인이
    같은 입력에 이 함수를 두 번 호출) 그대로 반환한다 — 중복 삽입 금지.
    앵커 자체가 없으면 CalendarCtaAnchorMissingError로 명시적으로
    실패한다 — 앵커 누락을 "CTA 없이 조용히 통과"로 처리하지 않는다."""
    if _CALENDAR_CTA_MARKER in html:
        return html
    if _CALENDAR_CTA_ANCHOR not in html:
        raise CalendarCtaAnchorMissingError(
            f"캘린더 CTA 삽입 앵커({_CALENDAR_CTA_ANCHOR!r})를 찾지 못했습니다 — "
            "이메일 템플릿 구조가 바뀌었을 수 있습니다. 빌드를 중단합니다."
        )
    return html.replace(_CALENDAR_CTA_ANCHOR, _CALENDAR_CTA_HTML + _CALENDAR_CTA_ANCHOR, 1)


def _clean_description(meta):
    """morning_thesis가 title과 사실상 같으면(현재 manifest 다수가 그렇다)
    "설명"으로서 정보가 없다 — 태그를 생략하고 제목을 복제하지 않는다."""
    desc = (meta.get("morning_thesis") or "").strip()
    title = (meta.get("title") or "").strip()
    if not desc or desc == title:
        return None
    return desc[:150]


def _news_article_jsonld(meta, description, canonical):
    """2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION) — headline/
    description을 {x!r}.replace("'", '"')로 이스케이프하던 기존 방식은
    제목에 큰따옴표가 실제로 들어있는 날(예: 2026-08-17 "머니무브")
    이스케이프되지 않은 "가 그대로 남아 JSON-LD 파싱이 깨졌다(pre-existing
    bug, 이 마이그레이션에서 처음 드러남). json.dumps로 교체 — 실제
    JSON 문자열 이스케이프 규칙을 따른다."""
    title = meta.get("title") or "Daily MOO:conomy"
    published = meta.get("published_at") if not meta.get("published_at_is_approximate") else None
    fields = [
        '"@context": "https://schema.org"',
        '"@type": "NewsArticle"',
        f'"headline": {json.dumps(title, ensure_ascii=False)}',
        f'"mainEntityOfPage": {{ "@type": "WebPage", "@id": "{canonical}" }}',
        f'"url": "{canonical}"',
        f'"image": ["{_OG_ISSUE_IMAGE}"]',
        '"publisher": { "@type": "Organization", "name": "Daily MOO:conomy", '
        f'"logo": {{ "@type": "ImageObject", "url": "{_PUBLISHER_LOGO}" }} }}',
    ]
    if description:
        fields.append(f'"description": {json.dumps(description, ensure_ascii=False)}')
    if published:
        fields.append(f'"datePublished": "{published}"')
    # dateModified: 실제 수정 시각 필드가 데이터에 없어 임의로 채우지 않는다(생략).
    body = ",\n  ".join(fields)
    return f'<script type="application/ld+json">\n{{\n  {body}\n}}\n</script>\n'


class MissingCanonicalPathError(ValueError):
    """meta['public_path']가 없으면 공유 위젯이 window.location으로
    조용히 폴백해(예: latest.html에서 자기 자신을 공유) 날짜별 canonical
    보장이 깨진다 — 2026-09-03(§F, CEO 승인 "canonical이 없으면 공유
    기능을 활성화하지 말고 빌드 검증을 실패시킨다") 빌드 단계에서
    즉시 실패시킨다."""


def _head_meta_block(meta, description):
    """canonical + OG(완전판) + Twitter Card + NewsArticle JSON-LD.
    두 렌더 경로 모두 이 한 함수만 쓰므로, 다음 자동 재생성부터도
    동일하게 적용된다(수동으로 산출물만 고치지 않는다)."""
    if not (meta or {}).get("public_path"):
        raise MissingCanonicalPathError(
            "meta['public_path']가 비어 있음 — canonical URL을 만들 수 없어 "
            "공유 위젯이 window.location으로 잘못 폴백할 위험이 있다. 빌드 중단.",
        )
    canonical = f"https://mooconomy.co.kr{meta['public_path']}"
    title = meta["title"] or "Daily MOO:conomy"
    lines = [
        f'<link rel="canonical" href="{canonical}">',
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="Daily MOO:conomy">',
        '<meta property="og:locale" content="ko_KR">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{_OG_ISSUE_IMAGE}">',
        f'<meta property="og:image:secure_url" content="{_OG_ISSUE_IMAGE}">',
        '<meta property="og:image:type" content="image/png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Daily MOO:conomy">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{title}">',
        f'<meta name="twitter:image" content="{_OG_ISSUE_IMAGE}">',
    ]
    if description:
        lines.insert(1, f'<meta name="description" content="{description}">')
        lines.append(f'<meta property="og:description" content="{description}">')
        lines.append(f'<meta name="twitter:description" content="{description}">')
    if meta.get("published_at") and not meta.get("published_at_is_approximate"):
        lines.append(f'<meta property="article:published_time" content="{meta["published_at"]}">')
    # article:modified_time / article:section: 실제 데이터에 없어 생략(추정 금지).
    lines.append(_news_article_jsonld(meta, description, canonical))
    return "\n".join(lines)


def _nav_block(meta):
    prev_link = (f'<a href="{meta["prev_path"]}">← {meta["prev_date"]}</a>'
                 if meta.get("prev_path") else '<span></span>')
    next_link = (f'<a href="{meta["next_path"]}">{meta["next_date"]} →</a>'
                 if meta.get("next_path") else '<span></span>')
    return (
        f'<div class="fx-issue-nav">{prev_link}{next_link}</div>'
        f'<div class="fx-archive-link"><a href="/archive/">전체 발행 목록 보기</a></div>'
    )


def _force_index_follow_robots(html):
    """발송 이메일 원문은 이메일이라 noindex를 갖고 있다 — 날짜별
    웹페이지로 쓸 때는 무조건 index,follow로 덮어쓴다(latest.html 전용
    noindex는 publish_issue_archive.py가 복사 시점에 별도로 적용)."""
    tag = '<meta name="robots" content="index,follow">'
    if re.search(r'<meta\s+name="robots"[^>]*>', html):
        return re.sub(r'<meta\s+name="robots"[^>]*>', tag, html, count=1)
    if "<head>" in html:
        return html.replace("<head>", "<head>\n" + tag, 1)
    return tag + "\n" + html


def render_from_public_safe_email(public_safe_html, meta):
    """오늘자처럼 실제 발송 HTML(개인정보 제거 완료본)이 있는 경우 —
    기존 문장·데이터·섹션 순서는 재작성하지 않고, <title>을 실제 제목으로,
    robots를 index,follow로 바꾸고 <head> 안에 canonical/OG/JSON-LD를,
    헤드라인 바로 아래에 Action Bar(+이전/다음/아카이브 링크는 하단)를
    삽입만 한다. 2026-09-05(TASK_TRACK=NEWSLETTER_MOBILE_SHARE_AND_
    CALENDAR_CTA)부터 예외 1건 추가: 뉴스 섹션 종료 지점에 고정 문구·고정
    링크(데이터 비의존) 캘린더 CTA 1개를 삽입한다 — 이것도 기존 문장을
    바꾸는 게 아니라 새 줄 하나를 끼워 넣는 것뿐이라 원칙은 유지된다."""
    html = public_safe_html
    html = _force_index_follow_robots(html)
    description = _clean_description(meta)
    title_tag = f'<title>{meta["title"] or "발행 기록"} | MOO:conomy</title>'
    html = re.sub(r"<title>.*?</title>", title_tag, html, count=1, flags=re.S)
    meta_block = _head_meta_block(meta, description)
    html = html.replace("</title>", "</title>\n" + meta_block, 1)
    html = html.replace(
        "</style>\n",
        "</style>\n<style>" + _ACTION_BAR_CSS + _NAV_CSS + _WEB_RESPONSIVE_OVERRIDE_CSS
        + _WEB_MOBILE_DENSITY_CSS + _CALENDAR_CTA_CSS + "</style>\n",
        1,
    )
    html = _insert_calendar_cta(html)

    # 헤드라인 바로 아래(웹 전용) — 이메일 템플릿마다 클래스명이 다를 수 있어
    # hero-headline을 우선 찾고, 없으면 body 시작 직후로 안전하게 폴백한다.
    action_bar = _action_bar_html(meta)
    headline_match = re.search(r'<h1[^>]*class="[^"]*hero-headline[^"]*"[^>]*>.*?</h1>', html, re.S)
    if headline_match:
        insert_at = headline_match.end()
        html = html[:insert_at] + action_bar + html[insert_at:]
    else:
        body_match = re.search(r"<body[^>]*>", html)
        if body_match:
            insert_at = body_match.end()
            html = html[:insert_at] + action_bar + html[insert_at:]

    # 아래쪽엔 공유/구독 버튼을 중복해 넣지 않는다(위 Action Bar 하나로
    # 통합 - 스펙 "DUPLICATE_ACTION_REMOVED") — prev/next+아카이브 링크만.
    injected = _nav_block(meta) + _SHARE_SCRIPT
    if "</body>" in html:
        html = html.replace("</body>", f'<div class="inner">{injected}</div>\n</body>', 1)
    else:
        html += injected
    return html


# ── V8 라이트 셸(과거 JSON 레코드 전용) ───────────────────────────────
# 실제 발행 중인 이메일(issues/2026-09-03.html 실측)과 같은 배경/잉크/
# 골드 토큰, 같은 컴포넌트 클래스명을 쓴다. 이메일 클라이언트 호환용
# table 마크업은 웹페이지에 불필요해 시맨틱 태그로 단순화했지만 색상·
# 폰트·크기는 실측값 그대로다. MOO:CHAIN/MOO:WORD/Korea Flow처럼 과거
# JSON 레코드에 없는 섹션은 만들지 않는다.
_V8_LIGHT_CSS = """
  body { margin:0; padding:0; background:#EFEAD9; color:#1A1613; font-family:-apple-system,BlinkMacSystemFont,'Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic','Segoe UI',Arial,sans-serif; font-size:14px; line-height:1.75; word-break:keep-all; }
  * { box-sizing:border-box; }
  .sheet { width:100%; max-width:760px; margin:0 auto; background:#FBF7ED; padding:0 48px; }
  @media (max-width:700px) { .sheet { padding:0 18px; } }

  .masthead { padding:36px 0 22px; text-align:center; border-bottom:3px double #3A2D18; }
  .brand-wm { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:44px; font-weight:800; color:#1A1613; letter-spacing:-0.03em; line-height:1; text-decoration:none; display:inline-block; }
  .brand-wm .g { color:#9E6A15; }
  .mast-tagline { font-size:13.5px; color:#6B5B44; line-height:1.55; margin-top:12px; }
  .mast-meta { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-top:18px; padding-top:14px; border-top:1px solid #E4D8B8; font-size:12px; color:#8A7550; letter-spacing:0.02em; }
  .status-badge { display:inline-block; background:#F2E4C0; color:#6B4B15; padding:4px 12px; font-weight:700; letter-spacing:0.06em; font-size:11.5px; }
  @media (max-width:700px) { .masthead { padding:26px 0 18px; } .brand-wm { font-size:34px; } .mast-meta { justify-content:center; text-align:center; } }

  .hero { padding:24px 0 18px; }
  .hero-kicker { font-family:'Iowan Old Style',Georgia,serif; font-size:11.5px; font-weight:700; color:#9E6A15; letter-spacing:0.24em; text-transform:uppercase; margin:0 0 12px; }
  .hero-headline { font-size:26px; font-weight:800; line-height:1.35; letter-spacing:-0.02em; color:#1A1613; margin:0; }
  @media (max-width:700px) { .hero-headline { font-size:22px; } }

  .chapter-mark { padding:20px 0 12px; }
  .chap-bar { height:4px; background:#1A1613; margin-bottom:14px; }
  .chap-row { display:flex; align-items:baseline; gap:14px; }
  .chap-num { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:18px; font-weight:800; color:#9E6A15; font-style:italic; flex-shrink:0; }
  .chap-title { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:21px; font-weight:800; color:#1A1613; }
  .chap-kicker { display:block; font-size:13px; color:#6B5B44; margin-top:5px; }
  @media (max-width:700px) { .chap-title { font-size:18px; } }

  .flag-data { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:13px; font-weight:700; color:#6B4B15; letter-spacing:0.22em; text-transform:uppercase; margin:0 0 10px; border-bottom:1px solid #C9B98A; padding-bottom:10px; font-style:italic; }
  .flag-brand { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:23px; font-weight:800; color:#1A1613; letter-spacing:-0.02em; font-style:italic; margin:0 0 14px; }
  .flag-brand .colon { color:#9E6A15; font-style:normal; }

  .signals-strip { padding:22px 0 0; }
  .signals { width:100%; }
  .signals-row { display:flex; gap:12px; padding:4px 0 5px; }
  .idx-num { font-family:'Iowan Old Style',Georgia,serif; font-size:14px; font-weight:700; color:#9E6A15; font-style:italic; flex-shrink:0; width:26px; }
  .signals-row .t { font-size:15px; line-height:1.55; color:#1A1613; }
  @media (max-width:700px) { .signals-row .t { font-size:14.5px; } }

  .metrics-wrap { padding:22px 0 0; }
  .metrics-grid { display:grid; grid-template-columns:repeat(3,1fr); }
  .cell-inner { background:#FFFCF3; border-top:2px solid #3A2D18; border-right:1px solid #E4D8B8; padding:12px 10px; text-align:center; }
  .metrics-grid > div:nth-child(3n) .cell-inner { border-right:none; }
  .m-label { font-size:12px; color:#8A7550; letter-spacing:0.02em; display:block; text-align:left; }
  .m-value { font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:26px; font-weight:700; color:#1A1613; letter-spacing:-0.01em; line-height:1.05; margin:6px 0 4px; font-variant-numeric:tabular-nums; }
  .m-chg { font-family:'Iowan Old Style',Georgia,serif; font-size:12.5px; font-weight:700; font-variant-numeric:tabular-nums; }
  .up { color:#8B2318; } .down { color:#1E3A5F; } .flat { color:#8A7550; }
  @media (max-width:700px) { .m-value { font-size:20px; } .m-label { font-size:11px; } .m-chg { font-size:11.5px; } }

  .brand-card { padding:22px 0; margin:24px 0; }
  .view-card { background:#FFFCF3; border:1px solid #E4D8B8; border-top:3px solid #1A1613; padding:22px 26px; }
  .view-p { font-size:14.5px; line-height:1.75; color:#1A1613; margin:0 0 12px; }
  .view-sig { padding-top:14px; border-top:1px solid #E4D8B8; font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif; font-size:14px; font-weight:800; color:#1A1613; font-style:italic; text-align:right; }
  .view-sig .g { color:#9E6A15; font-style:normal; }

  .doc-card { background:#F5EDD3; border:1px solid #C9B98A; padding:22px 26px; }
  .spine-block + .spine-block { margin-top:18px; padding-top:16px; border-top:1px dashed #C9B98A; }
  .spine-t-lbl { font-family:'Iowan Old Style',Georgia,serif; font-size:11px; font-weight:700; color:#9E6A15; letter-spacing:0.22em; text-transform:uppercase; margin:0 0 10px; font-style:italic; }
  .spine-tq { font-size:15px; font-weight:700; color:#1A1613; line-height:1.5; margin:0 0 8px; }
  .spine-note { font-size:12.5px; color:#6B5B44; margin:0; }
  .verdict-inline { display:inline-block; font-family:'Iowan Old Style',Georgia,serif; font-size:11px; font-weight:700; padding:3px 6px; letter-spacing:0.02em; border:1px solid #8A7550; background:#FBF7ED; color:#6B5B44; margin-top:6px; }

  .watch-wrap { padding:22px 0 0; }
  .watch-item { font-size:15px; line-height:1.55; color:#1A1613; padding:8px 0; }
  @media (max-width:700px) { .watch-item { font-size:14.5px; } }
  .watch-oneliner { font-size:15px; font-weight:700; color:#1A1613; line-height:1.6; margin:16px 0 0; padding:14px 18px; background:#FBF3DE; border-left:3px solid #9E6A15; }

  .src-wrap { padding:22px 0 0; }
  .src-row { padding:4px 0; font-size:12px; color:#6B5B44; }
  .src-row a { color:#9E6A15; text-decoration:underline; }

  .footer-wrap { padding:28px 0 42px; }
  .footer-rule { height:3px; background:#1A1613; margin-bottom:22px; }
  .footer-copyright { font-family:'Iowan Old Style',Georgia,serif; font-size:11px; color:#A08A5E; font-style:italic; }
"""


def _chapter_mark(num, title, kicker):
    return (
        '<div class="chapter-mark"><div class="chap-bar"></div>'
        f'<div class="chap-row"><span class="chap-num">{num}</span>'
        f'<span><span class="chap-title">{title}</span><span class="chap-kicker">{kicker}</span></span></div></div>'
    )


def _fmt_change(m):
    unit = "%" if m.get("displayMode") == "pct" else ""
    sign = "▲" if m.get("direction") == "up" else ("▼" if m.get("direction") == "down" else "―")
    return f"{sign} {abs(m.get('change') or 0):.2f}{unit}"


def render_from_json_record(record, meta):
    """과거 날짜(실발송 HTML 없음)용 — data/daily_archive/{date}.json의
    실콘텐츠만으로 V8 라이트 톤앤매너 페이지를 만든다. 문장을 새로 쓰지
    않고 레코드 값을 그대로 옮긴다. 레코드에 없는 섹션은 생략한다."""
    thesis = record.get("thesis") or {}
    main_story = record.get("main_story") or {}
    narratives = record.get("narratives") or {}
    moo_q = record.get("moo_q")
    moo_check = record.get("moo_check") or []
    sources = record.get("sources") or []
    metrics = record.get("metrics") or []

    signals_html = "".join(
        f'<div class="signals-row"><span class="idx-num">{i:02d}</span><span class="t">{s}</span></div>'
        for i, s in enumerate((thesis.get("three_signals") or []), 1)
    ) or '<div class="signals-row"><span class="t">오늘 확인된 신호가 충분하지 않습니다.</span></div>'

    metric_html = "".join(
        '<div><div class="cell-inner">'
        f'<span class="m-label">{_METRIC_LABELS.get(m["id"], m["id"])}</span>'
        f'<div class="m-value">{m["value"]:,.2f}</div>'
        f'<div class="m-chg {m.get("direction") or ""}">{_fmt_change(m)}</div>'
        '</div></div>'
        for m in metrics
    )

    moo_view_text = narratives.get("moo_view") or ""
    moo_view_html = "".join(
        f'<p class="view-p">{p}</p>'
        for p in (p.strip() for p in moo_view_text.split("\n\n")) if p
    )

    watch_items = narratives.get("todays_watch") or []
    watch_html = "".join(f'<div class="watch-item">· {w}</div>' for w in watch_items)
    if narratives.get("todays_watch_oneliner"):
        watch_html += f'<div class="watch-oneliner">{narratives["todays_watch_oneliner"]}</div>'
    if not watch_html:
        watch_html = '<div class="watch-item">오늘의 관전 포인트가 충분하지 않습니다.</div>'

    moo_q_block = ""
    if moo_q:
        moo_q_block = (
            '<div class="spine-block">'
            '<div class="spine-t-lbl">오늘의 새 질문</div>'
            f'<p class="spine-tq">{moo_q["claim_text"]}</p>'
            f'<p class="spine-note">확인 예정일 {moo_q.get("resolution_at", "다음 거래일")}</p>'
            '</div>'
        )

    moo_check_block = ""
    if moo_check:
        rows = "".join(
            '<div class="spine-block">'
            f'<p class="spine-tq">{c["previous_claim"]}</p>'
            f'<span class="verdict-inline">판정: {c.get("verdict", "—")}</span>'
            '</div>'
            for c in moo_check
        )
        moo_check_block = rows

    sources_html = "".join(
        f'<div class="src-row"><a href="{s["source_url"]}" target="_blank" rel="noopener noreferrer">{s["source_name"]} — {s["source_headline"]}</a></div>'
        for s in sources if s.get("source_url", "").startswith(("http://", "https://"))
    )

    description = _clean_description(meta)
    title = meta["title"] or "발행 기록"
    story_headline = main_story.get("headline") or ""
    story_fact = main_story.get("verified_fact") or ""

    main_story_block = ""
    if story_headline or story_fact:
        main_story_block = (
            '<div class="brand-card"><div class="view-card">'
            '<div class="flag-brand">Main Story</div>'
            + (f'<p class="view-p" style="font-weight:700;">{story_headline}</p>' if story_headline else "")
            + (f'<p class="view-p">{story_fact}</p>' if story_fact else "")
            + '</div></div>'
        )

    moo_view_block = ""
    if moo_view_html:
        moo_view_block = (
            '<div class="brand-card"><div class="view-card">'
            '<div class="flag-brand">MOO<span class="colon">:</span>VIEW</div>'
            f'{moo_view_html}<div class="view-sig">— MOO<span class="g">:</span>Editor</div>'
            '</div></div>'
        )

    moo_qc_block = ""
    if moo_q_block or moo_check_block:
        moo_qc_block = (
            '<div class="brand-card"><div class="doc-card">'
            '<div class="flag-brand">MOO<span class="colon">:</span>Q → CHECK</div>'
            f'{moo_q_block}{moo_check_block}'
            '</div></div>'
        )

    body = (
        '<div class="hero">'
        '<div class="hero-kicker">오늘의 관점</div>'
        f'<h1 class="hero-headline">{title}</h1>'
        f'{_action_bar_html(meta)}'
        '</div>'
        + _chapter_mark("CH · I", "Today&#39;s Angle", "— 오늘 시장이 어느 쪽으로 기울었는가")
        + f'<div class="signals-strip"><div class="flag-data">Today&#39;s 3 Signals</div><div class="signals">{signals_html}</div></div>'
        + main_story_block
        + (f'<div class="metrics-wrap"><div class="flag-data">Main Metrics</div><div class="metrics-grid">{metric_html}</div></div>' if metric_html else "")
        + moo_view_block
        + moo_qc_block
        + f'<div class="watch-wrap"><div class="flag-data">Today&#39;s Watch</div>{watch_html}</div>'
        + (f'<div class="src-wrap"><div class="flag-data">Sources</div>{sources_html}</div>' if sources_html else "")
        + f'<div class="footer-wrap">{_nav_block(meta)}<div class="footer-rule"></div><div class="footer-copyright">© 2026 MOO:conomy</div></div>'
    )

    html = (
        '<!DOCTYPE html>\n<html lang="ko">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<meta name="robots" content="index,follow">\n'
        f'<title>{title} | MOO:conomy</title>\n'
        f'{_head_meta_block(meta, description)}\n'
        f'<style>{_V8_LIGHT_CSS}{_ACTION_BAR_CSS}{_NAV_CSS}</style>\n'
        '</head>\n<body>\n'
        f'<div class="sheet">\n'
        '<div class="masthead"><a class="brand-wm" href="/">MOO<span class="g">:</span>conomy</a>'
        f'<div class="mast-meta"><span>발행 {meta["issue_date"]}</span><span class="status-badge">발행 기록</span></div></div>'
        f'{body}\n'
        '</div>\n'
        f'{_SHARE_SCRIPT}\n'
        '</body>\n</html>\n'
    )
    return html


_OLD_SHARE_ROW_RE = re.compile(r'<div class="fx-share-row[^"]*">.*?</div>', re.S)
_OLD_SHARE_STYLE_RE = re.compile(r'<style>\s*\.fx-share-row \{.*?</style>', re.S)
_OLD_SHARE_SCRIPT_RE = re.compile(r"<script>(?:(?!</script>).)*?\.closest\('\.fx-share-row'\).*?</script>", re.S)


def upgrade_existing_v8_page(html, meta):
    """2026-09-04(TASK_ID=ARCHIVE_ISSUE_V8_SHELL_UNIFICATION_REBASE) —
    이 날짜는 이미 실제 V8 라이트 셸(오늘자로 처음 만들어질 때
    render_from_public_safe_email이 만든 것)이라 콘텐츠를 다시 뽑아낼
    필요가 없다. 다만 그 날 TODAY였을 때 아직 통합 Action Bar 이전
    코드로 만들어졌다면(상단+하단 중복 공유 버튼, 구독 버튼 없음,
    noindex) — 그 낡은 위젯만 새 통합 Action Bar로 교체한다. 본문·
    수치·표·링크는 전혀 건드리지 않는다(rich_email_extract처럼
    fingerprint로 검증 가능 — 교체 대상은 위젯 마크업뿐)."""
    out = html
    out = _force_index_follow_robots(out)
    out = _OLD_SHARE_SCRIPT_RE.sub("", out)
    out = _OLD_SHARE_STYLE_RE.sub("", out)
    out = _OLD_SHARE_ROW_RE.sub("", out)
    if "web-responsive-override" not in out:
        out = out.replace(
            "</style>\n",
            "</style>\n<style class=\"web-responsive-override\">" + _WEB_RESPONSIVE_OVERRIDE_CSS + "</style>\n",
            1,
        )
    if "fx-action-bar" not in out:
        out = out.replace("</style>\n", "</style>\n<style>" + _ACTION_BAR_CSS + "</style>\n", 1)
        action_bar = _action_bar_html(meta)
        headline_match = re.search(r'<h1[^>]*class="[^"]*hero-headline[^"]*"[^>]*>.*?</h1>', out, re.S)
        if headline_match:
            insert_at = headline_match.end()
            out = out[:insert_at] + action_bar + out[insert_at:]
        if "</body>" in out:
            out = out.replace("</body>", _SHARE_SCRIPT + "\n</body>", 1)
    return out


def render_from_rich_extracted(payload, meta):
    """실제 발송 이메일 원문이었지만 지금은 폐기된 다크 템플릿으로
    만들어진 과거 날짜용 — rich_email_extract.extract_rich_payload()가
    떼어낸 콘텐츠(원본 HTML 바이트 그대로)를 V8 라이트 셸에 넣는다.
    본문 태그·텍스트·링크·표는 그대로, 색상만 원본 <style> 블록에서
    라이트 토큰으로 치환해 재사용한다(원본 클래스명도 그대로 유지 —
    별도 재매핑이 필요 없다)."""
    description = _clean_description(meta)
    title = meta["title"] or payload["hero_title_html"]
    masthead = payload["masthead"]
    mast_meta_bits = [b for b in (masthead.get("pubdate"), masthead.get("sub")) if b]
    mast_meta_line = " · ".join(mast_meta_bits)

    legacy_css = ree.relight_legacy_css(payload["original_style_css"])
    # <style> 블록뿐 아니라 이메일 호환용 인라인 style="background:#..."/
    # bgcolor="#..." 속성도 같은 색상표로 다시 칠한다 — get_text()가
    # 속성값은 애초에 읽지 않으므로 content fingerprint(가시 텍스트/
    # 링크/표/숫자)에는 전혀 영향이 없다(migrate_rich_issues.py가 이미
    # 검증한 값 그대로 유지).
    legacy_body_html = ree.relight_legacy_css(payload["body_html"])

    body = (
        '<div class="hero">'
        '<div class="hero-kicker">오늘의 관점</div>'
        f'<h1 class="hero-headline">{payload["hero_title_html"]}</h1>'
        f'{_action_bar_html(meta)}'
        '</div>'
        f'<div class="legacy-content">{legacy_body_html}</div>'
        f'<div class="footer-wrap">{_nav_block(meta)}<div class="footer-rule"></div><div class="footer-copyright">© 2026 MOO:conomy</div></div>'
    )

    html = (
        '<!DOCTYPE html>\n<html lang="ko">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<meta name="robots" content="index,follow">\n'
        f'<title>{title} | MOO:conomy</title>\n'
        f'{_head_meta_block(meta, description)}\n'
        f'<style>{_V8_LIGHT_CSS}{_ACTION_BAR_CSS}{_NAV_CSS}{legacy_css}</style>\n'
        '</head>\n<body>\n'
        f'{RICH_EXTRACTED_MARKER}\n'
        f'<div class="sheet">\n'
        '<div class="masthead"><a class="brand-wm" href="/">MOO<span class="g">:</span>conomy</a>'
        + (f'<div class="mast-tagline">{masthead["tagline"]}</div>' if masthead.get("tagline") else "")
        + '<div class="mast-meta">'
        + f'<span>{mast_meta_line}</span>'
        + (f'<span class="status-badge">{masthead["status"]}</span>' if masthead.get("status") else "")
        + '</div></div>'
        f'{body}\n'
        '</div>\n'
        f'{_SHARE_SCRIPT}\n'
        '</body>\n</html>\n'
    )
    return html
