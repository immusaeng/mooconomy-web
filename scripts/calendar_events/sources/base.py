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
        # requests.HTTPError 등은 str(e)에 요청 URL(쿼리스트링의 키 포함)을
        # 그대로 담는다 - traceback.print_exc()는 "원본" 예외 객체를 다시
        # str()해서 그대로 찍으므로, 그걸 그대로 쓰면 위에서 막 지운 키가
        # 트레이스백에는 그대로 남아 로그로 샌다. 반드시 이미 마스킹된
        # msg/타입만 stderr에 남긴다 - 원본 예외 객체나 traceback.print_exc()를
        # 직접 부르지 않는다.
        if msg != "missing_api_key":
            tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
            for line in tb_lines:
                print(strip_query_secrets(line), file=sys.stderr, end="")
        return SourceResult(source_name, [], error=msg)
