"""
מייצר אייקון פשוט לאפליקציה (כדור לוטו כחול עם מספר) לשימוש כ-apple-touch-icon.
"""
import base64
import io
import os

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(__file__)
SIZE = 1024
BLUE = (42, 120, 214)
WHITE = (255, 255, 255)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_icon():
    img = Image.new("RGB", (SIZE, SIZE), BLUE)
    draw = ImageDraw.Draw(img)

    circle_r = int(SIZE * 0.34)
    cx, cy = SIZE // 2, SIZE // 2
    draw.ellipse(
        [cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r],
        fill=WHITE,
    )

    font = load_font(int(SIZE * 0.34))
    text = "7"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), text, fill=BLUE, font=font)

    return img


def main():
    img = make_icon()
    out_1024 = os.path.join(BASE_DIR, "icon-1024.png")
    img.save(out_1024)

    icon_180 = img.resize((180, 180), Image.LANCZOS)
    out_180 = os.path.join(BASE_DIR, "icon-180.png")
    icon_180.save(out_180)

    buf = io.BytesIO()
    icon_180.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    out_txt = os.path.join(BASE_DIR, "icon-180.base64.txt")
    with open(out_txt, "w") as f:
        f.write(b64)

    print(f"נוצר: {out_1024}")
    print(f"נוצר: {out_180}")
    print(f"נוצר base64 ({len(b64)} תווים): {out_txt}")


if __name__ == "__main__":
    main()
