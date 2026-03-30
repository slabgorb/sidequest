---
story_id: "6-4"
jira_key: none
epic: "6"
epic_title: "Active World & Scene Directives"
workflow: "tdd"
---
# Story 6-4: FactionAgenda model — schema for faction goals, urgency, and scene injection rules

## Story Details
- **ID:** 6-4
- **Epic:** 6 (Active World & Scene Directives)
- **Jira Key:** None (personal project)
- **Workflow:** tdd
- **Stack Parent:** 6-1 (feat/6-1-scene-directive-formatter)
- **Points:** 3
- **Priority:** p1

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-03-27T20:15:26Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27T20:01:07Z | 2026-03-27T20:02:01Z | 54s |
| red | 2026-03-27T20:02:01Z | 2026-03-27T20:06:07Z | 4m 6s |
| green | 2026-03-27T20:06:07Z | 2026-03-27T20:08:16Z | 2m 9s |
| spec-check | 2026-03-27T20:08:16Z | 2026-03-27T20:09:00Z | 44s |
| verify | 2026-03-27T20:09:00Z | 2026-03-27T20:11:04Z | 2m 4s |
| review | 2026-03-27T20:11:04Z | 2026-03-27T20:14:56Z | 3m 52s |
| spec-reconcile | 2026-03-27T20:14:56Z | 2026-03-27T20:15:26Z | 30s |
| finish | 2026-03-27T20:15:26Z | - | - |

## Story Context

This story implements the `FactionAgenda` model as part of Epic 6 (Active World & Scene Directives). The world needs to be an active agent where NPCs and factions pursue agendas independent of player input.

**Key goals:**
- Define the schema for faction goals, urgency levels, and scene injection rules
- Enable factions to inject world-driven events into the narrator prompt
- Create a structure that composes with the scene directive formatter (6-1)

**Reference materials:**
- sq-2/docs/architecture/active-world-pacing-design.md
- sq-2/sprint/epic-61.yaml
- Story 6-1: Scene directive formatter (completed dependency)

## Sm Assessment

Story 6-4 starts Epic 6 (Active World). 3-point TDD story defining the FactionAgenda model — schema for faction goals, triggers, and outcomes. Depends on 6-1 (scene directive formatter, completed). No blockers. Routing to TEA for red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 3-point TDD story defining new FactionAgenda model with validation, serialization, and scene integration

**Test Files:**
- `crates/sidequest-game/tests/faction_agenda_story_6_4_tests.rs` — 25 tests across 8 sections

**Tests Written:** 25 tests covering derived ACs (no formal context doc — ACs inferred from story title, epic description, and sibling story requirements)
**Status:** RED (compilation errors — faction_agenda module doesn't exist)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `error_is_debug_and_display` (error enum exists) | failing |
| #5 validated constructors | `try_new_rejects_empty_*` (5 tests) | failing |
| #8 Deserialize bypass | `deserialize_rejects_empty_*` (2 tests) | failing |
| #9 public fields | `fields_accessed_through_getters` | failing |
| #13 constructor/deser consistency | Covered by #5 + #8 tests | failing |

**Rules checked:** 5 of 15 applicable
**Self-check:** 0 vacuous tests found

### Dev Implementation Required

1. **`faction_agenda` module** in sidequest-game
2. **`AgendaUrgency`** enum — Dormant, Simmering, Pressing, Critical with Ord, Default, serde
3. **`FactionAgenda`** struct — private fields, try_new(), getters, serde(try_from)
4. **`FactionAgendaError`** enum — validation errors
5. **`scene_injection()`** method — returns Option<String>, None for Dormant
6. **`to_directive_priority()`** on AgendaUrgency — maps to DirectivePriority
7. **`set_urgency()`** for escalation/de-escalation

**Handoff:** To Loki Silvertongue (Dev) for implementation

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/faction_agenda.rs` — new module: AgendaUrgency, FactionAgenda, FactionAgendaError, serde support
- `crates/sidequest-game/src/lib.rs` — added `pub mod faction_agenda`

**Tests:** 23/23 passing (GREEN)
**Branch:** feat/6-4-faction-agenda (pushed)

**Handoff:** To next phase (verify)

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | Manual trim().is_empty() duplicates NonBlankString (high) |
| simplify-quality | 1 finding | Missing pub use re-exports in lib.rs (high) |
| simplify-efficiency | clean | No issues |

**Applied:** 1 high-confidence fix — added `pub use faction_agenda::{AgendaUrgency, FactionAgenda, FactionAgendaError}` to lib.rs
**Flagged for Review:** 1 — NonBlankString reuse opportunity (changing field types would alter error mapping and serde path; too risky for auto-apply)
**Noted:** 0
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** 23/23 tests passing
**Handoff:** To Heimdall (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

Implementation covers all 3 key goals from session context: schema defined (FactionAgenda with urgency enum), scene injection via `scene_injection() -> Option<String>` for `SceneDirective.faction_events`, and composition with 6-1's `DirectivePriority` via `to_directive_priority()`. Sibling story 6-5 can wire this directly. Stories 6-7/6-8 can deserialize from YAML. Validated construction, private fields, `#[non_exhaustive]`, serde try_from, and tracing all present.

**Decision:** Proceed to verify

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): No story context document exists at `sprint/context/context-story-6-4.md`. ACs were inferred from story title, epic description, and sibling story requirements (6-5 wire-up, 6-7/6-8 genre pack YAML). Affects `sprint/context/` (context doc should be created). *Found by TEA during test design.*

