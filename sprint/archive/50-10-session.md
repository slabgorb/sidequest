---
story_id: "50-10"
jira_key: ""
epic: "50"
workflow: "tdd"
---

# Story 50-10: Disposition: central Attitude enum + Disposition.attitude() derivation (replace dispatch/opening helper)

## Story Details

- **ID:** 50-10
- **Epic:** 50 — Pingpong-archive triage and dropped-work cleanup
- **Jira Key:** None (personal project, no Jira)
- **Workflow:** tdd
- **Stack Parent:** none (foundation for 50-11, 50-12, 50-13)
- **Type:** refactor
- **Points:** 3
- **Priority:** p2

## Story Context

**ADR-020** defines the NPC disposition system: a numeric disposition (-100..+100) maps to a qualitative attitude ("friendly" / "neutral" / "hostile"). The decision was to keep the world-state agent (which thinks numerically: "+5 disposition") separate from the narrator/NPC agents (which think qualitatively: "the NPC is friendly").

The Rust-era implementation included:
- An `Attitude` enum with three variants: `Friendly | Neutral | Hostile`
- A `Disposition(i32)` newtype with `.attitude()` derivation
- Automatic re-derivation on every access to ensure consistency

The 2026-04 Python port kept the **numeric layer** but dropped the qualitative layer. The 2026-05-13 audit surfaced that the one place attitude derivation *does* exist is opening-scene-only (`sidequest/server/dispatch/opening.py:49`), in a private helper:

```python
def disposition_attitude(disposition: int) -> str:
    if disposition > 10:
        return "friendly"
    if disposition < -10:
        return "hostile"
    return "neutral"
```

This breaks the "agents see only the attitude" architectural decision. The narrator prompt and NPC serialization see raw `int` disposition for the rest of play. The qualitative layer exists for one screen, then disappears.

**Story 50-10** restores the qualitative split:

1. Create a central `Attitude` enum with three string-valued variants ("friendly", "neutral", "hostile")
2. Add a `Disposition` class that wraps the numeric value and provides `.attitude()` derivation
3. Move NPC's `disposition: int` field to use `Disposition` instead
4. Replace all call sites to use `.attitude()` instead of the helper function
5. Keep the string literal values ("friendly" / "neutral" / "hostile") stable for downstream consumers (OTEL, GM panel, narrator serialization)

This refactor unblocks 50-11 (threshold-crossing OTEL detection), 50-12 (narrator NPC serialization), and 50-13 (genre-configurable thresholds).

## Technical Approach

### Step 1: Create `Attitude` enum in `sidequest/game/disposition.py`

Define three-variant enum with string values:

```python
from enum import Enum

class Attitude(str, Enum):
    """Three-tier attitude band per ADR-020.
    
    Values are deliberately string-based to maintain the stable contract
    with downstream consumers (OTEL spans, GM panel, narrator serialization).
    """
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    HOSTILE = "hostile"
```

### Step 2: Create `Disposition` class

Wrap numeric disposition with `.attitude()` derivation:

```python
class Disposition:
    """Non-player character disposition score with attitude derivation.
    
    Boundaries per ADR-020:
    - > 10: friendly
    - -10 to 10: neutral
    - < -10: hostile
    """
    
    def __init__(self, value: int = 0):
        self.value = max(-100, min(100, value))  # clamp to ±100
    
    def attitude(self) -> Attitude:
        """Derive the qualitative attitude from numeric disposition."""
        if self.value > 10:
            return Attitude.FRIENDLY
        if self.value < -10:
            return Attitude.HOSTILE
        return Attitude.NEUTRAL
    
    # Support int conversion and serialization for backward compat
    def __int__(self) -> int:
        return self.value
    
    def __repr__(self) -> str:
        return f"Disposition({self.value})"
```

### Step 3: Update `Npc` model

Change the disposition field from `int` to `Disposition`:

```python
from sidequest.game.disposition import Disposition

class Npc(BaseModel):
    # ... other fields ...
    disposition: Disposition = Disposition()  # or Field(default_factory=lambda: Disposition())
```

Handle Pydantic serialization/deserialization with a custom serializer if needed to keep round-trip compatibility.

### Step 4: Replace call sites

Replace all `disposition_attitude(npc.disposition)` calls with `npc.disposition.attitude()`:
- `sidequest/server/dispatch/opening.py:140, 341` — when building NPC lists for opening scene
- `sidequest/game/session.py` — when emitting OTEL `SPAN_DISPOSITION_SHIFT` spans

### Step 5: Retire the old helper

Mark `disposition_attitude` as deprecated or remove it once all call sites are migrated. Keep it in the module if any external tests still depend on it, but it should be unused in production.

## Acceptance Criteria

- [ ] `Attitude` enum exists with three variants: `FRIENDLY`, `NEUTRAL`, `HOSTILE` with string values ("friendly" / "neutral" / "hostile")
- [ ] `Disposition` class wraps an int, exposes `.attitude()` derivation, and clamps to ±100
- [ ] `Npc.disposition` field accepts `Disposition` instances (verify Pydantic round-trip works)
- [ ] All production call sites (`opening.py`, `session.py`) use `.attitude()` instead of the helper
- [ ] OTEL `SPAN_DISPOSITION_SHIFT` spans still emit `before_attitude` / `after_attitude` with correct string values
- [ ] Unit tests cover boundary cases (value=0, value=10, value=11, value=-10, value=-11, value=±100)
- [ ] Integration test verifies the full NPC lookup → attitude derivation → OTEL wiring (opening scene dispatch)
- [ ] No test failures; existing tests still pass with minimal changes to mock/fixture setup

## Sm Assessment

Setup complete. Story is a focused refactor (3 pts) on `sidequest-server`, restoring the qualitative attitude layer dropped during the 2026-04 Python port. The Rust-era pattern (Attitude enum + Disposition newtype with `.attitude()` derivation) is well-documented in ADR-020 and the 2026-05-13 audit pinpointed the surviving code at `sidequest/server/dispatch/opening.py:49`.

**Why this is ready for TEA (red phase):**
- Acceptance criteria are concrete and testable (boundary values at ±10, ±11, ±100, 0; Pydantic round-trip; OTEL string emission)
- No upstream dependencies — this is the foundation for 50-11/50-12/50-13
- Branch `feat/50-10-disposition-central-attitude-enum` created on sidequest-server develop
- Call sites enumerated (`opening.py:140,341`, `session.py` OTEL emission)

