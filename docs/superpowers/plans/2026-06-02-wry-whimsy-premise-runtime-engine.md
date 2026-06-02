# wry_whimsy Premise/Bloc Runtime Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the wry_whimsy political substrate *live*: hydrate runtime `PremiseState`/`BlocState` dials onto the session snapshot from the Plan-1 content, and apply witnessed acts that drain a Premise's belief, soft-couple defiance into propping Blocs, fire collapse/tip thresholds, inject contradicting beliefs via ADR-053, and emit OTEL — all behind a registered `witnessed_act` dispatch subsystem reachable through the production dispatch bank.

**Architecture:** Plan 1 shipped the content schema (`PremiseDef`/`BlocDef`/`witnessed_acts.yaml`) with **no runtime behavior**. This plan adds: (1) a runtime `PoliticalState` container on `GameSnapshot` (mutable dials + a provenance ledger), hydrated at chargen-confirm; (2) a pure `apply_witnessed_act` engine (the spec §5 causal chain, soft-coupling per §4.4); (3) ADR-053 reuse — a witnessed act injects a contradicting `BeliefFact` into witness NPCs so the existing `GossipEngine` can later spread it; (4) a `witnessed_act` dispatch subsystem (ADR-113/123) with a precondition gate; (5) OTEL spans so the GM panel can lie-detect the political layer. The `belief_reserve`/`defiance` numbers are **authoritative aggregate dials** (spec §4.4/§11) — *not* a roll-up over per-NPC `BeliefState`; the fixed-pool conservation law stays a deferred v2 spike.

**Tech Stack:** Python 3.12+, pydantic v2, `uv`/`pytest`, OpenTelemetry. Touches `sidequest-server` only (plus one small `sidequest-content` tuning value). Follows project rules **No Silent Fallbacks**, **No Stubbing**, **Don't Reinvent — Wire Up What Exists** (reuses ADR-053 belief layer + the ADR-123 dispatch bank), **Every Test Suite Needs a Wiring Test**, and the **OTEL Observability Principle**.

---

## Plan Series Context (read before starting)

This is Plan 2 of the wry_whimsy political-substrate series (spec `docs/superpowers/specs/2026-06-02-wry-whimsy-premise-belief-flow-design.md`). **Plan 1 (content schema + loader) must be merged first** — this plan imports `PremiseDef`/`BlocDef` and reads `World.premises`/`World.blocs` + `GenrePack.witnessed_acts`.

