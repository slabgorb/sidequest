---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-2: Turn barrier counts active turn-takers, not lobby connections

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session):** four save files clustered
at 16:30–16:31 UTC; only Rux actually played. The structured-mode turn barrier
nonetheless waited on all four lobby connections, so Rux hit barriers mid-solo
because three phantom lobby peers never took their turns. Logs show the saves
existed but the chargen path on three of them never reached the
"character committed" state.

This is the bug Alex (slow reader, easily blocked under time pressure) and Rux
(here, a solo player blocked by phantoms) both feel directly. It is also the
sealed-letter pacing fix Sprint 3 is built around — a barrier that counts
non-players cannot be both inclusive and responsive.

**Design direction set by Keith (2026-04-27):** of the four fix dimensions in
the story description, implement **#3 (explicit lobby joined-vs-playing
states) AND #4 (chargen-abandonment cancels the lobby slot).** Dimensions #1
(timeout-based pruning) and #2 (round-0 heuristic) are explicitly out of
scope; the state machine is the structural fix and timeout pruning would just
paper over a real lifecycle gap. The two selected dimensions are
complementary: #3 defines the state machine; #4 is the rule that drives the
chargen → abandoned transition.

This is **load-bearing for the sprint goal** — sealed-letter turns require the
barrier to track playing peers, not lobby presence.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the test to exercise the actual barrier-decision
seam, **not** an internal predicate test. Two seams must be hit:

1. **Lobby ↔ turn-barrier seam** — `_buffer_action()` /
   `_dispatch_structured_round()` in `sidequest/server/session_handler.py:3207–3277`.
   Specifically the predicate at line 3222 that calls
   `room.seated_player_count()`; that is the line whose output must change.
2. **Chargen → lobby-state seam** — `_chargen_confirmation()` at
   `sidequest/server/session_handler.py:2573–2690` (success path that today
   builds the character) and `disconnect()` at
   `sidequest/server/session_room.py:206` (today removes the socket but does
   NOT cancel the seat if chargen was in flight). The `playing`-state
   transition lands in `_chargen_confirmation()` after `builder.build()` on
   line ~2597; the `abandoned` transition lands in `disconnect()`.

Boundary tests must drive these via the WebSocket message dispatch path, using
`session_handler_factory()` in `tests/server/conftest.py:330` and the
`_FakeClaudeClient` (conftest.py:195) so chargen completes deterministically.

### Lobby state machine (NEW)

Add an explicit lifecycle to `_Seat` (currently
`sidequest/server/session_room.py:30`) — promote it from a `(player_id,
character_slot)` pair to a state-bearing dataclass:

```python
class LobbyState(StrEnum):
    CONNECTED = "connected"          # WS open, no PLAYER_SEAT yet
    CLAIMING_SEAT = "claiming_seat"  # PLAYER_SEAT sent, awaiting SEAT_CONFIRMED
    CHARGEN = "chargen"              # seat confirmed, CharacterBuilder active
    PLAYING = "playing"              # chargen committed, character in world
    ABANDONED = "abandoned"          # disconnected during chargen — reclaimable
```

Transitions (all must emit `lobby.state_transition` OTEL spans — see below):

| Trigger | From → To | Site |
|---------|-----------|------|
| `SessionRoom.connect()` | (new) → `connected` | `session_room.py:191` |
| `PLAYER_SEAT` received | `connected` → `claiming_seat` | `_handle_player_seat()` (find via grep) |
| `seat()` succeeds (SEAT_CONFIRMED emitted) | `claiming_seat` → `chargen` | `session_room.py:216` |
| `_chargen_confirmation()` success path (post-`builder.build()`) | `chargen` → `playing` | `session_handler.py:~2597` |
| `disconnect()` while in `chargen` | `chargen` → `abandoned` | `session_room.py:206` |
| `disconnect()` while in `playing` | `playing` → `playing` (paused — keep slot held; existing `is_paused()` semantics at `session_room.py:299` survive intact) | `session_room.py:206` |

