# Forensics Telemetry Phase 2 — Mechanical-State Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Photograph every seated PC's canonical mechanical state once per round — emitted inside the existing C2 turn transaction so Phase 1's unchanged sink persists it atomically — and surface it in `/forensics` as a per-round per-PC mechanical **diff** plus a macro-strip mechanical lane, so a narration-vs-mechanics discrepancy is visually obvious to the GM.

**Architecture:** A new pure projection module (`mechanical_census.py`) turns canonical game-model objects into plain dicts. A new emitter call site **inside `emitters.emit_event`'s `with conn:` block, gated to the canonical `kind=="NARRATION"` emit**, loops the seated roster and calls the existing `publish_event(..., component="mechanical")` — so Phase 1's `_persist_turn_telemetry` sink (UNCHANGED) writes each as a `turn_telemetry` row, atomic with the turn. A new pure `fold_mechanical_census` (mirroring `fold_turn_telemetry`) diffs each PC's round-N census against that PC's previous-census-round. A new collapsed `<details>` lane + a net-new macro-strip lane render it. **Nothing in Phase 1 is modified** — the fold module is appended to, the read path gains a parallel `mechanical` key, the emitter is net-new instrumentation (exactly the "new emitter" the Phase 2 spec scopes).

**Tech Stack:** Python 3 / `sqlite3` (stdlib, no ORM), pytest + `caplog`, FastAPI route already in place, zero-JS static `forensics.html`.

**Owning repo / branch:** all implementation in `sidequest-server/`, on branch `feat/forensics-telemetry-phase2` cut from `develop` **before any implementer is dispatched** (gitflow; subrepo branches are independent of the orchestrator). This plan doc lives in the orchestrator repo (`docs/superpowers/plans/`, targets `main`), mirroring the Phase 1 plan's placement. Paths below are repo-relative to `sidequest-server/`.

**Project test-execution note:** under the Pennyfarthing TDD workflow, tests run via the `testing-runner` subagent, **not** invoked directly (CLAUDE.md). Each step's `Run:` line is the test contract (selector + expected result) the `testing-runner` targets, not a literal shell instruction for the implementer.

---

## Spec Reconciliation (READ FIRST — divergences from the design spec, confirmed from source 2026-05-18)

The Phase 2 design spec (`docs/superpowers/specs/2026-05-18-forensics-telemetry-phase2-mechanical-coverage-design.md`) explicitly delegated the emission point and the canonical accessors to "the plan's first two tasks to confirm from source," and every census-schema row carried "(plan confirms exact accessor)." That confirmation was done during plan authoring (three source audits, production call sites, not log-absence). It surfaced facts that **change the spec's literal schema and architecture wording**. Each is locked here so the spec-check and spec-reconcile Architect can audit every divergence from the session file alone.

| # | Spec said | Source truth | Resolution |
|---|-----------|--------------|------------|
| **R1** | "end-of-round (state settled, INSIDE the open C2 turn transaction) └─ for each SEATED pc" — implying a hook in the turn-resolution pipeline. | The C2 write txn is **local to `emitters.emit_event`**: opens `emitters.py:276` (`with conn:`), first DML `:277` (`append_in_transaction` → `events` INSERT), commits at block-exit `:388`. There is **no point in `websocket_session_handler._execute_narration_turn` where state is settled AND the txn is open** — by the NARRATION emit the txn is opened *by* that emit and closed immediately after. | Emit the per-PC census loop **inside `emit_event`'s `with conn:` block, gated `kind == "NARRATION" and event_log is not None`**, after the `events` INSERT (`:277`) and before block-exit (`:388`). State is settled upstream (xp/edge/trope/snapshot persisted in the `persistence` phase before the NARRATION emit, `websocket_session_handler.py:3005-3036`); `conn.in_transaction` is True there so the sink rides the C2 txn (`event_seq = MAX(seq)`). Same *intent* as the spec (settled + in-txn), concrete location. **This is the load-bearing constraint.** |
| **R2** | Census keyed on `round`; schema `round`. | Codebase keys per-turn telemetry on `snapshot.turn_manager.interaction` (`turn.py:60`); `turn_manager.round` is the display counter and **historically froze** while `interaction` ticked (ADR-051; Felix Playtest 3: round=65 vs max=72). The Phase-1 sink only persists `fields["round"]` when it is an `int` (`watcher_hub.py:372-374`). | Emitter puts `snapshot.turn_manager.interaction` into `fields["round"]` (so Phase-1's `round` column is populated and the read path's `round`-column bucket works) AND carries it as `fields["interaction"]` for label honesty. The forensics lane labels it "round" for the GM (it is the per-turn counter they see). |
| **R3** | Vitals = "`edge` (cur/max), `composure` (cur/max)". | ADR-078 collapsed HP **and** composure into ONE `EdgePool` (`creature_core.py:46`). There is no separate Composure pool. Emitting both double-counts the same number. | Census emits **one** `edge: {current, max, base_max}` (`character.core.edge.*`), `down: bool` (`character.is_broken()`, `character.py:169`), and `statuses: [{text, severity}]` (`character.core.statuses`, `status.py:45`). No `composure` field. |
| **R4** | Progression = "`xp_total`, `tier`/`level`, `pending_advancements`, unlocked-ability flags". | Actual fields: `core.xp` (int, default 0), `core.level` (int, default 1), `core.acquired_advancements` (list[str], P2-deferred, usually `[]`), `character.abilities` (list). **No `xp_total`, no `tier`, no `pending_advancements` field exists.** | Census emits `xp` (`core.xp`), `level` (`core.level`), `acquired_advancements` (`core.acquired_advancements`), `ability_count` (`len(character.abilities)`). No fabricated `tier`/`pending_advancements` (No-Stubbing: do not synthesize fields the model lacks). |
| **R5** | Trope = per-PC "`active tropes + progress/activation counters`"; tension tracked. | `snapshot.active_tropes` (`session.py:569`, `TropeState` `:409-414`) is **session/party-level — no PC key**. `TensionTracker` is a non-persisted runtime object, **not on `GameSnapshot`** (unreachable from any save read). | Per-PC trope is structurally impossible. Emit **one session-level trope census per round** (`event_type="trope_census"`, `component="mechanical"`), payload = `active_tropes` digest + `turns_since_meaningful` + `total_beats_fired`. Tension is **excluded** (not in the save — No-Silent-Fallback: do not fabricate it). |
| **R6** | Location = "`location_id` + label, room-graph `node`, party `formation`/`adjacency`". | Per-PC location is `snapshot.character_locations.get(core.name)` (`session.py:709`) — a free-text string that *also* carries the room-graph node id (seeded by `init_room_graph_location`). There is **no live per-PC room-graph node accessor and no party-formation/adjacency model anywhere**. | Census emits `location` (the `character_locations` string) and `chassis_room` (`character.current_room`, `character.py:126`, may be `None`). **No `formation`/`adjacency`** (not modeled — No-Stubbing). |
| **R7** | Inventory = "digest `[{item, qty}]` + stable `inv_hash`". | `character.core.inventory.items` is `list[dict]` (`creature_core.py:195`); narrator-added items arrive as `quantity:1` singletons and dedupe is incomplete (`narration_apply.py:2044-2054`) — per-entry `quantity` is **unreliable**; duplicates appear as repeated entries. | Digest must **aggregate by `name`**, summing `entry.get("quantity", 1)`. A tested pure helper `inventory_digest()` owns this fold; `inv_hash` is a stable hash of the sorted aggregated digest. (Spec shape preserved; computation corrected.) |
| **R8** | "macro-strip mechanical lane — the strip row the Phase 1 spec explicitly reserved for Phase 2." | **No reserved strip row exists in code.** The only forward-looking comment (`forensics.html:125-127`) reserves a *cumulative-KnownFacts curve* (P1.1), not a mechanical lane. The strip is a fixed single-row, one-rect-per-round renderer (`:128-158`). | The macro-strip mechanical lane is **net-new layout** (a second rect row), modeled on the existing rect loop — not a placeholder fill. Budgeted as its own task (Task 9). |
| **R9** | "No seat index" assumption implicit. | No `seat` integer attribute exists; seating is dict-insertion order in `SessionRoom._seated` (runtime, not persisted, not stable across reconnect). | `seat` is a **best-effort positional index** from `room.playing_player_ids()`; `player_id` is the durable key the fold diffs on. Documented limitation, not a bug. |

**Non-goals preserved unchanged from the spec:** no narration-text parsing, no automated accusation/badging, no deterministic tripwires, no event-sourcing of mutations, no backfill, **no Phase 1 code changed** (sink, `turn_telemetry` schema, transaction logic untouched). Dice/confrontation already covered — untouched.

**Pre-flight (one-time, before Task 1):**

```bash
cd sidequest-server
git fetch origin
git switch develop && git pull --ff-only
git switch -c feat/forensics-telemetry-phase2
```

---

## The load-bearing invariant (correctness rests on this)

In this codebase `sqlite3` connections use default *deferred* isolation (`_configure_connection` sets WAL + `foreign_keys`, never `isolation_level=None`). The C2 turn write transaction has a **lifetime local to `emitters.emit_event`**: it opens at the `with conn:` (`emitters.py:276`), its first DML is the `events` INSERT via `append_in_transaction` (`emitters.py:277` → `event_log.py:59`, which does NOT commit — caller owns the txn), and it commits at the `with conn:` block exit (`emitters.py:388`; no explicit `.commit()` inside). Therefore, **inside that block, after line 277 and before line 388, `conn.in_transaction` is `True`**, and a `publish_event(...)` issued there reaches Phase 1's sink (`watcher_hub.py:338`) with `in_transaction == True` (`watcher_hub.py:381`), which attributes `event_seq = MAX(seq) FROM events` (= this turn's just-inserted NARRATION row) and rides the C2 txn — committing or rolling back atomically with `events`. `conn` here is `store._conn` where `store = handler._event_log.store`, the **same** connection object Phase 1's sink reads (`_event_store._conn`, bound at `connect.py:271-273`). Task 1 pins this as an executable regression guard before anything is built on it. If it does not hold, the whole approach is unsound — escalate, do not proceed.

---

## File Structure

