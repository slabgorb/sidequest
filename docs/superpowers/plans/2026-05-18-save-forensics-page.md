# Save Forensics Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A read-only `/forensics` web page that opens a local save and lets you scrub a turn timeline with per-turn drill-down (narrative, raw events, derived state deltas, per-player projection lens, scrapbook).

**Architecture:** Mirror the proven `dashboard.py` delivery pattern — a self-contained static HTML page served by a 4-line `FileResponse` route, plus three read-only REST endpoints in the existing `create_rest_router()`. A pure `forensic_fold` module folds the trusted event log into derived `StateDelta` fields with per-field source-seq provenance; a thin `forensic_query` module assembles per-turn bundles. Truth is tiered: stored vs. derived vs. absent, never blended, never fabricated.

**Tech Stack:** Python 3 / FastAPI / stdlib `sqlite3` / pydantic v2 (existing); plain HTML+CSS+JS (no React, no build step); pytest + `fastapi.testclient.TestClient`.

**Spec:** `docs/superpowers/specs/2026-05-18-save-forensics-page-design.md`

**Repo & branch:** all work in `sidequest-server`, on a feature branch off `develop`:
`git -C sidequest-server checkout develop && git -C sidequest-server pull --ff-only && git -C sidequest-server checkout -b feat/save-forensics-page`
(Subrepos default to `develop`; the orchestrator is on `main` — never commit server code from the orchestrator root.)

**Run tests via the testing-runner subagent** per project rules, not raw `pytest`, except the single targeted `uv run pytest <nodeid>` red/green checks each task specifies.

---

## File Structure

All paths under `sidequest-server/`.

| File | Responsibility |
|---|---|
| `sidequest/game/forensic_fold.py` *(create)* | **Pure** fold: `fold_state_deltas(events) -> FoldResult`. No DB, no I/O. |
| `sidequest/game/forensic_query.py` *(create)* | DB assembly over a `SqliteStore`: `list_saves`, `build_timeline`, `build_turn_bundle`. Mirrors the existing `query_encounter_events(store)` precedent. |
| `sidequest/server/forensics.py` *(create)* | `forensics_router`: `GET /forensics` → `FileResponse(static/forensics.html)`. Exact sibling of `dashboard.py`. |
| `sidequest/server/static/forensics.html` *(create)* | Self-contained page (HTML+CSS+JS). |
| `sidequest/server/app.py` *(modify ~line 27, ~line 294)* | Import + `include_router(forensics_router)` next to `dashboard_router`. |
| `sidequest/server/rest.py` *(modify, inside `create_rest_router()` near `/api/debug/state` at line 251)* | Three new read-only endpoints. |
| `tests/game/test_forensic_fold.py` *(create)* | Pure fold unit tests. |
| `tests/game/test_forensic_query.py` *(create)* | DB-assembly tests over a real sqlite save fixture. |
| `tests/server/test_forensics_routes.py` *(create)* | Endpoint + mandatory wiring tests via `TestClient`. |

**Confirmed facts (verified against source 2026-05-18) — the plan depends on these:**

- Event log primitive: `from sidequest.game.event_log import EventLog, EventRow`. `EventLog(store).read_since(since_seq=0)` returns `list[EventRow]`; `EventRow(seq:int, kind:str, payload_json:str, created_at:str)`.
- `from sidequest.game.persistence import SqliteStore`. `SqliteStore.open(path:str)` → store; `.close()`; `.connection()` → live `sqlite3.Connection` (row_factory is `sqlite3.Row`).
- `from sidequest.game.session import NarrativeEntry` — pydantic model with fields `timestamp:int, round:int, author:str, content:str, tags:list`. Write via `store.append_narrative(entry)`.
- Event payloads are `payload_model.model_dump_json(exclude={"seq"})` of the message variant. `ProtocolBase.model_config = {"populate_by_name": True, "extra": "forbid"}` — **no alias generator**, so `state_delta` serializes as the literal key `"state_delta"` at the **top level** of the payload dict.
- `StateDelta` (`protocol/models.py:205`) closed field set, all optional: `location`, `characters`, `quests`, `items_gained`, `encounter_id`, `party_formation`, `magic_state`. It is carried (field name `state_delta`) inside `NARRATION` / `NARRATION_END` / `TURN_STATUS` payloads. The fold is **kind-agnostic**: any event whose payload has a non-null `state_delta` contributes (future-proof; do not hardcode kinds).
- Save path: `<save_dir>/games/<slug>/save.db`. `session_meta` columns: `id, genre_slug, world_slug, created_at, last_played, schema_version`. `narrative_log`: `id, round_number, author, content, tags, created_at`. `events`: `seq, kind, payload_json, created_at`. `projection_cache`: `event_seq, player_id, include, payload_json`. `scrapbook_entries`: `id, turn_id, scene_title, scene_type, location, image_url, narrative_excerpt, world_facts, npcs_present, render_status, created_at`.
- Test app: `from sidequest.server.app import create_app`; `create_app(genre_pack_search_paths=[packs_dir], save_dir=saves_dir)`; wrap in `fastapi.testclient.TestClient`.
- `dashboard.py` pattern to copy verbatim (only names change): `APIRouter()`, `@router.get(<path>, include_in_schema=False)`, `files("sidequest.server").joinpath("static/<file>")`, `as_file`, `return FileResponse(path, media_type="text/html")`.

---

## Task 1: Spike — confirm seq↔round join + state_delta serialization

No production code. Output: a short **Spike Findings** note appended to the bottom of this plan file and committed, so later tasks reference a fact, not a guess.

**Files:** none (investigation only).

- [ ] **Step 1: Confirm the serialized `state_delta` key**

Run from `sidequest-server/`:
```bash
uv run python -c "
import json
from sidequest.protocol.messages import NarrationEndPayload
from sidequest.protocol.models import StateDelta
p = NarrationEndPayload(state_delta=StateDelta(location='Cave'))
print(json.loads(p.model_dump_json(exclude={'seq'})))
"
```
Expected: a dict containing top-level key `"state_delta"` with `{"location": "Cave", ...}`. Record the exact key in the findings note. (If — contrary to verification — it is `stateDelta`, record that; Task 2 uses the recorded constant.)

- [ ] **Step 2: Confirm `events` has no round column; choose the join**

