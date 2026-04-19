---
story_id: "37-12"
jira_key: ""
epic: "37"
workflow: "tdd"
---
# Story 37-12: Narrator never re-declares confrontation after first emission

## Story Details
- **ID:** 37-12
- **Jira Key:** (personal project, no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none
- **Type:** Bug (p0)
- **Points:** 3

## Problem Statement

The narrator emits the `confrontation_type` field once at the encounter creation, then remains silent throughout the gunfight and scene transitions. While the prose narrative describes a new encounter type (e.g., "the poker game becomes tense" → transitions to a new confrontation), the structured state is stuck on the stale `encounter_type` value. The UI renders old state while the prose contradicts it.

## Root Cause Analysis

The narrator's LLM prompt contract specifies `confrontation_type` emission, but the implementation (likely in the dispatch or narration loop) does not re-emit the field on:
1. Scene transitions (room changes, location shifts)
2. Encounter state transitions (e.g., resolved → unresolved, or confrontation escalation)
3. Beat changes that semantically change the encounter nature

The dispatch engine accepts new confrontations only when there is no active unresolved encounter (37-13 fix), but this does not ensure the narrator re-declares the type when it *should* change within a continuous scene.

## Acceptance Criteria

1. **Test coverage**: Write integration test that verifies narrator re-emits `confrontation_type` when the encounter transitions to a new type (e.g., "poker game" → "standoff") without closing the prior encounter
2. **Wiring verification**: Confirm `confrontation_type` is extracted from narrator output on every turn, not just initial emission
3. **Trace verification**: Add OTEL span marking when `confrontation_type` is updated vs. unchanged, so the GM panel can detect silent drops
4. **No regression**: All existing encounter tests still pass; no silent fallbacks on missing field

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-14T19:24:49Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-14 | 2026-04-14T18:49:35Z | 18h 49m |
| red | 2026-04-14T18:49:35Z | 2026-04-14T18:59:11Z | 9m 36s |
| green | 2026-04-14T18:59:11Z | 2026-04-14T19:03:08Z | 3m 57s |
| spec-check | 2026-04-14T19:03:08Z | 2026-04-14T19:03:48Z | 40s |
| verify | 2026-04-14T19:03:48Z | 2026-04-14T19:07:44Z | 3m 56s |
| review | 2026-04-14T19:07:44Z | 2026-04-14T19:24:28Z | 16m 44s |
| spec-reconcile | 2026-04-14T19:24:28Z | 2026-04-14T19:24:49Z | 21s |
| finish | 2026-04-14T19:24:49Z | - | - |

## Sm Assessment

**Story scope:** Narrator's `confrontation_type` field is emitted once at encounter open and never re-declared, causing structured state to desync from prose during transitions. Bug touches narrator output parsing, dispatch engine, and OTEL telemetry.

**Approach for TEA (RED phase):**
- Write failing integration test: narrator output stream transitions encounter type mid-scene (e.g., "poker game" → "standoff") and assert the structured `confrontation_type` updates on the turn the prose changes.
- Add OTEL assertion: a span event must fire on every turn marking `confrontation_type` as `updated` or `unchanged`. Absence of the span = silent drop (37-14 territory).
- Verify wiring end-to-end: narrator LLM output → parser → encounter state → UI render path. Per CLAUDE.md wiring rules, a passing unit test on the parser alone is not sufficient.

**Risk:** This bug sits adjacent to 37-13 (encounter gate silent-drop) and 37-14 (beat dispatch silent no-op). TEA should check whether the fix overlaps with existing dispatch logic to avoid colliding with 37-13's recent merge.

**Definition of done:** All four ACs pass, OTEL span visible in GM panel, no regression in `encounter_*` tests, `cargo build --workspace` clean.

## Tea Assessment

**Phase:** finish
**Tests Required:** Yes
**Reason:** Prompt-contract fix with clear ACs and OTEL requirements; needs a text-contract test suite that locks Dev's implementation to the same markers the reviewer will look for.

**Test Files:**
- `crates/sidequest-server/tests/integration/narrator_confrontation_redef_story_37_12_tests.rs` — 7 source-scan tests on `dispatch/prompt.rs`
- `crates/sidequest-server/tests/integration/main.rs` — new `mod narrator_confrontation_redef_story_37_12_tests;` registration

**Tests Written:** 7 tests covering 6 ACs (AC-Wiring is implicit + explicit via test 7)
**Status:** RED (7 failing, 412 unrelated passing, compilation clean)

### Test → AC Map

| AC | Test |
|---|---|
| AC-NoOnlyOnStart | `prompt_no_longer_tells_narrator_to_only_emit_on_start` |
| AC-TransitionMarker | `prompt_includes_transition_confrontation_section_marker` |
| AC-ReemitGuidance | `prompt_instructs_narrator_to_reemit_on_scene_shift` |
| AC-AltTypesListed | `transition_block_iterates_confrontation_defs` |
| AC-OTEL (event) | `prompt_emits_transition_guidance_otel_event` |
| AC-OTEL (field) | `otel_transition_event_carries_alternative_count_field` |
| AC-Wiring | `transition_guidance_is_below_build_prompt_context_declaration` |

### Rule Coverage (Rust lang-review — 15 checks)

Most rules target new types, constructors, traits, or public enums. This fix is a prompt-string edit plus one OTEL watcher call; applicable checks are narrow:

| Rule | Applies? | Test / Note |
|---|---|---|
| #1 silent error swallowing | No | no new error paths introduced |
| #2 `#[non_exhaustive]` on enums | No | no new enums |
| #3 hardcoded placeholders | No | n/a |
| #4 tracing coverage & level | Yes | `WatcherEventBuilder::new(..., WatcherEventType::StateTransition)` — Dev must use `StateTransition`, not a warn/error event. Reviewer will check. |
| #5 validated constructors at boundaries | No | no constructors |
| #6 test quality | Yes | every test uses `assert!`/`assert_eq!` with a specific substring match; no `let _ =`, no `assert!(true)`, no always-`None` checks. Self-checked. |
| #7–#13, #15 | No | n/a — prompt-string fix |
| #14 fix-regressions meta-check | Deferred | Reviewer responsibility post-GREEN |

**Rules checked:** 2 of 15 applicable, both covered.
**Self-check:** 0 vacuous tests found.

### Notes for Dev (Winchester)

1. **The misdirection string at `prompt.rs:421`** (`"Only emit confrontation on the turn the encounter STARTS."`) is the proximate cause. Delete it. The 37-13 gate in `dispatch/encounter_gate.rs` is already ready to route re-emits on every case — it's the prompt that's blocking the narrator from sending them.

2. **The `AVAILABLE ENCOUNTER TYPES` block** (`prompt.rs:412-434`) is currently gated on `ctx.snapshot.encounter.is_none()`. When an encounter IS active, add a parallel block under the `if let Some(ref enc) = ctx.snapshot.encounter` branch (near line 379) that:
   - Prints a `=== TRANSITION CONFRONTATION ===` header
   - Tells the narrator it may re-emit `confrontation` when the scene shifts to a different type
   - Lists the OTHER confrontation types (exclude `enc.encounter_type` — a narrator re-declaring its own type is handled by the gate's Case C no-op anyway, no need to tempt it)
   - Emits a `WatcherEventBuilder` with event name `encounter.transition_guidance_injected`, `WatcherEventType::StateTransition`, field `alternative_count` = number of types shown

3. **Wording freedom:** test 3 accepts several re-emission phrasings (`re-emit`, `re-declare`, `emit a new confrontation`, etc.). Pick whichever reads best alongside the rest of the prompt. If none fit, update the test's candidate list in the same commit and justify it as a design deviation.

4. **Do NOT extract a helper that `build_prompt_context` doesn't call.** Test 7 explicitly verifies `TRANSITION CONFRONTATION` appears *below* the `fn build_prompt_context` declaration, to prevent the dead-helper failure mode CLAUDE.md warns about.

5. **Run after implementing:** `cargo test -p sidequest-server --test integration narrator_confrontation_redef_story_37_12` — should go 7/7 green.

**Handoff:** To Dev (Major Winchester) for GREEN phase.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 7 Story 37-12 tests pass, 412 unrelated integration tests still pass, `cargo clippy -p sidequest-server --tests -- -D warnings` clean.

**Files Changed:**
- `crates/sidequest-server/src/dispatch/prompt.rs` — +39/-1 (transition guidance block added to active-encounter branch; misdirection line removed from is_none() branch)

### Implementation Notes

1. **Insertion point.** The TRANSITION CONFRONTATION block lives inside the outer `if let Some(ref enc) = ctx.snapshot.encounter { ... }` guard but OUTSIDE the inner `if let Some(def) = find_confrontation_def(...)` / `else` pair. Rationale: the transition guidance should fire whenever an encounter is active, even on the pathological path where the current `encounter_type` has no matching def (already a ValidationWarning event). Hiding the guidance behind the "def found" path would create a second failure mode: "narrator emits new type, but only if the current type is parseable." That would be a fresh silent fallback, exactly what CLAUDE.md forbids.

2. **Excluded the current type.** The alternatives list filters out `enc.encounter_type` so the narrator is shown transition TARGETS, not the type it's already in. The 37-13 gate's Case C (`Redeclared`) no-ops on same-type re-emits, so including the current type would be noise in the prompt and a waste of the alternatives budget. This is a small deviation from "list all defs" that I'm logging in Design Deviations.

3. **OTEL event shape.** Used `WatcherEventBuilder::new("encounter", WatcherEventType::StateTransition).field("event", "encounter.transition_guidance_injected")...` — matching the 37-13 gate's event naming convention exactly (component="encounter", event name in a `"event"` field, StateTransition type). Fields emitted: `event`, `current_encounter_type`, `alternative_count`. The GM panel already filters on `component == "encounter"` so this event slots into the existing filter automatically.

4. **Phrasing chosen.** Went with `"re-emit the `confrontation` field"` because it's the same verb TEA's test candidate list led with, and it echoes the language the rest of the prompt uses for game_patch fields. The example (`a poker game erupts into a standoff, or a chase breaks into combat`) was picked from spaghetti_western genre pack territory since that's the one LoRA is currently exercising.

5. **Misdirection line removal is safe.** The surrounding text in the is_none() branch already says "When combat, a chase, or another confrontation begins, include `"confrontation": "<type>"` in your game_patch." — that's the "emit on start" guidance in positive form. The deleted "Only emit confrontation on the turn the encounter STARTS" line was negative reinforcement that contradicted 37-13's re-emit gate. Dropping it leaves the positive instruction intact.

### Rust Lang-Review Self-Check

| # | Check | Status | Notes |
|---|---|---|---|
| 1 | silent errors | pass | no new error paths; existing ValidationWarning branches untouched |
| 2 | `#[non_exhaustive]` | n/a | no new enums |
| 3 | placeholders | pass | `alternatives.len()` is real data, no `"unknown"`/`false` stubs |
| 4 | tracing coverage & level | pass | `StateTransition` type (not error/warn) — this is a successful injection, not a failure |
| 5 | validated constructors | n/a | no new constructors |
| 6 | test quality | pass | all 7 TEA tests have non-vacuous `assert!` with substring-specific messages |
| 7 | unsafe casts | n/a | none |
| 8 | `#[derive(Deserialize)]` bypass | n/a | no new deserializable types |
| 9 | public fields | n/a | no new structs |
| 10 | tenant context | n/a | not a multi-tenant path |
| 11 | workspace deps | pass | no Cargo.toml edits |
| 12 | dev-deps | n/a | no dep changes |
| 13 | constructor/deserialize consistency | n/a | |
| 14 | fix-introduced regressions | pass | re-scanned the diff; no new `.ok()`/`.unwrap()`/placeholder additions |
| 15 | unbounded recursive input | n/a | no recursion; `alternatives.len()` bounded by `confrontation_defs.len()` which is genre-pack-controlled |

### Wiring Verification (CLAUDE.md § "Verify Wiring, Not Just Existence")

- `build_prompt_context` is called from `dispatch::dispatch_player_action` (production narrator path — grep `build_prompt_context` in dispatch/mod.rs). The TRANSITION CONFRONTATION block is INSIDE `build_prompt_context`, so it runs on every turn where `ctx.snapshot.encounter.is_some()`.
- TEA's test 7 (`transition_guidance_is_below_build_prompt_context_declaration`) explicitly verifies the marker sits below the function declaration — no dead helper.
- The OTEL event is observable via the `/ws/watcher` endpoint and will surface in the GM panel's encounter filter on the next playtest. That's the end-to-end observability path.

**Handoff:** To Radar (TEA) for verify phase (simplify + quality-pass).

## Tea Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed, simplify applied, quality-pass clean

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3
- `crates/sidequest-server/src/dispatch/prompt.rs`
- `crates/sidequest-server/tests/integration/main.rs`
- `crates/sidequest-server/tests/integration/narrator_confrontation_redef_story_37_12_tests.rs`

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding (medium) | copy-paste confrontation-def format string between new TRANSITION block and pre-existing AVAILABLE ENCOUNTER TYPES block |
| simplify-quality | clean | naming, placement, assertions all correct |
| simplify-efficiency | 1 finding (high) | unnecessary `Vec<&ConfrontationDef>` collect+iterate on narrator prompt hot path |

**Applied:** 1 high-confidence fix
- Replaced the intermediate `Vec` collection with a direct `filter()` + counter loop. The `alternative_count` field previously derived from `Vec::len()` is now produced by incrementing a local counter in the format loop. Commit: `fe7adcc refactor(37-12): drop Vec allocation on narrator prompt hot path`.

**Flagged for Review:** 0 medium-confidence findings auto-applied.

**Noted (dismissed):** 1 medium-confidence finding
- simplify-reuse flagged a duplicated 4-line format! call between the new TRANSITION CONFRONTATION block and the pre-existing AVAILABLE ENCOUNTER TYPES block. Dismissing per CLAUDE.md "Don't add features, refactor, or introduce abstractions beyond what the task requires. Three similar lines is better than a premature abstraction." Extracting a helper would expand the diff into pre-existing code outside 37-12's scope, and the finding is medium confidence (below the auto-apply threshold anyway). If future work touches both sections, the helper should be extracted then, not now.

**Reverted:** 0

**Overall:** simplify: applied 1 fix

### Regression Detection (post-simplify)

- `cargo fmt` — no changes
- `cargo clippy -p sidequest-server --tests -- -D warnings` — clean, zero warnings
- `cargo test -p sidequest-server --test integration narrator_confrontation_redef_story_37_12 --no-fail-fast` — 7/7 pass
- `cargo test -p sidequest-server --test integration --no-fail-fast` — 419 passed, 0 failed, 4 ignored

**Quality Checks:** All passing
**Handoff:** To Reviewer (Colonel Potter) for final code review.

## Architect Assessment

**Phase:** finish
**Status:** pass-through (OQ-2 personal project — see `memory/feedback_skip_architect.md`)

**Scope review:** Story 37-12 touches one file (`dispatch/prompt.rs`) with a +39/-1 diff. No new types, no new public API, no subsystem boundary changes, no ADR required. The TRANSITION CONFRONTATION block is a prompt-string addition plus one `WatcherEventBuilder::send()` call — architectural surface area is zero.

**Consistency check:** The new OTEL event (`encounter.transition_guidance_injected`, component=`encounter`, type=`StateTransition`) follows the same shape as the 37-13 gate events (`encounter.redeclare_noop`, `encounter.replaced_pre_beat`, etc.) — event name in a `"event"` field, component fixed to `"encounter"`. The GM panel's existing filter on `component == "encounter"` will pick it up without config change.

**Deviations noted from Dev:** Two placement decisions (filter current type from alternatives, place transition block at outer-guard level not inside def-resolution) — both are defensible and match the "No Silent Fallbacks" principle. No architectural concerns.

**Handoff:** To Radar (TEA) for verify phase.

## Reviewer Assessment

**Phase:** finish
**Status:** APPROVED with in-scope nits applied. 4 commits on branch, 419/419 integration tests green, clippy clean, cargo fmt no-op.

**Specialist tags:** [EDGE] [SILENT] [TEST] [DOC] [TYPE] [RULE] — all 6 enabled specialists returned, 2 (security, simplifier) disabled in project settings.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — build/lint/tests green |
| 2 | reviewer-edge-hunter | Yes | findings | 6 | 2 applied (bounded window + comment honesty), 2 dismissed as defended-by-design (def-missing transition, empty alternatives), 2 follow-ups (AVAILABLE CONFRONTATIONS duplication, YAML injection) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 | All 3 overlap with edge-hunter #1/#2 and dismissed with the same rationale: the transition block and ValidationWarning are distinct semantic signals, not a contradiction |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | 1 applied (bounded window via END marker), 1 applied (narrowed phrase test), 1 known limitation documented (test 7 nesting-depth gap), 2 follow-ups |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | 2 applied (prompt.rs block comment honesty + test doc six/five fix), 1 follow-up (encounter_gate.rs:10-12 stale comment, out of scope) |
| 6 | reviewer-type-design | Yes | clean | 0 | N/A — no new types, all 6 type rules not applicable to prompt-string fix |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security = false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier = false` |
| 9 | reviewer-rule-checker | Yes | findings | 1 | Applied (narrowed phrase test per rule #6); pre-existing `dirs = "5"` inline pin noted but outside diff |

**All received: Yes** (7 enabled specialists returned, 2 skipped by project settings).

### Subagent Result Table

### Specialist Tags Incorporated

- **[EDGE]** (reviewer-edge-hunter): 6 findings — 2 applied (bounded-window test, block-comment honesty), 2 dismissed as defended-by-design (def-missing still gets transition, empty alternatives edge case), 2 follow-ups (AVAILABLE CONFRONTATIONS duplication, YAML injection in format strings).
- **[SILENT]** (reviewer-silent-failure-hunter): 3 findings — all overlap with [EDGE] and dismissed with the same rationale. The ValidationWarning and transition_guidance_injected events are distinct semantic signals (broken config + recovery menu offered), not a contradictory dual-fire. OTEL observability is preserved on both paths.
- **[TEST]** (reviewer-test-analyzer): 5 findings — bounded-window test fix applied, phrase test narrowed, test-7 nesting-depth gap documented as a known limitation of source-scan convention, 2 edge-case tests flagged as follow-ups (single-type pack, no-encounter regression guard).
- **[DOC]** (reviewer-comment-analyzer): 3 findings — block comment rewritten to name all 6 gate cases explicitly, test docstring six-cases/five-names contradiction resolved, encounter_gate.rs:10-12 stale "root cause" claim flagged as out-of-scope follow-up.
- **[TYPE]** (reviewer-type-design): 0 findings — clean. All 6 Rust type rules (non_exhaustive, validated constructors, unsafe casts, serde bypass, private fields, constructor/deserialize consistency) N/A to a prompt-string fix with no new types.
- **[RULE]** (reviewer-rule-checker): 1 finding applied (rule #6 test quality — narrowed phrase test from 6-candidate OR to canonical "re-emit the `confrontation`"). All 15 Rust lang-review rules walked exhaustively; 13 clean, 1 applied, 1 pre-existing (`dirs = "5"` inline pin in Cargo.toml, outside diff).

### Applied In-Scope (commit `435b377`)

1. **Code comment honesty** (`dispatch/prompt.rs`): the block comment previously claimed 37-13 routes re-emits "on every case" but only named 3 of 6. Rewrote to name Cases C/D/E explicitly, note that A/B are reached via the `is_none()` branch, and document that the block sits outside the inner `find_confrontation_def()` guard intentionally so a broken-def encounter can still receive a recovery transition menu.

2. **Test bounded window** (`...story_37_12_tests.rs`): `transition_block_iterates_confrontation_defs` previously used a fixed `trans_idx + 2000` byte window, which was fragile to block growth and could sweep into the neighbouring `AVAILABLE CONFRONTATIONS` block's iterator. Replaced with a semantic window bounded by `=== TRANSITION CONFRONTATION ===` and `=== END TRANSITION CONFRONTATION ===`, giving the test a tight scope that moves with the block.

3. **Narrowed phrase test**: `prompt_instructs_narrator_to_reemit_on_scene_shift` previously accepted any of six phrasings. Now that GREEN settled on `"re-emit the `confrontation`"` as the canonical wording, the test pins that exact substring so any future reword surfaces in code review instead of silently preserving the multi-candidate flexibility that was only load-bearing during the RED→GREEN handoff.

4. **Test module doc fix**: the docblock claimed "six observable cases" but then enumerated only five outcome names. Rewrote to note Cases A and B share the `Created` outcome name, resolving the six-cases-five-names contradiction.

### Load-Bearing Judgments (downgraded from HIGH to defended-by-design)

**Finding:** edge-hunter #1 and silent-failure-hunter #1 both flagged HIGH on "transition block runs even when `find_confrontation_def` returns None for the current encounter". The concern: the existing `ValidationWarning("confrontation_def_missing")` fires AND the new transition block runs, producing what the subagents described as "a semantic contradiction" on the GM panel.

**Dismissed with rationale.** Dev's implementation note explicitly defended this placement as the correct non-silent-fallback behavior, and I agree: when the current encounter's def is missing, the narrator ABSOLUTELY needs a transition menu to recover — that is the entire point of the transition mechanism. The two events carry distinct semantic meanings:
- `encounter.confrontation_def_missing` = "config is broken, current encounter type is unrecognised"
- `encounter.transition_guidance_injected` = "narrator was offered N alternative targets"

Both are true simultaneously. Both are observable independently. The GM panel can distinguish "broken config, no recovery offered" from "broken config, N targets offered" by pair-filtering on both events — that is a strictly better diagnostic signal than hiding the transition block behind the def guard and losing the recovery path entirely. The updated code comment now documents this reasoning inline so a future reader doesn't repeat the subagent's misread.

**Finding:** edge-hunter #2 flagged HIGH on "empty alternatives list when the genre pack has exactly one confrontation type — narrator sees header + prose + empty body". In practice no shipped genre pack has a single confrontation type (every pack has at least combat + one social/exploration flavor), but the subagent's concern is real for pathological or half-built packs.

**Dismissed as non-blocking.** The OTEL event already fires with `alternative_count: 0`, which is the mechanical fingerprint the GM panel needs to detect "guidance injected but empty". That is sufficient observability; adding a suppress-when-empty optimization would require either re-introducing the Vec allocation we just removed in the verify phase or doing a pre-count pass, both of which degrade the simplify-efficiency fix for a marginal benefit. Follow-up: if a playtest against a single-type pack ever shows narrator confusion from the empty menu, revisit with a sentinel line ("no transition targets") instead of suppressing the section.

### Known Limitation Documented (not blocking)

**Finding:** test-analyzer #3 correctly points out that test 7 (`transition_guidance_is_below_build_prompt_context_declaration`) is insufficient to prove the transition block sits at the CORRECT nesting depth inside `build_prompt_context`. A hypothetical Dev could move the block one level deeper (into the `if let Some(def)` arm), passing all 7 tests while silently regressing the def-missing recovery path.

**Accepted as a limit of the source-scan convention.** Source-scan tests are a text contract, not a structural one. The strongest structural anchor we could add without building a full `DispatchContext` is a scan for a unique comment marker (`// 37-12: transition block — outside def guard`) and a test that it appears after `format_encounter_context` but before the closing brace of the outer guard — but that chain of string offsets starts to approximate a poor man's AST walker and would be fragile to unrelated edits in prompt.rs. The honest cost-benefit is: the current tests catch the 99% failure modes (missing marker, dead helper, wrong phrasing, missing OTEL event), and the 1% nesting-depth regression is the reviewer's job to catch at review time. I caught it this round; that's the point of adversarial review.

### Follow-Up Tickets (out of scope, opened mentally — not filing now)

1. **`encounter_gate.rs:10-12` stale comment** — flagged by comment-analyzer. The 37-13 doc comment claims it IS the root-cause fix for 37-12. It's not. It's the dispatch-side prerequisite. Future agents reading that comment might dismiss 37-12 follow-ups as "already shipped" (exactly the pattern Keith's memory `feedback_verify_story_not_already_shipped.md` warns about). Open a chore ticket to soften the wording.

2. **`AVAILABLE CONFRONTATIONS` block duplication** — flagged by edge-hunter #3. The block at `prompt.rs:362` runs unconditionally when defs exist, so mid-encounter the narrator sees both that list AND the new `TRANSITION CONFRONTATION` list, with slightly different framing. This is a pre-existing design; 37-12 only makes it more visible. A future cleanup story should either (a) guard `AVAILABLE CONFRONTATIONS` on `encounter.is_none()` like the other `AVAILABLE ENCOUNTER TYPES` block, or (b) merge the two blocks into a single prompt section with both framings inline.

3. **YAML field injection in prompt format strings** — flagged by edge-hunter #4 at medium confidence. The `format!("- \"{}\" ({}, {})\n", alt.confrontation_type, alt.label, alt.category)` pattern doesn't escape quotes or newlines in the field values. A malicious or malformed genre pack could break out of the quoted literal. Pre-existing surface (line 372 in the same file does the same thing), not introduced by 37-12. Appropriate fix is validation at `ConfrontationDef` deserialization time, not at prompt-format time.

4. **Single-type genre pack edge case** — flagged by edge-hunter #2. See "Load-Bearing Judgments" above; only actionable if a real playtest surfaces narrator confusion.

5. **`dirs = "5"` inline version pin** — flagged by rule-checker. Pre-existing workspace-deps rule violation in `sidequest-server/Cargo.toml`. Not in this diff.

### Rule Compliance Summary

All 15 Rust lang-review checks walked exhaustively by the rule-checker:
- 13 clean (including all type/security rules, which were N/A for this prompt-string fix)
- 1 applied this round (#6 test quality — phrase test narrowing)
- 1 pre-existing (#11 workspace deps — `dirs` inline pin, outside diff)

Zero rules were violated by code this PR introduces.

### Wiring Verification

Per CLAUDE.md § "Verify Wiring, Not Just Existence":
- `build_prompt_context` is called from `crates/sidequest-server/src/dispatch/mod.rs:628` on the production narrator path
- The TRANSITION CONFRONTATION block sits inside `build_prompt_context` (test 7 verifies this with a source-scan on `fn build_prompt_context` position)
- `encounter.transition_guidance_injected` OTEL event is observable via the `/ws/watcher` endpoint and will surface in the GM panel's existing encounter filter on the next playtest — no config change required because the event's `component == "encounter"` matches the filter that the 37-13 events already use

**Handoff:** To Hawkeye (SM) for merge and finish ceremony. Ready to push branch and open PR.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Observation** (non-blocking): Story 37-12 and Story 37-13 were split as symptom vs. root cause, and the 37-13 module doc at `dispatch/encounter_gate.rs:10-12` claims it IS the root-cause fix for 37-12. It isn't — 37-13 fixed the dispatch-side *receiver*, 37-12 fixes the prompt-side *sender*. Both halves are needed. The 37-13 doc comment should be softened in a future cleanup pass (not in this story) to avoid the next agent dismissing 37-12 as "already shipped". Affects `crates/sidequest-server/src/dispatch/encounter_gate.rs` (doc comment lines 10-12). *Found by TEA during test design.*

### TEA (test verification)
- No upstream findings during test verification. Simplify found one high-confidence efficiency improvement that was applied in-scope; one medium-confidence reuse finding was dismissed as premature abstraction.

### Reviewer (code review)
- **Improvement** (non-blocking): `dispatch/encounter_gate.rs:10-12` claims 37-13 is "the root cause for 37-12". It isn't — 37-13 is the dispatch-side prerequisite; the root cause fix is this diff's prompt change. Future agents reading that comment might conclude 37-12 is already shipped and skip the prompt fix. Soften to "dispatch-side prerequisite for 37-12 — prompt-side fix ships separately". Affects `crates/sidequest-server/src/dispatch/encounter_gate.rs` (doc comment lines 10-12). *Found by Reviewer during code review (comment-analyzer subagent).*
- **Improvement** (non-blocking): `AVAILABLE CONFRONTATIONS` block at `prompt.rs:362` runs unconditionally when defs exist, so mid-encounter the narrator now sees both that list AND the new `TRANSITION CONFRONTATION` list. Pre-existing design; 37-12 only makes it more visible. Consider guarding the former on `encounter.is_none()` or merging the two into a single section with dual framing. Affects `crates/sidequest-server/src/dispatch/prompt.rs:362`. *Found by Reviewer during code review (edge-hunter subagent).*
- **Improvement** (non-blocking): Genre-pack field format in `format!("- \"{}\" ({}, {})\n", ...)` does not escape quotes or newlines in `confrontation_type`/`label`/`category`. A crafted or malformed YAML could break the prompt quoting. Pre-existing surface at line 372 in the same file. Fix belongs at `ConfrontationDef` deserialization, not at prompt format time. Affects `crates/sidequest-server/src/dispatch/prompt.rs` (lines 372 and the new 437) and `crates/sidequest-genre/src/models/rules.rs` (validation layer). *Found by Reviewer during code review (edge-hunter subagent, medium confidence).*

### Dev (implementation)
- **Improvement** (non-blocking): The `action` field vs. `event` field naming across watcher events in `dispatch/prompt.rs` is inconsistent — the context_injected event uses `.field("action", "context_injected")` while my new transition event uses `.field("event", "encounter.transition_guidance_injected")` (matching the 37-13 gate's convention). The GM panel can filter on either, but a future cleanup should standardize on one key across prompt.rs. Affects `crates/sidequest-server/src/dispatch/prompt.rs` (lines 383 and 452 use different field names for the same semantic). *Found by Dev during implementation.*
- **Question** (non-blocking): Should there be a rate limit or cooldown on how often the narrator is prompted to transition, to prevent chain-transitions ("combat → chase → standoff → combat" on a single turn)? 37-13's Case E rejects mid-encounter re-emits (beat > 0) so there's already a backstop, but the prompt now actively invites transitions on every active-encounter turn. A playtest will show whether this is over-eager. Not blocking for this story; flagging for GM panel observation post-merge. *Found by Dev during implementation.*

## Impact Summary

**Upstream Effects:** 2 findings (0 Gap, 0 Conflict, 0 Question, 2 Improvement)
**Blocking:** None

- **Improvement:** `dispatch/encounter_gate.rs:10-12` claims 37-13 is "the root cause for 37-12". It isn't — 37-13 is the dispatch-side prerequisite; the root cause fix is this diff's prompt change. Future agents reading that comment might conclude 37-12 is already shipped and skip the prompt fix. Soften to "dispatch-side prerequisite for 37-12 — prompt-side fix ships separately". Affects `crates/sidequest-server/src/dispatch/encounter_gate.rs`.
- **Improvement:** The `action` field vs. `event` field naming across watcher events in `dispatch/prompt.rs` is inconsistent — the context_injected event uses `.field("action", "context_injected")` while my new transition event uses `.field("event", "encounter.transition_guidance_injected")` (matching the 37-13 gate's convention). The GM panel can filter on either, but a future cleanup should standardize on one key across prompt.rs. Affects `crates/sidequest-server/src/dispatch/prompt.rs`.

### Downstream Effects

- **`crates/sidequest-server/src/dispatch`** — 2 findings

### Deviation Justifications

3 deviations

- **Exclude current encounter type from alternatives list**
  - Rationale: TEA's brief explicitly called for this. The narrator declaring a transition TO the current type is redundant prompt noise and the gate silently no-ops on it (Case C). Listing only alternatives keeps the prompt lean.
  - Severity: minor (follows TEA brief, not a spec departure)
  - Forward impact: none — genre packs with a single confrontation type will emit an empty alternatives list (`alternative_count: 0`), and the GM panel can flag that as a content gap without any code change.
- **Transition block placement below def resolution, not inside it**
  - Rationale: Hiding the transition guidance behind "current def is parseable" would create a second failure mode: "narrator cannot signal a transition if the current encounter has a broken def." That would be a fresh silent fallback. Placing the block at the outer guard level means the narrator can ALWAYS see transition options while an encounter is active, and the broken-def case is independently surfaced via the existing ValidationWarning.
  - Severity: minor (architectural placement decision, not an AC departure)
  - Forward impact: reviewer should confirm the placement is legible; one extra level of indentation might feel awkward but the nested structure is the honest representation of "active encounter AND defs present."
- **Source-scan tests instead of behavioral tests**
  - Rationale: `DispatchContext` carries 50+ fields including `AppState`, `Arc<Mutex<SharedGameSession>>`, render queue, music director, audio mixer, unbounded mpsc sender, and lore store — constructing one for an integration test would be an order of magnitude larger than the prompt-string fix itself, and no existing test does so. The 28-4 precedent source-scans the same file for the same kind of prompt-contract change. Wiring is implicit because `build_prompt_context` is the SOLE production narrator prompt entry point in `prompt.rs`, and test 7 explicitly verifies the marker is positioned below that function's declaration (catching the dead-helper failure mode).
  - Severity: minor
  - Forward impact: Reviewer should confirm during verify phase that the new lines are actually reached at runtime by inspecting `encounter.transition_guidance_injected` events in the GM panel during a live playtest. Source-scan tests prove the source contains the right strings; only OTEL observation proves they execute.

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Exclude current encounter type from alternatives list**
  - Spec source: TEA Assessment § "Notes for Dev" item 2, SM Assessment
  - Spec text: "Lists the OTHER confrontation types (exclude `enc.encounter_type` — a narrator re-declaring its own type is handled by the gate's Case C no-op anyway, no need to tempt it)"
  - Implementation: Filter `ctx.confrontation_defs.iter().filter(|d| d.confrontation_type != enc.encounter_type)` before rendering the list.
  - Rationale: TEA's brief explicitly called for this. The narrator declaring a transition TO the current type is redundant prompt noise and the gate silently no-ops on it (Case C). Listing only alternatives keeps the prompt lean.
  - Severity: minor (follows TEA brief, not a spec departure)
  - Forward impact: none — genre packs with a single confrontation type will emit an empty alternatives list (`alternative_count: 0`), and the GM panel can flag that as a content gap without any code change.

- **Transition block placement below def resolution, not inside it**
  - Spec source: CLAUDE.md § "No Silent Fallbacks"
  - Spec text: "If something isn't where it should be, fail loudly. Never silently try an alternative path, config, or default."
  - Implementation: The TRANSITION CONFRONTATION block is positioned after the `if let Some(def) = find_confrontation_def(...) { ... } else { ValidationWarning }` pair but still inside the outer `if let Some(ref enc) = ctx.snapshot.encounter` guard. It therefore fires even when the current encounter's def is missing (the `else` branch already logs a ValidationWarning for that case).
  - Rationale: Hiding the transition guidance behind "current def is parseable" would create a second failure mode: "narrator cannot signal a transition if the current encounter has a broken def." That would be a fresh silent fallback. Placing the block at the outer guard level means the narrator can ALWAYS see transition options while an encounter is active, and the broken-def case is independently surfaced via the existing ValidationWarning.
  - Severity: minor (architectural placement decision, not an AC departure)
  - Forward impact: reviewer should confirm the placement is legible; one extra level of indentation might feel awkward but the nested structure is the honest representation of "active encounter AND defs present."

### TEA (test verification)
- No deviations during verify phase. Simplify findings were in-scope (efficiency fix applied, reuse dismissed per project rules); no new tests added; no spec departures.

### TEA (test design)
- **Source-scan tests instead of behavioral tests**
  - Spec source: CLAUDE.md § "Every Test Suite Needs a Wiring Test" + Story 37-12 SM Assessment (`.session/37-12-session.md`)
  - Spec text: "Write failing integration test that verifies narrator re-emits `confrontation_type` when the encounter transitions... Verify wiring end-to-end: narrator LLM output → parser → encounter state → UI render path."
  - Implementation: All 7 tests are source-scan assertions on `dispatch/prompt.rs` via `include_str!`, following the Story 28-4 convention. No test instantiates `DispatchContext` and calls `build_prompt_context` directly.
  - Rationale: `DispatchContext` carries 50+ fields including `AppState`, `Arc<Mutex<SharedGameSession>>`, render queue, music director, audio mixer, unbounded mpsc sender, and lore store — constructing one for an integration test would be an order of magnitude larger than the prompt-string fix itself, and no existing test does so. The 28-4 precedent source-scans the same file for the same kind of prompt-contract change. Wiring is implicit because `build_prompt_context` is the SOLE production narrator prompt entry point in `prompt.rs`, and test 7 explicitly verifies the marker is positioned below that function's declaration (catching the dead-helper failure mode).
  - Severity: minor
  - Forward impact: Reviewer should confirm during verify phase that the new lines are actually reached at runtime by inspecting `encounter.transition_guidance_injected` events in the GM panel during a live playtest. Source-scan tests prove the source contains the right strings; only OTEL observation proves they execute.