# Beneath Sünden Plan 5 — Persistence Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the Beneath Sünden region graph, frontier, mutation overlay, and complication ledger into the existing per-session SQLite save DB, with exact round-trip reload, per-region freeze, and no floor-indexed keys.

**Architecture:** A new self-contained `sidequest/dungeon/persistence.py` `DungeonStore` operates on a *caller-supplied* SQLite connection (it never opens its own), reusing `sidequest/game/persistence.py`'s WAL/`foreign_keys` PRAGMA discipline and `PersistError` taxonomy. Five additive `CREATE TABLE IF NOT EXISTS` tables (`dungeon_map`, `dungeon_edge`, `dungeon_frontier`, `dungeon_mutation_overlay`, `dungeon_complication_ledger`). Plan 2–4's plain dataclasses get a Plan-5-created exact-inverse `to_dict()/from_dict()` pair (Approach A). The runtime caller (materializer / frontier-crossing session path) is **honestly deferred to Plan 7** — Plan 5 ships the store + a real save-DB round-trip and a documented Plan-7 wiring contract, matching the Plan 2–4 deferral discipline.

**Tech Stack:** Python 3, stdlib `sqlite3`, `dataclasses`, `uv` + `pytest` + `pyright` + `ruff`, OpenTelemetry via the project's `sidequest.telemetry.spans` registry.

**Spec:** `docs/superpowers/specs/2026-05-16-beneath-sunden-plan-5-persistence-design.md` (read it; Decisions 4/4a and §3.5 are load-bearing — edges are graph-level, persisted in their own `dungeon_edge` table, and the serde pair is *created* by Plan 5, not reused).

---

## Context an engineer with zero project knowledge needs

- **Run everything from `sidequest-server/`.** Branch off `develop` (gitflow; PRs target `develop`). Branch name: `feat/beneath-sunden-persistence`.
- Commands: `uv run pytest -v <path>`, `uv run pyright`, `uv run ruff check .`, `uv run ruff format .`.
- The region-graph models you will serialize already exist and are **frozen dataclasses** in `sidequest/dungeon/region_graph/model.py`:
  - `RegionNode(id: str, expansion_id: int, theme: str, depth_score: float | None = None)`
  - `RegionEdge(a: str, b: str, kind: str, hidden: bool = False, shortcut: bool = False)` — has `.endpoints() -> frozenset[str]`
  - `RegionGraph(entrance_id: str, nodes: dict[str, RegionNode], edges: list[RegionEdge])` — `.add_node()`, `.add_edge()` (validates endpoints loudly), `.bfs_dist()`, etc.
  - `Expansion(expansion_id: int, new_nodes: list[RegionNode], new_edges: list[RegionEdge])` — `.new_region_ids() -> set[str]`
- These models have **no serialization methods**. The only `as_dict()` in the package is on the transient OTEL *report* objects `GenerationReport` (`region_graph/invariants.py`) and `DepthReport` (`region_graph/depth.py`). **Do NOT touch the report classes. Do NOT add `from_dict` to them.** They are Plan 7's span contracts and have zero field overlap with what Plan 5 persists.
- Real generators you will reuse as test fixtures (no hand-built graphs in the property sweep):
  - `generate_expansion(*, graph, campaign_seed, expansion_id, attach_region_ids, theme_pool, config=None) -> tuple[Expansion, GenerationReport]` (`region_graph/generator.py`)
  - `attach_expansion(graph, exp) -> RegionGraph` (mutates + returns `graph`)
  - `assign_depth_scores(graph, *, campaign_seed, config=None) -> DepthReport` (`region_graph/depth.py`; replaces `graph.nodes` entries with depth-scored frozen copies, in place)
- Existing save infra to mirror (`sidequest/game/persistence.py`): module-level `SCHEMA_SQL` string run via `conn.executescript(...)`; `_configure_connection(conn)` sets `row_factory=sqlite3.Row`, `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`; error base `class PersistError(Exception)` with `NotFoundError`, `DatabaseError`, `SerializationError` subclasses; store `__init__(self, conn: sqlite3.Connection | Path)`.
- OTEL convention (`sidequest/telemetry/spans/`): one module per domain, `SPAN_X = "dotted.name"` constants, register each into `SPAN_ROUTES[name] = SpanRoute(event_type=..., component=..., extract=...)` (or `FLAT_ONLY_SPANS.add(name)`), expose `@contextmanager` `*_span()` helpers built on `Span.open(...)`, list `__all__`, and add `from .<module> import *` to `spans/__init__.py`. `tests/telemetry/test_routing_completeness.py` fails if any emitted span is neither routed nor flat-only — this is the wiring gate; `event_type="state_transition"` is a known type (used by `cookbook.py`/`persistence.py`).

### File structure (locked before tasks)

| File | Responsibility |
|---|---|
| Modify `sidequest/dungeon/region_graph/model.py` | Add exact-inverse `to_dict()/from_dict()` to `RegionNode`, `RegionEdge`, `RegionGraph` only |
| Create `sidequest/dungeon/persistence.py` | `DungeonStore` (5-table schema, API), the three Plan-5-owned payload models + their serde, error taxonomy reuse, OTEL emission |
| Create `sidequest/telemetry/spans/dungeon_persist.py` | `dungeon.persist.commit` / `ledger.add` / `ledger.resolve` span constants, routes, `@contextmanager` helpers |
| Modify `sidequest/telemetry/spans/__init__.py` | One line: `from .dungeon_persist import *` (alphabetical: after `from .dogfight import *`, before `from .emitter import Emitter`) |
| Create `tests/dungeon/test_persistence.py` | All Plan-5 tests (serde, schema, round-trip, overlay, ledger, freeze, no-floor, OTEL, property sweep, wiring contract) |

---

## Task 1: Branch + empty test module

**Files:**
- Create: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Create the branch**

Run:
```bash
git checkout develop && git pull --rebase && git checkout -b feat/beneath-sunden-persistence
```
Expected: on a new branch `feat/beneath-sunden-persistence` off the latest `develop`.

- [ ] **Step 2: Create the test module with one import-smoke test**

Create `tests/dungeon/test_persistence.py`:
```python
"""Beneath Sünden Plan 5 — persistence layer tests.

Round-trip, freeze, no-floor, overlay, ledger, OTEL, and the Plan-7
wiring contract. Real SQLite only (:memory: + temp-file for WAL).
"""

from __future__ import annotations


def test_persistence_module_importable() -> None:
    import sidequest.dungeon.persistence as persistence

    assert hasattr(persistence, "DungeonStore")
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.persistence'`.

- [ ] **Step 4: Create the minimal module so the smoke test passes**

Create `sidequest/dungeon/persistence.py`:
```python
"""Beneath Sünden Plan 5 — dungeon persistence layer.

Persists the contiguous region graph, frontier, mutation overlay, and
complication ledger into the existing per-session SQLite save DB. The
store operates on a CALLER-SUPPLIED connection (never opens its own) so
Plan 7's materializer can wrap game-save + dungeon-save in one
transaction (spec §7.5). No materializer/session caller exists yet —
honest deferral, Plan 2-4 precedent.
"""

from __future__ import annotations


class DungeonStore:
    """Defined in Task 4."""
```

