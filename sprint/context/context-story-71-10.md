---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-10: Peer-action transcript: anchor by exact round (add round to PlayerActionPayload) — replaces positional placement

## Business Context

This story makes the multiplayer peer-action transcript correct under the
conditions Keith's playgroup actually plays in. Per ADR-036's 2026-05-03
amendment, peer action text *is* visible during the wait phase — collaborative
visibility helps the table coordinate (it serves Alex, the slow typist, by
letting everyone see who has acted without rushing anyone). Story 71-4 persisted
those peer actions into the transcript so they survive resolution, but it
anchored them **positionally**: the i-th captured round is dropped at the i-th
`NARRATION_END` boundary. The 2026-05-27 `coyote_star` MP playtest surfaced that
positional anchoring drifts — any skipped, empty, out-of-order, or
late-submitted round shifts every subsequent peer block to the wrong turn, so a
teammate's action shows up attached to the wrong narration. For a 140+-turn
session that desync compounds and corrupts the shared record the table relies on
to reconstruct "who did what, when." The fix is to carry the **exact round** on
the player-action wire payload and anchor peer entries by matching that round —
so placement is deterministic regardless of round gaps. Expected outcome: peer
actions always render under the turn they belong to, durably, with no positional
drift.

## Technical Guardrails

**Server (`sidequest-server`):**
- `PlayerActionPayload` lives in
  `sidequest-server/sidequest/protocol/messages.py` (lines ~55–64). Current
  fields: `action: NonBlankString` and `aside: bool = False`. Add a
  `round: int` field (pydantic v2 `ProtocolBase` model). Re-export is already in
  `sidequest-server/sidequest/protocol/__init__.py`; no new export needed.
- The payload is **inbound** (client→server, `PlayerActionMessage.payload` at
  `messages.py:872`); the server does not construct it for narration fan-out.
  Treat the new field per "No Silent Fallbacks": prefer a required field (or a
  validated default) so a malformed/legacy payload fails loud rather than
  silently anchoring to round 0.
- Round semantics follow **ADR-051** (two-tier turn counter: interaction vs
  round). The value carried is the **round** counter, not the interaction
  counter — confirm against the round source feeding the turn coordinator so the
  wire value matches what the UI accumulator keys on.

**UI (`sidequest-ui`):**
- TypeScript `PlayerActionPayload` is in
  `sidequest-ui/src/types/payloads.ts` (lines ~164–167) — currently
  `{ action: string; aside?: boolean }`. Add `round: number` to mirror the
  server. Note: `ActionRevealEntry` (same file, ~28–36) **already** carries
  `round` and `seq` — the live peer-reveal path is already round-aware; this
  story closes the gap on the persisted player-action path.
- The positional anchoring to replace is in
  `sidequest-ui/src/lib/narrativeSegments.ts` (`buildSegments`, ~lines 46–98):
  `sortedPeerRounds` + the `turnBoundaryIndex` counter map the i-th captured
  round to the i-th `NARRATION_END` boundary. The code comment itself documents
  the defect: *"PLAYER_ACTION carries no round, so we anchor positionally."*
  Replace with exact-round matching now that `PLAYER_ACTION` carries `round`.
- `peerActionsByRound: Map<number, ActionRevealEntry[]>` flows
  `usePersistedPeerActions` (`src/hooks/usePersistedPeerActions.ts`) →
  `NarrationScroll` (`src/components/NarrationScroll.tsx:19,26`) →
  `buildSegments`. The accumulator already keys by round and dedups per
  `(player_id, round)`; the anchoring fix consumes that key directly.
- Round source: `currentRound` state in `src/App.tsx` (line ~348) is the round
  threaded into `usePeerReveals` and `persistedPeerActions.capture` and into the
  outbound action send (`App.tsx:1364 round: currentRound`). Use this same value
  for the new outbound `PlayerActionPayload.round`.

**Patterns / integration points:**
- Source-of-truth firewall invariant is load-bearing (ADR-104/105): peer action
  TEXT must continue to derive ONLY from the perception-filtered reveals map —
  do not widen the source while changing the anchor.
- Wiring rule (CLAUDE.md): every test suite needs an integration/wiring test;
  no source-text grep assertions. Drive `buildSegments` with real fixtures.

**Do NOT touch:**
- The perception/redaction firewall logic (ADR-104/105) or per-genre contrast —
  those are siblings 71-11/71-12.
- The `ActionRevealEntry` shape (already round-aware).

## Scope Boundaries

**In scope:**
- Add a `round` field to `PlayerActionPayload` on the server
  (`sidequest-server/sidequest/protocol/messages.py`) and to the mirrored UI
  type (`sidequest-ui/src/types/payloads.ts`).
