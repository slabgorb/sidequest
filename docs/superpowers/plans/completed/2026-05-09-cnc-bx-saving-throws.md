# C&C B/X Saving Throws — Implementation Plan

> **COMPLETED via sprint stories — checkbox state never updated.** Resolver lives at `sidequest-server/sidequest/game/saves.py` and implements the spec at `docs/superpowers/specs/2026-05-09-cnc-bx-saving-throws-design.md`: `resolve_save`, `apply_spell_effect`, `SaveResult`, `SpellEffectOutcome`, hard-fail-loud on missing class or save table. Schema (`SaveCategory`, `SavingThrowsTable`) lives in `sidequest-server/sidequest/genre/models/rules.py` and `character.py`. All four C&C classes carry per-class `saving_throws` tables in `classes.yaml`. Plan body left intact as historical reference.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire B/X saving throws into Caverns & Claudes — schema (`SaveCategory`, `SavingThrowsTable`, per-class table on `ClassDef`), thin resolver that rides existing `resolve_opposed_check` with a synthetic threat-as-opponent (the "circle says POISON" model), pack-load validation, OTEL span, narration_apply integration for `learned_v1` spells, content authoring, and tests.

**Architecture:** Reuse `resolve_opposed_check` from `sidequest/game/opposed_check.py` by adding a single `fixed_opponent_roll: int | None = None` kwarg. The save resolver synthesizes a one-shot `EncounterActor` for the threat, pins its d20 to the B/X B26 table target, and lets the existing shift-bands tier classifier give us success/critical for free. Spell catalog already has `SpellSave.stat` + `effect`; we add `category` (which B26 column) and `requires_mind` (skip mindless targets entirely). Save call site is the existing `_apply_magic_working` seam in `narration_apply.py`, immediately after `apply_working` returns and before OTEL span emission.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest, OpenTelemetry, uv. Server repo `sidequest-server/`, content repo `sidequest-content/`.

**Spec:** `docs/superpowers/specs/2026-05-09-cnc-bx-saving-throws-design.md` (orchestrator repo).

---

## File Structure

### Server changes (`sidequest-server/`)

| Path | Action | Responsibility |
|---|---|---|
| `sidequest/genre/models/rules.py` | Modify | Add `SaveCategory` enum (5 B26 columns) and `SavingThrowsTable` model |
| `sidequest/genre/models/character.py` | Modify | Add `ClassDef.saving_throws: SavingThrowsTable \| None`; add `NpcArchetype.saves_as_class: str = "Fighter"` |
| `sidequest/magic/spell_catalog.py` | Modify | Add `SpellSave.category` (default `rods_staves_spells`), Dragon Breath stat-must-be-null validator, `Spell.requires_mind: bool = False` |
| `sidequest/game/opposed_check.py` | Modify | Add `fixed_opponent_roll: int \| None = None` kwarg to `resolve_opposed_check` |
| `sidequest/game/saves.py` | **Create** | `resolve_save()`, `SaveResult`, `apply_spell_effect()` |
| `sidequest/genre/loader.py` | Modify | Pack-load validation: every class declares `saving_throws` when pack has spell catalogs |
| `sidequest/server/narration_apply.py` | Modify | After `_apply_magic_working`, run save resolution + apply spell effect for every target |
| `sidequest/telemetry/spans/encounter.py` | Modify | Add `SPAN_ENCOUNTER_SAVING_THROW_RESOLVED` declaration + `SpanRoute` |

### Server tests (`sidequest-server/tests/`)

| Path | Action | Responsibility |
|---|---|---|
| `tests/genre/test_models/test_saving_throws.py` | **Create** | `SaveCategory` enum closedness; `SavingThrowsTable` value range 2..20; `target_for()` lookup |
| `tests/genre/test_models/test_character.py` | Modify | `ClassDef.saving_throws` accepts table; `NpcArchetype.saves_as_class` default Fighter + override |
| `tests/magic/test_spell_catalog.py` | Modify | `SpellSave.category` defaults; dragon_breath rejects non-null `stat`; `Spell.requires_mind` default False |
| `tests/genre/test_pack_load.py` | Modify | C&C `classes.yaml` declares `saving_throws` for every class; numbers match B26 |
| `tests/game/test_opposed_check_fixed_roll.py` | **Create** | `fixed_opponent_roll` kwarg pins opponent's d20; existing path unchanged when omitted |
| `tests/game/test_saves.py` | **Create** | `resolve_save` outcomes per class+category; nat20/nat1 crit; ability=None ignores defender stat; mindless gate handled by caller |
| `tests/server/test_narration_apply_save_integration.py` | **Create** | Spell with save: `negates` triggers save call; mindless+`requires_mind` skips save and skips effect; `effect: none` spell skips save |
| `tests/telemetry/test_saving_throw_span.py` | **Create** | `encounter.saving_throw_resolved` emits with required attrs |

### Content changes (`sidequest-content/`)

| Path | Action | Responsibility |
|---|---|---|
| `genre_packs/caverns_and_claudes/classes.yaml` | Modify | Add `saving_throws` block (5 ints) to each of fighter/mage/cleric/thief, verbatim from B/X B26 |
| `genre_packs/caverns_and_claudes/spells/cc_arcane_l1.yaml` | Modify | Add `category: rods_staves_spells` to every spell with `effect != none` |
| `genre_packs/caverns_and_claudes/spells/cc_divine_l1.yaml` | Modify | Same — add `category` to each save block |
| `genre_packs/caverns_and_claudes/worlds/caverns_sunden/<archetypes>` | Modify | Add `saves_as_class: Mage` / `Cleric` / `Thief` where canon supports; default Fighter is fine |

---

## Conventions

- All `pytest`, `ruff`, and `uv` commands run from the **server subrepo root**: `cd sidequest-server && uv run pytest ...`. The `cd` is shown explicitly in each command for clarity.
- All commits target the **server subrepo's tracked branch** (per `repos.yaml`: `develop`).
- Content commits target the **content subrepo's tracked branch** (per `repos.yaml`: `develop`).
- Each task ends with a commit. Run `uv run ruff format .` and `uv run ruff check .` before each commit; if either fails, fix and recommit.
- Test names use `snake_case`. Module-level docstrings explain *what* the module covers; function docstrings only when behavior is non-obvious.
- B/X reference: `~/Downloads/D&D_Basic_Set_Rulebook_(B_X_ed.)_(Basic).pdf`. Saving Throws table B26. Ability adjustments B7.

---

## Task 1: Add `SaveCategory` enum and `SavingThrowsTable` model

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (append after `MoraleDef`, around line 207)
- Create: `sidequest-server/tests/genre/test_models/test_saving_throws.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_models/test_saving_throws.py`:

```python
"""Tests for SaveCategory enum and SavingThrowsTable model (B/X B26 port)."""

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import SaveCategory, SavingThrowsTable


def test_save_category_enum_closed():
    assert {c.value for c in SaveCategory} == {
        "death_ray_or_poison",
        "magic_wands",
        "paralysis_or_stone",
        "dragon_breath",
        "rods_staves_spells",
    }


def _fighter_table() -> SavingThrowsTable:
    return SavingThrowsTable(
        death_ray_or_poison=12,
        magic_wands=13,
        paralysis_or_stone=14,
        dragon_breath=15,
        rods_staves_spells=16,
    )


def test_saving_throws_table_constructs():
    t = _fighter_table()
    assert t.dragon_breath == 15
    assert t.rods_staves_spells == 16


def test_saving_throws_table_target_for_lookup():
    t = _fighter_table()
    assert t.target_for(SaveCategory.dragon_breath) == 15
    assert t.target_for(SaveCategory.rods_staves_spells) == 16


def test_saving_throws_table_rejects_below_2():
    with pytest.raises(ValidationError, match="saving throw"):
        SavingThrowsTable(
            death_ray_or_poison=1,
            magic_wands=13,
            paralysis_or_stone=14,
            dragon_breath=15,
            rods_staves_spells=16,
        )


def test_saving_throws_table_rejects_above_20():
    with pytest.raises(ValidationError, match="saving throw"):
        SavingThrowsTable(
            death_ray_or_poison=12,
            magic_wands=13,
            paralysis_or_stone=14,
            dragon_breath=15,
            rods_staves_spells=21,
        )


def test_saving_throws_table_extra_forbid():
    with pytest.raises(ValidationError):
        SavingThrowsTable(
            death_ray_or_poison=12,
            magic_wands=13,
            paralysis_or_stone=14,
            dragon_breath=15,
            rods_staves_spells=16,
            crit_save=99,  # not a real column
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_saving_throws.py -v`
Expected: FAIL with `ImportError: cannot import name 'SaveCategory'`

- [ ] **Step 3: Implement `SaveCategory` and `SavingThrowsTable`**

Append to `sidequest-server/sidequest/genre/models/rules.py` (after the `MoraleDef` class ending around line 207):

```python
class SaveCategory(StrEnum):  # noqa: UP042 — matches project convention
    """B/X B26 saving-throw columns. Closed enum — adding a new
    category is a deliberate edit, not a string-typo accident."""

    death_ray_or_poison = "death_ray_or_poison"
    magic_wands = "magic_wands"
    paralysis_or_stone = "paralysis_or_stone"
    dragon_breath = "dragon_breath"
    rods_staves_spells = "rods_staves_spells"


class SavingThrowsTable(BaseModel):
    """Per-class B/X saving-throw target numbers (B26).

    Targets are flat per Basic-set canon (B26 footnote): no level
    adjustments. Per-level scaling is an Expert-set feature; if/when
    XP advancement crosses a level boundary in C&C, this model
    becomes a per-level dict.
    """

    model_config = {"extra": "forbid"}

    death_ray_or_poison: int
    magic_wands: int
    paralysis_or_stone: int
    dragon_breath: int
    rods_staves_spells: int

    @model_validator(mode="after")
    def _validate(self) -> SavingThrowsTable:
        for f, v in self.model_dump().items():
            if not (2 <= v <= 20):
                raise ValueError(
                    f"saving throw {f}={v} outside legal d20 range 2..20"
                )
        return self

    def target_for(self, category: SaveCategory) -> int:
        return getattr(self, category.value)
```

