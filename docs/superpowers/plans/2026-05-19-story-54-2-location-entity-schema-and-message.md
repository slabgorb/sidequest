# Story 54-2: Server Schema — LocationEntity Types + LOCATION_DESCRIPTION WebSocket Message

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the foundational types (`LocationEntity`, `LocationEntityBinding`, `EncounterLocationOverlay`), extend cartography region + `<world>/rooms/<id>.yaml` schemas to carry `entities[]`, surface the manifest through `TacticalGridPayload` and the cartography region payload, and emit a new `LOCATION_DESCRIPTION` WebSocket message on `current_room` change and session resume.

**Architecture:** Models live in `sidequest/protocol/models.py` (alongside `TacticalGridPayload`). Cartography region (in `sidequest/genre/models/world.py`) gains a typed `entities` field — the existing untyped `landmarks: list[Any]` stays for backward compatibility (content backfill happens in 54-4/54-5). `room_file_loader.load_room_payload()` parses the new top-level `entities[]` from YAML and stuffs it on `TacticalGridPayload.entities`. A new `LocationDescriptionMessage` is registered in `MessageType` and dispatched from `websocket_session_handler._maybe_emit_location_description()` parallel to the existing `_maybe_emit_tactical_grid()`. Session-resume calls the same emit. This story does NOT mutate save state, does NOT call any resolver (54-6), and does NOT render UI (54-9).

**Tech Stack:** Python 3.14, Pydantic v2 (`model_config = {"extra": "forbid"}`), pytest. Existing FastAPI WebSocket layer.

**Workflow:** tdd.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `sidequest-server/sidequest/protocol/models.py` | modify | Add `LocationEntity`, `LocationEntityBinding`, `EncounterLocationOverlay`, `LocationDescriptionPayload`. Extend `TacticalGridPayload` with `entities: list[LocationEntity]`. |
| `sidequest-server/sidequest/protocol/enums.py` | modify | Add `MessageType.LOCATION_DESCRIPTION = "LOCATION_DESCRIPTION"`. |
| `sidequest-server/sidequest/protocol/messages.py` | modify | Add `LocationDescriptionMessage`. Register in `_MSG_TYPE_TO_CLS` dispatch table. |
| `sidequest-server/sidequest/protocol/__init__.py` | modify | Re-export new classes. |
| `sidequest-server/sidequest/genre/models/world.py` | modify | Add `entities: list[LocationEntity]` to `Region`. |
| `sidequest-server/sidequest/game/room_file_loader.py` | modify | Parse `entities[]` from YAML; populate `TacticalGridPayload.entities`. |
| `sidequest-server/sidequest/server/websocket_session_handler.py` | modify | Add `_maybe_emit_location_description()`; wire to room-change branch and session-resume. |
| `sidequest-server/tests/protocol/test_location_entity_models.py` | create | Pydantic validation tests. |
| `sidequest-server/tests/game/test_room_file_loader_entities.py` | create | Loader-with-manifest tests. |
| `sidequest-server/tests/genre/test_region_entities.py` | create | Cartography parsing tests. |
| `sidequest-server/tests/server/test_location_description_emit.py` | create | WebSocket emit integration test (wiring test per CLAUDE.md). |
| `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/<one-room>.yaml` | modify (fixture-only) | Add a single `entities:` block for the wiring test. Revert before commit OR commit as the first sample. **Recommendation: commit the sample — 54-5 will expand it.** |

---

