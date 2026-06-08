# Heavy Metal → WWN, Story 1: Binding + Combat Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind the `heavy_metal` genre pack to the `wwn` ruleset with ablative-HP combat (the de-risking foundation of the heavy_metal→WWN epic), proven by an end-to-end OTEL wiring test on the real pack.

**Architecture:** Pure content + config port — **no new engine code**. The `wwn` ruleset module, `hp_depletion` combat spine, and `state_patch.hp` lie-detector span are already live (proven by `elemental_harmony`). This story (1) rewrites `heavy_metal/rules.yaml` to bind `ruleset: wwn` with a canonical→abbreviation `attribute_map`, convert the `combat` confrontation to `beat_selection` + `hp_depletion`, and remove the ADR-078 `edge_config` block; (2) adds an integration test driving the real bound pack's combat through the production seating + dice seam, asserting HP ablates and the span fires; (3) migrates the one collateral load test.

**Tech Stack:** Python 3.12 / pydantic v2 (`sidequest-server`), YAML genre packs (`sidequest-content`), pytest (`uv run pytest`), OTEL InMemorySpanExporter.

**Repos (two — branch BOTH off `develop` before any commit):**
- `sidequest-content` — `genre_packs/heavy_metal/rules.yaml`
- `sidequest-server` — `tests/integration/`, `tests/genre/`

**Spec:** `docs/superpowers/specs/2026-06-04-heavy-metal-wwn-port-design.md` (§6 is this story).

**Test environment (mandatory — without these the suite throws phantom failures):**
```bash
export SIDEQUEST_DATABASE_URL="postgresql://$USER@localhost:5432/sidequest_test"
export SIDEQUEST_GENRE_PACKS="/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs"
```

---

## Task 0: Branch both repos off `develop`

**Files:** none (git only)

- [ ] **Step 1: Branch sidequest-content**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git checkout develop && git pull --ff-only
git checkout -b feat/heavy-metal-wwn-story-1
git branch --show-current   # expect: feat/heavy-metal-wwn-story-1
```

- [ ] **Step 2: Branch sidequest-server**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git checkout develop && git pull --ff-only
git checkout -b feat/heavy-metal-wwn-story-1
git branch --show-current   # expect: feat/heavy-metal-wwn-story-1
```

---

## Task 1: Write the end-to-end WWN combat wiring proof (RED)

This is the mandated wiring test (CLAUDE.md: "Every Test Suite Needs a Wiring Test"; "the GM panel is the lie detector"). It drives the **real** `heavy_metal` pack through the **production** seating seam (`instantiate_encounter_from_trigger`) and the **production** dice seam (`dispatch_dice_throw`), asserting (a) the pack is bound `ruleset: wwn`, (b) a strike beat ablates the opponent's HP, and (c) the `state_patch.hp` span fires. It is RED now because the pack is still `native` (no `ruleset`, combat is `opposed_check` with momentum dials and no HP).

Modeled on `tests/integration/test_space_opera_hp_e2e.py` (the `dispatch_dice_throw` strike→HP path) seated via the real-pack seam from `tests/integration/test_wwn_elemental_harmony_dispatch.py`.

**Files:**
- Create: `sidequest-server/tests/integration/test_wwn_heavy_metal_combat.py`

- [ ] **Step 1: Write the failing wiring test**