**Risks for TEA to probe:**
- Pydantic v2 serialization of the `Disposition` class — round-trip through SQLite save files must keep the integer value stable
- Existing fixtures may set `npc.disposition = 5` as raw int; tests should cover both forms during migration
- The OTEL `SPAN_DISPOSITION_SHIFT` contract emits string `before_attitude`/`after_attitude` — TEA should fail-test that contract before any code moves

Handoff to The Caterpillar (TEA) for RED phase.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-13T11:39:19Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-13 | 2026-05-13T10:54:00Z | 10h 54m |
| red | 2026-05-13T10:54:00Z | 2026-05-13T11:01:31Z | 7m 31s |
| green | 2026-05-13T11:01:31Z | 2026-05-13T11:12:55Z | 11m 24s |
| spec-check | 2026-05-13T11:12:55Z | 2026-05-13T11:14:39Z | 1m 44s |
| verify | 2026-05-13T11:14:39Z | 2026-05-13T11:22:44Z | 8m 5s |
| review | 2026-05-13T11:22:44Z | 2026-05-13T11:36:06Z | 13m 22s |
| spec-reconcile | 2026-05-13T11:36:06Z | 2026-05-13T11:39:19Z | 3m 13s |
| finish | 2026-05-13T11:39:19Z | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** Pure refactor with explicit type contracts; ACs name boundary values, Pydantic round-trip, and OTEL string contract — all directly testable.

**Test Files:**
- `sidequest-server/tests/game/test_disposition_attitude_enum.py` — Attitude enum shape + Disposition value/.attitude() unit tests (23 tests)
- `sidequest-server/tests/game/test_npc_disposition_field.py` — Pydantic field round-trip, raw-int backward compat, default_factory independence (12 tests)
- `sidequest-server/tests/game/test_disposition_call_site_migration.py` — wiring: no production calls to legacy helper + behavioral SPAN_DISPOSITION_SHIFT contract (5 tests)

