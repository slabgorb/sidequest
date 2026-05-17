# Beneath Sünden — Plan 7 Session Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a real `caverns_and_claudes` / `beneath_sunden` game grow its dungeon by registering the merged Plan-7 look-ahead worker into the live WebSocket session lifecycle, bootstrapping the seed at session-open, and moving the materializer curate call onto the Anthropic SDK.

**Architecture:** One new isolation seam module `sidequest/dungeon/session_integration.py` (two functions: `attach_dungeon_to_session` / `detach_dungeon_from_session`) is called from exactly two one-line incisions in the hot session subsystem (connect open, cleanup teardown). It resolves the six worker deps honestly, persists a write-once `campaign_seed`, idempotently seeds expansion 0+1 via the merged `materialize` pipeline, and registers `register_lookahead_worker`. The merged curate stage moves off `claude -p` onto the codebase-idiomatic one-shot SDK call.

**Tech Stack:** Python 3.12, FastAPI, stdlib `sqlite3`, `uv` + `pytest` (`asyncio_mode="auto"`, `--timeout=30`), Anthropic SDK via `agents/llm_factory.build_llm_client()`.

**Spec:** `docs/superpowers/specs/2026-05-17-beneath-sunden-plan-7-session-integration-design.md` (authoritative; commits e15f452 / 155ddb5 / 53ffc67).

**Repo / branch:** All code changes are in **`sidequest-server`** on a new branch **`feat/beneath-sunden-plan-7-session-integration`** off `develop` (HEAD `bcabbf6`, Plan 7 merged). This plan doc lives in the oq-1 orchestrator on `docs/beneath-sunden-plan-7-session-integration-spec`. Per the subrepo-branch discipline, create the server branch BEFORE dispatching any implementer.

**Test runner facts:** From `/Users/slabgorb/Projects/oq-1/sidequest-server`: `uv run pytest <path> -v`. `asyncio_mode="auto"` — `async def test_*` needs **no** `@pytest.mark.asyncio`. Per-test 30s timeout; the only mocked seam allowed is an injected fake LLM client (never a real `claude`/network call). Lint: `uv run ruff check .`. Type: `uv run pyright`.

---

## Task 0: Branch setup (run once, before any task)

- [ ] **Step 1: Create the server feature branch off merged develop**

Run (absolute path; shell cwd may reset):

```bash
git -C /Users/slabgorb/Projects/oq-1/sidequest-server fetch origin --quiet
git -C /Users/slabgorb/Projects/oq-1/sidequest-server checkout develop
git -C /Users/slabgorb/Projects/oq-1/sidequest-server pull --ff-only origin develop
git -C /Users/slabgorb/Projects/oq-1/sidequest-server checkout -b feat/beneath-sunden-plan-7-session-integration
git -C /Users/slabgorb/Projects/oq-1/sidequest-server log -1 --format='%h %s'
```

Expected: HEAD is `bcabbf6 Merge pull request #306 …` (or a later develop tip that still contains `sidequest/dungeon/materializer.py`), on branch `feat/beneath-sunden-plan-7-session-integration`.

---

## File Structure

| Path | Create/Modify | Responsibility |
|---|---|---|
| `sidequest/game/persistence.py` | Modify | Add public `SqliteStore.connection()` accessor (Task 1). |
| `sidequest/dungeon/persistence.py` | Modify | `dungeon_meta` table in `DUNGEON_SCHEMA_SQL`; `get_campaign_seed` / `set_campaign_seed` on `DungeonStore` (Task 2). |
| `sidequest/dungeon/seed_bootstrap.py` | Create | Pure builders: shallowest-band entrance theme, entrance seed `RegionGraph`, the expansion-1 `MaterializationRequest` (Task 3). |
| `sidequest/dungeon/materializer.py` | Modify | `_stage_curate` one-shot SDK call; `materialize` required client; widened annotations (Task 4). |
| `tests/dungeon/test_materializer.py` | Modify | Add SDK fakes (`_reflecting_sdk_client`, `_failing_sdk_client`); repoint `_materialize_full` + curate tests (Task 4). |
| `tests/dungeon/test_lookahead_worker.py` | Modify | Repoint `_register` / probe / failing-client tests to SDK fakes (Task 4). |
| `sidequest/dungeon/session_integration.py` | Create | `attach_dungeon_to_session` / `detach_dungeon_from_session` (Task 5). |
| `sidequest/server/session_handler.py` | Modify | `_SessionData.lookahead_handle` field (Task 6). |
| `sidequest/handlers/connect.py` | Modify | One `await attach_dungeon_to_session(...)` incision (Task 6). |
| `sidequest/server/websocket_session_handler.py` | Modify | One `await detach_dungeon_from_session(...)` incision in `cleanup()` (Task 6). |
| `tests/game/test_sqlite_store_connection.py` | Create | Task 1 test. |
| `tests/dungeon/test_dungeon_meta_seed.py` | Create | Task 2 test. |
| `tests/dungeon/test_seed_bootstrap.py` | Create | Task 3 test. |
| `tests/dungeon/test_session_integration.py` | Create | Task 5 unit tests. |
| `tests/dungeon/test_session_lifecycle_wiring.py` | Create | Task 7 keystone wiring test. |

---

## Task 1: `SqliteStore.connection()` accessor

**Files:**
- Modify: `sidequest/game/persistence.py` (add a method after `close()`, ~L626-628)
- Test: `tests/game/test_sqlite_store_connection.py` (create)

Rationale: Plan 5/7 §7.5 requires game-save + dungeon-save share **one** sqlite connection. `DungeonStore(conn)` needs a raw `sqlite3.Connection`; today production reaches it via the private `store._conn`. Add a public accessor (no behavior change).

- [ ] **Step 1: Write the failing test**

Create `tests/game/test_sqlite_store_connection.py`:

```python
from __future__ import annotations

import sqlite3

import pytest

from sidequest.dungeon.persistence import DungeonStore
from sidequest.game.persistence import SqliteStore


def test_connection_returns_the_live_shared_conn() -> None:
    store = SqliteStore.open_in_memory()
    conn = store.connection()
    assert isinstance(conn, sqlite3.Connection)
    # Same object — one connection, never a copy (spec §7.5).
    assert conn is store._conn


def test_dungeonstore_shares_sqlitestore_connection() -> None:
    store = SqliteStore.open_in_memory()
    ds = DungeonStore(store.connection())  # must NOT raise the Path guard
    ds.ensure_schema()
    rows = store.connection().execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dungeon_map'"
    ).fetchall()
    assert rows, (
        "DungeonStore.ensure_schema did not write through the shared "
        "connection — connection() handed out a different conn (spec §7.5 "
        "one-transaction contract broken)"
    )
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_sqlite_store_connection.py -v`
Expected: FAIL — `AttributeError: 'SqliteStore' object has no attribute 'connection'`.

