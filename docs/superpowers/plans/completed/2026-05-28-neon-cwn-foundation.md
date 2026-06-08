# CWN Foundation & Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind `neon_dystopia` to a new `cwn` (Cities Without Number) ruleset module that subclasses `swn`, adds the CWN Luck save, and fixes the dispatch layer so a non-`swn` ruleset receives its own config block.

**Architecture:** CWN shares SWN's resolution engine (same attribute curve, d20-vs-AC attacks, 2d6 checks, d20 saves, 1d8+DEX initiative). `CwnRulesetModule` subclasses `SwnRulesetModule` and inherits all of that, overriding only `save_params` to add the attribute-free Luck save. A `CwnConfig` (subclass of `SwnConfig`) carries the per-pack `attribute_map`. The dispatch layer currently hardcodes `cfg = pack.rules.swn`; we replace that with a `RulesConfig.ruleset_config()` accessor so `cwn` gets `pack.rules.cwn`. Neon's `rules.yaml` adopts six cyberpunk-flavored attribute names mapped 1:1 to canonical STR/DEX/CON/INT/WIS/CHA.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`uv run pytest`, parallel via `-n auto`), ruff. Two git repos: `sidequest-server` (engine, branch `develop`) and `sidequest-content` (YAML, branch per its CLAUDE.md).

**This plan is the first of four.** Subsequent plans (not in scope here): System Strain; Combat lethality (Trauma/Shock + Major Injury); Hacking-as-confrontation. See `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md`.

**Scope note — what this plan deliberately does NOT do:** it does not remove neon's `humanity` resource, does not convert combat to HP/AC, does not add Trauma/Shock, and does not rebuild the hacking confrontation. Neon's existing momentum-dial confrontations keep working (their strike beats have `damage_channel: none`, so they move the dial and never exercise the attack-vs-AC path). The end state is: neon loads and resolves on the CWN engine with SWN-identical math plus Luck saves.

---

## File Structure

**`sidequest-server`:**
- Modify `sidequest/genre/models/rules.py` — add `CwnConfig`, add `RulesConfig.cwn` field, add `_validate_cwn` validator, add `RulesConfig.ruleset_config()` accessor.
- Create `sidequest/game/ruleset/cwn.py` — `CwnRulesetModule`.
- Modify `sidequest/game/ruleset/registry.py` — register `cwn`.
- Modify `sidequest/server/dispatch/check.py` — `cfg = pack.rules.ruleset_config()`.
- Modify `sidequest/server/dispatch/encounter_lifecycle.py` — `cfg = pack.rules.ruleset_config()`.
- Create `tests/game/ruleset/test_cwn_module.py`.
- Modify `tests/game/ruleset/test_registry.py`.
- Create `tests/genre/models/test_ruleset_config_accessor.py`.
- Create `tests/genre/test_neon_loads_cwn.py`.

**`sidequest-content`:**
- Modify `genre_packs/neon_dystopia/rules.yaml` — attribute names, `ruleset: cwn`, `cwn.attribute_map`, beat `stat_check` remap.

---

## Task 1: `CwnConfig` model + `RulesConfig.cwn` field + validator

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (add after `SwnConfig`, ends line 793; and inside `RulesConfig`, swn field at line 855, validator at 857–883)
- Test: `sidequest-server/tests/game/ruleset/test_cwn_module.py`

Working directory for all commands: `sidequest-server`.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_cwn_module.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import CwnConfig, RulesConfig

_NEON_FLAVOR = ["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"]
_NEON_AMAP = {
    "STRENGTH": "Brawn",
    "DEXTERITY": "Reflex",
    "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech",
    "WISDOM": "Instinct",
    "CHARISMA": "Cool",
}


def test_cwn_config_inherits_swn_defaults():
    cfg = CwnConfig(attribute_map=_NEON_AMAP)
    # CWN's "16 - level" save target equals SWN's "save_base - (level-1)" with save_base=15.
    assert cfg.save_base == 15
    assert cfg.unarmored_ac == 10
    assert cfg.difficulties["formidable"] == 14
    assert cfg.attribute_map["CONSTITUTION"] == "Body"


