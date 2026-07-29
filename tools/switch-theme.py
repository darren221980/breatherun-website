#!/usr/bin/env python3
"""
Switch the whole site to a brand theme.

The CSS side of a theme is one data-theme attribute, but a few things a
browser or a crawler sees are files rather than custom properties: favicons,
the apple touch icon, the logo lockup, the social preview card, and the
theme-color that paints the mobile browser chrome. This script moves all of
them together so a seasonal swap cannot half-apply.

    ./tools/switch-theme.sh holly
    ./tools/switch-theme.sh --list
    ./tools/switch-theme.sh --check
    ./tools/switch-theme.sh holly --brand ~/src/breatherun-brand

The brand asset pack is not kept in this repo. On first run the script asks
where yours is and remembers the answer in .brandpath; after that it is
silent. See tools/brandpath.py for the full resolution order.

Per the brand guidelines, seasonal themes are time-boxed: ship one, then run
this again with `ocean` to revert.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brandpath

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "privacy.html", "support.html"]
MANIFEST = ROOT / "site.webmanifest"
THEMES_CSS = ROOT / "themes.css"

FAVICONS = [
    "favicon.ico",
    "favicon.svg",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon-48x48.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
]

# source name in the pack -> name under images/brand/
LOGOS = {
    "logo-horizontal.svg": "logo-horizontal.svg",
    "logo-stacked.svg": "logo-stacked.svg",
    "icon.svg": "breatherun-icon.svg",
}


def themes_in_css():
    """Theme keys the generated stylesheet knows about."""
    css = THEMES_CSS.read_text(encoding="utf-8")
    return sorted(set(re.findall(r'\[data-theme="([a-z-]+)"\]', css)))


def surface_colour(theme):
    """The theme's --bg, read back out of the generated stylesheet."""
    css = THEMES_CSS.read_text(encoding="utf-8")
    block = re.search(
        r'\[data-theme="%s"\]\s*\{(.*?)\n\}' % re.escape(theme), css, re.S)
    if not block:
        sys.exit(f"themes.css has no block for '{theme}'. "
                 f"Run tools/build-themes.py first.")
    bg = re.search(r"--bg:\s*(#[0-9A-Fa-f]{6});", block.group(1))
    if not bg:
        sys.exit(f"themes.css block for '{theme}' has no --bg")
    return bg.group(1).upper()


def current():
    m = re.search(r'<html[^>]*data-theme="([a-z-]+)"',
                  (ROOT / PAGES[0]).read_text(encoding="utf-8"))
    return m.group(1) if m else None


def apply(theme, pack, quiet=False):
    if theme not in pack.themes():
        sys.exit(f"'{theme}' is not in {pack.root}. "
                 f"Available there: {', '.join(pack.themes())}")

    bg = surface_colour(theme)
    changed = []

    # 1. favicons and the touch icon
    dst = ROOT / "favicon"
    dst.mkdir(exist_ok=True)
    copied = 0
    for name in FAVICONS:
        src = pack.file(theme, name)
        if src.exists():
            shutil.copyfile(src, dst / name)
            copied += 1
    changed.append(f"favicon/ ({copied} files)")

    # 2. logo lockups
    dst = ROOT / "images" / "brand"
    dst.mkdir(parents=True, exist_ok=True)
    for name, target in LOGOS.items():
        src = pack.file(theme, name)
        if src.exists():
            shutil.copyfile(src, dst / target)
    changed.append("images/brand/")

    # 3. social card
    src = pack.file(theme, "social-preview.png")
    if src.exists():
        shutil.copyfile(src, ROOT / "images" / "social-preview.png")
        changed.append("images/social-preview.png")

    # 4. data-theme and theme-color on every page
    for page in PAGES:
        p = ROOT / page
        s = p.read_text(encoding="utf-8")
        s, n = re.subn(r'(<html[^>]*?)\sdata-theme="[a-z-]+"',
                       r'\1 data-theme="%s"' % theme, s, count=1)
        if n == 0:
            s = s.replace('<html lang="en">',
                          f'<html lang="en" data-theme="{theme}">', 1)
        s = re.sub(r'(<meta name="theme-color"\s+content=")#[0-9A-Fa-f]{6}(">)',
                   r"\g<1>%s\g<2>" % bg, s)
        p.write_text(s, encoding="utf-8")
    changed.append(f"{len(PAGES)} pages (data-theme, theme-color)")

    # 5. manifest colours
    s = MANIFEST.read_text(encoding="utf-8")
    s = re.sub(r'("(?:background_color|theme_color)":\s*")#[0-9A-Fa-f]{6}(")',
               r"\g<1>%s\g<2>" % bg, s)
    MANIFEST.write_text(s, encoding="utf-8")
    changed.append("site.webmanifest")

    if not quiet:
        print(f"switched to '{theme}'  (surface {bg})")
        for c in changed:
            print(f"  updated {c}")
    return bg


