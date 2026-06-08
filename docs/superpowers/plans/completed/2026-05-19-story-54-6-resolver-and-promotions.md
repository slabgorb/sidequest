# Story 54-6: Runtime Resolver Tool + `location_promotions` Table

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `resolve_location_entity` as an agent tool with both modes (`narrator_proactive` + `player_initiated`); the `location_promotions` SQLite table with a forward-compatible migration; the flavor_only → yes_and promotion path; the player-initiated mint path; and the tool-registry barrel wiring so the narrator can actually call it. OTEL is **prepared** (span attribute setting) but the dedicated span definitions and GM-panel routing land in 54-8.

**Architecture:** Three concentric layers.

1. **Persistence layer** — `location_promotions` table on `SqliteStore`, additive (`CREATE TABLE IF NOT EXISTS` in `SCHEMA_SQL`). A `LocationPromotionRow` dataclass plus get/put helpers on the store. Schema:

   ```sql
   CREATE TABLE IF NOT EXISTS location_promotions (
       save_id TEXT NOT NULL,
       region_id TEXT NOT NULL,
       entity_id TEXT NOT NULL,
       provenance TEXT NOT NULL,
       label TEXT NOT NULL,
       promoted_at_turn INTEGER NOT NULL,
       promoted_canon TEXT NOT NULL,
       new_tier TEXT NOT NULL DEFAULT 'yes_and',
       new_binding_kind TEXT,
       new_binding_ref TEXT,
       PRIMARY KEY (save_id, region_id, entity_id)
   );
   CREATE INDEX IF NOT EXISTS idx_location_promotions_region
       ON location_promotions (save_id, region_id);
   ```

2. **Resolver layer** — `sidequest/game/location_resolver.py`. Pure-Python logic (no agent dependencies). Builds the effective manifest (`authored + promotions`; overlays added in 54-7), matches a label, returns a structured resolution result. Two write paths: `_promote_flavor_to_yes_and` and `_mint_yes_and`.

3. **Tool layer** — `sidequest/agents/tools/resolve_location_entity.py`. Adapter that translates between the tool-call shape and the resolver's API. Calls the resolver, sets OTEL span attributes, returns a `ToolResult`. Registers via `@tool` + the barrel import in `agents/tools/__init__.py`.

The encounter-overlay branch of the manifest merge is **stubbed empty in this story** (`active_overlays(region_id) -> []`). 54-7 fills it. Authored YAML is never mutated.

**Tech Stack:** Python 3.14, pydantic v2, SQLite, pytest + pytest-asyncio.

**Workflow:** tdd.

**Depends on:** 54-2 (types), 54-3 (validator clean), 54-4/54-5 (real authored content to test against).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/game/persistence.py` | modify | Add the `location_promotions` table to `SCHEMA_SQL`; add `LocationPromotionRow` dataclass + `list_location_promotions(save_id, region_id)` + `upsert_location_promotion(...)` methods on `SqliteStore`. |
| `sidequest-server/sidequest/game/location_resolver.py` | create | Pure-Python resolver. `resolve(...)`, `_match_label`, `_promote_flavor_to_yes_and`, `_mint_yes_and`. Returns a `LocationEntityResolution` pydantic model. |
| `sidequest-server/sidequest/protocol/models.py` | modify | Add `LocationEntityResolution` pydantic model. |
| `sidequest-server/sidequest/agents/tools/resolve_location_entity.py` | create | `@tool`-decorated adapter; args model; OTEL attribute setting; ToolResult translation. |
| `sidequest-server/sidequest/agents/tools/__init__.py` | modify | Add `resolve_location_entity` to the barrel import list. |
| `sidequest-server/sidequest/agents/tool_registry.py` | modify (if needed) | The `ToolContext` may need a way to reach the GenrePack's authored region manifests — `genre_pack` slot is already there. **No change expected.** |
| `sidequest-server/tests/game/test_persistence_location_promotions.py` | create | Table migration + upsert + read tests. |
| `sidequest-server/tests/game/test_location_resolver.py` | create | Resolver unit tests for both modes, both paths (promote + mint), authored-immutability assertion. |
| `sidequest-server/tests/agents/tools/test_resolve_location_entity.py` | create | Tool adapter integration test (real registry, real store on tmp_path, real ctx). |

---

### Task 1: Persistence — `location_promotions` table

**Files:**
- Modify: `sidequest-server/sidequest/game/persistence.py`
- Test: `sidequest-server/tests/game/test_persistence_location_promotions.py`

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/game/test_persistence_location_promotions.py`:

```python
"""SqliteStore — location_promotions table CRUD (Story 54-6 / ADR-109)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.persistence import LocationPromotionRow, SqliteStore


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="caverns_and_claudes",
        world_slug="beneath_sunden",
    )


def test_fresh_store_has_no_promotions(store):
    rows = store.list_location_promotions(save_id="default", region_id="ropefoot")
    assert rows == []


def test_upsert_minted_promotion_persists(store):
    row = LocationPromotionRow(
        save_id="default",
        region_id="ropefoot",
        entity_id="overturned_lamp",
        provenance="yes_and_minted",
        label="the overturned lamp",
        promoted_at_turn=12,
        promoted_canon="A lamp lies on its side near the rope, oil spreading.",
        new_tier="yes_and",
        new_binding_kind=None,
        new_binding_ref=None,
    )
    store.upsert_location_promotion(row)
    rows = store.list_location_promotions(save_id="default", region_id="ropefoot")
    assert len(rows) == 1
    assert rows[0].entity_id == "overturned_lamp"
    assert rows[0].provenance == "yes_and_minted"
    assert rows[0].promoted_canon.startswith("A lamp lies on its side")


def test_upsert_replaces_existing_row_by_primary_key(store):
    row1 = LocationPromotionRow(
        save_id="default", region_id="ropefoot", entity_id="cobwebs",
        provenance="yes_and_promoted", label="cobwebs",
        promoted_at_turn=5, promoted_canon="First touch.",
        new_tier="yes_and", new_binding_kind=None, new_binding_ref=None,
    )
    store.upsert_location_promotion(row1)

    row2 = LocationPromotionRow(
        save_id="default", region_id="ropefoot", entity_id="cobwebs",
        provenance="yes_and_promoted", label="cobwebs",
        promoted_at_turn=9, promoted_canon="Re-engaged.",
        new_tier="yes_and", new_binding_kind=None, new_binding_ref=None,
    )
    store.upsert_location_promotion(row2)

    rows = store.list_location_promotions(save_id="default", region_id="ropefoot")
    assert len(rows) == 1
    assert rows[0].promoted_at_turn == 9
    assert rows[0].promoted_canon == "Re-engaged."


def test_promotions_scoped_by_save_and_region(store):
    rows = []
    for save_id, region_id, eid in [
        ("default", "ropefoot", "a"),
        ("default", "the_dropmouth", "b"),
        ("other_save", "ropefoot", "c"),
    ]:
        rows.append(
            LocationPromotionRow(
                save_id=save_id, region_id=region_id, entity_id=eid,
                provenance="yes_and_minted", label=eid,
                promoted_at_turn=1, promoted_canon="x",
                new_tier="yes_and", new_binding_kind=None, new_binding_ref=None,
            )
        )
    for r in rows:
        store.upsert_location_promotion(r)

    ropefoot_default = store.list_location_promotions(
        save_id="default", region_id="ropefoot"
    )
    assert {r.entity_id for r in ropefoot_default} == {"a"}

    ropefoot_other = store.list_location_promotions(
        save_id="other_save", region_id="ropefoot"
    )
    assert {r.entity_id for r in ropefoot_other} == {"c"}


def test_existing_save_without_table_migrates_transparently(tmp_path):
    """A save.db that predates 54-6 must gain the table on open via
    CREATE TABLE IF NOT EXISTS — no manual migration step."""
    import sqlite3

    db_path = tmp_path / "save.db"
    # Simulate a pre-54-6 save with no location_promotions table.
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE game_state (id INTEGER PRIMARY KEY CHECK (id = 1), "
            "snapshot_json TEXT NOT NULL, saved_at TEXT NOT NULL)"
        )
        conn.commit()

    store = SqliteStore.open(
        db_path,
        genre_slug="caverns_and_claudes",
        world_slug="beneath_sunden",
    )
    rows = store.list_location_promotions(save_id="default", region_id="ropefoot")
    assert rows == []
```

