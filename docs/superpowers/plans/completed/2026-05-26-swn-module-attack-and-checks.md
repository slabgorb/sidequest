# SWN Module — Attack, Skill Checks & Saves Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a faithful `SwnRulesetModule` as a second `RulesetModule` so an SWN attack resolves d20 + attack-bonus + skill + attribute-mod **vs Armor Class** and deals SWN weapon-dice HP damage, and SWN **2d6 skill checks** and **d20 saving throws** resolve through a new server-initiated (non-beat) dice path — with the existing `native` module proven byte-for-byte unchanged.

**Architecture:** Builds on the **already-implemented** Spec-0 seam (`sidequest/game/ruleset/{base,native,registry}.py`, commits `217b12d`→`6419b75`). This plan (a) generalizes the resolution surface so the bound module computes the attack **modifier** and **target number** with access to the *attacker and target* (not just a beat), letting SWN read target AC where native reads a beat DC; (b) adds an `armor_class` field to `CreatureCore`; (c) adds `SwnRulesetModule` with the SWN modifier curve and config-driven class/skill/save constants; (d) builds a non-beat `dispatch_check` path for skill checks and saves, triggered by a new client message + handler, reusing the live `DiceRequestPayload`/`DiceResultPayload` round-trip and OTEL spans.

**Tech Stack:** Python 3.12, pydantic v2, pytest, `uv` (run via `cd sidequest-server && uv run pytest`). All server-side; no UI repo changes in this plan.

**Precondition (verify before starting):** `sidequest/game/ruleset/native.py` exists and `RulesConfig` has a `ruleset: str = "native"` field. If not, the Spec-0 plan (`2026-05-26-ruleset-module-seam-native-wrap.md`) must land first.

**Source of truth for SWN constants:** `~/Documents/DriveThruRPG/Sine Nomine Publishing/Stars Without Number_ Revised Edition _Free Version_/StarsWithoutNumberRevised-FreeEdition-122917.pdf`. Where this plan cannot cite a number from memory it is marked `[SRD→config]` and sourced by a transcription task — never fabricated.

**Scope boundary:** This plan is the **engine + resolution + wire path**. It does NOT re-author `space_opera` content to SWN (that is a later content plan), does NOT design the per-module narrator tool contract (later plan — the non-beat check path here is triggered by an explicit client message so it has a real consumer without the narrator), and does NOT populate the `initiative` order (turn-model plan). Tests build SWN fixtures inline per `feedback_tests_not_point_at_content` — no test loads `genre_packs/*`.

---

## File Structure

**New:**
- `sidequest-server/sidequest/game/ruleset/swn.py` — `SwnRulesetModule`: the SWN modifier curve, attack/check/save resolution, config-driven constants.
- `sidequest-server/sidequest/game/ruleset/resolution.py` — small shared value types for the generalized surface (`AttackRollParams`, `CheckRollParams`). Lives in the ruleset package because both modules produce them.
- `sidequest-server/sidequest/server/dispatch/check.py` — `dispatch_check`: the non-beat dice path for skill checks and saves.
- `sidequest-server/sidequest/handlers/check_throw.py` — handler wiring a client `CHECK_THROW` message to `dispatch_check`.
- Tests: `tests/game/ruleset/test_swn_module.py`, `tests/game/ruleset/test_native_unchanged.py`, `tests/server/dispatch/test_check_dispatch.py`, `tests/handlers/test_check_throw_handler.py`.

**Modified:**
- `sidequest/game/ruleset/base.py` — add the generalized resolution methods to the `RulesetModule` ABC.
- `sidequest/game/ruleset/native.py` — implement the new methods over existing native logic (behavior-preserving).
- `sidequest/game/ruleset/registry.py` — register `SwnRulesetModule`.
- `sidequest/game/creature_core.py` — add `armor_class: int = 10` to `CreatureCore`.
- `sidequest/server/dispatch/dice.py` — route the attack roll setup through the generalized methods.
- `sidequest/genre/models/rules.py` — add the optional `swn:` config block to `RulesConfig`.
- `sidequest/protocol/` — add `CheckThrowPayload` + `CHECK_THROW` message type.

---

## Part A — Character shape: Armor Class

### Task 1: Add `armor_class` to `CreatureCore`

SWN attacks roll against ascending AC; `CreatureCore` has no AC today (only flat `mitigation` on items). Add a first-class field, defaulting to SWN unarmored AC 10.

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py` (`CreatureCore`, ~line 99-162)
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/game/ruleset/test_swn_module.py
from sidequest.game.creature_core import CreatureCore, HpPool


def _core(*, name="Mara", ac=10, **kw):
    return CreatureCore(
        name=name, description="d", personality="p",
        hp=HpPool(current=8, max=8, base_max=8), armor_class=ac, **kw,
    )


def test_creature_core_has_armor_class_default_10():
    core = CreatureCore(name="x", description="d", personality="p")
    assert core.armor_class == 10


def test_creature_core_armor_class_settable():
    assert _core(ac=15).armor_class == 15
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -v`
Expected: FAIL — `extra="forbid"` rejects `armor_class` (model has no such field).

- [ ] **Step 3: Add the field**

In `CreatureCore` (the `model_config = {"extra": "forbid"}` model), add beside `hp`:

```python
    armor_class: int = 10  # SWN ascending AC; unarmored = 10. Seeded from content armor.
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -v`
Expected: PASS.

- [ ] **Step 5: Run the creature-core regression**

Run: `cd sidequest-server && uv run pytest tests/game -k creature -v`
Expected: PASS — additive field with a default breaks nothing.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/creature_core.py sidequest-server/tests/game/ruleset/test_swn_module.py
git commit -m "feat(swn): add armor_class to CreatureCore (SWN ascending AC, default 10)"
```

---

## Part B — Generalized resolution surface + SWN attack (beat rails)

### Task 2: Define the generalized resolution value types

The native seam computes the roll modifier from a stats dict and the DC from a beat. SWN needs the *attacker* (class/level/skills) for the modifier and the *target* (AC) for the target number. Introduce small value types both modules return.

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/resolution.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py` (extend)

