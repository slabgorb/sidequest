# Session Handler Phase 1 — Event Emitters Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract four event-emission methods from `WebSocketSessionHandler` (5458-line `session_handler.py`) into a new sibling module `sidequest-server/sidequest/server/emitters.py`, with byte-identical behavior, mandatory wiring tests, and preserved OTEL span surface.

**Architecture:** Each extracted method becomes a free function in `emitters.py` that takes `handler: WebSocketSessionHandler` as its first argument. The original method on `WebSocketSessionHandler` becomes a thin delegate calling the new free function. No new abstractions, no narrow context dataclasses, no class hierarchies. Behavior is preserved verbatim.

**Tech Stack:** Python 3.12, FastAPI/Uvicorn, pytest, `uv` package manager. Tests run via `just server-test` from orchestrator root or `uv run pytest -v` from `sidequest-server/`.

**Spec:** `docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md` (Phase 1).

**Out of scope for this plan:** Phases 2–8 (views, lore/embed, media, chargen, small handlers, connect, narration turn). Each gets its own plan after this one merges and the extraction pattern is validated.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/server/emitters.py` | **Create** | Houses four free functions: `emit_event`, `emit_scrapbook_entry`, `emit_map_update_for_cartography`, `persist_scrapbook_entry` |
| `sidequest-server/sidequest/server/session_handler.py` | **Modify** | The four method bodies are replaced with thin delegates calling the free functions. All other content untouched. |
| `sidequest-server/tests/server/test_emitters.py` | **Create** | Unit tests for the four functions plus wiring tests confirming the delegates call them |

The four functions are extracted in dependency order:
1. `persist_scrapbook_entry` first (no callers within this cluster)
2. `emit_event` next (called by `emit_scrapbook_entry`)
3. `emit_map_update_for_cartography` next (independent)
4. `emit_scrapbook_entry` last (calls both `persist_scrapbook_entry` and `emit_event`)

This order means each task's extracted function has its dependencies already extracted.

---

## Task 1: Create empty `emitters.py` and confirm the test target fails

**Files:**
- Create: `sidequest-server/sidequest/server/emitters.py`
- Create: `sidequest-server/tests/server/test_emitters.py`

- [ ] **Step 1.1: Create the empty module file**

Create `sidequest-server/sidequest/server/emitters.py` with this exact content:

```python
"""Event emission helpers extracted from WebSocketSessionHandler.

Phase 1 of the session_handler.py decomposition (see
docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).

Each function takes `handler: WebSocketSessionHandler` as its first
argument and operates on the handler's mutable state. No new abstractions
introduced — this is pure extraction with byte-identical behavior to the
original methods on WebSocketSessionHandler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.protocol.messages import ScrapbookEntryPayload
    from sidequest.server.session_handler import WebSocketSessionHandler, _SessionData
```

- [ ] **Step 1.2: Create the test file with one failing import-existence test**

Create `sidequest-server/tests/server/test_emitters.py` with this exact content:

```python
"""Unit + wiring tests for sidequest/server/emitters.py.

Phase 1 of session_handler decomposition. These tests verify:
1. Each extracted function exists with the expected signature.
2. The thin delegate methods on WebSocketSessionHandler still call
   into emitters.py (wiring guard per CLAUDE.md).
3. Behavior is preserved (functional parity with the pre-extraction
   methods).
"""

from __future__ import annotations


def test_emitters_module_exposes_required_functions() -> None:
    """Wiring guard — the four required functions must be importable
    from sidequest.server.emitters by their canonical names."""
    from sidequest.server import emitters

    assert hasattr(emitters, "persist_scrapbook_entry")
    assert hasattr(emitters, "emit_event")
    assert hasattr(emitters, "emit_map_update_for_cartography")
    assert hasattr(emitters, "emit_scrapbook_entry")
```

- [ ] **Step 1.3: Run the test and confirm it fails**

Run from `sidequest-server/`:
```bash
uv run pytest tests/server/test_emitters.py::test_emitters_module_exposes_required_functions -v
```

Expected: FAIL with `AssertionError` (the four functions don't exist yet).

- [ ] **Step 1.4: Commit the skeleton**

```bash
git add sidequest-server/sidequest/server/emitters.py sidequest-server/tests/server/test_emitters.py
git commit -m "refactor(server): create emitters.py skeleton (Phase 1 of session_handler decomposition)"
```

---

## Task 2: Extract `_persist_scrapbook_entry` → `emitters.persist_scrapbook_entry`

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:1336-1373`
- Modify: `sidequest-server/tests/server/test_emitters.py`

- [ ] **Step 2.1: Add wiring test — confirm delegate calls the free function**

Append to `sidequest-server/tests/server/test_emitters.py`:

```python
def test_persist_scrapbook_entry_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._persist_scrapbook_entry
    must delegate to emitters.persist_scrapbook_entry."""
    from sidequest.protocol.messages import ScrapbookEntryPayload
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    captured: list[tuple] = []

    def _spy(h, payload):
        captured.append((h, payload))

    monkeypatch.setattr(emitters, "persist_scrapbook_entry", _spy)

    payload = ScrapbookEntryPayload(
        turn_id=1,
        location="test_loc",
        narrative_excerpt="hello",
        scene_title=None,
        scene_type=None,
        image_url=None,
        world_facts=[],
        npcs_present=[],
    )
    handler._persist_scrapbook_entry(payload)

    assert captured == [(handler, payload)]
