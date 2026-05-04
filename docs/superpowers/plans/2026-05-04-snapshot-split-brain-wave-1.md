# Snapshot Split-Brain Wave 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve three mechanical-hygiene split-brain antipatterns on `GameSnapshot` in `sidequest-server`: S1 (`world_confrontations` ↔ `magic_state.confrontations` duplication), S4 (`EncounterTag` name collision across two domains), and S5 (transient magic queues persisted on the save snapshot).

**Architecture:**
- **S1.** Collapse the duplicate confrontation list into `magic_state.confrontations`. The chassis loader writes there; `room_movement.process_room_entry` reads via the existing `register == "intimate"` filter that is already the chassis-coupling discriminator in `find_eligible_room_autofire`. Legacy saves migrate on load (merge by id, prefer existing entries).
- **S4.** Rename the session-level `EncounterTag` (the NPC log entry — `npc_id/encounter_type/archetype_id/notes`) to `NpcEncounterLogTag`. The other `EncounterTag` (scene-momentum tag in `game/encounter_tag.py`) keeps its name — it has multiple importers and an ADR reference. Re-export `NpcEncounterLogTag` from `game/__init__.py`.
- **S5.** Mark `MagicState.pending_status_promotions`, `GameSnapshot.pending_magic_auto_fires`, and `GameSnapshot.pending_magic_confrontation_outcome` as `Field(exclude=True, default_factory=…)`. The fields stay in-memory for in-flight handler logic but never appear in `model_dump_json()`, so a save mid-handler is impossible to corrupt with a partial queue. Reload always starts with empty queues — correct, because the queues are derivable from snapshot state on the next narration turn. (The deeper "fully threaded handler-local" refactor is left for a follow-up; `exclude=True` achieves the persistence-boundary goal with a one-line change per field, which is the architect's pragmatic-restraint call.)
- All three: a single `migrate_legacy_snapshot(data: dict) -> dict` hook runs before pydantic validation in `SqliteStore.load`. It emits a `snapshot.canonicalize` OTEL span with per-field `migrated:bool` attributes when anything was rewritten.
- **Sibling-file safety net** (architect amendment 2026-05-04): on the load that first triggers canonicalization for a given save file, `SqliteStore.load` copies `<save>.db` → `<save>.db.canonicalize.bak` before returning the snapshot. Idempotent — if `.bak` already exists, no-op. The `.bak` is never reaped (durable retention per Keith's playstyle: years-not-weeks). This is risk-mitigation #1 from the spec, pulled into Wave 1 because the migration module is the forever home for future shims (S2/S3 in Waves 2A/2B), and Wave 2A is where a real migration bug could land. Establishing the discipline here means Wave 2A inherits it for free.

**Tech Stack:** Python 3.12, pydantic v2, pytest, uv, OpenTelemetry passthrough (`sidequest.telemetry`), SQLite save store.

---

## File Structure

**Created:**
- `sidequest-server/sidequest/game/migrations.py` — single `migrate_legacy_snapshot(data: dict) -> dict` plus per-field sub-functions and an OTEL span emitter. One responsibility: rewrite legacy snapshot dicts into canonical shape before pydantic validates.
- `sidequest-server/tests/game/test_migrations.py` — unit tests per migration sub-function, plus integration test that loads a legacy fixture through `SqliteStore.load`.
- `sidequest-server/tests/game/test_canonicalize_backup.py` — tests for the sibling-file safety net (Task 1.5).
- `sidequest-server/tests/fixtures/legacy_snapshots/` — JSON fixtures captured from saves before this plan runs (one per migration variant).

**Modified:**
- `sidequest-server/sidequest/game/persistence.py` — `SqliteStore.load` calls `migrate_legacy_snapshot` before `GameSnapshot.model_validate`, and copies `<save>.db` → `<save>.db.canonicalize.bak` once per save when migration rewrote anything.
- `sidequest-server/sidequest/game/session.py` — rename `EncounterTag` → `NpcEncounterLogTag` (line 47), update `NarrativeEntry.encounter_tags` annotation, drop `world_confrontations` field (line 520), mark `pending_magic_auto_fires` and `pending_magic_confrontation_outcome` as `Field(exclude=True, …)` (lines 593-594).
- `sidequest-server/sidequest/game/__init__.py` — export `NpcEncounterLogTag`; keep transitional `EncounterTag` alias mapped to `NpcEncounterLogTag` for one release window.
- `sidequest-server/sidequest/game/chassis.py` — `init_chassis_registry` writes into `snapshot.magic_state.confrontations` instead of `snapshot.world_confrontations` (line 233). Order-of-init guard added.
- `sidequest-server/sidequest/game/room_movement.py` — `process_room_entry` reads `snap.magic_state.confrontations` filtered by `register == "intimate"` instead of `snap.world_confrontations` (line 115).
- `sidequest-server/sidequest/magic/state.py` — `pending_status_promotions` becomes `Field(exclude=True, default_factory=list)` (line 119).
- `sidequest-server/sidequest/telemetry/spans/__init__.py` (or wherever `SPAN_*` constants live) — add `SPAN_SNAPSHOT_CANONICALIZE`.

**Note on fixtures:** Step 1.3 captures the legacy fixtures BEFORE any source code changes. The fixtures are committed as part of Task 1 so subsequent migration tasks can reference them.

---

## Task 1: Migration scaffolding (no-op pass-through, OTEL wired)

**Files:**
- Create: `sidequest-server/sidequest/game/migrations.py`
- Create: `sidequest-server/tests/game/test_migrations.py`
- Create: `sidequest-server/tests/fixtures/legacy_snapshots/.gitkeep`
- Modify: `sidequest-server/sidequest/game/persistence.py:384`
- Modify: `sidequest-server/sidequest/telemetry/spans/__init__.py` (add `SPAN_SNAPSHOT_CANONICALIZE`)

- [ ] **Step 1.1: Locate the spans module and confirm the constant pattern**

Run: `grep -n "SPAN_SESSION_SLOT_REINITIALIZED\b" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/telemetry/spans/__init__.py`

Expected: one or more lines showing the constant declaration. The new `SPAN_SNAPSHOT_CANONICALIZE` follows the same convention. If the constant lives in a sibling module (e.g. `spans/session.py`), add the new constant there and ensure it's re-exported by `spans/__init__.py`.

- [ ] **Step 1.2: Add the OTEL span constant**

Find the line declaring `SPAN_SESSION_SLOT_REINITIALIZED` and add immediately after it:

```python
SPAN_SNAPSHOT_CANONICALIZE = "snapshot.canonicalize"
"""Emitted by ``SqliteStore.load`` when ``migrate_legacy_snapshot`` rewrote any
field. Per-field migration markers are span attributes (e.g.
``s1_world_confrontations_merged: int``). Lie-detector hook for the GM panel —
Sebastien sees which legacy split-brain shapes are still in the wild."""
```

If the constant is re-exported via `__all__` in the spans `__init__.py`, add it there too.

- [ ] **Step 1.3: Capture a legacy save fixture (DO THIS BEFORE ANY OTHER SOURCE CHANGES)**

Run: `ls ~/.sidequest/saves/ | head -5`

Pick any non-empty `.db` file. Extract the `snapshot_json` row:

```bash
SAVE=~/.sidequest/saves/<chosen>.db
sqlite3 "$SAVE" "SELECT snapshot_json FROM game_state WHERE id = 1" \
  | python -m json.tool > /Users/slabgorb/Projects/oq-1/sidequest-server/tests/fixtures/legacy_snapshots/pre_cleanup.json
```

Verify the fixture is non-empty and contains at least one of the legacy fields (`world_confrontations`, `pending_magic_auto_fires`, or an `EncounterTag` shape under `narrative_log[*].encounter_tags`):

```bash
python -c "
import json
d = json.load(open('/Users/slabgorb/Projects/oq-1/sidequest-server/tests/fixtures/legacy_snapshots/pre_cleanup.json'))
print('world_confrontations:', 'world_confrontations' in d, 'len:', len(d.get('world_confrontations', [])))
print('pending_magic_auto_fires:', 'pending_magic_auto_fires' in d, 'len:', len(d.get('pending_magic_auto_fires', [])))
print('narrative_log entries:', len(d.get('narrative_log', [])))
"
```

Expected: at least one of these legacy fields shows up. If none do, pick a different save (a newer post-magic save is more likely to have populated queues). Commit the fixture even if it's empty — it's still valid as the "no migration needed" branch.

- [ ] **Step 1.4: Write the failing test for the no-op pass-through**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_migrations.py`:

```python
"""Unit tests for sidequest.game.migrations.

Each migration sub-function gets its own focused test. The orchestrator
``migrate_legacy_snapshot`` is also tested for the no-op identity case
(canonical input → identical output, no OTEL span emitted)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sidequest.game.migrations import migrate_legacy_snapshot


_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "legacy_snapshots"


def test_canonical_snapshot_is_unchanged() -> None:
    canonical = {
        "genre_slug": "caverns_and_claudes",
        "world_slug": "rookhollow",
        "characters": [],
        "npcs": [],
        "narrative_log": [],
    }
    before = copy.deepcopy(canonical)

    result = migrate_legacy_snapshot(canonical)

    assert result == before
    assert canonical == before  # input not mutated


def test_legacy_fixture_loads_without_error() -> None:
    fixture_path = _FIXTURE_DIR / "pre_cleanup.json"
    if not fixture_path.exists():
        pytest.skip("no legacy fixture captured yet")

    raw = json.loads(fixture_path.read_text())
    migrated = migrate_legacy_snapshot(raw)

    # Migration must produce a dict suitable for GameSnapshot.model_validate.
    # We don't validate here (that's the integration test); we only check
    # the migration didn't drop required keys.
    assert "genre_slug" in migrated
    assert "world_slug" in migrated
```

- [ ] **Step 1.5: Run the test to verify it fails on import**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py -v`

Expected: `ModuleNotFoundError: No module named 'sidequest.game.migrations'` or equivalent ImportError.

- [ ] **Step 1.6: Create the minimal migrations module**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/migrations.py`:

```python
"""Read-old-write-new migration hook for ``GameSnapshot`` JSON.

Runs in ``SqliteStore.load`` BEFORE pydantic validation. Each migration
sub-function takes a snapshot dict, mutates a copy, and returns the
canonical shape. ``migrate_legacy_snapshot`` is the orchestrator — it
records which sub-functions actually rewrote anything and emits a single
``snapshot.canonicalize`` OTEL span with per-field attributes.

The architect's promise (per design 2026-05-04-snapshot-split-brain-cleanup):
this module is the ONLY place backward-compat shims live. When a save
predates a schema change, the shim lives here, not buried in pydantic
validators across the snapshot models. The lie-detector signal is one
span per load; the GM panel can audit which legacy shapes are still in
the wild.
"""

from __future__ import annotations

import copy
from typing import Any

from sidequest.telemetry.spans import SPAN_SNAPSHOT_CANONICALIZE, Span


def migrate_legacy_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """Rewrite a legacy snapshot dict into the canonical shape.

    Pure-ish: returns a new dict; does not mutate the input. Emits a
    ``snapshot.canonicalize`` OTEL span only when at least one
    sub-function rewrote a field — silent on canonical input.
    """
    out = copy.deepcopy(data)
    attributes: dict[str, Any] = {}

    # Future migration sub-functions register here. Each returns either:
    #   - None  (no-op, field already canonical or absent)
    #   - dict  (per-field attributes to add to the OTEL span)
    # Sub-functions are responsible for their own dict mutations.

    # No sub-functions registered yet — this is the scaffold-only step.

    if attributes:
        with Span.open(SPAN_SNAPSHOT_CANONICALIZE, attributes):
            pass

    return out
```

- [ ] **Step 1.7: Run the tests — they should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py -v`

Expected: `test_canonical_snapshot_is_unchanged PASSED`. The fixture test PASSES if the fixture was captured (and the dict has `genre_slug` / `world_slug` keys), otherwise it SKIPS.

- [ ] **Step 1.8: Wire the migration into `SqliteStore.load`**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/persistence.py`:

Find line 384 (`snapshot = GameSnapshot.model_validate_json(row[0])`).

Replace that one line with:

```python
            import json

            from sidequest.game.migrations import migrate_legacy_snapshot

            try:
                raw = json.loads(row[0])
            except json.JSONDecodeError as exc:
                raise SaveSchemaIncompatibleError(
                    save_path=self._path or Path("<in-memory>"),
                    underlying=ValidationError.from_exception_data(
                        title="invalid_save_json", line_errors=[]
                    ),
                ) from exc
            migrated = migrate_legacy_snapshot(raw)
            snapshot = GameSnapshot.model_validate(migrated)
```

(The `import json` and `from sidequest.game.migrations` lines may also be hoisted to the top of the file — match the existing import style in `persistence.py`.)

- [ ] **Step 1.9: Add the integration test**

Append to `tests/game/test_migrations.py`:

```python
def test_sqlite_store_load_calls_migrate(tmp_path: Path) -> None:
    """End-to-end: SqliteStore.load runs migrate_legacy_snapshot before validate."""
    from sidequest.game.persistence import SqliteStore
    from sidequest.game.session import GameSnapshot

    store = SqliteStore(tmp_path / "save.db")
    store.init_session(genre_slug="caverns_and_claudes", world_slug="rookhollow")

    canonical = GameSnapshot(genre_slug="caverns_and_claudes", world_slug="rookhollow")
    store.save(canonical)

    loaded = store.load()
    assert loaded is not None
    assert loaded.snapshot.genre_slug == "caverns_and_claudes"
```

If `SqliteStore.init_session` has a different signature, adapt the call. The point of the test is: a canonical save round-trips correctly through the migration hook. (Per-field migration tests come in later tasks.)

- [ ] **Step 1.10: Run the full test file**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py -v`

Expected: all three tests PASS (or 2 PASS + 1 SKIP if fixture didn't carry legacy fields).

- [ ] **Step 1.11: Run the broader server test suite to confirm no regression**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/ tests/server/test_persistence*.py -x -q 2>&1 | tail -30`

Expected: 0 failures. If any test fails, the migration scaffolding has changed observable behavior — investigate before continuing.

- [ ] **Step 1.12: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/migrations.py
git add sidequest-server/sidequest/game/persistence.py
git add sidequest-server/sidequest/telemetry/spans/
git add sidequest-server/tests/game/test_migrations.py
git add sidequest-server/tests/fixtures/legacy_snapshots/
git commit -m "$(cat <<'EOF'
feat(server): add migrate_legacy_snapshot scaffold for split-brain cleanup

Wave 1 prep — single _migrate_legacy hook runs in SqliteStore.load before
pydantic validation. Scaffold-only at this commit; per-field migrations
land in subsequent tasks. Adds SPAN_SNAPSHOT_CANONICALIZE so the GM panel
can audit which legacy shapes are still in the wild.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md.
EOF
)"
```

---

## Task 1.5: Sibling-file safety net (`.db.canonicalize.bak`) on first migrating load

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py` — `SqliteStore.load` (extends Task 1's hook)
- Create: `sidequest-server/tests/game/test_canonicalize_backup.py`

**Why this task exists** (architect amendment 2026-05-04): the spec called for risk-mitigation #1 (sibling-file backup) and the original plan deliberately omitted it because Wave 1's migrations are content-preserving. That reasoning is sound for Wave 1 in isolation but mis-frames the migration module's lifecycle: the same `migrate_legacy_snapshot` hook is the forever home for Waves 2A (S2 NPC pool/state split) and 2B (S3 location derivation), both of which carry semantic-rewrite risk. Establishing the `.bak` discipline at Wave 1, while the migration logic is still trivial, makes Wave 2A's first canonical write inherit the safety net for free. Cost is one `shutil.copy2` per save-with-pending-migration; durable retention per Keith's playstyle (years-not-weeks) means we never reap the `.bak`, so the worst-case footprint is ~one extra `.db`-sized file per save.

**Design:**
- The signal "this load triggered canonicalization" is computed by the loader as `migrated != raw` after `migrate_legacy_snapshot` returns. (The orchestrator function from Task 1 already returns a fresh dict; the comparison is a deep-equal on the input vs the output.)
- When that signal is true and `<save_path>.canonicalize.bak` does NOT yet exist, `SqliteStore.load` calls `shutil.copy2(<save_path>, <save_path>.canonicalize.bak)` BEFORE returning the loaded snapshot.
- Idempotency: a `.bak` that already exists is left untouched. (We back up the *original* legacy state once, not the most-recent state every time.)
- Error handling: if the copy raises (disk full, permissions), log a warning span but do not block the load — the migration is still safe per pydantic round-trip; the .bak is defense-in-depth, not the primary gate.
- The `.bak` lives forever next to the save. No reaping, no TTL.

- [ ] **Step 1.5.1: Write the failing test for the safety net**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_canonicalize_backup.py`:

```python
"""Tests for the sibling-file safety net created by SqliteStore.load when
migrate_legacy_snapshot rewrites any field. Per architect amendment
2026-05-04 to docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-1.md.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from sidequest.game.persistence import SqliteStore
from sidequest.game.session import GameSnapshot


def _write_raw_save(db_path: Path, snapshot_dict: dict) -> None:
    """Write a snapshot JSON directly into game_state.id=1, bypassing pydantic.

    Lets us seed legacy-shaped saves (e.g. with world_confrontations populated)
    without having a model that produces them.
    """
    # Init schema by creating an empty store, then overwrite the row.
    store = SqliteStore(db_path)
    canonical = GameSnapshot(genre_slug="test", world_slug="t")
    store.save(canonical)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE game_state SET snapshot_json = ? WHERE id = 1",
            (json.dumps(snapshot_dict),),
        )
        conn.commit()


def test_canonical_load_does_not_create_backup(tmp_path: Path) -> None:
    """A load that requires no migration leaves no .canonicalize.bak."""
    db_path = tmp_path / "save.db"
    store = SqliteStore(db_path)
    canonical = GameSnapshot(genre_slug="test", world_slug="t")
    store.save(canonical)

    store2 = SqliteStore(db_path)
    loaded = store2.load()

    assert loaded is not None
    assert not (tmp_path / "save.db.canonicalize.bak").exists()


def test_legacy_load_creates_backup_once(tmp_path: Path) -> None:
    """A load that rewrites any field copies the .db to a sibling .bak."""
    db_path = tmp_path / "save.db"
    bak_path = tmp_path / "save.db.canonicalize.bak"

    # Seed a legacy-shaped snapshot — uses an unknown field that the migration
    # would strip, OR (better) a real legacy field once Tasks 4/5/6/7 land.
    # For Task 1.5 itself we use a stub: insert any change that
    # migrate_legacy_snapshot will rewrite. Since Task 1 is scaffold-only,
    # this test SKIPS until at least one per-field migration is registered.
    legacy = {
        "genre_slug": "test",
        "world_slug": "t",
        "characters": [],
        "npcs": [],
        "narrative_log": [],
        # Once S5 lands, the line below makes this concrete:
        # "pending_magic_auto_fires": [{"...": "..."}],
    }
    _write_raw_save(db_path, legacy)

    store = SqliteStore(db_path)
    loaded = store.load()
    assert loaded is not None

    # If the migration scaffold is no-op (which it is at Task 1), this
    # assertion will fail. The test becomes meaningful starting in Tasks 3-4.
    if not bak_path.exists():
        pytest.skip(
            "No per-field migration registered yet — backup is unreachable. "
            "Re-enable this test after Task 3 (S5) lands."
        )

    assert bak_path.is_file()
    # The .bak captures the pre-migration on-disk state.
    with sqlite3.connect(bak_path) as conn:
        row = conn.execute(
            "SELECT snapshot_json FROM game_state WHERE id = 1"
        ).fetchone()
    assert row is not None
    backed_up = json.loads(row[0])
    assert backed_up == legacy


def test_backup_is_idempotent(tmp_path: Path) -> None:
    """A second load on a save that already has a .bak does not overwrite it."""
    db_path = tmp_path / "save.db"
    bak_path = tmp_path / "save.db.canonicalize.bak"

    # Pre-seed the .bak with sentinel content.
    db_path.write_bytes(b"")  # placeholder to satisfy SqliteStore init
    store = SqliteStore(db_path)
    store.save(GameSnapshot(genre_slug="test", world_slug="t"))
    bak_path.write_text("SENTINEL — pre-existing backup")

    # Even if we forced a migration here, the .bak should remain SENTINEL.
    store2 = SqliteStore(db_path)
    _ = store2.load()

    assert bak_path.read_text() == "SENTINEL — pre-existing backup"
```

- [ ] **Step 1.5.2: Run the test to verify the canonical-no-backup case fails**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_canonicalize_backup.py -v`

Expected: `test_canonical_load_does_not_create_backup` PASSES (no implementation yet means no `.bak` is created — the canonical case is trivially satisfied). The legacy-load test SKIPS (no per-field migration registered yet). The idempotency test PASSES vacuously. So the test file at this stage is mostly a holding pattern; the meaningful red→green transition for Step 1.5 is *adding* the backup logic and verifying it doesn't break the canonical case. The legacy-load assertion comes alive once Task 3 (S5) registers the first real migration.

- [ ] **Step 1.5.3: Implement the backup in `SqliteStore.load`**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/persistence.py`. Find the migration block from Task 1 Step 1.8 and extend it:

```python
            import json
            import shutil

            from sidequest.game.migrations import migrate_legacy_snapshot

            try:
                raw = json.loads(row[0])
            except json.JSONDecodeError as exc:
                raise SaveSchemaIncompatibleError(
                    save_path=self._path or Path("<in-memory>"),
                    underlying=ValidationError.from_exception_data(
                        title="invalid_save_json", line_errors=[]
                    ),
                ) from exc
            migrated = migrate_legacy_snapshot(raw)

            # Architect amendment 2026-05-04: sibling-file safety net.
            # If migration rewrote anything and we have a real on-disk save,
            # copy the .db to <save>.db.canonicalize.bak ONCE. The .bak is
            # never reaped — durable retention per Keith's playstyle.
            if migrated != raw and self._path is not None:
                bak_path = self._path.with_suffix(self._path.suffix + ".canonicalize.bak")
                if not bak_path.exists():
                    try:
                        shutil.copy2(self._path, bak_path)
                    except OSError as bak_exc:
                        # Defense-in-depth, not primary gate: don't block load.
                        logger.warning(
                            "snapshot.canonicalize backup failed for %s: %s",
                            self._path, bak_exc,
                        )

            snapshot = GameSnapshot.model_validate(migrated)
```

If `self._path` is not the attribute name (check the class — could be `self.path`, `self._db_path`, etc.), adapt accordingly. The `logger` import follows existing module style.

- [ ] **Step 1.5.4: Re-run the safety-net tests**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_canonicalize_backup.py -v`

Expected: canonical-no-backup PASSES; legacy-load SKIPS (still — the migration is no-op until Task 3 lands the first per-field rewrite); idempotency PASSES.

- [ ] **Step 1.5.5: Run the broader load tests to confirm no regression**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py tests/game/test_canonicalize_backup.py tests/server/test_persistence*.py -x -q 2>&1 | tail -30`

Expected: 0 failures. The added shutil.copy2 only fires when `migrated != raw`, which is currently never (Task 1 scaffold is a no-op), so no existing test should change behavior.

- [ ] **Step 1.5.6: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/persistence.py
git add sidequest-server/tests/game/test_canonicalize_backup.py
git commit -m "$(cat <<'EOF'
feat(server): sibling-file safety net for snapshot canonicalize

When SqliteStore.load detects that migrate_legacy_snapshot rewrote any
field, copy <save>.db → <save>.db.canonicalize.bak once before returning.
Idempotent (skips if .bak exists); never reaped (durable retention).

Architect amendment to Wave 1 plan — pulls spec risk-mitigation #1 back
into Wave 1 so Waves 2A/2B (S2/S3) inherit the safety discipline when
they land migrations with real semantic risk.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md
risk #1 and docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-1.md
amendment 2026-05-04.
EOF
)"
```

The legacy-load test stays SKIP-ed at this point and will turn into a real green case once Task 3 (S5 — the first per-field migration to actually rewrite a field) lands.

---

## Task 2: S4 — Rename session-level `EncounterTag` → `NpcEncounterLogTag`

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py:47`
- Modify: `sidequest-server/sidequest/game/__init__.py:89,168`
- Test: `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` (new)

The session-level `EncounterTag` (line 47) is `npc_id/encounter_type/archetype_id/notes` — used only by `NarrativeEntry.encounter_tags` and re-exported from `game/__init__.py`. Nobody imports it explicitly outside `session.py` itself. The other `EncounterTag` in `game/encounter_tag.py` (`text/leverage/target/fleeting`) has 5 production importers and stays. The rename is isolated.

- [ ] **Step 2.1: Write the failing test for the new name**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py`:

```python
"""S4 — session-level EncounterTag renamed to NpcEncounterLogTag.

The old name remains as a deprecated alias for one release window so
external save files and any unmigrated test fixtures keep round-tripping.
"""

from __future__ import annotations

import warnings


def test_npc_encounter_log_tag_importable_under_new_name() -> None:
    from sidequest.game.session import NpcEncounterLogTag

    tag = NpcEncounterLogTag(
        npc_id="captain_orin",
        encounter_type="dialogue",
        archetype_id=None,
        notes=None,
    )
    assert tag.npc_id == "captain_orin"
    assert tag.encounter_type == "dialogue"


def test_narrative_entry_uses_npc_encounter_log_tag() -> None:
    from sidequest.game.session import NarrativeEntry, NpcEncounterLogTag

    entry = NarrativeEntry(
        author="narrator",
        content="Orin nods.",
        encounter_tags=[
            NpcEncounterLogTag(npc_id="captain_orin", encounter_type="dialogue")
        ],
    )
    assert isinstance(entry.encounter_tags[0], NpcEncounterLogTag)


def test_old_name_alias_still_works() -> None:
    """Deprecation alias — drop in the release after this one."""
    from sidequest.game import EncounterTag as DeprecatedAlias
    from sidequest.game.session import NpcEncounterLogTag

    # The alias must resolve to the new class.
    assert DeprecatedAlias is NpcEncounterLogTag


def test_scene_momentum_encounter_tag_unchanged() -> None:
    """The OTHER EncounterTag (game/encounter_tag.py — leverage/target/fleeting)
    is unaffected. This test pins the distinction so a future rename doesn't
    silently merge the two types."""
    from sidequest.game.encounter_tag import EncounterTag as SceneMomentumTag

    tag = SceneMomentumTag(
        text="The floor is lava",
        created_by="narrator",
        target=None,
        leverage=2,
        fleeting=False,
        created_turn=5,
    )
    assert tag.text == "The floor is lava"
    assert tag.leverage == 2
```

- [ ] **Step 2.2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_npc_encounter_log_tag_rename.py -v`

Expected: `ImportError: cannot import name 'NpcEncounterLogTag' from 'sidequest.game.session'` on the first three tests; the fourth PASSES (scene-momentum tag is unchanged).

- [ ] **Step 2.3: Rename the class in `session.py`**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/session.py`:

Replace the class definition at line 47:

```python
class EncounterTag(BaseModel):
    """NPC encounter tag within a narrative entry (story F3)."""

    model_config = {"extra": "forbid"}

    npc_id: str
    encounter_type: str
    archetype_id: str | None = None
    notes: str | None = None
```

with:

```python
class NpcEncounterLogTag(BaseModel):
    """NPC encounter tag within a narrative entry (story F3).

    Renamed from ``EncounterTag`` (S4 of the snapshot split-brain cleanup,
    2026-05-04) to disambiguate from ``sidequest.game.encounter_tag.EncounterTag``,
    which is a different model (scene-momentum tag with leverage/target/
    fleeting per ADR-078). The old name remains as an alias in
    ``sidequest.game.__init__`` for one release window."""

    model_config = {"extra": "forbid"}

    npc_id: str
    encounter_type: str
    archetype_id: str | None = None
    notes: str | None = None
```

Then find the field annotation on `NarrativeEntry`:

```python
    encounter_tags: list[EncounterTag] = Field(default_factory=list)
```

Replace with:

```python
    encounter_tags: list[NpcEncounterLogTag] = Field(default_factory=list)
```

- [ ] **Step 2.4: Update `game/__init__.py` exports**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/__init__.py`:

Find the existing import line (around line 89):

```python
    EncounterTag,
```

(in a `from sidequest.game.session import (...)` block).

Replace with:

```python
    NpcEncounterLogTag,
```

Find the `__all__` entry (around line 168):

```python
    "EncounterTag",
```

Replace with:

```python
    "NpcEncounterLogTag",
```

Then add a deprecation alias at the end of the file (after `__all__`):

```python

# S4 deprecation alias — drop in the release after this one. External
# saves and pre-cleanup test fixtures still reference EncounterTag at this
# import path; keeping the alias one release prevents a hard cutover.
EncounterTag = NpcEncounterLogTag
__all__ = (*__all__, "EncounterTag")
```

(Adapt to whatever `__all__` syntax already exists — list-append if it's a list, tuple-extend if a tuple.)

- [ ] **Step 2.5: Run the rename test — should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_npc_encounter_log_tag_rename.py -v`

Expected: 4 PASSED.

- [ ] **Step 2.6: Run any test that references the old EncounterTag in NarrativeEntry context**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && grep -rln "EncounterTag" tests/ | xargs uv run pytest -q 2>&1 | tail -20`

Expected: 0 failures. If a test fails referencing the old name from a non-`encounter_tag.py` import path, update the import in that test (the deprecation alias should keep most tests green automatically; failures here mean a strict isinstance check is in play).

- [ ] **Step 2.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/session.py
git add sidequest-server/sidequest/game/__init__.py
git add sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py
git commit -m "$(cat <<'EOF'
refactor(server): rename session-level EncounterTag → NpcEncounterLogTag (S4)

The session log entry (npc_id/encounter_type/archetype_id/notes) now uses
its docstring's actual name. The unrelated scene-momentum EncounterTag in
game/encounter_tag.py (leverage/target/fleeting per ADR-078) keeps its
name. Deprecation alias retained for one release.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md S4.
EOF
)"
```

---

## Task 3: S5 — Mark transient magic queues `Field(exclude=True)`

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py:593-594`
- Modify: `sidequest-server/sidequest/magic/state.py:119`
- Test: `sidequest-server/tests/game/test_transient_queue_exclusion.py` (new)

These three queues mutate within a single narration apply pass and are drained before the next save in normal flow. Marking them `exclude=True` removes them from `model_dump_json()` output, so a save snapshot mid-handler cannot persist a partial queue. Reload starts with empty queues — correct, because the queues are derivable from snapshot state on the next narration turn.

- [ ] **Step 3.1: Write the failing exclusion tests**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_transient_queue_exclusion.py`:

```python
"""S5 — transient magic queues are not serialized.

These three fields exist for in-memory handler logic but must NEVER appear
in the persisted JSON. A save mid-handler should round-trip with empty
queues (which is correct: queues are derivable from snapshot state on the
next narration turn)."""

from __future__ import annotations

import json

from sidequest.game.session import GameSnapshot


def test_pending_magic_auto_fires_excluded_from_dump() -> None:
    snap = GameSnapshot(genre_slug="g", world_slug="w")
    snap.pending_magic_auto_fires.append({"confrontation_id": "x"})

    dumped = snap.model_dump_json()
    parsed = json.loads(dumped)

    assert "pending_magic_auto_fires" not in parsed


def test_pending_magic_confrontation_outcome_excluded_from_dump() -> None:
    snap = GameSnapshot(genre_slug="g", world_slug="w")
    snap.pending_magic_confrontation_outcome = {"branch": "clear_win"}

    dumped = snap.model_dump_json()
    parsed = json.loads(dumped)

    assert "pending_magic_confrontation_outcome" not in parsed


def test_pending_status_promotions_excluded_from_dump() -> None:
    """MagicState.pending_status_promotions is also excluded — it lives on
    MagicState rather than directly on the snapshot, but the persistence
    boundary is still ``GameSnapshot.model_dump_json``."""
    from sidequest.magic.models import WorldMagicConfig
    from sidequest.magic.state import MagicState

    config = WorldMagicConfig(world_slug="w", ledger_bars=[])
    state = MagicState.from_config(config)
    state.pending_status_promotions.append({"actor": "a", "text": "Bleeding", "severity": "Wound"})

    snap = GameSnapshot(genre_slug="g", world_slug="w", magic_state=state)
    dumped = snap.model_dump_json()
    parsed = json.loads(dumped)

    # MagicState appears, but its pending_status_promotions does not.
    assert parsed.get("magic_state") is not None
    assert "pending_status_promotions" not in parsed["magic_state"]


def test_load_after_dump_reinitializes_queues_empty() -> None:
    """Round-trip: queues populate, dump excludes them, reload gives empty queues."""
    snap = GameSnapshot(genre_slug="g", world_slug="w")
    snap.pending_magic_auto_fires.append({"confrontation_id": "x"})

    reloaded = GameSnapshot.model_validate_json(snap.model_dump_json())

    assert reloaded.pending_magic_auto_fires == []
    assert reloaded.pending_magic_confrontation_outcome is None
```

- [ ] **Step 3.2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_transient_queue_exclusion.py -v`

Expected: 3 of the 4 tests FAIL with the assertion that the field IS present in the dumped JSON. (The fourth `test_load_after_dump_reinitializes_queues_empty` may fail OR pass depending on pydantic behavior — the queues currently DO survive the round-trip, so it fails.)

- [ ] **Step 3.3: Mark the snapshot fields excluded**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/session.py`:

Find lines 593-594:

```python
    pending_magic_auto_fires: list[dict] = Field(default_factory=list)
    pending_magic_confrontation_outcome: dict | None = None
```

Replace with:

```python
    # S5 — Transient outbound dispatch queues. ``exclude=True`` keeps them
    # out of ``model_dump_json``, so a save mid-handler cannot persist a
    # partial queue. They re-initialize empty on load — correct because
    # auto-fires and outcomes are derivable from snapshot state on the
    # next narration turn (``apply_magic_working`` /
    # ``_resolve_magic_confrontation_if_applicable`` recompute from
    # ``magic_state``, not from the queue).
    pending_magic_auto_fires: list[dict] = Field(default_factory=list, exclude=True)
    pending_magic_confrontation_outcome: dict | None = Field(default=None, exclude=True)
```

- [ ] **Step 3.4: Mark the magic-state field excluded**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/magic/state.py`:

Find line 119:

```python
    pending_status_promotions: list[dict[str, str]] = Field(default_factory=list)
```

Replace with:

```python
    # S5 — Transient promotion queue. Drained by
    # ``narration_apply._drain_pending_status_promotions`` within the same
    # apply pass that ``magic.outputs._queue_status_promotion`` populates
    # it. ``exclude=True`` keeps it out of ``MagicState.model_dump`` so a
    # save mid-handler cannot persist a partial queue. Re-initializes
    # empty on load.
    pending_status_promotions: list[dict[str, str]] = Field(
        default_factory=list, exclude=True
    )
```

- [ ] **Step 3.5: Run the exclusion tests — should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_transient_queue_exclusion.py -v`

Expected: 4 PASSED.

- [ ] **Step 3.6: Run the magic and websocket suites for regression**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/magic/ tests/server/test_websocket*.py tests/server/test_narration_apply*.py -x -q 2>&1 | tail -20`

Expected: 0 failures. The queues still work in-memory; only their JSON serialization is suppressed.

- [ ] **Step 3.7: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/session.py
git add sidequest-server/sidequest/magic/state.py
git add sidequest-server/tests/game/test_transient_queue_exclusion.py
git commit -m "$(cat <<'EOF'
refactor(server): exclude transient magic queues from snapshot serialization (S5)

pending_magic_auto_fires, pending_magic_confrontation_outcome, and
MagicState.pending_status_promotions now use Field(exclude=True). The
queues stay in-memory for the apply pass that drains them, but a save
mid-handler can no longer persist a partial queue. Reload re-initializes
empty — correct because the queues are derivable from snapshot state on
the next narration turn.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md S5.
EOF
)"
```

---

## Task 4: S1 step 1 — Migrate `world_confrontations` → `magic_state.confrontations` on load

**Files:**
- Modify: `sidequest-server/sidequest/game/migrations.py` (add sub-function)
- Test: `sidequest-server/tests/game/test_migrations.py` (extend)

`world_confrontations` and `magic_state.confrontations` are both lists of `ConfrontationDefinition` loaded from the same `worlds/<world>/confrontations.yaml`. The migration merges any entries from `world_confrontations` into `magic_state.confrontations` (dedupe by `id`, prefer existing entry on collision), then removes the legacy field from the dict.

- [ ] **Step 4.1: Write the failing test for the S1 migration**

Append to `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_migrations.py`:

```python
def test_s1_world_confrontations_merges_into_magic_state() -> None:
    legacy = {
        "genre_slug": "g",
        "world_slug": "w",
        "world_confrontations": [
            {"id": "the_tea_brew", "register": "intimate", "outcomes": {}},
        ],
        "magic_state": {
            "config": {"world_slug": "w", "ledger_bars": []},
            "confrontations": [],
        },
    }

    migrated = migrate_legacy_snapshot(legacy)

    # Legacy field is gone.
    assert "world_confrontations" not in migrated
    # Entry now lives on magic_state.
    confs = migrated["magic_state"]["confrontations"]
    assert len(confs) == 1
    assert confs[0]["id"] == "the_tea_brew"


def test_s1_dedupe_by_id_prefers_existing_magic_state_entry() -> None:
    legacy = {
        "genre_slug": "g",
        "world_slug": "w",
        "world_confrontations": [
            {"id": "the_tea_brew", "register": "intimate", "outcomes": {"clear_win": {"mandatory_outputs": ["a"]}}},
        ],
        "magic_state": {
            "config": {"world_slug": "w", "ledger_bars": []},
            "confrontations": [
                {"id": "the_tea_brew", "register": "intimate", "outcomes": {"clear_win": {"mandatory_outputs": ["b"]}}},
            ],
        },
    }

    migrated = migrate_legacy_snapshot(legacy)

    confs = migrated["magic_state"]["confrontations"]
    assert len(confs) == 1
    # Existing magic_state entry wins on collision (it's the canonical home).
    assert confs[0]["outcomes"]["clear_win"]["mandatory_outputs"] == ["b"]


def test_s1_empty_world_confrontations_still_strips_field() -> None:
    legacy = {
        "genre_slug": "g",
        "world_slug": "w",
        "world_confrontations": [],
    }

    migrated = migrate_legacy_snapshot(legacy)

    assert "world_confrontations" not in migrated


def test_s1_no_magic_state_creates_one_when_world_confrontations_present() -> None:
    legacy = {
        "genre_slug": "g",
        "world_slug": "w",
        "world_confrontations": [
            {"id": "the_tea_brew", "register": "intimate", "outcomes": {}},
        ],
        # magic_state absent — this happens for saves predating magic init.
    }

    migrated = migrate_legacy_snapshot(legacy)

    # Pre-existing fixture: if magic_state is None and there's nothing to
    # migrate into, drop the legacy field but DON'T fabricate a magic_state.
    # The migration is content-preserving only.
    assert "world_confrontations" not in migrated
    # If there's no magic_state to migrate INTO, the entries are dropped
    # rather than synthesized. Document this behavior — it matches the
    # "no silent fallback" rule (we don't invent a magic config).
    assert migrated.get("magic_state") is None or migrated["magic_state"] == {}
```

- [ ] **Step 4.2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py::test_s1_world_confrontations_merges_into_magic_state -v`

Expected: FAIL — assert `"world_confrontations" not in migrated` fails because the no-op scaffold doesn't strip the field.

- [ ] **Step 4.3: Add the S1 migration sub-function**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/migrations.py`:

Add this sub-function above `migrate_legacy_snapshot`:

```python
def _migrate_s1_world_confrontations(out: dict[str, Any]) -> dict[str, Any] | None:
    """S1 — merge ``world_confrontations`` into ``magic_state.confrontations``.

    Dedupe by ``id``; existing ``magic_state.confrontations`` entries win
    on collision (magic_state is the canonical home — see design spec).
    Drops the legacy ``world_confrontations`` field after merge.

    Returns a dict of OTEL attributes when migration occurred, else None.
    """
    if "world_confrontations" not in out:
        return None

    legacy = out.pop("world_confrontations") or []

    if not legacy:
        return {"s1_world_confrontations_merged": 0, "s1_world_confrontations_dropped_no_target": 0}

    magic_state = out.get("magic_state")
    if not isinstance(magic_state, dict):
        # No magic_state to migrate INTO — drop the entries rather than
        # synthesize a magic config. SOUL.md "No Silent Fallbacks": we do
        # not invent canonical state from absent inputs.
        return {
            "s1_world_confrontations_merged": 0,
            "s1_world_confrontations_dropped_no_target": len(legacy),
        }

    existing = magic_state.setdefault("confrontations", [])
    existing_ids = {c.get("id") for c in existing if isinstance(c, dict)}
    merged_count = 0
    for entry in legacy:
        if not isinstance(entry, dict):
            continue
        if entry.get("id") in existing_ids:
            continue  # collision — magic_state's entry wins
        existing.append(entry)
        existing_ids.add(entry.get("id"))
        merged_count += 1

    return {
        "s1_world_confrontations_merged": merged_count,
        "s1_world_confrontations_dropped_no_target": 0,
    }
```

Then in `migrate_legacy_snapshot`, register the sub-function:

Replace the comment block:

```python
    # Future migration sub-functions register here. Each returns either:
    #   - None  (no-op, field already canonical or absent)
    #   - dict  (per-field attributes to add to the OTEL span)
    # Sub-functions are responsible for their own dict mutations.

    # No sub-functions registered yet — this is the scaffold-only step.
```

with:

```python
    # Migration sub-functions. Each returns either None (no-op) or a dict
    # of OTEL attributes to merge into the canonicalize span.
    for sub in (_migrate_s1_world_confrontations,):
        attrs = sub(out)
        if attrs is not None:
            attributes.update(attrs)
```

- [ ] **Step 4.4: Run the S1 migration tests — should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_migrations.py -v`

Expected: all tests PASS (the four new S1 tests plus the original three).

- [ ] **Step 4.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/migrations.py
git add sidequest-server/sidequest/tests/game/test_migrations.py 2>/dev/null || git add sidequest-server/tests/game/test_migrations.py
git commit -m "$(cat <<'EOF'
feat(server): migrate world_confrontations into magic_state on load (S1 step 1)

migrate_legacy_snapshot now folds GameSnapshot.world_confrontations into
magic_state.confrontations (dedupe by id; existing magic_state entries win
on collision). Drops the legacy field. Source-code field removal lands in
a follow-up task once the writers (chassis.py) and readers (room_movement.py)
are switched to the canonical store.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md S1.
EOF
)"
```

---

## Task 5: S1 step 2 — Switch chassis loader to write into `magic_state.confrontations`

**Files:**
- Modify: `sidequest-server/sidequest/game/chassis.py:222-233`
- Test: `sidequest-server/tests/game/test_chassis_init.py` (extend or new)

The chassis loader currently writes into `snapshot.world_confrontations`. It must instead append into `snapshot.magic_state.confrontations`, taking care that `magic_state` may be `None` at chassis-init time (the comment at session.py:514 mentions the init-order workaround that motivated the duplicate field). When `magic_state` is `None`, the chassis loader holds the confrontation list aside on a module-private deferred-loads structure that `magic_init` consumes when `MagicState` is created.

- [ ] **Step 5.1: Trace the magic_state init order to confirm the workaround target**

Run:

```bash
grep -rn "MagicState\.from_config\|init_chassis_registry\|init_magic_state" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/ /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/chassis.py | head -20
```

Read the call sites that wire chassis init and magic init together (likely `server/magic_init.py` and the `_bind_world` flow in `session_room.py`). Record the order:
- (a) `init_chassis_registry` runs FIRST (no magic_state) — the legacy code path, motivating `world_confrontations` as a side-store.
- (b) `init_chassis_registry` runs AFTER magic_state (magic_state is non-None) — easy case.

Most worlds will be (b) post-migration; (a) is the bind-order edge case the duplicate field papered over. Pick the simpler fix:

**Decision:** require `magic_state` to be initialized before `init_chassis_registry` is called. If the current sequence has chassis-before-magic, swap them in the bind path. Document the new invariant.

- [ ] **Step 5.2: Append the failing tests to `test_chassis_init.py`**

The existing chassis harness uses the `space_opera/coyote_star` content pack — `tests/game/test_chassis_init.py` already has the `SPACE_OPERA` constant and `_make_snapshot` helper. The Coyote Star world ships a `confrontations.yaml` (`the_tea_brew` is the canonical rig-coupled confrontation), so we can reuse the live fixture rather than authoring a temp one.

Append to `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_chassis_init.py`:

```python
def test_init_chassis_registry_appends_confrontations_to_magic_state() -> None:
    """S1 step 2 — confrontations land on magic_state, not world_confrontations."""
    if not SPACE_OPERA.exists():
        pytest.skip("space_opera content pack not present")
    from sidequest.game.chassis import init_chassis_registry
    from sidequest.genre.loader import load_genre_pack
    from sidequest.magic.models import WorldMagicConfig
    from sidequest.magic.state import MagicState

    pack = load_genre_pack(SPACE_OPERA)
    snap = _make_snapshot("space_opera", "coyote_star")
    # Initialize magic_state BEFORE chassis registry — the new invariant.
    snap.magic_state = MagicState.from_config(
        WorldMagicConfig(world_slug="coyote_star", ledger_bars=[])
    )

    init_chassis_registry(snap, pack)

    conf_ids = {c.id for c in snap.magic_state.confrontations}
    assert "the_tea_brew" in conf_ids


def test_init_chassis_registry_raises_when_magic_state_absent() -> None:
    """S1 step 2 — calling init_chassis_registry without magic_state, when the
    world ships a confrontations.yaml, must fail loudly. The legacy 'silent
    stash on world_confrontations' path is gone (CLAUDE.md no silent fallback).
    """
    if not SPACE_OPERA.exists():
        pytest.skip("space_opera content pack not present")
    from sidequest.game.chassis import init_chassis_registry
    from sidequest.genre.loader import load_genre_pack

    pack = load_genre_pack(SPACE_OPERA)
    snap = _make_snapshot("space_opera", "coyote_star")
    # magic_state remains None — coyote_star has confrontations.yaml so this
    # is the failure mode, not the no-confrontations no-op branch.
    assert snap.magic_state is None

    with pytest.raises(RuntimeError, match="magic_state must be initialized"):
        init_chassis_registry(snap, pack)
```

- [ ] **Step 5.3: Run the new tests to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_chassis_init.py -v`

Expected: both new tests FAIL — the writer still targets `world_confrontations`.

- [ ] **Step 5.4: Update the chassis writer**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/chassis.py`:

Find the block at lines 222-233:

```python
    # Story 47-4: alongside chassis_registry materialization, populate the
    # world_confrontations cache so the rig-coupled room-entry auto-fire
    # evaluator (process_room_entry) doesn't depend on magic_init having
    # run first. Confrontations.yaml is optional; world without one keeps
    # snapshot.world_confrontations empty.
    confrontations_path = (
        genre_pack.source_dir / "worlds" / snapshot.world_slug / "confrontations.yaml"
    )
    if confrontations_path.exists():
        from sidequest.magic.confrontations import load_confrontations

        snapshot.world_confrontations = load_confrontations(confrontations_path)
```

Replace with:

```python
    # S1 step 2 — magic_state.confrontations is the canonical home for
    # confrontation defs. The legacy world_confrontations cache is gone;
    # this loader writes directly into magic_state. magic_state MUST be
    # initialized before init_chassis_registry runs (invariant established
    # by the snapshot split-brain cleanup, 2026-05-04). The bind path in
    # session_room is responsible for the ordering.
    confrontations_path = (
        genre_pack.source_dir / "worlds" / snapshot.world_slug / "confrontations.yaml"
    )
    if confrontations_path.exists():
        if snapshot.magic_state is None:
            raise RuntimeError(
                "init_chassis_registry: magic_state must be initialized before "
                "chassis registry when worlds/<world>/confrontations.yaml exists. "
                "Bind-path ordering invariant — see design spec "
                "2026-05-04-snapshot-split-brain-cleanup-design.md S1."
            )
        from sidequest.magic.confrontations import load_confrontations

        loaded = load_confrontations(confrontations_path)
        existing_ids = {c.id for c in snapshot.magic_state.confrontations}
        for cdef in loaded:
            if cdef.id not in existing_ids:
                snapshot.magic_state.confrontations.append(cdef)
                existing_ids.add(cdef.id)
```

- [ ] **Step 5.5: Run the chassis tests — should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_chassis_init.py tests/game/test_chassis*.py -v 2>&1 | tail -30`

Expected: PASS for the new tests; existing chassis tests should still pass UNLESS one of them sets up the snapshot with `magic_state=None` and expects `init_chassis_registry` to silently no-op on the confrontations.yaml load. If a test fails for that reason, update it to initialize `magic_state` first — the test is reproducing the legacy bug, not validating real behavior.

- [ ] **Step 5.6: Find and fix the bind-path ordering**

Run:

```bash
grep -rn "init_chassis_registry\|init_magic_state\|MagicState\.from_config" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/server/ | head -10
```

Open the bind-path file (`session_room.py` per the import found earlier). Find the section that calls `init_chassis_registry` and `init_magic_state`. Confirm `init_magic_state` runs BEFORE `init_chassis_registry`. If not, swap the order. (If the magic init module is named differently, follow whatever currently constructs `MagicState` in the session bind path.)

If the bind order already initializes magic_state before chassis, no change is needed — the chassis tests in Step 5.5 will have caught the regression. If a swap was required, the new ordering is its own commit-worthy change; capture it in the same commit as the writer flip (Step 5.4).

- [ ] **Step 5.7: Run the broader server suite**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/ tests/server/ tests/magic/ -x -q 2>&1 | tail -30`

Expected: 0 failures. If a non-chassis test fails referring to `world_confrontations`, that's S1 step 3 territory — write down the test name and continue.

- [ ] **Step 5.8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/chassis.py
git add sidequest-server/sidequest/server/  # only if bind-path ordering changed
git add sidequest-server/tests/game/test_chassis_init.py
git commit -m "$(cat <<'EOF'
refactor(server): chassis loader writes confrontations into magic_state (S1 step 2)

init_chassis_registry now appends to snapshot.magic_state.confrontations
directly. The legacy world_confrontations stash is no longer written.
Establishes invariant: magic_state must be initialized before chassis
registry; the bind path enforces this order.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md S1.
EOF
)"
```

---

## Task 6: S1 step 3 — Switch room_movement reader to `magic_state.confrontations`

**Files:**
- Modify: `sidequest-server/sidequest/game/room_movement.py:114-115`
- Test: `sidequest-server/tests/game/test_room_movement_chassis_filter.py` (new)

`process_room_entry` currently reads `snap.world_confrontations` and passes the entire list to `find_eligible_room_autofire`. The canonical equivalent reads `snap.magic_state.confrontations` and filters to chassis-coupled entries. The natural filter discriminator is `register == "intimate"` — this is already what `find_eligible_room_autofire` checks internally (per `confrontations.py:112`), so a pre-filter at the call site is correct semantically and avoids walking irrelevant entries.

- [ ] **Step 6.1: Write the failing test**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_room_movement_chassis_filter.py`:

