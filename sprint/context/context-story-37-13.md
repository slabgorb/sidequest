# Story 37-13: Encounter creation gate silently drops new confrontation type

## Overview

The encounter-creation branch in `dispatch/mod.rs` silently discards a new `confrontation_type` from the narrator whenever the current `StructuredEncounter` exists and is unresolved. No OTEL event, no state transition, no warning. The narrator describes a new scene (poker game) while the mechanical state is still locked to the previous encounter (gunfight). This is the root cause for 37-12 and a direct CLAUDE.md "No Silent Fallbacks" violation.

**Status:** Setup complete. Ready for TEA (RED phase).

## Story Scope

### What Gets Built
- A **decision gate** that covers every case of `(current_encounter_state, incoming_confrontation_type)` with a clear, observable branch.
- An OTEL `WatcherEvent` on every branch — accept-new / replace-stale / reject-duplicate-redeclare / reject-mid-encounter / def-missing.
- Actor re-population from the fresh snapshot when a replacement occurs (players + `result.npcs_present`), mirroring the existing success-path construction.
- Tests (RED first) covering every branch and one integration test asserting the gate is reachable from the real narrator-response dispatch path.

### What Stays Unchanged
- `apply_beat` and all beat dispatch logic (`dispatch/mod.rs:1821+`, `dispatch/beat.rs`).
- `find_confrontation_def` and `ConfrontationDef` loading.
- Genre pack YAML or confrontation type catalog.
- Narrator prompt / re-declare logic — that is **37-12**, a downstream story.
- Trope completion handshake — that is **37-15**, a separate story.

## Problem Location

`sidequest-api/crates/sidequest-server/src/dispatch/mod.rs`, lines **1773–1819**:

```rust
if let Some(ref confrontation_type) = result.confrontation {
    if ctx.snapshot.encounter.is_none()
        || ctx.snapshot.encounter.as_ref().is_some_and(|e| e.resolved)
    {
        if let Some(def) = crate::find_confrontation_def(&ctx.confrontation_defs, confrontation_type) {
            // build encounter, populate actors
            WatcherEventBuilder::new("encounter", WatcherEventType::StateTransition)
                .field("event", "encounter.created")
                ...
            ctx.snapshot.encounter = Some(encounter);
        } else {
            tracing::warn!(...); // ONLY log — no watcher event
        }
    }
    // <<< NO ELSE: if encounter exists and unresolved, new type is SILENTLY dropped
}
```

The outer `if` has no `else`. Every code path where `encounter.is_some() && !resolved` exits the block untouched, with zero telemetry.

## Design Decision — Replace vs Reject

**Policy: Conditional Replace, keyed on "has any beat been dispatched on the current encounter."**

| Case | Current state | Incoming `confrontation_type` | Action | OTEL event |
|------|---------------|------------------------------|--------|------------|
| A | `None` | `Some(new)` | Create new encounter (existing success path) | `encounter.created` (unchanged) |
| B | `Some(e)`, `e.resolved == true` | `Some(new)` | Create new encounter (existing path, different type) | `encounter.created` (unchanged) |
| C | `Some(e)`, `!resolved`, `e.encounter_type == new` | `Some(new)` | **No-op**. Narrator re-declared the same active encounter; keep state as-is. | `encounter.redeclare_noop` (`StateTransition`, info) |
| D | `Some(e)`, `!resolved`, different type, **no beats have fired yet** (`e.beat == 0`) | `Some(new)` | **Replace**. Old encounter was never acted on; it's dead weight. | `encounter.replaced_pre_beat` (`StateTransition`, info) |
| E | `Some(e)`, `!resolved`, different type, **beats already fired** (`e.beat > 0`) | `Some(new)` | **Reject**. Mid-encounter state (metric, actor state) must not be clobbered. Keep old encounter. | `encounter.new_type_rejected_mid_encounter` (`ValidationWarning`, warn) |
| F | Any | `Some(new)`, `find_confrontation_def` returns `None` | Keep existing `tracing::warn!` AND emit watcher event. | `encounter.creation_failed_unknown_type` (`ValidationWarning`, warn) |

### Rationale

