# WWN Module Foundation Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land a registered, bound `WwnRulesetModule` that resolves the entire non-magic Worlds Without Number turn (attacks, skill checks, saves incl. Luck, initiative, and the CWN-shared lethality layer), by inheriting SWN and copying CWN's lethality methods — no shared-base abstraction, no magic yet, no content binding.

**Architecture:** `class WwnRulesetModule(SwnRulesetModule)` follows the exact CWN pattern. Attack/check/initiative/damage/find_confrontation/apply_beat are inherited from SWN verbatim (identical in WWN per the SRD). The lethality layer (Luck save, Shock, Trauma, System Strain, Mortal Injury) is **copied** from `cwn.py` into `wwn.py`, adapted to a new `WwnConfig` and a new `wwn.*` span namespace. Hacking is dropped (left at base default); `ship_attack_params` is overridden to fail loud. The duplication between `cwn.py` and `wwn.py` is **intentional** — the ruleset-library abstraction is a separate, deferred effort (see spec §2.1).

**Tech Stack:** Python 3.12, pydantic v2, pytest (`-n auto` via xdist), OpenTelemetry spans, `uv`. Run from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-05-29-wwn-ruleset-elemental-harmony-design.md` (§2, §4, §5 lethality + binding/registry tests).

**Repo / branch:** `sidequest-server` (gitflow; base branch `develop`). All commits in this plan land on a single feature branch `feat/wwn-module-foundation`.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `sidequest-server/sidequest/genre/models/rules.py` | Add `WwnConfig` (extends `SwnConfig`), `wwn` field + `_validate_wwn` validator + `ruleset_config()` branch | Modify |
| `sidequest-server/sidequest/telemetry/spans/wwn.py` | `wwn.*` spans (copy of `cwn.py` spans minus hacking, renamed) | Create |
| `sidequest-server/sidequest/game/ruleset/wwn.py` | `WwnRulesetModule` — inherit SWN, copy CWN lethality, drop hacking, fail-loud ship | Create |
| `sidequest-server/sidequest/game/ruleset/registry.py` | Register `wwn` | Modify |
| `sidequest-server/tests/game/ruleset/test_wwn_config.py` | `WwnConfig` + `RulesConfig` validator tests | Create |
| `sidequest-server/tests/game/ruleset/test_wwn_module.py` | Module slug, inherited attack/save curve, Luck save, fail-loud ship | Create |
| `sidequest-server/tests/game/ruleset/test_wwn_lethality.py` | Copied Shock / Trauma / System Strain / Mortal Injury behaviors, pinned to WWN | Create |
| `sidequest-server/tests/game/ruleset/test_registry.py` | Extend: `wwn` resolves + singleton | Modify |
| `sidequest-server/tests/game/ruleset/test_loader_binding.py` | Extend: `ruleset: wwn` parses | Modify |

**Reference sources to copy from (read these verbatim before editing):**
- `sidequest-server/sidequest/game/ruleset/cwn.py` — the lethality methods being copied
- `sidequest-server/sidequest/telemetry/spans/cwn.py` — the span module being copied
- `sidequest-server/sidequest/game/ruleset/swn.py` — the parent (do not edit)
- `sidequest-server/sidequest/genre/models/rules.py:759-1055` — `SwnConfig`/`CwnConfig`/`RulesConfig` pattern

---

## Task 0: Branch

- [ ] **Step 1: Create the feature branch off `develop`**

```bash
cd sidequest-server
git checkout develop && git pull
git checkout -b feat/wwn-module-foundation
```

---

## Task 1: `WwnConfig` model + `RulesConfig` wiring

WWN reuses `SystemStrainConfig` and `TraumaConfig` (same models CWN uses) and has **no hacking**. The `attribute_map` validation mirrors `_validate_cwn` (minus the hacking cross-check).

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (after `CwnConfig`, ~line 879; add field ~line 942; add validator ~line 1043; extend `ruleset_config` ~line 1055)
- Test: `sidequest-server/tests/game/ruleset/test_wwn_config.py`

- [ ] **Step 1: Write the failing tests**

Create `sidequest-server/tests/game/ruleset/test_wwn_config.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import RulesConfig, WwnConfig

_EH_FLAVOR = ["Strength", "Agility", "Endurance", "Insight", "Spirit", "Harmony"]
_EH_AMAP = {
    "STRENGTH": "Strength",
    "DEXTERITY": "Agility",
    "CONSTITUTION": "Endurance",
    "INTELLIGENCE": "Insight",
    "WISDOM": "Spirit",
    "CHARISMA": "Harmony",
}


def test_wwn_config_inherits_swn_defaults():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    assert cfg.save_base == 15
    assert cfg.unarmored_ac == 10
    assert cfg.difficulties["formidable"] == 14
    assert cfg.attribute_map["WISDOM"] == "Spirit"


def test_wwn_config_has_strain_and_trauma_defaults():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    assert cfg.system_strain.max_source == "CONSTITUTION"
    assert cfg.trauma.default_trauma_target == 6


def test_wwn_config_has_no_hacking_field():
    # WWN has no cyberspace; the field must not exist (extra='forbid' rejects it).
    with pytest.raises(ValidationError):
        WwnConfig(attribute_map=_EH_AMAP, hacking={"default_tier": "x", "security_tiers": {"x": 7}})


