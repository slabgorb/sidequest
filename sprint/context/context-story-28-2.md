---
parent: context-epic-28.md
---

# Story 28-2: OTEL for StructuredEncounter

## Business Context

StructuredEncounter is about to become the sole runtime model for all encounters.
Before routing real traffic through it, every mechanical decision must emit OTEL
watcher events. The game crate currently has exactly 2 watcher event emissions
(both in persistence.rs). 71 modules of game mechanics run dark. This story
establishes the pattern for game-crate OTEL and instruments StructuredEncounter.

## Technical Approach

### Step 1: Add sidequest-telemetry dependency to sidequest-game

`sidequest-telemetry` is already a standalone crate with no circular dependency risk.
Add it to `sidequest-game/Cargo.toml`. This unlocks WatcherEventBuilder for the
entire game crate.

### Step 2: Instrument StructuredEncounter methods in encounter.rs

**apply_beat()** (line 446):
```
encounter.beat_applied:
  encounter_type, beat_id, stat_check, metric_before, metric_after,
  phase_before, phase_after, resolved, threshold_crossed
```

**Resolution check** (inside apply_beat, line 493):
```
encounter.resolved:
  encounter_type, total_beats, outcome, final_metric
```

**Phase transitions** (inside apply_beat, line 498):
```
encounter.phase_transition:
  encounter_type, old_phase, new_phase, beat_number
```

**escalate_to_combat()** (line 517):
```
encounter.escalated:
  from_type, to_type, actors
```

### Step 3: Instrument CreatureCore::apply_hp_delta()

This is the single most dangerous blind spot. Every damage/heal in the game
flows through this 3-line function. Add an event BEFORE the clamp:

```
creature.hp_delta:
  name, old_hp, new_hp, delta, max_hp, clamped (bool)
```

File: `sidequest-game/src/creature_core.rs:44`

## Key Files

| File | Action |
|------|--------|
| `sidequest-game/Cargo.toml` | Add `sidequest-telemetry` dependency |
| `sidequest-game/src/encounter.rs` | Add WatcherEvent emissions to apply_beat, escalate_to_combat |
| `sidequest-game/src/creature_core.rs` | Add WatcherEvent to apply_hp_delta |

## Acceptance Criteria

| AC | Detail | Wiring Verification |
|----|--------|---------------------|
| Telemetry dep | sidequest-game/Cargo.toml lists sidequest-telemetry | `grep "sidequest-telemetry" sidequest-game/Cargo.toml` |
| apply_beat OTEL | Every call to apply_beat() emits encounter.beat_applied | Grep: WatcherEventBuilder with "beat_applied" in encounter.rs |
| Resolution OTEL | Resolution emits encounter.resolved | Grep: WatcherEventBuilder with "resolved" in encounter.rs |
| Phase OTEL | Phase transitions emit encounter.phase_transition | Grep: WatcherEventBuilder with "phase_transition" in encounter.rs |
| HP delta OTEL | apply_hp_delta emits creature.hp_delta | Grep: WatcherEventBuilder with "hp_delta" in creature_core.rs |
| Builds clean | `cargo build -p sidequest-game` succeeds | Build verification |
| Wiring | WatcherEventBuilder appears in non-test code in encounter.rs and creature_core.rs | `grep -v test` verification |

## Scope Boundaries

**In scope:** Telemetry dependency, OTEL for encounter.rs and creature_core.rs
**Out of scope:** OTEL for other game crate modules (tropes, disposition, etc.) — that's 28-12
