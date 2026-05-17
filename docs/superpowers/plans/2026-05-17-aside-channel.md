# Out-of-Band Aside Channel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the half-wired `aside` feature so a player can ask the GM a clarifying question without consuming a turn, advancing the world, or blocking the multiplayer barrier — answered out-of-character, table-visible, OTEL-audited.

**Architecture:** Approach A from the spec — reuse the existing inbound `aside: bool` on `PLAYER_ACTION`; branch at the `handlers/player_action.py` entry *before* the ADR-036 barrier; resolve via a read-only `AsideResolver` (no write path); return a new typed `ASIDE_ANSWER` message broadcast to the whole room; emit a routed `aside.resolve` span. Correct the `api-contract.md` lie and author ADR-107.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 (`sidequest-server`, `uv`); React/TypeScript/Vitest (`sidequest-ui`); OpenTelemetry span registry (`sidequest.telemetry.spans`); ADR-101 Anthropic SDK LLM factory.

**Spec:** `docs/superpowers/specs/2026-05-17-aside-channel-design.md`

---

## File Structure

**`sidequest-server` (branch `feat/aside-channel`, base `develop`):**
- Modify `sidequest/protocol/enums.py` — add `ASIDE_ANSWER` to `MessageType`
- Modify `sidequest/protocol/messages.py` — add `AsideAnswerPayload`
- Create `sidequest/telemetry/spans/aside.py` — routed `aside.resolve` span
- Modify `sidequest/telemetry/spans/__init__.py` — register the new span module
- Create `sidequest/agents/aside_resolver.py` — read-only `AsideResolver`
- Modify `sidequest/handlers/player_action.py` — branch on `aside` before the barrier
- Create `tests/agents/test_aside_resolver.py`
- Create `tests/handlers/test_aside_channel_wiring.py` — the mandatory MP wiring test
- Modify `tests/protocol/test_enums.py` — enum-count pin (if present)

**`sidequest-ui` (branch `feat/aside-channel`, base `develop`):**
- Modify `src/types/protocol.ts` — `ASIDE_ANSWER` + payload type
- Modify `src/App.tsx` — route `ASIDE_ANSWER` into the narrative stream
- Modify `src/lib/narrativeSegments.ts` — `gm-aside` segment kind
- Modify `src/components/InputBar.tsx` — placeholder copy
- Modify/create vitest specs alongside the above

**`oq-1` orchestrator (branch `docs/aside-channel-spec`, base `main`):**
- Modify `docs/api-contract.md` — correct the aside contract
- Create `docs/adr/107-out-of-band-aside-channel.md`
- Create `tests/`-style doc-contract guard (see Task 8)

> **Cross-repo note:** subrepos branch off `develop`; the orchestrator off `main`. Create the subrepo branches BEFORE implementing or commits land on `develop`.

---

### Task 0: Branch setup

**Files:** none (git only)

- [ ] **Step 1: Create server branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git fetch origin && git checkout develop && git pull --ff-only
git checkout -b feat/aside-channel
git branch --show-current   # expect: feat/aside-channel
```

- [ ] **Step 2: Create UI branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui
git fetch origin && git checkout develop && git pull --ff-only
git checkout -b feat/aside-channel
git branch --show-current   # expect: feat/aside-channel
```

- [ ] **Step 3: Confirm orchestrator branch**

```bash
cd /Users/slabgorb/Projects/oq-1
git branch --show-current   # expect: docs/aside-channel-spec
```

---

### Task 1: Server protocol — `ASIDE_ANSWER` message type + payload

**Files:**
- Modify: `sidequest-server/sidequest/protocol/enums.py` (`MessageType`, after `ACTION_REVEAL`)
- Modify: `sidequest-server/sidequest/protocol/messages.py` (new `AsideAnswerPayload`)
- Test: `sidequest-server/tests/protocol/test_aside_payload.py` (create)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/protocol/test_aside_payload.py`:

```python
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import AsideAnswerPayload


def test_aside_answer_message_type_exists():
    assert MessageType.ASIDE_ANSWER == "ASIDE_ANSWER"


def test_aside_answer_payload_roundtrips():
    p = AsideAnswerPayload(
        asker_id="Hiken",
        question="can I wade or must I be carried?",
        answer="Knee-deep on you, Hiken. Wading's slow but no carry needed.",
        grounded_on=["character.size", "region.water_depth"],
        round=7,
    )
    dumped = p.model_dump()
    assert dumped["asker_id"] == "Hiken"
    assert dumped["grounded_on"] == ["character.size", "region.water_depth"]
    assert AsideAnswerPayload(**dumped).answer.startswith("Knee-deep")


def test_aside_answer_payload_defaults_are_safe():
    p = AsideAnswerPayload()
    assert p.asker_id == "" and p.answer == "" and p.grounded_on == [] and p.round == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_aside_payload.py -v`
Expected: FAIL — `ImportError: cannot import name 'AsideAnswerPayload'` / `AttributeError: ASIDE_ANSWER`

- [ ] **Step 3: Add the enum member**

In `sidequest/protocol/enums.py`, in `class MessageType(StrEnum)`, immediately after the `ACTION_REVEAL = "ACTION_REVEAL"` line, add:

```python
    ASIDE_ANSWER = "ASIDE_ANSWER"
