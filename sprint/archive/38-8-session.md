---
story_id: "38-8"
jira_key: "NO_JIRA"
epic: "38"
workflow: "wire-first"
---

# Story 38-8: Extend-and-return rule

## Story Details

- **ID:** 38-8
- **Jira Key:** NO_JIRA
- **Workflow:** wire-first
- **Stack Parent:** none
- **Repos:** sidequest-content
- **Branch:** feat/38-8-extend-and-return-rule

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-17T01:24:04Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-16T21:05Z | 2026-04-17T01:04:44Z | 3h 59m |
| red | 2026-04-17T01:04:44Z | 2026-04-17T01:13:02Z | 8m 18s |
| green | 2026-04-17T01:13:02Z | 2026-04-17T01:19:35Z | 6m 33s |
| review | 2026-04-17T01:19:35Z | 2026-04-17T01:24:04Z | 4m 29s |
| finish | 2026-04-17T01:24:04Z | - | - |

## Story Summary

After a sealed-letter turn resolves with no hit (neither pilot's `gun_solution` true) and at least one actor's descriptor has `closure: opening_fast`, the engagement has broken apart too far. The extend-and-return rule resets both actors to the merge starting state (closing_fast/head_on/close) while preserving current energy. This creates the 3-exchange duel arc without requiring additional interaction tables for every post-turn geometry.

The rule can be implemented as:
1. **Engine rule** in `sidequest-server/src/dispatch/sealed_letter.rs` — post-resolution step in SealedLetterLookup
2. **Content clause** in `sidequest-content/genre_packs/space_opera/dogfight/interactions_mvp.yaml` — post_turn section

ADR-077 recommends the engine rule approach with content override capability.

## AC Verification

**AC1: Reset triggers on correct conditions**
- After `[straight, straight]` turn with both at `closure: opening` (NOT opening_fast), rule should NOT fire
- After `[kill_rotation, straight]` with both at `closure: opening_fast` and no hit landed, rule SHOULD fire

**AC2: Reset preserves energy, clears geometry**
- Post-reset state: `target_bearing: "12"`, `target_range: close`, `target_aspect: head_on`, `closure: closing_fast`, `gun_solution: false`
- Energy carries over from previous resolved state (a pilot with 30 energy keeps 30 after reset, not reset to 60)

**AC3: Documented for paper playtest**
- Rule expressible in plain language for duel_01.md GM

## Sm Assessment

**Routing:** Content/engine story for the extend-and-return mechanic. Wire-first workflow (user override). Phased: setup → red → green → review → finish.

**Scope:** 1-point story — post-turn reset when no hit and opening_fast closure. Prevents infinite drift-apart. Can be engine rule or content clause per ADR-077.

**Repos:** content (primary), possibly api for engine rule
**Branch:** feat/38-8-extend-and-return-rule
**Next:** RED phase → Radar (TEA) writes failing tests.

## Delivery Findings

No upstream findings yet.

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): Extract hardcoded merge starting-state values from descriptor_schema.yaml at load time instead of inlining literals. Affects `sidequest-api/crates/sidequest-server/src/dispatch/sealed_letter.rs` (ADR-068 magic literal extraction). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Add negative OTEL assertion to at least one "does not trigger" test. Affects `sidequest-api/crates/sidequest-server/tests/integration/extend_return_story_38_8_tests.rs` (verify 0 extend_and_return spans on non-trigger paths). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations from spec" → ✓ ACCEPTED by Reviewer: Tests correctly cover all 3 ACs with boundary conditions.
- Dev "No deviations from spec" → ✓ ACCEPTED by Reviewer: Implementation follows ADR-077 engine rule recommendation. Hardcoded values are a style concern (ADR-068), not a spec deviation.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Engine rule with post-resolution behavior — needs boundary condition tests

**Test Files:**
- `sidequest-api/crates/sidequest-server/tests/integration/extend_return_story_38_8_tests.rs` — 7 tests covering 3 ACs + OTEL wiring