| # | Plan | Depends on | This plan's relationship |
|---|------|-----------|--------------------------|
| 1 | Content schema + loader | — | **Prerequisite** (merged: server PR #580, content PR #331) |
| **2** | **Runtime engine — mechanical spine (THIS PLAN)** | 1 | Hydration + apply-engine + belief injection + OTEL + registered `witnessed_act` subsystem. Reachable through the production bank; proven by a synthetic-dispatch integration test. |
| 2b | Intent-router classification | 2 | Teach the LLM router to *emit* `witnessed_act` (prompt + surface the act vocabulary into the router state summary). Split out because it is non-deterministic LLM-prompt work evaluated by playtest/eval, not unit assertions. **Until 2b lands, the subsystem is reachable through the bank/tests but not yet player-triggerable via natural language.** |
| 3 | Confrontation integration ("Refuse the Premise"/"Expose the Humbug") | 2 | Victory fires the same `apply_witnessed_act` path (no new VictoryMoveDef). |
| 4 | UI Standing panel | 2 | Projects `PoliticalState` (belief/defiance bars + the ledger) to the client. |
| 5 | Spectacles toggle | 2 (+UX spike) | Net-new illusion render. |

**Decisions locked here:** `belief_reserve`/`defiance` are authoritative dials (no population roll-up in v1). Soft coupling (§4.4): a drained Premise routes `COUPLING_FRACTION` of the drain into its propping Blocs' defiance; the rest dissipates. A witnessed act with **no witness moves nothing** (spec §5). Every belief/defiance change emits OTEL (CLAUDE.md OTEL principle) — addressing the Plan-1 reviewer's carry-forward note.

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `sidequest-server/sidequest/game/political_state.py` | Runtime models: `PoliticalState`, `PremiseState`, `BlocState`, `BeliefLedgerEntry` + `from_world` hydration | **Create** |
| `sidequest-server/sidequest/game/session.py` | Add `political_state` field to `GameSnapshot` | **Modify** |
| `sidequest-server/sidequest/telemetry/spans/premise.py` | OTEL span constants + routes | **Create** |
| `sidequest-server/sidequest/telemetry/spans/__init__.py` | Aggregate the new span routes | **Modify** |
| `sidequest-server/sidequest/game/political_engine.py` | `apply_witnessed_act` engine + `inject_witnessed_contradiction` (ADR-053 reuse) | **Create** |
| `sidequest-server/sidequest/server/dispatch/premise_bind.py` | `bind_political_state` hydration hook | **Create** |
| `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py` | Call `bind_political_state` after `bind_scenario` (both sites) | **Modify** |
| `sidequest-server/sidequest/agents/subsystems/witnessed_act.py` | `run_witnessed_act_dispatch` handler + OTEL emit | **Create** |
| `sidequest-server/sidequest/agents/subsystems/__init__.py` | Register `witnessed_act` | **Modify** |
| `sidequest-server/sidequest/agents/dispatch_precondition_gate.py` | `witnessed_act` precondition (inert if no `political_state`) | **Modify** |
| `sidequest-content/genre_packs/wry_whimsy/rules.yaml` | `dispatch_confidence_thresholds.witnessed_act: 0.7` (earned acts) | **Modify** |
| Tests | one per unit + the integration wiring test | **Create** |

Server commands run from `sidequest-server/`. Single test: `uv run pytest tests/<path>::<name> -v`.

**Branching:** work on a feature branch off `origin/develop` in each touched subrepo (per the dual-clone hazard — never commit on `develop`). Suggested: `feat/wry-whimsy-premise-runtime`.

---

### Task 1: Runtime state models + hydration + snapshot field

**Files:**
- Create: `sidequest-server/sidequest/game/political_state.py`
- Modify: `sidequest-server/sidequest/game/session.py` (add `political_state` to `GameSnapshot`)
- Test: `sidequest-server/tests/game/test_political_state.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_political_state.py`:

```python
"""Runtime PoliticalState models + hydration (Plan 2, Task 1)."""

from __future__ import annotations

from types import SimpleNamespace

from sidequest.game.political_state import (
    BeliefLedgerEntry,
    BlocState,
    PoliticalState,
    PremiseState,
)


def _world(premises, blocs):
    # Duck-typed stand-in for a genre World (only .premises/.blocs are read).
    return SimpleNamespace(premises=premises, blocs=blocs)


def _premise_def(premise_id="p1", belief_reserve=90):
    return SimpleNamespace(premise_id=premise_id, belief_reserve=belief_reserve)


def _bloc_def(bloc_id="b1", defiance=5):
    return SimpleNamespace(bloc_id=bloc_id, defiance=defiance)


def test_from_world_seeds_live_dials_from_content():
    state = PoliticalState.from_world(
        _world([_premise_def("the_wizards_humbug", 90)], [_bloc_def("munchkins", 5)])
    )
    assert state is not None
    assert state.premises["the_wizards_humbug"].belief_reserve == 90
    assert state.premises["the_wizards_humbug"].collapsed is False
    assert state.blocs["munchkins"].defiance == 5
    assert state.blocs["munchkins"].tipped is False
    assert state.ledger == []


def test_from_world_returns_none_when_no_politics():
    # A world with no premises/blocs is a valid authoring choice — NOT an error,
    # and NOT an empty container. None keeps the precondition gate honest.
    assert PoliticalState.from_world(_world([], [])) is None


def test_ledger_entry_round_trips():
    e = BeliefLedgerEntry(
        turn=3,
        act_id="expose_the_humbug",
        target_id="the_wizards_humbug",
        target_kind="premise",
        effect="drained",
        delta=-35,
        new_value=55,
        witnesses=["Dorothy", "Toto"],
    )
    assert e.delta == -35
    assert e.witnesses == ["Dorothy", "Toto"]


def test_political_state_serializes_round_trip():
    state = PoliticalState(
        premises={"p1": PremiseState(premise_id="p1", belief_reserve=40, collapsed=False)},
        blocs={"b1": BlocState(bloc_id="b1", defiance=20, tipped=False)},
        ledger=[],
    )
    dumped = state.model_dump_json()
    restored = PoliticalState.model_validate_json(dumped)
    assert restored.premises["p1"].belief_reserve == 40
    assert restored.blocs["b1"].defiance == 20


def test_snapshot_carries_optional_political_state():
    # Wiring: GameSnapshot must hold the runtime state and default to None
    # (a save from before this feature, or a world with no politics).
    from sidequest.game.session import GameSnapshot

    snap = GameSnapshot()
    assert snap.political_state is None
    snap.political_state = PoliticalState(
        premises={"p1": PremiseState(premise_id="p1", belief_reserve=10)},
        blocs={},
        ledger=[],
    )
    restored = GameSnapshot.model_validate_json(snap.model_dump_json())
    assert restored.political_state is not None
    assert restored.political_state.premises["p1"].belief_reserve == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_political_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.political_state'`

- [ ] **Step 3: Create the runtime models**

Create `sidequest-server/sidequest/game/political_state.py`:

```python
"""Runtime political state for the wry_whimsy substrate (Plan 2).

Live, mutable dials hydrated from the Plan-1 content (``PremiseDef``/``BlocDef``):
``belief_reserve`` (an authority's power) and ``defiance`` (a population's
willingness to act). These are AUTHORITATIVE aggregate dials per spec §4.4/§11
— not a roll-up over per-NPC ``BeliefState``. The ledger is the provenance trail
(which act, which witnesses, which turn) for OTEL and the future Standing panel.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PremiseState(BaseModel):
    """Live dial for one authority's sustaining illusion."""

    model_config = {"extra": "forbid"}

    premise_id: str
    belief_reserve: int
    collapsed: bool = False


class BlocState(BaseModel):
    """Live dial for one population the outsider can move."""

    model_config = {"extra": "forbid"}

    bloc_id: str
    defiance: int
    tipped: bool = False


class BeliefLedgerEntry(BaseModel):
    """One recorded change to a dial — the receipt the world keeps (spec §6)."""

    model_config = {"extra": "forbid"}

    turn: int
    act_id: str
    target_id: str
    target_kind: str  # "premise" | "bloc"
    effect: str  # "drained" | "coupled" | "awakened" | "collapsed" | "tipped"
    delta: int  # signed change applied (0 for collapse/tip markers)
    new_value: int  # belief_reserve or defiance after the change
    witnesses: list[str] = Field(default_factory=list)


class PoliticalState(BaseModel):
    """Container for a session's live premises, blocs, and provenance ledger."""

    model_config = {"extra": "forbid"}

    premises: dict[str, PremiseState] = Field(default_factory=dict)
    blocs: dict[str, BlocState] = Field(default_factory=dict)
    ledger: list[BeliefLedgerEntry] = Field(default_factory=list)

    @classmethod
    def from_world(cls, world: Any) -> "PoliticalState | None":
        """Hydrate live dials from a genre ``World``'s authored premises/blocs.

        Returns ``None`` when the world authors no political layer — a valid
        authoring choice (NOT an empty container, NOT a fallback). ``None`` is
        what the precondition gate keys on to make ``witnessed_act`` inert.
        """
        premises = list(getattr(world, "premises", None) or [])
        blocs = list(getattr(world, "blocs", None) or [])
        if not premises and not blocs:
            return None
        return cls(
            premises={
                p.premise_id: PremiseState(
                    premise_id=p.premise_id, belief_reserve=p.belief_reserve
                )
                for p in premises
            },
            blocs={
                b.bloc_id: BlocState(bloc_id=b.bloc_id, defiance=b.defiance)
                for b in blocs
            },
            ledger=[],
        )
```

- [ ] **Step 4: Add the field to `GameSnapshot`**

In `sidequest-server/sidequest/game/session.py`:

(4a) Add the import near the other `from sidequest.game.* import` lines:

```python
from sidequest.game.political_state import PoliticalState
```

(4b) Find the `scenario_state` field on `GameSnapshot` (anchor: `scenario_state: ScenarioState | None = None`, ~line 804) and insert immediately after it:

```python
    # Political substrate (wry_whimsy, Plan 2). Hydrated at chargen-confirm
    # when the active world declares premises/blocs (spec 2026-06-02); None
    # when the world ships no political layer — a valid authoring choice, the
    # precondition-gate signal that makes witnessed_act inert. Old saves
    # deserialize to None (model_config extra="ignore").
    political_state: PoliticalState | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/game/test_political_state.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/political_state.py sidequest/game/session.py tests/game/test_political_state.py
git commit -m "feat(game): runtime PoliticalState dials on the snapshot, hydrated from world content"
```

---

### Task 2: OTEL spans for the political layer

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/premise.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py`
- Test: `sidequest-server/tests/telemetry/test_premise_spans.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_premise_spans.py`:

```python
"""Premise/Bloc OTEL span routes are registered (Plan 2, Task 2)."""

from __future__ import annotations


def test_premise_span_constants_exported_and_routed():
    from sidequest.telemetry.spans import (
        SPAN_BLOC_DEFIANCE_RAISED,
        SPAN_BLOC_TIPPED,
        SPAN_PREMISE_BELIEF_DRAINED,
        SPAN_PREMISE_COLLAPSED,
    )
    from sidequest.telemetry.spans._core import SPAN_ROUTES

    for name in (
        SPAN_PREMISE_BELIEF_DRAINED,
        SPAN_BLOC_DEFIANCE_RAISED,
        SPAN_PREMISE_COLLAPSED,
        SPAN_BLOC_TIPPED,
    ):
        assert name in SPAN_ROUTES, f"{name} not registered in SPAN_ROUTES"


def test_belief_drained_route_extracts_fields():
    from sidequest.telemetry.spans import SPAN_PREMISE_BELIEF_DRAINED
    from sidequest.telemetry.spans._core import SPAN_ROUTES

    route = SPAN_ROUTES[SPAN_PREMISE_BELIEF_DRAINED]
    assert route.component == "premise"

    class _FakeSpan:
        attributes = {
            "premise_id": "the_wizards_humbug",
            "act_id": "expose_the_humbug",
            "delta": -35,
            "new_reserve": 55,
            "witnesses": "Dorothy,Toto",
            "turn": 3,
        }

    fields = route.extract(_FakeSpan())
    assert fields["premise_id"] == "the_wizards_humbug"
    assert fields["new_reserve"] == 55
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_premise_spans.py -v`
Expected: FAIL — `ImportError: cannot import name 'SPAN_PREMISE_BELIEF_DRAINED'`

- [ ] **Step 3: Create the span-route module**

Create `sidequest-server/sidequest/telemetry/spans/premise.py`:

```python
"""Premise/Bloc political-substrate spans (wry_whimsy, Plan 2).

Every belief/defiance change emits one of these so the GM panel is the
lie-detector for the political layer too (CLAUDE.md OTEL principle): a real
revolution writes these spans; narrated improvisation does not.
"""

from __future__ import annotations

from ._core import SPAN_ROUTES, SpanRoute

__all__ = [
    "SPAN_PREMISE_BELIEF_DRAINED",
    "SPAN_BLOC_DEFIANCE_RAISED",
    "SPAN_PREMISE_COLLAPSED",
    "SPAN_BLOC_TIPPED",
]

SPAN_PREMISE_BELIEF_DRAINED = "premise.belief_drained"
SPAN_BLOC_DEFIANCE_RAISED = "bloc.defiance_raised"
SPAN_PREMISE_COLLAPSED = "premise.collapsed"
SPAN_BLOC_TIPPED = "bloc.tipped"

SPAN_ROUTES[SPAN_PREMISE_BELIEF_DRAINED] = SpanRoute(
    event_type="state_transition",
    component="premise",
    extract=lambda span: {
        "field": "premise.belief_drained",
        "premise_id": (span.attributes or {}).get("premise_id", ""),
        "act_id": (span.attributes or {}).get("act_id", ""),
        "delta": (span.attributes or {}).get("delta", 0),
        "new_reserve": (span.attributes or {}).get("new_reserve", 0),
        "witnesses": (span.attributes or {}).get("witnesses", ""),
        "turn": (span.attributes or {}).get("turn", 0),
    },
)

SPAN_ROUTES[SPAN_BLOC_DEFIANCE_RAISED] = SpanRoute(
    event_type="state_transition",
    component="bloc",
    extract=lambda span: {
        "field": "bloc.defiance_raised",
        "bloc_id": (span.attributes or {}).get("bloc_id", ""),
        "act_id": (span.attributes or {}).get("act_id", ""),
        "source": (span.attributes or {}).get("source", ""),
        "delta": (span.attributes or {}).get("delta", 0),
        "new_defiance": (span.attributes or {}).get("new_defiance", 0),
        "turn": (span.attributes or {}).get("turn", 0),
    },
)

SPAN_ROUTES[SPAN_PREMISE_COLLAPSED] = SpanRoute(
    event_type="state_transition",
    component="premise",
    extract=lambda span: {
        "field": "premise.collapsed",
        "premise_id": (span.attributes or {}).get("premise_id", ""),
        "new_reserve": (span.attributes or {}).get("new_reserve", 0),
        "turn": (span.attributes or {}).get("turn", 0),
    },
)

SPAN_ROUTES[SPAN_BLOC_TIPPED] = SpanRoute(
    event_type="state_transition",
    component="bloc",
    extract=lambda span: {
        "field": "bloc.tipped",
        "bloc_id": (span.attributes or {}).get("bloc_id", ""),
        "new_defiance": (span.attributes or {}).get("new_defiance", 0),
        "turn": (span.attributes or {}).get("turn", 0),
    },
)
```

- [ ] **Step 4: Aggregate in `__init__.py`**

In `sidequest-server/sidequest/telemetry/spans/__init__.py`, add a star-import for the new module alongside the other `from .<domain> import *` lines, in alphabetical order (i.e. place `from .premise import *` before `from .prompt import *` / after `.movement`/`.npc` — match the existing ordering in the file):

```python
from .premise import *  # noqa: F401, F403
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/telemetry/test_premise_spans.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/premise.py sidequest/telemetry/spans/__init__.py tests/telemetry/test_premise_spans.py
git commit -m "feat(telemetry): premise/bloc OTEL span routes for the political layer"
```

---

### Task 3: The `apply_witnessed_act` engine

**Files:**
- Create: `sidequest-server/sidequest/game/political_engine.py`
- Test: `sidequest-server/tests/game/test_political_engine.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_political_engine.py`:

```python
"""apply_witnessed_act engine — drain, couple, awaken, thresholds (Plan 2, Task 3)."""

from __future__ import annotations

from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.game.political_engine import COUPLING_FRACTION, apply_witnessed_act
from sidequest.game.political_state import BlocState, PoliticalState, PremiseState


def _humbug():
    return PremiseDef(
        premise_id="humbug",
        authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="great and terrible"),
        belief_reserve=90,
        propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose", belief_delta=40)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )


def _munchkins(defiance=0, awaken_delta=10):
    return BlocDef(
        bloc_id="munchkins",
        defiance=defiance,
        grants_belief_to=["humbug"],
        awakening_acts=[BlocAwakening(act="rally", defiance_delta=awaken_delta)],
        tipping_threshold=70,
        tipped_outcome="They revolt.",
    )


def _state(reserve=90, defiance=0):
    return PoliticalState(
        premises={"humbug": PremiseState(premise_id="humbug", belief_reserve=reserve)},
        blocs={"munchkins": BlocState(bloc_id="munchkins", defiance=defiance)},
        ledger=[],
    )


def test_drain_reduces_belief_and_soft_couples_defiance():
    state = _state(reserve=90, defiance=0)
    events = apply_witnessed_act(
        state=state,
        premises=[_humbug()],
        blocs=[_munchkins()],
        act_id="expose",
        witnesses=["Dorothy"],
        turn=1,
    )
    assert state.premises["humbug"].belief_reserve == 50  # 90 - 40
    # soft coupling: floor(40 * COUPLING_FRACTION) into the propping bloc
    assert state.blocs["munchkins"].defiance == int(40 * COUPLING_FRACTION)
    effects = {e.effect for e in events}
    assert "drained" in effects and "coupled" in effects
    # ledger keeps the receipt with the witness
    assert any(le.effect == "drained" and le.witnesses == ["Dorothy"] for le in state.ledger)


def test_awakening_act_raises_defiance_directly():
    state = _state(defiance=0)
    apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins(awaken_delta=15)],
        act_id="rally", witnesses=["Dorothy"], turn=1,
    )
    assert state.blocs["munchkins"].defiance == 15  # awakened, no premise drain (act != drained_by)
    assert state.premises["humbug"].belief_reserve == 90