def test_rules_wwn_requires_complete_attribute_map():
    with pytest.raises(ValidationError, match="attribute_map"):
        RulesConfig(
            ruleset="wwn",
            ability_score_names=_EH_FLAVOR,
            wwn=WwnConfig(attribute_map={"STRENGTH": "Strength"}),  # missing 5 keys
        )


def test_rules_wwn_rejects_flavor_not_in_ability_scores():
    bad = dict(_EH_AMAP, CHARISMA="Charm")  # Charm not declared
    with pytest.raises(ValidationError, match="ability_score_names"):
        RulesConfig(ruleset="wwn", ability_score_names=_EH_FLAVOR, wwn=WwnConfig(attribute_map=bad))


def test_rules_wwn_accepts_complete_map():
    rules = RulesConfig(
        ruleset="wwn", ability_score_names=_EH_FLAVOR, wwn=WwnConfig(attribute_map=_EH_AMAP)
    )
    assert rules.wwn is not None
    assert rules.wwn.attribute_map["INTELLIGENCE"] == "Insight"
    assert rules.ruleset_config() is rules.wwn


def test_rules_wwn_with_no_config_block_fails_loud():
    with pytest.raises(ValidationError, match="attribute_map"):
        RulesConfig(ruleset="wwn", ability_score_names=_EH_FLAVOR)


def test_rules_wwn_strain_source_must_be_in_map():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    cfg.system_strain.max_source = "NONEXISTENT"
    with pytest.raises(ValidationError, match="max_source"):
        RulesConfig(ruleset="wwn", ability_score_names=_EH_FLAVOR, wwn=cfg)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/game/ruleset/test_wwn_config.py -n0 -q`
Expected: FAIL — `ImportError: cannot import name 'WwnConfig'`.

- [ ] **Step 3: Add `WwnConfig` after `CwnConfig`**

In `sidequest-server/sidequest/genre/models/rules.py`, immediately after the `CwnConfig` class (ends ~line 878), insert:

```python
class WwnConfig(SwnConfig):
    """Worlds Without Number universal constants (Sine Nomine, CC0).

    WWN shares the SWN/CWN resolution engine, so this inherits SwnConfig
    verbatim (unarmored_ac=10, save_base=15, the 6/8/10/12/14 ladder,
    attribute_map). It carries the same System Strain and Trauma tuning CWN
    uses (reused models), but has NO hacking — WWN has no cyberspace. Magic
    (Effort / spell slots / Fray Die) is configured via the `magic` block added
    in Plan 2. NOT a fallback — selected explicitly by `ruleset: wwn`.
    """

    model_config = {"extra": "forbid"}

    system_strain: SystemStrainConfig = Field(default_factory=SystemStrainConfig)
    trauma: TraumaConfig = Field(default_factory=TraumaConfig)
```

- [ ] **Step 4: Add the `wwn` field on `RulesConfig`**

In `RulesConfig`, directly after the `cwn: CwnConfig | None = None` line (~line 942), add:

```python
    # Present only when ruleset == "wwn"; None for all other rulesets.
    wwn: WwnConfig | None = None
```

- [ ] **Step 5: Add the `_validate_wwn` model validator**

After the `_validate_cwn` method (ends ~line 1043), add:

```python
    @model_validator(mode="after")
    def _validate_wwn(self) -> RulesConfig:
        """Enforce a complete attribute_map when ruleset == 'wwn'; raises ValueError if omitted."""
        if self.ruleset != "wwn":
            return self
        if self.wwn is None:
            object.__setattr__(self, "wwn", WwnConfig())
        required = {"STRENGTH", "CONSTITUTION", "DEXTERITY", "INTELLIGENCE", "WISDOM", "CHARISMA"}
        assert self.wwn is not None
        amap = self.wwn.attribute_map
        if not amap:
            raise ValueError(
                "ruleset 'wwn' requires rules.wwn.attribute_map (WWN attribute -> flavor stat); "
                "none authored — no silent default"
            )
        missing = required - amap.keys()
        if missing:
            raise ValueError(f"wwn attribute_map missing required keys: {sorted(missing)}")
        declared = set(self.ability_score_names)
        for wwn_attr, flavor in amap.items():
            if flavor not in declared:
                raise ValueError(
                    f"wwn attribute_map[{wwn_attr!r}] = {flavor!r} is not in "
                    f"ability_score_names {sorted(declared)}"
                )
        strain_source = self.wwn.system_strain.max_source
        if strain_source not in amap:
            raise ValueError(
                f"wwn.system_strain.max_source = {strain_source!r} is not a key of "
                f"wwn.attribute_map {sorted(amap.keys())}"
            )
        valid_saves = {"physical", "evasion", "mental", "luck"}
        if self.wwn.trauma.major_injury_save not in valid_saves:
            raise ValueError(
                f"wwn.trauma.major_injury_save = {self.wwn.trauma.major_injury_save!r} "
                f"is not one of {sorted(valid_saves)}"
            )
        return self
