# 67-6 Authenticated Player Identity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate authenticated player identity (Cloudflare Access email) from the seated-character name, so PARTY_STATUS and the UI header stop fabricating peer identity from the character name.

**Architecture:** Add a pure `resolve_player_identity(headers)` resolver (Cf-Access email → Host → raise). Resolve once per socket at the WS boundary, stash on the handler, and bind to `player_id` in the connect handler by writing a room-only `SessionRoom.player_identities` dict. Repoint the one perspective call-site that abused `sd.player_name` to an explicit seat accessor, and carry a nullable `player_identity` field through PARTY_STATUS to the UI. Identity is never persisted to saves; no email/PII in telemetry.

**Tech Stack:** Python 3 / FastAPI / Starlette WebSocket, pydantic v2 (`ProtocolBase`), pytest (+ pytest-xdist, Postgres test fixtures), OpenTelemetry watcher events, React/TypeScript (Vitest) for the UI.

**Spec:** `docs/superpowers/specs/2026-05-31-67-6-player-identity-design.md`

**Repo paths:** server = `sidequest-server/`, ui = `sidequest-ui/`. Run server tests from `sidequest-server/` with `uv run pytest`. Server branch targets `develop` (gitflow, `feat/67-6-player-identity`). Commit after every task.

---

## File Structure

**Create:**
- `sidequest-server/sidequest/server/player_identity.py` — pure resolver + `MissingPlayerIdentityError` + `identity_source`.
- `sidequest-server/tests/server/test_player_identity.py` — resolver pinning tests.
- `sidequest-server/tests/server/test_player_identity_wiring.py` — WS-boundary + room-store + PARTY_STATUS behavior/wiring tests.
- `docs/adr/119-authenticated-player-identity.md` — ADR under the ADR-037 umbrella.

**Modify:**
- `sidequest-server/sidequest/server/session_room.py:147-213` — add `player_identities` field + set/clear in connect/disconnect.
- `sidequest-server/sidequest/server/websocket.py:44-58` — resolve identity at the boundary, fail-loud close, stash on handler.
- `sidequest-server/sidequest/server/websocket_session_handler.py` — `attach_room_context` gains identity params; add `perspective_character_name`; repoint line ~2570.
- `sidequest-server/sidequest/handlers/connect.py:303-360` — bind identity to `player_id` in the room; emit watcher event.
- `sidequest-server/sidequest/protocol/models.py:430-478` — add `player_identity` to `PartyMember`.
- `sidequest-server/sidequest/server/views.py:573-639` — thread identity into PARTY_STATUS (self + peer), kill char-name fabrication.
- `sidequest-ui/src/types/payloads.ts:51-66` — add `player_identity?` to `PartyMemberPayload`.
- `sidequest-ui/src/components/CharacterPanel.tsx:247-259` — render suffix from `player_identity`.

---

## Task 1: Pure identity resolver

**Files:**
- Create: `sidequest-server/sidequest/server/player_identity.py`
- Test: `sidequest-server/tests/server/test_player_identity.py`

- [ ] **Step 1: Write the failing tests**

```python
# sidequest-server/tests/server/test_player_identity.py
"""Pinning tests for resolve_player_identity (Story 67-6, ADR-119).

Resolution order: Cf-Access-Authenticated-User-Email (non-blank,
case-insensitive) -> Host header -> raise. No silent default.
"""
import pytest

from sidequest.server.player_identity import (
    MissingPlayerIdentityError,
    identity_source,
    resolve_player_identity,
)

CF = "cf-access-authenticated-user-email"


def test_cf_access_email_wins():
    assert resolve_player_identity({CF: "alice@example.com", "host": "p1.local"}) == "alice@example.com"


def test_cf_access_header_is_case_insensitive():
    headers = {"Cf-Access-Authenticated-User-Email": "bob@example.com"}
    assert resolve_player_identity(headers) == "bob@example.com"


def test_blank_cf_access_falls_through_to_host():
    assert resolve_player_identity({CF: "   ", "host": "player1.local"}) == "player1.local"


def test_missing_cf_access_falls_through_to_host():
    assert resolve_player_identity({"host": "player2.local"}) == "player2.local"


def test_host_is_trimmed():
    assert resolve_player_identity({"host": "  player1.local  "}) == "player1.local"


def test_raises_when_neither_present():
    with pytest.raises(MissingPlayerIdentityError):
        resolve_player_identity({})


def test_raises_when_both_blank():
    with pytest.raises(MissingPlayerIdentityError):
        resolve_player_identity({CF: "", "host": "   "})


def test_identity_source_reports_cf_access():
    assert identity_source({CF: "alice@example.com", "host": "p1.local"}) == "cf_access"


def test_identity_source_reports_host_when_email_blank():
    assert identity_source({CF: "  ", "host": "player1.local"}) == "host"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.server.player_identity'`

