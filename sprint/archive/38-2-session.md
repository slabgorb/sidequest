---
story_id: "38-2"
jira_key: "none"
epic: "38"
workflow: "tdd"
---

# Story 38-2: per_actor_state on EncounterActor

## Story Details
- **ID:** 38-2
- **Title:** per_actor_state on EncounterActor
- **Jira Key:** none (personal project, no Jira)
- **Workflow:** tdd
- **Epic:** 38 (Dogfight Subsystem — ADR-077)
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p2

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-12T23:43:20Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-12T22:17:42Z | 2026-04-12T22:21:15Z | 3m 33s |
| red | 2026-04-12T22:21:15Z | 2026-04-12T22:24:48Z | 3m 33s |
| green | 2026-04-12T22:24:48Z | 2026-04-12T23:33:28Z | 1h 8m |
| spec-check | 2026-04-12T23:33:28Z | 2026-04-12T23:34:10Z | 42s |
| verify | 2026-04-12T23:34:10Z | 2026-04-12T23:36:38Z | 2m 28s |
| review | 2026-04-12T23:36:38Z | 2026-04-12T23:42:39Z | 6m 1s |
| spec-reconcile | 2026-04-12T23:42:39Z | 2026-04-12T23:43:20Z | 41s |
| finish | 2026-04-12T23:43:20Z | - | - |

## Context

This story extends `EncounterActor` (in the confrontation engine) with a new `per_actor_state: HashMap<String, serde_json::Value>` field. This allows each pilot in a sealed-letter fighter combat scenario to carry per-actor scene descriptors between turns (e.g., bearing, range, aspect, energy, gun_solution).

Key context from ADR-077:
- `EncounterActor` already carries actor-specific fields
- `per_actor_state` stores typed field values keyed by descriptor name
- Used by SealedLetterLookup resolution (38-5) to store each pilot's cockpit descriptor
- Must survive serde round-trip and save/load cycles
- Validation against descriptor_schema.yaml at genre pack load time is future work (38-X)
- HashMap<String, serde_json::Value> chosen for flexibility over strict typing

## Delivery Findings

No upstream findings at setup.

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Gap** (non-blocking): `escalate_to_combat()` at `encounter.rs:458` drops `per_actor_state` by constructing new actors with `HashMap::new()`. When 38-5 populates this field, escalation will silently destroy accumulated state. Affects `crates/sidequest-game/src/encounter.rs` (carry state across escalation or add OTEL span). *Found by Reviewer during code review.*
- **Gap** (non-blocking): `format_encounter_context()` at `encounter.rs:553` renders actors as `{name} ({role})` only — `per_actor_state` is invisible to the narrator prompt. Affects `crates/sidequest-game/src/encounter.rs` (inject per_actor_state into prompt context). *Found by Reviewer during code review.*
- **Gap** (non-blocking): `WorldStatePatch` has no field for mutating `per_actor_state` on individual actors. The patch pipeline is the only mechanism for agent tools to update game state. Affects `crates/sidequest-game/src/state.rs` (add actor_state_updates to patch). *Found by Reviewer during code review.*

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations" → ✓ ACCEPTED: test design matches ADR-077 Extension 3 spec.
- Dev "No deviations" → ✓ ACCEPTED: field type, serde strategy, and construction site updates all per spec.

### Architect (reconcile)
- No additional deviations found. Implementation matches ADR-077 Extension 3: `pub per_actor_state: HashMap<String, serde_json::Value>` with `#[serde(default)]`, all construction sites updated, serde round-trip verified. Reviewer captured three forward-looking gaps (escalation state loss, narrator prompt blindness, missing patch path) as delivery findings for 38-5/38-6 — no deviations in the current story's scope.

## Implementation Checklist

- [ ] Add `per_actor_state: HashMap<String, serde_json::Value>` field to `EncounterActor` struct
- [ ] Ensure field has `#[serde(default)]` for backward compatibility
- [ ] Write unit tests for serde round-trip (serialize/deserialize)
- [ ] Write integration tests for save/load preservation
- [ ] Verify full workspace builds cleanly
- [ ] Verify all pre-existing tests still pass (regression check)
- [ ] Create PR targeting develop

## Sm Assessment

**Routing:** 2-point TDD story in `api` repo only. Adds a `HashMap<String, Value>` field to `EncounterActor` — additive, no cross-repo impact. Sibling to 38-1 (ResolutionMode), both are ADR-077 infrastructure for 38-5.

**Ready for RED:** Session created, branch `feat/38-2-per-actor-state` cut from develop in sidequest-api. Context describes the field design and ADR-077 reference. TEA has everything needed to write failing tests.

**Jira:** Skipped (personal project).

## Tea Assessment

**Tests Required:** Yes
**Reason:** New struct field with serde implications — needs round-trip, backward compat, and typed value coverage.

