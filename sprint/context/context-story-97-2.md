---
parent: context-epic-97.md
workflow: tdd
---

# Story 97-2: Seal-reconcile roster races reconnect order — first reconnector told the table is solo (sealed=0/1)

## Business Context

Measured 3× in server log `.20260607-090551` (lines 652/668, 863/878), always the first reconnector: after a server reload both seats reconnect; the FIRST gets `turn_status.reconciled_on_connect sealed=0/1` (solo roster), the second `0/2`. The submit-and-wait barrier is the playgroup's core pacing mechanism (Alex must never be rushed; nobody should be told the table is solo when it isn't) — a first reconnector seeing 0/1 believes no one is waiting on anyone, which plausibly contributes to the seat-2 "Enter enabled / no waiting lock" symptom in the MP desync entry (#740's NEW OBSERVATION, which filed this story). With server reloads being routine during play (WatchFiles hot-reload mid-session is normal operations in this project), the race fires in practice, not just in theory.

## Technical Guardrails

- Seam: `sidequest/server/turn_status_roster.py:58` — `build_seal_reconcile_roster(snapshot, playing_player_ids, ...)` builds from `playing_player_ids` (live sockets via `room.playing_player_ids()`), using `snapshot.player_seats` only for display names (line 45). The durable seat roster (`snapshot.player_seats`) is the source that knows the table is 2-seat before the second socket lands — reconcile against it.
- **CAUTION — the 45-2 phantom-chargen-peer guard is why `playing_*` exists.** A player mid-chargen has a seat-in-progress but must NOT inflate the barrier roster (the table shouldn't wait on someone still rolling a character). The fix must distinguish "durably seated PC, socket not yet reconnected" (count them) from "phantom mid-chargen peer" (exclude them). Look at what distinguishes a completed seat in `snapshot.player_seats` vs an in-flight chargen before designing the predicate — the data model may already encode it; don't invent a parallel flag if one exists.
- Room/presence model: ADR-122 (RoomRegistry never-evict, multi-socket presence ref-counting). `playing_player_ids()` semantics serve other call sites — prefer changing what `build_seal_reconcile_roster` consumes over changing what `playing_player_ids()` returns, unless inspection shows all consumers want durable seats.
- The reconcile path runs on connect (`reconciled_on_connect`) — the fix is read-side; no persistence change expected.

## Scope Boundaries

**In scope:**
- First reconnector after a reload reconciles against the full seated-PC roster (sealed=0/2 for a 2-seat session)
- Regression test for the 45-2 phantom-chargen-peer exclusion
- (Per house OTEL rule) the reconcile span/log should name which roster source produced the count, so the next desync forensics can tell live-socket from durable-seat derivation

**Out of scope:**
- The #740 confrontation-clear desync (fixed, merged) and its `confrontation.delivery` lie-detector
- The seat-2 "Enter enabled" UI symptom itself — if it recurs after this fix on a clean fight, it gets its own entry per the #740 notes
- Any change to lobby/LobbyState FSM or presence ref-counting semantics

## AC Context

1. **"First reconnector after a reload reconciles against the full seated-PC roster (sealed=0/2 for a 2-seat session)"** — Test: 2-seat snapshot with both seats durably persisted; simulate reconnect where only one socket is live; `build_seal_reconcile_roster` (and the wire-level `turn_status.reconciled_on_connect` it feeds) reports total=2. Edge: if one seat had already sealed before the reload, sealed-count must also derive durably (sealed=1/2, not 0/2 — check what the reconcile carries for sealed state, not just the denominator).
2. **"Phantom chargen peers still excluded (45-2 guard regression test)"** — Test: snapshot with one seated PC + one peer mid-chargen (no completed seat) → roster counts 1, not 2. This is the load-bearing negative; it must be a real wiring-level test against the production reconcile path, not a unit on a helper.

## Assumptions

- `snapshot.player_seats` is durably correct at reconnect time (it's read from the persisted snapshot — post-ADR-115 Postgres, no staleness window beyond the last persist).
- A completed seat is distinguishable from an in-flight chargen in existing state. If implementation finds it is NOT distinguishable, that's a design deviation to log — do not silently approximate with a timeout or socket heuristic (No Silent Fallbacks).
- Solo sessions genuinely report 0/1 — the fix must not make solo look like phantom-MP (negative test: 1-seat snapshot → 0/1 stays correct).