| File | Responsibility | Change |
|------|----------------|--------|
| `sidequest/game/mechanical_census.py` | NEW pure module: `inventory_digest`, `inv_hash`, `seat_index`, `build_pc_census`, `build_trope_census`, `emit_mechanical_census`. Pure projections of canonical model → plain dicts; the emit fn is the only non-pure piece (calls `publish_event`, fully wrapped). | Create |
| `sidequest/server/emitters.py` | One guarded call to `emit_mechanical_census(...)` inside `emit_event`'s `with conn:` block, after the `events` INSERT, gated `kind == "NARRATION" and event_log is not None`. | Modify (~`:279`, inside the `with conn:` opened `:276`) |
| `sidequest/game/forensic_fold.py` | Append `MechanicalRow`, `PcMechanicalDiff`, `MechanicalFold`, `fold_mechanical_census(current_rows, prior_rows)`, `fold_mechanical_strip(all_rows)`. Mirror `fold_turn_telemetry` discipline verbatim. | Modify (append after `:195`, EOF) |
| `sidequest/game/forensic_query.py` | Import `fold_mechanical_census`/`fold_mechanical_strip`; add `_empty_mechanical()`, `_mechanical_for_round()`, `mechanical_strip()`; add `"mechanical"` key to both `build_turn_bundle` return literals; add `mechanical_rows` to `list_saves`. | Modify (`:16`, `:303`, `:307`, `:384`, new helpers ~`:198-260`, `list_saves` ~`:94`) |
| `sidequest/server/rest.py` | `debug_save_turn` `empty` literal gains `"mechanical": {...}`. | Modify (`:470`) |
| `sidequest/server/static/forensics.html` | `.tier-mechanical` CSS; per-round mechanical-diff `<details>` lane after the telemetry `</details>`; net-new macro-strip mechanical row; `.lbl` mechanical count. | Modify (`:27-31`, after `:340`, `:116-121`, `:128-158`) |
| `tests/game/test_mechanical_census_contract.py` | Task 1 characterization (emission-point load-bearing invariant) | Create |
| `tests/game/test_mechanical_census.py` | Task 2 per-subsystem accuracy + Task 4 isolation | Create |
| `tests/server/test_mechanical_census_emit.py` | Task 3 emitter (in-txn, per-seated-PC, trope row) | Create |
| `tests/server/test_turn_telemetry_wiring.py` | Task 5 mandatory wiring (real turn writes `component='mechanical'`); Task 10 cost guard | Modify (append) |
| `tests/game/test_forensic_fold.py` | Task 6 `fold_mechanical_census` / `fold_mechanical_strip` pure tests | Modify (append) |
| `tests/game/test_forensic_query.py` | Task 7 read path + byte-identity; Task 9 strip data | Modify (append) |
| `tests/server/test_forensics_routes.py` | Task 7 never-500 literal sync; Task 8 lane wiring | Modify |

---

## Task 1: Pin the emission-point load-bearing invariant (characterization, test-only)

**Why first:** the spec names this the plan's first task. The investigation resolved it (R1); this task *codifies* the resolution as an executable regression guard so every later task can rely on it. No production code changes.

**Files:**
- Test: `tests/game/test_mechanical_census_contract.py` (create)

- [ ] **Step 1: Write the characterization test**

```python
# tests/game/test_mechanical_census_contract.py
"""Characterization: pins the invariant the mechanical census rests on.

R1: the C2 turn write txn is LOCAL to emitters.emit_event's `with conn:`
block. A publish_event issued inside that block (after the events INSERT,
before block exit) rides the C2 txn: in_transaction is True and the sink
attributes event_seq = MAX(seq) FROM events. If this fails, the census
cannot be made atomic with the turn — STOP and escalate.
"""
from sidequest.game.persistence import SqliteStore
from sidequest.telemetry import watcher_hub
from sidequest.telemetry.watcher_hub import bind_event_store, publish_event


def _store(tmp_path) -> SqliteStore:
    return SqliteStore.open(str(tmp_path / "save.db"))


def test_publish_inside_emit_style_block_rides_the_c2_txn(tmp_path):
    """Simulates emit_event's `with conn:` block: events INSERT first
    (append_in_transaction), THEN a component='mechanical' publish. The
    census row must (a) attribute event_seq = the in-flight events row and
    (b) roll back with the turn."""
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        conn = store._conn
        try:
            with conn:  # the emit_event C2 transaction
                conn.execute(
                    "INSERT INTO events (kind, payload_json, created_at) "
                    "VALUES ('NARRATION', '{}', 't')"
                )
                assert conn.in_transaction is True  # first DML flipped it
                publish_event(
                    "census",
                    {"player_id": "p1", "round": 4},
                    component="mechanical",
                )
                inflight = conn.execute(
                    "SELECT event_seq, round, component, event_type "
                    "FROM turn_telemetry"
                ).fetchall()
                # rides the txn: event_seq = MAX(seq) of the in-flight event
                assert inflight == [(1, 4, "mechanical", "census")]
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass
        # turn rolled back -> census rolled back atomically with it
        assert conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry"
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
    finally:
        bind_event_store(None)
        store.close()


def test_publish_outside_any_block_does_not_ride_a_turn(tmp_path):
    """Sanity foil: a mechanical publish with no open txn takes its own
    short txn and event_seq is NULL (NOT attributed to a turn). Proves the
    in-txn attribution in the test above is the meaningful signal."""
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        publish_event(
            "census", {"player_id": "p1", "round": 4}, component="mechanical"
        )
        row = store._conn.execute(
            "SELECT event_seq, round, component FROM turn_telemetry"
        ).fetchone()
        assert row == (None, 4, "mechanical")
    finally:
        bind_event_store(None)
        store.close()
```

- [ ] **Step 2: Run to verify it passes-as-characterization**

Run: `uv run pytest tests/game/test_mechanical_census_contract.py -v`
Expected: **PASS** (both). This characterizes existing Phase-1 sink behavior; nothing new is built yet. If `test_publish_inside_emit_style_block_rides_the_c2_txn` FAILS, the R1 invariant is unsound — STOP, escalate, do not proceed. If `SqliteStore` has no `.close()`, use `store._conn.close()` (verify the real teardown on `SqliteStore`).

- [ ] **Step 3: Commit**

```bash
git add tests/game/test_mechanical_census_contract.py
git commit -m "test(census): pin emission-point load-bearing invariant (C2-txn ride)"
```

---

## Task 2: Pure census-builder module — `mechanical_census.py`

**Why:** the spec's "state is read, never reconstructed" pillar and the anti-log-absence proof: each gap subsystem is read from the canonical model and asserted, in isolation, for a seeded character.

**Files:**
- Create: `sidequest/game/mechanical_census.py`
- Test: `tests/game/test_mechanical_census.py` (create)

- [ ] **Step 1: Write the failing per-subsystem accuracy tests**

```python
# tests/game/test_mechanical_census.py
"""Per-subsystem accuracy: each census field is read from the CANONICAL
game model for a seeded character (anti-log-absence — every gap closed
against real state, not a hoped-for emitter)."""
from sidequest.game.mechanical_census import (
    build_pc_census,
    build_trope_census,
    inv_hash,
    inventory_digest,
    seat_index,
)


# --- inventory_digest: aggregate by name, sum quantity, singleton-safe ---
def test_inventory_digest_aggregates_singletons_by_name():
    items = [
        {"name": "torch", "quantity": 1},
        {"name": "torch", "quantity": 1},   # narrator singleton dup (R7)
        {"name": "brass key"},               # no quantity -> 1
        {"name": "rations", "quantity": 3},
    ]
    assert inventory_digest(items) == [
        {"item": "brass key", "qty": 1},
        {"item": "rations", "qty": 3},
        {"item": "torch", "qty": 2},
    ]


def test_inventory_digest_skips_nameless_entries_loudly(caplog):
    with caplog.at_level("WARNING"):
        d = inventory_digest([{"quantity": 2}, {"name": "rope", "quantity": 1}])
    assert d == [{"item": "rope", "qty": 1}]
    assert "mechanical_census.inventory_unnamed_entry" in caplog.text


def test_inv_hash_is_stable_and_order_independent():
    a = inv_hash([{"name": "b"}, {"name": "a", "quantity": 2}])
    b = inv_hash([{"name": "a", "quantity": 2}, {"name": "b"}])
    assert a == b and isinstance(a, str) and len(a) == 16


# --- seat_index: positional in playing_player_ids, never raises (R9) ---
class _Room:
    def __init__(self, ids):
        self._ids = ids

    def playing_player_ids(self):
        return list(self._ids)


def test_seat_index_is_positional_and_defensive():
    room = _Room(["p2", "p1", "p3"])
    assert seat_index(room, "p1") == 1
    assert seat_index(room, "ghost") == -1   # absent -> -1, never raises
    assert seat_index(None, "p1") == -1      # no room -> -1, never raises


# --- build_pc_census: canonical reads (R3/R4/R6/R7) ---
class _Edge:
    current, max, base_max = 7, 12, 12


class _Inv:
    items = [{"name": "torch", "quantity": 1}, {"name": "torch", "quantity": 1}]
    gold = 9


class _Core:
    name = "Rux"
    xp = 150
    level = 3
    acquired_advancements = ["adv.iron_grip"]
    statuses = [type("S", (), {"text": "Wound: ribs", "severity": "wound"})()]
    edge = _Edge()
    inventory = _Inv()


class _Char:
    core = _Core()
    current_room = "antechamber"
    abilities = [object(), object()]

    def is_broken(self):
        return self.core.edge.current <= 0


def test_build_pc_census_reads_every_gap_subsystem():
    c = build_pc_census(
        character=_Char(),
        player_id="p1",
        character_name="Rux",
        seat=0,
        round_number=4,
        location="The Kept Fire",
    )
    assert c["player_id"] == "p1"
    assert c["character_name"] == "Rux"
    assert c["seat"] == 0
    assert c["round"] == 4
    assert c["interaction"] == 4
    assert c["location"] == "The Kept Fire"
    assert c["chassis_room"] == "antechamber"
    assert c["edge"] == {"current": 7, "max": 12, "base_max": 12}
    assert c["down"] is False
    assert c["statuses"] == [{"text": "Wound: ribs", "severity": "wound"}]
    assert c["inventory"] == [{"item": "torch", "qty": 2}]
    assert c["inv_hash"] == inv_hash(_Inv.items)
    assert c["gold"] == 9
    assert c["xp"] == 150
    assert c["level"] == 3
    assert c["acquired_advancements"] == ["adv.iron_grip"]
    assert c["ability_count"] == 2
    # R4: no fabricated tier / pending_advancements
    assert "tier" not in c and "pending_advancements" not in c
    # R3: no separate composure field
    assert "composure" not in c


def test_build_pc_census_none_location_is_honest_none():
    c = build_pc_census(
        character=_Char(),
        player_id="p1",
        character_name="Rux",
        seat=0,
        round_number=1,
        location=None,
    )
    assert c["location"] is None  # absent scene -> None, not "" or fabricated


# --- build_trope_census: session-level, NOT per-PC (R5) ---
class _Trope:
    def __init__(self, tid, status, prog, beats):
        self.id, self.status, self.progress = tid, status, prog
        self.beats_fired, self.last_fired_turn = beats, 3
        self.fire_cooldown_until = None


class _Snap:
    active_tropes = [_Trope("vengeance", "active", 0.4, 2)]
    turns_since_meaningful = 1
    total_beats_fired = 5


def test_build_trope_census_is_session_scoped():
    t = build_trope_census(_Snap(), round_number=4)
    assert t["round"] == 4
    assert t["turns_since_meaningful"] == 1
    assert t["total_beats_fired"] == 5
    assert t["active_tropes"] == [
        {
            "id": "vengeance",
            "status": "active",
            "progress": 0.4,
            "beats_fired": 2,
            "last_fired_turn": 3,
        }
    ]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_mechanical_census.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.mechanical_census'`.

- [ ] **Step 3: Create the pure module**