Run:
```bash
uv run python -c "
import sqlite3, glob, os
db = sorted(glob.glob(os.path.expanduser('~/.sidequest/saves/games/*/save.db')), key=os.path.getmtime)[-1]
c = sqlite3.connect(db); c.row_factory = sqlite3.Row
print('events cols:', [r[1] for r in c.execute('PRAGMA table_info(events)')])
print('sample events:', [dict(r) for r in c.execute('SELECT seq,kind,created_at FROM events ORDER BY seq LIMIT 3')])
print('sample narrative:', [dict(r) for r in c.execute('SELECT round_number,author,created_at FROM narrative_log ORDER BY id LIMIT 3')])
"
```
Expected: `events` columns are `seq, kind, payload_json, created_at` — **no `round` column**. Confirm both `events.created_at` and `narrative_log.created_at` are ISO-8601 strings.

- [ ] **Step 3: Lock the join strategy**

Default join (use this unless Step 2 reveals a round-bearing column or a `round` key inside `narrative_log` rows that also appears in event payloads): **timestamp bucketing** — round `r`'s event seq-range is every event whose `created_at` is `>=` the min `narrative_log.created_at` of round `r` and `<` the min `narrative_log.created_at` of the next round (the last round's upper bound is `+∞`). Events before the first narrative row attach to the first round.

- [ ] **Step 4: Write findings + commit**

Append a `## Spike Findings (Task 1)` section to this plan file: the exact `state_delta` key, confirmation of no round column, and the locked join strategy. Then:
```bash
git -C sidequest-server add -A
git -C ../oq-1 add docs/superpowers/plans/2026-05-18-save-forensics-page.md
git -C ../oq-1 commit -m "docs(plan): save-forensics spike findings"
```
(The plan lives in the orchestrator repo on `main`; commit it there. No server code changed in this task.)

---

## Task 2: `forensic_fold` — types + empty/no-delta fold

**Files:**
- Create: `sidequest/game/forensic_fold.py`
- Test: `tests/game/test_forensic_fold.py`

- [ ] **Step 1: Write the failing test**

`tests/game/test_forensic_fold.py`:
```python
import json

from sidequest.game.event_log import EventRow
from sidequest.game.forensic_fold import FoldResult, fold_state_deltas


def _ev(seq: int, payload: dict, kind: str = "NARRATION") -> EventRow:
    return EventRow(seq=seq, kind=kind, payload_json=json.dumps(payload), created_at="t")


def test_empty_event_list_yields_empty_result():
    result = fold_state_deltas([])
    assert result == FoldResult(derived={}, unparseable_seqs=())


def test_events_without_state_delta_contribute_nothing():
    events = [
        _ev(1, {"type": "NARRATION", "text": "hello"}),
        _ev(2, {"type": "NARRATION", "state_delta": None}),
    ]
    result = fold_state_deltas(events)
    assert result.derived == {}
    assert result.unparseable_seqs == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_forensic_fold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.forensic_fold'`.

- [ ] **Step 3: Write minimal implementation**

`sidequest/game/forensic_fold.py`:
```python
"""Pure fold of the trusted event log into derived StateDelta fields.

Read-only forensic reconstruction. No DB, no I/O, no fabrication: a field
appears in ``FoldResult.derived`` only if some event explicitly carried it.
Mirrors the catch-up fold a reconnecting peer already trusts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sidequest.game.event_log import EventRow

logger = logging.getLogger(__name__)

# Closed StateDelta field set (protocol/models.py:205). Kind-agnostic:
# any event whose payload carries a non-null ``state_delta`` contributes.
STATE_DELTA_FIELDS: tuple[str, ...] = (
    "location",
    "characters",
    "quests",
    "items_gained",
    "encounter_id",
    "party_formation",
    "magic_state",
)


@dataclass(frozen=True)
class DerivedField:
    """One reconstructed StateDelta field and its provenance."""

    value: object
    source_seqs: tuple[int, ...]


@dataclass(frozen=True)
class FoldResult:
    """Outcome of folding an ordered event slice."""

    derived: dict[str, DerivedField] = field(default_factory=dict)
    unparseable_seqs: tuple[int, ...] = ()


def fold_state_deltas(events: list[EventRow]) -> FoldResult:
    """Fold events (any order) into derived StateDelta fields.

    Events are sorted by ``seq`` internally. A payload that fails JSON
    parsing is skipped *loudly* (logged + recorded in
    ``unparseable_seqs``), never silently dropped.
    """
    derived: dict[str, DerivedField] = {}
    unparseable: list[int] = []
    for ev in sorted(events, key=lambda e: e.seq):
        try:
            payload = json.loads(ev.payload_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("forensic_fold.unparseable_payload seq=%s", ev.seq)
            unparseable.append(ev.seq)
            continue
        if not isinstance(payload, dict):
            continue
        sd = payload.get("state_delta")
        if not isinstance(sd, dict):
            continue
        for fname in STATE_DELTA_FIELDS:
            fval = sd.get(fname)
            if fval is None:
                continue
            prev = derived.get(fname)
            seqs = (*prev.source_seqs, ev.seq) if prev else (ev.seq,)
            derived[fname] = DerivedField(value=fval, source_seqs=seqs)
    return FoldResult(derived=derived, unparseable_seqs=tuple(unparseable))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_forensic_fold.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/forensic_fold.py tests/game/test_forensic_fold.py
git -C sidequest-server commit -m "feat(forensic): pure StateDelta fold — types + empty/no-delta path"
```

---

## Task 3: `forensic_fold` — accumulate fields with source-seq provenance

