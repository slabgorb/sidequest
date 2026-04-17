---
story_id: "38-10"
jira_key: "NO_JIRA"
epic: "38"
workflow: "wire-first"
---

# Story 38-10: Tail-chase starting state — author duel_02.md with tail_chase geometry and a second 16-cell interaction table, proving the confrontation generalizes beyond merge

## Story Details

- **ID:** 38-10
- **Jira Key:** NO_JIRA
- **Epic:** 38 — Dogfight Subsystem — Sealed-Letter Fighter Combat via StructuredEncounter
- **Workflow:** wire-first
- **Points:** 3
- **Stack Parent:** none

## Acceptance Criteria

**AC1: Tail-chase initial descriptor authored**
- `descriptor_schema.yaml` starting state `tail_chase` promoted from `future` to `mvp`
- Initial descriptor defined: pursuer (Red) has `target_bearing: "12"`, `target_aspect: tail_on`, `gun_solution: false` (not yet in firing solution — close but not locked); evader (Blue) has `target_bearing: "06"`, `target_aspect: head_on`
- Starting energy: both 60 (same as merge — the geometry is different, not the resource)
- Verify: the initial descriptor is consistent with the merge state's field schema

**AC2: 16-cell interaction table authored**
- All 16 `(red_maneuver, blue_maneuver)` pairs covered for tail_chase geometry
- Each cell has: `pair`, `name`, `shape`, `red_view`, `blue_view`, `narration_hint`
- The table reflects asymmetric geometry: Red is the pursuer, Blue is the evader
- The RPS balance should differ from merge: in a tail chase, evasive maneuvers (bank) are more valuable for the evader, and passive (straight) for the pursuer is more rewarding than in a merge
- Verify: 16 cells present, all 4x4 pairs covered, no duplicates

**AC3: duel_02.md playtest scaffold created**
- Follows the same protocol as `duel_01.md`: sealed-letter commits, GM lookup, per-pilot narration, debrief
- Opening narration describes the tail-chase geometry (one ship behind the other, not head-on)
- Debrief section includes the same calibration tag framework and go/no-go assessment
- Verify: scaffold is structurally identical to `duel_01.md` with tail-chase-specific content

**AC4: Narration hints reflect asymmetric geometry**
- Pursuer narration hints describe chasing, closing, lining up shots
- Evader narration hints describe being chased, breaking free, desperate reversal attempts
- Neither pilot's hints reference the other pilot's private state
- Verify: read all 16 narration hints and confirm they consistently frame Red as pursuer and Blue as evader

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-17T01:53:36Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-16 | 2026-04-17T01:44:50Z | 25h 44m |
| red | 2026-04-17T01:44:50Z | 2026-04-17T01:47:33Z | 2m 43s |
| green | 2026-04-17T01:47:33Z | 2026-04-17T01:51:55Z | 4m 22s |
| review | 2026-04-17T01:51:55Z | 2026-04-17T01:53:36Z | 1m 41s |
| finish | 2026-04-17T01:53:36Z | - | - |

## Sm Assessment

**Routing:** Content authoring story proving system generalizability. Wire-first workflow (user override). Phased: setup → red → green → review → finish.

**Scope:** 3-point story — author tail-chase interaction table (16 cells), duel_02.md scaffold, update descriptor_schema.yaml. Proves the sealed-letter system works with asymmetric starting geometry, not just head-on merge.

**Repos:** content (sidequest-content)
**Branch:** feat/38-10-tail-chase-starting-state
**Next:** RED phase → Radar (TEA) writes validation tests for tail-chase content.

## Delivery Findings

No upstream findings yet.

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- No upstream findings during code review.

### TEA (test design)
- No upstream findings during test design.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations from spec" → ✓ ACCEPTED by Reviewer: Tests validate all 4 ACs structurally.
- Dev "No deviations from spec" → ✓ ACCEPTED by Reviewer: Content follows the story context's asymmetric geometry spec faithfully. RPS balance is distinct from merge as required.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Skipped | proportional | N/A | Pure content, no Rust in diff |
| 2 | reviewer-edge-hunter | Skipped | proportional | N/A | YAML content, no code edge cases |
| 3 | reviewer-silent-failure-hunter | Skipped | proportional | N/A | No failure paths in content |
| 4 | reviewer-test-analyzer | Skipped | proportional | N/A | 8 tests reviewed manually |
| 5 | reviewer-comment-analyzer | Skipped | proportional | N/A | YAML comments reviewed inline |
| 6 | reviewer-type-design | Skipped | proportional | N/A | No type changes |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | proportional | N/A | No Rust code to check rules against |

**All received:** Yes (all skipped — pure content story, no Rust code in diff)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** YAML interactions_tail_chase.yaml → load_interaction_table (verified by test) → InteractionTable with 16 cells, starting_state=tail_chase → cells carry asymmetric gun_solution (Red:8, Blue:4) → narration hints frame pursuer/evader consistently.

