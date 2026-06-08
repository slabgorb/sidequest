# SQLite Write-Race Fix — Design

**Date:** 2026-05-24
**Status:** Draft (Architect — Leonard of Quirm)
**Source incident:** [Sunday Playgroup Post-Mortem 2026-05-24](../playtest-reports/2026-05-24-sunday-playgroup-post-mortem.md), Bomb #3
**Scope:** `sidequest-server` only. No content, UI, or daemon changes.

---

## 1. Problem

The save-DB `sqlite3.Connection` is opened with `check_same_thread=False` and shared across every thread that writes the save file: narrator workers, the renderer, the C2 event-append path, the watcher telemetry sink, snapshot save, narrative log appends, scrapbook writes, world-save writes, and several lobby helpers. The docstring at `persistence.py:340-345` promises that *"per-write serialization is enforced at the watcher layer with a module-level lock"*, but only **two** of the **fourteen** writer sites actually acquire that lock.

The consequence:

1. **`sqlite3.OperationalError: database is locked`** every MP turn — the watcher tries to insert telemetry through the shared connection while another writer (typically `SqliteStore.save()` or the C2 event-append) is mid-transaction. Wrapped in `try/except` (`watcher_hub.py:404-411`) and silently swallowed by design, so the GM panel goes blind without anyone noticing.
2. **Cross-purpose transaction sharing**: when the telemetry path observes `conn.in_transaction=True`, it rides whatever transaction is open — sometimes that's the C2 event frame (intentional, FK-bearing), sometimes it's a snapshot save (accidental, semantically wrong). Telemetry rows can land in transactions that weren't meant to carry them.
3. **`busy_timeout=5000` does not help.** The `busy_timeout` PRAGMA addresses inter-connection contention against the WAL. The bug is **intra-connection** — two threads contending on the same `sqlite3.Connection`'s statement state. Same-day playtests on 2026-05-18 and 2026-05-24 show the same symptom both times despite the timeout being in place.

The full inventory of write sites and their lock status as of 2026-05-24 is in §4.

---

## 2. Goal

Restore the doctrine the docstring already promises:

> Every write through `SqliteStore._conn` is serialized by a single process-wide mutex.

With one constraint: the **`turn_telemetry → events` FK with `ON DELETE CASCADE` is load-bearing** and must be preserved. `_persist_turn_telemetry`'s "ride the open turn transaction" branch (`watcher_hub.py:396-400`) is the mechanism that gives telemetry rows their event-frame atomicity, and the FK constraint enforces it. Any fix that breaks the same-transaction coupling between an event-frame and the telemetry rows referencing it is rejected.

Non-goals:

- **Not** switching storage backend (Postgres / LMDB / DuckDB). Considered; rejected for this fix — costs are described in §7.
- **Not** redesigning the telemetry data model.
- **Not** fixing Bomb #1 (stuck MP rounds) — separate story.
- **Not** fixing Bomb #4 (lobby session sprawl) — separate story.
- **Not** wiring `SIDEQUEST_OTLP_ENDPOINT` — separate story.

---

## 3. Design

### 3.1 The lock

A single process-wide reentrant mutex named **`SAVE_WRITE_LOCK`**, defined at module scope in `sidequest/game/persistence.py`:

```python
import threading

# All writes through any SqliteStore._conn must be made inside
#     with SAVE_WRITE_LOCK:
#         with conn:           # SQLite transaction
#             ...
# The acquire order is mandatory: SAVE_WRITE_LOCK outside the
# transaction, never the reverse. See §3.2 below for rationale.
#
# The lock is reentrant (RLock) because the C2 event-append
# transaction (server/emitters.py:_emit_event_frame) calls
# emit_mechanical_census() inside its open transaction, which
# publishes events that re-enter _persist_turn_telemetry. Without
# reentrancy, that re-entry would deadlock.
SAVE_WRITE_LOCK: threading.RLock = threading.RLock()
```

The existing `_persist_lock` in `watcher_hub.py` is removed; `watcher_hub.py` imports `SAVE_WRITE_LOCK` from `sidequest.game.persistence` and uses it in place of `_persist_lock`.

### 3.2 Acquire order — lock outside transaction

Mandatory pattern:

```python
with SAVE_WRITE_LOCK:
    with conn:                                # SQLite implicit txn
        conn.execute("INSERT INTO …")
        conn.execute("UPDATE …")
```