- [ ] **Step 5: Run it to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add tests/dungeon/test_persistence.py sidequest/dungeon/persistence.py
git commit -m "test(dungeon): Plan 5 persistence scaffold + import smoke"
```

---

## Task 2: `to_dict()/from_dict()` on `RegionNode` and `RegionEdge`

**Files:**
- Modify: `sidequest/dungeon/region_graph/model.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
from sidequest.dungeon.region_graph.model import RegionEdge, RegionNode


def test_region_node_dict_roundtrip_exact_inverse() -> None:
    n = RegionNode(id="exp001.r0", expansion_id=1, theme="crypt", depth_score=42.5)
    assert RegionNode.from_dict(n.to_dict()) == n

    n_unscored = RegionNode(id="entrance", expansion_id=0, theme="threshold")
    d = n_unscored.to_dict()
    assert d["depth_score"] is None
    assert RegionNode.from_dict(d) == n_unscored


def test_region_edge_dict_roundtrip_exact_inverse() -> None:
    e = RegionEdge(a="entrance", b="exp001.r0", kind="secret", hidden=True, shortcut=True)
    assert RegionEdge.from_dict(e.to_dict()) == e

    plain = RegionEdge(a="x", b="y", kind="corridor")
    d = plain.to_dict()
    assert d["hidden"] is False and d["shortcut"] is False
    assert RegionEdge.from_dict(d) == plain
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k roundtrip_exact_inverse -v`
Expected: FAIL — `AttributeError: type object 'RegionNode' has no attribute 'from_dict'`.

- [ ] **Step 3: Write minimal implementation**

In `sidequest/dungeon/region_graph/model.py`, add these methods inside the existing classes (do not change any field). Add to `RegionNode`:
```python
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "expansion_id": self.expansion_id,
            "theme": self.theme,
            "depth_score": self.depth_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RegionNode:
        return cls(
            id=d["id"],
            expansion_id=d["expansion_id"],
            theme=d["theme"],
            depth_score=d["depth_score"],
        )
```
Add to `RegionEdge`:
```python
    def to_dict(self) -> dict:
        return {
            "a": self.a,
            "b": self.b,
            "kind": self.kind,
            "hidden": self.hidden,
            "shortcut": self.shortcut,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RegionEdge:
        return cls(
            a=d["a"],
            b=d["b"],
            kind=d["kind"],
            hidden=d["hidden"],
            shortcut=d["shortcut"],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k roundtrip_exact_inverse -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Type-check + lint**

Run: `uv run pyright sidequest/dungeon/region_graph/model.py && uv run ruff check sidequest/dungeon/region_graph/model.py`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest/dungeon/region_graph/model.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): RegionNode/RegionEdge to_dict/from_dict (Plan 5 Approach A)"
```

---

## Task 3: `to_dict()/from_dict()` on `RegionGraph`

**Files:**
- Modify: `sidequest/dungeon/region_graph/model.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
from sidequest.dungeon.region_graph.model import RegionGraph


def test_region_graph_dict_roundtrip_exact_inverse() -> None:
    g = RegionGraph(entrance_id="entrance")
    g.add_node(RegionNode(id="entrance", expansion_id=0, theme="threshold", depth_score=0.0))
    g.add_node(RegionNode(id="exp001.r0", expansion_id=1, theme="crypt", depth_score=10.0))
    g.add_node(RegionNode(id="exp001.r1", expansion_id=1, theme="crypt", depth_score=12.0))
    g.add_edge(RegionEdge(a="entrance", b="exp001.r0", kind="corridor"))
    g.add_edge(RegionEdge(a="exp001.r0", b="exp001.r1", kind="stairs"))
    g.add_edge(RegionEdge(a="entrance", b="exp001.r1", kind="secret", hidden=True))

    restored = RegionGraph.from_dict(g.to_dict())
    assert restored.entrance_id == g.entrance_id
    assert restored.nodes == g.nodes
    assert restored.edges == g.edges
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k region_graph_dict_roundtrip -v`
Expected: FAIL — `AttributeError: type object 'RegionGraph' has no attribute 'from_dict'`.

- [ ] **Step 3: Write minimal implementation**

Add to the `RegionGraph` class in `sidequest/dungeon/region_graph/model.py`:
```python
    def to_dict(self) -> dict:
        return {
            "entrance_id": self.entrance_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> RegionGraph:
        g = cls(entrance_id=d["entrance_id"])
        for nd in d["nodes"]:
            g.add_node(RegionNode.from_dict(nd))
        for ed in d["edges"]:
            g.add_edge(RegionEdge.from_dict(ed))
        return g
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k region_graph_dict_roundtrip -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/model.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): RegionGraph to_dict/from_dict (load-time reassembly target)"
```

---

## Task 4: `DungeonStore` skeleton + 5-table schema + `ensure_schema()`

**Files:**
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
import sqlite3

from sidequest.dungeon.persistence import DungeonStore

_EXPECTED_TABLES = {
    "dungeon_map",
    "dungeon_edge",
    "dungeon_frontier",
    "dungeon_mutation_overlay",
    "dungeon_complication_ledger",
}


def _mem_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def test_ensure_schema_creates_all_five_tables() -> None:
    conn = _mem_conn()
    DungeonStore(conn).ensure_schema()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert _EXPECTED_TABLES.issubset(names)


def test_ensure_schema_is_idempotent() -> None:
    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    store.ensure_schema()  # second call must not raise
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    assert _EXPECTED_TABLES.issubset({r["name"] for r in rows})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k ensure_schema -v`
Expected: FAIL — `TypeError: DungeonStore() takes no arguments` (or AttributeError on `ensure_schema`).

- [ ] **Step 3: Write minimal implementation**

Replace the placeholder body of `sidequest/dungeon/persistence.py` with:
```python
"""Beneath Sünden Plan 5 — dungeon persistence layer.

Persists the contiguous region graph, frontier, mutation overlay, and
complication ledger into the existing per-session SQLite save DB. The
store operates on a CALLER-SUPPLIED connection (never opens its own) so
Plan 7's materializer can wrap game-save + dungeon-save in one
transaction (spec §7.5). No materializer/session caller exists yet —
honest deferral, Plan 2-4 precedent (verified by the wiring-contract
test, not stubbed).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sidequest.game.persistence import (
    DatabaseError,
    NotFoundError,
    PersistError,
    SerializationError,
)

__all__ = [
    "DungeonStore",
    "PersistError",
    "NotFoundError",
    "DatabaseError",
    "SerializationError",
]

# Bumped only when a frozen on-disk region's bytes would change. Plan 5
# stamps it per region at commit; frozen regions are never rewritten
# (spec §7). The freeze test bumps this constant to prove immutability.
GENERATOR_VERSION = "plan5.v1"

DUNGEON_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS dungeon_map (
    region_id TEXT PRIMARY KEY,
    expansion_id INTEGER NOT NULL,
    depth_score REAL,
    generator_version TEXT NOT NULL,
    payload TEXT NOT NULL,
    mask BLOB,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dungeon_map_expansion ON dungeon_map(expansion_id);
CREATE INDEX IF NOT EXISTS idx_dungeon_map_depth ON dungeon_map(depth_score);

CREATE TABLE IF NOT EXISTS dungeon_edge (
    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    expansion_id INTEGER NOT NULL,
    a TEXT NOT NULL,
    b TEXT NOT NULL,
    kind TEXT NOT NULL,
    hidden INTEGER NOT NULL,
    shortcut INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dungeon_edge_a ON dungeon_edge(a);
CREATE INDEX IF NOT EXISTS idx_dungeon_edge_b ON dungeon_edge(b);
CREATE INDEX IF NOT EXISTS idx_dungeon_edge_expansion ON dungeon_edge(expansion_id);

CREATE TABLE IF NOT EXISTS dungeon_frontier (
    frontier_edge_id TEXT PRIMARY KEY,
    from_region_id TEXT NOT NULL,
    heading TEXT NOT NULL,
    spawn_depth_score REAL NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dungeon_frontier_from ON dungeon_frontier(from_region_id);

CREATE TABLE IF NOT EXISTS dungeon_mutation_overlay (
    mutation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dungeon_mutation_region ON dungeon_mutation_overlay(region_id);

CREATE TABLE IF NOT EXISTS dungeon_complication_ledger (
    thread_id TEXT PRIMARY KEY,
    origin_region_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at_depth_score REAL NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_dungeon_ledger_status ON dungeon_complication_ledger(status);
CREATE INDEX IF NOT EXISTS idx_dungeon_ledger_origin ON dungeon_complication_ledger(origin_region_id);
"""


class DungeonStore:
    """Dungeon persistence over a caller-supplied save-DB connection.

    Does NOT open or own the connection (Plan 7 passes the live session
    connection so its commit wraps game-save + dungeon-save in one
    transaction, spec §7.5). Does NOT autocommit — the caller owns the
    transaction boundary.
    """

    def __init__(self, conn: sqlite3.Connection | Path) -> None:
        if isinstance(conn, Path):
            raise PersistError(
                "DungeonStore requires a caller-supplied sqlite3.Connection "
                "(it never opens its own DB — Plan 7 owns the connection so "
                "game-save + dungeon-save share one transaction, spec §7.5)"
            )
        self._conn = conn

    def ensure_schema(self) -> None:
        """Idempotent additive schema creation. No migration framework —
        additive CREATE TABLE IF NOT EXISTS only (spec Decision 5)."""
        try:
            self._conn.executescript(DUNGEON_SCHEMA_SQL)
        except sqlite3.Error as exc:  # fail loud — no silent fallback
            raise DatabaseError(f"dungeon schema creation failed: {exc}") from exc
```

> **Design note (do not skip):** the `Path` branch raises rather than opening a file. The spec (Decision 3) requires a caller-supplied connection; silently opening a private DB would be the exact "silent fallback" CLAUDE.md forbids and would break Plan 7's one-transaction guarantee.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k ensure_schema -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Type-check + lint**

Run: `uv run pyright sidequest/dungeon/persistence.py && uv run ruff check sidequest/dungeon/persistence.py`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): DungeonStore + 5-table additive schema (Plan 5 §3)"
```

---

## Task 5: No-floor schema-introspection gate

**Files:**
- Test: `tests/dungeon/test_persistence.py`

This is a deliberate completeness gate (parent spec §5/§11 hard constraint), the Plan-5 analogue of Plan 4's exhaustiveness contract — a failure here means someone reintroduced the explicitly-rejected floor concept.

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
import re


def test_no_floor_indexed_keys_anywhere() -> None:
    """Spec §5/§11: nothing in the dungeon schema may be keyed by or
    named for a 'floor'. Introspect every table/column/index name."""
    conn = _mem_conn()
    DungeonStore(conn).ensure_schema()
    floor = re.compile(r"floor", re.IGNORECASE)

    objects = conn.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE name LIKE 'dungeon_%' OR name LIKE 'idx_dungeon_%'"
    ).fetchall()
    assert objects, "schema introspection returned nothing — schema not created"
    for row in objects:
        assert not floor.search(row["name"]), f"floor in object name: {row['name']}"
        assert not floor.search(row["sql"] or ""), f"floor in DDL: {row['sql']}"
```