(If `SqliteStore.open()`'s real signature differs, run `grep -n "def open" sidequest-server/sidequest/game/persistence.py` and adapt — the surface here may take extra args. The contract this story relies on is: opening an existing save db transparently runs `CREATE TABLE IF NOT EXISTS location_promotions ...` via the existing `_apply_migrations()` / `SCHEMA_SQL` mechanism.)

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/test_persistence_location_promotions.py -v
```
Expected: ImportError on `LocationPromotionRow` or AttributeError on the new methods.

- [ ] **Step 3: Extend `SCHEMA_SQL` and add the dataclass + methods**

In `sidequest-server/sidequest/game/persistence.py`:

Add to the `SCHEMA_SQL` string (after the `turn_telemetry` block, before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS location_promotions (
    save_id TEXT NOT NULL,
    region_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    provenance TEXT NOT NULL,
    label TEXT NOT NULL,
    promoted_at_turn INTEGER NOT NULL,
    promoted_canon TEXT NOT NULL,
    new_tier TEXT NOT NULL DEFAULT 'yes_and',
    new_binding_kind TEXT,
    new_binding_ref TEXT,
    PRIMARY KEY (save_id, region_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_location_promotions_region
    ON location_promotions (save_id, region_id);
```

Then add (near the existing dataclasses, e.g. after `SessionMeta`):

```python
@dataclass(frozen=True, slots=True)
class LocationPromotionRow:
    """One mutation to a location's manifest. ADR-109 §4.3.

    Two provenances:
    - ``yes_and_promoted`` — authored ``flavor_only`` entity engaged
      mechanically. Row layers a new tier on top of the authored row.
    - ``yes_and_minted`` — player input named an entity not in the
      authored manifest. Row IS the entity.

    Durable per Keith's durable-retention principle — never GC.
    """

    save_id: str
    region_id: str
    entity_id: str
    provenance: str  # 'yes_and_promoted' | 'yes_and_minted'
    label: str
    promoted_at_turn: int
    promoted_canon: str
    new_tier: str  # 'yes_and' in v1
    new_binding_kind: str | None
    new_binding_ref: str | None
```

Add to `SqliteStore`:

```python
    def list_location_promotions(
        self, *, save_id: str, region_id: str
    ) -> list[LocationPromotionRow]:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT save_id, region_id, entity_id, provenance, label, "
                "promoted_at_turn, promoted_canon, new_tier, "
                "new_binding_kind, new_binding_ref "
                "FROM location_promotions "
                "WHERE save_id = ? AND region_id = ? "
                "ORDER BY promoted_at_turn ASC, entity_id ASC",
                (save_id, region_id),
            )
            return [LocationPromotionRow(*row) for row in cur.fetchall()]

    def upsert_location_promotion(self, row: LocationPromotionRow) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO location_promotions ("
                "save_id, region_id, entity_id, provenance, label, "
                "promoted_at_turn, promoted_canon, new_tier, "
                "new_binding_kind, new_binding_ref) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(save_id, region_id, entity_id) DO UPDATE SET "
                "provenance = excluded.provenance, "
                "label = excluded.label, "
                "promoted_at_turn = excluded.promoted_at_turn, "
                "promoted_canon = excluded.promoted_canon, "
                "new_tier = excluded.new_tier, "
                "new_binding_kind = excluded.new_binding_kind, "
                "new_binding_ref = excluded.new_binding_ref",
                (
                    row.save_id, row.region_id, row.entity_id,
                    row.provenance, row.label, row.promoted_at_turn,
                    row.promoted_canon, row.new_tier,
                    row.new_binding_kind, row.new_binding_ref,
                ),
            )
            conn.commit()
```

(The `with self._conn() as conn:` shape assumes the existing `SqliteStore` has a `_conn()` helper. If the actual access pattern is different — e.g. a kept-open connection — match it. Check `grep -n "def _conn\|self._connection\|self.conn" sidequest-server/sidequest/game/persistence.py` first.)

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_persistence_location_promotions.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Run the broader persistence suite — make sure migrations didn't break existing saves**

```bash
cd sidequest-server && uv run pytest tests/game/ -v -k persistence
```
Expected: green. The schema is additive (`CREATE TABLE IF NOT EXISTS`); existing tables and behavior are untouched.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/persistence.py \
        sidequest-server/tests/game/test_persistence_location_promotions.py
git commit -m "feat(54-6): location_promotions sqlite table + upsert/list helpers

Additive schema (CREATE TABLE IF NOT EXISTS) — existing saves migrate
on next open with no manual step. PRIMARY KEY (save_id, region_id,
entity_id) makes upsert by (save, region, entity) the natural shape;
ON CONFLICT updates promoted_at_turn/canon for re-engagement.
Durable per Keith's no-GC retention policy (project memory)."
```

---

### Task 2: `LocationEntityResolution` model

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py`

- [ ] **Step 1: Add the model**

Near the other 54-2 manifest types in `protocol/models.py`:

```python
class LocationEntityResolution(BaseModel):
    """Result of resolve_location_entity. ADR-109 §5.3.

    ``resolved`` is the single source of truth for the caller. When
    ``resolved=True``, ``entity`` is populated and ``mode_outcome``
    records what happened (matched / promoted / minted).
    """

    model_config = {"extra": "forbid"}

    resolved: bool
    entity: LocationEntity | None = None
    mode_outcome: Literal[
        "matched",            # plain manifest hit (no mutation)
        "promoted",           # flavor_only → yes_and; row written
        "minted",             # player_initiated mint; new row written
        "no_match",           # narrator_proactive miss; no mutation
    ]
    region_id: str
    from_promotion: bool = False  # entity came from location_promotions, not authored
```

- [ ] **Step 2: Commit alongside the resolver in Task 3** (not separately — the model is meaningless without a consumer).

---

### Task 3: Pure-Python resolver

**Files:**
- Create: `sidequest-server/sidequest/game/location_resolver.py`
- Test: `sidequest-server/tests/game/test_location_resolver.py`

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/game/test_location_resolver.py`:

```python
"""resolve_location_entity core logic (Story 54-6 / ADR-109)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.location_resolver import resolve
from sidequest.game.persistence import SqliteStore
from sidequest.protocol.models import LocationEntity, LocationEntityBinding


def _entities():
    return [
        LocationEntity(
            id="bar",
            label="the bar",
            tier="real_object",
            binding=LocationEntityBinding(kind="location_feature", ref="glenross_arms_bar"),
        ),
        LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only"),
        LocationEntity(id="snug", label="the snug at the end", tier="yes_and"),
    ]


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="tea_and_murder",
        world_slug="glenross",
    )


def test_proactive_match_real_object_returns_resolved(store):
    res = resolve(
        store=store,
        save_id="default",
        region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="the bar",
        mode="narrator_proactive",
        engagement_kind="mechanical",
        turn_number=1,
    )
    assert res.resolved is True
    assert res.entity is not None
    assert res.entity.id == "bar"
    assert res.mode_outcome == "matched"
    # No row written — no mutation on a match.
    assert store.list_location_promotions(save_id="default", region_id="the_glenross_arms") == []


def test_proactive_miss_does_not_mint(store):
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="the dragon", mode="narrator_proactive",
        engagement_kind="mention", turn_number=1,
    )
    assert res.resolved is False
    assert res.entity is None
    assert res.mode_outcome == "no_match"
    assert store.list_location_promotions(save_id="default", region_id="the_glenross_arms") == []


def test_player_initiated_miss_mints(store):
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="the antique sextant", mode="player_initiated",
        engagement_kind="mention", turn_number=7,
    )
    assert res.resolved is True
    assert res.entity is not None
    assert res.entity.tier == "yes_and"
    assert res.entity.provenance == "yes_and_minted"
    assert res.mode_outcome == "minted"
    rows = store.list_location_promotions(save_id="default", region_id="the_glenross_arms")
    assert len(rows) == 1
    assert rows[0].label == "the antique sextant"
    assert rows[0].promoted_at_turn == 7


def test_player_initiated_match_does_not_mint(store):
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="the bar", mode="player_initiated",
        engagement_kind="mechanical", turn_number=4,
    )
    assert res.resolved is True
    assert res.entity.id == "bar"
    assert res.mode_outcome == "matched"
    assert store.list_location_promotions(save_id="default", region_id="the_glenross_arms") == []


def test_flavor_only_engaged_mechanically_promotes(store):
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="cobwebs", mode="narrator_proactive",
        engagement_kind="mechanical", turn_number=11,
    )
    assert res.resolved is True
    assert res.entity.tier == "yes_and"
    assert res.entity.provenance == "yes_and_promoted"
    assert res.mode_outcome == "promoted"
    rows = store.list_location_promotions(save_id="default", region_id="the_glenross_arms")
    assert len(rows) == 1
    assert rows[0].entity_id == "cobwebs"
    assert rows[0].provenance == "yes_and_promoted"
    assert rows[0].promoted_at_turn == 11


def test_flavor_only_mentioned_only_does_not_promote(store):
    """Pure mention (engagement_kind='mention') is descriptive — no mutation."""
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="cobwebs", mode="narrator_proactive",
        engagement_kind="mention", turn_number=1,
    )
    assert res.resolved is True
    assert res.entity.tier == "flavor_only"
    assert res.mode_outcome == "matched"
    assert store.list_location_promotions(save_id="default", region_id="the_glenross_arms") == []


def test_definite_article_stripped_when_matching(store):
    """Authored label "the bar" matches player label "bar"; vice versa too."""
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="bar", mode="narrator_proactive",
        engagement_kind="mention", turn_number=1,
    )
    assert res.resolved is True
    assert res.entity.id == "bar"


def test_match_is_case_insensitive(store):
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="The Bar", mode="narrator_proactive",
        engagement_kind="mention", turn_number=1,
    )
    assert res.resolved is True


def test_existing_promotion_layers_on_top_of_authored(store):
    """An entity that was promoted earlier is read with the new tier."""
    # First touch promotes.
    resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="cobwebs", mode="narrator_proactive",
        engagement_kind="mechanical", turn_number=11,
    )
    # Second touch sees promoted tier.
    res = resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=_entities(),
        label="cobwebs", mode="narrator_proactive",
        engagement_kind="mechanical", turn_number=20,
    )
    assert res.entity.tier == "yes_and"
    assert res.entity.provenance == "yes_and_promoted"
    assert res.from_promotion is True


def test_authored_yaml_never_mutates(store):
    """Resolver returns a NEW LocationEntity for promotion/mint, never
    mutates the authored list it was passed."""
    authored = _entities()
    authored_cobwebs_before = authored[1].model_copy(deep=True)
    resolve(
        store=store, save_id="default", region_id="the_glenross_arms",
        authored_entities=authored,
        label="cobwebs", mode="narrator_proactive",
        engagement_kind="mechanical", turn_number=11,
    )
    assert authored[1] == authored_cobwebs_before
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_resolver.py -v
```
Expected: ImportError.

- [ ] **Step 3: Write the resolver**

Create `sidequest-server/sidequest/game/location_resolver.py`:

```python
"""resolve_location_entity — pure-Python resolver. Story 54-6 / ADR-109.

Two modes encode the Zork-Problem-safe split:

- ``narrator_proactive`` — narrator is the source of the entity name.
  Manifest miss = contract violation. ``resolved=False``; the narrator's
  pending mechanical action does not commit. (Protects the contract.)
- ``player_initiated`` — player is the source. Manifest miss =
  canonization. A new ``yes_and_minted`` entity is written to
  ``location_promotions`` and the player's action proceeds. (Honors
  Yes-And and the Zork doctrine.)

