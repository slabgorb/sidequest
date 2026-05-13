# 50-4 — Trope `rate_per_day` Between-Session Advancement

**Date:** 2026-05-13
**Story:** 50-4 (sprint 3, Playtest 3 closeout)
**Original estimate:** 5 points
**Re-estimate after design:** ~8 points (new narrator field, prompt teaching, snapshot field, persistence, Pass A2, prompt-assembly integration, OTEL span, tests, ADR amendment)
**ADR:** Closes the last remaining gap in ADR-018 (line 81). Updates ADR-018's implementation-status block.
**Related:** ADR-031 (game watcher telemetry), ADR-039 (narrator structured output), ADR-058 (Claude subprocess OTEL passthrough), ADR-009 (attention-aware prompt zones)

## Problem

The trope engine's `rate_per_day` field exists on `TropeDefinition.passive_progression` and every wired genre pack populates it (`tea_and_murder` 0.01–0.04, `space_opera` 0.008–0.02, `mutant_wasteland` 0.02–0.05, `caverns_and_claudes` 0.0 by design). No code path consumes it. SOUL.md's Living World pillar is unwired for trope pacing — when a session resumes after a real-world week, or when the narrator emits "two weeks of investigation pass," progressing tropes do not drift, off-screen plot does not advance, and the world stops feeling alive between scenes.

## Locked design decisions

| Decision | Choice | Reasoning |
|---|---|---|
| What "day" means | **In-game day**, narrator-driven | Wall-clock would bind drift to real-world session cadence; an unplayed month would resolve every trope. In-fiction days match how the playgroup actually paces stories. |
| Day source | **Narrator emits `days_advanced: int`** in `game_patch` | Piggybacks on the existing structured-output protocol (ADR-039). Narrator already decides time passage when it patches `time_of_day`. |
| Tick trigger | **On any turn with `days_advanced > 0`** | "Between sessions" reframes as "between in-game days." Time only passes when fiction says so. Naturally bridges both session boundaries and mid-session time skips. |
| Beat firing | **Fire all crossed beats**, summary fed to next turn | A 14-day jump that crosses three thresholds means three things happened. Stagger discipline is a within-realtime constraint; a time skip is explicitly out-of-band. |
| Drift cap | **Hard cap of 14 days per tick** | Clamps narrator over-emission ("a year later") that would otherwise resolve every trope in one turn. Configurable per pack is YAGNI for v1. |
| Tick architecture | **New Pass A2** between Pass A and Pass B | Clean separation from `rate_per_turn` (Pass A); distinct OTEL span; multi-beat logic isolated. |
| Summary surface | **TIME-SKIP CONTEXT prompt section**, prominent | High-stakes mechanical state goes near the top per ADR-009. Distinct named section in OTEL prompt replay. |
| Summary lifecycle | **One-shot, cleared on consumption** | Simpler protocol. If narrator turn fails before clearing, list stays populated for next attempt. |

## Architecture

The narrator decides when time advances. When its structured output includes `days_advanced > 0`, a new trope-engine pass advances every progressing trope by `clamp(days, 0, 14) * rate_per_day`, fires every crossed beat, and queues a summary that the *next* narrator turn renders as prose.

```
[narrator turn N]                                              [narrator turn N+1]
  emits days_advanced=7  ───►  trope_tick.tick_tropes()  ───►   prompt builder reads
                                  Pass A  (rate_per_turn)        pending_time_skip_summary,
                                  Pass A2 (rate_per_day × 7)     renders TIME-SKIP CONTEXT block,
                                       └► fires crossed beats     clears the field
                                       └► appends to summary
                                  Pass B  (staggered fire)
                                  └► emits trope.time_skip span
```

Three repos touched:

- **sidequest-server** — protocol field, snapshot fields, persistence, Pass A2, prompt assembly, OTEL span, tests
- **sidequest-content** — no per-pack changes; every pack's `rate_per_day` values are already populated
- **orchestrator** — ADR-018 amendment removing the "remaining gap" bullet

## Protocol changes

Add one optional integer field to the narrator `game_patch`:

```jsonc
"game_patch": {
  // ... existing fields ...
  "days_advanced": 7   // optional, default 0; in-game days elapsed THIS turn
}
```

### Narrator emission rule (added to `output_only.md`)

