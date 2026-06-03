---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-6: Wire milestone accumulation → level-up engine + OTEL + player-facing advancement delta (ADR-021 track 1)

> Split from 82-3 (the 8-pt "wire tracks 1-3" umbrella) as track 1 / sub-story "a".
> See `context-story-82-3.md` for the shared umbrella scope; this doc narrows to the
> milestone→level-up engine only.

## Business Context

ADR-021 defines four progression tracks; only track 4 (journey recap) is live. Track 1 —
milestone accumulation driving level-up — exists as a data model with a standing
`TODO: wire at level-up` and no engine, so **characters never actually advance**. This is
the single most felt gap for the mechanics-first players: Sebastien and Jade want to see
the numbers move and understand how play is rewarded (CLAUDE.md). Wiring this track turns
advancement from an inert data model into a felt reward loop — and, per the epic's wiring
doctrine, the ADR cannot be called `live` until a production consumer reaches the
milestone→level-up path and emits OTEL the GM panel can read.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `genre/models/progression.py` — `~:62` carries the `TODO: wire at level-up`; this is the
  seam to resolve. `~:187-221` holds `milestone_categories` (data-only) that the engine reads.
- `game/persistence.py` / `game/pg/snapshot.py` — **track 4 (recap) is the live precedent**:
  mirror its wiring point in the turn pipeline and its snapshot persistence for the new engine.
- Disposition's `SPAN_DISPOSITION_SHIFT` — the OTEL/watcher span style to mirror for the
  level-up emission, so the GM panel can confirm engagement (OTEL Observability Principle).

**Patterns to follow:**
- Add a runtime engine that runs in the turn pipeline and emits an OTEL/watcher span on the
  state change (level-up crossing). Mirror the disposition-shift span shape.
- Mechanics-first: surface the advancement delta (what level, what changed, why) in a
  **player-facing** projection — a player-UI consideration, not a dev/GM-only emit.

**What NOT to touch:**
- Track 4 (journey recap) — already live; it is the precedent, not the target.
- Tracks 2 (affinity, 82-7) and 3 (item weight, 82-8) — sibling sub-stories; stay in lane.
- The progression YAML schema — consume `milestone_categories`, don't reshape it.

## Scope Boundaries

**In scope:**
- A runtime engine: milestone accumulation → level-up, resolving the `progression.py:62` TODO.
- An OTEL/watcher span on level-up.
- Player-facing advancement-delta exposure (reuse an existing projection/state-mirror channel).
- A behavioral wiring test that proves the engine runs in a real turn and fails on current `develop`.

**Out of scope:**
- Affinity tiers (82-7) and item weight / wealth (82-8).
- New progression content/config authoring.
- Track 4 changes.

## AC Context

1. **Milestone → level-up.** Milestone accumulation drives level-up — the
   `progression.py:62` TODO is resolved and the engine runs inside the turn pipeline (not a
   data-model helper called only by tests). **Edge:** a turn that crosses two milestone
   thresholds at once is handled (multi-level-up, or explicitly capped per the model).
2. **OTEL emission.** A span/watcher event fires on each level-up crossing, mirroring the
   disposition-shift span style, so the GM panel can confirm the subsystem engaged.
3. **Player-facing delta.** The advancement delta is legible in a player-facing surface —
   the player sees the level change and its driver, not just a silent stat bump.
4. **Wiring test.** A behavioral test proves the engine runs in a real turn (not data-model
   existence); it fails on current `develop`. Full `just server-test` green.

## Assumptions

- Turn processing already exposes the outcome signals needed to accumulate milestones
  (combat/scene/NPC interaction outcomes). If a needed signal is missing, surfacing it is
  small and in scope — log a deviation if it turns out larger.
- Per-track persistence rides the existing session/Postgres snapshot (mirror track 4); a
  single snapshot field addition is in scope, a larger migration is a follow-up.
- "Player-facing delta exposure" can reuse an existing projection/state-mirror channel
  rather than a new panel; if a new surface is genuinely required, scope it minimally or
  split it out.