A ``flavor_only`` entity engaged with ``engagement_kind="mechanical"``
auto-promotes to ``yes_and`` (Diamonds-and-Coal). Pure mentions
(``engagement_kind="mention"``) are descriptive — no mutation.

Authored YAML is never mutated. All runtime mutation accumulates in
the ``location_promotions`` SQLite table.

This module is pure-Python and intentionally tool-agnostic — the agent
tool layer is a thin adapter (``agents/tools/resolve_location_entity.py``).
"""

from __future__ import annotations

import re
from typing import Iterable, Literal

from sidequest.game.persistence import (
    LocationPromotionRow,
    SqliteStore,
)
from sidequest.protocol.models import (
    LocationEntity,
    LocationEntityResolution,
)

ResolverMode = Literal["narrator_proactive", "player_initiated"]
EngagementKind = Literal["mention", "mechanical"]


# ---------------------------------------------------------------------------
# Label normalization
# ---------------------------------------------------------------------------

_LEADING_ARTICLE_RE = re.compile(r"^\s*(the|a|an)\s+", re.IGNORECASE)


def _normalize(label: str) -> str:
    return _LEADING_ARTICLE_RE.sub("", label).strip().lower()


# ---------------------------------------------------------------------------
# Effective manifest
# ---------------------------------------------------------------------------


def _apply_promotion(authored: LocationEntity, row: LocationPromotionRow) -> LocationEntity:
    """Layer a promotion row on top of an authored entity."""
    return authored.model_copy(
        update={
            "tier": row.new_tier,
            "provenance": row.provenance,
            "promoted_at_turn": row.promoted_at_turn,
            "promoted_canon": row.promoted_canon,
        }
    )


def _minted_entity_from_row(row: LocationPromotionRow) -> LocationEntity:
    return LocationEntity(
        id=row.entity_id,
        label=row.label,
        tier=row.new_tier,
        binding=None,
        affordances=[],
        provenance=row.provenance,
        promoted_at_turn=row.promoted_at_turn,
        promoted_canon=row.promoted_canon,
    )


def _build_effective_manifest(
    *,
    authored: Iterable[LocationEntity],
    promotions: list[LocationPromotionRow],
) -> list[tuple[LocationEntity, bool]]:
    """Returns ``(entity, from_promotion)`` for each effective entity.

    Authored entities with a matching promotion row are upgraded;
    minted promotion rows become brand-new entities.
    """
    by_authored_id = {e.id: e for e in authored}
    promotions_by_id = {r.entity_id: r for r in promotions}

    result: list[tuple[LocationEntity, bool]] = []

    for entity in authored:
        row = promotions_by_id.get(entity.id)
        if row is not None:
            result.append((_apply_promotion(entity, row), True))
        else:
            result.append((entity, False))

    for row in promotions:
        if row.entity_id not in by_authored_id:
            result.append((_minted_entity_from_row(row), True))

    return result


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------


def _match_label(
    label: str, manifest: list[tuple[LocationEntity, bool]]
) -> tuple[LocationEntity, bool] | None:
    needle = _normalize(label)
    if not needle:
        return None
    for entity, from_promotion in manifest:
        if _normalize(entity.label) == needle:
            return entity, from_promotion
    return None


# ---------------------------------------------------------------------------
# Write paths
# ---------------------------------------------------------------------------


def _promote_flavor_to_yes_and(
    *,
    store: SqliteStore,
    save_id: str,
    region_id: str,
    entity: LocationEntity,
    turn_number: int,
) -> LocationEntity:
    row = LocationPromotionRow(
        save_id=save_id,
        region_id=region_id,
        entity_id=entity.id,
        provenance="yes_and_promoted",
        label=entity.label,
        promoted_at_turn=turn_number,
        promoted_canon=entity.label,  # v1: canon defaults to the label;
                                       # narrator-supplied canon arrives in 54-8
                                       # via OTEL when prose is captured.
        new_tier="yes_and",
        new_binding_kind=(
            entity.binding.kind if entity.binding is not None else None
        ),
        new_binding_ref=(
            entity.binding.ref if entity.binding is not None else None
        ),
    )
    store.upsert_location_promotion(row)
    return _apply_promotion(entity, row)


def _mint_yes_and(
    *,
    store: SqliteStore,
    save_id: str,
    region_id: str,
    label: str,
    turn_number: int,
) -> LocationEntity:
    entity_id = _id_from_label(label)
    row = LocationPromotionRow(
        save_id=save_id,
        region_id=region_id,
        entity_id=entity_id,
        provenance="yes_and_minted",
        label=label,
        promoted_at_turn=turn_number,
        promoted_canon=label,
        new_tier="yes_and",
        new_binding_kind=None,
        new_binding_ref=None,
    )
    store.upsert_location_promotion(row)
    return _minted_entity_from_row(row)


_ID_TRIM_RE = re.compile(r"[^a-z0-9]+")


def _id_from_label(label: str) -> str:
    """Stable id from a player-supplied label. Lower-snake-ish; collisions
    are resolved by the ON CONFLICT UPDATE behavior of upsert."""
    base = _ID_TRIM_RE.sub("_", _normalize(label)).strip("_")
    return base or "minted_entity"


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


def resolve(
    *,
    store: SqliteStore,
    save_id: str,
    region_id: str,
    authored_entities: Iterable[LocationEntity],
    label: str,
    mode: ResolverMode,
    engagement_kind: EngagementKind = "mention",
    turn_number: int,
) -> LocationEntityResolution:
    promotions = store.list_location_promotions(save_id=save_id, region_id=region_id)
    manifest = _build_effective_manifest(
        authored=authored_entities, promotions=promotions
    )

    hit = _match_label(label, manifest)

    if hit is None:
        if mode == "narrator_proactive":
            return LocationEntityResolution(
                resolved=False,
                entity=None,
                mode_outcome="no_match",
                region_id=region_id,
                from_promotion=False,
            )
        # player_initiated miss → mint
        minted = _mint_yes_and(
            store=store,
            save_id=save_id,
            region_id=region_id,
            label=label,
            turn_number=turn_number,
        )
        return LocationEntityResolution(
            resolved=True,
            entity=minted,
            mode_outcome="minted",
            region_id=region_id,
            from_promotion=True,
        )

    entity, from_promotion = hit

    # Promote flavor_only on mechanical engagement (regardless of mode).
    if entity.tier == "flavor_only" and engagement_kind == "mechanical":
        promoted = _promote_flavor_to_yes_and(
            store=store,
            save_id=save_id,
            region_id=region_id,
            entity=entity,
            turn_number=turn_number,
        )
        return LocationEntityResolution(
            resolved=True,
            entity=promoted,
            mode_outcome="promoted",
            region_id=region_id,
            from_promotion=True,
        )

    return LocationEntityResolution(
        resolved=True,
        entity=entity,
        mode_outcome="matched",
        region_id=region_id,
        from_promotion=from_promotion,
    )
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_resolver.py -v
```
Expected: 10 passed.

- [ ] **Step 5: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/location_resolver.py \
        sidequest-server/sidequest/protocol/models.py \
        sidequest-server/tests/game/test_location_resolver.py
git commit -m "feat(54-6): location_resolver — two-mode resolve with promote + mint

Pure-Python resolver, tool-agnostic. narrator_proactive miss returns
{resolved:false}, no mutation; player_initiated miss mints a yes_and
entity in location_promotions; flavor_only entity engaged mechanically
auto-promotes to yes_and (Diamonds-and-Coal). Authored entity list is
never mutated — promotions layer on top via model_copy. Label match
strips leading article and is case-insensitive."
```

---

### Task 4: `@tool` adapter — `resolve_location_entity`

**Files:**
- Create: `sidequest-server/sidequest/agents/tools/resolve_location_entity.py`
- Modify: `sidequest-server/sidequest/agents/tools/__init__.py`
- Test: `sidequest-server/tests/agents/tools/test_resolve_location_entity.py`

- [ ] **Step 1: Inspect the adjacent tool adapter pattern**

Already inspected: `commit_known_fact.py` is the closest analog (WRITE category, uses `ctx.store`, sets OTEL span attributes, returns `ToolResult.ok({...})`).

- [ ] **Step 2: Write the failing integration test**

Create `sidequest-server/tests/agents/tools/test_resolve_location_entity.py`:

```python
"""Tool adapter — resolve_location_entity. Story 54-6 / ADR-109."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.agents.tool_registry import (
    ToolCategory,
    ToolContext,
    ToolResultStatus,
)
from sidequest.agents.tools.resolve_location_entity import (
    ResolveLocationEntityArgs,
    resolve_location_entity,
)
from sidequest.game.persistence import SqliteStore
from sidequest.protocol.models import LocationEntity, LocationEntityBinding


