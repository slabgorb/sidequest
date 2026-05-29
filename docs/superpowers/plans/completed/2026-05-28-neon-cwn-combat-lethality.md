# CWN Combat Lethality Implementation Plan (3 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `neon_dystopia` real CWN combat lethality — move personal combat from the momentum dial onto the ablative `HpPool`/Armor Class path (the one `space_opera` already uses), then layer the CWN **Trauma** damage multiplier, **Shock**-on-miss, **Mortal Injury** death timer, and the **Major Injury d12 table** on top, each driven by `CwnRulesetModule` and observable through `cwn.*` OTEL spans.

**Architecture:** The existing strike-damage dispatch (`server/dispatch/dice.py`) already resolves a `DamageSpec` → rolls server faces → `dmg_total` → `damage_resolver` lambda → `apply_beat` → `apply_beat_hp_channel` → `state_patch.hp`. CWN inserts three seams into that flow, all owned by `CwnRulesetModule` (so generic engine code stays ruleset-agnostic): (1) **Trauma** multiplies `dmg_total` *after* the roll and *before* the resolver lambda on a hit; (2) **Shock** chips fixed damage on a *miss* in the branch that currently skips damage; (3) **resolve_downed** fires when a strike drops the target to 0 HP — it always declares a Mortal Injury, and if a Traumatic Hit landed earlier in the scene (tracked via an `EncounterTag`) it additionally rolls a Physical save and, on failure, the Major Injury d12 table. Weapon Trauma/Shock numbers and armor AC/soak are **content** in `inventory.yaml`; Trauma defaults live in a `cwn.trauma` config block. Stabilization of a Mortal Injury (and the 6th-round death) is narrator-tool-driven with OTEL — the same pattern plan 2 used for `adjust_system_strain` — because the engine has no per-round status-tick hook and CWN keeps the lie-detector on the tool call.

**Tech Stack:** Python 3.12, pydantic v2, pytest (`uv run pytest`, `-n0` for ordered/isolated, `-n auto` for the suite), ruff, pyright, OpenTelemetry. Two repos: `sidequest-server` (engine) and `sidequest-content` (YAML).

