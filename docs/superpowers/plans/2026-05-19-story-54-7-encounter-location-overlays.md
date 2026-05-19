# Story 54-7: Encounter Location Overlays — read-time merge + LOCATION_OVERLAY_CHANGED

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire encounter-bound `EncounterLocationOverlay` into the live system. Encounters carry an optional overlay that contributes (a) extra typed entities (`entity_delta`) and (b) a `prose_suffix` appended below the base description. Both are merged at **read time** — base manifest and base description never mutate. A new `LOCATION_OVERLAY_CHANGED` WebSocket message fires whenever an encounter touching a `bound_room_id` activates or deactivates.

**Architecture:** Three concentric layers.

1. **State** — `StructuredEncounter` (`sidequest/game/encounter.py`) gains an optional `location_overlay: EncounterLocationOverlay | None` field. Pure data, no behavior change for non-overlay encounters.

2. **Read** — `sidequest/game/location_view.py` (new, per spec §5.5) exposes `get_location_manifest(region_id, *, authored, snapshot, store, save_id)` and `get_location_prose(region_id, *, authored_description, snapshot)`. The resolver (`location_resolver.py:_build_effective_manifest`) is extended to accept an `overlays` parameter so 54-6's contract is preserved: when `overlays=[]` (the default) behavior is bit-for-bit unchanged.

3. **Emit** — a new `LOCATION_OVERLAY_CHANGED` message + `_maybe_emit_location_overlay_changed()` in `websocket_session_handler.py`. The emit site is the narration turn loop's existing encounter-transition guard (`prior_live` / `now_live` at lines 2717–2992): on `prior_live=False, now_live=True` with `enc.location_overlay`, emit `activate`; on `prior_live=True, now_live=False` with `prior_encounter.location_overlay`, emit `deactivate`. The existing `_maybe_emit_location_description` from 54-2 is updated to populate `payload.overlays` from the snapshot's active encounter so a fresh snapshot includes the live overlay.

Multiple overlays on the same room are concatenated in encounter-arrival order (v1 only has `snapshot.encounter` — one at a time — so the multi-overlay path is implemented via a list collector even though it can only carry zero or one item today; this keeps the seam open without speculative complexity).

This story does NOT add a new pydantic model, does NOT touch the resolver's promotion or mint logic, and does NOT render UI. The `EncounterLocationOverlay` model itself was already shipped by 54-2.

**Tech Stack:** Python 3.14, pydantic v2, pytest, FastAPI WebSocket.

**Workflow:** tdd.

**Depends on:** 54-2 (`EncounterLocationOverlay` model, `LocationDescriptionPayload.overlays`, `_maybe_emit_location_description`), 54-6 (`_build_effective_manifest` seam in `location_resolver.py`).

**Branch:** `feat/54-7-encounter-location-overlays` (off `develop`; subrepo `sidequest-server`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/game/encounter.py` | modify | Add `location_overlay: EncounterLocationOverlay | None = None` to `StructuredEncounter`. |
| `sidequest-server/sidequest/game/location_resolver.py` | modify | Extend `_build_effective_manifest` to accept an `overlays: list[EncounterLocationOverlay]` parameter; thread it through `resolve(...)` as a new kwarg with default `[]` (backward compatible). |
| `sidequest-server/sidequest/game/location_view.py` | create | Read-time merge per spec §5.5: `get_location_manifest()`, `get_location_prose()`, `active_overlays_for(snapshot, region_id)`. Pure functions, no I/O beyond `store.list_location_promotions`. |
| `sidequest-server/sidequest/protocol/enums.py` | modify | Add `MessageType.LOCATION_OVERLAY_CHANGED = "LOCATION_OVERLAY_CHANGED"`. |
| `sidequest-server/sidequest/protocol/models.py` | modify | Add `LocationOverlayChangedPayload` (region_id + overlays summary list). |
| `sidequest-server/sidequest/protocol/messages.py` | modify | Add `LocationOverlayChangedMessage`. Register in dispatch table. |
| `sidequest-server/sidequest/protocol/__init__.py` | modify | Re-export new classes. |
| `sidequest-server/sidequest/server/websocket_session_handler.py` | modify | Add `_maybe_emit_location_overlay_changed()`; call from the encounter-transition guard (lines ~2717 / ~2782 / ~2991). Update `_maybe_emit_location_description` to populate `payload.overlays` from the current snapshot's active overlay. |
| `sidequest-ui/src/types/protocol.ts` | modify | Add `MessageType.LOCATION_OVERLAY_CHANGED`. |
| `sidequest-ui/src/types/payloads.ts` | modify | Add `LocationOverlayChangedPayload` TS interface. |
| `sidequest-server/tests/game/test_encounter_location_overlay_field.py` | create | StructuredEncounter accepts `location_overlay`. |
| `sidequest-server/tests/game/test_location_view.py` | create | Read-time merge unit tests. |
| `sidequest-server/tests/game/test_location_resolver_overlays.py` | create | Resolver honours `overlays=` kwarg. |
| `sidequest-server/tests/protocol/test_location_overlay_changed_message.py` | create | Pydantic + enum + dispatch registry tests. |
| `sidequest-server/tests/server/test_location_overlay_emit.py` | create | Wiring test — emit fires from encounter activate/deactivate paths. |

---

### Task 1: Add `location_overlay` field to `StructuredEncounter`

**Files:**
- Modify: `sidequest-server/sidequest/game/encounter.py`
- Test: `sidequest-server/tests/game/test_encounter_location_overlay_field.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/game/test_encounter_location_overlay_field.py`:

```python
"""StructuredEncounter carries an optional EncounterLocationOverlay (Story 54-7)."""

from __future__ import annotations

from sidequest.game.encounter import (
    EncounterMetric,
    StructuredEncounter,
)
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
)


def _base_kwargs() -> dict:
    return {
        "encounter_type": "tavern_brawl",
        "player_metric": EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        "opponent_metric": EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
    }


def test_encounter_default_has_no_location_overlay():
    enc = StructuredEncounter(**_base_kwargs())
    assert enc.location_overlay is None


def test_encounter_accepts_location_overlay():
    overlay = EncounterLocationOverlay(
        bound_room_id="glenross_pub",
        entity_delta=[
            LocationEntity(
                id="overturned_table",
                label="an overturned table",
                tier="yes_and",
            ),
        ],
        prose_suffix="A chair lies in splinters by the door.",
    )
    enc = StructuredEncounter(**_base_kwargs(), location_overlay=overlay)
    assert enc.location_overlay is not None
    assert enc.location_overlay.bound_room_id == "glenross_pub"
    assert len(enc.location_overlay.entity_delta) == 1
    assert "splinters" in enc.location_overlay.prose_suffix
