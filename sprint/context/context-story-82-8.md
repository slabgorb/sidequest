---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-8: Wire item narrative_weight / WealthTier gold→label consumer + OTEL + player-facing (ADR-021 track 3)

> Split from 82-3 (the 8-pt "wire tracks 1-3" umbrella) as track 3 / sub-story "c".
> See `context-story-82-3.md` for the shared umbrella scope; this doc narrows to the
> item-weight / wealth track only. Tightest of the three (2 pts).

## Business Context

ADR-021 track 3 covers two thin, related seams that never reach production: item
`narrative_weight` (P2-deferred, no runtime consumer) and `WealthTier` (a gold→label mapping
that exists data-only). As shipped, **an item's significance never matters mechanically and
wealth never resolves to a legible tier** — the data is loaded but nothing drives it. The
mechanics-first players want this visible (CLAUDE.md), and by the epic's wiring doctrine the
track is not `live` until a production consumer reaches one of these seams and emits OTEL the
GM panel can read. This story may wire **either** seam (whichever yields the cleaner single
consumer) and still satisfy track 3 — they are alternatives, not both-required.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `game/item_catalog_resolution.py` — `~:31` is the item `narrative_weight` seam (P2-deferred,
  no runtime consumer).
- `genre/models/progression.py` — `~:187-221` holds `WealthTier` + `milestone_categories`
  (data-only); the gold→label mapping lives here.
- `game/persistence.py` / `game/pg/snapshot.py` — **track 4 (recap) is the live precedent**
  for the turn-pipeline wiring point and persistence; mirror it.
- Disposition's `SPAN_DISPOSITION_SHIFT` — the OTEL/watcher span style to mirror for the
  weight-application / wealth-tier emission.

**Patterns to follow:**
- Add a single production consumer for the chosen seam that runs in the real runtime path
  (item resolution or wealth display), and emit an OTEL/watcher span when it applies.
- Mechanics-first: surface the result (item weight applied, or wealth tier label) in a
  **player-facing** surface — a player-UI consideration, not a dev/GM-only emit.

**What NOT to touch:**
- Track 4 (journey recap) — already live; precedent, not target.
- Tracks 1 (milestone/level-up, 82-6) and 2 (affinity, 82-7) — sibling sub-stories.
- The item/progression YAML schema — consume it, don't reshape it.

## Scope Boundaries

**In scope:**
- A real runtime consumer for **one** of: item `narrative_weight` (P2 un-deferred) OR
  `WealthTier` gold→label mapping.
- An OTEL/watcher span on the chosen seam's application.
- Player-facing exposure of the result.
- A behavioral wiring test that proves the consumer runs in a real path and fails on current `develop`.

**Out of scope:**
- Milestone/level-up (82-6) and affinity tiers (82-7).
- Wiring both seams — one satisfies track 3 (note which in the PR; the other can be a follow-up).
- New item/wealth content authoring; track 4 changes.

## AC Context

1. **Item weight OR wealth tier wired.** Either item `narrative_weight` has a real runtime
   consumer (P2 un-deferred) **or** `WealthTier` maps gold→label in a production consumer.
   The chosen seam runs in a real path, not a test-only helper. **Edge:** boundary values
   (zero/min weight, gold exactly on a tier boundary) resolve to the intended label/behavior.
2. **OTEL emission.** The chosen seam emits an OTEL/watcher span on application, mirroring the
   disposition-shift style, so the GM panel can confirm engagement.
3. **Player-facing result.** The applied weight or wealth-tier label is visible in a
   player-facing surface.
4. **Wiring test.** A behavioral test proves the consumer runs in a real path (not data-model
   existence); it fails on current `develop`. Full `just server-test` green.

## Assumptions

- The chosen seam's input (item catalog entry / character gold) is already available at the
  consumer's runtime point; if not, surfacing it is small and in scope — log a deviation if larger.
- Persistence (if any state is added) rides the existing session/Postgres snapshot; a single
  field addition is in scope, a larger migration is a follow-up.
- "Player-facing" can reuse an existing projection/state-mirror channel rather than a new panel.