**Pattern observed:** [VERIFIED] Table follows exact same cell schema as merge table (pair, name, shape, red_view, blue_view, narration_hint, hit_severity). New table loads through existing loader without any engine changes — this IS the generalizability proof.

**Error handling:** N/A — content files, no error paths.

**Observations:**
1. [VERIFIED] 16 cells, all 4x4 pairs, no duplicates. Loads through load_interaction_table.
2. [VERIFIED] Asymmetric balance: Red 8 shots, Blue 4. Evader's only offense is reversal (kill_rotation).
3. [VERIFIED] Hit severity on all gun_solution cells. Distribution: 1 devastating (snap shot on flee), 4 clean, 5 graze.
4. [VERIFIED] Narration hints consistently frame Red as pursuer, Blue as evader. No cross-state leakage.
5. [VERIFIED] duel_02.md scaffold structurally identical to duel_01.md with tail-chase content.
6. [VERIFIED] descriptor_schema.yaml tail_chase promoted to mvp with all required fields.

[EDGE] N/A. [SILENT] N/A. [TEST] Reviewed manually. [DOC] Comments reviewed inline. [TYPE] N/A. [SEC] N/A. [SIMPLE] N/A. [RULE] N/A — no Rust code.

### Devil's Advocate

Is the pursuer advantage too strong? Red has 8 gun_solution cells vs Blue's 4, and straight/straight gives Red a clean hit for doing nothing. In the merge table, straight/straight is dull (no shots). In tail-chase, the evader is punished for passivity — this feels correct (you can't just fly straight when someone is behind you), but it means the evader's dominant strategy is always bank (break turn). If bank is always the right call, the RPS collapses for Blue. The save is that bank/bank gives Red a graze (anticipated the break), so the evader can't spam bank safely either. The design tension holds: Blue must mix bank (safe but predictable) with kill_rotation (risky reversal) to stay alive. The calibration playtest (future duel_02 runs) will validate this in practice.

**Handoff:** To Hawkeye (SM) for finish-story — LAST STORY IN EPIC 38

## TEA Assessment

**Tests Required:** Yes
**Reason:** Content authoring story with specific structural requirements — needs schema validation

**Test Files:**
- `sidequest-api/crates/sidequest-genre/tests/tail_chase_story_38_10_tests.rs` — 8 tests covering 4 ACs

**Tests Written:** 8 tests covering 4 ACs
**Status:** RED (8/8 failing — content files don't exist yet)

**Test Breakdown:**
| Test | AC | What it validates |
|------|-----|-------------------|
| `descriptor_schema_has_tail_chase_mvp_with_initial_descriptor` | AC-1 | tail_chase promoted to mvp with all fields |
| `tail_chase_table_exists_and_loads` | AC-2 | File exists, starting_state = tail_chase |
| `tail_chase_table_has_16_cells` | AC-2 | 4x4 grid complete |
| `tail_chase_table_covers_all_4x4_pairs` | AC-2 | All maneuver combinations present |
| `tail_chase_table_consumes_same_maneuvers_as_merge` | AC-2 | Same 4 maneuvers |
| `tail_chase_has_asymmetric_gun_solutions` | AC-2 | Red (pursuer) has more shots than Blue (evader) |
| `duel_02_scaffold_exists` | AC-3 | Scaffold has Turn 1, Debrief, Go/no-go sections |
| `tail_chase_table_loads_standalone` | wiring | Table loads + all 16 narration hints present (AC-4 structural) |

**Handoff:** To Dev (Winchester) — author all tail-chase content files

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-content/genre_packs/space_opera/dogfight/descriptor_schema.yaml` — Promoted tail_chase from `future` to `mvp`, authored initial_descriptor with pursuer-behind-evader geometry
- `sidequest-content/genre_packs/space_opera/dogfight/interactions_tail_chase.yaml` — New 16-cell interaction table with asymmetric pursuer/evader RPS balance. Red (pursuer) has 8 gun_solution cells, Blue (evader) has 4 — asymmetry verified by test.
- `sidequest-content/genre_packs/space_opera/dogfight/playtest/duel_02.md` — Paper playtest scaffold structurally identical to duel_01.md with tail-chase-specific content, opening narration, and tail-chase debrief questions

**RPS Balance (tail-chase):**
- Pursuer straight vs evader straight = pursuer scores (clean) — fleeing doesn't work at close range
- Pursuer straight vs evader bank = evader escapes — break turn is the primary defense
- Pursuer bank vs evader bank = pursuer maintains pursuit (graze) — anticipated the break
- Evader kill_rotation = high-risk reversal, rewarded only against pursuer bank
- Mutual kill_rotation = head-on knife fight (both clean) — tail-chase collapses to merge-like geometry

**Tests:** 8/8 passing (GREEN), plus 13/13 38-4 regression
**Branch:** feat/38-10-tail-chase-starting-state (pushed: api + content)

**Handoff:** To Colonel Potter (Reviewer)