# SWN P4 — Initiative Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SWN-bound confrontations a real, engine-owned, ceremony-free turn order — roll `1d8 + DEX` once per fight (server-side, OTEL-logged, no 3D cup, no player prompt), persist it, show it to the table, and hand it to the narrator as the authoritative resolution order.

**Architecture:** The blind-commit/no-replan property already ships via the ADR-036 sealed-letter barrier; the only gap is that initiative is never rolled. The `RulesetModule` gets a pure `roll_initiative(actor_dex_scores, rng)` method (SWN does the math, `native` returns `None`). The dispatch seam (`instantiate_encounter_from_trigger`) resolves each actor's DEX — PC from `Character.stats["Reflex"]`, opponent from a new `dexterity` reserved key on `opponent_default_stats` enforced at pack-load by the existing `ConfrontationDef` validator — calls the module, persists the order on `StructuredEncounter.initiative`, emits an OTEL span, surfaces it on the confrontation payload, and prepends it to the narrator turn input. `dead_premise` is explicitly **out of scope** (deferred to P5, where the per-actor tool walk can enforce it).

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest (`-n auto` via xdist), OpenTelemetry, `uv`. Two repos: `sidequest-server` and `sidequest-content` (github-flow off `develop`).

**Spec:** `docs/superpowers/specs/2026-05-27-swn-p4-initiative-spine-design.md`

---

## File Structure

**sidequest-server:**
- `sidequest/genre/models/rules.py` — add `dexterity` reserved key, `opponent_dexterity` property, extend `ConfrontationDef._validate` (Task 1).
- `sidequest/game/ruleset/base.py` — `roll_initiative` default `None` (Task 2).
- `sidequest/game/ruleset/swn.py` — SWN `roll_initiative` impl (Task 3).
- `sidequest/game/encounter.py` — `StructuredEncounter.initiative` field (Task 4).
- `sidequest/telemetry/spans/encounter.py` — `encounter_initiative_rolled_span` (Task 5).
- `sidequest/server/dispatch/encounter_lifecycle.py` — resolve DEX + roll + persist + span; drop redundant runtime check (Task 6).
- `sidequest/protocol/messages.py` + `sidequest/server/dispatch/confrontation.py` — `initiative_order` payload field + population (Task 7).
- `sidequest/handlers/player_action.py` — prepend initiative preamble to narrator input (Task 8).

**sidequest-content:**
- `genre_packs/space_opera/rules.yaml` — `dexterity` on both opponent blocks (Task 1).

---

## Task 0: Branch setup (both repos)

**Files:** none (git only)

- [ ] **Step 1: Branch both changed subrepos off `develop` before any commit**

The pf commit hook scans all subrepos; branch every repo you will touch before the first commit anywhere.

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && env -u GITHUB_TOKEN git checkout develop && git pull --ff-only && git checkout -b feat/swn-p4-initiative-spine
cd /Users/slabgorb/Projects/oq-2/sidequest-content && env -u GITHUB_TOKEN git checkout develop && git pull --ff-only && git checkout -b feat/swn-p4-opponent-dexterity
```

Expected: both repos on their new `feat/…` branch, clean tree.

---

## Task 1: Opponent DEX reserved key + load-time contract + content

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/rules.py:23` (reserved keys), `:437-478` (validator), add property near `:528-542`
- Modify: `sidequest-content/genre_packs/space_opera/rules.yaml:226,323` (opponent blocks)
- Test: `sidequest-server/tests/genre/test_confrontation_def_dexterity_contract.py` (new)

