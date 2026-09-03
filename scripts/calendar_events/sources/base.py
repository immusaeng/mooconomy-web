"""2026-09-03(TASK_ID=UNIFIED_CALENDAR_DATA_PIPELINE)
소스 어댑터 공통 인터페이스. 각 소스 모듈은 fetch(config) -> list[event
dict] 하나만 구현하면 되고, 여기 fetch_safe()가 예외를 잡아 파이프라인
전체가 한 소스 실패로 죽지 않게 한다(스펙 §9 "일부 소스 실패해도
파이프라인 중단 안 함").

라이브 API 키가 없는 소스는 여기서 이미 (events=[], error="missing_api_key")로
걸러지므로, 개별 어댑터는 "키 없으면 빈 리스트"를 매번 안 써도 된다
(각 어댑터가 그래도 방어적으로 다시 확인은 한다 — 단독 호출 대비)."""
import sys
import traceback

sys.path.insert(0, __file__.rsplit("sources", 1)[0])
from security import strip_query_secrets  # noqa: E402


class SourceResult:
    def __init__(self, source_name, events, error=None, request_url=None):
        self.source_name = source_name
        self.events = events
        self.error = error
        self.request_url = strip_query_secrets(request_url) if request_url else None

    @property
    def ok(self):
        return self.error is None


def fetch_safe(source_name, fetch_fn, config):
    """fetch_fn(config) -> list[event dict]를 호출하고, 무슨 예외가
    나든(네트워크/파싱/타임아웃/HTTP 4xx·5xx) SourceResult로 감싸서
    돌려준다. 예외 메시지에 URL이 들어있으면 키를 지운다."""
    if not config.is_enabled(source_name):
        return SourceResult(source_name, [], error="disabled_by_config")
    try:
        events = fetch_fn(config)
        return SourceResult(source_name, events)
    except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 잡는다
        msg = strip_query_secrets(str(e))
        # 키 미설정은 정상적인 "아직 설정 안 됨" 상태라 스택 트레이스로
        # 로그를 어지럽히지 않는다. 그 외(네트워크/파싱/HTTP 오류)만
        # stderr에 전체 트레이스를 남긴다(운영 로그, 키는 이미 지움).
        if msg != "missing_api_key":
            traceback.print_exc(file=sys.stderr)
        return SourceResult(source_name, [], error=msg)