```

- [ ] **Step 2: Confirm fail**

Run:
```bash
cd sidequest-server && uv run pytest tests/game/test_encounter_location_overlay_field.py -v
```
Expected: FAIL — `StructuredEncounter` has no `location_overlay` field.

- [ ] **Step 3: Add the field**

In `sidequest-server/sidequest/game/encounter.py`, add the import at the top of the file (in the imports block, alongside the other `sidequest.protocol` imports — if none exist yet, add a `TYPE_CHECKING` block to avoid a circular import, then import at runtime under a guarded function only):

```python
from sidequest.protocol.models import EncounterLocationOverlay
```

If a `TYPE_CHECKING` guard is needed to avoid an import cycle (check by running the test suite after the direct import attempt — if `ImportError: cannot import name` fires, use the guard), use:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sidequest.protocol.models import EncounterLocationOverlay
```

…and quote the annotation: `location_overlay: "EncounterLocationOverlay | None" = None`.

Then add the field to `StructuredEncounter`, immediately after `taunt: TauntState = Field(default_factory=TauntState)` (around line 179):

```python
    # Story 54-7 / ADR-109: per-encounter location overlay. When set,
    # ``bound_room_id`` names the region/room whose manifest and prose
    # the overlay contributes to. Read-time merge in
    # ``sidequest.game.location_view`` layers ``entity_delta`` and
    # ``prose_suffix`` on top of the authored base; base never mutates.
    # ``None`` for encounters that have nothing to add to the room
    # description (the common case).
    location_overlay: EncounterLocationOverlay | None = None
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_encounter_location_overlay_field.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Run the broader encounter suite — no regression**

```bash
cd sidequest-server && uv run pytest tests/game/ -v -k encounter
```
Expected: full green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/encounter.py \
        sidequest-server/tests/game/test_encounter_location_overlay_field.py
git commit -m "feat(54-7): StructuredEncounter.location_overlay field

Optional EncounterLocationOverlay carried on each StructuredEncounter.
Read-time merge ships in Task 3; pure data shape here so existing
encounter creation paths default to None without explicit opt-in."
```

---

### Task 2: Extend resolver's `_build_effective_manifest` to accept overlays

**Files:**
- Modify: `sidequest-server/sidequest/game/location_resolver.py`
- Test: `sidequest-server/tests/game/test_location_resolver_overlays.py`

The 54-6 contract is: `_build_effective_manifest(authored, promotions)` → `[(entity, from_promotion)]`. Extending it with an `overlays` kwarg (default `[]`) preserves backward compatibility. The same kwarg is added to `resolve(...)` so the tool adapter can pass it in 54-8 / future stories.

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/game/test_location_resolver_overlays.py`:

```python
"""Resolver honours encounter overlays in the effective manifest (Story 54-7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.location_resolver import _build_effective_manifest, resolve
from sidequest.game.persistence import SqliteStore
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
    LocationEntityBinding,
)


def _authored() -> list[LocationEntity]:
    return [
        LocationEntity(
            id="bar",
            label="the bar",
            tier="real_object",
            binding=LocationEntityBinding(kind="location_feature", ref="glenross_arms_bar"),
        ),
        LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only"),
    ]


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="tea_and_murder",
        world_slug="glenross",
    )


def test_build_effective_manifest_accepts_empty_overlays_default():
    """Backward-compatible call signature: no overlays kwarg = old behavior."""
    out = _build_effective_manifest(authored=_authored(), promotions=[])
    ids = [e.id for e, _ in out]
    assert ids == ["bar", "cobwebs"]


def test_overlay_entity_delta_appends_to_manifest():
    overlay = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(
                id="overturned_table",
                label="an overturned table",
                tier="yes_and",
            ),
        ],
    )
    out = _build_effective_manifest(
        authored=_authored(), promotions=[], overlays=[overlay]
    )
    ids = [e.id for e, _ in out]
    assert ids == ["bar", "cobwebs", "overturned_table"]


def test_multiple_overlays_concatenated_in_arrival_order():
    overlay_a = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(id="a", label="a", tier="yes_and"),
        ],
    )
    overlay_b = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(id="b", label="b", tier="yes_and"),
        ],
    )
    out = _build_effective_manifest(
        authored=_authored(), promotions=[], overlays=[overlay_a, overlay_b]
    )
    # base ("bar", "cobwebs") + overlay_a ("a") + overlay_b ("b"), in that order.
    assert [e.id for e, _ in out] == ["bar", "cobwebs", "a", "b"]


def test_overlay_entity_matches_via_resolver(store):
    """Resolve a label that only exists in the overlay — must resolve."""
    overlay = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(
                id="overturned_table",
                label="an overturned table",
                tier="yes_and",
            ),
        ],
    )
    res = resolve(
        store=store,
        save_id="default",
        region_id="the_glenross_arms",
        authored_entities=_authored(),
        label="the overturned table",
        mode="narrator_proactive",
        engagement_kind="mention",
        turn_number=5,
        overlays=[overlay],
    )
    assert res.resolved is True
    assert res.entity is not None
    assert res.entity.id == "overturned_table"
    assert res.mode_outcome == "matched"


def test_overlay_entity_does_not_persist_to_promotions_table(store):
    """Overlay entities are encounter-scoped, never written to durable storage."""
    overlay = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(
                id="overturned_table",
                label="an overturned table",
                tier="yes_and",
            ),
        ],
    )
    resolve(
        store=store,
        save_id="default",
        region_id="the_glenross_arms",
        authored_entities=_authored(),
        label="the overturned table",
        mode="narrator_proactive",
        engagement_kind="mention",
        turn_number=5,
        overlays=[overlay],
    )
    rows = store.list_location_promotions(
        save_id="default", region_id="the_glenross_arms"
    )
    assert rows == []


def test_proactive_miss_when_label_not_in_authored_promotion_or_overlay(store):
    overlay = EncounterLocationOverlay(
        bound_room_id="the_glenross_arms",
        entity_delta=[
            LocationEntity(id="a", label="a", tier="yes_and"),
        ],
    )
    res = resolve(
        store=store,
        save_id="default",
        region_id="the_glenross_arms",
        authored_entities=_authored(),
        label="the dragon",
        mode="narrator_proactive",
        engagement_kind="mention",
        turn_number=1,
        overlays=[overlay],
    )
    assert res.resolved is False
    assert res.mode_outcome == "no_match"
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_resolver_overlays.py -v
```
Expected: FAIL — `_build_effective_manifest` doesn't accept `overlays`; `resolve` doesn't accept `overlays`.

- [ ] **Step 3: Extend the resolver**

In `sidequest-server/sidequest/game/location_resolver.py`, change `_build_effective_manifest`'s signature and body:

```python
def _build_effective_manifest(
    *,
    authored: Iterable[LocationEntity],
    promotions: list[LocationPromotionRow],
    overlays: Iterable["EncounterLocationOverlay"] = (),
) -> list[tuple[LocationEntity, bool]]:
    """Returns ``(entity, from_promotion)`` for each effective entity.

    Read order (spec §5.5):
        authored (with promotion-row overlay)
        + active overlays' entity_delta (encounter arrival order)
        + minted-only promotion rows (no authored entity to layer on top of)

    ``overlays`` defaults to ``()`` for backward compatibility with the
    54-6 resolver contract. The ``from_promotion`` flag stays semantically
    "did this entity come from a durable source other than authored?" —
    overlay entities are NOT promotions (they're encounter-scoped) so they
    are tagged ``from_promotion=False``.
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

    for overlay in overlays:
        for ent in overlay.entity_delta:
            result.append((ent, False))

    for row in promotions:
        if row.entity_id not in by_authored_id:
            result.append((_minted_entity_from_row(row), True))

    return result
```

Add the import at the top of the file:

```python
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
    LocationEntityResolution,
)
```

Then extend `resolve(...)` to thread the kwarg through. Change the signature:

```python
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
    overlays: Iterable[EncounterLocationOverlay] = (),
) -> LocationEntityResolution:
```

…and pass `overlays=overlays` into the `_build_effective_manifest(...)` call inside the function body:

```python
    promotions = store.list_location_promotions(save_id=save_id, region_id=region_id)
    manifest = _build_effective_manifest(
        authored=authored_entities, promotions=promotions, overlays=overlays
    )
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_resolver_overlays.py tests/game/test_location_resolver.py -v
```
Expected: all green. (The 54-6 tests still pass — default `overlays=()` is the old behavior.)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/location_resolver.py \
        sidequest-server/tests/game/test_location_resolver_overlays.py
git commit -m "feat(54-7): resolver accepts encounter overlays in effective manifest

Adds overlays= kwarg (default ()) to _build_effective_manifest and
resolve. Overlay entities append in encounter-arrival order between
authored+promotion entries and minted-only promotion entries. Overlay
entities are encounter-scoped — never persisted to location_promotions
— so they carry from_promotion=False through resolution. Backward
compatible: 54-6 callers that pass no overlays= see no behavior change."
```

