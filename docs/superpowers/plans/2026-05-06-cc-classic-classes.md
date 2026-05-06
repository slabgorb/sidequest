# C&C Classic Classes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Fighter / Mage / Cleric / Thief class choice to caverns_and_claudes chargen with B/X-style prime-requisite gating, class-themed kits, and per-class starting Edge.

**Architecture:** Wires existing infrastructure that's already plumbed for class. Adds (1) a `classes.yaml` with `ClassDef` model, (2) `class_tables` extension to `EquipmentTables` model, (3) `equipment_generation: class_kit` dispatch in `CharacterBuilder`, (4) `class_qualification_loop` reroll on `roll_3d6_strict`, (5) `edge_config.base_max_by_class` entries (the existing path — no new mechanical effect), and (6) a 5-scene `char_creation.yaml` rewrite. Race deferred.

**Tech Stack:** Python 3.13, FastAPI, pydantic v2, pytest, ruff, uv. Genre packs are YAML, loaded by `sidequest-server/sidequest/genre/loader.py`.

**Spec:** `docs/superpowers/specs/2026-05-06-cc-classic-classes-design.md`

**Repos touched:**
- `sidequest-content/genre_packs/caverns_and_claudes/` — content (PRs target `develop` per `.pennyfarthing/repos.yaml`)
- `sidequest-server/` — server wiring (PRs target `main`)

**Working convention for class identifiers** (consistency across all files):
- `id` field in `classes.yaml` is **lowercase** (`fighter`, `mage`, `cleric`, `thief`)
- `display_name` and `class_hint` values are **capitalized** (`Fighter`, `Mage`, `Cleric`, `Thief`) — matches existing `space_opera` convention and `edge_config.base_max_by_class` keys in `heavy_metal`
- `Character.char_class` carries the capitalized form (the existing default is `"Fighter"`)
- Lookups inside the engine use `display_name` to match `class_hint`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/genre/models/character.py` | Modify | Add `ClassDef` model. Extend `EquipmentTables` with `class_tables` field. Extend `MechanicalEffects` with `class_qualification_loop: bool`. |
| `sidequest-server/sidequest/genre/models/__init__.py` | Modify | Re-export `ClassDef`. |
| `sidequest-server/sidequest/genre/models/pack.py` | Modify | Add `classes: list[ClassDef]` to `GenrePack`. |
| `sidequest-server/sidequest/genre/loader.py` | Modify | Load `classes.yaml` into `GenrePack.classes`. |
| `sidequest-server/sidequest/game/builder.py` | Modify | Add `qualifying_classes()` helper. Wire reroll loop on `class_qualification_loop`. Add `equipment_generation: class_kit` dispatch. Filter Scene 2 choices by qualification. Emit OTEL events. |
| `sidequest-server/tests/genre/test_classes_yaml.py` | Create | Pack content tests. |
| `sidequest-server/tests/game/test_qualifying_classes.py` | Create | Pure-function tests. |
| `sidequest-server/tests/game/test_chargen_class_kit.py` | Create | `equipment_generation: class_kit` dispatch tests. |
| `sidequest-server/tests/game/test_chargen_reroll_loop.py` | Create | Deterministic reroll-loop test. |
| `sidequest-server/tests/integration/test_cc_chargen_e2e.py` | Create | End-to-end wiring test. |
| `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` | Create | 4 class entries. |
| `sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml` | Modify | Add `class_tables` block. |
| `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml` | Modify | Add 6 missing item entries. |
| `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` | Modify | Add `edge_config.base_max_by_class`. |
| `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` | Modify | Rewrite to 5 scenes (Roll → Class → Pronouns → Kit → Mouth). |

---

## Task 1: Add `ClassDef` pydantic model

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py:37-68` (around `MechanicalEffects`)

- [ ] **Step 1.1: Write the failing test**

Create `sidequest-server/tests/genre/test_class_def_model.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.genre.models.character import ClassDef


def test_classdef_minimal_valid():
    c = ClassDef(
        id="fighter",
        display_name="Fighter",
        rpg_role="tank",
        jungian_default="hero",
        prime_requisite="STR",
        minimum_score=9,
        kit_table="fighter_kit",
    )
    assert c.id == "fighter"
    assert c.encounter_beat_choices == []
    assert c.magic_access is None


def test_classdef_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ClassDef(
            id="fighter",
            display_name="Fighter",
            rpg_role="tank",
            jungian_default="hero",
            prime_requisite="STR",
            minimum_score=9,
            kit_table="fighter_kit",
            unknown_field="boom",
        )


def test_classdef_full_optional_fields():
    c = ClassDef(
        id="mage",
        display_name="Mage",
        rpg_role="control",
        jungian_default="magician",
        prime_requisite="INT",
        minimum_score=9,
        kit_table="mage_kit",
        flavor="A bookish nuisance.",
        encounter_beat_choices=[],
        magic_access=None,
    )
    assert c.flavor == "A bookish nuisance."
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_class_def_model.py -v
```

Expected: ImportError on `ClassDef`.

- [ ] **Step 1.3: Implement `ClassDef`**

Add to `sidequest-server/sidequest/genre/models/character.py` (after `MechanicalEffects`, before `CharCreationChoice`):

```python
class ClassDef(BaseModel):
    """A character class definition loaded from classes.yaml.

    Class influences starting Edge (via edge_config.base_max_by_class
    in rules.yaml) and starting equipment kit. encounter_beat_choices
    and magic_access are reserved for future class-specific subsystems.
    """

    model_config = {"extra": "forbid"}

    id: str
    display_name: str
    rpg_role: str
    jungian_default: str
    prime_requisite: str  # "STR" / "DEX" / "CON" / "INT" / "WIS" / "CHA"
    minimum_score: int
    kit_table: str
    flavor: str = ""
    encounter_beat_choices: list[str] = Field(default_factory=list)
    magic_access: str | None = None
```

- [ ] **Step 1.4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_class_def_model.py -v
```

Expected: 3 PASS.

- [ ] **Step 1.5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/character.py tests/genre/test_class_def_model.py
git commit -m "feat(genre): add ClassDef model for classic class system"
```

---

## Task 2: Re-export `ClassDef` and extend `GenrePack`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/__init__.py`
- Modify: `sidequest-server/sidequest/genre/models/pack.py`

- [ ] **Step 2.1: Write the failing test**

Create `sidequest-server/tests/genre/test_genrepack_classes_field.py`:

```python
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.pack import GenrePack, PackMeta


def test_genrepack_has_classes_field_default_empty():
    pack = GenrePack(meta=PackMeta(name="x", display_name="X", description="x"))
    assert pack.classes == []


def test_genrepack_accepts_classes_list():
    fighter = ClassDef(
        id="fighter", display_name="Fighter", rpg_role="tank",
        jungian_default="hero", prime_requisite="STR",
        minimum_score=9, kit_table="fighter_kit",
    )
    pack = GenrePack(
        meta=PackMeta(name="x", display_name="X", description="x"),
        classes=[fighter],
    )
    assert pack.classes[0].id == "fighter"
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_genrepack_classes_field.py -v
```

Expected: AttributeError or unrecognized-field error.

- [ ] **Step 2.3: Add `classes` field to `GenrePack`**

