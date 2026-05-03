# Live Teammate Typing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all party members' in-progress and post-submit action text visible to each other in real time during cinematic-mode rounds, while preserving the sealed-letter barrier and CAS-guarded dispatcher.

**Architecture:** Wire up the stubbed `ACTION_REVEAL` message. Client-side 250ms debounce broadcasts in-progress text; server fans out via `SessionRoom.broadcast(exclude_socket_id=sender)`; server emits `cleared` on barrier-fire and on disconnect to flush peer state. UI adds a new `PeerRevealList` component above the existing `MultiplayerTurnBanner`.

**Tech Stack:** Python 3.13 / FastAPI / pydantic v2 (server); React 19 / TypeScript / Vitest (client); pytest (server tests); existing `_watcher_publish` for OTEL.

**Spec:** `docs/superpowers/specs/2026-05-03-live-teammate-typing-design.md`

**Refinements vs spec:**
- Drop the "cleared on cinematic-mode timeout" trigger — no such timeout exists in the codebase yet. Two trigger sites only: dispatch + disconnect. Spec section "Edge Case C" is parked until cinematic timeout itself is implemented.
- Field name in payload is `action` (not `text`), matching existing `ActionRevealEntry` / `PlayerActionPayload` convention.
- UI introduces a new `PeerRevealList` component as a sibling of `MultiplayerTurnBanner` rather than modifying the banner's existing state machine.

---

## File Structure

**Server — new files:**
- `sidequest-server/sidequest/handlers/action_reveal.py` — handler
- `sidequest-server/tests/handlers/test_action_reveal.py` — unit tests
- `sidequest-server/tests/handlers/test_player_action_clears_reveals.py` — dispatch trigger
- `sidequest-server/tests/server/test_session_room_disconnect_clears_reveals.py` — disconnect trigger
- `sidequest-server/tests/server/test_action_reveal_wired.py` — end-to-end wiring
- `sidequest-server/tests/telemetry/test_action_reveal_otel.py` — OTEL coverage

**Server — modified files:**
- `sidequest-server/sidequest/protocol/messages.py` — add `ActionRevealStatus`, `ActionRevealPayload`, `ActionRevealMessage`
- `sidequest-server/sidequest/server/websocket_session_handler.py` — register handler at line ~648
- `sidequest-server/sidequest/handlers/player_action.py` — emit `cleared` at the barrier-fired branch (~line 267)
- `sidequest-server/sidequest/server/session_room.py` — emit `cleared` from `disconnect()` (~line 312)

**Client — new files:**
- `sidequest-ui/src/hooks/usePeerReveals.ts` — peer reveal map hook
- `sidequest-ui/src/hooks/__tests__/usePeerReveals.test.tsx`
- `sidequest-ui/src/components/PeerRevealList.tsx` — sibling banner that renders peer composing/submitted rows
- `sidequest-ui/src/components/__tests__/PeerRevealList.test.tsx`
- `sidequest-ui/src/__tests__/action-reveal-wiring.test.tsx` — end-to-end wiring

**Client — modified files:**
- `sidequest-ui/src/types/payloads.ts` — extend `ActionRevealEntry`
- `sidequest-ui/src/types/protocol.ts` — already has `ACTION_REVEAL` enum value (verify only)
- `sidequest-ui/src/components/InputBar.tsx` — debounce composing + submitted-before-onSend + seq
- `sidequest-ui/src/screens/Game.tsx` (or whichever component currently mounts `MultiplayerTurnBanner` and `InputBar`) — wire `PeerRevealList` and `usePeerReveals`

**Docs — modified files:**
- `docs/adr/036-multiplayer-turn-coordination.md` — Action Visibility Model section

---

## Task 1: Server protocol types

Add `ActionRevealStatus`, `ActionRevealPayload`, and `ActionRevealMessage` to `sidequest/protocol/messages.py`. The existing `ACTION_REVEAL` value in `enums.py:48` does not need changes.

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Test: `sidequest-server/tests/protocol/test_action_reveal_payload.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/protocol/test_action_reveal_payload.py`:

```python
"""Tests for ACTION_REVEAL protocol types."""

import pytest
from pydantic import ValidationError

from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)


def test_composing_payload_round_trips():
    payload = ActionRevealPayload(
        player_id="p1",
        character_name="Alex",
        status=ActionRevealStatus.COMPOSING,
        action="I creep along the rafters",
        aside=False,
        seq=3,
        round=7,
    )
    msg = ActionRevealMessage(payload=payload)
    dumped = msg.model_dump(mode="json")
    assert dumped["type"] == "ACTION_REVEAL"
    assert dumped["payload"]["status"] == "composing"
    assert dumped["payload"]["seq"] == 3
    rehydrated = ActionRevealMessage.model_validate(dumped)
    assert rehydrated.payload.action == "I creep along the rafters"


def test_status_must_be_known_value():
    with pytest.raises(ValidationError):
        ActionRevealPayload(
            player_id="p1",
            character_name="Alex",
            status="banana",  # type: ignore[arg-type]
            action="hi",
            aside=False,
            seq=0,
            round=0,
        )


def test_action_can_be_empty_when_cleared():
    payload = ActionRevealPayload(
        player_id="p1",
        character_name="Alex",
        status=ActionRevealStatus.CLEARED,
        action="",
        aside=False,
        seq=99,
        round=7,
    )
    assert payload.action == ""


def test_seq_must_be_non_negative():
    with pytest.raises(ValidationError):
        ActionRevealPayload(
            player_id="p1",
            character_name="Alex",
            status=ActionRevealStatus.COMPOSING,
            action="x",
            aside=False,
            seq=-1,
            round=0,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_action_reveal_payload.py -v`
Expected: FAIL — `ImportError: cannot import name 'ActionRevealMessage'`

- [ ] **Step 3: Write minimal implementation**

In `sidequest-server/sidequest/protocol/messages.py`, near the existing `TurnStatusPayload` / `TurnStatusMessage` (around line 309):

```python
from enum import StrEnum

class ActionRevealStatus(StrEnum):
    """Lifecycle state of a player's in-progress action visible to peers."""
    COMPOSING = "composing"
    SUBMITTED = "submitted"
    CLEARED = "cleared"


class ActionRevealPayload(ProtocolBase):
    """Per-player live action visibility update.

    See ADR-036 (Action Visibility Model). Broadcast to all party members
    except the sender so peers can coordinate during cinematic-mode rounds.
    Sealed-letter barrier and CAS dispatcher are unaffected.
    """
    player_id: str
    """Player whose action this reveal describes."""
    character_name: str
    """Display name of the player's character."""
    status: ActionRevealStatus
    """composing | submitted | cleared. Clients send composing/submitted; server emits cleared."""
    action: str = ""
    """Current action text. Empty string when status=cleared."""
    aside: bool = False
    """OOC aside flag, mirrors PlayerActionPayload.aside."""
    seq: int = Field(ge=0)
    """Monotonic per (player_id, round). Receivers drop non-monotonic seq within a round."""
    round: int = Field(ge=0)
    """Round counter (ADR-051). Server stamps; clients' values are overwritten."""
```

Then near the existing `TurnStatusMessage` (around line 679) add:

```python
class ActionRevealMessage(ProtocolBase):
    """GameMessage::ActionReveal wire representation."""
    type: Literal[MessageType.ACTION_REVEAL] = MessageType.ACTION_REVEAL
    payload: ActionRevealPayload
    player_id: str = ""
```

If `Field` is not yet imported in this file, add to existing pydantic import:

```python
from pydantic import Field  # add to existing pydantic import line
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/protocol/test_action_reveal_payload.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/protocol/messages.py tests/protocol/test_action_reveal_payload.py
git commit -m "feat(protocol): add ActionReveal payload + message types"
```

---

## Task 2: Action reveal handler — happy path

Create the handler that accepts `composing` and `submitted` from clients and fans them out via `SessionRoom.broadcast(exclude_socket_id=sender)`.

**Files:**
- Create: `sidequest-server/sidequest/handlers/action_reveal.py`
- Test: `sidequest-server/tests/handlers/test_action_reveal.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/handlers/test_action_reveal.py`:

```python
"""Tests for ActionRevealHandler."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from sidequest.handlers.action_reveal import HANDLER, ActionRevealHandler
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)


def _make_session(player_id: str = "p1", socket_id: str = "s1", round: int = 7):
    session = MagicMock()
    session._room = MagicMock()
    session._room.broadcast = MagicMock(return_value=[])
    session._room.slug = "test-slug"
    session._socket_id = socket_id
    session._player_id = player_id
    snapshot = MagicMock()
    snapshot.turn_manager.round = round
    session._room.snapshot.return_value = snapshot
    return session


def _make_msg(
    *,
    status: ActionRevealStatus,
    action: str = "I sneak around the back",
    seq: int = 0,
    round: int = 7,
    player_id: str = "p1",
    character_name: str = "Alex",
    aside: bool = False,
):
    payload = ActionRevealPayload(
        player_id=player_id,
        character_name=character_name,
        status=status,
        action=action,
        aside=aside,
        seq=seq,
        round=round,
    )
    return ActionRevealMessage(payload=payload, player_id=player_id)


@pytest.mark.asyncio
async def test_composing_is_broadcast_excluding_sender():
    handler = ActionRevealHandler()
    session = _make_session()
    msg = _make_msg(status=ActionRevealStatus.COMPOSING, action="I creep", seq=1)

    result = await handler.handle(session, msg)

    assert result == []
    session._room.broadcast.assert_called_once()
    sent_msg, kwargs = (
        session._room.broadcast.call_args.args[0],
        session._room.broadcast.call_args.kwargs,
    )
    assert kwargs["exclude_socket_id"] == "s1"
    assert sent_msg.payload.status == ActionRevealStatus.COMPOSING
    assert sent_msg.payload.action == "I creep"


@pytest.mark.asyncio
async def test_submitted_is_broadcast():
    handler = ActionRevealHandler()
    session = _make_session()
    msg = _make_msg(status=ActionRevealStatus.SUBMITTED, action="I draw my sword", seq=5)

    await handler.handle(session, msg)

    session._room.broadcast.assert_called_once()
    sent_msg = session._room.broadcast.call_args.args[0]
    assert sent_msg.payload.status == ActionRevealStatus.SUBMITTED


@pytest.mark.asyncio
async def test_module_exports_handler_singleton():
    assert isinstance(HANDLER, ActionRevealHandler)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_action_reveal.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.handlers.action_reveal'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest-server/sidequest/handlers/action_reveal.py`:

```python
"""ActionRevealHandler — broadcasts in-progress action visibility (ADR-036)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)

if TYPE_CHECKING:
    from sidequest.protocol import GameMessage
    from sidequest.server.websocket_session_handler import WebSocketSessionHandler

logger = logging.getLogger(__name__)


class ActionRevealHandler:
    """Handle ACTION_REVEAL: broadcast composing/submitted to peers."""

    async def handle(
        self,
        session: "WebSocketSessionHandler",
        msg: "GameMessage",
    ) -> list[object]:
        assert isinstance(msg, ActionRevealMessage)
        payload: ActionRevealPayload = msg.payload

        # Server stamps round + sender player_id authoritatively.
        snapshot = session._room.snapshot()
        stamped = payload.model_copy(
            update={
                "round": snapshot.turn_manager.round,
                "player_id": session._player_id,
            }
        )
        outbound = ActionRevealMessage(payload=stamped, player_id=session._player_id)
        session._room.broadcast(outbound, exclude_socket_id=session._socket_id)
        return []


HANDLER = ActionRevealHandler()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_action_reveal.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/handlers/action_reveal.py tests/handlers/test_action_reveal.py
git commit -m "feat(handlers): action reveal handler — happy-path broadcast"
```

---

## Task 3: Handler defensive layer

Drop client-sent `cleared` (server-only); drop stale or non-monotonic seq within a round; rate-limit `composing` to a 100ms-per-(player_id) floor.

**Files:**
- Modify: `sidequest-server/sidequest/handlers/action_reveal.py`
- Test: `sidequest-server/tests/handlers/test_action_reveal.py` (extend)

- [ ] **Step 1: Write the failing tests**

Append to `sidequest-server/tests/handlers/test_action_reveal.py`:

```python
import time


@pytest.mark.asyncio
async def test_client_cleared_is_silently_dropped():
    handler = ActionRevealHandler()
    session = _make_session()
    msg = _make_msg(status=ActionRevealStatus.CLEARED, action="", seq=0)

    result = await handler.handle(session, msg)

    assert result == []
    session._room.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_stale_seq_dropped_in_same_round():
    handler = ActionRevealHandler()
    session = _make_session(round=7)
    first = _make_msg(status=ActionRevealStatus.COMPOSING, action="abc", seq=5)
    stale = _make_msg(status=ActionRevealStatus.COMPOSING, action="ab", seq=3)

    await handler.handle(session, first)
    await handler.handle(session, stale)

    assert session._room.broadcast.call_count == 1


@pytest.mark.asyncio
async def test_seq_resets_on_new_round():
    handler = ActionRevealHandler()
    session = _make_session(round=7)
    first = _make_msg(status=ActionRevealStatus.COMPOSING, action="abc", seq=5)
    await handler.handle(session, first)

    # New round
    snapshot = session._room.snapshot.return_value
    snapshot.turn_manager.round = 8
    new_round = _make_msg(status=ActionRevealStatus.COMPOSING, action="x", seq=0, round=8)
    await handler.handle(session, new_round)

    assert session._room.broadcast.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_drops_too_fast_composing(monkeypatch):
    handler = ActionRevealHandler()
    session = _make_session()
    fake_now = [1000.0]
    monkeypatch.setattr(
        "sidequest.handlers.action_reveal.time.monotonic",
        lambda: fake_now[0],
    )

    await handler.handle(session, _make_msg(status=ActionRevealStatus.COMPOSING, seq=0))
    fake_now[0] = 1000.05  # 50ms later — under floor
    await handler.handle(session, _make_msg(status=ActionRevealStatus.COMPOSING, seq=1))
    fake_now[0] = 1000.20  # 200ms total — past floor
    await handler.handle(session, _make_msg(status=ActionRevealStatus.COMPOSING, seq=2))

    assert session._room.broadcast.call_count == 2  # first + third


@pytest.mark.asyncio
async def test_submitted_bypasses_rate_limit(monkeypatch):
    """Submitted is a discrete event — never throttled."""
    handler = ActionRevealHandler()
    session = _make_session()
    fake_now = [1000.0]
    monkeypatch.setattr(
        "sidequest.handlers.action_reveal.time.monotonic",
        lambda: fake_now[0],
    )

    await handler.handle(session, _make_msg(status=ActionRevealStatus.COMPOSING, seq=0))
    fake_now[0] = 1000.01  # 10ms later
    await handler.handle(session, _make_msg(status=ActionRevealStatus.SUBMITTED, seq=1))

    assert session._room.broadcast.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_action_reveal.py -v`
Expected: FAIL — 5 new tests fail (handler accepts/broadcasts everything currently)

- [ ] **Step 3: Write minimal implementation**

Replace the body of `sidequest-server/sidequest/handlers/action_reveal.py`:

```python
"""ActionRevealHandler — broadcasts in-progress action visibility (ADR-036)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)

if TYPE_CHECKING:
    from sidequest.protocol import GameMessage
    from sidequest.server.websocket_session_handler import WebSocketSessionHandler

logger = logging.getLogger(__name__)

# Server-side rate-limit floor for composing updates per (player_id).
# Clients should debounce at 250ms; this is a safety net for buggy or
# hand-fired clients. Submitted events bypass this throttle.
_COMPOSING_FLOOR_S = 0.100


class ActionRevealHandler:
    """Handle ACTION_REVEAL: broadcast composing/submitted to peers."""

    def __init__(self) -> None:
        # Per-(socket_id) state. Cleaned up on socket disconnect via
        # session_room.disconnect emitting a `cleared` (separate path);
        # entries naturally evict when player_id changes for a socket.
        self._last_seq: dict[str, tuple[int, int]] = {}  # socket_id -> (round, last_seq)
        self._last_composing_t: dict[str, float] = {}    # socket_id -> monotonic seconds

    async def handle(
        self,
        session: "WebSocketSessionHandler",
        msg: "GameMessage",
    ) -> list[object]:
        assert isinstance(msg, ActionRevealMessage)
        payload: ActionRevealPayload = msg.payload

        # Server emits cleared; clients sending it are silently dropped.
        if payload.status == ActionRevealStatus.CLEARED:
            return []

        snapshot = session._room.snapshot()
        round_no = snapshot.turn_manager.round
        socket_id = session._socket_id

        # seq monotonicity per (socket_id, round).
        prev = self._last_seq.get(socket_id)
        if prev is not None and prev[0] == round_no and payload.seq <= prev[1]:
            return []

        # Rate-limit composing only.
        if payload.status == ActionRevealStatus.COMPOSING:
            now = time.monotonic()
            last_t = self._last_composing_t.get(socket_id)
            if last_t is not None and (now - last_t) < _COMPOSING_FLOOR_S:
                return []
            self._last_composing_t[socket_id] = now

        # Server stamps round + sender player_id authoritatively.
        stamped = payload.model_copy(
            update={
                "round": round_no,
                "player_id": session._player_id,
            }
        )
        outbound = ActionRevealMessage(payload=stamped, player_id=session._player_id)
        session._room.broadcast(outbound, exclude_socket_id=socket_id)
        self._last_seq[socket_id] = (round_no, payload.seq)
        return []


HANDLER = ActionRevealHandler()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_action_reveal.py -v`
Expected: PASS — 8 passed

- [ ] **Step 5: Commit**

```bash
cd sidequest-server
git add sidequest/handlers/action_reveal.py tests/handlers/test_action_reveal.py
git commit -m "feat(handlers): action reveal — drop client cleared, stale seq, rate-limit"
```

---

## Task 4: Register handler in WS dispatch

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (around line 638)

- [ ] **Step 1: Inspect the registration site**

Read `sidequest-server/sidequest/server/websocket_session_handler.py` lines 638–657. Confirm the `_MESSAGE_HANDLERS` registry exists with the imports + dict pattern from the recon.

- [ ] **Step 2: Write the failing test (wiring)**

Create `sidequest-server/tests/server/test_action_reveal_dispatch_registration.py`:

```python
"""Verify ActionRevealHandler is registered in the WS dispatch registry."""

from sidequest.handlers.action_reveal import ActionRevealHandler
from sidequest.server.websocket_session_handler import WebSocketSessionHandler


def test_action_reveal_handler_is_registered():
    # Reset class-level cache if test isolation needs it.
    WebSocketSessionHandler._MESSAGE_HANDLERS = None  # type: ignore[attr-defined]
    handler = WebSocketSessionHandler._handler_for("ACTION_REVEAL")  # type: ignore[attr-defined]
    assert isinstance(handler, ActionRevealHandler)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_action_reveal_dispatch_registration.py -v`
Expected: FAIL — registry returns None

- [ ] **Step 4: Modify dispatch registration**

In `sidequest-server/sidequest/server/websocket_session_handler.py`, edit the existing block around line 638:

```python
if registry is None:
    from sidequest.handlers.action_reveal import HANDLER as ACTION_REVEAL_HANDLER  # ADD
    from sidequest.handlers.character_creation import HANDLER as CHARACTER_CREATION_HANDLER
    from sidequest.handlers.dice_throw import HANDLER as DICE_THROW_HANDLER
    from sidequest.handlers.orbital_intent import HANDLER as ORBITAL_INTENT_HANDLER
    from sidequest.handlers.player_action import HANDLER as PLAYER_ACTION_HANDLER
    from sidequest.handlers.player_seat import HANDLER as PLAYER_SEAT_HANDLER
    from sidequest.handlers.session_event import HANDLER as SESSION_EVENT_HANDLER
    from sidequest.handlers.yield_action import HANDLER as YIELD_HANDLER

    registry = {
        "SESSION_EVENT": SESSION_EVENT_HANDLER,
        "PLAYER_ACTION": PLAYER_ACTION_HANDLER,
        "CHARACTER_CREATION": CHARACTER_CREATION_HANDLER,
        "PLAYER_SEAT": PLAYER_SEAT_HANDLER,
        "DICE_THROW": DICE_THROW_HANDLER,
        "YIELD": YIELD_HANDLER,
        "ORBITAL_INTENT": ORBITAL_INTENT_HANDLER,
        "ACTION_REVEAL": ACTION_REVEAL_HANDLER,  # ADD
    }
```

If `_handler_for` is the actual lookup method name, search for it; otherwise use whichever method already returns the handler from the registry (e.g. `registry.get(msg_type)`).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_action_reveal_dispatch_registration.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/server/websocket_session_handler.py tests/server/test_action_reveal_dispatch_registration.py
git commit -m "feat(server): register ActionRevealHandler in WS dispatch"
```

---

## Task 5: Cleared on barrier-fire

In `player_action.py` at the barrier-fired branch, after the CAS guard takes the dispatch lock and before narrator dispatch, broadcast `ACTION_REVEAL cleared` for every party member.

**Files:**
- Modify: `sidequest-server/sidequest/handlers/player_action.py` (~line 267, immediately after CAS guard)
- Test: `sidequest-server/tests/handlers/test_player_action_clears_reveals.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/handlers/test_player_action_clears_reveals.py`:

```python
"""Verify dispatch fires ACTION_REVEAL cleared for every party member."""

from unittest.mock import MagicMock

from sidequest.handlers.player_action import _broadcast_cleared_to_party
from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealStatus,
)


def test_broadcast_cleared_to_party_emits_one_per_member():
    room = MagicMock()
    broadcast_calls = []
    room.broadcast.side_effect = lambda msg, **kw: broadcast_calls.append((msg, kw)) or []
    party_members = [
        {"player_id": "p1", "character_name": "Alex"},
        {"player_id": "p2", "character_name": "Bob"},
        {"player_id": "p3", "character_name": "Carol"},
    ]

    _broadcast_cleared_to_party(room, party_members, round_no=7, reason="dispatch")

    assert room.broadcast.call_count == 3
    statuses = [m.payload.status for m, _ in broadcast_calls]
    player_ids = [m.payload.player_id for m, _ in broadcast_calls]
    rounds = [m.payload.round for m, _ in broadcast_calls]
    assert all(s == ActionRevealStatus.CLEARED for s in statuses)
    assert player_ids == ["p1", "p2", "p3"]
    assert all(r == 7 for r in rounds)
    # exclude_socket_id is None — cleared goes to everyone including the
    # last-submitter, who needs their own row to clear.
    assert all(kw.get("exclude_socket_id") is None for _, kw in broadcast_calls)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_player_action_clears_reveals.py -v`
Expected: FAIL — `ImportError: cannot import name '_broadcast_cleared_to_party'`

- [ ] **Step 3: Write minimal implementation**

In `sidequest-server/sidequest/handlers/player_action.py`, add a module-level helper near the top (after imports, before the class):

```python
def _broadcast_cleared_to_party(
    room,
    party_members,
    *,
    round_no: int,
    reason: str,
) -> None:
    """Emit ACTION_REVEAL cleared for every party member.

    Called at barrier-fire (reason="dispatch") and on disconnect
    (reason="disconnect"). reason flows into OTEL only — the wire
    payload is identical.
    """
    from sidequest.protocol.messages import (
        ActionRevealMessage,
        ActionRevealPayload,
        ActionRevealStatus,
    )

    for member in party_members:
        payload = ActionRevealPayload(
            player_id=member["player_id"],
            character_name=member["character_name"],
            status=ActionRevealStatus.CLEARED,
            action="",
            aside=False,
            seq=0,
            round=round_no,
        )
        msg = ActionRevealMessage(payload=payload)
        room.broadcast(msg, exclude_socket_id=None)