def test_belief_clamps_at_zero_and_collapse_fires_once():
    state = _state(reserve=30)
    events = apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins()],
        act_id="expose", witnesses=["Dorothy"], turn=1,
    )
    assert state.premises["humbug"].belief_reserve == 0  # 30-40 clamped
    assert state.premises["humbug"].collapsed is True
    collapse_events = [e for e in events if e.effect == "collapsed"]
    assert len(collapse_events) == 1
    assert collapse_events[0].detail == "He flees."
    # collapsed premise does not drain again
    again = apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins()],
        act_id="expose", witnesses=["Dorothy"], turn=2,
    )
    assert not any(e.effect == "drained" for e in again)


def test_bloc_tips_when_defiance_crosses_threshold():
    state = _state(defiance=60)
    events = apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins(defiance=60, awaken_delta=15)],
        act_id="rally", witnesses=["Dorothy"], turn=1,
    )
    assert state.blocs["munchkins"].defiance == 75
    assert state.blocs["munchkins"].tipped is True
    tip = [e for e in events if e.effect == "tipped"]
    assert len(tip) == 1 and tip[0].detail == "They revolt."


def test_unmatched_act_is_a_noop():
    state = _state()
    events = apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins()],
        act_id="not_an_act", witnesses=["Dorothy"], turn=1,
    )
    assert events == []
    assert state.premises["humbug"].belief_reserve == 90
    assert state.ledger == []


