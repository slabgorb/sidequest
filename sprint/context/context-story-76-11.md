# Story 76-11 Context

## Title
Location source coverage v2 — wire room-graph + world_materialization adapters into the entity index (via location_view authored-prose resolution), batch the per-region promotion read, and surface per-region read failures as a watcher event (carries forward 76-7 Reviewer/Dev Delivery Findings)

## Metadata
- **Story ID:** 76-11
- **Type:** story
- **Points:** 5
- **Priority:** p3
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** Universal Retrieval Follow-Ups — 75-6 Hardening + Source Coverage

## Problem

Story 76-7 wired only 1 of 3 named location sources into the entity index (PG `location_promotions`). Two additional sources remain unwired:
1. Room-graph rooms (`RoomState` carries `room_id`+`containers` but **no prose**).
2. World_materialization outputs (emits **no description-bearing location entity** today).

Location projection requires real authored prose via `location_view.get_location_prose(region_id, authored_description, snapshot)` merged with `get_location_manifest(...)` — no Silent Fallbacks / No Stubbing discipline forbids synthesizing descriptions. Additionally, the per-region promotion read in `_collect_location_views` scales linearly with `len(snapshot.discovered_regions)` (one DB round-trip per region, every turn), and read failures emit no watcher event (GM-panel blind spot).

## Technical Approach

**Three concrete threads in ONE file: `sidequest/server/dispatch/entity_sync.py` + `sidequest/game/entity_card.py`**

### Thread 1: Source coverage v2 (the core, ~3pt)
Wire room-graph and world_materialization as adapters in `_collect_location_views`:

1. **Room-graph rooms:** `RoomState` carries `room_id`+`containers` but no prose. Collect `snapshot.interior.rooms[room_id]` and resolve description via `location_view.get_location_prose(region_id, <authored_description>, snapshot)` + `get_location_manifest(...)`. Pass normalized `LocationSyncView` (source-tagged `"room"`) to `sync_entity_cards`.

2. **World_materialization locations:** The materialization output (emits creatures/items/NPCs) has no native location entity. Extract region context, resolve authored prose via `location_view.get_location_prose(region_id, <authored_description>, snapshot)`, materialize a `LocationSyncView` (source-tagged `"materialization"`). Pass to `sync_entity_cards`.

3. **Normalize via the existing source-agnostic path:** `LocationSyncView` dataclass + `sync_entity_cards(..., locations=)` kwarg + `project_location_card` projector already handle multiple sources (per ADR-118 §D3 — "per-source adaptation belongs to the consumer"). Dev picks the source priority/merge order; the wiring remains clean.

**Constraint:** The projector `sidequest/game/entity_card.py::project_location_card` has a blank-description guard. These adapters must feed **real prose** via `location_view`, never synthesize/stub a description. If a source cannot provide prose, skip it (fail-loud, zero cards for that source) — do NOT mint degenerate stub cards.

### Thread 2: Batch the per-region promotion read (Reviewer perf finding)
Currently: `_collect_location_views` runs one `list_location_promotions` DB round-trip **per discovered region, every turn** — O(N) cost per turn. Refactor to a single batched read:
- Read all promotions once: `list_location_promotions(discovered_regions_list)` (if available) OR manually batch.
- Per-region projection loops over the batched result.
- Pin with an assertion: `called_once_on_batched_input` (query-count or call-count spy).

### Thread 3: Surface per-region read failures as a watcher event
Per-region read failure (e.g., a stale foreign key in the promotions table) is currently `logger.exception`-logged and `continue`d, but emits **no watcher event** and does not increment `result.failed` — silent `location_count` under-report, GM panel blind.

Add a watcher event when a per-region read fails:
- Increment `result.failed`.
- Publish a watcher event: `_watcher_publish(op="sync_failed", entity_type="location", detail=f"region {region_id}: {error}")` (or similar).
- The GM panel (lie detector) then sees a signal that region data was unavailable.