```

Then in the barrier-fired branch (around line 267, immediately after the CAS guard succeeds and BEFORE the `_watcher_publish("mp.round_dispatched", …)` call), add:

```python
# ADR-036 Action Visibility Model: clear all peer reveal rows
# before narrator dispatch. Send to everyone — even the last
# submitter, whose own row needs to clear.
party_members = [
    {"player_id": pid, "character_name": p.character_name}
    for pid, p in pending
]
_broadcast_cleared_to_party(
    session._room,
    party_members,
    round_no=snapshot.turn_manager.round,
    reason="dispatch",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_player_action_clears_reveals.py -v`
Expected: PASS

- [ ] **Step 5: Run the full handler test suite — guard against regression in player_action**

Run: `cd sidequest-server && uv run pytest tests/handlers/ -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/handlers/player_action.py tests/handlers/test_player_action_clears_reveals.py
git commit -m "feat(server): emit ACTION_REVEAL cleared at barrier-fire"
```

---

## Task 6: Cleared on socket disconnect

When `SessionRoom.disconnect()` removes a player, fire `ACTION_REVEAL cleared` for that player so peers' rows clear.

**Files:**
- Modify: `sidequest-server/sidequest/server/session_room.py` (`disconnect()` around line 312)
- Test: `sidequest-server/tests/server/test_session_room_disconnect_clears_reveals.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/server/test_session_room_disconnect_clears_reveals.py`:

```python
"""Verify SessionRoom.disconnect emits ACTION_REVEAL cleared."""

from unittest.mock import MagicMock

from sidequest.protocol.messages import ActionRevealMessage, ActionRevealStatus
from sidequest.server.session_room import SessionRoom


def test_disconnect_emits_cleared_for_departed_player():
    # NOTE: This test mocks just enough of SessionRoom internals to drive
    # the disconnect path. If SessionRoom requires a richer setup, follow
    # the patterns in existing session_room tests.
    room = SessionRoom(slug="test")  # adjust constructor args to match codebase
    socket_id = "s1"
    player_id = "p1"

    # Manually wire the socket↔player mapping.
    room._sockets[socket_id] = player_id
    room._connected[player_id] = socket_id
    # Stub out outbound queues so broadcast has somewhere to land.
    captured = []

    def fake_broadcast(msg, *, exclude_socket_id=None):
        captured.append((msg, exclude_socket_id))
        return []

    room.broadcast = fake_broadcast  # type: ignore[assignment]

    room.disconnect(socket_id=socket_id)

    cleared = [m for m, _ in captured if isinstance(m, ActionRevealMessage)]
    assert len(cleared) == 1
    assert cleared[0].payload.status == ActionRevealStatus.CLEARED
    assert cleared[0].payload.player_id == player_id
```

If `SessionRoom`'s constructor needs more setup, adapt to the pattern in `tests/server/test_session_room.py` (or whichever existing test file constructs `SessionRoom`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room_disconnect_clears_reveals.py -v`
Expected: FAIL — no ActionRevealMessage in captured broadcasts

- [ ] **Step 3: Modify `SessionRoom.disconnect()`**

In `sidequest-server/sidequest/server/session_room.py`, edit `disconnect()` around line 312. After the existing `with self._lock` block that pops the socket and after the existing `_hub.publish_event` calls, BEFORE returning `player_id`:

```python
# ADR-036 Action Visibility Model: clear the departed player's
# reveal row from peers so they don't see a frozen "composing"
# with no sender.
if player_id is not None:
    snapshot = self.snapshot()
    character_name = ""
    seat = self._seated.get(player_id)
    if seat is not None and getattr(seat, "character_name", None):
        character_name = seat.character_name
    _emit_action_reveal_cleared(
        self,
        player_id=player_id,
        character_name=character_name,
        round_no=snapshot.turn_manager.round,
        reason="disconnect",
    )
```

Add a module-level helper near the top of `session_room.py`:

```python
def _emit_action_reveal_cleared(
    room: "SessionRoom",
    *,
    player_id: str,
    character_name: str,
    round_no: int,
    reason: str,
) -> None:
    """Broadcast ACTION_REVEAL cleared for one player. reason is OTEL-only."""
    from sidequest.protocol.messages import (
        ActionRevealMessage,
        ActionRevealPayload,
        ActionRevealStatus,
    )

    payload = ActionRevealPayload(
        player_id=player_id,
        character_name=character_name,
        status=ActionRevealStatus.CLEARED,
        action="",
        aside=False,
        seq=0,
        round=round_no,
    )
    room.broadcast(ActionRevealMessage(payload=payload), exclude_socket_id=None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room_disconnect_clears_reveals.py -v`
Expected: PASS

- [ ] **Step 5: Run the surrounding suite — guard against disconnect regressions**

Run: `cd sidequest-server && uv run pytest tests/server/ -k "session_room or disconnect" -v`
Expected: PASS (all)

- [ ] **Step 6: Commit**

```bash
cd sidequest-server
git add sidequest/server/session_room.py tests/server/test_session_room_disconnect_clears_reveals.py
git commit -m "feat(server): emit ACTION_REVEAL cleared on socket disconnect"
```

---

## Task 7: OTEL watcher events

Emit `action_reveal.composing`, `action_reveal.submitted`, `action_reveal.cleared`, and `action_reveal.dropped_rate_limit`. Per CLAUDE.md observability principle: text content is NEVER in the payload — length only.

**Files:**
- Modify: `sidequest-server/sidequest/handlers/action_reveal.py`
- Modify: `sidequest-server/sidequest/handlers/player_action.py` (cleared at dispatch site)
- Modify: `sidequest-server/sidequest/server/session_room.py` (cleared at disconnect site)
- Test: `sidequest-server/tests/telemetry/test_action_reveal_otel.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/telemetry/test_action_reveal_otel.py`:

```python
"""OTEL coverage for ACTION_REVEAL — the GM panel lie-detector."""

from unittest.mock import MagicMock, patch

import pytest

from sidequest.handlers.action_reveal import ActionRevealHandler
from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)


def _session(socket_id="s1", player_id="p1", round_no=7):
    s = MagicMock()
    s._socket_id = socket_id
    s._player_id = player_id
    s._room.slug = "test"
    snapshot = MagicMock()
    snapshot.turn_manager.round = round_no
    s._room.snapshot.return_value = snapshot
    s._room.broadcast.return_value = []
    return s


def _msg(status, *, action="abc", seq=0, round=7):
    return ActionRevealMessage(
        payload=ActionRevealPayload(
            player_id="p1",
            character_name="Alex",
            status=status,
            action=action,
            aside=False,
            seq=seq,
            round=round,
        ),
        player_id="p1",
    )


@pytest.mark.asyncio
async def test_composing_emits_otel_with_length_only():
    handler = ActionRevealHandler()
    session = _session()
    with patch("sidequest.handlers.action_reveal._watcher_publish") as pub:
        await handler.handle(session, _msg(ActionRevealStatus.COMPOSING, action="hello world"))
    pub.assert_called_with(
        "action_reveal.composing",
        {
            "slug": "test",
            "player_id": "p1",
            "round": 7,
            "seq": 0,
            "text_length": 11,
        },
        component="multiplayer",
    )


@pytest.mark.asyncio
async def test_submitted_emits_otel_with_aside_flag():
    handler = ActionRevealHandler()
    session = _session()
    msg = ActionRevealMessage(
        payload=ActionRevealPayload(
            player_id="p1",
            character_name="Alex",
            status=ActionRevealStatus.SUBMITTED,
            action="hi there",
            aside=True,
            seq=4,
            round=7,
        ),
        player_id="p1",
    )
    with patch("sidequest.handlers.action_reveal._watcher_publish") as pub:
        await handler.handle(session, msg)
    pub.assert_called_with(
        "action_reveal.submitted",
        {
            "slug": "test",
            "player_id": "p1",
            "round": 7,
            "text_length": 8,
            "aside": True,
        },
        component="multiplayer",
    )


@pytest.mark.asyncio
async def test_rate_limit_emits_dropped_counter(monkeypatch):
    handler = ActionRevealHandler()
    session = _session()
    fake_now = [1000.0]
    monkeypatch.setattr(
        "sidequest.handlers.action_reveal.time.monotonic",
        lambda: fake_now[0],
    )
    with patch("sidequest.handlers.action_reveal._watcher_publish") as pub:
        await handler.handle(session, _msg(ActionRevealStatus.COMPOSING, seq=0))
        fake_now[0] = 1000.05
        await handler.handle(session, _msg(ActionRevealStatus.COMPOSING, seq=1))
    names = [c.args[0] for c in pub.call_args_list]
    assert "action_reveal.dropped_rate_limit" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_action_reveal_otel.py -v`
Expected: FAIL — `_watcher_publish` not imported in handler module / not called

- [ ] **Step 3: Add OTEL emission to the handler**

In `sidequest-server/sidequest/handlers/action_reveal.py` add to imports:

```python
from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish
```

In `ActionRevealHandler.handle`, after the rate-limit drop branch and after the seq drop branch, add OTEL calls. Replace the body so the structure is:

```python
async def handle(
    self,
    session: "WebSocketSessionHandler",
    msg: "GameMessage",
) -> list[object]:
    assert isinstance(msg, ActionRevealMessage)
    payload: ActionRevealPayload = msg.payload
    slug = session._room.slug
    sender_pid = session._player_id

    if payload.status == ActionRevealStatus.CLEARED:
        return []

    snapshot = session._room.snapshot()
    round_no = snapshot.turn_manager.round
    socket_id = session._socket_id

    prev = self._last_seq.get(socket_id)
    if prev is not None and prev[0] == round_no and payload.seq <= prev[1]:
        return []

    if payload.status == ActionRevealStatus.COMPOSING:
        now = time.monotonic()
        last_t = self._last_composing_t.get(socket_id)
        if last_t is not None and (now - last_t) < _COMPOSING_FLOOR_S:
            _watcher_publish(
                "action_reveal.dropped_rate_limit",
                {"slug": slug, "player_id": sender_pid, "round": round_no},
                component="multiplayer",
            )
            return []
        self._last_composing_t[socket_id] = now

    stamped = payload.model_copy(
        update={"round": round_no, "player_id": sender_pid}
    )
    outbound = ActionRevealMessage(payload=stamped, player_id=sender_pid)
    session._room.broadcast(outbound, exclude_socket_id=socket_id)
    self._last_seq[socket_id] = (round_no, payload.seq)

    if payload.status == ActionRevealStatus.COMPOSING:
        _watcher_publish(
            "action_reveal.composing",
            {
                "slug": slug,
                "player_id": sender_pid,
                "round": round_no,
                "seq": payload.seq,
                "text_length": len(payload.action),
            },
            component="multiplayer",
        )
    elif payload.status == ActionRevealStatus.SUBMITTED:
        _watcher_publish(
            "action_reveal.submitted",
            {
                "slug": slug,
                "player_id": sender_pid,
                "round": round_no,
                "text_length": len(payload.action),
                "aside": payload.aside,
            },
            component="multiplayer",
        )

    return []
```

- [ ] **Step 4: Add OTEL emission to the cleared trigger sites**

In `sidequest-server/sidequest/handlers/player_action.py`, modify `_broadcast_cleared_to_party` to publish an OTEL event per cleared message:

```python
def _broadcast_cleared_to_party(
    room,
    party_members,
    *,
    round_no: int,
    reason: str,
) -> None:
    from sidequest.protocol.messages import (
        ActionRevealMessage,
        ActionRevealPayload,
        ActionRevealStatus,
    )
    from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish

    for member in party_members:
        payload = ActionRevealPayload(
            player_id=member["player_id"],
            character_name=member["character_name"],
            status=ActionRevealStatus.CLEARED,
            action="",
            aside=False,
            seq=0,
            round=round_no,
        )
        room.broadcast(ActionRevealMessage(payload=payload), exclude_socket_id=None)
        _watcher_publish(
            "action_reveal.cleared",
            {
                "slug": room.slug,
                "player_id": member["player_id"],
                "round": round_no,
                "reason": reason,
            },
            component="multiplayer",
        )
```

In `sidequest-server/sidequest/server/session_room.py`, modify `_emit_action_reveal_cleared` to do the same:

```python
def _emit_action_reveal_cleared(
    room: "SessionRoom",
    *,
    player_id: str,
    character_name: str,
    round_no: int,
    reason: str,
) -> None:
    from sidequest.protocol.messages import (
        ActionRevealMessage,
        ActionRevealPayload,
        ActionRevealStatus,
    )
    from sidequest.telemetry.watcher_hub import publish_event as _watcher_publish

    payload = ActionRevealPayload(
        player_id=player_id,
        character_name=character_name,
        status=ActionRevealStatus.CLEARED,
        action="",
        aside=False,
        seq=0,
        round=round_no,
    )
    room.broadcast(ActionRevealMessage(payload=payload), exclude_socket_id=None)
    _watcher_publish(
        "action_reveal.cleared",
        {
            "slug": room.slug,
            "player_id": player_id,
            "round": round_no,
            "reason": reason,
        },
        component="multiplayer",
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/telemetry/test_action_reveal_otel.py -v`
Expected: PASS — 3 passed

- [ ] **Step 6: Run all action_reveal-related tests for regression**

Run: `cd sidequest-server && uv run pytest tests/handlers/test_action_reveal.py tests/handlers/test_player_action_clears_reveals.py tests/server/test_session_room_disconnect_clears_reveals.py tests/telemetry/test_action_reveal_otel.py -v`
Expected: PASS (all)

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/handlers/action_reveal.py sidequest/handlers/player_action.py sidequest/server/session_room.py tests/telemetry/test_action_reveal_otel.py
git commit -m "feat(otel): action_reveal watcher events — composing, submitted, cleared, dropped"
```

---

## Task 8: Server end-to-end wiring test

Drive a real `SessionRoom` with two seated players. Send `composing` from socket 1; assert socket 2 receives it and socket 1 does not. Proves the dispatch is wired AND `exclude_socket_id` is respected.

**Files:**
- Test: `sidequest-server/tests/server/test_action_reveal_wired.py`

- [ ] **Step 1: Write the wiring test**

Create `sidequest-server/tests/server/test_action_reveal_wired.py`:

```python
"""End-to-end wiring test for ACTION_REVEAL.

Boots a real SessionRoom with two seated players, dispatches an
ACTION_REVEAL composing message from socket 1, and asserts that
socket 2's outbound queue receives the message verbatim while
socket 1's queue is empty.
"""

import asyncio
import pytest

from sidequest.handlers.action_reveal import ActionRevealHandler
from sidequest.protocol.messages import (
    ActionRevealMessage,
    ActionRevealPayload,
    ActionRevealStatus,
)
from sidequest.server.session_room import SessionRoom


@pytest.mark.asyncio
async def test_composing_fans_out_to_peer_only():
    room = SessionRoom(slug="wiring-test")  # adjust constructor if needed
    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()
    # Wire two sockets + queues. Adjust to whatever API SessionRoom exposes
    # (e.g., room.register_socket(...), or direct dict mutation matching
    # the disconnect test pattern).
    room._outbound_queues["s1"] = q1
    room._outbound_queues["s2"] = q2
    room._sockets["s1"] = "p1"
    room._sockets["s2"] = "p2"

    # Build a mock session for socket 1.
    class FakeSession:
        _socket_id = "s1"
        _player_id = "p1"
        _room = room

    handler = ActionRevealHandler()
    msg = ActionRevealMessage(
        payload=ActionRevealPayload(
            player_id="p1",
            character_name="Alex",
            status=ActionRevealStatus.COMPOSING,
            action="I sneak around the back",
            aside=False,
            seq=0,
            round=0,
        ),
        player_id="p1",
    )

    await handler.handle(FakeSession(), msg)

    assert q1.empty(), "sender's own socket should not receive its own composing"
    assert not q2.empty(), "peer socket should receive the broadcast"
    received = q2.get_nowait()
    assert isinstance(received, ActionRevealMessage)
    assert received.payload.action == "I sneak around the back"
    assert received.payload.player_id == "p1"
```

If `SessionRoom` constructor or registration API differs, adapt — refer to existing tests in `tests/server/` for boot patterns.

- [ ] **Step 2: Run test**

Run: `cd sidequest-server && uv run pytest tests/server/test_action_reveal_wired.py -v`
Expected: PASS

- [ ] **Step 3: Run the entire server suite — final regression check before client work**

Run: `cd sidequest-server && uv run pytest -x`
Expected: PASS (all)

- [ ] **Step 4: Commit**

```bash
cd sidequest-server
git add tests/server/test_action_reveal_wired.py
git commit -m "test(action-reveal): end-to-end wiring — fan-out excludes sender"
```

---

## Task 9: Client TS types

Extend `ActionRevealEntry` and add a discriminated `ActionRevealMessage` type matching the server payload.

**Files:**
- Modify: `sidequest-ui/src/types/payloads.ts`
- Modify: `sidequest-ui/src/types/protocol.ts` (verify existing `ACTION_REVEAL` enum)
- Test: `sidequest-ui/src/types/__tests__/action-reveal-types.test.ts`

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/types/__tests__/action-reveal-types.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { MessageType } from "../protocol";
import type { ActionRevealEntry, ActionRevealStatus } from "../payloads";

describe("ActionReveal types", () => {
  it("MessageType.ACTION_REVEAL exists", () => {
    expect(MessageType.ACTION_REVEAL).toBe("ACTION_REVEAL");
  });

  it("ActionRevealEntry carries status, action, aside, seq, round", () => {
    const entry: ActionRevealEntry = {
      player_id: "p1",
      character_name: "Alex",
      status: "composing" as ActionRevealStatus,
      action: "I sneak in",
      aside: false,
      seq: 3,
      round: 7,
    };
    expect(entry.status).toBe("composing");
    expect(entry.seq).toBe(3);
  });

  it("ActionRevealStatus union covers all three", () => {
    const composing: ActionRevealStatus = "composing";
    const submitted: ActionRevealStatus = "submitted";
    const cleared: ActionRevealStatus = "cleared";
    expect([composing, submitted, cleared]).toEqual([
      "composing",
      "submitted",
      "cleared",
    ]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/types/__tests__/action-reveal-types.test.ts`
Expected: FAIL — type errors / `ActionRevealStatus` not exported

- [ ] **Step 3: Modify `src/types/payloads.ts`**

Replace the existing `ActionRevealEntry`:

```typescript
export type ActionRevealStatus = "composing" | "submitted" | "cleared";

export interface ActionRevealEntry {
  player_id: string;
  character_name: string;
  status: ActionRevealStatus;
  action: string;
  aside: boolean;
  seq: number;
  round: number;
}

export interface ActionRevealPayload extends ActionRevealEntry {}
```

- [ ] **Step 4: Verify existing `ACTION_REVEAL` enum value**

Read `sidequest-ui/src/types/protocol.ts`. Confirm `ACTION_REVEAL: "ACTION_REVEAL"` is present (recon shows it is). No change needed.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/types/__tests__/action-reveal-types.test.ts`
Expected: PASS

- [ ] **Step 6: Run client typecheck for regressions in consumers of the old shape**

Run: `cd sidequest-ui && npx tsc -b --noEmit 2>&1 | head -40`
Expected: Either no errors, OR errors only in places that consumed the OLD `ActionRevealEntry.action` field with no other fields. Investigate any breakage; the old shape was unused per recon, so this should be clean.

- [ ] **Step 7: Commit**

```bash
cd sidequest-ui
git add src/types/payloads.ts src/types/__tests__/action-reveal-types.test.ts
git commit -m "feat(types): extend ActionRevealEntry with status, aside, seq, round"
```

---

## Task 10: `usePeerReveals` hook

State map of peer reveals keyed by `player_id`. Drops self. Upserts only on monotonic seq within `round`. `cleared` deletes. Round-counter transition flushes the map.

**Files:**
- Create: `sidequest-ui/src/hooks/usePeerReveals.ts`
- Test: `sidequest-ui/src/hooks/__tests__/usePeerReveals.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/hooks/__tests__/usePeerReveals.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePeerReveals } from "../usePeerReveals";
import type { ActionRevealEntry } from "@/types/payloads";