```

- [ ] **Step 2.2: Run wiring test to confirm it fails**

```bash
uv run pytest tests/server/test_emitters.py::test_persist_scrapbook_entry_delegate_calls_module_function -v
```

Expected: FAIL — either `AttributeError: module 'sidequest.server.emitters' has no attribute 'persist_scrapbook_entry'`, or the assertion on `captured` fails because the delegate does not yet call the module function.

- [ ] **Step 2.3: Move the body into `emitters.py`**

Add to `sidequest-server/sidequest/server/emitters.py` (below the `if TYPE_CHECKING` block):

```python
def persist_scrapbook_entry(
    handler: "WebSocketSessionHandler",
    payload: "ScrapbookEntryPayload",
) -> None:
    """Insert a scrapbook row into the dedicated table (schema in
    ``game/persistence.py``). The table allows multiple rows per turn —
    no UNIQUE on turn_id.
    """
    import json as _json

    if handler._event_log is None:
        return  # Legacy non-slug path — no DB to write to
    store = handler._event_log.store
    npcs_json = _json.dumps(
        [
            {"name": ref.name, "role": ref.role, "disposition": ref.disposition}
            for ref in payload.npcs_present
        ]
    )
    facts_json = _json.dumps(list(payload.world_facts))
    with store._conn:
        store._conn.execute(
            "INSERT INTO scrapbook_entries "
            "(turn_id, scene_title, scene_type, location, image_url, "
            " narrative_excerpt, world_facts, npcs_present) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload.turn_id,
                payload.scene_title,
                payload.scene_type,
                payload.location,
                payload.image_url,
                payload.narrative_excerpt,
                facts_json,
                npcs_json,
            ),
        )
```

- [ ] **Step 2.4: Replace the method body with a thin delegate**

In `sidequest-server/sidequest/server/session_handler.py`, find the method:
```python
    def _persist_scrapbook_entry(self, payload: ScrapbookEntryPayload) -> None:
```
(currently at file:1336)

Replace its body (file:1336-1373) with:

```python
    def _persist_scrapbook_entry(self, payload: ScrapbookEntryPayload) -> None:
        """Insert a scrapbook row. Delegates to ``emitters.persist_scrapbook_entry``.

        Phase 1 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import emitters

        emitters.persist_scrapbook_entry(self, payload)
```

- [ ] **Step 2.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_emitters.py::test_persist_scrapbook_entry_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 2.6: Add a behavior unit test for the function itself**

Append to `sidequest-server/tests/server/test_emitters.py`:

```python
def test_persist_scrapbook_entry_inserts_row(session_handler_factory) -> None:
    """Behavioral test — calling the function inserts a row into the
    scrapbook_entries table that can be read back."""
    from sidequest.game.event_log import EventLog
    from sidequest.protocol.messages import ScrapbookEntryNpcRef, ScrapbookEntryPayload
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    # The factory does not seed an EventLog by default (legacy path);
    # attach one so the function has a store to write to.
    handler._event_log = EventLog(sd.store)

    payload = ScrapbookEntryPayload(
        turn_id=42,
        location="test_loc",
        narrative_excerpt="The fighter pondered.",
        scene_title="A pondering",
        scene_type="character",
        image_url=None,
        world_facts=["a fact"],
        npcs_present=[
            ScrapbookEntryNpcRef(name="Goblin", role="opponent", disposition="hostile"),
        ],
    )

    emitters.persist_scrapbook_entry(handler, payload)

    rows = sd.store._conn.execute(
        "SELECT turn_id, location, narrative_excerpt FROM scrapbook_entries"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 42
    assert rows[0][1] == "test_loc"
    assert rows[0][2] == "The fighter pondered."


def test_persist_scrapbook_entry_legacy_path_no_event_log_is_noop(
    session_handler_factory,
) -> None:
    """Behavioral test — when handler._event_log is None (legacy path),
    the function returns cleanly without writing or raising."""
    from sidequest.protocol.messages import ScrapbookEntryPayload
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    handler._event_log = None  # legacy path

    payload = ScrapbookEntryPayload(
        turn_id=1,
        location="test_loc",
        narrative_excerpt="nope",
        scene_title=None,
        scene_type=None,
        image_url=None,
        world_facts=[],
        npcs_present=[],
    )

    # Must not raise.
    emitters.persist_scrapbook_entry(handler, payload)
```

- [ ] **Step 2.7: Run the new unit tests — confirm they pass**

```bash
uv run pytest tests/server/test_emitters.py -v
```

Expected: all four tests PASS (the wiring sanity test from Task 1, the wiring guard, and two behavioral tests).

- [ ] **Step 2.8: Run the full server test suite to confirm no regression**

From orchestrator root:
```bash
just server-test
```

Or from `sidequest-server/`:
```bash
uv run pytest -v
```

Expected: all tests PASS. If any test fails, the extraction broke behavior — stop and investigate before committing.

- [ ] **Step 2.9: Commit**

```bash
git add sidequest-server/sidequest/server/emitters.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_emitters.py
git commit -m "refactor(server): extract _persist_scrapbook_entry to emitters.persist_scrapbook_entry"
```

---

## Task 3: Extract `_emit_event` → `emitters.emit_event`

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:918-1074`
- Modify: `sidequest-server/tests/server/test_emitters.py`

- [ ] **Step 3.1: Add wiring test for `emit_event`**

Append to `sidequest-server/tests/server/test_emitters.py`:

```python
def test_emit_event_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._emit_event must delegate
    to emitters.emit_event."""
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    sentinel = object()
    captured: list[tuple] = []

    def _spy(h, kind, payload):
        captured.append((h, kind, payload))
        return sentinel

    monkeypatch.setattr(emitters, "emit_event", _spy)

    result = handler._emit_event("NARRATION", object())

    assert result is sentinel
    assert len(captured) == 1
    assert captured[0][0] is handler
    assert captured[0][1] == "NARRATION"
