"""Genera subscriptions/static/og-image.png (1200x630) para social shares.

Editorial dark — fondo Charcoal Ember, wordmark serif Georgia, accent amber.
No depende de Playwright ni headless Chrome. Usa solo Pillow (pip install Pillow).

Uso:
    python3 tools/build_og_image.py

Re-correr cada vez que cambie el wordmark o la tagline.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 1200, 630

# Charcoal Ember palette
BG = (0x13, 0x16, 0x1a)
TEXT = (0xed, 0xe9, 0xe0)
MUTED = (0x86, 0x89, 0x8e)
ACCENT = (0xd9, 0x9c, 0x5e)


def _font(*candidates: str, size: int) -> ImageFont.ImageFont:
    """Prueba paths de fuentes hasta encontrar uno; fallback a default."""
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except (OSError, FileNotFoundError):
            continue
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Fuentes — paths comunes en macOS, Linux, alpine
    georgia = _font(
        "/System/Library/Fonts/Supplemental/Georgia.ttf",  # macOS
        "/usr/share/fonts/truetype/msttcorefonts/Georgia.ttf",  # debian
        "/usr/share/fonts/TTF/Georgia.ttf",  # arch
        "/System/Library/Fonts/Times.ttc",  # macOS fallback
        size=110,
    )
    georgia_italic = _font(
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        "/System/Library/Fonts/Times.ttc",
        size=36,
    )
    mono = _font(
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        size=22,
    )

    # ===== Layout =====

    # Eyebrow: "ESTABLISHED 2026" — small letterspaced caps top-left
    eyebrow_font = _font(
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        size=22,
    )
    draw.text(
        (80, 80),
        "T H E  D A I L Y",
        font=eyebrow_font,
        fill=ACCENT,
    )

    # Main wordmark: "The Daily Abstract"
    # Centered horizontally, slightly above middle
    wm = "The Daily Abstract"
    bbox = draw.textbbox((0, 0), wm, font=georgia)
    wm_w = bbox[2] - bbox[0]
    wm_h = bbox[3] - bbox[1]
    wm_x = (W - wm_w) // 2
    wm_y = (H - wm_h) // 2 - 50
    draw.text((wm_x, wm_y), wm, font=georgia, fill=TEXT)

    # Amber rule below wordmark
    rule_y = wm_y + wm_h + 30
    draw.line(
        [(W // 2 - 90, rule_y), (W // 2 + 90, rule_y)],
        fill=ACCENT,
        width=2,
    )

    # Tagline italic below rule
    tagline = "A daily edition of new arXiv research"
    bbox = draw.textbbox((0, 0), tagline, font=georgia_italic)
    tl_w = bbox[2] - bbox[0]
    draw.text(
        ((W - tl_w) // 2, rule_y + 30),
        tagline,
        font=georgia_italic,
        fill=MUTED,
    )

    # URL in mono, bottom-left
    draw.text(
        (80, H - 60),
        "arxivdaily.ignorelist.com",
        font=mono,
        fill=ACCENT,
    )

    # Volume/issue in mono, bottom-right
    vol_text = "Vol. I"
    bbox = draw.textbbox((0, 0), vol_text, font=mono)
    vol_w = bbox[2] - bbox[0]
    draw.text(
        (W - vol_w - 80, H - 60),
        vol_text,
        font=mono,
        fill=MUTED,
    )

    # ===== Save =====
    out_path = Path(__file__).parent.parent / "subscriptions" / "static" / "og-image.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    print(f"OK: {out_path} ({W}x{H}, {out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