**Files:**
- Modify: `tests/game/test_forensic_fold.py` (add tests)
- (No production change expected — Task 2's implementation already covers this; these tests pin the contract.)

- [ ] **Step 1: Write the failing tests**

Append to `tests/game/test_forensic_fold.py`:
```python
def test_last_write_wins_with_ordered_provenance():
    events = [
        _ev(5, {"type": "NARRATION", "state_delta": {"location": "Cave"}}),
        _ev(2, {"type": "NARRATION", "state_delta": {"location": "Gate"}}),
        _ev(9, {"type": "TURN_STATUS", "state_delta": {"location": "Hall"}}),
    ]
    result = fold_state_deltas(events)
    loc = result.derived["location"]
    assert loc.value == "Hall"  # highest seq wins (sorted internally)
    assert loc.source_seqs == (2, 5, 9)  # every contributing seq, in order


def test_independent_fields_tracked_separately():
    events = [
        _ev(1, {"type": "NARRATION", "state_delta": {"location": "Cave"}}),
        _ev(2, {"type": "NARRATION", "state_delta": {"quests": {"q1": "open"}}}),
    ]
    result = fold_state_deltas(events)
    assert result.derived["location"].source_seqs == (1,)
    assert result.derived["quests"].value == {"q1": "open"}
    assert result.derived["quests"].source_seqs == (2,)
    assert "characters" not in result.derived  # absent, not fabricated
```

- [ ] **Step 2: Run tests to verify they pass (contract pinned)**

Run: `uv run pytest tests/game/test_forensic_fold.py -v`
Expected: PASS (4 passed). If any fail, fix `forensic_fold.py` minimally until green — do not weaken the assertions.

- [ ] **Step 3: Commit**

```bash
git -C sidequest-server add tests/game/test_forensic_fold.py
git -C sidequest-server commit -m "test(forensic): pin last-write-wins + per-field provenance"
```

---

## Task 4: `forensic_fold` — unparseable payload skipped loudly

**Files:**
- Modify: `tests/game/test_forensic_fold.py` (add test)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_forensic_fold.py`:
```python
def test_unparseable_payload_is_recorded_and_logged_not_silently_dropped(caplog):
    bad = EventRow(seq=7, kind="NARRATION", payload_json="{not json", created_at="t")
    good = _ev(8, {"type": "NARRATION", "state_delta": {"location": "Cave"}})
    with caplog.at_level("WARNING"):
        result = fold_state_deltas([bad, good])
    assert result.unparseable_seqs == (7,)
    assert result.derived["location"].value == "Cave"  # good event still folds
    assert "forensic_fold.unparseable_payload seq=7" in caplog.text
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/game/test_forensic_fold.py::test_unparseable_payload_is_recorded_and_logged_not_silently_dropped -v`
Expected: PASS. (Implementation from Task 2 already handles this; if it fails, fix minimally.)

- [ ] **Step 3: Commit**

```bash
git -C sidequest-server add tests/game/test_forensic_fold.py
git -C sidequest-server commit -m "test(forensic): unparseable event skipped loudly, not dropped"
```

---

## Task 5: `forensic_query.list_saves` — enumerate saves + meta

**Files:**
- Create: `sidequest/game/forensic_query.py`
- Test: `tests/game/test_forensic_query.py`

- [ ] **Step 1: Write the failing test**

`tests/game/test_forensic_query.py`:
```python
import json
from pathlib import Path

from sidequest.game.event_log import EventLog
from sidequest.game.forensic_query import list_saves
from sidequest.game.persistence import SqliteStore
from sidequest.game.session import NarrativeEntry


def _make_save(saves_dir: Path, slug: str, *, genre: str, world: str) -> SqliteStore:
    db = saves_dir / "games" / slug / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore.open(str(db))
    conn = store.connection()
    conn.execute(
        "INSERT OR REPLACE INTO session_meta "
        "(id, genre_slug, world_slug, created_at, last_played, schema_version) "
        "VALUES (1, ?, ?, ?, ?, 1)",
        (genre, world, "2026-05-18T00:00:00+00:00", "2026-05-18T00:05:00+00:00"),
    )
    conn.commit()
    return store


def test_list_saves_returns_meta_for_each_save(tmp_path):
    saves = tmp_path / "saves"
    s = _make_save(saves, "caverns_and_claudes_test", genre="caverns_and_claudes", world="test")
    s.close()
    result = list_saves(saves)
    assert len(result) == 1
    row = result[0]
    assert row["slug"] == "caverns_and_claudes_test"
    assert row["genre"] == "caverns_and_claudes"
    assert row["world"] == "test"
    assert "last_activity_ts" in row


def test_list_saves_skips_broken_db_loudly(tmp_path, caplog):
    saves = tmp_path / "saves"
    s = _make_save(saves, "good_save", genre="g", world="w")
    s.close()
    broken = saves / "games" / "broken_save" / "save.db"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("this is not sqlite")
    with caplog.at_level("WARNING"):
        result = list_saves(saves)
    slugs = {r["slug"] for r in result}
    assert slugs == {"good_save"}
    assert "broken_save" in caplog.text


def test_list_saves_missing_root_returns_empty(tmp_path):
    assert list_saves(tmp_path / "nope") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.forensic_query'`.

- [ ] **Step 3: Write minimal implementation**

`sidequest/game/forensic_query.py`:
```python
"""Read-only DB assembly for the save-forensics page.

Mirrors the module-level ``query_encounter_events(store)`` precedent:
plain functions over an open ``SqliteStore``. Never writes, never
checkpoints (respects the WAL/save-clobber hazard).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sidequest.game.persistence import SqliteStore

logger = logging.getLogger(__name__)


def list_saves(save_dir: Path) -> list[dict]:
    """Enumerate ``<save_dir>/games/<slug>/save.db`` files.

    Broken/meta-less DBs are skipped *loudly* (logged WARNING), never
    silently. Sorted newest-first by save-file mtime.
    """
    games_root = Path(save_dir) / "games"
    out: list[dict] = []
    if not games_root.exists():
        return out
    for slug_dir in sorted(games_root.iterdir()):
        if not slug_dir.is_dir():
            continue
        db_file = slug_dir / "save.db"
        if not db_file.is_file():
            continue
        try:
            store = SqliteStore.open(str(db_file))
        except Exception as exc:  # noqa: BLE001 — best-effort enumeration
            logger.warning("forensic_query.open_failed slug=%s err=%s", slug_dir.name, exc)
            continue
        try:
            row = store.connection().execute(
                "SELECT genre_slug, world_slug, created_at, last_played "
                "FROM session_meta WHERE id = 1"
            ).fetchone()
        except Exception as exc:  # noqa: BLE001
            logger.warning("forensic_query.meta_failed slug=%s err=%s", slug_dir.name, exc)
            store.close()
            continue
        store.close()
        if row is None:
            logger.warning("forensic_query.no_meta slug=%s", slug_dir.name)
            continue
        out.append(
            {
                "slug": slug_dir.name,
                "genre": row["genre_slug"],
                "world": row["world_slug"],
                "created_at": row["created_at"],
                "last_played": row["last_played"],
                "last_activity_ts": int(db_file.stat().st_mtime * 1000),
            }
        )
    out.sort(key=lambda r: r["last_activity_ts"], reverse=True)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/forensic_query.py tests/game/test_forensic_query.py
git -C sidequest-server commit -m "feat(forensic): list_saves — enumerate saves + meta, skip broken loudly"
```

---

## Task 6: `forensic_query.build_timeline` — round-keyed turns

**Files:**
- Modify: `sidequest/game/forensic_query.py` (add `build_timeline`)
- Modify: `tests/game/test_forensic_query.py` (add tests + a narrative/event helper)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_forensic_query.py`:
```python
def _seed_rounds(store):
    """Round 1: 2 events + 1 narrative. Round 2: 1 event + 1 narrative."""
    log = EventLog(store)
    store.connection().execute(
        "INSERT INTO narrative_log (round_number, author, content, tags, created_at) "
        "VALUES (1, 'narrator', 'You enter the cave.', '[]', '2026-05-18T00:01:00+00:00')"
    )
    store.connection().commit()
    store.connection().execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES "
        "('NARRATION', ?, '2026-05-18T00:01:01+00:00')",
        (json.dumps({"type": "NARRATION", "state_delta": {"location": "Cave"}}),),
    )
    store.connection().execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES "
        "('TURN_STATUS', ?, '2026-05-18T00:01:02+00:00')",
        (json.dumps({"type": "TURN_STATUS", "state_delta": None}),),
    )
    store.connection().execute(
        "INSERT INTO narrative_log (round_number, author, content, tags, created_at) "
        "VALUES (2, 'narrator', 'A goblin lunges.', '[]', '2026-05-18T00:02:00+00:00')"
    )
    store.connection().execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES "
        "('NARRATION', ?, '2026-05-18T00:02:01+00:00')",
        (json.dumps({"type": "NARRATION", "state_delta": {"location": "Hall"}}),),
    )
    store.connection().commit()