### TEA (test verification)
- **Improvement** (non-blocking): FactionAgenda string fields could use `NonBlankString` newtype from sidequest-protocol instead of manual `trim().is_empty()` checks. Affects `crates/sidequest-game/src/faction_agenda.rs` (replace String fields with NonBlankString). *Found by TEA during test verification.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- No upstream findings during code review.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean | none | N/A |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 2 (LOW test quality), dismissed 1 (pre-existing base64 pin) |

**All received:** Yes (3 returned, 6 disabled via settings)
**Total findings:** 2 confirmed (LOW), 1 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] `AgendaUrgency` has `#[non_exhaustive]`, Ord, Default, serde with `rename_all = "lowercase"` — faction_agenda.rs:14-29. Rules #2 compliant. Variant order (Dormant < Simmering < Pressing < Critical) is correct for derived Ord.
2. [VERIFIED] `FactionAgendaError` has `#[non_exhaustive]` and uses `thiserror` — faction_agenda.rs:45-57. Rule #2 compliant.
3. [VERIFIED] All `FactionAgenda` fields are private with getters — faction_agenda.rs:62-65, getters at lines 98-115. Rule #9 compliant.
4. [VERIFIED] `try_new()` validates all 3 string fields with `tracing::warn!` on each rejection — faction_agenda.rs:77-88. Rules #4 and #5 compliant.
5. [VERIFIED] Custom Deserialize via `RawFactionAgenda` + `TryFrom` — faction_agenda.rs:132-157. Deserialization routes through `try_new()`. Rules #8 and #13 compliant. Validation cannot be bypassed via serde.
6. [VERIFIED] `scene_injection()` returns `None` for Dormant, `Some(event_text)` otherwise — faction_agenda.rs:124-129. Correct scene integration contract for story 6-5.
7. [VERIFIED] `to_directive_priority()` maps urgency to `DirectivePriority` — faction_agenda.rs:34-41. Dormant→None, Simmering→Low, Pressing→Medium, Critical→High. Composes with 6-1's `SceneDirective`.
8. [VERIFIED] `pub use` re-exports in lib.rs — line 55. Follows crate convention for public API.
9. [LOW] [RULE] `urgency_has_four_levels` test is tautological — tests:21. Asserts distinct enum literals are distinct. Cannot fail. Inflates test count but not harmful.
10. [LOW] [RULE] `urgency_is_debug_clone_copy` test is tautological — tests:65. Asserts `u == u2` where `u2 = u` (Copy). Cannot fail for any reflexive PartialEq.

### Rule Compliance

| Rule | Instances | Status |
|------|-----------|--------|
| #1 silent errors | 2 checked | PASS |
| #2 non_exhaustive | 2 enums | PASS |
| #3 placeholders | 3 checked | PASS |
| #4 tracing | 3 error paths | PASS — warn! on all |
| #5 constructors | 1 constructor | PASS — try_new only, no bypass |
| #6 test quality | 23 tests | LOW — 2 tautological tests |
| #7 unsafe casts | 0 | PASS — N/A |
| #8 serde bypass | 1 type | PASS — custom Deserialize |
| #9 public fields | 4 fields | PASS — all private |
| #10 tenant context | 0 traits | PASS — N/A |
| #11 workspace deps | 10 checked | PASS (base64 pre-existing) |
| #12 dev deps | 5 checked | PASS |
| #13 constructor/deser | 3 paths | PASS — unified via try_new |
| #14 fix regressions | 1 checked | PASS — new file |
| #15 unbounded input | 3 checked | PASS |

