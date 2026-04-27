---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-3: Momentum readout state sync — UI subscribes to BEAT_RESOLVED

## Business Context

**Playtest 3 evidence (2026-04-19):** the dual-dial momentum bars in
`ConfrontationOverlay` lagged the server's beat resolution. A player would
click a beat, watch the dice settle, see `[BEAT_RESOLVED]` in the server log
with new `player_momentum` / `opponent_momentum` values, and the UI dial
would still show the prior values until the narrator's next prose came back
— typically several seconds later, sometimes a full turn later.

**Audience:** Sebastien (mechanical-first). Per CLAUDE.md, the GM panel is
the lie-detector — but so is the on-screen dial. ADR-024 (Dual-Track
Tension Model) makes the bars the player-facing crunch surface; ADR-027
(Reactive State Messaging) requires that any state the UI mirrors arrive in
its own typed message, not as a side-effect of NARRATION. A momentum dial
that lags the actual beat by a narrator round is worse than no dial — it
teaches Sebastien that the surface is decorative, which kills the
mechanical credibility the engine depends on.

This story is in **Lane A** (MP correctness). It is the third sealed-letter-
era state-sync fix after 45-1 (shared-world delta) and 45-2 (turn barrier).
Was 37-32 in the prior epic; re-scoped per ADR-085.

## Technical Guardrails

### Diagnosis (verified 2026-04-27)

The CONFRONTATION message is the canonical carrier of
`player_metric.current` / `opponent_metric.current`. It is built via
`build_confrontation_payload()`
(`sidequest-server/sidequest/server/dispatch/confrontation.py:30-62`),
which dumps the live `encounter.player_metric` / `encounter.opponent_metric`
fields. The payload shape is fixed by `ConfrontationPayload`
(`sidequest-server/sidequest/protocol/messages.py:486-513`).

CONFRONTATION is emitted from exactly **one** site in production:
`session_handler.py:3592-3666`, inside `_execute_narration_turn` AFTER
`_apply_narration_result_to_snapshot()` (line 3404) and
`record_interaction()` (line 3424). The emit guard at line 3611 checks
`now_live and now_encounter is not None` — so the post-narration encounter
state is what reaches the UI.

The DICE_THROW dispatch path (`session_handler.py:1174-1270`,
`server/dispatch/dice.py:205-499`) mutates `encounter.player_metric.current`
and `encounter.opponent_metric.current` via `apply_beat()`
(`game/beat_kinds.py`) at `dice.py:361`, but **does not emit a
CONFRONTATION frame**. Grep confirms: `build_confrontation_payload` and
`build_clear_confrontation_payload` have only the two call sites in
`session_handler.py:3613/3642` — neither is in the dice path.

The UI receives CONFRONTATION at `App.tsx:760-765` and stores the payload
in `confrontationData` state (line 349). `ConfrontationOverlay` reads
`data.player_metric` / `data.opponent_metric` directly (line 306-307 of
`components/ConfrontationOverlay.tsx`); the bars at `MetricBar`
(line 114-146) interpolate `metric.current / metric.threshold` for the
fill width.

**Root cause:** between the player's beat-click → DICE_RESULT broadcast
(dice.py:441) and the narrator's NARRATION_END, the server holds the new
`encounter.player_metric.current` value but never broadcasts it. The UI
keeps rendering the stale snapshot from the prior turn's CONFRONTATION
emit. On a long narrator turn (5–15s) the dial sits visibly stale
through the entire dice + narration cycle — exactly the lag Sebastien
flagged.

`useStateMirror` (`sidequest-ui/src/hooks/useStateMirror.ts`) does NOT
mirror encounter momentum — its `applyDelta` (lines 236-256) only handles
`location`, `quests`, and `characters`. There is no encounter slice in
`ClientGameState`; the overlay reads off the `confrontationData` React
state, not the mirror.

### Outermost reachable seam (wire-first gate)

Two seams must be exercised end-to-end:

1. **Server emit seam (post-beat-apply):** `dispatch_dice_throw()`
   (`server/dispatch/dice.py:205`) — must broadcast a CONFRONTATION
   frame after the metric mutation at line 371 / 463 and BEFORE the
   inline narrator runs in `_handle_dice_throw` (`session_handler.py:1268-1270`).
   The frame must reflect the post-beat-apply `encounter.player_metric.current`
   and `encounter.opponent_metric.current`. Reuse `build_confrontation_payload()`
   and route through `room_broadcast` (the same callable already used at
   line 453-457 for DICE_REQUEST / DICE_RESULT). Do NOT invent a new
   payload type.