1. **Narrator is authoritative on scene transitions** — but only when the scene hasn't yet generated mechanical state. A fresh encounter with `beat == 0` has no HP depletion, no per-actor state, nothing to lose. Replacing it is safe and correct.
2. **Mid-encounter state is sacred** — once beats fire, metric values, per-actor state, and tier events have accumulated. Clobbering them would corrupt the confrontation engine's invariants. In that case, narrator prose diverges, but we surface the divergence as `ValidationWarning` so the GM panel catches it. 37-12 will later teach the narrator to re-declare only within valid transitions; 37-13 just needs to not lie.
3. **Case C (re-declare same type) is a known narrator behavior** — the narrator often restates the encounter type each turn for prompt clarity. Treating that as a no-op with explicit telemetry is better than treating it as a replace (churn) or a reject (false alarm).
4. **Every branch is observable** — the GM panel becomes the lie-detector the ADR-031 model requires. A silent drop is the failure mode OTEL exists to prevent.

### Replacement Path — State Integrity Rules (Case D)

When replacing:
1. Mark old encounter `resolved = true` before overwrite (or log `encounter.abandoned_pre_beat` — pick one inside the implementation; TEA tests for the observable effect: the old encounter is not still sitting in state after replacement).
2. Rebuild the new `StructuredEncounter` from `ConfrontationDef` via `from_confrontation_def` (same call as current success path).
3. Re-populate actors from `ctx.snapshot.characters` + `result.npcs_present` (same loop as current success path) — **do not** copy actors from the old encounter. The new confrontation type may have a completely different actor set.
4. `per_actor_state` starts empty (same as current path). Any old per-actor state is intentionally dropped — it belonged to a different encounter type.
5. Assign to `ctx.snapshot.encounter = Some(new_encounter)` exactly like the current success path.

### "Has any beat been dispatched" check

The existing `StructuredEncounter` carries a `beat: u32` counter (see ADR-033 struct excerpt). Policy check:

```rust
let old_has_fired = ctx.snapshot.encounter.as_ref().is_some_and(|e| e.beat > 0);
```

TEA: if the real struct uses a different field name, the policy stays the same — "has any beat been applied to this encounter." Dev can map it to the correct field during GREEN.

## Acceptance Criteria (RED Phase Gate)

All tests must be written and failing before GREEN starts.

### AC1 — No Silent Drops
- [ ] When `result.confrontation == Some(new)` and `ctx.snapshot.encounter` is `Some(unresolved, different_type, beat > 0)`, the gate emits a `WatcherEvent` (`encounter.new_type_rejected_mid_encounter`) and leaves state unchanged.
- [ ] When `result.confrontation == Some(new)` and `ctx.snapshot.encounter` is `Some(unresolved, different_type, beat == 0)`, the gate emits `encounter.replaced_pre_beat` and `ctx.snapshot.encounter` is now the new type with fresh actors.
- [ ] No code path in the gate exits without emitting a `WatcherEvent` when `result.confrontation.is_some()`.

### AC2 — Distinct Events Per Branch
- [ ] `encounter.created` — new encounter from `None` or resolved old (existing behavior preserved).
- [ ] `encounter.redeclare_noop` — same-type re-declare.
- [ ] `encounter.replaced_pre_beat` — replacement before any beat fired.
- [ ] `encounter.new_type_rejected_mid_encounter` — rejection after beats have fired.
- [ ] `encounter.creation_failed_unknown_type` — `find_confrontation_def` returned `None` (complements existing `tracing::warn!`, does not replace it).
- [ ] Each event carries `encounter_type` (incoming), and where applicable `previous_encounter_type` and `beat_count`.

### AC3 — Replacement Integrity
- [ ] After a Case D replacement, `ctx.snapshot.encounter.as_ref().unwrap().encounter_type == new_type`.
- [ ] Actors on the new encounter include every `ctx.snapshot.characters` entry with `role = "player"` and every `result.npcs_present` entry with `role = "npc"`.
- [ ] No actor from the old encounter is carried over unless it is independently present in `characters` or `npcs_present`.
- [ ] New encounter's `per_actor_state` is empty for every actor.

### AC4 — Same-Type Re-declare is a No-Op
- [ ] Case C: `ctx.snapshot.encounter` pointer/contents unchanged (metric, actors, beat counter all identical before and after the gate).
- [ ] A single `encounter.redeclare_noop` event is emitted (not `encounter.created`, not `encounter.replaced_pre_beat`).