**Why this order**: if the transaction is opened first and the lock acquired second, two threads can both call `conn.__enter__` (opening a transaction on the shared connection) and then race for the lock. Whichever thread acquires the lock holds an open transaction — but the connection's per-statement state has already been corrupted by the loser's interleaved `BEGIN`. SQLite returns "database is locked" in this scenario. Acquiring the lock first means a thread cannot open a transaction unless it owns the right to write at all.

### 3.3 Reentrancy — why `RLock` not `Lock`

Site #10 (the C2 event-append in `server/emitters.py:_emit_event_frame`, around lines 267-310) opens a transaction and then calls `emit_mechanical_census(...)` inside that transaction by design — the census event rows ride the same FK-coupled transaction as the canonical `NARRATION` event-frame row. `emit_mechanical_census` calls `publish_event(...)` which fires `_persist_turn_telemetry` — which acquires the lock. If the lock is non-reentrant, the same thread blocks forever waiting for itself.

With `threading.RLock`, the same thread can re-enter the lock as many times as needed; the lock is released when the outermost `__exit__` runs, which is when the C2 transaction commits.

### 3.4 All writer sites acquire the lock

Every write site enumerated in §4 wraps its existing `with conn:` block (or, for the few sites without an explicit transaction wrapper, wraps its `conn.execute(...)` + `conn.commit()` sequence) in `with SAVE_WRITE_LOCK:`. Init paths (`_init_schema`, the post-init ALTER TABLE migration) get the lock too, even though they run once at construction — a uniform "every write holds the lock" rule is easier to enforce and audit than "every write except the init paths".

The two sites that already acquire `_persist_lock` in `watcher_hub.py` (`_maybe_persist_encounter_row` and `_persist_turn_telemetry`) are updated to acquire `SAVE_WRITE_LOCK` instead. No behavior change beyond the rename.

### 3.5 Documentation discipline

A block comment in `persistence.py` immediately above `SAVE_WRITE_LOCK` documents:

1. The mandatory acquire order (lock outside conn).
2. The reentrancy requirement (why RLock).
3. The list of consumer modules (`persistence.py`, `server/emitters.py`, `telemetry/watcher_hub.py`) — so a future writer that lands in a fourth module is forced to read this comment when adding their import.
4. A sentence directing the reader to the regression test in §5 as the authoritative example.

The class docstring on `SqliteStore` also gets a one-line addendum: *"All writes through `self._conn` must hold `SAVE_WRITE_LOCK` from `sidequest.game.persistence` — see the lock's module-level docstring."*

No runtime assertion is added. The regression test in §5 is the enforcement.

---

## 4. Writer-site inventory

The full list of save-DB write sites as of 2026-05-24, ranked by call frequency. The "Today" column is whether the site currently acquires `_persist_lock`. The "After" column is whether the site acquires `SAVE_WRITE_LOCK` in the fix.

| # | Site | Frequency | Today | After |
|---|------|-----------|-------|-------|
| 1 | `SqliteStore._init_schema` (`persistence.py:354`) | once at open | ✗ | ✓ |
| 2 | `SqliteStore.__init__` migration ALTER (`persistence.py:371`) | once at open | ✗ | ✓ |
| 3 | `SqliteStore.reinitialize_slot` (`persistence.py:400`) | rare | ✗ | ✓ |
| 4 | **`SqliteStore.save`** (`persistence.py:439`) | every turn | ✗ | ✓ |
| 5 | `SqliteStore.save_world_save` (`persistence.py:605`) | session start / world transitions | ✗ | ✓ |
| 6 | **`SqliteStore.append_narrative`** (`persistence.py:617`) | every turn | ✗ | ✓ |
| 7 | `SqliteStore.upsert_location_promotion` (`persistence.py:716`) | per promotion | ✗ | ✓ |
| 8 | **`emitters.insert_scrapbook_entry`** (`server/emitters.py:49`) | every turn | ✗ | ✓ |
| 9 | `emitters.update_scrapbook_image_url` (`server/emitters.py:100`) | per image render | ✗ | ✓ |
| 10 | **C2 event-append + projection cache** (`server/emitters.py` `_emit_event_frame` C2 block, around line 267) | every emit | ✗ | ✓ (RLock reentry by `mechanical_census` inside) |
| 11 | `persistence.ensure_game` (`persistence.py:810`) | once per session | ✗ | ✓ |
| 12 | `persistence.set_claude_session_id` (`persistence.py:836`) | rare | ✗ | ✓ |
| 13 | `watcher_hub._maybe_persist_encounter_row` (`telemetry/watcher_hub.py:328`) | per encounter event | ✓ (`_persist_lock`) | ✓ (renamed) |
| 14 | `watcher_hub._persist_turn_telemetry` (`telemetry/watcher_hub.py:395`) | per watcher emit | ✓ (`_persist_lock`) | ✓ (renamed) |