- [ ] **Step 3: Write the resolver**

```python
# sidequest-server/sidequest/server/player_identity.py
"""Authenticated player identity resolution (Story 67-6, ADR-119).

The app sits behind Cloudflare Zero Trust, which injects the authenticated
user's email as ``Cf-Access-Authenticated-User-Email``. Local dev distinguishes
players by per-player Host names (player1.local, player2.local). Identity is the
*human*, distinct from the seated character name (snapshot.player_seats).

No silent fallback: if neither header yields a non-blank value, raise.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

CF_ACCESS_EMAIL_HEADER = "cf-access-authenticated-user-email"
HOST_HEADER = "host"


class MissingPlayerIdentityError(Exception):
    """No player identity could be resolved from request headers."""


def _lowered(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(k).lower(): v for k, v in headers.items()}


def resolve_player_identity(headers: Mapping[str, str]) -> str:
    """Resolve the authenticated player identity. Cf-Access email -> Host -> raise."""
    lowered = _lowered(headers)
    email = (lowered.get(CF_ACCESS_EMAIL_HEADER) or "").strip()
    if email:
        return email
    host = (lowered.get(HOST_HEADER) or "").strip()
    if host:
        return host
    raise MissingPlayerIdentityError(
        "No player identity: neither Cf-Access-Authenticated-User-Email nor Host header present"
    )


def identity_source(headers: Mapping[str, str]) -> Literal["cf_access", "host"]:
    """Which header the resolved identity came from (for OTEL; never the value)."""
    lowered = _lowered(headers)
    if (lowered.get(CF_ACCESS_EMAIL_HEADER) or "").strip():
        return "cf_access"
    return "host"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Lint + commit**

```bash
cd sidequest-server && uv run ruff check sidequest/server/player_identity.py tests/server/test_player_identity.py
git add sidequest/server/player_identity.py tests/server/test_player_identity.py
git commit -m "feat(67-6): pure resolve_player_identity resolver + pinning tests"
```

---

## Task 2: `SessionRoom.player_identities` store + lifecycle

**Files:**
- Modify: `sidequest-server/sidequest/server/session_room.py:147-213` (field), connect/disconnect methods
- Test: `sidequest-server/tests/server/test_player_identity_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/server/test_player_identity_wiring.py
"""WS-boundary, room-store, and PARTY_STATUS wiring tests (Story 67-6)."""
from sidequest.server.session_room import SessionRoom
from sidequest.game.state import GameMode  # GameMode enum import path


def _room() -> SessionRoom:
    return SessionRoom(slug="s", mode=GameMode.SOLO)


def test_room_stores_and_clears_player_identity():
    room = _room()
    room.set_player_identity("p1", "alice@example.com")
    assert room.player_identities.get("p1") == "alice@example.com"
    room.clear_player_identity("p1")
    assert "p1" not in room.player_identities
```

> NOTE: confirm the `GameMode` import path and the `SessionRoom` constructor's required args by reading `session_room.py` top-of-file imports and the dataclass header; adjust `_room()` to match (the dataclass shows `slug: str`, `mode: GameMode`).

- [ ] **Step 2: Run it to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_room_stores_and_clears_player_identity -v`
Expected: FAIL — `AttributeError: 'SessionRoom' object has no attribute 'set_player_identity'`

- [ ] **Step 3: Add the field and helpers**

In `session_room.py`, add the field after `_seated` (around line 164):

```python
    # player_id -> resolved player identity (Cf-Access email or dev Host).
    # Room-only and ephemeral (Story 67-6, ADR-119): re-resolved every
    # connect, never persisted to the snapshot/save. PARTY_STATUS reads it
    # so peer identity is the human, not the character name.
    player_identities: dict[str, str] = field(default_factory=dict)
```

Add these methods to the class (near `connected_player_ids`, ~line 651), using the existing `self._lock`:

```python
    def set_player_identity(self, player_id: str, identity: str) -> None:
        with self._lock:
            self.player_identities[player_id] = identity

    def clear_player_identity(self, player_id: str) -> None:
        with self._lock:
            self.player_identities.pop(player_id, None)
```

- [ ] **Step 4: Run it to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_room_stores_and_clears_player_identity -v`
Expected: PASS

- [ ] **Step 5: Wire `clear_player_identity` into disconnect**

In `session_room.py` `disconnect()` (lines 466-540), after the player's last socket is removed (where presence is dropped because `_player_sockets[player_id]` becomes empty), add the clear. Find the branch that removes the player from `_connected` and add alongside it:

```python
            self.player_identities.pop(player_id, None)
```

(Place it inside the same `with self._lock:` block that already mutates `_connected`/`_player_sockets`, so it's covered by the existing lock — do not call `clear_player_identity` re-entrantly.)

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && uv run ruff check sidequest/server/session_room.py
git add sidequest/server/session_room.py tests/server/test_player_identity_wiring.py
git commit -m "feat(67-6): SessionRoom.player_identities room-only store + lifecycle"
```

---

## Task 3: Resolve at the WS boundary + thread to handler

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket.py:44-58`
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (`attach_room_context`)
- Test: `sidequest-server/tests/server/test_player_identity_wiring.py`

- [ ] **Step 1: Write the failing test (fail-loud close on missing identity)**

Append to `tests/server/test_player_identity_wiring.py`:

```python
import pytest
from starlette.websockets import WebSocketDisconnect


class _FakeWS:
    """Minimal WebSocket double: headers + accept/close recording."""
    def __init__(self, headers: dict[str, str]):
        self.headers = headers
        self.accepted = False
        self.closed_code: int | None = None

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000) -> None:
        self.closed_code = code


@pytest.mark.asyncio
async def test_ws_boundary_closes_when_identity_unresolvable(monkeypatch):
    from sidequest.server import websocket as ws_mod

    ws = _FakeWS(headers={})  # no Cf-Access, no Host -> unresolvable
    handler = object()  # not reached; close happens before handler use

    await ws_mod.resolve_identity_or_close(ws)  # helper under test

    assert ws.accepted is False
    assert ws.closed_code == 1008  # policy violation
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_ws_boundary_closes_when_identity_unresolvable -v`
Expected: FAIL — `AttributeError: module 'sidequest.server.websocket' has no attribute 'resolve_identity_or_close'`

- [ ] **Step 3: Add the boundary helper and call it in `ws_endpoint`**

In `websocket.py`, add imports at the top:

```python
from sidequest.server.player_identity import (
    MissingPlayerIdentityError,
    identity_source,
    resolve_player_identity,
)
```

Add the helper (returns `(identity, source)` or closes and returns `None`):

```python
async def resolve_identity_or_close(websocket) -> tuple[str, str] | None:
    """Resolve the authenticated player identity from WS headers before accept.

    Fail-loud (No Silent Fallbacks): a connection with no resolvable identity is
    a misconfiguration, not a guest. Close 1008 (policy violation) and return None.
    """
    try:
        identity = resolve_player_identity(websocket.headers)
    except MissingPlayerIdentityError:
        logger.error(
            "ws.identity_unresolved remote=%s — closing (no Cf-Access email or Host header)",
            getattr(websocket, "client", None),
        )
        await websocket.close(code=1008)
        return None
    return identity, identity_source(websocket.headers)
```

Modify `ws_endpoint` so resolution happens **before** `accept()`:

```python
async def ws_endpoint(websocket: WebSocket, handler: WebSocketSessionHandler) -> None:
    """WebSocket connection lifecycle — resolve identity, accept, loop, cleanup."""
    resolved = await resolve_identity_or_close(websocket)
    if resolved is None:
        return
    player_identity, player_identity_source = resolved
    await websocket.accept()
    socket_id = uuid.uuid4().hex
    registry = websocket.app.state.room_registry
    out_queue: asyncio.Queue[Any] = asyncio.Queue()
    handler.attach_room_context(
        registry=registry,
        socket_id=socket_id,
        out_queue=out_queue,
        player_identity=player_identity,
        player_identity_source=player_identity_source,
    )
    logger.info("ws.connection_accepted remote=%s socket=%s", websocket.client, socket_id)
