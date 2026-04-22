# Multiplayer Plan 02 — Party, Presence, Pause-on-Drop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Depends on:** Plan 01 must be merged first (slug routing + mode in WS connect).

**Goal:** Support multiple simultaneous WebSocket connections to a single multiplayer slug, track display-name identity, gate solo slugs to one socket, pause narrator advancement whenever any seated player is disconnected.

**Architecture:** An in-memory `SessionRoom` per slug holds the set of connected sockets and the roster of seated players (player_id → character_slot, plus disconnected/connected state). Narrator-advancing mutations check the room and refuse to proceed if any seated player is missing. Display name is a cookie/localStorage value on the client; it's attached to the WebSocket connect frame as `player_id` and the server uses it verbatim.

**Tech Stack:** Python (FastAPI WebSocket, asyncio), pytest, React + TypeScript, vitest.

---

## File Structure

**Create:**
- `sidequest-server/sidequest/server/session_room.py` — in-memory room registry.
- `sidequest-server/tests/server/test_session_room.py`
- `sidequest-server/tests/server/test_solo_single_slot.py`
- `sidequest-server/tests/server/test_pause_on_drop.py`
- `sidequest-server/tests/server/test_party_wiring.py`
- `sidequest-ui/src/hooks/useDisplayName.ts`
- `sidequest-ui/src/hooks/__tests__/useDisplayName.test.ts`
- `sidequest-ui/src/components/PausedBanner.tsx`
- `sidequest-ui/src/components/__tests__/PausedBanner.test.tsx`

**Modify:**
- `sidequest-server/sidequest/server/websocket.py` — register/unregister with room on accept/disconnect.
- `sidequest-server/sidequest/server/session_handler.py` — consult room; add `player_joined` / `player_left` broadcast; gate narrator.
- `sidequest-server/sidequest/protocol/messages.py` — add `PLAYER_PRESENCE`, `GAME_PAUSED`, `GAME_RESUMED` message types.
- `sidequest-ui/src/screens/GameScreen.tsx` — read display name, pass on connect, render PausedBanner.

---

### Task 1: SessionRoom registry

