"""2026-09-04(TASK_ID=HOMEPAGE_EDITORIAL_IDENTITY_AND_OG_HOOK_RESTORE)
scripts/og/home-editorial-3lines.html(디자인 원본)을 정확히 1200x630
뷰포트로 열어 스크린샷해 assets/og/og-home-editorial-3lines-v4.png를
만든다. LLM/이미지 생성 API 미사용 — Playwright는 그냥 헤드리스
브라우저일 뿐, 디자인은 순수 HTML/CSS다. 폰트는 assets/fonts/og/에
로컬로 이미 번들돼 있어(출처: Google Fonts, OFL 1.1 — 같은 디렉터리의
OFL-*.txt) 이 스크립트는 실행 시점에 네트워크를 쓰지 않는다.

동일 입력(HTML 원본 + 폰트 파일)에서 항상 동일한 출력을 만든다 — 같은
브라우저 엔진의 텍스트 레이아웃이 결정론적이기 때문이다(폰트 힌팅
설정을 바꾸지 않는 한).

문구를 바꾸려면:
1. home-editorial-3lines.html의 텍스트를 수정한다.
2. 새 문구에 없는 새 글자가 필요하면 assets/fonts/og/의 해당 서브셋을
   원본 Fraunces/IBM Plex Sans KR/Noto Serif KR(Google Fonts, OFL)에서
   fontTools.subset으로 다시 잘라내야 한다(이 스크립트가 자동으로 하지
   않는다 — 원본 풀폰트 파일을 저장소에 계속 두지 않기 위한 트레이드
   오프).
3. python scripts/generate_og_home.py 를 다시 실행한다.
"""
import os
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE_HTML = os.path.join(ROOT, "scripts", "og", "home-editorial-3lines.html")
OUT_PATH = os.path.join(ROOT, "assets", "og", "og-home-editorial-3lines-v4.png")
WIDTH, HEIGHT = 1200, 630


def generate():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        page.goto("file:///" + SOURCE_HTML.replace("\\", "/"), wait_until="load")
        page.wait_for_timeout(200)  # 로컬 @font-face 로드 여유
        page.screenshot(path=OUT_PATH, clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT})
        browser.close()
    size = os.path.getsize(OUT_PATH)
    print(f"wrote {OUT_PATH} ({size} bytes)")


if __name__ == "__main__":
    generate()
