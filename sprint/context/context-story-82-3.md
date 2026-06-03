---
parent: context-epic-82.md
workflow: tdd
---

# Story 82-3: Wire progression tracks 1-3 — milestone level-up, affinity tiers, item narrative_weight (ADR-021)

## Business Context

ADR-021 defines four progression tracks. Only track 4 (journey recap) is live; tracks 1-3
exist as data models with no engine, so characters never actually advance, affinities never
shift tier, and item significance never matters mechanically. This hits the mechanics-first
players hardest: Sebastien and Jade specifically want to see the numbers move and understand
how the system rewards play (CLAUDE.md). Wiring these tracks — and exposing the resulting
advancement deltas in player-facing surfaces — turns progression from a data model into a
felt reward loop.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 anchors may drift):**
- `genre/models/progression.py` (~:62 `TODO: wire at level-up`; ~:187-221 `WealthTier` + `milestone_categories`, data-only).
- `game/character.py` (~:55-57, ~:102-103 — `AffinityState` tier promotion P6-deferred).
- `game/item_catalog_resolution.py` (~:31 — item `narrative_weight` P2-deferred, no runtime consumer).
- `game/persistence.py` / `game/pg/snapshot.py` — track 4 (recap) is the live precedent to mirror for wiring + OTEL.

**Patterns to follow:**
- Each track gets a runtime engine that runs in the turn pipeline and emits an OTEL/watcher
  span on its state change (level-up, tier crossing, weight application) — mirror the existing
  disposition `SPAN_DISPOSITION_SHIFT` style so the GM panel can confirm engagement.
- Mechanics-first: surface the advancement delta in a player-facing projection (Sebastien/Jade
  see what just changed and why) — a player-UI consideration, not a dev/GM-only emit.

**What NOT to touch:**
- Track 4 (journey recap) — already live.
- The progression YAML schema — consume it, don't reshape it.

## Scope Boundaries

**In scope:**
- Runtime engines for: milestone accumulation → level-up; AffinityState tier promotion; an
  item `narrative_weight` consumer (and/or WealthTier gold→label).
- OTEL per track; player-facing delta exposure; wiring test(s).

**Out of scope:**
- New progression content/config authoring.
- Track 4 changes.

**Split note:** 8 points is large. If the three engines don't fit one clean TDD cycle, split
into 82-3a (milestone/level-up), 82-3b (affinity tiers), 82-3c (item weight / wealth) with a
logged split; each sub-story keeps its own consumer + OTEL + wiring test.

## AC Context

1. **Milestone → level-up.** Milestone accumulation drives level-up (the `progression.py:62`
   TODO is resolved); an OTEL span fires on level-up; the advancement delta is legible in a
   player-facing surface. Edge: a turn that crosses two milestone thresholds at once is handled.
2. **Affinity tiers.** `AffinityState` tier promotion fires at runtime (P6 un-deferred); a
   watcher/OTEL event records the tier crossing. Edge: affinity that drops back across a
   boundary demotes correctly (or is explicitly one-way per the model).
3. **Item weight / wealth.** Item `narrative_weight` has a real runtime consumer (P2
   un-deferred) OR `WealthTier` maps gold→label in a production consumer; the chosen track
   emits OTEL.
4. **Wiring test(s).** Each wired track has a test proving its engine runs in a real turn
   (behavioral, not data-model existence); it fails on current `develop`. Full `just
   server-test` green.

## Assumptions

- Turn processing exposes the events needed to accumulate milestones / shift affinity (combat,
  scene, NPC interaction outcomes); if a needed signal is missing, surfacing it is small and in
  scope — log a deviation if larger.
- Per-track persistence rides the existing session/Postgres snapshot; a schema field addition
  is in scope, a larger migration is a follow-up.
- "Player-facing delta exposure" can reuse an existing projection/state-mirror channel rather
  than a new panel; if a new surface is required, scope it minimally or split it out.