def test_rules_cwn_requires_complete_attribute_map():
    with pytest.raises(ValidationError, match="attribute_map"):
        RulesConfig(
            ruleset="cwn",
            ability_score_names=_NEON_FLAVOR,
            cwn=CwnConfig(attribute_map={"STRENGTH": "Brawn"}),  # missing 5 keys
        )


def test_rules_cwn_rejects_flavor_not_in_ability_scores():
    bad = dict(_NEON_AMAP, CHARISMA="Swagger")  # Swagger not declared
    with pytest.raises(ValidationError, match="ability_score_names"):
        RulesConfig(
            ruleset="cwn",
            ability_score_names=_NEON_FLAVOR,
            cwn=CwnConfig(attribute_map=bad),
        )


def test_rules_cwn_accepts_complete_map():
    rules = RulesConfig(
        ruleset="cwn",
        ability_score_names=_NEON_FLAVOR,
        cwn=CwnConfig(attribute_map=_NEON_AMAP),
    )
    assert rules.cwn is not None
    assert rules.cwn.attribute_map["INTELLIGENCE"] == "Tech"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_module.py -n0 -q`
Expected: FAIL with `ImportError: cannot import name 'CwnConfig'`.

- [ ] **Step 3: Add `CwnConfig` after `SwnConfig`**

In `sidequest/genre/models/rules.py`, immediately after the `SwnConfig` class (after line 793), add:

```python
class CwnConfig(SwnConfig):
    """Cities Without Number universal constants (Sine Nomine, CC0).

    CWN shares SWN's resolution engine, so this inherits SwnConfig verbatim:
    - unarmored_ac=10, save_base=15 (CWN's "16 - level" == "save_base - (level-1)").
    - the 6/8/10/12/14 difficulty ladder.
    - attribute_map: CWN attribute -> this pack's flavor stat (all six keys
      required when ruleset == 'cwn'; validated on RulesConfig).
    System Strain / Trauma fields are added by the System Strain and Combat
    Lethality plans (YAGNI here).
    """

    model_config = {"extra": "forbid"}
```

- [ ] **Step 4: Add the `cwn` field to `RulesConfig`**

In `RulesConfig`, immediately after the `swn` field (line 855: `swn: SwnConfig | None = None`), add:

```python
    # Present only when ruleset == "cwn"; None for all other rulesets.
    cwn: CwnConfig | None = None
```

- [ ] **Step 5: Add the `_validate_cwn` validator**

In `RulesConfig`, immediately after the `_validate_swn` validator (after line 883), add:

```python
    @model_validator(mode="after")
    def _validate_cwn(self) -> RulesConfig:
        """Enforce a complete attribute_map when ruleset == 'cwn'; raises ValueError if omitted."""
        if self.ruleset != "cwn":
            return self
        if self.cwn is None:
            object.__setattr__(self, "cwn", CwnConfig())
        required = {"STRENGTH", "CONSTITUTION", "DEXTERITY", "INTELLIGENCE", "WISDOM", "CHARISMA"}
        assert self.cwn is not None
        amap = self.cwn.attribute_map
        if not amap:
            raise ValueError(
                "ruleset 'cwn' requires rules.cwn.attribute_map (CWN attribute -> flavor stat); "
                "none authored — no silent default"
            )
        missing = required - amap.keys()
        if missing:
            raise ValueError(f"cwn attribute_map missing required keys: {sorted(missing)}")
        declared = set(self.ability_score_names)
        for cwn_attr, flavor in amap.items():
            if flavor not in declared:
                raise ValueError(
                    f"cwn attribute_map[{cwn_attr!r}] = {flavor!r} is not in "
                    f"ability_score_names {sorted(declared)}"
                )
        return self
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_module.py -n0 -q`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/models/rules.py tests/game/ruleset/test_cwn_module.py
git commit -m "feat(cwn): CwnConfig model + RulesConfig.cwn field and validator"
```

---

## Task 2: `RulesConfig.ruleset_config()` accessor (the wiring fix, part A)

