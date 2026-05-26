---
parent: context-epic-67.md
workflow: tdd
---

# Story 67-1: GameBoard render crash must not orphan the table's turn — survive client subtree errors server-side

## Business Context

In a real playgroup session, one player's browser hitting a GameBoard render crash currently risks the **whole table's** in-flight turn. That is the worst class of multiplayer bug for this group: it punishes everyone for one person's local failure, and it directly violates the CLAUDE.md bar that one player's problem must never degrade the shared experience. This story makes the server the source of truth for turn survival: the turn is applied and persisted server-side independent of any single client rendering it, so a crashed client recovers by reconnect-replay and the rest of the table never notices.

## Technical Guardrails

**Verify-and-close-the-gap, do NOT reinvent.** Recon during setup found the substrate already largely exists. The TDD work is to (a) write failing tests that reproduce the orphaned-turn scenario, then (b) close whatever gap actually breaks, not rebuild working pieces. Key seams:

- **Server apply→persist (the invariant):** `sidequest-server/sidequest/server/websocket_session_handler.py` — `_handle_player_action()` (:3364) → `_execute_narration_turn()` (:3374) → persist via `_room.save()` / `sd.store.save(snapshot)` (:3996-4044). Confirm persistence is committed *before* the result depends on any single client's successful render.
- **Disconnect path:** `sidequest-server/sidequest/server/session_room.py` `disconnect(socket_id=...)` (:448-571) — ref-counted presence (multi-socket player not dropped on one socket close), ADR-036 action-visibility clearing (:551-570). Verify a mid-turn disconnect does NOT abort/clear the shared pending-turn state.
- **Reconnect replay:** `sidequest-server/sidequest/handlers/connect.py:1073-1270` — per-player filtered replay since `last_seen_seq` + tail-backfill of the last NARRATION block.
- **UI error boundary (already present):** `sidequest-ui/src/App.tsx:2019` wraps GameBoard in `ErrorBoundary name="Game"` (`components/ErrorBoundary.tsx`). The gap is likely that the boundary catches the crash but does not drive a clean reconnect to pick up the replay.
- **WS lifecycle:** `sidequest-ui/src/hooks/useWebSocket.ts` (onclose/reconnect :177-186) and `hooks/useGameSocket.ts`.

**Constraints:**
- ADR-104/105 perception firewall: reconnect-replay may only re-surface what the recovering player was entitled to see. Do not leak canonical/other-player state through the replay path.
- OTEL: emit a watcher event on the survive/persist/replay seam so the GM panel can confirm the fix engaged (CLAUDE.md OTEL principle). No silent fallbacks (CLAUDE.md).
- Every test suite needs a wiring test — prove the recovery path is reachable from production code, not just unit-green.

## Scope Boundaries

**In scope:**
- Server-side: guarantee the turn is applied + persisted and survives one client's render crash / mid-turn disconnect without orphaning the shared turn.
- Recovery: a crashed/reconnecting client replays the persisted in-flight turn; the rest of the table proceeds unaffected.
- OTEL watcher coverage on the survival/replay seam.
- Whatever minimal UI change is needed so the GameBoard ErrorBoundary recovery drives a clean reconnect (not a full UI presence redesign).

**Out of scope:**
- ACTION_REVEAL retry/backfill resilience → 67-2.
- Peer-visibility / "Composing/Sealed/Resolving" canonical surface + slow-typist reassurance → 67-3.
- Player-vs-character identity mapping / doubled `X — X` header → 67-4.

## AC Context

(Story body carries no ACs; derived from epic 67. TEA should confirm with SM before locking the test list.)

1. **Turn persists before client render dependence.** A turn applied server-side is committed to the SQLite save before the outcome hinges on any single client rendering it. *Test:* drive a turn, assert the persisted snapshot reflects the applied turn at the persist checkpoint independent of client ack.
2. **A GameBoard render crash does not orphan the table's turn.** *Test:* simulate one client's subtree error / socket drop mid-turn; assert the shared pending-turn state in `session_room` is intact and the other players' turn is not aborted.
3. **Reconnect replays the in-flight turn.** *Test:* reconnect the crashed client; assert it receives the persisted in-flight turn via the connect.py replay path (per-player filtered, tail-backfilled), and ends in sync.
4. **No perception leak on replay.** *Test:* in a 2-player session, assert the reconnecting player's replay contains only its own entitled events (ADR-104/105) — no canonical/other-player-only data.
5. **OTEL proof.** *Test:* a watcher event fires on the survive/persist or reconnect-replay seam so the GM panel shows the recovery engaged.

Edge cases to probe: multi-socket player where only one socket crashes (ref-counted presence must not drop the player); crash *during* the submit-and-wait barrier vs. after narration; the slow-typist window (don't let recovery logic shorten anyone's response window).

## Assumptions

- The apply→persist ordering at `websocket_session_handler.py:3996-4044` is already correct and the bug is in the recovery/teardown coupling, not the persist itself. If TEA finds persist happens *after* render-dependence, log a Design Deviation — that widens scope.
- The existing `connect.py` reconnect-replay path is the intended recovery mechanism (not a new wire message). If a new message type proves necessary, notify SM.
- `ErrorBoundary name="Game"` (App.tsx:2019) is the right UI seam; the fix is wiring its recovery to a clean reconnect, not adding a new boundary.