### Task 1: Add manifest pydantic models

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py`
- Test: `sidequest-server/tests/protocol/test_location_entity_models.py`

- [ ] **Step 1: Write the failing tests**

Create `sidequest-server/tests/protocol/test_location_entity_models.py`:

```python
"""Pydantic validation for LocationEntity types (Story 54-2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidequest.protocol.models import (
    EncounterLocationOverlay,
    LocationEntity,
    LocationEntityBinding,
)


def test_real_object_entity_with_binding_validates():
    entity = LocationEntity(
        id="bar",
        label="the bar",
        tier="real_object",
        binding=LocationEntityBinding(kind="location_feature", ref="glenross_bar"),
        affordances=["lean_on", "order_drink"],
    )
    assert entity.provenance == "authored"
    assert entity.promoted_at_turn is None


def test_flavor_only_entity_without_binding_validates():
    entity = LocationEntity(id="cobwebs", label="cobwebs", tier="flavor_only")
    assert entity.binding is None
    assert entity.affordances == []


def test_real_object_without_binding_is_allowed_at_model_level():
    """Model-level allows it; cross-field invariant is enforced by 54-3 validator."""
    entity = LocationEntity(id="bar", label="the bar", tier="real_object")
    assert entity.binding is None


def test_yes_and_minted_provenance_validates():
    entity = LocationEntity(
        id="player_chair",
        label="the wobbly chair",
        tier="yes_and",
        provenance="yes_and_minted",
        promoted_at_turn=42,
        promoted_canon="A wobbly chair near the hearth.",
    )
    assert entity.provenance == "yes_and_minted"
    assert entity.promoted_at_turn == 42


def test_unknown_tier_rejected():
    with pytest.raises(ValidationError):
        LocationEntity(id="x", label="x", tier="nonsense")  # type: ignore[arg-type]


def test_unknown_binding_kind_rejected():
    with pytest.raises(ValidationError):
        LocationEntityBinding(kind="banana", ref="x")  # type: ignore[arg-type]


def test_unknown_provenance_rejected():
    with pytest.raises(ValidationError):
        LocationEntity(
            id="x", label="x", tier="yes_and", provenance="invented_yesterday"  # type: ignore[arg-type]
        )


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        LocationEntity(id="x", label="x", tier="flavor_only", surprise="!")  # type: ignore[call-arg]


def test_blank_label_rejected():
    with pytest.raises(ValidationError):
        LocationEntity(id="x", label="", tier="flavor_only")


def test_blank_id_rejected():
    with pytest.raises(ValidationError):
        LocationEntity(id="", label="x", tier="flavor_only")


def test_encounter_overlay_defaults():
    overlay = EncounterLocationOverlay(bound_room_id="glenross_pub")
    assert overlay.entity_delta == []
    assert overlay.prose_suffix == ""


def test_encounter_overlay_with_delta():
    overlay = EncounterLocationOverlay(
        bound_room_id="glenross_pub",
        entity_delta=[
            LocationEntity(
                id="overturned_table", label="an overturned table", tier="yes_and"
            )
        ],
        prose_suffix="A chair lies in splinters by the door.",
    )
    assert len(overlay.entity_delta) == 1
    assert "splinters" in overlay.prose_suffix


def test_overlay_extra_field_rejected():
    with pytest.raises(ValidationError):
        EncounterLocationOverlay(bound_room_id="x", whatever="no")  # type: ignore[call-arg]
```

- [ ] **Step 2: Run tests, confirm they fail**

Run:
```bash
cd sidequest-server && uv run pytest tests/protocol/test_location_entity_models.py -v
```
Expected: FAIL — `ImportError: cannot import name 'LocationEntity' from 'sidequest.protocol.models'`.

- [ ] **Step 3: Add the models to `sidequest/protocol/models.py`**

Open `sidequest-server/sidequest/protocol/models.py`. Find an appropriate insertion point — read the file first to spot a clean seam (likely after the existing payload/typed-model definitions and before any region-specific blocks). Add:

```python
# ---------------------------------------------------------------------------
# Location manifest (Story 54-2 / ADR-109)
# ---------------------------------------------------------------------------

# Stable identifier — must be non-empty. Re-uses ``constr`` pattern that
# exists elsewhere in this module for blank-string rejection (see e.g.
# NonBlankString). If a NonBlankString alias is already defined above,
# use it instead of inline ``Field(min_length=1)``.

class LocationEntityBinding(BaseModel):
    """Pointer to the real subsystem object backing a ``real_object`` entity.

    The cross-field invariant (``real_object`` SHOULD have a binding) is
    enforced by the ``pf validate locations`` validator (Story 54-3), not
    by pydantic. Authored content is loaded leniently; the validator
    catches mistakes at author time.
    """

    model_config = {"extra": "forbid"}

    kind: Literal["location_feature", "npc", "item", "clue", "scenario_clue"]
    ref: str = Field(min_length=1)


class LocationEntity(BaseModel):
    """A named, typed entry in a location's manifest.

    See ADR-109 / spec §4.1. The ``tier`` determines mechanical weight;
    ``provenance`` records how the entity entered the manifest.

    Authored YAML never mutates at runtime — promotions and player-initiated
    mints accumulate in the ``location_promotions`` SQLite table (Story
    54-6) and are merged on top at read time.
    """

    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    tier: Literal["real_object", "yes_and", "flavor_only"]
    binding: LocationEntityBinding | None = None
    affordances: list[str] = Field(default_factory=list)
    provenance: Literal[
        "authored",
        "cookbook",
        "yes_and_promoted",
        "yes_and_minted",
    ] = "authored"
    promoted_at_turn: int | None = None
    promoted_canon: str | None = None


class EncounterLocationOverlay(BaseModel):
    """Per-encounter contribution merged at read time. Base manifest and
    base description never mutate from overlays — see ADR-109 §5.5."""

    model_config = {"extra": "forbid"}

    bound_room_id: str = Field(min_length=1)
    entity_delta: list[LocationEntity] = Field(default_factory=list)
    prose_suffix: str = ""
```

Ensure `Literal` and `Field` are imported at the top of the module (they may already be).

- [ ] **Step 4: Run tests, confirm green**

Run:
```bash
cd sidequest-server && uv run pytest tests/protocol/test_location_entity_models.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/protocol/models.py sidequest-server/tests/protocol/test_location_entity_models.py
git commit -m "feat(54-2): add LocationEntity, LocationEntityBinding, EncounterLocationOverlay

Pydantic models for the persistent-location-description manifest.
Cross-field invariants (real_object requires binding, etc.) are
enforced by pf validate locations (54-3), not by the model layer —
authored content loads leniently and validator catches drift at
author time. See ADR-109."
```

---

### Task 2: Extend cartography Region schema

**Files:**
- Modify: `sidequest-server/sidequest/genre/models/world.py`
- Test: `sidequest-server/tests/genre/test_region_entities.py`

- [ ] **Step 1: Write failing tests**

Create `sidequest-server/tests/genre/test_region_entities.py`:

```python
"""Region.entities[] parsing tests (Story 54-2)."""

from __future__ import annotations

from sidequest.genre.models.world import Region
from sidequest.protocol.models import LocationEntity


def test_region_with_no_entities_defaults_empty():
    region = Region(name="Glenross", summary="A village.", description="Quiet.")
    assert region.entities == []


def test_region_parses_typed_entities():
    region = Region(
        name="Glenross",
        summary="A village.",
        description="The pub door is ajar.",
        entities=[
            {
                "id": "pub_door",
                "label": "the pub door",
                "tier": "real_object",
                "binding": {"kind": "location_feature", "ref": "glenross_pub_door"},
            },
            {"id": "cobwebs", "label": "cobwebs", "tier": "flavor_only"},
        ],
    )
    assert len(region.entities) == 2
    assert isinstance(region.entities[0], LocationEntity)
    assert region.entities[0].tier == "real_object"
    assert region.entities[1].tier == "flavor_only"


def test_landmarks_field_still_accepted_for_backcompat():
    """Pre-54 worlds still load — landmarks coexists with entities."""
    region = Region(
        name="x",
        summary="x",
        description="x",
        landmarks=["the well", "the church"],
        entities=[{"id": "well", "label": "the well", "tier": "flavor_only"}],
    )
    assert region.landmarks == ["the well", "the church"]
    assert len(region.entities) == 1
```

- [ ] **Step 2: Run, confirm fail**

```bash
cd sidequest-server && uv run pytest tests/genre/test_region_entities.py -v
```
Expected: FAIL — `Region` has no `entities` attribute.

- [ ] **Step 3: Add `entities` to `Region`**

In `sidequest-server/sidequest/genre/models/world.py`, modify the `Region` class (around line 197). Add after the existing `landmarks` field:

```python
    # Story 54-2 / ADR-109: typed entity manifest. Coexists with the legacy
    # untyped ``landmarks`` for backward compat — content backfill in 54-4
    # and 54-5 ports authored worlds to the typed shape. New code reads
    # ``entities``; ``landmarks`` is read-only legacy and slated for
    # removal once all packs are backfilled.
    entities: list[LocationEntity] = Field(default_factory=list)
```

Add the import at the top of the file:
```python
from sidequest.protocol.models import LocationEntity
```

(If a circular import surfaces, move the import into a `TYPE_CHECKING` block and use a forward reference. Check the existing import discipline in this file before deciding.)

- [ ] **Step 4: Run, confirm green**

```bash
cd sidequest-server && uv run pytest tests/genre/test_region_entities.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Make sure the existing cartography loader didn't regress**

```bash
cd sidequest-server && uv run pytest tests/genre/ -v
```
Expected: full genre suite green.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/genre/models/world.py sidequest-server/tests/genre/test_region_entities.py
git commit -m "feat(54-2): Region.entities[] for typed location manifest

Extends cartography Region with a typed LocationEntity list,
coexisting with the legacy landmarks[] field. Existing worlds load
unchanged; content backfill lands in 54-4/54-5."
```

---

### Task 3: Parse `entities[]` in `room_file_loader`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py` (extend `TacticalGridPayload`)
- Modify: `sidequest-server/sidequest/game/room_file_loader.py`
- Test: `sidequest-server/tests/game/test_room_file_loader_entities.py`
- Fixture (commit): add one `entities:` block to a real room YAML for the wiring test (see Task 1's File Map note)

- [ ] **Step 1: Identify the room YAML for the fixture**

Run:
```bash
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/ | head -10
```
Pick one with a real authored `description` (likely `mouth.yaml` or `sunden_square.yaml`). The pick goes into the fixture in step 5.

- [ ] **Step 2: Write failing tests**

Create `sidequest-server/tests/game/test_room_file_loader_entities.py`:

```python
"""Room file loader surfaces ``entities[]`` on TacticalGridPayload (Story 54-2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sidequest.game.room_file_loader import load_room_payload
from sidequest.protocol.models import LocationEntity


@pytest.fixture
def caverns_sunden_dir() -> Path:
    here = Path(__file__).resolve()
    repo = here.parents[3]
    return (
        repo
        / "sidequest-content"
        / "genre_packs"
        / "caverns_and_claudes"
        / "worlds"
        / "caverns_sunden"
    )


def test_room_without_entities_defaults_empty(caverns_sunden_dir):
    """All rooms that have no ``entities:`` block produce an empty list."""
    payload = load_room_payload(caverns_sunden_dir, "mouth")
    assert payload.entities == []


def test_room_with_entities_block_parses_typed(caverns_sunden_dir):
    """The fixture room (``sunden_square``) carries a real manifest after this story."""
    payload = load_room_payload(caverns_sunden_dir, "sunden_square")
    # sunden_square is the fixture seeded in Step 5 with at least one entity.
    assert len(payload.entities) >= 1
    assert all(isinstance(e, LocationEntity) for e in payload.entities)
```

(If `sunden_square` doesn't exist, swap the room id in both the fixture and the test.)

- [ ] **Step 3: Run, confirm fail**

```bash
cd sidequest-server && uv run pytest tests/game/test_room_file_loader_entities.py -v
```
Expected: FAIL — `TacticalGridPayload` has no `entities` attribute (or the fixture room has none).

- [ ] **Step 4: Extend `TacticalGridPayload`**

In `sidequest-server/sidequest/protocol/models.py`, find `TacticalGridPayload` (the file already imports `LocationEntity` you just added). Add:

```python
    # Story 54-2 / ADR-109: typed location manifest. Loaded from the
    # top-level ``entities`` field of the room YAML. Empty when the room
    # has no manifest yet — graceful absence per the no-silent-fallback
    # principle: empty means "no manifest authored", not "lookup failed".
    entities: list[LocationEntity] = Field(default_factory=list)
```

- [ ] **Step 5: Seed the fixture (sunden_square or your chosen room)**

Open `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/sunden_square.yaml`. Add at the top level (alongside `description:`):

```yaml
entities:
  - id: square_well
    label: the well at the centre
    tier: real_object
    binding:
      kind: location_feature
      ref: sunden_square_well
    affordances:
      - draw_water
      - peer_into
  - id: cobwebbed_lantern
    label: a cobwebbed lantern
    tier: flavor_only
```

If the chosen room's existing `description` doesn't already mention these, *do not* invent prose — pick entities whose labels appear (case-insensitive) in the existing description, or stop and ask the spec author. 54-5 is the proper backfill story; this fixture is the minimum to exercise the wiring.

- [ ] **Step 6: Update the loader to read `entities[]`**

In `sidequest-server/sidequest/game/room_file_loader.py`, modify `load_room_payload`. Both the `settlement` and `cavern` branches need:

```python
    entities_raw = data.get("entities", []) or []
    entities = [LocationEntity.model_validate(e) for e in entities_raw]
```

…and pass `entities=entities` when constructing `TacticalGridPayload`. Add the import at the top:
```python
from sidequest.protocol.models import (
    CellularParams,
    DerivedRoomData,
    LocationEntity,
    TacticalGridPayload,
)
```

- [ ] **Step 7: Run, confirm green**

```bash
cd sidequest-server && uv run pytest tests/game/test_room_file_loader_entities.py tests/game/test_room_file_loader.py -v
```
Expected: all green. The pre-existing `test_room_file_loader.py` tests must still pass — they read the same YAMLs.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/models.py \
        sidequest-server/sidequest/game/room_file_loader.py \
        sidequest-server/tests/game/test_room_file_loader_entities.py \
        sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/sunden_square.yaml
git commit -m "feat(54-2): room_file_loader parses entities[] into TacticalGridPayload

TacticalGridPayload gains a typed entities field; loader populates it
from the room YAML's top-level entities block. Seeds sunden_square
with two entities (one real_object, one flavor_only) for the wiring
test — content backfill proper lands in 54-5."
```

---

### Task 4: Add `MessageType.LOCATION_DESCRIPTION` + `LocationDescriptionMessage`

**Files:**
- Modify: `sidequest-server/sidequest/protocol/enums.py`
- Modify: `sidequest-server/sidequest/protocol/models.py` (add `LocationDescriptionPayload`)
- Modify: `sidequest-server/sidequest/protocol/messages.py` (add `LocationDescriptionMessage`, register in dispatch)
- Modify: `sidequest-server/sidequest/protocol/__init__.py` (re-export)
- Test: extend `sidequest-server/tests/protocol/test_location_entity_models.py`

- [ ] **Step 1: Write failing tests**

Append to `sidequest-server/tests/protocol/test_location_entity_models.py`:

```python
from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import LocationDescriptionMessage
from sidequest.protocol.models import LocationDescriptionPayload


def test_location_description_payload_minimum():
    payload = LocationDescriptionPayload(
        region_id="glenross_pub",
        prose="The pub door is ajar.",
        terrain="building",
        entities=[],
        overlays=[],
    )
    assert payload.region_id == "glenross_pub"


def test_location_description_message_roundtrip():
    msg = LocationDescriptionMessage(
        payload=LocationDescriptionPayload(
            region_id="glenross_pub",
            prose="The pub door is ajar.",
            terrain="building",
            entities=[],
            overlays=[],
        ),
        player_id="",
    )
    assert msg.type == MessageType.LOCATION_DESCRIPTION
    dumped = msg.model_dump()
    assert dumped["type"] == "LOCATION_DESCRIPTION"
    assert dumped["payload"]["region_id"] == "glenross_pub"
```

- [ ] **Step 2: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/protocol/test_location_entity_models.py::test_location_description_payload_minimum -v
```
Expected: FAIL — import errors.

- [ ] **Step 3: Add the enum**

In `sidequest-server/sidequest/protocol/enums.py`, alongside the other `MessageType` values (after `TACTICAL_GRID`):

```python
    # Story 54-2 / ADR-109: persistent location description + manifest
    # snapshot. Emitted on current_room change and session resume.
    # The OVERLAY_CHANGED delta variant lands in Story 54-7.
    LOCATION_DESCRIPTION = "LOCATION_DESCRIPTION"
```

- [ ] **Step 4: Add `LocationDescriptionPayload` to `models.py`**

Add (near the manifest models you added in Task 1):

```python
class LocationDescriptionOverlaySummary(BaseModel):
    """UI-facing summary of an active encounter overlay (Story 54-7 fills
    this with real data; 54-2 emits an empty list)."""

    model_config = {"extra": "forbid"}

    encounter_id: str
    prose_suffix: str = ""
    entity_delta_count: int = 0


class LocationDescriptionPayload(BaseModel):
    """Snapshot of one location's description + manifest for the UI.

    Emitted by ``LOCATION_DESCRIPTION``. Overlay delta channel is
    ``LOCATION_OVERLAY_CHANGED`` (Story 54-7).
    """

    model_config = {"extra": "forbid"}

    region_id: str = Field(min_length=1)
    prose: str
    terrain: str | None = None
    entities: list[LocationEntity] = Field(default_factory=list)
    overlays: list[LocationDescriptionOverlaySummary] = Field(default_factory=list)
```

- [ ] **Step 5: Add `LocationDescriptionMessage` to `messages.py`**

Find the `TacticalGridMessage` definition and mirror it. Add:

```python
class LocationDescriptionMessage(ProtocolBase):
    """GameMessage::LocationDescription — persistent location snapshot.

    Story 54-2 / ADR-109. Emitted on current_room change (so the UI
    Location tab updates as the party moves) and on session resume
    (so a returning client gets the manifest without polling). The
    delta channel for encounter overlays is LOCATION_OVERLAY_CHANGED
    (Story 54-7).
    """

    type: Literal[MessageType.LOCATION_DESCRIPTION] = MessageType.LOCATION_DESCRIPTION
    payload: LocationDescriptionPayload
    player_id: str = ""
```

Then register in the dispatch table (search `_MSG_TYPE_TO_CLS` or `"TACTICAL_GRID": TacticalGridMessage`, around `session_handler.py:151`):

```python
    "LOCATION_DESCRIPTION": LocationDescriptionMessage,
```

(The exact registry location varies; use `grep -n '"TACTICAL_GRID": TacticalGridMessage' sidequest-server/sidequest -r` to find every dispatch site and update all of them.)

- [ ] **Step 6: Re-export**

In `sidequest-server/sidequest/protocol/__init__.py`, add re-exports for `LocationEntity`, `LocationEntityBinding`, `EncounterLocationOverlay`, `LocationDescriptionPayload`, `LocationDescriptionMessage`, `LocationDescriptionOverlaySummary` so callers can `from sidequest.protocol import LocationDescriptionMessage`. Match the existing re-export style.

- [ ] **Step 7: Confirm green**

```bash
cd sidequest-server && uv run pytest tests/protocol/ -v
```
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/
git commit -m "feat(54-2): LOCATION_DESCRIPTION message + payload

Wires MessageType.LOCATION_DESCRIPTION, LocationDescriptionPayload
(region_id, prose, terrain, entities, overlays), and
LocationDescriptionMessage into the protocol layer. Overlays list is
populated by Story 54-7; this story ships empty overlay arrays on
every emit."
```

---

### Task 5: Emit `LOCATION_DESCRIPTION` on room change and session resume

**Files:**
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py`
- Test: `sidequest-server/tests/server/test_location_description_emit.py`

This is the **wiring test** required by CLAUDE.md — every test suite needs at least one integration test proving the component is reached from production code paths.

- [ ] **Step 1: Read the existing tactical-grid emit + its call sites**

Already explored above: `_maybe_emit_tactical_grid()` at `websocket_session_handler.py:454`, called at lines 2050, 3980; `_maybe_emit_dungeon_map()` parallel at line 605, called at line 3994. Skim those handlers — they show the exact shape (genre/world dir lookup, error envelope, watcher publish, emit_fn dispatch). Read at least lines 454-605 and the call sites at 2050, 3980, 3994.

- [ ] **Step 2: Find the session-resume site**

Run:
```bash
grep -n "session.*resume\|on_resume\|resume_session" sidequest-server/sidequest/server/websocket_session_handler.py | head -10
```
Note the line(s) where a resumed session is detected and initial state is sent to the client. This is the second emit site.

- [ ] **Step 3: Write the failing integration test**

Create `sidequest-server/tests/server/test_location_description_emit.py`:

```python
"""Wiring test: LOCATION_DESCRIPTION fires on room change + session resume.

Story 54-2 / ADR-109. This is the integration test required by
CLAUDE.md "Every test suite needs a wiring test" — proves the handler
calls _maybe_emit_location_description from real dispatch code paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sidequest.protocol.enums import MessageType
from sidequest.protocol.messages import LocationDescriptionMessage
from sidequest.server.websocket_session_handler import (
    _maybe_emit_location_description,
)


def test_emit_skips_when_no_room_id():
    """No room → no message. Graceful absence per CLAUDE.md."""
    emit_fn = MagicMock()
    sd = MagicMock()
    sd.genre_slug = "caverns_and_claudes"
    sd.world_slug = "caverns_sunden"
    snapshot = MagicMock()
    snapshot.character_locations = {}
    _maybe_emit_location_description(
        handler=MagicMock(),
        sd=sd,
        snapshot=snapshot,
        actor="alice",
        emit_fn=emit_fn,
    )
    emit_fn.assert_not_called()


def test_emit_sends_message_when_room_has_manifest(monkeypatch):
    """Production path: room with entities → LocationDescriptionMessage emitted."""
    from sidequest.game.room_file_loader import load_room_payload
    from pathlib import Path

    # Use the real fixture seeded in Task 3.
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
    real_payload = load_room_payload(world_dir, "sunden_square")
    assert real_payload.entities, "fixture room must have entities for this test"

    emit_fn = MagicMock()
    sd = MagicMock()
    sd.genre_slug = "caverns_and_claudes"
    sd.world_slug = "caverns_sunden"
    sd.player_id = ""
    sd.genre_pack = MagicMock()
    sd.genre_pack.worlds = {"caverns_sunden": MagicMock()}
    snapshot = MagicMock()
    snapshot.character_locations = {"alice": "sunden_square"}

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
    assert sent_msg.type == MessageType.LOCATION_DESCRIPTION
    assert sent_msg.payload.region_id == "sunden_square"
    assert len(sent_msg.payload.entities) >= 1
    # Overlays empty until Story 54-7.
    assert sent_msg.payload.overlays == []


def test_emit_called_from_room_change_dispatch():
    """Statically prove _maybe_emit_location_description has a non-test caller.

    CLAUDE.md "Verify wiring, not just existence" — the function must be
    invoked from production code, not just live in the module.
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
    # Definition + at least one call site (room-change path).
    assert "def _maybe_emit_location_description(" in handler_src
    call_count = handler_src.count("_maybe_emit_location_description(")
    # def + at least 1 call site (room change). 2 minimum.
    assert call_count >= 2, (
        f"expected definition + at least one call site, found {call_count} mentions"
    )
```

- [ ] **Step 4: Confirm fail**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_description_emit.py -v
```
Expected: FAIL — `_maybe_emit_location_description` does not exist.

- [ ] **Step 5: Add `_maybe_emit_location_description`**

In `sidequest-server/sidequest/server/websocket_session_handler.py`, add — right after `_maybe_emit_tactical_grid`:

```python
def _maybe_emit_location_description(
    handler: object,
    *,
    sd: _SessionData,
    snapshot: GameSnapshot,
    actor: str | None,
    emit_fn: object,
    room_id_override: str | None = None,
) -> None:
    """Emit a LOCATION_DESCRIPTION message when the party's current_room changes.

    Story 54-2 / ADR-109. Mirrors the _maybe_emit_tactical_grid wiring.
    Called from:
    1. Narrator location-change branch (same call site as tactical grid).
    2. Chargen room-graph init (room_id_override).
    3. Session-resume dispatch (room_id_override = current saved room).

    Graceful absence:
    - no room id → silent return (CLAUDE.md no-silent-fallback: absence
      is observable via the lack of an emit watcher event, not a noisy
      log).
    - room YAML missing or has no entities → emit a payload with empty
      ``entities`` and the room's authored description if available.
      The UI Location tab handles empty manifests gracefully.

    Overlays list is empty until Story 54-7 wires
    LOCATION_OVERLAY_CHANGED.
    """
    from sidequest.game.room_file_loader import RoomNotFoundError, load_room_payload
    from sidequest.genre.loader import DEFAULT_GENRE_PACK_SEARCH_PATHS, GenreLoader
    from sidequest.protocol.messages import LocationDescriptionMessage
    from sidequest.protocol.models import LocationDescriptionPayload

    world = sd.genre_pack.worlds.get(sd.world_slug)
    if world is None:
        return

    room_id = (
        room_id_override
        if room_id_override is not None
        else (snapshot.character_locations.get(actor or "") if actor else None)
    )
    if not room_id:
        return

    # Resolve description + entities. Two paths:
    # 1. Procedural / per-room YAML — load_room_payload.
    # 2. POI cartography — read from world.cartography.regions[room_id].
    prose: str = ""
    terrain: str | None = None
    entities: list = []

    try:
        loader = GenreLoader(search_paths=DEFAULT_GENRE_PACK_SEARCH_PATHS)
        world_dir = loader.find(sd.genre_slug) / "worlds" / sd.world_slug
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "location_description.world_dir_lookup_failed genre=%s world=%s error=%s",
            sd.genre_slug,
            sd.world_slug,
            exc,
        )
        return

    try:
        room_payload = load_room_payload(world_dir, room_id, genre_slug=sd.genre_slug)
        prose = room_payload.settlement_description or ""
        terrain = room_payload.room_type
        entities = list(room_payload.entities)
    except RoomNotFoundError:
        # Fall back to cartography region lookup (POI worlds).
        cartography = getattr(world, "cartography", None)
        region = cartography.regions.get(room_id) if cartography else None
        if region is not None:
            prose = region.description or ""
            terrain = getattr(region, "terrain", None)
            entities = list(getattr(region, "entities", []))
        else:
            # Neither room YAML nor cartography region — no manifest.
            # Watcher event so absence is visible.
            _watcher_publish(
                "location_description.no_source",
                {
                    "genre": sd.genre_slug,
                    "world": sd.world_slug,
                    "room_id": room_id,
                },
                component="location",
            )
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "location_description.load_failed genre=%s world=%s room=%s error=%s",
            sd.genre_slug,
            sd.world_slug,
            room_id,
            exc,
        )
        _watcher_publish(
            "location_description.load_failed",
            {
                "genre": sd.genre_slug,
                "world": sd.world_slug,
                "room_id": room_id,
                "error": str(exc),
            },
            component="location",
            severity="warning",
        )
        return

    payload = LocationDescriptionPayload(
        region_id=room_id,
        prose=prose,
        terrain=terrain,
        entities=entities,
        overlays=[],  # Story 54-7 populates this.
    )
    msg = LocationDescriptionMessage(
        payload=payload,
        player_id=getattr(sd, "player_id", ""),
    )
    _watcher_publish(
        "location_description.emitted",
        {
            "genre": sd.genre_slug,
            "world": sd.world_slug,
            "room_id": room_id,
            "entity_count": len(entities),
            "prose_chars": len(prose),
        },
        component="location",
    )
    logger.info(
        "location_description.emitted genre=%s world=%s room=%s entities=%d",
        sd.genre_slug,
        sd.world_slug,
        room_id,
        len(entities),
    )
    emit_fn(msg, "LOCATION_DESCRIPTION")  # type: ignore[operator]
```

- [ ] **Step 6: Add the call sites**

At every site where `_maybe_emit_tactical_grid(` is called (`grep -n` previously showed lines 2050 and 3980, plus the dungeon-map site at 3994), add a matching `_maybe_emit_location_description(...)` call **immediately after** with identical args.

At the session-resume site (Step 2's grep), add a call passing `room_id_override=<saved current room>`.

Pattern:
```python
                _maybe_emit_tactical_grid(
                    handler,
                    sd=sd,
                    snapshot=snapshot,
                    actor=actor,
                    emit_fn=emit_fn,
                )
                _maybe_emit_location_description(
                    handler,
                    sd=sd,
                    snapshot=snapshot,
                    actor=actor,
                    emit_fn=emit_fn,
                )
```

- [ ] **Step 7: Run, confirm green**

```bash
cd sidequest-server && uv run pytest tests/server/test_location_description_emit.py -v
```
Expected: 3 passed.

- [ ] **Step 8: Run the broader server suite to confirm no regression**

```bash
cd sidequest-server && uv run pytest tests/ -v --timeout=60
```
Expected: full green. If anything related to room-change dispatch fails, the new call probably needs to match the precise call-site signature variant — check the failing test and pull the right args.

- [ ] **Step 9: Lint + format**

```bash
just server-fmt && just server-lint
```
Expected: clean. Fix any ruff complaints (likely import sorting or unused imports).

- [ ] **Step 10: Commit**

```bash
git add sidequest-server/sidequest/server/websocket_session_handler.py \
        sidequest-server/tests/server/test_location_description_emit.py
git commit -m "feat(54-2): emit LOCATION_DESCRIPTION on room change + session resume

_maybe_emit_location_description mirrors the tactical-grid wiring:
called from the narrator location-change branch, chargen room-graph
init, and session-resume dispatch. Watcher event location_description.
emitted fires on every successful emit; no_source/load_failed surface
the absent-manifest case. Overlays array is empty until Story 54-7."
```

---

### Task 6: UI payload type (TypeScript)

**Files:**
- Modify: `sidequest-ui/src/types/payloads.ts`

The UI render lands in Story 54-9 — but the *payload type* is part of 54-2 per the spec (line: "new `LOCATION_DESCRIPTION` WebSocket message + server-side emit on `current_room` change and session resume"). Just the type, no component changes here.

- [ ] **Step 1: Locate the existing payload types**

Run:
```bash
grep -n "TacticalGridPayload\|interface.*Payload" sidequest-ui/src/types/payloads.ts | head -10
```

- [ ] **Step 2: Add the type**

In `sidequest-ui/src/types/payloads.ts`, mirror the pydantic shape:

```typescript
// Story 54-2 / ADR-109: persistent location description + manifest.
// The Location tab consumer lands in Story 54-9.
export type LocationEntityTier = "real_object" | "yes_and" | "flavor_only";

export type LocationEntityBindingKind =
  | "location_feature"
  | "npc"
  | "item"
  | "clue"
  | "scenario_clue";

export interface LocationEntityBinding {
  kind: LocationEntityBindingKind;
  ref: string;
}

export interface LocationEntity {
  id: string;
  label: string;
  tier: LocationEntityTier;
  binding: LocationEntityBinding | null;
  affordances: string[];
  provenance:
    | "authored"
    | "cookbook"
    | "yes_and_promoted"
    | "yes_and_minted";
  promoted_at_turn: number | null;
  promoted_canon: string | null;
}

export interface LocationDescriptionOverlaySummary {
  encounter_id: string;
  prose_suffix: string;
  entity_delta_count: number;
}

export interface LocationDescriptionPayload {
  region_id: string;
  prose: string;
  terrain: string | null;
  entities: LocationEntity[];
  overlays: LocationDescriptionOverlaySummary[];
}
```

- [ ] **Step 3: Type-check + lint the UI**

```bash
just client-lint
cd sidequest-ui && npx tsc --noEmit
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add sidequest-ui/src/types/payloads.ts
git commit -m "feat(54-2): LocationDescriptionPayload TS types

Mirrors the pydantic shape; the UI consumer (LocationPanel) lands in
Story 54-9. State-mirror integration also waits on 54-9."
```

---

### Self-review checklist

- [ ] **Spec coverage:** §4.1 manifest types ✓; §5.2 loader wiring (cartography region + room_file_loader) ✓; §6.2 LOCATION_DESCRIPTION emit on `current_room` change and session resume ✓; UI WebSocket payload types added ✓. LOCATION_OVERLAY_CHANGED, resolver, promotions table, OTEL spans, UI component, validator — all explicitly **out of scope** for this story, owned by 54-3/54-6/54-7/54-8/54-9.
- [ ] **Placeholder scan:** no TBDs, every code block complete.
- [ ] **Type consistency:** `LocationEntity` shape matches across pydantic, the TS interface, and the YAML fixture. `LocationDescriptionPayload.region_id` field name matches at every layer.
- [ ] **Wiring test present:** `test_emit_called_from_room_change_dispatch` proves the function has a non-test caller in production code, per CLAUDE.md.
- [ ] **No silent fallback:** missing manifest emits a `location_description.no_source` watcher event rather than swallowing.
- [ ] **No stub:** every code path implemented end to end. `overlays=[]` is **not** a stub — it's the explicit v1 contract, owned by Story 54-7.

### Dependencies / handoff

- **Unblocks:** 54-3 (validator needs the types), 54-6 (resolver), 54-7 (overlays), 54-9 (UI), 55-1 (procedural emit).
- **Blocked by:** 54-1 (ADR — should land first as the durable contract).
