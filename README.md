# breatherun-website

Static marketing site for BreatheRun. No build step: `index.html`, `privacy.html`
and `support.html` are served as-is.

```
index.html  privacy.html  support.html
style.css       layout, type and components
themes.css      GENERATED — every colour, for all 18 brand themes
site.webmanifest
favicon/        active theme's favicons and touch icon
images/         screenshots, social card
images/brand/   active theme's logo lockups
tools/          theme generator and switcher
```

Only the active theme's assets live here. The full brand pack is kept outside
the repo, see below.

## Theming

Colour lives entirely in `themes.css`, keyed off `data-theme` on `<html>`.
`style.css` holds no colour values, only geometry and motion, so restyling
never means editing component CSS.

The brand ships 18 themes. Ocean is the core identity; the winter, Christmas,
autumn and Halloween sets are meant to be time-boxed. Ship one, then switch
back to Ocean.

### Where the brand pack lives

The pack is not in this repo: it is large, mostly binary, and useful to other
projects. Keep it wherever suits, a private repo or a local folder.

The tools find it in this order, first hit wins:

1. `--brand PATH` on the command line
2. `$BREATHERUN_BRAND`
3. the path saved in `.brandpath` (gitignored)
4. `./brand`, if you keep a copy alongside the site
5. an interactive prompt

So the first run asks, and every run after that is silent:

```bash
./tools/switch-theme.sh holly
# Cannot find the BreatheRun brand asset pack.
# Path to brand pack: ~/src/breatherun-brand
# saved to .brandpath, future runs will not ask
```

Both pack shapes work. Point at the pack as it ships (`web/<theme>/`,
`svg/<theme>/`, `social/<theme>/`) or at a flattened copy with everything for
a theme in one folder; the layout is detected, not configured.

### Switching theme

```bash
./tools/switch-theme.sh holly      # go seasonal
./tools/switch-theme.sh ocean      # revert
./tools/switch-theme.sh --list     # show all 18, marking the active one
./tools/switch-theme.sh --check    # verify the active theme is fully applied
```

A theme is more than CSS, so the script also swaps the favicons, apple touch
icon, logo lockups, social preview card, the `theme-color` meta on each page,
and the manifest colours. Doing these by hand is how a swap ends up
half-applied, with a Christmas site still serving a blue favicon.

`--check` is worth running in CI or before a deploy. It confirms every page
and the manifest agree on one theme, and that the assets are present. Given
the pack it also compares the copied files byte-for-byte; without it, it says
so and checks everything else. It never prompts, so it is safe unattended.

### Changing a palette

`brand-guidelines.md`, inside the pack, is the source of truth. Edit the
colour table there, then:

```bash
python3 tools/build-themes.py     # rewrites themes.css
./tools/switch-theme.sh ocean     # re-apply, so assets and meta follow
```

`build-themes.py` takes `--brand` too, and shares the same resolution order.

`build-themes.py` derives the site's full token set from the ten tokens each
theme defines. Surface steps are lifted toward the theme's own ring colour so
cards stay tinted rather than grey, and two ramps are contrast-corrected:

- `--primary-text` is `--primary` lifted just enough to clear WCAG AA on the
  theme background. In Ocean it is identical to `--primary`; only the redder,
  more saturated themes move. Use it wherever the brand colour is *text*.
  `--primary` itself stays true to the guidelines for fills and tints.
- `--plate-ink-*` is a darker (or, on the light-plate themes, lighter) cut of
  the launcher plate gradient. The plate is tuned to sit behind the large
  runner glyph, so at button-label size it falls short: white on Ocean's
  `#12AFA6` is 2.7:1. The ink ramp clears 4.5:1 in all 18 themes.

Do not hand-edit `themes.css`, it gets overwritten.

## Notes

- Typeface is Manrope, loaded via `<link>` rather than `@import`, which blocks
  rendering.
- Logo lockups contain the wordmark as outlined paths, so no text sits beside
  them in the markup and no font is needed to render them.
- Every theme surface is dark, including Ice, Snow and Gold. Only their
  *launcher plates* are light, which is why those three get dark button labels.
