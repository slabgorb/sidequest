# Dogfight × SWN Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Layer faithful SWN shot resolution (d20 vs AC, weapon dice, armor-piercing, HP ablation, `hp_depletion` win) onto the dogfight's maneuver cross-product, so the maneuver game *positions* the shot and SWN *resolves* it — without gutting the favorite feature.

**Architecture:** The maneuver cross-product stays the positioning engine; SWN becomes the resolution engine; the two are layered, not merged. The pure resolver (`resolve_sealed_letter_lookup`) gains geometry → gun-solution detection and computes SWN attack params (no I/O, fully unit-testable). A separate, equally-pure shot-resolution function (`resolve_dogfight_shots`) takes injected d20s, rolls damage, applies AP/armor, ablates HP, and runs the shared depletion check. The stateful dice round-trip (player client-rolls via Rapier; NPC server-rolls) lives at the dispatch/handler layer, reusing the existing opposed-check stash-and-re-enter precedent on `_SessionData`. Shots are ordered so the **NPC-only-shot path is wired and playable first** (no round-trip), then the player client-throw round-trip extends it — every task ends in a wired, mergeable state.

**Tech Stack:** Python 3 / pydantic v2 / FastAPI WebSocket (sidequest-server), YAML genre packs (sidequest-content), pytest + pytest-xdist, OpenTelemetry spans.

**Source spec:** `docs/superpowers/specs/2026-05-27-dogfight-swn-compatibility-design.md`
**Prerequisite (shipped):** Story 59-17 — dogfight instantiates via the production path with a seated opponent.

---

## Reconciliations with the spec (read before starting)

The spec was written before a full code read. These mechanism corrections preserve the spec's **intent** but match the actual code. They are documented here so the executing engineer treats them as the plan of record:

1. **Shot phase is NOT literally "inside `resolve_sealed_letter_lookup`."** That function is pure (mutates the encounter, returns a `SealedLetterOutcome`, no I/O). It is *extended* to detect gun solutions and compute SWN params, which it returns. The dice round-trip and damage application live at the dispatch/handler layer — mirroring the existing opposed-check pattern (`pending_opposed_player_d20` stashed on `_SessionData`, re-entered on `DICE_THROW`).

2. **No `hit_severity` model field exists.** `damage_increments` / `starting_hull` are validated-but-unconsumed fields on `InteractionTable`; `hit_severity` lives only as loose strings inside the YAML `red_view`/`blue_view` dicts. "Strip damage" = remove the two model fields + their validator AND delete the loose YAML keys.

3. **No `strike_fighter` frame infra exists.** Reuse-first decision: author the PC frame on the dogfight ConfrontationDef via a **`player_default_stats`** block mirroring the existing `opponent_default_stats` seam. No new `frames.yaml`, no loader work, no owned-entity modeling.

4. **`ship_attack_params` mirrors `save_params`**, not `attack_params`, for the better-of-INT/DEX modifier — it takes the SWN `cfg` and resolves DEXTERITY/INTELLIGENCE flavor stats via `cfg.attribute_map` (same idiom as `_SAVE_ATTRS`).

5. **Interim within this plan (NOT a shipped half-feature):** the first wiring slice (Task 13) server-rolls *both* pilots' shots so the full mechanical loop is wired and playable in one turn. Task 14 then replaces the *player's* roll with the client-side Rapier throw, realizing locked decision #7 (player client-rolls, NPC server-rolls). Both tasks live in this one plan; nothing server-rolled-for-the-player ever merges as a "final" state.

---

## File Structure

**sidequest-content** (genre data):
- Modify `genre_packs/space_opera/dogfight/interactions_mvp.yaml` — strip table damage + cell `hit_severity`; keep geometry + `gun_solution`.
- Modify `genre_packs/space_opera/rules.yaml` — dogfight def: strike-fighter `opponent_default_stats`, new `player_default_stats`, new `geometry_modifiers`, weapon ids.
- Modify `genre_packs/space_opera/inventory.yaml` — author `multifocal_laser` weapon (`damage: 1d4`, `armor_piercing: 20`).

**sidequest-server** (engine):
- `sidequest/genre/models/inventory.py` — add `armor_piercing` to `DamageSpec`.
- `sidequest/genre/models/rules.py` — drop `damage_increments`/`starting_hull` from `InteractionTable`; add `geometry_modifiers` + `player_default_stats` accessors to `ConfrontationDef`; add `GeometryModifiers` model.
- `sidequest/game/ruleset/base.py` — add optional `ship_attack_params` hook.
- `sidequest/game/ruleset/swn.py` — implement `ship_attack_params`.
- `sidequest/game/dogfight_shot.py` *(new)* — geometry-modifier resolution, AP/armor damage math, `GunSolution`, `resolve_dogfight_shots`.
- `sidequest/game/hp_depletion.py` *(new)* — extracted shared `check_hp_depletion`.
- `sidequest/game/beat_kinds.py` — call the extracted `check_hp_depletion`.
- `sidequest/server/dispatch/sealed_letter.py` — extend `SealedLetterOutcome` + `resolve_sealed_letter_lookup` with gun-solution detection.
- `sidequest/telemetry/spans/dogfight.py` — add `shot_attempted` / `shot_damage` spans.
- `sidequest/server/session_state.py` — add `pending_dogfight_shot` stash.
- `sidequest/server/narration_apply.py` — sealed-letter branch shot wiring + SWN-binding assert.
- `sidequest/server/websocket_session_handler.py` — emit `DiceRequestMessage`, stash, re-enter.
- `sidequest/handlers/dice_throw.py` — detect + resolve a pending dogfight shot.

**Test files** (created/extended alongside each task; exact paths in the tasks).

---

## Task 1: Add `armor_piercing` to `DamageSpec`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/inventory.py:36-56`
- Test: `sidequest-server/tests/genre/test_damage_spec.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_damage_spec.py`:

```python
from sidequest.genre.models.inventory import DamageSpec


def test_damage_spec_defaults_armor_piercing_zero():
    spec = DamageSpec(dice="1d4")
    assert spec.armor_piercing == 0


def test_damage_spec_accepts_armor_piercing():
    spec = DamageSpec(dice="1d4", armor_piercing=20)
    assert spec.armor_piercing == 20


def test_damage_spec_rejects_negative_armor_piercing():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        DamageSpec(dice="1d4", armor_piercing=-1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_damage_spec.py -v`
Expected: FAIL — `test_damage_spec_accepts_armor_piercing` errors because `extra: forbid` rejects the unknown `armor_piercing` field.

- [ ] **Step 3: Add the field**

In `sidequest/genre/models/inventory.py`, inside `class DamageSpec`, after `bonus: int = 0`:

```python
    dice: str          # "NdM" — M must be a supported DieSides face count
    bonus: int = 0
    armor_piercing: int = Field(default=0, ge=0)  # AP: reduces target Armor soak before subtraction (SWN). 0 = none.
```