---

### Task 3: `location_view` — `get_location_manifest`, `get_location_prose`, `active_overlays_for`

**Files:**
- Create: `sidequest-server/sidequest/game/location_view.py`
- Test: `sidequest-server/tests/game/test_location_view.py`

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/game/test_location_view.py`:

```python
"""Read-time merge helpers per spec §5.5 (Story 54-7)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidequest.game.encounter import EncounterMetric, StructuredEncounter
from sidequest.game.location_view import (
    active_overlays_for,
    get_location_manifest,
    get_location_prose,
)
from sidequest.game.persistence import SqliteStore
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
)


def _authored() -> list[LocationEntity]:
    return [
        LocationEntity(id="bar", label="the bar", tier="real_object"),
        LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only"),
    ]


def _enc_with_overlay(bound_room: str, *, resolved: bool = False) -> StructuredEncounter:
    return StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
        resolved=resolved,
        location_overlay=EncounterLocationOverlay(
            bound_room_id=bound_room,
            entity_delta=[
                LocationEntity(
                    id="overturned_table",
                    label="an overturned table",
                    tier="yes_and",
                ),
            ],
            prose_suffix="A chair lies in splinters by the door.",
        ),
    )


def test_active_overlays_for_empty_when_no_encounter():
    snapshot = MagicMock()
    snapshot.encounter = None
    assert active_overlays_for(snapshot, region_id="glenross_pub") == []


def test_active_overlays_for_returns_overlay_when_matched_and_live():
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("glenross_pub", resolved=False)
    overlays = active_overlays_for(snapshot, region_id="glenross_pub")
    assert len(overlays) == 1
    assert overlays[0].bound_room_id == "glenross_pub"


def test_active_overlays_for_empty_when_encounter_resolved():
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("glenross_pub", resolved=True)
    assert active_overlays_for(snapshot, region_id="glenross_pub") == []


def test_active_overlays_for_empty_when_bound_room_id_mismatch():
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("other_room", resolved=False)
    assert active_overlays_for(snapshot, region_id="glenross_pub") == []


def test_active_overlays_for_empty_when_encounter_has_no_overlay():
    snapshot = MagicMock()
    snapshot.encounter = StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
    )
    assert active_overlays_for(snapshot, region_id="glenross_pub") == []


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    return SqliteStore.open(
        tmp_path / "save.db",
        genre_slug="tea_and_murder",
        world_slug="glenross",
    )


def test_get_location_manifest_no_overlay(store):
    snapshot = MagicMock()
    snapshot.encounter = None
    manifest = get_location_manifest(
        region_id="glenross_pub",
        authored=_authored(),
        snapshot=snapshot,
        store=store,
        save_id="default",
    )
    assert [e.id for e in manifest] == ["bar", "cobwebs"]


def test_get_location_manifest_with_overlay(store):
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("glenross_pub")
    manifest = get_location_manifest(
        region_id="glenross_pub",
        authored=_authored(),
        snapshot=snapshot,
        store=store,
        save_id="default",
    )
    assert [e.id for e in manifest] == ["bar", "cobwebs", "overturned_table"]


def test_get_location_prose_no_overlay():
    snapshot = MagicMock()
    snapshot.encounter = None
    prose = get_location_prose(
        region_id="glenross_pub",
        authored_description="The pub door is ajar.",
        snapshot=snapshot,
    )
    assert prose == "The pub door is ajar."


def test_get_location_prose_appends_suffix():
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("glenross_pub")
    prose = get_location_prose(
        region_id="glenross_pub",
        authored_description="The pub door is ajar.",
        snapshot=snapshot,
    )
    assert prose == (
        "The pub door is ajar.\n\nA chair lies in splinters by the door."
    )


def test_get_location_prose_empty_authored_with_overlay():
    snapshot = MagicMock()
    snapshot.encounter = _enc_with_overlay("glenross_pub")
    prose = get_location_prose(
        region_id="glenross_pub",
        authored_description="",
        snapshot=snapshot,
    )
    # Don't emit a leading double-newline when base is empty.
    assert prose == "A chair lies in splinters by the door."


def test_get_location_prose_overlay_with_empty_suffix():
    """Overlay carries entity_delta but no prose_suffix — base unchanged."""
    enc = _enc_with_overlay("glenross_pub")
    enc.location_overlay.prose_suffix = ""
    snapshot = MagicMock()
    snapshot.encounter = enc
    prose = get_location_prose(
        region_id="glenross_pub",
        authored_description="The pub door is ajar.",
        snapshot=snapshot,
    )
    assert prose == "The pub door is ajar."
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_view.py -v
```
Expected: ImportError.

- [ ] **Step 3: Create `location_view.py`**

Create `sidequest-server/sidequest/game/location_view.py`:

```python
"""Read-time merge of authored manifest + promotions + encounter overlays.

