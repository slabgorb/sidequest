# Ruleset Seam Cleanup — Debt 1 (mirror-math routing) + Debt 2 (layer inversion) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the two follow-up debts left by the pluggable-SRD Spec 0 merge (PR #466): (1) route the three hand-copied DC/stat-modifier formulas through the bound `RulesetModule`, and (2) relocate two pure-game functions out of the `server.dispatch.*` layer so `game/ruleset/native.py` no longer imports `server`.

**Architecture:** Debt 2 (relocation) goes first — it removes the `game→server` import inversion and gives the game layer a clean home, mechanically, with no behavior change. Debt 1 (routing) then threads the bound `RulesetModule` into the opposed-check / save resolvers so the *opponent* and *defender* modifiers honor the same bound ruleset the player's dispatch path uses. A new minimal ABC method `score_modifier(score: int) -> int` is the enabler: the opposed/save resolvers already hold a *resolved* ability score, so they need the score→modifier mapping (not the lookup-bundled `stat_modifier`). `NativeRulesetModule.stat_modifier` is refactored to delegate to `score_modifier`, collapsing all three formula copies to one canonical implementation.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`uv run pytest`, parallel `-n auto` by default), `uv`. Run from `sidequest-server/`.

**Scope discovered during planning (read before starting):**
- `resolve_save` (`sidequest/game/saves.py`) has **no production caller** — only `tests/game/test_saves.py` exercises it. Threading the ruleset through it is forward-looking dedup (the B/X save resolver is built ahead of being wired); it is still in scope because its private `_ability_modifier` copy is one of the three duplicated formulas the goal collapses.
- `resolve_opposed_check` is called from **one production site** (`narration_apply.py:3820`) and **~15 test sites across 4 files** (`test_opposed_check.py`, `test_opposed_check_distribution.py`, `test_opposed_check_fixed_roll.py`, `test_opposed_check_numerical_advantage.py`). Adding a required `ruleset` keyword param means every one of those call sites is updated. This is mechanical but is the bulk of the diff. A default value is **forbidden** (project hard rule: no silent fallbacks) — the param is required and explicit.

**Out of scope (do not touch):** the dispatch path (`dispatch_dice_throw`) — already routed in Spec 0. The `BeatDef`/`ConfrontationDef`/`DamageSpec` models. Any `rules.yaml` content. The SWN/BX module bodies.

---

## File Structure

**Debt 2 — relocation (new game-layer homes):**
- Modify: `sidequest-server/sidequest/game/encounter.py` — gains `find_confrontation_def` (moved in).
- Create: `sidequest-server/sidequest/game/damage.py` — new module owning `resolve_damage_spec_from_beat_and_actor`.
- Modify: `sidequest-server/sidequest/server/dispatch/confrontation.py` — `find_confrontation_def` removed (other names stay).
- Modify: `sidequest-server/sidequest/server/dispatch/damage_roll.py` — `resolve_damage_spec_from_beat_and_actor` removed (other names stay).
- Modify (importers of `find_confrontation_def`, single pass): `sidequest/game/ruleset/native.py`, `sidequest/handlers/connect.py`, `sidequest/handlers/yield_action.py`, `sidequest/server/dispatch/encounter_lifecycle.py`, `sidequest/server/narration_apply.py` (3 inline imports), `sidequest/server/session_helpers.py`, `sidequest/server/websocket_session_handler.py`, plus tests `tests/fixtures/dogfight_playtest_encounter.py`, `tests/server/dispatch/test_sealed_letter_dispatch_integration.py`, `tests/server/test_confrontation_dispatch.py`.
- Modify (importers of `resolve_damage_spec_from_beat_and_actor`): `sidequest/game/ruleset/native.py`, `sidequest/server/narration_apply.py`.
- Delete: the duplicate `_find_confrontation_def` in `sidequest/server/session_helpers.py:1221` + its re-export in `sidequest/server/session_handler.py:334,364`.