**Files:**
- Create: `sidequest-server/sidequest/server/session_room.py`
- Test: `sidequest-server/tests/server/test_session_room.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_session_room.py
import pytest
from sidequest.server.session_room import SessionRoom, RoomRegistry, SoloSlotConflict
from sidequest.game.persistence import GameMode


def test_room_registry_returns_same_room_for_same_slug():
    reg = RoomRegistry()
    r1 = reg.get_or_create("slug-a", mode=GameMode.MULTIPLAYER)
    r2 = reg.get_or_create("slug-a", mode=GameMode.MULTIPLAYER)
    assert r1 is r2


def test_room_tracks_connected_players():
    room = SessionRoom(slug="slug-a", mode=GameMode.MULTIPLAYER)
    room.connect("alice", socket_id="sock-1")
    room.connect("bob", socket_id="sock-2")
    assert set(room.connected_player_ids()) == {"alice", "bob"}


def test_room_disconnect_removes_player():
    room = SessionRoom(slug="slug-a", mode=GameMode.MULTIPLAYER)
    room.connect("alice", socket_id="sock-1")
    room.disconnect(socket_id="sock-1")
    assert room.connected_player_ids() == []


def test_same_player_reconnect_updates_socket():
    room = SessionRoom(slug="slug-a", mode=GameMode.MULTIPLAYER)
    room.connect("alice", socket_id="sock-1")
    room.connect("alice", socket_id="sock-2")
    room.disconnect(socket_id="sock-1")
    assert "alice" in room.connected_player_ids()  # sock-2 still holds alice


def test_solo_room_rejects_second_connection():
    room = SessionRoom(slug="slug-a", mode=GameMode.SOLO)
    room.connect("alice", socket_id="sock-1")
    with pytest.raises(SoloSlotConflict):
        room.connect("bob", socket_id="sock-2")


def test_solo_room_allows_same_player_reconnect():
    room = SessionRoom(slug="slug-a", mode=GameMode.SOLO)
    room.connect("alice", socket_id="sock-1")
    room.disconnect(socket_id="sock-1")
    room.connect("alice", socket_id="sock-2")  # must not raise
    assert room.connected_player_ids() == ["alice"]


def test_seated_players_separate_from_connected():
    room = SessionRoom(slug="slug-a", mode=GameMode.MULTIPLAYER)
    room.seat("alice", character_slot="rux")
    room.seat("bob", character_slot="vex")
    room.connect("alice", socket_id="sock-1")
    # bob seated but not connected
    assert set(room.seated_player_ids()) == {"alice", "bob"}
    assert set(room.connected_player_ids()) == {"alice"}
    assert set(room.absent_seated_player_ids()) == {"bob"}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement SessionRoom**

```python
# sidequest-server/sidequest/server/session_room.py
"""In-memory per-slug room: who is connected, who is seated, solo-slot enforcement.

One SessionRoom exists per game slug. Lives for the life of the process; content
is derivable from the save so loss on restart is acceptable (players reconnect
and re-seat).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, Iterable, List

from sidequest.game.persistence import GameMode


class SoloSlotConflict(Exception):
    """Raised when a second player tries to connect to a solo game."""


@dataclass
class _Seat:
    player_id: str
    character_slot: str | None = None


@dataclass
class SessionRoom:
    slug: str
    mode: GameMode
    # player_id -> socket_id (only connected players)
    _connected: Dict[str, str] = field(default_factory=dict)
    _sockets: Dict[str, str] = field(default_factory=dict)  # socket_id -> player_id
    _seated: Dict[str, _Seat] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def connect(self, player_id: str, *, socket_id: str) -> None:
        with self._lock:
            if self.mode == GameMode.SOLO:
                other_players = [p for p in self._connected if p != player_id]
                if other_players:
                    raise SoloSlotConflict(
                        f"solo game {self.slug} already occupied by {other_players[0]}"
                    )
            # If same player reconnects on a new socket, drop the old socket mapping.
            old_socket = self._connected.get(player_id)
            if old_socket and old_socket != socket_id:
                self._sockets.pop(old_socket, None)
            self._connected[player_id] = socket_id
            self._sockets[socket_id] = player_id

    def disconnect(self, *, socket_id: str) -> str | None:
        with self._lock:
            player_id = self._sockets.pop(socket_id, None)
            if player_id is None:
                return None
            # Only remove from _connected if this socket is still the active one for that player.
            if self._connected.get(player_id) == socket_id:
                self._connected.pop(player_id, None)
            return player_id

    def seat(self, player_id: str, *, character_slot: str | None) -> None:
        with self._lock:
            self._seated[player_id] = _Seat(player_id=player_id, character_slot=character_slot)

    def unseat(self, player_id: str) -> None:
        with self._lock:
            self._seated.pop(player_id, None)

    def connected_player_ids(self) -> List[str]:
        with self._lock:
            return list(self._connected.keys())

    def seated_player_ids(self) -> List[str]:
        with self._lock:
            return list(self._seated.keys())

    def absent_seated_player_ids(self) -> List[str]:
        with self._lock:
            return [p for p in self._seated if p not in self._connected]

    def is_paused(self) -> bool:
        """Game is paused if any seated player is not currently connected."""
        return len(self.absent_seated_player_ids()) > 0


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: Dict[str, SessionRoom] = {}
        self._lock = RLock()

    def get_or_create(self, slug: str, *, mode: GameMode) -> SessionRoom:
        with self._lock:
            existing = self._rooms.get(slug)
            if existing is not None:
                return existing
            room = SessionRoom(slug=slug, mode=mode)
            self._rooms[slug] = room
            return room

    def get(self, slug: str) -> SessionRoom | None:
        with self._lock:
            return self._rooms.get(slug)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_room.py sidequest-server/tests/server/test_session_room.py
git commit -m "feat(server): SessionRoom + RoomRegistry with solo-slot enforcement"
```

---

### Task 2: Wire RoomRegistry into the FastAPI app + WebSocket lifecycle

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket.py`
- Modify: wherever the app is constructed (find with `grep -rn "FastAPI()" sidequest-server/sidequest`)

- [ ] **Step 1: Write failing wiring test**

```python
# sidequest-server/tests/server/test_session_room_wired.py
from datetime import date
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sidequest.server.app import create_app  # or import actual app module


def _seed_game(save_dir: Path, slug: str, mode: str) -> None:
    from sidequest.game.persistence import (
        SqliteStore, db_path_for_slug, upsert_game, GameMode,
    )
    db = db_path_for_slug(save_dir, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug=slug, mode=GameMode(mode),
                genre_slug="low_fantasy", world_slug="moldharrow-keep")


def test_connecting_adds_player_to_room(tmp_path: Path):
    app = create_app(save_dir=tmp_path)
    _seed_game(tmp_path, "2026-04-22-moldharrow-keep", "multiplayer")
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                      "payload": {"event": "connect", "game_slug": "2026-04-22-moldharrow-keep"}})
        ws.receive_json()  # drain SESSION_CONNECTED
        room = app.state.room_registry.get("2026-04-22-moldharrow-keep")
        assert room is not None
        assert "alice" in room.connected_player_ids()
    # Socket closed — player should be gone
    room = app.state.room_registry.get("2026-04-22-moldharrow-keep")
    assert "alice" not in room.connected_player_ids()
```

- [ ] **Step 2: Run it (failure)**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room_wired.py -v`
Expected: FAIL — no `room_registry` on `app.state`.

- [ ] **Step 3: Add registry + lifecycle hooks**

In the app factory (the file identified above), add:

```python
from sidequest.server.session_room import RoomRegistry

def create_app(save_dir: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.state.save_dir = save_dir or Path.home() / ".sidequest" / "saves"
    app.state.room_registry = RoomRegistry()
    # ... existing setup
    return app
```

In `sidequest-server/sidequest/server/websocket.py`, modify `ws_endpoint`:

```python
import uuid

async def ws_endpoint(websocket: WebSocket, handler: "WebSocketSessionHandler") -> None:
    await websocket.accept()
    socket_id = uuid.uuid4().hex
    registry = websocket.app.state.room_registry
    handler.attach_room_context(registry=registry, socket_id=socket_id)
    logger.info("ws.connection_accepted socket=%s", socket_id)
    try:
        while True:
            # ... existing loop unchanged
            ...
    except WebSocketDisconnect:
        pass
    finally:
        room = handler.current_room()
        if room is not None:
            left_player = room.disconnect(socket_id=socket_id)
            if left_player is not None:
                await handler.broadcast_presence_change(left_player=left_player)
        await handler.cleanup()
```

In `session_handler.py`, add:

```python
def attach_room_context(self, *, registry, socket_id: str) -> None:
    self._room_registry = registry
    self._socket_id = socket_id
    self._room: "SessionRoom | None" = None

def current_room(self):
    return self._room
```

And in the slug-connect branch (from Plan 01 Task 4), after loading the game row, add:

```python
from sidequest.server.session_room import SoloSlotConflict

room = self._room_registry.get_or_create(slug, mode=row.mode)
try:
    room.connect(player_id, socket_id=self._socket_id)
except SoloSlotConflict as exc:
    return [self._error(str(exc), reconnect_required=False)]
self._room = room
```

- [ ] **Step 4: Run the wiring test**

Run: `cd sidequest-server && uv run pytest tests/server/test_session_room_wired.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/websocket.py sidequest-server/sidequest/server/session_handler.py sidequest-server/sidequest/server/app.py sidequest-server/tests/server/test_session_room_wired.py
git commit -m "feat(ws): register/unregister sockets with SessionRoom on connect/disconnect"
```

---

### Task 3: Solo single-slot — second connection is rejected

**Files:**
- Test: `sidequest-server/tests/server/test_solo_single_slot.py`

- [ ] **Step 1: Write the test**

```python
# sidequest-server/tests/server/test_solo_single_slot.py
from datetime import date
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import SqliteStore, db_path_for_slug, upsert_game, GameMode


def test_second_connection_to_solo_is_rejected(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db); store.initialize()
    upsert_game(store, slug=slug, mode=GameMode.SOLO,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")

    app = create_app(save_dir=tmp_path)
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws1:
        ws1.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                       "payload": {"event": "connect", "game_slug": slug}})
        ws1.receive_json()

        with client.websocket_connect("/ws") as ws2:
            ws2.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                           "payload": {"event": "connect", "game_slug": slug}})
            msg = ws2.receive_json()
            assert msg["type"] == "ERROR"
            assert "solo" in msg["payload"]["message"].lower()
```

- [ ] **Step 2: Run — should already pass from Task 2's slug-connect branch**

Run: `cd sidequest-server && uv run pytest tests/server/test_solo_single_slot.py -v`
Expected: 1 passed. If it fails, the SoloSlotConflict branch in Task 2 wasn't wired — fix it.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_solo_single_slot.py
git commit -m "test(ws): solo slug rejects second connection"
```

---

### Task 4: Presence broadcast — PLAYER_PRESENCE messages

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_presence_broadcast.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_presence_broadcast.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import SqliteStore, db_path_for_slug, upsert_game, GameMode


def _seed(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")


def test_second_player_join_broadcasts_presence_to_first(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws_a:
        ws_a.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                        "payload": {"event": "connect", "game_slug": slug}})
        ws_a.receive_json()  # SESSION_CONNECTED

        with client.websocket_connect("/ws") as ws_b:
            ws_b.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                            "payload": {"event": "connect", "game_slug": slug}})
            ws_b.receive_json()  # SESSION_CONNECTED for bob

            msg = ws_a.receive_json()  # presence event for bob
            assert msg["type"] == "PLAYER_PRESENCE"
            assert msg["payload"]["player_id"] == "bob"
            assert msg["payload"]["state"] == "connected"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_presence_broadcast.py -v`
Expected: FAIL — no `PLAYER_PRESENCE` in protocol.

- [ ] **Step 3: Add protocol message**

In `sidequest-server/sidequest/protocol/messages.py`:

```python
class PlayerPresencePayload(BaseModel):
    player_id: str
    state: Literal["connected", "disconnected"]


class PlayerPresenceMessage(BaseModel):
    type: Literal["PLAYER_PRESENCE"] = "PLAYER_PRESENCE"
    payload: PlayerPresencePayload
```

Register it in the `GameMessage` union where other message types live (locate with `grep -n "SESSION_CONNECTED\|NARRATION" sidequest-server/sidequest/protocol/messages.py`).

- [ ] **Step 4: Fan-out via registry**

Add a per-slug broadcast helper. Simplest path: the `RoomRegistry` keeps a map `socket_id → asyncio.Queue` for outbound messages, and handlers append to every queue except their own when broadcasting. Extend `SessionRoom`:

```python
# In session_room.py
import asyncio

@dataclass
class SessionRoom:
    # ... existing fields ...
    _outbound_queues: Dict[str, asyncio.Queue] = field(default_factory=dict)

    def attach_outbound(self, socket_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            self._outbound_queues[socket_id] = queue

    def detach_outbound(self, socket_id: str) -> None:
        with self._lock:
            self._outbound_queues.pop(socket_id, None)

    def broadcast(self, msg, *, exclude_socket_id: str | None = None) -> None:
        with self._lock:
            targets = [(sid, q) for sid, q in self._outbound_queues.items() if sid != exclude_socket_id]
        for _sid, q in targets:
            q.put_nowait(msg)
```

In `websocket.py`, replace the single-loop `while True` with a reader task and a writer task that drains a per-socket queue:

```python
import asyncio

async def ws_endpoint(websocket, handler):
    await websocket.accept()
    socket_id = uuid.uuid4().hex
    registry = websocket.app.state.room_registry
    out_queue: asyncio.Queue = asyncio.Queue()
    handler.attach_room_context(registry=registry, socket_id=socket_id, out_queue=out_queue)

    async def writer():
        while True:
            msg = await out_queue.get()
            await _send_message(websocket, msg)

    writer_task = asyncio.create_task(writer())
    try:
        while True:
            raw = await websocket.receive_text()
            # ... existing parse + dispatch, but call out_queue.put_nowait for outbound
            msg = GameMessage.model_validate_json(raw)
            outbound = await handler.handle_message(msg)
            for m in outbound:
                out_queue.put_nowait(m)
    except WebSocketDisconnect:
        pass
    finally:
        writer_task.cancel()
        room = handler.current_room()
        if room is not None:
            room.detach_outbound(socket_id)
            left = room.disconnect(socket_id=socket_id)
            if left is not None:
                room.broadcast(_presence_msg(left, "disconnected"), exclude_socket_id=socket_id)
        await handler.cleanup()


def _presence_msg(player_id: str, state: str):
    from sidequest.protocol.messages import PlayerPresenceMessage, PlayerPresencePayload
    return PlayerPresenceMessage(payload=PlayerPresencePayload(player_id=player_id, state=state))
```

In `session_handler.py`, after successfully connecting into a room, attach the queue and broadcast the join:

```python
def attach_room_context(self, *, registry, socket_id: str, out_queue) -> None:
    self._room_registry = registry
    self._socket_id = socket_id
    self._out_queue = out_queue

# After room.connect(...) succeeds:
self._room.attach_outbound(self._socket_id, self._out_queue)
self._room.broadcast(
    _presence_msg(player_id, "connected"),
    exclude_socket_id=self._socket_id,
)
```

- [ ] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_presence_broadcast.py tests/server/test_session_room.py tests/server/test_session_room_wired.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/sidequest/server/websocket.py sidequest-server/sidequest/server/session_handler.py sidequest-server/sidequest/server/session_room.py sidequest-server/tests/server/test_presence_broadcast.py
git commit -m "feat(ws): PLAYER_PRESENCE broadcast on connect/disconnect + per-socket write queue"
```

---

### Task 5: Seat claim — PLAYER_SEAT message

**Files:**
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_seat_claim.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_seat_claim.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import SqliteStore, db_path_for_slug, upsert_game, GameMode


def _seed(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")


def test_claim_seat_updates_room(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                      "payload": {"event": "connect", "game_slug": slug}})
        ws.receive_json()  # SESSION_CONNECTED
        ws.send_json({"type": "PLAYER_SEAT", "player_id": "alice",
                      "payload": {"character_slot": "rux"}})
        resp = ws.receive_json()
        assert resp["type"] == "SEAT_CONFIRMED"
        room = app.state.room_registry.get(slug)
        assert "alice" in room.seated_player_ids()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_seat_claim.py -v`
Expected: FAIL — no PLAYER_SEAT type.

- [ ] **Step 3: Add protocol + handler**

In `messages.py`:

```python
class PlayerSeatPayload(BaseModel):
    character_slot: str


class PlayerSeatMessage(BaseModel):
    type: Literal["PLAYER_SEAT"] = "PLAYER_SEAT"
    player_id: str
    payload: PlayerSeatPayload


class SeatConfirmedPayload(BaseModel):
    player_id: str
    character_slot: str


class SeatConfirmedMessage(BaseModel):
    type: Literal["SEAT_CONFIRMED"] = "SEAT_CONFIRMED"
    payload: SeatConfirmedPayload
```

In `session_handler.py`, in `handle_message`:

```python
if msg.type == "PLAYER_SEAT":
    self._room.seat(msg.player_id, character_slot=msg.payload.character_slot)
    confirmed = SeatConfirmedMessage(payload=SeatConfirmedPayload(
        player_id=msg.player_id, character_slot=msg.payload.character_slot,
    ))
    self._room.broadcast(confirmed, exclude_socket_id=None)  # everyone sees it
    return []  # broadcast handles fan-out; no direct return needed
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_seat_claim.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_seat_claim.py
git commit -m "feat(ws): PLAYER_SEAT + SEAT_CONFIRMED for character slot claim"
```

---

### Task 6: Pause narrator when any seated player is absent

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Test: `sidequest-server/tests/server/test_pause_on_drop.py`

- [ ] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_pause_on_drop.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import SqliteStore, db_path_for_slug, upsert_game, GameMode


def _seed(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")


def test_player_action_during_paused_state_is_queued_not_dispatched(tmp_path: Path, monkeypatch):
    slug = "2026-04-22-moldharrow-keep"
    _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    # Stub narrator to record calls
    calls = []

    from sidequest.server import session_handler as sh
    original_dispatch = sh.WebSocketSessionHandler._dispatch_to_narrator
    async def recording_dispatch(self, *a, **kw):
        calls.append(a)
        return await original_dispatch(self, *a, **kw)
    monkeypatch.setattr(sh.WebSocketSessionHandler, "_dispatch_to_narrator", recording_dispatch)

    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        ws_a.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                        "payload": {"event": "connect", "game_slug": slug}})
        ws_a.receive_json()
        ws_a.send_json({"type": "PLAYER_SEAT", "player_id": "alice",
                        "payload": {"character_slot": "rux"}})
        ws_a.receive_json()
        # Seat a second player (via a second connection) then drop them
        with client.websocket_connect("/ws") as ws_b:
            ws_b.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                            "payload": {"event": "connect", "game_slug": slug}})
            ws_b.receive_json()
            ws_b.send_json({"type": "PLAYER_SEAT", "player_id": "bob",
                            "payload": {"character_slot": "vex"}})
            ws_b.receive_json()
        # bob disconnected — now the room has a seated-but-absent player
        # alice tries to act; narrator must NOT be dispatched
        ws_a.receive_json()  # drain presence event
        ws_a.send_json({"type": "PLAYER_ACTION", "player_id": "alice",
                        "payload": {"text": "I draw my sword"}})
        resp = ws_a.receive_json()
        assert resp["type"] == "GAME_PAUSED"
        assert "bob" in resp["payload"]["waiting_for"]
        assert len(calls) == 0
```

- [ ] **Step 2: Run — expect failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_pause_on_drop.py -v`
Expected: FAIL — narrator dispatches anyway, no GAME_PAUSED.

- [ ] **Step 3: Add GAME_PAUSED protocol + gate**

In `messages.py`:

```python
class GamePausedPayload(BaseModel):
    waiting_for: list[str]


class GamePausedMessage(BaseModel):
    type: Literal["GAME_PAUSED"] = "GAME_PAUSED"
    payload: GamePausedPayload


class GameResumedMessage(BaseModel):
    type: Literal["GAME_RESUMED"] = "GAME_RESUMED"
    payload: dict = {}
```

In `session_handler.py`, gate PLAYER_ACTION:

```python
if msg.type == "PLAYER_ACTION":
    if self._room is not None and self._room.is_paused():
        absent = self._room.absent_seated_player_ids()
        return [GamePausedMessage(payload=GamePausedPayload(waiting_for=absent))]
    # ... existing dispatch to narrator
```

And in the disconnect path (in websocket.py), after broadcasting disconnect presence, also broadcast GAME_PAUSED if the room is now paused; on reconnect (in session_handler after successful room.connect), if the room is no longer paused, broadcast GAME_RESUMED.

```python
# In websocket.py finally block, after room.disconnect + presence broadcast:
if room.is_paused():
    room.broadcast(GamePausedMessage(payload=GamePausedPayload(
        waiting_for=room.absent_seated_player_ids()
    )), exclude_socket_id=None)

# In session_handler.py slug-connect branch, after room.connect succeeds:
if not self._room.is_paused():
    # This connect may have resolved a pause
    self._room.broadcast(GameResumedMessage(), exclude_socket_id=None)
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_pause_on_drop.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/messages.py sidequest-server/sidequest/server/session_handler.py sidequest-server/sidequest/server/websocket.py sidequest-server/tests/server/test_pause_on_drop.py
git commit -m "feat(ws): pause narrator when any seated player is absent"
```

---

### Task 7: UI — display name cookie + attach to connect

**Files:**
- Create: `sidequest-ui/src/hooks/useDisplayName.ts`
- Test: `sidequest-ui/src/hooks/__tests__/useDisplayName.test.ts`

- [ ] **Step 1: Write failing test**

```ts
// sidequest-ui/src/hooks/__tests__/useDisplayName.test.ts
import { act, renderHook } from '@testing-library/react';
import { useDisplayName } from '../useDisplayName';

describe('useDisplayName', () => {
  beforeEach(() => { localStorage.clear(); });

  it('returns null when unset', () => {
    const { result } = renderHook(() => useDisplayName());
    expect(result.current.name).toBeNull();
  });

  it('persists name to localStorage', () => {
    const { result } = renderHook(() => useDisplayName());
    act(() => result.current.setName('alice'));
    expect(localStorage.getItem('sq:display-name')).toBe('alice');
    expect(result.current.name).toBe('alice');
  });

  it('restores name on rerender', () => {
    localStorage.setItem('sq:display-name', 'bob');
    const { result } = renderHook(() => useDisplayName());
    expect(result.current.name).toBe('bob');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useDisplayName.test.ts`
Expected: file-not-found.

- [ ] **Step 3: Implement**

```ts
// sidequest-ui/src/hooks/useDisplayName.ts
import { useCallback, useState } from 'react';

const KEY = 'sq:display-name';

export function useDisplayName() {
  const [name, setState] = useState<string | null>(() => localStorage.getItem(KEY));
  const setName = useCallback((n: string) => {
    localStorage.setItem(KEY, n);
    setState(n);
  }, []);
  return { name, setName };
}
```

- [ ] **Step 4: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useDisplayName.test.ts`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/hooks/useDisplayName.ts sidequest-ui/src/hooks/__tests__/useDisplayName.test.ts
git commit -m "feat(ui): useDisplayName hook with localStorage persistence"
```

---

### Task 8: UI — PausedBanner + wire into GameScreen

**Files:**
- Create: `sidequest-ui/src/components/PausedBanner.tsx`
- Test: `sidequest-ui/src/components/__tests__/PausedBanner.test.tsx`
- Modify: `sidequest-ui/src/screens/GameScreen.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/components/__tests__/PausedBanner.test.tsx
import { render, screen } from '@testing-library/react';
import { PausedBanner } from '../PausedBanner';

describe('PausedBanner', () => {
  it('renders nothing when not paused', () => {
    const { container } = render(<PausedBanner paused={false} waitingFor={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('lists waitingFor when paused', () => {
    render(<PausedBanner paused={true} waitingFor={['bob', 'carol']} />);
    expect(screen.getByRole('status')).toHaveTextContent(/bob/);
    expect(screen.getByRole('status')).toHaveTextContent(/carol/);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/components/__tests__/PausedBanner.test.tsx`
Expected: file-not-found.

- [ ] **Step 3: Implement**

```tsx
// sidequest-ui/src/components/PausedBanner.tsx
export function PausedBanner({ paused, waitingFor }: { paused: boolean; waitingFor: string[] }) {
  if (!paused) return null;
  return (
    <div role="status" aria-live="polite">
      Paused — waiting for {waitingFor.join(', ')}
    </div>
  );
}
```

- [ ] **Step 4: Wire into GameScreen**

In `sidequest-ui/src/screens/GameScreen.tsx`, extend it to consume the WS stream (use existing useStateMirror hook pattern) and track paused state:

```tsx
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDisplayName } from '../hooks/useDisplayName';
import { PausedBanner } from '../components/PausedBanner';

export function GameScreen({ mode }: { mode: 'solo' | 'multiplayer' }) {
  const { slug = '' } = useParams<{ slug: string }>();
  const { name } = useDisplayName();
  const [paused, setPaused] = useState(false);
  const [waitingFor, setWaitingFor] = useState<string[]>([]);

  useEffect(() => {
    if (!name) return;  // name required before connecting
    const ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => ws.send(JSON.stringify({
      type: 'SESSION_EVENT',
      player_id: name,
      payload: { event: 'connect', game_slug: slug },
    }));
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type === 'GAME_PAUSED') { setPaused(true); setWaitingFor(m.payload.waiting_for); }
      if (m.type === 'GAME_RESUMED') { setPaused(false); setWaitingFor([]); }
    };
    return () => ws.close();
  }, [name, slug]);

  if (!name) {
    return <NamePrompt />;  // simple input that calls setName from useDisplayName
  }

  return (
    <div data-testid="game-screen" data-mode={mode} data-slug={slug}>
      <PausedBanner paused={paused} waitingFor={waitingFor} />
      {/* ... rest of existing game UI */}
    </div>
  );
}

function NamePrompt() {
  const { setName } = useDisplayName();
  const [v, setV] = useState('');
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (v.trim()) setName(v.trim()); }}>
      <label>Your name: <input value={v} onChange={(e) => setV(e.target.value)} /></label>
      <button type="submit">Join</button>
    </form>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/components/__tests__/PausedBanner.test.tsx`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add sidequest-ui/src/components/PausedBanner.tsx sidequest-ui/src/components/__tests__/PausedBanner.test.tsx sidequest-ui/src/screens/GameScreen.tsx
git commit -m "feat(ui): PausedBanner + name prompt + WebSocket connect in GameScreen"
```

---

### Task 9: End-to-end wiring test — two clients, drop, pause, reconnect, resume

**Files:**
- Create: `sidequest-server/tests/server/test_party_wiring.py`

- [ ] **Step 1: Write the test**

```python
# sidequest-server/tests/server/test_party_wiring.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import SqliteStore, db_path_for_slug, upsert_game, GameMode


def _seed(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")


def test_drop_pauses_reconnect_resumes(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)

    with client.websocket_connect("/ws") as ws_a:
        ws_a.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                        "payload": {"event": "connect", "game_slug": slug}})
        ws_a.receive_json()
        ws_a.send_json({"type": "PLAYER_SEAT", "player_id": "alice",
                        "payload": {"character_slot": "rux"}})
        ws_a.receive_json()

        with client.websocket_connect("/ws") as ws_b:
            ws_b.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                            "payload": {"event": "connect", "game_slug": slug}})
            ws_b.receive_json()
            ws_b.send_json({"type": "PLAYER_SEAT", "player_id": "bob",
                            "payload": {"character_slot": "vex"}})
            ws_b.receive_json()
        # ws_b closed → pause expected

        saw_pause = False
        for _ in range(5):
            m = ws_a.receive_json()
            if m["type"] == "GAME_PAUSED":
                saw_pause = True
                break
        assert saw_pause

        with client.websocket_connect("/ws") as ws_b2:
            ws_b2.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                             "payload": {"event": "connect", "game_slug": slug}})
            ws_b2.receive_json()

            saw_resume = False
            for _ in range(5):
                m = ws_a.receive_json()
                if m["type"] == "GAME_RESUMED":
                    saw_resume = True
                    break
            assert saw_resume
```

- [ ] **Step 2: Run — should pass from Tasks 4+6**

Run: `cd sidequest-server && uv run pytest tests/server/test_party_wiring.py -v`
Expected: 1 passed. If GAME_RESUMED doesn't fire, the reconnect-side broadcast in Task 6 isn't wired — fix it there.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_party_wiring.py
git commit -m "test(wiring): drop→pause→reconnect→resume end-to-end"
```

---

## Plan 02 Self-Review

Spec sections covered:
- Open join anytime → **Tasks 2, 4** (any WS connect with a known slug succeeds)
- Drop-out = pause narrator → **Task 6, 9**
- Solo URL single-slot → **Tasks 1, 3**
- Display name + cookie identity → **Task 7, 8**
- Seat claim for late joiners → **Task 5**

**Still deferred to Plan 03:** asymmetric-info filtered event streams, reconnect catch-up via last_seen_seq, peer save as projection cache, read-only mode when narrator-host unreachable.

**Known shortcut:** The `_dispatch_to_narrator` method referenced in Task 6's test must exist on `WebSocketSessionHandler`. If the current session_handler calls the narrator inline without a named method, extract it first as a prep step inside Task 6 so the monkeypatch target exists — this is a real refactor, not fake, because it's needed for the pause gate to wrap it cleanly.
