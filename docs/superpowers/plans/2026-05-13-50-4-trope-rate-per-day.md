# 50-4 Trope `rate_per_day` Between-Session Advancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `TropeDefinition.passive_progression.rate_per_day` into the live trope engine via a narrator-emitted `days_advanced` field, closing ADR-018's last remaining gap.

**Architecture:** Narrator emits `days_advanced: int` in `game_patch`. A new Pass A2 in `trope_tick.py` (between existing Pass A and Pass B) advances every progressing trope by `clamp(days, 0, 14) × rate_per_day`, fires every crossed beat, and queues a `TimeSkipBeatEvent` summary that the next narrator prompt renders as a `## TIME-SKIP CONTEXT` block. Distinct OTEL span `trope.time_skip` for GM-panel observability.

**Tech Stack:** Python 3.13, pydantic v2, FastAPI, pytest, SQLite (sidequest-server). One repo touched: `sidequest-server/`. Spec: `docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md`.

**Working directory for all tasks:** `/Users/slabgorb/Projects/oq-1/sidequest-server` unless noted. Run tests via `uv run pytest`.

**Commit convention:** Conventional commits. Branch `feat/50-4-trope-rate-per-day` off `develop`. Each commit message prefixed `feat(50-4):` or `test(50-4):` or `chore(50-4):`. Co-Author trailer is fine but not required for this personal project.

---

## File Structure

**Create:**
- `sidequest/game/trope_time_skip.py` — `TimeSkipBeatEvent`, `TimeSkipSpanFields`, `DAY_TICK_CAP`, `_pass_a2_time_skip` (target ~150 lines; if it grows past 200, factor `TimeSkipBeatEvent` to a separate models module)
- `tests/game/test_trope_time_skip.py` — Pass A2 unit tests
- `tests/game/test_session_time_skip.py` — snapshot/persistence round-trip
- `tests/integration/test_trope_time_skip_e2e.py` — end-to-end narrator→tick→prompt
- `tests/protocol/test_game_patch_days_advanced.py` — protocol field validation

**Modify:**
- `sidequest/agents/orchestrator.py` (line 259, `NarrationTurnResult`) — add `days_advanced: int = 0`
- `sidequest/agents/orchestrator.py` (game_patch extractor, search for `items_gained` extraction) — extract `days_advanced` from raw `game_patch_dict`
- `sidequest/agents/narrator_prompts/output_only.md` — add CRITICAL TIME RULE + examples + field in valid-fields list (line 7)
- `sidequest/agents/narrator.py` (`build_narrator_prompt`) — render `## TIME-SKIP CONTEXT` when `snapshot.pending_time_skip_summary` non-empty, then clear field
- `sidequest/game/session.py` (`Snapshot` ~line 538) — add `days_elapsed: int = 0`, `pending_time_skip_summary: list[TimeSkipBeatEvent] = Field(default_factory=list)`
- `sidequest/game/delta.py` — add `days_elapsed: bool = False`, `pending_time_skip_summary: bool = False` to `SnapshotFlags`; detect changes
- `sidequest/game/persistence.py` — bump `SCHEMA_VERSION`, add columns + ALTER TABLE migration, serialize/deserialize on save/load
- `sidequest/game/trope_tick.py` (`tick_tropes` line 79) — call `_pass_a2_time_skip` between Pass A and Pass B; emit `trope.time_skip` span
- `sidequest/server/narration_apply.py` (search for `tick_tropes` call) — pass `days_advanced=result.days_advanced` to `tick_tropes`
- `sidequest/telemetry/spans/trope.py` (line 28 area) — add `SPAN_TROPE_TIME_SKIP = "trope.time_skip"` and `TropeTimeSkipFields` pydantic model
- `sidequest/server/static/dashboard.html` — Day N indicator in session header; `+Nd` badge handler for `trope.time_skip` events
- `docs/adr/018-trope-engine.md` (orchestrator repo) — strike the `rate_per_day` gap bullet, add implementation update paragraph
- `docs/adr/DRIFT.md` (orchestrator repo) — remove ADR-018 entry or downgrade to doc-drift-only
- `docs/adr/087-post-port-subsystem-restoration-plan.md` (orchestrator repo) — mark row 64 complete

---

## Task 1: Narrator output field — `days_advanced` on `NarrationTurnResult`

**Files:**
- Modify: `sidequest/agents/orchestrator.py:259+` (NarrationTurnResult)
- Modify: `sidequest/agents/orchestrator.py` (game_patch extractor — find by searching for `items_gained` extraction site)
- Test: `tests/protocol/test_game_patch_days_advanced.py` (new)

- [ ] **Step 1: Create the failing test file**

Create `tests/protocol/test_game_patch_days_advanced.py`:

```python
"""Story 50-4 — protocol-layer tests for narrator days_advanced field.

Verifies the narrator's game_patch can emit an integer days_advanced field
that round-trips through NarrationTurnResult extraction.
"""
from sidequest.agents.orchestrator import _extract_game_patch_fields  # adjust import to actual extractor


def test_days_advanced_field_parses() -> None:
    raw = {"days_advanced": 7}
    result = _extract_game_patch_fields(raw)
    assert result.days_advanced == 7


def test_days_advanced_defaults_zero() -> None:
    raw: dict = {}
    result = _extract_game_patch_fields(raw)
    assert result.days_advanced == 0


def test_days_advanced_rejects_negative() -> None:
    raw = {"days_advanced": -3}
    result = _extract_game_patch_fields(raw)
    assert result.days_advanced == 0  # negative coerced to 0; do not raise


def test_days_advanced_rejects_non_int() -> None:
    raw = {"days_advanced": "seven"}
    result = _extract_game_patch_fields(raw)
    assert result.days_advanced == 0  # silently dropped on type mismatch, like other fields
```

NOTE: The exact extractor function name and import may differ. Search `sidequest/agents/orchestrator.py` for how `items_gained` is extracted into `NarrationTurnResult.items_gained` and follow the same pattern. If the extractor inlined into `run_narration_turn`, factor it out enough to test in isolation, or write the test against `NarrationTurnResult` constructed directly from a mocked extraction call. Adjust the imports above accordingly.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/protocol/test_game_patch_days_advanced.py -v
```

Expected: FAIL — `_extract_game_patch_fields` doesn't recognize `days_advanced`, OR `NarrationTurnResult` has no `days_advanced` attribute.

- [ ] **Step 3: Add `days_advanced` to `NarrationTurnResult`**

Edit `sidequest/agents/orchestrator.py` line ~259 (`NarrationTurnResult` dataclass). After the existing `companions_dismissed` field and before the `game_patch_dict` field, add:

```python
    # Story 50-4 — in-game day advancement signal from narrator.
    # When > 0, narration_apply calls trope_tick with this value so
    # Pass A2 advances every progressing trope by rate_per_day * clamp(N, 0, 14).
    # Sub-day passage stays 0 (time_of_day handles intra-day cues).
    days_advanced: int = 0
```

- [ ] **Step 4: Extract `days_advanced` in the game_patch parser**

Find the extraction site in `sidequest/agents/orchestrator.py` (search: `items_gained` near the `NarrationTurnResult(...)` construction). Add a line that pulls `days_advanced` from the raw `game_patch_dict`:

```python
# Coerce: only accept non-negative ints. Anything else (string, float,
# negative, missing) maps to 0 — same silent-drop pattern as items.
raw_days = game_patch_dict.get("days_advanced", 0)
days_advanced = raw_days if isinstance(raw_days, int) and raw_days >= 0 else 0
```

Pass `days_advanced=days_advanced` to the `NarrationTurnResult(...)` constructor.

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/protocol/test_game_patch_days_advanced.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 6: Run linter and full server test suite for regression**

```bash
uv run ruff check sidequest/agents/orchestrator.py tests/protocol/test_game_patch_days_advanced.py
uv run pytest -x
```

Expected: ruff clean; all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest/agents/orchestrator.py tests/protocol/test_game_patch_days_advanced.py
git commit -m "feat(50-4): extract days_advanced from narrator game_patch"
```

---

## Task 2: `TimeSkipBeatEvent` and `TimeSkipSpanFields` models

**Files:**
- Create: `sidequest/game/trope_time_skip.py`
- Test: deferred to Task 4 (these models are exercised through Pass A2)

- [ ] **Step 1: Create the new module**

Create `sidequest/game/trope_time_skip.py`:

```python
"""Story 50-4 — time-skip pass for the trope engine.

When the narrator emits a multi-day jump (``days_advanced > 0`` in the
game_patch), this module's ``_pass_a2_time_skip`` advances every
progressing trope by ``rate_per_day * clamp(days, 0, DAY_TICK_CAP)``,
fires every crossed beat threshold, and appends ``TimeSkipBeatEvent``
entries to ``snapshot.pending_time_skip_summary`` for the next
narrator turn to render as a TIME-SKIP CONTEXT block.

See ADR-018 (trope engine) and the design spec at
docs/superpowers/specs/2026-05-13-50-4-trope-rate-per-day-design.md.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# Hard cap on days applied per tick. Prevents narrator over-emission
# ("a year passes") from resolving every trope in one turn. Visible in
# OTEL via ``TropeTimeSkipFields.clamped``. Configurable per genre pack
# is a deliberate YAGNI deferral (see spec out-of-scope).
DAY_TICK_CAP: int = 14


class TimeSkipBeatEvent(BaseModel):
    """A single beat that fired during a time-skip pass.

    Queued onto ``Snapshot.pending_time_skip_summary``. The next narrator
    prompt assembly renders these as bullet entries in the TIME-SKIP
    CONTEXT block and then clears the field (one-shot lifecycle).
    """

    model_config = {"extra": "forbid"}

    trope_id: str
    trope_name: str
    beat_index: int
    beat_event: str
    stakes: str
    npcs_involved: list[str] = Field(default_factory=list)
    days_into_skip: int


class TropeTimeSkipFields(BaseModel):
    """OTEL span payload for ``trope.time_skip``.

    Emitted once per ``tick_tropes`` call where ``days_advanced > 0``,
    regardless of whether any beats fired. Zero-beat ticks are useful
    telemetry — they confirm drift happened on a turn with no eligible
    tropes.
    """

    model_config = {"extra": "forbid"}

    days_requested: int
    days_applied: int
    clamped: bool = False
    tropes_affected: list[str] = Field(default_factory=list)
    tropes_skipped_zero_rate: list[str] = Field(default_factory=list)
    beats_fired_count: int = 0
    beats_fired: list[TimeSkipBeatEvent] = Field(default_factory=list)
    resolved_during_skip: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: Run ruff to verify clean**

```bash
uv run ruff check sidequest/game/trope_time_skip.py
uv run pyright sidequest/game/trope_time_skip.py
```

Expected: both clean.

- [ ] **Step 3: Commit**

```bash
git add sidequest/game/trope_time_skip.py
git commit -m "feat(50-4): add TimeSkipBeatEvent and TropeTimeSkipFields models"
```

---

## Task 3: Snapshot state fields + delta wiring + persistence migration

**Files:**
- Modify: `sidequest/game/session.py` (Snapshot ~line 586)
- Modify: `sidequest/game/delta.py` (SnapshotFlags)
- Modify: `sidequest/game/persistence.py` (schema bump, columns, ALTER TABLE, read/write)
- Test: `tests/game/test_session_time_skip.py` (new)

- [ ] **Step 1: Write failing persistence/snapshot tests**

Create `tests/game/test_session_time_skip.py`:

```python
"""Story 50-4 — snapshot fields and persistence round-trip for time-skip state."""
import tempfile
from pathlib import Path

import pytest

from sidequest.game.session import Snapshot
from sidequest.game.trope_time_skip import TimeSkipBeatEvent
from sidequest.game.persistence import SessionPersistence
from sidequest.game.delta import SnapshotFlags


def _make_event() -> TimeSkipBeatEvent:
    return TimeSkipBeatEvent(
        trope_id="murder_mystery_clock",
        trope_name="Murder Mystery Clock",
        beat_index=1,
        beat_event="Another body found, identically posed",
        stakes="high",
        npcs_involved=["constable_finch"],
        days_into_skip=2,
    )


def test_snapshot_default_days_elapsed_zero() -> None:
    snap = Snapshot()
    assert snap.days_elapsed == 0
    assert snap.pending_time_skip_summary == []


def test_snapshot_carries_days_elapsed_and_summary() -> None:
    snap = Snapshot()
    snap.days_elapsed = 7
    snap.pending_time_skip_summary.append(_make_event())
    assert snap.days_elapsed == 7
    assert len(snap.pending_time_skip_summary) == 1
    assert snap.pending_time_skip_summary[0].trope_id == "murder_mystery_clock"


def test_delta_marks_days_elapsed_change() -> None:
    before = Snapshot()
    after = Snapshot()
    after.days_elapsed = 5
    flags = SnapshotFlags.from_diff(before, after)
    assert flags.days_elapsed is True


def test_delta_marks_pending_summary_change() -> None:
    before = Snapshot()
    after = Snapshot()
    after.pending_time_skip_summary.append(_make_event())
    flags = SnapshotFlags.from_diff(before, after)
    assert flags.pending_time_skip_summary is True


def test_persistence_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    store = SessionPersistence(db_path)
    snap = Snapshot()
    snap.days_elapsed = 9
    snap.pending_time_skip_summary.append(_make_event())
    store.save(snap)

    loaded = store.load()
    assert loaded.days_elapsed == 9
    assert len(loaded.pending_time_skip_summary) == 1
    assert loaded.pending_time_skip_summary[0].beat_event == "Another body found, identically posed"


def test_migration_legacy_save_loads_with_defaults(tmp_path: Path) -> None:
    """Old saves missing the new columns load with days_elapsed=0 and empty summary."""
    db_path = tmp_path / "legacy.db"
    # Create a DB at the prior schema version (without the new columns) and load
    # via the new persistence module. Migration should add the columns with defaults.
    # NOTE: Replace prior-schema seed with the actual mechanism — see how
    # tests in `tests/game/test_session_persistence.py` create legacy DBs.
    store = SessionPersistence(db_path)
    legacy = store._connect_for_migration_test()  # adjust to actual test helper
    legacy.execute(
        "CREATE TABLE session_meta (id INTEGER PRIMARY KEY, schema_version INTEGER NOT NULL)"
    )
    legacy.execute("INSERT INTO session_meta (id, schema_version) VALUES (1, 5)")
    legacy.commit()
    legacy.close()

    loaded = store.load()
    assert loaded.days_elapsed == 0
    assert loaded.pending_time_skip_summary == []
```

NOTE on the migration test: the exact seeding mechanism depends on how `tests/game/test_session_persistence.py` builds a "before-migration" database — adapt to that pattern. If no helper exists, write the legacy schema directly via `sqlite3` and then call `SessionPersistence(db_path).load()` to trigger migration.

NOTE on `SnapshotFlags.from_diff`: check the actual method name in `delta.py`. Common names: `from_diff`, `diff_against`, `detect_changes`. Use the existing one.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/game/test_session_time_skip.py -v
```

Expected: all FAIL — fields don't exist on Snapshot, SnapshotFlags, or in persistence.

- [ ] **Step 3: Add fields to Snapshot**

Edit `sidequest/game/session.py` near line 586 (in `Snapshot`, after `active_tropes`). Add the import at the top:

```python
from sidequest.game.trope_time_skip import TimeSkipBeatEvent
```

In the `Snapshot` class:

```python
    # Story 50-4 — in-game day counter and time-skip beat summary.
    # ``days_elapsed`` is monotonic, advances by clamp(days_advanced, 0, 14)
    # on every narrator turn that emits a multi-day jump. ``pending_time_skip_summary``
    # is a one-shot queue: Pass A2 appends, narrator prompt builder consumes + clears.
    days_elapsed: int = 0
    pending_time_skip_summary: list[TimeSkipBeatEvent] = Field(default_factory=list)
```

- [ ] **Step 4: Add fields to SnapshotFlags**

Edit `sidequest/game/delta.py`. Find `SnapshotFlags` and add:

```python
    days_elapsed: bool = False
    pending_time_skip_summary: bool = False
```

Find the diff/detection method and add comparisons:

```python
        days_elapsed=before.days_elapsed != after.days_elapsed,
        pending_time_skip_summary=before.pending_time_skip_summary != after.pending_time_skip_summary,
```

- [ ] **Step 5: Persistence — schema bump, columns, migration**

Edit `sidequest/game/persistence.py`. Search for `SCHEMA_VERSION` and increment it by 1 (e.g., `5 → 6`). Find the session table CREATE statement and add the two columns to the schema:

