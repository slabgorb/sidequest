# Confrontation beats — collapse to one filtered delivery path

**Date:** 2026-05-26
**Story:** 59-16 (Epic 59 — Intent Router / Mechanical-Engagement Spine; bug, p1, 5pts, tdd)
**Branch:** `feat/confrontation-single-filtered-delivery` (sidequest-server)
**Status:** diagnosis complete, design locked, implementation pending

## Symptom

In solo play a Fighter is offered other classes' beats (Backstab, Cast
Cantrip, Cast Spell, Turn Undead, Pray for Aid). Correct on first load,
wrong after a flee or after a client reconnect ("changed the look").

## Confirmed root cause (Phase 1–3 complete)

Beats are delivered to clients by **two racing mechanisms** (Story 49-7):

1. An **unfiltered full-union** `CONFRONTATION` is broadcast to clients
   (`websocket_session_handler.py:4525` start path via `_emit_event`;
   `dispatch/dice.py:647` mid-turn via `room_broadcast`).
2. A **per-PC class-filtered overlay** is queued *behind* it
   (`wssh:4614-4657`, `dice.py:667-704`). The UI is last-message-wins.

Mechanical root: `emitters.py:240` `project_emitter = author_player_id is
not None`. The `CONFRONTATION` emit passes **no author**, so the emitter
(in solo, the player themselves) **raw-bypasses the projection firewall**
(ADR-105 Invariant 3) and `out_to_self` (`emitters.py:460-464`) is the raw
union. The overlay was a doomed attempt to re-filter the bypassed emitter;
it loses the race after a flee/reconnect.

- **Connect/resume path** (`handlers/connect.py:1474`) filters in a single
  clean call → correct on first load. **This is the model.**
- `GameStateView` (`projection/view.py:14`) exposes no class/spell context,
  so the firewall *cannot* compute class-legal beats today.

## Locked design (Keith, 2026-05-26): one CONFRONTATION delivery path

- Beat/class logic stays in the **encounter layer** (not the firewall).
- The canonical full-union payload is persisted to the **EventLog only**
  (replay/audit) — it is **never** sent to a client socket.
- Exactly **one** client fan-out for `CONFRONTATION`: per-recipient
  class-filtered, delivered to **every connected socket including the
  emitter** (kills the solo bypass).
- Delete both overlay loops and the union-to-client delivery.

## Implementation

1. **Extend `emit_event`** (`emitters.py`) with an optional
   `per_recipient_payload: Callable[[str], BaseModel] | None = None`.
   When supplied:
   - Persist the canonical `payload_model` (union) to EventLog as today.
   - For **every** connected player *including the emitter*, deliver
     `per_recipient_payload(pid)` instead of the projected-canonical /
     raw-bypass frame. (Overrides Invariant 3 for this emit only — the
     emitter is no longer raw-bypassed when a supplier is given.)
   - `out_to_self` becomes the emitter's filtered frame.
2. **Start path** (`wssh:4515-4657`): call `emit_event` with a supplier
   that does `resolve_recipient_pc` + `build_confrontation_payload(
   recipient_pc=...)`. Delete the overlay loop (4614-4657) and the
   `recipient_pc=None` canonical-to-client assumption.
3. **Dice mid-turn** (`dice.py:639-704`): same supplier; drop the
   `room_broadcast(union)` + overlay; deliver filtered per recipient.
4. **Connect/resume** (`connect.py:1474`): already filtered — confirm it
   uses the same supplier shape; dedupe with the new helper.
5. **Fallback ban:** if `resolve_recipient_pc` returns None for a seated,
   connected PC, fail LOUD (ERROR span), do not silently send the union.
   (Lobby/unseated sockets legitimately have no PC — they get no beats,
   not the union.)

## OTEL

`build_confrontation_payload(recipient_pc=...)` already fires
`confrontation_beat_filter_span(source='ui_panel_projection')` per
recipient — that is the lie-detector for "filtering ran." Keep it firing
on the single path. Add a count of recipients delivered-to vs connected so
the GM panel can catch a future skip.

## Tests (rewrite to new shape — do NOT revert features)

- `test_confrontation_per_pc_projection.py`, `..._call_site_audit.py`,
  `..._mp_broadcast.py` encode the overlay mechanism being deleted →
  rewrite to assert the single filtered path.
- **New (red-first):** fixture-driven — synthetic caverns_and_claudes
  pack + solo Fighter snapshot + real `CONFRONTATION` emit through the
  handler; assert the **emitter's own** delivered frame contains no
  `backstab`/`cast_spell`/`turn_undead`/`pray_for_aid`/`cast_cantrip`
  beat ids. This is the regression that reproduces today's bug.
- Wiring test: assert the supplier is invoked for the emitter (the path
  that was bypassed).

## Acceptance

- Solo Fighter never receives non-Fighter beats on any emit (start,
  mid-turn/flee, reconnect).
- No `CONFRONTATION` union ever reaches a client socket; EventLog still
  holds the canonical union row.
- Overlay loops deleted; `confrontation_beat_filter_span` fires once per
  recipient on the single path; full server suite green.
