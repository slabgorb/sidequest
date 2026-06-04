# Story 76-7 Context

## Title
Source coverage: sync factions + locations into the entity index — wire faction (world lore) and location (diffuse: room graph / world_materialization / PG promotions) sources through project_faction_card/project_location_card so entity_sync.{faction,location}_count stop reading 0. Makes the universal index actually universal.

## Metadata
- **Story ID:** 76-7
- **Type:** feature
- **Points:** 5
- **Priority:** p3
- **Workflow:** tdd
- **Repo:** sidequest-server
- **Epic:** Universal Retrieval Follow-Ups — 75-6 Hardening + Source Coverage

## Problem
The entity index (ADR-118: Universal Retrieval Layer) extends sources across the game state. Story 76-6 completed sync of stateful `snapshot.npcs`. However, two critical entity sources remain unwired:

1. **Factions** (world lore): world-defined factions are loaded but not indexed for retrieval via `_retrieve_entities_for_turn()`.
2. **Locations** (diffuse sources): locations originate from multiple sources — room graph, world_materialization module, and PostgreSQL promotions. None are currently synced into the entity index.

This makes the "universal" retrieval index incomplete. The NPC-only v1 (ADR-118 permitted) now requires faction and location coverage to deliver full semantic retrieval value to the narrator and GM panel.

## Technical Approach
The pattern is established by story 76-6 (snapshot.npcs sync) and mirrored from story 76-3 (lore embedding). Two projector paths are needed:

1. **Faction Source Sync:**
   - Extend or create `project_faction_card()` to extract faction data from world lore (faction ID, name, description, goals/beliefs).
   - Update `sync_entity_cards()` to iterate over the session's loaded world factions and project each via `project_faction_card()`.
   - Ensure faction cards are tagged with `entity_type: 'faction'` for classification.

2. **Location Source Sync:**
   - Extend or create `project_location_card()` to extract location data from diffuse sources:
     - Room-graph rooms (interior/orrery navigation state)
     - World_materialization outputs (materializer-generated location entities)
     - PG location promotions (persisted location entities from session store)
   - Update `sync_entity_cards()` to iterate over all three location sources and project each via `project_location_card()`.
   - Ensure location cards are tagged with `entity_type: 'location'` for classification.

3. **Wiring and Coverage:**
   - Verify that `sync_entity_cards()` is called at the canonical turn-context build point (entry gate to narrator, per ADR-118 §D2).
   - Confirm `entity_sync.{faction,location}_count` OTEL spans emit non-zero when sources are present (verify end-to-end wiring).
   - Include a wiring test demonstrating production reachability (acceptance criterion 5).

## Scope
- **In scope:** faction projector path, location projector path, sync extension, OTEL telemetry confirmation, wiring test.
- **Out of scope:** test helper consolidation (story 76-9), pre-existing test-stub failures (story 76-8), other embed pipeline hardening (stories 76-2–76-5).

## Acceptance Criteria
1. `project_faction_card()` exists and can extract and project faction entities from world lore. Faction cards carry consistent attributes (id, name, description, goals/beliefs where available).
2. `project_location_card()` exists and can extract location entities from three sources: room-graph rooms, world_materialization outputs, and PG promotions. Location cards are tagged with their source origin.
3. `sync_entity_cards()` iterates over both faction and location sources, projects each via the respective projectors, and adds them to the entity sync batch.
4. OTEL/watcher telemetry: `entity_sync.{faction,location}_count` emit > 0 when sources are present in a real game-state session (verified via GM-panel or logged watcher event).
5. Wiring test: a passing integration test that seed a world with factions + locations, runs a turn through narrator context building, and asserts that faction and location entities are indexed and retrievable via `_retrieve_entities_for_turn()`. (Not a source-text test per project rule — assert on entity_sync counts and retrieval, not on YAML presence.)
6. Full server suite green (uv run pytest tests/); ruff check + format clean.

## Key References
- **ADR-118 — Universal Retrieval Layer:** §D2 entity card sync/reproject pattern (established by 75-6, extended by 76-6, now extended to factions/locations).
- **Story 76-6 context** (`sprint/context/context-story-76-6.md`): the Npc projector path and sync extension pattern — faction and location paths follow the same blueprint.
- **Epic 76 context** (`sprint/context/context-epic-76.md`): full epic scope and cross-story dependencies. This story unblocks 75-7 (OTEL/GM-panel) and 75-8 (e2e retrieval integration).
- **lore_embedding.py**, **entity_embedding.py:** embedding patterns and OTEL telemetry model (story 76-3 mirrored expected_dim; story 76-5 modeled entity_pending telemetry).
- **Lore load model** (world loader): how factions are loaded and stored in the game state (`world_loader.py` / `world_lore` binding).
- **world_materialization module:** how locations are generated (ADR-005 background-first pipeline).
- **Room-graph navigation:** interior state and room representation.

## Context Dependencies
**Depends on:**
- Story 76-6 (snapshot.npcs sync) — the pattern and projector infrastructure this story extends.
- Stories 76-2 through 76-5 (hardening) — these stories improve test assertion quality and OTEL telemetry precision that this story builds on.

**Depended on by:**
- Story 75-7 (OTEL retrieval.universal instrumentation) — full GM-panel value depends on faction/location counts being > 0.
- Story 75-8 (end-to-end retrieval integration) — full e2e narrative integration depends on factions/locations being retrievable.

---
_Generated by sm-setup for story 76-7 during phase setup._
