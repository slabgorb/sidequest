# Class Mechanical Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the literal `"No abilities."` string on Lv 1 character sheets in `caverns_and_claudes` with a four-source Abilities tab — Class signature (data-driven), Class moves (chip row), Item-source (hook only), and Earned (existing/conditional) — and wire `taunt` as the Fighter's signature beat.

**Architecture:** Class signature abilities load from a new `abilities:` key on `ClassDef` (loader stamps `source=Class`), seeded onto `Character.abilities` during chargen. Protocol stops flattening abilities to `list[str]`; UI rebuilds `AbilitiesContent` to render the four sections with empty-state visibility rules. New `taunt` beat is added as a B/X-canonical strike+redirect with per-encounter state.

**Tech Stack:** Python 3 (FastAPI server, pydantic v2), TypeScript/React (Vite), pytest, Vitest. YAML genre packs loaded by `sidequest-server/sidequest/genre/loader.py`.

**Scope:** `caverns_and_claudes` only (per spec §3). Other genre packs adopt this shape lazily as they surface for playtest.

**Spec:** `docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md`. Read it first.

**Audience reminder (CLAUDE.md):** Sebastien reads the sheet before the prose. Keith is the 40-year B/X veteran. The string `"No abilities."` shipping at L1 is the bug this plan fixes.

---

## File Structure

### Files created

| Path | Responsibility |
|---|---|
| `docs/adr/ADR-095-class-mechanical-surface.md` | New ADR or amendment to ADR-021. Records "classes are a mechanical lane" decision. |
| `sidequest-server/sidequest/game/taunt.py` | Per-encounter taunt state model + decay logic. Single-responsibility, easy to grep. |
| `sidequest-server/tests/genre/test_class_abilities_loader.py` | Genre loader strictness for `abilities:` key. |
| `sidequest-server/tests/game/test_chargen_class_abilities.py` | Chargen seeds class signature abilities with `source=Class`. |
| `sidequest-server/tests/game/test_taunt.py` | Taunt activation, decay, OTEL emission. |
| `sidequest-server/tests/game/test_taunt_targeting.py` | Targeting bias + damage redirect under taunt. |
| `sidequest-server/tests/protocol/test_character_sheet_abilities.py` | Protocol contract — `abilities: list[AbilityDefinition]` and `class_moves` filtering. |
| `sidequest-server/tests/integration/test_class_signature_wiring.py` | Mandatory CLAUDE.md wiring test — full chargen → state mirror → assert. |
| `sidequest-ui/src/components/__tests__/AbilitiesContent.test.tsx` | Four-section render, empty-state visibility, regression guard. |

### Files modified

| Path | Changes |
|---|---|
| `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` | Add `taunt` beat to confrontations. |
| `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` | Add `taunt` to Fighter `encounter_beat_choices`; add `abilities:` key to Cleric/Fighter/Thief. |
| `sidequest-server/sidequest/genre/models/character.py` | New `ClassAbilityDef` model; new `abilities` field on `ClassDef`. |
| `sidequest-server/sidequest/genre/loader.py` | Validate well-formed `abilities:` (loud-fail). |
| `sidequest-server/sidequest/game/builder.py` | New `_seed_class_abilities` + stub `_seed_item_abilities`; OTEL emission. |
| `sidequest-server/sidequest/game/beat_kinds.py` and/or beat resolution path | Taunt resolution wiring. |
| `sidequest-server/sidequest/game/encounter.py` (or session.py — task pins exact file) | Targeting bias, damage redirect, decay, OTEL. |
| `sidequest-server/sidequest/protocol/models.py` | `CharacterSheetDetails.abilities: list[AbilityDefinition]`; new `class_moves: list[str]` field. |
| `sidequest-server/sidequest/server/views.py` | Build full `AbilityDefinition`s; pre-filter `class_moves`. |
| `sidequest-server/sidequest/telemetry/spans.py` | New OTEL span constants. |
| `sidequest-ui/src/components/CharacterPanel.tsx` | Replace `AbilitiesContent` with four-section component; remove letter-square chip rendering and the `"No abilities."` string. |
| `sidequest-ui/src/types/...` (find via grep) | Update client-side type for `abilities` from `string[]` to `AbilityDefinition[]`. |

### Files NOT touched

- `sidequest-server/sidequest/game/character.py` — `AbilityDefinition` is reused as-is (per spec §5.3).
- `sidequest-server/sidequest/game/ability.py` — `AbilitySource` enum unchanged.
- Affinity / progression rendering — out of scope; spec §4 lists "Earned" as "Already implemented" but UI grep returns no `affinity`/`Affinity` matches. The plan treats the Earned section as **conditional**: render only if `character.affinities` is non-empty. At L1 it is empty everywhere, so the section header is suppressed via the same visibility rule as Item-source. **No new affinity rendering code lands in this story.**

---

## Sequencing & Dependencies

The plan runs as 15 tasks across three phases:

- **Phase A: Engine + Content (Tasks 1–8)** — must complete before chargen wiring.
- **Phase B: Chargen + Protocol (Tasks 9–13)** — depends on A. Each landable independently.
- **Phase C: UI + Wiring + ADR (Tasks 14–15)** — depends on B; integration test is the merge gate.

Tasks within a phase are mostly independent and can land in any order, but committing in numeric order is the safest path for an engineer with no context.

---

## Task 1: Add `taunt` beat to genre data

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` (add a beat after `cleave` ~line 134)
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml:15-22` (Fighter `encounter_beat_choices`)
- Test: `sidequest-server/tests/genre/test_class_beats_caverns.py` (existing; we add a case there if present, or create a new tiny test in `tests/genre/test_class_abilities_loader.py`)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/genre/test_class_abilities_loader.py
"""Story 2026-05-10 — class mechanical surface.

Loader-level checks for the new `abilities` key on ClassDef and the
`taunt` beat for Fighter.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.genre.loader import load_genre_pack


GENRE_ROOT = Path(__file__).parents[2] / "../sidequest-content/genre_packs"


def test_caverns_and_claudes_loads_with_taunt_beat():
    pack = load_genre_pack(GENRE_ROOT.resolve() / "caverns_and_claudes")
    fighter = next(c for c in pack.classes if c.id == "fighter")
    assert "taunt" in fighter.encounter_beat_choices, (
        "Fighter must declare 'taunt' in encounter_beat_choices"
    )
    all_beat_ids = {b.id for cd in pack.rules.confrontations for b in cd.beats}
    assert "taunt" in all_beat_ids, "rules.yaml must declare a 'taunt' beat"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/genre/test_class_abilities_loader.py::test_caverns_and_claudes_loads_with_taunt_beat -v
```
Expected: FAIL — `'taunt' not in encounter_beat_choices` OR loader raises `PackError` because Fighter doesn't reference taunt yet (depending on whether you add the class change first or the rules change first).

- [ ] **Step 3: Add `taunt` beat to rules.yaml**

In `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml`, after the `cleave` beat (~line 141), insert:

```yaml
      - id: taunt
        label: Taunt
        kind: strike
        base: 2
        stat_check: CHA
        class_filter: [Fighter]
        effect: "Pull the next blow onto yourself — eat it on Edge so the squishies survive"
        risk: "Hit lands harder when you've made yourself the target"
        narrator_hint: "A half-step forward, eye contact, an insult that lands in the gut. They have to swing at you now."
```

Notes for the engineer:
- `kind: strike` is the closest existing beat kind (taunt advances your own narrative weight by absorbing). The targeting-bias and damage-redirect logic happens in Python (Tasks 3–4), not as a beat-data field.
- `base: 2` is intentionally modest — the value of taunt is in the redirect, not the dial advance.
- `class_filter: [Fighter]` — only Fighters declare taunt. The loader rejects any class that doesn't list `taunt` in `encounter_beat_choices` from selecting it.

- [ ] **Step 4: Add `taunt` to Fighter `encounter_beat_choices`**

In `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml:15-22`, append `taunt`:

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
    - taunt        # NEW — class signature, redirect-on-hit
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py::test_caverns_and_claudes_loads_with_taunt_beat -v
```
Expected: PASS

- [ ] **Step 6: Run full server-test to confirm nothing else broke**

```bash
uv run pytest -v
```
Expected: PASS (or pre-existing unrelated failures only — note them; do not fix them in this task).

- [ ] **Step 7: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/rules.yaml \
        sidequest-content/genre_packs/caverns_and_claudes/classes.yaml \
        sidequest-server/tests/genre/test_class_abilities_loader.py
git commit -m "feat(cnc): add taunt beat to Fighter encounter beats"
```

---

## Task 2: Engine — taunt encounter state + activation OTEL

**Files:**
- Create: `sidequest-server/sidequest/game/taunt.py`
- Modify: `sidequest-server/sidequest/telemetry/spans.py` (add span constants)
- Test: `sidequest-server/tests/game/test_taunt.py`

- [ ] **Step 1: Add OTEL span constants**

In `sidequest-server/sidequest/telemetry/spans.py`, add:

```python
SPAN_ENCOUNTER_TAUNT_ACTIVATED = "encounter.taunt.activated"
SPAN_ENCOUNTER_TAUNT_EXPIRED = "encounter.taunt.expired"
SPAN_CHARGEN_CLASS_ABILITIES_SEEDED = "chargen.class_abilities.seeded"
```

- [ ] **Step 2: Write the failing test**

```python
# sidequest-server/tests/game/test_taunt.py
"""Story 2026-05-10 — taunt mechanic.

