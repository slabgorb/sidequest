---
parent: context-epic-67.md
workflow: tdd
---

# Story 67-2: ACTION_REVEAL delivery resilience — retry/backfill on reconnect so a sealed peer never stalls at "Composing"

## Business Context

In the playgroup, the submit-and-wait barrier (ADR-036) is the social contract that lets Alex take his time without being rushed. The flip side: when a peer **has** sealed, the table needs to *see* it — otherwise the other players sit watching "Adam Composing…" while Adam is actually done and the narrator is already building the resolution. That is exactly what the 2026-05-27 ping-pong run caught in `beneath_sunden` MP (finding `[BUG] ws.send_failed type=ACTION_REVEAL → peer-presence desync`): Adam sealed, the server recorded his submission and started the prompt, but Eve's tab stayed pinned on "Adam Composing… (1/2) / Waiting on Adam to act…" because the `ACTION_REVEAL` broadcast that flips a peer to "Sealed" raced a transient socket state and never arrived. The turn resolved correctly server-side — this is a **presence-display** bug, not a barrier-logic bug — but a stranded "Composing" indicator erodes trust in the barrier and invites a confused re-submit.

This story makes peer-seal visibility **self-healing**: a dropped reveal/status frame must be recoverable, so a sealed peer never strands the table at "Composing" — without reinventing the event-sourced replay machinery 67-1 already leans on.

## Root Cause (measured during recon — what actually breaks)

The strand is the intersection of three facts in the current code:

1. **`ACTION_REVEAL` and `TURN_STATUS` are fire-and-forget, not event-sourced.** `ActionRevealHandler.handle` (`sidequest-server/sidequest/handlers/action_reveal.py:120`) and the per-player seal signal in `_emit_player_action` (`sidequest-server/sidequest/handlers/player_action.py:587`, `status="submitted"`) both deliver via `SessionRoom.broadcast()` (`session_room.py:865`), which `put_nowait`s onto each socket's outbound queue and returns. Neither calls `emit_event` / `event_log.append`. There is **no per-connection retry, no ack, and no seq-gap detection** at the queue→socket boundary.

2. **The actual delivery failure is at the socket-write layer.** `_send_message` (`sidequest-server/sidequest/server/websocket.py:226-252`) drains the queue and `await websocket.send_text(...)`; on exception it logs `ws.send_failed type=ACTION_REVEAL error=` and **drops the frame** (no requeue, no recipient-drop watcher event — the empty `error=` is a transient socket state during reconnect churn). Note 67-1's sibling fix added `broadcast.recipient_dropped` telemetry to the *event-sourced* `emitters._deliver_fanout` path; `SessionRoom.broadcast` (used by reveal/status) is a **separate, un-instrumented path** that does not get that coverage.

3. **Reconnect-replay does not carry seal state.** The connect.py replay path (`sidequest-server/sidequest/handlers/connect.py:1137-1255`) replays only **event-log / projection-cache** rows, rebuilt through `_build_message_for_kind` (`sidequest-server/sidequest/server/session_handler.py:173-217`), whose kind table is `NARRATION`, `NARRATION_SEGMENT`, `CONFRONTATION`, `SECRET_NOTE`, `SCRAPBOOK_ENTRY`. `ACTION_REVEAL` and `TURN_STATUS` are **not** in that set and are never written to the event log — so a reconnecting (or never-received) peer gets **no backfill** of who has sealed. There is also no re-derivation of the live `build_turn_status_roster` on connect.

**Net:** if the single `ACTION_REVEAL{submitted}` frame AND the authoritative `TURN_STATUS{submitted}` frame are both missed (same socket-churn window), the peer has no signal and no recovery channel, and stalls at "Composing" until the next round's broadcast — which may never come once everyone has sealed and the table is waiting on resolution.

## What Already Exists (do NOT reinvent — CLAUDE.md "Wire up what exists")

- **`TURN_STATUS` is the server-authoritative seal channel; `ACTION_REVEAL` is best-effort visibility.** The UI already encodes this precedence: `mergePeerRevealsWithSubmittedStatus` + `computeSubmittedPlayerIds` (`sidequest-ui/src/lib/turnStatusDerivation.ts`) and `PeerRevealList`'s `sealedPlayerIds` prop (`sidequest-ui/src/components/PeerRevealList.tsx:46-69`) already force a row to "✓ Sealed" when `TURN_STATUS` says submitted even if `ACTION_REVEAL` is stale/missing. **The resilient channel to harden is `TURN_STATUS`, not `ACTION_REVEAL`'s text** — recover the *seal fact*, and the existing UI merge surfaces it.
- **`build_turn_status_roster(snapshot, playing_player_ids)`** (`sidequest-server/sidequest/server/turn_status_roster.py`) already computes the canonical pending/submitted roster from durable state (the per-room pending-action buffer / barrier `_submitted` set). The seal fact is **reconstructible at any time** from `SessionRoom` + snapshot — no new persistent store needed.
- **Per-`(socket_id, round)` seq monotonicity** already exists for `ACTION_REVEAL` server-side (`action_reveal.py:43,76-82,121`) and client-side (`usePeerReveals.ts` `lastSeq`), and the wire payload already carries `seq` + `round` (`docs/api-contract.md:449-466`). Any gap-detection design should build on this, not invent a new sequence space.
- **Reconnect-replay scaffold** (`connect.py:1112-1271`, `since_seq` cache read + tail-backfill + replay OTEL span `slug_connect.replay.*`). The fix is to **add the seal-state recovery to this existing on-connect path**, not to build a parallel reconnect mechanism.
- **`SessionRoom.broadcast` returns the actually-queued `(socket_id, player_id)` list** (`session_room.py:865-892`) — the lie-detector ground truth already exists for detecting a recipient whose queue diverged from `_connected`.