**Debt 1 — routing (ABC + resolvers):**
- Modify: `sidequest-server/sidequest/game/ruleset/base.py` — add `score_modifier` abstractmethod.
- Modify: `sidequest-server/sidequest/game/ruleset/native.py` — implement `score_modifier`; `stat_modifier` delegates to it.
- Modify: `sidequest-server/sidequest/game/opposed_check.py` — `resolve_opponent_modifier` + `resolve_opposed_check` gain a `ruleset` param; delete `_ability_modifier`.
- Modify: `sidequest-server/sidequest/game/saves.py` — `resolve_save` gains a `ruleset` param; delete `_ability_modifier`.
- Modify: `sidequest-server/sidequest/server/narration_apply.py` — resolve `ruleset` once in `_resolve_opposed_check_branch`; pass it down; replace `_opposed_dc` calls with `ruleset.compute_dc`; delete `_opposed_dc`.
- Modify (tests): `tests/game/test_opposed_check.py`, `tests/game/test_opposed_check_distribution.py`, `tests/game/test_opposed_check_fixed_roll.py`, `tests/game/test_opposed_check_numerical_advantage.py`, `tests/game/test_saves.py`.

> **Test-data rule (per `feedback_no_content_coupled_tests`):** no test loads live `genre_packs/*`. Tests construct a `NativeRulesetModule()` directly and pass it as `ruleset=`.

---

## Task 1: Relocate `find_confrontation_def` to `game/encounter.py` (Debt 2A)

Pure move — the function only depends on `ConfrontationDef` (a genre model). Behavior is identical; only the import path changes. There are existing behavior tests in `tests/server/test_confrontation_dispatch.py` that will guard correctness once their import path is updated.

**Files:**
- Modify: `sidequest/game/encounter.py` (add function)
- Modify: `sidequest/server/dispatch/confrontation.py:81-95` (remove function)
- Modify: 7 production importers + 3 test importers (listed below)
- Delete: `sidequest/server/session_helpers.py:1221` (`_find_confrontation_def`) + `sidequest/server/session_handler.py:334,364`

- [ ] **Step 1: Read the function and confirm its only dependency**

Read `sidequest/server/dispatch/confrontation.py:81-95`. Confirm `find_confrontation_def(defs: list[ConfrontationDef], encounter_type: str) -> ConfrontationDef | None` uses only `ConfrontationDef`. Confirm `sidequest/game/encounter.py` can import `ConfrontationDef` from `sidequest.genre.models.rules` without a cycle (encounter.py is already in the game layer; genre.models is below it). Run:

```bash
cd sidequest-server && uv run python -c "import sidequest.game.encounter; from sidequest.genre.models.rules import ConfrontationDef; print('ok')"
```
Expected: `ok`.

- [ ] **Step 2: Add the function to `game/encounter.py`**

Append to `sidequest/game/encounter.py` (ensure `from sidequest.genre.models.rules import ConfrontationDef` is imported at module top — add it if absent):

```python
def find_confrontation_def(
    defs: list[ConfrontationDef],
    encounter_type: str,
) -> ConfrontationDef | None:
    """Return the ConfrontationDef whose ``confrontation_type`` equals ``encounter_type``.

    Exact string match. Returns ``None`` when no def matches; callers MUST handle
    the miss (CLAUDE.md: no silent fallback — caller decides whether to error).
    """
    for d in defs:
        if d.confrontation_type == encounter_type:
            return d
    return None
```

- [ ] **Step 3: Remove it from `confrontation.py` and update that module's importers within the server layer**

Delete the `find_confrontation_def` definition from `sidequest/server/dispatch/confrontation.py:81-95`. Do NOT remove the other functions (`build_confrontation_payload`, `resolve_recipient_pc`, `build_clear_confrontation_payload`, `resolve_magic_confrontation`) — they stay.

- [ ] **Step 4: Update every importer to the new path (single pass)**

For each call site, change the import source from `sidequest.server.dispatch.confrontation` to `sidequest.game.encounter`. The call signature is unchanged.

Production (update the import line in each; several are function-local inline imports):
- `sidequest/game/ruleset/native.py:19` — change to `from sidequest.game.encounter import find_confrontation_def` (this is the line that removes the layer inversion for this function).
- `sidequest/handlers/connect.py:1455` (inline import)
- `sidequest/handlers/yield_action.py:60` (inline import)
- `sidequest/server/dispatch/encounter_lifecycle.py:22` (top-level import)
- `sidequest/server/narration_apply.py:429, 1457, 2437` (three inline imports)
- `sidequest/server/session_helpers.py:761` (inline import)
- `sidequest/server/websocket_session_handler.py:1813` (inline import)

Tests:
- `tests/fixtures/dogfight_playtest_encounter.py:40`
- `tests/server/dispatch/test_sealed_letter_dispatch_integration.py:465`
- `tests/server/test_confrontation_dispatch.py:23`