```

- [ ] **Step 3.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_event_delegate_calls_module_function -v
```

Expected: FAIL — `emitters.emit_event` does not exist yet, or the delegate is not yet calling it.

- [ ] **Step 3.3: Move the `_emit_event` body into `emitters.py`**

Append to `sidequest-server/sidequest/server/emitters.py` (after `persist_scrapbook_entry`):

```python
def emit_event(
    handler: "WebSocketSessionHandler",
    kind: str,
    payload_model: object,
) -> object:
    """Persist an event to the EventLog and fan-out to all connected players.

    Invariants (per Plan 03):
    1. EventLog.append fires BEFORE any socket send.
    2. Fan-out consults ProjectionFilter per recipient.
    3. The emitter (handler) receives the raw, unfiltered event.

    Returns the outbound message object for the calling player (the emitter).
    Falls back to a plain message without seq when EventLog is unavailable
    (legacy non-slug connect path doesn't initialize _event_log).
    """
    import json

    from pydantic import BaseModel

    from sidequest.agents.perception_rewriter import rewrite_for_recipient
    from sidequest.game.projection.envelope import MessageEnvelope
    from sidequest.game.projection_filter import FilterDecision
    from sidequest.server.session_handler import (
        _KIND_TO_MESSAGE_CLS,
        _project_frames,
        logger,
    )

    message_cls = _KIND_TO_MESSAGE_CLS.get(kind)
    if message_cls is None:
        raise ValueError(f"emit_event: unknown kind {kind!r}")

    event_log = handler._event_log
    projection_filter = handler._projection_filter

    # Serialize payload excluding seq (seq is assigned from the DB row)
    if isinstance(payload_model, BaseModel):
        payload_json = payload_model.model_dump_json(exclude={"seq"})
    else:
        payload_json = json.dumps(payload_model)  # type: ignore[arg-type]

    if event_log is not None:
        room = handler._room
        emitter_player_id = handler._session_data.player_id if handler._session_data else None

        # C2: event append + all cache writes share a single transaction.
        # Projections are computed inside the block so the cache row's
        # event_seq is the freshly-assigned one. If the server crashes
        # mid-block, sqlite rolls back both the event row and any partial
        # cache rows — either the event is fully persisted with its
        # projection cache, or not at all.
        store = event_log.store
        conn = store._conn
        fanout: list[tuple[str, FilterDecision, dict]] = []
        with conn:
            row = event_log.append_in_transaction(
                kind=kind, payload_json=payload_json, conn=conn
            )
            seq = row.seq

            if room is not None and projection_filter is not None:
                view = handler._build_game_state_view()
                envelope = MessageEnvelope(
                    kind=row.kind,
                    payload_json=row.payload_json,
                    origin_seq=row.seq,
                )
                # G6: status-effect perception overlay. Built once per
                # event (not per recipient) — snapshot statuses don't
                # change mid-fanout.
                status_effects = handler.status_effects_by_player()

                # G8: route through the shared write-split helper so the
                # per-peer filter loop is a single code path (test and
                # production exercise `_project_frames`).
                recipients = [
                    pid for pid in room.connected_player_ids() if pid != emitter_player_id
                ]

                def _cache_decision(pid: str, decision: FilterDecision) -> None:
                    if handler._projection_cache is not None:
                        handler._projection_cache.write_in_transaction(
                            event_seq=seq,
                            player_id=pid,
                            decision=decision,
                            conn=conn,
                        )

                decisions = _project_frames(
                    envelope=envelope,
                    projection_filter=projection_filter,
                    connected_players=recipients,
                    view=view,
                    on_decision=_cache_decision,
                )
                for other_pid, decision in decisions:
                    filtered_data: dict = {}
                    if decision.include:
                        filtered_data = json.loads(decision.payload_json)
                        # G6: PerceptionRewriter — strip spans whose kind
                        # is incompatible with the recipient's effective
                        # fidelity (base fidelity + status effects like
                        # blinded/deafened). Runs on the already-filtered
                        # payload, before WS send. Deterministic only;
                        # LLM re-voicing is deferred to post-MP.
                        filtered_data = rewrite_for_recipient(
                            canonical_payload=filtered_data,
                            viewer_player_id=other_pid,
                            status_effects=status_effects,
                        )
                    fanout.append((other_pid, decision, filtered_data))

        # Build emitter's message with raw, unfiltered payload + seq
        # (Invariant 3). model_copy with scalar update is safe here —
        # only `seq` is being added, no existing field is being replaced
        # with a filtered value.
        if isinstance(payload_model, BaseModel):
            emitter_payload = payload_model.model_copy(update={"seq": seq})
        else:
            emitter_payload = payload_model  # type: ignore[assignment]
        out_to_self = message_cls(payload=emitter_payload)

        # Socket fan-out happens AFTER the DB transaction commits. A
        # crash between commit and send is recoverable via the cache on
        # reconnect; sending before commit would risk a client observing
        # an event that never hit disk.
        if room is not None:
            payload_cls = type(payload_model) if isinstance(payload_model, BaseModel) else None
            for other_pid, decision, filtered_data in fanout:
                if not decision.include:
                    continue
                socket_id = room.socket_for_player(other_pid)
                if socket_id is None:
                    continue
                queue = room.queue_for_socket(socket_id)
                if queue is None:
                    continue
                try:
                    if payload_cls is not None:
                        # C3: rebuild the recipient payload from the
                        # filtered dict alone (plus seq). Do NOT use
                        # model_copy(update=...) — merging leaves fields
                        # absent from the filtered dict at their canonical
                        # values, which would leak any field a future rule
                        # drops entirely.
                        recipient_payload = payload_cls.model_validate(
                            {**filtered_data, "seq": seq}
                        )
                        recipient_msg = message_cls(payload=recipient_payload)
                    else:
                        recipient_msg = message_cls(payload={**filtered_data, "seq": seq})
                except Exception:
                    # Never silently fail fan-out; log and skip this recipient.
                    logger.error(
                        "emit_event.fanout_failed kind=%s other_pid=%s",
                        kind,
                        other_pid,
                    )
                    continue
                queue.put_nowait(recipient_msg)
    else:
        # Legacy path (non-slug connect): no EventLog, no seq
        out_to_self = message_cls(payload=payload_model)

    return out_to_self
```