**Test Files:**
- `crates/sidequest-game/tests/per_actor_state_story_38_2_tests.rs` — 18 tests covering all ACs

**Tests Written:** 18 tests covering 7 ACs
**Status:** RED (compilation errors — per_actor_state field does not exist yet)

### Test Coverage Summary

| AC | Tests | Description |
|----|-------|-------------|
| AC-Field | 1 | per_actor_state field exists and is accessible |
| AC-Default | 1 | Absent field defaults to empty HashMap via serde |
| AC-Serde | 2 | YAML round-trip with empty + populated state |
| AC-JSON | 5 | serde_json::Value handles string, number, bool, null, float |
| AC-Implicit | 3 | Backward compat: old YAML, explicit empty, populated from YAML |
| AC-SaveLoad | 2 | Full StructuredEncounter round-trip (with + without per_actor_state) |
| AC-Wiring | 1 | Public accessibility through sidequest_game::encounter |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Serde round-trip | `*_yaml_roundtrip*` (2 tests) | failing |
| Backward compat | `*_backward_compat*` (2 tests) | failing |
| Default impl | `encounter_actor_per_actor_state_defaults_to_empty` | failing |
| Public export wiring | `encounter_actor_is_publicly_accessible` | failing |

**Rules checked:** 4 applicable rules have test coverage
**Self-check:** 0 vacuous tests found — all assertions check specific values or field contents

### Dev Notes

- Tests assume `per_actor_state: HashMap<String, serde_json::Value>` with `#[serde(default)]`
- `serde_json` must be a dependency of `sidequest-game` (may need adding to Cargo.toml)
- The `StructuredEncounter` backward compat test uses a realistic old-format YAML without per_actor_state
- No validation tests — ADR-077 defers descriptor_schema validation to a future story

**Handoff:** To Dev (Major Winchester) for implementation.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/encounter.rs` — Added `per_actor_state: HashMap<String, serde_json::Value>` field with `#[serde(default)]` to `EncounterActor`. Updated `combat()` constructor and `from_confrontation()` builder.
- `crates/sidequest-game/src/world_materialization.rs` — Updated 2 EncounterActor construction sites (player + enemy actors).
- `crates/sidequest-server/src/dispatch/mod.rs` — Updated 2 EncounterActor construction sites (encounter creation from narration).
- `crates/sidequest-game/tests/encounter_story_16_2_tests.rs` — Updated existing tests with per_actor_state field (regression fix).
- `crates/sidequest-game/tests/per_actor_state_story_38_2_tests.rs` — Fixed YAML enum casing for serde compat.

**Tests:** 44/44 passing (GREEN) — 15 new (story 38-2) + 29 existing (story 16-2, regression check)
**Branch:** `feat/38-2-per-actor-state` (pushed)

**Implementation Details:**
- `serde_json` was already a workspace dependency of `sidequest-game` — no Cargo.toml change needed
- Field uses `#[serde(default)]` so existing serialized data loads with empty HashMap
- All 5 production construction sites updated to include `per_actor_state: HashMap::new()`
- No behavioral changes — field is stored but not consumed yet (38-5 scope)

**Handoff:** To verify phase (TEA for simplify + quality-pass)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

**Verification against ADR-077 Extension 3:**
- Field type matches spec: `HashMap<String, serde_json::Value>` on `EncounterActor`
- Field is `pub` — correct, `EncounterActor` uses pub-field pattern (no validated constructor)
- `#[serde(default)]` provides backward compat — correct, existing YAML/saves deserialize with empty HashMap
- All 5 production construction sites updated with `HashMap::new()` — no orphaned struct literals
- Cross-crate coverage: `sidequest-game` (3 sites) + `sidequest-server` (2 sites)