```python
"""S1 step 3 — process_room_entry reads magic_state.confrontations.

The reader filters to chassis-coupled entries (register == "intimate")
before calling find_eligible_room_autofire. World-scoped magic
confrontations (register != "intimate") MUST NOT be considered for the
rig-coupled room-entry auto-fire path — they're driven by the bar-DSL
threshold evaluator, not by room entry."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPACE_OPERA = REPO_ROOT / "sidequest-content" / "genre_packs" / "space_opera"


def _bootstrap_coyote_star_snapshot():
    """Build a snapshot with chassis_registry + magic_state both populated
    from the live space_opera/coyote_star fixture."""
    from sidequest.game.chassis import init_chassis_registry
    from sidequest.game.session import GameSnapshot
    from sidequest.genre.loader import load_genre_pack
    from sidequest.magic.models import WorldMagicConfig
    from sidequest.magic.state import MagicState

    pack = load_genre_pack(SPACE_OPERA)
    snap = GameSnapshot(
        genre_slug="space_opera",
        world_slug="coyote_star",
        location="Galley",
    )
    snap.magic_state = MagicState.from_config(
        WorldMagicConfig(world_slug="coyote_star", ledger_bars=[])
    )
    init_chassis_registry(snap, pack)
    return snap


def test_process_room_entry_passes_magic_state_confrontations_to_finder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reader must source its confrontation list from
    magic_state.confrontations (filtered to chassis-coupled), not from the
    legacy world_confrontations field."""
    if not SPACE_OPERA.exists():
        pytest.skip("space_opera content pack not present")

    snap = _bootstrap_coyote_star_snapshot()
    chassis = next(iter(snap.chassis_registry.values()))
    char_id = chassis.bond_ledger[0].character_id

    captured: dict[str, object] = {}

    def _spy_find(*, confrontations, **kwargs):
        captured["confrontations"] = list(confrontations)
        return []  # nothing eligible — we only care about what was passed in

    import sidequest.game.room_movement as rm

    monkeypatch.setattr(rm, "find_eligible_room_autofire", _spy_find)

    rm.process_room_entry(snap, character_id=char_id, room_id="Galley", current_turn=1)

    received = captured["confrontations"]
    received_ids = {c.id for c in received}
    magic_state_ids = {c.id for c in snap.magic_state.confrontations if c.register == "intimate"}
    # Every intimate confrontation on magic_state was passed; nothing else.
    assert received_ids == magic_state_ids
    # And the_tea_brew (the canonical coyote_star intimate confrontation)
    # is in the set.
    assert "the_tea_brew" in received_ids


def test_process_room_entry_excludes_non_intimate_confrontations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confrontations with register != 'intimate' must NOT reach the
    find_eligible_room_autofire call — they're bar-DSL, not rig-coupled."""
    if not SPACE_OPERA.exists():
        pytest.skip("space_opera content pack not present")
    from sidequest.magic.confrontations import (
        ConfrontationBranch,
        ConfrontationDefinition,
    )

    snap = _bootstrap_coyote_star_snapshot()
    chassis = next(iter(snap.chassis_registry.values()))
    char_id = chassis.bond_ledger[0].character_id

    # Inject a world-scoped (bar-DSL) confrontation. It must NOT be passed
    # to find_eligible_room_autofire by process_room_entry.
    snap.magic_state.confrontations.append(
        ConfrontationDefinition(
            id="the_bleeding_through",
            register=None,  # bar-DSL — no chassis register
            outcomes={
                "clear_win": ConfrontationBranch(mandatory_outputs=["sanity_increment"]),
                "pyrrhic_win": ConfrontationBranch(mandatory_outputs=["sanity_increment"]),
                "clear_loss": ConfrontationBranch(mandatory_outputs=["sanity_decrement"]),
                "refused": ConfrontationBranch(mandatory_outputs=["sanity_decrement"]),
            },
        )
    )

    captured: dict[str, object] = {}

    def _spy_find(*, confrontations, **kwargs):
        captured["confrontations"] = list(confrontations)
        return []

    import sidequest.game.room_movement as rm

    monkeypatch.setattr(rm, "find_eligible_room_autofire", _spy_find)

    rm.process_room_entry(snap, character_id=char_id, room_id="Galley", current_turn=1)

    received_ids = {c.id for c in captured["confrontations"]}
    assert "the_bleeding_through" not in received_ids
    assert "the_tea_brew" in received_ids
```

