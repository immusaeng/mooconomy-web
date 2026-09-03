"""2026-09-03(TASK_ID=OG_SEO_CORRECTION)
v3 OG 카드(1200x630) 4장을 만든다 — 홈/아카이브/캘린더/개별 발행판(공용).
디자인은 v3 확정 팔레트(아이보리 배경 #EFEAD9, 잉크 #1A1613, 골드
#6B4B15)만 쓰고, 시장 숫자·본문 텍스트는 절대 넣지 않는다(카드톡
모바일 미리보기에서도 읽히게 큰 워드마크 + 짧은 문구만).

실행: python3 scripts/og_image/generate_og_images.py
출력: assets/og/og-{home,archive,calendar,issue-v3}.png (1200x630 PNG)

발행판별 동적 OG 이미지는 아직 만들지 않는다 — og-issue-v3.png를
모든 발행판이 공용으로 쓴다. 나중에 발행판별로 분리하고 싶으면 이
스크립트의 _card() 함수에 제목 인자를 추가하면 된다(현재는 미사용).
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIR = os.path.join(ROOT, "assets", "og")

W, H = 1200, 630
BG = "#EFEAD9"
INK = "#1A1613"
GOLD = "#6B4B15"
GOLD_LINE = "#9E6A15"
MUTED = "#6B5B44"

FONT_DIR = "C:/Windows/Fonts"
F_BOLD = os.path.join(FONT_DIR, "malgunbd.ttf")
F_REG = os.path.join(FONT_DIR, "malgun.ttf")


def _font(path, size):
    return ImageFont.truetype(path, size)


def _center_text(draw, cx, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), text, font=font, fill=fill)
    return bbox[3] - bbox[1]


def _card(eyebrow, title, sub, out_name):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 상하 double border (v3 신문톤 시그니처)
    for oy in (48, 52):
        d.line([(80, oy), (W - 80, oy)], fill=INK, width=2)
    for oy in (H - 52, H - 48):
        d.line([(80, oy), (W - 80, oy)], fill=INK, width=2)

    cx = W // 2
    y = 150

    if eyebrow:
        _center_text(d, cx, y, eyebrow, _font(F_BOLD, 26), GOLD)
        y += 56

    # 워드마크: MOO + 골드 콜론 + conomy — 큰 사이즈로 모바일 카톡 카드에서도 읽히게
    wm_font = _font(F_BOLD, 108)
    moo_w = d.textbbox((0, 0), "MOO", font=wm_font)[2]
    colon_w = d.textbbox((0, 0), ":", font=wm_font)[2]
    conomy_w = d.textbbox((0, 0), "conomy", font=wm_font)[2]
    total_w = moo_w + colon_w + conomy_w
    start_x = cx - total_w / 2
    d.text((start_x, y), "MOO", font=wm_font, fill=INK)
    d.text((start_x + moo_w, y), ":", font=wm_font, fill=GOLD_LINE)
    d.text((start_x + moo_w + colon_w, y), "conomy", font=wm_font, fill=INK)
    y += 150

    if title:
        _center_text(d, cx, y, title, _font(F_BOLD, 40), INK)
        y += 62

    if sub:
        _center_text(d, cx, y, sub, _font(F_REG, 30), MUTED)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, out_name)
    img.save(out_path, "PNG")
    print("wrote", out_path)


def main():
    _card("DAILY MOO:CONOMY", "월 Weekly · 화–토 Daily", "오전 7시 · 예측보다 기록과 검증", "og-home-v3.png")
    _card("ARCHIVE", "전체 발행 기록", "매일의 발행판이 쌓여 만드는 긴 흐름", "og-archive-v3.png")
    _card("EVENT CALENDAR", "경제 일정 캘린더", "발표 이후 즉시 해석하고 검증합니다", "og-calendar-v3.png")
    _card("DAILY MOO:CONOMY", "", "예측하지 않고 기록하고 검증합니다", "og-issue-v3.png")


if __name__ == "__main__":
    main()