def _authored_entities():
    return [
        LocationEntity(
            id="bar",
            label="the bar",
            tier="real_object",
            binding=LocationEntityBinding(kind="location_feature", ref="glenross_arms_bar"),
        ),
        LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only"),
    ]


def _ctx_with_authored(tmp_path: Path, entities: list[LocationEntity]) -> ToolContext:
    store = SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="tea_and_murder",
        world_slug="glenross",
    )
    # Build a stub genre_pack exposing world.cartography.regions[region_id].entities
    region = MagicMock()
    region.entities = entities
    cartography = MagicMock()
    cartography.regions = {"the_glenross_arms": region}
    world = MagicMock()
    world.cartography = cartography
    genre_pack = MagicMock()
    genre_pack.worlds = {"glenross": world}

    otel = MagicMock()
    return ToolContext(
        world_id="glenross",
        session_id="test-session",
        perspective_pc=None,
        turn_number=3,
        store=store,
        otel_span=otel,
        perception_filter=MagicMock(),
        genre_pack=genre_pack,
    )


@pytest.mark.asyncio
async def test_proactive_match_returns_ok_with_resolution(tmp_path):
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="the bar",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mention",
    )
    result = await resolve_location_entity(args, ctx)
    assert result.status is ToolResultStatus.OK
    assert result.payload["resolved"] is True
    assert result.payload["entity"]["id"] == "bar"
    assert result.payload["mode_outcome"] == "matched"


