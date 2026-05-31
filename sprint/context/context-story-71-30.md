---
parent: context-epic-71.md
workflow: trivial
---

# Story 71-30: action_reveal.dropped_rate_limit also ephemeral — add to _EPHEMERAL_EVENT_TYPES (sibling of composing-storm fix)

## Business Context

The ADR-036 multiplayer action-visibility channel fans out "composing" / "submitted"
keystroke state to peers so the table can coordinate (Alex isn't rushed; the group
sees who is typing). A prior fix (the "composing-storm" fix) found that
`action_reveal.composing` events were 30% of all telemetry rows on a real session
(`perseus_cloud` session 894 — one Postgres INSERT per debounced keystroke, zero
forensic value in solo), so `action_reveal.composing` was added to
`_EPHEMERAL_EVENT_TYPES` (`sidequest/telemetry/watcher_hub.py`): live-pushed to the
GM panel but never event-sourced to `turn_telemetry`.

The `ActionRevealHandler` ALSO publishes `action_reveal.dropped_rate_limit` — a
diagnostic event emitted every time a composing update is throttled by the
server-side rate-limit floor. Because composing updates fire on a debounce storm, the
*dropped* events fire on the same storm cadence — so `dropped_rate_limit` is exactly
as high-frequency and exactly as forensically worthless to persist as
`action_reveal.composing` was. It is a pure keystroke/UI-state byproduct. Today it
falls through to persistence (it is NOT in the ephemeral set), re-creating the same
write-amplification the composing-storm fix removed. This story adds
`action_reveal.dropped_rate_limit` to `_EPHEMERAL_EVENT_TYPES` so it is live-push only
— the trivial sibling of the composing fix.

## Technical Guardrails

**The one-line change site:**
- `sidequest/telemetry/watcher_hub.py` — `_EPHEMERAL_EVENT_TYPES: frozenset[str]`
  (line ~335). Today it contains exactly `{"action_reveal.composing"}`. Add
  `"action_reveal.dropped_rate_limit"`. The surrounding docstring (lines ~325-334)
  documents the doctrine: "LIVE-PUSH ONLY — broadcast to the GM panel but never
  written to turn_telemetry ... intrinsic to the event TYPE ... must NOT be persisted
  in ANY mode." Extend the rationale comment to name the new member.
- `_persist_turn_telemetry` (line ~398) already short-circuits on the set:
  `if event_type in _EPHEMERAL_EVENT_TYPES: return` (lines ~436-437). No other code
  change is required for the persistence skip — membership in the frozenset is the
  whole mechanism.

**The emit site (read-only context, do not change):**
- `sidequest/handlers/action_reveal.py` — `action_reveal.dropped_rate_limit` is
  published at line ~89-97 via `_watcher_publish("action_reveal.dropped_rate_limit",
  {... "slug", "player_id", "round" ...}, component="multiplayer")`, inside the
  composing rate-limit guard (`_COMPOSING_FLOOR_S = 0.100`, line ~32). This is the
  storm cadence. Leave the emit as-is — the event still LIVE-pushes to the panel;
  only its persistence changes.

**Doctrine note:** the discrete, low-frequency sibling `action_reveal.submitted`
(emitted at lines ~136-146) is deliberately NOT ephemeral and keeps persisting (it
has diagnostic value — who submitted, when). Do NOT add `submitted` to the set. Only
`dropped_rate_limit` (the storm byproduct) joins `composing`.

**No Silent Fallbacks framing:** adding to the ephemeral set is intentional
non-persistence by design (keystroke state has no forensic value), which the
docstring already establishes is NOT a silent fallback — there is nothing to fail
loudly about. Mirror that wording.

## Scope Boundaries

**In scope:**
- Add `"action_reveal.dropped_rate_limit"` to `_EPHEMERAL_EVENT_TYPES`.
- A test asserting the event type is treated as ephemeral (not persisted) while
  still being live-pushable.
- Update the frozenset's rationale comment to name the new member.

**Out of scope:**
- Changing the rate-limit floor, the emit site, or the live-push (panel) path.
- Touching `action_reveal.composing` (already done) or `action_reveal.submitted`
  (stays persisted).
- Any change to the `ActionRevealHandler` broadcast/seq logic.

## AC Context

**AC1 — membership.** `"action_reveal.dropped_rate_limit"` is in
`_EPHEMERAL_EVENT_TYPES`. A test can assert membership directly, OR (preferred,
behavioral) assert non-persistence per AC2.

**AC2 — treated as ephemeral (not persisted).** Call `publish_event` (or drive
`_persist_turn_telemetry`) with `event_type="action_reveal.dropped_rate_limit"` and a
bound telemetry sink; assert NO `turn_telemetry` row is written / the sink's
`record`/`write_telemetry` is not called for that event. Mirror the existing test
for `action_reveal.composing` (the composing-storm fix's test is the template — find
it and clone its shape for the new member).

**Edge case:** the live-push (panel broadcast) path is unaffected — if the existing
composing test also asserts "still broadcast to subscribers," replicate that so the
new member is proven LIVE-PUSH-ONLY (pushed, not persisted), not LIVE-PUSH-NONE.

## Assumptions

- `dropped_rate_limit` carries no forensic value worth a row — it is a pure
  high-frequency byproduct of the composing storm, identical in character to
  `composing`. (Strongly supported: it fires inside the composing rate-limit guard on
  the same cadence.) If an operator workflow actually relies on counting dropped
  events from `turn_telemetry`, that would contradict this — but the live-push panel
  path still surfaces them in real time, which is the appropriate place for
  rate-limit diagnostics.
- The composing-storm fix's test exists and is the canonical template; if it is
  absent, write the test fresh against `_persist_turn_telemetry`'s ephemeral
  short-circuit.
- No migration or backfill is needed — this only changes go-forward persistence.

If a real forensic consumer of `dropped_rate_limit` rows exists, log a Design
Deviation and notify SM before removing persistence.