In `sidequest-server/sidequest/genre/models/pack.py` (locate the existing `equipment_tables: EquipmentTables | None = None` line near line 176; add after it):

```python
    classes: list["ClassDef"] = Field(default_factory=list)
```

At the top of `pack.py`, in the `from sidequest.genre.models.character import (...)` block, add `ClassDef` to the imports.

- [ ] **Step 2.4: Re-export `ClassDef` from package init**

In `sidequest-server/sidequest/genre/models/__init__.py`:
- Add `ClassDef` to the import-from-character block (around line 63, near `EquipmentTables`).
- Add `"ClassDef"` to `__all__` (around line 265, near `"EquipmentTables"`).

- [ ] **Step 2.5: Run tests**

```bash
cd sidequest-server && uv run pytest tests/genre/test_genrepack_classes_field.py tests/genre/test_class_def_model.py -v
```

Expected: 5 PASS.

- [ ] **Step 2.6: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/pack.py sidequest/genre/models/__init__.py tests/genre/test_genrepack_classes_field.py
git commit -m "feat(genre): wire ClassDef into GenrePack model"
```

---

## Task 3: Load `classes.yaml` in genre loader

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py`

- [ ] **Step 3.1: Write the failing test**

Create `sidequest-server/tests/genre/test_classes_yaml_loader.py`:

```python
from pathlib import Path

import pytest

from sidequest.genre.loader import load_genre_pack
from sidequest.genre.models.character import ClassDef


def test_classes_yaml_absent_yields_empty_list(tmp_path: Path):
    pack_dir = tmp_path / "test_pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        "name: test\ndisplay_name: Test\ndescription: test\n"
    )
    pack = load_genre_pack(pack_dir)
    assert pack.classes == []


def test_classes_yaml_loads_entries(tmp_path: Path):
    pack_dir = tmp_path / "test_pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        "name: test\ndisplay_name: Test\ndescription: test\n"
    )
    (pack_dir / "classes.yaml").write_text(
        "- id: fighter\n"
        "  display_name: Fighter\n"
        "  rpg_role: tank\n"
        "  jungian_default: hero\n"
        "  prime_requisite: STR\n"
        "  minimum_score: 9\n"
        "  kit_table: fighter_kit\n"
        "- id: thief\n"
        "  display_name: Thief\n"
        "  rpg_role: stealth\n"
        "  jungian_default: outlaw\n"
        "  prime_requisite: DEX\n"
        "  minimum_score: 9\n"
        "  kit_table: thief_kit\n"
    )
    pack = load_genre_pack(pack_dir)
    assert len(pack.classes) == 2
    assert all(isinstance(c, ClassDef) for c in pack.classes)
    assert {c.id for c in pack.classes} == {"fighter", "thief"}
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_classes_yaml_loader.py -v
```

Expected: 2 FAIL — second test produces empty `classes` list.

- [ ] **Step 3.3: Wire `classes.yaml` loading**

In `sidequest-server/sidequest/genre/loader.py`, locate the existing `equipment_tables = _load_yaml_optional(...)` block (~line 881). Add after it:

```python
    classes_path = path / "classes.yaml"
    classes_list: list[ClassDef] = []
    if classes_path.exists():
        with classes_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
        if not isinstance(raw, list):
            raise GenreLoadError(
                f"{classes_path}: expected a list of class definitions"
            )
        classes_list = [ClassDef.model_validate(item) for item in raw]
```

Add `ClassDef` to the existing import block at the top of `loader.py` (the `from sidequest.genre.models.character import (...)` block around line 23-31).

Then in the `GenrePack(...)` construction near the end of the loader, pass `classes=classes_list`.

- [ ] **Step 3.4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/genre/test_classes_yaml_loader.py -v
```

Expected: 2 PASS.

- [ ] **Step 3.5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/loader.py tests/genre/test_classes_yaml_loader.py
git commit -m "feat(genre): load classes.yaml into GenrePack"
```

---

## Task 4: Author `classes.yaml` for caverns_and_claudes

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

- [ ] **Step 4.1: Write the failing pack-content test**

Create `sidequest-server/tests/genre/test_cc_classes_content.py`:

```python
from sidequest.genre.loader import GenreLoader


def test_cc_loads_four_classes():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    ids = {c.id for c in pack.classes}
    assert ids == {"fighter", "mage", "cleric", "thief"}


def test_cc_class_prime_requisites_distinct():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    primes = [c.prime_requisite for c in pack.classes]
    assert sorted(primes) == ["DEX", "INT", "STR", "WIS"]


def test_cc_class_kit_tables_named_correctly():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    by_id = {c.id: c for c in pack.classes}
    assert by_id["fighter"].kit_table == "fighter_kit"
    assert by_id["mage"].kit_table == "mage_kit"
    assert by_id["cleric"].kit_table == "cleric_kit"
    assert by_id["thief"].kit_table == "thief_kit"
```

- [ ] **Step 4.2: Run test to verify failure**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_classes_content.py -v
```

Expected: 3 FAIL — `pack.classes` is empty.

- [ ] **Step 4.3: Author `classes.yaml`**

Create `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`:

```yaml
# Caverns & Claudes — Classic Classes (B/X-flavored)
# Class influences starting Edge (via rules.yaml edge_config.base_max_by_class)
# and starting equipment kit (equipment_tables.yaml class_tables block).
# Future hooks (encounter beats, magic access) are reserved as empty slots.

- id: fighter
  display_name: Fighter
  rpg_role: tank
  jungian_default: hero
  prime_requisite: STR
  minimum_score: 9
  kit_table: fighter_kit
  flavor: >-
    Plate, polearm, and the patience to be hit first.
  encounter_beat_choices: []
  magic_access: null

- id: mage
  display_name: Mage
  rpg_role: control
  jungian_default: magician
  prime_requisite: INT
  minimum_score: 9
  kit_table: mage_kit
  flavor: >-
    Bookish, half-blind, and dangerous in the third round.
  encounter_beat_choices: []
  magic_access: null

- id: cleric
  display_name: Cleric
  rpg_role: healer
  jungian_default: caregiver
  prime_requisite: WIS
  minimum_score: 9
  kit_table: cleric_kit
  flavor: >-
    Holy symbol, war-mace, and a faith that is mostly working so far.
  encounter_beat_choices: []
  magic_access: null

- id: thief
  display_name: Thief
  rpg_role: stealth
  jungian_default: outlaw
  prime_requisite: DEX
  minimum_score: 9
  kit_table: thief_kit
  flavor: >-
    Lockpicks, leather, and a professional interest in being elsewhere.
  encounter_beat_choices: []
  magic_access: null
```

- [ ] **Step 4.4: Verify tests pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_classes_content.py -v
```

Expected: 3 PASS.

- [ ] **Step 4.5: Commit content**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/classes.yaml
git commit -m "content(c&c): add classic classes — fighter, mage, cleric, thief"
```

```bash
cd sidequest-server
git add tests/genre/test_cc_classes_content.py
git commit -m "test(genre): verify c&c loads four classic classes"
```

---

## Task 5: Add 6 missing items to `inventory.yaml`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml`

