"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
KOSIS(국가통계포털) — 공표 일정 전용 API가 확인되지 않아(스펙 §3),
이번 라운드에서는 실제값 enrichment 자리만 만들고 새 이벤트를 만들지
않는다(ECOS와 동일한 이유).

향후: KOSIS Open API(stat_data.do)로 이미 스케줄된 이벤트의 actual을
채우는 adapter로 확장. 공식 공표 일정 소스가 별도로 확인되면 그때
이 함수가 이벤트를 만들도록 바꾼다.
"""


def fetch(config):
    api_key = config.get_api_key("kosis")
    if not api_key:
        raise RuntimeError("missing_api_key")
    # TODO: 실제값 enrichment만 — 일정 이벤트는 만들지 않는다.
    return []