def test_build_timeline_buckets_events_by_round(tmp_path):
    from sidequest.game.forensic_query import build_timeline

    saves = tmp_path / "saves"
    store = _make_save(saves, "tl_test", genre="g", world="w")
    _seed_rounds(store)
    timeline = build_timeline(store)
    store.close()

    assert [t["round"] for t in timeline] == [1, 2]
    r1, r2 = timeline
    assert r1["seq_start"] == 1 and r1["seq_end"] == 2
    assert r1["event_kind_counts"] == {"NARRATION": 1, "TURN_STATUS": 1}
    assert r1["narrative_authors"] == ["narrator"]
    assert r2["seq_start"] == 3 and r2["seq_end"] == 3
    assert r2["event_kind_counts"] == {"NARRATION": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py::test_build_timeline_buckets_events_by_round -v`
Expected: FAIL — `ImportError: cannot import name 'build_timeline'`.

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest/game/forensic_query.py`:
```python
def _round_boundaries(conn) -> list[tuple[int, str]]:
    """Ordered (round_number, min_created_at) for each round in narrative_log."""
    rows = conn.execute(
        "SELECT round_number, MIN(created_at) AS first_ts "
        "FROM narrative_log GROUP BY round_number ORDER BY round_number"
    ).fetchall()
    return [(r["round_number"], r["first_ts"]) for r in rows]


def _events_for_round(conn, lo_ts: str, hi_ts: str | None, *, first_round: bool):
    """Events whose created_at is in [lo_ts, hi_ts). First round also
    sweeps any events that predate the first narrative row."""
    if first_round and hi_ts is not None:
        sql = "SELECT seq, kind, created_at FROM events WHERE created_at < ? ORDER BY seq"
        return conn.execute(sql, (hi_ts,)).fetchall()
    if first_round and hi_ts is None:
        return conn.execute("SELECT seq, kind, created_at FROM events ORDER BY seq").fetchall()
    if hi_ts is None:
        sql = "SELECT seq, kind, created_at FROM events WHERE created_at >= ? ORDER BY seq"
        return conn.execute(sql, (lo_ts,)).fetchall()
    sql = (
        "SELECT seq, kind, created_at FROM events "
        "WHERE created_at >= ? AND created_at < ? ORDER BY seq"
    )
    return conn.execute(sql, (lo_ts, hi_ts)).fetchall()


def build_timeline(store: SqliteStore) -> list[dict]:
    """One entry per narrative round, with its event seq-range + summary.

    Join strategy: timestamp bucketing (Spike Findings, Task 1) — events
    lack a round column.
    """
    conn = store.connection()
    bounds = _round_boundaries(conn)
    timeline: list[dict] = []
    for idx, (rnd, lo_ts) in enumerate(bounds):
        hi_ts = bounds[idx + 1][1] if idx + 1 < len(bounds) else None
        evs = _events_for_round(conn, lo_ts, hi_ts, first_round=(idx == 0))
        kind_counts: dict[str, int] = {}
        for e in evs:
            kind_counts[e["kind"]] = kind_counts.get(e["kind"], 0) + 1
        authors = [
            r["author"]
            for r in conn.execute(
                "SELECT DISTINCT author FROM narrative_log "
                "WHERE round_number = ? ORDER BY author",
                (rnd,),
            ).fetchall()
        ]
        timeline.append(
            {
                "round": rnd,
                "seq_start": evs[0]["seq"] if evs else None,
                "seq_end": evs[-1]["seq"] if evs else None,
                "event_kind_counts": kind_counts,
                "narrative_authors": authors,
                "ts": lo_ts,
            }
        )
    return timeline
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py -v`
Expected: PASS (4 passed total in file).

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/forensic_query.py tests/game/test_forensic_query.py
git -C sidequest-server commit -m "feat(forensic): build_timeline — round-keyed turns via timestamp bucketing"
```

---

## Task 7: `forensic_query.build_turn_bundle` — drill-down for one round

**Files:**
- Modify: `sidequest/game/forensic_query.py` (add `build_turn_bundle`)
- Modify: `tests/game/test_forensic_query.py` (add test)

- [ ] **Step 1: Write the failing test**

Append to `tests/game/test_forensic_query.py`:
```python
def test_build_turn_bundle_assembles_all_panels(tmp_path):
    from sidequest.game.forensic_query import build_turn_bundle

    saves = tmp_path / "saves"
    store = _make_save(saves, "bundle_test", genre="g", world="w")
    _seed_rounds(store)
    # projection row for the round-1 NARRATION event (seq 1)
    store.connection().execute(
        "INSERT INTO projection_cache (event_seq, player_id, include, payload_json) "
        "VALUES (1, 'player1', 1, ?)",
        (json.dumps({"type": "NARRATION", "text": "You enter the cave."}),),
    )
    store.connection().execute(
        "INSERT INTO scrapbook_entries "
        "(turn_id, scene_title, scene_type, location, image_url, narrative_excerpt, "
        " world_facts, npcs_present, render_status) "
        "VALUES (1, 'The Cave Mouth', 'exploration', 'Cave', NULL, 'You enter.', "
        " '[]', '[]', 'rendered')"
    )
    store.connection().commit()

    bundle = build_turn_bundle(store, 1)
    store.close()

    assert bundle["round"] == 1
    assert [n["content"] for n in bundle["narrative"]] == ["You enter the cave."]
    assert [e["seq"] for e in bundle["events"]] == [1, 2]
    assert bundle["events"][0]["kind"] == "NARRATION"
    # derived through this turn: location set by seq 1
    assert bundle["derived"]["location"]["value"] == "Cave"
    assert bundle["derived"]["location"]["source_seqs"] == [1]
    assert bundle["unparseable_seqs"] == []
    # per-player projection lens
    assert bundle["projection"][0]["player_id"] == "player1"
    assert bundle["projection"][0]["include"] == 1
    # scrapbook
    assert bundle["scrapbook"][0]["scene_title"] == "The Cave Mouth"


def test_build_turn_bundle_unknown_round_is_empty_not_error(tmp_path):
    from sidequest.game.forensic_query import build_turn_bundle

    saves = tmp_path / "saves"
    store = _make_save(saves, "empty_round", genre="g", world="w")
    _seed_rounds(store)
    bundle = build_turn_bundle(store, 999)
    store.close()
    assert bundle["round"] == 999
    assert bundle["narrative"] == []
    assert bundle["events"] == []
    assert bundle["derived"] == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py::test_build_turn_bundle_assembles_all_panels -v`
Expected: FAIL — `ImportError: cannot import name 'build_turn_bundle'`.

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest/game/forensic_query.py`:
```python
from sidequest.game.event_log import EventRow
from sidequest.game.forensic_fold import fold_state_deltas


def _timeline_entry(store: SqliteStore, round_number: int) -> dict | None:
    for entry in build_timeline(store):
        if entry["round"] == round_number:
            return entry
    return None


def build_turn_bundle(store: SqliteStore, round_number: int) -> dict:
    """Assemble every drill-down panel for one round.

    Truth tiers stay separate: ``narrative``/``events``/``projection``/
    ``scrapbook`` are verbatim DB rows; ``derived`` is the fold of every
    event up to and including this round's last seq, badged by the UI.
    Unknown round → empty bundle (lossy/best-effort, mirrors
    ``/api/debug/state``), never a raised error.
    """
    conn = store.connection()
    entry = _timeline_entry(store, round_number)

    narrative = [
        {"round": r["round_number"], "author": r["author"],
         "content": r["content"], "tags": json.loads(r["tags"] or "[]"),
         "created_at": r["created_at"]}
        for r in conn.execute(
            "SELECT round_number, author, content, tags, created_at "
            "FROM narrative_log WHERE round_number = ? ORDER BY id",
            (round_number,),
        ).fetchall()
    ]

    if entry is None or entry["seq_start"] is None:
        return {"round": round_number, "narrative": narrative, "events": [],
                "derived": {}, "projection": [], "scrapbook": [],
                "unparseable_seqs": []}

    seq_start, seq_end = entry["seq_start"], entry["seq_end"]
    raw_events = conn.execute(
        "SELECT seq, kind, payload_json, created_at FROM events "
        "WHERE seq >= ? AND seq <= ? ORDER BY seq",
        (seq_start, seq_end),
    ).fetchall()
    events = [
        {"seq": e["seq"], "kind": e["kind"],
         "payload": _safe_json(e["payload_json"]), "created_at": e["created_at"]}
        for e in raw_events
    ]

    # Derived state THROUGH this turn = fold every event with seq <= seq_end.
    fold_rows = conn.execute(
        "SELECT seq, kind, payload_json, created_at FROM events "
        "WHERE seq <= ? ORDER BY seq",
        (seq_end,),
    ).fetchall()
    fold = fold_state_deltas(
        [EventRow(seq=r["seq"], kind=r["kind"],
                  payload_json=r["payload_json"], created_at=r["created_at"])
         for r in fold_rows]
    )
    derived = {
        k: {"value": v.value, "source_seqs": list(v.source_seqs)}
        for k, v in fold.derived.items()
    }

    projection = [
        {"event_seq": p["event_seq"], "player_id": p["player_id"],
         "include": p["include"], "payload": _safe_json(p["payload_json"])}
        for p in conn.execute(
            "SELECT event_seq, player_id, include, payload_json "
            "FROM projection_cache WHERE event_seq >= ? AND event_seq <= ? "
            "ORDER BY event_seq, player_id",
            (seq_start, seq_end),
        ).fetchall()
    ]

    scrapbook = [
        {"scene_title": s["scene_title"], "scene_type": s["scene_type"],
         "location": s["location"], "image_url": s["image_url"],
         "narrative_excerpt": s["narrative_excerpt"],
         "world_facts": json.loads(s["world_facts"] or "[]"),
         "npcs_present": json.loads(s["npcs_present"] or "[]"),
         "render_status": s["render_status"]}
        for s in conn.execute(
            "SELECT scene_title, scene_type, location, image_url, "
            "narrative_excerpt, world_facts, npcs_present, render_status "
            "FROM scrapbook_entries WHERE turn_id = ? ORDER BY id",
            (round_number,),
        ).fetchall()
    ]

    return {"round": round_number, "narrative": narrative, "events": events,
            "derived": derived, "projection": projection,
            "scrapbook": scrapbook,
            "unparseable_seqs": list(fold.unparseable_seqs)}


def _safe_json(raw: str | None):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"__unparseable__": raw}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py -v`
Expected: PASS (6 passed total).

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/forensic_query.py tests/game/test_forensic_query.py
git -C sidequest-server commit -m "feat(forensic): build_turn_bundle — all five drill-down panels"
```

---

## Task 8: REST endpoints in `create_rest_router()`

**Files:**
- Modify: `sidequest/server/rest.py` (add 3 routes inside `create_rest_router()`, next to `/api/debug/state` ~line 251; add imports near the existing imports at top)
- Test: `tests/server/test_forensics_routes.py`

- [ ] **Step 1: Write the failing test**

`tests/server/test_forensics_routes.py`:
```python
import json
from pathlib import Path

from fastapi.testclient import TestClient

from sidequest.game.persistence import SqliteStore
from sidequest.server.app import create_app


def _client(tmp_path: Path) -> TestClient:
    packs = tmp_path / "genre_packs"
    packs.mkdir(parents=True, exist_ok=True)
    saves = tmp_path / "saves"
    saves.mkdir(parents=True, exist_ok=True)
    app = create_app(genre_pack_search_paths=[packs], save_dir=saves)
    return TestClient(app)


def _seed(saves: Path, slug: str):
    db = saves / "games" / slug / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore.open(str(db))
    c = store.connection()
    c.execute(
        "INSERT OR REPLACE INTO session_meta "
        "(id, genre_slug, world_slug, created_at, last_played, schema_version) "
        "VALUES (1, 'caverns_and_claudes', 'test', "
        "'2026-05-18T00:00:00+00:00', '2026-05-18T00:05:00+00:00', 1)"
    )
    c.execute(
        "INSERT INTO narrative_log (round_number, author, content, tags, created_at) "
        "VALUES (1, 'narrator', 'You enter.', '[]', '2026-05-18T00:01:00+00:00')"
    )
    c.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES "
        "('NARRATION', ?, '2026-05-18T00:01:01+00:00')",
        (json.dumps({"type": "NARRATION", "state_delta": {"location": "Cave"}}),),
    )
    c.commit()
    store.close()


