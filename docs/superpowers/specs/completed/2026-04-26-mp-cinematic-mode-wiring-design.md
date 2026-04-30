# Wire ADR-036 Cinematic Mode in `_handle_player_action`

- **Spec date:** 2026-04-26
- **Author:** Architect (The Man in Black)
- **Source finding:** [S5-ARCH] in `/Users/slabgorb/Projects/sq-playtest-pingpong.md`
- **Related ADRs:** ADR-036 (Multiplayer Turn Coordination), ADR-006 (Two-Tier Turn Counter), ADR-082 (Rust → Python port), ADR-067 (Unified Narrator)
- **Status:** approved by user 2026-04-26, awaiting implementation plan

## Problem

In multiplayer rooms, every player's WebSocket submission triggers its own
narrator dispatch immediately. When two players each take a turn, the narrator
runs twice in parallel, each call seeing only the submitting player's action.
Players receive disjoint responses; neither narration acknowledges the other
player's action. Verified live in the 2026-04-26 caverns_and_claudes/grimvault
session — see `[S5-ARCH]` in pingpong.

The peer-turn UI (`turn_status_active` broadcast cycling between submitters)
gives the *appearance* of waiting for both players, but the dispatch loop
underneath is FreePlay mode (ADR-036 nomenclature): per-submission narration,
not per-round.

## Root Cause

ADR-036 specified three turn modes: FreePlay (current), Structured (barrier),
and Cinematic (sealed-letter / simultaneous reveal). The Rust implementation
had `TurnBarrier` (`tokio::sync::Notify`) plus claim-election (`AtomicU64`
CAS) to support Cinematic mode.

The Python port (ADR-082, ~3 weeks ago) carried over the `TurnManager.submit_input()`
barrier API at `sidequest-server/sidequest/game/turn.py:93–101` but did **not**
re-implement the dispatch-side wiring. `grep -rn submit_input
sidequest-server/sidequest --include='*.py' | grep -v tests` returns only
the definition — zero production callers.

`_handle_player_action` in `sidequest/server/session_handler.py:3380–3461`
calls `_execute_narration_turn(action)` immediately on every submission. The
TurnManager barrier is dead code in production.

## Goals

1. Multiplayer rooms with N seated players run the narrator **once per round**,
   with all players' actions visible in a single combined input.
2. Solo rooms (`seated_player_count == 1`) keep their current behavior — zero
   barrier overhead, immediate dispatch on submission.
3. Reuse the existing `TurnManager.submit_input` barrier; do not invent new
   primitives where the framework already has them.
4. Preserve every working multiplayer signal Keith called out: `turn_status_active`
   broadcasts per submission, pause-gate on disconnect, LocalDM decompose
   pipeline.

## Non-Goals (deferred)

1. **Adaptive timeout** — round blocks indefinitely until all seated players
   submit. Aligns with Alex (slow typist) protection from CLAUDE.md primary-audience
   design. ADR-036's `AdaptiveTimeout` + "remains silent" default deferred to a
   later story.
2. **ADR-028 perception rewrites** — every player receives the same canonical
   narration text in v1. Per-player perception splits land in a follow-up.
3. **Retry on narrator failure** — if Claude CLI errors out mid-dispatch, the
   round stays open and the elected handler surfaces the error. Auto-retry
   semantics deferred. The GM panel will see the failed round via existing
   error-path OTEL.
4. **Combat / sealed-letter dogfight interaction** — `dispatch/sealed_letter.py`
   (red/blue maneuver resolution) is unrelated to this round-level barrier and
   continues to function unchanged. Nesting (a multi-player round during a
   sealed-letter dogfight encounter) is theoretically possible but out of scope
   for v1 — file as known limitation.

## Design

### Action shape

Combined actions are concatenated prose. The narrator-facing contract
(`orchestrator.run_narration_turn(action: str, ...)`) does **not** change.
The dispatcher builds:

```
Gladstone: I prepare for the dungeon.
Zanzibar Jones: I get my pole.
```

— and passes that string into the existing pipeline. The narrator's persistent
session (ADR-067, Opus) parses labeled prose without difficulty; party context
is already injected as natural-language sentences in the prompt framework.

### Dispatch model: last-submitter-runs

Every player's WebSocket handler writes its action into a per-room buffer and
calls `TurnManager.submit_input(player_id)`. When that call flips the phase
from `InputCollection` to `IntentRouting`, the submitting handler has just
been elected to run the narrator.