- [ ] **Step 2: Run test to verify it passes immediately**

Run: `uv run pytest tests/dungeon/test_persistence.py -k no_floor -v`
Expected: PASS (1 passed) — the schema from Task 4 already contains no `floor`. (This test has no implementation step; it is a standing gate. If it ever fails, the fix is to remove the floor concept, never to weaken the test.)

- [ ] **Step 3: Commit**

```bash
git add tests/dungeon/test_persistence.py
git commit -m "test(dungeon): no-floor schema-introspection gate (Plan 5 §5/§11)"
```

---

## Task 6: `commit_expansion()` + `load_map()` — region/edge round-trip

**Files:**
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

`commit_expansion` takes the `Expansion` (it knows which edges are new and the `expansion_id`) **and** the post-`assign_depth_scores` `RegionGraph` (it holds the depth-scored node instances — `assign_depth_scores` replaces `graph.nodes` entries but the `Expansion.new_nodes` list still holds the pre-score copies). Edges have no `expansion_id` field, so the owning expansion is taken from the `Expansion` argument.

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
import tempfile
from pathlib import Path as _Path

from sidequest.dungeon.region_graph.generator import (
    attach_expansion,
    generate_expansion,
)
from sidequest.dungeon.region_graph.depth import assign_depth_scores
from sidequest.dungeon.region_graph.model import Expansion


def _seed_graph() -> RegionGraph:
    g = RegionGraph(entrance_id="entrance")
    g.add_node(RegionNode(id="entrance", expansion_id=0, theme="threshold"))
    return g


def _generate_and_attach(
    g: RegionGraph, *, campaign_seed: int, expansion_id: int, attach_ids: list[str]
) -> Expansion:
    exp, _ = generate_expansion(
        graph=g,
        campaign_seed=campaign_seed,
        expansion_id=expansion_id,
        attach_region_ids=attach_ids,
        theme_pool=["crypt", "catacomb", "flooded"],
    )
    attach_expansion(g, exp)
    assign_depth_scores(g, campaign_seed=campaign_seed)
    return exp


def _file_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def test_commit_then_load_map_roundtrips_graph_in_memory() -> None:
    g = _seed_graph()
    exp = _generate_and_attach(g, campaign_seed=7, expansion_id=1, attach_ids=["entrance"])

    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    store.commit_expansion(exp, g)
    conn.commit()

    reloaded = store.load_map(entrance_id="entrance")
    assert reloaded.nodes == g.nodes
    assert sorted(reloaded.edges, key=repr) == sorted(g.edges, key=repr)