```python
"""Heavy Metal → WWN Story 1 — end-to-end combat wiring proof.

Drives the REAL heavy_metal pack (ruleset: wwn) through the production seating
seam (instantiate_encounter_from_trigger) and the production dice seam
(dispatch_dice_throw) with the converted Blade-work combat
(beat_selection / hp_depletion). Proves on the real bound pack:

  1. pack.rules.ruleset == "wwn";
  2. the opponent seats with hp/armor_class from opponent_default_stats;
  3. a strike beat ablates the opponent's HP through the HP channel;
  4. the state_patch.hp span fires (the GM-panel lie detector).

The strike beat under test ("committed_blow") carries a deterministic
damage_override (2d6) so the proof does not depend on weapon-catalog plumbing;
rng is pinned so the damage roll is deterministic.

Skips cleanly when sidequest-content is not present on disk.
"""

from __future__ import annotations

import pytest

from tests._helpers.genre_paths import GENRE_PACKS_DIR, PackNotFound, find_pack_path

# Authored on heavy_metal Blade-work opponent_default_stats (rules.yaml, Task 2).
_OPPONENT_HP = 10
_OPPONENT_AC = 12
_STRIKE_BEAT = "committed_blow"  # strike, damage_override 2d6 (deterministic)


def _has_real_content() -> bool:
    return GENRE_PACKS_DIR.is_dir()


def _load_heavy_metal():
    from sidequest.genre.loader import load_genre_pack

    try:
        return load_genre_pack(find_pack_path("heavy_metal"))
    except PackNotFound:
        pytest.skip("sidequest-content not on disk in this checkout")


def _make_attacker(name: str):
    """Synthetic Warrior attacker. Story 1 has no classes.yaml yet (Story 2),
    so the attacker is built directly, not through CharacterBuilder."""
    from sidequest.game.character import Character
    from sidequest.game.creature_core import CreatureCore, Inventory

    core = CreatureCore(
        name=name,
        description="A blade-bearer of a house that is ending.",
        personality="grim",
        inventory=Inventory(),
        hp={"current": 12, "max": 12, "base_max": 12},
    )
    return Character(core=core, char_class="Warrior", race="Human", backstory="—")


@pytest.mark.skipif(not _has_real_content(), reason="sidequest-content not on disk")
def test_heavy_metal_combat_is_wwn_bound_and_ablates_hp(otel_capture, monkeypatch):
    from sidequest.agents.orchestrator import NpcMention
    from sidequest.game.session import GameSnapshot
    from sidequest.game.turn import TurnManager
    from sidequest.protocol.dice import DiceThrowPayload, ThrowParams
    from sidequest.server.dispatch.dice import dispatch_dice_throw
    from sidequest.server.dispatch.encounter_lifecycle import (
        instantiate_encounter_from_trigger,
    )
    from sidequest.telemetry.spans.state_patch import SPAN_STATE_PATCH_HP

    pack = _load_heavy_metal()

    # ── Assertion 0: the pack is bound ruleset: wwn ───────────────────────
    assert pack.rules is not None
    assert pack.rules.ruleset == "wwn", (
        f"heavy_metal must be bound ruleset: wwn; got {pack.rules.ruleset!r}"
    )

    # ── Snapshot + attacker ───────────────────────────────────────────────
    attacker_name = "Sael"
    opponent = "The Collector's Blade"
    snap = GameSnapshot(
        genre_slug="heavy_metal",
        world_slug="test_world",
        turn_manager=TurnManager(interaction=2),
    )
    snap.characters.append(_make_attacker(attacker_name))
    snap.character_locations[attacker_name] = "The Antechamber"

    # ── Seat the real Blade-work combat via the production seam ────────────
    enc = instantiate_encounter_from_trigger(
        snapshot=snap,
        pack=pack,
        encounter_type="combat",
        player_name=attacker_name,
        npcs_present=[NpcMention(name=opponent, side="opponent")],
        genre_slug="heavy_metal",
    )
    assert enc is not None, "seating Blade-work must produce an encounter"
    snap.encounter = enc

    opponent_core = snap.find_creature_core(opponent)
    assert opponent_core is not None, (
        "opponent core must be reachable via find_creature_core — without it the "
        "strike has no defender HP to ablate"
    )
    assert opponent_core.armor_class == _OPPONENT_AC, (
        "opponent AC must come from opponent_default_stats"
    )
    assert opponent_core.hp.current == _OPPONENT_HP, (
        "opponent HP must come from opponent_default_stats"
    )

    # ── Pin rng: max 2d6 roll → deterministic damage, but below the 10-HP
    # kill threshold is not guaranteed; pin to MIN (1 per die = 2) so the
    # opponent survives and the downed seam is not tripped (this story proves
    # ablation, not the kill path). ──────────────────────────────────────
    monkeypatch.setattr(
        "sidequest.server.dispatch.dice.random.randint", lambda a, b: a
    )

    hp_before = opponent_core.hp.current

    # face high enough to clear the strike DC (base=4 → DC = 10 + 4*2 = 18;
    # face 20 + STR mod clears it). character_stats passes the attacker's STR.
    broadcasts: list[object] = []
    dispatch_dice_throw(
        payload=DiceThrowPayload(
            request_id="hm-wwn-req-1",
            throw_params=ThrowParams(
                velocity=(0.0, 5.0, -2.0),
                angular=(1.0, 1.0, 1.0),
                position=(0.5, 0.5),
            ),
            face=[20],
            beat_id=_STRIKE_BEAT,
        ),
        rolling_player_id="player-sael",
        character_name=attacker_name,
        character_stats={"STR": 12, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
        encounter=enc,
        pack=pack,
        genre_slug="heavy_metal",
        session_id="hm-wwn-session",
        round_number=1,
        room_broadcast=broadcasts.append,
        snapshot=snap,
    )

    # ── Assertion 1: HP ablated through the HP channel ────────────────────
    assert opponent_core.hp.current < hp_before, (
        f"committed_blow must ablate the opponent's HP on the real wwn pack; "
        f"before={hp_before} after={opponent_core.hp.current}"
    )

    # ── Assertion 2: state_patch.hp span fired (the lie detector) ─────────
    finished = [s.name for s in otel_capture.get_finished_spans()]
    assert SPAN_STATE_PATCH_HP in finished, (
        f"the wwn combat spine must emit a state_patch.hp span (GM-panel lie "
        f"detector); got spans: {finished}"
    )
```