def test_coupling_can_tip_a_propping_bloc():
    # Soft coupling alone can push a bloc over the line — caught by the final pass.
    state = _state(reserve=90, defiance=69)
    apply_witnessed_act(
        state=state, premises=[_humbug()], blocs=[_munchkins(defiance=69)],
        act_id="expose", witnesses=["Dorothy"], turn=1,
    )
    # coupled += floor(40*0.5)=20 → 89 ≥ 70
    assert state.blocs["munchkins"].tipped is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_political_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.political_engine'`

- [ ] **Step 3: Write the engine**

Create `sidequest-server/sidequest/game/political_engine.py`:

```python
"""The belief-flow engine for the wry_whimsy political substrate (Plan 2, spec §5).

Pure logic: given the live ``PoliticalState`` dials, the world's content defs,
and one classified witnessed act, mutate the dials and return the ordered list
of events. No I/O, no snapshot, no OTEL — the caller (the dispatch subsystem)
records the ledger-derived spans and the narrator directive. This keeps the
causal math unit-testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass

from sidequest.game.political_state import BeliefLedgerEntry, PoliticalState
from sidequest.genre.models.premises import BlocDef, PremiseDef

# Spec §4.4 soft conservation: a drained Premise routes this fraction of the
# drain into its propping Blocs' defiance; the remainder dissipates. A tuning
# knob, NOT a hard physics law (the fixed-pool conservation law is a v2 spike).
COUPLING_FRACTION = 0.5


@dataclass
class PoliticalEvent:
    """One applied change, for OTEL + the narrator directive."""

    effect: str  # "drained" | "coupled" | "awakened" | "collapsed" | "tipped"
    target_kind: str  # "premise" | "bloc"
    target_id: str
    delta: int  # signed change (0 for collapse/tip markers)
    new_value: int
    detail: str = ""  # collapse outcome / tipped_outcome for the narrator


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def apply_witnessed_act(
    *,
    state: PoliticalState,
    premises: list[PremiseDef],
    blocs: list[BlocDef],
    act_id: str,
    witnesses: list[str],
    turn: int,
) -> list[PoliticalEvent]:
    """Apply one witnessed act to the live dials. Mutates ``state`` in place.

    1. Drain every premise whose ``drained_by`` includes ``act_id`` (clamped ≥0),
       and soft-couple ``COUPLING_FRACTION`` of each drain into its propping blocs.
    2. Awaken every bloc whose ``awakening_acts`` includes ``act_id``.
    3. Final pass: fire ``collapsed`` for any premise at/under its collapse
       threshold and ``tipped`` for any bloc at/over its tipping threshold
       (a single pass so coupling-induced crossings are not missed).
    """
    events: list[PoliticalEvent] = []
    witnesses = list(witnesses)

    def _record(effect: str, kind: str, tid: str, delta: int, new_value: int) -> None:
        state.ledger.append(
            BeliefLedgerEntry(
                turn=turn,
                act_id=act_id,
                target_id=tid,
                target_kind=kind,
                effect=effect,
                delta=delta,
                new_value=new_value,
                witnesses=witnesses,
            )
        )

    # 1. Drain premises + soft-couple propping blocs.
    for pdef in premises:
        drain = next((d for d in pdef.drained_by if d.act == act_id), None)
        if drain is None:
            continue
        pstate = state.premises.get(pdef.premise_id)
        if pstate is None or pstate.collapsed:
            continue
        before = pstate.belief_reserve
        pstate.belief_reserve = _clamp(before - drain.belief_delta)
        applied = pstate.belief_reserve - before  # negative
        events.append(
            PoliticalEvent("drained", "premise", pdef.premise_id, applied, pstate.belief_reserve)
        )
        _record("drained", "premise", pdef.premise_id, applied, pstate.belief_reserve)

        coupled = int(drain.belief_delta * COUPLING_FRACTION)
        if coupled > 0:
            for bloc_id in pdef.propped_by:
                bstate = state.blocs.get(bloc_id)
                if bstate is None or bstate.tipped:
                    continue
                bbefore = bstate.defiance
                bstate.defiance = _clamp(bbefore + coupled)
                bapplied = bstate.defiance - bbefore
                if bapplied:
                    events.append(
                        PoliticalEvent("coupled", "bloc", bloc_id, bapplied, bstate.defiance)
                    )
                    _record("coupled", "bloc", bloc_id, bapplied, bstate.defiance)

    # 2. Awaken blocs whose awakening_acts include the act.
    for bdef in blocs:
        awk = next((a for a in bdef.awakening_acts if a.act == act_id), None)
        if awk is None:
            continue
        bstate = state.blocs.get(bdef.bloc_id)
        if bstate is None or bstate.tipped:
            continue
        before = bstate.defiance
        bstate.defiance = _clamp(before + awk.defiance_delta)
        applied = bstate.defiance - before
        if applied:
            events.append(
                PoliticalEvent("awakened", "bloc", bdef.bloc_id, applied, bstate.defiance)
            )
            _record("awakened", "bloc", bdef.bloc_id, applied, bstate.defiance)

    # 3. Threshold pass (collapse / tip), once, after all dial movement.
    premise_by_id = {p.premise_id: p for p in premises}
    bloc_by_id = {b.bloc_id: b for b in blocs}
    for pid, pstate in state.premises.items():
        pdef = premise_by_id.get(pid)
        if pdef is None or pstate.collapsed:
            continue
        if pstate.belief_reserve <= pdef.collapse.threshold:
            pstate.collapsed = True
            events.append(
                PoliticalEvent(
                    "collapsed", "premise", pid, 0, pstate.belief_reserve, pdef.collapse.outcome
                )
            )
            _record("collapsed", "premise", pid, 0, pstate.belief_reserve)
    for bid, bstate in state.blocs.items():
        bdef = bloc_by_id.get(bid)
        if bdef is None or bstate.tipped:
            continue
        if bstate.defiance >= bdef.tipping_threshold:
            bstate.tipped = True
            events.append(
                PoliticalEvent("tipped", "bloc", bid, 0, bstate.defiance, bdef.tipped_outcome)
            )
            _record("tipped", "bloc", bid, 0, bstate.defiance)

    return events
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_political_engine.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/political_engine.py tests/game/test_political_engine.py
git commit -m "feat(game): apply_witnessed_act engine — drain, soft-couple, awaken, thresholds"
```

---

### Task 4: ADR-053 belief injection on witnessed acts

**Files:**
- Modify: `sidequest-server/sidequest/game/political_engine.py` (add `inject_witnessed_contradiction`)
- Test: `sidequest-server/tests/game/test_political_belief_injection.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_political_belief_injection.py`:

```python
"""Witnessed acts inject a contradicting BeliefFact via ADR-053 (Plan 2, Task 4)."""

from __future__ import annotations

from sidequest.genre.models.premises import PremiseClaim, PremiseCollapse, PremiseDef
from sidequest.game.belief_state import BeliefState
from sidequest.game.political_engine import inject_witnessed_contradiction
from sidequest.game.session import Npc


def _premise():
    return PremiseDef(
        premise_id="humbug",
        authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="great and terrible"),
        belief_reserve=90,
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )


def test_only_witnesses_receive_the_contradicting_fact():
    dorothy = Npc(name="Dorothy", belief_state=BeliefState())
    bystander = Npc(name="Boq", belief_state=BeliefState())
    n = inject_witnessed_contradiction(
        npcs=[dorothy, bystander], witnesses=["Dorothy"], premise=_premise(), turn=3
    )
    assert n == 1
    assert len(dorothy.belief_state.beliefs) == 1
    assert len(bystander.belief_state.beliefs) == 0
    fact = dorothy.belief_state.beliefs[0]
    assert fact.variant == "fact"
    assert fact.subject == "the_wizard"
    assert fact.source.kind == "witnessed"
    assert fact.turn_learned == 3


def test_no_witnesses_injects_nothing():
    dorothy = Npc(name="Dorothy", belief_state=BeliefState())
    n = inject_witnessed_contradiction(
        npcs=[dorothy], witnesses=[], premise=_premise(), turn=1
    )
    assert n == 0
    assert dorothy.belief_state.beliefs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_political_belief_injection.py -v`
Expected: FAIL — `ImportError: cannot import name 'inject_witnessed_contradiction'`

- [ ] **Step 3: Add the injection helper**

Append to `sidequest-server/sidequest/game/political_engine.py`:

```python
def inject_witnessed_contradiction(
    *,
    npcs: list,
    witnesses: list[str],
    premise: PremiseDef,
    turn: int,
) -> int:
    """Inject a contradicting ``BeliefFact`` (Witnessed source) into each witness
    NPC's ``belief_state``, reusing the ADR-053 layer so the existing GossipEngine
    can later propagate it (spec §5/§9). Returns the count of NPCs updated.

    Matches witnesses by ``npc.name``. We do NOT touch the authoritative
    ``belief_reserve`` dial here — that is the engine's job; this only seeds the
    propositional belief layer so the contradiction can spread and so the GM
    panel sees the per-NPC belief mutation (belief_state.belief_added fires
    inside add_belief).
    """
    from sidequest.game.belief_state import BeliefFact, BeliefSourceWitnessed

    witness_set = {w for w in witnesses}
    updated = 0
    for npc in npcs:
        if getattr(npc, "name", None) in witness_set:
            npc.belief_state.add_belief(
                BeliefFact(
                    subject=premise.claim.subject,
                    content=f"witnessed contradiction of: {premise.claim.proposition}",
                    turn_learned=turn,
                    source=BeliefSourceWitnessed(),
                )
            )
            updated += 1
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_political_belief_injection.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/political_engine.py tests/game/test_political_belief_injection.py
git commit -m "feat(game): inject witnessed contradiction into witness belief_state (ADR-053 reuse)"
```

---

### Task 5: Hydration hook at chargen-confirm

**Files:**
- Create: `sidequest-server/sidequest/server/dispatch/premise_bind.py`
- Modify: `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py`
- Test: `sidequest-server/tests/server/test_premise_bind.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_premise_bind.py`:

```python
"""bind_political_state hydration (Plan 2, Task 5)."""

from __future__ import annotations

from types import SimpleNamespace

from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.game.session import GameSnapshot
from sidequest.server.dispatch.premise_bind import bind_political_state


def _pack_with_oz():
    humbug = PremiseDef(
        premise_id="humbug",
        authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="great and terrible"),
        belief_reserve=90,
        propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose", belief_delta=40)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )
    munchkins = BlocDef(
        bloc_id="munchkins",
        defiance=5,
        grants_belief_to=["humbug"],
        awakening_acts=[BlocAwakening(act="rally", defiance_delta=10)],
        tipping_threshold=70,
        tipped_outcome="Revolt.",
    )
    world = SimpleNamespace(premises=[humbug], blocs=[munchkins])
    return SimpleNamespace(worlds={"oz": world})


def test_bind_hydrates_political_state_onto_snapshot():
    snap = GameSnapshot(world_slug="oz")
    bound = bind_political_state(_pack_with_oz(), snap, genre_slug="wry_whimsy", world_slug="oz")
    assert bound is True
    assert snap.political_state is not None
    assert snap.political_state.premises["humbug"].belief_reserve == 90
    assert snap.political_state.blocs["munchkins"].defiance == 5


def test_bind_is_noop_when_world_has_no_politics():
    pack = SimpleNamespace(worlds={"plain": SimpleNamespace(premises=[], blocs=[])})
    snap = GameSnapshot(world_slug="plain")
    bound = bind_political_state(pack, snap, genre_slug="g", world_slug="plain")
    assert bound is False
    assert snap.political_state is None


def test_bind_is_noop_for_unknown_world():
    snap = GameSnapshot(world_slug="missing")
    bound = bind_political_state(_pack_with_oz(), snap, genre_slug="wry_whimsy", world_slug="missing")
    assert bound is False
    assert snap.political_state is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_premise_bind.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.server.dispatch.premise_bind'`

- [ ] **Step 3: Write the bind helper**

Create `sidequest-server/sidequest/server/dispatch/premise_bind.py`:

```python
"""Hydrate the runtime PoliticalState onto a snapshot at session start (Plan 2).

Mirrors ``scenario_bind.bind_scenario``: a no-op when the active world ships no
premises/blocs (a valid authoring choice, NOT a silent fallback to any default).
"""

from __future__ import annotations

from typing import Any

from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot


def bind_political_state(
    pack: Any,
    snapshot: GameSnapshot,
    *,
    genre_slug: str,
    world_slug: str,
) -> bool:
    """Hydrate ``snapshot.political_state`` from the active world's premises/blocs.

    Returns True when state was bound, False when the world has none (or is
    unknown) — in which case ``snapshot.political_state`` is left as ``None``.
    """
    world = pack.worlds.get(world_slug) if getattr(pack, "worlds", None) else None
    if world is None:
        return False
    state = PoliticalState.from_world(world)
    if state is None:
        return False
    snapshot.political_state = state
    return True
```

- [ ] **Step 4: Wire it into chargen-confirm (both `bind_scenario` sites)**

In `sidequest-server/sidequest/server/websocket_handlers/chargen_mixin.py`:

(4a) Add the import next to the existing `from sidequest.server.dispatch.scenario_bind import bind_scenario` (line ~72):

```python
from sidequest.server.dispatch.premise_bind import bind_political_state
```

(4b) There are **two** `bind_scenario(...)` call sites (~line 871 and ~line 1055). At **each** site, immediately after the `if bind_result is not None:` block that sets `sd.active_scenario`, insert:

```python
            # Political substrate hydration (wry_whimsy, Plan 2). No-op unless
            # the active world declares premises/blocs; sets snapshot.political_state
            # so the witnessed_act subsystem stops being inert.
            bind_political_state(
                sd.genre_pack,
                sd.snapshot,
                genre_slug=sd.genre_slug,
                world_slug=sd.world_slug,
            )
```

