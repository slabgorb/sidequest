---
story_id: "67-2"
jira_key: "67-2"
epic: "epic-67"
workflow: "tdd"
---
# Story 67-2: ACTION_REVEAL delivery resilience — retry/backfill on reconnect so a sealed peer never stalls at Composing

## Story Details
- **ID:** 67-2
- **Jira Key:** 67-2
- **Workflow:** tdd
- **Type:** bug
- **Points:** 3
- **Priority:** p2
- **Stack Parent:** none

## Story Context
This story is part of **Epic 67: Multiplayer resilience & presence** (Playtest-3 findings).

Full context available at: `sprint/context/context-story-67-2.md`

**Root Problem:** When a peer seals (submits their action), the table needs to see "Adam Sealed" immediately. Currently, if the `ACTION_REVEAL{submitted}` or `TURN_STATUS{submitted}` broadcast races a transient socket disconnect, the peer can be permanently stranded at "Adam Composing…" until resolution (or forever if everyone else has sealed).

**Business Impact:** This erodes trust in the turn barrier and invites confused re-submits.

**Recommended Fix (Architect):**
1. Server: on (re)connect, re-derive and send the current `build_turn_status_roster` so seal state is always reconciled
2. Server: replace the silent `ws.send_failed` drop with loud OTEL watcher events
3. UI: verify the existing `TURN_STATUS` merge in `mergePeerRevealsWithSubmittedStatus` surfaces recovered seal state (likely already wired)

**Scope:** See story context for in-scope vs. out-of-scope details. Key constraints: perception firewall (ADR-104/105), no silent fallbacks, OTEL proof required, every test must be a wiring test.

## Workflow Tracking
**Workflow:** tdd
**Phase:** green
**Phase Started:** 2026-05-27T20:23:07Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-27T20:06:50Z | 2026-05-27T20:09:14Z | 2m 24s |
| red | 2026-05-27T20:09:14Z | 2026-05-27T20:23:07Z | 13m 53s |
| green | 2026-05-27T20:23:07Z | - | - |

## SM Assessment

Setup complete. Story is well-scoped by the Architect's context doc — this is a **presence-display** bug, not a barrier-logic bug, which keeps the blast radius narrow. The fix hardens the *authoritative* `TURN_STATUS` roster channel on (re)connect rather than chasing dropped best-effort `ACTION_REVEAL` frames, which aligns with "wire up what exists" (the UI merge path is likely already in place).

**Routing to TEA (red phase).** TDD is the right call for a robustness bug: the red test must reproduce the stranded-at-Composing state by simulating a dropped `TURN_STATUS`/`ACTION_REVEAL` frame across a reconnect, then assert the reconnect-replay re-derives the roster. Per CLAUDE.md every test set needs a wiring test, and per the OTEL principle the silent `ws.send_failed` drop must gain a loud watcher event that the GM panel can verify.

**Carry-forward flag for Dev:** the central assumption is that the seal set is still queryable at peer-reconnect time. If `_submitted`/pending-action state is already cleared by then, scope widens to a durable per-round seal record — that's a Design Deviation trigger, not a silent expansion. TEA should write the red test in a way that surfaces which of these worlds we're in.