```sql
days_elapsed INTEGER NOT NULL DEFAULT 0,
pending_time_skip_summary TEXT NOT NULL DEFAULT '[]'
```

Find the migration block (the place that ALTERs old DBs up to the current schema). Add an idempotent migration for the new schema version:

```python
if current_version < 6:
    conn.execute("ALTER TABLE session_meta ADD COLUMN days_elapsed INTEGER NOT NULL DEFAULT 0")
    conn.execute("ALTER TABLE session_meta ADD COLUMN pending_time_skip_summary TEXT NOT NULL DEFAULT '[]'")
    conn.execute("UPDATE session_meta SET schema_version = 6 WHERE id = 1")
```

NOTE: The session_meta table layout may differ. Find the actual table that stores per-session state and put the columns there. Check `persistence.py:106` for `last_played` — the new columns belong next to that.

In the save path (where snapshot is serialized to row), add:

```python
"days_elapsed": snapshot.days_elapsed,
"pending_time_skip_summary": json.dumps(
    [event.model_dump() for event in snapshot.pending_time_skip_summary]
),
```

In the load path (where rows are read back into snapshot), add:

```python
snapshot.days_elapsed = row["days_elapsed"]
raw_summary = json.loads(row["pending_time_skip_summary"])
snapshot.pending_time_skip_summary = [TimeSkipBeatEvent(**entry) for entry in raw_summary]
```

Import `TimeSkipBeatEvent` from `sidequest.game.trope_time_skip` at top of file.

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/game/test_session_time_skip.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 7: Run lint, type check, and full test suite**

```bash
uv run ruff check sidequest/game/session.py sidequest/game/delta.py sidequest/game/persistence.py tests/game/test_session_time_skip.py
uv run pyright sidequest/game/session.py sidequest/game/delta.py sidequest/game/persistence.py
uv run pytest -x
```

Expected: clean. If existing snapshot tests fail because of pydantic round-trip mismatches, the new fields are missing from a default-state assertion somewhere — fix the assertion to include them rather than reverting the field addition.

- [ ] **Step 8: Commit**

```bash
git add sidequest/game/session.py sidequest/game/delta.py sidequest/game/persistence.py tests/game/test_session_time_skip.py
git commit -m "feat(50-4): snapshot days_elapsed counter and pending_time_skip_summary with persistence migration"
```

---

## Task 4: Pass A2 algorithm — TDD'd test by test

**Files:**
- Modify: `sidequest/game/trope_time_skip.py` (add `_pass_a2_time_skip`)
- Test: `tests/game/test_trope_time_skip.py` (new)

This is the largest task. Each step adds one test, makes it pass, commits. Single file under iteration is intentional — the algorithm grows incrementally and Git history records the progression.

- [ ] **Step 1: Create test file with no-op test**

Create `tests/game/test_trope_time_skip.py`:

```python
"""Story 50-4 — Pass A2 time-skip algorithm tests.

Each test isolates one aspect: no-op, advancement, cap, single/multi beat fire,
skip conditions, implicit resolution, days_elapsed accumulation.
"""
from __future__ import annotations

from sidequest.game.session import Snapshot, TropeState
from sidequest.game.trope_time_skip import (
    DAY_TICK_CAP,
    TimeSkipBeatEvent,
    TropeTimeSkipFields,
    _pass_a2_time_skip,
)


# --- Test helpers ---

def _trope_def(
    *,
    id_: str = "test_trope",
    name: str = "Test Trope",
    rate_per_day: float = 0.04,
    escalation_thresholds: list[float] | None = None,
    escalation_events: list[str] | None = None,
):
    """Build a minimal TropeDefinition-like fake. Use the real model if importable."""
    from sidequest.genre.models.tropes import (
        PassiveProgression,
        TropeDefinition,
        TropeEscalation,
    )
    escalation = []
    thresholds = escalation_thresholds or [0.25, 0.50, 0.75, 1.0]
    events = escalation_events or [f"beat-{i}" for i in range(len(thresholds))]
    for at, event in zip(thresholds, events, strict=False):
        escalation.append(TropeEscalation(at=at, event=event, stakes="high"))
    return TropeDefinition(
        id=id_,
        name=name,
        passive_progression=PassiveProgression(rate_per_day=rate_per_day),
        escalation=escalation,
    )


def _genre_pack_with_tropes(tropes):
    """Build a minimal genre pack carrying these trope defs. Adjust to actual loader API."""
    # The Pass A2 function signature takes a genre_pack. Tests need the function
    # to look up TropeDefinition by id. Two options: pass a real GenrePack object
    # (heavy) or pass a thin shim. Recommendation: write a small adapter the
    # function accepts via duck-typing OR refactor Pass A2 to take a
    # ``Mapping[str, TropeDefinition]`` directly. The latter is cleaner and
    # matches how Pass A is structured if you check trope_tick._progressing_tropes.
    return {t.id: t for t in tropes}


def test_no_op_when_days_zero() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.1, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def()])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=0, now_turn=10)

    assert fields.days_applied == 0
    assert fields.beats_fired_count == 0
    assert snap.active_tropes[0].progress == 0.1  # unchanged
    assert snap.days_elapsed == 0
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_no_op_when_days_zero -v
```

Expected: FAIL — `_pass_a2_time_skip` doesn't exist or has wrong signature.

- [ ] **Step 3: Implement skeleton + no-op path**

Edit `sidequest/game/trope_time_skip.py`. Add at bottom:

```python
def _pass_a2_time_skip(
    snapshot,
    genre_pack,
    days_advanced: int,
    now_turn: int,
) -> TropeTimeSkipFields:
    """Apply rate_per_day drift and fire crossed beats during a time skip.

    Runs between Pass A (rate_per_turn) and Pass B (staggered fire). Only acts
    when days_advanced > 0. See spec for full algorithm.
    """
    days_applied = max(0, min(days_advanced, DAY_TICK_CAP))
    if days_applied == 0:
        return TropeTimeSkipFields(
            days_requested=days_advanced,
            days_applied=0,
            clamped=False,
        )
    # TODO subsequent steps will fill in the body — keep no-op for now to make
    # the first test pass.
    return TropeTimeSkipFields(
        days_requested=days_advanced,
        days_applied=days_applied,
        clamped=(days_advanced > DAY_TICK_CAP),
    )
```

- [ ] **Step 4: Verify test passes**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_no_op_when_days_zero -v
```

Expected: PASS.

- [ ] **Step 5: Commit the skeleton**

```bash
git add sidequest/game/trope_time_skip.py tests/game/test_trope_time_skip.py
git commit -m "test(50-4): Pass A2 skeleton with no-op path"
```

- [ ] **Step 6: Add advancement test**

Append to `tests/game/test_trope_time_skip.py`:

```python
def test_advances_progress() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.10, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.04)])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=5, now_turn=10)

    # 0.10 + 0.04 * 5 = 0.30 — crosses the 0.25 beat threshold (handled in later test)
    assert snap.active_tropes[0].progress == 0.30
    assert fields.days_applied == 5
    assert "test_trope" in fields.tropes_affected
    assert snap.days_elapsed == 5
```

- [ ] **Step 7: Run, expect FAIL (advancement not implemented)**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_advances_progress -v
```

Expected: FAIL — progress unchanged at 0.10.

- [ ] **Step 8: Implement progress advancement (still skipping beat fires)**

Replace the `_pass_a2_time_skip` body in `sidequest/game/trope_time_skip.py` with the progress-only version:

```python
def _pass_a2_time_skip(
    snapshot,
    genre_pack,
    days_advanced: int,
    now_turn: int,
) -> TropeTimeSkipFields:
    days_applied = max(0, min(days_advanced, DAY_TICK_CAP))
    if days_applied == 0:
        return TropeTimeSkipFields(
            days_requested=days_advanced,
            days_applied=0,
            clamped=False,
        )

    tropes_affected: list[str] = []
    tropes_skipped_zero_rate: list[str] = []

    for tstate in snapshot.active_tropes:
        if tstate.status != "progressing":
            continue
        tdef = genre_pack.get(tstate.id) if isinstance(genre_pack, dict) else None
        if tdef is None:
            continue
        rate = (tdef.passive_progression.rate_per_day if tdef.passive_progression else 0.0) or 0.0
        if rate <= 0.0:
            tropes_skipped_zero_rate.append(tstate.id)
            continue

        progress_before = tstate.progress
        progress_after = min(1.0, progress_before + rate * days_applied)
        if progress_after == progress_before:
            continue
        tstate.progress = progress_after
        tropes_affected.append(tstate.id)

    snapshot.days_elapsed += days_applied

    return TropeTimeSkipFields(
        days_requested=days_advanced,
        days_applied=days_applied,
        clamped=(days_advanced > DAY_TICK_CAP),
        tropes_affected=tropes_affected,
        tropes_skipped_zero_rate=tropes_skipped_zero_rate,
    )
```

