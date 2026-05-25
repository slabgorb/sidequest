# SWN Ablative HP Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reintroduce ablative HP as the personal lethality substrate beneath the confrontation dials — a first-class `HpPool` on every creature, dice-rolled weapon damage via the existing player-facing overlay, per-genre 0-HP verdicts, and an OTEL `state_patch` span on every HP mutation — per ADR-114.

**Architecture:** HP reclaims the personal vitality/damage role that ADR-078 gave `EdgePool`. The confrontation dials (ADR-033) are untouched; beats gain an *optional* damage channel (`strike` deals dice-rolled weapon damage to HP, `brace` mitigates). Damage rolls reuse the ADR-074/075 dice protocol. The lethality arbiter and the `CatalogItem` catalog are re-pointed from edge to HP. This is largely **deleting a translation** — content already authors B/X HP and the materializer currently throws it away.

**Tech Stack:** Python 3 / pydantic v2 (`sidequest-server`), pytest (`-n auto` via addopts), uv. OTEL spans via `sidequest.telemetry.spans`. Existing dice grammar in `sidequest/game/dice.py` and `sidequest/protocol/dice.py`.

**Read first:**
- ADR-114 (`docs/adr/114-ablative-hp-substrate.md`) — the decision this executes.
- The superseded ADR-078 (`docs/adr/078-edge-composure-advancement-rituals.md`) — what `EdgePool` was and why it's being replaced.
- Project rule **"No Source-Text Wiring Tests"** (`sidequest-server/CLAUDE.md`) — wiring is proven by OTEL span assertions or fixture-driven behavior tests, never by grepping source. Several tasks below rely on this.
- Project memory: legacy saves are throwaway — **no Edge→HP save migration is built** (`feedback_legacy_saves.md`). Fresh sessions seed HP from content.

**Naming convention for this plan:** the personal vitality field on `CreatureCore` moves from `edge: EdgePool` to `hp: HpPool`. Where ADR-078 used `edge`/`Edge`, the HP analogue uses `hp`/`Hp`. Keep this 1:1 so later tasks match earlier ones.

**Branch:** This change touches `sidequest-server` (engine) and `sidequest-content` (YAML key renames in `lethality_policy.yaml` + the `space_opera` catalog damage values). Branch **each** changed subrepo off its base (`develop`) before the first commit anywhere — the pf commit hook scans all subrepos. Orchestrator branches off `main`.

---

## EXECUTION RE-SEQUENCE (2026-05-25, post-Task-1 discovery)

Task 1's grep proved the `core.edge`→`core.hp` field rename cascades into ~15 files,
not the handful the original task split named. Deferring those to a catch-all cleanup
would leave the suite red across eight intermediate commits. **Revised order — rename
to green first, then build the damage-channel feature on top:**

