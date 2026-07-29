#!/usr/bin/env python3
"""
Locate the BreatheRun brand asset pack.

The pack is not vendored in this repo. It lives wherever you keep it: a private
repo, a synced folder, an unzipped download. This module finds it, remembers
where it was, and understands both the shape the pack ships in and a flattened
one, so you do not have to reorganise anything to point at it.

Resolution order, first hit wins:

  1. --brand PATH on the command line
  2. $BREATHERUN_BRAND
  3. the path saved in .brandpath (written on first successful run)
  4. ./brand, if you happen to keep a copy alongside the site
  5. an interactive prompt

Layouts understood:

  pack   <root>/web/<theme>/…  <root>/svg/<theme>/…  <root>/social/<theme>/…
         the pack as shipped, whether you point at the zip's root or the
         Branding/ folder inside it

  flat   <root>/<theme>/…      every file for a theme in one directory
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".brandpath"
ENV_VAR = "BREATHERUN_BRAND"

# Which of the pack's source folders each asset comes from. In the flat
# layout they all sit together, so this is only consulted for "pack".
SOURCE_FOLDER = {
    "favicon.ico": "web",
    "favicon.svg": "web",
    "favicon-16x16.png": "web",
    "favicon-32x32.png": "web",
    "favicon-48x48.png": "web",
    "apple-touch-icon.png": "web",
    "android-chrome-192x192.png": "web",
    "android-chrome-512x512.png": "web",
    "logo-horizontal.svg": "svg",
    "logo-stacked.svg": "svg",
    "icon.svg": "svg",
    "social-preview.png": "social",
}


class BrandPack:
    """A located brand pack, normalised so callers ignore the layout."""

    def __init__(self, root, layout):
        self.root = Path(root)
        self.layout = layout

    @property
    def guidelines(self):
        return self.root / "brand-guidelines.md"

    def themes(self):
        base = self.root / "web" if self.layout == "pack" else self.root
        found = []
        for p in base.iterdir():
            try:
                if p.is_dir() and not p.name.startswith(".") \
                        and (p / "favicon.ico").exists():
                    found.append(p.name)
            except OSError:
                continue
        return sorted(found)

    def file(self, theme, name):
        """Absolute path to one asset, wherever the layout keeps it."""
        if self.layout == "flat":
            return self.root / theme / name
        folder = SOURCE_FOLDER.get(name)
        if folder is None:
            raise KeyError(f"no source folder known for asset '{name}'")
        return self.root / folder / theme / name

    def __str__(self):
        return f"{self.root} ({self.layout} layout)"


def _holds_a_theme(directory):
    """True if `directory` has a subdirectory that looks like a theme.

    Tolerant of unreadable entries: a path the user points at may well sit
    beside directories this process cannot stat, and that is not a reason to
    fail. /tmp is the obvious example.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        return False

    for theme in entries:
        try:
            if theme.is_dir() and (theme / "favicon.ico").exists():
                return True
        except OSError:
            continue
    return False


def _detect(path):
    """Return a layout name if `path` looks like a brand pack, else None."""
    try:
        path = Path(path).expanduser()
        if not path.is_dir():
            return None
    except OSError:
        return None

    # pack layout: web/<theme>/favicon.ico
    if _holds_a_theme(path / "web"):
        return "pack"

    # flat layout: <theme>/favicon.ico
    if _holds_a_theme(path):
        return "flat"

    return None


def _try(path, why, verbose=True):
    if not path:
        return None
    layout = _detect(path)
    if layout:
        return BrandPack(Path(path).expanduser().resolve(), layout)
    if verbose:
        print(f"  {why}: {path} is not a brand pack", file=sys.stderr)
    return None


def _prompt():
    if not sys.stdin.isatty():
        sys.exit(
            "Cannot find the brand asset pack, and there is no terminal to ask on.\n"
            f"Set {ENV_VAR}=/path/to/pack, or pass --brand /path/to/pack."
        )

    print("\nCannot find the BreatheRun brand asset pack.")
    print("It is not kept in this repo. Point me at your copy: the folder")
    print("containing brand-guidelines.md, or the one holding the per-theme")
    print("folders. Press Enter on its own to give up.\n")

    while True:
        try:
            raw = input("Path to brand pack: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit("cancelled")

        if not raw:
            sys.exit("cancelled, no brand pack given")

        # Tolerate quotes and trailing slashes from drag-and-drop or tab-complete
        raw = raw.strip("'\"").rstrip("/\\")
        pack = _try(raw, "prompt", verbose=False)
        if pack:
            return pack

        print(f"  {raw} does not look like a brand pack "
              f"(expected web/<theme>/ or <theme>/ with favicon.ico). "
              f"Try again.\n")


def save(pack):
    """Remember this pack so the next run does not ask."""
    try:
        CONFIG.write_text(str(pack.root) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"note: could not save brand path to {CONFIG.name}: {e}",
              file=sys.stderr)


def find(explicit=None, remember=True, required=True):
    """
    Locate the brand pack. Returns a BrandPack, or None when `required` is
    False and nothing is found without asking.
    """
    if explicit:
        pack = _try(explicit, "--brand")
        if not pack:
            sys.exit(f"--brand {explicit} is not a brand pack")
        if remember:
            save(pack)
        return pack

    pack = _try(os.environ.get(ENV_VAR), f"${ENV_VAR}")
    if pack:
        return pack

    if CONFIG.exists():
        saved = CONFIG.read_text(encoding="utf-8").strip()
        pack = _try(saved, f"{CONFIG.name}")
        if pack:
            return pack
        print(f"  the path saved in {CONFIG.name} no longer resolves",
              file=sys.stderr)

    pack = _try(ROOT / "brand", "./brand", verbose=False)
    if pack:
        return pack

    if not required:
        return None

    pack = _prompt()
    if remember:
        save(pack)
        print(f"saved to {CONFIG.name}, future runs will not ask\n")
    return pack