const reveal = (overrides: Partial<ActionRevealEntry>): ActionRevealEntry => ({
  player_id: "p2",
  character_name: "Bob",
  status: "composing",
  action: "I draw",
  aside: false,
  seq: 0,
  round: 1,
  ...overrides,
});

describe("usePeerReveals", () => {
  it("upserts composing for a peer", () => {
    const { result } = renderHook(() =>
      usePeerReveals({ selfPlayerId: "p1", round: 1 })
    );
    act(() => result.current.apply(reveal({ seq: 0, action: "I" })));
    act(() => result.current.apply(reveal({ seq: 1, action: "I dr" })));
    expect(result.current.reveals.get("p2")?.action).toBe("I dr");
  });

  it("drops own player_id", () => {
    const { result } = renderHook(() =>
      usePeerReveals({ selfPlayerId: "p1", round: 1 })
    );
    act(() => result.current.apply(reveal({ player_id: "p1" })));
    expect(result.current.reveals.size).toBe(0);
  });

  it("drops stale seq within same round", () => {
    const { result } = renderHook(() =>
      usePeerReveals({ selfPlayerId: "p1", round: 1 })
    );
    act(() => result.current.apply(reveal({ seq: 5, action: "five" })));
    act(() => result.current.apply(reveal({ seq: 3, action: "three" })));
    expect(result.current.reveals.get("p2")?.action).toBe("five");
  });

  it("submitted upsert preserves later updates", () => {
    const { result } = renderHook(() =>
      usePeerReveals({ selfPlayerId: "p1", round: 1 })
    );
    act(() => result.current.apply(reveal({ seq: 1, status: "composing", action: "abc" })));
    act(() => result.current.apply(reveal({ seq: 2, status: "submitted", action: "abc" })));
    expect(result.current.reveals.get("p2")?.status).toBe("submitted");
  });

  it("cleared deletes the entry", () => {
    const { result } = renderHook(() =>
      usePeerReveals({ selfPlayerId: "p1", round: 1 })
    );
    act(() => result.current.apply(reveal({ seq: 1 })));
    act(() =>
      result.current.apply(reveal({ status: "cleared", action: "", seq: 0 }))
    );
    expect(result.current.reveals.size).toBe(0);
  });

  it("round transition flushes the map", () => {
    const { result, rerender } = renderHook(
      ({ round }) => usePeerReveals({ selfPlayerId: "p1", round }),
      { initialProps: { round: 1 } }
    );
    act(() => result.current.apply(reveal({ seq: 1, round: 1 })));
    expect(result.current.reveals.size).toBe(1);
    rerender({ round: 2 });
    expect(result.current.reveals.size).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/hooks/__tests__/usePeerReveals.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write the hook**

Create `sidequest-ui/src/hooks/usePeerReveals.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import type { ActionRevealEntry } from "@/types/payloads";

export interface PeerReveal extends ActionRevealEntry {}

export interface UsePeerRevealsOptions {
  selfPlayerId: string | null | undefined;
  round: number;
}

export interface UsePeerRevealsResult {
  reveals: Map<string, PeerReveal>;
  apply: (entry: ActionRevealEntry) => void;
}

/**
 * Track peer reveals (composing / submitted) for the current round.
 * Drops self, drops non-monotonic seq, deletes on cleared, flushes on round change.
 *
 * ADR-036 Action Visibility Model.
 */
export function usePeerReveals({
  selfPlayerId,
  round,
}: UsePeerRevealsOptions): UsePeerRevealsResult {
  const [reveals, setReveals] = useState<Map<string, PeerReveal>>(new Map());
  // Track last seq per player_id within the current round for monotonicity.
  const lastSeqRef = useRef<Map<string, number>>(new Map());

  // Round transition: flush state.
  useEffect(() => {
    setReveals(new Map());
    lastSeqRef.current = new Map();
  }, [round]);

  const apply = useCallback(
    (entry: ActionRevealEntry) => {
      if (entry.player_id === selfPlayerId) return;
      // Reject prior-round entries; current-round only.
      if (entry.round !== round) return;

      if (entry.status === "cleared") {
        setReveals((prev) => {
          if (!prev.has(entry.player_id)) return prev;
          const next = new Map(prev);
          next.delete(entry.player_id);
          return next;
        });
        lastSeqRef.current.delete(entry.player_id);
        return;
      }

      const lastSeq = lastSeqRef.current.get(entry.player_id);
      if (lastSeq !== undefined && entry.seq <= lastSeq) return;
      lastSeqRef.current.set(entry.player_id, entry.seq);

      setReveals((prev) => {
        const next = new Map(prev);
        next.set(entry.player_id, { ...entry });
        return next;
      });
    },
    [selfPlayerId, round]
  );

  return { reveals, apply };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/hooks/__tests__/usePeerReveals.test.tsx`
Expected: PASS — 6 passed

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add src/hooks/usePeerReveals.ts src/hooks/__tests__/usePeerReveals.test.tsx
git commit -m "feat(hooks): usePeerReveals — peer reveal state machine"
```

---

## Task 11: `PeerRevealList` component

A new sibling to `MultiplayerTurnBanner`. Renders one row per peer reveal with composing/submitted styling. Stable order by `partyMembers` prop. `prefers-reduced-motion` guards transitions. Empty `reveals` → `null` (no DOM).

**Files:**
- Create: `sidequest-ui/src/components/PeerRevealList.tsx`
- Test: `sidequest-ui/src/components/__tests__/PeerRevealList.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `sidequest-ui/src/components/__tests__/PeerRevealList.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PeerRevealList } from "../PeerRevealList";
import type { PeerReveal } from "@/hooks/usePeerReveals";

const reveal = (over: Partial<PeerReveal>): PeerReveal => ({
  player_id: "p2",
  character_name: "Bob",
  status: "composing",
  action: "I draw my sword",
  aside: false,
  seq: 1,
  round: 1,
  ...over,
});

const partyOrder = ["p1", "p2", "p3"];

describe("PeerRevealList", () => {
  it("renders nothing when reveals empty", () => {
    const { container } = render(
      <PeerRevealList reveals={new Map()} partyOrder={partyOrder} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a composing row with header + action text", () => {
    const map = new Map([["p2", reveal({ action: "I creep" })]]);
    render(<PeerRevealList reveals={map} partyOrder={partyOrder} />);
    expect(screen.getByText(/Bob is composing/)).toBeInTheDocument();
    expect(screen.getByText(/I creep/)).toBeInTheDocument();
  });

  it("renders a submitted row with check + action text", () => {
    const map = new Map([
      ["p2", reveal({ status: "submitted", action: "I draw my pistol" })],
    ]);
    render(<PeerRevealList reveals={map} partyOrder={partyOrder} />);
    expect(screen.getByText(/Bob.*submitted/)).toBeInTheDocument();
    expect(screen.getByText(/I draw my pistol/)).toBeInTheDocument();
  });

  it("renders rows in partyOrder, not insertion order", () => {
    const map = new Map([
      ["p3", reveal({ player_id: "p3", character_name: "Carol", action: "z" })],
      ["p2", reveal({ player_id: "p2", character_name: "Bob", action: "y" })],
    ]);
    render(<PeerRevealList reveals={map} partyOrder={partyOrder} />);
    const headers = screen.getAllByTestId("peer-reveal-header");
    expect(headers[0].textContent).toMatch(/Bob/);
    expect(headers[1].textContent).toMatch(/Carol/);
  });

  it("aside flag adds the OOC visual marker", () => {
    const map = new Map([
      ["p2", reveal({ aside: true, action: "looks like a trap" })],
    ]);
    render(<PeerRevealList reveals={map} partyOrder={partyOrder} />);
    const row = screen.getByTestId("peer-reveal-row-p2");
    expect(row.querySelector("[data-aside='true']")).not.toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/PeerRevealList.test.tsx`
Expected: FAIL — module not found

- [ ] **Step 3: Write the component**

Create `sidequest-ui/src/components/PeerRevealList.tsx`:

```typescript
import type { PeerReveal } from "@/hooks/usePeerReveals";

export interface PeerRevealListProps {
  reveals: Map<string, PeerReveal>;
  /** Stable ordering — array of player_ids in seat order. Rows render in this order regardless of insertion. */
  partyOrder: string[];
}

export function PeerRevealList({ reveals, partyOrder }: PeerRevealListProps) {
  if (reveals.size === 0) return null;

  // Order strictly by partyOrder; any peers not in partyOrder are appended last (alphabetic by player_id).
  const ordered: PeerReveal[] = [];
  for (const pid of partyOrder) {
    const r = reveals.get(pid);
    if (r) ordered.push(r);
  }
  for (const [pid, r] of reveals) {
    if (!partyOrder.includes(pid)) ordered.push(r);
  }

  return (
    <div
      data-testid="peer-reveal-list"
      className="space-y-1 mb-1 motion-reduce:transition-none"
    >
      {ordered.map((r) => (
        <div
          key={r.player_id}
          data-testid={`peer-reveal-row-${r.player_id}`}
          className={`flex flex-col gap-0.5 px-3 py-1.5 rounded-md text-sm border-l-4 ${
            r.status === "submitted"
              ? "border-l-emerald-500 bg-emerald-500/5 text-emerald-100/90"
              : "border-l-amber-500/60 bg-amber-500/5 text-amber-100/80"
          }`}
        >
          <span
            data-testid="peer-reveal-header"
            className="text-xs uppercase tracking-wide opacity-70"
          >
            {r.status === "submitted"
              ? `${r.character_name} ✓ submitted`
              : `${r.character_name} is composing`}
          </span>
          <span
            data-aside={r.aside ? "true" : "false"}
            className={r.aside ? "italic text-muted-foreground" : ""}
          >
            {r.aside ? `(${r.action})` : r.action}
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/PeerRevealList.test.tsx`
Expected: PASS — 5 passed

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add src/components/PeerRevealList.tsx src/components/__tests__/PeerRevealList.test.tsx
git commit -m "feat(ui): PeerRevealList component — composing + submitted rows"
```

---

## Task 12: Wire `PeerRevealList` + `usePeerReveals` into the screen

The screen that mounts `MultiplayerTurnBanner` and `InputBar` needs to:
1. Mount `usePeerReveals` with the current round + self player_id.
2. Route incoming `ACTION_REVEAL` messages from the WS handler into `usePeerReveals.apply`.
3. Render `<PeerRevealList />` directly above `<MultiplayerTurnBanner />`.

**Files:**
- Modify: the screen/component currently mounting `<MultiplayerTurnBanner>` (likely `src/screens/Game.tsx` or `src/App.tsx` near the InputBar block — recon flagged App.tsx 1554–1616 as the relevant region)

- [ ] **Step 1: Find the mount site**

Run: `cd sidequest-ui && grep -rn "MultiplayerTurnBanner" src/ --include="*.tsx" --include="*.ts" | head -20`

Identify the file + line where `<MultiplayerTurnBanner ... />` is rendered. That's where `<PeerRevealList />` goes immediately above. Also identify where the WS message handler dispatches incoming messages (e.g. `onMessage` in App.tsx, or a switch/case on `msg.type`).

- [ ] **Step 2: Add the hook + dispatch wiring**

In the screen file, near the existing WS state derivation (App.tsx ~1554–1616 per recon):

```typescript
import { usePeerReveals } from "@/hooks/usePeerReveals";
import { PeerRevealList } from "@/components/PeerRevealList";
import { MessageType } from "@/types/protocol";
import type { ActionRevealEntry } from "@/types/payloads";

// Inside the component:
const peerReveals = usePeerReveals({
  selfPlayerId: localPlayerId,
  round: currentRound, // whichever local var holds the round counter
});

const partyOrder = useMemo(
  () => partyMembers.map((m) => m.player_id),
  [partyMembers]
);

// In the WS message handler (the existing onMessage dispatch):
//   case MessageType.ACTION_REVEAL:
//     peerReveals.apply(msg.payload as ActionRevealEntry);
//     break;
```

If the file uses a different message-routing pattern (e.g. a useEffect listening to a message stream), apply the same call: `peerReveals.apply(payload)`.

- [ ] **Step 3: Render `PeerRevealList` above `MultiplayerTurnBanner`**

Replace the existing `<MultiplayerTurnBanner ... />` render block with:

```tsx
<>
  <PeerRevealList reveals={peerReveals.reveals} partyOrder={partyOrder} />
  <MultiplayerTurnBanner
    /* … existing props unchanged … */
  />
</>
```

- [ ] **Step 4: Manual smoke check**

Run: `cd /Users/slabgorb/Projects/oq-2 && just up`

Open two browser tabs as separate players in the same session. Type in tab 1; expect to see the text appear in tab 2 within ~300ms (you'll see this once Task 13 lands — the InputBar broadcast). For now, the component is wired but no client is sending — verify `npx tsc -b` is clean.

Run: `cd sidequest-ui && npx tsc -b --noEmit 2>&1 | head -20`
Expected: clean (no errors)

- [ ] **Step 5: Commit**

```bash
cd sidequest-ui
git add <screen file>
git commit -m "feat(ui): wire PeerRevealList + usePeerReveals into game screen"
```

---

## Task 13: InputBar — broadcast composing + submitted

Add 250ms-debounced `composing` broadcast on text changes. On submit, fire `submitted` (synchronously) before the existing `onSend` callback. Reset seq when the round prop changes.

**Files:**
- Modify: `sidequest-ui/src/components/InputBar.tsx`
- Test: `sidequest-ui/src/components/__tests__/InputBar.test.tsx` (extend if exists; create if not)

- [ ] **Step 1: Write the failing tests**

Create or extend `sidequest-ui/src/components/__tests__/InputBar.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, act } from "@testing-library/react";
import InputBar from "../InputBar";

describe("InputBar — action reveal broadcast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces composing broadcasts to 250ms", () => {
    const onReveal = vi.fn();
    const { container } = render(
      <InputBar
        onSend={() => {}}
        onReveal={onReveal}
        round={1}
      />
    );
    const input = container.querySelector("input") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "I" } });
    fireEvent.change(input, { target: { value: "I s" } });
    fireEvent.change(input, { target: { value: "I sn" } });

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(onReveal).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200); // total 300ms
    });
    expect(onReveal).toHaveBeenCalledTimes(1);
    expect(onReveal).toHaveBeenLastCalledWith({
      status: "composing",
      action: "I sn",
      aside: false,
      seq: 0,
    });
  });

  it("submits before onSend with monotonic seq", () => {
    const onSend = vi.fn();
    const onReveal = vi.fn();
    const { container } = render(
      <InputBar onSend={onSend} onReveal={onReveal} round={1} />
    );
    const input = container.querySelector("input") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "I draw" } });
    act(() => vi.advanceTimersByTime(300));
    fireEvent.keyDown(input, { key: "Enter" });

    const submitCallIdx = onReveal.mock.calls.findIndex(
      ([arg]) => arg.status === "submitted"
    );
    const sendCallIdx = onSend.mock.invocationCallOrder[0];
    const submittedInvocation =
      onReveal.mock.invocationCallOrder[submitCallIdx];
    expect(submittedInvocation).toBeLessThan(sendCallIdx);
    expect(onReveal.mock.calls[submitCallIdx][0].action).toBe("I draw");
  });

  it("seq resets when round prop changes", () => {
    const onReveal = vi.fn();
    const { container, rerender } = render(
      <InputBar onSend={() => {}} onReveal={onReveal} round={1} />
    );
    const input = container.querySelector("input") as HTMLInputElement;

    fireEvent.change(input, { target: { value: "x" } });
    act(() => vi.advanceTimersByTime(300));
    fireEvent.change(input, { target: { value: "xy" } });
    act(() => vi.advanceTimersByTime(300));
    expect(onReveal.mock.calls[0][0].seq).toBe(0);
    expect(onReveal.mock.calls[1][0].seq).toBe(1);

    rerender(<InputBar onSend={() => {}} onReveal={onReveal} round={2} />);
    fireEvent.change(input, { target: { value: "new" } });
    act(() => vi.advanceTimersByTime(300));
    expect(onReveal.mock.calls.at(-1)![0].seq).toBe(0);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/InputBar.test.tsx`
Expected: FAIL — `onReveal` and `round` not props on InputBar

- [ ] **Step 3: Modify `InputBar.tsx`**

Replace the contents of `sidequest-ui/src/components/InputBar.tsx`:

```typescript
import { useState, useCallback, useEffect, useRef, type KeyboardEvent } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface InputBarRevealCall {
  status: "composing" | "submitted";
  action: string;
  aside: boolean;
  seq: number;
}

export interface InputBarProps {
  onSend: (text: string, aside: boolean) => void;
  /**
   * ADR-036 Action Visibility Model: emit composing/submitted action reveal
   * to peers. Optional — single-player and legacy callers pass nothing.
   */
  onReveal?: (call: InputBarRevealCall) => void;
  /**
   * Current ADR-051 round counter; passed in so the component can reset its
   * monotonic seq counter on round transitions.
   */
  round?: number;
  disabled?: boolean;
  mobile?: boolean;
  thinking?: boolean;
  waitingForPlayer?: string;
}

const COMPOSING_DEBOUNCE_MS = 250;

export default function InputBar({
  onSend,
  onReveal,
  round = 0,
  disabled,
  mobile,
  thinking,
  waitingForPlayer,
}: InputBarProps) {
  const [text, setText] = useState("");
  const [aside, setAside] = useState(false);

  // seq monotonic per-round; reset when round prop changes.
  const seqRef = useRef(0);
  useEffect(() => {
    seqRef.current = 0;
  }, [round]);

  // Debounced composing broadcast.
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!onReveal) return;
    if (text.length === 0) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onReveal({
        status: "composing",
        action: text,
        aside,
        seq: seqRef.current++,
      });
    }, COMPOSING_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [text, aside, onReveal]);

  const submit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;
    // Cancel any pending composing — the submitted message supersedes it.
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    if (onReveal) {
      onReveal({
        status: "submitted",
        action: trimmed,
        aside,
        seq: seqRef.current++,
      });
    }
    onSend(trimmed, aside);
    setText("");
  }, [text, aside, onSend, onReveal]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  const placeholder =
    waitingForPlayer ? `Waiting for ${waitingForPlayer}…` :
    thinking ? "The narrator is thinking..." :
    aside ? "What do you whisper?" :
    "What do you do?";

  return (
    <div data-testid="input-bar" className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex items-center flex-1">
          {aside && (
            <span className="text-muted-foreground/40 text-lg pl-1 select-none">(</span>
          )}
          <Input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            className={cn(aside && "text-muted-foreground/70 italic")}
            {...(mobile ? { "data-mobile": "true" } : {})}
          />
          {aside && (
            <span className="text-muted-foreground/40 text-lg pr-1 select-none">)</span>
          )}
        </div>
        <button
          data-testid="aside-toggle"
          className={cn(
            "text-sm transition-colors px-1.5",
            aside
              ? "text-muted-foreground/60"
              : "text-muted-foreground/25 hover:text-muted-foreground/45"
          )}
          onClick={() => setAside(!aside)}
          aria-label={aside ? "Speaking aside (click to speak normally)" : "Click to speak aside"}
          title={aside ? "Speaking aside" : "Aside"}
        >
          (…)
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/InputBar.test.tsx`
Expected: PASS — 3 passed

- [ ] **Step 5: Wire `onReveal` + `round` from the parent screen**

In the same parent file edited in Task 12, build the `onReveal` callback that constructs an `ACTION_REVEAL` `GameMessage` and calls the WS hook's `send`. Pass `onReveal` and `round` to `<InputBar>`:

```tsx
const handleReveal = useCallback(
  (call: InputBarRevealCall) => {
    send({
      type: MessageType.ACTION_REVEAL,
      payload: {
        player_id: localPlayerId ?? "",
        character_name: localCharacterName ?? "",
        status: call.status,
        action: call.action,
        aside: call.aside,
        seq: call.seq,
        round: currentRound,
      },
      player_id: localPlayerId ?? "",
    });
  },
  [send, localPlayerId, localCharacterName, currentRound]
);

// then:
<InputBar
  onSend={handleSend}
  onReveal={handleReveal}
  round={currentRound}
  /* ... existing props ... */
/>
```

- [ ] **Step 6: Run full client suite for regressions**

Run: `cd sidequest-ui && npx vitest run`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd sidequest-ui
git add src/components/InputBar.tsx src/components/__tests__/InputBar.test.tsx <screen file>
git commit -m "feat(ui): InputBar broadcasts ACTION_REVEAL composing + submitted"
```

---

## Task 14: Client end-to-end wiring test

Mount the actual screen wrapper with a `MockWebSocket`. Type into the input — assert outbound `ACTION_REVEAL composing` messages. Inject inbound `ACTION_REVEAL` from a peer — assert `PeerRevealList` renders the row. Proves end-to-end through the real component graph.

**Files:**
- Test: `sidequest-ui/src/__tests__/action-reveal-wiring.test.tsx`

- [ ] **Step 1: Read the existing wiring-test pattern**

Read `sidequest-ui/src/__tests__/reconnect-banner-wiring.test.tsx` (referenced in recon, lines 1–145). Note the `MockWebSocket`, `vi.stubGlobal("WebSocket", MockWebSocket)`, `vi.useFakeTimers()`, and `act()` patterns.

- [ ] **Step 2: Write the wiring test**

Create `sidequest-ui/src/__tests__/action-reveal-wiring.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, act, screen } from "@testing-library/react";
import { useGameSocket } from "@/hooks/useGameSocket";
import { usePeerReveals } from "@/hooks/usePeerReveals";
import { PeerRevealList } from "@/components/PeerRevealList";
import InputBar from "@/components/InputBar";
import { MessageType } from "@/types/protocol";

// MockWebSocket — copy of pattern from reconnect-banner-wiring.test.tsx
const instances: MockWebSocket[] = [];
class MockWebSocket {
  url: string;
  readyState = WebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  sent: string[] = [];
  constructor(url: string) {
    this.url = url;
    instances.push(this);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close"));
  }
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
}

describe("ACTION_REVEAL end-to-end wiring", () => {
  beforeEach(() => {
    instances.length = 0;
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  function Host() {
    const { send } = useGameSocket({ url: "ws://test/socket", onMessage: (msg) => {
      if (msg.type === MessageType.ACTION_REVEAL) {
        peerReveals.apply(msg.payload);
      }
    }});
    const peerReveals = usePeerReveals({ selfPlayerId: "p1", round: 1 });
    return (
      <>
        <PeerRevealList reveals={peerReveals.reveals} partyOrder={["p1", "p2"]} />
        <InputBar
          onSend={() => {}}
          onReveal={(call) => send({
            type: MessageType.ACTION_REVEAL,
            payload: {
              player_id: "p1",
              character_name: "Alex",
              status: call.status,
              action: call.action,
              aside: call.aside,
              seq: call.seq,
              round: 1,
            },
            player_id: "p1",
          })}
          round={1}
        />
      </>
    );
  }

  it("typing produces outbound composing; inbound peer reveal renders", () => {
    render(<Host />);
    act(() => {
      const ws = instances[0];
      ws.readyState = WebSocket.OPEN;
      ws.onopen?.(new Event("open"));
    });

    // Type — debounced composing fires.
    const input = screen.getByPlaceholderText("What do you do?");
    fireEvent.change(input, { target: { value: "I sneak in" } });
    act(() => vi.advanceTimersByTime(300));

    const sent = instances[0].sent.map((s) => JSON.parse(s));
    const composing = sent.find(
      (m) => m.type === "ACTION_REVEAL" && m.payload.status === "composing"
    );
    expect(composing).toBeDefined();
    expect(composing.payload.action).toBe("I sneak in");

    // Inject inbound peer reveal.
    act(() => {
      instances[0].onmessage?.(
        new MessageEvent("message", {
          data: JSON.stringify({
            type: "ACTION_REVEAL",
            payload: {
              player_id: "p2",
              character_name: "Bob",
              status: "composing",
              action: "I draw",
              aside: false,
              seq: 0,
              round: 1,
            },
          }),
        })
      );
    });

    expect(screen.getByText(/Bob is composing/)).toBeInTheDocument();
    expect(screen.getByText(/I draw/)).toBeInTheDocument();
  });
});
```

The exact API for `useGameSocket` may differ slightly — adapt to the existing hook's interface. The point is to mount the real `useGameSocket`, the real `usePeerReveals`, the real `PeerRevealList`, and the real `InputBar` — proving the chain is wired.

- [ ] **Step 3: Run the wiring test**

Run: `cd sidequest-ui && npx vitest run src/__tests__/action-reveal-wiring.test.tsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd sidequest-ui
git add src/__tests__/action-reveal-wiring.test.tsx
git commit -m "test(ui): action-reveal end-to-end wiring through useGameSocket"
```

---

## Task 15: ADR-036 amendment

Add an "Action Visibility Model" section recording the doctrine shift: action text broadcasts live to all party members; sealed-letter discipline retreats to narration output (SECRET_NOTE, per-player visibility tags). Cross-link the playtest 2026-05-03 feedback memory and this spec.

**Files:**
- Modify: `docs/adr/036-multiplayer-turn-coordination.md`

- [ ] **Step 1: Read the existing ADR-036**

Read `/Users/slabgorb/Projects/oq-2/docs/adr/036-multiplayer-turn-coordination.md` to see the structure and tone.

- [ ] **Step 2: Append the amendment section**

Add a new section before any existing "Status" / "Consequences" tail:

```markdown
## Amendment — Action Visibility Model (2026-05-03)

**Trigger:** Playtest 2026-05-03 feedback. Coordination broke down because
cinematic-mode's information-hiding default was too aggressive — players
couldn't see what teammates were composing or what they had already
submitted, so plans formed in isolation and conflicted on resolution.

**Decision:** Action *input* visibility is the new default. All party
members see each other's in-progress and post-submit action text in real
time during cinematic-mode rounds. Information-hiding moves entirely into
*narration output* — SECRET_NOTE payloads and per-player `visibility_tag`
filtering, both of which already exist.

**What is unchanged:**
- The cinematic-mode action buffer.
- The barrier and CAS-guarded dispatcher (single narrator dispatch per round).
- `PLAYER_ACTION` semantics. The sealed-letter resolution mechanic (dogfight
  cross-product lookup in `sealed_letter.py`) is a different system and is
  untouched.

**Mechanism:** New `ACTION_REVEAL` message type carries `composing` /
`submitted` updates from clients (debounced ~250ms) and `cleared` updates
from the server (emitted at barrier-fire dispatch and on socket disconnect).

**Cross-references:**
- Spec: `docs/superpowers/specs/2026-05-03-live-teammate-typing-design.md`
- Memory: `project_playtest_2026_05_03.md`
- ADR-051 (round counter authority for the `round` field)

**Future:** If a scene ever genuinely needs hidden input (perception
rewriter, traitor briefings, charmed players), introduce a per-scene flag
then. Current playgroup play does not need it.
```

- [ ] **Step 3: Verify the link target exists**

Run: `ls /Users/slabgorb/Projects/oq-2/docs/superpowers/specs/2026-05-03-live-teammate-typing-design.md`
Expected: file exists.

- [ ] **Step 4: Commit**

```bash
cd /Users/slabgorb/Projects/oq-2
git add docs/adr/036-multiplayer-turn-coordination.md
git commit -m "docs(adr-036): action visibility model — relax sealed-letter input hiding"
```

---

## Task 16: Final verification + manual smoke

Run all suites and perform the three-step manual smoke described in the spec.

- [ ] **Step 1: Server full suite**

Run: `cd sidequest-server && uv run pytest -x`
Expected: PASS (all)

- [ ] **Step 2: Server lint**

Run: `cd sidequest-server && uv run ruff check .`
Expected: clean

- [ ] **Step 3: Client full suite**

Run: `cd sidequest-ui && npx vitest run`
Expected: PASS (all)

- [ ] **Step 4: Client typecheck + lint**

Run: `cd sidequest-ui && npx tsc -b --noEmit && npx eslint .`
Expected: clean

- [ ] **Step 5: Manual smoke test**

Run: `cd /Users/slabgorb/Projects/oq-2 && just up`

In two browser tabs joined to the same session as different players:

1. Type in tab 1 — text appears in tab 2's PeerRevealList row within ~300ms.
2. Send from tab 1 — tab 2's row flips to "✓ submitted" with locked text.
3. Submit from both — narration kicks off — both PeerRevealLists clear.

Expected: all three pass.

- [ ] **Step 6: Verify OTEL events flow**

While the smoke test is running, check the GM dashboard / OTEL stream for the four event names:
- `action_reveal.composing`
- `action_reveal.submitted`
- `action_reveal.cleared`
- (`action_reveal.dropped_rate_limit` only fires under buggy/hand-fired clients — not expected in normal play)

If `action_reveal.composing` does not fire while you're typing, the feature is broken — investigate the InputBar → useGameSocket path before declaring done.

- [ ] **Step 7: No commit needed; verification only.**

---

## Self-Review Checklist (run after writing the plan)

- [x] Spec coverage: every spec section maps to at least one task. Cinematic-mode timeout was dropped intentionally (documented in the refinements block at the top); journal feature is explicitly out of scope.
- [x] Placeholder scan: no TBD/TODO/"add appropriate" placeholders.
- [x] Type consistency:
  - `action` field name used everywhere (server `ActionRevealPayload.action`, client `ActionRevealEntry.action`, InputBar `call.action`).
  - `seq: int` non-negative on server (Field(ge=0)); seq monotonic per (player_id, round) on both sides.
  - `status` is `"composing" | "submitted" | "cleared"` with identical strings between server and client.
  - `_broadcast_cleared_to_party` referenced consistently in Task 5 and Task 7.
  - `_emit_action_reveal_cleared` referenced consistently in Task 6 and Task 7.
  - `usePeerReveals` returns `{reveals, apply}` — used consistently in Tasks 10, 12, 14.
  - `PeerRevealList` props `{reveals, partyOrder}` — used consistently in Tasks 11, 12, 14.
  - `InputBarProps.onReveal` and `round` — used consistently in Tasks 13, 14.