NOTE: The genre_pack accessor is sketched as a dict for the test. In production, you'll receive an actual `GenrePack` object. Look at how `trope_tick.py:_progressing_tropes` looks up `TropeDefinition` by id, and replicate that. Acceptable refactor: change Pass A2 to take a `mapping: dict[str, TropeDefinition]` and have `tick_tropes` (Task 5) build the mapping once and pass it.

- [ ] **Step 9: Verify advancement test passes**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 10: Commit**

```bash
git add sidequest/game/trope_time_skip.py tests/game/test_trope_time_skip.py
git commit -m "feat(50-4): Pass A2 advances progressing trope progress by rate_per_day"
```

- [ ] **Step 11: Add cap test**

Append to test file:

```python
def test_clamps_at_cap() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.04)])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=365, now_turn=10)

    assert fields.days_applied == DAY_TICK_CAP  # 14
    assert fields.clamped is True
    # 0.0 + 0.04 * 14 = 0.56
    assert snap.active_tropes[0].progress == pytest.approx(0.56, abs=1e-6)
    assert snap.days_elapsed == DAY_TICK_CAP


def test_days_elapsed_accumulates_clamped_value() -> None:
    """days_elapsed advances by days_applied (post-cap), not by days_requested."""
    snap = Snapshot()
    snap.days_elapsed = 100
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.04)])
    _pass_a2_time_skip(snap, pack, days_advanced=365, now_turn=10)
    assert snap.days_elapsed == 100 + DAY_TICK_CAP
```

Add `import pytest` at top of the test file.

- [ ] **Step 12: Run, verify both pass**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 4 tests PASS (cap was already implemented in step 8).

- [ ] **Step 13: Commit**

```bash
git add tests/game/test_trope_time_skip.py
git commit -m "test(50-4): Pass A2 clamp at DAY_TICK_CAP and days_elapsed accumulation"
```

- [ ] **Step 14: Add single-beat fire test**

Append:

```python
def test_fires_single_crossed_beat() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.20, beats_fired=0)
    )
    # Beat at 0.25; 7 days * 0.04 = +0.28 -> progress=0.48, crosses 0.25 only.
    pack = _genre_pack_with_tropes([
        _trope_def(rate_per_day=0.04, escalation_thresholds=[0.25, 0.60, 1.0])
    ])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=7, now_turn=10)

    assert fields.beats_fired_count == 1
    assert len(fields.beats_fired) == 1
    event = fields.beats_fired[0]
    assert event.trope_id == "test_trope"
    assert event.beat_index == 0
    assert event.stakes == "high"
    assert snap.active_tropes[0].beats_fired == 1
    assert snap.active_tropes[0].last_fired_turn == 10
    assert len(snap.pending_time_skip_summary) == 1
```

- [ ] **Step 15: Run, expect FAIL (no beat-fire logic)**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_fires_single_crossed_beat -v
```

Expected: FAIL — `beats_fired_count == 0`.

- [ ] **Step 16: Implement beat-fire logic**

Update `_pass_a2_time_skip` in `sidequest/game/trope_time_skip.py`. After advancing progress and before adding to `tropes_affected`, scan escalation for crossed thresholds:

```python
        # Inside the per-trope loop, after `tstate.progress = progress_after`:
        beats_fired_here: list[TimeSkipBeatEvent] = []
        for idx, beat in enumerate(tdef.escalation):
            if idx < tstate.beats_fired:
                continue  # already fired in a prior tick
            if beat.at <= progress_after:
                # Crossed during this tick. Compute days_into_skip for ordering
                # in the summary (1..days_applied).
                if rate > 0:
                    days_to_cross = max(1, int(round((beat.at - progress_before) / rate)))
                else:
                    days_to_cross = days_applied
                days_into_skip = min(days_to_cross, days_applied)

                beats_fired_here.append(TimeSkipBeatEvent(
                    trope_id=tdef.id or tstate.id,
                    trope_name=tdef.name,
                    beat_index=idx,
                    beat_event=beat.event,
                    stakes=beat.stakes,
                    npcs_involved=list(beat.npcs_involved),
                    days_into_skip=days_into_skip,
                ))
                tstate.beats_fired = idx + 1
                tstate.last_fired_turn = now_turn

        all_beats_fired.extend(beats_fired_here)
        tropes_affected.append(tstate.id)
```

Before the loop, initialize: `all_beats_fired: list[TimeSkipBeatEvent] = []`.

After the loop and before returning, sort and append to snapshot:

```python
    all_beats_fired.sort(key=lambda b: (b.days_into_skip, b.trope_id))
    snapshot.pending_time_skip_summary.extend(all_beats_fired)
```

Update the return:

```python
    return TropeTimeSkipFields(
        days_requested=days_advanced,
        days_applied=days_applied,
        clamped=(days_advanced > DAY_TICK_CAP),
        tropes_affected=tropes_affected,
        tropes_skipped_zero_rate=tropes_skipped_zero_rate,
        beats_fired_count=len(all_beats_fired),
        beats_fired=all_beats_fired,
    )
```

- [ ] **Step 17: Verify single-beat test passes**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 18: Commit**

```bash
git add sidequest/game/trope_time_skip.py tests/game/test_trope_time_skip.py
git commit -m "feat(50-4): Pass A2 fires single crossed beat into TimeSkipBeatEvent"
```

- [ ] **Step 19: Add multi-beat fire + ordering test**

Append:

```python
def test_fires_multiple_crossed_beats_in_order() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    # Thresholds 0.10, 0.30, 0.50 with rate=0.04 and days=14 -> progress=0.56.
    # All three cross.
    pack = _genre_pack_with_tropes([
        _trope_def(
            rate_per_day=0.04,
            escalation_thresholds=[0.10, 0.30, 0.50, 0.80],
            escalation_events=["beat-A", "beat-B", "beat-C", "beat-D"],
        )
    ])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=14, now_turn=10)

    assert fields.beats_fired_count == 3
    events_by_index = sorted(fields.beats_fired, key=lambda b: b.beat_index)
    assert events_by_index[0].beat_event == "beat-A"
    assert events_by_index[1].beat_event == "beat-B"
    assert events_by_index[2].beat_event == "beat-C"
    # Summary stored in chronological order
    summary = snap.pending_time_skip_summary
    assert summary == sorted(summary, key=lambda b: (b.days_into_skip, b.trope_id))
    assert snap.active_tropes[0].beats_fired == 3
```

- [ ] **Step 20: Run, verify pass**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 6 tests PASS (multi-beat logic was already implemented in step 16's loop).

- [ ] **Step 21: Commit**

```bash
git add tests/game/test_trope_time_skip.py
git commit -m "test(50-4): Pass A2 fires multiple crossed beats sorted by days_into_skip"
```

- [ ] **Step 22: Add skip-condition tests**

Append:

```python
def test_skips_dormant_tropes() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="dormant", progress=0.5, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.04)])
    _pass_a2_time_skip(snap, pack, days_advanced=14, now_turn=10)
    assert snap.active_tropes[0].progress == 0.5  # unchanged


def test_skips_resolved_tropes() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="resolved", progress=1.0, beats_fired=4)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.04)])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=14, now_turn=10)
    assert "test_trope" not in fields.tropes_affected


def test_zero_rate_no_op_even_with_days() -> None:
    """Caverns_and_claudes pattern: rate_per_day=0.0 prevents drift."""
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    pack = _genre_pack_with_tropes([_trope_def(rate_per_day=0.0)])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=14, now_turn=10)
    assert snap.active_tropes[0].progress == 0.0
    assert "test_trope" in fields.tropes_skipped_zero_rate
    # days_elapsed still advances — time passes even if no tropes have rate_per_day
    assert snap.days_elapsed == 14
