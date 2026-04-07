---
story_id: "7-8"
jira_key: ""
epic: "Epic 7"
workflow: "tdd"
repos: ["sidequest-api"]
---

# Story 7-8: Scenario Scoring — Evidence Collection Metrics, Accusation Accuracy, Deduction Quality

## Story Details

- **ID:** 7-8
- **Jira Key:** (pending — no Jira integration active)
- **Workflow:** tdd
- **Stack Parent:** 7-4 (accusation system)
- **Points:** 3
- **Epic:** 7 (Scenario System — Bottle Episodes, Whodunit, Belief State)
- **Base Branch:** develop (sidequest-api uses gitflow)
- **Feature Branch:** feat/7-8-scenario-scoring

## Business Context

After a scenario resolves, the player should see how well they investigated. The scenario scoring system provides a structured scorecard with multiple dimensions:

- **Evidence Coverage:** Percentage of available clues found
- **Interrogation Breadth:** Percentage of relevant NPCs questioned
- **Deduction Quality:** Guesswork / Methodical / Masterful based on evidence quality
- **Grade Assignment:** Bronze / Silver / Gold / Failed based on combined metrics

## Technical Scope

**In scope:**
- `ScenarioScore`, `DeductionQuality`, `ScenarioGrade` types
- `score_scenario()` function computing all dimensions
- Evidence coverage, interrogation breadth, deduction quality metrics
- Grade computation from combined metrics
- Unit tests for scoring at each grade tier
- Serialization support for scenario archives

**Out of scope:**
- UI presentation of scorecard (frontend concern)
- Leaderboards or cross-session score comparison
- Scoring affecting future gameplay (score is informational only)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Evidence coverage | Percentage of available clues the player activated |
| Interrogation breadth | Percentage of relevant NPCs the player interacted with |
| Deduction quality | Guesswork/Methodical/Masterful based on evidence quality |
| Grade assignment | Gold requires correct accusation + airtight evidence + high coverage |
| Failed grade | Wrong accusation always results in Failed grade |
| Turn tracking | Total turns recorded in scorecard |
| Serializable | `ScenarioScore` serializes for archive inclusion |

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-07T03:15:30Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-07T00:09:38Z | 2026-04-07T00:10:47Z | 1m 9s |
| red | 2026-04-07T00:10:47Z | 2026-04-07T00:16:18Z | 5m 31s |
| green | 2026-04-07T00:16:18Z | 2026-04-07T00:35:52Z | 19m 34s |
| spec-check | 2026-04-07T00:35:52Z | 2026-04-07T03:06:28Z | 2h 30m |
| verify | 2026-04-07T03:06:28Z | 2026-04-07T03:08:44Z | 2m 16s |
| review | 2026-04-07T03:08:44Z | 2026-04-07T03:14:33Z | 5m 49s |
| spec-reconcile | 2026-04-07T03:14:33Z | 2026-04-07T03:15:30Z | 57s |
| finish | 2026-04-07T03:15:30Z | - | - |

## Delivery Findings

No upstream findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- No upstream findings during test design.

### Dev (implementation)

- No upstream findings during implementation.

### Reviewer (code review)

- **Improvement** (non-blocking): `score_scenario()` emits no OTEL spans. When wired in 7-9, add `tracing::info!` for grade assignment and deduction quality. Affects `crates/sidequest-game/src/scenario_scoring.rs` (add instrument/tracing calls). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Missing test for Airtight + low coverage → Silver branch at `compute_grade():169`. Affects `crates/sidequest-game/tests/scenario_scoring_story_7_8_tests.rs` (add boundary test). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing silent fallback in `scenario_state.rs:152` — guilty_npc defaults to "unknown" when no suspects marked can_be_guilty. Affects `crates/sidequest-game/src/scenario_state.rs` (should return Result). *Found by Reviewer during code review.*

## Sm Assessment

**Story is ready for TDD.** Scenario scoring is a new subsystem within Epic 7 (Scenario System). Single repo (api), depends on 7-4 (accusation system, done). TEA should assess what scenario infrastructure exists in `sidequest-game/src/` and `sidequest-genre/src/models/scenario.rs`, then write failing tests for scoring metrics (evidence collection, accusation accuracy, deduction quality).