- [ ] **Step 2: Run the test to verify it fails (RED)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/integration/test_wwn_heavy_metal_combat.py -v
```

Expected: FAIL at `Assertion 0` — `assert pack.rules.ruleset == "wwn"` fails because heavy_metal is still `native` (ruleset is `None`). (If content is absent it SKIPs — run on a checkout with `sidequest-content` present.)

---

## Task 2: Bind `heavy_metal/rules.yaml` to WWN (make Task 1 GREEN)

Rewrite the pack header, add the `wwn:` block (with the mandatory canonical→abbreviation `attribute_map`), remove the ADR-078 `edge_config` block, and convert the `combat` confrontation to `beat_selection` + `hp_depletion` with WWN damage annotations and a full `opponent_default_stats`.

**Files:**
- Modify: `sidequest-content/genre_packs/heavy_metal/rules.yaml`

- [ ] **Step 1: Add the ruleset header + magic_level/lethality**

At the top of the file, change `magic_level: medium` to `magic_level: high` and add the `ruleset`, `lethality`, and `wwn:` block. Insert this block immediately after the `ability_score_names` list (which already reads `STR/DEX/CON/INT/WIS/CHA` — leave it unchanged):

```yaml
lethality: high

ruleset: wwn
wwn:
  # Required by _validate_wwn: all six canonical WWN attribute keys, each
  # mapping to a declared ability_score_names entry. heavy_metal uses the
  # standard abbreviations, so the map is canonical -> abbreviation.
  attribute_map:
    STRENGTH: STR
    DEXTERITY: DEX
    CONSTITUTION: CON
    INTELLIGENCE: INT
    WISDOM: WIS
    CHARISMA: CHA
  system_strain:
    # max_source must be a canonical KEY of attribute_map (not "CON").
    max_source: CONSTITUTION
    rest_recovery_per_night: 1
    first_aid_cost: 1
  trauma:
    # Faithful WWN/EH baseline; lethality tuning is Keith's crunch call.
    default_trauma_target: 6
    mortal_injury_rounds: 6
    major_injury_save: physical
  magic:
    effort_base: 1
    killing_blow_divisor: 2
    day_reclaim_requires_comfort: true
    default_spell_save: mental
```

- [ ] **Step 2: Remove the `edge_config` block**

Delete the entire `edge_config:` block (the `# ── Edge / Composure ──` comment header through the `display_fields:` list, currently lines ~63–130). The combatant is now an ablative-HP WWN character; Edge/Composure (ADR-078) is removed engine-wide for this pack. Leave the `encounter_base_tension:` block that follows it intact.

