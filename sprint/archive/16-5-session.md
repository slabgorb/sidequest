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
**Phase:** finish
**Phase Started:** 2026-04-04T12:30:43Z

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

### TEA (test design)
- **Conflict** (resolved): Story context originally specified type-alias refactor; Architect rewrote to bridge pattern ACs. All 5 rewritten ACs found already implemented: dispatch sync (mod.rs:1701), prompt injection (prompt.rs:275), save/load migration (state.rs:303 via GameSnapshotRaw), OTEL (prompt.rs:283). *Found by TEA during test design.*
- **Improvement** (non-blocking): 39 existing tests validate bridge mechanics comprehensively but have no test for the save/load migration path specifically (GameSnapshotRaw → GameSnapshot auto-populates encounter from chase). Affects `sidequest-game/tests/chase_as_confrontation_story_16_5_tests.rs` (could add explicit deserialization migration test). *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. All ACs were already implemented — no new code written.

### TEA (test design)
- **Original story context rewritten by Architect — spec conflict resolved**
  - Spec source: sprint/context/context-story-16-5.md (rewritten 2026-04-04)
  - Spec text: Original spec called for "type alias" refactor. Architect rewrote to bridge pattern with 5 new ACs (dispatch wiring, prompt, save/load, regression, OTEL).
  - Implementation: All 5 rewritten ACs found to be already implemented. Bridge pattern wired in dispatch (mod.rs:1701-1708), prompt injection (prompt.rs:275-298), save/load migration (state.rs:303-310 via GameSnapshotRaw), OTEL on prompt injection (prompt.rs:283-289). 39 existing tests cover bridge mechanics.
  - Rationale: No new failing tests needed — existing code satisfies all ACs. Chore bypass: coverage already exists.
  - Severity: minor (resolved by spec rewrite)
  - Forward impact: none — bridge pattern is the established pattern for all encounter type migrations

### Architect (reconcile)
- No additional deviations found.

TEA's deviation entry (spec rewrite from type-alias to bridge pattern) is accurate and complete:
- Spec source: verified — `sprint/context/context-story-16-5.md` exists and was rewritten by Architect on 2026-04-04
- Spec text: accurately describes the original vs rewritten spec
- Implementation: confirmed — all 5 rewritten ACs implemented in pre-existing code
- Forward impact: correct — bridge pattern is the established migration pattern (same as 16-4 combat)
- No AC deferrals — all 5 ACs marked DONE

Dev logged no deviations (no new code). Accurate — zero diff on branch.

## Reviewer Assessment

**Review Type:** Pass-through (zero diff, no PR)
**Verdict:** Approved — no code changes to review

**Rationale:** Branch `feat/16-5-migrate-chase-confrontation` has zero diff against `develop`. All 5 ACs are satisfied by code already merged to develop through prior story branches:

- AC-1 (dispatch sync): merged via playtest fixes branch
- AC-2 (prompt injection): merged via encounter wiring branches
- AC-3 (save/load migration): merged via story 16-2 (GameSnapshotRaw)
- AC-4 (39 tests pass): tests committed with implementation
- AC-5 (OTEL): merged via encounter wiring branches

**No PR needed.** The branch can be deleted — all work is already on develop.

**Findings:** None. The TEA deviation log correctly documents the spec rewrite. The Architect spec-check confirms alignment.

**Specialist Tags:**
- [TYPE] No type design issues — zero diff, no new types introduced on this branch.
- [RULE] No rule violations — zero diff, no new code to check against lang-review rules.
- [SILENT] No silent failure patterns — zero diff, no new error handling paths.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | N/A — zero diff | none | N/A |
| 2 | reviewer-type-design | Yes | N/A — zero diff | none | N/A |
| 3 | reviewer-security | Yes | N/A — zero diff | none | N/A |
| 4 | reviewer-test-analyzer | Yes | N/A — zero diff | none | N/A |
| 5 | reviewer-rule-checker | Yes | N/A — zero diff | none | N/A |
| 6 | reviewer-silent-failure-hunter | Yes | N/A — zero diff | none | N/A |

All received: Yes (all skipped — zero diff, no code to analyze)

