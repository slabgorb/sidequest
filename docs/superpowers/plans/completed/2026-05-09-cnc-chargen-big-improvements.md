# C&C Chargen Big Improvements — Implementation Plan

> **COMPLETED via sprint stories — checkbox state never updated.** Six-scene flow ships in `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml`: `the_roll`, `the_arrangement`, `the_calling`, `the_story`, `the_kit`, `the_mouth`. UI: `sidequest-ui/src/components/CharacterCreation/{StatArrangePanel,StoryPanel}.tsx` with companion tests; `CharacterCreation.tsx` renders `stat_arrange` and `story` input_type branches. Server builder.py handles the `stat_arrange` input_type at line 1302 and emits `SPAN_CHARGEN_BACKSTORY_COMPOSED` for the autogen step. Server-side dispatch tests: `test_chargen_arrange_dispatch.py`, `test_chargen_story_dispatch.py`, `test_45_2_chargen_to_playing_wire.py`. Plan body left intact as historical reference.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace C&C's silent stat-generation flow with player-visible 3d6 rolls, click-to-assign stat arrangement with a live-qualifying class panel, a folded story scene (pronouns + background + description with autogen), and reject-and-reroll. Drop prime-requisite XP and the manual-edit Pencil affordance.

**Architecture:** Six-scene flow keyed off `caverns_and_claudes/char_creation.yaml`. New `MechanicalEffects` fields (`assignment_required`, `allow_reject`, `identity_capture`, `background_autogen_source`) drive the builder FSM. New `ARRANGING` and `STORY` builder states replace the silent reroll loop and the today's pronouns scene. UI gets two new render branches in `CharacterCreation.tsx` (`stat_arrange`, `story`). Dice rolls go through ADR-074 with graceful numeric-reveal degrade.

**Tech Stack:** Python 3.12 (sidequest-server, pydantic, FastAPI, opentelemetry), TypeScript/React 18 (sidequest-ui, Vitest), YAML (sidequest-content).

**Spec:** `docs/superpowers/specs/2026-05-09-cnc-chargen-big-improvements-design.md`

**Repo branching:** All PRs target `develop` per `repos.yaml`. Three sub-PRs:
- `sidequest-server` — server FSM + protocol + cleanup
- `sidequest-ui` — UI render branches + Pencil removal
- `sidequest-content` — `caverns_and_claudes` YAML changes

---

## Phase 0 — Branches and shared scaffolding

### Task 0.1: Create feature branches

**Files:**
- Modify: working directories of `sidequest-server`, `sidequest-ui`, `sidequest-content`

- [ ] **Step 1: Create three feature branches**

```bash
cd sidequest-server && git checkout develop && git pull && git checkout -b feat/cnc-chargen-visible-dice && cd ..
cd sidequest-ui && git checkout develop && git pull && git checkout -b feat/cnc-chargen-visible-dice && cd ..
cd sidequest-content && git checkout develop && git pull && git checkout -b feat/cnc-chargen-visible-dice && cd ..
```

- [ ] **Step 2: Verify clean state**

```bash
just status
```

Expected: three repos on `feat/cnc-chargen-visible-dice`, working trees clean.

---

## Phase 1 — Content schema extensions (sidequest-server)

The `MechanicalEffects` pydantic model gates which YAML keys are recognized. We add the new keys here so all subsequent server work has a real schema to validate against.

### Task 1.1: Read current `MechanicalEffects` shape

**Files:**
- Read: `sidequest-server/sidequest/genre/models/character.py`

- [ ] **Step 1: Open and study `MechanicalEffects`**

Locate the class definition. Note current fields (`stat_generation`, `class_qualification_loop`, `equipment_generation`, `class_hint`, `pronoun_hint`, etc.). Note `model_config = {"extra": "forbid"}` — adding new keys requires extending the model.

### Task 1.2: Add `IdentityCapture` and `MechanicalEffects` fields

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py`
- Test: `sidequest-server/tests/genre/test_mechanical_effects.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_mechanical_effects.py
from sidequest.genre.models.character import MechanicalEffects, IdentityCapture


def test_assignment_required_field_accepted():
    eff = MechanicalEffects(assignment_required=True)
    assert eff.assignment_required is True


def test_allow_reject_field_accepted():
    eff = MechanicalEffects(allow_reject=True)
    assert eff.allow_reject is True


def test_background_autogen_source_field_accepted():
    eff = MechanicalEffects(background_autogen_source="backstory_tables")
    assert eff.background_autogen_source == "backstory_tables"


def test_identity_capture_subscript():
    eff = MechanicalEffects(
        identity_capture=IdentityCapture(
            pronouns_required=True,
            background_optional=True,
            description_optional=True,
        )
    )
    assert eff.identity_capture.pronouns_required is True
    assert eff.identity_capture.background_optional is True


def test_unknown_field_still_forbidden():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MechanicalEffects(some_garbage_field=True)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/genre/test_mechanical_effects.py -v
```

Expected: FAIL — `IdentityCapture` not importable; `MechanicalEffects` lacks the new fields.

- [ ] **Step 3: Implement the schema additions**

In `sidequest-server/sidequest/genre/models/character.py`, alongside the existing models:

```python
class IdentityCapture(BaseModel):
    """Story-scene identity capture flags (pronouns + freeform fields).

    Used by the_story scene in genre packs that fold pronouns into a
    combined identity scene. ``pronouns_required=True`` means the player
    must select a pronoun before confirming. ``*_optional`` flags allow
    empty submissions.
    """

    model_config = {"extra": "forbid"}

    pronouns_required: bool = True
    background_optional: bool = True
    description_optional: bool = True
```

Add to `MechanicalEffects`:

```python
    # Arrange-scene flags (the_arrangement)
    assignment_required: bool | None = None
    allow_reject: bool | None = None

    # Story-scene flags (the_story)
    identity_capture: IdentityCapture | None = None
    background_autogen_source: str | None = None  # e.g. "backstory_tables"
```

Export `IdentityCapture` from the module's public namespace where the existing models are exported.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/genre/test_mechanical_effects.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run full mechanical-effects-adjacent suite**

```bash
cd sidequest-server && uv run pytest tests/genre -v
```

Expected: PASS. Surfaces any other test that constructed `MechanicalEffects` and would silently drift.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/genre/models/character.py tests/genre/test_mechanical_effects.py
git commit -m "feat(chargen): add MechanicalEffects fields for arrange + story scenes

New fields gate the_arrangement and the_story scene shapes:
- assignment_required, allow_reject (the_arrangement)
- identity_capture (pronouns + freeform), background_autogen_source (the_story)

Schema-only — no consumer logic yet.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — Content rewrite (sidequest-content)

The new YAML lands here. Server changes from Phase 3+ are tested against it.

### Task 2.1: Replace `char_creation.yaml`

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml`

- [ ] **Step 1: Read current file in full**

```bash
cat sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml
```

Note: 5 scenes today (`the_roll`, `the_calling`, `pronouns`, `the_kit`, `the_mouth`). `the_roll` declares `class_qualification_loop: true`.

- [ ] **Step 2: Replace with the six-scene flow**

Open `sidequest-content/genre_packs/caverns_and_claudes/char_creation.yaml` and replace the entire contents with:

```yaml
# Character creation — Caverns & Claudes (classic-class era)
# 6 scenes: roll → arrange → class → story → kit → mouth.
# Visible 3d6 rolls; click-to-assign arrangement with live class
# qualification panel; reject-and-reroll on arrangement scene only.
# Story scene folds pronouns + background + description with autogen.

- id: the_roll
  title: "Six Bones, In Any Order You Can Stomach"
  narration: |
    You sit at a scarred table in a lamplit room that smells of tallow and old
    sweat. Brecca Half-Hand — missing three fingers from her left hand,
    seven-delve veteran — pushes six bone dice across the wood toward you.

    "Roll them in any order you can stomach. The bones don't care which trade
    you pick. They only care which numbers land."
  loading_text: "Brecca counts the bones..."
  choices: []
  allows_freeform: false
  mechanical_effects:
    stat_generation: roll_3d6_arrange_visible

- id: the_arrangement
  title: "Arrange Them"
  narration: |
    Brecca taps the table once. "Now arrange them. The trade is yours to
    choose, if the bones allow it."

    Drop each number into a slot — Strength, Dexterity, Constitution,
    Intelligence, Wisdom, Charisma. The list to the side will tell you which
    trades the bones permit.

    If you cannot stomach what they gave you, throw them again.
  loading_text: "Brecca watches you arrange..."
  choices: []
  allows_freeform: false
  mechanical_effects:
    assignment_required: true
    allow_reject: true

- id: the_calling
  title: "What You'll Be Called"
  narration: |
    Brecca looks at the bones, then at you. "These are the trades the bones
    will let you take. The dungeon doesn't care which one you pick. The
    records do."
  choices:
    - label: "Fighter"
      description: "Plate, polearm, and the patience to be hit first."
      mechanical_effects:
        class_hint: Fighter
        rpg_role_hint: tank
        jungian_hint: hero
    - label: "Mage"
      description: "Bookish, half-blind, and dangerous in the third round."
      mechanical_effects:
        class_hint: Mage
        rpg_role_hint: control
        jungian_hint: magician
    - label: "Cleric"
      description: "Holy symbol, war-mace, and a faith that is mostly working so far."
      mechanical_effects:
        class_hint: Cleric
        rpg_role_hint: healer
        jungian_hint: caregiver
    - label: "Thief"
      description: "Lockpicks, leather, and a professional interest in being elsewhere."
      mechanical_effects:
        class_hint: Thief
        rpg_role_hint: stealth
        jungian_hint: outlaw
  allows_freeform: false

- id: the_story
  title: "For The Tally"
  narration: |
    Brecca dips the quill and looks up. "For the tally," she says. "In case
    you don't come back."

    She wants three things: how to refer to you, what you did before, and
    what you look like. Or you can let her make something up.
  loading_text: "Brecca writes in the ledger..."
  choices: []
  allows_freeform: true
  mechanical_effects:
    identity_capture:
      pronouns_required: true
      background_optional: true
      description_optional: true
    background_autogen_source: backstory_tables

- id: the_kit
  title: "What You Have"
  narration: |
    Brecca reaches beneath the table and drops a canvas sack in front of you.
    It lands with a dull thud. "Standard kit," she says. "Sized to the trade.
    Some of it's useful. Some of it isn't. All of it's yours now."
  choices: []
  allows_freeform: false
  mechanical_effects:
    equipment_generation: class_kit

- id: the_mouth
  title: "The Dungeon Waits"
  narration: |
    Dawn. The mouth of the dungeon is a crack in the hillside, edged with
    moss and old tooth-marks in the stone. Cold air breathes outward, carrying
    the smell of wet rock and something older.

    Behind you, the town is already forgetting your name. Ahead, the dark
    waits with the patience of something that has swallowed better than you.
  choices: []
  allows_freeform: false
```