**Tests Written:** 40 tests covering 8 ACs
**Status:** RED (failing at import — `Attitude` and `Disposition` symbols don't exist in `sidequest.game.disposition`)

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 mutable defaults | `test_two_disposition_instances_with_defaults_are_independent_objects`, `test_two_npcs_with_default_disposition_have_independent_state` | failing (RED) |
| #3 type annotations at boundaries | Implicit via `isinstance(npc.disposition, Disposition)` checks across field tests | failing (RED) |
| #6 test quality | All tests assert concrete values; no `assert True` / vacuous truthy checks; self-checked before commit | passing (no vacuous tests written) |
| #10 import hygiene | `test_opening_dispatch_imports_disposition_class_not_helper`, `test_session_apply_patch_does_not_import_disposition_attitude_helper` | failing (RED) |
| Wiring (CLAUDE.md) | `test_no_production_module_calls_disposition_attitude_helper` (source scan) + `test_apply_patch_emits_attitude_strings_from_disposition_method` (behavioral) | failing (RED) |

**Rules checked:** 5 of 13 applicable Python lang-review rules have test coverage. Rules #1, #4, #5, #7-9, #11-13 are not exercised by this refactor (no exception handling, no path I/O, no async, no deserialization-from-untrusted, no new dependencies, no logging changes).

**Self-check:** 0 vacuous tests found. Every assertion checks a specific value, type, or band literal.

### Test Strategy Notes for Dev

1. **`Attitude` is `str, Enum`** — locked by `test_attitude_is_str_subclass_for_otel_serialization`. Without the str-subclass, OTEL span attributes would serialize as `"Attitude.FRIENDLY"` (the repr), not `"friendly"`. The existing `test_disposition_threshold_crossing.py` integration tests assert `evt["fields"]["before_attitude"] == "neutral"` — that string equality only works if Attitude is a str subclass OR the span extract coerces to `.value` before emit. Recommend `class Attitude(str, Enum)` — minimal cognitive load downstream.

2. **`Npc.disposition` must use `default_factory`** — `test_two_npcs_with_default_disposition_have_independent_state` will fail if you write `disposition: Disposition = Disposition()` at the class level. Use `disposition: Disposition = Field(default_factory=Disposition)`.

3. **Backward-compat coercion is mandatory** — `test_npc_disposition_field_accepts_raw_int_for_backward_compat` covers the existing integration tests (`test_disposition_otel_wiring.py`, `test_disposition_threshold_crossing.py`) which all pass raw ints to `Npc(disposition=...)`. Pydantic v2 needs a `field_validator` (mode="before") that accepts `int | Disposition` and coerces.

4. **`session.apply_world_patch` mutator must preserve type** — `test_apply_patch_npc_disposition_remains_disposition_object` will catch the easy mistake of `npc.disposition = max(-100, min(100, npc.disposition + delta))` where `+ delta` falls through to int. The cleanest path: write `npc.disposition = Disposition(int(npc.disposition) + delta)` and let Disposition clamp internally.

5. **Pre-existing integration tests will need fixture-edit-touch** — `test_disposition_otel_wiring.py:113` asserts `snapshot.npcs[0].disposition == 25` (raw int compare). After the refactor that's `Disposition(25) == 25` — either define `Disposition.__eq__(int)` OR update those callsites to `int(snapshot.npcs[0].disposition) == 25`. Per memory `feedback_dont_revert_features`, prefer to update the assertions to fit the new shape rather than adding `__eq__(int)` for backward compat.

**Handoff:** To Dev for implementation (GREEN phase).

## Delivery Findings

No upstream findings at setup time.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Improvement** (non-blocking): The Rust-era `Disposition` newtype design summary in the session's Technical Approach proposes `__init__(self, value: int = 0): self.value = max(-100, min(100, value))`. Pydantic v2 won't accept a non-`BaseModel` non-dataclass as a field type by default — a `field_validator(mode="before")` on `Npc.disposition` is needed to coerce raw ints, plus either `arbitrary_types_allowed=True` on `model_config` or making `Disposition` a Pydantic model itself. Affects `sidequest/game/disposition.py` (model decoration) and `sidequest/game/session.py:119` (`Npc.model_config`). *Found by TEA during test design.*
- **Question** (non-blocking): Disposition equality semantics — should `Disposition(25) == 25` be true? The existing `test_disposition_otel_wiring.py:113` and `:141` assume raw-int comparison. TEA recommends NOT defining `__eq__(int)` (it breaks Python's reflexive equality contract: `25 == Disposition(25)` would not symmetrically work without `int.__eq__` cooperation, which Python forbids overriding). Instead update those two assertions to `int(snapshot.npcs[0].disposition) == 25`. Affects `tests/integration/test_disposition_otel_wiring.py:113,141`. *Found by TEA during test design.*

### Dev (implementation)

- No upstream findings during implementation.

### TEA (test verification)

- **Improvement** (non-blocking): Test fixtures for OTEL watcher setup duplicated across three files (`tests/integration/test_disposition_otel_wiring.py`, `tests/integration/test_disposition_threshold_crossing.py`, `tests/game/test_disposition_call_site_migration.py`).
  Affects `tests/integration/test_disposition_otel_wiring.py`, `tests/integration/test_disposition_threshold_crossing.py`, `tests/game/test_disposition_call_site_migration.py` (extract `_make_pc`, `_make_npc`, `_setup`, `_wait_for_event` into a shared `tests/_otel_fixtures.py` module).
  *Found by TEA during test verification.*
- **Improvement** (non-blocking): `opening.py` NPC roster rendering duplicated between `_render_directive_chassis` (lines 131-137) and `_render_directive_location` (lines 332-336) — pre-existing pattern, touched by 50-10 only at the attitude-derivation line.
  Affects `sidequest/server/dispatch/opening.py` (extract `_render_npc_roster_lines(npcs: list[AuthoredNpc]) -> list[str]`).
  *Found by TEA during test verification.*
- **Improvement** (non-blocking): Pre-existing flaky tests in `tests/server/test_chargen_*.py` — different test fails on each full-suite run, all pass in isolation. Likely test-ordering coupling through shared SQLite save state at `~/.sidequest/saves/`.
  Affects `tests/server/test_chargen_persist_and_play.py`, `tests/server/test_chargen_dispatch.py` (and conftest isolation strategy — possibly session-scoped temp save directory).
  *Found by TEA during test verification.*

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/game/disposition.py` — added `Attitude` (StrEnum) and `Disposition` (value wrapper with clamping, `.attitude()` derivation, Pydantic v2 schema hook for raw-int coercion and bare-int serialization); kept `disposition_attitude()` helper for transition-era cutover tests.
- `sidequest-server/sidequest/game/session.py` — `Npc.disposition: int → Disposition` with `default_factory=Disposition`; `apply_world_patch` mutator rewritten to use `Disposition(before + delta)` (clamps internally) and emit `Attitude.value` (plain str) in OTEL span attrs; removed the inline import of the legacy helper.
- `sidequest-server/sidequest/server/dispatch/opening.py` — both `AuthoredNpc` render sites switched from `disposition_attitude(npc.initial_disposition)` to `Disposition(npc.initial_disposition).attitude().value`; dropped helper import.
- `sidequest-server/tests/integration/test_disposition_otel_wiring.py` — two assertions adapted `npc.disposition == N` → `int(npc.disposition) == N`.
- `sidequest-server/tests/integration/test_disposition_threshold_crossing.py` — `_apply_shift` return now unwraps with `int(...)`.
- `sidequest-server/tests/game/test_session.py` — four assertions adapted (`npc.disposition == 0|-20|10`).
- `sidequest-server/tests/game/test_world_materialization_authored_npcs.py` — two assertions adapted.
- `sidequest-server/tests/server/dispatch/test_monster_manual_inject.py` — two assertions adapted.

**Tests:** 5163/5163 passing on full server suite (`uv run pytest` from sidequest-server); the 40 new TEA tests for Story 50-10 all GREEN.
**Lint:** `uv run ruff check sidequest/ tests/` clean (Attitude migrated to `StrEnum` per UP042 — same str-subclass contract, cleaner formatting).
**Branch:** `feat/50-10-disposition-central-attitude-enum` (pushed to origin sidequest-server).

**Wiring verified:**
- `grep -rn "disposition_attitude(" sidequest/` returns only the helper's own definition in `disposition.py` — zero production call sites.
- `opening.py` and `session.py` import `Disposition` (not `disposition_attitude`).
- `world_materialization.py` and `monster_manual_inject.py` continue to call `Npc(disposition=int(...))` and rely on the Pydantic schema hook to coerce — no changes needed there, but the runtime `Npc.disposition` is now a `Disposition` everywhere.
- OTEL `SPAN_DISPOSITION_SHIFT` route extracts `before_attitude`/`after_attitude` as plain strings ("friendly"/"neutral"/"hostile") and `crossed: bool` — wire contract unchanged across the refactor (50-11 invariant preserved).

**Acceptance criteria status:**
- [x] `Attitude` enum exists with three variants (`FRIENDLY`, `NEUTRAL`, `HOSTILE`) with string values ("friendly" / "neutral" / "hostile")
- [x] `Disposition` class wraps an int, exposes `.attitude()` derivation, clamps to ±100
- [x] `Npc.disposition` field accepts `Disposition` instances; Pydantic round-trip (model_dump/model_validate AND model_dump_json/model_validate_json) preserves value and attitude
- [x] All production call sites (`opening.py`, `session.py`) use `.attitude()` instead of the helper
- [x] OTEL `SPAN_DISPOSITION_SHIFT` spans emit `before_attitude` / `after_attitude` with correct string values
- [x] Unit tests cover boundary cases (value=0, ±10, ±11, ±100, ±500 clamping)
- [x] Integration test verifies full NPC → attitude derivation → OTEL wiring through `apply_world_patch`
- [x] No test failures; existing tests adapted via `int(npc.disposition)` unwrap at the comparison site

**Handoff:** To Reviewer for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None warranting rework

Each AC was traced through to the code:

| AC | Code surface | Status |
|----|--------------|--------|
| AC1 — Attitude enum with three string variants | `disposition.py:39-52` (`class Attitude(StrEnum)`) | Aligned. `StrEnum` is the lint-clean Python 3.11+ form of the spec's `(str, Enum)`; same str-subclass behavior, str() returns value (eliminates a latent OTEL repr-leak risk). Dev's deviation log captures this. |
| AC2 — Disposition wraps int, .attitude(), clamps ±100 | `disposition.py:55-86` | Aligned. `__slots__` is a small memory win, no spec concern. |
| AC3 — Pydantic round-trip with raw-int backward compat | `disposition.py:88-129` (schema hook), `session.py:140` (field) | Aligned. Schema hook covers int / Disposition / dict inputs; serializes to bare int. Default_factory ensures instance independence. |
| AC4 — Production call sites use `.attitude()` | `session.py:1173-1174`, `opening.py:132,333` | Aligned. Two source-level wiring tests + one behavioral test enforce it. |
| AC5 — OTEL SPAN_DISPOSITION_SHIFT emits string attitudes | `session.py:1173-1174` extracts `.value` | Aligned. Wire contract unchanged; 50-11's `crossed` invariant preserved by band-identity comparison on Attitude. |
| AC6 — Unit tests for boundaries (0, ±10, ±11, ±100) | `test_disposition_attitude_enum.py` (23 tests) | Aligned. Also covers clamped-derivation edges (±500 → attitude on clamped value). |
| AC7 — Integration test for NPC → attitude → OTEL wiring | `test_disposition_call_site_migration.py::test_apply_patch_emits_attitude_strings_from_disposition_method` | Aligned. Exercises the session.py mutator path. Opening-scene path covered separately by pre-existing `test_opening_render_*.py` (still green after refactor). |
| AC8 — Existing tests still pass with minimal fixture-setup changes | 8 assertions adapted across 4 files | Aligned. Adaptation is uniform (`int(npc.disposition) == N`), Dev's deviation entry justifies refusing `__eq__(int)` on Python-equality-symmetry grounds. |
| Step 5 — Mark helper deprecated or remove | `disposition.py:132-145` retained without `DeprecationWarning`, docstring notes cutover-test dependency | Aligned. Spec explicitly allowed "keep if tests depend on it"; one cutover test (`test_disposition_threshold_crossing.py:338`) imports it to compare old-vocabulary against new-enum vocabulary. Future-cleanup path is one commit (rewrite that test, delete helper). |

**Architectural review notes (non-blocking, posterity):**

- The two-layer split (numeric `value` vs qualitative `attitude()`) is preserved exactly as ADR-020 prescribes, with the Rust newtype shape mirrored in Python. The narrator/world-state agent separation continues to hold: world-state writes `Disposition(int)` via the schema hook, narrator surfaces read `.attitude()`.
- The Pydantic schema's dict-input branch (`{"value": <int>}`) is defensive coding for a serialization shape the serializer never emits. Trivial — adds no maintenance cost.
- `session.py:1173` reconstructs `Disposition(before)` to derive `before_attitude` rather than capturing the attitude before mutating `npc.disposition`. Semantically identical; the chosen form makes the "before snapshot" explicit. Not worth a hand-back.

**Three Dev deviations reviewed:**

1. `StrEnum` vs `(str, Enum)` — accepted as Option A (spec implicitly updated; lint hygiene wins, no behavior change).
2. Helper retained without DeprecationWarning — accepted; falls within spec's allowed branch ("keep it in the module if any external tests still depend on it").
3. No `__eq__(int)`, 8 test sites adapted — accepted as Option A. The rationale (Python's equality reflexivity contract) is architecturally correct and produces a self-documenting test idiom (`int(npc.disposition) == 25` reads as "unwrap and compare").

**Decision:** Proceed to review. Hand off to TEA for verify (simplify + quality-pass).

## TEA Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 11

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | 3 high-confidence about duplication (opening.py NPC roster loop at 131,332; test fixtures duplicated across `test_disposition_otel_wiring.py` and `test_disposition_threshold_crossing.py`; same fixtures redefined in new `test_disposition_call_site_migration.py`), 1 low-confidence (attitude derivation pattern at opening.py:132,333 — recommended NO extraction). |
| simplify-quality | clean | 0 findings. Naming, layering, type safety, error handling, dead-code, OTEL coverage, and ADR-020 contract all verified. |
| simplify-efficiency | 8 findings | 1 in-scope but contradicts spec (remove `disposition_attitude` helper — Dev's deviation log explicitly retained it for `test_disposition_threshold_crossing.py:338`'s cutover assertion). 7 in regions of `session.py`/`opening.py` **outside** the 50-10 diff (`perspective_supplied` at 894, region-patch dedup at 1060, `_resolve_name_form` at 34, `_matches_*` predicates at 195, `_render_directive_*` overlap at 291, `apply_world_patch` wrapper at 1020). Out of story scope. |

**Applied:** 0 fixes
**Flagged for Review:** 0 medium-confidence findings within scope
**Noted:** 4 findings deferred (rationale below)
**Reverted:** 0

**Overall:** simplify: clean (within story scope)

### Findings Triage

- **opening.py NPC roster duplication (reuse, high)** — Lines 131-137 and 332-336 share the format `f"- {npc.name} ({npc.role}): {npc.appearance}, disposition: {attitude}"` plus a `history_seeds` branch. The duplication is **pre-existing** — 50-10 touched only line 132 and 333 (the attitude derivation call). Extracting `_render_npc_roster_lines(npcs)` would expand the diff into adjacent rendering code that has nothing to do with this story. Per CLAUDE.md's "Don't add features, refactor, or introduce abstractions beyond what the task requires" and user memory `feedback_boy_scout_bounded` (defer anything that goes exponential), this is the wrong moment. Deferred — recommend a follow-up cleanup story scoped to opening.py rendering deduplication.

- **Test fixture duplication across 3 files (reuse, high × 2)** — `_make_pc`, `_make_npc`, `_setup`, `_wait_for_event` exist in `test_disposition_otel_wiring.py` and `test_disposition_threshold_crossing.py` (pre-existing) and were re-copied into my new `test_disposition_call_site_migration.py`. Consolidating to a shared module (e.g., `tests/integration/_disposition_fixtures.py` plus updates in 3 files) is bounded but is a real cleanup operation rather than a simplify-pass tweak — two of the three files were not substantively touched by 50-10. Deferred to a follow-up story; flagged as TEA finding below.

- **`disposition_attitude` helper retention (efficiency, low)** — Dev explicitly logged this as a deviation with rationale: `test_disposition_threshold_crossing.py:338` imports the helper to assert the new `Attitude` enum's vocabulary matches the legacy helper's output. That's the cutover-contract test. Removing the helper would break that assertion. The Architect Assessment accepted Dev's reasoning. Confirmed correct — not applied.

- **Pre-existing efficiency findings in `session.py` and `opening.py` (efficiency, medium × 6)** — All point at code regions outside the 50-10 diff. `perspective_supplied`, region-patch dedup, `_resolve_name_form`, `_matches_*`, `_render_directive_*` overlap, and `apply_world_patch` wrapper are pre-existing patterns that this story didn't touch. Flagged for a future tech-debt sweep on `opening.py` and `session.py`.

### Quality Checks

- `uv run ruff check sidequest/ tests/` — **All checks passed!**
- `uv run pytest -q` — 5162 passed, 64 skipped. One pre-existing flaky test fails per run (a different one each run: `test_chargen_persist_and_play.py::test_chargen_confirm_persists_deduped_inventory` then `test_chargen_dispatch.py::test_caverns_delver_loadout_wired_into_snapshot`). Both pass in isolation. The flake is unrelated to 50-10 (these tests exercise chargen persistence + dispatch wiring, no disposition path). The 74 tests that touch disposition (including all 40 new TEA tests) pass cleanly in every run.

**Quality Checks:** All passing on the story-relevant test surface; lint clean. Pre-existing flakes flagged but non-blocking per memory `feedback_dont_revert_features`.

### Delivery Findings (verify phase — TEA inline)

- **Improvement** (non-blocking): Test fixtures for OTEL watcher setup duplicated across three files (`tests/integration/test_disposition_otel_wiring.py`, `tests/integration/test_disposition_threshold_crossing.py`, `tests/game/test_disposition_call_site_migration.py`). Affects all three (extract `_make_pc`, `_make_npc`, `_setup`, `_wait_for_event` into a shared `tests/_otel_fixtures.py` module). *Found by TEA during test verification.*
- **Improvement** (non-blocking): `opening.py` NPC roster rendering duplicated between `_render_directive_chassis` (lines 131-137) and `_render_directive_location` (lines 332-336) — pre-existing pattern, touched by 50-10 only at the attitude-derivation line. Affects `sidequest/server/dispatch/opening.py` (extract `_render_npc_roster_lines(npcs: list[AuthoredNpc]) -> list[str]`). *Found by TEA during test verification.*
- **Improvement** (non-blocking): Pre-existing flaky tests in `tests/server/test_chargen_*.py` — different test fails on each full-suite run, all pass in isolation. Likely test-ordering coupling through shared SQLite save state at `~/.sidequest/saves/`. Affects test isolation strategy (conftest cleanup, session DB scoping). Worth its own story; not in 50-10 scope. *Found by TEA during test verification.*

**Handoff:** To Reviewer for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 5163/5163 tests pass, ruff clean, zero smells, no flake hits |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 11 | confirmed 2, dismissed 5, deferred 4 |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 4, dismissed 1 |

**All received:** Yes (4 enabled, all returned; 5 disabled via `workflow.reviewer_subagents` settings)
**Total findings:** 9 confirmed, 6 dismissed (with rationale), 4 deferred

## Reviewer Assessment

**Verdict:** Approve. Follow-up commit `ede7e8e` addresses every confirmed finding; branch is ready to merge.

The diff is sound. Two HIGH-confidence rule violations were caught and fixed by Reviewer:

1. **[RULE] #9 `asyncio.get_event_loop()` inside `async _wait_for_event` (Python 3.12+ deprecation)** — fixed by switching to `asyncio.get_running_loop()`, matching the rest of the file. The pre-existing two integration test files (`test_disposition_otel_wiring.py`, `test_disposition_threshold_crossing.py`) use the same legacy pattern; flagged in delivery findings as a follow-up sweep.

2. **[RULE] A2 `disposition_attitude()` helper retained as dead production code (No Stubbing)** — Dev's deviation log justified retention for `test_disposition_threshold_crossing.py`'s cutover assertion, but on closer reading the cutover test already pinned the literal strings (`"neutral"` / `"friendly"`) on the next two lines, making the helper-import path redundant. Helper deleted from `disposition.py`; cutover test now compares against `Attitude.NEUTRAL.value` / `Attitude.FRIENDLY.value` directly. This supersedes Dev deviation #2.

Three HIGH-confidence comment-staleness findings (Story 50-10 framed as in-flight in its own delivery — `disposition.py` "Story 50-10 must not change them", `test_disposition_attitude_enum.py` "is being re-introduced", `test_disposition_threshold_crossing.py` claiming `disposition_attitude` is "the source of truth") were all corrected to present/past tense.

One HIGH-confidence test-quality finding (`test_npc_disposition_json_payload_contains_numeric_value` used substring matching on `json.dumps()` output — would pass coincidentally on any `15` in the encoded sub-object) was strengthened to exact type+value equality.

One MEDIUM-confidence test-quality finding (`test_two_disposition_instances_with_defaults_are_independent_objects` only asserted `a is not b`) was strengthened to mutate one instance and assert the other unchanged.

Reviewer also self-caught a **dead dict-input branch + silent fallback** in `Disposition.__get_pydantic_core_schema__` — the serializer always emits a bare int, so no code path produced the `{"value": <int>}` shape; additionally `v.get("value", 0)` was a silent fallback on missing key (No Silent Fallbacks rule). Dropped the dict branch entirely.

Added `__all__ = ["Attitude", "Disposition"]` to `disposition.py` to make the public surface explicit now that `disposition_attitude` is gone (rule #10).

### Confirmed Findings (9, all addressed in `ede7e8e`)

| Source | File | Finding | Fix |
|--------|------|---------|-----|
| [RULE] #9 | `tests/game/test_disposition_call_site_migration.py:163` | `asyncio.get_event_loop()` in async ctx, deprecated 3.10+, error 3.12+ | Switched to `asyncio.get_running_loop()` |
| [RULE] A2 | `sidequest/game/disposition.py:132` | `disposition_attitude()` is dead production code, retained for one test | Helper removed; cutover test rewritten to use `Attitude.*.value` directly |
| [RULE] #10 | `sidequest/game/disposition.py:1` | Missing `__all__` on public module | Added `__all__ = ["Attitude", "Disposition"]` |
| [SELF] | `sidequest/game/disposition.py:88-129` | Dead dict-input branch + silent fallback (`v.get("value", 0)` defaults to 0) | Dropped dict branch from schema; serializer emits bare int only |
| [DOC] | `sidequest/game/disposition.py:39` | "Story 50-10 must not change them" — self-referential post-delivery | Rewrote to present-tense statement |
| [DOC] | `tests/game/test_disposition_attitude_enum.py:18-23` | "is being re-introduced", "Story 50-10 must preserve" — future-tense | Past-tense rewrite |
| [DOC] | `tests/integration/test_disposition_threshold_crossing.py:18-23` | Claims `disposition_attitude` is "the source of truth" — actively false | Rewrote to name `Disposition.attitude()` as the contract |
| [TEST] | `tests/game/test_npc_disposition_field.py:801` | Substring match on `json.dumps()` — vacuous | Exact equality: `payload["disposition"] == 15` + `isinstance(..., int)` |
| [TEST] | `tests/game/test_disposition_attitude_enum.py:412` | Independence test only asserts `a is not b` | Added mutate-and-check: `a.value = 50; assert b.value == 0` |

### Dismissed Findings (6, with rationale)

| Source | Finding | Rationale for dismissal |
|--------|---------|------------------------|
| [TEST] | Set-equality `test_attitude_string_value_matches_otel_contract_exactly` redundant with individual value tests | Catches member-rename even if individual test names are renamed in sync. Cheap belt-and-suspenders. Keep. |
| [TEST] | `test_attitude_is_str_subclass_for_otel_serialization` equality lines duplicate individual tests | The `isinstance` check is unique; equality lines document str-subclass semantics in one place. Keep. |
| [TEST] | `test_attitude_enum_has_exactly_three_members` missing member-name assertion | Individual value tests cover member naming. Naming coverage is partitioned. |
| [TEST] | Source-text scan tests are implementation-coupled | Fragile-by-design — entire point is regression catch. Docstring updated to disclaim "the integration test required by CLAUDE.md". |
| [TEST] | ±101 over-clamp boundary explicit test missing | `Disposition(150)` and `Disposition(-150)` already cover the over-clamp path; band derivation at exact ±100 is covered. |
| [TEST] | No round-trip test at exact band boundary (value=10) | Pydantic int round-trip is value-preserving by construction; no precision-loss path for clamped ints. |

### Deferred Findings (4 — into Delivery Findings for future cleanup)

- Pre-existing `asyncio.get_event_loop()` usage in `test_disposition_otel_wiring.py` and `test_disposition_threshold_crossing.py`.
- No behavioral test asserts `"disposition: friendly"` in rendered opening directives from `opening.py` (A5 — opening.py wiring is via render tests that don't pin attitude string content).
- Test fixture duplication across 3 OTEL test files (TEA-flagged; concurred).
- `opening.py` NPC roster rendering duplication at lines 131-137 and 332-336 (TEA-flagged; concurred).

### Rule Compliance (lang-review checklist)

| Rule | Status | Note |
|------|--------|------|
| #1 Silent exception swallowing | Pass | No exception handling added; errors propagate. |
| #2 Mutable defaults | Pass | `Disposition()` default is immutable int; `Npc.disposition` uses `default_factory`. |
| #3 Type annotations at boundaries | Pass | All public methods annotated. |
| #4 Logging | Pass | No logging changes; OTEL span carries observability per project principle. |
| #5 Path handling | Pass | `read_text(encoding="utf-8")` used. |
| #6 Test quality | Pass (after fixes) | Vacuous substring test fixed; independence test strengthened. |
| #7 Resource leaks | Pass | `Span.open()` used as context manager. |
| #8 Unsafe deserialization | Pass | `json.loads()` only on trusted internal Pydantic output. |
| #9 Async pitfalls | Pass (after fix) | `get_event_loop()` → `get_running_loop()`. |
| #10 Import hygiene | Pass (after fix) | `__all__` added. |
| #11 Input validation | Pass | `Disposition.__init__` clamps; Pydantic schema rejects non-int. |
| #12 Dependency hygiene | Pass | No new dependencies. |
| #13 Fix-introduced regressions | Pass | Reviewer fixes re-scanned against #1-#12; no new violations. |
| CLAUDE.md A1 No Silent Fallbacks | Pass (after fix) | Dict-branch silent fallback removed. |
| CLAUDE.md A2 No Stubbing | Pass (after fix) | Dead helper removed. |
| CLAUDE.md A4 Verify Wiring | Pass | Behavioral wiring test for session.py path; opening.py covered by existing render tests. |
| CLAUDE.md A5 Wiring Test | Pass | Behavioral test present; deferred follow-up for opening.py string-content assertion. |
| CLAUDE.md A6 OTEL | Pass | `SPAN_DISPOSITION_SHIFT` enriched with Disposition-derived attitudes. |

### Delivery Findings (review phase — Reviewer inline)

- **Improvement** (non-blocking): Pre-existing `asyncio.get_event_loop()` usage in `tests/integration/test_disposition_otel_wiring.py:78` and `tests/integration/test_disposition_threshold_crossing.py:96` — same Python 3.12+ deprecation pattern. Affects both files (switch to `asyncio.get_running_loop()`). *Found by Reviewer during review.*
- **Improvement** (non-blocking): No behavioral test asserts rendered `"disposition: friendly"` string content from `opening.py`'s `_render_directive_chassis` / `_render_directive_location` paths. Affects `tests/server/test_opening_render_chassis.py`, `tests/server/test_opening_render_location.py` (add string-content assertions on rendered directive payload). *Found by Reviewer during review.*

**Verdict:** Approve. Hand off to SM for finish phase. Branch `feat/50-10-disposition-central-attitude-enum` ready for PR + merge.

## Design Deviations

None at setup time.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)

- **Added JSON-payload negative invariant beyond explicit AC**
  - Spec source: session 50-10, AC "Npc.disposition field accepts Disposition instances (verify Pydantic round-trip works)"
  - Spec text: "verify Pydantic round-trip works"
  - Implementation: Added `test_npc_disposition_json_payload_contains_numeric_value` which asserts the JSON form contains the numeric value and explicitly does NOT contain the string `"Disposition("` (Python repr leak). This is a stricter contract than the AC stated.
  - Rationale: Save files are SQLite JSON blobs (ADR-023); a Disposition that round-trips via Python repr instead of int would corrupt every save and be invisible to `model_validate` (since Pydantic would coerce the string back through the validator). Negative invariant catches this class of bug.
  - Severity: minor
  - Forward impact: locks Dev's serializer choice — must emit a JSON-native int or dict, never a repr string.
  - **Correction (Architect reconcile, 2026-05-13):** Reviewer commit `ede7e8e` superseded this test. Substring matching was vacuous (could pass coincidentally on any `"15"` substring in the JSON blob); the test was rewritten as `test_npc_disposition_json_payload_is_bare_integer` with exact type+value equality (`payload["disposition"] == 15` and `isinstance(payload["disposition"], int)`). The narrowed contract is "bare int", not "int or dict" — the dict-form serialization path was also removed from `Disposition.__get_pydantic_core_schema__`. The original deviation's forward-impact line ("must emit JSON-native int or dict") is now narrower: must emit bare int.

- **Wiring assertion is import-string-grep, not AST**
  - Spec source: session 50-10, Technical Approach Step 4 ("Replace all call sites")
  - Spec text: "Replace all `disposition_attitude(npc.disposition)` calls with `npc.disposition.attitude()`"
  - Implementation: `test_no_production_module_calls_disposition_attitude_helper` uses regex `\bdisposition_attitude\s*\(` rather than an AST walk.
  - Rationale: Regex is sufficient for the migration's blast radius (5 call sites across 2 files). AST would catch `getattr(module, "disposition_attitude")(...)` indirection, but no such pattern exists in this codebase. Regex is faster and gives clearer failure messages naming the file:line.
  - Severity: minor
  - Forward impact: if Dev introduces dynamic dispatch as a workaround to dodge the regex, the wiring test would pass while production still uses the helper. The behavioral test (`test_apply_patch_emits_attitude_strings_from_disposition_method`) is the safety net.

### Dev (implementation)

- **Used `StrEnum` instead of `class Attitude(str, Enum)`**
  - Spec source: session 50-10, Technical Approach Step 1
  - Spec text: `class Attitude(str, Enum):\n    FRIENDLY = "friendly"\n    NEUTRAL = "neutral"\n    HOSTILE = "hostile"`
  - Implementation: `class Attitude(StrEnum):` with the same three members.
  - Rationale: Python 3.11+ codebases trip on ruff's UP042 with the `(str, Enum)` form, which lints to `StrEnum`. Server runs Python 3.14 and lint is part of `pf check`. `StrEnum` is functionally equivalent for every TEA assertion (still `isinstance(x, str)`, still `Attitude.FRIENDLY == "friendly"`, still `Attitude.FRIENDLY.value == "friendly"`) and has a small ergonomic win — `str(Attitude.FRIENDLY)` returns `"friendly"` (in Python 3.11+ the `(str, Enum)` form returns the enum repr `"Attitude.FRIENDLY"`, which would silently corrupt OTEL span attrs if `.value` were ever omitted in span construction).
  - Severity: trivial
  - Forward impact: none — the wire contract is identical and 50-11/50-12/50-13 see no shape change.

- **Retained `disposition_attitude()` helper instead of marking deprecated or removing**
  - Spec source: session 50-10, Technical Approach Step 5
  - Spec text: "Mark `disposition_attitude` as deprecated or remove it once all call sites are migrated. Keep it in the module if any external tests still depend on it, but it should be unused in production."
  - Implementation: kept the helper function in `sidequest/game/disposition.py` with a docstring noting it's retained only for compatibility with cutover tests. No `DeprecationWarning` raised.
  - Rationale: `tests/integration/test_disposition_threshold_crossing.py:338` deliberately imports `disposition_attitude` to assert the new enum vocabulary matches the old helper's output — that's the cutover-contract test. Emitting a `DeprecationWarning` from `disposition_attitude` would make the test suite noisy without a clear winning consumer to migrate. The wiring tests in `test_disposition_call_site_migration.py` enforce zero production calls, which is the actual invariant the spec is protecting.
  - Severity: minor
  - Forward impact: low. If a future story (50-12 or 50-13) wants the helper gone entirely, that test's two assertions can switch to `Attitude.NEUTRAL.value` etc. and the helper can be deleted in one commit.
  - **Correction (Architect reconcile, 2026-05-13):** SUPERSEDED by Reviewer commit `ede7e8e`. The reviewer-rule-checker (subagent) found this retention violated CLAUDE.md "No Stubbing — Dead code is worse than no code." On re-reading the cutover test, the helper-call assertions at lines 346-347 of `test_disposition_threshold_crossing.py` were redundant with the literal-string assertions at lines 349-350. The Reviewer therefore: (a) deleted `disposition_attitude` from `disposition.py`; (b) rewrote the cutover test to compare against `Attitude.NEUTRAL.value` / `Attitude.FRIENDLY.value` directly; (c) renamed it `test_attitude_strings_match_attitude_enum_vocabulary`. Forward impact is now zero — the helper does not exist in any file, and the "follow-up to remove it" reservation from this entry's original Forward Impact is satisfied.

- **Did not define `Disposition.__eq__(int)` — adapted 8 test assertions instead**
  - Spec source: session 50-10 SM Assessment risk note ("Existing fixtures may set `npc.disposition = 5` as raw int; tests should cover both forms during migration")
  - Spec text: "tests should cover both forms during migration" (construction-side compat)
  - Implementation: Disposition accepts raw int construction (via Pydantic schema hook) but does not define `__eq__(int)`. The 8 test sites that compared `npc.disposition == N` were updated to `int(npc.disposition) == N`.
  - Rationale: Python's equality contract is reflexive — `Disposition.__eq__(int)` would return True but `int.__eq__(Disposition)` would not (Python forbids overriding built-in types' equality from the subclass side), leading to asymmetric comparisons that quietly differ depending on operand order. The explicit `int()` unwrap is honest, self-documenting, and survives future refactors of `Disposition`'s internals.
  - Severity: minor
  - Forward impact: every new test or production site that compares a Disposition with an int must use `int(...)` or `.value` at the call site. The pattern is consistent across all 10 touched files.

### TEA (test verification)

- **Did not apply 3 high-confidence simplify-reuse findings during verify**
  - Spec source: simplify workflow policy (`.pennyfarthing/agents/tea.md`, verify-workflow Step 5) — *(path corrected from original `pennyfarthing-dist/agents/tea.md` which does not exist in this clone; the orchestrator-side path is `.pennyfarthing/agents/tea.md`)*
  - Spec text: "For each finding with `confidence: high`: 1. Read the file at the specified line. 2. Apply the suggestion (edit the file). 3. Track what was changed and why."
  - Implementation: Deferred all three high-confidence findings (opening.py NPC roster duplication; test fixtures duplicated across 3 files × 2 findings) rather than applying. Captured them in the Delivery Findings instead.
  - Rationale: All three findings target **pre-existing duplication** that 50-10 touched only marginally (one-line attitude-derivation change at opening.py:132,333; a new test file that propagated the existing fixture pattern). Applying them would expand the diff into rendering logic and test infrastructure outside the story's scope. Per CLAUDE.md ("Don't add features, refactor, or introduce abstractions beyond what the task requires") and user memory `feedback_boy_scout_bounded` (defer anything that goes exponential), the simplify pass should not balloon a 3-point refactor into a multi-file infrastructure change. The findings are properly captured as upstream Delivery Findings for a dedicated cleanup story.
  - Severity: minor
  - Forward impact: a follow-up story (likely in epic 50 cleanup) should consolidate the OTEL watcher test fixtures and extract `_render_npc_roster_lines` in opening.py. Until then, the duplication remains visible to future Architects/TEAs as documented tech debt.

### Architect (reconcile)

- **Removed dead dict-input branch + silent fallback from `Disposition.__get_pydantic_core_schema__`**
  - Spec source: session 50-10, Technical Approach Step 3 ("Handle Pydantic serialization/deserialization with a custom serializer if needed to keep round-trip compatibility")
  - Spec text: "Handle Pydantic serialization/deserialization with a custom serializer if needed to keep round-trip compatibility."
  - Implementation: Dev's original `__get_pydantic_core_schema__` accepted three input shapes — `Disposition`, raw `int`, and a dict `{"value": <int>}` with a `v.get("value", 0)` silent default. Reviewer (commit `ede7e8e`) dropped the dict branch entirely; the serializer always emits a bare int, so no code path produced the dict shape, making the dict-arm dead code. Additionally `v.get("value", 0)` was a silent fallback (key missing → silently substitutes 0), violating CLAUDE.md "No Silent Fallbacks". The current schema accepts only `Disposition` or `int` and serializes to bare int.
  - Rationale: The dict branch was defensive coding for a serialization shape that doesn't exist in this codebase. Removing it eliminates a silent-fallback path and shrinks the schema to its actual contract (int ↔ Disposition). The save-file JSON path produces bare ints, so the dict branch could never fire on real input.
  - Severity: minor
  - Forward impact: future serializers (e.g., if a different output format is added) must not assume the dict input shape is supported. Any persistence migration that produces a non-int form must validate explicitly rather than relying on the dict-arm coercion.

- **Added `__all__ = ["Attitude", "Disposition"]` to `sidequest/game/disposition.py`**
  - Spec source: `.pennyfarthing/gates/lang-review/python.md`, rule #10 (Import hygiene)
  - Spec text: "Missing `__all__` on public modules — unclear public API"
  - Implementation: Reviewer (commit `ede7e8e`) added an `__all__` declaration listing the two public types. Deliberately excludes the now-removed `disposition_attitude` and the closure `_from_int`, making the public surface explicit.
  - Rationale: Without `__all__`, a future `from sidequest.game.disposition import *` would pull in private helpers and Pydantic-internal symbols. Declaring it locks the contract and makes the helper-removal in this same commit load-bearing — any future re-introduction would have to explicitly re-export.
  - Severity: trivial
  - Forward impact: callers should keep using direct imports (`from sidequest.game.disposition import Attitude, Disposition`). No behavior change for any existing code.

- **Fixed `asyncio.get_event_loop()` → `asyncio.get_running_loop()` in `test_disposition_call_site_migration.py:163-164`**
  - Spec source: `.pennyfarthing/gates/lang-review/python.md`, rule #9 (Async/await pitfalls)
  - Spec text: "Blocking calls (`time.sleep`, `requests.get`, file I/O) inside async functions — use `aiohttp`, `aiofiles`, or `asyncio.to_thread()`" (rule #9 covers async pitfalls broadly; `asyncio.get_event_loop()` from within a running loop is deprecated in Python 3.10+ and errors in Python 3.12+)
  - Implementation: TEA copy-pasted `_wait_for_event` from `test_disposition_otel_wiring.py` / `test_disposition_threshold_crossing.py`, both of which use the legacy `asyncio.get_event_loop().time()` pattern. Reviewer (commit `ede7e8e`) hoisted the call to a local `loop = asyncio.get_running_loop()` at the top of the function and used it for both `loop.time()` reads. The two pre-existing integration tests still use the legacy pattern and are captured as a non-blocking Delivery Finding for a follow-up sweep.
  - Rationale: Server runs Python 3.14.4 where `get_event_loop()` from within an async function emits a `DeprecationWarning` and will raise `RuntimeError` if no current loop is set. `get_running_loop()` is the contract-correct equivalent and is the pattern used elsewhere in the same file (`_setup` already calls `watcher_hub.bind_loop(asyncio.get_running_loop())`).
  - Severity: minor
  - Forward impact: all future async tests added to this file (and tests elsewhere) should use `asyncio.get_running_loop()`. The two pre-existing files flagged in Delivery Findings should be migrated when convenient.

- **Stale-future-tense docstring sweep (3 files)**
  - Spec source: CLAUDE.md ("Don't explain WHAT the code does, since well-named identifiers already do that. Don't reference the current task, fix, or callers ... since those belong in the PR description and rot as the codebase evolves.")
  - Spec text: "those belong in the PR description and rot as the codebase evolves"
  - Implementation: Three module docstrings authored during in-flight phases framed 50-10 as still-pending work that "must preserve" / "must not change" / "will centralise" the contract. After 50-10 itself merged, those forward-looking imperatives are stale-by-construction. Reviewer (commit `ede7e8e`) rewrote them in past/present tense: `disposition.py` ("Story 50-10 restored…"), `test_disposition_attitude_enum.py` ("These tests lock the wire contract"), `test_disposition_threshold_crossing.py` ("Story 50-10 centralised…, the source of truth is now `Disposition.attitude()`"). Architect (this reconcile) further corrected the stale `_production_py_files` docstring in `test_disposition_call_site_migration.py:54-58` which still claimed the helper "may still define" itself; the function no longer exists.
  - Rationale: Docstrings that frame the in-flight story as future work become actively misleading the moment the story merges. CLAUDE.md's comment-hygiene rule explicitly flags task-tense framing as rot.
  - Severity: trivial
  - Forward impact: none. Comment-only changes.

- **Spec source paths in TEA/Dev deviation entries**
  - Spec source: this session file's existing TEA verify entry referenced `pennyfarthing-dist/agents/tea.md`; that path does not exist in this clone. The actual path is `.pennyfarthing/agents/tea.md` (a symlink that resolves into the installed pennyfarthing distribution).
  - Spec text: `pennyfarthing-dist/agents/tea.md` (referenced by TEA verify entry #1)
  - Implementation: Annotated the existing entry with the corrected path inline; did not delete the original reference per the spec-reconcile guidance ("annotate it with a correction note rather than deleting it").
  - Rationale: A spec source that names a non-existent path fails the spec-reconcile field-completeness check. The annotation preserves audit history while pointing future readers at the correct file.
  - Severity: trivial
  - Forward impact: none. Affects only the audit trail.