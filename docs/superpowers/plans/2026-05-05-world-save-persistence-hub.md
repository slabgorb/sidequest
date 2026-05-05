# World Save Persistence — Sünden Hub Item 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `world_save` storage layer that persists hub-world state (hireling roster, currency, Wall ledger, per-dungeon wound flags, latest-delve drift flag) across delves into different dungeons within the same campaign — surviving the per-slot reinit that clears the per-delve game state today.

**Architecture:** New singleton `world_save` table inside the existing per-slug `.db`, deliberately *excluded* from `_PER_SLOT_TABLES` so `SqliteStore.init_session()` does not clear it on a fresh delve. New `WorldSave` pydantic aggregate alongside `GameSnapshot` (kept structurally separate — delve state stays in `game_state`, hub state stays in `world_save`, no double-storage). New `SqliteStore.load_world_save()` / `save_world_save()` API. One read-side production consumer wired now (`GET /api/games/{slug}/hub`); write-side production consumers (recruit, delve-end commit, wall append, wound flag, drift flag) land in **engine plan item 4** (dungeon-pick UI), which is the natural orchestrator of those events. Until item 4 ships, this plan's writes are exercised by tests only — that gap is intentional and called out in §"Risks".

**Tech Stack:** Python 3.12, pydantic v2, stdlib `sqlite3`, FastAPI, pytest.

**Date:** 2026-05-05
**Status:** Draft
**Repo:** sidequest-server (everything; no content changes)
**Spec parent:** `docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md` §"Engine Surface" item 2
**Sibling plans:**
- `docs/superpowers/plans/completed/2026-05-04-genre-loader-dungeon-recursion.md` — item 1 (loader recursion). MERGED. Provides `World.dungeons` and the connect-handler hub guard this plan's read endpoint depends on.
- `docs/superpowers/plans/2026-05-05-stress-field-hireling.md` — item 3, *to be authored*. Will add the numeric stress accrual mechanics that mutate `Hireling.stress`. This plan only declares the field; it does not move it.
- `docs/superpowers/plans/2026-05-05-dungeon-pick-ui.md` — item 4, *to be authored*. Becomes the write-side consumer of every API in this plan (recruit hirelings, materialize delve party, commit-back on delve-end, append Wall entries, set wound/drift flags).
- `docs/superpowers/plans/2026-05-05-narrator-zones-drift-wound-wall.md` — items 5/6/7, *to be authored*. Becomes the read-side consumer of the drift/wound/wall fields when the narrator builds Hamlet-scene prompts.

---

## Why

The Sünden design (spec §"Sünden — the Hamlet" / §"Wounded Sins" / §"The Wall") promises a Darkest-Dungeon-shaped loop: **roll/recruit hirelings in Sünden → pick a dungeon → delve → survivors return → spend currency on stress relief → repeat.** Every word of that loop assumes data that survives a delve. Today's `SqliteStore.init_session()` *atomically clears* `_PER_SLOT_TABLES` on every reinit (`projection_cache, events, game_state, narrative_log, scrapbook_entries, lore_fragments`) so the per-delve session can start clean. That is the right behavior for delve state, and the wrong behavior for hub state. There is no second tier of persistence between "session-meta identity" (genre/world only) and "per-slot game state" (cleared on reinit). This plan introduces that second tier.

Without this storage, items 3 (stress field) and 4 (dungeon-pick UI) cannot land — both need a place to *put* hirelings between delves. Items 5/6/7 (narrator prompt zones for drift/wound/wall) cannot land — all three read flags this plan defines.

## Scope

This plan ends when:
- A hub-world `.db` carries a `world_save` row. Reading it returns a typed `WorldSave` populated with current roster, currency, wall entries, dungeon wounds, and latest-delve drift flag.
- `SqliteStore.init_session()` does **not** clear the `world_save` row. A test invokes `init_session()` against a save that already has a non-trivial `world_save` and asserts the row is byte-identical afterward.
- `GET /api/games/{slug}/hub` returns the WorldSave as JSON, plus an enriched dungeon list `[{slug, sin, wounded}, ...]` (slug from `World.dungeons`, sin from `Dungeon.config.sin` — item 1, wounded from `WorldSave.dungeon_wounds`). The richer payload eliminates the need for any client-side `SIN_BY_DUNGEON` mapping. 404 when slug doesn't exist; 409 with code `not_a_hub_world` when the slug's world has no dungeons.
- All other genre packs / leaf-world save behavior is bit-identical to today. Verified by a leaf-world load test.
- `tests/game/test_persistence.py` and the new `tests/game/test_world_save.py` are green. `just server-lint` clean.

**Explicitly NOT a goal of this plan:**
- The dungeon-pick UI route, the materialize-delve-party flow, or the commit-back-on-delve-end flow. Item 4.
- Stress accrual mechanics (numeric stress changes per encounter). Item 3.
- Narrator prompt-zone consumption of drift / wound / wall. Items 5–7.
- Stress-relief service mechanics (Confessional / Workhouse / Masquerade currency costs and cure rates). Item 4.

**Out of scope (separate, deliberately):**
- Save-file migration for legacy saves. Per `feedback_legacy_saves`, legacy saves are throwaway. Existing saves opened against the new code get a fresh empty `world_save` row via the lazy-on-first-read path; that's a feature, not a migration concern.
- Pre-populating `world_save` on every game-create (including non-hub worlds). Universal `WorldSave` was considered (every world gets a row regardless of hub-ness) and rejected as YAGNI. The lazy-on-first-read path means a non-hub save never accrues a `world_save` row at all.
- Multiplayer-shared roster semantics. The roster lives in `world_save`, which is per-slug; multiplayer slugs already share a `.db`, so multiplayer just works for free. No special MP code in this plan.
- Currency name. The spec defers this (§"Open Questions"). The field is `currency: int`.