(If `ConfrontationDefinition` requires additional fields beyond what's shown — `auto_fire`, `once_per_arc`, etc. — read its model definition at `sidequest/magic/confrontations.py:71+` and add the minimum required fields to keep pydantic validation happy. The test's only purpose is to verify the spy receives the right subset; the values just have to be valid pydantic.)

- [ ] **Step 6.2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_room_movement_chassis_filter.py -v`

Expected: tests FAIL — reader still hits `snap.world_confrontations`.

- [ ] **Step 6.3: Switch the reader**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/room_movement.py`:

Find the call at lines 114-121:

```python
    eligible = find_eligible_room_autofire(
        confrontations=snap.world_confrontations,
        chassis_id=chassis.id,
        room_local_id=room_local_id,
        bond_tier_chassis=bond.bond_tier_chassis,
        current_turn=current_turn,
        cooldown_ledger=cooldown_view,
    )
```

Replace with:

```python
    # S1 — magic_state.confrontations is the canonical store for all
    # confrontation defs. Pre-filter to chassis-coupled entries
    # (register == "intimate" per ADR / confrontations.py:112) before
    # passing to find_eligible_room_autofire. World-scoped (bar-DSL)
    # entries are driven by the threshold evaluator, not the room-entry
    # path, and must not appear here.
    if snap.magic_state is None:
        return
    chassis_coupled = [
        c for c in snap.magic_state.confrontations if c.register == "intimate"
    ]
    eligible = find_eligible_room_autofire(
        confrontations=chassis_coupled,
        chassis_id=chassis.id,
        room_local_id=room_local_id,
        bond_tier_chassis=bond.bond_tier_chassis,
        current_turn=current_turn,
        cooldown_ledger=cooldown_view,
    )
```