**Tests Written:** 7 tests covering 3 ACs
**Status:** RED (3 failing, 4 passing — negative cases correctly pass because no reset logic exists)

**Test Breakdown:**
| Test | AC | What it validates |
|------|-----|-------------------|
| `extend_return_triggers_on_opening_fast_no_hit` | AC-1 | Reset fires when opening_fast + no gun_solution |
| `extend_return_does_not_trigger_on_opening_without_fast` | AC-1 | No reset on plain "opening" closure |
| `extend_return_does_not_trigger_when_hit_landed` | AC-1 | No reset when gun_solution=true |
| `extend_return_does_not_trigger_on_mutual_hits` | AC-1 | No reset on mutual gunline |
| `extend_return_preserves_energy_on_reset` | AC-2 | Energy carries over, not reset to 60 |
| `extend_return_resets_all_geometric_fields` | AC-2 | All 5 geometric fields reset to merge values |
| `extend_return_emits_otel_span_on_reset` | wiring | OTEL span for GM panel visibility |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 Tracing/OTEL | `emits_otel_span_on_reset` | failing (RED) |
| #6 Test quality | all assertions verified meaningful | passing (self-check) |

**Rules checked:** 2 of 6 applicable lang-review rules have test coverage
**Self-check:** 0 vacuous tests found