> **Note on `_KIND_TO_MESSAGE_CLS`, `_project_frames`, and `logger`:** these are module-level symbols defined at the top of `session_handler.py` (file:1–579). They are imported by `emitters.py` rather than re-defined. This keeps the move minimal — those module-level helpers stay in place per the spec's "out of scope" section.

- [ ] **Step 3.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:
```python
    def _emit_event(self, kind: str, payload_model: object) -> object:
```
(currently at file:918)

Replace its body (file:918-1074) with:

```python
    def _emit_event(self, kind: str, payload_model: object) -> object:
        """Persist + fan-out an event. Delegates to ``emitters.emit_event``.

        Phase 1 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import emitters

        return emitters.emit_event(self, kind, payload_model)
```

- [ ] **Step 3.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_event_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 3.6: Run the full server test suite to confirm no regression**

```bash
uv run pytest -v
```

Expected: all tests PASS. Pay attention to tests that exercise event emission directly:
- `tests/server/test_projection_end_to_end_wiring.py`
- `tests/server/test_perception_rewriter_wiring.py`
- `tests/server/test_replay_kind_coverage.py`
- `tests/server/test_confrontation_mp_broadcast.py`

If any fail, the extraction broke behavior. Stop and investigate.

- [ ] **Step 3.7: Commit**

```bash
git add sidequest-server/sidequest/server/emitters.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_emitters.py
git commit -m "refactor(server): extract _emit_event to emitters.emit_event"
```

---