## Design

### 1. Models — `sidequest/game/world_save.py` (new file)

A new module to keep the hub-shaped types out of the already-hefty `session.py`. Three pydantic v2 models:

```python
"""Hub-world persistence — survives ``SqliteStore.init_session()`` reinit.

This is the second tier of persistence: session_meta carries identity,
game_state carries the per-delve snapshot (cleared on reinit), and
world_save carries hub-shaped data that lives across delves into
different dungeons within one campaign.

Engine plan item 2 of the Hamlet-of-Sünden spec. Only the data layer
ships here. Mechanics that mutate these fields land in items 3 and 4
of the spec (see file header for plan links).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Hireling(BaseModel):
    """A roster member. Lives in WorldSave; materialized into
    GameSnapshot.characters at delve-start (item 4).

    The `stress` field is declared here for storage but its accrual
    mechanics are item 3 of the spec. This plan never increments it.
    """

    model_config = {"extra": "ignore"}

    # Stable identifier — slug-shaped, lowercase, alphanumeric + underscore.
    # The pattern is enforced so item 4a's recruit generator and items
    # 5/6/7's narrator-zone consumers cannot drift on shape (e.g. one
    # picks UUIDs, the other expects vol_1). The recruit generator owns
    # the construction; this field locks the contract.
    id: str = Field(pattern=r"^[a-z][a-z0-9_]+$")
    name: str                                # display name
    archetype: str                           # archetype slug from world archetypes.yaml
    stress: int = 0                          # 0..100 (item 3 enforces bounds)
    status: Literal["active", "dead", "missing"] = "active"
    recruited_at_delve: int = 0              # the WorldSave.delve_count when added
    notes: str = ""                          # narrator-emitted flavor; free text


class WallEntry(BaseModel):
    """One row of Sünden's Wall (the campaign-memory monument).

    Append-only ledger; the Wall does not erase. One entry per
    delve-resolution event, regardless of outcome.
    """

    model_config = {"extra": "ignore"}

    delve_number: int                        # 1-indexed, matches WorldSave.delve_count at write-time
    sin: str                                 # the dungeon's sin slug ("pride" | "greed" | "gluttony"); read from Dungeon.config.sin at write-time
    dungeon: str                             # dungeon slug ("grimvault" | "horden" | "mawdeep")
    party_hireling_ids: list[str]            # ids of the hirelings who delved (alive or dead)

    # Party fate. Three orthogonal-to-wound outcomes: cleared dungeon
    # without TPK (victory), TPK (defeat), or chose to leave alive
    # (retreat). The spec ("Wounded Sins") treats wound-status as a
    # SEPARATE flag — see ``wounded_boss`` below. This split lets
    # "TPK after wounding the boss" be recorded honestly instead of
    # being forced into a single conflated literal.
    outcome: Literal["victory", "defeat", "retreat"]

    # Did this delve culminate in the boss-floor / wound event the
    # spec calls out? Independent of ``outcome`` — a defeat can still
    # have wounded the boss. The post-delve apply step uses this flag
    # to flip ``WorldSave.dungeon_wounds[dungeon]``.
    wounded_boss: bool = False

    timestamp: datetime                      # write-time, UTC


class WorldSave(BaseModel):
    """Hub-world state that persists across delves.

    Each campaign (.db file) has at most one WorldSave row. Fresh hub
    worlds get a default-populated WorldSave on first read. Non-hub
    worlds never instantiate one (no production code reads them).
    """

    model_config = {"extra": "ignore"}

    roster: list[Hireling] = Field(default_factory=list)
    currency: int = 0
    wall: list[WallEntry] = Field(default_factory=list)

    # Per-dungeon wound flag. Keys are dungeon slugs from the genre pack;
    # absence means "not yet wounded". Item 4a flips the bool to True on
    # any delve-end where ``WallEntry.wounded_boss`` is True (regardless
    # of outcome — TPK-after-wound still wounds the dungeon). Once True,
    # never flips back (spec §"Wounded Sins": "A dungeon can only be
    # wounded once"). Item 6 reads the flag to merge wound_profile.yaml
    # into the Keeper definition.
    dungeon_wounds: dict[str, bool] = Field(default_factory=dict)

    # The most-recent-delve drift flag. None on a campaign with no
    # completed delves. Set by item 4 at delve-end; consumed by item 5
    # in the Hamlet-scene prompt zone. Overwritten on every subsequent
    # delve — the spec deliberately limits drift to the most recent.
    latest_delve_sin: str | None = None

    # Monotonic counter of completed delves (any outcome). Used as the
    # delve_number stamp for WallEntry and as the time-axis for any
    # future "recruited at delve N" UI affordances.
    delve_count: int = 0

    # ISO-8601 string set by save_world_save(); read for the GM panel.
    last_saved_at: datetime | None = None
```

### 2. Schema — extend `SCHEMA_SQL` in `persistence.py`

Add one new table inside the existing `SCHEMA_SQL` literal. Singleton, mirrors the `session_meta` / `game_state` shape:

```sql
CREATE TABLE IF NOT EXISTS world_save (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload_json TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
```

No migration step needed in `_apply_migrations()` — `CREATE TABLE IF NOT EXISTS` is the migration. Per `feedback_legacy_saves`, legacy saves opening against the new code path get the table created on `_init_schema()` and then take the lazy-create-empty-on-first-read path.

### 3. `_PER_SLOT_TABLES` — explicit non-membership

