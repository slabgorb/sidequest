---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-7: Encounter location overlays — read-time merge + `LOCATION_OVERLAY_CHANGED`

## Business Context

Wires `EncounterLocationOverlay` (the model 54-2 already shipped) into a live consumer. Encounters can contribute (a) extra typed entities (`entity_delta`) and (b) a `prose_suffix` to their bound room's manifest and description. Both merge at **read time** — the base authored manifest and base description never mutate. A new `LOCATION_OVERLAY_CHANGED` WebSocket message fires whenever an encounter touching a `bound_room_id` activates or deactivates.

This is the mechanism behind "a bar fight happens in the pub — when you walk back in next round, you see splinters and an overturned table appear in the description; when the encounter resolves and the bar is cleaned up, they vanish." Base prose never lies; overlays are encounter-scoped.

**Audience:** Keith-as-player (the narrative weight earned by mechanically-grounded transient state); the playgroup (when encounters touch the world, the world looks like it).

**Expected outcome:** `StructuredEncounter.location_overlay` is the new optional field. The read path returns a layered manifest/prose. The websocket delta channel fires on activate/deactivate transitions detected at the existing `prior_live`/`now_live` edges in the narration turn loop.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-7-encounter-location-overlays.md` — task-by-task TDD guide with exact file paths, full test code, and the activate/deactivate emit-site identification.

**Key files:**
- `sidequest-server/sidequest/game/encounter.py` — `StructuredEncounter` gains `location_overlay: EncounterLocationOverlay | None = None`.
- `sidequest-server/sidequest/game/location_resolver.py` — `_build_effective_manifest` + `resolve` extended with `overlays=` kwarg (default `()` — backward compatible with 54-6 callers).
- `sidequest-server/sidequest/game/location_view.py` (new) — `get_location_manifest`, `get_location_prose`, `active_overlays_for` per spec §5.5.
- `sidequest-server/sidequest/protocol/{enums,models,messages,__init__}.py` — `MessageType.LOCATION_OVERLAY_CHANGED` + payload + message class.
- `sidequest-server/sidequest/server/websocket_session_handler.py` — `_maybe_emit_location_overlay_changed()` helper; call sites at the existing `prior_live=False, now_live=True` activation edge (lines ~2991) and the existing `encounter_resolved_this_turn` deactivation edge (lines ~2782). Also: `_maybe_emit_location_description` (54-2) is updated to populate `payload.overlays` from the live snapshot.
- `sidequest-ui/src/types/{protocol,payloads}.ts` — TS payload types only (UI consumer is 54-9).

**Patterns to follow:**
- 54-6 contract preservation: `overlays=` default `()` so 54-6 callers see identical behavior.
- Single live encounter at a time per ADR-033 in v1 — the overlay list is a one-element seam for future multi-encounter support, not speculative engineering.
- `encounter_id` v1 shape: `f"{encounter_type}@{region_id}"` — `StructuredEncounter` has no stable instance id field today; documented inline.
- Deactivate payload carries an empty `overlays` list — UI replaces its slice rather than reconciling enter/leave diffs.

**What NOT to touch:**
- Dedicated `location.overlay.*` OTEL spans (54-8 wraps the watcher_publish event this story emits).
- The 54-6 resolver promote/mint logic.
- The UI render (54-9).

## Scope Boundaries

**In scope:**
- `StructuredEncounter.location_overlay` field.
- `_build_effective_manifest` overlay kwarg + resolver kwarg threading.
- `location_view.py` read-time merge.
- `LOCATION_OVERLAY_CHANGED` protocol surface (enum + payload + message + dispatch registration).
- `_maybe_emit_location_overlay_changed` + the two production call sites.
- `_maybe_emit_location_description` updated to populate `payload.overlays` from the snapshot.
- TS payload types.

**Out of scope:**
- Dedicated OTEL spans (54-8).
- GM-panel routing (54-8).
- UI render (54-9).
- Server-side authoring of which encounters get overlays (encounter content is separate; this story is plumbing).

## AC Context

**AC-1:** `StructuredEncounter` accepts `location_overlay: EncounterLocationOverlay | None`; default `None`; non-overlay encounters behave unchanged.

**AC-2:** `_build_effective_manifest(authored, promotions, overlays=())` returns `authored+promotions` when `overlays` is empty (backcompat) and `authored + overlay.entity_delta + minted-only promotions` when overlays are passed. Overlay entities carry `from_promotion=False` (they are encounter-scoped, never written to `location_promotions`).

**AC-3:** `get_location_manifest` and `get_location_prose` in `location_view.py` honor spec §5.5: authored + overlays merged; empty suffix dropped from prose; empty base + non-empty suffix returns suffix-only (no orphan separator).

**AC-4:** `MessageType.LOCATION_OVERLAY_CHANGED` is registered in the protocol enum, dispatch table, and TS const-object.

**AC-5:** `_maybe_emit_location_overlay_changed(transition="activate")` fires on the `prior_live=False, now_live=True` edge when the new encounter has a `location_overlay`. Payload carries one overlay summary.

**AC-6:** `_maybe_emit_location_overlay_changed(transition="deactivate", prior_overlay=...)` fires on the `encounter_resolved_this_turn` edge when the prior encounter had a `location_overlay`. Payload carries an empty `overlays` list.

**AC-7:** A wiring test asserts the emit helper has ≥2 non-test call sites in `websocket_session_handler.py` (def + activate + deactivate = 3 mentions minimum).

**AC-8:** The 54-2 `_maybe_emit_location_description` snapshot emit now includes the live overlay in `payload.prose` (via `get_location_prose`) and `payload.overlays` (via `active_overlays_for`), so a session-resume client sees the live overlay state without waiting for a delta.

**AC-9:** TS payload types in `sidequest-ui/src/types/payloads.ts` mirror the pydantic shape.
