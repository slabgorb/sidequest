---
id: 122
title: "SessionRoom Lifecycle — RoomRegistry Never-Evict Policy, LobbyState FSM, Multi-Socket Presence Ref-Counting"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [36, 37, 38, 67]
tags: [multiplayer, transport-infrastructure]
implementation-status: live
implementation-pointer: null
---

# ADR-122: SessionRoom Lifecycle

> **Documents a system already live in code.** `SessionRoom`, `RoomRegistry`,
> the `LobbyState` FSM, and the multi-socket presence ref-count shipped
> incrementally across the multiplayer turn-coordination, shared-world, and
> unified-narrator work (Story 45-2, the 2026-05-07 host-presence fix, the
> 2026-05-24 `close_store` ordering fix) without a single governing ADR. The
> lower-level spec `docs/superpowers/specs/2026-05-01-session-aggregate-design.md`
> exists, but it is an *implementation* spec, not an architecture-of-record. This
> record closes that gap and states what the decision *was*.

## Context

A SideQuest game is identified by a **slug** (genre/world session key — the same
`session_slug` that is the Postgres `sessions` row per ADR-115). Multiple
WebSocket connections — multiple players, and even multiple sockets for the *same*
player — converge on one slug and must share one consistent view of one world.

Three architectural facts forced a per-slug in-memory aggregate to exist:

1. **ADR-037 (shared-world / per-player split)** requires one canonical
   `GameSnapshot` and one `SaveRepository` per slug, written by every session
   bound to it — not a per-connection copy.