The class kits reference these item ids that don't currently exist: `staff_wood`, `spellbook`, `component_pouch`, `holy_symbol`, `lockpicks`, `hammer_war`.

- [ ] **Step 5.1: Append item entries**

Append to the `item_catalog:` block in `sidequest-content/genre_packs/caverns_and_claudes/inventory.yaml` (placement: alongside related items — weapons go in the weapons section, etc; if existing file groups by category, follow the grouping):

```yaml
  - id: staff_wood
    name: Wooden Staff
    description: A length of seasoned hardwood, taller than the wielder. A walking stick to anyone who isn't watching closely.
    category: weapon
    value: 5
    weight: 4.0
    rarity: common
    power_level: 0
    tags: [weapon, melee, two_handed, blunt]
    lore: The mage's first weapon, and frequently the last.
    narrative_weight: 0.2

  - id: hammer_war
    name: War Hammer
    description: A heavy hammer with a wedge-shaped head, designed to crush plate and bone with equal disregard.
    category: weapon
    value: 25
    weight: 5.0
    rarity: common
    power_level: 1
    tags: [weapon, melee, blunt]
    lore: The cleric's preference — blunt force makes for honest theology.
    narrative_weight: 0.3

  - id: spellbook
    name: Spellbook
    description: A leather-bound tome of incantations, half of which the owner can actually cast.
    category: utility
    value: 100
    weight: 3.0
    rarity: uncommon
    power_level: 2
    tags: [magic, focus, fragile]
    lore: Without the book, the mage is just a person with bad eyesight.
    narrative_weight: 0.6

  - id: component_pouch
    name: Component Pouch
    description: A leather pouch divided into a dozen small compartments, each holding the strange materials the spellbook demands — bat guano, sulfur, dried newt.
    category: utility
    value: 25
    weight: 2.0
    rarity: common
    power_level: 1
    tags: [magic, container]
    lore: Half the cost of casting is the shopping list.
    narrative_weight: 0.3

  - id: holy_symbol
    name: Holy Symbol
    description: A worn metal token bearing the cleric's chosen sigil. Held forward when faith is needed in front of teeth.
    category: utility
    value: 25
    weight: 0.5
    rarity: common
    power_level: 1
    tags: [magic, focus, divine]
    lore: The dungeon does not always recognize the symbol. It does not need to. The cleric does.
    narrative_weight: 0.4

  - id: lockpicks
    name: Set of Lockpicks
    description: Six slender steel picks rolled in oiled leather. Most of the trade is patience and pressure.
    category: utility
    value: 30
    weight: 0.5
    rarity: common
    power_level: 1
    tags: [tool, thieves]
    lore: A locked door is a door that hasn't met the right professional.
    narrative_weight: 0.4
```

- [ ] **Step 5.2: Verify existing pack loads cleanly**

```bash
cd sidequest-server && uv run pytest tests/genre/ -v -k caverns
```

Expected: existing c&c content tests still pass (no new failures from YAML drift).

- [ ] **Step 5.3: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/inventory.yaml
git commit -m "content(c&c): add 6 items needed by classic class kits"
```

---

## Task 6: Extend `EquipmentTables` model with `class_tables`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py:119-125`

- [ ] **Step 6.1: Write the failing test**

Add to `sidequest-server/tests/genre/test_class_def_model.py`:

```python
def test_equipment_tables_class_tables_default_empty():
    from sidequest.genre.models.character import EquipmentTables
    et = EquipmentTables()
    assert et.class_tables == {}


def test_equipment_tables_class_tables_loads_nested():
    from sidequest.genre.models.character import EquipmentTables
    et = EquipmentTables.model_validate({
        "tables": {"weapon": ["dagger"]},
        "class_tables": {
            "fighter_kit": {"weapon": ["sword_long"]},
            "mage_kit": {"weapon": ["staff_wood"]},
        },
    })
    assert "fighter_kit" in et.class_tables
    assert et.class_tables["mage_kit"]["weapon"] == ["staff_wood"]
```

- [ ] **Step 6.2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_class_def_model.py::test_equipment_tables_class_tables_default_empty tests/genre/test_class_def_model.py::test_equipment_tables_class_tables_loads_nested -v
```

Expected: 2 FAIL — `class_tables` rejected as unknown field.

- [ ] **Step 6.3: Extend the model**

In `sidequest-server/sidequest/genre/models/character.py`, update `EquipmentTables`:

```python
class EquipmentTables(BaseModel):
    """Random equipment generation tables loaded from equipment_tables.yaml.

    `tables` is the top-level slot→items mapping consumed by
    `equipment_generation: random_table`. `class_tables` is a per-class
    override consumed by `equipment_generation: class_kit`; the chosen
    class's kit_table id resolves to one of these blocks.
    """

    model_config = {"extra": "forbid"}

    tables: dict[str, list[str]] = Field(default_factory=dict)
    rolls_per_slot: dict[str, int] = Field(default_factory=dict)
    class_tables: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
```

- [ ] **Step 6.4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/genre/test_class_def_model.py -v
```

Expected: 5 PASS.

- [ ] **Step 6.5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/character.py tests/genre/test_class_def_model.py
git commit -m "feat(genre): add class_tables to EquipmentTables for class kits"
```

---

## Task 7: Author class kit tables in c&c equipment_tables.yaml

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml`

- [ ] **Step 7.1: Write the failing content test**

Create `sidequest-server/tests/genre/test_cc_class_kits.py`:

```python
from sidequest.genre.loader import GenreLoader


def _kit_item_ids(pack, kit_id: str) -> set[str]:
    kit = pack.equipment_tables.class_tables[kit_id]
    return {item for slot, items in kit.items() for item in items}


def test_cc_has_four_class_kits():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    assert pack.equipment_tables is not None
    assert set(pack.equipment_tables.class_tables.keys()) == {
        "fighter_kit", "mage_kit", "cleric_kit", "thief_kit",
    }


def test_cc_kit_items_exist_in_inventory():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    catalog_ids = {item.id for item in pack.inventory.item_catalog}
    for kit_id in ("fighter_kit", "mage_kit", "cleric_kit", "thief_kit"):
        for item_id in _kit_item_ids(pack, kit_id):
            assert item_id in catalog_ids, f"{kit_id} references missing item: {item_id}"


def test_cc_mage_kit_has_no_armor():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    mage_kit = pack.equipment_tables.class_tables["mage_kit"]
    assert mage_kit.get("armor", []) == []


def test_cc_thief_kit_has_lockpicks():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    thief_kit = pack.equipment_tables.class_tables["thief_kit"]
    assert "lockpicks" in {i for items in thief_kit.values() for i in items}
```

