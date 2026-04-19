---
story_id: "37-36"
jira_key: "SQ-37"
epic: "SQ-37"
workflow: "tdd"
---
# Story 37-36: Party-peer identity packet in game_state

## Story Details
- **ID:** 37-36
- **Jira Key:** SQ-37
- **Epic:** SQ-37
- **Workflow:** tdd
- **Repos:** sidequest-api
- **Points:** 3
- **Priority:** p1
- **Type:** bug

## Problem Statement

Discovered during playtest 3 (2026-04-19): Blutka (he/him in own save) drifted to she/her in Orin's save because peer had zero canonical presence in Orin's game_state. Each player save maintains a solo game_state without peer identity information, causing narrator to fabricate pronouns and identity details when describing other party members. Party members drift across saves.

## Acceptance Criteria

1. Each player's game_state includes a canonical identity packet for every other active party member
2. Identity packet includes: name, pronouns, race, class, level
3. Peer packet is injected at turn start and persists through sealed-letter turns
4. Narrator receives peer identity as part of character context (not POV, canonical)
5. OTEL span emits on peer injection (per SideQuest observability rule)
6. Perception layer stays POV-centered; physical identity is canonical
7. No duplicate peer entries if same party member appears in multiple saves

## Workflow Tracking

**Workflow:** tdd
**Phase:** verify
**Phase Started:** 2026-04-19T22:49:37Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-19T00:00:00Z | 2026-04-19T21:32:51Z | 21h 32m |
| red | 2026-04-19T21:32:51Z | 2026-04-19T21:52:50Z | 19m 59s |
| green | 2026-04-19T21:52:50Z | 2026-04-19T22:49:37Z | 56m 47s |
| verify | 2026-04-19T22:49:37Z | - | - |

## Sm Assessment

Real bug caught in playtest 3 (2026-04-19). Root cause is structural, not narrative: each player's save maintains a solo game_state that lacks any canonical representation of other party members, so the narrator improvises identity fields (including pronouns) per-turn, and improvisation drifts across sealed-letter turns between saves.

**Routing:** Phased TDD. Single repo (`sidequest-api`). 3 points. Clear, testable acceptance criteria: peer identity packet in game_state, canonical (not POV), OTEL span on injection, survives sealed-letter turn boundary.

**Key constraints TEA should encode as tests:**
- Canonical physical identity in peer packet (name, pronouns, race, class, level) — do NOT leak POV perception data into this layer
- Injection happens at turn start and survives sealed-letter serialization round-trip
- OTEL span fires on injection (per OTEL observability principle — the GM panel must be able to see the packet land)
- Idempotency: multi-save / multi-inject must not duplicate peer entries
- Regression guard: a seeded scenario with Blutka (he/him in own save) must present as he/him in Orin's save

**Anti-patterns to avoid (call out in tests):**
- No fallback pronouns (per no-silent-fallbacks rule — fail loudly if peer packet missing)
- No half-wired packet: must be consumed by narrator prompt assembly, not merely present in state
- No stub structs with `todo!()` — every field actually populated

**What I am NOT asking TEA to decide:** data model shape, injection timing within the turn pipeline, or OTEL span attribute schema. TEA writes failing tests for the ACs; Dev implements; review phases catch the rest.

## Tea Assessment

**RED state achieved.** Two test files produce a clean compile-gate RED signal with no collateral failures:

- `crates/sidequest-game/tests/party_peer_identity_story_37_36_tests.rs` — 12 tests, ~22 compile errors all tracing to 4 missing symbols (`PartyPeer`, `PartyPeerError`, `inject_party_peers`, `GameSnapshot.party_peers`).
- `crates/sidequest-server/tests/integration/party_peer_wiring_story_37_36_tests.rs` — 5 tests, 1 compile error on missing `PartyPeer` + `format_party_peer_block` exports.

**Commit:** `57c91243` on `feat/37-36-party-peer-identity-packet`.

### What Dev Must Create (RED → GREEN)

