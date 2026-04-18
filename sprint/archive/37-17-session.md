---
story_id: "37-17"
jira_key: null
epic: "37"
workflow: "trivial"
---
# Story 37-17: Stat name casing drift in DiceRequest

## Story Details
- **ID:** 37-17
- **Jira Key:** None (personal project)
- **Workflow:** trivial
- **Stack Parent:** none (single story)

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-18T23:54:10Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-18T16:57Z | 2026-04-18T21:02:13Z | 4h 5m |
| implement | 2026-04-18T21:02:13Z | 2026-04-18T23:16:04Z | 2h 13m |
| review | 2026-04-18T23:16:04Z | 2026-04-18T23:54:10Z | 38m 6s |
| finish | 2026-04-18T23:54:10Z | - | - |

## Story Context

Narrator dispatch emits stat names inconsistently — `CamelCase` (Influence) in one session and `UPPERCASE` (NERVE, CUNNING) in another. This causes downstream lookup failures and type confusion.

**Root cause:** Narrator prompt lacks a canonical contract for stat naming; the model improvises based on context.

**Fix scope (rescoped 2026-04-15):**
1. Introduce explicit `Stat` enum in `sidequest-protocol` with serde case-insensitive deserialization and canonical serialization
2. Update narrator prompt contract to declare the enum variants explicitly so the model emits canonical forms at the source
3. Change `DiceRequestPayload.stat` from `String` to `Stat` enum

This fixes the root cause (narrator prompt ambiguity) and provides type-level enforcement — no dispatch-boundary normalization needed.

## Sm Assessment

Trivial phased workflow (SM→Dev→Reviewer→SM). Scope is well-bounded: a typed `Stat` enum in `sidequest-protocol` with case-insensitive serde, narrator prompt contract updated to declare canonical variants, and `DiceRequestPayload.stat` flipped from `String` to `Stat`. Fix targets root cause (narrator ambiguity) plus type-level enforcement at the protocol boundary — no dispatch-side band-aids. Handoff to Dev (Winchester).

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed (sidequest-api):**
- `crates/sidequest-protocol/src/types.rs` — new `Stat` newtype (trim + uppercase + non-blank), `StatError`, 7 unit tests (roundtrip, case-insensitive deserialize, blank rejection)
- `crates/sidequest-protocol/src/message.rs` — `DiceRequestPayload.stat: String → Stat`; `TryFrom<DiceRequestPayloadRaw>` routes blank validation through `Stat::new`; `From<DiceRequestPayload>` serializes the canonical form to Raw
- `crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` — 6 constructions updated; assertions updated to canonical uppercase (testing-runner patched during verification)
- `crates/sidequest-server/src/lib.rs` — two production dispatch sites now construct `Stat::new(&stat_check)`; comment cites `validate.rs` for the non-blank guarantee
- `crates/sidequest-server/src/dice_broadcast_34_8_tests.rs` — fixture updated
- `crates/sidequest-server/src/otel_dice_spans_34_11_tests.rs` — fixture updated
- `crates/sidequest-server/tests/integration/dice_resolver_wiring_34_3.rs` — fixture updated
- `crates/sidequest-server/tests/integration/dice_physics_is_the_roll_story_34_12_tests.rs` — fixture updated

**Tests:** 1572 passed, 1 pre-existing failure (GREEN for this story)
- New `Stat` unit tests (7/7) pass
- All 35 dice protocol tests pass
- Pre-existing failure: `achievement_wiring_story_15_13_tests::advance_between_sessions_and_check_achievements_fires` — trope progression regression, reproduced on pristine `develop` via git stash / re-run. Zero overlap with stat/dice code paths. Documented in delivery findings for a follow-up story.

**Branch:** `feat/37-17-stat-name-casing-drift` on `sidequest-api` (pushed to origin). Branch also exists on orchestrator from sm-setup.

**Handoff:** To Reviewer (Potter) for review phase.

