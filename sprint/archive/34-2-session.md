---
story_id: "34-2"
jira_key: null
epic: "34"
workflow: "tdd"
---

# Story 34-2: DiceRequest/DiceThrow/DiceResult protocol types + serde

## Story Details

- **ID:** 34-2
- **Jira Key:** null (OQ-2 personal project — no Jira)
- **Epic:** 34 — 3D Dice Rolling System MVP
- **Workflow:** tdd
- **Repos:** api (sidequest-protocol crate)
- **Branch:** feat/34-2-dice-protocol-types
- **Points:** 3
- **Priority:** p0

## Story Overview

This story establishes the protocol layer for the dice rolling system. Three new `GameMessage` variants and supporting types must be added to `sidequest-protocol` crate so the server and clients can communicate about dice rolls.

The types are the foundation for all dependent stories (34-3 through 34-8). Until these types compile and serialize correctly, downstream stories cannot proceed.

## Scope

**In scope:**
- Define `DiceRequest` struct (server → client)
- Define `DiceThrow` struct with `ThrowParams` (client → server)
- Define `DiceResult` struct (server → broadcast)
- Define `RollOutcome` enum (CritSuccess, Success, Fail, CritFail)
- Define `DieSpec` struct (dice pool specification)
- Add three new `GameMessage` variants
- Implement serde serialization/deserialization for all types
- Proptest roundtrip tests for all types
- Verify types compile and integrate with existing message enum

**Out of scope:**
- Dice resolution logic
- Dispatch integration (wiring into beat selection flow)
- UI rendering or interaction
- OTEL spans
- Narrator integration

## Technical Approach

### Type Layout (per ADR-074)

The protocol defines these message flows:

```
Server → Client: DiceRequest {
    request_id: String,
    player_id: String,
    character_name: String,
    dice: Vec<DieSpec>,
    modifier: i32,
    stat: String,
    difficulty: u32,
    context: String,
}

DieSpec {
    sides: u32,
    count: u32,
}

Client → Server: DiceThrow {
    request_id: String,
    throw_params: ThrowParams,
}

ThrowParams {
    velocity: [f32; 3],
    angular: [f32; 3],
    position: [f32; 2],
}

Server → Broadcast: DiceResult {
    request_id: String,
    player_id: String,
    character_name: String,
    rolls: Vec<u32>,
    modifier: i32,
    total: u32,
    difficulty: u32,
    outcome: RollOutcome,
    seed: u64,
    throw_params: ThrowParams,
}

enum RollOutcome {
    CritSuccess,
    Success,
    Fail,
    CritFail,
}
```

### Serde Tagging Strategy

- `DiceRequest`, `DiceThrow`, `DiceResult` are new variants on the existing `GameMessage` enum
- Use `#[serde(rename = "DICE_REQUEST")]` pattern to match existing SCREAMING_CASE convention
- Add `#[serde(deny_unknown_fields)]` to payload structs to match existing safety
- Use standard derives: `Debug, Clone, PartialEq, Serialize, Deserialize`
- No custom serialization — all types are simple POD (except the enum)

### Crate Organization

All new types live in `sidequest-protocol`:
- `message.rs` — new `GameMessage` variants and payload structs
- `types.rs` — optional if newtypes are needed for validation (e.g., request_id as newtype, but likely not needed for MVP)

No changes to other crates in this story.

## Acceptance Criteria

- [ ] **Compilation:** All types compile without warnings in `sidequest-protocol` crate
- [ ] **Variants added:** `DiceRequest`, `DiceThrow`, `DiceResult` appear as GameMessage variants
- [ ] **Serde round-trip:** Types serialize to JSON and deserialize back identically
- [ ] **Proptest coverage:** At least one roundtrip test using proptest or serde_test
- [ ] **RollOutcome completeness:** All four variants (CritSuccess, Success, Fail, CritFail) defined and tested
- [ ] **Protocol integration:** New variants integrate cleanly with existing GameMessage matching
- [ ] **No wiring required:** This story adds types only — no dispatch, no rendering, no OTEL
- [ ] **Wiring test:** Test file verifies types can be deserialized from JSON that matches the ADR schema
- [ ] **No deprecations:** Existing message types unchanged

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-11T18:29:55Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-11 | 2026-04-11T15:15:03Z | 15h 15m |
| red | 2026-04-11T15:15:03Z | 2026-04-11T15:23:28Z | 8m 25s |
| green | 2026-04-11T15:23:28Z | 2026-04-11T15:52:14Z | 28m 46s |
| verify | 2026-04-11T15:52:14Z | 2026-04-11T17:31:38Z | 1h 39m |
| review | 2026-04-11T17:31:38Z | 2026-04-11T17:50:30Z | 18m 52s |
| green | 2026-04-11T17:50:30Z | 2026-04-11T18:12:21Z | 21m 51s |
| review | 2026-04-11T18:12:21Z | 2026-04-11T18:18:15Z | 5m 54s |
| green | 2026-04-11T18:18:15Z | 2026-04-11T18:26:09Z | 7m 54s |
| review | 2026-04-11T18:26:09Z | 2026-04-11T18:29:55Z | 3m 46s |
| finish | 2026-04-11T18:29:55Z | - | - |

## Sm Assessment

**Story readiness:** GREEN. Setup is clean. Story 34-2 is a well-scoped protocol-types-only story with no cross-repo concerns and no external dependencies beyond `sidequest-protocol` crate internals.

**Dependency state:** 34-1 (spike) is done. 34-2 unblocks 34-3 through 34-8. No blockers.

**Workflow choice:** TDD is correct. This is a pure types-plus-serde story — the ideal TDD shape is "write a serde round-trip test that fails because the type doesn't exist yet, then add the type." RED phase will be small but meaningful.

**Risk call:** LOW. Types are additive to `GameMessage` enum; no existing variant changes. Main risks are (a) drifting from ADR-074 schema, and (b) forgetting to wire new variants into any exhaustive match statements elsewhere in the crate — TEA should scan for `match msg {` sites and include a test that exercises the new arms.

**Scope discipline:** Out-of-scope list is explicit and enforceable. No dispatch, no rendering, no OTEL, no narrator. If TEA or Dev is tempted to "also do resolution logic," that belongs in 34-3.

**Next owner:** TEA (Mr. Praline) for RED phase. TEA should:
1. Read ADR-074 (`docs/adr/074-*.md`) and `sprint/planning/prd-dice-rolling.md` for authoritative schema
2. Write failing proptest/serde_test roundtrips for each new type
3. Write a "new variant appears in GameMessage" compile-time test (e.g., exhaustive match on a fixture)
4. Verify no wiring is required outside the protocol crate

**Handoff:** Clean to TEA. No open questions.

## TEA Assessment

**Phase:** finish
**Tests Required:** Yes
**Reason:** Pure types-plus-serde story — ideal TDD target. Failing tests enforce the ADR-074 wire schema at compile time AND at runtime.

**Test Files:**
- `sidequest-api/crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` — 33 tests covering every ADR-074 field, serde round-trip, SCREAMING_CASE tags, `deny_unknown_fields`, and RollOutcome completeness
- `sidequest-api/crates/sidequest-protocol/src/lib.rs` — module registration (one 4-line stanza following the existing `#[cfg(test)] #[path = ...]` pattern)

**Tests Written:** 33 tests covering 8 ACs
**Status:** RED (fails to compile — 86 errors, all for missing dice types)

### Rule Coverage (rust-review-checklist)

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 `#[non_exhaustive]` on public enums | N/A — RollOutcome is protocol-fixed, matches `FactCategory` precedent. Reviewer-enforced per existing convention. | noted |
| #3 No hardcoded placeholders | Fixtures use realistic values (Kira, req-abc, seeds) not "none"/"unknown" | pass |
| #5 Validated constructors | N/A — no `::new()` constructors in this story; fields are plain POD | n/a |
| #6 Test quality (no vacuous asserts) | Every test has concrete `assert_eq!` or `matches!` on actual values; `std::mem::discriminant` used for enum variant equality in the round-trip loop | pass |
| #8 `#[derive(Deserialize)]` bypass | N/A — no validated constructors exist on these types | n/a |
| #9 Public fields on security-critical types | None — dice fields are game-mechanical, not security policy. `seed: u64` is broadcast anyway (ADR-074: "All clients run identical physics from the same seed") | n/a |
| #11 Workspace deps | No new deps added — proptest intentionally skipped (see deviation) | pass |
| #12 Dev-only deps in `[dependencies]` | N/A — no new deps | n/a |
| **deny_unknown_fields enforcement** | 5 tests: `dice_request_payload_rejects_unknown_fields`, `dice_throw_payload_rejects_unknown_fields`, `dice_result_payload_rejects_unknown_fields`, `die_spec_rejects_unknown_fields`, `throw_params_rejects_unknown_fields` | failing (RED) |
| **ADR-074 schema fidelity** | 3 fixture tests deserialize exact ADR-074 JSON and assert every field | failing (RED) |
| **Wiring test (crate re-export)** | `dice_types_reachable_via_crate_root` — compile-time check that new types reach `use super::*;` via `lib.rs pub use message::*` | failing (RED) |