Activation, decay, OTEL emission. Targeting + redirect tested in
test_taunt_targeting.py.
"""
from __future__ import annotations

import pytest

from sidequest.game.taunt import TauntState


def test_taunt_state_starts_inactive():
    state = TauntState()
    assert state.active_actor is None
    assert state.remaining_rounds == 0
    assert state.redirects_this_round == 0


def test_taunt_activate_records_actor_and_round():
    state = TauntState()
    state.activate(actor_id="fighter-1")
    assert state.active_actor == "fighter-1"
    assert state.remaining_rounds == 1
    assert state.redirects_this_round == 0


def test_taunt_decay_at_end_of_round_clears_actor():
    state = TauntState()
    state.activate(actor_id="fighter-1")
    state.end_of_round_decay()
    assert state.active_actor is None
    assert state.remaining_rounds == 0


def test_taunt_redirect_count_resets_at_end_of_round():
    state = TauntState()
    state.activate(actor_id="fighter-1")
    state.try_consume_redirect()
    assert state.redirects_this_round == 1
    # Re-activate next round.
    state.end_of_round_decay()
    state.activate(actor_id="fighter-1")
    assert state.redirects_this_round == 0


def test_taunt_redirect_capped_at_one_per_round():
    state = TauntState()
    state.activate(actor_id="fighter-1")
    assert state.try_consume_redirect() is True
    assert state.try_consume_redirect() is False  # second attempt rejected
    assert state.redirects_this_round == 1
```

- [ ] **Step 3: Run test to verify it fails**

```bash
uv run pytest tests/game/test_taunt.py -v
```
Expected: FAIL — `ModuleNotFoundError: sidequest.game.taunt`.

- [ ] **Step 4: Create `taunt.py`**

```python
# sidequest-server/sidequest/game/taunt.py
"""Per-encounter taunt state.

Tracks which actor is currently 'taunting' (forcing enemy attention onto
themselves), how many rounds remain on the effect, and how many damage
redirects have already fired this round (capped at 1 per spec §8).

Spec: docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md §8.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TauntState:
    """Mutable per-encounter taunt tracker."""

    active_actor: Optional[str] = None
    remaining_rounds: int = 0
    redirects_this_round: int = 0

    def activate(self, actor_id: str) -> None:
        """Start a 1-round taunt. Resets redirect counter."""
        self.active_actor = actor_id
        self.remaining_rounds = 1
        self.redirects_this_round = 0

    def end_of_round_decay(self) -> None:
        """Decrement; at 0, clear the actor and redirect counter."""
        if self.remaining_rounds > 0:
            self.remaining_rounds -= 1
        if self.remaining_rounds == 0:
            self.active_actor = None
            self.redirects_this_round = 0

    def try_consume_redirect(self) -> bool:
        """Returns True if a redirect is available this round and consumes it.
        Returns False if cap is reached or no taunt is active."""
        if self.active_actor is None:
            return False
        if self.redirects_this_round >= 1:
            return False
        self.redirects_this_round += 1
        return True
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/game/test_taunt.py -v
```
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/taunt.py \
        sidequest-server/sidequest/telemetry/spans.py \
        sidequest-server/tests/game/test_taunt.py
git commit -m "feat(engine): TauntState — activate/decay/redirect-cap primitives"
```

---

## Task 3: Engine — taunt activation hook + OTEL `encounter.taunt.activated`

**Files:**
- Modify: `sidequest-server/sidequest/game/encounter.py` (add taunt state to `EncounterState`; the engineer should grep for the existing per-encounter mutable container — likely a pydantic model or dataclass)
- Modify: `sidequest-server/sidequest/game/beat_kinds.py` or whichever module dispatches beat resolution
- Test: extend `sidequest-server/tests/game/test_taunt.py`

**Implementation note for the engineer:** before coding, run

```bash
grep -rn "class EncounterState\|@dataclass.*Encounter\|class.*Encounter.*BaseModel" sidequest-server/sidequest/game/ --include="*.py"
```

to find the encounter container. The taunt state lives on it as a `taunt: TauntState = field(default_factory=TauntState)` (dataclass) or `Field(default_factory=TauntState)` (pydantic).

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/game/test_taunt.py`:

```python
def test_taunt_beat_resolution_activates_state(taunt_test_encounter):
    """Resolving a 'taunt' beat for the Fighter sets active_actor and remaining_rounds."""
    enc = taunt_test_encounter  # fixture — Fighter PC + 2 enemies, fresh encounter
    fighter_id = enc.fighter_id

    enc.resolve_beat(actor_id=fighter_id, beat_id="taunt", outcome="success")

    assert enc.state.taunt.active_actor == fighter_id
    assert enc.state.taunt.remaining_rounds == 1


def test_taunt_activation_emits_otel(taunt_test_encounter, otel_capture):
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id

    enc.resolve_beat(actor_id=fighter_id, beat_id="taunt", outcome="success")

    events = otel_capture.events_named("encounter.taunt.activated")
    assert len(events) == 1
    assert events[0].attrs["actor_id"] == fighter_id
    assert events[0].attrs["round"] == enc.state.current_round
```

The fixture `taunt_test_encounter` and the `otel_capture` fixture should be added to `sidequest-server/tests/game/conftest.py`. The engineer pins their exact shape against the existing encounter test infrastructure (grep `tests/game/conftest.py` and `tests/game/test_encounter*.py` for the established pattern).

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_taunt.py::test_taunt_beat_resolution_activates_state tests/game/test_taunt.py::test_taunt_activation_emits_otel -v
```
Expected: FAIL — fixture missing or `EncounterState.taunt` attribute missing.

- [ ] **Step 3: Add `taunt` to encounter state**

Wherever the encounter container is defined (likely `sidequest-server/sidequest/game/encounter.py` — confirm via grep), add:

```python
from sidequest.game.taunt import TauntState

# inside the EncounterState class:
    taunt: TauntState = field(default_factory=TauntState)  # dataclass
    # OR for pydantic BaseModel:
    # taunt: TauntState = Field(default_factory=TauntState)
```

If `TauntState` needs to be a pydantic model for the existing serializer to round-trip it, convert from `@dataclass` to `BaseModel` — keep the same field names and method signatures. Tests from Task 2 will still pass.

- [ ] **Step 4: Add taunt activation in beat resolution**

In the beat-resolution path (find via `grep -rn "resolve_beat\|_apply_beat\|def.*beat.*resolve" sidequest-server/sidequest/game/`), after a `taunt` beat resolves with non-failure outcome:

```python
from sidequest.telemetry.spans import SPAN_ENCOUNTER_TAUNT_ACTIVATED

# Inside beat-resolution, after deltas are applied, before next beat:
if beat.id == "taunt" and outcome.is_success_or_better():  # adapt to the project's RollOutcome API
    encounter_state.taunt.activate(actor_id=actor_id)
    span.add_event(
        SPAN_ENCOUNTER_TAUNT_ACTIVATED,
        {
            "actor_id": actor_id,
            "round": encounter_state.current_round,
        },
    )
```

The engineer pins `outcome.is_success_or_better()` against the project's `RollOutcome` API (found in `sidequest-server/sidequest/protocol/dice.py`). If the project doesn't have a helper, use `outcome != RollOutcome.crit_fail and outcome != RollOutcome.fail`.

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/game/test_taunt.py -v
```
Expected: PASS (7 tests).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/encounter.py \
        sidequest-server/sidequest/game/beat_kinds.py \
        sidequest-server/sidequest/game/taunt.py \
        sidequest-server/tests/game/conftest.py \
        sidequest-server/tests/game/test_taunt.py
git commit -m "feat(engine): wire taunt beat resolution + OTEL activation event"
```

---

## Task 4: Engine — targeting bias under taunt

**Files:**
- Modify: enemy beat-selection / targeting logic (find via `grep -rn "select_target\|enemy.*pick\|adversary.*beat" sidequest-server/sidequest/game/`)
- Test: `sidequest-server/tests/game/test_taunt_targeting.py`

