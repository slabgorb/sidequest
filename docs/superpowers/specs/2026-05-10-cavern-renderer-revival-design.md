# Cavern Renderer Revival — Design Spec

**Status:** Draft (brainstorm complete, awaiting user review before plan)
**Date:** 2026-05-10
**Author:** Keith Avery
**ADR:** ADR-096 (to be written) — revives ADR-089's cellular-automata cavern path with current context. ADR-089's own callout instructs "do not revive this one — write a fresh ADR."
**Origin:** Claude Design hi-fi handoff (`/Users/slabgorb/Downloads/cavern maps-handoff.zip`, variation A).

## Summary

Replace the SVG-from-ASCII tactical renderer with a pre-rendered PNG path. A Python authoring tool (port of `maze-maker`'s `Cellular`) lives in `sidequest-content/tools/cavern_renderer/`. It reads room parameters (seed + cellular params) and emits committed PNG + ASCII-mask sidecars per room. The server delivers the PNG URL via the existing `TacticalGridPayload` (renamed `grid` → `mask`, plus new fields). The frontend `TacticalGridRenderer.tsx` is rewritten to image-mode; `DungeonMapRenderer.tsx` and ASCII-rendering paths are deleted. First slice: default + selected UI states. AoE targeting and explore-mode fog are out of scope for v1.

## Motivation

ADR-089 stated, and a year of failed renderer rounds confirmed, that SVG-from-ASCII is the wrong source-of-truth for tactical maps:

- The renderer has been through many rounds of fixes and never cleared a usability bar.
- Hand-authored grids are sterile rectangles; the cavern character lives entirely in narrative prose.
- A perfect renderer would faithfully display the wrong shapes.

ADR-086 (recipe-pipeline) shipped for portraits / POIs / illustrations and is correct for those. It is **not** correct for tactical maps where mechanical structure (LOS, movement validation, AoE anchoring) needs grounded cell data, not prompt-interpreted geometry. ADR-089's cellular-automata approach is the right answer for tactical caverns specifically. The hi-fi handoff bundle is the new design context that justifies revival.

## Audience and design constraints

Following CLAUDE.md's audience rubric:

- **Keith (forever-GM-as-player)** — needs a tactical view that surprises him; the cavern shapes must feel organic, not rectangular. Cellular CA delivers that.
- **Sebastien (mechanical-first)** — needs cell math to be real and visible. Cell-stepped movement / AoE / reach is the model. OTEL spans surface seed/density/floor_count for the GM panel.
- **Alex (slow typist, narrative-first)** — needs the renderer to never block his turn; image-mode renders instantly from a static PNG instead of recomputing SVG.
- **Playgroup pacing** — feature flag rollout is rejected (per locked decision); the cutover is single-merge so the playgroup never sees a half-wired state.

## Locked decisions (from brainstorm)

1. **Source of truth: seed + cellular parameters.** Mask + PNG are derived artifacts, regenerable.
2. **Generation: author-time CLI.** Artifacts (PNG + mask) are committed to `sidequest-content`; durable-by-default.
3. **Tool location: `sidequest-content/tools/cavern_renderer/`.** Its own `pyproject.toml`; uv-managed; no coupling to server install.
4. **Asset layout: `worlds/<world>/rooms/<room_id>.{yaml,cavern.png,mask.txt}`.** One file-set per room.
5. **First-target world: `caverns_sunden`.** Whole-world authoring: 3 dungeon descents fully (mawdeep_gullet, grimvault_descent, horden_warren) + hamlet stubs.
6. **Rollout: rip the SVG ASCII stack in one merge.** No feature flag. Replace `TacticalGridPayload`'s `grid` field; delete `DungeonMapRenderer.tsx` and SVG floor paths in `TacticalGridRenderer.tsx`.
7. **Cell math: cell-stepped (snap-to-cell).** Tokens occupy one cell; movement is N cells per turn; AoE evaluated against the floor mask cell-by-cell. Reach disc is a cell-set within Chebyshev radius `speed/5`, drawn as a circle but truth is discrete.
8. **UI scope v1: default + selected states.** AoE targeting and explore-fog deferred.
9. **Format flexibility: `room_type` field.** `cavern | settlement` for v1; future room types slot in.

## Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│  Authoring (offline, content-repo)                          │
│  sidequest-content/tools/cavern_renderer/                   │
│    cellular.py  → mask                                      │
│    render.py    → PNG  (Pillow, deterministic)              │
│    derive.py    → exits, POIs                               │
│    cli.py       → reads <room>.yaml, writes sidecars        │
└──────────────┬──────────────────────────────────────────────┘
               │ commits
               ▼
┌─────────────────────────────────────────────────────────────┐
│  sidequest-content/                                         │
│  genre_packs/caverns_and_claudes/worlds/caverns_sunden/     │
│    rooms/                                                   │
│      mouth.yaml         (seed + params, room_type: cavern)  │
│      mouth.cavern.png   (rendered)                          │
│      mouth.mask.txt     (ASCII)                             │
│      ...                                                    │
└──────────────┬──────────────────────────────────────────────┘
               │ static-served by FastAPI
               ▼
┌─────────────────────────────────────────────────────────────┐
│  sidequest-server (FastAPI)                                 │
│  Room loader → TacticalGridPayload (mask + cavern_image_url)│
│  OTEL: room_id, seed, density, floor_count, mask_bytes      │
└──────────────┬──────────────────────────────────────────────┘
               │ WebSocket
               ▼
┌─────────────────────────────────────────────────────────────┐
│  sidequest-ui                                               │
│  TacticalGridRenderer.tsx — <img> + token overlay           │
│  MapOverlay.tsx — default + selected states                 │
│  SettlementRoomView.tsx — non-cavern rooms                  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Authoring tool — `sidequest-content/tools/cavern_renderer/`

Layout:

```
sidequest-content/tools/cavern_renderer/
├── pyproject.toml                  # uv-managed; deps: pillow, pyyaml, click (or argparse)
├── cavern_renderer/
│   ├── __init__.py
│   ├── cellular.py                 # port of maze_maker/lib/maze_maker/cellular.rb
│   ├── render.py                   # Pillow → PNG (matches hi-fi canvas look)
│   ├── derive.py                   # exits + POIs (port of cave-gen.js helpers)
│   └── cli.py                      # python -m cavern_renderer <room.yaml>
└── tests/
    ├── test_cellular.py
    ├── test_render.py
    └── test_cli.py
```

**Cellular algorithm** — straight port of Ruby `Cellular`:
- Seeded RNG (`random.Random(seed)` — deterministic for `(width, height, seed, density, cutoff, passes)`).
- Initialize grid with `density` proportion floor (`0`) cells.
- `passes` iterations: each cell becomes wall if ≥ `cutoff` of 8 neighbors are walls, floor if < 4 are walls.
- Border is forced to wall.
- Flood-fill: keep largest connected floor component; everything else becomes wall.
- Output: `list[list[int]]` (0=floor, 1=wall).

**Render** — Pillow targets the hi-fi canvas look. Matching elements:
- Wall fill: `#0e0e18`.
- Floor cells: stone gradient `#3a3a4a` base, deterministic per-cell grain (small dots at hashed positions).
- Wall edges: inked dark line at floor↔wall boundaries.
- Wall stipple: `#28283a`-ish small dots in wall cells.
- Optional cell grid overlay (low-opacity white).
- Soft radial vignette (transparent center → 0.45 alpha at edges).
- Cell size configurable; default 28px to match the mock.

The hi-fi canvas (in `Map Tab Hi-Fi.html`) is a sketch, not a contractual target. Contract: "looks like cavern stone in the dark sidequest-ui theme."

**Derived data** (`derive.py`):
- `exits: {north|south|east|west: [x, y] | null}` — first floor cell adjacent to each border (port of `findExits`).
- `pois: [[x, y], ...]` — chamber centers (low local wall density, ≥3.5 cells apart; port of `findPOIs`).

Both can be overridden in the room YAML's `overrides:` block.

**CLI**:
- `python -m cavern_renderer <room.yaml>` — process one room. Writes sibling PNG + mask, re-writes YAML's `derived:` block.
- `python -m cavern_renderer --world worlds/<world>` — batch all rooms in a world.
- Idempotent: same input → byte-identical output.

### 2. Per-room data format

`worlds/<world>/rooms/<room_id>.yaml` — author-edited:

```yaml
id: mouth
name: "The Mouth"
region: mawdeep_gullet
narrative_tag: "the wet entrance, dripping limestone, sour air"
room_type: cavern              # cavern | settlement

cellular:                      # required when room_type == cavern
  size: [18, 18]
  seed: 1042
  density: 0.55
  cutoff: 5
  passes: 4
  cell_size: 28

overrides:                     # optional, all empty by default
  exits: {}
  pois: []
  poi_labels: {}

derived:                       # tool-written; hand-edits are stomped
  floor_count: 142
  exits: {north: [9, 0], east: [17, 9], south: null, west: null}
  pois: [[8, 8], [13, 6], [5, 11]]
  generated_at: "2026-05-10T14:22:00Z"
  generator_version: "0.1.0"
```

Settlement rooms:

```yaml
id: confessional
name: "The Confessional"
region: sunden_hamlet
room_type: settlement
description: >-
  A small house keyed to humility, against pride. ...
exits:                         # hand-authored for settlements
  - {to: sunden_square, label: "out to the square"}
```

**Exit semantics** — cavern rooms and settlement rooms use different `exits` shapes because they serve different purposes:
- Cavern rooms' `derived.exits: {direction: [x, y] | null}` are **cell positions** on the rendered map — the renderer pulses them per the hi-fi mock as visual affordances. They do *not* link to other rooms in v1; navigation between rooms is deferred to the room-graph follow-on (ADR-055 territory).
- Settlement rooms' `exits: [{to, label}]` are **pure links** — settlement rooms have no tactical map, so navigation is the only thing exits do.

A future room-graph story will likely unify these by adding `to: room_id` to cavern exits as well.

`<room_id>.mask.txt` — tool-written, one `.` (floor) or `#` (wall) per cell, rows newline-separated, no trailing whitespace.

`<room_id>.cavern.png` — tool-written, `cell_size * width × cell_size * height` pixels.

### 3. Authored world content

`caverns_sunden` gets fully authored in this slice:

- **mawdeep_gullet** (Gluttony, wet deep) — multi-room descent, cellular caverns. Exact room count determined during authoring (target ≥6).
- **grimvault_descent** (Pride, cold vault) — multi-room descent, cellular caverns. Target ≥6.
- **horden_warren** (Greed, counting passages) — multi-room descent, cellular caverns. Target ≥6.
- **sunden_hamlet** — settlement-type stubs for the named landmarks in `cartography.yaml`: Sünden Square, the Wall, Recruiter's Post, Confessional, Workhouse, Masquerade. ~6 rooms total. No tactical map, just navigation.

Total: ~18-25 cavern rooms + ~6 settlement stubs.

The `region:` field is a soft binding; multi-room navigation within a descent is **not** in this slice (deferred to a future room-graph story per ADR-055). The data exists for that story to consume.

### 4. Server protocol & data flow

**`TacticalGridPayload` shape** (`sidequest-server/sidequest/protocol/models.py:440`):

```python
class CellularParams(ProtocolBase):
    size: tuple[int, int]
    seed: int
    density: float
    cutoff: int
    passes: int

class DerivedRoomData(ProtocolBase):
    floor_count: int
    exits: dict[str, tuple[int, int] | None]
    pois: list[tuple[int, int]]

class TacticalGridPayload(ProtocolBase):
    room_id: str
    room_name: str
    room_type: Literal["cavern", "settlement"]

    # cavern fields (None when room_type == "settlement")
    mask: str | None                    # was: grid (semantics same; field renamed)
    cavern_image_url: str | None        # e.g. /content/.../mouth.cavern.png
    cell_size: int | None
    cellular: CellularParams | None
    derived: DerivedRoomData | None

    # always present
    tokens: list[TokenPayload]
    initiative: list[InitiativeEntry] | None  # null when not in combat
```

**Room loader** — reads `worlds/<world>/rooms/<room_id>.yaml` plus sibling `<room_id>.mask.txt` (cavern rooms only). PNG is referenced by URL, never loaded server-side.

**Static delivery** — confirmed during planning: `sidequest-server/sidequest/server/app.py:267` already mounts `/genre/*` against `SIDEQUEST_GENRE_PACKS`, and `sidequest-server/sidequest/server/asset_urls.py` provides `resolve_asset_url("genre_packs/...")` to convert content-relative paths into UI-fetchable URLs (CDN in prod, `/genre/...` locally). The room loader feeds `resolve_asset_url(f"genre_packs/{genre}/worlds/{world}/rooms/{room_id}.cavern.png")` into the payload. No new mount, no new env var.

**OTEL spans** — every cavern-room enter emits a span carrying `{room_id, seed, density, floor_count, mask_bytes_sha, image_url}`. The GM panel (Keith's lie-detector) can verify Claude isn't winging the room.

### 5. Frontend renderer

> **Spec correction (during planning, 2026-05-10):** The original draft of this section misidentified which UI files host tactical rendering. The MapWidget routing is: orbital → `OrbitalChartView`; room graph → `Automapper` (which delegates to `TacticalGridRenderer` for the current room when grid data is present, or to `DungeonMapRenderer` for the room-graph overhead view); cartography → `MapOverlay`. So:
>
> - **`MapOverlay.tsx` is the cartography view, not the tactical view.** It is not touched in this slice.
> - **`DungeonMapRenderer.tsx` is the room-graph view (ADR-055).** It is not touched in this slice.
> - **`TacticalGridRenderer.tsx` is the single-room tactical view.** It is the rewrite target.
> - The selection state (token click → reach disc + action panel) lives **inside** `TacticalGridRenderer.tsx` (or a small co-located component the renderer composes), not in `MapOverlay`.
> - Settlement rooms route through a new `SettlementRoomView.tsx` which `Automapper.tsx` mounts when `room_type == "settlement"` — a small branch added to `Automapper`'s existing 3-way delegation, not a parallel tree.

**Files deleted:**
- ASCII-rendering test paths in `tactical-grid-renderer.test.tsx` and `tactical-entity-story-29-10.test.tsx`; rewritten as image-mode tests.

**`TacticalGridRenderer.tsx` rewritten** — currently takes `grid: TacticalGridData` + `theme` props (single-room SVG renderer, story 29-4). Rewritten to accept the new `cavern_image_url` + `mask` + `tokens` shape, render `<img>` + token overlay, and own the selection state (default + selected per UI scope).

```typescript
// pseudo-shape
function TacticalGridRenderer({ payload, selectedTokenId, onSelectToken }) {
  if (payload.room_type === "settlement") return <SettlementRoomView payload={payload} />;
  const { cavern_image_url, cell_size, mask, tokens, derived } = payload;
  return (
    <div className="cavern-stage">
      <img src={cavern_image_url} className="cavern-floor" />
      <div className="overlay">
        {tokens.map(t => <Token cell={t.cell} cellSize={cell_size} ... />)}
        {selectedTokenId && <ReachDisc tokenId={selectedTokenId} mask={mask} cellSize={cell_size} />}
      </div>
    </div>
  );
}
```

Cell math helpers exported from the renderer module:
- `cellToPixel(cell, cellSize)` — for absolute positioning.
- `pixelToCell(point, cellSize)` — for click hit-testing.
- `isFloor(mask, cell)` — for movement / reach validation.

The renderer never reads `cellular` params; those ride along for OTEL/GM-panel transparency only.

**Default and selected states inside `TacticalGridRenderer.tsx`:**
- **Default** — image + tokens + initiative bar; hover-cell tooltip retained; no reach disc, no action panel.
- **Selected** — clicking a player/ally token opens the right-rail action panel (Move / Dash / Attack / Cast / Object / Dodge / End turn) and overlays the reach disc as a cell-set: every floor cell within Chebyshev radius `speed / 5`, highlighted as a translucent fill. Visualization is a circle silhouette; truth is discrete.

**`SettlementRoomView.tsx`** (new) — name + description + exit list. Mounted by `Automapper.tsx` as a new branch in its existing delegation when the current room's `room_type == "settlement"`.

**`Automapper.tsx`** — small change: the existing "single room with grid → TacticalGridRenderer" branch gains a sibling for settlement rooms. Its room-graph fallback (DungeonMapRenderer) is unchanged.

**`GameBoard/widgets/MapWidget.tsx`** — no changes; it routes by mapData shape, not by room_type. The settlement / cavern decision happens one layer down inside `Automapper`.

## Testing strategy

- **Cellular unit tests** — determinism across 10 random seeds; largest-component invariant (no isolated floor pockets); density bounds (0 < density < 1); same input → byte-identical mask output.
- **Render unit tests** — PNG dimensions match `cell_size * width × cell_size * height`; byte-stable golden PNG for one fixed seed (the test is the contract that PNG output is reproducible across machines).
- **CLI integration test** — run end-to-end on a fixture room.yaml; assert PNG and mask exist; assert `derived:` block written to YAML; re-run is idempotent (no diffs).
- **Server room-loader test** — load a real `caverns_sunden/rooms/mouth.yaml`; assert payload shape; assert `cavern_image_url` resolves to a file on disk.
- **Server static-mount wiring test** — spin the FastAPI app; HTTP-GET `cavern_image_url`; assert 200 + PNG bytes. Per CLAUDE.md "every test suite needs a wiring test."
- **Frontend renderer unit test** — render `TacticalGridRenderer` with a fixture cavern payload; assert `<img>` src matches `cavern_image_url`; assert tokens render at expected pixel positions for given cells.
- **Frontend selection test** — render with a selected token; assert reach disc highlights the correct cell-set for `speed=30, cellSize=28`.
- **Frontend settlement-route test** — render with `room_type: settlement`; assert `SettlementRoomView` mounts, no `<img>` is rendered, no tokens.

## Migration / cutover plan

Single merge, no feature flag.

**Note on rip-scope reconciliation.** During brainstorm the user first answered "Replace immediately, rip the SVG stack" (which on its surface meant deleting `MapOverlay.tsx`, `TacticalGridRenderer.tsx`, `DungeonMapRenderer.tsx` and starting fresh). They then pushed back with "why do we need a fresh view?" which narrowed the rip to: **evolve `MapOverlay.tsx` and `TacticalGridRenderer.tsx`** (the rendering hosts) while **deleting `DungeonMapRenderer.tsx` and the SVG floor-cell paths within `TacticalGridRenderer.tsx`**. That narrowed scope is what this spec implements. The intent of "rip the SVG stack" is honored — every SVG floor-rendering code path is gone — without rebuilding components that are already fit-for-purpose hosts.

1. **ADR-096** lands first as a standalone commit. ADR-089 frontmatter gets `superseded-by: 96`. Run `scripts/regenerate_adr_indexes.py`.
2. **Cavern renderer tool** lands second (independent — touches no app code).
3. **Author all `caverns_sunden` rooms**, run the tool, commit YAML + PNG + mask.
4. **Server changes** in one commit-set: room loader, payload shape, OTEL spans, static mount (if needed). Server tests rewritten in the same commit-set.
5. **Frontend changes** in one commit-set: `TacticalGridRenderer.tsx` rewrite, `MapOverlay.tsx` evolution, `SettlementRoomView.tsx` add, `DungeonMapRenderer.tsx` delete. Frontend tests rewritten in the same commit-set.
6. `just check-all` passes; manual playtest of one Mawdeep room and one hamlet room before merge.

**Pre-existing state risk** — verify (one grep) that no live save file references a `TacticalGridPayload` with the old `grid` field. `caverns_sunden` has never had per-room tactical maps, so no save should be affected. If a stale save is found, document the manual-fixup path; not a re-architect trigger.

**Documentation** — `CLAUDE.md` ADR index gets ADR-096 added. `docs/adr/DRIFT.md` gets any ADR-089 entry removed. `docs/adr/SUPERSEDED.md` updates ADR-089's supersession target. ADR-086 is unchanged.

## Out of scope (deferred follow-ons)

- AoE cone preview + casting confirmation flow (hi-fi state 3).
- Explore-mode vision fog + initiative-hidden HUD (hi-fi state 4).
- Room-graph navigation between rooms within a descent (ADR-055 territory).
- Authored (non-procedural) room layouts — e.g., a hand-drawn boss arena. Future `room_type` value (`dungeon_authored`).
- Token drag affordance (mock note flagged as not yet drawn).
- Hover-cell tooltip on every cell (currently retained from existing renderer; no expansion).
- Room-transition animation between maps.

## Open implementation questions

These are deliberately deferred to the implementation plan rather than pre-decided here:

- Whether `cavern_image_url` should carry a content-hash query param for cache-busting (probably yes; small detail).
- Exact pixel grain pattern in `render.py` (visual taste; iterate during impl).
- Whether `Pillow` wheels need pinning for Apple Silicon determinism (bytes-identical-across-machines goal — verify with the Python wheel that ships with `uv` and pin if it drifts).
- Per-pyproject-toml lockfile for the content-tools tree (probably yes; details in plan).

These are all "judge during implementation" questions, not architecture choices.
