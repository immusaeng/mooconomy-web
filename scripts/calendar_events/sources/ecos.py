"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
ECOS(한국은행 경제통계시스템) — 일정 자체를 제공한다고 가정하지 않는다
(스펙 §3). 이번 라운드에서는 BOK가 만든 scheduled 이벤트에 실제값을
보강하는 역할까지는 merge 단계에 연결하지 않았다 — fetch()는 새
이벤트를 만들지 않고 빈 리스트를 반환한다(정직하게 미구현으로 표시).

향후: BOK 이벤트의 title에서 통계 코드로 매핑할 사전을 만들고,
ECOS StatisticSearch API(https://ecos.bok.or.kr/api/StatisticSearch/...)
로 실제값을 조회해 merge.py의 actual 필드를 보강하도록 확장한다.
"""


def fetch(config):
    api_key = config.get_api_key("ecos")
    if not api_key:
        raise RuntimeError("missing_api_key")
    # TODO: BOK 이벤트 title -> ECOS 통계코드 매핑 후 실제값 조회.
    # 지금은 "일정 이벤트를 새로 만들지 않는다"는 계약만 지킨다.
    return []
