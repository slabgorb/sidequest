---
parent: context-epic-38.md
workflow: tdd
---

# Story 38-5: SealedLetterLookup Resolution Handler

## Business Context

This is the keystone story. It adds the new `match` arm in the confrontation resolution
dispatch that actually RUNS the dogfight mechanic: gather actor commits via TurnBarrier,
look up the cross-product in the interaction table, apply per-actor deltas, emit OTEL
spans. Without this, the types and data structures from 38-1/2/3/4 are unused
infrastructure.

This is where Ace of Aces comes to life in the engine.

## Technical Guardrails

### CLAUDE.md Wiring Rules (MANDATORY)

1. **Verify Wiring, Not Just Existence.** This story IS the wiring. The new match arm
   must be reachable from the production dispatch path. A function that exists but isn't
   called from `dispatch/` is dead code.
2. **Every Test Suite Needs a Wiring Test.** Integration test that sends a dogfight
   confrontation through the REAL dispatch pipeline — not a unit test calling the
   handler directly.
3. **No Silent Fallbacks.** If the interaction table is missing a cell for a commit pair,
   PANIC. The table must be exhaustive. Don't fall back to "no change."
4. **No Stubbing.** The handler must fully resolve: gather commits, lookup cell, apply
   ALL deltas (set_fields, metric_delta, secondary_delta), record narration hint. No
   "apply deltas later" shortcuts.
5. **Don't Reinvent — Wire Up What Exists.** Use TurnBarrier as-is (or as extended by
   38-3). Use the interaction table as loaded by 38-4. Use per_actor_state as added by
   38-2. Don't build parallel infrastructure.

### Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-server/src/dispatch/` | Add `SealedLetterLookup` match arm in confrontation resolution |
| `sidequest-api/crates/sidequest-game/src/encounter.rs` | `apply_per_actor_delta()` function — writes to `EncounterActor.per_actor_state` |
| `sidequest-api/crates/sidequest-game/src/barrier.rs` | Consume `drain_actor_commits()` for confrontation-scoped commits |
| `sidequest-api/crates/sidequest-telemetry/src/` | Add dogfight OTEL span definitions |

### Critical Wiring Path

```
dispatch_confrontation_resolution()
  → match confrontation.def.resolution_mode
    → SealedLetterLookup:
      → session.turn_barrier.drain_actor_commits(confrontation_id)
      → confrontation.def.interaction_table.lookup(commit_a, commit_b)
      → apply_per_actor_delta(&mut actors[0], &cell.actor_a_delta)
      → apply_per_actor_delta(&mut actors[1], &cell.actor_b_delta)
      → record_narration_hint(cell.narration_hint)
      → emit OTEL spans
```

Every step in this chain must be a real function call, not a placeholder.

### Dependencies

- **38-1:** `ResolutionMode` enum exists on `ConfrontationDef`
- **38-2:** `per_actor_state` exists on `EncounterActor`
- **38-3:** TurnBarrier is verified/extended for confrontation scope
- **38-4:** Interaction table and `_from:` loader are working
- ALL FOUR must be merged before this story starts.

## Scope Boundaries

**In scope:**
- New match arm for `ResolutionMode::SealedLetterLookup` in confrontation dispatch
- `apply_per_actor_delta()` function that writes cell deltas to actor's `per_actor_state`
- Interaction table lookup by `(actor_a_commit, actor_b_commit)` pair
- Narration hint recording (stored for 38-6 to consume)
- OTEL spans: `dogfight.maneuver_committed`, `dogfight.cell_resolved`, `dogfight.gun_solution_fired`, `dogfight.energy_depleted`
- Integration test: full dispatch path with mock session, two actors, commit-reveal-resolve cycle

**Out of scope:**
- Narrator rendering of cockpit POV (38-6)
- UI display of dogfight state (future epic)
- Three-actor dogfights (MVP is 2-actor only)
- Skill tier resolution at confrontation start (future — MVP uses Veteran for both)
- Damage model / hull deduction (depends on 38-7 content, can be added later)

## AC Context

**AC1: Match arm dispatches correctly**
- A `StructuredEncounter` with `resolution_mode: SealedLetterLookup` takes the new code path
- A `StructuredEncounter` with `resolution_mode: BeatSelection` still takes the existing path
- Test: create both types, dispatch each, verify correct path taken

**AC2: Commit gathering works**
- Two actors commit maneuvers via TurnBarrier
- Handler calls `drain_actor_commits()` and gets exactly 2 commits
- Test: simulate two actor commits, verify both returned

**AC3: Interaction table lookup succeeds**
- Given commits `("loop", "straight")`, lookup returns the correct cell
- All 16 cells are reachable (exhaustive test over all 4x4 permutations)
- Missing cell pair panics (not silently ignored)
- Test: load real space_opera interaction table, verify all 16 lookups succeed

**AC4: Per-actor deltas applied correctly**
- After resolution, each actor's `per_actor_state` reflects the cell's deltas
- `set_fields` overwrites/adds fields in the actor's state
- `metric_delta` updates the encounter's shared metric (if present)
- Test: before/after comparison of actor state for a known cell

**AC5: OTEL spans emitted**
- `dogfight.maneuver_committed` emitted for each actor commit with actor_id and maneuver_id
- `dogfight.cell_resolved` emitted with cell_name, shape, delta summaries
- `dogfight.gun_solution_fired` emitted when cell sets `gun_solution: true`
- `dogfight.energy_depleted` emitted when energy drops below threshold
- Test: span collector in test harness, assert span presence and attributes

**AC6: Multi-turn cycle**
- Run 3 consecutive commit-resolve turns on the same encounter
- State accumulates correctly across turns (energy depletes, descriptors evolve)
- No stale state from previous turns

**AC7: Wiring test — production dispatch path**
- Integration test in `sidequest-server/tests/` that sends a dogfight confrontation
  through the REAL dispatch pipeline
- Not a direct call to the handler function — must go through the dispatch entry point
- Proves the match arm is reachable from production code

## Assumptions

- Confrontation dispatch is in `sidequest-server/src/dispatch/` (verify path)
- The dispatch function already has a match on some encounter property (verify pattern)
- TurnBarrier's API was settled by 38-3 (must be merged first)
- Interaction table loaded by 38-4 is available on `ConfrontationDef` at dispatch time