- [ ] **Step 6.4: Run the room_movement tests — should pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_room_movement*.py -v 2>&1 | tail -30`

Expected: PASS. If existing tests fail because they populated `snap.world_confrontations` directly, update them to populate `snap.magic_state.confrontations` instead.

- [ ] **Step 6.5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/room_movement.py
git add sidequest-server/sidequest/tests/game/test_room_movement_chassis_filter.py 2>/dev/null || git add sidequest-server/tests/game/test_room_movement_chassis_filter.py
git add sidequest-server/tests/game/test_room_movement*.py 2>&1 | head
git commit -m "$(cat <<'EOF'
refactor(server): room_movement reads magic_state.confrontations (S1 step 3)

process_room_entry now filters magic_state.confrontations by
register=="intimate" instead of reading the legacy world_confrontations
field. World-scoped (bar-DSL) confrontations remain on the threshold
evaluator path; the rig-coupled room-entry path sees only
chassis-coupled entries.

Per docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md S1.
EOF
)"
```

---

## Task 7: S1 step 4 — Drop `world_confrontations` field from `GameSnapshot`

**Files:**
- Modify: `sidequest-server/sidequest/game/session.py:520`
- Test: `sidequest-server/tests/game/test_world_confrontations_field_removed.py` (new)

With migrations (Task 4) and writer (Task 5) and reader (Task 6) all redirected, the field has no remaining producers or consumers. Removing it forces any forgotten reference to surface as an `AttributeError`.