Find any you missed:
```bash
cd sidequest-server && grep -rn "from sidequest.server.dispatch.confrontation import" sidequest/ tests/ | grep find_confrontation_def
```
Expected after edits: zero hits.

- [ ] **Step 5: Delete the dead duplicate `_find_confrontation_def`**

In `sidequest/server/session_helpers.py`, delete the `_find_confrontation_def(pack, confrontation_type)` definition at line 1221 (it is a duplicate of `find_confrontation_def` and has no live caller — only a dead re-export). In `sidequest/server/session_handler.py`, remove the `_find_confrontation_def,` import (line 334) and the `"_find_confrontation_def",` entry from `__all__` (line 364). Confirm nothing else references it:
```bash
cd sidequest-server && grep -rn "_find_confrontation_def" sidequest/ tests/
```
Expected: zero hits.

- [ ] **Step 6: Run the confrontation + dispatch tests**

```bash
cd sidequest-server && uv run pytest tests/server/test_confrontation_dispatch.py tests/server/dispatch tests/game/ruleset -q
```
Expected: PASS (behavior unchanged; only import paths moved).

- [ ] **Step 7: Import-cycle + lint check**

```bash
cd sidequest-server && uv run python -c "import sidequest.server.dispatch.dice, sidequest.game.ruleset, sidequest.server.narration_apply; print('ok')"
uv run ruff check sidequest/game/encounter.py sidequest/server/dispatch/confrontation.py sidequest/server/session_helpers.py sidequest/server/session_handler.py
```
Expected: `ok` then `All checks passed!`.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(ruleset): relocate find_confrontation_def to game/encounter; drop dead duplicate"
```

---

## Task 2: Relocate `resolve_damage_spec_from_beat_and_actor` to new `game/damage.py` (Debt 2B)

This is the second half of the layer-inversion fix. The function is pure game logic (depends only on `DamageSpec`, `GenrePack`, `BeatDef`, all genre models). The server-dispatch utilities that build dice requests (`damage_request_from_spec`, `generate_server_faces`, `_DAMAGE_THROW_PARAMS`) stay in `damage_roll.py`.

**Files:**
- Create: `sidequest/game/damage.py`
- Modify: `sidequest/server/dispatch/damage_roll.py:120-200` (remove function)
- Modify: `sidequest/game/ruleset/native.py:20`, `sidequest/server/narration_apply.py:3717`

- [ ] **Step 1: Read the function body and confirm dependencies**

Read `sidequest/server/dispatch/damage_roll.py:120-200`. Confirm `resolve_damage_spec_from_beat_and_actor(*, beat: BeatDef, actor_core: object | None, pack: GenrePack | None) -> DamageSpec | None` imports only `DamageSpec` (`sidequest.genre.models.inventory`), `GenrePack` (`sidequest.genre.models.pack`), `BeatDef` (`sidequest.genre.models.rules`), and stdlib `logging`. Note any module-private helpers it calls — if it calls helpers defined in `damage_roll.py`, those helpers must move with it (or be duplicated into `damage.py`). Report which helpers (if any) it depends on before moving.

- [ ] **Step 2: Create `game/damage.py` with the relocated function**

Create `sidequest/game/damage.py`. Copy the EXACT function body from Step 1 (including any private helpers it calls), with this module header:

```python
"""Damage-spec resolution — pure game logic for deriving a strike beat's DamageSpec.

Relocated from server.dispatch.damage_roll (it had no server dependencies) so the
game layer — including ruleset modules — can resolve damage without importing server.
The dice-request/face-rolling utilities (damage_request_from_spec, generate_server_faces)
remain in server.dispatch.damage_roll; only the pure resolution logic lives here.
"""
from __future__ import annotations

import logging

from sidequest.genre.models.inventory import DamageSpec
from sidequest.genre.models.pack import GenrePack
from sidequest.genre.models.rules import BeatDef

logger = logging.getLogger(__name__)