Use `grep -n "bind_result = bind_scenario" sidequest/server/websocket_handlers/chargen_mixin.py` to find both sites; add the block after each. If only one site is found, STOP — the file changed since this plan was written; report it.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/server/test_premise_bind.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Verify the wiring edit is syntactically sound**

Run: `uv run python -c "import sidequest.server.websocket_handlers.chargen_mixin; print('chargen ok')"`
Expected: prints `chargen ok`

- [ ] **Step 7: Commit**

```bash
git add sidequest/server/dispatch/premise_bind.py sidequest/server/websocket_handlers/chargen_mixin.py tests/server/test_premise_bind.py
git commit -m "feat(server): hydrate PoliticalState at chargen-confirm (mirrors bind_scenario)"
```

---

### Task 6: The `witnessed_act` dispatch subsystem

**Files:**
- Create: `sidequest-server/sidequest/agents/subsystems/witnessed_act.py`
- Modify: `sidequest-server/sidequest/agents/subsystems/__init__.py` (register)
- Modify: `sidequest-server/sidequest/agents/dispatch_precondition_gate.py` (precondition)
- Test: `sidequest-server/tests/agents/test_witnessed_act_subsystem.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/agents/test_witnessed_act_subsystem.py`:

```python
"""witnessed_act dispatch subsystem (Plan 2, Task 6)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sidequest.agents.subsystems import get_registered
from sidequest.agents.subsystems.witnessed_act import run_witnessed_act_dispatch
from sidequest.agents.dispatch_precondition_gate import _INERT_PRECONDITIONS
from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.game.belief_state import BeliefState
from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot, Npc
from sidequest.protocol.dispatch import SubsystemDispatch


def _dispatch(params):
    return SubsystemDispatch(
        subsystem="witnessed_act",
        params=params,
        idempotency_key="wa-1",
        visibility={"visible_to": "all"},
        confidence=0.9,
    )


def _pack():
    humbug = PremiseDef(
        premise_id="humbug", authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="great and terrible"),
        belief_reserve=90, propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose", belief_delta=40)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )
    munchkins = BlocDef(
        bloc_id="munchkins", defiance=5, grants_belief_to=["humbug"],
        awakening_acts=[BlocAwakening(act="rally", defiance_delta=10)],
        tipping_threshold=70, tipped_outcome="Revolt.",
    )
    return SimpleNamespace(worlds={"oz": SimpleNamespace(premises=[humbug], blocs=[munchkins])})


def _snapshot():
    snap = GameSnapshot(world_slug="oz", round=2)
    snap.political_state = PoliticalState.from_world(_pack().worlds["oz"])
    snap.npcs = [Npc(name="Dorothy", belief_state=BeliefState())]
    return snap


def test_registered_in_bank():
    assert "witnessed_act" in get_registered()


def test_precondition_inert_without_political_state():
    pred = _INERT_PRECONDITIONS["witnessed_act"]
    assert pred(GameSnapshot()) is not None  # no political_state → inert reason
    snap = _snapshot()
    assert pred(snap) is None  # hydrated → not inert


@pytest.mark.asyncio
async def test_handler_drains_injects_and_returns_directive():
    snap = _snapshot()
    out = await run_witnessed_act_dispatch(
        _dispatch({"act_id": "expose", "witnesses": ["Dorothy"]}),
        snapshot=snap, pack=_pack(), player_name="Dorothy", npcs=snap.npcs,
    )
    assert snap.political_state.premises["humbug"].belief_reserve == 50
    assert snap.political_state.blocs["munchkins"].defiance == 25  # 5 + floor(40*0.5)
    # ADR-053 reuse: the witness got a contradicting fact
    assert len(snap.npcs[0].belief_state.beliefs) == 1
    # narrator gets told something mechanical happened
    assert out.directives and out.directives[0].kind == "must_narrate"
    assert out.data["act_id"] == "expose"


@pytest.mark.asyncio
async def test_no_witness_moves_nothing():
    snap = _snapshot()
    out = await run_witnessed_act_dispatch(
        _dispatch({"act_id": "expose", "witnesses": []}),
        snapshot=snap, pack=_pack(), player_name="Dorothy", npcs=snap.npcs,
    )
    assert snap.political_state.premises["humbug"].belief_reserve == 90  # unmoved
    assert out.data.get("error") == "no_witness"


@pytest.mark.asyncio
async def test_missing_act_id_raises():
    snap = _snapshot()
    with pytest.raises(ValueError, match="act_id"):
        await run_witnessed_act_dispatch(
            _dispatch({"witnesses": ["Dorothy"]}),
            snapshot=snap, pack=_pack(), player_name="Dorothy", npcs=snap.npcs,
        )
```

> Note: `test_handler_*` use `@pytest.mark.asyncio`. This repo already runs async tests (the dispatch bank is async) — if the marker errors as unknown, confirm `asyncio_mode`/`pytest-asyncio` config exists (it does for the existing subsystem tests); match how `tests/agents/` async tests are written.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agents/test_witnessed_act_subsystem.py -v`
Expected: FAIL — `ModuleNotFoundError: ...witnessed_act`

- [ ] **Step 3: Write the handler**

Create `sidequest-server/sidequest/agents/subsystems/witnessed_act.py`:

```python
"""The witnessed_act dispatch subsystem (wry_whimsy political substrate, Plan 2).

Engages when the player commits a publicly-witnessed act that contradicts a
belief-powered authority or shows a population that defiance survives. Applies
the act to the live PoliticalState dials, injects the contradiction into witness
beliefs (ADR-053), emits OTEL per change, and tells the narrator what moved.
"""

from __future__ import annotations

from typing import Any

from sidequest.game.political_engine import (
    apply_witnessed_act,
    inject_witnessed_contradiction,
)
from sidequest.protocol.dispatch import NarratorDirective, SubsystemDispatch
from sidequest.protocol.dispatch import SubsystemOutput
from sidequest.telemetry.spans import (
    SPAN_BLOC_DEFIANCE_RAISED,
    SPAN_BLOC_TIPPED,
    SPAN_PREMISE_BELIEF_DRAINED,
    SPAN_PREMISE_COLLAPSED,
    Span,
)


def _emit_political_events(events, *, act_id: str, witnesses: list[str], turn: int) -> None:
    witness_attr = ",".join(witnesses)
    for ev in events:
        if ev.effect == "drained":
            with Span.open(
                SPAN_PREMISE_BELIEF_DRAINED,
                {
                    "premise_id": ev.target_id,
                    "act_id": act_id,
                    "delta": ev.delta,
                    "new_reserve": ev.new_value,
                    "witnesses": witness_attr,
                    "turn": turn,
                },
            ):
                pass
        elif ev.effect in ("coupled", "awakened"):
            with Span.open(
                SPAN_BLOC_DEFIANCE_RAISED,
                {
                    "bloc_id": ev.target_id,
                    "act_id": act_id,
                    "source": ev.effect,
                    "delta": ev.delta,
                    "new_defiance": ev.new_value,
                    "turn": turn,
                },
            ):
                pass
        elif ev.effect == "collapsed":
            with Span.open(
                SPAN_PREMISE_COLLAPSED,
                {"premise_id": ev.target_id, "new_reserve": ev.new_value, "turn": turn},
            ):
                pass
        elif ev.effect == "tipped":
            with Span.open(
                SPAN_BLOC_TIPPED,
                {"bloc_id": ev.target_id, "new_defiance": ev.new_value, "turn": turn},
            ):
                pass


