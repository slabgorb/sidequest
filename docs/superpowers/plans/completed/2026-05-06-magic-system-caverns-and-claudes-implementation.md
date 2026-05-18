# C&C Magic System (Loose-Vancian B/X) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `learned_v1` magic plugin for Caverns & Claudes so Mage and Cleric prepare and cast B/X-canon L1 spells in Sünden, alongside the existing `item_legacy_v1` track for scrolls/wands/potions.

**Architecture:** New plugin under existing magic framework (`MAGIC_PLUGINS` registry, `MagicState` aggregate, `apply_working` cost-routing). Loose-Vancian: known list + per-rest preparation + slot economy. Saves use C&C's existing `opposed_check` attribute primitive. Damage applies to `momentum`. Spell catalog YAML drives per-spell mechanical effect; plugin enforces validation; `narration_apply` mutates state at parse-time (per ADR-001 — no reactive tools).

**Tech Stack:** Python 3.12 + pydantic + pytest (server), TypeScript + React + vitest (ui), YAML (content). Three repos: `sidequest-server`, `sidequest-content`, `sidequest-ui`. All target `develop` branch.

**Spec:** `docs/superpowers/specs/2026-05-06-magic-system-caverns-and-claudes-implementation-design.md`

---

## File Structure

### Server (`sidequest-server`)

| File | Action | Responsibility |
|---|---|---|
| `sidequest/magic/models.py` | Modify | Add `studied`/`granted` mechanism literals; add `spell_id`/`slot_level` fields to `MagicWorking` |
| `sidequest/magic/state.py` | Modify | Add `known_spells` and `prepared_spells` collections to `MagicState` |
| `sidequest/magic/plugins/learned_v1.yaml` | Create | Plugin descriptor (mechanisms, ledger templates, narrator register) |
| `sidequest/magic/plugins/learned_v1.py` | Create | Plugin class — validator + plugin_id registration |
| `sidequest/magic/plugins/__init__.py` | Modify | Star-import the new plugin |
| `sidequest/magic/learned_ops.py` | Create | Operations: `prepare`, `cast`, `rest`, `turn_undead` (free functions on MagicState) |
| `sidequest/magic/spell_catalog.py` | Create | Spell catalog loader + `SpellCatalog` model |
| `sidequest/genre/models/character.py` | Modify | Add `ClassMagicConfig` sub-model; `magic_config` field on `ClassDef` |
| `sidequest/genre/magic_loader.py` | Modify | Load spell catalogs from genre `spells/*.yaml`; bind to plugin instances |
| `sidequest/server/magic_init.py` | Modify | Per-class learned_v1 state instantiation at chargen |
| `sidequest/magic/context_builder.py` | Modify | Render `<learned-magic>` block for casting actors |
| `sidequest/telemetry/spans/magic.py` | Modify | Add `learned_v1.*` span definitions |
| `tests/magic/test_plugin_learned_v1.py` | Create | Plugin unit tests |
| `tests/magic/test_learned_ops.py` | Create | Prepare/cast/rest unit tests |
| `tests/magic/test_spell_catalog.py` | Create | Catalog loader tests |
| `tests/magic/test_e2e_learned_v1.py` | Create | End-to-end wiring test (chargen → prepare → cast → rest) |
| `tests/magic/fixtures/cc_arcane_l1.yaml` | Create | Frozen test fixture, 2-3 spells |

### Content (`sidequest-content`)

| File | Action | Responsibility |
|---|---|---|
| `genre_packs/caverns_and_claudes/magic.yaml` | Modify | `permitted_plugins`, `cost_types`, narrator register, design notes |
| `genre_packs/caverns_and_claudes/rules.yaml` | Modify | Update deprecation comment block (lines 4-7) |
| `genre_packs/caverns_and_claudes/classes.yaml` | Modify | `mage` + `cleric` `magic_access` + `magic_config` |
| `genre_packs/caverns_and_claudes/spells/arcane_l1.yaml` | Create | 12 M-U L1 spells, B/X canon, C&C voice |
| `genre_packs/caverns_and_claudes/spells/divine_l1.yaml` | Create | 8 Cleric L1 spells, B/X canon, C&C voice |
| `genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml` | Create | World-level magic config (intensity, divine_favor bar, Sünden register) |

### UI (`sidequest-ui`)

| File | Action | Responsibility |
|---|---|---|
| `src/components/CharacterPanel/LedgerPanel.tsx` | Modify | Render learned_v1 block (known/prepared/slots, divine_favor) |
| `src/components/CharacterPanel/PrepareSpellsAction.tsx` | Create | Button + modal: pick spells from known list to fill slot budget |
| `src/components/CharacterPanel/TurnUndeadAction.tsx` | Create | Cleric-only button; opposed-check trigger |
| `src/types/magic.ts` | Modify | TypeScript types matching server protocol additions |
| `src/__tests__/LedgerPanel.test.tsx` | Modify | Cover learned_v1 render path |

### Scenarios (orchestrator)

| File | Action | Responsibility |
|---|---|---|
| `scenarios/cc_mage_smoke.yaml` | Create | Headless playtest: Mage in Sünden delves Grimvault, casts Magic Missile |

---

## Branching

- **server**: `feat/magic-learned-v1` off `develop`. PRs target `develop`.
- **content**: `feat/cc-magic-learned-v1` off `develop`. PRs target `develop`.
- **ui**: `feat/cc-magic-ledger-panel` off `develop`. PRs target `develop`.
- **orchestrator**: scenario change can land on `main` directly per recent C&C class commits.

Each phase below names the repo. Cross-repo dependencies are flagged.

---

## Phase 1 — Spell catalog content (content repo)

The content fights the schema first. Shape the YAML before writing the loader against it.

### Task 1.1: Author arcane L1 spell catalog

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/spells/arcane_l1.yaml`

- [ ] **Step 1: Create the file with the schema header and the first three spells (the test set)**

```yaml
# Caverns & Claudes — Arcane L1 spell catalog (Magic-User / Elf list)
# Moldvay/Cook B/X canon, twelve spells, C&C voice.
# Schema: see docs/superpowers/specs/2026-05-06-magic-system-caverns-and-claudes-implementation-design.md §2

version: "0.1.0"
genre: caverns_and_claudes
tradition: arcane
level: 1

spells:
  - id: magic_missile
    name: "Magic Missile"
    level: 1
    tradition: arcane
    range: near
    target: single
    duration: instant
    save:
      stat: null
      effect: none
    effect_template: "Force dart strikes target — 1 momentum damage, auto-hit"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: |
      A bolt of glowing force, half-thought, half-aimed. The dart finds
      what the caster pointed at, even in dark, even around a corner if
      the corner is short. It does not miss. It also does not impress.
    hard_limits_check: []
    domain: physical
    otel_attrs: [cast_intent, validator_outcome]

  - id: sleep
    name: "Sleep"
    level: 1
    tradition: arcane
    range: near
    target: area
    duration: turns:1d4+1
    save:
      stat: WIS
      effect: negates
    effect_template: "Up to 4d4 HD of creatures (lowest HD first); save WIS or unconscious"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: |
      A slow, kind weight. The eyes go first, then the knees. The smallest
      foes drop first; the strongest may yet stand and look at you.
    hard_limits_check: []
    domain: psychic
    otel_attrs: [cast_intent, hd_affected, saves_made, saves_failed]

  - id: charm_person
    name: "Charm Person"
    level: 1
    tradition: arcane
    range: near
    target: single
    duration: until_rest
    save:
      stat: WIS
      effect: negates
    effect_template: "Single humanoid; save WIS or treats caster as trusted friend"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: |
      The target's eyes settle. The grip on the hilt loosens. They have
      always known you, and have always wanted to help you, and the
      reasons will come later. This works on people. People are flexible.
      Saint statues, talking doors, and the things in Grimvault are not.
    hard_limits_check: []
    domain: psychic
    otel_attrs: [cast_intent, save_made]
```

- [ ] **Step 2: Add the remaining 9 spells**

Add to `spells:` array in the same file: `detect_magic`, `floating_disc`, `hold_portal`, `light`, `protection_from_evil`, `read_languages`, `read_magic`, `shield`, `ventriloquism`. Each follows the schema above. Reference: any B/X retroclone for canonical mechanics. Write each `narrator_register` in the C&C voice (limestone, lamp-oil, the careful courtesy of Sünden) — no generic fantasy.

- [ ] **Step 3: Validate the YAML parses cleanly**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/spells/arcane_l1.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git checkout -b feat/cc-magic-learned-v1 develop
git add genre_packs/caverns_and_claudes/spells/arcane_l1.yaml
git commit -m "feat(c&c): arcane L1 spell catalog — 12 M-U spells, B/X canon"
```

### Task 1.2: Author divine L1 spell catalog

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/spells/divine_l1.yaml`

- [ ] **Step 1: Create the file with the 8 Cleric L1 spells**

```yaml
version: "0.1.0"
genre: caverns_and_claudes
tradition: divine
level: 1

spells:
  - id: cure_light_wounds
    name: "Cure Light Wounds"
    level: 1
    tradition: divine
    range: touch
    target: single
    duration: instant
    save: { stat: null, effect: none }
    effect_template: "Restore 1d6+1 momentum to touched ally"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: |
      A hand on the wound. A breath drawn together. The bleeding does not
      stop because the blood was lost; it stops because the body has been
      reminded what it is for. Whatever the cleric carries, they leave a
      little of it in the patient.
    hard_limits_check: [no_resurrection]
    domain: physical
    otel_attrs: [cast_intent, momentum_restored]
    reverse:
      id: cause_light_wounds
      effect_template: "Touch deals 1d6+1 momentum damage; opposed_check WIS to resist"
      narrator_register: |
        The cleric's hand lays on, but what passes through is the absence,
        not the presence. The thing they serve takes its share.
      domain: necromantic
```

- [ ] **Step 2: Add the remaining 7 spells**

`detect_evil`, `detect_magic`, `light` (with reverse `darkness`), `protection_from_evil`, `purify_food_and_water`, `remove_fear` (with reverse `cause_fear`), `resist_cold`. Each follows the schema. The Cleric `light` is the same mechanical effect as Mage `light` but with `tradition: divine` and a divine narrator_register.

- [ ] **Step 3: Validate**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/spells/divine_l1.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/spells/divine_l1.yaml
git commit -m "feat(c&c): divine L1 spell catalog — 8 Cleric spells, B/X canon"
```

---

## Phase 2 — Server framework extensions (server repo)

Extend the existing magic models so they can carry learned_v1 workings and so MagicState can hold the prepared/known spell collections.

### Task 2.1: Extend MagicWorking with `studied`/`granted` mechanisms + spell_id/slot_level

