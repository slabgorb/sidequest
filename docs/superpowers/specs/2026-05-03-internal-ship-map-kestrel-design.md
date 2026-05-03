# Internal Ship Map — Kestrel (Coyote Star) — Design

**Date:** 2026-05-03
**Author:** SM brainstorm w/ Keith
**Status:** Approved (brainstorm)
**Related plans:** `2026-04-29-rig-mvp-coyote-reach.md` (Phase A shipped, Phase C filed as 47-4)
**Related ADRs:** ADR-026 (client state mirror), ADR-027 (reactive state messaging), ADR-038 (WebSocket transport), ADR-090 (OTEL dashboard)
**Mirrors pattern of:** `2026-05-01-orbital-map-design.md` (orbital chart — server-rendered SVG, fetched on bind, refetched on STATE_PATCH)

## Goal

Ship a **persistent server-rendered SVG of the Kestrel's interior** for tonight's playgroup session. Four rooms, four crew stations, narrator-tracked PC and NPC positions. FTL-style vector aesthetic in the Coyote Star engraved register so it sits visually next to the orbital chart.

This is a *one-off feature* for the Friday game, not a Sprint 3 story. Filed via `/pf-patch` or `/pf-standalone`. The downstream features (intercom, battle stations) are explicitly **out of scope** — see "Deferred / Future" at the bottom.

## Why this and not something else

Per the SOUL.md *Tabletop First, Then Better* principle: a tabletop DM cannot sustain "where everyone is on the ship" across a multi-hour session — the medium can. Persistent visual state is exactly the amplifier the medium provides over verbal play. Battle Stations and natural-language ship comms are already covered by Opus + the table. The map is the bit Opus can't sustain alone.

## Architecture

