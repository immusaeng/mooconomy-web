# 뉴스레터 모바일웹 디자인 계약(Stitch 단계, 초안)

상태: **초안 — 사용자 승인 대기.** 아래 섹션 후보·색상 토큰은 Stitch 디자인
단계의 출발점으로 이번 요청에서 지정된 값을 그대로 기록한 것이며, 실제
구현·확정은 Gate 2 이후(사용자가 Stitch 자료를 제공한 뒤)에 진행한다.

## ⚠️ 색상 토큰: Stitch Candidate와 Legacy Email Baseline은 서로 다른 두 팔레트다

두 팔레트를 하나로 섞어 쓰지 않는다 — 이름 자체를 분리해 어느 값이 어느
맥락의 것인지 항상 명확히 한다.

**Stitch Candidate**(이번 Stitch 모바일웹 디자인 단계의 신규 후보값 — 아직
승인 전):
- Brand Navy: `#001026`
- Navy Container: `#0B2545`
- Brand Gold Candidate: `#FDC003`
- Background: `#F8F9FA`
- Card: `#FFFFFF`
- Surface Low: `#F3F4F5`

**Legacy Email Baseline**(daily-briefing `templates/briefing.html`이 실제로
쓰는 현재 프로덕션 이메일 값 — 코드에서 직접 확인):
- Legacy Email Navy: `#0B2545`
- Legacy Email Gold: `#F5B301`

명시 사항:
- `#FDC003`은 **Stitch 신규 디자인 후보값**이다 — 아직 어디에도 적용되지 않았다.
- `#F5B301`은 **현재 롤백 이메일 기준값**이다(daily-briefing HEAD `a60fa52`,
  `templates/briefing.html`에서 실제 사용 중).
- 이번 문서 작업에서 **production CSS나 이메일 색상을 변경하지 않는다.**
- **Stitch 화면이 승인되기 전까지 두 Gold 값(`#FDC003`/`#F5B301`)을 자동으로
  통합하지 않는다** — Navy 값(`#001026`/`#0B2545`)도 동일하게 자동 통합 금지.
- 우연히 일치하는 값도 있다(Navy Container `#0B2545` == Legacy Email Navy
  `#0B2545`) — 이것이 "의도적으로 같다"는 뜻인지 "Stitch가 기존 값을 그대로
  이어받은 것"인지는 확인되지 않았으므로 추정하지 않는다.

## 기준 화면
- 기준: 모바일 브라우저웹 **390px**
- 축소 검증: **320px**
- 추가 검증: 360px, 375px, 412px, 430px

## 브랜드
- 표기: **MOO:conomy**(daily-briefing `test_brand_consistency.py`가 이미
  강제하는 표기와 동일 — 이 부분은 실제 코드와 일치 확인됨)
- 공식 황소 심볼 사용 원칙 유지(현재 이메일이 쓰는
  `https://raw.githubusercontent.com/immusaeng/mooconomy-assets/main/bull-gold.png`
  와 동일 자산을 쓸지, Stitch 전용 자산을 새로 쓸지는 미확정)

## 색상 토큰
위 "Stitch Candidate" 팔레트를 디자인 출발점으로 쓴다(Legacy Email Baseline과
혼용 금지, 위 섹션 참고).
- 상승/하락 색상은 Gold와 분리(현재 이메일은 up-red `#d32f2f`/down-blue
  `#1565c0` — 이 값을 그대로 가져올지는 미확정, Stitch 후보 확인 후 결정)

## 타이포그래피
- Pretendard(본문) + Inter(영문 라벨) + 시스템 fallback
- 숫자는 `tabular-nums` 사용 원칙(현재 이메일에는 이 속성이 없음 — 신규 적용 후보)

## 형태
- border-radius: 10px / 12px / 16px
- 최소 터치 영역: 44px

## 금지 사항(모바일웹 프리뷰 단계 공통)
- 수평 스크롤 금지
- 텍스트 잘림 금지
- 고정 390px `body`(반응형이어야 함, 이메일과 달리 브라우저는 뷰포트 대응 가능)
- Tailwind CDN 금지
- Material Symbols 금지
- placeholder 링크 금지(`href="#"` 등)
- fake data 금지

## 섹션 후보(디자인 후보 구조일 뿐, 자동 확정 아님)

1. Header
2. 발행일
3. 오늘의 시장 온도
4. 핵심 지표 6개
5. 오늘의 3줄
6. MOO:Q
7. MOO:CHECK
8. 오늘의 연결고리
9. 해석
10. 반대 시나리오
11. 일정
12. 뉴스
13. 리스크
14. 구독/공유 CTA
15. PART 구분
16. Footer

**중요**: 위 목록은 디자인 후보 구조다. 현재 롤백된 뉴스레터(daily-briefing
HEAD `a60fa52`)에는 8(연결고리)·10(반대 시나리오)·14(CTA)가 렌더링되지
않는다(2026-07-22 롤백, ADR-001). 이 문서가 후보로 나열한다고 해서 자동으로
복원되는 것이 아니다 — 실제 신규 디자인 포함 여부는 사용자 승인 후
`newsletter-content-inventory.md`에서 섹션별로 확정한다.
