# Turn Pipeline Phase Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `total_duration_ms` honest and add per-phase wall-clock timings to every `TurnRecord`, so the GM panel can see where each turn's seconds actually go.

**Architecture:** One new module (`PhaseTimings` accumulator) attached to the existing `TurnContext`. Ten named phase wrappers sprinkled at existing call-site seams in the session handler and orchestrator. `TurnRecord` gains three fields; the validator's `turn_complete` event carries them through. No new OTEL span constants, no `SPAN_ROUTES` changes.

**Tech Stack:** Python 3.12, `dataclasses`, `contextlib`, `time.monotonic`, `asyncio` (no new asyncio surface), `pytest` (with `pytest-asyncio` already in repo).

**Spec:** `docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `sidequest-server/sidequest/telemetry/phase_timing.py` | Create | The `PhaseTimings` accumulator class |
| `sidequest-server/tests/telemetry/test_phase_timing.py` | Create | Unit + property tests for `PhaseTimings` |
| `sidequest-server/sidequest/agents/orchestrator.py` | Modify | Add `phase_timings` field to `TurnContext`; wrap phases 2-6 |
| `sidequest-server/sidequest/telemetry/turn_record.py` | Modify | Add `phase_durations_ms`, `phase_call_counts`, `total_duration_ms` fields |
| `sidequest-server/sidequest/server/session_handler.py` | Modify | Instantiate `PhaseTimings` in `_execute_narration_turn`; wrap phases 1, 7-10; pass through to `TurnRecord` |
| `sidequest-server/sidequest/telemetry/validator.py` | Modify | Stop aliasing `total_duration_ms`; emit `phase_durations_ms`, `phase_call_counts`, `_unaccounted_ms` |
| `sidequest-server/tests/server/test_session_handler.py` | Modify (or new sibling) | Wiring test: all expected phase keys present in `TurnRecord` |
| `sidequest-server/tests/telemetry/test_validator.py` | Modify (or new sibling) | Wiring tests: alias regression + phase emission |

---

## Task 1: `PhaseTimings` accumulator module

**Files:**
- Create: `sidequest-server/sidequest/telemetry/phase_timing.py`
- Test: `sidequest-server/tests/telemetry/test_phase_timing.py`

**Why this first:** Pure addition with no consumers. Lock the API down with TDD before any call-site touches it. If the API is wrong, every later task breaks; finding out now is cheap.

- [ ] **Step 1: Create the test file with the first failing test (single phase records elapsed)**

Create `sidequest-server/tests/telemetry/test_phase_timing.py`:

```python
"""Unit + property tests for PhaseTimings accumulator."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from sidequest.telemetry.phase_timing import PhaseTimings


def test_phase_records_elapsed_ms() -> None:
    """A single .phase() block records the elapsed time in to_dict()."""
    times = iter([100.0, 100.0, 100.5])  # __init__, __enter__, __exit__
    with patch("sidequest.telemetry.phase_timing.time.monotonic", side_effect=lambda: next(times)):
        timings = PhaseTimings(action_received_monotonic=100.0)
        with timings.phase("preprocess_llm"):
            pass
        assert timings.to_dict() == {"preprocess_llm": 500}
```

- [ ] **Step 2: Run the test and confirm import failure**

Run from repo root:

```
cd sidequest-server && uv run pytest tests/telemetry/test_phase_timing.py::test_phase_records_elapsed_ms -v
```

Expected: `ModuleNotFoundError: No module named 'sidequest.telemetry.phase_timing'`.

- [ ] **Step 3: Create the module with a minimal implementation**

Create `sidequest-server/sidequest/telemetry/phase_timing.py`:

```python
"""PhaseTimings — per-turn wall-clock phase accumulator.

Attached to TurnContext. Records elapsed-ms for each named phase via a
context manager. Survives exceptions inside phase blocks (try/finally in
__exit__). Repeated phase names accumulate additively. After mark_done()
the instance is finalized; subsequent .phase() calls raise RuntimeError.

The class is a passive accumulator. It does not interpret, threshold,
log, or alert. All semantic decisions live downstream (validator, panel).

See docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import ClassVar, Iterator


class PhaseTimings:
    """Per-turn phase-timing accumulator. One instance per turn."""

    NULL: "ClassVar[PhaseTimings]"

    def __init__(self, *, action_received_monotonic: float) -> None:
        self._start: float = action_received_monotonic
        self._totals_ms: dict[str, int] = {}
        self._call_counts: dict[str, int] = {}
        self._total_duration_ms: int | None = None
        self._finalized: bool = False

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        if self._finalized:
            raise RuntimeError("PhaseTimings already finalized")
        t0 = time.monotonic()
        try:
            yield
        finally:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            self._totals_ms[name] = self._totals_ms.get(name, 0) + elapsed_ms
            self._call_counts[name] = self._call_counts.get(name, 0) + 1

    def mark_done(self) -> None:
        if self._finalized:
            return
        self._total_duration_ms = int((time.monotonic() - self._start) * 1000)
        self._finalized = True

    @property
    def total_ms(self) -> int:
        if self._total_duration_ms is None:
            return int((time.monotonic() - self._start) * 1000)
        return self._total_duration_ms

    @property
    def phase_call_counts(self) -> dict[str, int]:
        return dict(self._call_counts)

    @property
    def unaccounted_ms(self) -> int:
        accounted = sum(self._totals_ms.values())
        return max(0, self.total_ms - accounted)

    def to_dict(self) -> dict[str, int]:
        return dict(self._totals_ms)