> **Why server + content in one task:** the validator change makes `space_opera` fail to *load* until the content authors `dexterity`. They must move together or the broader server suite (which loads the real pack) breaks between tasks.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/genre/test_confrontation_def_dexterity_contract.py`:

```python
"""SWN P4: a combat hp_depletion confrontation must author opponent `dexterity`
at LOAD time (third reserved combat key), not discover it missing mid-seating."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.genre.models.rules import (
    OPPONENT_RESERVED_STAT_KEYS,
    ConfrontationDef,
    WinCondition,
)


def _combat_kwargs(**overrides):
    base = dict(
        confrontation_type="firefight",
        label="Firefight",
        category="combat",
        win_condition=WinCondition.hp_depletion,
        opponent_default_stats={"hp": 7, "armor_class": 12, "dexterity": 13},
        beats=[
            {
                "id": "shoot",
                "label": "Shoot",
                "stat_check": "Physique",
                "base": 1,
                "kind": "strike",
            }
        ],
    )
    base.update(overrides)
    return base


def test_dexterity_is_a_reserved_combat_key():
    assert "dexterity" in OPPONENT_RESERVED_STAT_KEYS


def test_combat_hp_depletion_requires_opponent_dexterity():
    with pytest.raises(ValidationError, match="dexterity"):
        ConfrontationDef(**_combat_kwargs(opponent_default_stats={"hp": 7, "armor_class": 12}))


def test_opponent_dexterity_must_be_at_least_three():
    with pytest.raises(ValidationError, match="dexterity"):
        ConfrontationDef(
            **_combat_kwargs(opponent_default_stats={"hp": 7, "armor_class": 12, "dexterity": 2})
        )


def test_valid_combat_confrontation_exposes_opponent_dexterity():
    cdef = ConfrontationDef(**_combat_kwargs())
    assert cdef.opponent_dexterity == 13


def test_opponent_ability_scores_strips_dexterity():
    cdef = ConfrontationDef(**_combat_kwargs(
        opponent_default_stats={"hp": 7, "armor_class": 12, "dexterity": 13, "Physique": 11}
    ))
    scores = cdef.opponent_ability_scores()
    assert "dexterity" not in scores and "hp" not in scores and "armor_class" not in scores
    assert scores == {"Physique": 11}
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/genre/test_confrontation_def_dexterity_contract.py -q`
Expected: FAIL — `dexterity` not in reserved keys; validator does not require it; `opponent_dexterity` attribute missing.

- [ ] **Step 3: Add `dexterity` to the reserved keys**

In `sidequest/genre/models/rules.py`, change line 23:

```python
OPPONENT_RESERVED_STAT_KEYS: frozenset[str] = frozenset({"hp", "armor_class", "dexterity"})
```

Update the docstring above it (lines 17-22) to add: `` ``dexterity`` seeds the opponent's SWN initiative (1d8 + DEX mod) for hp_depletion combats. ``

- [ ] **Step 4: Extend the validator to require `dexterity`**

In `ConfrontationDef._validate` (the `if self.category == "combat" and self.win_condition == WinCondition.hp_depletion:` block, ~line 456), after the existing `ac` checks and before `valid_categories`, add:

```python
            dex = ods.get("dexterity")
            if dex is None:
                raise ValueError(
                    f"combat confrontation '{self.confrontation_type}' uses "
                    "win_condition 'hp_depletion' but its opponent_default_stats is "
                    f"missing reserved combat key (dexterity={dex!r}); author "
                    "`dexterity` (SWN DEX score) so 1d8+DEX initiative can roll for "
                    "the opponent (SWN P4 — no silent +0 fallback)"
                )
            if int(dex) < 3:
                raise ValueError(
                    f"combat confrontation '{self.confrontation_type}' has "
                    f"opponent_default_stats.dexterity={dex!r}; must be >= 3 "
                    "(SWN ability-score floor)"
                )
```

- [ ] **Step 5: Add the `opponent_dexterity` property**

In `rules.py`, after the `opponent_armor_class` property (~line 542):

```python
    @property
    def opponent_dexterity(self) -> int | None:
        """Content-authored opponent DEX score (SWN P4 initiative), or ``None``."""
        if not self.opponent_default_stats:
            return None
        raw = self.opponent_default_stats.get("dexterity")
        return int(raw) if raw is not None else None
```

- [ ] **Step 6: Author `dexterity` in the content opponent blocks**

In `sidequest-content/genre_packs/space_opera/rules.yaml`, in each `opponent_default_stats` block (the ship at line ~238 `hp: 30` and the personal-combat opponent at line ~334 `hp: 7`), add a `dexterity` line. Feel-calibrated placeholders pending Keith's playtest (like the existing hp/AC):

```yaml
    opponent_default_stats:
      hp: 30
      armor_class: 14
      dexterity: 10   # SWN P4 initiative (1d8+DEX); placeholder, feel-calibrate in playtest
```

```yaml
    opponent_default_stats:
      hp: 7
      armor_class: 12
      dexterity: 13   # SWN P4 initiative (1d8+DEX); placeholder, feel-calibrate in playtest
```

- [ ] **Step 7: Run the tests, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs uv run pytest tests/genre/test_confrontation_def_dexterity_contract.py tests/server/test_space_opera_swn_combat_e2e.py -q`
Expected: PASS — the contract tests pass AND the real `space_opera` pack still loads clean (Test 4 `test_world_loads_clean_under_swn`).

- [ ] **Step 8: Commit (both repos)**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-content && git add genre_packs/space_opera/rules.yaml && git commit -m "feat(space_opera): author opponent dexterity for SWN P4 initiative"
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/genre/models/rules.py tests/genre/test_confrontation_def_dexterity_contract.py && git commit -m "feat(swn): opponent dexterity reserved key + load-time contract (P4)"
```

---

## Task 2: `roll_initiative` seam — base default + native

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/base.py`
- Test: `sidequest-server/tests/game/ruleset/test_roll_initiative_base.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_roll_initiative_base.py`:

```python
"""SWN P4: roll_initiative is optional on the seam — native (and the base
default) return None (no ordering); only SWN populates it."""

from __future__ import annotations

import random

from sidequest.game.ruleset.native import NativeRulesetModule


def test_native_roll_initiative_returns_none():
    result = NativeRulesetModule().roll_initiative(
        actor_dex_scores={"Rux": 12, "Raider": 11},
        rng=random.Random(1),
    )
    assert result is None
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/ruleset/test_roll_initiative_base.py -q`
Expected: FAIL — `AttributeError: 'NativeRulesetModule' object has no attribute 'roll_initiative'`.

- [ ] **Step 3: Add the optional method to the base class**

In `sidequest/game/ruleset/base.py`, add the import at the top:

```python
import random

from sidequest.protocol.models import InitiativeEntry
```

Add this concrete (non-abstract) default method to `RulesetModule` (after `save_params`, ~line 64):

```python
    def roll_initiative(
        self,
        *,
        actor_dex_scores: dict[str, int],
        rng: random.Random,
    ) -> list[InitiativeEntry] | None:
        """Resolution order (descending) for a confrontation, or None for no ordering.

        Default: None (no turn ordering). SWN overrides with 1d8 + DEX mod.
        `actor_dex_scores` maps actor name -> raw DEX score; the dispatch seam
        resolves it (PC from Character.stats, opponent from the dexterity
        reserved key) because CreatureCore carries no ability scores.
        """
        return None
```

`native` inherits this default — no change to `native.py` needed.

- [ ] **Step 4: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/ruleset/test_roll_initiative_base.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/game/ruleset/base.py tests/game/ruleset/test_roll_initiative_base.py && git commit -m "feat(ruleset): optional roll_initiative seam, default None (P4)"
```

---

## Task 3: SWN `roll_initiative` implementation

**Files:**
- Modify: `sidequest-server/sidequest/game/ruleset/swn.py`
- Test: `sidequest-server/tests/game/ruleset/test_swn_roll_initiative.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/ruleset/test_swn_roll_initiative.py`:

```python
"""SWN P4: SwnRulesetModule.roll_initiative — 1d8 + swn_attribute_modifier(DEX),
sorted descending, one InitiativeEntry per actor, deterministic under a seed."""

from __future__ import annotations

import random

from sidequest.game.ruleset.swn import SwnRulesetModule, swn_attribute_modifier
from sidequest.protocol.models import InitiativeEntry


def test_one_entry_per_actor_sorted_descending():
    mod = SwnRulesetModule()
    result = mod.roll_initiative(
        actor_dex_scores={"Rux": 14, "Raider": 8, "Scout": 18},
        rng=random.Random(42),
    )
    assert result is not None
    assert all(isinstance(e, InitiativeEntry) for e in result)
    assert {e.token_id for e in result} == {"Rux", "Raider", "Scout"}
    # Descending by value.
    values = [e.value for e in result]
    assert values == sorted(values, reverse=True)


def test_value_is_d8_plus_dex_mod_in_range():
    mod = SwnRulesetModule()
    # DEX 18 -> +2 mod (swn curve); total in 1+2 .. 8+2 = 3..10.
    result = mod.roll_initiative(actor_dex_scores={"Ace": 18}, rng=random.Random(7))
    assert result is not None
    (entry,) = result
    assert swn_attribute_modifier(18) == 2
    assert 3 <= entry.value <= 10


def test_deterministic_under_seed():
    mod = SwnRulesetModule()
    scores = {"A": 12, "B": 13, "C": 7}
    a = mod.roll_initiative(actor_dex_scores=scores, rng=random.Random(99))
    b = mod.roll_initiative(actor_dex_scores=scores, rng=random.Random(99))
    assert [(e.token_id, e.value) for e in a] == [(e.token_id, e.value) for e in b]


def test_empty_actor_map_returns_empty_list():
    result = SwnRulesetModule().roll_initiative(actor_dex_scores={}, rng=random.Random(1))
    assert result == []
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/ruleset/test_swn_roll_initiative.py -q`
Expected: FAIL — SWN inherits the base `None` default, so `test_one_entry_per_actor_sorted_descending` fails on `result is not None`.

- [ ] **Step 3: Implement SWN `roll_initiative`**

In `sidequest/game/ruleset/swn.py`, add imports at the top:

```python
import random

from sidequest.protocol.models import InitiativeEntry
```

Add the method to `SwnRulesetModule` (after `resolve_damage`):

```python
    def roll_initiative(
        self,
        *,
        actor_dex_scores: dict[str, int],
        rng: random.Random,
    ) -> list[InitiativeEntry] | None:
        """SWN initiative: 1d8 + DEX modifier per actor, sorted descending.

        Faithful SWN (SRD): rolled once at combat start; the seam persists the
        result and reuses it each round. Tie-break: stable sort preserves the
        caller's actor order (TODO: confirm SRD tie-break and pin to SwnConfig).
        """
        entries = [
            InitiativeEntry(
                token_id=name,
                value=rng.randint(1, 8) + swn_attribute_modifier(score),
            )
            for name, score in actor_dex_scores.items()
        ]
        entries.sort(key=lambda e: e.value, reverse=True)
        return entries
```

- [ ] **Step 4: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/ruleset/test_swn_roll_initiative.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/game/ruleset/swn.py tests/game/ruleset/test_swn_roll_initiative.py && git commit -m "feat(swn): roll_initiative — 1d8 + DEX mod, sorted (P4)"
```

---

## Task 4: `StructuredEncounter.initiative` field

**Files:**
- Modify: `sidequest-server/sidequest/game/encounter.py`
- Test: `sidequest-server/tests/game/test_encounter_initiative_field.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_encounter_initiative_field.py`:

```python
"""SWN P4: StructuredEncounter persists the rolled initiative order."""

from __future__ import annotations

from sidequest.game.encounter import EncounterMetric, StructuredEncounter
from sidequest.protocol.models import InitiativeEntry


def _enc(**overrides) -> StructuredEncounter:
    base = dict(
        encounter_type="firefight",
        player_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
        opponent_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
    )
    base.update(overrides)
    return StructuredEncounter(**base)


def test_initiative_defaults_empty():
    assert _enc().initiative == []


def test_initiative_can_be_set():
    enc = _enc()
    enc.initiative = [InitiativeEntry(token_id="Rux", value=9)]
    assert enc.initiative[0].token_id == "Rux"
    assert enc.initiative[0].value == 9
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/test_encounter_initiative_field.py -q`
Expected: FAIL — `StructuredEncounter` has no `initiative` field (with `extra="forbid"` the set raises, and the default assert fails).

- [ ] **Step 3: Add the field**

In `sidequest/game/encounter.py`, extend the existing protocol import (line 17):

```python
from sidequest.protocol.models import EncounterLocationOverlay, InitiativeEntry
```

In `StructuredEncounter` (after `actors: list[EncounterActor] = Field(default_factory=list)`, ~line 161), add:

```python
    initiative: list[InitiativeEntry] = Field(default_factory=list)
    """SWN P4: 1d8+DEX resolution order, rolled once at instantiation. Empty for
    rulesets with no ordering (native) and non-combat encounters."""
```

- [ ] **Step 4: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/game/test_encounter_initiative_field.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/game/encounter.py tests/game/test_encounter_initiative_field.py && git commit -m "feat(encounter): persist SWN initiative order on StructuredEncounter (P4)"
```

---

## Task 5: `encounter_initiative_rolled` OTEL span

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/encounter.py`
- Test: `sidequest-server/tests/telemetry/test_initiative_rolled_span.py` (new)

> Mirror the existing `encounter_resolved_span` (same file, ~line 299): `@contextmanager`, `Span.open(NAME, attrs, tracer_override=_tracer)`, plus the `SPAN_ROUTES` registration pattern used by the other encounter spans.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_initiative_rolled_span.py`:

```python
"""SWN P4: the initiative roll emits an OTEL span (the polygraph) so the GM
panel can verify the order is engine-rolled, not narrator improv."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.telemetry.spans.encounter import encounter_initiative_rolled_span


