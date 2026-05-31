---
id: 79
title: "Genre Theme System Unification"
status: accepted
date: 2026-04-16
deciders: [Keith Avery, Major Houlihan (Architect)]
supersedes: []
superseded-by: null
related: []
tags: [frontend-protocol]
implementation-status: live
implementation-pointer: null
---

# ADR-079: Genre Theme System Unification

## Context

The UI has three competing theme layers that each touch CSS custom properties independently:

1. **ThemeProvider** (React context) — sets `--font-family`, color vars, and `.dark` class. Zero non-test consumers of `ThemeContext`. `setTheme()` is never called from game code. Dead code.
2. **useGenreTheme** (hook) — injects genre `client_theme.css` via `<style>` tag, then runs a JS bridge that parses genre vars (`--surface`, `--text`) and re-sets them as Tailwind vars (`--card`, `--foreground`). Also manages `.dark` class via luminance detection.
3. **archetype-chrome.css** — reads genre vars (`--surface`, `--border`, `--primary`) directly, bypassing the bridge.

Additionally, several components use `var(--surface)` in inline Tailwind classes (CharacterPanel, CharacterSheet, InventoryPanel, MapOverlay), creating a third resolution path.

### Problems

1. **ThemeProvider vs useGenreTheme race:** ThemeProvider defaults `.dark` on mount. If useGenreTheme removes it for a light genre, ThemeProvider's `useEffect` can re-add it.
2. **Specificity collision:** `.dark` selector in `index.css` has specificity `(0,1,0)`. Genre CSS uses `:root` at `(0,0,1)`. Dark-mode stock values shadow genre values for any token not explicitly overridden by the JS bridge.
3. **Incomplete bridge:** The JS bridge maps 16 tokens. It misses `--destructive`, `--chart-*`, `--sidebar-*`, and any future Tailwind tokens. Every new shadcn component is a potential theme bug.
4. **Dual resolution:** Tailwind classes resolve through the bridge. Archetype-chrome and inline styles read genre vars directly. Two parallel paths, neither covers everything.

## Decision

**Make genre CSS the single source of truth. Kill the middleman.**

### Specificity Solution

Genre `client_theme.css` files use `:root[data-genre]` as their selector instead of `:root`. `useGenreTheme` sets `data-genre` attribute on `<html>` when injecting theme CSS. Specificity of `:root[data-genre]` is `(0,1,1)` — beats `.dark` at `(0,1,0)`. Genre vars always win when a genre is loaded. Before genre loads, `.dark` stock defaults apply as the pre-theme state.

### Variable Ownership

Genre CSS files own ALL CSS custom properties — both genre identity vars (`--surface`, `--text`, `--primary`, etc.) and Tailwind token vars (`--card`, `--foreground`, `--border`, etc.). No JS bridge.

```
Genre CSS (client_theme.css)
  :root[data-genre] {
    --surface, --text, --primary, ...        → archetype-chrome, inline styles
    --card, --foreground, --border, ...      → Tailwind/shadcn components
  }
```

One source, two consumer paths, zero translation layer.

## Changes Required

| File | Action |
|------|--------|
| `providers/ThemeProvider.tsx` + test | Delete |
| `App.tsx` | Remove ThemeProvider import + wrapper |
| `useGenreTheme.ts` | Remove JS bridge (parseRootVar/bridge/setProperty block). Add `data-genre` attribute. Keep: style injection, luminance detection, Google Font loading |
| `index.css` | No changes — pre-genre fallback |
| `archetype-chrome.css` | No changes — already reads genre vars correctly |
| All 9 `client_theme.css` files | Selector `:root` → `:root[data-genre]`. Add Tailwind token mappings |
| Components with `var(--surface)` | No changes — both paths resolve from genre CSS |

## Consequences

### Positive
- Single source of truth for all theme tokens
- No JS↔CSS translation layer to maintain
- Light genres work without `.dark` class fights
- New shadcn components just work (tokens set in CSS, not a JS allowlist)
- `data-genre` attribute available as a CSS hook for future genre-specific styling

