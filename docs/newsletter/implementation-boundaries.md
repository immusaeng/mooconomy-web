# 구현 경계(저장소·영역별 책임)

## daily-briefing
- 책임: 실제 이메일 렌더러(`templates/briefing.html`), 데이터 파이프라인
  (`main.py`/`collectors/*`/`site_narrative.py`/`claims.py`), 발송 로직
  (`mailer.py`)
- 금지된 교차 복사: mooconomy-web의 `design/newsletter/stitch/source/*`
  HTML을 `templates/briefing.html`에 직접 붙여넣는 것(ADR-001)
- 이번 워크스페이스 준비 라운드에서: **코드 수정 금지**(확인만 수행)

## mooconomy-web
- 책임: 홈페이지(`index.html`), 대시보드(`markets.html`), Stitch 디자인
  기준·계약 문서(`design/newsletter/`), 향후 브라우저 프리뷰
  (`preview/newsletter-mobile/`)
- 금지된 교차 복사: `preview/newsletter-mobile/`이 완성되기 전에
  `latest.html`이나 `index.html`에서 이를 참조하는 것
- 이번 라운드에서: `design/newsletter/**`, `docs/newsletter/**`,
  `preview/newsletter-mobile/README.md`, `tests/visual/newsletter-mobile/**`
  경로만 신규 생성. `latest.html`/`index.html`/`data/home.json`/
  `data/history/**`/기존 untracked 파일은 변경하지 않음.

## Stitch(외부 디자인 도구, 저장소 아님)
- 책임: 모바일웹 디자인 시안(이미지/HTML) 생성 — 사용자가 직접 운용
- 금지된 교차 복사: Stitch 산출 HTML이 그대로 production 코드(daily-briefing
  또는 mooconomy-web의 실제 배포 페이지)에 들어가는 것 — 반드시 계약 문서를
  거쳐 "의미"만 재구현

## 브라우저 latest.html(mooconomy-web)
- 책임: 최신 발행 뉴스레터의 웹 아카이브(실제 이메일 HTML을 그대로 복사한 것)
- 금지된 교차 복사: Stitch/프리뷰 산출물을 검증 없이 이 파일에 바로 반영하는
  것(Gate 6 백업 절차 없이 진행하는 것)

## 실제 이메일 HTML(Resend로 발송되는 최종본)
- 책임: `mailer.py`가 `css_inline`으로 인라인화한 최종 결과물
- 금지된 교차 복사: 검증(release-gate 스킬)을 거치지 않은 HTML을 발송하는 것,
  세그먼트 이름만으로(ID 검증 없이) 발송 대상을 결정하는 것

## 요약 원칙
각 영역은 자기 책임 범위 안에서만 수정한다. 한 영역의 산출물을 다른 영역에
가져올 때는 항상 "계약 문서(토큰/데이터/카피/컴포넌트 의미)"를 거치지,
파일 자체를 복사하지 않는다.