## Repositories & Branches
- **sidequest-server** (api): `feat/67-2-action-reveal-delivery-resilience`
- **sidequest-ui** (ui): `feat/67-2-action-reveal-delivery-resilience`

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (blocking): The connect-wiring test (AC2/AC5) cannot run without Postgres. Affects `sidequest-server/tests/server/test_seal_reconcile_on_connect.py` (Dev must run `just pg-up` and `uv run pytest tests/server/test_seal_reconcile_on_connect.py` before claiming GREEN — the local run skipped it, do not treat the skip as passing). *Found by TEA during test design.*
- **Question** (non-blocking): Once the barrier has fired (`recheck_barrier` via 67-1's crash-release path), a crashed/released awaiter who never submitted is still projected `submitted` by the all-submitted terminal projection. This matches the existing `player_action.py:568-574` behavior, so it's consistent — but if Dev finds the crash-release + reconnect combination needs a distinct status, flag to SM. Affects `sidequest-server/sidequest/server/turn_status_roster.py` (reconcile helper semantics). *Found by TEA during test design.*
- **Improvement** (non-blocking): `PeerRevealList` (sidequest-ui) only renders rows for peers already in the `reveals` map — a sealed peer with no ACTION_REVEAL gets no *reveal-text* row (the roster-driven TurnStatusPanel covers the seal indicator, so this is not a 67-2 strand). The reveal-text surface consolidation is explicitly 67-3 scope; noting so 67-3 picks it up. Affects `sidequest-ui/src/components/PeerRevealList.tsx`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The connect-time reconcile sends the full roster on EVERY MP reconnect, not only when a seal is outstanding. This is intentional (it also corrects the per-tab denominator), and cheap (roster recompute is O(players)), but a future optimization could skip the frame when the roster is all-pending. Affects `sidequest-server/sidequest/handlers/connect.py` (reconcile gate). *Found by Dev during implementation.*
- **Question** (non-blocking): The `broadcast.recipient_dropped` watcher now fires from `SessionRoom.broadcast` for ANY message type when a connected recipient lacks a queue — not just seal frames. This is correct (any silent drop is a blind spot) but will surface drops on narration/image broadcasts too during socket churn. If the GM panel gets noisy, consider rate-limiting or a per-type filter. Affects `sidequest-server/sidequest/server/session_room.py`. *Found by Dev during implementation.*

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev), confirmed by testing-runner (run_id 67-2-tea-red)

This is a presence-display recovery bug. I verified the Architect's load-bearing
assumption against the real code before writing a line: `room.bind_world`
(connect.py:638-642) makes the snapshot **canonical and shared** across MP
connections, and `_submitted` is runtime-only on that shared snapshot's
turn_manager — so a sealed peer's seal **survives a reconnecting peer's connect**
even though it never hits Postgres. **The assumption holds for the primary repro
(partial-seal, barrier still collecting).** It does NOT hold once the barrier
fires: `submit_input`/`recheck_barrier` (turn.py:96-98,119-122) clear `_submitted`
on the transition out of InputCollection. The existing terminal-projection guard
in `player_action.py:560-574` is the proof — the reconcile MUST apply the same
all-submitted projection when phase is past InputCollection or it will regress a
sealed table back to "Composing". My roster tests pin **both worlds** so Dev can't
ship a naive `_submitted`-read that strands the post-fire case.

**Test Files:**
- `sidequest-server/tests/server/test_seal_reconcile_roster.py` — pure helper
  `build_seal_reconcile_roster` (AC1 input-collection, AC1-edge barrier-fired
  terminal projection, AC1 3-player denominator, AC6 read-only/no-mutation).
- `sidequest-server/tests/server/test_broadcast_recipient_drop.py` — `SessionRoom.broadcast`
  must emit `broadcast.recipient_dropped` for a connected-but-queueless recipient
  (AC4). Mirrors 67-1's `test_emit_fanout_recipient_drop.py` on the **separate,
  un-instrumented** `broadcast` path.
- `sidequest-server/tests/server/test_seal_reconcile_on_connect.py` — WIRING:
  real `connect` handler + real `SessionRoom` + Postgres. Reconnecting peer's
  out_queue must carry a TURN_STATUS marking the sealed peer `submitted` (AC2),
  and the reconcile seam must emit a watcher event (AC5).
- `sidequest-ui/src/__tests__/seal-reconcile-surface-67-2.test.tsx` — AC3
  verification (already-wired surfaces).

**Tests Written:** 12 (4 server roster, 3 broadcast-drop, 2 connect-wiring, 4 UI) covering 6 ACs.

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | `test_connected_recipient_without_queue_emits_loud_watcher_event` (AC4) | failing (RED) |
| #4 logging coverage/severity (drop = warning) | same — asserts `severity="warning"` | failing (RED) |
| #6 test quality (no vacuous asserts) | self-checked all 12; assertions check values/sets, not truthiness | pass |
| #9 async pitfalls | connect-wiring tests `await` the handler; reconcile asserted read-only (AC6) so it can't block on a mutation | covered |