- [ ] **Step 3: Add the accessor**

In `sidequest/game/persistence.py`, immediately after the existing `close()` method:

```python
    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def connection(self) -> sqlite3.Connection:
        """Return the live sqlite3 connection.

        Plan 7 (spec §7.5): DungeonStore wraps this exact connection so
        game-save + dungeon-save share one transaction. Never hands out a
        copy — callers must observe each other's writes.
        """
        return self._conn
```

(`import sqlite3` is already at the top of this module.)

- [ ] **Step 4: Run the tests, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/game/test_sqlite_store_connection.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/game/persistence.py tests/game/test_sqlite_store_connection.py
git add sidequest/game/persistence.py tests/game/test_sqlite_store_connection.py
git commit -m "feat(persistence): public SqliteStore.connection() accessor (Plan 7 §7.5 shared conn)"
```

---

## Task 2: `dungeon_meta` table + write-once campaign seed

**Files:**
- Modify: `sidequest/dungeon/persistence.py` (`DUNGEON_SCHEMA_SQL` literal ~L135-194; add two methods to `DungeonStore`)
- Test: `tests/dungeon/test_dungeon_meta_seed.py` (create)

- [ ] **Step 1: Write the failing test**

Create `tests/dungeon/test_dungeon_meta_seed.py`:

```python
from __future__ import annotations

import sqlite3

import pytest

from sidequest.dungeon.persistence import DungeonStore, PersistError


def _mem() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_campaign_seed_absent_on_fresh_save() -> None:
    ds = DungeonStore(_mem())
    ds.ensure_schema()
    assert ds.get_campaign_seed() is None


def test_campaign_seed_roundtrips_verbatim() -> None:
    conn = _mem()
    ds = DungeonStore(conn)
    ds.ensure_schema()
    ds.set_campaign_seed(4611686018427387903)  # a 63-bit value
    conn.commit()
    assert ds.get_campaign_seed() == 4611686018427387903


def test_campaign_seed_is_write_once() -> None:
    conn = _mem()
    ds = DungeonStore(conn)
    ds.ensure_schema()
    ds.set_campaign_seed(111)
    conn.commit()
    with pytest.raises(PersistError):
        ds.set_campaign_seed(222)
    assert ds.get_campaign_seed() == 111  # frozen — refused overwrite
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_dungeon_meta_seed.py -v`
Expected: FAIL — `AttributeError: 'DungeonStore' object has no attribute 'get_campaign_seed'`.

- [ ] **Step 3: Add the table to `DUNGEON_SCHEMA_SQL`**

In `sidequest/dungeon/persistence.py`, inside the triple-quoted `DUNGEON_SCHEMA_SQL` string, append this block at the end of the string (after the last existing `dungeon_complication_ledger` table, matching house style — `created_at TEXT NOT NULL DEFAULT (datetime('now'))`):

```sql
CREATE TABLE IF NOT EXISTS dungeon_meta (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    campaign_seed INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
```

- [ ] **Step 4: Add the two methods to `DungeonStore`**

In `sidequest/dungeon/persistence.py`, add to `class DungeonStore` (place immediately after `ensure_schema`):

```python
    def get_campaign_seed(self) -> int | None:
        """The persisted campaign seed, or ``None`` on a fresh save.

        Save-is-truth: the seed is frozen at bootstrap and read back
        verbatim every reopen (Plan 7 session-integration spec §5). Fails
        loud on a real sqlite error (No Silent Fallbacks).
        """
        try:
            row = self._conn.execute(
                "SELECT campaign_seed FROM dungeon_meta WHERE id = 1"
            ).fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"dungeon_meta read failed: {exc}") from exc
        return None if row is None else int(row[0])

    def set_campaign_seed(self, seed: int) -> None:
        """Persist the campaign seed exactly once (write-once).

        A second write is a contract violation, not an upsert — the seed
        is frozen with the dungeon (save-is-truth). Does NOT autocommit:
        the caller owns the transaction boundary (spec §7.5).
        """
        if self.get_campaign_seed() is not None:
            raise PersistError(
                "campaign_seed already set — it is write-once "
                "(save-is-truth); refusing to overwrite a frozen seed"
            )
        try:
            self._conn.execute(
                "INSERT INTO dungeon_meta (id, campaign_seed) VALUES (1, ?)",
                (seed,),
            )
        except sqlite3.Error as exc:
            raise DatabaseError(f"dungeon_meta write failed: {exc}") from exc
```

(`sqlite3`, `DatabaseError`, `PersistError` are already imported in this module — confirmed in the contracts dossier §2.)

- [ ] **Step 5: Run the tests, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_dungeon_meta_seed.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/dungeon/persistence.py tests/dungeon/test_dungeon_meta_seed.py
git add sidequest/dungeon/persistence.py tests/dungeon/test_dungeon_meta_seed.py
git commit -m "feat(dungeon): dungeon_meta write-once campaign_seed (Plan 7 session-integration §5)"
```

---

## Task 3: Production entrance seed-graph + expansion-1 request builders

**Files:**
- Create: `sidequest/dungeon/seed_bootstrap.py`
- Test: `tests/dungeon/test_seed_bootstrap.py`

These are pure builders (no I/O) — the production analog of the test helpers `_make_seed_graph` / `_seed_graph_themed` / `MaterializationRequest_build`, with the entrance theme = shallowest depth-band palette theme (spec §13 decision 2). Contracts (dossier): `RegionGraph(entrance_id=...)` dataclass with `.add_node`; `RegionNode(id, expansion_id, theme, depth_score=None)`; `ThemePalette.themes_for_depth(depth_score) -> list[DungeonTheme]`; `DungeonTheme.id`; `MaterializationRequest.build(...)`; `FrontierEdge(frontier_edge_id, from_region_id, heading, spawn_depth_score)`. The entrance is `expansion_id=0`, `depth_score` left `None` (the commit stage freezes it to 0.0 per Seed=Expansion-0).

- [ ] **Step 1: Write the failing test**

Create `tests/dungeon/test_seed_bootstrap.py`:

```python
from __future__ import annotations

import pytest

from sidequest.dungeon.seed_bootstrap import (
    ENTRANCE_ID,
    build_entrance_seed_graph,
    build_expansion_one_request,
    select_entrance_theme_id,
)


def _palette(theme_id: str = "sunden_threshold"):
    # Reuse the real Task-5 DungeonTheme builder (no mocking the dungeon layer).
    from tests.dungeon.test_materializer import _commit_palette

    return _commit_palette(theme_id)


def test_select_entrance_theme_id_picks_depth_zero_eligible_theme() -> None:
    palette = _palette("sunden_threshold")
    assert select_entrance_theme_id(palette) == "sunden_threshold"


def test_select_entrance_theme_id_is_deterministic_by_id() -> None:
    from sidequest.dungeon.themes import ThemePalette
    from tests.dungeon.test_materializer import _theme_with_set_piece

    palette = ThemePalette(
        themes={
            "zeta_pit": _theme_with_set_piece("zeta_pit"),
            "alpha_gate": _theme_with_set_piece("alpha_gate"),
        }
    )
    # Both eligible at depth 0.0 (DepthBand(min=0.0, max=None)); tie broken
    # by id → deterministic, reproducible (No Silent Fallbacks).
    assert select_entrance_theme_id(palette) == "alpha_gate"


def test_select_entrance_theme_id_raises_when_nothing_covers_surface() -> None:
    from sidequest.dungeon.themes import (
        Adjacency,
        DepthBand,
        DungeonTheme,
        InteriorSpec,
        NarratorFlavor,
        ThemePalette,
    )

    deep_only = DungeonTheme(
        id="deep_only",
        display_name="Deep Only",
        generator_class="organic",
        interior=InteriorSpec(algorithm="cellular", braid_ratio=0.0),
        depth_band=DepthBand(min=300.0, max=None),
        narrator=NarratorFlavor(register="grave", flavor="x"),
        adjacency=Adjacency(),
        set_pieces=[],
    )
    with pytest.raises(ValueError, match="no theme covers the surface entrance"):
        select_entrance_theme_id(ThemePalette(themes={"deep_only": deep_only}))


def test_build_entrance_seed_graph_has_only_entrance_at_expansion_zero() -> None:
    g = build_entrance_seed_graph("sunden_threshold")
    assert g.entrance_id == ENTRANCE_ID == "entrance"
    assert set(g.nodes) == {"entrance"}
    n = g.nodes["entrance"]
    assert n.id == "entrance"
    assert n.expansion_id == 0
    assert n.theme == "sunden_threshold"
    assert n.depth_score is None  # frozen to 0.0 by the commit stage, not here


def test_build_expansion_one_request_is_valid_expansion_one() -> None:
    req = build_expansion_one_request(campaign_seed=7)
    assert req.expansion_id == 1
    assert req.campaign_seed == 7
    assert req.frontier_edge.from_region_id == "entrance"
    assert req.frontier_edge.spawn_depth_score == 0.0
    assert req.attach_region_ids == ("entrance",)
    assert req.burst_magnitude >= 1
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_seed_bootstrap.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.seed_bootstrap'`.

- [ ] **Step 3: Create the module**

Create `sidequest/dungeon/seed_bootstrap.py`:

```python
"""Beneath Sünden Plan 7 session-integration — pure seed builders.

Production analog of the test seeding helpers (``_make_seed_graph`` /
``_seed_graph_themed`` / ``MaterializationRequest_build``). No I/O: builds
the entrance ``RegionGraph`` and the expansion-1 ``MaterializationRequest``
the bootstrap feeds to the merged ``materialize`` pipeline, which commits
the entrance as Expansion 0 (Seed = Expansion 0 contract) and the generated
expansion 1.

Entrance theme = the shallowest depth-band palette theme (spec §13
decision 2). Deterministic (ties broken by theme id) — No Silent Fallbacks.
"""

from __future__ import annotations

from typing import Any

from sidequest.dungeon.materializer import MaterializationRequest
from sidequest.dungeon.persistence import FrontierEdge
from sidequest.dungeon.region_graph import RegionGraph, RegionNode

__all__ = [
    "ENTRANCE_ID",
    "build_entrance_seed_graph",
    "build_expansion_one_request",
    "select_entrance_theme_id",
]

# The Seed=Expansion-0 fixed anchor id (matches
# lookahead_worker._ENTRANCE_ID and load_map(entrance_id=...)).
ENTRANCE_ID = "entrance"

# The surface entrance sits at depth 0.0 (frozen root, spec §7).
_ENTRANCE_DEPTH = 0.0


def select_entrance_theme_id(palette: Any) -> str:
    """The theme id for the surface entrance: the shallowest-band theme
    eligible at depth 0.0, deterministic by id.

    Raises loudly if no theme covers the surface — a beneath_sunden
    palette with no depth-0 theme is a real content gap, never papered
    over with a silent default (No Silent Fallbacks).
    """
    eligible = palette.themes_for_depth(_ENTRANCE_DEPTH)
    if not eligible:
        raise ValueError(
            "no theme covers the surface entrance (depth 0.0) in the "
            "loaded ThemePalette — beneath_sunden content gap; refusing "
            "to invent an entrance theme (No Silent Fallbacks)"
        )
    return sorted(theme.id for theme in eligible)[0]


def build_entrance_seed_graph(entrance_theme_id: str) -> RegionGraph:
    """A seed graph containing only the entrance node at expansion 0.

    ``depth_score`` is left ``None`` — the merged commit stage freezes it
    to 0.0 (Seed = Expansion 0); the bootstrap never assigns it (save-is-
    truth: never recompute a frozen score).
    """
    g = RegionGraph(entrance_id=ENTRANCE_ID)
    g.add_node(RegionNode(id=ENTRANCE_ID, expansion_id=0, theme=entrance_theme_id))
    return g


def build_expansion_one_request(*, campaign_seed: int) -> MaterializationRequest:
    """The first generated expansion's request (expansion_id == 1),
    pushing off the entrance.

    Mirrors the test ``MaterializationRequest_build`` shape: one frontier
    edge rooted at the entrance at spawn depth 0.0; attach to the
    entrance; burst 3.
    """
    fe = FrontierEdge(
        frontier_edge_id="seed_fe1",
        from_region_id=ENTRANCE_ID,
        heading="down",
        spawn_depth_score=_ENTRANCE_DEPTH,
    )
    return MaterializationRequest.build(
        campaign_seed=campaign_seed,
        expansion_id=1,
        frontier_edge=fe,
        frontier=[fe],
        attach_region_ids=[ENTRANCE_ID],
        heading="down",
        burst_magnitude=3,
        lookahead_breadth=1,
    )
```

