---
story_id: "37-19"
jira_key: null
epic: "37"
workflow: "wire-first"
---
# Story 37-19: Phantom-player dedup on resume

## Story Details
- **ID:** 37-19
- **Jira Key:** (none)
- **Workflow:** wire-first
- **Type:** bug
- **Priority:** p0
- **Points:** 3
- **Repos:** api
- **Stack Parent:** none

## Problem Statement

**Duplicate party entry on resume.** When a player reconnects (same genre:world, same player name), the code correctly:
1. Detects the reconnect via old player_id lookup (connect.rs:2595-2601)
2. Transfers the old PlayerState to the new player_id (connect.rs:2606-2621)
3. Skips creating a new PlayerState because `is_reconnect = true` (connect.rs:2723 guard)

However, a duplicate party entry is being created, causing:
- `player_count` to report 2 when only 1 player is in session
- Structured-mode auto-promotion to create a barrier expecting 2 players
- Barrier deadlock waiting on the phantom second player

**Suspected cause:** The snapshot being loaded from persistence may contain characters that aren't being deduped when they're re-added to the session. The party reconciliation code (connect.rs:2781-2826) checks `ss.players.len() > 1` to decide whether to reconcile, but if the party has duplicates before reconciliation runs, it will reconcile against a phantom player count.

**Solution approach:** Verify that when loading a saved snapshot on resume, the party composition is deduplicated by player_name before any multiplayer logic (party reconciliation, barrier initialization) runs.

## Workflow Tracking
**Workflow:** wire-first
**Phase:** finish
**Phase Started:** 2026-04-18T16:44:08Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-18T11:24Z | 2026-04-18T15:30:04Z | 4h 6m |
| red | 2026-04-18T15:30:04Z | 2026-04-18T15:37:09Z | 7m 5s |
| green | 2026-04-18T15:37:09Z | 2026-04-18T15:52:13Z | 15m 4s |
| review | 2026-04-18T15:52:13Z | 2026-04-18T16:15:30Z | 23m 17s |
| green | 2026-04-18T16:15:30Z | 2026-04-18T16:36:01Z | 20m 31s |
| review | 2026-04-18T16:36:01Z | 2026-04-18T16:44:08Z | 8m 7s |
| finish | 2026-04-18T16:44:08Z | - | - |

## Sm Assessment

**Setup complete.** Session file, branch (`feat/37-19-phantom-player-dedup`), and story context created. Problem statement pinpoints `connect.rs:2595-2826` as the suspect region: PlayerState transfer is correct, but a duplicate party entry is being created that makes `player_count` report 2 on resume.

**Handoff to TEA (red phase):** Write a failing integration test at the session-reconnect boundary. Single-player saves a session, reconnects with a new WebSocket, asserts `player_count == 1` after transfer. Any unit tests must be paired with a wiring test that drives the server resume code path end-to-end (per CLAUDE.md: no wiring-only tests, no tests-only wiring).

**Scope fence:** api only. Do not touch UI — this is a server-side party-reconciliation bug.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (10 compile errors — method `insert_player_dedup_by_name` does not yet exist)

**Test File:**
- `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs` — 9 tests

**Root cause (confirmed during test design):**
Two independent insertion sites into `SharedGameSession::players`:
1. `src/dispatch/connect.rs:2621` + `:2725` — has reconnect detection via `old_pid` lookup by player_name; correctly transfers PlayerState on reconnect.
2. `src/lib.rs:2473` — the `session.is_playing()` returning-player path — unconditionally inserts a fresh PlayerState under the new `player_id` with NO reconnect detection. This is the phantom-entry source.

**Fix contract locked by the tests:**
- Add `SharedGameSession::insert_player_dedup_by_name(&mut self, new_pid: &str, ps: PlayerState) -> Option<String>` that removes any existing entry with the same `player_name` under a different `player_id` and returns the removed `player_id` so the caller can sync the turn barrier, perception filters, and any other external rosters.
- BOTH insertion sites route through this chokepoint. `players.insert(...)` becomes illegal outside `shared_session.rs` (enforced by source-grep wiring tests).
- The chokepoint (or its call sites) emits an OTEL watcher event (`phantom_player_removed` / `player.dedup` / `session.reconnect.phantom`) when a phantom entry is removed — per CLAUDE.md OTEL observability principle.

### Rule Coverage (lang-review/rust.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 hardcoded placeholders | covered by explicit expected pid assertions (`"old-pid"`, `"new-pid"`) — no magic `None`/`Some` unchecked | passing by design |
| #6 test quality — no vacuous `is_none`/`let _` | every test asserts concrete equality; `removed` values are compared to `Some("old-pid".to_string())`, not just `.is_some()` | self-checked |
| OTEL requirement (CLAUDE.md) | `phantom_player_dedup_emits_otel_event` scans lib.rs / connect.rs / shared_session.rs for a dedup telemetry field | failing |
| Wiring — every insert site routed through chokepoint | `lib_returning_player_path_uses_dedup_chokepoint`, `dispatch_connect_insertions_use_dedup_chokepoint`, `no_other_server_src_file_inserts_into_players_directly` | failing |

**Self-check:** No vacuous assertions. No `let _ =`. No `assert!(true)`. Every `assert_eq!` compares against a specific expected value.

**Handoff:** To Dev (Major Charles Emerson Winchester III) for green phase. The RED signal is a compile error on `insert_player_dedup_by_name` — until Dev adds that method to `SharedGameSession`, the integration test binary will not link. Once it links, the wiring tests enforce that both sites are converted and OTEL is emitted.

## Design Deviations

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Dev (implementation, round 2)
- No deviations from spec. Round-2 rework addressed every CRITICAL/HIGH/MEDIUM Reviewer finding directly; no new deviations introduced.

## Delivery Findings