class _NullPhaseTimings(PhaseTimings):
    """No-op singleton for fixtures and partial mocks."""

    def __init__(self) -> None:  # noqa: D401 — explicit override
        super().__init__(action_received_monotonic=0.0)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        yield

    def mark_done(self) -> None:
        return

    @property
    def total_ms(self) -> int:
        return 0

    @property
    def unaccounted_ms(self) -> int:
        return 0

    def to_dict(self) -> dict[str, int]:
        return {}


PhaseTimings.NULL = _NullPhaseTimings()
```

- [ ] **Step 4: Run the test and confirm it passes**

```
cd sidequest-server && uv run pytest tests/telemetry/test_phase_timing.py::test_phase_records_elapsed_ms -v
```

Expected: PASS.

- [ ] **Step 5: Add the remaining unit tests**

Append to `sidequest-server/tests/telemetry/test_phase_timing.py`:

```python
def test_phase_accumulates_on_repeat() -> None:
    """Two .phase('X') blocks sum into one entry; call count tracks both."""
    times = iter([0.0, 0.0, 0.1, 0.5, 0.7])  # __init__, enter1, exit1, enter2, exit2
    with patch("sidequest.telemetry.phase_timing.time.monotonic", side_effect=lambda: next(times)):
        timings = PhaseTimings(action_received_monotonic=0.0)
        with timings.phase("X"):
            pass
        with timings.phase("X"):
            pass
        assert timings.to_dict() == {"X": 100 + 200}
        assert timings.phase_call_counts == {"X": 2}


def test_phase_records_on_exception() -> None:
    """Exception inside a phase block: elapsed still recorded, exception propagates."""
    times = iter([0.0, 0.0, 0.4])  # __init__, enter, exit
    with patch("sidequest.telemetry.phase_timing.time.monotonic", side_effect=lambda: next(times)):
        timings = PhaseTimings(action_received_monotonic=0.0)
        with pytest.raises(ValueError, match="boom"):
            with timings.phase("preprocess_llm"):
                raise ValueError("boom")
        assert timings.to_dict() == {"preprocess_llm": 400}


def test_finalized_timer_rejects_writes() -> None:
    """After mark_done(), .phase() raises RuntimeError."""
    timings = PhaseTimings(action_received_monotonic=0.0)
    timings.mark_done()
    with pytest.raises(RuntimeError, match="finalized"):
        with timings.phase("X"):
            pass


def test_null_singleton_is_noop() -> None:
    """PhaseTimings.NULL.phase() is a no-op; to_dict() is empty."""
    with PhaseTimings.NULL.phase("anything"):
        pass
    assert PhaseTimings.NULL.to_dict() == {}
    assert PhaseTimings.NULL.total_ms == 0
    assert PhaseTimings.NULL.unaccounted_ms == 0
    PhaseTimings.NULL.mark_done()  # no-op, no error


def test_unaccounted_ms_computed() -> None:
    """unaccounted_ms = total - sum(phases); always >= 0."""
    times = iter([0.0, 0.0, 0.1, 1.0])  # __init__, enter, exit, mark_done
    with patch("sidequest.telemetry.phase_timing.time.monotonic", side_effect=lambda: next(times)):
        timings = PhaseTimings(action_received_monotonic=0.0)
        with timings.phase("preprocess_llm"):
            pass
        timings.mark_done()
    assert timings.to_dict() == {"preprocess_llm": 100}
    assert timings.total_ms == 1000
    assert timings.unaccounted_ms == 900
```

- [ ] **Step 6: Run all unit tests and confirm pass**

```
cd sidequest-server && uv run pytest tests/telemetry/test_phase_timing.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 7: Add the property test (invariant: sum-of-phases <= total)**

Append to `sidequest-server/tests/telemetry/test_phase_timing.py`:

```python
import random


def test_sum_of_phases_approximates_total() -> None:
    """Over 100 randomized turn shapes: sum(phases) + unaccounted == total, all >= 0."""
    rng = random.Random(0xC0FFEE)
    for _ in range(100):
        # Build a sequence of (start, exit) monotonic timestamps for K phases.
        # All phases happen between t=0 (start) and t=total (mark_done).
        k = rng.randint(0, 8)
        total_s = rng.uniform(0.5, 5.0)
        times: list[float] = [0.0]  # __init__
        cursor = 0.0
        for _ in range(k):
            enter = cursor + rng.uniform(0.0, 0.05)
            exit_ = enter + rng.uniform(0.0, 0.4)
            times.extend([enter, exit_])
            cursor = exit_
            if cursor > total_s:
                break
        times.append(total_s)  # mark_done

        it = iter(times)
        with patch("sidequest.telemetry.phase_timing.time.monotonic", side_effect=lambda: next(it)):
            timings = PhaseTimings(action_received_monotonic=0.0)
            phase_count = (len(times) - 2) // 2
            for i in range(phase_count):
                with timings.phase(f"p{i}"):
                    pass
            timings.mark_done()

        accounted = sum(timings.to_dict().values())
        assert timings.total_ms >= 0
        assert timings.unaccounted_ms >= 0
        assert accounted + timings.unaccounted_ms == timings.total_ms
```

- [ ] **Step 8: Run all tests and confirm pass**

```
cd sidequest-server && uv run pytest tests/telemetry/test_phase_timing.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 9: Lint and format**

```
cd sidequest-server && uv run ruff check sidequest/telemetry/phase_timing.py tests/telemetry/test_phase_timing.py
cd sidequest-server && uv run ruff format sidequest/telemetry/phase_timing.py tests/telemetry/test_phase_timing.py
```

Expected: clean.

- [ ] **Step 10: Commit**

```
git add sidequest-server/sidequest/telemetry/phase_timing.py sidequest-server/tests/telemetry/test_phase_timing.py
git commit -m "feat(telemetry): add PhaseTimings accumulator