Story 54-7 / ADR-109 §5.5. Pure functions: ``authored`` and
``authored_description`` come from the loader; ``snapshot`` carries the
live ``StructuredEncounter`` (with its optional ``location_overlay``);
``store`` is the SQLite layer that owns ``location_promotions``.

Authored YAML is never mutated. Promotions accumulate in
``location_promotions``. Encounter overlays are encounter-scoped — they
exist while ``snapshot.encounter`` is live and bound to the region, and
vanish when the encounter resolves.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from sidequest.game.location_resolver import _build_effective_manifest
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
)

if TYPE_CHECKING:
    from sidequest.game.persistence import SqliteStore
    from sidequest.game.session import GameSnapshot


def active_overlays_for(
    snapshot: "GameSnapshot", *, region_id: str
) -> list[EncounterLocationOverlay]:
    """Return every active encounter overlay bound to ``region_id``.

    V1 has at most one active encounter (``snapshot.encounter``), so this
    is at most a one-element list. The list shape is the seam for future
    multi-encounter support — keeps the read path uniform.
    """
    enc = getattr(snapshot, "encounter", None)
    if enc is None or enc.resolved:
        return []
    overlay = getattr(enc, "location_overlay", None)
    if overlay is None:
        return []
    if overlay.bound_room_id != region_id:
        return []
    return [overlay]


def get_location_manifest(
    *,
    region_id: str,
    authored: Iterable[LocationEntity],
    snapshot: "GameSnapshot",
    store: "SqliteStore",
    save_id: str = "default",
) -> list[LocationEntity]:
    """Effective manifest for ``region_id``: authored + overlays + promotions.

    Matches the resolver's effective-manifest order so the UI and the
    resolver agree on what's "in the room" at any moment.
    """
    overlays = active_overlays_for(snapshot, region_id=region_id)
    promotions = store.list_location_promotions(
        save_id=save_id, region_id=region_id
    )
    merged = _build_effective_manifest(
        authored=authored, promotions=promotions, overlays=overlays
    )
    return [entity for entity, _ in merged]


def get_location_prose(
    *,
    region_id: str,
    authored_description: str,
    snapshot: "GameSnapshot",
) -> str:
    """Effective prose for ``region_id``: base description + overlay suffixes.

    Suffixes joined by a blank line so the UI can render them as separate
    paragraphs without parsing. Empty suffixes are dropped. When the
    authored base is empty, the suffix-only string is returned without a
    leading separator (no orphan double-newline).
    """
    overlays = active_overlays_for(snapshot, region_id=region_id)
    suffixes = [o.prose_suffix for o in overlays if o.prose_suffix]
    if not suffixes:
        return authored_description
    joined_suffixes = "\n\n".join(suffixes)
    if not authored_description:
        return joined_suffixes
    return authored_description + "\n\n" + joined_suffixes
```

- [ ] **Step 4: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_location_view.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/game/location_view.py \
        sidequest-server/tests/game/test_location_view.py
git commit -m "feat(54-7): location_view read-time merge

get_location_manifest / get_location_prose / active_overlays_for —
pure functions per ADR-109 §5.5. Layers active encounter overlays
on top of authored manifest + promotions (manifest) and on top of
authored description (prose). Empty suffix dropped; empty base
with non-empty suffix returns suffix-only (no orphan separator)."
```

---

### Task 4: `LOCATION_OVERLAY_CHANGED` message — enum, payload, message class

**Files:**
- Modify: `sidequest-server/sidequest/protocol/enums.py`
- Modify: `sidequest-server/sidequest/protocol/models.py`
- Modify: `sidequest-server/sidequest/protocol/messages.py`
- Modify: `sidequest-server/sidequest/protocol/__init__.py`
- Test: `sidequest-server/tests/protocol/test_location_overlay_changed_message.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/protocol/test_location_overlay_changed_message.py`:

```python
"""LOCATION_OVERLAY_CHANGED message + payload (Story 54-7)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import LocationOverlayChangedMessage
from sidequest.protocol.models import (
    LocationDescriptionOverlaySummary,
    LocationOverlayChangedPayload,
)


def test_payload_minimum():
    payload = LocationOverlayChangedPayload(
        region_id="glenross_pub",
        overlays=[],
    )
    assert payload.region_id == "glenross_pub"
    assert payload.overlays == []


def test_payload_with_overlay_summary():
    payload = LocationOverlayChangedPayload(
        region_id="glenross_pub",
        overlays=[
            LocationDescriptionOverlaySummary(
                encounter_id="tavern_brawl-7",
                prose_suffix="A chair lies in splinters by the door.",
                entity_delta_count=1,
            ),
        ],
    )
    assert len(payload.overlays) == 1
    assert payload.overlays[0].encounter_id == "tavern_brawl-7"


def test_payload_blank_region_id_rejected():
    with pytest.raises(ValidationError):
        LocationOverlayChangedPayload(region_id="", overlays=[])


def test_payload_extra_field_rejected():
    with pytest.raises(ValidationError):
        LocationOverlayChangedPayload(  # type: ignore[call-arg]
            region_id="x", overlays=[], surprise="!"
        )


def test_message_roundtrip():
    msg = LocationOverlayChangedMessage(
        payload=LocationOverlayChangedPayload(
            region_id="glenross_pub",
            overlays=[
                LocationDescriptionOverlaySummary(
                    encounter_id="tavern_brawl-7",
                    prose_suffix="",
                    entity_delta_count=2,
                ),
            ],
        ),
        player_id="",
    )
    assert msg.type == MessageType.LOCATION_OVERLAY_CHANGED
    dumped = msg.model_dump()
    assert dumped["type"] == "LOCATION_OVERLAY_CHANGED"
    assert dumped["payload"]["region_id"] == "glenross_pub"
    assert dumped["payload"]["overlays"][0]["entity_delta_count"] == 2
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/protocol/test_location_overlay_changed_message.py -v
```
Expected: ImportError.

- [ ] **Step 3: Add the enum value**

