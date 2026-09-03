"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
API 키가 로그·예외 메시지·커밋에 새지 않게 하는 유틸.
"""
import re

_ENV_KEY_NAMES = [
    "FRED_API_KEY", "FMP_API_KEY", "FINNHUB_API_KEY", "ECOS_API_KEY",
    "KOSIS_API_KEY", "EIA_API_KEY", "DART_API_KEY",
]

# 흔한 상용 API 키 형태(대략) — 오탐이 있어도 "의심 라인 보고"용이라 괜찮다.
_SECRET_LIKE_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?"),
]


def mask_secret(value):
    """로그에 쓸 수 있는 마스킹된 형태. 앞 2글자·뒤 2글자만 남긴다."""
    if not value:
        return "(unset)"
    s = str(value)
    if len(s) <= 6:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def strip_query_secrets(url):
    """URL 쿼리스트링에서 key/token/secret류 파라미터 값을 제거한 뒤
    반환한다 — 요청 URL을 로그에 남길 때 이 함수를 거친 결과만 쓴다."""
    if not url:
        return url
    return re.sub(
        r"(?i)([?&](?:api[_-]?key|apikey|token|secret|key)=)[^&]+",
        r"\1***",
        url,
    )


def scan_text_for_secrets(text, known_secrets=()):
    """텍스트(파일 내용)에서 (a) 알려진 실제 시크릿 값이 그대로 들어있는지,
    (b) 시크릿처럼 생긴 하드코딩 패턴이 있는지 확인한다. 실제 값은
    반환하지 않고, 몇 번째 줄에서 걸렸는지만 돌려준다."""
    hits = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        for secret in known_secrets:
            if secret and len(secret) >= 8 and secret in line:
                hits.append((i, "known_secret_value"))
        for pat in _SECRET_LIKE_PATTERNS:
            if pat.search(line):
                hits.append((i, "secret_like_pattern"))
    return hits


def scan_repo_for_secrets(root, known_secrets=(), extensions=(".py", ".js", ".json", ".html", ".md", ".yml", ".yaml")):
    """저장소를 훑어 known_secrets(실제 env 값들) 노출과 secret-like 패턴을
    찾는다. .git/, node_modules/, __pycache__/는 건너뛴다. 결과는
    [(relative_path, line_no, reason), ...] — 값 자체는 절대 포함하지 않는다."""
    import os

    skip_dirs = {".git", "node_modules", "__pycache__", "_build_tmp"}
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fn in filenames:
            if not fn.endswith(extensions):
                continue
            full = os.path.join(dirpath, fn)
            try:
                with open(full, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            for line_no, reason in scan_text_for_secrets(text, known_secrets):
                rel = os.path.relpath(full, root)
                findings.append((rel, line_no, reason))
    return findings