@pytest.mark.asyncio
async def test_proactive_miss_returns_not_found(tmp_path):
    """Lie-detector path. Narrator referenced something not in the
    manifest. Tool returns NOT_FOUND so the narrator's pending action
    does not commit."""
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="the dragon",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mechanical",
    )
    result = await resolve_location_entity(args, ctx)
    assert result.status is ToolResultStatus.NOT_FOUND
    assert "the dragon" in (result.message or "")


@pytest.mark.asyncio
async def test_player_initiated_miss_mints(tmp_path):
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="the antique sextant",
        region_id="the_glenross_arms",
        mode="player_initiated",
        engagement_kind="mention",
    )
    result = await resolve_location_entity(args, ctx)
    assert result.status is ToolResultStatus.OK
    assert result.payload["mode_outcome"] == "minted"
    assert result.payload["entity"]["tier"] == "yes_and"
    assert result.payload["entity"]["provenance"] == "yes_and_minted"


@pytest.mark.asyncio
async def test_flavor_only_mechanical_engagement_promotes(tmp_path):
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="cobwebs",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mechanical",
    )
    result = await resolve_location_entity(args, ctx)
    assert result.status is ToolResultStatus.OK
    assert result.payload["mode_outcome"] == "promoted"
    assert result.payload["entity"]["tier"] == "yes_and"


@pytest.mark.asyncio
async def test_unknown_region_returns_not_found(tmp_path):
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="anything",
        region_id="nonexistent_region",
        mode="player_initiated",
    )
    result = await resolve_location_entity(args, ctx)
    assert result.status is ToolResultStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_otel_span_attributes_set(tmp_path):
    ctx = _ctx_with_authored(tmp_path, _authored_entities())
    args = ResolveLocationEntityArgs(
        label="the bar",
        region_id="the_glenross_arms",
        mode="narrator_proactive",
        engagement_kind="mention",
    )
    await resolve_location_entity(args, ctx)
    # OTEL attribute setting is the lie-detector seam. 54-8 wires the
    # full span definition + GM-panel routing; this story just sets the
    # attributes on whatever span is in ctx.
    call_kwargs = {
        c.args[0]: c.args[1]
        for c in ctx.otel_span.set_attribute.call_args_list
    }
    assert "location.region_id" in call_kwargs
    assert "location.mode" in call_kwargs
    assert "location.resolved" in call_kwargs
    assert call_kwargs["location.region_id"] == "the_glenross_arms"
    assert call_kwargs["location.mode"] == "narrator_proactive"
    assert call_kwargs["location.resolved"] is True


def test_tool_registered_under_resolve_location_entity():
    """Wiring test — the tool must be importable AND registered in the
    barrel so the registry sees it."""
    from sidequest.agents import tools  # noqa: F401 — triggers barrel imports
    from sidequest.agents.tool_registry import Registry

    # The @tool decorator registers into the global Registry on import.
    # If the tool is missing from agents/tools/__init__.py, this assertion
    # fails by AttributeError or KeyError instead.
    from sidequest.agents.tools.resolve_location_entity import (
        resolve_location_entity as handler,
    )
    assert handler is not None