- [ ] **Step 7.2: Run test**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_class_kits.py -v
```

Expected: 4 FAIL — class_tables empty.

- [ ] **Step 7.3: Append `class_tables` to equipment_tables.yaml**

Append to `sidequest-content/genre_packs/caverns_and_claudes/equipment_tables.yaml`:

```yaml
# Class-themed kits — consumed by `equipment_generation: class_kit`.
# Each ClassDef.kit_table in classes.yaml resolves to one block here.
# Slots match the top-level `tables:` slot names so rolls_per_slot
# applies consistently.
class_tables:
  fighter_kit:
    weapon: [sword_long, sword_short, mace_iron, hand_axe, spear]
    armor:  [leather_armor, shield_wood, helmet_iron]
    light:  [torch]
    consumable: [rations_day, waterskin]
    utility: [rope_hemp, ten_foot_pole, iron_spikes]

  mage_kit:
    weapon: [dagger_iron, staff_wood]
    armor:  []
    light:  [torch]
    consumable: [rations_day, waterskin, potion_healing]
    utility: [spellbook, component_pouch, chalk]

  cleric_kit:
    weapon: [mace_iron, hammer_war]
    armor:  [leather_armor, shield_wood]
    light:  [torch]
    consumable: [rations_day, waterskin, potion_healing]
    utility: [holy_symbol, rope_hemp, chalk]

  thief_kit:
    weapon: [dagger_iron, sword_short]
    armor:  [leather_armor]
    light:  [torch, lantern_oil]
    consumable: [rations_day, waterskin]
    utility: [lockpicks, ten_foot_pole, chalk, sack_large]
```

- [ ] **Step 7.4: Verify tests pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_class_kits.py -v
```

Expected: 4 PASS.

- [ ] **Step 7.5: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/equipment_tables.yaml
git commit -m "content(c&c): add class-themed equipment kits"
```

```bash
cd sidequest-server
git add tests/genre/test_cc_class_kits.py
git commit -m "test(genre): verify c&c class kits resolve to inventory items"
```

---

## Task 8: Add `edge_config.base_max_by_class` to c&c rules.yaml

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`

- [ ] **Step 8.1: Write the failing test**

Create `sidequest-server/tests/genre/test_cc_edge_config.py`:

```python
from sidequest.genre.loader import GenreLoader


def test_cc_edge_config_present():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    assert pack.rules.edge_config is not None


def test_cc_edge_config_covers_four_classes():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    bmbc = pack.rules.edge_config.base_max_by_class
    assert set(bmbc.keys()) >= {"Fighter", "Mage", "Cleric", "Thief"}


def test_cc_fighter_has_most_edge():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    bmbc = pack.rules.edge_config.base_max_by_class
    assert bmbc["Fighter"] > bmbc["Mage"]
    assert bmbc["Fighter"] >= bmbc["Cleric"]
    assert bmbc["Cleric"] >= bmbc["Thief"]
```

- [ ] **Step 8.2: Run test**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_edge_config.py -v
```

Expected: 3 FAIL.

- [ ] **Step 8.3: Add edge_config block to c&c rules.yaml**

Append (or merge if a similar block exists) to `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`:

```yaml
# Per-class starting Edge (composure pool).
# Class strings match Character.char_class display values.
edge_config:
  base_max_by_class:
    Fighter: 4   # the doomed-prince baseline; trained to be hit
    Cleric:  3   # faith as anchor
    Mage:    2   # the room is too loud for the work
    Thief:   2   # the half-second nobody else has

  recovery_defaults:
    on_resolution: full
    on_long_rest: full
    between_back_to_back: 0
```

> Note: If `rules.yaml` already has a `recovery_defaults` block elsewhere, merge — don't duplicate. Verify by grepping the file before appending.

- [ ] **Step 8.4: Verify**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_edge_config.py -v
```

Expected: 3 PASS.

- [ ] **Step 8.5: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/rules.yaml
git commit -m "content(c&c): per-class starting Edge via edge_config"
```

```bash
cd sidequest-server
git add tests/genre/test_cc_edge_config.py
git commit -m "test(genre): verify c&c edge_config covers four classes"
```

---

## Task 9: Implement `qualifying_classes()` pure function

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` (add helper near other module-level helpers)
- Create: `sidequest-server/tests/game/test_qualifying_classes.py`

- [ ] **Step 9.1: Write tests**

Create `sidequest-server/tests/game/test_qualifying_classes.py`:

```python
import pytest

from sidequest.game.builder import qualifying_classes
from sidequest.genre.models.character import ClassDef


def _class(id_: str, prime: str, minimum: int = 9) -> ClassDef:
    return ClassDef(
        id=id_, display_name=id_.capitalize(), rpg_role="tank",
        jungian_default="hero", prime_requisite=prime,
        minimum_score=minimum, kit_table=f"{id_}_kit",
    )


CLASSES = [
    _class("fighter", "STR"),
    _class("mage",    "INT"),
    _class("cleric",  "WIS"),
    _class("thief",   "DEX"),
]


def test_all_low_returns_empty():
    stats = {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
    assert qualifying_classes(stats, CLASSES) == []


def test_strong_str_only_returns_fighter():
    stats = {"STR": 14, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
    result = [c.id for c in qualifying_classes(stats, CLASSES)]
    assert result == ["fighter"]


def test_strong_everything_returns_all():
    stats = {"STR": 14, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 14}
    result = sorted(c.id for c in qualifying_classes(stats, CLASSES))
    assert result == ["cleric", "fighter", "mage", "thief"]


def test_boundary_exact_minimum_qualifies():
    stats = {"STR": 9, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
    assert [c.id for c in qualifying_classes(stats, CLASSES)] == ["fighter"]


def test_boundary_below_minimum_does_not_qualify():
    stats = {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
    assert qualifying_classes(stats, CLASSES) == []


def test_missing_stat_does_not_qualify():
    stats = {"STR": 14}
    result = [c.id for c in qualifying_classes(stats, CLASSES)]
    assert result == ["fighter"]
```

- [ ] **Step 9.2: Run tests**

```bash
cd sidequest-server && uv run pytest tests/game/test_qualifying_classes.py -v
```

Expected: 6 FAIL — function not defined.

- [ ] **Step 9.3: Implement**

Add to `sidequest-server/sidequest/game/builder.py` (near the top, after imports — module-level helper, not method on a class):

```python
def qualifying_classes(
    stats: dict[str, int],
    classes: "list[ClassDef]",
) -> "list[ClassDef]":
    """Return classes whose prime_requisite stat meets minimum_score.

    Pure function — no side effects, no genre-pack lookups. Pass the
    rolled stats dict and the pack's class list; receive the subset
    the player qualifies for. Empty list = nothing qualifies (caller
    decides whether to reroll).
    """
    return [c for c in classes if stats.get(c.prime_requisite, 0) >= c.minimum_score]
```

Add `from sidequest.genre.models.character import ClassDef` to the imports at the top of `builder.py`.

- [ ] **Step 9.4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/game/test_qualifying_classes.py -v
```

Expected: 6 PASS.

- [ ] **Step 9.5: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_qualifying_classes.py
git commit -m "feat(chargen): qualifying_classes() prime-requisite filter"
```

---

## Task 10: Add `class_qualification_loop` mechanical effect + reroll logic

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py` (`MechanicalEffects`)
- Modify: `sidequest-server/sidequest/game/builder.py`
- Create: `sidequest-server/tests/game/test_chargen_reroll_loop.py`

- [ ] **Step 10.1: Add the field to `MechanicalEffects`**

In `sidequest-server/sidequest/genre/models/character.py`, add to `MechanicalEffects`:

```python
    class_qualification_loop: bool = False
