"""data/history/*.json 파일 목록을 스캔해 data/history/index.json(정렬된
날짜 배열)을 만든다.

home-data.js의 Market Pulse(fetchNearestOnOrBefore/fetchHistoryRange)가
존재하지 않는 휴장일 파일을 추측만으로 반복 요청하며 콘솔 404를 냈던
문제를 막기 위한 색인이다 — 클라이언트는 이 index.json을 먼저 확인하고
실제로 존재하는 날짜만 fetch한다.

이 스크립트는 daily.yml이 data/history/*.json을 web_repo로 복사하는
스텝 바로 뒤에서 실행되어(같은 git commit으로 함께 push) index.json이
실제 파일 목록과 항상 동기화되도록 한다 — 그래서 클라이언트 쪽 fallback은
"index 자체가 없거나 파싱 실패"만 방어하면 된다(파일은 있는데 index가
모른다는 staleness 케이스는 이 배선상 발생하지 않는다).

결정적: 파일시스템에 있는 파일명만 읽는다(네트워크·LLM 호출 없음). 같은
디렉터리 상태면 항상 같은 바이트를 만든다.
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HISTORY_DIR = os.path.join(ROOT, "data", "history")
INDEX_PATH = os.path.join(HISTORY_DIR, "index.json")
_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def build_index(history_dir):
    dates = []
    for fname in os.listdir(history_dir):
        m = _DATE_RE.match(fname)
        if m:
            dates.append(m.group(1))
    dates.sort()
    return {"dates": dates}


def write_index(history_dir=HISTORY_DIR, index_path=INDEX_PATH):
    index = build_index(history_dir)
    tmp_path = index_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp_path, index_path)
    return index


def main():
    index = write_index()
    print(json.dumps({"written": INDEX_PATH, "date_count": len(index["dates"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
