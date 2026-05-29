---
parent: context-epic-67.md
workflow: tdd
---

# Story 67-8: Eliminate duplicate-socket reconnect loop stranding confrontations in AwaitingConnect

## Business Context

Multiplayer is how the playgroup actually plays, and Epic 67's throughline is that a single client's transport hiccup must never punish the whole table. Playtest 2026-05-28 (coyote_star, solo) exposed a sharp failure: committing a dogfight beat fired `DICE_THROW` frames that the server rejected with `session.message_rejected_unbound` four-plus times because the session sat stranded in `AwaitingConnect`. One beat cost ~5 rejected attempts plus a full page reload before a single roll landed.

That is exactly the experience the epic exists to kill — and it is worst for the players the design protects most. A career GM (Keith) playing as a player will read repeated silent rejections as "the engine is broken"; a slower participant (Alex) has no way to tell churn from a genuine wait. The engine is in fact sound — a post-reload handshake (`slug_resumed turn=3`, `slug_resume_confrontation_emitted ship_combat`) let the very next Broadside resolve `CritSuccess`. The defect is transport-layer churn: the client opens a second socket / re-runs the connect handshake, the `AwaitingConnect`→`Playing` binding never completes before the action frame is sent, and the guard correctly rejects an unbound frame. The fix must remove the churn so a roll lands on the first attempt with zero reloads.

Story 67-7 (merged PR #516) delivered only **AC5** — the telemetry watcher event that lets us *detect* an unbound rejection. 67-8 is the fix-leg: it carries the deferred **AC1/AC2/AC3/AC6** and uses that telemetry as its diagnostic instrument.

## Technical Guardrails

**Decision already locked (AC4, from the 67-7 Architect):** pursue **eliminate-the-loop**, NOT buffer-until-Playing. The guard rejection on an unbound frame is *correct* behavior; the bug is the duplicate-socket / remount churn that keeps the session unbound. Removing the churn is the fix. A buffer-until-Playing shim is explicitly ruled out — it belongs to the #G3 WS-teardown-hardening track and would mask the real bind failure (**No Silent Fallbacks**).

**Key files / seams (verify, don't reinvent — much substrate already exists):**
- **UI WebSocket lifecycle:** `sidequest-ui/src/hooks/useWebSocket.ts` — onclose/reconnect (`:177-186`), `detachHandlers` (`:129-135`); and `hooks/useGameSocket.ts` (reconnect on non-1000 close). A `window.WebSocket` patch being wiped mid-session is a UI-side clue pointing here.
- **UI mount/remount:** `sidequest-ui/src/App.tsx` slug-connect effect + `ErrorBoundary name="Game"` (`:2019`). The doubled `connection open` / two `ws.connection_accepted` + `chargen_gate` cycles per reconnect suggest a remount loop.
- **Server presence / bind:** `sidequest-server/sidequest/server/session_room.py` — ref-counted `disconnect(socket_id=...)` (`:448-571`) so a multi-socket player is not dropped on one socket close; this is the seam where a bind race could strand `AwaitingConnect`.
- **Server reconnect replay:** `handlers/connect.py:1073-1270` (per-player filtered replay since `last_seen_seq`). Touch only if the diagnosis lands server-side.
- **AC5 telemetry (the instrument):** the `_emit_unbound_rejection_event` helper and the three Playing-state-guarding handlers (`dice_throw.py`, `player_action.py`, `orbital_intent.py`) already emit the `session_unbound` watcher event (`state_transition` / component=`session` / `recovery=session_unbound`). Reuse it to tell genuine-unbound rejection from reconnect churn.

**Cross-cutting constraints:**
- **No Silent Fallbacks:** a genuinely unbound frame must still reject loudly. Any retry/buffer that survives must be explicit and bounded — and per AC4 it should not be the primary fix at all.
- **OTEL principle:** every resilience seam touched must emit a watcher event so the GM panel confirms the fix engaged. The fix's success criterion is observable as *zero* `session_unbound` rejections across a multi-beat confrontation.
- **Perception firewall (ADR-104/105):** any reconnect-replay change may only re-surface what the player was entitled to see.

## Scope Boundaries

**In scope:**
- Root-cause diagnosis of the duplicate-socket / repeated `ws.connection_accepted` cycle, with log/OTEL evidence recorded in the session (AC1).
- Eliminate the spurious second socket / handshake re-run so `AwaitingConnect`→`Playing` completes before action frames are submitted (AC2).
- A dogfight beat's `DICE_THROW` lands on the first attempt — no `message_rejected_unbound` loop, no required reload (AC3).
- Regression coverage on the reconnect/bind path; if reproducible in MP as well as solo, cover both (AC6).

**Out of scope:**
- Buffer/retry of action frames across a reconnect until `Playing` (AC4 rules this out; #G3 territory).
- Heavy-hammer WS-teardown hardening (#G1/#G3).
- The per-recipient delivery firewall seam (59-20) — distinct.
- AC5 telemetry — already delivered in 67-7.

## AC Context

- **AC1 — Root cause identified (diagnosis/doc AC).** Pass = the duplicate-socket / repeated `ws.connection_accepted` cycle is *explained* (UI remount loop vs server bind race) with log/OTEL evidence captured in the session's Delivery Findings. This is not unit-testable directly; it requires a **live repro** of the dogfight churn (practically in oq-2 with the playtest beat-commit sequence). The *testable proxy* is the symptom that the others assert. Edge: the cause may be UI-side, server-side, or both — RED coverage must not presuppose which.
- **AC2 — No spurious second socket.** Pass = a solo confrontation session does not open a second socket or re-run the connect handshake; the FSM reaches `Playing` before any action frame is accepted. Test angle: drive the connect lifecycle and assert exactly one `ws.connection_accepted` / bind per session; assert no remount re-entry of the slug-connect effect. Edge: a legitimate reconnect after a real close (non-1000) must still be allowed exactly once — assert we don't *over*-correct into "never reconnect."
- **AC3 — First-attempt roll.** Pass = committing a dogfight beat against a freshly-connected session resolves one `DICE_THROW` with zero `session_unbound` rejections and zero reloads. Test angle: with the AC5 telemetry as the lie-detector, assert the unbound-rejection count is 0 across the beat commit; assert exactly one roll resolves. Edge: a frame that arrives genuinely before bind (true race) must still reject — the assertion is "no *loop*," not "never reject."
- **AC6 — Regression coverage.** Pass = the reconnect/bind path has tests proving it does not re-trigger duplicate-socket opens, and they fail on today's code (RED). If the churn reproduces in MP, the suite covers the MP path too. Edge: ref-counted multi-socket presence (`session_room.disconnect`) must not be regressed — closing one socket of a multi-socket player must not strand the session.

## Assumptions

- The server-side bind/guard logic is sound (67-7 finding); the primary suspect is UI-side remount/reconnect churn. If diagnosis shows a server bind race instead, log a Design Deviation and widen server coverage.
- The AC5 watcher event from 67-7 is live on `develop` in both repos and can be asserted against in tests as the unbound-rejection signal.
- A live repro is reproducible from the playtest beat-commit sequence; AC1 is satisfied by recorded evidence, not by an automated test of the root cause itself.
- Both feature branches (`feat/67-8-duplicate-socket-reconnect-loop`) are cut off current `develop` in server and ui.

## Interaction Patterns

The player-visible loop this story repairs: player commits a confrontation beat → expects one die roll to resolve immediately. Today the broken path shows repeated non-response (silent rejections) until a manual page reload "fixes" it. The repaired path: commit → single roll resolves, no reload, no dead air. For a slow typist this matters doubly — the table must never read transport churn as "waiting on you."