> CRITICAL TIME RULE: If your narration spans more than one in-game day — overnight rest, hard cut ("the next morning"), fast travel sequence, or explicit time skip ("a week of investigation passes") — you MUST emit `days_advanced` set to the integer day count elapsed during this turn. Sub-day passage (a few hours, sunset to nightfall, an afternoon's negotiation) is `time_of_day` only — do NOT emit `days_advanced`. Multi-day jumps without `days_advanced` mean tropes don't drift, off-screen plot stalls, and the world stops feeling alive between scenes.

Examples appended to the prompt:

- "By dawn, the cook was missing" → `days_advanced: 1`
- "A week of cold leads later, she returned to the manor" → `days_advanced: 7`
- "They argued until sundown" → `days_advanced: 0` (sub-day; `time_of_day` only)

### Wire-up sites

- `sidequest/protocol/` — `GamePatch` model gains `days_advanced: int = Field(default=0, ge=0)` (pydantic validator: non-negative int)
- `sidequest/agents/narrator_prompts/output_only.md` — rule + examples + `days_advanced` added to the valid-fields list on line 7
- `sidequest/server/narration_apply.py` — after parsing the `NarrationTurnResult`, extract `result.days_advanced` and pass it to `tick_tropes(..., days_advanced=N)`. No interim turn-context structure needed; the field is read once at the apply site and consumed in the same call frame.

## State & persistence

### Snapshot fields (new)

```python
# sidequest/game/session.py — Snapshot
days_elapsed: int = 0                                  # cumulative in-game day counter, monotonic
pending_time_skip_summary: list[TimeSkipBeatEvent] = Field(default_factory=list)
```

### TimeSkipBeatEvent model (new)

Co-located in `sidequest/game/trope_tick.py` (or new file `trope_time_skip.py` if Pass A2 plus model exceeds ~150 lines together).

```python
class TimeSkipBeatEvent(BaseModel):
    model_config = {"extra": "forbid"}
    trope_id: str                # e.g. "murder_mystery_clock"
    trope_name: str              # human-readable
    beat_index: int              # which escalation step (0-based)
    beat_event: str              # TropeEscalation.event text
    stakes: str                  # low/medium/high/climactic
    npcs_involved: list[str]
    days_into_skip: int          # 1..N within the skip — for narrator ordering
```

### Delta wiring

```python
# sidequest/game/delta.py — SnapshotFlags
days_elapsed: bool = False
pending_time_skip_summary: bool = False
```

Both fields compared in `SnapshotFlags.detect_changes()`. Reactive state messaging (ADR-027) surfaces them to the client mirror.

### SQLite persistence

Schema bump in `persistence.py`:

- New columns on session table:
  - `days_elapsed INTEGER NOT NULL DEFAULT 0`
  - `pending_time_skip_summary TEXT NOT NULL DEFAULT '[]'` (JSON-encoded list)
- `schema_version` bumps by 1
- One-shot ALTER TABLE migration runs on load if a save's schema_version is below the new bump

Default values mean every existing save loads cleanly: `days_elapsed=0`, empty summary. Caverns saves don't notice the change (rate_per_day=0.0 everywhere).

## Pass A2 algorithm

Constants:

```python
DAY_TICK_CAP = 14  # hard cap; ADR-follow-up could later move to genre pack
```

Pass A2 sits in `trope_tick.py`. Runs after Pass A, before Pass B. Guarded by `days_advanced > 0`.

```python
def _pass_a2_time_skip(
    snapshot: Snapshot,
    genre_pack: GenrePack,
    days_advanced: int,
    now_turn: int,
) -> TimeSkipSpanFields:
    days_applied = max(0, min(days_advanced, DAY_TICK_CAP))
    if days_applied == 0:
        return TimeSkipSpanFields(days_requested=days_advanced, days_applied=0, beats_fired=[])

    beats_fired: list[TimeSkipBeatEvent] = []
    tropes_affected: list[str] = []
    tropes_skipped_zero_rate: list[str] = []
    resolved_during_skip: list[str] = []

    for tdef, tstate in _progressing_tropes(snapshot, genre_pack):
        rate = (tdef.passive_progression and tdef.passive_progression.rate_per_day) or 0.0
        if rate <= 0.0:
            tropes_skipped_zero_rate.append(tdef.id)
            continue

        progress_before = tstate.progress
        progress_after = min(1.0, progress_before + rate * days_applied)
        if progress_after == progress_before:
            continue

        tstate.progress = progress_after
        tropes_affected.append(tdef.id)

        # Fire EVERY crossed beat
        for idx, beat in enumerate(tdef.escalation):
            if idx < tstate.beats_fired:
                continue
            if beat.at <= progress_after:
                days_into = max(1, round((beat.at - progress_before) / rate))
                beats_fired.append(TimeSkipBeatEvent(
                    trope_id=tdef.id,
                    trope_name=tdef.name,
                    beat_index=idx,
                    beat_event=beat.event,
                    stakes=beat.stakes,
                    npcs_involved=beat.npcs_involved,
                    days_into_skip=min(days_into, days_applied),
                ))
                tstate.beats_fired = idx + 1
                tstate.last_fired_turn = now_turn  # blocks Pass B re-firing same beat

        # Implicit resolution
        if progress_after >= 1.0 and tstate.beats_fired >= len(tdef.escalation):
            tstate.status = TropeStatus.RESOLVED
            resolved_during_skip.append(tdef.id)
            # trope_resolve span emitted via existing path

    # Order summary by (days_into_skip ASC, trope_id ASC) for chronological narrator presentation
    beats_fired.sort(key=lambda b: (b.days_into_skip, b.trope_id))
    snapshot.pending_time_skip_summary.extend(beats_fired)
    snapshot.days_elapsed += days_applied

    return TimeSkipSpanFields(
        days_requested=days_advanced,
        days_applied=days_applied,
        clamped=(days_advanced > DAY_TICK_CAP),
        beats_fired=beats_fired,
        tropes_affected=tropes_affected,
        tropes_skipped_zero_rate=tropes_skipped_zero_rate,
        resolved_during_skip=resolved_during_skip,
    )
```

### Ordering inside `tick_tropes`

1. **Pass A** — rate_per_turn (unchanged)
2. **Pass A2** — rate_per_day (new, conditional on `days_advanced > 0`)
3. **Pass B** — staggered single-beat fire (unchanged; sees post-A2 progress)

### Interaction notes

- **Pass B after A2:** Pass B's eligibility check (`beat.at > progress AND idx == beats_fired`) naturally excludes already-fired beats, so it cannot re-fire what A2 fired. It can still fire one *additional* beat for the highest-progress trope if A2 advanced progress past a fresh threshold without crossing the index.
- **Cooldown:** Dormant→progressing activation cooldown is unaffected (A2 only touches progressing tropes). Pass B's post-fire cooldown is updated via `last_fired_turn = now_turn` on each beat A2 fires.
- **Implicit resolution:** If `days_applied × rate` pushes progress to ≥1.0 AND all beats are fired, the trope resolves in this pass. Existing `trope_resolve` span emission path handles this.

## Narrator prompt integration

### Read + clear in prompt builder

In the narrator turn assembly path (`sidequest/agents/` prompt construction), before sending to Claude:

```python
if snapshot.pending_time_skip_summary:
    time_skip_block = _render_time_skip_context(
        snapshot.pending_time_skip_summary,
        snapshot.days_elapsed,
    )
    prompt_sections.append(time_skip_block)
    snapshot.pending_time_skip_summary = []   # one-shot, cleared
    # delta flag propagates the change for persistence
```

### Rendered block

Distinct named section near the top of the state context (above quest log, below current location). Position per ADR-009 — high-stakes mechanical state lives in the top attention zone.

```
## TIME-SKIP CONTEXT

The previous narration advanced time by 7 in-game days. The following developed off-screen during that span. Weave these into your next narration as has-already-happened context — the players are arriving INTO this changed state, not witnessing it unfold.

- Day 2 — murder_mystery_clock — "Another body found, identically posed" (stakes: high; npcs: constable_finch, victim_unnamed)
- Day 4 — gossip_propagation — "Servant rumor spreads beyond the household" (stakes: medium; npcs: maid_dorothy, vicar_pell)
- Day 6 — investigator_arc — "Lady Ashworth grows suspicious of the inspector" (stakes: medium; npcs: lady_ashworth, inspector_grey)

Acknowledge the time passage. Reference the most impactful items by stakes. You do not need to cite all beats — pick what serves the scene. Do NOT contradict any beat that fired.
```

The "Do NOT contradict" guardrail targets the specific failure mode (Lady Ashworth still trusts the inspector after the prompt said she suspects him). Compression and selective citation (per the Cut the Dull Bits pillar) is desirable, not a failure.

### Failure mode

If the narrator's prose makes no reference to time-skip events, the state-prose divergence is detectable in OTEL (`trope.time_skip` span has 3 beats fired; narrator prose has zero matching references). That's a prompt-tuning follow-up, not a state-corruption bug — beats already advanced `beats_fired`, summary was already cleared.

## OTEL & telemetry

New span emitted once per `tick_tropes` call where `days_advanced > 0`, regardless of whether any beats fired (zero-beat ticks are still useful telemetry — confirms drift happened).

```python
# sidequest/telemetry/spans.py — additions
SPAN_TROPE_TIME_SKIP = "trope.time_skip"

class TropeTimeSkipFields(BaseModel):
    days_requested: int                       # what narrator emitted
    days_applied: int                         # after cap
    clamped: bool                             # days_requested > DAY_TICK_CAP
    tropes_affected: list[str]                # trope_ids whose progress advanced
    tropes_skipped_zero_rate: list[str]       # progressing tropes with rate_per_day=0.0
    beats_fired_count: int                    # total across all tropes
    beats_fired: list[dict]                   # serialized TimeSkipBeatEvent list
    resolved_during_skip: list[str]           # trope_ids hitting implicit resolution
```

`trope.tick` (existing) continues to mean "Pass A rate_per_turn happened" — no `days_advanced` field added there. Separation is the Sebastien-axis test: looking at any span on the GM panel, you can answer "is this drift from in-session pacing or from a time skip?" without reading the trope state diff.

### GM panel surface

Session header gains a `Day N` indicator next to `time_of_day`. When a `trope.time_skip` span lands, the trope strip flashes with a `+Nd` badge on each affected trope; hover tooltip lists fired beats. One new event handler in `dashboard.html`, not a new panel.

### Span ordering in replay

```
narrator.turn (turn N)  → emits days_advanced=7
trope.time_skip          → days_applied=7, 3 beats fired
narrator.turn (turn N+1) → prompt contains TIME-SKIP CONTEXT block
```

Every causal step has a span.

## Testing strategy

TDD workflow per story config. Three layers + wiring test (mandatory per CLAUDE.md).

### Unit — `tests/game/test_trope_time_skip.py` (new)

- `test_pass_a2_no_op_when_days_zero` — `days_advanced=0` returns early, no state mutation
- `test_pass_a2_advances_progress` — single progressing trope, days=5 × rate=0.04 → progress +0.20
- `test_pass_a2_clamps_at_cap` — days=365 clamps to 14, `clamped=True` in span fields
- `test_pass_a2_fires_single_crossed_beat` — 7-day jump crosses one threshold → one `TimeSkipBeatEvent`
- `test_pass_a2_fires_multiple_crossed_beats` — 14-day jump on a trope with 3 beats clustered → all 3 fire, ordered by `days_into_skip`
- `test_pass_a2_skips_dormant_tropes` — dormant trope with rate_per_day=0.04 doesn't advance
- `test_pass_a2_skips_resolved_tropes` — resolved trope doesn't advance
- `test_pass_a2_zero_rate_no_op` — rate_per_day=0.0 (caverns pattern) does nothing even with days=14
- `test_pass_a2_implicit_resolution` — progress reaches 1.0 AND all beats fired → status = `RESOLVED`
- `test_pass_a2_updates_last_fired_turn` — `beats_fired` bumped per beat, `last_fired_turn = now_turn`
- `test_pass_b_respects_a2_fires` — Pass B after A2 doesn't re-fire the same beats
- `test_pass_b_can_still_fire_additional_beat` — if a trope has unfired beats after A2, Pass B may still fire one (highest-progress winner)
- `test_days_elapsed_increments_by_clamped_amount` — `snapshot.days_elapsed` advances by `days_applied`, not `days_requested`

### Snapshot/persistence — `tests/game/test_session_time_skip.py` (new)

- `test_days_elapsed_persists_round_trip` — write+load session, `days_elapsed` survives
- `test_pending_summary_persists_round_trip` — JSON column round-trips list of `TimeSkipBeatEvent`
- `test_delta_marks_days_elapsed_change` — `snapshot.diff` flags `days_elapsed=True` on change
- `test_delta_marks_pending_summary_change` — same for `pending_time_skip_summary`
- `test_migration_existing_save_loads_with_defaults` — schema-bump migration: old DB loads with `days_elapsed=0`, empty summary

### Wiring/integration — `tests/integration/test_trope_time_skip_e2e.py` (new, MANDATORY per CLAUDE.md)

- `test_narrator_days_advanced_advances_tropes` — feed narrator response with `days_advanced=7` through `narration_apply`, assert progressing trope advanced and summary populated
- `test_next_turn_prompt_contains_time_skip_context` — set pending summary, run prompt assembly, assert `## TIME-SKIP CONTEXT` header + each beat event text appears in the rendered prompt, AND assert summary is cleared post-assembly
- `test_otel_span_emitted_with_correct_fields` — capture watcher events, assert `trope.time_skip` span has `days_requested`, `days_applied`, `clamped`, `beats_fired_count`, `tropes_affected`

### Protocol — `tests/protocol/test_game_patch_days_advanced.py` (new)

- `test_days_advanced_field_parses` — narrator JSON with `days_advanced: 7` deserializes
- `test_days_advanced_defaults_zero` — omitted field defaults to 0
- `test_days_advanced_rejects_negative` — pydantic validator rejects negative ints
- `test_days_advanced_rejects_non_int` — string/float rejected

### Not tested (deliberate)

- "Fold into Pass A" path — rejected by design
- "Fire only lowest beat" path — rejected by design
- Wall-clock day calculation — rejected by design
- Accelerators/decelerators on rate_per_day — YAGNI, deferred

### Fixture impact

None. Genre packs already carry meaningful `rate_per_day` values. Caverns' 0.0 entries are themselves a test vector (no-op case).

## ADR amendment

`docs/adr/018-trope-engine.md` — update the "Remaining gaps" section. After this story merges:

- Strike the bullet: `**rate_per_day between-session advancement** — the data model carries the field, every genre pack's YAML can set it, but no code path consumes it...`
- Add an "Implementation update" paragraph dated to the merge day (use the actual merge date when writing) documenting Pass A2, the `days_advanced` narrator field, the cap, and the time-skip summary surface.
- Mark `implementation-status` accepted (currently `partial`).

`docs/adr/DRIFT.md` — remove ADR-018 from the drift list, or downgrade to "documentation drift only" since the ADR's prose lifecycle (`DORMANT → ACTIVE → PROGRESSING → RESOLVED`) still doesn't match the three-state implementation.

`docs/adr/087-post-port-subsystem-restoration-plan.md` — row 64 (trope engine) marked complete.

## Acceptance criteria

1. Narrator can emit `days_advanced: int` in `game_patch`; pydantic validates non-negative integer.
2. `narration_apply` calls `tick_tropes(..., days_advanced=N)` after applying the patch.
3. Pass A2 advances every progressing trope's progress by `clamp(days_advanced, 0, 14) × rate_per_day`.
4. Pass A2 fires every crossed beat threshold on each progressing trope.
5. `snapshot.days_elapsed` increments by `min(days_advanced, 14)`.
6. `snapshot.pending_time_skip_summary` is populated with `TimeSkipBeatEvent` entries sorted by `(days_into_skip, trope_id)`.
7. Next narrator prompt assembly renders a `## TIME-SKIP CONTEXT` section near the top of state context and clears the field.
8. `trope.time_skip` OTEL span fires with `days_requested`, `days_applied`, `clamped`, `tropes_affected`, `beats_fired_count`, `resolved_during_skip`.
9. GM panel session header shows `Day N` indicator.
10. Existing saves load cleanly post-migration with `days_elapsed=0`, empty summary.
11. Caverns pack (`rate_per_day=0.0` everywhere) shows zero drift even with `days_advanced=14`.
12. Pass B continues to fire one additional beat if a progressing trope has an unfired eligible beat after Pass A2.
13. All four test files above land with the unit/integration coverage listed.
14. ADR-018 amendment lands in the same PR.

## Out of scope

- Wall-clock day calculation (any `last_played`-based drift)
- Per-genre-pack day cap configuration (deferred until a pack proves it needs one)
- Accelerator/decelerator application to `rate_per_day` (YAGNI; never wired for `rate_per_turn` either)
- Narrator ack protocol for `pending_time_skip_summary` (one-shot clearing is sufficient)
- Dashboard warning when `pending_time_skip_summary` persists across multiple turns (deferred)
- ADR-018 lifecycle prose update (DORMANT → ACTIVE → PROGRESSING → RESOLVED vs. the three-state implementation) — documentation drift unrelated to this gap

## Risks

- **Narrator under-emits `days_advanced`.** Multi-day prose without the field means no drift. Mitigation: CRITICAL TIME RULE pattern (same shape as INVENTORY/LOCATION rules, which the model obeys reliably).
- **Narrator over-emits `days_advanced`.** "A year passes" → clamped to 14 days. Visible in OTEL as `clamped=True`; if it happens regularly, prompt tightening or per-pack cap follow-up.
- **Time-skip summary feels disconnected from prose.** The narrator pastes "another body was found" but doesn't connect it to live NPCs. Mitigation: summary includes `npcs_involved`, narrator already conditions on the NPC registry.
- **Stale summary if a narrator turn aborts before consumption.** Acceptable — one-shot lifecycle catches this on the next attempt. If a real bug emerges, dashboard warning is a quick follow-up.