### AC5 — Unknown Confrontation Type Observability
- [ ] When `find_confrontation_def` returns `None`, the existing `tracing::warn!` still fires (do not delete it).
- [ ] A `ValidationWarning` `WatcherEvent` with `event = "encounter.creation_failed_unknown_type"` is emitted.
- [ ] `ctx.snapshot.encounter` is unchanged.

### Wiring Test (mandatory per CLAUDE.md)
- [ ] One integration test drives the gate through the real narrator-response dispatch entry point (the same caller as today — search for the function that invokes this block in `dispatch/mod.rs`). Unit-only coverage of the gate is insufficient.
- [ ] Assertion: with a pre-populated `ctx.snapshot.encounter` and a narrator result carrying a new `confrontation` field, the expected `WatcherEvent` appears on the `subscribe_global()` channel.

### No Regressions
- [ ] Existing `encounter.created` path still fires for Cases A and B.
- [ ] `apply_beat` flow (lines 1821+) is not modified.
- [ ] `dispatch/beat.rs` is not modified.
- [ ] `find_confrontation_def` is not modified.

## Test Strategy Hints for TEA

### Existing Patterns to Mirror

**OTEL capture:** `crates/sidequest-server/src/otel_dice_spans_34_11_tests.rs` is the reference.
- `sidequest_telemetry::init_global_channel` + `subscribe_global` to get a `broadcast::Receiver<WatcherEvent>`.
- Local `drain_events(&mut rx) -> Vec<WatcherEvent>` helper.
- Filter by `event` field name; assert `WatcherEventType` variant.

**Dispatch context construction:** Search for call sites that build a `DispatchContext` in tests:
- `crates/sidequest-server/src/dispatch/connect.rs`, `mod.rs`, `beat.rs` all construct `DispatchContext` — check for a `#[cfg(test)]` builder or a test helper already in use.
- If none exists, a minimal struct-literal build is fine (same pattern as production call sites) — keep it in the test file, not a new module.

**Encounter fixtures:** `crates/sidequest-server/tests/integration/encounter_context_wiring_story_28_4_tests.rs` has `standoff_yaml()` / `combat_yaml()` fixtures you can reuse or copy. Load `ConfrontationDef` via `sidequest_genre` YAML parsing like that test does.

**Snapshot pre-population:** Build a `GameSnapshot` with `encounter: Some(StructuredEncounter { encounter_type: "combat", beat: 0, resolved: false, actors: vec![..], .. })`. The existing 28-x tests show how to mint a `StructuredEncounter` directly (not through the gate).

### Test File Location
Put tests at `crates/sidequest-server/tests/integration/encounter_creation_gate_story_37_13_tests.rs`. Register in `crates/sidequest-server/tests/integration/main.rs` (follow pattern of other `_story_XX_Y_tests.rs` files).

### Test Matrix (one test per case)
1. `case_a_no_current_encounter_creates_new` (regression guard on existing `encounter.created`)
2. `case_b_resolved_current_encounter_creates_new` (regression guard)
3. `case_c_same_type_redeclare_is_noop`
4. `case_d_different_type_pre_beat_replaces`
5. `case_d_replacement_repopulates_actors_from_snapshot_and_npcs`
6. `case_d_replacement_drops_old_per_actor_state`
7. `case_e_different_type_mid_encounter_rejects_with_validation_warning`
8. `case_f_unknown_confrontation_type_emits_validation_warning`
9. `wiring_narrator_response_dispatch_hits_gate` (integration via real entry point)

## Files to Modify

### Primary (Dev / GREEN phase)
- `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` — extend the gate block at lines 1773–1819 to cover all six cases.

### Test Coverage (TEA / RED phase)
- `sidequest-api/crates/sidequest-server/tests/integration/encounter_creation_gate_story_37_13_tests.rs` — NEW
- `sidequest-api/crates/sidequest-server/tests/integration/main.rs` — register new test module

### No Changes
- `sidequest-genre`, `sidequest-game::encounter`, `sidequest-telemetry`, `sidequest-protocol`
- Any other crate

## Out of Scope (Do Not Touch)

