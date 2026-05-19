---
story_id: "53-1"
jira_key: ""
epic: "Epic 53"
workflow: "tdd"
---
# Story 53-1: RigComposurePool: extend Edge framework for vessel-attached pools

## Story Details
- **ID:** 53-1
- **Jira Key:** (SideQuest is personal — no Jira)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-19T12:22:22Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19 | 2026-05-19T11:55:42Z | 11h 55m |
| red | 2026-05-19T11:55:42Z | 2026-05-19T12:02:28Z | 6m 46s |
| green | 2026-05-19T12:02:28Z | 2026-05-19T12:06:42Z | 4m 14s |
| spec-check | 2026-05-19T12:06:42Z | 2026-05-19T12:08:09Z | 1m 27s |
| verify | 2026-05-19T12:08:09Z | 2026-05-19T12:16:56Z | 8m 47s |
| review | 2026-05-19T12:16:56Z | 2026-05-19T12:20:22Z | 3m 26s |
| spec-reconcile | 2026-05-19T12:20:22Z | 2026-05-19T12:22:22Z | 2m |
| finish | 2026-05-19T12:22:22Z | - | - |

## Sm Assessment

**Story shape:** Foundation story for Epic 53 (Road Warrior). Pure server work in `sidequest-server`, extending the EdgePool framework from ADR-078 to support vessel-attached pools. 3pt TDD — moderate scope, well-bounded.

**Critical-path position:** Unblocks 53-2 (materializer binds RigComposurePool to character via vessel item) and 53-3 (crash event handler reads Composure→0 zero-crossing). 53-1 just *detects* zero-crossing; it does NOT apply damage or fire crash events. That's 53-3's job. Keep this story tight — no scope creep into crash logic.

**Pattern to copy:** `sidequest-server/sidequest/game/pools.py:EdgePool` (per ADR-014, ADR-078). Mirror that API surface: delta operations, max/current bounds, serialization, zero-crossing detection. The binding model adds `character_id` + `vessel_item_id` to the existing EdgePool shape.

**OTEL requirement (CLAUDE.md):** Every subsystem decision must emit watcher events. Stub spans (`rig_pool.created`, `rig_pool.delta`, `rig_pool.zero_crossing`) in this story; 53-4 surfaces them to the GM panel. Do NOT skip the stubs — they're how Sebastien-the-mechanics-first-player audits this subsystem.

**Wiring requirement (CLAUDE.md):** Every test suite needs a wiring test. The `RigComposurePool` class must be reachable from a production code path (game state module import), not just unit-tested in isolation. TEA: include this as a red test.

**HP-removed reminder (user memory):** Edge replaces HP for runtime entities. RigComposurePool is a *new* pool, not a re-skinned HP bar. Mirror EdgePool semantics, not D&D HP semantics.

**Risk flags:**
- 🟡 Don't over-engineer the vessel binding — one rig per character per session, swap allowed. No multi-vessel state machine.
- 🟡 Persistence (53-2 territory) — RigComposurePool serialization must be friendly to the materializer seam. Test round-trip in this story, but don't wire up the materializer here.
- 🟢 No UI work — 53-5 surfaces this to CharacterSheet later.

**Next:** TEA writes red tests against the contract above. Use the pool factory pattern from existing EdgePool tests.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Gap** (non-blocking): Story context names `vessel_item_id` for the rig binding, but the existing codebase uses `chassis_id` universally (`sidequest/game/chassis.py`, `sidequest/telemetry/spans/rig.py`, and the bond ledger). Tests adopted `chassis_id` to stay aligned with the in-tree taxonomy. Affects `sprint/context/53-1.md` AC list — update the spec to match code, or have Dev expose both names. *Found by TEA during test design.*
- **Gap** (non-blocking): Story context names `sidequest/game/pools.py` as the implementation file, but the codebase uses one-pool-per-file (`creature_core.py` houses `EdgePool`; `resource_pool.py` houses `ResourcePool`). Tests import from `sidequest.game` (package root) so Dev can choose the canonical file location without churning tests. Affects `sprint/context/53-1.md` — clarify naming convention or pick a file. *Found by TEA during test design.*
- **Question** (non-blocking): Story 53-2 ("Materializer: instantiate rig vessel item → bind RigComposurePool to character") implies the materializer constructs the pool from a `ChassisInstance` + character. RigComposurePool's `base_max` should likely be derived from a chassis class config (analogous to `edge_pool_from_config` in `creature_core.py:138`). Out of scope for 53-1, but Dev should size `base_max` as a fixed init parameter — do NOT silently default it. *Found by TEA during test design.*
- **Improvement** (non-blocking): `sidequest/telemetry/spans/rig.py` already exists with chassis-bond emitters. The three new pool spans (`rig_pool.created`, `rig_pool.delta`, `rig_pool.zero_crossing`) should be added to that same module — keeps the rig taxonomy in one file rather than fragmenting across `rig.py` and a new `rig_pool.py`. *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Field naming: chassis_id instead of vessel_item_id**
  - Spec source: `sprint/context/53-1.md`, AC line "Bound to a `character_id` and `rig_item_id`"
  - Spec text: "Bound to a `character_id` and `rig_item_id`"
  - Implementation: Tests assert `pool.chassis_id` (not `pool.vessel_item_id` / `pool.rig_item_id`)
  - Rationale: The entire chassis subsystem (`sidequest/game/chassis.py`, `sidequest/telemetry/spans/rig.py`, `sidequest/genre/models/chassis.py`) uses `chassis_id` as the canonical identifier for a `ChassisInstance`. The materializer in 53-2 will bind by chassis id. Using `vessel_item_id`/`rig_item_id` would introduce a third synonym for the same concept and break grep-for-callers consistency.
  - Severity: minor
  - Forward impact: Dev will implement `chassis_id`. 53-2's materializer wires `RigComposurePool(chassis_id=instance.id, ...)`. Spec doc should be updated to match.

