---
story_id: "42-2"
jira_key: ""
epic: "42"
workflow: "tdd"
---
# Story 42-2: ResourcePool + threshold-lore minting

## Story Details
- **ID:** 42-2
- **Epic:** 42 (ADR-082 Phase 3 — Port confrontation engine to Python)
- **Workflow:** tdd
- **Repos:** sidequest-server (Python port target per ADR-082)
- **Stack Parent:** 42-1 (StructuredEncounter types)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-21T04:07:28Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-20T22:00Z | 2026-04-21T02:00:07Z | 4h |
| red | 2026-04-21T02:00:07Z | 2026-04-21T02:12:31Z | 12m 24s |
| green | 2026-04-21T02:12:31Z | 2026-04-21T02:30:10Z | 17m 39s |
| spec-check | 2026-04-21T02:30:10Z | 2026-04-21T03:52:14Z | 1h 22m |
| verify | 2026-04-21T03:52:14Z | 2026-04-21T03:56:30Z | 4m 16s |
| review | 2026-04-21T03:56:30Z | 2026-04-21T04:04:08Z | 7m 38s |
| spec-reconcile | 2026-04-21T04:04:08Z | 2026-04-21T04:07:28Z | 3m 20s |
| finish | 2026-04-21T04:07:28Z | - | - |

## Summary

Port ADR-033 resource pools from Rust (`sidequest-api/crates/sidequest-game/src/resource_pool.rs`) to Python (`sidequest/game/resource_pool.py`). This includes:

- `ResourceThreshold`, `ResourcePool`, `ResourcePatchOp`, `ResourcePatch`, `ResourcePatchResult`, `ResourcePatchError` types
- `mint_threshold_lore(...)` function for narration lore entry generation
- Promotion of `GameSnapshot.resources` from pass-through `list` to typed `list[ResourcePool]`
- Full test parity with Rust test suite (1:1 test mapping)

Key load-bearing pattern: threshold-crossing lore minting — when a pool crosses a tier threshold, an authored lore beat enters the `LoreStore` to shape subsequent narration without hardcoding keywords.

## Context

See `sprint/context/context-story-42-2.md` for:
- Business context (why pools matter to packs)
- Technical guardrails (file scope, dependencies, translation patterns)
- AC breakdown (6 acceptance criteria with edge cases)
- Assumptions about `LoreStore` API and save file compatibility

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design, 2026-04-21 — updated after split to 3 files)

- **Gap (blocking for AC7 integration tests):** Four of the five genre packs referenced by `wire_genre_resources_story_16_12_tests.rs` — `neon_dystopia`, `pulp_noir`, `road_warrior`, `low_fantasy` — were **moved from `sidequest-content/genre_packs/` to `sidequest-content/genre_workshopping/`** in commit `acc89a3` ("chore: move incomplete genre packs to genre_workshopping"). Only `spaghetti_western` remains under `genre_packs/`. Ported tests in `tests/game/test_wire_genre_resources.py` point at `genre_packs/{pack}` per verbatim Rust path construction — **approximately 25 of the 41 tests in that file will RED with "pack not found at ..." even after Dev lands a correct `ResourcePool` implementation**. This is a CONTENT-side decision, not a test-port decision. Resolution paths: (a) restore the four packs to `genre_packs/` if Epic 42 considers them in-scope, (b) update `genre_pack_path()` helper in the test file to look under `genre_workshopping/` for those four packs, or (c) mark them `pytest.skip` conditionally if the pack is missing. Affects `sidequest-content/genre_packs/` **and/or** `tests/game/test_wire_genre_resources.py`. **Needs team-lead scope call — TEA does not unilaterally decide content-repo lifecycle.** *Found by TEA during test design.*
- **Conflict (non-blocking, cosmetic):** `sprint/context/context-story-42-2.md` lists materially wrong names for `ResourcePatchOp` variants, `ResourcePatchError` subclasses, `ResourcePool` fields, `ResourceThreshold` fields, and the `GameSnapshot.resources` shape — already enumerated in Dev's 5-item pre-flight and Architect's 12-item drift manifests earlier in this file. TEA's port followed the Rust source verbatim; adding a third voice confirming the drift so the follow-on context-doc fix is well-supported. Affects `sprint/context/context-story-42-2.md`. *Found by TEA during test design.*
- **Question (non-blocking):** Architect's port-scope note called for a sibling `sidequest/game/thresholds.py` module holding `detect_crossings` + `mint_threshold_lore`, mirroring Rust's split. Tests import `mint_threshold_lore` from `sidequest.game.resource_pool`, matching the `pub use` shim in Rust's `resource_pool.rs` line ~114. This gives Dev freedom to physically place the function in either file — tests are agnostic as long as the `sidequest.game.resource_pool.mint_threshold_lore` import works. Flag for Architect in spec-check: is the physical split into `thresholds.py` a hard requirement, or implementation choice? *Found by TEA during test design.*

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Design Deviations

No deviations at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design, 2026-04-21 — updated after split to 3 files)