```

- [ ] **Step 4: Add the payload**

In `sidequest/protocol/messages.py`, after the `ActionRevealPayload` class, add:

```python
class AsideAnswerPayload(ProtocolBase):
    """OOC GM answer to a player aside (ADR-107).

    Never a turn record: emitting this does not advance the world, the
    turn/round counter, the narrative log, or the scrapbook. ``round`` is
    carried for client ordering only.
    """

    asker_id: str = ""
    """Player/character id that asked."""
    question: str = ""
    """Verbatim aside text the player submitted."""
    answer: str = ""
    """The GM's out-of-character reply (1-3 sentences)."""
    grounded_on: list[str] = Field(default_factory=list)
    """State keys the answer was derived from — the audit trail. Empty on
    a refusal/decline outcome."""
    round: int = 0
    """Current round at ask time. Ordering only — NOT a turn record."""
```

If `Field` is not already imported in `messages.py`, add `from pydantic import Field` to the existing pydantic import (grep `^from pydantic` to confirm; do not duplicate).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_aside_payload.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Update the enum-count pin if one exists**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_enums.py -v`
If a test asserts a fixed `len(MessageType)` (e.g. `assert count == 46`), bump it by 1 (e.g. `47`) — this is an intentional addition, not a regression. If no such test exists, skip.

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/protocol/enums.py sidequest/protocol/messages.py tests/protocol/test_aside_payload.py
# include tests/protocol/test_enums.py only if you bumped the pin
git commit -m "feat(protocol): ASIDE_ANSWER message type + AsideAnswerPayload (ADR-107)"
```

---

### Task 2: Server telemetry — routed `aside.resolve` span

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/aside.py`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py` (add star-import)
- Test: `sidequest-server/tests/telemetry/test_routing_completeness.py` (already exists — used as the gate, not modified)

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_aside_span.py`:

```python
from sidequest.telemetry.spans import SPAN_ROUTES
from sidequest.telemetry.spans.aside import SPAN_ASIDE_RESOLVE


def test_aside_resolve_is_routed():
    assert SPAN_ASIDE_RESOLVE == "aside.resolve"
    assert SPAN_ASIDE_RESOLVE in SPAN_ROUTES
    route = SPAN_ROUTES[SPAN_ASIDE_RESOLVE]
    assert route.event_type == "state_transition"
    assert route.component == "aside"


def test_aside_resolve_extract_pulls_attributes():
    route = SPAN_ROUTES[SPAN_ASIDE_RESOLVE]

    class _Span:
        name = "aside.resolve"
        attributes = {
            "asker_id": "Hiken",
            "outcome": "answered",
            "grounded_on": "character.size,region.water_depth",
            "model": "haiku",
            "latency_ms": 412,
        }

    fields = route.extract(_Span())
    assert fields["asker_id"] == "Hiken"
    assert fields["outcome"] == "answered"
    assert fields["op"] == "resolved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_aside_span.py -v`
Expected: FAIL — `ModuleNotFoundError: sidequest.telemetry.spans.aside`

- [ ] **Step 3: Create the span module**

Create `sidequest/telemetry/spans/aside.py`:

```python
"""Aside spans — out-of-band player→GM table-talk (ADR-107).

``aside.resolve`` fires on every aside resolution so Sebastien's GM panel
(CLAUDE.md "OTEL Observability Principle") proves the channel engaged and
exposes whether the answer was grounded. Routed (not flat-only) because an
ungrounded aside is exactly the kind of narrator-lie the panel must catch.
"""

from __future__ import annotations

from ._core import SPAN_ROUTES, SpanRoute

SPAN_ASIDE_RESOLVE = "aside.resolve"

SPAN_ROUTES[SPAN_ASIDE_RESOLVE] = SpanRoute(
    event_type="state_transition",
    component="aside",
    extract=lambda span: {
        "field": "aside",
        "op": "resolved",
        "asker_id": (span.attributes or {}).get("asker_id", ""),
        "outcome": (span.attributes or {}).get("outcome", ""),
        "grounded_on": (span.attributes or {}).get("grounded_on", ""),
        "model": (span.attributes or {}).get("model", ""),
        "latency_ms": (span.attributes or {}).get("latency_ms", 0),
    },
)
```

- [ ] **Step 4: Register the module**

In `sidequest/telemetry/spans/__init__.py`, find the alphabetically-ordered star-import block (`from .agent import *`, `from .asset_url import *`, ...). Insert between `.agent` and `.asset_url` (alpha order: `aside` < `asset_url`):

