# C&C B/X Class-Distinct Beats and Morale — Implementation Plan

> **COMPLETED via sprint stories — checkbox state never updated.** Server resolver at `sidequest-server/sidequest/game/morale.py` (pure 2d6 vs `MoraleDef.score` per spec §4.4). Three-tier wiring in `narration_apply.py`: `_emit_morale_triggers` (first_blood / half_killed / leader_killed / intimidated), `_apply_flee_consequences` (chase / surrender / rout via `cdef.morale.flee_consequence` → `encounter.flee_consequence_pending`), and `_apply_morale_sidecar` (narrator-emitted morale_event per Task 10 / ADR-039). All 4 C&C classes carry distinct `encounter_beat_choices` in `classes.yaml`. Content: confrontations in `rules.yaml` carry `morale: {score, triggers, flee_consequence}` blocks. OTEL `confrontation.morale_trigger` + `confrontation.flee_consequence` spans emit. Tests at `tests/game/test_morale.py` and `tests/genre/test_models/test_morale.py`. Plan body left intact as historical reference.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire B/X-style class-distinct combat beats and 2d6 morale into the Caverns & Claudes genre pack — schema, pack-load validation, beat-filter helper, morale function, OTEL spans, narrator prompt invariant, content authoring, and tests.

**Architecture:** Approach 3 (minimal-touch) from the spec — extend three existing pydantic models (`BeatDef`, `ConfrontationDef`, `NpcArchetype`) with optional fields rather than introducing new subsystems. New `MoraleDef` model + `MoraleTrigger`/`FleeConsequence` enums. New `morale.py` module with one pure function. Beat filter is a single helper that replaces direct `confrontation.beats` iteration at the selection call site. Plug-in seam for memorization story #2 lives in the beat-filter helper at the `cast_spell` resource gate.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest, OpenTelemetry, uv. Server repo `sidequest-server/`, content repo `sidequest-content/`.

**Spec:** `docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md` (orchestrator repo).

---

## File Structure

### Server changes (`sidequest-server/`)

| Path | Action | Responsibility |
|---|---|---|
| `sidequest/genre/models/rules.py` | Modify | Add `BeatDef.class_filter`, new `MoraleTrigger`/`FleeConsequence` enums, new `MoraleDef`, `ConfrontationDef.morale` |
| `sidequest/genre/models/character.py` | Modify | Add `NpcArchetype.mindless: bool = False` |
| `sidequest/genre/loader.py` | Modify | Pack-load validation: class_filter ↔ classes.yaml refs, encounter_beat_choices ↔ beat IDs, empty whitelist for participating classes |
| `sidequest/game/morale.py` | **Create** | `maybe_check_morale()` pure function, `MoraleOutcome` enum |
| `sidequest/game/beat_filter.py` | **Create** | `beats_available_for()` helper: class_filter ∩ encounter_beat_choices ∩ resource gate |
| `sidequest/server/narration_apply.py` | Modify | Replace direct beat iteration with `beats_available_for()`; emit morale trigger calls at first_blood / half_killed / leader_killed / intimidated |
| `sidequest/telemetry/spans/combat.py` | Modify | Add `SPAN_BEAT_FILTER` and `SPAN_MORALE_CHECK` declarations + SpanRoute entries |
| `sidequest/agents/narrator.py` | Modify | Add one-line prompt invariant under the per-turn available-actions zone (ADR-009) |

### Server tests (`sidequest-server/tests/`)

| Path | Action | Responsibility |
|---|---|---|
| `tests/genre/test_models/test_rules.py` | Modify | BeatDef class_filter validation (None / non-empty / empty rejection) |
| `tests/genre/test_models/test_morale.py` | **Create** | MoraleDef score range, non-empty triggers; enum closedness |
| `tests/genre/test_models/test_character.py` | Modify | NpcArchetype.mindless default + override |
| `tests/genre/test_pack_load.py` | Modify | New: dangling class_filter, dangling encounter_beat_choices, empty encounter_beat_choices for participating class, C&C combat has morale block |
| `tests/game/test_beat_filter.py` | **Create** | beats_available_for unit tests per class + cast_spell resource gate |
| `tests/game/test_morale.py` | **Create** | maybe_check_morale: deterministic RNG, mindless skip, side-level outcome, no-op when morale=None |
| `tests/server/test_apply_beat.py` | Modify | Trigger emission integration + flee_consequence application |
| `tests/telemetry/test_combat_spans.py` | Modify (or create) | beat_filter and morale_check spans emit with required attrs |

### Content changes (`sidequest-content/`)

| Path | Action | Responsibility |
|---|---|---|
| `genre_packs/caverns_and_claudes/rules.yaml` | Modify | Re-tag shield_bash + feint with class_filter; add 8 new beats; add morale block to combat; sync allowed_classes; drop stale custom_rules flags |
| `genre_packs/caverns_and_claudes/classes.yaml` | Modify | Populate encounter_beat_choices per class; set magic_access for Mage and Cleric |
| `genre_packs/caverns_and_claudes/worlds/caverns_sunden/<archetype-files>` | Modify | Add `mindless: true` to skeleton/zombie/animated/golem/ooze archetypes |

---

## Conventions

- All `pytest` and `ruff` commands run from the **server subrepo root**: `cd sidequest-server && uv run pytest ...`. The `cd` is shown explicitly in each command for clarity.
- All commits target the **server subrepo's tracked branch** (per `repos.yaml`).
- Content commits target the **content subrepo's tracked branch**.
- Each task ends with a commit. Run `uv run ruff format .` and `uv run ruff check .` before each commit; if either fails, fix and recommit.
- Test names use `snake_case`. Module-level docstrings explain *what* the module covers; function docstrings only when behavior is non-obvious.

---

## Task 1: Add `BeatDef.class_filter`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:73-142` (BeatDef class)
- Test: `sidequest-server/tests/genre/test_models/test_rules.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_models/test_rules.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import BeatDef, BeatKind


def _beat(**overrides):
    base = dict(id="x", label="X", kind=BeatKind.strike, stat_check="STR", base=1)
    base.update(overrides)
    return base


def test_beat_class_filter_defaults_none():
    b = BeatDef(**_beat())
    assert b.class_filter is None


def test_beat_class_filter_accepts_nonempty_list():
    b = BeatDef(**_beat(class_filter=["Fighter"]))
    assert b.class_filter == ["Fighter"]


def test_beat_class_filter_rejects_empty_list():
    with pytest.raises(ValidationError) as exc:
        BeatDef(**_beat(class_filter=[]))
    assert "class_filter" in str(exc.value).lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_rules.py -v -k class_filter
```

Expected: 3 failures with `BeatDef` rejecting unknown field `class_filter`.

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/genre/models/rules.py`, inside `BeatDef`, add the field and validator. The new field is added below `resource_deltas: dict[str, float] | None = None` (the last existing field):

```python
    class_filter: list[str] | None = None
```

Then in the existing `_validate` `model_validator(mode="after")` method on `BeatDef`, add at the end (before `return self`):

```python
        if self.class_filter is not None and not self.class_filter:
            raise ValueError(f"beat '{self.id}' class_filter must be None or non-empty list")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_rules.py -v -k class_filter
```

Expected: 3 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/genre/models/rules.py tests/genre/test_models/test_rules.py
git commit -m "feat(rules): add BeatDef.class_filter for class-restricted beats"
```

---

## Task 2: Add `MoraleTrigger`, `FleeConsequence`, `MoraleDef`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py`
- Test: `sidequest-server/tests/genre/test_models/test_morale.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_models/test_morale.py`:

```python
"""Tests for MoraleDef and morale enums (B/X port)."""
import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import (
    FleeConsequence,
    MoraleDef,
    MoraleTrigger,
)


def test_morale_trigger_enum_values():
    assert {t.value for t in MoraleTrigger} == {
        "first_blood",
        "half_killed",
        "intimidated",
        "leader_killed",
    }


def test_flee_consequence_enum_values():
    assert {f.value for f in FleeConsequence} == {"chase", "surrender", "rout"}


def test_morale_def_defaults_score_8_chase():
    m = MoraleDef(triggers=[MoraleTrigger.first_blood])
    assert m.score == 8
    assert m.flee_consequence is FleeConsequence.chase


def test_morale_def_rejects_score_below_2():
    with pytest.raises(ValidationError):
        MoraleDef(score=1, triggers=[MoraleTrigger.first_blood])


def test_morale_def_rejects_score_above_12():
    with pytest.raises(ValidationError):
        MoraleDef(score=13, triggers=[MoraleTrigger.first_blood])


def test_morale_def_rejects_empty_triggers():
    with pytest.raises(ValidationError):
        MoraleDef(score=8, triggers=[])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_morale.py -v
```