- [ ] **Step 4: Run the tests, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_seed_bootstrap.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/dungeon/seed_bootstrap.py tests/dungeon/test_seed_bootstrap.py
git add sidequest/dungeon/seed_bootstrap.py tests/dungeon/test_seed_bootstrap.py
git commit -m "feat(dungeon): pure entrance seed-graph + expansion-1 request builders (Plan 7 §6)"
```

---

## Task 4: Move `_stage_curate` to the one-shot SDK call (+ migrate shared test fakes)

**Files:**
- Modify: `sidequest/dungeon/materializer.py` (`_stage_curate` ~L873-887; `materialize` signature ~L1487-1498 + `curation_client` line ~L1557; imports ~L141)
- Modify: `tests/dungeon/test_materializer.py` (add SDK fakes; repoint `_materialize_full` + curate tests)
- Modify: `tests/dungeon/test_lookahead_worker.py` (repoint `_register` / probe / failing-client tests)

The merged curate stage calls `await claude_client.send(prompt)` then `response.text` (dossier §3c). The SDK client (`AnthropicSdkClient`, default of `build_llm_client()`) exposes only `complete_with_tools` → `ToolingResult` (no `.send`). Per spec §7, use the established one-shot: `complete_with_tools(system_blocks, messages, tools=[], tool_dispatch=None, model=resolve_model(CallType.SCRATCH))`, catch `LlmClientError`. This breaks the `.send`-shaped shared fakes, so migrate them to an SDK shape in the same task (spec §7 reconciled clause).

- [ ] **Step 1: Add SDK fakes to `tests/dungeon/test_materializer.py`**

Add these helpers near the existing `_reflecting_claude_client` (the verdict-reflection logic is preserved verbatim; only the client surface changes):

```python
def _reflecting_sdk_client() -> Any:
    """ToolingLlmClient-shaped fake: parses the curation prompt's
    ``INPUT:\\n<json>`` and echoes a well-formed per-region verdict as
    ToolingResult.text. SDK analog of _reflecting_claude_client — NEVER a
    real network call (the only mocked seam)."""
    import json as _json

    from sidequest.agents.tooling_protocol import ToolingResult

    class _ReflectingSdk:
        async def complete_with_tools(
            self,
            system_blocks: Any,
            messages: Any,
            tools: Any,
            tool_dispatch: Any = None,
            *,
            model: str,
            max_iterations: int = 8,
            on_text_delta: Any = None,
        ) -> ToolingResult:
            prompt = messages[0].content
            _, _, input_blob = prompt.partition("INPUT:\n")
            payload = _json.loads(input_blob)
            verdict = {
                region_id: {
                    "race": region["race"],
                    "cr_band": region["cr_band"],
                    "wandering_table": [
                        {**row, "telegraph": (row.get("telegraph") or "It is here.")}
                        for row in region["wandering_table"]
                    ],
                    "big_bad": region["big_bad"],
                }
                for region_id, region in payload.items()
            }
            return ToolingResult(
                text=_json.dumps(verdict),
                stop_reason="end_turn",
                input_tokens=1,
                output_tokens=7,
                cached_input_read_tokens=0,
                cached_input_write_tokens=0,
                model=model,
            )

    return _ReflectingSdk()


def _failing_sdk_client() -> Any:
    """ToolingLlmClient-shaped fake whose call fails with an
    LlmClientError subclass (SDK analog of a curation subprocess
    failure)."""
    from sidequest.agents.anthropic_sdk_client import AnthropicSdkClientError

    class _FailingSdk:
        async def complete_with_tools(self, *a: Any, **k: Any) -> Any:
            raise AnthropicSdkClientError("forced curation failure (test)")

    return _FailingSdk()
```

- [ ] **Step 2: Repoint the materializer test client construction to the SDK fake**

In `tests/dungeon/test_materializer.py`, change `_materialize_full` to pass `claude_client=_reflecting_sdk_client()` instead of `_reflecting_claude_client()`. Then update every curate/commit test that constructed a `_fake_claude_client(_FakeProc(...))` or `_reflecting_claude_client()` for the curate path:
- success/verdict cases → `_reflecting_sdk_client()`
- forced-failure cases (previously `_fake_claude_client(_FakeProc(b"not json", b"boom", returncode=1))`) → `_failing_sdk_client()`

(Find them: `grep -n "_reflecting_claude_client\|_fake_claude_client\|_FakeProc" tests/dungeon/test_materializer.py`. Leave `_FakeProc` / `_fake_claude_client` / `_reflecting_claude_client` defined if other non-curate tests still use them; only the curate-path call sites move.)

- [ ] **Step 3: Repoint `tests/dungeon/test_lookahead_worker.py`**

- `_register` (dossier §7): change `claude_client=_reflecting_claude_client()` → import and use `_reflecting_sdk_client` from `tests.dungeon.test_materializer`, i.e. `claude_client=_reflecting_sdk_client()`.
- `test_default_lookahead_breadth_is_one`: same repoint.
- `_yielding_concurrency_probe_client`: rewrite as a `ToolingLlmClient`-shaped probe whose `complete_with_tools` does the same `probe['live']/probe['max']` accounting + `await asyncio.sleep(0)` yields, then returns the reflected `ToolingResult` (reuse the `_reflecting_sdk_client` verdict logic; keep the probe counters).
- `test_worker_failure_loud_on_span_and_does_not_abort_transition`: replace `failing_client = _fake_claude_client(_FakeProc(b"not json", b"boom", returncode=1))` with `failing_client = _failing_sdk_client()` (import from `tests.dungeon.test_materializer`).
- The `_ExplodingFrontierStore` / no-frontier / dedupe tests do not touch the client and need no change.

- [ ] **Step 4: Migrate `_stage_curate` and `materialize` to the SDK one-shot**

In `sidequest/dungeon/materializer.py`:

(a) Imports — replace the line `from sidequest.agents.claude_client import ClaudeClient, ClaudeClientError` with:

```python
from sidequest.agents.claude_client import LlmClientError
from sidequest.agents.model_routing import CallType, resolve_model
from sidequest.agents.tooling_protocol import CacheableBlock, Message
```

(b) `_stage_curate` — replace the `try: response = await claude_client.send(prompt) except ClaudeClientError as exc:` block (dossier §3c) with:

```python
    prompt = _build_curation_prompt(manifests, region_look)
    try:
        result = await claude_client.complete_with_tools(
            system_blocks=[
                CacheableBlock(
                    text=(
                        "You curate procedural dungeon regions: select and "
                        "refine each region's creatures, CR band, wandering "
                        "table, and telegraphs. Reply with the verdict JSON "
                        "only."
                    ),
                    cache=False,
                )
            ],
            messages=[Message(role="user", content=prompt)],
            tools=[],
            tool_dispatch=None,
            model=resolve_model(CallType.SCRATCH),
        )
    except LlmClientError as exc:
        span.set_attribute("curated", False)
        span.set_attribute("reason", f"llm: {exc}")
        raise CurationError(
            f"curation LLM call failed: {exc} — aborting "
            f"materialization (no raw-manifest-stamped-curated fallback)"
        ) from exc

    try:
        verdict = _parse_curation_verdict(result.text)
    except CurationError as exc:
        span.set_attribute("curated", False)
        span.set_attribute("reason", str(exc))
        raise
```

Also change `_stage_curate`'s signature annotation `claude_client: ClaudeClient | None` → `claude_client: Any` (the `Any` import already exists in this module — dossier §3e), and keep its existing `if claude_client is None: raise ValueError(...)` guard.

(c) `materialize` signature — change `claude_client: ClaudeClient | None = None` → `claude_client: Any` (required, no default).

(d) The `curation_client = claude_client if claude_client is not None else ClaudeClient()` line (dossier §3d) — replace with:

```python
    if claude_client is None:
        raise ValueError(
            "materialize requires an explicit claude_client (the look-ahead "
            "worker/session supplies the SDK client via build_llm_client(); "
            "No Silent Fallbacks — no implicit ClaudeClient())"
        )
    curation_client = claude_client