def test_commit_then_load_map_roundtrips_over_wal_file() -> None:
    g = _seed_graph()
    exp = _generate_and_attach(g, campaign_seed=11, expansion_id=1, attach_ids=["entrance"])

    with tempfile.TemporaryDirectory() as d:
        db = str(_Path(d) / "save.db")
        c1 = _file_conn(db)
        s1 = DungeonStore(c1)
        s1.ensure_schema()
        s1.commit_expansion(exp, g)
        c1.commit()
        c1.close()

        c2 = _file_conn(db)
        reloaded = DungeonStore(c2).load_map(entrance_id="entrance")
        c2.close()

    assert reloaded.nodes == g.nodes
    assert sorted(reloaded.edges, key=repr) == sorted(g.edges, key=repr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k load_map -v`
Expected: FAIL — `AttributeError: 'DungeonStore' object has no attribute 'commit_expansion'`.

- [ ] **Step 3: Write minimal implementation**

Add to `sidequest/dungeon/persistence.py` — imports at top:
```python
import json

from sidequest.dungeon.region_graph.model import (
    Expansion,
    RegionEdge,
    RegionGraph,
    RegionNode,
)
```
Add these methods to `DungeonStore`:
```python
    def commit_expansion(
        self,
        expansion: Expansion,
        graph: RegionGraph,
        *,
        generator_version: str = GENERATOR_VERSION,
    ) -> None:
        """Persist one expansion's regions + edges WITHIN the caller's
        transaction (no autocommit — Plan 7 owns the txn boundary,
        spec §7.5). Regions are read from `graph` (depth-scored); edge
        ownership is taken from `expansion`.
        """
        try:
            for node in expansion.new_nodes:
                live = graph.nodes.get(node.id)
                if live is None:
                    raise NotFoundError(
                        f"expansion region {node.id!r} is not in the graph "
                        f"(commit must run after attach_expansion)"
                    )
                self._conn.execute(
                    "INSERT INTO dungeon_map "
                    "(region_id, expansion_id, depth_score, generator_version, payload) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        live.id,
                        live.expansion_id,
                        live.depth_score,
                        generator_version,
                        json.dumps(live.to_dict()),
                    ),
                )
            for edge in expansion.new_edges:
                self._conn.execute(
                    "INSERT INTO dungeon_edge "
                    "(expansion_id, a, b, kind, hidden, shortcut, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        expansion.expansion_id,
                        edge.a,
                        edge.b,
                        edge.kind,
                        int(edge.hidden),
                        int(edge.shortcut),
                        json.dumps(edge.to_dict()),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            # A region_id already committed = a re-commit of a frozen
            # expansion. Fail loud (spec §7: frozen regions never rewritten).
            raise PersistError(
                f"dungeon expansion {expansion.expansion_id} re-commit "
                f"violates the freeze contract: {exc}"
            ) from exc
        except sqlite3.Error as exc:
            raise DatabaseError(f"commit_expansion failed: {exc}") from exc

    def load_map(self, *, entrance_id: str) -> RegionGraph:
        """Rebuild the full RegionGraph from dungeon_map + dungeon_edge.
        Nodes first (RegionGraph.add_edge validates endpoints loudly)."""
        try:
            node_rows = self._conn.execute(
                "SELECT payload FROM dungeon_map"
            ).fetchall()
            edge_rows = self._conn.execute(
                "SELECT payload FROM dungeon_edge ORDER BY edge_id"
            ).fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"load_map query failed: {exc}") from exc

        g = RegionGraph(entrance_id=entrance_id)
        try:
            for r in node_rows:
                g.add_node(RegionNode.from_dict(json.loads(r["payload"])))
            for r in edge_rows:
                g.add_edge(RegionEdge.from_dict(json.loads(r["payload"])))
        except (json.JSONDecodeError, KeyError) as exc:
            raise SerializationError(f"corrupt dungeon payload: {exc}") from exc
        return g
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k load_map -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Type-check + lint**

Run: `uv run pyright sidequest/dungeon/persistence.py && uv run ruff check sidequest/dungeon/persistence.py`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): commit_expansion + load_map region/edge round-trip (Plan 5 §3.1/§3.5)"
```

---

## Task 7: Frontier persistence

**Files:**
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
from sidequest.dungeon.persistence import FrontierEdge


def test_frontier_roundtrip() -> None:
    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()

    fe = FrontierEdge(
        frontier_edge_id="f1",
        from_region_id="exp001.r0",
        heading="down-and-east",
        spawn_depth_score=30.0,
    )
    store.put_frontier(fe)
    conn.commit()

    loaded = store.load_frontier()
    assert loaded == [fe]
    assert FrontierEdge.from_dict(fe.to_dict()) == fe
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k frontier -v`
Expected: FAIL — `ImportError: cannot import name 'FrontierEdge'`.

- [ ] **Step 3: Write minimal implementation**

Add to `sidequest/dungeon/persistence.py` — a dataclass import and the model + methods. Add `from dataclasses import dataclass` to the imports, add `"FrontierEdge"` to `__all__`, then:
```python
@dataclass(frozen=True)
class FrontierEdge:
    """An unexpanded frontier edge — where, and at what depth, an
    expansion would spawn. Plan 7's materializer is the producer."""

    frontier_edge_id: str
    from_region_id: str
    heading: str
    spawn_depth_score: float

    def to_dict(self) -> dict:
        return {
            "frontier_edge_id": self.frontier_edge_id,
            "from_region_id": self.from_region_id,
            "heading": self.heading,
            "spawn_depth_score": self.spawn_depth_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FrontierEdge:
        return cls(
            frontier_edge_id=d["frontier_edge_id"],
            from_region_id=d["from_region_id"],
            heading=d["heading"],
            spawn_depth_score=d["spawn_depth_score"],
        )
```
Add to `DungeonStore`:
```python
    def put_frontier(self, fe: FrontierEdge) -> None:
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO dungeon_frontier "
                "(frontier_edge_id, from_region_id, heading, spawn_depth_score, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    fe.frontier_edge_id,
                    fe.from_region_id,
                    fe.heading,
                    fe.spawn_depth_score,
                    json.dumps(fe.to_dict()),
                ),
            )
        except sqlite3.Error as exc:
            raise DatabaseError(f"put_frontier failed: {exc}") from exc

    def load_frontier(self) -> list[FrontierEdge]:
        try:
            rows = self._conn.execute(
                "SELECT payload FROM dungeon_frontier ORDER BY frontier_edge_id"
            ).fetchall()
            return [FrontierEdge.from_dict(json.loads(r["payload"])) for r in rows]
        except sqlite3.Error as exc:
            raise DatabaseError(f"load_frontier failed: {exc}") from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise SerializationError(f"corrupt frontier payload: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k frontier -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): frontier persistence (Plan 5 §3.2)"
```

---

## Task 8: Mutation overlay — append-only, ordered replay, survives reload

**Files:**
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
from sidequest.dungeon.persistence import DungeonMutation


