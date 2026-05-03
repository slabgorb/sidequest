# Turn Pipeline Phase Timing — Design

**Date:** 2026-04-26
**Author:** Architect (The Man in Black)
**Related:** ADR-090 (OTEL Dashboard Restoration), CLAUDE.md OTEL Observability Principle
**Status:** Draft for review

## Background

A SideQuest turn currently exposes a single timing field, `agent_duration_ms`, which captures only the narrator subprocess (`_client.send_with_session` in `agents/orchestrator.py:1467`). The server's `Validator` emits this same value under a second, misleading name: `total_duration_ms = record.agent_duration_ms` (`telemetry/validator.py:434-435`). The GM panel and any downstream consumer that reads `total_duration_ms` therefore sees the narrator's subprocess time, not the wall-clock turn duration.

Live playtest data (2026-04-26, single-player Victorian session) shows the gap this hides:

| Turn | Action received → narration_complete | `agent_duration_ms` | Pre-narrator gap |
|------|--------------------------------------|---------------------|------------------|
| 4 | 19:12:42 → 19:14:23 (101 s) | 14 336 | ~87 s |
| 5 | 19:21:05 → 19:21:55 (50 s) | 25 826 | ~24 s |
| 6 | 19:23:40 → 19:25:25 (105 s) | 17 908 | ~87 s |

Two of three turns show a recurring ~87 s pre-narrator gap — close to a 90 s timeout boundary, suggesting an LLM client retry pattern in `LocalDM.decompose` or the subsystems bank. The instrumentation is the prerequisite for diagnosing it; this design is the instrumentation.

This is also a direct violation of the CLAUDE.md OTEL principle ("Every backend fix that touches a subsystem MUST add OTEL watcher events so the GM panel can verify the fix is working"). The "lie detector" currently lies — it reports narrator time as total time.

## Goals

1. Replace the dishonest `total_duration_ms` alias with a real wall-clock measurement from action receipt to last outbound frame queued.
2. Add a `phase_durations_ms` map to `TurnRecord` and to the `turn_complete` event payload, broken down by named phase.
3. Make the breakdown visible in the GM panel via the existing `turn_complete` event route — no new span constants, no schema upheaval.
4. Survive errors: phase timings are recorded even when phases raise; a partial `TurnRecord` is submitted on the exception path so degraded turns are still measurable.

## Non-Goals

- Per-subsystem visibility inside `dispatch_bank`. The `local_dm.subsystem` spans already exist; promoting them through `SPAN_ROUTES` is a follow-up (F1) that benefits from this design but is out of scope.
- Defensive `asyncio.wait_for` timeouts on LLM calls. The suspected ~87 s LocalDM retry pattern (F3) is a real bug; this design measures it precisely so a separate small story can fix it surgically.
- Threshold-based alerting. The server measures; the panel decides what's slow.
- Cross-turn aggregation (rolling averages, percentiles). Panel concern.
- Frontend rendering of the new fields. Server change is value-positive without it; UI iteration is a separate PR.

## Architecture

One new module: `sidequest/telemetry/phase_timing.py`. One class.

```python
class PhaseTimings:
    """Per-turn phase-timing accumulator, attached to TurnContext."""

    NULL: "PhaseTimings"   # singleton no-op for fixtures / partial mocks

    def __init__(self, *, action_received_monotonic: float) -> None: ...

    def phase(self, name: str) -> ContextManager[None]:
        """Time a named phase. Records elapsed even on exception
        (try/finally in __exit__). Repeated names accumulate additively;
        phase_call_counts[name] increments per entry."""

    def mark_done(self) -> None:
        """Close the timer. Subsequent .phase() calls raise RuntimeError.
        Computes total_duration_ms = monotonic() - action_received_monotonic."""

    @property
    def total_ms(self) -> int: ...

    def to_dict(self) -> dict[str, int]:
        """Returns phase_durations_ms map. Excludes phases never entered."""

    @property
    def phase_call_counts(self) -> dict[str, int]: ...

    @property
    def unaccounted_ms(self) -> int:
        """total_duration_ms - sum(phase_durations_ms.values()).
        Surfaces instrumentation gaps. Always >= 0."""
```