## Technical Guardrails

**Verify-and-close-the-gap, do NOT rebuild.** The recovery substrate (reconnect path, canonical roster builder, UI TURN_STATUS precedence) is present. The TDD work is to (a) write failing tests that reproduce a dropped seal frame stranding a peer at "Composing", then (b) close the specific recovery gap — recommended: **on (re)connect, re-derive and send the current `build_turn_status_roster` to the connecting socket** so seal state is always reconciled, plus instrument the `SessionRoom.broadcast`/`_send_message` drop so it stops being silent.

**Recommended approach (Architect decision — Dev/TEA to confirm scope with SM):**
1. **Server, primary fix — reconcile seal state on connect.** In `connect.py`, after the existing replay loop, build the live roster via `build_turn_status_roster(snapshot, room.playing_player_ids())` and send a `TURN_STATUS` frame (status reflecting the in-flight round, e.g. `submitted` entries for already-sealed peers) to the *connecting socket only*. This makes seal state **idempotently recoverable** on every reconnect regardless of which transient frame was dropped — the same "persist server-side, let reconnect replay" doctrine 67-1 follows, applied to seal presence. This is preferred over a per-frame ACTION_REVEAL retry queue because the roster is cheap to recompute and the UI already treats TURN_STATUS as authoritative.
2. **Server, observability fix — kill the silent drop.** Make the `SessionRoom.broadcast` → `_send_message` drop loud: emit a watcher event (mirror 67-1's `broadcast.recipient_dropped`, `component=multiplayer`/`broadcast`, `severity=warning`, carrying `recipient_player_id` + message `type`) when an outbound queue/socket has gone for an *included* recipient. This satisfies the OTEL lie-detector mandate — a dropped reveal must be visible on the GM panel, not an empty `error=`.
3. **(Evaluate, do NOT default to)** a per-frame ACTION_REVEAL/TURN_STATUS retry-on-send. Only pursue if (1)+(2) prove insufficient — e.g. if the drop happens on a connection that does *not* reconnect. Flag to SM before adding a retry queue; the connect-time reconcile covers the observed repro (the peer's socket churned and re-settled).

**Constraints:**
- **ADR-104/105 perception firewall.** Seal presence is membership-level, not canonical content — recovering "Adam has sealed" leaks nothing Adam's text would. But the connect-time roster send must go through the *same* projection discipline as any other on-connect frame; do not bypass the firewall to ship the roster. Reveal **text** (`ACTION_REVEAL.action`) is OOC table-talk visible per ADR-036's 2026-05-03 amendment, so backfilling it is allowed — but if scope creeps to re-sending text, keep it inside the firewall path.
- **No silent fallbacks (CLAUDE.md).** The current empty-`error=` drop is exactly the anti-pattern; the fix must surface the failure via OTEL.
- **OTEL proof required.** Emit a watcher event on the recover/reconcile seam so the GM panel confirms the fix engaged (e.g. `turn_status.reconciled_on_connect` or reuse the `slug_connect.replay.*` span with a seal-roster attribute).
- **Every test suite needs a wiring test** — prove the recovery path is reachable from the real `connect` handler / real `SessionRoom`, not just unit-green helpers. Per server CLAUDE.md, prefer OTEL-span or fixture-driven behavior tests; **no source-text grep wiring tests**.
- **Do not weaken the barrier.** This is display/presence recovery only. The CAS-guarded dispatcher and `submit_input` barrier are untouched (the repro confirms the turn already resolved server-side). Do not let recovery logic shorten anyone's response window (Alex).

## Scope Boundaries

**In scope:**
- Server: make peer-seal presence recoverable so a dropped `ACTION_REVEAL{submitted}` / `TURN_STATUS{submitted}` cannot permanently strand a peer at "Composing" — recommended via connect-time re-derivation + send of the canonical turn-status roster.
- Server: replace the silent `ws.send_failed`/`broadcast` drop with a loud OTEL watcher event for an included-but-undeliverable recipient on the `SessionRoom.broadcast` path.
- UI (only if needed): ensure the reconnect/connect handshake consumes the reconciled `TURN_STATUS` and the existing `mergePeerRevealsWithSubmittedStatus` / `sealedPlayerIds` merge surfaces it — likely already wired (App.tsx:737-808 handles `TURN_STATUS.entries`); verify, don't redesign.
- OTEL watcher coverage on the recover/reconcile + drop-detect seams.

**Out of scope:**
- Reconnect-replay of in-flight **narration** turns / GameBoard-crash survival → **67-1** (sibling; this story assumes 67-1's persist+replay invariant holds and builds the seal-presence recovery alongside it).
- The "Composing / Sealed / Resolving" canonical-surface consolidation + slow-typist reassurance copy → **67-3** (that's labeling/UX; this is delivery recovery).
- MP player-vs-character identity mapping / doubled `X — X` header → **67-4**.
- The sticky "Server reconnecting — please retry your last action" banner that never auto-clears (a separate `[BUG]` in the same ping-pong run, line 76) — related UX but a different state flag; do not fold in without SM sign-off.
- Reviving any retired ACTION_REVEAL antecedent passes / POV concerns (unrelated findings in the same file).

## AC Context

(Story body carries no ACs; derived from epic 67 + the ping-pong `ws.send_failed` finding. TEA to confirm the test list with SM before locking.)

1. **A dropped seal frame does not permanently strand a peer at "Composing."** *Test (server, fixture-driven):* construct a 2-player room where player A has sealed (`submit_input` recorded, roster shows A `submitted`); simulate the `ACTION_REVEAL{submitted}` + `TURN_STATUS{submitted}` to peer B being dropped (B's outbound queue gone during broadcast). Assert that B's recovery path yields the authoritative submitted roster for A (B can no longer be stranded).
2. **Reconnect reconciles current seal state.** *Test:* peer B reconnects mid-round (A already sealed, turn not yet resolved); assert B receives a `TURN_STATUS` frame whose entries mark A `submitted`, derived from `build_turn_status_roster` — without relying on a replayed ACTION_REVEAL.
3. **Recovered seal state flows to the UI merge.** *Test (UI):* given a `TURN_STATUS` with A `submitted` arriving after a missed ACTION_REVEAL, `mergePeerRevealsWithSubmittedStatus` / `sealedPlayerIds` render A's `PeerRevealList` row as "✓ Sealed" (override the stale/absent composing state). Confirm App.tsx's `TURN_STATUS.entries` handling feeds this.
4. **The drop is no longer silent.** *Test (OTEL):* drive a broadcast where one included recipient's queue/socket is gone; assert a watcher event fires (`component=multiplayer`/`broadcast`, carries `recipient_player_id` + message `type`) instead of only the bare `ws.send_failed` log.
5. **Recovery is observable on the GM panel.** *Test (OTEL):* the connect-time seal reconcile emits a watcher span/attribute (e.g. `turn_status.reconciled_on_connect` or a `slug_connect.replay.*` seal attribute) so the fix's engagement is verifiable.
6. **Barrier + dispatch are untouched.** *Test:* the resolved-turn outcome is identical with and without a dropped seal frame — recovery is display-only; no double-dispatch, no shortened window, CAS dispatcher unaffected.

**Edge cases to probe:**
- Both seal frames (ACTION_REVEAL + TURN_STATUS) dropped in the same churn window (the literal repro) vs. only one dropped (UI merge already covers the one-dropped case via `sealedPlayerIds`).
- Multi-socket player where only one socket missed the frame (ref-counted presence — `session_room.disconnect` :448-571) — reconcile must target the right socket.
- Seal frame dropped *after* the barrier already fired (`barrier_fired` path, player_action.py:568-574 sends an all-submitted projection) — reconcile must not regress a sealed peer back to pending.
- Round boundary: a recovered roster for round N must not pin stale state into round N+1 (usePeerReveals round-flush + `TURN_STATUS{resolved}` clear at App.tsx:758-766 already handle the resolved clear).
- 3–4 player rooms (roster denominator correctness; the canonical-roster wire-shape bugs at App.tsx:740-752 are prior art for off-by-one risk).

## Assumptions

- **The seal fact is reconstructible from `SessionRoom` + snapshot at connect time** via `build_turn_status_roster`. If recon finds the pending-action buffer / barrier `_submitted` set is already cleared by the time a peer reconnects (so the roster can no longer report who sealed this round), that widens scope to a durable per-round seal record — **log a Design Deviation and notify SM** rather than persisting blind.
- **TURN_STATUS, not ACTION_REVEAL, is the recovery target.** The UI already treats TURN_STATUS as authoritative (`turnStatusDerivation.ts`), so recovering the seal fact is sufficient; recovering reveal *text* is a nice-to-have, not required to clear the strand. If SM wants text recovered too, that's an explicit scope add.
- **67-1's persist+replay invariant is the trusted base.** This story adds seal-presence reconciliation to the same on-connect path; it does not re-solve turn survival.
- **`SessionRoom.broadcast` is the correct seam to instrument**, distinct from the already-instrumented `emitters._deliver_fanout` event-sourced path (67-1). If Dev finds reveal/status should instead be routed through `emit_event` to inherit existing telemetry + replay, that is a larger architectural change — **flag to SM** before re-routing, as it touches the perception-projection contract for these frame types.