```

- [ ] **Step 6: Extend `ruleset_config()`**

In `ruleset_config` (~line 1045), add the `wwn` branch before the final `return None`:

```python
        if self.ruleset == "wwn":
            return self.wwn
        return None
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/game/ruleset/test_wwn_config.py -n0 -q`
Expected: PASS (8 passed).

- [ ] **Step 8: Commit**

```bash
git add sidequest/genre/models/rules.py tests/game/ruleset/test_wwn_config.py
git commit -m "feat(ruleset): WwnConfig + RulesConfig wwn validator"
```

---

## Task 2: `wwn.*` OTEL spans

Copy `telemetry/spans/cwn.py` into `telemetry/spans/wwn.py`, drop the hacking span, and rename every `cwn`/`SPAN_CWN` identifier and every `"cwn.*"` span name to `wwn`. Distinct namespace so the GM panel separates `elemental_harmony` (`wwn.*`) from `neon_dystopia` (`cwn.*`).

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/wwn.py`
- Test: covered indirectly by Task 4's lethality tests (spans asserted there). No standalone span test — span emission is verified through the module behavior in `test_wwn_lethality.py`.

- [ ] **Step 1: Create `telemetry/spans/wwn.py`**

Create the file with the five span helpers (system_strain, trauma, shock, mortal_injury, major_injury) — copied from `cwn.py` with identifiers and span-name strings renamed `cwn`→`wwn`, and the hacking span omitted:

```python
"""WWN-specific OTEL spans. The GM panel is the lie detector for engine truth.

Copied from telemetry/spans/cwn.py (the WWN lethality layer is the shared
"Without Number" core) with the cwn->wwn namespace rename and the hacking span
dropped (WWN has no cyberspace). Duplication is intentional per the WWN spec §2.1.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_WWN_SYSTEM_STRAIN_DELTA = "wwn.system_strain.delta"
SPAN_ROUTES[SPAN_WWN_SYSTEM_STRAIN_DELTA] = SpanRoute(
    event_type="state_transition",
    component="wwn",
    extract=lambda span: {
        "field": "system_strain",
        "actor": (span.attributes or {}).get("actor", ""),
        "source": (span.attributes or {}).get("source", ""),
        "amount": (span.attributes or {}).get("amount", 0),
        "new_total": (span.attributes or {}).get("new_total", 0),
        "max": (span.attributes or {}).get("max", 0),
        "applied": (span.attributes or {}).get("applied", True),
    },
)


def wwn_system_strain_delta_span(
    *,
    actor: str,
    source: str,
    amount: int,
    new_total: int,
    max: int,
    applied: bool,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a wwn.system_strain.delta span (lie-detector for WWN System Strain)."""
    attributes: dict[str, Any] = {
        "field": "system_strain",
        "actor": actor,
        "source": source,
        "amount": amount,
        "new_total": new_total,
        "max": max,
        "applied": applied,
        **attrs,
    }
    with Span.open(SPAN_WWN_SYSTEM_STRAIN_DELTA, attributes, tracer_override=_tracer):
        pass


SPAN_WWN_TRAUMA_ROLL = "wwn.trauma.roll"
SPAN_ROUTES[SPAN_WWN_TRAUMA_ROLL] = SpanRoute(
    event_type="state_transition",
    component="wwn",
    extract=lambda span: {
        "field": "trauma",
        "actor": (span.attributes or {}).get("actor", ""),
        "weapon_die": (span.attributes or {}).get("weapon_die", ""),
        "roll": (span.attributes or {}).get("roll", 0),
        "target": (span.attributes or {}).get("target", 0),
        "traumatic": (span.attributes or {}).get("traumatic", False),
        "rating": (span.attributes or {}).get("rating", 1),
        "base": (span.attributes or {}).get("base", 0),
        "final": (span.attributes or {}).get("final", 0),
    },
)

SPAN_WWN_SHOCK_APPLIED = "wwn.shock.applied"
SPAN_ROUTES[SPAN_WWN_SHOCK_APPLIED] = SpanRoute(
    event_type="state_transition",
    component="wwn",
    extract=lambda span: {
        "field": "shock",
        "actor": (span.attributes or {}).get("actor", ""),
        "amount": (span.attributes or {}).get("amount", 0),
        "melee_ac": (span.attributes or {}).get("melee_ac", 0),
        "shock_rating": (span.attributes or {}).get("shock_rating", 0),
        "shock_ac": (span.attributes or {}).get("shock_ac", 0),
    },
)

SPAN_WWN_MORTAL_INJURY_DECLARED = "wwn.mortal_injury.declared"
SPAN_ROUTES[SPAN_WWN_MORTAL_INJURY_DECLARED] = SpanRoute(
    event_type="state_transition",
    component="wwn",
    extract=lambda span: {
        "field": "mortal_injury",
        "actor": (span.attributes or {}).get("actor", ""),
        "rounds_to_die": (span.attributes or {}).get("rounds_to_die", 0),
    },
)

SPAN_WWN_MAJOR_INJURY_ROLL = "wwn.major_injury.roll"
SPAN_ROUTES[SPAN_WWN_MAJOR_INJURY_ROLL] = SpanRoute(
    event_type="state_transition",
    component="wwn",
    extract=lambda span: {
        "field": "major_injury",
        "actor": (span.attributes or {}).get("actor", ""),
        "save_made": (span.attributes or {}).get("save_made", True),
        "roll": (span.attributes or {}).get("roll", 0),
        "text": (span.attributes or {}).get("text", ""),
    },
)


def wwn_trauma_roll_span(
    *,
    actor: str,
    weapon_die: str,
    roll: int,
    target: int,
    traumatic: bool,
    rating: int,
    base: int,
    final: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a wwn.trauma.roll span (lie-detector for WWN trauma threshold check)."""
    attributes: dict[str, Any] = {
        "field": "trauma",
        "actor": actor,
        "weapon_die": weapon_die,
        "roll": roll,
        "target": target,
        "traumatic": traumatic,
        "rating": rating,
        "base": base,
        "final": final,
        **attrs,
    }
    with Span.open(SPAN_WWN_TRAUMA_ROLL, attributes, tracer_override=_tracer):
        pass


def wwn_shock_applied_span(
    *,
    actor: str,
    amount: int,
    melee_ac: int,
    shock_rating: int,
    shock_ac: int | None = None,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a wwn.shock.applied span (lie-detector for WWN shock damage application)."""
    attributes: dict[str, Any] = {
        "field": "shock",
        "actor": actor,
        "amount": amount,
        "melee_ac": melee_ac,
        "shock_rating": shock_rating,
        "shock_ac": shock_ac,
        **attrs,
    }
    with Span.open(SPAN_WWN_SHOCK_APPLIED, attributes, tracer_override=_tracer):
        pass


def wwn_mortal_injury_declared_span(
    *,
    actor: str,
    rounds_to_die: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a wwn.mortal_injury.declared span (lie-detector for WWN mortal wound declaration)."""
    attributes: dict[str, Any] = {
        "field": "mortal_injury",
        "actor": actor,
        "rounds_to_die": rounds_to_die,
        **attrs,
    }
    with Span.open(SPAN_WWN_MORTAL_INJURY_DECLARED, attributes, tracer_override=_tracer):
        pass


def wwn_major_injury_roll_span(
    *,
    actor: str,
    save_made: bool,
    roll: int,
    text: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit a wwn.major_injury.roll span (lie-detector for WWN major injury table roll)."""
    attributes: dict[str, Any] = {
        "field": "major_injury",
        "actor": actor,
        "save_made": save_made,
        "roll": roll,
        "text": text,
        **attrs,
    }
    with Span.open(SPAN_WWN_MAJOR_INJURY_ROLL, attributes, tracer_override=_tracer):
        pass
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `uv run python -c "import sidequest.telemetry.spans.wwn as w; print(w.SPAN_WWN_SHOCK_APPLIED, w.SPAN_WWN_TRAUMA_ROLL)"`
Expected: prints `wwn.shock.applied wwn.trauma.roll` with no import error.

- [ ] **Step 3: Confirm no `cwn`/hacking leakage in the new file**

Run: `! grep -n "cwn\|hacking" sidequest/telemetry/spans/wwn.py`
Expected: command exits 0 (grep found nothing → the `!` inverts a no-match to success). If it prints lines, fix the rename.

- [ ] **Step 4: Commit**

```bash
git add sidequest/telemetry/spans/wwn.py
git commit -m "feat(telemetry): wwn.* OTEL spans (copy of cwn minus hacking)"
```

---

## Task 3: `WwnRulesetModule`

Copy CWN's five lethality methods into a new module that subclasses `SwnRulesetModule`. Swap `cwn_*_span` → `wwn_*_span`, `CwnConfig` → `WwnConfig`, drop `resolve_hacking`, and override `ship_attack_params` to fail loud.

**Files:**
- Create: `sidequest-server/sidequest/game/ruleset/wwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_wwn_module.py` (Task 4)

- [ ] **Step 1: Create `game/ruleset/wwn.py`**

```python
"""WwnRulesetModule — Worlds Without Number resolution behind the seam.

WWN (Sine Nomine, CC0) shares the SWN/CWN resolution engine, so this subclasses
SwnRulesetModule and inherits attack/skill/save/initiative/damage verbatim. The
WWN lethality layer (Luck save, Shock, Trauma, System Strain, Mortal Injury) is
the same "Without Number" core CWN implemented; per the WWN spec §2.1 it is
COPIED here (not hoisted to a shared base) so neon_dystopia/cwn cannot regress
WWN. WWN has no cyberspace (resolve_hacking left at the base default) and no ship
gunnery (ship_attack_params fails loud). Magic is added in Plan 2. NOT a
fallback — selected explicitly by `ruleset: wwn`.
"""