# <paste resolve_damage_spec_from_beat_and_actor and any private helpers it depends on, verbatim>
```

- [ ] **Step 3: Remove it from `damage_roll.py`**

Delete `resolve_damage_spec_from_beat_and_actor` (and only the helpers that moved with it in Step 2) from `sidequest/server/dispatch/damage_roll.py`. Keep `damage_request_from_spec`, `generate_server_faces`, `_DAMAGE_THROW_PARAMS`. If `damage_roll.py` no longer uses `BeatDef`/`DamageSpec` after the removal, drop those now-unused imports (ruff will flag them in Step 6).

- [ ] **Step 4: Update the two importers**

- `sidequest/game/ruleset/native.py:20` — change to `from sidequest.game.damage import resolve_damage_spec_from_beat_and_actor` (removes the second layer inversion).
- `sidequest/server/narration_apply.py:3717` — the inline import `... import resolve_damage_spec_from_beat_and_actor as _resolve_dmg_spec` → change source to `sidequest.game.damage`.

Confirm none missed:
```bash
cd sidequest-server && grep -rn "resolve_damage_spec_from_beat_and_actor" sidequest/ tests/
```
Expected: definition in `game/damage.py`, calls in `native.py` + `narration_apply.py`, zero references to the old `damage_roll` path.

- [ ] **Step 5: Confirm the inversion is gone**

```bash
cd sidequest-server && grep -n "server.dispatch" sidequest/game/ruleset/native.py
```
Expected: zero hits — `native.py` no longer imports from `server`. Update or remove the now-stale layer-inversion comment block in `native.py` (the comment added in Spec 0 explaining the inversion) since the inversion no longer exists.

- [ ] **Step 6: Tests + lint + import smoke**

```bash
cd sidequest-server && uv run pytest tests/game/ruleset tests/server/dispatch tests/server/test_damage_dice_request.py -q
uv run python -c "import sidequest.game.damage, sidequest.game.ruleset, sidequest.server.dispatch.dice; print('ok')"
uv run ruff check sidequest/game/damage.py sidequest/game/ruleset/native.py sidequest/server/dispatch/damage_roll.py sidequest/server/narration_apply.py
```
Expected: PASS, `ok`, `All checks passed!`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(ruleset): relocate resolve_damage_spec to game/damage; native no longer imports server"
```

---

## Task 3: Add `score_modifier` to the ABC; `NativeRulesetModule.stat_modifier` delegates to it

This is the enabler for Debt 1. The opposed-check and save resolvers hold a *resolved* score and need the score→modifier mapping; the dispatch path holds a stats dict and needs lookup+mapping. `score_modifier(score)` is the shared primitive; `stat_modifier` = lookup + `score_modifier`.

**Files:**
- Modify: `sidequest/game/ruleset/base.py`
- Modify: `sidequest/game/ruleset/native.py`
- Test: `tests/game/ruleset/test_native_module.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/game/ruleset/test_native_module.py`:

```python
@pytest.mark.parametrize("score,expected", [(10, 0), (12, 1), (8, -1), (18, 4), (3, -4), (20, 5)])
def test_native_score_modifier(score, expected):
    assert _NATIVE.score_modifier(score) == expected


def test_stat_modifier_delegates_to_score_modifier():
    # stat_modifier must equal score_modifier applied to the looked-up score
    assert _NATIVE.stat_modifier({"STR": 18}, "STR") == _NATIVE.score_modifier(18) == 4
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd sidequest-server && uv run pytest tests/game/ruleset/test_native_module.py -k score_modifier -v
```
Expected: FAIL — `NativeRulesetModule` has no `score_modifier`.

- [ ] **Step 3: Add the abstractmethod to the ABC**

In `sidequest/game/ruleset/base.py`, add to `RulesetModule` (place it just above `stat_modifier`):

```python
    @abstractmethod
    def score_modifier(self, score: int) -> int:
        """The check modifier this ruleset derives from a resolved ability score.

        ``stat_modifier`` is lookup-then-this; callers that already hold a resolved
        score (opposed-check opponent, saving throws) use this directly.
        """
```

- [ ] **Step 4: Implement in native and refactor `stat_modifier` to delegate**

In `sidequest/game/ruleset/native.py`, replace the `stat_modifier` method with:

```python
    def score_modifier(self, score: int) -> int:
        return (score - 10) // 2

    def stat_modifier(self, stats: dict[str, int], stat_check: str) -> int:
        score = _stat_score(stats, stat_check)
        if score is None:
            return 0
        return self.score_modifier(score)
```

- [ ] **Step 5: Run the full ruleset suite**

```bash
cd sidequest-server && uv run pytest tests/game/ruleset/test_native_module.py -v
```
Expected: PASS — new tests green, all prior equivalence/characterization tests still green (delegation is behavior-preserving).