```python
# sidequest/game/mechanical_census.py
"""Phase 2 forensics: pure projections of canonical mechanical state.

Every accessor here was confirmed from source 2026-05-18 (see the plan's
Spec Reconciliation table R3-R9). These functions are PURE (no I/O, never
raise) EXCEPT emit_mechanical_census, which calls publish_event and is
fully wrapped so telemetry never crashes a turn (Phase 1 contract).
"""
from __future__ import annotations

import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def inventory_digest(items: list) -> list[dict]:
    """Fold raw inventory entries into [{item, qty}], aggregated by name.

    R7: items is list[dict]; narrator dups arrive as quantity:1 singletons,
    so we MUST sum by name, not trust per-entry quantity. Nameless entries
    are loud-skipped (never silently dropped). Output is name-sorted for a
    stable diff key."""
    agg: dict[str, int] = {}
    for entry in items or []:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name:
            logger.warning(
                "mechanical_census.inventory_unnamed_entry entry=%r", entry
            )
            continue
        qty = entry.get("quantity", 1)
        if not isinstance(qty, int):
            qty = 1
        agg[name] = agg.get(name, 0) + qty
    return [{"item": n, "qty": agg[n]} for n in sorted(agg)]


def inv_hash(items: list) -> str:
    """Stable 16-hex digest of the aggregated inventory (cheap diff key)."""
    digest = inventory_digest(items)
    blob = json.dumps(digest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def seat_index(room, player_id: str) -> int:
    """Best-effort positional seat (R9): index in playing_player_ids().
    Not durable across reconnect; player_id is the real key. Never raises
    — absent / no room -> -1 (honest sentinel, not a silent 0)."""
    try:
        return list(room.playing_player_ids()).index(player_id)
    except (AttributeError, ValueError, TypeError):
        return -1


def build_pc_census(
    *,
    character,
    player_id: str,
    character_name: str,
    seat: int,
    round_number: int,
    location,
) -> dict:
    """Project ONE seated PC's canonical mechanical state to a plain dict.

    Reads (confirmed from source): edge = single EdgePool (R3); xp/level/
    acquired_advancements from core (R4 — no tier/pending); location string
    + chassis current_room (R6); inventory aggregated digest (R7). Never
    raises on a partial model — missing attrs degrade to honest None/[]."""
    core = character.core
    edge = core.edge
    statuses = [
        {"text": getattr(s, "text", ""), "severity": getattr(s, "severity", "")}
        for s in (getattr(core, "statuses", None) or [])
    ]
    raw_items = getattr(getattr(core, "inventory", None), "items", None) or []
    return {
        "player_id": player_id,
        "character_name": character_name,
        "seat": seat,
        "round": round_number,
        "interaction": round_number,
        "location": location,
        "chassis_room": getattr(character, "current_room", None),
        "edge": {
            "current": getattr(edge, "current", None),
            "max": getattr(edge, "max", None),
            "base_max": getattr(edge, "base_max", None),
        },
        "down": bool(character.is_broken()),
        "statuses": statuses,
        "inventory": inventory_digest(raw_items),
        "inv_hash": inv_hash(raw_items),
        "gold": getattr(getattr(core, "inventory", None), "gold", 0),
        "xp": getattr(core, "xp", 0),
        "level": getattr(core, "level", 1),
        "acquired_advancements": list(
            getattr(core, "acquired_advancements", None) or []
        ),
        "ability_count": len(getattr(character, "abilities", None) or []),
    }


def build_trope_census(snapshot, round_number: int) -> dict:
    """Project SESSION-level trope state once per round (R5: tropes have
    no PC key; tension is not in the save and is excluded)."""
    tropes = []
    for t in getattr(snapshot, "active_tropes", None) or []:
        tropes.append(
            {
                "id": getattr(t, "id", ""),
                "status": getattr(t, "status", "dormant"),
                "progress": getattr(t, "progress", 0.0),
                "beats_fired": getattr(t, "beats_fired", 0),
                "last_fired_turn": getattr(t, "last_fired_turn", None),
            }
        )
    return {
        "round": round_number,
        "interaction": round_number,
        "active_tropes": tropes,
        "turns_since_meaningful": getattr(
            snapshot, "turns_since_meaningful", None
        ),
        "total_beats_fired": getattr(snapshot, "total_beats_fired", None),
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/game/test_mechanical_census.py -v`
Expected: PASS (all). `ruff check sidequest/game/mechanical_census.py` clean.

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/mechanical_census.py tests/game/test_mechanical_census.py
git commit -m "feat(census): pure canonical-state projections (edge/xp/inv/trope, R3-R9)"
```

---

## Task 3: Wire the emitter into `emitters.emit_event` (C2-atomic, NARRATION-gated)

**Files:**
- Modify: `sidequest/game/mechanical_census.py` (add `emit_mechanical_census`)
- Modify: `sidequest/server/emitters.py` (one guarded call inside the `with conn:` block)
- Test: `tests/server/test_mechanical_census_emit.py` (create)

- [ ] **Step 1: Bounded discovery — confirm the two `emit_event` locals (the ONLY project-specific bindings)**

Read `sidequest/server/emitters.py:225-340`. `emit_event` already binds, inside its body: the room (~`:229`, as `room = handler._room` — confirm the exact name) and the snapshot (used ~`:231` / `:321` — confirm the exact accessor expression, e.g. `handler._session_data.snapshot`). Record both **verbatim** expressions; the call added in Step 4 must reuse THOSE, never a new accessor (No-Silent-Fallback). These two are the only fill-ins (bounded exactly like the Phase-1 plan's `<HARNESS_IMPORT>`).

- [ ] **Step 2: Write the failing emitter test**

```python
# tests/server/test_mechanical_census_emit.py
"""emit_mechanical_census: one component='mechanical' census row per
SEATED PC + one session trope_census row, all inside the open C2 txn,
event_seq attributed, rolled back with the turn. Sealed-rounds: every
seated PC every round, no acting-player bias (ADR-036)."""
from sidequest.game.mechanical_census import emit_mechanical_census
from sidequest.game.persistence import SqliteStore
from sidequest.telemetry.watcher_hub import bind_event_store


def _store(tmp_path):
    return SqliteStore.open(str(tmp_path / "save.db"))


class _Edge:
    current, max, base_max = 10, 10, 10


class _Inv:
    items = [{"name": "torch", "quantity": 1}]
    gold = 0


def _char(name):
    core = type(
        "C", (), {
            "name": name, "xp": 0, "level": 1,
            "acquired_advancements": [], "statuses": [],
            "edge": _Edge(), "inventory": _Inv(),
        },
    )()
    return type(
        "Ch", (), {
            "core": core, "current_room": None, "abilities": [],
            "is_broken": lambda self: False,
        },
    )()


class _Snap:
    active_tropes = []
    turns_since_meaningful = 0
    total_beats_fired = 0
    character_locations = {"Rux": "Cave", "Vex": "Cave"}

    class turn_manager:  # noqa: N801
        interaction = 5

    characters = [_char("Rux"), _char("Vex")]
    player_seats = {"p1": "Rux", "p2": "Vex"}


class _Room:
    def playing_player_ids(self):
        return ["p1", "p2"]


def test_emits_one_census_per_seated_pc_plus_one_trope_in_txn(tmp_path):
    store = _store(tmp_path)
    try:
        bind_event_store(store)
        conn = store._conn
        with conn:  # simulate emit_event's C2 transaction
            conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) "
                "VALUES ('NARRATION', '{}', 't')"
            )
            emit_mechanical_census(_Room(), _Snap())
            rows = conn.execute(
                "SELECT event_seq, round, component, event_type, payload_json "
                "FROM turn_telemetry ORDER BY seq"
            ).fetchall()
        # 2 seated PCs + 1 session trope row, all event_seq=1 (this turn)
        assert [(r[0], r[2], r[3]) for r in rows] == [
            (1, "mechanical", "census"),
            (1, "mechanical", "census"),
            (1, "mechanical", "trope_census"),
        ]
        assert all(r[1] == 5 for r in rows)  # round = turn_manager.interaction
        import json

        pcs = {json.loads(r[4])["player_id"] for r in rows if r[3] == "census"}
        assert pcs == {"p1", "p2"}  # no acting-player bias
    finally:
        bind_event_store(None)
        store.close()


def test_empty_roster_emits_nothing_and_does_not_raise(tmp_path):
    store = _store(tmp_path)
    try:
        bind_event_store(store)

        class _Empty:
            def playing_player_ids(self):
                return []

        class _S(_Snap):
            player_seats: dict = {}

        with store._conn:
            store._conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) "
                "VALUES ('NARRATION','{}','t')"
            )
            emit_mechanical_census(_Empty(), _S())  # must not raise
        assert store._conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry"
        ).fetchone()[0] == 0  # honest no-rows, not an error
    finally:
        bind_event_store(None)
        store.close()
```

- [ ] **Step 3: Add `emit_mechanical_census` to `mechanical_census.py`**

Append to `sidequest/game/mechanical_census.py`:

```python
def emit_mechanical_census(room, snapshot) -> None:
    """Emit one component='mechanical' census per SEATED PC + one session
    trope_census, via Phase 1's publish_event sink. MUST be called from
    inside emit_event's open C2 `with conn:` block (R1) so each row rides
    the turn txn (event_seq attributed, atomic with events).

    Sealed rounds (ADR-036): every seated PC every round, keyed by
    player_id, no acting-player concept. Fully wrapped: ANY failure
    loud-logs and returns — telemetry never crashes a turn. Per-PC build
    failure is isolated (one bad PC never drops the others or the trope
    row). The census fields NEVER set field='encounter' (so the adjacent
    _maybe_persist_encounter_row hazard cannot fire on a census)."""
    # Imported here (not module top) to avoid a telemetry<->game import
    # cycle; publish_event is the Phase-1 sink entrypoint.
    from sidequest.telemetry.watcher_hub import publish_event

    try:
        round_number = int(
            getattr(getattr(snapshot, "turn_manager", None), "interaction", 0)
        )
    except (TypeError, ValueError):
        round_number = 0
    try:
        player_seats = dict(getattr(snapshot, "player_seats", None) or {})
        by_name = {
            getattr(c.core, "name", None): c
            for c in (getattr(snapshot, "characters", None) or [])
        }
        locations = dict(getattr(snapshot, "character_locations", None) or {})
        seated = list(room.playing_player_ids()) if room is not None else []
    except Exception:  # noqa: BLE001 — telemetry must never crash a turn
        logger.warning(
            "mechanical_census.roster_resolution_failed", exc_info=True
        )
        return

    for pid in seated:
        name = player_seats.get(pid)
        character = by_name.get(name)
        if character is None:
            # seated but no committed PC yet (CHARGEN) -> honest skip,
            # not a zeroed/fabricated body (No-Silent-Fallback).
            continue
        try:
            census = build_pc_census(
                character=character,
                player_id=pid,
                character_name=name,
                seat=seat_index(room, pid),
                round_number=round_number,
                location=locations.get(name),
            )
            publish_event("census", census, component="mechanical")
        except Exception:  # noqa: BLE001 — isolate one PC's failure
            logger.warning(
                "mechanical_census.build_failed pc=%s", pid, exc_info=True
            )
            continue

    try:
        trope = build_trope_census(snapshot, round_number)
        publish_event("trope_census", trope, component="mechanical")
    except Exception:  # noqa: BLE001
        logger.warning("mechanical_census.trope_build_failed", exc_info=True)
```

- [ ] **Step 4: Add the guarded call site in `emit_event`**

In `sidequest/server/emitters.py`, inside the `with conn:` block opened at `:276`, immediately after `seq = row.seq` (~`:278`, after the `append_in_transaction` at `:277`, before the projection fan-out), add — using the exact `room`/`snapshot` expressions confirmed in Step 1:

```python
            if kind == "NARRATION" and event_log is not None:
                # Phase 2: photograph every seated PC's mechanical state
                # while the C2 turn txn is open (R1) so it rides the turn.
                # Gated to the single canonical NARRATION emit so it fires
                # once per turn, not per segment/confrontation frame.
                from sidequest.game.mechanical_census import (
                    emit_mechanical_census,
                )

                emit_mechanical_census(<ROOM_EXPR>, <SNAPSHOT_EXPR>)