The class is a passive accumulator. It does not interpret, threshold, log, or alert. All semantic decisions live downstream (validator, panel).

### Surface integrations

- `sidequest/game/turn.py::TurnContext` — gain a `phase_timings: PhaseTimings` field. Default to `PhaseTimings.NULL` so legacy fixtures and partial mocks continue to work.
- `sidequest/server/session_handler.py::_execute_narration_turn` — instantiate a real `PhaseTimings` at entry; call `.mark_done()` after the last `outbound.append(...)`; pass through to `TurnRecord`.
- `sidequest/agents/orchestrator.py::Orchestrator.process_action` — read `turn_context.phase_timings` and use the same `with timings.phase(...):` API for the phases it owns internally.

### Data-shape changes

- `TurnRecord` (`telemetry/turn_record.py`) gains:
  - `phase_durations_ms: dict[str, int]`
  - `total_duration_ms: int`
  - `phase_call_counts: dict[str, int]`
- `Validator._validate` (`telemetry/validator.py:423`) stops aliasing `total_duration_ms` to `agent_duration_ms`. Reads the real fields.
- `turn_complete` event payload (`telemetry/validator.py:425`) gains `phase_durations_ms`, `phase_call_counts`, `_unaccounted_ms`.

No new OTEL span constants. No `FLAT_ONLY_SPANS` changes. No `SPAN_ROUTES` changes.

## Phase Taxonomy

Ten phases, one per existing call-site seam:

| # | Phase key | Site | Owner | Today |
|---|-----------|------|-------|-------|
| 1 | `preprocess_llm` | `local_dm.decompose` (`agents/local_dm.py:368`) | session_handler | unmeasured |
| 2 | `dispatch_bank` | `run_dispatch_bank` (`agents/subsystems/__init__.py:153`) | orchestrator | unmeasured |
| 3 | `lethality_arbiter` | `LethalityArbiter.arbitrate` (`agents/orchestrator.py:1356`) | orchestrator | unmeasured |
| 4 | `prompt_build` | `build_narrator_prompt` post-bank, post-arbiter, pre-LLM (prompt assembly + section registration) | orchestrator | unmeasured |
| 5 | `narrator_subprocess` | `_client.send_with_session` (`agents/orchestrator.py:1467`) | orchestrator | measured (`agent_duration_ms`) |
| 6 | `narrator_extraction` | `extract_structured_from_response` (`agents/orchestrator.py:1520`) | orchestrator | unmeasured |
| 7 | `state_apply` | `_apply_narration_result_to_snapshot` + `apply_resource_patches` | session_handler | unmeasured |
| 8 | `dispatch_post` | side-effect emissions before outbound assembly (CONFRONTATION, SECRET_NOTE, scrapbook) | session_handler | unmeasured |
| 9 | `broadcast` | outbound list build, per-recipient projection, `_room.broadcast(...)`, party_status refresh | session_handler | unmeasured |
| 10 | `persistence` | any synchronous save flush in the dispatch chain (records ~0 ms if persistence is fully async — the phase exists as a placeholder for any sync component) | session_handler | unmeasured |

`narrator_subprocess` continues to be reflected in `agent_duration_ms` — that field stays for backwards compatibility. The new `phase_durations_ms["narrator_subprocess"]` value matches it.

**Invariant:** `sum(phase_durations_ms.values()) ≈ total_duration_ms` (modulo a few ms of bookkeeping). The `_unaccounted_ms` derived field exposes any drift; large values mean instrumentation has a hole.

## Data Flow

```
session.player_action received
  │
  └─ _execute_narration_turn() {
       timings = PhaseTimings(action_received_monotonic=time.monotonic())
       turn_context.phase_timings = timings

       with timings.phase("preprocess_llm"):
           dispatch_package = await sd.local_dm.decompose(...)

       result = await sd.orchestrator.run_narration_turn(...)
         #   ├─ with timings.phase("dispatch_bank"):       ...
         #   ├─ with timings.phase("lethality_arbiter"):   ...
         #   ├─ with timings.phase("prompt_build"):        ...
         #   ├─ with timings.phase("narrator_subprocess"): ...
         #   └─ with timings.phase("narrator_extraction"): ...

       with timings.phase("state_apply"):
           _apply_narration_result_to_snapshot(...)
           apply_resource_patches(...)

       with timings.phase("dispatch_post"):
           # confrontation, secret_note, scrapbook
           ...

       with timings.phase("broadcast"):
           # outbound build + per-recipient rewrite + party_status

       with timings.phase("persistence"):
           # save flush

       timings.mark_done()
       record = TurnRecord(
           ...,
           phase_durations_ms=timings.to_dict(),
           phase_call_counts=timings.phase_call_counts,
           total_duration_ms=timings.total_ms,
       )
       await self._validator.submit(record)
     }
```