This is the load-bearing safety guarantee. The existing constant in `persistence.py`:

```python
_PER_SLOT_TABLES: tuple[str, ...] = (
    "projection_cache",
    "events",
    "game_state",
    "narrative_log",
    "scrapbook_entries",
    "lore_fragments",
)
```

stays unchanged in this plan. `world_save` is *deliberately not in this tuple*. Add a doc comment immediately above the constant naming the absence:

```python
# Per-slot tables that ``init_session()`` clears on reinit. ``games``
# (slug-keyed), ``scenario_archive`` (session_id-keyed), and
# ``world_save`` (singleton hub state — Sünden engine plan item 2) are
# all global lifecycle, not per-slot, and survive reinit. ``session_meta``
# is replaced (not cleared) by the INSERT OR REPLACE in ``init_session()``.
```

A test in task 7 enforces this by asserting `world_save` survives a `init_session()` call against a populated row.

### 4. SqliteStore — `load_world_save()` / `save_world_save()`

Two new methods on `SqliteStore`:

```python
def load_world_save(self) -> WorldSave:
    """Load this campaign's hub state, or a fresh empty WorldSave.

    Lazy-on-first-read: a save that predates this feature, or a new
    save in a non-hub world, returns a default-populated WorldSave
    without writing anything to disk. The first write happens via
    save_world_save() (called from item 4's recruit / delve-end flows).

    Raises SaveSchemaIncompatibleError on JSON or pydantic validation
    failure — same pattern as load(), so the websocket layer's typed
    error path catches it cleanly.
    """
    row = self._conn.execute(
        "SELECT payload_json FROM world_save WHERE id = 1"
    ).fetchone()
    if row is None:
        return WorldSave()
    try:
        raw = json.loads(row[0])
        return WorldSave.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise SaveSchemaIncompatibleError(
            save_path=self._path or Path("<in-memory>"),
            underlying=(
                exc if isinstance(exc, ValidationError)
                else ValidationError.from_exception_data(
                    title="invalid_world_save_json", line_errors=[]
                )
            ),
        ) from exc

def save_world_save(self, world_save: WorldSave) -> None:
    """Persist this campaign's hub state. Atomic via transaction."""
    now = datetime.now(tz=UTC)
    stamped = world_save.model_copy(update={"last_saved_at": now})
    payload_json = stamped.model_dump_json()
    with self._conn:
        self._conn.execute(
            """INSERT OR REPLACE INTO world_save (id, payload_json, saved_at)
               VALUES (1, ?, ?)""",
            (payload_json, now.isoformat()),
        )
```

`WorldSave` import goes at the top of `persistence.py` next to the existing `GameSnapshot` / `NarrativeEntry` imports from `sidequest.game.session`.

### 5. REST endpoint — `GET /api/games/{slug}/hub`

Add to `sidequest/server/rest.py`. Returns:
- `404` with `detail="no game with slug {slug}"` when the slug's `.db` does not exist (mirrors `GET /api/games/{slug}`).
- `409` with `detail={"code": "not_a_hub_world", "world_slug": "<slug>", "reason": "world has no dungeons"}` when the slug's world is not a hub. This is the *correct* terminal behavior — non-hub worlds have no hub state to report. Same loud-failure contract as the connect-handler hub guard from item 1.
- `200` with the WorldSave JSON plus an enumeration of available dungeons:

```python
from sidequest.genre.loader import (
    DEFAULT_GENRE_PACK_SEARCH_PATHS,
    load_genre_pack_cached,
)


@router.get("/api/games/{slug}/hub")
async def get_hub_state(slug: str, request: Request) -> dict:
    save_dir: Path = request.app.state.save_dir
    db = db_path_for_slug(save_dir, slug)
    if not db.exists():
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")
    store = SqliteStore(db)
    store.initialize()
    row = get_game(store, slug)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no game with slug {slug}")

    search_paths = getattr(
        request.app.state,
        "genre_pack_search_paths",
        DEFAULT_GENRE_PACK_SEARCH_PATHS,
    )
    genre_pack = load_genre_pack_cached(row.genre_slug, search_paths=search_paths)
    world = genre_pack.worlds.get(row.world_slug)
    if world is None or not world.dungeons:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "not_a_hub_world",
                "world_slug": row.world_slug,
                "reason": "world has no dungeons",
            },
        )

    world_save = store.load_world_save()
    # Enriched dungeon enumeration: ship slug + sin + wounded together
    # so the client doesn't need a hardcoded SIN_BY_DUNGEON map. The
    # sin comes from the loader-merged ``Dungeon.config.sin`` (item 1),
    # and wounded comes from this WorldSave. Future hub-world packs
    # (heavy_metal, mutant_wasteland) get sin-labeled UI for free.
    available_dungeons = [
        {
            "slug": dungeon_slug,
            "sin": world.dungeons[dungeon_slug].config.sin,
            "wounded": world_save.dungeon_wounds.get(dungeon_slug, False),
        }
        for dungeon_slug in sorted(world.dungeons)
    ]
    return {
        "slug": slug,
        "genre_slug": row.genre_slug,
        "world_slug": row.world_slug,
        "available_dungeons": available_dungeons,
        "world_save": world_save.model_dump(mode="json"),
    }
```

The loader access pattern (`load_genre_pack_cached` + `getattr(... "genre_pack_search_paths", DEFAULT_...)`) is verified against the existing rest.py contract: rest.py reads `app.state.genre_pack_search_paths` and falls back to `DEFAULT_GENRE_PACK_SEARCH_PATHS` for the same field elsewhere (rest.py:108-113). `load_genre_pack_cached` is the process-lifetime-cached helper at `sidequest.genre.loader:1280`. No other rest.py endpoint loads genre packs today — this is the first; the precedent is set here for future endpoints.

