"""Daily snapshot persistence guard (read-only input, append-only output).

home.json은 매일 덮어써져 국내 수급/시장온도 근거 등 풍부한 필드가
다음날이면 사라진다. 이 스크립트는 home.json 전체를 복사하지 않고
Stage 3 계약(docs/design/web-residency-platform/archive/03-archive-
data-contract.md)이 공개 가능하다고 정의한 필드만 allowlist로 뽑아
data/archive/daily/{date}.json에 저장한다.

정책(같은 날짜 재실행):
- 기존 파일이 없으면 새로 쓴다.
- 기존 파일이 있고 핵심 내용(content_version/created_at 제외)이
  동일하면 아무것도 하지 않는다(no-op).
- 기존 파일이 있고 내용이 다르면 **원본을 덮어쓰지 않고**
  {date}.v{n}.json으로 별도 버전을 남긴 뒤 CONFLICT를 보고한다.
"""
import copy
import hashlib
import json
import os


def _content_hash(record):
    core = {k: v for k, v in record.items() if k not in ("content_version", "created_at")}
    canonical = json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_daily_archive_record(home):
    """home.json(dict) -> allowlist 추출 결과. 존재하지 않는 값은 지어내지 않고 None."""
    date = home.get("publishDate")
    mt = home.get("marketTemperature") or {}
    kw = home.get("koreaWatch") or {}
    claims = ((home.get("claims") or {}).get("todayClaims") or [])
    question_id = claims[0].get("claimId") if claims else None

    indicators = []
    for ind in home.get("indicators") or []:
        indicators.append({
            "id": ind.get("id"),
            "value": ind.get("value"),
            "change": ind.get("change"),
            "change_unit": ind.get("changeUnit"),
            "direction": ind.get("direction"),
            "as_of": ind.get("asOf"),
            "source": ind.get("source"),
            "status": ind.get("status"),
        })

    korea_watch = []
    for item in kw.get("items") or []:
        korea_watch.append({
            "id": item.get("id"),
            "label": item.get("label"),
            "value": item.get("value"),
            "direction": item.get("direction"),
            "status": item.get("status"),
        })

    record = {
        "issue_date": date,
        "observed_at": home.get("generatedAt"),
        "source_snapshot_id": f"{date}-snapshot",
        "domestic_market_date": home.get("marketDateKr"),
        "us_market_date": home.get("marketDateUs"),
        "indicators": indicators,
        "korea_watch": korea_watch or None,
        "market_temperature": {
            "status": mt.get("label"),
            "score": None,
            "reasons": mt.get("reasons"),
        } if mt.get("label") else None,
        "moo_view": None,
        "question_id": question_id,
        "source_references": sorted({i.get("source") for i in (home.get("indicators") or []) if i.get("source")}),
        "formula_version": "v1",
        "content_version": 1,
    }
    record["created_at"] = home.get("generatedAt")
    return record


def persist(home, archive_dir):
    """반환: (status, path) — status는 WRITTEN|NOOP|CONFLICT_VERSIONED."""
    record = build_daily_archive_record(home)
    date = record["issue_date"]
    if not date:
        raise ValueError("home.json에 publishDate가 없음 — 저장 대상 날짜를 알 수 없음")

    os.makedirs(archive_dir, exist_ok=True)
    path = os.path.join(archive_dir, f"{date}.json")

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
        return "WRITTEN", path

    with open(path, encoding="utf-8") as f:
        existing = json.load(f)

    if _content_hash(existing) == _content_hash(record):
        return "NOOP", path

    # 내용이 다름 — 원본은 절대 덮어쓰지 않고 다음 버전 번호로 별도 저장
    n = 2
    while os.path.exists(os.path.join(archive_dir, f"{date}.v{n}.json")):
        n += 1
    versioned = copy.deepcopy(record)
    versioned["content_version"] = n
    vpath = os.path.join(archive_dir, f"{date}.v{n}.json")
    with open(vpath, "w", encoding="utf-8") as f:
        json.dump(versioned, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    return "CONFLICT_VERSIONED", vpath


if __name__ == "__main__":
    import sys
    home_path = sys.argv[1] if len(sys.argv) > 1 else "data/home.json"
    archive_dir = sys.argv[2] if len(sys.argv) > 2 else "data/archive/daily"
    with open(home_path, encoding="utf-8") as f:
        home = json.load(f)
    status, path = persist(home, archive_dir)
    print(json.dumps({"status": status, "path": path}, ensure_ascii=False))