**This is the third of four plans.** Plan 1 (foundation: `CwnConfig`, `CwnRulesetModule` + Luck save, registry, attribute remap) and plan 2 (System Strain) are **merged to `develop`** in both repos (server #502/#506, content #280/#281). Plan 4 (hacking-as-confrontation, `net_run`) is **out of scope here**. See `docs/superpowers/specs/2026-05-28-neon-cwn-ruleset-design.md` (the Trauma & Shock section, lines 111-132, is this plan's spec).

**Branch note:** Plans 1 & 2 are merged, so this plan branches directly off `develop` — no stacking. The controller creates, before Task 1: in `sidequest-server` `git checkout develop && git pull && git checkout -b feat/neon-cwn-combat-lethality`; in `sidequest-content` `git checkout develop && git pull && git checkout -b feat/neon-combat-lethality`. `develop` is protected — land via PRs at the end (content PR first, then server, mirroring plan 2's merge order so server CI sees the new pack content).

**Scope note — what this plan deliberately does NOT do:**
- No `net_run` hacking confrontation (plan 4).
- The `net_combat` momentum confrontation (neon `rules.yaml`) **stays** — it is the cyberspace-flavored dial fight, untouched by this plan. Only the personal **`combat`** momentum confrontation is retired and rebuilt on HP/AC.
- `negotiation` and `chase` (social/movement dials) **stay** dial-based per the spec ("Social/chase stay dial-based").
- Armor as a *Trauma Target modifier* is simplified to a flat `cwn.trauma.default_trauma_target` (6, the unarmored-human value); per-armor Trauma-Target raises are deferred (YAGNI — no weapon/armor content in this plan needs them, and the d12 table + soak already model armor's protective role). Logged as a deviation if a reviewer flags it.
- "Lethally-intended attack" is modeled as **any strike-channel beat in a combat confrontation whose weapon carries a `trauma_die`**. A future `non_lethal` beat flag is YAGNI.

---

## File Structure

**`sidequest-server`:**
- Modify `sidequest/genre/models/inventory.py` — add `trauma_die`, `trauma_rating`, `shock` (+ optional `trauma_target` override) to `DamageSpec`; add `armor_class` to `CatalogItem` (armor AC, distinct from the existing `mitigation` soak).
- Modify `sidequest/genre/models/rules.py` — add `TraumaConfig`, add `trauma: TraumaConfig` field to `CwnConfig`, extend `_validate_cwn`.
- Create `sidequest/game/lethality.py` — `LethalityResult`, `DownedResult` data models, the `MAJOR_INJURY_TABLE` (12 entries) + `major_injury_entry(roll)` lookup.
- Modify `sidequest/telemetry/spans/cwn.py` — add four spans (`cwn.trauma.roll`, `cwn.shock.applied`, `cwn.mortal_injury.declared`, `cwn.major_injury.roll`) + routes.
- Modify `sidequest/game/ruleset/base.py` — add `resolve_trauma`, `resolve_shock`, `resolve_downed` as **non-abstract, identity/no-op default** methods (so `native`/`swn` keep working; only `cwn` overrides).
- Modify `sidequest/game/ruleset/cwn.py` — override the three lethality methods.
- Modify `sidequest/server/dispatch/dice.py` — wire `resolve_trauma` (hit path), `resolve_shock` (miss path), `resolve_downed` (0-HP after `apply_beat`).
- Create `sidequest/agents/tools/stabilize_mortal_injury.py` + register in `sidequest/agents/tools/__init__.py`.
- Tests: `tests/genre/models/test_damage_spec_trauma.py`, `tests/genre/models/test_cwn_trauma_config.py`, `tests/game/test_lethality_models.py`, `tests/game/test_major_injury_table.py`, `tests/telemetry/test_cwn_lethality_spans.py`, `tests/game/ruleset/test_cwn_trauma.py`, `tests/game/ruleset/test_cwn_shock.py`, `tests/game/ruleset/test_cwn_downed.py`, `tests/server/test_neon_combat_lethality_dispatch.py`, `tests/agents/tools/test_stabilize_mortal_injury_tool.py`, `tests/genre/test_neon_combat_lethality_wiring.py`.

**`sidequest-content`:**
- Modify `genre_packs/neon_dystopia/inventory.yaml` — weapons gain `damage` + `trauma_die`/`trauma_rating`/`shock`; armor gains `armor_class` + `mitigation`.
- Modify `genre_packs/neon_dystopia/rules.yaml` — retire the momentum `combat` confrontation; add an `hp_depletion` `combat` confrontation (mirror `space_opera`); add `cwn.trauma` config; add a `combat_lethality` custom-rule prose entry.

---

## Task 1: `DamageSpec` Trauma/Shock fields + `CatalogItem.armor_class`

`DamageSpec` is at `sidequest/genre/models/inventory.py:37-68` (currently `dice`, `bonus`, `armor_piercing`, with a `roll()` helper). `CatalogItem` is at `71-89` (has `damage: DamageSpec | None` and `mitigation: int | None`). Add the CWN weapon-lethality fields to `DamageSpec` and an `armor_class` field to `CatalogItem`. All new fields default to "off" so every existing pack's inventory still validates unchanged.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/inventory.py`
- Test: `sidequest-server/tests/genre/models/test_damage_spec_trauma.py`

Working directory for all server commands: `sidequest-server`.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/models/test_damage_spec_trauma.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.inventory import CatalogItem, DamageSpec


def test_damage_spec_trauma_fields_default_off():
    spec = DamageSpec(dice="1d6")
    assert spec.trauma_die is None
    assert spec.trauma_rating == 1
    assert spec.shock == 0
    assert spec.trauma_target is None


def test_damage_spec_accepts_trauma_and_shock():
    spec = DamageSpec(dice="2d8", trauma_die="1d6", trauma_rating=3, shock=2, trauma_target=7)
    assert spec.trauma_die == "1d6"
    assert spec.trauma_rating == 3
    assert spec.shock == 2
    assert spec.trauma_target == 7


def test_trauma_die_validated_as_dice_notation():
    with pytest.raises(ValidationError):
        DamageSpec(dice="1d6", trauma_die="banana")


def test_trauma_rating_must_be_at_least_one():
    with pytest.raises(ValidationError):
        DamageSpec(dice="1d6", trauma_rating=0)


def test_shock_non_negative():
    with pytest.raises(ValidationError):
        DamageSpec(dice="1d6", shock=-1)


def test_catalog_item_armor_class_optional():
    armor = CatalogItem(id="vest", name="Vest", description="x", category="armor",
                        armor_class=15, mitigation=2)
    assert armor.armor_class == 15
    assert armor.mitigation == 2
    plain = CatalogItem(id="rock", name="Rock", description="x", category="misc")
    assert plain.armor_class is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/models/test_damage_spec_trauma.py -n0 -q`
Expected: FAIL — `DamageSpec` rejects `trauma_die` (`extra="forbid"`).

- [ ] **Step 3: Add the fields to `DamageSpec`**

In `sidequest/genre/models/inventory.py`, in the `DamageSpec` class body, after the `armor_piercing` field (line 45), add:

```python
    # CWN lethality (spec 2026-05-28). All default to "off" so non-CWN content
    # validates unchanged. trauma_die: weapon's Trauma Die rolled vs the victim's
    # Trauma Target; on a Traumatic Hit total damage is multiplied by trauma_rating.
    # trauma_target overrides the victim's default Trauma Target when the weapon
    # itself sets the bar (rare; usually None → cfg default). shock: melee chip
    # damage applied on a MISS vs a low-Melee-AC target.
    trauma_die: str | None = None
    trauma_rating: int = Field(default=1, ge=1)
    trauma_target: int | None = Field(default=None, ge=2)
    shock: int = Field(default=0, ge=0)

    @field_validator("trauma_die")
    @classmethod
    def _valid_trauma_die(cls, v: str | None) -> str | None:
        if v is None:
            return v
        m = _DICE_RE.match(v.strip())
        if not m:
            raise ValueError(f"trauma_die {v!r} is not NdM notation")
        if DieSides.from_wire(int(m["faces"])) is DieSides.Unknown:
            raise ValueError(f"trauma_die {v!r} uses unsupported face count")
        return v
```

(`Field`, `field_validator`, `_DICE_RE`, and `DieSides` are all already imported/defined in this file — see lines 13-17.)

- [ ] **Step 4: Add `armor_class` to `CatalogItem`**

In the `CatalogItem` class body, immediately after the `mitigation` field (line 89), add:

```python
    armor_class: int | None = None  # armor: SWN ascending AC the attack rolls against (distinct from mitigation soak)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/genre/models/test_damage_spec_trauma.py -n0 -q`
Expected: 6 passed.

- [ ] **Step 6: Confirm no regression in existing inventory tests**

Run: `uv run pytest tests/genre -n auto -q -k "inventory or damage or catalog"`
Expected: all pass (new fields are additive with defaults).

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/models/inventory.py tests/genre/models/test_damage_spec_trauma.py
git commit -m "feat(cwn): DamageSpec Trauma/Shock fields + CatalogItem.armor_class"
```

---

## Task 2: `TraumaConfig` on `CwnConfig` + validator

`CwnConfig` (post plan 2) is at `sidequest/genre/models/rules.py:813-827` with `model_config`, the inherited `SwnConfig` fields, and `system_strain: SystemStrainConfig`. `SystemStrainConfig` is at `796-810` as the sibling-pattern template. `_validate_cwn` is at `945-976`. Add a `TraumaConfig` and a `trauma` field, following the exact `SystemStrainConfig` pattern.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py`
- Test: `sidequest-server/tests/genre/models/test_cwn_trauma_config.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/models/test_cwn_trauma_config.py`:

```python
from __future__ import annotations

from sidequest.genre.models.rules import CwnConfig, RulesConfig, TraumaConfig

_FLAVOR = ["Brawn", "Reflex", "Body", "Tech", "Instinct", "Cool"]
_AMAP = {
    "STRENGTH": "Brawn", "DEXTERITY": "Reflex", "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech", "WISDOM": "Instinct", "CHARISMA": "Cool",
}


def test_trauma_config_defaults():
    cfg = TraumaConfig()
    assert cfg.default_trauma_target == 6
    assert cfg.mortal_injury_rounds == 6
    assert cfg.major_injury_save == "physical"


def test_cwn_config_has_trauma_by_default():
    cfg = CwnConfig(attribute_map=_AMAP)
    assert isinstance(cfg.trauma, TraumaConfig)
    assert cfg.trauma.default_trauma_target == 6


def test_cwn_accepts_custom_trauma():
    rules = RulesConfig(
        ruleset="cwn",
        ability_score_names=_FLAVOR,
        cwn=CwnConfig(attribute_map=_AMAP, trauma=TraumaConfig(default_trauma_target=7)),
    )
    assert rules.cwn is not None
    assert rules.cwn.trauma.default_trauma_target == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/genre/models/test_cwn_trauma_config.py -n0 -q`
Expected: FAIL with `ImportError: cannot import name 'TraumaConfig'`.

- [ ] **Step 3: Add `TraumaConfig` immediately before `CwnConfig`**

In `sidequest/genre/models/rules.py`, immediately before the `CwnConfig` class (currently at line 813), add:

```python
class TraumaConfig(BaseModel):
    """CWN combat-lethality tuning (genre-level, content-authorable).

    default_trauma_target: the Trauma Target an unarmored human presents — the
      number a weapon's Trauma Die must MEET OR EXCEED for a Traumatic Hit
      (CWN: 6). A weapon may override per-strike via DamageSpec.trauma_target.
    mortal_injury_rounds: rounds a downed (0-HP) character survives before death
      unless stabilized (CWN: 6).
    major_injury_save: the save category rolled when a Traumatic Hit dropped the
      character this scene (CWN: a Physical save). Must be a save the bound
      module's save_params understands ("physical", "evasion", "mental", "luck").
    """

    model_config = {"extra": "forbid"}

    default_trauma_target: int = 6
    mortal_injury_rounds: int = 6
    major_injury_save: str = "physical"
```

- [ ] **Step 4: Add the `trauma` field to `CwnConfig`**

In the `CwnConfig` class body, after the `system_strain` field, add:

```python
    trauma: TraumaConfig = Field(default_factory=TraumaConfig)
```

- [ ] **Step 5: Extend `_validate_cwn` to validate `major_injury_save`**

In `_validate_cwn` (ends with `return self` at line 976), immediately before that final `return self`, add:

```python
        valid_saves = {"physical", "evasion", "mental", "luck"}
        if self.cwn.trauma.major_injury_save not in valid_saves:
            raise ValueError(
                f"cwn.trauma.major_injury_save = {self.cwn.trauma.major_injury_save!r} "
                f"is not one of {sorted(valid_saves)}"
            )
```

- [ ] **Step 6: Run test + plan-1/2 cwn config tests**

Run: `uv run pytest tests/genre/models/test_cwn_trauma_config.py tests/genre/models/test_cwn_system_strain_config.py tests/game/ruleset/test_cwn_module.py -n0 -q`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/models/test_cwn_trauma_config.py
git commit -m "feat(cwn): TraumaConfig on CwnConfig + major_injury_save validation"
```

---

## Task 3: `LethalityResult` + `DownedResult` data models

Pure data models for method outcomes, mirroring plan 2's `StrainResult` (dumb pydantic, all rules in the module methods). They live in a new `game/lethality.py` alongside the Major Injury table (Task 4).

**Files:**
- Create: `sidequest-server/sidequest/game/lethality.py`
- Test: `sidequest-server/tests/game/test_lethality_models.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_lethality_models.py`:

```python
from __future__ import annotations

from sidequest.game.lethality import DownedResult, LethalityResult


def test_lethality_result_passthrough_shape():
    r = LethalityResult(base_total=7, final_total=7, traumatic=False, trauma_roll=0, trauma_target=6)
    assert r.base_total == 7
    assert r.final_total == 7
    assert r.traumatic is False


def test_lethality_result_traumatic_multiplies():
    r = LethalityResult(base_total=7, final_total=21, traumatic=True, trauma_roll=6, trauma_target=6)
    assert r.final_total == 21
    assert r.traumatic is True


def test_downed_result_mortal_only():
    r = DownedResult(mortal=True, major=False, major_roll=0, major_text="", save_made=True)
    assert r.mortal is True
    assert r.major is False


def test_downed_result_major_injury():
    r = DownedResult(mortal=True, major=True, major_roll=12, major_text="Instant death.", save_made=False)
    assert r.major is True
    assert r.major_roll == 12
    assert "death" in r.major_text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_lethality_models.py -n0 -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sidequest.game.lethality'`.

- [ ] **Step 3: Create the module (models only — table added in Task 4)**

Create `sidequest-server/sidequest/game/lethality.py`:

```python
"""CWN combat-lethality data models + Major Injury table.

Pure data + a lookup table. All rules (Trauma roll, Shock, Mortal/Major Injury
resolution) live in CwnRulesetModule. Mirrors plan 2's system_strain.py split:
dumb models here, behavior in the ruleset module.
"""

from __future__ import annotations

from pydantic import BaseModel


class LethalityResult(BaseModel):
    """Outcome of a Trauma check on a hit (for the narrator/dispatch to apply)."""

    model_config = {"extra": "forbid"}

    base_total: int       # damage rolled before Trauma
    final_total: int      # damage after Trauma multiplication (== base_total if not traumatic)
    traumatic: bool       # did the Trauma Die meet/exceed the Trauma Target?
    trauma_roll: int      # the Trauma Die result (0 if the weapon has no trauma_die)
    trauma_target: int    # the target it was rolled against


class DownedResult(BaseModel):
    """Outcome of resolving a character dropped to 0 HP under CWN."""

    model_config = {"extra": "forbid"}

    mortal: bool          # Mortal Injury declared (always True under CWN at 0 HP from lethal damage)
    major: bool           # Major Injury table rolled (only when a Traumatic Hit landed this scene)
    major_roll: int       # 1d12 result (0 if no Major Injury roll)
    major_text: str       # the table entry text ("" if no roll)
    save_made: bool       # Physical save result (True = save succeeded, no Major Injury)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_lethality_models.py -n0 -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/lethality.py tests/game/test_lethality_models.py
git commit -m "feat(cwn): LethalityResult + DownedResult data models"
```

---

## Task 4: Major Injury d12 table + lookup

Add the CWN Major Injury table (CWN SRD, 1d12) to `game/lethality.py`. Each entry is a (roll → text) mapping; the lookup raises on an out-of-range roll (fail loud). Text is drawn from the CWN SRD Major Injury table (spec line 128: "instant death, internal damage, brain damage, lost eye/limb, etc.").

**Files:**
- Modify: `sidequest-server/sidequest/game/lethality.py`
- Test: `sidequest-server/tests/game/test_major_injury_table.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_major_injury_table.py`:

```python
from __future__ import annotations

import pytest

from sidequest.game.lethality import MAJOR_INJURY_TABLE, major_injury_entry


def test_table_has_twelve_entries():
    assert len(MAJOR_INJURY_TABLE) == 12
    assert sorted(MAJOR_INJURY_TABLE.keys()) == list(range(1, 13))


def test_lookup_returns_text():
    assert isinstance(major_injury_entry(1), str)
    assert major_injury_entry(12).strip() != ""


def test_roll_12_is_instant_death():
    assert "death" in major_injury_entry(12).lower()


@pytest.mark.parametrize("bad", [0, 13, -1, 100])
def test_out_of_range_fails_loud(bad):
    with pytest.raises(ValueError, match="1..12"):
        major_injury_entry(bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_major_injury_table.py -n0 -q`
Expected: FAIL — `MAJOR_INJURY_TABLE` / `major_injury_entry` not defined.

- [ ] **Step 3: Add the table + lookup**

In `sidequest/game/lethality.py`, append:

```python
# CWN Major Injury table (1d12). Rolled when a character drops to 0 HP in a
# scene where a Traumatic Hit landed and they failed the Physical save. Text is
# the in-world consequence the narrator dramatizes; the engine applies it as a
# Scar-severity Status (see CwnRulesetModule.resolve_downed).
MAJOR_INJURY_TABLE: dict[int, str] = {
    1: "Knocked senseless — out cold for the rest of the scene, but no lasting harm.",
    2: "Deep bleeding wound. Frail until properly treated and rested.",
    3: "Broken limb — an arm or leg is fractured; that limb is useless until set and healed.",
    4: "Cracked ribs and internal bruising. Every exertion costs; Frail until healed.",
    5: "Severe blood loss. Stabilize within the hour or slip toward death.",
    6: "Concussion — dazed, disoriented; mental tasks suffer until recovered.",
    7: "Lost an eye. Permanent — depth perception and ranged accuracy are diminished.",
    8: "Mangled hand — fingers crushed or severed; fine manipulation is permanently impaired.",
    9: "Severed limb — an arm or leg is lost. Permanent without expensive chrome.",
    10: "Internal damage — a punctured organ. Frail and failing until major surgery.",
    11: "Brain damage — permanent cognitive or motor impairment.",
    12: "Instant death. The wound is mortal beyond saving.",
}


def major_injury_entry(roll: int) -> str:
    """Return the Major Injury text for a 1d12 roll. Fail loud out of range."""
    if roll not in MAJOR_INJURY_TABLE:
        raise ValueError(f"major injury roll {roll} out of range 1..12")
    return MAJOR_INJURY_TABLE[roll]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_major_injury_table.py -n0 -q`
Expected: passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/lethality.py tests/game/test_major_injury_table.py
git commit -m "feat(cwn): Major Injury d12 table + lookup"
```

---

## Task 5: CWN lethality OTEL spans

Add four spans to the existing `sidequest/telemetry/spans/cwn.py` (which already holds `cwn.system_strain.delta` from plan 2). Mirror that module's exact shape — `SPAN_* = "..."` constant, a `SPAN_ROUTES[...] = SpanRoute(...)` registration, and a `*_span(...)` point-emitter. The routing-completeness test (`tests/telemetry/test_routing_completeness.py`) requires every `SPAN_*` constant to be routed.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/cwn.py`
- Test: `sidequest-server/tests/telemetry/test_cwn_lethality_spans.py`

- [ ] **Step 1: Read the existing module**

Read `sidequest/telemetry/spans/cwn.py` in full (it is ~57 lines, written in plan 2). Mirror the `cwn_system_strain_delta_span` definition exactly: the `SpanRoute(event_type="state_transition", component="cwn", extract=lambda span: {...})` form and the `Span.open(NAME, attributes, tracer_override=_tracer)` emitter body.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/telemetry/test_cwn_lethality_spans.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans._core import SPAN_ROUTES
from sidequest.telemetry.spans.cwn import (
    SPAN_CWN_MAJOR_INJURY_ROLL,
    SPAN_CWN_MORTAL_INJURY_DECLARED,
    SPAN_CWN_SHOCK_APPLIED,
    SPAN_CWN_TRAUMA_ROLL,
    cwn_major_injury_roll_span,
    cwn_mortal_injury_declared_span,
    cwn_shock_applied_span,
    cwn_trauma_roll_span,
)


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_all_four_spans_are_routed():
    for name in (
        SPAN_CWN_TRAUMA_ROLL,
        SPAN_CWN_SHOCK_APPLIED,
        SPAN_CWN_MORTAL_INJURY_DECLARED,
        SPAN_CWN_MAJOR_INJURY_ROLL,
    ):
        assert name in SPAN_ROUTES
        assert SPAN_ROUTES[name].component == "cwn"


def test_trauma_span_emits():
    exporter, tracer = _exporter()
    cwn_trauma_roll_span(actor="Mook", weapon_die="1d6", roll=6, target=6,
                         traumatic=True, rating=3, base=7, final=21, _tracer=tracer)
    spans = exporter.get_finished_spans()
    assert spans[0].name == "cwn.trauma.roll"
    attrs = dict(spans[0].attributes or {})
    assert attrs["traumatic"] is True
    assert attrs["final"] == 21


def test_shock_span_emits():
    exporter, tracer = _exporter()
    cwn_shock_applied_span(actor="Mook", amount=2, melee_ac=8, shock_rating=10, _tracer=tracer)
    assert exporter.get_finished_spans()[0].name == "cwn.shock.applied"


def test_mortal_span_emits():
    exporter, tracer = _exporter()
    cwn_mortal_injury_declared_span(actor="Jax", rounds_to_die=6, _tracer=tracer)
    assert exporter.get_finished_spans()[0].name == "cwn.mortal_injury.declared"


def test_major_span_emits():
    exporter, tracer = _exporter()
    cwn_major_injury_roll_span(actor="Jax", save_made=False, roll=9,
                               text="Severed limb.", _tracer=tracer)
    spans = exporter.get_finished_spans()
    assert spans[0].name == "cwn.major_injury.roll"
    assert dict(spans[0].attributes or {})["roll"] == 9
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_cwn_lethality_spans.py -n0 -q`
Expected: FAIL — the span constants/functions don't exist.

- [ ] **Step 4: Add the four spans**

In `sidequest/telemetry/spans/cwn.py`, after the existing `cwn_system_strain_delta_span` definition, append (matching the existing module's import block — `SpanRoute`, `SPAN_ROUTES` from `._core`, `Span` from `.span`, `Any`, `trace`):

```python
SPAN_CWN_TRAUMA_ROLL = "cwn.trauma.roll"
SPAN_ROUTES[SPAN_CWN_TRAUMA_ROLL] = SpanRoute(
    event_type="state_transition",
    component="cwn",
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

SPAN_CWN_SHOCK_APPLIED = "cwn.shock.applied"
SPAN_ROUTES[SPAN_CWN_SHOCK_APPLIED] = SpanRoute(
    event_type="state_transition",
    component="cwn",
    extract=lambda span: {
        "field": "shock",
        "actor": (span.attributes or {}).get("actor", ""),
        "amount": (span.attributes or {}).get("amount", 0),
        "melee_ac": (span.attributes or {}).get("melee_ac", 0),
        "shock_rating": (span.attributes or {}).get("shock_rating", 0),
    },
)

SPAN_CWN_MORTAL_INJURY_DECLARED = "cwn.mortal_injury.declared"
SPAN_ROUTES[SPAN_CWN_MORTAL_INJURY_DECLARED] = SpanRoute(
    event_type="state_transition",
    component="cwn",
    extract=lambda span: {
        "field": "mortal_injury",
        "actor": (span.attributes or {}).get("actor", ""),
        "rounds_to_die": (span.attributes or {}).get("rounds_to_die", 0),
    },
)

SPAN_CWN_MAJOR_INJURY_ROLL = "cwn.major_injury.roll"
SPAN_ROUTES[SPAN_CWN_MAJOR_INJURY_ROLL] = SpanRoute(
    event_type="state_transition",
    component="cwn",
    extract=lambda span: {
        "field": "major_injury",
        "actor": (span.attributes or {}).get("actor", ""),
        "save_made": (span.attributes or {}).get("save_made", True),
        "roll": (span.attributes or {}).get("roll", 0),
        "text": (span.attributes or {}).get("text", ""),
    },
)


def cwn_trauma_roll_span(
    *, actor: str, weapon_die: str, roll: int, target: int, traumatic: bool,
    rating: int, base: int, final: int,
    _tracer: "trace.Tracer | None" = None, **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "trauma", "actor": actor, "weapon_die": weapon_die, "roll": roll,
        "target": target, "traumatic": traumatic, "rating": rating,
        "base": base, "final": final, **attrs,
    }
    with Span.open(SPAN_CWN_TRAUMA_ROLL, attributes, tracer_override=_tracer):
        pass


def cwn_shock_applied_span(
    *, actor: str, amount: int, melee_ac: int, shock_rating: int,
    _tracer: "trace.Tracer | None" = None, **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "shock", "actor": actor, "amount": amount,
        "melee_ac": melee_ac, "shock_rating": shock_rating, **attrs,
    }
    with Span.open(SPAN_CWN_SHOCK_APPLIED, attributes, tracer_override=_tracer):
        pass


def cwn_mortal_injury_declared_span(
    *, actor: str, rounds_to_die: int,
    _tracer: "trace.Tracer | None" = None, **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "mortal_injury", "actor": actor, "rounds_to_die": rounds_to_die, **attrs,
    }
    with Span.open(SPAN_CWN_MORTAL_INJURY_DECLARED, attributes, tracer_override=_tracer):
        pass


def cwn_major_injury_roll_span(
    *, actor: str, save_made: bool, roll: int, text: str,
    _tracer: "trace.Tracer | None" = None, **attrs: Any,
) -> None:
    attributes: dict[str, Any] = {
        "field": "major_injury", "actor": actor, "save_made": save_made,
        "roll": roll, "text": text, **attrs,
    }
    with Span.open(SPAN_CWN_MAJOR_INJURY_ROLL, attributes, tracer_override=_tracer):
        pass
```

(If the existing module's `import` line for `Any`/`trace`/`Span`/`SpanRoute`/`SPAN_ROUTES` differs from this, the constants/functions still reference the same names already in scope — do not duplicate imports.)

- [ ] **Step 5: Run tests + routing-completeness gate**

Run: `uv run pytest tests/telemetry/test_cwn_lethality_spans.py tests/telemetry/test_routing_completeness.py tests/telemetry/test_cwn_strain_span.py -n0 -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/cwn.py tests/telemetry/test_cwn_lethality_spans.py
git commit -m "feat(cwn): trauma/shock/mortal/major OTEL spans + routes"
```

---

## Task 6: Base no-op lethality hooks + `CwnRulesetModule.resolve_trauma`

The dispatch wiring (Tasks 9-11) calls `ruleset.resolve_trauma/resolve_shock/resolve_downed` on whatever module is bound. `native` and `swn` must keep working unchanged, so add these as **non-abstract default methods on the base** that are identity/no-op, then have `cwn` override `resolve_trauma` with the real Trauma logic. (Shock and downed overrides come in Tasks 7-8.)

`RulesetModule` base is at `sidequest/game/ruleset/base.py`. `CwnRulesetModule` is at `sidequest/game/ruleset/cwn.py` (post plan 2: imports `CreatureCore`, `CwnConfig`, `SwnConfig`, the strain span; has `save_params` + `apply_system_strain`).

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/base.py`
- Modify: `sidequest-server/sidequest/game/ruleset/cwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_cwn_trauma.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_cwn_trauma.py`:

```python
from __future__ import annotations

import random

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.ruleset.native import NativeRulesetModule
from sidequest.game.ruleset.swn import SwnRulesetModule
from sidequest.genre.models.inventory import DamageSpec
from sidequest.genre.models.rules import CwnConfig, TraumaConfig

_AMAP = {
    "STRENGTH": "Brawn", "DEXTERITY": "Reflex", "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech", "WISDOM": "Instinct", "CHARISMA": "Cool",
}
_CFG = CwnConfig(attribute_map=_AMAP, trauma=TraumaConfig(default_trauma_target=6))
_MOD = CwnRulesetModule()


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_base_modules_passthrough_damage():
    spec = DamageSpec(dice="1d6")
    for mod in (NativeRulesetModule(), SwnRulesetModule()):
        r = mod.resolve_trauma(spec=spec, base_total=5, cfg=None, rng=random.Random(1))
        assert r.final_total == 5
        assert r.traumatic is False


def test_no_trauma_die_is_passthrough():
    spec = DamageSpec(dice="1d6")  # no trauma_die
    r = _MOD.resolve_trauma(spec=spec, base_total=5, cfg=_CFG, rng=random.Random(1))
    assert r.final_total == 5
    assert r.traumatic is False


def test_traumatic_hit_multiplies_by_rating():
    spec = DamageSpec(dice="2d6", trauma_die="1d6", trauma_rating=3)
    # rng forced so the d6 trauma roll == 6 (>= target 6) → traumatic
    rng = random.Random()
    rng.randint = lambda a, b: 6  # type: ignore[method-assign]
    r = _MOD.resolve_trauma(spec=spec, base_total=7, cfg=_CFG, rng=rng)
    assert r.traumatic is True
    assert r.trauma_roll == 6
    assert r.trauma_target == 6
    assert r.final_total == 21  # 7 * 3


def test_non_traumatic_roll_below_target():
    spec = DamageSpec(dice="2d6", trauma_die="1d6", trauma_rating=3)
    rng = random.Random()
    rng.randint = lambda a, b: 2  # below target 6
    r = _MOD.resolve_trauma(spec=spec, base_total=7, cfg=_CFG, rng=rng)
    assert r.traumatic is False
    assert r.final_total == 7


def test_weapon_trauma_target_override():
    spec = DamageSpec(dice="1d6", trauma_die="1d6", trauma_rating=2, trauma_target=4)
    rng = random.Random()
    rng.randint = lambda a, b: 4  # meets the weapon's override target 4
    r = _MOD.resolve_trauma(spec=spec, base_total=4, cfg=_CFG, rng=rng)
    assert r.trauma_target == 4
    assert r.traumatic is True
    assert r.final_total == 8


def test_trauma_emits_span():
    spec = DamageSpec(dice="1d6", trauma_die="1d6", trauma_rating=2)
    rng = random.Random()
    rng.randint = lambda a, b: 6
    exporter, tracer = _exporter()
    _MOD.resolve_trauma(spec=spec, base_total=4, cfg=_CFG, rng=rng, actor="Mook", _tracer=tracer)
    spans = exporter.get_finished_spans()
    assert spans[0].name == "cwn.trauma.roll"
    assert dict(spans[0].attributes or {})["traumatic"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_trauma.py -n0 -q`
Expected: FAIL — `RulesetModule` has no `resolve_trauma`.

- [ ] **Step 3: Add the no-op default hooks to the base**

In `sidequest/game/ruleset/base.py`, add these imports near the top (the `TYPE_CHECKING` block already imports `DamageSpec`; add the runtime imports):

```python
import random as _random  # noqa: F401  (only the annotation needs it; keep TYPE_CHECKING tidy)
```

Then, in the `RulesetModule` class body (after `roll_initiative`, the last method, ~line 101), add three non-abstract defaults:

```python
    def resolve_trauma(self, *, spec, base_total, cfg, rng, actor="", _tracer=None):
        """Per-hit lethality multiplier. Default: identity passthrough (no Trauma).

        Only CWN overrides. Returns a LethalityResult. Imported lazily to avoid
        a base→game.lethality dependency at module import for the lean rulesets."""
        from sidequest.game.lethality import LethalityResult

        return LethalityResult(
            base_total=base_total, final_total=base_total,
            traumatic=False, trauma_roll=0, trauma_target=0,
        )

    def resolve_shock(self, *, spec, target_melee_ac, actor="", _tracer=None) -> int:
        """Chip damage applied on a MISS. Default: 0 (no Shock). Only CWN overrides."""
        return 0

    def resolve_downed(self, *, core, save_target, scene_traumatic, cfg, rng, _tracer=None):
        """Resolve a 0-HP character. Default: no special consequence (None).

        CWN overrides to declare Mortal Injury and (if a Traumatic Hit landed
        this scene) roll the Major Injury table. Returns DownedResult | None."""
        return None
```

- [ ] **Step 4: Override `resolve_trauma` in `CwnRulesetModule`**

In `sidequest/game/ruleset/cwn.py`, add to the import block:

```python
import random

from sidequest.game.lethality import LethalityResult
from sidequest.genre.models.inventory import DamageSpec
from sidequest.telemetry.spans.cwn import cwn_trauma_roll_span
```

(`CwnConfig` and `cwn_system_strain_delta_span` are already imported from plan 2.)

Add the method to the `CwnRulesetModule` class body:

```python
    def resolve_trauma(
        self,
        *,
        spec: DamageSpec,
        base_total: int,
        cfg: SwnConfig | None,
        rng: random.Random,
        actor: str = "",
        _tracer: "trace.Tracer | None" = None,
    ) -> LethalityResult:
        """CWN Trauma: if the weapon has a Trauma Die, roll it; on a result that
        meets/exceeds the Trauma Target, multiply total damage by trauma_rating.

        Trauma Target = the weapon's override (spec.trauma_target) if set, else
        the genre default (cfg.trauma.default_trauma_target, 6 for unarmored).
        Emits cwn.trauma.roll on every CWN strike that has a trauma_die (the GM
        lie-detector sees both traumatic and non-traumatic rolls)."""
        if spec.trauma_die is None:
            return LethalityResult(
                base_total=base_total, final_total=base_total,
                traumatic=False, trauma_roll=0, trauma_target=0,
            )
        if not isinstance(cfg, CwnConfig):
            raise ValueError(
                f"resolve_trauma requires a CwnConfig; got {type(cfg).__name__!r}"
            )
        target = spec.trauma_target if spec.trauma_target is not None else cfg.trauma.default_trauma_target
        # Trauma Die is validated NdM at DamageSpec construction.
        from sidequest.genre.models.inventory import DamageSpec as _DS  # local, for roll parse

        trauma_roll = _DS(dice=spec.trauma_die).roll(rng)  # sum of the trauma dice (usually 1 die)
        traumatic = trauma_roll >= target
        final = base_total * spec.trauma_rating if traumatic else base_total
        cwn_trauma_roll_span(
            actor=actor, weapon_die=spec.trauma_die, roll=trauma_roll, target=target,
            traumatic=traumatic, rating=spec.trauma_rating, base=base_total, final=final,
            _tracer=_tracer,
        )
        return LethalityResult(
            base_total=base_total, final_total=final,
            traumatic=traumatic, trauma_roll=trauma_roll, trauma_target=target,
        )
```

(Note: `DamageSpec.roll(rng)` adds `spec.bonus`. For the trauma *die* we construct a bare `DamageSpec(dice=spec.trauma_die)` whose `bonus` defaults to 0, so the trauma roll is the pure die result — correct.)

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_trauma.py -n0 -q`
Expected: all passed (6 tests).

- [ ] **Step 6: Confirm native/swn unaffected**

Run: `uv run pytest tests/game/ruleset -n auto -q`
Expected: all pass (base defaults are no-ops; swn/native behavior unchanged).

- [ ] **Step 7: Commit**

```bash
git add sidequest/game/ruleset/base.py sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_trauma.py
git commit -m "feat(cwn): base lethality no-op hooks + CwnRulesetModule.resolve_trauma"
```

---

## Task 7: `CwnRulesetModule.resolve_shock`

CWN Shock: a melee weapon with `Shock X/AC` chips X damage on a *miss* against a target whose Melee AC ≤ the weapon's Shock rating (spec line 122). Here `spec.shock` is the damage chipped (X), and the "Shock rating" AC threshold is also `spec.shock`'s gate — CWN writes Shock as "X/AC" where AC is the threshold. To keep one content number simple for v1, model it as: **a weapon with `shock > 0` chips `shock` damage on a miss when the target's AC ≤ the genre Trauma-target-adjacent threshold.** Read the spec phrasing precisely: "chips X damage on a miss against a target whose Melee AC ≤ the weapon's Shock rating." So the threshold IS the shock rating. We need both numbers. Add a second content field is overkill; instead treat `spec.shock` as X (the chip), and gate on `target_melee_ac <= (cfg-driven default shock AC threshold)`. **Decision (logged as a deviation):** the AC threshold for Shock is the same `cfg.trauma.default_trauma_target`-style constant is wrong semantically; instead pass the threshold explicitly from content via a new `shock_ac` is also overkill. For v1 we gate Shock on `target_melee_ac <= shock` reusing the single number as both the chip amount and the AC ceiling, matching CWN's most common stat block where they're equal (e.g. Shock 2/15 is rare; melee shock weapons cluster at low values). This is a faithful simplification — note it as a deviation.

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/cwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_cwn_shock.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_cwn_shock.py`:

```python
from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.genre.models.inventory import DamageSpec

_MOD = CwnRulesetModule()


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_no_shock_field_is_zero():
    spec = DamageSpec(dice="1d6")  # shock defaults 0
    assert _MOD.resolve_shock(spec=spec, target_melee_ac=8) == 0


def test_shock_applies_when_ac_at_or_below_rating():
    spec = DamageSpec(dice="1d8", shock=2)  # chips 2, AC ceiling 2... see note: ceiling == shock
    # target AC 2 <= shock 2 → applies
    assert _MOD.resolve_shock(spec=spec, target_melee_ac=2) == 2


def test_shock_skipped_when_ac_above_rating():
    spec = DamageSpec(dice="1d8", shock=2)
    assert _MOD.resolve_shock(spec=spec, target_melee_ac=5) == 0


def test_shock_emits_span_only_when_applied():
    spec = DamageSpec(dice="1d8", shock=3)
    exporter, tracer = _exporter()
    _MOD.resolve_shock(spec=spec, target_melee_ac=3, actor="Mook", _tracer=tracer)
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "cwn.shock.applied"
    # a skipped shock emits nothing
    _MOD.resolve_shock(spec=spec, target_melee_ac=9, actor="Mook", _tracer=tracer)
    assert len(exporter.get_finished_spans()) == 1
```

> **Note for the implementer:** the test encodes the v1 decision that the Shock chip amount and the AC ceiling are the same content number (`spec.shock`). If review prefers two numbers, add a `shock_ac` field on `DamageSpec` (Task 1 pattern) and gate on it; update this test accordingly. Log whichever you ship as a deviation.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_shock.py -n0 -q`
Expected: FAIL — base `resolve_shock` returns 0 always, so `test_shock_applies...` fails.

- [ ] **Step 3: Override `resolve_shock` in `CwnRulesetModule`**

Add to `sidequest/game/ruleset/cwn.py` imports:

```python
from sidequest.telemetry.spans.cwn import cwn_shock_applied_span
```

Add the method:

```python
    def resolve_shock(
        self,
        *,
        spec: DamageSpec,
        target_melee_ac: int,
        actor: str = "",
        _tracer: "trace.Tracer | None" = None,
    ) -> int:
        """CWN Shock: a melee weapon with shock>0 chips `shock` damage on a MISS
        when the target's Melee AC <= the weapon's Shock rating. v1 models the
        chip amount and the AC ceiling as the same content number (spec.shock).
        Returns the chip damage (0 when not applicable). Emits cwn.shock.applied
        only when damage is actually chipped."""
        if spec.shock <= 0 or target_melee_ac > spec.shock:
            return 0
        cwn_shock_applied_span(
            actor=actor, amount=spec.shock, melee_ac=target_melee_ac,
            shock_rating=spec.shock, _tracer=_tracer,
        )
        return spec.shock
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_shock.py -n0 -q`
Expected: passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_shock.py
git commit -m "feat(cwn): resolve_shock — chip damage on a miss vs low-AC target"
```

---

## Task 8: `CwnRulesetModule.resolve_downed` — Mortal + Major Injury

When a strike drops a character to 0 HP, CWN resolves the consequence. Always declare a **Mortal Injury** (a Scar-severity Status: dies at end of `mortal_injury_rounds` unless stabilized). If a **Traumatic Hit landed this scene** (the caller passes `scene_traumatic=True`), additionally roll a **Physical save**; on failure, roll **1d12 on the Major Injury table** and apply that as a second Scar Status. The save *target number* is computed by the caller (Task 11, via `save_params`) and passed in as `save_target` — `resolve_downed` rolls the d20 with the injected `rng` (testable, deterministic).

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/cwn.py`
- Test: `sidequest-server/tests/game/ruleset/test_cwn_downed.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_cwn_downed.py`:

```python
from __future__ import annotations

import random

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.creature_core import CreatureCore
from sidequest.game.ruleset.cwn import CwnRulesetModule
from sidequest.game.status import StatusSeverity
from sidequest.genre.models.rules import CwnConfig, TraumaConfig

_AMAP = {
    "STRENGTH": "Brawn", "DEXTERITY": "Reflex", "CONSTITUTION": "Body",
    "INTELLIGENCE": "Tech", "WISDOM": "Instinct", "CHARISMA": "Cool",
}
_CFG = CwnConfig(attribute_map=_AMAP, trauma=TraumaConfig(mortal_injury_rounds=6))
_MOD = CwnRulesetModule()


def _core() -> CreatureCore:
    return CreatureCore(name="Jax", description="runner", personality="cool")


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_non_traumatic_downed_is_mortal_only():
    core = _core()
    r = _MOD.resolve_downed(core=core, save_target=10, scene_traumatic=False,
                            cfg=_CFG, rng=random.Random(1))
    assert r is not None
    assert r.mortal is True
    assert r.major is False
    # a Mortal Injury Status was attached
    assert any("Mortal Injury" in s.text for s in core.statuses)
    assert all(s.severity == StatusSeverity.Scar for s in core.statuses if "Mortal" in s.text)


def test_traumatic_downed_save_made_no_major():
    core = _core()
    rng = random.Random()
    rng.randint = lambda a, b: 20  # d20 save roll = 20, beats target
    r = _MOD.resolve_downed(core=core, save_target=10, scene_traumatic=True,
                            cfg=_CFG, rng=rng)
    assert r.mortal is True
    assert r.major is False
    assert r.save_made is True
    assert not any("Major Injury" in s.text for s in core.statuses)


def test_traumatic_downed_save_failed_rolls_major():
    core = _core()
    # first randint is the d20 save (=1, fails target 10); second is the d12 major roll (=9)
    seq = iter([1, 9])
    rng = random.Random()
    rng.randint = lambda a, b: next(seq)
    r = _MOD.resolve_downed(core=core, save_target=10, scene_traumatic=True,
                            cfg=_CFG, rng=rng)
    assert r.mortal is True
    assert r.major is True
    assert r.save_made is False
    assert r.major_roll == 9
    assert any("Major Injury" in s.text for s in core.statuses)


def test_downed_emits_spans():
    core = _core()
    seq = iter([1, 12])  # fail save, roll 12 (instant death)
    rng = random.Random()
    rng.randint = lambda a, b: next(seq)
    exporter, tracer = _exporter()
    _MOD.resolve_downed(core=core, save_target=10, scene_traumatic=True,
                        cfg=_CFG, rng=rng, _tracer=tracer)
    names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.mortal_injury.declared" in names
    assert "cwn.major_injury.roll" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_cwn_downed.py -n0 -q`
Expected: FAIL — base `resolve_downed` returns None.

- [ ] **Step 3: Override `resolve_downed` in `CwnRulesetModule`**

Add to `sidequest/game/ruleset/cwn.py` imports:

```python
from sidequest.game.lethality import DownedResult, major_injury_entry
from sidequest.game.status import Status, StatusSeverity
from sidequest.telemetry.spans.cwn import (
    cwn_major_injury_roll_span,
    cwn_mortal_injury_declared_span,
)
```

Add the method:

```python
    def resolve_downed(
        self,
        *,
        core: CreatureCore,
        save_target: int,
        scene_traumatic: bool,
        cfg: SwnConfig | None,
        rng: random.Random,
        _tracer: "trace.Tracer | None" = None,
    ) -> DownedResult:
        """Resolve a CWN character dropped to 0 HP.

        Always declares a Mortal Injury (Scar status; the character dies at the
        end of cfg.trauma.mortal_injury_rounds unless stabilized via the
        stabilize_mortal_injury tool). If a Traumatic Hit landed this scene,
        additionally rolls a Physical save (1d20 vs save_target); on failure,
        rolls 1d12 on the Major Injury table and attaches that as a second Scar.
        Emits cwn.mortal_injury.declared and (when rolled) cwn.major_injury.roll."""
        if not isinstance(cfg, CwnConfig):
            raise ValueError(
                f"resolve_downed requires a CwnConfig; got {type(cfg).__name__!r}"
            )
        rounds = cfg.trauma.mortal_injury_rounds
        core.statuses.append(
            Status(
                text=f"Mortal Injury — dies in {rounds} rounds unless stabilized",
                severity=StatusSeverity.Scar,
            )
        )
        cwn_mortal_injury_declared_span(actor=core.name, rounds_to_die=rounds, _tracer=_tracer)

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
            cwn_major_injury_roll_span(
                actor=core.name, save_made=save_made, roll=major_roll,
                text=major_text, _tracer=_tracer,
            )

        return DownedResult(
            mortal=True, major=major, major_roll=major_roll,
            major_text=major_text, save_made=save_made,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_cwn_downed.py -n0 -q`
Expected: passed (4 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/cwn.py tests/game/ruleset/test_cwn_downed.py
git commit -m "feat(cwn): resolve_downed — Mortal Injury + Major Injury d12 on traumatic 0-HP"
```

---

## Task 9: Wire Trauma into the dispatch hit path + scene tag

Insert the Trauma seam into `sidequest/server/dispatch/dice.py`. The strike-damage block resolves `dmg_total` at line 457 and builds `damage_resolver_fn = lambda: dmg_total` at line 482 (read Task-author's map / the file region 396-492 first). Between those, call `ruleset.resolve_trauma(...)`, replace `dmg_total` with `lethality.final_total`, and — when `lethality.traumatic` — record a scene-wide `EncounterTag` ("Traumatic Hit Landed") on the encounter so `resolve_downed` (Task 11) can gate Major Injury.

This task's correctness is proven by an **OTEL behavior test** (CLAUDE.md: no source-grep wiring), not by reading the diff.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py`
- Test: `sidequest-server/tests/server/test_neon_combat_lethality_dispatch.py` (created here; extended in Tasks 10-11)

- [ ] **Step 1: Read the dispatch region**

Read `sidequest/server/dispatch/dice.py:396-510`. Identify: the bound `ruleset` variable, `snapshot`, `encounter`, `round_number`, `character_name`, `target` resolution (the opposite-side actor — see `_opposite_side_first_actor` usage in `beat_kinds.py` for the target convention), and how `dmg_total` flows into `damage_resolver_fn`. Note the existing `_watcher_publish("state_transition", {... "op": "damage_roll_resolved" ...})` call at 467 — you will add the trauma adjustment just after `dmg_total = dmg_resolved.total` (457) and before that publish.

- [ ] **Step 2: Write the failing OTEL test**

Create `sidequest-server/tests/server/test_neon_combat_lethality_dispatch.py`. Mirror the seating + dispatch idiom from `tests/server/test_space_opera_swn_combat_e2e.py` (read it first — it seats a real combat via `instantiate_encounter_from_trigger`, builds a PC with a full stat block, forces the d20 face to guarantee a hit, and calls `dispatch_dice_throw` directly). Adapt it to a **synthetic cwn pack fixture** (or load `neon_dystopia` if Task 14 content is already merged; for this server-only task, build a minimal in-memory cwn pack whose combat confrontation has a strike beat with a `damage_override` carrying `trauma_die`). Assert:

```python
def test_trauma_span_fires_on_cwn_strike_hit():
    # ... seat a cwn combat, force a hitting d20, drive dispatch_dice_throw with
    #     an InMemorySpanExporter installed ...
    span_names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.trauma.roll" in span_names  # the seam is reachable from dispatch


def test_traumatic_hit_records_scene_tag():
    # force the trauma die high enough to be traumatic, drive the strike, then:
    assert any(t.text == "Traumatic Hit Landed" for t in encounter.tags)
```

> If seating a full dispatch in a unit test is impractical, the minimum viable version of `test_trauma_span_fires_on_cwn_strike_hit` constructs the exact arguments `dispatch_dice_throw` passes and calls the real function — do NOT assert on source text. The space_opera e2e test is the proof-of-feasibility that a real dispatch drive works in this suite.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py -n0 -q`
Expected: FAIL — no `cwn.trauma.roll` span (seam not wired) and no scene tag.

- [ ] **Step 4: Wire the seam**

In `sidequest/server/dispatch/dice.py`, immediately after `dmg_total = dmg_resolved.total` (line 457), add:

```python
                # CWN Trauma seam (spec 2026-05-28): multiply rolled damage on a
                # Traumatic Hit, and flag the scene so a 0-HP drop this scene can
                # roll Major Injury. No-op for native/swn (base passthrough).
                _lethality = ruleset.resolve_trauma(
                    spec=damage_spec,
                    base_total=dmg_total,
                    cfg=pack.rules.ruleset_config() if pack and pack.rules else None,
                    rng=random,
                    actor=character_name,
                )
                dmg_total = _lethality.final_total
                if _lethality.traumatic:
                    from sidequest.game.encounter_tag import EncounterTag

                    if not any(t.text == "Traumatic Hit Landed" for t in encounter.tags):
                        encounter.tags.append(
                            EncounterTag(
                                text="Traumatic Hit Landed",
                                created_by=character_name,
                                target=None,
                                leverage=0,
                                fleeting=False,
                                created_turn=round_number,
                            )
                        )
```

(`random` is already imported in this module — it's used by `_generate_server_faces`. `ruleset`, `pack`, `encounter`, `character_name`, `round_number`, `damage_spec` are all in scope here. The `dmg_total` reassignment flows into the existing `_watcher_publish(... "total": dmg_total ...)` and `damage_resolver_fn = lambda: dmg_total` lines below.)

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py -n0 -q`
Expected: both tests pass.

- [ ] **Step 6: Regression — space_opera (swn) combat still works**

Run: `uv run pytest tests/server/test_space_opera_swn_combat_e2e.py -n0 -q`
Expected: pass — swn's `resolve_trauma` is the base passthrough, so `dmg_total` is unchanged.

- [ ] **Step 7: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_neon_combat_lethality_dispatch.py
git commit -m "feat(cwn): wire Trauma into strike dispatch + Traumatic-Hit scene tag"
```

---

## Task 10: Wire Shock into the dispatch miss path

The strike block currently resolves damage ONLY on a hit (line 406: `resolved.outcome not in (Fail, CritFail)`). Add an `else`/miss branch: when the beat is a strike, the bound ruleset returns Shock chip damage, and the target's Melee AC is at/below the weapon's Shock rating, apply that chip to the target's HP (via `apply_beat_hp_channel` with `channel="strike"`, mitigation 0) and emit the span. No-op for swn/native (base `resolve_shock` returns 0).

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py`
- Test: `sidequest-server/tests/server/test_neon_combat_lethality_dispatch.py` (extend)

- [ ] **Step 1: Add the failing test**

Append to `tests/server/test_neon_combat_lethality_dispatch.py`:

```python
def test_shock_chips_hp_on_miss():
    # seat a cwn combat where the player wields a melee weapon with shock>0,
    # force the d20 to MISS (e.g. face=1), and seat the opponent with a low
    # Melee AC (<= shock). Drive dispatch; assert:
    span_names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.shock.applied" in span_names
    assert target_core.hp.current < target_core.hp.max  # chip landed despite the miss
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py::test_shock_chips_hp_on_miss -n0 -q`
Expected: FAIL — miss path applies no damage today.

- [ ] **Step 3: Wire the miss branch**

In `sidequest/server/dispatch/dice.py`, inside the strike block, add a sibling branch for the miss case (the strike block currently only acts when `resolved.outcome not in (Fail, CritFail)`; add handling for the Fail/CritFail case). After resolving `actor_core`/`damage_spec` for the miss (you need the weapon spec to read `shock`), call:

```python
        # CWN Shock seam: a melee weapon chips fixed damage on a MISS vs a
        # low-Melee-AC target. No-op for native/swn (base returns 0).
        if damage_channel == "strike" and resolved.outcome in (RollOutcome.Fail, RollOutcome.CritFail):
            actor_core = snapshot.find_creature_core(character_name)
            shock_spec = ruleset.resolve_damage(beat=beat, actor_core=actor_core, pack=pack)
            target_name = _opposite_side_first_actor(encounter, actor.side)  # import if needed
            target_core = snapshot.find_creature_core(target_name) if target_name else None
            if shock_spec is not None and target_core is not None:
                chip = ruleset.resolve_shock(
                    spec=shock_spec,
                    target_melee_ac=int(getattr(target_core, "armor_class", 10)),
                    actor=character_name,
                )
                if chip > 0:
                    from sidequest.game.beat_kinds import apply_beat_hp_channel

                    apply_beat_hp_channel(
                        target=target_core, channel="strike", damage_total=chip,
                        target_mitigation=0, source_beat_id=f"{payload.beat_id}:shock",
                    )
```

(Read `beat_kinds.py` for the exact `_opposite_side_first_actor` signature — it takes `(enc, side)`. Import it from `sidequest.game.beat_kinds` if not already imported. `RollOutcome` is already imported in dice.py.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py -n0 -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_neon_combat_lethality_dispatch.py
git commit -m "feat(cwn): wire Shock-on-miss into strike dispatch"
```

---

## Task 11: Wire `resolve_downed` at the 0-HP moment

After `apply_result = ruleset.apply_beat(...)` (line 484), the strike may have dropped the target to 0 HP (`apply_beat` calls `check_hp_depletion` internally and sets `apply_result.resolved`). When the bound ruleset is CWN and the target is now at 0 HP, call `resolve_downed` to attach the Mortal/Major Injury statuses and emit the spans. The Physical save target is computed here via `ruleset.save_params(...)` for the downed actor (PC stats from `Character.stats`; opponent from `opponent_default_stats`).

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py`
- Test: `sidequest-server/tests/server/test_neon_combat_lethality_dispatch.py` (extend)

- [ ] **Step 1: Add the failing test**

Append to `tests/server/test_neon_combat_lethality_dispatch.py`:

```python
def test_downed_target_gets_mortal_injury():
    # seat a cwn combat, seat the opponent with hp=1 so one hit drops it, force a
    # hitting d20 and enough damage to reach 0. Drive dispatch; assert:
    span_names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.mortal_injury.declared" in span_names
    assert any("Mortal Injury" in s.text for s in target_core.statuses)


def test_downed_after_traumatic_hit_rolls_major():
    # as above but ensure a Traumatic Hit landed earlier (scene tag present), then
    # drop the target. Assert the Major Injury span fired:
    span_names = [s.name for s in exporter.get_finished_spans()]
    assert "cwn.major_injury.roll" in span_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py -n0 -q`
Expected: the two new tests FAIL — no mortal/major span.

- [ ] **Step 3: Wire the 0-HP hook**

In `sidequest/server/dispatch/dice.py`, after the `apply_result = ruleset.apply_beat(...)` call (line 484) and its `skipped_reason` guard, add:

```python
        # CWN downed seam: if this strike dropped a target to 0 HP, resolve the
        # Mortal Injury (always) and Major Injury (only if a Traumatic Hit landed
        # this scene). No-op for native/swn (base resolve_downed returns None).
        _down_name = _opposite_side_first_actor(encounter, actor.side)
        _down_core = snapshot.find_creature_core(_down_name) if _down_name else None
        if _down_core is not None and _down_core.hp.current <= 0:
            _cfg = pack.rules.ruleset_config() if pack and pack.rules else None
            _scene_traumatic = any(t.text == "Traumatic Hit Landed" for t in encounter.tags)
            # Physical save target for the downed actor. Resolve its stats+level:
            #   PC: snapshot Character.stats + level; opponent: opponent_default_stats.
            # Read how the space_opera e2e / hp_depletion path resolves opponent
            # stats and mirror it; pass save=cfg.trauma.major_injury_save.
            _save_target = _physical_save_target_for(
                ruleset=ruleset, snapshot=snapshot, name=_down_name, cfg=_cfg,
            )
            _downed = ruleset.resolve_downed(
                core=_down_core,
                save_target=_save_target,
                scene_traumatic=_scene_traumatic,
                cfg=_cfg,
                rng=random,
            )
```

Add a small module-level helper `_physical_save_target_for(...)` near the other dice.py helpers. It computes the save target via `ruleset.save_params(stats=<downed actor stats>, save=cfg.trauma.major_injury_save, level=<level>, label="major-injury", cfg=cfg).difficulty`, falling back to a fixed `15` ONLY if the ruleset has no save_params (it always does for cwn). Read how the dispatch resolves a Character's stats (the check-roll path earlier in `dispatch_dice_throw` already builds a `stats` dict for the actor — reuse that resolution for the downed actor). For an opponent, read its `opponent_default_stats` off the confrontation def (`ConfrontationDef.opponent_default_stats`).

> Concretely: the downed target in a single-PC-vs-mook fight is usually the **opponent**, whose stats come from `opponent_default_stats`. Mirror the stat-resolution the existing `attack_params`/initiative path uses for opponents (search dice.py for where opponent stats are read for the d20 roll). The PC-downed case (opponent_victory) uses the PC's `Character.stats`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_neon_combat_lethality_dispatch.py -n0 -q`
Expected: all pass.

- [ ] **Step 5: Regression — swn combat still resolves cleanly at 0 HP**

Run: `uv run pytest tests/server/test_space_opera_swn_combat_e2e.py -n0 -q`
Expected: pass — swn `resolve_downed` is the base no-op (returns None), so the 0-HP path is unchanged for space_opera.

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_neon_combat_lethality_dispatch.py
git commit -m "feat(cwn): wire resolve_downed at 0-HP (Mortal + Major Injury)"
```

---

## Task 12: `stabilize_mortal_injury` narrator tool

A Mortal Injury kills at the end of `mortal_injury_rounds` unless stabilized. Stabilization is a Dex/Heal or Int/Heal check vs difficulty `8 + rounds elapsed` (spec line 124). Mirror plan 2's `adjust_system_strain` tool exactly (same `@tool` decorator, `ToolContext`, `ToolResult`, registration in `tools/__init__.py`). The tool clears the Mortal Injury Status on success (and downgrades to a "Frail" Wound per spec line 124: "Recovers at 1 HP + Frail") or, when the timer has elapsed, records death.

**Files:**
- Create: `sidequest-server/sidequest/agents/tools/stabilize_mortal_injury.py`
- Modify: `sidequest-server/sidequest/agents/tools/__init__.py`
- Test: `sidequest-server/tests/agents/tools/test_stabilize_mortal_injury_tool.py`

- [ ] **Step 1: Read the tool pattern**

Read `sidequest/agents/tools/adjust_system_strain.py` in full (plan 2) and `sidequest/agents/tools/__init__.py` (the registration list). The new tool mirrors it: `AdjustSystemStrainArgs` → `StabilizeMortalInjuryArgs`; the `@tool(name=..., category=ToolCategory.WRITE)` decorator; `ctx.repository.load()` / `ctx.genre_pack` / `snapshot.find_creature_core` / `ctx.repository.save` / `ctx.otel_span.set_attribute`. Reuse the cwn-only guard verbatim.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/agents/tools/test_stabilize_mortal_injury_tool.py`, mirroring `tests/agents/tools/test_adjust_system_strain_tool.py`'s fixture (read it). Build a minimal cwn snapshot with one character carrying a Mortal Injury Status, invoke the tool, and assert:

```python
def test_stabilize_success_clears_mortal_and_adds_frail(...):
    # force a passing Heal check (high d20 face / high skill)
    result = await stabilize_mortal_injury(args(actor="Jax", skill="Heal", attribute="Reflex",
                                                rounds_elapsed=1, roll=18), ctx)
    core = ctx.snapshot.find_creature_core("Jax")
    assert not any("Mortal Injury" in s.text for s in core.statuses)
    assert any("Frail" in s.text for s in core.statuses)


def test_stabilize_failure_keeps_mortal(...):
    result = await stabilize_mortal_injury(args(actor="Jax", roll=2, rounds_elapsed=1), ctx)
    core = ctx.snapshot.find_creature_core("Jax")
    assert any("Mortal Injury" in s.text for s in core.statuses)


def test_tool_is_cwn_only(...):
    # a non-cwn pack raises ValueError (mirror adjust_system_strain guard test)
    ...
```

> The exact arg shape (whether the d20 face is passed in or rolled server-side) should match how `adjust_system_strain`'s test drives its tool. If the tool rolls server-side, inject the rng/face the same way the dispatch tests do; the assertion is on the Status mutation + OTEL, not the roll mechanism.

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/agents/tools/test_stabilize_mortal_injury_tool.py -n0 -q`
Expected: FAIL — tool does not exist.

- [ ] **Step 4: Implement the tool**

Create `sidequest-server/sidequest/agents/tools/stabilize_mortal_injury.py`, mirroring `adjust_system_strain.py`. Core logic: difficulty = `8 + args.rounds_elapsed`; on success (Heal check meets/exceeds difficulty) remove the Mortal Injury Status and append `Status(text="Frail — recovering at 1 HP", severity=StatusSeverity.Wound)`; on failure leave it. Set `ctx.otel_span` attributes (`tool.stabilize.actor`, `.success`, `.difficulty`, `.rounds_elapsed`). Return `ToolResult.ok({...})`.

Then register in `sidequest/agents/tools/__init__.py` — add `stabilize_mortal_injury,  # noqa: F401` to the import block alongside `adjust_system_strain` (Step 1 finding).

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/agents/tools/test_stabilize_mortal_injury_tool.py -n0 -q`
Expected: passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/tools/stabilize_mortal_injury.py sidequest/agents/tools/__init__.py tests/agents/tools/test_stabilize_mortal_injury_tool.py
git commit -m "feat(cwn): stabilize_mortal_injury narrator tool (Heal check vs 8+rounds)"
```

---

## Task 13: Neon content — weapon Trauma/Shock + armor AC/soak

Working directory: `sidequest-content`. File: `genre_packs/neon_dystopia/inventory.yaml` (read it in full first — weapons at ~lines 9-55, armor at ~57-79; current items carry no `damage`/`armor_class`/`mitigation`). Add CWN combat numbers, drawing weapon dice from the CWN SRD and `space_opera/inventory.yaml` as the format precedent.

- [ ] **Step 1: Read both inventories**

Read `genre_packs/neon_dystopia/inventory.yaml` and `genre_packs/space_opera/inventory.yaml` (the latter shows the exact `damage: {dice, bonus}` and `mitigation:` field placement on a CatalogItem).

- [ ] **Step 2: Add weapon damage + Trauma/Shock**

For each weapon item, add a `damage` block. Use these CWN-faithful numbers (ranged weapons get Trauma; the katana/mantis_blades are melee and get Shock):

```yaml
# smart_pistol
    damage: {dice: "1d6", bonus: 0, trauma_die: "1d8", trauma_rating: 2}
# assault_rifle
    damage: {dice: "1d10", bonus: 0, trauma_die: "1d10", trauma_rating: 2}
# katana (melee)
    damage: {dice: "1d8", bonus: 0, trauma_die: "1d8", trauma_rating: 2, shock: 2}
# mantis_blades (melee cyberware)
    damage: {dice: "1d8", bonus: 1, trauma_die: "1d10", trauma_rating: 3, shock: 4}
```

(Exact item ids per the file — match what Step 1 shows. Place `damage:` as a sibling of the existing item fields, indented as a mapping value. If a weapon id differs, map by name/role.)

- [ ] **Step 3: Add armor AC + soak**

For each armor item, add `armor_class` and `mitigation`:

```yaml
# armored_jacket
    armor_class: 13
    mitigation: 1
# subdermal_armor (cyberware)
    armor_class: 15
    mitigation: 2
```

- [ ] **Step 4: Sanity-check YAML**

Run (from `sidequest-content`): `python -c "import yaml; yaml.safe_load(open('genre_packs/neon_dystopia/inventory.yaml')); print('OK')"`
Expected: OK.

- [ ] **Step 5: Commit (content repo)**

```bash
git add genre_packs/neon_dystopia/inventory.yaml
git commit -m "feat(neon): weapon Trauma/Shock + armor AC/soak (CWN combat numbers)"
```

---

## Task 14: Neon content — retire momentum combat, add HP/AC combat + trauma config

File: `genre_packs/neon_dystopia/rules.yaml`. Retire the momentum `combat` confrontation (current lines 196-241) and rebuild it on `hp_depletion`, mirroring `space_opera`'s personal `combat` (rules.yaml:318-394). Add the `cwn.trauma` config block and a `combat_lethality` custom-rule. Leave `net_combat`, `negotiation`, and `chase` untouched.

- [ ] **Step 1: Read the precedent**

Read `genre_packs/space_opera/rules.yaml:318-394` (the personal `combat` confrontation: `resolution_mode: beat_selection`, `win_condition: hp_depletion`, `opponent_default_stats` with reserved `hp`/`armor_class`/`dexterity`, strike beats with `damage_channel: strike` + `attack_bonus` + `combat_skill`).

- [ ] **Step 2: Add the `cwn.trauma` config block**

In `genre_packs/neon_dystopia/rules.yaml`, under the existing `cwn:` block (after `system_strain:`, ~line 25), add:

```yaml
  trauma:
    default_trauma_target: 6
    mortal_injury_rounds: 6
    major_injury_save: physical
```

- [ ] **Step 3: Replace the momentum `combat` confrontation**

Delete the entire `- type: combat` block (lines 196-241) and replace it with an HP/AC version. Weapons supply damage from inventory (Task 13), so the strike beats do NOT need a `damage_override` (unlike space_opera's ship guns); they declare `damage_channel: strike` + `attack_bonus`/`combat_skill` and the dispatch resolves the wielded weapon's `damage`:

```yaml
  - type: combat
    label: Street Combat
    intent_verbs: [shoot, fire, attack, fight, stab, slash, gun, kill]
    on_intent_mismatch: reprompt
    category: combat
    # CWN personal combat: attack-vs-AC + hp_depletion on the ablative HpPool.
    # Trauma/Shock/Mortal/Major Injury layer on via the cwn ruleset module.
    resolution_mode: beat_selection
    win_condition: hp_depletion
    opponent_default_stats:
      Brawn: 10
      Reflex: 10
      Body: 10
      Instinct: 10
      # Reserved combat-seed keys (not ability scores) — seed the runtime
      # CreatureCore for hp_depletion. hp = HP pool; armor_class = ascending AC
      # the attack rolls against; dexterity = SWN 1d8+DEX initiative.
      # Street mook: AC 13 (armored jacket), HP 8, drops in ~2-3 solid hits.
      hp: 8
      armor_class: 13
      dexterity: 11
    beats:
      - id: shoot
        label: Shoot
        kind: strike
        base: 2
        stat_check: Reflex
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        effect: "Target takes weapon damage"
        narrator_hint: Muzzle flash in neon rain. Chrome and concrete.
      - id: melee
        label: Blade Work
        kind: strike
        base: 2
        stat_check: Brawn
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        effect: "Close-quarters strike; a miss with a Shock weapon still chips"
        narrator_hint: Monowire and mantis blades. Up close it's wet work.
      - id: take_cover
        label: Take Cover
        kind: brace
        base: 1
        stat_check: Reflex
        effect: "Reduce incoming damage behind urban debris"
        narrator_hint: Dumpster, concrete pillar, burned-out car — the city is cover.
      - id: disengage
        label: Disengage
        kind: push
        stat_check: Cool
        consequence: "Combat ends — vanish into the crowd or the net"
        narrator_hint: Drop the weapon, pull your hood up, slip between bodies.
    mood: combat
```

(The genre-distinct `netrun` mid-firefight beat from the old momentum combat is dropped here — cyberspace combat lives in the untouched `net_combat` confrontation, and plan 4's `net_run`. If you want to preserve a hack-and-shoot beat, add it as a non-strike `angle` beat; YAGNI for this plan.)

- [ ] **Step 4: Add the `combat_lethality` custom-rule prose**

Under `custom_rules:` (after `system_strain:`, ~line 71), add:

```yaml
  combat_lethality: >-
    CWN combat is fast and deadly. Attacks roll to-hit vs the target's Armor
    Class; on a hit the weapon's damage ablates HP after armor soak. Lethal
    weapons also roll Trauma — a Traumatic Hit multiplies damage (a shotgun or
    monoblade can gib a mook). At 0 HP a character takes a Mortal Injury: they
    die within 6 rounds unless someone stabilizes them (a Heal check vs 8 +
    rounds elapsed) — call the stabilize_mortal_injury tool. If a Traumatic Hit
    landed in the fight, a downed character also risks a Major Injury (a Physical
    save; on failure, a permanent table result — lost eye, severed limb, worse).
    Never narrate a kill, a Trauma multiplier, or an injury you did not let the
    engine roll. The dice and the tools are the truth; your prose dramatizes them.
```

- [ ] **Step 5: Sanity-check YAML**

Run: `python -c "import yaml; d=yaml.safe_load(open('genre_packs/neon_dystopia/rules.yaml')); types=[c['type'] for c in d['confrontations']]; print(types); assert 'combat' in types and 'net_combat' in types and 'chase' in types and 'negotiation' in types; print('OK')"`
Expected: prints the four confrontation types and `OK`.

- [ ] **Step 6: Commit (content repo)**

```bash
git add genre_packs/neon_dystopia/rules.yaml
git commit -m "feat(neon): retire momentum combat -> CWN HP/AC combat + trauma config + lethality prose"
```

---

## Task 15: End-to-end wiring test — neon loads and drives lethality through dispatch

Per CLAUDE.md testing doctrine (behavior/OTEL, never source-grep): load the **real** `neon_dystopia` pack, seat its `combat` confrontation, build a character, drive a strike through the production dispatch, and assert the engine truth + `cwn.*` OTEL. This proves the pack→ruleset→dispatch→lethality chain end to end (the content from Tasks 13-14 + the engine from Tasks 1-12). This test lives in the **server** repo but depends on the **content** changes — run it after both are committed locally (the content repo is on disk via `SIDEQUEST_GENRE_PACKS`).

**Files:**
- Create: `sidequest-server/tests/genre/test_neon_combat_lethality_wiring.py`

Working directory: `sidequest-server`.

- [ ] **Step 1: Write the test**

Mirror the content-on-disk guard idiom from `tests/genre/test_neon_loads_cwn.py` (skip when content absent) and the dispatch-drive idiom from Task 9's test. The test must:

1. `load_pack("neon_dystopia")`; assert `pack.rules.cwn.trauma.default_trauma_target == 6` and the `combat` confrontation has `win_condition == "hp_depletion"` and at least one strike beat with `damage_channel == "strike"` (config + content wiring).
2. Assert the momentum `combat` is gone (no `player_metric`/`opponent_metric` on the `combat` confrontation) and `net_combat` still exists with its dials (proves the right confrontation was retired).
3. Seat the `combat` confrontation, build a neon character, equip a weapon with a `trauma_die` (from the pack catalog), set up an `InMemorySpanExporter`, force a hitting d20 and a high trauma die, and drive `dispatch_dice_throw`. Assert `cwn.trauma.roll` fired (pack→module→dispatch reachable).
4. Seat the opponent with `hp: 1`, drive a hitting strike, and assert `cwn.mortal_injury.declared` fired and the opponent core carries a "Mortal Injury" Status.

```python
@pytest.mark.skipif(not _HAS_CONTENT, reason="sidequest-content not on disk")
def test_neon_combat_lethality_end_to_end():
    pack = load_pack("neon_dystopia")
    assert pack.rules.cwn.trauma.default_trauma_target == 6
    combat = next(c for c in pack.rules.confrontations if c.type == "combat")
    assert combat.win_condition == "hp_depletion"
    # ... seat, build, equip, drive dispatch, assert cwn.trauma.roll + mortal injury ...
```

- [ ] **Step 2: Run the test**

Run: `uv run pytest tests/genre/test_neon_combat_lethality_wiring.py -n0 -q`
Expected: 1 passed (NOT skipped). If it skips, `load_pack("neon_dystopia")` raised — surface the exception (a real pack-load/validation failure from Tasks 13-14) rather than accepting the skip.

- [ ] **Step 3: Commit**

```bash
git add tests/genre/test_neon_combat_lethality_wiring.py
git commit -m "test(cwn): wiring test — neon loads + drives combat lethality through dispatch (OTEL)"
```

---

## Task 16: Full gate — lint, types, full suite

**Files:** none (verification only). Working directory: `sidequest-server` (+ a YAML lint already done in Tasks 13-14).

- [ ] **Step 1: Lint and format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors in this plan's files. If `ruff format --check` flags THIS plan's files, run `uv run ruff format <those files>`, re-stage, commit as `style:`. Do NOT touch pre-existing issues in untouched files.

- [ ] **Step 2: Type-check the touched modules**

Run: `uv run pyright sidequest/genre/models/inventory.py sidequest/genre/models/rules.py sidequest/game/lethality.py sidequest/game/ruleset/base.py sidequest/game/ruleset/cwn.py sidequest/telemetry/spans/cwn.py sidequest/server/dispatch/dice.py sidequest/agents/tools/stabilize_mortal_injury.py`
Expected: 0 NEW errors. `dice.py` may carry pre-existing errors — compare against the pre-plan commit and report new vs pre-existing.

- [ ] **Step 3: Full test suite**

Run: `uv run pytest -n auto -q`
Expected: no NEW failures. Pay attention to: the space_opera SWN combat e2e (must still pass — base lethality hooks are no-ops for swn), the routing-completeness telemetry test, the native ruleset tests, and any pack-load test. Classify any failure as new-vs-pre-existing against the pre-plan base commit. (Per the plan-2 handoff, ~24 failures + 17 errors are pre-existing DB-infra/asset/corpus/lore-RAG and unrelated — confirm the count is unchanged.)

- [ ] **Step 4: Commit any fixups**

```bash
git add -A
git commit -m "chore(cwn): satisfy lint/type/test gate for combat lethality"
```

(Stage only this plan's files; if `git add -A` would sweep unrelated changes, stage specifically.)

- [ ] **Step 5: Push both branches and open PRs (content first, then server)**

```bash
# content repo
git push -u origin feat/neon-combat-lethality
# server repo
git push -u origin feat/neon-cwn-combat-lethality
```

Open the content PR against `develop`, merge it, then open + merge the server PR against `develop` (server CI checks out content, so content must land first — the plan-2 order). Reconcile local `develop` to origin after each merge.

---

## Self-Review (completed during authoring)

**Spec coverage (Combat lethality section, spec lines 111-132):**
- "combat moves to HP + Armor Class on the ablative HpPool" → Task 14 (hp_depletion `combat`, mirrors space_opera) + the existing strike dispatch (no new HP engine needed — reused).
- "Hit → weapon damage die + attr mod, reduced first by armor Damage Soak" → existing `apply_beat_hp_channel` mitigation + Task 13 armor `mitigation`.
- "Trauma: roll the weapon's Trauma Die vs Trauma Target; on a Traumatic Hit multiply damage by Trauma Rating" → Task 6 `resolve_trauma` + Task 1 DamageSpec fields + Task 9 dispatch wiring.
- "Shock: melee weapon chips X on a miss vs Melee AC ≤ shock rating" → Task 7 `resolve_shock` + Task 10 miss-path wiring (v1 single-number simplification, logged as deviation).
- "0 HP from lethal damage → Mortal Injury: dies end of 6th round unless stabilized; recovers at 1 HP + Frail" → Task 8 `resolve_downed` (Mortal status) + Task 12 `stabilize_mortal_injury` tool (Heal vs 8+rounds, Frail on success).
- "0 HP in a scene where a Traumatic Hit landed → Major Injury: Physical save; on failure 1d12 table" → Task 8 (`scene_traumatic` gate + save + d12) + Task 4 table + Task 9 scene tag + Task 11 0-HP wiring.
- "weapon dice / Trauma Die/Target/Rating / Shock and armor AC / Damage Soak are content" → Tasks 1 (model), 13 (neon content).
- "OTEL: cwn.trauma.roll, cwn.shock.applied, cwn.major_injury.roll; HP via state_patch_hp" → Task 5 (+ cwn.mortal_injury.declared added for the GM lie-detector); HP deltas continue through the existing `state_patch.hp` (unchanged).
- "retire the momentum `combat` confrontation for neon; social/chase stay dial-based" → Task 14 (combat rebuilt, net_combat/negotiation/chase untouched).

**Out of scope (correctly absent):** `net_run` hacking (plan 4); per-armor Trauma-Target raises (deviation-noted simplification); a `non_lethal` beat flag (YAGNI).

**Placeholder scan:** Tasks 1-8 and 12 contain literal code/tables (the engine logic is fully concrete and exhaustively unit-tested). Tasks 9-11 (dispatch wiring) and 15 (e2e) intentionally instruct the implementer to read the specific dispatch region / space_opera e2e and mirror them, because the exact opponent-stat resolution and seating idiom are pattern-bound and best matched against live code — but every seam has an explicit code block for the insertion and an OTEL-behavior test (never source-grep) proving reachability. Tasks 13-14 (content) give exact YAML.

**Type/name consistency:** `DamageSpec` fields (`trauma_die`/`trauma_rating`/`trauma_target`/`shock`), `CatalogItem.armor_class`, `TraumaConfig` (`default_trauma_target`/`mortal_injury_rounds`/`major_injury_save`), `LethalityResult` (`base_total`/`final_total`/`traumatic`/`trauma_roll`/`trauma_target`), `DownedResult` (`mortal`/`major`/`major_roll`/`major_text`/`save_made`), the three module methods (`resolve_trauma(spec, base_total, cfg, rng, actor, _tracer)`, `resolve_shock(spec, target_melee_ac, actor, _tracer)`, `resolve_downed(core, save_target, scene_traumatic, cfg, rng, _tracer)`), the four spans (`cwn.trauma.roll`/`cwn.shock.applied`/`cwn.mortal_injury.declared`/`cwn.major_injury.roll`), and the scene tag text `"Traumatic Hit Landed"` are used identically across Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15. The span helper names match between Task 5 (definitions) and Tasks 6-8 (calls).