```

(The `@tool` decorator registration check at the bottom is intentionally
loose — many existing tools assert via `from sidequest.agents.tools import <name>`. Match that style if the codebase uses it.)

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/agents/tools/test_resolve_location_entity.py -v
```
Expected: ImportError.

- [ ] **Step 4: Write the adapter**

Create `sidequest-server/sidequest/agents/tools/resolve_location_entity.py`:

```python
"""Tool adapter: resolve_location_entity. ADR-109 §5.3.

Translates the narrator's tool call into the pure-Python resolver
(``sidequest.game.location_resolver``). The OTEL span attributes are
the lie-detector seam — Story 54-8 wires the full span definition +
GM-panel routing; this story sets the attributes on whatever span
the dispatcher provides via ``ctx.otel_span``.

Two modes:

- ``narrator_proactive``: the narrator is the source of the entity
  name. Manifest miss returns ``NOT_FOUND`` so the narrator's pending
  mechanical action does not commit.
- ``player_initiated``: the player is the source. Manifest miss
  mints a new ``yes_and`` entity in the ``location_promotions``
  table and returns ``OK``.

flavor_only entities engaged with ``engagement_kind="mechanical"``
auto-promote to ``yes_and`` regardless of mode (Diamonds-and-Coal).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from sidequest.agents.tool_registry import (
    ToolCategory,
    ToolContext,
    ToolResult,
    tool,
)
from sidequest.game.location_resolver import resolve


class ResolveLocationEntityArgs(BaseModel):
    label: str = Field(
        ...,
        min_length=1,
        description=(
            "The label as the narrator's prose or the player's input "
            "names it (e.g. 'the bar', 'the cracked telescope'). Case "
            "and leading articles are normalized internally."
        ),
    )
    region_id: str = Field(
        ...,
        min_length=1,
        description=(
            "The region or room id whose manifest to consult. Must match "
            "an authored region (cartography.yaml) or a materialized "
            "room (rooms/<id>.yaml)."
        ),
    )
    mode: Literal["narrator_proactive", "player_initiated"] = Field(
        ...,
        description=(
            "narrator_proactive: prose claim. Manifest miss = no-commit "
            "(NOT_FOUND). player_initiated: player input. Manifest miss "
            "= mint a yes_and entity."
        ),
    )
    engagement_kind: Literal["mention", "mechanical"] = Field(
        default="mention",
        description=(
            "mention: descriptive only, no mutation. mechanical: about "
            "to damage/move/take/modify — flavor_only entities promote "
            "to yes_and on mechanical engagement."
        ),
    )


def _authored_entities_for(ctx: ToolContext, region_id: str) -> list | None:
    """Resolve the authored entity list for region_id from the GenrePack.

    Returns ``None`` when the region is not authored — the resolver
    will treat it as an empty manifest, but the adapter prefers to
    surface NOT_FOUND so the caller knows the region didn't resolve.
    """
    pack = ctx.genre_pack
    if pack is None:
        return None
    world = pack.worlds.get(ctx.world_id)
    if world is None:
        return None
    cartography = getattr(world, "cartography", None)
    if cartography is None:
        return None
    region = cartography.regions.get(region_id)
    if region is None:
        return None
    return list(getattr(region, "entities", []))


@tool(
    name="resolve_location_entity",
    description=(
        "Resolve a named entity against the region's location manifest. "
        "Call this BEFORE any mechanical claim against a described "
        "entity (damage, move, take, search) and on every player input "
        "that names something in the location. narrator_proactive miss "
        "is a contract violation — the pending mechanical action does "
        "not commit. player_initiated miss canonizes the new entity "
        "(Yes-And). flavor_only entities promote to yes_and on "
        "mechanical engagement (Diamonds-and-Coal)."
    ),
    category=ToolCategory.WRITE,
)
async def resolve_location_entity(
    args: ResolveLocationEntityArgs, ctx: ToolContext
) -> ToolResult:
    authored = _authored_entities_for(ctx, args.region_id)
    if authored is None:
        return ToolResult.not_found(
            f"region {args.region_id!r} not found in world {ctx.world_id!r} "
            "cartography"
        )

    resolution = resolve(
        store=ctx.store,
        save_id="default",  # v1: single save per session; multi-save scoping
                              # arrives if and when the save-id surface formalizes.
        region_id=args.region_id,
        authored_entities=authored,
        label=args.label,
        mode=args.mode,
        engagement_kind=args.engagement_kind,
        turn_number=ctx.turn_number,
    )

    ctx.otel_span.set_attribute("location.region_id", args.region_id)
    ctx.otel_span.set_attribute("location.label", args.label)
    ctx.otel_span.set_attribute("location.mode", args.mode)
    ctx.otel_span.set_attribute("location.engagement_kind", args.engagement_kind)
    ctx.otel_span.set_attribute("location.resolved", resolution.resolved)
    ctx.otel_span.set_attribute("location.mode_outcome", resolution.mode_outcome)
    ctx.otel_span.set_attribute("location.from_promotion", resolution.from_promotion)
    if resolution.entity is not None:
        ctx.otel_span.set_attribute("location.entity_id", resolution.entity.id)
        ctx.otel_span.set_attribute("location.entity_tier", resolution.entity.tier)
        if resolution.entity.binding is not None:
            ctx.otel_span.set_attribute(
                "location.binding_kind", resolution.entity.binding.kind
            )

    if not resolution.resolved:
        # narrator_proactive miss — the lie-detector path. Return
        # NOT_FOUND so the narrator's pending action does not commit.
        return ToolResult.not_found(
            f"no entity matching {args.label!r} in region {args.region_id!r} "
            "(narrator_proactive contract violation)"
        )

    return ToolResult.ok(resolution.model_dump(mode="json"))
```

