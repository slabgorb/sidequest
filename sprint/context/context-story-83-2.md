---
parent: context-epic-83.md
workflow: tdd
---

# Story 83-2: Standing Folio lobby — close AC8 gaps (880/560 breakpoints + reduced-motion) and design-divergence ratification

## Business Context

Story 83-1 rebuilt the lobby into the Standing Folio and merged to `develop` (`2f62b58`).
A UX verification pass (Alex/ux-designer, 2026-06-03, Playwright on `localhost:5173`)
confirmed the redesign is sound and faithful — but two AC8 items shipped incomplete and two
design divergences shipped as silent contradictions. This story is **polish, not rework**:
it closes the load-bearing AC8 gaps (responsive breakpoints + reduced-motion), resolves the
parked implementation items from 83-1, fixes a cold-mount flash-of-error, and ratifies two
conscious divergences so they stop being silent contradictions.

The lobby is the first surface every player meets and shared-table furniture for Keith's
playgroup — a **primary-audience** polish. Reduced-motion support in particular is plain
correctness (it serves low-motion-tolerance and accessibility needs across the whole table),
not a niche nice-to-have. Breakpoint fidelity keeps the lobby usable on the smaller surfaces
the group actually opens it on.

## Technical Guardrails

- **Polish only — no data-model change.** This is a re-layout/re-skin refinement of the
  *merged* Standing Folio. Keep every existing data path and behavior. No new endpoints, no
  new `WorldMeta` fields, no change to the start/join protocol.
- **Match the numbers, not the mechanism (breakpoints).** AC8 spec'd `≤880px` (single-column
  folio + two-up index grid) and `≤560px` (stacked commit row + full-width Start). The build
  shipped Tailwind defaults `md:` (768) / `sm:` (640). Fix with arbitrary breakpoints
  (`max-[880px]:` / `max-[560px]:`) **or** registered `folio`/`fold` screens in Tailwind
  config — either is acceptable. Relevant classes live in `ConnectScreen.tsx`
  (`md:grid-cols-[296px_1fr]`, `md:grid-cols-2`) and `ModePicker`.
- **Reduced-motion: end-state is the base style.** Guard every looping animation with
  `motion-reduce:animate-none` (Tailwind) or wrap entrance motion in
  `@media (prefers-reduced-motion: no-preference)`. The resting/end state must be the *base*
  style — never `opacity:0` waiting on an animation to reveal it. Unguarded motion to fix:
  `WorldPreview.tsx:103` (`animate-pulse` skeleton), `WorldPreview.tsx:133` (`animate-spin`
  spinner), `ConnectScreen.tsx:617` (`animate-pulse` "loading" text).
- **Reduced-motion + breakpoints are runtime-only.** jsdom cannot evaluate media queries.
  These ACs need a **Playwright/runtime verify** (`emulateMedia({ reducedMotion: 'reduce' })`,
  viewport resize at the boundaries), not jsdom unit tests. Keep unit tests for *structure*;
  add runtime checks for the media-query behavior.
- **No Silent Fallbacks.** The three swallowed catches (`/dev/scenes`, `loadSavedState`,
  `saveState` in `ConnectScreen.tsx`) must `console.warn` on failure — this is the project's
  No-Silent-Fallbacks principle applied, not optional polish.
- **Personal project — no Jira, no work-org anything** (per `sidequest-ui/CLAUDE.md`).
- **Base branch is `develop`** (gitflow) for `sidequest-ui`. Work on
  `feat/83-2-standing-folio-ac8-gaps`.

## Scope Boundaries

**In scope:**
- AC1 — breakpoints corrected to 880/560 (the load-bearing gap).
- AC2 — `prefers-reduced-motion` respected on `animate-spin` + `animate-pulse`; static,
  fully-legible lobby under `reduce`.
- AC3 — parked items: (a) Pirata One self-hosted for the wordmark; (b) `console.warn` on the
  three silent catches; (c) `data-testid="lobby-accent-root"` added + AC7 accent test pointed
  at it; (d) `effectiveOpenGenre` guarded against a stale removed-pack genre.
- AC4 — cold-mount worlds fetch shows a neutral loading state until it resolves or genuinely
  fails (no pre-fetch "Could not load worlds…" flash).

**Out of scope:**
- **The two RESOLVED divergences — ZERO CODE** (Keith, 2026-06-03):
  - `CurrentSessions` null-on-empty is **KEPT** — no "No lanterns lit here tonight." copy.
    The design's empty-state copy and 83-1 AC6's "empty-state copy when none" clause are
    **deliberately superseded.** Do not add empty-state copy.
  - Rules-in-commit-row placement is **ACCEPTED** — pack-Rules staying behind a world
    selection is fine; the ADR-135 tension is acknowledged and deferred. Do not move Rules.