```

Replace `<ROOM_EXPR>` / `<SNAPSHOT_EXPR>` with the verbatim expressions from Step 1 (e.g. `room` and `handler._session_data.snapshot`). Do **not** introduce a new accessor. Leave every existing line in `emit_event` (the `append_in_transaction`, projection cache, `emit.author_resolved` publish, fan-out) untouched.

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/server/test_mechanical_census_emit.py -v`
Expected: PASS (both).

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/mechanical_census.py sidequest/server/emitters.py tests/server/test_mechanical_census_emit.py
git commit -m "feat(census): emit per-seated-PC + session trope census inside C2 NARRATION txn"
```

---

## Task 4: Per-PC failure isolation + no-encounter-field guard (contract guards)

**Files:**
- Test: `tests/game/test_mechanical_census.py` (append)

- [ ] **Step 1: Write the contract-guard tests**

```python
# append to tests/game/test_mechanical_census.py
from sidequest.game.mechanical_census import emit_mechanical_census
from sidequest.game.persistence import SqliteStore
from sidequest.telemetry.watcher_hub import bind_event_store


def test_one_bad_pc_is_isolated_others_and_trope_still_emit(
    tmp_path, caplog
):
    """A PC whose build raises must loud-log mechanical_census.build_failed
    and NOT drop the healthy PC or the session trope row."""
    store = SqliteStore.open(str(tmp_path / "s.db"))
    try:
        bind_event_store(store)

        class _GoodCore:
            name = "Rux"
            xp = 0
            level = 1
            acquired_advancements: list = []
            statuses: list = []
            edge = type("E", (), {"current": 5, "max": 5, "base_max": 5})()
            inventory = type("I", (), {"items": [], "gold": 0})()

        good = type(
            "G", (), {"core": _GoodCore(), "current_room": None,
                      "abilities": [], "is_broken": lambda self: False}
        )()

        class _BadCore:
            name = "Vex"

            @property
            def edge(self):
                raise RuntimeError("corrupt edge pool")

        bad = type(
            "B", (), {"core": _BadCore(), "current_room": None,
                      "abilities": [], "is_broken": lambda self: False}
        )()

        class _Snap:
            active_tropes: list = []
            turns_since_meaningful = 0
            total_beats_fired = 0
            character_locations = {"Rux": "Cave", "Vex": "Cave"}
            characters = [good, bad]
            player_seats = {"p1": "Rux", "p2": "Vex"}

            class turn_manager:  # noqa: N801
                interaction = 2

        class _Room:
            def playing_player_ids(self):
                return ["p1", "p2"]

        with caplog.at_level("WARNING"), store._conn:
            store._conn.execute(
                "INSERT INTO events (kind, payload_json, created_at) "
                "VALUES ('NARRATION','{}','t')"
            )
            emit_mechanical_census(_Room(), _Snap())  # must not raise
        rows = store._conn.execute(
            "SELECT event_type, payload_json FROM turn_telemetry ORDER BY seq"
        ).fetchall()
        types = [r[0] for r in rows]
        assert types == ["census", "trope_census"]  # good PC + trope kept
        assert "mechanical_census.build_failed pc=p2" in caplog.text
    finally:
        bind_event_store(None)
        store.close()


def test_census_payload_never_sets_encounter_field(tmp_path):
    """The adjacent _maybe_persist_encounter_row hazard only fires on
    fields['field']=='encounter'. A census must never carry that key
    (defends the open C2 txn from a premature commit)."""
    from sidequest.game.mechanical_census import build_pc_census

    class _C:
        core = type(
            "C", (), {"name": "Rux", "xp": 0, "level": 1,
                      "acquired_advancements": [], "statuses": [],
                      "edge": type("E", (), {"current": 1, "max": 1,
                                              "base_max": 1})(),
                      "inventory": type("I", (), {"items": [], "gold": 0})()}
        )()
        current_room = None
        abilities: list = []

        def is_broken(self):
            return False

    c = build_pc_census(
        character=_C(), player_id="p1", character_name="Rux",
        seat=0, round_number=1, location=None,
    )
    assert "field" not in c or c.get("field") != "encounter"
```

- [ ] **Step 2: Run to verify it passes**

Run: `uv run pytest tests/game/test_mechanical_census.py -v -k "isolated or encounter_field"`
Expected: **PASS** — the `except Exception` per-PC wrapper and the census schema (Tasks 2-3) already provide this. These are the spec-mandated contract guards; they should pass without new production code. If `test_one_bad_pc_is_isolated...` FAILS, the Task 3 per-PC wrapper is wrong — fix the wrapper, do not weaken the test.

- [ ] **Step 3: Commit**

```bash
git add tests/game/test_mechanical_census.py
git commit -m "test(census): guard per-PC isolation + never field=encounter"
```

---

## Task 5: Mandatory wiring test — a real production turn writes `component='mechanical'`

**Why:** CLAUDE.md "Every Test Suite Needs a Wiring Test". Tasks 1-4 call the emitter directly. This proves the census fires from a **real turn through `connect.py`'s `bind_event_store` and `emit_event`'s NARRATION emit** — a read-only fold + UI with no live producer would be a half-wired feature (`sq-wire-it`).

**Files:**
- Test: `tests/server/test_turn_telemetry_wiring.py` (append — reuse the existing `_drive_one_real_turn` harness, lines ~148-232; it seeds a MP game and drives one production turn, returning the save `.db` path)

- [ ] **Step 1: Write the failing wiring test**

```python
# append to tests/server/test_turn_telemetry_wiring.py
def test_a_real_turn_persists_mechanical_census_rows(tmp_path):
    """A real production turn writes one component='mechanical' census
    row per seated PC + one session trope_census row, attributed to the
    turn's event frame. Proves the emitter is wired into emit_event's
    NARRATION path, not just importable."""
    import sqlite3

    save_db = _drive_one_real_turn(tmp_path)  # existing harness
    conn = sqlite3.connect(f"file:{save_db}?mode=ro", uri=True)
    try:
        census = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry "
            "WHERE component='mechanical' AND event_type='census'"
        ).fetchone()[0]
        tropes = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry "
            "WHERE component='mechanical' AND event_type='trope_census'"
        ).fetchone()[0]
        attributed = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry "
            "WHERE component='mechanical' AND event_seq IS NOT NULL"
        ).fetchone()[0]
        assert census >= 1, (
            "no mechanical census rows: emit_mechanical_census is not "
            "wired into emit_event's NARRATION path"
        )
        assert tropes >= 1, "no session trope_census row from a real turn"
        assert attributed >= 1, (
            "mechanical rows not event_seq-attributed: census did not ride "
            "the C2 turn txn (R1 violated)"
        )
    finally:
        conn.close()
```

If `_drive_one_real_turn` is not the exact helper name / signature, use the real one identified in the existing `tests/server/test_turn_telemetry_wiring.py` (it is the Phase-1 wiring harness; do **not** fork a new server harness — reuse-first).

- [ ] **Step 2: Run to verify it passes (and prove non-vacuous)**

Run: `uv run pytest tests/server/test_turn_telemetry_wiring.py::test_a_real_turn_persists_mechanical_census_rows -v`
Expected: **PASS** once Tasks 2-3 are merged. To prove non-vacuous: temporarily comment out the `emit_mechanical_census(...)` call added in Task 3 Step 4, re-run, confirm it **FAILS** with "is not wired into emit_event's NARRATION path", restore the call, confirm PASS. Document this in the commit body.

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_turn_telemetry_wiring.py
git commit -m "test(census): wiring test — a real turn writes mechanical census rows

Verified non-vacuous: removing the emit_mechanical_census call makes it
fail with 'not wired into emit_event's NARRATION path'."
```

---

## Task 6: Read-time fold — `fold_mechanical_census` + `fold_mechanical_strip` (pure)

**Files:**
- Modify: `sidequest/game/forensic_fold.py` (append after `:195`, EOF — mirrors `fold_turn_telemetry` discipline verbatim; do NOT touch lines 1-195)
- Test: `tests/game/test_forensic_fold.py` (append; reuse the existing `_trow(seq, component, event_type, payload_json, ts="t")` factory at `:153`)

- [ ] **Step 1: Write the failing fold tests**

```python
# append to tests/game/test_forensic_fold.py
import json as _json

from sidequest.game.forensic_fold import (
    MechanicalFold,
    fold_mechanical_census,
    fold_mechanical_strip,
)


def _crow(seq, payload: dict, event_type="census"):
    return _trow(seq, "mechanical", event_type, _json.dumps(payload))


def test_mechanical_empty_yields_absent():
    r = fold_mechanical_census([], [])
    assert isinstance(r, MechanicalFold)
    assert r.state == "absent"
    assert r.pcs == ()
    assert r.unparseable_seqs == ()


def test_mechanical_first_round_per_pc_is_baseline_no_deltas():
    cur = [_crow(1, {"player_id": "p1", "character_name": "Rux", "seat": 0,
                     "round": 1, "edge": {"current": 10, "max": 10},
                     "location": "Cave", "inventory": [{"item": "torch",
                     "qty": 1}], "xp": 0, "level": 1,
                     "acquired_advancements": []})]
    r = fold_mechanical_census(cur, [])  # no prior rows
    assert r.state == "moved"            # round has data
    [pc] = r.pcs
    assert pc.player_id == "p1"
    assert pc.kind == "baseline"         # first census -> absolute, no diff
    assert pc.deltas == ()
    assert pc.absolute["edge"] == {"current": 10, "max": 10}


def test_mechanical_no_change_is_static_not_moved():
    body = {"player_id": "p1", "character_name": "Rux", "seat": 0,
            "edge": {"current": 7, "max": 10}, "location": "Cave",
            "inventory": [{"item": "torch", "qty": 1}], "xp": 5,
            "level": 1, "acquired_advancements": []}
    prior = [_crow(1, {**body, "round": 1})]
    cur = [_crow(2, {**body, "round": 2})]
    r = fold_mechanical_census(cur, prior)
    [pc] = r.pcs
    assert pc.kind == "static"
    assert pc.deltas == ()
    assert r.state == "static"  # the WHOLE round had no mechanical change


def test_mechanical_moved_emits_typed_deltas():
    prior = [_crow(1, {"player_id": "p1", "character_name": "Rux", "seat": 0,
                       "round": 1, "edge": {"current": 10, "max": 10},
                       "location": "Ropefoot",
                       "inventory": [{"item": "torch", "qty": 1}], "xp": 0,
                       "level": 2, "acquired_advancements": []})]
    cur = [_crow(2, {"player_id": "p1", "character_name": "Rux", "seat": 0,
                     "round": 2, "edge": {"current": 7, "max": 10},
                     "location": "The Kept Fire",
                     "inventory": [{"item": "brass key", "qty": 1}],
                     "xp": 15, "level": 3,
                     "acquired_advancements": ["adv.iron_grip"]})]
    r = fold_mechanical_census(cur, prior)
    [pc] = r.pcs
    assert pc.kind == "moved"
    d = dict(pc.deltas)
    assert d["location"] == "Ropefoot → The Kept Fire"
    assert d["edge"] == "10→7 (−3)"
    assert d["xp"] == "+15"
    assert d["level"] == "2→3"
    assert d["inventory"] == "+brass key, −torch×1"
    assert d["advancements"] == "+adv.iron_grip"
    assert r.state == "moved"


def test_mechanical_trope_census_folds_session_block():
    prior = [_crow(1, {"round": 1, "active_tropes": [{"id": "vengeance",
             "status": "active", "progress": 0.2, "beats_fired": 1}],
             "turns_since_meaningful": 0, "total_beats_fired": 3},
             event_type="trope_census")]
    cur = [_crow(2, {"round": 2, "active_tropes": [{"id": "vengeance",
           "status": "active", "progress": 0.5, "beats_fired": 2}],
           "turns_since_meaningful": 1, "total_beats_fired": 4},
           event_type="trope_census")]
    r = fold_mechanical_census(cur, prior)
    assert r.trope is not None
    assert "vengeance" in r.trope["summary"]
    assert r.trope["kind"] == "moved"


def test_mechanical_unparseable_row_is_loud_skipped_and_recorded(caplog):
    bad = _trow(9, "mechanical", "census", "{not json")
    good = _crow(10, {"player_id": "p1", "character_name": "Rux",
                      "seat": 0, "round": 1, "edge": {"current": 1,
                      "max": 1}, "location": "Cave", "inventory": [],
                      "xp": 0, "level": 1, "acquired_advancements": []})
    with caplog.at_level("WARNING"):
        r = fold_mechanical_census([bad, good], [])
    assert r.unparseable_seqs == (9,)
    assert [pc.player_id for pc in r.pcs] == ["p1"]
    assert "forensic_fold.mechanical_unparseable_payload seq=9" in caplog.text


def test_fold_mechanical_strip_tristate_per_round():
    body = {"player_id": "p1", "character_name": "Rux", "seat": 0,
            "edge": {"current": 5, "max": 5}, "location": "Cave",
            "inventory": [], "xp": 0, "level": 1,
            "acquired_advancements": []}
    rows = [
        _crow(1, {**body, "round": 1}),                       # baseline
        _crow(2, {**body, "round": 2}),                       # static
        _crow(3, {**body, "round": 3, "xp": 9}),              # moved
    ]
    strip = fold_mechanical_strip(rows)
    assert strip == [
        {"round": 1, "state": "moved"},   # first census = has data
        {"round": 2, "state": "static"},
        {"round": 3, "state": "moved"},
    ]


def test_fold_mechanical_strip_empty_is_empty_list():
    assert fold_mechanical_strip([]) == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_fold.py -v -k mechanical`