**Rules checked:** 9 of 15 lang-review rules applicable; 6 enforced by tests, 3 reviewer-noted
**Self-check:** 0 vacuous tests — every assertion validates a specific ADR-074 invariant. No `let _ =`, no `assert!(true)`, no `assert!(x.is_some())` as a cheap stand-in.

### RED Verification

Verified via `cargo build -p sidequest-protocol --tests`:
- Build FAILS with 86 compile errors
- Error codes: E0422 (57), E0433 (20), E0599 (6), E0425 (1)
- All errors target missing types: `DiceRequest`/`DiceThrow`/`DiceResult` variants, `DiceRequestPayload`/`DiceThrowPayload`/`DiceResultPayload` structs, `DieSpec`, `ThrowParams`, `RollOutcome`
- Zero unrelated errors — no test pollution into other modules

**Handoff:** To Dev (Bicycle Repair Man) for GREEN phase implementation.

### Dev Guidance

Dev should add to `sidequest-api/crates/sidequest-protocol/src/message.rs`:

1. Three new `GameMessage` variants at the end of the enum (before the closing `}` on line 352):
   - `#[serde(rename = "DICE_REQUEST")] DiceRequest { payload: DiceRequestPayload, player_id: String }`
   - `#[serde(rename = "DICE_THROW")] DiceThrow { payload: DiceThrowPayload, player_id: String }`
   - `#[serde(rename = "DICE_RESULT")] DiceResult { payload: DiceResultPayload, player_id: String }`

2. Six new types, each deriving `Debug, Clone, PartialEq, Serialize, Deserialize` and using `#[serde(deny_unknown_fields)]` where applicable:
   - `DiceRequestPayload` — 8 fields from ADR-074
   - `DiceThrowPayload` — `request_id`, `throw_params`
   - `DiceResultPayload` — 10 fields (`rolls` is `Vec<u32>`, `seed` is `u64`, `outcome` is `RollOutcome`)
   - `DieSpec` — `sides: u32, count: u32`
   - `ThrowParams` — `velocity: [f32;3], angular: [f32;3], position: [f32;2]`
   - `RollOutcome` — enum with 4 variants: `CritSuccess`, `Success`, `Fail`, `CritFail`. Use the `FactCategory` pattern (derives `Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize` and likely `#[non_exhaustive]` per crate precedent)

3. **DO NOT** change anything else. This is a types-only story. No dispatch wiring, no dice resolution logic, no OTEL spans, no UI work.

4. Run `cargo build -p sidequest-protocol --tests` to confirm compilation; then `cargo test -p sidequest-protocol dice_protocol_story_34_2` to verify all 33 tests pass.

## Dev Assessment

**Implementation Complete:** Yes (review-fix pass — all 17 items addressed)
**Phase:** finish (rework after REJECT)
**Branch:** `feat/34-2-dice-protocol-types` (pushed to origin — commit `30646e3`)
**Worktree:** `/Users/keithavery/Projects/oq-2/.worktrees/api-34-2` (main worktree kept on `chore/clippy-workspace-cleanup` with Keith's WIP untouched — used `git worktree add` per the Reviewer's handoff guidance, no stash)

**Files Changed:**
- `sidequest-api/crates/sidequest-protocol/src/message.rs` — wholesale type revision to address review findings #1–#7 and #13–#17
- `sidequest-api/crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` — full rewrite to address test findings #8–#12 and to exercise the new invariants
- `sidequest-api/crates/sidequest-game/src/journal.rs` — wildcard arm on `JournalSortOrder` match (cascade from adding `#[non_exhaustive]` to the enum)
- `sidequest-api/crates/sidequest-agents/src/orchestrator.rs` — two wildcard arms (one each on `NarratorVerbosity` and `NarratorVocabulary` matches)
- `sidequest-api/crates/sidequest-agents/src/prompt_framework/mod.rs` — two wildcard arms (same enums)

**Review fix list — all 17 items:**