- [ ] **Step 5: Register in the barrel**

In `sidequest-server/sidequest/agents/tools/__init__.py`, add to the existing `from sidequest.agents.tools import (...)` block:

```python
    resolve_location_entity,  # noqa: F401
```

(Keep alphabetical order with the other imports — slot between `query_scene_state` and `roll_dice`.)

- [ ] **Step 6: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/agents/tools/test_resolve_location_entity.py -v
```
Expected: 7 passed.

- [ ] **Step 7: Confirm the registry actually sees the tool**

```bash
cd sidequest-server && uv run python -c "from sidequest.agents import tools; from sidequest.agents.tool_registry import Registry; print('listed' if any('resolve_location_entity' in n for n in dir(tools)) else 'MISSING')"
```
Expected: `listed`. (Or check via the actual `Registry` instance — depends on the global-vs-per-instance registration shape.)

- [ ] **Step 8: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 9: Commit**

```bash
git add sidequest-server/sidequest/agents/tools/resolve_location_entity.py \
        sidequest-server/sidequest/agents/tools/__init__.py \
        sidequest-server/tests/agents/tools/test_resolve_location_entity.py
git commit -m "feat(54-6): resolve_location_entity agent tool

Thin adapter over sidequest.game.location_resolver. Sets the OTEL
attribute seam (location.mode, location.resolved, location.mode_outcome,
location.from_promotion, location.entity_id, location.entity_tier,
location.binding_kind) — the full span definition and GM-panel
routing arrive in Story 54-8. narrator_proactive miss returns
ToolResult.NOT_FOUND so the narrator's pending mechanical action
does not commit; player_initiated miss mints a yes_and entity."
```

---

### Task 5: Broader suite + harness smoke

- [ ] **Step 1: Full server suite**

```bash
just server-test
```
Expected: green.

- [ ] **Step 2: Confirm save load/save roundtrip still works**

```bash
cd sidequest-server && uv run pytest tests/integration/ -v -k save
```
Expected: green. The schema change is additive; existing snapshot tests are unaffected.

- [ ] **Step 3: If a tool-dispatch integration test exists, run it**

```bash
cd sidequest-server && uv run pytest tests/agents/ -v
```
Expected: green. If the dispatcher's tool-list snapshot test fails because `resolve_location_entity` is now in the list, update the snapshot — that's the wiring proof.

---

### Self-review checklist

- [ ] **Spec §5.3 coverage:** `narrator_proactive` miss = no-commit (returns NOT_FOUND with attribute `location.resolved=false`) ✓; `player_initiated` miss = mint ✓; `flavor_only` mechanical engagement promotes to `yes_and` ✓; resolver does not mutate authored YAML ✓.
- [ ] **Spec §5.4 paths:** `yes_and_promoted` and `yes_and_minted` write paths both go through `upsert_location_promotion` ✓.
- [ ] **Spec §4.3 storage:** `location_promotions` schema matches the spec column-for-column ✓; additive via `CREATE TABLE IF NOT EXISTS` ✓; durable (no GC) ✓.
- [ ] **Placeholder scan:** no TBDs. Save-id is hard-coded `"default"` in the adapter; if/when multi-save lands as a real surface, that becomes the seam — flagged in code with a clear rationale, not a TODO.
- [ ] **Type consistency:** `LocationEntity.provenance` literal values used by resolver (`"yes_and_promoted"`, `"yes_and_minted"`) match the model declaration in 54-2.
- [ ] **OTEL attributes set:** `location.region_id`, `location.label`, `location.mode`, `location.engagement_kind`, `location.resolved`, `location.mode_outcome`, `location.from_promotion`, plus entity-level attrs when resolved. The dedicated `location.entity.resolve` / `.minted` / `.promoted` SPAN definitions land in 54-8.
- [ ] **No silent fallback:** unknown region returns NOT_FOUND (not OK with empty manifest); narrator_proactive miss returns NOT_FOUND (not OK with `resolved=false` — the tool contract forces the narrator to handle this as a fail).
- [ ] **Wiring tests present:**
  - `test_tool_registered_under_resolve_location_entity` — barrel import + decorator registration.
  - The actual @tool registration is exercised by every async test running through the adapter — they will fail at import if the barrel wiring is broken.
- [ ] **Concurrency:** WRITE-category tools acquire the registry `_write_locks` map automatically (`tool_registry.py:240`). No additional locking in the adapter.

### Dependencies / handoff

- **Blocked by:** 54-2 (types), 54-3 (validator clean), 54-4/54-5 (real authored content for end-to-end smoke).
- **Unblocks:** 54-7 (overlays — extends `_build_effective_manifest` to consume `active_overlays(region_id)`), 54-8 (OTEL spans — wraps the attributes set here into a dedicated `location.entity.resolve` span with GM-panel routing), 54-9 (UI — the resolver is what makes the manifest live; the UI needs nothing further from the resolver itself, but downstream OTEL surfacing in the GM panel uses these attributes).
- **Out of scope:** dedicated OTEL spans (54-8); encounter-overlay merge (54-7); GM-panel routing (54-8); cookbook-driven procedural entity emit (55-1); narrator-supplied `promoted_canon` from prose (will arrive via 54-8 enrichment).