## Task 4: Extract `_emit_map_update_for_cartography` → `emitters.emit_map_update_for_cartography`

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:1207-1334`
- Modify: `sidequest-server/tests/server/test_emitters.py`

- [ ] **Step 4.1: Add wiring test**

Append to `sidequest-server/tests/server/test_emitters.py`:

```python
def test_emit_map_update_for_cartography_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._emit_map_update_for_cartography
    must delegate to emitters.emit_map_update_for_cartography."""
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    captured: list[tuple] = []

    def _spy(h, *, sd, render_id, player_id):
        captured.append((h, sd, render_id, player_id))

    monkeypatch.setattr(emitters, "emit_map_update_for_cartography", _spy)

    handler._emit_map_update_for_cartography(
        sd=sd, render_id="render-1", player_id=sd.player_id
    )

    assert captured == [(handler, sd, "render-1", sd.player_id)]
```

- [ ] **Step 4.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_map_update_for_cartography_delegate_calls_module_function -v
```

Expected: FAIL — function does not exist or delegate does not yet call it.

- [ ] **Step 4.3: Add the function to `emitters.py`**

Append to `sidequest-server/sidequest/server/emitters.py`:

```python
def emit_map_update_for_cartography(
    handler: "WebSocketSessionHandler",
    *,
    sd: "_SessionData",
    render_id: str,
    player_id: str,
) -> None:
    """Push a ``MAP_UPDATE`` frame to the player's outbound queue when a
    cartography render is dispatched. Mirrors the IMAGE async-emit
    pattern: direct queue push, no journaling, no fan-out via
    ``emit_event``.

    Why no journaling: ``MAP_UPDATE`` is a derived view of world state —
    on reconnect the slice-3 reconnect-replay path will rebuild the
    current map from cartography + ``snapshot.discovered_regions``
    rather than replay every historical frame.

    OTEL: emits ``map.update_emitted`` so the GM panel's "lie detector"
    can confirm the map subsystem actually fired.
    """
    import asyncio

    from sidequest.protocol.enums import MessageType
    from sidequest.protocol.messages import MapUpdateMessage
    from sidequest.server.dispatch.map_update import build_map_update_payload
    from sidequest.server.session_handler import _watcher_publish, logger

    # Resolve the live outbound queue. Mirror of the IMAGE completion
    # path (story 37-30): when room context is bound, the registry's
    # current socket queue survives mid-turn reconnects; otherwise fall
    # back to the legacy out_queue captured at construction.
    target_queue: asyncio.Queue[object] | None = None
    room_slug: str | None = None
    if handler._room is not None:
        room_slug = handler._room.slug
        registry = handler._room_registry
        if registry is not None:
            room = registry.get(room_slug)
            if room is not None:
                socket_id = room.socket_for_player(player_id)
                if socket_id is not None:
                    target_queue = room.queue_for_socket(socket_id)
    if target_queue is None:
        target_queue = handler._out_queue
    if target_queue is None:
        logger.warning(
            "map_update.skipped reason=no_outbound_queue render_id=%s",
            render_id,
        )
        return

    # Pull cartography from the bound world. ``getattr`` chain handles
    # legacy/test fixtures where the world or its cartography may be
    # absent — emit anyway with cartography=None (the wire model allows
    # it) so the UI at least learns the current location.
    world = sd.genre_pack.worlds.get(sd.world_slug) if sd.genre_pack else None
    cartography = getattr(world, "cartography", None) if world is not None else None

    payload = build_map_update_payload(
        snapshot=sd.snapshot, cartography=cartography,
    )
    if payload is None:
        # No current location — emitting an empty MAP_UPDATE would make
        # the UI worse, not better. Surface via OTEL so the GM panel
        # can see the skip rather than silently dropping.
        _watcher_publish(
            "state_transition",
            {
                "field": "map",
                "op": "skipped",
                "reason": "no_current_location",
                "render_id": render_id,
                "tier": "cartography",
                "player_id": player_id,
            },
            component="map",
            severity="warning",
        )
        return

    msg = MapUpdateMessage(
        type=MessageType.MAP_UPDATE,  # type: ignore[arg-type]
        payload=payload,
        player_id=player_id,
    )

    try:
        target_queue.put_nowait(msg)
    except asyncio.QueueFull:
        logger.warning(
            "map_update.outbound_queue_full render_id=%s", render_id
        )
        return

    # OTEL lie-detector — every MAP_UPDATE that hits a queue gets a
    # span. Origin marker mirrors the Rust ``emit_map_update_telemetry``
    # helper so when the location-change and reconnect paths land in
    # slices 2/3, the GM panel can distinguish them at a glance.
    nav_mode = (
        payload.cartography.navigation_mode if payload.cartography else "none"
    )
    _watcher_publish(
        "state_transition",
        {
            "field": "map",
            "op": "update_emitted",
            "origin": "cartography_render",
            "render_id": render_id,
            "tier": "cartography",
            "player_id": player_id,
            "room_slug": room_slug or "",
            "current_location": str(payload.current_location),
            "region": str(payload.region),
            "explored_count": len(payload.explored),
            "has_cartography": payload.cartography is not None,
            "cartography_navigation_mode": nav_mode,
            "genre": sd.genre_slug,
        },
        component="map",
    )
    logger.info(
        "map_update.emitted render_id=%s location=%s explored=%d",
        render_id,
        str(payload.current_location),
        len(payload.explored),
    )
```

- [ ] **Step 4.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:
```python
    def _emit_map_update_for_cartography(
        self,
        *,
        sd: _SessionData,
        render_id: str,
        player_id: str,
    ) -> None:
```
(currently at file:1207)

Replace its body (file:1207-1334) with:

```python
    def _emit_map_update_for_cartography(
        self,
        *,
        sd: _SessionData,
        render_id: str,
        player_id: str,
    ) -> None:
        """Push a MAP_UPDATE frame. Delegates to ``emitters.emit_map_update_for_cartography``.

        Phase 1 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import emitters

        emitters.emit_map_update_for_cartography(
            self, sd=sd, render_id=render_id, player_id=player_id
        )