```

- [ ] **Step 23: Run, expect all to pass**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 9 tests PASS (existing logic already covers these cases).

- [ ] **Step 24: Commit**

```bash
git add tests/game/test_trope_time_skip.py
git commit -m "test(50-4): Pass A2 skip conditions for dormant, resolved, and zero-rate tropes"
```

- [ ] **Step 25: Add implicit resolution test**

Append:

```python
def test_implicit_resolution_when_all_beats_fire_and_progress_maxes() -> None:
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    # Two beats at 0.25 and 0.50; rate=0.04 * 14 days = 0.56 -> crosses both and progress goes to 0.56
    # but we need progress=1.0 for resolution, so set rate=0.1 to push to 1.0
    pack = _genre_pack_with_tropes([
        _trope_def(rate_per_day=0.1, escalation_thresholds=[0.25, 0.50, 1.0])
    ])
    fields = _pass_a2_time_skip(snap, pack, days_advanced=14, now_turn=10)
    # progress capped at 1.0
    assert snap.active_tropes[0].progress == 1.0
    assert snap.active_tropes[0].beats_fired == 3
    assert snap.active_tropes[0].status == "resolved"
    assert "test_trope" in fields.resolved_during_skip
```

- [ ] **Step 26: Run, expect FAIL (no resolution logic)**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_implicit_resolution_when_all_beats_fire_and_progress_maxes -v
```

Expected: FAIL — status still "progressing".

- [ ] **Step 27: Implement implicit resolution**

After the beats-fire scan inside the per-trope loop in `_pass_a2_time_skip`, add:

```python
        # Implicit resolution — both conditions: full progress AND all beats fired.
        if progress_after >= 1.0 and tstate.beats_fired >= len(tdef.escalation):
            tstate.status = "resolved"
            resolved_during_skip.append(tstate.id)
```

Initialize `resolved_during_skip: list[str] = []` before the loop. Pass it into the return:

```python
        resolved_during_skip=resolved_during_skip,
```

- [ ] **Step 28: Run, expect pass**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 10 tests PASS.

- [ ] **Step 29: Commit**

```bash
git add sidequest/game/trope_time_skip.py tests/game/test_trope_time_skip.py
git commit -m "feat(50-4): Pass A2 emits implicit resolution when progress and beats both max"
```

- [ ] **Step 30: Lint and type check the new module**

```bash
uv run ruff check sidequest/game/trope_time_skip.py tests/game/test_trope_time_skip.py
uv run pyright sidequest/game/trope_time_skip.py
```

Expected: clean.

---

## Task 5: Wire Pass A2 into `tick_tropes`

**Files:**
- Modify: `sidequest/game/trope_tick.py` (`tick_tropes` line 79)
- Test: `tests/game/test_trope_time_skip.py` (append Pass B interaction tests)

- [ ] **Step 1: Read the existing tick_tropes signature**

```bash
sed -n '70,100p' sidequest/game/trope_tick.py
```

Note the existing parameters of `tick_tropes`. The plan adds `days_advanced: int = 0` to its signature with default 0 so all existing call sites still compile.

- [ ] **Step 2: Add Pass B interaction test (red)**

Append to `tests/game/test_trope_time_skip.py`:

```python
def test_pass_a2_runs_between_pass_a_and_pass_b() -> None:
    """When tick_tropes is called with days_advanced > 0, Pass A2 fires before Pass B
    and Pass B does not re-fire beats Pass A2 already fired."""
    from sidequest.game.trope_tick import tick_tropes

    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.20, beats_fired=0)
    )
    # Build a real GenrePack carrying the trope def, or pass via test-only override.
    # Adjust to whatever fixture mechanism trope_tick tests already use.
    pack = ...  # build a real pack containing _trope_def(rate_per_day=0.04, thresholds=[0.25, 0.60])

    tick_tropes(snap, pack, now_turn=10, days_advanced=7)

    # Pass A2 fired the 0.25 beat (progress 0.20 -> 0.48 crosses 0.25).
    # Pass B sees beats_fired=1 and progress=0.48 -> no second beat eligible
    # (next threshold is 0.60, not yet crossed). So Pass B fires nothing here.
    assert snap.active_tropes[0].beats_fired == 1
    assert snap.active_tropes[0].progress == pytest.approx(0.48)
```

NOTE: The right way to build a `GenrePack` for this test depends on existing test patterns. Look at `tests/game/test_trope_tick.py` (the file that exercises Pass A and Pass B) and copy its pack-construction approach. Replace the `pack = ...` placeholder with the real builder. If that test uses a YAML fixture, write a minimal fixture (or reuse one) that carries a single trope matching `_trope_def`.

- [ ] **Step 3: Run, expect FAIL (days_advanced kwarg not accepted)**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_pass_a2_runs_between_pass_a_and_pass_b -v
```

Expected: FAIL — `tick_tropes() got unexpected keyword argument 'days_advanced'`.

- [ ] **Step 4: Wire Pass A2 into tick_tropes**

Edit `sidequest/game/trope_tick.py`:

1. Add to top: `from sidequest.game.trope_time_skip import _pass_a2_time_skip, TropeTimeSkipFields`
2. Add to top: `from sidequest.telemetry.spans.trope import SPAN_TROPE_TIME_SKIP` (this constant added in Task 6 — for now declare it locally if Task 6 hasn't landed: `SPAN_TROPE_TIME_SKIP = "trope.time_skip"`)
3. Change `tick_tropes(...)` signature to add `days_advanced: int = 0` as a keyword argument.
4. Between Pass A and Pass B (you'll see the structure in `tick_tropes`), insert:

```python
    if days_advanced > 0:
        time_skip_fields = _pass_a2_time_skip(
            snapshot=snapshot,
            genre_pack=genre_pack,
            days_advanced=days_advanced,
            now_turn=now_turn,
        )
        # Emit OTEL span (full wiring lands in Task 6; placeholder watcher call here)
        _emit_watcher_event(  # adjust to actual watcher emission API used in this file
            event=SPAN_TROPE_TIME_SKIP,
            payload=time_skip_fields.model_dump(),
        )
```

NOTE: The exact watcher-emission call differs across the trope-tick file. Search for how Pass A emits `trope.tick` and use the same idiom. If `_emit_watcher_event` is internal, mirror it.

- [ ] **Step 5: Run, expect PASS**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 11 tests PASS.

- [ ] **Step 6: Add Pass-B-can-still-fire test**

Append:

```python
def test_pass_b_can_still_fire_after_a2() -> None:
    """If A2 leaves progress above an unfired beat threshold, Pass B may fire it as the
    standard staggered single beat for the highest-progress trope."""
    from sidequest.game.trope_tick import tick_tropes
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.20, beats_fired=0)
    )
    pack = ...  # _trope_def(rate_per_day=0.05, thresholds=[0.25, 0.50, 0.75])
    # 7 days * 0.05 = +0.35 -> progress = 0.55, crosses 0.25 AND 0.50
    # Pass A2 fires both. Pass B has nothing else to fire (next threshold 0.75 not crossed).
    # In a separate scenario: if A2 only crosses 0.25 and progress lands at 0.55,
    # Pass B (which already fires per-turn rate_per_turn=0) sees beats_fired=1, progress=0.55,
    # next threshold 0.50 — eligible! Pass B fires it as the staggered single beat.

    tick_tropes(snap, pack, now_turn=10, days_advanced=7)
    # Verify Pass A2 fired the beats, NOT Pass B re-firing them
    assert snap.active_tropes[0].beats_fired == 2  # A2 fired both
