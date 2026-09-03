"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
날짜/시간대 정규화 + 안정적 이벤트 ID 생성.
표준 라이브러리 zoneinfo만 쓴다(pytz 등 신규 의존성 추가 안 함).
"""
import hashlib
import re
from datetime import datetime, timezone as _tz
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def to_utc_iso(dt):
    """timezone-aware datetime -> UTC ISO-8601 문자열('...+00:00' 형식)."""
    if dt.tzinfo is None:
        raise ValueError("to_utc_iso() requires a timezone-aware datetime")
    return dt.astimezone(_tz.utc).isoformat()


def utc_iso_to_kst_date(iso_str):
    """UTC ISO-8601 -> Asia/Seoul 기준 YYYY-MM-DD. 자정 전후 날짜가
    바뀌는 케이스(예: UTC 15:30 -> KST 다음날 00:30)가 여기서 갈린다."""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_tz.utc)
    return dt.astimezone(KST).date().isoformat()


def now_utc_iso():
    return datetime.now(_tz.utc).isoformat()


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text):
    return _SLUG_RE.sub("-", (text or "").strip().lower()).strip("-")


def build_event_id(source_name, country, indicator_key, scheduled_date):
    """소스+국가+지표+날짜 기반 결정적 ID. 같은 이벤트가 하루이틀
    당겨지거나 밀려도(재공표) 이 ID의 안정성을 완전히 보장하진 않는다 —
    그건 merge.py의 매칭 로직(날짜 근접 + 지표명)이 별도로 처리한다.
    이 함수는 "같은 입력이면 항상 같은 ID"만 보장한다(결정적, 무작위 없음)."""
    raw = f"{source_name}:{country}:{_slug(indicator_key)}:{scheduled_date}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{source_name}-{_slug(indicator_key)}-{scheduled_date}-{digest}"


def normalize_title(raw_title):
    return (raw_title or "").strip()