**Not in scope** (separate DB, separate connection): `dungeon/persistence.py` is a different SQLite file with its own connection. If the dungeon DB ever cross-talks to the save DB through a shared write path, that's a separate fix. As of 2026-05-24 it does not.

---

## 5. Regression test

Location: `sidequest-server/tests/server/test_save_write_lock.py`

The test fires concurrent writes from N=8 threads against an in-memory `SqliteStore`, simulating one playtest's worth of activity:

- Thread group A (`N=2`): repeatedly calls `store.save(synthetic_snapshot)` — the snapshot-save path.
- Thread group B (`N=2`): repeatedly calls `store.append_narrative(synthetic_entry)` — the narrative-log append.
- Thread group C (`N=2`): repeatedly calls `emit_event_frame(...)` with synthetic `NARRATION` payloads, which drives the C2 event-append + `mechanical_census` + telemetry path (the reentry case).
- Thread group D (`N=2`): repeatedly calls `publish_event(component="mechanical", event_type="census", fields=...)` directly — the telemetry-only path.

Run for **100 turns × N players** (≈ 500 iterations across all threads). Assertions:

1. Zero `turn_telemetry.sink_failed` warnings (captured via `caplog`).
2. Zero `sqlite3.OperationalError` exceptions raised from any thread (collected by each worker into a shared list).
3. The final row count in `turn_telemetry` equals the expected count (publish_events × 1 telemetry row each — minus zero, because no events were dropped).
4. The FK from `turn_telemetry.event_seq` → `events.seq` is intact: every non-NULL `event_seq` matches a real `events.seq`.

The test is the enforcement mechanism for future writers — anyone adding a 15th write site without acquiring the lock will see it fail.

A weaker companion test (single-threaded smoke) verifies the rename in `watcher_hub.py` — that `_maybe_persist_encounter_row` and `_persist_turn_telemetry` still work after `_persist_lock` → `SAVE_WRITE_LOCK`.

---

## 6. Migration notes

### Old saves on disk

No save-file schema change. The on-disk format is unchanged. Old saves load and re-save identically.

### Process restart in the middle of a transaction

Unchanged from today. SQLite WAL durability means an uncommitted transaction rolls back on connection close; both before and after this fix, a crash mid-`save()` discards the partial write. The lock affects only in-process serialization, not durability.

### Behavior under load

Lock-hold duration is bounded by the slowest write — `SqliteStore.save()` serializes a full `GameSnapshot` to JSON before the `INSERT`, which is the dominant cost (often a few MB on a long session). The serialization happens *outside* the lock (it runs against the in-memory `snapshot` object), so the lock-hold itself is sub-100ms in practice. With ≤1 write/second across all writers during normal play, contention is negligible.

The one site whose hold-time grows is #10, the C2 event-append: it holds the lock across `append_in_transaction` + `emit_mechanical_census` + the broadcast fanout's projection writes. That's still sub-100ms today; if profiling later shows it becoming a bottleneck, the fanout's broadcast (the WebSocket sends) can be hoisted out of the lock without losing correctness, because broadcast doesn't touch the DB.

---

## 7. Alternatives considered (rejected)

### (ii) Two connections — telemetry on its own `sqlite3.Connection`

Would have eliminated single-connection state contention by giving telemetry its own write path. **Rejected** because the `turn_telemetry.event_seq → events.seq` FK with `ON DELETE CASCADE` requires both writes to live in the same transaction. Splitting connections breaks the atomicity — telemetry rows could persist with FK references to a rolled-back event frame, which would fail the FK constraint at commit and re-introduce the symptom we're fixing.

### (iii) Telemetry off the save DB entirely

