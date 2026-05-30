---
parent: context-epic-73.md
workflow: tdd
---

# Story 73-3: advance_confrontation lost-update fix

> **Type:** bug · **Points:** 3 · **Repo:** sidequest-server · **Workflow:** tdd
> **Epic:** 73 — Confrontation Engine Hardening
> Read the parent epic context first: `sprint/context/context-epic-73.md`.

## Business Context

`advance_confrontation` is the narrator's **only** off-roll lever for moving a
confrontation dial. Under the default `beat_selection` resolution mode, the
opponent dial never advances from a roll — the narrator must call this WRITE tool
to nudge `opponent_metric.current` (e.g. "the witness's composure cracks two
points"). Even after Epic 73 converts the social siblings to `opposed_check`
(73-1/73-2), this tool remains the sanctioned path for narrator-fiat dial nudges
that aren't backed by an opposed roll.

Today that nudge **silently disappears**. The tool reads a fresh copy of the
session from Postgres, mutates the dial on that copy, and saves it — but the
narration pipeline holds a *different*, canonical in-turn snapshot object, and its
end-of-turn save writes that canonical object back over the tool's write. The dial
move is lost. From the table's perspective: the narration says "the witness is
rattled, two steps closer to breaking," the GM panel may even show a
`tool.confrontation` span, and then next turn the dial is exactly where it was.
The confrontation can stall or never resolve on the opponent's side — the same
class of "this duel can't end" failure 59-8 found for `social_duel`, but arriving
through a state-coherence bug rather than a missing roll.

**Who this serves.** Sebastien and Jade are the group's mechanics-first players;
they read the dial as the real state of the contest. A dial that visibly moves in
the prose and the GM panel but then reverts is exactly the "Claude is improvising
with no mechanical backing" failure the OTEL lie-detector exists to catch — except
here the span fires *and lies*, because it reports the write the tool made to a
doomed snapshot. Keith and Jade as forever-GMs need the off-roll nudge to be a
real, durable mechanical act, not theater. This is drawing-room `tea_and_murder`'s
primary mechanical surface; the dial has to mean something.

## Technical Guardrails

### The bug (read-modify-write against the wrong snapshot object)

`sidequest/agents/tools/advance_confrontation.py:117-135`:

```python
session = ctx.repository.load()        # FRESH SavedSession deserialized from PG
snapshot = session.snapshot            # a NEW GameSnapshot object — NOT canonical
encounter = snapshot.encounter
metric = encounter.player_metric if args.axis == "player" else encounter.opponent_metric
metric.current = value_before + args.delta
ctx.repository.save(snapshot)          # persists the fresh copy...
```

The clobber is **deterministic ordering, not a race.** The narration pipeline runs
the whole turn against one canonical `GameSnapshot` instance. Under ADR-037 the
`SessionRoom` *owns* that canonical snapshot (`session_room.py:265` binds it,
`session_room.py:270-272` exposes it, `session_room.py:287-297` `room.save()`
persists `self._store.save(self._snapshot)`). At end of turn the handler calls
`room.save()` (or, on the legacy non-slug path,
`repository.save(self._session_data.snapshot)` —
`websocket_session_handler.py:456`, `:1172`,
`session_handler` disconnect path `:~456`). That save writes the **canonical**
object — the one `apply_beat` and every other in-turn engine mutated — and it runs
*after* the tool. The tool's `repository.save(fresh_snapshot)` is overwritten.

`repository.load()` returns a brand-new `SavedSession`
(`game/repository.py:112`, `game/pg/save_repository.py:148`) deserialized from
Postgres. Its `.snapshot.encounter` is a *different `EncounterMetric` object* than
the canonical `snapshot.encounter.opponent_metric` the rest of the turn (and the
end-of-turn save) operates on. So even setting aside the clobber, the tool is
mutating an object nobody else reads.

### The reference path that works (the seam to mirror)

`apply_beat`-driven dial moves **persist** because they mutate the canonical
snapshot. In `narration_apply.py` the engine reads `snapshot.encounter`
(e.g. `:2648`, `:4142`, the per-side `apply_beat` calls around `:3159`) where
`snapshot` IS the canonical in-turn object. No fresh load, no separate save — the
mutation rides the same object the end-of-turn save persists. **`advance_confrontation`
must reach that same canonical `snapshot.encounter`, not a `repository.load()` copy.**

### The canonical-snapshot seam

`ToolContext` (`tool_registry.py:84-142`) currently carries only
`repository: Any` — it has **no reference to the canonical in-turn snapshot**.
That absence is the root cause: with only the repository, the tool can do nothing
*but* `load()` a fresh copy. By contrast, `TurnContext` (the narrator-side context,
`orchestrator.py:867`, `snapshot: GameSnapshot | None`) DOES carry the canonical
`context.snapshot`. The `ToolContext` is constructed once per turn in
`orchestrator.py:3853` from that `TurnContext` (it already threads `repository`,
`lore_store`, `monster_manual`, `genre_pack`, world-grounding from `context.*`).

**The fix shape (route through canonical, don't `load()`):** give the WRITE tool a
handle to the canonical snapshot the rest of the turn mutates, and mutate *that*,
so the dial move survives the end-of-turn save. Concretely, thread the canonical
snapshot reference onto `ToolContext` at the `orchestrator.py:3853` construction
site (sourced from `context.snapshot`, mirroring how `genre_pack=context.pack` and
the grounding fields are threaded), and in `advance_confrontation.py` mutate
`ctx.<canonical-snapshot>.encounter.<metric>` instead of
`ctx.repository.load().snapshot.encounter.<metric>`. Drop the tool's own
`ctx.repository.save(...)` — the end-of-turn canonical save is now the single,
correct persistence point (a WRITE tool that participated in the canonical snapshot
should not race its own save against the pipeline's).

- **No silent fallback** (CLAUDE.md `<critical>`): if the canonical snapshot is not
  wired onto `ToolContext`, the tool must **fail loudly** (`ToolResult.error(...,
  recoverable=False)`), not quietly fall back to `repository.load()`. A silent
  fallback would reintroduce the exact lost-update this story fixes and mask the
  wiring regression. Preserve the existing fail-loud guards (no session / no
  encounter at `:119-128`).
- **Don't reinvent — wire up what exists.** The canonical snapshot already exists
  on `TurnContext.snapshot` and is already plumbed to the `ToolContext`
  construction site. This is a wiring fix (add one threaded field + change the
  mutation target), not new persistence machinery.
- **No new save.** The end-of-turn `room.save()` / `repository.save(canonical)` is
  the persistence point. Adding another `save()` on the canonical object inside the
  tool is redundant and re-creates an ordering hazard.

### OTEL (the lie-detector must now tell the truth)

The tool already emits `tool.confrontation.{id,axis,delta,value_after,reason,
crossed_threshold}` (`advance_confrontation.py:139-144`). After the fix those
attributes describe a mutation to the **canonical** dial that will actually persist
— that is the point. Per the epic's 73-3 directive and the CLAUDE.md OTEL
principle, **add/verify an OTEL signal that the advance survives past the
end-of-turn save** so the GM panel can confirm persistence, not just intent.
Surface that the mutation targeted the canonical snapshot (e.g.
`tool.confrontation.canonical=true` / a `persisted_delta` the test can correlate
against `value_after - value_before`). Reuse `encounter.metric_advance`
(`telemetry/spans/encounter.py`, per the epic key-files table) if it is the natural
home; do not invent a parallel span family.

## Scope Boundaries

**In scope (73-3 only):**
- `sidequest/agents/tools/advance_confrontation.py` — change the mutation target
  from a fresh `repository.load()` snapshot to the canonical in-turn snapshot;
  remove the now-redundant in-tool save; preserve fail-loud guards.
- `sidequest/agents/tool_registry.py` — thread the canonical snapshot onto
  `ToolContext` (new field, mirroring the existing optional context fields).
- `sidequest/agents/orchestrator.py:3853` — populate the new field from
  `context.snapshot` at the construction site.
- OTEL: assert/extend the span so persistence past end-of-turn is observable.
- `tests/agents/tools/test_advance_confrontation.py` (and/or a new sibling) —
  add the lost-update regression + composition + OTEL-persistence tests.

**Out of scope:**
- **73-1 / 73-2 recipe conversions** (`negotiation`/`scandal`/`trial` →
  `opposed_check`, `rules.yaml` edits, `opponent_default_stats`, threshold
  recalibration). Do not touch `sidequest-content` or
  `tests/genre/test_confrontation_calibration.py`.
- **73-4** push/angle CritSuccess legibility (`beat_kinds.py` `DEFAULT_DELTAS`,
  beat-kind reporting). The dial math is unchanged here.
- **73-5** confrontation_initiated span suppression
  (`confrontation.py` / `orchestrator.py` extraction log).
- The `confrontation_id` registry / multi-confrontation support — still
  forward-compat; v1 targets `snapshot.encounter`. Do not implement the registry.
- Clamping `metric.current` — the engine intentionally does not clamp
  (`advance_confrontation.py:91-98`); keep that behavior.
- General WRITE-tool save refactors for other tools — scope to
  `advance_confrontation`.

## AC Context

No explicit ACs existed; these are derived. **Server rule: assert behavior and
OTEL spans, never source text** (CLAUDE.md "No Source-Text Wiring Tests"). Drive
the tool through the real handler against a canonical snapshot, simulate the
end-of-turn save, and assert on persisted state + emitted spans.

- **AC1 — Dial move survives the end-of-turn save (the lost-update fix).** Given an
  active `StructuredEncounter` on the canonical snapshot, when the narrator calls
  `advance_confrontation(axis="opponent", delta=N)` and then the pipeline performs
  the end-of-turn canonical save (`room.save()` /
  `repository.save(canonical_snapshot)`), the persisted `opponent_metric.current`
  reflects the delta. **Regression test:** assert that after the tool call *and* a
  subsequent canonical save, the loaded value equals `before + N` — not `before`.
  (A test that asserts only the tool's return payload would pass against the buggy
  code; the load-after-canonical-save is the load-bearing assertion.)

- **AC2 — The tool mutates the canonical in-turn snapshot, not a fresh load.**
  Construct a `ToolContext` carrying a canonical snapshot object; after the call,
  assert the **same object instance** the pipeline holds reflects the new dial
  value (object identity / mutation-in-place), and that the tool did not depend on
  `repository.load()` to find its target. If the canonical snapshot is absent on
  the context, the tool fails loudly (`ToolResult.error(... recoverable=False)`) —
  no silent `repository.load()` fallback.

- **AC3 — Sequential advances within one turn compose.** Two
  `advance_confrontation` calls in the same turn (e.g. `opponent +2` then
  `opponent +3`, or `player +2` then `opponent +1`) compose to the cumulative dial
  state on the canonical snapshot, and that cumulative state persists through the
  single end-of-turn save (no second call clobbering the first). Per-side
  composition: advancing `player` then `opponent` leaves both deltas intact.

- **AC4 — Advance + resolve in the same turn.** When an advance crosses a metric's
  threshold (`crossed_threshold == True`) and the encounter resolves that same turn
  (a `push`/`resolution` beat or dial ≥ threshold), the resolved state AND the
  crossing dial value both persist through the end-of-turn save — the resolution
  reads the canonical dial the tool moved, and a confrontation that ends this turn
  records the final dial, not a clobbered one.

- **AC5 — OTEL confirms persisted delta matches intended delta.** The emitted
  confrontation/metric-advance span reports the delta that actually lands on the
  canonical snapshot (`value_after - value_before == delta`), and a signal
  distinguishes "mutated the canonical snapshot" from the old fresh-load path
  (e.g. `tool.confrontation.canonical` / persisted-delta attribute). Assert the
  span fires with attributes matching the post-save persisted state — the GM panel
  must be able to verify the advance is real, closing the "span fires but the write
  is lost" lie.

**Edge cases to cover (from the epic directive):**
- Multiple advances in one turn (AC3) — including same-axis accumulation and
  mixed-axis.
- Advance + resolve in the same turn (AC4).
- Advance on a confrontation that ends that turn — the final dial value persists
  (covered by AC4; assert the resolved encounter's dial is the advanced value).
- Negative delta ("regroup"/"de-escalate" nudge): the engine does not clamp;
  assert a negative delta also persists canonically (regression symmetry with AC1).

## Assumptions

1. **The canonical snapshot is reachable from the `ToolContext` construction site.**
   `orchestrator.py:3853` already threads `context.repository`,
   `genre_pack=context.pack`, and the world-grounding fields from `TurnContext`,
   and `TurnContext.snapshot` (`orchestrator.py:867`) holds the canonical
   snapshot. The fix threads that reference the same way. If `context.snapshot` is
   `None` on a legacy/ad-hoc path, the tool fails loudly rather than silently
   loading a fresh copy.
2. **ADR-037 holds: the room owns the canonical snapshot and the end-of-turn save
   persists it once.** `session_room.py:265/270/287-297`. The fix relies on the
   tool's mutation riding that same object so the single canonical save carries it.
   The legacy non-slug path (`repository.save(self._session_data.snapshot)`,
   `websocket_session_handler.py:1172`) saves the same `self._session_data.snapshot`
   the `ToolContext` should reference — verify both paths reference the same object.
3. **`advance_confrontation` is sequentially executed per session** (the Registry
   `_write_locks` map, `tool_registry.py:162`; documented at
   `advance_confrontation.py:53-57`), so within-turn composition (AC3) is ordered,
   not concurrent. "Concurrent advances" in the epic means multiple advances issued
   within one turn that must compose — not parallel writers. The bug is a
   deterministic lost-update, not a data race.
4. **Test harness:** the existing suite builds `ToolContext` via `_make_ctx` and a
   PG-backed store via `tests/agents/tools/conftest.pg_store_with`
   (`test_advance_confrontation.py:106-126`). The new tests extend that harness to
   (a) hold a canonical snapshot reference and (b) simulate the end-of-turn
   canonical save, then load-and-assert. Reuse `pg_store_with`; do not stand up a
   new persistence path.
5. **No protocol/UI change.** This is a server-internal state-coherence fix. The
   tool's args model and result payload shape stay stable (modulo the OTEL
   attribute additions); 73-4 owns player-facing mechanical readout changes.
6. **No new ADR.** This fixes an implementation defect against the existing
   ADR-033/ADR-037 contracts; it does not change a decision.