Expected: import errors (`MoraleDef`, `MoraleTrigger`, `FleeConsequence` don't exist).

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/genre/models/rules.py`, near the existing `BeatKind` / `ResolutionMode` enum block (top of file under imports), add:

```python
from enum import StrEnum  # already imported; do not duplicate


class MoraleTrigger(StrEnum):
    """B/X morale check triggers. Per spec §2.2."""

    first_blood = "first_blood"
    half_killed = "half_killed"
    intimidated = "intimidated"
    leader_killed = "leader_killed"


class FleeConsequence(StrEnum):
    """How the opponent side breaks off when morale fails."""

    chase = "chase"
    surrender = "surrender"
    rout = "rout"
```

Then directly after the `MetricDef` class definition (around line 165), add the `MoraleDef` model:

```python
class MoraleDef(BaseModel):
    """Optional morale block on a combat ConfrontationDef. B/X port.

    Score is the 2d6 target; total ≤ score = stay, > = flee.
    """

    model_config = {"extra": "forbid"}

    score: int = 8
    triggers: list[MoraleTrigger]
    flee_consequence: FleeConsequence = FleeConsequence.chase

    @model_validator(mode="after")
    def _validate(self) -> MoraleDef:
        if not (2 <= self.score <= 12):
            raise ValueError(f"morale score {self.score} not in 2..12")
        if not self.triggers:
            raise ValueError("morale.triggers must be non-empty")
        return self
```

(`StrEnum`, `BaseModel`, `model_validator` are already imported in this file. Confirm before saving.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_morale.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/genre/models/rules.py tests/genre/test_models/test_morale.py
git commit -m "feat(rules): add MoraleTrigger, FleeConsequence, MoraleDef"
```

---

## Task 3: Add `ConfrontationDef.morale` field

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:248-307` (ConfrontationDef)
- Test: append to `sidequest-server/tests/genre/test_models/test_morale.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_models/test_morale.py`:

```python
from sidequest.genre.models.rules import (
    BeatDef,
    BeatKind,
    ConfrontationDef,
    MetricDef,
)


def _minimal_combat_kwargs():
    return dict(
        type="combat",
        label="Test Combat",
        category="combat",
        player_metric=MetricDef(name="momentum", starting=0, threshold=7),
        opponent_metric=MetricDef(name="momentum", starting=0, threshold=7),
        beats=[
            BeatDef(id="attack", label="Attack", kind=BeatKind.strike, stat_check="STR")
        ],
    )


def test_confrontation_morale_defaults_none():
    cd = ConfrontationDef(**_minimal_combat_kwargs())
    assert cd.morale is None


def test_confrontation_accepts_morale_block():
    cd = ConfrontationDef(
        **_minimal_combat_kwargs(),
        morale=MoraleDef(score=8, triggers=[MoraleTrigger.first_blood]),
    )
    assert cd.morale is not None
    assert cd.morale.score == 8
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_morale.py::test_confrontation_morale_defaults_none -v
```

Expected: FAIL — ConfrontationDef rejects unknown field `morale`.

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/genre/models/rules.py`, inside `ConfrontationDef`, add the field directly after `opponent_default_stats: dict[str, int] | None = None`:

```python
    morale: MoraleDef | None = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_morale.py -v
```

Expected: all 8 tests PASS (6 from Task 2 + 2 new).

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/genre/models/rules.py tests/genre/test_models/test_morale.py
git commit -m "feat(rules): add ConfrontationDef.morale optional block"
```

---

## Task 4: Add `NpcArchetype.mindless`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py`
- Test: `sidequest-server/tests/genre/test_models/test_character.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_models/test_character.py`:

```python
def test_npc_archetype_mindless_defaults_false():
    """B/X mindless flag — bypasses morale checks."""
    arch = NpcArchetype(id="goblin", role="enemy")
    assert arch.mindless is False


def test_npc_archetype_mindless_can_be_true():
    arch = NpcArchetype(id="skeleton", role="enemy", mindless=True)
    assert arch.mindless is True
```

(If the existing `test_character.py` doesn't already import `NpcArchetype`, add `from sidequest.genre.models.character import NpcArchetype` at the top. Read the existing imports first; do not duplicate.)

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py -v -k mindless
```

Expected: FAIL — `mindless` accepted as extras dict but not as a typed attribute (`arch.mindless` raises AttributeError).

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/genre/models/character.py`, find the `NpcArchetype` class (the docstring mentions "genre packs may add extra fields"). Add as a new explicit field after the existing core fields:

```python
    mindless: bool = False
```

(Place it adjacent to other behavioral flags. If the file has no clear "flags" section, place it after the `role` field.)

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/genre/test_models/test_character.py -v -k mindless
```

Expected: 2 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/genre/models/character.py tests/genre/test_models/test_character.py
git commit -m "feat(character): add NpcArchetype.mindless flag (B/X morale bypass)"
```

---

## Task 5: Pack-load validation — three new rules

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py:148-268` (around `_load_rules_config`)
- Test: `sidequest-server/tests/genre/test_pack_load.py`

The three new rules:
1. Every `BeatDef.class_filter` entry references a class declared in `classes.yaml`.
2. Every `ClassDef.encounter_beat_choices` entry references a beat ID in some confrontation pool.
3. Every class participating in a confrontation has non-empty `encounter_beat_choices`.

For rule (3), "participating" means: appears in `rules.yaml.allowed_classes`. (Conservative scope; tighter rules can come later.)

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/genre/test_pack_load.py`:

```python
import pytest
from sidequest.genre.error import PackError
from sidequest.genre.loader import load_pack  # confirm exact import path


def test_pack_load_rejects_dangling_class_filter(tmp_path, minimal_pack_factory):
    """class_filter must reference a class declared in classes.yaml."""
    pack = minimal_pack_factory(tmp_path)
    pack.set_rules_yaml(
        confrontations=[{
            "type": "combat",
            "label": "C", "category": "combat",
            "player_metric": {"name": "m", "starting": 0, "threshold": 7},
            "opponent_metric": {"name": "m", "starting": 0, "threshold": 7},
            "beats": [{
                "id": "ghost_strike", "label": "X",
                "kind": "strike", "stat_check": "STR",
                "class_filter": ["Necromancer"],  # not in classes.yaml
            }],
        }],
        allowed_classes=["Fighter"],
    )
    pack.set_classes_yaml([{"id": "fighter", "display_name": "Fighter",
                             "rpg_role": "tank", "prime_requisite": "STR",
                             "minimum_score": 9, "kit_table": "fighter_kit",
                             "flavor": "—",
                             "encounter_beat_choices": ["ghost_strike"]}])
    with pytest.raises(PackError, match="class_filter.*Necromancer.*not declared"):
        load_pack(pack.path)


def test_pack_load_rejects_dangling_encounter_beat_choice(tmp_path, minimal_pack_factory):
    """encounter_beat_choices must reference a beat that exists in some pool."""
    pack = minimal_pack_factory(tmp_path)
    pack.set_rules_yaml(
        confrontations=[{
            "type": "combat", "label": "C", "category": "combat",
            "player_metric": {"name": "m", "starting": 0, "threshold": 7},
            "opponent_metric": {"name": "m", "starting": 0, "threshold": 7},
            "beats": [{"id": "attack", "label": "A", "kind": "strike", "stat_check": "STR"}],
        }],
        allowed_classes=["Fighter"],
    )
    pack.set_classes_yaml([{"id": "fighter", "display_name": "Fighter",
                             "rpg_role": "tank", "prime_requisite": "STR",
                             "minimum_score": 9, "kit_table": "fighter_kit",
                             "flavor": "—",
                             "encounter_beat_choices": ["attack", "smite"]}])  # smite missing
    with pytest.raises(PackError, match="encounter_beat_choices.*smite.*not in pool"):
        load_pack(pack.path)


def test_pack_load_rejects_empty_encounter_beat_choices_for_allowed_class(tmp_path, minimal_pack_factory):
    """A class in allowed_classes must have a non-empty encounter_beat_choices."""
    pack = minimal_pack_factory(tmp_path)
    pack.set_rules_yaml(
        confrontations=[{
            "type": "combat", "label": "C", "category": "combat",
            "player_metric": {"name": "m", "starting": 0, "threshold": 7},
            "opponent_metric": {"name": "m", "starting": 0, "threshold": 7},
            "beats": [{"id": "attack", "label": "A", "kind": "strike", "stat_check": "STR"}],
        }],
        allowed_classes=["Fighter"],
    )
    pack.set_classes_yaml([{"id": "fighter", "display_name": "Fighter",
                             "rpg_role": "tank", "prime_requisite": "STR",
                             "minimum_score": 9, "kit_table": "fighter_kit",
                             "flavor": "—",
                             "encounter_beat_choices": []}])
    with pytest.raises(PackError, match="encounter_beat_choices.*empty"):
        load_pack(pack.path)
```

If `minimal_pack_factory` fixture does not exist, add it as a conftest fixture or extend an existing one. Check `tests/genre/conftest.py` for reusable fixtures first.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k "dangling or empty_encounter"
```

Expected: 3 FAIL — current loader does not perform these cross-checks.

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/genre/loader.py`, find the function that finalizes rules + classes loading (`_load_rules_config` is the entry; the cross-validation likely belongs in or just after the call site that loads both). Add a new helper near the top of the loader module:

```python
def _validate_class_filter_refs(rules: RulesConfig, classes: list[ClassDef]) -> None:
    """Loud-fail if any beat.class_filter references a class not in classes.yaml,
    if any class.encounter_beat_choices references a missing beat ID,
    or if a class in allowed_classes has empty encounter_beat_choices.
    """
    declared_classes = {c.display_name for c in classes}
    all_beat_ids: set[str] = set()
    for cd in rules.confrontations:
        for beat in cd.beats:
            all_beat_ids.add(beat.id)
            if beat.class_filter is not None:
                missing = [c for c in beat.class_filter if c not in declared_classes]
                if missing:
                    raise PackError(
                        f"beat '{beat.id}' class_filter references class(es) "
                        f"{missing!r} not declared in classes.yaml"
                    )

    for c in classes:
        if c.display_name in rules.allowed_classes:
            if not c.encounter_beat_choices:
                raise PackError(
                    f"class '{c.display_name}' is in allowed_classes but has "
                    f"empty encounter_beat_choices"
                )
            missing = [b for b in c.encounter_beat_choices if b not in all_beat_ids]
            if missing:
                raise PackError(
                    f"class '{c.display_name}' encounter_beat_choices "
                    f"references beat id(s) {missing!r} not in pool"
                )
```

Call `_validate_class_filter_refs(rules, classes)` from the pack-load orchestrator function (find it by `rg "RulesConfig" sidequest/genre/loader.py | head` — likely a `load_pack` or `load_genre_pack` function that already loads both). Place the call after both `rules` and `classes` are loaded but before the GenrePack object is finalized.

If `PackError` doesn't exist, check `sidequest/genre/error.py` (the import in the test exists; if absent, define `class PackError(Exception)` there).

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v -k "dangling or empty_encounter"
```

Expected: 3 PASS.

- [ ] **Step 5: Run the full pack-load suite to verify no regressions**

```bash
cd sidequest-server && uv run pytest tests/genre/test_pack_load.py -v
```

Expected: all PASS. If existing C&C pack-load fails because the production C&C pack doesn't yet declare `encounter_beat_choices`, **stop** — content authoring (Task 14–16) must precede the loader change OR the loader change must coexist with content. Resolve by either: (a) sequencing content first; or (b) noting in the loader that empty encounter_beat_choices is only an error when the class is *also* configured with at least one signature beat. Default: stay loud-fail; commit Task 14 before merging Task 5. Add a TODO note in the test file linking back to Task 14.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/genre/loader.py sidequest/genre/error.py tests/genre/test_pack_load.py
git commit -m "feat(loader): validate class_filter / encounter_beat_choices cross-references"
```

---

## Task 6: Create `beats_available_for` helper

**Files:**
- Create: `sidequest-server/sidequest/game/beat_filter.py`
- Test: `sidequest-server/tests/game/test_beat_filter.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_beat_filter.py`:

```python
"""Tests for beats_available_for: class_filter ∩ encounter_beat_choices ∩ resource gate."""
import pytest

from sidequest.game.beat_filter import beats_available_for
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.rules import (
    BeatDef,
    BeatKind,
    ConfrontationDef,
    MetricDef,
)


def _beat(id_, *, class_filter=None):
    return BeatDef(id=id_, label=id_, kind=BeatKind.strike, stat_check="STR",
                   class_filter=class_filter)


def _confrontation(beats):
    return ConfrontationDef(
        type="combat", label="C", category="combat",
        player_metric=MetricDef(name="m", starting=0, threshold=7),
        opponent_metric=MetricDef(name="m", starting=0, threshold=7),
        beats=beats,
    )


def _class(display_name, choices):
    return ClassDef(
        id=display_name.lower(), display_name=display_name,
        rpg_role="tank", prime_requisite="STR", minimum_score=9,
        kit_table=f"{display_name.lower()}_kit", flavor="-",
        encounter_beat_choices=choices,
    )


def test_universal_beats_visible_to_every_class():
    cd = _confrontation([_beat("attack")])
    fighter = _class("Fighter", ["attack"])
    out = beats_available_for(cd, fighter, spell_slots_remaining=0.0)
    assert [b.id for b in out] == ["attack"]


def test_class_filter_excludes_other_classes():
    cd = _confrontation([_beat("cleave", class_filter=["Fighter"])])
    mage = _class("Mage", ["cleave"])  # mage's whitelist is wrong but filter still excludes
    out = beats_available_for(cd, mage, spell_slots_remaining=0.0)
    assert out == []


def test_encounter_beat_choices_narrows_pool():
    cd = _confrontation([_beat("attack"), _beat("flee")])
    fighter = _class("Fighter", ["attack"])  # excludes flee
    out = beats_available_for(cd, fighter, spell_slots_remaining=0.0)
    assert [b.id for b in out] == ["attack"]


def test_cast_spell_filtered_when_no_slots():
    cd = _confrontation([_beat("cast_spell", class_filter=["Mage"])])
    mage = _class("Mage", ["cast_spell"])
    out = beats_available_for(cd, mage, spell_slots_remaining=0.0)
    assert out == []


def test_cast_spell_visible_when_slot_available():
    cd = _confrontation([_beat("cast_spell", class_filter=["Mage"])])
    mage = _class("Mage", ["cast_spell"])
    out = beats_available_for(cd, mage, spell_slots_remaining=1.0)
    assert [b.id for b in out] == ["cast_spell"]


def test_empty_encounter_beat_choices_raises():
    from sidequest.genre.error import PackError

    cd = _confrontation([_beat("attack")])
    fighter = _class("Fighter", [])
    with pytest.raises(PackError, match="empty encounter_beat_choices"):
        beats_available_for(cd, fighter, spell_slots_remaining=0.0)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_beat_filter.py -v
```

Expected: import error — `sidequest.game.beat_filter` doesn't exist.

- [ ] **Step 3: Implement**

Create `sidequest-server/sidequest/game/beat_filter.py`:

```python
"""Per-class beat filter — single source of truth for 'what can the player do this turn?'.

Per spec docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md §4.3.
This is the seam where future story #2 (B/X memorization) will plug in additional
named-spell gating for cast_spell — extend the filter, do not replace it.
"""
from __future__ import annotations

from sidequest.genre.error import PackError
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.rules import BeatDef, ConfrontationDef


def beats_available_for(
    confrontation: ConfrontationDef,
    class_def: ClassDef,
    spell_slots_remaining: float,
) -> list[BeatDef]:
    """Return the BeatDefs the given class can select this turn.

    Filter chain:
      1. class_filter on each beat (None = universal; non-empty = whitelist)
      2. class_def.encounter_beat_choices intersection (per-class whitelist)
      3. resource gates (cast_spell requires spell_slots_remaining >= 1.0)
    """
    if not class_def.encounter_beat_choices:
        raise PackError(
            f"class {class_def.display_name!r} has empty encounter_beat_choices"
        )

    pool: list[BeatDef] = []
    for beat in confrontation.beats:
        if beat.class_filter is not None and class_def.display_name not in beat.class_filter:
            continue
        if beat.id not in class_def.encounter_beat_choices:
            continue
        if beat.id == "cast_spell" and spell_slots_remaining < 1.0:
            continue
        pool.append(beat)
    return pool
```

If `sidequest/game/` does not have an `__init__.py` for module discovery, check before adding (it should — `game` is an existing package).

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_beat_filter.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/game/beat_filter.py tests/game/test_beat_filter.py
git commit -m "feat(game): beats_available_for helper — class filter + slot gate"
```

---

## Task 7: Wire `beats_available_for` into the beat-selection call site

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py:1983-1995` (and any sibling sites that iterate `confrontation.beats` directly for player-facing beat selection)
- Test: `sidequest-server/tests/server/test_apply_beat.py`

The narration_apply file has direct iteration around lines 1983 and 1995 (`pack_beats={b.id: b for b in cdef.beats}`). Audit those sites and replace with the filtered helper for any path that produces *player-selectable* beats. Internal lookups (e.g., `pack_beats` dict for resolving an already-rolled beat by ID) should stay unchanged — they need the full pool.

- [ ] **Step 1: Identify call sites**

```bash
cd sidequest-server && rg -n "cdef\.beats|confrontation\.beats" sidequest/server/narration_apply.py
```

For each match: classify as **selection** (player chooses a beat) or **lookup** (resolve a known beat ID). Selection sites get the helper; lookup sites do not.

- [ ] **Step 2: Write the failing test**

Append to `sidequest-server/tests/server/test_apply_beat.py`:

```python
def test_player_beat_selection_filtered_by_class(scenario_combat_with_class_filter):
    """Fighter must not see Mage-only cast_spell beat in available actions."""
    session = scenario_combat_with_class_filter(class_name="Fighter")
    available = session.player_available_beats()
    assert "cast_spell" not in [b.id for b in available]
    assert "attack" in [b.id for b in available]


def test_player_beat_selection_includes_class_signature(scenario_combat_with_class_filter):
    """Mage at full slots sees cast_spell in available actions."""
    session = scenario_combat_with_class_filter(class_name="Mage", spell_slots=1.0)
    available = session.player_available_beats()
    assert "cast_spell" in [b.id for b in available]
```

(Use existing test fixtures or extend conftest. The scenario fixture should produce a session whose `player_available_beats()` exposes the filter output. If no such API exists, the test exercises the filter via whatever method the call site uses — adapt to the existing test style.)

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k "filtered_by_class or class_signature"
```

Expected: FAIL — selection currently exposes all beats regardless of class.

- [ ] **Step 4: Replace direct iteration at selection sites**

Import at top of `sidequest-server/sidequest/server/narration_apply.py`:

```python
from sidequest.game.beat_filter import beats_available_for
```

For each **selection** site identified in Step 1, replace the direct iteration with:

```python
available_beats = beats_available_for(
    cdef,
    class_def_for(character),  # or however the file already obtains ClassDef
    spell_slots_remaining=character.resources.spell_slots,
)
```

If `class_def_for(character)` does not exist as a helper, locate the existing pattern the file uses to resolve class info from a Character (likely `genre_pack.classes_by_name[character.char_class]`) and inline that. Do not introduce a new helper unless the call repeats more than twice.

The two **lookup** sites at 1983 / 1995 (`pack_beats={b.id: b for b in cdef.beats}`) stay unchanged — they're used to resolve a beat by ID after roll, not to present options.

- [ ] **Step 5: Run all narration_apply tests to verify no regression**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v
```

Expected: all PASS, including the two new tests.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/server/narration_apply.py tests/server/test_apply_beat.py
git commit -m "feat(narration): filter player-selectable beats by class via beats_available_for"
```

---

## Task 8: Create `maybe_check_morale` function

**Files:**
- Create: `sidequest-server/sidequest/game/morale.py`
- Test: `sidequest-server/tests/game/test_morale.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_morale.py`:

```python
"""Tests for maybe_check_morale — B/X 2d6 morale check, side-level outcome."""
import random

import pytest

from sidequest.game.morale import (
    MoraleOutcome,
    OpponentSideState,
    OpponentState,
    maybe_check_morale,
)
from sidequest.genre.models.rules import (
    ConfrontationDef,
    FleeConsequence,
    MetricDef,
    MoraleDef,
    MoraleTrigger,
    BeatDef,
    BeatKind,
)


def _confrontation(*, morale=None):
    return ConfrontationDef(
        type="combat", label="C", category="combat",
        player_metric=MetricDef(name="m", starting=0, threshold=7),
        opponent_metric=MetricDef(name="m", starting=0, threshold=7),
        beats=[BeatDef(id="attack", label="A", kind=BeatKind.strike, stat_check="STR")],
        morale=morale,
    )


def _side(opponents):
    return OpponentSideState(label="goblins", opponents=opponents)


def _opp(id_, *, mindless=False, alive=True, is_leader=False):
    return OpponentState(id=id_, mindless=mindless, alive=alive, is_leader=is_leader)


def _morale(score=8, triggers=None, flee=FleeConsequence.chase):
    return MoraleDef(
        score=score,
        triggers=triggers or [MoraleTrigger.first_blood, MoraleTrigger.half_killed],
        flee_consequence=flee,
    )


def test_no_morale_block_returns_stay():
    cd = _confrontation(morale=None)
    out = maybe_check_morale(cd, _side([_opp("g1")]), MoraleTrigger.first_blood, random.Random(0))
    assert out is MoraleOutcome.stay


def test_trigger_not_in_morale_returns_stay():
    cd = _confrontation(morale=_morale(triggers=[MoraleTrigger.first_blood]))
    out = maybe_check_morale(
        cd, _side([_opp("g1")]), MoraleTrigger.intimidated, random.Random(0)
    )
    assert out is MoraleOutcome.stay


def test_total_le_score_returns_stay():
    cd = _confrontation(morale=_morale(score=8))
    # random.Random with seed → produces a known sequence; this seed yields 2d6 total ≤ 8
    rng = random.Random(42)
    out = maybe_check_morale(cd, _side([_opp("g1")]), MoraleTrigger.first_blood, rng)
    assert out is MoraleOutcome.stay


def test_total_gt_score_returns_flee():
    cd = _confrontation(morale=_morale(score=2))  # almost always > 2
    rng = random.Random(42)
    out = maybe_check_morale(cd, _side([_opp("g1")]), MoraleTrigger.first_blood, rng)
    assert out is MoraleOutcome.flee


def test_all_mindless_side_returns_stay_regardless_of_roll():
    cd = _confrontation(morale=_morale(score=2))
    # All mindless — even a guaranteed-flee roll must return stay
    side = _side([_opp("s1", mindless=True), _opp("s2", mindless=True)])
    out = maybe_check_morale(cd, side, MoraleTrigger.first_blood, random.Random(0))
    assert out is MoraleOutcome.stay


def test_mixed_mindless_side_rolls_for_non_mindless_only():
    cd = _confrontation(morale=_morale(score=2))
    side = _side([
        _opp("s1", mindless=True),     # stays no matter what
        _opp("g1", mindless=False),    # rolls; almost certainly flees
    ])
    out = maybe_check_morale(cd, side, MoraleTrigger.first_blood, random.Random(42))
    assert out is MoraleOutcome.flee
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_morale.py -v
```

Expected: import error — `sidequest.game.morale` doesn't exist.

- [ ] **Step 3: Implement**

Create `sidequest-server/sidequest/game/morale.py`:

```python
"""B/X morale check (2d6 vs MoraleDef.score).

Per spec docs/superpowers/specs/2026-05-08-cnc-bx-class-beats-morale-design.md §4.4.
Pure function — no side effects, no game-state mutation. Caller applies
the outcome (chase escalation / surrender / rout) per ConfrontationDef.morale.flee_consequence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from random import Random

from sidequest.genre.models.rules import (
    ConfrontationDef,
    MoraleTrigger,
)


class MoraleOutcome(StrEnum):
    stay = "stay"
    flee = "flee"


@dataclass(frozen=True)
class OpponentState:
    """Minimal per-opponent snapshot for morale evaluation."""

    id: str
    mindless: bool = False
    alive: bool = True
    is_leader: bool = False


@dataclass(frozen=True)
class OpponentSideState:
    label: str
    opponents: list[OpponentState] = field(default_factory=list)


def maybe_check_morale(
    confrontation: ConfrontationDef,
    opponent_side: OpponentSideState,
    trigger: MoraleTrigger,
    rng: Random,
) -> MoraleOutcome:
    """Roll 2d6 vs MoraleDef.score. Stay if total ≤ score; flee if >.

    No-op (Stay) if confrontation.morale is None or trigger not in morale.triggers.
    Sides composed entirely of mindless opponents always Stay (B/X canon — no
    Intelligence score, no morale check). Mixed sides roll once for the
    non-mindless cohort; mindless members keep fighting on a Flee outcome
    (handled by the caller, not this function).
    """
    morale = confrontation.morale
    if morale is None or trigger not in morale.triggers:
        return MoraleOutcome.stay

    living = [o for o in opponent_side.opponents if o.alive]
    non_mindless = [o for o in living if not o.mindless]
    if not non_mindless:
        return MoraleOutcome.stay

    total = rng.randint(1, 6) + rng.randint(1, 6)
    return MoraleOutcome.stay if total <= morale.score else MoraleOutcome.flee
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_morale.py -v
```

Expected: 6 PASS. If a test relies on `random.Random(42)` producing a specific 2d6 sequence and the actual sequence differs, replace the seed-based assertion with an injected fake RNG (e.g., a class with a deterministic `randint` queue). Adjust both test and (if needed) the function signature to accept a callable.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/game/morale.py tests/game/test_morale.py
git commit -m "feat(game): maybe_check_morale — B/X 2d6 morale check (pure function)"
```

---

## Task 9: Emit auto-fired morale triggers from `narration_apply`

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Test: `sidequest-server/tests/server/test_apply_beat.py`

Auto triggers: `first_blood`, `half_killed`, `leader_killed`. Each fires from a **single emission point** after a beat resolution that downs an opponent.

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/server/test_apply_beat.py`:

```python
def test_first_blood_fires_once_per_side(scenario_two_goblins):
    """first_blood emits exactly once when the first opponent goes down."""
    session = scenario_two_goblins(rng_seed=0)
    session.advance_beat_kill_one_opponent()
    assert session.morale_events_emitted == [("first_blood", "goblins")]
    session.advance_beat_kill_one_opponent()  # second kill — no first_blood again
    assert session.morale_events_emitted.count(("first_blood", "goblins")) == 1


def test_half_killed_fires_when_side_crosses_half(scenario_four_goblins):
    """half_killed fires when standing opponents drop to ⌊initial/2⌋ = 2."""
    session = scenario_four_goblins(rng_seed=0)
    session.advance_beat_kill_one_opponent()  # 3 left
    session.advance_beat_kill_one_opponent()  # 2 left → half_killed
    assert ("half_killed", "goblins") in session.morale_events_emitted


def test_leader_killed_fires_only_for_tagged_leader(scenario_leader_and_grunts):
    session = scenario_leader_and_grunts(rng_seed=0)
    session.advance_beat_kill_grunt()
    assert "leader_killed" not in [t for (t, _) in session.morale_events_emitted]
    session.advance_beat_kill_leader()
    assert ("leader_killed", "warband") in session.morale_events_emitted
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k "first_blood or half_killed or leader_killed"
```

Expected: FAIL — no morale emission yet.

- [ ] **Step 3: Implement**

In `sidequest-server/sidequest/server/narration_apply.py`, locate the function that processes opponent KO state changes (probably the section that updates opponent_actor.alive after damage application). Add a helper near the top of the module:

```python
from random import Random

from sidequest.game.morale import (
    MoraleOutcome,
    OpponentSideState,
    OpponentState,
    maybe_check_morale,
)
from sidequest.genre.models.rules import MoraleTrigger


def _emit_morale_triggers(
    session,
    confrontation,
    opponent_side_label: str,
    pre_kill_state: list[OpponentState],
    post_kill_state: list[OpponentState],
    killed_was_leader: bool,
    rng: Random,
) -> list[tuple[MoraleTrigger, MoraleOutcome]]:
    """Detect and fire first_blood, half_killed, leader_killed in one pass.
    Returns (trigger, outcome) tuples for downstream chase/surrender/rout dispatch."""
    fired: list[tuple[MoraleTrigger, MoraleOutcome]] = []

    pre_alive = sum(1 for o in pre_kill_state if o.alive)
    post_alive = sum(1 for o in post_kill_state if o.alive)
    initial = len(pre_kill_state)
    side = OpponentSideState(label=opponent_side_label, opponents=post_kill_state)

    triggers_to_check: list[MoraleTrigger] = []
    if pre_alive == initial and post_alive == initial - 1:
        triggers_to_check.append(MoraleTrigger.first_blood)
    if post_alive <= initial // 2 < pre_alive:
        triggers_to_check.append(MoraleTrigger.half_killed)
    if killed_was_leader:
        triggers_to_check.append(MoraleTrigger.leader_killed)

    for trig in triggers_to_check:
        outcome = maybe_check_morale(confrontation, side, trig, rng)
        fired.append((trig, outcome))
        session.record_morale_event(trig, opponent_side_label, outcome)
    return fired
```

(The exact `session` API to record events depends on the existing infrastructure. If no recording API exists, store on a session attribute the test fixture exposes.)

Find the call site immediately after opponent KO is applied. Insert:

```python
fired = _emit_morale_triggers(
    session,
    cdef,
    opponent_side_label=cdef.label,  # or whichever label the file already uses
    pre_kill_state=opponents_before,
    post_kill_state=opponents_after,
    killed_was_leader=ko_was_leader_flag,
    rng=session.rng,  # use existing session RNG
)
```

If the surrounding code does not already track `pre_kill_state` and `post_kill_state`, snapshot them right before/after the damage-application block.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k "first_blood or half_killed or leader_killed"
```

Expected: 3 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/server/narration_apply.py tests/server/test_apply_beat.py
git commit -m "feat(narration): emit first_blood / half_killed / leader_killed morale triggers"
```

---

## Task 10: Sidecar-driven `intimidated` trigger

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (sidecar parsing path)
- Test: `sidequest-server/tests/server/test_apply_beat.py`

Per ADR-039, the narrator emits a JSON sidecar block alongside prose. The `intimidated` trigger is fired when the sidecar carries `morale_event: intimidated`.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/server/test_apply_beat.py`:

```python
def test_intimidated_fires_when_sidecar_signals(scenario_combat_with_morale):
    """Narrator JSON sidecar `morale_event: intimidated` fires the trigger."""
    session = scenario_combat_with_morale(rng_seed=0)
    sidecar = {"morale_event": "intimidated"}
    session.apply_narrator_sidecar(sidecar)
    assert ("intimidated", session.opponent_side_label) in [
        (t, l) for (t, l) in session.morale_events_emitted
    ]


def test_intimidated_ignored_when_no_morale_block(scenario_combat_no_morale):
    session = scenario_combat_no_morale(rng_seed=0)
    sidecar = {"morale_event": "intimidated"}
    session.apply_narrator_sidecar(sidecar)
    assert session.morale_events_emitted == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k intimidated
```

Expected: FAIL — sidecar handler doesn't process `morale_event`.

- [ ] **Step 3: Implement**

Locate the sidecar parsing path (search for an existing handler for sidecar fields — `rg "sidecar" sidequest/server/narration_apply.py`). Add handling for the `morale_event` key:

```python
sidecar_morale_event = sidecar.get("morale_event") if sidecar else None
if sidecar_morale_event == "intimidated":
    # Caller already snapshotted opponent state for this turn
    side = OpponentSideState(
        label=current_opponent_side_label,
        opponents=current_opponents_snapshot,
    )
    outcome = maybe_check_morale(
        cdef, side, MoraleTrigger.intimidated, session.rng
    )
    session.record_morale_event(MoraleTrigger.intimidated, current_opponent_side_label, outcome)
elif sidecar_morale_event is not None:
    # Loud-fail on unknown sidecar morale_event values to surface narrator drift early.
    raise ValueError(
        f"narrator sidecar morale_event={sidecar_morale_event!r} not recognized"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k intimidated
```

Expected: 2 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/server/narration_apply.py tests/server/test_apply_beat.py
git commit -m "feat(narration): sidecar-driven intimidated morale trigger (ADR-039)"
```

---

## Task 11: Apply `flee_consequence` outcomes

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py`
- Test: `sidequest-server/tests/server/test_apply_beat.py`

When a morale check returns `flee`, the caller applies the consequence per `morale.flee_consequence`: `chase` (escalate to chase confrontation), `surrender` (combat ends, opponents drop weapons), `rout` (combat ends, scattered).

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/server/test_apply_beat.py`:

```python
def test_flee_consequence_chase_escalates(scenario_combat_morale_flee_chase):
    session = scenario_combat_morale_flee_chase(rng_seed=42)  # seed → flee
    session.advance_beat_kill_one_opponent()
    assert session.confrontation_type_after == "chase"


def test_flee_consequence_surrender_ends_combat(scenario_combat_morale_flee_surrender):
    session = scenario_combat_morale_flee_surrender(rng_seed=42)
    session.advance_beat_kill_one_opponent()
    assert session.confrontation_ended is True
    assert session.opponents_disposition == "surrendered"


def test_flee_consequence_rout_ends_combat(scenario_combat_morale_flee_rout):
    session = scenario_combat_morale_flee_rout(rng_seed=42)
    session.advance_beat_kill_one_opponent()
    assert session.confrontation_ended is True
    assert session.opponents_disposition == "routed"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k flee_consequence
```

Expected: FAIL — outcome not applied yet.

- [ ] **Step 3: Implement**

In `narration_apply.py`, after the auto-trigger emission block from Task 9 and the sidecar branch from Task 10, add a single dispatcher that consumes the `fired` list:

```python
from sidequest.genre.models.rules import FleeConsequence


def _apply_flee_consequences(
    session,
    cdef,
    fired: list[tuple[MoraleTrigger, MoraleOutcome]],
) -> None:
    if not any(outcome is MoraleOutcome.flee for _, outcome in fired):
        return
    consequence = cdef.morale.flee_consequence
    if consequence is FleeConsequence.chase:
        session.escalate_to("chase")
    elif consequence is FleeConsequence.surrender:
        session.end_confrontation(disposition="surrendered")
    elif consequence is FleeConsequence.rout:
        session.end_confrontation(disposition="routed")
    else:
        raise ValueError(f"unknown flee_consequence: {consequence!r}")
```

Call `_apply_flee_consequences(session, cdef, fired)` at the end of the morale-emission block (Task 9) and after the sidecar `intimidated` branch (Task 10) — collect both into a single `fired` list before the dispatcher.

`session.escalate_to` / `session.end_confrontation` are existing session-API methods — locate them via `rg "def escalate_to|def end_confrontation" sidequest/`. If the names differ, adapt.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd sidequest-server && uv run pytest tests/server/test_apply_beat.py -v -k flee_consequence
```

Expected: 3 PASS.

- [ ] **Step 5: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/server/narration_apply.py tests/server/test_apply_beat.py
git commit -m "feat(narration): apply flee_consequence (chase / surrender / rout)"
```

---

## Task 12: Add `confrontation.beat_filter` and `confrontation.morale_check` OTEL spans

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/combat.py`
- Modify: `sidequest-server/sidequest/game/beat_filter.py` (emit beat_filter span)
- Modify: `sidequest-server/sidequest/game/morale.py` (emit morale_check span)
- Test: `sidequest-server/tests/telemetry/test_combat_spans.py` (new or extend existing)

- [ ] **Step 1: Write the failing tests**

Create or extend `sidequest-server/tests/telemetry/test_combat_spans.py`:

```python
"""Tests for new combat OTEL spans: beat_filter, morale_check."""
import pytest

from sidequest.telemetry.spans.combat import (
    SPAN_BEAT_FILTER,
    SPAN_MORALE_CHECK,
)
from sidequest.telemetry.spans._core import SPAN_ROUTES


def test_span_constants_declared():
    assert SPAN_BEAT_FILTER == "confrontation.beat_filter"
    assert SPAN_MORALE_CHECK == "confrontation.morale_check"


def test_beat_filter_span_route_registered():
    route = SPAN_ROUTES.get(SPAN_BEAT_FILTER)
    assert route is not None
    assert route.component == "combat"


def test_morale_check_span_route_registered():
    route = SPAN_ROUTES.get(SPAN_MORALE_CHECK)
    assert route is not None
    assert route.component == "combat"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_combat_spans.py -v
```

Expected: FAIL — span constants don't exist.

- [ ] **Step 3: Add span declarations**

In `sidequest-server/sidequest/telemetry/spans/combat.py`, after the existing `SPAN_COMBAT_ENDED` block, add:

```python
SPAN_BEAT_FILTER = "confrontation.beat_filter"
SPAN_ROUTES[SPAN_BEAT_FILTER] = SpanRoute(
    event_type="state_inspection",
    component="combat",
    extract=lambda span: {
        "field": "beat_filter",
        "character_class": (span.attributes or {}).get("character_class", ""),
        "confrontation_type": (span.attributes or {}).get("confrontation_type", ""),
        "pool_size": (span.attributes or {}).get("pool_size", 0),
        "filtered_size": (span.attributes or {}).get("filtered_size", 0),
        "beat_ids": (span.attributes or {}).get("beat_ids", ""),
        "mindless_opponents_count": (span.attributes or {}).get("mindless_opponents_count", 0),
    },
)

SPAN_MORALE_CHECK = "confrontation.morale_check"
SPAN_ROUTES[SPAN_MORALE_CHECK] = SpanRoute(
    event_type="state_transition",
    component="combat",
    extract=lambda span: {
        "field": "morale_check",
        "trigger": (span.attributes or {}).get("trigger", ""),
        "score": (span.attributes or {}).get("score", 0),
        "roll": (span.attributes or {}).get("roll", ""),
        "total": (span.attributes or {}).get("total", 0),
        "outcome": (span.attributes or {}).get("outcome", ""),
        "opponent_side_label": (span.attributes or {}).get("opponent_side_label", ""),
        "mindless_opponents_count": (span.attributes or {}).get("mindless_opponents_count", 0),
        "flee_consequence": (span.attributes or {}).get("flee_consequence", ""),
    },
)
```

(`event_type` values must match the project's existing convention — check the existing `SPAN_COMBAT_TICK` route for reference. Use `state_transition` for spans that record a change; `state_inspection` for read-only filter spans. If the project does not have a `state_inspection` event_type, use the closest existing value.)

- [ ] **Step 4: Emit `beat_filter` span from `beats_available_for`**

In `sidequest-server/sidequest/game/beat_filter.py`, wrap the body in a span emission. Add at the top:

```python
from opentelemetry import trace

from sidequest.telemetry.spans.combat import SPAN_BEAT_FILTER

_tracer = trace.get_tracer(__name__)
```

Wrap the function body:

```python
def beats_available_for(...):
    with _tracer.start_as_current_span(SPAN_BEAT_FILTER) as span:
        # ... existing body ...
        span.set_attribute("character_class", class_def.display_name)
        span.set_attribute("confrontation_type", confrontation.confrontation_type)
        span.set_attribute("pool_size", len(confrontation.beats))
        span.set_attribute("filtered_size", len(pool))
        span.set_attribute("beat_ids", ",".join(b.id for b in pool))
        # mindless_opponents_count is unavailable here — caller passes it via context
        # if needed; default 0 for now (filter doesn't see opponent state).
        return pool
```

(Pass `mindless_opponents_count` only if straightforward to thread through. If not, leave the attr at 0 — the morale_check span carries the same data and is the primary lie-detector for mindless logic.)

- [ ] **Step 5: Emit `morale_check` span from `maybe_check_morale`**

In `sidequest-server/sidequest/game/morale.py`, wrap the function body:

```python
from opentelemetry import trace

from sidequest.telemetry.spans.combat import SPAN_MORALE_CHECK

_tracer = trace.get_tracer(__name__)


def maybe_check_morale(...):
    with _tracer.start_as_current_span(SPAN_MORALE_CHECK) as span:
        morale = confrontation.morale
        span.set_attribute("trigger", trigger.value)
        span.set_attribute("opponent_side_label", opponent_side.label)

        if morale is None or trigger not in morale.triggers:
            span.set_attribute("outcome", MoraleOutcome.stay.value)
            span.set_attribute("score", 0)
            span.set_attribute("total", 0)
            return MoraleOutcome.stay

        living = [o for o in opponent_side.opponents if o.alive]
        non_mindless = [o for o in living if not o.mindless]
        span.set_attribute("mindless_opponents_count", len(living) - len(non_mindless))
        if not non_mindless:
            span.set_attribute("outcome", MoraleOutcome.stay.value)
            return MoraleOutcome.stay

        d1, d2 = rng.randint(1, 6), rng.randint(1, 6)
        total = d1 + d2
        outcome = MoraleOutcome.stay if total <= morale.score else MoraleOutcome.flee
        span.set_attribute("score", morale.score)
        span.set_attribute("roll", f"{d1}+{d2}")
        span.set_attribute("total", total)
        span.set_attribute("outcome", outcome.value)
        span.set_attribute("flee_consequence", morale.flee_consequence.value)
        return outcome
```

- [ ] **Step 6: Run all relevant tests**

```bash
cd sidequest-server && uv run pytest tests/telemetry/test_combat_spans.py tests/game/test_morale.py tests/game/test_beat_filter.py -v
```

Expected: all PASS, including the original Task 6 + Task 8 tests still passing under span instrumentation.

- [ ] **Step 7: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/telemetry/spans/combat.py sidequest/game/beat_filter.py sidequest/game/morale.py tests/telemetry/test_combat_spans.py
git commit -m "feat(otel): beat_filter and morale_check spans for combat lie-detector"
```

---

## Task 13: Narrator prompt zone invariant

**Files:**
- Modify: `sidequest-server/sidequest/agents/narrator.py` (per-turn context-builder, ADR-009 attention zone)
- Test: `sidequest-server/tests/agents/test_narrator_prompt.py` (locate existing pattern; or extend)

Per spec §4.7: add a one-line invariant under the per-turn available-actions zone telling the narrator not to perform actions outside the listed available beats.

- [ ] **Step 1: Locate the per-turn prompt zone**

```bash
cd sidequest-server && rg -n "available.*action|player.*action|beat" sidequest/agents/narrator.py | head -20
```

Identify the section where the prompt enumerates the player's selectable beats for the current turn.

- [ ] **Step 2: Write the failing test**

Append to or create `sidequest-server/tests/agents/test_narrator_prompt.py`:

```python
def test_narrator_per_turn_prompt_includes_action_invariant(narrator_prompt_for_combat_turn):
    """The per-turn prompt zone tells the narrator not to perform unlisted actions."""
    prompt = narrator_prompt_for_combat_turn()
    assert "Do not narrate actions outside that list as performed" in prompt
```

(Use whatever fixture or helper builds a per-turn prompt for combat. If no such helper exists, the test exercises the smallest unit available — likely a `build_turn_prompt(...)` function inside narrator.py.)

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator_prompt.py -v -k action_invariant
```

Expected: FAIL — string not present.

- [ ] **Step 4: Add the invariant**

In `narrator.py`, in the section identified in Step 1 — after the line that enumerates available actions — add:

```python
prompt_block += (
    "\nThe player's available actions for this turn are listed above. "
    "Do not narrate actions outside that list as performed.\n"
)
```

(Adapt to the actual prompt-building style of the file. The exact phrasing must match the test assertion.)

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/agents/test_narrator_prompt.py -v -k action_invariant
```

Expected: PASS.

- [ ] **Step 6: Format, lint, commit**

```bash
cd sidequest-server && uv run ruff format . && uv run ruff check .
git add sidequest/agents/narrator.py tests/agents/test_narrator_prompt.py
git commit -m "feat(narrator): per-turn invariant — do not narrate unlisted actions (ADR-009)"
```

---

## Task 14: Content — `rules.yaml` re-tag + new beats + morale + housekeeping

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`

This is content-side authoring. The server changes from Tasks 1–13 must be merged first (they validate against this content).

- [ ] **Step 1: Verify server merge prerequisite**

```bash
cd sidequest-server && git log --oneline -20 | grep -E "class_filter|MoraleDef|beats_available_for|morale check" | head
```

Expected: at least the model + helper commits appear. If empty, stop and finish server tasks.

- [ ] **Step 2: Re-tag existing beats in `combat` confrontation**

In `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`, find the `combat` confrontation and modify two existing beats:

```yaml
- id: shield_bash
  ...
  class_filter: [Fighter, Cleric]   # NEW

- id: feint
  ...
  class_filter: [Fighter, Thief]    # NEW
```

Leave `attack`, `defend`, `flee` without `class_filter` (universal).

- [ ] **Step 3: Add 8 new beats to the `combat` confrontation `beats:` list**

Append to the same `beats:` list:

```yaml
  - id: cleave
    label: Cleave
    kind: strike
    base: 3
    stat_check: STR
    class_filter: [Fighter]
    effect: "Wide swing — opens up space against multiple foes"
    narrator_hint: "Two-handed sweep, momentum carrying through to the next stance."
  - id: parry
    label: Parry
    kind: brace
    base: 2
    stat_check: DEX
    class_filter: [Fighter]
    effect: "Trade momentum for a guarantee — turn the next blow aside"
    narrator_hint: "Steel meets steel, deflecting just enough."
  - id: backstab
    label: Backstab
    kind: strike
    base: 4
    stat_check: DEX
    target_tag: "Off-Balance"
    class_filter: [Thief]
    risk: "Requires Off-Balance setup — wasted swing without it"
    effect: "Out of the dark, blade between ribs"
    narrator_hint: "Shadow into the gap, blade going in where armor stops."
  - id: sneak
    label: Slip Behind
    kind: angle
    target_tag: "Off-Balance"
    stat_check: DEX
    class_filter: [Thief]
    effect: "Set up an Off-Balance tag the next backstab can spend"
    narrator_hint: "A step into the side passage, gone before the lantern catches."
  - id: cast_cantrip
    label: Cast Cantrip
    kind: strike
    base: 1
    stat_check: INT
    class_filter: [Mage]
    effect: "A small working — a glamour, a spark, a trick"
    narrator_hint: "A flick of the wrist, a syllable too brief to catch."
  - id: cast_spell
    label: Cast Spell
    kind: strike
    base: 4
    stat_check: INT
    class_filter: [Mage]
    risk: "Consumes a spell slot; without one, the verb does not exist"
    effect: "The prepared spell unspools — page burns or memory empties"
    narrator_hint: "The morning's memorized syllables, spent in one pass."
  - id: turn_undead
    label: Turn Undead
    kind: push
    base: 3
    stat_check: WIS
    class_filter: [Cleric]
    effect: "Drives the dead off the field"
    narrator_hint: "Holy symbol raised; the unliving recoil from the will behind it."
  - id: pray
    label: Pray for Aid
    kind: brace
    base: 1
    stat_check: WIS
    class_filter: [Cleric]
    edge_delta: 1
    effect: "The saint listens, briefly — composure returns"
    narrator_hint: "A whispered name, an answered breath."
```

- [ ] **Step 4: Add `morale` block to the `combat` confrontation**

Add a sibling key under the `combat` confrontation (alongside `mood: combat`):

```yaml
    morale:
      score: 8
      triggers: [first_blood, half_killed, intimidated, leader_killed]
      flee_consequence: chase
```

- [ ] **Step 5: Sync `allowed_classes` and drop stale `custom_rules` flags**

Replace the `allowed_classes` line:

```yaml
allowed_classes:
  - Fighter
  - Mage
  - Cleric
  - Thief
```

In `custom_rules:`, **remove** these three lines:

```yaml
  no_classes: "true"      # DELETE
  no_races: "true"        # DELETE
  no_spells: "true"       # DELETE
```

Keep `treasure_as_xp`, `keeper_awareness`, `resource_ticks`, `extraction_phase`, `encumbrance`, `injuries`.

- [ ] **Step 6: Run pack-load tests against the modified content**

From the orchestrator, set the pack path env var if not already set, and run:

```bash
cd sidequest-server && SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run pytest tests/genre/test_pack_load.py -v
```

Expected: all PASS, including the new C&C-specific assertions added in Task 5.

- [ ] **Step 7: Commit (in content repo)**

```bash
cd sidequest-content && git add genre_packs/caverns_and_claudes/rules.yaml
cd sidequest-content && git commit -m "feat(c&c): B/X class beats + morale block in combat confrontation"
```

---

## Task 15: Content — `classes.yaml` encounter_beat_choices + magic_access

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`

- [ ] **Step 1: Update each of the four classes**

Replace the four class entries with:

```yaml
- id: fighter
  display_name: Fighter
  rpg_role: tank
  jungian_default: hero
  prime_requisite: STR
  minimum_score: 9
  kit_table: fighter_kit
  flavor: >-
    Plate, polearm, and the patience to be hit first.
  encounter_beat_choices:
    - attack
    - defend
    - flee
    - shield_bash
    - cleave
    - parry
    - feint
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
  encounter_beat_choices:
    - attack
    - defend
    - flee
    - cast_cantrip
    - cast_spell
  magic_access: innate_v1

- id: cleric
  display_name: Cleric
  rpg_role: healer
  jungian_default: caregiver
  prime_requisite: WIS
  minimum_score: 9
  kit_table: cleric_kit
  flavor: >-
    Holy symbol, war-mace, and a faith that is mostly working so far.
  encounter_beat_choices:
    - attack
    - defend
    - flee
    - shield_bash
    - turn_undead
    - pray
  magic_access: innate_v1

- id: thief
  display_name: Thief
  rpg_role: stealth
  jungian_default: outlaw
  prime_requisite: DEX
  minimum_score: 9
  kit_table: thief_kit
  flavor: >-
    Lockpicks, leather, and a professional interest in being elsewhere.
  encounter_beat_choices:
    - attack
    - defend
    - flee
    - feint
    - backstab
    - sneak
  magic_access: null
```

- [ ] **Step 2: Run pack-load tests**

```bash
cd sidequest-server && SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run pytest tests/genre/test_pack_load.py -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
cd sidequest-content && git add genre_packs/caverns_and_claudes/classes.yaml
cd sidequest-content && git commit -m "feat(c&c): per-class encounter_beat_choices + magic_access (B/X port)"
```

---

## Task 16: Content — `caverns_sunden` archetype `mindless` tags

**Files:**
- Modify: archetype YAML files under `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/`

- [ ] **Step 1: Locate archetype files**

```bash
cd sidequest-content && find genre_packs/caverns_and_claudes/worlds/caverns_sunden -name "*.yaml" | xargs grep -l "role:" | head
```

Identify which files declare archetypes (often `npcs.yaml`, `archetypes.yaml`, or world-specific files).

- [ ] **Step 2: Tag the qualifying archetypes**

For every archetype matching one of these categories, add `mindless: true` as a top-level field on the archetype entry:

- Skeletons
- Zombies
- Animated armor / animated objects
- Oozes / slimes
- Golems / constructs
- Mind-controlled thralls (non-sapient)

Leave default (`mindless: false` implicit) for: goblins, kobolds, brigands, cultists, dragons, mages, beast-NPCs with self-preservation, anything sapient or self-directed.

Example edit:

```yaml
- id: skeleton_warrior
  role: enemy
  mindless: true   # NEW — B/X morale bypass
  ...
```

- [ ] **Step 3: Run pack-load tests**

```bash
cd sidequest-server && SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs uv run pytest tests/genre/test_pack_load.py -v
```

Expected: all PASS (mindless flag is opt-in; no existing archetypes are invalidated).

- [ ] **Step 4: Commit**

```bash
cd sidequest-content && git add genre_packs/caverns_and_claudes/worlds/caverns_sunden/
cd sidequest-content && git commit -m "feat(caverns_sunden): mindless: true on undead/automaton archetypes"
```

---

## Task 17: Playtest exit verification

**Files:**
- No edits — this task is verification only.

Per spec §5.6, the story is done when these four observations are confirmed against a live `caverns_sunden` playtest.

- [ ] **Step 1: Boot the stack**

```bash
just up
```

Expected: server (8765), client (5173), daemon all up; logs tee'd to `/tmp/sidequest-*.log`.

- [ ] **Step 2: Open the GM dashboard**

```bash
just otel
```

Expected: dashboard at `http://localhost:8765/dashboard`.

- [ ] **Step 3: Run a scripted playtest in caverns_sunden**

```bash
just playtest --genre caverns_and_claudes --world caverns_sunden
```

Pick a Fighter; trigger a multi-NPC combat against a goblin warband (≥ 4 opponents).

- [ ] **Step 4: Verify exit criterion 1 — class-distinct beat menus**

Switch through Fighter / Mage / Cleric / Thief characters (or run four separate playtests). For each, inspect the `confrontation.beat_filter` span attributes in the GM dashboard and confirm `beat_ids` differs per class — each shows their signature beats and not the others' (Fighter sees `cleave`; Mage does not).

- [ ] **Step 5: Verify exit criterion 2 — multi-NPC fight ends in flight or surrender**

In a 5-turn fight against goblins, observe at least one `confrontation.morale_check` span with `outcome: flee`. The narrator should describe the goblins breaking; the confrontation type should transition to `chase` (per `flee_consequence: chase` in the C&C content).

- [ ] **Step 6: Verify exit criterion 3 — mindless skeletons do not check morale**

Trigger a combat against skeletons (or any archetype tagged `mindless: true`). Across 5 turns, confirm: no `confrontation.morale_check` spans fire on the skeleton side after KOs, OR the spans that do fire show `mindless_opponents_count` equal to the side total and `outcome: stay`.

- [ ] **Step 7: Verify exit criterion 4 — Mage `cast_spell` drops slot ledger**

As Mage with full slots (1.0), use `cast_spell` once. Confirm in the GM dashboard that the `spell_slots` ledger drops 1.0 → 0.0. After the drop, confirm `cast_spell` is no longer offered as an available action (filtered by `beats_available_for`'s slot gate).

- [ ] **Step 8: Record findings**

If any criterion fails, write a finding to `/Users/slabgorb/Projects/sq-playtest-pingpong.md` with severity, OTEL evidence (which span was missing or carried wrong values), steps to reproduce. Hand off to Dev to fix; rerun this task after the fix.

If all four pass, the story is verifiable-done.

---

## Self-review summary

**Spec coverage check:** Each numbered section of the spec maps to at least one task:
- §2.1 BeatDef.class_filter → Task 1
- §2.2 MoraleDef + enums → Task 2
- §2.3 ConfrontationDef.morale → Task 3
- §2.4 NpcArchetype.mindless → Task 4
- §3.1–§3.3 content rules.yaml → Task 14
- §3.2 classes.yaml → Task 15
- §3.4 caverns_sunden archetypes → Task 16
- §4.1 model changes → Tasks 1–4
- §4.2 pack-load validation → Task 5
- §4.3 beats_available_for → Tasks 6–7
- §4.4 maybe_check_morale + triggers → Tasks 8–11
- §4.5 cast_spell consumption → Task 6 (resource gate) + Task 7 (wired)
- §4.6 OTEL spans → Task 12
- §4.7 narrator prompt invariant → Task 13
- §5 testing strategy → embedded in Tasks 1–13
- §5.6 playtest exit criteria → Task 17

**Placeholder scan:** No `TBD`, `TODO`, "implement later", or "fill in details" remain. A few "if no fixture exists, adapt to the existing pattern" notes remain — these are unavoidable because the engineer does not have access to private fixtures from this writing context, and the surrounding code's testing conventions take precedence over guesses from this plan.

**Type consistency:** Method signatures and property names cross-check:
- `beats_available_for(confrontation, class_def, spell_slots_remaining)` — used identically in Task 6 (definition) and Task 7 (call site).
- `maybe_check_morale(confrontation, opponent_side, trigger, rng)` — used identically in Task 8 (definition), Task 9 (auto-triggers), Task 10 (intimidated), Task 12 (span instrumentation).
- `MoraleOutcome.stay` / `MoraleOutcome.flee` — consistent across Tasks 8–12.
- `_apply_flee_consequences(session, cdef, fired)` — Task 11 only.
- `_emit_morale_triggers(...)` — Task 9 only.
- `class_def.encounter_beat_choices` and `class_def.display_name` — consistent across Tasks 5–7.
- `confrontation.morale.score` / `.triggers` / `.flee_consequence` — consistent.

**Scope check:** Single coherent unit. 17 tasks, 3–5 estimated story points per the spec.