def test_mutation_overlay_append_only_ordered_and_survives_reload() -> None:
    with tempfile.TemporaryDirectory() as d:
        db = str(_Path(d) / "save.db")
        c1 = _file_conn(db)
        s1 = DungeonStore(c1)
        s1.ensure_schema()
        s1.record_mutation("exp001.r0", "trap_sprung", {"trap": "scything_blade"})
        s1.record_mutation("exp001.r0", "looted", {"item": "ring"})
        s1.record_mutation("exp001.r1", "collapsed", {})
        c1.commit()
        c1.close()

        c2 = _file_conn(db)
        muts = DungeonStore(c2).load_mutations()
        c2.close()

    # append-only + deterministic replay order (mutation_id ascending)
    assert [m.kind for m in muts] == ["trap_sprung", "looted", "collapsed"]
    assert muts[0].region_id == "exp001.r0"
    assert muts[0].payload == {"trap": "scything_blade"}
    assert DungeonMutation.from_dict(muts[1].to_dict()) == muts[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k mutation_overlay -v`
Expected: FAIL — `ImportError: cannot import name 'DungeonMutation'`.

- [ ] **Step 3: Write minimal implementation**

Add to `sidequest/dungeon/persistence.py` (`"DungeonMutation"` into `__all__`):
```python
@dataclass(frozen=True)
class DungeonMutation:
    """One append-only mutation fact (sprung trap, looted room,
    collapse, resolved set-piece). Never updated or deleted; load
    replays in mutation_id order over the base map."""

    region_id: str
    kind: str
    payload: dict

    def to_dict(self) -> dict:
        return {"region_id": self.region_id, "kind": self.kind, "payload": self.payload}

    @classmethod
    def from_dict(cls, d: dict) -> DungeonMutation:
        return cls(region_id=d["region_id"], kind=d["kind"], payload=d["payload"])
```
Add to `DungeonStore`:
```python
    def record_mutation(self, region_id: str, kind: str, payload: dict) -> None:
        try:
            self._conn.execute(
                "INSERT INTO dungeon_mutation_overlay (region_id, kind, payload) "
                "VALUES (?, ?, ?)",
                (region_id, kind, json.dumps(payload)),
            )
        except sqlite3.Error as exc:
            raise DatabaseError(f"record_mutation failed: {exc}") from exc

    def load_mutations(self) -> list[DungeonMutation]:
        try:
            rows = self._conn.execute(
                "SELECT region_id, kind, payload FROM dungeon_mutation_overlay "
                "ORDER BY mutation_id"
            ).fetchall()
            return [
                DungeonMutation(
                    region_id=r["region_id"],
                    kind=r["kind"],
                    payload=json.loads(r["payload"]),
                )
                for r in rows
            ]
        except sqlite3.Error as exc:
            raise DatabaseError(f"load_mutations failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SerializationError(f"corrupt mutation payload: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k mutation_overlay -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): append-only mutation overlay + ordered replay (Plan 5 §3.3)"
```

---

## Task 9: Complication ledger — open/resolve, status query, accumulation across expansions

**Files:**
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
from sidequest.dungeon.persistence import ComplicationThread


def test_complication_ledger_open_resolve_and_accumulation() -> None:
    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()

    # expansion 1 lights two threads
    store.open_thread(ComplicationThread(
        thread_id="t1", origin_region_id="exp001.r0", kind="trope",
        status="open", started_at_depth_score=10.0, payload={"trope": "sacrifice_priest"},
    ))
    store.open_thread(ComplicationThread(
        thread_id="t2", origin_region_id="exp001.r1", kind="quest",
        status="open", started_at_depth_score=12.0, payload={"quest": "drowned_bell"},
    ))
    conn.commit()
    assert {t.thread_id for t in store.open_threads()} == {"t1", "t2"}

    # expansion 2 lights a third — accumulation observable (spec §7.1)
    store.open_thread(ComplicationThread(
        thread_id="t3", origin_region_id="exp002.r0", kind="trope",
        status="open", started_at_depth_score=30.0, payload={},
    ))
    conn.commit()
    assert len(store.open_threads()) == 3  # nothing cleared by pushing deeper

    # resolution is the ONLY thing that shrinks the ledger
    store.resolve_thread("t1")
    conn.commit()
    open_ids = {t.thread_id for t in store.open_threads()}
    assert open_ids == {"t2", "t3"}
    assert ComplicationThread.from_dict(
        store.get_thread("t1").to_dict()
    ).status == "resolved"


def test_resolve_unknown_thread_fails_loud() -> None:
    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    import pytest

    with pytest.raises(NotFoundError):
        store.resolve_thread("does-not-exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k complication_ledger -v`
Expected: FAIL — `ImportError: cannot import name 'ComplicationThread'`.

- [ ] **Step 3: Write minimal implementation**

Add to `sidequest/dungeon/persistence.py` (`"ComplicationThread"` into `__all__`):
```python
@dataclass(frozen=True)
class ComplicationThread:
    """A started-but-unresolved trope/quest thread (spec §7.1 — the
    spine). Starts at attach (Plan 6/7 produce it), persists until
    player-resolved. Plan 5 owns storage + status transitions only."""

    thread_id: str
    origin_region_id: str
    kind: str
    status: str
    started_at_depth_score: float
    payload: dict

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "origin_region_id": self.origin_region_id,
            "kind": self.kind,
            "status": self.status,
            "started_at_depth_score": self.started_at_depth_score,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ComplicationThread:
        return cls(
            thread_id=d["thread_id"],
            origin_region_id=d["origin_region_id"],
            kind=d["kind"],
            status=d["status"],
            started_at_depth_score=d["started_at_depth_score"],
            payload=d["payload"],
        )
```
Add to `DungeonStore`:
```python
    def open_thread(self, thread: ComplicationThread) -> None:
        try:
            self._conn.execute(
                "INSERT INTO dungeon_complication_ledger "
                "(thread_id, origin_region_id, kind, status, "
                " started_at_depth_score, payload) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    thread.thread_id,
                    thread.origin_region_id,
                    thread.kind,
                    thread.status,
                    thread.started_at_depth_score,
                    json.dumps(thread.payload),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise PersistError(
                f"thread {thread.thread_id!r} already open: {exc}"
            ) from exc
        except sqlite3.Error as exc:
            raise DatabaseError(f"open_thread failed: {exc}") from exc

    def get_thread(self, thread_id: str) -> ComplicationThread:
        row = self._conn.execute(
            "SELECT thread_id, origin_region_id, kind, status, "
            "started_at_depth_score, payload FROM dungeon_complication_ledger "
            "WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"complication thread {thread_id!r} not found")
        return ComplicationThread(
            thread_id=row["thread_id"],
            origin_region_id=row["origin_region_id"],
            kind=row["kind"],
            status=row["status"],
            started_at_depth_score=row["started_at_depth_score"],
            payload=json.loads(row["payload"]),
        )

    def resolve_thread(self, thread_id: str) -> None:
        cur = self._conn.execute(
            "UPDATE dungeon_complication_ledger "
            "SET status = 'resolved', resolved_at = datetime('now') "
            "WHERE thread_id = ?",
            (thread_id,),
        )
        if cur.rowcount == 0:
            raise NotFoundError(
                f"cannot resolve unknown complication thread {thread_id!r}"
            )

    def open_threads(self) -> list[ComplicationThread]:
        rows = self._conn.execute(
            "SELECT thread_id, origin_region_id, kind, status, "
            "started_at_depth_score, payload FROM dungeon_complication_ledger "
            "WHERE status = 'open' ORDER BY thread_id"
        ).fetchall()
        return [
            ComplicationThread(
                thread_id=r["thread_id"],
                origin_region_id=r["origin_region_id"],
                kind=r["kind"],
                status=r["status"],
                started_at_depth_score=r["started_at_depth_score"],
                payload=json.loads(r["payload"]),
            )
            for r in rows
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k complication_ledger -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Type-check + lint**

Run: `uv run pyright sidequest/dungeon/persistence.py && uv run ruff check sidequest/dungeon/persistence.py`
Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): complication ledger open/resolve + accumulation (Plan 5 §3.4/§7.1)"
```

---

## Task 10: Generator-version freeze — frozen region untouched after version bump

**Files:**
- Test: `tests/dungeon/test_persistence.py`

Spec §7: a committed region is frozen — never rewritten, even if the generator version changes mid-campaign. The re-commit path already raises (Task 6 `IntegrityError` → `PersistError`). This test proves the on-disk bytes are immutable across a `generator_version` change.

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
def test_frozen_region_untouched_after_generator_version_bump() -> None:
    g = _seed_graph()
    exp = _generate_and_attach(g, campaign_seed=3, expansion_id=1, attach_ids=["entrance"])

    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    store.commit_expansion(exp, g, generator_version="plan5.v1")
    conn.commit()

    before = conn.execute(
        "SELECT region_id, payload, generator_version FROM dungeon_map "
        "ORDER BY region_id"
    ).fetchall()
    before_snap = [(r["region_id"], r["payload"], r["generator_version"]) for r in before]

    # generator version changes mid-campaign; re-committing the SAME
    # frozen expansion must fail loud, never silently rewrite.
    import pytest

    with pytest.raises(PersistError):
        store.commit_expansion(exp, g, generator_version="plan5.v2")
    conn.rollback()

    after = conn.execute(
        "SELECT region_id, payload, generator_version FROM dungeon_map "
        "ORDER BY region_id"
    ).fetchall()
    after_snap = [(r["region_id"], r["payload"], r["generator_version"]) for r in after]

    assert after_snap == before_snap  # bytes + version unchanged (frozen)
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k frozen_region -v`
Expected: PASS (1 passed) — the freeze contract from Task 6 already enforces this. If it fails, the fix is in `commit_expansion` (re-commit must raise before any write), never weakening this test.

- [ ] **Step 3: Commit**

```bash
git add tests/dungeon/test_persistence.py
git commit -m "test(dungeon): frozen-region immutability across generator-version bump (Plan 5 §7)"
```

---

## Task 11: OTEL spans — `dungeon_persist.py` registered + emitted + routing gate green

**Files:**
- Create: `sidequest/telemetry/spans/dungeon_persist.py`
- Modify: `sidequest/telemetry/spans/__init__.py`
- Modify: `sidequest/dungeon/persistence.py`
- Test: `tests/dungeon/test_persistence.py`

Spec §6: Plan 5 emits only spans it has *real callers* for — `dungeon.persist.commit`, `ledger.add`, `ledger.resolve` — from the store methods. The materializer spans are Plan 7's (not emitted here).

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
def test_dungeon_persist_spans_registered_and_routed() -> None:
    from sidequest.telemetry.spans import FLAT_ONLY_SPANS, SPAN_ROUTES
    from sidequest.telemetry.spans.dungeon_persist import (
        SPAN_DUNGEON_PERSIST_COMMIT,
        SPAN_LEDGER_ADD,
        SPAN_LEDGER_RESOLVE,
    )

    for name in (SPAN_DUNGEON_PERSIST_COMMIT, SPAN_LEDGER_ADD, SPAN_LEDGER_RESOLVE):
        assert name in SPAN_ROUTES or name in FLAT_ONLY_SPANS, (
            f"{name} has no routing decision — routing-completeness gate "
            f"will fail"
        )


def test_commit_and_ledger_emit_spans() -> None:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
        ConsoleSpanExporter,
    )

    captured: list[str] = []

    class _Capture(ConsoleSpanExporter):
        def export(self, spans):  # type: ignore[override]
            captured.extend(s.name for s in spans)
            return super().export(spans)

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_Capture()))
    trace.set_tracer_provider(provider)

    g = _seed_graph()
    exp = _generate_and_attach(g, campaign_seed=5, expansion_id=1, attach_ids=["entrance"])
    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    store.commit_expansion(exp, g)
    store.open_thread(ComplicationThread(
        thread_id="t1", origin_region_id="exp001.r0", kind="trope",
        status="open", started_at_depth_score=10.0, payload={},
    ))
    store.resolve_thread("t1")

    assert "dungeon.persist.commit" in captured
    assert "ledger.add" in captured
    assert "ledger.resolve" in captured
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/test_persistence.py -k "spans_registered or emit_spans" -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.telemetry.spans.dungeon_persist'`.

- [ ] **Step 3: Create the spans module**

Create `sidequest/telemetry/spans/dungeon_persist.py` (mirrors `cookbook.py` exactly):
```python
"""Dungeon persistence spans (Beneath Sünden Plan 5 §6).

Only spans with a REAL store-method caller live here: commit, ledger
add, ledger resolve. The materializer / frontier-expand spans are
Plan 7's — emitting them here with no caller would be the exact
Illusionism the GM panel exists to catch (spec §6).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ._core import SPAN_ROUTES, SpanRoute
from .span import Span

SPAN_DUNGEON_PERSIST_COMMIT = "dungeon.persist.commit"
SPAN_LEDGER_ADD = "ledger.add"
SPAN_LEDGER_RESOLVE = "ledger.resolve"


def _attr(field: str):
    return lambda span, f=field: (span.attributes or {}).get(f)


SPAN_ROUTES[SPAN_DUNGEON_PERSIST_COMMIT] = SpanRoute(
    event_type="state_transition",
    component="dungeon",
    extract=lambda s: {
        "field": "dungeon_map",
        "op": "commit_expansion",
        "expansion_id": _attr("expansion_id")(s),
        "regions": _attr("regions")(s),
        "edges": _attr("edges")(s),
        "generator_version": _attr("generator_version")(s),
    },
)
SPAN_ROUTES[SPAN_LEDGER_ADD] = SpanRoute(
    event_type="state_transition",
    component="dungeon",
    extract=lambda s: {
        "field": "complication_ledger",
        "op": "open_thread",
        "thread_id": _attr("thread_id")(s),
        "kind": _attr("kind")(s),
        "origin_region_id": _attr("origin_region_id")(s),
    },
)
SPAN_ROUTES[SPAN_LEDGER_RESOLVE] = SpanRoute(
    event_type="state_transition",
    component="dungeon",
    extract=lambda s: {
        "field": "complication_ledger",
        "op": "resolve_thread",
        "thread_id": _attr("thread_id")(s),
    },
)


@contextmanager
def dungeon_persist_commit_span(
    *,
    expansion_id: int,
    regions: int,
    edges: int,
    generator_version: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_DUNGEON_PERSIST_COMMIT,
        {
            "expansion_id": expansion_id,
            "regions": regions,
            "edges": edges,
            "generator_version": generator_version,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def ledger_add_span(
    *,
    thread_id: str,
    kind: str,
    origin_region_id: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_LEDGER_ADD,
        {
            "thread_id": thread_id,
            "kind": kind,
            "origin_region_id": origin_region_id,
            **attrs,
        },
        tracer_override=_tracer,
    ) as span:
        yield span


@contextmanager
def ledger_resolve_span(
    *,
    thread_id: str,
    _tracer: trace.Tracer | None = None,
    **attrs: Any,
) -> Iterator[trace.Span]:
    with Span.open(
        SPAN_LEDGER_RESOLVE,
        {"thread_id": thread_id, **attrs},
        tracer_override=_tracer,
    ) as span:
        yield span


__all__ = [
    "SPAN_DUNGEON_PERSIST_COMMIT",
    "SPAN_LEDGER_ADD",
    "SPAN_LEDGER_RESOLVE",
    "dungeon_persist_commit_span",
    "ledger_add_span",
    "ledger_resolve_span",
]
```

- [ ] **Step 4: Register the module**

In `sidequest/telemetry/spans/__init__.py`, add this line in alphabetical position (immediately after `from .dogfight import *  # noqa: F401, F403` and before `from .emitter import Emitter  # noqa: F401`):
```python
from .dungeon_persist import *  # noqa: F401, F403
```

- [ ] **Step 5: Emit the spans from the store methods**

In `sidequest/dungeon/persistence.py`, import the helpers:
```python
from sidequest.telemetry.spans.dungeon_persist import (
    dungeon_persist_commit_span,
    ledger_add_span,
    ledger_resolve_span,
)
```
Wrap the body of `commit_expansion` so the whole insert runs inside the span and the span records counts (open the span first, do the inserts inside the `with`):
```python
    def commit_expansion(
        self,
        expansion: Expansion,
        graph: RegionGraph,
        *,
        generator_version: str = GENERATOR_VERSION,
    ) -> None:
        with dungeon_persist_commit_span(
            expansion_id=expansion.expansion_id,
            regions=len(expansion.new_nodes),
            edges=len(expansion.new_edges),
            generator_version=generator_version,
        ):
            try:
                for node in expansion.new_nodes:
                    live = graph.nodes.get(node.id)
                    if live is None:
                        raise NotFoundError(
                            f"expansion region {node.id!r} is not in the graph "
                            f"(commit must run after attach_expansion)"
                        )
                    self._conn.execute(
                        "INSERT INTO dungeon_map "
                        "(region_id, expansion_id, depth_score, generator_version, payload) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            live.id,
                            live.expansion_id,
                            live.depth_score,
                            generator_version,
                            json.dumps(live.to_dict()),
                        ),
                    )
                for edge in expansion.new_edges:
                    self._conn.execute(
                        "INSERT INTO dungeon_edge "
                        "(expansion_id, a, b, kind, hidden, shortcut, payload) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            expansion.expansion_id,
                            edge.a,
                            edge.b,
                            edge.kind,
                            int(edge.hidden),
                            int(edge.shortcut),
                            json.dumps(edge.to_dict()),
                        ),
                    )
            except sqlite3.IntegrityError as exc:
                raise PersistError(
                    f"dungeon expansion {expansion.expansion_id} re-commit "
                    f"violates the freeze contract: {exc}"
                ) from exc
            except sqlite3.Error as exc:
                raise DatabaseError(f"commit_expansion failed: {exc}") from exc
```
Wrap `open_thread`'s insert in `ledger_add_span(thread_id=thread.thread_id, kind=thread.kind, origin_region_id=thread.origin_region_id):` and `resolve_thread`'s update in `ledger_resolve_span(thread_id=thread_id):` — open the span, then run the existing body inside the `with` (keep the existing `NotFoundError`/`IntegrityError` handling unchanged inside).

- [ ] **Step 6: Run the Plan-5 OTEL tests + the project routing-completeness gate**

Run:
```bash
uv run pytest tests/dungeon/test_persistence.py -k "spans_registered or emit_spans" -v
uv run pytest tests/telemetry/test_routing_completeness.py -v
```
Expected: all PASS. `test_routing_completeness.py` proves the three new spans are routed (the project-wide wiring gate — CLAUDE.md "every subsystem decision emits OTEL").

- [ ] **Step 7: Type-check + lint**

Run: `uv run pyright sidequest/dungeon/persistence.py sidequest/telemetry/spans/dungeon_persist.py && uv run ruff check sidequest/`
Expected: 0 errors.

- [ ] **Step 8: Commit**

```bash
git add sidequest/telemetry/spans/dungeon_persist.py sidequest/telemetry/spans/__init__.py sidequest/dungeon/persistence.py tests/dungeon/test_persistence.py
git commit -m "feat(dungeon): OTEL spans for commit/ledger + routing registration (Plan 5 §6)"
```

---

## Task 12: `to_dict()/from_dict()` exact-inverse property sweep (real generators)

**Files:**
- Test: `tests/dungeon/test_persistence.py`

Spec §11: the central invariant — `from_dict(to_dict(x)) == x` for every persisted region/edge across a Plan-2/3 seed sweep, using the real generators as fixtures (no hand-built graphs).

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
import pytest


@pytest.mark.parametrize("campaign_seed", [1, 2, 7, 13, 24301, 99991])
def test_serde_exact_inverse_over_seed_sweep(campaign_seed: int) -> None:
    """Generate → attach → depth-score a real 3-expansion chain, persist,
    reload, and assert the rebuilt graph is identical (spec §11)."""
    g = _seed_graph()
    exp1 = _generate_and_attach(
        g, campaign_seed=campaign_seed, expansion_id=1, attach_ids=["entrance"]
    )
    deep_ids = [n.id for n in exp1.new_nodes][:2] or ["entrance"]
    exp2 = _generate_and_attach(
        g, campaign_seed=campaign_seed, expansion_id=2,
        attach_ids=(deep_ids + ["entrance"])[:2],
    )
    deeper = [n.id for n in exp2.new_nodes][:2] or deep_ids
    exp3 = _generate_and_attach(
        g, campaign_seed=campaign_seed, expansion_id=3,
        attach_ids=(deeper + deep_ids)[:2],
    )

    conn = _mem_conn()
    store = DungeonStore(conn)
    store.ensure_schema()
    for exp in (exp1, exp2, exp3):
        store.commit_expansion(exp, g)
    conn.commit()

    reloaded = store.load_map(entrance_id="entrance")
    assert reloaded.nodes == g.nodes
    assert sorted(reloaded.edges, key=repr) == sorted(g.edges, key=repr)
    # every node carries its frozen depth_score through the round-trip
    assert all(
        reloaded.nodes[rid].depth_score == g.nodes[rid].depth_score
        for rid in g.nodes
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k serde_exact_inverse -v`
Expected: PASS (6 passed) — the serde from Tasks 2–3 and round-trip from Task 6 already satisfy this; this is the spec §11 contract lock across the real generator surface. If a seed fails, the bug is in `to_dict/from_dict` or `load_map` ordering — fix there, never narrow the seed list.

> Note: `24301` is in the sweep deliberately — it is the `seed ^ 0x5EED` fixed-point gotcha from the Beneath Sünden carry-forward; persistence must round-trip it like any other seed.

- [ ] **Step 3: Commit**

```bash
git add tests/dungeon/test_persistence.py
git commit -m "test(dungeon): to_dict/from_dict exact-inverse property sweep (Plan 5 §11)"
```

---

## Task 13: Plan-7 wiring contract — real save-DB-shaped connection

**Files:**
- Test: `tests/dungeon/test_persistence.py`

CLAUDE.md mandates a wiring test. Plan 5's runtime caller (materializer / frontier-crossing) is Plan 7's — so Plan 5's wiring contract is: the store round-trips against a connection configured **identically to the real save DB** (`sidequest.game.persistence._configure_connection`), proving it will drop into the live save path Plan 7 builds. The materializer integration test itself is explicitly Plan 7's (documented deferral, Plan 2–4 precedent).

- [ ] **Step 1: Write the failing test**

Append to `tests/dungeon/test_persistence.py`:
```python
def test_wiring_contract_runs_on_real_save_db_connection() -> None:
    """Plan-7 deferral contract: DungeonStore must work on a connection
    configured exactly like the real save DB. We reuse the production
    _configure_connection so a PRAGMA drift in game/persistence.py
    breaks THIS test — proving Plan 7 can pass it the live connection.
    """
    from sidequest.game.persistence import _configure_connection

    with tempfile.TemporaryDirectory() as d:
        db = str(_Path(d) / "caverns_beneath_sunden.db")
        conn = sqlite3.connect(db)
        _configure_connection(conn)  # the REAL save-DB PRAGMA contract

        g = _seed_graph()
        exp = _generate_and_attach(
            g, campaign_seed=42, expansion_id=1, attach_ids=["entrance"]
        )
        store = DungeonStore(conn)
        store.ensure_schema()
        store.commit_expansion(exp, g)
        conn.commit()

        reloaded = store.load_map(entrance_id="entrance")
        conn.close()

    assert reloaded.nodes == g.nodes
    assert sorted(reloaded.edges, key=repr) == sorted(g.edges, key=repr)


def test_dungeonstore_refuses_to_open_its_own_db() -> None:
    """Spec Decision 3: the store never owns the connection. A Path
    argument must fail loud, not silently open a private DB (that would
    break Plan 7's one-transaction guarantee, spec §7.5)."""
    import pytest

    with pytest.raises(PersistError):
        DungeonStore(_Path("/tmp/should-not-be-opened.db"))
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/test_persistence.py -k "wiring_contract or refuses_to_open" -v`
Expected: PASS (2 passed). These lock the two halves of the Plan-7 deferral contract: (a) the store is drop-in compatible with the real save-DB connection, (b) it refuses to own a connection.

- [ ] **Step 3: Add the deferral marker to the module docstring**

Confirm the `sidequest/dungeon/persistence.py` module docstring already states the Plan-7 deferral (it does, from Task 4). No code change — verify the sentence "No materializer/session caller exists yet — honest deferral, Plan 2-4 precedent (verified by the wiring-contract test, not stubbed)." is present. If absent, add it.

- [ ] **Step 4: Commit**

```bash
git add tests/dungeon/test_persistence.py
git commit -m "test(dungeon): Plan-7 wiring contract — real save-DB connection + no-self-open (Plan 5 §6/§7)"
```

---

## Task 14: Full-suite green + handoff

**Files:** none (verification only)

- [ ] **Step 1: Run the full dungeon + telemetry suites**

Run:
```bash
uv run pytest tests/dungeon/ tests/telemetry/test_routing_completeness.py -v
```
Expected: all PASS, including the pre-existing Plan 1–4 dungeon tests (Plan 5 is purely additive — `model.py` only gained methods; no field or signature changed).

- [ ] **Step 2: Full regression — server suite**

Run: `uv run pytest -q`
Expected: no NEW failures attributable to Plan 5. Record the pass/fail counts in the session/assessment. (Any unrelated pre-existing failure must be named explicitly and shown to predate this branch — never silence it.)

- [ ] **Step 3: Final gate**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: 0 errors.

- [ ] **Step 4: Push**

```bash
git push -u origin feat/beneath-sunden-persistence
```

- [ ] **Step 5: Stop. Do not open a PR or merge.** Report completion (files changed, test counts, the spec §11/§6 contracts locked, and the explicit Plan-6/7 carry-forward) and hand back for review.

---

## Carry-forward to Plan 6 / 7 (record in the memory note on completion)

- **Plan 6** (set-piece attach + trope/quest-at-attach) is the *producer* of `ComplicationThread` / `DungeonMutation` objects; it must serialize through Plan 5's `to_dict()/from_dict()` pair — never a parallel format.
- **Plan 7** (materializer) owns: the caller of `commit_expansion` (passing the live session connection so game-save + dungeon-save share one transaction, spec §7.5), the `dungeon.materialize.*` / `frontier.expand` spans, and the **mandatory materializer-invoked-from-real-session integration wiring test**. `DungeonStore(conn)` deliberately takes the caller's connection for exactly this.
- `commit_expansion(expansion, graph, *, generator_version=...)` reads depth-scored nodes from `graph` (not `expansion.new_nodes`, which keep pre-`assign_depth_scores` copies) — Plan 7 must call it *after* `assign_depth_scores`.
- Re-committing a frozen expansion raises `PersistError` before any write (freeze contract); Plan 7's look-ahead must never re-commit a materialized expansion.

---

## Self-Review (completed by plan author)

**1. Spec coverage:** §3.1 dungeon_map → Task 4/6; §3.5 dungeon_edge → Task 4/6; §3.2 frontier → Task 7; §3.3 mutation overlay → Task 8; §3.4 ledger → Task 9; §4 serde (created, not reused; report classes untouched) → Tasks 2/3 + the "zero context" note; §5 API (`DungeonStore`, caller-supplied conn, non-autocommit, fail-loud taxonomy) → Tasks 4/6/13; §6 OTEL (only real-caller spans, materializer spans deferred) → Task 11; §7 freeze → Task 10; §11 round-trip/property/no-floor/WAL/wiring → Tasks 5/6/12/13; §8/§9 carry-forward → Carry-forward section + Task 13. No spec section is unmapped.

**2. Placeholder scan:** No "TBD/TODO/handle edge cases/similar to Task N"; every code step shows complete code; every command has an expected result.

**3. Type consistency:** `to_dict()->dict` / `from_dict(d:dict)->T` uniform across `RegionNode`/`RegionEdge`/`RegionGraph`/`FrontierEdge`/`DungeonMutation`/`ComplicationThread`. `DungeonStore.__init__(conn: sqlite3.Connection | Path)`, `ensure_schema()`, `commit_expansion(expansion, graph, *, generator_version=...)`, `load_map(*, entrance_id)`, `put_frontier`/`load_frontier`, `record_mutation`/`load_mutations`, `open_thread`/`get_thread`/`resolve_thread`/`open_threads` — signatures are consistent everywhere they recur. Error taxonomy reused from `sidequest.game.persistence` (`PersistError`/`NotFoundError`/`DatabaseError`/`SerializationError`), not redefined. Span constants/helpers names match between `dungeon_persist.py` and Task 11's emission edits.
