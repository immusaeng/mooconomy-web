# 캘린더 파이프라인 — 운영 가이드

## 실행

```
# 실제 API 호출(기본). 키가 없는 소스는 조용히 건너뛰고 failedSources에 남는다.
python scripts/calendar_events/build_calendar.py --live

# 특정 소스만
python scripts/calendar_events/build_calendar.py --live --sources fred,fmp,bok

# 기존 data/calendar_events.json만 검증(쓰기 없음)
python scripts/calendar_events/build_calendar.py --validate-only

# 빌드는 하되 파일에 쓰지 않음(CI 사전 점검용)
python scripts/calendar_events/build_calendar.py --dry-run

# canonical은 그대로 두고 3개 view만 재생성
python scripts/calendar_events/build_calendar.py --views-only

# 네트워크 없이 fixture로 전체 파이프라인 동작 확인 — data/에는 절대 안 씀
# (_build_tmp/calendar_fixture_output/에만 씀)
python scripts/calendar_events/build_calendar.py --fixtures
```

## 환경변수

`FRED_API_KEY`, `FMP_API_KEY`, `FINNHUB_API_KEY`, `ECOS_API_KEY`,
`KOSIS_API_KEY`, `EIA_API_KEY`, `DART_API_KEY` — 셸 환경변수 또는
GitHub Actions repository secrets로만 주입한다. `.env` 파일을 쓴다면
`.gitignore`에 이미 `.env`/`.env.*`가 있다(커밋되지 않음).

`CALENDAR_SOURCES`(기본 전체), `CALENDAR_LOOKBACK_DAYS`(7),
`CALENDAR_LOOKAHEAD_DAYS`(45), `CALENDAR_TIMEZONE`(Asia/Seoul),
`CALENDAR_STRICT_MODE`(false — true면 검증 이슈가 있을 때 종료 코드 1).

BOK는 API 키가 없다(공개 페이지 스크래핑). 이 세션에는 위 키들이 전혀
설정돼 있지 않았다 — 그래서 지금 저장소의 `data/calendar_events.json`은
"정직하게 비어 있는" 상태(freshness.status=stale, 8개 소스 모두
missing_api_key 또는 재검증 필요)다. 실제 키를 넣으면 다음 `--live`
실행부터 바로 채워진다. 코드 변경은 필요 없다.

## 산출물

- `data/calendar_events.json` — canonical dataset(전 소스 병합).
- `data/calendar_views/{home,daily,weekly}.json` — 소비자별 view.
  home.json은 홈페이지가, daily/weekly.json은 향후 뉴스레터/주간
  리포트가 읽게 될 계약이다(이번 라운드에서는 아직 아무도 daily/weekly
  view를 실제로 소비하지 않는다 — 파일만 준비됨).

## 자동 실행(이번 라운드엔 미배선)

이 저장소에 `.github/workflows/`가 없어서(다른 저장소인
daily-mooconomy가 실제 발행 자동화를 갖고 있을 가능성이 높다) 이번
라운드에서는 GitHub Actions cron을 새로 만들지 않았다. 대신:

1. 로컬/수동으로 `python scripts/calendar_events/build_calendar.py --live`를
   실행하면 그 결과가 바로 운영 데이터가 된다.
2. 매일 자동으로 돌리려면, daily-mooconomy 쪽 발행 파이프라인의 사전
   단계로 이 스크립트를 호출하거나(스펙이 1순위로 권장하는 방식),
   이 저장소에 별도 GitHub Actions 워크플로를 새로 추가해야 한다 —
   둘 다 이번 라운드에서는 실행하지 않았다(별도 승인 필요 항목).

## 실패 시 동작

- 일부 소스만 실패 -> `freshness.status="partial"`, 성공한 소스의
  이벤트는 그대로 살아있다.
- 전체 실패(현재 상태처럼 키가 하나도 없을 때) -> 새 이벤트 0건이면서
  기존에 성공적으로 쓰인 `data/calendar_events.json`이 있으면 그
  파일을 지우지 않고 보존한 채 view만 그걸로 재생성한다. 기존 파일이
  아예 없으면(최초 실행) 정직한 빈 canonical을 쓴다 — 이게 지금
  저장소의 실제 상태다.

## 보안 점검

배포 전에 항상:

```
python -c "
import sys; sys.path.insert(0, 'scripts/calendar_events')
from security import scan_repo_for_secrets
findings = scan_repo_for_secrets('.')
print(len(findings), 'findings')
for f in findings: print(f)
"
```

실제 키 값이 포함된 findings가 하나라도 있으면 커밋하지 않는다 —
해당 키를 즉시 회전(재발급)하고 새 키를 secrets로만 등록한다.
