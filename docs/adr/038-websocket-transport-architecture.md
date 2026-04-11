# ADR-038: WebSocket Transport Architecture

> Retrospective — documents a decision already implemented in the codebase.

## Status
Accepted (partially superseded — TTS removed 2026-04, see ADR-076)

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
