# design/newsletter/stitch/

## 폴더 목적
사용자가 Stitch로 생성한 뉴스레터 모바일웹 디자인 원본(이미지·HTML·메타데이터)을
그대로 보관한다. Claude Code가 생성하지 않는다 — 사용자가 제공하는 자료 전용
보관소다.

## 입력 파일
- `source/` — Stitch가 내보낸 원본 HTML/CSS(있다면)
- `screenshots/390/` — 390px 기준 화면 스크린샷
- `screenshots/320/` — 320px 축소 검증 화면 스크린샷
- `screenshots/components/` — 개별 컴포넌트 단위 스크린샷(시장 온도, Daily 3 등)
- `metadata/` — 위 자료에 대한 설명(어떤 게 승인본인지, 생성 일자 등)

## 출력 파일
없음(이 폴더는 순수 입력 보관소).

## production 여부
아니오.

## 사용자 승인 필요 여부
예 — 이 폴더에 무엇을 "기준"으로 채택할지는 전부 사용자 결정 사항이다.

## 금지 작업
- 실제 Stitch 파일이 없는 상태에서 가짜 이미지, 샘플 HTML, 임의 데이터,
  placeholder JSON을 생성하는 것
- `source/`의 HTML을 이메일 템플릿에 직접 복사하는 것(ADR-001,
  `../contracts/email-translation-boundaries.md` 참고)

## 아직 없는 파일 목록
`source/`, `screenshots/390/`, `screenshots/320/`, `screenshots/components/`,
`metadata/` 전부 비어 있음 — 사용자가 Stitch 자료를 제공할 때까지 대기.

## 다음 단계
Gate 2(Stitch 390 Candidate) — 사용자가 Stitch에서 390px 후보를 생성해 이
폴더에 제공하면 시작한다. 이번 세션에서는 시작하지 않는다.