- [ ] **Step 1: Write the value types**

```python
# sidequest/game/ruleset/resolution.py
"""Value types for the generalized RulesetModule resolution surface.

A module computes these from the full turn context (attacker + target), so SWN can
read target AC where native reads a beat DC. Frozen — pure data, no behavior.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttackRollParams:
    """Everything dispatch needs to roll one attack: the d20 modifier and the number to meet."""
    modifier: int        # attacker to-hit modifier (native: stat mod; SWN: attack_bonus + skill + attr)
    target_number: int   # number the roll must meet/beat (native: beat DC; SWN: target AC)


@dataclass(frozen=True)
class CheckRollParams:
    """A non-beat check (skill check or save): the dice pool, modifier, and difficulty."""
    sides: int           # 6 for 2d6 skill checks, 20 for saves
    count: int           # 2 for skill checks, 1 for saves
    modifier: int        # attr mod (+ skill level for skill checks)
    difficulty: int      # SWN difficulty (skill check) or save target
    label: str           # human label for the dice overlay context, e.g. "Notice check" / "Physical save"
```

- [ ] **Step 2: Import smoke**

Run: `cd sidequest-server && uv run python -c "from sidequest.game.ruleset.resolution import AttackRollParams, CheckRollParams; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/resolution.py
git commit -m "feat(ruleset): AttackRollParams + CheckRollParams resolution value types"
```

---

### Task 3: Add `attack_params` to the `RulesetModule` ABC and implement it for native (behavior-preserving)

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/base.py`
- Modify: `sidequest-server/sidequest/game/ruleset/native.py`
- Test: `sidequest-server/tests/game/ruleset/test_native_unchanged.py`

- [ ] **Step 1: Add the abstract method to `base.py`**

In `RulesetModule`, after `compute_dc`, add (keep `stat_modifier`/`compute_dc` — native composes them):

```python
    @abstractmethod
    def attack_params(
        self,
        *,
        beat: BeatDef,
        attacker_stats: dict[str, int],
        attacker_core: object | None,
        target_core: object | None,
    ) -> "AttackRollParams":
        """Modifier + target number for one attack. native: stat mod vs beat DC.
        SWN: attack_bonus + skill + attr-mod vs target AC."""
```

Add the import at the top of `base.py`:

```python
from sidequest.game.ruleset.resolution import AttackRollParams
```

- [ ] **Step 2: Write the characterization test (native result equals legacy two-call result)**

```python
# tests/game/ruleset/test_native_unchanged.py
from sidequest.game.ruleset.native import NativeRulesetModule
from sidequest.genre.models.rules import BeatDef

_N = NativeRulesetModule()


def _beat(base=2):
    return BeatDef(id="b", label="B", kind="strike", base=base, stat_check="STRENGTH")


def test_native_attack_params_equals_stat_mod_and_compute_dc():
    beat = _beat(base=2)
    stats = {"STRENGTH": 16}
    params = _N.attack_params(beat=beat, attacker_stats=stats, attacker_core=None, target_core=None)
    assert params.modifier == _N.stat_modifier(stats, "STRENGTH")   # +3
    assert params.target_number == _N.compute_dc(beat)              # 14
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_native_unchanged.py -v`
Expected: FAIL — `NativeRulesetModule` is abstract / has no `attack_params`.

- [ ] **Step 4: Implement `attack_params` on native (composes existing logic — target ignored)**

In `native.py`, add the import and method:

```python
from sidequest.game.ruleset.resolution import AttackRollParams
```

```python
    def attack_params(self, *, beat, attacker_stats, attacker_core, target_core):
        # native ignores attacker_core/target_core: its modifier is the stat mod and its
        # target number is the beat DC. This reproduces the pre-generalization two-call path.
        return AttackRollParams(
            modifier=self.stat_modifier(attacker_stats, beat.stat_check),
            target_number=self.compute_dc(beat),
        )
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_native_unchanged.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/base.py sidequest-server/sidequest/game/ruleset/native.py sidequest-server/tests/game/ruleset/test_native_unchanged.py
git commit -m "feat(ruleset): attack_params surface; native composes stat_modifier+compute_dc"
```

---

### Task 4: Route the attack roll setup in dispatch through `attack_params`

After this, `dispatch_dice_throw` computes the attack modifier and target number via the bound module's `attack_params`, with the target reachable from the snapshot — so SWN can use target AC. native output is identical.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py` (the modifier/DC computation site, ~lines 287-326)
- Test: `sidequest-server/tests/server/dispatch/test_dice_dispatch.py` (extend the existing file — reuse its fixtures)

- [ ] **Step 1: Read the current modifier/DC site**

Read `sidequest-server/sidequest/server/dispatch/dice.py:287-326`. Confirm the current two calls: `modifier = ruleset.stat_modifier(character_stats, beat.stat_check)` and `difficulty = ruleset.compute_dc(beat)`, and that `snapshot` (a `GameSnapshot` with `find_creature_core`) and `encounter` are in scope.

- [ ] **Step 2: Write a regression test asserting native dispatch output is unchanged**

```python
# tests/server/dispatch/test_dice_dispatch.py  (append; reuse _pack_with_combat/_make_encounter/_make_snapshot/_throw)
from sidequest.protocol.dice import RollOutcome


def test_native_dispatch_attack_params_unchanged():
    outcome = dispatch_dice_throw(
        payload=_throw(face=13),
        rolling_player_id="p1",
        character_name="Bob",
        character_stats={"STRENGTH": 16},  # +3
        encounter=_make_encounter(),
        pack=_pack_with_combat(),  # type: ignore[arg-type]
        genre_slug="test", session_id="s1", round_number=1,
        room_broadcast=None, snapshot=_make_snapshot(),
    )
    # Identical to the pre-generalization expectation: 13 + 3 = 16 >= DC 14 → Success.
    assert outcome.outcome is RollOutcome.Success
    assert outcome.result.total == 16
    assert outcome.result.difficulty == 14
```

