"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
중요도는 규칙 기반으로만 정한다 — LLM 호출 없음(LLM_CALL_COUNT=0 유지).
"""

_HIGH_KEYWORDS = [
    "기준금리", "금융통화위원회", "fomc", "federal funds", "cpi", "consumer price",
    "ppi", "producer price", "고용보고서", "비농업", "nonfarm payroll", "실업률",
    "unemployment rate", "gdp", "국내총생산", "핵심 물가", "core pce", "core cpi",
    "금리 결정", "rate decision", "policy rate",
]
_MEDIUM_KEYWORDS = [
    "산업생산", "industrial production", "소매판매", "retail sales", "무역수지",
    "trade balance", "pmi", "소비심리", "consumer confidence", "consumer sentiment",
    "원유재고", "crude oil inventor", "재고", "housing", "주택",
]


def classify_importance(title, source_importance=None):
    """제목 키워드로 high/medium/low를 규칙 기반 판정한다.
    source_importance(원천 API가 준 값)가 있으면 함께 반환해 검증에
    쓸 수 있게 하되, 최종 판정은 이 함수의 규칙이 우선한다(스펙 §6)."""
    t = (title or "").lower()
    if any(k in t for k in _HIGH_KEYWORDS):
        rule_result = "high"
    elif any(k in t for k in _MEDIUM_KEYWORDS):
        rule_result = "medium"
    elif t:
        rule_result = "low"
    else:
        rule_result = "unknown"
    return rule_result


def cross_check_importance(title, source_importance):
    """규칙 판정과 원천 API 중요도가 크게 어긋나면(예: 원천은 low인데
    규칙은 high) 참고용 경고 문자열을 돌려준다. None이면 어긋남 없음."""
    rule_result = classify_importance(title)
    if not source_importance or source_importance == "unknown":
        return None
    if rule_result != source_importance:
        return f"rule={rule_result} source={source_importance}"
    return None