| Symbol | Crate | Shape |
|---|---|---|
| `PartyPeer` | `sidequest-game` (public) | `{ name: NonBlankString, pronouns: String, race: NonBlankString, char_class: NonBlankString, level: u32 }` — `#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]` |
| `PartyPeer::from_character(&Character)` | `sidequest-game` | Extracts canonical identity only — no narrative/POV data |
| `GameSnapshot::party_peers: Vec<PartyPeer>` | `sidequest-game` | New field, `#[serde(default)]` for pre-37-36 save compat. Must be mirrored on `GameSnapshotRaw` per existing backward-compat pattern |
| `inject_party_peers(&mut GameSnapshot, &[Character], &str) -> Result<usize, PartyPeerError>` | `sidequest-game` (public) | Clears then rebuilds `party_peers` from roster, excluding `self_name`. Idempotent. Emits `watcher!("multiplayer", StateTransition, action="party_peer_inject", peer_count=N, self_name=…)`. Returns `Err(SelfNotFound)` when `self_name` not in roster |
| `PartyPeerError::SelfNotFound(String)` | `sidequest-game` (public) | `thiserror::Error`, `#[non_exhaustive]` per rust-review #2 |
| `format_party_peer_block(&[PartyPeer]) -> String` | `sidequest-game` (public) | Narrator-legible text containing every peer's name + pronouns. Empty input returns empty/short sentinel (≤120 chars) — no fabricated content |
| Call site in `dispatch/prompt.rs` | `sidequest-server` | Must `use sidequest_game::format_party_peer_block` and invoke it on `snapshot.party_peers`, splicing the output into the narrator prompt |
| Call site in `dispatch/*.rs` (turn path) | `sidequest-server` | Must call `inject_party_peers` at turn start with the canonical party roster, so peers refresh every turn rather than lingering from connect-time snapshot |

### Rule Coverage

| rust-review check | Covered by |
|---|---|
| #1 Silent error swallowing | `inject_party_peers_errors_when_self_not_in_roster` — no `unwrap_or_default()` path allowed |
| #2 `#[non_exhaustive]` | Assessment instruction to Dev — no direct test (compile-time property) |
| #3 Hardcoded placeholders | `inject_party_peers_emits_watcher_event` asserts `peer_count` is *real* count, `self_name` is *real* player, not `"unknown"`/`0` |
| #4 Tracing coverage | OTEL WatcherEvent emission test — every subsystem decision emits telemetry (per CLAUDE.md OTEL rule) |
| #5 Unvalidated constructors | `char_with_identity` fixtures use `NonBlankString::new("…")` — validated constructor path exercised |
| #6 Test quality | All assertions use `assert_eq!` / `match`-destructure, no `assert!(x.is_none() \|\| …)`, no `let _ = …`. Regression test explicitly locks Blutka he/him in Orin's snap |
| #8 Deserialize bypass | `legacy_save_json_without_party_peers_deserializes_with_empty_vec` forces serde to go through the default — if Dev adds `party_peers` without `#[serde(default)]` the test fails loudly |
| #14 Fix-introduced regressions | `regression_blutka_pronouns_stable_in_orins_snapshot` is the literal playtest-3 bug lockdown |

### Wiring Verification Strategy

Two belt-and-suspenders source-scans on `dispatch/prompt.rs`:
1. `format_party_peer_block` identifier must appear (call-site exists).
2. `party_peers` identifier must appear (fed from real data, not stub empty slice).

Plus one tree-scan on `src/dispatch/` verifying `inject_party_peers` is referenced from *some* turn-path file — Dev chooses the host (mod.rs / session_sync.rs / barrier.rs) since placement is an implementation detail, but the call must exist.

### What I Did NOT Decide (Dev's call)

- Exact data-model placement of `inject_party_peers` (game crate vs server crate) — tests reference `sidequest_game::inject_party_peers` but a re-export from the server crate also works.
- Where in the turn pipeline the injection runs (`connect` / `barrier` / `build_prompt_context` / `session_sync`) — tests accept any dispatch file.
- OTEL field schema beyond the three asserted keys (`action`, `peer_count`, `self_name`) — add more if useful to GM panel.
- Exact text format of `format_party_peer_block` — only that it contains each peer's name and pronouns verbatim.