- **Implementation file location: package root re-export (deferred to Dev)**
  - Spec source: `sprint/context/53-1.md`, AC-1 "RigComposurePool class defined in `sidequest/game/pools.py`"
  - Spec text: "RigComposurePool class defined in `sidequest/game/pools.py`"
  - Implementation: Tests import from `sidequest.game` (package root), not from a specific file. Dev chooses the file path.
  - Rationale: No `pools.py` exists in the repo. The established convention is one-pool-per-file (`creature_core.py` owns `EdgePool`; `resource_pool.py` owns `ResourcePool`). Creating a generic `pools.py` would break the existing layout. Tests pin only the import surface — `sidequest.game.RigComposurePool` — leaving Dev to either add to `creature_core.py` or create `sidequest/game/rig_composure_pool.py`.
  - Severity: minor
  - Forward impact: Dev must update `sidequest/game/__init__.py` to re-export the class and add to `__all__`. The wiring test asserts both.

- **`apply_delta` return type: structured result, not bare int**
  - Spec source: `sprint/context/53-1.md`, "Technical Context" line `apply_composure_delta(delta: int) -> int (new value)`
  - Spec text: "`apply_composure_delta(delta: int) -> int` (new value)"
  - Implementation: Tests assert `apply_delta(delta) -> RigComposureDeltaResult` with `old_current`, `new_current`, and `zero_crossed` fields.
  - Rationale: The bare-int return cannot signal zero-crossing detection. The crash handler in 53-3 needs to know whether *this* delta crossed zero (vs. landed on already-zero). The EdgePool `apply_delta` returns bare int because it has no crossing semantics; RigComposurePool does. Mirroring `ResourcePatchResult` (also pydantic, with old/new/crossings) gives Dev a precedent.
  - Severity: moderate
  - Forward impact: Story 53-3's crash handler reads `result.zero_crossed` instead of a separate `is_destroyed()` check after the call. Spec doc should be updated; downstream stories already need the richer return.

- **Method name: `apply_delta` not `apply_composure_delta`**
  - Spec source: `sprint/context/53-1.md`, "Technical Context" line `apply_composure_delta(delta: int)`
  - Spec text: "`apply_composure_delta(delta: int) -> int`"
  - Implementation: Tests call `pool.apply_delta(...)` to match EdgePool's verb.
  - Rationale: EdgePool (the pattern this story explicitly mirrors per the SM Assessment and AC-1) uses `apply_delta`. Diverging to `apply_composure_delta` would break the shared verb-shape across the pool family. The receiver type already disambiguates the domain.
  - Severity: minor
  - Forward impact: None — fits the existing pool API verb.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New domain class, foundation for Epic 53. Must be TDD per workflow.

**Test Files:**
- `sidequest-server/tests/game/test_rig_composure_pool.py` — RigComposurePool unit tests, OTEL span emission tests, and package-level wiring tests.

**Tests Written:** 36 tests
**Status:** RED (all 36 fail with ImportError / missing-attribute — verified via testing-runner RUN_ID=53-1-tea-red)

### Coverage Breakdown

| Group | Count | What it asserts |
|-------|-------|-----------------|
| Wiring | 3 | `RigComposurePool` and `RigComposureDeltaResult` re-exported from `sidequest.game`; in `__all__` |
| Construction | 8 | Required fields, blank-id rejection, `extra='forbid'`, current bounds at construction, max > 0 |
| `apply_delta` mechanics | 5 | Positive/negative delta, clamp to max, floor at 0, zero-delta no-op |
| Zero-crossing | 6 | Fires on downward-to-0; does NOT fire on already-0, upward-from-0, non-fatal hit; re-arms after repair |
| `is_destroyed` | 2 | True at 0, False above 0 |
| No-damage isolation | 1 | Reaching zero must not mutate binding fields (53-3 needs them intact) |
| Serialization | 3 | model_dump / model_validate / JSON round-trip; binding fields preserved |
| OTEL spans | 8 | Constants exist + FLAT_ONLY registration + emission on construct/delta/zero-crossing + suppression on non-crossing |

### Rule Coverage

| Rule (CLAUDE.md / SOUL.md) | Test(s) | Status |
|-----------------------------|---------|--------|
| Every test suite needs a wiring test | `test_rig_composure_pool_imports_from_game_package`, `test_rig_composure_pool_in_game_package_all` | failing (RED) |
| No silent fallbacks (pydantic `extra='forbid'`) | `test_rig_composure_pool_strict_extra_forbid` | failing (RED) |
| Fail loud on bad data (non-blank ids, valid bounds) | `test_rig_composure_pool_rejects_blank_*`, `test_rig_composure_pool_rejects_negative_current`, `*_above_max`, `*_zero_or_negative_max` | failing (RED) |
| OTEL on every subsystem decision | `test_rig_pool_construction_emits_created_span`, `*_apply_delta_emits_delta_span`, `*_zero_crossing_emits_zero_crossing_span` | failing (RED) |
| OTEL false-positive suppression | `*_zero_crossing_span_does_not_fire_on_already_zero`, `*_does_not_fire_on_upward_zero_crossing` | failing (RED) |
| Round-trip persistence (save-file safety) | `*_round_trip_via_model_dump_and_validate`, `*_round_trip_via_json`, `*_dump_contains_all_binding_fields` | failing (RED) |

**Rules checked:** 6 of 6 applicable CLAUDE.md / SOUL.md rules have test coverage.
**Self-check:** 0 vacuous tests. Every test calls `assert` against a specific value, not just `is not None`.

### What Dev Needs To Build (GREEN phase brief)

1. **`RigComposurePool`** (pydantic BaseModel, `extra='forbid'`):
   - Fields: `current: int`, `max: int`, `base_max: int`, `character_id: str` (non-blank), `chassis_id: str` (non-blank)
   - Validators: `current` ∈ `[0, max]` at construction; `max > 0`; non-blank string ids
   - Method: `apply_delta(delta: int) -> RigComposureDeltaResult` — clamp to `[0, max]`, detect downward-only zero-crossing
   - Method: `is_destroyed() -> bool` — `current == 0`
   - **MUST NOT** apply damage, mutate `character_id`/`chassis_id` on zero, or call into the crash handler. 53-1 detects; 53-3 acts.

2. **`RigComposureDeltaResult`** (pydantic BaseModel, no extra-forbid needed — non-persistent):
   - `old_current: int`, `new_current: int`, `zero_crossed: bool`
   - `zero_crossed` is True iff `old_current > 0 and new_current == 0`