```

(e) Update the `materialize` docstring `claude_client:` param note: replace the "None → a real ClaudeClient() is constructed" sentence with "Required. The session supplies the SDK client (`build_llm_client()` default `AnthropicSdkClient`); the curate stage issues a one-shot `complete_with_tools`."

(Note: `_build_curation_prompt` still produces the same `…INPUT:\n<json>` prompt; only the transport changed. `result.text` replaces `response.text`. `CurationError` / span attributes unchanged.)

- [ ] **Step 5: Run the dungeon suite, verify green**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/ -v`
Expected: PASS (the full dungeon suite — materializer + lookahead_worker + setpiece + themes + the Task 1-3 new tests). If any curate test still references a `.send`/`_FakeProc` path, finish repointing it to `_reflecting_sdk_client()` / `_failing_sdk_client()` (Steps 2-3) — do not revert the production change.

- [ ] **Step 6: Type-check the changed production module**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pyright sidequest/dungeon/materializer.py`
Expected: 0 errors. (If `pyright` flags the now-`Any` client, that is expected/acceptable — the tooling protocol is structural; ensure no *new* errors beyond the widened annotation.)

- [ ] **Step 7: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/dungeon/materializer.py tests/dungeon/test_materializer.py tests/dungeon/test_lookahead_worker.py
git add sidequest/dungeon/materializer.py tests/dungeon/test_materializer.py tests/dungeon/test_lookahead_worker.py
git commit -m "feat(dungeon): curate stage one-shot SDK (complete_with_tools); migrate shared Plan-7 test fakes to SDK shape (Plan 7 §7)"
```

---

## Task 5: `session_integration` module (attach/detach)

**Files:**
- Create: `sidequest/dungeon/session_integration.py`
- Test: `tests/dungeon/test_session_integration.py`

`attach_dungeon_to_session` gates inside (returns `None` for non-`beneath_sunden`), resolves deps, idempotently seeds-or-loads, registers the worker. `detach_dungeon_from_session` is null-safe. Contracts from the dossier: `register_lookahead_worker(*, persistence, bundle, palette, pack_tropes, claude_client, campaign_seed, lookahead_breadth=1) -> LookaheadWorkerHandle` (`.unregister()`, `await .drain()`); `load_cookbook(world: Path) -> CookbookBundle`; `load_theme_palette(pack_dir: Path) -> ThemePalette`; `DungeonStore.load_map(entrance_id=...)`, `.ensure_schema()`, `.get/set_campaign_seed()`; `materialize(request, *, graph, bundle, palette, persistence, snapshot, pack_tropes, claude_client)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/dungeon/test_session_integration.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from sidequest.dungeon import frontier_hook


@pytest.fixture(autouse=True)
def _restore_frontier_observers() -> Any:
    before = list(frontier_hook._OBSERVERS)
    try:
        yield
    finally:
        frontier_hook._OBSERVERS[:] = before


def _sqlite_store() -> Any:
    from sidequest.game.persistence import SqliteStore

    return SqliteStore.open_in_memory()


def _beneath_sunden_world_dir() -> Path:
    return (
        # tests/dungeon/<file> → tests → sidequest-server → repo root;
        # sidequest-content is a SIBLING of sidequest-server (parents[3]),
        # matching the existing _BENEATH_SUNDEN_WORLD in test_materializer.py.
        Path(__file__).resolve().parents[3]
        / "sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden"
    )


def _snapshot() -> Any:
    from sidequest.game.session import GameSnapshot

    return GameSnapshot(genre_slug="caverns_and_claudes", world_slug="beneath_sunden")


async def test_non_beneath_sunden_is_a_clean_noop() -> None:
    from sidequest.dungeon.session_integration import attach_dungeon_to_session

    handle = await attach_dungeon_to_session(
        store=_sqlite_store(),
        snapshot=_snapshot(),
        genre_pack=object(),
        genre_slug="space_opera",
        world_slug="some_world",
        world_dir=Path("/nonexistent"),
    )
    assert handle is None
    assert frontier_hook.registered_observer_count() == 0


async def test_detach_is_null_safe() -> None:
    from sidequest.dungeon.session_integration import detach_dungeon_from_session

    await detach_dungeon_from_session(None)  # must not raise


async def test_attach_seeds_and_registers_then_detach_unregisters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fresh beneath_sunden save: attach bootstraps expansion 0+1,
    persists a seed, and registers exactly one frontier observer; detach
    unregisters it. The only mocked seam is the SDK curate client."""
    from sidequest.dungeon import session_integration
    from sidequest.dungeon.persistence import DungeonStore
    from tests.dungeon.test_materializer import _reflecting_sdk_client

    monkeypatch.setattr(
        session_integration, "build_llm_client", _reflecting_sdk_client
    )

    store = _sqlite_store()
    snap = _snapshot()
    handle = await session_integration.attach_dungeon_to_session(
        store=store,
        snapshot=snap,
        genre_pack=_pack(),
        genre_slug="caverns_and_claudes",
        world_slug="beneath_sunden",
        world_dir=_beneath_sunden_world_dir(),
    )
    assert handle is not None
    assert frontier_hook.registered_observer_count() == 1

    ds = DungeonStore(store.connection())
    assert ds.get_campaign_seed() is not None  # frozen seed persisted
    nodes = ds.load_map(entrance_id="entrance").nodes
    assert "entrance" in nodes and nodes["entrance"].expansion_id == 0
    assert any(n.expansion_id == 1 for n in nodes.values())  # expansion 1 grew

    await session_integration.detach_dungeon_from_session(handle)
    assert frontier_hook.registered_observer_count() == 0


async def test_attach_is_idempotent_reuses_persisted_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sidequest.dungeon import session_integration
    from sidequest.dungeon.persistence import DungeonStore
    from tests.dungeon.test_materializer import _reflecting_sdk_client

    monkeypatch.setattr(
        session_integration, "build_llm_client", _reflecting_sdk_client
    )
    store = _sqlite_store()
    kw = dict(
        store=store,
        snapshot=_snapshot(),
        genre_pack=_pack(),
        genre_slug="caverns_and_claudes",
        world_slug="beneath_sunden",
        world_dir=_beneath_sunden_world_dir(),
    )
    h1 = await session_integration.attach_dungeon_to_session(**kw)
    await session_integration.detach_dungeon_from_session(h1)
    seed1 = DungeonStore(store.connection()).get_campaign_seed()
    map1 = sorted(DungeonStore(store.connection()).load_map(entrance_id="entrance").nodes)

    h2 = await session_integration.attach_dungeon_to_session(**dict(kw, snapshot=_snapshot()))
    await session_integration.detach_dungeon_from_session(h2)
    seed2 = DungeonStore(store.connection()).get_campaign_seed()
    map2 = sorted(DungeonStore(store.connection()).load_map(entrance_id="entrance").nodes)

    assert seed1 == seed2, "reopen must reuse the frozen campaign_seed"
    assert map1 == map2, "reopen must NOT re-seed (idempotent bootstrap)"


def _pack() -> Any:
    """Pack-shaped object carrying .tropes (duck type, dossier _attach_pack)."""
    from tests.dungeon.test_materializer import _attach_pack

    return _attach_pack("cave_in")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_integration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.session_integration'`.

