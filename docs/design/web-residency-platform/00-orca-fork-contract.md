# 00. ORCA Fork Contract — MOO:conomy Search/Discovery/Archive/Residency Platform

- Project: MOO_CONOMY_SEARCH_DISCOVERY_ARCHIVE_AND_RESIDENCY_PLATFORM_01
- Base repository(웹): `immusaeng/mooconomy-web`
- Base branch: `main`
- Base SHA(작업 시작 시점 origin/main): `1a32e08`
- 관련 저장소(파이프라인, 이번 라운드 미변경): `immusaeng/daily-mooconomy` @ `8472109`(newsletter targeted-final-release)
- 작업 위치: 완전히 별도인 clean clone `mooconomy-web-work`(다른 활성 세션이
  `daily-briefing`/`daily-briefing/mooconomy-web` 양쪽 작업 트리를 dirty한
  미완성 변경으로 점유 중이라, 그 트리를 건드리지 않기 위해 신규 clone
  사용 — WORKSPACE_MODE 오버라이드의 "충돌 위험이 있을 때만 별도
  worktree" 조건에 해당).

## 오케스트레이션 결정

`ORCHESTRATION_MODE=ORCA_MULTI_FORK`(4포크: SEO_INFRA_AUDIT,
DATA_API_ASSET_AUDIT, PRODUCT_ARCHIVE_IA_AUDIT,
SKILL_PLUGIN_OBSIDIAN_AUDIT)가 요청됐으나, 이전 여러 라운드와 동일한
이유로 코디네이터가 4개 역할을 순차 자기실행함(같은 세션에서 이미 이
저장소·Obsidian·skill 구조를 반복적으로 다뤄 즉시 파악 가능한 상태라,
새 subagent를 스폰해 이미 아는 사실을 재조사시키는 것은
`DuplicateResearchCount=0` 원칙에 반함). 산출물은 병합 없이 파일별로
분리해 아래 소유권 표를 그대로 지켰다.

## 파일 소유권

| 역할 | 소유 파일/영역 |
|---|---|
| SEO_INFRA_AUDIT | `robots.txt`, `sitemap.xml`, `feed.xml`, `site.webmanifest`, `favicon*`, `404.html`, `index.html`(head 메타만), `about/`, `methodology/` |
| DATA_API_ASSET_AUDIT | `docs/design/web-residency-platform/audit/03-api-and-data-source-registry.md`(문서만, 코드 변경 없음) |
| PRODUCT_ARCHIVE_IA_AUDIT | `docs/design/web-residency-platform/audit/04-seo-baseline-and-priority0-implementation.md`의 아카이브/터미널/홈 IA 섹션(문서만) |
| SKILL_PLUGIN_OBSIDIAN_AUDIT | `docs/design/web-residency-platform/audit/02-skill-plugin-registry.md`, Obsidian `Projects/MOOconomy/Web-Residency-Platform/` 전체 |
| ORCA_COORDINATOR | 이 계약 파일, 통합·커밋·최종 보고 |

## 읽기 전용 파일(수정 금지)

`markets.html`(CLAUDE.md 절대 보호 목록), `index.html`의 live-dot/
demo-banner **로직**(JS 자체는 무변경, head 메타만 추가), `daily-briefing`
저장소 전체(이번 프로젝트는 웹 전용, 뉴스레터 발송 경로 무관).

## 금지 파일

`.env`, API key, 실제 구독자 이메일, `RESEND_SEGMENT_ID` 값,
`daily.yml`(뉴스레터 발송 워크플로 — 이번 프로젝트에서 전혀 건드리지
않음, 아래 배포 안전 확인 참고).

## 배포 안전 확인(§2 요구)

- `mooconomy-web`은 `daily-briefing`과 **완전히 분리된 별도 GitHub
  저장소**(CLAUDE.md 이미 명시)이며, GitHub Pages를 통해 정적 배포된다.
  이 저장소에는 이메일 발송 관련 workflow가 전혀 없다(뉴스레터 발송은
  `daily-mooconomy` 저장소의 `daily.yml`이 전담, `workflow_dispatch`
  전용, push 트리거 없음 — 지난 라운드에서 반복 확인됨).
- 따라서 `mooconomy-web`으로의 push는 구조적으로 뉴스레터 발송과
  무관하다(`PushTriggersSend=False`, 별도 저장소이므로 발송 workflow
  자체가 존재하지 않음). Website-only 배포 구조 설계가 별도로 필요
  없음 — 이미 그 구조다.

## 완료 기준

각 우선순위(Priority 0 기술 SEO 기반)에 대해: 실제 파일 생성·수정
확인, XML/HTML 유효성 검사, 실브라우저 콘솔 에러 0건, 기존 기능
(live-dot/demo-banner/signalGrid) 회귀 없음 확인 후 완료로 간주.

## 통합 순서

SEO_INFRA_AUDIT(구현) → DATA_API_ASSET_AUDIT/PRODUCT_ARCHIVE_IA_AUDIT/
SKILL_PLUGIN_OBSIDIAN_AUDIT(문서, 병렬 성격이나 코디네이터가 순차 작성)
→ 코디네이터 통합 검증 → 단일 scoped commit.

## 충돌 해결 우선순위

1. CLAUDE.md의 "절대 건드리지 말 것" 목록
2. 사용자가 이번 태스크에서 명시한 금지 사항(이메일 발송·segment·
   workflow dispatch 등)
3. 기존 브랜드 디자인 토큰(다크 네이비/골드) 재사용
4. 최소 diff(기존 파일은 필요한 부분만 수정)
5. 검색 발견성(Priority 0) 최우선