- **37-12** — narrator prompt re-declare behavior. This story fixes the *gate*, not the prompt. Once the gate stops lying, 37-12 can wire the narrator to emit re-declares when appropriate.
- **37-15** — trope completion handshake with encounter lifecycle.
- `apply_beat` / `dispatch/beat.rs` / beat dispatch loop.
- `find_confrontation_def` and any changes to how confrontation types are looked up.
- New confrontation types in `sidequest-content/genre_packs/`.
- The narrator's system prompt.
- Any UI/GM panel changes (they'll start showing the new events automatically via the existing subscribe-global pipe).

## Branch Recommendation

**Current API branch:** `chore/api-ci-and-test-isolation` (NOT yet merged to `develop`). Recent commits on this branch:
- `dc5cf15 chore(tests): rewrite the 39 broken wiring tests, ship honest green`
- `dc6fa19 chore(ci): add GitHub Actions, triage 39 broken integration tests`

**Recommendation:** TEA should branch from `chore/api-ci-and-test-isolation` as `feat/37-13-encounter-gate-telemetry`. Reasons:
1. The CI + test-isolation fixes on that branch are precisely what TEA needs to run the integration suite cleanly. Branching from `develop` would re-expose the 39 broken wiring tests.
2. When 37-13 merges, it goes to `chore/api-ci-and-test-isolation`, which will then fast-forward into `develop` as a single landed train — no conflict risk.
3. Do not rebase `chore/api-ci-and-test-isolation` onto `develop` mid-story; it's a stable base for current work until Keith merges it.

## Key References

- **ADR-033** — Confrontation Engine & Resource Pools (`docs/adr/033-confrontation-engine-resource-pools.md`). `StructuredEncounter` replaced `CombatState`/`ChaseState`; all encounter types share the same beat + metric shape. The `beat: u32` counter is the signal for "mid-encounter."
- **ADR-031** — Game Watcher Semantic Telemetry (`docs/adr/031-game-watcher-semantic-telemetry.md`). Every subsystem decision must emit a structured span. The gate's silent branch is exactly the failure mode this ADR exists to prevent.
- **Existing reference pattern:** `encounter.player_beat_from_narrator_ignored` at `dispatch/mod.rs:1846` — the template for "narrator tried X, we rejected it" `ValidationWarning`.
- **OTEL test reference:** `crates/sidequest-server/src/otel_dice_spans_34_11_tests.rs` — `init_global_channel` / `subscribe_global` / `drain_events` pattern.
- **Encounter fixture reference:** `crates/sidequest-server/tests/integration/encounter_context_wiring_story_28_4_tests.rs`.

## Notes for TEA (RED Phase)

### Focus Areas
1. **No silent branches.** Every path through the gate when `result.confrontation.is_some()` must emit exactly one `WatcherEvent`. Tests should enumerate the cases and assert the event.
2. **Event field stability.** The five event names in AC2 become the contract the GM panel reads. Pick final strings now; Dev implements exactly those.
3. **Replacement integrity** (Case D) is the riskiest case — actors and per-actor state must come from the fresh snapshot, not the old encounter.
4. **Wiring test** must drive the gate from the real dispatch entry point, not a direct call to an extracted helper.

### Questions to Resolve in RED
- Does `StructuredEncounter` expose the "has any beat fired" signal as `beat > 0`, or is it a different field? Verify in `sidequest_game::encounter` and encode the right check in the test fixtures. If the correct signal is different, update AC wording and notify Dev before GREEN.
- Does the existing dispatch entry point hand TEA enough surface to populate a pre-existing encounter? If a new test helper is unavoidable, keep it in the test module — do not add production code just to make tests easier.

### Watch Out For
- **False-green from refactor-only extraction.** If Dev extracts the gate into a helper and tests only the helper, the wiring test is the safety net. Do not skip it.
- **Double-emission.** A replacement must emit exactly one event (`encounter.replaced_pre_beat`), not `encounter.created` + something else. Assert count, not just presence.
- **Lost `tracing::warn!`.** AC5 keeps the existing log line alongside the new watcher event. Do not let Dev delete the warn in favor of "we have OTEL now."

## Ready for TEA
Session file complete. Design decision logged. RED phase awaits test development on `feat/37-13-encounter-gate-telemetry` branched from `chore/api-ci-and-test-isolation`.