```

- [ ] **Step 4: Extend `attach_room_context` to store identity on the handler**

In `websocket_session_handler.py`, find `def attach_room_context(self, *, registry, socket_id, out_queue)` and add the two keyword params with defaults (so existing test callers that omit them still work), storing them on the instance:

```python
    def attach_room_context(
        self,
        *,
        registry,
        socket_id,
        out_queue,
        player_identity: str | None = None,
        player_identity_source: str | None = None,
    ) -> None:
        # ... existing body unchanged ...
        self._player_identity = player_identity
        self._player_identity_source = player_identity_source
```

Also initialize the attributes in `__init__` (or alongside the other `_socket_id`/`_room` attributes) so they always exist:

```python
        self._player_identity: str | None = None
        self._player_identity_source: str | None = None
```

- [ ] **Step 5: Run the boundary test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_ws_boundary_closes_when_identity_unresolvable -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd sidequest-server && uv run ruff check sidequest/server/websocket.py sidequest/server/websocket_session_handler.py
git add sidequest/server/websocket.py sidequest/server/websocket_session_handler.py tests/server/test_player_identity_wiring.py
git commit -m "feat(67-6): resolve player identity at WS boundary, fail-loud close, stash on handler"
```

---

## Task 4: Bind identity to player_id in connect + OTEL watcher event

**Files:**
- Modify: `sidequest-server/sidequest/handlers/connect.py:303-360`
- Test: `sidequest-server/tests/server/test_player_identity_wiring.py`

- [ ] **Step 1: Write the failing test (binding writes the room store)**

Append to `tests/server/test_player_identity_wiring.py`:

```python
def test_bind_player_identity_writes_room_store_and_skips_blank():
    from sidequest.handlers.connect import bind_player_identity

    room = _room()
    # identity present -> stored
    bind_player_identity(room, player_id="p1", identity="alice@example.com", source="cf_access")
    assert room.player_identities.get("p1") == "alice@example.com"
    # identity absent -> no entry, no crash
    bind_player_identity(room, player_id="p2", identity=None, source=None)
    assert "p2" not in room.player_identities
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_bind_player_identity_writes_room_store_and_skips_blank -v`
Expected: FAIL — `ImportError: cannot import name 'bind_player_identity'`

- [ ] **Step 3: Add `bind_player_identity` and call it from the slug-connect branch**

In `connect.py`, add the import for the watcher near the existing `_watcher_publish` usage (it is already used at lines 387-397, so the symbol is in scope) and add this module-level function:

```python
def bind_player_identity(
    room,
    *,
    player_id: str,
    identity: str | None,
    source: str | None,
) -> None:
    """Bind the per-socket resolved identity to player_id in the room (Story 67-6).

    Room-only and ephemeral. Emits a watcher event carrying the SOURCE only —
    never the identity value (no PII in telemetry).
    """
    if not identity:
        return
    room.set_player_identity(player_id, identity)
    _watcher_publish(
        "player_identity_resolved",
        {"player_id": player_id, "source": source or "unknown"},
        component="session",
        severity="info",
    )
```

In `ConnectHandler.handle`, inside the slug-connect branch where `snapshot.player_seats[player_id] = display_name` is set (line 556 area) and the room is in scope, add:

```python
            bind_player_identity(
                room,
                player_id=player_id,
                identity=getattr(session, "_player_identity", None),
                source=getattr(session, "_player_identity_source", None),
            )
```

> Confirm the local variable name for the room in that branch (the handler reaches it via the registry / `session._room`). Use whatever the surrounding code already calls it; if it is `session._room`, pass that.

- [ ] **Step 4: Run it to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_bind_player_identity_writes_room_store_and_skips_blank -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && uv run ruff check sidequest/handlers/connect.py
git add sidequest/handlers/connect.py tests/server/test_player_identity_wiring.py
git commit -m "feat(67-6): bind player identity to player_id in connect + player_identity_resolved watcher event"
```

---

## Task 5: `perspective_character_name` accessor + repoint wssh:2570

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py` (add accessor; repoint line ~2570)
- Test: `sidequest-server/tests/server/test_player_identity_wiring.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/server/test_player_identity_wiring.py`:

```python
def test_perspective_character_name_uses_seat_then_falls_back():
    from sidequest.server.websocket_session_handler import perspective_character_name

    class _Snap:
        def __init__(self, seats):
            self.player_seats = seats

    class _SD:
        def __init__(self, pid, pname, seats):
            self.player_id = pid
            self.player_name = pname
            self.snapshot = _Snap(seats)

    # seated -> returns the seated character name
    sd = _SD("p1", "DISPLAY", {"p1": "Rux"})
    assert perspective_character_name(sd) == "Rux"
    # unseated -> falls back to sd.player_name (behavior-preserving for pre-seat)
    sd2 = _SD("p2", "Laverne", {})
    assert perspective_character_name(sd2) == "Laverne"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_perspective_character_name_uses_seat_then_falls_back -v`
Expected: FAIL — `ImportError: cannot import name 'perspective_character_name'`

- [ ] **Step 3: Add the accessor and repoint the call-site**

In `websocket_session_handler.py`, add this module-level function (near the top, after imports):

```python
def perspective_character_name(sd) -> str:
    """The seated character name to use as a party_location perspective key.

    Story 67-6: the POV key is the seated CHARACTER, resolved from
    snapshot.player_seats[player_id] — never the player identity. Falls back to
    sd.player_name (which is itself the character name pre-seat) when no seat is
    bound yet, preserving prior behavior.
    """
    return sd.snapshot.player_seats.get(sd.player_id, sd.player_name)
```

Repoint line ~2570. Change:

```python
            else sd.snapshot.party_location(perspective=sd.player_name)
```

to:

```python
            else sd.snapshot.party_location(perspective=perspective_character_name(sd))
```

- [ ] **Step 4: Run the new test + the existing wssh suite to verify no POV regression**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_perspective_character_name_uses_seat_then_falls_back -v`
Expected: PASS

Run the broader handler/perception suite to confirm no regression:
Run: `cd sidequest-server && uv run pytest tests/server -k "perspective or party_location or perception or location" -v`
Expected: PASS (no new failures vs. baseline)

- [ ] **Step 5: Commit**

```bash
cd sidequest-server && uv run ruff check sidequest/server/websocket_session_handler.py
git add sidequest/server/websocket_session_handler.py tests/server/test_player_identity_wiring.py
git commit -m "feat(67-6): perspective_character_name accessor; repoint sd.player_name perspective abuse"
```

---

## Task 6: PARTY_STATUS dual-field (protocol + views)

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py:430-478` (`PartyMember`)
- Modify: `sidequest-server/sidequest/server/views.py:573-639` (`build_session_start_party_status`, `party_member_from_character`)
- Test: `sidequest-server/tests/server/test_player_identity_wiring.py`

- [ ] **Step 1: Write the failing behavior test**

Append to `tests/server/test_player_identity_wiring.py`:

```python
def test_party_member_identity_present_for_connected_absent_for_disconnected():
    """Self carries identity from the room; a disconnected peer carries None
    and is NEVER given the character name as a fabricated identity."""
    from sidequest.protocol.models import PartyMember

    # The room knows p1's identity (connected) but not peer:Rux (disconnected).
    identities = {"p1": "alice@example.com"}

    def lookup(pid: str) -> str | None:
        return identities.get(pid)

    self_member = PartyMember(
        player_id="p1", name="Laverne", player_identity=lookup("p1"),
        character_name="Laverne", current_hp=10, max_hp=10,
        survivability_pool_label=None, statuses=[], **{"class": "Fighter"},
        level=1,
    )
    peer_member = PartyMember(
        player_id="peer:Rux", name="Rux", player_identity=lookup("peer:Rux"),
        character_name="Rux", current_hp=10, max_hp=10,
        survivability_pool_label=None, statuses=[], **{"class": "Mage"},
        level=1,
    )
    assert self_member.player_identity == "alice@example.com"
    assert peer_member.player_identity is None
    assert peer_member.player_identity != peer_member.character_name
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_party_member_identity_present_for_connected_absent_for_disconnected -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'player_identity'` (the `PartyMember` field does not exist yet).

- [ ] **Step 3: Add the protocol field**

In `models.py`, inside `class PartyMember(ProtocolBase)`, add after `name` (around line 439):

```python
    player_identity: str | None = None
    """Resolved player identity (Cf-Access email / dev Host). None when the player
    is not currently connected (room-only store). Story 67-6 / ADR-119."""
```

- [ ] **Step 4: Thread identity through the views builder**

In `views.py` `party_member_from_character` (the helper called at line 608), add a `player_identity: str | None = None` parameter and pass it into the `PartyMember(...)` construction as `player_identity=player_identity`.