- [ ] **Step 3: Validate the YAML loads**

```bash
cd sidequest-server
uv run python -c "
from sidequest.genre.loader import load_pack
from pathlib import Path
pack = load_pack(Path('../sidequest-content/genre_packs/caverns_and_claudes'))
scenes = pack.char_creation
print(f'Loaded {len(scenes)} scenes')
for s in scenes:
    print(f'  {s.id}')
"
```

Expected: prints 6 scene ids in order: `the_roll`, `the_arrangement`, `the_calling`, `the_story`, `the_kit`, `the_mouth`.

If it fails: read the error, fix the YAML, repeat.

- [ ] **Step 4: Commit (content repo)**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/char_creation.yaml
git commit -m "content(cnc): rewrite char_creation as 6-scene visible-dice flow

Replaces silent reroll loop with: roll → arrange → calling → story →
kit → mouth. Story folds pronouns + background + description.

Schema fields (assignment_required, allow_reject, identity_capture,
background_autogen_source) require sidequest-server feat/cnc-chargen-visible-dice.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 2.2: Remove `prime_requisite` from classes (and any prime-req XP table)

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/progression.yaml` (only if it references prime-req)

> **Note:** `ClassDef.prime_requisite` is also load-bearing for the **legacy** `qualifying_classes()` predicate in `sidequest-server/sidequest/game/builder.py`. We replace that consumer in Phase 3, then come back and remove the field. **Do not remove `prime_requisite` from classes.yaml in this task** — only audit and remove any XP-bonus table that references it. The class-yaml field deletion happens in Task 6.3.

- [ ] **Step 1: Inspect what's there**

```bash
cd sidequest-content
grep -n 'prime_req\|prime_requisite\|prime_bonus' genre_packs/caverns_and_claudes/progression.yaml genre_packs/caverns_and_claudes/classes.yaml
```

- [ ] **Step 2: If `progression.yaml` has any `prime_req_bonus` table, remove it.** Edit the file directly. Save.

- [ ] **Step 3: Verify pack still loads**

```bash
cd sidequest-server
uv run python -c "
from sidequest.genre.loader import load_pack
from pathlib import Path
pack = load_pack(Path('../sidequest-content/genre_packs/caverns_and_claudes'))
print('OK')
"
```

Expected: prints `OK`.

- [ ] **Step 4: Commit (content repo) — only if any change was made**

```bash
cd sidequest-content
git add genre_packs/caverns_and_claudes/progression.yaml
git commit -m "content(cnc): drop prime-req XP bonus table

Per chargen-big-improvements design — playgroup judgment, no prime-req XP.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

If no prime-req XP table existed, skip the commit and note it in the impact summary.

---

## Phase 3 — Builder FSM extension (sidequest-server)

The builder grows two new states (`ARRANGING`, `STORY`) and a server-side qualifying-class predicate that doesn't depend on `prime_requisite`.

### Task 3.1: Add `qualifying_classes_arrangement` predicate

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` (add a new function near the existing `qualifying_classes`)
- Test: `sidequest-server/tests/game/test_qualifying_classes.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_qualifying_classes.py
from sidequest.game.builder import qualifying_classes_arrangement
from sidequest.genre.models.character import ClassDef


def _cls(name: str, prime: str, minimum: int) -> ClassDef:
    """Minimal ClassDef per sidequest/genre/models/character.py:95."""
    return ClassDef(
        id=name.lower(),
        display_name=name,
        rpg_role="tank",
        jungian_default="hero",
        prime_requisite=prime,
        minimum_score=minimum,
        kit_table=f"{name.lower()}_kit",
    )


def test_arrangement_qualifies_when_any_stat_meets_threshold():
    fighter = _cls("Fighter", "STR", 9)
    mage = _cls("Mage", "INT", 9)
    arrangement = {"STR": 14, "DEX": 8, "CON": 10, "INT": 6, "WIS": 7, "CHA": 11}
    result = qualifying_classes_arrangement(arrangement, [fighter, mage])
    assert [c.display_name for c in result] == ["Fighter"]


def test_arrangement_qualifies_multiple_classes():
    fighter = _cls("Fighter", "STR", 9)
    thief = _cls("Thief", "DEX", 9)
    arrangement = {"STR": 14, "DEX": 12, "CON": 10, "INT": 6, "WIS": 7, "CHA": 11}
    result = qualifying_classes_arrangement(arrangement, [fighter, thief])
    assert {c.display_name for c in result} == {"Fighter", "Thief"}


def test_arrangement_qualifies_none_when_all_low():
    fighter = _cls("Fighter", "STR", 9)
    mage = _cls("Mage", "INT", 9)
    arrangement = {"STR": 8, "DEX": 8, "CON": 8, "INT": 8, "WIS": 8, "CHA": 8}
    result = qualifying_classes_arrangement(arrangement, [fighter, mage])
    assert result == []


def test_arrangement_partial_unfilled_treated_as_zero():
    fighter = _cls("Fighter", "STR", 9)
    arrangement = {"STR": 14, "DEX": None, "CON": None, "INT": None, "WIS": None, "CHA": None}
    result = qualifying_classes_arrangement(arrangement, [fighter])
    assert [c.display_name for c in result] == ["Fighter"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_qualifying_classes.py -v
```

Expected: FAIL — `qualifying_classes_arrangement` not importable.

- [ ] **Step 3: Implement the predicate**

Add to `sidequest-server/sidequest/game/builder.py`, immediately below the existing `qualifying_classes`:

```python
def qualifying_classes_arrangement(
    arrangement: dict[str, int | None],
    classes: list[ClassDef],
) -> list[ClassDef]:
    """Return classes whose prime_requisite is met by an in-progress arrangement.

    Same predicate as :func:`qualifying_classes` but tolerates ``None`` slot
    values (an arrangement still being filled). Unfilled slots are treated
    as 0 — they cannot satisfy any minimum.
    """
    return [
        c
        for c in classes
        if (arrangement.get(c.prime_requisite) or 0) >= c.minimum_score
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_qualifying_classes.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_qualifying_classes.py
git commit -m "feat(chargen): qualifying_classes_arrangement predicate

Tolerates partial arrangements (None slots → 0). Same logic as the
existing qualifying_classes; new function so callers can be migrated
incrementally.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.2: Add visible-roll path `_roll_3d6_arrange_visible`

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py`
- Test: `sidequest-server/tests/game/test_builder_arrange_visible.py`

- [ ] **Step 1: Read current `_roll_3d6_with_qualification` for context**

```bash
cd sidequest-server && grep -n '_roll_3d6_with_qualification\|stat_generation' sidequest/game/builder.py
```

Read each match plus 30 surrounding lines.

- [ ] **Step 2: Write the failing test**

```python
# tests/game/test_builder_arrange_visible.py
import random

from sidequest.game.builder import CharacterBuilder
from sidequest.genre.models.character import (
    CharCreationScene,
    MechanicalEffects,
)
from sidequest.genre.models.rules import RulesConfig


def _make_scenes_with_arrange_visible() -> list[CharCreationScene]:
    """Five-scene minimal fixture: roll(arrange_visible) → arrange → call → story → mouth."""
    return [
        CharCreationScene(
            id="the_roll",
            title="Roll",
            narration="...",
            choices=[],
            allows_freeform=False,
            mechanical_effects=MechanicalEffects(
                stat_generation="roll_3d6_arrange_visible",
            ),
        ),
        CharCreationScene(
            id="the_arrangement",
            title="Arrange",
            narration="...",
            choices=[],
            allows_freeform=False,
            mechanical_effects=MechanicalEffects(
                assignment_required=True,
                allow_reject=True,
            ),
        ),
        CharCreationScene(
            id="the_calling",
            title="Call",
            narration="...",
            choices=[],
            allows_freeform=False,
        ),
        CharCreationScene(
            id="the_story",
            title="Story",
            narration="...",
            choices=[],
            allows_freeform=True,
        ),
        CharCreationScene(
            id="the_mouth",
            title="Mouth",
            narration="...",
            choices=[],
            allows_freeform=False,
        ),
    ]


def test_arrange_visible_produces_pool_of_six_3d6():
    rules = RulesConfig(ability_score_names=["STR", "DEX", "CON", "INT", "WIS", "CHA"])
    rng = random.Random(42)
    builder = CharacterBuilder(scenes=_make_scenes_with_arrange_visible(), rules=rules, rng=rng)

    pool = builder.arrangement_pool()
    assert len(pool) == 6
    for n in pool:
        assert 3 <= n <= 18


def test_arrange_visible_does_not_assign_in_order():
    """Pool is a list, not labeled stats — labels come from arrangement."""
    rules = RulesConfig.minimal_for_test()
    builder = CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(),
        rules=rules,
        rng=random.Random(42),
    )
    # rolled_stats should be None — only the pool exists pre-arrangement
    assert builder.rolled_stats() is None


def test_arrange_visible_no_qualification_loop():
    """Pool is rolled once; no rerolls regardless of qualification."""
    rules = RulesConfig.minimal_for_test()
    rng = random.Random(0)  # any seed; we measure call count via patching if needed

    # Roll 100 builders with different seeds; ensure first pool is always taken.
    # (We can't directly measure "no reroll loop" without instrumenting RNG;
    # a structural check is: no `class_qualification_loop` setting was read.)
    builder = CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(), rules=rules, rng=rng,
    )
    pool_before = list(builder.arrangement_pool())
    # Constructing a second time with same seed must yield same pool —
    # proves no reroll loop is firing for arrange_visible mode.
    builder2 = CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(), rules=rules, rng=random.Random(0),
    )
    assert pool_before == builder2.arrangement_pool()
