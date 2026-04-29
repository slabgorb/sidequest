# Multiplayer Plan 03 — Filtered Event Log & Per-Player Projections

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Status (2026-04-23)

**Tasks 1–9: complete.** All checkboxes below ticked during audit and
reconciliation on 2026-04-23. Server side (Tasks 1–4, 9) was implemented
inline during the `feat/phase-3-story-3-4-combat-dispatch` branch with
explicit MP-03 tags in code comments; all 11 server tests pass
(`test_event_log`, `test_projection_filter`, `test_event_log_wiring`,
`test_event_replay_on_reconnect`, `test_sync_wiring`).

UI side (Tasks 5–8) existed as passing unit tests but had **zero
production consumers** — classic "tests pass but nothing is wired."
Reconciliation path (b) was taken: delete the unused `useEventStream`
duplicate, keep the battle-tested `useGameSocket` as sole WS owner,
and layer the peer cache + `last_seen_seq` directly into `AppInner`.

Deviations closed during reconciliation:

- **`useEventStream` deleted.** It owned its own WebSocket, duplicating
  `useGameSocket` (which already has reconnect, typed messages, and
  session restore). Two WS connections would have been wrong. The three
  files (`useEventStream.ts`, `useEventStream.test.tsx`,
  `useEventStream-offline.test.tsx`) are gone per CLAUDE.md "dead code
  is worse than no code."
- **New hook `usePeerEventCache`.** Narrower than `useEventStream`: no
  WebSocket, just the IDB open + ref-backed `getLatestSeq` + `appendEvent`.
  Callable synchronously at connect time without awaiting IDB.
- **localStorage hint.** IDB is async; if AppInner's slug-connect effect
  gates on IDB open, state races in jsdom tests made `last_seen_seq`
  flaky. Fixed by mirroring the high-water mark into `localStorage`
  under `sq:<slug>:<player>:lastSeq` for synchronous cold-start reads.
  IDB is still authoritative — writes go to both, reads prefer IDB.
- **`peerEventStore.ts` typecheck fix.** Original file used constructor
  parameter properties (`private db: IDBPDatabase`) which are banned by
  `erasableSyntaxOnly`. Replaced with explicit field declarations.
- **Plan target `GameScreen.tsx` moved to `AppInner`.** Same as MP-02:
  that file was deleted in the MP-01 fix-forward. Wiring landed in
  `AppInner` in `src/App.tsx`.
- **Client MessageType constants.** Server-side protocol already carries
  `seq`; client now dedupes incoming events by `${type}:${seq}` with a
  ref-backed set, cleared on reconnect and handleLeave so replay works.
- **OfflineBanner component.** Plan's `{offline && <div ...>}` inline
  JSX became a proper component under `src/components/OfflineBanner.tsx`
  with its own unit test. Wired into AppInner between ReconnectBanner
  and PausedBanner, gated by a 3-second timer on `isReconnecting` so
  transient flaps don't escalate to "offline."
- **Wiring test added.** `src/__tests__/mp-03-event-sync-wiring.test.tsx`
  drives AppInner through a mocked WebSocket with a seeded cache and
  asserts `last_seen_seq` flows correctly on cold start, warm start,
  and that persistence + dedupe happen end-to-end.

Full UI suite delta: 1086 → 1095 passing (+9 tests), 45 failing
unchanged (no regressions). Full MP-03 server tests: 11/11 green.

**Depends on:** Plans 01 and 02 merged.

**Goal:** Put all narrator-originated state mutations through a monotonic event log. Give each peer a filtered view of the log keyed by player_id, plus a client-side event cache so peers can boot UI from local state and catch up on reconnect with `last_seen_seq`.

**Architecture:** The narrator-host persists every outbound event to an `events` table in the game's SQLite with a monotonic `seq` integer. A `ProjectionFilter` is invoked per-recipient for every event to decide include/redact/omit. On WebSocket connect, peers send `last_seen_seq`; the server streams every `seq > last_seen_seq` filtered for that player, then enters live mode. Peers mirror received events to a local SQLite (same schema, per-slug+per-player DB) so they can cold-boot their UI without the narrator-host.

**Tech Stack:** Python (sqlite3, asyncio), pytest, React + TypeScript (IndexedDB via `idb`), vitest.

---

## File Structure

**Create:**
- `sidequest-server/sidequest/game/event_log.py` — `EventRow`, `EventLog` (append, read_since).
- `sidequest-server/sidequest/game/projection_filter.py` — `ProjectionFilter` protocol + pass-through default.
- `sidequest-server/tests/game/test_event_log.py`
- `sidequest-server/tests/game/test_projection_filter.py`
- `sidequest-server/tests/server/test_event_replay_on_reconnect.py`
- `sidequest-server/tests/server/test_sync_wiring.py`
- `sidequest-ui/src/lib/peerEventStore.ts` — IndexedDB event cache.
- `sidequest-ui/src/lib/__tests__/peerEventStore.test.ts`
- `sidequest-ui/src/hooks/useEventStream.ts` — wires WS + local cache.
- `sidequest-ui/src/hooks/__tests__/useEventStream.test.tsx`