Per-turn phase-timing accumulator with try/finally semantics, additive
accumulation on repeat names, finalization guard, and a NULL singleton
for fixture compatibility.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 2: Extend `TurnContext` with `phase_timings` field

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:291-345` (TurnContext dataclass)

**Why next:** Phase wrappers in later tasks need this field to exist. Default-to-NULL so no caller is forced to provide one.

- [ ] **Step 1: Add the import and field**

Edit `sidequest-server/sidequest/agents/orchestrator.py`. Add the import near the top of the file with other `sidequest.telemetry` imports (search for an existing `from sidequest.telemetry` line; if absent, place near the existing `from sidequest.agents.claude_client import` cluster):

```python
from sidequest.telemetry.phase_timing import PhaseTimings
```

Add the new field at the end of the `TurnContext` dataclass body, after the last existing field. Find the closing of the dataclass (search for the next non-indented `class ` or `def ` after line 292). Add:

```python
    # Per-turn phase-timing accumulator (Story: phase-timing instrumentation).
    # Defaults to PhaseTimings.NULL so legacy fixtures and partial mocks
    # continue to work without provisioning a real timer. Real instances
    # are populated by ``_execute_narration_turn`` at action receipt.
    phase_timings: PhaseTimings = field(default_factory=lambda: PhaseTimings.NULL)
```

(`field` is already imported in `orchestrator.py` — confirm with `grep "^from dataclasses" sidequest-server/sidequest/agents/orchestrator.py`. If only `dataclass` is imported, change the line to `from dataclasses import dataclass, field`.)

- [ ] **Step 2: Run the existing orchestrator tests to confirm no regression**

```
cd sidequest-server && uv run pytest tests/ -k "turn_context or orchestrator" -v
```

Expected: all PASS — adding a field with a default does not break existing constructors.

- [ ] **Step 3: Lint**

```
cd sidequest-server && uv run ruff check sidequest/agents/orchestrator.py
```

Expected: clean.

- [ ] **Step 4: Commit**

```
git add sidequest-server/sidequest/agents/orchestrator.py
git commit -m "feat(orchestrator): add phase_timings field to TurnContext

Defaults to PhaseTimings.NULL for fixture compatibility. Real instances
are populated by _execute_narration_turn at action receipt.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 3: Extend `TurnRecord` shape

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/turn_record.py:27-48`

**Why now:** Validator (Task 6) and session handler (Task 4) both need this. Frozen dataclass — new fields go at the end with defaults so existing call-sites (especially `session_handler.py:4128` where `TurnRecord(...)` is constructed positionally) keep working.

- [ ] **Step 1: Add the new fields to `TurnRecord`**

Edit `sidequest-server/sidequest/telemetry/turn_record.py`. Confirm the imports at the top include `field`:

```python
from dataclasses import dataclass, field
```

(If only `dataclass` is currently imported, add `field` to the line.)

After the existing `is_degraded: bool` field (line 47), add:

```python
    # Phase-timing fields (Story: turn-pipeline phase-timing).
    # Defaulted so existing TurnRecord(...) call-sites that don't yet pass
    # phase data keep working until they migrate. The Validator emits
    # whichever values arrive — empty dicts are surfaced as missing keys
    # in the turn_complete event, not zeros (a missing phase ≠ a 0 ms phase).
    phase_durations_ms: dict[str, int] = field(default_factory=dict)
    phase_call_counts: dict[str, int] = field(default_factory=dict)
    total_duration_ms: int = 0
```

- [ ] **Step 2: Run telemetry and server tests for regressions**

```
cd sidequest-server && uv run pytest tests/telemetry/ tests/server/ -v
```

Expected: existing tests PASS — adding defaulted fields cannot break frozen-dataclass equality unless someone constructed a record positionally past field 17. There are no such call-sites.

- [ ] **Step 3: Lint**

```
cd sidequest-server && uv run ruff check sidequest/telemetry/turn_record.py
```

Expected: clean.

- [ ] **Step 4: Commit**

```
git add sidequest-server/sidequest/telemetry/turn_record.py
git commit -m "feat(telemetry): add phase-timing fields to TurnRecord

phase_durations_ms, phase_call_counts, total_duration_ms — all defaulted
so existing constructors keep working until callers migrate.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 4: Wire phases 1, 7, 8, 9, 10 in `_execute_narration_turn`

**Files:**
- Modify: `sidequest-server/sidequest/server/session_handler.py:3585-4151` (`_execute_narration_turn` method)

**Why this order:** the session handler owns the outer turn boundary (action receipt → outbound queued). Once this lands, `total_duration_ms` is honest even before the orchestrator-internal phases (Task 5) are wired — that already moves the needle.

- [ ] **Step 1: Add the import**

In `sidequest-server/sidequest/server/session_handler.py`, find the existing `from sidequest.telemetry` block (search `grep -n "from sidequest.telemetry" sidequest-server/sidequest/server/session_handler.py`). Add:

```python
from sidequest.telemetry.phase_timing import PhaseTimings
```

Confirm `import time` is already at the top (it should be — `time.monotonic()` is used elsewhere in the file via the orchestrator). If not, add `import time`.

- [ ] **Step 2: Instantiate `PhaseTimings` at the top of `_execute_narration_turn` and attach to `turn_context`**

In `_execute_narration_turn` (starts at session_handler.py:3585), find the line:

```python
        snapshot = sd.snapshot
        snapshot_before_hash = _hash_snapshot(snapshot)
```

Replace with:

```python
        snapshot = sd.snapshot
        snapshot_before_hash = _hash_snapshot(snapshot)

        timings = PhaseTimings(action_received_monotonic=time.monotonic())
        turn_context.phase_timings = timings
```