```python
from .aside import *  # noqa: F401, F403
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_aside_span.py tests/telemetry/test_routing_completeness.py -v`
Expected: PASS — new span tests pass AND `test_every_span_is_routed_or_explicitly_flat` / `test_routes_target_known_event_types` still pass (the new span is routed with a known `event_type`).

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/telemetry/spans/aside.py sidequest/telemetry/spans/__init__.py tests/telemetry/test_aside_span.py
git commit -m "feat(telemetry): routed aside.resolve span (ADR-107)"
```

---

### Task 3: Server — read-only `AsideResolver`

**Files:**
- Create: `sidequest-server/sidequest/agents/aside_resolver.py`
- Test: `sidequest-server/tests/agents/test_aside_resolver.py` (create)

The resolver has **no write path**. It takes a read view and a question, asks the LLM with a policy system-prompt, and returns a structured resolution. The LLM is injected behind a `Protocol` so unit tests assert policy without a live model.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/agents/test_aside_resolver.py`:

```python
import pytest

from sidequest.agents.aside_resolver import (
    AsideReadView,
    AsideResolver,
    AsideResolution,
)


def _view() -> AsideReadView:
    return AsideReadView(
        character_summary="Hiken, halfling, Small, unencumbered.",
        region_summary="Flooded chamber, standing water ankle-deep for a human.",
        inventory=["torch", "sling"],
        rulebook_summary="Small creatures wade in water rated knee-deep-or-less.",
        recent_narration="The door bursts; black water ankle-deep across the floor.",
    )


class _FakeLLM:
    """Returns whatever JSON the test wires, capturing the system prompt."""

    def __init__(self, payload: str):
        self.payload = payload
        self.seen_system = ""

    async def complete(self, *, system: str, user: str) -> str:
        self.seen_system = system
        return self.payload


@pytest.mark.asyncio
async def test_capability_question_is_answered_and_grounded():
    llm = _FakeLLM(
        '{"answer":"Knee-deep on you, Hiken — wading is slow but fine, no carry.",'
        '"outcome":"answered","grounded_on":["character.size","region.water_depth"]}'
    )
    res = await AsideResolver(llm=llm).resolve(
        question="can I wade or must I be carried?", read_view=_view()
    )
    assert isinstance(res, AsideResolution)
    assert res.outcome == "answered"
    assert res.grounded_on == ("character.size", "region.water_depth")
    assert "wading" in res.answer.lower()


@pytest.mark.asyncio
async def test_hidden_state_question_is_refused():
    llm = _FakeLLM(
        '{"answer":"You\\u0027d have to check — that\\u0027s an action, not a question.",'
        '"outcome":"refused_hidden_state","grounded_on":[]}'
    )
    res = await AsideResolver(llm=llm).resolve(
        question="is the far door trapped?", read_view=_view()
    )
    assert res.outcome == "refused_hidden_state"
    assert res.grounded_on == ()


@pytest.mark.asyncio
async def test_policy_is_in_system_prompt():
    llm = _FakeLLM('{"answer":"x","outcome":"answered","grounded_on":["a"]}')
    await AsideResolver(llm=llm).resolve(question="how does Edge work?", read_view=_view())
    sys = llm.seen_system.lower()
    assert "out-of-character" in sys or "ooc" in sys
    assert "you'd have to check" in sys or "action, not a question" in sys


@pytest.mark.asyncio
async def test_unparseable_llm_output_declines_loudly_not_improvises():
    res = await AsideResolver(llm=_FakeLLM("not json at all")).resolve(
        question="anything", read_view=_view()
    )
    assert res.outcome == "resolver_error"
    assert res.grounded_on == ()
    assert res.answer  # a non-empty loud "ask again" message, never invented lore


@pytest.mark.asyncio
async def test_resolver_has_no_write_surface():
    # Structural guarantee: the resolver exposes only `resolve`. No method
    # name hints at mutation.
    public = [m for m in dir(AsideResolver) if not m.startswith("_")]
    assert public == ["resolve"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/agents/test_aside_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: sidequest.agents.aside_resolver`

- [ ] **Step 3: Implement the resolver**

Create `sidequest/agents/aside_resolver.py`:

```python
"""Read-only out-of-band aside resolver (ADR-107).

A GM ruling, not a story beat. Receives a *read* view of state and returns
a short OOC answer. It holds no write path — it structurally cannot advance
the world, mutate inventory, tick tropes, or touch the dungeon. "No turn
consumed" is enforced by this object having no hands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

_VALID_OUTCOMES = {
    "answered",
    "refused_hidden_state",
    "refused_would_advance",
    "ungrounded_declined",
    "resolver_error",
}

_SYSTEM_PROMPT = """You are the GM answering a player's OUT-OF-CHARACTER aside \
during a tabletop session. This is table-talk, not narration. The fiction is \
FROZEN — nothing you say moves the world.

ANSWER (1-3 plain sentences, second-person GM voice):
- Capability/perception the character would already know (size, encumbrance, \
stated depth, what they can see/reach).
- Rules/genre mechanics from the rulebook summary.
- Recap from the recent narration / inventory.

REFUSE by saying "You'd have to check — that's an action, not a question." \
(outcome refused_hidden_state) for hidden world state: traps, unseen creature \
stats, what's behind an unopened door, anything the character has not earned.

If answering honestly would require the world to change, outcome \
refused_would_advance and point back to the action box.

If the provided state does not contain the answer, outcome \
ungrounded_declined and say the game doesn't pin it down — never invent.

grounded_on MUST list the state keys you used (e.g. character.size, \
region.water_depth, rulebook, inventory, recent_narration). Empty only on a \
refusal/decline.

Respond ONLY as compact JSON: \
{"answer": str, "outcome": str, "grounded_on": [str, ...]}"""


@dataclass(frozen=True)
class AsideReadView:
    """Immutable read slice handed to the resolver. No setters, no handles."""

    character_summary: str
    region_summary: str
    inventory: list[str]
    rulebook_summary: str
    recent_narration: str


@dataclass(frozen=True)
class AsideResolution:
    answer: str
    outcome: str
    grounded_on: tuple[str, ...]


class AsideLLM(Protocol):
    async def complete(self, *, system: str, user: str) -> str: ...


class AsideResolver:
    def __init__(self, llm: AsideLLM) -> None:
        self._llm = llm

    async def resolve(
        self, *, question: str, read_view: AsideReadView
    ) -> AsideResolution:
        user = (
            f"CHARACTER: {read_view.character_summary}\n"
            f"REGION: {read_view.region_summary}\n"
            f"INVENTORY: {', '.join(read_view.inventory) or '(none)'}\n"
            f"RULEBOOK: {read_view.rulebook_summary}\n"
            f"RECENT: {read_view.recent_narration}\n\n"
            f"PLAYER ASIDE: {question}"
        )
        try:
            raw = await self._llm.complete(system=_SYSTEM_PROMPT, user=user)
            data = json.loads(raw)
            outcome = str(data.get("outcome", ""))
            if outcome not in _VALID_OUTCOMES:
                raise ValueError(f"invalid outcome {outcome!r}")
            grounded = tuple(str(g) for g in data.get("grounded_on", []))
            answer = str(data.get("answer", "")).strip()
            if not answer:
                raise ValueError("empty answer")
            return AsideResolution(
                answer=answer, outcome=outcome, grounded_on=grounded
            )
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            # No Silent Fallbacks: loud, honest, never invents lore.
            return AsideResolution(
                answer="(The GM didn't catch that — ask again.)",
                outcome="resolver_error",
                grounded_on=(),
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/agents/test_aside_resolver.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/agents/aside_resolver.py tests/agents/test_aside_resolver.py
git commit -m "feat(agents): read-only AsideResolver with GM-craft answer policy (ADR-107)"
```

---

### Task 4: Server — branch on `aside` before the barrier

**Files:**
- Modify: `sidequest-server/sidequest/handlers/player_action.py` (the `handle()` entry; existing aside block ~line 132-141)
- Modify: `sidequest-server/sidequest/agents/llm_factory.py` — none if a Haiku-tier helper already exists; otherwise wire the real `AsideLLM` adapter here (see Step 3)
- Test: covered by Task 5 (the wiring test is the real assertion; this task makes it reachable)

- [ ] **Step 1: Locate the seam**

Run: `cd sidequest-server && grep -n "aside\|def handle\|pending_actions\|TurnManager\|return \[" sidequest/handlers/player_action.py | head -40`
Identify: (a) the `async def handle(...)` entry and its return type (a `list[GameMessage]`), (b) the existing `if getattr(payload, "aside", False):` combat-strip block, (c) the first line that enqueues into the MP barrier (`pending_actions` / `TurnManager`). The new branch must sit **after** payload+action are resolved and **before** the barrier enqueue.

- [ ] **Step 2: Write/extend the aside branch**