- [ ] **Step 3: Convert the `combat` "Blade-work" confrontation to WWN**

Replace the existing `- type: combat` confrontation (currently `resolution_mode: opposed_check` with momentum dials and `opponent_default_stats: {STR: 12, DEX: 12, CON: 12}`) with this WWN version. Note: `resolution_mode: beat_selection` + `win_condition: hp_depletion`; the `player_metric`/`opponent_metric` are removed; the strike beats gain `damage_channel: strike` + `attack_bonus` + `combat_skill`; `committed_blow` gains a deterministic `damage_override`; `opponent_default_stats` carries all six abilities (≤ 10) plus the reserved seed keys `hp`/`armor_class`/`dexterity`.

```yaml
  - type: combat
    label: Blade-work
    category: combat
    # WWN personal combat: attack-vs-AC + hp_depletion on the ablative HpPool.
    # Trauma / Mortal Injury layer on via the wwn ruleset module.
    resolution_mode: beat_selection
    win_condition: hp_depletion
    opponent_default_stats:
      # ALL SIX ability scores must be authored so the WWN defender-save path
      # can resolve any save (Mental = best-of WIS/CHA, etc.). The SWN module
      # fails loud on a missing save attribute — an incomplete block KeyErrors.
      STR: 10
      DEX: 10
      CON: 10
      INT: 10
      WIS: 10
      CHA: 10
      # Reserved combat-seed keys (not ability scores): hp = HP pool;
      # armor_class = ascending AC the attack rolls against; dexterity =
      # initiative (1d8 + DEX). A hired blade: AC 12, HP 10.
      hp: 10
      armor_class: 12
      dexterity: 11
    beats:
      - id: strike
        label: Strike
        kind: strike
        base: 2
        stat_check: STR
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        effect: "Target takes damage this round"
        narrator_hint: "Describe the blow with specificity — which grip, which angle, what gave way. Heavy Metal combat is not choreography; it is plumbing."
      - id: brace
        label: Brace
        kind: brace
        base: 1
        stat_check: CON
        effect: "Reduce incoming damage this round"
        narrator_hint: "The character sets their weight, takes the impact, pays for it later."
      - id: committed_blow
        label: "Committed Blow"
        kind: strike
        base: 4
        stat_check: STR
        attack_bonus: 1
        combat_skill: 1
        damage_channel: strike
        damage_override: {dice: "2d6", bonus: 0}
        deltas:
          crit_fail:
            own: -3
        risk: "Overcommits — take a counter on failure"
        effect: "Target takes heavy damage"
        narrator_hint: "An all-in swing; the character is not planning a follow-up. Describe the violence as expensive — to the one making it, as well as the one receiving it."
      - id: break_contact
        label: "Break Contact"
        kind: push
        stat_check: DEX
        consequence: "Combat ends — the character withdraws, or the enemy lets them go"
        narrator_hint: "Disengagement is a mercy in Heavy Metal. Describe it as such."
    mood: combat
```

Leave the `negotiation` ("Cold Negotiation"), `chase` ("Pursuit"), `pact_working` ("Working the Rite"), and `debt_collection` ("The Collector at the Door") confrontations **unchanged** in this story — they are dial confrontations (`win_condition` defaults to `dial_threshold`) and survive the migrated load test. (`pact_working`/`debt_collection` retirement is Story 4.) Likewise leave `allowed_classes`, `allowed_races`, `banned_spells`, and `custom_rules` unchanged in Story 1 (Story 2/4 sweep).

- [ ] **Step 4: Run the wiring test to verify it passes (GREEN)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/integration/test_wwn_heavy_metal_combat.py -v
```

Expected: PASS — pack loads `ruleset: wwn`, opponent seats with HP 10 / AC 12, `committed_blow` ablates HP, `state_patch.hp` span fires.

If load fails with a pydantic `ValidationError` mentioning `attribute_map` or `max_source`, re-check Step 1 (every canonical key present; `max_source: CONSTITUTION` is a key of the map; every map value is in `ability_score_names`).

---

## Task 3: Migrate the collateral load test (GREEN)

Task 2 makes the `combat` confrontation metricless (`hp_depletion`), so `test_heavy_metal_pack_loads_with_dual_dial_schema` now NPEs on `cdef.player_metric.threshold`. Migrate it to the EH/space_opera shape: filter to `win_condition == "dial_threshold"` confrontations and assert at least one remains.

**Files:**
- Modify: `sidequest-server/tests/genre/test_pack_load.py:44-52`

- [ ] **Step 1: Confirm the test now fails**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/genre/test_pack_load.py::test_heavy_metal_pack_loads_with_dual_dial_schema -v
```