- [ ] **Step 3: Wrap phase 1 (`preprocess_llm`) around `LocalDM.decompose`**

Find the call (around session_handler.py:3592):

```python
            dispatch_package = await sd.local_dm.decompose(
                turn_id=turn_id,
                player_id=f"player:{sd.player_name}",
                raw_action=action,
                state_summary=turn_context.state_summary,
                visibility_baseline=sd.genre_pack.visibility_baseline,
            )
```

Wrap it:

```python
            with timings.phase("preprocess_llm"):
                dispatch_package = await sd.local_dm.decompose(
                    turn_id=turn_id,
                    player_id=f"player:{sd.player_name}",
                    raw_action=action,
                    state_summary=turn_context.state_summary,
                    visibility_baseline=sd.genre_pack.visibility_baseline,
                )
```

- [ ] **Step 4: Wrap phase 7 (`state_apply`) around `_apply_narration_result_to_snapshot` + `apply_resource_patches`**

Find the block (around session_handler.py:3744-3794) starting with the comment `# Unified dispatch — passes the pack so encounter instantiation /` and ending after `apply_resource_patches(...)` returns. The wrap target starts at the line `dice_outcome = getattr(sd, "pending_roll_outcome", None)` and ends at the closing of the resource-patch try block:

```python
            with timings.phase("state_apply"):
                dice_outcome = getattr(sd, "pending_roll_outcome", None)
                # ... existing code through ...
                try:
                    crossed_thresholds = apply_resource_patches(
                        snapshot,
                        affinity_progress=result.affinity_progress or [],
                        lore_store=sd.lore_store,
                        turn=snapshot.turn_manager.interaction,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "resource.patch_failed error=%s — skipping threshold mint for this turn",
                        exc,
                    )
                    crossed_thresholds = []
```

Use `Read` then `Edit` with the exact `old_string` from the file. Indentation increases by one level (4 spaces) inside the `with` block. The threshold-crossed `for t in crossed_thresholds:` loop that follows can stay outside the `with` — it's logging, not state apply.

- [ ] **Step 5: Wrap phase 8 (`dispatch_post`) around scrapbook + secret-note + confrontation emission**

The dispatch-post block runs from the scrapbook `try:` block (around session_handler.py:3799) through the `confrontation_msg` assignment after `_emit_event("CONFRONTATION", ...)` (around session_handler.py:3950). Wrap as:

```python
            with timings.phase("dispatch_post"):
                # ... scrapbook emit, secret-note routing, confrontation emit ...
```

Concretely, the `with timings.phase("dispatch_post"):` block opens at the comment `# Group G Task 6: route prompt-redacted dispatches as SECRET_NOTE` (or the `try: emit_scrapbook` line, whichever comes first in the current file — pick the earlier one). It closes after the last line of the confrontation-emit block, which is the `_watcher_publish("confrontation_peer_projection_broadcast", ...)` call. Re-indent the contained code by one level.

The next lines beginning with `outbound: list[object] = [narration_msg]` are NOT inside this phase — they belong to phase 9.

- [ ] **Step 6: Wrap phase 9 (`broadcast`) around outbound list build + party_status refresh**

Find the line (around session_handler.py:3952):

```python
            outbound: list[object] = [narration_msg]
```

Open a phase block that runs from there through the end of the `if snapshot.characters:` party-status refresh (around session_handler.py:4063):

```python
            with timings.phase("broadcast"):
                outbound: list[object] = [narration_msg]
                # ... confrontation_msg append, ChapterMarkerMessage,
                #     NarrationEndMessage, turn_status_resolved broadcast,
                #     party_status refresh ...
```

The block closes just before the line `# Visual-scene render dispatch.` (around session_handler.py:4065).

- [ ] **Step 7: Wrap phase 10 (`persistence`) around the visual-render + audio + validator submit block**

This phase covers any sync save flush in the dispatch chain. Today's code does not call a save explicitly here — the persistence is async and event-driven — so the `persistence` phase will record near-zero ms. Per the spec, the phase exists as a placeholder for any sync component.

Find the block (around session_handler.py:4065-4150) starting at `render_queued = self._maybe_dispatch_render(sd, result)` and ending just before `return outbound` (around session_handler.py:4151). Wrap:

```python
            with timings.phase("persistence"):
                render_queued = self._maybe_dispatch_render(sd, result)
                if render_queued is not None:
                    outbound.append(render_queued)
                # ... audio cue dispatch ...
                # ... TurnRecord assembly + validator submit ...
```

The `validator.submit` call lives inside this phase. That's intentional: queue-put time is part of the wall-clock total.

- [ ] **Step 8: Call `mark_done()` and pass timings into `TurnRecord`**

Find the `TurnRecord(...)` constructor (around session_handler.py:4128). Just before that block, add:

```python
                    timings.mark_done()
```

Then add the three new fields to the constructor:

```python
                    record = TurnRecord(
                        turn_id=snapshot.turn_manager.interaction,
                        # ... existing fields unchanged ...
                        agent_duration_ms=result.agent_duration_ms or 0,
                        is_degraded=result.is_degraded,
                        phase_durations_ms=timings.to_dict(),
                        phase_call_counts=timings.phase_call_counts,
                        total_duration_ms=timings.total_ms,
                    )
```

- [ ] **Step 9: Add a `try/finally` so a partial `TurnRecord` is submitted when `_execute_narration_turn` raises**

Wrap the body of `_execute_narration_turn` from `timings = PhaseTimings(...)` through `return outbound` in a `try/finally`. The `finally` calls `timings.mark_done()` and, **only if the validator submit has not already happened**, submits a degraded `TurnRecord` with the timings collected so far.