from __future__ import annotations

import random

from opentelemetry import trace

from sidequest.game.creature_core import CreatureCore
from sidequest.game.lethality import DownedResult, LethalityResult, major_injury_entry
from sidequest.game.ruleset.resolution import AttackRollParams, CheckRollParams
from sidequest.game.ruleset.swn import SwnRulesetModule
from sidequest.game.status import Status, StatusSeverity
from sidequest.game.system_strain import StrainResult
from sidequest.genre.models.inventory import DamageSpec
from sidequest.genre.models.rules import SwnConfig, WwnConfig
from sidequest.telemetry.spans.wwn import (
    wwn_major_injury_roll_span,
    wwn_mortal_injury_declared_span,
    wwn_shock_applied_span,
    wwn_system_strain_delta_span,
    wwn_trauma_roll_span,
)


class WwnRulesetModule(SwnRulesetModule):
    slug = "wwn"

    def ship_attack_params(
        self, *, attacker_stats, pilot_skill, attack_bonus, geometry_modifier, target_ac, cfg
    ) -> AttackRollParams:
        """WWN has no ship gunnery — fail loud rather than inherit SWN's dogfight math."""
        raise NotImplementedError("wwn ruleset has no ship-gunnery resolution")

    def save_params(self, *, stats, save, level, label, cfg) -> CheckRollParams:
        """WWN saves: three attribute saves inherited from SWN, plus Luck (no attribute)."""
        if save == "luck":
            return CheckRollParams(
                sides=20,
                count=1,
                modifier=0,
                difficulty=int(cfg.save_base) - (int(level) - 1),
                label=label,
            )
        return super().save_params(stats=stats, save=save, level=level, label=label, cfg=cfg)

    def resolve_shock(
        self,
        *,
        spec: DamageSpec,
        target_melee_ac: int,
        actor: str = "",
        _tracer: trace.Tracer | None = None,
    ) -> int:
        """WWN Shock ("Shock X/AC Y"): a melee weapon with shock>0 chips `shock`
        damage on a MISS when the target's Melee AC <= `spec.shock_ac`. Returns
        the chip damage (0 when not applicable). Emits wwn.shock.applied only
        when damage is actually chipped."""
        if spec.shock <= 0 or spec.shock_ac is None or target_melee_ac > spec.shock_ac:
            return 0
        wwn_shock_applied_span(
            actor=actor,
            amount=spec.shock,
            melee_ac=target_melee_ac,
            shock_rating=spec.shock,
            shock_ac=spec.shock_ac,
            _tracer=_tracer,
        )
        return spec.shock

    def resolve_trauma(
        self,
        *,
        spec: DamageSpec,
        base_total: int,
        cfg: SwnConfig | None,
        rng: random.Random,
        actor: str = "",
        _tracer: trace.Tracer | None = None,
    ) -> LethalityResult:
        """WWN Trauma: if the weapon has a Trauma Die, roll it; on a result that
        meets/exceeds the Trauma Target, multiply total damage by trauma_rating.
        Emits wwn.trauma.roll on every WWN strike that has a trauma_die."""
        if spec.trauma_die is None:
            return LethalityResult(
                base_total=base_total,
                final_total=base_total,
                traumatic=False,
                trauma_roll=0,
                trauma_target=0,
            )
        if not isinstance(cfg, WwnConfig):
            raise ValueError(f"resolve_trauma requires a WwnConfig; got {type(cfg).__name__!r}")
        target = (
            spec.trauma_target
            if spec.trauma_target is not None
            else cfg.trauma.default_trauma_target
        )
        trauma_roll = DamageSpec(dice=spec.trauma_die).roll(rng)
        traumatic = trauma_roll >= target
        final = base_total * spec.trauma_rating if traumatic else base_total
        wwn_trauma_roll_span(
            actor=actor,
            weapon_die=spec.trauma_die,
            roll=trauma_roll,
            target=target,
            traumatic=traumatic,
            rating=spec.trauma_rating,
            base=base_total,
            final=final,
            _tracer=_tracer,
        )
        return LethalityResult(
            base_total=base_total,
            final_total=final,
            traumatic=traumatic,
            trauma_roll=trauma_roll,
            trauma_target=target,
        )

    def apply_system_strain(
        self,
        *,
        core: CreatureCore,
        kind: str,
        amount: int,
        source: str,
        cfg: SwnConfig | None,
        _tracer: trace.Tracer | None = None,
    ) -> StrainResult:
        """Apply a System Strain change under WWN rules; emit wwn.system_strain.delta.

        kind: "temporary" | "first_aid" | "permanent" | "rest". Over-max
        temporary/permanent adds are REFUSED (applied=False). Rest recovers
        toward (never below) the permanent floor. Fails loud if the character has
        no strain pool or kind is unknown.
        """
        pool = core.system_strain
        if pool is None:
            raise ValueError(
                f"{core.name!r} has no system_strain pool; wwn characters must seed one at chargen"
            )
        if not isinstance(cfg, WwnConfig):
            raise ValueError(
                f"apply_system_strain requires a WwnConfig; got {type(cfg).__name__!r}"
            )
        scfg = cfg.system_strain

        before = pool.current
        applied = True
        reason = ""
        requested: int = 0

        if kind == "first_aid":
            requested = scfg.first_aid_cost
            new_current = pool.current + requested
            if new_current > pool.max:
                applied = False
                reason = f"would exceed max ({pool.max})"
                new_current = pool.current
        elif kind == "temporary":
            requested = amount
            new_current = pool.current + amount
            if new_current > pool.max:
                applied = False
                reason = f"would exceed max ({pool.max})"
                new_current = pool.current
        elif kind == "permanent":
            requested = amount
            new_perm = max(0, pool.permanent + amount)
            new_current = pool.current + amount
            if amount > 0 and new_current > pool.max:
                applied = False
                reason = f"would exceed max ({pool.max})"
                new_current = pool.current
                new_perm = pool.permanent
            else:
                new_current = max(new_perm, new_current)
            if applied:
                pool.permanent = new_perm
        elif kind == "rest":
            requested = -scfg.rest_recovery_per_night * max(0, amount)
            new_current = max(pool.permanent, pool.current + requested)
        else:
            raise ValueError(f"unknown system_strain kind {kind!r}")

        if applied:
            pool.current = new_current
        delta = pool.current - before

        wwn_system_strain_delta_span(
            actor=core.name,
            source=source,
            amount=requested,
            new_total=pool.current,
            max=pool.max,
            applied=applied,
            _tracer=_tracer,
        )
        return StrainResult(
            applied=applied,
            current=pool.current,
            max=pool.max,
            permanent=pool.permanent,
            delta=delta,
            reason=reason,
        )

    def resolve_downed(
        self,
        *,
        core: CreatureCore,
        save_target: int,
        scene_traumatic: bool,
        cfg: SwnConfig | None,
        rng: random.Random,
        _tracer: trace.Tracer | None = None,
    ) -> DownedResult:
        """Resolve a WWN character dropped to 0 HP.

        Always declares a Mortal Injury (Scar status; dies at the end of
        cfg.trauma.mortal_injury_rounds unless stabilized). If a Traumatic Hit
        landed this scene, additionally rolls a Physical save (1d20 vs
        save_target); on failure, rolls 1d12 on the Major Injury table and
        attaches a second Scar. Emits wwn.mortal_injury.declared and (when
        rolled) wwn.major_injury.roll.
        """
        if not isinstance(cfg, WwnConfig):
            raise ValueError(f"resolve_downed requires a WwnConfig; got {type(cfg).__name__!r}")
        rounds = cfg.trauma.mortal_injury_rounds
        core.statuses.append(
            Status(
                text=f"Mortal Injury — dies in {rounds} rounds unless stabilized",
                severity=StatusSeverity.Scar,
            )
        )
        wwn_mortal_injury_declared_span(actor=core.name, rounds_to_die=rounds, _tracer=_tracer)

        major = False
        major_roll = 0
        major_text = ""
        save_made = True
        if scene_traumatic:
            save_roll = rng.randint(1, 20)
            save_made = save_roll >= save_target
            if not save_made:
                major = True
                major_roll = rng.randint(1, 12)
                major_text = major_injury_entry(major_roll)
                core.statuses.append(
                    Status(text=f"Major Injury — {major_text}", severity=StatusSeverity.Scar)
                )
            wwn_major_injury_roll_span(
                actor=core.name,
                save_made=save_made,
                roll=major_roll,
                text=major_text,
                _tracer=_tracer,
            )

        return DownedResult(
            mortal=True,
            major=major,
            major_roll=major_roll,
            major_text=major_text,
            save_made=save_made,
        )