The dispatch layer hardcodes `cfg = pack.rules.swn`. Add an accessor that returns the config block for whichever ruleset is bound, so `cwn` packs get `pack.rules.cwn` and `native` packs get `None` (unchanged behavior — `native` carries no config and its check/save params raise `NotImplementedError`).

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (add a method to `RulesConfig`)
- Test: `sidequest-server/tests/genre/models/test_ruleset_config_accessor.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/models/test_ruleset_config_accessor.py`:

```python
from __future__ import annotations

from sidequest.genre.models.rules import CwnConfig, RulesConfig, SwnConfig

_FLAVOR = ["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"]
_AMAP = {
    "STRENGTH": "Brawn",
    "DEXTERITY": "Reflex",
    "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech",
    "WISDOM": "Instinct",
    "CHARISMA": "Cool",
}


def test_ruleset_config_returns_cwn_block_for_cwn():
    rules = RulesConfig(ruleset="cwn", ability_score_names=_FLAVOR, cwn=CwnConfig(attribute_map=_AMAP))
    cfg = rules.ruleset_config()
    assert isinstance(cfg, CwnConfig)
    assert cfg.attribute_map["INTELLIGENCE"] == "Tech"


def test_ruleset_config_returns_swn_block_for_swn():
    rules = RulesConfig(ruleset="swn", ability_score_names=_FLAVOR, swn=SwnConfig(attribute_map=_AMAP))
    cfg = rules.ruleset_config()
    assert isinstance(cfg, SwnConfig)
    # A CwnConfig is also a SwnConfig (subclass), so guard against the wrong block:
    assert not isinstance(cfg, CwnConfig)


def test_ruleset_config_returns_none_for_native():
    rules = RulesConfig(ruleset="native")
    assert rules.ruleset_config() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/models/test_ruleset_config_accessor.py -n0 -q`
Expected: FAIL with `AttributeError: 'RulesConfig' object has no attribute 'ruleset_config'`.

- [ ] **Step 3: Add the accessor method**

In `RulesConfig`, after the `_validate_cwn` validator, add:

```python
    def ruleset_config(self) -> SwnConfig | None:
        """The config block for the bound ruleset, or None for engines that carry none.

        Dispatch resolves the cfg this way instead of hardcoding `.swn`, so a
        `cwn` pack receives its own block. `native` carries no config (None).
        """
        if self.ruleset == "swn":
            return self.swn
        if self.ruleset == "cwn":
            return self.cwn
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/genre/models/test_ruleset_config_accessor.py -n0 -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/models/test_ruleset_config_accessor.py
git commit -m "feat(cwn): RulesConfig.ruleset_config() accessor for ruleset-keyed cfg block"
```

---

## Task 3: Rewire dispatch to use `ruleset_config()` (the wiring fix, part B)

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/check.py:68`
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py:196`

This is a mechanical swap. Both sites currently read `cfg = pack.rules.swn`.

- [ ] **Step 1: Edit `check.py`**

In `sidequest/server/dispatch/check.py`, change line 68 from:

```python
    cfg = pack.rules.swn
```

to:

```python
    cfg = pack.rules.ruleset_config()
```

Also update the param comment on line 55 from `# genre pack with .rules.ruleset and .rules.swn` to `# genre pack with .rules.ruleset and a .rules.ruleset_config() block`.

- [ ] **Step 2: Edit `encounter_lifecycle.py`**

In `sidequest/server/dispatch/encounter_lifecycle.py`, change line 196 from:

```python
    cfg = pack.rules.swn
```

to:

```python
    cfg = pack.rules.ruleset_config()
```

- [ ] **Step 3: Verify no other site hardcodes `pack.rules.swn`**

Run: `grep -rn "rules\.swn" sidequest/server sidequest/game | grep -v "rules\.swn\b.*#"`
Expected: no matches in dispatch code paths (matches inside `rules.py` model definitions are fine; there should be none under `sidequest/server` or `sidequest/game` reading it as the dispatch cfg). If any dispatch site still reads `pack.rules.swn`, change it to `pack.rules.ruleset_config()` too.

- [ ] **Step 4: Run the existing swn dispatch tests to confirm no regression**