Expected: FAIL — `ImportError: cannot import name 'fold_mechanical_census'`.

- [ ] **Step 3: Implement the folds (append to `forensic_fold.py`, EOF)**

```python
# ---- Phase 2: mechanical-state census fold (mirrors fold_turn_telemetry) ----


@dataclass(frozen=True)
class PcMechanicalDiff:
    """One seated PC's mechanical state for a round.

    kind: 'baseline' (first census for this PC — absolute, no deltas),
    'static' (census fired, nothing changed), or 'moved' (typed deltas)."""

    player_id: str
    character_name: str
    seat: int
    kind: str
    deltas: tuple[tuple[str, str], ...] = ()
    absolute: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MechanicalFold:
    """Read-time curation of a round's mechanical census.

    state: 'absent' (no census rows this round — save predates Phase 2),
    'static' (all PCs static), or 'moved' (>=1 PC moved/baseline)."""

    state: str = "absent"
    pcs: tuple[PcMechanicalDiff, ...] = ()
    trope: dict | None = None
    unparseable_seqs: tuple[int, ...] = ()


def _mech_rows(raw_rows: list, want_type: str):
    """Parse mechanical rows of one event_type; loud-skip bad ones.
    Returns (parsed_payloads, unparseable_seqs) — same contract as
    fold_turn_telemetry's loud-skip (logged + recorded, never silent)."""
    parsed: list[dict] = []
    unparseable: list[int] = []

    def _key(row) -> int:
        try:
            return int(row.get("seq"))
        except (TypeError, ValueError, AttributeError):
            return -1

    for row in sorted(raw_rows or [], key=_key):
        try:
            seq = int(row["seq"])
            if str(row.get("event_type") or "") != want_type:
                continue
            payload = json.loads(row.get("payload_json"))
        except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
            seq_val = row.get("seq") if hasattr(row, "get") else None
            logger.warning(
                "forensic_fold.mechanical_unparseable_payload seq=%s", seq_val
            )
            if isinstance(seq_val, int):
                unparseable.append(seq_val)
            continue
        if not isinstance(payload, dict):
            logger.warning(
                "forensic_fold.mechanical_non_dict_payload seq=%s", seq
            )
            unparseable.append(seq)
            continue
        parsed.append(payload)
    return parsed, unparseable


def _esc_num(n) -> str:
    try:
        return f"{int(n):+d}"
    except (TypeError, ValueError):
        return "?"


def _pc_deltas(cur: dict, prior: dict | None) -> tuple[tuple[str, str], ...]:
    """Typed consecutive diff. prior None -> caller renders baseline."""
    if prior is None:
        return ()
    out: list[tuple[str, str]] = []
    if cur.get("location") != prior.get("location"):
        out.append(
            ("location",
             f"{prior.get('location')} → {cur.get('location')}")
        )
    ce, pe = cur.get("edge") or {}, prior.get("edge") or {}
    if ce.get("current") != pe.get("current"):
        try:
            d = int(ce.get("current")) - int(pe.get("current"))
            sign = "−" if d < 0 else "+"
            out.append(("edge",
                        f"{pe.get('current')}→{ce.get('current')} "
                        f"({sign}{abs(d)})".replace("(+", "(+")
                        .replace("(−", "(−")))
        except (TypeError, ValueError):
            out.append(("edge", f"{pe.get('current')}→{ce.get('current')}"))
    if cur.get("xp") != prior.get("xp"):
        try:
            out.append(("xp", _esc_num(int(cur.get("xp")) - int(prior.get("xp")))))
        except (TypeError, ValueError):
            out.append(("xp", f"{prior.get('xp')}→{cur.get('xp')}"))
    if cur.get("level") != prior.get("level"):
        out.append(("level", f"{prior.get('level')}→{cur.get('level')}"))
    # inventory: set-diff the aggregated digests by item name
    cmap = {i["item"]: i["qty"] for i in cur.get("inventory") or []
            if isinstance(i, dict) and "item" in i}
    pmap = {i["item"]: i["qty"] for i in prior.get("inventory") or []
            if isinstance(i, dict) and "item" in i}
    inv_bits: list[str] = []
    for item in sorted(set(cmap) | set(pmap)):
        cq, pq = cmap.get(item, 0), pmap.get(item, 0)
        if cq == pq:
            continue
        if pq == 0:
            inv_bits.append(f"+{item}" + (f"×{cq}" if cq != 1 else ""))
        elif cq == 0:
            inv_bits.append(f"−{item}" + (f"×{pq}" if pq != 1 else ""))
        else:
            inv_bits.append(f"{item}×{pq}→×{cq}")
    if inv_bits:
        out.append(("inventory", ", ".join(inv_bits)))
    ca = set(cur.get("acquired_advancements") or [])
    pa = set(prior.get("acquired_advancements") or [])
    if ca - pa:
        out.append(("advancements",
                    ", ".join("+" + a for a in sorted(ca - pa))))
    return tuple(out)


def fold_mechanical_census(
    current_rows: list, prior_rows: list
) -> MechanicalFold:
    """Pure, no I/O, never raises (mirrors fold_turn_telemetry).

    current_rows = this round's component='mechanical' rows; prior_rows =
    the previous CENSUS round's rows (read path supplies both). Per PC:
    no prior -> baseline; prior == current -> static; else moved with
    typed deltas. Round state: absent (no current rows) / static (all
    PCs static) / moved (any moved or baseline)."""
    cur_pc, u1 = _mech_rows(current_rows, "census")
    pri_pc, u2 = _mech_rows(prior_rows, "census")
    cur_tr, u3 = _mech_rows(current_rows, "trope_census")
    pri_tr, u4 = _mech_rows(prior_rows, "trope_census")
    unparseable = tuple(u1 + u2 + u3 + u4)

    if not cur_pc and not cur_tr:
        return MechanicalFold(state="absent", unparseable_seqs=unparseable)

    prior_by_pid = {p.get("player_id"): p for p in pri_pc}
    pcs: list[PcMechanicalDiff] = []
    any_moved = False
    for c in cur_pc:
        pid = c.get("player_id")
        prior = prior_by_pid.get(pid)
        if prior is None:
            kind, deltas = "baseline", ()
            any_moved = True
        else:
            deltas = _pc_deltas(c, prior)
            kind = "moved" if deltas else "static"
            any_moved = any_moved or bool(deltas)
        pcs.append(
            PcMechanicalDiff(
                player_id=str(pid),
                character_name=str(c.get("character_name") or ""),
                seat=c.get("seat") if isinstance(c.get("seat"), int) else -1,
                kind=kind,
                deltas=deltas,
                absolute={
                    k: c.get(k)
                    for k in ("edge", "location", "inventory", "xp",
                              "level", "acquired_advancements", "down",
                              "statuses", "gold", "chassis_room")
                },
            )
        )

    trope = None
    if cur_tr:
        ct = cur_tr[-1]
        pt = pri_tr[-1] if pri_tr else None
        cur_ids = {t.get("id"): t for t in ct.get("active_tropes") or []}
        pri_ids = {t.get("id"): t for t in (pt or {}).get("active_tropes")
                   or []} if pt else {}
        bits: list[str] = []
        for tid in sorted(cur_ids):
            ctp = cur_ids[tid]
            ptp = pri_ids.get(tid)
            if ptp is None:
                bits.append(f"{tid} → {ctp.get('status')} "
                            f"p={ctp.get('progress')}")
            elif ptp.get("progress") != ctp.get("progress") or \
                    ptp.get("status") != ctp.get("status"):
                bits.append(f"{tid} {ptp.get('progress')}→"
                            f"{ctp.get('progress')}")
        trope = {
            "summary": "; ".join(bits) if bits else "· no trope change",
            "kind": "moved" if (pt is None or bits) else "static",
            "turns_since_meaningful": ct.get("turns_since_meaningful"),
            "total_beats_fired": ct.get("total_beats_fired"),
        }

    state = "moved" if any_moved or (trope and trope["kind"] == "moved") \
        else "static"
    return MechanicalFold(
        state=state,
        pcs=tuple(pcs),
        trope=trope,
        unparseable_seqs=unparseable,
    )


def fold_mechanical_strip(all_rows: list) -> list[dict]:
    """Whole-save per-round tri-state for the macro strip. One pass,
    computed once at save-select (mirrors the P1.1 'needs the per-round
    fold' reservation). Pure, never raises. Returns
    [{round, state}] in round order; absent rounds simply do not appear."""
    census, _ = _mech_rows(all_rows, "census")
    tropes, _ = _mech_rows(all_rows, "trope_census")
    by_round: dict[int, list[dict]] = {}
    for p in census:
        r = p.get("round")
        if isinstance(r, int):
            by_round.setdefault(r, []).append(p)
    tr_by_round: dict[int, list[dict]] = {}
    for p in tropes:
        r = p.get("round")
        if isinstance(r, int):
            tr_by_round.setdefault(r, []).append(p)

    out: list[dict] = []
    prev_pc: dict[str, dict] = {}
    prev_tr: dict | None = None
    for rnd in sorted(set(by_round) | set(tr_by_round)):
        moved = False
        for c in by_round.get(rnd, []):
            pid = c.get("player_id")
            prior = prev_pc.get(pid)
            if prior is None or _pc_deltas(c, prior):
                moved = True
            prev_pc[pid] = c
        tlist = tr_by_round.get(rnd, [])
        if tlist:
            ct = tlist[-1]
            if prev_tr is None or _json.dumps(
                ct.get("active_tropes"), sort_keys=True
            ) != _json.dumps(prev_tr.get("active_tropes"), sort_keys=True):
                moved = True
            prev_tr = ct
        out.append({"round": rnd, "state": "moved" if moved else "static"})
    return out
```

