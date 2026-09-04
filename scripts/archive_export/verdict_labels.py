"""MOO:Q 판정(verdict) 표시 라벨의 단일 진실 공급원.

claims_store.json의 status 값(hit/miss/neutral/unresolved/invalidated/
error)은 여기서 절대 바꾸지 않는다 — 이 모듈은 그 값을 사용자에게 보여줄
문구로 "변환"만 한다. 데이터 원본에 한글 라벨을 중복 저장하지 않는다.

표준(CEO 지시, TASK_TRACK=HOMEPAGE_DATA_REFRESH_AND_CONSOLE_HYGIENE §C):
  MATCH=적중 / PARTIAL_MATCH=부분 적중 / MISMATCH=불일치 /
  NEUTRAL=중립 / PENDING=판정 대기

home-data.js의 VERDICT_LABEL 객체가 이 파일의 미러다(JS/Python 두 언어라
import는 불가능 — tests/test_verdict_label_consistency.py가 두 값이
어긋나면 실패시켜 드리프트를 막는다). home-data.js를 고칠 때 이 파일도
반드시 함께 고칠 것.
"""

DISPLAY_LABEL = {
    "MATCH": "적중",
    "PARTIAL_MATCH": "부분 적중",
    "MISMATCH": "불일치",
    "NEUTRAL": "중립",
    "PENDING": "판정 대기",
}

# claims_store.json의 raw status -> 표준 카테고리.
# invalidated/error는 "판정할 결과가 없다"는 점에서 unresolved와 동일하게
# PENDING으로 묶는다(export.py의 기존 _VERDICT_MAP과 동일 정책 — 이번에
# home-data.js도 이 정책에 맞춘다. 이전에는 홈 카드만 "무효"/"오류"로
# 따로 표시해 questions 아카이브의 "판단보류"와 어긋났었다).
# PARTIAL_MATCH는 현재 claims_store.json에 실제로 나타나는 raw status가
# 없다 — 예약된 표준 카테고리로 존재만 해둔다(향후 그런 status가 추가되면
# 여기 매핑을 채우면 된다, 지금 임의로 아무 status에나 붙이지 않는다).
STATUS_TO_CATEGORY = {
    "hit": "MATCH",
    "miss": "MISMATCH",
    "neutral": "NEUTRAL",
    "unresolved": "PENDING",
    "invalidated": "PENDING",
    "error": "PENDING",
}


class UnknownVerdictError(ValueError):
    """claims_store.json에 STATUS_TO_CATEGORY가 모르는 status가 나타났을 때.
    임의로 아무 라벨에나 매핑하지 않고 발행 자체를 막기 위한 신호다."""


def label_for_status(status):
    category = STATUS_TO_CATEGORY.get(status)
    if category is None:
        raise UnknownVerdictError(f"UNKNOWN_VERDICT: {status!r}")
    return DISPLAY_LABEL[category]
