---
id: 36
title: "Multiplayer Turn Coordination"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [multiplayer]
implementation-status: live
implementation-pointer: null
---

# ADR-036: Multiplayer Turn Coordination

> Retrospective — documents a decision already implemented in the codebase.

## Context

Multiplayer SideQuest sessions require turn coordination: knowing when all players have
submitted their action for a turn so the narrator can run. In a real-time async system,
different players submit at different times. Naively waking the narrator on every
submission causes duplicate narration calls. Waiting indefinitely for a slow player
blocks the game.

Additionally, once all players have submitted, multiple WebSocket handler tasks wake
simultaneously from the same broadcast notification — each believing it should run the
narrator. Without a claim mechanism, narrator calls would duplicate.

## Decision

Multiplayer sessions use a three-mode TurnMode FSM with a Tokio-based adaptive barrier
for turn synchronization and a claim-election mechanism ensuring exactly one WebSocket
handler runs the narrator per turn.

**Three modes** (`sidequest-game/src/turn_mode.rs`):

- **FreePlay** — async, non-blocking. Players act independently; the narrator runs as
  soon as any player submits. No waiting. Currently the always-active mode.
- **Structured** — barrier mode. Narrator waits until all connected players have
  submitted, with an adaptive timeout. On timeout, missing players receive a
  mode-aware default action ("hesitates").
- **Cinematic** — sealed-letter mode. Actions collected simultaneously, revealed all
  at once. Default on timeout: "remains silent". Used for high-drama simultaneous
  reveal scenes.

Structured is intentionally disabled at runtime to prevent blocking when one player
submits early and others are slow. It exists for future activation with proper UX.

**TurnBarrier** (`barrier.rs`) — uses `tokio::sync::Notify` for immediate wake-on-last-
submission rather than polling. An `AdaptiveTimeout` scales the wait window with player
count to account for latency variance in larger sessions.

**Claim election** (`multiplayer.rs`) — when multiple WebSocket tasks wake simultaneously:

```rust
// In SharedGameSession
last_claim_turn: AtomicU64,
resolution_lock: Mutex<()>,
```

Each woken task attempts to claim the current turn by atomically comparing-and-swapping
`last_claim_turn`. Only the task that wins the CAS proceeds to `wait_for_turn()` and
dispatches to the narrator. Losers drop their claim and return without processing.
The `resolution_lock` mutex serializes the claim check itself.

## Alternatives Considered

- **Global lock on narrator dispatch** — rejected. Too coarse; serializes all WebSocket
  handlers even in single-player sessions where it's unnecessary.
- **Per-player action queues** — rejected. Complex fan-in logic; moves the "who narrates"
  decision into queue drain logic, making it harder to reason about.
- **External coordinator (Redis, message queue)** — rejected. Overengineered for a
  single-server deployment. All WebSocket connections are on the same server process;
  in-process primitives are sufficient and faster.
- **Channel-based rendezvous** — considered but `Notify` is simpler for the
  wake-on-last-submission pattern and avoids buffering concerns.

## Consequences

**Positive:**
- Single-player sessions pay zero overhead — the barrier and claim election are no-ops
  when `connected_players == 1`.
- FreePlay mode maintains the feel of a responsive single-player game even in multiplayer
  lobbies where players aren't synchronized.
- Claim election is lock-free on the fast path (atomic CAS); the mutex only serializes
  the rare simultaneous-wake race.
- Timeout auto-resolve keeps the game moving without manual GM intervention.

**Negative:**
- Structured and Cinematic modes require explicit activation and tested UX before
  enabling; they are dead code paths for now.
- The claim election logic is subtle — a missed CAS means a player's action is silently
  dropped from that turn's narration, which must be monitored via OTEL spans.
- AdaptiveTimeout tuning for large player counts is empirical, not formally derived.