In `sidequest-server/sidequest/protocol/enums.py`, immediately after `LOCATION_DESCRIPTION`:

```python
    # Story 54-7 / ADR-109: delta channel for encounter location overlay
    # state changes. Fires when an encounter with a non-None
    # location_overlay activates or deactivates touching a bound_room_id.
    LOCATION_OVERLAY_CHANGED = "LOCATION_OVERLAY_CHANGED"
```

- [ ] **Step 4: Add the payload**

In `sidequest-server/sidequest/protocol/models.py`, immediately after `LocationDescriptionPayload`:

```python
class LocationOverlayChangedPayload(BaseModel):
    """Delta payload for ``LOCATION_OVERLAY_CHANGED``.

    Story 54-7 / ADR-109 §5.5. Fires whenever an encounter's
    location_overlay activates or deactivates. ``overlays`` is the FULL
    current overlay set for the region after the transition (not a diff)
    so the UI can replace its overlay slice without reconciling
    enter/leave events.
    """

    model_config = {"extra": "forbid"}

    region_id: str = Field(min_length=1)
    overlays: list[LocationDescriptionOverlaySummary] = Field(default_factory=list)
```

- [ ] **Step 5: Add the message class**

In `sidequest-server/sidequest/protocol/messages.py`, immediately after `LocationDescriptionMessage`:

```python
class LocationOverlayChangedMessage(ProtocolBase):
    """GameMessage::LocationOverlayChanged — encounter overlay delta.

    Story 54-7 / ADR-109. Emitted on encounter activate (when the
    encounter has a location_overlay touching the party's current room)
    and on encounter resolve (deactivate). Payload carries the full
    post-transition overlay set for the region; on activate that's one
    overlay, on deactivate that's an empty list.
    """

    type: Literal[MessageType.LOCATION_OVERLAY_CHANGED] = (
        MessageType.LOCATION_OVERLAY_CHANGED
    )
    payload: LocationOverlayChangedPayload
    player_id: str = ""
```

Register in the dispatch table. Find every site where `"LOCATION_DESCRIPTION": LocationDescriptionMessage` is registered (added by 54-2). Use:

```bash
grep -rn '"LOCATION_DESCRIPTION": LocationDescriptionMessage' sidequest-server/sidequest -r
```

At each site, add:

```python
    "LOCATION_OVERLAY_CHANGED": LocationOverlayChangedMessage,
```

- [ ] **Step 6: Re-export**

In `sidequest-server/sidequest/protocol/__init__.py`, add `LocationOverlayChangedPayload` and `LocationOverlayChangedMessage` to the existing re-export block (alongside the 54-2 additions).

- [ ] **Step 7: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/protocol/test_location_overlay_changed_message.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/
git commit -m "feat(54-7): LOCATION_OVERLAY_CHANGED message + payload

Delta channel for encounter location overlay state. Payload carries
the FULL post-transition overlay set (not a diff) so the UI can
replace its overlay slice without reconciling enter/leave events.
54-2's LocationDescriptionOverlaySummary is reused as the per-overlay
shape."
```

---

### Task 5: Update `_maybe_emit_location_description` to populate `payload.overlays`

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py`
- Test: extend `sidequest-server/tests/server/test_location_description_emit.py` (the 54-2 test file)

54-2 ships with `payload.overlays = []` unconditionally. With encounter overlays now live, the snapshot emit must reflect the current state — otherwise a returning client on session resume sees stale base prose during an active overlay.

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/server/test_location_description_emit.py`:

```python
def test_emit_includes_active_overlay_in_payload(monkeypatch):
    """When an encounter with location_overlay is live and bound to the
    actor's room, the emitted LocationDescriptionPayload carries the
    overlay summary."""
    from unittest.mock import MagicMock
    from pathlib import Path

    from sidequest.game.encounter import (
        EncounterMetric,
        StructuredEncounter,
    )
    from sidequest.game.room_file_loader import load_room_payload
    from sidequest.protocol.messages import LocationDescriptionMessage
    from sidequest.protocol.models import (
        EncounterLocationOverlay,
        LocationEntity,
    )
    from sidequest.server.websocket_session_handler import (
        _maybe_emit_location_description,
    )

    here = Path(__file__).resolve()
    repo = here.parents[3]
    world_dir = (
        repo
        / "sidequest-content"
        / "genre_packs"
        / "caverns_and_claudes"
        / "worlds"
        / "caverns_sunden"
    )
    # Reuse the 54-2 fixture room.
    real_payload = load_room_payload(world_dir, "sunden_square")
    assert real_payload.entities, "fixture room must have entities"

    emit_fn = MagicMock()
    sd = MagicMock()
    sd.genre_slug = "caverns_and_claudes"
    sd.world_slug = "caverns_sunden"
    sd.player_id = ""

    enc = StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
        resolved=False,
        location_overlay=EncounterLocationOverlay(
            bound_room_id="sunden_square",
            entity_delta=[
                LocationEntity(
                    id="overturned_cart",
                    label="an overturned cart",
                    tier="yes_and",
                ),
            ],
            prose_suffix="Smoke drifts from the alley.",
        ),
    )
    snapshot = MagicMock()
    snapshot.character_locations = {"alice": "sunden_square"}
    snapshot.encounter = enc

    _maybe_emit_location_description(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        actor="alice",
        emit_fn=emit_fn,
    )

    emit_fn.assert_called_once()
    sent_msg, sent_type = emit_fn.call_args.args
    assert sent_type == "LOCATION_DESCRIPTION"
    assert isinstance(sent_msg, LocationDescriptionMessage)
    assert len(sent_msg.payload.overlays) == 1
    overlay = sent_msg.payload.overlays[0]
    assert overlay.prose_suffix == "Smoke drifts from the alley."
    assert overlay.entity_delta_count == 1
    assert "Smoke drifts" in sent_msg.payload.prose
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_description_emit.py::test_emit_includes_active_overlay_in_payload -v
```
Expected: FAIL — overlays list is empty (54-2's hard-coded `overlays=[]`).

- [ ] **Step 3: Update `_maybe_emit_location_description`**

In `sidequest-server/sidequest/server/websocket_session_handler.py`, find the `_maybe_emit_location_description` function (added by 54-2 — `grep -n "_maybe_emit_location_description" sidequest-server/sidequest/server/websocket_session_handler.py`).

Replace the prose + payload construction. Old (from 54-2):

```python
    payload = LocationDescriptionPayload(
        region_id=room_id,
        prose=prose,
        terrain=terrain,
        entities=entities,
        overlays=[],  # Story 54-7 populates this.
    )
