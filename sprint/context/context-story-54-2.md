---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-2: Server schema — LocationEntity types + LOCATION_DESCRIPTION WebSocket message

## Business Context

The foundation story of Epic 54. Lands the typed pydantic models (`LocationEntity`, `LocationEntityBinding`, `EncounterLocationOverlay`), extends `cartography.yaml regions[*]` and `<world>/rooms/<id>.yaml` with a typed `entities[]` field, surfaces the manifest through `TacticalGridPayload` and the cartography region payload, and emits a new `LOCATION_DESCRIPTION` WebSocket message on `current_room` change and session resume.

**Audience:** Every story 54-3 through 54-9 plus 55-1 depends on this story. The type names, OTEL attribute names, save-id convention (`"default"`), and the `_build_effective_manifest()` extension seam established here are referenced by every later plan.

**Expected outcome:** A single PR that lands the schema + the snapshot emit message, with the `overlays` payload field explicitly empty until 54-7 lands. Existing worlds load unchanged (the legacy untyped `landmarks: list[str]` coexists with the new typed `entities[]` for backward compatibility).

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-2-location-entity-schema-and-message.md` — task-by-task TDD guide with exact file paths, full test code, and step-level commit shape.

**Key files (read these first):**
- `sidequest-server/sidequest/protocol/models.py` — where the manifest models land (alongside `TacticalGridPayload`).
- `sidequest-server/sidequest/protocol/enums.py` — `MessageType.LOCATION_DESCRIPTION`.
- `sidequest-server/sidequest/protocol/messages.py` — `LocationDescriptionMessage` + dispatch registration (look for `"TACTICAL_GRID": TacticalGridMessage` to find every dispatch site).
- `sidequest-server/sidequest/genre/models/world.py` — `Region` model gains `entities: list[LocationEntity]`.
- `sidequest-server/sidequest/game/room_file_loader.py` — parses top-level `entities[]` from YAML, surfaces through `TacticalGridPayload`.
- `sidequest-server/sidequest/server/websocket_session_handler.py` — `_maybe_emit_location_description()` mirrors `_maybe_emit_tactical_grid()` (lines ~454, ~2050, ~3980).
- `sidequest-ui/src/types/payloads.ts` — TS payload types (mirror the pydantic shape).
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/sunden_square.yaml` — seeded with a small `entities:` block for the wiring test.

**Patterns to follow:**
- pydantic v2 `model_config = {"extra": "forbid"}`.
- Mirror the existing `_maybe_emit_tactical_grid` shape exactly — same call sites, same args, same watcher-event style.
- "Every test suite needs a wiring test" (CLAUDE.md): the integration test asserts `_maybe_emit_location_description` has a non-test caller in production code.

**What NOT to touch:**
- The resolver (54-6), overlays (54-7), OTEL spans (54-8), UI render (54-9), or validator (54-3) — all explicitly out of scope.
- Mutating authored YAML at runtime — authored is read-only by contract.

## Scope Boundaries

**In scope:**
- `LocationEntity`, `LocationEntityBinding`, `EncounterLocationOverlay` pydantic models.
- `LocationDescriptionPayload` + `LocationDescriptionMessage` + `MessageType.LOCATION_DESCRIPTION`.
- `Region.entities` field (cartography-side).
- `TacticalGridPayload.entities` field + `room_file_loader` parsing.
- `_maybe_emit_location_description()` + call sites at room-change and session-resume.
- TypeScript payload types in `sidequest-ui/src/types/payloads.ts` (consumed by 54-9; type lands here).
- One seeded fixture room (`sunden_square.yaml`) for the wiring test.

**Out of scope:**
- `LOCATION_OVERLAY_CHANGED` (54-7).
- Resolver tool / `location_promotions` table (54-6).
- Dedicated OTEL spans (54-8).
- UI component (54-9).
- Validator (54-3).
- Authored content backfill beyond the one fixture (54-4, 54-5).

## AC Context

**AC-1:** pydantic models import cleanly, reject extra fields, reject blank ids/labels, accept all four `provenance` literals, and round-trip via `model_dump()`.

**AC-2:** `MessageType.LOCATION_DESCRIPTION = "LOCATION_DESCRIPTION"` is in the enum; the dispatch table maps it to `LocationDescriptionMessage`.

**AC-3:** `Region.entities` defaults to `[]` and parses typed entities from cartography YAML; the legacy `landmarks` field still loads on pre-54 worlds.

**AC-4:** `room_file_loader.load_room_payload()` parses top-level `entities:` and surfaces it on `TacticalGridPayload.entities`; rooms without an `entities:` block produce an empty list.

**AC-5:** `_maybe_emit_location_description()` exists and is called from production code paths (room change + session resume). When called with a room that has no manifest source, it emits a `location_description.no_source` watcher event and silently returns (graceful absence).

**AC-6:** A wiring test asserts the emit helper has at least one non-test caller in `websocket_session_handler.py` (per CLAUDE.md). A second wiring test mounts a real `load_room_payload` against the `sunden_square` fixture and asserts the emitted message carries the typed entities.

**AC-7:** TypeScript `LocationDescriptionPayload` (and `LocationEntity`, `LocationEntityBinding`, `LocationDescriptionOverlaySummary`) types mirror the pydantic shape. `npx tsc --noEmit` clean.

**AC-8:** `payload.overlays` is always emitted as `[]` in this story — overlay population is explicitly owned by 54-7.