```

> **Note (deliberate copy fidelity):** `resolve_downed` replicates CWN's Mortal-Injury + 1d12 Major-Injury behavior verbatim. WWN's published "Catastrophic Damage" rule differs in detail; retuning it to the WWN SRD is explicitly **out of scope for this plan** (copy first — spec §2.1, §8). The behavior is correct and span-backed; a later pass can diverge it safely because WWN's tests (Task 4) pin WWN's behavior independently of CWN's.

- [ ] **Step 2: Verify the module imports**

Run: `uv run python -c "from sidequest.game.ruleset.wwn import WwnRulesetModule; print(WwnRulesetModule().slug)"`
Expected: prints `wwn`.

- [ ] **Step 3: Confirm hacking was dropped**

Run: `! grep -n "hacking" sidequest/game/ruleset/wwn.py`
Expected: exits 0 (no matches). `resolve_hacking` must NOT be defined — WWN inherits the base no-op.

- [ ] **Step 4: Commit**

```bash
git add sidequest/game/ruleset/wwn.py
git commit -m "feat(ruleset): WwnRulesetModule — inherit SWN, copy CWN lethality, drop hacking/ship"
```

---

## Task 4: Module unit tests (slug, inheritance, Luck save, fail-loud ship, lethality)

**Files:**
- Create: `sidequest-server/tests/game/ruleset/test_wwn_module.py`
- Create: `sidequest-server/tests/game/ruleset/test_wwn_lethality.py`

- [ ] **Step 1: Write `test_wwn_module.py` (resolution surface)**

```python
from __future__ import annotations