### 6. No write-side production consumer — call this out, do not stub

This plan deliberately ships zero production code that *writes* a `world_save` row. Recruit / delve-end / wall-append / wound-flag / drift-flag *triggers* are all item 4 territory; doing them here would either stub item 4 or build a half-wired flow. CLAUDE.md forbids both.

The wiring requirement ("every test suite needs a wiring test") is satisfied on the read side by the `GET /api/games/{slug}/hub` endpoint, which exercises `load_world_save()` end-to-end through a real route. The write side is exercised by the unit tests in task 7 and by the round-trip test in task 9, but no production caller writes a row until item 4 lands. That gap is **two days, not two months** — item 4 is the next plan and is the unblocker for actually playtesting Sünden. Calling it out so a reviewer can challenge the gap rather than letting it surprise them.

If item 4 slips materially (>1 sprint), the cheap defense is to add a CLI subcommand under `sidequest/cli/` — `sidequest worldsave dump <slug>` / `sidequest worldsave reset <slug>` — which gives a real production write consumer at zero design cost. Adding it preemptively is YAGNI.

## Tasks

### Task 1: New `world_save.py` module — `Hireling` model

**Files:**
- Create: `sidequest-server/sidequest/game/world_save.py`
- Test: `sidequest-server/tests/game/test_world_save.py` (new)

- [ ] **Step 1: Write the failing test for Hireling defaults**

```python
# tests/game/test_world_save.py
from sidequest.game.world_save import Hireling


def test_hireling_defaults_active_zero_stress():
    h = Hireling(id="vol_1", name="Volga Stein", archetype="prig")
    assert h.stress == 0
    assert h.status == "active"
    assert h.recruited_at_delve == 0
    assert h.notes == ""


def test_hireling_status_validates_literal():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Hireling(id="vol_1", name="x", archetype="x", status="ghost")  # type: ignore[arg-type]


def test_hireling_id_pattern_enforced():
    """Item 4a's recruit generator and items 5/6/7's narrator-zone
    consumers share this contract — locked at model boundary."""
    import pytest
    from pydantic import ValidationError
    # Valid shapes
    Hireling(id="vol_1", name="x", archetype="x")
    Hireling(id="prig_a3f", name="x", archetype="x")
    # Invalid shapes — must fail loud, no silent normalization
    for bad in ("Vol_1", "1vol", "vol-1", "vol 1", "", "vol!"):
        with pytest.raises(ValidationError):
            Hireling(id=bad, name="x", archetype="x")
```

- [ ] **Step 2: Run the tests; expect failure**

```bash
cd sidequest-server && uv run pytest tests/game/test_world_save.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.world_save'`.

- [ ] **Step 3: Create the module with the `Hireling` model**

Create `sidequest-server/sidequest/game/world_save.py` with the file-header docstring shown in §1 plus the `Hireling` model exactly as specified. Do NOT add `WallEntry` or `WorldSave` yet — separate tasks for each so the test that drives them can fail first.

- [ ] **Step 4: Run the tests; expect pass**

```bash
cd sidequest-server && uv run pytest tests/game/test_world_save.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/world_save.py sidequest-server/tests/game/test_world_save.py
git commit -m "feat(world_save): add Hireling model (Sünden engine plan item 2)"
```

### Task 2: `WallEntry` model

**Files:**
- Modify: `sidequest-server/sidequest/game/world_save.py`
- Modify: `sidequest-server/tests/game/test_world_save.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/game/test_world_save.py`:

```python
from datetime import UTC, datetime
from sidequest.game.world_save import WallEntry


def test_wall_entry_required_fields():
    e = WallEntry(
        delve_number=1,
        sin="pride",
        dungeon="grimvault",
        party_hireling_ids=["a", "b"],
        outcome="victory",
        timestamp=datetime.now(tz=UTC),
    )
    assert e.delve_number == 1
    assert e.party_hireling_ids == ["a", "b"]
    assert e.wounded_boss is False  # default


def test_wall_entry_outcome_validates_literal():
    """Outcome is the party-fate literal — wounded_dungeon is NOT here.
    Wound status lives on the orthogonal ``wounded_boss`` bool so that
    e.g. a TPK-after-wound is recordable as ``outcome=defeat``,
    ``wounded_boss=True``."""
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        WallEntry(
            delve_number=1,
            sin="pride",
            dungeon="grimvault",
            party_hireling_ids=[],
            outcome="wounded_dungeon",  # rejected — not a party-fate
            timestamp=datetime.now(tz=UTC),
        )


def test_wall_entry_wounded_boss_is_orthogonal_to_outcome():
    """All four (outcome, wounded_boss) combinations must construct."""
    for outcome in ("victory", "defeat", "retreat"):
        for wounded in (True, False):
            e = WallEntry(
                delve_number=1, sin="pride", dungeon="grimvault",
                party_hireling_ids=[], outcome=outcome,
                wounded_boss=wounded,
                timestamp=datetime.now(tz=UTC),
            )
            assert e.outcome == outcome
            assert e.wounded_boss is wounded
```

- [ ] **Step 2: Run; expect failure**

Expected: ImportError on `WallEntry`.

- [ ] **Step 3: Add `WallEntry` to `world_save.py`**

Exactly as specified in §1. Order in the file: `Hireling` → `WallEntry` → (next task adds `WorldSave`).