The simplest pattern: introduce a `submitted = False` flag set to `True` after `await self._validator.submit(record)` succeeds. In `finally`:

```python
            timings.mark_done()
            if not submitted and self._validator is not None:
                try:
                    degraded_record = TurnRecord(
                        turn_id=snapshot.turn_manager.interaction,
                        timestamp=datetime.now(UTC),
                        player_id=sd.player_id,
                        player_input=action,
                        classified_intent="unknown",
                        agent_name="narrator",
                        narration="",
                        patches_applied=[],
                        snapshot_before_hash=snapshot_before_hash,
                        snapshot_after=snapshot,
                        delta=None,
                        beats_fired=[],
                        extraction_tier=0,
                        token_count_in=0,
                        token_count_out=0,
                        agent_duration_ms=0,
                        is_degraded=True,
                        phase_durations_ms=timings.to_dict(),
                        phase_call_counts=timings.phase_call_counts,
                        total_duration_ms=timings.total_ms,
                    )
                    await self._validator.submit(degraded_record)
                except Exception:  # noqa: BLE001 — finally must never re-raise
                    logger.exception("turn_record.degraded_submit_failed")
```

Set `submitted = True` immediately after the existing `await self._validator.submit(record)` line.

- [ ] **Step 10: Run the existing session_handler tests for regressions**

```
cd sidequest-server && uv run pytest tests/server/test_session_handler.py -v
```

Expected: existing tests PASS. If any test that constructs `TurnContext` directly is affected, it's because the test was relying on positional construction past field N — fix by switching to keyword args. Such tests are visible in this run.

- [ ] **Step 11: Lint and format**

```
cd sidequest-server && uv run ruff check sidequest/server/session_handler.py
cd sidequest-server && uv run ruff format sidequest/server/session_handler.py
```

Expected: clean.

- [ ] **Step 12: Commit**

```
git add sidequest-server/sidequest/server/session_handler.py
git commit -m "feat(server): wire phases 1,7-10 in _execute_narration_turn

Wraps preprocess_llm, state_apply, dispatch_post, broadcast, and
persistence with PhaseTimings.phase() blocks. Marks done before
TurnRecord assembly; submits a degraded record on the exception path
so timing data is preserved even when the turn crashes.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 5: Wire phases 2, 3, 4, 5, 6 in `Orchestrator.process_action` and `build_narrator_prompt`

**Files:**
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:1217-1416` (`build_narrator_prompt` — phases 2, 3, 4)
- Modify: `sidequest-server/sidequest/agents/orchestrator.py:1422-1609` (`run_narration_turn` — phases 5, 6)

**Why now:** The session handler is already publishing total + phases 1, 7-10. Adding 2-6 closes the picture.

- [ ] **Step 1: Wrap phase 2 (`dispatch_bank`) around `run_dispatch_bank`**

Find (around orchestrator.py:1341):

```python
            bank_result = await run_dispatch_bank(
                visible_dispatch_package, context=bank_context,
            )
```

Wrap:

```python
            with context.phase_timings.phase("dispatch_bank"):
                bank_result = await run_dispatch_bank(
                    visible_dispatch_package, context=bank_context,
                )
```

- [ ] **Step 2: Wrap phase 3 (`lethality_arbiter`) around `arbiter.arbitrate(...)`**

Find (around orchestrator.py:1356):

```python
                arbiter = LethalityArbiter(policy=context.lethality_policy)
                l_result = arbiter.arbitrate(
                    package=visible_dispatch_package,
                    bank_result=bank_result,
                    pc_cores_by_player=context.pc_cores_by_player,
                    npc_cores_by_name=context.npc_cores_by_name,
                )
                arbiter_directives = l_result.directives
```

Wrap the `arbiter.arbitrate(...)` call (the constructor `LethalityArbiter(...)` is microseconds — include it inside the phase for simplicity):

```python
                with context.phase_timings.phase("lethality_arbiter"):
                    arbiter = LethalityArbiter(policy=context.lethality_policy)
                    l_result = arbiter.arbitrate(
                        package=visible_dispatch_package,
                        bank_result=bank_result,
                        pc_cores_by_player=context.pc_cores_by_player,
                        npc_cores_by_name=context.npc_cores_by_name,
                    )
                    arbiter_directives = l_result.directives
```

- [ ] **Step 3: Wrap phase 4 (`prompt_build`) around the rest of `build_narrator_prompt` after the bank/arbiter**

Phase 4 covers section registration + `registry.compose(agent_name)`. The simplest seam: open the phase right after the `arbiter_directives` block above closes, and close it at the `return prompt_text, registry` statement.

Find (around orchestrator.py:1364):

```python
            combined_directives = list(bank_result.directives) + arbiter_directives
```

Open the phase from the line *before* this (so it covers the directive-block registration) through the `return`:

```python
            with context.phase_timings.phase("prompt_build"):
                combined_directives = list(bank_result.directives) + arbiter_directives
                if combined_directives:
                    block = "\n".join(
                        f"- [{d.kind}] {d.payload}" for d in combined_directives
                    )
                    registry.register_section(
                        agent_name,
                        PromptSection.new(
                            "narrator_directives",
                            block,
                            AttentionZone.Recency,
                            SectionCategory.State,
                        ),
                    )
                for key, err in bank_result.errors:
                    logger.warning(
                        "orchestrator.subsystem_error key=%s error=%s", key, err,
                    )

                # Player action (Recency zone — highest attention, every tier)
                registry.register_section(
                    agent_name,
                    PromptSection.new(
                        "player_action",
                        f"{context.character_name} says: {action}",
                        AttentionZone.Recency,
                        SectionCategory.Action,
                    ),
                )

                prompt_text = registry.compose(agent_name)
                section_count = len(registry.registry(agent_name))
                logger.info(
                    "turn.agent_llm.prompt_build section_count=%d",
                    section_count,
                )
                from sidequest.telemetry.watcher_hub import publish_event as _pub

                _pub(
                    "prompt_assembled",
                    {
                        "agent_name": agent_name,
                        "section_count": section_count,
                        "prompt_len": len(prompt_text),
                        "tier": str(tier),
                    },
                    component="prompt_builder",
                )
            return prompt_text, registry
```