### Devil's Advocate

What if this code is broken? Let me try.

**What if a genre pack YAML has an unknown urgency string like "urgent"?** The `#[serde(rename_all = "lowercase")]` on `AgendaUrgency` means only "dormant", "simmering", "pressing", and "critical" are accepted. An unknown string produces a hard deserialization error, not a silent fallback to Dormant. There's no `#[serde(other)]` catch-all. This is correct — fail loudly on bad data.

**What if `scene_injection()` is called rapidly in a loop?** Each call clones the `event_text` String. For a game with ~5 factions, this is negligible. If hundreds of agendas exist, the clone cost could matter, but that's far beyond the current design's intent. Not a concern for a tabletop-scale game.

**What if urgency is mutated via `set_urgency()` during scene directive composition?** `set_urgency` takes `&mut self`, so the borrow checker prevents concurrent reads during mutation. No race condition possible in single-threaded game logic. In async contexts, the agenda would be behind a lock (like the multiplayer session pattern from 8-9).

**What about the NonBlankString reuse opportunity TEA flagged?** Valid observation — `FactionAgenda` manually validates what `NonBlankString` already does. But switching would change the error types (NonBlankString has its own error, not FactionAgendaError), requiring error mapping and potentially breaking the serde try_from path. The current approach is self-contained and correct. The reuse is a future improvement, not a bug.

**What if someone adds `#[derive(Serialize)]` to `FactionAgenda`?** Currently the struct has no Serialize derive — only Deserialize (custom impl). If Serialize is added, it would serialize the raw fields without validation (which is fine — serializing validated data doesn't need re-validation). No risk.

No critical issues found. The code is clean, well-structured, and follows all project rules.

**Data flow traced:** Genre YAML → `serde_yaml::from_str` → `RawFactionAgenda` → `TryFrom` → `try_new()` (validates) → `FactionAgenda`. Scene path: `FactionAgenda::scene_injection()` → `Option<String>` → collected into `SceneDirective.faction_events` (story 6-5). Safe.

**Pattern observed:** Validated model with custom Deserialize via intermediate raw struct — same pattern as ReminderConfig from 8-9 but more thorough (no bypass constructor).

**Error handling:** `try_new()` returns typed `FactionAgendaError` with descriptive messages and tracing. No panic paths.

[EDGE] N/A — disabled.
[SILENT] Clean — no silent failures found.
[TEST] N/A — disabled.
[DOC] N/A — disabled.
[TYPE] N/A — disabled.
[SEC] N/A — disabled.
[SIMPLE] N/A — disabled.
[RULE] 2 LOW test quality findings (tautological tests). No implementation violations.

**Handoff:** To Baldur the Bright (SM) for finish-story.

## Design Deviations

### TEA (test design)
- **ACs derived from title and epic, not from context doc**
  - Spec source: sprint/epic-6.yaml, story 6-4 title + epic description
  - Spec text: "FactionAgenda model — schema for faction goals, urgency, and scene injection rules"
  - Implementation: Tests derive 6 ACs: urgency enum, validated construction, private fields, scene injection, serde deserialization, urgency mutation
  - Rationale: No context-story-6-4.md exists. ACs inferred from story title decomposition and sibling story requirements (6-5 needs faction events in SceneDirective, 6-7/6-8 need YAML deserialization).
  - Severity: minor
  - Forward impact: If a context doc is created later with different ACs, tests may need adjustment

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **ACs derived from title and epic** → ✓ ACCEPTED by Reviewer: Reasonable inference given no context doc exists. Implementation aligns with all derived ACs and composes correctly with sibling stories.
- **Dev: No deviations from spec** → ✓ ACCEPTED by Reviewer: Implementation matches all key goals from session. No undocumented deviations found.

### Architect (reconcile)
- No additional deviations found. TEA's deviation is accurate and well-formed. The derived ACs cover the story title's three components (goals, urgency, scene injection rules) and compose correctly with sibling stories 6-5 (wire-up) and 6-7/6-8 (genre pack YAML). No missed deviations.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->