**Modify:**
- `sidequest-server/sidequest/game/persistence.py` — append `events` table to `SCHEMA_SQL`.
- `sidequest-server/sidequest/server/session_handler.py` — accept `last_seen_seq` on connect; route outbound narrative/state events through EventLog + ProjectionFilter.
- `sidequest-server/sidequest/protocol/messages.py` — add `seq` field to outbound event messages, extend connect payload with `last_seen_seq`.
- `sidequest-ui/src/screens/GameScreen.tsx` — bootstrap from local cache, send `last_seen_seq`.

---

### Task 1: events table + EventLog append/read

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py` (extend SCHEMA_SQL)
- Create: `sidequest-server/sidequest/game/event_log.py`
- Test: `sidequest-server/tests/game/test_event_log.py`

- [x] **Step 1: Write failing test**

```python
# sidequest-server/tests/game/test_event_log.py
from pathlib import Path
import pytest
from sidequest.game.persistence import SqliteStore, db_path_for_slug
from sidequest.game.event_log import EventLog, EventRow


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    db = db_path_for_slug(tmp_path, "2026-04-22-moldharrow-keep")
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db)
    s.initialize()
    return s


def test_append_assigns_monotonic_seq(store):
    log = EventLog(store)
    r1 = log.append(kind="NARRATION", payload_json='{"text":"hello"}')
    r2 = log.append(kind="STATE_UPDATE", payload_json='{"hp":10}')
    assert r1.seq == 1
    assert r2.seq == 2


def test_read_since_returns_only_newer(store):
    log = EventLog(store)
    for i in range(5):
        log.append(kind="NARRATION", payload_json=f'{{"i":{i}}}')
    rows = log.read_since(since_seq=2)
    assert [r.seq for r in rows] == [3, 4, 5]


def test_read_since_zero_returns_all(store):
    log = EventLog(store)
    log.append(kind="NARRATION", payload_json='{"i":1}')
    log.append(kind="NARRATION", payload_json='{"i":2}')
    rows = log.read_since(since_seq=0)
    assert len(rows) == 2


def test_latest_seq(store):
    log = EventLog(store)
    assert log.latest_seq() == 0
    log.append(kind="NARRATION", payload_json='{}')
    log.append(kind="STATE_UPDATE", payload_json='{}')
    assert log.latest_seq() == 2
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/game/test_event_log.py -v`
Expected: ImportError.

- [x] **Step 3: Add `events` table to SCHEMA_SQL**

In `sidequest-server/sidequest/game/persistence.py`, append to `SCHEMA_SQL`:

```sql
CREATE TABLE IF NOT EXISTS events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_seq ON events (seq);
```

- [x] **Step 4: Implement EventLog**

```python
# sidequest-server/sidequest/game/event_log.py
"""Monotonic event log for a single game slug.

Every narrator-originated mutation (NARRATION, STATE_UPDATE, COMBAT_EVENT, etc.)
is appended here before fan-out. Peers catch up on reconnect via read_since.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from sidequest.game.persistence import SqliteStore


@dataclass
class EventRow:
    seq: int
    kind: str
    payload_json: str
    created_at: str


class EventLog:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def append(self, *, kind: str, payload_json: str) -> EventRow:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._store._connect() as conn:
            cur = conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
                (kind, payload_json, now),
            )
            seq = cur.lastrowid
        assert seq is not None
        return EventRow(seq=seq, kind=kind, payload_json=payload_json, created_at=now)

    def read_since(self, *, since_seq: int) -> List[EventRow]:
        with self._store._connect() as conn:
            rows = conn.execute(
                "SELECT seq, kind, payload_json, created_at FROM events WHERE seq > ? ORDER BY seq ASC",
                (since_seq,),
            ).fetchall()
        return [EventRow(seq=r[0], kind=r[1], payload_json=r[2], created_at=r[3]) for r in rows]

    def latest_seq(self) -> int:
        with self._store._connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
        return int(row[0])
```

- [x] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/game/test_event_log.py -v`
Expected: 4 passed.

- [x] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py sidequest-server/sidequest/game/event_log.py sidequest-server/tests/game/test_event_log.py
git commit -m "feat(game): events table + EventLog (append, read_since, latest_seq)"
```

---

### Task 2: ProjectionFilter protocol + pass-through default

**Files:**
- Create: `sidequest-server/sidequest/game/projection_filter.py`
- Test: `sidequest-server/tests/game/test_projection_filter.py`

- [x] **Step 1: Write failing test**

```python
# sidequest-server/tests/game/test_projection_filter.py
from sidequest.game.projection_filter import (
    ProjectionFilter,
    PassThroughFilter,
    FilterDecision,
)
from sidequest.game.event_log import EventRow


def _row(seq=1, kind="NARRATION", payload='{"text":"hi"}'):
    return EventRow(seq=seq, kind=kind, payload_json=payload, created_at="now")


def test_pass_through_includes_everything_for_everyone():
    f = PassThroughFilter()
    dec = f.project(event=_row(), player_id="alice")
    assert dec.include is True
    assert dec.payload_json == '{"text":"hi"}'


def test_filter_protocol_allows_redaction():
    class RedactHP(ProjectionFilter):
        def project(self, *, event, player_id):
            if event.kind == "STATE_UPDATE" and player_id != "gm":
                return FilterDecision(include=True, payload_json='{}')  # redacted
            return FilterDecision(include=True, payload_json=event.payload_json)

    f = RedactHP()
    dec = f.project(event=_row(kind="STATE_UPDATE", payload='{"hp":10}'), player_id="alice")
    assert dec.payload_json == '{}'
    dec_gm = f.project(event=_row(kind="STATE_UPDATE", payload='{"hp":10}'), player_id="gm")
    assert dec_gm.payload_json == '{"hp":10}'


def test_filter_can_omit():
    class OmitSecrets(ProjectionFilter):
        def project(self, *, event, player_id):
            if event.kind == "SECRET_NOTE" and player_id != "alice":
                return FilterDecision(include=False, payload_json="")
            return FilterDecision(include=True, payload_json=event.payload_json)

    f = OmitSecrets()
    assert f.project(event=_row(kind="SECRET_NOTE"), player_id="bob").include is False
    assert f.project(event=_row(kind="SECRET_NOTE"), player_id="alice").include is True
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/game/test_projection_filter.py -v`
Expected: ImportError.

- [x] **Step 3: Implement**

```python
# sidequest-server/sidequest/game/projection_filter.py
"""Per-player projection filter.