The spec §8 says "prefer that actor as target. Bias the selection, do not force it." For L1 ship, full bias is acceptable.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/game/test_taunt_targeting.py
"""Targeting bias under taunt — enemies prefer the taunting actor."""
from __future__ import annotations

import random
import pytest

from sidequest.game.taunt import TauntState


def test_enemy_targets_taunter_when_taunt_active(taunt_test_encounter):
    """With taunt active, the next 10 enemy beats target the Fighter."""
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id
    cleric_id = enc.cleric_id  # ally — must NOT be targeted while taunt is up

    enc.state.taunt.activate(actor_id=fighter_id)

    rng = random.Random(42)
    targets = []
    for _ in range(10):
        # adapt to the project's enemy-targeting helper:
        target = enc.select_enemy_target(rng=rng, allies=[fighter_id, cleric_id])
        targets.append(target)

    assert all(t == fighter_id for t in targets), (
        f"Expected all 10 enemy targets = {fighter_id}, got {targets}"
    )


def test_enemy_targeting_unbiased_without_taunt(taunt_test_encounter):
    """With no taunt, enemy targeting hits both allies across many trials."""
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id
    cleric_id = enc.cleric_id

    rng = random.Random(42)
    targets = [
        enc.select_enemy_target(rng=rng, allies=[fighter_id, cleric_id])
        for _ in range(50)
    ]

    assert fighter_id in targets and cleric_id in targets, (
        "Without taunt, both allies should appear as targets"
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_taunt_targeting.py -v
```
Expected: FAIL — taunt has no influence on targeting yet.

- [ ] **Step 3: Implement targeting bias**

In the enemy-targeting helper (engineer pins exact location via grep), insert at the top:

```python
# Spec: 2026-05-10 class-mechanical-surface §8 — taunt targeting bias.
if encounter_state.taunt.active_actor and encounter_state.taunt.active_actor in allies:
    return encounter_state.taunt.active_actor
```

If the targeting helper has no parameter list shape that matches the test, refactor it to take `allies: list[str]` and `rng: Random` and `encounter_state: EncounterState` — the test pins the contract.

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/game/test_taunt_targeting.py -v
```
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/encounter.py \
        sidequest-server/tests/game/test_taunt_targeting.py
git commit -m "feat(engine): taunt biases enemy targeting onto the taunter"
```

---

## Task 5: Engine — damage redirect (capped at 1/round)

**Files:**
- Modify: damage routing (find via `grep -rn "apply_damage\|damage_to\|def.*damage" sidequest-server/sidequest/game/`)
- Test: extend `sidequest-server/tests/game/test_taunt_targeting.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/game/test_taunt_targeting.py`:

```python
def test_damage_to_ally_reroutes_to_taunter(taunt_test_encounter):
    """While taunt is active, damage destined for an ally reroutes to the Fighter."""
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id
    cleric_id = enc.cleric_id

    enc.state.taunt.activate(actor_id=fighter_id)
    fighter_edge_before = enc.character_by_id(fighter_id).core.edge.current
    cleric_edge_before = enc.character_by_id(cleric_id).core.edge.current

    enc.apply_damage(target_id=cleric_id, amount=3, source="enemy-1")

    # Fighter took the hit, Cleric is untouched.
    assert enc.character_by_id(cleric_id).core.edge.current == cleric_edge_before
    assert enc.character_by_id(fighter_id).core.edge.current == fighter_edge_before - 3


def test_damage_redirect_capped_at_one_per_round(taunt_test_encounter):
    """Two enemies in one round → only one redirect; second hit lands on the original ally."""
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id
    cleric_id = enc.cleric_id

    enc.state.taunt.activate(actor_id=fighter_id)

    enc.apply_damage(target_id=cleric_id, amount=2, source="enemy-1")  # redirect → fighter
    enc.apply_damage(target_id=cleric_id, amount=2, source="enemy-2")  # cap reached → cleric

    assert enc.character_by_id(fighter_id).core.edge.current == enc.fighter_edge_baseline - 2
    assert enc.character_by_id(cleric_id).core.edge.current == enc.cleric_edge_baseline - 2


def test_damage_redirect_resets_each_round(taunt_test_encounter):
    """After end-of-round decay + re-activation, a fresh redirect is available."""
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id
    cleric_id = enc.cleric_id

    enc.state.taunt.activate(actor_id=fighter_id)
    enc.apply_damage(target_id=cleric_id, amount=1, source="enemy-1")  # consumed
    enc.apply_damage(target_id=cleric_id, amount=1, source="enemy-2")  # capped

    enc.state.taunt.end_of_round_decay()
    enc.state.taunt.activate(actor_id=fighter_id)  # next round, taunt again

    enc.apply_damage(target_id=cleric_id, amount=1, source="enemy-3")  # redirect available again

    fighter_edge = enc.character_by_id(fighter_id).core.edge.current
    cleric_edge = enc.character_by_id(cleric_id).core.edge.current
    assert fighter_edge == enc.fighter_edge_baseline - 2  # round 1 redirect + round 2 redirect
    assert cleric_edge == enc.cleric_edge_baseline - 1   # only the round-1 capped hit
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_taunt_targeting.py -v
```
Expected: FAIL — redirect logic absent.

- [ ] **Step 3: Implement damage redirect**

In the damage application path (engineer pins exact location), at the top of the function:

```python
# Spec: 2026-05-10 class-mechanical-surface §8 — taunt damage redirect (cap 1/round).
if (
    encounter_state.taunt.active_actor
    and target_id != encounter_state.taunt.active_actor
    and target_id in self.ally_ids()  # adapt to project's ally check
):
    if encounter_state.taunt.try_consume_redirect():
        target_id = encounter_state.taunt.active_actor
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/game/test_taunt_targeting.py -v
```
Expected: PASS (5 tests total in file).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/encounter.py \
        sidequest-server/tests/game/test_taunt_targeting.py
git commit -m "feat(engine): taunt damage redirect with 1/round cap"
```

---

## Task 6: Engine — taunt decay + expiration OTEL

**Files:**
- Modify: end-of-round hook (find via `grep -rn "end_of_round\|advance_round\|def.*round.*tick" sidequest-server/sidequest/game/`)
- Test: extend `sidequest-server/tests/game/test_taunt.py`

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/game/test_taunt.py`:

```python
def test_taunt_expires_at_end_of_round_emits_otel(taunt_test_encounter, otel_capture):
    enc = taunt_test_encounter
    fighter_id = enc.fighter_id

    enc.state.taunt.activate(actor_id=fighter_id)
    enc.advance_round()  # end-of-round hook should fire

    events = otel_capture.events_named("encounter.taunt.expired")
    assert len(events) == 1
    assert events[0].attrs["actor_id"] == fighter_id
    assert events[0].attrs["round"] == enc.state.current_round - 1  # the round that just ended
    assert enc.state.taunt.active_actor is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_taunt.py::test_taunt_expires_at_end_of_round_emits_otel -v
```
Expected: FAIL — decay not wired into round advance.

- [ ] **Step 3: Wire decay into round advance**

In the round-advance / end-of-round hook:

```python
from sidequest.telemetry.spans import SPAN_ENCOUNTER_TAUNT_EXPIRED

# Before advancing the round counter:
prior_taunter = encounter_state.taunt.active_actor
prior_round = encounter_state.current_round
encounter_state.taunt.end_of_round_decay()
if prior_taunter and encounter_state.taunt.active_actor is None:
    span.add_event(
        SPAN_ENCOUNTER_TAUNT_EXPIRED,
        {"actor_id": prior_taunter, "round": prior_round},
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/game/test_taunt.py -v
```
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/encounter.py \
        sidequest-server/tests/game/test_taunt.py
git commit -m "feat(engine): taunt decay + OTEL expiration event"
```

---

## Task 7: Genre model — `ClassAbilityDef` + `ClassDef.abilities`

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/character.py:118` (add field on `ClassDef`)
- Test: `sidequest-server/tests/genre/test_class_abilities_loader.py` (extend)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_class_abilities_loader.py`:

```python
def test_class_def_parses_abilities_key():
    """A class with abilities: yields a list of ClassAbilityDef entries."""
    from sidequest.genre.models.character import ClassAbilityDef, ClassDef

    cd = ClassDef.model_validate(
        {
            "id": "cleric",
            "display_name": "Cleric",
            "rpg_role": "healer",
            "jungian_default": "caregiver",
            "prime_requisite": "WIS",
            "minimum_score": 9,
            "kit_table": "cleric_kit",
            "encounter_beat_choices": ["attack", "defend", "flee", "turn_undead"],
            "abilities": [
                {
                    "name": "Turn Undead",
                    "genre_description": "He raises the symbol; the unliving recoil.",
                    "mechanical_effect": "2d6 vs HD; loud; fails on intelligent unliving.",
                    "involuntary": False,
                }
            ],
        }
    )
    assert len(cd.abilities) == 1
    assert isinstance(cd.abilities[0], ClassAbilityDef)
    assert cd.abilities[0].name == "Turn Undead"
    assert cd.abilities[0].involuntary is False


def test_class_def_default_empty_abilities():
    """Absent abilities: → empty list. Mage path."""
    from sidequest.genre.models.character import ClassDef

    cd = ClassDef.model_validate(
        {
            "id": "mage",
            "display_name": "Mage",
            "rpg_role": "control",
            "jungian_default": "magician",
            "prime_requisite": "INT",
            "minimum_score": 9,
            "kit_table": "mage_kit",
            "encounter_beat_choices": ["attack", "defend", "flee", "cast_spell"],
        }
    )
    assert cd.abilities == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py::test_class_def_parses_abilities_key tests/genre/test_class_abilities_loader.py::test_class_def_default_empty_abilities -v
```
Expected: FAIL — `ImportError: cannot import name 'ClassAbilityDef'`.

- [ ] **Step 3: Add `ClassAbilityDef` and field**

In `sidequest-server/sidequest/genre/models/character.py`, before `class ClassDef`, add:

```python
class ClassAbilityDef(BaseModel):
    """Class-source signature ability authored in classes.yaml.

    Mirrors AbilityDefinition (sidequest.game.character) minus the
    `source` field. Loader stamps source=AbilitySource.Class on each
    entry during chargen seeding so authors don't have to type a
    discriminator they never vary.

    Spec: docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md §5.2.
    """

    model_config = {"extra": "forbid"}

    name: str
    genre_description: str
    mechanical_effect: str
    involuntary: bool = False
```

Then add to `ClassDef` (line 118+, after `encounter_beat_choices`):

```python
    abilities: list[ClassAbilityDef] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py -v
```
Expected: PASS (3 tests in file now).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/genre/models/character.py \
        sidequest-server/tests/genre/test_class_abilities_loader.py
git commit -m "feat(genre): ClassAbilityDef model + ClassDef.abilities field"
```

---

## Task 8: Genre loader — content authoring (Turn Undead, Taunt, Backstab)

**Files:**
- Modify: `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml` (Cleric/Fighter/Thief blocks)
- Test: extend `sidequest-server/tests/genre/test_class_abilities_loader.py`

The prose below matches C&C voice (illuminated-manuscript, B/X-flavored, second-person sense-memory). It is sufficient for shipping; if you want a writer-agent polish pass, dispatch *after* Task 8 is committed and ship the polish as a follow-up commit. Do not block this task on prose perfection.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_class_abilities_loader.py`:

```python
def test_caverns_classes_have_signature_abilities():
    pack = load_genre_pack(GENRE_ROOT.resolve() / "caverns_and_claudes")

    by_id = {c.id: c for c in pack.classes}
    cleric, fighter, thief, mage = by_id["cleric"], by_id["fighter"], by_id["thief"], by_id["mage"]

    assert len(cleric.abilities) == 1 and cleric.abilities[0].name == "Turn Undead"
    assert len(fighter.abilities) == 1 and fighter.abilities[0].name == "Taunt"
    assert len(thief.abilities) == 1 and thief.abilities[0].name == "Backstab"
    assert mage.abilities == []  # signature filled by magic plugin

    # Prose is non-empty (no {writer agent fills} placeholder).
    for c in (cleric, fighter, thief):
        gd = c.abilities[0].genre_description
        assert gd and "{writer agent" not in gd, (
            f"{c.id} genre_description still has placeholder text"
        )
        assert c.abilities[0].mechanical_effect, f"{c.id} mechanical_effect blank"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py::test_caverns_classes_have_signature_abilities -v
```
Expected: FAIL — Cleric/Fighter/Thief have no `abilities:` key yet.

- [ ] **Step 3: Author content in classes.yaml**

In `sidequest-content/genre_packs/caverns_and_claudes/classes.yaml`:

For the Cleric block (after `saving_throws:`, ~line 121):

```yaml
  abilities:
    - name: "Turn Undead"
      genre_description: >-
        He lifts the holy symbol — wood worn pale where the thumb has rested
        for a thousand prayers. The unliving feel it before they see it: a
        line drawn between the world that is theirs and the world that is
        no longer. Some break. Some do not. The intelligent ones already
        chose, long ago, and the symbol means nothing to them.
      mechanical_effect: >-
        2d6 vs target HD; loud (raises Keeper awareness); auto-fails on
        intelligent unliving who have made their alignment.
      involuntary: false
```

For the Fighter block (after `saving_throws:`, ~line 32):

```yaml
  abilities:
    - name: "Taunt"
      genre_description: >-
        A half-step forward — close enough that the swing has to come at
        you. An insult landing somewhere it costs to ignore. The squishies
        are behind you now, and the thing in front has lost the option of
        choosing prettier prey. You are the meal. Eat it on the chin.
      mechanical_effect: >-
        Forces enemy attention onto the Fighter for the round; one ally
        attack per round reroutes to the Fighter; expires at end of round.
      involuntary: false
```

For the Thief block (after `saving_throws:`, ~line 145):

```yaml
  abilities:
    - name: "Backstab"
      genre_description: >-
        She picks the moment the way a counterman picks the right coin
        from a handful — by feel, without looking. The gap between rib
        and rib. The gap between one breath and the next. Quiet, brief,
        complete. The kind of removal you wouldn't notice happened to
        someone else.
      mechanical_effect: >-
        Requires unaware target (sneak / feint setup or surprise round);
        damage multiplier per Edge math; one-shot ends combat against
        single weak unaware targets.
      involuntary: false
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py -v
```
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/classes.yaml \
        sidequest-server/tests/genre/test_class_abilities_loader.py
git commit -m "content(cnc): Turn Undead / Taunt / Backstab signature abilities"
```

---

## Task 9: Genre loader — strict failure on malformed `abilities:`

**Files:**
- Modify: `sidequest-server/sidequest/genre/loader.py` (add a validator near the existing `_validate_class_filter_refs`, ~line 512)
- Test: extend `sidequest-server/tests/genre/test_class_abilities_loader.py`

**Note:** pydantic's `extra="forbid"` on `ClassAbilityDef` already rejects unknown keys. This task adds an explicit, friendly error message — and a check that `ClassAbilityDef.name`, `genre_description`, and `mechanical_effect` are all non-blank.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/genre/test_class_abilities_loader.py`:

```python
def test_blank_genre_description_raises():
    """Empty genre_description fails loud, not silent."""
    from sidequest.genre.error import PackError
    from sidequest.genre.models.character import ClassAbilityDef, ClassDef

    with pytest.raises((PackError, ValueError, Exception)) as exc:
        ClassDef.model_validate(
            {
                "id": "cleric",
                "display_name": "Cleric",
                "rpg_role": "healer",
                "jungian_default": "caregiver",
                "prime_requisite": "WIS",
                "minimum_score": 9,
                "kit_table": "cleric_kit",
                "encounter_beat_choices": ["attack"],
                "abilities": [
                    {
                        "name": "Turn Undead",
                        "genre_description": "",   # blank — must fail
                        "mechanical_effect": "2d6 vs HD",
                    }
                ],
            }
        )
    # Error message should mention which field is blank.
    assert "genre_description" in str(exc.value).lower() or "blank" in str(exc.value).lower()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py::test_blank_genre_description_raises -v
```
Expected: FAIL — pydantic accepts blank strings by default.

- [ ] **Step 3: Add field validators to `ClassAbilityDef`**

In `sidequest-server/sidequest/genre/models/character.py`, on `ClassAbilityDef`:

```python
from pydantic import BaseModel, Field, field_validator


class ClassAbilityDef(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    genre_description: str
    mechanical_effect: str
    involuntary: bool = False

    @field_validator("name", "genre_description", "mechanical_effect")
    @classmethod
    def _non_blank(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(
                f"ClassAbilityDef field {info.field_name!r} must be non-blank"
            )
        return v
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/genre/test_class_abilities_loader.py -v
```
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/genre/models/character.py \
        sidequest-server/tests/genre/test_class_abilities_loader.py
git commit -m "feat(genre): loud-fail on blank ClassAbilityDef fields"
```

---

## Task 10: Chargen — `_seed_class_abilities` + OTEL

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py` (around line 1959, after the existing `chargen.abilities_resolved` event)
- Test: `sidequest-server/tests/game/test_chargen_class_abilities.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/game/test_chargen_class_abilities.py
"""Story 2026-05-10 — _seed_class_abilities populates Class-source abilities."""
from __future__ import annotations

import pytest

from sidequest.game.ability import AbilitySource
from sidequest.game.builder import _seed_class_abilities
from sidequest.game.character import AbilityDefinition


def _make_class_def(class_id: str, ability_name: str | None):
    from sidequest.genre.models.character import ClassAbilityDef, ClassDef

    abilities = []
    if ability_name:
        abilities = [
            ClassAbilityDef(
                name=ability_name,
                genre_description=f"{ability_name} prose.",
                mechanical_effect=f"{ability_name} effect.",
                involuntary=False,
            )
        ]
    return ClassDef(
        id=class_id,
        display_name=class_id.capitalize(),
        rpg_role="x",
        jungian_default="x",
        prime_requisite="STR",
        minimum_score=9,
        kit_table=f"{class_id}_kit",
        encounter_beat_choices=["attack", "defend", "flee"],
        abilities=abilities,
    )


def test_seed_class_abilities_appends_one_with_class_source():
    abilities: list[AbilityDefinition] = []
    cd = _make_class_def("cleric", "Turn Undead")

    _seed_class_abilities(abilities, cd)

    assert len(abilities) == 1
    a = abilities[0]
    assert a.name == "Turn Undead"
    assert a.source == AbilitySource.Class
    assert a.genre_description == "Turn Undead prose."
    assert a.mechanical_effect == "Turn Undead effect."
    assert a.involuntary is False


def test_seed_class_abilities_noop_for_mage():
    abilities: list[AbilityDefinition] = []
    cd = _make_class_def("mage", None)

    _seed_class_abilities(abilities, cd)

    assert abilities == []


def test_seed_class_abilities_preserves_prior_entries():
    """The seam appends; it must not clobber scene-driven hints already in the list."""
    prior = AbilityDefinition(
        name="Prior",
        genre_description="x",
        mechanical_effect="y",
        involuntary=False,
        source=AbilitySource.Class,
    )
    abilities = [prior]
    cd = _make_class_def("cleric", "Turn Undead")

    _seed_class_abilities(abilities, cd)

    assert len(abilities) == 2
    assert abilities[0] is prior
    assert abilities[1].name == "Turn Undead"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_chargen_class_abilities.py -v
```
Expected: FAIL — `ImportError: cannot import name '_seed_class_abilities'`.

- [ ] **Step 3: Add the seam**

In `sidequest-server/sidequest/game/builder.py`, near the top (after imports), add:

```python
from sidequest.genre.models.character import ClassAbilityDef, ClassDef


def _seed_class_abilities(
    abilities: list[AbilityDefinition], class_def: ClassDef
) -> None:
    """Append Class-source signature abilities from class_def.abilities.

    Loader stamps source=AbilitySource.Class on each entry; authors do not
    type the discriminator. Empty class_def.abilities (e.g., Mage —
    signature lives in magic plugin) is a no-op.

    Spec: docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md §6.1.
    """
    for ca in class_def.abilities:
        abilities.append(
            AbilityDefinition(
                name=ca.name,
                genre_description=ca.genre_description,
                mechanical_effect=ca.mechanical_effect,
                involuntary=ca.involuntary,
                source=AbilitySource.Class,
            )
        )
```

Then in the chargen `_compose_character` (the function that contains the existing line 1922 `abilities: list[AbilityDefinition] = []`), after line 1969 (the `chargen.abilities_resolved` span event closes the scene-driven loop), call:

```python
        # Class signature seeding (spec 2026-05-10 §6.1).
        if self._class_def is not None:
            class_seed_count_before = len(abilities)
            _seed_class_abilities(abilities, self._class_def)
            class_seed_count = len(abilities) - class_seed_count_before
            from sidequest.telemetry.spans import SPAN_CHARGEN_CLASS_ABILITIES_SEEDED
            span.add_event(
                SPAN_CHARGEN_CLASS_ABILITIES_SEEDED,
                {
                    "class_id": self._class_def.id,
                    "ability_count": class_seed_count,
                    "ability_names": ", ".join(
                        a.name
                        for a in abilities[class_seed_count_before:]
                    ),
                },
            )
```

The engineer pins `self._class_def` against the actual builder field name (grep `self\._class` in `builder.py`). If the builder doesn't carry the resolved `ClassDef`, resolve it via `self._classes` lookup using `class_str` (already in scope at line 2049).

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/game/test_chargen_class_abilities.py -v
```
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/builder.py \
        sidequest-server/tests/game/test_chargen_class_abilities.py
git commit -m "feat(chargen): _seed_class_abilities + OTEL emission"
```

---

## Task 11: Chargen — `_seed_item_abilities` stub (documented exception)

**Files:**
- Modify: `sidequest-server/sidequest/game/builder.py`
- Test: extend `sidequest-server/tests/game/test_chargen_class_abilities.py`

This is an explicit exception to the project's "no stubs" rule per spec §6.2 — the next story owns it. The test pins the contract so a future Reviewer doesn't delete the empty-body function as dead code.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/game/test_chargen_class_abilities.py`:

```python
def test_seed_item_abilities_is_callable_and_returns_none():
    """Contract test — locks the documented stub against accidental deletion.
    Spec 2026-05-10 §6.2."""
    from sidequest.game.builder import _seed_item_abilities

    abilities: list[AbilityDefinition] = []
    # `kit_def=None` is the current-story shape — the next story replaces this with
    # KitDefinition. The contract that matters here: callable, returns None,
    # leaves abilities untouched.
    result = _seed_item_abilities(abilities, kit_def=None)

    assert result is None
    assert abilities == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/game/test_chargen_class_abilities.py::test_seed_item_abilities_is_callable_and_returns_none -v
```
Expected: FAIL — `cannot import name '_seed_item_abilities'`.

- [ ] **Step 3: Add the stub**

In `sidequest-server/sidequest/game/builder.py`, next to `_seed_class_abilities`:

```python
def _seed_item_abilities(
    abilities: list[AbilityDefinition], kit_def: object
) -> None:
    """Populate Item-source abilities from the starting kit.

    DOCUMENTED STUB — empty body retained as the architectural seam for
    the imminent next story (item-source ability content). Removing this
    function or its call site requires updating spec
    docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md §6.2.
    Reviewer guard: contract test in tests/game/test_chargen_class_abilities.py.
    """
    return None
```

Add the call in chargen, immediately after `_seed_class_abilities` invocation:

```python
        # Stub seam — next story owns Item-source ability population (spec §6.2).
        _seed_item_abilities(abilities, kit_def=getattr(self, "_kit_def", None))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/game/test_chargen_class_abilities.py -v
```
Expected: PASS (4 tests in file).

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/builder.py \
        sidequest-server/tests/game/test_chargen_class_abilities.py
git commit -m "feat(chargen): _seed_item_abilities stub seam (next-story hook)"
```

---

## Task 12: Protocol — full `AbilityDefinition` + `class_moves` filtering

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:295` (`CharacterSheetDetails.abilities`)
- Modify: `sidequest-server/sidequest/server/views.py:354` (build path)
- Test: `sidequest-server/tests/protocol/test_character_sheet_abilities.py`

**Universal beats to filter from `class_moves`:** `attack`, `defend`, `flee`. The auto-filled scaffolding suffix to drop is anything matching `auto-filled` (per current UI filter at `CharacterPanel.tsx:831`).

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/protocol/test_character_sheet_abilities.py
"""Story 2026-05-10 — protocol contract for full AbilityDefinition + class_moves."""
from __future__ import annotations

import pytest

from sidequest.game.ability import AbilitySource
from sidequest.game.character import AbilityDefinition
from sidequest.protocol.models import CharacterSheetDetails


def _ab(name: str, source: AbilitySource = AbilitySource.Class) -> AbilityDefinition:
    return AbilityDefinition(
        name=name,
        genre_description=f"{name} prose.",
        mechanical_effect=f"{name} effect.",
        involuntary=False,
        source=source,
    )


def test_abilities_serializes_as_full_objects_not_strings():
    sheet = CharacterSheetDetails(
        race="Human",
        stats={"STR": 10},
        abilities=[_ab("Turn Undead")],
        backstory="Backstory",
        personality="Devout",
        equipment=[],
        class_moves=["pray", "shield_bash", "turn_undead"],
    )
    dumped = sheet.model_dump()
    assert isinstance(dumped["abilities"], list)
    assert dumped["abilities"][0]["name"] == "Turn Undead"
    assert dumped["abilities"][0]["source"] == "Class"
    assert dumped["abilities"][0]["genre_description"] == "Turn Undead prose."


def test_class_moves_field_exists_and_is_list_of_str():
    sheet = CharacterSheetDetails(
        race="Human",
        stats={},
        abilities=[],
        backstory="x",
        personality="y",
        equipment=[],
        class_moves=["pray", "shield_bash"],
    )
    assert sheet.class_moves == ["pray", "shield_bash"]


def test_views_build_filters_universal_beats_and_autofilled():
    """The view layer drops attack/defend/flee + 'auto-filled' before sending to UI."""
    from sidequest.server.views import _filter_class_moves  # new helper added in Task 12

    raw = ["attack", "defend", "flee", "shield_bash", "turn_undead", "pray", "thing-auto-filled"]
    filtered = _filter_class_moves(raw)
    assert filtered == ["shield_bash", "turn_undead", "pray"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/protocol/test_character_sheet_abilities.py -v
```
Expected: FAIL — `class_moves` field doesn't exist; `abilities` is `list[str]`; `_filter_class_moves` doesn't exist.

- [ ] **Step 3: Update the protocol model**

In `sidequest-server/sidequest/protocol/models.py:285-307`, replace the `CharacterSheetDetails` definition:

```python
class CharacterSheetDetails(ProtocolBase):
    """Character sheet details nested inside PartyMember.

    Spec: docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md §7.1.
    `abilities` is now full AbilityDefinition (was: list[str] flatten).
    `class_moves` is server-pre-filtered encounter_beat_choices (universal
    beats + 'auto-filled' scaffolding stripped before send).
    """
    from sidequest.game.character import AbilityDefinition  # local import — avoid module cycle

    race: NonBlankString
    stats: dict[str, int]
    abilities: list[AbilityDefinition]
    """Full ability records, including source classification."""
    class_moves: list[str] = Field(default_factory=list)
    """Pre-filtered encounter_beat_choices (universal beats + scaffolding stripped)."""
    backstory: NonBlankString
    personality: NonBlankString
    pronouns: NonBlankString | None = None
    equipment: list[str] = Field(default_factory=list)
```

If `AbilityDefinition` import causes a circular-import problem, use `if TYPE_CHECKING:` for the type hint and `model_rebuild()` after both modules load. Alternatively (and likely simpler), import at module top — pydantic v2 handles forward refs cleanly when the model is loaded once.

- [ ] **Step 4: Add the filter helper in views.py**

In `sidequest-server/sidequest/server/views.py`, add near the top:

```python
_UNIVERSAL_BEATS = {"attack", "defend", "flee"}


def _filter_class_moves(raw: list[str]) -> list[str]:
    """Drop universal beats and any 'auto-filled' scaffolding from a raw
    encounter_beat_choices list before sending to the UI.

    Spec: 2026-05-10 class-mechanical-surface §7.1 — UI receives a clean list.
    """
    return [
        b for b in raw
        if b not in _UNIVERSAL_BEATS and "auto-filled" not in b
    ]
```

Then update `party_member_from_character` (line 336+) to:

```python
    # Full AbilityDefinition list (no longer flattened to .name).
    abilities = list(character.abilities)

    # class_moves — derive from class_def in genre pack if available.
    class_moves: list[str] = []
    class_def = next(
        (c for c in sd.genre_pack.classes if c.display_name == character.char_class),
        None,
    )
    if class_def is not None:
        class_moves = _filter_class_moves(class_def.encounter_beat_choices)

    sheet = CharacterSheetDetails(
        race=NonBlankString(character.race),
        stats=stats,
        abilities=abilities,
        class_moves=class_moves,
        backstory=NonBlankString(character.backstory or "(no backstory)"),
        personality=NonBlankString(character.core.personality),
        pronouns=NonBlankString(character.pronouns) if character.pronouns else None,
        equipment=equipment,
    )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/protocol/test_character_sheet_abilities.py -v
```
Expected: PASS.

- [ ] **Step 6: Run full test suite to catch any regression from the protocol shape change**

```bash
uv run pytest -v 2>&1 | tail -40
```
Expected: PASS for all (or only pre-existing unrelated failures). Pay attention to any test that asserts `abilities[0]` is a string — those need updating.

- [ ] **Step 7: Commit**

```bash
git add sidequest-server/sidequest/protocol/models.py \
        sidequest-server/sidequest/server/views.py \
        sidequest-server/tests/protocol/test_character_sheet_abilities.py
git commit -m "feat(protocol): full AbilityDefinition + server-side class_moves filtering"
```

---

## Task 13: UI types — update client side

**Files:**
- Modify: client-side type for character sheet (find via `grep -rn "abilities.*string\[\]\|abilities: string" sidequest-ui/src/`)
- Modify: any consumer of `character.abilities` (likely `CharacterPanel.tsx:325`)

- [ ] **Step 1: Locate the type**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui
grep -rn "abilities.*string\[\]\|abilities: string" src/
```

The likely hit is `src/types/character.ts` or similar. Pin the file before editing.

- [ ] **Step 2: Update the type**

```typescript
// In whatever file defines the Character / CharacterSheet shape:
export type AbilitySource = "Race" | "Class" | "Item" | "Play";

export interface AbilityDefinition {
  name: string;
  genre_description: string;
  mechanical_effect: string;
  involuntary: boolean;
  source: AbilitySource;
}

export interface CharacterSheet {
  // ...existing fields...
  abilities: AbilityDefinition[];   // was: string[]
  class_moves: string[];             // NEW
}
```

- [ ] **Step 3: Run the type-check / build to find consumer breaks**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui
npx tsc --noEmit 2>&1 | head -40
```
Expected: errors at `CharacterPanel.tsx:325` and the `AbilitiesContent` props.

- [ ] **Step 4: Don't fix consumers yet — that's Task 14**

This task is just the type-side change. Commit and move on.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/types/  # adjust to whatever file you edited
git commit -m "feat(ui-types): AbilityDefinition + class_moves on CharacterSheet"
```

---

## Task 14: UI — AbilitiesContent four-section restructure

**Files:**
- Modify: `sidequest-ui/src/components/CharacterPanel.tsx:820-909`
- Test: `sidequest-ui/src/components/__tests__/AbilitiesContent.test.tsx`

The new layout:

| Section | Visibility |
|---|---|
| **Class signature** | hidden when no Class-source abilities (header AND content) |
| **Class moves** | hidden when `class_moves` empty |
| **From inventory** | hidden when no Item-source abilities (header AND content) |
| **Earned** | hidden when no Play-source abilities AND no `affinities` data (header AND content) |
| **Sensitivities** | always visible (existing component, unchanged) |

**The string `"No abilities."` is removed entirely.**

- [ ] **Step 1: Write the failing test**

```typescript
// sidequest-ui/src/components/__tests__/AbilitiesContent.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AbilitiesContent } from "../CharacterPanel";  // export named
import type { AbilityDefinition } from "../../types/character";  // adjust path

const cleric_turn_undead: AbilityDefinition = {
  name: "Turn Undead",
  genre_description: "He raises the holy symbol.",
  mechanical_effect: "2d6 vs HD.",
  involuntary: false,
  source: "Class",
};

describe("AbilitiesContent — four-section restructure", () => {
  it("never renders 'No abilities.'", () => {
    const { container } = render(
      <AbilitiesContent
        abilities={[]}
        class_moves={[]}
        magicState={null}
        characterId="c1"
      />,
    );
    expect(container.textContent).not.toContain("No abilities.");
  });

  it("renders Class signature card with prose for a Cleric", () => {
    render(
      <AbilitiesContent
        abilities={[cleric_turn_undead]}
        class_moves={["pray", "shield_bash", "turn_undead"]}
        magicState={null}
        characterId="c1"
      />,
    );
    expect(screen.getByText("Turn Undead")).toBeInTheDocument();
    expect(screen.getByText(/raises the holy symbol/i)).toBeInTheDocument();
  });

  it("renders class_moves as a chip row", () => {
    render(
      <AbilitiesContent
        abilities={[]}
        class_moves={["pray", "shield_bash", "turn_undead"]}
        magicState={null}
        characterId="c1"
      />,
    );
    expect(screen.getByText("pray")).toBeInTheDocument();
    expect(screen.getByText("shield_bash")).toBeInTheDocument();
    expect(screen.getByText("turn_undead")).toBeInTheDocument();
  });

  it("hides Class signature header when no Class-source abilities", () => {
    render(
      <AbilitiesContent
        abilities={[]}
        class_moves={["cast_spell"]}  // Mage-like
        magicState={null}
        characterId="c1"
      />,
    );
    expect(screen.queryByText(/class signature/i)).not.toBeInTheDocument();
  });

  it("hides 'From inventory' header when no Item-source abilities", () => {
    render(
      <AbilitiesContent
        abilities={[cleric_turn_undead]}
        class_moves={["pray"]}
        magicState={null}
        characterId="c1"
      />,
    );
    expect(screen.queryByText(/from inventory/i)).not.toBeInTheDocument();
  });

  it("does not surface auto-filled scaffolding entries", () => {
    const leak: AbilityDefinition = {
      ...cleric_turn_undead,
      name: "thing-auto-filled",
    };
    render(
      <AbilitiesContent
        abilities={[cleric_turn_undead, leak]}
        class_moves={[]}
        magicState={null}
        characterId="c1"
      />,
    );
    expect(screen.queryByText("thing-auto-filled")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui
npx vitest run src/components/__tests__/AbilitiesContent.test.tsx
```
Expected: FAIL — `AbilitiesContent` not exported, or it still uses `string[]` props.

- [ ] **Step 3: Rewrite `AbilitiesContent` in `CharacterPanel.tsx`**

Replace lines 820–909 of `sidequest-ui/src/components/CharacterPanel.tsx` with:

```typescript
export function AbilitiesContent({
  abilities,
  class_moves,
  magicState,
  characterId,
}: {
  abilities: AbilityDefinition[];
  class_moves: string[];
  magicState: MagicState | null;
  characterId: string;
}) {
  // Filter scaffolding leaks (server-side filter is the source of truth, but
  // a client guard prevents regressions if a future server change forgets).
  const real = abilities.filter((a) => !a.name.includes("auto-filled"));

  const classAbilities = real.filter((a) => a.source === "Class");
  const itemAbilities = real.filter((a) => a.source === "Item");
  const playAbilities = real.filter((a) => a.source === "Play");

  const showClassSig = classAbilities.length > 0;
  const showClassMoves = class_moves.length > 0;
  const showItem = itemAbilities.length > 0;
  const showEarned = playAbilities.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {showClassSig && (
        <section>
          <h4 style={{ fontFamily: FONT_DISPLAY, color: FOLIO.crimson, marginBottom: 6 }}>
            Class signature
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {classAbilities.map((a) => (
              <AbilityCard key={a.name} ability={a} />
            ))}
          </div>
        </section>
      )}

      {showClassMoves && (
        <section>
          <h4 style={{ fontFamily: FONT_DISPLAY, color: FOLIO.crimson, marginBottom: 6 }}>
            Class moves
          </h4>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {class_moves.map((m) => (
              <span
                key={m}
                style={{
                  padding: "2px 8px",
                  background: FOLIO.paper2,
                  border: `1px solid ${FOLIO.rule}`,
                  fontFamily: FONT_BODY,
                  fontSize: 13,
                  color: FOLIO.ink,
                }}
              >
                {m}
              </span>
            ))}
          </div>
        </section>
      )}

      {showItem && (
        <section>
          <h4 style={{ fontFamily: FONT_DISPLAY, color: FOLIO.crimson, marginBottom: 6 }}>
            From inventory
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {itemAbilities.map((a) => (
              <AbilityCard key={a.name} ability={a} />
            ))}
          </div>
        </section>
      )}

      {showEarned && (
        <section>
          <h4 style={{ fontFamily: FONT_DISPLAY, color: FOLIO.crimson, marginBottom: 6 }}>
            Earned
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {playAbilities.map((a) => (
              <AbilityCard key={a.name} ability={a} />
            ))}
          </div>
        </section>
      )}

      <SensitivitiesSection magicState={magicState} characterId={characterId} />
    </div>
  );
}

function AbilityCard({ ability }: { ability: AbilityDefinition }) {
  return (
    <div
      style={{
        padding: 10,
        background: FOLIO.paper2,
        border: `1px solid ${FOLIO.gold}`,
      }}
    >
      <div
        style={{
          fontFamily: FONT_DISPLAY,
          fontSize: 17,
          color: FOLIO.ink,
          marginBottom: 4,
        }}
      >
        {ability.name}
      </div>
      <div
        style={{
          fontFamily: FONT_BODY,
          fontSize: 14,
          color: FOLIO.ink,
          marginBottom: 6,
          lineHeight: 1.4,
        }}
      >
        {ability.genre_description}
      </div>
      <div
        style={{
          fontFamily: FONT_BODY,
          fontSize: 12,
          fontStyle: "italic",
          color: FOLIO.inkSoft,
        }}
      >
        {ability.mechanical_effect}
      </div>
    </div>
  );
}
```

Also update the call site at line 327 to pass `class_moves`:

```typescript
{activeTab === "abilities" && (
  <AbilitiesContent
    abilities={character.abilities}
    class_moves={character.class_moves ?? []}
    magicState={magicState}
    characterId={character.id}
  />
)}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx vitest run src/components/__tests__/AbilitiesContent.test.tsx
```
Expected: PASS (6 tests).

- [ ] **Step 5: Run client lint + full test suite**

```bash
cd /Users/slabgorb/Projects/oq-1
just client-lint
just client-test
```
Expected: PASS (or pre-existing unrelated failures only).

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/components/CharacterPanel.tsx \
        sidequest-ui/src/components/__tests__/AbilitiesContent.test.tsx
git commit -m "feat(ui): four-section AbilitiesContent — no more 'No abilities.'"
```

---

## Task 15: Integration wiring test (CLAUDE.md mandatory)

**Files:**
- Create: `sidequest-server/sidequest/tests/integration/test_class_signature_wiring.py`

This test is the merge gate. It spins the server, runs a real chargen for a Cleric in `caverns_and_claudes`, captures the state-mirror message, and asserts the new payload shape end-to-end.

- [ ] **Step 1: Write the test**

```python
# sidequest-server/tests/integration/test_class_signature_wiring.py
"""Story 2026-05-10 — full end-to-end wiring for class mechanical surface.

Mandatory wiring test per CLAUDE.md "Every Test Suite Needs a Wiring Test".

Spins a real session, runs chargen for a Cleric, parses the state-mirror
party-member payload, and asserts the full AbilityDefinition + class_moves
contract holds end-to-end.
"""
from __future__ import annotations

import pytest

from sidequest.game.ability import AbilitySource


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleric_chargen_yields_turn_undead_in_state_mirror(test_session_with_caverns):
    """A Cleric created in caverns_and_claudes shows Turn Undead with full prose."""
    session = test_session_with_caverns

    # Run chargen for a Cleric. The fixture should expose a helper that
    # walks the chargen scenes; engineer pins the exact API against
    # tests/integration/conftest.py and existing chargen integration tests.
    char = await session.run_chargen(class_id="cleric")

    # Snapshot the state-mirror payload that the WS handler builds.
    sheet = session.snapshot_party_member(char.id).sheet

    assert sheet.abilities, "Expected at least one ability for Cleric"

    turn_undead_entries = [a for a in sheet.abilities if a.name == "Turn Undead"]
    assert len(turn_undead_entries) == 1, (
        f"Expected exactly one Turn Undead entry, got {[a.name for a in sheet.abilities]}"
    )
    tu = turn_undead_entries[0]
    assert tu.source == AbilitySource.Class
    assert tu.genre_description and "{writer agent" not in tu.genre_description, (
        "Turn Undead must ship with real prose, not the placeholder"
    )

    # class_moves: filtered, includes class-distinctive beats, excludes universals.
    assert "turn_undead" in sheet.class_moves
    assert "pray" in sheet.class_moves
    assert "shield_bash" in sheet.class_moves
    assert "attack" not in sheet.class_moves
    assert "defend" not in sheet.class_moves
    assert "flee" not in sheet.class_moves


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mage_chargen_has_empty_class_signature_but_class_moves(test_session_with_caverns):
    """Mage's signature is the magic plugin — Class abilities empty, but class_moves populated."""
    session = test_session_with_caverns

    char = await session.run_chargen(class_id="mage")
    sheet = session.snapshot_party_member(char.id).sheet

    class_source = [a for a in sheet.abilities if a.source == AbilitySource.Class]
    assert class_source == [], (
        f"Mage should have no Class-source abilities; got {[a.name for a in class_source]}"
    )
    assert "cast_spell" in sheet.class_moves
    assert "cast_cantrip" in sheet.class_moves
```

The fixture `test_session_with_caverns` and helpers (`run_chargen`, `snapshot_party_member`) should be added to `tests/integration/conftest.py`. The engineer pins their exact shape against the existing chargen integration tests in that directory.

- [ ] **Step 2: Run the test**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/integration/test_class_signature_wiring.py -v
```
Expected: PASS — every prior task ships green; this test validates the full chain.

If it fails, the engineer must trace the failure back through the protocol (Task 12), chargen (Tasks 10–11), and content (Task 8). **Do not skip-mark this test.** It is the merge gate.

- [ ] **Step 3: Run the full server + client test suite**

```bash
cd /Users/slabgorb/Projects/oq-1
just check-all
```
Expected: PASS across server-test, client-lint, client-test, daemon-lint.

- [ ] **Step 4: Manual smoke**

Spin everything up:

```bash
just up
```

Open `http://localhost:5173`, create a Cleric, open the Abilities tab. Verify:

- "Class signature" header is visible.
- "Turn Undead" card shows the prose ("He lifts the holy symbol — wood worn pale...").
- Mechanical-effect line appears in italic, muted color.
- "Class moves" chip row shows `pray`, `shield_bash`, `turn_undead` (no `attack`/`defend`/`flee`).
- "From inventory" header is **absent** (no Item-source abilities at L1).
- "Earned" header is **absent** (no affinities at L1).
- The string `"No abilities."` does not appear anywhere on the sheet.

Repeat for Fighter (expect "Taunt") and Thief (expect "Backstab"). Repeat for Mage — expect Class signature header **absent**, but Class moves chip row showing `cast_cantrip`, `cast_spell`.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/tests/integration/test_class_signature_wiring.py \
        sidequest-server/tests/integration/conftest.py
git commit -m "test(integration): end-to-end class signature wiring for C&C"
```

---

## Task 16: ADR — Class Mechanical Surface

**Files:**
- Create: `docs/adr/ADR-095-class-mechanical-surface.md` (next free ADR number — confirm via `ls docs/adr/ | grep -oE 'ADR-[0-9]+' | sort -u | tail -5`)

The ADR records the load-bearing decision: "classes are a mechanical lane, not flavor-only" (spec §2). It sits adjacent to ADR-014 (Diamonds and Coal) and amends ADR-021 (Progression System) by clarifying that Affinities are the *growth* lane on top of the per-class *starting* lane.

- [ ] **Step 1: Write the ADR**

```markdown
---
adr: 95
title: Class Mechanical Surface — One Signature Ability Per Non-Magical Class
status: accepted
date: 2026-05-10
deciders: [keith, architect]
relates_to: [014, 021]
amends: [021]
---

# ADR-095: Class Mechanical Surface

## Status

Accepted.

## Context

Two of the four primary-audience players (Keith — 40-year B/X veteran;
Sebastien — mechanics-first) read the character sheet before the prose. A
freshly-created Lv 1 Cleric and Lv 1 Thief in `caverns_and_claudes`
displayed `"No abilities."` on the Abilities tab — honest data, honest
rendering, but to a B/X reader it parses as a load failure or a missing
class definition.

ADR-021 established Affinities (`progression.yaml`) as the growth lane —
class-agnostic, earned through play. The data shape of `classes.yaml`
implied that classes themselves are a flavor lane (kit, stat prime,
encounter beats, magic plugin) with no mechanical signature of their own.

## Decision

**Classes are a mechanical lane, not flavor-only.** Every class either
has a magic plugin filling its signature mechanical slot, or carries one
Class-source `AbilityDefinition` that does. Affinities remain the
*growth* lane on top — the class signature is the *starting* mechanical
lane. Both ship and coexist; neither replaces the other.

For `caverns_and_claudes`:

- Cleric → **Turn Undead** (Class-source signature ability)
- Fighter → **Taunt** (Class-source signature ability + new beat ID)
- Thief → **Backstab** (Class-source signature ability)
- Mage → no Class signature; magic plugin fills the slot

The Abilities tab renders four sections gated on per-source presence:
Class signature, Class moves (chip row from `encounter_beat_choices`),
From inventory (Item-source — hooked but empty), Earned (Play-source).
Empty sections suppress their headers. The string `"No abilities."` does
not appear in rendered output.

## Scope

`caverns_and_claudes` only. Other 10 genre packs adopt the data shape
lazily as they surface for playtest.

## Consequences

### Positive

- Sebastien sees a mechanical signature on every L1 sheet — the design
  intent is now visible without prose mediation.
- Keith's B/X expectations are met: Cleric has Turn Undead, Thief has
  Backstab, both rendered with mechanical detail.
- The "no abilities" empty state dies. Empty Item-source and Earned
  sections gracefully suppress their headers.
- The four-source layout (Race / Class / Item / Play) is now load-bearing
  at the UI level, not just the data level.

### Negative

- Per-genre adoption is now a real cost — each genre pack that wants to
  show class signatures must author them in `abilities:` blocks.
- A class with both `magic_config` and `abilities:` populates both. By
  design, but a future genre author could create unexpected combinations.

### Neutral

- ADR-021 is amended, not superseded. Affinities continue exactly as
  designed. The class signature is *additive*.

## Alternatives Considered

Three options were brainstormed (per design spec
`docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md` §10):

1. **Minimum visibility fix.** Change the empty-state string; surface
   Turn Undead via the existing `magic_config.turn_undead: true` flag.
   Rejected — papers over the structural issue.
2. **Promote class beats to abilities.** Treat `encounter_beat_choices`
   (filtered) as Class-source abilities directly. Rejected — collapses
   two abstractions that should remain separate (the cards-vs-chips
   visual distinction is load-bearing).
3. **Restore B/X canonical class data.** Add Thief percentage skills,
   Turn Undead matrix, etc. Deferred — likely the right move for a future
   "canonical sheets" pass, but blocks this story on too much content.

The chosen design (Variant 1 in the spec) — one signature `AbilityDefinition`
per non-magical class plus the chip row — captures most of the
mechanical-signal value at a fraction of Option 3's content lift.

## References

- Design spec: `docs/superpowers/specs/2026-05-10-class-mechanical-surface-design.md`
- Implementation plan: `docs/superpowers/plans/2026-05-10-class-mechanical-surface.md`
- Pre-brainstorm handoff: `docs/design/class-mechanical-surface-handoff.md`
- ADR-014 (Diamonds and Coal) — detail signals importance
- ADR-021 (Progression System) — Affinity lane (this ADR amends)
- CLAUDE.md "Who This Is For" — Sebastien / Keith audience rubric
```

- [ ] **Step 2: Update the ADR index**

If the project regenerates the ADR index automatically (per ADR-088), run:

```bash
python scripts/regenerate_adr_indexes.py
```

Otherwise, add a line in `docs/adr/README.md` under the appropriate category (Game Systems / Character) and update the ADR Index in `CLAUDE.md` if needed.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/ADR-095-class-mechanical-surface.md \
        docs/adr/README.md \
        CLAUDE.md
git commit -m "docs(adr): ADR-095 class mechanical surface — one signature per non-magical class"
```

---

## Final Verification

Before declaring the story done:

- [ ] All tests in this plan pass: `just check-all`
- [ ] Manual smoke against all four C&C classes (Cleric / Fighter / Thief / Mage) passes per Task 15 Step 4
- [ ] OTEL events visible in GM panel during smoke: `chargen.class_abilities.seeded`, `encounter.taunt.activated`, `encounter.taunt.expired`
- [ ] No occurrence of `"No abilities."` in `sidequest-ui/src/` (`grep -rn "No abilities" sidequest-ui/src/` returns empty)
- [ ] No skipped tests added by this story
- [ ] All commits use the conventional-commit format established by the project

---

## Self-Review Notes (architect)

Spec coverage check:

- §1 problem statement → addressed by Tasks 8, 12, 14 (data, protocol, UI)
- §2 deeper-question answer → captured in ADR-095 (Task 16)
- §3 scope (C&C only) → enforced by tasks touching only `caverns_and_claudes` content
- §4 four-layer architecture → implemented by Task 14
- §5.1 classes.yaml change (taunt + abilities key) → Tasks 1, 8
- §5.2 ClassAbilityDef → Tasks 7, 9
- §5.3 AbilityDefinition reused as-is → no task needed; explicitly noted in File Structure
- §5.4 future-proof notes → captured in ClassAbilityDef docstring; not implemented (correct)
- §6.1 _seed_class_abilities → Task 10
- §6.2 _seed_item_abilities stub → Task 11
- §6.3 magic plugin path unchanged → no task; stub in §6.2 ensures no regression
- §6.4 failure modes → Task 9 (loud-fail validators)
- §6.5 OTEL emission → Tasks 2, 3, 6, 10
- §7.1 protocol shape change → Task 12
- §7.2 AbilitiesContent restructure → Task 14
- §7.3 multiplayer concern → no change required; existing perception filter handles per-character payloads. Task 15 verifies via single-player path; multiplayer-specific verification deferred to playtest.
- §8 Taunt handler → Tasks 2–6
- §9 content authoring → Task 8 (prose written inline; writer-agent polish deferrable)
- §10 testing strategy → Tasks 7, 9–12, 14, 15 (every category covered)
- §11 out of scope → respected; no extra-scope tasks
- §12 locked decisions → no task; respected throughout
- §14 open questions → resolved during plan authoring (chargen finalization at builder.py line ~1969; protocol carrier at views.py line 354; Affinity rendering does NOT exist in UI today and the plan treats Earned section as conditional)

Placeholder scan: no TBD/TODO/"add appropriate error handling"/"similar to Task N" patterns. Every code step ships actual code.

Type consistency: `AbilityDefinition` shape used identically across server (Task 12), UI types (Task 13), UI component (Task 14), and tests. `ClassAbilityDef` shape used identically across genre model (Task 7), content (Task 8), and chargen seam (Task 10).