Add `import json as _json` near the top of the existing `forensic_fold.py` import block if `_json` is not already imported (the file imports `json`; alias to avoid touching the Phase-1 `json` usages). If a plain `json` is acceptable in the new code, use `json` and skip the alias — match whatever the file already exposes; do not rename existing imports.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_fold.py -v`
Expected: PASS (all mechanical tests + all pre-existing `fold_known_facts` / `fold_turn_telemetry` tests still green — Phase 1 untouched).

- [ ] **Step 5: Commit**

```bash
git add sidequest/game/forensic_fold.py tests/game/test_forensic_fold.py
git commit -m "feat(forensics): pure fold_mechanical_census + strip (baseline/static/moved/absent)"
```

---

## Task 7: Read path — `mechanical` key in `build_turn_bundle`; missing-table → absent

**Files:**
- Modify: `sidequest/game/forensic_query.py` (import `:16`; new helpers ~`:198`; both bundle returns `:303`, `:384`; call ~`:307`)
- Modify: `sidequest/server/rest.py` (`debug_save_turn` empty literal `:470`)
- Test: `tests/game/test_forensic_query.py` (append; reuse `_make_save` `:9` + `_seed_rounds(store)` `:109`); `tests/server/test_forensics_routes.py` (sync the two never-500 literals)

**Coupled literal sites — ALL must add `mechanical` together (the spec's key-set-drift hazard):**
1. `forensic_query.py:303` empty/unknown-round return → `"mechanical": _empty_mechanical()`
2. `forensic_query.py:384` full return → `"mechanical": mechanical`
3. `rest.py:470` `debug_save_turn` `empty` literal → `"mechanical": {"state": "absent", "pcs": [], "trope": None, "unparseable_seqs": []}`
4. `tests/server/test_forensics_routes.py` `test_turn_bundle_unknown_slug_is_empty_not_500` literal (~`:98-107`) → same dict
5. `tests/server/test_forensics_routes.py` `test_turn_bundle_corrupt_save_is_empty_not_500` literal (~`:119-128`) → same dict

- [ ] **Step 1: Write the failing read-path tests**

```python
# append to tests/game/test_forensic_query.py
def _add_mechanical(db, rows):
    """rows = list of (event_seq, round, event_type, payload_dict)."""
    import json as _j
    import sqlite3

    con = sqlite3.connect(str(db))
    con.executescript(
        "CREATE TABLE IF NOT EXISTS turn_telemetry ("
        " seq INTEGER PRIMARY KEY AUTOINCREMENT, event_seq INTEGER,"
        " round INTEGER, ts TEXT NOT NULL, component TEXT NOT NULL,"
        " event_type TEXT NOT NULL, payload_json TEXT NOT NULL);"
    )
    con.executemany(
        "INSERT INTO turn_telemetry "
        "(event_seq, round, ts, component, event_type, payload_json) "
        "VALUES (?,?,?,?,?,?)",
        [(es, rn, "t", "mechanical", et, _j.dumps(p)) for es, rn, et, p in rows],
    )
    con.commit()
    con.close()


def test_bundle_mechanical_diffs_round_against_prev_census_round(tmp_path):
    db = tmp_path / "saves" / "games" / "mech" / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    store = _make_save(tmp_path / "saves", "mech", genre="g", world="w")
    _seed_rounds(store)            # rounds 1 & 2 of events/narrative
    store.close()
    base = {"player_id": "p1", "character_name": "Rux", "seat": 0,
            "edge": {"current": 10, "max": 10}, "location": "Cave",
            "inventory": [], "xp": 0, "level": 1,
            "acquired_advancements": []}
    _add_mechanical(db, [
        (None, 1, "census", {**base, "round": 1}),
        (None, 2, "census", {**base, "round": 2, "xp": 25}),
    ])
    from sidequest.game.forensic_query import _ro_connect, build_turn_bundle

    conn = _ro_connect(db)
    try:
        b = build_turn_bundle(conn, 2)
        m = b["mechanical"]
        assert m["state"] == "moved"
        [pc] = m["pcs"]
        assert pc["player_id"] == "p1"
        assert pc["kind"] == "moved"
        assert dict(pc["deltas"])["xp"] == "+25"
    finally:
        conn.close()


def test_bundle_missing_turn_telemetry_table_is_absent_not_error(tmp_path):
    store = _make_save(tmp_path / "saves", "old", genre="g", world="w")
    _seed_rounds(store)            # NO turn_telemetry table
    store.close()
    from sidequest.game.forensic_query import _ro_connect, build_turn_bundle

    db = tmp_path / "saves" / "games" / "old" / "save.db"
    conn = _ro_connect(db)
    try:
        b = build_turn_bundle(conn, 1)
        assert b["mechanical"] == {
            "state": "absent", "pcs": [], "trope": None,
            "unparseable_seqs": [],
        }
    finally:
        conn.close()


def test_bundle_unknown_round_includes_empty_mechanical_key(tmp_path):
    store = _make_save(tmp_path / "saves", "uk", genre="g", world="w")
    _seed_rounds(store)
    store.close()
    from sidequest.game.forensic_query import _ro_connect, build_turn_bundle

    db = tmp_path / "saves" / "games" / "uk" / "save.db"
    conn = _ro_connect(db)
    try:
        b = build_turn_bundle(conn, 999)
        assert b["mechanical"] == {
            "state": "absent", "pcs": [], "trope": None,
            "unparseable_seqs": [],
        }
    finally:
        conn.close()


def test_mechanical_read_does_not_mutate_the_save(tmp_path):
    import sqlite3

    store = _make_save(tmp_path / "saves", "bi", genre="g", world="w")
    _seed_rounds(store)
    store.close()
    db = tmp_path / "saves" / "games" / "bi" / "save.db"
    con = sqlite3.connect(str(db))
    con.executescript("PRAGMA journal_mode=DELETE;")
    con.commit()
    con.close()
    _add_mechanical(db, [(None, 1, "census",
                          {"player_id": "p1", "character_name": "Rux",
                           "seat": 0, "round": 1,
                           "edge": {"current": 1, "max": 1},
                           "location": "Cave", "inventory": [], "xp": 0,
                           "level": 1, "acquired_advancements": []})])
    bytes_before = db.read_bytes()
    mtime_before = db.stat().st_mtime_ns
    from sidequest.game.forensic_query import _ro_connect, build_turn_bundle

    conn = _ro_connect(db)
    try:
        build_turn_bundle(conn, 1)
    finally:
        conn.close()
    assert db.read_bytes() == bytes_before
    assert db.stat().st_mtime_ns == mtime_before
```

> Match `_seed_rounds`'s real signature (`_seed_rounds(store)`, `tests/game/test_forensic_query.py:109`) and `_make_save`'s real save path layout (`<saves>/games/<slug>/save.db`, `:9-21`). The assertions only depend on `_seed_rounds` producing `events`+`narrative_log` for rounds 1-2.

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k mechanical`
Expected: FAIL — `KeyError: 'mechanical'`.

- [ ] **Step 3: Add the read helpers + bundle key**

In `sidequest/game/forensic_query.py`, extend the fold import at `:16`:

```python
from sidequest.game.forensic_fold import (
    fold_known_facts,
    fold_mechanical_census,
    fold_mechanical_strip,
    fold_turn_telemetry,
)
```

Add near `_empty_telemetry` (~`:190`):

```python
def _empty_mechanical() -> dict:
    return {"state": "absent", "pcs": [], "trope": None,
            "unparseable_seqs": []}


def _mechanical_for_round(
    conn: sqlite3.Connection, seq_start: int, seq_end: int, round_number: int
) -> dict:
    """Read this round's component='mechanical' rows + the PREVIOUS census
    round's rows, fold into a per-PC diff. Missing table (pre-Phase-2
    saves) == absent. ?mode=ro — never creates the table (Phase-1
    discipline)."""
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='turn_telemetry'"
    ).fetchone()
    if has_table is None:
        return _empty_mechanical()
    cur = conn.execute(
        "SELECT seq, event_seq, round, ts, component, event_type, "
        "payload_json FROM turn_telemetry "
        "WHERE component='mechanical' AND ("
        "  (event_seq IS NOT NULL AND event_seq >= ? AND event_seq <= ?) "
        "  OR (round = ?)) ORDER BY seq",
        (seq_start, seq_end, round_number),
    ).fetchall()
    prev_round_row = conn.execute(
        "SELECT MAX(round) FROM turn_telemetry "
        "WHERE component='mechanical' AND round IS NOT NULL AND round < ?",
        (round_number,),
    ).fetchone()
    prev = []
    if prev_round_row and prev_round_row[0] is not None:
        prev = conn.execute(
            "SELECT seq, event_seq, round, ts, component, event_type, "
            "payload_json FROM turn_telemetry "
            "WHERE component='mechanical' AND round = ? ORDER BY seq",
            (prev_round_row[0],),
        ).fetchall()
    fold = fold_mechanical_census(
        [dict(r) for r in cur], [dict(r) for r in prev]
    )
    return {
        "state": fold.state,
        "pcs": [
            {
                "player_id": pc.player_id,
                "character_name": pc.character_name,
                "seat": pc.seat,
                "kind": pc.kind,
                "deltas": list(pc.deltas),
                "absolute": pc.absolute,
            }
            for pc in fold.pcs
        ],
        "trope": fold.trope,
        "unparseable_seqs": list(fold.unparseable_seqs),
    }


def mechanical_strip(conn: sqlite3.Connection) -> list:
    """Whole-save per-round tri-state for the macro strip. Missing table
    -> []. One pass, ?mode=ro, never creates the table."""
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='turn_telemetry'"
    ).fetchone()
    if has_table is None:
        return []
    rows = conn.execute(
        "SELECT seq, round, component, event_type, payload_json "
        "FROM turn_telemetry WHERE component='mechanical' ORDER BY seq"
    ).fetchall()
    return fold_mechanical_strip([dict(r) for r in rows])
```

In `build_turn_bundle`, the **empty/unknown-round return** (`:303` area, alongside `"telemetry": _empty_telemetry()`):

```python
        "mechanical": _empty_mechanical(),
```

In `build_turn_bundle`, alongside the `telemetry = _telemetry_for_round(...)` call (~`:307`):

```python
    mechanical = _mechanical_for_round(conn, seq_start, seq_end, round_number)
```

