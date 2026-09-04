"""2026-09-04(TASK_ID=HOMEPAGE_NARRATIVE_PULSE_VALUES_AND_CALENDAR_KO §9-11)
캘린더 이벤트 제목의 한국어화. LLM/외부 번역 API를 전혀 쓰지 않는다 —
data/calendar_translations.ko.json(고정 용어집, 사람이 검토한 값)만
조회한다. 못 찾으면 원문을 그대로 titleKo에 넣는다(빈 문자열이나
추측 번역으로 채우지 않는다 — untranslated_count로 정직하게 집계).

BOK/DART처럼 원천 자체가 한국어인 소스는 번역할 필요가 없다 —
원문 그대로 titleKo로 쓴다(원문 훼손 없음, 그대로 복사).
"""
import json
import os
import re

_ALREADY_KOREAN_SOURCES = {"BOK", "OpenDART", "DART"}
_HANGUL_RE = re.compile(r"[가-힣]")

GLOSSARY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "calendar_translations.ko.json"
)


def _normalize_key(title):
    return " ".join((title or "").split())


def load_glossary(path=None):
    path = path or GLOSSARY_PATH
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_comment", None)
    return {_normalize_key(k): v for k, v in data.items()}


def is_already_korean(title):
    return bool(_HANGUL_RE.search(title or ""))


def translate_title(original_title, source_name, glossary):
    """(titleKo, translated_bool) 반환. translated_bool=False는 '원문
    유지'를 뜻한다 — 실패가 아니라 정직한 미번역 상태."""
    if source_name in _ALREADY_KOREAN_SOURCES or is_already_korean(original_title):
        return original_title, True
    key = _normalize_key(original_title)
    hit = glossary.get(key)
    if hit:
        return hit, True
    return original_title, False


def apply_ko_titles(events, glossary=None):
    """merge_events() 결과(canonical event dict 리스트)를 그 자리에서
    수정해 각 이벤트에 titleKo를 채운다. 반환값은 커버리지 통계
    (build_calendar.py 로그·검증용) — 원문/날짜/수치는 절대 건드리지
    않는다."""
    glossary = glossary if glossary is not None else load_glossary()
    translated = 0
    untranslated_titles = set()
    for ev in events:
        original = ev.get("originalTitle") or ev.get("title")
        titleKo, ok = translate_title(original, ev.get("sourceName"), glossary)
        ev["titleKo"] = titleKo
        if ok:
            translated += 1
        else:
            untranslated_titles.add(original)
    return {
        "total_events": len(events),
        "translated_count": translated,
        "untranslated_count": len(events) - translated,
        "untranslated_unique_titles": sorted(untranslated_titles),
    }