3. **OTEL spans** in `sidequest/telemetry/spans/rig.py` (extend the existing rig module — see Improvement finding):
   - `SPAN_RIG_POOL_CREATED = "rig_pool.created"` — attrs: `character_id`, `chassis_id`, `current`, `max`
   - `SPAN_RIG_POOL_DELTA = "rig_pool.delta"` — attrs: `character_id`, `chassis_id`, `delta`, `old_current`, `new_current`
   - `SPAN_RIG_POOL_ZERO_CROSSING = "rig_pool.zero_crossing"` — attrs: `character_id`, `chassis_id`, `old_current`, `new_current` (will be 0)
   - All three added to `FLAT_ONLY_SPANS`
   - Emit at the appropriate spots in `RigComposurePool.__init__` (via `model_post_init`) and `apply_delta`

4. **Re-export** from `sidequest/game/__init__.py`: add `RigComposurePool` and `RigComposureDeltaResult` to imports and `__all__`.

### Watch-Out-For

- The construct-time `rig_pool.created` span: pydantic models can't easily emit during `__init__`. Use `model_post_init` (pydantic v2 hook) — it fires after validation, before the constructor returns. Patching `tracer()` after construction (as the test does on the *delta* tests) is intentional: we only want to capture creation in the dedicated creation test.
- `zero_crossed` is downward-only. `old_current > 0 and new_current == 0` — both clauses matter. A pool at 0 hit again should NOT re-fire. A pool healed from 0 to positive should NOT fire.
- Span attribute coercion: per the magic.py / rig.py precedent, None values become `""`. Not load-bearing here (all attrs are non-optional ints/strs), but follow the precedent if you add fields.

**Handoff:** To Dev (Charles) for implementation.

## Design Deviations (Dev addendum)

### Dev (implementation)

- **Implementation file: `sidequest/game/rig_composure_pool.py`**
  - Spec source: `sprint/context/53-1.md`, AC-1 ("`sidequest/game/pools.py`")
  - Spec text: "RigComposurePool class defined in `sidequest/game/pools.py`"
  - Implementation: New file `sidequest/game/rig_composure_pool.py` houses both `RigComposurePool` and `RigComposureDeltaResult`, re-exported from `sidequest.game.__init__`.
  - Rationale: TEA's deviation already flagged this; the project convention is one-pool-per-file (`creature_core.py` owns `EdgePool`, `resource_pool.py` owns `ResourcePool`). Putting the class in a generic `pools.py` would have broken the existing layout.
  - Severity: minor
  - Forward impact: 53-2's materializer imports `RigComposurePool` from `sidequest.game` (package root), not from the module path.

- **Construction-time OTEL span via `model_post_init`**
  - Spec source: `sprint/context/53-1.md`, AC-3 ("Emit in RigComposurePool methods")
  - Spec text: "Emit in RigComposurePool methods" — implying `__init__`-like timing.
  - Implementation: `rig_pool.created` fires from `model_post_init` (pydantic v2 lifecycle hook) so the span emits *after* validators run, not during a half-constructed model.
  - Rationale: A failed validation must NOT emit a creation span — a bad save file would otherwise leave a phantom `rig_pool.created` in the dashboard without a real pool in state. `model_post_init` is the documented pydantic v2 hook that fires once construction is fully validated.
  - Severity: trivial
  - Forward impact: Loading a saved pool also fires `rig_pool.created` (model_validate path). This is intentional — the GM panel should see every live pool instance, whether new or rehydrated. If 53-2's materializer needs to distinguish "fresh-bind" from "rehydrate," it can read the dashboard or add a separate span there.

- **`max <= 0` raises at construction**
  - Spec source: `sprint/context/53-1.md`, AC-1 ("Tracks `composure` integer (max and current)")
  - Spec text: AC does not explicitly forbid `max=0`, but states the pool is a bounded composure tracker.
  - Implementation: `_check_bounds` model_validator raises if `max <= 0`. Tests assert this (`test_rig_composure_pool_rejects_zero_or_negative_max`).
  - Rationale: A `max=0` pool would report `is_destroyed()==True` at construction with no game event to justify it. Per CLAUDE.md "No Silent Fallbacks," this is the kind of malformed save data that needs to fail loud. EdgePool's analog is `creature_edge_pool_from_hp` which clamps to `max(1, hp)` — strict-up rather than clamp-up better matches the save-surface posture.
  - Severity: minor
  - Forward impact: 53-2's materializer must pass `max >= 1`. If chassis classes define `composure_base_max: 0` in YAML, the materializer must reject the chassis config rather than silently zero the pool.

## Dev Assessment

