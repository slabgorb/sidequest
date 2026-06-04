# Epic 83: Lobby Redesign — The Standing Folio

## Overview

Epic 83 is a holistic, from-scratch redesign of the SideQuest lobby (`ConnectScreen`) per
the Claude Design handoff, **Direction A — "The Standing Folio."** It kills the scrollbar
in the world list, replaces it with a fold-fitting genre accordion, and reframes the lobby
as a literary manuscript title page: masthead name ritual, two-pane folio card (genre
accordion + cinematic per-genre preview), commit row (Solo/MP toggle + Start), and
below-the-fold sections (live presence, past journeys, dev scene library). It applies a
Dark Folio palette with Pirata One / EB Garamond type and a subtle per-genre accent shift.
The redesign wires to the existing real worlds/sessions data hooks; hero art stays
atmospheric CSS-gradient placeholders standing in for runtime AI renders.

**Priority:** P2
**Repo:** sidequest-ui (ui)
**Stories:** 2 (8 points) — 83-1 (5pt, done) + 83-2 (3pt, in_progress)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **83-2 follow-up design handoff** (`docs/design/83-2-lobby-folio-followups.md`) | Findings→Work (breakpoints, reduced-motion, parked items, cold-mount), Out-of-scope, Notes for Dev — authoritative spec for 83-2 |
| **Standing Folio prototype** (`sidequest-ui/design-reference/lobby-standing-folio/`) | `SideQuest Lobby.html` (pixel/layout target), `tokens.css` (Dark Folio palette + per-genre accents); `worlds.js` is fixture-only, never wired |
| **83-1 story context** (`sprint/context/context-story-83-1.md`) | Baseline structure, data-wiring reuse list, AC8 (responsive + motion) — the source of 83-2's gaps |
| **ADR-135** Reference Pages Are a Public Table Tool | Rules-discoverability tension acknowledged + deferred (83-2 finding #4, resolved accept-current) |

## Background

The lobby is the first surface every player meets. The pre-83 `ConnectScreen` grouped
worlds in a scrolling list capped at `70vh` with `overflow-y: auto`. Keith opened a Claude
Design session specifically because he "hates the scrollbar" and wanted a holistic
redesign; he reviewed three directions and locked in Direction A — "The Standing Folio."
The lobby must feel like the threshold to "an evening's adventure, told by lamplight," and
it must hold the full real catalogue (11 genres) in the fold with no scrollbar. This is a
**primary-audience polish** for Keith's playgroup — the lobby is shared-table furniture.

**Current state.** Story 83-1 rebuilt `ConnectScreen` into the Standing Folio and merged to
`develop` (`2f62b58`). A UX verification pass (Alex/ux-designer, 2026-06-03, Playwright on
`localhost:5173`) drove the *merged* lobby against the original design handoff and 83-1's
own AC8. Verdict: the redesign is sound and faithful — masthead, zero-scrollbar accordion,
cinematic preview, per-genre accent flip, commit row, and single-column collapse all verify
good. But two AC8 items shipped incomplete, and two design divergences shipped as silent
contradictions. Story 83-2 is the **polish-and-ratify** follow-up that closes those gaps.

**Why 83-2 exists.** (1) Responsive breakpoints shipped as Tailwind defaults (768/640)
instead of the spec's 880/560 — at 860px the lobby is still two-column. (2)
`prefers-reduced-motion` is entirely unhandled: no media query or `motion-reduce:` variant
in `src/`, and the build *added* unguarded `animate-spin`/`animate-pulse`. Plus parked
implementation items from 83-1 (Pirata One self-host, console.warn on silent catches,
`data-testid` hardening, stale-genre guard) and a cold-mount flash-of-error. Two further
findings (empty-state copy, Rules placement) were resolved by Keith as accept-current —
**zero code** — and are recorded for provenance only.

## Technical Architecture

**Component structure** — all in `sidequest-ui/src/screens/lobby/*` (plus `ConnectScreen.tsx`):

```
ConnectScreen.tsx          masthead + folio card + commit row + below-the-fold; route-mounted
├── GenreAccordion         single-open genre rows from /api/genres (zero scrollbar)
├── WorldPreview.tsx       cinematic preview (art, era, tone glyphs, blurb, Lore link)
│                          → animate-pulse (skeleton :103), animate-spin (spinner :133)
├── ModePicker             Solo/MP segmented toggle; drives Start label + breakpoint stack
├── CurrentSessions.tsx    live presence via useSessions (null-on-empty — ratified)
└── JourneyHistory         past journeys via historyStore (click re-selects world)
```

**Key files (83-2 touch surface):**

| File | Role | 83-2 change |
|------|------|-------------|
| `src/screens/ConnectScreen.tsx` | Lobby root; grid breakpoints (`md:grid-cols-[296px_1fr]`, `md:grid-cols-2`), `/dev/scenes` + `loadSavedState`/`saveState` catches, `animate-pulse` (:617), `effectiveOpenGenre` | breakpoints → 880/560; warn on catches; reduced-motion guard; stale-genre guard; cold-mount loading state; `data-testid="lobby-accent-root"` |
| `src/screens/lobby/WorldPreview.tsx` | Cinematic preview | `motion-reduce:animate-none` on `animate-pulse` (:103) + `animate-spin` (:133) |
| `ModePicker` (commit row) | Solo/MP toggle | `max-[560px]:` stacked row + full-width Start |
| `lobby-folio.css` / `tokens.css` | Dark Folio palette, `scrollbar-width:none`, `[data-genre]` accents | font self-host (Pirata One); reduced-motion `@media` if used instead of Tailwind variant |

**Data flow.** Real catalogue from `/api/genres` (`GenresResponse`/`GenreMeta`/`WorldMeta`
in `@/types/genres`); live presence via `useSessions`; history via `historyStore`; start/join
via `useStartGame`; name via `useDisplayName` (`sidequest-connect` localStorage key). 83-2
adds **no** endpoints, **no** new `WorldMeta` fields, **no** data-model change.

**Breakpoint + motion mechanism.** Match the *numbers*, not the mechanism — arbitrary
Tailwind breakpoints (`max-[880px]:` / `max-[560px]:`) or registered `folio`/`fold` screens
are both acceptable. Reduced-motion is **runtime-only** behavior (jsdom can't evaluate media
queries) — it requires a Playwright/runtime verify (`emulateMedia`), not jsdom unit tests.
Resting/end state must be the *base* style; never `opacity:0` waiting on an animation.

## Cross-Epic Dependencies

**Depends on:**
- 83-1 (merged to `develop`, `2f62b58`) — the Standing Folio baseline 83-2 polishes.
- Existing lobby data hooks (`/api/genres`, `useSessions`, `useStartGame`, `historyStore`,
  `useDisplayName`) — reused, not rebuilt.

**Depended on by:**
- None currently. The lobby is a leaf surface. ADR-135 (reference pages / Rules
  discoverability) shares a tension acknowledged here and deferred — not a hard dependency.