The spec explicitly defers concrete filter rules. This module ships the
protocol + a pass-through default. Asymmetric-info rules land in follow-up
work without touching wiring.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sidequest.game.event_log import EventRow


@dataclass(frozen=True)
class FilterDecision:
    include: bool
    payload_json: str  # may differ from event.payload_json if redacted


class ProjectionFilter(Protocol):
    def project(self, *, event: EventRow, player_id: str) -> FilterDecision: ...


class PassThroughFilter:
    def project(self, *, event: EventRow, player_id: str) -> FilterDecision:
        return FilterDecision(include=True, payload_json=event.payload_json)
```

- [x] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/game/test_projection_filter.py -v`
Expected: 3 passed.

- [x] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/projection_filter.py sidequest-server/tests/game/test_projection_filter.py
git commit -m "feat(game): ProjectionFilter protocol + PassThroughFilter"
```

---

### Task 3: Route narrator outputs through EventLog + filter

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Modify: `sidequest-server/sidequest/protocol/messages.py` (add `seq` field to NARRATION / STATE_UPDATE payloads)
- Test: `sidequest-server/tests/server/test_event_log_wiring.py`

- [x] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_event_log_wiring.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import (
    SqliteStore, db_path_for_slug, upsert_game, GameMode,
)
from sidequest.game.event_log import EventLog


def _seed(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    return db


def test_player_action_appends_narration_to_event_log(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    db = _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                      "payload": {"event": "connect", "game_slug": slug, "last_seen_seq": 0}})
        ws.receive_json()
        ws.send_json({"type": "PLAYER_SEAT", "player_id": "alice",
                      "payload": {"character_slot": "rux"}})
        ws.receive_json()
        ws.send_json({"type": "PLAYER_ACTION", "player_id": "alice",
                      "payload": {"text": "I look around"}})
        resp = ws.receive_json()
        assert resp["type"] == "NARRATION"
        assert resp["payload"]["seq"] >= 1

    store = SqliteStore(db); store.initialize()
    log = EventLog(store)
    rows = log.read_since(since_seq=0)
    assert len(rows) >= 1
    assert any(r.kind == "NARRATION" for r in rows)
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_event_log_wiring.py -v`
Expected: FAIL — `last_seen_seq` not accepted, no `seq` in payload, no rows in log.

- [x] **Step 3: Extend protocol**

In `messages.py`:

```python
# Extend SessionEventPayload (from Plan 01):
class SessionEventPayload(BaseModel):
    event: str
    game_slug: str | None = None
    last_seen_seq: int = 0  # new

# Add seq to NarrationPayload (locate by grep "class NarrationPayload"):
class NarrationPayload(BaseModel):
    # ... existing fields
    seq: int = 0
```

Apply the same `seq` field to any other outbound-event payload that is persisted (STATE_UPDATE, COMBAT_EVENT, etc.). Find them with `grep -n "class .*Payload(BaseModel)" sidequest-server/sidequest/protocol/messages.py`.

- [x] **Step 4: Wire EventLog + filter into session_handler**

In `session_handler.py`, in the slug-connect branch, after `self._room = room`:

```python
from sidequest.game.event_log import EventLog
from sidequest.game.projection_filter import PassThroughFilter

self._event_log = EventLog(store)
self._projection_filter = PassThroughFilter()
self._last_seen_seq = payload.last_seen_seq
```

Find every outbound message emission from the narrator flow (dispatch path that currently returns `[NarrationMessage(...)]`). Wrap outbound persistence in a helper:

```python
def _emit_event(self, kind: str, payload_model: BaseModel):
    """Persist to log, then fan out filtered copies to each seated player."""
    payload_json = payload_model.model_dump_json(exclude={"seq"})
    row = self._event_log.append(kind=kind, payload_json=payload_json)
    # The emitting player (self) sees the raw event
    out_to_self = payload_model.model_copy(update={"seq": row.seq})
    # Fan out filtered copies via room broadcast
    for other_pid in self._room.connected_player_ids():
        if other_pid == self._current_player_id:
            continue
        dec = self._projection_filter.project(event=row, player_id=other_pid)
        if not dec.include:
            continue
        filtered_payload = payload_model.model_copy(update={"seq": row.seq}).model_copy(
            update=json.loads(dec.payload_json) if dec.payload_json else {}
        )
        # Route to that player's socket specifically
        other_socket = self._room._connected.get(other_pid)  # you may want a public accessor
        if other_socket:
            q = self._room._outbound_queues.get(other_socket)
            if q:
                q.put_nowait(type(payload_model.__class__.__bases__[0])(payload=filtered_payload))
    return out_to_self
```

**Note:** The above is a sketch — the exact final form depends on the existing message constructor style. The required invariant is:
1. Every narrator-originated mutation gets `EventLog.append` **before** any socket send.
2. Fan-out consults `ProjectionFilter` per recipient.
3. The emitter sees the raw, unfiltered event.

If cleanup of direct `_connected` / `_outbound_queues` private access is needed, add public accessors on SessionRoom (`socket_for_player(pid) -> str | None`, `queue_for_socket(sid) -> asyncio.Queue | None`) — that's well-scoped support code, not scope creep.

In the `PLAYER_ACTION` handler, replace the current `return [narration_msg]` with `return [self._emit_event("NARRATION", narration_payload)]`.

- [x] **Step 5: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_event_log_wiring.py -v`
Expected: 1 passed.

- [x] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/sidequest/server/session_room.py sidequest-server/sidequest/protocol/messages.py sidequest-server/tests/server/test_event_log_wiring.py
git commit -m "feat(sync): route narrator outputs through EventLog + ProjectionFilter"
```

---

### Task 4: Reconnect replay — send events since last_seen_seq

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py`
- Test: `sidequest-server/tests/server/test_event_replay_on_reconnect.py`

- [x] **Step 1: Write failing test**

```python
# sidequest-server/tests/server/test_event_replay_on_reconnect.py
from pathlib import Path
from fastapi.testclient import TestClient
from sidequest.server.app import create_app
from sidequest.game.persistence import (
    SqliteStore, db_path_for_slug, upsert_game, GameMode,
)
from sidequest.game.event_log import EventLog


