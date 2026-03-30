---
story_id: "6-5"
jira_key: "none"
epic: "6"
workflow: "tdd"
---
# Story 6-5: Wire faction agendas into scene directive — faction-driven events appear in narrator prompt

## Story Details
- **ID:** 6-5
- **Jira Key:** none (personal project, no Jira)
- **Epic:** 6 (Active World & Scene Directives — Living World That Acts On Its Own)
- **Workflow:** tdd
- **Stack Parent:** 6-4 (FactionAgenda model, completed)
- **Points:** 2
- **Priority:** p1
- **Repos:** sidequest-api

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T20:37:47Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27 | 2026-03-27T20:25:31Z | 20h 25m |
| red | 2026-03-27T20:25:31Z | 2026-03-27T20:27:34Z | 2m 3s |
| green | 2026-03-27T20:27:34Z | 2026-03-27T20:31:34Z | 4m |
| spec-check | 2026-03-27T20:31:34Z | 2026-03-27T20:32:00Z | 26s |
| verify | 2026-03-27T20:32:00Z | 2026-03-27T20:33:57Z | 1m 57s |
| review | 2026-03-27T20:33:57Z | 2026-03-27T20:37:17Z | 3m 20s |
| spec-reconcile | 2026-03-27T20:37:17Z | 2026-03-27T20:37:47Z | 30s |
| finish | 2026-03-27T20:37:47Z | - | - |

## Sm Assessment

Story 6-5 wires FactionAgenda (6-4, just completed) into SceneDirective (6-1, completed). 2-point TDD story — faction-driven events appear in narrator prompt via `SceneDirective.faction_events`. Straightforward integration. No blockers. Routing to TEA for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 2-point TDD integration story wiring FactionAgenda into SceneDirective

**Test Files:**
- `crates/sidequest-game/tests/wire_faction_agenda_story_6_5_tests.rs` — 10 tests across 5 sections

