---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-11: turn_manager.round invariant against narrative_log.max_round

## Business Context

**Playtest 3 evidence — Felix's long-running solo session:** the database
ended at `turn_manager.round = 65` while `SELECT MAX(round_number) FROM
narrative_log = 72`, a 7-round gap. Round-keyed gating across the engine
(arc generation, scrapbook backfill, trope cooldown, world history maturity
injection) reads `turn_manager.round` as the authoritative round counter;
when that value lags the persistent narrative-log evidence, every
round-gated subsystem operates on stale data.

**Audience:** Felix is the canary for long-session bugs — at 72 rounds his
save reveals the same write-back asymmetry pattern Lane B addresses
(extractor writes → applier never observes). Sebastien sees the same gap
through the GM panel: a span that says "round 65" while the narrative log
shows 72 entries reads as a lie. Per CLAUDE.md, telemetry-first when the
divergence is unclear — the OTEL invariant span is the diagnostic surface
that turns this into a fixable bug.

This story sits in **Lane A** (MP correctness) but borrows Lane B's
telemetry-first discipline (Epic 45 design theme #5). It was 37-38 sub-4;
re-scoped per ADR-085 onto the Python tree.

ADRs in play: **ADR-051** (Two-Tier Turn Counter — display `round` vs
granular `interaction`); **ADR-031** (Game Watcher / OTEL on every
subsystem decision).

## Technical Guardrails

### Diagnosis (verified 2026-04-27)

`TurnManager` lives at `sidequest-server/sidequest/game/turn.py:39-115` and
exposes two counters per ADR-051:

- `interaction` (line 55): monotonic per-narration counter; advanced by
  `record_interaction()` at line 95-100, called once per narration turn
  from `session_handler.py:3424`.
- `round` (line 54): display counter; advanced by `advance_round()` at
  line 102-104 — **never called in production code**. Grep across
  `sidequest-server/sidequest/` returns zero non-test, non-self callers
  (the only hit besides the definition is a docstring exclusion in
  `agents/narrator.py:281` warning the LLM not to emit `advance_round`).

`narrative_log.round_number` (schema at
`game/persistence.py:87-94`) is written at
`session_handler.py:3472-3479`:

```
NarrativeEntry(
    timestamp=0,
    round=snapshot.turn_manager.interaction,   # NB: interaction, not round
    ...
)
sd.store.append_narrative(narrative_entry)
```

So `narrative_log.round_number` is fed by `interaction`, while
`turn_manager.round` is the never-advanced display counter.
`SELECT MAX(round_number) FROM narrative_log` returns the latest
`interaction` write — currently at 72 in Felix's save — while
`turn_manager.round` is frozen at its initialization value.

Three consumers read `turn_manager.round` today (verified by grep):

- `session_handler.py:3232` — `mp.barrier_fired` watcher event (Lane A
  observability surface).
- `session_handler.py:3260` — `mp.round_dispatched` watcher event
  (same).
- `world_materialization.py:72` — `turn = int(snapshot.turn_manager.round)`
  used as the seed turn when materializing a world from the genre pack.

In Felix's session those three sites all reported `round=65` while the
durable record had advanced to 72. The "round-keyed gating" the story
description names is exactly these consumers plus any future ones.

### Outermost reachable seam (wire-first gate)

The wire-first test must exercise the actual write/dispatch pipeline,
not a unit on `TurnManager.advance_round()`. Two candidate seams:

1. **`_execute_narration_turn` end-of-turn write-back**
   (`session_handler.py:3404-3486`). The interaction increment + the
   `append_narrative` write happen here in sequence. After this
   sequence completes, `turn_manager.round` should be `>= MAX(narrative_log.round_number)`.
   The invariant check lands at the end of this block (after persistence,
   before `_dispatch_embed_worker` at line 3495) so it sees the post-
   write state.

2. **`record_interaction()` itself** (`game/turn.py:95-100`). This is
   the natural extractor-applier coupling site: every interaction
   advance is paired with a narrative-log row, so `round` should
   advance in lock-step or strictly track interaction. The cleanest
   structural fix is to also update `round` here (matching narrative-log
   semantics) — but that decision wants telemetry first to confirm no
   other producer mutates `round` out of band.

**Telemetry-first discipline** (Epic 45 theme #5): land the invariant
span FIRST, run a playtest or scenario through it to confirm the
divergence reproduces and is captured, THEN decide between the two
fix shapes. The span MUST emit on every tick even when the invariant
holds (Sebastien needs to see "round=72, max_round=72" to know the
detector is engaged), not only on violation.

The boundary test must drive `_execute_narration_turn` via
`session_handler_factory()` (`tests/server/conftest.py:332`) with
`_FakeClaudeClient` (`conftest.py:197`). Run N narration turns,
read both `snapshot.turn_manager.round` and the SQL
`SELECT MAX(round_number) FROM narrative_log`, assert the gap is
zero at every tick. A unit test on `TurnManager` does not satisfy the
wire-first gate — the bug is precisely that the production write
sequence never calls the unit-tested method.

### Decide between two structural fixes

After landing the OTEL detector, the production fix is one of:

1. **Wire `advance_round()` into the resolution pipeline.** Call it
   from `record_interaction()` (line 95), or from
   `_execute_narration_turn` after `record_interaction` at
   session_handler.py:3424. This makes `round` track interaction 1:1.

2. **Repoint `narrative_log.round_number` to `turn_manager.round` and
   start advancing it deliberately.** Higher blast radius — the SQL
   schema reads "round_number" but is fed "interaction" today; many
   downstream readers (corpus mining, scrapbook backfill 45-10) take
   the column name at face value.

Option 1 is the smaller surface and matches the documented two-tier
model (ADR-051). Land the invariant span; run it; use the captured
divergence trace to confirm Option 1 closes the gap before changing
the column semantics.

### OTEL spans (LOAD-BEARING — the story's primary deliverable)

Define in `sidequest/telemetry/spans.py` and register in `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `turn_manager.round_invariant` | `round`, `interaction`, `max_narrative_round`, `gap` (= `max_narrative_round - round`), `holds` (bool) | end of `_execute_narration_turn` after `append_narrative` (session_handler.py:~3486) |

Schema convention `<subsystem>.<action>` per Epic 45 theme #2. The
`gap` attribute is what the GM panel charts; `holds=False` is the
lie-detector trigger. SPAN_ROUTES entry uses
`event_type="state_transition"`, `component="turn_manager"`,
`extract` lifts `gap` and `holds` so the watcher feed can colour-
code violations red.

**The span must fire on every tick, not only on violation.** A
violation that fires only when broken is invisible until something
else breaks; an invariant span that fires every tick proves the
detector is engaged.

Optional (if the fix lands in this story): emit a
`watcher_publish("state_transition", ..., component="turn_manager")`
event with `field="round_invariant"` and `op="restored"` on the first
tick after a previously-divergent state returns to `gap=0`.

### Sibling work — share, don't duplicate

Story 45-2 (turn-barrier active-turn-count) lands `lobby.state_transition`,
`lobby.seat_abandoned`, `barrier.wait` spans through the same
`SPAN_ROUTES` infrastructure. Reuse the registration plumbing. Do NOT
introduce a new span-routing pattern.

Story 45-10 (scrapbook backfill on resume) reads
`narrative_log.max_round` directly to detect coverage gaps. If 45-10
lands first, its `MAX(round_number)` query helper is the same shape
this story needs — share a single helper rather than duplicating the
SQL. Search for `max_round` / `MAX(round_number)` after 45-10 lands
to consolidate.

### Reuse, don't reinvent

- `TurnManager.advance_round()` (`game/turn.py:102-104`) already
  exists; the fix is to wire it, not to write a new method.
- `Persistence.recent_narrative()` (`game/persistence.py:339-364`)
  already reads `narrative_log` rows; an `max_narrative_round()`
  helper belongs alongside it.
- `_watcher_publish` and `SPAN_ROUTES` registration patterns are
  established (`telemetry/spans.py:64-78` for SpanRoute,
  `:331-336` for an existing route). Use them; do not bypass.
- `session_handler_factory()` is the multiplayer-capable test fixture;
  use it for the wiring test even in a solo scenario so the test
  exercises the production code path.

### Test files

- New: `sidequest-server/tests/server/test_turn_manager_round_invariant.py`
  — wire-first boundary test driving N narration turns and asserting
  the invariant span fires every tick with `gap=0`. Includes a
  regression scenario that synthesizes the divergence (manually
  decrement `round` before a tick) and asserts the span fires with
  `holds=False` and `gap>0`.
- Extend: `sidequest-server/tests/game/test_turn.py` (or create if
  absent) — unit coverage for whatever production wire-up lands
  (`record_interaction` advancing `round`, or whichever site is chosen).
- New: `sidequest-server/tests/telemetry/test_round_invariant_span.py`
  — span attribute extraction + SPAN_ROUTES routing assertions
  (mirrors the route-test pattern in `test_span_routes.py` if present).

## Scope Boundaries

**In scope:**

- New `turn_manager.round_invariant` OTEL span + SPAN_ROUTES entry.
- Invariant check at end of `_execute_narration_turn` reading both
  `turn_manager.round` and `MAX(narrative_log.round_number)`.
- Production fix wiring `advance_round` (or equivalent) into the
  resolution pipeline so the invariant holds going forward.
- Wire-first boundary test exercising the WS-driven narration loop
  and asserting the gap stays zero across multiple turns.
- Unit coverage for the new `max_narrative_round()` persistence helper.

**Out of scope:**

- Migrating `narrative_log.round_number` semantics or column name —
  defer until consumers (corpus, scrapbook, world history) are
  audited. The detector + advance fix closes Felix's gap without
  touching the column.
- Backfilling `turn_manager.round` on existing saves. The invariant
  detector logs the gap; existing saves with `round=65 / max=72`
  load and play with the gap visible. A migration is its own story
  if needed.
- Re-keying any specific gating consumer (arc generation, scrapbook
  backfill 45-10, trope cooldown 45-27) onto a different counter.
  Those stories own their gating choice; this story restores the
  invariant they all assume.
- Fixing `narrative_log.round_number = interaction` write at
  session_handler.py:3474 — that is intentional today (every
  narration is an interaction) and changing it would re-key every
  Lane B story. Out of scope here.

## AC Context

1. **`turn_manager.round_invariant` span fires on every narration turn,
   regardless of whether the invariant holds.**
   - Test: drive 5 narration turns through `_execute_narration_turn`;
     assert exactly 5 spans fired and each carries `round`,
     `interaction`, `max_narrative_round`, `gap`, `holds`.
   - Wire-first: drive via the WS message loop, not by calling a
     helper directly. The span must be reachable from the production
     code path.

2. **`turn_manager.round` does not lag `MAX(narrative_log.round_number)`
   after the production fix lands.**
   - Test: drive 10 narration turns; at every tick assert
     `snapshot.turn_manager.round == max(narrative_log.round_number)`.
     `gap == 0` and `holds == True` on every span.
   - Negative test: synthesize divergence (decrement `round` mid-test,
     run one more turn) and assert the span fires once with
     `holds=False`, `gap>0`. Sebastien needs to see the violation
     captured, not silently corrected.

3. **Span routes through SPAN_ROUTES to the GM panel watcher feed.**
   - Test: register the span, run a turn, assert the typed
     `state_transition` watcher event fired with
     `component="turn_manager"`, `field="round_invariant"`, and
     attributes lifted from the span. Mirrors the existing route
     pattern at `telemetry/spans.py:332-336`.

4. **`max_narrative_round()` persistence helper returns the correct
   value across edge cases.**
   - Empty `narrative_log` → returns 0 (or `None`, caller's choice
     codified in tests). The invariant span's `max_narrative_round`
     attribute is `0` on a brand-new session.
   - Single row → returns that row's `round_number`.
   - 100 rows with non-monotonic insertion order → returns the SQL
     `MAX`, not the last-inserted.

5. **No regression to existing `mp.barrier_fired` /
   `mp.round_dispatched` events.**
   - Regression test: the events at `session_handler.py:3232/3260`
     still emit with the post-fix `round` value, which now tracks
     interaction. No callers downstream of those events break.

6. **Existing `record_interaction()` semantics preserved.**
   - Regression test: `interaction` still advances by 1 per narration;
     `phase` still resets to `InputCollection`; `_submitted` still
     clears. Whatever wiring choice lands for `round` advance is
     additive — the existing per-turn sequence at line 95-100 must
     not regress.