### TEA (test design)
- **Gap** (non-blocking): Story 37-19 has no `sprint/context/context-story-37-19.md` nor `context-epic-37.md`. Setup gate passed anyway. Affects `sprint/context/` (context files should be created for cross-story traceability or the gate updated to stop passing on absence). *Found by TEA during test design.*
- **Improvement** (non-blocking): The existing `src/dispatch/connect.rs` reconnect path already has correct dedup logic — the bug is that a second insertion site in `src/lib.rs:2441-2473` skips it. The RED tests lock dedup as a single chokepoint on `SharedGameSession` rather than asking Dev to duplicate the connect.rs logic into lib.rs. This also catches future regressions where a third insertion site appears elsewhere in `sidequest-server/src`. *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-api/crates/sidequest-server/src/shared_session.rs` — added `SharedGameSession::insert_player_dedup_by_name(new_pid, ps) -> Option<String>` chokepoint. Scans `players` for an entry with matching `player_name` under a *different* `player_id`; if found, removes it, emits a `WatcherEvent::StateTransition` with `event=phantom_player_removed`, `old_player_id`, `new_player_id`, `player_name`, then inserts under `new_pid`. Returns the displaced pid so callers can reconcile downstream state.
- `sidequest-api/crates/sidequest-server/src/lib.rs` (≈line 2478) — returning-player path (`session.is_playing()` branch) now routes through `ss_guard.insert_player_dedup_by_name(player_id, ps)` instead of `ss_guard.players.insert(...)`. This was the phantom source from playtest 2026-04-12.
- `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` (≈lines 2625, 2730) — both the reconnect-transfer insert and the new-player insert route through the chokepoint, keeping the dedup invariant enforced in a single place.
- Incidental `cargo fmt` drift: `dispatch/mod.rs`, `dispatch/sealed_letter.rs`, `dispatch/telemetry.rs`, four sibling test files — whitespace-only reformatting, bundled per project policy (formatting is never scope creep).

**Tests:** 9/9 passing (GREEN)
- Behavioral: `reconnect_same_name_new_pid_collapses_to_single_entry`, `two_different_names_coexist_after_dedup_insert`, `reinsert_same_pid_same_name_is_idempotent`, `dedup_insert_returns_old_pid_not_new_pid`, `player_count_after_solo_reconnect_cannot_trigger_barrier_auto_promotion`
- Source-level wiring: `lib_returning_player_path_uses_dedup_chokepoint`, `dispatch_connect_insertions_use_dedup_chokepoint`, `no_other_server_src_file_inserts_into_players_directly`
- OTEL: `phantom_player_dedup_emits_otel_event`

**Branch:** `feat/37-19-phantom-player-dedup` (will push after commit)

**Wiring verified end-to-end:** chokepoint has two non-test consumers (`lib.rs` returning-player path + `dispatch/connect.rs` transfer and new-player paths), the source-grep wiring tests forbid future regressions, and the OTEL event is emitted from production code (not test harnesses). GM panel can now see every phantom-removal as a `StateTransition` watcher event.

**Handoff:** To review phase.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells; tests 9/9 GREEN; working tree clean; pre-existing clippy debt in sidequest-agents (37-10) is not our regression | confirmed 0, dismissed 0, deferred 1 (pre-existing 37-10 clippy — not this branch) |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | confirmed 3 (lib.rs:2478, connect.rs:2730, AC-9 too-loose string scan), dismissed 3 (connect.rs:2625 safe today — barrier already reconciled by adjacent code; empty-name + case-sensitivity are real concerns but dismissed to MEDIUM non-blockers because `player_name` is validated upstream at connect; multi-duplicate is a theoretical-invariant violation), deferred 1 (test AC-1 redundant return capture) |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 2 (lib.rs:2478 + connect.rs:2730 discard of Option<String>), dismissed 2 (connect.rs:2625 — barrier already reconciled via `old` captured before the call, safe today but fragile [note as MEDIUM]; lib.rs:2456 `unwrap_or_default` on resolve_region is pre-existing, out of scope) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 4 (AC-9 OTEL scan too loose; AC-2/AC-3 ignore return values; no runtime end-to-end wiring test per CLAUDE.md), dismissed 2 (AC-5 redundant assert is low-severity; AC-6 false-positive risk through aliased inserts is theoretical) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 (rustdoc promises roster sync at shared_session.rs:262 that callers don't deliver; stale comment at connect.rs:2619; overstated "outside this module" claim at shared_session.rs:270) |
| 6 | reviewer-type-design | Yes | findings | 2 | confirmed 2 (missing #[must_use] on Option<String> return; stringly-typed new_pid &str at trust boundary) |
| 7 | reviewer-security | No | skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.security=false`) |
| 8 | reviewer-simplifier | No | skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.simplifier=false`) |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 4 (rule #1 silent-discard at lib.rs:2478; rule #4 no tracing::warn! on phantom removal; rule #9 pub `players` field bypasses invariant; rule #6 uninterpolated `{raw_inserts}` in assert_eq! messages) |

**All received:** Yes (7 returned, 2 skipped by setting)
**Total findings:** 18 confirmed, 8 dismissed (with rationale), 2 deferred

## Rule Compliance

Mapping against `.pennyfarthing/gates/lang-review/rust.md` 15 checks and sidequest-api CLAUDE.md:

- **Rule #1 (silent error swallowing):** [RULE][SILENT] VIOLATION at `lib.rs:2478` — `ss_guard.insert_player_dedup_by_name(player_id, ps)` discards `Option<String>`. This is the **critical** finding. At `connect.rs:2625` the call is compliant because the caller captured `old` before the manual `players.remove(old)` above and reconciles the barrier directly; at `connect.rs:2730` the call is compliant because it is the fresh-player path where `is_reconnect == false` guarantees no phantom (benign today, fragile tomorrow).
- **Rule #2 (#[non_exhaustive]):** No new pub enums. VERIFIED clean.
- **Rule #3 (hardcoded placeholders):** No new magic literals. Event field values `"phantom_player_removed"` and `"multiplayer"` are semantic identifiers, not placeholders. VERIFIED.
- **Rule #4 (tracing coverage):** [RULE] VIOLATION at `shared_session.rs:364-373`. The phantom-removal branch emits a WatcherEvent (OTEL) but has no `tracing::warn!`. An anomalous reconnect event needs both channels — CLAUDE.md OTEL rule says the GM panel is the lie detector, but structured-log aggregators and human-readable server logs are blind to this.
- **Rule #5 (validated constructors at trust boundaries):** [TYPE] VIOLATION (MEDIUM) — `insert_player_dedup_by_name(new_pid: &str, ...)` is the single public chokepoint for player insertion and accepts any `&str` including empty. Type-design agent recommends a `PlayerId` newtype. Dismissed to MEDIUM (non-blocker) because `player_id` is validated upstream in the connect handshake; the boundary gap is a hardening item, not a bug.
- **Rule #6 (test quality):** [RULE][TEST] VIOLATION at `phantom_player_dedup_story_37_19_tests.rs:206-207, 226-228` — `assert_eq!(raw_inserts, 0, "... found {raw_inserts} raw call sites")` has uninterpolated `{raw_inserts}` because the message is a plain string literal, not a `format!`. Failure output will be misleading. Additional lower-severity: AC-2 / AC-3 discard the method's return; AC-9 OTEL scan accepts three alternative strings anywhere in the file, including comments.
- **Rule #7 (unsafe `as` casts):** None introduced. VERIFIED.
- **Rule #8 (Deserialize bypass):** No new Deserialize derives. VERIFIED.
- **Rule #9 (public fields on types with invariants):** [RULE] VIOLATION at `shared_session.rs:290` — `pub players: HashMap<String, PlayerState>`. The entire point of this story is to enforce a per-player-name uniqueness invariant on that field, but the field is pub, so the invariant is enforced only by convention and by the AC-8 source-grep test. This diff's fix *depends on* the field being inaccessible. It should be `pub(crate)` (preferable minimum) or private with a `players()` getter. PlayerState::role is correctly private with pub(crate) setter — VERIFIED.
- **Rule #10 (tenant context in traits):** No new trait methods. N/A.
- **Rule #11 (workspace deps):** No Cargo.toml changes. N/A.
- **Rule #12 (dev-only deps):** No Cargo.toml changes. N/A.
- **Rule #13 (constructor/Deserialize consistency):** No new types with both paths. N/A.
- **Rule #14 (fix-introduced regressions):** [RULE] VIOLATION — the fix introduces a NEW class of the same bug at one level up. Prior code had no dedup and no barrier mismatch; the fix creates the possibility of a phantom-removed-from-players-but-still-in-barrier state because lib.rs:2478 discards the old pid. The regression meta-check is the reason rule #14 exists, and this hits it.
- **Rule #15 (unbounded recursive input):** `insert_player_dedup_by_name` does an O(n) scan bounded by `players.len()`; not user-controlled recursion. VERIFIED.

Additional CLAUDE.md rules:
- **No silent fallbacks:** Violated by lib.rs:2478 return discard (see rule #1).
- **Every test suite needs a wiring test:** [TEST] VIOLATION — all 9 tests are either pure `SharedGameSession` unit tests or source-grep static checks. No runtime test spins up the connect-dispatch path to verify the chokepoint is reached with a real reconnect message. The source-grep assertions prove the *text* of production code; they don't prove the *runtime flow*.
- **OTEL observability:** Chokepoint emits `phantom_player_removed` as a WatcherEvent. GM panel will show dedup firings. VERIFIED — this part of the story is delivered correctly.
- **No half-wired features:** Violated — the downstream-roster reconciliation the story promises is half-wired. Chokepoint wire-up is complete; caller-side reconciliation is absent.

### Devil's Advocate

Let me argue this PR is broken even more than the specialists already flagged.

Scenario: Keith's playgroup opens a multiplayer session. Alice connects as `player_id="alice-tab1"` and joins a barrier for two players. Connection flaps. Her browser reopens the WebSocket with `player_id="alice-tab2"`. The dispatch enters the `session.is_playing()` branch at `lib.rs:2473`, which now calls `insert_player_dedup_by_name("alice-tab2", PlayerState::new("Alice"))`. The chokepoint finds `alice-tab1` (same name, different pid), removes it, emits the OTEL event, and returns `Some("alice-tab1")`. **The caller discards that.** `players` now has exactly one entry — `alice-tab2` — so `player_count() == 1`, and the RED test passes. But `turn_barrier` was built earlier with the `expected` set containing `alice-tab1`. When the barrier evaluates `all_submitted()`, it's still waiting on `alice-tab1`, which no longer exists in `players`. `alice-tab2` submits — barrier doesn't recognize her. Deadlock. Same class of bug, one subsystem over. The story's AC-5 test literally names this scenario ("structured-mode auto-promotion triggers when player_count >= 2; dedup must keep solo reconnects below this threshold") — but the test only checks `player_count()`. It doesn't construct a live TurnBarrier and re-evaluate it. A malicious user wouldn't need to do anything special; this is a normal reconnect flap.

Second scenario: Sebastien (the mechanics-first player) is watching the GM panel. The OTEL event fires. Good — he sees it. But there's no `tracing::warn!`, so when he checks the server log to correlate with the OTEL timestamp, there's silence. Observability is asymmetric — half-wired between GM panel and aggregator.

Third scenario: a future contributor adds a new method on `SharedGameSession` called, say, `restore_from_snapshot`, which loops over saved players and does `self.players.insert(pid, ps)`. That call is inside `shared_session.rs`, so the AC-8 source-grep (which only forbids `ss.` and `ss_guard.` prefixes *outside* `src/`) passes. A new phantom-source is born. The docstring at shared_session.rs:270 promises "outside this module" enforcement that the test doesn't actually provide — comment-analyzer flagged this, but in the devil's-advocate frame, it's a concrete loophole waiting to be stepped through.

Fourth: the `pub players` field means nothing in the *current* sidequest-server crate or any future consumer prevents `session.players.insert(fabricated_pid, rogue_state)`. Rule #9 exists to prevent exactly this — `tenant_id` equivalents that fields that encode security/invariant state must be private. `players` is now an invariant-carrying field.

## Reviewer Assessment

**Verdict:** REJECTED

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [CRITICAL] | [RULE][SILENT][EDGE] Return value of `insert_player_dedup_by_name` discarded on the returning-player reconnect path. When dedup fires, the old `player_id` persists in `turn_barrier`, `perception_filters`, and `pending_dice_requests` — reproducing the playtest-2026-04-12 deadlock one subsystem removed. This breaks the exact contract the method's own rustdoc documents. | `sidequest-api/crates/sidequest-server/src/lib.rs:2478` | Bind the return: `if let Some(old_pid) = ss_guard.insert_player_dedup_by_name(player_id, ps) { /* remove old_pid from turn_barrier, perception_filters, pending_dice_requests */ }`. Mirror the barrier-swap pattern already present at `connect.rs:~2628`. |
| [HIGH] | [RULE][SILENT][EDGE] Return value discarded on the fresh-connect (`!is_reconnect`) path. Benign today because `is_reconnect==false` implies no phantom exists, but the code relies on a semantic precondition rather than a type guarantee. If the invariant drifts (rapid reconnect, handshake race), the old_pid is silently dropped. | `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs:2730` | Capture the return; either `debug_assert!(result.is_none())` to pin the invariant, or reconcile downstream rosters defensively. |
| [HIGH] | [TYPE] No `#[must_use]` on `insert_player_dedup_by_name` and no newtype on the return, so the compiler issues no warning when callers discard the contract-bearing Option. This is the root cause of the CRITICAL and HIGH silent-discard findings. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:351` | Add `#[must_use = "caller must reconcile TurnBarrier and perception_filters when Some(old_pid) is returned"]` on the method. (Stronger option: return `Option<RemovedPlayerId>` with `#[must_use]` on the newtype.) |
| [HIGH] | [RULE] `pub players: HashMap<String, PlayerState>` — the field whose invariant this whole story enforces is publicly writable, so the chokepoint is bypassable from any future caller in the crate or (worse) outside it. Rule #9 requires invariant-carrying fields to be private with getters. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:290` | Change to `pub(crate)` at minimum; prefer private with a `players()` getter. Update tests that access `players.contains_key` through the getter. |
| [MEDIUM] | [RULE] No `tracing::warn!` on the phantom-removal branch — only OTEL. Structured-log aggregators and human server logs cannot see when dedup fires. CLAUDE.md OTEL rule is about GM-panel visibility; rule #4 requires the tracing channel as well. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:364-373` | Add `tracing::warn!(old_pid=%old, new_pid=%new_pid, player_name=%name, "phantom player removed on reconnect")` inside the `if let Some(ref old)` block. |
| [MEDIUM] | [TEST][RULE] No runtime end-to-end wiring test. All 9 tests are unit-level on `SharedGameSession` or source-grep static checks. CLAUDE.md explicitly requires at least one integration test that drives the component from production code paths. The source-grep tests prove *text*, not *runtime flow*. | `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs` | Add a runtime test that invokes `handle_ws_connection` (or the appropriate dispatch entry) with two sequential reconnect messages for the same player_name and asserts `player_count() == 1` AND `turn_barrier.expected_players()` reflects only the new pid. This test would catch the CRITICAL finding above. |
| [MEDIUM] | [TEST] `assert_eq!(raw_inserts, 0, "found {raw_inserts} raw call sites")` uses a plain string literal as the message — `{raw_inserts}` will appear literally in failure output, not the count. Makes debugging future regressions harder. | `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs:206, 226` | Change the message arg to `format!(...)`, or use `assert_eq!(raw_inserts, 0, "... found {} raw call sites", raw_inserts)`. |
| [MEDIUM] | [TEST] AC-9 OTEL presence test accepts any of three alternative event names anywhere in the file — including comments, dead strings, or unrelated identifiers. A future refactor that accidentally comments out the emit but leaves the string in a docstring passes. | `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs:287-293` | Pin to the canonical name (`phantom_player_removed`) and ideally assert it appears on a line that also contains `WatcherEventBuilder::new` or `.field("event"`. |
| [MEDIUM] | [DOC] Rustdoc at `shared_session.rs:337-350` promises that the returned pid lets the caller "keep external rosters (turn barrier, perception filters, dice requests) in sync" — a promise no caller currently keeps. Lying docstring. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:337` | After the CRITICAL/HIGH fixes wire up the reconciliation, this docstring will be accurate. If the PR is re-routed to Dev for fixes, verify the docstring remains true. |
| [LOW] | [DOC] Stale comment at connect.rs:~2619 ("Route through the dedup chokepoint even though we just removed the old entry — keeps all player insertions on one code path") implies the dedup logic actively fires at that site; it cannot, because the caller already removed the entry above. | `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs:~2619` | Reword to clarify this call is a no-op at runtime and exists for wire-invariant uniformity. |
| [LOW] | [DOC] Docstring at `shared_session.rs:270` claims "A source-level wiring test forbids raw `players.insert(...)` outside this module" — the AC-8 test actually forbids `ss.` and `ss_guard.` prefixes specifically, not "outside this module" in the general sense. A new method inside `shared_session.rs` could add a second raw insert and evade the test. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:270` | Tighten the wording to match what AC-8 actually enforces. |
| [LOW] | [TYPE] `new_pid: &str` at the chokepoint public API accepts empty strings and placeholder values. Non-blocking — upstream connect handshake validates — but a `PlayerId` newtype would make the boundary structural rather than conventional. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:351` | (Future hardening — not blocking.) |

**Data flow traced:** Player reconnect (WebSocket) → `session.is_playing()` branch in `lib.rs:~2441` → `ss_guard.insert_player_dedup_by_name(player_id, ps)` at line 2478 (return discarded) → `turn_barrier` still contains stale `old_pid` → barrier deadlock on `submit`. Unsafe because of the CRITICAL finding.

**Pattern observed:** Chokepoint pattern correctly designed at shared_session.rs:351–378 (single point of invariant enforcement, OTEL emission, informative return). Pattern implementation correctly matches the pattern intent. Pattern *usage* by callers is where the bug lives — the Option contract is advisory, not enforced. `#[must_use]` / newtype would close the gap.