Run: `uv run pytest tests/ -n auto -q -k "swn or check or encounter_lifecycle or space_opera"`
Expected: all pass (space_opera still resolves because `ruleset_config()` returns its `swn` block).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/dispatch/check.py sidequest/server/dispatch/encounter_lifecycle.py
git commit -m "fix(cwn): dispatch sources ruleset cfg via ruleset_config(), not hardcoded .swn"
```

---

## Task 4: `CwnRulesetModule` with the Luck save

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/cwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_cwn_module.py` (append)

- [ ] **Step 1: Write the failing test (append to `test_cwn_module.py`)**

Append to `sidequest-server/tests/game/ruleset/test_cwn_module.py`:

```python
from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.genre.models.rules import BeatDef


_C = CwnRulesetModule()


def test_cwn_slug():
    assert _C.slug == "cwn"


def test_cwn_luck_save_has_no_attribute_modifier():
    # Luck: target = save_base - (level-1), no attribute mod. At level 3, 15 - 2 = 13.
    cfg = CwnConfig(attribute_map=_NEON_AMAP)
    p = _C.save_params(stats={"Body": 18, "Cool": 18}, save="luck", level=3, label="Luck save", cfg=cfg)
    assert (p.sides, p.count) == (20, 1)
    assert p.modifier == 0  # high stats are irrelevant to Luck
    assert p.difficulty == 13


def test_cwn_physical_save_inherits_swn_best_of_two():
    # Physical: better of STR(Brawn)/CON(Body). Body=14 -> +1. Level 1 -> target 15.
    cfg = CwnConfig(attribute_map=_NEON_AMAP)
    p = _C.save_params(stats={"Brawn": 8, "Body": 14}, save="physical", level=1, label="Physical save", cfg=cfg)
    assert p.modifier == 1
    assert p.difficulty == 15


def test_cwn_inherits_swn_attack_params_vs_ac():
    beat = BeatDef.model_validate(
        {"id": "shoot", "label": "Shoot", "kind": "strike", "base": 0,
         "stat_check": "Reflex", "combat_skill": 1, "attack_bonus": 2}
    )

    class _Core:
        armor_class = 13

    params = _C.attack_params(beat=beat, attacker_stats={"Reflex": 14}, attacker_core=None, target_core=_Core())
    assert params.modifier == 2 + 1 + 1  # attack_bonus + combat_skill + DEX(Reflex) mod
    assert params.target_number == 13
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_module.py -n0 -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.ruleset.cwn'`.

- [ ] **Step 3: Create the module**

Create `sidequest-server/sidequest/game/ruleset/cwn.py`:

```python
"""CwnRulesetModule — Cities Without Number resolution behind the seam.

CWN (Sine Nomine, CC0) shares SWN's resolution engine, so this subclasses
SwnRulesetModule and inherits attack/skill/save/initiative/damage verbatim.
The only core divergence is the CWN Luck saving throw: target = save_base -
(level - 1), unmodified by any attribute. NOT a fallback — selected explicitly
by `ruleset: cwn`.
"""

from __future__ import annotations

from sidequest.game.ruleset.resolution import CheckRollParams
from sidequest.game.ruleset.swn import SwnRulesetModule


class CwnRulesetModule(SwnRulesetModule):
    slug = "cwn"

    def save_params(self, *, stats, save, level, label, cfg) -> CheckRollParams:
        """CWN saves: three attribute saves inherited from SWN, plus Luck (no attribute)."""
        if save == "luck":
            return CheckRollParams(
                sides=20,
                count=1,
                modifier=0,
                difficulty=int(cfg.save_base) - (int(level) - 1),
                label=label,
            )
        return super().save_params(stats=stats, save=save, level=level, label=label, cfg=cfg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_module.py -n0 -q`