Ensure `Field` is imported (it is used elsewhere in the file; confirm `from pydantic import ... Field`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_damage_spec.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/genre/models/inventory.py tests/genre/test_damage_spec.py
git commit -m "feat(swn): add armor_piercing field to DamageSpec"
```

---

## Task 2: Drop `damage_increments` / `starting_hull` from `InteractionTable`

The fields are validated but never consumed; SWN replaces them with dice. Remove the fields and their validator branch.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:349-382`
- Test: `sidequest-server/tests/genre/test_interaction_table.py` (locate existing tests of `damage_increments` first)

- [ ] **Step 1: Find existing tests that assert on the removed fields**

Run: `cd sidequest-server && grep -rn "damage_increments\|starting_hull" tests/ sidequest/`
Expected: surfaces the validator tests (likely in `tests/genre/`) and any other references. These tests will be updated in Step 5; note their paths now.

- [ ] **Step 2: Write the failing test (new invariant: cells carry geometry only)**

Create or extend `sidequest-server/tests/genre/test_interaction_table.py`:

```python
import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import InteractionCell, InteractionTable


def _cell(red: str, blue: str) -> InteractionCell:
    return InteractionCell(
        pair=[red, blue],
        name=f"{red}_vs_{blue}",
        red_view={"gun_solution": False},
        blue_view={"gun_solution": True},
    )


def test_interaction_table_rejects_damage_increments_field():
    # SWN replaces deterministic increments with dice; the field is gone.
    with pytest.raises(ValidationError):
        InteractionTable(
            version="1",
            starting_state="merge",
            maneuvers_consumed=["straight", "loop"],
            cells=[_cell("straight", "loop")],
            damage_increments={"graze": 5, "clean": 15, "devastating": 30},
        )


def test_interaction_table_loads_geometry_only():
    table = InteractionTable(
        version="1",
        starting_state="merge",
        maneuvers_consumed=["straight", "loop"],
        cells=[_cell("straight", "loop")],
    )
    assert table.cells[0].blue_view["gun_solution"] is True
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_interaction_table.py -v`
Expected: `test_interaction_table_rejects_damage_increments_field` FAILS — the field still exists and is accepted.

- [ ] **Step 4: Remove the fields and validator branch**

In `sidequest/genre/models/rules.py`, `class InteractionTable`:

Delete these two lines:
```python
    damage_increments: dict[str, int] | None = None
    starting_hull: int | None = None
```

In the `_validate` model-validator, delete the entire trailing block:
```python
        if self.damage_increments is not None:
            for tier in ("graze", "clean", "devastating"):
                val = self.damage_increments.get(tier)
                if val is None:
                    raise ValueError(f"damage_increments missing required severity tier: '{tier}'")
                if val <= 0:
                    raise ValueError(f"damage_increments '{tier}' must be positive, got {val}")
        return self
```
…leaving the validator ending at the existing `return self` after the duplicate-pair check.

- [ ] **Step 5: Update/retire the obsolete tests found in Step 1**

For each test that constructed an `InteractionTable` with `damage_increments`/`starting_hull` or asserted the old validation messages: delete the now-invalid assertions and remove the kwargs. Do not leave a test that pins the removed behavior. (Per CLAUDE.md: delete dead code in the same change.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/genre/test_interaction_table.py -v && grep -rn "damage_increments\|starting_hull" sidequest/ tests/`
Expected: PASS; grep returns no hits in `sidequest/` (a residual hit only in a deleted-assertion file is a miss — fix it).

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && git add sidequest/genre/models/rules.py tests/genre/
git commit -m "refactor(dogfight): drop deterministic damage fields from InteractionTable"
```

---

## Task 3: Add `GeometryModifiers` + `player_default_stats` to `ConfrontationDef`

`geometry_modifiers` maps the maneuver-cell geometry (aspect, range) into a to-hit modifier, authored and tunable in content. `player_default_stats` mirrors `opponent_default_stats` so the PC's strike-fighter frame (HP/AC/Armor/gun) seeds the same way the opponent ace does.

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py` (near `ConfrontationDef`, ~line 545 where `opponent_hp` is defined)
- Test: `sidequest-server/tests/genre/test_geometry_modifiers.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_geometry_modifiers.py`:

```python
from sidequest.genre.models.rules import GeometryModifiers


def test_geometry_modifiers_defaults_empty():
    gm = GeometryModifiers()
    assert gm.aspect == {}
    assert gm.range == {}


def test_geometry_modifiers_loads_authored_calibration():
    gm = GeometryModifiers(
        aspect={"tail_on": 2, "quartering": 1, "crossing": -1, "head_on": -2},
        range={"gun": 2, "close": 0, "medium": -2, "far": -4},
    )
    assert gm.aspect["tail_on"] == 2
    assert gm.range["far"] == -4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/genre/test_geometry_modifiers.py -v`
Expected: FAIL — `ImportError: cannot import name 'GeometryModifiers'`.

- [ ] **Step 3: Add the `GeometryModifiers` model**

In `sidequest/genre/models/rules.py`, near the other rules models (above `ConfrontationDef`):

```python
class GeometryModifiers(BaseModel):
    """Maneuver-cell geometry → ship-gunnery to-hit modifier (dogfight SWN layer).

    Authored & tunable in content. ``aspect`` keys match the cell view's
    ``target_aspect`` value (tail_on/quartering/crossing/head_on); ``range``
    keys match ``target_range`` (gun/close/medium/far). Sum of the matched
    aspect and range modifiers feeds ``ship_attack_params(geometry_modifier=...)``.
    """

    model_config = {"extra": "forbid"}

    aspect: dict[str, int] = Field(default_factory=dict)
    range: dict[str, int] = Field(default_factory=dict)
```

- [ ] **Step 4: Add the fields/accessors to `ConfrontationDef`**

Find `class ConfrontationDef` and its `opponent_default_stats` field and `opponent_hp`/`opponent_armor_class` properties (~lines 540-560). Add a `geometry_modifiers` field and a `player_default_stats` field plus mirror accessors. Add near the existing fields:

```python
    geometry_modifiers: GeometryModifiers | None = None
    player_default_stats: dict[str, int] = Field(default_factory=dict)
```

And mirror the opponent accessors for the player frame (place beside `opponent_hp`/`opponent_armor_class`):

```python
    @property
    def player_hp(self) -> int | None:
        return self.player_default_stats.get("hp")

    @property
    def player_armor_class(self) -> int | None:
        return self.player_default_stats.get("armor_class")
```

(If `ConfrontationDef` uses `model_config = {"extra": "forbid"}`, these new fields are required for the YAML in Task 5 to load — confirm the new field names match the YAML keys exactly.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/genre/test_geometry_modifiers.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/genre/models/rules.py tests/genre/test_geometry_modifiers.py
git commit -m "feat(dogfight): add GeometryModifiers + player_default_stats to ConfrontationDef"
```

---

## Task 4: `SwnRulesetModule.ship_attack_params`

SWN ship gunnery: `d20 + attack_bonus + pilot_skill + better-of(INT,DEX) mod + geometry_modifier` vs target fighter AC. Pilot stands in for Shoot on a fighter-class ship. Mirrors `save_params`'s `cfg.attribute_map` idiom for the better-of-two-attributes modifier.

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/base.py:22-81` (add optional hook)
- Modify: `sidequest-server/sidequest/game/ruleset/swn.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_ship_attack_params.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_swn_ship_attack_params.py`:

```python
from sidequest.game.ruleset.swn import SwnRulesetModule


class _Cfg:
    # Mirrors SwnConfig.attribute_map shape used by save_params.
    attribute_map = {
        "STRENGTH": "Physique",
        "CONSTITUTION": "Physique",
        "DEXTERITY": "Reflex",
        "INTELLIGENCE": "Intellect",
        "WISDOM": "Resolve",
        "CHARISMA": "Cunning",
    }


def test_ship_attack_params_uses_better_of_int_dex():
    mod = SwnRulesetModule()
    # Reflex 16 -> +1 (DEX), Intellect 10 -> 0 (INT): better is +1.
    params = mod.ship_attack_params(
        attacker_stats={"Reflex": 16, "Intellect": 10},
        pilot_skill=1,
        attack_bonus=1,
        geometry_modifier=2,
        target_ac=16,
        cfg=_Cfg(),
    )
    # attack_bonus(1) + pilot_skill(1) + better_mod(1) + geometry(2) = 5
    assert params.modifier == 5
    assert params.target_number == 16


def test_ship_attack_params_negative_geometry():
    mod = SwnRulesetModule()
    params = mod.ship_attack_params(
        attacker_stats={"Reflex": 8, "Intellect": 8},  # both 0 mod
        pilot_skill=0,
        attack_bonus=0,
        geometry_modifier=-6,  # head_on(-2) + far(-4)
        target_ac=16,
        cfg=_Cfg(),
    )
    assert params.modifier == -6
    assert params.target_number == 16
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_ship_attack_params.py -v`
Expected: FAIL — `AttributeError: 'SwnRulesetModule' object has no attribute 'ship_attack_params'`.

- [ ] **Step 3: Add the base-class hook**

In `sidequest/game/ruleset/base.py`, add a non-abstract default that fails loud (matching the `check_params`/`save_params` NotImplementedError idiom) below `attack_params`:

```python
    def ship_attack_params(
        self,
        *,
        attacker_stats: dict[str, int],
        pilot_skill: int,
        attack_bonus: int,
        geometry_modifier: int,
        target_ac: int,
        cfg,
    ) -> "AttackRollParams":
        """Modifier + target number for one ship-gunnery shot (dogfight SWN layer)."""
        raise NotImplementedError(f"{self.slug} ruleset has no ship-gunnery resolution")
```

(`AttackRollParams` is already imported in `base.py` for the abstract `attack_params`; reuse it.)

- [ ] **Step 4: Implement on `SwnRulesetModule`**

In `sidequest/game/ruleset/swn.py`, add to `class SwnRulesetModule` (after `attack_params`):

```python
    def ship_attack_params(
        self, *, attacker_stats, pilot_skill, attack_bonus, geometry_modifier, target_ac, cfg
    ) -> AttackRollParams:
        """SWN strike-craft gunnery: d20 + attack_bonus + pilot_skill +
        better-of(INT,DEX) mod + geometry_modifier vs target fighter AC.
        Pilot stands in for Shoot on a fighter-class ship (SRD ship combat)."""
        amap = cfg.attribute_map
        flavor_attrs = []
        for swn_attr in ("DEXTERITY", "INTELLIGENCE"):
            flavor = amap.get(swn_attr)
            if flavor is None:
                raise KeyError(
                    f"attribute_map missing {swn_attr!r} for ship gunnery "
                    "(RulesConfig validator should have caught this)"
                )
            flavor_attrs.append(flavor)
        best_mod = max(self.stat_modifier(attacker_stats, f) for f in flavor_attrs)
        return AttackRollParams(
            modifier=int(attack_bonus) + int(pilot_skill) + best_mod + int(geometry_modifier),
            target_number=int(target_ac),
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/ruleset/test_swn_ship_attack_params.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/game/ruleset/base.py sidequest/game/ruleset/swn.py tests/game/ruleset/test_swn_ship_attack_params.py
git commit -m "feat(swn): add ship_attack_params for fighter-class gunnery"
```

---

## Task 5: Author the strike-fighter content (sidequest-content)

Now wire the data the resolver will read. **Branch the content repo first** (it targets `develop`).

**Files:**
- Modify: `sidequest-content/genre_packs/space_opera/inventory.yaml`
- Modify: `sidequest-content/genre_packs/space_opera/rules.yaml` (dogfight def ~lines 375-455)
- Modify: `sidequest-content/genre_packs/space_opera/dogfight/interactions_mvp.yaml`

- [ ] **Step 1: Branch the content repo**

```bash
cd sidequest-content && git checkout develop && git pull && git checkout -b feat/dogfight-swn-resolution
```

- [ ] **Step 2: Author the multifocal laser weapon**

In `genre_packs/space_opera/inventory.yaml`, add a catalog weapon (match the file's existing item shape — `id`, `name`, `damage: {dice, bonus, armor_piercing}`):

```yaml
  - id: multifocal_laser
    name: "multifocal laser"
    kind: weapon
    description: "Iconic strike-fighter gun. Light but armor-shredding."
    damage:
      dice: "1d4"
      bonus: 0
      armor_piercing: 20
```

- [ ] **Step 3: Rewrite the dogfight ConfrontationDef statline**

In `genre_packs/space_opera/rules.yaml`, the `type: dogfight` def. Replace the `opponent_default_stats` block with authentic strike-fighter numbers and reserved gunnery keys, add `player_default_stats`, and add `geometry_modifiers`:

```yaml
  - type: dogfight
    label: Fighter Duel
    category: combat
    resolution_mode: sealed_letter
    win_condition: sealed_letter
    opponent_default_stats:
      Physique: 10
      Reflex: 12
      Intellect: 10
      Cunning: 10
      Resolve: 10
      # Strike-fighter frame (SWN Revised Free Edition SRD):
      hp: 8
      armor_class: 16
      armor: 5            # flat soak; multifocal laser AP 20 negates it
      dexterity: 12       # initiative (1d8+DEX)
      # Ship-gunnery reserved keys for the opponent ace:
      pilot_skill: 1
      attack_bonus: 1
      weapon: multifocal_laser
    player_default_stats:
      # PC strike-fighter frame. HP/AC/Armor/gun come from the frame; the
      # pilot's real Pilot skill + attributes come from their character sheet
      # (seeded at instantiation — see server Task 13).
      hp: 8
      armor_class: 16
      armor: 5
      weapon: multifocal_laser
      # Default gunnery values if the PC sheet carries no Pilot skill / attack
      # bonus (authored, NOT a silent runtime fallback — see Task 13).
      pilot_skill: 0
      attack_bonus: 0
    geometry_modifiers:
      aspect:
        tail_on: 2
        quartering: 1
        crossing: -1
        head_on: -2
      range:
        gun: 2
        close: 0
        medium: -2
        far: -4
    beats: []
    mood: tense
```

- [ ] **Step 4: Strip damage from the interaction table**

In `genre_packs/space_opera/dogfight/interactions_mvp.yaml`:
- Delete the table-header `damage_increments:` block (graze/clean/devastating) and the `starting_hull:` line.
- In every cell's `red_view`/`blue_view`, delete any `hit_severity:` line. Keep `gun_solution`, `target_bearing`, `target_range`, `target_aspect`, `closure`, and energy deltas.

Verify nothing references the removed keys:
```bash
cd sidequest-content && grep -n "hit_severity\|damage_increments\|starting_hull" genre_packs/space_opera/dogfight/interactions_mvp.yaml
```
Expected: no output.

- [ ] **Step 5: Validate the pack loads (server-side validator)**

From the server repo, load the pack to confirm the new fields parse and the stripped fields don't trip `extra: forbid`:
```bash
cd sidequest-server && SIDEQUEST_GENRE_PACKS=../sidequest-content/genre_packs \
  uv run python -c "from sidequest.genre.loader import load_pack; p = load_pack('space_opera'); \
  d = next(c for c in p.rules.confrontations if c.type=='dogfight'); \
  print('opp_hp', d.opponent_hp, 'opp_ac', d.opponent_armor_class, 'pc_hp', d.player_hp, 'geo', d.geometry_modifiers is not None)"
```
Expected: `opp_hp 8 opp_ac 16 pc_hp 8 geo True` (adjust the loader import to the actual `load_pack` entrypoint if named differently — confirm via `grep -rn "def load_pack\|def load_genre" sidequest/genre/`).

- [ ] **Step 6: Commit (content repo)**

```bash
cd sidequest-content && git add genre_packs/space_opera/inventory.yaml genre_packs/space_opera/rules.yaml genre_packs/space_opera/dogfight/interactions_mvp.yaml
git commit -m "feat(space_opera): strike-fighter SWN statline + geometry modifiers for dogfight"
```

---

## Task 6: Geometry-modifier resolution + AP/armor damage math

New pure module. `resolve_geometry_modifier` reads a shooter's `per_actor_state` geometry (set by the cell views) and sums the authored aspect+range modifiers. `apply_ship_shot_damage` computes `effective_armor = max(0, armor − AP)` then `applied = max(0, damage − effective_armor)`.

**Files:**
- Create: `sidequest-server/sidequest/game/dogfight_shot.py`
- Test: `sidequest-server/tests/game/test_dogfight_shot_math.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_dogfight_shot_math.py`:

```python
from sidequest.game.dogfight_shot import (
    effective_armor_after_ap,
    resolve_geometry_modifier,
)
from sidequest.genre.models.rules import GeometryModifiers

GM = GeometryModifiers(
    aspect={"tail_on": 2, "quartering": 1, "crossing": -1, "head_on": -2},
    range={"gun": 2, "close": 0, "medium": -2, "far": -4},
)


def test_geometry_modifier_tail_on_gun_is_plus_4():
    state = {"target_aspect": "tail_on", "target_range": "gun"}
    assert resolve_geometry_modifier(state, GM) == 4


def test_geometry_modifier_head_on_far_is_minus_6():
    state = {"target_aspect": "head_on", "target_range": "far"}
    assert resolve_geometry_modifier(state, GM) == -6


def test_geometry_modifier_unknown_keys_contribute_zero():
    # No silent fallback to a wrong number: unknown aspect/range = 0 contribution.
    state = {"target_aspect": "inverted", "target_range": "gun"}
    assert resolve_geometry_modifier(state, GM) == 2  # only range matched


def test_effective_armor_full_penetration():
    # AP 20 >> Armor 5 -> 0 effective armor
    assert effective_armor_after_ap(armor=5, armor_piercing=20) == 0


def test_effective_armor_partial():
    assert effective_armor_after_ap(armor=5, armor_piercing=2) == 3


def test_effective_armor_floor_zero():
    assert effective_armor_after_ap(armor=2, armor_piercing=10) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_dogfight_shot_math.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create the module with the math helpers**

Create `sidequest/game/dogfight_shot.py`:

```python
"""Dogfight SWN shot resolution — pure positioning→resolution layer.

The maneuver cross-product (sealed-letter cells) sets each pilot's geometry in
``per_actor_state``. This module turns geometry into a to-hit modifier, and
resolves SWN shots (d20 vs AC, weapon dice, armor-piercing, HP ablation). No
I/O — dice values are injected by the caller (player: client Rapier throw; NPC:
server roll), so every branch is unit-testable.
"""

from __future__ import annotations

from sidequest.genre.models.rules import GeometryModifiers


def resolve_geometry_modifier(
    per_actor_state: dict, geometry_modifiers: GeometryModifiers
) -> int:
    """Sum the authored aspect + range modifiers for a shooter's current geometry.

    Unknown aspect/range values contribute 0 (the authored table is the source
    of truth; an unlisted geometry is neutral, not an error)."""
    aspect = per_actor_state.get("target_aspect")
    rng = per_actor_state.get("target_range")
    mod = 0
    if aspect is not None:
        mod += geometry_modifiers.aspect.get(aspect, 0)
    if rng is not None:
        mod += geometry_modifiers.range.get(rng, 0)
    return mod


def effective_armor_after_ap(*, armor: int, armor_piercing: int) -> int:
    """SWN AP rule: AP reduces effective Armor before damage subtraction."""
    return max(0, int(armor) - int(armor_piercing))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_dogfight_shot_math.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/game/dogfight_shot.py tests/game/test_dogfight_shot_math.py
git commit -m "feat(dogfight): geometry-modifier + AP/armor shot math"
```

---

## Task 7: Add `shot_attempted` / `shot_damage` OTEL spans

CLAUDE.md OTEL principle: every shot decision emits a span so the GM panel proves the dice fired.

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/dogfight.py`
- Test: `sidequest-server/tests/telemetry/test_dogfight_shot_spans.py`

- [ ] **Step 1: Find the span-name constants pattern**

Run: `cd sidequest-server && grep -n "SPAN_DOGFIGHT" sidequest/telemetry/spans/dogfight.py`
Expected: shows `SPAN_DOGFIGHT_CONFRONTATION_STARTED`, `SPAN_DOGFIGHT_MANEUVER_COMMITTED`, `SPAN_DOGFIGHT_CELL_RESOLVED` and where they're defined. Note the deferred-span comment at the file top.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/telemetry/test_dogfight_shot_spans.py` (mirror an existing span test's capture harness — find one with `grep -rln "in_memory_span_exporter\|InMemorySpanExporter\|span_exporter" tests/telemetry/` and copy its fixture):

```python
from sidequest.telemetry.spans.dogfight import (
    dogfight_shot_attempted_span,
    dogfight_shot_damage_span,
)


def test_shot_attempted_span_carries_roll(span_exporter):
    with dogfight_shot_attempted_span(
        shooter="Red Baron",
        target="player",
        d20_total=18,
        target_ac=16,
        hit=True,
        geometry_modifier=4,
        source="npc",
    ):
        pass
    spans = span_exporter.get_finished_spans()
    span = next(s for s in spans if s.name.endswith("shot_attempted"))
    assert span.attributes["d20_total"] == 18
    assert span.attributes["hit"] is True
    assert span.attributes["source"] == "npc"


def test_shot_damage_span_carries_ablation(span_exporter):
    with dogfight_shot_damage_span(
        shooter="Red Baron",
        target="player",
        dice="1d4",
        armor_piercing=20,
        armor_negated=5,
        applied=3,
        target_hp_after=5,
    ):
        pass
    spans = span_exporter.get_finished_spans()
    span = next(s for s in spans if s.name.endswith("shot_damage"))
    assert span.attributes["applied"] == 3
    assert span.attributes["target_hp_after"] == 5
```

(Use whatever the project's span-capture fixture is named; adapt `span_exporter` to it.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_dogfight_shot_spans.py -v`
Expected: FAIL — `ImportError` on the two new span helpers.

- [ ] **Step 4: Add the span constants + helpers**

In `sidequest/telemetry/spans/dogfight.py`, add the two constants beside the existing `SPAN_DOGFIGHT_*` definitions:

```python
SPAN_DOGFIGHT_SHOT_ATTEMPTED = "dogfight.shot_attempted"
SPAN_DOGFIGHT_SHOT_DAMAGE = "dogfight.shot_damage"
```

Add the two context managers (mirror `dogfight_cell_resolved_span`):

```python
@contextmanager
def dogfight_shot_attempted_span(
    *,
    shooter: str,
    target: str,
    d20_total: int,
    target_ac: int,
    hit: bool,
    geometry_modifier: int,
    source: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_DOGFIGHT_SHOT_ATTEMPTED,
        {
            "shooter": shooter,
            "target": target,
            "d20_total": d20_total,
            "target_ac": target_ac,
            "hit": hit,
            "geometry_modifier": geometry_modifier,
            "source": source,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def dogfight_shot_damage_span(
    *,
    shooter: str,
    target: str,
    dice: str,
    armor_piercing: int,
    armor_negated: int,
    applied: int,
    target_hp_after: int,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_DOGFIGHT_SHOT_DAMAGE,
        {
            "shooter": shooter,
            "target": target,
            "dice": dice,
            "armor_piercing": armor_piercing,
            "armor_negated": armor_negated,
            "applied": applied,
            "target_hp_after": target_hp_after,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span
```

If the file top lists these as "deferred" spans, remove `shot_attempted`/`shot_damage` from that deferred list comment now that they're live.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_dogfight_shot_spans.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/telemetry/spans/dogfight.py tests/telemetry/test_dogfight_shot_spans.py
git commit -m "feat(dogfight): shot_attempted + shot_damage OTEL spans"
```

---

## Task 8: Extract shared `check_hp_depletion`

Move the `hp_depletion` win check out of `beat_kinds.py` into a shared helper so the sealed-letter path can call it after shots. The helper is **unconditional** (no `win_condition` gate inside) — each caller decides when to invoke it.

**Files:**
- Create: `sidequest-server/sidequest/game/hp_depletion.py`
- Modify: `sidequest-server/sidequest/game/beat_kinds.py:829-863`
- Test: `sidequest-server/tests/game/test_hp_depletion.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_hp_depletion.py`:

```python
from sidequest.game.encounter import EncounterActor, StructuredEncounter
from sidequest.game.creature_core import hp_pool_from_hp
from sidequest.game.hp_depletion import check_hp_depletion


class _Core:
    def __init__(self, name, hp):
        self.name = name
        self.hp = hp_pool_from_hp(hp)


def _enc():
    enc = StructuredEncounter(encounter_type="dogfight", win_condition="sealed_letter")
    enc.actors = [
        EncounterActor(name="PC", role="red", side="player"),
        EncounterActor(name="Ace", role="blue", side="opponent"),
    ]
    return enc


def test_opponent_down_resolves_player_victory():
    enc = _enc()
    cores = {"PC": _Core("PC", 8), "Ace": _Core("Ace", 0)}
    result = check_hp_depletion(enc, lambda n: cores.get(n))
    assert result is not None
    assert enc.resolved is True
    assert enc.outcome == "player_victory"


def test_mutual_down_resolves_mutual_destruction():
    enc = _enc()
    cores = {"PC": _Core("PC", 0), "Ace": _Core("Ace", 0)}
    result = check_hp_depletion(enc, lambda n: cores.get(n))
    assert enc.resolved is True
    assert enc.outcome == "mutual_destruction"


def test_nobody_down_no_resolution():
    enc = _enc()
    cores = {"PC": _Core("PC", 8), "Ace": _Core("Ace", 8)}
    result = check_hp_depletion(enc, lambda n: cores.get(n))
    assert result is None
    assert enc.resolved is False
```

(Confirm `StructuredEncounter`/`EncounterActor` constructor kwargs against `sidequest/game/encounter.py`; adjust if `win_condition` is set differently. Confirm `hp_pool_from_hp` import path from `creature_core.py`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_depletion.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Create the shared helper**

Create `sidequest/game/hp_depletion.py`:

```python
"""Shared HP-depletion win check (ADR-114). Callable from the beat loop and the
dogfight sealed-letter shot path. Unconditional — the caller decides WHEN to run
it; this function only reads HP and resolves. Emits encounter.resolved (lie
detector) with source='hp_depletion'."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sidequest.game.encounter import EncounterPhase
from sidequest.telemetry.spans.encounter import encounter_resolved_span


@dataclass(frozen=True)
class HpDepletionResult:
    outcome: str          # player_victory | opponent_victory | mutual_destruction
    down_side: str        # opponent | player | both


def check_hp_depletion(enc, edge_resolver: Callable[[str], object | None]):
    """Resolve ``enc`` if a side's combatant is at 0 HP. Returns the result, or
    None if nobody is down. Mutates enc.resolved/outcome/structured_phase and
    emits the resolution span when it resolves. Mutual KO -> mutual_destruction."""
    if getattr(enc, "resolved", False):
        return None

    def _any_down(side: str) -> bool:
        for a in enc.actors:
            if a.side != side:
                continue
            core = edge_resolver(a.name)
            if core is not None and core.hp.current <= 0:
                return True
        return False

    player_down = _any_down("player")
    opponent_down = _any_down("opponent")
    if not player_down and not opponent_down:
        return None

    if player_down and opponent_down:
        outcome, down_side = "mutual_destruction", "both"
    elif opponent_down:
        outcome, down_side = "player_victory", "opponent"
    else:
        outcome, down_side = "opponent_victory", "player"

    enc.resolved = True
    enc.outcome = outcome
    enc.structured_phase = EncounterPhase.Resolution
    with encounter_resolved_span(
        encounter_type=enc.encounter_type,
        outcome=outcome,
        source="hp_depletion",
        down_side=down_side,
    ):
        pass
    return HpDepletionResult(outcome=outcome, down_side=down_side)
```

(Confirm `EncounterPhase` import path matches what `beat_kinds.py` imports.)

- [ ] **Step 4: Run the new helper's test**

Run: `cd sidequest-server && uv run pytest tests/game/test_hp_depletion.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Refactor `beat_kinds.py` to call the helper**

In `sidequest/game/beat_kinds.py:829-863`, replace the inline `_any_actor_down` block with a call to the shared helper, keeping the `win_condition == "hp_depletion"` gate at the call site:

```python
    hp_depletion = enc.win_condition == "hp_depletion"

    if hp_depletion and not resolved and edge_resolver is not None:
        from sidequest.game.hp_depletion import check_hp_depletion

        result = check_hp_depletion(enc, edge_resolver)
        if result is not None:
            resolved = True
```

Delete the old inline `_any_actor_down` closure and the duplicated `encounter_resolved_span` emission (the helper now owns it). Note: the helper adds `mutual_destruction`, which the old beat-loop code didn't produce — that's a superset, harmless for the existing 1v1 beat combats (they can't double-KO in one beat).

- [ ] **Step 6: Run beat tests to verify no regression**

Run: `cd sidequest-server && uv run pytest tests/game/ -k "beat or hp_depletion or combat" -v`
Expected: PASS. Investigate any failure before proceeding — this is the guard-relaxation risk; run the full owning module if anything is red: `uv run pytest tests/game/ -v`.

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && git add sidequest/game/hp_depletion.py sidequest/game/beat_kinds.py tests/game/test_hp_depletion.py
git commit -m "refactor(combat): extract shared check_hp_depletion helper"
```

---

## Task 9: `GunSolution` + gun-solution detection in `resolve_sealed_letter_lookup`

Extend the pure resolver to detect which pilots have a `gun_solution` after geometry, and compute each shooter's SWN `ship_attack_params` (modifier + target AC) + the weapon/armor needed for damage. Returned in an extended `SealedLetterOutcome`. **No dice, no damage here.**

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/sealed_letter.py:65-79` (`SealedLetterOutcome`) and `:81-214` (resolver)
- Test: `sidequest-server/tests/server/dispatch/test_sealed_letter_gun_solutions.py`

- [ ] **Step 1: Decide the GunSolution shape and write the failing test**

Create `sidequest-server/tests/server/dispatch/test_sealed_letter_gun_solutions.py`:

```python
from sidequest.game.encounter import EncounterActor, StructuredEncounter
from sidequest.genre.models.rules import (
    GeometryModifiers,
    InteractionCell,
    InteractionTable,
)
from sidequest.genre.models.inventory import DamageSpec
from sidequest.server.dispatch.sealed_letter import resolve_sealed_letter_lookup


class _Cfg:
    attribute_map = {
        "STRENGTH": "Physique", "CONSTITUTION": "Physique",
        "DEXTERITY": "Reflex", "INTELLIGENCE": "Intellect",
        "WISDOM": "Resolve", "CHARISMA": "Cunning",
    }


def _table():
    return InteractionTable(
        version="1",
        starting_state="merge",
        maneuvers_consumed=["straight", "loop"],
        cells=[
            InteractionCell(
                pair=["straight", "loop"],
                name="blue_on_six",
                red_view={"gun_solution": False, "target_aspect": "head_on", "target_range": "close"},
                blue_view={"gun_solution": True, "target_aspect": "tail_on", "target_range": "gun"},
            )
        ],
    )


def _enc():
    enc = StructuredEncounter(encounter_type="dogfight", win_condition="sealed_letter")
    enc.actors = [
        EncounterActor(name="PC", role="red", side="player"),
        EncounterActor(name="Ace", role="blue", side="opponent"),
    ]
    return enc


def test_resolver_emits_one_gun_solution_for_blue():
    enc = _enc()
    gm = GeometryModifiers(
        aspect={"tail_on": 2, "head_on": -2}, range={"gun": 2, "close": 0}
    )
    shot_inputs = {
        # role -> the per-shooter SWN inputs the dispatch layer assembles
        "blue": {
            "attacker_stats": {"Reflex": 12, "Intellect": 10},
            "pilot_skill": 1, "attack_bonus": 1,
            "target_ac": 16, "target_armor": 5,
            "weapon": DamageSpec(dice="1d4", armor_piercing=20), "weapon_name": "multifocal laser",
        },
    }
    outcome = resolve_sealed_letter_lookup(
        enc, {"red": "straight", "blue": "loop"}, _table(),
        geometry_modifiers=gm, shot_inputs=shot_inputs, swn_cfg=_Cfg(),
    )
    assert len(outcome.gun_solutions) == 1
    gs = outcome.gun_solutions[0]
    assert gs.shooter_role == "blue"
    assert gs.target_role == "red"
    # tail_on(+2)+gun(+2)=+4 geometry; attack_bonus 1 + pilot 1 + DEX mod(+1) + 4 = 7
    assert gs.attack.modifier == 7
    assert gs.attack.target_number == 16
    assert gs.target_armor == 5


def test_resolver_no_gun_solution_returns_empty_list():
    enc = _enc()
    table = InteractionTable(
        version="1", starting_state="merge", maneuvers_consumed=["straight", "loop"],
        cells=[InteractionCell(
            pair=["straight", "loop"], name="merge",
            red_view={"gun_solution": False}, blue_view={"gun_solution": False},
        )],
    )
    outcome = resolve_sealed_letter_lookup(
        enc, {"red": "straight", "blue": "loop"}, table,
        geometry_modifiers=GeometryModifiers(), shot_inputs={}, swn_cfg=_Cfg(),
    )
    assert outcome.gun_solutions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_sealed_letter_gun_solutions.py -v`
Expected: FAIL — `resolve_sealed_letter_lookup` doesn't accept the new kwargs / `SealedLetterOutcome` has no `gun_solutions`.

- [ ] **Step 3: Add the `GunSolution` dataclass + extend `SealedLetterOutcome`**

In `sidequest/server/dispatch/sealed_letter.py`, add imports and the dataclass near `SealedLetterOutcome`:

```python
from dataclasses import dataclass, field

from sidequest.game.dogfight_shot import resolve_geometry_modifier
from sidequest.game.ruleset.resolution import AttackRollParams
from sidequest.genre.models.inventory import DamageSpec
from sidequest.genre.models.rules import GeometryModifiers


@dataclass
class GunSolution:
    """A pilot who got a shot this cell + the SWN params to resolve it."""

    shooter_role: str
    shooter_name: str
    target_role: str
    target_name: str
    attack: AttackRollParams
    weapon: DamageSpec
    weapon_name: str
    target_armor: int
    geometry_modifier: int
```

Add `gun_solutions` to the outcome:

```python
@dataclass
class SealedLetterOutcome:
    cell_name: str
    red_maneuver: str
    blue_maneuver: str
    narration_hint: str
    extend_and_return_triggered: bool = False
    gun_solutions: list[GunSolution] = field(default_factory=list)
```

- [ ] **Step 4: Extend the resolver signature + add detection after geometry**

Change `resolve_sealed_letter_lookup`'s signature to accept optional SWN inputs (keep them optional so existing callers/tests that don't pass them still work and simply get no gun solutions):

```python
def resolve_sealed_letter_lookup(
    encounter: StructuredEncounter,
    commits: dict[str, str],
    table: InteractionTable,
    *,
    geometry_modifiers: GeometryModifiers | None = None,
    shot_inputs: dict[str, dict] | None = None,
    swn_cfg: object | None = None,
) -> SealedLetterOutcome:
```

After `_apply_view_deltas(...)` for both actors and before the `cell_resolved` span, add gun-solution detection:

```python
    gun_solutions: list[GunSolution] = []
    if geometry_modifiers is not None and shot_inputs and swn_cfg is not None:
        from sidequest.game.ruleset.swn import SwnRulesetModule

        swn = SwnRulesetModule()
        role_actor = {ROLE_RED: red_actor, ROLE_BLUE: blue_actor}
        for shooter_role, shooter in role_actor.items():
            if not bool(shooter.per_actor_state.get("gun_solution")):
                continue
            inp = shot_inputs.get(shooter_role)
            if inp is None:
                raise ValueError(
                    f"actor role={shooter_role!r} has a gun_solution but no shot_inputs "
                    "entry — dispatch must supply SWN params for every shooter (no silent skip)"
                )
            target_role = ROLE_BLUE if shooter_role == ROLE_RED else ROLE_RED
            geo = resolve_geometry_modifier(shooter.per_actor_state, geometry_modifiers)
            attack = swn.ship_attack_params(
                attacker_stats=inp["attacker_stats"],
                pilot_skill=inp["pilot_skill"],
                attack_bonus=inp["attack_bonus"],
                geometry_modifier=geo,
                target_ac=inp["target_ac"],
                cfg=swn_cfg,
            )
            gun_solutions.append(
                GunSolution(
                    shooter_role=shooter_role,
                    shooter_name=shooter.name,
                    target_role=target_role,
                    target_name=role_actor[target_role].name,
                    attack=attack,
                    weapon=inp["weapon"],
                    weapon_name=inp["weapon_name"],
                    target_armor=int(inp["target_armor"]),
                    geometry_modifier=geo,
                )
            )
```

Add `gun_solutions=gun_solutions` to the returned `SealedLetterOutcome(...)`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_sealed_letter_gun_solutions.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Run the existing sealed-letter suite for regression**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/ -k "sealed_letter" -v`
Expected: PASS — the new kwargs are optional; existing geometry/extend-and-return/energy tests unaffected.

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && git add sidequest/server/dispatch/sealed_letter.py tests/server/dispatch/test_sealed_letter_gun_solutions.py
git commit -m "feat(dogfight): detect gun solutions + compute SWN params in resolver"
```

---

## Task 10: `resolve_dogfight_shots` — pure shot resolution with injected d20s

Takes the detected `GunSolution`s + a `{shooter_role: d20_face}` map, computes hit/miss vs AC, rolls weapon damage on a hit, applies AP/armor, ablates target HP via `apply_hp_delta`, emits both shot spans, then runs `check_hp_depletion`. Resolves **all shots against pre-shot HP** (no shot ablates before all are computed). Mutual KO → `mutual_destruction`.

**Files:**
- Modify: `sidequest-server/sidequest/game/dogfight_shot.py`
- Test: `sidequest-server/tests/game/test_resolve_dogfight_shots.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_resolve_dogfight_shots.py`:

```python
from sidequest.game.creature_core import CreatureCore, Inventory, hp_pool_from_hp
from sidequest.game.encounter import EncounterActor, StructuredEncounter
from sidequest.game.ruleset.resolution import AttackRollParams
from sidequest.genre.models.inventory import DamageSpec
from sidequest.server.dispatch.sealed_letter import GunSolution
from sidequest.game.dogfight_shot import resolve_dogfight_shots


def _core(name, hp):
    return CreatureCore(
        name=name, description="", personality="", inventory=Inventory(),
        hp=hp_pool_from_hp(hp), armor_class=16,
    )


def _enc():
    enc = StructuredEncounter(encounter_type="dogfight", win_condition="sealed_letter")
    enc.actors = [
        EncounterActor(name="PC", role="red", side="player"),
        EncounterActor(name="Ace", role="blue", side="opponent"),
    ]
    return enc


def _gs(shooter_role, shooter, target_role, target, modifier):
    return GunSolution(
        shooter_role=shooter_role, shooter_name=shooter,
        target_role=target_role, target_name=target,
        attack=AttackRollParams(modifier=modifier, target_number=16),
        weapon=DamageSpec(dice="1d4", armor_piercing=20),
        weapon_name="multifocal laser", target_armor=5, geometry_modifier=4,
    )


def test_npc_hit_ablates_player_hp(monkeypatch):
    import sidequest.game.dogfight_shot as ds
    monkeypatch.setattr(ds, "_roll_damage_dice", lambda spec: 3)  # deterministic 1d4 -> 3
    cores = {"PC": _core("PC", 8), "Ace": _core("Ace", 8)}
    enc = _enc()
    gs = _gs("blue", "Ace", "red", "PC", modifier=13)  # 13 + d20
    res = resolve_dogfight_shots(
        encounter=enc, gun_solutions=[gs],
        d20_by_shooter={"blue": 10},  # 10 + 13 = 23 >= 16 hit
        edge_resolver=lambda n: cores.get(n),
    )
    # AP 20 vs armor 5 -> effective 0; applied = 3
    assert cores["PC"].hp.current == 5
    assert any(s.hit and s.shooter_role == "blue" for s in res.shots)


def test_miss_does_no_damage():
    cores = {"PC": _core("PC", 8), "Ace": _core("Ace", 8)}
    enc = _enc()
    gs = _gs("blue", "Ace", "red", "PC", modifier=0)
    res = resolve_dogfight_shots(
        encounter=enc, gun_solutions=[gs],
        d20_by_shooter={"blue": 5},  # 5 < 16 miss
        edge_resolver=lambda n: cores.get(n),
    )
    assert cores["PC"].hp.current == 8
    assert all(not s.hit for s in res.shots)


def test_mutual_kill_resolves_mutual_destruction(monkeypatch):
    import sidequest.game.dogfight_shot as ds
    monkeypatch.setattr(ds, "_roll_damage_dice", lambda spec: 4)
    cores = {"PC": _core("PC", 3), "Ace": _core("Ace", 3)}
    enc = _enc()
    shots = [
        _gs("blue", "Ace", "red", "PC", modifier=20),
        _gs("red", "PC", "blue", "Ace", modifier=20),
    ]
    res = resolve_dogfight_shots(
        encounter=enc, gun_solutions=shots,
        d20_by_shooter={"blue": 10, "red": 10},
        edge_resolver=lambda n: cores.get(n),
    )
    # both resolved against PRE-shot HP=3, 4 dmg each -> both to 0
    assert cores["PC"].hp.current == 0
    assert cores["Ace"].hp.current == 0
    assert enc.outcome == "mutual_destruction"
    assert res.depletion is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_resolve_dogfight_shots.py -v`
Expected: FAIL — `resolve_dogfight_shots` / `_roll_damage_dice` not defined.

- [ ] **Step 3: Find the existing damage-dice roller to reuse**

Run: `cd sidequest-server && grep -rn "def .*roll" sidequest/server/dispatch/damage_roll.py sidequest/game/dice*.py`
Expected: locate the function that rolls an `NdM` `DamageSpec` to an int (the value `apply_beat_hp_channel` ultimately consumes). Note its import path; the `_roll_damage_dice` wrapper below delegates to it so tests can monkeypatch one seam.

- [ ] **Step 4: Implement `resolve_dogfight_shots` + result types**

Append to `sidequest/game/dogfight_shot.py`:

```python
from dataclasses import dataclass, field
from typing import Callable

from sidequest.telemetry.spans.dogfight import (
    dogfight_shot_attempted_span,
    dogfight_shot_damage_span,
)


def _roll_damage_dice(spec) -> int:
    """Roll a DamageSpec's dice+bonus to an int. Thin wrapper over the engine's
    damage roller so a single seam is monkeypatchable in tests."""
    from sidequest.server.dispatch.damage_roll import roll_damage_spec  # confirm name in Step 3

    return roll_damage_spec(spec)


@dataclass
class ShotResult:
    shooter_role: str
    shooter_name: str
    target_name: str
    d20_total: int
    target_ac: int
    hit: bool
    applied: int
    source: str  # player | npc — set by caller-supplied source_by_shooter


@dataclass
class DogfightShotResolution:
    shots: list[ShotResult] = field(default_factory=list)
    depletion: object | None = None  # HpDepletionResult | None


def resolve_dogfight_shots(
    *,
    encounter,
    gun_solutions: list,
    d20_by_shooter: dict[str, int],
    edge_resolver: Callable[[str], object | None],
    source_by_shooter: dict[str, str] | None = None,
) -> DogfightShotResolution:
    """Resolve every gun solution against PRE-shot HP, then run depletion.

    Two-pass: pass 1 computes hit + damage for every shot (no mutation); pass 2
    ablates HP. This guarantees mutual solutions resolve against the same
    starting HP (mutual_destruction is reachable). Fails loud (ValueError) on a
    gun solution with no d20, no target core, or no weapon."""
    from sidequest.game.hp_depletion import check_hp_depletion

    source_by_shooter = source_by_shooter or {}
    results: list[ShotResult] = []
    pending_ablation: list[tuple[object, int, ShotResult, str]] = []

    # ---- Pass 1: compute hits + damage, no mutation ----
    for gs in gun_solutions:
        if gs.shooter_role not in d20_by_shooter:
            raise ValueError(
                f"gun solution for role={gs.shooter_role!r} has no d20 in "
                f"d20_by_shooter {sorted(d20_by_shooter)} — no silent skip"
            )
        target_core = edge_resolver(gs.target_name)
        if target_core is None:
            raise ValueError(
                f"gun solution target {gs.target_name!r} has no creature core "
                "(opponent not seated with stats) — fail loud per spec"
            )
        d20 = int(d20_by_shooter[gs.shooter_role])
        total = d20 + gs.attack.modifier
        hit = total >= gs.attack.target_number
        source = source_by_shooter.get(gs.shooter_role, "npc")
        with dogfight_shot_attempted_span(
            shooter=gs.shooter_name, target=gs.target_name,
            d20_total=total, target_ac=gs.attack.target_number, hit=hit,
            geometry_modifier=gs.geometry_modifier, source=source,
        ):
            pass
        applied = 0
        if hit:
            raw = _roll_damage_dice(gs.weapon)
            eff_armor = effective_armor_after_ap(
                armor=gs.target_armor, armor_piercing=gs.weapon.armor_piercing
            )
            applied = max(0, raw - eff_armor)
            pending_ablation.append((target_core, applied, None, str(eff_armor)))
        res = ShotResult(
            shooter_role=gs.shooter_role, shooter_name=gs.shooter_name,
            target_name=gs.target_name, d20_total=total,
            target_ac=gs.attack.target_number, hit=hit, applied=applied, source=source,
        )
        results.append(res)
        if hit:
            # backfill the ShotResult ref + armor-negated for the damage span
            target_core_ref, applied_v, _, eff = pending_ablation[-1]
            pending_ablation[-1] = (target_core_ref, applied_v, res, eff)

    # ---- Pass 2: ablate HP + emit damage spans ----
    for target_core, applied, res, eff in pending_ablation:
        if applied > 0:
            target_core.apply_hp_delta(-applied)
        # find the weapon dice for the span
        gs = next(g for g in gun_solutions if g.shooter_role == res.shooter_role)
        with dogfight_shot_damage_span(
            shooter=res.shooter_name, target=res.target_name,
            dice=gs.weapon.dice, armor_piercing=gs.weapon.armor_piercing,
            armor_negated=int(eff) and gs.target_armor - int(eff) or gs.target_armor,
            applied=applied, target_hp_after=target_core.hp.current,
        ):
            pass

    depletion = check_hp_depletion(encounter, edge_resolver)
    return DogfightShotResolution(shots=results, depletion=depletion)
```

(In Step 3 you confirmed the real roller name; if it isn't `roll_damage_spec`, update the import in `_roll_damage_dice`. The `armor_negated` expression computes `armor − effective_armor`; simplify to `gs.target_armor - int(eff)` if clearer — keep it equal to the negated soak.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_resolve_dogfight_shots.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/game/dogfight_shot.py tests/game/test_resolve_dogfight_shots.py
git commit -m "feat(dogfight): resolve_dogfight_shots — SWN shot resolution with injected d20s"
```

---

## Task 11: Assert SWN binding + assemble shot inputs at the dispatch seam

A pure helper that builds the `shot_inputs` map and `swn_cfg` the resolver needs, sourcing the opponent ace from `opponent_default_stats` and the PC from `player_default_stats` + the PC's real sheet (Pilot skill / attributes). Fails loud if the pack isn't SWN-bound or the dogfight opponent isn't seated.

**Files:**
- Modify: `sidequest-server/sidequest/game/dogfight_shot.py` (add `build_dogfight_shot_inputs`)
- Test: `sidequest-server/tests/game/test_dogfight_shot_inputs.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_dogfight_shot_inputs.py`:

```python
import pytest

from sidequest.game.dogfight_shot import build_dogfight_shot_inputs


class _Weapon:
    def __init__(self):
        from sidequest.genre.models.inventory import DamageSpec
        self.spec = DamageSpec(dice="1d4", armor_piercing=20)


def test_build_inputs_fails_loud_when_not_swn():
    with pytest.raises(ValueError, match="requires SWN"):
        build_dogfight_shot_inputs(ruleset_slug="native", cdef=None, encounter=None,
                                   pc_stats={}, pc_pilot_skill=0, pc_attack_bonus=0,
                                   weapon_lookup=lambda wid: None)
```

(This first test pins the fail-loud SWN guard. A second, fuller test that asserts the assembled opponent/player input dicts requires a constructed `cdef` + `encounter`; add it after Step 3 once the helper's shape is concrete, modeling the dicts the resolver consumes in Task 9's test.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/game/test_dogfight_shot_inputs.py -v`
Expected: FAIL — `build_dogfight_shot_inputs` not defined.

- [ ] **Step 3: Implement the input assembler**

Append to `sidequest/game/dogfight_shot.py`:

```python
def build_dogfight_shot_inputs(
    *,
    ruleset_slug: str,
    cdef,
    encounter,
    pc_stats: dict[str, int],
    pc_pilot_skill: int,
    pc_attack_bonus: int,
    weapon_lookup: Callable[[str], object | None],
):
    """Assemble the per-role SWN shot inputs the resolver needs.

    Returns ``(shot_inputs, geometry_modifiers)``. Opponent ace numbers come
    from ``cdef.opponent_default_stats``; the PC frame from
    ``cdef.player_default_stats`` with Pilot skill / attributes overridden by
    the PC's real sheet. Fails loud if the pack isn't SWN-bound, the dogfight
    def lacks geometry_modifiers, or a weapon id can't be resolved."""
    if ruleset_slug != "swn":
        raise ValueError(
            f"dogfight SWN resolution requires SWN binding; pack ruleset={ruleset_slug!r}"
        )
    if cdef.geometry_modifiers is None:
        raise ValueError("dogfight ConfrontationDef missing geometry_modifiers block")

    def _weapon(stats_block: dict):
        wid = stats_block.get("weapon")
        if not wid:
            raise ValueError("dogfight shooter frame missing 'weapon' id")
        item = weapon_lookup(wid)
        if item is None or getattr(item, "damage", None) is None:
            raise ValueError(f"dogfight weapon id {wid!r} not found / has no damage spec")
        return item.damage, getattr(item, "name", wid)

    role_by_side = {a.side: a.role for a in encounter.actors}
    opp_role = role_by_side.get("opponent")
    pc_role = role_by_side.get("player")
    if opp_role is None or pc_role is None:
        raise ValueError("dogfight encounter missing player or opponent actor")

    opp = cdef.opponent_default_stats
    pcf = cdef.player_default_stats
    opp_weapon, opp_weapon_name = _weapon(opp)
    pc_weapon, pc_weapon_name = _weapon(pcf)

    shot_inputs = {
        opp_role: {
            "attacker_stats": opp,
            "pilot_skill": int(opp.get("pilot_skill", 0)),
            "attack_bonus": int(opp.get("attack_bonus", 0)),
            "target_ac": int(pcf["armor_class"]),
            "target_armor": int(pcf["armor"]),
            "weapon": opp_weapon, "weapon_name": opp_weapon_name,
        },
        pc_role: {
            "attacker_stats": pc_stats,
            "pilot_skill": int(pc_pilot_skill),
            "attack_bonus": int(pc_attack_bonus),
            "target_ac": int(opp["armor_class"]),
            "target_armor": int(opp["armor"]),
            "weapon": pc_weapon, "weapon_name": pc_weapon_name,
        },
    }
    return shot_inputs, cdef.geometry_modifiers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/game/test_dogfight_shot_inputs.py -v`
Expected: PASS (1 test); add the fuller assembled-dict test now and make it pass.

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && git add sidequest/game/dogfight_shot.py tests/game/test_dogfight_shot_inputs.py
git commit -m "feat(dogfight): assemble SWN shot inputs + SWN-binding guard"
```

---

## Task 12: Seed the opponent ace HP/AC for the dogfight (verify 59-17 path)

The opponent must carry an `Npc.core` with HP 8 / AC 16 so `resolve_dogfight_shots`' `edge_resolver` finds a target. Reuse `_seed_combat_hp_depletion_to_npcs`. Verify it fires for the sealed-letter dogfight; if it's gated on `win_condition == "hp_depletion"`, widen the gate to also cover the dogfight.

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py` (seeding call site)
- Test: `sidequest-server/tests/server/dispatch/test_dogfight_opponent_seeding.py`

- [ ] **Step 1: Find the seeding call site and its gate**

Run: `cd sidequest-server && grep -n "_seed_combat_hp_depletion_to_npcs\|hp_depletion\|sealed_letter" sidequest/server/dispatch/encounter_lifecycle.py`
Expected: shows where `_seed_combat_hp_depletion_to_npcs` is invoked and the condition guarding it. Determine whether a `dogfight` (win_condition `sealed_letter`, category `combat`) currently reaches it.

- [ ] **Step 2: Write the failing test**

Create `sidequest-server/tests/server/dispatch/test_dogfight_opponent_seeding.py` — construct a dogfight instantiation through the lifecycle path (model it on an existing `encounter_lifecycle` test) and assert the opponent actor's backing `Npc.core.hp.max == 8` and `armor_class == 16` after seeding.

```python
# Skeleton — fill the instantiation harness from the nearest existing
# encounter_lifecycle test (grep tests/server/dispatch for one that calls the
# instantiation entrypoint and inspects snapshot.npcs).
def test_dogfight_opponent_seeded_with_strike_fighter_stats(...):
    # ... instantiate the space_opera dogfight via the production path ...
    ace = next(n for n in snapshot.npcs if n.core.name == opponent_name)
    assert ace.core.hp.max == 8
    assert ace.core.armor_class == 16
```

- [ ] **Step 3: Run test to verify it fails (or passes — diagnostic)**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_dogfight_opponent_seeding.py -v`
Expected: If 59-17 already wired seeding for the dogfight, this may PASS with the OLD stats (hp 30) and FAIL the `== 8` assertion — confirming Task 5's content change flows. If seeding is gated off for `sealed_letter`, it FAILS with no seeded core.

- [ ] **Step 4: Widen the seeding gate if needed**

If the gate excludes the dogfight, change it to also seed when `cdef.type == "dogfight"` (or `resolution_mode == sealed_letter` with `category == combat`). Keep it explicit — no blanket "seed everything." Example:

```python
    needs_hp_seed = enc.win_condition == "hp_depletion" or cdef.type == "dogfight"
    if needs_hp_seed:
        _seed_combat_hp_depletion_to_npcs(...)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/dispatch/test_dogfight_opponent_seeding.py -v`
Expected: PASS — opponent seeded with hp 8 / AC 16.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/server/dispatch/encounter_lifecycle.py tests/server/dispatch/test_dogfight_opponent_seeding.py
git commit -m "feat(dogfight): seed strike-fighter opponent HP/AC at instantiation"
```

---

## Task 13: Wire shots into the sealed-letter dispatch branch (NPC-only + interim all-server-rolled)

First wiring slice — fully playable. In `_apply_narration_result_to_snapshot`'s sealed-letter branch: after `resolve_sealed_letter_lookup`, if there are gun solutions, server-roll a d20 per shooter, call `resolve_dogfight_shots`, and (if resolved) build the resolution signal. **This slice server-rolls the player too** (interim per Reconciliation #5); Task 14 replaces the player's roll with the client throw.

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py:2581-2637` (sealed-letter branch)
- Test: `sidequest-server/tests/server/test_dogfight_shot_wiring.py`

- [ ] **Step 1: Write the failing wiring test (OTEL-driven)**

Create `sidequest-server/tests/server/test_dogfight_shot_wiring.py` — drive a sealed-letter dogfight turn where a cell yields an NPC gun solution, through `_apply_narration_result_to_snapshot`, and assert (a) the player's HP dropped and (b) `dogfight.shot_attempted` + `dogfight.shot_damage` spans fired. Model the harness on an existing `narration_apply` sealed-letter test (`grep -rln "resolution_mode.*sealed_letter\|sealed_letter" tests/server/`).

```python
def test_npc_gun_solution_ablates_player_hp_and_emits_spans(span_exporter, ...):
    # ... build snapshot with SWN space_opera dogfight, seated ace, PC frame ...
    # ... craft a narration result whose beat_selections commit maneuvers that
    #     land on a cell giving the NPC (opponent) a gun_solution ...
    _apply_narration_result_to_snapshot(snapshot, result, player_name, room=room, pack=pack)
    spans = [s.name for s in span_exporter.get_finished_spans()]
    assert any(n.endswith("shot_attempted") for n in spans)
    assert any(n.endswith("shot_damage") for n in spans)
    # PC HP < frame max after a hit (deterministic via monkeypatched d20/dice)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_dogfight_shot_wiring.py -v`
Expected: FAIL — no shot spans (the branch doesn't resolve shots yet).

- [ ] **Step 3: Wire the shot phase into the branch**

In `sidequest/server/narration_apply.py`, in the `if cdef.resolution_mode == ResolutionMode.sealed_letter_lookup:` block, after building `commits` and BEFORE calling the resolver, assemble shot inputs; pass them to the resolver; then resolve shots:

```python
                from sidequest.game.dogfight_shot import (
                    build_dogfight_shot_inputs,
                    resolve_dogfight_shots,
                )
                from sidequest.server.narration_apply import _roll_d20_server_side  # or its module

                pc_actor = next((a for a in enc.actors if a.side == "player"), None)
                pc_core = (
                    snapshot.find_creature_core(pc_actor.name) if pc_actor is not None else None
                )
                # PC pilot skill + attack bonus from the real sheet; fall back to
                # the authored frame default (player_default_stats) — authored, not silent.
                pc_pilot_skill = _pc_pilot_skill(pc_core, cdef)   # helper: sheet skill or frame default
                pc_attack_bonus = _pc_attack_bonus(pc_core, cdef)
                pc_stats = _pc_stats_for_swn(pc_core, snapshot, pack)  # flavor stat dict

                shot_inputs, geo_mods = build_dogfight_shot_inputs(
                    ruleset_slug=pack.rules.ruleset,
                    cdef=cdef,
                    encounter=enc,
                    pc_stats=pc_stats,
                    pc_pilot_skill=pc_pilot_skill,
                    pc_attack_bonus=pc_attack_bonus,
                    weapon_lookup=lambda wid: pack.find_item(wid),  # confirm catalog accessor name
                )

                sl_outcome = resolve_sealed_letter_lookup(
                    enc, commits, cdef.interaction_table,
                    geometry_modifiers=geo_mods,
                    shot_inputs=shot_inputs,
                    swn_cfg=pack.rules.swn,
                )

                if sl_outcome.gun_solutions:
                    # Interim: both pilots server-roll. Task 14 swaps the player's
                    # roll for the client Rapier throw.
                    d20_by_shooter = {
                        gs.shooter_role: _roll_d20_server_side()
                        for gs in sl_outcome.gun_solutions
                    }
                    source_by_shooter = {
                        gs.shooter_role: ("player" if gs.shooter_role == (pc_actor.role if pc_actor else None) else "npc")
                        for gs in sl_outcome.gun_solutions
                    }
                    shot_res = resolve_dogfight_shots(
                        encounter=enc,
                        gun_solutions=sl_outcome.gun_solutions,
                        d20_by_shooter=d20_by_shooter,
                        edge_resolver=snapshot.find_creature_core,
                        source_by_shooter=source_by_shooter,
                    )
                    if shot_res.depletion is not None:
                        snapshot.pending_resolution_signal = _build_resolution_signal(enc)
```

Add the three small PC-stat helper functions (`_pc_pilot_skill`, `_pc_attack_bonus`, `_pc_stats_for_swn`) near the top of the module. `_pc_pilot_skill`/`_pc_attack_bonus` read the PC sheet skill/progression if present, else `cdef.player_default_stats["pilot_skill"]`/`["attack_bonus"]` (authored default — document the precedence in a comment, no silent zero). `_pc_stats_for_swn` returns the PC's flavor-stat dict the SWN attribute_map expects. (Confirm `snapshot.find_creature_core`, `pack.find_item`, and `pack.rules.swn` accessor names via grep; adjust.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_dogfight_shot_wiring.py -v`
Expected: PASS — shot spans fire, PC HP drops.

- [ ] **Step 5: Run the broader dogfight + narration_apply regression**

Run: `cd sidequest-server && uv run pytest tests/server/ -k "sealed_letter or dogfight or narration_apply" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && git add sidequest/server/narration_apply.py tests/server/test_dogfight_shot_wiring.py
git commit -m "feat(dogfight): wire SWN shot resolution into sealed-letter dispatch (server-rolled)"
```

---

## Task 14: Player shot via client Rapier throw (round-trip)

Realize locked decision #7: the player's shot uses a client-side `DiceRequestMessage` → Rapier throw → `DiceThrowPayload`; the NPC shot stays server-rolled and is held against pre-shot HP until the player's d20 returns. Reuses the opposed-check stash-and-re-enter precedent.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_state.py` (`_SessionData` stash)
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (signal a pending player shot instead of server-rolling it)
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (emit `DiceRequestMessage`, stash, clear)
- Modify: `sidequest-server/sidequest/handlers/dice_throw.py` (detect + resolve a pending dogfight shot)
- Test: `sidequest-server/tests/server/test_dogfight_player_throw_roundtrip.py`

- [ ] **Step 1: Add the `_SessionData` stash + write the failing test**

In `sidequest/server/session_state.py`, add to `_SessionData` (beside the opposed-check fields):

```python
    # Pending dogfight player shot (SWN dogfight). Set when a sealed-letter turn
    # yields a player gun_solution: the held NPC shot(s) + the player's gun
    # solution wait here for the player's client Rapier d20 (DICE_THROW). Read
    # and cleared by the dice_throw handler, which resolves all shots against
    # pre-shot HP. None when no dogfight shot is pending.
    pending_dogfight_shot: Any | None = None
```

Define the payload type (a small frozen dataclass) in `sidequest/game/dogfight_shot.py`:

```python
@dataclass
class PendingDogfightShot:
    gun_solutions: list           # list[GunSolution]
    npc_d20_by_shooter: dict      # role -> server-rolled d20 (held)
    player_shooter_role: str      # the role awaiting the client throw
    encounter_type: str
```

Create `sidequest-server/tests/server/test_dogfight_player_throw_roundtrip.py`:

```python
def test_player_gun_solution_stashes_pending_shot_and_emits_dice_request(...):
    # drive a sealed-letter turn where the PLAYER (red, side=player) gets a
    # gun_solution; assert: (a) NO player HP/opponent HP changed yet,
    # (b) a DICE_REQUEST frame was emitted, (c) sd.pending_dogfight_shot is set.
    ...

def test_dice_throw_completes_pending_shot_and_resolves(span_exporter, ...):
    # given a stashed pending_dogfight_shot, dispatch a DICE_THROW carrying the
    # player's face; assert shots resolve, HP ablates, shot spans fire, and
    # sd.pending_dogfight_shot is cleared.
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_dogfight_player_throw_roundtrip.py -v`
Expected: FAIL — no pending stash / no DICE_REQUEST emitted.

- [ ] **Step 3: Signal a pending player shot in the sealed-letter branch**

In `narration_apply.py`, replace Task 13's "both pilots server-roll" block with a player/NPC split:

```python
                if sl_outcome.gun_solutions:
                    pc_role = pc_actor.role if pc_actor else None
                    player_solos = [g for g in sl_outcome.gun_solutions if g.shooter_role == pc_role]
                    npc_solos = [g for g in sl_outcome.gun_solutions if g.shooter_role != pc_role]
                    # NPC shots roll server-side now and are HELD (not applied).
                    npc_d20 = {gs.shooter_role: _roll_d20_server_side() for gs in npc_solos}

                    if player_solos:
                        # Defer: stash held NPC rolls + player solution; emit a
                        # DiceRequest at the session-handler layer; resolve on
                        # the player's DICE_THROW.
                        from sidequest.game.dogfight_shot import PendingDogfightShot

                        outcome.pending_dogfight_shot = PendingDogfightShot(
                            gun_solutions=sl_outcome.gun_solutions,
                            npc_d20_by_shooter=npc_d20,
                            player_shooter_role=pc_role,
                            encounter_type=enc.encounter_type,
                        )
                        outcome.pending_dogfight_player_attack = player_solos[0].attack
                        outcome.pending_dogfight_player_actor = pc_actor.name
                    else:
                        # NPC-only: resolve immediately (Task 13 path).
                        shot_res = resolve_dogfight_shots(
                            encounter=enc, gun_solutions=npc_solos,
                            d20_by_shooter=npc_d20,
                            edge_resolver=snapshot.find_creature_core,
                            source_by_shooter={gs.shooter_role: "npc" for gs in npc_solos},
                        )
                        if shot_res.depletion is not None:
                            snapshot.pending_resolution_signal = _build_resolution_signal(enc)
```

Add `pending_dogfight_shot`, `pending_dogfight_player_attack`, `pending_dogfight_player_actor` fields to the `NarrationApplyOutcome` type (find its dataclass/model definition in `narration_apply.py`).

- [ ] **Step 4: Emit the DiceRequest + stash at the session handler**

In `websocket_session_handler.py`, after `_apply_narration_result_to_snapshot` returns `applied_outcome` (~line 855-906), if `applied_outcome.pending_dogfight_shot is not None`: build a `DiceRequestMessage` (one d20, `modifier = pending_dogfight_player_attack.modifier`, `difficulty = pending_dogfight_player_attack.target_number`, `context="dogfight gun solution"`, `character_name = pending_dogfight_player_actor`) and append it to `outbound`; stash `sd.pending_dogfight_shot = applied_outcome.pending_dogfight_shot`. Model the message construction on how the opposed-check / combat path builds its `DiceRequestMessage` (grep `DiceRequestMessage(` in the handler). Add `sd.pending_dogfight_shot = None` to the existing stash-clear block (lines ~900-906).

- [ ] **Step 5: Resolve the pending shot on DICE_THROW**

In `sidequest/handlers/dice_throw.py`, before/around the opposed-check stash logic (~line 232), detect a pending dogfight shot and route to resolution instead of the normal beat path:

```python
    if getattr(sd, "pending_dogfight_shot", None) is not None:
        from sidequest.game.dogfight_shot import resolve_dogfight_shots

        pending = sd.pending_dogfight_shot
        player_face_total = sum(payload.face)  # single d20 -> its face value
        d20_by_shooter = dict(pending.npc_d20_by_shooter)
        d20_by_shooter[pending.player_shooter_role] = player_face_total
        source_by_shooter = {
            gs.shooter_role: ("player" if gs.shooter_role == pending.player_shooter_role else "npc")
            for gs in pending.gun_solutions
        }
        shot_res = resolve_dogfight_shots(
            encounter=encounter,
            gun_solutions=pending.gun_solutions,
            d20_by_shooter=d20_by_shooter,
            edge_resolver=snapshot.find_creature_core,
            source_by_shooter=source_by_shooter,
        )
        sd.pending_dogfight_shot = None
        # Broadcast the player's DiceResult + the resolution narration handshake
        # (reuse the existing DICE_RESULT broadcast + NARRATION_END path).
        # ... build DiceResultOutcome and return it ...
```

Confirm: `payload.face` is the client-thrown faces list (per `DiceThrowPayload`); a single d20 means `face == [n]`. Surface the player's roll via the existing `DiceResultMessage` broadcast so Sebastien/Jade see the d20+AC+damage (player-facing math legibility). Wire the resolution into the same `DiceThrowOutcome` return shape the handler already uses so narration/broadcast fire.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_dogfight_player_throw_roundtrip.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Full dogfight + dice regression**

Run: `cd sidequest-server && uv run pytest tests/server/ -k "dogfight or dice or sealed_letter or opposed" -v`
Expected: PASS — opposed-check stash and dogfight stash coexist without cross-talk.

- [ ] **Step 8: Commit**

```bash
cd sidequest-server && git add sidequest/server/session_state.py sidequest/server/narration_apply.py sidequest/server/websocket_session_handler.py sidequest/handlers/dice_throw.py sidequest/game/dogfight_shot.py tests/server/test_dogfight_player_throw_roundtrip.py
git commit -m "feat(dogfight): player shot via client Rapier throw; NPC shot held server-side"
```

---

## Task 15: Production-path wiring test (CLAUDE.md mandatory)

One integration test driving the **whole** flow through production code: instantiation → opponent seated with SWN stats → maneuver commits → gun solution → shot (NPC server + player client throw) → HP ablation → `hp_depletion` resolve, asserting OTEL spans fire in order.

**Files:**
- Test: `sidequest-server/tests/server/test_dogfight_swn_production_wiring.py`

- [ ] **Step 1: Write the end-to-end wiring test**

Create `sidequest-server/tests/server/test_dogfight_swn_production_wiring.py`. Use the real `space_opera` pack (load via the loader with `SIDEQUEST_GENRE_PACKS` pointing at `../sidequest-content/genre_packs`), instantiate the dogfight through the production instantiation entrypoint (model on Task 12's harness), then:

1. Assert the opponent NPC core is seated (hp 8 / AC 16).
2. Commit maneuvers (red + blue beat_selections) landing on a cell with a player gun solution; run the turn.
3. Assert `sd.pending_dogfight_shot` is set and a `DICE_REQUEST` frame emitted.
4. Dispatch a `DICE_THROW` with a deterministic high face (monkeypatch `_roll_d20_server_side` + the damage roller for determinism).
5. Assert: opponent HP ablated, the ordered span sequence fired —
   `dogfight.confrontation_started` → `dogfight.maneuver_committed`×2 → `dogfight.cell_resolved` → `dogfight.shot_attempted` (source player + npc) → `dogfight.shot_damage` → (on a kill) `encounter.resolved` with `source="hp_depletion"`.

```python
def test_dogfight_full_swn_production_path(span_exporter, monkeypatch, ...):
    # ... load real space_opera, instantiate dogfight, drive the two-message
    #     round-trip, assert span ORDER and HP ablation ...
    names = [s.name for s in span_exporter.get_finished_spans()]
    def _idx(suffix): return next(i for i, n in enumerate(names) if n.endswith(suffix))
    assert _idx("cell_resolved") < _idx("shot_attempted") < _idx("shot_damage")
```

- [ ] **Step 2: Run it; iterate to green**

Run: `cd sidequest-server && uv run pytest tests/server/test_dogfight_swn_production_wiring.py -v`
Expected: PASS. This is the test that proves the feature is *wired*, not merely present — fix real wiring gaps it surfaces (do not weaken the assertions to pass).

- [ ] **Step 3: Commit**

```bash
cd sidequest-server && git add tests/server/test_dogfight_swn_production_wiring.py
git commit -m "test(dogfight): production-path SWN dogfight wiring test with span ordering"
```

---

## Task 16: Remove dead deterministic-damage code + final gate

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/sealed_letter.py` (any residual `damage_increments`/`starting_hull`/`hit_severity` references)
- Sweep: server + content

- [ ] **Step 1: Grep for any remaining deterministic-damage references**

Run: `cd sidequest-server && grep -rn "damage_increments\|starting_hull\|hit_severity" sidequest/ && cd ../sidequest-content && grep -rn "damage_increments\|starting_hull\|hit_severity" genre_packs/space_opera/`
Expected: no hits. Delete any stragglers (per CLAUDE.md: delete dead code in the same change; no half-stripped fields).

- [ ] **Step 2: Run the full server gate**

Run: `cd sidequest-server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest -q`
Expected: clean lint/format, no type errors, full suite green. Fix everything before opening PRs.

- [ ] **Step 3: Commit any cleanup**

```bash
cd sidequest-server && git add -A && git commit -m "chore(dogfight): remove dead deterministic-damage references"
```

---

## Self-Review (completed by author)

**Spec coverage** — every spec section maps to a task:
- Content (a) strip damage → Tasks 2 (model) + 5 (YAML). (b) opponent statline → Task 5 + 12. (c) PC frame → Task 5 (`player_default_stats`) + 11/13 (seeding/sourcing). (d) geometry_modifiers → Task 3 + 5 + 6. (e) weapon + AP → Task 1 + 5 + 6.
- Server (1) `ship_attack_params` → Task 4. (2) shot phase in resolver → Tasks 9 (detect) + 13/14 (resolve/round-trip). (3) damage + AP → Task 6 + 10. (4) shared depletion → Task 8. (5) OTEL → Task 7 (+ asserted in 13/15). (6) remove dead damage → Task 2 + 16.
- Edge cases: no gun solution → Task 9 test; mutual → Task 10 test; AP floors → Task 6 test; missing weapon/AC/HP fail loud → Task 10/11 raises; already-resolved guard → Task 8 helper guard; non-SWN pack → Task 11 guard. Dice-disconnect: follows existing combat behavior (no new path) — noted, not a task (the round-trip reuses the existing DICE_REQUEST plumbing whose timeout behavior is unchanged).
- Out of scope honored: no PvP, no ship_combat change, no Speed→to-hit, no owned Ship entity, no cockpit HUD.

**Placeholder scan** — code steps carry real bodies. Three spots are explicitly flagged for the engineer to confirm-then-fill against the live code (the damage-roller function name in Task 10 Step 3; the catalog/`find_item` + `pack.rules.swn` accessor names in Task 13 Step 3; the span-capture fixture name in Task 7). These are *verification* steps with a grep command provided, not hidden TODOs.

**Type consistency** — `GunSolution`, `SealedLetterOutcome.gun_solutions`, `resolve_dogfight_shots(d20_by_shooter=...)`, `PendingDogfightShot`, `build_dogfight_shot_inputs(...)`, `effective_armor_after_ap`, `resolve_geometry_modifier`, `check_hp_depletion`, `ship_attack_params(...)`, `armor_piercing`, `geometry_modifiers`, `player_default_stats` are used with identical names/signatures across the tasks that define and consume them.

**Design-risk note for execution:** Tasks 13 and 14 are the highest-risk (cross-message state machine, PC-stat sourcing seam). Recommend subagent-driven execution with a review checkpoint after each.