**Files:**
- Modify: `sidequest-server/sidequest/magic/models.py:79-101`
- Modify: `sidequest-server/sidequest/magic/state.py:43-57` (mirror in WorkingRecord)
- Test: `sidequest-server/tests/magic/test_models.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_models.py`:

```python
def test_magic_working_accepts_studied_mechanism_and_spell_id():
    """learned_v1 emits workings with mechanism='studied' and a spell_id."""
    from sidequest.magic.models import MagicWorking

    w = MagicWorking(
        plugin="learned_v1",
        mechanism="studied",
        actor="rux",
        domain="physical",
        narrator_basis="cast Magic Missile from prepared list",
        spell_id="magic_missile",
        slot_level=1,
        costs={"slots_l1": 1.0},
    )
    assert w.spell_id == "magic_missile"
    assert w.slot_level == 1


def test_magic_working_accepts_granted_mechanism():
    """learned_v1/divine emits workings with mechanism='granted'."""
    from sidequest.magic.models import MagicWorking

    w = MagicWorking(
        plugin="learned_v1",
        mechanism="granted",
        actor="brother_hesh",
        domain="physical",
        narrator_basis="Cleric heals via Cure Light Wounds",
        spell_id="cure_light_wounds",
        slot_level=1,
        costs={"slots_l1": 1.0},
    )
    assert w.mechanism == "granted"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_models.py::test_magic_working_accepts_studied_mechanism_and_spell_id -v`

Expected: FAIL — `pydantic.ValidationError: ... mechanism: Input should be 'faction', 'place', ...`

- [ ] **Step 3: Implement — extend the model**

Edit `sidequest/magic/models.py:79-101`:

```python
class MagicWorking(BaseModel):
    """A single magic event emitted by the narrator in game_patch.magic_working."""

    model_config = {"extra": "forbid"}

    plugin: str
    mechanism: Literal[
        "faction", "place", "time", "condition", "native",
        "discovery", "relational", "cosmic",
        "studied", "granted",
    ]
    actor: str
    costs: dict[str, float] = Field(default_factory=dict)
    domain: Literal[
        "elemental", "physical", "psychic", "spatial", "temporal",
        "necromantic", "illusory", "divinatory", "transmutative", "alchemical",
    ]
    narrator_basis: str
    # Plugin-specific fields. Validators enforce per-plugin requirements.
    flavor: str | None = None
    consent_state: str | None = None
    item_id: str | None = None
    alignment_with_item_nature: float | None = None
    # learned_v1 fields:
    spell_id: str | None = None
    slot_level: int | None = None
```

Mirror in `sidequest/magic/state.py:43-57` `WorkingRecord` (same two field additions).

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_models.py -v`

Expected: PASS (new tests + all prior tests still green).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git checkout -b feat/magic-learned-v1 develop
git add sidequest/magic/models.py sidequest/magic/state.py tests/magic/test_models.py
git commit -m "feat(magic): MagicWorking adds studied/granted mechanisms + spell_id/slot_level"
```

### Task 2.2: Add ClassMagicConfig sub-model on ClassDef

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py:72-92`
- Test: `sidequest-server/tests/genre/test_class_def.py` (create if absent)

- [ ] **Step 1: Write the failing test**

Create or append `tests/genre/test_class_def.py`:

```python
def test_class_def_accepts_magic_config():
    from sidequest.genre.models.character import ClassDef

    c = ClassDef(
        id="mage",
        display_name="Mage",
        rpg_role="control",
        jungian_default="magician",
        prime_requisite="INT",
        minimum_score=9,
        kit_table="mage_kit",
        magic_access="learned_v1",
        magic_config={
            "tradition": "arcane",
            "slots_by_class_level": {"1": {"1": 1}},
            "starting_known_spells": 2,
            "save_dc_stat": "INT",
        },
    )
    assert c.magic_config is not None
    assert c.magic_config.tradition == "arcane"
    assert c.magic_config.slots_by_class_level["1"]["1"] == 1


def test_class_def_magic_config_optional_for_non_caster():
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
    assert c.magic_access is None
    assert c.magic_config is None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/genre/test_class_def.py -v`

Expected: FAIL — `magic_config` extra-forbidden by ClassDef.

- [ ] **Step 3: Implement**

Edit `sidequest/genre/models/character.py:72-92` — add ClassMagicConfig and field:

```python
class ClassMagicConfig(BaseModel):
    """Per-class magic configuration. Loaded from classes.yaml.

    Carried into MagicState at chargen by magic_init to instantiate
    per-actor known/prepared/slot bookkeeping.
    """

    model_config = {"extra": "forbid"}

    tradition: str  # "arcane" | "divine"
    # str-keyed dicts because YAML 1.1 + JSON serialization both flatten
    # int keys to strings; pydantic handles round-trip.
    slots_by_class_level: dict[str, dict[str, int]]
    starting_known_spells: int
    save_dc_stat: str  # "INT" | "WIS" | "CHA"
    turn_undead: bool = False  # cleric-only class-special


class ClassDef(BaseModel):
    """A character class definition loaded from classes.yaml.

    Class influences starting Edge (via edge_config.base_max_by_class
    in rules.yaml), starting equipment kit, and (when magic_access is
    set) per-class magic config consumed by the magic_init pipeline.
    """

    model_config = {"extra": "forbid"}

    id: str
    display_name: str
    rpg_role: str
    jungian_default: str
    prime_requisite: str
    minimum_score: int
    kit_table: str
    flavor: str = ""
    encounter_beat_choices: list[str] = Field(default_factory=list)
    magic_access: str | None = None
    magic_config: ClassMagicConfig | None = None
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_class_def.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/character.py tests/genre/test_class_def.py
git commit -m "feat(genre): ClassDef adds optional ClassMagicConfig for caster classes"
```

### Task 2.3: Extend MagicState with learned_v1 collections

**Files:**
- Modify: `sidequest-server/sidequest/magic/state.py:91-150` (`MagicState`)
- Test: `sidequest-server/tests/magic/test_state.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_state.py`:

```python
def test_magic_state_learned_collections_default_empty():
    from sidequest.magic.state import MagicState
    from sidequest.magic.models import WorldMagicConfig, WorldKnowledge

    cfg = WorldMagicConfig(
        world_slug="test",
        allowed_sources=["learned"],
        active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[],
        hard_limits=[],
    )
    state = MagicState.from_config(cfg)
    assert state.known_spells == {}
    assert state.prepared_spells == {}


def test_magic_state_learn_spell_records_per_actor_known_list():
    from sidequest.magic.state import MagicState
    from sidequest.magic.models import WorldMagicConfig, WorldKnowledge

    cfg = WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    )
    state = MagicState.from_config(cfg)
    state.learn_spell("rux", "magic_missile")
    state.learn_spell("rux", "sleep")
    assert state.known_spells["rux"] == ["magic_missile", "sleep"]


def test_magic_state_prepare_spells_replaces_prior_preparation():
    from sidequest.magic.state import MagicState
    from sidequest.magic.models import WorldMagicConfig, WorldKnowledge

    cfg = WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    )
    state = MagicState.from_config(cfg)
    state.learn_spell("rux", "magic_missile")
    state.learn_spell("rux", "sleep")
    state.prepare_spells("rux", {1: ["magic_missile"]})
    assert state.prepared_spells["rux"] == {1: ["magic_missile"]}
    state.prepare_spells("rux", {1: ["sleep"]})
    assert state.prepared_spells["rux"] == {1: ["sleep"]}
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_state.py::test_magic_state_learned_collections_default_empty -v`

Expected: FAIL — `AttributeError: 'MagicState' object has no attribute 'known_spells'`.

- [ ] **Step 3: Implement**

Edit `sidequest/magic/state.py` — add to `MagicState` class:

```python
    # learned_v1 collections — per-actor known and prepared spell lists.
    # Slots themselves ride the existing LedgerBar registry (one bar per
    # spell level: slots_l1, slots_l2, ...). These two collections carry
    # the list-shaped state that doesn't fit a numeric bar.
    known_spells: dict[str, list[str]] = Field(default_factory=dict)
    prepared_spells: dict[str, dict[int, list[str]]] = Field(default_factory=dict)

    def learn_spell(self, actor_id: str, spell_id: str) -> None:
        """Append spell_id to actor's known list (idempotent)."""
        self.known_spells.setdefault(actor_id, [])
        if spell_id not in self.known_spells[actor_id]:
            self.known_spells[actor_id].append(spell_id)

    def prepare_spells(self, actor_id: str, prep: dict[int, list[str]]) -> None:
        """Replace actor's prepared spell list. Caller validates slot budget."""
        self.prepared_spells[actor_id] = prep
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_state.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/state.py tests/magic/test_state.py
git commit -m "feat(magic): MagicState adds learned_v1 known/prepared spell collections"
```

---

## Phase 3 — Spell catalog loader (server repo)

### Task 3.1: SpellCatalog model + loader

**Files:**
- Create: `sidequest-server/sidequest/magic/spell_catalog.py`
- Create: `sidequest-server/tests/magic/test_spell_catalog.py`
- Create: `sidequest-server/tests/magic/fixtures/cc_arcane_l1.yaml` (3-spell minimal fixture)

- [ ] **Step 1: Write the failing test**

Create `tests/magic/test_spell_catalog.py`:

```python
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "cc_arcane_l1.yaml"


def test_spell_catalog_loads_three_spell_fixture():
    from sidequest.magic.spell_catalog import load_spell_catalog

    cat = load_spell_catalog(FIXTURE)
    assert cat.tradition == "arcane"
    assert cat.level == 1
    assert len(cat.spells) == 3
    spell_ids = {s.id for s in cat.spells}
    assert spell_ids == {"magic_missile", "sleep", "charm_person"}


def test_spell_catalog_lookup_by_id():
    from sidequest.magic.spell_catalog import load_spell_catalog

    cat = load_spell_catalog(FIXTURE)
    s = cat.get("magic_missile")
    assert s.name == "Magic Missile"
    assert s.save.stat is None
    assert s.range == "near"


def test_spell_catalog_lookup_missing_raises():
    from sidequest.magic.spell_catalog import load_spell_catalog

    cat = load_spell_catalog(FIXTURE)
    with pytest.raises(KeyError, match="firewing"):
        cat.get("firewing")
```

Create the fixture `tests/magic/fixtures/cc_arcane_l1.yaml`:

```yaml
version: "0.1.0"
genre: caverns_and_claudes
tradition: arcane
level: 1