Expected: FAIL with `AttributeError`/`NoneType` on `player_metric` (the `combat` confrontation has no metric).

- [ ] **Step 2: Rewrite the test to the dial_threshold-filter shape**

Replace the existing `test_heavy_metal_pack_loads_with_dual_dial_schema` body (lines 44–52) with:

```python
@pytest.mark.skipif(not _has_real_content(), reason="sidequest-content not on disk")
def test_heavy_metal_pack_loads_with_dual_dial_schema():
    """heavy_metal is bound ruleset: wwn (Story 1): its ``combat`` ("Blade-work")
    moved off opposed_check dual-dial metrics to ``resolution_mode:
    beat_selection`` + ``win_condition: hp_depletion`` — combat resolves on HP
    reaching 0 and legitimately carries NO player_metric/opponent_metric,
    mirroring elemental_harmony / space_opera. The dual-dial invariant therefore
    only applies to its remaining dial confrontations (negotiation, chase,
    pact_working, debt_collection), which are ``win_condition: dial_threshold``
    (the model default) and still carry metrics. Filter on win_condition so the
    metricless hp_depletion combat is skipped rather than NPE-ing on
    ``player_metric.threshold``. At least one dial confrontation must remain so
    this assertion does not pass vacuously."""
    pack = load_pack("heavy_metal")
    assert pack.rules is not None
    dial_confrontations = [
        cdef
        for cdef in pack.rules.confrontations
        if (
            cdef.win_condition.value if hasattr(cdef.win_condition, "value") else cdef.win_condition
        )
        == "dial_threshold"
    ]
    assert dial_confrontations, (
        "heavy_metal must retain at least one dial_threshold confrontation "
        "(negotiation/chase) for this dual-dial assertion to be meaningful"
    )
    for cdef in dial_confrontations:
        assert cdef.player_metric.threshold > 0
        assert cdef.opponent_metric.threshold > 0
        for beat in cdef.beats:
            kind = beat.kind.value if hasattr(beat.kind, "value") else beat.kind
            assert kind in {"strike", "brace", "push", "angle"}
```

- [ ] **Step 3: Run the migrated test to verify it passes (GREEN)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/genre/test_pack_load.py::test_heavy_metal_pack_loads_with_dual_dial_schema -v
```

Expected: PASS.

---

## Task 4: Full-suite regression gate + lint + commit

heavy_metal is NOT in `COMBAT_PACKS`/`SHIPPED_PACKS` (`tests/genre/test_confrontation_calibration.py`), so no calibration list edits are needed — but the full suite must stay green (an `edge_config` consumer or a heavy_metal fixture elsewhere could surface).

**Files:** none new (verification + commit)

- [ ] **Step 1: Record the baseline failure list (pre-existing failures)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git stash list   # must be empty — never stash
# Baseline on develop is recorded separately; any failure here NOT about
# heavy_metal/wwn is pre-existing. Do NOT silence real regressions.
```

- [ ] **Step 2: Run the targeted suites**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest tests/integration/test_wwn_heavy_metal_combat.py tests/genre/test_pack_load.py tests/genre/test_confrontation_calibration.py -v
```

Expected: all PASS (heavy_metal wiring + migrated load test + calibration unaffected).

- [ ] **Step 3: Run the FULL server suite (catch edge_config / fixture fallout)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run pytest -q
```

