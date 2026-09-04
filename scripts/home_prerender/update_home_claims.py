"""data/claims_store.json(canonical, 읽기 전용) -> data/home.json의 "claims"
필드 갱신. home.json의 다른 필드는 건드리지 않는다(claims 키만 교체).

home-data.js의 renderMooCheck()가 소비하는 정확한 형태는
scripts/archive_export/export.py의 build_home_claims()가 정의한다 —
단위·문구를 이 스크립트에서 새로 만들지 않고 그 함수를 그대로 재사용한다.

결정적(deterministic): 현재 시각을 쓰지 않는다. 같은 입력이면 항상 같은
바이트를 만든다(idempotent).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "archive_export"))
from export import build_home_claims  # noqa: E402

CLAIMS_STORE_PATH = os.path.join(ROOT, "data", "claims_store.json")
HOME_JSON_PATH = os.path.join(ROOT, "data", "home.json")


def main():
    with open(CLAIMS_STORE_PATH, encoding="utf-8") as f:
        claims_store = json.load(f)
    with open(HOME_JSON_PATH, encoding="utf-8") as f:
        home = json.load(f)

    home["claims"] = build_home_claims(claims_store)

    with open(HOME_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(home, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"updated {HOME_JSON_PATH}: claims.previousClaims={len(home['claims']['previousClaims'])} "
          f"todayClaims={len(home['claims']['todayClaims'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