spells:
  - id: magic_missile
    name: "Magic Missile"
    level: 1
    tradition: arcane
    range: near
    target: single
    duration: instant
    save: { stat: null, effect: none }
    effect_template: "Force dart, 1 momentum damage, auto-hit"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: "A bolt of glowing force."
    hard_limits_check: []
    domain: physical
    otel_attrs: [cast_intent]

  - id: sleep
    name: "Sleep"
    level: 1
    tradition: arcane
    range: near
    target: area
    duration: turns:1d4+1
    save: { stat: WIS, effect: negates }
    effect_template: "Up to 4d4 HD; save WIS or unconscious"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: "A slow, kind weight."
    hard_limits_check: []
    domain: psychic
    otel_attrs: [cast_intent]

  - id: charm_person
    name: "Charm Person"
    level: 1
    tradition: arcane
    range: near
    target: single
    duration: until_rest
    save: { stat: WIS, effect: negates }
    effect_template: "Single humanoid; save WIS or trusted friend"
    components: { verbal: true, somatic: true, material: null }
    backlash: null
    narrator_register: "Their eyes settle."
    hard_limits_check: []
    domain: psychic
    otel_attrs: [cast_intent]
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_spell_catalog.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.magic.spell_catalog'`.

- [ ] **Step 3: Implement**

Create `sidequest/magic/spell_catalog.py`:

```python
"""Spell catalog loader — reads spells/<tradition>_l<n>.yaml from a genre pack.

Each catalog file is a list of spells at one tradition+level. Plugins consume
the catalog to validate cast workings and to render spell metadata in the
narrator context block.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class SpellSave(BaseModel):
    model_config = {"extra": "forbid"}
    stat: str | None
    effect: Literal["none", "negates", "halves"] | str  # str allows partial:<text>


class SpellComponents(BaseModel):
    model_config = {"extra": "forbid"}
    verbal: bool = False
    somatic: bool = False
    material: str | None = None


class SpellReverse(BaseModel):
    """Cleric reversed-spell variant. Mage spells leave this None."""

    model_config = {"extra": "forbid"}
    id: str
    effect_template: str
    narrator_register: str
    domain: str


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
    effect_template: str
    components: SpellComponents
    backlash: str | None
    narrator_register: str
    hard_limits_check: list[str] = Field(default_factory=list)
    domain: str
    otel_attrs: list[str] = Field(default_factory=list)
    reverse: SpellReverse | None = None


class SpellCatalog(BaseModel):
    model_config = {"extra": "forbid"}

    version: str
    genre: str
    tradition: Literal["arcane", "divine"]
    level: int
    spells: list[Spell]

    def get(self, spell_id: str) -> Spell:
        for s in self.spells:
            if s.id == spell_id:
                return s
        raise KeyError(f"spell {spell_id!r} not in catalog (have: {[s.id for s in self.spells]})")


def load_spell_catalog(path: Path) -> SpellCatalog:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SpellCatalog.model_validate(raw)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_spell_catalog.py -v`

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/spell_catalog.py tests/magic/test_spell_catalog.py tests/magic/fixtures/cc_arcane_l1.yaml
git commit -m "feat(magic): spell_catalog loader — Spell/SpellCatalog pydantic models + load function"
```

### Task 3.2: Wire catalog discovery into magic_loader

**Files:**
- Modify: `sidequest-server/sidequest/genre/magic_loader.py`
- Test: `sidequest-server/tests/magic/test_loader.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_loader.py`:

```python
def test_load_world_magic_returns_spell_catalogs_when_present(tmp_path):
    """When a genre has spells/ dir, load_world_magic returns the catalogs."""
    from sidequest.genre.magic_loader import load_world_magic

    # Arrange — minimal genre + world magic.yaml plus spells/arcane_l1.yaml
    genre_dir = tmp_path / "test_genre"
    genre_dir.mkdir()
    spells_dir = genre_dir / "spells"
    spells_dir.mkdir()
    (genre_dir / "magic.yaml").write_text(
        "genre: test_genre\n"
        "allowed_sources: [learned]\n"
        "permitted_plugins: [learned_v1]\n"
        "intensity: { default: 0.3 }\n"
        "world_knowledge_default: { primary: folkloric }\n"
        "hard_limits: []\n"
        "cost_types: [slot]\n"
        "narrator_register: 'test'\n"
    )
    world_dir = genre_dir / "worlds" / "test_world"
    world_dir.mkdir(parents=True)
    (world_dir / "magic.yaml").write_text(
        "world: test_world\n"
        "genre: test_genre\n"
        "intensity: 0.3\n"
        "active_plugins: [learned_v1]\n"
        "world_knowledge: { primary: folkloric }\n"
        "visibility: { primary: feared }\n"
        "can_build_caster: true\n"
        "can_build_item_user: true\n"
        "cost_types_active: [slot]\n"
        "ledger_bars: []\n"
        "narrator_register: 'test'\n"
    )
    # 1-spell fixture
    (spells_dir / "arcane_l1.yaml").write_text(
        'version: "0.1.0"\n'
        "genre: test_genre\ntradition: arcane\nlevel: 1\n"
        "spells:\n"
        "  - id: magic_missile\n"
        '    name: "Magic Missile"\n'
        "    level: 1\n    tradition: arcane\n"
        "    range: near\n    target: single\n"
        "    duration: instant\n"
        "    save: { stat: null, effect: none }\n"
        "    effect_template: 'force dart'\n"
        "    components: { verbal: true, somatic: true, material: null }\n"
        "    backlash: null\n"
        "    narrator_register: 'glow'\n"
        "    hard_limits_check: []\n"
        "    domain: physical\n"
        "    otel_attrs: []\n"
    )

    # Act
    config = load_world_magic(
        genre_yaml=genre_dir / "magic.yaml",
        world_yaml=world_dir / "magic.yaml",
    )

    # Assert
    assert config.spell_catalogs is not None
    assert "arcane_l1" in config.spell_catalogs
    assert config.spell_catalogs["arcane_l1"].spells[0].id == "magic_missile"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_loader.py::test_load_world_magic_returns_spell_catalogs_when_present -v`

Expected: FAIL — `WorldMagicConfig has no attribute 'spell_catalogs'`.

- [ ] **Step 3: Implement**

In `sidequest/magic/models.py:243` (`WorldMagicConfig`), add the field:

```python
    spell_catalogs: dict[str, SpellCatalog] | None = None
```

(with `from sidequest.magic.spell_catalog import SpellCatalog` at top of file).

In `sidequest/genre/magic_loader.py`, in `load_world_magic`, after building `config`:

```python
    spells_dir = genre_yaml.parent / "spells"
    if spells_dir.is_dir():
        catalogs: dict[str, SpellCatalog] = {}
        for catalog_path in sorted(spells_dir.glob("*.yaml")):
            cat = load_spell_catalog(catalog_path)
            key = catalog_path.stem  # e.g. "arcane_l1"
            catalogs[key] = cat
        config = config.model_copy(update={"spell_catalogs": catalogs})
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_loader.py -v`

Expected: PASS (existing tests + the new one).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/models.py sidequest/genre/magic_loader.py tests/magic/test_loader.py
git commit -m "feat(magic): magic_loader discovers and loads spells/ catalogs"
```

---

## Phase 4 — `learned_v1` plugin (server repo)

### Task 4.1: Create learned_v1.yaml descriptor

**Files:**
- Create: `sidequest-server/sidequest/magic/plugins/learned_v1.yaml`

- [ ] **Step 1: Author the descriptor**

```yaml
plugin_id: learned_v1
source: learned
delivery_mechanisms:
  - studied
  - granted
ledger_bar_templates:
  divine_favor:
    id: divine_favor
    scope: character
    direction: bidirectional
    range: [-1.0, 1.0]
    threshold_high: 0.7
    threshold_low: -0.7
    consequence_on_high_cross: "narrator-discretion: cleric receives one free reliquary effect within the session"
    consequence_on_low_cross: "narrator-discretion: cleric cannot Turn until favor is restored"
    starts_at_chargen: 0.0
narrator_register: |
  Magic the caster carries. Mages prepare from a spellbook they keep close
  but rarely show; clerics receive what is granted, and forget when it
  passes. The casting is a budgeted thing — slots filled at safe rest,
  expended one at a time, gone until the next quiet hour.
required_span_attrs:
  - spell_id
  - slot_level
optional_span_attrs:
  - save_target_actor
  - save_outcome
```

- [ ] **Step 2: Validate it parses against the existing Plugin model**

Run: `cd sidequest-server && uv run python -c "
import yaml
from pathlib import Path
from sidequest.magic.models import Plugin
p = Path('sidequest/magic/plugins/learned_v1.yaml')
descriptor = Plugin.model_validate(yaml.safe_load(p.read_text()))
print(descriptor.plugin_id, descriptor.delivery_mechanisms)
"`

Expected: `learned_v1 ['studied', 'granted']`

- [ ] **Step 3: Commit**

```bash
cd sidequest-server
git add sidequest/magic/plugins/learned_v1.yaml
git commit -m "feat(magic): learned_v1.yaml descriptor — studied/granted, divine_favor template"
```

### Task 4.2: Create learned_v1.py plugin class + register

**Files:**
- Create: `sidequest-server/sidequest/magic/plugins/learned_v1.py`
- Modify: `sidequest-server/sidequest/magic/plugins/__init__.py`
- Create: `sidequest-server/tests/magic/test_plugin_learned_v1.py`

- [ ] **Step 1: Write the failing test**

Create `tests/magic/test_plugin_learned_v1.py`:

```python
def test_learned_v1_registered_in_magic_plugins():
    from sidequest.magic.plugin import MAGIC_PLUGINS

    assert "learned_v1" in MAGIC_PLUGINS
    assert MAGIC_PLUGINS["learned_v1"].plugin_id == "learned_v1"


def test_learned_v1_validate_flags_missing_spell_id():
    from sidequest.magic.models import MagicWorking, WorldKnowledge, WorldMagicConfig
    from sidequest.magic.plugin import MAGIC_PLUGINS

    plugin = MAGIC_PLUGINS["learned_v1"]
    cfg = WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    )
    w = MagicWorking(
        plugin="learned_v1",
        mechanism="studied",
        actor="rux",
        domain="physical",
        narrator_basis="missing spell_id",
        # spell_id intentionally omitted
        slot_level=1,
        costs={"slots_l1": 1.0},
    )

    flags = plugin.validate_working(w, cfg)
    assert any(f.reason == "missing_required_attr_spell_id" for f in flags)


def test_learned_v1_validate_clean_when_complete():
    from sidequest.magic.models import MagicWorking, WorldKnowledge, WorldMagicConfig
    from sidequest.magic.plugin import MAGIC_PLUGINS

    plugin = MAGIC_PLUGINS["learned_v1"]
    cfg = WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    )
    w = MagicWorking(
        plugin="learned_v1",
        mechanism="studied",
        actor="rux",
        domain="physical",
        narrator_basis="ok",
        spell_id="magic_missile",
        slot_level=1,
        costs={"slots_l1": 1.0},
    )

    flags = plugin.validate_working(w, cfg)
    assert flags == []


def test_learned_v1_validate_rejects_item_lane():
    """learned_v1 firing with discovery is item_legacy_v1 territory — lane violation."""
    from sidequest.magic.models import MagicWorking, WorldKnowledge, WorldMagicConfig
    from sidequest.magic.plugin import MAGIC_PLUGINS

    plugin = MAGIC_PLUGINS["learned_v1"]
    cfg = WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    )
    w = MagicWorking(
        plugin="learned_v1",
        mechanism="discovery",  # wrong lane
        actor="rux",
        domain="physical",
        narrator_basis="bad mechanism",
        spell_id="magic_missile",
        slot_level=1,
        costs={"slots_l1": 1.0},
    )

    flags = plugin.validate_working(w, cfg)
    assert any(f.reason == "learned_via_item_mechanism_is_lane_violation" for f in flags)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_plugin_learned_v1.py -v`