```

This test is fiddly — the boundary between "what A2 fires" and "what Pass B fires" depends on whether A2's per-trope sweep already advanced `beats_fired` past every crossed threshold. If you want to deliberately test Pass B firing in addition: construct a scenario where A2 crosses ONE threshold and leaves progress just below the next; then in the same tick, Pass A (rate_per_turn) bumps progress past the next threshold; then Pass B picks it up. That requires rate_per_turn > 0 in the trope def. Adjust the test fixture to exercise this case if needed, or accept that A2 firing the same beats Pass B would have fired is the common case.

If the spec-style "Pass B fires one additional beat" test is too fragile to write cleanly, document it as covered by `test_pass_a2_runs_between_pass_a_and_pass_b` (Pass B is implicitly tested by not re-firing) and skip the additional case here.

- [ ] **Step 7: Run, verify pass**

```bash
uv run pytest tests/game/test_trope_time_skip.py -v
```

Expected: 12 tests PASS (or 11 if you drop the fragile Pass-B-fires case).

- [ ] **Step 8: Lint and full-suite regression**

```bash
uv run ruff check sidequest/game/trope_tick.py
uv run pytest -x
```

Expected: clean.

- [ ] **Step 9: Commit**

```bash
git add sidequest/game/trope_tick.py tests/game/test_trope_time_skip.py
git commit -m "feat(50-4): wire Pass A2 between Pass A and Pass B in tick_tropes"
```

---

## Task 6: OTEL span — `trope.time_skip`

**Files:**
- Modify: `sidequest/telemetry/spans/trope.py` (line ~28 area)
- Modify: `sidequest/game/trope_tick.py` (replace the local SPAN_TROPE_TIME_SKIP placeholder with the imported constant; ensure span emission matches the existing watcher pattern)

- [ ] **Step 1: Add constant + Fields model**

Edit `sidequest/telemetry/spans/trope.py`. After line 39 (`SPAN_TROPE_CAP_BLOCKED`), add:

```python
# Story 50-4 — distinct from SPAN_TROPE_TICK_PER (which is rate_per_turn).
# Fires once per tick_tropes call where days_advanced > 0, regardless of
# whether any beats fired. Sebastien-axis: GM panel can distinguish
# in-session pacing drift from explicit time-skip drift.
SPAN_TROPE_TIME_SKIP = "trope.time_skip"
```

If this file defines pydantic Fields models for each span (check existing patterns), add:

```python
class TropeTimeSkipFields(BaseModel):
    """Re-exported from sidequest.game.trope_time_skip for watcher consumers."""
    days_requested: int
    days_applied: int
    clamped: bool = False
    tropes_affected: list[str] = Field(default_factory=list)
    tropes_skipped_zero_rate: list[str] = Field(default_factory=list)
    beats_fired_count: int = 0
    resolved_during_skip: list[str] = Field(default_factory=list)
```

If span-payload validation lives elsewhere (`sidequest/telemetry/validator.py`), check the existing trope-span validators and add a parallel one for `trope.time_skip`.

- [ ] **Step 2: Replace the placeholder in trope_tick.py**

In `sidequest/game/trope_tick.py`, ensure the import is real (not the local placeholder from Task 5 step 4):

```python
from sidequest.telemetry.spans.trope import SPAN_TROPE_TIME_SKIP
```

Remove the local fallback if you added one.

Confirm the watcher emission produces the full payload (all `TropeTimeSkipFields` keys) by passing `time_skip_fields.model_dump()` or building the dict from the Pass A2 return.

- [ ] **Step 3: Add OTEL integration test**

In `tests/integration/test_trope_time_skip_e2e.py` (will be created in Task 10), add a test that captures watcher events and verifies the span fires with the right fields. For now, add to `tests/game/test_trope_time_skip.py`:

```python
def test_otel_span_emitted_when_days_advanced(monkeypatch) -> None:
    """Verifies tick_tropes emits trope.time_skip when days_advanced > 0."""
    from sidequest.game import trope_tick

    captured = []
    def fake_emit(event: str, payload: dict) -> None:
        captured.append((event, payload))
    monkeypatch.setattr(trope_tick, "_emit_watcher_event", fake_emit)  # adjust to real name

    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.0, beats_fired=0)
    )
    pack = ...  # real GenrePack with _trope_def(rate_per_day=0.04)
    trope_tick.tick_tropes(snap, pack, now_turn=10, days_advanced=7)

    time_skip_spans = [(e, p) for e, p in captured if e == "trope.time_skip"]
    assert len(time_skip_spans) == 1
    _, payload = time_skip_spans[0]
    assert payload["days_requested"] == 7
    assert payload["days_applied"] == 7
    assert payload["clamped"] is False
    assert "test_trope" in payload["tropes_affected"]
