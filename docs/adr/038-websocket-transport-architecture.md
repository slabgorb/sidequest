---
id: 38
title: "WebSocket Transport Architecture"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [76, 82, 62]
tags: [transport-infrastructure]
implementation-status: live
implementation-pointer: null
---

# ADR-038: WebSocket Transport Architecture

> Retrospective — documents a decision already implemented in the codebase.

> **Note (2026-04-11):** The original three-channel design below included a
> binary PCM channel for Kokoro TTS frames. **TTS has been removed from the
> server**; no production code path now sends `Message::Binary` frames. The
> reader/writer split and `ProcessingGuard` RAII pattern remain in active use,
> but the broadcast topology is effectively two channels (JSON `GameMessage`
> and session-scoped `TargetedMessage`). ADR-076 formalizes the post-TTS
> narration flow. Treat the "three channels" language below as historical.

## Context

SideQuest requires bidirectional real-time communication between the game engine and the
browser client: JSON game state events flowing to the client, player actions flowing to
the server, and raw TTS audio frames streaming to the client in near-real-time. A single
naive channel design either forces TTS audio through JSON serialization (expensive, lossy
for binary data) or requires complex type unions.

Additionally, multiplayer sessions need both broadcast (all players receive narration)
and unicast (one player receives their inventory update) without maintaining a separate
connection registry per session.

## Decision

Each WebSocket connection uses Tokio's reader/writer task split with three separate
broadcast channels and a `ProcessingGuard` RAII type preventing concurrent dispatch
for the same player.

**Reader/writer split** (`sidequest-server/src/ws.rs`):

```
WebSocket connection
├── reader task — receives player actions, feeds dispatch pipeline
└── writer task — merges three channels via tokio::select!, sends to client
```

The two tasks share only the WebSocket sink/stream halves (split via axum's WebSocket
split). Neither task blocks the other.

**Three channels:**

1. **`broadcast_tx: broadcast::Sender<GameMessage>`** (on `AppState`) — JSON-serialized
   game state events: narration, state patches, NPC updates, trope activations. Reaches
   all connected clients. Subscribers filter by session if needed.

2. **`session_tx: broadcast::Sender<TargetedMessage>`** (on `SharedGameSession`) —
   session-scoped delivery. `TargetedMessage` carries an optional `target_player_id`:
   `None` = fan-out to all players in the session, `Some(id)` = unicast to one player.
   Eliminates the need for a separate per-connection sender registry.

3. **`binary_broadcast_tx: broadcast::Sender<Vec<u8>>`** — raw PCM audio frames
   (s16le, 24kHz). TTS audio bypasses JSON entirely; frames are sent as WebSocket
   binary messages. This channel exists because JSON serialization of audio is
   prohibitively expensive and base64 encoding introduces ~33% size overhead with
   no benefit for a binary-native protocol.

**Writer task merge:**

```rust
loop {
    tokio::select! {
        Ok(msg) = game_rx.recv()     => send_json(&msg).await,
        Ok(msg) = targeted_rx.recv() => {
            if msg.targets(player_id) { send_json(&msg.payload).await }
        },
        Ok(frame) = audio_rx.recv()  => send_binary(frame).await,
    }
}
```

**`ProcessingGuard`** — RAII type acquired by the reader task before dispatching a
player action. If a guard is already held for this player (e.g., a slow LLM call is
still in flight), the new action is rejected with an `ActionRejected` response rather
than queued. This prevents action pile-up when the narrator is slow and ensures game
state is never patched by two concurrent dispatches for the same player.

## Alternatives Considered

- **Single multiplexed channel with enum payload** — rejected. Forces the writer task
  to match on type for every message, including binary audio. Audio frames would need
  wrapping/unwrapping on every send, adding allocation overhead in the hot path.
- **Server-Sent Events (SSE) + REST POST for actions** — rejected. SSE is
  unidirectional; player action submission requires a separate HTTP round-trip per
  action. Adds latency and eliminates connection state.
- **Raw TCP** — rejected. Browsers cannot open raw TCP connections; WebSocket is the
  minimum viable browser-compatible bidirectional protocol.
- **WebRTC DataChannel for audio** — considered but substantially more complex to
  establish (requires signaling, STUN/TURN). WebSocket binary frames are sufficient
  for TTS latency requirements.
- **Action queue instead of ProcessingGuard** — rejected. Queuing actions during slow
  LLM calls allows players to queue up 5 actions that all fire when the narrator
  resumes, producing incoherent narration. Hard rejection is correct game behavior.

## Consequences

**Positive:**
- Audio channel bypasses serialization entirely — PCM frames go wire-ready with no
  encoding overhead.
- `TargetedMessage` fan-out/unicast on a single channel eliminates per-connection
  sender tracking; the session doesn't need to know which connections are active.
- Reader/writer split means slow audio sends don't block action processing and vice versa.
- `ProcessingGuard` rejection is immediately visible to the client and generates an
  OTEL span — no silent action loss.

**Negative:**
- Three channels means three `recv()` arms in `tokio::select!`; starvation of lower-
  priority channels is possible under sustained audio load (audio frames are frequent).
  Priority must be managed by the select ordering.
- `broadcast::Sender` has a fixed channel capacity; a slow subscriber that falls behind
  will receive a `RecvError::Lagged` and must reconnect. This is acceptable but must
  be handled gracefully in the client.
- Binary audio channel carries no metadata (player target, sequence number); ordering
  and routing are implicit from connection context. Multi-player TTS interleaving
  requires careful daemon scheduling to avoid frame mixing.

## Amendment (2026-05-31): Python Fan-Out — Per-Socket asyncio.Queue + Writer Task