def test_list_saves_endpoint(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir(parents=True, exist_ok=True)
    _seed(saves, "caverns_and_claudes_test")
    client = _client(tmp_path)
    resp = client.get("/api/debug/saves")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["slug"] == "caverns_and_claudes_test"
    assert body[0]["genre"] == "caverns_and_claudes"


def test_timeline_endpoint(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir(parents=True, exist_ok=True)
    _seed(saves, "caverns_and_claudes_test")
    client = _client(tmp_path)
    resp = client.get("/api/debug/save/caverns_and_claudes_test/timeline")
    assert resp.status_code == 200
    assert resp.json()[0]["round"] == 1


def test_turn_bundle_endpoint(tmp_path):
    saves = tmp_path / "saves"
    saves.mkdir(parents=True, exist_ok=True)
    _seed(saves, "caverns_and_claudes_test")
    client = _client(tmp_path)
    resp = client.get("/api/debug/save/caverns_and_claudes_test/turn/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["round"] == 1
    assert body["derived"]["location"]["value"] == "Cave"


def test_turn_bundle_unknown_slug_is_empty_not_500(tmp_path):
    client = _client(tmp_path)
    resp = client.get("/api/debug/save/nope/turn/1")
    assert resp.status_code == 200
    assert resp.json() == {"round": 1, "narrative": [], "events": [],
                           "derived": {}, "projection": [], "scrapbook": [],
                           "unparseable_seqs": []}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_forensics_routes.py -v`
Expected: FAIL — 404s (routes not registered).

- [ ] **Step 3: Add imports near the top of `rest.py`**

In `sidequest/server/rest.py`, with the other `from sidequest...` imports at the top of the file, add:
```python
from sidequest.game.forensic_query import build_timeline, build_turn_bundle, list_saves
from sidequest.game.persistence import SqliteStore
```
(If `SqliteStore` is already imported there, do not duplicate it.)

- [ ] **Step 4: Add the three routes inside `create_rest_router()`**

Immediately after the `debug_state` handler (the `@router.get("/api/debug/state")` block, ~line 251), add:
```python
    @router.get("/api/debug/saves")
    async def debug_saves(request: Request) -> list[dict[str, Any]]:
        """List local saves for the forensics page. Read-only, lossy."""
        return list_saves(request.app.state.save_dir)

    def _open_save(request: Request, slug: str) -> SqliteStore | None:
        db = Path(request.app.state.save_dir) / "games" / slug / "save.db"
        if not db.is_file():
            return None
        try:
            return SqliteStore.open(str(db))
        except Exception:  # noqa: BLE001 — lossy/best-effort, mirrors debug_state
            return None

    @router.get("/api/debug/save/{slug}/timeline")
    async def debug_save_timeline(request: Request, slug: str) -> list[dict[str, Any]]:
        """Round-keyed turn timeline for one save. Empty list if absent."""
        store = _open_save(request, slug)
        if store is None:
            return []
        try:
            return build_timeline(store)
        finally:
            store.close()

    @router.get("/api/debug/save/{slug}/turn/{round_number}")
    async def debug_save_turn(
        request: Request, slug: str, round_number: int
    ) -> dict[str, Any]:
        """Drill-down bundle for one round. Empty bundle if save absent."""
        store = _open_save(request, slug)
        if store is None:
            return {"round": round_number, "narrative": [], "events": [],
                    "derived": {}, "projection": [], "scrapbook": [],
                    "unparseable_seqs": []}
        try:
            return build_turn_bundle(store, round_number)
        finally:
            store.close()
```
Confirm `Path` and `Any` are already imported at the top of `rest.py` (they are used by `debug_state`); if not, add `from pathlib import Path` and `from typing import Any`.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/server/test_forensics_routes.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git -C sidequest-server add sidequest/server/rest.py tests/server/test_forensics_routes.py
git -C sidequest-server commit -m "feat(forensic): /api/debug/saves + timeline + turn endpoints"
```

---

## Task 9: `/forensics` route + app wiring (mandatory wiring test)

**Files:**
- Create: `sidequest/server/forensics.py`
- Modify: `sidequest/server/app.py` (~line 27 import, ~line 294 include)
- Create (empty placeholder so `FileResponse` resolves in the wiring test): `sidequest/server/static/forensics.html` — replaced for real in Task 10
- Modify: `tests/server/test_forensics_routes.py` (add wiring test)

- [ ] **Step 1: Write the failing wiring test**

Append to `tests/server/test_forensics_routes.py`:
```python
def test_forensics_route_is_wired_and_serves_html(tmp_path):
    """Mandatory wiring test: proves app.py registered the router and the
    static asset resolves — not merely that the module imports."""
    client = _client(tmp_path)
    resp = client.get("/forensics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Save Forensics" in resp.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Create a minimal static file so the route resolves**

`sidequest/server/static/forensics.html`:
```html
<!DOCTYPE html><html><head><title>Save Forensics</title></head>
<body><h1>Save Forensics</h1></body></html>
```

- [ ] **Step 4: Create `sidequest/server/forensics.py`**

```python
"""HTTP route that serves the Save Forensics page.

Read-only post-mortem counterpart to the live OTEL dashboard. A single
self-contained HTML file under ``sidequest/server/static/``; it fetches
the ``/api/debug/save*`` JSON endpoints on the same origin. No WebSocket.
Exact sibling of ``dashboard.py``.
"""

from __future__ import annotations

from importlib.resources import as_file, files

from fastapi import APIRouter
from fastapi.responses import FileResponse

forensics_router = APIRouter()


@forensics_router.get("/forensics", include_in_schema=False)
async def forensics() -> FileResponse:
    """Return the forensics page HTML."""
    asset = files("sidequest.server").joinpath("static/forensics.html")
    with as_file(asset) as path:
        return FileResponse(path, media_type="text/html")
```

- [ ] **Step 5: Wire it into `app.py`**

In `sidequest/server/app.py`, next to the existing dashboard import (~line 27):
```python
from sidequest.server.forensics import forensics_router
```
And next to `app.include_router(dashboard_router)` (~line 294):
```python
    app.include_router(forensics_router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/server/test_forensics_routes.py -v`
Expected: PASS (5 passed).

- [ ] **Step 7: Commit**

```bash
git -C sidequest-server add sidequest/server/forensics.py sidequest/server/app.py sidequest/server/static/forensics.html tests/server/test_forensics_routes.py
git -C sidequest-server commit -m "feat(forensic): /forensics route wired into app (wiring test)"
```

---

## Task 10: The forensics page UI

**Files:**
- Modify (replace placeholder with the real page): `sidequest/server/static/forensics.html`
- Modify: `tests/server/test_forensics_routes.py` (tighten the served-content assertion)

- [ ] **Step 1: Replace `sidequest/server/static/forensics.html` with the full page**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Save Forensics — SideQuest</title>
<style>
  :root { --bg:#0e1116; --panel:#161b22; --line:#2b313a; --txt:#d6deeb;
          --stored:#3fb950; --derived:#d29922; --absent:#6e7681; --acc:#58a6ff; }
  * { box-sizing:border-box; }
  body { margin:0; font:13px/1.5 ui-monospace,Menlo,monospace; background:var(--bg); color:var(--txt); }
  header { padding:10px 16px; border-bottom:1px solid var(--line); display:flex; gap:16px; align-items:center; }
  header h1 { font-size:15px; margin:0; }
  .legend span { margin-right:14px; }
  .dot { display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:5px; vertical-align:middle; }
  .layout { display:flex; height:calc(100vh - 47px); }
  aside { width:280px; border-right:1px solid var(--line); overflow:auto; }
  aside .save, .turn { padding:8px 12px; border-bottom:1px solid var(--line); cursor:pointer; }
  aside .save:hover, .turn:hover { background:#1c2230; }
  aside .save.sel, .turn.sel { background:#1f6feb33; border-left:3px solid var(--acc); }
  main { flex:1; overflow:auto; padding:16px; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:6px; margin-bottom:14px; }
  .panel h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; margin:0;
              padding:8px 12px; border-bottom:1px solid var(--line); color:#9aa7b8; }
  .panel .body { padding:10px 12px; }
  pre { white-space:pre-wrap; word-break:break-word; margin:4px 0; }
  .tier-stored { color:var(--stored); }
  .tier-derived { color:var(--derived); }
  .tier-absent  { color:var(--absent); font-style:italic; }
  .badge { font-size:10px; padding:1px 6px; border-radius:8px; border:1px solid currentColor; margin-left:6px; }
  table { width:100%; border-collapse:collapse; }
  td,th { border-bottom:1px solid var(--line); padding:4px 6px; text-align:left; vertical-align:top; }
  .muted { color:var(--absent); }
  .seqs { color:var(--absent); font-size:11px; }
  .warn { color:#f85149; }
</style>
</head>
<body>
<header>
  <h1>Save Forensics</h1>
  <span class="muted">read-only post-mortem · sibling of the OTEL dashboard</span>
  <span class="legend" style="margin-left:auto">
    <span><i class="dot" style="background:var(--stored)"></i>stored</span>
    <span><i class="dot" style="background:var(--derived)"></i>derived</span>
    <span><i class="dot" style="background:var(--absent)"></i>absent</span>
  </span>
</header>
<div class="layout">
  <aside id="rail"><div class="save muted" style="padding:12px">Loading saves…</div></aside>
  <main id="main"><p class="muted">Pick a save on the left.</p></main>
</div>
<script>
const rail = document.getElementById('rail');
const main = document.getElementById('main');
let curSlug = null;

const esc = s => String(s == null ? '' : s).replace(/[&<>]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const j = o => esc(JSON.stringify(o, null, 2));

async function getJSON(u){ const r = await fetch(u); if(!r.ok) throw new Error(u+' '+r.status); return r.json(); }

async function loadSaves(){
  let saves;
  try { saves = await getJSON('/api/debug/saves'); }
  catch(e){ rail.innerHTML = '<div class="save warn">'+esc(e.message)+'</div>'; return; }
  if(!saves.length){ rail.innerHTML = '<div class="save muted">No saves found.</div>'; return; }
  rail.innerHTML = '';
  for(const s of saves){
    const d = document.createElement('div');
    d.className = 'save'; d.dataset.slug = s.slug;
    d.innerHTML = '<b>'+esc(s.slug)+'</b><br><span class="muted">'+
      esc(s.genre)+' / '+esc(s.world)+'</span>';
    d.onclick = () => selectSave(s.slug, d);
    rail.appendChild(d);
  }
}

async function selectSave(slug, el){
  curSlug = slug;
  document.querySelectorAll('.save').forEach(n => n.classList.remove('sel'));
  el.classList.add('sel');
  main.innerHTML = '<p class="muted">Loading timeline…</p>';
  const tl = await getJSON('/api/debug/save/'+encodeURIComponent(slug)+'/timeline');
  if(!tl.length){ main.innerHTML = '<p class="muted">No narrative rounds in this save.</p>'; return; }
  main.innerHTML = '<div class="panel"><h2>Timeline — '+esc(slug)+
    '</h2><div class="body" id="tl"></div></div><div id="drill"></div>';
  const tlBox = document.getElementById('tl');
  for(const t of tl){
    const kinds = Object.entries(t.event_kind_counts||{})
      .map(([k,n]) => k+'×'+n).join(' ');
    const r = document.createElement('div');
    r.className = 'turn';
    r.innerHTML = '<b>Round '+t.round+'</b> <span class="seqs">seq '+
      (t.seq_start??'–')+'–'+(t.seq_end??'–')+'</span><br>'+
      '<span class="muted">'+esc(kinds||'no events')+'</span>';
    r.onclick = () => selectTurn(t.round, r);
    tlBox.appendChild(r);
  }
}

async function selectTurn(round, el){
  document.querySelectorAll('.turn').forEach(n => n.classList.remove('sel'));
  el.classList.add('sel');
  const drill = document.getElementById('drill');
  drill.innerHTML = '<p class="muted">Loading round '+round+'…</p>';
  const b = await getJSON('/api/debug/save/'+encodeURIComponent(curSlug)+
    '/turn/'+round);
  let snap = null;
  try { snap = await getJSON('/api/debug/state?session_key='+
    encodeURIComponent(curSlug)); } catch(e){ snap = {error:e.message}; }

  const narr = b.narrative.map(n =>
    '<pre class="tier-stored"><b>'+esc(n.author)+':</b> '+esc(n.content)+'</pre>')
    .join('') || '<span class="tier-absent">— no narrative this round</span>';

  const evs = b.events.map(e =>
    '<pre class="tier-stored">#'+e.seq+' '+esc(e.kind)+'\n'+j(e.payload)+'</pre>')
    .join('') || '<span class="tier-absent">— no events this round</span>';

  let der = Object.entries(b.derived).map(([k,v]) =>
    '<tr><td class="tier-derived">'+esc(k)+
    '<span class="badge tier-derived">derived</span></td>'+
    '<td><pre class="tier-derived">'+j(v.value)+'</pre></td>'+
    '<td class="seqs">seq '+(v.source_seqs||[]).join(', ')+'</td></tr>').join('');
  if(!der) der = '<tr><td colspan="3" class="tier-absent">'+
    '— no event carried any state through this turn</td></tr>';
  const unp = (b.unparseable_seqs||[]).length
    ? '<p class="warn">⚠ unparseable event seqs: '+
      b.unparseable_seqs.join(', ')+'</p>' : '';

  const proj = b.projection.map(p =>
    '<tr><td>'+p.event_seq+'</td><td>'+esc(p.player_id)+'</td>'+
    '<td class="'+(p.include?'tier-stored':'tier-absent')+'">'+
    (p.include?'shown':'hidden')+'</td>'+
    '<td><pre>'+j(p.payload)+'</pre></td></tr>').join('') ||
    '<tr><td colspan="4" class="tier-absent">— no projection rows</td></tr>';

  const scrap = b.scrapbook.map(s =>
    '<pre class="tier-stored"><b>'+esc(s.scene_title)+'</b> ('+
    esc(s.scene_type)+' @ '+esc(s.location)+') ['+esc(s.render_status)+
    ']\n'+esc(s.narrative_excerpt)+'</pre>').join('') ||
    '<span class="tier-absent">— no scrapbook entry</span>';

  drill.innerHTML =
    '<div class="panel"><h2>Narrative · Round '+round+'</h2><div class="body">'+narr+'</div></div>'+
    '<div class="panel"><h2>Event stream (verbatim)</h2><div class="body">'+evs+'</div></div>'+
    '<div class="panel"><h2>Derived state — NOT a stored snapshot</h2><div class="body">'+
      unp+'<table><tr><th>field</th><th>value</th><th>provenance</th></tr>'+der+'</table></div></div>'+
    '<div class="panel"><h2>Per-player projection lens</h2><div class="body">'+
      '<table><tr><th>seq</th><th>player</th><th>visibility</th><th>projected payload</th></tr>'+
      proj+'</table></div></div>'+
    '<div class="panel"><h2>Scrapbook</h2><div class="body">'+scrap+'</div></div>'+
    '<div class="panel"><h2>Final stored snapshot (the ONLY absolute state)</h2>'+
      '<div class="body"><pre class="tier-stored">'+j(snap)+'</pre></div></div>';
}

loadSaves();
</script>
</body>
</html>
```

- [ ] **Step 2: Tighten the served-content assertion**

In `tests/server/test_forensics_routes.py`, in `test_forensics_route_is_wired_and_serves_html`, replace the last assertion with:
```python
    assert "Save Forensics" in resp.text
    assert "/api/debug/saves" in resp.text  # the page actually calls the API
    assert "NOT a stored snapshot" in resp.text  # honesty contract visible
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run pytest tests/server/test_forensics_routes.py -v`
Expected: PASS (5 passed).

- [ ] **Step 4: Manual smoke (operator-gated, optional but recommended)**

From the orchestrator root: `just server`, then open `http://localhost:8765/forensics`. Confirm: saves list populates; clicking a save shows the timeline; clicking a round shows all five panels + final snapshot; derived fields are amber-badged; absent fields read "— no event…" (never `0`/`null`).

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/server/static/forensics.html tests/server/test_forensics_routes.py
git -C sidequest-server commit -m "feat(forensic): forensics page UI — timeline + 5 panels, truth-tiered"
```

---

## Task 11: Full gate + lint + finalize

**Files:** none (verification only).

- [ ] **Step 1: Lint + format**

Run: `git -C sidequest-server status` to confirm cwd repo, then from `sidequest-server/`:
`uv run ruff check . && uv run ruff format --check .`
Expected: clean. If `ruff format --check` flags the new files, run `uv run ruff format .` and re-commit with `style(forensic): ruff format`.

- [ ] **Step 2: Full server suite via testing-runner subagent**

Dispatch the `testing-runner` subagent — `REPOS: server`, `CONTEXT: save-forensics feature complete`, `RUN_ID: forensic-final`. Expected: full suite passes, 0 failures (the prior baseline was 6124 passed / 430 skipped / 0 failed — the new tests add to passed, regress nothing).

- [ ] **Step 3: Confirm wiring end-to-end**

Verify the new code has non-test consumers: `grep -n forensics_router sidequest/server/app.py` (must show import + `include_router`); `grep -n "forensic_query" sidequest/server/rest.py` (must show the import + 3 routes). This satisfies the "verify wiring, not just existence" rule.

- [ ] **Step 4: Push the branch**

```bash
git -C sidequest-server push -u origin feat/save-forensics-page
```
Do not open the PR here — hand back per the executing skill (Reviewer/SM owns merge).

---

## Self-Review (completed by plan author)

**1. Spec coverage**

| Spec section | Task(s) |
|---|---|
| §4 placement — `/forensics` route mirroring `dashboard.py`, separate page | Task 9 |
| §5 `/api/debug/saves` · `/timeline` · `/turn/{round}` | Task 8 |
| §5 pure `forensic_fold` on `EventLog.read_since` | Tasks 2–4 (fold takes the read rows; query layer feeds them) |
| §5 `forensic_query` sibling of `query_encounter_events` | Tasks 5–7 |
| §5 read-only, never checkpoint | Tasks 5,7 (open/close, no writes) + Task 8 (`finally: close`) |
| §6 honesty contract — stored/derived/absent never blended | Task 7 (separate keys) + Task 10 (CSS tiers, "— no event…", amber badge) |
| §6 malformed payload skipped loudly | Task 4 (fold) + `_safe_json` Task 7 + UI warn Task 10 |
| §7 timeline spine + 5 drill-down panels + final snapshot | Tasks 6,7,10 |
| §7.4 per-player projection lens | Task 7 (`projection`) + Task 10 (lens table) |
| §9 R1 seq↔round spike-first | Task 1 |
| §10 fold unit tests / endpoint tests / mandatory wiring test | Tasks 2–4 / 8 / 9 |
| §10 OTEL — none needed (read-only) | by omission, intentional |

No spec requirement is unmapped.

**2. Placeholder scan:** No "TBD/TODO/handle edge cases" — every code step is complete. Task 9's intentionally-minimal HTML is explicitly replaced in Task 10 (called out, not a hidden placeholder).

**3. Type consistency:** `FoldResult{derived: dict[str,DerivedField], unparseable_seqs: tuple[int,...]}` and `DerivedField{value, source_seqs}` defined Task 2, consumed unchanged Tasks 3,4,7. `build_turn_bundle` JSON keys (`round, narrative, events, derived, projection, scrapbook, unparseable_seqs`) identical across Task 7 impl, Task 8 unknown-slug fallback, and Task 9/10 UI. `EventRow(seq,kind,payload_json,created_at)` used consistently. Endpoint paths identical between Task 8 routes and Task 10 `fetch` calls.