**Implementation Complete:** Yes
**Phase:** finish
**Files Changed:**
- `sidequest-server/sidequest/game/rig_composure_pool.py` — new module: `RigComposurePool` (pydantic BaseModel with bounds + binding + zero-crossing detection) and `RigComposureDeltaResult` (delta result with old/new/zero_crossed)
- `sidequest-server/sidequest/telemetry/spans/rig.py` — added `SPAN_RIG_POOL_CREATED`, `SPAN_RIG_POOL_DELTA`, `SPAN_RIG_POOL_ZERO_CROSSING` constants + `FLAT_ONLY_SPANS` registration (extending the existing rig module per TEA's Improvement finding)
- `sidequest-server/sidequest/game/__init__.py` — re-exports `RigComposurePool` and `RigComposureDeltaResult`; added to `__all__`

**Tests:** 36/36 passing (verified via testing-runner RUN_ID=53-1-dev-green)
**Branch:** `feat/53-1-rig-composure-pool` (pushed to origin)

### Regression Sweep

| Suite | Tests | Pass | Fail | Skip |
|-------|-------|------|------|------|
| `tests/game/test_rig_composure_pool.py` (this story) | 36 | 36 | 0 | 0 |
| `tests/telemetry/` (FLAT_ONLY_SPANS additions safe) | 236 | 236 | 0 | 0 |
| `tests/game/` (sidequest.game.__init__ edit safe) | 1604 | 1575 | 0 | 29 (pre-existing) |

No new failures. No new warnings. Skipped tests are pre-existing.

### Lint + Type

- `uv run ruff check sidequest/game/rig_composure_pool.py sidequest/game/__init__.py sidequest/telemetry/spans/rig.py tests/game/test_rig_composure_pool.py` — All checks passed
- `uv run pyright sidequest/game/rig_composure_pool.py` — 0 errors, 0 warnings, 0 informations

### Acceptance Criteria

- [x] RigComposurePool class — fields (`current`, `max`, `base_max`, `character_id`, `chassis_id`), inheritance via pydantic, delta operations, zero-crossing detection, serialization (model_dump/model_validate/json)
- [x] Binding model: `character_id` + `chassis_id` required and non-blank
- [x] Unit tests in `tests/game/test_rig_composure_pool.py` — initialization, bounds, delta, round-trip, zero-crossing (positive + negative cases)
- [x] OTEL stubs — three `rig_pool.*` spans emitted on construct / delta / zero-crossing
- [x] Wiring test — `RigComposurePool` reachable via `sidequest.game.RigComposurePool` and listed in `__all__`
- [x] No crash logic — RigComposurePool detects zero-crossing only; no injury tags, no Edge loss, no dismount. 53-3 owns the consequences.

### Watch-Out-For (passing to next phase)

- **OTEL on rehydrate:** Loading a saved pool also emits `rig_pool.created` (because pydantic v2 runs validation + `model_post_init` on every `model_validate` call). This is intentional — see deviation entry — but the verify/review phase should sanity-check that the GM panel can tolerate "creation" spans appearing on session resume without misinterpreting them as new-rig events.
- **Span attribute types:** OTEL doesn't like `None` attrs. All current attrs (`character_id`, `chassis_id`, `delta`, `old_current`, `new_current`, `current`, `max`) are non-optional ints/strs, so no `or ""` coercion was needed. If 53-2 wires more chassis metadata into the spans, follow the magic.py / rig.py precedent of `value or ""` for Optional fields.

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (with four pre-logged deviations, all minor/moderate, all defensible)
**Mismatches Found:** 1 missed AC handling (cosmetic — AC was conditional and resolved correctly)

### Pre-logged deviations — review

All four TEA/Dev deviations are well-formed (6 fields each, spec text quoted inline, forward impact noted) and substantively defensible:

| Deviation | Category | Severity | Recommendation |
|---|---|---|---|
| `chassis_id` instead of `vessel_item_id` | Different behavior — Cosmetic | Minor | **A — Update spec.** The chassis subsystem is already the canonical taxonomy (`sidequest/game/chassis.py:74` `ChassisInstance.id`); a third synonym would be friction. Update `sprint/context/53-1.md` AC text in the spec-reconcile phase. |
| File location: `rig_composure_pool.py` instead of `pools.py` | Different behavior — Architectural | Minor | **A — Update spec.** The repo convention is one-pool-per-file (`creature_core.py:46` `EdgePool`; `resource_pool.py:114` `ResourcePool`). The chosen path matches the pattern; the spec was misinformed about the existing layout. |
| `apply_delta` returns `RigComposureDeltaResult`, not bare `int` | Different behavior — Architectural | Moderate | **A — Update spec.** The structured result is load-bearing for 53-3: the crash handler needs `zero_crossed` to distinguish "this delta destroyed the rig" from "delta hit an already-zero pool." Bare-int return would force the handler to maintain its own prior-state cache. `ResourcePatchResult` is the existing precedent (`resource_pool.py:102`). |
| Method name: `apply_delta` not `apply_composure_delta` | Different behavior — Cosmetic | Minor | **A — Update spec.** Matches EdgePool's verb (`creature_core.py:66`). The receiver type already disambiguates the domain — `pool.apply_delta(-5)` is unambiguous on a `RigComposurePool` instance. |

### Missed AC (now documented)

- **AC-2 conditional skip: type contract in `sidequest/protocol/`** (Missing in code — Behavioral — Trivial)
  - Spec: AC-2 says "Type contract in `sidequest/protocol/` (if needed for WebSocket/REST)"
  - Code: No protocol type added.
  - Assessment: The "if needed" conditional resolves to NO at the 53-1 layer. RigComposurePool is engine-internal state, owned by `sidequest.game`. It enters the wire only via `GameSnapshot` serialization (the standard game-state projection path), not as a first-class WebSocket message. No new protocol type is required by 53-1's scope. Story 56-1 (UI: surface RigComposure on CharacterSheet) is the first story that *might* need a wire contract — and only if it needs a delta-update message distinct from the existing state-mirror pipeline.
  - Recommendation: **A — Update spec.** Strike the AC-2 conditional from the story context in spec-reconcile, OR carry it forward to 56-1's context as a question for the UI surfacing decision.
  - Neither TEA nor Dev flagged this — minor process gap, no code change needed.

### Substantive spot-checks

Read the code on disk:

- `sidequest/game/rig_composure_pool.py:55-65` — `RigComposurePool` has the 5 required fields (`current`, `max`, `base_max`, `character_id`, `chassis_id`), `extra='forbid'`. ✓
- `sidequest/game/rig_composure_pool.py:68-87` — validators reject blank ids and `max <= 0` / `current` out of bounds. ✓
- `sidequest/game/rig_composure_pool.py:88-104` — `model_post_init` emits `rig_pool.created` AFTER validation. ✓ (the deviation rationale checks out — a failed validation cannot phantom-emit.)
- `sidequest/game/rig_composure_pool.py:107-152` — `apply_delta` clamps to `[0, max]`, computes `zero_crossed = old_current > 0 and new_current == 0`, emits both spans on the crossing path. ✓ (Downward-only edge logic is correct: already-zero won't fire because `old_current > 0` is False; upward-from-zero won't fire because `new_current == 0` is False.)
- `sidequest/telemetry/spans/rig.py:21-28` — three new constants + `FLAT_ONLY_SPANS` update. ✓ (Routing-completeness test in `tests/telemetry/` confirms — Dev's regression sweep passed 236/236 there.)
- `sidequest/game/__init__.py` — re-exports `RigComposureDeltaResult` and `RigComposurePool`, both in `__all__`. ✓
- No `cr`/`hp` raw fields leak — the HP-removed-per-ADR-078 memory holds. ✓
- No crash logic in this layer — `is_destroyed()` is a snapshot query, no side effects, no event publishing beyond OTEL. ✓

### Cross-story forward impact (for spec-reconcile awareness)

- **53-2 (materializer)** — must construct via `RigComposurePool(character_id=..., chassis_id=instance.id, current=N, max=N, base_max=N)`. The materializer needs a `base_max` source (likely from `genre.chassis_classes.<class>.composure_base_max` — TEA's Question finding flagged this; out of 53-1 scope).
- **53-3 (crash handler)** — subscribes to `rig_pool.zero_crossing` OTEL events. Reads `result.zero_crossed` from `apply_delta` calls in the damage-resolution path. The binding fields (`character_id`, `chassis_id`) are preserved across the zero state — confirmed by `test_rig_composure_pool_apply_delta_does_not_mutate_character_or_chassis_id`.
- **53-5 (UI surface)** — `GameSnapshot` serialization will need to project `RigComposurePool` to the client. If the projection needs per-pool deltas (vs. full snapshots), that's where a `sidequest/protocol/` type might re-enter the picture (revisits AC-2 above).

**Decision:** Proceed to TEA verify. No hand-back to Dev required. The four deviations are all "A — Update spec" cases (improvements over the original spec), and the missed AC-2 is a conditional that correctly resolved to no-op. Spec-reconcile phase (post-review) will fold these into the canonical deviation manifest.

## Design Deviations (TEA verify addendum)

### TEA (test verification)

- **Validator dedup: single multi-field `_binding_id_non_blank` replaces two single-field validators**
  - Spec source: none — internal refactor, no spec deviation
  - Spec text: N/A (style choice within the existing validator pattern)
  - Implementation: Replaced `_character_id_non_blank` + `_chassis_id_non_blank` (identical predicates, distinct field decorators) with `@field_validator("character_id", "chassis_id") _binding_id_non_blank(cls, v, info)` using `ValidationInfo.field_name` for error messages.
  - Rationale: Simplify-efficiency flagged it high-confidence; pydantic v2's multi-field validator preserves identical behavior while eliminating the duplicate body. All 36 tests still pass; error messages still field-specific.
  - Severity: trivial
  - Forward impact: None.

## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed (36/36 story tests; 6520/6520 broader server suite)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (rig_composure_pool.py, __init__.py, telemetry/spans/rig.py, test_rig_composure_pool.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings | (1) inline OTEL → emit_* helpers in rig.py [medium]; (2) test-fixture extraction for repeated pool constructor [high] |
| simplify-quality | 2 findings | (1) missing emit_rig_pool_* helpers in rig.py [medium]; (2) `Any` vs `object` for model_post_init param [low] |
| simplify-efficiency | 3 findings | (1) merge two non-blank validators [high]; (2) model_post_init for single span [medium]; (3) three Span.open blocks in apply_delta [low] |

### Applied Fixes

| # | Source | Finding | Action |
|---|--------|---------|--------|
| 1 | efficiency | Merge two non-blank validators into one multi-field validator | ✅ Applied (commit `71e7195`) — 4 insertions, 11 deletions; 36/36 tests still pass |

### Flagged for Manual Review (medium / not auto-applied)

| Source | Finding | Defer rationale |
|--------|---------|------------------|
| reuse + quality | Move inline `Span.open` to dedicated `emit_rig_pool_*` helpers in `sidequest/telemetry/spans/rig.py` | This is a real convention gap (`rig.py` already houses `emit_rig_bond_event`, `emit_rig_voice_register_change`, etc.) but the change ripples into the producer-helper pattern and may belong in 53-3 when the crash handler becomes a second producer of `rig_pool.zero_crossing`. Reviewer (Potter) should decide whether to require it now or defer to 53-3. |
| efficiency | `model_post_init` for a single OTEL span | Justified by round-trip load semantics (every `model_validate` must emit `rig_pool.created` so the GM panel sees rehydrated pools). Already documented in code comments and Dev deviation log. No-op for TEA. |

### Noted (low / explicit no-op)

| Source | Finding | Decision |
|--------|---------|----------|
| quality | `Any` → `object` for `model_post_init` context param | Style nit; both pydantic-acceptable. `object` matches `turn.py:67` precedent; not load-bearing. Reviewer can ask Dev to change if they care. |
| efficiency | Three `Span.open` blocks in `apply_delta` | Intentional — the GM panel filters `rig_pool.zero_crossing` independently from `rig_pool.delta`. Documented in module docstring. |
| reuse | Pytest fixture for repeated pool constructor | Deliberately not extracted. The verbose constructors are documentation: each test self-documents its starting state. A fixture would force readers to scroll to find what `default_rig_pool` is. Test verbosity > test brevity for AC-anchored cases. |

### Quality Checks

| Check | Result |
|-------|--------|
| `tests/game/test_rig_composure_pool.py` (story tests) | 36/36 pass |
| `tests/telemetry/` (FLAT_ONLY_SPANS additions) | 236/236 pass |
| `tests/game/` (game package smoke) | 1575/1575 pass (29 pre-existing skips) |
| Server full suite (`just server-test`) | 6520/6520 pass (396 pre-existing skips, 786 pre-existing pydantic-shadow warnings) |
| `ruff check sidequest/game/rig_composure_pool.py sidequest/game/__init__.py sidequest/telemetry/spans/rig.py tests/game/test_rig_composure_pool.py` | Clean |
| `pyright sidequest/game/rig_composure_pool.py` | 0 errors / 0 warnings |

**Pre-existing breakage not caused by this story (`just check-all`):**
- Client typecheck (`client-typecheck`) fails on `dice-lib/src/DiceTray.tsx` with TS1484 (`verbatimModuleSyntax` import-type rule). The file lives in a sibling `dice-lib` workspace, last touched by a "wip: pre-tuner-plan changes" commit unrelated to 53-1. 53-1 is server-only — no UI or dice-lib files in this branch's diff. Reviewer should not gate 53-1 on this.
- Client ESLint warning in `App.tsx:1694` (missing `displayName` dep in `useEffect`) — pre-existing, not in this branch's diff.

### Delivery Findings

No new upstream findings during test verification. All TEA-red and Dev-green findings remain accurate.

**Overall:** simplify: applied 1 fix
**Handoff:** To Reviewer (Colonel Potter) for code review.

## Subagent Results

Per `pf settings get workflow.reviewer_subagents`, only `preflight` is enabled on this project; the other 8 specialists are toggled off in `.pennyfarthing/config.local.yaml`. I performed substantive review myself by reading the diff and rules files.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (0 smells, 0 lint, 0 type errors, 36/36 tests, routing GREEN) | N/A |
| 2 | reviewer-edge-hunter | Yes | Skipped — disabled | N/A | Disabled via settings; edge cases reviewed manually below |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped — disabled | N/A | Disabled via settings; reviewed manually below |
| 4 | reviewer-test-analyzer | Yes | Skipped — disabled | N/A | Disabled via settings; reviewed manually below |
| 5 | reviewer-comment-analyzer | Yes | Skipped — disabled | N/A | Disabled via settings; reviewed manually below |
| 6 | reviewer-type-design | Yes | Skipped — disabled | N/A | Disabled via settings; reviewed manually below |
| 7 | reviewer-security | Yes | Skipped — disabled | N/A | Disabled via settings; engine-internal pool, no boundary surface |
| 8 | reviewer-simplifier | Yes | Skipped — disabled | N/A | Disabled via settings; TEA verify already ran a simplify fan-out |
| 9 | reviewer-rule-checker | Yes | Skipped — disabled | N/A | Disabled via settings; reviewed manually below |

**All received:** Yes (1 returned, 8 disabled-and-pre-filled)
**Total findings:** 0 confirmed (blocker / major), 4 noted (minor / observational), 0 dismissed

## Reviewer Assessment

**Verdict:** ✅ Approved
**Confidence:** High
**Blockers:** None
**Branch:** `feat/53-1-rig-composure-pool` (pushed to origin, in sync)
**Tests:** 36/36 (story) — 6520/6520 (full server suite) — 0 lint — 0 type — routing-completeness GREEN

### What I Verified (manual review of the 4-file, 901-line diff)

**Implementation (`sidequest/game/rig_composure_pool.py`, 172 LOC):**
- VERIFIED: `apply_delta` clamp arithmetic is correct. `raw = current + delta; new = max(0, min(self.max, raw))`. Edge cases: positive overflow clamps to `max`, negative overflow floors at `0`. Matches the `EdgePool.apply_delta` precedent in `creature_core.py:66-74` and `ResourcePool._apply_and_clamp` in `resource_pool.py:136-163`.
- VERIFIED: Zero-crossing semantics are downward-edge-only: `zero_crossed = old_current > 0 and new_current == 0`. Re-zero (already-at-zero hit again) → `0 > 0` is False → no crossing. Upward (0 → positive) → `new_current == 0` is False → no crossing. Heal-then-redestroy → crossing re-fires. All four cases tested.
- VERIFIED: `model_post_init` fires AFTER `_check_bounds` (pydantic v2 ordering: field validators → model_validator → model_post_init). Confirmed by `test_rig_composure_pool_rejects_zero_or_negative_max` etc. — a ValidationError prevents `model_post_init` from running, so no phantom `rig_pool.created` span is emitted for a malformed pool. The Dev deviation note on this is accurate.
- VERIFIED: `pydantic-v2 multi-field @field_validator("character_id", "chassis_id")` + `ValidationInfo.field_name` for error specificity — the TEA-verify dedup is correct (no functional regression).
- VERIFIED: `model_config = {"extra": "forbid"}` matches the project's save-surface posture (`EdgePool`, `ResourcePool`).
- VERIFIED: `max` as a field name does not shadow the builtin — `apply_delta` uses `max(0, min(self.max, raw))` and `max` resolves to the LEGB-global builtin because the field is `self.max`. EdgePool and ResourcePool use the same pattern.

**OTEL spans (`sidequest/telemetry/spans/rig.py`, 167 LOC, +10 lines):**
- VERIFIED: All three constants added to `FLAT_ONLY_SPANS`. Routing-completeness test (`tests/telemetry/test_routing_completeness.py`) passed in preflight.
- VERIFIED: Span attribute types are all int/str — OTEL-safe (no None coercion needed).
- VERIFIED: Star-imported by `sidequest/telemetry/spans/__init__.py:82` via existing `from .rig import *`.

**Re-exports (`sidequest/game/__init__.py`, +7 lines):**
- VERIFIED: Both classes added to imports AND `__all__`. Alphabetical within the rig block.

**Tests (`tests/game/test_rig_composure_pool.py`, 712 LOC, 36 tests):**
- VERIFIED: No vacuous assertions — every test asserts a specific value (none of `assert x is not None` or `let _ =` patterns).
- VERIFIED: Zero-crossing matrix is exhaustive: positive→0, overflow→0, already-0 hit, upward-from-0, heal-then-redestroy cycle. Five tests cover the four corners + the re-arming case. This is the load-bearing semantic for story 53-3.
- VERIFIED: OTEL span tests use the `InMemorySpanExporter` + `monkeypatch.setattr(_spans, "tracer", ...)` pattern from `tests/telemetry/test_rig_spans.py`. Correct pattern.
- VERIFIED: Wiring test (`test_rig_composure_pool_imports_from_game_package`, `test_rig_composure_pool_in_game_package_all`) covers the CLAUDE.md "Every Test Suite Needs a Wiring Test" rule at the importability layer.

### Observations (minor — not blockers)

1. **[MANUAL-edge] `apply_delta` mutates `self.current` BEFORE emitting spans.** If `Span.open` ever raises (it shouldn't — OTEL provider failures are swallowed by the SDK and fall back to NoOp), the pool would be in a mutated state but the caller would see an exception instead of a `RigComposureDeltaResult`. In practice, `Span.open` is a `pass`-inside-context idiom and the existing `emit_rig_bond_event` etc. follow the same shape. Severity: trivial. No change recommended unless OTEL semantics change project-wide.

2. **[MANUAL-wiring] CLAUDE.md "Verify Wiring, Not Just Existence" — there is no production non-test consumer yet.** `grep -rn "RigComposurePool" sidequest/` returns only the module itself, `__init__.py`, and the docstring reference in `rig.py`. Story 53-2 (materializer) is the first non-test callsite. This is acknowledged by SM, Architect, and Dev as foundation-story nature, but the wiring principle is strictly speaking only half-satisfied (importability ✓, callsite ✗). **Follow-up:** Story 53-2's reviewer MUST verify the materializer wires this class through `world_materialization.py` / the chassis path. If 53-2 ships without wiring it up, this becomes dead code.

3. **[MANUAL-test] No whitespace-only-id test.** `_binding_id_non_blank` uses `not v.strip()`, so `chassis_id="   "` would also be rejected, but no test asserts that. The `""`-rejection tests cover the most common bad-data case; whitespace-only is a corner. Severity: trivial.

4. **[MANUAL-simple] `base_max` has no validator.** EdgePool's `base_max` defaults to `max` in constructor helpers; here, `base_max` can be 0 or negative without rejection. RigComposurePool doesn't read `base_max` in this story — it's a passthrough field for 53-2's materializer to populate. If 53-2 silently defaults `base_max=0`, the bug would only surface when an advancement-tier story reads it. Severity: minor — flag for 53-2's reviewer rather than block here.

### Rule Compliance

Manually checked against `CLAUDE.md` (root + `sidequest-server/CLAUDE.md`) and `SOUL.md`:

| Rule | Source | Compliance |
|------|--------|------------|
| No silent fallbacks | CLAUDE.md (server) | ✅ `extra='forbid'` rejects unknown fields; non-blank validators reject empty IDs; `_check_bounds` rejects malformed bounds |
| No stubbing | CLAUDE.md (server) | ✅ Full implementation, no `pass`-only methods, no NotImplementedError stubs |
| Don't reinvent — wire up what exists | CLAUDE.md (server) | ✅ Mirrors EdgePool/ResourcePool patterns; extends existing `rig.py` spans module rather than creating `rig_pool.py` |
| Verify wiring, not just existence | CLAUDE.md (server) | ⚠️ Half-satisfied — see Observation #2. Importability ✓, production callsite ✗ (deferred to 53-2). Acceptable for foundation story. |
| Every test suite needs a wiring test | CLAUDE.md (server) | ✅ Two wiring tests cover `sidequest.game.RigComposurePool` import and `__all__` membership |
| OTEL on every subsystem decision | CLAUDE.md OTEL principle, ADR-031 | ✅ Three spans (`rig_pool.created`, `rig_pool.delta`, `rig_pool.zero_crossing`) emit on construct, mutation, and edge-trigger |
| HP-removed (ADR-078) | user memory | ✅ No `hp` or `max_hp` fields; the pool is independent of `EdgePool` (sibling, not subclass) |
| Test paranoia (CLAUDE.md / TEA agent definition) | CLAUDE.md | ✅ 36 tests cover happy path + null/empty IDs + boundary values + zero-crossing matrix + serialization round-trip + OTEL false-positive suppression |
| Branch targets `develop` (sidequest-server uses gitflow) | `.pennyfarthing/repos.yaml` | ✅ `feat/53-1-rig-composure-pool` branched from develop; PR target should be `develop` |

### Spec / Deviation Notes

The four TEA + two Dev deviations are all well-formed (6 fields each, spec text quoted, forward impact noted). All resolve to "Update spec" in spec-reconcile (Architect agreed in spec-check). No deviations introduce risk to 53-2/53-3/53-5 — in fact the structured `RigComposureDeltaResult.zero_crossed` is load-bearing for 53-3 (already noted as forward impact).

### Decision: Approve & Merge

Approve. The implementation is tight, the tests are exhaustive, the OTEL discipline matches the project's lie-detector philosophy, and the deviation log is honest about the bare-int-vs-structured-result improvement over the original spec.

**Reasoning:** SM, TEA, Dev, Architect, and TEA-verify have all done substantive work. The change is 4 files, isolated to `sidequest-server`, with zero impact on cross-repo surfaces. Foundation story with no current consumers — but that's the explicit story decomposition.

### Handoff

- Story 53-1: ready for SM finish (PR creation + merge).
- **Action item for 53-2:** Reviewer must verify the materializer actually wires `RigComposurePool` into game state — observation #2 above.
- **Action item for 53-2:** Reviewer must verify `base_max` is set to a sensible value at materialization — observation #4 above.

**Handoff:** To Architect (Houlihan) for spec-reconcile, then SM (Hawkeye) for finish.

## Design Deviations (Architect reconcile addendum)

### Architect (reconcile)

#### Verified existing entries

I cross-checked every TEA, Dev, and TEA-verify deviation against `sprint/context/53-1.md` and the diff at `feat/53-1-rig-composure-pool`. All spec_source paths exist, all quoted spec text is accurate (verbatim quotes confirmed against the context file), all 6 fields are populated, and all "Forward impact" lines correctly identify sibling story consumers (53-2, 53-3, 53-5). No corrections required.

#### Missed deviations (now documented)

- **Spec internal inconsistency: three synonyms for the same identifier (`rig_item_id` / `vessel_item_id` / `chassis_id`)**
  - Spec source: `sprint/context/53-1.md`, AC-1 (line 9) AND Design Notes (line 28)
  - Spec text: "Bound to a `character_id` and `rig_item_id`" (AC-1) and "**Binding model**: vessel_item_id + character_id unique pair" (Design Notes). The story context itself uses two different names for the same field; the code adopted a third (`chassis_id`) to match the existing `ChassisInstance.id` taxonomy.
  - Implementation: Code uses `chassis_id`. TEA's first deviation flagged this against the AC; this entry adds that the spec is *internally* inconsistent, not just spec-vs-code inconsistent.
  - Rationale: The Design Notes' "vessel_item_id" leaked from an earlier iteration; the AC's "rig_item_id" was the intended canonical name; the code's "chassis_id" matches the broader codebase taxonomy. Three names → one name (`chassis_id`) is a strict improvement. **Spec-side fix:** `sprint/context/53-1.md` should be updated in this same PR or its successor to use `chassis_id` consistently in both AC-1 and Design Notes.
  - Severity: minor
  - Forward impact: None on code. Documentation hygiene: 53-2's context document should also use `chassis_id` to avoid propagating the synonym drift.

- **OTEL import path: `Span` helper used instead of `TraceProvider`**
  - Spec source: `sprint/context/53-1.md`, AC-4 "OTEL integration stub" (line 18)
  - Spec text: "Import `TraceProvider` and define spans (rig_pool.created, rig_pool.delta, rig_pool.zero_crossing)"
  - Implementation: `sidequest/game/rig_composure_pool.py:32` imports `Span` from `sidequest.telemetry.spans` (a project-internal `contextmanager` wrapper around `TracerProvider.start_as_current_span`). The literal `TraceProvider` (or `TracerProvider`) is never imported in this module.
  - Rationale: `Span` is the project-wide pattern for OTEL emission, established in `sidequest/telemetry/spans/span.py` and used by every existing emitter in the `spans/` package (`rig.py`, `magic.py`, `combat.py`, etc.). It honors the monkeypatched `_spans.tracer` binding used by the test fixtures (`tests/telemetry/test_rig_spans.py:53`) — a direct `trace.get_tracer(...)` call would bypass that and break the test pattern. The spec's mention of `TraceProvider` was an inadvertent specificity; the conventional helper is correct.
  - Severity: trivial
  - Forward impact: None.

- **Constraint not enforced at the pool layer: "one rig per character per session"**
  - Spec source: `sprint/context/53-1.md`, Design Notes (line 28)
  - Spec text: "**Binding model**: vessel_item_id + character_id unique pair; one rig per character per session (can swap vessels)"
  - Implementation: `RigComposurePool` carries `character_id` and `chassis_id` but does not enforce uniqueness — any caller can instantiate two pools with the same `character_id`. There is no global registry check.
  - Rationale: Uniqueness enforcement belongs to the materializer (story 53-2), which is the single construction call site that knows about the live `GameSnapshot` and can enforce "one pool per character." Putting the constraint on the pool itself would require either a class-level registry (bad — saves/loads would conflict) or a snapshot-aware factory (which is the materializer). Correct layering: foundation models stay pure; the materializer enforces game-state invariants.
  - Severity: minor
  - Forward impact: **53-2 (materializer) MUST enforce the "one pool per character" invariant** — e.g., reject a second `RigComposurePool` for a character that already has one bound (or replace + emit a `rig_pool.unbound` span on the old one). The Reviewer of 53-2 should grep for this enforcement; missing it would silently allow ghost pools to accumulate.

- **Refactor phase ownership: spec says "ORCHESTRATOR", workflow says TEA verify**
  - Spec source: `sprint/context/53-1.md`, Testing Strategy step 3 (line 43)
  - Spec text: "**Refactor phase** (ORCHESTRATOR): Extract common patterns, ensure wiring test passes"
  - Implementation: The TDD workflow YAML (`pennyfarthing-dist/workflows/tdd.yaml`) routes the refactor stage to TEA verify, not an Orchestrator phase. TEA-verify ran the simplify fan-out and applied the one high-confidence dedup.
  - Rationale: The spec's "ORCHESTRATOR" is shorthand from an older workflow shape; the project's current tdd workflow uses TEA-as-refactor-verifier per `pf workflow show tdd`. No code change required — the right work happened, just under a different agent label.
  - Severity: trivial
  - Forward impact: Spec doc should drop "(ORCHESTRATOR)" from Testing Strategy, or rename it "(TEA verify)" to match the live workflow.

#### AC Deferral Verification

- AC-2 ("Type contract in `sidequest/protocol/`") was conditionally not-applicable per the Architect spec-check assessment (engine-internal pool, reaches the wire via standard `GameSnapshot` projection). The Reviewer's manual review of `grep -rn "RigComposurePool" sidequest/` confirmed no protocol-layer additions in the diff. The deferral holds — no protocol type was inadvertently added or removed during review.

- AC-5 wiring test: The Reviewer noted importability ✓ but production-callsite ✗ (deferred to 53-2). This is a half-satisfied CLAUDE.md rule that the entire chain (SM → Architect spec-check → Dev → TEA verify → Reviewer) has consistently acknowledged as the correct decomposition for a foundation story. The "fully wired" portion of AC-5 is **DEFERRED to story 53-2** and the Reviewer's action item for 53-2 makes that explicit.

#### Reconcile Summary

| Layer | Deviations Logged | Layer-Owner |
|-------|-------------------|-------------|
| Tests | 4 | TEA (red) |
| Implementation | 3 | Dev (green) |
| Refactor | 1 | TEA (verify) |
| **Reconcile (this section)** | **4 newly added** | **Architect** |
| **Total deviations on story 53-1** | **12** | — |

All twelve deviations are minor or trivial. None changes the semantic contract that 53-2/53-3/53-5 will consume. The one moderate-severity item (`apply_delta` returns `RigComposureDeltaResult` instead of bare `int`) is a strict improvement over the spec — without `zero_crossed` in the return, 53-3's crash handler would need its own pre-state cache.

#### Boss-Audit Summary

A reader auditing this story from the session file alone should know:

1. **Story shipped.** 36/36 story tests, 6520/6520 server suite, lint and pyright clean.
2. **Foundation only.** RigComposurePool has no production consumers yet. 53-2 wires the materializer, 53-3 wires the crash handler, 53-5 wires the UI. The Reviewer logged explicit action items for 53-2's reviewer.
3. **Spec drift was minor.** Twelve deviations, all logged with rationale. Eleven are "spec was loose" cases (synonym drift, off-by-one workflow phase name, conditional ACs); one is a small API improvement (structured delta result).
4. **OTEL discipline holds.** Three flat-only spans (`rig_pool.created`, `rig_pool.delta`, `rig_pool.zero_crossing`) emit on construct/mutate/edge-trigger. GM panel will see every pool entering live state and every damage event.
5. **Three doc updates owed in spec-reconcile housekeeping (non-blocking):** `sprint/context/53-1.md` should be patched to use `chassis_id` consistently, drop the AC-4 `TraceProvider` literal, and rename Testing Strategy phase 3 from "(ORCHESTRATOR)" to "(TEA verify)". These can ride on a future story's chore commit or stay as historical record — the live spec is the code.

**Decision:** Spec aligned. Proceed to SM finish.