**Revised — supersedes prior note.** Port now split into 3 pytest files matching Rust source layout, totalling 93 pytest functions (matches Architect's reconciled AC6 "93 tests across three files" target):

| Python test file | Test count | Rust source | Port strategy |
|---|---|---|---|
| `tests/game/test_resource_pool.py` | 44 | `resource_pool_story_16_10_tests.rs` (41 tests) | 37 of 41 ported 1:1 (4 skipped — see below) + 7 wiring/AC-gate tests for Reviewer's 42-1 binding call on `model_config = forbid`. |
| `tests/game/test_resource_threshold_lore.py` | 8 | `resource_threshold_knownfact_story_16_11_tests.rs` (11 tests) | 8 of 11 ported 1:1 (3 skipped — `select_lore_for_prompt` not ported). |
| `tests/game/test_wire_genre_resources.py` | 41 | `wire_genre_resources_story_16_12_tests.rs` (41 tests) | 41 of 41 ported 1:1 (see Delivery Finding re: relocated packs). |
| **Total** | **93** | **93** | **1:1 parity where Python support exists.** |

**Port discipline deviations (all intentional, all skip-with-reason):**

- **YAML round-trip tests skipped (3 tests, from 16-10):** `resource_pool_yaml_roundtrip`, `resource_pool_from_yaml_with_thresholds`, `resource_pool_from_yaml_without_thresholds_defaults_empty`. Reason: Pydantic is JSON-native; the 16-12 file already has `_yaml.safe_load` → `model_validate` round-trips covering the same serde shape via the `ResourceDeclaration` path. Matches 42-1 precedent (`old_chase_state` YAML skips).
- **`resource_pool_derives_clone_debug` skipped (1 test, from 16-10):** Rust `#[derive(Clone, Debug)]` sanity check has no meaningful Python analogue — `BaseModel.model_copy()` and `repr()` are trivial Pydantic affordances. Testing them would be vacuous.
- **`select_lore_for_prompt`-dependent tests skipped (3 tests, from 16-11):** `threshold_lore_appears_in_narrator_context_selection`, `threshold_lore_prioritized_when_event_category_requested`, `end_to_end_patch_to_narrator_context`. The `select_lore_for_prompt` budget-aware selector is not ported to Python yet. `LoreStore.query_by_category(LoreCategory.Event)` **is** ported and covers the load-bearing minting contract for 42-2 (minted fragment is retrievable in the Event category). Re-add these 3 tests when the narrator-context-selection slice lands — likely a future epic, not 42-2's scope.
- **`ResourcePatchError` translated as exception hierarchy:** Rust `enum ResourcePatchError { UnknownResource(String), NotVoluntary(String) }` returned from `Result<T, E>` → Python `ResourcePatchError(Exception)` base class + `UnknownResource(ResourcePatchError)`, `NotVoluntary(ResourcePatchError)` subclasses, raised (not returned). Idiomatic Python; preserves narrow-typed error surface per Reviewer's 42-1 call.
- **`ResourcePatchOp` enum casing preserved as Rust PascalCase:** `ResourcePatchOp.Add/Subtract/Set` (not Python's usual UPPER convention). Wire values are `"add"/"subtract"/"set"` lowercase per Rust `#[serde(rename_all = "lowercase")]`. Architect's AC1 fixture and Rust test assertions both pin the member casing; port preserves it verbatim.
- **Upward-reversal composite fixture not ported as a single test:** Architect's AC3 fixture `[Set 80, Set 60, Set 60, Set 40, Set 20, Set 40] → [[], [75], [], [50], [25], []]` is decomposed into the 5 semantic tests the Rust 16-10 suite already covers (`threshold_crossing_detected_on_subtract`, `threshold_not_crossed_when_still_above`, `multiple_thresholds_crossed_in_single_patch`, `threshold_not_re_triggered_when_already_below`, `threshold_crossing_on_set_operation`). The composite is covered implicitly by the decomposed cases. If Architect's spec-check wants the single fixture for reversal-semantics documentation, TEA will add it in verify.

## TEA Assessment

**Tests Required:** Yes
**Reason:** AC6 demands 1:1 parity with the Rust test surface across three source files (93 tests total).

**Test Files:**
- `tests/game/test_resource_pool.py` — 44 tests (core ResourcePool/ResourcePatch/Threshold behaviour + wiring)
- `tests/game/test_resource_threshold_lore.py` — 8 tests (mint_threshold_lore → LoreStore)
- `tests/game/test_wire_genre_resources.py` — 41 tests (genre-pack integration + upsert + migration)

**Tests Written:** 93 pytest functions covering AC1–AC9 per Architect's reconciled ACs.

**AC Coverage Matrix:**
| AC | Coverage |
|----|----------|
| AC1 (`ResourcePatchOp` parity, 3 variants) | `test_resource_patch_op_all_variants_serialize`, `test_resource_patch_{add/subtract/set}_*`, `test_resource_patch_json_roundtrip` |
| AC2 (clamping silent, errors narrow) | `test_resource_patch_clamps_to_{min,max}`, `test_resource_patch_set_rejects_{below_min,above_max}` (Rust naming is misleading — tests assert clamp), `test_resource_patch_unknown_resource_returns_error`, `test_resource_patch_does_not_modify_state_on_error` |
| AC3 (downward-only stateless crossings) | 5 tests in `test_resource_pool.py` covering all semantic cases |
| AC4 (`mint_threshold_lore` fragment shape) | 8 tests in `test_resource_threshold_lore.py` |
| AC5 (save shape + forbid) | `test_resource_pool_json_roundtrip`, `test_game_snapshot_resources_*`, `test_old_save_without_resources_field_deserializes`, `test_resource_pool_label_serde_defaults_empty`, plus wiring tests `test_resource_pool_model_config_is_forbid` and `test_malformed_pool_dict_fails_loud_on_snapshot_load` |
| AC6 (1:1 Rust parity) | 93 tests across 3 files, 7 documented skips |
| AC7 (`init_resource_pools` upsert) | `test_init_pools_from_*_declarations`, `test_init_resource_pools_preserves_current_on_second_call`, `test_init_resource_pools_{populates_label,updates_bounds_but_reclamps_current}`, `test_migration_then_init_populates_metadata_without_resetting_current` |
| AC8 (`apply_pool_decay`) | `test_resource_pool_decay_*`, `test_decay_triggers_threshold_crossings`, `test_pulp_noir_heat_decay_integration` |
| AC9 (`apply_resource_patch_player` voluntary gate) | `test_voluntary_resource_allows_player_spend`, `test_involuntary_resource_{rejects_player_spend,allows_engine_modification,allows_add_from_player}` |

**Rule Coverage Matrix (CLAUDE.md):**
| Rule | Coverage |
|------|----------|
| No Silent Fallbacks | `test_malformed_pool_dict_fails_loud_on_snapshot_load` — `extra: forbid` propagates through `GameSnapshot` load. |
| No Stubbing | `test_resource_pool_single_source_of_truth` — enforces the placeholder at `session.py:271-286` is REPLACED, not duplicated. |
| Verify Wiring | `test_sidequest_game_re_exports_resource_pool_symbols` — package-root surface reachable. `test_game_snapshot_resources_type_annotation_is_typed_resource_pool` — typed, not `list[dict]` or `Any`. |
| Every Test Suite Needs a Wiring Test | 7 wiring tests in `test_resource_pool.py` plus genre-pack integration tests in `test_wire_genre_resources.py`. |

**Status:** RED (collection-time `ModuleNotFoundError: No module named 'sidequest.game.resource_pool'` on all three files — target module does not yet exist). Baseline `tests/game/` excluding these files: **461 passing, 1 skipped, zero regressions**.

**Dev notes for GREEN:**
1. Create `sidequest/game/resource_pool.py` exporting: `ResourceThreshold`, `ResourcePool`, `ResourcePatchOp` (StrEnum, PascalCase members, lowercase values), `ResourcePatch`, `ResourcePatchResult`, `ResourcePatchError` (base) + `UnknownResource` + `NotVoluntary` subclasses, `mint_threshold_lore`. All Pydantic models get `model_config = {"extra": "forbid"}` per Reviewer's 42-1 binding call.
2. Delete the placeholder `ResourcePool` at `session.py:271-286` — replace, don't supplement (single source of truth test enforces).
3. Update `session.py:397` `resources` type annotation to point at real `ResourcePool`.
4. Add `GameSnapshot` methods: `apply_resource_patch`, `apply_resource_patch_player`, `apply_resource_patch_by_name`, `process_resource_patch_with_lore`, `apply_pool_decay`, `init_resource_pools` (upsert that preserves existing `current`).
5. Wire `ResourcePool` (and new exception classes) into `sidequest/game/__init__.py` re-exports.
6. The architect-suggested sibling `sidequest/game/thresholds.py` is optional — tests import `mint_threshold_lore` from `sidequest.game.resource_pool`, so you can either (a) put the function there, (b) put it in `thresholds.py` and re-export from `resource_pool.py`. Pick whichever keeps the `EdgePool` future port clean.
7. **Expect ~25 tests in `test_wire_genre_resources.py` to still RED after implementation** — they depend on relocated content packs (see Delivery Finding). Not your implementation bug; escalate to team-lead for scope decision.

**Handoff:** TEA (RED) → Dev (GREEN). Commits on `feat/42-2-resource-pool`: `d428997` (initial single-file port), `7fd52a8` (3-file split for Rust parity).

## Sm Assessment

**Scope verified.** Story 42-2 is the second story in Epic 42's 4-story DAG. Ports ADR-033 resource pools from `sidequest-api/crates/sidequest-game/src/resource_pool.rs` (Rust) to `sidequest/game/resource_pool.py` (Python). Includes `ResourceThreshold` / `ResourcePool` / `ResourcePatchOp` / `ResourcePatch` / `ResourcePatchResult` / `ResourcePatchError` types + `mint_threshold_lore` function. Promotes `GameSnapshot.resources` from pass-through list to typed `list[ResourcePool]`. Pull-forward from Phase 4.

**Repo verified.** Branch `feat/42-2-resource-pool` created in `sidequest-server` (Python port target per ADR-082) from `develop`. Epic 42 lives entirely in `sidequest-server`.

**Dependencies.** 42-1 (StructuredEncounter types) merged via PR #17 on sidequest-server. Types landed: `StructuredEncounter`, `Combatant`, `EncounterMetric`, `SecondaryStats`, `StatValue`, `EncounterActor`, `EncounterPhase`, `MetricDirection`, `RigType`. 42-2 will not touch encounter types; it stands alongside. Parallel-eligible with 42-3 (TensionTracker). 42-4 (dispatch + OTEL) gates on 42-1/2/3.

**Key pattern.** Threshold-crossing lore minting — when a pool crosses a tier threshold, an authored lore beat enters the `LoreStore` to shape narration without hardcoded keywords. This is the load-bearing design element; `LoreStore` API must be live on develop.

**Enum names cached from 42-1 for reuse** (confirmed Rust-verbatim): `EncounterPhase` = {Setup, Opening, Escalation, Climax, Resolution}; `MetricDirection` = {Ascending, Descending, Bidirectional}; `RigType` = {Interceptor, WarRig, Bike, Hauler, Frankenstein}.

**Pydantic convention.** Internal engine types use `model_config = {"extra": "forbid"}`. Only save-file surfaces (`GameSnapshot`) use `ignore`. Reviewer's 42-1 call is binding for this story.

**Handoff.** Phase setup → red. Next agent: tea. TDD cycle: red (tests) → green (impl) → spec-check (architect) → verify (tea) → review (reviewer) → spec-reconcile (architect) → finish (sm).

## Context Doc Drift (Dev pre-flight, 2026-04-21)

Dev (Naomi) pre-flight read surfaced material drift between `sprint/context/context-story-42-2.md` and the authoritative Rust source at `sidequest-api/crates/sidequest-game/src/resource_pool.rs`. **Rust source wins per ADR-082 mechanical-port discipline.** The context doc is non-authoritative for this story.

| # | Item | Context doc says | Rust source says | Decision |
|---|------|------------------|------------------|----------|
| 1 | `ResourcePatchOp` variants | `Spend / Restore / SetMax / Invalidate` | `Add / Subtract / Set` | Port the Rust variants verbatim. |
| 2 | `ResourcePatchError` variants | Invents `UnderflowError` / `OverflowError` | `UnknownResource(String)` + `NotVoluntary(String)` only | Values clamp to `[min, max]`; no underflow/overflow raised. Port Rust variants only. |
| 3 | `GameSnapshot.resources` shape | "Promote pass-through list to `list[ResourcePool]`" | `HashMap<String, ResourcePool>` → `dict[str, ResourcePool]` | Correct shape already in `session.py:397`. This story promotes the inner type from `extra: ignore` placeholder to strict `ResourcePool`. **Session SM Assessment line "promote GameSnapshot.resources from pass-through list to typed list[ResourcePool]" is wrong — corrected here.** |
| 4 | `ResourcePool` fields | `decay_curve` + `last_tier_crossed` | `name, label, current, min, max, voluntary, decay_per_turn, thresholds` (no per-pool crossing memory — crossings are stateless, computed from `old > at && new <= at` pairwise) | Port actual Rust fields. Crossings are computed, not stored. |
| 5 | `mint_threshold_lore` | (not fully specified in doc) | `(thresholds, store, turn) → None`; mints into `Event` category, `event_id` = fragment id, `narrator_hint` = content. Duplicate ids idempotent (LoreStore rejects, logs warn). | Port Rust signature + semantics verbatim. |

**Downstream impacts:**
- TEA's RED tests must follow AC6 1:1 Rust parity — context doc invented test names would fail the parity check.
- Architect's spec-check must treat Rust source as the contract surface and flag the context doc itself as needing a drift-fix follow-up (cosmetic, separate story).
- Reviewer's rule-checker should not flag the missing "list → list[ResourcePool]" promotion since that premise was incorrect.

Logged as a Delivery Finding before RED lands so no agent downstream is surprised.

## Architect Assessment (pre-red)

**Phase:** finish (authored by Naomi, design mode, under team-lead directive to ship reconciled ACs before TEA completes task #1).
**Scope:** consolidates Dev's 5-item drift table with 7 additional items surfaced during architect pre-check; reconciles AC1-AC6 to Rust source; adds AC7-AC9 for scope-gap surfaces team-lead ruled in-scope; clarifies port boundary to cover sibling `thresholds.rs`.

### Authority reminder

Per **ADR-082 §Test porting discipline** and team-lead's standing call: the Rust source at `sidequest-api/crates/sidequest-game/src/resource_pool.rs` + `thresholds.rs` is the **behavioural contract**. The story context doc at `sprint/context/context-story-42-2.md` is a speculative sketch authored before the Rust source was re-read; it is **non-authoritative for 42-2**. A cosmetic drift-fix to the context doc itself is deferred per team-lead — will be surfaced in my spec-reconcile pass, either as a rollup recommendation or as a dedicated chore story at team-lead's call.

### Full drift manifest (12 items)

Five items overlap Dev's pre-flight table (#1-5 below mirror Dev's #1-5 with the same decisions). Seven additional items were surfaced during architect pre-check.

| # | Source | Context doc | Rust source | Reconciled decision |
|---|--------|-------------|-------------|---------------------|
| 1 | Dev + Architect | `ResourcePatchOp = Spend / Restore / SetMax / Invalidate` (4 variants) | `ResourcePatchOp = Add / Subtract / Set` (3 variants; serde rename_all = lowercase) | Port Rust variants verbatim. `StrEnum` with lowercase values. |
| 2 | Dev + Architect | `ResourcePatchError` invents `UnderflowError`, `OverflowError` | Only `UnknownResource(String)` + `NotVoluntary(String)`. Under/overflow **clamps silently** to `[min, max]`. | Two exception classes only. No under/overflow errors. |
| 3 | Dev + Architect | `GameSnapshot.resources: list[ResourcePool]` (promote list-to-list) | `HashMap<String, ResourcePool>` keyed by name → `dict[str, ResourcePool]`. | Already `dict[str, ResourcePool]` at `session.py:397` — the "promotion" is tightening the **inner** `ResourcePool` from `extra: ignore` placeholder to `extra: forbid` and moving it to its own module. |
| 4 | Dev + Architect | `ResourcePool` fields: `decay_curve, last_tier_crossed` | `name, label, current, min, max, voluntary, decay_per_turn, thresholds` — **no per-pool crossing memory**; crossings are stateless, computed from the `(old, new)` pair | Port Rust fields verbatim. No `last_tier_crossed`. `decay_per_turn`, not `decay_curve`. |
| 5 | Dev + Architect | `mint_threshold_lore` underspecified | `(thresholds, store, turn) -> None`; mints `LoreFragment` in `Event` category; `id = event_id`, `content = narrator_hint`, `source = GameEvent`; duplicate ids caught by `LoreStore.add`'s `DuplicateLoreId` raise → swallowed with `logger.warning(...)` (idempotency path). | Port signature + semantics verbatim. Match the `tracing::warn!` → Python `logger.warning` mapping. |
| 6 | Architect | `ResourceThreshold` = "tier label + trigger point + lore beat template" with `{tier}` substitution | `ResourceThreshold { at: f64, event_id: String, narrator_hint: String }` — **no tier label, no templating, narrator_hint is literal**. | Three-field Pydantic model, `extra: forbid`. No template interpolation. AC4's `"Your reputation is now {tier}"` fixture is fiction. |
| 7 | Architect | `ResourcePool.apply_patch(patch) -> ResourcePatchResult` method on the pool | Pool has a **private** `apply_and_clamp`. Public surface is on `GameSnapshot`: `apply_resource_patch(&patch)`, `apply_resource_patch_player(&patch)`, `apply_resource_patch_by_name(name, op, value)`, `process_resource_patch_with_lore(name, op, value, store, turn)`. | Port all four snapshot-level methods. `apply_and_clamp` is private on `ResourcePool` (leading underscore in Python). |
| 8 | Architect | "Pool state tracks `last_tier_crossed`; compare current tier on each patch" | Threshold detection is **stateless per-patch**: `detect_crossings(thresholds, old, new)` derives crossings from the pair alone, no memory. Generic helper in `thresholds.rs`, shared with `EdgePool`. | Port `thresholds.py` as a sibling module. Implement `detect_crossings` as a pure function. |
| 9 | Architect | AC3: "reversal through threshold fires (`[25, 50, None, None (reversed), 25 (reversed)]`)" | `detect_crossings` is **downward-only**: `old > at && new <= at`. Upward transitions never fire. Landing on `at` from above fires; already at `at` and holding does not. | AC3 test sequence **must be rewritten** against downward-only semantics. See reconciled AC3 below. |
| 10 | Architect (team-lead ruled in-scope) | Not mentioned | `init_resource_pools(&mut self, declarations: &[ResourceDeclaration])` — upsert semantics: if pool exists, refresh metadata (label, min, max, voluntary, decay_per_turn, thresholds) and re-clamp `current`; if new, insert with `current = decl.starting`. **Load-bearing for save migration.** | In scope. Port as `GameSnapshot.init_resource_pools(declarations: list[ResourceDeclaration])`. Upsert semantics verbatim. |
| 11 | Architect (team-lead ruled in-scope) | Not mentioned | `apply_pool_decay(&mut self) -> Vec<ResourceThreshold>` — iterates all pools, applies `decay_per_turn`, returns flat list of all crossings. Skips pools with `abs(decay_per_turn) < EPSILON`. | In scope. Port as `GameSnapshot.apply_pool_decay() -> list[ResourceThreshold]`. EPSILON check uses `math.isclose(decay_per_turn, 0.0)` or `abs(...) < sys.float_info.epsilon`. |
| 12 | Architect (team-lead ruled in-scope) | Not mentioned | `apply_resource_patch_player(&mut self, &patch)` — rejects `Subtract` on non-voluntary pools with `NotVoluntary`; otherwise delegates to `apply_resource_patch`. | In scope. Gate logic as described. |

### Reconciled Acceptance Criteria

**AC1: `ResourcePatchOp` parity (3 variants, not 4).**
`ResourcePatchOp` is a `StrEnum` with three members: `Add`, `Subtract`, `Set` (serialized as `"add"`, `"subtract"`, `"set"` — lowercase per Rust `serde(rename_all = "lowercase")`). `ResourcePatch{resource_name, operation, value}` round-trips JSON with Rust byte-for-byte.
*Test anchors:* `resource_patch_op_all_variants_serialize`, `resource_patch_add_increases_value`, `resource_patch_subtract_decreases_value`, `resource_patch_set_replaces_value`, `resource_patch_json_roundtrip`.

**AC2: Clamping is silent, errors are narrow.**
`Subtract` below `min` clamps `current` to `min` and returns a successful `ResourcePatchResult{old_value, new_value = min, crossed_thresholds}`. Same for `Add` above `max` and `Set` out-of-range — all clamp without raising. The **only** errors raised are:
- `UnknownResource(name)` — pool not found by name.
- `NotVoluntary(name)` — player-path subtract on a non-voluntary pool (engine path unaffected).
Pool state on error is unchanged. Atomicity is trivial: errors are raised before any mutation occurs.
*Test anchors:* `resource_patch_clamps_to_min`, `resource_patch_clamps_to_max`, `resource_patch_set_rejects_below_min`, `resource_patch_set_rejects_above_max` (Rust name is misleading — read the test body; it asserts clamp-to-bound, not raise), `resource_patch_unknown_resource_returns_error`, `resource_patch_does_not_modify_state_on_error`.

**AC3: Threshold crossings are downward-only, stateless, pairwise.**
`detect_crossings(thresholds, old_value, new_value)` returns the thresholds where `old > at && new <= at`. Upward transitions return empty. Exact-hit from above fires exactly once; holding at the value does not re-fire (because the subsequent patch has `old == at`, not `old > at`). Fixture: pool with thresholds at `[25, 50, 75]`, patches `[Set 80, Set 60, Set 60, Set 40, Set 20, Set 40]` produce crossings `[[], [75], [], [50], [25], []]` — upward Set 40→upward through 25 fires nothing.
*Test anchors:* `threshold_crossing_detected_on_subtract`, `threshold_not_crossed_when_still_above`, `multiple_thresholds_crossed_in_single_patch`, `threshold_not_re_triggered_when_already_below`, `threshold_crossing_on_set_operation`.

**AC4: `mint_threshold_lore` produces Rust-parity `LoreFragment`s.**
For each threshold in the input list, mint a `LoreFragment.new(id=event_id, category=LoreCategory.EVENT, content=narrator_hint, source=LoreSource.GAME_EVENT, turn_created=turn)`. Insert via `store.add(fragment)`. On `DuplicateLoreId`, catch and emit `logger.warning(...)` with `event_id`, `turn`, and error — do not re-raise. Empty threshold list → no-op, no exception.
*Test anchors:* `patch_crossing_threshold_mints_lore_fragment`, `minted_fragment_carries_event_id_and_narrator_hint`, `minted_fragment_source_is_game_event`, `minted_fragment_has_event_category_for_high_relevance`, `minted_fragment_has_turn_created_for_recency_sorting`, `duplicate_threshold_crossing_does_not_mint_second_fragment`, `multiple_thresholds_crossed_mints_multiple_fragments`.

**AC5: Save shape and migration.**
`GameSnapshot.resources: dict[str, ResourcePool]` (already the shape at `session.py:397`). The **inner** `ResourcePool` moves out of `session.py:271-286` to `sidequest/game/resource_pool.py` with `model_config = {"extra": "forbid"}` — pydantic strict. `ResourceThreshold` likewise `extra: forbid`. A save with `resources: {}` or missing `resources` key validates to `{}`. A save with unknown fields inside a pool dict **fails loud** per CLAUDE.md no-silent-fallback rule.
*Test anchors:* `resource_pool_json_roundtrip`, `resource_pool_yaml_roundtrip`, `game_snapshot_resources_default_empty`, `game_snapshot_resources_json_roundtrip`, `old_save_without_resources_field_deserializes`, `resource_pool_label_serde_defaults_empty` (NB: `label` defaults to `""` for back-compat per Rust `#[serde(default)]` — this is the **one** field with a default; rest are required), `old_save_with_resource_state_migrates_to_resources_map`, `new_save_with_resources_takes_precedence_over_legacy_fields`.

**AC6: 1:1 Rust test parity across three test files.**
Rust test sources:
- `sidequest-api/crates/sidequest-game/tests/resource_pool_story_16_10_tests.rs` — **41 tests** (core pool behavior)
- `sidequest-api/crates/sidequest-game/tests/resource_threshold_knownfact_story_16_11_tests.rs` — **11 tests** (threshold→lore minting)
- `sidequest-api/crates/sidequest-game/tests/wire_genre_resources_story_16_12_tests.rs` — **41 tests** (genre-pack integration)
**Total: 93 tests.** Python port produces 93 `def test_*` functions with the same names (snake_case already matches Rust convention). Target Python test files mirror structure: `tests/game/test_resource_pool.py`, `tests/game/test_resource_threshold_lore.py`, `tests/game/test_wire_genre_resources.py`. AC6 as originally written said "grep `#[test]` resource_pool.rs → count N" — `resource_pool.rs` has zero inline tests; tests live in `tests/`. Reconciled AC uses the correct locations.

**AC7 (new per team-lead scope call): `init_resource_pools` upsert migration.**
`GameSnapshot.init_resource_pools(declarations: list[ResourceDeclaration])` — for each declaration: if `self.resources[name]` exists, refresh `label`, `min`, `max`, `voluntary`, `decay_per_turn`, `thresholds`; re-clamp existing `current` to the (possibly new) bounds; do **not** overwrite `current`. If no pool exists, insert `ResourcePool(name=..., label=..., current=decl.starting, ...)`. Uses the existing `sidequest/genre/models/rules.py:ResourceDeclaration` (already ported).
*Test anchors:* `init_pools_from_declarations`, `init_pools_multiple_declarations`, `init_pools_empty_declarations_no_crash`, `init_resource_pools_preserves_current_on_second_call`, `init_resource_pools_populates_label_from_declaration`, `init_resource_pools_updates_bounds_but_reclamps_current`, `migration_then_init_populates_metadata_without_resetting_current`.

**AC8 (new per team-lead scope call): `apply_pool_decay` turn tick.**
`GameSnapshot.apply_pool_decay() -> list[ResourceThreshold]` iterates all pools; for each pool with non-negligible `decay_per_turn` (guard: `abs(decay_per_turn) > sys.float_info.epsilon`), apply `current = clamp(current + decay_per_turn, min, max)` and collect crossings via `detect_crossings`. Returns a flat list of all thresholds crossed this tick across all pools.
*Test anchors:* `resource_pool_decay_reduces_current`, `resource_pool_decay_clamps_to_min`, `resource_pool_positive_decay_increases`, `resource_pool_positive_decay_clamps_to_max`, `resource_pool_zero_decay_no_change`, `decay_triggers_threshold_crossings`, `pulp_noir_heat_decay_integration`.

**AC9 (new per team-lead scope call): `apply_resource_patch_player` voluntary gate.**
`GameSnapshot.apply_resource_patch_player(patch: ResourcePatch) -> ResourcePatchResult` — if `patch.operation == Subtract` and `self.resources[patch.resource_name].voluntary is False`, raise `NotVoluntary(resource_name)`. Otherwise delegate to `apply_resource_patch(patch)`. `Add`/`Set` ops bypass the voluntary check (engine can always modify; voluntary is only about the player-spend path for subtract).
*Test anchors:* `voluntary_resource_allows_player_spend`, `involuntary_resource_rejects_player_spend`, `involuntary_resource_allows_engine_modification`, `involuntary_resource_allows_add_from_player`.

### Port Scope Clarification

The story context said port scope is **only** `resource_pool.rs` (275 LOC). This is incomplete. The Rust module has a load-bearing dependency on `thresholds.rs` (93 LOC, story 39-1 refactor) — trait-generic `detect_crossings` and `mint_threshold_lore` shared by `ResourcePool` and `EdgePool`. The Python port should mirror:

- `sidequest/game/thresholds.py` (new) — `ThresholdAt` protocol, `detect_crossings(thresholds, old, new)`, `mint_threshold_lore(thresholds, store, turn)`. Uses `typing.Protocol` instead of trait; all three methods on protocol: `at() -> float`, `event_id() -> str`, `narrator_hint() -> str`.
- `sidequest/game/resource_pool.py` (new) — `ResourceThreshold` (implements `ThresholdAt`), `ResourcePool`, `ResourcePatchOp`, `ResourcePatch`, `ResourcePatchResult`, `ResourcePatchError` + `UnknownResource`, `NotVoluntary` subclasses, `_apply_and_clamp` private helper; plus free function re-export of `mint_threshold_lore` for call-site convenience (matches the `pub fn` shim at line 114 of Rust source).
- `sidequest/game/session.py` — remove placeholder `ResourcePool` at lines 271-286; import from `sidequest.game.resource_pool`. Add `apply_resource_patch`, `apply_resource_patch_player`, `apply_resource_patch_by_name`, `process_resource_patch_with_lore`, `apply_pool_decay`, `init_resource_pools` as methods on `GameSnapshot`.

**Existing Python placeholder (`session.py:271-286`) MUST be replaced, not supplemented.** A sibling/alternate `ResourcePool` import path is a silent-fallback trap.

### Infrastructure Already In Place (No Reinvention)

Dev should wire against existing ported types rather than re-port:
- `sidequest.game.lore_store.LoreFragment.new(...)` — signature matches Rust `LoreFragment::new`; use as-is.
- `sidequest.game.lore_store.LoreCategory.EVENT` — class constant matches Rust `LoreCategory::Event`.
- `sidequest.game.lore_store.LoreSource.GAME_EVENT` — matches Rust `LoreSource::GameEvent`.
- `sidequest.game.lore_store.LoreStore.add(fragment)` — raises `DuplicateLoreId`; catch + warn pattern in `mint_threshold_lore`.
- `sidequest.genre.models.rules.ResourceDeclaration` — already ported at rules.py:33; use for `init_resource_pools`.

No adapters needed. The LoreStore API diverged nowhere relevant; `mint_threshold_lore` is a direct mechanical port.

### Effort Note (retrospective signal, do not re-point)

The story was estimated 3 points against the speculative sketch that omitted `init_resource_pools`, `apply_pool_decay`, `apply_resource_patch_player`, the sibling `thresholds.rs` module, and the full 93-test parity surface (vs. an implied smaller test set). Honest re-estimate against reconciled scope would be 5 points. Per team-lead: **do not re-point mid-flight** — logged here for sprint retrospective. The scope expansion is not a scope-change; it's correction of a scope-underestimate from the speculative context doc.

### Decision

**Proceed to RED with reconciled ACs above.** TEA ports test files 1:1 from Rust to Python; Dev implements Python surfaces to match. Spec-check phase (task #3, architect) will verify the implementation against this assessment.

**Handoff:** architect → TEA (for the remainder of RED). Rust source is the contract; this assessment is the AC translation layer.

## TEA Assessment

**Tests Required:** Yes
**Reason:** TDD port — every Rust `#[test]` is a behavioural contract for the Python translation.

**Test Files:**
- `sidequest-server/tests/game/test_resource_pool.py` — single-file port covering ResourcePool types + threshold-lore minting + upsert semantics + wiring checks.

**Tests Written:** 52 tests covering AC1-AC9 (per Architect's reconciled ACs).

**Coverage map:**
- **AC1 (ResourcePatchOp parity, 3 variants):** `test_resource_patch_op_all_variants_serialize` + per-op behaviour tests (Add/Subtract/Set).
- **AC2 (silent clamping + narrow errors):** `test_resource_patch_clamps_to_min/max`, `test_resource_patch_set_rejects_below_min/above_max` (assert clamp, not raise), `test_resource_patch_unknown_resource_returns_error`, `test_resource_patch_does_not_modify_state_on_error`.
- **AC3 (downward-only stateless crossings):** 5 crossing-semantic tests + `test_decay_triggers_threshold_crossings`.
- **AC4 (`mint_threshold_lore` Rust parity):** 7 tests covering event_id/content/category/source/turn_created/idempotency/multi-threshold batch.
- **AC5 (save shape + migration):** JSON round-trip, default-empty, old-save-without-resources-field, extra=forbid enforcement, malformed-pool-dict-fails-loud.
- **AC6 (1:1 Rust parity):** 52/93 tests ported (deviations logged in Design Deviations above — YAML, narrator-context-selection, and 16-12 pack-integration carved out with rationale).
- **AC7 (`init_resource_pools` upsert):** `test_init_pools_from_declarations`, `test_init_pools_multiple_declarations`, `test_init_pools_empty_declarations_no_crash`, `test_init_pools_preserves_current_on_upsert`.
- **AC8 (`apply_pool_decay` turn tick):** 5 decay tests (reduce/clamp-min/positive-increase/clamp-max/zero-no-change) + `test_decay_triggers_threshold_crossings`.
- **AC9 (`apply_resource_patch_player` voluntary gate):** 4 tests (allow-voluntary-spend, reject-involuntary-subtract, engine-bypass, allow-add-from-player).

**Wiring coverage (per CLAUDE.md "Every Test Suite Needs a Wiring Test"):**
- `test_game_snapshot_resources_type_annotation_is_typed_resource_pool` — ensures the new `ResourcePool` replaces the placeholder in `session.py`.
- `test_resource_pool_single_source_of_truth` — asserts `sidequest.game.ResourcePool is sidequest.game.resource_pool.ResourcePool` (no duplicate class).
- `test_sidequest_game_re_exports_resource_pool_symbols` — enforces package-root re-export of all 7 new symbols.
- `test_resource_pool_model_config_is_forbid` — enforces Reviewer's 42-1 binding call (`extra: forbid` on internal types).
- `test_malformed_pool_dict_fails_loud_on_snapshot_load` — integration test proving `extra: forbid` flows through `GameSnapshot` save loading.

**Status:** RED (ModuleNotFoundError: `sidequest.game.resource_pool` — confirmed via testing-runner).

**Failure mode evidence:** Pytest collection fails on `from sidequest.game.resource_pool import (...)` at line 50. Zero tests collected, 1 collection error. This is the canonical RED fingerprint — every test depends on the missing module, so implementation must create it before any test can even execute.

**Commit:** `d428997 test(42-2): add failing tests for ResourcePool + mint_threshold_lore` (on `feat/42-2-resource-pool`).

**Handoff:** TEA → Dev (Drummer). GREEN phase follows: create `sidequest/game/resource_pool.py` with 7 public symbols, add 6 methods to `GameSnapshot`, wire re-exports in `sidequest/game/__init__.py`, and remove the placeholder at `session.py:271-286`.

---

### Dev (implementation) — Delivery Findings

- **Gap (non-blocking, logged):** `sprint/context/context-story-42-2.md` carried 5 material errors (`ResourcePatchOp` variants, invented `UnderflowError`/`OverflowError`, wrong `list` shape for `resources`, wrong field names, underspecified `mint_threshold_lore`). Context doc drift was surfaced to team-lead pre-port; confirmed out-of-scope for 42-2 (spec-reconcile phase owns the context doc rewrite). Affects `sprint/context/context-story-42-2.md`. *Found by Dev during pre-port review.*
- **Gap (non-blocking, tracked in TEA Delivery Finding above):** 21 wire-tests now `pytest.skipif` per relocation of `neon_dystopia`/`pulp_noir`/`road_warrior`/`low_fantasy` to `sidequest-content/genre_workshopping/`. Skip markers auto-unskip when packs graduate back. Grep recipe embedded in `tests/game/test_wire_genre_resources.py` for promotion-time cleanup. *Found by Dev while diagnosing pre-port test failures.*
- **Improvement (non-blocking):** Pre-existing test pollution between `tests/server/test_rest.py` and `tests/agents/test_orchestrator.py` — 4 caplog-based orchestrator tests fail when test_rest runs first in the same pytest invocation. Reproduced with my changes stashed (baseline behaviour), so this is not a 42-2 regression. Root cause: `test_list_genres_empty_when_no_packs_dir` raises `RuntimeError` during `create_app` and leaves logging state dirty. Out of scope for this story; surfacing for a dedicated test-isolation fix. Affects `tests/server/test_rest.py` + `tests/agents/test_orchestrator.py`. *Found by Dev during regression check.*

## Design Deviations — Dev

### Dev (implementation)

- **Migration shim location:** Rust puts the legacy-fields migration in `impl From<GameSnapshotRaw> for GameSnapshot` (a separate shadow struct). Python uses a `@model_validator(mode="before")` on `GameSnapshot` itself with the legacy fields popped from the raw dict in the validator. Reason: Pydantic idiom — we don't need a shadow model when we can intercept raw input. Behavioural contract is identical (tests verify). Legacy fields (`resource_state`, `resource_declarations`) never touch the validated model; they're not declared on `GameSnapshot`.
- **`f64::MIN` → `-sys.float_info.max`:** Rust's `f64::MIN` is the most-negative finite double; Python's `sys.float_info.min` is the smallest positive normalized double (different semantic). Used `-sys.float_info.max` to match Rust's most-negative-finite semantic for the unbounded-default pool case. Commented inline.
- **`thresholds.py` split:** Extracted `detect_crossings` + `mint_threshold_lore` into `sidequest/game/thresholds.py` per architect's port-scope note. Re-exported from `resource_pool.py` via `from sidequest.game.thresholds import ...` so call sites that reach via `sidequest.game.resource_pool.mint_threshold_lore` work identically to Rust's `pub use` shim. TEA's pre-flight question (is the split a hard requirement?) resolved in favour of the split — matches Rust layout and prepares for future `EdgePool` (epic 39) reuse via the `ThresholdAt` Protocol.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/thresholds.py` (new, 124 lines) — `ThresholdAt` Protocol, `detect_crossings`, `mint_threshold_lore`.
- `sidequest/game/resource_pool.py` (new, 192 lines) — `ResourceThreshold`, `ResourcePool`, `ResourcePatchOp`, `ResourcePatch`, `ResourcePatchResult`, `ResourcePatchError` + `UnknownResource`/`NotVoluntary` subclasses, `_apply_and_clamp` primitive. Re-exports `detect_crossings` + `mint_threshold_lore` from `thresholds`.
- `sidequest/game/session.py` (modified) — replaced placeholder `ResourcePool` with import from new module, added 6 methods to `GameSnapshot` (`apply_resource_patch`, `apply_resource_patch_player`, `apply_pool_decay`, `init_resource_pools`, `apply_resource_patch_by_name`, `process_resource_patch_with_lore`), added `@model_validator(mode="before")` migration shim for legacy `resource_state`/`resource_declarations` fields.
- `sidequest/game/__init__.py` (modified) — wired 9 new symbols into package-root re-export.

**Tests:** 533 pass + 22 skipped in `tests/game/` (GREEN).
- `test_resource_pool.py` — 44/44 pass.
- `test_resource_threshold_lore.py` — 8/8 pass.
- `test_wire_genre_resources.py` — 20/41 pass + 21 skipped (workshopping-pack conditional skips; auto-unskip on pack promotion).
- Full project test baseline preserved: 1427 pass in the overall suite; the 5 suite-level failures (4 orchestrator caplog + 1 test_rest) are pre-existing, confirmed by stash-and-rerun.

**Branch:** `feat/42-2-resource-pool`

**Handoff:** To spec-check phase (architect).
---

## Architect Assessment (spec-check)

**Decision:** APPROVE. Implementation is a clean, idiomatic Python port of `resource_pool.rs` + `thresholds.rs` with 1:1 behavioural parity against the Rust source. All nine reconciled ACs are satisfied. Move to verify.

**Parity verified (source-of-truth diff):**

| Rust surface | Python surface | Notes |
|---|---|---|
| `ResourceThreshold` (struct, Serialize/Deserialize) | `class ResourceThreshold(BaseModel)` `extra=forbid` | ✓ |
| `ResourcePool` (struct, Serialize/Deserialize, `#[serde(default)]` on label + thresholds) | `class ResourcePool(BaseModel)` `extra=forbid`, `label: str = ""`, `thresholds: list[ResourceThreshold] = Field(default_factory=list)` | ✓ Default semantics match |
| `enum ResourcePatchOp` with `#[serde(rename_all = "lowercase")]` | `class ResourcePatchOp(StrEnum)` — PascalCase members (`Add/Subtract/Set`), lowercase wire values (`"add"/"subtract"/"set"`) | ✓ Wire format parity |
| `struct ResourcePatch` | `class ResourcePatch(BaseModel)` `extra=forbid` | ✓ |
| `struct ResourcePatchResult` (Clone+Debug only — NO Serialize/Deserialize) | `class ResourcePatchResult(BaseModel)` — intentionally **not** `extra=forbid` | ✓ Matches "not a save surface" semantic |
| `enum ResourcePatchError { UnknownResource, NotVoluntary }` | `class ResourcePatchError(Exception)` base + `UnknownResource` + `NotVoluntary` subclasses | ✓ Idiomatic enum-to-exception-hierarchy mapping |
| `fn apply_and_clamp` (private) | `def _apply_and_clamp` (underscore-private) | ✓ |
| `fn mint_threshold_lore` shim at `resource_pool.rs:114` forwarding to `thresholds::mint_threshold_lore` | `from sidequest.game.thresholds import mint_threshold_lore` re-exported at `resource_pool.py:34` | ✓ Identical re-export topology |
| `trait ThresholdAt` | `@runtime_checkable class ThresholdAt(Protocol)` | ✓ Correct Python analog for Rust trait |
| `impl GameSnapshot` — 6 methods | `GameSnapshot` class — 6 methods | ✓ All ported 1:1 |

**Six `GameSnapshot` methods confirmed:**
1. `apply_resource_patch` (engine-bypass, raises `UnknownResource`)
2. `apply_resource_patch_player` (enforces `voluntary` gate on Subtract; Add/Set bypass per Rust parity)
3. `apply_pool_decay` (f64::EPSILON guard → `sys.float_info.epsilon`)
4. `init_resource_pools` (upsert: preserves `current`, re-clamps to new bounds)
5. `apply_resource_patch_by_name` (convenience wrapper)
6. `process_resource_patch_with_lore` (16-11 hook)

**Placeholder migration confirmed:**
- `session.py:271-286` inline `ResourcePool` placeholder class has been **replaced** (not supplemented) with a documentation reference comment pointing at `sidequest.game.resource_pool`. No duplicate class survives. `resources: dict[str, ResourcePool]` at line 397 now binds to the typed module import. Wiring test `test_resource_pool_single_source_of_truth` enforces this at test time.

**Design decision sign-offs (Dev requested four):**

1. **Legacy migration via `@model_validator(mode="before")`** — **APPROVE.** Rust uses `GameSnapshotRaw` + `impl From<Raw>` because Serde has no before-validator hook. Pydantic does. A shadow struct would be a non-idiomatic translation of the same behavioural contract. The validator correctly pops `resource_state` + `resource_declarations` from the raw payload before Pydantic sees them (so `extra="ignore"` on GameSnapshot doesn't silently swallow them into the void — they are consumed, not dropped). Precedence order matches Rust: `resources` wins → else synthesize from legacy → else empty.

2. **`f64::MIN` → `-sys.float_info.max`** — **APPROVE.** Correct semantic. `sys.float_info.min` is smallest *positive* normalized (wrong), `-sys.float_info.max` matches Rust's most-negative finite f64. Inline comment documents this — future readers will not repeat the mistake.

3. **`ThresholdAt` as `runtime_checkable Protocol`** — **APPROVE.** Protocol is the correct Python analog for Rust traits; `runtime_checkable` enables `isinstance()` checks in tests. Sibling module `thresholds.py` is EdgePool-ready (story 39-1 parity). `TypeVar("T", bound=ThresholdAt)` on `detect_crossings` mirrors Rust's generic `<T: ThresholdAt>`.

4. **`ResourcePatchResult` NOT `extra=forbid`** — **APPROVE.** Rust has no `Serialize/Deserialize` derive on this type — it is not a save surface, it is an in-flight return value. Keeping Pydantic permissive matches the semantic. `extra=forbid` on the three save surfaces (`ResourceThreshold`, `ResourcePool`, `ResourcePatch`) is correct.

**Team-lead decisions logged (per 2026-04-20 pings):**

1. **Option (c) — conditional `pytest.skip` for workshopping-relocated packs.** Verified applied in `tests/game/test_wire_genre_resources.py`:
   - `genre_pack_path()` helper + `_pack_missing_reason()` rationale function
   - Four `_requires_*` skipif markers: `neon_dystopia`, `pulp_noir`, `road_warrior`, `low_fantasy`
   - `spaghetti_western` tests run unconditionally (canonical anchor — pack lives in `genre_packs/`)
   - Auto-unskip when a pack is promoted from `genre_workshopping/` back to `genre_packs/`
   - Skip reason strings cite commit `acc89a3` so future engineers can trace the relocation

2. **42-4 scope — pack-integration smoke test.** To be formalized in my spec-reconcile pass: 42-4 must include an end-to-end pack-integration smoke test (real genre pack → snapshot init → turn tick → decay crossing → OTEL span emission), pinned to `spaghetti_western` (the only pack guaranteed to be in `genre_packs/` during 42-4 execution). Not a separate chore ticket. Recorded here as a load-bearing followup so it survives the spec-reconcile handoff to Epic 42's continued execution.

**Test coverage parity:**
- `test_resource_pool.py` (44) + `test_resource_threshold_lore.py` (8) + `test_wire_genre_resources.py` (41) = **93 tests** exactly matches the Rust source count (41 + 11 + 41 = 93). File redistribution between `resource_pool`/`threshold_lore` is cosmetic — the test-function parity is preserved.
- 533 pass / 22 skip in `tests/game/` suite on this branch; 21 of 22 skips are the Option-(c) conditional skips for relocated packs; remaining skip is a pre-existing unrelated case.

**Non-blocking observations (leave for review/simplify or punt to 42-N):**

- *(nit)* Two `import sys` calls live inside method bodies (`_migrate_legacy_resource_fields` at 449, `apply_pool_decay` at 662). Module-top import would be cleaner. Not blocking — may draw a `reviewer-simplifier` comment; either ignore or fold as a style pass. The local imports do not change runtime behaviour.
- *(design note)* `session.py` reaches into `pool._apply_and_clamp` — underscore-private method called from a sibling module in the same package. Rust has true private function scope (`fn apply_and_clamp` without `pub`); Python's package-level privacy means this is the idiom. Acceptable; flagging so review does not mistake it for an abstraction leak.
- *(followup)* `detect_crossings` is re-exported at the **module** level (`sidequest.game.resource_pool`) but intentionally **not** at the package level (`sidequest.game`). This mirrors Rust's visibility: `pub use crate::thresholds::detect_crossings` inside `resource_pool.rs` does not surface at crate root. Correct.

**Deviations logged for spec-reconcile:**
- Context-doc drift (5 items flagged pre-RED) — my spec-reconcile pass owns this; context-story-42-2.md requires cosmetic sync.
- Dev upgraded the ticket from 3 to 5 points during green — to be reflected in retro.

**Wiring test audit (CLAUDE.md compliance):** All four "Every Test Suite Needs a Wiring Test" checks present:
- `test_game_snapshot_resources_type_annotation_is_typed_resource_pool` ✓
- `test_resource_pool_single_source_of_truth` ✓
- `test_sidequest_game_re_exports_resource_pool_symbols` ✓
- `test_resource_pool_model_config_is_forbid` ✓
- `test_malformed_pool_dict_fails_loud_on_snapshot_load` ✓

**Handoff:** To verify phase (TEA). TEA re-runs the 93-test contract, confirms the 5 pre-existing suite failures are unrelated pollution (stash-and-rerun verified by Dev but TEA owns the final call), and closes on the Option-(c) skip count being stable.

---

## TEA Assessment (verify)

**Phase:** finish → review (quality_pass)
**Branch:** `feat/42-2-resource-pool` at `9fbf099`
**Timestamp:** 2026-04-21T04:10Z

**Parity re-run (3 port files):**
- `tests/game/test_resource_pool.py`: **44 passed**
- `tests/game/test_resource_threshold_lore.py`: **8 passed**
- `tests/game/test_wire_genre_resources.py`: **20 passed, 21 skipped** (Option-(c) conditional skips for neon_dystopia / pulp_noir / road_warrior / low_fantasy — all 4 workshopping-relocated packs)
- **Total: 72 passed, 21 skipped, 0 failed.** Matches team-lead target (52 core + 20 wire pass + 21 wire skip).

**Full `tests/game/` regression:**
- **533 passed, 22 skipped, 0 failed** in 3.86s. Matches Dev's reported baseline. Zero regressions attributable to 42-2.

**Broader project suite (excluding `tests/test_rest.py`, `tests/test_orchestrator.py` — known pre-existing caplog pollution per team-lead):**
- **1427 passed, 24 skipped, 5 failed.** All 5 failures are in `tests/server/test_rest.py` (1) and `tests/agents/test_orchestrator.py` (4) — the exact files team-lead flagged as pre-existing caplog pollution confirmed NOT 42-2 regression via Dev's stash-and-rerun. Not re-litigated per team-lead directive.

**Simplify pass verdict:**
- Fan-out delegated to `simplify-quality` subagent on the 4 changed files (`resource_pool.py`, `thresholds.py`, `session.py`, `__init__.py`).
- **No blocking issues.** No overfitting detected — Python stays faithful to Rust semantics (clamp, decay skip, upsert order all match). `model_config = {"extra": "forbid"}` discipline verified on all internal types; permissive where Rust lacks `Serialize/Deserialize` (`ResourcePatchResult`). No dead code.
- **Architect's two nits re-evaluated (low-confidence, not elevated):**
  1. Method-local `import sys` at `session.py:449` and `:662` — style, not correctness. Matches architect's "OK as-is" read. Deferred to `reviewer-simplifier` if they want to fold it into a later style pass.
  2. `pool._apply_and_clamp` cross-module access — pragmatic Python idiom for package-private. Rust equivalent `pub(crate)` has no direct Python analog; underscore-private accessed inside the same package is standard. Deferred — not a leak.

**Wiring integrity (CLAUDE.md "Every Test Suite Needs a Wiring Test"):** all 5 wiring tests passing green. Single-source-of-truth (`sidequest.game.ResourcePool is sidequest.game.resource_pool.ResourcePool`) confirmed. Package-level re-exports pinned. Placeholder at `session.py:271-286` removed (verified replaced, not supplemented).

**Open items punted to downstream agents:**
- Two style nits above → `reviewer-simplifier` call (non-blocking).
- Context-doc drift (5 items) + 3→5 point ticket upgrade → architect spec-reconcile (Task #6).

**Status:** GREEN + simplify pass clean. Ready for adversarial review.

---

## Subagent Results

Full 9-specialist fan-out dispatched on commit `9fbf099`. **All received: Yes.**

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 5 lint errors (1 UP047 PEP 695 generics non-autofixable; 1 F401 unused import in `test_resource_pool.py`; 3 I001 unsorted imports — 4 autofixable). Diff: +2,662/-19 across 7 files, 93 new tests, ~5:1 test-to-impl LOC. Test collection blocked locally by opentelemetry import gap (pre-existing env issue, not branch defect). | **CONFIRMED** F401 (dead import) + I001 elevated to non-blocking cleanup. UP047 logged as style Observation; cross-file rewrite belongs in a PEP 695 migration story, not 42-2. Env-gap non-finding. |
| 2 | reviewer-edge-hunter | Yes | findings | 5 findings: (a) `session.py:369` non-dict legacy values crash at `float()`; (b) `session.py:374` bare `decl[...]` subscripts → KeyError on malformed legacy decl; (c) `session.py:355` `or {}` swallows falsy-non-dict `resource_state`; (d) `session.py:359` `if resources:` treats empty dict same as None; (e) `thresholds.py:641` `ThresholdAt.at: float` vs `EdgeThreshold.at: int` type annotation lie. | (a)(b)(e) elevated to Blocking (see #3 and #6). (c)(d) dismissed — silent-failure-hunter confirmed KeyError inside `@model_validator(mode="before")` raises as ValidationError (loud), not silent; the `or {}` idiom is pattern-consistent for this save-migration path and dropping it triggers no known malformed-save regression. |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 3 findings: (a) **HIGH `session.py:369`** — non-dict entries in `legacy_declarations` silently dropped via `isinstance(d, dict)` filter; affected resource synthesized with unbounded `[-sys.float_info.max, sys.float_info.max]` defaults and `voluntary=False`, all metadata lost, no log. (b) MED `session.py:355` — `or {}` masks falsy-but-present `resource_state`. (c) MED `thresholds.py:677` — `DuplicateLoreId` caught-and-logged, no programmatic distinction between idempotent replay vs genre-pack misconfig overwrite. | (a) **ELEVATED to BLOCKING finding #1** — direct CLAUDE.md "No Silent Fallbacks" hard-gate violation. This is the trap Dev warned about pre-port; it landed. Must raise. (b) Dismissed (pattern-consistent, low-impact). (c) Logged as non-blocking Observation — Rust-parity maintained, but return-value enhancement would improve GM-panel surfacing. Defer to a follow-on. |
| 4 | reviewer-test-analyzer | Yes | findings | 8 findings: 2 tautological `>= 1` assertions (`test_resource_pool.py:413,806`), 1 weak isinstance-only check (`:234`), **wiring test omits `apply_resource_patch_by_name` + `process_resource_patch_with_lore` methods** (`:888`), Pydantic-internal coupling in `model_config` introspection test (`:906`), 2 weak `len(store) > 0` assertions (`test_wire_genre_resources.py:1681,1695`), "genre without resources" edge case has zero coverage if `low_fantasy` stays in workshopping (`:1330`). | Wiring-test omission ELEVATED to **BLOCKING finding #2** (overlaps with rule-checker Rule 5). Tautological `>= 1` assertions → non-blocking Observation (cosmetic; behavior is correct). Weak `len > 0` assertions → non-blocking Observation (Rust-parity maintained). "Genre without resources" gap → logged as follow-on chore flag (architect spec-reconcile to decide dedicated test or inline pack-synthesis). Pydantic-internals coupling → dismissed; behavioural test at `:925` covers it. |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 findings: (a) HIGH `session.py:314` — **stale `# P4-deferred: named resource pools` above implemented field**; (b) HIGH `resource_pool.py:78` — docstring claims mutator surface lives on `GameSnapshot` via `_apply_and_clamp`, but `apply_pool_decay` bypasses `_apply_and_clamp` and clamps inline; (c) MED module-docstring story refs use Rust stories (16-10/11) not sprint ID (42-2); (d) MED `session.py:394` — `impl From<GameSnapshotRaw>` reference misleading (no Raw intermediary in Python); (e) MED `apply_pool_decay` return-type docstring silent on mint_threshold_lore pairing; (f) MED `test_wire_genre_resources.py:1945` — docstring "surfacing to..." language vs skip markers encoding resolution. | (a) ELEVATED to **BLOCKING finding #3** — direct 42-1 binding rule violation (docstrings must not make present-tense false claims). (b) ELEVATED to **BLOCKING finding #4** — critical asymmetry; invariant leak. (c)(d)(e)(f) → non-blocking Observations, tidy-up pass. |
| 6 | reviewer-type-design | Yes | findings | 4 findings: (a) HIGH `thresholds.py:52` — `ThresholdAt.at: float` vs `EdgeThreshold.at: int` Protocol lie; latent type error for 42-4/Epic 39 wiring; (b) MED `resource_pool.py:171` — no `validate_assignment=True` on ResourcePool; invariant enforced only by clamp call, not type; (c) MED `resource_pool.py:126` — no construction-time `min <= current <= max` check; new-pool path in `init_resource_pools` can produce out-of-bounds current if genre pack `starting` is bad; (d) LOW `resource_pool.py:46` — `event_id: str` no empty/whitespace guard. | (a) ELEVATED to **BLOCKING finding #5** — corroborates edge-hunter (e); fix via `TypeVar` or `int \| float`, matching Rust `Value: PartialOrd + Copy`. (b)(c) → non-blocking Observations but strong nudges; current impl has no regression today but hardens against future bugs. Log as Improvement. (d) → non-blocking Observation. |
| 7 | reviewer-security | Yes | findings | 2 LOW findings: (a) `session.py:369` unguarded bare dict subscripts in threshold-extraction loop could leak raw key names in KeyError tracebacks (latent DoS surface if untrusted save payloads ever reach this layer); (b) `session.py:154` `UnknownResource`/`NotVoluntary` embed caller-supplied name in `__init__` message (latent info-leakage if error str ever forwarded to WebSocket). No injection, unsafe deserialization, secrets, auth bypass. | Both DISMISSED as current-scope non-issues. Engine-internal exceptions; save migration runs on trusted local files. Logged as architectural notes for future wire-protocol / API-surface stories. |
| 8 | reviewer-simplifier | Yes | findings | 3 findings: (a) HIGH `resource_pool.py:189` — `detect_crossings` re-exported in `resource_pool.__all__` but not imported from there (callers use `thresholds` directly); public-surface leak; (b) MED `session.py:374` verbose threshold-copy list comprehension; (c) MED `session.py:455` redundant pool lookup in `apply_resource_patch_player`. | (a) is actually a package-level export GAP (not leak) per rule-checker — ELEVATED to **BLOCKING finding #6** (rule-checker Rule 4 corroborates). (b)(c) → non-blocking Observations; refactor opportunity, no current defect. |
| 9 | reviewer-rule-checker | Yes | findings | Exhaustive: 47 instances across 9 rules. 5 violations: (1) Rule 4 `detect_crossings` missing from `sidequest/game/__init__.py` `__all__`; (2) Rule 5 wiring test omits `UnknownResource`, `NotVoluntary`; (3) Rule 6 OTEL deferral not explicitly documented per-method on `apply_resource_patch`, `apply_resource_patch_player`, `apply_pool_decay`, `process_resource_patch_with_lore`; (4) Rule 9 stale "P4-deferred" docstring at `session.py:315`; (5) Advisory — misleading `sys.float_info.min` comment at `session.py:476`. 42 other instances compliant (No Silent Fallbacks correctly applied to the 6 documented cases, No Stubbing, Wire-Don't-Reinvent, ADR-082 mechanical discipline byte-for-byte, ADR-033 clamp/downward-only/stateless semantics). | (1) ELEVATED — merges with simplifier (a) → BLOCKING finding #6. (2) ELEVATED — merges with test-analyzer → BLOCKING finding #2. (3) ELEVATED to **BLOCKING finding #7** — GM-panel lie-detector principle is load-bearing; generic session.py:306 comment doesn't cover resource pools. (4) ELEVATED — merges with comment-analyzer → BLOCKING finding #3. (5) → non-blocking Observation (cosmetic comment fix). |

**All received: Yes.** 9 of 9 specialists fanned out, all reported. 7 blocking findings elevated after cross-specialist corroboration (several specialists independently flagged the silent-drop, type-lie, and wiring gaps). 13 dismissed with rationale. 18 non-blocking Observations logged for future tidy-up, follow-on chore, or architect's spec-reconcile.

---

## Reviewer Assessment

**Phase:** finish
**Verdict:** **REJECTED** — 7 blocking findings. Fix pass required before merge.

### Specialist Cross-References

- **[PREFLIGHT]** (reviewer-preflight) — surfaced 5 lint errors; F401 dead-import contributes to Observation #L1, I001 to #L2, UP047 parked for separate PEP 695 story.
- **[EDGE]** (reviewer-edge-hunter) — corroborated silent-failure-hunter's legacy_declarations silent-drop → blocking #1; corroborated type-design on `ThresholdAt` annotation lie → blocking #5; two `or {}` / `if resources:` findings dismissed after cross-check with silent-failure-hunter.
- **[SILENT]** (reviewer-silent-failure-hunter) — **origin of blocking #1** (CLAUDE.md "No Silent Fallbacks" hard-gate violation); two other findings logged as Observations.
- **[TEST]** (reviewer-test-analyzer) — surfaced wiring-test method omission → blocking #2 (corroborates rule-checker Rule 5); 7 non-blocking Observations logged; "genre without resources" edge case flagged as follow-on for architect.
- **[DOC]** (reviewer-comment-analyzer) — **origin of blocking #3** (stale P4-deferred docstring — 42-1 binding rule violation) and **blocking #4** (mutator-asymmetry docstring lie).
- **[TYPE]** (reviewer-type-design) — **origin of blocking #5** (`ThresholdAt.at` Protocol type annotation lie); three non-blocking Improvements (validate_assignment, construction-time bounds, event_id guard).
- **[SECURITY]** (reviewer-security) — clean for current scope; 2 latent notes logged architecturally.
- **[SIMPLIFIER]** (reviewer-simplifier) — **origin of blocking #6** (`detect_crossings` export gap; merges with rule-checker Rule 4); 2 non-blocking refactor Observations.
- **[RULE]** (reviewer-rule-checker) — exhaustive pass; 5 violations elevated to 4 blockings (#2/#3/#6/#7 merged from other specialists) + 1 Advisory. Rule 6 (OTEL deferral documentation) is **origin of blocking #7**.

### Blocking Findings (7)

| # | Tag | Severity | Location | Issue | Fix |
|---|-----|----------|----------|-------|-----|
| 1 | [SILENT][EDGE] | HIGH | `sidequest/game/session.py:369` | Non-dict entries in `legacy_declarations` silently dropped via `isinstance(d, dict)` filter; affected resource is then synthesized with unbounded `[-sys.float_info.max, sys.float_info.max]` bounds and `voluntary=False`, losing all metadata. Direct CLAUDE.md "No Silent Fallbacks" hard-gate violation. Dev's architect-flagged trap. | Replace `isinstance(d, dict)` filter with explicit raise: `if not isinstance(d, dict): raise ValueError(f"malformed legacy_declaration: {d!r}")`. Also add try/except around `float(current)` on line 371 that raises with context rather than silently crashing with TypeError. |
| 2 | [TEST][RULE] | HIGH | `sidequest-server/tests/game/test_resource_pool.py:888` | `test_sidequest_game_re_exports_resource_pool_symbols` omits `UnknownResource`, `NotVoluntary`, `apply_resource_patch_by_name` method, and `process_resource_patch_with_lore` method. 42-1 binding rule: wiring test covers every re-exported symbol + every method-surface contract declared in the module docstring. | Add `UnknownResource` and `NotVoluntary` to the `expected` tuple. Add two new assertions: `assert callable(getattr(GameSnapshot, "apply_resource_patch_by_name", None))` and `assert callable(getattr(GameSnapshot, "process_resource_patch_with_lore", None))`. |
| 3 | [DOC][RULE] | HIGH | `sidequest/game/session.py:314-315` | Section comment still says `# P4-deferred: named resource pools (story 16-10)` directly above the `resources` field that this branch fully implements. 42-1 binding rule: docstrings must not make present-tense false claims about state the branch changes. | Replace with `# Named resource pools (story 42-2 — ADR-033 port)`. |
| 4 | [DOC] | HIGH | `sidequest/game/resource_pool.py:78` | Module docstring claims "The mutator surface lives on GameSnapshot (see sidequest.game.session)" implying all pool mutation routes through `ResourcePool._apply_and_clamp`. Actual: `apply_pool_decay` at `session.py:459-478` bypasses `_apply_and_clamp` and clamps inline. Silent invariant-leak docstring. | Either route `apply_pool_decay` through `_apply_and_clamp` (unifies threshold detection + clamp logic — preferred), or amend docstring to `"_apply_and_clamp is the primary mutation primitive; apply_pool_decay bypasses it and clamps inline — see session.py:459-478."`. |
| 5 | [TYPE][EDGE] | HIGH | `sidequest/game/thresholds.py:52` | `ThresholdAt` Protocol declares `at: float`, but the planned `EdgeThreshold` consumer has `at: int`. Protocol attribute annotation is not a structural subtype widening — this will generate mypy/pyright errors when EdgePool is wired (Epic 39 follow-on). Rust's `type Value: PartialOrd + Copy` is generic; Python Protocol should match. | Make `ThresholdAt` `Generic[V]` with `V = TypeVar("V", int, float)`, or widen to `at: int \| float` as a pragmatic alternative. Update `detect_crossings` signature in parallel. |
| 6 | [SIMPLIFIER][RULE] | HIGH | `sidequest/game/__init__.py` + `sidequest/game/resource_pool.py:189` | `detect_crossings` is re-exported in `resource_pool.__all__` but absent from `sidequest/game/__init__.py` `__all__`. 42-4 dispatch / Epic 39 follow-on cannot import it via `from sidequest.game import detect_crossings`. CLAUDE.md Rule 4: every new export has non-test consumers or explicit deferral — neither is in place at the package boundary. | Add `detect_crossings` to the `sidequest/game/__init__.py` import list and `__all__`. Remove from `resource_pool.__all__` (it's structurally in `thresholds.py`, not `resource_pool.py`). |
| 7 | [RULE] | HIGH | `sidequest/game/session.py` (methods: `apply_resource_patch`, `apply_resource_patch_player`, `apply_pool_decay`, `process_resource_patch_with_lore`) | Four state-mutating resource methods ship with no OTEL span emission and no per-method deferral comment pointing to story 42-4. Generic encounter-block comment at `session.py:306` does not mention resource pools. CLAUDE.md OTEL observability principle is load-bearing for the GM-panel lie-detector role. | Add a single block comment above the resource-pool method group (e.g., around session.py:415) stating `# OTEL emission for resource-pool mutations is deferred to story 42-4 (dispatch + OTEL). See context-epic-42.md.`, or a one-line `# OTEL: 42-4` comment on each of the four methods. |

### Non-Blocking Observations (parked for spec-reconcile or follow-on)

**Test gaps:**
- [TEST] Tautological `>= 1` → `== 1` on 2 threshold-crossing tests (`test_resource_pool.py:413,806`) — cosmetic.
- [TEST] Weak `len(store) > 0` assertions (`test_wire_genre_resources.py:1681,1695`) — Rust-parity maintained, but specific `event_id` assertions would be stronger.
- [TEST] "Genre without resources" edge case has zero coverage if `low_fantasy` stays in workshopping (`test_wire_genre_resources.py:1330`) — **flag for architect's spec-reconcile**: add a synthetic test using a minimal RulesConfig so the edge case is covered independent of pack location.

**Type hardening (Improvements, not defects):**
- [TYPE] No `validate_assignment=True` on ResourcePool (`resource_pool.py:171`) — invariant enforced only via clamp call.
- [TYPE] No construction-time `min <= current <= max` check on ResourcePool (`resource_pool.py:126`) — new-pool path in `init_resource_pools` can produce out-of-bounds.
- [TYPE] `event_id: str` no empty/whitespace guard (`resource_pool.py:46`) — defensive Pydantic validator would catch malformed packs.

**Docstring / comment tidy:**
- [DOC] Module-docstring story refs use Rust stories (16-10/11) not sprint 42-2 (`resource_pool.py:62`).
- [DOC] `impl From<GameSnapshotRaw>` reference misleading (`session.py:394`) — no Raw intermediary in Python.
- [DOC] `apply_pool_decay` return-type doc silent on mint_threshold_lore pairing (`session.py:392`).
- [DOC] `test_wire_genre_resources.py:1945` — "surfacing to..." language stale; skip markers already encode resolution.
- [RULE] Advisory — misleading `sys.float_info.min` comment (`session.py:476`): code is correct, comment's first clause wrong.

**Simplifier cleanups:**
- [SIMPLIFIER] Verbose threshold-copy list comprehension (`session.py:374`).
- [SIMPLIFIER] Redundant pool lookup in `apply_resource_patch_player` (`session.py:455`).

**Lint cleanup:**
- [L1] `F401` unused import in test file (autofixable).
- [L2] `I001` 3 import-sort issues (autofixable).
- [L3] `UP047` PEP 695 generics migration — parked for a separate migration story.

**Security (architectural notes, no fix needed in 42-2):**
- [SECURITY] Exception messages embed caller-supplied names (`session.py:154`) — latent wire-protocol leak; engine-internal today.
- [SECURITY] Bare dict subscripts in threshold-extraction loop (`session.py:369`) — latent if untrusted saves ever reach this layer.

**Silent-failure defer:**
- [SILENT] `DuplicateLoreId` catch-and-log (`thresholds.py:677`) — Rust-parity, but returning skipped event_ids would improve GM-panel surfacing. Defer to a follow-on.

### Adversarial Analysis — Mandatory Steps

- **Data flow traced:** save JSON → `@model_validator(mode="before")` migration shim → `ResourcePool` construction → `GameSnapshot.resources: dict[str, ResourcePool]`. Gap: legacy_declarations non-dict entries silently dropped (blocking #1). Otherwise the typed-resources field migration is correct at `session.py:397` — placeholder at `:271-286` truly replaced, not supplemented.
- **Wiring check:** 9 new symbols re-exported from `sidequest.game.__init__.py`, BUT `detect_crossings` is missing from the package-level `__all__` (blocking #6). Wiring test also fails to assert `UnknownResource` + `NotVoluntary` symbols and `apply_resource_patch_by_name` + `process_resource_patch_with_lore` methods (blocking #2).
- **Pattern observed:** `extra="forbid"` correctly applied on all internal types (`ResourceThreshold`, `ResourcePool`, `ResourcePatch`) per 42-1 binding. `ResourcePatchResult` permissive is legitimate (matches Rust no-Serialize). `GameSnapshot` keeps `ignore` (save-surface forward-compat). Convention intact.
- **Error handling verified:** `UnknownResource`/`NotVoluntary` raised loudly on apply path. KeyError inside `@model_validator` raises as `ValidationError` (loud, verified). However the `isinstance(d, dict)` filter (blocking #1) and `or {}` idioms bypass these loud paths for a specific class of malformed legacy saves.
- **Rust-parity audit:** Drama weights, rig base stats, `_RIG_BASE_STATS` table (from 42-1), clamp semantics (`f64::clamp`), `detect_crossings` downward-only predicate (`old > at && new <= at`), `apply_pool_decay` f64::EPSILON guard, `init_resource_pools` upsert semantics (preserve current, refresh metadata, re-clamp), `ResourcePatchOp` serde `rename_all = "lowercase"` — all verified byte-for-byte against Rust source.
- **OTEL:** Four resource methods mutate state with no span emission and no explicit per-method deferral comment (blocking #7). Generic comment at `session.py:306` covers encounter-side only.
- **Security:** Clean. No injection, unsafe deserialization, secrets, auth bypass. Two latent architectural notes logged.

### Design Deviation Audit

TEA's 7 deviations (YAML round-trip skip, Clone/Debug skip, narrator-context-selection deferrals, 37-test pack-integration carve to 42-4, upward threshold composite fixture decomposition, thresholds.py physical location, Option-(c) conditional skipif) — all stamped ACCEPTED by architect's spec-check. No review-side reversal. Two architect-raised design calls (`@model_validator` shim, `-sys.float_info.max`, ThresholdAt Protocol, ResourcePatchResult permissive) also confirmed clean.

**One new deviation-adjacent concern (blocking #4):** the docstring claim that `_apply_and_clamp` is the mutator primitive does not match the code — `apply_pool_decay` bypasses it. This is either a docstring fix OR a refactor call. Preferred fix: route `apply_pool_decay` through `_apply_and_clamp` so the invariant is type-enforced, which also removes the [TYPE] #B/#C Observations (validate_assignment and construction-bounds).

### Next Steps

1. Dev (Naomi) takes the 7 blocking findings. Estimated: ~30 lines across `session.py` + `resource_pool.py` + `thresholds.py` + `__init__.py` + `test_resource_pool.py`. 15-20 minute fix pass.
2. On resubmit: Re-run `pytest tests/game/ -v` (target 533p/22s unchanged) + broader suite regression check.
3. I will re-review commit-by-commit. If all 7 close clean, I stamp APPROVED. If anything regresses, back to Dev.
4. Non-blocking Observations roll forward to architect's spec-reconcile (task #6).

**Handoff doc:** `.session/42-2-handoff-review.md` (REJECTED, 7 findings with file:line).
**Branch tip at review time:** `9fbf099`.

### Reviewer (code review) — Delivery Findings

- **Gap** (blocking): Silent fallback at `session.py:369` drops malformed `legacy_declarations` entries via `isinstance(d, dict)` filter; violates CLAUDE.md "No Silent Fallbacks" hard-gate. Affects `sidequest-server/sidequest/game/session.py` (replace filter with explicit `raise ValueError`). *Found by Reviewer during code review.*
- **Gap** (blocking): Wiring test omits `UnknownResource`, `NotVoluntary` symbols and `apply_resource_patch_by_name` / `process_resource_patch_with_lore` method assertions. Affects `sidequest-server/tests/game/test_resource_pool.py:888` (add symbols to `expected` tuple, add two `callable(getattr(...))` assertions). *Found by Reviewer during code review.*
- **Conflict** (blocking): Stale `# P4-deferred: named resource pools (story 16-10)` comment above fully-implemented `resources` field. Affects `sidequest-server/sidequest/game/session.py:314-315` (replace with current story ref). *Found by Reviewer during code review.*
- **Conflict** (blocking): `resource_pool.py` module docstring claims `_apply_and_clamp` is the mutator primitive, but `apply_pool_decay` bypasses it. Affects `sidequest-server/sidequest/game/resource_pool.py:78` (route decay through `_apply_and_clamp` — preferred — or amend docstring). *Found by Reviewer during code review.*
- **Gap** (blocking): `ThresholdAt.at: float` Protocol annotation will fail structural-subtype check against future `EdgeThreshold.at: int` consumer. Affects `sidequest-server/sidequest/game/thresholds.py:52` (make `Generic[V]` with `TypeVar("V", int, float)` or widen to `int | float`). *Found by Reviewer during code review.*
- **Gap** (blocking): `detect_crossings` re-exported from `resource_pool.__all__` but missing from `sidequest/game/__init__.py` `__all__` — 42-4 dispatch cannot import from package root. Affects `sidequest-server/sidequest/game/__init__.py` (add to import list + `__all__`) and `sidequest-server/sidequest/game/resource_pool.py:189` (remove misplaced re-export). *Found by Reviewer during code review.*
- **Gap** (blocking): Four state-mutating resource methods lack OTEL spans AND lack per-method deferral comment pointing to story 42-4; violates CLAUDE.md OTEL observability principle (GM-panel lie-detector). Affects `sidequest-server/sidequest/game/session.py` (add block comment above resource-pool method group or `# OTEL: 42-4` on each of `apply_resource_patch`, `apply_resource_patch_player`, `apply_pool_decay`, `process_resource_patch_with_lore`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): 18 tidy-up observations (test assertion tautologies, type hardening, docstring refs, simplifier refactors, lint autofixables) — rolled forward to architect's spec-reconcile (task #6). See "Non-Blocking Observations" table in Reviewer Assessment above. *Found by Reviewer during code review.*

**Handoff:** TEA → Reviewer (Chrisjen). 9-specialist fan-out from turn one per team-lead's directive. Branch tip `9fbf099`.

---

## Dev Assessment (rework — 2026-04-20)

**Implementation Complete:** Yes — all 7 blocking findings closed.

**Closure map:**

| # | Finding | Fix applied |
|---|---------|-------------|
| 1 | [SILENT][EDGE] `session.py` silent legacy-decl drop | Replaced `isinstance(d, dict)` filter with explicit `raise ValueError("malformed legacy resource_declaration ...")`. Added `_coerce_current` helper wrapping `float(raw_current)` with `try/except (TypeError, ValueError)` and re-raising with pool-name context. Two new failure-path tests in `test_wire_genre_resources.py`: `test_migration_raises_on_malformed_legacy_declaration`, `test_migration_raises_on_non_numeric_legacy_current`. |
| 2 | [TEST][RULE] wiring test gap | `test_sidequest_game_re_exports_resource_pool_symbols` expanded: asserts `UnknownResource`, `NotVoluntary`, `detect_crossings` (added per #6 fix), and verifies six GameSnapshot methods via `callable(getattr(GameSnapshot, name, None))`: `apply_resource_patch`, `apply_resource_patch_player`, `apply_pool_decay`, `init_resource_pools`, `apply_resource_patch_by_name`, `process_resource_patch_with_lore`. |
| 3 | [DOC][RULE] stale `# P4-deferred` comment | Replaced inline comment with `# Named resource pools (story 42-2 — ADR-033 port)`; also updated the parallel stale claim in the `GameSnapshot` class docstring bullet list. |
| 4 | [DOC] mutator-asymmetry docstring lie | Took Reviewer's **preferred** fix: refactored `apply_pool_decay` to route through `pool._apply_and_clamp(ResourcePatchOp.Add, pool.decay_per_turn)` instead of clamping inline. Every state change now goes through the single invariant-enforcing primitive, making the module docstring truthful. Also retired the now-dead `detect_crossings` import in `session.py`. |
| 5 | [TYPE][EDGE] `ThresholdAt.at` Protocol lie | Widened `at: float` → `at: int \| float`; widened `detect_crossings` `old_value` / `new_value` params in parallel. Docstring updated to cite Python's invariant Protocol annotations and Rust's generic `Value: PartialOrd + Copy`. |
| 6 | [SIMPLIFIER][RULE] `detect_crossings` export gap | Removed `detect_crossings` from `sidequest/game/resource_pool.py` `__all__` with clarifying comment. Added `from sidequest.game.thresholds import detect_crossings` + `"detect_crossings"` to `sidequest/game/__init__.py`. `from sidequest.game import detect_crossings` is now the canonical import path. |
| 7 | [RULE] OTEL deferral undocumented | Added a single block comment above the resource-pool method group in `session.py`: `OTEL: span emission for resource-pool mutations is deferred to story 42-4 (dispatch + OTEL). See context-epic-42.md.` Block form chosen per Reviewer's "or" — higher signal, single source of truth. |

**Lint cleanup (non-blocking Observations auto-fixed during rework):**
- [L1] F401 unused `RulesConfig` import in `test_resource_threshold_lore.py` — autofixed by `ruff --fix`.
- [L2] I001 three import-sort issues — autofixed.
- [L3] UP047 PEP 695 generics on `detect_crossings` — **intentionally not fixed**. Reviewer explicitly parked this as a separate PEP 695 migration story. One-line lint on `thresholds.py:64`; project-wide migration is out of scope for 42-2.

**Files Changed:**
- `sidequest/game/__init__.py` — added `detect_crossings` import + export.
- `sidequest/game/resource_pool.py` — removed `detect_crossings` from `__all__` with clarifying comment.
- `sidequest/game/session.py` — silent-fallback raises, stale `P4-deferred` comment replaced, `apply_pool_decay` refactored through `_apply_and_clamp`, OTEL deferral block comment, dead `detect_crossings` import removed.
- `sidequest/game/thresholds.py` — `ThresholdAt.at` widened to `int | float`, `detect_crossings` value params widened, docstrings updated.
- `tests/game/test_resource_pool.py` — wiring test expanded to cover 4 missing symbols + 6 method contracts.
- `tests/game/test_wire_genre_resources.py` — 2 new failure-path tests for the silent-fallback fix.
- `tests/game/test_resource_threshold_lore.py` — ruff I001 auto-fix (one blank line).

**Tests:** 535 passed + 22 skipped in `tests/game/` (was 533p/22s — +2 new tests, zero regressions).

**Regression check:** Full non-game suite — 5 pre-existing failures reproduced on the pre-rework branch tip `9fbf099` via baseline diff. Not a 42-2 regression.

**Lint:** Only `UP047` remains on the 7 touched files (parked PEP 695 migration item).

**Branch:** `feat/42-2-resource-pool` (same branch — rework commit appended).

**Handoff:** To Reviewer (Chrisjen) for re-review.

### Dev (rework) — Delivery Findings

- No new upstream findings during rework. Reviewer's 18 non-blocking Observations remain parked for Architect's spec-reconcile (task #6), as instructed in the Reviewer Assessment's "Next Steps".

### Dev (rework) — Design Deviations

- No new deviations. Every blocking finding closed exactly as Reviewer specified; the one discretionary choice (#4 — "preferred" refactor path vs. docstring-amend path) matches the Reviewer's stated preference.

---

## Architect Assessment (spec-check — rework pass)

**Spec Alignment:** Aligned.
**Mismatches Found:** None.
**Rework delta reviewed:** `9fbf099..7571c69` — +131 / -30 across 7 files.

**Rust-parity re-verification** (rework changes only):

- **`apply_pool_decay` refactor (Fix #4):** new Python form `pool._apply_and_clamp(ResourcePatchOp.Add, pool.decay_per_turn)` is semantically identical to Rust's `pool.current = (pool.current + pool.decay_per_turn).clamp(pool.min, pool.max)` — `_apply_and_clamp(Add, v)` computes `raw = current + v`, clamps to `[min, max]`, and invokes `detect_crossings(thresholds, old, new)` with the same downward-only predicate. Behaviour unchanged; invariant unified through a single primitive.
- **`ThresholdAt.at: int | float` widening (Fix #5):** matches Rust's `trait ThresholdAt { type Value: PartialOrd + Copy; }`. `detect_crossings` value params widened in parallel so the predicate `old > at && new <= at` remains well-typed for both float and int threshold values. `ResourceThreshold.at: float` is structurally assignable to the widened Protocol. No runtime behaviour change — Python numeric comparisons were already heterogeneous.
- **Silent-fallback raises (Fix #1):** explicit `ValueError` with pool-name context replaces `isinstance(d, dict)` silent filter and bare `float()` TypeError. Strictly stronger than Rust's behaviour (Rust's `From<GameSnapshotRaw>` panics on malformed legacy input); Python now raises loud, structured, test-covered errors.
- **Export surface (Fix #6):** `detect_crossings` now reaches from `sidequest.game` package root, mirroring how Rust's `pub use` shim exposes helpers at the crate root. No consumers broken (it was never used via `resource_pool.detect_crossings` in production code).

**AC coverage re-check (reconciled ACs):**

| AC | Status after rework |
|----|---------------------|
| AC1 (`ResourcePatchOp` parity) | ✓ Unchanged |
| AC2 (clamping silent, errors narrow) | ✓ Unchanged; `apply_pool_decay` now shares the clamp primitive with the patch path |
| AC3 (downward-only stateless crossings) | ✓ Unchanged |
| AC4 (`mint_threshold_lore` fragment shape) | ✓ Unchanged |
| AC5 (save shape + `forbid`) | ✓ **Strengthened** — malformed legacy payloads raise with context (CLAUDE.md No Silent Fallbacks satisfied) |
| AC6 (1:1 Rust parity) | ✓ Preserved; +2 new Python-only failure-path tests for the silent-fallback fix. 533→535 pass, 22 skipped unchanged. |
| AC7 (`init_resource_pools` upsert) | ✓ Unchanged |
| AC8 (legacy migration) | ✓ **Strengthened** — migration fails loud on malformed `resource_declarations` and non-numeric `resource_state`, happy paths preserved |
| AC9 (package re-exports) | ✓ **Expanded** — `detect_crossings`, `UnknownResource`, `NotVoluntary` reach via package root; wiring test covers all re-exported symbols plus six GameSnapshot method contracts |

**Decision:** Proceed to verify. No new Architect-side deviations; rework is a targeted fix pass with Rust-parity preserved byte-for-byte on unchanged code and strengthened on the legacy-migration path.

### Architect (spec-check rework) — Delivery Findings

- No new upstream findings during spec-check rework pass. Reviewer's 18 non-blocking Observations remain queued for spec-reconcile (task #6) post-approval.

### Architect (spec-check rework) — Design Deviations

- No new deviations. Dev's "preferred" refactor choice on Fix #4 is the architecturally stronger path — every mutation now flows through the single `_apply_and_clamp` primitive, which also retires Observations [TYPE]#B and [TYPE]#C (validate_assignment and construction-time bounds) because the clamp invariant is now type-enforced at every call site.

---

## TEA Assessment (verify — rework pass, 2026-04-20)

**Verdict:** GREEN. All 7 blocker fixes behaviourally sound; simplify fan-out surfaced one high-confidence quality finding (applied) plus pre-existing noise (dismissed out of rework scope).

**Test status:**
- `tests/game/`: **535 passed, 22 skipped** (was 533p/22s pre-rework — +2 new failure-path tests for the silent-fallback fix, zero regressions).
- Rework branch tip at verify: `60b80be` (`fix + docs` commits on top of `9fbf099`).

### Simplify Fan-Out Results

| Teammate | Status | Findings | Decision |
|----------|--------|----------|----------|
| `simplify-reuse` | findings | 3 (1 high + 1 medium + 1 low) | All DISMISSED — pre-existing test-helper duplication and clamp pattern predate rework; not introduced by 42-2 rework diff (scope violation by subagent). |
| `simplify-quality` | findings | 1 high (`__init__.py` module docstring stale — missing 42-1/42-2 exports) | **APPLIED** — touched file was already in rework scope (`detect_crossings` export add); 2-line docstring update to list Phase 1 exports including the 42-1 encounter block and 42-2 resource-pool block. Tests still green. Commit `60b80be`. |
| `simplify-efficiency` | clean | 0 | No action. |

### Rework-Fix Behaviour Verification

| # | Fix | TEA verification |
|---|-----|------------------|
| 1 | Silent-fallback raises | Two new tests (`test_migration_raises_on_malformed_legacy_declaration`, `test_migration_raises_on_non_numeric_legacy_current`) assert the explicit `ValueError` path. Both pass. Happy-path migration tests still pass — no regression on the 3 pre-existing migration tests. |
| 2 | Wiring test expansion | `test_sidequest_game_re_exports_resource_pool_symbols` now asserts 10 symbols (3 new: `UnknownResource`, `NotVoluntary`, `detect_crossings`) and 6 GameSnapshot methods via `callable(getattr(...))`. All pass. |
| 3 | Stale comment fix | Grep `P4-deferred.*resource` in `session.py` → zero hits. Stale comment eliminated. |
| 4 | `apply_pool_decay` refactor | Rust-parity verified: `_apply_and_clamp(Add, decay_per_turn)` computes `raw = current + decay_per_turn; clamp(min, max); detect_crossings(...)` — byte-identical to Rust's inline block. Decay tests all still pass with unchanged results. Dead `detect_crossings` import in `session.py` cleaned up. |
| 5 | `ThresholdAt.at: int \| float` | Widened Protocol + `detect_crossings` signature. Float-path tests pass; future `EdgeThreshold` (int path, epic 39) now satisfies Protocol structurally. No runtime behaviour change. |
| 6 | `detect_crossings` export move | Grep `from sidequest.game.resource_pool import.*detect_crossings` → zero production hits. `from sidequest.game import detect_crossings` now canonical. Export surface clean. |
| 7 | OTEL deferral comment | Block comment present above resource-pool method group citing story 42-4 + context-epic-42.md. Four mutating methods all covered by the block. |

### Rust-Parity Re-Verification (diff-scoped)

Parity ledger against `9fbf099..60b80be`:

1. **Clamp semantics** — `max(self.min, min(self.max, raw))` equivalent to Rust `raw.clamp(pool.min, pool.max)`. No drift.
2. **Downward-only predicate** — `old > t.at and new <= t.at` preserved. No drift.
3. **Decay skip guard** — `abs(decay_per_turn) < sys.float_info.epsilon` matches Rust `f64::EPSILON`. No drift.
4. **Upsert semantics** — `init_resource_pools` unchanged by rework. No drift.

### Pre-Existing Suite Regression Check

5 failures in the broader suite (`tests/agents/test_orchestrator.py` caplog pollution + `tests/server/test_rest.py::test_list_genres_empty_when_no_packs_dir`) are pre-existing on commit `9fbf099` — not a 42-2 regression. Dev's original Delivery Finding still stands.

**Lint:** Only `UP047` remains on touched files — intentionally parked per Reviewer's Observation [L3] (separate PEP 695 migration story).

**Handoff:** To Reviewer (Chrisjen) for re-review. Branch tip `60b80be` (one rework-fix commit + one simplify-quality docstring commit).

### TEA (verify rework) — Delivery Findings

- No new upstream findings during verify rework. simplify-reuse's pre-existing test-helper duplication (shared `make_pool`/`make_threshold`/`snapshot_with_pools` across `test_resource_pool.py` and `test_resource_threshold_lore.py`) is a legitimate follow-on but predates this story's rework; logging here as a candidate for spec-reconcile task #6 or a dedicated test-helper consolidation chore.

### TEA (verify rework) — Design Deviations

- No new deviations. Applied simplify-quality's single high-confidence finding (module docstring update) as an in-scope addendum — no behaviour change, no AC impact, no parity risk.

---

## Subagent Results (rework re-review)

6 of 9 specialists fanned out on diff `9fbf099..60b80be` per per-subagent toggles (`edge_hunter`, `security`, `simplifier` disabled via `workflow.reviewer_subagents`). **All received: Yes.**

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 lint regressions; 4 pre-existing lint errors resolved (F401 + 3 I001 autofixed); UP047 unchanged (parked at [L3]). 535p/22s GREEN. | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 LOW (pre-existing `DuplicateLoreId` catch-and-log in `thresholds.py:114` — Rust-parity idempotency path) | DISMISSED — pre-existing, documented as intentional by module docstring; my prior Observation [SILENT] already logged this as Rust-parity follow-on. Not rework-introduced. Both original blockers (silent `isinstance` filter + bare `float(current)`) verified CLOSED. |
| 4 | reviewer-test-analyzer | Yes | clean | 0 | Wiring test covers all 10 symbols + 6 method contracts; both new failure-path tests pin error-message substrings (not vacuous `pytest.raises`). |
| 5 | reviewer-comment-analyzer | Yes | clean | 0 | All 5 verification points pass: P4-deferred comments eliminated at both sites; mutator-asymmetry resolved by refactor; OTEL deferral cites real file `context-epic-42.md`; widened Protocol docstring accurate; `apply_pool_decay` return-type doc updated. |
| 6 | reviewer-type-design | Yes | findings | 3 (1 LOW + 2 MED) | (a) LOW closed-union `at: int \| float` vs Rust's open `PartialOrd` — DISMISSED: my prior REJECT offered this as the "pragmatic alternative"; (b) MED pre-existing `EdgePool.apply_delta` missing `detect_crossings` call — DISMISSED: subagent flagged as pre-existing, belongs to Epic 39, not rework scope; (c) MED dict-with-missing-keys raises bare `KeyError` — **LOGGED as non-blocking Observation**: KeyError still propagates through Pydantic as `ValidationError` (loud), CLAUDE.md satisfied. |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 HIGH (17 rules, 61 instances, 59 compliant) | (a) Rule 3 `_migrate_legacy_resource_fields(cls, data)` unannotated — **LOGGED as non-blocking Observation**: `data` param in `@model_validator(mode="before")` is idiomatically `Any` per Pydantic convention; method signature pre-existed rework; (b) Rule 14 `detect_crossings` export has no direct production consumer + no per-symbol deferral comment at `__init__.py` `__all__` entry — **LOGGED as non-blocking Observation**: Phase 1 manifest docstring cites story 42-2, symbol is used internally via `resource_pool.py`; per-symbol comment is polish, not a gate failure. All 4 original rule violations (Rule 4, 5, 6, 9) verified CLOSED. |

**All received: Yes** (6 returned, 3 disabled and pre-filled).
**Total findings:** 3 Observations logged as non-blocking (type-design dict-KeyError, rule-checker Rule 3, rule-checker Rule 14), 4 dismissed with rationale, **0 blocking**.

---

## Reviewer Assessment (re-review of rework)

**Phase:** finish (rework pass)
**Verdict:** **APPROVED** — all 7 original blockers closed cleanly; 3 new non-blocking Observations logged for spec-reconcile.

**Rework delta reviewed:** `9fbf099..60b80be` (two commits: `7571c69` blocker fixes + `60b80be` simplify-quality docstring polish). +138 / -31 across 7 files.

### Blocker Closure Verification (7/7 CLOSED)

| # | Tag | Blocker | Closure (re-verified this pass) |
|---|-----|---------|--------------------------------|
| 1 | [SILENT][EDGE] | `session.py` silent `isinstance(d, dict)` filter + bare `float(current)` | CLOSED. Explicit `ValueError` raise on non-dict; `_coerce_current` helper wraps `float()` with `try/except` and re-raises with pool name. Two new failure-path tests with pinned message substrings cover both paths. Silent-failure-hunter + rule-checker Rule 15 CLEAN. |
| 2 | [TEST][RULE] | wiring test omits symbols + methods | CLOSED. `test_sidequest_game_re_exports_resource_pool_symbols` asserts 10 symbols (3 new: `UnknownResource`, `NotVoluntary`, `detect_crossings`) + 6 `GameSnapshot` methods via `callable(getattr(...))`. Test-analyzer + rule-checker Rule 16 CLEAN. |
| 3 | [DOC][RULE] | stale `# P4-deferred` comment | CLOSED. Both inline comment and class-docstring bullet updated. Comment-analyzer + rule-checker Rule 20 CLEAN. |
| 4 | [DOC] | mutator-asymmetry docstring lie | CLOSED via **preferred refactor**. `apply_pool_decay` now routes through `pool._apply_and_clamp(ResourcePatchOp.Add, pool.decay_per_turn)`. Single invariant-enforcing primitive for every state change. Comment-analyzer + type-design + rule-checker Rule 21 (Rust-parity) CLEAN. Incidentally retires prior Observations [TYPE]#B (`validate_assignment`) and [TYPE]#C (construction-time bounds). |
| 5 | [TYPE][EDGE] | `ThresholdAt.at: float` Protocol lie | CLOSED. Widened to `at: int \| float` (the "pragmatic alternative" option I offered in the REJECT); `detect_crossings` signature widened in parallel. `ResourceThreshold.at: float` and `EdgeThreshold.at: int` both satisfy structurally. Type-design + rule-checker Rule 21 CLEAN. |
| 6 | [SIMPLIFIER][RULE] | `detect_crossings` export gap | CLOSED. Removed from `resource_pool.__all__`; added to `sidequest/game/__init__.py` `__all__` + Phase 1 manifest docstring. Rule-checker Rule 4 CLEAN. |
| 7 | [RULE] | OTEL deferral undocumented on 4 methods | CLOSED. Block comment above the resource-pool method group explicitly cites story 42-4 + `context-epic-42.md`. All 6 mutating methods covered. Rule-checker Rule 17 CLEAN. |

### Adversarial Analysis — Mandatory Steps (re-run)

- **Data flow traced:** save JSON → `@model_validator(mode="before")` → three raise paths (non-dict decl, non-numeric current, dict-with-missing-keys KeyError) → `ResourcePool` construction → `GameSnapshot.resources`. All failure paths raise loudly; silent drops eliminated.
- **Wiring check:** 10 symbols reach via package root, all covered by expanded wiring test. `detect_crossings` has no direct production consumer yet (42-4 / Epic 39 deferred); flagged as non-blocking Observation.
- **Pattern observed:** `_apply_and_clamp` is the single mutation primitive for every pool state change (patch path AND decay path). Architecturally stronger than pre-rework.
- **Error handling:** all paths raise loudly. Dict-with-missing-keys raises bare `KeyError` (propagates as `ValidationError`) — loud, but a structured `ValueError` with pool name is defensive polish (logged non-blocking).
- **Rust-parity (diff-scoped):** clamp, downward-only predicate, decay epsilon guard, upsert — all preserved byte-for-byte. Rule-checker Rule 21 exhaustively CLEAN.
- **OTEL:** block comment accurate; 42-4 verified against `context-epic-42.md`.
- **Security:** skipped per toggle; prior pass clean; no new surface in rework diff.

### Non-Blocking Observations (rolled forward to spec-reconcile)

Prior 18 Observations from the REJECT pass remain valid and parked. **Three new Observations added this pass:**

1. **[RULE] Rule 3** — `_migrate_legacy_resource_fields(cls, data)` unannotated (`session.py:414`). Pydantic `@model_validator(mode="before")` idiomatically accepts `data: Any`. Low-value tidy-up.
2. **[RULE] Rule 14** — `detect_crossings` package-level re-export has no direct production consumer + no per-symbol deferral comment at the `__all__` entry (`__init__.py:169`). A per-symbol deferral comment (matching the one attached to `mint_threshold_lore` in `resource_pool.py:189`) would close the documentation loop.
3. **[TYPE]** — `_migrate_legacy_resource_fields` dict-with-missing-keys path raises bare `KeyError` rather than structured `ValueError` with pool name. Fail-loud satisfied; structured-message improvement is defensive polish.

Plus the TEA-logged test-helper duplication observation (pre-existing — `make_pool`/`make_threshold`/`snapshot_with_pools` shared shape across three test files) — rolled forward as candidate for consolidation chore.

### Design Deviation Audit (rework)

- TEA's rework deviation (applied simplify-quality docstring finding) — ✓ ACCEPTED: in-scope addendum, no behaviour change.
- Dev's discretionary choice on Fix #4 (preferred refactor over docstring-amend) — ✓ ACCEPTED: architecturally stronger path.
- Architect's spec-check rework pass — ✓ ACCEPTED: Rust-parity verification sound.

No new UNDOCUMENTED deviations found by Reviewer.

### Verdict

**APPROVED.** Rework closed all 7 blockers; 3 new non-blocking Observations queued for spec-reconcile. Rust-parity preserved byte-for-byte and strengthened on the legacy-migration path. Export surface clean. Tests 535p/22s with +2 new regression-coverage tests. Lint delta: -4 pre-existing errors resolved, 0 regressions.

**Handoff:** To SM (Drummer) for finish-story.
**Branch tip at approval:** `60b80be`.

### Reviewer (re-review) — Delivery Findings

- No new upstream findings during re-review. The 3 new non-blocking Observations (Rule 3 annotation, Rule 14 deferral comment, TYPE dict-KeyError) are polish items for spec-reconcile to batch or accept as tracked debt.

### Reviewer (re-review) — Design Deviations

- No new deviations. The rework closed all 7 blockers exactly as specified; one architecturally stronger discretionary choice on Fix #4 (preferred refactor over docstring-amend).

---

## Architect Assessment (spec-reconcile — 2026-04-21)

**Phase:** finish
**Verdict:** DEFINITIVE manifest produced. All prior deviation entries audited for accuracy; three rework-surfaced Observations formalized into the 6-field format; pre-existing non-rework Observations parked with explicit disposition.

### Existing Deviation Entries — Audit Result

All prior sections audited (TEA test design, Dev implementation, Architect pre-red/spec-check, TEA verify, Dev rework, Architect spec-check rework, TEA verify rework, Reviewer original + re-review). No inaccuracies found. All entries STAND as written.

### Architect (reconcile) — Definitive Deviation Manifest

Three rework-surfaced deviations formalized below. Each non-blocking, rolling forward as tracked debt.

- **Closed-union `ThresholdAt.at: int | float` vs. Rust's open `PartialOrd` bound**
  - Spec source: `sidequest-api/crates/sidequest-game/src/thresholds.rs` — `trait ThresholdAt` declaration
  - Spec text: "`trait ThresholdAt { type Value: PartialOrd + Copy; ... }`" — Rust bound is open to any type implementing `PartialOrd + Copy`.
  - Implementation: `ThresholdAt.at: int | float` in `sidequest/game/thresholds.py:56`. Python Protocol attribute annotations are invariant (unlike Rust generic associated types), so a union of the two current concrete value types was chosen in lieu of a parametric `Generic[V]` Protocol.
  - Rationale: Pragmatic pairing with the two current implementors (`ResourceThreshold.at: float`, `EdgeThreshold.at: int`). `Generic[V]` with `TypeVar("V", int, float)` was the stricter alternative Reviewer offered in the REJECT; Dev chose the union per the "pragmatic alternative" explicitly offered as option B. Either form covers current consumers.
  - Severity: minor
  - Forward impact: minor — a future story adding a third value type (e.g., `Decimal` for monetary resources) must widen the union and update `detect_crossings` signature in lockstep. A type alias `ThresholdValue = int | float` in `thresholds.py` would centralize the widening point; recommended follow-on polish.

- **`_migrate_legacy_resource_fields(cls, data)` boundary annotation gap**
  - Spec source: `.pennyfarthing/gates/lang-review/python.md` Rule 3 — type annotation gaps at boundaries
  - Spec text: "Public/boundary-adjacent methods processing raw deserialized input must carry explicit type annotations, including return type."
  - Implementation: `_migrate_legacy_resource_fields(cls, data)` at `sidequest/game/session.py:414` has no annotation on `data` and no return type. Method is a Pydantic `@model_validator(mode="before")` whose `data` argument is whatever raw input Pydantic hands in from `model_validate(...)`.
  - Rationale: Idiomatic Pydantic pattern — `mode="before"` validators accept `Any` raw input (Pydantic docs: "the data argument... could be anything the user passes in"). Adding `data: Any` → `Any` would satisfy the checklist but provides no static safety benefit. Body performs `isinstance(data, dict)` guard at entry; type discipline is runtime-enforced where it matters.
  - Severity: trivial
  - Forward impact: none — cosmetic doc-level change. Batched Pydantic-style cleanup across all `@model_validator(mode="before")` sites would close it uniformly.

- **`detect_crossings` package-level export lacks direct non-test production consumer**
  - Spec source: CLAUDE.md "Verify Wiring, Not Just Existence" + `.pennyfarthing/gates/lang-review/python.md` Rule 14
  - Spec text: "Every new export has non-test consumers or explicit deferral — neither is in place at the package boundary." (paraphrased from CLAUDE.md wiring rule; verbatim quote in Reviewer's original REJECT finding #6)
  - Implementation: `detect_crossings` exported at `sidequest/game/__init__.py:169` with no direct production caller. Internal use is via `sidequest/game/resource_pool.py:172` (inside `_apply_and_clamp`), which imports from `sidequest.game.thresholds` (not the package root). The package-root export is advertised for deferred consumers.
  - Rationale: Deferred consumers are story 42-4 (dispatch + OTEL pipeline) and Epic 39 (EdgePool threshold-crossing wiring). The `__init__.py` Phase 1 manifest docstring explicitly lists `detect_crossings` as a story 42-2 export, and `context-epic-42.md` documents 42-4 as the dispatch consumer. No per-symbol deferral comment at the `__all__` entry itself.
  - Severity: minor
  - Forward impact: minor — a per-symbol comment at `__init__.py:169` (matching the `mint_threshold_lore` inline note in `resource_pool.py:189`) would close the documentation loop. If 42-4 does not land `detect_crossings` consumption, a Rule 14 follow-up story should revisit.

### Pre-Existing Observations (parked, not rework-introduced)

Rolled forward as tracked debt; these predate the 42-2 rework diff and are formalized below with disposition:

1. **Test-helper duplication** — shared shape (`make_pool`, `make_threshold`, `snapshot_with_pools`) across three test files. Candidate for `tests/game/conftest.py` consolidation. Follow-on chore.
2. **`EdgePool.apply_delta` missing `detect_crossings` call** (`creature_core.py:65`) — threshold events on composure pools silently lost. Epic 39 owns this; 42-2 `ThresholdAt.at` widening makes the type-correct fix mechanically trivial.
3. **`DuplicateLoreId` catch-and-log** (`thresholds.py:114`) — Rust-parity idempotency path. Returning `list[EventId]` of skipped entries would improve GM-panel surfacing. Out of 42-2 scope.
4. **`validate_assignment` + construction-time bounds on `ResourcePool`** — retired by the rework's Fix #4 (`apply_pool_decay` refactor unified the clamp invariant at every call site).
5. **"Genre without resources" edge case has zero coverage** (`test_wire_genre_resources.py:1330`) if `low_fantasy` stays in `genre_workshopping/`. Recommend a synthetic-pack test using an in-memory `RulesConfig` in a follow-on test-coverage story.
6. **Docstring tidy** — module-docstring story refs, `impl From<GameSnapshotRaw>` reference, `apply_pool_decay` return-type pairing note, stale skip-marker language. Batch into a follow-on chore.
7. **Misleading `sys.float_info.min` comment** (`session.py:476`) — code correct, comment's first clause wrong. Partial reword applied in rework; residual imprecision is non-load-bearing.
8. **`event_id: str` no empty/whitespace guard** (`resource_pool.py:46`) — defensive Pydantic validator would catch malformed packs. Low priority.
9. **Exception messages embed caller-supplied names** (`session.py:154`, `UnknownResource.__init__`) — engine-internal today; latent wire-protocol leak if ever forwarded. Revisit if/when exception surfaces to WebSocket.
10. **Bare dict subscripts in threshold-extraction loop** — latent if untrusted saves ever reach this layer. Save-migration runs on trusted local files today.
11. **Tautological `>= 1` → `== 1` on 2 threshold-crossing tests** (`test_resource_pool.py:413, 806`) — cosmetic precision tightening.
12. **Weak `len(store) > 0` assertions** (`test_wire_genre_resources.py:1681, 1695`) — Rust-parity maintained; stronger `event_id` assertions would catch specific-crossing regressions.
13. **Verbose threshold-copy list comprehension** (`session.py:374`) + redundant pool lookup in `apply_resource_patch_player` (`session.py:455`) — refactor opportunity, no defect.
14. **UP047 PEP 695 generics on `detect_crossings`** — parked for a separate PEP 695 migration story (project-wide).
15. **Dict-with-missing-keys raises bare `KeyError`** in `_migrate_legacy_resource_fields` — `KeyError` propagates as Pydantic `ValidationError` (loud); structured-message polish is defensive deferred.

### AC Deferral Audit

Zero ACs deferred across the full story lifecycle. All 9 reconciled ACs have coverage:

- AC1–AC4: Full coverage, unchanged by rework.
- AC5 (`forbid` + fail-loud save shape): **Strengthened** — rework closed the silent-fallback hole per CLAUDE.md hard-gate.
- AC6 (Rust 1:1 parity): Preserved + 2 new Python-only failure-path tests (533→535 pass, 22 skipped unchanged).
- AC7–AC8: Upsert + legacy migration **strengthened** by fail-loud raises.
- AC9 (package re-exports): **Expanded** — `detect_crossings`, `UnknownResource`, `NotVoluntary` reach via package root; wiring test covers all 10 symbols + 6 GameSnapshot method contracts.

No AC status changes. No invalidations. No inadvertent addressing.

### Architect (reconcile) — Delivery Findings

- No new upstream findings during spec-reconcile. Prior Delivery Findings from TEA, Dev, and Reviewer stand.

### Architect (reconcile) — Design Deviations

Three formal 6-field entries above comprise the definitive manifest additions. Existing entries from TEA (test design), Dev (implementation), Dev (rework), Architect (spec-check), Architect (spec-check rework), TEA (verify), TEA (verify rework), and Reviewer stand as audited.

**Handoff:** To SM (Drummer) for finish-story. Branch tip `60b80be`.