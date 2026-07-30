# 02. Skill & Plugin Registry Audit

## 등록 skill(실제 SKILL.md 확인, `daily-briefing/.claude/skills/`)

| SkillName | Purpose | Status | Classification | Owner |
|---|---|---|---|---|
| newsletter-release-gate | 뉴스레터 발송 전 릴리스 게이트 | 기존, 이 세션에서 반복 참고 | CANONICAL | 기존 |
| cross-platform-design-audit | 뉴스레터/웹 디자인 교차 감사 | 기존 | CANONICAL | 기존 |
| moo-change-plan | 계획→승인→diff→커밋 워크플로 강제(Edit/Write 직접 호출 안 함) | **다른 세션 작업, 아직 uncommitted** | SPECIALIZED | 다른 세션 |
| moo-context | 세션 시작 시 두 저장소 상태 요약(읽기 전용) | **다른 세션 작업, 아직 uncommitted** | SPECIALIZED | 다른 세션 |
| moo-diff-review | 커밋 전 diff를 CLAUDE.md 규칙과 대조(읽기 전용, `disable-model-invocation` — 수동 호출만) | **다른 세션 작업, 아직 uncommitted** | SPECIALIZED | 다른 세션 |
| moo-email-verify | 뉴스레터 이메일 템플릿 안전성 4단계 검증(수동 호출만) | **다른 세션 작업, 아직 uncommitted** | SPECIALIZED | 다른 세션 |

이 4개는 실제로 존재하고 잘 구성돼 있음을 SKILL.md 본문 확인으로
검증했다(이름만 보고 판단하지 않음, §요구사항 충족). **다른 활성
세션의 미커밋 작업이라 이번 프로젝트에서 수정·커밋하지 않는다** —
다만 향후 웹 레지던시 프로젝트 전용 skill(예: SEO 검증, 아카이브
데이터 계약 검증)이 필요해지면 이 4개와 이름 충돌 없이 새로 추가
가능함을 확인.

이전 세션 메모에 있던 "email-safe-css/repo-safety" skill 생성 계획은
skill-creator 플러그인 로드 문제로 계속 보류 중이었는데, 실제로는
다른 이름(moo-*)으로 유사한 목적(계획 강제, 컨텍스트 요약, diff 검토,
이메일 검증)의 skill들이 이미 만들어져 있었음 — 중복 생성 불필요,
이번 프로젝트도 이 4개를 그대로 재사용 가능(생성만 완료되면).

## Plugin/Tool 실측 상태

| Tool | Type | 실제 사용 가능 여부 | Fallback |
|---|---|---|---|
| Figma MCP | MCP server | 등록됨(도구 목록에 노출), 이번 프로젝트에서 미사용(웹 코드 직접 작성이 더 빠름) | 해당없음 |
| WebFetch | 내장 도구 | 사용 가능(이전 라운드에서 실제 기사 원문 검증에 사용) | 해당없음 |
| playwright-core(시스템 Chrome 구동) | 저장소 밖 `/tmp` 전용 설치 | **사용 가능, 이번에도 재사용**(렌더 스크린샷·콘솔 에러·HTTP 상태 검증) | 없음, 이미 검증된 유일한 실브라우저 검증 경로 |
| `gh` CLI | 공식 CLI | **인증 안 됨**(`gh auth login` 필요, 플랫폼 권한 분류기 이슈로 반복 확인됨) | `git` 명령 + 비인증 REST API로 대체 |
| Google Search Console / 네이버 서치어드바이저 | 외부 웹 콘솔 | **API/CLI 접근 불가**(계정 인증 필요, 이 세션에 자격증명 없음) | 수동 제출 checklist 작성(아래 04번 문서) |
| Lighthouse | CLI/확장 | 이번 세션에 설치 확인 안 됨 | 실브라우저 렌더+콘솔 에러 체크로 대체(성능 수치 측정은 보류) |
| PIL(Python Imaging Library) | 로컬 설치됨(이전 라운드에서 pixel-diff 검증에 사용) | **사용 가능** | favicon 생성에 실제 사용 |

플랫폼 인증 제한으로 사용 불가능한 도구(`gh`, Search Console, 네이버
서치어드바이저)는 반복 시도하지 않고 즉시 수동 checklist/read-only
대체 경로로 전환했다(§요구사항 그대로 준수).
