---
parent: sprint/epic-45.yaml
workflow: wire-first
---

# Story 45-19: world_history arcs extend past turn 30 — recompute campaign maturity on interval

## Business Context

**Playtest 3 evidence (2026-04-19, evropi session — Felix):** session reached
turn 72; `snapshot.world_history` contained four arcs covering turns 1-30
only. Turns 31-72 ran with a stale 30-turn-old historical context block in
the narrator prompt's Valley zone. `campaign_maturity` was never recomputed
after the chargen-time `Fresh` materialization, so the narrator's
state_summary kept reporting `campaign_maturity="Fresh"` long after the
session entered Veteran territory (51+).

The pattern is a Lane B canonical write-back failure: the chargen path
writes once (`materialize_from_genre_pack(..., CampaignMaturity.Fresh, ...)`
at `session_handler.py:2652–2657`), and no subsequent caller exists for
`materialize_world()` (the in-place updater at `world_materialization.py:466`
that is *designed* to recompute maturity from the current snapshot). The
extractor (`CampaignMaturity.from_snapshot`) and applier (`materialize_world`)
exist as a complete round-trip but are not wired to fire on a turn cadence.

**Audience tie:** James (narrative-first) loses story texture when the
narrator forgets the campaign has aged — beats fired thirty turns ago are
all the prompt remembers. Sebastien (mechanical-first) needs the OTEL span
to verify the maturity tier is climbing; without the span the GM panel
cannot distinguish "arc tick fired and no chapter promoted" from "arc tick
silently never fired."

**ADR linkage:**
- **ADR-014 (Diamonds and Coal):** the existing maturity-derivation diamond
  (`from_snapshot`) is being treated as coal because no caller invokes it
  past chargen.
- **ADR-031 (Game Watcher / OTEL):** every Lane B fix emits a span on the
  write path. The arc tick is a write — even when the tier doesn't change,
  the GM panel needs to see the tick.
- **ADR-067 (Unified Narrator Agent):** the narrator reads `state_summary`
  built from `snapshot.model_dump_json()` at `session_helpers.py:226`;
  recomputing `campaign_maturity` and `world_history` before that line is
  what makes the fix visible to prose.

This is **P2** — important but downstream of Lane A (45-2/45-3) for sprint
ordering. The fix is bookkeeping, not correctness-critical, and it exists
because Felix's solo run made the divergence legible at turn 72.

## Technical Guardrails

### Outermost reachable layer (wire-first seam)

The wire-first gate requires the test to exercise the actual recompute seam,
**not** a unit test on `materialize_world` alone. Two seams must be hit:

1. **Turn-tick → arc-recompute seam** — fire the recompute from inside
   `_execute_narration_turn()` at `sidequest/server/session_handler.py:3286–3490`,
   immediately after `snapshot.turn_manager.record_interaction()` at
   `session_handler.py:3424`. That is the only point post-turn where the
   round counter is authoritative for the just-completed turn.
2. **Recompute → state_summary seam** — the recomputed
   `snapshot.world_history` / `snapshot.campaign_maturity` must be in place
   *before* `state_summary_payload = json.loads(snapshot.model_dump_json())`
   at `session_helpers.py:226`. The next narrator turn is what consumes the
   output; without this seam the recompute is dead code.

Boundary tests must drive both seams via the WS-driven dispatch path using
`session_handler_factory()` at `tests/server/conftest.py:332` and the
`_FakeClaudeClient` at `conftest.py:197` so the chapter-promotion can be
asserted on the JSON the orchestrator receives, not the in-memory snapshot
alone.

### Recompute predicate (THE FIX)

The fix is to call `materialize_world(snapshot, chapters)` on a cadence,
where `chapters` is the same parsed pack history that chargen used. The
session-data needs to retain the parsed chapter list so we are not re-
parsing `history.yaml` per turn — extend `_SessionData` at
`sidequest/server/session_handler.py` with a `cached_history_chapters:
list[HistoryChapter]` field, populated alongside the chargen-time
materialization at `session_handler.py:2647–2693`.