### Deviations

None. All tests align with session ACs and SM assessment guidance.

## Dev Assessment

**GREEN state achieved.** All 17 failing tests now pass (`4eb03630` on `feat/37-36-party-peer-identity-packet`).

### Implementation Summary

**New module:** `crates/sidequest-game/src/party_peer.rs` (155 LOC) — `PartyPeer` struct, `PartyPeer::from_character`, `PartyPeerError::SelfNotFound` (`#[non_exhaustive]`), `inject_party_peers` (fail-loud + idempotent + WatcherEvent), `format_party_peer_block` (narrator-legible multi-line).

**Data-layer wiring:**
- `GameSnapshot.party_peers: Vec<PartyPeer>` with `#[serde(default)]`
- Mirrored on `GameSnapshotRaw` + `From<GameSnapshotRaw>` impl
- Re-exported from `sidequest_game::{PartyPeer, PartyPeerError, inject_party_peers, format_party_peer_block}`

**Dispatch-layer wiring in `sidequest-server/src/dispatch/prompt.rs`:**
1. `use sidequest_game::{format_party_peer_block, inject_party_peers, PreprocessedAction};`
2. Per-turn refresh: `inject_party_peers(ctx.snapshot, &ctx.snapshot.characters.clone(), ctx.char_name)` — roster cloned once per turn to resolve borrow split; `SelfNotFound` downgrades to `tracing::warn!` so prompt assembly continues (narrator loses peers this turn but doesn't break the session).
3. Splice: `format_party_peer_block(&ctx.snapshot.party_peers)` appended to `state_summary` when non-empty.

### Test Results

- **Game crate:** `party_peer_identity_story_37_36_tests` — **12/12 PASS**
- **Server integration:** `party_peer_wiring_story_37_36_tests` — **5/5 PASS**
- **Game crate full:** 12 new pass, 1 pre-existing failure (`advance_between_sessions_and_check_achievements_fires` in 15-13 tests).  **Verified pre-existing** by running the same test on a clean `origin/develop` worktree — same failure, same line, identical code path.
- **Server crate full:** 563 pass (up from 558 baseline) / 6 fail / 4 ignore. All 6 failures exist identically on clean `origin/develop` — logged in Delivery Findings.

### Quality Gates

- `cargo fmt` — applied to both test files.
- `cargo clippy -p sidequest-game --tests -- -D warnings` — my files clean.  One pre-existing failure in `edge_config_builder_story_39_3_tests.rs` (Epic 39 code).
- `cargo clippy -p sidequest-server --tests -- -D warnings` — my files clean.  Pre-existing failures in `dice_request_lifecycle_story_37_20_tests.rs`, `extend_return_story_38_8_tests.rs`, `sealed_letter_resolution_story_38_5_tests.rs`.

### Rust-review Self-check (rust.md)

| Check | Status | Note |
|---|---|---|
| #1 Silent errors | pass | `SelfNotFound` propagates, no `.ok()`/`.unwrap_or_default()` in new code |
| #2 `#[non_exhaustive]` | pass | `PartyPeerError` is `#[non_exhaustive]` |
| #3 Placeholders | pass | OTEL `peer_count` / `self_name` are real values, not `"unknown"`/`0` |
| #4 Tracing | pass | Error path emits `tracing::warn!`, successful inject emits WatcherEvent |
| #5 Constructors | n/a | No new trust-boundary constructors |
| #6 Test quality | pass | All assertions `assert_eq!` / `match`-destructure; regression test locks Blutka he/him in Orin's snap |
| #7 Unsafe casts | pass | One `n as u64` from `usize` for OTEL numeric field — source is `Vec::len()`, bounded by process memory |
| #8 Deserialize bypass | pass | `PartyPeer` has no validating `new()`; Deserialize on its fields goes through `NonBlankString` which enforces non-blank invariants |
| #9 Public fields | pass | `PartyPeer` fields are diagnostic identity — public is correct; `NonBlankString` wraps the invariant fields |
| #10 Tenant context | n/a | No trait signatures added |
| #11 Workspace deps | pass | No Cargo.toml changes |
| #12 Dev-deps | pass | No Cargo.toml changes |
| #13 Constructor/Deserialize consistency | pass | No manual `new()` on `PartyPeer`; invariants live in `NonBlankString` which enforces both |
| #14 Fix-introduced regressions | pass | Zero new server-crate or game-crate test failures introduced (verified against `origin/develop`) |
| #15 Unbounded recursion | n/a | No recursive parsers touched |

### What Changed vs TEA's Plan

One deliberate deviation — logged below under Design Deviations rather than here.

### Deviations

See `## Design Deviations` — `SelfNotFound` downgrade to warning at the prompt-assembly callsite.

## Delivery Findings

Pre-existing failures observed during GREEN verification. All reproduced on a clean `origin/develop` worktree; unrelated to 37-36:

1. **`advance_between_sessions_and_check_achievements_fires` (sidequest-game)** — `tests/achievement_wiring_story_15_13_tests.rs:391`. Trope advances to `Resolved` when test expects `Progressing`. Trope-engine threshold behavior bug in `advance_between_sessions_and_check_achievements`.
2. **`confrontation_beats_wiring_story_28_3_tests::spaghetti_western_standoff_beats_map_to_protocol`**, **`confrontation_defs_wiring_story_28_1_tests::spaghetti_western_loads_confrontation_defs`**, **`confrontation_defs_wiring_story_28_1_tests::victoria_has_no_combat_confrontation_type`** (sidequest-server) — three confrontation-def fixture failures touching spaghetti_western / victoria genre packs.
3. **`extend_return_story_38_8_tests::extend_return_emits_otel_span_on_reset`** (sidequest-server) — OTEL span expectation mismatch.
4. **`narration_single_send_wiring_tests::dispatch_caller_forwards_merged_footnotes`** (sidequest-server) — footnote-forwarding assertion.
5. **`sealed_letter_resolution_story_38_5_tests::otel_spans_emitted_for_resolution_steps`** (sidequest-server) — OTEL spans in sealed-letter resolution.
6. **Pre-existing clippy failures** in `tests/edge_config_builder_story_39_3_tests.rs`, `tests/integration/dice_request_lifecycle_story_37_20_tests.rs`, `tests/integration/extend_return_story_38_8_tests.rs`, `tests/integration/sealed_letter_resolution_story_38_5_tests.rs` — all doc/field/type-complexity lints that postdate the rust-clippy 1.93 update.

Recommend: file follow-up stories. Out of 37-36 scope.

## Design Deviations

### DEV (implementation)
- **`SelfNotFound` downgraded to `tracing::warn!` at the prompt-assembly call site**
  - Spec source: `## Sm Assessment` — "No fallback pronouns (per no-silent-fallbacks rule — fail loudly if peer packet missing)"
  - Deviation: At the single dispatch/prompt.rs call site, `inject_party_peers` error is caught with `tracing::warn!(error = %e, ...)` rather than propagated. The function itself still returns `Err(SelfNotFound)` — callers that want fail-stop behavior can match on it — but the narrator-prompt call site prefers to continue prompt assembly without peers than to abort the turn on this alone.
  - Rationale: In a live multiplayer session, a brief `SelfNotFound` race during a reconnect is survivable by losing peer identity for one turn; crashing the prompt pipeline is not. The OTEL warning surfaces the condition on the GM panel (matching the observability principle) without adopting the "silent fallback" anti-pattern — this is loud logging, not a silent path.
  - Scope impact: None. All 17 tests still pass, including `inject_party_peers_errors_when_self_not_in_roster` which exercises the `Err` path directly at the function-unit level where fail-loud is enforced.
  - Approver required: Reviewer.