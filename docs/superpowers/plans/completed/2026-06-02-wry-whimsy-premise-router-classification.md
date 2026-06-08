# wry_whimsy Premise/Bloc Intent-Router Classification Implementation Plan (Plan 2b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the LLM Intent Router to classify a natural-language player action as a witnessed act and emit a `SubsystemDispatch(subsystem="witnessed_act", params={"act_id", "witnesses"}, confidence=…)`, so the already-merged Plan-2 engine becomes player-triggerable instead of only reachable through hand-built test dispatches.

**Architecture:** Mirror the existing `confrontation_types` mechanism (Story 59-10) exactly: a **static prompt vocabulary entry** in `intent_router.py` `_SYSTEM_PROMPT` tells the model the subsystem exists and its params; a **gated state-summary projection** in `intent_router_pass.py` `_build_state_summary` surfaces the available acts (`witnessed_act_vocabulary`) and the witness candidate set (`present_npcs`, computed via the canonical `is_npc_in_scene` predicate); and two new OTEL spans make the surfacing and the classification decision visible to the GM panel. No engine change, no content change — the dispatch's `act_id`/`witnesses` contract is exactly what the merged handler already reads.

**Tech Stack:** Python 3.12+, pydantic v2, `uv`/`pytest`, `pytest-asyncio`, OpenTelemetry. Touches `sidequest-server` only. Follows project rules **No Silent Fallbacks**, **No Stubbing**, **Don't Reinvent — Wire Up What Exists** (reuses `is_npc_in_scene` + the confrontation-vocabulary idiom), **No Source-Text Wiring Tests** (wiring proven by behavior/OTEL, never by grepping the prompt), **Every Test Suite Needs a Wiring Test**, and the **OTEL Observability Principle**.

---

## Plan Series Context (read before starting)