import pytest

from sidequest.game.ruleset.swn import swn_attribute_modifier
from sidequest.game.ruleset.wwn import WwnRulesetModule
from sidequest.genre.models.rules import BeatDef, WwnConfig

_EH_AMAP = {
    "STRENGTH": "Strength",
    "DEXTERITY": "Agility",
    "CONSTITUTION": "Endurance",
    "INTELLIGENCE": "Insight",
    "WISDOM": "Spirit",
    "CHARISMA": "Harmony",
}
_W = WwnRulesetModule()


def test_wwn_slug():
    assert _W.slug == "wwn"


def test_wwn_inherits_swn_attribute_curve():
    # WWN curve is identical to SWN: 3->-2, 18->+2.
    assert _W.stat_modifier({"Strength": 3}, "Strength") == swn_attribute_modifier(3) == -2
    assert _W.stat_modifier({"Strength": 18}, "Strength") == swn_attribute_modifier(18) == 2


def test_wwn_luck_save_has_no_attribute_modifier():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    p = _W.save_params(
        stats={"Endurance": 18, "Harmony": 18}, save="luck", level=3, label="Luck", cfg=cfg
    )
    assert (p.sides, p.count) == (20, 1)
    assert p.modifier == 0
    assert p.difficulty == 13  # 15 - (3-1)


def test_wwn_physical_save_inherits_swn_best_of_two():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    p = _W.save_params(
        stats={"Strength": 8, "Endurance": 14}, save="physical", level=1, label="Phys", cfg=cfg
    )
    assert p.modifier == 1  # Endurance 14 -> +1, better of Str/Con
    assert p.difficulty == 15


