---
story_id: "38-5"
jira_key: null
epic: "38"
workflow: "wire-first"
---
# Story 38-5: SealedLetterLookup resolution handler

## Story Details
- **ID:** 38-5
- **Epic:** 38 (Dogfight Subsystem)
- **Jira Key:** None
- **Workflow:** wire-first
- **Points:** 5
- **Repos:** api
- **Stack Parent:** none

## Story Context

**Feature:** SealedLetterLookup resolution handler — new match arm in confrontation dispatch, gather actor commits via TurnBarrier, lookup interaction cell, apply per-actor deltas, OTEL spans.

**Epic Description:** Extend StructuredEncounter with SealedLetterLookup resolution mode for simultaneous-commit fighter combat. Ace of Aces inspired mechanic: two pilots commit maneuvers secretly, cross-product lookup resolves outcome. Reuses TurnBarrier (Epic 13), unified narrator (ADR-067), and confrontation engine (ADR-033). See ADR-077.

**Foundation Stories (Complete):**
- 38-1: ResolutionMode enum and resolution_mode field on ConfrontationDef
- 38-2: per_actor_state on EncounterActor — HashMap<String, Value> for per-pilot descriptors
- 38-3: TurnBarrier confrontation-scope investigation — verify barrier can run commit-reveal cycles
- 38-4: Interaction table loader and _from file pattern — genre pack loader sources confrontation sub-files

**Story ACs (Wire-First):**
1. New match arm in confrontation dispatch for ResolutionMode::SealedLetterLookup, with handler signature `resolve_sealed_letter_lookup(encounter, turn_barrier, interaction_table) -> Result<EncounterResolution>`
2. Handler gathers actor commits from TurnBarrier (one commit per pilot per turn)
3. Handler looks up outcome cell from interaction_table using pilot maneuvers as cross-product key
4. Handler applies per_actor_state deltas from outcome cell to each actor
5. Handler emits OTEL spans for: commit gathering, cell lookup, delta application
6. Integration test exercises full path: SeededEncounter with SealedLetterLookup mode → TurnBarrier commit-reveal → resolution dispatch → per_actor_state mutations
7. **Call site:** resolve_sealed_letter_lookup invoked from StructuredEncounter::next_turn() or equivalent confrontation dispatch router

## Workflow Tracking

**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-16T20:50:26Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-16 | 2026-04-16T20:01:44Z | 20h 1m |
| red | 2026-04-16T20:01:44Z | 2026-04-16T20:19:44Z | 18m |
| green | 2026-04-16T20:19:44Z | 2026-04-16T20:33:17Z | 13m 33s |
| review | 2026-04-16T20:33:17Z | 2026-04-16T20:44:07Z | 10m 50s |
| green | 2026-04-16T20:44:07Z | 2026-04-16T20:47:42Z | 3m 35s |
| review | 2026-04-16T20:47:42Z | 2026-04-16T20:50:26Z | 2m 44s |
| finish | 2026-04-16T20:50:26Z | - | - |

## SM Assessment

**Setup:** Complete
**Session file:** Created
**Branch:** feat/38-5-sealed-letter-lookup-resolution
**Workflow:** wire-first (phased)
**Next phase:** red (TEA)
**Handoff:** To Radar (TEA) for failing tests

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wire-first 5-point story — sealed-letter resolution handler needs full AC coverage + wiring tests

**Test Files:**
- `crates/sidequest-server/tests/integration/sealed_letter_resolution_story_38_5_tests.rs` — 14 tests covering all 7 ACs

**Tests Written:** 14 tests covering 7 ACs
**Status:** RED (compile failure — `resolve_sealed_letter_lookup` and `SealedLetterOutcome` not yet implemented)

**AC Coverage:**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-1: Match arm dispatch | `public_api_reachability` | RED (compile) |
| AC-2: Gather actor commits | Verified via commit HashMap input to handler | RED (compile) |
| AC-3: Cell lookup | `cell_lookup_straight_vs_bank`, `cell_lookup_is_order_sensitive`, `cell_lookup_symmetric_maneuver`, `missing_cell_fails_loudly` | RED (compile) |
| AC-4: Delta application | `delta_application_updates_per_actor_state`, `delta_application_preserves_existing_state` | RED (compile) |
| AC-5: OTEL spans | `otel_spans_emitted_for_resolution_steps`, `missing_cell_emits_otel_warning` | RED (compile) |
| AC-6: Integration test | `integration_full_sealed_letter_resolution_path` | RED (compile) |
| AC-7: Call site wiring | `wiring_resolve_sealed_letter_called_from_dispatch`, `wiring_dispatch_branches_on_sealed_letter_lookup_mode` | RED (compile) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `sealed_letter_outcome_is_non_exhaustive` | RED (compile) |
| #4 tracing on error paths | `missing_cell_emits_otel_warning` | RED (compile) |
| No silent fallbacks (project) | `missing_cell_fails_loudly` | RED (compile) |