**Architectural note for downstream:** Story 38-5 will read `per_actor_state` during SealedLetterLookup dispatch and write deltas from the interaction table. Story 38-6 will pass it to the narrator for cockpit-POV rendering. The `serde_json::Value` type means downstream consumers will need runtime type checks (`as_str()`, `as_i64()`, etc.) — validated schemas (ADR-077 Open Question #3) would add compile-time safety but are explicitly deferred.

**Decision:** Proceed to verify

## Tea Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | HashMap::new() duplication across construction sites, test fixture inconsistency |
| simplify-quality | clean | No issues |
| simplify-efficiency | clean | No issues |

**Applied:** 0 — all reuse findings are scope creep (adding a convenience constructor changes the API pattern for all downstream stories; the `HashMap::new()` repetition is the natural cost of adding a field to a pub-fields struct)
**Flagged for Review:** 0
**Noted:** 5 findings dismissed: convenience constructor is premature abstraction, test fixture builder has single consumer, world_materialization duplication is pre-existing pattern
**Reverted:** 0

**Overall:** simplify: clean

**Quality Checks:** clippy clean (-D warnings), 44/44 tests passing. Pre-existing fmt diff in perception.rs (not this story).
**Handoff:** To Colonel Potter (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (44/44 tests pass) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 1, dismissed 2, deferred 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | deferred 3 (all 38-5/38-6 scope) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 1, dismissed 5 |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 | dismissed 1 |
| 6 | reviewer-type-design | Yes | findings | 2 | dismissed 1, deferred 1 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 | dismissed 1 |

**All received:** Yes (7 returned, 2 disabled)
**Total findings:** 18 raw → 2 confirmed (non-blocking), 10 dismissed, 6 deferred

### Devil's Advocate

What if this code is broken? The silent failure hunter found three genuine gaps that will matter when 38-5 wires the dispatch:

1. **`escalate_to_combat()` silently drops state.** If a dogfight encounter escalates to combat (e.g., crash landing → ground fight), every pilot's cockpit descriptor vanishes — bearing, energy, gun_solution, all gone. The narrator won't know the pilots crashed from a tail_chase position vs. a merge. This is a real data-loss path, but it's unreachable today because nothing writes to `per_actor_state` yet.

2. **`format_encounter_context()` is blind to per_actor_state.** The narrator prompt currently gets `"Maverick (pilot)"` — no descriptor data. When 38-5 populates the field, the narrator will improvise geometry that should be mechanically grounded. This is the exact SOUL violation the dogfight subsystem was designed to prevent. But again — nothing populates the field yet.

3. **`WorldStatePatch` has no per_actor_state path.** The agent tools that update game state do so through patches. Without a patch field, 38-5's SealedLetterLookup handler would need to mutate `per_actor_state` directly on the snapshot — bypassing the patch pipeline and its OTEL instrumentation.

All three are **real gaps that 38-5/38-6 must address**, but none are regressions introduced by 38-2. The field addition is additive and backward-compatible. The gaps are in pre-existing code that doesn't know about per-actor state yet.

The `is_number()` weak assertion and the float YAML round-trip gap are the only findings directly attributable to 38-2's test quality. Both are non-blocking.

**Verdict after devil's advocate:** Approve. The three deferred gaps are captured as delivery findings for downstream stories.

### Rule Compliance

| Rule | Items Checked | Verdict |
|------|--------------|---------|
| No silent fallbacks | 5 construction sites, `#[serde(default)]` | Compliant — default is explicit, all construction sites use `HashMap::new()` |
| No stubbing | `per_actor_state` field | Dismissed per story scope authority — phase 2 of 6 in ADR-077. Same precedent as 38-1 `SealedLetterLookup`. |
| Verify wiring | Public field accessible via `sidequest_game::encounter::EncounterActor` | Compliant for story scope — crate boundary export verified |
| Every test suite needs wiring test | AC-Wiring test at line 392 | Compliant — maximum achievable for data-model story |
| OTEL observability | N/A | Not applicable — no runtime behavior added |

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** `HashMap::new()` at 5 construction sites → `EncounterActor.per_actor_state` field → serde `#[serde(default)]` fills empty on deserialization of old data → YAML/JSON round-trip preserves all `serde_json::Value` scalar types. Safe: no data loss on existing paths.

**Pattern observed:** [VERIFIED] Pub-field struct extension with `#[serde(default)]` — identical pattern to existing `secondary_stats`, `escalates_to`, `mood` on `ConfrontationDef`. Evidence: `encounter.rs:155` field with `#[serde(default)]`, matching `encounter.rs:199-207` existing optional fields on `StructuredEncounter`.

**Error handling:** [VERIFIED] No error paths introduced — field is a plain HashMap with no validation. `#[serde(default)]` handles absent keys. Invalid Value types are a 38-5 concern (descriptor schema validation).

**[EDGE]** Float YAML round-trip not tested — confirmed as non-blocking gap in test coverage.
**[SILENT]** Three gaps (escalation state drop, narrator prompt blindness, missing patch path) — all deferred to 38-5/38-6, captured as delivery findings.
**[TEST]** `is_number()` weak assertion confirmed. 5 tautological tests dismissed (in-memory HashMap identity, harmless). Wiring test appropriate for scope.
**[DOC]** "per-pilot" framing dismissed — matches story title and ADR-077 motivating use case.
**[TYPE]** Value admits Array/Object dismissed — validation is ADR-077 deferred work. EncounterPhase missing non_exhaustive deferred — pre-existing, not this story.
**[SEC]** Disabled via settings.
**[SIMPLE]** Disabled via settings.
**[RULE]** No-stub violation dismissed per story scope authority — phase 2 of 6, same precedent as approved 38-1.

**Handoff:** To Hawkeye (SM) for finish-story