**Tick cadence — design choice required, default to every-N interactions:**
the bug calls for "arc generation must run on interval past session cap."
Recommend `ARC_RECOMPUTE_INTERVAL = 5` interactions; the recompute is
idempotent on stable maturity (`materialize_world` is "Idempotent — safe to
call repeatedly" per docstring at `world_materialization.py:472`). Cadence
must be a module-level constant in `world_materialization.py` so a future
tuning pass adjusts one site.

**Unbounded growth past turn 50** — `CampaignMaturity` tops out at `Veteran`
(turns 51+, `world_materialization.py:62`). After Veteran, `materialize_world`
returns the same chapter set every tick; that is correct, NOT a bug. The
story's "extend past turn 30" framing is about closing the gap between
chargen's `Fresh` start and the snapshot's actual maturity — once the
snapshot reaches Veteran, ticks become idempotent confirmations and the
OTEL span is the only observable.

### OTEL spans (LOAD-BEARING — gate-blocking per CLAUDE.md OTEL principle)

Define in `sidequest/telemetry/spans.py` and register `SPAN_ROUTES`:

| Span | Attributes | Site |
|------|------------|------|
| `world_history.arc_tick` | `interaction`, `round`, `from_maturity`, `to_maturity`, `chapters_before`, `chapters_after`, `tier_changed` (bool), `cadence_interval` | every recompute call (fires regardless of whether the tier changed — the no-op tick is the lie-detector signal Sebastien needs) |
| `world_history.arc_promoted` | `interaction`, `from_maturity`, `to_maturity`, `chapters_added` (list of chapter ids) | only fires when `tier_changed=True`, scoped for filtered GM-panel views of the meaningful transitions |

The `arc_tick` span MUST fire on every recompute, not only on
"tier_changed=True". The bug is the silent no-tick; if the span only emits
on tier transitions the panel cannot tell whether the tick is firing at all.

### Reuse, don't reinvent

- `CampaignMaturity.from_snapshot()` at `world_materialization.py:65–83`
  already derives maturity from `turn_manager.round + total_beats_fired/2`.
  Use it; do not re-implement the formula.
- `materialize_world(snapshot, chapters)` at `world_materialization.py:466`
  is the exact in-place applier the bug is asking for. The function is
  documented as idempotent and stateless. Wire it; do not author a parallel
  recomputer.
- `_world_history_value()` at `session_helpers.py:281` reads the raw pack
  history. `parse_history_chapters()` at `world_materialization.py:140`
  parses it. Both already run at chargen — cache the parsed list on
  `_SessionData` at chargen success rather than re-parsing per tick.
- `materialize_from_genre_pack()` at `world_materialization.py:490` is the
  chargen entry point; do NOT call it for recompute (it builds a fresh
  snapshot via `WorldBuilder.build()` and would discard live state).

### Test files (where new tests should land)

- New: `tests/game/test_world_materialization_recompute.py` — unit tests for
  the cadence predicate and `materialize_world` invocation past turn 30 /
  turn 50 / turn 100 boundaries.
- Extend: `tests/server/test_narration_turn_dispatch.py` (or the closest
  existing `_execute_narration_turn` integration test) — wire-first
  boundary test driving 35+ turns through the WS path and asserting
  `world_history` chapter count grows from `Fresh` (1 chapter) through
  `Early` / `Mid` / `Veteran` as the turn count crosses thresholds.
- Extend: `tests/telemetry/test_spans.py` — assert
  `SPAN_WORLD_HISTORY_ARC_TICK` is registered and the helper builds attrs
  matching the table above.

## Scope Boundaries

**In scope:**

- `_SessionData.cached_history_chapters: list[HistoryChapter]` populated at
  `session_handler.py:~2657` after the first-commit materialization.
- `ARC_RECOMPUTE_INTERVAL` constant + `should_recompute_arc(interaction:
  int) -> bool` predicate in `world_materialization.py`.
- Recompute call from `_execute_narration_turn()` at the post-
  `record_interaction()` site (`session_handler.py:3424`), gated on the
  predicate.
- Two new OTEL spans: `world_history.arc_tick` (always-fire) and
  `world_history.arc_promoted` (transition-fire). Register `SPAN_ROUTES`
  entries so the GM panel surfaces them as state-transition events.
- Wire-first boundary test reproducing Felix's evropi scenario: drive a
  session past turn 30, assert `snapshot.world_history` advances through
  the `Early`/`Mid`/`Veteran` chapters, and that the recompute did NOT
  re-author scene context (location/atmosphere/active_stakes — those
  fields belong to the live snapshot, not chapter chrome).

**Out of scope:**

- **NEW arc generation past Veteran.** `CampaignMaturity` has four tiers;
  ticks past Veteran are idempotent. A future story can add a "Legendary"
  tier or LLM-generated arcs, but that is a content-pipeline question, not
  a state-write fix.
- **45-23 (arc-embedding writeback to narrative_log/lore).** That story is
  the *consumer* of the arc tick. 45-19 must emit the `arc_promoted` span
  but MUST NOT itself write into `narrative_log` or `lore_store`. Crossing
  the boundary collapses two stories into one and obscures which fix
  fired. The two stories' OTEL spans are the contract: 45-19 emits
  `arc_promoted`, 45-23 listens and writes back.
- **Trope progression / resolution.** 45-20 owns the trope `Resolved` →
  `quest_log` write-back. The `_apply_trope` upsert in `WorldBuilder`
  (`world_materialization.py:429`) DOES update active_tropes, but only
  via chapter promotion — that is a side-effect of the recompute the
  current story owns, not a cross-cutting concern.
- **Schema migration / save-file changes.** `world_history` and
  `campaign_maturity` are already on `GameSnapshot`
  (`session.py:383–384`); the recompute mutates them in place and the
  existing save round-trip handles it.
- **Narrator prompt template changes.** Only the JSON the narrator sees
  changes (chapter count grows, maturity string climbs); no edits to the
  prompt scaffolding.

## AC Context

The story description carries the contract; we expand it into testable ACs:

1. **Recompute fires on a regular cadence past chargen.**
   - Test: drive a session through 35 narration turns via the WS dispatch
     path. Assert `world_history.arc_tick` span fires `35 //
     ARC_RECOMPUTE_INTERVAL` times (e.g. 7 times at interval=5).
   - Test verifies the wire (the call happens), not just the helper.

2. **`world_history` chapter set grows as the turn count crosses tier
   boundaries.**
   - Test: drive past turn 6 → assert `Early` chapter present; past turn
     21 → `Mid`; past turn 51 → `Veteran`. Chapters are cumulative
     (per `WorldBuilder.build` semantics at `world_materialization.py:215`).
   - Negative: a session at turn 30 with `total_beats_fired=0` is `Mid`,
     not `Veteran` — confirms `from_snapshot` formula (round +
     beats_fired // 2) is the predicate, not raw turn count.

3. **Arc tick past turn 100 is a no-op confirmation.**
   - Boundary test at turn 100: `arc_tick` span fires, `tier_changed=False`,
     `chapters_before == chapters_after`. Confirms the recompute is
     idempotent and the cadence is unbounded — the bug Felix saw at turn 72
     does not recur at higher turns.

4. **OTEL `world_history.arc_tick` span fires on every tick with both maturity
   values.**
   - Test: trigger 5 ticks; assert each span carries `from_maturity` and
     `to_maturity` (equal when tier_changed=False), `chapters_before`,
     `chapters_after`, `interaction`, `round`. Verify SPAN_ROUTES
     registers the watcher mapping so the GM panel sees the events.
   - Sebastien's lie detector requires the no-tier-change tick to be
     observable — the divergence between "tick happened, no promotion" and
     "tick never fired" is the story.

5. **`world_history.arc_promoted` span fires once per tier transition.**
   - Test: drive a session from turn 0 through turn 60. Assert
     `arc_promoted` fires exactly three times (Fresh→Early at turn 6,
     Early→Mid at turn 21, Mid→Veteran at turn 51), each with the
     correct `from_maturity`, `to_maturity`, and `chapters_added` list.

6. **Live snapshot fields are not clobbered by recompute.**
   - Negative / regression test: between recomputes, mutate
     `snapshot.location`, `snapshot.active_stakes`, `snapshot.atmosphere`
     to non-chapter values. After the next recompute, those fields
     remain the live values — `materialize_world` per its docstring only
     sets `world_history` and `campaign_maturity` (`world_materialization.py:481–482`),
     unlike `WorldBuilder.build` which also overwrites scene context.
     This is the contract that lets the recompute be idempotent and safe
     mid-session.