```

New:

```python
    from sidequest.game.location_view import (
        active_overlays_for,
        get_location_prose,
    )
    from sidequest.protocol.models import (
        LocationDescriptionOverlaySummary,
    )

    # Story 54-7: layer active encounter overlay on top of the loaded base.
    effective_prose = get_location_prose(
        region_id=room_id,
        authored_description=prose,
        snapshot=snapshot,
    )
    active = active_overlays_for(snapshot, region_id=room_id)
    overlay_summaries = [
        LocationDescriptionOverlaySummary(
            encounter_id=_overlay_encounter_id(snapshot, room_id),
            prose_suffix=o.prose_suffix,
            entity_delta_count=len(o.entity_delta),
        )
        for o in active
    ]

    payload = LocationDescriptionPayload(
        region_id=room_id,
        prose=effective_prose,
        terrain=terrain,
        entities=entities,
        overlays=overlay_summaries,
    )
```

…and add the `_overlay_encounter_id` helper alongside `_maybe_emit_location_description`:

```python
def _overlay_encounter_id(snapshot: GameSnapshot, region_id: str) -> str:
    """Best-effort id for the encounter contributing the live overlay.

    StructuredEncounter has no stable instance id field today; encounter
    typing is keyed by encounter_type. The UI just needs *some* stable
    key per emit; encounter_type + bound_room_id is unique per active
    encounter in v1 (only one is active at a time per ADR-033).
    """
    enc = getattr(snapshot, "encounter", None)
    if enc is None or enc.resolved:
        return ""
    overlay = getattr(enc, "location_overlay", None)
    if overlay is None or overlay.bound_room_id != region_id:
        return ""
    return f"{enc.encounter_type}@{region_id}"
```

- [ ] **Step 4: Confirm green (focused)**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_description_emit.py -v
```
Expected: all four tests in the file pass — both the 54-2 baseline and the new overlay case.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/server/test_location_description_emit.py
git commit -m "feat(54-7): LOCATION_DESCRIPTION payload includes active overlay

get_location_prose + active_overlays_for merged into the existing
54-2 emit. Snapshot-side payload now carries effective prose (base +
suffix) and a non-empty overlays list when an encounter overlay is
live. Returning clients on session resume see the live overlay state
without waiting for a separate LOCATION_OVERLAY_CHANGED delta."
```

---

### Task 6: Emit `LOCATION_OVERLAY_CHANGED` on encounter activate/deactivate

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py`
- Test: `sidequest-server/tests/server/test_location_overlay_emit.py`

This is the **wiring test** required by CLAUDE.md — proves the emit fires from production transition detection, not just exists as a function.

The encounter-transition site is already in place — `websocket_session_handler.py` lines 2717–2992 capture `prior_live` / `now_live` and detect `encounter_resolved_this_turn`. Hook into that scope.

- [ ] **Step 1: Read the existing transition code**

Run:
```bash
sed -n '2710,2725p;2780,2790p;2985,3000p' sidequest-server/sidequest/server/websocket_session_handler.py
```
Note the variable names: `prior_encounter`, `prior_live`, `encounter_resolved_this_turn`, `now_encounter`, `now_live`. The activate edge is `prior_live=False and now_live=True`. The deactivate edge is `encounter_resolved_this_turn` (already set, line 2782).

- [ ] **Step 2: Write the failing wiring tests**

Create `sidequest-server/tests/server/test_location_overlay_emit.py`:

```python
"""Wiring test: LOCATION_OVERLAY_CHANGED fires on encounter activate + deactivate.

Story 54-7 / ADR-109. CLAUDE.md "Every test suite needs a wiring test" —
proves _maybe_emit_location_overlay_changed has a non-test caller in the
session handler.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sidequest.game.encounter import (
    EncounterMetric,
    StructuredEncounter,
)
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import LocationOverlayChangedMessage
from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
)
from sidequest.server.websocket_session_handler import (
    _maybe_emit_location_overlay_changed,
)


def _enc(*, resolved: bool = False) -> StructuredEncounter:
    return StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
        resolved=resolved,
        location_overlay=EncounterLocationOverlay(
            bound_room_id="glenross_pub",
            entity_delta=[
                LocationEntity(
                    id="overturned_table",
                    label="an overturned table",
                    tier="yes_and",
                ),
            ],
            prose_suffix="A chair lies in splinters by the door.",
        ),
    )


def test_activate_emits_with_overlay_in_payload():
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.genre_slug = "tea_and_murder"
    sd.world_slug = "glenross"
    sd.player_id = ""
    snapshot = MagicMock()
    snapshot.encounter = _enc(resolved=False)

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="activate",
        emit_fn=emit_fn,
    )

    emit_fn.assert_called_once()
    sent_msg, sent_type = emit_fn.call_args.args
    assert sent_type == "LOCATION_OVERLAY_CHANGED"
    assert isinstance(sent_msg, LocationOverlayChangedMessage)
    assert sent_msg.type == MessageType.LOCATION_OVERLAY_CHANGED
    assert sent_msg.payload.region_id == "glenross_pub"
    assert len(sent_msg.payload.overlays) == 1


def test_deactivate_emits_with_empty_overlay_list():
    """When the encounter has just resolved, payload.overlays is empty —
    the UI replaces its overlay slice rather than reconciling diffs."""
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.player_id = ""
    snapshot = MagicMock()
    # Deactivate path: pass the prior overlay explicitly so the emitter
    # knows which region_id was affected.
    prior_overlay = EncounterLocationOverlay(
        bound_room_id="glenross_pub",
        entity_delta=[],
        prose_suffix="A chair lies in splinters by the door.",
    )

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="deactivate",
        emit_fn=emit_fn,
        prior_overlay=prior_overlay,
    )

    emit_fn.assert_called_once()
    sent_msg, sent_type = emit_fn.call_args.args
    assert sent_type == "LOCATION_OVERLAY_CHANGED"
    assert sent_msg.payload.region_id == "glenross_pub"
    assert sent_msg.payload.overlays == []


def test_activate_skips_when_encounter_has_no_overlay():
    """Encounters without location_overlay never emit."""
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.player_id = ""
    snapshot = MagicMock()
    snapshot.encounter = StructuredEncounter(
        encounter_type="tavern_brawl",
        player_metric=EncounterMetric(
            name="composure", current=10, starting=10, threshold=20
        ),
        opponent_metric=EncounterMetric(
            name="brawl_energy", current=10, starting=10, threshold=20
        ),
    )

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="activate",
        emit_fn=emit_fn,
    )
    emit_fn.assert_not_called()


def test_deactivate_skips_when_no_prior_overlay():
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.player_id = ""
    snapshot = MagicMock()

    _maybe_emit_location_overlay_changed(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        transition="deactivate",
        emit_fn=emit_fn,
        prior_overlay=None,
    )
    emit_fn.assert_not_called()


def test_overlay_emit_called_from_encounter_transition_dispatch():
    """Static wiring proof — production code paths invoke the emit helper.

    CLAUDE.md "Verify wiring, not just existence." We grep the handler
    source for the call sites instead of running the whole narration
    pipeline; the two transition edges are the activate path right after
    encounter instantiation and the deactivate path inside the
    encounter_resolved_this_turn branch.
    """
    from pathlib import Path

    here = Path(__file__).resolve()
    handler_src = (
        here.parents[3]
        / "sidequest-server"
        / "sidequest"
        / "server"
        / "websocket_session_handler.py"
    ).read_text()
    assert "def _maybe_emit_location_overlay_changed(" in handler_src
    call_count = handler_src.count("_maybe_emit_location_overlay_changed(")
    # 1 def + 2 call sites (activate, deactivate) = 3 minimum.
    assert call_count >= 3, (
        f"expected definition + activate + deactivate call sites, "
        f"found {call_count} mentions"
    )
```