```

- [ ] **Step 4.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_map_update_for_cartography_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 4.6: Run the existing map-update integration test**

```bash
uv run pytest tests/server/test_map_update_cartography_wiring.py -v
```

Expected: all tests PASS. This is the canonical integration test for this code path; it must keep passing without modification.

- [ ] **Step 4.7: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4.8: Commit**

```bash
git add sidequest-server/sidequest/server/emitters.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_emitters.py
git commit -m "refactor(server): extract _emit_map_update_for_cartography to emitters module"
```

---

## Task 5: Extract `_emit_scrapbook_entry` → `emitters.emit_scrapbook_entry`

**Files:**
- Modify: `sidequest-server/sidequest/server/emitters.py`
- Modify: `sidequest-server/sidequest/server/session_handler.py:1076-1205`
- Modify: `sidequest-server/tests/server/test_emitters.py`

- [ ] **Step 5.1: Add wiring test**

Append to `sidequest-server/tests/server/test_emitters.py`:

```python
def test_emit_scrapbook_entry_delegate_calls_module_function(
    monkeypatch, session_handler_factory
) -> None:
    """Wiring guard — WebSocketSessionHandler._emit_scrapbook_entry
    must delegate to emitters.emit_scrapbook_entry."""
    from sidequest.game.session import GameSnapshot
    from sidequest.server import emitters

    sd, handler = session_handler_factory()
    captured: list[tuple] = []

    def _spy(h, *, sd, snapshot, result):
        captured.append((h, sd, snapshot, result))

    monkeypatch.setattr(emitters, "emit_scrapbook_entry", _spy)

    snap = GameSnapshot(genre_slug=sd.genre_slug)
    sentinel_result = object()
    handler._emit_scrapbook_entry(sd=sd, snapshot=snap, result=sentinel_result)

    assert captured == [(handler, sd, snap, sentinel_result)]
```

- [ ] **Step 5.2: Run the wiring test — confirm it fails**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_scrapbook_entry_delegate_calls_module_function -v
```

Expected: FAIL.

- [ ] **Step 5.3: Add the function to `emitters.py`**

Append to `sidequest-server/sidequest/server/emitters.py`:

```python
def emit_scrapbook_entry(
    handler: "WebSocketSessionHandler",
    *,
    sd: "_SessionData",
    snapshot,  # GameSnapshot — avoid circular import in TYPE_CHECKING
    result: object,
) -> None:
    """Persist a scrapbook row + emit a SCRAPBOOK_ENTRY event for one turn.

    Called immediately after the NARRATION emit so the entry's seq lands
    adjacent to its narration in the journal. The IMAGE that may follow
    from the daemon is async — its URL arrives later and the UI gallery
    merges by ``turn_id``. We never block on the daemon here.

    Pure reuse: location from snapshot, excerpt from the narrator's prose,
    NPCs from the orchestrator's structured extraction. No new LLM calls.
    """
    from sidequest.agents.orchestrator import NarrationTurnResult
    from sidequest.protocol.messages import ScrapbookEntryNpcRef, ScrapbookEntryPayload
    from sidequest.server.session_handler import (
        _resolve_location_display,
        _watcher_publish,
        logger,
    )

    if not isinstance(result, NarrationTurnResult):
        return

    narration_text = (result.narration or "").strip()
    if not narration_text:
        # The UI requires a non-empty excerpt; skip cleanly when the turn
        # produced no prose (only happens in degraded edge cases).
        return

    # UI contract: ``location`` must be non-empty. Fall back to the raw
    # snapshot location when the display lookup yields nothing — better
    # to surface "Unknown" than to silently drop the entry.
    loc_display = _resolve_location_display(
        sd.genre_pack, sd.world_slug, snapshot.location
    ) or (snapshot.location or "Unknown")

    # Trim the excerpt to a reasonable length for caption rendering. The
    # narrator's full prose lives on the NarrationMessage; the scrapbook
    # caption is a short teaser.
    excerpt = narration_text
    if len(excerpt) > 320:
        excerpt = excerpt[:317].rstrip() + "..."

    # NPCs from the orchestrator's structured extraction — no new
    # inference. ``role`` is the side flag (player/opponent/neutral);
    # ``disposition`` falls back to role when no behavioral string was
    # extracted.
    npc_refs: list[ScrapbookEntryNpcRef] = []
    for mention in result.npcs_present or []:
        name = (getattr(mention, "name", "") or "").strip()
        if not name:
            continue
        role = getattr(mention, "side", "") or "neutral"
        disposition = getattr(mention, "role", "") or role
        npc_refs.append(
            ScrapbookEntryNpcRef(
                name=name,
                role=role,
                disposition=disposition,
            )
        )

    # World facts: lift the narrator's footnote summaries when present.
    world_facts: list[str] = []
    for fn in result.footnotes or []:
        if not isinstance(fn, dict):
            continue
        summary = fn.get("summary") or fn.get("text") or ""
        if isinstance(summary, str) and summary.strip():
            world_facts.append(summary.strip())

    scene_type: str | None = None
    scene_title: str | None = None
    visual = getattr(result, "visual_scene", None)
    if visual is not None:
        tier = (getattr(visual, "tier", None) or "").strip()
        scene_type = tier or None
        subject = (getattr(visual, "subject", None) or "").strip()
        if subject:
            scene_title = subject[:120]

    turn_id = int(snapshot.turn_manager.interaction)

    payload = ScrapbookEntryPayload(
        turn_id=turn_id,
        location=loc_display,
        narrative_excerpt=excerpt,
        scene_title=scene_title,
        scene_type=scene_type,
        image_url=None,  # Async — IMAGE frame follows from the daemon
        world_facts=world_facts,
        npcs_present=npc_refs,
    )

    # Persist to the dedicated scrapbook_entries table — keeps the
    # gallery queryable post-game without walking the events journal.
    try:
        persist_scrapbook_entry(handler, payload)
    except Exception as exc:  # noqa: BLE001 — persistence failure must not block emit
        logger.warning("scrapbook.persist_failed turn=%d error=%s", turn_id, exc)

    # Route through emit_event so the journal gets a row + reconnect
    # replay surfaces prior entries to fresh sockets.
    emit_event(handler, "SCRAPBOOK_ENTRY", payload)

    # OTEL lie-detector: GM panel sees per-turn confirmation that the
    # scrapbook subsystem fired. Without this, regression #2 was
    # invisible for two stories.
    _watcher_publish(
        "state_transition",
        {
            "field": "scrapbook",
            "op": "entry_emitted",
            "turn_id": turn_id,
            "image_url": None,
            "location": loc_display,
            "npc_count": len(npc_refs),
            "world_fact_count": len(world_facts),
            "player_id": sd.player_id,
        },
        component="scrapbook",
    )
```

> **Note on intra-module calls:** `emit_scrapbook_entry` calls `persist_scrapbook_entry` and `emit_event` — both already extracted in this module. Call them directly (not through `handler._emit_event` etc.), so the in-module functions become the canonical call site. The handler delegate methods exist only for callers outside this module.

- [ ] **Step 5.4: Replace the method body in `session_handler.py`**

In `sidequest-server/sidequest/server/session_handler.py`, find:
```python
    def _emit_scrapbook_entry(
        self,
        *,
        sd: _SessionData,
        snapshot: GameSnapshot,
        result: object,
    ) -> None:
```
(currently at file:1076)

Replace its body (file:1076-1205) with:

```python
    def _emit_scrapbook_entry(
        self,
        *,
        sd: _SessionData,
        snapshot: GameSnapshot,
        result: object,
    ) -> None:
        """Persist + emit a scrapbook entry. Delegates to ``emitters.emit_scrapbook_entry``.

        Phase 1 of session_handler decomposition (see
        docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md).
        """
        from sidequest.server import emitters

        emitters.emit_scrapbook_entry(self, sd=sd, snapshot=snapshot, result=result)
```

- [ ] **Step 5.5: Run the wiring test — confirm it passes**

```bash
uv run pytest tests/server/test_emitters.py::test_emit_scrapbook_entry_delegate_calls_module_function -v
```

Expected: PASS.

- [ ] **Step 5.6: Run the full server test suite**