**Rules checked:** 4 of 14 applicable lang-review rules have test coverage (the
fix is delivery/observability — silent-fallback #1 and logging #4 are the load-bearing ones; #1/#4 ARE AC4).
**Self-check:** 0 vacuous tests found.

### RED Verification (testing-runner)

- `test_seal_reconcile_roster.py` → ImportError (`build_seal_reconcile_roster` missing) — expected RED.
- `test_broadcast_recipient_drop.py` → 1 fail (drop watcher not emitted) + 2 pass (guard cases already hold) — RED on the key assertion.
- `test_seal_reconcile_on_connect.py` → **could not run locally: Postgres not provisioned**. Dev MUST run with `just pg-up` (per SM sidecar gotcha "pg test env"). Test is written and reviewed; do not treat the skip as green.
- UI `seal-reconcile-surface-67-2.test.tsx` → 4/4 GREEN — verifies the reconciled roster surfaces correctly (TurnStatusPanel + derivation + App batch-entries seam). UI needs **no new code**; the work is server-side.

**Handoff:** To Dev (Major Winchester) for GREEN.

**Dev contract notes (read before implementing):**
1. **`build_seal_reconcile_roster(snapshot, playing_player_ids)`** is a *proposed*
   symbol/contract in `turn_status_roster.py`. The behavior is non-negotiable; the
   name is adjustable — but if you rename it, update `test_seal_reconcile_roster.py`
   and the unit import. The connect wiring test (AC2/AC5) asserts pure behavior
   (queue contents + watcher) and survives any internal naming.
2. **AC4 seam:** `SessionRoom.broadcast` (session_room.py:865) — the intended-recipient
   ground truth is `_connected` minus `exclude_socket_id`; a `_connected` player whose
   socket is absent from `_outbound_queues` is the drop. `_watcher_publish` is already
   imported (session_room.py:30). Match 67-1's shape: `field="broadcast.recipient_dropped"`,
   `recipient_player_id`, `type` (message type), `component`, `severity="warning"`.
3. **AC5 watcher name:** proposed `turn_status.reconciled_on_connect`. The test accepts
   `field`/`event`-keyed or any event_type containing "reconcile" — pick one and emit it.
4. **AC6 is a guardrail:** the reconcile read must NOT mutate `_submitted` or `phase`.
   Build into a local, send; never advance the barrier from the recovery path.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Proposed a new helper symbol (`build_seal_reconcile_roster`) rather than testing only the existing `build_turn_status_roster`**
  - Spec source: context-story-67-2.md, Technical Guardrails + Assumptions
  - Spec text: "on (re)connect, re-derive and send the current `build_turn_status_roster`"
  - Implementation: Tests target a NEW phase-aware helper, because `build_turn_status_roster` reads `_submitted` directly and returns all-pending once the barrier has fired (turn.py:98 clears `_submitted`). The barrier-fired terminal projection currently lives inline in `player_action.py:568-574` and is not reusable from connect.
  - Rationale: Reusing `build_turn_status_roster` unchanged would silently fail the post-barrier-fire reconnect (regress sealed peers to pending). A phase-aware reconcile builder is the honest contract; the unit test pins both phases.
  - Severity: minor
  - Forward impact: Dev adds one helper (or extends the existing one with phase-awareness); connect calls it. Name is adjustable per Dev contract note 1.
- **AC3 server-recommended UI work reduced to verification (no new UI code)**
  - Spec source: context-story-67-2.md, Scope Boundaries (UI "only if needed")
  - Spec text: "UI (only if needed): … likely already wired … verify, don't redesign"
  - Implementation: UI tests are GREEN regression/wiring guards, not RED.
  - Rationale: Confirmed TurnStatusPanel renders from the roster directly and App.tsx:798-808 already replaces entries on a batch TURN_STATUS — the reconcile's output surfaces with zero UI change.
  - Severity: minor
  - Forward impact: none — Dev's work is server-only unless a UI gap surfaces in GREEN.

### Dev (implementation)
- **Adopted TEA's proposed helper name `build_seal_reconcile_roster` verbatim**
  - Spec source: context-story-67-2.md, Technical Guardrails; TEA Dev-contract note 1
  - Spec text: "on (re)connect, re-derive and send the current roster … name is adjustable"
  - Implementation: Added `build_seal_reconcile_roster(snapshot, playing_player_ids)` to `turn_status_roster.py` exactly as TEA proposed — phase-aware (defers to `build_turn_status_roster` during InputCollection; projects all-submitted once the barrier fired). No rename, so no test edits needed.
  - Rationale: TEA's contract matched the existing terminal-projection precedent (player_action.py:568-574). No reason to diverge.
  - Severity: none (confirms spec)
  - Forward impact: none
- **Reconcile TURN_STATUS uses inert payload-level `status="pending"`**
  - Spec source: TEA test `test_reconnect_reconciles_sealed_peer_into_turn_status` (asserts `entries`, not payload status)
  - Spec text: "out_queue must carry a TURN_STATUS marking the sealed peer submitted"
  - Implementation: The reconcile frame sets payload `status="pending"` so the UI's TURN_STATUS handler hits NO transition branch and NO per-player push — only the batch-entries path (App.tsx:798-808) runs, replacing the roster cleanly. Seal truth rides `entries`.
  - Rationale: active/resolving/resolved would each fire an unwanted side-effect (active banner / narrationInFlight / clear). "pending" is the only inert payload status.
  - Severity: minor
  - Forward impact: none — adoptable to a future "roster snapshot" status if 67-3 introduces one.
- **Corrected TEA's connect wiring test to observe the return value, not the broadcast out_queue**
  - Spec source: TEA test `test_seal_reconcile_on_connect.py` (AC2)
  - Spec text: test drained the connecting socket's `out_queue` to find the reconcile frame
  - Implementation: Changed `_connect` to return `handle_message(...)`'s result and assert against it. The connect handler RETURNS `[*bootstrap_msgs, *replay_msgs]` (connect.py:1648) — the real per-socket delivery channel — rather than enqueueing onto the broadcast `out_queue`.
  - Rationale: Corrects WHERE the test observes delivery to match production; does not weaken the assertion (still requires Adam `submitted` in a real TURN_STATUS frame). The AC5 watcher test was unaffected and passed throughout.
  - Severity: minor
  - Forward impact: none — establishes the correct connect-test observation pattern (inspect the return) for sibling stories.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (sidequest-server):**
- `sidequest/server/turn_status_roster.py` — added phase-aware `build_seal_reconcile_roster` (AC1, AC1-barrier-fired edge, AC6 read-only).
- `sidequest/server/session_room.py` — `broadcast` now detects a connected-but-queueless recipient and emits a loud `broadcast.recipient_dropped` watcher (warning) + log (AC4). No silent drop.
- `sidequest/handlers/connect.py` — MP-only seal reconcile in `_State.Playing`: re-derive the roster, append a `TURN_STATUS` to the connecting socket's bootstrap frames, emit `turn_status.reconciled_on_connect` (AC2, AC5).
- `tests/server/test_seal_reconcile_on_connect.py` — corrected observation channel (see deviation).

**UI:** No code changes — TurnStatusPanel + App batch-entries path already surface the reconciled roster (AC3 verified green).

**Tests:** 9/9 (67-2) GREEN · 64/64 regression on touched subsystems GREEN · 43/43 UI GREEN (run_id 67-2-dev-green). Lint clean (ruff). Postgres-backed connect tests verified with `just pg-up`.

**Branch:** `feat/67-2-action-reveal-delivery-resilience` (pushed, both repos).

**Self-review:**
- ✅ Wired end-to-end: reconcile fires from the real `connect` handler, frame reaches the connecting socket, UI consumes it.
- ✅ Follows project patterns: mirrors 67-1's drop-watcher shape; reuses existing roster builder; no new infra (CLAUDE.md "wire up what exists").
- ✅ All 6 ACs met. Error path (broadcast drop) surfaces loudly per OTEL principle + No Silent Fallbacks.
- ✅ AC6 guardrail: reconcile is read-only — does not touch `_submitted`/phase/dispatch.

**Handoff:** To Reviewer (Colonel Potter).