### Negative
- Genre CSS files grow (~15 more lines each) with Tailwind token mappings
- Adding a new Tailwind token requires updating all genre CSS files (but this is explicit and auditable, vs. the silent failure of a missing bridge entry)

### Neutral
- `data-genre` attribute serves double duty: specificity bump + semantic hook
- Pre-genre flash-of-dark is unchanged (acceptable — genre CSS arrives within the first WebSocket message batch)

## Genre-to-Token Mapping Reference

For each genre, derive Tailwind tokens from genre identity vars:

| Genre var | Tailwind token | Mapping |
|-----------|---------------|---------|
| `--text` | `--foreground`, `--card-foreground`, `--popover-foreground`, `--primary-foreground`, `--secondary-foreground`, `--accent-foreground` | Direct |
| `--background` | `--background` | Same name |
| `--surface` | `--card`, `--popover`, `--muted` | Surface = card/popover/muted |
| `--primary` | `--primary` | Same name |
| `--secondary` | `--secondary` | Same name |
| `--accent` | `--accent`, `--ring` | Accent = ring |
| `--surface` | `--border`, `--input` | Border/input derive from surface |
| (computed) | `--muted-foreground` | Midpoint between text and surface — genre-specific tuning |

## Amendment 2026-05-28 — Implementation reconciliation (claims confirmed)

Verified the §Decision claims against `sidequest-ui/src` and the content packs —
all three hold:

- **ThemeProvider is deleted.** No `ThemeProvider`/`ThemeContext` file exists
  under `sidequest-ui/src/providers/` (only `GameStateProvider.tsx`,
  `ImageBusProvider.tsx`, plus non-provider helpers), and a repo-wide search
  finds **zero** `ThemeProvider`/`ThemeContext` references in `src/`. The
  §Changes Required "Delete `providers/ThemeProvider.tsx`" action shipped.
- **`useGenreTheme` is the sole consumer and sets the `data-genre` attribute.**
  `sidequest-ui/src/hooks/useGenreTheme.ts:187` runs
  `root.setAttribute("data-genre", "active")` (the comment at `:185` notes
  "`:root[data-genre]` beats `.dark`"), and removes it on teardown at `:235`.
  The JS-bridge middleman the §Decision set out to kill is gone.
- **Genre CSS uses `:root[data-genre]` specificity.** All 10 live genre packs'
  `client_theme.css` files (`caverns_and_claudes`, `elemental_harmony`,
  `heavy_metal`, `mutant_wasteland`, `neon_dystopia`, `pulp_noir`,
  `road_warrior`, `space_opera`, `spaghetti_western`, `tea_and_murder`) match
  `:root[data-genre]`, confirming the §Specificity Solution / §Changes Required
  selector migration landed pack-wide.

No correction needed — the ADR body matches the running implementation.

## Amendment (2026-05-31): Theme Transport Loud-Fail Guard + data-genre Lifecycle

ADR-079 covers the ThemeProvider deletion and the `:root[data-genre]` specificity
strategy (with `useGenreTheme` as the sole consumer). This amendment records the
**operational hardening** that shipped *after* those decisions — three guards in
`sidequest-ui/src/hooks/useGenreTheme.ts` that exist to honor the loud-fail /
No-Silent-Fallbacks principle. None of these change the §Decision; they make the
"genre theme didn't load" failure mode visible and self-correcting instead of a
silent collapse to the inherited `.dark` defaults.

The original ADR's §Consequences ("Pre-genre flash-of-dark is unchanged …
acceptable — genre CSS arrives within the first WebSocket message batch") quietly
assumed `theme_css` *always* arrives. Playtests showed two ways that assumption
breaks: the transport can drop the event entirely, and React's effect lifecycle
was stripping the `data-genre` attribute milliseconds after the first load. Both
are now handled loudly.

### 1. Loud-fail grace timer (theme_css never arrives)