```

> The `RulesConfig` constructor takes defaults for everything except what we set explicitly; `ability_score_names` is required because `_roll_3d6_arrange_visible` reads it.

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrange_visible.py -v
```

Expected: FAIL — `arrangement_pool` does not exist; `roll_3d6_arrange_visible` not handled.

- [ ] **Step 4: Implement the visible-roll path and accessor**

In `sidequest-server/sidequest/game/builder.py`:

(a) Add new instance attribute initializers in `__init__` near `self._rolled_stats`:

```python
        # Arrange-visible mode: pool is a list of six 3d6 totals,
        # unassigned. Arrangement happens via assign_stat / clear_stat,
        # confirmed via confirm_arrangement, rejected via reject_arrangement.
        self._arrangement_pool: list[int] | None = None
        self._arrangement_assignment: dict[str, int | None] | None = None
```

(b) In the construction-time scene scan that today reads `roll_3d6_strict`, add a branch for `roll_3d6_arrange_visible`:

```python
        for s in scenes:
            eff = s.mechanical_effects
            if eff is None or eff.stat_generation is None:
                continue
            if eff.stat_generation == "roll_3d6_strict":
                self._roll_3d6_with_qualification(
                    qualification_loop=eff.class_qualification_loop,
                )
            elif eff.stat_generation == "roll_3d6_arrange_visible":
                self._roll_3d6_arrange_visible()
            break
```

(c) Add the new private method (place near `_roll_3d6_with_qualification`):

```python
    def _roll_3d6_arrange_visible(self) -> None:
        """Roll six 3d6 totals into an unlabeled pool.

        No qualification loop. The arrangement scene resolves which stat
        gets which roll, and rejection is the only escape valve. Stat
        labels come from ``self._ability_score_names``.
        """
        self._arrangement_pool = [
            self._rng.randint(1, 6) + self._rng.randint(1, 6) + self._rng.randint(1, 6)
            for _ in range(6)
        ]
        self._arrangement_assignment = {
            name: None for name in self._ability_score_names
        }
        # rolled_stats stays None until confirm_arrangement materializes it.
```

(d) Add the public accessor:

```python
    def arrangement_pool(self) -> list[int] | None:
        """Return the six unassigned 3d6 totals, or None if not in arrange mode."""
        return list(self._arrangement_pool) if self._arrangement_pool is not None else None
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrange_visible.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_builder_arrange_visible.py
git commit -m "feat(chargen): roll_3d6_arrange_visible builder path

Six 3d6 totals into an unlabeled pool. No qualification loop — rejection
is the only escape valve. Pool/assignment state tracked separately from
rolled_stats.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.3: Add `assign_stat`, `clear_stat`, `confirm_arrangement`, `reject_arrangement`

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py`
- Test: `sidequest-server/tests/game/test_builder_arrangement_ops.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_builder_arrangement_ops.py
import random

import pytest

from sidequest.game.builder import (
    CharacterBuilder,
    NoQualifyingClassesError,
    PoolValueNotPresentError,
    UnfilledArrangementError,
)
from sidequest.genre.models.character import ClassDef
from tests.game.test_builder_arrange_visible import _make_scenes_with_arrange_visible


def _classes_fighter_thief() -> list[ClassDef]:
    """Two classes; each qualifies on a different stat."""
    return [
        ClassDef(
            id="fighter", display_name="Fighter", rpg_role="tank",
            jungian_default="hero", prime_requisite="STR",
            minimum_score=9, kit_table="fighter_kit",
        ),
        ClassDef(
            id="thief", display_name="Thief", rpg_role="stealth",
            jungian_default="outlaw", prime_requisite="DEX",
            minimum_score=9, kit_table="thief_kit",
        ),
    ]


def _seeded_builder():
    from sidequest.genre.models.rules import RulesConfig
    rules = RulesConfig.minimal_for_test()
    return CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(),
        rules=rules,
        rng=random.Random(42),
    ).with_classes(_classes_fighter_thief())


def test_assign_stat_moves_value_from_pool_to_slot():
    builder = _seeded_builder()
    pool = builder.arrangement_pool()
    value = pool[0]
    builder.assign_stat(stat_name="STR", value=value)
    assert builder.arrangement_assignment()["STR"] == value
    # Pool should no longer contain that occurrence
    new_pool = builder.arrangement_pool()
    assert new_pool.count(value) == pool.count(value) - 1


def test_assign_stat_value_not_in_pool_raises():
    builder = _seeded_builder()
    with pytest.raises(PoolValueNotPresentError):
        builder.assign_stat(stat_name="STR", value=99)


def test_clear_stat_returns_value_to_pool():
    builder = _seeded_builder()
    pool_before = builder.arrangement_pool()
    value = pool_before[0]
    builder.assign_stat(stat_name="STR", value=value)
    builder.clear_stat(stat_name="STR")
    assert builder.arrangement_assignment()["STR"] is None
    assert sorted(builder.arrangement_pool()) == sorted(pool_before)


def test_confirm_arrangement_requires_all_six_filled():
    builder = _seeded_builder()
    pool = builder.arrangement_pool()
    builder.assign_stat("STR", pool[0])
    with pytest.raises(UnfilledArrangementError):
        builder.confirm_arrangement()


def test_confirm_arrangement_requires_at_least_one_qualifying_class():
    """Force an all-low arrangement; expect refusal."""
    # Reseed so we get controlled pool. Cheat: monkey-set the pool.
    builder = _seeded_builder()
    builder._arrangement_pool = [3, 4, 5, 6, 7, 8]
    builder._arrangement_assignment = dict(STR=3, DEX=4, CON=5, INT=6, WIS=7, CHA=8)
    with pytest.raises(NoQualifyingClassesError):
        builder.confirm_arrangement()


def test_confirm_arrangement_materializes_rolled_stats():
    builder = _seeded_builder()
    pool = builder.arrangement_pool()
    # Distribute pool deterministically so at least Fighter qualifies.
    sorted_pool = sorted(pool, reverse=True)
    builder.assign_stat("STR", sorted_pool[0])  # highest into STR
    builder.assign_stat("DEX", sorted_pool[1])
    builder.assign_stat("CON", sorted_pool[2])
    builder.assign_stat("INT", sorted_pool[3])
    builder.assign_stat("WIS", sorted_pool[4])
    builder.assign_stat("CHA", sorted_pool[5])
    builder.confirm_arrangement()
    # rolled_stats now exists
    rolled = builder.rolled_stats()
    assert rolled is not None
    assert {n for n, _ in rolled} == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    # And the pool is consumed
    assert builder.arrangement_pool() is None


def test_reject_arrangement_rerolls_pool():
    builder = _seeded_builder()
    pool_before = list(builder.arrangement_pool())
    builder.assign_stat("STR", pool_before[0])
    builder.reject_arrangement()
    pool_after = builder.arrangement_pool()
    # Pool exists, fully unassigned, and (with overwhelming probability)
    # different from before.
    assert pool_after is not None
    assert len(pool_after) == 6
    assert all(v is None for v in builder.arrangement_assignment().values())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrangement_ops.py -v
```

Expected: ImportError on the three exception classes; missing methods.

- [ ] **Step 3: Implement the operations**

Add the exception classes near the top of `builder.py` where other domain exceptions live (search for `class NoScenesError` to find the cluster):

```python
class PoolValueNotPresentError(Exception):
    """assign_stat called with a value not currently in the arrangement pool."""


class UnfilledArrangementError(Exception):
    """confirm_arrangement called before all six slots are filled."""


class NoQualifyingClassesError(Exception):
    """confirm_arrangement called but the arrangement qualifies for no classes."""
```

Add the public methods to `CharacterBuilder`:

```python
    def arrangement_assignment(self) -> dict[str, int | None] | None:
        """Return the current arrangement (stat → value-or-None)."""
        if self._arrangement_assignment is None:
            return None
        return dict(self._arrangement_assignment)

    def assign_stat(self, stat_name: str, value: int) -> None:
        """Move ``value`` from the arrangement pool into ``stat_name``.

        If the slot already has a value, that value is returned to the pool
        first. Raises ``PoolValueNotPresentError`` if ``value`` isn't in the
        pool.
        """
        if self._arrangement_pool is None or self._arrangement_assignment is None:
            raise RuntimeError("not in arrangement mode")
        if value not in self._arrangement_pool:
            raise PoolValueNotPresentError(
                f"value {value} not in pool {self._arrangement_pool}"
            )
        # If slot already filled, return previous to pool
        existing = self._arrangement_assignment.get(stat_name)
        if existing is not None:
            self._arrangement_pool.append(existing)
        self._arrangement_pool.remove(value)
        self._arrangement_assignment[stat_name] = value

    def clear_stat(self, stat_name: str) -> None:
        """Return the value in ``stat_name`` (if any) to the pool."""
        if self._arrangement_pool is None or self._arrangement_assignment is None:
            raise RuntimeError("not in arrangement mode")
        existing = self._arrangement_assignment.get(stat_name)
        if existing is None:
            return
        self._arrangement_pool.append(existing)
        self._arrangement_assignment[stat_name] = None

    def confirm_arrangement(self) -> None:
        """Lock the arrangement and materialize ``rolled_stats``.

        Raises:
            UnfilledArrangementError: not all six slots filled.
            NoQualifyingClassesError: arrangement qualifies for zero classes
                from the pack's class list.
        """
        if self._arrangement_assignment is None:
            raise RuntimeError("not in arrangement mode")
        if any(v is None for v in self._arrangement_assignment.values()):
            raise UnfilledArrangementError("not all six stats assigned")
        # Use the new arrangement-aware predicate; classes attached via
        # with_classes(). If no classes attached, qualification is vacuous —
        # pack misconfig, raise.
        if not self._classes:
            raise RuntimeError("no classes attached; call with_classes() before confirm")
        qualifying = qualifying_classes_arrangement(
            self._arrangement_assignment, self._classes,
        )
        if not qualifying:
            raise NoQualifyingClassesError(
                f"arrangement {self._arrangement_assignment} qualifies for no class"
            )
        # Materialize rolled_stats in the canonical ability_score_names order
        self._rolled_stats = [
            (name, self._arrangement_assignment[name])
            for name in self._ability_score_names
        ]
        # Consume pool/assignment
        self._arrangement_pool = None
        self._arrangement_assignment = None

    def reject_arrangement(self) -> None:
        """Discard the current pool and reroll. Idempotent if already in arrange mode."""
        if self._arrangement_assignment is None:
            raise RuntimeError("not in arrangement mode")
        # Re-fire the visible roll
        self._roll_3d6_arrange_visible()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrangement_ops.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Run the full builder test suite**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder*.py -v
```

Expected: PASS. Surfaces any older test that the new state could have broken.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_builder_arrangement_ops.py
git commit -m "feat(chargen): assign/clear/confirm/reject arrangement ops

Move dice between pool and stat slots. Confirm refuses unfilled or
zero-qualifying-class arrangements. Reject rerolls. Materializes
rolled_stats only at confirm time.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.4: Wire arrangement scene into the builder's scene loop

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` — `apply_response` / scene-advance code path
- Test: `sidequest-server/tests/game/test_builder_arrangement_scene_flow.py`

- [ ] **Step 1: Read the current `apply_response` / scene-advance code**

```bash
cd sidequest-server && grep -n 'apply_response\|advance\|next_scene' sidequest/game/builder.py | head -40
```

Read the relevant region (likely 100-200 lines around `apply_response`).

- [ ] **Step 2: Write the failing test**

Test that the builder, when its current scene declares `assignment_required: true`, **only** advances when `apply_arrangement_confirm` is called and refuses ordinary `apply_response`. Test that `apply_arrangement_reject` returns the builder to the previous (`the_roll`) scene.

```python
# tests/game/test_builder_arrangement_scene_flow.py
import random

import pytest

from sidequest.game.builder import (
    ArrangementSceneActiveError,
    CharacterBuilder,
)
from sidequest.genre.models.character import ClassDef
from sidequest.genre.models.rules import RulesConfig
from tests.game.test_builder_arrange_visible import _make_scenes_with_arrange_visible


def _seeded():
    rules = RulesConfig.minimal_for_test()
    return CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(),
        rules=rules,
        rng=random.Random(42),
    ).with_classes([
        ClassDef(
            id="fighter", display_name="Fighter", rpg_role="tank",
            jungian_default="hero", prime_requisite="STR",
            minimum_score=9, kit_table="fighter_kit",
        ),
    ])


def test_arrangement_scene_blocks_choice_input():
    """During the_arrangement, ChoiceInput is rejected."""
    from sidequest.game.builder import ChoiceInput
    b = _seeded()
    # Advance from the_roll to the_arrangement
    b.advance_past_roll_scene()  # helper if exists; otherwise apply continue
    assert b.current_scene().id == "the_arrangement"
    with pytest.raises(ArrangementSceneActiveError):
        b.apply_response(ChoiceInput(index=0))


def test_apply_arrangement_confirm_advances_to_calling():
    b = _seeded()
    b.advance_past_roll_scene()
    pool = b.arrangement_pool()
    sorted_pool = sorted(pool, reverse=True)
    for stat, v in zip(["STR", "DEX", "CON", "INT", "WIS", "CHA"], sorted_pool):
        b.assign_stat(stat, v)
    b.apply_arrangement_confirm()
    assert b.current_scene().id == "the_calling"


def test_apply_arrangement_reject_resets_pool_and_stays_on_arrangement():
    b = _seeded()
    b.advance_past_roll_scene()
    pool_before = list(b.arrangement_pool())
    b.assign_stat("STR", pool_before[0])
    b.apply_arrangement_reject()
    assert b.current_scene().id == "the_arrangement"
    # Pool exists and is fully unassigned
    assert b.arrangement_pool() is not None
    assert all(v is None for v in b.arrangement_assignment().values())
```

> **`advance_past_roll_scene` is a fictional helper.** Replace with whatever the real `apply_response` flow looks like for the_roll scene (it likely takes a `continue`-style input or auto-advances). Read the existing flow first.

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrangement_scene_flow.py -v
```

Expected: FAIL — `ArrangementSceneActiveError` and the two new public methods don't exist.

- [ ] **Step 4: Implement the scene-flow gating**

(a) Add the exception:

```python
class ArrangementSceneActiveError(Exception):
    """apply_response called while the_arrangement scene is active.

    The arrangement scene only accepts apply_arrangement_confirm /
    apply_arrangement_reject — not generic ChoiceInput / FreeformInput.
    """
```

(b) In `apply_response`, near the top, add a guard:

```python
    def apply_response(self, response: SceneInputType) -> None:
        # ... existing precondition checks ...
        scene = self.current_scene()
        eff = scene.mechanical_effects
        if eff is not None and eff.assignment_required:
            raise ArrangementSceneActiveError(
                f"scene {scene.id!r} requires apply_arrangement_confirm/reject"
            )
        # ... existing dispatch ...
```

(c) Add public methods that drive the arrangement scene to advance / reject:

```python
    def apply_arrangement_confirm(self) -> None:
        """Confirm the current arrangement and advance to the next scene.

        Raises ``UnfilledArrangementError`` or ``NoQualifyingClassesError``
        from confirm_arrangement(); otherwise records the SceneResult and
        advances scene_index.
        """
        scene = self.current_scene()
        eff = scene.mechanical_effects
        if not (eff and eff.assignment_required):
            raise RuntimeError(f"scene {scene.id!r} is not an arrangement scene")
        self.confirm_arrangement()  # may raise
        # Record a SceneResult for the arrangement scene so go_back works.
        # Use a synthetic FreeformInput carrying the assignment as JSON?
        # Simpler: record a new SceneResult variant that captures the
        # assignment dict directly.
        self._results.append(
            SceneResult(
                scene_id=scene.id,
                input=FreeformInput(text=str(dict(self._rolled_stats or []))),
                # Real implementation should add a structured field here;
                # the placeholder text above is fine for go_back parity.
            )
        )
        self._advance_scene_index()  # use the existing advance helper

    def apply_arrangement_reject(self) -> None:
        """Reject the current pool, reroll, stay on the_arrangement scene."""
        scene = self.current_scene()
        eff = scene.mechanical_effects
        if not (eff and eff.assignment_required):
            raise RuntimeError(f"scene {scene.id!r} is not an arrangement scene")
        self.reject_arrangement()
```

> **The `SceneResult` placeholder text above is intentionally minimal.** When wiring summary rendering (Task 4.x) we'll need to read assignment back; if the existing `SceneResult` shape doesn't have a structured assignment field, add one as part of this task. Look at how the Pencil-edit `target_step` consumed `SceneResult` for guidance.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_arrangement_scene_flow.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_builder_arrangement_scene_flow.py
git commit -m "feat(chargen): arrangement scene gates apply_response, adds confirm/reject

apply_response on an assignment-required scene raises
ArrangementSceneActiveError. apply_arrangement_confirm / reject drive
the scene-advance / reroll.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.5: Story scene — accept structured pronouns + background + description

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (or wherever chargen response payloads live)
- Modify: `sidequest-server/sidequest/game/builder.py` — story-scene handler
- Test: `sidequest-server/tests/game/test_builder_story_scene.py`

- [ ] **Step 1: Find chargen payload model**

```bash
cd sidequest-server && grep -rn 'CharacterCreationPayload\|character_creation_response' sidequest/protocol/ --include='*.py' | head
```

- [ ] **Step 2: Write the failing test**

```python
# tests/game/test_builder_story_scene.py
import random

from sidequest.game.builder import (
    CharacterBuilder,
    StoryInput,
)
from sidequest.genre.models.rules import RulesConfig
from tests.game.test_builder_arrange_visible import _make_scenes_with_arrange_visible


def _builder_at_story_scene():
    """Seed a builder, drive it past roll/arrange/calling so current_scene == the_story."""
    # Implementation: construct, advance through scenes step by step.
    # See test_builder_arrangement_scene_flow.py for the pattern.
    raise NotImplementedError("fill me in once apply_arrangement_confirm is wired")


def test_story_input_records_pronouns_and_text():
    b = _builder_at_story_scene()
    b.apply_response(StoryInput(
        pronouns="they/them",
        background="Former ratcatcher.",
        description="Tall, soot-stained.",
    ))
    # After applying, the builder should advance past the_story
    assert b.current_scene().id == "the_kit"
    # And the SceneResult should record pronouns + freeform text.
    last = b._results[-1]
    assert last.scene_id == "the_story"
    # Per the existing SceneResult shape, the fields land in choice_label /
    # choice_description / freeform_text. Adapt assertion to whichever
    # fields the model actually carries.
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_story_scene.py -v
```

