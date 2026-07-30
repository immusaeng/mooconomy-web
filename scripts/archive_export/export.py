"""Archive export layer prototype (read-only adapter).

원천(data/history/*.json, data/claims_store.json)을 전혀 수정하지
않는다 — 읽기만 하고, 03-archive-data-contract.md 계약에 맞는 정규화된
JSON을 별도 출력 디렉터리에 쓴다. 현재 배포 파이프라인 어디에도 연결돼
있지 않은 설계/검증 전용 스크립트다(공개 라우트 없음).

Determinism: 현재 시각을 절대 사용하지 않는다 — 입력 파일에 이미 기록된
시각/날짜만 사용한다. 같은 입력이면 항상 같은 바이트의 출력을 만든다.
"""
import json
import os

_INDICATOR_MAP = {
    "kospi": "kospi", "kosdaq": "kosdaq", "nasdaq": "nasdaq", "sp500": "sp500",
    "usdkrw": "krw_usd", "us10y": "treasury_10y", "wti": "oil", "vix": "vix",
}

_UNIT_MAP = {"usdkrw": "원", "kospi": None, "kosdaq": None, "nasdaq": None, "sp500": None, "us10y": "%p", "wti": "%", "vix": "%"}


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")


def build_market_snapshot(history_record):
    """data/history/{date}.json 1건 -> MarketSnapshot(계약 §B)."""
    date = history_record["date"]
    metrics = {}
    for ind in history_record.get("indicators", []):
        key = _INDICATOR_MAP.get(ind.get("id"))
        if not key:
            continue
        metrics[key] = {
            "value": ind.get("value"),
            "change": ind.get("change"),
            "change_unit": ind.get("displayMode"),
            "direction": ind.get("direction"),
            "status": ind.get("status", "missing"),
        }

    snapshot = {
        "snapshot_id": f"{date}-snapshot",
        "observed_at": date,
        "domestic_market_date": date,
        "us_market_date": None,
        "foreign_flow": None,
        "institution_flow": None,
        "source_references": ["FinanceDataReader"],
        "collection_status": "ok" if metrics else "missing",
        "snapshot_version": history_record.get("schemaVersion", 1),
        "created_at": history_record.get("generatedAt"),
        "updated_at": history_record.get("generatedAt"),
    }
    for key in ("kospi", "kosdaq", "nasdaq", "sp500", "krw_usd", "treasury_10y", "vix", "oil"):
        snapshot[key] = metrics.get(key)
    return snapshot


def build_temperature_observation(history_record, previous_status=None):
    """marketTemperature 값이 없는 날짜는 None을 반환한다(레코드 생성 안 함,
    가짜 관측치 금지) — 호출부가 None이면 건너뛴다."""
    mt = history_record.get("marketTemperature")
    if not mt or not mt.get("label"):
        return None
    date = history_record["date"]
    direction = None
    if previous_status:
        order = ["risk_off", "cautious", "neutral", "risk_on", "strong_risk_on"]
        if mt["label"] in order and previous_status in order:
            diff = order.index(mt["label"]) - order.index(previous_status)
            direction = "improved" if diff > 0 else ("worsened" if diff < 0 else "unchanged")
    return {
        "observation_id": f"{date}-temp",
        "date": date,
        "observed_at": history_record.get("generatedAt"),
        "status": mt["label"],
        "score": None,
        "previous_status": previous_status,
        "direction": direction,
        "reason_codes": None,
        "reason_text": mt.get("reasons"),
        "linked_snapshot_id": f"{date}-snapshot",
        "formula_version": "v1",
        "correction_version": 1,
    }


_VERDICT_MAP = {"hit": "hit", "miss": "miss", "neutral": "neutral", "unresolved": "unresolved",
                "invalidated": "unresolved", "error": "unresolved"}


def build_question_record(claim):
    """claims_store.json의 claim 1건 -> QuestionRecord(계약 §D)."""
    baseline = claim.get("baseline") or {}
    resolution = claim.get("resolution") or {}
    metric_id = claim.get("metricId")
    status = claim.get("status", "unresolved")
    return {
        "question_id": claim["claimId"],
        "question": claim.get("claimText"),
        "issued_at": claim.get("issuedAt"),
        "observation_value": baseline.get("value"),
        "observation_unit": _UNIT_MAP.get(metric_id) or metric_id,
        "observation_as_of": baseline.get("asOf"),
        "expected_direction": claim.get("expectedDirection"),
        "check_due_at": (claim.get("horizon") or {}).get("resolutionAt"),
        "result_value": resolution.get("endValue"),
        "result_unit": resolution.get("changeUnit"),
        "actual_direction": None,
        "verdict": _VERDICT_MAP.get(status, "unresolved"),
        "evidence": resolution.get("explanation"),
        "status": status,
        "method_version": f"{claim.get('verificationType')}-{claim.get('thresholdRuleId')}",
        "locked_at": claim.get("lockedAt"),
        "corrected_at": None,
        "correction_reason": None,
    }


def export_all(data_dir, out_dir):
    """전체 export 실행 — 반환값은 생성 개수 요약(테스트/보고용)."""
    history_dir = os.path.join(data_dir, "history")
    dates = sorted(f[:-5] for f in os.listdir(history_dir) if f.endswith(".json"))

    snapshots, observations = [], []
    prev_status = None
    for date in dates:
        with open(os.path.join(history_dir, f"{date}.json"), encoding="utf-8") as f:
            record = json.load(f)
        snap = build_market_snapshot(record)
        snapshots.append(snap)
        obs = build_temperature_observation(record, previous_status=prev_status)
        if obs:
            observations.append(obs)
            prev_status = obs["status"]

    with open(os.path.join(data_dir, "claims_store.json"), encoding="utf-8") as f:
        claims_store = json.load(f)
    questions = [build_question_record(c) for cid, c in sorted(claims_store.get("claims", {}).items())]

    _write_json(os.path.join(out_dir, "market_snapshots.json"), snapshots)
    _write_json(os.path.join(out_dir, "temperature_observations.json"), observations)
    _write_json(os.path.join(out_dir, "question_records.json"), questions)

    return {"market_snapshots": len(snapshots), "temperature_observations": len(observations), "question_records": len(questions)}


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "scripts/archive_export/dryrun_output"
    summary = export_all(data_dir, out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