- [ ] **Step 3: Create the module**

Create `sidequest/dungeon/session_integration.py`:

```python
"""Beneath Sünden Plan 7 session-integration — the live wiring seam.

The only new production seam (spec Decision 5 / Approach A). Two
functions called from exactly two one-line incisions in the WS session
lifecycle: register the merged look-ahead worker for the session's life,
and bootstrap the Seed=Expansion-0 dungeon on the first open of a
campaign. All dungeon/bootstrap/dep-resolution complexity is isolated
here so the hot session subsystem stays thin.

No Silent Fallbacks: every unresolved dep raises loudly; the genre/world
gate returns None (a clean no-op) only for worlds this dungeon does not
apply to.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from sidequest.agents.llm_factory import build_llm_client
from sidequest.dungeon.lookahead_worker import (
    LookaheadWorkerHandle,
    register_lookahead_worker,
)
from sidequest.dungeon.materializer import materialize
from sidequest.dungeon.persistence import DungeonStore
from sidequest.dungeon.seed_bootstrap import (
    build_entrance_seed_graph,
    build_expansion_one_request,
    select_entrance_theme_id,
)
from sidequest.dungeon.themes import load_theme_palette
from sidequest.game.cookbook.loader import load_cookbook

__all__ = [
    "attach_dungeon_to_session",
    "detach_dungeon_from_session",
]

_GENRE = "caverns_and_claudes"
_WORLD = "beneath_sunden"
# 63-bit seed: positive, fits a SQLite INTEGER, ample entropy.
_SEED_BITS = 63


def _theme_pack_root(world_dir: Path) -> Path:
    """The genre-pack dir holding ``themes/`` (Plan 4 layout
    ``genre_packs/<genre>/themes/``). ``world_dir`` is
    ``…/genre_packs/<genre>/worlds/<world>`` → parents[1] is the pack
    root. Verified loud by load_theme_palette (raises if themes/ absent).
    """
    return world_dir.parent.parent


async def attach_dungeon_to_session(
    *,
    store: Any,
    snapshot: Any,
    genre_pack: Any,
    genre_slug: str,
    world_slug: str,
    world_dir: Path,
) -> LookaheadWorkerHandle | None:
    """Register the look-ahead worker for this session; bootstrap the
    seed on a fresh campaign. Returns the handle (held by the session for
    teardown), or ``None`` for any non-beneath_sunden session (clean
    no-op — the gate lives here so the call site is unconditional)."""
    if genre_slug != _GENRE or world_slug != _WORLD:
        return None

    conn = store.connection()
    persistence = DungeonStore(conn)
    persistence.ensure_schema()  # outside any txn (executescript implicit COMMIT)

    bundle = load_cookbook(world_dir)
    palette = load_theme_palette(_theme_pack_root(world_dir))
    claude_client = build_llm_client()

    # Save-is-truth: reuse a frozen seed; only generate+persist on a
    # genuinely fresh save (a prior failed bootstrap left the seed but no
    # map → reuse it so the retry is deterministic).
    campaign_seed = persistence.get_campaign_seed()
    if campaign_seed is None:
        campaign_seed = secrets.randbits(_SEED_BITS)
        persistence.set_campaign_seed(campaign_seed)
        conn.commit()

    already_seeded = bool(persistence.load_map(entrance_id="entrance").nodes)
    if not already_seeded:
        entrance_theme = select_entrance_theme_id(palette)
        seed_graph = build_entrance_seed_graph(entrance_theme)
        request = build_expansion_one_request(campaign_seed=campaign_seed)
        # The merged commit stage seeds Expansion 0 (entrance) before
        # expansion 1 and rolls back on PersistError (Seed=Expansion-0,
        # spec §6). A bootstrap failure raises loudly here — the connect
        # handler must not start a beneath_sunden session with a broken
        # dungeon (No Silent Fallbacks, spec §9).
        await materialize(
            request,
            graph=seed_graph,
            bundle=bundle,
            palette=palette,
            persistence=persistence,
            snapshot=snapshot,
            pack_tropes=genre_pack,
            claude_client=claude_client,
        )

    return register_lookahead_worker(
        persistence=persistence,
        bundle=bundle,
        palette=palette,
        pack_tropes=genre_pack,
        claude_client=claude_client,
        campaign_seed=campaign_seed,
    )


async def detach_dungeon_from_session(
    handle: LookaheadWorkerHandle | None,
) -> None:
    """Teardown: unregister the observer and drain in-flight look-ahead
    tasks. Null-safe and unconditional-call-safe (handle is None for
    non-beneath_sunden sessions). Does NOT close the connection — the
    room owns the store lifecycle (spec §8 / dossier §9)."""
    if handle is None:
        return
    handle.unregister()
    await handle.drain()
```

Note `genre_pack` is passed straight through as `pack_tropes` — the merged worker/`attach_set_piece` duck-types `.tropes` (dossier `_attach_pack`); the loaded `GenrePack` exposes `.tropes` (Explore report §6). The test injects a `.tropes`-shaped object.

- [ ] **Step 4: Run the tests, verify pass**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_integration.py -v`
Expected: PASS (4 passed). If `pack_tropes`/`genre_pack` shape mismatches a real materialize call, the test injects `_attach_pack(...)` which is the correct duck type — keep the production code passing `genre_pack` through (real `GenrePack.tropes` is the production analog; do not stub).

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/dungeon/session_integration.py tests/dungeon/test_session_integration.py
git add sidequest/dungeon/session_integration.py tests/dungeon/test_session_integration.py
git commit -m "feat(dungeon): session_integration attach/detach seam (gate, deps, idempotent bootstrap, register) — Plan 7 §3-§6"
```

---

## Task 6: Two lifecycle incisions + `_SessionData` field

**Files:**
- Modify: `sidequest/server/session_handler.py` (`_SessionData` ~L423-577 — add a defaulted field after `orchestrator`)
- Modify: `sidequest/handlers/connect.py` (one `await` after `_SessionData(...)` closes, ~L750-768)
- Modify: `sidequest/server/websocket_session_handler.py` (`cleanup()` ~L927-928)

No new behavior is unit-tested here in isolation — Task 7's session-lifecycle wiring test is the integration proof (these three edits are the wiring it exercises). This task is mechanical; verify by the full server import + Task 7.