1. **Task 1** ✅ DONE (`4191f28`) — `HpPool` + `CreatureCore.edge`→`hp` + `apply_hp_delta`.
2. **Task 2** — `hp_pool_from_config` helper + chargen wiring (`builder.py`), `chargen.hp_seeded` span. (Original "Task 3" body below.)
3. **Task 3 (consolidated)** — behavior-preserving `edge`→`hp` re-point of ALL remaining callers, restore the tree to green, and delete the dead Edge code. Absorbs original Tasks 2 (materializer), 8 (lethality + content YAML), and 9's cleanup. **Includes** re-pointing the existing `agents/tools/apply_damage.py` narrator tool (`apply_edge_delta`→`apply_hp_delta`, span attr `target_edge_after`→`target_hp_after`) — kept as a **complementary** damage path to the beat channel per Keith's 2026-05-25 decision and ADR-114 §2 addendum. File list (from Task 1's grep): `world_materialization.py`, `game/character.py` (`is_broken`/`edge_fraction`), `game/rig_crash.py` (driver hit → HP), `game/session.py`, `server/views.py`, `server/websocket_session_handler.py`, `server/narration_apply.py`, `server/dispatch/encounter_lifecycle.py`, `server/dispatch/yield_action.py`, `game/mechanical_census.py`, `game/commands.py`, `game/beat_kinds.py` (edge-delta sites), `agents/tools/{query_character,query_encounter,apply_damage}.py`, `agents/lethality_arbiter.py`, `genre/models/lethality.py`, `genre/models/advancement.py` (`EdgeMaxBonus`→`HpMaxBonus`, `EdgeRecovery`→`HpRecovery`), `game/__init__.py` (drop Edge re-exports), and every `genre_packs/*/lethality_policy.yaml` (`verdicts_on_zero_edge`→`verdicts_on_zero_hp`). **Acceptance gate:** `grep -rn "EdgePool\|apply_edge_delta\|placeholder_edge_pool\|verdicts_on_zero_edge\|core\.edge\b" sidequest/` returns only ADR-historical comments; `uv run pytest && uv run ruff check . && uv run pyright` all green. Two-stage review (this is the substantive one).
4. **Task 4** — `CatalogItem.damage` + `mitigation` schema. (Body below.)
5. **Task 5** — `BeatDef.damage_channel` schema. (Body below.)
6. **Task 6** — `apply_beat_hp_channel` + `state_patch` span (beat strike/brace path; `apply_damage` already re-pointed in Task 3 and stays as the narrator's freeform sibling). (Body below.)
7. **Task 7** — damage rolls ride the player-facing dice overlay. (Body below.)
8. **Task 8** — narrative sheet exposes the HP number (ADR-040 amendment). (Original Task 9 narrative-sheet steps.)
9. **Task 9 (e2e)** — `space_opera` canary content + both-layers-in-one-turn test + flip ADR-114 to `live`. (Original Task 10.)

The task bodies below retain their TDD steps and code/test blocks; only the order and
the Task-3 consolidation changed. Where a body says "leave the edge path untouched for
this task," that is now Task 3's job — read this re-sequence as authoritative on ordering.

---

## File Structure

**`sidequest-server` (engine):**
- `sidequest/game/creature_core.py` — **modify**: add `HpPool`, `hp_pool_from_hp()`, `hp_pool_from_config()`; replace the `edge: EdgePool` field on `CreatureCore` with `hp: HpPool`; add `apply_hp_delta()`. `EdgePool` and its helpers are **deleted** in the same file (no dead code per CLAUDE.md).
- `sidequest/game/world_materialization.py` — **modify**: `_apply_npc()` and the dungeon CR seam stop calling the HP→Edge translator; seed `HpPool` from the authored `hp`.
- `sidequest/game/builder.py` — **modify**: chargen seeds `HpPool` from class base + CON mod (re-point of the ADR-078 amendment seed).
- `sidequest/genre/models/inventory.py` — **modify**: add `DamageSpec`, `CatalogItem.damage`, `CatalogItem.mitigation`.
- `sidequest/genre/models/rules.py` — **modify**: add `DamageChannel` enum + `BeatDef.damage_channel`, `damage_override`, `mitigation_override`; add an `unarmed_damage` field to the rules/combat config.
- `sidequest/genre/models/lethality.py` — **modify**: rename `verdicts_on_zero_edge` → `verdicts_on_zero_hp`.
- `sidequest/agents/lethality_arbiter.py` — **modify**: trigger on `core.hp.current == 0`, read `verdicts_on_zero_hp`.
- `sidequest/game/beat_kinds.py` — **modify**: add the strike/brace HP-damage channel beside the existing edge-delta path; emit `state_patch` on every HP delta.
- `sidequest/genre/models/advancement.py` — **modify**: rename the two vitality variants (`EdgeMaxBonus`→`HpMaxBonus`, `EdgeRecovery`→`HpRecovery`) at the data-shape layer.
- `sidequest/game/narrative_sheet.py` — **modify**: expose the raw HP number (ADR-040 amendment) alongside the existing band.
- `sidequest/server/dispatch/dice.py` — **modify**: build a damage `DiceRequestPayload` from the equipped weapon's `DamageSpec` for `strike` beats.

**`sidequest-content`:**
- `genre_packs/space_opera/lethality_policy.yaml` (+ every other pack's copy) — **modify**: YAML key `verdicts_on_zero_edge` → `verdicts_on_zero_hp`.
- `genre_packs/space_opera/inventory.yaml` — **modify** (Lane A coordination): weapons gain `damage:`, armor gains `mitigation:`. *Authored under the Lane A plan; this plan only lands the schema + one canary item to prove wiring.*
- `genre_packs/space_opera/rules.yaml` — **modify**: combat beats gain `damage_channel:`; add `unarmed_damage`.

---

## Task 1: `HpPool` type + `apply_hp_delta`, replacing `EdgePool` on `CreatureCore`

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py`
- Test: `sidequest-server/tests/game/test_hp_pool.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_hp_pool.py
import pytest
from sidequest.game.creature_core import HpPool, hp_pool_from_hp


def test_hp_pool_clamps_to_zero_and_max():
    pool = HpPool(current=8, max=8, base_max=8)
    assert pool.apply_delta(-3) == 5
    assert pool.apply_delta(-100) == 0          # floored at 0
    assert pool.apply_delta(50) == 8            # capped at max
    assert pool.current == 8


def test_hp_pool_from_hp_seeds_full_floored_at_one():
    pool = hp_pool_from_hp(30)
    assert (pool.current, pool.max, pool.base_max) == (30, 30, 30)
    # authored hp:0 must remain a representable, alive actor
    assert hp_pool_from_hp(0).max == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_pool.py -v`
Expected: FAIL — `ImportError: cannot import name 'HpPool'`.

- [ ] **Step 3: Add `HpPool` + `hp_pool_from_hp` and delete `EdgePool`'s damage-track equivalents**

In `creature_core.py`, add (mirroring the deleted `EdgePool` shape, minus the composure-specific `recovery_triggers`/`thresholds` which were the Edge-advancement scaffold):

```python
class HpPool(BaseModel):
    """First-class personal vitality pool (ADR-114). Replaces EdgePool as the
    damage/lethality track. ``current`` is clamped to ``[0, max]``."""

    model_config = {"extra": "forbid"}

    current: int
    max: int
    base_max: int

    def apply_delta(self, delta: int) -> int:
        raw = self.current + delta
        self.current = max(0, min(self.max, raw))
        return self.current


def hp_pool_from_hp(hp: int) -> HpPool:
    """Seed an :class:`HpPool` from an authored B/X ``hp`` integer.

    ADR-114 §1: content YAML already carries B/X HP. The single canonical
    seeder — ``current == max == base_max == authored hp``, floored at 1
    because a pool needs a positive ceiling (an ``hp: 0`` creature must
    still be a representable, alive actor). This REPLACES
    ``creature_edge_pool_from_hp`` (which re-interpreted HP as composure);
    HP is now seeded as-authored, not translated away.
    """
    seed = max(1, hp)
    return HpPool(current=seed, max=seed, base_max=seed)
```

Then on `CreatureCore` (currently `creature_core.py:218`), replace the field:

```python
    # was: edge: EdgePool = Field(default_factory=placeholder_edge_pool)
    hp: HpPool = Field(default_factory=lambda: HpPool(current=10, max=10, base_max=10))
```

And replace `apply_edge_delta` (currently `creature_core.py:260`):

```python
    def apply_hp_delta(self, delta: int) -> int:
        """Apply an HP delta and return the new current value."""
        return self.hp.apply_delta(delta)
```

Delete `EdgePool`, `EdgeThreshold`, `RecoveryTrigger`, `placeholder_edge_pool`, `creature_edge_pool_from_hp`, `EdgeConfigMissingClassError`, and `edge_pool_from_config` **only after** Tasks 2–3 and 8 stop referencing them — to keep each commit compiling, defer the physical deletion to Task 9's cleanup step and leave them in place for now. (They are not re-exported as new API; nothing new calls them.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_pool.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/creature_core.py tests/game/test_hp_pool.py
git commit -m "feat(hp): add HpPool + hp_pool_from_hp, swap CreatureCore.edge→hp (ADR-114)"
```

---

## Task 2: Materializer stops translating HP away — seed `HpPool` from authored `hp`

**Files:**
- Modify: `sidequest-server/sidequest/game/world_materialization.py` (`_apply_npc()` new-NPC branch; the dungeon CR→pool seam at the three `edge=placeholder_edge_pool()` / `creature_edge_pool_from_hp` sites — locate via `grep -n "edge=placeholder_edge_pool\|creature_edge_pool_from_hp" sidequest/game/world_materialization.py`)
- Test: `sidequest-server/tests/game/test_materializer_hp.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_materializer_hp.py
from sidequest.game.creature_core import CreatureCore, hp_pool_from_hp


def test_authored_hp_survives_to_creature_core():
    """ADR-114: the materializer must seed HpPool from authored hp, not
    discard it. Constructing a CreatureCore from an authored hp=24 must
    yield hp.max == 24 (was: translated into a composure pool)."""
    core = CreatureCore(name="Patient Butcher", description="x", personality="x",
                         hp=hp_pool_from_hp(24))
    assert core.hp.max == 24
    assert core.hp.current == 24
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_materializer_hp.py -v`
Expected: FAIL — `CreatureCore` still takes `edge=...`, not `hp=...` (until Task 1 merged) / `TypeError` on unknown kwarg if run before Task 1. After Task 1 it passes the construction but you still must fix the materializer call-sites below.

- [ ] **Step 3: Re-point every materializer construction site**

In `world_materialization.py`, every `CreatureCore(...)` constructor currently passes `edge=placeholder_edge_pool()` (the new-NPC branch ~`:525`) or `edge=creature_edge_pool_from_hp(...)` (dungeon seam). Replace each:

```python
# new-NPC branch (_apply_npc): NPCs authored without an explicit hp get the default
core = CreatureCore(
    name=npc_data.name,
    description=npc_data.description or "An NPC.",
    personality=npc_data.personality or "Neutral.",
    level=1,
    xp=0,
    inventory=Inventory(),
    statuses=[],
    hp=hp_pool_from_hp(npc_data.hp) if getattr(npc_data, "hp", None) else HpPool(current=10, max=10, base_max=10),
    acquired_advancements=[],
)
```

For the dungeon/creature seam that previously called `creature_edge_pool_from_hp(creature.hp)`, call `hp_pool_from_hp(creature.hp)` instead. Update imports at the top of the file: drop `placeholder_edge_pool`, `creature_edge_pool_from_hp`; add `HpPool`, `hp_pool_from_hp`.

The docstring at `:331` ("hp/max_hp/ac from chapter are intentionally unused — the placeholder EdgePool stays as-is") is now **false** — update it to: *"hp from chapter seeds HpPool directly (ADR-114); max_hp/ac remain advisory."*

- [ ] **Step 4: Run to verify it passes + no regressions in the materializer suite**

Run: `cd sidequest-server && uv run pytest tests/game/test_materializer_hp.py -v && uv run pytest -k materializ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/world_materialization.py tests/game/test_materializer_hp.py
git commit -m "feat(hp): materializer seeds HpPool from authored hp, stops translating to composure (ADR-114)"
```

---

## Task 3: Chargen seeds `HpPool` from class base + CON modifier

**Files:**
- Modify: `sidequest-server/sidequest/game/creature_core.py` (add `hp_pool_from_config`)
- Modify: `sidequest-server/sidequest/game/builder.py` (locate the edge-seed call via `grep -n "edge_pool_from_config\|edge_seeded" sidequest/game/builder.py`)
- Test: `sidequest-server/tests/game/test_hp_seed_from_config.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_hp_seed_from_config.py
import pytest
from sidequest.game.creature_core import hp_pool_from_config, HpConfigMissingClassError


class _Cfg:
    base_max_by_class = {"Fighter": 8, "Mage": 4}


def test_hp_seed_applies_con_modifier_floored_at_one():
    # Fighter base 8, CON 17 (+3) → 11
    assert hp_pool_from_config(_Cfg(), "Fighter", con_score=17).base_max == 11
    # Mage base 4, CON 6 (-2) → 2
    assert hp_pool_from_config(_Cfg(), "Mage", con_score=6).base_max == 2
    # floor at 1 even if class base + con mod would go below
    assert hp_pool_from_config(_Cfg(), "Mage", con_score=3).base_max == 1  # 4 + (-4) → floored 1


def test_missing_class_raises_loudly():
    with pytest.raises(HpConfigMissingClassError):
        hp_pool_from_config(_Cfg(), "Psion", con_score=10)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_seed_from_config.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Add `hp_pool_from_config` (re-point of `edge_pool_from_config`)**

In `creature_core.py`:

```python
class HpConfigMissingClassError(KeyError):
    """Genre pack declared an HP config but omitted a base_max entry for the
    character's class. Fail loud at the boundary (SOUL.md: no silent fallbacks)."""

    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        super().__init__(f"hp base_max_by_class missing entry for class '{class_name}'")


def hp_pool_from_config(hp_config: object, class_name: str, *, con_score: int) -> HpPool:
    """Build a genre-authored HpPool from class base + CON modifier (ADR-114 §1,
    re-pointing ADR-078's 2026-05-10 CON-mod seed from Edge to HP).

    base_max = max(1, base_max_by_class[class_name] + floor((con_score - 10) / 2)).
    ``hp_config`` is typed ``object`` to avoid a circular import with the genre
    layer; we duck-type ``base_max_by_class``."""
    base_max_by_class = getattr(hp_config, "base_max_by_class", {})
    if class_name not in base_max_by_class:
        raise HpConfigMissingClassError(class_name=class_name)
    con_modifier = (con_score - 10) // 2
    base_max = max(1, base_max_by_class[class_name] + con_modifier)
    return HpPool(current=base_max, max=base_max, base_max=base_max)
```

- [ ] **Step 4: Wire it in `builder.py`**

Find the chargen edge-seed block (the `edge_pool_from_config(...)` call and the `chargen.edge_seeded` OTEL event). Replace the call with `hp_pool_from_config(hp_config, class_name, con_score=<rolled CON>)`, assign to the new core's `hp` field, and rename the OTEL event `chargen.edge_seeded` → `chargen.hp_seeded` (keep its `con_modifier` / `seed_formula` attributes; set `seed_formula="class_base+con_mod"`). The genre `hp_config` is whatever the loader exposes for class baselines — reuse the same config object the edge path read (the genre `edge_config` block becomes the `hp` baseline block; coordinate the YAML key rename with content in Task 8's pack pass, or keep the existing key name and just re-read it for HP — pick one and apply it consistently; the *engine* must not silently fall back if the block is absent).

- [ ] **Step 5: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_seed_from_config.py -v && uv run pytest -k chargen -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/creature_core.py sidequest/game/builder.py tests/game/test_hp_seed_from_config.py
git commit -m "feat(hp): chargen seeds HpPool from class base + CON mod, chargen.hp_seeded span (ADR-114)"
```

---

## Task 4: `CatalogItem.damage` + `mitigation` schema with pack-load dice validation

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/inventory.py`
- Test: `sidequest-server/tests/genre/test_catalog_item_damage.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_catalog_item_damage.py
import pytest
from pydantic import ValidationError
from sidequest.genre.models.inventory import CatalogItem, DamageSpec


def test_weapon_carries_swn_native_damage_dice():
    item = CatalogItem(id="mag_pistol", name="Mag Pistol", description="x",
                       category="weapon", damage=DamageSpec(dice="1d6", bonus=1))
    assert item.damage.dice == "1d6"
    assert item.damage.bonus == 1


def test_armor_carries_flat_mitigation():
    item = CatalogItem(id="armored_vac", name="Armored Vacc Suit", description="x",
                       category="armor", mitigation=2)
    assert item.mitigation == 2


def test_unparseable_or_unsupported_damage_dice_rejected_at_load():
    # garbage notation
    with pytest.raises(ValidationError):
        DamageSpec(dice="banana")
    # unsupported face count (no d7 die in protocol/dice.py)
    with pytest.raises(ValidationError):
        DamageSpec(dice="1d7")


def test_damage_absent_by_default():
    item = CatalogItem(id="ration", name="Ration", description="x", category="consumable")
    assert item.damage is None and item.mitigation is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_catalog_item_damage.py -v`
Expected: FAIL — `ImportError: cannot import name 'DamageSpec'`.

- [ ] **Step 3: Implement `DamageSpec` + fields with a validator**

In `inventory.py`. The validator parses `NdM` and checks `M` against the supported faces enum (reuse `sidequest.protocol.dice.DieSides` — `_SUPPORTED_SIDES`), failing loud per `extra="forbid"` discipline:

```python
import re
from sidequest.protocol.dice import DieSides

_DICE_RE = re.compile(r"^(?P<count>\d+)d(?P<faces>\d+)$")


class DamageSpec(BaseModel):
    """Weapon damage descriptor (ADR-114 §3). SWN-native dice (1d6…2d12) so the
    value is concrete and feeds the ADR-074/075 dice overlay directly."""

    model_config = {"extra": "forbid"}

    dice: str          # "NdM" — M must be a supported DieSides face count
    bonus: int = 0

    @field_validator("dice")
    @classmethod
    def _valid_dice(cls, v: str) -> str:
        m = _DICE_RE.match(v.strip())
        if not m:
            raise ValueError(f"damage dice {v!r} is not NdM notation")
        count, faces = int(m["count"]), int(m["faces"])
        if count < 1:
            raise ValueError(f"damage dice {v!r} needs at least 1 die")
        if DieSides.from_wire(faces) is DieSides.Unknown:
            raise ValueError(f"damage dice {v!r} uses unsupported face count d{faces}")
        return v
```

Add `from pydantic import field_validator` to the imports, and to `CatalogItem`:

```python
    damage: DamageSpec | None = None    # weapons
    mitigation: int | None = None       # armor: flat damage reduction (SWN soak)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_catalog_item_damage.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/inventory.py tests/genre/test_catalog_item_damage.py
git commit -m "feat(hp): CatalogItem.damage (SWN dice) + mitigation, load-time dice validation (ADR-114)"
```

---

## Task 5: `BeatDef` damage channel schema

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (`BeatDef`, ~`:120`; add the enum near the other beat enums)
- Test: `sidequest-server/tests/genre/test_beat_damage_channel.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/genre/test_beat_damage_channel.py
from sidequest.genre.models.rules import BeatDef, DamageChannel


def _beat(**kw):
    base = dict(id="b", label="L", kind="strike", stat_check="MIGHT")
    base.update(kw)
    return BeatDef(**base)


def test_damage_channel_defaults_to_none():
    assert _beat().damage_channel is DamageChannel.none


def test_strike_and_brace_channels_parse():
    assert _beat(damage_channel="strike").damage_channel is DamageChannel.strike
    assert _beat(damage_channel="brace").damage_channel is DamageChannel.brace


def test_creature_natural_attack_override():
    b = _beat(damage_channel="strike", damage_override={"dice": "1d8", "bonus": 0})
    assert b.damage_override.dice == "1d8"
    assert _beat(damage_channel="brace", mitigation_override=1).mitigation_override == 1
```

Note: `BeatDef.kind` is a closed `BeatKind` enum — confirm `"strike"` and `"brace"` are existing members via `grep -n "class BeatKind" -A12 sidequest/genre/models/rules.py`. If `brace` is not a member, this plan's damage channel is independent of `kind`: the `damage_channel` field is what the engine reads (Task 6), so `kind` can stay whatever the pacing design uses. Adjust the test's `kind=` to a valid member if needed; `damage_channel` is the load-bearing field.

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_beat_damage_channel.py -v`
Expected: FAIL — `ImportError: cannot import name 'DamageChannel'`.

- [ ] **Step 3: Implement the enum + fields**

In `rules.py`, reuse `DamageSpec` from `inventory.py` for `damage_override`:

```python
from enum import StrEnum
from sidequest.genre.models.inventory import DamageSpec


class DamageChannel(StrEnum):
    none = "none"       # dial-only beat (angle/push) — never touches HP
    strike = "strike"   # rolls weapon (or override) damage onto target HP
    brace = "brace"     # mitigates incoming HP damage this round
```

On `BeatDef` (beside the existing `edge_delta`/`target_edge_delta` fields):

```python
    damage_channel: DamageChannel = DamageChannel.none
    damage_override: DamageSpec | None = None   # creature natural attack (no catalog weapon)
    mitigation_override: int | None = None      # brace beat with no armor item
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_beat_damage_channel.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/genre/models/rules.py tests/genre/test_beat_damage_channel.py
git commit -m "feat(hp): BeatDef.damage_channel (strike/brace/none) + overrides (ADR-114)"
```

---

## Task 6: Strike/brace HP-damage resolution in `apply_beat`, with `state_patch` span

**Files:**
- Modify: `sidequest-server/sidequest/game/beat_kinds.py` (the side-effect block at `:543–642` that today handles `edge_delta`/`target_edge_delta`)
- Modify: `sidequest-server/sidequest/telemetry/spans/state_patch.py` (add an `hp_delta` span helper if one is not already exposed — check `grep -n "hp\|def .*_span" sidequest/telemetry/spans/state_patch.py`)
- Test: `sidequest-server/tests/game/test_beat_hp_channel.py` (create)

**Design note:** This task applies a **pre-rolled** damage total (the dice are rolled player-facing in Task 7; here `apply_beat` receives the resolved total via the same resolver-injection pattern the edge path already uses — see `edge_resolver` at `beat_kinds.py:553`). Mirror that: add a `damage_resolver`/`damage_total` parameter so the pure engine function stays deterministic and testable. Do not roll dice inside `apply_beat`.

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_beat_hp_channel.py
from sidequest.game.creature_core import CreatureCore, HpPool
from sidequest.game.beat_kinds import apply_beat_hp_channel  # pure helper added this task


def _core(hp, mitig=0):
    c = CreatureCore(name="t", description="x", personality="x",
                     hp=HpPool(current=hp, max=hp, base_max=hp))
    return c


def test_strike_subtracts_damage_total_minus_mitigation():
    target = _core(10)
    # damage_total=6, target mitigation=2 → 4 applied → 6 remaining
    applied = apply_beat_hp_channel(target=target, channel="strike",
                                    damage_total=6, target_mitigation=2)
    assert applied == 4
    assert target.hp.current == 6


def test_strike_floors_at_zero():
    target = _core(3)
    apply_beat_hp_channel(target=target, channel="strike", damage_total=99, target_mitigation=0)
    assert target.hp.current == 0


def test_mitigation_never_makes_a_strike_heal():
    target = _core(10)
    applied = apply_beat_hp_channel(target=target, channel="strike",
                                    damage_total=1, target_mitigation=5)
    assert applied == 0            # max(0, 1-5)
    assert target.hp.current == 10
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_beat_hp_channel.py -v`
Expected: FAIL — `ImportError: cannot import name 'apply_beat_hp_channel'`.

- [ ] **Step 3: Implement the pure HP-channel helper + emit `state_patch`**

In `beat_kinds.py`:

```python
from sidequest.telemetry.spans import state_patch_hp_span  # added in this task's span step


def apply_beat_hp_channel(*, target, channel: str, damage_total: int,
                          target_mitigation: int, source_beat_id: str = "?") -> int:
    """Apply a strike beat's damage to target HP, after flat mitigation.

    Returns the HP actually removed (>= 0). ADR-114 §2: brace is a defensive
    posture handled by passing its mitigation into the NEXT strike's
    ``target_mitigation`` — it does not itself mutate HP, so this helper is a
    no-op for channel != "strike". Every HP delta emits a state_patch span
    (ADR-114 §6 — GM-panel lie detector)."""
    if channel != "strike" or damage_total <= 0:
        return 0
    applied = max(0, damage_total - max(0, target_mitigation))
    if applied == 0:
        return 0
    before = target.hp.current
    target.apply_hp_delta(-applied)
    after = target.hp.current
    state_patch_hp_span(actor=target.name, delta=-applied, source=source_beat_id,
                        current=after, maximum=target.hp.max)
    return before - after
```

Add the span helper in `state_patch.py` (follow the existing span-function shape in that module — e.g. `quest_update_span` at `:56`):

```python
SPAN_STATE_PATCH_HP = "state_patch"  # reuse the existing state_patch route (ADR-114 §6)

def state_patch_hp_span(*, actor: str, delta: int, source: str, current: int, maximum: int):
    # emit on the state_patch route with hp-specific attributes
    ...  # mirror the module's existing emit pattern; attributes:
         # {"field": "hp", "actor": actor, "delta": delta, "source": source,
         #  "current": current, "max": maximum}
```

Then in the existing side-effect block (`beat_kinds.py:543` onward), after the edge-delta handling, read `beat.damage_channel`; for `strike`, resolve `damage_total` from the injected resolver (Task 7 supplies it from the weapon dice) and `target_mitigation` from the target's equipped armor `CatalogItem.mitigation`, then call `apply_beat_hp_channel(...)`. The edge-delta path is **removed** in Task 9's cleanup once HP is proven; for this task leave it untouched so the commit compiles.

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_beat_hp_channel.py -v`
Expected: PASS.

- [ ] **Step 5: Wiring test — `state_patch` span fires on a real strike**

Per CLAUDE.md "No Source-Text Wiring Tests," prove the wiring with an OTEL span assertion, not a grep. Add to the same test file a test that captures emitted spans (use the project's span-capture fixture — find it via `grep -rln "def.*span.*fixture\|capture_spans\|InMemorySpan" tests/`) and asserts a `state_patch` span with `field=="hp"` fired after `apply_beat_hp_channel(... channel="strike", damage_total=5 ...)`.

Run: `cd sidequest-server && uv run pytest tests/game/test_beat_hp_channel.py -v`
Expected: PASS — span captured.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/beat_kinds.py sidequest/telemetry/spans/state_patch.py tests/game/test_beat_hp_channel.py
git commit -m "feat(hp): strike/brace HP-damage channel in apply_beat, state_patch span on every delta (ADR-114)"
```

---

## Task 7: Damage rolls ride the player-facing dice overlay

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/dice.py` (the DICE_THROW arm; build a damage `DiceRequestPayload` for `strike` beats)
- Test: `sidequest-server/tests/server/test_damage_dice_request.py` (create)

**Design note:** Read the file header in `dispatch/dice.py` — the rolling client builds `DiceRequestPayload` locally, auto-rolls in Rapier, and reports settled faces in `DICE_THROW`. For a `strike` beat, the request must carry the **weapon's damage dice** (`DamageSpec.dice` → `DieSpec`/`DieSides`) so the overlay shows, e.g., `1d8+1` resolving. The settled total (plus `bonus`) becomes the `damage_total` fed to `apply_beat_hp_channel` (Task 6).

- [ ] **Step 1: Write the failing test**

```python
# tests/server/test_damage_dice_request.py
from sidequest.genre.models.inventory import DamageSpec
from sidequest.server.dispatch.dice import damage_request_from_spec  # pure helper added here
from sidequest.protocol.dice import DieSides


def test_damage_request_maps_dice_to_die_specs():
    req = damage_request_from_spec(DamageSpec(dice="2d6", bonus=1), request_id="r1")
    faces = [g.sides for g in req.throw_params.groups]   # adjust attr names to ThrowParams shape
    assert faces == [DieSides.D6, DieSides.D6]
    assert req.modifier == 1   # bonus rides as the roll modifier


def test_single_d12_weapon():
    req = damage_request_from_spec(DamageSpec(dice="1d12"), request_id="r2")
    assert [g.sides for g in req.throw_params.groups] == [DieSides.D12]
```

(Inspect `DiceRequestPayload` / `ThrowParams` / `DieSpec` / `DieGroupResult` in `sidequest/protocol/dice.py` and match the real attribute names — the test above sketches the shape; bind it to the actual fields before running.)

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_damage_dice_request.py -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement `damage_request_from_spec` and wire the strike path**

Add a pure helper that turns a `DamageSpec` into a `DiceRequestPayload` (N `DieSpec`s of the parsed face count, `bonus` as the modifier), reusing the same payload constructors the beat-check path already uses. Then in the DICE_THROW dispatch, when the committed beat has `damage_channel == strike`, after the beat-check resolves, build and broadcast a damage `DiceRequestMessage`/`DiceResultMessage` (same broadcast pattern as the existing check roll), resolve the settled faces via `resolve_dice_with_faces`, and pass the total to the Task-6 HP channel.

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_damage_dice_request.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/dispatch/dice.py tests/server/test_damage_dice_request.py
git commit -m "feat(hp): strike beats roll weapon damage via player-facing dice overlay (ADR-074/075) (ADR-114)"
```

---

## Task 8: Lethality arbiter triggers on 0 HP; `verdicts_on_zero_hp` rename

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/lethality.py` (`verdicts_on_zero_edge` → `verdicts_on_zero_hp`)
- Modify: `sidequest-server/sidequest/agents/lethality_arbiter.py` (`core.edge.current == 0` → `core.hp.current == 0`; read `verdicts_on_zero_hp`; cause string)
- Modify (content): every `sidequest-content/genre_packs/*/lethality_policy.yaml` — rename the YAML key
- Test: `sidequest-server/tests/agents/test_lethality_zero_hp.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/agents/test_lethality_zero_hp.py
from sidequest.game.creature_core import CreatureCore, HpPool
from sidequest.agents.lethality_arbiter import LethalityArbiter
from sidequest.genre.models.lethality import LethalityPolicy, VerdictsOnZeroHp
# (import DispatchPackage / BankResult fixtures as the existing arbiter tests do —
#  find them via: grep -rln "LethalityArbiter(" tests/)


def _zero_hp_core():
    return CreatureCore(name="Doomed", description="x", personality="x",
                        hp=HpPool(current=0, max=8, base_max=8))


def test_zero_hp_pc_fires_policy_verdict(make_policy, empty_package, empty_bank):
    arb = LethalityArbiter(make_policy())   # policy with verdicts_on_zero_hp.pc set
    res = arb.arbitrate(package=empty_package, bank_result=empty_bank,
                        pc_cores_by_player={"p1": _zero_hp_core()},
                        npc_cores_by_name={})
    assert len(res.verdicts) == 1
    assert res.verdicts[0].entity == "player:p1"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/agents/test_lethality_zero_hp.py -v`
Expected: FAIL — `VerdictsOnZeroHp` does not exist / arbiter still reads `core.edge`.

- [ ] **Step 3: Rename in the model and re-point the arbiter**

In `lethality.py`: rename class `VerdictsOnZeroEdge` → `VerdictsOnZeroHp` and field `LethalityPolicy.verdicts_on_zero_edge` → `verdicts_on_zero_hp`. Update `__all__`.

In `lethality_arbiter.py`: change both `if core.edge.current == 0:` guards (`:71`, `:79`) to `if core.hp.current == 0:`; change `verdicts_on_zero_edge.pc/.npc` reads to `verdicts_on_zero_hp.pc/.npc`; update the `_emit` cause string `"reduced to zero edge (0/{core.edge.max})"` → `"reduced to zero HP (0/{core.hp.max})"`.

- [ ] **Step 4: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/agents/test_lethality_zero_hp.py -v && uv run pytest -k lethality -v`
Expected: PASS.

- [ ] **Step 5: Rename the content YAML key in every pack**

For each `sidequest-content/genre_packs/*/lethality_policy.yaml`, rename the top-level mapping key `verdicts_on_zero_edge:` → `verdicts_on_zero_hp:` (values unchanged: `space_opera` stays moderate, `beneath_sunden` stays harsher). Validate each pack loads:

Run: `cd sidequest-server && uv run python -m sidequest.cli.validate space_opera` (and repeat per pack, or `just content-validate space_opera` from the orchestrator).
Expected: exit 0, no schema errors. A pack still carrying `verdicts_on_zero_edge` must now fail loud (`extra="forbid"`) — that is the intended no-silent-fallback behavior.

- [ ] **Step 6: Commit**

```bash
# server
git add sidequest/genre/models/lethality.py sidequest/agents/lethality_arbiter.py tests/agents/test_lethality_zero_hp.py
git commit -m "feat(hp): lethality arbiter fires on 0 HP, verdicts_on_zero_hp (ADR-114)"
# content (separate repo / branch)
cd ../sidequest-content && git add genre_packs/*/lethality_policy.yaml
git commit -m "feat(hp): rename verdicts_on_zero_edge → verdicts_on_zero_hp in all packs (ADR-114)"
```

---

## Task 9: Advancement variant rename, narrative-sheet HP exposure, and dead-Edge cleanup

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/advancement.py` (rename the two vitality variants)
- Modify: `sidequest-server/sidequest/game/narrative_sheet.py` (expose the raw HP number per ADR-040 amendment)
- Modify: `sidequest-server/sidequest/game/creature_core.py` (delete the now-unreferenced `EdgePool` + helpers)
- Test: `sidequest-server/tests/game/test_narrative_sheet_hp.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/game/test_narrative_sheet_hp.py
from sidequest.game.creature_core import CreatureCore, HpPool
# import the narrative-sheet builder as the existing tests do —
# find via: grep -rln "narrative_sheet\|NarrativeSheet" tests/ sidequest/game/narrative_sheet.py


def test_sheet_exposes_raw_hp_number_alongside_band():
    core = CreatureCore(name="Pilot", description="x", personality="x",
                        hp=HpPool(current=4, max=8, base_max=8))
    sheet = build_narrative_sheet(core)          # bind to the real builder name
    assert sheet.hp_current == 4                  # ADR-040 amendment: lethality number visible
    assert sheet.hp_max == 8
    assert sheet.health_band == "wounded"         # 0.50 ratio → existing band still present
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_narrative_sheet_hp.py -v`
Expected: FAIL — `NarrativeSheet` has no `hp_current`/`hp_max`.

- [ ] **Step 3: Add HP fields to the narrative sheet (ADR-040 amendment)**

Add `hp_current: int` and `hp_max: int` to the `NarrativeSheet` model and populate them from `core.hp` in the builder. Keep `describe_health()` and the six-band string — the raw number is **additive**, not a replacement (ADR-114 §8 / ADR-040 amendment). This is the *only* raw stat exposed; do not add others.

- [ ] **Step 4: Rename advancement variants**

In `advancement.py`, rename the data-shape variants `EdgeMaxBonus` → `HpMaxBonus` and `EdgeRecovery` → `HpRecovery` (and the fields `edge_delta_mod`/`target_edge_delta_mod` stay — those drive dial costs, not HP, per ADR-114 §4c). `BeatDiscount`, `LeverageBonus`, `LoreRevealBonus` are unchanged. These are loaded-but-unwired per ADR-078 status, so no runtime wiring changes — just the names and any loader literal that maps the YAML `type:` string.

- [ ] **Step 5: Delete dead Edge code**

Now that no production path references them, delete from `creature_core.py`: `EdgePool`, `EdgeThreshold`, `RecoveryTrigger`, `placeholder_edge_pool`, `creature_edge_pool_from_hp`, `EdgeConfigMissingClassError`, `edge_pool_from_config`. Run a tree-wide search to confirm zero remaining references before deleting (`grep -rn "EdgePool\|edge_pool_from_config\|placeholder_edge_pool\|apply_edge_delta\|verdicts_on_zero_edge" sidequest/` should return nothing but comments/ADR-historical strings). Fix any stragglers (e.g. `session.py` edge apply at `:884–888`, `yield_action.py:43` — re-point to `hp` or remove if the yield-refund no longer applies to HP). Per CLAUDE.md, delete dead code in this same PR — do not leave shells.

- [ ] **Step 6: Run the full server suite**

Run: `cd sidequest-server && uv run pytest && uv run ruff check . && uv run pyright`
Expected: PASS / clean. Investigate any test still asserting on `edge` — re-point to `hp` or delete if it tested retired behavior.

- [ ] **Step 7: Commit**

```bash
git add sidequest/genre/models/advancement.py sidequest/game/narrative_sheet.py sidequest/game/creature_core.py sidequest/game/session.py sidequest/server/dispatch/yield_action.py tests/game/test_narrative_sheet_hp.py
git commit -m "feat(hp): HpMaxBonus/HpRecovery rename, narrative sheet exposes HP number, delete dead Edge code (ADR-114)"
```

---

## Task 10: End-to-end acceptance — one `space_opera` combat turn shows both layers

**Files:**
- Modify (content canary): `sidequest-content/genre_packs/space_opera/inventory.yaml` (one weapon gets `damage: {dice: "1d8", bonus: 1}`, one armor gets `mitigation: 1` — full catalog authoring is the Lane A plan), `sidequest-content/genre_packs/space_opera/rules.yaml` (a combat beat tagged `damage_channel: strike`, plus `unarmed_damage`).
- Test: `sidequest-server/tests/server/test_space_opera_hp_e2e.py` (create)

- [ ] **Step 1: Write the end-to-end behavior test**

Drive a synthetic `space_opera` combat turn through the real dispatch (model it on the existing confrontation/dice dispatch tests — find via `grep -rln "DiceThrow\|apply_beat\|space_opera" tests/server/`). Assert, in one turn:
1. the target's `hp.current` decreased by the resolved damage total minus mitigation,
2. a `state_patch` span with `field=="hp"` fired,
3. the confrontation's dial metric (`momentum`/`leverage`) also moved (the dial layer still runs).

This is the ADR-114 success criterion: **both layers legible in one turn.**

- [ ] **Step 2: Run to verify it fails, then passes after canary content lands**

Run: `cd sidequest-server && uv run pytest tests/server/test_space_opera_hp_e2e.py -v`
Expected: FAIL first (no `damage_channel` beat / no `damage` weapon), PASS after the canary content edits.

- [ ] **Step 3: Validate the pack loads and commit**

Run: `just content-validate space_opera` (expect exit 0), then:

```bash
cd sidequest-content && git add genre_packs/space_opera/inventory.yaml genre_packs/space_opera/rules.yaml
git commit -m "feat(hp): space_opera canary — damage weapon + strike beat + unarmed_damage (ADR-114)"
cd ../sidequest-server && git add tests/server/test_space_opera_hp_e2e.py
git commit -m "test(hp): space_opera e2e — strike deals dice HP damage while dials move (ADR-114)"
```

- [ ] **Step 4: Flip ADR-114 to live**

Once Task 10 passes in a real `just up` playtest of `space_opera`, change `docs/adr/114-ablative-hp-substrate.md` frontmatter `implementation-status: partial` → `live` and clear `implementation-pointer`, then rerun `python3 scripts/regenerate_adr_indexes.py`. (The Sünden backport — umbrella spec Part 3 / Plan #5 — is a separate plan and does not gate this flip.)

---

## Self-Review notes (Architect)

- **Spec coverage (ADR-114 §§1–8):** §1 HpPool → Tasks 1–3; §2 damage channel → Tasks 5–7; §3 CatalogItem.damage → Task 4; §4a Edge retired → Task 9; §4c advancement repoint → Task 9; §5 0-HP verdict → Task 8; §6 state_patch span → Task 6; §7 ships unchanged → no task (explicitly out of scope); §8 HP visible → Task 9. Two-layer acceptance → Task 10.
- **No save migration** by design (legacy saves throwaway). Stated up front; no task.
- **Wiring tests** use OTEL span assertions / fixture-driven behavior (Tasks 6, 10) per CLAUDE.md "No Source-Text Wiring Tests" — never grep source.
- **Anchored, not fabricated:** verified symbols/locations are named (`beat_kinds.py:543–642`, `lethality_arbiter.py:71/79`, `creature_core.py:218/260`, `inventory.py:31–47`, `protocol/dice.py` `DieSides`). Where a call-site or fixture wasn't read in full, the step gives the exact `grep` to locate it rather than inventing a line number — bind those before running.
- **Sünden backport (Plan #5)** is deliberately *not* in this plan — ADR-114 sequences it after `space_opera` proves the substrate.
```