- [ ] **Step 6: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/game/ruleset && uv run ruff format sidequest/game/ruleset
git add sidequest/game/ruleset/base.py sidequest/game/ruleset/native.py tests/game/ruleset/test_native_module.py
git commit -m "feat(ruleset): add RulesetModule.score_modifier; stat_modifier delegates to it"
```

---

## Task 4: Route `_opposed_dc` through `ruleset.compute_dc` (Debt 1B — easy half)

`pack` is already in scope in `_resolve_opposed_check_branch`; resolve the module once and swap the three `_opposed_dc` calls.

**Files:**
- Modify: `sidequest/server/narration_apply.py` (`_resolve_opposed_check_branch` ~3658; `_opposed_dc` def ~3528; calls 3864, 3865, 3943)

- [ ] **Step 1: Confirm `pack` is non-None in the branch**

Read `sidequest/server/narration_apply.py:3658-3720`. Confirm `_resolve_opposed_check_branch` either declares `pack: GenrePack` non-optional or raises early when `pack is None`. If it can proceed with `pack=None`, note where, because `get_ruleset_module(pack.rules.ruleset)` requires a pack — and the project rule is to fail loud, not to fall back. (It already calls `resolve_opponent_modifier`/damage resolution that need pack, so a None pack is not a supported path here.)

- [ ] **Step 2: Resolve the module once near the top of the branch**

After `pack` is confirmed in scope (and after the existing early guards), add:

```python
    from sidequest.game.ruleset import get_ruleset_module

    ruleset = get_ruleset_module(pack.rules.ruleset)
```

(Use a function-local import to match the existing inline-import style in this file, OR add it to the module-top imports if that's cleaner — `narration_apply.py` is in the server layer so importing `game.ruleset` is the correct direction.)

- [ ] **Step 3: Replace the three `_opposed_dc` calls**

```python
    # was: player_dc = _opposed_dc(player_beat)
    player_dc = ruleset.compute_dc(player_beat)
    # was: opponent_dc = _opposed_dc(opponent_beat)
    opponent_dc = ruleset.compute_dc(opponent_beat)
    # was (companion loop, ~3943): c_dc = _opposed_dc(c_beat)
    c_dc = ruleset.compute_dc(c_beat)
```

- [ ] **Step 4: Delete `_opposed_dc`**

Delete the `_opposed_dc` function (`narration_apply.py:3528-3537`). Confirm no other references:
```bash
cd sidequest-server && grep -rn "_opposed_dc" sidequest/ tests/
```
Expected: zero hits.

- [ ] **Step 5: Run the opposed-check + narration tests**

```bash
cd sidequest-server && uv run pytest tests/game/test_opposed_check.py tests/server -k "opposed or narration" -q
```
Expected: PASS (native `compute_dc` == old `_opposed_dc` for the same beat; `_opposed_dc` had a `getattr(beat,"base",1)` default — confirm test beats always carry `base`, which `BeatDef` guarantees, so behavior is identical).

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/narration_apply.py
git commit -m "feat(ruleset): route opposed-check DC through bound module.compute_dc; delete _opposed_dc"
```

---

## Task 5: Thread `ruleset` into `resolve_opponent_modifier` + `resolve_opposed_check`; delete `opposed_check._ability_modifier` (Debt 1A — opposed path)

`resolve_opponent_modifier` holds a resolved score; route it through `ruleset.score_modifier`. It is called by `resolve_opposed_check`, so that function also gains a `ruleset` param, which ripples to its one production caller and ~15 test call sites.

**Files:**
- Modify: `sidequest/game/opposed_check.py` (`resolve_opponent_modifier` ~181-199, `resolve_opposed_check` ~202-270, `_ability_modifier` 83-89)
- Modify: `sidequest/server/narration_apply.py` (call sites 3820 `resolve_opposed_check`, 3909 `resolve_opponent_modifier`)
- Test: `tests/game/test_opposed_check.py`, `tests/game/test_opposed_check_distribution.py`, `tests/game/test_opposed_check_fixed_roll.py`, `tests/game/test_opposed_check_numerical_advantage.py`

- [ ] **Step 1: Add the `ruleset` param to `resolve_opponent_modifier` and route through `score_modifier`**

In `sidequest/game/opposed_check.py`, import the type and add the param:

```python
from sidequest.game.ruleset.base import RulesetModule  # at module top (game->game, no inversion)
```

```python
def resolve_opponent_modifier(*, actor: EncounterActor, cdef: Any, stat_check: str, ruleset: RulesetModule) -> int:
    # ... existing score lookup unchanged (_stat_score_from_actor / _stat_score_from_cdef_default) ...
    return ruleset.score_modifier(score)
```