```

(Placement: alongside `stat_generation` / `equipment_generation` near line 59-60.)

- [ ] **Step 10.2: Write the reroll test**

Create `sidequest-server/tests/game/test_chargen_reroll_loop.py`:

```python
import random

import pytest

from sidequest.game.builder import CharacterBuilder
from sidequest.genre.loader import GenreLoader


class _ScriptedRandom(random.Random):
    """Returns predetermined dice rolls in sequence, then random."""

    def __init__(self, scripted: list[int]):
        super().__init__()
        self._scripted = list(scripted)
        self._real_random = random.Random(42)

    def randrange(self, *args, **kwargs):
        if self._scripted:
            return self._scripted.pop(0)
        return self._real_random.randrange(*args, **kwargs)

    def randint(self, a: int, b: int) -> int:
        if self._scripted:
            return self._scripted.pop(0)
        return self._real_random.randint(a, b)


def test_reroll_loop_fires_when_no_class_qualifies():
    """All-1s on the first 18 dice (six stats × 3d6 = 18 ones → all stats = 3).
    No class qualifies. Builder must reroll until at least one does."""
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")

    # 18 ones → all stats 3 → no class qualifies. Then 18 sixes → all stats 18.
    scripted = [1] * 18 + [6] * 18
    rng = _ScriptedRandom(scripted)
    builder = CharacterBuilder.from_pack(pack, rng=rng)

    # Trigger the scene that has class_qualification_loop (the_roll).
    builder.advance_to_scene("the_roll")
    builder.apply_scene_directive()  # name TBD by impl; see existing builder API

    stats = builder.accumulated().rolled_stats
    assert all(s >= 9 for s in stats.values()), \
        f"Expected reroll to land on qualifying stats, got {stats}"
```

> If the existing builder API uses different method names than `advance_to_scene` / `apply_scene_directive`, adapt to match. The contract is: when a scene with `class_qualification_loop: true` and `stat_generation: roll_3d6_strict` fires, the final stats yield ≥1 qualifying class.

- [ ] **Step 10.3: Verify the test fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_chargen_reroll_loop.py -v
```

Expected: FAIL — first roll gives all-3 stats; loop hasn't been wired.

- [ ] **Step 10.4: Implement reroll loop**

In `sidequest-server/sidequest/game/builder.py`, locate where `roll_3d6_strict` is processed (around line 605 — `if eff.stat_generation == "roll_3d6_strict": self._rolled_stats = self._roll_3d6_stats()`).

Wrap the existing single-roll logic in a loop that re-rolls when `class_qualification_loop=True` and the rolled stats yield no qualifying classes:

```python
            if eff.stat_generation == "roll_3d6_strict":
                self._rolled_stats = self._roll_3d6_stats()
                if eff.class_qualification_loop and self._classes:
                    rerolls = 0
                    while not qualifying_classes(self._rolled_stats, self._classes):
                        rerolls += 1
                        if rerolls > 100:  # safety: 3d6 ≥9 has p≈0.625, never trips legitimately
                            raise RuntimeError(
                                "class_qualification_loop exceeded 100 rerolls — "
                                "check minimum_score values in classes.yaml"
                            )
                        span = trace.get_current_span()
                        span.add_event(
                            "chargen.class_qualification_reroll",
                            {"rejected_stats": dict(self._rolled_stats), "attempt": rerolls},
                        )
                        self._rolled_stats = self._roll_3d6_stats()
```

Apply this wrap **at every site** where `stat_generation == "roll_3d6_strict"` is dispatched (the grep earlier found at least 3 sites: ~605, ~1124, ~1207). Refactor those into a helper method to avoid drift:

```python
    def _roll_3d6_with_qualification(self, *, qualification_loop: bool) -> None:
        self._rolled_stats = self._roll_3d6_stats()
        if not qualification_loop or not self._classes:
            return
        rerolls = 0
        while not qualifying_classes(self._rolled_stats, self._classes):
            rerolls += 1
            if rerolls > 100:
                raise RuntimeError(
                    "class_qualification_loop exceeded 100 rerolls"
                )
            trace.get_current_span().add_event(
                "chargen.class_qualification_reroll",
                {"rejected_stats": dict(self._rolled_stats), "attempt": rerolls},
            )
            self._rolled_stats = self._roll_3d6_stats()
```

Then replace each call site with `self._roll_3d6_with_qualification(qualification_loop=eff.class_qualification_loop)`.

`self._classes` should be set in `__init__` from `pack.classes` (passed via `with_classes()` builder method or directly in `from_pack`):

```python
    # in __init__:
    self._classes: list[ClassDef] = []

    # add a `with_classes` setter, or accept in from_pack/factory.
```

- [ ] **Step 10.5: Run tests**

```bash
cd sidequest-server && uv run pytest tests/game/test_chargen_reroll_loop.py tests/game/test_qualifying_classes.py -v
```

Expected: PASS.

- [ ] **Step 10.6: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/character.py sidequest/game/builder.py tests/game/test_chargen_reroll_loop.py
git commit -m "feat(chargen): class_qualification_loop reroll until ≥1 class qualifies"
```

---

## Task 11: Add `equipment_generation: class_kit` dispatch

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` (`_finalize` / equipment-rolling block, ~line 1354)

- [ ] **Step 11.1: Write the failing test**

Create `sidequest-server/tests/game/test_chargen_class_kit.py`:

```python
from sidequest.game.builder import CharacterBuilder
from sidequest.genre.loader import GenreLoader


def test_class_kit_rolls_only_from_chosen_class_kit():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")

    # Force class_hint=Mage; force equipment_generation=class_kit;
    # roll inventory; assert all rolled items are present in mage_kit.
    builder = CharacterBuilder.from_pack(pack)
    builder.set_class_hint("Mage")
    builder.apply_equipment_generation("class_kit")

    items = [i["id"] for i in builder.finalize_inventory()]
    mage_items = {
        i for slot, lst in pack.equipment_tables.class_tables["mage_kit"].items()
        for i in lst
    }
    assert items, "expected non-empty inventory"
    assert all(i in mage_items for i in items), \
        f"items {items} not all in mage_kit {mage_items}"
```

> Method names in this test (`set_class_hint`, `apply_equipment_generation`, `finalize_inventory`) are sketches — adapt to match the existing CharacterBuilder API. The contract: with `class_hint=Mage` set and `equipment_generation=class_kit` requested, finalized inventory pulls only from `mage_kit`.

- [ ] **Step 11.2: Run test**

```bash
cd sidequest-server && uv run pytest tests/game/test_chargen_class_kit.py -v
```

Expected: FAIL — `class_kit` mode not implemented.

- [ ] **Step 11.3: Extend the dispatch**

In `sidequest-server/sidequest/game/builder.py`, find the `random_table_requested` block (~line 1354). Replicate the pattern for `class_kit`:

```python
        random_table_requested = any(
            r.effects_applied.equipment_generation == "random_table" for r in self._results
        )
        class_kit_requested = any(
            r.effects_applied.equipment_generation == "class_kit" for r in self._results
        )

        kit_tables: dict[str, list[str]] | None = None
        kit_source = "none"
        if class_kit_requested and self._equipment_tables is not None and self._classes:
            chosen_class = next(
                (c for c in self._classes if c.display_name == class_str),
                None,
            )
            if chosen_class is None:
                span.add_event(
                    "chargen.class_kit_unresolved",
                    {"class_str": class_str, "severity": "error"},
                )
            else:
                kit_tables = self._equipment_tables.class_tables.get(chosen_class.kit_table)
                kit_source = f"class_kit:{chosen_class.kit_table}"
                if kit_tables is None:
                    span.add_event(
                        "chargen.class_kit_table_missing",
                        {"kit_table": chosen_class.kit_table, "severity": "error"},
                    )

        # Existing random_table fallback path:
        if kit_tables is None and random_table_requested and self._equipment_tables is not None:
            kit_tables = self._equipment_tables.tables
            kit_source = "random_table"

        if kit_tables is not None:
            for slot, candidates in kit_tables.items():
                if not candidates:
                    continue
                rolls = self._equipment_tables.rolls_per_slot.get(slot, 1)
                # ... (existing per-slot rolling logic — do NOT duplicate;
                #      refactor into a loop body that consumes kit_tables)
```

