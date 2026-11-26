"""Draw CafeMice's icon (an original drawing): a cheese wedge on a dark tile.

    python tools/cafe_exe/make_icon.py    # -> tools/cafe_exe/cafemice.ico
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / "cafemice.ico"
S = 1024  # drawn large, scaled down for each icon size


def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Dark rounded tile, like the Café's theme.
    d.rounded_rectangle((32, 32, S - 32, S - 32), radius=200, fill=(24, 27, 33, 255))
    d.rounded_rectangle((32, 32, S - 32, S - 32), radius=200, outline=(245, 184, 66, 255), width=28)
    # Cheese wedge: top face, front face, side face.
    top = [(210, 470), (720, 300), (840, 470)]
    front = [(210, 470), (840, 470), (840, 760), (210, 760)]
    d.polygon(front, fill=(245, 184, 66, 255))
    d.polygon(top, fill=(255, 214, 120, 255))
    d.line([(210, 470), (840, 470)], fill=(204, 140, 30, 255), width=14)
    # Holes.
    for cx, cy, r in ((360, 590, 58), (560, 650, 42), (700, 560, 50), (470, 420, 26), (650, 395, 22)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(204, 140, 30, 255))
    return img


def main():
    img = draw()
    img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    img.resize((256, 256), Image.LANCZOS).save(HERE / "cafemice.png")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
