---
story_id: "16-4"
jira_key: "none"
epic: "16"
workflow: "tdd"
---
# Story 16-4: Migrate combat as confrontation — CombatState becomes a confrontation type preset

## Story Details
- **ID:** 16-4
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 16 — Genre Mechanics Engine — Confrontations & Resource Pools
- **Repository:** sidequest-api (Rust backend)
- **Points:** 5
- **Priority:** p1
- **Status:** in-progress

## Context

Epic 16 builds two missing generic subsystems: Confrontation (universal structured encounter engine) and ResourcePool (persistent named resources).

Story 16-4 refactors the existing CombatState into a specialization of the new ConfrontationState type system introduced in 16-2.

**Dependency chain:**
- 16-1 (Narrator resource injection) — COMPLETE
- 16-2 (Confrontation trait + ConfrontationState) — COMPLETE
- 16-3 (Confrontation YAML schema) — COMPLETE
- 16-4 (Migrate combat as confrontation) ← current
- 16-5 (Migrate chase as confrontation)
- etc.

## What This Story Does

**Migrate combat as confrontation** expresses existing combat mechanics (rounds, damage log, turn order, status effects) as a confrontation type. The metric is HP, beats are attack/defend/ability actions, resolution is someone hitting 0.

### Current State
- `CombatState` (combat.rs) — fully implemented with 198 LOC
  - Owns: round tracking, damage log, status effects, turn order, available actions, drama weight
  - Used by: TurnManager, NarrationPipeline, UI overlays
  - Tested: Full suite of combat mechanics tests
- `ConfrontationState` (from 16-2) — exists as the universal encounter container
- No behavioral changes needed — this is pure refactoring

### What Needs to Happen

1. **Define combat as a confrontation type preset:**
   - Metric: HP (descending to 0)
   - Beats: Attack, Defend, Ability (mapped to existing action names)
   - Turn order and damage log become part of beat history
   - Status effects persist as secondary stats
   - Resolution: any actor reaches 0 HP

2. **Map existing CombatState fields to ConfrontationState:**
   - `round` → beat count / timeline position
   - `damage_log` → beat history with damage detail
   - `effects` → secondary_stats block
   - `in_combat`, `turn_order`, `current_turn`, `available_actions` → standard confrontation flow
   - `drama_weight` → confrontation metadata (preserved)

3. **CombatState as convenience alias:**
   - `type CombatState = ConfrontationState` (with type = "combat" preset)
   - Or struct wrapping ConfrontationState with as_combat_view() → CombatState
   - All existing code continues to work unchanged

4. **All existing combat tests pass:**
   - Round advancement
   - Damage logging
   - Status effect application and expiry
   - Turn order management
   - Available actions filtering

### Implementation Strategy

- **Phase 1 (RED):** Write acceptance tests that verify combat mechanics still work when expressed as a confrontation
- **Phase 2 (GREEN):** Implement the mapping layer; make CombatState an alias or wrapper
- **Phase 3 (VERIFY):** Ensure all existing combat and integration tests pass
- **No breaking changes** — all public APIs remain compatible

## Workflow Phases

| Phase | Owner | Status |
|-------|-------|--------|
| setup | sm | in-progress |
| red | tea | pending |
| green | dev | pending |
| spec-check | architect | pending |
| verify | tea | pending |
| review | reviewer | pending |
| spec-reconcile | architect | pending |
| finish | sm | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-31T18:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-31T18:45Z | — | — |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings yet.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.
