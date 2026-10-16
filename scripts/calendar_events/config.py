"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
환경변수 로딩 + 기본값. API 키는 여기서 한 번만 읽고, 이 모듈 밖으로는
값 그대로 로그/문자열에 넣지 않는다(security.py의 mask_secret 참고).
"""
import json
import os

# fmp/finnhub는 플랜 403으로 비활성(2026-10-16) — 소스 모듈은 남기고 기본 실행에서만 뺀다.
DEFAULT_SOURCES = "fred,bok,ecos,kosis,eia,dart"
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_LOOKAHEAD_DAYS = 45
DEFAULT_TIMEZONE = "Asia/Seoul"

ALL_SOURCE_NAMES = ["fred", "fmp", "finnhub", "bok", "ecos", "kosis", "eia", "dart"]

# freshness.sources에 남기는 고정 상태. 실행 대상이 아니거나 미구현인 소스를
# ok=True count=0(정상처럼 보임) 대신 명시한다.
DISABLED_PLAN_403 = ("fmp", "finnhub")
NOT_IMPLEMENTED = ("ecos", "kosis")

FRED_RELEASES_PATH = os.path.join(os.path.dirname(__file__), "fred_releases.json")

# 소스별 env var 키 이름 매핑 — 실제 값은 get_api_key()로만 읽는다.
_KEY_ENV = {
    "fred": "FRED_API_KEY",
    "fmp": "FMP_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
    "ecos": "ECOS_API_KEY",
    "kosis": "KOSIS_API_KEY",
    "eia": "EIA_API_KEY",
    "dart": "DART_API_KEY",
    # bok(한국은행 공표 일정 페이지)는 API 키가 없다 — 공개 페이지 스크래핑.
}


class CalendarConfig:
    def __init__(self, env=None):
        env = env if env is not None else os.environ
        sources_raw = env.get("CALENDAR_SOURCES", DEFAULT_SOURCES)
        self.sources = [s.strip() for s in sources_raw.split(",") if s.strip()]
        self.lookback_days = int(env.get("CALENDAR_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS))
        self.lookahead_days = int(env.get("CALENDAR_LOOKAHEAD_DAYS", DEFAULT_LOOKAHEAD_DAYS))
        self.timezone = env.get("CALENDAR_TIMEZONE", DEFAULT_TIMEZONE)
        self.strict_mode = env.get("CALENDAR_STRICT_MODE", "false").strip().lower() == "true"
        # 롤백 플래그: "0"이면 허용 목록 없이 현행(전체 release) 동작.
        self.fred_allowlist_enabled = env.get("CAL_FRED_ALLOWLIST_ENABLED", "1").strip() != "0"
        with open(FRED_RELEASES_PATH, encoding="utf-8") as f:
            self.fred_release_ids = set(json.load(f)["releases"])
        self._env = env

    def get_api_key(self, source_name):
        """소스명 -> API 키 문자열 또는 None(미설정). 이 함수의 반환값을
        직접 print/log하지 않는다 — security.mask_secret()을 거칠 것."""
        env_name = _KEY_ENV.get(source_name)
        if not env_name:
            return None
        val = self._env.get(env_name)
        return val.strip() if val else None

    def has_key(self, source_name):
        return bool(self.get_api_key(source_name))

    def is_enabled(self, source_name):
        return source_name in self.sources