- [ ] **Step 2: Add the `ruleset` param to `resolve_opposed_check` and pass it down**

`resolve_opposed_check` calls `resolve_opponent_modifier` twice (lines ~262, ~267). Add `ruleset: RulesetModule` as a required keyword param to its signature and forward it:

```python
    player_mod = resolve_opponent_modifier(actor=..., cdef=..., stat_check=..., ruleset=ruleset)
    opponent_mod = resolve_opponent_modifier(actor=..., cdef=..., stat_check=..., ruleset=ruleset)
```

- [ ] **Step 3: Delete `_ability_modifier` from opposed_check.py**

Delete `_ability_modifier` (lines 83-89). Its only non-test caller was `resolve_opponent_modifier` (now routed). Tests import it directly — those are updated in Step 5.

- [ ] **Step 4: Update the production caller in narration_apply.py**

`_resolve_opposed_check_branch` already resolved `ruleset` in Task 4 Step 2. Pass it to both call sites:

```python
    # line ~3820
    roll_result = resolve_opposed_check(..., ruleset=ruleset)
    # line ~3909 (companion)
    c_mod = resolve_opponent_modifier(..., ruleset=ruleset)
```

- [ ] **Step 5: Update the test call sites**

In the four `tests/game/test_opposed_check*.py` files:
- Add `from sidequest.game.ruleset.native import NativeRulesetModule` and a module-level `_RULESET = NativeRulesetModule()`.
- Pass `ruleset=_RULESET` to every `resolve_opposed_check(...)` and `resolve_opponent_modifier(...)` call (~15 + 2 sites).
- In `tests/game/test_opposed_check.py`, the assertions that imported `_ability_modifier` (lines 27, 119, 295, 296) must change: replace `_ability_modifier(score)` with `_RULESET.score_modifier(score)` (identical value), and remove the now-broken `_ability_modifier` import.

Find every site needing the new kwarg:
```bash
cd sidequest-server && grep -rn "resolve_opposed_check(\|resolve_opponent_modifier(" tests/game/
```

- [ ] **Step 6: Run the opposed-check suite**

```bash
cd sidequest-server && uv run pytest tests/game/test_opposed_check.py tests/game/test_opposed_check_distribution.py tests/game/test_opposed_check_fixed_roll.py tests/game/test_opposed_check_numerical_advantage.py -q
```
Expected: PASS — modifiers identical (native `score_modifier` == old `_ability_modifier`).

- [ ] **Step 7: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/game/opposed_check.py sidequest/server/narration_apply.py tests/game/
git add sidequest/game/opposed_check.py sidequest/server/narration_apply.py tests/game/test_opposed_check*.py
git commit -m "feat(ruleset): thread bound module into opposed-check modifiers; delete _ability_modifier copy"
```

---

## Task 6: Thread `ruleset` into `resolve_save`; delete `saves._ability_modifier` (Debt 1A — save path)

`resolve_save` is prod-unwired (test-only) but holds the third copy of the modifier formula. Thread the module so the save modifier honors the bound ruleset.

**Files:**
- Modify: `sidequest/game/saves.py` (`resolve_save` ~101-160, `_ability_modifier` 29, `_defender_score` 34 stays)
- Test: `tests/game/test_saves.py`

- [ ] **Step 1: Add the `ruleset` param and route through `score_modifier`**

In `sidequest/game/saves.py`:

```python
from sidequest.game.ruleset.base import RulesetModule  # module top
```

Add `ruleset: RulesetModule` as a required keyword param to `resolve_save`, and at line ~156:

```python
    mod = 0 if ability is None else ruleset.score_modifier(_defender_score(defender, ability))
```

- [ ] **Step 2: Delete `saves._ability_modifier`**

Delete `_ability_modifier` (saves.py:29). Keep `_defender_score` (it does the score lookup and is still used). Confirm:
```bash
cd sidequest-server && grep -rn "_ability_modifier" sidequest/ tests/
```
Expected: zero hits anywhere (all three copies now gone).

- [ ] **Step 3: Update the test callers**

In `tests/game/test_saves.py`, add `from sidequest.game.ruleset.native import NativeRulesetModule`, a `_RULESET = NativeRulesetModule()`, and pass `ruleset=_RULESET` to every `resolve_save(...)` call (7 sites: lines ~79, 98, 112, 127, 136, 152, 171, 196 — grep to confirm).

```bash
cd sidequest-server && grep -n "resolve_save(" tests/game/test_saves.py
```

- [ ] **Step 4: Run the saves suite**

```bash
cd sidequest-server && uv run pytest tests/game/test_saves.py -q
```
Expected: PASS — modifier values identical.

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/game/saves.py tests/game/test_saves.py
git add sidequest/game/saves.py tests/game/test_saves.py
git commit -m "feat(ruleset): thread bound module into save resolver; delete last _ability_modifier copy"
```

