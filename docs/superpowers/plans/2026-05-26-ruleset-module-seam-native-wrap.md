# Ruleset Module Seam + Native-Wrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a pluggable `RulesetModule` seam in the server and prove it by relocating the existing confrontation/dial turn resolution into a `NativeRulesetModule` with zero behavior change.

**Architecture:** A genre pack declares `ruleset:` in `rules.yaml` (default `native`). At pack load the loader resolves the slug to a registered `RulesetModule` (fail loud if unregistered). The confrontation dispatch pipeline routes every resolution call (`find_confrontation`, `stat_modifier`, `compute_dc`, `apply_beat`, `resolve_damage`) through the bound module instead of calling free functions directly. The existing logic *moves into* `NativeRulesetModule` — there is exactly one resolution path, no `None` branch, no surviving inline copy, no fallback.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `uv` (run via `cd sidequest-server && uv run pytest`).

**Scope:** This is **Spec 0** of the pluggable-SRD design (`docs/superpowers/specs/2026-05-26-pluggable-srd-ruleset-modules-design.md`). The SWN and B/X modules are separate plans. The `RulesetModule` interface defined here is **minimal** — only the five resolution operations the native turn already performs (YAGNI: character-shape, advancement, and the per-module narrator contract are added when the SWN plan needs them).

---

## File Structure

**New package — `sidequest/game/ruleset/`** (a module is behavior, not data; it lives next to the game engine it drives):

- Create: `sidequest-server/sidequest/game/ruleset/__init__.py` — re-exports the public surface (`RulesetModule`, `get_ruleset_module`, `UnknownRulesetError`).
- Create: `sidequest-server/sidequest/game/ruleset/base.py` — the `RulesetModule` ABC (the interface contract) + `UnknownRulesetError`.
- Create: `sidequest-server/sidequest/game/ruleset/native.py` — `NativeRulesetModule`, the relocated current behavior.
- Create: `sidequest-server/sidequest/game/ruleset/registry.py` — slug → singleton-instance resolution, fail-loud on unknown.

**Modified:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` — add `ruleset: str = "native"` to `RulesConfig` (`extra="forbid"` model change).
- Modify: `sidequest-server/sidequest/genre/loader.py` — validate the bound module is registered at load time (fail loud).
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py` — route resolution through the module; delete the relocated free functions.

**Tests:**
- Create: `sidequest-server/tests/game/ruleset/test_registry.py`
- Create: `sidequest-server/tests/game/ruleset/test_native_module.py`
- Create: `sidequest-server/tests/game/ruleset/test_loader_binding.py`
- Create: `sidequest-server/tests/game/ruleset/test_dispatch_routing.py` (the wiring test)

> **Note on test data:** Per `feedback_no_content_coupled_tests`, none of these tests load live `genre_packs/*`. They build `RulesConfig` / `BeatDef` / `ConfrontationDef` fixtures inline.

---

## Task 1: Characterize the current resolution math

Lock the existing behavior of `_stat_modifier` and `_compute_dc` before moving them, so the relocation is provably behavior-preserving.

**Files:**
- Test: `sidequest-server/tests/game/ruleset/test_native_module.py`
- Read for reference: `sidequest-server/sidequest/server/dispatch/dice.py:127-153`

- [ ] **Step 1: Read the current functions to copy their exact behavior**

Read `sidequest-server/sidequest/server/dispatch/dice.py:127-153`. Confirm:
- `_stat_modifier(stats, stat_check)` returns `(stats.get(<canonical stat>, 10) - 10) // 2` (confirm the exact key-canonicalization and default).
- `_compute_dc(beat)` returns `max(10, min(30, 10 + abs(beat.base) * 2))`.

- [ ] **Step 2: Write characterization tests against the current free functions**