2. **UI subscribe seam:** `App.tsx:760-765` already handles CONFRONTATION
   correctly (`setConfrontationData(payload.active !== false ? payload : null)`).
   The wire-first test must drive a CONFRONTATION arriving mid-dice-flow
   and assert `screen.getByTestId('metric-bar-fill')` width updates BEFORE
   any NARRATION_END arrives. The fix is server-side; the UI test exists
   to prove there is no UI batching / dedup that would suppress a second
   CONFRONTATION frame within the same turn.

The boundary test must drive both legs through `session_handler_factory()`
(`tests/server/conftest.py:332`) using `_FakeClaudeClient`
(`tests/server/conftest.py:197`) so the narrator step completes
deterministically. A unit test on `dispatch_dice_throw` alone fails the
wire-first gate — the test must include the actual `_handle_dice_throw`
invocation so a future regression that re-orders emit vs broadcast is
caught.

### OTEL spans (LOAD-BEARING per CLAUDE.md OTEL principle)

The existing `encounter.beat_applied` span
(`telemetry/spans.py:1088-1098`, helper at line 1251) carries
`metric_delta` but not the post-apply absolute values. The GM panel
needs to see the mutation AND the broadcast that follows it. Define in
`sidequest/telemetry/spans.py` and register in `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `encounter.momentum_broadcast` | `encounter_type`, `player_metric_after`, `opponent_metric_after`, `source` (`"dice_throw"` / `"narration_apply"`), `beat_id` (nullable) | every site that broadcasts CONFRONTATION post-mutation |

Sebastien's lie-detector requires that, when the bars move on screen, a
matching `encounter.momentum_broadcast` span fired in the watcher
dashboard. The existing `encounter.beat_applied` span's `metric_delta`
attribute is not enough — without the absolute post-values, you can't
tell from a span trace whether the dial the player saw matches the engine
state.

The downstream `state_transition` watcher event at `dice.py:380-396`
(`field=encounter`, `op=beat_applied`) stays unchanged.

### Reuse, don't reinvent

- `build_confrontation_payload()` is the single source of truth for
  the CONFRONTATION wire shape. Call it from the dice-throw broadcast
  path; do NOT reach into the encounter to build a partial dict.
- `room_broadcast` callable at `session_handler.py:1208-1218` is already
  the fan-out path for dice messages. Use the same callable for the
  CONFRONTATION emit; do NOT introduce a new fan-out helper.
- `find_confrontation_def()` (`server/dispatch/confrontation.py:14-27`)
  resolves the active `cdef` from the pack — needed because
  `build_confrontation_payload` requires it. The encounter already
  carries the type; the dispatcher already calls `find_confrontation_def`
  at `dice.py:241`; reuse the local.
- `confrontationReceivedThisTurnRef` (`App.tsx:352`) — the UI already
  tracks "did a CONFRONTATION arrive this turn?" Don't break the
  NARRATION_END auto-clear at line 475-477; the new mid-turn frame
  should set the ref, the same way the existing handler does.
- `_FakeClaudeClient` at `tests/server/conftest.py:197` returns canned
  narrator output so the inline narration step in `_handle_dice_throw`
  doesn't hang the test.

### Test files

- New: `sidequest-server/tests/server/test_dice_throw_confrontation_emit.py`
  — wire-first server boundary test. Drives DICE_THROW through
  `_handle_dice_throw`, asserts a CONFRONTATION frame is broadcast
  with post-apply momentum BEFORE NARRATION_END.
- Extend: `sidequest-server/tests/server/test_dice_dispatch.py` — unit
  coverage for the new `momentum_broadcast` span attributes on the
  apply path (positive: span fires with correct `player_metric_after`;
  negative: opposed-pending path does NOT emit since deltas are deferred).
- New: `sidequest-ui/src/__tests__/confrontation-mid-turn-momentum-sync.test.tsx`
  — wire-first UI boundary test. Drives two CONFRONTATION messages in
  the same turn (the existing post-narration emit + the new post-dice
  emit) and asserts `metric-bar-fill` width updates after the second
  one arrives. Reuse the fixture pattern from
  `__tests__/confrontation-wiring.test.tsx`.

## Scope Boundaries

**In scope:**

- New CONFRONTATION emit in `dispatch_dice_throw` (or `_handle_dice_throw`,
  caller's choice — the broadcast must happen between beat-apply and
  narration step).
- New `encounter.momentum_broadcast` OTEL span + `SPAN_ROUTES` entry.
- Wire-first server test: DICE_THROW → CONFRONTATION (post-beat) →
  NARRATION_END → CONFRONTATION (post-narration); assert two frames,
  both with current momentum.
- Wire-first UI test: two CONFRONTATION frames in one turn update the
  bar width.
- Unit + extension tests confirming `apply_beat` mutation + broadcast +
  span all line up.

**Out of scope:**

- Adding an encounter slice to `useStateMirror` / `ClientGameState`. The
  overlay reads off a dedicated React state today (`confrontationData`)
  and that is correct — this story does not unify the two state mirrors.
  If a future story migrates encounter state into the unified mirror,
  it can build on the broadcast path landed here.
- Renaming `BEAT_RESOLVED` to a wire message kind. The story title says
  "UI subscribes to BEAT_RESOLVED" but `[BEAT_RESOLVED]` is only the
  synthetic narrator-replay tag at `dice.py:198` (a string, not a
  message). The actual wire kind the UI subscribes to is CONFRONTATION;
  the story is about getting the UI a fresh CONFRONTATION sooner, not
  about minting a new message type.
- Opposed-check encounter momentum — when `opposed_pending=True`
  (`dice.py:336-359`) the deltas are deferred to `narration_apply.py`,
  so there is nothing to broadcast at the dice-throw site for that
  branch. The opposed path's emit lands inside the existing post-
  narration site at `session_handler.py:3611`; this story does not
  change that.
- DICE_RESULT carrying momentum directly. Wider protocol change; the
  CONFRONTATION re-emit is the surgical fix.

## AC Context

1. **Server emits CONFRONTATION after beat-apply, before narrator
   completes.**
   - Test: drive a DICE_THROW for an active confrontation through
     `_handle_dice_throw`. Assert the room's broadcast queue contains
     a CONFRONTATION message whose `payload.player_metric.current`
     matches `encounter.player_metric.current` post-`apply_beat()` —
     and that this CONFRONTATION arrives BEFORE the NARRATION_END
     emitted by the inline narrator. Use a recording mock for
     `room_broadcast` so the order is observable.
   - Negative: the opposed-check branch (`opposed_pending=True`,
     `dice.py:336`) must NOT emit the mid-turn CONFRONTATION (deltas
     are deferred). Assert no CONFRONTATION fires between DICE_RESULT
     and NARRATION_END on that path.

2. **`encounter.momentum_broadcast` OTEL span fires on every emit.**
   - Test: drive a successful beat resolution; assert the span fires
     with `encounter_type`, `player_metric_after`, `opponent_metric_after`,
     `source="dice_throw"`, `beat_id=<id>`. Verify SPAN_ROUTES routes the
     event to the GM panel watcher feed.
   - Negative: a beat that is `skipped` (per `apply_beat` skip path,
     `dice.py:366`) raises `DiceDispatchError` before broadcast — the
     span MUST NOT fire on the error path.

3. **UI overlay reads live momentum off the latest CONFRONTATION.**
   - Test: render `ConfrontationOverlay` via the `App.tsx` message
     dispatch path. Send two CONFRONTATION frames within the same turn
     (mid-dice + post-narration); assert
     `screen.getByTestId('metric-bar-fill')` `style.width` reflects the
     second frame's `current / threshold` ratio.
   - Negative: a CONFRONTATION with `active=false` (clear payload)
     unmounts the overlay even if it arrives mid-turn — must not strand
     a stale dial when the encounter resolves on a beat-fire.

4. **`confrontationReceivedThisTurnRef` is preserved across mid-turn
   re-emits.**
   - Regression test: the existing NARRATION_END auto-clear path
     (`App.tsx:475-477`) depends on the ref being true when ANY
     CONFRONTATION arrived this turn. With two CONFRONTATIONs in one
     turn the ref must be true at NARRATION_END handling time and the
     overlay must NOT auto-clear unless the second frame had
     `active=false`.

5. **Existing post-narration CONFRONTATION emit unchanged.**
   - Regression test: the emit at `session_handler.py:3657-3666` still
     fires once per narration turn with the correct payload. The new
     mid-turn emit is additive — neither replaces nor delays the
     post-narration frame.