- [ ] **Step 3: Run to verify it passes against current code (it characterizes today's behavior)**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_dice_dispatch.py::test_native_dispatch_attack_params_unchanged -v`
Expected: PASS (behavior exists today via the two-call path).

- [ ] **Step 4: Replace the two calls with `attack_params`**

In `dispatch_dice_throw`, find the target core (the opposing-side first actor) and call the module once:

```python
    # Generalized attack setup: the module computes modifier + target number with the target
    # in hand, so SWN reads target AC. native ignores the cores and reproduces stat_mod vs DC.
    target_core = None
    if encounter is not None:
        target_name = _first_opponent_name(encounter, actor_side="player")  # existing helper or inline
        if target_name is not None:
            target_core = snapshot.find_creature_core(target_name)
    attacker_core = snapshot.find_creature_core(character_name)
    attack = ruleset.attack_params(
        beat=beat, attacker_stats=character_stats,
        attacker_core=attacker_core, target_core=target_core,
    )
    modifier = attack.modifier
    difficulty = attack.target_number
```

> If no `_first_opponent_name` helper exists, reuse `beat_kinds._opposite_side_first_actor(enc, actor.side)` (confirmed present at `beat_kinds.py:698-716`); import it. Do not invent a new traversal.

- [ ] **Step 5: Run the regression + full dispatch suite**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_dice_dispatch.py -v`
Expected: PASS — native dispatch output unchanged.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/dispatch/dice.py sidequest-server/tests/server/dispatch/test_dice_dispatch.py
git commit -m "feat(ruleset): dispatch attack setup routes through attack_params (target-aware)"
```

---

### Task 5: Source the SWN universal constants into config

Transcribe the SWN constants this plan cannot assert from memory, from the SRD PDF, into a typed config block on `RulesConfig`. The modifier curve and difficulty ladder are stated inline (high confidence); the **save-target derivation** and **base AC** are `[SRD→config]`.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (`RulesConfig` + a new `SwnConfig` model)
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py` (extend)

- [ ] **Step 1: Open the SRD and transcribe two tables**

Open `StarsWithoutNumberRevised-FreeEdition-122917.pdf`. Read the **"Saving Throws"** rules and the **"Armor Class"** rules (Combat chapter). Record, as exact text in the commit message: (a) the save-target formula (how base, character level, and the relevant attribute modifier combine into the number a d20 must meet), and (b) unarmored AC. These populate the defaults below — correct the defaults if the SRD differs from the representative values.

- [ ] **Step 2: Write the failing config test**

```python
# tests/game/ruleset/test_swn_module.py  (append)
from sidequest.genre.models.rules import RulesConfig, SwnConfig


def test_rules_swn_config_defaults():
    rules = RulesConfig(ruleset="swn")
    assert rules.swn is not None
    assert rules.swn.unarmored_ac == 10
    # save target = save_base - level - attribute_mod  (representative; verify vs SRD in Step 1)
    assert rules.swn.save_base == 15


def test_rules_swn_config_absent_for_native():
    assert RulesConfig().swn is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k swn_config -v`
Expected: FAIL — no `SwnConfig` / `swn` field.

- [ ] **Step 4: Add `SwnConfig` and the optional field**

In `rules.py`:

```python
class SwnConfig(BaseModel):
    """SWN universal constants (per-class/per-item numbers live in pack content)."""
    model_config = {"extra": "forbid"}
    unarmored_ac: int = 10                 # [SRD] verify in Task 5 Step 1
    save_base: int = 15                    # [SRD] save target = save_base - level - attr_mod
    # SWN difficulty ladder for 2d6 skill checks (high confidence; verify):
    difficulties: dict[str, int] = Field(
        default_factory=lambda: {"easy": 6, "routine": 8, "tricky": 10, "hard": 12, "formidable": 14}
    )
```

Add to `RulesConfig`:

```python
    swn: SwnConfig | None = None  # present only when ruleset == "swn"
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k swn_config -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/genre/models/rules.py sidequest-server/tests/game/ruleset/test_swn_module.py
git commit -m "feat(swn): SwnConfig universal constants (AC/save-base/difficulty ladder) [SRD-sourced]"
```

---

### Task 6: `SwnRulesetModule` — modifier curve + `attack_params` (vs AC)

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/swn.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py` (extend)

- [ ] **Step 1: Write failing tests for the SWN modifier curve and attack params**

```python
# tests/game/ruleset/test_swn_module.py  (append)
import pytest
from sidequest.game.ruleset.swn import SwnRulesetModule, swn_attribute_modifier
from sidequest.genre.models.rules import BeatDef

_S = SwnRulesetModule()


@pytest.mark.parametrize("score,mod", [(3, -2), (4, -1), (7, -1), (8, 0), (13, 0), (14, 1), (17, 1), (18, 2)])
def test_swn_modifier_curve(score, mod):
    # SWN Revised tight curve — NOT D&D (score-10)//2.
    assert swn_attribute_modifier(score) == mod


def test_swn_attack_params_uses_target_ac_and_attack_bonus():
    beat = BeatDef.model_validate({
        "id": "shoot", "label": "Shoot", "kind": "strike", "base": 0,
        "stat_check": "DEXTERITY",
        # SWN to-hit inputs carried on the beat/action:
        "combat_skill": 1, "attack_bonus": 2,
    })
    attacker_stats = {"DEXTERITY": 14}   # +1 SWN
    target = _core(ac=13)
    params = _S.attack_params(beat=beat, attacker_stats=attacker_stats, attacker_core=None, target_core=target)
    assert params.modifier == 2 + 1 + 1   # attack_bonus + combat_skill + DEX mod = 4
    assert params.target_number == 13     # target AC
```

> `BeatDef` must accept `combat_skill` and `attack_bonus`. If `BeatDef` is `extra="forbid"` and lacks them, add both as optional `int = 0` fields to `BeatDef` in `rules.py` in this step (paired model change), and note it in the commit. Confirm by reading `BeatDef` first.

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k "modifier_curve or attack_params" -v`
Expected: FAIL — `sidequest.game.ruleset.swn` does not exist.

- [ ] **Step 3: Implement the SWN module**

```python
# sidequest/game/ruleset/swn.py
"""SwnRulesetModule — faithful Stars Without Number resolution behind the seam.

Attacks: d20 + attack_bonus + combat_skill + attribute_mod vs target Armor Class.
Skill checks: 2d6 + attribute_mod + skill_level vs difficulty (non-beat path).
Saves: d20 vs (save_base - level - attribute_mod) (non-beat path).

Universal SWN constants come from RulesConfig.swn; per-class/per-item numbers
(attack bonus progression, weapon dice, armor AC) come from pack content.
This module is NOT a fallback — it is selected explicitly by `ruleset: swn`.
"""
from __future__ import annotations

from sidequest.game.ruleset.base import RulesetModule
from sidequest.game.ruleset.resolution import AttackRollParams, CheckRollParams


# SWN Revised ability modifier curve (free edition). Tight band, not (score-10)//2.
def swn_attribute_modifier(score: int) -> int:
    if score <= 3:
        return -2
    if score <= 7:
        return -1
    if score <= 13:
        return 0
    if score <= 17:
        return 1
    return 2


def _stat(stats: dict[str, int], key: str) -> int:
    v = stats.get(key)
    if v is None:
        for k, val in stats.items():
            if k.upper() == key.upper():
                return val
        return 10
    return v


class SwnRulesetModule(RulesetModule):
    slug = "swn"

    # --- scene framing: SWN still uses ConfrontationDefs as the Bang/scene catalog ---
    def find_confrontation(self, confrontations, encounter_type):
        from sidequest.server.dispatch.confrontation import find_confrontation_def
        return find_confrontation_def(confrontations, encounter_type)

    # --- attribute modifier (SWN curve) ---
    def stat_modifier(self, stats: dict[str, int], stat_check: str) -> int:
        return swn_attribute_modifier(_stat(stats, stat_check))

    # native-compat: SWN attacks carry their target number as AC, so a bare beat DC is
    # meaningless. compute_dc must never be the resolution path for SWN; fail loud if reached.
    def compute_dc(self, beat) -> int:
        raise NotImplementedError(
            "SWN resolves attacks vs target AC via attack_params; compute_dc is native-only."
        )

    # --- attack: d20 + attack_bonus + combat_skill + attr_mod vs target AC ---
    def attack_params(self, *, beat, attacker_stats, attacker_core, target_core) -> AttackRollParams:
        attr_mod = self.stat_modifier(attacker_stats, beat.stat_check)
        combat_skill = int(getattr(beat, "combat_skill", 0) or 0)
        attack_bonus = int(getattr(beat, "attack_bonus", 0) or 0)
        target_ac = int(getattr(target_core, "armor_class", 10)) if target_core is not None else 10
        return AttackRollParams(modifier=attack_bonus + combat_skill + attr_mod, target_number=target_ac)

    # --- reuse the engine beat application + weapon-dice damage unchanged ---
    def apply_beat(self, *, encounter, actor, beat, outcome, turn, edge_resolver, damage_resolver):
        from sidequest.game.beat_kinds import apply_beat as _engine_apply_beat
        return _engine_apply_beat(
            encounter, actor, beat, outcome,
            turn=turn, edge_resolver=edge_resolver, damage_resolver=damage_resolver,
        )

    def resolve_damage(self, *, beat, actor_core, pack):
        from sidequest.server.dispatch.damage_roll import resolve_damage_spec_from_beat_and_actor
        return resolve_damage_spec_from_beat_and_actor(beat=beat, actor_core=actor_core, pack=pack)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k "modifier_curve or attack_params" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/swn.py sidequest-server/sidequest/genre/models/rules.py sidequest-server/tests/game/ruleset/test_swn_module.py
git commit -m "feat(swn): SwnRulesetModule modifier curve + attack_params (d20 vs target AC)"
```

---

### Task 7: Register `swn` and prove an SWN attack resolves end-to-end through dispatch

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/registry.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py` (extend — the wiring test)

- [ ] **Step 1: Write the failing registry + dispatch wiring test**

```python
# tests/game/ruleset/test_swn_module.py  (append)
from sidequest.game.ruleset import get_ruleset_module
from sidequest.server.dispatch.dice import dispatch_dice_throw
from sidequest.protocol.dice import RollOutcome
# Reuse the dispatch fixtures from the dispatch test module:
from tests.server.dispatch.test_dice_dispatch import _make_snapshot, _make_encounter, _throw


def test_swn_registered():
    assert get_ruleset_module("swn").slug == "swn"


def test_swn_attack_resolves_vs_ac_through_dispatch(monkeypatch):
    # Build an SWN pack stub with one strike beat carrying SWN to-hit inputs.
    from unittest.mock import MagicMock
    from sidequest.genre.models.rules import ConfrontationDef, MetricDef, BeatDef, RulesConfig, SwnConfig
    cdef = ConfrontationDef(
        type="combat", label="Firefight", category="combat",
        player_metric=MetricDef(name="momentum", starting=0, threshold=10),
        opponent_metric=MetricDef(name="momentum", starting=0, threshold=10),
        beats=[BeatDef.model_validate({
            "id": "shoot", "label": "Shoot", "kind": "strike", "base": 0,
            "stat_check": "DEXTERITY", "combat_skill": 1, "attack_bonus": 2,
        })],
    )
    rules = MagicMock(spec=RulesConfig)
    rules.confrontations = [cdef]
    rules.ruleset = "swn"
    rules.swn = SwnConfig()
    pack = MagicMock(); pack.rules = rules

    enc = _make_encounter()
    snap = _make_snapshot()
    # Seat a target with AC 13 reachable via snapshot.find_creature_core.
    # (If _make_snapshot has no creatures, monkeypatch find_creature_core to return a core with armor_class=13.)
    from sidequest.game.creature_core import CreatureCore, HpPool
    target = CreatureCore(name="Raider", description="d", personality="p",
                          hp=HpPool(current=6, max=6, base_max=6), armor_class=13)
    monkeypatch.setattr(snap, "find_creature_core", lambda name: target if name == "Raider" else None)

    # face 14 + (2+1+1=4) = 18 >= AC 13 → Success
    outcome = dispatch_dice_throw(
        payload=_throw(face=14), rolling_player_id="p1", character_name="Bob",
        character_stats={"DEXTERITY": 14}, encounter=enc, pack=pack,  # type: ignore[arg-type]
        genre_slug="test", session_id="s1", round_number=1, room_broadcast=None, snapshot=snap,
    )
    assert outcome.outcome is RollOutcome.Success
    assert outcome.result.difficulty == 13   # the target's AC was the target number
    assert outcome.result.total == 18
```

> If `_make_encounter` seats the opponent under a name other than `"Raider"`, align the target name to whatever `_opposite_side_first_actor` returns for the player side in the fixture, and set that name on the `CreatureCore` and the `monkeypatch` lambda.

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k "swn_registered or attack_resolves" -v`
Expected: FAIL — `swn` not registered (`UnknownRulesetError`).

- [ ] **Step 3: Register the module**

In `registry.py`:

```python
from sidequest.game.ruleset.swn import SwnRulesetModule

_REGISTRY: dict[str, RulesetModule] = {
    NativeRulesetModule.slug: NativeRulesetModule(),
    SwnRulesetModule.slug: SwnRulesetModule(),
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -v`
Expected: PASS — an SWN attack rolls d20 vs the target's AC and resolves.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/registry.py sidequest-server/tests/game/ruleset/test_swn_module.py
git commit -m "feat(swn): register swn module; SWN attack resolves vs target AC end-to-end"
```

---

## Part C — The non-beat dice path (skill checks & saves)

### Task 8: SWN `check_params` and `save_params` on the module

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/swn.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_module.py` (extend)

- [ ] **Step 1: Write failing tests**

```python
# tests/game/ruleset/test_swn_module.py  (append)
from sidequest.genre.models.rules import SwnConfig

_CFG = SwnConfig()


def test_swn_skill_check_params_2d6():
    # 2d6 + DEX mod (+1) + skill level (2) vs "tricky"(10)
    p = _S.check_params(stats={"DEXTERITY": 14}, attribute="DEXTERITY", skill_level=2,
                        difficulty_key="tricky", label="Notice", cfg=_CFG)
    assert (p.sides, p.count) == (6, 2)
    assert p.modifier == 1 + 2
    assert p.difficulty == 10
    assert p.label == "Notice"


def test_swn_save_params_d20():
    # save target = save_base(15) - level(3) - attr_mod(WIS 14 → +1) = 11
    p = _S.save_params(stats={"WISDOM": 14}, attribute="WISDOM", level=3,
                       label="Mental save", cfg=_CFG)
    assert (p.sides, p.count) == (20, 1)
    assert p.modifier == 0          # SWN saves roll d20 raw vs target; attr folds into the target
    assert p.difficulty == 15 - 3 - 1
    assert p.label == "Mental save"
```

> The save math here uses `save_base - level - attr_mod` per Task 5 Step 1. If the SRD transcription in Task 5 produced a different formula, update both the test expectation and the implementation in Step 2 to match the SRD, and note the correction in the commit.

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k "skill_check_params or save_params" -v`
Expected: FAIL — methods don't exist.

- [ ] **Step 3: Implement the methods on `SwnRulesetModule`**

```python
    def check_params(self, *, stats, attribute, skill_level, difficulty_key, label, cfg) -> CheckRollParams:
        attr_mod = self.stat_modifier(stats, attribute)
        return CheckRollParams(
            sides=6, count=2,
            modifier=attr_mod + int(skill_level),
            difficulty=int(cfg.difficulties[difficulty_key]),
            label=label,
        )

    def save_params(self, *, stats, attribute, level, label, cfg) -> CheckRollParams:
        attr_mod = self.stat_modifier(stats, attribute)
        return CheckRollParams(
            sides=20, count=1,
            modifier=0,  # d20 raw vs target; attribute folds into the target number
            difficulty=int(cfg.save_base) - int(level) - attr_mod,
            label=label,
        )
```

Add to `base.py` `RulesetModule` (NOT abstract — these are SWN-family capabilities; native genuinely has no free-check path and must fail loud, not silently, if misrouted):

```python
    def check_params(self, *, stats, attribute, skill_level, difficulty_key, label, cfg):
        raise NotImplementedError(f"{self.slug} ruleset has no non-beat skill-check resolution")

    def save_params(self, *, stats, attribute, level, label, cfg):
        raise NotImplementedError(f"{self.slug} ruleset has no saving-throw resolution")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_module.py -k "skill_check_params or save_params" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/ruleset/swn.py sidequest-server/sidequest/game/ruleset/base.py sidequest-server/tests/game/ruleset/test_swn_module.py
git commit -m "feat(swn): check_params (2d6 skill check) + save_params (d20 save); base fails loud"
```

---

### Task 9: `dispatch_check` — the non-beat resolution + broadcast

Resolve a skill check or save without an encounter/beat, reusing the live dice round-trip (`DiceRequestPayload`/`DiceResultPayload`) and the five-tier `RollOutcome` ladder.

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/check.py`
- Test: `sidequest-server/tests/server/dispatch/test_check_dispatch.py`

- [ ] **Step 1: Read the dice-resolution helper to reuse it**

Read `sidequest/game/dice.py` for `resolve_dice_with_faces` (the helper `dispatch_dice_throw` uses) and `sidequest/protocol/dice.py:126-216` for `DieSpec`, `DieGroupResult`, `DiceResultPayload`. Confirm the signature for turning faces + modifier + difficulty into a `RollOutcome` and total.

- [ ] **Step 2: Write the failing dispatch test**

```python
# tests/server/dispatch/test_check_dispatch.py
from unittest.mock import MagicMock
from sidequest.server.dispatch.check import dispatch_check
from sidequest.protocol.dice import RollOutcome
from sidequest.genre.models.rules import RulesConfig, SwnConfig


def _swn_pack():
    rules = MagicMock(spec=RulesConfig)
    rules.ruleset = "swn"
    rules.swn = SwnConfig()
    pack = MagicMock(); pack.rules = rules
    return pack


def test_dispatch_skill_check_success():
    # 2d6 faces [4,5]=9 + mod(DEX +1 + skill 2 =3) = 12 >= tricky(10) → Success
    sent = []
    outcome = dispatch_check(
        kind="skill_check", attribute="DEXTERITY", skill_level=2, difficulty_key="tricky",
        level=1, label="Notice", character_stats={"DEXTERITY": 14},
        faces=[4, 5], pack=_swn_pack(), rolling_player_id="p1", character_name="Bob",
        session_id="s1", room_broadcast=sent.append,
    )
    assert outcome.outcome is RollOutcome.Success
    assert outcome.result.total == 12
    assert outcome.result.difficulty == 10
    # broadcast carried a DiceRequest + DiceResult to the room
    assert sent, "dispatch_check did not broadcast the roll to the room"


def test_dispatch_save_against_target():
    # d20 face [12] vs save target 15-3-1(WIS +1)=11 → 12 >= 11 → Success
    outcome = dispatch_check(
        kind="save", attribute="WISDOM", skill_level=0, difficulty_key=None,
        level=3, label="Mental save", character_stats={"WISDOM": 14},
        faces=[12], pack=_swn_pack(), rolling_player_id="p1", character_name="Bob",
        session_id="s1", room_broadcast=None,
    )
    assert outcome.outcome is RollOutcome.Success
    assert outcome.result.difficulty == 11
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_check_dispatch.py -v`
Expected: FAIL — `sidequest.server.dispatch.check` does not exist.

- [ ] **Step 4: Implement `dispatch_check`**

```python
# sidequest/server/dispatch/check.py
"""Non-beat dice resolution: SWN skill checks (2d6) and saving throws (d20).

Reuses the live DiceRequest/DiceResult round-trip and the five-tier RollOutcome
ladder. No encounter, no beat — the bound module produces the roll params; this
function rolls, resolves, broadcasts, and emits an OTEL span. Fail loud if the
bound ruleset has no check/save capability (NotImplementedError from the module).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sidequest.game.dice import resolve_dice_with_faces
from sidequest.game.ruleset import get_ruleset_module
from sidequest.protocol.dice import (
    DiceRequestPayload, DiceResultPayload, DieGroupResult, DieSides, DieSpec, RollOutcome,
)
from sidequest.telemetry.spans.encounter import check_resolved_span  # added in Task 10


@dataclass(frozen=True)
class CheckThrowOutcome:
    outcome: RollOutcome
    result: DiceResultPayload


def dispatch_check(
    *,
    kind: str,                       # "skill_check" | "save"
    attribute: str,
    skill_level: int,
    difficulty_key: str | None,      # required for skill_check; None for save
    level: int,
    label: str,
    character_stats: dict[str, int],
    faces: list[int],                # client-reported dice faces (3D overlay)
    pack,
    rolling_player_id: str,
    character_name: str,
    session_id: str,
    room_broadcast: Callable[[object], None] | None,
) -> CheckThrowOutcome:
    ruleset = get_ruleset_module(pack.rules.ruleset)
    cfg = pack.rules.swn
    if kind == "skill_check":
        params = ruleset.check_params(
            stats=character_stats, attribute=attribute, skill_level=skill_level,
            difficulty_key=difficulty_key, label=label, cfg=cfg,
        )
    elif kind == "save":
        params = ruleset.save_params(
            stats=character_stats, attribute=attribute, level=level, label=label, cfg=cfg,
        )
    else:
        raise ValueError(f"dispatch_check: unknown kind {kind!r} (expected skill_check|save)")

    spec = DieSpec(sides=DieSides.from_wire(params.sides), count=params.count)
    resolved = resolve_dice_with_faces(
        faces=faces, modifier=params.modifier, difficulty=params.difficulty,
    )  # returns total + RollOutcome; confirm exact return shape in Task 9 Step 1
    result = DiceResultPayload(
        request_id=f"{session_id}:{kind}:{character_name}",
        rolling_player_id=rolling_player_id,
        rolls=[DieGroupResult(spec=spec, faces=faces)],
        modifier=params.modifier, total=resolved.total,
        difficulty=params.difficulty, outcome=resolved.outcome,
    )
    if room_broadcast is not None:
        request = DiceRequestPayload(
            request_id=result.request_id, rolling_player_id=rolling_player_id,
            dice=[spec], modifier=params.modifier, stat=attribute,
            difficulty=params.difficulty, context=params.label,
        )
        room_broadcast(request)
        room_broadcast(result)
    check_resolved_span(kind=kind, actor=character_name, label=params.label,
                        total=resolved.total, difficulty=params.difficulty,
                        outcome=resolved.outcome.value)
    return CheckThrowOutcome(outcome=resolved.outcome, result=result)
```

> In Task 9 Step 1 you confirmed the exact return of `resolve_dice_with_faces`. If it returns a tuple/other shape rather than an object with `.total`/`.outcome`, adapt the two `resolved.` accesses accordingly. Do not invent a new resolver — reuse the one `dispatch_dice_throw` uses.

- [ ] **Step 5: Run to verify it passes (after Task 10 adds the span, run together)**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_check_dispatch.py -v`
Expected: PASS once Task 10's span helper exists. If running before Task 10, expect an ImportError on `check_resolved_span` — do Task 10 next, then re-run.

- [ ] **Step 6: Commit (after Task 10 green)**

```bash
git add sidequest-server/sidequest/server/dispatch/check.py sidequest-server/tests/server/dispatch/test_check_dispatch.py
git commit -m "feat(swn): dispatch_check resolves 2d6 skill checks + d20 saves (non-beat path)"
```

---

### Task 10: OTEL span for non-beat checks (the polygraph)

Per the OTEL Observability Principle, every mechanical decision emits a span. The non-beat path needs its own.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/encounter.py`
- Test: `sidequest-server/tests/server/dispatch/test_check_dispatch.py` (extend)

- [ ] **Step 1: Read an existing span helper to copy the pattern**

Read `sidequest/telemetry/spans/encounter.py:316-337` (`encounter_beat_applied_span`) and the watcher-extraction block (~lines 37-47) to match the emit + route pattern exactly.

- [ ] **Step 2: Write the failing span test**

```python
# tests/server/dispatch/test_check_dispatch.py  (append)
def test_check_emits_otel_span(monkeypatch):
    captured = {}
    import sidequest.server.dispatch.check as check_mod
    monkeypatch.setattr(check_mod, "check_resolved_span",
                        lambda **kw: captured.update(kw))
    dispatch_check(
        kind="save", attribute="WISDOM", skill_level=0, difficulty_key=None,
        level=3, label="Mental save", character_stats={"WISDOM": 14},
        faces=[12], pack=_swn_pack(), rolling_player_id="p1", character_name="Bob",
        session_id="s1", room_broadcast=None,
    )
    assert captured["kind"] == "save"
    assert captured["actor"] == "Bob"
    assert captured["difficulty"] == 11
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_check_dispatch.py::test_check_emits_otel_span -v`
Expected: FAIL — `check_resolved_span` does not exist.

- [ ] **Step 4: Add the span helper**

In `sidequest/telemetry/spans/encounter.py`, mirroring `encounter_beat_applied_span`:

```python
def check_resolved_span(
    *,
    kind: str,
    actor: str,
    label: str,
    total: int,
    difficulty: int,
    outcome: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Span for a non-beat SWN check/save (the GM-panel polygraph for free rolls)."""
    tracer = _tracer or trace.get_tracer(__name__)
    with tracer.start_as_current_span("encounter.check_resolved") as span:
        span.set_attribute("check.kind", kind)
        span.set_attribute("check.actor", actor)
        span.set_attribute("check.label", label)
        span.set_attribute("check.total", total)
        span.set_attribute("check.difficulty", difficulty)
        span.set_attribute("check.outcome", outcome)
        for k, v in attrs.items():
            span.set_attribute(k, v)
```

Add `encounter.check_resolved` to the watcher-extraction routing block alongside `encounter.beat_applied` so the GM panel surfaces it (follow the existing dict/list pattern at ~lines 37-47).

- [ ] **Step 5: Run the full check-dispatch suite**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_check_dispatch.py -v`
Expected: PASS (both dispatch tests and the span test).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/encounter.py sidequest-server/tests/server/dispatch/test_check_dispatch.py
git commit -m "feat(swn): encounter.check_resolved OTEL span for non-beat checks (GM polygraph)"
```

---

### Task 11: Wire `dispatch_check` to a client message (the real consumer)

Per CLAUDE.md "verify wiring, not existence": `dispatch_check` needs a non-test consumer. Add a `CHECK_THROW` client message + handler so a player can initiate an SWN skill check or save.

**Files:**
- Modify: `sidequest-server/sidequest/protocol/` (add `CheckThrowPayload` + register `CHECK_THROW` message type — follow how `DiceThrowPayload`/`DICE_THROW` is declared)
- Create: `sidequest-server/sidequest/handlers/check_throw.py`
- Modify: the handler dispatch registry that maps message type → handler (find where `dice_throw` is registered)
- Test: `sidequest-server/tests/handlers/test_check_throw_handler.py`

- [ ] **Step 1: Read how `DICE_THROW` is declared and dispatched**

Read `sidequest/handlers/dice_throw.py` (handler shape, how it pulls `character.stats` and `snapshot`) and grep for where `DICE_THROW` maps to its handler (`grep -rn "DICE_THROW" sidequest/`). Copy that registration pattern.

- [ ] **Step 2: Write the failing handler test**

```python
# tests/handlers/test_check_throw_handler.py
"""Wiring test: a CHECK_THROW message reaches dispatch_check via the handler."""
from unittest.mock import MagicMock
from sidequest.handlers.check_throw import handle_check_throw
from sidequest.protocol.dice import RollOutcome


def test_check_throw_handler_routes_to_dispatch_check():
    # Build the minimal message + session context the handler reads, mirroring dice_throw's test.
    # Assert the handler returns/broadcasts a resolved check outcome.
    ...  # Mirror tests/handlers/test_dice_throw*.py setup for session/snapshot/character.
    outcome = handle_check_throw(...)
    assert outcome.outcome in set(RollOutcome)
```

> Before writing this body, read `tests/handlers/` for the existing `dice_throw` handler test and copy its session/snapshot/character construction. Reuse beats re-deriving the handler call shape.

- [ ] **Step 3: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_check_throw_handler.py -v`
Expected: FAIL — handler module / payload type does not exist.

- [ ] **Step 4: Add `CheckThrowPayload` + `CHECK_THROW`**

In the protocol package, beside `DiceThrowPayload`, add (matching the project's payload/message-type registration convention exactly — confirm in Step 1):

```python
class CheckThrowPayload(ProtocolBase):
    """Client → server: initiate a non-beat SWN skill check or save."""
    kind: str                      # "skill_check" | "save"
    attribute: str                 # e.g. "DEXTERITY"
    skill_level: int = 0
    difficulty_key: str | None = None
    label: str = ""
    faces: list[int]               # rolled on the client 3D overlay
```

Register a `CHECK_THROW` message type pointing at this payload (mirror `DICE_THROW`).

- [ ] **Step 5: Implement the handler**

```python
# sidequest/handlers/check_throw.py
"""Handler: CHECK_THROW → dispatch_check. Pulls the rolling character's stats and level
from the session snapshot exactly as the dice_throw handler does, then resolves a
non-beat SWN check/save."""
from __future__ import annotations

from sidequest.server.dispatch.check import dispatch_check, CheckThrowOutcome


def handle_check_throw(payload, *, snapshot, pack, rolling_player_id, session_id,
                       room_broadcast) -> CheckThrowOutcome:
    # Resolve the rolling character the same way dice_throw does (player_seats → characters).
    pc_name = snapshot.player_seats.get(rolling_player_id) if snapshot.player_seats else None
    character = next((c for c in snapshot.characters if c.core.name == pc_name), None) \
        if pc_name else (snapshot.characters[0] if snapshot.characters else None)
    stats = dict(character.stats) if character is not None else {}
    level = character.core.level if character is not None else 1
    name = character.core.name if character is not None else "Unknown"
    return dispatch_check(
        kind=payload.kind, attribute=payload.attribute, skill_level=payload.skill_level,
        difficulty_key=payload.difficulty_key, level=level, label=payload.label or payload.kind,
        character_stats=stats, faces=payload.faces, pack=pack,
        rolling_player_id=rolling_player_id, character_name=name,
        session_id=session_id, room_broadcast=room_broadcast,
    )
```

Register `CHECK_THROW → handle_check_throw` in the same dispatch map where `DICE_THROW` is registered (located in Step 1).

- [ ] **Step 6: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_check_throw_handler.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/protocol/ sidequest-server/sidequest/handlers/check_throw.py sidequest-server/tests/handlers/test_check_throw_handler.py
git commit -m "feat(swn): CHECK_THROW message + handler wires dispatch_check to a real consumer"
```

---

## Task 12: Full-suite gate

**Files:** none (verification only)

- [ ] **Step 1: Run the ruleset, dispatch, and handler suites**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset tests/server/dispatch tests/handlers -v`
Expected: PASS.

- [ ] **Step 2: Run the server suite**

Run: `cd sidequest-server && uv run pytest`
Expected: PASS, excluding known pre-existing env-coupled failures (see `reference_server_test_gate_composition`). Confirm no *new* failures vs `develop`.

- [ ] **Step 3: Lint**

Run: `cd sidequest-server && uv run ruff check sidequest/game/ruleset sidequest/server/dispatch sidequest/handlers sidequest/telemetry sidequest/genre`
Expected: clean.

- [ ] **Step 4: Confirm native behavior is provably unchanged**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_native_unchanged.py tests/server/dispatch/test_dice_dispatch.py -v`
Expected: PASS — the `native` module's resolution output is identical to before this plan.

---

## Self-Review (completed)

**Spec coverage (against `2026-05-26-swn-module-design.md`):**
- §3 interface reshape (beat→action, target-aware) → Tasks 2, 3, 4 (`AttackRollParams`/`CheckRollParams` + `attack_params` + dispatch routing). The full `enumerate_actions`/`initiative` surface is correctly deferred to the turn-model plan (out of this plan's scope line).
- §4 character shape: AC → Task 1; modifier curve → Task 6; saves (three-save *math*) → Task 8; class attack-bonus/skill as content-carried beat fields → Task 6 Step 1.
- §5 resolution: attack vs AC → Tasks 6, 7; 2d6 skill check + d20 save → Tasks 8, 9.
- §8 narrator contract → **deferred** (explicit scope boundary); the non-beat path here is reachable via `CHECK_THROW` so it has a real consumer now.
- §9 player-visible math → the `DiceResultPayload` round-trip surfaces AC/difficulty/total to the table (existing overlay).
- OTEL principle → Task 10 (`encounter.check_resolved`); HP-delta `state_patch` span is reused unchanged via `apply_beat_hp_channel`.

**Deferred (named, not dropped):** `enumerate_actions`/`initiative` population (turn-model plan), narrator tool contract (narrator plan), `space_opera` content re-author + real SWN constant transcription beyond Task 5's universal block (content plan), psionics (follow-on).

**Placeholder scan:** The only `...` bodies are Task 11 Step 2's handler-test setup and Task 7 Step 1's target-name alignment — both deliberately deferred to copying a *located, real* existing test (`tests/handlers/test_dice_throw*.py`, `tests/server/dispatch/test_dice_dispatch.py`) rather than inventing session/handler constructor args blind. Flagged inline. The `[SRD→config]` markers (save formula, base AC) are sourced by Task 5 Step 1 from the cited PDF — not fabricated.

**Type consistency:** `attack_params` / `check_params` / `save_params` signatures, `AttackRollParams(modifier, target_number)`, and `CheckRollParams(sides, count, modifier, difficulty, label)` are identical across `base.py`, `native.py`, `swn.py`, `dispatch/check.py`, and every test. `slug` values `"native"`/`"swn"` are the single registry keys. `CheckThrowOutcome(outcome, result)` is the single dispatch return type used by the handler.

**Risk note:** Task 8 places `check_params`/`save_params` as base methods that raise `NotImplementedError` for non-SWN modules. This is an explicit fail-loud capability boundary (native genuinely has no free-check path), consistent with the no-silent-fallback rule — not a stub. If a future Fate/PbtA module needs free checks, it overrides them; the base raise guards misrouting.
