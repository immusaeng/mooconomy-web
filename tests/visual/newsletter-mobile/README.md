# tests/visual/newsletter-mobile/

## 폴더 목적
향후 Stitch 모바일웹 프리뷰(`preview/newsletter-mobile/`)의 시각 회귀 테스트
기준선(baseline)과 검증 스크립트를 보관한다.

## 입력 파일
- `preview/newsletter-mobile/`의 구현체(Gate 4 이후)
- `baselines/` — 승인된 스크린샷/DOM 스냅샷(Gate 5 승인 이후 저장)

## 출력 파일
- `baselines/*`(아직 없음 — Gate 5 승인 이후 생성)

## production 여부
아니오.

## 사용자 승인 필요 여부
baseline으로 저장할 스크린샷은 Gate 5(Browser Approval)에서 사용자가 승인한
것만 저장한다.

## 금지 작업
- 승인되지 않은 화면을 baseline으로 저장하는 것
- `preview/newsletter-mobile/`이 구현되기 전에 가짜 baseline을 만드는 것

## 아직 없는 파일 목록
`baselines/` 전체 — Gate 4/5 완료 전까지 비어 있음.

## 향후 기준 viewport
- 320×700
- 360×800
- 375×812
- 390×844
- 412×915
- 430×932

## 향후 검증 항목
- horizontal overflow
- text clipping
- header/logo spacing
- market temperature visibility
- six metrics
- Daily 3 count
- MOO:Q state
- MOO:CHECK state
- link validity
- CTA presence only when approved(연결고리/CTA 재도입이 승인된 경우에만
  존재해야 함 — 승인 없이 나타나면 회귀로 간주)

## 다음 단계
Gate 4(Browser Preview) 구현 이후 이 폴더의 실제 테스트 스크립트를 작성한다.
이번 라운드에서는 README만 작성하고 스크립트는 만들지 않는다.