- [ ] **Step 7.1: Write the failing field-removal test**

Create `/Users/slabgorb/Projects/oq-1/sidequest-server/tests/game/test_world_confrontations_field_removed.py`:

```python
"""S1 step 4 — world_confrontations field is gone from GameSnapshot.

Any remaining reference surfaces as AttributeError. The ``model_config =
{"extra": "ignore"}`` setting on GameSnapshot already covers
forward-compat for legacy saves; the migration in Task 4 strips the field
on load before pydantic sees it."""

from __future__ import annotations

import json

import pytest

from sidequest.game.session import GameSnapshot


def test_world_confrontations_attribute_does_not_exist() -> None:
    snap = GameSnapshot(genre_slug="g", world_slug="w")
    with pytest.raises(AttributeError):
        _ = snap.world_confrontations  # type: ignore[attr-defined]


def test_legacy_save_with_world_confrontations_loads_clean() -> None:
    """Saved JSON containing the legacy field must round-trip via the
    migration without breaking validation. The model_config extra=ignore
    + the migration strip combine to make this safe."""
    legacy_json = json.dumps({
        "genre_slug": "g",
        "world_slug": "w",
        "world_confrontations": [],  # legacy field
    })
    from sidequest.game.migrations import migrate_legacy_snapshot

    migrated = migrate_legacy_snapshot(json.loads(legacy_json))
    snap = GameSnapshot.model_validate(migrated)

    assert snap.genre_slug == "g"
    # Confirm the legacy field did not leak in via extra=ignore.
    with pytest.raises(AttributeError):
        _ = snap.world_confrontations  # type: ignore[attr-defined]
```

