---
parent: context-epic-81.md
workflow: tdd
---

# Story 81-2: Instantiate and drive TensionTracker in the turn pipeline (ADR-024)

## Business Context

ADR-024's dual-track tension model (action track + stakes track, with event spikes) is the
mechanical substrate that lets the system reason about narrative pacing instead of the
narrator improvising it. SOUL.md's "Cost Scales with Drama" and "Cut the Dull Bits" both
assume a real signal for how much is at stake right now. Today that signal does not exist
in production: `TensionTracker` is only ever constructed in tests, so the tracks never
accumulate during play and the OTEL spans the GM panel relies on never fire. This story
stands up the producer — a live per-session tracker fed by turn events — so a real tension
signal exists for the pacing hint (81-3) to consume and for the GM panel to observe.

## Technical Guardrails

**Key files (navigate by symbol; 2026-06-03 line anchors may drift):**
- `sidequest/game/tension_tracker.py:266` — `class TensionTracker`; `record_event` (~:322), `pacing_hint(thresholds)` (~:359), `with_values(...)` constructor helper.
- `sidequest/server/session_state.py` (~:245) — `_SessionData`; `entity_store` is the model to mirror for a per-session field.
- Turn-processing path — `sidequest/server/websocket_session_handler.py` and/or `sidequest/handlers/player_action.py` (where combat/scene events resolve and `_build_turn_context` is assembled) — the place to call `record_event`.
- `tests/game/test_tension_tracker.py`, `tests/game/test_tension_tracker_otel_wiring.py` — existing isolation + OTEL coverage to extend with a production-path wiring test.

**Patterns to follow:**
- Per-session state lives on `_SessionData` (the `entity_store` precedent). One tracker per
  session, created when the session/room is set up, not per turn.
- Reuse the tracker's existing OTEL emission — do not add a parallel telemetry path. The
  spans should now fire because the tracker runs in a real turn (OTEL lie-detector principle).
- Fail-loud: if the events feeding `record_event` are absent, surface it; don't quietly skip.

**Integration points / what NOT to touch:**
- Do not modify `TensionTracker`'s internal math or `pacing_hint()` — they are tested and
  correct. This story only constructs and feeds it.
- Do not wire the hint into `TurnContext` here — that is 81-3's job (keep producer and
  consumer in separate stories so each has its own wiring test).

## Scope Boundaries

**In scope:**
- A `TensionTracker` on `_SessionData`, created per session, surviving across turns.
- Feeding resolved combat/scene events into `record_event` from the turn path.
- A wiring test proving the production turn path drives the tracker; OTEL span fires in a real turn.

**Out of scope:**
- Deriving/injecting `PacingHint` into `TurnContext` (81-3).
- Resume-time rehydration of tension state across save/load (see Assumptions).
- The accelerator/decelerator keyword scan stubbed in `trope_tick.py` (deferred per code).

## AC Context

1. **Per-session tracker exists.** `_SessionData` carries a `TensionTracker` created once per
   session and reused across turns. Test: drive two turns and assert it is the same instance
   accumulating, not re-created (state from turn 1 is visible in turn 2).
2. **Turn events feed the tracker.** Turn processing calls `record_event` for resolved
   combat/scene events so the action and stakes tracks move. Test: run a turn carrying a
   tension-bearing event and assert non-zero track values; a quiet turn moves them less /
   decays per the tracker's own rules. Edge case: a turn with no events must not crash and
   leaves tracks in a valid state.
3. **OTEL fires in production.** The tension span/watcher event is emitted during a real turn
   (not only under the existing isolation test). Verify the watcher receives it through the
   production path so the GM panel can confirm engagement.
4. **Wiring test is real.** An integration test asserts the production turn path constructs a
   `TensionTracker` and calls `record_event` (behavioral — e.g. observing accumulated state or
   the OTEL event, not just `grep`). It fails on current `develop` (tracker never instantiated)
   and passes after the fix. Full `just server-test` green; `just server-lint` clean.

## Assumptions

- Resolved combat/scene events are available at the turn-processing site in a form
  `record_event` accepts (`CombatEvent`); if a mapping/adapter is needed, it is small and in
  scope. If the available events don't cleanly map, log a Design Deviation.
- Per-session in-memory tension state is acceptable for v1; tension resets on session reload.
  If playtest shows resume must preserve tension, that is a follow-up story, not this one —
  log the assumption if you rely on it.
- 81-3 will consume `tracker.pacing_hint(thresholds)`; this story must leave the tracker in a
  state where that call is meaningful (tracks actually reflect recent turns).
