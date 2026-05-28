---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-11: Per-genre peer-action contrast a11y sweep — axe/devtools across live theme_css, bump peer token if <4.5:1

## Business Context

The 2026-05-27 `coyote_star` multiplayer playtest surfaced a long tail of UI
contrast findings (Epic 71's bucket). Story 71-4 already fixed the *own-echo*
readability bug — own player actions now use the high-contrast `text-foreground`
token (WCAG AA ≥4.5:1) and peer actions persist using the lower-contrast
`text-muted-foreground` token, per ADR-036's collaborative-visibility amendment.

But 71-4 only verified contrast for the *base* (non-genre) theme. Per ADR-079,
each live genre pack ships its own `client_theme.css` that overrides
`--muted-foreground` with a genre-specific color, delivered at runtime via the
`theme_css` SESSION_EVENT. Peer-action text is therefore only as legible as the
*weakest* genre theme allows. This is squarely an Alex/Jade concern: in MP,
peer-action text is the collaborative signal the table reads to coordinate
(ADR-036), and if a genre's muted token washes out against its card background,
slow-reading or low-vision players lose that signal. This story closes the gap
by holding every live theme to the same 4.5:1 AA bar that 71-4 set for the base.

## Technical Guardrails

The peer-action token is **`--muted-foreground`**, consumed in the UI via the
Tailwind class `text-muted-foreground`. The discriminator and render path:

- `sidequest-ui/src/components/narrativeRenderers.tsx` (`case "player-action"`,
  ~L203–221): `const isPeer = seg.is_peer === true;` →
  `contrastClass = isPeer ? "text-muted-foreground" : "text-foreground"`. Peer
  text renders inside a `.player-action` div with `data-peer="true"`.
- Token → CSS var mapping: `sidequest-ui/src/index.css` —
  `--color-muted-foreground: var(--muted-foreground)` (L31); base/dark defaults
  `--muted-foreground` (L64 light, L104 dark).
- The contrasting **background** is the card/transcript surface (`--card` /
  `--background`), also genre-overridden in each theme.
- Per-genre override (the actual values to audit/bump) live in each pack's
  `client_theme.css` `:root` block, key `--muted-foreground` (e.g.
  `spaghetti_western/client_theme.css:21` `#6E4E2C` on `--card #E8D5B8`;
  `neon_dystopia/client_theme.css:21` `#607080` on `--card #12121A`).
- Delivery + injection: server emits `theme_css` SESSION_EVENT
  (`sidequest-server/sidequest/handlers/connect.py`,
  `sidequest/genre/loader.py`); the UI injects it via
  `sidequest-ui/src/hooks/useGenreTheme.ts` into a `<style id="genre-theme-css">`
  tag, setting `:root[data-genre]`.

**Live genre packs to sweep (10), each at `sidequest-content/genre_packs/<pack>/client_theme.css`:**
caverns_and_claudes, elemental_harmony, heavy_metal, mutant_wasteland,
neon_dystopia, pulp_noir, road_warrior, space_opera, spaghetti_western,
tea_and_murder.

**Patterns / constraints:**
- Tool: axe DevTools (or browser devtools contrast inspector) measured on the
  live `.player-action[data-peer="true"]` element against its rendered card/
  background, per genre. WCAG 2.x AA threshold = **4.5:1** for body text.
- When a genre's peer token fails, **bump that genre's `--muted-foreground`**
  in its `client_theme.css` until ≥4.5:1 — keep the genre's hue/character; only
  raise contrast (lightness/darkness toward the threshold).
- No-Silent-Fallbacks (CLAUDE.md): the fix lives in the genre source of truth
  (`client_theme.css`), not a UI-side override that masks a bad theme value.
- This is a cosmetic/color change — per UI CLAUDE.md, OTEL spans are **not**
  required for this story.

**Do not touch:** the `text-foreground` own-action path (71-4 owns it), the
`useGenreTheme` injection logic, the segment model in `narrativeSegments.ts`,
or any non-peer transcript styling.

## Scope Boundaries

**In scope:**
- Audit peer-action (`is_peer`) text contrast — the `--muted-foreground` token
  against its rendered background — across **all 10 live genre themes** using
  axe DevTools / browser devtools.
- Where the measured ratio is **< 4.5:1**, bump that genre's `--muted-foreground`
  value in the pack's `client_theme.css` until it meets ≥4.5:1, preserving genre
  hue/character.

**Out of scope:**
- Restyling any other transcript elements (narration prose, player-aside,
  thinking indicator, error/alert text, headings).
- Adjusting non-peer color tokens (`--foreground`, `--accent`, `--primary`,
  `--card`, `--background`, etc.) — except as a *background reference* for
  measuring the peer token; backgrounds are not re-themed here.
- The base/dark `--muted-foreground` in `index.css` (covered by 71-4).
- Genre-workshopping packs (e.g. `low_fantasy`, `caverns_sunden`) — not live.
- Any UI render-path change in `narrativeRenderers.tsx` or `useGenreTheme.ts`.

## AC Context

**AC1 — Every live theme audited.** All 10 live `client_theme.css` peer tokens
are measured with axe/devtools against the peer-action element's actual rendered
background. Pass = a recorded per-genre contrast ratio for the peer token in
each of the 10 packs (no genre skipped). Edge case: the active genre is set via
the runtime `theme_css` SESSION_EVENT, so the audit must be performed with each
genre theme actually applied (`:root[data-genre]` set), not against the base
`index.css` defaults. Verify by switching genres / loading each theme and
re-measuring the same `.player-action[data-peer="true"]` element.

**AC2 — Sub-threshold tokens bumped to ≥4.5:1.** Any genre whose peer token
measures < 4.5:1 has its `--muted-foreground` adjusted in `client_theme.css`
until the re-measured ratio is ≥ 4.5:1. Pass = no live genre's peer-action text
falls below 4.5:1 after the sweep. Edge cases: light-background packs
(spaghetti_western, tea_and_murder) need a *darker* muted token; dark-background
packs (neon_dystopia, heavy_metal, mutant_wasteland) need a *lighter* one — the
bump direction follows the genre's background luminance. A genre already ≥4.5:1
is left unchanged (no gratuitous restyle). A test would assert, per genre, that
`contrastRatio(--muted-foreground, --card)` ≥ 4.5 (computable from the
WCAG-luminance helper already in `useGenreTheme.ts`).

## Accessibility Requirements

- **Target:** peer-action transcript text must meet **WCAG 2.x AA — 4.5:1**
  contrast against its background in **every live genre theme** (it is normal-
  size body text, not large text, so 3:1 does not apply).
- The contrast pair under test is the genre `--muted-foreground` (foreground)
  vs. the genre transcript surface (`--card` / `--background`).
- Aligns with the existing No-Silent-Fallbacks a11y posture in
  `useGenreTheme.ts` (loud banner when a theme fails to load, so `--accent`
  never silently collapses to an invisible value) — this story extends that
  "themes must be legible" guarantee to the peer token specifically.
- Measurement uses axe DevTools / the browser contrast inspector on the live
  rendered element; do not approximate from token values alpha-composited in
  isolation (the `.player-action` div sits over `--card`, not raw `--background`).

## Visual Constraints

- Only the `--muted-foreground` value per `client_theme.css` may change; the
  genre's overall palette, font, `--accent`, and card/background surfaces stay
  fixed.
- Bumps should preserve each genre's hue/identity — raise contrast by shifting
  lightness toward the threshold, not by swapping to a generic gray.
- Token plumbing is fixed: `--color-muted-foreground: var(--muted-foreground)`
  (index.css L31) and the Tailwind `text-muted-foreground` consumer in
  `narrativeRenderers.tsx` are not modified — the change is purely the per-genre
  `:root { --muted-foreground: … }` value.