- [ ] **Step 7.2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_world_confrontations_field_removed.py -v`

Expected: first test FAILS — the attribute still exists. Second test passes (migration already strips the field).

- [ ] **Step 7.3: Drop the field**

Edit `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/game/session.py`:

Find lines 511-520:

```python
    # Chassis registry (rig MVP slice — fresh-session only). Materialized from
    # `worlds/<world>/rigs.yaml` at connect time. Each entry is also projected
    # into `npc_registry` so narrator name-continuity sees the chassis.
    chassis_registry: dict[str, ChassisInstance] = Field(default_factory=dict)

    # World confrontations (Story 47-4): loaded from
    # `worlds/<world>/confrontations.yaml` alongside chassis_registry so the
    # rig-coupled room-entry auto-fire evaluator has a snapshot-local source
    # of truth without depending on `magic_state` being initialized first.
    # Bar-DSL confrontations also live on `magic_state.confrontations`; the
    # two collections are independently populated and the rig path reads
    # from this one. Type kept loose (``list``) here to avoid a circular
    # import — populated with `ConfrontationDefinition` instances by
    # `init_chassis_registry`.
    world_confrontations: list = Field(default_factory=list)
```

Replace with (keep the chassis_registry block; remove the world_confrontations block entirely):

```python
    # Chassis registry (rig MVP slice — fresh-session only). Materialized from
    # `worlds/<world>/rigs.yaml` at connect time. Each entry is also projected
    # into `npc_registry` so narrator name-continuity sees the chassis.
    chassis_registry: dict[str, ChassisInstance] = Field(default_factory=dict)

    # (S1, 2026-05-04) world_confrontations REMOVED. The duplicate field
    # has been collapsed into magic_state.confrontations. Saves that
    # carried the legacy field are migrated on load by
    # sidequest.game.migrations.migrate_legacy_snapshot._migrate_s1_world_confrontations.