### Reviewer
- No upstream findings during review.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

No code changes to review — skipping simplify. Branch `feat/16-5-migrate-chase-confrontation` has zero diff against `develop`.

**Overall:** simplify: clean (no changed files)

**Quality Checks:** N/A — no code changes
**Handoff:** To Reviewer for review phase

### TEA (verify)
- No upstream findings during test verification.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 5 ACs from the rewritten story context (context-story-16-5.md) are satisfied:

| AC | Spec | Code | Verdict |
|----|------|------|---------|
| AC-1 | Dispatch auto-populates encounter | dispatch/mod.rs:1701-1708 | Aligned |
| AC-2 | Narrator prompt uses encounter format | dispatch/prompt.rs:275-298 | Aligned |
| AC-3 | Old saves auto-populate from chase | state.rs:303-310 (GameSnapshotRaw) | Aligned |
| AC-4 | All existing tests pass | 39/39 pass | Aligned |
| AC-5 | OTEL on encounter sync | dispatch/prompt.rs:283-289 | Aligned |

**Note on AC-5:** The OTEL event fires at prompt injection time rather than at snapshot sync time. This is architecturally preferable — it confirms the encounter data reached the narrator, not just that it was synced internally. No mismatch.

**Deviation review:** TEA's deviation (spec rewrite) is properly documented with all 6 fields. Dev logged no deviations (no new code). Both are accurate.

**Decision:** Proceed to verify.

## Dev Assessment

**Implementation Complete:** Yes (no new code — all ACs pre-satisfied)
**Files Changed:** None
**Tests:** 39/39 passing (GREEN)
**Branch:** feat/16-5-migrate-chase-confrontation

**AC Verification:**
- AC-1: Dispatch sync confirmed at dispatch/mod.rs:1701-1708
- AC-2: Prompt injection confirmed at dispatch/prompt.rs:275-298
- AC-3: Save/load migration confirmed at state.rs:303-310 (GameSnapshotRaw)
- AC-4: 39/39 tests pass
- AC-5: OTEL encounter span at dispatch/prompt.rs:283-289

**Handoff:** To review phase — no code changes, purely a pipeline pass-through.

### Dev (implementation)
- No upstream findings during implementation.

## TEA Assessment

**Tests Required:** No (chore bypass — existing coverage satisfies all ACs)
**Reason:** All 5 ACs from Architect's rewritten spec are already implemented and tested.

**Existing Test File:**
- `sidequest-game/tests/chase_as_confrontation_story_16_5_tests.rs` — 39 tests, all passing

**AC Coverage:**

| AC | Status | Evidence |
|----|--------|----------|
| AC-1: Dispatch auto-populates encounter | Implemented | dispatch/mod.rs:1701-1708 |
| AC-2: Narrator prompt uses encounter format | Implemented | dispatch/prompt.rs:275-298 |
| AC-3: Old saves auto-populate from chase | Implemented | state.rs:303-310 (GameSnapshotRaw migration) |
| AC-4: All existing tests pass | Verified | 39/39 pass |
| AC-5: OTEL on encounter sync | Implemented | dispatch/prompt.rs:283-289 (encounter span at prompt injection) |

**Status:** GREEN (all ACs satisfied, 39 tests passing)

**Self-check:** 0 vacuous tests found. All 39 existing tests have meaningful assertions.

**Note:** Story was implemented across previous sessions but never formally completed through the TDD pipeline. The bridge infrastructure, dispatch wiring, prompt injection, save/load migration, and OTEL were built incrementally. This RED phase confirms no new tests needed.

**Handoff:** Skip Dev (no implementation needed) → proceed to review and finish.

## Sm Assessment

**Story:** 16-5 — Migrate chase as confrontation
**Readiness:** Ready for RED phase

- Session file created with full context and field mapping reference
- Branch `feat/16-5-migrate-chase-confrontation` created off develop in sidequest-api
- Epic 16 context freshly updated with current architecture state
- Dependencies satisfied: 16-1 through 16-4 all done
- StructuredEncounter already has `chase()` constructor and `from_chase_state()` — this story wires it end-to-end
- No Jira (personal project)
- Handoff to Fezzik (TEA) for RED phase