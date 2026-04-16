# ADR-079: Genre Theme System Unification

**Status:** Accepted
**Date:** 2026-04-16
**Deciders:** Keith Avery, Major Houlihan (Architect)

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