In `build_session_start_party_status`, resolve identity from the room per member and pass it down. Replace the self/peer loop body (lines ~600-608):

```python
    room = handler._room
    id_map: dict[str, str] = dict(getattr(room, "player_identities", {})) if room is not None else {}
    for char in self_chars + peer_chars:
        is_self = char.core.name == character.core.name
        if is_self:
            pid = player_id or "anon"
            pname = sd.player_name or "Player"
        else:
            pid = seat_map.get(char.core.name) or f"peer:{char.core.name}"
            pname = char.core.name
        members.append(
            party_member_from_character(
                handler, sd, char, pid, pname,
                player_identity=id_map.get(pid),
            )
        )
```

This sets `player_identity` from the room store keyed by the member's `pid`; a disconnected peer (not in `player_identities`) gets `None`. The character-name value still flows into `character_name`/`pname` as before — it is no longer reused as identity.

- [ ] **Step 5: Run the behavior test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py::test_party_member_identity_present_for_connected_absent_for_disconnected -v`
Expected: PASS

- [ ] **Step 6: Run the full identity wiring file + party-status suite**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity_wiring.py tests/server -k "party_status or PARTY_STATUS" -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd sidequest-server && uv run ruff check sidequest/protocol/models.py sidequest/server/views.py
git add sidequest/protocol/models.py sidequest/server/views.py tests/server/test_player_identity_wiring.py
git commit -m "feat(67-6): PARTY_STATUS carries nullable player_identity; stop fabricating peer identity from character name"
```

---

## Task 7: UI — payload type + CharacterPanel render

**Files:**
- Modify: `sidequest-ui/src/types/payloads.ts:51-66`
- Modify: `sidequest-ui/src/components/CharacterPanel.tsx:247-259`
- Test: `sidequest-ui/src/components/__tests__/CharacterPanel.test.tsx` (create or extend the nearest existing CharacterPanel test)

- [ ] **Step 1: Add the payload field**

In `payloads.ts`, inside `interface PartyMemberPayload`, add after `name` (line ~53):

```typescript
  player_identity?: string;
```

- [ ] **Step 2: Write the failing UI test**

Create/extend `sidequest-ui/src/components/__tests__/CharacterPanel.test.tsx`. First inspect an existing component test in `sidequest-ui/src/**/__tests__/` to mirror the render/import harness, then add:

```typescript
import { render, screen } from "@testing-library/react";
import { CharacterPanel } from "../CharacterPanel";

// Build the minimal props CharacterPanel needs; mirror an existing test's fixture.
function renderWithIdentity(identity?: string) {
  const character = {
    name: "Laverne",
    player_id: "p1",
    player_identity: identity,
    // ...spread the other required fields from an existing fixture...
  } as any;
  return render(<CharacterPanel character={character} characters={[character, { name: "Rux" } as any]} />);
}

test("renders player_identity suffix when present", () => {
  renderWithIdentity("alice@example.com");
  expect(screen.getByTestId("character-panel-player-name").textContent).toContain("alice@example.com");
});

test("renders no fabricated suffix when identity absent and id equals name", () => {
  const character = { name: "Rux", player_id: "Rux", player_identity: undefined } as any;
  render(<CharacterPanel character={character} characters={[character]} />);
  expect(screen.queryByTestId("character-panel-player-name")).toBeNull();
});
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/CharacterPanel.test.tsx`
Expected: FAIL — suffix shows `player_id`, not `player_identity`.

- [ ] **Step 4: Render the suffix from `player_identity`**

In `CharacterPanel.tsx` (lines 247-259), change the suffix source to prefer `player_identity`, falling back to `player_id`, and only render when it differs from the character name:

```typescript
{(() => {
  const suffix = character.player_identity || character.player_id;
  const show = suffix && suffix !== character.name && characters && characters.length > 1;
  return show ? (
    <span
      data-testid="character-panel-player-name"
      className="ml-2 text-xs font-normal"
      style={{ fontFamily: FONT_BODY, color: FOLIO.inkSoft, letterSpacing: 0 }}
    >
      — {suffix}
    </span>
  ) : null;
})()}
```

