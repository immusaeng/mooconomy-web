"""2026-09-03(TASK_ID=HOMEPAGE_VISIBLE_ACTIVATION_FIX)
로컬 CSS/JS 링크에 캐시 무효화용 버전 쿼리(?v={short_sha})를 붙인다.
canonical/OG URL은 절대 건드리지 않는다(그쪽은 캐시 버스팅 쿼리가
붙으면 안 된다 - 별도 정규식으로, 저 두 정규식이 겹치지 않는다).

현재 HEAD의 short SHA를 쓴다(이번에 만들 커밋 자신의 SHA는 커밋하기
전에는 알 수 없으므로, "직전 커밋" SHA를 쓴다 - 매 배포마다 값이
바뀌는 게 목적이라 캐시 무효화 효과는 동일하다). ASSET_VERSION
파일에도 같은 값을 써 둔다 - build_archive_pages.py가 아카이브 페이지를
생성할 때마다 이 파일을 읽어 같은 버전을 자동으로 반영한다(수동으로
매번 SHA를 다시 입력할 필요 없음).

실행: python scripts/deploy/stamp_asset_versions.py
"""
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ASSET_VERSION_PATH = os.path.join(ROOT, "ASSET_VERSION")

# 버전 쿼리를 붙일 로컬 자산 파일명(경로 접두어는 무엇이든 상관없음).
_ASSET_NAMES = [
    "styles.css", "shared-shell.css", "archive.css", "calendar.css",
    "app.js", "home-data.js", "calendar-data.js",
]

_TARGET_HTML_FILES = ["index.html", os.path.join("calendar", "index.html")]


def get_short_sha():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "dev"


def _stamp_html(text, version):
    names_alt = "|".join(re.escape(n) for n in _ASSET_NAMES)
    # href="...styles.css" 또는 href="...styles.css?v=abc123" 모두 매치해서
    # 항상 현재 버전으로 덮어쓴다(멱등 - 이미 붙어 있어도 최신 값으로 갱신).
    pattern = re.compile(
        rf'((?:href|src)=")([^"?]*(?:{names_alt}))(?:\?v=[A-Za-z0-9]+)?(")'
    )
    return pattern.sub(rf"\g<1>\g<2>?v={version}\g<3>", text)


def main():
    version = get_short_sha()
    with open(ASSET_VERSION_PATH, "w", encoding="utf-8") as f:
        f.write(version + "\n")
    print(f"ASSET_VERSION = {version}")

    for rel in _TARGET_HTML_FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            html = f.read()
        new_html = _stamp_html(html, version)
        matched = bool(re.search(
            r'(?:href|src)="[^"?]*(?:' + "|".join(re.escape(n) for n in _ASSET_NAMES) + r')',
            html,
        ))
        if not matched:
            print(f"{rel}: WARNING - no matching asset links found at all")
        elif new_html != html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"stamped {rel} -> v={version}")
        else:
            print(f"{rel}: already at v={version}, no change needed")


if __name__ == "__main__":
    main()