**Reuse, don't reinvent:** `connected_player_ids()` (line 224),
`seated_player_ids()` (line 228), and `absent_seated_player_ids()` (line 232)
already exist. Add a sibling `playing_player_ids() -> list[str]` that filters
on `state == PLAYING`. Do NOT delete the existing predicates — `is_paused()`
and the pause-banner UI rely on `absent_seated_player_ids()`.

### Turn barrier predicate (THE FIX)

`session_handler.py:3222` currently calls `room.seated_player_count()`. After
this story:

```python
# OLD:
turn_manager.set_player_count(room.seated_player_count())
# NEW:
turn_manager.set_player_count(room.playing_player_count())
```

`TurnManager.submit_input()` at `sidequest/game/turn.py:85–93` does not need
to change — its predicate is unchanged, only the input count moves.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Define in `sidequest/telemetry/spans.py` and register routes in `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `lobby.state_transition` | `player_id`, `from_state`, `to_state`, `reason` | every transition site listed above |
| `lobby.seat_abandoned` | `player_id`, `character_slot`, `from_state` (always `"chargen"`) | `disconnect()` when transitioning to `abandoned` |
| `barrier.wait` | `lobby_participant_count` (sum across all non-`abandoned` states), `active_turn_count` (= `playing` count), `submitted_count`, `interaction_id` | every call to `_dispatch_structured_round()` after `submit_input()` even when the barrier does NOT fire — Sebastien needs to see the wait state, not just the fire state |

The `barrier.wait` span must fire on **every barrier check**, not only on
"barrier_fired". A wait that never fires is exactly the bug being fixed; if
the span only emits on fire, the GM panel can't see why the wait persists.

The existing `mp.barrier_fired` watcher event (`session_handler.py:3228`) and
`mp.round_dispatched` (line 3256) are unchanged — they are downstream of the
wait check.

### Out-of-scope dimensions (DO NOT IMPLEMENT)

- **#1 timeout-based pruning** — explicitly rejected. Timeouts are racy and
  punish slow players (Alex). If a real disconnect-during-play case appears in
  playtest, a follow-up story can layer timeout pruning on top of the state
  machine.
- **#2 round-0 heuristic** — explicitly rejected. The "advanced past round 0"
  proxy doesn't address chargen-abandonment (the actual evropi failure).

### Reuse, don't reinvent

- `_Seat` dataclass exists at `session_room.py:30` — extend with `state` field;
  do not create a parallel state map.
- `is_paused()` at `session_room.py:299` is the existing predicate the UI's
  pause banner reads. It is a function of `absent_seated_player_ids()` and must
  continue to return True for `playing`-but-disconnected peers. Do not collapse
  pause-state and barrier-state — they are distinct.
- `_FakeClaudeClient` at `tests/server/conftest.py:195` lets chargen complete
  without an LLM call. Use it.
- `session_handler_factory()` at `tests/server/conftest.py:330` is the
  multiplayer test fixture. Use it for the wiring tests.

### Test files (where new tests should land)

- New: `tests/server/test_lobby_state_machine.py` — unit tests for the
  transitions and `playing_player_ids()` predicate.
- New or extend: `tests/server/test_mp_turn_barrier_active_turn_count.py` —
  the wire-first boundary test exercising the WS-driven scenario from playtest 3.
- Extend: `tests/server/test_seat_claim.py` — add `claiming_seat` →
  `chargen` transition assertions.
- Extend: `tests/server/test_chargen_dispatch.py` — add the
  `chargen` → `playing` transition on `_chargen_confirmation()` and the
  `chargen` → `abandoned` transition on `disconnect()` mid-chargen.

## Scope Boundaries

**In scope:**

- New `LobbyState` enum and state field on `_Seat`.
- New `SessionRoom.playing_player_ids()` / `playing_player_count()` predicate.
- State transitions at the five sites named in Technical Guardrails.
- Replace `room.seated_player_count()` with `room.playing_player_count()` at
  `session_handler.py:3222`.
- New OTEL spans `lobby.state_transition`, `lobby.seat_abandoned`,
  `barrier.wait` (+ register `SPAN_ROUTES` entries).
- Wire-first boundary test reproducing the evropi scenario: 4 lobby
  connections, 1 reaches `playing`, 3 disconnect during chargen → barrier
  fires after only the 1 active player submits.
- Unit + integration tests covering each transition trigger.

**Out of scope:**

- **Dimensions #1 and #2** (timeout pruning, round-0 heuristic) — see Technical
  Guardrails.
- Changing the pause-banner / `is_paused()` semantics. `playing`-but-
  disconnected peers continue to pause the game; they are NOT abandoned.
- UI changes (pause banner, lobby view). The `barrier.wait` span feeds the GM
  panel, which is server-side observability only. UI sees the same
  `mp.barrier_fired` / `mp.round_dispatched` events as today.
- Reconnection flow for an `abandoned` slot. If a player who abandoned during
  chargen reconnects, today's behavior (claim a fresh seat) survives. A
  follow-up could let them resume their abandoned slot, but that is its own
  design.
- Migration / persisted-storage concerns. State is in-memory on `_Seat`; not
  serialized to save files.

## AC Context

The story's title carries the contract; we expand it into testable ACs:

1. **Turn barrier fires when only `playing` peers have submitted, regardless of
   how many are merely connected.**
   - Test: 4 WS peers connect; 1 completes chargen and submits a turn; the
     other 3 stay in `chargen` (or disconnect mid-chargen). Assert
     `mp.barrier_fired` fires after the 1 submission, not blocked.
   - Negative test: the same scenario where the 3 are in `playing` (e.g.,
     reconnected after chargen) — barrier should still wait until all 4
     submit. Distinguishes correctness from "always fire on 1."

2. **Lobby state transitions are explicit and observable.**
   - Test: drive each transition (connect → claim → confirm → chargen → playing,
     plus chargen → abandoned via mid-chargen disconnect) and assert
     `_Seat.state` reflects the new value at each step.
   - Wire-first: the transitions are driven by real WS messages /
     `_chargen_confirmation()` calls, not by directly mutating `_Seat`.

3. **Chargen-abandonment cancels the seat (transitions to `abandoned`).**
   - Test: peer connects, claims seat, enters chargen, disconnects WS before
     `_chargen_confirmation()` fires. Assert `_Seat.state == ABANDONED` and
     the seat is no longer counted by `playing_player_count()` or
     `seated_player_count()` filtered on non-`abandoned`.
   - Negative test: peer in `playing` disconnects → seat stays held,
     `is_paused()` returns True, slot is NOT counted as abandoned.

4. **OTEL `barrier.wait` span fires on every barrier check with both counts.**
   - Test: trigger 3 barrier waits across a session (1 fires, 2 are still
     waiting). Assert the span fires 3 times and each carries
     `lobby_participant_count` and `active_turn_count`. Sebastien's lie
     detector requires both — the divergence is the story.
   - Test: verify SPAN_ROUTES registers the watcher mapping, so events reach
     the GM panel.

5. **`lobby.state_transition` and `lobby.seat_abandoned` spans fire at the
   correct sites with correct attributes.**
   - Test: drive each transition, assert the corresponding span fires once
     with `from_state`, `to_state`, `player_id` (and `reason` where
     applicable). Mid-chargen disconnect must produce both
     `lobby.state_transition (chargen→abandoned)` AND `lobby.seat_abandoned`
     (the latter is the convenience event for GM-panel filtering).

6. **Existing pause semantics preserved.**
   - Negative / regression test: a `playing` peer disconnecting still triggers
     `is_paused() == True`, still appears in `absent_seated_player_ids()`,
     and the pause-banner state-mirror message still emits as today. The new
     state machine is **additive** — it must not break the existing pause UX.