def test_wwn_attack_params_vs_ac():
    beat = BeatDef.model_validate(
        {
            "id": "strike",
            "label": "Strike",
            "kind": "strike",
            "base": 0,
            "stat_check": "Agility",
            "combat_skill": 1,
            "attack_bonus": 2,
        }
    )

    class _Core:
        armor_class = 13

    params = _W.attack_params(
        beat=beat, attacker_stats={"Agility": 14}, attacker_core=None, target_core=_Core()
    )
    assert params.modifier == 2 + 1 + 1
    assert params.target_number == 13


def test_wwn_has_no_ship_gunnery():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    with pytest.raises(NotImplementedError, match="ship-gunnery"):
        _W.ship_attack_params(
            attacker_stats={"Agility": 14},
            pilot_skill=1,
            attack_bonus=0,
            geometry_modifier=0,
            target_ac=12,
            cfg=cfg,
        )
```

- [ ] **Step 2: Write `test_wwn_lethality.py` (copied behaviors, span-backed)**

```python
from __future__ import annotations

import random

from sidequest.game.creature_core import CreatureCore
from sidequest.game.ruleset.wwn import WwnRulesetModule
from sidequest.genre.models.inventory import DamageSpec
from sidequest.genre.models.rules import WwnConfig

_EH_AMAP = {
    "STRENGTH": "Strength",
    "DEXTERITY": "Agility",
    "CONSTITUTION": "Endurance",
    "INTELLIGENCE": "Insight",
    "WISDOM": "Spirit",
    "CHARISMA": "Harmony",
}
_W = WwnRulesetModule()


def test_wwn_shock_chips_on_low_ac_target():
    spec = DamageSpec(dice="1d6", shock=2, shock_ac=15)
    assert _W.resolve_shock(spec=spec, target_melee_ac=13, actor="Lin") == 2


def test_wwn_shock_skips_high_ac_target():
    spec = DamageSpec(dice="1d6", shock=2, shock_ac=15)
    assert _W.resolve_shock(spec=spec, target_melee_ac=16, actor="Lin") == 0


def test_wwn_trauma_multiplies_on_threshold():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    spec = DamageSpec(dice="1d8", trauma_die="1d6", trauma_rating=3, trauma_target=2)
    rng = random.Random(1)  # deterministic
    result = _W.resolve_trauma(spec=spec, base_total=5, cfg=cfg, rng=rng, actor="Lin")
    # trauma_target=2 is trivially met by any 1d6 roll -> traumatic, final = 5*3.
    assert result.traumatic is True
    assert result.final_total == 15


def test_wwn_trauma_identity_without_die():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    spec = DamageSpec(dice="1d8")  # no trauma_die
    result = _W.resolve_trauma(spec=spec, base_total=5, cfg=cfg, rng=random.Random(1))
    assert result.traumatic is False
    assert result.final_total == 5


def test_wwn_downed_declares_mortal_injury():
    cfg = WwnConfig(attribute_map=_EH_AMAP)
    core = CreatureCore(name="Lin")
    if core.system_strain is None:  # downed does not need strain; guard only if constructor requires
        pass
    result = _W.resolve_downed(
        core=core, save_target=15, scene_traumatic=False, cfg=cfg, rng=random.Random(1)
    )
    assert result.mortal is True
    assert any("Mortal Injury" in s.text for s in core.statuses)
```

> **Executor note:** `CreatureCore(...)` construction may require more fields than `name`. Read `sidequest/game/creature_core.py` and build the minimal valid core (mirror how `tests/game/ruleset/` or `tests/game/test_*strain*`/`*downed*` fixtures build one for CWN). The assertion targets — Shock chip value, Trauma multiplier, Mortal-Injury status — are the contract; adjust only the construction boilerplate.

- [ ] **Step 3: Run both test files**

Run: `uv run pytest tests/game/ruleset/test_wwn_module.py tests/game/ruleset/test_wwn_lethality.py -n0 -q`
Expected: PASS. If `test_wwn_downed_declares_mortal_injury` errors on `CreatureCore` construction, fix per the executor note (do not weaken the Mortal-Injury assertion).

- [ ] **Step 4: Commit**

```bash
git add tests/game/ruleset/test_wwn_module.py tests/game/ruleset/test_wwn_lethality.py
git commit -m "test(ruleset): WWN module + copied-lethality behavior tests"
```

---

## Task 5: Register `wwn` + extend registry/loader-binding tests

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/registry.py`
- Modify: `sidequest-server/tests/game/ruleset/test_registry.py`
- Modify: `sidequest-server/tests/game/ruleset/test_loader_binding.py`

- [ ] **Step 1: Write the failing registry test**

Append to `sidequest-server/tests/game/ruleset/test_registry.py`:

```python
def test_wwn_registered_and_singleton():
    from sidequest.game.ruleset.registry import get_ruleset_module
    from sidequest.game.ruleset.wwn import WwnRulesetModule

    mod = get_ruleset_module("wwn")
    assert isinstance(mod, WwnRulesetModule)
    assert get_ruleset_module("wwn") is mod  # stateless singleton
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_registry.py::test_wwn_registered_and_singleton -n0 -q`
Expected: FAIL — `UnknownRulesetError: Unknown ruleset 'wwn'`.

- [ ] **Step 3: Register the module**

In `sidequest-server/sidequest/game/ruleset/registry.py`, add the import and registry entry:

```python
from sidequest.game.ruleset.wwn import WwnRulesetModule
```
```python
_REGISTRY: dict[str, RulesetModule] = {
    NativeRulesetModule.slug: NativeRulesetModule(),
    SwnRulesetModule.slug: SwnRulesetModule(),
    CwnRulesetModule.slug: CwnRulesetModule(),
    WwnRulesetModule.slug: WwnRulesetModule(),
}
```

- [ ] **Step 4: Add the loader-binding test**

Read `sidequest-server/tests/game/ruleset/test_loader_binding.py` to match its existing idiom for building a minimal `RulesConfig`/pack, then append a test that a `ruleset: "wwn"` config (with the elemental_harmony attribute_map) binds to `WwnRulesetModule`. Use the same construction the existing `test_explicit_ruleset_parses` uses, substituting `wwn` + `WwnConfig(attribute_map=_EH_AMAP)`:

```python
def test_wwn_ruleset_binds():
    from sidequest.game.ruleset.registry import get_ruleset_module
    from sidequest.game.ruleset.wwn import WwnRulesetModule
    from sidequest.genre.models.rules import RulesConfig, WwnConfig

    amap = {
        "STRENGTH": "Strength", "DEXTERITY": "Agility", "CONSTITUTION": "Endurance",
        "INTELLIGENCE": "Insight", "WISDOM": "Spirit", "CHARISMA": "Harmony",
    }
    rules = RulesConfig(
        ruleset="wwn",
        ability_score_names=["Strength", "Agility", "Endurance", "Insight", "Spirit", "Harmony"],
        wwn=WwnConfig(attribute_map=amap),
    )
    assert isinstance(get_ruleset_module(rules.ruleset), WwnRulesetModule)
```

- [ ] **Step 5: Run the registry + binding tests**

Run: `uv run pytest tests/game/ruleset/test_registry.py tests/game/ruleset/test_loader_binding.py -n0 -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/ruleset/registry.py tests/game/ruleset/test_registry.py tests/game/ruleset/test_loader_binding.py
git commit -m "feat(ruleset): register wwn; bind + singleton tests"
```

---

## Task 6: Full-suite gate

- [ ] **Step 1: Lint + format**

Run: `uv run ruff format . && uv run ruff check . && uv run pyright sidequest/game/ruleset/wwn.py sidequest/telemetry/spans/wwn.py sidequest/genre/models/rules.py`
Expected: clean (or only pre-existing pyright findings unrelated to these files).

- [ ] **Step 2: Run the full server suite with the required env**

`SIDEQUEST_DATABASE_URL` and `SIDEQUEST_GENRE_PACKS` MUST both be set or the suite throws phantom `MissingDatabaseUrlError` / SKIPs content-gated tests (a "scoped subset" hides real regressions).

Run:
```bash
SIDEQUEST_DATABASE_URL=postgresql://$USER@localhost:5432/sidequest_test \
SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
uv run pytest -q
```
Expected: the new `test_wwn_*` tests pass; **no new failures** vs the pre-change baseline. Record the baseline failure list first (run the suite once on `develop` before Task 1) — only a failure absent from that baseline is a regression.

- [ ] **Step 3: Open the PR**

```bash
env -u GITHUB_TOKEN gh pr create -R slabgorb/sidequest-server -B develop \
  -t "feat(ruleset): WWN module foundation" \
  -b "Plan 1 of 3 for WWN (docs/superpowers/plans/2026-05-29-wwn-module-foundation.md). WwnRulesetModule inherits SWN, copies CWN's lethality layer (Luck/Shock/Trauma/System Strain/Mortal Injury) per spec §2.1, drops hacking, fails loud on ship gunnery. No magic yet (Plan 2), no content binding (Plan 3)."
```

---

## Self-Review

**Spec coverage (this plan = spec §2 + §4 + the lethality/registry/binding slices of §5):**
- §4 inherit-SWN / copy-CWN-lethality / drop-hacking / fail-loud-ship → Task 3 ✓
- §4.1 `WwnConfig` extends `SwnConfig`, reuses Strain/Trauma, `RulesConfig` field + validator + `ruleset_config()` → Task 1 ✓
- §5 `wwn.*` spans → Task 2 ✓
- §7 `test_wwn_module`, lethality tests, registry, loader-binding → Tasks 4, 5 ✓; full-suite gate discipline → Task 6 ✓
- **Deferred to Plan 2/3 (correctly absent here):** magic (Effort/slots/cast spine/Fray Die), chargen seeding, scene/day reset, magic spans, the dispatch-routing + chargen wiring tests (they need the real `elemental_harmony` pack, which Plan 3 authors), content load.

**Placeholder scan:** No "TBD/TODO" in steps. Two explicit **executor notes** (CreatureCore construction in Task 4; loader-binding idiom in Task 5) point at real source to read rather than guessing field lists — this is faithfulness, not a placeholder; the behavioral assertions are fully specified.

**Type consistency:** `WwnConfig` (Task 1) is the type referenced by `WwnRulesetModule` isinstance checks (Task 3) and all tests (Tasks 1,4,5). Span helper names `wwn_*_span` (Task 2) match the imports in `wwn.py` (Task 3). `slug = "wwn"` is consistent across module, registry, and tests.

**Scope check:** Self-contained and testable on its own — a fully bound WWN ruleset with the complete non-magic turn, even before any magic or content exists.