and in the **full success return** (`:384` area, alongside `"telemetry": telemetry`):

```python
        "mechanical": mechanical,
```

- [ ] **Step 4: Sync the coupled never-500 literals (sites 3-5)**

`sidequest/server/rest.py` `debug_save_turn` `empty` literal (`:470`) — add:

```python
            "mechanical": {"state": "absent", "pcs": [], "trope": None, "unparseable_seqs": []},
```

`tests/server/test_forensics_routes.py` — in BOTH `test_turn_bundle_unknown_slug_is_empty_not_500` (~`:98-107`) and `test_turn_bundle_corrupt_save_is_empty_not_500` (~`:119-128`) expected-dict literals, add the identical:

```python
        "mechanical": {"state": "absent", "pcs": [], "trope": None, "unparseable_seqs": []},
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py tests/server/test_forensics_routes.py -v`
Expected: PASS — new mechanical read tests pass; the never-500 / byte-identity / "assembles all panels" tests still pass with both `telemetry` and `mechanical` keys present.

- [ ] **Step 6: Commit**

```bash
git add sidequest/game/forensic_query.py sidequest/server/rest.py tests/game/test_forensic_query.py tests/server/test_forensics_routes.py
git commit -m "feat(forensics): per-round mechanical read (prev-census-round diff, missing-table=absent)"
```

---

## Task 8: Forensics UI — per-round mechanical-diff lane (three honest renderings)

**Files:**
- Modify: `sidequest/server/static/forensics.html` (`.tier-mechanical` CSS ~`:31`; new `<details>` block immediately after the telemetry `</details>` at `:340`, before the terminal-snapshot `<details>` at `:341`)
- Modify: `tests/server/test_forensics_routes.py` (extend the existing wiring test `test_forensics_route_is_wired_and_serves_html` ~`:147`)

- [ ] **Step 1: Write the failing wiring assertions**

Append to the existing `test_forensics_route_is_wired_and_serves_html` (do not create a new test):

```python
    assert "mechanical state (this round)" in resp.text       # lane label
    assert "no mechanical census (save predates" in resp.text  # absent
    assert "no mechanical change" in resp.text                 # static
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest "tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html" -v`
Expected: FAIL — none of the strings are in `forensics.html` yet.

- [ ] **Step 3: Add the lane to `forensics.html`**

Add a CSS class near `:31` (after `.tier-absent`):

```css
    .tier-mechanical { color:var(--derived); }
```

In the per-round bundle render, **immediately after the decision-telemetry `</details>'+` at line 340** and before the terminal-snapshot `<details>` at line 341, insert (mirroring the `tel`/`telBody` idiom at `:297-316`, using existing `esc()`/`j()` `:80-82`):

```javascript
  const mech = (b.mechanical) || {state:'absent',pcs:[],trope:null,unparseable_seqs:[]};
  const mechRow = pc => {
    if (pc.kind === 'baseline') {
      const a = pc.absolute || {};
      return '<tr><td class="tier-mechanical">'+esc(pc.character_name)+
        ' (seat '+esc(pc.seat)+')</td><td>baseline</td><td><pre '+
        'class="tel-fields">'+j(a)+'</pre></td></tr>';
    }
    if (pc.kind === 'static') {
      return '<tr><td class="tier-mechanical">'+esc(pc.character_name)+
        '</td><td colspan="2"><span class="tier-absent">· no '+
        'mechanical change</span></td></tr>';
    }
    const ds = (pc.deltas||[]).map(d =>
      esc(d[0])+': '+esc(d[1])).join('<br>');
    return '<tr><td class="tier-mechanical">'+esc(pc.character_name)+
      '</td><td>moved</td><td>'+ds+'</td></tr>';
  };
  const mechBody = (mech.state === 'absent')
    ? '<span class="tier-absent">— no mechanical census '+
      '(save predates Phase 2 coverage)</span>'
    : '<table><tr><th>pc</th><th>state</th><th>change</th></tr>'+
      (mech.pcs||[]).map(mechRow).join('')+'</table>'+
      (mech.trope
        ? '<div class="seqs">trope: '+esc(mech.trope.summary)+
          ' (since-meaningful '+esc(mech.trope.turns_since_meaningful)+
          ', beats '+esc(mech.trope.total_beats_fired)+')</div>'
        : '')+
      ((mech.unparseable_seqs||[]).length
        ? '<div class="tier-absent">— '+
          esc(mech.unparseable_seqs.length)+
          ' unparseable census row(s) skipped (seq '+
          mech.unparseable_seqs.map(esc).join(', ')+')</div>'
        : '');
```

and add the lane wrapper into the evidence-section string, immediately after the telemetry `</details>'+` (line 340) and before the terminal-snapshot `'<details><summary>terminal snapshot...` (line 341), matching the `+`-terminated concatenation idiom:

```javascript
      '<details><summary>mechanical state (this round)<span class="meta">'+
        esc((mech.pcs||[]).length)+' PCs · '+esc(mech.state)+
        '</span></summary><div class="ev-body">'+mechBody+
        '</div></details>'+
```

(Every adjacent lane line ends with `+`; the section finally closes `'</section>'` at `:349`. Do **not** alter the telemetry block `:297-340` or the terminal-snapshot block `:341-348`.)

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest "tests/server/test_forensics_routes.py::test_forensics_route_is_wired_and_serves_html" -v`
Expected: PASS.

- [ ] **Step 5: Manual visual check (one real save)**

Boot the server, open `/forensics`, pick a save with post-Phase-2 rounds, click a round. Confirm: the "mechanical state (this round) — N PCs · {moved|static}" lane appears collapsed; expands to a per-PC table (baseline shows absolute state, static shows "· no mechanical change", moved shows typed deltas); a pre-Phase-2 round shows exactly "— no mechanical census (save predates Phase 2 coverage)". Spec §"Three honest states, three distinct renderings — never conflated."

- [ ] **Step 6: Commit**

```bash
git add sidequest/server/static/forensics.html tests/server/test_forensics_routes.py
git commit -m "feat(forensics): per-round mechanical-diff lane (baseline/static/moved/absent)"
```

---

## Task 9: Macro-strip mechanical lane (net-new — R8: no reserved row exists)

**Why:** the spec wants a strip lane to scan a whole session and jump to the round where prose and numbers disagree. R8: there is **no** Phase-1-reserved strip row — this is net-new layout modeled on the existing single rect-per-round loop (`forensics.html:128-158`). Lowest-priority tail; must not reshape the timeline payload.

**Files:**
- Modify: `sidequest/game/forensic_query.py` (`list_saves` ~`:94` — add a save-wide `mechanical_rows` count, mirroring `telemetry_rows`)
- Modify: `sidequest/server/rest.py` (only if `mechanical_strip` needs a route — see Step 1; prefer reusing the existing turn-bundle/saves path)
- Modify: `sidequest/server/static/forensics.html` (`.lbl` count `:116-121`; a second strip rect-row in `renderStrip` `:128-158`)
- Test: `tests/game/test_forensic_query.py` (append)

- [ ] **Step 1: Decide the strip data source (bounded discovery)**

The strip renders in `selectSave()` from the timeline list, without per-round bundle fetches. `mechanical_strip(conn)` (added in Task 7) returns the per-round tri-state in ONE pass. Confirm how `selectSave` obtains its per-save data: it already fetches `/api/debug/saves` (the `list_saves` payload) and a timeline. The minimal, non-invasive choice is: add `mechanical_rows` (a save-wide count, exactly like Phase-1's `telemetry_rows`) to `list_saves` for the macro-header `.lbl`, and expose the per-round tri-state via the **already-existing** save-timeline path. If no timeline endpoint carries per-round data, the strip lane degrades to the binary present/absent derived from the per-round bundle the page already fetches on column-click — do **not** add a new fetch or reshape the timeline payload (No-Silent-Fallback: pick one source explicitly and document it in the commit).

- [ ] **Step 2: Write the failing `list_saves` count test**

```python
# append to tests/game/test_forensic_query.py
def test_list_saves_includes_mechanical_row_count(tmp_path):
    import sqlite3

    from sidequest.game.forensic_query import list_saves

    saves = tmp_path / "saves"
    db = saves / "games" / "mech" / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(
        "PRAGMA journal_mode=DELETE;"
        "CREATE TABLE session_meta (id INTEGER PRIMARY KEY CHECK (id=1),"
        " genre_slug TEXT NOT NULL, world_slug TEXT NOT NULL,"
        " created_at TEXT NOT NULL, last_played TEXT NOT NULL,"
        " schema_version INTEGER NOT NULL DEFAULT 1);"
        "INSERT INTO session_meta VALUES "
        "(1,'g','w','2026-05-18T00:00:00+00:00','2026-05-18T00:05:00+00:00',1);"
        "CREATE TABLE turn_telemetry (seq INTEGER PRIMARY KEY AUTOINCREMENT,"
        " event_seq INTEGER, round INTEGER, ts TEXT NOT NULL,"
        " component TEXT NOT NULL, event_type TEXT NOT NULL,"
        " payload_json TEXT NOT NULL);"
        "INSERT INTO turn_telemetry "
        "(event_seq,round,ts,component,event_type,payload_json) VALUES "
        "(1,1,'t','mechanical','census','{}'),"
        "(1,1,'t','intent','state_transition','{}'),"
        "(2,2,'t','mechanical','census','{}');"
    )
    con.commit()
    con.close()
    [save] = list_saves(saves)
    assert save["mechanical_rows"] == 2   # only component='mechanical'
    assert save["telemetry_rows"] == 3    # Phase-1 count unchanged (all rows)


def test_list_saves_mechanical_count_zero_when_table_missing(tmp_path):
    import sqlite3

    from sidequest.game.forensic_query import list_saves

    saves = tmp_path / "saves"
    db = saves / "games" / "old" / "save.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(
        "PRAGMA journal_mode=DELETE;"
        "CREATE TABLE session_meta (id INTEGER PRIMARY KEY CHECK (id=1),"
        " genre_slug TEXT NOT NULL, world_slug TEXT NOT NULL,"
        " created_at TEXT NOT NULL, last_played TEXT NOT NULL,"
        " schema_version INTEGER NOT NULL DEFAULT 1);"
        "INSERT INTO session_meta VALUES "
        "(1,'g','w','2026-05-18T00:00:00+00:00','2026-05-18T00:05:00+00:00',1);"
    )
    con.commit()
    con.close()
    [save] = list_saves(saves)
    assert save["mechanical_rows"] == 0   # missing table -> 0, not error
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k mechanical_row`
Expected: FAIL — `KeyError: 'mechanical_rows'`.

- [ ] **Step 4: Add the count to `list_saves`**

In `list_saves` (`forensic_query.py` ~`:60-94`), beside the existing `telemetry_rows` block, add (reusing the same already-open `_ro_connect` conn and `has_tt` table check — do not add a second `sqlite_master` query if `has_tt` is already computed):

```python
        try:
            mechanical_rows = (
                conn.execute(
                    "SELECT COUNT(*) FROM turn_telemetry "
                    "WHERE component='mechanical'"
                ).fetchone()[0]
                if has_tt
                else 0
            )
        except sqlite3.Error:
            mechanical_rows = 0