If `StrEnum` and `model_validator` are not yet imported in `rules.py`, verify the existing imports — both are already used by `MoraleTrigger` and `MoraleDef` (added by PR #220), so no new imports needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_saving_throws.py -v`
Expected: PASS — 6 tests pass.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/genre/models/rules.py tests/genre/test_models/test_saving_throws.py
uv run ruff check sidequest/genre/models/rules.py tests/genre/test_models/test_saving_throws.py
git add sidequest/genre/models/rules.py tests/genre/test_models/test_saving_throws.py
git commit -m "feat(rules): add SaveCategory enum and SavingThrowsTable (B/X B26)"
```

---

## Task 2: Re-export and add `ClassDef.saving_throws` field

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/__init__.py` (re-export new types)
- Modify: `sidequest-server/sidequest/genre/models/character.py` (line 91-111: `ClassDef`)
- Modify: `sidequest-server/tests/genre/test_models/test_character.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_models/test_character.py`:

```python
def test_class_def_accepts_saving_throws_table():
    from sidequest.genre.models.character import ClassDef
    from sidequest.genre.models.rules import SavingThrowsTable

    c = ClassDef(
        id="fighter",
        display_name="Fighter",
        rpg_role="tank",
        jungian_default="hero",
        prime_requisite="STR",
        minimum_score=9,
        kit_table="fighter_kit",
        saving_throws=SavingThrowsTable(
            death_ray_or_poison=12,
            magic_wands=13,
            paralysis_or_stone=14,
            dragon_breath=15,
            rods_staves_spells=16,
        ),
    )
    assert c.saving_throws is not None
    assert c.saving_throws.dragon_breath == 15


def test_class_def_saving_throws_defaults_none():
    from sidequest.genre.models.character import ClassDef

    c = ClassDef(
        id="fighter",
        display_name="Fighter",
        rpg_role="tank",
        jungian_default="hero",
        prime_requisite="STR",
        minimum_score=9,
        kit_table="fighter_kit",
    )
    assert c.saving_throws is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py::test_class_def_accepts_saving_throws_table -v`
Expected: FAIL with `ValidationError` (extra="forbid" rejects `saving_throws` field).

- [ ] **Step 3: Add the field to `ClassDef`**

Edit `sidequest-server/sidequest/genre/models/character.py` line 110-111. Replace:

```python
    magic_access: str | None = None
    magic_config: ClassMagicConfig | None = None
```

with:

```python
    magic_access: str | None = None
    magic_config: ClassMagicConfig | None = None
    saving_throws: SavingThrowsTable | None = None
```

Add the import at the top of the file (around line 12, near `OceanProfile`):

```python
from sidequest.genre.models.rules import SavingThrowsTable
```

If a circular-import warning surfaces (rules.py imports from character.py or vice versa), use a `TYPE_CHECKING` guard — but verify first; rules.py currently does NOT import from character.py, so a direct import is fine.

- [ ] **Step 4: Re-export from `models/__init__.py`**

Read `sidequest-server/sidequest/genre/models/__init__.py` to find the existing re-export block. Add `SaveCategory` and `SavingThrowsTable` to the imports (alphabetical or grouped with other rules.py exports per the file's existing convention).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py -v`
Expected: PASS — both new tests + existing tests.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/genre/models/character.py sidequest/genre/models/__init__.py tests/genre/test_models/test_character.py
uv run ruff check sidequest/genre/models/character.py sidequest/genre/models/__init__.py tests/genre/test_models/test_character.py
git add sidequest/genre/models/character.py sidequest/genre/models/__init__.py tests/genre/test_models/test_character.py
git commit -m "feat(character): add ClassDef.saving_throws field (B/X B26)"
```

---

## Task 3: Add `NpcArchetype.saves_as_class` field

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py` (line 15-35: `NpcArchetype`)
- Modify: `sidequest-server/tests/genre/test_models/test_character.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_models/test_character.py`:

```python
def test_npc_archetype_saves_as_class_default_fighter():
    from sidequest.genre.models.character import NpcArchetype

    a = NpcArchetype(name="Goblin", description="green and mean")
    assert a.saves_as_class == "Fighter"


def test_npc_archetype_saves_as_class_override():
    from sidequest.genre.models.character import NpcArchetype

    a = NpcArchetype(
        name="Necromancer",
        description="bones and willpower",
        saves_as_class="Mage",
    )
    assert a.saves_as_class == "Mage"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py::test_npc_archetype_saves_as_class_default_fighter -v`
Expected: FAIL with `AttributeError: 'NpcArchetype' object has no attribute 'saves_as_class'`.

- [ ] **Step 3: Add the field**

Edit `sidequest-server/sidequest/genre/models/character.py` line 35 — add `saves_as_class` after `mindless`:

```python
    ocean: OceanProfile | None = None
    mindless: bool = False
    saves_as_class: str = "Fighter"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py -v`
Expected: PASS — both new tests + existing tests.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/genre/models/character.py tests/genre/test_models/test_character.py
uv run ruff check sidequest/genre/models/character.py tests/genre/test_models/test_character.py
git add sidequest/genre/models/character.py tests/genre/test_models/test_character.py
git commit -m "feat(character): add NpcArchetype.saves_as_class (B/X B26 NPC saves)"
```

---

## Task 4: Extend `SpellSave` with `category` and add `Spell.requires_mind`

**Files:**
- Modify: `sidequest-server/sidequest/magic/spell_catalog.py` (lines 19-38: `SpellSave`; lines 58-76: `Spell`)
- Modify: `sidequest-server/tests/magic/test_spell_catalog.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/magic/test_spell_catalog.py`:

```python
def test_spell_save_category_defaults_rods_staves_spells():
    from sidequest.genre.models.rules import SaveCategory
    from sidequest.magic.spell_catalog import SpellSave

    s = SpellSave(stat="WIS", effect="negates")
    assert s.category is SaveCategory.rods_staves_spells


def test_spell_save_category_dragon_breath_requires_null_stat():
    import pytest
    from pydantic import ValidationError

    from sidequest.genre.models.rules import SaveCategory
    from sidequest.magic.spell_catalog import SpellSave

    with pytest.raises(ValidationError, match="dragon_breath"):
        SpellSave(stat="WIS", effect="halves", category=SaveCategory.dragon_breath)


def test_spell_save_category_dragon_breath_with_null_stat_ok():
    from sidequest.genre.models.rules import SaveCategory
    from sidequest.magic.spell_catalog import SpellSave

    s = SpellSave(stat=None, effect="halves", category=SaveCategory.dragon_breath)
    assert s.category is SaveCategory.dragon_breath


def test_spell_requires_mind_default_false():
    from sidequest.magic.spell_catalog import Spell, SpellComponents, SpellSave

    s = Spell(
        id="magic_missile",
        name="Magic Missile",
        level=1,
        tradition="arcane",
        range="near",
        target="single",
        duration="instant",
        save=SpellSave(stat=None, effect="none"),
        effect_template="auto-hit",
        components=SpellComponents(),
        backlash=None,
        narrator_register="A bolt.",
        domain="physical",
    )
    assert s.requires_mind is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/magic/test_spell_catalog.py -v`
Expected: FAIL — first new test fails on `assert s.category is ...` (attribute missing).

- [ ] **Step 3: Implement**

Edit `sidequest-server/sidequest/magic/spell_catalog.py`. Replace the `SpellSave` class (currently lines 19-38):

```python
class SpellSave(BaseModel):
    model_config = {"extra": "forbid"}
    stat: str | None
    # Allowed values: one of {"none", "negates", "halves"} OR a discriminated
    # "partial:<text>" form. The plain `str` is intentional only to admit the
    # partial: prefix; arbitrary strings (including typos like "negate") are
    # rejected by the validator below.
    effect: str
    # Which B26 column this save consults. Default matches the catch-all
    # magic column for arcane and divine spells; per-spell override exists
    # for the rare ray-type or stone-type variant.
    category: SaveCategory = SaveCategory.rods_staves_spells

    @field_validator("effect")
    @classmethod
    def _validate_effect(cls, v: str) -> str:
        if v in _SPELL_SAVE_EFFECT_FIXED:
            return v
        if v.startswith("partial:") and len(v) > len("partial:"):
            return v
        raise ValueError(
            f"SpellSave.effect={v!r} is not a known value; expected one of "
            f"{sorted(_SPELL_SAVE_EFFECT_FIXED)} or a 'partial:<text>' discriminated form"
        )

    @model_validator(mode="after")
    def _validate_dragon_breath_no_stat(self) -> SpellSave:
        if self.category is SaveCategory.dragon_breath and self.stat is not None:
            raise ValueError(
                f"SpellSave with category=dragon_breath must have stat=None "
                f"(B/X B7: WIS does not modify Dragon Breath saves), got stat={self.stat!r}"
            )
        return self
```

Add the import at the top of the file (around line 14):

```python
from pydantic import BaseModel, Field, field_validator, model_validator

from sidequest.genre.models.rules import SaveCategory
```

(`model_validator` may already be imported; verify before adding.)

Modify the `Spell` class (around line 58) to add `requires_mind`. Insert the field after `save`:

```python
class Spell(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    name: str
    level: int
    tradition: Literal["arcane", "divine"]
    range: Literal["touch", "close", "near", "far", "unlimited"]
    target: Literal["single", "area", "self", "object"]
    duration: str  # "instant" | "until_rest" | "turns:<N|XdY>" | "permanent"
    save: SpellSave
    requires_mind: bool = False  # NEW — mindless targets skip save AND skip effect
    effect_template: str
    components: SpellComponents
    backlash: str | None
    narrator_register: str
    hard_limits_check: list[str] = Field(default_factory=list)
    domain: str
    otel_attrs: list[str] = Field(default_factory=list)
    reverse: SpellReverse | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_spell_catalog.py -v`
Expected: PASS — all four new tests + existing tests.

- [ ] **Step 5: Verify the existing fixture still loads**

Run: `cd sidequest-server && uv run pytest tests/magic/test_spell_catalog.py tests/magic/test_loader.py -v`
Expected: PASS — `cc_arcane_l1.yaml` fixture loads without modification (it has no `category:` line, so the default kicks in).

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/magic/spell_catalog.py tests/magic/test_spell_catalog.py
uv run ruff check sidequest/magic/spell_catalog.py tests/magic/test_spell_catalog.py
git add sidequest/magic/spell_catalog.py tests/magic/test_spell_catalog.py
git commit -m "feat(magic): add SpellSave.category + Spell.requires_mind (B/X save schema)"
```

---

## Task 5: Add `fixed_opponent_roll` kwarg to `resolve_opposed_check`

**Files:**
- Modify: `sidequest-server/sidequest/game/opposed_check.py` (lines 202-285: `resolve_opposed_check`)
- Create: `sidequest-server/tests/game/test_opposed_check_fixed_roll.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_opposed_check_fixed_roll.py`:

```python
"""Tests for ``fixed_opponent_roll`` kwarg on resolve_opposed_check.

The save resolver pins the threat's d20 to the B26 table target via
this kwarg; existing combat callers omit the kwarg and the path is
identical to the prior behavior.
"""

import pytest

from sidequest.game.encounter import EncounterActor
from sidequest.game.opposed_check import resolve_opposed_check
from sidequest.protocol.dice import RollOutcome


class _FakeBeat:
    def __init__(self, stat_check: str = "STR") -> None:
        self.stat_check = stat_check


class _FakeCdef:
    def __init__(self, opponent_default_stats: dict[str, int]) -> None:
        self.opponent_default_stats = opponent_default_stats


def _player(stat: str = "STR", score: int = 12) -> EncounterActor:
    return EncounterActor(
        name="player",
        side="player",
        per_actor_state={"stats": {stat: score}},
    )


def _opp(stat: str = "STR", score: int = 10) -> EncounterActor:
    return EncounterActor(
        name="threat",
        side="opponent",
        per_actor_state={"stats": {stat: score}},
    )


def test_fixed_opponent_roll_pins_opponent_d20():
    cdef = _FakeCdef({"STR": 10})
    res = resolve_opposed_check(
        player_actor=_player(score=12),
        opponent_actor=_opp(score=10),
        player_beat=_FakeBeat("STR"),
        opponent_beat=_FakeBeat("STR"),
        cdef=cdef,
        player_roll=15,
        opponent_roll=99,  # would be invalid if used; pinned value wins
        fixed_opponent_roll=14,
    )
    # Opponent's effective roll is 14 (pinned), mod 0 (score 10).
    # Player: 15 + 1 (score 12) = 16. Shift = 16 - 14 = +2 → Success.
    assert res.opponent_roll == 14
    assert res.shift == 2
    assert res.tier is RollOutcome.Success


def test_fixed_opponent_roll_validates_range():
    cdef = _FakeCdef({"STR": 10})
    with pytest.raises(ValueError, match="fixed_opponent_roll"):
        resolve_opposed_check(
            player_actor=_player(),
            opponent_actor=_opp(),
            player_beat=_FakeBeat(),
            opponent_beat=_FakeBeat(),
            cdef=cdef,
            player_roll=10,
            opponent_roll=10,
            fixed_opponent_roll=21,
        )


def test_fixed_opponent_roll_default_none_unchanged_path():
    cdef = _FakeCdef({"STR": 10})
    res = resolve_opposed_check(
        player_actor=_player(score=12),
        opponent_actor=_opp(score=10),
        player_beat=_FakeBeat("STR"),
        opponent_beat=_FakeBeat("STR"),
        cdef=cdef,
        player_roll=15,
        opponent_roll=10,
        # fixed_opponent_roll omitted — opponent_roll used directly
    )
    assert res.opponent_roll == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_opposed_check_fixed_roll.py -v`
Expected: FAIL with `TypeError: resolve_opposed_check() got an unexpected keyword argument 'fixed_opponent_roll'`.

- [ ] **Step 3: Add the kwarg**

Edit `sidequest-server/sidequest/game/opposed_check.py`. In `resolve_opposed_check` (line 202), add the kwarg and the override logic. Update the function signature and add validation immediately after the existing `player_roll` / `opponent_roll` validators (around line 245):

```python
def resolve_opposed_check(
    *,
    player_actor: EncounterActor,
    opponent_actor: EncounterActor,
    player_beat: Any,  # BeatDef
    opponent_beat: Any,  # BeatDef
    cdef: Any,  # ConfrontationDef
    player_roll: int,
    opponent_roll: int,
    encounter: StructuredEncounter | None = None,
    edge_resolver: EdgeResolver | None = None,
    fixed_opponent_roll: int | None = None,
) -> OpposedRollResult:
    """... (existing docstring)

    ``fixed_opponent_roll``: when set, overrides ``opponent_roll`` with
    the given value as the opponent's d20 face. Used by the save
    resolver (``sidequest.game.saves``) to pin the threat's "roll" to
    the B/X B26 table target — the threat does not roll randomly; the
    table value IS its deterministic d20. Validated to ``1..20``.
    """
    if fixed_opponent_roll is not None:
        if not (1 <= fixed_opponent_roll <= 20):
            raise ValueError(
                f"fixed_opponent_roll {fixed_opponent_roll} not in 1..20"
            )
        opponent_roll = fixed_opponent_roll

    if not (1 <= player_roll <= 20):
        raise ValueError(...)
    # ... rest unchanged
```

The full diff: insert the validation block immediately after the function docstring, BEFORE the existing `if not (1 <= player_roll <= 20)` check, so that an invalid `fixed_opponent_roll` raises before the `opponent_roll` check (which otherwise would accept the original out-of-range `99` and reject only on `1..20` after the override). Override `opponent_roll` to the pinned value before the existing range check runs on it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_opposed_check_fixed_roll.py tests/game/test_opposed_check_distribution.py -v`
Expected: PASS — new tests pass, distribution tests unchanged.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/game/opposed_check.py tests/game/test_opposed_check_fixed_roll.py
uv run ruff check sidequest/game/opposed_check.py tests/game/test_opposed_check_fixed_roll.py
git add sidequest/game/opposed_check.py tests/game/test_opposed_check_fixed_roll.py
git commit -m "feat(opposed_check): add fixed_opponent_roll kwarg for synthetic-threat saves"
```

---

## Task 6: Build `resolve_save` and `apply_spell_effect` in `game/saves.py`

**Files:**
- Create: `sidequest-server/sidequest/game/saves.py`
- Create: `sidequest-server/tests/game/test_saves.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_saves.py`:

```python
"""Tests for resolve_save and apply_spell_effect (B/X B26 save resolver)."""

import random

import pytest

from sidequest.game.encounter import EncounterActor
from sidequest.game.saves import (
    SaveResult,
    apply_spell_effect,
    resolve_save,
)
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.rules import SaveCategory, SavingThrowsTable
from sidequest.protocol.dice import RollOutcome


def _fighter() -> ClassDef:
    return ClassDef(
        id="fighter",
        display_name="Fighter",
        rpg_role="tank",
        jungian_default="hero",
        prime_requisite="STR",
        minimum_score=9,
        kit_table="fighter_kit",
        saving_throws=SavingThrowsTable(
            death_ray_or_poison=12,
            magic_wands=13,
            paralysis_or_stone=14,
            dragon_breath=15,
            rods_staves_spells=16,
        ),
    )


def _mage() -> ClassDef:
    return ClassDef(
        id="mage",
        display_name="Mage",
        rpg_role="caster",
        jungian_default="magician",
        prime_requisite="INT",
        minimum_score=9,
        kit_table="mage_kit",
        saving_throws=SavingThrowsTable(
            death_ray_or_poison=13,
            magic_wands=14,
            paralysis_or_stone=13,
            dragon_breath=16,
            rods_staves_spells=15,
        ),
    )


def _classes() -> dict[str, ClassDef]:
    return {"Fighter": _fighter(), "Mage": _mage()}


def _actor(name: str = "carl", wis: int = 10) -> EncounterActor:
    return EncounterActor(
        name=name,
        side="player",
        per_actor_state={"stats": {"WIS": wis, "STR": 10, "DEX": 10}},
    )


class _DeterministicRng:
    """Returns the next value from a queue. random.Random API subset."""

    def __init__(self, values: list[int]) -> None:
        self._values = list(values)

    def randint(self, lo: int, hi: int) -> int:
        v = self._values.pop(0)
        assert lo <= v <= hi, f"queued {v} outside requested range [{lo},{hi}]"
        return v


def test_resolve_save_mage_vs_spells_pass_on_total_eq_target():
    # Mage vs Spells = 15. Defender rolls d20=14, WIS=12 (mod +1) → total 15.
    # Shift = 15 - 15 = 0 → Tie band (per opposed_check ±1 band).
    rng = _DeterministicRng([14])
    res = resolve_save(
        defender=_actor(wis=12),
        defender_class="Mage",
        pack_classes=_classes(),
        category=SaveCategory.rods_staves_spells,
        ability="WIS",
        threat_label="SLEEP",
        rng=rng,
    )
    assert res.target == 15
    assert res.roll == 14
    assert res.mod == 1
    assert res.total == 15
    assert res.shift == 0
    assert res.tier is RollOutcome.Tie


def test_resolve_save_mage_vs_spells_clear_success():
    # Mage rolls d20=20 → CritSuccess regardless of mod/target.
    rng = _DeterministicRng([20])
    res = resolve_save(
        defender=_actor(wis=10),
        defender_class="Mage",
        pack_classes=_classes(),
        category=SaveCategory.rods_staves_spells,
        ability="WIS",
        threat_label="SLEEP",
        rng=rng,
    )
    assert res.tier is RollOutcome.CritSuccess


def test_resolve_save_mage_vs_spells_nat1_critfail():
    rng = _DeterministicRng([1])
    res = resolve_save(
        defender=_actor(wis=18),  # +4, would normally beat 15 — nat1 still fails crit
        defender_class="Mage",
        pack_classes=_classes(),
        category=SaveCategory.rods_staves_spells,
        ability="WIS",
        threat_label="SLEEP",
        rng=rng,
    )
    assert res.tier is RollOutcome.CritFail


def test_resolve_save_target_differs_by_class():
    rng_fighter = _DeterministicRng([10])
    rng_mage = _DeterministicRng([10])
    f = resolve_save(
        defender=_actor(wis=10),
        defender_class="Fighter",
        pack_classes=_classes(),
        category=SaveCategory.rods_staves_spells,
        ability="WIS",
        threat_label="SLEEP",
        rng=rng_fighter,
    )
    m = resolve_save(
        defender=_actor(wis=10),
        defender_class="Mage",
        pack_classes=_classes(),
        category=SaveCategory.rods_staves_spells,
        ability="WIS",
        threat_label="SLEEP",
        rng=rng_mage,
    )
    assert f.target == 16
    assert m.target == 15
    assert f.shift == m.shift - 1  # fighter target is 1 higher → shift is 1 lower


def test_resolve_save_dragon_breath_ignores_ability():
    # Even with WIS=20 (+5), Dragon Breath ignores the ability mod.
    rng = _DeterministicRng([10])
    res = resolve_save(
        defender=_actor(wis=20),
        defender_class="Mage",
        pack_classes=_classes(),
        category=SaveCategory.dragon_breath,
        ability=None,  # B/X B7: no ability adjustment for Dragon Breath
        threat_label="DRAGON BREATH",
        rng=rng,
    )
    assert res.mod == 0
    assert res.total == 10
    assert res.target == 16
    assert res.shift == -6
    assert res.tier is RollOutcome.Fail


def test_resolve_save_loud_fails_when_class_not_in_pack():
    rng = _DeterministicRng([10])
    with pytest.raises(KeyError, match="Druid"):
        resolve_save(
            defender=_actor(),
            defender_class="Druid",
            pack_classes=_classes(),
            category=SaveCategory.rods_staves_spells,
            ability="WIS",
            threat_label="SLEEP",
            rng=rng,
        )


def test_resolve_save_loud_fails_when_class_has_no_table():
    rng = _DeterministicRng([10])
    classes = {
        "Bard": ClassDef(
            id="bard",
            display_name="Bard",
            rpg_role="support",
            jungian_default="trickster",
            prime_requisite="CHA",
            minimum_score=9,
            kit_table="bard_kit",
        ),  # no saving_throws
    }
    with pytest.raises(ValueError, match="saving_throws"):
        resolve_save(
            defender=_actor(),
            defender_class="Bard",
            pack_classes=classes,
            category=SaveCategory.rods_staves_spells,
            ability="WIS",
            threat_label="SLEEP",
            rng=rng,
        )


def test_apply_spell_effect_negates_on_critsuccess_save():
    # Spell with effect=negates: a CritSuccess save means no effect.
    res = SaveResult(
        defender_actor="carl",
        category=SaveCategory.rods_staves_spells,
        target=15,
        roll=20,
        mod=0,
        total=20,
        shift=5,
        tier=RollOutcome.CritSuccess,
        threat_label="SLEEP",
    )
    outcome = apply_spell_effect(spell_effect="negates", save_tier=res.tier)
    assert outcome.applies_full_effect is False
    assert outcome.applies_status is False


def test_apply_spell_effect_negates_on_fail_full_effect():
    outcome = apply_spell_effect(spell_effect="negates", save_tier=RollOutcome.Fail)
    assert outcome.applies_full_effect is True


def test_apply_spell_effect_halves_on_success_quarters():
    # Halves on Success = quarter; halves on Tie = half; halves on Fail = full.
    success = apply_spell_effect(spell_effect="halves", save_tier=RollOutcome.Success)
    tie = apply_spell_effect(spell_effect="halves", save_tier=RollOutcome.Tie)
    fail = apply_spell_effect(spell_effect="halves", save_tier=RollOutcome.Fail)
    assert success.damage_multiplier < tie.damage_multiplier < fail.damage_multiplier
    assert fail.damage_multiplier == 1.0


def test_apply_spell_effect_none_always_full():
    # `effect: none` means no save was rolled; always full effect.
    outcome = apply_spell_effect(spell_effect="none", save_tier=None)
    assert outcome.applies_full_effect is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_saves.py -v`
Expected: FAIL — `ModuleNotFoundError: sidequest.game.saves`.

- [ ] **Step 3: Implement `saves.py`**

Create `sidequest-server/sidequest/game/saves.py`:

```python
"""B/X-style saving throws — d20 + ability mod vs class+category target.

Resolver synthesizes the threat (POISON, SPELLS, DRAGON BREATH) as a
one-shot opponent in ``resolve_opposed_check``. The threat's d20 face
is pinned to the B/X B26 table target via ``fixed_opponent_roll``;
its modifier is 0. The defender's d20 + ability mod runs through the
existing shift-bands tier classifier — saves get critical bands for
free (CritSuccess save = bonus, CritFail = full effect + status).

Spec: ``docs/superpowers/specs/2026-05-09-cnc-bx-saving-throws-design.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from random import Random

from sidequest.game.encounter import EncounterActor
from sidequest.game.opposed_check import (
    OpposedRollResult,
    resolve_opposed_check,
)
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.rules import SaveCategory
from sidequest.protocol.dice import RollOutcome


@dataclass(frozen=True)
class SaveResult:
    """Outcome of one saving-throw resolution.

    Carries everything the GM panel needs to audit the save (math
    + threat label + tier). The synthetic-threat ``opponent_roll`` is
    deterministic — equal to the B26 table target — so the GM panel
    can render a chip like "SLEEP — 15 (vs your 11): Fail."
    """

    defender_actor: str
    category: SaveCategory
    target: int
    roll: int
    mod: int
    total: int
    shift: int
    tier: RollOutcome
    threat_label: str


def _ability_modifier(score: int) -> int:
    return (score - 10) // 2


def _defender_score(defender: EncounterActor, ability: str) -> int:
    pas = defender.per_actor_state or {}
    stats = pas.get("stats", {})
    if not isinstance(stats, dict):
        raise ValueError(
            f"defender {defender.name!r} per_actor_state.stats is not a dict; got {type(stats)}"
        )
    if ability in stats:
        return int(stats[ability])
    for k, v in stats.items():
        if isinstance(k, str) and k.lower() == ability.lower():
            return int(v)
    raise ValueError(
        f"defender {defender.name!r} has no stat {ability!r} in per_actor_state.stats "
        f"(present: {sorted(stats.keys())})"
    )


def resolve_save(
    *,
    defender: EncounterActor,
    defender_class: str,
    pack_classes: Mapping[str, ClassDef],
    category: SaveCategory,
    ability: str | None,
    threat_label: str,
    rng: Random,
) -> SaveResult:
    """Resolve a B/X save: d20 + ability_mod vs ``classes[defender_class].saving_throws[category]``.

    ``ability=None`` means no ability modifier (B/X B7: Dragon Breath).
    Hard-fail-loud if ``defender_class`` is not in ``pack_classes`` or
    the class has no ``saving_throws`` table set (CLAUDE.md
    no-silent-fallback). Hard-fail-loud if ``defender`` lacks
    ``ability`` in its stat block when ``ability`` is non-None.
    """
    if defender_class not in pack_classes:
        raise KeyError(
            f"defender_class {defender_class!r} not in pack classes "
            f"({sorted(pack_classes.keys())})"
        )
    cdef = pack_classes[defender_class]
    if cdef.saving_throws is None:
        raise ValueError(
            f"class {defender_class!r} has no saving_throws table; pack must declare one"
        )
    target = cdef.saving_throws.target_for(category)

    roll = rng.randint(1, 20)
    if ability is None:
        mod = 0
    else:
        score = _defender_score(defender, ability)
        mod = _ability_modifier(score)
    total = roll + mod
    shift = total - target

    # Reuse the existing tier classifier from opposed_check via a
    # synthetic-opponent path. Build a minimal opponent actor with no
    # stats — its modifier resolves to 0 because we pass an empty
    # opponent_default_stats and an opponent_beat with stat_check=""
    # (the `or 0` path in resolve_opponent_modifier is reached because
    # we don't actually want the opponent's mod). Wait — that path
    # raises. So we use a different approach: pin the opponent_roll
    # via fixed_opponent_roll, give the synthetic opponent the
    # defender's stat block (so the modifier-resolver doesn't fail-
    # loud), and the per-actor mod is computed but DEPENDS only on the
    # defender side via the formula. Simpler: bypass resolve_opposed_check
    # entirely and use the same tier classifier inline since the math
    # is the same shape.
    tier = _classify_save_tier(roll=roll, total=total, target=target)

    return SaveResult(
        defender_actor=defender.name,
        category=category,
        target=target,
        roll=roll,
        mod=mod,
        total=total,
        shift=shift,
        tier=tier,
        threat_label=threat_label,
    )


_DECISIVE_MARGIN = 10


def _classify_save_tier(*, roll: int, total: int, target: int) -> RollOutcome:
    """Per-side tier from one d20 face vs static target.

    Mirrors ``narration_apply._classify_legacy_tier`` semantics so a
    save resolves with the same crit rules combat uses:

    - nat20 → CritSuccess
    - nat1  → CritFail
    - total >= target + 10 → CritSuccess (decisive margin)
    - total > target → Success
    - total == target → Tie
    - total < target → Fail
    """
    if roll == 20:
        return RollOutcome.CritSuccess
    if roll == 1:
        return RollOutcome.CritFail
    if total >= target + _DECISIVE_MARGIN:
        return RollOutcome.CritSuccess
    if total > target:
        return RollOutcome.Success
    if total == target:
        return RollOutcome.Tie
    return RollOutcome.Fail


@dataclass(frozen=True)
class SpellEffectOutcome:
    """How a spell's mechanical effect lands after the save resolves.

    ``applies_full_effect``: caller applies the spell's full mechanical
    effect (damage, status). On ``False``, the save mitigated.
    ``applies_status``: caller applies any status flag (paralysis,
    sleep, charm). Independent of full_effect — a halved-damage spell
    may still skip a status on a successful save.
    ``damage_multiplier``: scalar applied to damage (0.0..1.0+). On
    CritFail the multiplier may exceed 1.0 (engine choice; v1 caps at 1.0).
    """

    applies_full_effect: bool
    applies_status: bool
    damage_multiplier: float


def apply_spell_effect(
    *,
    spell_effect: str,
    save_tier: RollOutcome | None,
) -> SpellEffectOutcome:
    """Map a (spell.save.effect, save tier) pair to mechanical outcome.

    ``save_tier=None`` means no save was rolled (spell has effect=none
    or save was skipped due to mindless gate). Caller is responsible
    for the gate decision; this function only encodes the after-roll
    payoff matrix.
    """
    if spell_effect == "none" or save_tier is None:
        return SpellEffectOutcome(
            applies_full_effect=True,
            applies_status=True,
            damage_multiplier=1.0,
        )

    if spell_effect == "negates":
        if save_tier in (RollOutcome.CritSuccess, RollOutcome.Success):
            return SpellEffectOutcome(
                applies_full_effect=False,
                applies_status=False,
                damage_multiplier=0.0,
            )
        if save_tier is RollOutcome.Tie:
            # Tie band: narrator-fiat half effect. Engine picks
            # ``applies_full_effect=False`` with a half multiplier so a
            # damage-bearing negates spell still does something on a tie.
            return SpellEffectOutcome(
                applies_full_effect=False,
                applies_status=False,
                damage_multiplier=0.5,
            )
        # Fail / CritFail
        return SpellEffectOutcome(
            applies_full_effect=True,
            applies_status=True,
            damage_multiplier=1.0,
        )

    if spell_effect == "halves":
        if save_tier is RollOutcome.CritSuccess:
            return SpellEffectOutcome(
                applies_full_effect=False,
                applies_status=False,
                damage_multiplier=0.0,
            )
        if save_tier is RollOutcome.Success:
            return SpellEffectOutcome(
                applies_full_effect=False,
                applies_status=False,
                damage_multiplier=0.25,
            )
        if save_tier is RollOutcome.Tie:
            return SpellEffectOutcome(
                applies_full_effect=False,
                applies_status=False,
                damage_multiplier=0.5,
            )
        # Fail / CritFail
        return SpellEffectOutcome(
            applies_full_effect=True,
            applies_status=True,
            damage_multiplier=1.0,
        )

    if spell_effect.startswith("partial:"):
        # v1: treat partial as halves; flavor authored in narration.
        return apply_spell_effect(spell_effect="halves", save_tier=save_tier)

    raise ValueError(f"unknown spell_effect {spell_effect!r}")
```

**Note on the simpler tier path:** the spec proposed a synthetic-opponent path through `resolve_opposed_check`. After implementing, the cleanest shape is to reuse only the **tier classifier** (mirrored as `_classify_save_tier`), not the full opposed_check call — the synthetic opponent would need a stat block to satisfy `resolve_opponent_modifier`, and synthesizing one is more code than mirroring the 7-line tier classifier. The `fixed_opponent_roll` kwarg from Task 5 still pays for itself: future callers (saves vs traps, environmental hazards) that want the synthetic-opponent shape get it for free if we change our minds. **Document the deviation** in the session file's Design Deviations section: "Spec §4.3 sketched calling `resolve_opposed_check` with a synthetic opponent; implementation mirrors only the tier classifier inline because synthesizing a stat-bearing opponent is more code than the 7-line classifier. The `fixed_opponent_roll` kwarg shipped anyway — useful for future trap/environment saves."

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_saves.py -v`
Expected: PASS — all 11 tests.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/game/saves.py tests/game/test_saves.py
uv run ruff check sidequest/game/saves.py tests/game/test_saves.py
git add sidequest/game/saves.py tests/game/test_saves.py
git commit -m "feat(game): resolve_save and apply_spell_effect (B/X B26 saves)"
```

---

## Task 7: Add `encounter.saving_throw_resolved` OTEL span

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/encounter.py` (append after existing encounter spans)
- Create: `sidequest-server/tests/telemetry/test_saving_throw_span.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_saving_throw_span.py`:

```python
"""Tests for encounter.saving_throw_resolved OTEL span."""

from sidequest.telemetry.spans._core import SPAN_ROUTES
from sidequest.telemetry.spans.encounter import (
    SPAN_ENCOUNTER_SAVING_THROW_RESOLVED,
    encounter_saving_throw_resolved_span,
)


def test_saving_throw_span_constant_declared():
    assert SPAN_ENCOUNTER_SAVING_THROW_RESOLVED == "encounter.saving_throw_resolved"


def test_saving_throw_span_route_registered():
    assert SPAN_ENCOUNTER_SAVING_THROW_RESOLVED in SPAN_ROUTES
    route = SPAN_ROUTES[SPAN_ENCOUNTER_SAVING_THROW_RESOLVED]
    assert route.event_type == "state_transition"
    assert route.component == "encounter"


def test_saving_throw_span_emits_with_required_attrs():
    # Context manager should be callable and not raise on the documented
    # attribute set. We don't assert against an OTEL collector here —
    # span fixture coverage lives in the dashboard regression tests.
    with encounter_saving_throw_resolved_span(
        defender_actor="carl",
        defender_class="Mage",
        category="rods_staves_spells",
        ability="WIS",
        threat_label="SLEEP",
        target=15,
        roll=11,
        mod=1,
        total=12,
        shift=-3,
        tier="Fail",
        spell_id="sleep",
        encounter_type="combat",
        mindless_gate=False,
    ):
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_saving_throw_span.py -v`
Expected: FAIL with `ImportError: cannot import name 'SPAN_ENCOUNTER_SAVING_THROW_RESOLVED'`.

- [ ] **Step 3: Add the span declaration**

Append to `sidequest-server/sidequest/telemetry/spans/encounter.py` (follow the pattern of `SPAN_ENCOUNTER_BEAT_APPLIED` already in the file — see the existing imports and `SpanRoute` registrations near the top):

```python
SPAN_ENCOUNTER_SAVING_THROW_RESOLVED = "encounter.saving_throw_resolved"
SPAN_ROUTES[SPAN_ENCOUNTER_SAVING_THROW_RESOLVED] = SpanRoute(
    event_type="state_transition",
    component="encounter",
    extract=lambda span: {
        "field": "encounter.saving_throw",
        "defender_actor": (span.attributes or {}).get("defender_actor", ""),
        "defender_class": (span.attributes or {}).get("defender_class", ""),
        "category": (span.attributes or {}).get("category", ""),
        "threat_label": (span.attributes or {}).get("threat_label", ""),
        "target": (span.attributes or {}).get("target", 0),
        "roll": (span.attributes or {}).get("roll", 0),
        "total": (span.attributes or {}).get("total", 0),
        "shift": (span.attributes or {}).get("shift", 0),
        "tier": (span.attributes or {}).get("tier", ""),
        "mindless_gate": (span.attributes or {}).get("mindless_gate", False),
        "spell_id": (span.attributes or {}).get("spell_id", ""),
    },
)


@contextmanager
def encounter_saving_throw_resolved_span(
    *,
    defender_actor: str,
    defender_class: str,
    category: str,
    ability: str | None,
    threat_label: str,
    target: int,
    roll: int,
    mod: int,
    total: int,
    shift: int,
    tier: str,
    spell_id: str,
    encounter_type: str,
    mindless_gate: bool,
) -> Iterator[trace.Span]:
    """Span emitted on every saving-throw resolution.

    The lie-detector for B/X save resolution: missing span → save
    subsystem isn't engaged → narrator is improvising the save outcome.

    ``mindless_gate=True`` indicates the save was SKIPPED because the
    target was mindless and the spell had ``requires_mind=True``;
    in that case ``roll/total/shift/tier`` are zero/empty and only
    the gate decision is logged.
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(SPAN_ENCOUNTER_SAVING_THROW_RESOLVED) as span:
        span.set_attribute("defender_actor", defender_actor)
        span.set_attribute("defender_class", defender_class)
        span.set_attribute("category", category)
        if ability is not None:
            span.set_attribute("ability", ability)
        span.set_attribute("threat_label", threat_label)
        span.set_attribute("target", target)
        span.set_attribute("roll", roll)
        span.set_attribute("mod", mod)
        span.set_attribute("total", total)
        span.set_attribute("shift", shift)
        span.set_attribute("tier", tier)
        span.set_attribute("spell_id", spell_id)
        span.set_attribute("encounter_type", encounter_type)
        span.set_attribute("mindless_gate", mindless_gate)
        yield span
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_saving_throw_span.py -v`
Expected: PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/telemetry/spans/encounter.py tests/telemetry/test_saving_throw_span.py
uv run ruff check sidequest/telemetry/spans/encounter.py tests/telemetry/test_saving_throw_span.py
git add sidequest/telemetry/spans/encounter.py tests/telemetry/test_saving_throw_span.py
git commit -m "feat(telemetry): add encounter.saving_throw_resolved span (lie-detector for B/X saves)"
```

---

## Task 8: Pack-load validation — every class declares `saving_throws` when pack has spells

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py` (find `_validate_class_filter_refs` from PR #220 — add a sibling validator)
- Modify: `sidequest-server/tests/genre/test_pack_load.py`

- [ ] **Step 1: Locate the existing validator**

Find `_validate_class_filter_refs` in `sidequest-server/sidequest/genre/loader.py`. The new validator will live next to it. Check what `pack` shape the existing validator receives.

Run: `cd sidequest-server && grep -n "_validate_class_filter_refs\|def _validate" sidequest/genre/loader.py`

- [ ] **Step 2: Write the failing test**

Append to `sidequest-server/tests/genre/test_pack_load.py`:

```python
def test_pack_load_rejects_class_without_saving_throws_when_pack_has_spells(tmp_path):
    """A class participating in a pack with spell catalogs must declare
    saving_throws — otherwise spells with save effects can't resolve."""
    from sidequest.genre.error import PackError
    from sidequest.genre.loader import load_genre_pack

    # Build a minimal pack with one class missing saving_throws and one spell catalog.
    # ... (use the existing test scaffolding pattern from test_pack_load.py;
    # see the cnc-bx morale tests at git show aaab798 -- tests/genre/test_pack_load.py
    # for the shape).
    pack_dir = tmp_path / "minimal_pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(...)  # minimal genre pack metadata
    (pack_dir / "classes.yaml").write_text(
        "- id: bard\n"
        "  display_name: Bard\n"
        "  rpg_role: support\n"
        "  jungian_default: trickster\n"
        "  prime_requisite: CHA\n"
        "  minimum_score: 9\n"
        "  kit_table: bard_kit\n"
        # NO saving_throws block
    )
    spells_dir = pack_dir / "spells"
    spells_dir.mkdir()
    (spells_dir / "test_l1.yaml").write_text(
        "version: '0.1.0'\n"
        "genre: minimal_pack\n"
        "tradition: arcane\n"
        "level: 1\n"
        "spells:\n"
        "  - id: test_spell\n"
        "    name: 'Test'\n"
        "    level: 1\n"
        "    tradition: arcane\n"
        "    range: near\n"
        "    target: single\n"
        "    duration: instant\n"
        "    save: { stat: WIS, effect: negates }\n"
        "    effect_template: 'test'\n"
        "    components: { verbal: false, somatic: false, material: null }\n"
        "    backlash: null\n"
        "    narrator_register: 'test'\n"
        "    domain: psychic\n"
    )

    with pytest.raises(PackError, match="saving_throws"):
        load_genre_pack(pack_dir)


def test_pack_load_passes_when_all_classes_have_saving_throws():
    """The C&C pack (after content authoring lands in Task 10) loads cleanly."""
    # This test is wired in Task 10 once the content is authored; for now
    # mark it as a placeholder skip OR write the inline minimal-pack
    # equivalent. Placeholder: write the inline version that DOES pass.
    pass
```

For the second test, replace `pass` with an inline minimal pack that DOES include `saving_throws` on every class, mirroring the failure case but with the table populated.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load.py::test_pack_load_rejects_class_without_saving_throws_when_pack_has_spells -v`
Expected: FAIL — pack loads without raising PackError.

- [ ] **Step 4: Implement the validator**

Add a function to `sidequest-server/sidequest/genre/loader.py` next to `_validate_class_filter_refs`:

```python
def _validate_saving_throws_refs(pack: GenrePack, *, has_spell_catalogs: bool) -> None:
    """When the pack ships any spell catalog, every class must declare
    saving_throws. Otherwise spells with save effects cannot resolve.

    No-op for packs without spells (heavy_metal, victoria, etc.) where
    saves aren't a wired subsystem yet.
    """
    if not has_spell_catalogs:
        return
    if not pack.classes:
        return
    missing = [c.display_name for c in pack.classes if c.saving_throws is None]
    if missing:
        raise PackError(
            f"pack has spell catalogs but classes missing saving_throws: {missing}. "
            f"Spells with save effects cannot resolve without a B/X B26 table per class."
        )
```

Then call `_validate_saving_throws_refs(pack, has_spell_catalogs=bool(pack.spell_catalogs))` from the same call site that calls `_validate_class_filter_refs` (locate via grep). The exact attribute name for spell catalogs on `GenrePack` should be verified — it might be `spell_catalogs`, `arcane_spells`, or `magic.catalogs` depending on how the loader registers them. Check via `grep -rn "spell_catalog\|SpellCatalog" sidequest/genre/`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v`
Expected: PASS — both new tests + existing tests.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/genre/loader.py tests/genre/test_pack_load.py
uv run ruff check sidequest/genre/loader.py tests/genre/test_pack_load.py
git add sidequest/genre/loader.py tests/genre/test_pack_load.py
git commit -m "feat(loader): require saving_throws on every class when pack has spell catalogs"
```

---

## Task 9: Wire save resolution into `narration_apply` after `_apply_magic_working`

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (the `_apply_magic_working` caller around line 388)
- Create: `sidequest-server/tests/server/test_narration_apply_save_integration.py`

- [ ] **Step 1: Locate the call site**

The seam is in `narration_apply.py` where `_apply_magic_working` is called. Find it:

Run: `cd sidequest-server && grep -n "_apply_magic_working\|magic_working" sidequest/server/narration_apply.py | head -20`

The save resolution wires in **after** `_apply_magic_working` returns — once the magic-state mutations land (slot consumed, ledger updated), iterate over the working's targets and resolve a save per target if the spell has a save effect.

- [ ] **Step 2: Write the failing integration test**

Create `sidequest-server/tests/server/test_narration_apply_save_integration.py`:

```python
"""Integration: narration_apply runs save resolution after learned_v1 cast.

These tests don't exercise the full WebSocket dispatch — they wire a
snapshot with magic_state seeded, drive a synthetic narrator JSON
sidecar carrying a magic_working patch_field, and assert that the
save resolver fires (or correctly skips) per the spell's save shape.
"""

import pytest

# Use the existing narration_apply test scaffolding. The shape mirrors
# tests/server/test_dispatch_pending_magic_frames.py — that file shows
# how to build a snapshot with magic_state and drive a magic_working
# through the apply path.


def test_save_fires_for_spell_with_negates_effect(monkeypatch):
    """When the narrator emits a magic_working for `sleep` against a
    Fighter NPC, narration_apply runs resolve_save and applies the
    spell effect according to the save tier."""
    pytest.skip("seed snapshot scaffolding pending; covered by e2e test in Task 13")


def test_save_skipped_for_mindless_target_with_requires_mind_spell(monkeypatch):
    """When `sleep` (requires_mind=True) targets a mindless skeleton,
    the save is SKIPPED and the spell effect is NOT applied; the OTEL
    span fires with mindless_gate=True."""
    pytest.skip("seed snapshot scaffolding pending; covered by e2e test in Task 13")


def test_save_skipped_for_spell_with_effect_none(monkeypatch):
    """`magic_missile` has effect=none — narration_apply applies full
    effect and emits NO save span."""
    pytest.skip("seed snapshot scaffolding pending; covered by e2e test in Task 13")
```

The full snapshot scaffolding for this kind of test is non-trivial (magic_state seeding + actor registration + working construction). For Task 9 we **defer the full integration tests to Task 13** (the end-to-end test) and ship Task 9 with a unit-level test of the new helper function we extract. Specifically:

Add a focused unit test of the new helper:

```python
def test_resolve_saves_for_working_calls_save_per_target(monkeypatch):
    """The new helper iterates working.targets and calls resolve_save
    for each one, returning a list of (target, SaveResult|None) pairs."""
    from sidequest.server.narration_apply import _resolve_saves_for_working
    # ... build minimal inputs (working with 2 targets, fake catalog,
    # fake pack_classes), assert resolve_save is called twice via
    # monkeypatch on sidequest.server.narration_apply.resolve_save.
    pytest.skip("scaffolding lands with implementation; see Task 9 step 4")
```

- [ ] **Step 3: Run test to verify the file is recognized**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_apply_save_integration.py -v --collect-only`
Expected: tests collected (skipped placeholders are fine for now).

- [ ] **Step 4: Implement the integration**

Edit `sidequest-server/sidequest/server/narration_apply.py`. After the call to `_apply_magic_working` (around line 388 in the function that handles a magic_working patch_field), add the save-resolution loop. Two options:

**Option A (minimal):** Inline the save loop right after `_apply_magic_working` returns, gated on `working.spell_id is not None` (the learned_v1 marker).

**Option B (cleaner):** Extract a `_resolve_saves_for_working(working, snapshot, pack, rng)` helper. **Choose Option B.**

Add the helper near the existing `_apply_magic_working` function:

```python
@dataclass(frozen=True)
class _ResolvedSaveForTarget:
    target_actor: str
    save: SaveResult | None  # None when skipped (mindless gate or effect=none)
    skipped_reason: str | None  # "mindless" | "no_save_required" | None
    spell_effect_outcome: SpellEffectOutcome


def _resolve_saves_for_working(
    *,
    working: MagicWorking,
    snapshot: Any,  # GameSnapshot
    pack: GenrePack,
    rng: Random,
) -> list[_ResolvedSaveForTarget]:
    """For a learned_v1 magic_working, iterate working.targets and run
    save resolution per target.

    Returns one ``_ResolvedSaveForTarget`` per target. Spells with
    ``effect: none`` skip the roll and return ``save=None,
    skipped_reason='no_save_required'``. ``requires_mind`` spells
    against mindless targets skip the roll and return
    ``save=None, skipped_reason='mindless'``. All cases emit a
    ``encounter.saving_throw_resolved`` OTEL span (the mindless and
    no-save cases set ``mindless_gate=True`` and ``mindless_gate=False``
    respectively, with null roll/tier).
    """
    if working.spell_id is None:
        return []  # not a learned_v1 working — innate or item magic
    catalog = pack.spell_catalogs_by_tradition_level.get(  # adjust attr name per loader
        (working.spell_id_tradition, working.slot_level), None
    )
    if catalog is None:
        raise ValueError(
            f"learned_v1 working refers to spell {working.spell_id!r} but "
            f"pack has no catalog for that tradition/level"
        )
    spell = catalog.get(working.spell_id)
    pack_classes = {c.display_name: c for c in pack.classes}

    results: list[_ResolvedSaveForTarget] = []
    for target_name in working.targets or []:
        target_actor = _lookup_target_actor(snapshot, target_name)
        target_class = _save_class_for_actor(target_actor, pack)

        # Mindless gate
        if spell.requires_mind:
            archetype = _archetype_for_actor(target_actor, pack)
            if archetype is not None and archetype.mindless:
                _emit_save_skipped_span(
                    target_actor=target_name,
                    target_class=target_class,
                    threat_label=spell.name.upper(),
                    spell_id=spell.id,
                    reason="mindless",
                )
                outcome = apply_spell_effect(spell_effect="none", save_tier=None)
                # Override: mindless target receives NO effect at all (B/X canon)
                outcome_no_effect = SpellEffectOutcome(
                    applies_full_effect=False,
                    applies_status=False,
                    damage_multiplier=0.0,
                )
                results.append(_ResolvedSaveForTarget(
                    target_actor=target_name,
                    save=None,
                    skipped_reason="mindless",
                    spell_effect_outcome=outcome_no_effect,
                ))
                continue

        # No-save spell (effect=none)
        if spell.save.effect == "none":
            outcome = apply_spell_effect(spell_effect="none", save_tier=None)
            results.append(_ResolvedSaveForTarget(
                target_actor=target_name,
                save=None,
                skipped_reason="no_save_required",
                spell_effect_outcome=outcome,
            ))
            continue

        # Regular save path
        save = resolve_save(
            defender=target_actor,
            defender_class=target_class,
            pack_classes=pack_classes,
            category=spell.save.category,
            ability=spell.save.stat,
            threat_label=spell.name.upper(),
            rng=rng,
        )
        with encounter_saving_throw_resolved_span(
            defender_actor=save.defender_actor,
            defender_class=target_class,
            category=save.category.value,
            ability=spell.save.stat,
            threat_label=save.threat_label,
            target=save.target,
            roll=save.roll,
            mod=save.mod,
            total=save.total,
            shift=save.shift,
            tier=save.tier.value,
            spell_id=spell.id,
            encounter_type=getattr(snapshot.encounter, "encounter_type", "")
            if snapshot.encounter else "",
            mindless_gate=False,
        ):
            pass
        outcome = apply_spell_effect(spell_effect=spell.save.effect, save_tier=save.tier)
        results.append(_ResolvedSaveForTarget(
            target_actor=target_name,
            save=save,
            skipped_reason=None,
            spell_effect_outcome=outcome,
        ))

    return results
```

The helpers `_lookup_target_actor`, `_save_class_for_actor`, `_archetype_for_actor`, and `_emit_save_skipped_span` are stubs that need real implementations. The shapes:

- `_lookup_target_actor(snapshot, name)`: returns `EncounterActor` from `snapshot.encounter.actors` matching by name. Hard-fail-loud on miss.
- `_save_class_for_actor(actor, pack)`: returns the `display_name` string. For PCs: `actor.character.char_class`. For NPCs: `archetype.saves_as_class` (default "Fighter"). Hard-fail-loud if neither path resolves.
- `_archetype_for_actor(actor, pack)`: returns `NpcArchetype | None`. PCs return None.
- `_emit_save_skipped_span(...)`: thin wrapper around `encounter_saving_throw_resolved_span` with `mindless_gate=True`, zeros for roll/total/shift, empty string for tier.

**The exact attribute names depend on the snapshot/pack shape — verify via grep before implementation.** Run:

```bash
cd sidequest-server && grep -n "spell_catalogs\|spell_catalog\|catalogs_by\|magic_catalogs" sidequest/genre/models/pack.py sidequest/genre/loader.py
```

Adjust the helper to match the actual loader attribute names. **No silent fallback** — if an attribute name doesn't match, fail loud.

Now wire `_resolve_saves_for_working` into the existing `_apply_magic_working` caller. After the existing `apply_result = snapshot.magic_state.apply_working(working)` line and before the OTEL `magic.working_applied` emission:

```python
# Run save resolution for every target of the working (learned_v1 only;
# innate_v1 and item_legacy_v1 workings have working.spell_id=None and
# this returns []). Then apply the spell effect to each target according
# to the save outcome.
session_rng = _get_session_rng(snapshot)  # use existing rng helper
save_outcomes = _resolve_saves_for_working(
    working=working,
    snapshot=snapshot,
    pack=pack,
    rng=session_rng,
)
for outcome in save_outcomes:
    _apply_spell_outcome_to_target(
        snapshot=snapshot,
        target_name=outcome.target_actor,
        spell=spell,  # same spell looked up in the helper
        outcome=outcome,
    )
```

`_apply_spell_outcome_to_target` is the bridge from `SpellEffectOutcome` to actual game-state mutation (damage to momentum, status flag set, etc.). For v1, it can be a thin function that:

- On `applies_full_effect=True`: applies the spell's full mechanical effect via the existing damage / status pipeline (whatever path `apply_working` already used for damage-to-momentum).
- On `applies_full_effect=False, damage_multiplier > 0`: applies scaled damage only.
- On all-zero outcome: no-op (target unaffected).

The simplest first implementation defers status effects entirely (only damage) and leaves status-application as a follow-up story. Mark this as a deviation.

- [ ] **Step 5: Run tests to verify**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_apply_save_integration.py tests/magic/ -v`
Expected: PASS — placeholder tests skip; existing magic tests still pass.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server
uv run ruff format sidequest/server/narration_apply.py tests/server/test_narration_apply_save_integration.py
uv run ruff check sidequest/server/narration_apply.py tests/server/test_narration_apply_save_integration.py
git add sidequest/server/narration_apply.py tests/server/test_narration_apply_save_integration.py
git commit -m "feat(narration_apply): wire B/X saving throws after learned_v1 working applies"
```

---

## Task 10: Content — `caverns_and_claudes/classes.yaml` saving_throws blocks

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

- [ ] **Step 1: Verify server merge prerequisite**

The server changes from Tasks 1-9 must be on `develop` before this content task can ship without breaking the pack. Verify:

Run: `cd sidequest-server && git log --oneline origin/develop | head -5`

Tasks 1-9 commits should be visible. If not, this content task waits.

- [ ] **Step 2: Add `saving_throws` to each class**

Read `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` to see the existing class entries' shape. For each of fighter / mage / cleric / thief, append a `saving_throws` block, verbatim from B/X B26:

```yaml
- id: fighter
  display_name: Fighter
  # ... existing fields ...
  saving_throws:
    death_ray_or_poison: 12
    magic_wands: 13
    paralysis_or_stone: 14
    dragon_breath: 15
    rods_staves_spells: 16

- id: mage
  display_name: Mage
  # ... existing fields ...
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15

- id: cleric
  display_name: Cleric
  # ... existing fields ...
  saving_throws:
    death_ray_or_poison: 11
    magic_wands: 12
    paralysis_or_stone: 14
    dragon_breath: 16
    rods_staves_spells: 15

- id: thief
  display_name: Thief
  # ... existing fields ...
  saving_throws:
    death_ray_or_poison: 13
    magic_wands: 14
    paralysis_or_stone: 13
    dragon_breath: 16
    rods_staves_spells: 15
```

- [ ] **Step 3: Run pack-load tests against the modified content**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k "caverns_and_claudes or cc_"`
Expected: PASS — pack loads with `saving_throws` blocks; the validator added in Task 8 confirms each class has a table.

- [ ] **Step 4: Commit (in content repo)**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/classes.yaml
git commit -m "feat(cc): add B/X B26 saving throws to all four classes"
```

Note: `sidequest-content` PRs target `develop` per `.pennyfarthing/repos.yaml`. Do not push to `main`.

---

## Task 11: Content — spell catalogs gain `category` field

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/spells/cc_arcane_l1.yaml`
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/spells/cc_divine_l1.yaml`

- [ ] **Step 1: Audit existing catalog**

Read both spell catalog files. For every spell with `save.effect != none`, the new `category:` field must be added to the save block. Default `rods_staves_spells` matches B/X for every learned_v1 spell that has any save in the L1 set.

- [ ] **Step 2: Append `category` to each save block**

For each spell with `save.effect: negates` or `save.effect: halves` or any partial form, change the YAML from:

```yaml
save: { stat: WIS, effect: negates }
```

to:

```yaml
save: { stat: WIS, effect: negates, category: rods_staves_spells }
```

Apply to: every spell in `cc_arcane_l1.yaml` and `cc_divine_l1.yaml` whose save effect is not `none`. Spells with `save: { stat: null, effect: none }` need NO change (no save fires; category is irrelevant but the default applies anyway).

For mind-affecting spells (`sleep`, `charm_person`, `hold_person`, `phantasmal_force`, `web` if it forces save vs sleep-paralysis effect), also add `requires_mind: true` at the spell level (sibling to `save:`):

```yaml
- id: sleep
  name: "Sleep"
  level: 1
  # ... existing fields ...
  save: { stat: WIS, effect: negates, category: rods_staves_spells }
  requires_mind: true
  # ... rest unchanged ...
```

Decide per spell using B/X canon (see B/X B15-18 for the spell list and the "affects living creatures only" wording — that's the mindless gate). The conservative pass:
- `sleep`: requires_mind: true
- `charm_person`: requires_mind: true
- `hold_person`: requires_mind: true (B/X says "human, demi-human or human-like")
- `phantasmal_force`: requires_mind: true (illusion — needs a mind to see it)
- `web`: requires_mind: false (physical strands, no mind needed)
- All damage-only or area-effect non-mind spells: requires_mind: false

- [ ] **Step 3: Run pack-load tests**

Run: `cd sidequest-server && uv run pytest tests/magic/test_loader.py tests/genre/test_pack_load.py -v -k "caverns_and_claudes or cc_"`
Expected: PASS.

- [ ] **Step 4: Commit (in content repo)**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/spells/cc_arcane_l1.yaml genre_packs/caverns_and_claudes/spells/cc_divine_l1.yaml
git commit -m "feat(cc-spells): add save category and requires_mind tags (B/X B26)"
```

---

## Task 12: Content — `caverns_sunden` archetypes get `saves_as_class`

**Files:**
- Modify: archetype YAML files under `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/`

- [ ] **Step 1: Locate archetype files**

Run: `cd sidequest-content && find genre_packs/caverns_and_claudes/worlds/caverns_sunden -name "*.yaml" | xargs grep -l "archetype\|NpcArchetype\|name:" | head -20`

Find the archetype-bearing files (NPC manifests, encounter rosters, faction sheets — depends on caverns_sunden's structure).

- [ ] **Step 2: Tag the qualifying archetypes**

For archetypes that should NOT save as Fighter, add `saves_as_class:` field. The conservative pass:

- **Spellcasters / scholars / occultists** → `saves_as_class: Mage`
- **Priests / inquisitors / cult leaders / undead-shepherds** → `saves_as_class: Cleric`
- **Burglars / spies / scouts / assassins** → `saves_as_class: Thief`
- **Everyone else (warriors, brigands, beasts, dragons, beasts of burden):** leave default (Fighter implicit).

Skip archetypes with `mindless: true` (skeletons, golems, oozes — already tagged by PR #220). Their `saves_as_class` is technically "Fighter" by default but only matters for non-mind-affecting saves like Dragon Breath; the default is fine.

Example diff:
```yaml
- name: "Necromancer of the Black Spire"
  description: "Bone-conjurer, willing to trade souls for power."
  saves_as_class: Mage
  # ... rest unchanged ...
```

- [ ] **Step 3: Run pack-load tests**

Run: `cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k "caverns_sunden"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/caverns_sunden/
git commit -m "feat(caverns-sunden): tag spellcasters/priests/rogues with saves_as_class (B/X)"
```

---

## Task 13: End-to-end integration test

**Files:**
- Create: `sidequest-server/tests/integration/test_save_resolution_e2e.py`

- [ ] **Step 1: Build the full integration test**

Create `sidequest-server/tests/integration/test_save_resolution_e2e.py`:

```python
"""End-to-end: a Mage casts sleep on mixed targets — saves resolve, mindless skip.

This is the wiring test that proves all of Tasks 1-12 are connected.
Without this test passing, the saves subsystem isn't actually engaged
in production code paths (CLAUDE.md "Every Test Suite Needs a Wiring Test").
"""

import pytest

# Use the existing C&C fixtures and snapshot scaffolding; pattern from
# tests/integration/test_cc_chargen_e2e.py.


def test_mage_sleep_on_fighter_npc_runs_save():
    """Mage casts sleep on a Fighter NPC. Save fires. OTEL span emits
    with category=rods_staves_spells. Effect application matches save tier."""
    pytest.skip(
        "scaffolding for full e2e test pending — see Task 13 design notes; "
        "for now the unit-level coverage in tests/game/test_saves.py + "
        "tests/server/test_narration_apply_save_integration.py is the gate"
    )


def test_mage_sleep_on_mindless_skeleton_skips_save_and_effect():
    """Mage casts sleep on a skeleton (mindless: true). Save SKIPPED
    (no roll), OTEL span emits with mindless_gate=True, spell has NO
    mechanical effect on the skeleton."""
    pytest.skip("scaffolding pending; see Task 13 design notes")


def test_mage_magic_missile_skips_save_path_entirely():
    """Mage casts magic_missile (effect=none). NO save span emits.
    Full effect applies."""
    pytest.skip("scaffolding pending; see Task 13 design notes")


def test_cleric_charm_person_on_thief_npc_uses_thief_save_target():
    """Cleric casts charm_person on a Thief NPC. Save target is Thief's
    rods_staves_spells = 15 (not Fighter's 16); the saves_as_class
    override on the archetype is honored."""
    pytest.skip("scaffolding pending; see Task 13 design notes")
```

The full integration test scaffolding requires a live snapshot with magic_state seeded, the encounter populated with PC + NPC actors, and a synthetic narrator JSON sidecar fed through `narration_apply`. The pattern exists in `test_cc_chargen_e2e.py` and `test_galley_autofires_tea_brew.py` — adapt those.

**This test is the playtest exit gate**, not a unit test. The skipped placeholders document intent; flesh them out using the e2e scaffolding patterns from existing tests when you reach this task. If the playtest in Task 14 surfaces issues, the e2e test fixtures will prove they regressed once fixed.

- [ ] **Step 2: Run the full check gate**

Run: `cd .. && just check-all`

Expected: server-check PASS, content lint PASS, daemon lint PASS, client tests PASS.

If any pre-existing failure surfaces unrelated to saves work, document and proceed (the saves changes shouldn't have introduced new failures).

- [ ] **Step 3: Commit**

```bash
cd sidequest-server
uv run ruff format tests/integration/test_save_resolution_e2e.py
git add tests/integration/test_save_resolution_e2e.py
git commit -m "test(saves): e2e integration scaffold for B/X save resolution"
```

---

## Task 14: Playtest exit verification

**Files:** none (manual verification — no code changes)

- [ ] **Step 1: Boot the stack**

Run: `cd .. && just up`

Watch for boot errors. Expect server on :8765, client on :5173.

- [ ] **Step 2: Open the GM dashboard**

Run: `cd .. && just otel`

Browser opens the GM dashboard at the dashboard endpoint.

- [ ] **Step 3: Run a scripted playtest in caverns_sunden**

In a separate terminal:
```bash
cd ..
just playtest --world caverns_sunden --class mage
```

Drive the playtest to a combat encounter that puts a Mage in spell-casting range of:
1. A goblin patrol (Fighter saves, fully alive, susceptible to sleep)
2. A mixed encounter with skeletons + goblins (mindless mixed with sentient)

- [ ] **Step 4: Verify exit criterion 1 — sleep on goblin patrol shows save chip**

Cast `sleep` on the goblin patrol. The dice overlay should show:
- Player's d20 settled
- For each goblin target: a chip labeled "SLEEP — 16" (Fighter target for `rods_staves_spells`) with the goblin's d20 result and tier.

Expected: some goblins save, others fail. The narrator should respect the dice — sleeping goblins go down, saving goblins stay up.

- [ ] **Step 5: Verify exit criterion 2 — mindless skeleton skipped**

Cast `sleep` on a mixed group of skeletons + goblins. Check the GM dashboard:
- Each goblin emits one `encounter.saving_throw_resolved` span with `mindless_gate=false`, valid roll/tier.
- Each skeleton emits one `encounter.saving_throw_resolved` span with `mindless_gate=true`, no roll/tier.
- Skeletons take NO effect from the spell (still standing, still hostile).

If the narrator prose claims "the skeletons resist your sleep" or "the skeletons fall," that's a narrator-prompt drift bug — file a follow-up story to add a prompt-zone invariant. The OTEL span is the lie-detector and shows the real behavior.

- [ ] **Step 6: Verify exit criterion 3 — Cleric charm_person on Thief NPC uses Thief target**

Switch to a Cleric character and cast `charm_person` on a Thief-archetype NPC (e.g., a "Cutpurse"). Check the GM dashboard:
- The save span shows `defender_class: Thief`, `target: 15` (Thief's `rods_staves_spells`).

If `target` shows 16 instead of 15, the `saves_as_class` override on the Cutpurse archetype isn't being read — debug `_save_class_for_actor` in narration_apply.

- [ ] **Step 7: Verify exit criterion 4 — magic_missile shows NO save span**

Cast `magic_missile` on any target. Check the GM dashboard: NO `encounter.saving_throw_resolved` span emitted. Full effect applies.

- [ ] **Step 8: Record findings**

Append session notes to the active story session file. Confirm the four exit criteria, or list deviations and file follow-up stories.

If all four criteria pass, the saves subsystem is wired and ready for normal playtest. Commit any session-note additions:

```bash
cd ..
git add sprint/<session-file>.md
git commit -m "test(saves): playtest exit verification for B/X saves"
```

---

## Self-review notes (for the implementing engineer)

1. **Spec coverage:** Tasks 1-3 cover §2.1-§2.5 schema; Task 4 covers §2.4 (SpellSave) plus `requires_mind` from §4.4; Task 5 covers §4.5; Task 6 covers §4.3 (resolver) and §4.6 (apply_spell_effect); Task 7 covers §4.7 (OTEL); Task 8 covers §4.2 (pack-load validation); Task 9 covers §4.6 (narration_apply integration); Tasks 10-12 cover §3 (content); Tasks 13-14 cover §5.4-§5.6 (testing + playtest exit). UI relabeling (§4.8) is documented as zero-surface — the dice overlay receives `threat_label` via the existing dice-result message; no client work needed if the message already carries an opponent label string.

2. **Deviation flag:** Task 6 deviates from spec §4.3 by mirroring the tier classifier inline rather than calling `resolve_opposed_check` with a synthetic opponent. Reason: synthesizing a stat-bearing opponent adds more code than the 7-line classifier. The `fixed_opponent_roll` kwarg from Task 5 still pays for itself for future trap/environment saves. **Log this deviation in the session file when implementing Task 6.**

3. **Snapshot/pack attribute names:** Task 9's helper signatures reference `pack.spell_catalogs_by_tradition_level` and `working.spell_id_tradition` — these are likely-but-unverified attribute names. Before implementing, run the grep commands listed in Task 9 step 4 and adjust to the actual loader shape. **No silent fallback** — if an attribute doesn't exist, fail loud and refactor the helper signature, do not invent a fallback.

4. **Test scaffolding deferral:** Task 9's integration tests and Task 13's e2e tests are placeholders. The unit-level coverage in `tests/game/test_saves.py` + the OTEL span test gives strong gates on the resolver itself; the full snapshot-driven integration is best filled in once the implementing engineer has the pattern from existing tests in front of them. If the full e2e tests are blockers for merge per project policy, expand them before Task 14 playtest.

5. **Sequencing with cnc-bx morale (in flight in another session):** This plan does NOT touch any of the files the cnc-bx morale story is editing. The shared dependency is `NpcArchetype.mindless` (already merged via PR #220). Both stories can land in either order.