Expected: FAIL — `StoryInput` doesn't exist.

- [ ] **Step 4: Implement `StoryInput` + handler**

Add to `builder.py` near `ChoiceInput` / `FreeformInput`:

```python
@dataclass(frozen=True)
class StoryInput(SceneInputType):
    """Player submitted the_story scene (pronouns + freeform background/description)."""

    pronouns: str
    background: str
    description: str
```

In `apply_response`'s dispatch, add a branch for the_story scene that accepts only `StoryInput`. Map `pronouns` to a `pronoun_hint` mechanical effect and `background` + `description` to the existing backstory-recording machinery (read where `MechanicalEffects.background` is consumed today — `chargen_summary.py` references it).

```python
        # Inside apply_response, after the assignment_required guard:
        if eff is not None and eff.identity_capture is not None:
            if not isinstance(response, StoryInput):
                raise RuntimeError(
                    f"scene {scene.id!r} requires StoryInput; got {type(response).__name__}"
                )
            ic = eff.identity_capture
            if ic.pronouns_required and not response.pronouns.strip():
                raise UnfilledArrangementError("pronouns required")
            # Record the SceneResult with structured fields.
            self._results.append(
                SceneResult(
                    scene_id=scene.id,
                    input=FreeformInput(text=response.background),  # adapt to real shape
                    # If SceneResult supports structured pronoun/background/description
                    # fields, set them here. Otherwise compose into the text body.
                )
            )
            self._advance_scene_index()
            return
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_story_scene.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_builder_story_scene.py
git commit -m "feat(chargen): the_story scene — StoryInput with pronouns + freeform

Story scene accepts structured StoryInput (pronouns + background +
description). Pronouns required iff identity_capture.pronouns_required.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 3.6: Backstory autogen — read tables and roll

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` — add `autogen_backstory` method
- Test: `sidequest-server/tests/game/test_builder_backstory_autogen.py`

- [ ] **Step 1: Read existing backstory_tables consumer**

```bash
cd sidequest-server && grep -rn 'BackstoryTables\|backstory_tables' sidequest --include='*.py' | head -20
```

- [ ] **Step 2: Write the failing test**

```python
# tests/game/test_builder_backstory_autogen.py
import random

from sidequest.game.builder import CharacterBuilder
from sidequest.genre.models.character import BackstoryTables
from sidequest.genre.models.rules import RulesConfig
from tests.game.test_builder_arrange_visible import _make_scenes_with_arrange_visible


def _builder_with_tables():
    rules = RulesConfig.minimal_for_test()
    tables = BackstoryTables(
        template="Former {trade}. {feature}. {reason}.",
        trade=["ratcatcher", "tinker"],
        feature=["one glass eye", "missing three fingers"],
        reason=["debt collectors", "a curse"],
    )
    # Adapt construction to the real BackstoryTables model.
    return CharacterBuilder(
        scenes=_make_scenes_with_arrange_visible(),
        rules=rules,
        rng=random.Random(0),
        backstory_tables=tables,
    )


def test_autogen_returns_background_and_description():
    b = _builder_with_tables()
    out = b.autogen_backstory(seed=42)
    assert "background" in out
    assert "description" in out
    assert isinstance(out["background"], str) and out["background"]
    # Description may be empty string if tables don't supply description fields —
    # autogen tolerates that.
    assert isinstance(out["description"], str)


def test_autogen_deterministic_with_seed():
    b1 = _builder_with_tables()
    b2 = _builder_with_tables()
    out1 = b1.autogen_backstory(seed=42)
    out2 = b2.autogen_backstory(seed=42)
    assert out1 == out2


def test_autogen_different_with_different_seed():
    b = _builder_with_tables()
    out1 = b.autogen_backstory(seed=1)
    out2 = b.autogen_backstory(seed=2)
    assert out1 != out2
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_backstory_autogen.py -v
```

Expected: FAIL — `autogen_backstory` not implemented.

- [ ] **Step 4: Implement `autogen_backstory`**

```python
    def autogen_backstory(self, seed: int) -> dict[str, str]:
        """Roll the pack's backstory tables and return a background + description.

        Deterministic for a given seed. The pack's tables provide a
        ``template`` plus per-slot lists; this method rolls one item per
        slot and substitutes into the template.

        Returns ``{"background": str, "description": str}``. If the pack's
        tables don't expose distinct description fields, ``description``
        is an empty string and the UI can leave that textarea blank.
        """
        if self._backstory_tables is None:
            return {"background": "", "description": ""}
        local_rng = random.Random(seed)
        bg = self._backstory_tables.roll(local_rng)  # pack's existing roll API
        # If the tables expose a distinct description sub-roll, call it here.
        # Otherwise leave description empty for the player to fill.
        return {"background": bg, "description": ""}
```

> **`BackstoryTables.roll` may or may not exist.** Read `sidequest/genre/models/character.py` (BackstoryTables definition) and `chargen_summary.py` for how today's code rolls. If no public `.roll` method exists, write one as part of this task — it's a clean place to land it.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd sidequest-server && uv run pytest tests/game/test_builder_backstory_autogen.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/game/builder.py tests/game/test_builder_backstory_autogen.py
git commit -m "feat(chargen): autogen_backstory rolls backstory_tables deterministically

Seed-driven roll of the pack's backstory tables for the_story scene's
'Let Brecca tell my story' button. No Claude call — fast for Alex.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4 — Server protocol & dispatch (sidequest-server)

Wire the new builder methods into the WebSocket message flow.

### Task 4.1: New protocol messages — arrange + story

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (and adjacent typed-payload files)
- Test: `sidequest-server/tests/protocol/test_chargen_arrange_messages.py`

- [ ] **Step 1: Read current chargen message shape**

```bash
cd sidequest-server && grep -n 'CharacterCreationMessage\|CharacterCreationPayload\|arrange\|story' sidequest/protocol/messages.py | head -20
```

- [ ] **Step 2: Write the failing test**

Test that:
- `ArrangementPayload` carries `pool: list[int]`, `assignment: dict[str, int|None]`, `qualifying_classes: list[str]`, `class_requirements: list[ClassRequirement]`.
- `StoryPayload` carries `pronouns_options`, `pronouns_allow_freeform`.
- Both serialize/deserialize through pydantic without `extra` fields.

(Test code follows the same pattern as Task 1.2.)

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Implement payload models**

```python
class ClassRequirement(BaseModel):
    """One row in the live-qualify panel."""
    model_config = {"extra": "forbid"}
    name: str
    requirement_label: str  # "STR 9+", "INT 9+"


class ArrangementPayload(BaseModel):
    """Server → client: state of the_arrangement scene."""
    model_config = {"extra": "forbid"}
    pool: list[int]
    assignment: dict[str, int | None]
    qualifying_classes: list[str]
    class_requirements: list[ClassRequirement]
    confirm_enabled: bool


class StoryPayload(BaseModel):
    """Server → client: shape of the_story scene."""
    model_config = {"extra": "forbid"}
    pronouns_options: list[str]      # e.g. ["she/her", "he/him", "they/them"]
    pronouns_allow_freeform: bool
    background_optional: bool
    description_optional: bool
    autogen_available: bool


class ArrangeAssignRequest(BaseModel):
    """Client → server: tap a number into a slot."""
    model_config = {"extra": "forbid"}
    stat: str
    value: int


class ArrangeClearRequest(BaseModel):
    """Client → server: empty a slot."""
    model_config = {"extra": "forbid"}
    stat: str


class ArrangeConfirmRequest(BaseModel):
    """Client → server: confirm arrangement and advance."""
    model_config = {"extra": "forbid"}


class ArrangeRejectRequest(BaseModel):
    """Client → server: reject pool and reroll."""
    model_config = {"extra": "forbid"}


class StoryAutogenRequest(BaseModel):
    """Client → server: roll backstory tables for autogen."""
    model_config = {"extra": "forbid"}
    seed: int | None = None


class StoryAutogenResult(BaseModel):
    """Server → client: autogen output."""
    model_config = {"extra": "forbid"}
    seed: int
    background: str
    description: str


class StoryConfirmRequest(BaseModel):
    """Client → server: commit the_story."""
    model_config = {"extra": "forbid"}
    pronouns: str
    background: str
    description: str
```

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/protocol/messages.py tests/protocol/test_chargen_arrange_messages.py
git commit -m "feat(chargen): protocol messages for arrange + story scenes

