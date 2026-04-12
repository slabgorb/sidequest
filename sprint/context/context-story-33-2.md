---
parent: context-epic-33.md
workflow: trivial
---

# Story 33-2: Background canvas per-archetype textures — genre-themed surface visible through grid gutters

## Business Context

BackgroundCanvas currently renders a single generic radial gradient using `--surface` and `--background` CSS vars. It looks the same for every genre — a soft vignette that provides depth but zero genre identity. The background is visible through Dockview gutter gaps (the narrow strips between panels), and when panels are resized or tabs are rearranged, larger sections of canvas become exposed.

Story 33-1 shipped archetype-specific widget chrome (borders, overlays, corner flourishes). The background canvas is the remaining "generic" surface — the one place where the archetype visual identity doesn't reach. This story closes that gap: a player running `neon_dystopia` should see a digital rain / circuit-trace pattern behind their panels, while `low_fantasy` should see a warm parchment fiber texture. CSS only, no image assets.

## Technical Guardrails

### Key Files

| File | Action |
|------|--------|
| `src/components/GameBoard/BackgroundCanvas.tsx` | Primary modification target — currently 21 lines |
| `src/styles/archetype-chrome.css` | Reference for archetype pattern conventions; may add `BackgroundCanvas`-specific rules here |
| `src/hooks/useChromeArchetype.ts` | Read-only reference — provides `data-archetype` on `<html>`, already wired |

### Patterns to Follow

1. **Consume from the CSS cascade, not props.** BackgroundCanvas currently reads `--surface` and `--background` from CSS vars set by `useGenreTheme`. The archetype textures should follow the same pattern — `data-archetype` is already on `<html>`, so CSS attribute selectors like `[data-archetype="terminal"] .background-canvas` work without touching React props.

2. **Archetype-level, not genre-level.** Three texture families (parchment, terminal, rugged), not eleven genre-specific backgrounds. Colors vary per-genre automatically via CSS vars; the texture pattern is structural (same for all genres in a family). This matches the two-layer architecture from 33-1.

3. **CSS-only patterns.** Use `background-image` with CSS gradients (`linear-gradient`, `radial-gradient`, `repeating-linear-gradient`, `conic-gradient`) and potentially `background-blend-mode`. No `<canvas>`, no JS animation, no image assets. The existing archetype overlays in `archetype-chrome.css` (vignettes, scanlines) demonstrate the pattern.

4. **Z-index: -10.** BackgroundCanvas is `fixed inset-0 -z-10`. Terminal scanline overlay is at `z-index: 100`. Parchment/rugged vignettes are at `z-index: 0`. Background textures must stay at `-z-10` — they render behind everything including the existing `::before` overlays.

### What NOT to Touch

- `useGenreTheme.ts` — no changes needed; CSS vars are already flowing
- `useChromeArchetype.ts` — no changes needed; `data-archetype` is already set
- `GameBoard.tsx` — BackgroundCanvas is already rendered; no wiring changes
- The existing `[data-archetype]::before` overlays in `archetype-chrome.css` — those are widget-area vignettes, separate from the background canvas

## Scope Boundaries

**In scope:**
- Per-archetype CSS background textures on BackgroundCanvas (parchment, terminal, rugged)
- Textures must use genre CSS custom properties for color values (not hardcoded colors)
- A CSS class or data attribute on the BackgroundCanvas div to enable archetype CSS targeting

**Out of scope:**
- Per-genre (as opposed to per-archetype) backgrounds — that would be 11 variants, not 3
- Animated backgrounds (CSS `@keyframes`, requestAnimationFrame) — static textures only for this story
- Image-based textures (PNG, SVG, WebP) — CSS gradients only
- Changes to the existing widget chrome overlays (33-1 territory)
- Dockview gutter styling — gutters are transparent by default, which is correct (they reveal the canvas)

## AC Context

**AC1: Each archetype has a distinct, genre-themed background texture.**
- Parchment: a warm, fiber-like texture suggesting aged paper or vellum. Achievable with layered `radial-gradient` noise and soft `repeating-linear-gradient` fibers using `--surface`/`--primary` color vars.
- Terminal: a digital/circuit pattern suggesting a CRT or data stream. Achievable with `repeating-linear-gradient` grid lines, dot patterns via `radial-gradient`, or diagonal hash marks using `--accent`/`--primary` color vars.
- Rugged: a cracked, gritty texture suggesting worn metal or desert hardpan. Achievable with layered diagonal `repeating-linear-gradient` scratches and asymmetric `radial-gradient` patches using `--border`/`--surface` color vars.
- **Test:** With each archetype active (`data-archetype` set), the background-canvas element's computed `background-image` should differ from the default radial gradient.

**AC2: Textures are CSS-only — no image assets.**
- All `background-image` values must be CSS gradient functions only.
- No `url()` references in any background property.
- **Test:** Grep the component and CSS files for `url(` — must return zero matches in BackgroundCanvas-related styles.

**AC3: Textures use genre CSS custom properties for color adaptation.**
- All color values in the texture gradients must reference CSS custom properties (`var(--surface)`, `var(--primary)`, `var(--accent)`, `var(--background)`, `var(--border)`) rather than hardcoded RGB/HSL values.
- This means the same parchment texture automatically looks warm-brown for `low_fantasy` and cool-silver for `star_chamber` based on the genre's palette.
- **Test:** Change genre (which changes CSS var values) with the same archetype active — the texture's colors should update without any React rerender.

**AC4: Background remains behind all content at z-index -10.**
- The `fixed inset-0 -z-10` positioning must be preserved.
- Textures must not interfere with the archetype `::before` vignette overlays (z-index 0 for parchment/rugged, z-index 100 for terminal).
- **Test:** Visual inspection — panels, overlays, and input bar all render above the background texture.

## Assumptions

- `data-archetype` is reliably set on `<html>` before BackgroundCanvas renders. Verified: `useChromeArchetype` runs in `App.tsx` which is a parent of `GameBoard`.
- CSS `color-mix()` is available in target browsers. Verified: already used in BackgroundCanvas and archetype-chrome.css (shipped in 33-1).
- No genre currently lacks a `theme_css` payload that sets `--surface`, `--background`, `--primary`, `--accent`. If a genre is missing vars, BackgroundCanvas already has fallbacks (`var(--surface, hsl(var(--card)))`).

## Visual Constraints

- **Texture density:** Subtle. The background is mostly occluded by panels — only visible through 4-8px gutter gaps and during panel resize. Textures should read as atmosphere, not distraction. Target opacity for pattern elements: 3-8% (matching the terminal scanline at `0.008` opacity and rugged vignette at `0.5` opacity for the outer edge).
- **No animation:** Static textures. Animated backgrounds would fight with the narrative focus and create a visual noise floor that makes text harder to read.
- **Contrast safety:** Background textures must not create high-contrast patterns that bleed through transparent panel areas. The existing `color-mix(in srgb, ... transparent)` approach in the current gradient is the right pattern — never fully opaque texture elements.
- **Dark/light mode:** Textures must work in both modes. Using CSS vars (which adapt to the genre palette) handles this automatically. Do not use hardcoded light or dark color values.