Expected: FAIL — `KeyError: 'learned_v1'` (plugin not registered).

- [ ] **Step 3: Implement the plugin**

Create `sidequest/magic/plugins/learned_v1.py`:

```python
"""learned_v1 — prepared-spell magic for caster classes (Mage, Cleric).

Loose-Vancian: known list per actor, daily preparation up to per-level
slots, cast = expended until rest. Slot bookkeeping rides the standard
LedgerBar registry (slots_l1, slots_l2, ...). Known/prepared lists ride
MagicState.known_spells / MagicState.prepared_spells.

Importing this module is the public API: it mutates MAGIC_PLUGINS by
side effect.
"""

from __future__ import annotations

from pathlib import Path

import yaml

__all__: list[str] = []

from sidequest.magic.models import (
    Flag,
    FlagSeverity,
    MagicWorking,
    Plugin,
    WorldMagicConfig,
)
from sidequest.magic.plugin import MAGIC_PLUGINS

_YAML_PATH = Path(__file__).with_suffix(".yaml")
descriptor: Plugin = Plugin.model_validate(yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8")))

# Mechanisms that belong to other plugins. learned_v1 firing with these
# is a lane violation (mirror of item_legacy_v1's `native` rejection).
_ITEM_LANE_MECHANISMS: set[str] = {
    "discovery", "mccoy", "relational", "faction",
}
_INNATE_LANE_MECHANISMS: set[str] = {"native", "condition"}


class LearnedV1Plugin:
    plugin_id = "learned_v1"

    def required_attrs(self) -> set[str]:
        return set(descriptor.required_span_attrs)

    def validate_working(self, working: MagicWorking, config: WorldMagicConfig) -> list[Flag]:
        flags: list[Flag] = []

        if working.spell_id is None:
            flags.append(
                Flag(
                    severity=FlagSeverity.YELLOW,
                    reason="missing_required_attr_spell_id",
                    detail="learned_v1 requires spell_id",
                )
            )
        if working.slot_level is None:
            flags.append(
                Flag(
                    severity=FlagSeverity.YELLOW,
                    reason="missing_required_attr_slot_level",
                    detail="learned_v1 requires slot_level",
                )
            )
        elif working.slot_level < 1:
            flags.append(
                Flag(
                    severity=FlagSeverity.RED,
                    reason="slot_level_below_one",
                    detail=f"slot_level must be >= 1, got {working.slot_level}",
                )
            )

        if working.mechanism in _ITEM_LANE_MECHANISMS:
            flags.append(
                Flag(
                    severity=FlagSeverity.RED,
                    reason="learned_via_item_mechanism_is_lane_violation",
                    detail=(
                        f"mechanism {working.mechanism!r} is item_legacy_v1 territory; "
                        "learned_v1 must use studied or granted"
                    ),
                )
            )
        if working.mechanism in _INNATE_LANE_MECHANISMS:
            flags.append(
                Flag(
                    severity=FlagSeverity.RED,
                    reason="learned_via_innate_mechanism_is_lane_violation",
                    detail=(
                        f"mechanism {working.mechanism!r} is innate_v1 territory; "
                        "learned_v1 must use studied or granted"
                    ),
                )
            )

        return flags


MAGIC_PLUGINS["learned_v1"] = LearnedV1Plugin()
```

Edit `sidequest/magic/plugins/__init__.py`:

```python
from sidequest.magic.plugins.innate_v1 import *  # noqa: F401, F403
from sidequest.magic.plugins.item_legacy_v1 import *  # noqa: F401, F403
from sidequest.magic.plugins.learned_v1 import *  # noqa: F401, F403
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_plugin_learned_v1.py tests/magic/test_plugin_registry.py -v`

Expected: PASS (4 new + the registry-completeness test still passes).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/plugins/learned_v1.py sidequest/magic/plugins/__init__.py tests/magic/test_plugin_learned_v1.py
git commit -m "feat(magic): learned_v1 plugin — validator, lane respect, registration"
```

---

## Phase 5 — Plugin operations (server repo)

Free functions on MagicState for prepare/cast/rest/turn_undead. These are the verbs the orchestrator calls when the narrator emits a learned_v1 working or the player declares an action.

### Task 5.1: prepare()

**Files:**
- Create: `sidequest-server/sidequest/magic/learned_ops.py`
- Create: `sidequest-server/tests/magic/test_learned_ops.py`

- [ ] **Step 1: Write the failing test**

Create `tests/magic/test_learned_ops.py`:

```python
import pytest


def _config_with_slots():
    """Build a WorldMagicConfig with per-actor slots_l1 bar template."""
    from sidequest.magic.models import LedgerBarSpec, WorldKnowledge, WorldMagicConfig

    return WorldMagicConfig(
        world_slug="test",
        allowed_sources=["learned"],
        active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[
            LedgerBarSpec(
                id="slots_l1",
                scope="character",
                direction="down",
                range=(0.0, 4.0),
                threshold_low=0.0,
                consequence_on_low_cross="out of L1 slots",
                starts_at_chargen=2.0,
            ),
        ],
        hard_limits=[],
    )


def test_prepare_populates_prepared_spells():
    from sidequest.magic.learned_ops import prepare
    from sidequest.magic.state import MagicState

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    state.learn_spell("rux", "sleep")

    prepare(state, actor="rux", prep={1: ["magic_missile", "sleep"]})

    assert state.prepared_spells["rux"] == {1: ["magic_missile", "sleep"]}


def test_prepare_rejects_unknown_spell():
    from sidequest.magic.learned_ops import prepare
    from sidequest.magic.state import MagicState

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")

    with pytest.raises(ValueError, match="not in known_spells"):
        prepare(state, actor="rux", prep={1: ["fireball"]})


def test_prepare_rejects_over_slot_budget():
    from sidequest.magic.learned_ops import prepare
    from sidequest.magic.state import MagicState

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    state.learn_spell("rux", "sleep")
    state.learn_spell("rux", "charm_person")

    # slots_l1 starts at 2; preparing 3 spells should fail.
    with pytest.raises(ValueError, match="exceeds slot budget"):
        prepare(state, actor="rux", prep={1: ["magic_missile", "sleep", "charm_person"]})
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.magic.learned_ops'`.

- [ ] **Step 3: Implement**

Create `sidequest/magic/learned_ops.py`:

```python
"""learned_v1 plugin operations — prepare, cast, rest, turn_undead.

Free functions on MagicState. The orchestrator calls prepare() when the
player declares "I prepare spells" at a safe site; cast() runs as a
narration_apply mutation when the narrator emits a learned_v1 working;
rest() restores slot bars and clears prepared_spells. turn_undead() is
the Cleric class-special; not a spell, no slot consumed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sidequest.magic.state import BarKey, MagicState

_log = logging.getLogger(__name__)


@dataclass
class PrepareResult:
    actor: str
    prepared: dict[int, list[str]]
    slots_used_per_level: dict[int, int]


def _slot_bar_key(actor: str, level: int) -> BarKey:
    return BarKey(scope="character", owner_id=actor, bar_id=f"slots_l{level}")


def prepare(state: MagicState, *, actor: str, prep: dict[int, list[str]]) -> PrepareResult:
    """Replace actor's prepared list. Validates: known + within slot budget.

    Raises ValueError on unknown spell or over-budget. On success, mutates
    state.prepared_spells[actor] to the new prep dict.
    """
    known = set(state.known_spells.get(actor, []))
    for level, spell_ids in prep.items():
        for sid in spell_ids:
            if sid not in known:
                raise ValueError(
                    f"spell {sid!r} not in known_spells for actor {actor!r} "
                    f"(known: {sorted(known)})"
                )
        # Slot budget check: bar.spec.range[1] is the per-rest max for this level.
        try:
            bar = state.get_bar(_slot_bar_key(actor, level))
        except KeyError as e:
            raise ValueError(
                f"actor {actor!r} has no slots_l{level} bar; class does not grant L{level} slots"
            ) from e
        max_slots = int(bar.spec.range[1])
        if len(spell_ids) > max_slots:
            raise ValueError(
                f"prep level {level}: {len(spell_ids)} spells exceeds slot budget {max_slots}"
            )

    state.prepared_spells[actor] = prep
    # Reset slot bars to max — preparation refreshes the budget.
    for level in prep:
        bar = state.get_bar(_slot_bar_key(actor, level))
        state.set_bar_value(_slot_bar_key(actor, level), bar.spec.range[1])

    return PrepareResult(
        actor=actor,
        prepared=prep,
        slots_used_per_level={lvl: len(ids) for lvl, ids in prep.items()},
    )
```

(`cast`, `rest`, and `turn_undead` come in tasks 5.2, 5.3, 5.4.)

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py -v`

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/learned_ops.py tests/magic/test_learned_ops.py
git commit -m "feat(magic): learned_ops.prepare — known/budget validation, slot bar refresh"
```

### Task 5.2: cast()

**Files:**
- Modify: `sidequest-server/sidequest/magic/learned_ops.py`
- Modify: `sidequest-server/tests/magic/test_learned_ops.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_learned_ops.py`:

```python
def test_cast_decrements_slot_and_records_working():
    from sidequest.magic.learned_ops import cast, prepare
    from sidequest.magic.models import MagicWorking
    from sidequest.magic.state import BarKey, MagicState

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    prepare(state, actor="rux", prep={1: ["magic_missile"]})

    working = MagicWorking(
        plugin="learned_v1", mechanism="studied", actor="rux",
        domain="physical", narrator_basis="cast magic missile",
        spell_id="magic_missile", slot_level=1, costs={"slots_l1": 1.0},
    )
    result = cast(state, working=working)

    bar = state.get_bar(BarKey(scope="character", owner_id="rux", bar_id="slots_l1"))
    assert bar.value == 1.0  # was 2, now 1
    assert state.working_log[-1].spell_id == "magic_missile"
    assert result.slot_consumed is True


def test_cast_rejects_unprepared_spell():
    from sidequest.magic.learned_ops import cast
    from sidequest.magic.models import MagicWorking
    from sidequest.magic.state import MagicState
    import pytest

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    # Did NOT prepare anything.

    working = MagicWorking(
        plugin="learned_v1", mechanism="studied", actor="rux",
        domain="physical", narrator_basis="cast magic missile",
        spell_id="magic_missile", slot_level=1, costs={"slots_l1": 1.0},
    )
    with pytest.raises(ValueError, match="not prepared"):
        cast(state, working=working)


def test_cast_rejects_when_slot_empty():
    from sidequest.magic.learned_ops import cast, prepare
    from sidequest.magic.models import MagicWorking
    from sidequest.magic.state import MagicState
    import pytest

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    prepare(state, actor="rux", prep={1: ["magic_missile"]})

    # Drain the slot:
    working = MagicWorking(
        plugin="learned_v1", mechanism="studied", actor="rux",
        domain="physical", narrator_basis="cast 1",
        spell_id="magic_missile", slot_level=1, costs={"slots_l1": 1.0},
    )
    cast(state, working=working)
    cast(state, working=working)  # 2nd cast: slot bar 2 -> 1 -> 0

    with pytest.raises(ValueError, match="no slots remaining"):
        cast(state, working=working)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py::test_cast_decrements_slot_and_records_working -v`

Expected: FAIL — `cast` not defined.

- [ ] **Step 3: Implement — add to `sidequest/magic/learned_ops.py`**

```python
@dataclass
class CastResult:
    actor: str
    spell_id: str
    slot_consumed: bool


def cast(state: MagicState, *, working: "MagicWorking") -> CastResult:
    """Resolve a learned_v1 cast working. Validates prep + slot, applies costs.

    Caller (narration_apply) is responsible for save-vs-spells resolution
    (separate concern; it goes through C&C's opposed_check). cast() handles
    the magic-state mutations only.
    """
    actor = working.actor
    if working.spell_id is None or working.slot_level is None:
        raise ValueError("cast requires spell_id and slot_level")
    spell_id = working.spell_id
    level = working.slot_level

    prepared_at_level = state.prepared_spells.get(actor, {}).get(level, [])
    if spell_id not in prepared_at_level:
        raise ValueError(
            f"spell {spell_id!r} not prepared at level {level} for actor {actor!r} "
            f"(prepared: {prepared_at_level})"
        )

    bar = state.get_bar(_slot_bar_key(actor, level))
    if bar.value <= 0:
        raise ValueError(
            f"actor {actor!r} has no slots remaining at level {level}"
        )

    # apply_working mutates the bar via cost routing:
    state.apply_working(working)

    return CastResult(actor=actor, spell_id=spell_id, slot_consumed=True)
```

Add `from sidequest.magic.models import MagicWorking` to module imports if not already present.

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py -v`

Expected: PASS (6 tests total).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/learned_ops.py tests/magic/test_learned_ops.py
git commit -m "feat(magic): learned_ops.cast — prep+slot validation, working_log via apply_working"
```

### Task 5.3: rest()

**Files:**
- Modify: `sidequest-server/sidequest/magic/learned_ops.py`
- Modify: `sidequest-server/tests/magic/test_learned_ops.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_learned_ops.py`:

```python
def test_rest_clears_prepared_and_resets_slots():
    from sidequest.magic.learned_ops import cast, prepare, rest
    from sidequest.magic.models import MagicWorking
    from sidequest.magic.state import BarKey, MagicState

    state = MagicState.from_config(_config_with_slots())
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    prepare(state, actor="rux", prep={1: ["magic_missile"]})

    working = MagicWorking(
        plugin="learned_v1", mechanism="studied", actor="rux",
        domain="physical", narrator_basis="cast",
        spell_id="magic_missile", slot_level=1, costs={"slots_l1": 1.0},
    )
    cast(state, working=working)

    rest(state, actor="rux")

    assert state.prepared_spells["rux"] == {}
    bar = state.get_bar(BarKey(scope="character", owner_id="rux", bar_id="slots_l1"))
    assert bar.value == 2.0  # back to max
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py::test_rest_clears_prepared_and_resets_slots -v`

Expected: FAIL — `rest` not defined.

- [ ] **Step 3: Implement — add to `sidequest/magic/learned_ops.py`**

```python
@dataclass
class RestResult:
    actor: str
    slots_restored: dict[int, float]


def rest(state: MagicState, *, actor: str) -> RestResult:
    """Reset all per-level slot bars to max; clear prepared_spells."""
    restored: dict[int, float] = {}
    # Find slot bars for this actor and reset.
    for serialized in list(state.ledger.keys()):
        if not serialized.startswith(f"character|{actor}|slots_l"):
            continue
        bar = state.ledger[serialized]
        max_value = bar.spec.range[1]
        bar.value = max_value
        # serialized is "character|<actor>|slots_l<N>"
        level = int(serialized.rsplit("slots_l", 1)[1])
        restored[level] = max_value
    state.prepared_spells[actor] = {}
    return RestResult(actor=actor, slots_restored=restored)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py -v`

Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/learned_ops.py tests/magic/test_learned_ops.py
git commit -m "feat(magic): learned_ops.rest — restore slot bars, clear prepared_spells"
```

### Task 5.4: turn_undead() (Cleric class-special)

**Files:**
- Modify: `sidequest-server/sidequest/magic/learned_ops.py`
- Modify: `sidequest-server/tests/magic/test_learned_ops.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_learned_ops.py`:

```python
def _config_with_slots_and_divine_favor():
    from sidequest.magic.models import LedgerBarSpec, WorldKnowledge, WorldMagicConfig
    return WorldMagicConfig(
        world_slug="test",
        allowed_sources=["learned"],
        active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[
            LedgerBarSpec(
                id="slots_l1", scope="character", direction="down",
                range=(0.0, 2.0), threshold_low=0.0,
                consequence_on_low_cross="out", starts_at_chargen=2.0,
            ),
            LedgerBarSpec(
                id="divine_favor", scope="character", direction="bidirectional",
                range=(-1.0, 1.0), threshold_high=0.7, threshold_low=-0.7,
                consequence_on_high_cross="boon", consequence_on_low_cross="dry",
                starts_at_chargen=0.0,
            ),
        ],
        hard_limits=[],
    )


def test_turn_undead_blocked_when_divine_favor_low():
    from sidequest.magic.learned_ops import turn_undead
    from sidequest.magic.state import BarKey, MagicState
    import pytest

    state = MagicState.from_config(_config_with_slots_and_divine_favor())
    state.add_character("vail")
    state.set_bar_value(
        BarKey(scope="character", owner_id="vail", bar_id="divine_favor"), -0.8,
    )
    with pytest.raises(ValueError, match="divine_favor below threshold"):
        turn_undead(state, actor="vail", undead_hd=2)


def test_turn_undead_returns_outcome_when_favor_clean():
    from sidequest.magic.learned_ops import turn_undead
    from sidequest.magic.state import MagicState

    state = MagicState.from_config(_config_with_slots_and_divine_favor())
    state.add_character("vail")
    result = turn_undead(state, actor="vail", undead_hd=2)
    # outcome is a structured request the orchestrator resolves via opposed_check;
    # turn_undead itself does not roll dice.
    assert result.actor == "vail"
    assert result.undead_hd == 2
    assert result.divine_favor == 0.0
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py::test_turn_undead_blocked_when_divine_favor_low -v`

Expected: FAIL — `turn_undead` not defined.

- [ ] **Step 3: Implement**

Add to `sidequest/magic/learned_ops.py`:

```python
@dataclass
class TurnUndeadResult:
    actor: str
    undead_hd: int
    divine_favor: float


def turn_undead(state: MagicState, *, actor: str, undead_hd: int) -> TurnUndeadResult:
    """Cleric class-special. Validates divine_favor; returns structured request.

    The opposed_check itself (favor*level vs HD) is rolled by the C&C check
    resolver — turn_undead surfaces the structured request and the favor
    value at request time. Threshold-low cross blocks the action with a
    descriptive ValueError so the GM panel can render the block reason.
    """
    favor_key = BarKey(scope="character", owner_id=actor, bar_id="divine_favor")
    try:
        bar = state.get_bar(favor_key)
    except KeyError as e:
        raise ValueError(
            f"actor {actor!r} has no divine_favor bar; not a Cleric class"
        ) from e
    if bar.spec.threshold_low is not None and bar.value <= bar.spec.threshold_low:
        raise ValueError(
            f"divine_favor below threshold ({bar.value:.2f} <= {bar.spec.threshold_low:.2f}); "
            f"cleric must restore favor at the Confessional/Workhouse/Masquerade before turning"
        )
    return TurnUndeadResult(actor=actor, undead_hd=undead_hd, divine_favor=bar.value)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_learned_ops.py -v`

Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/learned_ops.py tests/magic/test_learned_ops.py
git commit -m "feat(magic): learned_ops.turn_undead — divine_favor gate, structured request"
```

---

## Phase 6 — Init wiring (server repo)

Hook the per-class learned_v1 setup into `init_magic_state_for_session`. Already-extant flow: chargen → `init_magic_state_for_session` → loads world+genre magic.yaml → constructs `MagicState`. Extension: when the character's class has `magic_access: learned_v1`, also instantiate per-level slot bars, seed `known_spells` (chargen picks), and skip `prepared_spells` (player prepares explicitly later).

### Task 6.1: Per-class learned_v1 init

**Files:**
- Modify: `sidequest-server/sidequest/server/magic_init.py`
- Modify: `sidequest-server/tests/magic/test_wiring.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_wiring.py` (or create one if absent):

```python
def test_magic_init_seeds_learned_v1_for_mage_class(tmp_path):
    """Mage chargen → init wires per-level slot bars + chosen known spells."""
    # This test exercises the init shape. Full chargen requires a heavier
    # fixture; we assemble enough to run init_magic_state_for_session.
    pytest.skip("integration test — see test_e2e_learned_v1.py for end-to-end")
```

(The full E2E lands in Task 11.1; this task stubs the wiring point and the seed logic.)

Then, write a focused unit test on the helper extracted in step 3:

```python
def test_seed_learned_v1_state_instantiates_slot_bars_per_level():
    from sidequest.genre.models.character import ClassDef, ClassMagicConfig
    from sidequest.magic.models import LedgerBarSpec, WorldKnowledge, WorldMagicConfig
    from sidequest.magic.state import BarKey, MagicState
    from sidequest.server.magic_init import seed_learned_v1_state

    class_def = ClassDef(
        id="mage", display_name="Mage", rpg_role="control",
        jungian_default="magician", prime_requisite="INT",
        minimum_score=9, kit_table="mage_kit",
        magic_access="learned_v1",
        magic_config=ClassMagicConfig(
            tradition="arcane",
            slots_by_class_level={"1": {"1": 1}, "3": {"1": 2, "2": 1}},
            starting_known_spells=2,
            save_dc_stat="INT",
        ),
    )
    state = MagicState.from_config(WorldMagicConfig(
        world_slug="test", allowed_sources=["learned"], active_plugins=["learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[], hard_limits=[],
    ))
    state.add_character("rux")

    seed_learned_v1_state(
        state, actor="rux", class_def=class_def, class_level=1,
        chosen_known_spells=["magic_missile", "sleep"],
    )

    assert state.known_spells["rux"] == ["magic_missile", "sleep"]
    bar = state.get_bar(BarKey(scope="character", owner_id="rux", bar_id="slots_l1"))
    assert bar.value == 1.0
    assert bar.spec.range == (0.0, 1.0)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_wiring.py::test_seed_learned_v1_state_instantiates_slot_bars_per_level -v`

Expected: FAIL — `seed_learned_v1_state` not defined.

- [ ] **Step 3: Implement**

Add to `sidequest/server/magic_init.py`:

```python
def seed_learned_v1_state(
    state: MagicState,
    *,
    actor: str,
    class_def: ClassDef,
    class_level: int,
    chosen_known_spells: list[str],
) -> None:
    """Per-actor learned_v1 seed: known_spells + per-level slot bars.

    Called from init_magic_state_for_session for any class with
    magic_access == 'learned_v1'. Slot-table lookup uses string-keyed
    dicts (YAML 1.1/JSON-safe) and selects the highest entry <= class_level.
    """
    if class_def.magic_config is None:
        raise ValueError(f"class {class_def.id!r} declares learned_v1 but has no magic_config")

    for sid in chosen_known_spells:
        state.learn_spell(actor, sid)

    # Pick the slot row for this class_level: largest key <= class_level.
    slot_table = class_def.magic_config.slots_by_class_level
    eligible = sorted(int(k) for k in slot_table if int(k) <= class_level)
    if not eligible:
        return  # class_level too low; no slots yet (e.g. cleric L1 has no L1 slots in some tables)
    row = slot_table[str(eligible[-1])]

    for spell_level_str, max_slots in row.items():
        spell_level = int(spell_level_str)
        bar_id = f"slots_l{spell_level}"
        spec = LedgerBarSpec(
            id=bar_id, scope="character", direction="down",
            range=(0.0, float(max_slots)), threshold_low=0.0,
            consequence_on_low_cross=f"out of L{spell_level} slots until rest",
            starts_at_chargen=float(max_slots),
        )
        key = BarKey(scope="character", owner_id=actor, bar_id=bar_id)
        state.ledger[
            f"character|{actor}|{bar_id}"
        ] = LedgerBar(spec=spec, value=float(max_slots))
```

(Imports: add `ClassDef` from `sidequest.genre.models.character`, `LedgerBarSpec` from `sidequest.magic.models`, `BarKey, LedgerBar` from `sidequest.magic.state`.)

Then call it from `init_magic_state_for_session` after `state.add_character(actor)` when the actor's class has `magic_access == "learned_v1"`. The full integration is verified in the E2E test (Task 11.1).

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_wiring.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/server/magic_init.py tests/magic/test_wiring.py
git commit -m "feat(magic): magic_init seeds learned_v1 — known_spells + per-level slot bars"
```

---

## Phase 7 — Genre + world content amendments (content repo)

### Task 7.1: Amend `caverns_and_claudes/magic.yaml`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/magic.yaml`

- [ ] **Step 1: Replace `permitted_plugins`, `cost_types`, narrator_register**

Edit the file:

```yaml
# Replace line 27:
permitted_plugins: [item_legacy_v1, learned_v1]

# Replace line 57:
cost_types: [components, backlash, slot]

# Replace narrator_register (lines 59-65) with:
narrator_register: |
  Magic in C&C is two things, both at once. Magic is found — scrolls
  burn, potions drain, wands run out, cursed swords cost more than they
  pay. Magic is also carried — Mages prepare from notes they keep close,
  Clerics receive what is granted and forget when it passes. The wizards
  who made the items are gone, but the practice survived: Mages still
  learn, Clerics still serve. Both kinds of magic are budgeted; both
  kinds run out. Cursed items remain the genre's signature trap.
```

In the design-notes block (lines 67-105), update:

```yaml
# player_options:
#   can_build_caster: true                # Mage and Cleric ship as classes
#   can_build_item_user: true             # Delver acquires items in play
#   chargen_caster_classes: [mage, cleric]
#   can_acquire_in_play: true             # finding magic items is core gameplay
```

And:

```yaml
# manifestation:
#   modes: [item_channeled, learned]
```