`PhaseTimings` rides on `TurnContext` because `TurnContext` is already the formal handoff structure between the session handler and the orchestrator. No back-channel state, no callbacks, no shared mutable singletons.

### `turn_complete` event after this change

```json
{
  "turn_id": 7,
  "agent_duration_ms": 25826,
  "total_duration_ms": 50050,
  "phase_durations_ms": {
    "preprocess_llm": 18000, "dispatch_bank": 200, "lethality_arbiter": 5,
    "prompt_build": 80, "narrator_subprocess": 25826, "narrator_extraction": 90,
    "state_apply": 50, "dispatch_post": 30, "broadcast": 200, "persistence": 350
  },
  "phase_call_counts": {
    "preprocess_llm": 1, "dispatch_bank": 1, "lethality_arbiter": 1,
    "prompt_build": 1, "narrator_subprocess": 1, "narrator_extraction": 1,
    "state_apply": 1, "dispatch_post": 1, "broadcast": 1, "persistence": 1
  },
  "_unaccounted_ms": 5219
}
```

`_unaccounted_ms` is the Sebastien-tier mechanical signal: large values indicate the instrumentation missed a wall-clock contributor.

## Error Handling

The timer must never crash a turn. Telemetry is auxiliary.

1. **Phase block raises an exception.** `__exit__` records elapsed time in a `try/finally`; the exception itself propagates unchanged. "Phase X took 90 s and then crashed" is the most diagnostically valuable signal we have.
2. **Phase never enters (early return / branch skip).** Missing key in `phase_durations_ms`. Frontend renders absent phases as `–` not `0`. `_unaccounted_ms` absorbs the gap. No assertion that all ten phases must appear.
3. **Phase entered twice in one turn.** Additive accumulation: `_totals[name] += elapsed`, `phase_call_counts[name] += 1`. Last-write-wins would hide retries.
4. **`mark_done()` never called** (exception escapes `_execute_narration_turn`). A `try/finally` at the bottom of `_execute_narration_turn` submits a partial `TurnRecord` with `is_degraded=True` and a real `total_duration_ms`. Better than no record.
5. **Validator queue full.** Already handled (`telemetry/validator.py:347`); record dropped, `validation_warning` published. No change.
6. **Time-monotonic skew.** `time.monotonic()` is process-local and never goes backward. `_execute_narration_turn` is single-process. Safe.
7. **`PhaseTimings` reused across turns.** Contract is one-instance-per-turn. After `mark_done()` the instance is finalized; subsequent `.phase()` calls raise `RuntimeError("PhaseTimings already finalized")`. Loud failure beats silent contamination.
8. **`turn_context.phase_timings` not present** (older fixtures, partial mocks). `PhaseTimings.NULL` singleton with no-op `phase()` keeps call-sites clean. The orchestrator never branches on `if timings is not None:`.

## Testing

### Layer 1 — `PhaseTimings` unit tests

New file: `sidequest-server/tests/telemetry/test_phase_timing.py`.

- `test_phase_records_elapsed_ms` — single phase, monotonic clock mocked.
- `test_phase_accumulates_on_repeat` — two `with .phase("X"):` blocks → totals sum, `phase_call_counts["X"] == 2`.
- `test_phase_records_on_exception` — exception inside `with`; phase time recorded; exception propagates.
- `test_finalized_timer_rejects_writes` — `mark_done()` then `.phase("X")` raises `RuntimeError`.
- `test_null_singleton_is_noop` — `PhaseTimings.NULL.phase("anything")` no-ops; `.to_dict() == {}`.
- `test_unaccounted_ms_computed` — total minus sum, always ≥ 0.

### Layer 2 — Wiring tests (mandatory per CLAUDE.md)