---

## Task 7: Full-suite gate + orphan/inversion sweep

**Files:** none (verification only)

- [ ] **Step 1: Confirm all duplication and inversion is gone**

```bash
cd sidequest-server
echo "ability_modifier copies (expect 0):"; grep -rn "_ability_modifier" sidequest/ tests/ || echo none
echo "_opposed_dc (expect 0):"; grep -rn "_opposed_dc" sidequest/ tests/ || echo none
echo "_find_confrontation_def (expect 0):"; grep -rn "_find_confrontation_def" sidequest/ tests/ || echo none
echo "native imports server (expect 0):"; grep -n "server.dispatch" sidequest/game/ruleset/native.py || echo none
echo "old find_confrontation_def path (expect 0):"; grep -rn "server.dispatch.confrontation import find_confrontation_def" sidequest/ tests/ || echo none
echo "old resolve_damage_spec path (expect 0):"; grep -rn "server.dispatch.damage_roll import resolve_damage_spec_from_beat_and_actor" sidequest/ tests/ || echo none
```
Expected: `none` for every check.

- [ ] **Step 2: Lint the whole touched surface**

```bash
cd sidequest-server && uv run ruff check sidequest/game sidequest/server/narration_apply.py sidequest/server/dispatch sidequest/server/session_helpers.py sidequest/server/session_handler.py
```
Expected: `All checks passed!`.

- [ ] **Step 3: Full suite — confirm no new failures vs the `develop` baseline**

```bash
cd sidequest-server && uv run pytest -q
```
Expected: PASS except the known pre-existing content/env-coupled failures (namegen-audit, pack-validator [missing asset dirs], dogfight-smoke, scene-harness, xdist-setup, api-contract — see `reference_server_test_gate_composition`). Confirm zero *new* failures versus `develop`. If a failure looks new, verify it is pre-existing by running that file against `develop` **in the main checkout** (not a `/tmp` worktree — the `/tmp` location skips content-coupled tests).

---

## Self-Review (completed)

**Spec coverage (against the two debts in `project_ruleset_seam_spec0`):**
- Debt 2A (find_confrontation_def relocation) → Task 1. Debt 2B (resolve_damage_spec relocation) → Task 2. Both remove the `game→server` inversion (verified in Task 2 Step 5 + Task 7 Step 1).
- Debt 1 routing → Tasks 3–6: `score_modifier` enabler (3), `_opposed_dc`→`compute_dc` (4), `_ability_modifier` opposed path (5) and save path (6). All three formula copies deleted (Task 7 Step 1 asserts zero).
- Bonus dedup the user approved: `session_helpers._find_confrontation_def` (Task 1 Step 5), `saves._ability_modifier` (Task 6).

**User decisions honored:** "thread the module through now" → Tasks 5 + 6 thread `ruleset` into `resolve_opponent_modifier`/`resolve_opposed_check`/`resolve_save` (required param, no default — no silent fallback). "encounter.py + new damage.py, single-pass, no shim" → Tasks 1 + 2 update every importer in one pass with no re-export shim.

**Placeholder scan:** The only deliberately deferred detail is "any private helpers `resolve_damage_spec` depends on" in Task 2 Step 1 — the executor must read the body and move helpers with it; this is a located, bounded read (a single function in one file), not an open-ended TODO. Flagged inline.

**Type/name consistency:** `score_modifier(score: int) -> int` is identical across base.py (abstractmethod), native.py (impl), the opposed/save call sites, and the tests. `ruleset` keyword param is the same name everywhere it's threaded. `get_ruleset_module(pack.rules.ruleset)` is the same resolution pattern already used in `dispatch_dice_throw`.

**Risk note for the executor:** Task 5 is the largest diff (≈17 test call sites gain `ruleset=`). It is mechanical but easy to miss a site — the grep in Step 5 enumerates them; do not hand-count.