- Populate `round` on the outbound player-action send in the UI from
  `currentRound`.
- Replace the positional `turnBoundaryIndex` anchoring in
  `narrativeSegments.ts` with exact-round matching (peer entries land under the
  turn whose round equals the captured round).
- Tests (TDD) on both sides: payload round-trip/validation; `buildSegments`
  round-anchored placement including gap/out-of-order/late cases.

**Out of scope:**
- Redaction / perception-filtering changes (ADR-104/105) — owned elsewhere.
- Per-genre peer-action contrast a11y sweep — 71-11.
- The peer-reveal capture-site comment-guard regression note — 71-12.
- Any change to `ActionRevealEntry`, the live wait-phase reveal display, or the
  `emit_event` fan-out (71-13, done).

## AC Context

Acceptance criteria expanded into testable detail (TDD — write failing tests
first, both repos):

1. **`PlayerActionPayload` carries `round` (server).**
   - Pass when: the pydantic model in `messages.py` exposes an integer `round`
     field; a payload serialized with `round` round-trips through
     deserialization with the value intact; a payload missing `round` fails loud
     (validation error) rather than silently defaulting — verify the
     fail-loud/required behavior matches the chosen contract.
   - Edge cases: `round = 0` (session start) is a valid value, distinct from
     "missing"; negative rounds rejected.
   - Test: pydantic construct/validate + `model_dump`/`model_validate` round-trip;
     a negative/absent-field case asserting the loud failure.

2. **UI `PlayerActionPayload` mirrors the field and sends it.**
   - Pass when: the TS interface includes `round: number`, and the outbound
     player-action message is built with `round: currentRound`.
   - Test: assert the constructed outbound payload includes the current round
     value (behavioral, via the send path / message builder — not a source grep).

3. **Peer actions anchor by exact round, not position (UI).**
   - Pass when: `buildSegments` places each captured round's peer entries under
     the turn whose round matches — independent of how many `NARRATION_END`
     boundaries preceded it.
   - Edge cases that MUST be covered (these are the positional-drift failures):
     - **Gap:** rounds {1, 3} captured with boundaries for 1, 2, 3 — round-3
       peers land under turn 3, not turn 2.
     - **Out-of-order arrival:** entries captured for a higher round before a
       lower one still render under their own round.
     - **Late / out-of-round submission:** a peer entry whose `round` differs
       from the "current" boundary index lands by its own `round`, not by
       arrival position.
     - **Empty round:** a round with no submitted peers produces no orphaned
       block and does not shift later rounds.
     - **Within-round order:** multiple peers in one round still sort by `seq`
       (existing behavior preserved).
   - Test: drive `buildSegments(messages, peerActionsByRound)` with synthetic
     `GameMessage[]` + a `Map<number, ActionRevealEntry[]>` and assert segment
     ordering/placement for each case above.

4. **Wiring / no regression.**
   - Pass when: an integration test exercises the real
     `usePersistedPeerActions` → `NarrationScroll`/`buildSegments` path (not the
     unit transform in isolation), and the existing 71-4 persistence tests
     (`peer-action-persistence-wiring-71-4.test.tsx`,
     `player-action-transcript-71-4.test.tsx`) still pass under round anchoring.
   - Source invariant: peer TEXT still originates solely from the
     perception-filtered reveals map (ADR-104/105).

## Assumptions

- The UI `currentRound` (`App.tsx:348`) is the authoritative round to stamp on
  the outbound payload and is the same key space as the `peerActionsByRound`
  accumulator. If these diverge (interaction vs round per ADR-051), log a Design
  Deviation and reconcile against the turn coordinator before anchoring.
- `ActionRevealEntry.round` (already present) and the new
  `PlayerActionPayload.round` share the same round numbering, so anchoring can
  match them directly.
- The server treats `PlayerActionPayload` as inbound-only; no narration-side
  construction needs the new field. If a server path is found that constructs
  this payload, extend it to pass `round` (fail loud, no default).
- 71-4 (peer-action persistence) is merged and live — this story refactors its
  anchoring, it does not reintroduce persistence.

## Interaction Patterns

Wait phase (ADR-036 amendment): peers' submitted actions are visible live via
`usePeerReveals`. On `TURN_STATUS{resolved}`, `persistedPeerActions.capture`
snapshots the round's submitted, firewall-filtered reveals before the ephemeral
map clears. At render, the transcript groups segments by turn; with this story
each captured round's peer block is placed under the turn whose round matches —
so a player scrolling back always sees a teammate's action attached to the
correct narration, even across skipped or late rounds.