This is **Plan 2b** of the wry_whimsy political-substrate series (spec `docs/superpowers/specs/2026-06-02-wry-whimsy-premise-belief-flow-design.md`; this plan's design `docs/superpowers/specs/2026-06-02-wry-whimsy-premise-router-classification-design.md`).

| # | Plan | Status | This plan's relationship |
|---|------|--------|--------------------------|
| 1 | Content schema + loader | merged (server #580, content #331) | provides `pack.witnessed_acts` (`WitnessedActArchetype`) |
| 2 | Runtime engine — mechanical spine | **merged (server #582, content #334)** | provides the registered `witnessed_act` subsystem, `snapshot.political_state`, the `0.7` confidence gate, and `apply_witnessed_act`. **Prerequisite.** |
| **2b** | **Intent-router classification (THIS PLAN)** | — | Teaches the router to *emit* `witnessed_act`. Server-only, no content change. |
| 3 | Confrontation integration | after 2 | unaffected by this plan |
| 4 | UI Standing panel | after 2 | unaffected |
| 5 | Spectacles toggle | after 2 | unaffected |

**Prerequisite verified on develop:** `sidequest/agents/subsystems/witnessed_act.py` exists with registry entry `("witnessed_act", run_witnessed_act_dispatch)`; `sidequest/server/intent_router_pass.py` exists with no `witnessed` references yet; `genre_packs/wry_whimsy/witnessed_acts.yaml` + `rules.yaml: dispatch_confidence_thresholds.witnessed_act: 0.7` are present. If any is absent, STOP — the prerequisite regressed.

**Out of scope (separate PRs):** the Plan-2 `apply_witnessed_act` "touched-this-turn" collapse guard and co-locating `witnessed_act` precondition coverage are engine-side follow-ups, deliberately NOT in this router-only diff (parent design §6).

---

## File Structure

| File | Responsibility | Action |
|------|----------------|--------|
| `sidequest-server/sidequest/telemetry/spans/intent_router.py` | Add two span constants + routes + contextmanagers: `intent_router.witnessed_act_vocabulary` (surfacing) and `intent_router.witnessed_act_classified` (decision) | **Modify** |
| `sidequest-server/sidequest/server/intent_router_pass.py` | `_present_npc_names` helper; two projections + vocabulary span in `_build_state_summary`; classification span after `decompose()` | **Modify** |
| `sidequest-server/sidequest/agents/intent_router.py` | Add the `witnessed_act:` vocabulary entry to `_SYSTEM_PROMPT` | **Modify** |
| `sidequest-server/tests/telemetry/test_intent_router_witnessed_act_spans.py` | Span constants exported + routed + extract fields | **Create** |
| `sidequest-server/tests/server/test_intent_router_witnessed_act_vocabulary.py` | `_present_npc_names` + state-summary gating + vocabulary span | **Create** |
| `sidequest-server/tests/server/test_intent_router_witnessed_act_classified.py` | classification-result span after decompose | **Create** |
| `sidequest-server/tests/server/test_witnessed_act_router_to_engine.py` | wiring test: stub router emission → bank → engine mutates `political_state` | **Create** |

Server commands run from `sidequest-server/`. Single test: `uv run pytest tests/<path>::<name> -v`. **Run the OTEL/span tests with `-n0`** (the full parallel `tests/server/` run deadlocks ~18 OTEL span-count tests — pre-existing; memory `project_server_test_otel_deadlock`).

**Branching (dual-clone hazard — memory `project_dualclone_subrepo_branch_hazard`):** in `sidequest-server`, before the first commit:
```bash
cd sidequest-server
git checkout develop && git pull origin develop
git checkout -b feat/wry-whimsy-premise-router
```
Do NOT chain another repo's git ops in the same compound command (each Bash call resets cwd; `cd repo && git …` only persists within ONE command). No `sidequest-content` change is needed in this plan.

---

### Task 1: OTEL span routes + contextmanagers for the political-router decisions

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/spans/intent_router.py`
- Test: `sidequest-server/tests/telemetry/test_intent_router_witnessed_act_spans.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_intent_router_witnessed_act_spans.py`:

```python
"""witnessed_act intent-router span routes (Plan 2b, Task 1)."""

from __future__ import annotations


def test_witnessed_act_span_constants_exported_and_routed():
    from sidequest.telemetry.spans.intent_router import (
        SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED,
        SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY,
    )
    from sidequest.telemetry.spans._core import SPAN_ROUTES

    assert SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY in SPAN_ROUTES
    assert SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED in SPAN_ROUTES


def test_vocabulary_route_extracts_fields():
    from sidequest.telemetry.spans._core import SPAN_ROUTES
    from sidequest.telemetry.spans.intent_router import (
        SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY,
    )

    route = SPAN_ROUTES[SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY]
    assert route.component == "intent_router"

    class _FakeSpan:
        attributes = {"act_count": 5, "present_npc_count": 2, "genre_slug": "wry_whimsy"}

    fields = route.extract(_FakeSpan())
    assert fields["act_count"] == 5
    assert fields["present_npc_count"] == 2
    assert fields["genre_slug"] == "wry_whimsy"


def test_classified_route_extracts_fields():
    from sidequest.telemetry.spans._core import SPAN_ROUTES
    from sidequest.telemetry.spans.intent_router import (
        SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED,
    )

    route = SPAN_ROUTES[SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED]
    assert route.component == "intent_router"

    class _FakeSpan:
        attributes = {"emitted": 1, "act_ids": "expose_the_humbug", "genre_slug": "wry_whimsy"}

    fields = route.extract(_FakeSpan())
    assert fields["emitted"] == 1
    assert fields["act_ids"] == "expose_the_humbug"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/telemetry/test_intent_router_witnessed_act_spans.py -v -n0`
Expected: FAIL — `ImportError: cannot import name 'SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY'`

- [ ] **Step 3: Add the span constants, routes, and contextmanagers**

In `sidequest-server/sidequest/telemetry/spans/intent_router.py`, immediately AFTER the `intent_router_confrontation_vocabulary_span` contextmanager (end of file region), append:

```python
SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY = "intent_router.witnessed_act_vocabulary"
SPAN_ROUTES[SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY] = SpanRoute(
    event_type="state_transition",
    component="intent_router",
    extract=lambda span: {
        "field": "intent_router.witnessed_act_vocabulary",
        "act_count": (span.attributes or {}).get("act_count", 0),
        "present_npc_count": (span.attributes or {}).get("present_npc_count", 0),
        "genre_slug": (span.attributes or {}).get("genre_slug", ""),
    },
)


@contextmanager
def intent_router_witnessed_act_vocabulary_span(
    *,
    act_count: int,
    present_npc_count: int,
    genre_slug: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    """Fires when the witnessed-act vocabulary + present-NPC witness set is
    injected into the router's state summary (wry_whimsy political worlds only).

    The GM-panel record that the acts were surfaced — the precondition for the
    router being able to classify an action as a witnessed act at all."""
    with Span.open(
        SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY,
        {
            "act_count": act_count,
            "present_npc_count": present_npc_count,
            "genre_slug": genre_slug,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span


SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED = "intent_router.witnessed_act_classified"
SPAN_ROUTES[SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED] = SpanRoute(
    event_type="state_transition",
    component="intent_router",
    extract=lambda span: {
        "field": "intent_router.witnessed_act_classified",
        "emitted": (span.attributes or {}).get("emitted", 0),
        "act_ids": (span.attributes or {}).get("act_ids", ""),
        "genre_slug": (span.attributes or {}).get("genre_slug", ""),
    },
)


@contextmanager
def intent_router_witnessed_act_classified_span(
    *,
    emitted: int,
    act_ids: str,
    genre_slug: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    """Fires after ``decompose`` in a political world where the vocabulary was
    surfaced. ``emitted`` is the count of ``witnessed_act`` dispatches the router
    produced this turn (0 = it had the vocabulary and judged the action NOT a
    witnessed act). The GM-panel lie-detector for the front door: distinguishes
    "router classified this as witnessed_act:X" from "router declined to emit"."""
    with Span.open(
        SPAN_INTENT_ROUTER_WITNESSED_ACT_CLASSIFIED,
        {"emitted": emitted, "act_ids": act_ids, "genre_slug": genre_slug, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/telemetry/test_intent_router_witnessed_act_spans.py -v -n0`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/telemetry/spans/intent_router.py tests/telemetry/test_intent_router_witnessed_act_spans.py
git commit -m "feat(telemetry): witnessed_act router vocabulary + classification span routes"
```

---

### Task 2: `_present_npc_names` helper (the witness candidate set)

**Files:**
- Modify: `sidequest-server/sidequest/server/intent_router_pass.py`
- Test: `sidequest-server/tests/server/test_intent_router_witnessed_act_vocabulary.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_intent_router_witnessed_act_vocabulary.py`:

```python
"""witnessed_act state-summary projections + present-NPC helper (Plan 2b, Tasks 2-3)."""

from __future__ import annotations

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest

from sidequest.game.belief_state import BeliefState
from sidequest.game.creature_core import CreatureCore, HpPool
from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot, Npc
from sidequest.genre.models.premises import WitnessedActArchetype
from sidequest.server.intent_router_pass import _build_state_summary, _present_npc_names


def _npc(name: str, *, location: str | None = None) -> Npc:
    return Npc(
        core=CreatureCore(
            name=name,
            description="A villager of the Munchkin country.",
            personality="Wary but hopeful.",
            hp=HpPool(current=10, max=10, base_max=10),
        ),
        belief_state=BeliefState(),
        location=location,
    )


def _oz_snapshot() -> GameSnapshot:
    """A hydrated political snapshot whose party has a consensus location."""
    snap = GameSnapshot(world_slug="oz")
    snap.genre_slug = "wry_whimsy"
    snap.player_seats = {"seat-1": "Dorothy"}
    snap.character_locations = {"Dorothy": "munchkin_country"}
    snap.npcs = [
        _npc("Boq", location="munchkin_country"),     # present
        _npc("Glinda", location="quadling_country"),  # elsewhere
    ]
    snap.political_state = PoliticalState(
        premises={}, blocs={}, ledger=[]
    )
    return snap


def _acts() -> list[WitnessedActArchetype]:
    return [
        WitnessedActArchetype(id="expose_the_humbug", label="Expose the Humbug", description="Pull the curtain."),
        WitnessedActArchetype(id="refuse_the_premise", label="Refuse the Premise", description="Decline the rule."),
    ]


def test_present_npc_names_returns_only_in_scene_npcs():
    snap = _oz_snapshot()
    names = _present_npc_names(snap)
    assert names == ["Boq"]  # Glinda is in quadling_country, not present


def test_present_npc_names_empty_when_party_location_unresolved():
    # No seated PCs → party_location() is None → no one is "present".
    snap = _oz_snapshot()
    snap.player_seats = {}
    assert _present_npc_names(snap) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_vocabulary.py -v -n0`
Expected: FAIL — `ImportError: cannot import name '_present_npc_names'`

- [ ] **Step 3: Add the helper**

In `sidequest-server/sidequest/server/intent_router_pass.py`, add the import near the other `from sidequest.game.*` imports (after `from sidequest.game.session import GameSnapshot`):

```python
from sidequest.game.npc_scene import is_npc_in_scene
```

Then add the helper immediately BEFORE `_build_state_summary`:

```python
def _present_npc_names(snapshot: GameSnapshot) -> list[str]:
    """Return the names of NPCs the player's action could be witnessed by.

    The witness candidate set for ``witnessed_act`` classification (spec §5: an
    act with no witness moves nothing). Reuses the canonical scene-membership
    predicate (``sidequest/game/npc_scene.py``) — the SAME one the narrator's
    scene projection trusts — so "present" means here what it means everywhere
    else in the system (no parallel, divergent definition). Scene id is the
    party's consensus location; an unresolved location (pre-chargen / party
    split) yields an empty set unless an unresolved encounter anchors actors.
    """
    current_room = snapshot.party_location()
    encounter = getattr(snapshot, "encounter", None)
    names: list[str] = []
    for npc in snapshot.npcs or []:
        if is_npc_in_scene(npc, current_room=current_room, encounter=encounter):
            names.append(npc.core.name)
    return names
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_vocabulary.py::test_present_npc_names_returns_only_in_scene_npcs tests/server/test_intent_router_witnessed_act_vocabulary.py::test_present_npc_names_empty_when_party_location_unresolved -v -n0`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/intent_router_pass.py tests/server/test_intent_router_witnessed_act_vocabulary.py
git commit -m "feat(server): _present_npc_names — witness candidate set via canonical scene predicate"
```

---

### Task 3: State-summary projections + vocabulary span

**Files:**
- Modify: `sidequest-server/sidequest/server/intent_router_pass.py` (`_build_state_summary`)
- Test: `sidequest-server/tests/server/test_intent_router_witnessed_act_vocabulary.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/server/test_intent_router_witnessed_act_vocabulary.py`:

```python
class _FakePack:
    """Minimal duck-typed pack: only the fields _build_state_summary reads."""

    def __init__(self, witnessed_acts):
        self.witnessed_acts = witnessed_acts
        self.rules = None  # no confrontations → confrontation block is skipped


@pytest.fixture
def otel_capture():
    from sidequest.telemetry.setup import init_tracer

    init_tracer()
    provider = otel_trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    try:
        yield exporter
    finally:
        processor.shutdown()


def test_state_summary_includes_vocabulary_and_present_npcs_in_political_world():
    snap = _oz_snapshot()
    summary = _build_state_summary(snap, pack=_FakePack(_acts()))

    assert "witnessed_act_vocabulary" in summary
    vocab = summary["witnessed_act_vocabulary"]
    assert {v["id"] for v in vocab} == {"expose_the_humbug", "refuse_the_premise"}
    assert set(vocab[0].keys()) == {"id", "label", "description"}
    assert summary["present_npcs"] == ["Boq"]


def test_state_summary_omits_both_when_no_political_state():
    snap = _oz_snapshot()
    snap.political_state = None  # world ships no premise/bloc layer
    summary = _build_state_summary(snap, pack=_FakePack(_acts()))
    assert "witnessed_act_vocabulary" not in summary
    assert "present_npcs" not in summary


def test_state_summary_omits_both_when_pack_has_no_acts():
    snap = _oz_snapshot()
    summary = _build_state_summary(snap, pack=_FakePack([]))
    assert "witnessed_act_vocabulary" not in summary
    assert "present_npcs" not in summary


def test_state_summary_omits_both_without_pack():
    snap = _oz_snapshot()
    summary = _build_state_summary(snap)  # pack=None
    assert "witnessed_act_vocabulary" not in summary
    assert "present_npcs" not in summary


def test_vocabulary_injection_emits_span(otel_capture):
    snap = _oz_snapshot()
    _build_state_summary(snap, pack=_FakePack(_acts()))
    spans = [
        s for s in otel_capture.get_finished_spans()
        if s.name == "intent_router.witnessed_act_vocabulary"
    ]
    assert len(spans) == 1
    assert spans[0].attributes["act_count"] == 2
    assert spans[0].attributes["present_npc_count"] == 1
    assert spans[0].attributes["genre_slug"] == "wry_whimsy"


def test_no_vocabulary_span_in_non_political_world(otel_capture):
    snap = _oz_snapshot()
    snap.political_state = None
    _build_state_summary(snap, pack=_FakePack(_acts()))
    spans = [
        s for s in otel_capture.get_finished_spans()
        if s.name == "intent_router.witnessed_act_vocabulary"
    ]
    assert len(spans) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_vocabulary.py -v -n0`
Expected: FAIL — the new `test_state_summary_includes_*` assert `KeyError`/`assert "witnessed_act_vocabulary" in summary` fails (the projection does not exist yet).

- [ ] **Step 3: Add the projections + span to `_build_state_summary`**

In `sidequest-server/sidequest/server/intent_router_pass.py`, add the span import alongside the existing confrontation-vocabulary span import:

```python
from sidequest.telemetry.spans.intent_router import (
    intent_router_confrontation_vocabulary_span,
    intent_router_witnessed_act_vocabulary_span,
)
```

Then, inside `_build_state_summary`, after the existing `if pack is not None:` confrontation block and BEFORE `return summary`, insert:

```python
    # Witnessed-act vocabulary + witness candidate set (wry_whimsy political
    # substrate, Plan 2b). Double-gated: the pack must declare witnessed-act
    # archetypes AND the world must have hydrated a political layer
    # (snapshot.political_state). The second gate keeps us from prompting the
    # model to emit a dispatch the precondition gate would immediately drop —
    # and keeps every non-political genre's router prompt free of this noise.
    if (
        pack is not None
        and getattr(pack, "witnessed_acts", None)
        and snapshot.political_state is not None
    ):
        summary["witnessed_act_vocabulary"] = [
            {"id": a.id, "label": a.label, "description": a.description}
            for a in pack.witnessed_acts
        ]
        present = _present_npc_names(snapshot)
        summary["present_npcs"] = present
        with intent_router_witnessed_act_vocabulary_span(
            act_count=len(pack.witnessed_acts),
            present_npc_count=len(present),
            genre_slug=snapshot.genre_slug or "",
        ):
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_vocabulary.py -v -n0`
Expected: PASS (8 tests total in the file)

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/intent_router_pass.py tests/server/test_intent_router_witnessed_act_vocabulary.py
git commit -m "feat(server): surface witnessed_act vocabulary + present_npcs into router state summary"
```

---

### Task 4: Classification-result span after `decompose()`

**Files:**
- Modify: `sidequest-server/sidequest/server/intent_router_pass.py` (`execute_intent_router_pre_narrator_pass`)
- Test: `sidequest-server/tests/server/test_intent_router_witnessed_act_classified.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_intent_router_witnessed_act_classified.py`:

```python
"""Classification-result span after decompose (Plan 2b, Task 4)."""

from __future__ import annotations

from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest

from sidequest.game.belief_state import BeliefState
from sidequest.game.creature_core import CreatureCore, HpPool
from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot, Npc
from sidequest.genre.models.premises import WitnessedActArchetype
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    SubsystemDispatch,
)
from sidequest.server.intent_router_pass import execute_intent_router_pre_narrator_pass


class _FakePack:
    def __init__(self, witnessed_acts):
        self.witnessed_acts = witnessed_acts
        self.rules = None


class _StubRouter:
    """Records the state_summary it received and returns a fixed package."""

    def __init__(self, package: DispatchPackage):
        self._package = package
        self.seen_summary = None

    async def decompose(self, *, action, state_summary):
        self.seen_summary = state_summary
        return self._package


def _npc(name: str, *, location: str) -> Npc:
    return Npc(
        core=CreatureCore(
            name=name, description="A Munchkin villager.", personality="Hopeful.",
            hp=HpPool(current=10, max=10, base_max=10),
        ),
        belief_state=BeliefState(),
        location=location,
    )


def _oz_snapshot() -> GameSnapshot:
    snap = GameSnapshot(world_slug="oz")
    snap.genre_slug = "wry_whimsy"
    snap.player_seats = {"seat-1": "Dorothy"}
    snap.character_locations = {"Dorothy": "munchkin_country"}
    snap.npcs = [_npc("Boq", location="munchkin_country")]
    snap.political_state = PoliticalState(premises={}, blocs={}, ledger=[])
    return snap


def _acts():
    return [WitnessedActArchetype(id="expose_the_humbug", label="Expose the Humbug", description="x")]


def _package_with_witnessed_act() -> DispatchPackage:
    return DispatchPackage(
        turn_id="t1",
        per_player=[
            PlayerDispatch(
                player_id="Dorothy",
                raw_action="I pull the curtain aside in front of Boq",
                dispatch=[
                    SubsystemDispatch(
                        subsystem="witnessed_act",
                        params={"act_id": "expose_the_humbug", "witnesses": ["Boq"]},
                        idempotency_key="wa-1",
                        visibility={"visible_to": "all"},
                        confidence=0.9,
                    )
                ],
            )
        ],
        cross_player=[],
        confidence_global=0.9,
    )


def _empty_package() -> DispatchPackage:
    return DispatchPackage(turn_id="t2", per_player=[], cross_player=[], confidence_global=0.5)


@pytest.fixture
def otel_capture():
    from sidequest.telemetry.setup import init_tracer

    init_tracer()
    provider = otel_trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider)
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    try:
        yield exporter
    finally:
        processor.shutdown()


def _classified_spans(exporter):
    return [
        s for s in exporter.get_finished_spans()
        if s.name == "intent_router.witnessed_act_classified"
    ]


@pytest.mark.asyncio
async def test_classified_span_fires_with_emitted_count(otel_capture):
    snap = _oz_snapshot()
    router = _StubRouter(_package_with_witnessed_act())
    await execute_intent_router_pre_narrator_pass(
        intent_router=router, snapshot=snap, pack=_FakePack(_acts()),
        action="I pull the curtain aside", player_name="Dorothy",
    )
    # The router actually received the surfaced vocabulary.
    assert "witnessed_act_vocabulary" in router.seen_summary
    spans = _classified_spans(otel_capture)
    assert len(spans) == 1
    assert spans[0].attributes["emitted"] == 1
    assert spans[0].attributes["act_ids"] == "expose_the_humbug"
    assert spans[0].attributes["genre_slug"] == "wry_whimsy"


@pytest.mark.asyncio
async def test_classified_span_emitted_zero_when_router_declines(otel_capture):
    snap = _oz_snapshot()
    router = _StubRouter(_empty_package())
    await execute_intent_router_pre_narrator_pass(
        intent_router=router, snapshot=snap, pack=_FakePack(_acts()),
        action="I admire the scenery", player_name="Dorothy",
    )
    spans = _classified_spans(otel_capture)
    assert len(spans) == 1
    assert spans[0].attributes["emitted"] == 0


@pytest.mark.asyncio
async def test_no_classified_span_in_non_political_world(otel_capture):
    snap = _oz_snapshot()
    snap.political_state = None  # vocabulary not surfaced → no classification span
    router = _StubRouter(_empty_package())
    await execute_intent_router_pre_narrator_pass(
        intent_router=router, snapshot=snap, pack=_FakePack(_acts()),
        action="I admire the scenery", player_name="Dorothy",
    )
    assert _classified_spans(otel_capture) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_classified.py -v -n0`
Expected: FAIL — `test_classified_span_fires_with_emitted_count` finds 0 classification spans (the emit does not exist yet).

> If instead these fail with `MissingDatabaseUrlError`, the pass is reaching a DB-backed path it should not — re-check that the stub router short-circuits `decompose`; the fixtures here construct synthetic state and must not touch Postgres.

- [ ] **Step 3: Add the classification emit + a scan helper**

In `sidequest-server/sidequest/server/intent_router_pass.py`, extend the span import to include the classified span:

```python
from sidequest.telemetry.spans.intent_router import (
    intent_router_confrontation_vocabulary_span,
    intent_router_witnessed_act_classified_span,
    intent_router_witnessed_act_vocabulary_span,
)
```

Add a module-level scan helper (after `_present_npc_names`):

```python
def _witnessed_act_ids(package: DispatchPackage) -> list[str]:
    """Collect the act_ids of every witnessed_act dispatch in the package."""
    ids: list[str] = []
    for pd in package.per_player:
        for d in pd.dispatch:
            if d.subsystem == "witnessed_act":
                ids.append(str((d.params or {}).get("act_id", "")))
    for ca in package.cross_player:
        for d in ca.dispatch:
            if d.subsystem == "witnessed_act":
                ids.append(str((d.params or {}).get("act_id", "")))
    return ids
```

In `execute_intent_router_pre_narrator_pass`, the state summary is built then `decompose` is called:

```python
    state_summary = _build_state_summary(snapshot, pack=pack)
    package = await intent_router.decompose(
        action=action,
        state_summary=state_summary,
    )
```

Immediately AFTER that `package = await intent_router.decompose(...)` assignment, insert the classification emit (before the existing `run_unregistered_subsystem_gate` line):

```python
    # Classification-result observability (Plan 2b): only when the vocabulary
    # was surfaced this turn (a political world) — so the GM panel can see the
    # router's front-door decision, "classified as witnessed_act:X" vs "had the
    # vocabulary and declined". Fires before the gates so it reflects the raw
    # router output, not the post-gate package.
    if "witnessed_act_vocabulary" in state_summary:
        act_ids = _witnessed_act_ids(package)
        with intent_router_witnessed_act_classified_span(
            emitted=len(act_ids),
            act_ids=",".join(act_ids),
            genre_slug=snapshot.genre_slug or "",
        ):
            pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_intent_router_witnessed_act_classified.py -v -n0`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/intent_router_pass.py tests/server/test_intent_router_witnessed_act_classified.py
git commit -m "feat(server): emit intent_router.witnessed_act_classified span on router decision"
```

---

### Task 5: Static prompt vocabulary entry

**Files:**
- Modify: `sidequest-server/sidequest/agents/intent_router.py` (`_SYSTEM_PROMPT`)

This is the prompt-engineering core: it teaches the model the `witnessed_act` subsystem exists, its params, the closed-enum/witness rules, and honest-confidence discipline. There is **no isolated unit test** for the static prompt string — asserting a literal appears in the source would be a forbidden source-text wiring test (`sidequest-server/CLAUDE.md` → "No Source-Text Wiring Tests"). Its delivery is proven behaviorally by Task 4 (`router.seen_summary` carries the vocabulary) and Task 6 (a stub emitting `witnessed_act` engages the engine end-to-end); its classification *quality* is an eval/playtest concern, not a unit assertion.

- [ ] **Step 1: Add the vocabulary entry**

In `sidequest-server/sidequest/agents/intent_router.py`, inside `_SYSTEM_PROMPT`, find the `- reflect_absence: player addresses someone/something not present.` line (the last subsystem bullet, just before the `Every dispatch carries a per-dispatch confidence` paragraph) and insert this block immediately AFTER it (keep the leading whitespace matching the surrounding bullets):

```python
       - witnessed_act: the player commits an EARNED, PUBLIC act that
         contradicts a belief-powered authority or shows a cowed population
         that defiance survives (pull the curtain on a humbug, name the trick
         to the authority's face, break a forbidden rule and walk away unharmed,
         help a population take a first collective refusal). params={
           "act_id": "<one of game_state.witnessed_act_vocabulary[].id>",
           "witnesses": ["<names drawn ONLY from game_state.present_npcs>"]
         }.
         Emit this ONLY when game_state.witnessed_act_vocabulary is present.
         The act_id MUST be one of the listed vocabulary ids — never invent an
         act. witnesses are the people who PERCEIVE the act; populate it only
         from game_state.present_npcs. An act with NO witness moves nothing
         (exposing a humbug in an empty room changes nothing): if no one present
         perceives it, emit an empty witnesses list and a LOW confidence. Do not
         invent a witness who is not in present_npcs. Reshaping a society is
         earned — score confidence honestly; a low score degrades to a narrator
         hint instead of moving the political dials.
```

- [ ] **Step 2: Verify the module still imports (syntax sound)**

Run: `uv run python -c "import sidequest.agents.intent_router; print('intent_router ok')"`
Expected: prints `intent_router ok`

- [ ] **Step 3: Verify no regression in the existing router/decompose tests**

Run: `uv run pytest tests/agents/ -k "intent_router or decompose" -v -n0`
Expected: PASS (the prompt is additive; existing decompose tests inject mocks and do not assert on prompt text).

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/intent_router.py
git commit -m "feat(agents): teach intent router the witnessed_act subsystem vocabulary"
```

---

### Task 6: Wiring test — router emission → bank → engine mutates `political_state`

**Files:**
- Test: `sidequest-server/tests/server/test_witnessed_act_router_to_engine.py`

This is the plan's **integration anchor** (project rule: every test suite needs a wiring test). It drives the production `execute_intent_router_pre_narrator_pass` with a STUB router (no real Claude — `IntentRouter` is dependency-injected, so no monkeypatch is needed) that returns a `witnessed_act` package, on a hydrated Oz-shaped snapshot, and proves the dispatch flows through the real `run_dispatch_bank` and **mutates the authoritative dials** — closing the loop the merged Plan-2 integration test left open (it hand-built the package; here the router "emits" it through the production pass).

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_witnessed_act_router_to_engine.py`:

```python
"""witnessed_act: router emission flows through the pass into the engine (Plan 2b, Task 6)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sidequest.game.belief_state import BeliefState
from sidequest.game.creature_core import CreatureCore, HpPool
from sidequest.game.political_state import PoliticalState
from sidequest.game.session import GameSnapshot, Npc
from sidequest.genre.models.premises import (
    BlocAwakening,
    BlocDef,
    PremiseClaim,
    PremiseCollapse,
    PremiseDef,
    PremiseDrain,
)
from sidequest.genre.models.premises import WitnessedActArchetype
from sidequest.protocol.dispatch import (
    DispatchPackage,
    PlayerDispatch,
    SubsystemDispatch,
)
from sidequest.server.intent_router_pass import execute_intent_router_pre_narrator_pass


def _humbug() -> PremiseDef:
    return PremiseDef(
        premise_id="the_wizards_humbug",
        authority="oz_the_great",
        claim=PremiseClaim(subject="oz_the_great", proposition="great and terrible"),
        belief_reserve=90,
        propped_by=["munchkins"],
        drained_by=[PremiseDrain(act="expose_the_humbug", belief_delta=40)],
        collapse=PremiseCollapse(threshold=20, outcome="He flees in his balloon."),
    )


def _munchkins() -> BlocDef:
    return BlocDef(
        bloc_id="munchkins",
        defiance=5,
        grants_belief_to=["the_wizards_humbug"],
        awakening_acts=[BlocAwakening(act="organize_a_first_small_refusal", defiance_delta=10)],
        tipping_threshold=70,
        tipped_outcome="The Munchkins revolt.",
    )


def _oz_world():
    return SimpleNamespace(premises=[_humbug()], blocs=[_munchkins()])


def _oz_pack():
    return SimpleNamespace(
        worlds={"oz": _oz_world()},
        witnessed_acts=[
            WitnessedActArchetype(id="expose_the_humbug", label="Expose the Humbug", description="x"),
        ],
        rules=None,
    )


def _npc(name: str, *, location: str) -> Npc:
    return Npc(
        core=CreatureCore(
            name=name, description="A Munchkin villager.", personality="Hopeful.",
            hp=HpPool(current=10, max=10, base_max=10),
        ),
        belief_state=BeliefState(),
        location=location,
    )


def _oz_snapshot() -> GameSnapshot:
    snap = GameSnapshot(world_slug="oz")
    snap.genre_slug = "wry_whimsy"
    snap.player_seats = {"seat-1": "Dorothy"}
    snap.character_locations = {"Dorothy": "munchkin_country"}
    snap.npcs = [_npc("Boq", location="munchkin_country")]
    snap.political_state = PoliticalState.from_world(_oz_world())
    return snap


class _StubRouter:
    def __init__(self, package):
        self._package = package
        self.seen_summary = None

    async def decompose(self, *, action, state_summary):
        self.seen_summary = state_summary
        return self._package


def _package() -> DispatchPackage:
    return DispatchPackage(
        turn_id="t1",
        per_player=[
            PlayerDispatch(
                player_id="Dorothy",
                raw_action="I pull the green curtain aside in front of Boq",
                dispatch=[
                    SubsystemDispatch(
                        subsystem="witnessed_act",
                        params={"act_id": "expose_the_humbug", "witnesses": ["Boq"]},
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
async def test_router_emitted_witnessed_act_engages_the_engine():
    snap = _oz_snapshot()
    router = _StubRouter(_package())

    await execute_intent_router_pre_narrator_pass(
        intent_router=router,
        snapshot=snap,
        pack=_oz_pack(),
        action="I pull the green curtain aside in front of Boq",
        player_name="Dorothy",
    )

    # The router received the surfaced vocabulary + witness candidate set.
    assert "witnessed_act_vocabulary" in router.seen_summary
    assert router.seen_summary["present_npcs"] == ["Boq"]

    # The engine actually moved the authoritative dials via the production path.
    assert snap.political_state.premises["the_wizards_humbug"].belief_reserve == 50  # 90 - 40
    assert snap.political_state.blocs["munchkins"].defiance == 25  # 5 + floor(40*0.5)

    # The ledger kept the receipt naming the witness.
    drained = [le for le in snap.political_state.ledger if le.effect == "drained"]
    assert drained and drained[0].witnesses == ["Boq"]

    # ADR-053 reuse: the witness received a contradicting belief.
    assert len(snap.npcs[0].belief_state.beliefs) == 1
```

- [ ] **Step 2: Run test to verify it fails (or passes) and adjust to real shapes**

Run: `uv run pytest tests/server/test_witnessed_act_router_to_engine.py -v -n0`

This test exercises already-built code (Tasks 2-4 + the merged engine), so it may PASS immediately once Tasks 2-4 are in. If it fails:
- On `DispatchPackage`/`PlayerDispatch`/`SubsystemDispatch` shape → re-read `sidequest/protocol/dispatch.py` and match field names (confirmed at plan time: `PlayerDispatch(player_id, raw_action, dispatch=[…])`, `DispatchPackage(turn_id, per_player, cross_player, confidence_global)`).
- On the bank not passing `npcs`/`player_name` to the handler → re-read the context dict in `execute_intent_router_pre_narrator_pass` (it already threads `snapshot`, `pack`, `player_name`, `npcs`) and the handler signature `run_witnessed_act_dispatch(dispatch, *, snapshot, pack, player_name, npcs)`; the bank signature-filters context by declared kwargs.
- The load-bearing assertions are the `political_state` mutations (50 / 25) + the ledger receipt; adjust only the constructor wiring, never those numbers.

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_witnessed_act_router_to_engine.py
git commit -m "test(server): witnessed_act router emission engages the engine end-to-end through the pass"
```

---

### Task 7: Full-suite regression sweep + lint

**Files:** none (verification only)

- [ ] **Step 1: Lint + format the touched files**

Run:
```bash
uv run ruff check sidequest/telemetry/spans/intent_router.py sidequest/server/intent_router_pass.py sidequest/agents/intent_router.py tests/telemetry/test_intent_router_witnessed_act_spans.py tests/server/test_intent_router_witnessed_act_vocabulary.py tests/server/test_intent_router_witnessed_act_classified.py tests/server/test_witnessed_act_router_to_engine.py
uv run ruff format sidequest/telemetry/spans/intent_router.py sidequest/server/intent_router_pass.py sidequest/agents/intent_router.py tests/telemetry/test_intent_router_witnessed_act_spans.py tests/server/test_intent_router_witnessed_act_vocabulary.py tests/server/test_intent_router_witnessed_act_classified.py tests/server/test_witnessed_act_router_to_engine.py
```
Expected: clean (or auto-fixed by format).

- [ ] **Step 2: Run the new suites serially (OTEL deadlock avoidance)**

Run:
```bash
uv run pytest -n0 \
  tests/telemetry/test_intent_router_witnessed_act_spans.py \
  tests/server/test_intent_router_witnessed_act_vocabulary.py \
  tests/server/test_intent_router_witnessed_act_classified.py \
  tests/server/test_witnessed_act_router_to_engine.py -v
```
Expected: PASS (all).

- [ ] **Step 3: Run the adjacent router/telemetry suites to confirm no regression**

Run:
```bash
uv run pytest -n0 \
  tests/server/test_intent_router_confrontation_vocabulary.py \
  tests/agents/test_witnessed_act_subsystem.py \
  tests/agents/test_witnessed_act_integration.py -v
```
Expected: PASS (the confrontation-vocabulary suite proves the shared `_build_state_summary` path is intact; the merged Plan-2 suites prove the engine is untouched).

> Many `tests/server/` flow tests require `SIDEQUEST_DATABASE_URL` and fail with `MissingDatabaseUrlError` if no Postgres is provisioned — that's environmental, not a regression (`just pg-up` provisions local Postgres). The four new suites are constructed to avoid Postgres.

- [ ] **Step 4: Commit any lint/format fixups**

```bash
git add -A
git commit -m "chore: ruff format/lint fixups for witnessed_act router classification" || echo "nothing to commit"
```

---

## Self-Review

**1. Spec coverage (design doc §4):**
- §4.2 Edit A — static prompt vocabulary entry (closed-enum `act_id`, witnesses from `present_npcs`, no-witness rule, honest confidence) → Task 5 ✓
- §4.3 Edit B — `witnessed_act_vocabulary` + `present_npcs` projections, double-gated on `pack.witnessed_acts` AND `political_state`; vocabulary span → Tasks 2 (present helper) + 3 (projections + span) ✓
- §4.4 Edit C — `intent_router.witnessed_act_classified` span after `decompose`, emitted-vs-not, gated on vocabulary-surfaced → Tasks 1 (span) + 4 (emit) ✓
- §7 Testing — projection gating (Task 3), `present_npcs` correctness (Task 2), vocabulary span (Task 3), classification span (Task 4), end-to-end wiring (Task 6) ✓
- §6 Out of scope — no content change (no `sidequest-content` task), no engine change (engine follow-ups omitted) ✓

**2. Placeholder scan:** Every step has concrete code/commands. Task 5 has no isolated unit test by design (forbidden source-text assertion) — its delivery is proven behaviorally in Tasks 4 & 6; this is an explicit, justified choice, not a blank. Task 6 Step 2 carries concrete fallback instructions with the real field names, not a vague "fix it".

**3. Type consistency:**
- `_present_npc_names(snapshot: GameSnapshot) -> list[str]` — defined Task 2, called in Task 3 (`_build_state_summary`). ✓
- `_witnessed_act_ids(package: DispatchPackage) -> list[str]` — defined Task 4, called in same function. ✓
- Span constants `SPAN_INTENT_ROUTER_WITNESSED_ACT_VOCABULARY` / `_CLASSIFIED` + contextmanagers `intent_router_witnessed_act_vocabulary_span(act_count, present_npc_count, genre_slug)` / `intent_router_witnessed_act_classified_span(emitted, act_ids, genre_slug)` — defined Task 1, imported/used Tasks 3 & 4. ✓
- `is_npc_in_scene(npc, *, current_room, encounter)` — existing (`sidequest/game/npc_scene.py`), used Task 2. ✓
- `WitnessedActArchetype(id, label, description)` — existing (`sidequest/genre/models/premises.py`), used Tasks 2-6. ✓
- Dispatch shapes `DispatchPackage(turn_id, per_player, cross_player, confidence_global)`, `PlayerDispatch(player_id, raw_action, dispatch)`, `SubsystemDispatch(subsystem, params, idempotency_key, visibility, confidence)` — confirmed against `sidequest/protocol/dispatch.py`, used Tasks 4 & 6. ✓
- `Npc(core=CreatureCore(name, description, personality, hp=HpPool(current, max, base_max)), belief_state=BeliefState(), location=…)` — confirmed against the merged Plan-2 test idiom + `creature_core.py`. ✓
- `snapshot.party_location()`, `snapshot.player_seats`, `snapshot.character_locations`, `snapshot.political_state`, `snapshot.genre_slug` — confirmed on `GameSnapshot`. ✓

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-02-wry-whimsy-premise-router-classification.md`.

Recommended: **Subagent-Driven** (REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`) — fresh implementer per task, two-stage spec→quality review between tasks, controller verifies the real code shapes (dispatch model fields, `is_npc_in_scene` signature, the `_SYSTEM_PROMPT` insertion anchor) before dispatching each task. Tasks 1-5 are sequential (each builds on the prior); Task 6 is the integration capstone; Task 7 is the regression sweep.