**Tests Written:** 10 tests covering: format_scene_directive accepts agendas parameter, dormant filtering, multiple active agendas, coexistence with stakes/hints, DirectiveSource::FactionEvent variant
**Status:** RED (compilation errors — format_scene_directive takes 3 args not 4, DirectiveSource::FactionEvent doesn't exist)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | DirectiveSource already has it; FactionEvent extends it | N/A (existing enum) |

**Rules checked:** 1 of 15 applicable (integration story, no new types with invariants)
**Self-check:** 0 vacuous tests found

### Dev Implementation Required

1. Add `&[FactionAgenda]` parameter to `format_scene_directive()`
2. Collect `scene_injection()` from non-dormant agendas into `faction_events`
3. Add `DirectiveSource::FactionEvent` variant to `DirectiveSource` enum

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/scene_directive.rs` — added `FactionAgenda` parameter, `DirectiveSource::FactionEvent`, faction_events collection
- `crates/sidequest-game/tests/scene_directive_story_6_1_tests.rs` — updated callers to pass `&[]`
- `crates/sidequest-agents/tests/wire_directive_story_6_9_tests.rs` — updated callers to pass `&[]`
- `crates/sidequest-agents/tests/scene_directive_weave_story_6_2_tests.rs` — updated callers to pass `&[]`

**Tests:** 53/53 passing (GREEN) — 9 new + 23 story-6-1 + 7 story-6-9 + 14 story-6-2
**Branch:** feat/6-5-wire-faction-agendas (pushed)

**Handoff:** To next phase (verify)

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 1

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication |
| simplify-quality | 1 finding | SceneDirective missing Debug/Clone derives (high) |
| simplify-efficiency | clean | No over-engineering |

**Applied:** 1 high-confidence fix — added `#[derive(Debug, Clone)]` to `SceneDirective`
**Flagged for Review:** 0
**Noted:** 0
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** All tests passing
**Handoff:** To Heimdall (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Story title: "Wire faction agendas into scene directive — faction-driven events appear in narrator prompt." Implementation adds `&[FactionAgenda]` parameter to `format_scene_directive()`, collects `scene_injection()` from non-dormant agendas into `faction_events`, and adds `DirectiveSource::FactionEvent`. All 44 existing tests from stories 6-1/6-2/6-9 pass unchanged (callers updated to `&[]`). Clean integration.

**Decision:** Proceed to verify

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Improvement** (non-blocking): `faction_events` in `SceneDirective` has no size cap unlike `mandatory_elements` (capped at 3). Add `DEFAULT_MAX_FACTION_EVENTS` with truncate, or sort by urgency and take top N. Affects `crates/sidequest-game/src/scene_directive.rs` (add cap to faction_events collection). *Found by Reviewer during code review.*

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | dismissed 2 (pre-existing from 6-1) |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 1 (MEDIUM unbounded events), dismissed 3 (pre-existing) |

**All received:** Yes (3 returned, 6 disabled via settings)
**Total findings:** 1 confirmed (MEDIUM), 5 dismissed (pre-existing)

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `DirectiveSource::FactionEvent` correctly extends `#[non_exhaustive]` enum — scene_directive.rs:46. Label at line 56. Rule #2 compliant.
2. [VERIFIED] `format_scene_directive` accepts `&[FactionAgenda]` — scene_directive.rs:98. Clean parameter addition.
3. [VERIFIED] `filter_map(scene_injection())` correctly filters dormant agendas — scene_directive.rs:120-123. None → filtered, Some → collected.
4. [VERIFIED] `SceneDirective` now derives `Debug, Clone` — scene_directive.rs:81. Consistency with sibling types.
5. [VERIFIED] All 44 existing tests updated with `&[]` — no regressions across stories 6-1, 6-2, 6-9.
6. [MEDIUM] [RULE] `faction_events` has no size cap — scene_directive.rs:120-123. `mandatory_elements` capped at 3, but faction_events grows unbounded. Practical risk low (hand-authored genre packs, 2-6 factions), but asymmetric design. Recommend adding cap in follow-up.

### Rule Compliance

| Rule | Instances | Status |
|------|-----------|--------|
| #1 silent errors | 3 checked | PASS |
| #2 non_exhaustive | 2 enums | PASS |
| #3 placeholders | 4 checked | PASS |
| #4 tracing | 1 checked | N/A — pure function, pre-existing |
| #5 constructors | 4 checked | PASS |
| #6 test quality | 16 checked | LOW — 1 weak test (pre-existing) |
| #7 unsafe casts | 0 | PASS |
| #8 serde bypass | 4 checked | PASS |
| #9 public fields | 4 checked | pre-existing pattern from 6-1 |
| #15 unbounded input | 3 checked | MEDIUM — faction_events uncapped |

### Devil's Advocate

What if this is broken? The faction_events Vec grows without bound. But FactionAgenda comes from genre pack YAML (stories 6-7/6-8), which is hand-authored content. A genre pack with 50 factions would be a design problem, not a code problem. The narrator prompt has a token budget — Claude's context window is the natural cap. If someone generates 100 faction events, the prompt would exceed the context window and the narrator call would fail visibly, not silently. Not a security risk, not a data corruption risk.

**Data flow:** Genre YAML → FactionAgenda::try_new (validated) → slice passed to format_scene_directive → filter_map scene_injection → Vec<String> in SceneDirective.faction_events → narrator prompt. Safe path, validated inputs.

[EDGE] N/A. [SILENT] Dismissed — pre-existing. [TEST] N/A. [DOC] N/A. [TYPE] N/A. [SEC] N/A. [SIMPLE] N/A. [RULE] 1 MEDIUM (unbounded faction_events).

**Handoff:** To Baldur the Bright (SM) for finish-story.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **TEA: No deviations** → ✓ ACCEPTED by Reviewer.
- **Dev: No deviations** → ✓ ACCEPTED by Reviewer. Implementation matches story title exactly.

### Architect (reconcile)
- No additional deviations found. TEA and Dev both reported no deviations, Reviewer accepted both. Implementation is a clean wire-up matching the story title exactly. The unbounded faction_events finding from Reviewer is a follow-up improvement, not a spec deviation.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->