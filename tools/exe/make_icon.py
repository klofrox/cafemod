"""Draw CafeMice's icon (an original drawing): a big cheese wedge, no frame.

The small sizes (16-32 px) get their own simpler drawing: at that size holes
and a dark tile turn into a blob, so they show a bold wedge with one hole.

    python tools/cafe_exe/make_icon.py    # -> tools/cafe_exe/cafemice.ico (+ a preview PNG)
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT = HERE / "cafemice.ico"

TOP = (255, 221, 110, 255)
FRONT = (250, 184, 40, 255)
SIDE = (222, 142, 20, 255)
HOLE = (196, 118, 10, 255)
EDGE = (92, 52, 8, 255)


def _wedge(size, holes=True):
    """A cheese wedge filling a ``size`` square, drawn at 8x and scaled down."""
    k = 8
    S = size * k
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def p(x, y):  # coordinates on a 0..100 grid
        return (x * S / 100, y * S / 100)

    top = [p(4, 46), p(64, 10), p(96, 34), p(96, 46)]
    front = [p(4, 46), p(96, 46), p(96, 92), p(4, 92)]
    width = max(k, int(S * (0.045 if size <= 32 else 0.025)))
    d.polygon(front, fill=FRONT)
    d.polygon(top, fill=TOP)
    d.line([p(4, 46), p(96, 46)], fill=SIDE, width=width)
    if holes:
        for cx, cy, r in ((25, 70, 10), (55, 77, 7), (77, 64, 8.5), (46, 35, 4.5), (72, 27, 4)):
            d.ellipse([p(cx - r, cy - r), p(cx + r, cy + r)], fill=HOLE)
    else:
        d.ellipse([p(28, 58), p(54, 82)], fill=HOLE)
    # A dark outline keeps the shape readable on light and dark backgrounds.
    d.line(top[:3] + [p(96, 92), p(4, 92), p(4, 46)], fill=EDGE, width=width, joint="curve")
    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = (16, 20, 24, 32, 40, 48, 64, 128, 256)
    images = [_wedge(s, holes=s >= 40) for s in sizes]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[:-1])
    images[-1].save(HERE / "cafemice.png")
    # Preview: every size on a dark and a light strip.
    sheet = Image.new("RGBA", (sum(sizes) + 12 * len(sizes) + 12, 2 * 256 + 36), (32, 32, 32, 255))
    ImageDraw.Draw(sheet).rectangle((0, 256 + 18, sheet.width, sheet.height), fill=(240, 240, 240, 255))
    x = 12
    for size, img in zip(sizes, images):
        sheet.alpha_composite(img, (x, 6))
        sheet.alpha_composite(img, (x, 256 + 24))
        x += size + 12
    sheet.save(HERE.parent.parent / "build" / "icon_preview.png")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
