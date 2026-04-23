---
story_id: "16-5"
jira_key: "none"
epic: "16"
workflow: "tdd"
---
# Story 16-5: Migrate chase as confrontation — ChaseState becomes a confrontation type preset

## Story Details
- **ID:** 16-5
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 16 — Genre Mechanics Engine — Confrontations & Resource Pools
- **Repository:** sidequest-api (Rust backend)
- **Branch:** feat/16-5-migrate-chase-confrontation
- **Points:** 5
- **Priority:** p1
- **Status:** in-progress

## Context

Epic 16 builds two missing generic subsystems: Confrontation (universal structured encounter engine) and ResourcePool (persistent named resources).

Story 16-5 refactors the existing ChaseState into a specialization of the new StructuredEncounter type system introduced in 16-2. This mirrors story 16-4 (Migrate combat as confrontation) but for chase mechanics.

**Dependency chain:**
- 16-1 (Narrator resource injection) — COMPLETE
- 16-2 (Confrontation trait + ConfrontationState) — COMPLETE
- 16-3 (Confrontation YAML schema) — COMPLETE
- 16-4 (Migrate combat as confrontation) — COMPLETE
- 16-5 (Migrate chase as confrontation) ← current
- etc.

## What This Story Does

**Migrate chase as confrontation** expresses existing chase mechanics (separation, escape threshold, chase beats, RigStats, fuel, terrain modifiers, multi-actor roles) as a confrontation type. The metric is separation, beats are the existing chase beat system, secondary stats are RigStats.

### Current State
- `ChaseState` (chase.rs) — fully implemented with 287 LOC
  - Owns: separation distance, goal, rounds, beat tracking, structured phase, rig stats, crew actors, outcome
  - Used by: NarrationPipeline, TurnManager, UI overlays, save/load
  - Tested: Full suite of chase mechanics tests
  - Chase Depth (C1-C5): Rig damage, multi-actor roles, beat system, terrain modifiers, cinematography
- `StructuredEncounter` (encounter.rs) — already has `chase()` constructor and `from_chase_state()` migration
- Reference: story 16-4 (Combat migration) is the pattern to follow

### What Needs to Happen

1. **Write acceptance tests** (RED phase):
   - Chase encounter created with `StructuredEncounter::chase()` maintains all chase semantics
   - Chase encounter created from existing `ChaseState` via `from_chase_state()` preserves all fields
   - All existing chase.rs tests continue to pass (no behavioral changes)
   - Chase Depth features (C1-C5) remain functional when expressed through StructuredEncounter

2. **Verify field mappings** (already partially done in encounter.rs):
   - `separation_distance` → `metric.current` (name="separation", Ascending direction)
   - `goal` → `metric.threshold_high`
   - `rig` → `secondary_stats` via `SecondaryStats::from_rig_stats()`
   - `actors` → `actors` (with roles mapped to strings)
   - `beat` → `beat`
   - `structured_phase` → `structured_phase` (ChasePhase → EncounterPhase)
   - `outcome` → `outcome` (formatted as string)
   - `resolved` → `resolved` (!chase.is_resolved() → encounter.resolved)

3. **ChaseState as convenience alias or wrapper** (choice based on wiring):
   - Option A: Keep ChaseState as-is, add migration layer to StructuredEncounter (already done)
   - Option B: Make ChaseState a type alias or thin wrapper with convenience accessors
   - All existing code continues to work unchanged

4. **All existing chase and chase_depth tests pass**:
   - Round recording and resolution
   - Rig damage tracking and tier changes
   - Beat advancement and phase progression
   - Terrain modifiers and outcome checking
   - Actor assignment and role management

### Implementation Strategy

- **Phase 1 (RED):** Write acceptance tests that verify chase mechanics still work when expressed as a StructuredEncounter
- **Phase 2 (GREEN):** Ensure all existing chase tests pass (migration layer already exists in encounter.rs)
- **Phase 3 (VERIFY):** Run full test suite for chase, chase_depth, and new integration tests
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
**Phase Started:** 2026-04-04T17:45Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-04T17:45Z | — | — |

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
