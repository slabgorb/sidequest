# Epic 42: ADR-082 Phase 3 — Port confrontation engine to Python

## Overview

Phase 3 of the ADR-082 Python port. Ports the unified `StructuredEncounter` confrontation engine (ADR-033) from `sidequest-api` (Rust) to `sidequest-server` (Python): types, resource pools, tension tracker, and combat dispatch. After Phase 3 merges, combat encounters play end-to-end on the Python server with parity OTEL spans and narrator-prompt integration.

**Priority:** P0
**Repo:** server (`sidequest-server`)
**Stories:** 4 (21 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **ADR-082** (`docs/adr/082-port-api-rust-to-python.md`) | Decision to port Rust → Python; 1:1 crate-to-package composition rule |
| **Execution Strategy Spec** (`docs/superpowers/specs/2026-04-19-python-port-execution-strategy-design.md`) | Eight-phase plan; Phase 3 anchoring decisions; test-porting discipline |
| **Phase 3 Decomposition** (`docs/plans/phase-3-combat-port.md`) | Story DAG; per-story scope + acceptance; structural corrections vs the original spec sketch |
| **ADR-033 Confrontation Engine** (`docs/adr/033-confrontation-engine.md`) | `StructuredEncounter` unified model; resource pool semantics; metric directions |
| **ADR-077 Sealed-Letter Lookup** (`docs/adr/077-sealed-letter-confrontations.md`) | `EncounterActor.per_actor_state` shape preserved in 42-1 |
| **Phase 2 Decomposition** (`docs/plans/phase-2-chargen-port.md`) | IOU audit from Phase 1/2 — `GameSnapshot.encounter` promotion due in 42-1 |

## Background

### Structural corrections vs the original spec

The execution-strategy spec (§Phase 3) sketched Phase 3 as porting *"`combat_models`, `combatant`, `engagement`, `encounter` + combat OTEL."* Recon during Phase 3 decomposition found three material errors in that sketch:

1. **`combat_models.rs` does not exist** in the Rust source. Naming error in the spec.
2. **`engagement.rs` (18 LOC) is not combat engagement.** It is a trope-engine pure function (`engagement_multiplier(turns_since_meaningful) -> f32`) that scales trope tick rate by player activity. Wrong subsystem.
3. **Combat and chase are already unified** in Rust under `StructuredEncounter` (ADR-033 / Story 16-2). The old `CombatState` and `ChaseState` structs were deleted. Everything — combat, chase, standoffs, negotiations — is a `StructuredEncounter` with a string-keyed `encounter_type` and a polymorphic `EncounterMetric`.

Consequence: the spec's Phase 3/Phase 4 split (combat / chase as separate subsystems) does not map to the Rust source. Chase is a *flavor* of encounter, not a distinct type. Phase 4 is rescoped to "chase cinematography" layering on top of the already-typed encounter — and per Keith's 2026-04-20 decision, **Phase 4 is skipped for the initial port**; a separate chase-polish pass will land later. Epic 42 must ship `StructuredEncounter.chase(...)` and `SecondaryStats.rig(...)` in 42-1 so chase encounters still construct correctly, but cinematic layers (camera modes, terrain modifiers, danger-level framing) are out of scope.

### Why Phase 3 now

Phase 2 (chargen) is merged end-to-end; the only open Phase 2 gate is the live playtest Keith still owes. With chargen working, every saved character is parked at Playing state with no encounter infrastructure to exercise — combat is the next subsystem the narrator prompt has been waiting for. Deferring Phase 3 stalls the rest of the port (scenario engine, advancement, CLIs all depend on having a live encounter model).

### What is already ported (do not re-port)

Epic 39 landed ahead of the port. Fragments live in `sidequest-server` already:

- `EdgePool` — `sidequest/game/creature_core.py:45` (composure axis)
- `Character.is_broken()` / `Character.edge_fraction()` — `sidequest/game/character.py:164,168`
- `GameSnapshot.encounter: dict | None` — `sidequest/game/session.py:340` (placeholder pass-through; 42-1 promotes to typed)

## Technical Architecture

### Scope map

| Rust source | LOC | Target (Python) |
|---|---|---|
| `sidequest-game/src/encounter.rs` | 724 | `sidequest/game/encounter.py` (new) |
| `sidequest-game/src/resource_pool.rs` | 275 | `sidequest/game/resource_pool.py` (new) |
| `sidequest-game/src/tension_tracker.rs` | 803 | `sidequest/game/tension_tracker.py` (new) |
| `sidequest-game/src/combatant.rs` | 152 | `sidequest/game/combatant.py` (new — `typing.Protocol`) |
| `sidequest-server/src/dispatch/response.rs` (combat) | ~200 | `sidequest/server/dispatch/confrontation.py` (new) |
| `sidequest-server/src/dispatch/tropes.rs:179-181` | ~3 | extend existing dispatch; resolve-from-trope |
| `sidequest-server/src/dispatch/aside.rs` (combat strip) | ~50 | extend existing aside dispatch |
| `sidequest-server/src/dispatch/state_mutations.rs:39` | ~2 | `in_combat()` helper on dispatch ctx |
| `sidequest-telemetry/src/lib.rs` (combat watchers) | ~50 | extend `sidequest/telemetry/spans.py` |

### Component flow

```
PLAYER_ACTION
    ↓
orchestrator.process_action(TurnContext)
    ↓
  [in_combat?]  →  yes: XP award = 25 (state_mutations)
    ↓
narrator prompt includes:
  - encounter_summary (Valley zone)          ← from GameSnapshot.encounter (typed)
  - pacing_hint (Early zone)                 ← from TensionTracker.tick(...)
  - world_context, opening_directive, etc.   ← existing Phase 1/2 wiring
    ↓
narration response
    ↓
game_patch extraction
    ↓
encounter delta applied to StructuredEncounter
    ↓
  [resolved?]  →  yes: emit resolution message + lore mint
    ↓
ResourcePool.apply_patch(...) for each declared resource
    ↓
  [threshold crossed?]  →  mint_threshold_lore → LoreStore
    ↓
OTEL: combat.tick, combat.ended, encounter.phase_transition
    ↓
STATE_PATCH + broadcast
```

### Key type seam

`GameSnapshot.encounter` flips from `dict | None` to `StructuredEncounter | None` in 42-1. Every `snapshot.encounter["key"]` dict-access in the codebase must migrate to attribute access. The 42-1 wiring check lists these; 42-4 finishes the migration on dispatch-side consumers.

### Test porting discipline

Per execution-strategy spec §2: Rust test file is the behavioural contract. Translations are mechanical — every Rust test becomes one pytest function with the same name. Idiomatic rewrites are forbidden during the port. TensionTracker fixture parity is load-bearing — 42-3 generates fixtures from Rust via a `cargo run --example` export rather than hand-transcribing the classification tables.

### OTEL span-name contract

Combat span names (`combat.tick`, `combat.ended`, `combat.player_dead`, `encounter.phase_transition`, `encounter.resolved`) are an external contract — the GM panel queries them by name for Sebastien's mechanical visibility. 42-4 enforces byte-identical names via a span-catalog parity test that reads Rust source.

### Deliberate non-goals

Explicit exclusions so scope does not creep:

- **Chase cinematography** (`chase_depth.rs`, 896 LOC) — skipped per Keith's 2026-04-20 decision; separate chase-polish pass later
- **Scenario engine** (belief_state, gossip, clue_activation, accusation, faction_agenda) — Phase 5
- **Advancement trees / affinity tiers** — Phase 6
- **CLIs** (encountergen, loadoutgen, namegen, promptpreview, validate) — Phase 7
- **Sealed-letter turn dispatcher** — ADR-077; Epic 42 honours `per_actor_state` shape but does not port the lookup logic

## Cross-Epic Dependencies

**Depends on:**
- Epic 41 (ADR-082 Phases 0-2) — provides Python scaffold, `GameSnapshot` base, orchestrator + narrator prompt zones, `EdgePool` types, session persistence. All 11 stories merged.
- Epic 39 (authored advancement effects) — Rust-ahead; provides `EdgePool` / edge-fraction semantics already ported forward. No blocking dependency; Phase 3 reuses ported fragments.

**Depended on by:**
- **Phase 4 (chase cinematography)** — deferred; will layer on `StructuredEncounter.chase(...)` which ships in 42-1
- **Phase 5 (scenario engine)** — scenarios fire pressure events that can instantiate encounters; requires typed encounter model
- **Phase 6 (advancement + edges)** — advancement-time edge math; requires `Combatant` protocol surfaced
- **Phase 7 (CLIs)** — `encountergen` CLI consumes `StructuredEncounter.combat(...)` construction

**Out-of-epic load-bearing assumption:** The narrator prompt's Early and Valley zones (from Epic 41) are stable enough to register `pacing_hint` and `encounter_summary` sections without conflict. If Phase 3 discovers the prompt zone contract needs revision, that is a 41-N follow-up, not scope creep into 42.