Note: the `return` is OUTSIDE the `with` block (de-dented).

**Edge case:** when `visible_dispatch_package is None`, the bank/arbiter blocks are skipped entirely. In that path, only phase 4 runs. The wrapper above is correct because it's keyed off the `combined_directives` line which always executes — but `arbiter_directives` and `bank_result` would be unbound. Confirm the existing `else` initialization (search for `bank_result = ` and `arbiter_directives = `). If they're conditionally assigned, leave Step 3 as-is and add an `else` branch in Steps 1-2 that initializes empty defaults so phase 4's `combined_directives` line doesn't `NameError`.

- [ ] **Step 4: Wrap phase 5 (`narrator_subprocess`) around `_client.send_with_session`**

Find (around orchestrator.py:1461-1474):

```python
            with turn_agent_llm_inference_span(
                model=NARRATOR_MODEL,
                prompt_len=len(send_prompt),
            ):
                call_start = time.monotonic()
                try:
                    response: ClaudeResponse = await self._client.send_with_session(
                        prompt=send_prompt,
                        model=NARRATOR_MODEL,
                        session_id=current_session_id,
                        system_prompt=system_prompt_for_establish,
                        allowed_tools=[],
                        env_vars={},
                    )
                    elapsed_ms = int((time.monotonic() - call_start) * 1000)
```

Wrap the `await self._client.send_with_session(...)` in a phase. Place the `with context.phase_timings.phase("narrator_subprocess"):` *inside* the `turn_agent_llm_inference_span` (so the OTEL span and the phase both observe the same call):

```python
            with turn_agent_llm_inference_span(
                model=NARRATOR_MODEL,
                prompt_len=len(send_prompt),
            ):
                call_start = time.monotonic()
                try:
                    with context.phase_timings.phase("narrator_subprocess"):
                        response: ClaudeResponse = await self._client.send_with_session(
                            prompt=send_prompt,
                            model=NARRATOR_MODEL,
                            session_id=current_session_id,
                            system_prompt=system_prompt_for_establish,
                            allowed_tools=[],
                            env_vars={},
                        )
                    elapsed_ms = int((time.monotonic() - call_start) * 1000)
```

The `except` clause that handles failures must stay outside the inner `with` so the existing degraded-response path is unchanged. Don't wrap that.

- [ ] **Step 5: Wrap phase 6 (`narrator_extraction`) around `extract_structured_from_response`**

Find (around orchestrator.py:1520):

```python
            extraction = extract_structured_from_response(raw_response)
```

Wrap:

```python
            with context.phase_timings.phase("narrator_extraction"):
                extraction = extract_structured_from_response(raw_response)
```

- [ ] **Step 6: Run orchestrator + session_handler tests for regressions**

```
cd sidequest-server && uv run pytest tests/agents/ tests/server/test_session_handler.py -v
```

Expected: all PASS. If any test directly constructs a `TurnContext` without `phase_timings`, it should still work because of the `default_factory=lambda: PhaseTimings.NULL` default. If a test asserts on the exact field set of `TurnContext` (unlikely), update it.

- [ ] **Step 7: Lint and format**

```
cd sidequest-server && uv run ruff check sidequest/agents/orchestrator.py
cd sidequest-server && uv run ruff format sidequest/agents/orchestrator.py
```

Expected: clean.

- [ ] **Step 8: Commit**

```
git add sidequest-server/sidequest/agents/orchestrator.py
git commit -m "feat(orchestrator): wire phases 2-6 via TurnContext.phase_timings

dispatch_bank, lethality_arbiter, prompt_build, narrator_subprocess,
narrator_extraction. Reads context.phase_timings (defaulted to
PhaseTimings.NULL), so test fixtures that don't provision a real timer
no-op cleanly.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 6: Update `Validator._validate` to emit honest fields

**Files:**
- Modify: `sidequest-server/sidequest/telemetry/validator.py:423-453` (`_validate` method)

**Why now:** With `TurnRecord` carrying real `total_duration_ms`, drop the alias and add the new fields.

- [ ] **Step 1: Replace the alias and add new fields to the `turn_complete` payload**

Find (validator.py:434-435):

```python
                "agent_duration_ms": record.agent_duration_ms,
                "total_duration_ms": record.agent_duration_ms,
```

Replace with:

```python
                "agent_duration_ms": record.agent_duration_ms,
                "total_duration_ms": record.total_duration_ms,
                "phase_durations_ms": dict(record.phase_durations_ms),
                "phase_call_counts": dict(record.phase_call_counts),
                "_unaccounted_ms": max(
                    0,
                    record.total_duration_ms - sum(record.phase_durations_ms.values()),
                ),
```

(The `dict(...)` copies are defensive — `publish_event` consumers should not be able to mutate the record's data via the event payload.)

- [ ] **Step 2: Run the validator tests**

```
cd sidequest-server && uv run pytest tests/telemetry/test_validator.py -v
```

Expected: existing tests PASS. If a test asserts the `turn_complete` payload shape exactly (unlikely — most assert on subsets), update it to expect the new keys.

- [ ] **Step 3: Lint**

```
cd sidequest-server && uv run ruff check sidequest/telemetry/validator.py
```

Expected: clean.

- [ ] **Step 4: Commit**

```
git add sidequest-server/sidequest/telemetry/validator.py
git commit -m "fix(telemetry): stop aliasing total_duration_ms to agent_duration_ms