- [ ] **Step 2: Validate**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/magic.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/magic.yaml
git commit -m "feat(c&c): magic.yaml allows learned_v1 — Mage/Cleric are real casters"
```

### Task 7.2: Amend `caverns_and_claudes/classes.yaml`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

- [ ] **Step 1: Update mage and cleric entries**

Edit the file. Replace the `mage` block:

```yaml
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
  magic_access: learned_v1
  magic_config:
    tradition: arcane
    # B/X Magic-User slot table (string-keyed for YAML+JSON round-trip):
    slots_by_class_level:
      "1":  { "1": 1 }
      "2":  { "1": 2 }
      "3":  { "1": 2, "2": 1 }
      "4":  { "1": 2, "2": 2 }
      "5":  { "1": 2, "2": 2, "3": 1 }
      "6":  { "1": 2, "2": 2, "3": 2 }
      "7":  { "1": 3, "2": 2, "3": 2, "4": 1 }
      "8":  { "1": 3, "2": 3, "3": 2, "4": 2 }
      "9":  { "1": 3, "2": 3, "3": 3, "4": 2, "5": 1 }
      "10": { "1": 3, "2": 3, "3": 3, "4": 3, "5": 2 }
      "11": { "1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1 }
      "12": { "1": 4, "2": 4, "3": 3, "4": 3, "5": 3, "6": 2 }
      "13": { "1": 4, "2": 4, "3": 4, "4": 3, "5": 3, "6": 2 }
      "14": { "1": 4, "2": 4, "3": 4, "4": 4, "5": 3, "6": 3 }
    starting_known_spells: 2
    save_dc_stat: INT
```

Replace the `cleric` block:

```yaml
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
  magic_access: learned_v1
  magic_config:
    tradition: divine
    # B/X Cleric slot table — note L1 cleric has NO spells per Moldvay
    # canon. Spells unlock at class level 2.
    slots_by_class_level:
      "1":  {}
      "2":  { "1": 1 }
      "3":  { "1": 2 }
      "4":  { "1": 2, "2": 1 }
      "5":  { "1": 2, "2": 2 }
      "6":  { "1": 2, "2": 2, "3": 1, "4": 1 }
      "7":  { "1": 2, "2": 2, "3": 2, "4": 1, "5": 1 }
      "8":  { "1": 3, "2": 3, "3": 2, "4": 2, "5": 1 }
      "9":  { "1": 3, "2": 3, "3": 3, "4": 2, "5": 2 }
      "10": { "1": 4, "2": 4, "3": 3, "4": 3, "5": 2 }
      "11": { "1": 4, "2": 4, "3": 4, "4": 3, "5": 3 }
      "12": { "1": 5, "2": 5, "3": 4, "4": 4, "5": 3 }
      "13": { "1": 5, "2": 5, "3": 5, "4": 4, "5": 4 }
      "14": { "1": 6, "2": 5, "3": 5, "4": 5, "5": 4 }
    starting_known_spells: 0   # cleric L1 has no spells; first known at L2
    save_dc_stat: WIS
    turn_undead: true
```

(`fighter` and `thief` entries unchanged — `magic_access: null`.)

- [ ] **Step 2: Validate**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/classes.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/classes.yaml
git commit -m "feat(c&c): mage + cleric magic_config — B/X slot tables, learned_v1 access"
```

### Task 7.3: Update rules.yaml deprecation comment

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml:3-7`

- [ ] **Step 1: Replace the comment block**

Lines 3-7 currently say:

```yaml
magic_level: none
# DRAFT (2026-04-27): the `magic_level` flag is being retired. It's misleading
# here — magic items are core gameplay; this pack's actual claim is "no caster
# classes" + `world_knowledge: folkloric`. See ./magic.yaml for the full
# napkin-shaped truth and docs/design/magic-taxonomy.md for the framework.
```

Replace with:

```yaml
magic_level: none
# DRAFT (2026-04-27, revised 2026-05-06): the `magic_level` flag is being
# retired. It was never load-bearing for caster classes — Mage and Cleric
# now ship as B/X classic classes (see ./classes.yaml) with `magic_access:
# learned_v1`. The truth lives in ./magic.yaml: `permitted_plugins:
# [item_legacy_v1, learned_v1]`, `intensity: 0.3`, `world_knowledge:
# folkloric`. See docs/design/magic-taxonomy.md for the framework.
```

- [ ] **Step 2: Validate**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/rules.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/rules.yaml
git commit -m "docs(c&c): rules.yaml deprecation comment reflects post-2026-05-06 magic doctrine"
```

### Task 7.4: Author `worlds/caverns_sunden/magic.yaml`

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml`

- [ ] **Step 1: Author the world magic file**

```yaml
# Caverns & Claudes — Hamlet of Sünden world magic config.
# Activates item_legacy_v1 (existing) and learned_v1 (new). Adds the
# Cleric-only divine_favor bar; slot bars are auto-instantiated per-actor
# at chargen by magic_init based on class.magic_config slot tables.
#
# Reference: docs/superpowers/specs/2026-05-06-magic-system-caverns-and-claudes-implementation-design.md

world: caverns_sunden
genre: caverns_and_claudes

intensity: 0.3

active_plugins:
  - item_legacy_v1
  - learned_v1

world_knowledge:
  primary: folkloric
  # The Three Towns know magic exists. The Wallwrights record which
  # delvers came back changed by what; the Confraternity has private
  # files on which cleric of which rite has been seen calling on
  # something. Nobody talks about it in joint session.

visibility:
  primary: feared

can_build_caster: true
can_build_item_user: true

cost_types_active: [components, backlash, slot]

ledger_bars:
  - id: divine_favor
    scope: character
    direction: bidirectional
    range: [-1.0, 1.0]
    threshold_high: 0.7
    threshold_low: -0.7
    consequence_on_high_cross: "narrator-discretion: cleric receives one free reliquary effect within the session"
    consequence_on_low_cross: "narrator-discretion: cleric cannot Turn until favor is restored at the Confessional / Workhouse / Masquerade"
    starts_at_chargen: 0.0

narrator_register: |
  Sünden has known magic for as long as it has known the three sins. The
  Wallwrights cut a name shallower for a delver who came back with the
  Words still in their head. The Confraternity does not name what Brother
  Hesh's lay-monastic discipline taught him, and Brother Hesh does not
  volunteer. The Lampwick keeps a back-room candle for the rare cleric
  passing through who needs one full night of unmolested rest and asks
  for it without elaboration. Magic is folkloric here. The folklore is
  also the truth.
```

- [ ] **Step 2: Validate**

Run: `cd sidequest-content && python -c "import yaml; yaml.safe_load(open('genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml').read())" && echo OK`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/worlds/caverns_sunden/magic.yaml
git commit -m "feat(c&c sünden): world magic.yaml — divine_favor bar, item+learned plugins"
```

---

## Phase 8 — Context block + OTEL (server repo)

### Task 8.1: Render `<learned-magic>` block in narrator context

**Files:**
- Modify: `sidequest-server/sidequest/magic/context_builder.py`
- Modify: `sidequest-server/tests/magic/test_context_builder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_context_builder.py`:

```python
def test_context_block_includes_learned_magic_for_caster_actor():
    from sidequest.magic.context_builder import build_magic_context_block
    from sidequest.magic.models import LedgerBarSpec, WorldKnowledge, WorldMagicConfig
    from sidequest.magic.state import MagicState

    cfg = WorldMagicConfig(
        world_slug="caverns_sunden",
        allowed_sources=["item_based", "learned"],
        active_plugins=["item_legacy_v1", "learned_v1"],
        world_knowledge=WorldKnowledge(primary="folkloric"),
        ledger_bars=[
            LedgerBarSpec(
                id="slots_l1", scope="character", direction="down",
                range=(0.0, 2.0), threshold_low=0.0,
                consequence_on_low_cross="out", starts_at_chargen=2.0,
            ),
        ],
        hard_limits=[],
    )
    state = MagicState.from_config(cfg)
    state.add_character("rux")
    state.learn_spell("rux", "magic_missile")
    state.learn_spell("rux", "sleep")
    state.prepared_spells["rux"] = {1: ["magic_missile"]}

    block = build_magic_context_block(magic_state=state, actor_id="rux")
    assert "<learned-magic" in block
    assert "magic_missile" in block
    assert "1/2" in block or "remaining" in block.lower()
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_context_builder.py::test_context_block_includes_learned_magic_for_caster_actor -v`

Expected: FAIL — block does not contain `<learned-magic>`.

- [ ] **Step 3: Implement**

Edit `sidequest/magic/context_builder.py`. After the existing per-actor character-bar rendering and before the world-scope block, append:

```python
    if actor_id is not None and actor_id in magic_state.known_spells:
        prepared = magic_state.prepared_spells.get(actor_id, {})
        known = magic_state.known_spells[actor_id]
        lines.append(f"<learned-magic actor=\"{actor_id}\">")
        lines.append(f"  <known>{', '.join(known)}</known>")
        if prepared:
            lines.append("  <prepared>")
            for level in sorted(prepared):
                lines.append(f"    <l{level}>{', '.join(prepared[level])}</l{level}>")
            lines.append("  </prepared>")
        # Slots remaining per level (read from bars):
        slots_lines: list[str] = []
        for spec in config.ledger_bars:
            if spec.id.startswith("slots_l"):
                level = int(spec.id.removeprefix("slots_l"))
                key = BarKey(scope="character", owner_id=actor_id, bar_id=spec.id)
                try:
                    bar = magic_state.get_bar(key)
                except KeyError:
                    continue
                slots_lines.append(f"    <l{level}>{int(bar.value)}/{int(spec.range[1])} remaining</l{level}>")
        # Also pick up dynamic slot bars (instantiated by seed_learned_v1_state, not in config).
        for serialized in magic_state.ledger:
            if not serialized.startswith(f"character|{actor_id}|slots_l"):
                continue
            level = int(serialized.rsplit("slots_l", 1)[1])
            if any(f"<l{level}>" in line for line in slots_lines):
                continue
            bar = magic_state.ledger[serialized]
            slots_lines.append(f"    <l{level}>{int(bar.value)}/{int(bar.spec.range[1])} remaining</l{level}>")
        if slots_lines:
            lines.append("  <slots>")
            lines.extend(slots_lines)
            lines.append("  </slots>")
        lines.append("</learned-magic>")
```

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_context_builder.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/magic/context_builder.py tests/magic/test_context_builder.py
git commit -m "feat(magic): context_builder renders <learned-magic> with known/prepared/slots"
```

### Task 8.2: Add `learned_v1.*` OTEL spans

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/magic.py`
- Modify: `sidequest-server/tests/magic/test_magic_span.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/magic/test_magic_span.py`:

```python
def test_learned_v1_span_routes_registered():
    """All five learned_v1 span names route to a renderer."""
    from sidequest.telemetry.spans.magic import MAGIC_SPAN_RENDERERS

    expected = {
        "learned_v1.prepare",
        "learned_v1.cast",
        "learned_v1.rest",
        "learned_v1.turn_undead",
        "learned_v1.backlash",
    }
    assert expected.issubset(set(MAGIC_SPAN_RENDERERS.keys()))
```

- [ ] **Step 2: Run to verify fail**

Run: `cd sidequest-server && uv run pytest tests/magic/test_magic_span.py::test_learned_v1_span_routes_registered -v`

Expected: FAIL — keys not in the renderer dict.

- [ ] **Step 3: Implement**

In `sidequest/telemetry/spans/magic.py`, follow the existing item_legacy_v1 span pattern. Add five renderers:

```python
def _render_learned_v1_prepare(span):
    return {
        "actor": span.attributes.get("actor_id"),
        "tradition": span.attributes.get("tradition"),
        "prepared": span.attributes.get("prepared_spells"),
        "slots_max": span.attributes.get("slots_max"),
    }


def _render_learned_v1_cast(span):
    return {
        "actor": span.attributes.get("actor_id"),
        "spell_id": span.attributes.get("spell_id"),
        "validator_outcome": span.attributes.get("validator_outcome"),
        "slot_consumed": span.attributes.get("slot_consumed"),
        "save_stat": span.attributes.get("save_stat"),
        "save_result": span.attributes.get("save_result"),
        "damage_applied": span.attributes.get("damage_applied"),
    }


def _render_learned_v1_rest(span):
    return {
        "actor": span.attributes.get("actor_id"),
        "slots_restored": span.attributes.get("slots_restored"),
        "location": span.attributes.get("location"),
    }


def _render_learned_v1_turn_undead(span):
    return {
        "actor": span.attributes.get("actor_id"),
        "undead_hd": span.attributes.get("undead_hd"),
        "divine_favor": span.attributes.get("divine_favor"),
        "outcome": span.attributes.get("outcome"),
    }


def _render_learned_v1_backlash(span):
    return {
        "actor": span.attributes.get("actor_id"),
        "spell_id": span.attributes.get("spell_id"),
        "backlash_reason": span.attributes.get("backlash_reason"),
        "hard_limit_violated": span.attributes.get("hard_limit_violated"),
    }


MAGIC_SPAN_RENDERERS["learned_v1.prepare"] = _render_learned_v1_prepare
MAGIC_SPAN_RENDERERS["learned_v1.cast"] = _render_learned_v1_cast
MAGIC_SPAN_RENDERERS["learned_v1.rest"] = _render_learned_v1_rest
MAGIC_SPAN_RENDERERS["learned_v1.turn_undead"] = _render_learned_v1_turn_undead
MAGIC_SPAN_RENDERERS["learned_v1.backlash"] = _render_learned_v1_backlash
```

(Adjust the dict name if the local module uses a different one — search for `item_legacy_v1.cast` in the file to find the registration pattern and mirror it.)

- [ ] **Step 4: Run to verify pass**

Run: `cd sidequest-server && uv run pytest tests/magic/test_magic_span.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans/magic.py tests/magic/test_magic_span.py
git commit -m "feat(telemetry): learned_v1.* span renderers — prepare/cast/rest/turn/backlash"
```

---

## Phase 9 — UI surface (ui repo)

### Task 9.1: Extend LedgerPanel with `learned_v1` block

**Files:**
- Modify: `sidequest-ui/src/components/CharacterPanel/LedgerPanel.tsx`
- Modify: `sidequest-ui/src/types/magic.ts`
- Modify: `sidequest-ui/src/__tests__/LedgerPanel.test.tsx`

- [ ] **Step 1: Add types**

Edit `src/types/magic.ts`. Append:

```typescript
export interface LearnedMagicState {
  tradition: 'arcane' | 'divine';
  knownSpells: string[];
  preparedSpells: Record<number, string[]>;
  slotsRemaining: Record<number, number>;
  slotsMax: Record<number, number>;
}

export interface DivineFavorBar {
  value: number;
  thresholdHigh: number;
  thresholdLow: number;
}
```

- [ ] **Step 2: Write failing component test**

Append to `src/__tests__/LedgerPanel.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react';
import { LedgerPanel } from '../components/CharacterPanel/LedgerPanel';

test('renders learned_v1 block when character has known spells', () => {
  render(
    <LedgerPanel
      itemBars={[]}
      learnedMagic={{
        tradition: 'arcane',
        knownSpells: ['magic_missile', 'sleep'],
        preparedSpells: { 1: ['magic_missile'] },
        slotsRemaining: { 1: 1 },
        slotsMax: { 1: 2 },
      }}
      divineFavor={null}
    />,
  );

  expect(screen.getByText(/Magic Missile/i)).toBeInTheDocument();
  expect(screen.getByText(/Prepared/i)).toBeInTheDocument();
  expect(screen.getByText(/1 \/ 2/)).toBeInTheDocument();
});

test('renders divine_favor bar for cleric', () => {
  render(
    <LedgerPanel
      itemBars={[]}
      learnedMagic={null}
      divineFavor={{ value: 0.0, thresholdHigh: 0.7, thresholdLow: -0.7 }}
    />,
  );
  expect(screen.getByLabelText(/divine favor/i)).toBeInTheDocument();
});
```

- [ ] **Step 3: Run to verify fail**

Run: `cd sidequest-ui && npx vitest run src/__tests__/LedgerPanel.test.tsx`

Expected: FAIL — props not accepted / elements not rendered.

- [ ] **Step 4: Implement**

Edit `src/components/CharacterPanel/LedgerPanel.tsx`. Add a sub-section that renders when `learnedMagic` is non-null:

```tsx
import type { LearnedMagicState, DivineFavorBar } from '../../types/magic';

interface LedgerPanelProps {
  itemBars: ItemBarSummary[];
  learnedMagic: LearnedMagicState | null;
  divineFavor: DivineFavorBar | null;
}

export function LedgerPanel({ itemBars, learnedMagic, divineFavor }: LedgerPanelProps) {
  return (
    <div className="ledger-panel">
      {/* existing item bars block stays as-is */}
      {/* ... */}

      {learnedMagic && (
        <section className="learned-magic" aria-label="learned magic">
          <h4>Spells</h4>
          <div className="known">
            <span className="label">Known:</span>
            {learnedMagic.knownSpells.map((sid) => (
              <span key={sid} className="spell-chip">
                {prettifySpellId(sid)}
              </span>
            ))}
          </div>
          <div className="prepared">
            <span className="label">Prepared:</span>
            {Object.entries(learnedMagic.preparedSpells).map(([level, spells]) => (
              <div key={level} className={`prep-row prep-l${level}`}>
                <span className="level">L{level}</span>
                {spells.map((sid) => (
                  <span key={sid} className="spell-chip prepared">
                    {prettifySpellId(sid)}
                  </span>
                ))}
                <span className="slots">
                  {learnedMagic.slotsRemaining[Number(level)] ?? 0} /{' '}
                  {learnedMagic.slotsMax[Number(level)] ?? 0}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {divineFavor && (
        <section className="divine-favor" aria-label="divine favor">
          <h4>Divine Favor</h4>
          <FavorBar
            value={divineFavor.value}
            thresholdHigh={divineFavor.thresholdHigh}
            thresholdLow={divineFavor.thresholdLow}
          />
        </section>
      )}
    </div>
  );
}

function prettifySpellId(sid: string): string {
  return sid
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function FavorBar({
  value,
  thresholdHigh,
  thresholdLow,
}: {
  value: number;
  thresholdHigh: number;
  thresholdLow: number;
}) {
  // -1..1 mapped to 0..100% width.
  const pct = ((value + 1) / 2) * 100;
  return (
    <div className="favor-bar" role="meter" aria-valuemin={-1} aria-valuemax={1} aria-valuenow={value}>
      <div className="favor-bar-fill" style={{ width: `${pct}%` }} />
      <span className="favor-bar-value">{value.toFixed(2)}</span>
    </div>
  );
}
```

- [ ] **Step 5: Run to verify pass**

Run: `cd sidequest-ui && npx vitest run src/__tests__/LedgerPanel.test.tsx`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-ui
git checkout -b feat/cc-magic-ledger-panel develop
git add src/components/CharacterPanel/LedgerPanel.tsx src/types/magic.ts src/__tests__/LedgerPanel.test.tsx
git commit -m "feat(ui): LedgerPanel renders learned_v1 known/prepared/slots + divine_favor"
```

(`PrepareSpellsAction.tsx` and `TurnUndeadAction.tsx` are deferred to a follow-up task — the LedgerPanel render is sufficient for the v1 playable; preparation can run via narration verb until the action button ships.)

---

## Phase 10 — Integration test + smoke playtest

### Task 10.1: End-to-end wiring test

**Files:**
- Create: `sidequest-server/tests/magic/test_e2e_learned_v1.py`

- [ ] **Step 1: Write the test**

Create the file:

```python
"""End-to-end wiring: chargen → seed → prepare → cast → rest in Sünden."""

from pathlib import Path

import pytest

CONTENT_ROOT = Path(__file__).parents[3] / "sidequest-content" / "genre_packs"


@pytest.mark.skipif(
    not CONTENT_ROOT.exists(), reason="sidequest-content not checked out alongside server"
)
def test_e2e_mage_in_sunden_prepares_casts_rests():
    """A Mage in caverns_sunden picks Magic Missile + Sleep, prepares Magic
    Missile, casts it (slot decrements), rests (slot restores)."""
    from sidequest.genre.magic_loader import load_world_magic
    from sidequest.magic.learned_ops import cast, prepare, rest
    from sidequest.magic.models import MagicWorking
    from sidequest.magic.state import BarKey, MagicState
    from sidequest.server.magic_init import seed_learned_v1_state
    from sidequest.genre.models.character import ClassDef, ClassMagicConfig

    genre_yaml = CONTENT_ROOT / "caverns_and_claudes" / "magic.yaml"
    world_yaml = CONTENT_ROOT / "caverns_and_claudes" / "worlds" / "caverns_sunden" / "magic.yaml"
    config = load_world_magic(genre_yaml=genre_yaml, world_yaml=world_yaml)

    # Sanity: the spell catalog loaded.
    assert config.spell_catalogs is not None
    assert "arcane_l1" in config.spell_catalogs
    assert any(s.id == "magic_missile" for s in config.spell_catalogs["arcane_l1"].spells)

    # Build the state and seed for an L1 Mage actor "rux".
    state = MagicState.from_config(config)
    state.add_character("rux")
    mage = ClassDef(
        id="mage", display_name="Mage", rpg_role="control",
        jungian_default="magician", prime_requisite="INT",
        minimum_score=9, kit_table="mage_kit",
        magic_access="learned_v1",
        magic_config=ClassMagicConfig(
            tradition="arcane",
            slots_by_class_level={"1": {"1": 1}},
            starting_known_spells=2,
            save_dc_stat="INT",
        ),
    )
    seed_learned_v1_state(
        state, actor="rux", class_def=mage, class_level=1,
        chosen_known_spells=["magic_missile", "sleep"],
    )

    # Prepare Magic Missile.
    prepare(state, actor="rux", prep={1: ["magic_missile"]})
    bar_key = BarKey(scope="character", owner_id="rux", bar_id="slots_l1")
    assert state.get_bar(bar_key).value == 1.0  # 1 slot, 1 prepared

    # Cast it.
    working = MagicWorking(
        plugin="learned_v1", mechanism="studied", actor="rux",
        domain="physical", narrator_basis="cast magic missile at the goblin",
        spell_id="magic_missile", slot_level=1, costs={"slots_l1": 1.0},
    )
    cast(state, working=working)
    assert state.get_bar(bar_key).value == 0.0

    # Rest at the Lampwick.
    rest(state, actor="rux")
    assert state.get_bar(bar_key).value == 1.0
    assert state.prepared_spells["rux"] == {}
```

- [ ] **Step 2: Run**

Run: `cd sidequest-server && uv run pytest tests/magic/test_e2e_learned_v1.py -v`

Expected: PASS (or SKIP if content dir not present).

- [ ] **Step 3: Commit**

```bash
cd sidequest-server
git add tests/magic/test_e2e_learned_v1.py
git commit -m "test(magic): e2e — Mage in Sünden prepares/casts/rests, content-pinned"
```

### Task 10.2: Smoke scenario for headless playtest

**Files:**
- Create: `scenarios/cc_mage_smoke.yaml` (orchestrator)

- [ ] **Step 1: Author the scenario**

Create at orchestrator root:

```yaml
# Caverns & Claudes / Sünden — Mage smoke playtest.
# Verifies learned_v1 plumbing in a real game session: chargen as Mage,
# walk to Grimvault, cast Magic Missile, see the OTEL span fire.
name: cc_mage_smoke
genre: caverns_and_claudes
world: caverns_sunden

character:
  strategy: chargen_canned
  class: mage
  starting_known_spells: [magic_missile, sleep]

actions:
  - "I prepare Magic Missile."
  - "I leave the Lampwick and walk north toward Grimvault."
  - "I descend the threshold and enter the Sorting Floor."
  - "If anything is in the room, I cast Magic Missile at the closest hostile."
  - "I return to Sünden, rest at the Lampwick, and prepare Sleep."

assertions:
  - span: learned_v1.prepare
    occurs: at_least_once
    attrs:
      actor_id: { not_null: true }
      tradition: arcane
  - span: learned_v1.cast
    occurs: at_least_once
    attrs:
      spell_id: magic_missile
      slot_consumed: true
  - span: learned_v1.rest
    occurs: at_least_once
```

- [ ] **Step 2: Run the scenario (after server changes are merged)**

Run from orchestrator root: `just playtest-scenario cc_mage_smoke`

Expected: scenario completes, all asserted spans fire.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2
git add scenarios/cc_mage_smoke.yaml
git commit -m "scenarios: cc_mage_smoke — headless verification of learned_v1 plumbing"
```

---

## Cross-repo PR sequence

1. **server PR**: `feat/magic-learned-v1` → `develop` (covers Phase 2-6, 8, 10.1).
2. **content PR**: `feat/cc-magic-learned-v1` → `develop` (covers Phase 1, 7).
3. **ui PR**: `feat/cc-magic-ledger-panel` → `develop` (covers Phase 9).
4. **orchestrator commit**: directly on `main` (Phase 10.2 scenario file).

Order matters: server merges first (so the wiring exists), content second (so the YAML loads cleanly into the new wiring), ui third (consumes the new state in messages).

---

## Self-Review

**Spec coverage check:**

- ✅ §1 plugin set (item_legacy_v1 + learned_v1) — Phase 4
- ✅ §1 cost types (components/backlash/slot) — Tasks 7.1, content
- ✅ §1 ledger bars (4 types) — Tasks 5.x (slot bars), 7.4 (divine_favor)
- ✅ §1 turn undead — Task 5.4
- ✅ §2 spell catalog schema — Task 3.1
- ✅ §3 plugin operations — Tasks 5.1-5.4
- ✅ §3 context block — Task 8.1
- ✅ §4 content YAML diff — Phase 7 in full
- ✅ §5 UI LedgerPanel — Task 9.1
- ✅ §6 OTEL spans — Task 8.2
- ✅ §7 hard limits enforced — handled by existing validator pipeline (no plan task; spec §7 calls out "the validator already runs hard_limits against any working regardless of source")
- ✅ §8 out of scope items left out — confirmed
- ✅ §11 success criteria — Tasks 10.1 (E2E) + 10.2 (smoke) cover all 6 success criteria

**Placeholder scan:** No "TBD", no "implement later", no "similar to", no "add error handling." Each step has concrete code or concrete commands.

**Type consistency:**

- `MagicWorking` field additions consistent across Tasks 2.1, 4.2, 5.2, 8.2.
- `ClassMagicConfig.slots_by_class_level` keyed `dict[str, dict[str, int]]` consistent in Tasks 2.2, 6.1, 7.2.
- `learn_spell` / `prepare_spells` / `prepared_spells` / `known_spells` field names consistent across Tasks 2.3, 5.1, 5.2, 5.3, 8.1.
- Span names `learned_v1.{prepare,cast,rest,turn_undead,backlash}` consistent across Task 8.2 and the spec §6.

No issues found.