**Routing:** Fezzik (TEA) takes the red phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New subsystem — no existing scoring code in sidequest-game

**Test Files:**
- `crates/sidequest-game/tests/scenario_scoring_story_7_8_tests.rs` — 21 tests for scenario scoring

**Tests Written:** 21 tests covering 7 ACs
**Status:** RED (compilation failure — `scenario_scoring` module does not exist)

| AC | Tests | Count |
|----|-------|-------|
| Evidence coverage | full/partial/none/red-herring-exclusion | 4 |
| Interrogation breadth | all/partial/none | 3 |
| Deduction quality | Guesswork/Methodical/Masterful | 3 |
| Grade assignment | Gold/Silver/Bronze | 3 |
| Failed grade | wrong+airtight, wrong+circumstantial | 2 |
| Turn tracking | normal, zero | 2 |
| Serializable | JSON roundtrip | 1 |

**Additional tests:** non_exhaustive (2), empty scenario edge case (1), wiring/export (1)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `deduction_quality_is_non_exhaustive`, `scenario_grade_is_non_exhaustive` | failing (compilation) |
| #6 test quality | Self-check: all 21 tests have meaningful assert_eq!/assert! — no vacuous assertions | pass |

**Rules checked:** 2 of 15 applicable (most rules apply to implementation, not test-only code)
**Self-check:** 0 vacuous tests found

### API Design Encoded in Tests

- `score_scenario(&ScenarioScoreInput) -> ScenarioScore` — single input struct
- `ScenarioScoreInput` bundles: `&ScenarioState`, `&AccusationResult`, `total_turns: u64`, `&[String]` (NPCs questioned)
- `ScenarioScore` has getters: `evidence_coverage()`, `interrogation_breadth()`, `deduction_quality()`, `grade()`, `total_turns()`
- `DeductionQuality`: Guesswork / Methodical / Masterful (non_exhaustive)
- `ScenarioGrade`: Failed / Bronze / Silver / Gold (non_exhaustive)
- Red herrings excluded from evidence coverage denominator
- Wrong accusation → always Failed grade

**Handoff:** To Inigo Montoya (Dev) for implementation

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- No undocumented deviations found. TEA and Dev deviations (both "none") are accurate — the implementation matches the story scope exactly.

### Architect (reconcile)
- No additional deviations found. TEA, Dev, and Reviewer entries are all accurate. Implementation aligns with story scope (types + function + tests + serialization). The two Reviewer delivery findings (OTEL tracing and untested Airtight+low-coverage branch) are logged as improvements for story 7-9, not spec deviations.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/scenario_scoring.rs` — New module: ScenarioScore, DeductionQuality, ScenarioGrade, score_scenario()
- `crates/sidequest-game/src/lib.rs` — Added pub mod + re-exports

**Tests:** 22/22 passing (GREEN)
**Branch:** feat/7-8-scenario-scoring (pushed)

**Handoff:** To next phase (verify)

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 7 ACs verified against implementation:
- Evidence coverage correctly excludes red herrings, handles 0/0 edge case
- Interrogation breadth validates questioned NPCs against scenario role set
- DeductionQuality maps 1:1 from EvidenceQuality
- Grade computation short-circuits on wrong accusation before evidence check
- Turn count stored as-is with no transformation
- Full Serialize/Deserialize via serde derive

**Rust rules compliance:** Private fields with getters (#9), `#[non_exhaustive]` on both enums (#2), no `as` casts on external input (#7 — uses `as f64` only on known-safe `usize` counts).

**Decision:** Proceed to verify

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication |
| simplify-quality | clean | No naming/dead code/readability issues |
| simplify-efficiency | 2 findings | Minor optimization opportunities |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 2 medium-confidence findings:
1. `scenario_scoring.rs:109` — Two-pass filtering in `compute_evidence_coverage()` could be a single fold. Readability trade-off; scenario sizes are small.
2. `scenario_scoring.rs:136` — HashSet allocation in `compute_interrogation_breadth()` could use direct `contains_key()` on the HashMap. Minor for 3-6 NPC scenarios.

