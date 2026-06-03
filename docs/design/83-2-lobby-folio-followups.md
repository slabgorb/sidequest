# Design Handoff: Standing Folio Lobby — Follow-up Polish (83-2)

**From:** Alex Kamal (UX Designer) · **To:** Dev (Naomi) · **Date:** 2026-06-03
**Repo:** `sidequest-ui` · **Epic:** 83 (reopened) · **Story:** 83-2 · **Workflow:** tdd

---

## Overview

Story 83-1 rebuilt `ConnectScreen` into "The Standing Folio" and merged to `develop`
(`2f62b58`). A UX verification pass on **2026-06-03** drove the **merged** lobby in
Playwright at `localhost:5173` and compared it against (a) the original Claude Design
handoff and (b) **83-1's own AC8**. The redesign is sound — this story is *polish*, not
rework. It closes the AC8 items that shipped incomplete and ratifies two conscious
design divergences so they stop being silent contradictions.

**Do not re-litigate what already works.** Verified-good and explicitly in scope to keep:

| Verified working | Evidence |
|---|---|
| Masthead: ornament, "SideQuest" wordmark, tagline, name ritual + localStorage | snapshot + screenshot |
| Genre accordion — 11 genres in the fold, **zero scrollbar**, single-open | snapshot; `lobby-folio.css` `scrollbar-width:none` |
| Cinematic preview — art, eyebrow, title, tone glyphs, blurb, Lore link | snapshot |
| Per-genre accent flip (Space Opera cool-blue → Tea&Murder warm-gold) | clicked through both, screenshots |
| Commit row — Solo/MP toggle drives Start label; gated on world selection | snapshot |
| Single-column collapse at narrow width | 540px screenshot |
| Console clean | 0 errors on localhost (the 2 warnings are React Router v7 future-flags) |

---

## Findings → Work

### 1. Breakpoints diverge from spec  *(AC8 gap — confirmed)*

83-1 AC8 reads: *"single-column folio + two-up index grid at **≤880px**; stacked commit
row + full-width Start at **≤560px**."* The build shipped **Tailwind defaults**:
`md:` (768px) and `sm:` (640px). Consequence: at **860px the lobby is still two-column**
(design intended single-column by 880).

**Spec:** Use arbitrary breakpoints matching the design — `max-[880px]:` for the
folio→single-column + index→two-up, and `max-[560px]:` for the commit-row stack +
full-width Start. (Or register `folio`/`fold` screens in Tailwind config; either is fine
— match the numbers, not the mechanism.) The relevant classes are in
`ConnectScreen.tsx` (`md:grid-cols-[296px_1fr]`, `md:grid-cols-2`) and `ModePicker`.

**Verify:** at 881 vs 880 and 561 vs 560 — the layout must switch *at* those boundaries.

### 2. `prefers-reduced-motion` unhandled  *(AC8 gap — confirmed)*

83-1 AC8 reads: *"reduced-motion respected (transform-only entrance, visible end-state
as base)."* Reality: **no `prefers-reduced-motion` media query and no `motion-reduce:`
variant anywhere in `src/`.** The build skipped the design's gated entrance fade
(`@media (prefers-reduced-motion: no-preference){ .fade-key{ animation:fade ... } }`)
*and* added unguarded motion that ignores `reduce`:

- `WorldPreview.tsx:103` `animate-pulse` (loading skeleton)
- `WorldPreview.tsx:133` `animate-spin` (image spinner)
- `ConnectScreen.tsx:617` `animate-pulse` ("loading" text)
- chevron `transition-transform`, image `transition-opacity`

**Spec:** Guard every looping animation with `motion-reduce:animate-none` (Tailwind) or
wrap entrance motion in `@media (prefers-reduced-motion: no-preference)`. The resting
(end) state must be the *base* style — never `opacity:0` waiting on an animation to
reveal it. Under `reduce`, the lobby is fully legible and static.

**Verify:** emulate `prefers-reduced-motion: reduce` (Playwright `emulateMedia` /
DevTools rendering) — no spinner spin, no pulse, content fully visible.

### 3. Empty "Currently in this world" — ~~ratify~~ **RESOLVED (Keith, 2026-06-03)**

`CurrentSessions.tsx:35` returns `null` when empty (comment: *"the lobby never shows a
'0 players online' sadness signal"*). The design showed **"No lanterns lit here
tonight."** when empty, and **83-1 AC6** said *"empty-state copy when none."*

**Decision: keep null-on-empty ("remove it for now").** No empty-state copy — the
section simply doesn't render when there are no live sessions. This is now the
*intended* behavior; the design's empty-state copy and 83-1 AC6's "empty-state copy when
none" clause are **deliberately superseded**. **No code change.** (Rationale: defensible
for a 4-person group usually offline — a permanent empty section is noise.)

### 4. Rules discoverability vs ADR-135 — ~~ratify~~ **RESOLVED (Keith, 2026-06-03)**

The Rules link sits in the **commit row** (`/reference/rules/<pack>`), so pack-Rules
needs a world selected first. The *approved design also put Rules in the commit row*
(`SideQuest Lobby.html:307–311`), so the current behavior is faithful to the design.

**Decision: accept commit-row placement ("the rules are fine for now too, I was able to
find them").** The ADR-135 tension is acknowledged and accepted for now; pack-Rules
staying behind a world selection is fine. **No code change.** Revisit only if
discoverability becomes a real complaint.

### 5. Parked items (from 83-1 archived session)

- **Pirata One self-host** — wordmark currently falls back to the house serif. Self-host
  the font so the masthead matches the design's display face.
- **Silent catches → `console.warn`** — `/dev/scenes`, `loadSavedState`, `saveState` in
  `ConnectScreen.tsx` swallow errors. Per *No Silent Fallbacks*, warn on failure.
- **`data-testid="lobby-accent-root"`** — add to the `.lobby-folio` root and point the
  AC7 accent test at it (the original AC7 test was vacuous; 83-1 tightened it, this
  hardens it against future drift).
- **Stale-genre guard** — `effectiveOpenGenre` can point at a genre whose pack was
  removed; guard so a removed pack can't wedge the accordion open on nothing.

### 6. Cold-mount flash-of-error  *(minor, observed)*

The navigation-instant a11y snapshot caught **"Could not load worlds. Is the server
running?"** before the worlds fetch settled. A first-load user on a slow fetch sees a
scary error that then vanishes.

**Spec:** Show a neutral loading state until the fetch resolves *or genuinely fails*; the
error copy appears only on real failure (not pre-fetch).

---

## Out of scope

- Hero art stays atmospheric placeholders (per the designer's own note + 83-1 scope).
- No full genre re-skin — accent shift only, manuscript house style stays.
- No new below-the-fold sections beyond what the design defined.

## Notes for Dev

- This is `sidequest-ui` only; base branch is **`develop`** (gitflow).
- AC8 items (1, 2) are the load-bearing fixes. Findings 3 (empty-state) and 4
  (Rules placement) are **resolved as accept-current-behavior — zero code** (Keith,
  2026-06-03); they stay documented above for provenance but require no work.
- Reduced-motion and breakpoint behavior are runtime-only (jsdom can't see media
  queries) — they need a Playwright/runtime verify, not just unit tests. Keep the unit
  tests for structure; add a runtime check for the media-query behavior.