In existing files: `tests/server/test_session_handler.py`, `tests/telemetry/test_validator.py`.

- `test_execute_narration_turn_records_all_named_phases` — drive `_execute_narration_turn` through one happy-path turn against an in-process orchestrator with stubbed LLM clients. Assert that the resulting `TurnRecord.phase_durations_ms` contains every expected phase key. Lie-detector for "did we actually instrument all ten seams?" — a future refactor that removes a `with timings.phase(...):` wrapper fails here.
- `test_validator_emits_phase_durations_in_turn_complete` — submit a `TurnRecord` with phase data; assert `turn_complete` event payload contains `phase_durations_ms` map and a real `total_duration_ms` distinct from `agent_duration_ms`. Catches alias regression.
- `test_total_duration_ms_is_not_aliased_to_agent` — explicit guard: `TurnRecord` where `total_duration_ms != agent_duration_ms` preserves the distinction through to the event.

### Layer 3 — Property test

- `test_sum_of_phases_approximates_total` — over 100 randomized turn shapes, `abs(total - sum(phases)) <= _unaccounted_ms` holds and `_unaccounted_ms >= 0`. Proves the invariant.

### Out of scope for this design's tests

- No mocks asserting a specific phase took N ms — flaky and meaningless.
- No real-`claude`-subprocess end-to-end timing test — too slow.
- No GM-panel rendering test — separate UI surface.

## Rollout

Steps 1–4 ship as one server PR. Step 5 ships independently.

1. Land `PhaseTimings` module + Layer-1 unit tests + Layer-3 property test. Pure addition; no call-sites.
2. Wire phases 1, 7, 8, 9, 10 in `_execute_narration_turn`. `total_duration_ms` becomes honest.
3. Wire phases 2–6 in `Orchestrator.process_action`.
4. Update `TurnRecord` shape + `Validator._validate` emission. Layer-2 wiring tests pass.
5. (Separate UI PR) GM panel ingests `phase_durations_ms`. Display: stacked bar per turn or simple two-column table.

## Migration

- `turn_complete` event schema is **additive only**. New fields: `phase_durations_ms`, `phase_call_counts`, `_unaccounted_ms`.
- `total_duration_ms` semantics change: was aliased to `agent_duration_ms`, now reflects real wall-clock. Existing consumers were already reading the wrong value per its name; the alias removal is a bug fix, not a breaking change.
- `agent_duration_ms` continues to mean "narrator subprocess." No change.
- `TurnRecord` is in-memory only; no save-file migration.
- No OTEL span-constant changes; ADR-090 Phase-2 follow-up work is unaffected and benefits from the same data.

## Risk

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Phase context-manager exception path leaves a phase un-recorded | Low | `try/finally` in `__exit__`; Layer-1 test. |
| Orchestrator and session handler disagree on a phase boundary (double-count or gap) | Medium | `_unaccounted_ms` makes drift visible; Layer-2 wiring test asserts all expected phase keys. |
| `time.monotonic()` overhead | Negligible | ~50 ns × 10 calls/turn = 500 ns. |
| Test fixtures fail because `TurnContext.phase_timings` not set | Medium | `PhaseTimings.NULL` singleton; Layer-1 test. |
| Frontend chokes on the new field | Low | Field is optional in JSON; UI iteration ignores unknown keys. |

## Out-of-Scope Follow-Ups

These are deliberately separate stories. This design is the prerequisite that makes them surgical.

- **F1.** Promote `local_dm.subsystem` spans into `SPAN_ROUTES` for per-subsystem visibility once `dispatch_bank` aggregate looks suspicious.
- **F2.** Add `asyncio.wait_for(..., timeout=N)` guards inside `run_dispatch_bank` and `LocalDM.decompose` once the panel confirms which call is stalling.
- **F3.** Diagnose and fix the suspected ~87 s LocalDM retry pattern (likely a `claude_client.py` timeout-and-retry). Scoped after instrumentation lands.

## Decision

Adopt Approach 1 (minimal-honest, single new module + dict-on-`TurnRecord`). Reject Approach 2 (per-span routing) and Approach 3 (full TraceContext flame-graph) as scope-creep without commensurate value at this stage; either can be layered on later without rework of this design.
