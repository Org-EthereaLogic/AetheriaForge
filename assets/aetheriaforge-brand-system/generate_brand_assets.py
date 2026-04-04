from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source"
ICONS_DIR = ROOT / "icons"
VARIANTS_DIR = ROOT / "variants"
FAVICONS_DIR = ROOT / "favicons"
SOCIAL_DIR = ROOT / "social"

PALETTE = {
    "deep_forge": "#0D1B2A",
    "crucible": "#1B2838",
    "forge_violet": "#7C3AED",
    "ember_amber": "#D97706",
    "forged_teal": "#14B8A6",
    "spark_gold": "#FBBF24",
    "ash_slate": "#8B9DB5",
    "cloud": "#E8EDF4",
    "mist": "#F5F7FA",
    "light_grid": "#D4DCE8",
}

BOLD_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Avenir Next Demi Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]

REGULAR_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    red, green, blue = ImageColor.getrgb(hex_color)
    return red, green, blue, alpha


def ensure_dirs() -> None:
    for path in (SOURCE_DIR, ICONS_DIR, VARIANTS_DIR, FAVICONS_DIR, SOCIAL_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_font(size: int, *, bold: bool) -> FontType:
    candidates = BOLD_FONT_CANDIDATES if bold else REGULAR_FONT_CANDIDATES
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def alpha_composite(base: Image.Image, overlay: Image.Image) -> Image.Image:
    return Image.alpha_composite(base.convert("RGBA"), overlay.convert("RGBA"))


def _draw_hexagon(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    *,
    fill: tuple[int, int, int, int] | None = None,
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> None:
    """Draw a regular hexagon centred at (cx, cy)."""
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 90)
        points.append((cx + int(radius * math.cos(angle)), cy + int(radius * math.sin(angle))))
    draw.polygon(points, fill=fill, outline=outline, width=width)


def _draw_arc_segment(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    start_deg: float,
    end_deg: float,
    *,
    fill: tuple[int, int, int, int],
    width: int,
) -> None:
    """Draw a thick arc segment as a series of short line segments."""
    steps = max(20, int(abs(end_deg - start_deg)))
    points = []
    for i in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        points.append((cx + int(radius * math.cos(angle)), cy + int(radius * math.sin(angle))))
    draw.line(points, fill=fill, width=width, joint="curve")


def render_badge(size: int, mode: str) -> Image.Image:
    """Render the AetheriaForge mark at the requested size.

    The mark shows a hexagonal crucible with layered transformation bands
    flowing upward, wrapped by a coherence-score arc on the left.
    """
    scale = 4
    canvas = 512 * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if mode == "dark":
        background = rgba(PALETTE["deep_forge"])
        hex_fill = rgba(PALETTE["crucible"])
        hex_outline = rgba(PALETTE["forge_violet"], 180)
        arc_color = rgba(PALETTE["forged_teal"], 200)
        arc_bg = rgba(PALETTE["ash_slate"], 60)
        ember = rgba(PALETTE["ember_amber"])
        violet = rgba(PALETTE["forge_violet"])
        teal = rgba(PALETTE["forged_teal"])
        gold = rgba(PALETTE["spark_gold"])
        structural = rgba(PALETTE["ash_slate"], 100)
    elif mode == "light":
        background = rgba(PALETTE["mist"])
        hex_fill = rgba("#E2E8F0")
        hex_outline = rgba("#6D28D9", 190)
        arc_color = rgba("#0D9488", 210)
        arc_bg = rgba(PALETTE["light_grid"], 180)
        ember = rgba("#B45309")
        violet = rgba("#6D28D9")
        teal = rgba("#0D9488")
        gold = rgba("#D97706")
        structural = rgba("#94A3B8", 140)
    elif mode == "transparent":
        background = None
        hex_fill = rgba("#1E293B", 200)
        hex_outline = rgba("#6D28D9", 200)
        arc_color = rgba("#0D9488", 220)
        arc_bg = rgba("#94A3B8", 80)
        ember = rgba("#B45309")
        violet = rgba("#6D28D9")
        teal = rgba("#0D9488")
        gold = rgba("#D97706")
        structural = rgba("#94A3B8", 120)
    else:
        msg = f"Unsupported badge mode: {mode}"
        raise ValueError(msg)

    cx = canvas // 2
    cy = canvas // 2

    # Background rounded rectangle
    if background is not None:
        inset = 20 * scale
        draw.rounded_rectangle(
            (inset, inset, canvas - inset, canvas - inset),
            radius=116 * scale,
            fill=background,
        )
        # Subtle glow behind hexagon
        draw.ellipse(
            (cx - 200 * scale, cy - 180 * scale, cx + 200 * scale, cy + 180 * scale),
            fill=rgba(PALETTE["forge_violet"], 18 if mode == "dark" else 12),
        )

    # Coherence arc background (full circle, faded)
    _draw_arc_segment(draw, cx, cy, 200 * scale, 150, 390, fill=arc_bg, width=12 * scale)

    # Coherence arc foreground (partial — represents ~78% score)
    _draw_arc_segment(draw, cx, cy, 200 * scale, 150, 338, fill=arc_color, width=12 * scale)

    # Score tick mark at end of arc
    tick_angle = math.radians(338)
    tick_cx = cx + int(200 * scale * math.cos(tick_angle))
    tick_cy = cy + int(200 * scale * math.sin(tick_angle))
    draw.ellipse(
        (tick_cx - 10 * scale, tick_cy - 10 * scale, tick_cx + 10 * scale, tick_cy + 10 * scale),
        fill=gold,
    )

    # Outer hexagon
    _draw_hexagon(draw, cx, cy, 160 * scale, fill=hex_fill, outline=hex_outline, width=10 * scale)

    # Inner hexagon (structural)
    _draw_hexagon(draw, cx, cy, 110 * scale, outline=structural, width=6 * scale)

    # Transformation flow: three horizontal bands through the hexagon
    # Bottom band — ember (raw input)
    band_w = 120 * scale
    band_h = 16 * scale
    for offset_y, color, alpha_val in [
        (50, PALETTE["ember_amber"], 200),
        (0, PALETTE["forge_violet"], 220),
        (-50, PALETTE["forged_teal"], 240),
    ]:
        y = cy + offset_y * scale
        bar_color = rgba(color, alpha_val)
        draw.rounded_rectangle(
            (cx - band_w, y - band_h, cx + band_w, y + band_h),
            radius=band_h,
            fill=bar_color,
        )

    # Upward flow arrows (three small chevrons)
    arrow_x = cx + 80 * scale
    for i, (ay_offset, color) in enumerate(
        [(40, ember), (0, violet), (-40, teal)]
    ):
        ay = cy + ay_offset * scale
        arrow_size = 14 * scale
        draw.line(
            [
                (arrow_x - arrow_size, ay + arrow_size // 2),
                (arrow_x, ay - arrow_size // 2),
                (arrow_x + arrow_size, ay + arrow_size // 2),
            ],
            fill=rgba(color[0:3][0], color[0:3][1], color[0:3][2], 180) if False else (*color[:3], 180),
            width=6 * scale,
            joint="curve",
        )

    # Spark dots at corners of inner hexagon
    for i in range(6):
        angle = math.radians(60 * i - 90)
        sx = cx + int(110 * scale * math.cos(angle))
        sy = cy + int(110 * scale * math.sin(angle))
        draw.ellipse(
            (sx - 6 * scale, sy - 6 * scale, sx + 6 * scale, sy + 6 * scale),
            fill=gold,
        )

    image = alpha_composite(image, overlay)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def render_logo(width: int, height: int, mode: str) -> Image.Image:
    background = {
        "dark": rgba(PALETTE["deep_forge"]),
        "light": rgba("#FFFFFF"),
        "transparent": None,
    }[mode]
    text_primary = PALETTE["cloud"] if mode == "dark" else PALETTE["crucible"]
    text_accent = PALETTE["forge_violet"] if mode == "dark" else "#6D28D9"

    image = Image.new("RGBA", (width, height), background or (0, 0, 0, 0))
    badge_mode = "dark" if mode == "dark" else "light" if mode == "light" else "transparent"
    badge = render_badge(256, badge_mode)
    image.alpha_composite(badge, (48, (height - badge.height) // 2))

    draw = ImageDraw.Draw(image)
    title_font = load_font(108, bold=True)
    subtitle_font = load_font(34, bold=False)

    title_y = 82
    # "Aetheria" in primary, "Forge" in accent
    draw.text((352, title_y), "Aetheria", font=title_font, fill=text_primary)
    aetheria_bbox = draw.textbbox((352, title_y), "Aetheria", font=title_font)
    draw.text((aetheria_bbox[2] + 8, title_y), "Forge", font=title_font, fill=text_accent)
    draw.text(
        (356, 224),
        "Coherence-scored data transformation engine",
        font=subtitle_font,
        fill=rgba(text_primary, 210),
    )

    return image


def write_svg_sources() -> None:
    """Write deterministic SVG source files for the mark and logo."""

    # Helper: hexagon points as SVG path
    def hex_path(cx: int, cy: int, r: int) -> str:
        points = []
        for i in range(6):
            angle = math.radians(60 * i - 90)
            points.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
        return "M " + " L ".join(points) + " Z"

    # Coherence arc as SVG path
    def arc_path(cx: int, cy: int, r: int, start_deg: float, end_deg: float) -> str:
        s = math.radians(start_deg)
        e = math.radians(end_deg)
        x1 = cx + r * math.cos(s)
        y1 = cy + r * math.sin(s)
        x2 = cx + r * math.cos(e)
        y2 = cy + r * math.sin(e)
        large = 1 if abs(end_deg - start_deg) > 180 else 0
        return f"M {x1:.1f},{y1:.1f} A {r},{r} 0 {large},1 {x2:.1f},{y2:.1f}"

    mark_svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">',
            "  <defs>",
            '    <linearGradient id="badge-bg" x1="0%" y1="0%" x2="100%" y2="100%">',
            f'      <stop offset="0%" stop-color="{PALETTE["crucible"]}"/>',
            f'      <stop offset="100%" stop-color="{PALETTE["deep_forge"]}"/>',
            "    </linearGradient>",
            '    <linearGradient id="flow-gradient" x1="256" y1="306" x2="256" y2="206"',
            '      gradientUnits="userSpaceOnUse">',
            f'      <stop offset="0%" stop-color="{PALETTE["ember_amber"]}"/>',
            f'      <stop offset="50%" stop-color="{PALETTE["forge_violet"]}"/>',
            f'      <stop offset="100%" stop-color="{PALETTE["forged_teal"]}"/>',
            "    </linearGradient>",
            "  </defs>",
            '  <rect x="20" y="20" width="472" height="472" rx="116" fill="url(#badge-bg)"/>',
            f'  <ellipse cx="256" cy="240" rx="200" ry="180" fill="{PALETTE["forge_violet"]}" opacity="0.07"/>',
            # Coherence arc background
            f'  <path d="{arc_path(256, 256, 200, 150, 390)}" fill="none"',
            f'    stroke="{PALETTE["ash_slate"]}" stroke-opacity="0.25" stroke-width="12"',
            '    stroke-linecap="round"/>',
            # Coherence arc foreground
            f'  <path d="{arc_path(256, 256, 200, 150, 338)}" fill="none"',
            f'    stroke="{PALETTE["forged_teal"]}" stroke-opacity="0.8" stroke-width="12"',
            '    stroke-linecap="round"/>',
            # Score tick
            f'  <circle cx="{256 + 200 * math.cos(math.radians(338)):.1f}"'
            f' cy="{256 + 200 * math.sin(math.radians(338)):.1f}" r="10"'
            f' fill="{PALETTE["spark_gold"]}"/>',
            # Outer hexagon
            f'  <path d="{hex_path(256, 256, 160)}" fill="none"',
            f'    stroke="{PALETTE["forge_violet"]}" stroke-opacity="0.7" stroke-width="10"/>',
            # Inner hexagon
            f'  <path d="{hex_path(256, 256, 110)}" fill="none"',
            f'    stroke="{PALETTE["ash_slate"]}" stroke-opacity="0.4" stroke-width="6"/>',
            # Transformation bands
            f'  <rect x="136" y="290" width="240" height="16" rx="8"'
            f' fill="{PALETTE["ember_amber"]}" opacity="0.78"/>',
            f'  <rect x="136" y="248" width="240" height="16" rx="8"'
            f' fill="{PALETTE["forge_violet"]}" opacity="0.86"/>',
            f'  <rect x="136" y="206" width="240" height="16" rx="8"'
            f' fill="{PALETTE["forged_teal"]}" opacity="0.94"/>',
            # Upward chevrons
            '  <path d="M 322 304 L 336 290 L 350 304" fill="none"',
            f'    stroke="{PALETTE["ember_amber"]}" stroke-width="6"'
            '    stroke-linecap="round" stroke-linejoin="round"/>',
            '  <path d="M 322 262 L 336 248 L 350 262" fill="none"',
            f'    stroke="{PALETTE["forge_violet"]}" stroke-width="6"'
            '    stroke-linecap="round" stroke-linejoin="round"/>',
            '  <path d="M 322 220 L 336 206 L 350 220" fill="none"',
            f'    stroke="{PALETTE["forged_teal"]}" stroke-width="6"'
            '    stroke-linecap="round" stroke-linejoin="round"/>',
            # Spark dots at hexagon vertices
            *[
                f'  <circle cx="{256 + 110 * math.cos(math.radians(60 * i - 90)):.1f}"'
                f' cy="{256 + 110 * math.sin(math.radians(60 * i - 90)):.1f}" r="6"'
                f' fill="{PALETTE["spark_gold"]}"/>'
                for i in range(6)
            ],
            "</svg>",
        ]
    )

    logo_svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 320" width="1200" height="320">',
            "  <defs>",
            '    <linearGradient id="logo-badge-bg" x1="0%" y1="0%" x2="100%" y2="100%">',
            f'      <stop offset="0%" stop-color="{PALETTE["crucible"]}"/>',
            f'      <stop offset="100%" stop-color="{PALETTE["deep_forge"]}"/>',
            "    </linearGradient>",
            "  </defs>",
            '  <g transform="translate(12 32) scale(0.5)">',
            '    <rect x="20" y="20" width="472" height="472" rx="116" fill="url(#logo-badge-bg)"/>',
            f'    <ellipse cx="256" cy="240" rx="200" ry="180" fill="{PALETTE["forge_violet"]}" opacity="0.07"/>',
            f'    <path d="{arc_path(256, 256, 200, 150, 390)}" fill="none"',
            f'      stroke="{PALETTE["ash_slate"]}" stroke-opacity="0.25" stroke-width="12"',
            '      stroke-linecap="round"/>',
            f'    <path d="{arc_path(256, 256, 200, 150, 338)}" fill="none"',
            f'      stroke="{PALETTE["forged_teal"]}" stroke-opacity="0.8" stroke-width="12"',
            '      stroke-linecap="round"/>',
            f'    <circle cx="{256 + 200 * math.cos(math.radians(338)):.1f}"'
            f' cy="{256 + 200 * math.sin(math.radians(338)):.1f}" r="10"'
            f' fill="{PALETTE["spark_gold"]}"/>',
            f'    <path d="{hex_path(256, 256, 160)}" fill="none"',
            f'      stroke="{PALETTE["forge_violet"]}" stroke-opacity="0.7" stroke-width="10"/>',
            f'    <path d="{hex_path(256, 256, 110)}" fill="none"',
            f'      stroke="{PALETTE["ash_slate"]}" stroke-opacity="0.4" stroke-width="6"/>',
            f'    <rect x="136" y="290" width="240" height="16" rx="8"'
            f' fill="{PALETTE["ember_amber"]}" opacity="0.78"/>',
            f'    <rect x="136" y="248" width="240" height="16" rx="8"'
            f' fill="{PALETTE["forge_violet"]}" opacity="0.86"/>',
            f'    <rect x="136" y="206" width="240" height="16" rx="8"'
            f' fill="{PALETTE["forged_teal"]}" opacity="0.94"/>',
            '    <path d="M 322 304 L 336 290 L 350 304" fill="none"',
            f'      stroke="{PALETTE["ember_amber"]}" stroke-width="6"'
            '      stroke-linecap="round" stroke-linejoin="round"/>',
            '    <path d="M 322 262 L 336 248 L 350 262" fill="none"',
            f'      stroke="{PALETTE["forge_violet"]}" stroke-width="6"'
            '      stroke-linecap="round" stroke-linejoin="round"/>',
            '    <path d="M 322 220 L 336 206 L 350 220" fill="none"',
            f'      stroke="{PALETTE["forged_teal"]}" stroke-width="6"'
            '      stroke-linecap="round" stroke-linejoin="round"/>',
            *[
                f'    <circle cx="{256 + 110 * math.cos(math.radians(60 * i - 90)):.1f}"'
                f' cy="{256 + 110 * math.sin(math.radians(60 * i - 90)):.1f}" r="6"'
                f' fill="{PALETTE["spark_gold"]}"/>'
                for i in range(6)
            ],
            "  </g>",
            '  <text x="352" y="164" font-family="Avenir Next, Arial, Helvetica, sans-serif"',
            f'    font-size="108" font-weight="700" fill="{PALETTE["crucible"]}">Aetheria</text>',
            '  <text x="872" y="164" font-family="Avenir Next, Arial, Helvetica, sans-serif"',
            '    font-size="108" font-weight="700" fill="#6D28D9">Forge</text>',
            '  <text x="356" y="244" font-family="Avenir Next, Arial, Helvetica, sans-serif"',
            f'    font-size="34" fill="{PALETTE["crucible"]}" fill-opacity="0.82">',
            "    Coherence-scored data transformation engine",
            "  </text>",
            "</svg>",
        ]
    )

    pinned_tab_svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">',
            # Outer hexagon
            f'  <path d="{hex_path(256, 256, 160)}" fill="none" stroke="#000000" stroke-width="30"/>',
            # Inner hexagon
            f'  <path d="{hex_path(256, 256, 110)}" fill="none" stroke="#000000"',
            '    stroke-width="20" opacity="0.65"/>',
            # Three transformation bands
            '  <rect x="136" y="290" width="240" height="16" rx="8" fill="#000000" opacity="0.75"/>',
            '  <rect x="136" y="248" width="240" height="16" rx="8" fill="#000000"/>',
            '  <rect x="136" y="206" width="240" height="16" rx="8" fill="#000000" opacity="0.85"/>',
            # Vertex dots
            *[
                f'  <circle cx="{256 + 110 * math.cos(math.radians(60 * i - 90)):.1f}"'
                f' cy="{256 + 110 * math.sin(math.radians(60 * i - 90)):.1f}" r="8" fill="#000000"/>'
                for i in range(6)
            ],
            "</svg>",
        ]
    )

    (SOURCE_DIR / "aetheriaforge-mark-source.svg").write_text(mark_svg, encoding="utf-8")
    (SOURCE_DIR / "aetheriaforge-logo-source.svg").write_text(logo_svg, encoding="utf-8")
    (SOURCE_DIR / "safari-pinned-tab.svg").write_text(pinned_tab_svg, encoding="utf-8")
    (FAVICONS_DIR / "safari-pinned-tab.svg").write_text(pinned_tab_svg, encoding="utf-8")


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def write_icons_variants_favicons() -> None:
    badge_512_dark = render_badge(512, "dark")
    badge_512_light = render_badge(512, "light")
    badge_512_transparent = render_badge(512, "transparent")
    logo_dark = render_logo(1200, 320, "dark")
    logo_light = render_logo(1200, 320, "light")
    logo_transparent = render_logo(1200, 320, "transparent")

    # icons/
    for size in (128, 256):
        save_png(render_badge(size, "dark"), ICONS_DIR / f"aetheriaforge-mark-{size}.png")
    save_png(badge_512_dark, ICONS_DIR / "aetheriaforge-mark-512.png")
    save_png(logo_transparent, ICONS_DIR / "aetheriaforge-logo-1200x320.png")

    # variants/
    save_png(badge_512_dark, VARIANTS_DIR / "mark-dark.png")
    save_png(badge_512_light, VARIANTS_DIR / "mark-light.png")
    save_png(badge_512_transparent, VARIANTS_DIR / "mark-transparent.png")
    save_png(logo_dark, VARIANTS_DIR / "logo-dark.png")
    save_png(logo_light, VARIANTS_DIR / "logo-light.png")
    save_png(logo_transparent, VARIANTS_DIR / "logo-transparent.png")

    # favicons/
    favicon_sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "favicon-48x48.png": 48,
        "apple-touch-icon.png": 180,
        "android-chrome-192x192.png": 192,
    }
    for filename, size in favicon_sizes.items():
        save_png(render_badge(size, "dark"), FAVICONS_DIR / filename)
    save_png(badge_512_dark, FAVICONS_DIR / "android-chrome-512x512.png")

    badge_512_dark.save(
        FAVICONS_DIR / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    manifest = {
        "name": "AetheriaForge",
        "short_name": "AetheriaForge",
        "icons": [
            {"src": "android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
            {
                "src": "android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable any",
            },
        ],
        "theme_color": PALETTE["deep_forge"],
        "background_color": PALETTE["deep_forge"],
        "display": "standalone",
    }
    (FAVICONS_DIR / "site.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def draw_pill(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, *, font: FontType) -> int:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = (right - left) + 52
    height = (bottom - top) + 26
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=height // 2,
        fill=rgba("#1E1338", 228),
    )
    draw.text((x + 26, y + 10), text, font=font, fill=PALETTE["cloud"])
    return width


def render_social(width: int, height: int, platform: str) -> Image.Image:
    image = Image.new("RGBA", (width, height), rgba(PALETTE["deep_forge"]))
    draw = ImageDraw.Draw(image)
    title_font = load_font(max(54, height // 7), bold=True)
    subtitle_font = load_font(max(26, height // 18), bold=False)
    pill_font = load_font(max(20, height // 24), bold=False)

    # Background shapes
    draw.ellipse((-120, -80, width // 2, height + 80), fill=rgba("#152240", 255))
    draw.ellipse((width // 2, -height // 2, width + 260, height // 2), fill=rgba("#1A1840", 180))

    badge_size = int(height * 0.48)
    badge = render_badge(badge_size, "dark")
    image.alpha_composite(
        badge,
        (64, (height - badge_size) // 2 - (18 if platform == "linkedin" else 0)),
    )

    left = 64 + badge_size + 56
    title_top = max(56, int(height * 0.18))
    # Title with two-tone
    draw.text((left, title_top), "Aetheria", font=title_font, fill=PALETTE["cloud"])
    aetheria_bbox = draw.textbbox((left, title_top), "Aetheria", font=title_font)
    draw.text((aetheria_bbox[2] + 8, title_top), "Forge", font=title_font, fill=PALETTE["forge_violet"])

    subtitle = "Coherence-scored data transformation engine"
    draw.text(
        (left, title_top + int(height * 0.19)),
        subtitle,
        font=subtitle_font,
        fill=rgba(PALETTE["cloud"], 214),
    )

    pill_y = title_top + int(height * 0.34)
    cursor = left
    for label in ("Shannon entropy", "Entity resolution", "Temporal merge"):
        cursor += draw_pill(draw, cursor, pill_y, label, font=pill_font) + 16

    # Accent band: amber → violet → teal (transformation flow)
    band_y = height - 74
    seg1 = int(left + (width - left - 72) * 0.33)
    seg2 = int(left + (width - left - 72) * 0.66)
    draw.line((left, band_y, seg1, band_y), fill=rgba(PALETTE["ember_amber"]), width=8)
    draw.line((seg1, band_y, seg2, band_y - 8), fill=rgba(PALETTE["forge_violet"]), width=8)
    draw.line((seg2, band_y - 8, width - 72, band_y - 16), fill=rgba(PALETTE["forged_teal"]), width=8)
    # Endpoint spark
    draw.ellipse(
        (width - 96, band_y - 40, width - 48, band_y + 8),
        fill=rgba(PALETTE["spark_gold"]),
    )

    return image


def write_social() -> None:
    save_png(render_social(1200, 630, "og"), SOCIAL_DIR / "og-image.png")
    save_png(render_social(1200, 600, "twitter"), SOCIAL_DIR / "twitter-card.png")
    save_png(render_social(1584, 396, "linkedin"), SOCIAL_DIR / "linkedin-banner.png")


def main() -> None:
    ensure_dirs()
    write_svg_sources()
    write_icons_variants_favicons()
    write_social()


if __name__ == "__main__":
    main()