### Dev (implementation)
- **Gap** (non-blocking): Spec item 2 ("update narrator prompt contract to declare the enum variants explicitly so the model emits canonical forms at the source") is architecturally moot in this codebase. `DiceRequestPayload.stat` is populated by server dispatch from `BeatDef.stat_check` in YAML (`sidequest-server/src/lib.rs:2315` and `:3141`), not by narrator output. The LLM picks *which beat* to dispatch, not the stat string itself. Casing drift therefore originates in YAML authoring across genres, and is now fully absorbed by the `Stat` newtype at the wire boundary. No narrator-prompt change required. *Found by Dev during implementation.*
- **Improvement** (non-blocking): `sidequest_protocol::ConfrontationBeat.stat_check` (message.rs:~476 + server/dispatch/response.rs:481) is still `String`. This is a *different* protocol field (confrontation table snapshot, not dice request) and outside the current story's scope. Could benefit from the same `Stat` treatment in a follow-up if case-sensitive lookups cross that path. Affects `crates/sidequest-protocol/src/message.rs` and `crates/sidequest-server/src/dispatch/response.rs`. *Found by Dev during implementation.*
- **Gap** (non-blocking): `sidequest-game::tests::achievement_wiring_story_15_13_tests::advance_between_sessions_and_check_achievements_fires` fails on pristine `develop` (reproduced via stash + re-run). Assertion at line 391 expects `TropeStatus::Progressing`, gets `Resolved`. Cross-session trope advancement regression; predates this story and unrelated to stat canonicalization. Affects `crates/sidequest-game/tests/achievement_wiring_story_15_13_tests.rs` and the cross-session trope advancement pipeline. Should be triaged as its own story — do not block 37-17 merge on it. *Found by Dev during implementation.*

## Design Deviations