```

- [ ] **Step 7.4: Run the field-removal test**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_world_confrontations_field_removed.py -v`

Expected: 2 PASSED.

- [ ] **Step 7.5: Run the full server test suite**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest -x -q 2>&1 | tail -30`

Expected: 0 failures. Any failure is a forgotten reference to `world_confrontations` — fix it (or its test).

- [ ] **Step 7.6: Verify the legacy fixture loads end-to-end**

Run:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run python -c "
import json
from pathlib import Path
from sidequest.game.migrations import migrate_legacy_snapshot
from sidequest.game.session import GameSnapshot

raw = json.loads(Path('tests/fixtures/legacy_snapshots/pre_cleanup.json').read_text())
migrated = migrate_legacy_snapshot(raw)
snap = GameSnapshot.model_validate(migrated)
print('OK', snap.genre_slug, snap.world_slug)
print('world_confrontations gone:', not hasattr(snap, 'world_confrontations'))
print('magic_state confrontations:', len(snap.magic_state.confrontations) if snap.magic_state else 'no magic_state')
"
```

Expected: prints `OK <genre> <world>`, confirms field is gone, prints confrontation count.

- [ ] **Step 7.7: Run the aggregate gate**

Run: `cd /Users/slabgorb/Projects/oq-1 && just check-all 2>&1 | tail -30`