def _summarize(events) -> str:
    parts: list[str] = []
    for ev in events:
        if ev.effect == "drained":
            parts.append(f"belief in {ev.target_id} fell to {ev.new_value}")
        elif ev.effect in ("coupled", "awakened"):
            parts.append(f"{ev.target_id} defiance rose to {ev.new_value}")
        elif ev.effect == "collapsed":
            parts.append(f"{ev.target_id} COLLAPSED — {ev.detail}")
        elif ev.effect == "tipped":
            parts.append(f"{ev.target_id} TIPPED — {ev.detail}")
    return "; ".join(parts)


async def run_witnessed_act_dispatch(
    dispatch: SubsystemDispatch,
    *,
    snapshot: Any,
    pack: Any,
    player_name: str,
    npcs: list[Any] | None = None,
) -> SubsystemOutput:
    """Apply a witnessed act to the political layer. Mutates the snapshot dials."""
    params = dispatch.params or {}
    act_id = params.get("act_id") or params.get("act_archetype")
    if not act_id or not isinstance(act_id, str):
        # No silent fallback: a witnessed_act dispatch with no act id is a
        # router-output bug, surfaced as an error span by the bank.
        raise ValueError(
            f"witnessed_act dispatch missing params['act_id']; got params={dispatch.params!r}"
        )

    state = getattr(snapshot, "political_state", None)
    if state is None:
        # Defense in depth — the precondition gate should have dropped this.
        return SubsystemOutput(directives=[], data={"error": "no_political_state"})

    world = pack.worlds.get(snapshot.world_slug) if getattr(pack, "worlds", None) else None
    if world is None:
        return SubsystemOutput(directives=[], data={"error": "world_not_found"})

    premises = list(getattr(world, "premises", None) or [])
    blocs = list(getattr(world, "blocs", None) or [])
    witnesses = [w for w in (params.get("witnesses") or []) if isinstance(w, str)]

    # Spec §5: an act with no witness moves nothing.
    if not witnesses:
        return SubsystemOutput(
            directives=[
                NarratorDirective(
                    kind="must_narrate",
                    payload=(
                        "The act had no witness, so no belief shifted — exposing a "
                        "humbug in an empty room changes nothing."
                    ),
                    visibility=dispatch.visibility,
                )
            ],
            data={"error": "no_witness"},
        )

    turn = int(getattr(snapshot, "round", 0))
    events = apply_witnessed_act(
        state=state,
        premises=premises,
        blocs=blocs,
        act_id=act_id,
        witnesses=witnesses,
        turn=turn,
    )

    if not events:
        return SubsystemOutput(
            directives=[
                NarratorDirective(
                    kind="must_narrate",
                    payload=(
                        f"The act ('{act_id}') did not match any standing illusion or "
                        "population here; narrate it, but no political dial moved."
                    ),
                    visibility=dispatch.visibility,
                )
            ],
            data={"error": "no_effect", "act_id": act_id},
        )

    # ADR-053 reuse: seed witness beliefs for every premise this act drained.
    npc_list = list(npcs or getattr(snapshot, "npcs", None) or [])
    premise_by_id = {p.premise_id: p for p in premises}
    drained_ids = {ev.target_id for ev in events if ev.effect == "drained"}
    for pid in drained_ids:
        pdef = premise_by_id.get(pid)
        if pdef is not None:
            inject_witnessed_contradiction(
                npcs=npc_list, witnesses=witnesses, premise=pdef, turn=turn
            )

    _emit_political_events(events, act_id=act_id, witnesses=witnesses, turn=turn)

    return SubsystemOutput(
        directives=[
            NarratorDirective(
                kind="must_narrate",
                payload=(
                    "The political layer moved (this is mechanically real, not color): "
                    + _summarize(events)
                    + ". Narrate the consequence in keeping with what shifted."
                ),
                visibility=dispatch.visibility,
            )
        ],
        data={
            "act_id": act_id,
            "events": [
                {
                    "effect": ev.effect,
                    "target_id": ev.target_id,
                    "delta": ev.delta,
                    "new_value": ev.new_value,
                }
                for ev in events
            ],
        },
    )
```

- [ ] **Step 4: Register the subsystem**

In `sidequest-server/sidequest/agents/subsystems/__init__.py`, inside `_register_defaults()`:

(4a) add the import alongside the other handler imports:

```python
    from sidequest.agents.subsystems.witnessed_act import run_witnessed_act_dispatch
```

(4b) add this entry to the registration tuple (next to the other `("name", fn)` pairs):

```python
        ("witnessed_act", run_witnessed_act_dispatch),
```

- [ ] **Step 5: Add the precondition gate**

In `sidequest-server/sidequest/agents/dispatch_precondition_gate.py`, add a predicate and register it in `_INERT_PRECONDITIONS` (next to `_scenario_clue_precondition_unmet`):

```python
def _witnessed_act_precondition_unmet(snapshot: GameSnapshot) -> str | None:
    if snapshot.political_state is None:
        return "snapshot.political_state is None (world ships no wry_whimsy premise/bloc layer)"
    return None
```

and add to the dict:

```python
    "witnessed_act": _witnessed_act_precondition_unmet,
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/agents/test_witnessed_act_subsystem.py -v`
Expected: PASS (6 tests)

- [ ] **Step 7: Commit**

```bash
git add sidequest/agents/subsystems/witnessed_act.py sidequest/agents/subsystems/__init__.py sidequest/agents/dispatch_precondition_gate.py tests/agents/test_witnessed_act_subsystem.py
git commit -m "feat(agents): witnessed_act dispatch subsystem + precondition gate + OTEL"
```

---

### Task 7: End-to-end integration wiring test (through the production bank)

**Files:**
- Test: `sidequest-server/tests/agents/test_witnessed_act_integration.py`

This is the subsystem's **wiring test** (project rule): it drives the production `run_dispatch_bank` path with a `witnessed_act` dispatch on a hydrated Oz-shaped snapshot, proving the subsystem is registered, reachable, gated, and mutates state + fires OTEL end-to-end. (The LLM router emitting the dispatch is Plan 2b; here we hand-build the package to keep the test deterministic.)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/agents/test_witnessed_act_integration.py`:

```python
"""witnessed_act end-to-end through run_dispatch_bank (Plan 2, Task 7)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sidequest.agents.subsystems import run_dispatch_bank
from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.game.belief_state import BeliefState
from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot, Npc
from sidequest.protocol.dispatch import DispatchPackage, PerPlayerDispatch, SubsystemDispatch


def _pack():
    humbug = PremiseDef(
        premise_id="humbug", authority="the_wizard",
        claim=PremiseClaim(subject="the_wizard", proposition="great and terrible"),
        belief_reserve=90, propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose", belief_delta=40)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees."),
    )
    munchkins = BlocDef(
        bloc_id="munchkins", defiance=5, grants_belief_to=["humbug"],
        awakening_acts=[], tipping_threshold=70, tipped_outcome="Revolt.",
    )
    return SimpleNamespace(
        worlds={"oz": SimpleNamespace(premises=[humbug], blocs=[munchkins])},
        rules=SimpleNamespace(dispatch_confidence_thresholds={}),
    )


def _snapshot():
    snap = GameSnapshot(world_slug="oz", round=1)
    snap.political_state = PoliticalState.from_world(_pack().worlds["oz"])
    snap.npcs = [Npc(name="Dorothy", belief_state=BeliefState())]
    return snap


def _package():
    return DispatchPackage(
        per_player=[
            PerPlayerDispatch(
                player="Dorothy",
                dispatch=[
                    SubsystemDispatch(
                        subsystem="witnessed_act",
                        params={"act_id": "expose", "witnesses": ["Dorothy"]},
                        idempotency_key="wa-int-1",
                        visibility={"visible_to": "all"},
                        confidence=0.9,
                    )
                ],
            )
        ],
        cross_player=[],
        confidence_global=0.9,
    )


@pytest.mark.asyncio
async def test_witnessed_act_engages_through_the_bank():
    snap = _snapshot()
    pack = _pack()
    result = await run_dispatch_bank(
        _package(),
        context={
            "snapshot": snap,
            "pack": pack,
            "player_name": "Dorothy",
            "npcs": snap.npcs,
        },
    )
    # The engine actually moved the authoritative dials via the production path.
    assert snap.political_state.premises["humbug"].belief_reserve == 50
    assert snap.political_state.blocs["munchkins"].defiance == 25
    # The ledger kept the receipt.
    assert any(le.effect == "drained" for le in snap.political_state.ledger)
    # The bank produced the narrator directive (engaged, not degraded-to-hint).
    assert result is not None
```

> Verify the exact `DispatchPackage` / `PerPlayerDispatch` field names against `sidequest/protocol/dispatch.py` before running — match the real model (the per-player entry field may be named differently, e.g. `player_name`; the bank context keys must match `intent_router_pass.py`). Adjust the constructor to the real shapes; the assertions on `snap.political_state` are the load-bearing part.

- [ ] **Step 2: Run test to verify it fails, then make it pass**

Run: `uv run pytest tests/agents/test_witnessed_act_integration.py -v`

If it fails on `DispatchPackage`/`PerPlayerDispatch` shape, read `sidequest/protocol/dispatch.py` and the `run_dispatch_bank` signature in `sidequest/agents/subsystems/__init__.py`, fix the constructor and context dict to the real shapes, and re-run. Expected once shapes match: PASS — `belief_reserve == 50`, `defiance == 25`, ledger has a `drained` entry.

- [ ] **Step 3: Commit**

```bash
git add tests/agents/test_witnessed_act_integration.py
git commit -m "test(agents): witnessed_act engages end-to-end through run_dispatch_bank"
```

---

### Task 8: Tune the engagement threshold (content)

**Files:**
- Modify: `sidequest-content/genre_packs/wry_whimsy/rules.yaml`

Acts that reshape a society should be *earned* (spec §5) — set a higher engagement bar than the 0.6 default so a low-confidence guess degrades to a narrator hint instead of moving the dials.

- [ ] **Step 1: Confirm the field name**

In `sidequest-server`, run: `grep -n "dispatch_confidence_thresholds" sidequest/genre/models/rules.py`
Confirm `RulesConfig.dispatch_confidence_thresholds: dict[str, float]` exists. If the field name differs, use the real one. If it does not exist as a settable content field, STOP and report — this task is content-tuning only and must not require an engine change.

- [ ] **Step 2: Add the override**

In `sidequest-content/genre_packs/wry_whimsy/rules.yaml`, add (or extend an existing `dispatch_confidence_thresholds:` mapping):

```yaml
dispatch_confidence_thresholds:
  witnessed_act: 0.7
```

- [ ] **Step 3: Verify the pack still loads**

In `sidequest-server`, run: `uv run pytest tests/genre/ -k "wry or load" -q`
Expected: PASS (no load regression).

- [ ] **Step 4: Commit (content repo)**

```bash
cd ../sidequest-content
git add genre_packs/wry_whimsy/rules.yaml
git commit -m "content(wry_whimsy): require 0.7 confidence to engage witnessed_act"
cd ../sidequest-server
```

---

## Self-Review

**1. Spec coverage (Plan 2 scope — the runtime mechanical spine):**
- §4.3 runtime `PremiseState`/`BlocState` + ledger with provenance → Task 1 ✓
- §4.4 soft belief→defiance coupling (independent deltas + `COUPLING_FRACTION`, not a hard law) → Task 3 ✓
- §5 causal chain: act → witness gate → drain → coupled defiance → thresholds; "no witness moves nothing" → Tasks 3 + 6 ✓
- §5/§9 ADR-053 reuse: witnessed act injects a contradicting `BeliefFact` (Witnessed) for the GossipEngine to spread → Task 4 ✓
- §10 OTEL emits (`premise.belief_drained`, `bloc.defiance_raised`, `premise.collapsed`, `bloc.tipped`) → Tasks 2 + 6 ✓ (closes the Plan-1 reviewer carry-forward)
- §11 v1: aggregation over authoritative dials, Oz reference; "Refuse the Premise"/UI/spectacles explicitly **out** → series map ✓
- Intent-router classification (the player-facing front door) → **deferred to Plan 2b** (documented in series map; subsystem is reachable through the bank now, proven by Task 7).

**2. Placeholder scan:** Every code step is complete. The two "verify the real shape" notes (Task 6 async marker, Task 7 `DispatchPackage` constructor) are explicit verification steps with concrete fallback instructions, not unfilled blanks — the load-bearing assertions are spelled out.

**3. Type consistency:**
- `PoliticalState` / `PremiseState` (`premise_id`, `belief_reserve`, `collapsed`) / `BlocState` (`bloc_id`, `defiance`, `tipped`) / `BeliefLedgerEntry` (`turn, act_id, target_id, target_kind, effect, delta, new_value, witnesses`) — defined Task 1, used identically in Tasks 3, 5, 6, 7. ✓
- `apply_witnessed_act(*, state, premises, blocs, act_id, witnesses, turn) -> list[PoliticalEvent]` — defined Task 3, called identically in Tasks 6, 7. ✓
- `PoliticalEvent(effect, target_kind, target_id, delta, new_value, detail)` — Task 3; consumed by `_emit_political_events`/`_summarize` (Task 6) reading `.effect/.target_id/.delta/.new_value/.detail`. ✓
- `inject_witnessed_contradiction(*, npcs, witnesses, premise, turn) -> int` — Task 4, called in Task 6. ✓
- `bind_political_state(pack, snapshot, *, genre_slug, world_slug) -> bool` — Task 5. ✓
- Span constants `SPAN_PREMISE_BELIEF_DRAINED`/`SPAN_BLOC_DEFIANCE_RAISED`/`SPAN_PREMISE_COLLAPSED`/`SPAN_BLOC_TIPPED` — Task 2, imported in Task 6. ✓
- `snapshot.political_state` (Task 1) is what the precondition gate (Task 6) and bind (Task 5) key on. `snapshot.round` is the turn source (confirmed `round: int = 0` on `GameSnapshot`). ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-02-wry-whimsy-premise-runtime-engine.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task (or per coherent phase), two-stage review between.

**2. Inline Execution** — execute in this session with checkpoints.

Suggested phasing for subagent-driven: **Phase A** = Tasks 1–4 (pure runtime: models, OTEL, engine, belief injection — all unit-testable, no integration); **Phase B** = Tasks 5–8 (hydration wiring, dispatch subsystem, integration test, threshold). Which approach — and shall I also queue Plan 2b (the intent-router classification) after?