When the session is `connected` but no `theme_css` SESSION_EVENT has been applied,
the hook arms a grace timer; if the timer fires with still no theme, it
`console.error`s and shows a hardcoded warning banner.

- Grace window is `THEME_CSS_GRACE_MS` — `useGenreTheme.ts:21`. **It was bumped
  from 4000ms to 8000ms** (`useGenreTheme.ts:13-19`) after a playtest regression:
  on a cold start the chargen-scene serialization + WS frame ordering raced past
  the 4s window, so the banner flashed and then auto-dismissed when the theme
  arrived ~5s in — confusing the player. 8s sits comfortably past the cold-start
  tail while still catching a real transport break.
- The guard is armed/cleared in the effect at `useGenreTheme.ts:135-157`: it clears
  any prior timer, skips arming if a theme is applied (or about to be), and only
  arms the `setTimeout` when `connected` is true and nothing has applied yet. The
  callback double-checks `everAppliedRef.current` before firing
  (`useGenreTheme.ts:147`).
- The banner is **styled with literal colors, not CSS vars** —
  `showThemeFailureBanner` at `useGenreTheme.ts:69-93` writes a hardcoded
  `background:#7f1d1d` / `color:#fff` / `border-bottom:2px solid #fca5a5`
  `cssText`. This is deliberate (`useGenreTheme.ts:64-68`): the banner has to stay
  legible precisely when theming failed, so it cannot lean on any `--*` custom
  property (in the failure state `--accent` collapses to an invisible
  `oklch(0.269)`, ~1.39:1 — see `THEME_CSS_FAILURE_BANNER_ID` doc at
  `useGenreTheme.ts:23-29`). The banner is `role="alert"`, `position:fixed`, max
  z-index, and is removed once any theme applies (`removeThemeFailureBanner`,
  `useGenreTheme.ts:95-97`; cleared at `:143` and `:181`).

### 2. `data-genre` re-assertion on every render (attribute-loss fix)

The recurring "genre text unreadable" bug: the effect re-runs on every `messages`
change and its cleanup strips `data-genre` (`useGenreTheme.ts:246`), but the
same-CSS early-return used to skip re-adding it — so the attribute was removed
milliseconds after the first theme load and never restored. With `data-genre`
gone, `:root[data-genre]` (the whole point of ADR-079's specificity solution)
stopped matching and every genre token silently collapsed to its `.dark` value
(`--accent` → `oklch(0.269)` ≈ near-black).

The fix re-asserts the attribute on **every** run, *before* the same-CSS
early-return: `root.setAttribute("data-genre", "active")` at `useGenreTheme.ts:175`,
with the root-cause explanation in the comment block `useGenreTheme.ts:162-173`.
The same-CSS early-return now sits *after* that line (`useGenreTheme.ts:178`), so
re-renders that carry no new CSS still keep the attribute alive for the life of the
theme.

### 3. Luminance-based dark/light toggle

The hook parses `--background` out of the injected CSS string (regex, not
`getComputedStyle`, because the style tag was only just injected) and toggles the
`.dark` class by computed luminance: `--background` extraction at
`useGenreTheme.ts:222-223`, `getLuminance` (WCAG-2.0 sRGB relative luminance, hex
or `rgb()`) at `useGenreTheme.ts:35-62`, and the `lum > 0.5` → remove/add `.dark`
decision at `useGenreTheme.ts:224-236`. If `--background` is absent the hook
`console.warn`s and leaves the mode unchanged rather than guessing
(`useGenreTheme.ts:237-242`) — again, no silent fallback.

### Net effect

The §Decision is unchanged: genre CSS remains the single source of truth and
`:root[data-genre]` is still how it wins the cascade. What changed is that the two
ways that contract can break in practice — the transport dropping `theme_css`, and
the effect lifecycle dropping `data-genre` — now surface loudly (banner +
`console.error`) or self-heal (per-render re-assertion), per CLAUDE.md's
No-Silent-Fallbacks principle.