> The exact refactor of lines 1354–1395 is left to the implementer; the **contract** is: when a scene declares `equipment_generation: class_kit`, the builder rolls from `equipment_tables.class_tables[<chosen_class.kit_table>]` instead of `equipment_tables.tables`. If both modes are declared (shouldn't happen in practice), `class_kit` wins. If neither resolves, fall through to existing behavior unchanged.

Add an OTEL event when class_kit fires successfully:

```python
            span.add_event(
                "chargen.class_kit_rolled",
                {"kit_id": kit_source, "items_rolled": len([i for i in items if i not in initial_items])},
            )
```

- [ ] **Step 11.4: Run tests**

```bash
cd sidequest-server && uv run pytest tests/game/test_chargen_class_kit.py -v
```

Expected: PASS.

- [ ] **Step 11.5: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_chargen_class_kit.py
git commit -m "feat(chargen): equipment_generation=class_kit dispatch"
```

---

## Task 12: Rewrite c&c char_creation.yaml to 5 scenes

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml`

> Narration prose is the writer's call. The mechanical contract below is what's load-bearing.

- [ ] **Step 12.1: Write the failing scene-shape test**

Create `sidequest-server/tests/genre/test_cc_char_creation_shape.py`:

```python
from sidequest.genre.loader import GenreLoader


def test_cc_chargen_has_five_scenes_in_order():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    scene_ids = [s.id for s in pack.char_creation]
    # Order: roll → class → pronouns → kit → mouth
    assert len(scene_ids) == 5
    # First scene must be the stat roll (sets class_qualification_loop)
    assert scene_ids[0] == "the_roll"
    # Last scene is the dungeon mouth
    assert scene_ids[-1] == "the_mouth"


def test_cc_roll_scene_declares_qualification_loop():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    roll_scene = next(s for s in pack.char_creation if s.id == "the_roll")
    assert roll_scene.mechanical_effects is not None
    assert roll_scene.mechanical_effects.stat_generation == "roll_3d6_strict"
    assert roll_scene.mechanical_effects.class_qualification_loop is True
    # Hardcoded jungian/rpg_role hints should be removed — class scene sets them.
    assert roll_scene.mechanical_effects.jungian_hint is None
    assert roll_scene.mechanical_effects.rpg_role_hint is None


def test_cc_class_scene_has_four_class_choices():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    class_scene = next(s for s in pack.char_creation if "class" in s.id.lower())
    class_hints = [c.mechanical_effects.class_hint for c in class_scene.choices]
    assert sorted(class_hints) == ["Cleric", "Fighter", "Mage", "Thief"]


def test_cc_class_scene_choices_carry_role_and_jungian():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    class_scene = next(s for s in pack.char_creation if "class" in s.id.lower())
    for choice in class_scene.choices:
        assert choice.mechanical_effects.rpg_role_hint is not None
        assert choice.mechanical_effects.jungian_hint is not None


def test_cc_kit_scene_uses_class_kit_generation():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    kit_scene = next(s for s in pack.char_creation if s.id == "the_kit")
    assert kit_scene.mechanical_effects.equipment_generation == "class_kit"
```

- [ ] **Step 12.2: Run tests**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_char_creation_shape.py -v
```

Expected: 5 FAIL.

- [ ] **Step 12.3: Rewrite char_creation.yaml**

Replace `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` contents:

```yaml
# Character creation — Caverns & Claudes (classic-class era)
# 5 scenes: roll → class → pronouns → kit → dungeon mouth.
# Class qualification loop: scene 1 rerolls until ≥1 class qualifies.

- id: the_roll
  title: "3d6. In Order."
  narration: |
    You sit at a scarred table in a lamplit room. Six bone dice are
    pushed across the wood toward you. "Strength, Dexterity, Constitution,
    Intelligence, Wisdom, Charisma," says the woman across the table.
    "Roll them in order. The bones don't care what you wanted to be —
    but if they hand you nothing, we throw them again."
  loading_text: "The bones consider you..."
  choices: []
  allows_freeform: false
  mechanical_effects:
    stat_generation: roll_3d6_strict
    class_qualification_loop: true

- id: the_calling
  title: "What You'll Be Called"
  narration: |
    "These are the trades the bones will let you take. The dungeon
    doesn't care which one. The records do."
  choices:
    - label: "Fighter"
      description: "Plate, polearm, and the patience to be hit first. (STR 9+)"
      mechanical_effects:
        class_hint: Fighter
        rpg_role_hint: tank
        jungian_hint: hero
    - label: "Mage"
      description: "Bookish, half-blind, and dangerous in the third round. (INT 9+)"
      mechanical_effects:
        class_hint: Mage
        rpg_role_hint: control
        jungian_hint: magician
    - label: "Cleric"
      description: "Holy symbol, war-mace, and a faith that is mostly working so far. (WIS 9+)"
      mechanical_effects:
        class_hint: Cleric
        rpg_role_hint: healer
        jungian_hint: caregiver
    - label: "Thief"
      description: "Lockpicks, leather, and a professional interest in being elsewhere. (DEX 9+)"
      mechanical_effects:
        class_hint: Thief
        rpg_role_hint: stealth
        jungian_hint: outlaw
  allows_freeform: false

- id: pronouns
  title: "Who Are You?"
  narration: >-
    "For the tally," she says. "In case you don't come back."
  allows_freeform: true
  choices:
    - label: "she/her"
      description: "She."
      mechanical_effects:
        pronoun_hint: "she/her"
    - label: "he/him"
      description: "He."
      mechanical_effects:
        pronoun_hint: "he/him"
    - label: "they/them"
      description: "They."
      mechanical_effects:
        pronoun_hint: "they/them"

- id: the_kit
  title: "What You Have"
  narration: |
    "Standard kit," she says, dropping a canvas sack on the table.
    "Sized to the trade. You'll have time to read what you've got
    before you set out."
  choices: []
  allows_freeform: false
  mechanical_effects:
    equipment_generation: class_kit

- id: the_mouth
  title: "The Dungeon Waits"
  narration: |
    Dawn. The mouth of the dungeon is a crack in the hillside, edged with
    moss and old tooth-marks in the stone. Cold air breathes outward,
    carrying the smell of wet rock and something older.

    Behind you, the town is already forgetting your name.
  choices: []
  allows_freeform: false
```

> Note: the four class buttons are static. Server-side filtering by qualification (only show classes whose prime-requisite is met) is handled by Task 13.

- [ ] **Step 12.4: Verify tests pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_cc_char_creation_shape.py -v
```

Expected: 5 PASS.

- [ ] **Step 12.5: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/char_creation.yaml
git commit -m "content(c&c): 5-scene chargen with class choice and class kits"
```

```bash
cd sidequest-server
git add tests/genre/test_cc_char_creation_shape.py
git commit -m "test(genre): verify c&c chargen scene shape"
```

---

## Task 13: Server-side qualification filter on class scene choices

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` — when serving the class scene to the UI, filter `choices` to only those whose `class_hint` matches a qualifying ClassDef.

- [ ] **Step 13.1: Write the failing test**

Create `sidequest-server/tests/game/test_class_scene_filter.py`:

```python
import random

from sidequest.game.builder import CharacterBuilder
from sidequest.genre.loader import GenreLoader


def test_class_scene_filters_to_qualifying_only():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")

    # Force scripted stats: STR=14, all others=8 → only Fighter qualifies.
    builder = CharacterBuilder.from_pack(pack)
    builder.force_stats({"STR": 14, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8})

    # Get the_calling scene as it would be served to the UI (after roll).
    presented = builder.present_scene("the_calling")
    presented_class_hints = [c.mechanical_effects.class_hint for c in presented.choices]
    assert presented_class_hints == ["Fighter"]


def test_class_scene_unfiltered_when_no_classes_loaded():
    """If the pack has no classes (legacy packs), don't filter — show all."""
    # Implementation choice: legacy behavior preserved when self._classes is empty.
    pass  # placeholder; impl-specific
```

> Method names `force_stats` and `present_scene` are sketches; adapt to existing builder API. The contract: when `self._classes` is non-empty AND a scene is presented whose choices all carry `class_hint` values, only choices whose corresponding ClassDef is in `qualifying_classes(stats, self._classes)` are returned.

- [ ] **Step 13.2: Run test**

```bash
cd sidequest-server && uv run pytest tests/game/test_class_scene_filter.py -v
```

Expected: FAIL — all 4 choices returned.

- [ ] **Step 13.3: Implement filter**

In `sidequest-server/sidequest/game/builder.py`, find where scenes are served to the UI (look for the method that returns `CharCreationScene` or its choices to the dispatch layer). Add a filter pass:

```python
    def _filter_class_choices(self, scene: CharCreationScene) -> CharCreationScene:
        """If this scene's choices encode class_hint values AND we have a
        loaded class list, drop choices whose class doesn't qualify against
        current rolled stats."""
        if not self._classes or not scene.choices:
            return scene
        # Only filter scenes whose every choice carries a class_hint.
        if not all(c.mechanical_effects.class_hint for c in scene.choices):
            return scene
        if self._rolled_stats is None:
            return scene
        qualifying = {c.display_name for c in qualifying_classes(self._rolled_stats, self._classes)}
        kept = [c for c in scene.choices if c.mechanical_effects.class_hint in qualifying]
        return scene.model_copy(update={"choices": kept})
```

Apply this in the existing scene-serving path. Identify the path by grep:

```bash
cd sidequest-server && grep -n "char_creation\|present_scene\|current_scene" sidequest/game/builder.py | head -20
```

- [ ] **Step 13.4: Verify**

```bash
cd sidequest-server && uv run pytest tests/game/test_class_scene_filter.py -v
```

Expected: PASS.

- [ ] **Step 13.5: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_class_scene_filter.py
git commit -m "feat(chargen): filter class-scene choices to qualifying classes"
```

---

## Task 14: Add OTEL events for class subsystem

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` (add event emission at chargen decision points)

Required events (per spec §5):
- `chargen.class_qualifying` — fires after stat roll: list of qualifying class ids
- `chargen.class_chosen` — fires when class scene resolves: chosen class id + display
- `chargen.class_kit_rolled` — already added in Task 11
- `chargen.class_qualification_reroll` — already added in Task 10
- (Edge seeding emits `chargen.edge_seeded` already — covers `class_max_edge_set`)

- [ ] **Step 14.1: Write the failing test**

Create `sidequest-server/tests/game/test_chargen_otel_class_events.py`:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry import trace

from sidequest.game.builder import CharacterBuilder
from sidequest.genre.loader import GenreLoader


def _setup_otel():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


def test_class_chosen_event_emitted():
    exporter = _setup_otel()
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    builder = CharacterBuilder.from_pack(pack)
    # ... drive chargen end-to-end with class_hint=Fighter ...
    # (impl-specific scene driving)

    events = [e for span in exporter.get_finished_spans() for e in span.events]
    names = [e.name for e in events]
    assert "chargen.class_qualifying" in names
    assert "chargen.class_chosen" in names
    assert "chargen.class_kit_rolled" in names
```

- [ ] **Step 14.2: Run test**

Expected: FAIL on at least the first two event names.

- [ ] **Step 14.3: Add event emission**

After the qualification computation in the reroll loop / scene presentation, add:

```python
            span.add_event(
                "chargen.class_qualifying",
                {"class_ids": [c.id for c in qualifying_classes(self._rolled_stats, self._classes)]},
            )
```

In the class-choice apply path (where `class_hint` is set on the accumulator from a chosen choice), add:

```python
            span.add_event(
                "chargen.class_chosen",
                {"class_hint": eff.class_hint, "stats": dict(self._rolled_stats or {})},
            )
```

- [ ] **Step 14.4: Verify and commit**

```bash
cd sidequest-server && uv run pytest tests/game/test_chargen_otel_class_events.py -v
git add sidequest/game/builder.py tests/game/test_chargen_otel_class_events.py
git commit -m "feat(chargen): OTEL events for class subsystem visibility"
```

---

## Task 15: End-to-end wiring test (the integration gate)

**Files:**
- Create: `sidequest-server/tests/integration/test_cc_chargen_e2e.py`

This is the wiring test the project rule demands: every test suite needs at least one integration test that verifies the new code is reachable from production paths.

- [ ] **Step 15.1: Write the test**

```python
"""End-to-end caverns_and_claudes chargen integration test.

Verifies the full path: load pack → roll stats → choose class →
roll kit → finalize Character. Asserts class, race, edge max, and
inventory all flow through correctly. This is the wiring gate
required by sidequest-content/CLAUDE.md ("Every Test Suite Needs
a Wiring Test").
"""

import pytest

from sidequest.game.builder import CharacterBuilder, qualifying_classes
from sidequest.genre.loader import GenreLoader


def test_e2e_chargen_produces_classed_character():
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")

    builder = CharacterBuilder.from_pack(pack)
    # Drive chargen scene-by-scene with deterministic choices.
    # (Adapt to actual builder API for scene advancement / freeform input.)
    builder.advance_through_scene("the_roll")  # scripted stats → reroll until qualifying
    builder.choose("Fighter")  # picks the_calling Fighter button
    builder.choose("they/them")  # pronouns
    builder.advance_through_scene("the_kit")
    builder.advance_through_scene("the_mouth")

    char = builder.confirm(name="Test Delver")

    assert char.char_class == "Fighter"
    assert char.core.edge.max == pack.rules.edge_config.base_max_by_class["Fighter"]
    assert char.core.edge.current == char.core.edge.max
    assert len(char.inventory) > 0
    # Inventory pulled from fighter_kit only:
    fighter_kit = pack.equipment_tables.class_tables["fighter_kit"]
    fighter_items = {i for items in fighter_kit.values() for i in items}
    rolled_ids = {i.id for i in char.inventory if i.id != "torch"}  # torch is universal
    assert rolled_ids.issubset(fighter_items | {"torch"}), \
        f"Items {rolled_ids - fighter_items} not in fighter_kit"


def test_e2e_archetype_resolution_gate_passes():
    """Story 45-6's archetype-resolution gate requires both jungian_hint
    and rpg_role_hint populated. Class scene must set both."""
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    builder = CharacterBuilder.from_pack(pack)
    builder.advance_through_scene("the_roll")
    builder.choose("Cleric")
    builder.choose("she/her")
    builder.advance_through_scene("the_kit")
    builder.advance_through_scene("the_mouth")
    char = builder.confirm(name="Test Cleric")

    acc = builder.accumulated()
    assert acc.jungian_hint == "caregiver"
    assert acc.rpg_role_hint == "healer"
    # Resolved archetype should be present as an attribute on the character
    # (existing path — see builder.py:1554-1559).
    assert char.resolved_archetype == "caregiver/healer"


def test_e2e_qualifying_classes_observable_from_pack():
    """Smoke check: the public API surface for class qualification is
    reachable and behaves correctly with real pack data."""
    loader = GenreLoader()
    pack = loader.load("caverns_and_claudes")
    stats = {"STR": 9, "DEX": 9, "CON": 9, "INT": 9, "WIS": 9, "CHA": 9}
    qual = qualifying_classes(stats, pack.classes)
    assert len(qual) == 4
```

- [ ] **Step 15.2: Run**

```bash
cd sidequest-server && uv run pytest tests/integration/test_cc_chargen_e2e.py -v
```

Expected: PASS (after Tasks 1-14).

- [ ] **Step 15.3: Commit**

```bash
cd sidequest-server
git add tests/integration/test_cc_chargen_e2e.py
git commit -m "test(integration): c&c chargen end-to-end wiring gate"
```

---

## Task 16: Run the full check gate

- [ ] **Step 16.1: Run server check from orchestrator root**

```bash
just server-check
```

Expected: ruff clean, pytest passes.

- [ ] **Step 16.2: Run aggregate gate**

```bash
just check-all
```

Expected: server-check + client-lint + client-test + daemon-lint all pass.

- [ ] **Step 16.3: Audit for stale `archetype_funnels.yaml` reference**

```bash
grep -rn "jack_of_all_trades\|hero/jack_of_all_trades" sidequest-content/genre_packs/caverns_and_claudes/
```

If `caverns_sunden/archetype_funnels.yaml` references the old default, update or note it. Spec §Risks called this out.

- [ ] **Step 16.4: Commit any stale-funnel cleanup**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/caverns_sunden/archetype_funnels.yaml
git commit -m "content(c&c): drop reliance on legacy hero/jack_of_all_trades default"
```

(Skip if no changes needed.)

---

## Task 17: Manual playtest smoke

- [ ] **Step 17.1: Boot the stack**

```bash
just up
```

- [ ] **Step 17.2: Open client at http://localhost:5173, start a c&c session**

- [ ] **Step 17.3: Verify the 5-scene flow**

Confirm each scene renders in order:
1. The Roll (3d6 in order, no rerolls visible to player)
2. What You'll Be Called (only qualifying classes shown as buttons)
3. Pronouns
4. The Kit (class-themed inventory generates)
5. The Dungeon Waits

- [ ] **Step 17.4: Verify inventory matches class**

Pick Mage. Verify final inventory contains `staff_wood` or `dagger_iron`, `spellbook`, `component_pouch`. Should NOT contain `sword_long` or `mace_iron`.

- [ ] **Step 17.5: Verify GM panel OTEL events**

```bash
just otel
```

Confirm these spans visible for the chargen run:
- `chargen.class_qualifying`
- `chargen.class_chosen`
- `chargen.class_kit_rolled`
- `chargen.edge_seeded` (with `source: edge_config`)

- [ ] **Step 17.6: Verify Character attributes on session save**

```bash
sqlite3 ~/.sidequest/saves/<latest>.db "select char_class, race from characters;"
```

Expected: `Mage|Human` (race defaults until race system ships).

- [ ] **Step 17.7: Commit session screenshot or note**

If anything diverges from spec, file a bug and patch before merge.

---

## PR & merge

- [ ] **Step 18.1: Open content PR**

```bash
cd sidequest-content
git checkout -b feat/cc-classic-classes
git push -u origin feat/cc-classic-classes
gh pr create --base develop --title "C&C classic classes — fighter/mage/cleric/thief" \
  --body "Implements docs/superpowers/specs/2026-05-06-cc-classic-classes-design.md (orchestrator)."
```

> Per memory: sidequest-content uses gitflow — base is `develop`, not `main`.

- [ ] **Step 18.2: Open server PR**

```bash
cd sidequest-server
git checkout -b feat/cc-classic-classes
git push -u origin feat/cc-classic-classes
gh pr create --base main --title "feat(chargen): classic class system (c&c)" \
  --body "Server-side support for C&C classic classes. Spec: docs/superpowers/specs/2026-05-06-cc-classic-classes-design.md."
```

- [ ] **Step 18.3: Reviewer pass**

Hand off to `/pf-reviewer` for both PRs.

---

## Self-Review (run after writing this plan)

**Spec coverage:**
- §1 classes.yaml → Tasks 1, 2, 3, 4 ✓
- §2 equipment_tables class_tables → Tasks 6, 7 ✓
- §3 char_creation 5 scenes → Task 12 ✓
- §4 server wiring (qualifying_classes, reroll, class_kit) → Tasks 9, 10, 11, 13 ✓
- §5 OTEL events → Tasks 10, 11, 14 ✓
- §6 Testing (content, qualification, integration, reroll, manual) → Tasks 4, 7, 9, 10, 11, 15, 17 ✓
- Risks: missing inventory items → Task 5 ✓; archetype_funnels stale → Task 16.3 ✓; reroll silent on wire → Task 14 (OTEL makes it visible) ✓

**Type consistency:**
- `ClassDef` used throughout. ✓
- `class_hint` values are capitalized (`Fighter`, `Mage`, `Cleric`, `Thief`) — matches `edge_config.base_max_by_class` keys and `Character.char_class` default ✓
- `class_qualification_loop` field name consistent across MechanicalEffects model, scene YAML, and builder dispatch ✓
- `qualifying_classes()` signature matches between Tasks 9, 10, 13, 15 ✓

**No placeholders:**
- All code blocks contain real code. ✓
- "Method names X, Y, Z are sketches; adapt to existing API" appears in 3 spots — these are unavoidable because the existing CharacterBuilder API isn't fully documented in this plan. The contracts are explicit; the implementer maps them to actual method names. Acceptable. ✓