The validator was emitting total_duration_ms = agent_duration_ms,
which made the GM panel report narrator subprocess time as full turn
wall-clock. Now reads record.total_duration_ms (set by the session
handler from PhaseTimings). Adds phase_durations_ms,
phase_call_counts, and _unaccounted_ms to turn_complete.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 7: Wiring tests (mandatory per CLAUDE.md)

**Files:**
- Modify: `sidequest-server/tests/telemetry/test_validator.py` (or new sibling `test_validator_phase_timing.py`)
- Modify: `sidequest-server/tests/server/test_session_handler.py` (or new sibling `test_session_handler_phase_timing.py`)

**Why now:** Per CLAUDE.md "Every Test Suite Needs a Wiring Test" — unit tests prove `PhaseTimings` works in isolation; these prove it's actually plumbed through.

- [ ] **Step 1: Write the validator alias-regression guard**

Add a new file `sidequest-server/tests/telemetry/test_validator_phase_timing.py` (sibling to `test_validator.py`):

```python
"""Wiring tests: phase-timing fields flow from TurnRecord through Validator."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from sidequest.telemetry.turn_record import TurnRecord
from sidequest.telemetry.validator import Validator


def _make_record(**overrides: Any) -> TurnRecord:
    base: dict[str, Any] = dict(
        turn_id=1,
        timestamp=datetime.now(UTC),
        player_id="p1",
        player_input="hello",
        classified_intent="speak",
        agent_name="narrator",
        narration="The wind picks up.",
        patches_applied=[],
        snapshot_before_hash="x",
        snapshot_after=object(),
        delta=None,
        beats_fired=[],
        extraction_tier=1,
        token_count_in=10,
        token_count_out=20,
        agent_duration_ms=14336,
        is_degraded=False,
        phase_durations_ms={"preprocess_llm": 87000, "narrator_subprocess": 14336},
        phase_call_counts={"preprocess_llm": 1, "narrator_subprocess": 1},
        total_duration_ms=101000,
    )
    base.update(overrides)
    return TurnRecord(**base)


@pytest.mark.asyncio
async def test_validator_emits_phase_durations_in_turn_complete(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []

    def fake_publish(event_type: str, payload: dict[str, Any], **_: Any) -> None:
        if event_type == "turn_complete":
            captured.append(payload)

    monkeypatch.setattr(
        "sidequest.telemetry.validator.publish_event", fake_publish,
    )

    v = Validator(checks=[])
    await v._validate(_make_record())  # noqa: SLF001 — we are validating the validator

    assert len(captured) == 1
    payload = captured[0]
    assert payload["phase_durations_ms"] == {
        "preprocess_llm": 87000, "narrator_subprocess": 14336,
    }
    assert payload["phase_call_counts"] == {
        "preprocess_llm": 1, "narrator_subprocess": 1,
    }
    assert payload["total_duration_ms"] == 101000
    assert payload["agent_duration_ms"] == 14336
    # _unaccounted_ms = 101000 - (87000 + 14336) = -336 -> max(0, ...) = 0
    assert payload["_unaccounted_ms"] == 0


@pytest.mark.asyncio
async def test_total_duration_ms_is_not_aliased_to_agent_duration_ms(monkeypatch) -> None:
    """Regression guard: total_duration_ms must come from record.total_duration_ms,
    not record.agent_duration_ms. The alias bug at validator.py:435 must stay fixed.
    """
    captured: list[dict[str, Any]] = []

    def fake_publish(event_type: str, payload: dict[str, Any], **_: Any) -> None:
        if event_type == "turn_complete":
            captured.append(payload)

    monkeypatch.setattr(
        "sidequest.telemetry.validator.publish_event", fake_publish,
    )

    v = Validator(checks=[])
    record = _make_record(agent_duration_ms=14336, total_duration_ms=101000)
    await v._validate(record)

    payload = captured[0]
    assert payload["agent_duration_ms"] == 14336
    assert payload["total_duration_ms"] == 101000
    assert payload["agent_duration_ms"] != payload["total_duration_ms"]
```

(Adjust the `Validator(checks=[])` constructor call if its real signature differs — check `validator.py` for the actual class signature.)

- [ ] **Step 2: Run the new tests and confirm they pass**

```
cd sidequest-server && uv run pytest tests/telemetry/test_validator_phase_timing.py -v
```

Expected: 2 PASS.

- [ ] **Step 3: Write the end-to-end session-handler wiring test**

Add `sidequest-server/tests/server/test_session_handler_phase_timing.py`:

```python
"""Wiring test: _execute_narration_turn populates all expected phase keys
in the resulting TurnRecord.

Lie-detector for "did we actually instrument all ten seams?" — a future
refactor that drops a `with timings.phase(...):` wrapper fails here.
"""
from __future__ import annotations

import pytest

# Import the existing fixture that boots a session handler against
# stubbed LLM clients. If the fixture name differs, search
# `tests/server/conftest.py` for the sealed-letter / single-player fixture.
# The expected name is one of: ``session_handler_fixture``, ``handler_with_stub_llm``.


EXPECTED_PHASES: set[str] = {
    "preprocess_llm",
    "dispatch_bank",
    "lethality_arbiter",
    "prompt_build",
    "narrator_subprocess",
    "narrator_extraction",
    "state_apply",
    "dispatch_post",
    "broadcast",
    "persistence",
}


@pytest.mark.asyncio
async def test_execute_narration_turn_records_all_named_phases(
    session_handler_fixture,
) -> None:
    handler, sd, validator_records = session_handler_fixture

    await handler._handle_player_action({  # noqa: SLF001
        "type": "PLAYER_ACTION",
        "payload": {"action": "look around"},
    })

    assert validator_records, "validator received no TurnRecord"
    record = validator_records[-1]
    present = set(record.phase_durations_ms.keys())
    missing = EXPECTED_PHASES - present
    assert not missing, (
        f"phase_timings missing expected keys: {sorted(missing)}; "
        f"got: {sorted(present)}"
    )
    assert record.total_duration_ms > 0
    assert record.total_duration_ms >= record.agent_duration_ms
```