An `asyncio.Lock` plus a `last_dispatched_round: int` counter on the room
guarantee exactly one dispatch per round even if two submissions race.

Solo path: with one seated player, `submit_input` flips the phase on the very
first call, so the same single submitter immediately enters the dispatch
branch. Zero overhead.

### Components — what changes, what doesn't

**Modified — `sidequest/server/session_room.py`** (the multiplayer room — class `SessionRoom`):

- New field `pending_actions: dict[str, PendingAction]` — keyed by `player_id`.
  `PendingAction` is a small dataclass `{character_name: str, action: str}`.
  Resolving the character name **at submit time** (while the submitter's
  `_SessionData` is in scope) lets us reuse the existing
  `_resolve_acting_character_name(sd, room)` helper from
  `sidequest/server/session_helpers.py:116` unchanged. The elected branch then
  reads the already-resolved name back from the buffer instead of trying to
  re-resolve foreign `player_id`s without their session data. Initialized empty.
- New field `dispatch_lock: asyncio.Lock` — election primitive. Initialized in
  `SessionRoom.__init__`.
- New field `last_dispatched_round: int` — CAS-check counter, initialized to `0`.
- New helper `record_pending_action(player_id: str, character_name: str, action: str) -> None` —
  sets `pending_actions[player_id] = PendingAction(character_name, action)`.
  Last-write-wins on duplicate submissions for the same player_id (covers
  "I changed my mind" — explicit feature, see Error Handling §2.5).
- New helper `drain_pending_actions() -> list[tuple[str, PendingAction]]` —
  returns the buffer as `[(player_id, pending), ...]` ordered by submission
  order, then clears the buffer. Order matters because the combined-prose
  builder uses it to label speakers.
- New helper `seated_player_count() -> int` — returns `len(self.seated_player_ids())`.
  (Pure convenience over the existing accessor; collapses one call site.)

**Modified — `sidequest/server/session_handler.py:_handle_player_action`** (around lines 3380–3461):

After the existing `turn_status_active` broadcast (lines 3429–3458, do not
touch this block), if `self._room is not None`:

1. Resolve the submitter's character name with the existing helper:
   `acting_name = _resolve_acting_character_name(sd, self._room)`. (This call
   already happens at line 3431 for the broadcast — reuse the same value;
   don't double-call.)
2. `self._room.record_pending_action(sd.player_id, acting_name, action)`
3. `snapshot.turn_manager.set_player_count(self._room.seated_player_count())`
   — keeps barrier player_count in sync with dynamic seating.
4. `snapshot.turn_manager.submit_input(sd.player_id)`
5. If `snapshot.turn_manager.get_phase() == TurnPhase.InputCollection` →
   return `[]`. The handler's work is done; broadcasts handle delivery.
6. Else (barrier fired) → enter the **dispatch-elected branch**:

```python
async with self._room.dispatch_lock:
    current_round = snapshot.turn_manager.round
    if self._room.last_dispatched_round >= current_round:
        # Lost the race; another handler already dispatched this round.
        return []
    self._room.last_dispatched_round = current_round
    pending = self._room.drain_pending_actions()

combined_action = "\n".join(
    f"{p.character_name}: {p.action}" for _, p in pending
)
result = await self._execute_narration_turn(sd, combined_action, turn_context)
snapshot.turn_manager.record_interaction()
return result
```

Note: `sd` in the elected branch is the *electing handler's* SessionData. The
narrator sees a multi-player action via the combined-prose string; it does not
need to know which player's WebSocket triggered the dispatch. Persistence,
inventory updates, and location changes flow through the existing
`_apply_narration_result_to_snapshot` path — already handles party-wide state.

**Untouched (Keith's "don't mess with that" list):**
- `turn_status_active` broadcast block (`session_handler.py:3429–3458`).
- `room.is_paused()` / `absent_seated_player_ids()` pause gate (lines 3393–3414).
- `LocalDM.decompose` pipeline (lines 3504–3533).
- `orchestrator.run_narration_turn` signature.
- `_execute_narration_turn` body — receives the combined string, runs unchanged.
- All `dispatch/sealed_letter.py` red/blue dogfight machinery.

### Data flow

```
Gladstone WS                          SessionRoom                       Zanzibar WS
    │                                       │                                 │
    │── action: "I prepare for dungeon" ────┤                                 │
    │  broadcast turn_status_active=Glad    │                                 │
    │  record_pending_action(glad, "...")   │                                 │
    │  turn_manager.set_player_count(2)     │                                 │
    │  turn_manager.submit_input(glad)      │                                 │
    │  phase still InputCollection          │                                 │
    │  return [] ───────────────────────────┤                                 │
    │                                       │                                 │
    │                                       │── action: "I get my pole" ──────┤
    │                                       │  broadcast turn_status_active   │
    │                                       │  record_pending_action(zan,...) │
    │                                       │  turn_manager.submit_input(zan) │
    │                                       │  phase → IntentRouting          │
    │                                       │  acquire dispatch_lock          │
    │                                       │  CAS last_dispatched_round      │
    │                                       │  drain → [(glad,...),(zan,...)] │
    │                                       │  combined_action = "Gladstone:  │
    │                                       │    ...\nZanzibar Jones: ..."    │
    │                                       │  await _execute_narration_turn  │
    │                                       │  ──── Claude CLI ~15s ────      │
    │                                       │  broadcast NARRATION (all)      │
    │                                       │  record_interaction()           │
    │                                       │  return [] ─────────────────────┤
    │                                       │                                 │
    ▼                                       ▼                                 ▼
```

Solo timeline (`seated_player_count == 1`): `submit_input` flips phase on
first call → handler enters dispatch branch immediately → single
`_execute_narration_turn` call → broadcast → done. Identical observable
behavior to today.

### Error handling

1. **Player disconnects after submitting, before barrier fires.** The pause
   gate (existing) flips `is_paused()` true on disconnect, so subsequent
   submissions from other players hit `GAME_PAUSED`. Buffered actions stay
   in `pending_actions` (room-scoped, survives the disconnect). On reconnect,
   the pause gate clears and the absent player's submission flows normally;
   if their action is buffered (they submitted *before* disconnecting), the
   barrier fires when the *other* outstanding player(s) submit.
2. **Player disconnects before submitting at all.** Pause gate returns
   `GAME_PAUSED` for new submissions; the round simply doesn't advance. Other
   players' buffered actions wait. On reconnect, the player submits and the
   barrier fires.
3. **Narrator dispatch fails (Claude CLI error / timeout / OOM).** The
   elected handler's `await _execute_narration_turn(...)` raises. The
   `record_interaction()` call is never reached, so the round does NOT
   advance. `last_dispatched_round` is set *before* the dispatch, so a
   re-attempt would see the CAS already claimed and refuse — **known
   limitation**: the round is stuck and requires manual intervention (server
   restart or admin action). v1 surfaces this via existing error-path OTEL;
   resilient retry is a follow-up story. File for Sebastien — he'll see it
   in the GM panel.
4. **Race — two submissions arrive concurrently and both see `phase !=
   InputCollection` after `submit_input`.** Impossible in single-event-loop
   asyncio for a given coroutine, but coroutine-interleaving across awaits
   means two handlers could both reach the elected branch. The
   `dispatch_lock` serializes them; the CAS check on `last_dispatched_round`
   ensures only the first acquires the round. The loser's
   `drain_pending_actions` is *never called* (early return after lock check)
   — buffer is consumed exactly once per round.
5. **Same player submits twice in one round (e.g., quick double-send).** The
   `_submitted` set in `TurnManager` deduplicates by player_id (it's a `set`).
   The second `submit_input` call is a no-op on the barrier.
   `record_pending_action` overwrites the buffer entry — last-write-wins.
   Behavior: the player's most recent action is the one the narrator sees.
   This is an explicit feature, not a bug — it covers "I changed my mind"
   scenarios cleanly. Document in user-facing release notes.
6. **`set_player_count` shrinks mid-round (player unseats while others have
   buffered actions).** `TurnManager.submit_input` already handles this: the
   `_submitted` set is cleared on phase transition, and the next submission
   from a still-seated player will check `len(submitted) >= player_count`
   against the new count. If the unseated player had already submitted, their
   entry remains in `pending_actions` until drain — which is fine, they were
   present when they acted. We accept their buffered action even though they
   left.

### OTEL / Watcher events

Per CLAUDE.md "OTEL Observability Principle" — every subsystem decision must
be visible to the GM panel. Two new events:

- **`mp.barrier_fired`** — emitted in `_handle_player_action` when
  `submit_input` flips the phase. Payload:
  `{slug, round, player_count, submitted_player_ids}`.
- **`mp.round_dispatched`** — emitted in the elected branch, after the CAS
  succeeds, before `_execute_narration_turn`. Payload:
  `{slug, round, player_count, action_lengths: dict[player_id, int],
  combined_action_len}`.

Both events route through the existing `_watcher_publish(...)` helper used
elsewhere in `session_handler.py`. No new telemetry plumbing.

### ADR-036 status update

ADR-036 frontmatter currently reads `implementation-status: live`. After
this story lands, the field stays `live` but the ADR body needs an
`implementation-notes` block recording the Python-port gap and its
resolution:

> **Implementation notes (2026-04-26):** ADR-082 port to Python carried
> over `TurnManager.submit_input` (`sidequest-game/turn.py`) but did not
> re-wire the dispatch loop. `_handle_player_action` continued to dispatch
> per-submission until story `<TBD>` wired the barrier in
> `sidequest-server/sidequest/server/session_handler.py` and added
> `pending_actions` / `dispatch_lock` / `last_dispatched_round` to
> `SessionRoom`. The Cinematic mode now matches the original Rust design
> intent.

The Tech Writer (The Grandfather) updates this block as part of story
finish.

## Testing

Wiring tests are mandatory per CLAUDE.md — every test suite needs at least
one integration test that proves production code paths reach the new
component. Three minimum:

1. **`test_mp_barrier_combines_two_actions`** — End-to-end with mocked
   `orchestrator.run_narration_turn`. Two `_handle_player_action` calls in
   sequence with different `player_id`s in a 2-seat room. Assert
   `run_narration_turn` was called **exactly once** and the action argument
   contains both player names with their respective action texts.
2. **`test_mp_solo_dispatches_immediately`** — Single seated player, one
   `_handle_player_action` call. Assert `run_narration_turn` called exactly
   once on the first submission, `last_dispatched_round` advanced from 0 to
   1, no buffering observable to the test.
3. **`test_mp_election_serializes_concurrent_dispatch`** — Two
   `_handle_player_action` calls awaited concurrently via `asyncio.gather`.
   Assert `run_narration_turn` called exactly once. Verifies
   `dispatch_lock` + CAS election under coroutine interleaving.

Plus light-touch:

4. **`test_mp_player_action_overwritten_by_later_submission`** — Same
   `player_id` calls `record_pending_action` twice with different texts;
   `drain_pending_actions` returns only the second text. Codifies the
   last-write-wins feature.
5. **`test_mp_pause_gate_buffers_survive_disconnect`** — Player A submits;
   player B disconnects (room enters paused state); player A's buffered
   action remains; on B reconnect + submit, barrier fires and combined
   action contains A's original buffered text.

Tests live in `sidequest-server/tests/server/` alongside the existing
`test_render_dispatch.py` / `test_session_handler_decomposer.py` neighbors.

## Risks

- **Asymmetric WS reply timing.** The last-submitter-runs pattern means the
  electing handler's WS reply takes 10–20s longer than the earlier
  submitters'. Cosmetic — broadcasts deliver everything; players don't see
  their handler "wait." Documented in case it surfaces in load testing.
- **Stuck round on narrator failure.** §2.3 above. v1 documents this as a
  known limitation with admin-intervention recovery. The retry-on-failure
  story should land before any "Cinematic mode in production for real" milestone.
- **`set_player_count` change midway through a round.** §2.6 covers it but
  the failure mode is subtle. Test 5 (`test_mp_pause_gate_buffers_survive_disconnect`)
  exercises the related disconnect/reconnect path; an additional test for
  the unseat-mid-round case is recommended.

## Estimated scope

This is a single sprint story. Code surface:
- `sidequest-server/sidequest/server/session_room.py` — three new fields,
  three new helpers, ~30 lines.
- `sidequest-server/sidequest/server/session_handler.py:_handle_player_action`
  — ~25 lines added (buffer + barrier + elected branch), zero deletions.
- `sidequest-server/tests/server/` — 3 mandatory + 2 recommended wiring tests,
  ~150–200 lines of test code.
- `docs/adr/036-multiplayer-turn-coordination.md` — implementation-notes
  block update, ~10 lines.

No content (genre packs / world data) changes. No UI changes. No daemon
changes.

## Definition of done

1. All five tests pass under `just server-test`.
2. Live verification with Keith and one peer in a 2-player Grimvault room:
   submit two actions, observe one narrator dispatch, both players see the
   same narration that integrates both actions.
3. OTEL: `mp.barrier_fired` and `mp.round_dispatched` events visible on the
   GM panel during the live verification.
4. ADR-036 implementation-notes block updated.
5. `[S5-ARCH]` entry in pingpong moved to "fixed (PR #N)" with the live
   verification details captured.
