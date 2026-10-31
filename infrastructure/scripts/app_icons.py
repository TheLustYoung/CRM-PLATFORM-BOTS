"""Draw the dashboard app icons (home screen / PWA / favicon) into dashboard/public.

    pip install pillow
    python -m infrastructure.scripts.app_icons
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "dashboard" / "public"
S = 2048  # drawn at 2x, downscaled for smooth edges
BG = (10, 10, 10)


def glow(size: int, center: tuple[float, float], radius: float, color: tuple[int, int, int], alpha: int) -> Image.Image:
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx, cy = center[0] * size, center[1] * size
    r = radius * size
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, alpha))
    return layer.filter(ImageFilter.GaussianBlur(r * 0.55))


def line(draw, points, width, fill=(255, 255, 255, 255)):
    draw.line(points, fill=fill, width=width, joint="curve")
    for x, y in (points[0], points[-1]):  # round caps
        draw.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=fill)


def master() -> Image.Image:
    img = Image.new("RGBA", (S, S), (*BG, 255))
    img = Image.alpha_composite(img, glow(S, (0.32, 0.30), 0.30, (0, 124, 240), 150))
    img = Image.alpha_composite(img, glow(S, (0.70, 0.72), 0.28, (255, 0, 128), 120))
    img = Image.alpha_composite(img, glow(S, (0.62, 0.36), 0.20, (121, 40, 202), 110))
    d = ImageDraw.Draw(img)
    u = S / 1024
    w = int(76 * u)
    # Download arrow into a tray: kept inside the 40% safe zone so the same file works as a maskable icon.
    line(d, [(512 * u, 300 * u), (512 * u, 590 * u)], w)
    line(d, [(392 * u, 474 * u), (512 * u, 594 * u), (632 * u, 474 * u)], w)
    line(d, [(312 * u, 600 * u), (312 * u, 704 * u), (712 * u, 704 * u), (712 * u, 600 * u)], w)
    return img


def rounded(img: Image.Image, radius: float) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *img.size), radius=int(img.size[0] * radius), fill=255)
    out = img.copy()
    out.putalpha(mask)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = master()
    full = m.convert("RGB")
    for name, size in {"icon-512.png": 512, "icon-192.png": 192, "apple-touch-icon.png": 180}.items():
        full.resize((size, size), Image.LANCZOS).save(OUT / name, optimize=True)
    small = rounded(m, 0.22)
    small.resize((32, 32), Image.LANCZOS).save(OUT / "favicon-32.png", optimize=True)
    small.resize((256, 256), Image.LANCZOS).save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print("icons written to", OUT)


if __name__ == "__main__":
    main()