def check(pack):
    """
    Confirm the pages, manifest and copied assets all agree.

    Works without the brand pack, in which case it checks internal
    consistency only and says so. That keeps --check usable in CI or on a
    deploy box that has no access to the pack.
    """
    theme = current()
    problems = []
    notes = []

    if theme is None:
        return None, ["no data-theme on <html> in index.html"], notes

    if theme not in themes_in_css():
        problems.append(f"themes.css has no block for '{theme}'")
        return theme, problems, notes

    bg = surface_colour(theme)

    for page in PAGES:
        s = (ROOT / page).read_text(encoding="utf-8")
        m = re.search(r'<html[^>]*data-theme="([a-z-]+)"', s)
        if not m or m.group(1) != theme:
            problems.append(f"{page}: data-theme is "
                            f"{m.group(1) if m else 'unset'}, expected {theme}")
        tc = re.search(r'<meta name="theme-color"\s+content="(#[0-9A-Fa-f]{6})"', s)
        if not tc or tc.group(1).upper() != bg:
            problems.append(f"{page}: theme-color is "
                            f"{tc.group(1) if tc else 'unset'}, expected {bg}")

    mf = MANIFEST.read_text(encoding="utf-8")
    for key in ("background_color", "theme_color"):
        m = re.search(r'"%s":\s*"(#[0-9A-Fa-f]{6})"' % key, mf)
        if not m or m.group(1).upper() != bg:
            problems.append(f"site.webmanifest: {key} is "
                            f"{m.group(1) if m else 'unset'}, expected {bg}")

    # Files that must exist whether or not we can compare them
    for name in FAVICONS:
        if not (ROOT / "favicon" / name).exists():
            problems.append(f"favicon/{name} missing")
    for target in LOGOS.values():
        if not (ROOT / "images" / "brand" / target).exists():
            problems.append(f"images/brand/{target} missing")
    if not (ROOT / "images" / "social-preview.png").exists():
        problems.append("images/social-preview.png missing")

    if pack is None:
        notes.append("brand pack not available, skipped byte comparison "
                     "of the copied assets")
        return theme, problems, notes

    if theme not in pack.themes():
        notes.append(f"'{theme}' is not in {pack.root}, "
                     f"skipped byte comparison")
        return theme, problems, notes

    def same(src, dst):
        return src.exists() and dst.exists() and src.read_bytes() == dst.read_bytes()

    for name in FAVICONS:
        src, dst = pack.file(theme, name), ROOT / "favicon" / name
        if src.exists() and dst.exists() and not same(src, dst):
            problems.append(f"favicon/{name} does not match the pack")
    for name, target in LOGOS.items():
        src, dst = pack.file(theme, name), ROOT / "images" / "brand" / target
        if src.exists() and dst.exists() and not same(src, dst):
            problems.append(f"images/brand/{target} out of sync")
    src = pack.file(theme, "social-preview.png")
    dst = ROOT / "images" / "social-preview.png"
    if src.exists() and dst.exists() and not same(src, dst):
        problems.append("images/social-preview.png out of sync")

    return theme, problems, notes


def main():
    ap = argparse.ArgumentParser(
        description="Switch the site to a BreatheRun brand theme.")
    ap.add_argument("theme", nargs="?", help="theme key, e.g. ocean or holly")
    ap.add_argument("--brand", metavar="PATH",
                    help="path to the brand asset pack "
                         "(saved to .brandpath for next time)")
    ap.add_argument("--list", action="store_true", help="list available themes")
    ap.add_argument("--check", action="store_true",
                    help="verify the active theme is applied consistently")
    args = ap.parse_args()

    if args.check:
        # Never prompt during a check: it may well be running unattended.
        pack = brandpath.find(args.brand, required=False)
        theme, problems, notes = check(pack)
        for n in notes:
            print(f"note: {n}")
        if problems:
            print(f"active theme '{theme}' is inconsistent:")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"active theme '{theme}' is applied consistently")
        return

    if args.list:
        active = current()
        pack = brandpath.find(args.brand, required=False)
        available = pack.themes() if pack else themes_in_css()
        if pack:
            print(f"brand pack: {pack}\n")
        else:
            print("brand pack not found, listing themes from themes.css\n")
        for t in available:
            print(f"{'*' if t == active else ' '} {t}")
        return

    if not args.theme:
        print(f"active theme: {current()}")
        print(f"known themes: {', '.join(themes_in_css())}")
        print("\nusage: ./tools/switch-theme.sh <theme> [--brand PATH]")
        return

    pack = brandpath.find(args.brand)
    apply(args.theme, pack)


if __name__ == "__main__":
    main()