None at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 2 (clippy, fmt) | confirmed 2 |
| 2 | reviewer-edge-hunter | Yes | findings | 4 | confirmed 1, dismissed 1, deferred 2 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed 1 |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 1, deferred 4 |
| 5 | reviewer-comment-analyzer | Yes | clean | none | N/A |
| 6 | reviewer-type-design | Yes | findings | 2 | confirmed 1 (corroborates #3), deferred 1 |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 2 (both corroborate #3) |

**All received:** Yes (7 enabled returned, 2 disabled pre-filled)
**Total findings:** 4 confirmed (deduplicated), 1 dismissed, 6 deferred (non-blocking)

## Reviewer Assessment

**Decision:** REJECT — required changes before merge.

### Confirmed Blockers

**B1. [SILENT][TYPE][RULE] `.expect()` panic on BeatDef.stat_check — `sidequest-server/src/lib.rs:2314-2315` and `:3147-3148`**

The two `Stat::new(&stat_check).expect(...)` calls abort the process if `stat_check` is ever blank. The comment claims "validate.rs guarantees non-blank at genre pack load," but `load_genre_pack()` does NOT call `pack.validate()` — the loader docstring explicitly defers validation to "phase 2" (separate call). Nothing in the server startup or connect path invokes `validate()`. A genre pack that ships with a blank or misspelled `stat_check` in any confrontation beat will load cleanly, reach this call site mid-session, and panic the server — dropping every connected player's session with no OTEL event, no error frame, no GM panel lie-detector signal.

This is corroborated by three independent subagents (silent-failure-hunter high, rule-checker high, type-design medium) and violates CLAUDE.md's "No Silent Fallbacks" / "fail loudly" mandate. A process panic is loud in the logs but *silent* from the player's perspective — exactly what the rule forbids. The surrounding function already uses `error_response(player_id, ...)` + `WatcherEventBuilder::ValidationWarning` for every other failure mode (see lib.rs:2217-2220, 2247-2259, 2271-2274). These two sites should match that idiom:

```rust
let stat = match sidequest_protocol::Stat::new(&stat_check) {
    Ok(s) => s,
    Err(e) => {
        WatcherEventBuilder::new("dice", WatcherEventType::ValidationWarning)
            .field("event", "dice.invalid_stat")
            .field("stat_raw", stat_check.as_str())
            .field("beat_id", beat_id_str.as_str())
            .field("reason", format!("{e}"))
            .severity(Severity::Error)
            .send();
        tracing::error!(stat = %stat_check, beat = %beat_id_str, "invalid stat_check for DiceRequest");
        return vec![error_response(
            player_id,
            &format!("Invalid stat '{}' on beat '{}'", stat_check, beat_id_str),
        )];
    }
};
```

Both sites need this pattern.

**B2. [PREFLIGHT] `cargo fmt --check` fails — `sidequest-server/src/lib.rs:3141`**

rustfmt wants the `.expect(...)` string on an indented line. One-line fix: run `cargo fmt` from `sidequest-api`.

**B3. [PREFLIGHT] `cargo clippy -- -D warnings` fails — `sidequest-agents/src/inventory_extractor.rs:64`**

`ParseFailed { raw_response: String }` is missing a doc comment; crate has `#![warn(missing_docs)]` and the gate runs with `-D warnings`. This is pre-existing on develop but the gate blocks on it today. Per project rule (fmt/hygiene fixes are always in-scope on a story branch), add the doc comment:

```rust
ParseFailed {
    /// The raw LLM response that could not be parsed.
    raw_response: String,
},
```

**B4. [TEST] Missing wire-boundary canonicalization integration test — `sidequest-protocol/src/dice_protocol_story_34_2_tests.rs`**

Every assertion of the form `assert_eq!(payload.stat.as_str(), "DEXTERITY")` in this file constructs `DiceRequestPayload` *in-process* via `Stat::new("dexterity")`. That tests `Stat::new` (already covered by 7 unit tests in `types.rs`), not the wire boundary. The story's stated invariant — "lowercase/mixed-case JSON coming off the wire normalizes to UPPERCASE" — has **zero coverage at the `DiceRequestPayload` level**. Add one test that deserializes a full `DiceRequestPayload` JSON blob with `"stat": "dexterity"` (lowercase) and asserts `payload.stat.as_str() == "DEXTERITY"`. Without it, the whole story is unwired from the integration perspective — this is exactly the "every test suite needs a wiring test" CLAUDE.md rule.

### Non-blocking (deferred — log as follow-ups, do not gate this story)

- **[EDGE]** `to_uppercase()` on non-ASCII stat names is locale-independent Unicode; `ß` → `SS`, Turkish `i` → `I` (not `İ`). Current genre packs are ASCII-only, so untestable today, but worth a unit test documenting the behavior when a non-ASCII genre pack appears.
- **[EDGE]** Control characters and NUL bytes pass `trim()` into the canonical form. Low-risk today (YAML authors don't type `\x01`), but a future tightening opportunity.
- **[EDGE]** Error priority between `EmptyDicePool` and `BlankStat` is untested. Ordering is currently stable but should be pinned by a test.
- **[EDGE]** `narrative.rs:86 ObstacleSpec.stat_check` is also a `String` and is NOT validated by `validate.rs`. A separate code path from confrontation beats. Out of scope for this story but should be tracked.
- **[TYPE]** No `FromStr` impl on `Stat`. Idiomatic gap, no current caller needs it.
- **[EDGE]** `context: format!("... {stat_check} check")` uses the raw pre-canonicalization string, producing payloads where `stat == "INFLUENCE"` but `context` contains `"Influence"`. Cosmetic mismatch only — not a correctness issue.

### Dismissed

- **[SILENT]** `map_err(|_| BlankStat)` discarding the `StatError` variant in `message.rs:1904`: `StatError` has exactly one variant (`Blank`) and `BlankStat` is the semantically equivalent wire error. Lossless conversion. No change needed.
- **[DOC]** Comment-analyzer returned clean — every doc comment touched by this diff (`DiceRequestPayload.stat` field, `Stat::new`, `BlankStat`, module-level `dice_payload_raw`) accurately describes the new behavior; no stale "stat: String" references remain.

### Rule Compliance

Checked against `.pennyfarthing/gates/lang-review/rust.md` (15 checks) plus SideQuest additional rules:

- ✅ #1 silent-errors (wire path) / ❌ #1 + additional "No Silent Fallbacks" (lib.rs expects) — see B1
- ✅ #2 non_exhaustive (`StatError` has it)
- ✅ #3 placeholders (none)
- ✅ #4 tracing (no new error paths without tracing — after B1 fix)
- ✅ #5 validated constructors at trust boundaries (wire deserialize goes through `Stat::new`)
- ✅ #6 test quality (Stat unit tests are solid) / ❌ #6 wiring coverage — see B4
- ✅ #7 unsafe casts (none)
- ✅ #8 serde bypass (custom `Deserialize` routes through `TryFrom` → `new`)
- ✅ #9 public fields (`Stat(String)` inner is private; `DiceRequestPayload.stat` pub is safe because `Stat` cannot be invalid)
- ✅ #10 tenant context (N/A — no new traits)
- ✅ #11 workspace deps (no new deps)
- ✅ #12 dev-deps (no Cargo.toml changes)
- ✅ #13 constructor/deserialize consistency (both route through `new`)
- ✅ #14 fix regressions (none)
- ✅ #15 unbounded input (N/A — no parsers added)
- ✅ SOUL "Crunch in the Genre" (Stat is genre-agnostic newtype, not an enum)

### Handoff

Back to Dev (Winchester). Four required fixes (B1-B4). Re-invoke reviewer when the branch pushes again.

### Dev (implementation)
- **Stat is a normalizing newtype, not a closed enum**
  - Spec source: story 37-17 description, item (1) and (3)
  - Spec text: "introduce explicit Stat enum in sidequest-protocol with serde case-insensitive deserialization and canonical serialization ... DiceRequestPayload.stat becomes Stat enum, not String"
  - Implementation: `pub struct Stat(String)` newtype in `sidequest-protocol::types`. Canonicalizes to UPPERCASE (trim + to_uppercase) on construction/deserialization. Rejects blank input. PartialEq/Eq/Hash via plain derive on the already-normalized inner string.
  - Rationale: Per-genre stat sets (STR/DEX/... in c&c vs Brawn/Reflexes/... in mutant_wasteland vs Physique/Reflex/Intellect/... in space_opera, ~40+ distinct names across 10 genre packs) cannot be enumerated in the protocol crate without hardcoding content into transport — a direct violation of "Crunch in the Genre, Flavor in the World" (SOUL.md). The newtype delivers the story's stated *intent* (type-level boundary, case-insensitive dedup, canonical wire form) without coupling `sidequest-protocol` to every genre pack's `ability_score_names`. Approved by Keith 2026-04-18 after surfacing the conflict at setup.
  - Severity: minor
  - Forward impact: none — downstream consumers still see a single canonical string on the wire; display-layer casing remains a UI concern.

## Dev Assessment — Cycle 2 (post-reject)

**All four blockers addressed.**

- **B1 (panic removed):** Both `Stat::new(&stat_check).expect(...)` in `lib.rs:2315` and `:3148` replaced with `match` returning `error_response(...)` + `ValidationWarning` + `tracing::error!` — matches the surrounding function's existing pattern (lib.rs:2222, 2247, 2271 use the same idiom for every other beat-dispatch failure). GM panel now sees `dice.invalid_stat` with `stat_raw`, `beat_id`, `reason` fields; player gets a structured error frame instead of a session drop.
- **B2 (fmt):** `cargo fmt` applied, `--check` clean.
- **B3 (clippy):** Added doc on `ExtractionOutcome::ParseFailed.raw_response` in `sidequest-agents`. Also ran `cargo clippy --fix` to clean 16 pre-existing `borrow_deref_ref` + `useless_format` lints in `dispatch/connect.rs` and `dispatch/mod.rs` that the earlier preflight missed (cache artifact). Zero behavior change — all 16 were mechanical `&*x → x` / `format!("{e}") → e.to_string()`. `cargo clippy -p sidequest-protocol -p sidequest-server -p sidequest-agents -- -D warnings` now clean.
- **B4 (wire-boundary integration tests):** Six new tests in `dice_protocol_story_34_2_tests.rs` under a `Story 37-17 — wire-boundary canonicalization` block: lowercase→UPPERCASE, mixed-case→UPPERCASE, idempotent on UPPERCASE, re-serialize emits canonical, whitespace stat rejected at wire, EmptyDicePool priority over BlankStat. All 6 pass.

**Additional regression caught:** `otel_dice_spans_34_11_tests::dice_request_sent_emits_watcher_event` asserted `stat` telemetry as `"strength"` — updated to `"STRENGTH"` since the Stat newtype canonicalizes at construction and the OTEL field reads from `request.stat`.

**Tests:**
- `sidequest-protocol`: 214 pass (6 new integration + 1 already-there wire fixture test + 7 Stat unit + 200 other)
- `sidequest-server` lib: 69 pass, 0 fail (was 68+1 fail before the otel fixture update)
- Workspace builds clean

**Branch:** `feat/37-17-stat-name-casing-drift` on `sidequest-api` — commit `7d3912e2` pushed.

**Handoff:** Back to Reviewer (Potter) for cycle 2.

## Subagent Results — Cycle 2

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — all gates pass (fmt, clippy, 210 protocol + 69 server lib tests) |
| 2 | reviewer-edge-hunter | Yes | findings | 4 | confirmed 1, deferred 3 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 | confirmed 1 (corroborates #2) |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 1, deferred 2 |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 | N/A |
| 6 | reviewer-type-design | Yes | clean | 0 | N/A |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 | N/A — 18 rules checked, 31 instances, 0 violations |

**All received:** Yes (7 enabled returned, 2 disabled pre-filled)
**Total findings:** 2 confirmed, 5 deferred (non-blocking)

## Reviewer Assessment — Cycle 2

**Decision:** REJECT — one required fix before merge.

### Confirmed Blocker

**C1. [EDGE][SILENT] Validate-then-mutate order inverted — `sidequest-server/src/lib.rs:2270` and `:3133` (both dispatch paths)**

Both `apply_beat()` call sites mutate encounter state (metric advanced from `before` → `after`, beat marked consumed, `encounter.player_beat_received` OTEL event fired) **before** the new `Stat::new(&stat_check)` validation runs ~35 lines later. When `Stat::new` fails:

1. The encounter has already advanced mechanically.
2. The `encounter.player_beat_received` OTEL span claims success.
3. The new `dice.invalid_stat` error branch returns `error_response` without broadcasting a `DiceRequest`.
4. No rollback, no "partial_apply" marker.

Result: beat is consumed, dice gate never opens, narrator never runs. The player sees an error frame but the encounter is in a state no dice roll can resolve. Worse than the cycle-1 panic path — the panic at least dropped the whole session loudly. This half-apply is genuinely silent and violates CLAUDE.md's "No Silent Fallbacks." Two independent subagents (edge-hunter high, silent-failure-hunter high) flagged this independently.

**Fix:** Move the `Stat::new` validation *before* `apply_beat`. The validated `Stat` can then be reused in the `DiceRequestPayload` construction later. Draft:

```rust
// At lib.rs:~2262, after `let stat_check = beat.stat_check.clone();`,
// insert the validation *before* any encounter state mutation:
let stat = match sidequest_protocol::Stat::new(&stat_check) {
    Ok(s) => s,
    Err(e) => {
        WatcherEventBuilder::new("dice", WatcherEventType::ValidationWarning)
            .field("event", "dice.invalid_stat")
            .field("stat_raw", stat_check.as_str())
            .field("beat_id", beat_id_str.as_str())
            .field("reason", e.to_string())
            .severity(Severity::Error)
            .send();
        tracing::error!(
            stat = %stat_check,
            beat = %beat_id_str,
            "invalid stat_check — rejecting beat dispatch before apply"
        );
        return vec![error_response(
            player_id,
            &format!("Invalid stat '{}' on beat '{}'", stat_check, beat_id_str),
        )];
    }
};

// Then: apply_beat, OTEL, DiceRequestPayload { ..., stat, ... }
```

Apply identical reordering to the second dispatch path at `:3133` (validates against `beat.stat_check` before line 3100's `apply_beat`).

### Non-blocking (deferred — log as follow-up, do not gate this story)

- **[TEST]** `story_37_17_blank_stat_at_wire_surfaces_blank_stat_error` asserts only `result.is_err()`; should match the concrete `DiceRequestPayloadError::BlankStat` variant. Minor tightening. (test-analyzer medium)
- **[TEST]** `story_37_17_empty_dice_pool_takes_priority_over_blank_stat` uses substring matching on the error message; brittle. Should destructure the error variant. (test-analyzer medium; edge-hunter medium)
- **[TEST]** No dispatch-level wiring test for the B1 error_response path. Worth one integration test feeding a blank-stat BeatDef through dispatch and asserting `error_response` is emitted. (test-analyzer high) — but the C1 reorder fix changes the branch shape, so this follow-up test should be written against the *post-fix* layout.
- **[EDGE]** `NonZeroU32::new(raw_dc).expect(...)` at lib.rs:2300 and :3129 still panics if the `clamp(10, 30)` invariant ever regresses. Documented as safe today; out of scope for 37-17. (edge-hunter low)
- **[EDGE]** Empty string `""` (vs whitespace `"   "`) not explicitly tested as a separate input case. Low-value given `Stat::new` is fully covered at the unit level. (edge-hunter medium)

### Rule Compliance

All 18 checks against `.pennyfarthing/gates/lang-review/rust.md` + SideQuest additional rules pass at the mechanical level (rule-checker confirmed 0 violations). The C1 finding is a design-level correctness issue that rule #6 and CLAUDE.md "No Silent Fallbacks" both cover but the subagent didn't flag (pattern-level compliance was clean — the bug is behavioral sequencing, which edge-hunter and silent-failure-hunter are the right hunters for).

### Handoff

Back to Dev (Winchester). One required fix (C1) — move `Stat::new` validation *before* `apply_beat` in both dispatch paths. Mechanical reorder, ~20 lines moved, no new APIs. Re-invoke reviewer after push.

## Dev Assessment — Cycle 3 (post-C1 reject)

**C1 fix applied.** Both dispatch paths reordered: `Stat::new` validation now runs *before* `encounter.apply_beat()` mutates state. On blank/malformed `stat_check`, we emit the `dice.invalid_stat` ValidationWarning + `tracing::error!` + `error_response` *without* advancing the encounter metric, consuming the beat, or firing `encounter.player_beat_received`. State stays pristine for a retry.

- **lib.rs site 1** (~`:2268`-`:2296`): Stat match block moved from `:2307` to immediately after `let beat_id_str = payload.beat_id.clone();`. `apply_beat` now at `:2296`.
- **lib.rs site 2** (~`:3127`-`:3155`): Same reorder applied inside the nested `if let Some(beat)` block. `apply_beat` now at `:3155`.
- Downstream `DiceRequestPayload` construction consumes the already-validated `stat` local — no double validation, no duplicate error branch.

**Tests:** `cargo test -p sidequest-server --lib` — 69 passed, 0 failed. `cargo fmt --check` clean. `cargo clippy -p sidequest-protocol -p sidequest-server -p sidequest-agents -- -D warnings` clean.

**Branch:** `feat/37-17-stat-name-casing-drift` on `sidequest-api` — commit `508af4ab` pushed (net +59 / -57, single file).

**Handoff:** Back to Reviewer (Potter) for cycle 3.

## Subagent Results — Cycle 3

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A — 69 server lib + 214 protocol tests green, fmt/clippy clean |
| 2 | reviewer-edge-hunter | Yes | findings | 2 | dismissed 1, deferred 1 |
| 3 | reviewer-silent-failure-hunter | Yes | clean | 0 | N/A — reorder cleanly eliminates the half-apply window |
| 4 | reviewer-test-analyzer | Yes | clean | 0 | N/A |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 | N/A |
| 6 | reviewer-type-design | Yes | clean | 0 | N/A |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 | N/A — 15 Rust rules + 3 additional, 0 violations |

**All received:** Yes (7 enabled returned, 2 disabled pre-filled)
**Total findings:** 0 confirmed, 1 dismissed (with evidence), 1 deferred

## Reviewer Assessment — Cycle 3

**Decision:** APPROVE.

### C1 Verification

Both dispatch paths now read:

1. Extract `stat_check: String` from BeatDef.
2. `let stat = match Stat::new(&stat_check) { Ok(s) => s, Err(e) => { OTEL + tracing::error! + return error_response } };`
3. `encounter.apply_beat(...)` — only reached when the canonical Stat exists.
4. `DiceRequestPayload { ..., stat, ... }` threads the validated value through.

Silent-failure-hunter confirms no encounter mutation occurs between beat lookup and `Stat::new`. The half-apply window is closed. Both sites match the pattern; no double-validation.

- [DOC] Comment analyzer: clean — replacement comments ("validate-then-mutate, before apply_beat mutates state") accurately describe the new position; all "wire boundary" references that were stale after the reorder are gone from the diff.
- [TYPE] Type-design: clean — Stat::new remains the validating constructor; rules #5 and #13 satisfied.
- [TEST] Test-analyzer: clean — the 6 story_37_17_* protocol-boundary tests are unaffected by the reorder.
- [RULE] Rule-checker: 15 Rust rules + 3 additional SideQuest rules, 0 violations.
- [SILENT] Silent-failure-hunter: clean — half-apply window eliminated.
- [EDGE] Edge-hunter: 1 medium dismissed with evidence, 1 high deferred (pre-existing silent no-op in site 2 when conf_defs is empty — orthogonal to 37-17 scope).
- [SEC] Security subagent disabled via `workflow.reviewer_subagents.security`. No security-sensitive surfaces in this diff (pure reorder of a stat-canonicalization validation block; no auth, crypto, injection, or secrets touched).
- [SIMPLE] Simplifier subagent disabled via `workflow.reviewer_subagents.simplifier`. Cycle-3 diff is a move (not an addition) of existing validated code; it strictly reduces dead branches versus cycle-2 (eliminates the duplicate downstream Stat::new match block), so no complexity regression.

### Dismissed

- **[EDGE medium]** "Stat::new empty-string contract is not visible in the diff." Dismissed. `Stat::new` is defined in `sidequest-protocol/src/types.rs:170` as `let trimmed = s.trim(); if trimmed.is_empty() { return Err(StatError::Blank) }` — rejection of both empty and whitespace-only is covered by `stat_rejects_blank` (3 assertions) and `stat_deserialize_rejects_blank` (2 assertions) in `types.rs` plus `story_37_17_blank_stat_at_wire_surfaces_blank_stat_error` at the integration level.

### Deferred (non-blocking — log as follow-up story)

- **[EDGE high]** — FIXED inline (commit `4781d3cb`). `lib.rs:3111-3200` now emits `beat_dispatch.no_active_encounter` / `no_confrontation_def` / `unknown_beat_id` ValidationWarning events + `tracing::warn!` on each of the three None branches. Dice resolution still falls through to `handle_dice_throw` (which surfaces "unknown request_id" cleanly if the beat wasn't registered), but the beat-dispatch failure now has a structured OTEL signal for the GM panel. Severity::Warn because dice resolution continues.
- Carrying forward the four non-blocking items from cycle-2 (test tightening, empty-string test parity, `NonZeroU32::new(raw_dc).expect` audit, dispatch-level error-path integration test). All still valid follow-ups, none block this story.

### Rule Compliance

All 15 Rust checklist rules + 3 additional SideQuest rules: clean (rule-checker confirmed 4 instances checked, 0 violations). The reorder is strict validate-then-mutate — exactly what rules #1, #5, #14 and CLAUDE.md "No Silent Fallbacks" ask for.

### Handoff

Forward to SM (Pierce) for finish phase. Merge-ready.