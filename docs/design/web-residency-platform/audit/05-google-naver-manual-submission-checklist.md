# 05. Google/Naver 수동 제출 체크리스트

이 세션에는 Google Search Console/네이버 서치어드바이저에 대한
API·CLI 인증 권한이 없어 자동 제출이 불가능하다. 배포 후 사용자가
직접 아래 순서로 진행하면 된다(반복 재시도·우회 로그인 없음).

## Google Search Console

- [ ] 속성이 `mooconomy.co.kr`(도메인 속성 또는 URL 접두어)로 등록돼
      있는지 확인
- [ ] Sitemaps 메뉴에서 `sitemap.xml` 제출(URL: `https://mooconomy.co.kr/sitemap.xml`)
- [ ] URL 검사 도구로 다음 URL 각각 수집 요청:
  - `https://mooconomy.co.kr/`
  - `https://mooconomy.co.kr/about/`
  - `https://mooconomy.co.kr/methodology/`
- [ ] 구조화 데이터 보고서에서 WebSite/Organization/AboutPage/
      BreadcrumbList 오류 없는지 확인
- [ ] 모바일 사용성 보고서 확인
- [ ] 페이지 색인 생성 보고서에서 `privacy.html`이 "제외됨(noindex
      태그)"로 정확히 분류되는지 확인(더 이상 sitemap에 없으므로
      혼란 없어야 함)

## 네이버 서치어드바이저

- [ ] 사이트 소유 확인 유지(이미 `naver247522d1c5ebe86602c18a402c47be06.html`
      존재 확인됨)
- [ ] robots.txt 확인 메뉴에서 정상 수집 허용 확인
- [ ] 사이트맵 제출 메뉴에서 `sitemap.xml` 제출/갱신
- [ ] RSS 제출 메뉴에서 `feed.xml` 제출
- [ ] 요청 확인 메뉴로 루트·`/about/`·`/methodology/` 수집 요청
- [ ] 사이트 진단 메뉴에서 title/description 중복 경고 없는지 확인