```

- [ ] **Step 4: Run, expect pass (or red→green if emission was placeholder)**

```bash
uv run pytest tests/game/test_trope_time_skip.py::test_otel_span_emitted_when_days_advanced -v
```

Expected: PASS if emission is wired correctly.

- [ ] **Step 5: Verify other watcher tests still pass**

```bash
uv run pytest tests/telemetry tests/game/test_trope_tick.py -v
```

Expected: no regressions.

- [ ] **Step 6: Commit**

```bash
git add sidequest/telemetry/spans/trope.py sidequest/game/trope_tick.py tests/game/test_trope_time_skip.py
git commit -m "feat(50-4): emit trope.time_skip OTEL span with TropeTimeSkipFields"
```

---

## Task 7: `narration_apply` wire-up

**Files:**
- Modify: `sidequest/server/narration_apply.py` (search for existing `tick_tropes(` call site)

- [ ] **Step 1: Find the tick_tropes call site**

```bash
grep -n "tick_tropes" sidequest/server/narration_apply.py
```

Note the line and the args currently passed.

- [ ] **Step 2: Add days_advanced to the call**

Edit that call site so it passes the value extracted from the narrator result:

```python
tick_tropes(
    snapshot=snapshot,
    genre_pack=genre_pack,
    now_turn=now_turn,
    days_advanced=result.days_advanced,  # Story 50-4 — Pass A2 time skip
)
```

- [ ] **Step 3: Run the narration_apply tests**

```bash
uv run pytest tests/server -v -k narration
```

Expected: existing tests pass (default `days_advanced=0` means no behavior change for tests that don't set it).

- [ ] **Step 4: Commit**

```bash
git add sidequest/server/narration_apply.py
git commit -m "feat(50-4): pass days_advanced from narrator result to tick_tropes"
```

---

## Task 8: Narrator output rule — CRITICAL TIME RULE

**Files:**
- Modify: `sidequest/agents/narrator_prompts/output_only.md`

- [ ] **Step 1: Add days_advanced to the valid-fields list (line 7)**

Edit `sidequest/agents/narrator_prompts/output_only.md`. Line 7 currently reads:

> After your prose, emit a fenced JSON block labeled game_patch containing mechanical intents from this turn. Only include fields that changed. Valid fields: confrontation, items_gained, items_lost, items_discarded, items_consumed, location, npcs_met, mood, state_snapshot, beat_selections, visual_scene, footnotes, gold_change, action_rewrite, status_changes, companions_added, companions_dismissed.

Add `days_advanced` to the list:

> ... companions_added, companions_dismissed, days_advanced.

- [ ] **Step 2: Add the CRITICAL TIME RULE block**

Insert after the existing CRITICAL COMPANION RULE block (search for "CRITICAL COMPANION RULE"):

```markdown

CRITICAL TIME RULE: If your narration spans more than one in-game day — overnight rest, hard cut ("the next morning"), fast travel sequence, or explicit time skip ("a week of investigation passes") — you MUST emit `days_advanced` set to the integer day count elapsed during this turn. Sub-day passage (a few hours, sunset to nightfall, an afternoon's negotiation) is `time_of_day` only — do NOT emit `days_advanced`. Multi-day jumps without `days_advanced` mean tropes don't drift, off-screen plot stalls, and the world stops feeling alive between scenes.

Examples:
- "By dawn, the cook was missing" → days_advanced: 1
- "A week of cold leads later, she returned to the manor" → days_advanced: 7
- "They argued until sundown" → days_advanced: 0 (sub-day; time_of_day only)
- "She slept fitfully through the night" → days_advanced: 1
```

- [ ] **Step 3: Verify markdown renders cleanly**

```bash
cat sidequest/agents/narrator_prompts/output_only.md | head -50
```

No tooling needed — eyeball the diff.

- [ ] **Step 4: Commit**

```bash
git add sidequest/agents/narrator_prompts/output_only.md
git commit -m "feat(50-4): narrator output rule for emitting days_advanced on multi-day spans"
```

---

## Task 9: Narrator prompt assembly — render TIME-SKIP CONTEXT

**Files:**
- Modify: `sidequest/agents/narrator.py` (`build_narrator_prompt` and helpers)
- Test: `tests/integration/test_trope_time_skip_e2e.py` (partial — full E2E in Task 10)

- [ ] **Step 1: Locate the prompt builder**

```bash
grep -n "def build_narrator_prompt\|time_of_day" sidequest/agents/narrator.py
```

Identify the section that assembles state context (location, time_of_day, quest log, etc.). The TIME-SKIP CONTEXT block goes near the top of state context — above quest log, below current location.

- [ ] **Step 2: Add helper function**

In `sidequest/agents/narrator.py`, add:

```python
def _render_time_skip_context(
    summary: list[TimeSkipBeatEvent],
    days_elapsed_total: int,
) -> str:
    """Story 50-4 — render the TIME-SKIP CONTEXT block for the next narrator turn.

    Called when ``snapshot.pending_time_skip_summary`` is non-empty. After
    rendering, the caller MUST clear ``snapshot.pending_time_skip_summary``
    (one-shot lifecycle).
    """
    if not summary:
        return ""
    skip_total = max(entry.days_into_skip for entry in summary)
    lines = [
        "## TIME-SKIP CONTEXT",
        "",
        (
            f"The previous narration advanced time by {skip_total} in-game days "
            f"(total elapsed: {days_elapsed_total}). The following developed off-screen "
            "during that span. Weave these into your next narration as has-already-happened "
            "context — the players are arriving INTO this changed state, not witnessing it unfold."
        ),
        "",
    ]
    for entry in summary:
        npcs = ", ".join(entry.npcs_involved) if entry.npcs_involved else "—"
        lines.append(
            f"- Day {entry.days_into_skip} — {entry.trope_id} — "
            f"\"{entry.beat_event}\" (stakes: {entry.stakes}; npcs: {npcs})"
        )
    lines.append("")
    lines.append(
        "Acknowledge the time passage. Reference the most impactful items by stakes. "
        "You do not need to cite all beats — pick what serves the scene. "
        "Do NOT contradict any beat that fired."
    )
    return "\n".join(lines)
```

Add the import at the top of the file:

```python
from sidequest.game.trope_time_skip import TimeSkipBeatEvent
```

- [ ] **Step 3: Wire it into `build_narrator_prompt`**

Find the state-context section assembly. Above the quest log block (or below the current-location block, per spec), insert:

```python
if snapshot.pending_time_skip_summary:
    time_skip_block = _render_time_skip_context(
        snapshot.pending_time_skip_summary,
        snapshot.days_elapsed,
    )
    state_context_sections.append(time_skip_block)
    # One-shot lifecycle — clear immediately so the next turn doesn't repeat it.
    snapshot.pending_time_skip_summary = []
```

NOTE: The exact variable name for the state-context accumulator depends on the function. Adjust to whatever the function uses.

- [ ] **Step 4: Add unit test for the helper**

Append to `tests/integration/test_trope_time_skip_e2e.py` (creating the file if needed):

```python
"""Story 50-4 — end-to-end tests for trope rate_per_day advancement.

Covers: narrator emits days_advanced -> tick_tropes runs Pass A2 -> snapshot
pending_time_skip_summary populated -> next narrator prompt renders TIME-SKIP
CONTEXT block and clears the summary.
"""
from sidequest.agents.narrator import _render_time_skip_context
from sidequest.game.session import Snapshot
from sidequest.game.trope_time_skip import TimeSkipBeatEvent


def _event(beat_event: str, day: int = 1) -> TimeSkipBeatEvent:
    return TimeSkipBeatEvent(
        trope_id="murder_mystery_clock",
        trope_name="Murder Mystery Clock",
        beat_index=0,
        beat_event=beat_event,
        stakes="high",
        npcs_involved=["constable_finch"],
        days_into_skip=day,
    )


def test_render_time_skip_context_includes_header_and_beats() -> None:
    summary = [_event("Another body found"), _event("Lady Ashworth grows suspicious", day=4)]
    block = _render_time_skip_context(summary, days_elapsed_total=12)
    assert "## TIME-SKIP CONTEXT" in block
    assert "Another body found" in block
    assert "Lady Ashworth grows suspicious" in block
    assert "Day 1" in block
    assert "Day 4" in block
    assert "constable_finch" in block


def test_render_time_skip_context_empty_returns_blank() -> None:
    assert _render_time_skip_context([], days_elapsed_total=0) == ""
```

- [ ] **Step 5: Run unit tests**

```bash
uv run pytest tests/integration/test_trope_time_skip_e2e.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add sidequest/agents/narrator.py tests/integration/test_trope_time_skip_e2e.py
git commit -m "feat(50-4): narrator prompt renders TIME-SKIP CONTEXT and clears summary"
```

---

## Task 10: End-to-end wiring test

**Files:**
- Modify: `tests/integration/test_trope_time_skip_e2e.py` (append)

This is the MANDATORY wiring test per CLAUDE.md — verifies the full pipeline rather than isolated components.

- [ ] **Step 1: Write the wiring test**

Append to `tests/integration/test_trope_time_skip_e2e.py`:

```python
def test_narrator_days_advanced_e2e_advances_tropes_and_populates_summary(tmp_path):
    """E2E: simulate a narration_apply call with a NarrationTurnResult carrying
    days_advanced=7 and assert tropes advance + summary populates."""
    from sidequest.agents.orchestrator import NarrationTurnResult
    from sidequest.game.session import Snapshot, TropeState
    from sidequest.server.narration_apply import apply_narration_to_snapshot  # adjust to actual function name
    # Build a Snapshot with one progressing trope + a real GenrePack
    snap = Snapshot()
    snap.active_tropes.append(
        TropeState(id="test_trope", status="progressing", progress=0.20, beats_fired=0)
    )
    pack = ...  # real GenrePack with the test trope at rate_per_day=0.04, thresholds=[0.25, 0.60]
    result = NarrationTurnResult(narration="A week of investigation passes.", days_advanced=7)

    apply_narration_to_snapshot(result, snap, pack)  # adjust to actual API

    assert snap.active_tropes[0].progress == pytest.approx(0.48)
    assert snap.active_tropes[0].beats_fired == 1
    assert len(snap.pending_time_skip_summary) == 1
    assert snap.pending_time_skip_summary[0].beat_event == "beat-0"  # or whatever your fixture uses
    assert snap.days_elapsed == 7


def test_next_prompt_consumes_and_clears_summary(tmp_path):
    """After a tick populates pending_time_skip_summary, the next call to
    build_narrator_prompt renders the TIME-SKIP CONTEXT block AND clears the field."""
    from sidequest.agents.narrator import build_narrator_prompt  # or whatever the public entry is
    from sidequest.game.session import Snapshot
    from sidequest.game.trope_time_skip import TimeSkipBeatEvent

    snap = Snapshot()
    snap.pending_time_skip_summary.append(TimeSkipBeatEvent(
        trope_id="murder_mystery_clock",
        trope_name="Murder Mystery Clock",
        beat_index=0,
        beat_event="Another body found",
        stakes="high",
        npcs_involved=["constable_finch"],
        days_into_skip=2,
    ))

    prompt = build_narrator_prompt(snapshot=snap, ...)  # adjust signature

    assert "## TIME-SKIP CONTEXT" in prompt
    assert "Another body found" in prompt
    assert snap.pending_time_skip_summary == []  # cleared
```

NOTE: The `build_narrator_prompt` signature is large; supply only the args needed for the test to assemble a prompt or look at how `tests/agents/test_narrator.py` builds fixtures.

- [ ] **Step 2: Run**

```bash
uv run pytest tests/integration/test_trope_time_skip_e2e.py -v
```

Expected: PASS. If the prompt-assembly test fails because `build_narrator_prompt` takes many required args, copy the minimum fixture from `tests/agents/test_narrator.py`.

- [ ] **Step 3: Run the entire server test suite for regression**

```bash
uv run pytest -x
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_trope_time_skip_e2e.py
git commit -m "test(50-4): end-to-end wiring — narrator days_advanced advances tropes, prompt consumes summary"
```

---

## Task 11: Dashboard surface — Day N + +Nd badge

**Files:**
- Modify: `sidequest/server/static/dashboard.html`

- [ ] **Step 1: Find the session header rendering**

```bash
grep -n "time_of_day\|s.time_of_day\|esc(s.time_of_day)" sidequest/server/static/dashboard.html
```

Line 460 carries the header per the project context. The change targets the same render path.

- [ ] **Step 2: Add Day N indicator**

In dashboard.html line ~460, find:

```javascript
${esc(s.genre_slug||'')} / ${esc(s.world_slug||'')}${s.current_region ? ' · Region: '+esc(s.current_region) : ''}${s.time_of_day ? ' · '+esc(s.time_of_day) : ''}
```

Add:

```javascript
${esc(s.genre_slug||'')} / ${esc(s.world_slug||'')}${s.current_region ? ' · Region: '+esc(s.current_region) : ''}${s.time_of_day ? ' · '+esc(s.time_of_day) : ''}${s.days_elapsed ? ' · Day '+esc(String(s.days_elapsed)) : ''}
```

This requires the session payload to include `days_elapsed`. Verify the server-side serializer at the dashboard endpoint (`sidequest/server/dashboard.py` or wherever `/dashboard/sessions` lives) emits `days_elapsed: snapshot.days_elapsed`. Add it if missing.

- [ ] **Step 3: Add trope.time_skip event handler for +Nd badge**

Search for the existing `trope.tick` event handler in dashboard.html:

```bash
grep -n "trope.tick\|trope_tick" sidequest/server/static/dashboard.html
```

Mirror that handler for `trope.time_skip`. Pseudo-code:

```javascript
case 'trope.time_skip': {
    const days = ev.payload.days_applied || 0;
    const affected = ev.payload.tropes_affected || [];
    affected.forEach(tropeId => {
        const el = document.querySelector(`[data-trope-id="${tropeId}"]`);
        if (!el) return;
        const badge = document.createElement('span');
        badge.className = 'trope-day-badge';
        badge.textContent = '+' + days + 'd';
        badge.title = (ev.payload.beats_fired || []).map(b =>
            `Day ${b.days_into_skip}: ${b.beat_event}`
        ).join('\n') || 'No beats fired during skip';
        el.appendChild(badge);
        setTimeout(() => badge.remove(), 8000);
    });
    break;
}
```

Adjust selectors and CSS classes to existing dashboard conventions.

- [ ] **Step 4: Sanity-check the dashboard renders**

Start the server, hit `http://localhost:8765/dashboard`, confirm the header still renders (Day indicator only appears when `days_elapsed > 0`). If you have a recent save with non-zero `days_elapsed`, load it. Otherwise add a temporary test save.

This step has no automated test — visual verification is the gate. Note in the commit message that visual smoke was performed.

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/static/dashboard.html sidequest/server/dashboard.py  # only if server-side serializer was edited
git commit -m "feat(50-4): dashboard Day N header and +Nd trope.time_skip badge"
```

---

## Task 12: ADR amendment + DRIFT.md + ADR-087 row

**Files (orchestrator repo at /Users/slabgorb/Projects/oq-1):**
- Modify: `docs/adr/018-trope-engine.md`
- Modify: `docs/adr/DRIFT.md`
- Modify: `docs/adr/087-post-port-subsystem-restoration-plan.md`

- [ ] **Step 1: Update ADR-018**

Open `docs/adr/018-trope-engine.md`. In the "Remaining gaps" section, strike the bullet that begins:

> **`rate_per_day` between-session advancement** — the data model carries the field, every genre pack's YAML can set it, but no code path consumes it. SOUL.md's "Living World" pillar is unwired for trope pacing across session boundaries. This is the only mechanical gap left.

If "Remaining gaps" becomes empty after this strike, replace the section header with:

```markdown
### Remaining gaps

None — all four pillars are wired.
```

Add a new subsection above "Drift between ADR text and implementation":

```markdown
### Implementation update (2026-05-XX)

Story 50-4 closed the rate_per_day gap. The narrator now emits `days_advanced: int` in the `game_patch` block (CRITICAL TIME RULE in `output_only.md`); `tick_tropes` runs a new Pass A2 (`sidequest/game/trope_time_skip.py`) between Pass A and Pass B; every progressing trope advances by `rate_per_day * clamp(days_advanced, 0, 14)`; every crossed beat threshold fires and is queued as a `TimeSkipBeatEvent` in `snapshot.pending_time_skip_summary`; the next narrator prompt renders these as a `## TIME-SKIP CONTEXT` block and clears the queue (one-shot). A distinct `trope.time_skip` OTEL span carries `days_requested`, `days_applied`, `clamped`, `tropes_affected`, `beats_fired`, and `resolved_during_skip` for GM-panel observability.
```

Replace `2026-05-XX` with the actual merge date.

Bump the frontmatter:

```yaml
implementation-status: accepted
```

(was `partial`).

- [ ] **Step 2: Update DRIFT.md**

Open `docs/adr/DRIFT.md`. Find the ADR-018 entry. Either:

- Remove it entirely if its only drift was the rate_per_day gap (which is now closed), OR
- Downgrade to documentation-only drift — the lifecycle prose (`DORMANT → ACTIVE → PROGRESSING → RESOLVED`) still doesn't match the three-state implementation. Use this wording:

```markdown
- **ADR-018** — documentation drift only. Lifecycle prose says four-state, implementation is three-state (ACTIVE collapsed into PROGRESSING). All four pillars now wired post-50-4. Code is source of truth.
```

- [ ] **Step 3: Update ADR-087**

Open `docs/adr/087-post-port-subsystem-restoration-plan.md`. Find row 64 (trope engine). Mark complete — change status indicator to whatever convention this file uses (e.g., ✅ or `complete` or strikethrough), and reference 50-4 in the notes column.

- [ ] **Step 4: Commit (orchestrator repo)**

```bash
cd /Users/slabgorb/Projects/oq-1
git add docs/adr/018-trope-engine.md docs/adr/DRIFT.md docs/adr/087-post-port-subsystem-restoration-plan.md
git commit -m "docs(adr): close ADR-018 rate_per_day gap; mark ADR-087 row 64 complete"
```

NOTE: This commit lands in the orchestrator repo, not sidequest-server. Push to `main` (orchestrator default per repos.yaml) per the standard merge flow. The sidequest-server PR can reference this commit hash in its description.

---

## Final task: Full-repo smoke and PR

- [ ] **Step 1: Run all checks from the orchestrator root**

```bash
cd /Users/slabgorb/Projects/oq-1
just server-check
```

Expected: lint + tests all pass for sidequest-server.

- [ ] **Step 2: Push the feature branch**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git push -u origin feat/50-4-trope-rate-per-day
```

- [ ] **Step 3: Open PR against develop**

Per server CLAUDE.md, base branch is `develop`. Use `gh pr create --base develop`.

- [ ] **Step 4: Manual playtest verification (recommended before merge)**

Boot the stack (`just up`), start a tea_and_murder session, and verify:
- A narration that contains a multi-day jump emits `days_advanced > 0` (visible in OTEL stream).
- Trope progress advances on the next snapshot.
- The next narrator turn's prompt contains `## TIME-SKIP CONTEXT` (visible in OTEL prompt capture).
- The next narration acknowledges the time passage.
- Dashboard shows `Day N` header and `+Nd` badge briefly on affected tropes.

Visual smoke only — no automated test for the live narrator behavior (the narrator's adherence to the CRITICAL TIME RULE is a prompt-tuning matter, not a unit-testable property).

---

## Self-Review Notes

**Spec coverage:** All 14 acceptance criteria from the spec are covered:
- AC1 (days_advanced field) → Task 1
- AC2 (narration_apply calls tick_tropes with days_advanced) → Task 7
- AC3 (Pass A2 advances progress) → Task 4
- AC4 (Pass A2 fires all crossed beats) → Task 4 (steps 14-21)
- AC5 (days_elapsed increments) → Task 4 (steps 11-13)
- AC6 (pending_time_skip_summary populated and sorted) → Task 4 (step 19)
- AC7 (next prompt renders TIME-SKIP CONTEXT and clears) → Task 9
- AC8 (trope.time_skip span with full fields) → Task 6
- AC9 (Day N indicator on dashboard) → Task 11
- AC10 (existing saves load with defaults) → Task 3 (migration test)
- AC11 (caverns rate_per_day=0.0 → no drift) → Task 4 (step 22)
- AC12 (Pass B continues to fire one additional beat) → Task 5 (step 6)
- AC13 (all four test files present) → Tasks 1, 3, 4, 9/10
- AC14 (ADR-018 amendment) → Task 12

**Placeholder scan:** Two intentional `...` placeholders remain in fixture-construction examples (Task 5 step 2, Task 6 step 3, Task 10 step 1) — these reference the engineer's local convention for building a `GenrePack`, since the test patterns already in `tests/game/test_trope_tick.py` should be reused. NOT a plan failure; the engineer must adapt to local idioms.

**Type consistency:** `TimeSkipBeatEvent`, `TropeTimeSkipFields`, `DAY_TICK_CAP`, `_pass_a2_time_skip` names match between definition (Task 2) and usage (Tasks 4-10). `days_advanced` field name matches between narrator prompt rule (Task 8), NarrationTurnResult (Task 1), tick_tropes signature (Task 5), and narration_apply call (Task 7).