**Error handling:** No new error paths introduced. OTEL emission does not propagate failure (acceptable — telemetry is best-effort). Silent-failure class is the discarded return, not thrown errors.

**Handoff:** Back to Dev (Major Winchester) for fixes. Findings are a mix of logic (lib.rs:2478 return handling, tracing::warn! addition, #[must_use]/visibility tightening) and test improvements. Route via `green` rework rather than `red` — the test contract is sound for what it covers; the CRITICAL finding is not coverable by the existing tests but needs a new runtime test that Dev/TEA can design together. Given the mix (primarily green-side fixes plus one new integration test), Dev can add the integration test as part of the green rework — no separate TEA round needed.

## Design Deviations

### Reviewer (audit)
- **TEA (test design): No deviations from spec.** → ✓ ACCEPTED by Reviewer: tests match the RED contract as stated; the undocumented-by-TEA item is the absence of a runtime wiring test, captured as a MEDIUM finding above rather than as a deviation since CLAUDE.md sets this as a global rule, not a story-specific spec line.
- **Dev (implementation): No deviations from spec.** → ✗ FLAGGED by Reviewer: the Dev Assessment claims "Wiring verified end-to-end" and that the chokepoint "has two non-test consumers" — true for insertion wiring, but the story's stated goal ("return the displaced pid so callers can reconcile downstream state") is undelivered. The call site in lib.rs:2478 takes the chokepoint's return and drops it. This is an undocumented deviation from the spec in the RED tests' contract language ("caller can sync the turn barrier, perception filters, and any other external rosters"). Severity: CRITICAL. Captured in the severity table above.

## Delivery Findings

### Reviewer (code review)
- **Gap** (blocking): The returning-player reconnect path in `lib.rs:2478` discards the chokepoint's `Option<String>` return, so `TurnBarrier`/`perception_filters`/`pending_dice_requests` keyed by the displaced pid are never reconciled. Affects `sidequest-api/crates/sidequest-server/src/lib.rs` (bind the return value and drive downstream roster cleanup). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The chokepoint would benefit from `#[must_use]` and/or a `RemovedPlayerId` newtype so the compiler enforces the caller contract. Affects `sidequest-api/crates/sidequest-server/src/shared_session.rs` (annotate the method or introduce a newtype). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `SharedGameSession::players` should be `pub(crate)` or private with a getter to structurally enforce the per-player-name invariant this story adds. Affects `sidequest-api/crates/sidequest-server/src/shared_session.rs` and any test call sites that read `.players.contains_key(...)` directly. *Found by Reviewer during code review.*
- **Gap** (non-blocking): No runtime wiring test exists for the reconnect flow. Affects `sidequest-api/crates/sidequest-server/tests/integration/` (add a test that drives `handle_ws_connection`/dispatch and verifies both `players` AND `turn_barrier.expected_players()` collapse to a single pid on reconnect). *Found by Reviewer during code review.*

### Dev (implementation, round 2)
- No upstream findings during rework.

## Dev Assessment (round 2 — rework)

**Implementation Complete:** Yes

**Review findings addressed (all confirmed items from Reviewer round 1):**

| Finding | Severity | Resolution |
|---------|----------|------------|
| [CRITICAL] lib.rs:2478 discarded `Option<String>` return — TurnBarrier/perception_filters/pending_dice_requests keyed by old pid never reconciled | Fixed | `if let Some(old_pid) = ss_guard.insert_player_dedup_by_name(...) { ss_guard.reconcile_removed_player(&old_pid); }` at lib.rs:2478 |
| [HIGH] connect.rs:2730 fresh-connect path discarded return | Fixed | Bind return, `tracing::warn!` + `reconcile_removed_player` if unexpectedly Some |
| [HIGH] No `#[must_use]` on chokepoint — compiler silent on discarded returns | Fixed | `#[must_use = "..."]` on `insert_player_dedup_by_name` with a message spelling out the reconcile contract. This caught four legitimate discards in the test setup — all fixed with explicit `None` assertions. |
| [HIGH] `pub players` field bypasses invariant | Fixed | Downgraded to `pub(crate)`; added `contains_player()` and `has_perception_filter()` read-only accessors for integration tests |
| [MEDIUM] No `tracing::warn!` on phantom-removal branch | Fixed | Added `tracing::warn!` alongside the OTEL emit in `insert_player_dedup_by_name` |
| [MEDIUM] No runtime end-to-end wiring test | Fixed | Added AC-11: installs TurnBarrier + PerceptionFilter keyed by old pid, reconnects under new pid, feeds returned pid through reconcile, asserts BOTH `players` AND downstream rosters collapse |
| [MEDIUM] `{raw_inserts}` uninterpolated in AC-6/7 assert_eq! messages | Fixed | Use format-arg tail so the count actually appears in failure output |
| [MEDIUM] AC-9 OTEL scan too loose (accepted three alternatives, matched comments) | Fixed | Pinned to canonical `phantom_player_removed`; requires adjacency to `WatcherEventBuilder::new(` AND `.field("event",` within 6 lines; rejects lines that start with `//` or `///` |
| [MEDIUM] Rustdoc promises roster sync that callers don't deliver | Fixed | Docstring now accurately describes the two-step contract (`insert_player_dedup_by_name` → `reconcile_removed_player`) |
| [LOW] Stale comment at connect.rs:~2619 reconnect-transfer site | Fixed | Rewrote to describe the runtime no-op and explicitly reference the wiring invariant (AC-7). Added `debug_assert!(result.is_none())` + release-build safety net. |
| [LOW] Docstring overstates "outside this module" claim at shared_session.rs | Fixed | Rewrote to describe what AC-8 actually enforces (`ss.players.insert(...)` / `ss_guard.players.insert(...)` patterns in `sidequest-server/src/`) |
| [LOW] `new_pid: &str` at trust boundary — deferred PlayerId newtype | Deferred (non-blocking per Reviewer) | Tracked as future hardening; `player_id` is validated upstream in the connect handshake, so this is a defence-in-depth improvement, not a bug |

**New public API surface:**
- `SharedGameSession::reconcile_removed_player(&mut self, old_pid: &str)` — evicts a just-removed pid from `turn_barrier`, `perception_filters`, and any `pending_dice_requests` with matching `rolling_player_id`. Emits `tracing::info!` + `WatcherEvent::phantom_player_reconciled` if anything was evicted.
- `SharedGameSession::contains_player(&self, player_id: &str) -> bool` — read-only membership check, replaces external `.players.contains_key(...)` access now that the field is `pub(crate)`.
- `SharedGameSession::has_perception_filter(&self, player_id: &str) -> bool` — read-only filter-presence check for AC-11.

**Files Changed (round 2):**
- `sidequest-api/crates/sidequest-server/src/shared_session.rs` — added `#[must_use]`, `tracing::warn!` on phantom removal, `reconcile_removed_player`, `contains_player`, `has_perception_filter`; downgraded `pub players` → `pub(crate)`; tightened rustdoc on the chokepoint and the module comment.
- `sidequest-api/crates/sidequest-server/src/lib.rs` — bind chokepoint return, call `reconcile_removed_player` on Some.
- `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` — both call sites handle the return defensively; reconnect-transfer has `debug_assert!(is_none())` + release-build reconcile; fresh-connect reconciles on unexpected Some with `tracing::warn!`.
- `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs` — added AC-10 (call-site / reconcile adjacency source-grep) and AC-11 (end-to-end runtime integration: full dedup+reconcile chain with TurnBarrier and PerceptionFilter), fixed `{raw_inserts}` interpolation, tightened AC-9 to adjacency check, converted AC-1/AC-2 to use `contains_player()` accessor, added explicit `None` assertions on all setup inserts that previously discarded the must-use return.

**Tests:** 11/11 passing (GREEN).

**Branch:** `feat/37-19-phantom-player-dedup` (pushed — commit `81e22a01`)

**Wiring verified end-to-end:**
- AC-10 (source-grep): every call to `insert_player_dedup_by_name` in production source has at least one `reconcile_removed_player` call in the same file — compile-time invariant that callers complete the two-step contract.
- AC-11 (runtime): exercises the full chain at the `SharedGameSession` API layer. Installing `TurnBarrier` + `PerceptionFilter` keyed by `old-pid`, reconnecting as `new-pid`, and reconciling — all three rosters collapse to the new pid. The test would fail loudly if a future refactor broke any link in the chain.
- OTEL: both `phantom_player_removed` (dedup fired) and `phantom_player_reconciled` (roster cleanup fired) surface on the GM panel.

**Handoff:** Back to Reviewer (Colonel Potter) for round-2 review.

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (fmt) | confirmed 1 (3 fmt diffs resolved by `cargo fmt --all` in the current working tree) |
| 2 | reviewer-edge-hunter | Yes | findings | 5 | confirmed 1 (AC-11 does not assert `pending_dice_requests`), dismissed 4 (lock-hierarchy MEDIUM doc improvement — outer Mutex and TurnBarrier inner std::Mutex are distinct; AC-10 count-parity semantic weakness noted as known limitation; connect.rs reconnect-transfer race window — dispelled because session Mutex is held continuously across remove+insert; silent no-op on empty reconcile — low-severity tracing omission) |
| 3 | reviewer-silent-failure-hunter | No | skipped | N/A | Not re-spawned on round 2 — round-1 findings in its domain (discarded return values) all confirmed resolved by rule-checker |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 1 (AC-11 `pending_dice_requests` gap — converges with edge-hunter), dismissed 3 (AC-5 tautological `< 2` assertion — LOW dismissible; AC-10 count-parity weakness — known limitation; AC-11 does not reach production `lib.rs` — AC-10 source-grep covers that invariant, together they form layered coverage) |
| 5 | reviewer-comment-analyzer | No | skipped | N/A | Not re-spawned on round 2 — all round-1 comment findings (lying docstring, stale transfer comment, "outside this module" overstatement) verified resolved by rule-checker |
| 6 | reviewer-type-design | No | skipped | N/A | Not re-spawned on round 2 — `#[must_use]` was the core type-design remediation; verified present by preflight compile |
| 7 | reviewer-security | No | skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.security=false`) |
| 8 | reviewer-simplifier | No | skipped | N/A | Disabled via settings (`workflow.reviewer_subagents.simplifier=false`) |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 2 at LOW severity (rule #1 silent Err swallow on `barrier.remove_player().is_ok()`; rule #6 AC-8 coverage-scope overpromise), verified all 5 round-1 findings RESOLVED |

**All received:** Yes (4 returned with findings, 2 skipped as duplicative of round-1 coverage, 2 skipped by setting)
**Total findings:** 4 confirmed (1 MEDIUM, 2 LOW, 1 FMT-mechanical), 12 dismissed (round-1 all resolved; round-2 nit-level items), 0 deferred

## Rule Compliance (round 2)

Rule-checker verified all 20 rules across 47 instances in the round-2 diff. Round-1 violations:

- **Rule #1 (silent error swallowing):** Round-1 violation at `lib.rs:2478` — **RESOLVED** at `lib.rs:2484-2485` with `if let Some(old_pid) = ... { reconcile_removed_player(&old_pid) }`. One NEW LOW-severity instance at `shared_session.rs:419` where `barrier.remove_player(old_pid).is_ok()` discards the `Err` variant. Practical impact negligible because `old_pid` is always a previously-inserted key — the only realistic Err is `PlayerNotFound` (benign, the expected case for barriers that haven't added the pid yet). Logged as delivery finding; not blocking.
- **Rule #4 (tracing coverage):** Round-1 violation — **RESOLVED** at `shared_session.rs:382` (`tracing::warn!` on phantom-removal branch), plus `tracing::info!` at line 435 on the reconcile success path, plus `tracing::warn!` at the two defensive connect.rs sites.
- **Rule #6 (test quality):** Round-1 format-arg violation in AC-6/AC-7 — **RESOLVED** (format-arg tail interpolates correctly now). AC-9 substring-match over-loose — **RESOLVED** via adjacency check to `WatcherEventBuilder::new(` + `.field("event",` with comment-line skipping. AC-2 return-discard — **RESOLVED** with explicit `None` asserts. One NEW LOW-severity item at AC-8: test title ("no other server src file inserts directly") overpromises — the two patterns only catch `.insert(`, not `.remove(` or `.get_mut(`. Since both of the `.remove`/`.get_mut` call sites in connect.rs are legitimate uses (reconnect-transfer path pre-removes the old entry correctly; post-insert read-back to populate character fields), this is a test-coverage scope note, not a production concern.
- **Rule #9 (public fields on types with invariants):** Round-1 violation on `pub players` — **RESOLVED** at `shared_session.rs:300` (`pub(crate)` with comment citing rule #9). Tests access membership through the new `contains_player()` / `has_perception_filter()` accessors.
- **Rule #14 (fix-introduced regressions):** Round-1 concern (the fix itself introduced the discarded-return class) — **RESOLVED**. The new `reconcile_removed_player` method does not recurse, does not call the chokepoint, and its call sites all bind the chokepoint's return. Defensive `debug_assert!` on the reconnect-transfer path plus release-build safety net eliminate the "benign today, fragile tomorrow" concern raised in round 1.
- **CLAUDE.md "Every test suite needs a wiring test":** Round-1 violation — **RESOLVED** via AC-11 (runtime integration, installs TurnBarrier + PerceptionFilter, drives the full dedup+reconcile chain). Remaining nit: AC-11 doesn't cover the third roster (`pending_dice_requests`) — logged as MEDIUM finding.
- **CLAUDE.md OTEL observability:** **VERIFIED** at both `phantom_player_removed` (insertion dedup) and `phantom_player_reconciled` (roster cleanup) emit sites. GM panel now sees both halves of the two-step contract.

No NEW CRITICAL or HIGH rule violations introduced by round-2 changes.

### Devil's Advocate (round 2)

If I'm trying to break this PR: where's the weak link?

Scenario 1 — the AC-11 gap. A future Dev, refactoring `reconcile_removed_player`, accidentally flips the `retain` predicate from `!= old_pid` to `== old_pid`. Every test passes. Every phantom reconnect now evicts the *active* player's in-flight dice rolls instead of the phantom's, breaking mid-roll reconnects. AC-11 would not catch it. AC-10 count-parity would not catch it. In production, Sebastien (our mechanics-first player) mid-roll would see his dice overlay vanish on a network hiccup. The retain() is in place and correct *today*, but the lack of test coverage makes a subtle bug invisible. This is a real risk worth logging.

Scenario 2 — the silent Err swallow at `barrier.remove_player().is_ok()`. If the TurnBarrier API grows a new error variant (e.g., `SessionClosed`), reconcile silently ignores it. In practice, `old_pid` is always a previously-inserted pid from the chokepoint, so the only realistic Err variant is `PlayerNotFound`, which is the expected case (the barrier may not have seen that pid yet). But the swallow is unconditional. If someone ever calls reconcile with a pid from a different source, an error would be eaten silently. Extremely unlikely given the function's API contract (only the chokepoint's return feeds it), but the pattern is a minor rule #1 deviation. LOW severity; not blocking.

Scenario 3 — the `pub(crate)` restriction on `players`. Can the invariant still be bypassed? Yes, within the crate, via direct mutation. The AC-8 source-grep catches `.insert(` across the whole `src/` tree, so a new raw `.insert()` from within `sidequest-server/src/` fails the test. But a future refactor could use `.remove() + .insert()` or `.values_mut()` + in-place mutation without triggering AC-8. The test's title overpromises relative to what it enforces. However, the `pub(crate)` visibility alone is enough to keep external consumers (including integration tests) honest, and AC-8 keeps the two most-common raw-insert patterns forbidden. Hardening beyond this is a future-phase concern.

Scenario 4 — a malicious user trying to force a phantom. Alice connects, then reconnects with a spoofed identical player_name. Dedup collapses them correctly. The WatcherEvent warns. The chokepoint's return is bound. The reconcile evicts from barrier/filters/dice. End-to-end safe at the layer we changed. An attacker can't force a phantom-induced deadlock anymore — the invariant is enforced structurally.

None of these scenarios reach CRITICAL or HIGH severity after the round-2 remediation. The AC-11 coverage gap is the strongest argument for another rework round, and it's a MEDIUM at worst.

## Reviewer Assessment (round 2)

**Verdict:** APPROVED (with MEDIUM/LOW findings logged for next-round hardening)

**Round-1 findings verified resolved:**
- CRITICAL `lib.rs:2478` return discarded → fixed with `if let Some(old_pid)` + `reconcile_removed_player`
- HIGH `connect.rs:2730` fresh-connect discard → fixed with bind + `tracing::warn!` + reconcile
- HIGH `#[must_use]` missing → added with the contract message
- HIGH `pub players` → downgraded to `pub(crate)` with rule-#9 citation
- MEDIUM no `tracing::warn!` on phantom removal → added
- MEDIUM no runtime wiring test → AC-11 added (TurnBarrier + PerceptionFilter exercised)
- MEDIUM AC-6/7 uninterpolated format → fixed with format-arg tail
- MEDIUM AC-9 too-loose scan → tightened to adjacency check with comment-line skipping
- MEDIUM lying docstring → rewritten to describe the two-step contract accurately
- LOW stale comments → rewritten
- LOW "outside this module" overstatement → corrected

**Round-2 findings (all non-blocking):**

| Severity | Issue | Location | Next-round action |
|----------|-------|----------|-------------------|
| [MEDIUM] [EDGE][TEST] AC-11 does not assert that `pending_dice_requests` entries keyed to `rolling_player_id == old_pid` are evicted after `reconcile_removed_player`. If a future refactor flips the `retain` predicate, every test still passes — the retain() is load-bearing but unasserted. Given that `pending_dice_requests` is the third roster the reconcile contract covers (after turn_barrier and perception_filters), this is a conspicuous coverage gap. | `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs:~1048` (AC-11) | Before calling `reconcile_removed_player` in AC-11, insert a `DiceRequestPayload` with `rolling_player_id = "old-pid"` into `ss.pending_dice_requests`. After reconcile, assert the map does not contain that entry. Mirrors the `perception_filter` assertion already present. |
| [LOW] [RULE] `reconcile_removed_player` calls `barrier.remove_player(old_pid).is_ok()` — the `Err` arm is consumed silently with no logging. Practically unreachable for anything other than the benign `PlayerNotFound` case, but a strict rule-#1 read. | `sidequest-api/crates/sidequest-server/src/shared_session.rs:~419` | Add `tracing::debug!` on the `Err` branch, or expand the match to log the variant. |
| [LOW] [RULE] AC-8's stated invariant ("every player insertion must go through `insert_player_dedup_by_name`") is not what the test actually enforces — it only catches `.insert(` prefixes of `ss.` and `ss_guard.`, not `.remove()` + `.insert()` patterns or `.get_mut()` mutations. Title overpromises. | `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs:~236` | Either rewrite AC-8's title to match scope (e.g., "forbids raw `ss.players.insert` / `ss_guard.players.insert` patterns") or broaden the test to catch `.remove()` + `.insert()` combos. |
| [FMT] cargo fmt --check found 3 diffs. | `sidequest-api/crates/sidequest-server/src/lib.rs`, `phantom_player_dedup_story_37_19_tests.rs` (two sites) | Already resolved — `cargo fmt --all` applied to the working tree. Commit the fmt changes as part of the approval merge. |

**Data flow traced (round 2):** Reconnect → `ss_guard.insert_player_dedup_by_name(player_id, ps)` → `Option<String>` bound via `if let Some(old_pid)` → `ss_guard.reconcile_removed_player(&old_pid)` → evicts from `turn_barrier` (via `barrier.remove_player`), `perception_filters` (via `HashMap::remove`), and `pending_dice_requests` (via `retain` on `rolling_player_id`). Two WatcherEvents emitted (one per step). All three rosters collapse to single pid at the session layer. End-to-end safe.

**Pattern observed:** Two-step chokepoint + reconcile pattern is clean, documented, and structurally enforced. `#[must_use]` on the chokepoint return with a message spelling out the contract is the type-system-as-lie-detector pattern I'd recommend for any future Rust API whose `Option` return encodes a mandatory caller action. The source-grep tests (AC-6/7/8/10) + runtime test (AC-11) form a defense-in-depth pair — the grep tests fail at compile-time on obvious regressions, the runtime test fails loudly on subtle ones.

**Error handling:** `reconcile_removed_player` has one LOW rule-#1 deviation on the `barrier.remove_player.is_ok()` swallow. `insert_player_dedup_by_name` has no error paths beyond the `Option` return. Defensive branches at the two connect.rs call sites catch invariant drift with `tracing::warn!` + reconcile.

**Handoff:** To SM (Hawkeye) for finish ceremony. The three round-2 findings are all non-blocking and can be addressed as a follow-up hardening story or bundled into an adjacent Epic 37 ticket — they do not block merging 37-19.

## Design Deviations

### Reviewer (audit, round 2)
- **Dev (implementation, round 2): No deviations from spec.** → ✓ ACCEPTED by Reviewer: every CRITICAL/HIGH/MEDIUM round-1 finding was addressed concretely in the diff; no new spec deviations introduced.

## Delivery Findings (round 2)

### Reviewer (code review, round 2)
- **Gap** (non-blocking): AC-11 runtime wiring test covers `turn_barrier` and `perception_filters` but does not assert `pending_dice_requests` eviction. Affects `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs` (add a `DiceRequestPayload` insert before reconcile; assert absence after). *Found by Reviewer during code review — round 2.*
- **Improvement** (non-blocking): `reconcile_removed_player` silently consumes `barrier.remove_player` `Err` via `.is_ok()`. Add a `tracing::debug!` on the `Err` arm so future error variants don't vanish. Affects `sidequest-api/crates/sidequest-server/src/shared_session.rs`. *Found by Reviewer during code review — round 2.*
- **Improvement** (non-blocking): AC-8 title overpromises vs. scope (only catches `.insert(` patterns, not `.remove() + .insert()` combos or `.get_mut()` mutations). Affects `sidequest-api/crates/sidequest-server/tests/integration/phantom_player_dedup_story_37_19_tests.rs` (retitle or broaden). *Found by Reviewer during code review — round 2.*
- **Improvement** (non-blocking): Uncommitted `cargo fmt` changes in the working tree from round-2 preflight. Should be bundled into the SM finish commit. Affects `sidequest-api/crates/sidequest-server/src/lib.rs` and the test file. *Found by Reviewer during code review — round 2.*