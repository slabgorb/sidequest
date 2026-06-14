# F1a — Fate Resolution Primitive + Module Registration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a registered `fate` ruleset whose single resolution primitive resolves one Fate action (4dF + skill vs opposition → shifts → outcome tier), emitting an OTEL span — the foundation every later Fate slice builds on.

**Architecture:** A pure, side-effect-free resolver (`fate_resolution.py`) computes outcomes; the `FateRulesetModule` (`fate.py`) wraps it, emits the lie-detector span, and registers in the fail-loud registry. The d20/beat-shaped abstract methods raise fail-loud (Fate doesn't use that paradigm) until ADR-144 F5 demotes them to base default-raise. No conflict engine, no character facet, no narrator/UI yet — those are F1b–F1d.

**Tech Stack:** Python 3.14, pytest (`-n auto` via addopts), OpenTelemetry SDK, `uv`. **All paths below are under `sidequest-server/`.** Branch off `develop` (gitflow); feature branch `feat/f1a-fate-resolution`.

**Decision of record:** ADR-144. **Design:** `docs/superpowers/specs/2026-06-14-fate-core-binding-replaces-native-design.md` §4.1.

---

## F1 slice map (context — this plan is F1a only)

| Slice | Scope | Status |
|-------|-------|--------|
| **F1a** | Resolution primitive + module registration + OTEL | **this plan** |
| F1b | Fate character facet (aspects, skills, stunts, refresh, fate points, stress, consequences) + fate-point economy | next plan |
| F1c | `fate_conflict.py` exchange engine (sides, zones, turn order, four actions, stress/consequences, taken-out/concede) | next plan |
| F1d | Dispatch routing by `isinstance(module, FateRulesetModule)` + end-to-end wiring | next plan |

F1a is independently testable and mergeable: it adds a resolver and a registered module with no consumers in dispatch yet (F1d wires it). That is intentional — F1d is the wiring slice.

---

## File structure (F1a)

- **Create** `sidequest/game/ruleset/fate_resolution.py` — pure resolver: ladder, `FateTier`, `Opposition`, `FateOutcome`, `classify_outcome`, `roll_4df`, `resolve_action`.
- **Create** `sidequest/game/ruleset/fate.py` — `FateRulesetModule`.
- **Create** `sidequest/telemetry/spans/fate.py` — `fate_action_resolved_span`.
- **Modify** `sidequest/telemetry/spans/__init__.py` — re-export the span helper.
- **Modify** `sidequest/game/ruleset/registry.py` — register `FateRulesetModule`.
- **Create** `tests/game/ruleset/test_fate_resolution.py` — pure-resolver tests.
- **Create** `tests/game/ruleset/test_fate_module.py` — module behavior + fail-loud d20 surface.
- **Create** `tests/game/ruleset/test_fate_spans.py` — OTEL wiring test (drives the real registered module).
- **Modify** `tests/game/ruleset/test_registry.py` — add `fate` registration tests.

---

## Task 1: Pure resolution primitive

**Files:**
- Create: `sidequest/game/ruleset/fate_resolution.py`
- Test: `tests/game/ruleset/test_fate_resolution.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/ruleset/test_fate_resolution.py`:

```python
from __future__ import annotations

import random

import pytest

from sidequest.game.ruleset.fate_resolution import (
    FateOutcome,
    FateTier,
    Opposition,
    classify_outcome,
    ladder_name,
    resolve_action,
    roll_4df,
)


@pytest.mark.parametrize(
    "ladder_total,opposition,expected_shifts,expected_tier",
    [
        (3, 5, -2, FateTier.Fail),           # rolled under
        (5, 5, 0, FateTier.Tie),             # exactly met
        (6, 5, 1, FateTier.Succeed),         # +1 shift
        (7, 5, 2, FateTier.Succeed),         # +2 shifts
        (8, 5, 3, FateTier.SucceedWithStyle),  # +3 shifts
        (12, 5, 7, FateTier.SucceedWithStyle),
    ],
)
def test_classify_outcome(ladder_total, opposition, expected_shifts, expected_tier):
    shifts, tier = classify_outcome(ladder_total, opposition)
    assert shifts == expected_shifts
    assert tier is expected_tier


def test_roll_4df_is_four_fudge_dice():
    rng = random.Random(12345)
    for _ in range(200):
        dice = roll_4df(rng)
        assert len(dice) == 4
        assert all(d in (-1, 0, 1) for d in dice)
    # range of the sum is [-4, 4]
    sums = [sum(roll_4df(rng)) for _ in range(500)]
    assert min(sums) >= -4 and max(sums) <= 4


def test_resolve_action_invariants():
    rng = random.Random(7)
    opp = Opposition(value=2, kind="passive")
    outcome = resolve_action(skill_rating=3, opposition=opp, rng=rng, invoke_bonus=2)
    assert isinstance(outcome, FateOutcome)
    assert outcome.roll_total == sum(outcome.dice)
    assert outcome.ladder_total == outcome.roll_total + 3 + 2
    assert outcome.shifts == outcome.ladder_total - 2
    expected_shifts, expected_tier = classify_outcome(outcome.ladder_total, 2)
    assert outcome.shifts == expected_shifts
    assert outcome.tier is expected_tier


def test_ladder_name_known_and_out_of_band():
    assert ladder_name(0) == "Mediocre"
    assert ladder_name(4) == "Great"
    assert ladder_name(8) == "Legendary"
    assert ladder_name(9).startswith("Legendary")
    assert ladder_name(-3).startswith("Terrible")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_fate_resolution.py -n0 -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.ruleset.fate_resolution'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest/game/ruleset/fate_resolution.py`:

```python
"""Pure Fate Core resolution primitive (ADR-144, design §4.1).

4dF (four Fudge dice, each -1/0/+1) + a skill rating on the ladder, versus an
opposition value. Shifts = ladder_total - opposition; the tier follows from
shifts. Pure and side-effect-free — the module layer (fate.py) wraps this and
emits OTEL. Used by every Fate roll: conflict AND out-of-combat overcome /
create-advantage.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

#: The Fate ladder — adjective per integer rung.
LADDER: dict[int, str] = {
    -2: "Terrible",
    -1: "Poor",
    0: "Mediocre",
    1: "Average",
    2: "Fair",
    3: "Good",
    4: "Great",
    5: "Superb",
    6: "Fantastic",
    7: "Epic",
    8: "Legendary",
}


def ladder_name(value: int) -> str:
    """Adjective for a ladder value. Out-of-band values report the nearest
    named edge with an offset (the book encourages naming beyond Legendary)."""
    if value < -2:
        return f"Terrible{value + 2}"
    if value > 8:
        return f"Legendary+{value - 8}"
    return LADDER[value]


class FateTier(str, Enum):
    """The four Fate outcomes, by shift count."""

    Fail = "Fail"
    Tie = "Tie"
    Succeed = "Succeed"
    SucceedWithStyle = "SucceedWithStyle"


@dataclass(frozen=True)
class Opposition:
    """The number a roll must meet, plus how it arose (for OTEL and fiction).

    ``kind`` is ``"active"`` (an opponent rolled this total) or ``"passive"``
    (a set difficulty on the ladder). The math uses only ``value``.
    """

    value: int
    kind: str


@dataclass(frozen=True)
class FateOutcome:
    """One resolved Fate roll. ``dice`` are the raw 4dF faces."""

    dice: tuple[int, int, int, int]
    roll_total: int
    ladder_total: int
    opposition: int
    shifts: int
    tier: FateTier


def classify_outcome(ladder_total: int, opposition_value: int) -> tuple[int, FateTier]:
    """Shifts + tier for a ladder total vs an opposition value (pure)."""
    shifts = ladder_total - opposition_value
    if shifts < 0:
        tier = FateTier.Fail
    elif shifts == 0:
        tier = FateTier.Tie
    elif shifts <= 2:
        tier = FateTier.Succeed
    else:
        tier = FateTier.SucceedWithStyle
    return shifts, tier


def roll_4df(rng: random.Random) -> tuple[int, int, int, int]:
    """Roll four Fudge dice; each face is -1, 0, or +1."""
    return (
        rng.choice((-1, 0, 1)),
        rng.choice((-1, 0, 1)),
        rng.choice((-1, 0, 1)),
        rng.choice((-1, 0, 1)),
    )


def resolve_action(
    *,
    skill_rating: int,
    opposition: Opposition,
    rng: random.Random,
    invoke_bonus: int = 0,
) -> FateOutcome:
    """Resolve one Fate action. ``invoke_bonus`` is the net +2-per-invoke
    modifier already decided by the caller (reroll handling is a higher layer)."""
    dice = roll_4df(rng)
    roll_total = sum(dice)
    ladder_total = roll_total + skill_rating + invoke_bonus
    shifts, tier = classify_outcome(ladder_total, opposition.value)
    return FateOutcome(
        dice=dice,
        roll_total=roll_total,
        ladder_total=ladder_total,
        opposition=opposition.value,
        shifts=shifts,
        tier=tier,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_fate_resolution.py -n0 -q`
Expected: PASS (all 11 cases)

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/fate_resolution.py tests/game/ruleset/test_fate_resolution.py
git commit -m "feat(fate): pure 4dF resolution primitive (ADR-144 F1a)"
```

---

## Task 2: Fate OTEL span helper

**Files:**
- Create: `sidequest/telemetry/spans/fate.py`
- Modify: `sidequest/telemetry/spans/__init__.py`
- Test: covered by Task 4's wiring test (the span is exercised through the module).

- [ ] **Step 1: Write the span helper**

Create `sidequest/telemetry/spans/fate.py`:

```python
"""Fate ruleset OTEL spans (ADR-144). The GM panel is the lie detector: a Fate
roll that fired emits ``fate.action_resolved`` carrying the full math."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from sidequest.telemetry.spans.span import Span


def fate_action_resolved_span(
    *,
    actor: str,
    skill_rating: int,
    dice: tuple[int, int, int, int],
    ladder_total: int,
    opposition: int,
    opposition_kind: str,
    shifts: int,
    tier: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> None:
    """Emit ``fate.action_resolved`` — one Fate roll resolved."""
    attributes: dict[str, Any] = {
        "field": "action_resolved",
        "actor": actor,
        "skill_rating": skill_rating,
        "dice": ",".join(str(d) for d in dice),
        "ladder_total": ladder_total,
        "opposition": opposition,
        "opposition_kind": opposition_kind,
        "shifts": shifts,
        "tier": tier,
        **attrs,
    }
    with Span.open("fate.action_resolved", attributes, tracer_override=_tracer):
        pass
```

- [ ] **Step 2: Re-export from the package init**

In `sidequest/telemetry/spans/__init__.py`, add the import alongside the existing `wn_round` re-exports (match the file's existing style — find the `from sidequest.telemetry.spans.wn_round import (...)` block and add this near it):

```python
from sidequest.telemetry.spans.fate import fate_action_resolved_span
```

If the file maintains an `__all__`, append `"fate_action_resolved_span"` to it.

- [ ] **Step 3: Verify the import resolves**

Run: `uv run python -c "from sidequest.telemetry.spans import fate_action_resolved_span; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add sidequest/telemetry/spans/fate.py sidequest/telemetry/spans/__init__.py
git commit -m "feat(fate): fate.action_resolved OTEL span helper (ADR-144 F1a)"
```

---

## Task 3: FateRulesetModule

**Files:**
- Create: `sidequest/game/ruleset/fate.py`
- Test: `tests/game/ruleset/test_fate_module.py`

- [ ] **Step 1: Write the failing test**

Create `tests/game/ruleset/test_fate_module.py`:

```python
from __future__ import annotations

import random

import pytest

from sidequest.game.ruleset.fate import FateRulesetModule
from sidequest.game.ruleset.fate_resolution import FateOutcome, Opposition


def test_slug():
    assert FateRulesetModule.slug == "fate"


def test_fate_does_not_award_native_turn_xp():
    # Fate advances by milestones, not an XP tick (ADR-144).
    assert FateRulesetModule().awards_native_turn_xp is False


def test_resolve_action_returns_outcome():
    module = FateRulesetModule()
    outcome = module.resolve_action(
        skill_rating=2,
        opposition=Opposition(value=1, kind="passive"),
        rng=random.Random(3),
        actor="Detective",
    )
    assert isinstance(outcome, FateOutcome)
    assert outcome.shifts == outcome.ladder_total - 1


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.find_confrontation([], "fight"),
        lambda m: m.stat_modifier({}, "STRENGTH"),
        lambda m: m.compute_dc(None),
        lambda m: m.attack_params(
            beat=None, attacker_stats={}, attacker_core=None, target_core=None
        ),
        lambda m: m.resolve_damage(beat=None, actor_core=None, pack=None),
        lambda m: m.apply_beat(
            encounter=None,
            actor=None,
            beat=None,
            outcome=None,
            turn=0,
            edge_resolver=None,
            damage_resolver=None,
        ),
    ],
)
def test_d20_surface_fails_loud(call):
    # Fate's paradigm has no beats/DCs/d20 — these raise (No Silent Fallbacks)
    # until ADR-144 F5 demotes them to base default-raise.
    module = FateRulesetModule()
    with pytest.raises(NotImplementedError):
        call(module)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/ruleset/test_fate_module.py -n0 -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.ruleset.fate'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest/game/ruleset/fate.py`:

```python
"""FateRulesetModule — Fate Core behind the RulesetModule seam (ADR-144).

Resolution is 4dF + skill vs opposition on the ladder (see fate_resolution.py).
The d20/beat-shaped abstract methods are NOT part of Fate's paradigm; they fail
loud here (No Silent Fallbacks) until ADR-144 F5 demotes them to base
default-raise and these overrides are deleted. The Fate conflict engine
(fate_conflict.py) arrives in F1c; dispatch routing in F1d.
"""

from __future__ import annotations

import random

from sidequest.game.ruleset import fate_resolution
from sidequest.game.ruleset.base import RulesetModule
from sidequest.game.ruleset.fate_resolution import FateOutcome, Opposition
from sidequest.telemetry.spans import fate_action_resolved_span

_NO_D20_SURFACE = (
    "the 'fate' ruleset resolves via the Fate conflict engine (4dF + ladder), "
    "not the d20/beat surface — No Silent Fallbacks (ADR-144)"
)


class FateRulesetModule(RulesetModule):
    slug = "fate"

    @property
    def awards_native_turn_xp(self) -> bool:
        # Fate advances by milestones, not the ADR-021 native XP tick.
        return False

    def resolve_action(
        self,
        *,
        skill_rating: int,
        opposition: Opposition,
        rng: random.Random,
        invoke_bonus: int = 0,
        actor: str = "",
        _tracer=None,
    ) -> FateOutcome:
        """Resolve one Fate action and emit the lie-detector span."""
        outcome = fate_resolution.resolve_action(
            skill_rating=skill_rating,
            opposition=opposition,
            rng=rng,
            invoke_bonus=invoke_bonus,
        )
        fate_action_resolved_span(
            actor=actor,
            skill_rating=skill_rating,
            dice=outcome.dice,
            ladder_total=outcome.ladder_total,
            opposition=outcome.opposition,
            opposition_kind=opposition.kind,
            shifts=outcome.shifts,
            tier=outcome.tier.value,
            _tracer=_tracer,
        )
        return outcome

    # --- d20/beat surface: not Fate's paradigm (fail loud until F5 re-cut) ---

    def find_confrontation(self, confrontations, encounter_type):
        raise NotImplementedError(_NO_D20_SURFACE)

    def stat_modifier(self, stats, stat_check):
        raise NotImplementedError(_NO_D20_SURFACE)

    def compute_dc(self, beat):
        raise NotImplementedError(_NO_D20_SURFACE)

    def apply_beat(self, *, encounter, actor, beat, outcome, turn, edge_resolver, damage_resolver):
        raise NotImplementedError(_NO_D20_SURFACE)

    def resolve_damage(self, *, beat, actor_core, pack, world_slug=None):
        raise NotImplementedError(_NO_D20_SURFACE)

    def attack_params(self, *, beat, attacker_stats, attacker_core, target_core):
        raise NotImplementedError(_NO_D20_SURFACE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/ruleset/test_fate_module.py -n0 -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/fate.py tests/game/ruleset/test_fate_module.py
git commit -m "feat(fate): FateRulesetModule with fail-loud d20 surface (ADR-144 F1a)"
```

---

## Task 4: Register in the fail-loud registry + OTEL wiring test

**Files:**
- Modify: `sidequest/game/ruleset/registry.py`
- Modify: `tests/game/ruleset/test_registry.py`
- Test: `tests/game/ruleset/test_fate_spans.py`

- [ ] **Step 1: Write the failing registry + wiring tests**

Append to `tests/game/ruleset/test_registry.py`:

```python
def test_fate_registered_and_singleton():
    from sidequest.game.ruleset.fate import FateRulesetModule
    from sidequest.game.ruleset.registry import get_ruleset_module

    module = get_ruleset_module("fate")
    assert isinstance(module, FateRulesetModule)
    assert module.slug == "fate"
    assert get_ruleset_module("fate") is module  # stateless singleton


def test_unknown_ruleset_still_fails_loud_after_fate():
    # Registering "fate" must not introduce a silent default (No Silent Fallbacks).
    with pytest.raises(UnknownRulesetError) as exc:
        get_ruleset_module("fudge")  # close to "fate" but not registered
    assert "fudge" in str(exc.value)
```

Create `tests/game/ruleset/test_fate_spans.py` (the wiring test — drives the REAL registered module through the production span helper, per server CLAUDE.md "OTEL span assertions"):

```python
"""OTEL wiring net for the Fate module (ADR-144 F1a).

Drives the real registered FateRulesetModule.resolve_action and asserts the
fate.action_resolved span fired with the resolved math. Exporter pattern matches
test_142_wn_lethality_spans.py: a local InMemorySpanExporter passed in as
_tracer so spans land locally regardless of global provider state.
"""

from __future__ import annotations

import random

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sidequest.game.ruleset import get_ruleset_module
from sidequest.game.ruleset.fate_resolution import Opposition


def _exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider.get_tracer("test")


def test_resolve_action_emits_fate_action_resolved_span():
    exporter, tracer = _exporter()
    module = get_ruleset_module("fate")  # production resolution path

    module.resolve_action(
        skill_rating=3,
        opposition=Opposition(value=2, kind="passive"),
        rng=random.Random(1),
        actor="Sleuth",
        _tracer=tracer,
    )

    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "fate.action_resolved" in names

    span = next(s for s in spans if s.name == "fate.action_resolved")
    assert span.attributes["actor"] == "Sleuth"
    assert span.attributes["skill_rating"] == 3
    assert span.attributes["opposition"] == 2
    assert span.attributes["opposition_kind"] == "passive"
    assert span.attributes["tier"] in {"Fail", "Tie", "Succeed", "SucceedWithStyle"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/game/ruleset/test_registry.py::test_fate_registered_and_singleton tests/game/ruleset/test_fate_spans.py -n0 -q`
Expected: FAIL — `UnknownRulesetError: Unknown ruleset 'fate'` (registry test) and the same when the wiring test calls `get_ruleset_module("fate")`.

- [ ] **Step 3: Register the module**

In `sidequest/game/ruleset/registry.py`, add the import (alphabetical, after `cwn`) and the registry entry:

```python
from sidequest.game.ruleset.fate import FateRulesetModule
```

```python
_REGISTRY: dict[str, RulesetModule] = {
    NativeRulesetModule.slug: NativeRulesetModule(),
    SwnRulesetModule.slug: SwnRulesetModule(),
    CwnRulesetModule.slug: CwnRulesetModule(),
    WwnRulesetModule.slug: WwnRulesetModule(),
    AwnRulesetModule.slug: AwnRulesetModule(),
    FateRulesetModule.slug: FateRulesetModule(),
}
```

(Note: the registry is a plain module-level dict literal — importing `registry.py` builds it. No decorator side-effect, so no subprocess test is needed here, unlike the MAGIC_PLUGINS/SPAN_ROUTES registries.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/game/ruleset/test_registry.py tests/game/ruleset/test_fate_spans.py -n0 -q`
Expected: PASS (the whole registry file, including the new fate cases, plus the wiring test)

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/ruleset/registry.py tests/game/ruleset/test_registry.py tests/game/ruleset/test_fate_spans.py
git commit -m "feat(fate): register fate module + OTEL wiring test (ADR-144 F1a)"
```

---

## Task 5: Gate — lint, types, full ruleset suite

**Files:** none (verification only)

- [ ] **Step 1: Lint the new files**

Run: `uv run ruff check sidequest/game/ruleset/fate.py sidequest/game/ruleset/fate_resolution.py sidequest/telemetry/spans/fate.py tests/game/ruleset/test_fate_resolution.py tests/game/ruleset/test_fate_module.py tests/game/ruleset/test_fate_spans.py`
Expected: `All checks passed!`

- [ ] **Step 2: Format the new files (scoped — do NOT format the repo)**

Run: `uv run ruff format sidequest/game/ruleset/fate.py sidequest/game/ruleset/fate_resolution.py sidequest/telemetry/spans/fate.py tests/game/ruleset/test_fate_resolution.py tests/game/ruleset/test_fate_module.py tests/game/ruleset/test_fate_spans.py`
Expected: files left unchanged or reformatted in place (commit any reformat).

- [ ] **Step 3: Type check**

Run: `uv run pyright sidequest/game/ruleset/fate.py sidequest/game/ruleset/fate_resolution.py sidequest/telemetry/spans/fate.py`
Expected: `0 errors`

- [ ] **Step 4: Run the full ruleset suite (no regressions to native/WN)**

Run: `uv run pytest tests/game/ruleset/ -q`
Expected: PASS — all pre-existing ruleset tests still green; the new fate tests included.

- [ ] **Step 5: Commit any format/lint fixups**

```bash
git add -p
git commit -m "chore(fate): lint/format/type fixups (ADR-144 F1a)"
```

---

## Self-review (done against the spec)

- **Spec §4.1 coverage:** resolution primitive (`resolve_action`, 4dF, ladder, shifts→tier) — Task 1; `FateRulesetModule` slug + paradigm-only surface — Task 3; registry — Task 4. ✓
- **Spec §6 OTEL:** `fate.action_resolved` consolidates the inventory's `fate.roll` + `fate.outcome` into one span carrying dice + rating + opposition + shifts + tier — Task 2/4. (Per-subsystem economy/consequence spans arrive with F1b/F1c.) ✓
- **Spec §7 wiring test:** OTEL span assertion through the real registered module, not a source grep — Task 4. Registry resolution + fail-loud preserved — Task 4. ✓
- **No Stubbing / No Silent Fallbacks:** the d20 surface raises with a specific message; it is a fail-loud paradigm declaration, scheduled for removal at F5, not a silent stub. ✓
- **Placeholder scan:** none — every code/command step is concrete.
- **Type consistency:** `Opposition`, `FateOutcome`, `FateTier`, `resolve_action`, `roll_4df`, `classify_outcome`, `ladder_name`, `fate_action_resolved_span` names are identical across all tasks. ✓
- **Out of F1a scope (correct):** conflict engine, character facet, fate-point economy, dispatch routing, 4dF UI overlay — F1b–F1d / F3.
```