Expected: no NEW failures vs the develop baseline. Any failure mentioning `heavy_metal`, `edge`, or `composure` is in-scope and must be fixed here (likely a test fixture that asserted heavy_metal's old Edge schema). Investigate before proceeding — do not run tests on a prior commit to prove a failure is pre-existing.

- [ ] **Step 4: Lint + format check**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
uv run ruff format --check tests/integration/test_wwn_heavy_metal_combat.py tests/genre/test_pack_load.py
uv run ruff check tests/integration/test_wwn_heavy_metal_combat.py tests/genre/test_pack_load.py
```

Expected: both clean. If `format --check` reports a diff, run `uv run ruff format` on the two files and re-run.

- [ ] **Step 5: Commit the content repo**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content
git add genre_packs/heavy_metal/rules.yaml
git commit -m "feat(heavy_metal): bind ruleset wwn — ablative-HP combat foundation

Story 1 of the heavy_metal -> WWN port. Add ruleset: wwn with the mandatory
canonical->abbreviation attribute_map, system_strain/trauma/magic config;
magic_level high; lethality high. Convert Blade-work combat to beat_selection
+ hp_depletion with WWN damage annotations and a full six-attribute
opponent_default_stats. Remove the ADR-078 edge_config block (Edge -> ablative
HP). Negotiation/chase/pact_working/debt_collection unchanged (Story 4 sweep).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Commit the server repo**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server
git add tests/integration/test_wwn_heavy_metal_combat.py tests/genre/test_pack_load.py
git commit -m "test(heavy_metal): e2e wwn combat wiring proof + dual-dial load migration

Story 1 of the heavy_metal -> WWN port. Add the mandated end-to-end wiring
proof: drives the real heavy_metal pack (ruleset: wwn) through the production
seating + dice seams and asserts the strike ablates opponent HP and the
state_patch.hp span fires. Migrate test_heavy_metal_pack_loads_with_dual_dial_schema
to the dial_threshold-filter shape (combat is now metricless hp_depletion),
mirroring elemental_harmony / space_opera.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage (§6 of the design):**
- §6.1 ruleset/wwn-block/attribute_map/magic_level/lethality → Task 2 Step 1 ✓
- §6.1 remove edge_config → Task 2 Step 2 ✓
- §6.1 convert combat to beat_selection/hp_depletion + opponent_default_stats (six + seed keys) → Task 2 Step 3 ✓
- §6.1 keep negotiation/chase, defer pact_working/debt_collection retirement → Task 2 Step 3 (explicit "leave unchanged") ✓
- §6.2 confirm load via `get_ruleset_module("wwn")` (fail-loud) → Task 1 Assertion 0 + Task 2 Step 4 (load round-trips) ✓
- §6.2 wiring-checklist VERIFY (spans `__init__`, downed seam already wwn-aware) → no edits needed (confirmed live via EH); the full-suite gate (Task 4 Step 3) catches any regression ✓
- §6.2 calibration migration → Task 3 (the only collateral test) ✓
- §6.3 OTEL / integration wiring test on a production turn path → Task 1 ✓

**Placeholder scan:** No TBD/TODO; all YAML and test code is complete. The `trauma` values are concrete (faithful EH baseline) with a flagged crunch-tuning note, not a placeholder.

**Type/name consistency:** `_STRIKE_BEAT = "committed_blow"` (Task 1) matches the beat id authored in Task 2 Step 3. `_OPPONENT_HP = 10` / `_OPPONENT_AC = 12` match `opponent_default_stats` `hp: 10` / `armor_class: 12`. The rng pin targets `sidequest.server.dispatch.dice.random.randint` — the module `dispatch_dice_throw` lives in (`sidequest/server/dispatch/dice.py`); the Dev confirms the `random` import site in RED→GREEN and adjusts the monkeypatch target if the damage roll fires from a different module.

**Risk flag for the implementer:** The wiring test assumes `dispatch_dice_throw` applies `damage_override` damage through the HP channel for a `beat_selection`/`hp_depletion` combat (proven for weapon damage in `test_space_opera_hp_e2e` Task 10). If `damage_override` resolves on a different seam, keep the three behavioral assertions (ruleset==wwn, HP ablated, `state_patch.hp` span) and route the strike through whichever production path the real pack uses — do not weaken the assertions to a synthetic fixture.
```
