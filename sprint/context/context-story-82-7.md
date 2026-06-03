---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-7: Wire AffinityState tier promotion + OTEL + player-facing delta (ADR-021 track 2)

> Split from 82-3 (the 8-pt "wire tracks 1-3" umbrella) as track 2 / sub-story "b".
> See `context-story-82-3.md` for the shared umbrella scope; this doc narrows to the
> AffinityState tier-promotion engine only.

## Business Context

ADR-021 track 2 — `AffinityState` tier promotion — exists as a data model marked
P6-deferred, with no runtime engine, so **affinities never actually shift tier**. A
relationship can accumulate without ever crossing a threshold the player or the narrator
can act on. This matters to the mechanics-first players (Sebastien/Jade want the numbers to
move) and feeds the project's player-facing relationship direction (ADR-136). By the epic's
wiring doctrine the track is not `live` until a production consumer drives tier promotion at
runtime and emits OTEL the GM panel can read.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `game/character.py` — `~:55-57` and `~:102-103` hold `AffinityState` and the P6-deferred
  tier-promotion seam; this is the target to un-defer and run at runtime.
- `game/persistence.py` / `game/pg/snapshot.py` — **track 4 (recap) is the live precedent**
  for the turn-pipeline wiring point and snapshot persistence; mirror it.
- Disposition's `SPAN_DISPOSITION_SHIFT` — the closest existing analogue (a relationship
  state crossing). Mirror its OTEL/watcher span style for the tier-crossing emission.

**Patterns to follow:**
- Add a runtime engine that evaluates `AffinityState` in the turn pipeline and emits an
  OTEL/watcher span on a tier crossing, mirroring the disposition-shift span shape.
- Mechanics-first: surface the tier delta in a **player-facing** projection (who moved, to
  what tier, why) — a player-UI consideration, not a dev/GM-only emit. Prefer the existing
  relationship/disposition projection channel over a new surface.

**What NOT to touch:**
- Track 4 (journey recap) — already live; precedent, not target.
- Tracks 1 (milestone/level-up, 82-6) and 3 (item weight, 82-8) — sibling sub-stories.
- The affinity/disposition data schema — consume it, don't reshape it.

## Scope Boundaries

**In scope:**
- A runtime engine: `AffinityState` tier promotion (P6 un-deferred), running in the turn pipeline.
- An OTEL/watcher event on each tier crossing.
- Player-facing tier-delta exposure (reuse an existing projection/state-mirror channel).
- A behavioral wiring test that proves the engine runs in a real turn and fails on current `develop`.

**Out of scope:**
- Milestone/level-up (82-6) and item weight / wealth (82-8).
- New affinity/relationship content authoring.
- Track 4 changes.

## AC Context

1. **Affinity tier promotion.** `AffinityState` tier promotion fires at runtime inside the
   turn pipeline (P6 un-deferred) when affinity crosses a tier boundary. **Edge:** affinity
   that drops back across a boundary demotes correctly — OR the model is explicitly one-way
   and the test asserts that intended behavior.
2. **OTEL emission.** A watcher/OTEL event records each tier crossing, mirroring the
   disposition-shift span style, so the GM panel can confirm the subsystem engaged.
3. **Player-facing delta.** The tier change is legible in a player-facing surface — the
   player sees the relationship move tiers and its driver, not a silent internal shift.
4. **Wiring test.** A behavioral test proves the engine runs in a real turn (not data-model
   existence); it fails on current `develop`. Full `just server-test` green.

## Assumptions

- Turn processing already exposes the NPC-interaction outcome signals needed to adjust
  affinity. If a needed signal is missing, surfacing it is small and in scope — log a
  deviation if larger.
- Per-track persistence rides the existing session/Postgres snapshot (mirror track 4); a
  single snapshot field addition is in scope, a larger migration is a follow-up.
- "Player-facing delta exposure" can reuse the existing relationship/disposition projection
  rather than a new panel; if a new surface is genuinely required, scope it minimally.
