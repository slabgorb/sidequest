---
parent: sprint/epic-45.yaml
---

# Epic 45: Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup

## Overview

Epic 45 is the **successor to Epic 37**. It absorbs Epic 37's open backlog, splits the
5–8pt grab-bag stories (37-38, 37-39, 37-40, 37-41) into tight single-AC stories, and
re-scopes everything that referenced the deleted `sidequest-api` (Rust) tree onto the
current Python tree per **ADR-085** (tracker hygiene during the Rust→Python port).

Each story names its source `37-N sub-N` in the description for traceability.

**Three lanes — priority-ordered:**

| Lane | Theme | Stories | Sprint pressure |
|------|-------|---------|-----------------|
| **A** | MP correctness — sealed-letter handshake, turn barrier, momentum sync | 45-1 (done), 45-2, 45-3, 45-11, 45-18 | aligned with Sprint 3 closeout |
| **B** | State write-back hygiene — counters and resolution handshakes that fire but never persist | 45-4..10, 45-12..17, 45-19..23 | bookkeeping-scale, OTEL-on-write per item |
| **C** | UI / cleanup tax + tuning + render observability | 45-24..28, 45-30, 45-31 | P2/P3 — must not displace Lane A/B |

## Background

### Playtest 3 (2026-04-19, evropi session)

Four players (Rux, Orin, Blutka + co.; Felix as long-running solo) generated the
diagnostic corpus this epic responds to. The sessions exposed three failure modes:

1. **Multiplayer correctness gaps** — turn-barrier waited on phantom lobby peers
   (45-2); momentum dial lagged behind `BEAT_RESOLVED` events (45-3); shared-world
   delta wasn't ground-truthed across players, so Orin's narrator fabricated a
   "collapsed corridor" rather than admit Blutka was right next to him (closed in
   45-1). These are the failures Sebastien (mechanical-first player) and Alex
   (slower reader) feel first — the GM-panel lie-detector and the pacing humanity
   are both load-bearing for the playgroup audience.

2. **Bookkeeping that fires but doesn't persist** — `total_beats_fired` frozen at 0
   despite real beat fires (45-9); `quest_log={}` and `active_stakes=''` after a
   Resolved trope (45-20); `world_history` arcs frozen at turn 30 in a 72-turn
   session (45-19); container/object retrieved-state forgotten on room re-entry
   (45-13); duplicate starting kits (45-12); discarded weapons stuck at
   `state=Carried` (45-14). The pattern is consistent: extractor writes, applier
   forgets. Lane B fixes the write-back.

3. **Port-drift residue from ADR-082** — Stories that referenced
   `sidequest-api/src/...` paths (Rust) and Rust-specific types are re-scoped to
   the Python tree. ADR-085 governs tracker hygiene during this transition. Any
   plan or context that still names a `.rs` file is a story that needs rethinking
   (cf. canceled 39-7) — call it out before implementation begins.

### Why this matters for the playgroup

Per CLAUDE.md, the primary audience is Keith's playgroup — Keith (forever-GM
finally playing), James (narrative-first), Alex (slower reader, hates time
pressure), Sebastien (mechanical-first, watches the GM panel). The narrator must
be *good enough to fool a career GM*. The playtest evidence is concrete:

- **Sebastien's lie-detector** depends on OTEL spans on every subsystem decision
  (CLAUDE.md OTEL principle). Lane B is, in part, an OTEL audit — every fix in
  this lane must add a span on the write path so the GM panel can prove the
  subsystem fired.
- **Alex's pacing concern** is what 45-2 closes. Phantom lobby peers force a
  fast-typist to drag a slow-typist behind them; or, in Rux's case, force a solo
  player to wait on imaginary peers. Sealed-letter pacing requires the barrier
  to count *playing* peers, not lobby presence.
- **James's narrative continuity** is what 45-1, 45-19, 45-20, and 45-23 close.
  When tropes resolve but the quest log doesn't update, the narrator's prompt
  loses durable beats — story texture starts to drift.

## Technical Architecture

### Subsystems touched

| Subsystem | Repo | Stories | Key files |
|-----------|------|---------|-----------|
| Lobby + turn barrier | server | 45-2, 45-3, 45-11, 45-18 | `sidequest/server/session_room.py`, `sidequest/server/session_handler.py`, `sidequest/game/turn.py` |
| Save/reload + chargen state hygiene | server | 45-5, 45-6, 45-8, 45-10, 45-12, 45-13 | `sidequest/server/session_handler.py` (chargen path), `sidequest/game/builder.py`, `sidequest/game/persistence.py` |
| World history + cartography write-back | server | 45-19, 45-20, 45-23 | `sidequest/game/world_history.py` (or equivalent), `sidequest/game/cartography.py`, narrative-log writer |
| Engine internals — progression, namegen | server, content | 45-27, 45-28 | `sidequest/game/tropes.py`, `sidequest/game/namegen/markov.py`, culture corpus YAML in `sidequest-content/conlang/` |
| REST cleanup | server | 45-26 | `sidequest/server/rest.py:283/365/418`, `sidequest/game/persistence.py` |
| UI — momentum sync, WS handshake, a11y | ui | 45-3 (UI half), 45-25 | `sidequest-ui/src/App.tsx`, `sidequest-ui/src/components/ConfrontationOverlay.tsx`, state-mirror hooks |
| Daemon — render policy + heartbeat | daemon, server | 45-30, 45-31 | `sidequest_daemon/...`, daemon span emit, server-side enqueue in renderer driver |