```bash
uv run pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5.7: Commit**

```bash
git add sidequest-server/sidequest/server/emitters.py sidequest-server/sidequest/server/session_handler.py sidequest-server/tests/server/test_emitters.py
git commit -m "refactor(server): extract _emit_scrapbook_entry to emitters module"
```

---

## Task 6: OTEL parity verification

**Files:** none modified — read-only verification.

- [ ] **Step 6.1: Confirm OTEL span surface count is preserved**

Count OTEL emissions in `session_handler.py` before this epic landed (the four extracted methods used `_watcher_publish` and `emit_event_span`-style calls). Run:

```bash
grep -nE "_watcher_publish|tracer\.start_as_current_span" sidequest-server/sidequest/server/session_handler.py | wc -l
```

Note the count.

Then count emissions now living in `emitters.py`:

```bash
grep -nE "_watcher_publish|tracer\.start_as_current_span" sidequest-server/sidequest/server/emitters.py | wc -l
```

The combined count (session_handler.py + emitters.py) must be ≥ the original session_handler.py count from before the epic. Use `git log -p docs/superpowers/specs/2026-04-27-session-handler-decomposition-design.md` to find the baseline if needed (the spec was committed before this epic started).

- [ ] **Step 6.2: Smoke playtest (optional but recommended)**

If a developer environment is available, run a brief playtest to confirm the GM panel still shows the `scrapbook.entry_emitted` and `map.update_emitted` watcher events on a real turn. From orchestrator root:

```bash
just up
# In another terminal
just playtest
# Trigger one narration turn that produces a cartography render
just down
```

Confirm the OTEL dashboard at the watcher port (default :9765) shows both events.

- [ ] **Step 6.3: No commit — this task is verification only**

If parity is preserved, proceed to Task 7. If parity is broken, the most likely culprit is a missing import or a `_watcher_publish` argument list that drifted during extraction — read the diff and reconcile.

---

## Task 7: Final cleanup and integration check

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py` (line-count check only)

- [ ] **Step 7.1: Confirm `session_handler.py` line count dropped**

```bash
wc -l sidequest-server/sidequest/server/session_handler.py
```

Expected: approximately **5000 lines** (down from 5458). Allow ±20 lines of variance from the spec's `-460` estimate — exact count depends on delegate-method comment style.

- [ ] **Step 7.2: Run lint**

```bash
just server-lint
```

Or from `sidequest-server/`:
```bash
uv run ruff check .
```

Expected: clean. If `emitters.py` has any lint warnings, fix them inline.

- [ ] **Step 7.3: Run formatter**

```bash
just server-fmt
```

Or:
```bash
uv run ruff format .
```

Expected: no changes. If `emitters.py` got reformatted, commit the formatter changes.

- [ ] **Step 7.4: Run the full check gate**

```bash
just server-check
```

Expected: all green (lint + tests).

- [ ] **Step 7.5: Final commit if formatter made changes**

If `just server-fmt` produced a diff:

```bash
git add -u
git commit -m "refactor(server): apply ruff format to emitters.py"
```

Otherwise skip this step.

---

## Definition of Done — Phase 1

- ✅ `sidequest-server/sidequest/server/emitters.py` exists with four free functions
- ✅ Four thin delegate methods on `WebSocketSessionHandler` route to the new module
- ✅ `tests/server/test_emitters.py` exists with at least one wiring test per delegate (4 wiring tests) and at least one behavioral test for `persist_scrapbook_entry` (the only function with simple-enough I/O for an isolated unit test; the others are exercised by existing integration tests)
- ✅ All existing server integration tests pass without modification (especially `test_map_update_cartography_wiring.py`, `test_projection_end_to_end_wiring.py`, `test_perception_rewriter_wiring.py`)
- ✅ `session_handler.py` line count dropped by ~460 lines
- ✅ OTEL `_watcher_publish` and span surface preserved (combined emitters.py + session_handler.py count ≥ original)
- ✅ `just server-check` passes
- ✅ Five commits land in this order: skeleton, persist_scrapbook_entry, emit_event, emit_map_update_for_cartography, emit_scrapbook_entry (plus optional formatter commit)

## What This Plan Does NOT Cover

- Phases 2–8 of the spec (views, lore/embed, media, chargen, small handlers, connect, narration turn). Each of those gets its own plan after Phase 1 lands and the pattern is validated.
- Removal of the four thin delegate methods on `WebSocketSessionHandler`. Per the spec, the delegates stay for the duration of the epic; their removal is a follow-up cleanup story.
- Any behavioral change. Pure decomposition only.

---

## Self-Review Notes (filled in by author after writing the plan)

**Spec coverage check:**
- All four Phase 1 functions in spec → Tasks 2, 3, 4, 5 (in dependency order)
- Spec acceptance criteria: ✅ free functions exist (each Task), ✅ thin delegates (each Task's "replace body" step), ✅ unit tests (Tasks 2–5 add at least wiring tests + Task 2 adds behavioral tests for the simplest function), ✅ wiring test per delegate (each Task), ✅ existing integration tests pass (each Task's "run full suite" step), ✅ OTEL parity (Task 6)

**Placeholder scan:** No "TBD", "TODO", or "implement later" tokens. All code blocks are complete and copy-pasteable.

**Type consistency:** All four functions take `handler: WebSocketSessionHandler` as first arg. Function names use `emit_*` and `persist_*` prefixes consistently. No drift between task references.

**Known imperfection:** The Task 6 OTEL parity check uses a "≥ original count" threshold rather than an exact `git show` baseline because the original count is what's in `main` before Task 1 lands — the implementing engineer can resolve this with `git show main:sidequest-server/sidequest/server/session_handler.py | grep -nE ...` if they want a precise baseline. This is documented as a sufficient gate, not an absolute requirement.