Everything above documents the **retired Rust mechanism** (Tokio reader/writer split,
three `broadcast::Sender` channels, the `ProcessingGuard` RAII type). Per the port-era
reading guide (`docs/adr/README.md`), that text is preserved as a historical design
record. The backend was ported from Rust to Python under **ADR-082**; the transport
layer was reimplemented, not transliterated. This amendment records the
**structurally-different Python fan-out that is the live transport** and the rationale
for its central choice.

### What's actually live

The live mechanism is **queue-per-socket**, not a single shared broadcast channel. The
Rust design subscribed every writer task to one `tokio::broadcast::Sender` and let the
writers filter; the Python design gives each connection its own
`asyncio.Queue` and a dedicated writer `asyncio.Task` that drains only that queue.

**Per-connection writer task** (`sidequest-server/sidequest/server/websocket.py`):

- On accept, each connection mints a `socket_id` and an
  `out_queue: asyncio.Queue` (`websocket.py`), then hands both to the
  handler via `attach_room_context(...)` (`websocket.py`).
- A dedicated writer is spawned per connection:
  `writer_task = asyncio.create_task(_writer())` (`websocket.py`), where `_writer`
  is an infinite `await out_queue.get()` → `_send_message(...)` loop
  (`websocket.py`). This is the structural analogue of the old Tokio writer
  task, but it drains **one socket's** queue rather than `tokio::select!`-merging
  shared channels.
- The reader loop never sends directly: handler output is enqueued with
  `out_queue.put_nowait(outbound_msg)` (`websocket.py`), so a broadcast
  reaching *other* sockets' queues and this socket's own turn-output both flow through
  the same single-drainer queue — no interleaving of `send_text` calls on one socket.
- On teardown the writer is cancelled and the queue is deregistered:
  `writer_task.cancel()` then `room.detach_outbound(socket_id)` (`websocket.py`).
- **Closing-state guard:** `_send_message` short-circuits when
  `websocket.application_state != WebSocketState.CONNECTED`, logging
  `ws.send_skipped_closing` at DEBUG and returning without sending
  (`websocket.py`). This absorbs the normal tab-refresh / mid-fan-out close
  race (a broadcast queued before the peer dropped) as a lifecycle event rather than a
  `ws.send_failed` WARNING — while genuine send faults still surface at WARNING
  (`websocket.py`). This replaces the Rust `RecvError::Lagged` →
  reconnect contract; a slow Python socket simply backs up its own queue.

**Room-level fan-out** (`sidequest-server/sidequest/server/session_room.py`):

- The room owns `_outbound_queues: dict[str, asyncio.Queue]`
  (`session_room.py`), populated via `attach_outbound(socket_id, queue)`
  (`session_room.py`, called from `handlers/connect.py`) and torn down via
  `detach_outbound(socket_id)` (`session_room.py`).
- `broadcast(msg, *, exclude_socket_id=None)` (`session_room.py`) snapshots the
  target queues under `_lock`, then `put_nowait`s the message onto each one outside the
  lock (`session_room.py`). Because `put_nowait` never blocks and the queues are
  unbounded, **any coroutine** (turn dispatch, presence broadcast, image emit) can fan a
  message out to every socket without awaiting and without holding the lock during
  delivery. This is the unicast/broadcast unification that `TargetedMessage` provided in
  Rust — here it falls out of "which queues do I put into."
- **`broadcast.recipient_dropped` detection** (`session_room.py`): `broadcast`
  also computes the set of players who are in `_connected` but whose socket has **no**
  entry in `_outbound_queues` — the mid-broadcast churn state where `_connected` and
  `_outbound_queues` diverge. Each such drop is logged
  (`broadcast.recipient_dropped ... reason=queue_missing`) and emitted as a
  `state_transition` watcher event at `severity="warning"` so the GM panel sees a
  stranded recipient instead of a silent loss. The method **returns the actual queued
  `(socket_id, player_id)` pairs** so callers use real delivery as ground truth rather
  than `len(_connected)`, which over-reports during the divergence (the 2026-04-30
  "Scrapbook only on first-connected player" bug).

### Rationale — why queue-per-socket instead of one shared channel

A single shared channel (the Rust `tokio::broadcast` topology, or a Python equivalent
where all writers consume one queue/stream) couples every consumer to the slowest one:
the fan-out cannot retire a message until laggards have taken it, so **one slow socket
exerts head-of-line blocking on the whole broadcast.** Giving each socket its own
`asyncio.Queue` with a dedicated drainer decouples them — `broadcast` `put_nowait`s into
N independent queues and returns immediately; a socket that is slow to flush (a
backgrounded tab, a stalled client) only backs up *its own* queue and *its own* writer
task. The other sockets' writers keep draining at full speed. The cost is N queues and N
tasks instead of one channel, which at playgroup scale (a handful of connections per
slug) is negligible and well worth never letting Alex's slower client stall narration
delivery to the rest of the table.

### Relationship to other ADRs

- **ADR-082** (port back to Python) is the umbrella decision under which this
  reimplementation happened; the transport was rebuilt on `asyncio` primitives rather
  than ported line-for-line.
- **ADR-062** (Rust `lib.rs` extraction — route groups, state, watcher events) is the
  pre-port ADR that carved the Rust `handle_ws_connection` / writer-task structure out
  of `lib.rs`; its post-port note maps that layout onto today's
  `sidequest/server/websocket.py` + `session_room.py`. Read it for the Rust-side
  lineage of the code this amendment describes.
- **ADR-076** already retired the binary PCM channel (post-TTS); combined with this
  amendment, the live transport is JSON-only, fanned out per-socket.
