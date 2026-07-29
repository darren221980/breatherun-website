#!/usr/bin/env python3
"""
Generate themes.css from the brand guidelines.

The guidelines are the source of truth. Each theme there defines ten brand
tokens; the website needs a slightly larger set (surface steps, secondary and
muted type, an accessible button ramp). Rather than hand-picking those 18 times
over, this script derives them, so a palette change in the guidelines is one
re-run away from being live.

The guidelines live in the brand asset pack, which is not kept in this repo.
The pack is located the same way switch-theme finds it: --brand, then
$BREATHERUN_BRAND, then .brandpath, then ./brand, then a prompt.

Usage:  python3 tools/build-themes.py [--brand PATH]
Writes: themes.css
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brandpath

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "themes.css"


# ----------------------------------------------------------------------
# Colour maths
# ----------------------------------------------------------------------

def to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h):
    r, g, b = to_rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a, b, t):
    """Blend a toward b. t=0 returns a, t=1 returns b."""
    ra, rb = to_rgb(a), to_rgb(b)
    return to_hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def mix_until(base, toward, against, target, steps=100):
    """
    Blend base toward `toward` in small steps until it reaches `target`
    contrast against `against`. Returns the first blend that clears the
    target, or the fully blended colour if it never does.
    """
    for i in range(steps + 1):
        c = mix(base, toward, i / steps)
        if contrast(c, against) >= target:
            return c
    return mix(base, toward, 1)


# ----------------------------------------------------------------------
# Parse the guidelines
# ----------------------------------------------------------------------

HEADING = re.compile(r"^###\s+(.*?)\s+—\s+`([a-z-]+)`\s*$", re.M)
ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", re.M)
HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def parse_themes(text):
    themes = []
    matches = list(HEADING.finditer(text))

    for n, m in enumerate(matches):
        label, key = m.group(1).strip(), m.group(2)
        end = matches[n + 1].start() if n + 1 < len(matches) else len(text)
        block = text[m.end():end]

        tokens = {}
        for name, value in ROW.findall(block):
            hexes = HEX.findall(value)
            if hexes:
                tokens[name.strip().lower()] = [h.upper() for h in hexes]

        required = ["ring start", "ring mid", "ring end", "accent dot",
                    "plate gradient", "mark ink on plate", "surface", "on-surface"]
        missing = [r for r in required if r not in tokens]
        if missing:
            sys.exit(f"{key}: missing rows in guidelines: {', '.join(missing)}")

        themes.append((key, label, tokens))

    return themes


# ----------------------------------------------------------------------
# Derive the website token set
# ----------------------------------------------------------------------

def derive(tokens):
    ring_start = tokens["ring start"][0]
    ring_mid = tokens["ring mid"][0]
    ring_end = tokens["ring end"][0]
    dot = tokens["accent dot"][0]
    plate = tokens["plate gradient"]
    on_plate = tokens["mark ink on plate"][0]
    bg = tokens["surface"][0]
    text = tokens["on-surface"][0]

    if len(plate) < 3:
        plate = [plate[0], plate[len(plate) // 2], plate[-1]]

    # Surface steps. Lifting straight toward the type colour washes the hue
    # out, so lift toward a half-blend of the deepest ring colour and the type
    # colour instead: the cards stay tinted, not grey.
    lift = mix(ring_start, text, 0.5)

    bg_alt = mix(bg, lift, 0.07)
    surface = mix(bg, lift, 0.13)
    surface_hover = mix(bg, lift, 0.22)
    surface_deep = mix(bg, "#000000", 0.35)

    # Type ramp. Fixed steps back toward the background keep the on-surface
    # tint, with a contrast floor in case a theme starts out low.
    text_secondary = mix_until(mix(text, bg, 0.22), text, bg, 7.0)
    text_muted = mix_until(mix(text, bg, 0.45), text, bg, 4.5)

    # A light tint of the primary, for badges and link hovers.
    primary_soft = mix_until(mix(ring_mid, text, 0.45), text, bg, 7.0)

    # Ring mid is a fill colour first and foremost, and in the redder and
    # more saturated themes it does not clear AA as body-sized text. This is
    # the smallest lift that does, so compliant themes keep the exact brand
    # hue and only the ones that need it move.
    primary_text = mix_until(ring_mid, text, bg, 4.5)

    # Button ramp. The plate is tuned to sit behind the large runner glyph, so
    # it is routinely too low-contrast for button labels. Push each stop away
    # from the plate ink until the label clears AA.
    away = "#000000" if luminance(on_plate) > 0.5 else "#FFFFFF"
    ink_ramp = [mix_until(stop, away, on_plate, 4.5) for stop in plate]

    return {
        "ring-start": ring_start,
        "ring-mid": ring_mid,
        "ring-end": ring_end,
        "dot": dot,
        "primary": ring_mid,
        "primary-dark": ring_start,
        "primary-soft": primary_soft,
        "primary-text": primary_text,
        "primary-rgb": ",".join(str(c) for c in to_rgb(ring_mid)),
        "accent": ring_end,
        "plate-start": plate[0],
        "plate-mid": plate[1],
        "plate-end": plate[2],
        "plate-ink-start": ink_ramp[0],
        "plate-ink-mid": ink_ramp[1],
        "plate-ink-end": ink_ramp[2],
        "on-plate": on_plate,
        "bg": bg,
        "bg-rgb": ",".join(str(c) for c in to_rgb(bg)),
        "bg-alt": bg_alt,
        "surface": surface,
        "surface-hover": surface_hover,
        "surface-deep": surface_deep,
        "text": text,
        "text-secondary": text_secondary,
        "text-muted": text_muted,
    }


ORDER = [
    ("Brand ramp (the mark's ring gradient)",
     ["ring-start", "ring-mid", "ring-end", "dot"]),
    ("Roles",
     ["primary", "primary-dark", "primary-soft", "primary-text",
      "primary-rgb", "accent"]),
    ("Launcher plate gradient, for decorative brand fills",
     ["plate-start", "plate-mid", "plate-end"]),
    ("Darker cut of the plate ramp, for fills that carry text",
     ["plate-ink-start", "plate-ink-mid", "plate-ink-end", "on-plate"]),
    ("Surfaces",
     ["bg", "bg-rgb", "bg-alt", "surface", "surface-hover", "surface-deep"]),
    ("Type",
     ["text", "text-secondary", "text-muted"]),
]


def render(key, label, values, selector):
    pad = max(len(n) for group in ORDER for n in group[1]) + 3
    lines = [f"{selector} {{", f"", f"    /* {label} */", ""]
    for comment, names in ORDER:
        lines.append(f"    /* {comment} */")
        lines.append("")
        for n in names:
            lines.append(f"    --{n}:".ljust(pad + 6) + f"{values[n]};")
        lines.append("")
    lines.append("}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Generate themes.css from the brand guidelines.")
    ap.add_argument("--brand", metavar="PATH",
                    help="path to the brand asset pack "
                         "(saved to .brandpath for next time)")
    args = ap.parse_args()

    pack = brandpath.find(args.brand)
    guidelines = pack.guidelines
    if not guidelines.exists():
        sys.exit(f"no brand-guidelines.md in {pack.root}")

    themes = parse_themes(guidelines.read_text(encoding="utf-8"))
    if not themes:
        sys.exit("no themes parsed, has the guidelines format changed?")

    out = [
        "/* ==========================================================",
        "   BreatheRun theme palettes",
        "",
        "   GENERATED FILE — do not edit by hand.",
        "   Source:     brand-guidelines.md, in the brand asset pack",
        "   Regenerate: python3 tools/build-themes.py",
        "",
        "   To change the active theme, run:",
        "       ./tools/switch-theme.sh <theme>",
        "   which sets data-theme on each page and swaps the matching",
        "   favicons, logo, social preview and manifest colours.",
        "",
        f"   {len(themes)} themes: " + ", ".join(k for k, _, _ in themes),
        "   ========================================================== */",
        "",
        "",
    ]

    ocean = next((t for t in themes if t[0] == "ocean"), themes[0])
    out.append("/* Default, so the site still renders with no data-theme set. */")
    out.append("")
    out.append(render(ocean[0], ocean[1], derive(ocean[2]), ":root"))
    out.append("")
    out.append("")

    for key, label, tokens in themes:
        out.append(render(key, label, derive(tokens), f'[data-theme="{key}"]'))
        out.append("")
        out.append("")

    OUT.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"read  {guidelines}")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(themes)} themes")


if __name__ == "__main__":
    main()