def test_initiative_rolled_span_carries_order():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    with encounter_initiative_rolled_span(
        encounter_type="firefight",
        initiative_order="Rux(9), Raider(5)",
        source="instantiate",
        _tracer=tracer,
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "encounter.initiative_rolled"
    assert span.attributes["encounter_type"] == "firefight"
    assert span.attributes["initiative_order"] == "Rux(9), Raider(5)"
    assert span.attributes["source"] == "instantiate"
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/telemetry/test_initiative_rolled_span.py -q`
Expected: FAIL — `ImportError: cannot import name 'encounter_initiative_rolled_span'`.

- [ ] **Step 3: Read the neighbours, then add the span**

First read `sidequest/telemetry/spans/encounter.py` lines 1-40 and 299-337 to copy the exact `SPAN_*` constant declaration, `SPAN_ROUTES` registration shape (the `SpanRoute`/`extract` lambda used by `SPAN_ENCOUNTER_RESOLVED`), and the `Span.open` import. Then add, mirroring `encounter_resolved_span`:

Near the other `SPAN_ENCOUNTER_*` constants at the top of the file:

```python
SPAN_ENCOUNTER_INITIATIVE_ROLLED = "encounter.initiative_rolled"
```

Register it in `SPAN_ROUTES` next to the other encounter routes (copy the exact `SpanRoute(...)` keyword shape used by the existing `SPAN_ENCOUNTER_RESOLVED` entry; this `extract` mirrors it):

```python
SPAN_ROUTES[SPAN_ENCOUNTER_INITIATIVE_ROLLED] = SpanRoute(
    event_type="state_transition",
    component="encounter",
    extract=lambda span: {
        "field": "encounter.initiative_rolled",
        "encounter_type": (span.attributes or {}).get("encounter_type", ""),
        "initiative_order": (span.attributes or {}).get("initiative_order", ""),
        "source": (span.attributes or {}).get("source", ""),
    },
)
```

Add the context manager next to `encounter_resolved_span`:

```python
@contextmanager
def encounter_initiative_rolled_span(
    *,
    encounter_type: str,
    initiative_order: str,
    source: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_ENCOUNTER_INITIATIVE_ROLLED,
        {
            "encounter_type": encounter_type,
            "initiative_order": initiative_order,
            "source": source,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span
```

> If `SpanRoute`/`SPAN_ROUTES` are not in this module, match whatever registration the neighbouring spans use — do not invent a new mechanism. If the existing `encounter_resolved_span` takes no `_tracer` override in this codebase version, follow its exact signature and adapt the test's tracer injection to the established pattern (e.g. an `otel_capture` fixture) rather than forcing `_tracer`.

- [ ] **Step 4: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/telemetry/test_initiative_rolled_span.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/telemetry/spans/encounter.py tests/telemetry/test_initiative_rolled_span.py && git commit -m "feat(telemetry): encounter.initiative_rolled span (P4 polygraph)"
```

---

## Task 6: Roll + persist at the instantiation seam (+ drop redundant runtime check)

**Files:**
- Modify: `sidequest-server/sidequest/server/dispatch/encounter_lifecycle.py`
- Test: `sidequest-server/tests/server/test_space_opera_swn_combat_e2e.py` (extend — the sanctioned real-pack wiring vehicle)

- [ ] **Step 1: Add a helper that resolves per-actor DEX and rolls**

In `encounter_lifecycle.py`, add a module-level helper (near `_seed_combat_hp_depletion_to_npcs`):

```python
def _roll_and_persist_initiative(
    *,
    snapshot: GameSnapshot,
    enc: StructuredEncounter,
    actors: list[EncounterActor],
    cdef,
    pack: GenrePack,
) -> None:
    """SWN P4: roll 1d8+DEX once for player+opponent actors, persist on the
    encounter, emit the polygraph span. No-op for rulesets with no ordering.

    DEX is resolved at THIS seam because CreatureCore/Npc carry no ability
    scores: PCs from Character.stats[attribute_map['DEXTERITY']], opponents
    from the content `dexterity` reserved key (guaranteed present by the
    ConfrontationDef load-time validator). Fail loud on a missing PC score.
    """
    import random

    from sidequest.game.ruleset import get_ruleset_module
    from sidequest.telemetry.spans.encounter import encounter_initiative_rolled_span

    cfg = pack.rules.swn
    if cfg is None:
        return  # non-SWN ruleset: no ordering (native returns None anyway)

    dex_key = cfg.attribute_map.get("DEXTERITY")
    if dex_key is None:
        raise ValueError(
            "ruleset 'swn' but attribute_map has no DEXTERITY entry — "
            "RulesConfig validator should have caught this"
        )

    char_by_name = {c.core.name: c for c in snapshot.characters}
    actor_dex_scores: dict[str, int] = {}
    for actor in actors:
        if actor.side == "opponent":
            dex = cdef.opponent_dexterity
            if dex is None:
                raise ValueError(
                    f"opponent '{actor.name}' has no dexterity in "
                    f"opponent_default_stats for '{cdef.confrontation_type}' — "
                    "the load-time validator should have required it"
                )
            actor_dex_scores[actor.name] = int(dex)
        elif actor.side == "player":
            ch = char_by_name.get(actor.name)
            if ch is None:
                raise ValueError(
                    f"player actor '{actor.name}' not found among snapshot.characters "
                    "— cannot resolve DEX for initiative (no silent fallback)"
                )
            score = ch.stats.get(dex_key)
            if score is None:
                raise ValueError(
                    f"player '{actor.name}' stat block has no '{dex_key}' "
                    f"(DEXTERITY flavor) — cannot roll initiative (stats={sorted(ch.stats)})"
                )
            actor_dex_scores[actor.name] = int(score)
        # neutral actors do not act → excluded from initiative.

    ruleset = get_ruleset_module(pack.rules.ruleset)
    entries = ruleset.roll_initiative(actor_dex_scores=actor_dex_scores, rng=random.Random())
    if not entries:
        return
    enc.initiative = entries
    order_str = ", ".join(f"{e.token_id}({e.value})" for e in entries)
    with encounter_initiative_rolled_span(
        encounter_type=enc.encounter_type,
        initiative_order=order_str,
        source="instantiate",
    ):
        pass
```

- [ ] **Step 2: Call it from the seam, after seeding**

In `instantiate_encounter_from_trigger`, inside the `if cdef.win_condition == WinCondition.hp_depletion:` branch, immediately AFTER the `_seed_combat_hp_depletion_to_npcs(...)` call (~line 642), add:

```python
                _roll_and_persist_initiative(
                    snapshot=snapshot,
                    enc=enc,
                    actors=actors,
                    cdef=cdef,
                    pack=pack,
                )
```

- [ ] **Step 3: Drop the now-redundant runtime hp/ac check**

In `_seed_combat_hp_depletion_to_npcs`, remove the `if hp is None or ac is None: raise ValueError(...)` block (lines ~126-132). The `ConfrontationDef` load-time validator (Task 1) already guarantees `hp`/`armor_class`/`dexterity` are present for any combat hp_depletion confrontation that loads, so this runtime raise is dead. Keep the `hp = cdef.opponent_hp` / `ac = cdef.opponent_armor_class` reads.

- [ ] **Step 4: Write the failing wiring test (extend the e2e)**

In `tests/server/test_space_opera_swn_combat_e2e.py`, first ensure the player `_STATS` dict includes the DEXTERITY-flavor key. Check the `attribute_map` in `space_opera/rules.yaml` — DEXTERITY maps to `Reflex` — so add `"Reflex": 13` to `_STATS` if absent. Then add:

```python
def test_initiative_rolled_and_persisted_on_instantiation(otel_capture):
    """SWN P4: instantiating a combat hp_depletion confrontation rolls 1d8+DEX
    for player + opponent, persists the order, and fires the polygraph span."""
    enc = _instantiate_firefight()  # reuse the existing helper that calls
                                     # instantiate_encounter_from_trigger for the
                                     # personal-combat ("firefight"/combat) type
    assert enc is not None
    # Two-sided order: the player actor and the opponent actor both seated.
    names = {e.token_id for e in enc.initiative}
    assert len(enc.initiative) >= 2
    # Polygraph span fired.
    init_spans = [s for s in otel_capture.get_finished_spans()
                  if s.name == "encounter.initiative_rolled"]
    assert init_spans, "encounter.initiative_rolled span must fire on instantiation"
    assert init_spans[0].attributes["encounter_type"]
    assert init_spans[0].attributes["initiative_order"]
```

> If no `_instantiate_firefight()` helper exists, mirror the existing Test 1 setup (it already calls `instantiate_encounter_from_trigger` with a player whose stats are `_STATS`, `npcs_present` carrying the opponent on `side="opponent"`, and the real pack). Reuse that exact construction; do not invent a synthetic pack.

- [ ] **Step 5: Run it, verify it fails then passes**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs uv run pytest tests/server/test_space_opera_swn_combat_e2e.py -q`
Expected: the new test PASSES (initiative populated + span fired); the existing Tests 1-4 still PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/server/dispatch/encounter_lifecycle.py tests/server/test_space_opera_swn_combat_e2e.py && git commit -m "feat(encounter): roll+persist SWN initiative at instantiation seam; drop redundant runtime check (P4)"
```

---

## Task 7: Surface the order on the confrontation payload

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py` (`ConfrontationPayload`, ~line 759)
- Modify: `sidequest-server/sidequest/server/dispatch/confrontation.py` (`build_confrontation_payload`, ~line 99)
- Test: `sidequest-server/tests/server/test_confrontation_payload_initiative.py` (new)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_confrontation_payload_initiative.py`:

```python
"""SWN P4: the confrontation payload surfaces the initiative order so the table
sees it as a plain list (no 3D cup) — Sebastien/Jade legibility."""

from __future__ import annotations

from sidequest.game.encounter import EncounterActor, EncounterMetric, StructuredEncounter
from sidequest.genre.models.rules import ConfrontationDef, WinCondition
from sidequest.protocol.models import InitiativeEntry
from sidequest.server.dispatch.confrontation import build_confrontation_payload


def _cdef() -> ConfrontationDef:
    return ConfrontationDef(
        confrontation_type="firefight",
        label="Firefight",
        category="combat",
        win_condition=WinCondition.hp_depletion,
        opponent_default_stats={"hp": 7, "armor_class": 12, "dexterity": 13},
        beats=[{"id": "shoot", "label": "Shoot", "stat_check": "Physique", "base": 1, "kind": "strike"}],
    )


def _enc() -> StructuredEncounter:
    return StructuredEncounter(
        encounter_type="firefight",
        win_condition="hp_depletion",
        player_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
        opponent_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
        actors=[
            EncounterActor(name="Rux", role="attacker", side="player"),
            EncounterActor(name="Raider", role="attacker", side="opponent"),
        ],
        initiative=[
            InitiativeEntry(token_id="Rux", value=9),
            InitiativeEntry(token_id="Raider", value=5),
        ],
    )


def test_payload_carries_initiative_order():
    payload = build_confrontation_payload(encounter=_enc(), cdef=_cdef(), genre_slug="space_opera")
    assert payload["initiative_order"] == [
        {"name": "Rux", "roll": 9},
        {"name": "Raider", "roll": 5},
    ]


def test_payload_omits_initiative_when_empty():
    enc = _enc()
    enc.initiative = []
    payload = build_confrontation_payload(encounter=enc, cdef=_cdef(), genre_slug="space_opera")
    assert payload.get("initiative_order") in (None, [])
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/server/test_confrontation_payload_initiative.py -q`
Expected: FAIL — `build_confrontation_payload` returns no `initiative_order` key; `ConfrontationPayload` has no such field.

- [ ] **Step 3: Add the payload field**

In `sidequest/protocol/messages.py`, in `ConfrontationPayload` (after `opponent_hp` / `seq`, ~line 798):

```python
    # SWN P4: 1d8+DEX resolution order, rolled once at instantiation. Plain list
    # for the UI (no 3D dice overlay). None/empty for rulesets with no ordering.
    initiative_order: list[dict[str, int | str]] | None = None
```

- [ ] **Step 4: Populate it in `build_confrontation_payload`**

In `sidequest/server/dispatch/confrontation.py`, before `return payload` (~line 230), add:

```python
    if encounter.initiative:
        payload["initiative_order"] = [
            {"name": e.token_id, "roll": e.value} for e in encounter.initiative
        ]
```

- [ ] **Step 5: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/server/test_confrontation_payload_initiative.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/protocol/messages.py sidequest/server/dispatch/confrontation.py tests/server/test_confrontation_payload_initiative.py && git commit -m "feat(protocol): surface SWN initiative order on ConfrontationPayload (P4)"
```

---

## Task 8: Thread the order into the narrator turn input

**Files:**
- Modify: `sidequest-server/sidequest/handlers/player_action.py` (`dispatch_fired_barrier`, ~line 195)
- Test: `sidequest-server/tests/handlers/test_initiative_preamble.py` (new)

> The narrator must resolve committed actions in initiative order. We extract a pure preamble builder (unit-testable) and prepend it to `combined_action`.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/handlers/test_initiative_preamble.py`:

```python
"""SWN P4: the narrator turn input carries the engine-rolled initiative order as
the authoritative resolution sequence (math is engine-owned; narrator describes)."""

from __future__ import annotations

from sidequest.game.encounter import EncounterMetric, StructuredEncounter
from sidequest.handlers.player_action import initiative_preamble
from sidequest.protocol.models import InitiativeEntry


def _enc(initiative):
    return StructuredEncounter(
        encounter_type="firefight",
        player_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
        opponent_metric=EncounterMetric(name="hp", current=0, starting=0, threshold=1),
        initiative=initiative,
    )


def test_preamble_lists_order_and_states_the_rule():
    enc = _enc([
        InitiativeEntry(token_id="Rux", value=9),
        InitiativeEntry(token_id="Raider", value=5),
    ])
    text = initiative_preamble(enc)
    assert text is not None
    assert "Rux" in text and "Raider" in text
    assert text.index("Rux") < text.index("Raider")  # ordered
    assert "0 HP" in text  # the dead-actor-does-not-act rule statement (P5 enforces)


def test_preamble_none_when_no_initiative():
    assert initiative_preamble(_enc([])) is None
    assert initiative_preamble(None) is None
```

- [ ] **Step 2: Run it, verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/handlers/test_initiative_preamble.py -q`
Expected: FAIL — `ImportError: cannot import name 'initiative_preamble'`.

- [ ] **Step 3: Add the pure preamble builder**

In `sidequest/handlers/player_action.py`, add a module-level function (near the top, after imports):

```python
def initiative_preamble(encounter: object | None) -> str | None:
    """SWN P4: the authoritative resolution-order line for the narrator turn.

    Returns None when the encounter has no initiative (native rulesets, non-combat).
    The 'reduced to 0 HP' clause keeps the prose correct before P5's tool walk
    mechanically enforces dead_premise.
    """
    init = getattr(encounter, "initiative", None)
    if not init:
        return None
    order = ", ".join(f"{e.token_id}({e.value})" for e in init)
    return (
        f"[INITIATIVE ORDER] Resolve the committed actions strictly in this "
        f"1d8+DEX order: {order}. An actor reduced to 0 HP earlier in this "
        f"order does not act."
    )
```

- [ ] **Step 4: Wire it into `dispatch_fired_barrier`**

In `dispatch_fired_barrier`, where `combined_action` is built (~line 195), prepend the preamble sourced from the live encounter:

```python
    combined_action = "\n".join(f"{p.character_name}: {p.action}" for _, p in pending)
    _preamble = initiative_preamble(getattr(snapshot, "encounter", None))
    if _preamble is not None:
        combined_action = f"{_preamble}\n{combined_action}"
    turn_context.merged_player_actions = [(p.character_name, p.action) for _, p in pending]
```

- [ ] **Step 5: Run it, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-2/sidequest-server && uv run pytest tests/handlers/test_initiative_preamble.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && git add sidequest/handlers/player_action.py tests/handlers/test_initiative_preamble.py && git commit -m "feat(handlers): thread initiative order into narrator turn input (P4)"
```

---

## Task 9: Full gate + finish

**Files:** none (verification + integration)

- [ ] **Step 1: Run the full server suite + lint + types**

```bash
cd /Users/slabgorb/Projects/oq-2/sidequest-server && SIDEQUEST_GENRE_PACKS=/Users/slabgorb/Projects/oq-2/sidequest-content/genre_packs uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run pyright
```

Expected: all green except the KNOWN pre-existing failures (do NOT chase): `test_61_12_output_format_compaction`, `test_prompt_cache_attribution_otel`, `test_audit_namegen_corpora`, `tests/integration/test_dogfight_playtest_smoke.py`. If any OTHER test fails, it's a regression from this work — fix it before finishing.

- [ ] **Step 2: Confirm native packs are unchanged (characterization guard)**

Run the Spec-0 `native`-wrap characterization tests (locate via `grep -rl "native" tests/game/ruleset/`). Expected: green — `native` returns `None` from `roll_initiative` and no encounter outside SWN combat gets an initiative order.

- [ ] **Step 3: Finish via the finishing-a-development-branch skill**

Two repos. **Content PR merges FIRST** (the server e2e loads the pack at runtime). Use `env -u GITHUB_TOKEN` on every `gh` call. Per repo: push the branch, open a PR to `develop`, squash-merge, verify the merge landed. Server PR second.

- [ ] **Step 4: Update the epic-state memory**

Update `project_swn_module_epic_state.md`: P4 turn model (initiative spine) landed; note `dead_premise` was deferred into P5; record the opponent-`dexterity` reserved key + content authoring; note the tie-break SRD lookup is still a `TODO` pinned in `swn.roll_initiative`.

---

## Notes for the implementer

- **Never** `git stash`; **never** run tests on a prior commit to "prove" a pre-existing failure. The known-failing tests above are documented — leave them.
- The opponent `dexterity` values (ship 10, boarder 13) are feel-calibrated placeholders; Keith will tune them in a live playtest. Do not treat them as SRD-derived.
- `dead_premise` is **not** in this plan. If you find yourself adding a dead-premise branch, stop — it belongs in P5 (the narrator tool walk).
- The SRD tie-break rule is an open lookup (left as a `TODO` in `swn.roll_initiative`); the stable-sort default is acceptable until P5/the next SRD pass pins it into `SwnConfig`.