- [ ] **Step 4: Run; expect pass**

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/world_save.py sidequest-server/tests/game/test_world_save.py
git commit -m "feat(world_save): add WallEntry model"
```

### Task 3: `WorldSave` aggregate

**Files:**
- Modify: `sidequest-server/sidequest/game/world_save.py`
- Modify: `sidequest-server/tests/game/test_world_save.py`

- [ ] **Step 1: Write failing tests**

```python
from sidequest.game.world_save import WorldSave


def test_world_save_defaults_empty():
    ws = WorldSave()
    assert ws.roster == []
    assert ws.currency == 0
    assert ws.wall == []
    assert ws.dungeon_wounds == {}
    assert ws.latest_delve_sin is None
    assert ws.delve_count == 0
    assert ws.last_saved_at is None


def test_world_save_round_trip_json():
    ws = WorldSave(
        roster=[Hireling(id="vol_1", name="Volga", archetype="prig")],
        currency=42,
        dungeon_wounds={"grimvault": True},
        latest_delve_sin="pride",
        delve_count=3,
    )
    raw = ws.model_dump_json()
    ws2 = WorldSave.model_validate_json(raw)
    assert ws2.roster[0].name == "Volga"
    assert ws2.currency == 42
    assert ws2.dungeon_wounds == {"grimvault": True}
    assert ws2.latest_delve_sin == "pride"
    assert ws2.delve_count == 3
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Add `WorldSave` to `world_save.py`**

Exactly as specified in §1.

- [ ] **Step 4: Run; expect pass**

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/world_save.py sidequest-server/tests/game/test_world_save.py
git commit -m "feat(world_save): add WorldSave aggregate"
```

### Task 4: Schema — `world_save` table in `SCHEMA_SQL`

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Test: `sidequest-server/tests/game/test_persistence.py` (existing — find or add a schema-introspection test)

- [ ] **Step 1: Write failing test for table existence**

Append to `tests/game/test_persistence.py`:

```python
def test_world_save_table_created_on_init():
    store = SqliteStore.open_in_memory()
    rows = store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='world_save'"
    ).fetchall()
    assert len(rows) == 1, "world_save table must be created by _init_schema"