## Scope
- **In scope:** 
  - Room-graph and world_materialization location adapters in `_collect_location_views` (source-agnostic, via `location_view`).
  - Batch the per-region promotion read (perf).
  - Per-region read failures surface as watcher events + `result.failed` increment (observability).
  - All 3 sources reach production via `sync_for_turn(handler, sd)`.
- **Out of scope:** 
  - Unrelated engine changes.
  - Changes to `location_view.get_location_prose` itself (use existing contract).

## Acceptance Criteria

**Derived from the title + Reviewer/Dev Delivery Findings (76-7 session):**

**AC1: room-graph room locations flow end-to-end to non-zero location_count**
- Behavioral test (mirroring 76-7's `TestPromotionLocationFlowsEndToEnd`):
  - Seed a snapshot with a real room in interior state.
  - Call `sync_for_turn(handler, sd)`.
  - Assert `entity_sync_result.location_count >= 1` AND at least one card has `source="room"`.
  - No test content synthesis; use fixture world.

**AC2: world_materialization location outputs flow end-to-end to location_count**
- Behavioral test (same shape as AC1):
  - Seed a materialization that emits a location context (region, scene, etc.).
  - Call `sync_for_turn(handler, sd)`.
  - Assert `location_count >= 1` AND at least one card has `source="materialization"`.

**AC3: Per-region promotion read is batched**
- Performance assertion:
  - Discover N regions.
  - Verify `list_location_promotions` is called **once** with a batched input (not N separate calls).
  - Spy/mock assertion: `list_location_promotions.call_count == 1`.

**AC4: Per-region read failures increment result.failed AND publish a watcher event**
- Observability test:
  - Mock `list_location_promotions` to raise an exception for region X.
  - Call `sync_for_turn(...)`.
  - Assert `result.failed >= 1`.
  - Assert watcher event published with detail (e.g., `op="sync_failed"` + region id + error).

**AC5: Each new source has a non-test consumer (wiring test)**
- Reachability assertion:
  - From `sync_for_turn(handler, sd)` (production dispatch seam), trace to both room-graph and materialization adapters in `_collect_location_views`.
  - No half-wired adapters; if an adapter exists but is never called from production, the story is incomplete.

## Key Project Constraints

**No Silent Fallbacks / No Stubbing:**
- Adapters must feed **real** `location_view` prose, never synthesized descriptions.
- The projector's blank-description guard stays; if a source cannot provide prose, skip it.

**Tests must use FIXTURE packs, not live sidequest-content:**
- `tests/server/` autouse fixture `_fixture_pack_search_paths` repoints the loader at `tests/fixtures/packs`.
- Use fixture world `caverns_and_claudes/flickering_reach` (the 76-7 precedent; has authored fixture factions/locations).
- Tests pointing at live content slugs fail when CI runs them (content is not available in `tests/server/`).

**Every test suite needs a wiring test:**
- Unit tests (pure projector/adapter) are necessary but not sufficient.
- **Mandatory:** At least one integration test reachable from `sync_for_turn(handler, sd)` (the production dispatch seam).
- This proves the adapter is integrated, not just unit-tested in isolation.

**OTEL Observability Principle (CLAUDE.md):**
- Thread 3 (watcher events on read failures) is **mandatory GM-panel observability**, not optional.
- The GM panel is the lie detector — if a subsystem isn't emitting watcher events, you can't tell whether it's working or whether Claude is improvising.

## Reference Files
- **Core dispatch file:** `sidequest/server/dispatch/entity_sync.py` (`_collect_location_views`, `sync_for_turn`, `sync_entity_cards`, `_apply_typed_card`, `_watcher_publish`).
- **Projector + normalized view:** `sidequest/game/entity_card.py` (`project_location_card`, `LocationSyncView`).
- **Prose resolution:** `location_view` module (`get_location_prose`, `get_location_manifest`).
- **Precedent tests:** `tests/server/dispatch/test_entity_sync_sources_wiring.py` (existing faction + promotion e2e tests to mirror).
- **Precedent session:** `sprint/archive/76-7-session.md` (lines 66–142: Delivery Findings; lines 111–132: Dev deviations for the location projector design).

---
_Generated by `pf context create story 76-11` from the sprint YAML._