Expected: all passed (Task 1's 4 tests + the 4 appended here).

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_module.py
git commit -m "feat(cwn): CwnRulesetModule subclassing swn, adds Luck save"
```

---

## Task 5: Register `cwn` in the ruleset registry

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/registry.py`
- Test: `sidequest-server/tests/game/ruleset/test_registry.py` (append)

- [ ] **Step 1: Write the failing test (append to `test_registry.py`)**

Append to `sidequest-server/tests/game/ruleset/test_registry.py`:

```python
def test_cwn_registered():
    from sidequest.game.ruleset.cwn import CwnRulesetModule
    from sidequest.game.ruleset.registry import get_ruleset_module

    module = get_ruleset_module("cwn")
    assert isinstance(module, CwnRulesetModule)
    assert module.slug == "cwn"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_registry.py::test_cwn_registered -n0 -q`
Expected: FAIL — `UnknownRulesetError: Unknown ruleset 'cwn'`.

- [ ] **Step 3: Register the module**

In `sidequest/game/ruleset/registry.py`, add the import after the swn import (line 5):

```python
from sidequest.game.ruleset.cwn import CwnRulesetModule
```

and add the registry entry inside `_REGISTRY` (after the `SwnRulesetModule.slug` line):

```python
    CwnRulesetModule.slug: CwnRulesetModule(),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_registry.py -n0 -q`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/registry.py tests/game/ruleset/test_registry.py
git commit -m "feat(cwn): register cwn in ruleset registry"
```

---

## Task 6: Rebind `neon_dystopia/rules.yaml` to `cwn`

**Files:**
- Modify: `sidequest-content/genre_packs/neon_dystopia/rules.yaml`

Working directory: `sidequest-content`.

The current head of the file (lines 1–28) declares the old six attributes and class/race lists. The confrontation beats (lines ~113–287) use `stat_check:` values `Cool`, `Edge`, `Net`, `Tech`, `Body`, `Reflex`. We rename the attribute set and remap every `stat_check`. Remap table:

| old stat_check | new stat_check |
|---|---|
| Body | Body (unchanged) |
| Reflex | Reflex (unchanged) |
| Cool | Cool (unchanged) |
| Tech | Tech (unchanged) |
| Net | Tech |
| Edge | Cool |

- [ ] **Step 1: Replace the attribute block and add the cwn binding**

In `genre_packs/neon_dystopia/rules.yaml`, replace lines 5–11 (the `ability_score_names` list) with:

```yaml
ability_score_names:
  - Brawn
  - Reflex
  - Body
  - Tech
  - Instinct
  - Cool

ruleset: cwn
cwn:
  attribute_map:
    STRENGTH: Brawn
    DEXTERITY: Reflex
    CONSTITUTION: Body
    INTELLIGENCE: Tech
    WISDOM: Instinct
    CHARISMA: Cool
```

(Leave `stat_generation`, `point_buy_budget`, `magic_level` and everything else in the head untouched. Leave the `humanity` resource block in place — it is removed by the System Strain plan, not this one.)

- [ ] **Step 2: Remap every confrontation beat `stat_check`**

Search the file for `stat_check: Net` and replace each with `stat_check: Tech`. Search for `stat_check: Edge` and replace each with `stat_check: Cool`. Leave `Body`, `Reflex`, `Cool`, `Tech` `stat_check` values as-is.

Verify none remain:

Run (from `sidequest-content`): `grep -nE "stat_check: (Net|Edge)\b" genre_packs/neon_dystopia/rules.yaml`
Expected: no output.

Run: `grep -nE "stat_check:" genre_packs/neon_dystopia/rules.yaml | grep -vE "stat_check: (Brawn|Reflex|Body|Tech|Instinct|Cool)\b"`
Expected: no output (every remaining `stat_check` is one of the six declared names).

- [ ] **Step 3: Commit (in the content repo)**

```bash
cd sidequest-content
git add genre_packs/neon_dystopia/rules.yaml
git commit -m "feat(neon): bind cwn ruleset, adopt CWN-mapped cyberpunk attributes"
cd -
```

---

## Task 7: Wiring test — neon loads and binds `cwn`

This is the behavior wiring test (load the real pack, assert the binding and the validated attribute map). It mirrors `tests/genre/test_space_opera_loads_swn.py`.

**Files:**
- Create: `sidequest-server/tests/genre/test_neon_loads_cwn.py`

Working directory: `sidequest-server`.

- [ ] **Step 1: Write the test**

Create `sidequest-server/tests/genre/test_neon_loads_cwn.py`:

```python
from __future__ import annotations

import pytest

from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.ruleset.registry import get_ruleset_module
from sidequest.genre.loader import load_pack
from sidequest.genre.models.rules import CwnConfig

# Mirror tests/genre/test_space_opera_loads_swn.py's content-on-disk guard.
try:
    load_pack("neon_dystopia")
    _HAS_CONTENT = True
except Exception:
    _HAS_CONTENT = False


@pytest.mark.skipif(not _HAS_CONTENT, reason="sidequest-content not on disk")
def test_neon_binds_cwn_with_attribute_map():
    pack = load_pack("neon_dystopia")
    assert pack.rules.ruleset == "cwn"
    assert isinstance(pack.rules.cwn, CwnConfig)

    amap = pack.rules.cwn.attribute_map
    assert amap["INTELLIGENCE"] == "Tech"
    assert amap["CONSTITUTION"] == "Body"

    # Every mapped flavor stat must be a declared ability score (validator contract).
    declared = set(pack.rules.ability_score_names)
    assert set(amap.values()) <= declared

    # The bound module resolves to the CWN module — proves pack -> registry wiring.
    assert isinstance(get_ruleset_module(pack.rules.ruleset), CwnRulesetModule)

    # ruleset_config() returns the cwn block (the accessor dispatch now calls).
    assert pack.rules.ruleset_config() is pack.rules.cwn
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/genre/test_neon_loads_cwn.py -n0 -q`
Expected: 1 passed (or skipped if `sidequest-content` is not on disk — in which case run it on a machine that has the content checkout before considering the task done).

- [ ] **Step 3: Commit**

```bash
git add tests/genre/test_neon_loads_cwn.py
git commit -m "test(cwn): wiring test — neon_dystopia binds cwn with valid attribute_map"
```

---

## Task 8: Full gate — lint, types, full suite

**Files:** none (verification only). Working directory: `sidequest-server`.

- [ ] **Step 1: Lint and format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors. If `ruff format --check` reports diffs, run `uv run ruff format .`, re-stage, and amend the most recent commit's files into a new `style:` commit.

- [ ] **Step 2: Type check the touched modules**

Run: `uv run pyright sidequest/game/ruleset/cwn.py sidequest/genre/models/rules.py sidequest/server/dispatch/check.py sidequest/server/dispatch/encounter_lifecycle.py`
Expected: 0 errors.

- [ ] **Step 3: Full test suite**

Run: `uv run pytest -n auto -q`
Expected: all pass, no new failures. Pay attention to any pack-load or space_opera tests — they exercise the `ruleset_config()` swap.

- [ ] **Step 4: Commit any fixups**

If steps 1–3 required changes:

```bash
git add -A
git commit -m "chore(cwn): satisfy lint/type/test gate for cwn foundation"
```

---

## Self-Review (completed during authoring)

**Spec coverage (this plan's slice):**
- "New `cwn` module subclassing `swn`, slug `cwn`, registered" → Tasks 4, 5.
- "Luck save (4th category, no attribute)" → Task 4.
- "save math identical to SWN" → encoded as `save_base=15` inherited (Task 1) + asserted in Task 4's physical-save test.
- "new cyberpunk attribute names, clean 6:1 map; hacking on INT (Tech)" → Task 6 attribute_map.
- "fail loud on incomplete attribute_map" → Task 1 validator + tests.
- "wiring test (behavior, not source-grep)" → Task 7.
- Deferred to later plans (correctly out of scope here): System Strain / Humanity removal, Trauma/Shock, Major Injury, combat→HP conversion, hacking confrontation rebuild. Stated in the scope note.

**Placeholder scan:** none — every code/edit step shows the literal code and exact line anchors.

**Type/name consistency:** `CwnConfig`, `CwnRulesetModule`, `ruleset_config()`, the six flavor names (Brawn/Reflex/Body/Tech/Instinct/Cool), and `_NEON_AMAP` are used identically across Tasks 1, 2, 4, 6, 7. `CheckRollParams` import path (`sidequest.game.ruleset.resolution`) matches `swn.py`. The `isinstance(cfg, CwnConfig)` guard in Task 2 accounts for `CwnConfig` being a `SwnConfig` subclass.