- Hero art stays atmospheric CSS-gradient placeholders (per designer's note + 83-1 scope).
- No full genre re-skin — accent shift only; manuscript house style stays.
- No new below-the-fold sections beyond what the design defined.

## AC Context

Authoritative AC copy lives in the session file / `sprint/epic-83.yaml` (story 83-2).

1. **Breakpoints match spec, runtime-verified at the boundaries.** The folio collapses to
   single-column + two-up index grid at `≤880px`, and the commit row stacks with full-width
   Start at `≤560px`. *Pass condition:* the layout switches **at** the boundary —
   two-column/inline-row at 881 and 561, single-column/stacked at 880 and 560. *Edge cases:*
   881 vs 880 and 561 vs 560 are the discriminating widths (a test fixed at 768/640 would
   false-pass the old behavior). *Verify:* Playwright viewport resize asserting the rendered
   layout (grid column count / row direction), **not** mere Tailwind class-string presence —
   class-presence assertions are coupling-prone for arbitrary breakpoints and don't prove the
   media query actually fires.

2. **Reduced-motion respected.** `animate-spin` (WorldPreview spinner), `animate-pulse`
   (WorldPreview skeleton + ConnectScreen "loading" text) are guarded with `motion-reduce:`
   (or gated behind `prefers-reduced-motion: no-preference`). *Pass condition:* under emulated
   `prefers-reduced-motion: reduce`, **no looping animation runs** and **all content has a
   visible end-state as its base** (no `opacity:0`-stuck cards). *Edge cases:* an element that
   relies on an entrance animation to become visible must already be visible at rest under
   `reduce`. *Verify:* Playwright `emulateMedia({ reducedMotion: 'reduce' })` — assert no
   `animate-spin`/`animate-pulse` active class is applied (or that computed animation is none)
   and that key content nodes have non-zero opacity.

3. **Parked items resolved (or explicitly deferred with rationale).**
   - (a) **Pirata One self-hosted** for the wordmark, replacing the house-serif fallback.
     *Verify:* an `@font-face` for Pirata One pointing at a self-hosted asset (not a remote
     CDN/Google Fonts URL); the masthead wordmark uses the Pirata One family.
   - (b) **`console.warn` on three silent catches** (`/dev/scenes`, `loadSavedState`,
     `saveState`). *Verify:* each `catch` block calls `console.warn` (spy asserts it fires on
     a forced failure); the catch no longer swallows silently.
   - (c) **`data-testid="lobby-accent-root"`** on the `.lobby-folio` root + the AC7 accent
     test asserts against it. *Verify:* the root element carries the testid; the accent test
     selects via the testid and asserts the `[data-genre]` accent changes on world selection.
   - (d) **Stale-genre guard on `effectiveOpenGenre`.** *Verify:* when the open genre's pack
     is absent from the live `/api/genres` catalogue, the accordion does not wedge open on a
     non-existent genre (falls back to closed / first valid genre) — a unit test with a
     removed-pack fixture covers this.

4. **Cold-mount loading state (no error flash).** The worlds fetch shows a neutral loading
   state until it resolves *or genuinely fails*; the "Could not load worlds. Is the server
   running?" copy appears **only on a real failure**, never pre-fetch. *Pass condition:* on
   first mount with an in-flight fetch, the error copy is absent and a loading indicator is
   present; on a rejected fetch, the error copy appears. *Edge cases:* the initial render
   (fetch pending) must not be treated as the failure state. *Verify:* unit test with a
   pending-then-resolved promise asserts no error copy during pending; a rejected promise
   asserts the error copy appears.

## Assumptions

- The merged Standing Folio (`develop`, `2f62b58`) is the working baseline; line numbers in
  the design spec (`WorldPreview.tsx:103/133`, `ConnectScreen.tsx:617`) reflect that merge and
  may have drifted — locate the animation/catch sites by content, not by fixed line number.
- A self-hostable Pirata One font file (OFL-licensed) can be vendored into `sidequest-ui`
  assets; if licensing/sourcing blocks self-hosting, that is a Delivery Finding, not license
  to ship a remote-CDN dependency silently.
- The test harness can run Playwright/runtime checks for media-query behavior (viewport +
  `emulateMedia`). The repo's existing lobby Playwright/reference tests establish the harness;
  if runtime media-query emulation is unavailable, log it as a Delivery Finding (AC1/AC2 can
  *not* be fully proven by jsdom alone — do not substitute a class-presence unit test and
  claim coverage).
- Findings #3 (empty-state) and #4 (Rules placement) require **no code** and **no test** —
  they are accept-current decisions; do not write tests that would re-litigate them.

## Interaction Patterns

- The lobby's interactive flow (accordion single-open, world selection drives preview +
  accent, commit row Solo/MP toggle) is unchanged from 83-1 — 83-2 only refines *how it
  reflows* (880/560 breakpoints) and *how it animates* (reduced-motion), plus the cold-mount
  loading state. No new interactions are introduced.

## Accessibility Requirements

- **`prefers-reduced-motion: reduce`** is a first-class requirement (AC2): no looping
  animation, every node legible at rest, end-state as the base style. This is the bug the
  designer hit and fixed in the prototype — do not regress it.
- Existing 83-1 a11y semantics (accordion `aria-expanded` buttons, `role=radiogroup`/`radio`
  worlds, visible accent focus-ring) must be preserved — none of 83-2's changes may remove
  them. The `data-testid="lobby-accent-root"` addition is test-infrastructure, not an a11y
  attribute, and must not displace existing ARIA.

## Visual Constraints

- **Breakpoints:** single-column folio + two-up index grid at `≤880px`; stacked commit row +
  full-width Start at `≤560px`. Switch *at* those exact widths.
- **Type:** Pirata One (display/masthead) self-hosted; EB Garamond (body), Oswald
  (eyebrows/labels) unchanged. Dark Folio palette and per-genre `[data-genre]` accents from
  `tokens.css` unchanged.
- **Motion:** entrance/looping motion gated on `prefers-reduced-motion: no-preference`;
  resting state is the visible base style. Global scrollbars stay hidden
  (`scrollbar-width:none`), as established in 83-1.
- **Pixel/layout target:** `sidequest-ui/design-reference/lobby-standing-folio/project/SideQuest Lobby.html`
  (Rules placement and breakpoint intent both trace to this reference).