**Noted:** 0 low-confidence observations
**Reverted:** 0

**Overall:** simplify: clean (medium findings flagged only, not applied)

**Quality Checks:** Tests 22/22 passing, no clippy issues in changed code
**Handoff:** To Westley (Reviewer) for code review

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (wiring gap) | dismissed 1 — story 7-9 owns wiring into dispatch |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 (all pre-existing) | deferred 3 — logged as delivery findings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 2 | dismissed 2 — see rationale below |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 1, dismissed 1, deferred 1 |

**All received:** Yes (4 returned, 5 disabled)
**Total findings:** 1 confirmed, 4 dismissed (with rationale), 4 deferred

### Finding Decisions

**Preflight — wiring gap (dismissed):** `score_scenario()` has no non-test callers. Story scope explicitly limits to types + function + tests. Story 7-9 ("ScenarioEngine integration — wire scenario into dispatch") owns wiring. The lib.rs re-export and compile-time wiring test satisfy this story's scope.

**Type-design — Deserialize bypass (dismissed):** `#[derive(Deserialize)]` on `ScenarioScore` is required by AC "Serializable — ScenarioScore serializes for archive inclusion." The test suite exercises JSON roundtrip. ScenarioScore is a computed output type — Deserialize is for loading archived scores, not constructing from untrusted input. No invariant violation risk in practice.

**Type-design — primitive obsession on npcs_questioned (dismissed):** Low confidence finding. `&[String]` for NPC names is consistent with codebase-wide convention (see `npc_roles: HashMap<String, ScenarioRole>` in scenario_state.rs).

**Rule-checker #4 — missing OTEL tracing (confirmed, MEDIUM):** `score_scenario()` emits no OTEL spans. Valid per CLAUDE.md OTEL Observability Principle. However, the module has no production callers yet (7-9's job), so OTEL wiring naturally pairs with dispatch wiring. Not blocking.

**Rule-checker #6 — missing test for Airtight+low-coverage→Silver (deferred):** Valid untested branch at `compute_grade():169`. Deferred — TEA can add this in a follow-up or during 7-9 integration.

**Rule-checker A3 — no production callers (dismissed):** Same as preflight wiring gap — story 7-9 scope.

**Silent-failure findings (deferred 3):** All in pre-existing code (scenario_state.rs:152 guilty_npc fallback, scenario_state.rs:98 silent type defaults, accusation.rs:202 credibility default). Logged as delivery findings for future stories.

## Reviewer Assessment

**Verdict:** APPROVED

### Observations (minimum 5)

1. [VERIFIED] `ScenarioScore` fields are private with getters — `scenario_scoring.rs:53-59` fields `evidence_coverage`, `interrogation_breadth`, `deduction_quality`, `grade`, `total_turns` all private; getters at lines 63-85 return by value/copy. Complies with rust-review rule #9.

2. [VERIFIED] Both enums have `#[non_exhaustive]` — `DeductionQuality` at `scenario_scoring.rs:15`, `ScenarioGrade` at `scenario_scoring.rs:27`. Complies with rust-review rule #2.

3. [VERIFIED] Division-by-zero guarded — `compute_evidence_coverage():116-117` returns 0.0 when `total == 0`; `compute_interrogation_breadth():132-133` returns 0.0 when `total_npcs == 0`. Empty scenario test confirms `is_finite()`.

4. [VERIFIED] Wrong accusation always yields Failed — `compute_grade():163-164` short-circuits with `ScenarioGrade::Failed` before examining evidence quality. Tests at lines 390-419 cover both Airtight and Circumstantial cases with wrong accusation.