```python
# tests/game/ruleset/test_native_module.py
import pytest
from sidequest.server.dispatch.dice import _stat_modifier, _compute_dc
from sidequest.genre.models.rules import BeatDef


@pytest.mark.parametrize("score,expected", [(10, 0), (12, 1), (8, -1), (18, 4), (3, -4), (20, 5)])
def test_stat_modifier_dnd_formula(score, expected):
    assert _stat_modifier({"STR": score}, "STR") == expected


def test_stat_modifier_missing_stat_defaults_to_10():
    assert _stat_modifier({}, "STR") == 0


@pytest.mark.parametrize("base,expected_dc", [(0, 10), (1, 12), (5, 20), (10, 30), (15, 30)])
def test_compute_dc_clamped(base, expected_dc):
    beat = BeatDef(id="b", label="B", kind="strike", base=base, stat_check="STR")
    assert _compute_dc(beat) == expected_dc
```

- [ ] **Step 3: Run to verify they pass against current code**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_native_module.py -v`
Expected: PASS (these characterize behavior that exists today).

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/tests/game/ruleset/test_native_module.py
git commit -m "test(ruleset): characterize current stat_modifier and compute_dc"
```

---

## Task 2: Define the `RulesetModule` interface

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/base.py`
- Test: `sidequest-server/tests/game/ruleset/test_registry.py`

- [ ] **Step 1: Write the ABC**

```python
# sidequest/game/ruleset/base.py
"""The RulesetModule seam — a genre pack binds one module that owns turn resolution.

Spec 0 surface only: the five resolution operations the native turn already performs.
Character-shape / advancement / narrator-contract surfaces are added when the SWN
module plan needs them (YAGNI).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from sidequest.genre.models.rules import BeatDef, ConfrontationDef


class UnknownRulesetError(ValueError):
    """Raised at pack load when rules.ruleset names no registered module. Fail loud."""


class RulesetModule(ABC):
    """Authority for how a turn resolves. One bound per session; no fallback between modules."""

    #: registry key, also the value authors write in rules.yaml `ruleset:`
    slug: str

    @abstractmethod
    def find_confrontation(
        self, confrontations: list[ConfrontationDef], encounter_type: str
    ) -> ConfrontationDef | None:
        """Locate the ConfrontationDef governing this encounter type."""

    @abstractmethod
    def stat_modifier(self, stats: dict[str, int], stat_check: str) -> int:
        """The check modifier this ruleset derives from an ability/skill value."""

    @abstractmethod
    def compute_dc(self, beat: BeatDef) -> int:
        """The difficulty class / target number this ruleset assigns a beat."""

    @abstractmethod
    def apply_beat(self, *, encounter, actor, beat, outcome, turn, edge_resolver, damage_resolver):
        """Apply a resolved beat's deltas to the encounter. Returns the engine ApplyResult."""

    @abstractmethod
    def resolve_damage(self, *, beat, actor_core, pack):
        """Resolve the DamageSpec for a strike beat (weapon or override), or None."""
```

- [ ] **Step 2: Run import smoke**

Run: `cd sidequest-server && uv run python -c "from sidequest.game.ruleset.base import RulesetModule, UnknownRulesetError; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/base.py
git commit -m "feat(ruleset): define RulesetModule ABC (Spec 0 resolution surface)"
```

---

## Task 3: Implement `NativeRulesetModule` (relocate behavior)

Move the small free functions into the module; delegate the large engine functions (`apply_beat`, damage resolution) which stay in place this pass. Behavior is identical.

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/native.py`
- Test: `sidequest-server/tests/game/ruleset/test_native_module.py` (extend)
- Read for reference: `sidequest-server/sidequest/server/dispatch/dice.py:127-153`, `sidequest/game/beat_kinds.py` (`apply_beat`), `sidequest/server/dispatch/damage_roll.py` (`resolve_damage_spec_from_beat_and_actor`)

- [ ] **Step 1: Write the native module, copying the exact formulas from Task 1 Step 1**

