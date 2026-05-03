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

## Implementation notes (2026-04-26)

ADR-082 port from Rust to Python (~2026-04-19) carried over the
`TurnManager.submit_input()` barrier API at
`sidequest-server/sidequest/game/turn.py:93–101` but did **not** re-implement
the dispatch-side wiring. `_handle_player_action` continued to call
`_execute_narration_turn` immediately on every WebSocket submission,
which is FreePlay semantics regardless of player count. The barrier
existed in the codebase as dead code with zero production callers
(`grep -rn submit_input sidequest-server/sidequest --include='*.py' | grep -v tests`
returned only the definition).

This was discovered live in the 2026-04-26 caverns_and_claudes/grimvault
playtest — both players submitted, both received independent narrations,
neither acknowledged the other's action. Filed as `[S5-ARCH]` in the
playtest pingpong.

The Cinematic mode is now wired in `_handle_player_action` via:

- `SessionRoom.pending_actions: dict[str, PendingAction]` — round-level
  action buffer keyed by player_id.
- `SessionRoom.dispatch_lock: asyncio.Lock` — serializes elected handlers.
- `SessionRoom.last_dispatched_round: int` — CAS guard against duplicate
  dispatch when two handlers wake from the same barrier flip.

The Rust `TurnBarrier` (tokio::Notify) and `AtomicU64` CAS were not ported
literally — Python's asyncio Lock + plain int counter cover the same
guarantees with simpler primitives. The "last submitter runs the
dispatch" pattern replaces the CAS-then-Notify-then-claim sequence; it's
equivalent for single-event-loop asyncio servers because no two handlers
can be inside the same `async with` block simultaneously.

`AdaptiveTimeout` and the "remains silent" default are still deferred per
CLAUDE.md primary-audience guidance (Alex / slow typist). v1 blocks the
round indefinitely; the table waits, the narrator does not gallop ahead.
Reintroduce the timeout when player feedback demands it.

OTEL events `mp.barrier_fired` and `mp.round_dispatched` are emitted on
every multiplayer round so the GM panel can audit the engagement of the
cinematic-mode pipeline.

`record_interaction()` is called exactly once per round, inside
`_execute_narration_turn` (existing call site preserved unchanged). An
earlier draft of the implementation also called it from the elected
branch, which silently double-incremented `turn_manager.interaction` in
multiplayer; the redundant call was removed before merge.

Spec: `docs/superpowers/specs/2026-04-26-mp-cinematic-mode-wiring-design.md`.
Plan: `docs/superpowers/plans/2026-04-26-mp-cinematic-mode-wiring.md`.

## Amendment — Action Visibility Model (2026-05-03)

**Trigger:** Playtest 2026-05-03 feedback. Coordination broke down because cinematic-mode's information-hiding default was too aggressive — players could not see what teammates were composing or what they had already submitted, so plans formed in isolation and conflicted on resolution.

**Decision:** Action *input* visibility is the new default. All party members see each other's in-progress and post-submit action text in real time during cinematic-mode rounds. Information-hiding moves entirely into *narration output* — SECRET_NOTE payloads and per-player `visibility_tag` filtering, both of which already exist.

**What is unchanged:**
- The cinematic-mode action buffer.
- The barrier and CAS-guarded dispatcher (single narrator dispatch per round).
- `PLAYER_ACTION` semantics. The sealed-letter resolution mechanic (dogfight cross-product lookup in `sealed_letter.py`) is a different system overloading the same name; it is untouched.

**Mechanism:** New `ACTION_REVEAL` message type carries `composing` / `submitted` updates from clients (debounced ~250ms) and `cleared` updates from the server (emitted at barrier-fire dispatch and on socket disconnect). Client-side a `usePeerReveals` hook owns the per-round peer reveal map; a `PeerRevealList` component renders the rows above `MultiplayerTurnBanner`.

**OTEL coverage:** `action_reveal.composing`, `action_reveal.submitted`, `action_reveal.cleared`, and `action_reveal.dropped_rate_limit` watcher events emitted from the handler and cleared-trigger sites. Privacy: `text_length` only — never the action content. Player input is sensitive; length + cadence + count are sufficient for the GM-panel lie-detector.

**Cross-references:**
- Spec: `docs/superpowers/specs/2026-05-03-live-teammate-typing-design.md`
- Plan: `docs/superpowers/plans/2026-05-03-live-teammate-typing.md`
- Playtest feedback memory: `project_playtest_2026_05_03.md` (in user auto-memory)
- ADR-051 (round counter authority for the `round` field on the wire payload)

**Future:** If a scene ever genuinely needs hidden input (perception rewriter, traitor briefings, charmed players), introduce a per-scene flag then. Current playgroup play does not need it. Cinematic-mode round timeout is also out of scope until that timeout itself is implemented.