- [ ] **Step 5: Run it to verify it passes**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/CharacterPanel.test.tsx`
Expected: PASS

- [ ] **Step 6: Lint + commit**

```bash
cd sidequest-ui && npx eslint src/types/payloads.ts src/components/CharacterPanel.tsx
git add src/types/payloads.ts src/components/CharacterPanel.tsx src/components/__tests__/CharacterPanel.test.tsx
git commit -m "feat(67-6): UI party_identity field; render player-identity suffix, no fabricated peer name"
```

---

## Task 8: ADR-119

**Files:**
- Create: `docs/adr/119-authenticated-player-identity.md`

- [ ] **Step 1: Write the ADR**

Mirror the frontmatter schema of a recent accepted ADR (read `docs/adr/117-pluggable-ruleset-module-system.md` for the exact frontmatter keys — ADR-088 governs the schema). Then write:

```markdown
# ADR-119: Authenticated Player Identity via Cloudflare Access + Player-vs-Character Identity Split

## Status
Accepted

## Context
Player display identity was derived from a user-typed `payload.player_name`, which in MP equals the character name — so `_SessionData.player_name` was overloaded as both display identity and the seated-character POV key. PARTY_STATUS fabricated peer identity as `char.core.name`, producing the doubled "X — X" header (67-4 patched the symptom in the UI). The app sits behind Cloudflare Zero Trust (`app.py`), which injects `Cf-Access-Authenticated-User-Email`, but it was never read.

## Decision
Separate three concepts: `player_id` (per-socket key), **player_identity** (authenticated email, resolved `Cf-Access-Authenticated-User-Email` → `Host` → raise), and **character perspective** (`snapshot.player_seats[player_id]`). Resolve identity once per socket at the WS boundary; store it room-only and ephemeral in `SessionRoom.player_identities` (no save/PII persistence); re-resolve every connect. Local dev distinguishes players by per-player Host names (`player1.local`). Repoint the perspective call-site that abused `sd.player_name` to `perspective_character_name(sd)`. PARTY_STATUS carries a nullable `player_identity`; the UI renders the suffix from it and never fabricates a peer suffix. Emit a `player_identity_resolved` watcher event carrying the source only (never the email).

This ADR sits under the ADR-037 (shared-world / per-player state split) umbrella.

## Consequences
- A connection with no resolvable identity is closed (1008) — fail-loud, No Silent Fallbacks.
- Identity is always fresh from the auth boundary; offline peers show their character name with no identity suffix.
- `sd.player_name` is retained as the seated-character name (no rename this story); a full rename/retire is deferred.
- Local MP requires per-player Host names in `/etc/hosts`.

## Alternatives considered
- Persisting identity into the snapshot/save (rejected: PII in saves, staleness).
- Re-admitting the typed `player_name` as a dev identity source (rejected: re-introduces the conflation).
- Full rename of `sd.player_name` (deferred: blast radius beyond one story).
```

- [ ] **Step 2: Regenerate ADR indexes**

Run: `cd /Users/slabgorb/Projects/oq-3 && python scripts/regenerate_adr_indexes.py`
Expected: updates `docs/adr/README.md` (and the CLAUDE.md generated block) with the ADR-119 entry. If the script errors on frontmatter, fix the ADR frontmatter to match the schema and re-run.

- [ ] **Step 3: Commit**

```bash
cd /Users/slabgorb/Projects/oq-3
git add docs/adr/119-authenticated-player-identity.md docs/adr/README.md CLAUDE.md
git commit -m "docs(adr): ADR-119 authenticated player identity (player-vs-character split)"
```

---

## Final verification

- [ ] **Full server suite**

Run: `cd sidequest-server && uv run pytest tests/server/test_player_identity.py tests/server/test_player_identity_wiring.py -v && uv run pytest -q`
Expected: new tests PASS; no regressions in the full suite.

- [ ] **Server lint + types**

Run: `cd sidequest-server && uv run ruff check . && uv run pyright`
Expected: clean (no new errors).

- [ ] **UI test + lint**

Run: `cd sidequest-ui && npx vitest run src/components/__tests__/CharacterPanel.test.tsx && npx eslint src/types/payloads.ts src/components/CharacterPanel.tsx`
Expected: PASS / clean.

- [ ] **Manual smoke (optional, documents the local-dev assumption)**

Confirm the local-MP Host-name assumption: with two clients connecting via `player1.local:5173` and `player2.local:5173` (or distinct Host headers), PARTY_STATUS shows two distinct identities. A single shared `localhost` collapses both to one identity — that is expected and is why per-player Host names are required in dev.