- [ ] **Step 3: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_overlay_emit.py -v
```
Expected: ImportError on `_maybe_emit_location_overlay_changed`.

- [ ] **Step 4: Add the emit helper**

In `sidequest-server/sidequest/server/websocket_session_handler.py`, add after `_maybe_emit_location_description`:

```python
def _maybe_emit_location_overlay_changed(
    handler: object,
    *,
    sd: _SessionData,
    snapshot: GameSnapshot,
    transition: str,
    emit_fn: object,
    prior_overlay: "EncounterLocationOverlay | None" = None,
) -> None:
    """Emit LOCATION_OVERLAY_CHANGED on encounter overlay activate/deactivate.

    Story 54-7 / ADR-109 §5.5. ``transition`` is ``"activate"`` or
    ``"deactivate"``:

    - **activate** — called right after ``snapshot.encounter`` is set
      to a new encounter (the existing ``prior_live=False, now_live=True``
      edge in the narration turn loop). Reads the overlay off the live
      encounter; no-op when the encounter has no location_overlay.
    - **deactivate** — called inside the ``encounter_resolved_this_turn``
      branch. ``prior_overlay`` is passed by the caller (the prior
      encounter has been replaced or cleared by this point). No-op when
      ``prior_overlay`` is None.

    The payload carries the FULL post-transition overlay set — on
    activate that's one item, on deactivate that's an empty list. The UI
    replaces its overlay slice rather than reconciling diffs (54-9).
    """
    from sidequest.protocol.messages import LocationOverlayChangedMessage
    from sidequest.protocol.models import (
        EncounterLocationOverlay,
        LocationDescriptionOverlaySummary,
        LocationOverlayChangedPayload,
    )

    region_id: str
    overlay_summaries: list[LocationDescriptionOverlaySummary]
    encounter_id_str: str

    if transition == "activate":
        enc = getattr(snapshot, "encounter", None)
        if enc is None or enc.resolved:
            return
        overlay = getattr(enc, "location_overlay", None)
        if overlay is None:
            return
        region_id = overlay.bound_room_id
        encounter_id_str = f"{enc.encounter_type}@{region_id}"
        overlay_summaries = [
            LocationDescriptionOverlaySummary(
                encounter_id=encounter_id_str,
                prose_suffix=overlay.prose_suffix,
                entity_delta_count=len(overlay.entity_delta),
            )
        ]
    elif transition == "deactivate":
        if prior_overlay is None:
            return
        region_id = prior_overlay.bound_room_id
        overlay_summaries = []
    else:
        raise ValueError(
            f"transition must be 'activate' or 'deactivate', got {transition!r}"
        )

    payload = LocationOverlayChangedPayload(
        region_id=region_id,
        overlays=overlay_summaries,
    )
    msg = LocationOverlayChangedMessage(
        payload=payload,
        player_id=getattr(sd, "player_id", ""),
    )
    _watcher_publish(
        "location_overlay_changed.emitted",
        {
            "genre": getattr(sd, "genre_slug", ""),
            "world": getattr(sd, "world_slug", ""),
            "region_id": region_id,
            "transition": transition,
            "overlay_count": len(overlay_summaries),
        },
        component="location",
    )
    logger.info(
        "location_overlay_changed.emitted region=%s transition=%s overlays=%d",
        region_id,
        transition,
        len(overlay_summaries),
    )
    emit_fn(msg, "LOCATION_OVERLAY_CHANGED")  # type: ignore[operator]
```

Add the `EncounterLocationOverlay` import at the top of the file (it's referenced only in a type annotation; using a string forward-ref means the runtime import inside the function body suffices, but the type-hint string `"EncounterLocationOverlay | None"` needs `from __future__ import annotations` — already present per project style; verify with `grep -n "from __future__" sidequest-server/sidequest/server/websocket_session_handler.py | head -1`).

- [ ] **Step 5: Wire the activate call site**

Find the encounter activation. Run:

```bash
grep -n "prior_live\|now_live\b" sidequest-server/sidequest/server/websocket_session_handler.py
```

Around line 2991–2992 the code reads:

```python
                    now_encounter = snapshot.encounter
                    now_live = now_encounter is not None and not now_encounter.resolved
```

Immediately after that pair (still inside the `with timings.phase("state_apply"):` block), add:

```python
                    # Story 54-7: encounter activation edge — when a new
                    # encounter is live this turn that wasn't live last
                    # turn AND it carries a location_overlay, emit
                    # LOCATION_OVERLAY_CHANGED so the UI overlays the
                    # encounter's contribution on top of the room
                    # description.
                    if now_live and not prior_live and now_encounter is not None:
                        _maybe_emit_location_overlay_changed(
                            self,
                            sd=sd,
                            snapshot=snapshot,
                            transition="activate",
                            emit_fn=emit_fn,
                        )
```

- [ ] **Step 6: Wire the deactivate call site**

The deactivation is captured at line 2782 as `encounter_resolved_this_turn`. The prior encounter is captured at line 2717 as `prior_encounter`. Find the spot right after the apply where both are in scope (still inside the `state_apply` block, before the `monster_manual` block that starts ~2785):

```python
                    encounter_resolved_this_turn = encounter_unresolved_before and (
                        snapshot.encounter is None or snapshot.encounter.resolved
                    )