If `session_handler_fixture` does not exist, create it in `tests/server/conftest.py` (keep it minimal — boot the handler with `ClaudeClient` replaced by a stub that returns a hand-coded narrator JSON response and a hand-coded LocalDM JSON response). The plan deliberately doesn't dictate the fixture body; existing test fixtures in `tests/server/` already do this dance — copy and adapt.

- [ ] **Step 4: Run the wiring test and confirm it passes**

```
cd sidequest-server && uv run pytest tests/server/test_session_handler_phase_timing.py -v
```

Expected: PASS. If a phase key is missing, the assertion message names exactly which one — go back to Task 4 or Task 5 and add the missing wrapper.

- [ ] **Step 5: Run the full test suite**

```
cd sidequest-server && uv run pytest -v
```

Expected: all PASS.

- [ ] **Step 6: Lint and format**

```
cd sidequest-server && uv run ruff check tests/
cd sidequest-server && uv run ruff format tests/telemetry/test_validator_phase_timing.py tests/server/test_session_handler_phase_timing.py
```

Expected: clean.

- [ ] **Step 7: Commit**

```
git add sidequest-server/tests/telemetry/test_validator_phase_timing.py sidequest-server/tests/server/test_session_handler_phase_timing.py sidequest-server/tests/server/conftest.py
git commit -m "test(telemetry): wiring tests for phase-timing instrumentation

Validator: confirms phase_durations_ms/phase_call_counts/total_duration_ms
flow through to turn_complete payload, and that total_duration_ms is
not aliased to agent_duration_ms.

Session handler: confirms _execute_narration_turn populates every
expected phase key — the lie-detector for missing-wrapper regressions.

Spec: docs/superpowers/specs/2026-04-26-turn-pipeline-phase-timing-design.md"
```

---

## Task 8: Run the aggregate gate; verify against live server

**Files:** none (verification only).

- [ ] **Step 1: Run the orchestrator aggregate gate**

From the repo root:

```
just check-all
```

Expected: server-check + client-lint + client-test + daemon-lint all pass.

- [ ] **Step 2: Boot the server with the OTEL dashboard and observe one real turn**

```
just up
just otel
```

Open the OTEL dashboard, run a single-player turn against any genre pack, and check that:

- A `turn_complete` event arrives with `phase_durations_ms` populated.
- `total_duration_ms` matches the wall-clock between `session.player_action` and the last frame for that turn (within ~50 ms).
- `_unaccounted_ms` is small (ideally < 1000 ms; large values mean instrumentation has a hole).
- The pre-narrator phases (`preprocess_llm`, `dispatch_bank`) account for the previously dark gap.

- [ ] **Step 3: If `_unaccounted_ms` is large (> 5 s), investigate**

Look at the gap between phases in the wall-clock — likely a missing phase wrapper. Add a phase wrapper for whatever code lives in the gap, repeat from Task 4/5/7, and re-test.

- [ ] **Step 4: Stop services**

```
just down
```

- [ ] **Step 5: Final commit (only if Step 3 required additional changes)**

```
git commit -m "fix(telemetry): close phase-timing gap discovered in live test"
```

---

## Self-Review

Performed inline against the spec. Findings:

- **Spec coverage:** every spec item is mapped to a task. `PhaseTimings` API → Task 1. `TurnContext` field → Task 2. `TurnRecord` fields → Task 3. Phase wrappers (1, 7-10) → Task 4. Phase wrappers (2-6) → Task 5. Validator emission → Task 6. Wiring tests + property test → Task 7 + Task 1 Step 7. Live verification → Task 8.
- **Placeholder scan:** no "TBD" or "implement later" in any step. Every code-changing step shows the code.
- **Type consistency:** `phase_durations_ms: dict[str, int]`, `phase_call_counts: dict[str, int]`, `total_duration_ms: int` are consistent across `TurnRecord`, `Validator._validate` payload, and `PhaseTimings` accessor return types. `PhaseTimings.NULL` referenced as `ClassVar` and as singleton attribute — consistent.
- **Open uncertainty (acceptable):** Task 5 Step 3 notes that if `bank_result` and `arbiter_directives` are conditionally bound when `visible_dispatch_package is None`, the implementer needs to add `else` defaults. This is a real branch in the existing code; the implementer must verify against current state. The note flags it explicitly rather than papering over.
- **Scope:** single-PR-sized for the server change. Task 1 is the only task that adds a new module; the rest are surgical edits at named line ranges.

---

## Out-of-Scope Follow-Ups (named in spec, not in this plan)

- F1: Promote `local_dm.subsystem` spans into `SPAN_ROUTES` for per-subsystem visibility.
- F2: Add `asyncio.wait_for` guards inside `run_dispatch_bank` and `LocalDM.decompose`.
- F3: Diagnose and fix the suspected ~87 s LocalDM retry pattern. **This is the actual bug fix.** Scoped after this plan lands and the GM panel tells us where the time goes.
- UI: Frontend rendering of `phase_durations_ms` in `sidequest-ui` GM panel — separate PR, separate plan.