5. [RULE] [MEDIUM] Missing OTEL tracing — `scenario_scoring.rs` has no `tracing::info!` or `#[instrument]`. Per CLAUDE.md OTEL principle, the grade assignment is a subsystem decision. Natural to add when wiring in 7-9. *(Confirmed from rule-checker #4)*

6. [RULE] [LOW] Untested branch — `compute_grade():169` `EvidenceQuality::Airtight => ScenarioGrade::Silver` (low coverage path) has no dedicated test. All Airtight tests use >80% coverage. *(Confirmed from rule-checker #6)*

7. [VERIFIED] `as f64` casts on safe values — `scenario_scoring.rs:126,144` cast `usize` from `.len()/.count()` (internal game state, not user input). Complies with rust-review rule #7.

8. [SILENT] Pre-existing silent fallbacks in adjacent code — `scenario_state.rs:152` guilty_npc defaults to "unknown"; `scenario_state.rs:98` unknown clue_type/discovery_method silently default; `accusation.rs:202` credibility defaults to 0.5. All pre-existing, not introduced by this PR. Deferred as delivery findings.

9. [TYPE] Deserialize on ScenarioScore — type-design flagged `#[derive(Deserialize)]` bypassing `score_scenario()`. Dismissed: ScenarioScore is a computed output type; Deserialize required by AC for archive roundtrip; no invariant violation risk in practice since values come from trusted archive data.

### Rule Compliance

| Rule | Instances | Compliant | Notes |
|------|-----------|-----------|-------|
| #1 Silent errors | 4 | 4/4 | No .ok()/.unwrap_or_default()/.expect() on user paths |
| #2 non_exhaustive | 2 enums | 2/2 | DeductionQuality, ScenarioGrade |
| #3 Placeholders | 5 values | 5/5 | 0.8 threshold documented; 0.0 guards explicit |
| #4 Tracing | 1 module | 0/1 | **MEDIUM: No OTEL spans** |
| #5 Constructors | 2 types | 2/2 | No trust-boundary constructors needed |
| #7 Unsafe casts | 4 casts | 4/4 | usize→f64 on internal counts |
| #8 Deserialize bypass | 2 types | 2/2 | Enums have no invariants; ScenarioScore is computed output |
| #9 Public fields | 2 structs | 2/2 | ScenarioScore private+getters; ScenarioScoreInput is input bundle |
| #10 Tenant context | 0 traits | N/A | No trait methods; no tenant data |
| #11 Workspace deps | 0 changes | N/A | No Cargo.toml changes |
| #15 Unbounded input | 3 fns | 3/3 | Flat iteration only |

### Data Flow Trace

`ScenarioState` (clue graph + discovered clues + NPC roles) + `AccusationResult` (quality + correctness) → `score_scenario()` → `ScenarioScore` (all computed values). Pure function with no side effects, no I/O, no state mutation. Input is already-validated game state.

### Devil's Advocate

What if this code is broken? The most likely failure mode is **semantic incorrectness in grading** — the 0.8 coverage threshold for Gold is a magic number that could produce surprising results at boundary values. What happens at exactly 0.8? The guard is `> 0.8`, so 80.0% exactly yields Silver, not Gold. Is that intentional? The AC says "high coverage" which is ambiguous — but the test uses 5/6 = 83.3% which passes. No test exercises the exact boundary (4/5 = 0.8 exactly). A player who finds exactly 80% of clues with airtight evidence gets Silver, not Gold. This is likely fine but worth documenting.

What about deserialization of a tampered ScenarioScore? If someone edits a save file and sets `evidence_coverage: 999.0`, the getters return it verbatim. But ScenarioScore is informational-only (explicitly out of scope for gameplay effects), so a tampered scorecard is harmless — it's like writing a fake grade on your own report card that nobody else reads.

What about the `npcs_questioned` parameter? It comes from the caller (will be the dispatch handler in 7-9). If the caller passes NPC names not in the scenario's role map, `compute_interrogation_breadth` silently filters them out. This means a caller bug (passing wrong names) produces a lower-than-expected breadth score rather than an error. For an informational scorecard, this is acceptable — silent degradation of a cosmetic metric is not a data integrity issue.

What about concurrent scoring? `score_scenario` takes immutable references — no `&mut` anywhere. It's inherently thread-safe. No race conditions possible.

**Conclusion:** The code is simple, correct, well-tested, and scope-appropriate. The untested Airtight+low-coverage branch and missing OTEL are real gaps but not blocking for a library module that will gain both when wired in 7-9.

**Handoff:** To Vizzini (SM) for finish-story