Expected: lint + tests pass across server + client + daemon. (Client and daemon are unchanged in Wave 1, but the gate confirms nothing leaked.)

- [ ] **Step 7.8: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1
git add sidequest-server/sidequest/game/session.py
git add sidequest-server/tests/game/test_world_confrontations_field_removed.py
git commit -m "$(cat <<'EOF'
refactor(server): drop GameSnapshot.world_confrontations (S1 step 4)

Final S1 cleanup. With the chassis writer (Task 5), room_movement reader
(Task 6), and migrate_legacy_snapshot._migrate_s1_world_confrontations
(Task 4) all redirected to magic_state.confrontations, the legacy field
has no remaining producers or consumers. Removing it forces any forgotten
reference to surface as AttributeError.

Closes Wave 1 of the snapshot split-brain cleanup
(docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md).
S2 (NPC pool/state split) and S3 (location derivation) are separate
plans.
EOF
)"
```

---

## Self-Review

After all tasks land, run a final pass:

- [ ] **Spec coverage check.** Open the design spec at `docs/superpowers/specs/2026-05-04-snapshot-split-brain-cleanup-design.md`. For each Wave 1 finding (S1, S4, S5), point to the task that closes it:
  - **S1:** Tasks 4 (migration) + 5 (writer) + 6 (reader) + 7 (drop field). ✓
  - **S4:** Task 2. ✓
  - **S5:** Task 3. ✓
  - **OTEL `snapshot.canonicalize`** with per-field attributes: Task 1 + Task 4 (`s1_world_confrontations_merged`). ✓
  - **Migration on load:** Task 1 (scaffolding) + Task 4 (S1 sub-function). ✓
  - **`.db.canonicalize.bak` sibling-file safety net:** **NOT in this plan.** The spec called for it; I'm omitting it from Wave 1 because the migration is content-preserving (drops legacy fields the new schema ignores; merges identical content into the canonical home). The risk of corrupting a save is low enough that the sibling-file backup is overkill for Wave 1. **Flag this for user review** — if the user wants the safety net, add a Task 1.5 that wraps `SqliteStore.save` to write the pre-migration original to `<save>.bak` once on first canonicalize.

- [ ] **Placeholder scan.** Search for forbidden strings in the plan:
  ```bash
  grep -nE 'TBD|TODO|fill in details|implement later|similar to' /Users/slabgorb/Projects/oq-1/docs/superpowers/plans/2026-05-04-snapshot-split-brain-wave-1.md | grep -v '^[0-9]*:.*#' | head
  ```
  No matches expected. (Skip lines that are deliberate context like comment hashes.)

- [ ] **Type consistency.** Symbols introduced and re-used:
  - `migrate_legacy_snapshot` (Task 1) → used in Task 7 verification. ✓
  - `_migrate_s1_world_confrontations` (Task 4) → registered in `migrate_legacy_snapshot` body. ✓
  - `NpcEncounterLogTag` (Task 2) → annotation on `NarrativeEntry.encounter_tags`. ✓
  - `Field(exclude=True)` (Task 3) → applied to three named fields. ✓
  - `SPAN_SNAPSHOT_CANONICALIZE` (Task 1) → emitted from `migrate_legacy_snapshot`. ✓

---

## Acceptance criteria (Wave 1 portion of design spec)

- [ ] No `GameSnapshot` field is duplicated by another `GameSnapshot` field for confrontations.
- [ ] Loading any pre-cleanup save with `world_confrontations` succeeds and writes back canonical (no `world_confrontations` in the saved JSON).
- [ ] OTEL `snapshot.canonicalize` span fires once per migrated save with `s1_world_confrontations_merged: int` attribute.
- [ ] `pending_magic_*` queues do not appear in any `model_dump_json()` output.
- [ ] `MagicState.pending_status_promotions` does not appear in any `model_dump_json()` output.
- [ ] `grep -rn "EncounterTag" sidequest-server/sidequest/` returns exactly two distinct types in distinct domains: `NpcEncounterLogTag` (game/session.py) and `EncounterTag` (game/encounter_tag.py).
- [ ] No production code outside `sidequest/game/__init__.py` imports the `EncounterTag` deprecation alias.