- [ ] **Step 1: Add the `_SessionData` field**

In `sidequest/server/session_handler.py`, in the `@dataclass _SessionData`, add a defaulted field **after** `orchestrator` (the last non-default field — dossier §8 documents this ordering constraint). Place it next to `embed_task` (the per-session async-resource sibling):

```python
    embed_task: asyncio.Task[None] | None = None
    lookahead_handle: "LookaheadWorkerHandle | None" = None
```

Add the import at the top of `session_handler.py` (with the other typing imports), using `TYPE_CHECKING` to avoid a runtime import cycle if one exists:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.dungeon.lookahead_worker import LookaheadWorkerHandle
```

(If `session_handler.py` already has a `TYPE_CHECKING` block, add the import there instead of a second block. The field annotation is a string literal so the `TYPE_CHECKING`-only import is sufficient.)

- [ ] **Step 2: Add the connect-open incision**

In `sidequest/handlers/connect.py`, immediately after the `session._session_data = _SessionData(...)` construction closes (the `)` at ~L750) and before the `if has_character:` block (~L768), insert:

```python
            from sidequest.dungeon.session_integration import (
                attach_dungeon_to_session,
            )

            session._session_data.lookahead_handle = await attach_dungeon_to_session(
                store=room.store,
                snapshot=room.snapshot,
                genre_pack=genre_pack,
                genre_slug=row.genre_slug,
                world_slug=row.world_slug,
                world_dir=world_dir,
            )
```

(`room.store`, `room.snapshot`, `genre_pack`, `row.genre_slug`, `row.world_slug`, `world_dir` are all in scope here — dossier §8. The handler is `async`. The function-local import avoids any module import-cycle risk and matches the established lazy-import style in this handler, e.g. the `frontier_hook` import in `session.py`.)

- [ ] **Step 3: Add the cleanup-teardown incision**

In `sidequest/server/websocket_session_handler.py`, in `cleanup()`, **after** the `embed_task` cancellation block ends (~L927) and **before** the `try:` of the `room.save()`/`store.save()` block (~L928), insert (single 12-space indent, inside `if self._session_data is not None:`):

```python
            from sidequest.dungeon.session_integration import (
                detach_dungeon_from_session,
            )

            await detach_dungeon_from_session(
                self._session_data.lookahead_handle
            )
```

(Null-safe: `lookahead_handle` is `None` for non-beneath_sunden sessions and for any session that disconnected before attach. Mirrors `embed_task.cancel()` — unregister only, never closes the store, dossier §9.)

- [ ] **Step 4: Sanity-check imports + full dungeon suite still green**

Run:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run python -c "import sidequest.handlers.connect, sidequest.server.websocket_session_handler, sidequest.server.session_handler; print('imports OK')"
uv run pytest tests/dungeon/ -v
```

Expected: `imports OK` (no circular-import error), and the dungeon suite still PASSES.

- [ ] **Step 5: Lint + commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run ruff check sidequest/server/session_handler.py sidequest/handlers/connect.py sidequest/server/websocket_session_handler.py
git add sidequest/server/session_handler.py sidequest/handlers/connect.py sidequest/server/websocket_session_handler.py
git commit -m "feat(server): wire dungeon session_integration into connect-open + cleanup-teardown (Plan 7 §8)"
```

---

## Task 7: Keystone session-lifecycle wiring test

**Files:**
- Create: `tests/dungeon/test_session_lifecycle_wiring.py`

Proves the seam is wired end-to-end through the **real production producer** (`frontier_hook.notify_region_transition`, called by `GameSnapshot.apply_world_patch`), not just that the worker exists. This is the Every-Suite-Needs-a-Wiring-Test requirement and the spec §10 keystone (success = `observers >= 1` + a real crossing materializes the next expansion).

- [ ] **Step 1: Write the wiring test**

Create `tests/dungeon/test_session_lifecycle_wiring.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sidequest.dungeon import frontier_hook


@pytest.fixture(autouse=True)
def _restore_frontier_observers() -> Any:
    """Prevent observer registration leaking into the ~6500-test suite
    (the Task-6/7 wiring-test fixture pattern)."""
    before = list(frontier_hook._OBSERVERS)
    try:
        yield
    finally:
        frontier_hook._OBSERVERS[:] = before


def _otel_in_memory() -> tuple[Any, Any, Any]:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider, provider.get_tracer("test")


def _beneath_sunden_world_dir() -> Path:
    return (
        # tests/dungeon/<file> → tests → sidequest-server → repo root;
        # sidequest-content is a SIBLING of sidequest-server (parents[3]),
        # matching the existing _BENEATH_SUNDEN_WORLD in test_materializer.py.
        Path(__file__).resolve().parents[3]
        / "sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden"
    )