### Shared design themes

These cut across multiple stories — a single fix in one story should not invent
its own pattern when another story in the epic will use the same thing:

1. **Explicit lifecycle states beat implicit booleans.** 45-2 (lobby states),
   45-13 (container retrieved), 45-14 (item state=Carried/Discarded/Consumed),
   45-15 (Consumed → removed) all converge on the same lesson: when an entity
   has a lifecycle, model it with named states and a transition function, not
   with `if connected and not disconnected and ...`. Implicit booleans rot.

2. **Every write-back gets an OTEL span on the success path** (CLAUDE.md OTEL
   principle). The GM panel is the lie-detector; if the subsystem doesn't emit a
   span, you cannot tell whether it engaged. Every story in Lane B (and most of
   Lane A) requires a new span on the write path. Span schema:
   `<subsystem>.<action>` (e.g., `quest_log.entry_written`, `region.write_rejected`,
   `barrier.wait` with `lobby_participant_count` and `active_turn_count`).

3. **Wire-first discipline for any cross-seam fix** (workflow=wire-first stories).
   Boundary tests must exercise the actual transport/pipeline seam, not internal
   state alone. Examples: 45-2 must exercise the lobby ↔ turn-barrier seam over
   WebSocket, not unit-test the predicate; 45-3 must exercise the
   server-emits-state → UI-subscribes-and-renders seam, not just the snapshot
   field; 45-23 must exercise the arc-generation → embedding-persist seam, not
   just the generator.

4. **Write-back symmetry (extractor ↔ applier).** Many Lane B bugs are the same
   shape: extractor writes a partial state (Consumed / Resolved / Discovered)
   and the applier never observes it. The fix in each case is to find both ends
   and confirm the round-trip, not to silently set the field. Tests must assert
   the *applier observed the extractor's write*, not just that the extractor
   wrote.

5. **Telemetry first, fix second, when the diagnosis is unclear** (45-11, 45-23,
   45-31). The bug description says "investigate why the divergence happens";
   the right move is to add the OTEL span FIRST (capture the divergence in a
   playtest), THEN fix. This is wire-first applied to diagnosis.

### Failure mode: tests pass but nothing is wired

CLAUDE.md flags this explicitly. Every Lane B story should have at least one
**integration / wiring test** that calls the production code path end-to-end
(extractor invoked → applier observes the write → snapshot reflects it →
narrator prompt sees it / GM panel reports it). Unit tests on extractor or
applier alone do not satisfy the wire-first gate.

## Planning Documents

| Reference | Relevance |
|-----------|-----------|
| **ADR-082** | Port `sidequest-api` from Rust back to Python — every story in this epic operates on the Python tree |
| **ADR-085** | Tracker hygiene during the Rust→Python port — the rationale for re-scoping 37-N sub-items into 45-N |
| **ADR-037** | Shared-world / per-player state split — load-bearing for 45-1 (done) and 45-3 |
| **ADR-038** | WebSocket Transport Architecture — load-bearing for 45-2, 45-3, 45-25 |
| **ADR-031** | Game Watcher / OTEL — every Lane B story emits per the patterns here |
| **ADR-014** | Diamonds and Coal — Lane B's bookkeeping bugs are coal-being-treated-as-diamond and vice versa |
| **CLAUDE.md** | Wire-up principle, Wire-test mandate, OTEL principle, Playgroup audience — all four are load-bearing for this epic |
| **SOUL.md** | The Test ("If a response includes the player doing something they didn't ask to do, it's wrong"); Living World; Cost Scales with Drama |

## Cross-Epic Dependencies

- **Epic 40** (Runtime Wiring Test Harness) — many Lane B stories should
  contribute their wire-tests through the harness Epic 40 produced. If a wiring
  shape doesn't fit, surface a finding for the harness rather than working
  around it.
- **Epic 42** (ADR-082 Phase 3 combat port) — done. 45-18 (`encounter.actors`
  registration) is downstream of the combat port and may have inherited the
  registration gap there.
- **Epic 43** (LoRA pipeline cleanup) — done. 45-30/31 are daemon stories but do
  not touch LoRA.
- **Sprint 3 sealed-letter goal** — 45-1 (done), 45-2, 45-3 are aligned with the
  sprint goal directly. The rest of Lane A is downstream support.