ArrangementPayload, StoryPayload, plus six client-request models for
assign/clear/confirm/reject/autogen/story-confirm.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 4.2: Dispatch handlers for new messages

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/` — likely `char_creation_resolve.py` or a new `chargen_arrangement.py`
- Test: `sidequest-server/tests/server/dispatch/test_chargen_arrangement_dispatch.py`

- [ ] **Step 1: Read current chargen dispatch**

```bash
cd sidequest-server && cat sidequest/server/dispatch/char_creation_resolve.py
```

- [ ] **Step 2: Write the failing integration test**

Test the full flow through the dispatch layer: send `ArrangeAssignRequest`, expect updated `ArrangementPayload`. Send `ArrangeConfirmRequest` with a complete qualifying assignment, expect scene advance to `the_calling`. Send `ArrangeRejectRequest`, expect new pool. Test idempotence: two assigns of the same stat replace, never duplicate.

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Implement dispatch handlers** — one per request type, each calling the corresponding builder method and emitting an updated `ArrangementPayload`.

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/server/dispatch/ tests/server/dispatch/test_chargen_arrangement_dispatch.py
git commit -m "feat(chargen): dispatch handlers for arrange + story messages

Wires the six new client-request models to the corresponding builder
methods. Each handler emits an updated payload back to the client.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 4.3: Dice protocol wiring (graceful-degrade compatible)

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` — add `dice_roll_request`, `dice_roll_played`, `dice_roll_revealed` (if not already present per ADR-074)
- Modify: `sidequest-server/sidequest/server/dispatch/...` — emit six `dice_roll_request`s for the_roll scene
- Test: `sidequest-server/tests/server/test_chargen_dice_protocol.py`

> **ADR-074 status:** *proposed* per the ADR index. If a dice-protocol implementation already exists, reuse it. If not, this task **scaffolds** the message envelope and uses immediate-resolve mode (degraded path per ADR-006). Either way, the_roll scene must end up with six 3d6 totals visible client-side.

- [ ] **Step 1: Probe for existing dice protocol**

```bash
cd sidequest-server && grep -rn 'dice_roll\|DiceRoll\|RollRequest' sidequest/protocol --include='*.py' | head
```

- [ ] **Step 2: Write the failing test**

Test that completing the_roll scene fires either:
- six `dice_roll_request` messages followed by an `arrangement_payload` (full ADR-074 mode), **or**
- a single `arrangement_payload` whose `pool` already contains six 3d6 totals (degraded mode).

The test asserts the *behavioral* contract — six numbers in the pool — without forcing one mode.

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Implement** — pick **degraded mode** for v1 (numeric reveal). Server immediately runs `_roll_3d6_arrange_visible` at scene-enter time and emits `ArrangementPayload`. The full ADR-074 hookup is a follow-on once that ADR ships.

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/protocol/messages.py sidequest/server/dispatch/ tests/server/test_chargen_dice_protocol.py
git commit -m "feat(chargen): the_roll dispatches arrangement_payload (degraded dice mode)

ADR-074 not yet shipped — degrade to immediate-resolve numeric reveal
per ADR-006. Pool of six 3d6 totals lands in the arrangement scene
payload directly. Full per-die-animation upgrade lands when ADR-074
ships.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 4.4: OTEL events

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/` — add chargen span definitions
- Modify: `sidequest-server/sidequest/game/builder.py` — emit spans inside the new methods
- Test: `sidequest-server/tests/telemetry/test_chargen_otel.py`

- [ ] **Step 1: Read current OTEL conventions**

```bash
cd sidequest-server && grep -rn 'chargen\.' sidequest/telemetry sidequest/game --include='*.py' | head -10
```

- [ ] **Step 2: Write the failing test**

Test that:
- `_roll_3d6_arrange_visible` emits six `chargen.roll.die` spans + one `chargen.roll.complete`.
- `assign_stat` emits `chargen.arrange.assign`.
- `reject_arrangement` emits `chargen.arrange.reject`.
- `confirm_arrangement` emits `chargen.arrange.confirm`.
- `apply_response` on the_calling scene emits `chargen.class.selected`.
- `autogen_backstory` emits `chargen.story.autogen`.
- the_story confirm emits `chargen.story.confirm`.

(Use the existing OTEL test infrastructure — read `tests/telemetry/` for how spans are asserted.)

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Implement spans** — one `tracer.start_as_current_span(...)` per method.

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/ sidequest/game/builder.py tests/telemetry/test_chargen_otel.py
git commit -m "feat(chargen): OTEL events for roll/arrange/story/class

Per SOUL — every chargen mechanical decision emits a watcher event so
the GM panel can audit the rolls Sebastien obsesses over.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 4.5: Server-filtered class menu for the_calling

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/char_creation_resolve.py` — or wherever the_calling's choices are emitted
- Test: `sidequest-server/tests/server/dispatch/test_calling_filter.py`

- [ ] **Step 1: Write the failing test**

Force an arrangement that qualifies only Fighter and Thief, advance to the_calling, assert the emitted choices are `["Fighter", "Thief"]` only.

- [ ] **Step 2-6:** Implement the filter. The_calling scene's choice list comes from `the_calling` YAML *intersected with* `qualifying_classes_arrangement(rolled_stats, classes)`. Commit.

```bash
cd sidequest-server
git commit -m "feat(chargen): the_calling shows only qualifying classes

Server-side filter at scene-render time. Removes the today-misleading
'(STR 9+)' hints from the YAML descriptions since unqualifying classes
no longer appear.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 5 — Server cleanup (sidequest-server)

Remove the silent reroll loop and the manual-edit handler now that the new flow is wired.

### Task 5.1: Remove `class_qualification_loop` from `MechanicalEffects`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py`
- Modify: `sidequest-server/sidequest/game/builder.py` — drop the qualification loop branch in construction
- Modify: `sidequest-server/sidequest/game/builder.py` — drop `_roll_3d6_with_qualification`'s qualification_loop param entirely (and rename, or fold into a single `_roll_3d6_strict`)
- Test: ensure no test references the removed field

- [ ] **Step 1: Find consumers**

```bash
cd sidequest-server && grep -rn 'class_qualification_loop\|qualification_loop' sidequest tests --include='*.py'
```

- [ ] **Step 2: Audit consumers — should be only the builder construction code now.**

- [ ] **Step 3: Remove the field from `MechanicalEffects` and the builder code path.**

- [ ] **Step 4: Run full server test suite**

```bash
cd sidequest-server && just server-test
```