```python
# sidequest/game/ruleset/native.py
"""NativeRulesetModule — the current SideQuest dial/confrontation turn, behind the seam.

This is ADR-033's confrontation engine, relocated. It is the resolution model for packs
that bind `ruleset: native` (and, later, the Fate family). It is NOT a fallback for other
modules — it is one module among several, selected explicitly by the pack.
"""
from __future__ import annotations

from sidequest.game.beat_kinds import apply_beat as _engine_apply_beat
from sidequest.game.encounter import find_confrontation_def
from sidequest.game.ruleset.base import RulesetModule
from sidequest.genre.models.rules import BeatDef, ConfrontationDef
from sidequest.server.dispatch.damage_roll import resolve_damage_spec_from_beat_and_actor


def _canonical_stat_value(stats: dict[str, int], stat_check: str) -> int:
    # Mirror dice.py _stat_modifier's lookup exactly (confirm key handling in Task 1 Step 1).
    return stats.get(stat_check, 10)


class NativeRulesetModule(RulesetModule):
    slug = "native"

    def find_confrontation(self, confrontations: list[ConfrontationDef], encounter_type: str) -> ConfrontationDef | None:
        return find_confrontation_def(confrontations, encounter_type)

    def stat_modifier(self, stats: dict[str, int], stat_check: str) -> int:
        return (_canonical_stat_value(stats, stat_check) - 10) // 2

    def compute_dc(self, beat: BeatDef) -> int:
        return max(10, min(30, 10 + abs(beat.base) * 2))

    def apply_beat(self, *, encounter, actor, beat, outcome, turn, edge_resolver, damage_resolver):
        return _engine_apply_beat(
            encounter, actor, beat, outcome,
            turn=turn, edge_resolver=edge_resolver, damage_resolver=damage_resolver,
        )

    def resolve_damage(self, *, beat, actor_core, pack):
        return resolve_damage_spec_from_beat_and_actor(beat, actor_core, pack)
```

> If Task 1 Step 1 revealed `_stat_modifier` canonicalizes the stat key (e.g. via a `Stat` enum) or uses a different default, reproduce that exactly in `_canonical_stat_value` and `stat_modifier`. The characterization tests in Step 2 guard it.

- [ ] **Step 2: Extend the characterization tests to target the module**

```python
# tests/game/ruleset/test_native_module.py  (append)
from sidequest.game.ruleset.native import NativeRulesetModule

_NATIVE = NativeRulesetModule()


@pytest.mark.parametrize("score,expected", [(10, 0), (12, 1), (8, -1), (18, 4), (3, -4), (20, 5)])
def test_native_stat_modifier_matches_legacy(score, expected):
    assert _NATIVE.stat_modifier({"STR": score}, "STR") == _stat_modifier({"STR": score}, "STR")
    assert _NATIVE.stat_modifier({"STR": score}, "STR") == expected


@pytest.mark.parametrize("base", [0, 1, 5, 10, 15])
def test_native_compute_dc_matches_legacy(base):
    beat = BeatDef(id="b", label="B", kind="strike", base=base, stat_check="STR")
    assert _NATIVE.compute_dc(beat) == _compute_dc(beat)
```

- [ ] **Step 3: Run to verify the module matches legacy**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_native_module.py -v`
Expected: PASS — module output equals the legacy free functions.

- [ ] **Step 4: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/native.py sidequest-server/tests/game/ruleset/test_native_module.py
git commit -m "feat(ruleset): NativeRulesetModule relocates current dial resolution"
```

---

## Task 4: The registry (fail-loud resolution)

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/registry.py`
- Create: `sidequest-server/sidequest/game/ruleset/__init__.py`
- Test: `sidequest-server/tests/game/ruleset/test_registry.py`

- [ ] **Step 1: Write the failing registry test**

```python
# tests/game/ruleset/test_registry.py
import pytest
from sidequest.game.ruleset import get_ruleset_module, UnknownRulesetError
from sidequest.game.ruleset.native import NativeRulesetModule


def test_native_resolves():
    assert isinstance(get_ruleset_module("native"), NativeRulesetModule)


def test_native_is_singleton():
    assert get_ruleset_module("native") is get_ruleset_module("native")


