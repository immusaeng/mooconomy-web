"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
캘린더 파이프라인 CLI. 홈페이지/Daily/Weekly가 공유하는 단일
canonical dataset(data/calendar_events.json)과 소비자별 view
(data/calendar_views/{home,daily,weekly}.json)를 만든다.

사용:
  python scripts/calendar_events/build_calendar.py --fixtures
  python scripts/calendar_events/build_calendar.py --live --sources fred,fmp,bok
  python scripts/calendar_events/build_calendar.py --validate-only
  python scripts/calendar_events/build_calendar.py --dry-run
  python scripts/calendar_events/build_calendar.py --views-only

기본(옵션 없음)은 --live와 동일 — 설정된 API 키가 있는 소스만 실제로
호출되고, 없는 소스는 조용히 건너뛴다(freshness.failedSources에
"missing_api_key"로 남는다).
"""
import argparse
import json
import os
import sys
from datetime import date

# Windows 콘솔의 기본 코드페이지(cp949 등)가 한글/em-dash를 못 만나 죽는
# 걸 막는다 — 로그 출력이 실패해서 파이프라인 전체가 죽는 건 부조리하다.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(__file__))
from config import CalendarConfig, ALL_SOURCE_NAMES  # noqa: E402
from models import make_canonical_dataset  # noqa: E402
from normalize import now_utc_iso  # noqa: E402
from merge import merge_events  # noqa: E402
from importance import classify_importance  # noqa: E402
from validate import validate_canonical, check_future_events_not_suspiciously_empty  # noqa: E402
from selectors import build_home_view, build_daily_view, build_weekly_view  # noqa: E402
from security import mask_secret  # noqa: E402
from sources.base import fetch_safe  # noqa: E402
from sources import fred, fmp, finnhub, bok, ecos, kosis, eia, dart  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CANONICAL_PATH = os.path.join(ROOT, "data", "calendar_events.json")
VIEWS_DIR = os.path.join(ROOT, "data", "calendar_views")
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

# --fixtures는 운영 경로(data/)에 절대 쓰지 않는다 — 샘플이 fallback으로
# 쓰이는 사고를 코드 레벨에서 막는다(스펙: "샘플은 어떤 경우에도
# fallback으로 쓰지 않는다"). 대신 _build_tmp 아래 별도 경로에 쓴다.
FIXTURE_OUT_DIR = os.path.join(ROOT, "_build_tmp", "calendar_fixture_output")

_SOURCE_MODULES = {
    "fred": fred, "fmp": fmp, "finnhub": finnhub, "bok": bok,
    "ecos": ecos, "kosis": kosis, "eia": eia, "dart": dart,
}


def _load_fixture(source_name):
    """원본 API 응답 형태 그대로의 fixture를 읽어, 실제 라이브 경로와
    똑같은 parse() 함수를 태운다 — fixture 모드도 파싱 로직을 검증하게
    되어 "가짜 canonical을 그냥 복사"가 아니다."""
    if source_name == "bok":
        path = os.path.join(FIXTURES_DIR, "bok.sample.html")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return bok.parse_html(f.read())

    if source_name in ("ecos", "kosis"):
        return []  # 이번 라운드엔 이벤트를 만들지 않는 소스(계약만 존재)

    path = os.path.join(FIXTURES_DIR, f"{source_name}.sample.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    mod = _SOURCE_MODULES.get(source_name)
    if mod is None or not hasattr(mod, "parse"):
        return payload.get("events", [])
    return mod.parse(payload)


def run_sources(config, use_fixtures, only_sources=None):
    """반환: (all_events, source_summaries) — source_summaries는
    {name: {"ok": bool, "count": int, "error": str|None}}, API 키
    자체는 절대 포함하지 않는다(mask_secret만 씀)."""
    all_events = []
    summaries = {}
    names = only_sources or config.sources
    for name in names:
        if name not in ALL_SOURCE_NAMES:
            summaries[name] = {"ok": False, "count": 0, "error": "unknown_source"}
            continue
        if use_fixtures:
            events = _load_fixture(name)
            summaries[name] = {"ok": True, "count": len(events), "error": None, "mode": "fixture"}
            all_events.extend(events)
            continue

        mod = _SOURCE_MODULES[name]
        has_key = name == "bok" or config.has_key(name)
        result = fetch_safe(name, mod.fetch, config)
        summaries[name] = {
            "ok": result.ok, "count": len(result.events), "error": result.error,
            "mode": "live", "had_key": has_key,
        }
        all_events.extend(result.events)
    return all_events, summaries


def build(config, use_fixtures, only_sources=None):
    from datetime import timedelta

    raw_events, summaries = run_sources(config, use_fixtures, only_sources)
    pre_filter_count = len(raw_events)

    today = date.today()
    range_from = today - timedelta(days=config.lookback_days)
    range_to = today + timedelta(days=config.lookahead_days)

    # 일부 소스(FRED release/dates 등)는 realtime 창을 우리 예상과 다르게
    # 해석해 훨씬 넓은 기간의 이벤트를 돌려줄 수 있다 — 어떤 소스가 몇
    # 건을 실제로 냈는지와 무관하게, 여기서 요청한 기간 밖 이벤트는
    # canonical에 절대 들어가지 않게 방어적으로 한 번 더 자른다.
    raw_events = [
        e for e in raw_events
        if e.get("scheduledDate") and range_from.isoformat() <= e["scheduledDate"] <= range_to.isoformat()
    ]
    post_filter_count = len(raw_events)

    # 중요도는 규칙 기반으로 다시 계산(원천 값은 신뢰하되 규칙이 최종 판정 — 스펙 §6).
    for ev in raw_events:
        rule_importance = classify_importance(ev["title"])
        if ev.get("importance") in (None, "unknown"):
            ev["importance"] = rule_importance
        if not ev.get("updatedAt"):
            ev["updatedAt"] = now_utc_iso()

    merged = merge_events(raw_events)
    print(f"counts: pre-filter={pre_filter_count} in-range={post_filter_count} after-merge={len(merged)}")

    failed = [name for name, s in summaries.items() if not s["ok"] and s.get("error") != "disabled_by_config"]
    succeeded = [name for name, s in summaries.items() if s["ok"] and s.get("count", 0) > 0]

    if succeeded and not failed:
        status = "fresh"
    elif succeeded and failed:
        status = "partial"
    else:
        status = "stale"

    dataset = make_canonical_dataset(
        generatedAt=now_utc_iso(),
        timezone=config.timezone,
        range_from=range_from.isoformat(),
        range_to=range_to.isoformat(),
        freshness={
            "status": status,
            "lastSuccessfulAt": now_utc_iso() if succeeded else None,
            "failedSources": failed,
        },
        sources=[{"name": n, **{k: v for k, v in s.items() if k != "error" or v}} for n, s in summaries.items()],
        events=merged,
    )
    return dataset, summaries


def _print_summary(summaries):
    for name, s in summaries.items():
        key_note = ""
        if "had_key" in s:
            key_note = " key=set" if s["had_key"] else " key=missing"
        print(f"  {name}: ok={s['ok']} count={s.get('count', 0)}{key_note} error={s.get('error')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", action="store_true", help="fixture 데이터로만 생성(네트워크 호출 없음)")
    parser.add_argument("--live", action="store_true", help="실제 API 호출(기본값과 동일)")
    parser.add_argument("--sources", type=str, default=None, help="쉼표로 구분된 소스만 실행")
    parser.add_argument("--validate-only", action="store_true", help="기존 data/calendar_events.json만 검증")
    parser.add_argument("--dry-run", action="store_true", help="빌드는 하되 파일에 쓰지 않음")
    parser.add_argument("--views-only", action="store_true", help="기존 canonical에서 view만 재생성")
    args = parser.parse_args()

    config = CalendarConfig()

    if args.validate_only:
        if not os.path.exists(CANONICAL_PATH):
            print("no canonical dataset to validate:", CANONICAL_PATH)
            sys.exit(1)
        with open(CANONICAL_PATH, encoding="utf-8") as f:
            dataset = json.load(f)
        issues = validate_canonical(dataset) + check_future_events_not_suspiciously_empty(dataset)
        for issue in issues:
            print("ISSUE:", issue)
        sys.exit(1 if issues else 0)

    if args.views_only:
        if not os.path.exists(CANONICAL_PATH):
            print("no canonical dataset found, cannot build views:", CANONICAL_PATH)
            sys.exit(1)
        with open(CANONICAL_PATH, encoding="utf-8") as f:
            dataset = json.load(f)
        _write_views(dataset, VIEWS_DIR)
        print("views written to", VIEWS_DIR)
        return

    only_sources = [s.strip() for s in args.sources.split(",")] if args.sources else None
    use_fixtures = args.fixtures and not args.live

    dataset, summaries = build(config, use_fixtures, only_sources)
    issues = validate_canonical(dataset)

    print(f"sources ({'fixtures' if use_fixtures else 'live'}):")
    _print_summary(summaries)
    print(f"freshness: {dataset['freshness']}")
    print(f"events: {len(dataset['events'])}")
    if issues:
        print(f"validation issues: {len(issues)}")
        for issue in issues[:20]:
            print("  -", issue)
        if config.strict_mode:
            sys.exit(1)

    if args.dry_run:
        print("dry-run: not writing files")
        return

    if use_fixtures:
        # 샘플/픽스처는 절대 운영 경로(data/)에 쓰지 않는다 — 별도
        # 스크래치 디렉터리에만 쓴다(스펙: "샘플은 어떤 경우에도
        # fallback으로 쓰지 않는다").
        canonical_path = os.path.join(FIXTURE_OUT_DIR, "calendar_events.json")
        views_dir = os.path.join(FIXTURE_OUT_DIR, "calendar_views")
        os.makedirs(FIXTURE_OUT_DIR, exist_ok=True)
        with open(canonical_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print("wrote (fixture-mode, NOT operational data/):", canonical_path)
        _write_views(dataset, views_dir)
        return

    # 라이브 실행에서 이벤트가 0건이면(예: 모든 소스에 키 미설정)
    # 마지막으로 성공한 canonical 파일을 지우지 않는다(스펙 §11).
    if len(dataset["events"]) == 0 and os.path.exists(CANONICAL_PATH):
        print("0 events from live run — preserving existing canonical file, writing views from it instead")
        with open(CANONICAL_PATH, encoding="utf-8") as f:
            existing = json.load(f)
        _write_views(existing, VIEWS_DIR)
        return

    os.makedirs(os.path.dirname(CANONICAL_PATH), exist_ok=True)
    with open(CANONICAL_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print("wrote", CANONICAL_PATH)

    _write_views(dataset, VIEWS_DIR)


def _write_views(dataset, views_dir):
    today = date.today()
    os.makedirs(views_dir, exist_ok=True)
    views = {
        "home.json": build_home_view(dataset, today),
        "daily.json": build_daily_view(dataset, today),
        "weekly.json": build_weekly_view(dataset, today),
    }
    for fn, view in views.items():
        path = os.path.join(views_dir, fn)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(view, f, ensure_ascii=False, indent=2)
        print("wrote", path)


if __name__ == "__main__":
    main()