Expected: PASS. If any test still references the removed field, update or delete it (the silent loop is gone — its test isn't valuable).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git commit -m "refactor(chargen): drop silent class_qualification_loop

Replaced by visible roll_3d6_arrange_visible + arrangement scene with
reject button. The silent loop was a Sebastien lie-detector failure
mode per SOUL — its removal is the point of this story.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 5.2: Remove server-side handler for the Pencil edit message

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/` — find the `action: "edit"` handler
- Modify: `sidequest-server/sidequest/game/builder.py` — drop `target_step` go-back-to-N support if it has no other consumer

- [ ] **Step 1: Find the edit handler**

```bash
cd sidequest-server && grep -rn 'target_step\|"action": "edit"\|action == "edit"' sidequest --include='*.py'
```

- [ ] **Step 2: Verify no other consumer.**

- [ ] **Step 3: Remove handler + dead code path.** Tests that exercised it: delete (the affordance is removed).

- [ ] **Step 4: Run server tests.**

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git commit -m "refactor(chargen): drop Pencil edit affordance server handler

Per chargen-big-improvements design — characters evolve through play,
not through chargen edits. UI-side removal lands in sidequest-ui.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 5.3: Drop `prime_requisite` migration (after migrating callers)

> **Important — do this after all Phase-3/4 server work is committed.** The legacy `qualifying_classes()` predicate in `builder.py` reads `prime_requisite`. The new `qualifying_classes_arrangement()` also reads it (same field on the `ClassDef` model). **We are NOT removing `ClassDef.prime_requisite`** — it remains canonical. We're only removing the `prime_req_bonus` XP table consumer (already done in Task 2.2).

This task is therefore a **no-op confirmation step** with one cleanup:

- [ ] **Step 1: Verify no `prime_req_bonus` consumer remains in server code**

```bash
cd sidequest-server && grep -rn 'prime_req_bonus\|prime_bonus' sidequest tests --include='*.py'
```

Expected: zero matches. If matches: remove them.

- [ ] **Step 2: If any cleanup happened, commit**

```bash
cd sidequest-server
git commit -m "refactor(chargen): remove dead prime_req_bonus references"
```

If no matches, skip the commit.

### Task 5.4: Push server PR

- [ ] **Step 1: Run full check**

```bash
cd sidequest-server && just server-check
```

Expected: lint clean, all tests PASS.

- [ ] **Step 2: Push and open PR (target develop)**

```bash
cd sidequest-server
git push -u origin feat/cnc-chargen-visible-dice
gh pr create --base develop --title "feat(chargen): C&C visible dice + arrange + story flow" --body "$(cat <<'EOF'
## Summary
- Replaces silent 3d6-in-order with visible 3d6-arrange flow
- New CharacterBuilder states: arrangement (assign/clear/confirm/reject) and story (pronouns + background + description with autogen)
- Drops silent class_qualification_loop and Pencil-edit server handler
- Adds OTEL events for every chargen mechanical decision

## Spec
docs/superpowers/specs/2026-05-09-cnc-chargen-big-improvements-design.md (orchestrator repo)

## Coordinated PRs
- sidequest-content: char_creation.yaml + progression.yaml
- sidequest-ui: stat_arrange + story render branches, Pencil removal

## Test plan
- [ ] uv run pytest tests/game tests/genre tests/protocol tests/telemetry
- [ ] uv run ruff check .
- [ ] Manual: just up, create C&C character, exercise arrange + reject + story autogen

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Phase 6 — UI render branches (sidequest-ui)

### Task 6.1: Stat-arrange render branch

**Files:**
- Modify: `sidequest-ui/src/components/CharacterCreation/CharacterCreation.tsx`
- Create: `sidequest-ui/src/components/CharacterCreation/StatArrangePanel.tsx`
- Test: `sidequest-ui/src/components/CharacterCreation/__tests__/StatArrangePanel.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// __tests__/StatArrangePanel.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatArrangePanel } from "../StatArrangePanel";

describe("StatArrangePanel", () => {
  const baseProps = {
    pool: [12, 9, 15, 8, 14, 11],
    assignment: { STR: null, DEX: null, CON: null, INT: null, WIS: null, CHA: null },
    classRequirements: [
      { name: "Fighter", requirementLabel: "STR 9+" },
      { name: "Mage", requirementLabel: "INT 9+" },
      { name: "Cleric", requirementLabel: "WIS 9+" },
      { name: "Thief", requirementLabel: "DEX 9+" },
    ],
    qualifyingClasses: [],
    onAssign: vi.fn(),
    onClear: vi.fn(),
    onConfirm: vi.fn(),
    onReject: vi.fn(),
    confirmEnabled: false,
  };

  it("renders six pool values", () => {
    render(<StatArrangePanel {...baseProps} />);
    expect(screen.getByTestId("arrange-pool-value-0")).toHaveTextContent("12");
    expect(screen.getByTestId("arrange-pool-value-5")).toHaveTextContent("11");
  });

  it("renders six empty stat slots", () => {
    render(<StatArrangePanel {...baseProps} />);
    ["STR", "DEX", "CON", "INT", "WIS", "CHA"].forEach((s) => {
      expect(screen.getByTestId(`arrange-slot-${s}`)).toHaveTextContent("—");
    });
  });

  it("highlights pool value on click", () => {
    render(<StatArrangePanel {...baseProps} />);
    fireEvent.click(screen.getByTestId("arrange-pool-value-0"));
    expect(screen.getByTestId("arrange-pool-value-0")).toHaveAttribute("data-selected", "true");
  });

  it("calls onAssign when pool then slot is tapped", () => {
    const onAssign = vi.fn();
    render(<StatArrangePanel {...baseProps} onAssign={onAssign} />);
    fireEvent.click(screen.getByTestId("arrange-pool-value-2"));  // value 15
    fireEvent.click(screen.getByTestId("arrange-slot-STR"));
    expect(onAssign).toHaveBeenCalledWith({ stat: "STR", value: 15 });
  });

  it("calls onClear when filled slot is tapped", () => {
    const onClear = vi.fn();
    const filled = { ...baseProps, assignment: { ...baseProps.assignment, STR: 14 } };
    render(<StatArrangePanel {...filled} onClear={onClear} />);
    fireEvent.click(screen.getByTestId("arrange-slot-STR"));
    expect(onClear).toHaveBeenCalledWith({ stat: "STR" });
  });

  it("renders class requirements with checkmarks for qualifying classes", () => {
    const props = { ...baseProps, qualifyingClasses: ["Fighter", "Thief"] };
    render(<StatArrangePanel {...props} />);
    expect(screen.getByTestId("arrange-class-Fighter")).toHaveAttribute("data-qualifies", "true");
    expect(screen.getByTestId("arrange-class-Mage")).toHaveAttribute("data-qualifies", "false");
  });

  it("disables confirm button when confirmEnabled is false", () => {
    render(<StatArrangePanel {...baseProps} />);
    expect(screen.getByTestId("arrange-confirm")).toBeDisabled();
  });

  it("enables confirm button when confirmEnabled is true", () => {
    render(<StatArrangePanel {...baseProps} confirmEnabled />);
    expect(screen.getByTestId("arrange-confirm")).toBeEnabled();
  });

  it("calls onReject when reject button is clicked", () => {
    const onReject = vi.fn();
    render(<StatArrangePanel {...baseProps} onReject={onReject} />);
    fireEvent.click(screen.getByTestId("arrange-reject"));
    expect(onReject).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/StatArrangePanel.test.tsx
```

Expected: FAIL — `StatArrangePanel` not found.

- [ ] **Step 3: Implement `StatArrangePanel`**

```tsx
// src/components/CharacterCreation/StatArrangePanel.tsx
import { useState } from "react";

interface ClassRequirement {
  name: string;
  requirementLabel: string;
}

export interface StatArrangePanelProps {
  pool: number[];
  assignment: Record<string, number | null>;
  classRequirements: ClassRequirement[];
  qualifyingClasses: string[];
  onAssign: (payload: { stat: string; value: number }) => void;
  onClear: (payload: { stat: string }) => void;
  onConfirm: () => void;
  onReject: () => void;
  confirmEnabled: boolean;
}

const STAT_ORDER = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

export function StatArrangePanel({
  pool,
  assignment,
  classRequirements,
  qualifyingClasses,
  onAssign,
  onClear,
  onConfirm,
  onReject,
  confirmEnabled,
}: StatArrangePanelProps) {
  // Selected pool index (not value — values can repeat).
  const [selectedPoolIdx, setSelectedPoolIdx] = useState<number | null>(null);

  const handlePoolClick = (idx: number) => {
    setSelectedPoolIdx(idx === selectedPoolIdx ? null : idx);
  };

  const handleSlotClick = (stat: string) => {
    if (assignment[stat] !== null) {
      onClear({ stat });
      return;
    }
    if (selectedPoolIdx === null) return;
    onAssign({ stat, value: pool[selectedPoolIdx] });
    setSelectedPoolIdx(null);
  };

  return (
    <div data-testid="stat-arrange-panel" className="flex flex-col gap-4 w-full max-w-xl">
      {/* Pool */}
      <div className="border-b border-border/40 pb-3">
        <div className="text-xs uppercase tracking-widest text-muted-foreground/60 mb-2">Pool</div>
        <div className="flex gap-2 flex-wrap">
          {pool.map((value, idx) => (
            <button
              key={idx}
              data-testid={`arrange-pool-value-${idx}`}
              data-selected={selectedPoolIdx === idx}
              onClick={() => handlePoolClick(idx)}
              className={`w-12 h-12 rounded border tabular-nums text-lg font-bold ${
                selectedPoolIdx === idx
                  ? "bg-primary/20 border-primary ring-2 ring-primary/50"
                  : "bg-card/50 border-border/50 hover:border-border"
              }`}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      {/* Slots */}
      <div className="grid grid-cols-3 gap-3">
        {STAT_ORDER.map((stat) => {
          const value = assignment[stat];
          return (
            <button
              key={stat}
              data-testid={`arrange-slot-${stat}`}
              onClick={() => handleSlotClick(stat)}
              className="flex flex-col items-center rounded bg-background/40 border border-border/40 py-2 hover:border-border"
            >
              <span className="text-[10px] uppercase tracking-[0.15em] text-muted-foreground/70">
                {stat}
              </span>
              <span className="text-lg font-bold text-[var(--primary)] tabular-nums">
                {value ?? "—"}
              </span>
            </button>
          );
        })}
      </div>

      {/* Class qualification panel */}
      <div className="border-t border-border/40 pt-3">
        <div className="text-xs uppercase tracking-widest text-muted-foreground/60 mb-2">Qualifies</div>
        <ul className="text-sm space-y-1">
          {classRequirements.map((req) => {
            const qualifies = qualifyingClasses.includes(req.name);
            return (
              <li
                key={req.name}
                data-testid={`arrange-class-${req.name}`}
                data-qualifies={qualifies}
                className={qualifies ? "text-foreground" : "text-muted-foreground/60 line-through"}
              >
                {qualifies ? "✓" : "✗"} {req.name} ({req.requirementLabel})
              </li>
            );
          })}
        </ul>
      </div>

      {/* Actions */}
      <div className="flex gap-3 justify-between border-t border-border/40 pt-3">
        <button
          data-testid="arrange-reject"
          onClick={onReject}
          className="text-sm px-4 py-2 rounded border border-border/50 hover:border-border text-muted-foreground hover:text-foreground"
        >
          Reject these dice
        </button>
        <button
          data-testid="arrange-confirm"
          onClick={onConfirm}
          disabled={!confirmEnabled}
          className="text-sm px-4 py-2 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Confirm arrangement
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd sidequest-ui && npx vitest run src/components/CharacterCreation/__tests__/StatArrangePanel.test.tsx
```

Expected: 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add src/components/CharacterCreation/StatArrangePanel.tsx src/components/CharacterCreation/__tests__/StatArrangePanel.test.tsx
git commit -m "feat(chargen): StatArrangePanel — click-to-assign + live class qualify

Pool, six stat slots, live-qualify panel, reject + confirm buttons.
Click pool → click slot to assign; click filled slot to clear.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 6.2: Story render branch

**Files:**
- Create: `sidequest-ui/src/components/CharacterCreation/StoryPanel.tsx`
- Test: `sidequest-ui/src/components/CharacterCreation/__tests__/StoryPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

Test:
- Renders pronoun radio options + freeform input.
- Renders background and description textareas.
- "Let Brecca tell my story" button calls `onAutogen`.
- Confirm button disabled until pronouns set.
- `onConfirm` receives `{ pronouns, background, description }`.
- When `autogenResult` prop changes, textareas populate (player can still edit).

(Test code follows the StatArrangePanel pattern.)

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement `StoryPanel`** with the layout from spec §2.4.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git commit -m "feat(chargen): StoryPanel — pronouns + background + description with autogen

Folds today's pronouns scene with two new freeform fields. Autogen
button populates the two textareas; player edits before confirm.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 6.3: Wire panels into `CharacterCreation.tsx`

**Files:**
- Modify: `sidequest-ui/src/components/CharacterCreation/CharacterCreation.tsx`
- Test: `sidequest-ui/src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx`

- [ ] **Step 1: Read the current dispatch in `CharacterCreation.tsx`** (already cached: 332 lines, switches on `scene.input_type` and `scene.phase`).

- [ ] **Step 2: Write the failing test**

Test that:
- `scene.input_type === "stat_arrange"` renders `<StatArrangePanel>` with the scene's `pool`, `assignment`, `classRequirements`, `qualifyingClasses`, `confirmEnabled`.
- `scene.input_type === "story"` renders `<StoryPanel>`.

- [ ] **Step 3: Run test to verify it fails**

- [ ] **Step 4: Add the two render branches**

```tsx
// In CharacterCreation.tsx, near the existing input_type branches:
if (scene.input_type === "stat_arrange") {
  return (
    <div data-testid="character-creation" className="flex flex-col items-center px-6 py-10 gap-6 max-w-2xl mx-auto">
      <p className="text-lg leading-relaxed italic text-foreground/90 max-w-prose">{scene.prompt}</p>
      <StatArrangePanel
        pool={scene.pool ?? []}
        assignment={scene.assignment ?? {}}
        classRequirements={scene.class_requirements ?? []}
        qualifyingClasses={scene.qualifying_classes ?? []}
        confirmEnabled={scene.confirm_enabled ?? false}
        onAssign={({ stat, value }) =>
          onRespond({ phase: "arrange_assign", stat, value })
        }
        onClear={({ stat }) => onRespond({ phase: "arrange_clear", stat })}
        onConfirm={() => onRespond({ phase: "arrange_confirm" })}
        onReject={() => onRespond({ phase: "arrange_reject" })}
      />
    </div>
  );
}

if (scene.input_type === "story") {
  return (
    <div data-testid="character-creation" className="flex flex-col items-center px-6 py-10 gap-6 max-w-2xl mx-auto">
      <p className="text-lg leading-relaxed italic text-foreground/90 max-w-prose">{scene.prompt}</p>
      <StoryPanel
        pronounsOptions={scene.pronouns_options ?? []}
        pronounsAllowFreeform={scene.pronouns_allow_freeform ?? true}
        backgroundOptional={scene.background_optional ?? true}
        descriptionOptional={scene.description_optional ?? true}
        autogenAvailable={scene.autogen_available ?? false}
        autogenResult={scene.autogen_result}
        onAutogen={() => onRespond({ phase: "story_autogen" })}
        onConfirm={(payload) => onRespond({ phase: "story_confirm", ...payload })}
      />
    </div>
  );
}
```

Update `CreationScene` interface to declare the new optional fields.

- [ ] **Step 5: Run test to verify it passes**

- [ ] **Step 6: Commit**

```bash
cd sidequest-ui
git commit -m "feat(chargen): wire stat_arrange + story render branches

CharacterCreation.tsx dispatches on scene.input_type to the new panels.
Adds the seven new optional CreationScene fields.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 6.4: Remove the Pencil edit affordance

**Files:**
- Modify: `sidequest-ui/src/components/CharacterCreation/CharacterCreation.tsx` — remove the per-section Pencil button + onClick (lines ~176-184 in current file)
- Modify: `sidequest-ui/src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx` — remove tests that exercised the Pencil

- [ ] **Step 1: Read the current confirmation render branch** (lines 122-209 in current file).

- [ ] **Step 2: Delete the Pencil button JSX, the `Pencil` import, and the `onRespond({action: "edit", target_step: index})` call.**

- [ ] **Step 3: Update tests** — delete or rewrite assertions that referenced `review-edit-${key}` testids.

- [ ] **Step 4: Run UI test suite**

```bash
cd sidequest-ui && npm test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add src/components/CharacterCreation/CharacterCreation.tsx src/components/CharacterCreation/__tests__/CharacterCreation.test.tsx
git commit -m "refactor(chargen): drop Pencil edit affordance from confirmation

Per chargen-big-improvements design — characters evolve through play.
Server-side handler deletion lands in sidequest-server PR.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

### Task 6.5: Push UI PR

- [ ] **Step 1: Run UI checks**

```bash
cd sidequest-ui && npm run lint && npm test
```

- [ ] **Step 2: Push and open PR (target develop)**

```bash
cd sidequest-ui
git push -u origin feat/cnc-chargen-visible-dice
gh pr create --base develop --title "feat(chargen): C&C visible dice + arrange + story UI" --body "$(cat <<'EOF'
## Summary
- StatArrangePanel — click-to-assign pool, six stat slots, live-qualify panel, reject + confirm
- StoryPanel — pronouns radio + background + description textareas + autogen
- Drops Pencil edit affordance from confirmation screen

## Spec
docs/superpowers/specs/2026-05-09-cnc-chargen-big-improvements-design.md (orchestrator repo)

## Coordinated PRs
- sidequest-server: builder FSM + protocol + cleanup
- sidequest-content: char_creation.yaml + progression.yaml

## Test plan
- [ ] npm test (Vitest)
- [ ] npm run lint
- [ ] Manual: just up, create C&C character, exercise arrange + reject + story autogen

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Phase 7 — Content PR push

### Task 7.1: Push content PR (target develop)

```bash
cd sidequest-content
git push -u origin feat/cnc-chargen-visible-dice
gh pr create --base develop --title "content(cnc): chargen 6-scene visible-dice flow" --body "$(cat <<'EOF'
## Summary
- char_creation.yaml: 5-scene → 6-scene flow (roll/arrange/calling/story/kit/mouth)
- progression.yaml: drop prime_req_bonus (if present)

## Spec
docs/superpowers/specs/2026-05-09-cnc-chargen-big-improvements-design.md (orchestrator repo)

## Coordinated PRs
- sidequest-server: builder FSM + protocol + cleanup
- sidequest-ui: stat_arrange + story render branches, Pencil removal

## Test plan
- [ ] sidequest-server pack-load smoke
- [ ] Manual: just up, create C&C character

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Phase 8 — Cross-repo verification

### Task 8.1: End-to-end smoke test

> **Run only after all three PRs are merged to develop.**

- [ ] **Step 1: Update all repos**

```bash
just status
cd sidequest-server && git checkout develop && git pull && cd ..
cd sidequest-ui && git checkout develop && git pull && cd ..
cd sidequest-content && git checkout develop && git pull && cd ..
```

- [ ] **Step 2: Boot the stack**

```bash
just up
```

- [ ] **Step 3: Manual smoke**

In a browser at `http://localhost:5173`:

- [ ] Connect → choose C&C
- [ ] Scene 1: see six dice (numeric reveal in degraded mode) land in the pool
- [ ] Scene 2: click a number, click a slot — assignment happens
- [ ] Scene 2: class panel updates as slots fill
- [ ] Scene 2: click Reject → six new numbers
- [ ] Scene 2: click filled slot → number returns to pool
- [ ] Scene 2: fill all six → Confirm enables
- [ ] Scene 3: only qualifying classes appear; pick one
- [ ] Scene 4: pronouns radio + background + description textareas
- [ ] Scene 4: click "Let Brecca tell my story" → textareas populate; edit one
- [ ] Scene 4: confirm
- [ ] Scene 5: kit reveal
- [ ] Scene 6: mouth, then character finalizes
- [ ] Open `/dashboard` (OTEL): see `chargen.roll.die` ×6, `chargen.arrange.assign`, `chargen.arrange.confirm`, `chargen.class.selected`, `chargen.story.autogen`, `chargen.story.confirm`

- [ ] **Step 4: Tear down**

```bash
just down
```

### Task 8.2: Update ADR-014 / ADR-015 / ADR-016 references if needed

- [ ] **Step 1: Re-read ADR-014, ADR-015, ADR-016** for accuracy after the FSM extension.

- [ ] **Step 2: If any becomes inaccurate, append a stale-pointer note** per memory rule "ADR hygiene priority — current accuracy beats historical preservation."

- [ ] **Step 3: Commit (orchestrator repo, target main)** if any ADR changed.

### Task 8.3: Update sprint tracker

- [ ] **Step 1:** This story should already be in the sprint backlog. Drive it to done via `pf` workflow as usual.

---

## Self-Review Notes

**Spec coverage:**
- §2.1 the_roll → Tasks 2.1, 3.2, 4.3
- §2.2 the_arrangement → Tasks 1.2, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.4, 6.1, 6.3
- §2.3 the_calling → Task 4.5
- §2.4 the_story → Tasks 1.2, 3.5, 3.6, 4.1, 4.2, 4.4, 6.2, 6.3
- §2.5 the_kit → unchanged behavior; covered by Task 8.1 smoke
- §2.6 the_mouth → unchanged
- §3.1 silent reroll loop removed → Task 5.1
- §3.2 prime-req XP removed → Task 2.2
- §3.3 Pencil removed → Tasks 5.2, 6.4
- §4 server architecture → Phases 3-5
- §5 UI architecture → Phase 6
- §7 OTEL → Task 4.4
- §10 repo split → branches in Task 0.1, three PRs across Phases 5/6/7

**Placeholder check:**
- A handful of code blocks reference `RulesConfig.minimal_for_test()` and `ClassDef(... ...)` with ellipses — these are flagged with explicit "if absent, build a minimal fixture" instructions, not silent placeholders.
- One `_builder_at_story_scene()` helper is described and pointed at the prior test pattern.
- These are knowable-from-code helpers, not requirements gaps.

**Type consistency:**
- `arrangement_pool`, `arrangement_assignment` consistent across builder, payloads, UI.
- `qualifying_classes_arrangement` → matches `ArrangementPayload.qualifying_classes` (list of class names) → matches `StatArrangePanelProps.qualifyingClasses` (list of class names).
- `StoryInput` (server dataclass) ↔ `StoryConfirmRequest` (protocol pydantic) ↔ `onConfirm({pronouns, background, description})` (UI callback) — all carry the same three fields.
- Phase numbering is contiguous: 0, 1, 2, 3, 4, 5, 6, 7, 8.

**Scope:**
- Three repos, but a single coherent feature with explicit dependency order. Each repo's PR can be reviewed independently; merges land in this order: content → server → ui (content blocks server tests; server blocks UI runtime).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-cnc-chargen-big-improvements.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