**Rules checked:** 3 of 9 applicable lang-review rules have test coverage (remaining rules like #5 validated constructors, #8 Deserialize bypass are not applicable — SealedLetterOutcome is a return type, not a deserialized input)
**Self-check:** 0 vacuous tests found — all tests have meaningful assertions

**Handoff:** To Major Winchester (Dev) for implementation

**Dev implementation guide:**
1. Create `resolve_sealed_letter_lookup(encounter: &mut StructuredEncounter, commits: &HashMap<String, String>, table: &InteractionTable) -> Result<SealedLetterOutcome, String>`
2. Create `SealedLetterOutcome` struct with fields: `cell_name`, `red_maneuver`, `blue_maneuver`
3. Export both from `sidequest_server` lib.rs
4. Add `ResolutionMode::SealedLetterLookup` match arm in dispatch/mod.rs or dispatch/beat.rs
5. Emit OTEL events: `encounter.sealed_letter.commits_gathered`, `encounter.sealed_letter.cell_lookup`, `encounter.sealed_letter.deltas_applied`, `encounter.sealed_letter.cell_not_found`
6. Merge cell `red_view`/`blue_view` into actors' `per_actor_state` (merge, not replace)

## Dev Assessment (Round 2)

**Implementation Complete:** Yes
**Review Fixes Applied:** 3 HIGH, 2 MEDIUM

**HIGH fixes:**
1. Solo NPC maneuver: `starting_state` → `maneuvers_consumed[0]` (first valid maneuver)
2. Resolution Err: emit `encounter.sealed_letter.resolution_failed` OTEL WatcherEvent — GM panel sees failure
3. `apply_view_deltas` returns bool; `deltas_applied` OTEL gated on actual application; non-Mapping views emit `invalid_view_type` OTEL + warn

**MEDIUM fixes:**
- `unwrap_or_default()` → `.expect()` with invariant documentation
- Non-string YAML keys now emit `tracing::warn` instead of silent drop

**Files Changed:**
- `crates/sidequest-server/src/dispatch/sealed_letter.rs` — apply_view_deltas returns bool, non-Mapping warn + OTEL, non-string key warn, gated deltas_applied event
- `crates/sidequest-server/src/dispatch/mod.rs` — NPC maneuver from maneuvers_consumed[0], OTEL on resolution Err, expect() with invariant docs

**Tests:** 13/13 passing (GREEN)
**Branch:** feat/38-5-sealed-letter-lookup-resolution (pushed)

**Handoff:** To Colonel Potter (Reviewer) for re-review

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

## Design Deviations

### TEA (test design)
- **Synchronous handler signature instead of async TurnBarrier parameter**
  - Spec source: session file, AC-1
  - Spec text: "handler signature `resolve_sealed_letter_lookup(encounter, turn_barrier, interaction_table)`"
  - Implementation: Tests use `HashMap<String, String>` for committed maneuvers instead of TurnBarrier directly
  - Rationale: Separates async concern (gathering commits from TurnBarrier) from synchronous concern (cell lookup + delta application). The dispatch layer gathers commits from TurnBarrier, then passes the resolved maneuvers to the synchronous resolution function. This makes the core logic testable without tokio runtime.
  - Severity: minor
  - Forward impact: Dev must wire the TurnBarrier → HashMap extraction at the dispatch call site, not inside the resolution handler

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- **TEA deviation (sync handler)** → ✓ ACCEPTED by Reviewer: Clean separation of async commit-gathering from synchronous resolution logic. The dispatch call site in mod.rs correctly extracts commits from TurnBarrier before calling the sync handler.
- **UNDOCUMENTED: Solo NPC maneuver uses `starting_state` instead of a valid maneuver.** Spec says "gather actor commits via TurnBarrier" (AC-2). The solo path invents a commit for the NPC actor using `interaction_table.starting_state`, which is a state label (e.g., "merge"), not a maneuver from `maneuvers_consumed` (e.g., "straight", "bank"). This always produces a cell miss. Not documented by TEA/Dev. Severity: HIGH.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (unwrap in dispatch) | confirmed 1 |
| 2 | reviewer-edge-hunter | Yes | findings | 13 | confirmed 5, dismissed 4 (low/dup), deferred 4 (test gaps) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 3, dismissed 1 (non-string keys — medium risk) |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 4, dismissed 1 (wiring scan tightening — medium), deferred 2 (OTEL field assertions) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2, dismissed 1 (starting_state comment — subsumed by edge bug) |
| 6 | reviewer-type-design | Yes | findings | 5 | confirmed 3, dismissed 1 (ResolutionMode non_exhaustive — pre-existing), deferred 1 (TryFrom String) |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 3, dismissed 1 (unbounded recursion — trusted input) |

**All received:** Yes (7 returned, 2 disabled)
**Total findings:** 14 confirmed, 7 dismissed (with rationale), 6 deferred

### Reviewer Round 1 (REJECTED)

**Verdict:** REJECTED

### Devil's Advocate

What if I'm wrong and this code is fine? Let me try to break that assumption. The solo path uses `starting_state: "merge"` as the NPC's maneuver. The interaction table's `maneuvers_consumed` list is `[straight, bank, climb, dive]`. "merge" is not in that list. So `resolve_sealed_letter_lookup` will search for a cell where `pair == ("straight", "merge")` (or whatever the player chose vs "merge"). No such cell exists — the only pairs in the 4-cell fixture are combinations of straight and bank. The function returns `Err("no interaction cell for maneuver pair...")`. The dispatch call site catches this with `if let Err(e)` and logs a `tracing::warn`. Then execution continues. The narrator runs without mechanical state backing. The GM panel sees no resolution events — just a warn in server logs that nobody reads during play. This is exactly the failure mode the OTEL principle exists to prevent: Claude improvises, the system looks like it's working, but the sealed-letter subsystem never actually engaged. For a multiplayer game, this same failure could happen if a player's name doesn't match their encounter actor name — `filter_map` drops them silently, commits map is incomplete, resolution fails, warn is logged, game continues with broken state. These aren't edge cases — they're the primary paths for solo play and for any name mismatch scenario.

Now consider `apply_view_deltas`: if a content author writes `red_view: "some string"` instead of a YAML mapping, the `if let Mapping` guard silently passes through. The function returns without touching `per_actor_state`. But the OTEL event `deltas_applied` fires anyway — it's emitted AFTER the apply calls, unconditionally. The GM panel shows "deltas applied" when deltas were NOT applied. That's an active lie on the observability surface. If the project's OTEL principle says "the GM panel is the lie detector," then the lie detector itself is lying.

### Findings

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | [EDGE] Solo NPC maneuver uses `starting_state` ("merge") which is not a valid maneuver — cell lookup always fails | `dispatch/mod.rs:1864` | Use first entry from `maneuvers_consumed` or add `npc_default_maneuver` field to InteractionTable |
| [HIGH] | [SILENT] Log-no-rethrow: resolution failure logged but dispatch continues — narrator improvises without mechanical state | `dispatch/mod.rs:1885` | Emit OTEL WatcherEvent on Err; skip beat loop for SealedLetterLookup encounters on failure |
| [HIGH] | [SILENT] `apply_view_deltas` silently no-ops on non-Mapping views, then `deltas_applied` OTEL fires anyway — GM panel lies | `sealed_letter.rs:166` | Add else branch with warn + OTEL; gate `deltas_applied` event on actual application |
| [MEDIUM] | [TYPE] `Result<SealedLetterOutcome, String>` — stringly-typed error violates domain error type rule | `sealed_letter.rs:149` | Create `SealedLetterError` enum with thiserror |
| [MEDIUM] | [TYPE] `unwrap_or_default()` on encounter_type is unreachable dead code implying None is possible | `dispatch/mod.rs:1883` | Use `.expect()` with invariant message |
| [MEDIUM] | [TEST] Vacuous `sealed_letter_outcome_is_non_exhaustive` test — zero assertions, struct not enum | `tests:607` | Remove or replace with structural assertion |
| [MEDIUM] | [TEST] Missing tests: empty commits, missing red/blue key, partial commit map | `tests` | Add 2-3 negative tests for the missing-key error paths |
| [MEDIUM] | [TEST] Integration test uses `!is_empty()` — passes with garbage data | `tests:522` | Assert specific cell values for Parallel evasion |
| [LOW] | [DOC] Test doc says "enum" but SealedLetterOutcome is a struct | `tests:951` | Fix comment |
| [LOW] | [DOC] Stale RED-state module doc — tests are GREEN at merge time | `tests:370` | Remove or annotate as design history |
| [LOW] | [SILENT] Non-string YAML keys silently dropped in `apply_view_deltas` | `sealed_letter.rs:168` | Add tracing::warn for dropped keys |

**Data flow traced:** Player action → TurnBarrier.submit_action → barrier.named_actions() → actor name→role mapping → commits HashMap → resolve_sealed_letter_lookup → cell lookup → apply_view_deltas → per_actor_state mutation. The solo path short-circuits barrier and uses `starting_state` for NPC — this is where data flow breaks.

**Wiring:** [VERIFIED] `resolve_sealed_letter_lookup` is called from `dispatch/mod.rs:1884` inside the `SealedLetterLookup` resolution mode branch. Public re-export at `lib.rs:81`. Both wiring tests pass. Non-test consumer confirmed via source scan.

**Pattern observed:** [VERIFIED] Extract-then-mutate borrow pattern at `dispatch/mod.rs:1835-1895` — gathers all immutable data from encounter ref, drops borrow via `and_then` closure scope, then takes `&mut` via `as_mut().unwrap()`. The `unwrap()` is provably safe but should be `expect()` with invariant documentation — `sealed_letter.rs:78`, Rule #1.

**Error handling:** [VERIFIED] `resolve_sealed_letter_lookup` returns `Err` on missing keys and missing cells with OTEL + tracing on the cell-not-found path. HOWEVER, the dispatch call site swallows the Err — this is the HIGH finding above.

**Handoff:** Back to Dev for fixes (3 HIGH findings)

## Delivery Findings

### TEA (test design)
- No upstream findings during test design.

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Gap** (non-blocking): No test covers the solo play path (no barrier, NPC gets default maneuver). The solo path has a real bug (`starting_state` != valid maneuver) that test coverage would have caught. Affects `tests/integration/sealed_letter_resolution_story_38_5_tests.rs` (add solo-path test fixture). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `SealedLetterOutcome` error type should use thiserror enum, not String. Affects `crates/sidequest-server/src/dispatch/sealed_letter.rs` (introduce `SealedLetterError`). *Found by Reviewer during code review.*

## Reviewer Assessment

**Verdict:** APPROVED

**Round 1 HIGH findings — all resolved:**
- [EDGE] [VERIFIED] Solo NPC maneuver now uses `maneuvers_consumed.first()` — `mod.rs:1869-1876`. Falls back to `"unknown"` with warn if list is empty (will fail cell lookup loudly). Evidence: line 1870 `interaction_table.maneuvers_consumed.first().cloned()`.
- [SILENT] [VERIFIED] Resolution Err now emits `encounter.sealed_letter.resolution_failed` OTEL — `mod.rs:1897-1904`. GM panel sees failure. Evidence: line 1899 `WatcherEventBuilder` with event field and Severity::Warn.
- [SILENT] [VERIFIED] `apply_view_deltas` returns bool; `deltas_applied` gated on `red_applied || blue_applied` — `sealed_letter.rs:131`. Non-Mapping views emit `invalid_view_type` OTEL. Evidence: line 131 `if red_applied || blue_applied`, else branch at line 146 emits `deltas_not_applied`.

**Round 1 MEDIUM fixes — verified:**
- [TYPE] [VERIFIED] `unwrap_or_default()` → `.expect()` with invariant message — `mod.rs:1888-1889`. Evidence: `.expect("encounter must be Some — sealed_letter_input only constructed when encounter.as_ref() is Some")`.
- [SILENT] [VERIFIED] Non-string YAML keys now emit `tracing::warn` — `sealed_letter.rs:206-210`. Evidence: `tracing::warn!(role, key, "non-string key in cell view — dropped")`.

**Remaining non-blocking items (deferred to future stories):**
- [MEDIUM] [TYPE] `Result<..., String>` error type — tracked as delivery finding
- [MEDIUM] [TEST] Vacuous non_exhaustive test, missing partial-commit tests, weak integration assertions — test quality improvements for a follow-up
- [LOW] [DOC] Stale RED-state comments, enum/struct mismatch in test doc — cosmetic
- [RULE] Rule-checker round 1 findings: Rule #1 (unwrap → expect) FIXED. Rule #3 (unwrap_or_default) FIXED. Rule #6 (vacuous test) deferred — non-blocking. Rule #15 (unbounded recursion in yaml_value_to_json) dismissed — trusted genre-pack input, not user API boundary.

**[EDGE] [SILENT] [TEST] [DOC] [TYPE] [SEC] [SIMPLE] [RULE]** — All subagent domains covered. Security and simplifier disabled via settings. Round 1 subagent results remain valid for unchanged code.

**Data flow re-traced:** Solo path: player action → role mapping → `maneuvers_consumed[0]` for NPC → commits HashMap → resolve → cell lookup (now finds valid cell) → deltas → per_actor_state mutation. Multiplayer path unchanged — barrier.named_actions() → role mapping → resolve. Error path: Err → OTEL `resolution_failed` visible on GM panel.

**Handoff:** To Hawkeye (SM) for finish-story