```

and include `"mechanical_rows": mechanical_rows` in the per-save dict appended ~`:94` (alongside `"telemetry_rows"`).

- [ ] **Step 5: Surface the count + strip lane in `forensics.html`**

In `selectSave()` (`.lbl` ~`:116-121`), extend the macro header to also show the mechanical count (mirror the existing `telemetry_rows` thread; look up the selected save from the already-fetched saves array — do **not** add a fetch):

```javascript
    '<section><p class="lbl">macro — '+esc(slug)+' · '+
      esc(tl.length)+' rounds · '+
      esc(sv && sv.telemetry_rows != null ? sv.telemetry_rows : 0)+
      ' telemetry · '+
      esc(sv && sv.mechanical_rows != null ? sv.mechanical_rows : 0)+
      ' mechanical · click a column</p><svg id="strip"></svg>'+
```

In `renderStrip` (`:128-158`), the strip draws one rect per round in a single row (`H = 70`). Add a thin second row beneath the event-density rects: for each round-column, a small mark colored by mechanical state — derived from the per-round bundle the page fetches on column-click (cache the tri-state as columns are visited) OR, if a per-save tri-state vector is available from the chosen Step-1 source, draw it directly. Mirror the existing rect loop exactly; keep the new row ≤ 8px tall so the existing layout is unperturbed. Use `.tier-mechanical` / `.tier-absent` colors via `setAttribute('fill', …)` as the existing rects do. Do **not** restructure the existing single-row loop — append a parallel `forEach` writing `rect`s at `y = H - 8`.

- [ ] **Step 6: Run to verify it passes**

Run: `uv run pytest tests/game/test_forensic_query.py -v -k mechanical_row`
Expected: PASS. Manual: reopen `/forensics`, pick a save → macro header reads `… · N mechanical · …` and the strip shows a second thin lane keyed by round state.

- [ ] **Step 7: Commit**

```bash
git add sidequest/game/forensic_query.py sidequest/server/static/forensics.html tests/game/test_forensic_query.py
git commit -m "feat(forensics): macro-strip mechanical lane + save-wide mechanical count (R8 net-new)"
```

---

## Task 10: Hot-path cost guard — one real turn's mechanical row count is bounded

**Why:** the spec mandates bounded payload (fixed field-set × party size). This pins a sane ceiling and is the regression tripwire if a future change makes the census fire per-segment instead of once per NARRATION (R1 gate #3).

**Files:**
- Test: `tests/server/test_turn_telemetry_wiring.py` (append; reuse the Task-5 `_drive_one_real_turn` harness)

- [ ] **Step 1: Add the measurement assertion**

```python
# append to tests/server/test_turn_telemetry_wiring.py
def test_mechanical_census_row_count_per_turn_is_bounded(tmp_path):
    """One real turn must write exactly (seated_PCs census rows + 1 session
    trope_census), NOT once-per-segment. If this explodes, the NARRATION
    gate (R1 #3) regressed — fix the gate, do not bump the bound."""
    import sqlite3

    save_db = _drive_one_real_turn(tmp_path)
    conn = sqlite3.connect(f"file:{save_db}?mode=ro", uri=True)
    try:
        census = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry "
            "WHERE component='mechanical' AND event_type='census'"
        ).fetchone()[0]
        tropes = conn.execute(
            "SELECT COUNT(*) FROM turn_telemetry "
            "WHERE component='mechanical' AND event_type='trope_census'"
        ).fetchone()[0]
    finally:
        conn.close()
    # The Phase-1 harness seats a small MP party. Generous ceiling: this
    # is a regression tripwire, not a tight bound. Once-per-turn gate means
    # tropes == (number of NARRATION turns played by the harness == 1).
    assert 0 < census <= 12, f"{census} census rows — NARRATION gate regressed?"
    assert tropes == 1, f"{tropes} trope rows — expected exactly one per turn"
```

- [ ] **Step 2: Run and record the real numbers**

Run: `uv run pytest "tests/server/test_turn_telemetry_wiring.py::test_mechanical_census_row_count_per_turn_is_bounded" -v -s`
Expected: PASS. **Record actual `census`/`tropes` in the commit body.** If `tropes > 1`, the harness plays >1 NARRATION turn (adjust the assertion to `tropes == <turns played>` and note it) — but if `census` scales with segments rather than seated PCs, the R1 NARRATION gate regressed: fix the gate, do not relax the test.

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_turn_telemetry_wiring.py
git commit -m "test(census): hot-path cost guard — one turn wrote N census rows (N=<fill>)"
```

---

## Final gate (before handoff to review)

- [ ] **Full server suite green:**

Run: `uv run pytest -q` (via `testing-runner`, `REPOS: server`)
Expected: full suite passes, 0 failed. Confirm NO pre-existing forensics/telemetry/Phase-1 test regressed (`fold_known_facts`, `fold_turn_telemetry`, the decision-telemetry lane, the never-500/byte-identity suite) and all new files are collected.

- [ ] **Lint/format clean:**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: clean. The intentional broad `except Exception` wrappers carry `# noqa: BLE001` matching the existing `watcher_hub.py` / `forensic_fold.py` convention (telemetry must never crash a turn).

- [ ] **Push the branch:**

```bash
git push -u origin feat/forensics-telemetry-phase2
```

Dev does NOT open the PR (project handoff rules). Hand off to the spec-check Architect → review → merge. The new emitter means existing live saves begin recording `component='mechanical'` rows on their next post-merge turn (forward-only, no backfill — pre-Phase-2 rounds honestly render the *absent* state).

---

## Documented out-of-scope risks (for the spec-check / spec-reconcile Architect, not tasks)

1. **`_maybe_persist_encounter_row` unconditional-commit hazard** (carried from Phase 1 memory, `watcher_hub.py:319`). It does `_event_store._conn.commit()` unconditionally, gated to `fields["field"]=="encounter"`. A census publish from inside the open C2 txn would prematurely commit it **iff** its fields set `field="encounter"` — they never do (`component="mechanical"`, no `field` key). Task 4 asserts this. **This plan does not touch `_maybe_persist_encounter_row`** (out of scope; fixing it goes exponential). Flag for the same future hardening sub-project Phase 1 flagged.
2. **Seat index is not durable (R9).** `seat` is positional in `playing_player_ids()`, may reorder across reconnect. The fold diffs on `player_id` (durable via `snapshot.player_seats`), so a reordered seat never corrupts a diff — only the displayed seat label can shift. Noted, not gated.
3. **"Previous-census-round" diff, not "previous-round" (R-design choice).** `_mechanical_for_round` diffs round N against the most recent *earlier round that has census rows* (`MAX(round) WHERE round < N`), skipping gaps where nothing was photographed (e.g. pre-Phase-2 prefix, or a crash-rolled-back round). This is bounded (2 census rounds read) and matches the spec's intent ("that PC's previous-round census") more faithfully than strict N-1 (which would spuriously baseline a PC after any gap). A PC absent from the prior census round correctly renders **baseline**, not a false zero-diff.
4. **Trope is session-scoped (R5).** The per-round `<details>` shows one trope block, not per-PC. The macro-strip "moved" includes a trope change even with no PC change — intended (a fired beat IS a mechanical event the GM should see).
5. **`round` is `interaction` (R2).** Labeled "round" in the UI for GM familiarity; it is the monotonic per-turn counter the rest of the pipeline keys on. Old saves with frozen `turn_manager.round` are unaffected — the census reads `interaction`.
6. **Payloads may embed location/inventory text.** Accepted per spec (the save is a local GM/dev artifact, not player-facing). Noted, not gated.
7. **Macro-strip is net-new (R8).** No Phase-1 placeholder was reused; the second rect-row is additive layout. If a future Tufte pass reworks the strip, this lane moves with it — it is not load-bearing for the per-round `<details>` (which is the primary discrepancy surface).

---

## Self-Review (run against the spec)

**Spec coverage:** Component 1 emitter (per-round per-PC census, fully wrapped, sealed-rounds) → Task 1 (invariant) + Task 2 (pure builder) + Task 3 (wired into the C2 NARRATION txn) + Task 4 (isolation). Component 2 read path (`build_turn_bundle.mechanical`, `?mode=ro`, missing-table=absent) → Task 7. Component 3 pure `fold_mechanical_census` (baseline/static/moved/absent, consecutive-diff, loud-skip mirroring `fold_known_facts`/`fold_turn_telemetry`) → Task 6. Component 4 UI: per-round mechanical-diff `<details>` (three distinct renderings) → Task 8; macro-strip mechanical lane → Task 9. §Testing's named criteria: per-subsystem accuracy/anti-log-absence → Task 2; pure fold (first-round baseline, static≠absent, unparseable loud-skip, honest-empty) → Task 6; mandatory wiring (real turn, non-stub) → Task 5; sealed-rounds/MP (one row per PC per round, no acting-player bias) → Task 3 + Task 5; read-only byte-identity + never-500 → Task 7; acceptance-gate human verification → deferred, mirroring the Phase-1 verification run (noted in the final gate handoff). §Observability "forensics page is the observability; loud `mechanical_census.build_failed`; row-count tell" → Task 4 (loud warnings) + Task 9 (macro count). §Migration forward-only / read-must-not-create → Task 7 (`sqlite_master` guard, `?mode=ro`, no schema change). §"Two load-bearing unknowns (plan's first two tasks)" → resolved by source audit during plan authoring, codified as Task 1 (emission point, R1) and Task 2 (canonical accessors, R3-R9), every divergence locked in the Spec Reconciliation table. No gaps.

**Placeholder scan:** the only intentional bounded fill-ins are (a) Task 3 Step 1's `<ROOM_EXPR>`/`<SNAPSHOT_EXPR>` — explicitly bounded ("use the verbatim expressions `emit_event` already binds ~`:229`/`:321`; do not introduce a new accessor"), exactly the Phase-1 plan's `<HARNESS_IMPORT>` pattern that passed review; and (b) Task 5/10's reuse of the existing `_drive_one_real_turn` harness (named, reuse-first, no new harness). Every code-bearing step contains complete code. No "TBD"/"add error handling"/"similar to Task N".

**Type/name consistency:** `PcMechanicalDiff`/`MechanicalFold`/`fold_mechanical_census`/`fold_mechanical_strip` defined in Task 6 are consumed with matching field names (`state`, `pcs`, `trope`, `unparseable_seqs`; `PcMechanicalDiff.{player_id,character_name,seat,kind,deltas,absolute}`) in Task 7's `_mechanical_for_round`/`mechanical_strip` and Task 8's `mechRow` render. `build_pc_census`/`build_trope_census`/`emit_mechanical_census`/`inventory_digest`/`inv_hash`/`seat_index` (Task 2-3) keep identical signatures across the emitter, tests, and the fold's expected payload keys (`player_id`, `character_name`, `seat`, `round`, `edge{current,max,base_max}`, `location`, `inventory[{item,qty}]`, `xp`, `level`, `acquired_advancements`, `down`, `statuses`). The empty-mechanical literal `{"state":"absent","pcs":[],"trope":None,"unparseable_seqs":[]}` is byte-identical across the four coupled sites in Task 7 (forensic_query empty-return, rest.py empty, the two route-test literals) and the `_empty_mechanical()` factory. `component="mechanical"` and `event_type` ∈ {`census`,`trope_census`} are identical across the emitter (Task 3), the read SELECT `WHERE component='mechanical'` (Task 7), the fold's `_mech_rows(..., want_type)` (Task 6), and the wiring/cost tests (Task 5/10). Consistent.