def test_unknown_ruleset_fails_loud():
    with pytest.raises(UnknownRulesetError) as exc:
        get_ruleset_module("swn")  # not registered until the SWN plan lands
    assert "swn" in str(exc.value)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError` / `ImportError` (registry not written yet).

- [ ] **Step 3: Write the registry and package init**

```python
# sidequest/game/ruleset/registry.py
from __future__ import annotations

from sidequest.game.ruleset.base import RulesetModule, UnknownRulesetError
from sidequest.game.ruleset.native import NativeRulesetModule

# Modules are stateless behavior → safe singletons. New modules register here as their plans land.
_REGISTRY: dict[str, RulesetModule] = {
    NativeRulesetModule.slug: NativeRulesetModule(),
}


def get_ruleset_module(slug: str) -> RulesetModule:
    """Resolve a registered ruleset module. Fails loud — never returns a default/fallback."""
    module = _REGISTRY.get(slug)
    if module is None:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise UnknownRulesetError(f"Unknown ruleset {slug!r}; registered rulesets: {known}")
    return module
```

```python
# sidequest/game/ruleset/__init__.py
from sidequest.game.ruleset.base import RulesetModule, UnknownRulesetError
from sidequest.game.ruleset.registry import get_ruleset_module

__all__ = ["RulesetModule", "UnknownRulesetError", "get_ruleset_module"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/registry.py sidequest-server/sidequest/game/ruleset/__init__.py sidequest-server/tests/game/ruleset/test_registry.py
git commit -m "feat(ruleset): fail-loud registry (native registered; unknown raises)"
```

---

## Task 5: Add `ruleset` to `RulesConfig` and validate at load

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (`RulesConfig`, near line 596-660)
- Modify: `sidequest-server/sidequest/genre/loader.py` (after `GenrePack` construction)
- Test: `sidequest-server/tests/game/ruleset/test_loader_binding.py`

- [ ] **Step 1: Write the failing tests for the field + load-time validation**

```python
# tests/game/ruleset/test_loader_binding.py
import pytest
from sidequest.genre.models.rules import RulesConfig
from sidequest.game.ruleset import get_ruleset_module, UnknownRulesetError


def test_ruleset_defaults_to_native():
    rules = RulesConfig()
    assert rules.ruleset == "native"
    assert get_ruleset_module(rules.ruleset).slug == "native"


def test_explicit_ruleset_parses():
    rules = RulesConfig(ruleset="native")
    assert rules.ruleset == "native"


def test_unknown_ruleset_rejected_at_bind():
    rules = RulesConfig(ruleset="nonsense")
    with pytest.raises(UnknownRulesetError):
        get_ruleset_module(rules.ruleset)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_loader_binding.py -v`
Expected: FAIL — `RulesConfig` has no `ruleset` field (and `extra="forbid"` would reject it).

- [ ] **Step 3: Add the field to `RulesConfig`**

In `sidequest-server/sidequest/genre/models/rules.py`, inside `RulesConfig` (the `extra="forbid"` model), add near the core-tuning fields:

```python
    ruleset: str = "native"  # bound RulesetModule slug (ADR pluggable-SRD). Default = current dial engine.
```

- [ ] **Step 4: Add fail-loud validation at pack load**

In `sidequest-server/sidequest/genre/loader.py`, immediately after the `GenrePack(...)` is constructed (the site identified at ~loader load chain), add:

```python
    from sidequest.game.ruleset import get_ruleset_module  # local import avoids a load-time cycle

    # Fail loud at load if the pack names an unregistered ruleset (no silent default).
    get_ruleset_module(pack.rules.ruleset)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_loader_binding.py -v`
Expected: PASS.

- [ ] **Step 6: Run the pack-model regression to confirm no live pack broke**

Run: `cd sidequest-server && uv run pytest tests/genre -v`
Expected: PASS — every existing pack defaults `ruleset` to `"native"`, which is registered.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/genre/models/rules.py sidequest-server/sidequest/genre/loader.py sidequest-server/tests/game/ruleset/test_loader_binding.py
git commit -m "feat(ruleset): RulesConfig.ruleset field + fail-loud bind at pack load"
```

---

## Task 6: Route dispatch through the bound module; delete the inline copies

This is the wrap. After it, `dice.py` calls the module for resolution and the relocated free functions no longer exist — one path, no fallback.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py` (call sites ~290, ~318-319, ~429, ~502-510; delete `_stat_modifier` ~127-143 and `_compute_dc` ~146-153)
- Test: `sidequest-server/tests/game/ruleset/test_dispatch_routing.py`

- [ ] **Step 1: Read the call sites and `dispatch_dice_throw` signature**

Read `sidequest-server/sidequest/server/dispatch/dice.py:237-520`. Note that `pack` is already a parameter of `dispatch_dice_throw`, so the module is reachable as `get_ruleset_module(pack.rules.ruleset)` without a signature change.

- [ ] **Step 2: Write the wiring test (the integration test that proves routing)**

```python
# tests/game/ruleset/test_dispatch_routing.py
"""Wiring test: dispatch resolves through the bound RulesetModule, not free functions."""
from unittest.mock import patch

from sidequest.game.ruleset.native import NativeRulesetModule


def test_dispatch_uses_bound_module_for_stat_and_dc():
    # Spy on the native module's resolution methods; assert dispatch calls them.
    real = NativeRulesetModule()
    calls = {"stat_modifier": 0, "compute_dc": 0}

    def spy_stat(stats, stat_check):
        calls["stat_modifier"] += 1
        return real.stat_modifier(stats, stat_check)

    def spy_dc(beat):
        calls["compute_dc"] += 1
        return real.compute_dc(beat)

    spy = NativeRulesetModule()
    spy.stat_modifier = spy_stat  # type: ignore[method-assign]
    spy.compute_dc = spy_dc  # type: ignore[method-assign]

    with patch("sidequest.server.dispatch.dice.get_ruleset_module", return_value=spy):
        from tests.game.ruleset._dispatch_fixture import resolve_one_combat_beat  # see Step 3
        outcome = resolve_one_combat_beat()

    assert calls["stat_modifier"] >= 1, "dispatch did not route stat_modifier through the module"
    assert calls["compute_dc"] >= 1, "dispatch did not route compute_dc through the module"
    assert outcome.encounter_resolved in (True, False)  # smoke: a real outcome came back
```

- [ ] **Step 3: Write the fixture that drives one combat beat**

Build an inline `RulesConfig` (with a single `combat` `ConfrontationDef` and one `strike` beat), a minimal `StructuredEncounter`, and minimal stats — then call `dispatch_dice_throw` with a forced face. Reuse existing test builders if `tests/` already has confrontation fixtures; otherwise:

```python
# tests/game/ruleset/_dispatch_fixture.py
# Construct the smallest real inputs dispatch_dice_throw accepts and invoke it.
# Mirror an existing dispatch test in tests/server/dispatch/ for the exact constructor
# arguments (encounter, pack, snapshot, broadcast no-op callbacks).
...
```

> Before writing this fixture from scratch, check `tests/server/dispatch/` for an existing `dispatch_dice_throw` test and copy its setup. Reuse beats re-deriving the call shape.

- [ ] **Step 4: Run to verify the wiring test fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_dispatch_routing.py -v`
Expected: FAIL — dispatch still calls the inline `_stat_modifier` / `_compute_dc`, so the spies see zero calls.

- [ ] **Step 5: Route the call sites through the module**

In `dispatch_dice_throw`, near the top (after `pack` is in scope):

```python
    from sidequest.game.ruleset import get_ruleset_module
    ruleset = get_ruleset_module(pack.rules.ruleset)
```

Then replace the resolution sites:

```python
    # was: find_confrontation_def(pack.rules.confrontations, encounter.encounter_type)
    cdef = ruleset.find_confrontation(pack.rules.confrontations, encounter.encounter_type)

    # was: _stat_modifier(character_stats, beat.stat_check)
    modifier = ruleset.stat_modifier(character_stats, beat.stat_check)

    # was: _compute_dc(beat)
    difficulty = ruleset.compute_dc(beat)

    # was: _resolve_damage_spec_from_beat_and_actor(beat, actor_core, pack)
    damage_spec = ruleset.resolve_damage(beat=beat, actor_core=actor_core, pack=pack)

    # was: apply_beat(encounter, actor, beat, resolved.outcome, turn=..., edge_resolver=..., damage_resolver=...)
    apply_result = ruleset.apply_beat(
        encounter=encounter, actor=actor, beat=beat, outcome=resolved.outcome,
        turn=round_number, edge_resolver=snapshot.find_creature_core, damage_resolver=damage_resolver_fn,
    )
```

- [ ] **Step 6: Delete the relocated free functions (no surviving inline copy)**

Delete `_stat_modifier` (dice.py ~127-143) and `_compute_dc` (~146-153). Their behavior now lives only in `NativeRulesetModule`. Update the Task 1 characterization test imports to pull from the module (the legacy-comparison assertions that import `_stat_modifier`/`_compute_dc` are removed; keep the absolute-value parametrized assertions against `_NATIVE`).

- [ ] **Step 7: Run the wiring test + the characterization tests**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/ -v`
Expected: PASS — dispatch routes through the module; module math unchanged.

- [ ] **Step 8: Run the existing dispatch suite to prove zero behavior change**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch -v`
Expected: PASS — the wrap is behavior-preserving for combat resolution.

- [ ] **Step 9: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/dice.py sidequest-server/tests/game/ruleset/
git commit -m "feat(ruleset): route confrontation dispatch through bound module; delete inline resolution"
```

---

## Task 7: Full-suite gate

**Files:** none (verification only)

- [ ] **Step 1: Run the server suite**

Run: `cd sidequest-server && uv run pytest`
Expected: PASS, excluding the known pre-existing env-coupled failures (namegen-audit, pack-validator, dogfight-smoke, prompt-compaction live-tree — see `reference_server_test_gate_composition`). Confirm no *new* failures versus `develop`.

- [ ] **Step 2: Run lint**

Run: `cd sidequest-server && uv run ruff check sidequest/game/ruleset sidequest/server/dispatch/dice.py sidequest/genre`
Expected: clean.

- [ ] **Step 3: Confirm no orphaned references to the deleted functions**

Run: `cd sidequest-server && grep -rn "_stat_modifier\|_compute_dc" sidequest/ tests/`
Expected: zero hits in `sidequest/` (production); any test hits are the intended module-based assertions only.

---

## Self-Review (completed)

**Spec coverage (against Spec 0 of the design doc):**
- §3 RulesetModule seam → Tasks 2, 4 (interface + registry).
- §3 `ruleset:` binding → Task 5.
- §3.3 "exactly one module, no fallback, fail loud on unknown" → Task 4 (registry raises), Task 5 (load-time bind), Task 6 (inline copies deleted — no second path).
- §5 step 1 (define seam) → Tasks 2, 4, 5. §5 step 2 (native-wrap, zero behavior change, characterization-tested) → Tasks 1, 3, 6, 7.
- §4.2 (dials = native module's turn) → Task 3 (`NativeRulesetModule` *is* the relocated dial engine).

**Out of scope here (correctly deferred to later plans):** SWN/B/X module bodies, the per-module narrator tool contract (§7), character-shape/advancement interface surfaces (added when SWN needs them), and any `rules.yaml` content edits to live packs (they default to `native`).

**Placeholder scan:** The only `...` is the `_dispatch_fixture.py` body in Task 6 Step 3, deliberately deferred to copying an existing dispatch test's setup (a real, located source — `tests/server/dispatch/`) rather than inventing constructor args blind. Flagged inline.

**Type consistency:** `RulesetModule` method names (`find_confrontation`, `stat_modifier`, `compute_dc`, `apply_beat`, `resolve_damage`) are identical across base.py, native.py, the registry tests, and the dispatch routing in Task 6. `slug` is the single registry key used in `rules.yaml`, the registry dict, and `get_ruleset_module`.