async def test_session_lifecycle_registers_worker_and_dungeon_grows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: attach (fresh save) bootstraps expansion 0+1 and
    registers the worker; a REAL production region transition
    (snap.apply_world_patch → frontier_hook.notify_region_transition)
    toward an unexpanded frontier edge materializes the next expansion;
    the frontier.region_transition span carries observers>=1 (the
    lie-detector signal flips off zero); detach unregisters cleanly."""
    import sidequest.telemetry.spans as _spans_module
    from sidequest.dungeon import session_integration
    from sidequest.dungeon.persistence import DungeonStore
    from sidequest.game.persistence import SqliteStore
    from sidequest.game.session import GameSnapshot, WorldStatePatch
    from sidequest.telemetry.spans.dungeon_materialize import (
        SPAN_FRONTIER_REGION_TRANSITION,
    )
    from tests.dungeon.test_materializer import _attach_pack, _reflecting_sdk_client

    monkeypatch.setattr(
        session_integration, "build_llm_client", _reflecting_sdk_client
    )

    store = SqliteStore.open_in_memory()
    snap = GameSnapshot(genre_slug="caverns_and_claudes", world_slug="beneath_sunden")
    snap.current_region = "entrance"

    exporter, _provider, real_tracer = _otel_in_memory()
    original_tracer_fn = _spans_module.tracer
    _spans_module.tracer = lambda: real_tracer  # type: ignore[method-assign]

    try:
        handle = await session_integration.attach_dungeon_to_session(
            store=store,
            snapshot=snap,
            genre_pack=_attach_pack("cave_in"),
            genre_slug="caverns_and_claudes",
            world_slug="beneath_sunden",
            world_dir=_beneath_sunden_world_dir(),
        )
        assert handle is not None
        assert frontier_hook.registered_observer_count() == 1, (
            "the look-ahead worker is not registered for the live session "
            "(observers=0 — the dungeon would not grow in a real game)"
        )

        ds = DungeonStore(store.connection())
        before = {n.expansion_id for n in ds.load_map(entrance_id="entrance").nodes.values()}
        assert before == {0, 1}, f"bootstrap did not seed expansion 0+1; got {before}"

        # A REAL production region transition toward an unexpanded
        # frontier edge rooted at an exp001 region.
        target = ds.load_frontier()[0].from_region_id
        snap.current_region = "entrance"
        snap.apply_world_patch(WorldStatePatch(current_region=target))
        await handle.drain()

        after = {n.expansion_id for n in ds.load_map(entrance_id="entrance").nodes.values()}
        assert max(after) >= 2, (
            f"region crossing toward an unexpanded frontier edge did NOT "
            f"materialize the next expansion; expansions={sorted(after)}"
        )

        # The lie-detector: frontier.region_transition carries observers>=1.
        finished = exporter.get_finished_spans()
        rt = [s for s in finished if s.name == SPAN_FRONTIER_REGION_TRANSITION]
        assert rt, "no frontier.region_transition span emitted (producer not fired)"
        assert any((s.attributes or {}).get("observers", 0) >= 1 for s in rt), (
            "every frontier.region_transition span has observers=0 — the "
            "seam fired but the session never registered a consumer (the "
            "ADR-106 lie-detector signal: dungeon does not grow)"
        )
    finally:
        await session_integration.detach_dungeon_from_session(
            handle if "handle" in dir() else None
        )
        _spans_module.tracer = original_tracer_fn  # type: ignore[method-assign]

    assert frontier_hook.registered_observer_count() == 0, (
        "detach did not unregister the observer (registry leak across "
        "sessions)"
    )
```

- [ ] **Step 2: Confirm the span constant name**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && grep -n "FRONTIER_REGION_TRANSITION\|region_transition" sidequest/telemetry/spans/dungeon_materialize.py`
Expected: a `SPAN_FRONTIER_REGION_TRANSITION = "frontier.region_transition"` (or equivalent) constant. If the exported name differs, use the actual constant in the import (do not hardcode the string — the span name is the contract). The producer (`frontier_hook.notify_region_transition`, dossier §5) emits `frontier_region_transition_span(... observers=len(_OBSERVERS))`.

- [ ] **Step 3: Run the wiring test**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest tests/dungeon/test_session_lifecycle_wiring.py -v`
Expected: PASS (1 passed). If it fails on `observers=0`, the connect/attach wiring is not actually invoked — fix the wiring, not the assertion (this assertion IS the deliverable).

- [ ] **Step 4: Full dungeon suite + targeted server gate**

Run:

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
uv run pytest tests/dungeon/ -v
uv run ruff check .
uv run pyright sidequest/dungeon/ sidequest/handlers/connect.py sidequest/server/session_handler.py sidequest/server/websocket_session_handler.py
```

Expected: dungeon suite PASS, ruff clean, pyright 0 errors on the changed surface.

- [ ] **Step 5: Commit**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
git add tests/dungeon/test_session_lifecycle_wiring.py
git commit -m "test(dungeon): keystone session-lifecycle wiring — observers>=1, real crossing grows the dungeon (Plan 7 §10)"
```

- [ ] **Step 6: Full server suite gate (final)**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run pytest -q`
Expected: green except any pre-existing, unrelated failures (e.g. content-subrepo `beneath_sunden/world.yaml` artifact gaps noted in MEMORY.md — verify any failure is pre-existing and NOT in `tests/dungeon/`, `tests/game/`, or the changed modules; if a dungeon/game test fails, it is in scope — fix forward, never revert the feature). Then push: `git push -u origin feat/beneath-sunden-plan-7-session-integration`.

---

## Self-Review

**1. Spec coverage:**
- §3 module boundary → Task 5 (`session_integration.py`, two functions, internal gate). ✔
- §4 dep resolution (6 deps) → Task 5 (`load_cookbook`, `load_theme_palette`, `DungeonStore(store.connection())`, `genre_pack`→pack_tropes, `build_llm_client()`, persisted seed). ✔ Task 1 supplies `connection()`.
- §5 seed persistence → Task 2 (`dungeon_meta`, write-once `get/set_campaign_seed`). ✔
- §6 idempotent bootstrap (Seed=Expansion-0) → Task 3 (builders) + Task 5 (already-seeded skip / fresh-save seed / seed reuse). ✔
- §7 SDK curate migration + shared-fake migration → Task 4. ✔
- §8 lifecycle incisions + `_SessionData` field → Task 6. ✔
- §9 error handling: fail-loud deps (Task 5 — `load_*` raise; `select_entrance_theme_id` raises; bootstrap `materialize` propagates), write-once seed (Task 2), central constraint preserved by reusing `register_lookahead_worker` verbatim (Task 5, no observer code added). ✔
- §10 testing: keystone wiring test → Task 7; idempotency/no-op/round-trip → Tasks 2,5; SDK curate unit → Task 4; existing suites green → Tasks 4,6,7. ✔
- §11 scope boundary: no streaming/broader SDK work; no #234 doc edits in this plan. ✔ (The spec §10 / Post-Impl "bottleneck CLOSED" recording is explicitly out of scope and is a post-merge verified deliverable.)
- §12 decomposition order → Tasks 1-7 match, reordered so Task 4 (SDK) precedes Task 5/7 that thread the SDK client. ✔
- §13 decisions: `CallType.SCRATCH` (Task 4 Step 4b); shallowest-band entrance theme (Task 3). ✔

**2. Placeholder scan:** No "TBD"/"TODO"/"similar to". Every code step has complete code; every command has an expected result. Task 6 has no isolated unit test by design (it is pure wiring proven by Task 7's integration test) — explicitly stated, not a gap. Task 7 Step 2 verifies the span constant name rather than guessing it (a concrete verification action, not a placeholder).

**3. Type/name consistency:** `connection()` (Task 1) used in Tasks 2-tests, 5, 7. `get_campaign_seed`/`set_campaign_seed` (Task 2) used in Task 5. `ENTRANCE_ID`/`build_entrance_seed_graph`/`build_expansion_one_request`/`select_entrance_theme_id` (Task 3) used in Task 5. `_reflecting_sdk_client`/`_failing_sdk_client` (Task 4) used in Tasks 5,7. `attach_dungeon_to_session`/`detach_dungeon_from_session` (Task 5) used in Task 6 incisions + Task 7. `lookahead_handle` field (Task 6) read in the cleanup incision + set in the connect incision. `register_lookahead_worker` kwargs match the dossier signature exactly. Consistent.

**Known residual to verify at execution (not placeholders — explicit verification steps in-task):** Task 7 Step 2 (exact span constant export name); Task 6 Step 1 (whether `session_handler.py` already has a `TYPE_CHECKING` block). Both have concrete in-task instructions.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-17-beneath-sunden-plan-7-session-integration.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage (spec → code-quality) review between tasks, fast iteration. This is the Plan 7 discipline the spec calls for.
2. **Inline Execution** — execute tasks in this session via executing-plans, batch with checkpoints.

Which approach?