Mirrors the orbital chart pattern (which just shipped in PR #177). Server is authoritative, UI is a thin SVG display layer. New `sidequest/interior/` module owns the content models, loader, and SVG renderer. UI gains a **Ship** tab beside Map; component fetches the SVG once on bind and re-fetches when a `STATE_PATCH` touches `current_room` for any tracked actor.

```
┌─────────────────────────────────┐
│ chassis_classes.yaml            │  content (NEW: stations block)
│ rigs.yaml (Kestrel instance)    │  content (existing)
└──────────────┬──────────────────┘
               │ load
               ▼
┌─────────────────────────────────┐
│ sidequest/interior/             │  server module (NEW)
│   models.py    Station,         │
│                InteriorRoom     │
│   loader.py                     │
│   renderer.py  SVG composer     │
└──────────────┬──────────────────┘
               │ GET /api/chassis/{instance_id}/interior
               ▼
┌─────────────────────────────────┐
│ sidequest-ui                    │
│   src/screens/ShipTab.tsx (NEW) │
│   InteriorView.tsx        (NEW) │
└─────────────────────────────────┘
```

**Position tracking:** narrator owns it (option B from brainstorm). When the narrator describes movement, it emits a `state_patch` updating `character.current_room`. Snapshot mirror picks it up; UI refetches the SVG.

## Content schema additions

Append to `sidequest-content/genre_packs/space_opera/chassis_classes.yaml` under `voidborn_freighter`:

```yaml
    stations:
      - id: command
        display_name: "Command"
        room: cockpit
        preferred_role: captain        # soft hint to narrator; Firefly skill curve
      - id: helm
        display_name: "Helm"
        room: cockpit
        preferred_role: pilot
      - id: weapons
        display_name: "Weapons"
        room: cockpit
        preferred_role: gunner
      - id: engineering_controls
        display_name: "Engineering"
        room: engineering
        preferred_role: engineer
```

**Layout summary:**

| Room | Stations |
|---|---|
| Cockpit | Command, Helm, Weapons |
| Engineering | Engineering Controls |
| Galley | (none — social/bond space, `the_tea_brew` lives here) |
| Deck Three Corridor | (none — `liminal_warm` connector) |

**Why no comms station:** the Kestrel itself is the comms. The chassis voice schema (already authored) gives the ship its own voice, addressing the captain by bond-tier-appropriate name-form. Players talk to each other via the ship — no separate console needed.

**Why station IDs are role-coded but operations are open:** Firefly model. Anyone can stand at any station; preferred_role is a soft hint the narrator uses to bias outcomes, not a hard gate. Zoe can fly. Wash is just better at it.

## Server module — `sidequest/interior/`

New module mirroring `sidequest/orbital/` shape. Files:

| File | Role |
|---|---|
| `models.py` | `Station`, `InteriorRoom` (extends existing `chassis_classes` schema with `stations: list[Station]` field) |
| `loader.py` | Load + validate stations from chassis YAML; cross-validate `station.room ∈ chassis.interior_rooms` |
| `renderer.py` | `render_interior_svg(chassis_instance, snapshot) -> str` — pure function, no I/O |
| `dispatch.py` | REST endpoint handler |

**Key data flow** for `render_interior_svg`:

1. Load chassis class definition (rooms, stations).
2. Load chassis instance (Kestrel: name, crew_npcs).
3. Walk snapshot to find every actor (PCs + NPCs) where `current_room` matches a chassis room.
4. Compose SVG with:
   - Room rectangles laid out in a hardcoded 2x2 grid (cockpit top-left, engineering top-right, galley bottom-left, corridor bottom-right — engraved frames).
   - Station pips inside each room, FTL-style (small filled circles with labels).
   - Actor markers in their `current_room`, color-coded PC vs NPC.
   - Chassis title bar with the Kestrel's name in the same engraved register as the orbital chart.

**Layout coordinates are hardcoded for the Kestrel.** Generalizing to multiple chassis classes is deferred.

## Snapshot extension

Add `current_room: str | None = None` to the character model (`sidequest/game/character.py` or wherever `Character` lives — Dev finds the canonical spot during execution).

Materialization defaults:
- PCs: default to `None` (narrator sets it on first scene; renderer draws PCs in cockpit if `None`).
- NPCs: default from `crew_role.default_seat` if defined; else first room of chassis.

The Kestrel NPCs (kestrel_captain, kestrel_engineer, kestrel_doc, kestrel_cook) get sensible defaults:
- captain → cockpit
- engineer → engineering
- doc → galley (if anyone's hurt, they're closest there)
- cook → galley

These are *defaults*, not constraints. The narrator can move anyone anywhere via `state_patch`.

## REST endpoint

`GET /api/chassis/{instance_id}/interior` → `image/svg+xml`

- Reads current snapshot from session bound to caller.
- Calls `render_interior_svg`.
- Emits `interior.render` OTEL span with attrs: `chassis_instance_id`, `actor_count`, `tracked_pcs`, `tracked_npcs`.
- Returns the SVG body.

## UI — Ship tab

New tab in the main game UI, sibling of Map (orbital chart already lives in Map). Component:

```typescript
// sidequest-ui/src/screens/ShipTab.tsx
export function ShipTab({ chassisInstanceId }: Props) {
  const svg = useChassisInteriorSVG(chassisInstanceId);
  return <InteriorView svg={svg} />;
}
```

`useChassisInteriorSVG` hook:
- Fetches the SVG once on tab bind.
- Subscribes to `STATE_PATCH` events on the WS mirror.
- Refetches when a patch touches `current_room` for any actor in this chassis.
- Caches the SVG in component state; falls back to the last good SVG if a refetch fails (graceful degradation).

No animation. Snap markers between fetches.

## Narrator hook

Two changes to the narrator prompt assembly:

1. **Surface `current_room`** for every PC and tracked NPC in the character section: "Rux is in the galley. Captain is in the cockpit."
2. **Instruct the narrator** to emit a state patch when characters move: when the narrative describes a character moving to a different room, include `{"op": "set", "path": "/characters/{id}/current_room", "value": "<room_id>"}` in the JSON sidecar.

**Graceful failure:** if the narrator forgets, positions stay where they last were. The map never breaks. This is consistent with how every other narrator-tracked field works.

## OTEL spans

Per CLAUDE.md OTEL principle (every backend fix that touches a subsystem MUST add OTEL):

| Span | When | Attrs |
|---|---|---|
| `interior.render` | Every SVG composition | chassis_instance_id, actor_count, tracked_pcs, tracked_npcs |
| `interior.position_change` | When a state_patch updates `current_room` | actor_id, from_room, to_room, source (narrator/default) |

Both spans live in `sidequest/telemetry/spans/interior.py` (mirrors orbital's pattern).

## Error handling — fail loud

Per CLAUDE.md *No Silent Fallbacks*:

| Condition | Behavior |
|---|---|
| Chassis instance not found | 404 from REST endpoint |
| Station references unknown room | `LoaderError` at startup with explicit `station_id`, `bad_room` |
| Snapshot has `current_room` referencing a room not in the chassis | Drop that actor's marker, emit `interior.render` span attr `dropped_actors=[id]`. Don't silently move them. |
| Narrator emits state_patch with bad room | State patch validator rejects (existing pipeline); narrator sees the error in next turn's context |

## Testing

Per CLAUDE.md *Every Test Suite Needs a Wiring Test*:

| Test file | Purpose |
|---|---|
| `tests/interior/test_models.py` | Station/InteriorRoom validation |
| `tests/interior/test_loader.py` | Cross-validation: every station's room exists in chassis interior_rooms |
| `tests/interior/test_renderer.py` | SVG snapshot test (golden vector) for the Kestrel |
| `tests/interior/test_endpoint_wired.py` | **Wiring test** — REST endpoint reachable from FastAPI app, returns SVG content-type |
| `tests/agents/test_narrator_current_room.py` | **Wiring test** — narrator prompt assembly includes `current_room` per character |
| `tests/server/test_state_patch_current_room.py` | State patch on `current_room` survives roundtrip |

UI: one vitest verifying the tab renders + refetches on STATE_PATCH (mirrors orbital's tab test).

## Phasing

| # | Step | Notes |
|---|---|---|
| 1 | Author 4 stations on voidborn_freighter | content |
| 2 | `current_room` snapshot field + materialization defaults | server |
| 3 | `sidequest/interior/` module: models, loader, renderer | server |
| 4 | REST endpoint + wiring test | server |
| 5 | UI Ship tab + fetch + STATE_PATCH mirror | ui |
| 6 | Narrator prompt hook + state-patch instruction | server |
| 7 | OTEL spans | server |
| 8 | Boot, smoke, fix one or two things | all |

**Total budget:** ~30 min for the code, a touch more with spec/plan/PR ceremony.

## Graceful cuts (if something breaks)

In priority order, drop from the bottom:

1. **OTEL spans** — file as debt, ship without.
2. **Narrator hook** — positions show defaults only; map still feels alive.
3. **NPC tracking** — PCs only.
4. **Station-occupied highlighting** — labels only, no "this station is being operated" pip.

The minimum-viable map is: 4 rooms, the Kestrel's name, PCs in their last-set rooms (or cockpit if `None`). Everything above is amplification.

## Out of scope / Deferred

These are the other two features from the original brainstorm. Explicitly **not** in this spec:

- **Intercom comms** — the Kestrel's voice already handles cross-room communication narratively. If it ever needs UI, that's a separate spec.
- **Battle Stations** — Opus already handles this from natural language ("Captain, battle stations!"). The map could later highlight unmanned stations during combat scenes, but that's a follow-on.
- **Click-to-move on the map** — contradicts the Zork Problem principle (UI menus narrowing the verb set). Position is narrator-driven, full stop.
- **Multi-chassis support** — layout coords are hardcoded for the Kestrel. The day a second chassis ships, the renderer gets a layout-by-class mapping; not before.
- **Damage / power / system state** — FTL has these because it's a real-time tactical sim. SideQuest is narrative; these belong in the narrator's prose, not the map.

## Acceptance

- The Kestrel's interior renders as an SVG when the player opens the Ship tab.
- All four rooms visible, four stations rendered as pips.
- Four NPCs visible at their default rooms.
- PCs visible in their `current_room` (or cockpit default).
- A narrator-emitted state patch on `current_room` causes the marker to move on next refetch.
- OTEL `interior.render` span fires on every render.
- No silent fallbacks; bad data fails loudly.
