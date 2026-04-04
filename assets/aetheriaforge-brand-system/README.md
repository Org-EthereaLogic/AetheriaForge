# AetheriaForge Brand System

Brand asset package for AetheriaForge.

## Visual Direction

The mark uses a hexagonal crucible with three layered transformation bands
flowing through it — amber (raw input) at the bottom, violet (forge
transformation) in the middle, and teal (clean output) at the top. A coherence
arc wraps the left side like a quality gauge with a gold score tick. The
composition is intended to read as:

- data transformation through the Medallion architecture
- coherence-scored quality measurement
- structured forging of clean, trustworthy output

## Brand Colors

| Name | Hex | Use |
| --- | --- | --- |
| Deep Forge | `#0D1B2A` | Primary background |
| Crucible | `#1B2838` | Secondary dark surface |
| Forge Violet | `#7C3AED` | Transformation energy, primary accent |
| Ember Amber | `#D97706` | Raw input / pre-forge state |
| Forged Teal | `#14B8A6` | Clean output / coherence pass |
| Spark Gold | `#FBBF24` | Coherence score highlight |
| Ash Slate | `#8B9DB5` | Structural lines |
| Cloud | `#E8EDF4` | Light text and light surface |
| Mist | `#F5F7FA` | Light-mode badge background (structural) |
| Light Grid | `#D4DCE8` | Light-mode grid and structural (structural) |

## Inventory

This package contains `25` generated assets across `source/`, `icons/`,
`variants/`, `favicons/`, and `social/`, plus `README.md` and
`generate_brand_assets.py` for `27` files total.

The layout intentionally follows the same top-level buckets used by
DriftSentinel for repo consistency, but it is not a full mirror of that
package. Marketplace collateral is omitted until there is a direct product
need for it.

## Directory Structure

```text
aetheriaforge-brand-system/
├── README.md
├── generate_brand_assets.py
├── source/
│   ├── aetheriaforge-mark-source.svg
│   ├── aetheriaforge-logo-source.svg
│   └── safari-pinned-tab.svg
├── icons/
│   ├── aetheriaforge-logo-1200x320.png
│   ├── aetheriaforge-mark-128.png
│   ├── aetheriaforge-mark-256.png
│   └── aetheriaforge-mark-512.png
├── variants/
│   ├── mark-dark.png
│   ├── mark-light.png
│   ├── mark-transparent.png
│   ├── logo-dark.png
│   ├── logo-light.png
│   └── logo-transparent.png
├── favicons/
│   ├── android-chrome-192x192.png
│   ├── android-chrome-512x512.png
│   ├── apple-touch-icon.png
│   ├── favicon-16x16.png
│   ├── favicon-32x32.png
│   ├── favicon-48x48.png
│   ├── favicon.ico
│   ├── safari-pinned-tab.svg
│   └── site.webmanifest
└── social/
    ├── linkedin-banner.png
    ├── og-image.png
    └── twitter-card.png
```

## Regeneration

Run the generator from the repository root:

```bash
python assets/aetheriaforge-brand-system/generate_brand_assets.py
```

The generator deterministically rewrites the SVG sources and regenerates the
raster assets in place when the same font environment is available. It uses
Pillow plus a best-effort system font lookup for the wordmark and social text,
so different host font selections can change the raster bytes. If no preferred
font exists, it falls back to Pillow's default font.

## Usage Guide

- Use `source/aetheriaforge-mark-source.svg` when a scalable vector mark is
  required.
- Use `icons/aetheriaforge-mark-*.png` for app icon or repository badge
  contexts.
- Use `favicons/` for browser and PWA favicon wiring.
- Use `social/og-image.png` for Open Graph previews.
- Use `variants/logo-transparent.png` or `variants/logo-light.png` on light
  surfaces.
- Use `variants/logo-dark.png` on dark surfaces.