Would have moved `turn_telemetry` into a separate DB file (or an in-memory ring buffer flushed asynchronously). **Rejected** for the same FK reason as (ii), plus a data-model redesign cost: `event_seq` becomes a soft reference instead of an enforced FK, and the existing GM-panel queries that JOIN telemetry against events would have to be rewritten as application-layer joins across two stores.

### (iv) Switch to Postgres

Would have eliminated the single-writer model entirely. **Rejected** because:

1. The save-file model (one self-contained `.db` per session, durable forever, hand-copyable) is load-bearing for the user's playstyle and is documented in `.pennyfarthing/guides/save-management.md`. Postgres rows in shared tables break the backup story.
2. Operational complexity grows substantially: daemon to install and keep running, schema migrations, networking, `pg_dump` in the backup story.
3. The actual bug is small — 14 write sites, 12 missing a lock, one mutex away from fixed. Replacing the storage engine to dodge a 50-line fix is disproportionate.
4. Postgres does not fix Bomb #1 (stuck MP rounds) or Bomb #4 (session sprawl), which are application-layer bugs.

The conversation about whether SideQuest ever needs Postgres remains open — primarily relevant if/when the game is hosted online and the per-machine save-file model has to die anyway. That's a separate decision, not this one.

---

## 8. Out of scope

The post-mortem identifies five additional concerns. None are in scope here:

- **Bomb #1**: stuck MP rounds (barrier denominator drift) — separate story; recommend adding `barrier.denominator_drift` and `barrier.submitted_set_reset` watcher tripwires.
- **Bomb #2 verification**: re-run a recorded SP/MP session to confirm IntentRouter is healthy post-#410 — depends on Bomb #3 being fixed first (otherwise telemetry that would prove router health gets eaten).
- **Bomb #4**: MP lobby session sprawl — separate story.
- **OTLP dormant**: `SIDEQUEST_OTLP_ENDPOINT` unset in `just up` — small env-var addition, separate story.
- **`turn_manager._submitted` undocumented MP fragility** — comment + tripwire watcher event, separate story.

---

## 9. Implementation outline

To be expanded into a TDD plan by the writing-plans skill. High-level checklist:

1. Define `SAVE_WRITE_LOCK` as `threading.RLock()` in `sidequest/game/persistence.py` at module scope, with the doc block.
2. Add the addendum to `SqliteStore`'s class docstring.
3. Wrap sites #1, #2, #3, #4, #5, #6, #7, #11, #12 (all in `persistence.py`) with `with SAVE_WRITE_LOCK:` outside the existing `with self._conn:` block.
4. Wrap sites #8, #9 in `server/emitters.py`.
5. Wrap site #10 (the C2 event-append) outermost — `with SAVE_WRITE_LOCK:` outside the existing `with conn:` block.
6. Remove `_persist_lock` from `telemetry/watcher_hub.py`; import `SAVE_WRITE_LOCK` from `sidequest.game.persistence`; replace both occurrences.
7. Add `tests/server/test_save_write_lock.py` per §5.
8. Add the smoke test for the watcher_hub rename.
9. Run `uv run pytest -v` — full suite. Pass.
10. Run `uv run ruff check . && uv run pyright`. Pass.
11. Manual smoke: `just server` + `just client` + one SP turn + grep server log for `turn_telemetry.sink_failed` (expect zero).

---

## 10. Risks

- **Performance regression** if any single writer is slower than expected. Profile during the smoke test; the contention is bounded to one writer at a time, but the slowest writer sets the floor for everyone else's wait. If `SqliteStore.save()` turns out to be slow under MP load (5+ characters, big inventories, lots of NPCs), the snapshot-serialize-then-INSERT pattern may need to be revisited. Out of scope for *this* fix — flagged for follow-up if observed.
- **Missed write site.** The §4 inventory is from a grep + manual code-walk on 2026-05-24. If a future writer is added without acquiring the lock, the regression test in §5 catches it under concurrent load. The doc block in `persistence.py` is the human-readable enforcement.
- **The reentry guarantee depends on the C2 path staying single-threaded per session.** If a future refactor makes C2 fan out across threads, the `RLock` no longer protects re-entry across those threads. As of 2026-05-24 the C2 path is single-threaded per `event_log` and there is no plan to change that.