```

Immediately after this line, add:

```python
                    # Story 54-7: encounter deactivation edge — the
                    # encounter that was live last turn has resolved this
                    # turn. If it carried a location_overlay, fire the
                    # deactivate emit so the UI clears its overlay slice.
                    if (
                        encounter_resolved_this_turn
                        and prior_encounter is not None
                        and prior_encounter.location_overlay is not None
                    ):
                        _maybe_emit_location_overlay_changed(
                            self,
                            sd=sd,
                            snapshot=snapshot,
                            transition="deactivate",
                            emit_fn=emit_fn,
                            prior_overlay=prior_encounter.location_overlay,
                        )
```

- [ ] **Step 7: Confirm green (focused)**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_overlay_emit.py -v
```
Expected: 5 passed.

- [ ] **Step 8: Run the broader handler suite — confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/server/ -v --timeout=60
```
Expected: full green. The encounter-transition block is well-trodden; the new helper is a side-effect call after the existing logic, so existing handler tests should not be affected. If a test fails on import order or the new helper being called unexpectedly, check whether the test fakes `snapshot.encounter` and adapt.

- [ ] **Step 9: Lint + format**

```bash
just server-fmt && just server-lint
```

- [ ] **Step 10: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/server/test_location_overlay_emit.py
git commit -m "feat(54-7): emit LOCATION_OVERLAY_CHANGED on encounter transitions

Hooks into the existing prior_live / now_live / encounter_resolved_this_turn
edges in the narration turn loop. activate path emits with the live
overlay summary; deactivate path emits with an empty overlay list so
the UI clears its slice. Watcher event location_overlay_changed.emitted
surfaces the transition on the GM panel (full dedicated OTEL span
arrives in Story 54-8)."
```

---

### Task 7: Frontend protocol types

**Files:**
- Modify: `sidequest-ui/src/types/protocol.ts`
- Modify: `sidequest-ui/src/types/payloads.ts`

The actual UI consumer ships in 54-9. This task just lands the wire types so the typed message can be matched in `useStateMirror`.

- [ ] **Step 1: Add the MessageType value**

In `sidequest-ui/src/types/protocol.ts`, in the `MessageType` const-object (between `TACTICAL_GRID` and the closing `} as const;`):

```typescript
  // Story 54-7 / ADR-109: delta channel for encounter location overlay
  // state changes. Fires when an encounter with a non-None
  // location_overlay activates or deactivates. UI consumer in 54-9.
  LOCATION_OVERLAY_CHANGED: "LOCATION_OVERLAY_CHANGED",
```

- [ ] **Step 2: Add the payload type**

In `sidequest-ui/src/types/payloads.ts`, near the `LocationDescriptionPayload` interface (added by 54-2):

```typescript
// Story 54-7 / ADR-109: delta-channel payload for encounter location
// overlay state changes. The overlays array carries the FULL
// post-transition overlay set — UI replaces its overlay slice rather
// than reconciling enter/leave events.
export interface LocationOverlayChangedPayload {
  region_id: string;
  overlays: LocationDescriptionOverlaySummary[];
}
```

(The `LocationDescriptionOverlaySummary` type was added by 54-2 in the same file — reuse it.)

- [ ] **Step 3: Type-check + lint the UI**

```bash
just client-lint
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/src/types/protocol.ts sidequest-ui/src/types/payloads.ts
git commit -m "feat(54-7): LOCATION_OVERLAY_CHANGED TS types

Mirrors the pydantic shape from sidequest-server. UI consumer (Location
panel state-mirror integration) lands in Story 54-9."
```

---

### Task 8: Full server + UI suite + smoke

- [ ] **Step 1: Full server suite**

```bash
just server-test
```
Expected: green.

- [ ] **Step 2: Full UI suite**

```bash
just client-test
```
Expected: green.

- [ ] **Step 3: Aggregate gate**

```bash
just check-all
```
Expected: green.

---

### Self-review checklist

- [ ] **Spec §4.1 coverage:** `EncounterLocationOverlay` is wired into a real consumer (StructuredEncounter + read-time merge + emit). The model itself shipped in 54-2. ✓
- [ ] **Spec §4.4 coverage:** action overrides layer at read time, never mutate base authored description or base authored manifest. ✓ (see `get_location_manifest` / `get_location_prose`)
- [ ] **Spec §5.5 coverage:** `get_location_manifest` and `get_location_prose` match the pseudocode in the spec, including the encounter-arrival concatenation and the empty-suffix drop. ✓
- [ ] **Spec §6.2 coverage:** `LOCATION_OVERLAY_CHANGED` direction = server→client, trigger = encounter activate/deactivate touching a `bound_room_id`, payload shape = `{region_id, overlays}`. ✓
- [ ] **Placeholder scan:** no TBDs, every code block complete. The "encounter_id" v1 shape (`encounter_type@region_id`) is an explicit decision documented in `_overlay_encounter_id`, not a TODO.
- [ ] **Type consistency:** `EncounterLocationOverlay.bound_room_id` matches the `region_id` field used throughout 54-2 / 54-6 / this story. `LocationDescriptionOverlaySummary` shape (`encounter_id`, `prose_suffix`, `entity_delta_count`) is reused unchanged from 54-2.
- [ ] **No silent fallback:** activate / deactivate emits skip cleanly when the encounter has no overlay (logged via the `_maybe_emit_location_overlay_changed` early returns); base + overlay get-prose returns base alone when suffix is empty (no orphan separator). The `transition` argument raises ValueError on bad input rather than silently no-op'ing.
- [ ] **No stub:** every code path implemented end to end. The `overlays` list shape is the live multi-overlay seam — v1 emits at most one overlay, but the list is honestly accurate (not a "TBD" comment).
- [ ] **54-6 contract preserved:** `_build_effective_manifest` and `resolve` accept `overlays=` with a default of `()`, so 54-6 callers that didn't pass it see identical behavior. Confirmed by running the 54-6 test file unchanged.
- [ ] **Wiring tests present:** `test_overlay_emit_called_from_encounter_transition_dispatch` proves the helper has 2+ non-test call sites (activate + deactivate).

### Dependencies / handoff

- **Blocked by:** 54-2 (model + LocationDescriptionPayload + emit scaffolding), 54-6 (resolver + `_build_effective_manifest` seam).
- **Unblocks:** 54-8 (replaces the bare watcher_publish events emitted here with proper OTEL spans + GM-panel routing), 54-9 (UI Location panel consumes the populated `payload.overlays` + the delta channel).
- **Out of scope:** dedicated `location.overlay.activate` / `location.overlay.deactivate` OTEL spans (54-8), GM-panel routing of overlay events (54-8), UI rendering of overlay prose + pip indicator (54-9), multi-encounter overlay scenarios (deferred — v1 has at most one live encounter at a time per ADR-033, the list shape is the future-proofing).