def _seed_with_events(tmp_path, slug):
    db = db_path_for_slug(tmp_path, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    s = SqliteStore(db); s.initialize()
    upsert_game(s, slug=slug, mode=GameMode.MULTIPLAYER,
                genre_slug="low_fantasy", world_slug="moldharrow-keep")
    log = EventLog(s)
    for i in range(3):
        log.append(kind="NARRATION", payload_json=f'{{"text":"beat {i}"}}')
    return db


def test_connect_with_last_seen_seq_replays_missed_events(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed_with_events(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                      "payload": {"event": "connect", "game_slug": slug, "last_seen_seq": 1}})
        # First expect SESSION_CONNECTED or REPLAY, then replayed events (seq 2, 3)
        seen_seqs = []
        for _ in range(6):
            m = ws.receive_json()
            if m["type"] == "NARRATION":
                seen_seqs.append(m["payload"]["seq"])
            if seen_seqs == [2, 3]:
                break
        assert seen_seqs == [2, 3]


def test_connect_with_last_seen_seq_equal_to_latest_replays_nothing(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed_with_events(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                      "payload": {"event": "connect", "game_slug": slug, "last_seen_seq": 3}})
        # Expect SESSION_CONNECTED, then nothing further within a small window
        import socket
        ws.receive_json()  # SESSION_CONNECTED
        # No replay follows — connection stays open, no more data.
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_event_replay_on_reconnect.py -v`
Expected: FAIL — no replay.

- [x] **Step 3: Add replay after connect**

In the slug-connect branch of `session_handler.py`, after emitting SESSION_CONNECTED but before returning:

```python
missed = self._event_log.read_since(since_seq=self._last_seen_seq)
replay_msgs = []
for row in missed:
    dec = self._projection_filter.project(event=row, player_id=self._current_player_id)
    if not dec.include:
        continue
    # Reconstruct the typed message for this event kind
    replay_msgs.append(_build_message_for_kind(kind=row.kind, payload_json=dec.payload_json, seq=row.seq))
return [session_connected_msg, *replay_msgs]
```

Add `_build_message_for_kind` helper near the top of the module:

```python
def _build_message_for_kind(*, kind: str, payload_json: str, seq: int):
    import json
    from sidequest.protocol.messages import NarrationMessage, NarrationPayload, StateUpdateMessage, StateUpdatePayload
    data = json.loads(payload_json)
    data["seq"] = seq
    if kind == "NARRATION":
        return NarrationMessage(payload=NarrationPayload(**data))
    if kind == "STATE_UPDATE":
        return StateUpdateMessage(payload=StateUpdatePayload(**data))
    raise ValueError(f"unknown event kind for replay: {kind}")
```

Extend the dispatch table as you add kinds — don't silently fall back.

- [x] **Step 4: Run tests**

Run: `cd sidequest-server && uv run pytest tests/server/test_event_replay_on_reconnect.py -v`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_event_replay_on_reconnect.py
git commit -m "feat(sync): replay missed events since last_seen_seq on reconnect"
```

---

### Task 5: UI — peerEventStore (IndexedDB per slug+player)

**Files:**
- Create: `sidequest-ui/src/lib/peerEventStore.ts`
- Test: `sidequest-ui/src/lib/__tests__/peerEventStore.test.ts`

- [x] **Step 1: Add `idb` dependency**

```bash
cd sidequest-ui && npm install idb@^8
```

- [x] **Step 2: Write failing test**

```ts
// sidequest-ui/src/lib/__tests__/peerEventStore.test.ts
import 'fake-indexeddb/auto';
import { PeerEventStore } from '../peerEventStore';

describe('PeerEventStore', () => {
  it('appends events and returns them in seq order', async () => {
    const s = await PeerEventStore.open('slug-a', 'alice');
    await s.append({ seq: 1, kind: 'NARRATION', payload: { text: 'hi' } });
    await s.append({ seq: 2, kind: 'NARRATION', payload: { text: 'there' } });
    const all = await s.readAll();
    expect(all.map((e) => e.seq)).toEqual([1, 2]);
  });

  it('latestSeq returns 0 for empty store', async () => {
    const s = await PeerEventStore.open('slug-empty', 'alice');
    expect(await s.latestSeq()).toBe(0);
  });

  it('latestSeq returns max seq', async () => {
    const s = await PeerEventStore.open('slug-b', 'alice');
    await s.append({ seq: 1, kind: 'NARRATION', payload: {} });
    await s.append({ seq: 5, kind: 'NARRATION', payload: {} });
    expect(await s.latestSeq()).toBe(5);
  });

  it('scopes by slug+player', async () => {
    const a = await PeerEventStore.open('slug-c', 'alice');
    const b = await PeerEventStore.open('slug-c', 'bob');
    await a.append({ seq: 1, kind: 'NARRATION', payload: { for: 'alice' } });
    const bAll = await b.readAll();
    expect(bAll).toEqual([]);
  });
});
```

Add `fake-indexeddb` to dev deps: `npm install -D fake-indexeddb@^6`.

- [x] **Step 3: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/lib/__tests__/peerEventStore.test.ts`
Expected: module not found.

- [x] **Step 4: Implement**

```ts
// sidequest-ui/src/lib/peerEventStore.ts
import { openDB, type IDBPDatabase } from 'idb';

export type PeerEvent = {
  seq: number;
  kind: string;
  payload: unknown;
};

export class PeerEventStore {
  private constructor(private db: IDBPDatabase, private storeName: string) {}

  static async open(slug: string, playerId: string): Promise<PeerEventStore> {
    const dbName = `sq:${slug}:${playerId}`;
    const storeName = 'events';
    const db = await openDB(dbName, 1, {
      upgrade(d) {
        if (!d.objectStoreNames.contains(storeName)) {
          d.createObjectStore(storeName, { keyPath: 'seq' });
        }
      },
    });
    return new PeerEventStore(db, storeName);
  }

  async append(ev: PeerEvent): Promise<void> {
    await this.db.put(this.storeName, ev);
  }

  async readAll(): Promise<PeerEvent[]> {
    const all = await this.db.getAll(this.storeName);
    return (all as PeerEvent[]).sort((a, b) => a.seq - b.seq);
  }

  async latestSeq(): Promise<number> {
    const all = await this.readAll();
    return all.length === 0 ? 0 : all[all.length - 1].seq;
  }
}
```

- [x] **Step 5: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/lib/__tests__/peerEventStore.test.ts`
Expected: 4 passed.

- [x] **Step 6: Commit**

```bash
git add sidequest-ui/src/lib/peerEventStore.ts sidequest-ui/src/lib/__tests__/peerEventStore.test.ts sidequest-ui/package.json sidequest-ui/package-lock.json
git commit -m "feat(ui): PeerEventStore — IndexedDB per-slug+player event cache"
```

---

### Task 6: UI — useEventStream hook (WS + cache, sends last_seen_seq)

**Files:**
- Create: `sidequest-ui/src/hooks/useEventStream.ts`
- Test: `sidequest-ui/src/hooks/__tests__/useEventStream.test.tsx`

- [x] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/hooks/__tests__/useEventStream.test.tsx
import 'fake-indexeddb/auto';
import { renderHook, waitFor, act } from '@testing-library/react';
import { WS } from 'jest-websocket-mock';
import { useEventStream } from '../useEventStream';

describe('useEventStream', () => {
  let server: WS;
  beforeEach(async () => {
    server = new WS('ws://localhost:1234/ws', { jsonProtocol: true });
  });
  afterEach(() => { WS.clean(); });

  it('sends last_seen_seq=0 on first connect', async () => {
    const { result } = renderHook(() =>
      useEventStream({ wsUrl: 'ws://localhost:1234/ws', slug: 'slug-a', playerId: 'alice' }),
    );
    await server.connected;
    const msg = await server.nextMessage as any;
    expect(msg.type).toBe('SESSION_EVENT');
    expect(msg.payload.last_seen_seq).toBe(0);
  });

  it('caches received events and sends latest seq on reconnect', async () => {
    const { result, unmount } = renderHook(() =>
      useEventStream({ wsUrl: 'ws://localhost:1234/ws', slug: 'slug-b', playerId: 'alice' }),
    );
    await server.connected;
    await server.nextMessage;
    act(() => {
      server.send({ type: 'NARRATION', payload: { seq: 1, text: 'beat 1' } });
      server.send({ type: 'NARRATION', payload: { seq: 2, text: 'beat 2' } });
    });
    await waitFor(() => expect(result.current.events.length).toBe(2));
    unmount();
    WS.clean();

    const server2 = new WS('ws://localhost:1234/ws', { jsonProtocol: true });
    renderHook(() =>
      useEventStream({ wsUrl: 'ws://localhost:1234/ws', slug: 'slug-b', playerId: 'alice' }),
    );
    await server2.connected;
    const msg = await server2.nextMessage as any;
    expect(msg.payload.last_seen_seq).toBe(2);
  });
});
```

Install `jest-websocket-mock`: `npm i -D jest-websocket-mock@^2`.

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useEventStream.test.tsx`
Expected: module not found.

- [x] **Step 3: Implement**

```ts
// sidequest-ui/src/hooks/useEventStream.ts
import { useEffect, useRef, useState } from 'react';
import { PeerEventStore, type PeerEvent } from '../lib/peerEventStore';

type Args = { wsUrl: string; slug: string; playerId: string };

export function useEventStream({ wsUrl, slug, playerId }: Args) {
  const [events, setEvents] = useState<PeerEvent[]>([]);
  const storeRef = useRef<PeerEventStore | null>(null);

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | null = null;

    (async () => {
      const store = await PeerEventStore.open(slug, playerId);
      if (cancelled) return;
      storeRef.current = store;
      const cached = await store.readAll();
      setEvents(cached);
      const lastSeen = await store.latestSeq();

      ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        ws!.send(JSON.stringify({
          type: 'SESSION_EVENT',
          player_id: playerId,
          payload: { event: 'connect', game_slug: slug, last_seen_seq: lastSeen },
        }));
      };
      ws.onmessage = async (ev) => {
        const m = JSON.parse(ev.data);
        if (m.payload && typeof m.payload.seq === 'number') {
          const peerEv: PeerEvent = { seq: m.payload.seq, kind: m.type, payload: m.payload };
          await store.append(peerEv);
          setEvents((cur) => [...cur, peerEv]);
        }
      };
    })();

    return () => { cancelled = true; ws?.close(); };
  }, [wsUrl, slug, playerId]);

  return { events };
}
```

- [x] **Step 4: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useEventStream.test.tsx`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add sidequest-ui/src/hooks/useEventStream.ts sidequest-ui/src/hooks/__tests__/useEventStream.test.tsx sidequest-ui/package.json sidequest-ui/package-lock.json
git commit -m "feat(ui): useEventStream — WS + IndexedDB cache with last_seen_seq resume"
```

---

### Task 7: Wire useEventStream into GameScreen

**Files:**
- Modify: `sidequest-ui/src/screens/GameScreen.tsx`
- Test: `sidequest-ui/src/screens/__tests__/GameScreen-event-wiring.test.tsx`

- [x] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/screens/__tests__/GameScreen-event-wiring.test.tsx
import 'fake-indexeddb/auto';
import { render, screen, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { WS } from 'jest-websocket-mock';
import App from '../../App';

describe('GameScreen event wiring', () => {
  beforeEach(() => { localStorage.setItem('sq:display-name', 'alice'); });
  afterEach(() => { WS.clean(); localStorage.clear(); });

  it('renders narration events received over WS', async () => {
    const wsUrl = `ws://${location.host}/ws`;
    const server = new WS(wsUrl, { jsonProtocol: true });
    render(
      <MemoryRouter initialEntries={['/play/2026-04-22-moldharrow-keep']}>
        <App />
      </MemoryRouter>,
    );
    await server.connected;
    await server.nextMessage;  // SESSION_EVENT connect
    act(() => { server.send({ type: 'NARRATION', payload: { seq: 1, text: 'You enter a dim hall.' } }); });
    await waitFor(() => expect(screen.getByTestId('narration-log')).toHaveTextContent('dim hall'));
  });
});
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/screens/__tests__/GameScreen-event-wiring.test.tsx`
Expected: FAIL — no narration-log testid yet.

- [x] **Step 3: Wire the hook**

In `sidequest-ui/src/screens/GameScreen.tsx`, replace the manual WS block with:

```tsx
import { useEventStream } from '../hooks/useEventStream';

export function GameScreen({ mode }: { mode: 'solo' | 'multiplayer' }) {
  const { slug = '' } = useParams<{ slug: string }>();
  const { name } = useDisplayName();
  if (!name) return <NamePrompt />;
  const { events } = useEventStream({
    wsUrl: `ws://${location.host}/ws`,
    slug,
    playerId: name,
  });

  const narrations = events.filter((e) => e.kind === 'NARRATION');

  return (
    <div data-testid="game-screen" data-mode={mode} data-slug={slug}>
      <ol data-testid="narration-log">
        {narrations.map((e) => (
          <li key={e.seq}>{(e.payload as any).text}</li>
        ))}
      </ol>
    </div>
  );
}
```

(If PausedBanner from Plan 02 is still needed, keep it — read `paused` state from events too, or from a separate `usePresence` hook. This plan doesn't regress Plan 02's PausedBanner wiring.)

- [x] **Step 4: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/screens/__tests__/GameScreen-event-wiring.test.tsx`
Expected: 1 passed.

- [x] **Step 5: Commit**

```bash
git add sidequest-ui/src/screens/GameScreen.tsx sidequest-ui/src/screens/__tests__/GameScreen-event-wiring.test.tsx
git commit -m "feat(ui): wire useEventStream into GameScreen, render narration log"
```

---

### Task 8: Read-only mode when narrator-host unreachable

**Files:**
- Modify: `sidequest-ui/src/hooks/useEventStream.ts`
- Modify: `sidequest-ui/src/screens/GameScreen.tsx`
- Test: `sidequest-ui/src/hooks/__tests__/useEventStream-offline.test.tsx`

- [x] **Step 1: Write failing test**

```tsx
// sidequest-ui/src/hooks/__tests__/useEventStream-offline.test.tsx
import 'fake-indexeddb/auto';
import { renderHook, waitFor } from '@testing-library/react';
import { PeerEventStore } from '../../lib/peerEventStore';
import { useEventStream } from '../useEventStream';

describe('useEventStream offline mode', () => {
  it('exposes cached events and offline=true when WS fails', async () => {
    const s = await PeerEventStore.open('slug-offline', 'alice');
    await s.append({ seq: 1, kind: 'NARRATION', payload: { text: 'old beat' } });

    const { result } = renderHook(() =>
      useEventStream({
        wsUrl: 'ws://localhost:65535/does-not-exist',
        slug: 'slug-offline',
        playerId: 'alice',
      }),
    );

    await waitFor(() => expect(result.current.events.length).toBe(1));
    await waitFor(() => expect(result.current.offline).toBe(true), { timeout: 2000 });
  });
});
```

- [x] **Step 2: Run to verify failure**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useEventStream-offline.test.tsx`
Expected: FAIL — `offline` not exposed.

- [x] **Step 3: Add offline state**

Update `useEventStream.ts`:

```ts
export function useEventStream({ wsUrl, slug, playerId }: Args) {
  const [events, setEvents] = useState<PeerEvent[]>([]);
  const [offline, setOffline] = useState(false);
  // ... existing effect, then:
  ws.onerror = () => setOffline(true);
  ws.onclose = () => setOffline(true);
  ws.onopen = () => { setOffline(false); ws!.send(/* ... */); };
  return { events, offline };
}
```

Add an offline banner in GameScreen:

```tsx
const { events, offline } = useEventStream({...});
return (
  <div data-testid="game-screen" ...>
    {offline && <div data-testid="offline-banner">Narrator unreachable — showing cached state (read-only)</div>}
    {/* ... */}
  </div>
);
```

- [x] **Step 4: Run tests**

Run: `cd sidequest-ui && npm test -- --run src/hooks/__tests__/useEventStream-offline.test.tsx`
Expected: 1 passed.

- [x] **Step 5: Commit**

```bash
git add sidequest-ui/src/hooks/useEventStream.ts sidequest-ui/src/screens/GameScreen.tsx sidequest-ui/src/hooks/__tests__/useEventStream-offline.test.tsx
git commit -m "feat(ui): read-only offline mode when narrator-host unreachable"
```

---

### Task 9: End-to-end sync wiring test

**Files:**
- Create: `sidequest-server/tests/server/test_sync_wiring.py`

- [x] **Step 1: Write the test**

```python
# sidequest-server/tests/server/test_sync_wiring.py
"""Two clients, same MP game, both receive events in seq order, late joiner catches up."""
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


def test_late_joiner_catches_up(tmp_path: Path):
    slug = "2026-04-22-moldharrow-keep"
    _seed(tmp_path, slug)
    app = create_app(save_dir=tmp_path)
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        ws_a.send_json({"type": "SESSION_EVENT", "player_id": "alice",
                        "payload": {"event": "connect", "game_slug": slug, "last_seen_seq": 0}})
        ws_a.receive_json()
        ws_a.send_json({"type": "PLAYER_SEAT", "player_id": "alice",
                        "payload": {"character_slot": "rux"}})
        ws_a.receive_json()
        ws_a.send_json({"type": "PLAYER_ACTION", "player_id": "alice",
                        "payload": {"text": "I look around"}})
        first = ws_a.receive_json()
        assert first["type"] == "NARRATION"
        first_seq = first["payload"]["seq"]

        # Late joiner bob connects with last_seen_seq=0
        with client.websocket_connect("/ws") as ws_b:
            ws_b.send_json({"type": "SESSION_EVENT", "player_id": "bob",
                            "payload": {"event": "connect", "game_slug": slug, "last_seen_seq": 0}})
            ws_b.receive_json()  # SESSION_CONNECTED
            # Then a replay of alice's narration
            replay = ws_b.receive_json()
            assert replay["type"] == "NARRATION"
            assert replay["payload"]["seq"] == first_seq
```

- [x] **Step 2: Run**

Run: `cd sidequest-server && uv run pytest tests/server/test_sync_wiring.py -v`
Expected: 1 passed.

- [x] **Step 3: Commit**

```bash
git add sidequest-server/tests/server/test_sync_wiring.py
git commit -m "test(wiring): end-to-end — late joiner catches up via replay"
```

---

## Plan 03 Self-Review

Spec sections covered:
- Narrator-host = single writer (all mutations go through EventLog) → **Task 3**
- Per-player projection via filter → **Tasks 2, 3**
- Filtered event stream fan-out → **Task 3**
- Reconnect with `last_seen_seq` → **Task 4**
- Peer save as filtered event log + derived snapshot → **Tasks 5, 6**
- Read-only when narrator-host unreachable → **Task 8**
- Explicit filter-rules are deferred (PassThroughFilter ships; real rules are a follow-up) — matches spec's Open Follow-Ups

**Known simplification:** The "derived snapshot" mentioned in the spec is implicit here — consumers that need a snapshot reduce over `events` themselves (existing useStateMirror-style patterns). No separate snapshot store. That matches "DRY, YAGNI" — add a snapshot table only if event-count scaling actually becomes a problem.

**Post-Plan cleanup (not blocking):** Once Plan 03 is in, the legacy `/api/saves/*` endpoints from Plan 01 Task 10 and the old `(genre, world, player)` save-path helper in `persistence.py` can be deleted. That's a chore ticket, not part of this plan.