```

- [ ] **Step 2: Run; expect failure**

```bash
cd sidequest-server && uv run pytest tests/game/test_persistence.py::test_world_save_table_created_on_init -v
```
Expected: FAIL — table missing.

- [ ] **Step 3: Add the table to `SCHEMA_SQL`**

In `persistence.py`, append to the `SCHEMA_SQL` literal (after `projection_cache`):

```sql
CREATE TABLE IF NOT EXISTS world_save (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload_json TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
```

- [ ] **Step 4: Run; expect pass**

Expected: pass.

- [ ] **Step 5: Update the `_PER_SLOT_TABLES` doc comment**

In `persistence.py`, replace the existing comment block above `_PER_SLOT_TABLES` with the version specified in §3 of this plan (adds `world_save` to the named survivor list).

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py sidequest-server/tests/game/test_persistence.py
git commit -m "feat(persistence): add world_save table; document non-clear policy"
```

### Task 5: `SqliteStore.load_world_save()`

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Modify: `sidequest-server/tests/game/test_world_save.py`

- [ ] **Step 1: Write failing tests**

```python
from sidequest.game.persistence import SqliteStore


def test_load_world_save_empty_returns_default():
    store = SqliteStore.open_in_memory()
    ws = store.load_world_save()
    assert ws.roster == []
    assert ws.currency == 0
    assert ws.delve_count == 0


def test_load_world_save_invalid_json_raises():
    import pytest
    from sidequest.game.persistence import SaveSchemaIncompatibleError
    store = SqliteStore.open_in_memory()
    store._conn.execute(
        "INSERT INTO world_save (id, payload_json, saved_at) VALUES (1, ?, ?)",
        ("not json", "2026-05-05T00:00:00+00:00"),
    )
    store._conn.commit()
    with pytest.raises(SaveSchemaIncompatibleError):
        store.load_world_save()
```

- [ ] **Step 2: Run; expect failure**

Expected: AttributeError or NameError on `load_world_save`.

- [ ] **Step 3: Add `load_world_save` to `SqliteStore`**

In `persistence.py`:
- Add `from sidequest.game.world_save import WorldSave` next to the existing `GameSnapshot`/`NarrativeEntry` import.
- Add the `load_world_save` method on `SqliteStore` exactly as specified in §4.

- [ ] **Step 4: Run; expect pass**

Expected: 8 passed total in `test_world_save.py`.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py sidequest-server/tests/game/test_world_save.py
git commit -m "feat(persistence): SqliteStore.load_world_save lazy-creates empty default"
```

### Task 6: `SqliteStore.save_world_save()` — round-trip

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Modify: `sidequest-server/tests/game/test_world_save.py`

- [ ] **Step 1: Write failing tests**

```python
def test_save_world_save_round_trip():
    store = SqliteStore.open_in_memory()
    ws = WorldSave(
        roster=[Hireling(id="x", name="X", archetype="x")],
        currency=10,
        delve_count=1,
    )
    store.save_world_save(ws)
    reloaded = store.load_world_save()
    assert reloaded.currency == 10
    assert reloaded.delve_count == 1
    assert len(reloaded.roster) == 1
    assert reloaded.roster[0].name == "X"
    assert reloaded.last_saved_at is not None  # save_world_save stamps it


def test_save_world_save_overwrites_singleton():
    store = SqliteStore.open_in_memory()
    store.save_world_save(WorldSave(currency=1))
    store.save_world_save(WorldSave(currency=2))
    rows = store._conn.execute("SELECT COUNT(*) FROM world_save").fetchone()
    assert rows[0] == 1, "INSERT OR REPLACE must keep singleton invariant"
    assert store.load_world_save().currency == 2
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Add `save_world_save` to `SqliteStore`**

Exactly as specified in §4.

- [ ] **Step 4: Run; expect pass**

Expected: 10 passed total in `test_world_save.py`.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py sidequest-server/tests/game/test_world_save.py
git commit -m "feat(persistence): SqliteStore.save_world_save singleton round-trip"
```

### Task 7: `init_session()` does NOT clear `world_save` — the load-bearing safety test

**Files:**
- Modify: `sidequest-server/tests/game/test_world_save.py`

This is the test that justifies the entire architectural choice. Make it explicit and named for what it protects.

- [ ] **Step 1: Write failing test**

```python
def test_init_session_preserves_world_save_across_reinit():
    """Hub-state persistence guarantee — Sünden engine plan item 2.

    A delve-end / fresh-delve flow calls ``init_session()`` to clear
    per-slot tables. The roster, currency, Wall, wound flags, and
    drift flag MUST survive that reinit; otherwise a hireling roster
    is emptied between delves and the entire DD-shaped loop falls
    apart.
    """
    from datetime import UTC, datetime
    store = SqliteStore.open_in_memory()
    store.init_session("caverns_and_claudes", "caverns_three_sins")

    ws = WorldSave(
        roster=[Hireling(id="vol_1", name="Volga", archetype="prig", stress=15)],
        currency=42,
        wall=[WallEntry(
            delve_number=1, sin="pride", dungeon="grimvault",
            party_hireling_ids=["vol_1"], outcome="victory",
            wounded_boss=True,
            timestamp=datetime.now(tz=UTC),
        )],
        dungeon_wounds={"grimvault": True},
        latest_delve_sin="pride",
        delve_count=1,
    )
    store.save_world_save(ws)

    # Simulate the next delve starting — slot reinit clears per-slot tables.
    store.init_session("caverns_and_claudes", "caverns_three_sins")

    reloaded = store.load_world_save()
    assert reloaded.currency == 42
    assert reloaded.delve_count == 1
    assert reloaded.roster[0].name == "Volga"
    assert reloaded.roster[0].stress == 15
    assert reloaded.wall[0].sin == "pride"
    assert reloaded.wall[0].dungeon == "grimvault"
    assert reloaded.wall[0].wounded_boss is True
    assert reloaded.dungeon_wounds == {"grimvault": True}
    assert reloaded.latest_delve_sin == "pride"
```

This test passes the moment Task 4 lands (since `world_save` was never added to `_PER_SLOT_TABLES`), but it is *the* documenting test for the design choice. Write it now so the invariant is named.

- [ ] **Step 2: Run; expect pass**

```bash
cd sidequest-server && uv run pytest tests/game/test_world_save.py::test_init_session_preserves_world_save_across_reinit -v
```
Expected: PASS.

- [ ] **Step 3: Defensive — add the inverse test (per-delve state IS cleared)**

```python
def test_init_session_clears_game_state_but_keeps_world_save():
    store = SqliteStore.open_in_memory()
    store.init_session("caverns_and_claudes", "caverns_three_sins")
    # populate game_state and world_save
    store._conn.execute(
        "INSERT INTO game_state (id, snapshot_json, saved_at) VALUES (1, '{}', ?)",
        (datetime.now(tz=UTC).isoformat(),),
    )
    store._conn.commit()
    store.save_world_save(WorldSave(currency=99))

    store.init_session("caverns_and_claudes", "caverns_three_sins")

    game_state_rows = store._conn.execute("SELECT COUNT(*) FROM game_state").fetchone()[0]
    world_save_rows = store._conn.execute("SELECT COUNT(*) FROM world_save").fetchone()[0]
    assert game_state_rows == 0, "game_state must be cleared by init_session"
    assert world_save_rows == 1, "world_save must NOT be cleared by init_session"
    assert store.load_world_save().currency == 99
```

- [ ] **Step 4: Run; expect pass**

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/tests/game/test_world_save.py
git commit -m "test(world_save): init_session preserves hub state, clears delve state"
```

### Task 8: REST endpoint — `GET /api/games/{slug}/hub`

**Files:**
- Modify: `sidequest-server/sidequest/server/rest.py`
- Test: `sidequest-server/tests/server/test_rest_hub_endpoint.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# tests/server/test_rest_hub_endpoint.py
"""Wiring tests for GET /api/games/{slug}/hub.

Sünden engine plan item 2. Exercises load_world_save() through a real
HTTP route — the production read-side consumer.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidequest.game.persistence import (
    GameMode, SqliteStore, db_path_for_slug, upsert_game,
)
from sidequest.game.world_save import Hireling, WorldSave
from sidequest.server.app import create_app  # adapt if entry point differs


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(save_dir=tmp_path)  # adapt signature if needed
    return TestClient(app)


def _seed_game(save_dir: Path, slug: str, genre: str, world: str) -> SqliteStore:
    db = db_path_for_slug(save_dir, slug)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(db)
    store.initialize()
    upsert_game(store, slug=slug, mode=GameMode.SOLO,
                genre_slug=genre, world_slug=world)
    return store


def test_hub_endpoint_404_when_slug_missing(client: TestClient) -> None:
    r = client.get("/api/games/nope/hub")
    assert r.status_code == 404


def test_hub_endpoint_409_when_world_not_a_hub(
    client: TestClient, tmp_path: Path,
) -> None:
    # Use an existing leaf world from a non-Caverns pack
    _seed_game(tmp_path, "spgo-test", "space_opera", "coyote_star")
    r = client.get("/api/games/spgo-test/hub")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "not_a_hub_world"


def test_hub_endpoint_returns_world_save_and_dungeons(
    client: TestClient, tmp_path: Path,
) -> None:
    store = _seed_game(
        tmp_path, "cnc-test",
        "caverns_and_claudes", "caverns_three_sins",
    )
    store.save_world_save(WorldSave(
        roster=[Hireling(id="vol_1", name="Volga", archetype="prig", stress=7)],
        currency=33,
        delve_count=2,
    ))
    store.close()

    r = client.get("/api/games/cnc-test/hub")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "cnc-test"
    assert body["genre_slug"] == "caverns_and_claudes"
    assert body["world_slug"] == "caverns_three_sins"
    # Enriched dungeon enumeration: server ships {slug, sin, wounded}
    # so the client never needs a hardcoded SIN_BY_DUNGEON map.
    dungeons = body["available_dungeons"]
    assert [d["slug"] for d in dungeons] == ["grimvault", "horden", "mawdeep"]
    assert {d["slug"]: d["sin"] for d in dungeons} == {
        "grimvault": "pride", "horden": "greed", "mawdeep": "gluttony",
    }
    assert all(d["wounded"] is False for d in dungeons)  # fresh save
    assert body["world_save"]["currency"] == 33
    assert body["world_save"]["delve_count"] == 2
    assert body["world_save"]["roster"][0]["name"] == "Volga"
    assert body["world_save"]["roster"][0]["stress"] == 7


def test_hub_endpoint_marks_wounded_dungeons(
    client: TestClient, tmp_path: Path,
) -> None:
    """A wounded dungeon round-trips through the available_dungeons
    payload. Items 5/6/7 read this; locking it now."""
    store = _seed_game(
        tmp_path, "cnc-wound",
        "caverns_and_claudes", "caverns_three_sins",
    )
    store.save_world_save(WorldSave(
        dungeon_wounds={"grimvault": True},
    ))
    store.close()

    r = client.get("/api/games/cnc-wound/hub")
    assert r.status_code == 200
    dungeons = {d["slug"]: d for d in r.json()["available_dungeons"]}
    assert dungeons["grimvault"]["wounded"] is True
    assert dungeons["horden"]["wounded"] is False
    assert dungeons["mawdeep"]["wounded"] is False


def test_hub_endpoint_fresh_hub_save_returns_empty_world_save(
    client: TestClient, tmp_path: Path,
) -> None:
    """Lazy-on-first-read: a hub save with no world_save row returns
    a default-populated WorldSave, not 404 / 500."""
    _seed_game(
        tmp_path, "cnc-fresh",
        "caverns_and_claudes", "caverns_three_sins",
    )
    r = client.get("/api/games/cnc-fresh/hub")
    assert r.status_code == 200
    body = r.json()
    assert body["world_save"]["roster"] == []
    assert body["world_save"]["currency"] == 0
    assert body["world_save"]["delve_count"] == 0
    assert [d["slug"] for d in body["available_dungeons"]] == \
        ["grimvault", "horden", "mawdeep"]
```

- [ ] **Step 2: Run; expect failure**

```bash
cd sidequest-server && uv run pytest tests/server/test_rest_hub_endpoint.py -v
```
Expected: FAIL — endpoint not found (404 on every test, including the 200/409 ones).

- [ ] **Step 3: Add the endpoint to `rest.py`**

Insert the handler block from §5 verbatim, including the new imports (`load_genre_pack_cached`, `DEFAULT_GENRE_PACK_SEARCH_PATHS`). Place the handler next to the existing `GET /api/games/{slug}` for cohesion. The `load_genre_pack_cached` import goes in the existing `from sidequest.genre.loader import ...` block at the top of `rest.py` (line 34 today imports `DEFAULT_GENRE_PACK_SEARCH_PATHS` from this same module — extend that import).

- [ ] **Step 4: Run; expect pass**

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/rest.py sidequest-server/tests/server/test_rest_hub_endpoint.py
git commit -m "feat(rest): GET /api/games/{slug}/hub returns WorldSave + enriched dungeons"
```

### Task 9: Integration — round-trip across an actual file-backed `.db`

**Files:**
- Modify: `sidequest-server/tests/game/test_world_save.py`

In-memory tests don't catch path-handling bugs (e.g. WAL checkpoint behavior, the `_path` attribute on `SqliteStore`). One file-backed test.

- [ ] **Step 1: Write failing test**

```python
def test_world_save_round_trip_file_backed(tmp_path):
    db_path = tmp_path / "save.db"
    store = SqliteStore(db_path)
    store.init_session("caverns_and_claudes", "caverns_three_sins")
    store.save_world_save(WorldSave(currency=7, delve_count=1))
    store.close()

    # Re-open
    store2 = SqliteStore(db_path)
    ws = store2.load_world_save()
    assert ws.currency == 7
    assert ws.delve_count == 1
```

- [ ] **Step 2: Run; expect pass** (no new code needed — just locks the contract)

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/game/test_world_save.py
git commit -m "test(world_save): file-backed round-trip across reopen"
```

### Task 10: Run the full test suite + lint

- [ ] **Step 1: Run all server tests (genre + game + server scopes new code touches)**

```bash
cd sidequest-server && uv run pytest tests/game/ tests/server/test_rest_hub_endpoint.py -v
```
Expected: all green.

- [ ] **Step 2: Run lint**

```bash
cd sidequest-server && uv run ruff check sidequest/game/world_save.py sidequest/game/persistence.py sidequest/server/rest.py tests/game/test_world_save.py tests/server/test_rest_hub_endpoint.py
```
Expected: no findings.

- [ ] **Step 3: Confirm the broader test sweep is unchanged**

The 44 existing failures referenced in `feedback` must remain at the same failure count and at the same world-slug-missing point. Run:

```bash
cd sidequest-server && uv run pytest tests/server/ tests/integration/ 2>&1 | tail -20
```
Compare the failure count to develop's baseline (pre-this-plan). Expected: identical failure count, identical failures. Any *new* failure is a regression introduced by this plan and must be fixed before merging.

- [ ] **Step 4: Smoke — boot the server and hit the endpoint**

```bash
just up
# In another shell:
curl -s http://localhost:8765/api/games/does-not-exist/hub  # expect 404
# Optionally create a hub-world game via the lobby UI and hit:
# curl -s http://localhost:8765/api/games/<your-slug>/hub | jq .
just down
```

### Task 11: PR

- [ ] **Step 1: Push branch and open PR (gitflow → develop)**

```bash
cd sidequest-server
git push -u origin feat/world-save-persistence-hub
gh pr create --base develop --title "feat: world save persistence (Sünden item 2)" --body "$(cat <<'EOF'
## Summary
- Adds `WorldSave` (roster + currency + Wall + dungeon_wounds + latest_delve_sin)
  as a singleton row in a new `world_save` SQLite table.
- `SqliteStore.init_session()` deliberately does not clear `world_save`,
  so hub state survives the per-slot reinit between delves.
- `GET /api/games/{slug}/hub` returns the WorldSave + the world's dungeon list.
- 404 when slug missing, 409 with `not_a_hub_world` for non-hub worlds.
- No write-side production caller yet — those land in engine plan item 4
  (dungeon-pick UI). Tests cover the write API end-to-end.

## Plan
docs/superpowers/plans/2026-05-05-world-save-persistence-hub.md (orchestrator).

## Test plan
- [x] tests/game/test_world_save.py — model defaults, round-trip, init_session preserves
- [x] tests/server/test_rest_hub_endpoint.py — 404 / 409 / 200 / lazy-empty
- [x] file-backed round-trip
- [x] ruff clean
EOF
)"
```

## Risks

- **Universal-WorldSave temptation.** It is tempting to pre-populate `world_save` on every `POST /api/games` regardless of whether the world is a hub. Spec is silent on non-hub worlds; YAGNI says wait. The lazy-on-first-read path (`load_world_save() → WorldSave()` when no row) keeps non-hub saves byte-clean. *Mitigation:* §"Out of scope" calls this out; reviewer should reject any task drift in that direction.
- **First rest.py consumer of the genre loader.** No other rest.py endpoint loads genre packs today — this is the first. Pattern was verified against the loader public API (`load_genre_pack_cached` at `sidequest/genre/loader.py:1280`) and rest.py's existing use of `app.state.genre_pack_search_paths` (rest.py:95, :110-113). *Mitigation:* §5 commits to the exact import and call site; future rest.py endpoints needing pack data should follow this precedent.
- **Schema migration tax for legacy saves.** Per `feedback_legacy_saves`, legacy saves are throwaway. A legacy `.db` opened against new code creates the `world_save` table on `_init_schema()` (no-op for legacy data — empty table). First call to `load_world_save()` returns the default empty WorldSave. There is no migration code in this plan, and there should not be one. *Mitigation:* documented explicitly in §"Out of scope" so a reviewer doesn't ask for a migration step.
- **Write side has no production consumer until item 4.** Tests cover the API. Nothing in production calls `save_world_save()` until item 4 lands. This is honest, not stubbed (no half-wired flow exists; the storage layer is just dormant on the write side). The CLAUDE.md "every test suite needs a wiring test" rule is satisfied on the read side via the GET endpoint. *Mitigation:* §6 explains the gap; if item 4 slips materially (>1 sprint) add a CLI subcommand. Not adding it preemptively per YAGNI.
- **`Hireling.stress` is declared here but mutated by item 3.** A reviewer may ask why the field lives here if mechanics are elsewhere. The answer is storage shape — declaring `stress: int = 0` here is less invasive than having item 3 add the field to a model that already exists. *Mitigation:* docstring on `Hireling` calls out the split.
- **Currency name not committed.** Spec defers (§"Open Questions"). The field is `currency: int`. When the name is decided (item 4 at the latest), it surfaces in UI strings, not in this storage shape. *Mitigation:* none needed; the field stays `currency`.
- **Wall ordering invariant.** `wall: list[WallEntry]` is append-only by convention but the model does not enforce it. A bug elsewhere could insert / reorder. *Mitigation:* not in scope for this plan; item 4 owns the append API and its tests will assert append-only behavior. The current plan limits the surface to "the list exists and round-trips."

## Definition of Done

- All eleven tasks complete.
- `tests/game/test_world_save.py` and `tests/server/test_rest_hub_endpoint.py` green (~17 tests total — added: Hireling-id-pattern, WallEntry-wounded-orthogonal, hub-endpoint-wounded-flag).
- `tests/game/test_persistence.py::test_world_save_table_created_on_init` green.
- `just server-lint` clean on touched files.
- The 44 pre-existing test failures referenced in the loader plan's follow-on remain at exactly the same failure count and same failure point — neither fixed nor regressed.
- `just up` boots; `curl http://localhost:8765/api/games/does-not-exist/hub` returns 404 with the typed body; a fresh hub-world save returns 200 with empty WorldSave defaults.
- PR open against `slabgorb/sidequest-server` `develop` branch.
- Item 3 (stress mechanics) and item 4 (dungeon-pick UI) plans can now be drafted on top of this storage layer — the storage commitments this plan makes (Hireling shape, WorldSave shape, init_session non-clear policy, lazy-on-first-read) are the inputs those plans build on.