2. **ADR-067 (unified narrator agent)** requires exactly one `Orchestrator` per
   slug. Without a slug-level singleton, each player constructs their own
   Orchestrator at connect and the system collapses into parallel solo games —
   the failure observed in playtest 2026-04-26 ("MP — players run as parallel
   solo games"), cited at `session_room.py`.
3. **ADR-036 (multiplayer turn coordination)** requires a per-slug submit-and-wait
   barrier whose denominator is *the count of players who must submit before
   narration fires*. That denominator is room state, not connection state.

ADR-038 governs the WebSocket transport itself (accept, reader/writer split,
typed frames). ADR-036 governs the *barrier mechanics* (round vs interaction,
election, action visibility). Neither governs **who owns the room, how long it
lives, or how presence is computed when sockets churn.** That ownership and
lifecycle is what this ADR records.

Three concrete bugs drove the lifecycle design and are preserved as inline
comments in the source — they are the "why":

- **Story 45-2 — phantom-chargen-peer turn-barrier bug** (`session_room.py`,
  `:664-674`). A peer who had connected and claimed a seat but was still in
  character creation was counted by the structured-mode barrier, so a solo player
  could not advance until a phantom never-played peer "submitted." Modeling lobby
  presence as implicit booleans had rotted; the fix is an explicit FSM.
- **2026-05-07 — host presence cleared on transient disconnect**
  (`session_room.py`, `:415-426`, `:466-480`). HMR, tab backgrounding, and
  Playwright tab-switch wakeups open a *second* concurrent WS for the same
  `player_id`; the legacy code dropped presence the instant *one* socket closed,
  evicting a still-present host from the roster. The fix ref-counts presence by
  `player_id`.
- **2026-05-24 — `close_store` ordering violation** (`session_room.py`).
  Tearing the store down before the final on-disconnect save silently no-op'd the
  save (`save()` early-returns on a `None` store); and the previous shape nulled
  `_store` but left `_snapshot` set, so the next `bind_world` early-returned on its
  idempotency check *without* re-attaching a store — every reconnecting session
  then crashed at `sd.store.recent_narrative(...)` (sq-playtest 2026-05-24,
  `'NoneType' object has no attribute 'recent_narrative'`).

## Decision

**The per-slug in-memory room aggregate `SessionRoom` owns all shared session
state; `RoomRegistry` is a process-global dict of these rooms that never evicts.
Lobby lifecycle is an explicit `LobbyState` FSM, and player presence is
ref-counted across all of a player's live sockets.**

### Room aggregate ownership (`SessionRoom`)

One `SessionRoom` exists per slug (`session_room.py`). It owns:

- **The canonical world.** `_snapshot: GameSnapshot` and `_store: SaveRepository`,
  bound once via `bind_world()` (idempotent — first connect binds, later connects
  observe via the `snapshot` / `store` properties; `:262-264` early-returns on an
  existing binding). A per-slug `Session` aggregate wraps these plus optional
  orbital content. (ADR-037.)
- **The canonical narrator.** `_orchestrator: Orchestrator`, created exactly once
  via `get_or_create_orchestrator(factory)` under `_lock` — a concurrent peer
  connecting on the same slug at the same instant cannot construct a second
  Orchestrator (`:303-333`). (ADR-067.)
- **Per-socket outbound queues.** `_outbound_queues: dict[socket_id, asyncio.Queue]`
  — one queue per WS, drained by that WS's dedicated writer task
  (`websocket.py`). `attach_outbound` / `detach_outbound` register and
  deregister them (`:880-888`); `broadcast()` fans a message into every queue
  except an optional excluded socket (`:900-964`).
- **The barrier denominator.** `_pending_actions`, `_crash_released` (per-interaction),
  and `_table_folded_player_ids` (per-hand) — the inputs to
  `effective_barrier_count()` (`:754-786`). (ADR-036.)
- **Presence bookkeeping.** `_connected` (player → latest socket), `_sockets`
  (socket → player), and the authoritative `_player_sockets` (player → set of all
  live sockets).
- **The lobby FSM.** `_seated: dict[player_id, _Seat]`, each seat carrying a
  `LobbyState`.

A SessionRoom holds **no truth that the save does not** — its content is derivable
from the canonical snapshot, so loss on process restart is acceptable (players
reconnect and re-seat; `session_room.py`).

### Never-evict policy (`RoomRegistry`)

`RoomRegistry` (`session_room.py`) is a process-global `dict[slug,
SessionRoom]` with `get_or_create` and `get` — and **no `remove`, no `evict`, no
TTL, no LRU.** Once a slug has a room, that room lives for the life of the process.

This is deliberate. The `AnthropicSdkClient` backing the room's orchestrator
(ADR-101) carries prompt-cache and rolling-baseline state keyed by the slug
(`session_id`); evicting and rebuilding it would discard that warm state on every
last-disconnect. The cost is explicit and accepted: **per-slug Claude-client state
lives for the entire process lifetime** (`session_room.py`). The
cost-runaway exposure this creates is mitigated by `reset_baselines` at teardown
(see Invariants and Consequences below) — *not* by eviction.

### LobbyState FSM (Story 45-2)

A peer's lobby slot is an explicit state machine (`session_room.py`),
replacing the implicit booleans that produced the phantom-peer bug. States:

| State | Stored? | Meaning |
|-------|---------|---------|
| `CONNECTED` | emitted, not stored | WS open, no `PLAYER_SEAT` yet (no `_Seat` exists at connect time) |
| `CLAIMING_SEAT` | reserved | The instantaneous edge between `PLAYER_SEAT` receipt and `seat()`; defined for forward extensibility but **no path emits it** (the edge is a single function call) |
| `CHARGEN` | on `_Seat` | Seat claimed, character builder active |
| `PLAYING` | on `_Seat` | Character committed, in the world |
| `ABANDONED` | on `_Seat` | Disconnected during chargen — reclaimable, never deleted |

Transitions:

- **`(new) → CONNECTED`** — `connect()` emits `lobby.state_transition`
  (`:441-450`). Not stored: no seat exists yet.
- **`CONNECTED → CHARGEN`** — `seat()` creates a `_Seat` defaulting to `CHARGEN`
  (`:591-615`); `_Seat.state` defaults to `CHARGEN` because a fresh seat-claim *is*
  chargen (`:129`).
- **`CHARGEN → PLAYING`** — `transition_to_playing()` (`:617-645`), called after
  `builder.build()` succeeds at chargen confirmation, and for returning players
  whose character is already in the snapshot. Idempotent (no-op if already
  `PLAYING`; no-op if no seat).
- **`CHARGEN → ABANDONED`** — `disconnect()` flips a still-in-chargen seat to
  `ABANDONED` when its *last* socket closes (`:516-528`). ABANDONED slots are
  reclaimable and are **not** counted by the turn barrier.

The FSM exists so three different predicates can each ask a different question of
the same record without rotting:

- **Turn barrier** reads `PLAYING`-only (`playing_player_ids()` / `playing_player_count()`,
  `:663-678`) — phantom CHARGEN peers no longer block the table.
- **Pause banner** reads `is_paused()` = any `PLAYING` peer not currently connected
  (`:854-874`) — a chargen-abandoned peer never pauses the game.
- **GM-panel lobby count** reads `non_abandoned_player_count()` = seats with
  `state != ABANDONED` (`:680-692`), so historical chargen-failure orphans do not
  inflate the lobby count shown against the active count.

### Multi-socket presence ref-counting (2026-05-07)

Presence is ref-counted by `player_id` over `_player_sockets`
(`session_room.py`): **a player is "present" as long as that set is
non-empty.** `connect()` adds the new socket to the set without untracking any
prior socket (`:434-437`) — each socket owns its own `WebSocketDisconnect`
lifecycle and calls `disconnect(socket_id=…)` exactly once. `disconnect()`
discards only the closing socket; presence-clearing side effects (drop
`_connected`, abandon a chargen seat, broadcast the cleared action-reveal, signal
`PLAYER_PRESENCE{disconnected}`) fire **only when the last socket for that
`player_id` closes** (`:484-528`). When other live sockets remain, `_connected`
is repointed at a surviving socket and `disconnect()` returns `None` to signal "no
presence change" so the WS endpoint does not broadcast a spurious disconnect
(`:497-551`).

## Invariants / Contracts

These are the load-bearing guarantees a contributor must not break.

### I1 — `close_store` persist-before-close (2026-05-24)

`room.save()` must complete **before** `room.close_store()`. The WS endpoint's
`finally` block enforces this: `handler.cleanup()` persists the final snapshot via
`room.save()` first; only then, and only if cleanup did not raise and the save was
not swallowed, does it call `room.close_store()` (`websocket.py`).
`close_store()` nulls `_store`, `_snapshot`, and `_session` **together**
(`session_room.py`) so the next `bind_world` re-binds fully instead of
early-returning on a stale snapshot with a null store. Nulling `_store` first
would make the cleanup `save()` silently no-op (`save()` early-returns on a `None`
store, `:294-297`) — the exact persist-before-close violation that lost the final
snapshot.

### I2 — Never-evict ⇒ `reset_baselines` on slug recycle

Because `RoomRegistry` never evicts (and thus the `AnthropicSdkClient` lives for
the process lifetime per slug), `close_store()` calls `reset_baselines(self.slug)`
on the orchestrator's SDK client as slug-recycle prep (`session_room.py`).
Without it, the rolling cost baseline can self-train onto a sustained runaway and
silence its own alarm; resetting at teardown ensures the next session on the same
slug starts cold. The reset is best-effort across backends (claude -p / Ollama
have no `reset_baselines`), but a *failure* logs at **ERROR**, never WARNING and
never silently — a swallowed reset is the cost-runaway hazard this guard exists to
prevent (`:403-413`, No Silent Fallbacks).

### I3 — Barrier denominator under crash and fold

`effective_barrier_count()` is the **single** source of truth for "how many
submissions the barrier needs" (`session_room.py`), read by both the
normal submission path and the crash-release path:

- `denominator = PLAYING peers − (crash_released ∪ table_folded)`.
- **Crash-release** (Story 67-1) is **per-interaction**: a client that signals a
  render crash before submitting drops from the denominator for *this* interaction
  only, and is cleared on `drain_pending_actions()` (`:797-812`). A crashed client
  stays `PLAYING` (its socket is open), so `playing_player_count()` alone would keep
  counting it — hence the explicit release set.
- **Table-fold** (confrontation): a seat that folds/goes out drops for the **rest
  of the hand** (multiple decision points) and is cleared only by
  `clear_table_folds()` at table teardown (`:733-752`), *not* by drain.
- A seat in both sets is subtracted once (the sets are unioned). Underflow is
  surfaced as a WARNING and clamped to 0 — never allowed to pass silently into
  `recheck_barrier`'s `<= 0` guard (`:773-786`).

### I4 — Presence ref-count invariant

Presence side effects fire **iff** the last socket for a `player_id` closes. While
`_player_sockets[player_id]` is non-empty the player is present; `_connected` always
points at a live socket for a present player. `broadcast()` treats
`_outbound_queues` as delivery ground truth and loudly logs/emits any `_connected`
player whose socket has no queue (`broadcast.recipient_dropped`,
`session_room.py`) — counting `len(_connected)` over-reports and silently
strands peers (the 2026-04-30 "scrapbook only on first-connected player" bug).

## Consequences

**Positive**

- One snapshot, one store, one orchestrator per slug — ADR-037 and ADR-067 are
  structurally guaranteed, not merely conventional.
- The LobbyState FSM gives the barrier, the pause banner, and the GM panel three
  independent, non-rotting predicates over one record; phantom-peer and
  chargen-abandonment edges are handled by state, not ad-hoc booleans.
- Multi-socket ref-counting makes HMR / tab-reload / Playwright tab-switch a no-op
  for everyone else's roster — transient client churn no longer evicts a present
  host.
- Every lifecycle decision emits OTEL (`lobby.state_transition`,
  `lobby.seat_abandoned`, `presence.multi_socket_attach`, `presence.disconnect_skipped`,
  `action_reveal.cleared`, `broadcast.recipient_dropped`) so the GM panel can verify
  the machinery engaged rather than infer it (project OTEL principle).

**Negative / risks**

- **Never-evict cost-runaway exposure.** Every slug ever opened keeps its room —
  and its `AnthropicSdkClient` with prompt-cache and rolling-baseline state — for
  the entire process lifetime. Memory grows monotonically with distinct slugs
  played per process, and a stale rolling baseline could self-train into silencing
  its own cost alarm. This is the explicit cost of the decision; `reset_baselines`
  at teardown (I2) is the mitigation, *not* eviction. A long-lived production
  process with many distinct slugs would eventually want eviction — see
  Alternatives.
- **In-memory only.** Room state is lost on process restart. Accepted because it is
  derivable from the save (players reconnect and re-seat), but it means presence,
  lobby state, and the barrier denominator are not durable across a server bounce.
- **FSM surface.** Five states (one reserved, one emitted-not-stored) is more
  conceptual weight than booleans; the payoff is the three clean predicates.

## Alternatives considered

- **LRU / TTL eviction of idle rooms.** Rejected for now. Evicting a room discards
  the warm `AnthropicSdkClient` (prompt cache, baseline) on every last-disconnect,
  re-paying cold-start cost when a table returns to a slug minutes later — and
  introduces a re-bind race against an in-flight reconnect. Never-evict + cold
  `reset_baselines` was chosen as the simpler, race-free option for a small-table
  process. Eviction is namable future work if per-process slug count grows
  unbounded; the persist-before-close and reset-on-recycle invariants already
  define the teardown an evictor would reuse.
- **Single shared broadcast channel vs. queue-per-socket.** Rejected. A single
  channel cannot honor `exclude_socket_id` (ADR-036 action visibility needs to omit
  the sender), cannot detect a connected player whose socket lost its queue
  (`broadcast.recipient_dropped`), and couples one slow consumer to all peers. One
  `asyncio.Queue` per socket drained by a dedicated writer task (`websocket.py`)
  isolates back-pressure per connection and makes `_outbound_queues` the auditable
  delivery ground truth (I4).
- **Implicit presence/lobby booleans (status quo ante).** Rejected — it produced
  both the phantom-chargen-peer barrier bug and the host-presence-on-transient-
  disconnect bug. The FSM and the ref-count are the direct repairs.

## Reconciliation with existing ADRs

- **ADR-036 (Multiplayer Turn Coordination):** complementary. ADR-036 owns barrier
  *mechanics* (round vs interaction counter, dispatch election, action-reveal
  visibility). ADR-122 owns *where the barrier denominator lives and how it is
  computed under crash-release, table-fold, and the PLAYING-only filter* — the room
  state the barrier reads, not the barrier algorithm.
- **ADR-037 (Shared-World / Per-Player State Split):** ADR-122 is the in-memory
  realization of ADR-037's "one canonical world per slug." The room owns the single
  `GameSnapshot` + `SaveRepository` every bound session reads and writes.
- **ADR-038 (WebSocket Transport):** complementary. ADR-038 owns the connection
  (accept, reader/writer split, typed frames). ADR-122 owns the slug-level aggregate
  those connections attach to via `attach_outbound` / `connect` and detach via
  `detach_outbound` / `disconnect`.
- **ADR-067 (Unified Narrator Agent):** ADR-122 supplies the single-Orchestrator-
  per-slug guarantee ADR-067 requires, via `get_or_create_orchestrator` under
  `_lock`. The never-evict policy is what lets that one narrator session — and its
  Anthropic SDK state — persist for the slug's life.
- **Implementation spec note:** `docs/superpowers/specs/2026-05-01-session-aggregate-design.md`
  is the lower-level design for this aggregate. It is an implementation spec, not an
  ADR; this record is the architecture-of-record above it.
