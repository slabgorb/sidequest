---
parent: context-epic-54.md
workflow: tdd
---

# Story 54-8: Location OTEL spans + GM-panel surfacing

## Business Context

Replace the bare OTEL attribute-setting (54-6) and bare `watcher_publish` events (54-7) with proper dedicated SPAN definitions for every location-resolver and location-overlay event. Surface them on the GM panel so Keith / Sebastien see the *exact* lie-detector signal (`narrator_proactive resolved=false` → yellow) and the *exact* positive-canon signal (`player_initiated minted`, `narrator_proactive promoted` → blue) when narration is running live.

**Audience:** Keith (the lie-detector — can a 40-year-veteran GM see when the narrator went off contract?); Sebastien (the mechanical-first player who wants to *see* the rules engage — OTEL visibility is a feature for him, not a debug tool, per project memory `project_gm_panel_audience`).

**Expected outcome:** Five dedicated spans (`location.entity.resolve`, `.minted`, `.promoted`, `.overlay.activate`, `.overlay.deactivate`) routed through `SPAN_ROUTES` as `state_transition` events under `component="location"`. GM-panel SubsystemsTab upgrades cells with `is_lie_detector: true` to warning treatment. The 54-7 bare `_watcher_publish("location_overlay_changed.emitted", ...)` is removed — the dedicated span carries the same fields through the same fan-out.

## Technical Guardrails

**Implementation plan:** `docs/superpowers/plans/2026-05-19-story-54-8-location-otel-and-gm-panel.md` — task-by-task TDD guide with full helper code and the route-extractor `is_lie_detector` / `is_positive_canon` boolean discipline.

**Key files:**
- `sidequest-server/sidequest/telemetry/spans/location.py` (new) — five `SPAN_*` constants, five `@contextmanager` helpers, five `SPAN_ROUTES` entries with `is_lie_detector` / `is_positive_canon` discipline in the extractors.
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — add `from .location import *` alphabetically (between `.local_dm` and `.lore`).
- `sidequest-server/sidequest/agents/tools/resolve_location_entity.py` — wraps the resolver call in `location_entity_resolve_span(...)`; emits `.minted` / `.promoted` on the corresponding `mode_outcome`. Keeps the 54-6 side-channel `ctx.otel_span.set_attribute(...)` calls (other write tools rely on the same pattern for tool-dispatch introspection).
- `sidequest-server/sidequest/server/websocket_session_handler.py` — `_maybe_emit_location_overlay_changed` (54-7) wrapped in the new `location.overlay.activate` / `location.overlay.deactivate` spans; the bare `_watcher_publish("location_overlay_changed.emitted", ...)` is **removed**.
- `sidequest-ui/src/components/Dashboard/shared/constants.ts` — `COMP_COLORS["location"]` added.
- `sidequest-ui/src/components/Dashboard/tabs/SubsystemsTab.tsx` — `is_lie_detector` field upgrades cell colour to warn even on info-severity spans.

**Patterns to follow:**
- `cavern_room.py` is the closest existing analog (`SPAN_CAVERN_ROOM_LOAD`, single `SpanRoute`, single `@contextmanager` helper).
- Severity stays `info` at emit time; UI applies the colour rule via the route extractor's explicit booleans. ADR-031 keeps colour logic in one place — the route, not the consumer.
- `test_routing_completeness.py` is the repo-wide static lint that enforces every `SPAN_*` constant gets a route. The new constants must each appear in `SPAN_ROUTES`.

**What NOT to touch:**
- The 54-6 resolver promote/mint logic.
- The 54-7 read-time merge or the `LOCATION_OVERLAY_CHANGED` payload shape.
- The 54-6 side-channel attributes on `ctx.otel_span` — keep them; they coexist with the new dedicated spans.

## Scope Boundaries

**In scope:**
- Five `SPAN_*` constants + `@contextmanager` helpers + `SPAN_ROUTES` entries.
- 54-6 tool adapter rewritten to wrap calls in the dedicated spans.
- 54-7 overlay emit rewritten to fire dedicated spans + bare `_watcher_publish` removed.
- GM panel `COMP_COLORS["location"]` + lie-detector cell upgrade.

**Out of scope:**
- A dedicated EncounterTab-style detail panel for location events (SubsystemsTab + ConsoleTab filter are sufficient for v1).
- UI Location panel rendering (54-9).
- Cookbook-driven span emit for procedural materialization (55-1).

## AC Context

**AC-1:** `SPAN_LOCATION_ENTITY_RESOLVE`, `_MINTED`, `_PROMOTED`, `_OVERLAY_ACTIVATE`, `_OVERLAY_DEACTIVATE` constants exist with canonical names (`"location.entity.resolve"`, etc.).

**AC-2:** Each constant has a `SPAN_ROUTES` entry with `event_type="state_transition"`, `component="location"`. `test_routing_completeness.py` stays green.

**AC-3:** `_extract_resolve` sets `is_lie_detector=True` when `mode="narrator_proactive" AND resolved=False`; `is_lie_detector=False` in every other case (explicit, never absent).

**AC-4:** `_extract_minted` and `_extract_promoted` set `is_positive_canon=True`.

**AC-5:** `resolve_location_entity` tool emits the dedicated `location.entity.resolve` span on every call; emits `.minted` on `mode_outcome="minted"`; emits `.promoted` on `mode_outcome="promoted"`; never emits `.minted` or `.promoted` on `mode_outcome="matched"` or `"no_match"`.

**AC-6:** `_maybe_emit_location_overlay_changed` emits `location.overlay.activate` on transition="activate" and `location.overlay.deactivate` on transition="deactivate". The previous bare `_watcher_publish("location_overlay_changed.emitted", ...)` call is removed.

**AC-7:** `COMP_COLORS["location"]` is added with a hue distinct from existing entries.

**AC-8:** `SubsystemsTab.tsx`'s `gridData` `useMemo` upgrades any cell whose events include `fields.is_lie_detector === true` to the warn treatment (amber border / cell colour) even when `event.severity === "info"`.

**AC-9:** A UI wiring test mounts SubsystemsTab with a synthetic location event carrying `is_lie_detector: true` and asserts the amber theme colour is present in the rendered output.

**AC-10:** `just check-all` green.