**Handoff:** To Dev (Winchester) for implementation — add post-resolution extend-and-return logic in resolve_sealed_letter_lookup

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-server/src/dispatch/sealed_letter.rs` — Added `maybe_apply_extend_and_return()` post-resolution function. Checks no-hit + opening_fast conditions, resets geometric fields to merge starting state, preserves energy, emits OTEL span.

**Implementation approach:** Engine rule per ADR-077 recommendation. Added as a post-resolution step called after delta application in `resolve_sealed_letter_lookup`. The function reads resolved `per_actor_state` to check conditions, then overwrites 5 geometric fields (target_bearing, target_range, target_aspect, closure, gun_solution) while leaving energy fields untouched.

**Tests:** 7/7 passing (GREEN), plus 13/13 38-5 regression suite (no regressions)
**Branch:** feat/38-8-extend-and-return-rule (pushed)

**Handoff:** To Colonel Potter (Reviewer)

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | No | timeout | N/A | Tests independently verified 7/7 + 13/13 GREEN |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 1, dismissed 2, deferred 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | confirmed 1, dismissed 1, deferred 1 |
| 4 | reviewer-test-analyzer | Skipped | not spawned | N/A | Small diff, proportional review |
| 5 | reviewer-comment-analyzer | Skipped | not spawned | N/A | Small diff, proportional review |
| 6 | reviewer-type-design | Skipped | not spawned | N/A | No new types in diff |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 2 |

**All received:** Yes (3 returned with findings, 1 timed out but verified independently, 5 skipped/disabled)
**Total findings:** 4 confirmed, 3 dismissed, 3 deferred

### Finding Triage

**Confirmed (non-blocking):**
1. [RULE] Hardcoded merge starting state values — sealed_letter.rs:314-339. Five string literals instead of loading from descriptor_schema. **MEDIUM** — current values are correct and tested; drift risk is for future schema changes. ADR-068 applies.
2. [RULE] Missing negative OTEL assertion in "does not trigger" tests. **MEDIUM** — positive OTEL test exists; negative OTEL would catch spurious emission.
3. [EDGE] Stale per_actor_state if apply_view_deltas returns false — sealed_letter.rs:172. **MEDIUM** — edge case requires content authoring error, already logged by existing OTEL warning.
4. [SILENT] gun_solution/closure absence vs false conflation — sealed_letter.rs:290. **MEDIUM** — only relevant on first-turn-before-delta edge, which is structurally impossible in the current flow (deltas always apply before extend-and-return check).

**Dismissed:**
1. gun_solution vs hit_severity semantic distinction — gun_solution IS the hit indicator per AC-1, confirmed by story context. Not a bug.
2. Symmetric reset on asymmetric closure — intentional per the paper playtest ("both sides re-merge"). The engagement geometry is shared.
3. Quoted "true" string edge case — low confidence, YAML authoring errors at this level would be caught by genre pack validation.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** committed maneuvers → cell lookup → delta application (red_view/blue_view → per_actor_state) → maybe_apply_extend_and_return checks gun_solution + closure in resolved per_actor_state → resets 5 geometric fields → OTEL span emitted. Safe because the function reads resolved state only after delta application completes.

**Pattern observed:** [VERIFIED] Post-resolution hook pattern — `maybe_apply_extend_and_return` is called after `apply_view_deltas`, reads resolved state, conditionally mutates. Consistent with the existing handler structure. sealed_letter.rs:170.

**Error handling:** [VERIFIED] Early returns on no-hit (line 295) and no-opening_fast (line 306) are correct no-ops. The function has no error path because it's a conditional mutation, not a validation step.

**Observations:**
1. [VERIFIED] Condition logic correct — `any_hit` uses `gun_solution` bool from per_actor_state. `unwrap_or(false)` is safe: absent gun_solution means cell had no shot. Lines 288-294.
2. [VERIFIED] Energy preservation — only 5 geometric fields are written. viewer_energy/target_energy are not in the insert list. Test `extend_return_preserves_energy_on_reset` verifies explicitly.
3. [VERIFIED] OTEL span fires on reset — `encounter.sealed_letter.extend_and_return` with encounter_type. Test `extend_return_emits_otel_span_on_reset` verifies count == 1.
4. [VERIFIED] No regression on 38-5 — all 13 existing sealed-letter tests pass. The post-resolution hook doesn't fire for the 38-5 test fixture because none of its cells produce opening_fast.
5. [MEDIUM] Hardcoded merge values — acknowledged, deferred to delivery finding per ADR-068.

[EDGE] Edge cases: stale state on failed delta application is structurally unlikely and already logged.
[SILENT] Silent failures: absent vs false conflation is safe in current flow (deltas always apply first).
[TEST] Not spawned — proportional to diff size.
[DOC] Not spawned — code comments are accurate.
[TYPE] Not spawned — no new types.
[SEC] Disabled.
[SIMPLE] Disabled.
[RULE] Two violations confirmed: hardcoded values (#3) and missing negative OTEL test (#6). Both non-blocking.

### Rule Compliance

| Rule | Instances | Verdict |
|------|-----------|---------|
| #1 Silent errors | 4 checked | PASS |
| #2 non_exhaustive | SealedLetterOutcome has it | PASS |
| #3 Hardcoded values | 5 merge literals | MEDIUM — delivery finding |
| #4 Tracing | OTEL span on reset path | PASS |
| #6 Test quality | Missing negative OTEL assertion | MEDIUM — delivery finding |
| #8 Deserialize bypass | No Deserialize in diff | N/A |
| #9 Public fields | No new public fields | N/A |

### Devil's Advocate

What if a future content author adds a cell where one actor gets gun_solution=true but the resolution is mechanically a "miss" (no damage)? The extend-and-return rule treats gun_solution=true as "hit landed" and suppresses the reset, even though no damage was actually applied. This would cause the engagement to drift apart without resetting — the fighters fly off into infinity. The fix would be to gate on actual damage application, not just gun_solution presence. But the current content (story 38-7) always pairs gun_solution with hit_severity and damage, so the conflation is safe today. The AC explicitly says "no hit landed" means "neither actor's gun_solution was true" — the implementation matches the spec exactly.

What about the hardcoded values? If story 38-10 (tail_chase starting state) introduces a different starting state, this function won't know. It always resets to merge. But 38-10 is explicitly about "proving generalizability" — it would need to parameterize the reset state. The hardcoded merge values are correct for the MVP single-starting-state dogfight.

**Handoff:** To Hawkeye (SM) for finish-story