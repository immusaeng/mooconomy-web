# design/newsletter/audits/

## 폴더 목적
`/cross-platform-design-audit` 스킬(daily-briefing 저장소
`.claude/skills/cross-platform-design-audit/SKILL.md`) 실행 결과나, 수동으로
수행한 디자인 일관성 감사 결과를 시간순으로 보관한다.

## 입력 파일
없음(감사는 다른 폴더의 자료를 대상으로 수행되고, 결과만 여기 저장됨).

## 출력 파일
감사 실행 시 생성되는 리포트(예: `2026-MM-DD-audit.md`) — 아직 없음.

## production 여부
아니오.

## 사용자 승인 필요 여부
감사 실행 자체는 읽기 전용이라 별도 승인 없이도 가능하나, 감사 결과에 따른
후속 조치(디자인 변경)는 승인이 필요하다.

## 금지 작업
- 실행하지 않은 감사의 결과를 미리 작성해두는 것
- 감사 리포트를 근거로 production 파일을 자동으로 고치는 것

## 아직 없는 파일 목록
전체 — 이번 라운드에서는 감사를 실행하지 않았다(Gate 1 준비 단계라 감사
대상 Stitch 자료 자체가 아직 없음).

## 다음 단계
Gate 2 이후, Stitch 후보 이미지/HTML이 확보되면 `/cross-platform-design-audit`
스킬을 실행해 첫 리포트를 이 폴더에 추가한다.