Type correctness (fixes 1–7, 17):
1. ✅ `DiceResultPayload.total: u32 → i32`. Signed total is the natural companion to signed modifier.
2. ✅ `DieSpec.sides: u32 → DieSides` bounded enum with the seven ADR-074 values (D4/D6/D8/D10/D12/D20/D100) plus `#[serde(other)] Unknown` catch-all. `DieSpec.count: u32 → NonZeroU8` caps allocation at 255 and rejects zero.
3. ✅ `GameMessage` + 4 (fix #17): `GameMessage`, `NarratorVerbosity`, `NarratorVocabulary`, and `JournalSortOrder` all now carry `#[non_exhaustive]`. Cascaded to 5 downstream match sites (4 match arms added across `sidequest-game` and `sidequest-agents`).
4. ✅ `RollOutcome` now has a `#[serde(other)] Unknown` catch-all variant. Doc comment fully rewritten to explain that `#[non_exhaustive]` (compile-time) and `#[serde(other)]` (wire-level) solve two orthogonal problems and both are needed. The prior doc incorrectly claimed `#[non_exhaustive]` alone provided wire forward-compat — corrected.
5. ✅ `DiceRequestPayload.stat` is now validated at deserialization (whitespace/blank stat rejected via `DiceRequestPayloadError::BlankStat`). A full `StatName` enum would require genre-pack knowledge not available at the protocol layer; the validated deserialization is the right hook for wire-boundary checks, and bounded-enum validation can layer on at dispatch in 34-3.
6. ✅ `DiceResultPayload.rolls: Vec<u32> → Vec<DieGroupResult>`. New `DieGroupResult { spec: DieSpec, faces: Vec<u32> }` struct preserves per-group attribution so `RollOutcome::CritSuccess` ("natural max on the primary die") is formally resolvable for mixed pools. Full serde round-trip coverage.
7. ✅ `player_id → rolling_player_id` rename on both `DiceRequestPayload` and `DiceResultPayload`. Envelope vs payload collision resolved at the type level. Doc on `GameMessage::DiceResult` variant now mirrors `DiceRequest`'s warning (previously asymmetric).
15. ✅ `DiceRequestPayload.difficulty: u32 → NonZeroU32`. Serde enforces non-zero at the wire boundary, preventing `difficulty=0` (guaranteed Success on any roll).
16. ✅ Empty dice pool rejected at deserialization via `DiceRequestPayloadError::EmptyDicePool`. Uses the standard `#[serde(try_from)]` / `#[serde(into)]` pattern — `DiceRequestPayloadRaw` is the deserialization intermediary with `deny_unknown_fields`, and `TryFrom` enforces the non-empty invariant before constructing the real payload.

Test correctness (fixes 8–12):
8. ✅ `dice_throw_payload_carries_request_id_and_params` — now asserts all three ThrowParams fields (velocity, angular, position). Previously ignored 2/3 despite constructing with specific values.
9. ✅ `roll_outcome_all_four_variants_round_trip` renamed to `roll_outcome_named_variants_round_trip_with_exact_wire_strings`. Now pins each variant's exact ADR-074 wire string (`"\"CritSuccess\""`, etc.) instead of using `mem::discriminant` comparison. Would now catch a hypothetical serde misconfig that encoded variants as integers.
10. ✅ `dice_result_round_trip_with_pool_rolls` renamed to `dice_result_round_trip_with_mixed_pool_preserves_group_attribution`. Replaced `if let` with `match { _ => panic!("expected DiceResult") }` to match sibling round-trip test pattern. Also exercises the new per-group `Vec<DieGroupResult>` structure.
11. ✅ Deleted the three tautological `*_variant_exists` tests. `assert!(matches!(...))` on a value just constructed as that variant cannot fail by Rust's type system — the round-trip tests cover the real behavior.
12. ✅ Expanded `dice_types_reachable_via_crate_root` (renamed `all_new_dice_public_types_reachable_via_crate_root`) to construct and assert on all seven new public types: `DieSides`, `DieSpec`, `DieGroupResult`, `ThrowParams`, `RollOutcome`, `DiceRequestPayload`, `DiceThrowPayload`, `DiceResultPayload`.

Doc correctness (fixes 13–14):
13. ✅ Moved "cryptographically generated" qualifier from `ThrowParams` struct doc to `DiceResultPayload.seed` field doc where the cheat-resistance rationale actually lives. `ThrowParams` doc now cross-references.
14. ✅ Rewrote `DiceRequestPayload.stat` doc to drop the cross-crate `BeatDef.stat_check` reference. Plain-language description used instead.

New tests added for the new invariants (not in the original 17):
- `dice_result_negative_total_round_trip` — locks in the signed-total contract (rolls=[1], modifier=-5, total=-4)
- `dice_request_payload_rejects_empty_dice_pool` — cites `dice pool is empty` in the error
- `dice_request_payload_rejects_blank_stat` — cites `stat field is blank` in the error
- `dice_request_payload_rejects_zero_difficulty` — NonZeroU32 rejection
- `die_spec_rejects_zero_count` — NonZeroU8 rejection
- `die_sides_rejects_invalid_sides_with_unknown_fallback` — sides=0/3/u32::MAX all fall to `Unknown`
- `die_group_result_rejects_unknown_fields` — deny_unknown_fields for the new type
- `roll_outcome_unknown_variant_absorbs_future_wire_strings` — `"NearMiss"` deserializes to `Unknown`
- `die_sides_covers_all_adr_074_tabletop_values` — wire-string pin for all seven variants + `faces()` return

**Tests:** 32/32 dice protocol tests passing. Full `sidequest-protocol` crate: 180 tests passing (baseline 179 +1 from DieGroupResult). `cargo build --workspace`: clean build. `cargo clippy -p sidequest-protocol --tests -- -D warnings`: clean. `cargo clippy -p sidequest-agents -- -D warnings`: clean (sidequest-agents lib only; a pre-existing sidequest-game clippy failure blocks full transitive clippy, see below).

**Test-count bookkeeping:** Dev's original assessment said 31; simplify commit `906e414` removed 4 redundant tests bringing it to 27; this commit adds 3 new explicit-variant tests, deletes 3 tautologies, adds 8 new invariant tests, and adds 2 consolidated pool-grouping tests → net **32 tests** in the final file. Every test has at least one non-vacuous `assert!`/`assert_eq!`/`matches!` against a real runtime value.

**Workspace cascade from `#[non_exhaustive]`:** Adding `#[non_exhaustive]` to `GameMessage`, `NarratorVerbosity`, `NarratorVocabulary`, and `JournalSortOrder` broke 5 exhaustive-match sites at compile time. Each fixed with a documented wildcard arm that falls through to the "default" variant for unknown values from newer wire versions:
- `sidequest-game/src/journal.rs:50` (`JournalSortOrder` → Time default)
- `sidequest-agents/src/orchestrator.rs:724` (`NarratorVerbosity` → Standard default)
- `sidequest-agents/src/orchestrator.rs:785` (`NarratorVocabulary` → Literary default)
- `sidequest-agents/src/prompt_framework/mod.rs:124` (same, Standard)
- `sidequest-agents/src/prompt_framework/mod.rs:178` (same, Literary)

This is exactly the "reactive vs preventative" distinction Reviewer flagged in fix #3: before this commit the breakage would have been discovered at compile time by downstream code. With `#[non_exhaustive]` in place, downstream code is now forced to handle unknown variants gracefully.

**Self-Review:**
- [x] Tests green (32/32 dice, 180/180 sidequest-protocol full)
- [x] Working tree clean (5 files staged, all committed)
- [x] No debug code / no `println!` / no `dbg!`
- [x] Correct branch (`feat/34-2-dice-protocol-types`, base `develop`, pushed)
- [x] Code follows existing `message.rs` patterns (deny_unknown_fields, SCREAMING_CASE rename, doc comments on every field). New pattern: `#[serde(try_from)]` / `#[serde(into)]` for validated payloads.
- [x] All 17 Reviewer fix items addressed. Plus 9 new tests for the new invariants.
- [x] Error handling: `DiceRequestPayloadError` enum with `EmptyDicePool` and `BlankStat` variants, `#[non_exhaustive]`, implements `Display` and `Error`. Wired into the `TryFrom` serde bridge.
- [x] Wiring verified: workspace cargo build passes end-to-end. All 5 downstream matches on now-`#[non_exhaustive]` enums have wildcard arms.
- [x] Scope discipline: every change serves a Reviewer fix item. No freelanced refactoring.

**Handoff:** Back to Reviewer (The Argument Professional) for the second review pass.

## Dev Assessment (Cycle 3 — rework after cycle-2 reject)

**Implementation Complete:** Yes (all 3 cycle-2 findings addressed — 2 blockers resolved, 1 non-blocking done anyway because the Raw-module refactor made it free)
**Branch:** `feat/34-2-dice-protocol-types` @ `004cf94` (pushed to origin)
**Files Changed:** `crates/sidequest-protocol/src/message.rs` and `crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` only.

### Cycle-2 finding resolution

**Finding 1 — `DieSides` doc/wire mismatch** → FIXED via option (a): made the wire format match the doc.
- Replaced `#[serde(rename = "N")]` variants + `#[serde(other)] Unknown` (which produced quoted strings) with `#[serde(from = "u32", into = "u32")]` on the enum plus explicit `From<u32>` and `From<DieSides> for u32` impls.
- `From<u32>` maps `{4,6,8,10,12,20,100}` → their variants; all other integers (including 0, 1, 3, 7, u32::MAX) fall through to `Unknown`. Forward-compat preserved via the infallible bridge.
- `From<DieSides> for u32` maps `Unknown` → `0` as a deliberate sentinel. Round-trip `Unknown → 0 → Unknown` is stable because 0 is not in the accepted set.
- Doc rewritten to accurately describe the integer wire format and note why the old serde-rename approach was wrong.
- Every ADR-074 fixture in the test file updated from `"sides": "20"` → `"sides": 20`. `die_spec_serde_round_trip` and `die_sides_covers_all_adr_074_tabletop_values` now pin the exact JSON shape (bare integer) so a regression would fail loudly.
- Added `die_sides_unknown_round_trips_via_zero_sentinel` to pin the sentinel behavior.

**Finding 2 — `DieGroupResult` invariant was documentary only** → FIXED via option (a): added the enforcement mechanism.
- Created `DiceResultPayloadRaw` mirroring `DiceRequestPayloadRaw`, both living in a new private `mod dice_payload_raw` submodule.
- `TryFrom<DiceResultPayloadRaw> for DiceResultPayload` walks `raw.rolls` and rejects any group where `faces.len() != spec.count.get() as usize`, returning `DiceResultPayloadError::FaceCountMismatch { group_index, declared, actual }`.
- `DiceResultPayloadError` is a new public `#[non_exhaustive]` error enum with `impl Display` and `impl Error`. Currently one variant — can grow to include additional consistency checks (e.g., total-lies-about-sum) without breaking the API.
- `DiceResultPayload` switched from `derive(Deserialize) + deny_unknown_fields` to manual `Deserialize` impl that routes through Raw + TryFrom, and `#[serde(into = "dice_payload_raw::DiceResultPayloadRaw")]` on the serialize side.
- `DieGroupResult` doc rewritten — the invariant claim now names the enforcement mechanism explicitly.
- Added `dice_result_payload_rejects_face_count_mismatch` (sends count=4 + faces=[6], asserts rejection with error message check) and `dice_result_payload_accepts_correct_face_counts_for_pool` (happy-path 4d6+2d10).

**Finding 3 — `DiceRequestPayloadRaw` escape hatch (non-blocking)** → FIXED via module-boundary hiding:
- Both Raw types are now inside `mod dice_payload_raw { ... }` with `pub(super)` visibility. Not nameable outside `crate::message`.
- Serde attributes reference them as `dice_payload_raw::DiceRequestPayloadRaw` / `dice_payload_raw::DiceResultPayloadRaw`.
- The adversarial probe from cycle-2 (deserializing Raw directly) would now fail to compile — stronger than the `#[doc(hidden)]` convention it replaces.

### Tests

- **35/35 dice protocol tests passing** (was 32 after cycle 2; +3 for face-count rejection, face-count happy-path, and Unknown sentinel pinning).
- **Full sidequest-protocol crate: 183 tests passing** (was 180).
- `cargo build --workspace`: clean.
- `cargo clippy -p sidequest-protocol --tests -- -D warnings`: clean.
- `cargo fmt --all`: applied.

### Deviations / Notes

- Cycle-2 Reviewer offered two options for each blocker; I picked option (a) (fix the code to match the doc) for both. Updating the code is strictly stricter than weakening the doc.
- `DiceResultPayloadError::FaceCountMismatch` currently has one variant. The cycle-2 reviewer mentioned a possible `TotalLiesAboutSum` check; I deferred it because the reviewer explicitly said "gate this if you think it's server-liar territory" and adding it would cascade through many manually-specified `total` fields in tests. Adding it later is a non-breaking extension to the `#[non_exhaustive]` enum.
- Picking `0` as the `Unknown` sentinel: simple, collides with no valid die size, and round-trips back to `Unknown` stably. Alternative `u32::MAX` would work but offers no advantage.

**Handoff:** Back to Reviewer (The Argument Professional) for the third review pass.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed, simplify completed in commit `906e414`

### Simplify Report

Simplify pass was run on this branch prior to Reviewer activation. Commit `906e414` ("refactor(34-2): simplify dice protocol per verify review") applied three findings from the simplify-efficiency analyzer:

1. Removed `Eq, Hash` from `DieSpec` — speculative derives for a hypothetical "cache pre-rendered dice meshes by spec" consumer that doesn't exist. CLAUDE.md: "Don't design for hypothetical future requirements."
2. Removed `Eq, Hash` from `RollOutcome` — `Hash` on a `#[non_exhaustive]` enum ties the hash surface to the public variant list. Doc updated to explain the omission.
3. Removed four redundant per-variant tests (`roll_outcome_crit_success_variant`, etc.) — fully subsumed by `roll_outcome_all_four_variants_round_trip` which constructs + serializes + deserializes + asserts every variant in a loop.

Rejected simplify findings (kept with rationale in the commit body): extraction of test helpers (would create style inconsistency — the crate has zero test helpers elsewhere) and two "redundant" individual field checks (kept as an explicit per-field ADR-074 checklist).

**Test count after simplify:** 27 dice protocol tests (down from 31). All passing.
**Workspace build:** Clean. Additional fmt commit `4782057` resolved pre-existing rustfmt drift across the workspace per `feedback_no_preexisting_excuse` (fix gates while context is loaded).

**Overall:** simplify: applied 3 high-confidence fixes, 2 rejected with rationale, 1 followup fmt chore

**Quality Checks:** All passing on branch tip `4782057`.
**Handoff:** To Reviewer for code review.

## Delivery Findings

No upstream findings at setup time.

<!-- Findings captured by each agent during their phase. -->

### TEA (test design)

- **Question** (non-blocking): Should `RollOutcome` use `#[non_exhaustive]`?
  Affects `sidequest-api/crates/sidequest-protocol/src/message.rs` (the enum declaration).
  The existing `FactCategory` enum is `#[non_exhaustive]`, but `NarratorVerbosity` and `NarratorVocabulary` are not. For this story, the four dice outcomes are protocol-fixed by ADR-074 — adding a fifth (e.g., `NearMiss`) would be a protocol change, not an internal refactor. Leaning toward `#[non_exhaustive]` for forward compatibility with future Growth scope (contested rolls could add outcomes), but Dev may decide otherwise.
  *Found by TEA during test design.*

- **Improvement** (non-blocking): The `pf validate context-story` and `pf validate context-epic` subcommands are broken — the help text advertises them, but the argument parser rejects them as "unknown validators". Additionally, OQ-2 doesn't actually use `context-story-*.md` / `context-epic-*.md` intermediate files — the pattern here is ADR + PRD → session directly. The context-gate check in `tea.md` on-activation should either be made project-aware, or the pf CLI should be fixed to match its help text.
  Affects `.pennyfarthing/agents/tea.md` (on-activation section) and/or the pf CLI validator module.
  *Found by TEA during test design.*

### Dev (implementation)

- **Gap** (non-blocking): TEA's non-blocking question about `RollOutcome` and `#[non_exhaustive]` was resolved by applying `#[non_exhaustive]` per the `FactCategory` precedent. Not a blocker, but future Reviewer should confirm this decision aligns with protocol evolution strategy. Affects `sidequest-api/crates/sidequest-protocol/src/message.rs` (no change needed — decision documented in Dev Assessment). *Found by Dev during implementation.*

- **Improvement** (non-blocking): `cargo fmt --check` reports pre-existing formatting drift at `sidequest-api/crates/sidequest-protocol/src/message.rs:177` (a blank line that rustfmt would remove). Not from my changes — it pre-dates this branch. Worth a separate chore PR that runs `cargo fmt --all` across the workspace so future per-file rustfmt invocations don't produce spurious diffs. Affects `sidequest-api` workspace formatting hygiene. *Found by Dev during implementation.*

- **Gap** (non-blocking): Docs `docs/api-contract.md` should eventually document the three new DICE_REQUEST / DICE_THROW / DICE_RESULT message types. Out of scope for story 34-2 (types-only) but belongs in a later docs task — likely after 34-4 (dispatch integration) and 34-8 (multiplayer broadcast) are wired, when the end-to-end flow is concrete. Affects `docs/api-contract.md` (add new message section citing ADR-074). *Found by Dev during implementation.*

### Reviewer (code review)

- **Conflict** (blocking): `DiceResultPayload.total: u32` type contradicts its doc (`sum(rolls) + modifier` with `modifier: i32`). Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1572` (change `u32` → `i32`, or add validated constructor with zero-clamp + test coverage for negative modifier boundary). *Found by Reviewer during code review.*
- **Gap** (blocking): `DieSpec.sides/count: u32` unbounded; ADR-074 enumerates `{4,6,8,10,12,20,100}` but the type accepts any u32 including `sides=0` (div-by-zero) and `count=u32::MAX` (DoS). Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1456` (convert `sides` to a bounded `DieSides` enum, or add validated `DieSpec::new()`). *Found by Reviewer during code review.*
- **Conflict** (blocking): `#[non_exhaustive]` on `RollOutcome` doc and session rationale claim wire forward-compatibility that serde does not provide — serde hard-rejects unknown variant tags regardless of the annotation. Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1484` (either add `#[serde(other)]` catch-all variant or amend the doc/session to remove the forward-compat claim). *Found by Reviewer during code review.*
- **Gap** (blocking): `GameMessage` pub enum is missing `#[non_exhaustive]`; this diff adds three variants, empirically proving it grows. Rule 2 of the Rust lang-review checklist requires it. Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:94` (one-line annotation addition). *Found by Reviewer during code review.*
- **Gap** (blocking): Four vacuous or under-asserted tests: `dice_throw_payload_carries_request_id_and_params` (missing `angular`/`position` asserts), `roll_outcome_all_four_variants_round_trip` (discriminant-only, not wire-string pin), `dice_result_round_trip_with_pool_rolls` (`if let` without `else panic!`), and the three `*_variant_exists` tautologies. Affects `sidequest-api/crates/sidequest-protocol/src/dice_protocol_story_34_2_tests.rs` (lines 46, 64, 81, 199, ~215, ~363). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `DiceResultPayload.rolls: Vec<u32>` flattens pool groupings — critical detection ("natural max on primary die"), UI display, and physics replay all need the per-spec slicing. Consider `Vec<DieGroupResult { spec, faces }>`, or document the intentional simplification and the server-side crit-detection contract. Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1568`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Envelope vs. payload `player_id` name collision on `DiceRequest`/`DiceResult` should be resolved by renaming the payload field to `rolling_player_id` rather than explaining the ambiguity in prose. Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1520, 1586`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `stat: String` should be a bounded `StatName` enum or validated newtype; doc currently references `BeatDef.stat_check` from a different crate (rustdoc can't validate cross-crate refs). Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1515, 1530`. *Found by Reviewer during code review.*
- **Question** (non-blocking): Should `dice: Vec<DieSpec>` allow empty pools and `difficulty: 0`? Both deserialize successfully and produce nonsensical game states. Decide intent and either document or enforce at the dispatch layer (34-3). Affects `sidequest-api/crates/sidequest-protocol/src/message.rs:1527, 1534`. *Found by Reviewer during code review.*

### Dev (rework after reject)

- **Gap** (non-blocking): `sidequest-agents/tests/script_tool_wiring_story_15_27_tests.rs` has 10 failing tests on `develop` HEAD (`7dce307`) and on every state of the `feat/34-2-dice-protocol-types` branch (before and after this commit). Verified against a separate worktree at develop. Failures: `allowed_tools_include_all_registered_script_tools`, `narrator_system_prompt_references_script_tools`, `prompt_includes_encountergen_section_when_registered_with_genre`, `prompt_includes_loadoutgen_section_when_registered_with_genre`, `prompt_includes_namegen_section_when_registered_with_genre`, `prompt_result_reports_injected_script_tools`, `registering_same_tool_twice_overwrites`, `script_tool_genre_passed_via_env_var`, `script_tool_sections_use_wrapper_names_not_binary_paths`, `wiring_script_tools_registered_injected_and_allowed`. Affects `sidequest-api/crates/sidequest-agents/tests/script_tool_wiring_story_15_27_tests.rs` (story 15-27 owns the fix — appears to be env_var / genre pack infrastructure for script tool invocation, unrelated to dice protocol types). *Found by Dev during rework after reject.*
- **Gap** (non-blocking): Workspace-wide `cargo clippy --workspace --tests -- -D warnings` fails with ~391 warnings at strict level, including `useless_vec`, `field_reassign_with_default`, `needless_loop` in `sidequest-game/src/lore/tests.rs`, `sidequest-genre/tests/hierarchical_graph_story_23_3_tests.rs`, and others. Verified as pre-existing — identical on `develop` HEAD and on the branch before my changes. Strict clippy on my direct touch-points (`sidequest-protocol` lib+tests, `sidequest-agents` lib, `sidequest-game/journal.rs`) is clean. Affects project-wide clippy hygiene; separate cleanup story needed. *Found by Dev during rework after reject.*
- **Conflict** (non-blocking): The main sidequest-api worktree had uncommitted modifications on `chore/clippy-workspace-cleanup` when the rework started. Used `git worktree add .worktrees/api-34-2 feat/34-2-dice-protocol-types` to work in isolation per the Reviewer's handoff guidance (and per `feedback_no_stash` memory). Worktree is at `/Users/keithavery/Projects/oq-2/.worktrees/api-34-2`; main worktree is untouched. Reviewer should be aware that the story branch work lives in a sibling worktree — `cd` to it or pull the branch in a fresh clone. *Found by Dev during rework after reject.*
- **Improvement** (non-blocking): `DiceResultPayload` still uses `deny_unknown_fields` directly rather than a `Raw` intermediary like `DiceRequestPayload` does. Reviewer finding #6 (pool grouping) was the only one touching `DiceResultPayload`'s structure; no validation invariants were added there (no empty-rolls check, no total-consistency check). Future work could mirror the validated-deserialization pattern on the result payload if we want total = sum(rolls_flat) + modifier enforced at the wire boundary — right now the invariant is documentary. *Found by Dev during rework after reject.*

## Design Deviations

No design deviations from ADR-074 or ADR-075 at setup time.

### TEA (test design)

- **Skipped proptest, used enumerated fixtures**
  - Spec source: `.session/34-2-session.md` AC section, written by SM
  - Spec text: "Proptest coverage: At least one roundtrip test using proptest or serde_test"
  - Implementation: Used enumerated fixtures (every RollOutcome variant, every tabletop die size d4..d100, negative modifier, dice pool with 4d6+2d10) instead of proptest-generated inputs
  - Rationale: Adding proptest as a new workspace dev-dep is out of scope for a types-only story. The enumerated fixtures cover 100% of the domain (4 outcome variants, 7 die sizes, all 8 ADR-074 fields per message) — proptest would generate redundant inputs. The AC allows "proptest OR serde_test" — my approach satisfies the underlying intent (prove serde preserves every field combination) without adding a dependency. If Dev or Reviewer wants property-based tests, they can be added in a follow-up test-only story.
  - Severity: minor
  - Forward impact: none — Dev's implementation surface is unchanged; the tests I wrote are strictly stricter than a single proptest would be (they assert exact values, not just round-trip equality)

### Dev (implementation)

- No deviations from spec. Implemented exactly as TEA's tests and the Dev Guidance section dictated: three GameMessage variants, six supporting types, `#[serde(deny_unknown_fields)]` on all payloads, `#[serde(rename = "SCREAMING_CASE")]` on all variants, `#[non_exhaustive]` on `RollOutcome` per TEA's non-blocking question and the `FactCategory` precedent.

- **Wire format revised during rework — intentional, per Reviewer fix list**
  - Spec source: `.session/34-2-handoff-green.md` (fix list #1–#17) and `.session/34-2-session.md` `## Reviewer Assessment`
  - Spec text: "Change `total: u32` → `total: i32`. Replace `sides: u32` with an enum whose variants are the seven ADR-074 values. Rename payload `player_id` → `rolling_player_id`. Change `rolls: Vec<u32>` to `Vec<DieGroupResult>`. Add `Unknown` variant to `RollOutcome` with `#[serde(other)]`."
  - Implementation: Applied all five schema changes plus `difficulty: NonZeroU32` and `count: NonZeroU8` validation. Every JSON fixture in the test suite updated to match the new wire format (`"sides": "20"` instead of `"sides": 20`, `"rolling_player_id"` instead of `"player_id"` inside payload blocks, `"rolls": [{"spec": ..., "faces": ...}]` instead of flat vec).
  - Rationale: Reviewer determined the prior schema encoded contract lies (u32 total can't hold sum(rolls)+negative_modifier, unbounded DieSpec permitted divide-by-zero, flat rolls lost pool attribution). Fixing at the protocol root — before dispatch/UI/physics stories consume these types — is strictly cheaper than migrating four downstream stories later.
  - Severity: major (wire format revision)
  - Forward impact: major on downstream stories that were planning against the original schema — 34-3 (resolution logic), 34-4 (dispatch wiring), 34-5 (physics replay), 34-8 (multiplayer broadcast) all need to use the new field names and per-group rolls shape. The UI story 34-4 also needs to read `rolling_player_id` and `DieGroupResult`. No downstream story has consumed the old schema yet (verified: no non-test consumers of `DiceRequestPayload`/`DiceResultPayload`/`DieSpec` exist on develop), so the migration cost is zero.

- **DiceRequestPayload uses serde try_from/into instead of plain derive**
  - Spec source: Reviewer fix list items #15, #16 (difficulty > 0, empty-pool rejection)
  - Spec text: "Add `difficulty > 0` invariant via validated constructor or type-level guard." / "Add `dice.is_empty()` guard."
  - Implementation: Introduced a private-by-convention `DiceRequestPayloadRaw` intermediary marked `#[doc(hidden)]`, with `DiceRequestPayload` implementing `TryFrom<Raw>` and a manual `Deserialize` impl that routes through it. `From<DiceRequestPayload>` for `Raw` provides the symmetric `Serialize` path via `#[serde(into = "DiceRequestPayloadRaw")]`. New error type `DiceRequestPayloadError` with `EmptyDicePool` and `BlankStat` variants, `#[non_exhaustive]`, `Display` + `Error` impls.
  - Rationale: This is the standard serde pattern for validated deserialization. It's the only way to enforce cross-field invariants (`dice.is_empty()` can't be expressed at the Vec type level, stat blank-check can't be expressed at the String type level) at the wire boundary. `difficulty=0` is caught earlier by `NonZeroU32`'s own deserializer. The extra indirection is mechanical and well-understood.
  - Severity: minor (implementation detail, not a user-visible contract change)
  - Forward impact: none — downstream consumers see the same `DiceRequestPayload` type. The `Raw` type is `#[doc(hidden)]` and not intended for direct use.

## Reviewer Assessment

**Verdict (Cycle 3):** APPROVED
**Branch:** `feat/34-2-dice-protocol-types` @ `004cf94` (Dev's cycle-3 rework commit)
**Data flow traced:** server emits `GameMessage::DiceRequest` → wire JSON with bare-integer `sides` + `NonZeroU32 difficulty` + non-empty `dice` pool (all validated at the wire boundary via `dice_payload_raw::DiceRequestPayloadRaw::try_from`) → client deserializes via `DiceRequestPayload::deserialize` → UI consumes `rolling_player_id` / `dice` / `difficulty` / `stat` / `context`. Mirror path for `DiceResult` routes through `dice_payload_raw::DiceResultPayloadRaw::try_from` which enforces `DieGroupResult.faces.len() == spec.count.get()` per-group. Both validated paths use the new private Raw submodule — the validation cannot be bypassed.
**Error handling:** `DiceRequestPayloadError` (EmptyDicePool, BlankStat) and `DiceResultPayloadError` (FaceCountMismatch { group_index, declared, actual }) are public, `#[non_exhaustive]`, implement `Display` and `Error`. Serde routes rejection through `serde::de::Error::custom`, surfacing the specific invariant in the error message — verified empirically in the cycle-3 probe.
**Cycle history:** Cycle 1 → 17 findings → fully applied. Cycle 2 → 3 new findings from the cycle-1 rework (doc/wire mismatch, unenforced invariant, escape hatch) → fully applied. Cycle 3 → verification pass below, 0 new findings.

### Cycle 3 verification

Re-ran the cycle-2 adversarial probe (same compiled binary pattern, same assertions) against Dev's `004cf94`. All 8 probes pass:

| # | Probe | Cycle-2 result | Cycle-3 result |
|---|-------|----------------|----------------|
| 1 | `DieSides::D20` wire format | `"20"` (quoted string — WRONG) | `20` (bare integer — correct) ✓ |
| 2 | Deserialize `20` (bare int) | `Err` (only quoted string worked) | `DieSides::D20` ✓ |
| 3 | Deserialize `"20"` (quoted) | `Ok` (legacy wire silently accepted) | `Err` — legacy wire properly dead ✓ |
| 4 | Unknown integer fallback (3, 999, u32::MAX) | N/A | all map to `DieSides::Unknown` ✓ |
| 5 | `count=4 + faces=[6]` | `Ok` (invariant NOT enforced — contract lie) | `Err("rolls[0] declared count=4 but got 1 face value(s)")` ✓ |
| 6 | Valid 4d6 pool happy path | N/A | deserializes cleanly ✓ |
| 7 | `DieSides::Unknown` round-trip | N/A | `Unknown → 0 → Unknown` stable ✓ |
| 8 | `DiceResultPayloadError::FaceCountMismatch` Display format | did not exist | `"rolls[2] declared count=4 but got 1 face value(s)"` — all fields present ✓ |

**Escape-hatch compile-time check:** Added a probe that tries `use sidequest_protocol::dice_payload_raw::DiceRequestPayloadRaw;` — fails at compile time with `error[E0432]: unresolved import sidequest_protocol::dice_payload_raw`. This is **stronger** than what I asked for in cycle-2 finding #3. I suggested either leaving it as `#[doc(hidden)]` or moving to a private inner module; Dev chose the stronger option, and the module system now makes bypass impossible from outside `crate::message`.

**Rust/serde insight worth archiving:** The `#[serde(rename = "N")]` pattern on unit enum variants tags the variant by its *name string*, producing quoted JSON strings on the wire — that's the default externally-tagged representation for unit variants. To get bare integer wire format, you need `#[serde(from = "u32", into = "u32")]` (infallible form — simpler than the `try_from` variant when you want an `Unknown` catch-all) plus explicit `From<u32> for EnumType` and `From<EnumType> for u32` impls. Cycle 1 used the `rename` pattern (producing strings); cycle 3 uses the `from/into` pattern (producing integers). Both work, but only one matches the doc claim and ADR-074 wire format.

### Cycle 2 findings (all resolved)

All three cycle-2 findings are fixed by commit `004cf94`:

1. **[DOC][TYPE] DieSides doc/wire mismatch** → FIXED. Serializer now emits bare integers matching both the doc and ADR-074. `From<u32>` / `From<DieSides> for u32` with infallible bridge. `DieSides::Unknown` uses `0` as the stable sentinel.
2. **[DOC][EDGE] DieGroupResult invariant unenforced** → FIXED. New `DiceResultPayloadRaw` intermediary with `TryFrom` validation that walks `rolls` and rejects any group where `faces.len() != spec.count.get()`. New error type `DiceResultPayloadError::FaceCountMismatch` with full field information.
3. **[TYPE] DiceRequestPayloadRaw escape hatch** → FIXED beyond the original ask. Both Raw types moved to a private `mod dice_payload_raw { pub(super) ... }` — no longer nameable from outside `crate::message`. Compile-time guarantee, not a `#[doc(hidden)]` convention.

### Tests

- **35/35 dice protocol tests passing** (was 32 after cycle 2; +3 for face-count rejection + happy-path pool + Unknown sentinel).
- **Full `sidequest-protocol` crate: 183 tests passing** (was 180).
- `cargo build --workspace`: clean.
- `cargo clippy -p sidequest-protocol --tests -- -D warnings`: clean.
- The pre-existing `script_tool_wiring_story_15_27_tests` failures on `develop` are unchanged — they were pre-existing on develop HEAD before this story started, fail identically at every branch state, and are unrelated to dice protocol. Not a regression. Out of scope for 34-2 per the cycle-1 delivery findings.

### Rule Compliance (cycle 3)

| Rule | Applied to | Result |
|------|-----------|--------|
| #2 `#[non_exhaustive]` on growing enums | `GameMessage`, `RollOutcome`, `DieSides`, `NarratorVerbosity`, `NarratorVocabulary`, `JournalSortOrder`, `DiceRequestPayloadError`, `DiceResultPayloadError` | ✓ all compliant |
| #3 No placeholder sentinels | `DieSides::Unknown → 0` is a **documented** sentinel, not a silent placeholder — the `From<u32>` impl explicitly handles the round-trip | ✓ compliant |
| #5 Validated constructors at trust boundaries | `DiceRequestPayload` and `DiceResultPayload` both route deserialization through private `Raw::try_from` | ✓ compliant |
| #6 Test quality | 35 dice tests; every new test has meaningful assertions pinning the fixed invariants | ✓ compliant |
| #7 No unsafe `as` casts on external input | Only `spec.count.get() as usize` inside the TryFrom, converting `NonZeroU8 → usize` for length comparison | ✓ safe (u8 always fits in usize) |
| #8 `#[derive(Deserialize)]` bypass | Both dice payload types have custom Deserialize impls routing through validated Raw paths — no bypass possible | ✓ compliant |
| #9 Public fields on invariant-bearing types | `DieGroupResult` has pub fields but the invariant is enforced at `DiceResultPayload` construction — can't be bypassed from wire. Direct struct construction in the same crate is acceptable for test helpers. | ✓ compliant |
| #11 Workspace deps | No deps added in cycle 3 | ✓ compliant |
| #15 Unbounded recursive input | No recursion in new types | ✓ compliant |

### Devil's Advocate (cycle 3)

What could still be broken?

- **Server-liar check on `total`.** The `total` field is still not validated against `sum(flat_rolls) + modifier`. Dev explicitly deferred this in the cycle-3 assessment: "gate this if you think it's server-liar territory." Is that deferral reasonable? Yes — the server is the authoritative source of `total` in ADR-074, and the client reading a wrong total would display the wrong number without breaking downstream logic. Unlike the face-count mismatch (which breaks CritSuccess detection), a wrong `total` is a display bug, not a state-corruption bug. Non-blocking. If Keith wants it, it's a one-function addition to `DiceResultPayloadRaw::try_from` — can be a later cycle.

- **Could an attacker use the `0` sentinel to forge an `Unknown` die?** No. The wire value `0` deserializes to `DieSides::Unknown`, and `Unknown.faces()` returns `None`. Any downstream RNG code that calls `.faces()?` will refuse the roll — that's the whole point of the `Option` return. A malicious client sending `sides: 0` gets exactly the same behavior as sending `sides: 3` or `sides: 999` — all fall to `Unknown` and all refuse to roll.

- **`NonZeroU8` for count caps at 255. Is that enough?** Yes. Tabletop dice pools in any sane game are < 20 dice. 255 is 10× above any reasonable pool size. The 255 cap is what prevents the `u32::MAX` allocation DoS the original type was vulnerable to.

- **`DiceRequestPayload.stat: String` is still not a bounded enum.** Cycle-1 finding #5 resolution: the validation was moved to "non-blank" at the wire boundary, with full bounded validation deferred to dispatch layer (34-3). I accepted this in cycle 1 because the stat list is genre-pack-configurable. Still stands — not a cycle-3 regression.

- **The `total` field is `i32` — can it overflow?** Max realistic roll: 255 dice × 100 sides = 25,500 + `i32::MAX` modifier. `i32::MAX` is ~2 billion; 25,500 + 2 billion doesn't overflow. Fine.

Devil's advocate finds nothing new. Approving.

### Deviation Audit

#### Reviewer (audit — cycle 3)

- **Dev picked option (a) — "fix the code" — for both cycle-2 blockers** → ✓ ACCEPTED. Option (a) is strictly stricter than option (b) for both findings. The rework actually delivers the invariants the docs claim, rather than weakening the docs to match.
- **Dev moved Raw types to a private submodule** → ✓ ACCEPTED, beyond the original ask. I suggested this as option (b) for finding #3; Dev implemented it. The compile-time guarantee is stronger than `#[doc(hidden)]`.
- **Dev deferred the `total` consistency check** → ✓ ACCEPTED with the rationale given in the cycle-3 assessment (reviewer explicitly said "gate this" + cascade cost in manual `total` fields). Not blocking. If needed, add it in a later cycle as a non-breaking extension to `DiceResultPayloadError`.
- **`DieSides::Unknown` serializes as `0` (sentinel collision with "zero-sided die")** → ✓ ACCEPTED. Zero-sided dice are physically nonsensical; the sentinel collision is harmless unless a future genre pack literally wants a `D0` die for flavor reasons, in which case a follow-up story can use a dedicated `Option<DieSides>` or move to a different sentinel.

### Handoff

**APPROVED.** Story 34-2 ready for finish. Over to SM (The Announcer) for `pf sprint story finish` and Epic 34's downstream stories (34-3 dispatch, 34-4 UI, 34-5 physics, 34-8 multiplayer broadcast) are unblocked on these types.

### Cycle 2 fix list — rework introduced new contract lies

All three findings verified empirically with a compiled adversarial probe against the branch-tip types. Probe output archived in the assessment commit notes.

1. **[DOC][TYPE] `DieSides` serializes as JSON string `"20"`, not integer `20` — doc comment says the opposite.** `message.rs:1457` (DieSides doc, top of enum) states: _"Serialized as the integer face count (`4`, `6`, `8`, `10`, `12`, `20`, `100`) to keep the JSON shape identical to what the UI drag-and-flick code expects from ADR-074 fixtures."_ This is false in two ways:
   - Empirical: `serde_json::to_string(&DieSides::D20)` produces the literal `"20"` (with quotes — a JSON string), and `serde_json::from_str::<DieSpec>("{\"sides\": 20, \"count\": 1}")` returns `Err`. Only the string form `{"sides": "20"}` deserializes.
   - Evidentiary: Dev had to change every test fixture in `dice_protocol_story_34_2_tests.rs` from `{"sides": 20}` to `{"sides": "20"}` during the rework — which is the paper trail proving the wire format shifted.
   - `#[serde(rename = "4")]` on unit enum variants tags the variant by string name — that's what Rust/serde produce, not what the doc claims.

   **Fix:** Pick one (Reviewer does not care which, as long as doc and code agree):
   - **(a)** Change the serializer to actually emit integers. Replace the current `#[serde(rename = "N")]` pattern with `#[serde(into = "u32", try_from = "u32")]` plus `impl From<DieSides> for u32` and `impl TryFrom<u32> for DieSides`. The Unknown variant stops carrying a wire value; serde forwards unknown u32 to the TryFrom impl which maps "not in set" → `Unknown`.
   - **(b)** Rewrite the DieSides doc to acknowledge the string wire format: _"Serialized as the stringified face count (`"4"`, `"6"`, `"8"`, `"10"`, `"12"`, `"20"`, `"100"`). This is a Rust/serde enum-representation choice — unit variants tag by name. Matching ADR-074's integer JSON would require a custom `into = "u32"` / `try_from = "u32"` adapter that adds maintenance burden. Pick (a) instead if ADR-074's integer wire is load-bearing for cross-client interop."_ Also update ADR-074 itself or add a comment in the ADR if the wire format has diverged from the original design.

   Either way, the test fixtures stay the same after the fix (they already use strings); only the doc (and possibly the serializer) changes.

2. **[DOC][EDGE] `DieGroupResult.faces.len() == spec.count` is a documentary invariant with no enforcement.** `message.rs:1543` (DieGroupResult doc) says: _"Invariant (enforced at construction and via the `#[serde(try_from)]` guard on the containing payload): `faces.len() == spec.count.get() as usize`."_ Neither mechanism exists:
   - No `try_from` on `DiceResultPayload` (it uses plain derive). Only `DiceRequestPayload` has the `try_from`/`into` bridge; `DiceResultPayload` still uses the naive derive path.
   - No constructor on `DieGroupResult` — all fields are public, so "enforced at construction" has no enforcement surface.
   - Empirical: sent `{"spec": {"sides": "6", "count": 4}, "faces": [6]}` in a complete `DiceResultPayload` JSON. Deserialized successfully with `count=4` declared but only 1 face. The claimed invariant is pure fiction.

   **Fix:** Pick one:
   - **(a)** Mirror the `DiceRequestPayload` pattern: introduce `DiceResultPayloadRaw` with `deny_unknown_fields`, add `TryFrom<Raw>` validation that walks `payload.rolls` and rejects any `DieGroupResult` where `faces.len() != spec.count.get() as usize`. Also consider validating `total == rolls.iter().flat_map(|g| &g.faces).sum::<i32>() + modifier` — the total field is currently capable of lying about the sum. Gate this second check if you think it's server-liar territory; the first check (faces count) is non-negotiable.
   - **(b)** Delete the invariant claim from the doc. Say: _"`faces` holds the rolled values in roll order. The length is expected to match `spec.count.get()` but is not enforced at the wire boundary — downstream consumers (dispatch in 34-3) must validate before using the values."_

   (a) is strictly better because it closes the same kind of "server sends garbage" hole that fix #16 in cycle 1 closed for `DiceRequestPayload`. (b) is acceptable only if Keith decides dispatch-layer validation is sufficient for the result side.

3. **[TYPE] (non-blocking, low) `DiceRequestPayloadRaw` is a `pub` escape hatch.** It is marked `#[doc(hidden)]` which is a documentation convention, not a compiler-enforced boundary. An advanced caller can bypass all the `TryFrom` validation by deserializing `DiceRequestPayloadRaw` directly:
   ```
   let raw: DiceRequestPayloadRaw = serde_json::from_str(bad_json).unwrap();
   // raw.dice is []; raw.stat is "" — neither validated.
   ```
   Empirically confirmed with the probe: a deserialize targeting `DiceRequestPayloadRaw` with `dice: []` and `stat: ""` succeeds.

   This is LOW severity because:
   - It requires actively circumventing `#[doc(hidden)]` and the clearly-named private-intent type.
   - The `#[serde(into = "DiceRequestPayloadRaw")]` attribute on `DiceRequestPayload` requires Raw to be accessible from the same visibility scope — making Raw `pub(crate)` would break the serialize side unless you put both types in the same module-private namespace with a re-export.

   **Suggested fix (if you want to close the hole):** Move `DiceRequestPayloadRaw` into a private inner module `mod raw { pub(super) struct DiceRequestPayloadRaw { ... } }`. Serde attributes reference it as `#[serde(into = "raw::DiceRequestPayloadRaw")]` — this keeps serde happy while hiding the type from the crate's public API. Alternatively, leave it and trust `#[doc(hidden)]` + the naming convention to warn careful users off.

### Cycle 1 fix list (for reference — all applied and verified)

All items below are fix-this-story, not fix-later. The Reviewer does not ship code it can see is broken.

**Type correctness**

1. **`DiceResultPayload.total: u32` → `i32`.** [TYPE] [EDGE] [TEST] [DOC] Doc says `total = sum(rolls) + modifier` with `modifier: i32`. `rolls=[1], modifier=-5` has no u32 representation; the server will wrap silently on release builds. Every test avoids this case by using non-negative modifiers. `message.rs:1572`.

2. **`DieSpec` → `DieSides` enum.** ADR-074 enumerates `{4, 6, 8, 10, 12, 20, 100}`. Current `sides: u32` accepts `0` (divide-by-zero in any `% sides` RNG) and `u32::MAX` (allocation DoS). Replace `sides: u32` with an enum whose variants are the seven ADR-074 values — serde will reject bad JSON at parse time. Cap `count` via `NonZeroU8` or bounded newtype. `message.rs:1456`.

3. **`GameMessage` add `#[non_exhaustive]`.** [RULE] This diff adds three variants to it, empirically proving it grows. Dev's compile-time exhaustive-check argument is reactive; `#[non_exhaustive]` is preventative. All downstream match arms are already wildcard-safe per Dev's own compile-time check, so adoption is zero-cost. `message.rs:94`.

4. **`RollOutcome` forward-compat claim is false.** Both the doc comment and Dev Assessment cite `#[non_exhaustive]` as delivering wire forward-compatibility. It does not — serde hard-rejects unknown variant strings regardless of the annotation. An older client receiving `"outcome": "NearMiss"` from a newer server will `Err` on the wire. Fix: add `#[serde(other)] Unknown` catch-all variant so deserialization of unknown tags silently falls to `Unknown` instead of erroring. This is the only way to actually get what the comment claims. `message.rs:1484`.

5. **`stat: String` → `StatName` enum.** Bounded domain (dexterity/strength/constitution/wisdom/intelligence/charisma/… per the genre pack ability list). Typos like `"Dexterity"` or `""` currently pass silently and reach the narrator prompt. If the list is genre-configurable, use a validated newtype with whitelist check at the server boundary. `message.rs:1515`.

6. **`rolls: Vec<u32>` → `Vec<DieGroupResult>`.** `DiceRequestPayload.dice` carries structured groups (4d6 + 2d10), but `DiceResultPayload.rolls` is a flat vec that loses attribution. `CritSuccess` is doc-defined as "natural maximum on the primary die" — formally unresolvable from a flat vec. Replace with `rolls: Vec<DieGroupResult { spec: DieSpec, faces: Vec<u32> }>` so UI display, crit detection, and physics replay all have per-group data. `message.rs:1568`.

7. **Rename payload `player_id` → `rolling_player_id`** on `DiceRequestPayload` and `DiceResultPayload`. Same-name collision with envelope `player_id` is currently explained away in prose; should be resolved in the type. Doc on `DiceResult` variant also needs to mirror `DiceRequest`'s warning (currently asymmetric). `message.rs:1520, 1586, 387`.

**Test correctness**

8. **`dice_throw_payload_carries_request_id_and_params`** silently ignores `angular` and `position` asserts despite constructing them with specific values. Add `assert_eq!(payload.throw_params.angular, [0.0, 0.0, 0.0])` and `assert_eq!(payload.throw_params.position, [0.5, 0.5])`. `dice_protocol_story_34_2_tests.rs:~195`.

9. **`roll_outcome_all_four_variants_round_trip`** uses `mem::discriminant` instead of pinning the wire string. Would pass even if variants serialized as integers. Add `assert_eq!(serde_json::to_string(&RollOutcome::CritSuccess).unwrap(), "\"CritSuccess\"")` for each variant. `dice_protocol_story_34_2_tests.rs:~215`.

10. **`dice_result_round_trip_with_pool_rolls`** [SILENT] uses `if let` without `else panic!`. Replace with `match { _ => panic!("expected DiceResult variant") }` to match the sibling round-trip tests. `dice_protocol_story_34_2_tests.rs:~363`.

11. **Delete the three tautological `*_variant_exists` tests** (`dice_request_variant_exists`, `dice_throw_variant_exists`, `dice_result_variant_exists`). `assert!(matches!(...))` on a value just constructed as that variant can never fail. The round-trip tests already cover the real behavior. `dice_protocol_story_34_2_tests.rs:46, 64, 81`.

12. **Expand `dice_types_reachable_via_crate_root`** to construct all six new public types, not just `DieSpec`/`ThrowParams`/`RollOutcome`. The AC8 wiring check should be exhaustive. `dice_protocol_story_34_2_tests.rs:~700`.

**Doc correctness**

13. **Move "cryptographically generated" qualifier** from `ThrowParams` struct doc to `DiceResultPayload.seed` field doc where it belongs. `message.rs:1479, 1579`.

14. **Rewrite `DiceRequestPayload.stat` doc** to drop the cross-crate `BeatDef.stat_check` reference (rustdoc can't validate cross-crate refs and it will drift silently). Plain-language description: `Ability name for the check (e.g., "dexterity", "strength"). Set by the narrator from the beat definition.` `message.rs:1530`.

15. **Add `difficulty > 0` invariant** via validated constructor or type-level guard. `difficulty=0` currently deserializes successfully and makes every roll a guaranteed `Success`. If genre packs need degenerate cases, document that explicitly. `message.rs:1534`.

16. **Add `dice.is_empty()` guard.** `DiceRequestPayload.dice: vec![]` currently deserializes successfully and yields a nonsensical game state (modifier-only roll with no dice). Either use `NonEmpty<DieSpec>` or add a validated constructor. `message.rs:1527`.

**Pre-existing rule violations in changed file (fix while context is loaded)**

17. **`NarratorVerbosity`, `NarratorVocabulary`, `JournalSortOrder` missing `#[non_exhaustive]`.** Rule-2 violations in `message.rs` flagged by rule-checker. These are pre-existing but the file is being touched anyway and the fix is a one-line annotation each. `message.rs:38, 73, 1276`.

### Deviation Audit

#### Reviewer (audit)

- **TEA skipped proptest in favor of enumerated fixtures** → ✓ ACCEPTED. Enumerated coverage over the bounded domain (4 outcomes × 7 die sizes × 8 fields) is strictly stricter than a single proptest would be, and avoids adding a dev-dep.

- **Dev applied `#[non_exhaustive]` to `RollOutcome` citing wire forward-compat** → ✗ FLAGGED. The annotation does not deliver the claimed behavior — see fix #4. Must either implement `#[serde(other)]` or correct the justification.

- **Session file drift:** Dev Assessment describes 31 tests and `DieSpec` deriving `Eq, Hash`. Post-simplify commit `906e414` removed four tests (now 27) and removed `Eq, Hash` from `DieSpec` + `RollOutcome`. Session is stale vs. branch. Not a blocker — flagging for housekeeping. Session files are for our own tracking, not cross-team comms, but they should still match reality. Recommend: Dev rewrites the Assessment after the fix pass to reflect the post-simplify state.

### Handoff (Cycle 2)

Back to Dev (Bicycle Repair Man) for the **2 blocking findings** (DieSides doc/wire mismatch, DieGroupResult invariant claim). Finding 3 (Raw escape hatch) is non-blocking — fold in if cheap, else defer. All 17 cycle-1 findings are verified applied and closed.

**Tests at branch tip `30646e3`:** 32/32 dice protocol tests pass, 180/180 full sidequest-protocol crate passes, workspace builds clean, clippy clean on all files Dev touched. The problems are the two documentation contract lies I found via the adversarial probe — not a regression in the test suite.

**Scope reminder for Dev:** pick exactly one resolution for each blocker (doc-only or code-change). Reviewer does not demand one over the other — both ends (make doc match code, or make code match doc) close the contract lie. The goal is: every claim the type makes is enforceable or empirically observable at the wire boundary.

**Branch handling:** Dev's worktree at `.worktrees/api-34-2` is already set up on the story branch. Keith's clippy WIP in the main worktree on `chore/clippy-workspace-cleanup` is still untouched. Keep it that way.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Skipped | n/a | n/a | Branch conflict: WIP on `chore/clippy-workspace-cleanup`. Domain covered via git show + compile-time reasoning. |
| 2 | reviewer-edge-hunter | Yes | findings | 7 | all confirmed |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 | confirmed |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 7, 1 superseded |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 | all confirmed |
| 6 | reviewer-type-design | Yes | findings | 6 | all confirmed |
| 7 | reviewer-security | Skipped | disabled | n/a | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | n/a | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 6 | all confirmed |

**All received:** Yes (6 returned, 2 disabled, 1 skipped with rationale)