Replace the existing combat-strip-only aside block with a full branch. The combat-strip is retained (so `[combat]` markers don't leak into the question), then the resolver runs and the handler RETURNS immediately — never reaching the barrier:

```python
        if getattr(payload, "aside", False):
            from sidequest.server.dispatch.combat_brackets import (
                strip_combat_brackets,
            )

            question = strip_combat_brackets(action).strip()
            if not question:
                return [_error_msg("Player aside is empty")]

            from sidequest.agents.aside_resolver import (
                AsideReadView,
                AsideResolver,
            )
            from sidequest.agents.llm_factory import build_aside_llm
            from sidequest.protocol.enums import MessageType
            from sidequest.protocol.messages import AsideAnswerPayload
            from sidequest.telemetry.spans import SPAN_ASIDE_RESOLVE
            from sidequest.telemetry.setup import tracer

            read_view = AsideReadView(
                character_summary=snapshot.describe_character(player_id),
                region_summary=snapshot.describe_current_region(),
                inventory=snapshot.inventory_names(player_id),
                rulebook_summary=snapshot.genre_rulebook_summary(),
                recent_narration=snapshot.recent_narration_window(),
            )
            with tracer().start_as_current_span(SPAN_ASIDE_RESOLVE) as span:
                import time

                t0 = time.monotonic()
                res = await AsideResolver(llm=build_aside_llm()).resolve(
                    question=question, read_view=read_view
                )
                span.set_attribute("asker_id", player_id)
                span.set_attribute("outcome", res.outcome)
                span.set_attribute("grounded_on", ",".join(res.grounded_on))
                span.set_attribute("model", "haiku")
                span.set_attribute(
                    "latency_ms", int((time.monotonic() - t0) * 1000)
                )

            answer_msg = _broadcast_msg(
                MessageType.ASIDE_ANSWER,
                AsideAnswerPayload(
                    asker_id=player_id,
                    question=question,
                    answer=res.answer,
                    grounded_on=list(res.grounded_on),
                    round=snapshot.current_round(),
                ),
            )
            # Out-of-band: do NOT enqueue into pending_actions / TurnManager,
            # do NOT advance turn/round, do NOT touch scrapbook or world.
            return [answer_msg]
```

> **Adapt to the real handler:** the helpers `snapshot.describe_character` / `describe_current_region` / `inventory_names` / `genre_rulebook_summary` / `recent_narration_window` / `current_round` and `_broadcast_msg` are named per intent. If the snapshot/room object exposes these under different names, use the real ones (grep the handler's existing reads — it already builds turn context from a snapshot for narration; reuse those exact accessors). `_broadcast_msg` must produce a message the room fan-out delivers to **all seats** (find how `NARRATION` is broadcast room-wide in this handler / the session room and mirror it — `ASIDE_ANSWER` is table-visible per spec §5). Do not invent a new broadcast path.

- [ ] **Step 3: Provide the Haiku-tier LLM adapter**

Run: `cd sidequest-server && grep -n "def build_\|haiku\|Haiku\|model=\|claude-haiku" sidequest/agents/llm_factory.py | head`
If a Haiku-tier client builder exists, add a thin `build_aside_llm()` that returns an object satisfying `AsideLLM` (`async def complete(*, system, user) -> str`) backed by it (ADR-101 per-call routing — cheapest tier; "Cost Scales with Drama"). If the factory exposes a generic per-model builder, wrap it. Keep the adapter in `llm_factory.py` next to the other builders. Do **not** route asides through the full narrator/orchestrator.

- [ ] **Step 4: Lint**

Run: `cd sidequest-server && uv run ruff check sidequest/handlers/player_action.py sidequest/agents/aside_resolver.py sidequest/agents/llm_factory.py`
Expected: clean (fix import ordering / unused if flagged).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/handlers/player_action.py sidequest/agents/llm_factory.py
git commit -m "feat(handlers): branch aside before the ADR-036 barrier, return ASIDE_ANSWER (ADR-107)"
```

---

### Task 5: Server — the mandatory MP wiring test

**Files:**
- Test: `sidequest-server/tests/handlers/test_aside_channel_wiring.py` (create)

This is the centerpiece. It drives the real handler path and asserts the out-of-band guarantees.

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/handlers/test_aside_channel_wiring.py`. Mirror the construction used by the nearest existing handler test in `tests/handlers/` (reuse its room/snapshot fixtures — do not hand-roll a session). Assert all seven guarantees:

```python
import pytest

from sidequest.protocol.enums import MessageType

# Reuse the existing handler-test harness. Replace `make_mp_room` /
# `submit` with the real helpers from the sibling handler test module
# (grep tests/handlers for the 3-player MP fixture already in use).
from tests.handlers._harness import make_mp_room, submit, fake_aside_llm


@pytest.mark.asyncio
async def test_aside_is_out_of_band_in_mp():
    room = make_mp_room(players=["Carl", "Donut", "Katia"], llm_aside=fake_aside_llm(
        '{"answer":"Knee-deep — wade, no carry.","outcome":"answered",'
        '"grounded_on":["character.size","region.water_depth"]}'
    ))

    nlog_before = room.narrative_log_count()
    scrap_before = room.scrapbook_count()
    turn_before = room.turn_round()

    # Carl submits a real action; Katia fires an aside mid-round; Donut pending.
    await submit(room, "Carl", "I open the door", aside=False)
    aside_out = await submit(room, "Katia", "can I wade or must I be carried?", aside=True)

    # (1)(2)(3)(4) no turn record / world advance
    assert room.narrative_log_count() == nlog_before
    assert room.scrapbook_count() == scrap_before
    assert room.turn_round() == turn_before
    assert room.world_patch_count() == 0

    # (5) barrier still waiting on Katia's real action + Donut unaffected
    assert not room.barrier_fired()
    assert room.pending_player_ids() == {"Katia", "Donut"}  # Carl submitted

    # (6) ASIDE_ANSWER broadcast to ALL seats
    assert aside_out and aside_out[0].type == MessageType.ASIDE_ANSWER
    assert room.last_broadcast_recipients() == {"Carl", "Donut", "Katia"}

    # (7) the aside.resolve span fired
    assert room.spans_named("aside.resolve")

    # Katia now submits her real action -> barrier fires normally
    await submit(room, "Katia", "I wade in", aside=False)
    await submit(room, "Donut", "I follow", aside=False)
    assert room.barrier_fired()
    assert room.turn_round() == turn_before + 1
```

> **Harness note:** if `tests/handlers/_harness.py` does not exist, factor the 3-player MP setup out of the existing sibling handler test into that module in this step (small refactor, no behavior change) so this test and the sibling share it. `fake_aside_llm` returns an object with `async def complete(*, system, user) -> str` yielding the fixed JSON.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_aside_channel_wiring.py -v`
Expected: FAIL initially on the assertion that first exposes a gap (e.g. broadcast recipients, or span fired) — confirm it fails for the *right* reason, not an import error. Fix wiring in `player_action.py` (Task 4) until green.

- [ ] **Step 3: Run to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_aside_channel_wiring.py -v`
Expected: PASS (1 passed)

- [ ] **Step 4: Regression envelope**

Run: `cd sidequest-server && uv run pytest tests/handlers tests/protocol tests/telemetry/test_routing_completeness.py tests/agents/test_aside_resolver.py -q`
Expected: all pass (no existing handler/barrier test regressed by the new branch).

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add tests/handlers/test_aside_channel_wiring.py tests/handlers/_harness.py
git commit -m "test(handlers): mandatory MP wiring test — aside is out-of-band (ADR-107)"
```

---

### Task 6: UI — `ASIDE_ANSWER` protocol type + route

**Files:**
- Modify: `sidequest-ui/src/types/protocol.ts` (`MessageType` map + payload type)
- Modify: `sidequest-ui/src/App.tsx` (route `ASIDE_ANSWER` into the narrative stream alongside `NARRATION`, ~line 529)
- Test: `sidequest-ui/src/__tests__/asideChannel.test.ts` (create)

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/__tests__/asideChannel.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { MessageType } from "../types/protocol";
import { messageToSegments } from "../lib/narrativeSegments";

describe("ASIDE_ANSWER", () => {
  it("is a known message type", () => {
    expect(MessageType.ASIDE_ANSWER).toBe("ASIDE_ANSWER");
  });

  it("renders as a gm-aside segment, not narration text", () => {
    const segs = messageToSegments({
      type: MessageType.ASIDE_ANSWER,
      payload: {
        asker_id: "Hiken",
        question: "can I wade?",
        answer: "Knee-deep — wade, no carry.",
        grounded_on: ["character.size"],
        round: 7,
      },
    } as never);
    expect(segs.some((s) => s.kind === "gm-aside")).toBe(true);
    expect(segs.every((s) => s.kind !== "text")).toBe(true);
  });
});
```

> Use the real exported segment-builder name (grep `narrativeSegments.ts` for the exported function — it may be `messageToSegments` or similar). Adjust the import to match.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/__tests__/asideChannel.test.ts`
Expected: FAIL — `ASIDE_ANSWER` undefined / no `gm-aside` segment.

- [ ] **Step 3: Add the message type + payload type**

In `src/types/protocol.ts`, in the `MessageType` const object after `ACTION_REVEAL`, add:

```ts
  ASIDE_ANSWER: "ASIDE_ANSWER",
```

Add the payload interface near the other payloads:

```ts
export interface AsideAnswerPayload {
  asker_id: string;
  question: string;
  answer: string;
  grounded_on: string[];
  round: number;
}
```

- [ ] **Step 4: Route it in App.tsx**

In `src/App.tsx`, find the branch that funnels `NARRATION` / `NARRATION_END` into the narrative stream (~line 529). Add `ASIDE_ANSWER` to the same stream-append path so it flows through `messageToSegments` and into the narrative scroll (it must NOT go through `setMapData`, turn-status, or scrapbook paths). Mirror exactly how `NARRATION` is appended:

```ts
    if (
      msg.type === MessageType.NARRATION ||
      msg.type === MessageType.NARRATION_END ||
      msg.type === MessageType.ASIDE_ANSWER
    ) {
```

> Adjust to the real condition shape at that line — only add `ASIDE_ANSWER` to the existing narrative-append predicate; change nothing else.

- [ ] **Step 5: Run test to verify it passes (after Task 7 adds the segment)**

`gm-aside` segment is produced in Task 7. After Task 7, run: `cd sidequest-ui && npx vitest run src/__tests__/asideChannel.test.ts`
Expected: PASS. (If running Task 6 standalone, the first `it` passes; the second goes green once Task 7 lands — note this ordering in the commit.)

- [ ] **Step 6: Commit**

```bash
cd sidequest-ui
git add src/types/protocol.ts src/App.tsx src/__tests__/asideChannel.test.ts
git commit -m "feat(ui): ASIDE_ANSWER message type + narrative-stream routing (ADR-107)"
```

---

### Task 7: UI — `gm-aside` segment + InputBar copy

**Files:**
- Modify: `sidequest-ui/src/lib/narrativeSegments.ts` (segment union + `ASIDE_ANSWER` case)
- Modify: `sidequest-ui/src/components/InputBar.tsx` (placeholder copy ~line 186)
- Modify: the segment renderer/CSS that styles `player-aside` (find it: grep `player-aside`)
- Test: `sidequest-ui/src/__tests__/asideChannel.test.ts` (from Task 6, now goes green)

- [ ] **Step 1: Extend the segment union + add the case**

In `src/lib/narrativeSegments.ts`, add `"gm-aside"` to the `kind` union (the line listing `"player-aside"` etc.). Add a switch case mirroring the `NARRATION` case but emitting `gm-aside`:

```ts
      case MessageType.ASIDE_ANSWER: {
        const p = msg.payload as {
          asker_id?: string;
          question?: string;
          answer?: string;
        };
        if (p.answer) {
          segments.push({
            kind: "gm-aside",
            text: `${p.asker_id ?? "?"} asked: ${p.question ?? ""}\nGM: ${p.answer}`,
          });
        }
        break;
      }
```

- [ ] **Step 2: Run the Task 6 test — now green**

Run: `cd sidequest-ui && npx vitest run src/__tests__/asideChannel.test.ts`
Expected: PASS (2 passed).

- [ ] **Step 3: Style `gm-aside` like `player-aside`**

Run: `cd sidequest-ui && grep -rn "player-aside" src/ | grep -v __tests__`
Wherever `player-aside` gets its OOC visual register (segment renderer component and/or CSS), add `gm-aside` to the same rule (indented, lighter, marginal table-talk). Do not create a new visual language — the GM aside is the answering half of the same OOC pair.

- [ ] **Step 4: InputBar placeholder copy**

In `src/components/InputBar.tsx` (~line 186), change the aside-mode placeholder from `"What do you whisper?"` to `"Ask the GM — no turn spent"`. No logic change.

- [ ] **Step 5: Lint + typecheck + targeted tests**

Run:
```bash
cd sidequest-ui
npx tsc --noEmit
npx eslint src/lib/narrativeSegments.ts src/components/InputBar.tsx src/App.tsx src/types/protocol.ts
npx vitest run src/__tests__/asideChannel.test.ts
```
Expected: tsc clean, eslint clean (ignore unrelated pre-existing warnings), vitest 2 passed.

- [ ] **Step 6: Commit**

```bash
cd sidequest-ui
git add src/lib/narrativeSegments.ts src/components/InputBar.tsx
# include the segment-renderer/CSS file you touched in Step 3
git commit -m "feat(ui): gm-aside segment + 'no turn spent' aside placeholder (ADR-107)"
```

---

### Task 8: Docs — correct the `api-contract.md` lie + guard it

**Files:**
- Modify: `oq-1/docs/api-contract.md` (the aside lines — grep `aside`)
- Test: `oq-1/sidequest-server/tests/protocol/test_api_contract_aside.py` (create — a doc-contract guard living with the server suite)

- [ ] **Step 1: Write the failing guard test**

Create `sidequest-server/tests/protocol/test_api_contract_aside.py`:

```python
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "api-contract.md"


def test_api_contract_does_not_lie_about_asides():
    text = CONTRACT.read_text(encoding="utf-8")
    assert CONTRACT.exists()
    # The old contradictory claims must be gone.
    assert "(not narrated)" not in text
    assert "broadcast identically to in-character text" not in text
    # The true contract must be present.
    assert "ASIDE_ANSWER" in text
    assert "no turn" in text.lower() or "non-turn" in text.lower()
```

> Confirm the relative depth: from `sidequest-server/tests/protocol/` to repo root is `parents[3]`. Adjust the index if the test errors on path (print `CONTRACT` once).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_api_contract_aside.py -v`
Expected: FAIL — `(not narrated)` still present / `ASIDE_ANSWER` absent.

- [ ] **Step 3: Rewrite the aside section of `docs/api-contract.md`**

Replace the contradictory aside lines with the true contract:

```markdown
- `aside: true` on `PLAYER_ACTION` = an out-of-band OOC question to the GM
  (ADR-107). It does **not** consume a turn, advance the world, or count
  toward the multiplayer submit-and-wait barrier. The server answers with an
  `ASIDE_ANSWER` message broadcast to the whole room (table-visible). The
  asker still owes their normal action for the turn to resolve.
- `ASIDE_ANSWER` payload: `{ asker_id, question, answer, grounded_on[],
  round }`. `round` is for client ordering only — it is never a turn record.
```

Remove the old `(not narrated)` and `broadcast identically to in-character text` lines entirely.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_api_contract_aside.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (two repos)**

```bash
cd /Users/slabgorb/Projects/oq-1
git add docs/api-contract.md
git commit -m "docs(api-contract): correct the aside contract — OOC, no turn, ASIDE_ANSWER (ADR-107)"
cd sidequest-server
git add tests/protocol/test_api_contract_aside.py
git commit -m "test(protocol): guard the api-contract aside lie from regressing (ADR-107)"
```

---

### Task 9: ADR-107

**Files:**
- Create: `oq-1/docs/adr/107-out-of-band-aside-channel.md`
- Modify: `oq-1/docs/adr/README.md` (regenerate index) + `oq-1/CLAUDE.md` ADR list if the generator touches it

- [ ] **Step 1: Author the ADR**

Create `docs/adr/107-out-of-band-aside-channel.md` following the frontmatter schema of a recent ADR (copy the frontmatter shape from `docs/adr/106-runtime-procedural-jaquaysed-megadungeon.md` — `status: accepted`, title, date, deciders, and the body sections **Context / Decision / Consequences / Alternatives**). Content, drawn from the spec:
- **Context:** half-wired aside flag; ADR-082 port-drift dropped Rust `handle_aside` (ADR-063); `api-contract.md` lie; playtest F6.
- **Decision:** Approach A — reuse the flag, branch before the ADR-036 barrier, read-only resolver, OOC GM answer, no turn/world advance, table-visible `ASIDE_ANSWER`, routed `aside.resolve` span, ADR-101 Haiku routing.
- **Consequences:** new out-of-band input class amends the ADR-036 barrier contract; doc lie corrected; GM-panel-auditable; the `aside` flag's historical "styled but narrated" meaning is retired.
- **Alternatives:** new message type (B), client REST side-channel (C) — rejected with reasons from the spec.
- Cross-reference: 036, 063, 082, 101, and SOUL (Tabletop First, Zork Problem, the lie-detector mandate).

- [ ] **Step 2: Regenerate ADR indexes**

Run: `cd /Users/slabgorb/Projects/oq-1 && python scripts/regenerate_adr_indexes.py`
Expected: `docs/adr/README.md` (and the CLAUDE.md generated block) updated to include ADR-107.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add docs/adr/107-out-of-band-aside-channel.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): ADR-107 — Out-of-Band Aside Channel"
```

---

### Task 10: Cross-repo gate + PRs

**Files:** none (verification + PRs)

- [ ] **Step 1: Server gate**

Run: `cd /Users/slabgorb/Projects/oq-1 && just server-check`
Expected: ruff clean + full pytest green (includes the new aside suites).

- [ ] **Step 2: UI gate**

Run: `cd /Users/slabgorb/Projects/oq-1 && just client-lint && just client-test`
Expected: eslint clean (pre-existing unrelated warnings ok), vitest green.

- [ ] **Step 3: Open the three PRs**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && gh pr create --base develop --fill
cd /Users/slabgorb/Projects/oq-1/sidequest-ui && gh pr create --base develop --fill
cd /Users/slabgorb/Projects/oq-1 && gh pr create --base main --fill   # spec+plan+ADR+api-contract
```

- [ ] **Step 4: Manual playtest sanity (the F6 reproduction)**

Restart services (`just down && just up`), start a Beneath Sünden MP session, toggle aside ("(…)"), ask *"can I wade or must I be carried?"*. Verify: GM answers OOC inline, no turn consumed, the barrier still waits for the asker's real action, all seats see the Q&A, and the GM panel shows an `aside.resolve` span with non-empty `grounded_on`. This is F6 closed.

---

## Self-Review

**1. Spec coverage:**
- §3 architecture/branch-before-barrier → Task 4 + Task 5 (wiring proof). ✓
- §4 resolver answer policy/grounding → Task 3 (units incl. refusal + ungrounded). ✓
- §5 protocol `ASIDE_ANSWER` not-a-turn-record / UI gm-aside / InputBar copy / doc-lie → Tasks 1, 6, 7, 8. ✓
- §6 OTEL `aside.resolve` routed span + error handling (resolver_error) → Task 2 + Task 3 + Task 4. ✓
- §7 mandatory wiring test (all 7 assertions) → Task 5. ✓
- §8 deliverables incl. ADR-107 → Task 9. ✓
- §9 out-of-scope respected (no private asides, no aside-driven world change, no TTS). ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases/similar to Task N". Integration points that legitimately depend on real local symbol names (snapshot accessors, broadcast seam, segment-builder export, ADR frontmatter) are flagged with an explicit grep-to-confirm instruction and the exact intent — not left vague. Acceptable: these are real-codebase seams the engineer must bind to existing code, and the plan names the existing code to mirror.

**3. Type consistency:** `AsideReadView` / `AsideResolution` / `AsideLLM` / `AsideResolver.resolve` consistent across Tasks 3, 4, 5. `AsideAnswerPayload` field set (`asker_id, question, answer, grounded_on, round`) identical in Tasks 1, 4, 6, 7, 8. `MessageType.ASIDE_ANSWER` literal `"ASIDE_ANSWER"` consistent server/UI. `SPAN_ASIDE_RESOLVE = "aside.resolve"` consistent Tasks 2/4/5/10. Outcome enum `{answered, refused_hidden_state, refused_would_advance, ungrounded_declined, resolver_error}` consistent spec §6 ↔ Task 3.

No gaps found.
