---
id: 89
title: "Pre-Rendered Cavern Battle Maps via Ported Cellular Automata"
status: proposed
date: 2026-04-24
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [71, 86]
tags: [media-audio, room-graph]
implementation-status: drift
implementation-pointer: null
---

# ADR-089: Pre-Rendered Cavern Battle Maps via Ported Cellular Automata

## Status

Proposed

## Context

ADR-071 (Tactical ASCII Grid Maps) established an ASCII-grid-as-source-of-
truth model for tactical battle maps. It is implemented:

- `rooms.yaml` carries per-room `grid: |` ASCII fields with a glyph
  vocabulary and `legend:` block
- The server emits a `tactical_grid` protocol payload
  (`sidequest-server/sidequest/protocol/models.py:380`)
- The client renders the grid as SVG via
  `sidequest-ui/src/components/TacticalGridRenderer.tsx`, with the
  `Automapper.tsx` topology view wrapping it
- 3 hand-authored C&C worlds (mawdeep, grimvault, horden) own ~19 grids each

**The client renderer has been through many rounds of fixes and does not
work adequately in the frontend.** This is not a subjective aesthetic
complaint; the end-to-end path from `grid: |` through wire transport to
on-screen tactical display has repeatedly failed to clear a usability bar
despite sustained effort. The ASCII-as-source-of-truth model assumes the
renderer is a solved problem. In practice, it is the opposite: the
renderer is the expensive, brittle part, and the source data is sterile.

Inspection of the hand-authored grids confirms a second problem:
current rooms are rectangles with corner-clipping (`_##..##_`), not organic
caverns. The "cavern" character lives entirely in narrative prose. Even a
perfect SVG renderer would faithfully display rectangles-with-clipped-
corners, which is not what Caverns & Claudes wants.

So the existing system fails on two axes simultaneously — unreliable
rendering of underwhelming shapes — and piling more rounds of fixes onto
either axis has diminishing returns.

Two local tools were evaluated:

- **DonJuan** (`~/Projects/donjuan`) — Python procedural dungeon generator
  with matplotlib/PIL textured renderers and a `cave` texture pack. Emits
  rectangular rooms joined by corridors. Rectangles are the wrong shape for
  caverns.
- **maze-maker** (`~/Projects/maze-maker`) — minimal Ruby library. The
  **Cellular** class is textbook cellular-automata cave generation (~40
  lines). Ships with an RMagick renderer that fills floor cells as polygons
  over a textured background. The algorithm is correct for caves; the
  language is wrong — Ruby/rubygems is being retired from the stack.

## Decision

**Port maze-maker's Cellular algorithm and image renderer to Python.**
Build it as an authoring-time tool in `sidequest-content/tools/` that
generates **pre-rendered PNG battle maps** committed alongside each world.
ADR-071's ASCII grid as runtime source of truth is **superseded for visual
rendering**. The ASCII model is retained only as lightweight metadata for
tactical mechanics that still need cell-level data (LOS, movement grids,
AoE anchoring).

### Content Pipeline

```
Authoring time:
  spec.yaml (size, seed, density, texture)
    ↓
  sidequest-content/tools/cavern_renderer/  (Python)
    ├── cellular.py    # port of maze_maker/cellular.rb
    ├── flood_fill.py  # port of maze/count_size + POI detection
    ├── render.py      # Pillow-based renderer
    └── cli.py
    ↓
  worlds/<world>/maps/<room_id>.png                 # committed battle map
  worlds/<world>/maps/<room_id>.meta.yaml           # committed metadata
                                                     # (dimensions, cell_size,
                                                     #  floor_mask, poi_cells,
                                                     #  seed, generator params)

Runtime:
  RoomDef.map_image: "maps/<room_id>.png"           # new field
  RoomDef.map_meta:  "maps/<room_id>.meta.yaml"     # new field
  Client loads PNG directly; overlays tokens/zones on a <canvas> or <img>.
```

### Python Tool — Scope

One package, `sidequest-content/tools/cavern_renderer/`, with a
deterministic CLI. Components:

| Module | Source | Responsibility |
|---|---|---|
| `cellular.py` | port of `maze_maker/cellular.rb` | Cellular-automata grid generator |
| `grid.py` | port of `maze_maker/maze.rb` | 2D grid + neighborhoods + flood-fill + POI detection |
| `render.py` | new, inspired by `maze_maker/display.rb` | PIL renderer: floor polygons on textured background |
| `textures/` | new | PNG tile textures (cave_stone, cave_moss, sandstone, etc.) — replaces the `.psd` |
| `cli.py` | new | `cavern-render --world mawdeep --room mouth --size 16x16 --seed 42` |
| `spec.py` | new | Batch mode: read `maps.yaml` per world, regenerate any missing/stale maps |

**Not ported:** Prim, DepthFirst (wrong aesthetic), `numbering.rb` /
`roman.rb` (POI labels don't belong in the rendered map), ImageMagick
dependency, PyQt5 GUI.

### Calibration Gate

Running the Ruby Cellular class today at default parameters produces
degenerate output — density ≤ 0.60 collapses to all-walls, density 0.70
leaves 2-3 disconnected pockets. The port is not a translation; it is a
tuning exercise.

Explicit port acceptance criteria:

1. **Calibrated defaults.** For each room-size bucket (8×8, 12×12, 16×16,
   20×20, 24×24), the generator must produce playable caves at a
   documented default (density, cutoff, automaton passes) without
   intervention.
2. **Single connected component.** After generation, flood-fill keeps the
   largest floor component; all smaller components are walled in. This
   guarantees every cell the player can stand on is reachable from every
   other such cell.
3. **Chokepoint control.** The `find_points` POI detector tags cells where
   `local_density ≤ 2` at distance 2 — these are chamber centers. Minimum
   chamber count per map is a tunable parameter; if the CA doesn't produce
   enough, the spec is rejected and a different seed is tried.
4. **Deterministic.** Given `(size, seed, density, cutoff, passes)`, output
   is byte-identical across runs and platforms.

### Metadata Sidecar

The rendered PNG is the picture. The `.meta.yaml` is the mechanical data
still needed for tactical decisions:

```yaml
# worlds/mawdeep/maps/mouth.meta.yaml
room_id: mouth
image: mouth.png
dimensions: [16, 16]      # cells
cell_size_px: 32          # so pixel→cell math is explicit
generator:
  algorithm: cellular
  seed: 1042
  density: 0.72
  cutoff: 5
  passes: 5
  texture: cave_stone
floor_mask: |             # single source of truth for "is this cell walkable"
  ################
  #######..#######
  #####......#####
  ####........####
  ###..........###
  ###..........###
  ##............##
  #..............#
  #..............#
  ##............##
  ###..........###
  ###..........###
  ####........####
  #####......#####
  #######..#######
  ################
poi_cells:
  - [8, 3]
  - [8, 12]
exits:                    # authored, not generated; aligns to floor_mask wall gaps
  - { direction: north, cells: [[7, 0], [8, 0]], target: throat }
```

`floor_mask` is kept so the server, narrator, and tactical overlay can
still answer cell-level questions — "is this cell walkable", "where does a
20-foot cone from (8,8) heading east hit a wall". It is **not** shown to
the player; it is mechanical-only. The PNG is the only thing rendered.

### Client-Side Renderer Collapse

`TacticalGridRenderer.tsx` becomes a thin image component:

- `<img src={room.map_image}>` (or `<canvas>` if overlay compositing is
  needed)
- Token/entity layer: absolutely-positioned tokens whose pixel positions
  come from `cell_size_px * cell_xy`
- AoE zones: SVG overlay layer on top of the `<img>`, sized to match
- Fog of war: darkening overlay (CSS filter or SVG mask) on undiscovered
  regions

The SVG-from-ASCII path is deleted once per-world maps are rendered for
the C&C pilot. `tacticalGridFromWire.ts` simplifies to "load map
metadata"; the rich wire schema shrinks.

### Shared-Wall Constraint — Deprecated

ADR-071 §4–5 (shared-wall alignment, jaquayed cycle layout solver) are
**not needed** in the pre-rendered model. Each room is its own image.
Rooms do not compose into a single dungeon-wide rendered grid. Movement
between rooms is already room-graph-based (ADR-055) — the player is "in"
the target room when they transition, and the target room's map is
displayed. "The whole dungeon as one tactical map" was never required by
any story; ADR-071 over-engineered for it.

### Phased Migration

| Phase | Scope | Outcome |
|---|---|---|
| **1** | Port Cellular + flood-fill + renderer to Python. CLI only, no integration. Generate pilot maps for mawdeep offline, eyeball-review. | Go / no-go on the aesthetic before touching any wired code. |
| **2** | Add `map_image` / `map_meta` fields to `RoomDef`. Extend server to emit metadata alongside ASCII grid. Run generator across all 3 C&C worlds, commit PNGs. | Dual-source: ASCII grid AND rendered map coexist. Client still uses SVG. |
| **3** | Rewrite `TacticalGridRenderer` as image + overlay. Ship behind a per-world config flag. Playtest on mawdeep. | C&C uses rendered maps; other genres unaffected. |
| **4** | Delete `grid:` / `legend:` from C&C rooms. Simplify wire protocol. Remove SVG-from-ASCII path. | Single source of truth per genre; dead code removed. |

**Phase 1 is the gate.** If the rendered caves don't look good enough to
clear the bar set by this ADR, the port is archived and we stay on ASCII.
No ripple into existing systems until the pictures are good.

### Non-Goals

- **No runtime generation.** The renderer runs at authoring time. Production
  runtime sees committed PNGs + metadata, nothing else.
- **No browser-side procedural anything.** Client loads images.
- **No automatic exit cutting.** The cellular algorithm produces cave
  walls; exit-gap placement is an authoring step (human or World Builder
  agent), validated against neighbor rooms.
- **No style transfer / ML rendering.** Pillow + tile textures only.
  Deterministic output is the main requirement. AI-rendered maps are a
  separate conversation.
- **No cross-genre rollout in this ADR.** The port targets Caverns &
  Claudes cavern aesthetics. Other genres (low_fantasy keeps, victoria
  parlors, neon_dystopia arcologies) will need different visual tools.
  DonJuan remains a candidate there and is neither accepted nor rejected
  here.

## Consequences

### Positive

- **Correct aesthetic.** Organic cave shapes by construction. The thing
  Keith asked for.
- **Pre-rendered** — no runtime rendering cost, no SVG DOM nodes by the
  thousand, trivial client.
- **Python-only stack.** Ruby dependency retired. Tool colocates with
  existing `scripts/` and `sidequest-content/tools/` conventions.
- **Deterministic regeneration.** Any map can be rebuilt byte-identical
  from its metadata sidecar.
- **Simplified wire protocol.** `tactical_grid` payload shrinks to
  `map_image` URL + `map_meta` URL.
- **Metadata sidecar keeps mechanics honest.** Walkability, LOS, and AoE
  math still operate on a cell grid; the grid is just hidden from the
  player.

### Negative

- **Frontend rewrite.** `TacticalGridRenderer.tsx`, the topology Automapper,
  the protocol model, and the tests under `tactical-grid-renderer.test.tsx`
  all need to be replaced. Given that the current SVG renderer has not
  cleared the usability bar after repeated attempts, a clean replacement
  path is likely cheaper than the N+1 round of incremental fixes — but it
  is still real work, on the order of 1–2 stories.
- **Content rework.** 3 C&C worlds × ~19 rooms = ~57 rooms to regenerate +
  refine. Scriptable but not free.
- **Double source of truth during migration.** Phase 2 has both ASCII
  grid and rendered map for every room. Managed by the phased rollout;
  still real.
- **Calibration risk.** Phase 1 may discover the aesthetic bar isn't
  clearable by pure cellular-automata + tile textures — in which case the
  port was speculative work. Bounded by the Phase 1 gate.

### Risks

- **Texture library quality.** Pillow + tile PNGs can look cheap if the
  tiles are weak. Mitigation: start with 3–4 hand-selected seamless cave
  textures; iterate on art separately.
- **POI semantics drift.** maze-maker's `find_points` tags cells by local
  density; these may not align with where narrative features belong.
  Mitigation: POI output is a *suggestion*; World Builder refines.
- **"Pre-rendered" tempts content explosion.** If every room gets a
  bespoke map, authoring cost climbs. Mitigation: fixed seed list per
  world — regeneration is reproducible and churn-free.
- **ADR-071 rollback friction.** Existing shipped tests lock the SVG
  renderer's wire contract. Phase 3 flip will need coordinated test
  rewrites.

## Alternatives Considered

1. **Keep ADR-071 as-is, improve ASCII authoring** — rejected by
   stakeholder. ASCII rectangles-with-clipped-corners do not read as
   caverns, and SVG rendering of same is the wrong output.

2. **DonJuan textured renderer** — deferred. DonJuan emits rectangular
   rooms; cavern aesthetic fails. Remains a candidate for architectural
   genres in a later ADR.

3. **LoRA-generated map images** — rejected (again, per ADR-071 Decision
   §1). Non-deterministic; can't be token-overlayed reliably; fails
   regeneration requirement.

4. **SVG-from-ASCII with hand-tuned wall curvature** — considered briefly.
   Output is still constrained by the authoring glyph vocabulary; the
   underlying grids are still rectangles-with-clipped-corners. Doesn't
   solve the aesthetic problem.

5. **Runtime Python server renders maps on demand** — rejected. The
   daemon is image-gen-hungry already; adding deterministic renders at
   session start adds latency with no benefit over pre-committed PNGs.

6. **Canvas + PNG tileset (ADR-071 alternatives table)** — partially
   adopted. The *rendering* is PNG, but the *source of truth* is the
   generator + metadata, not hand-placed tiles.

## References

- ADR-055: Room Graph Navigation
- ADR-071: Tactical ASCII Grid Maps **(superseded in part by this ADR for
  visual rendering; retained for mechanical cell data via metadata sidecar)**
- `~/Projects/maze-maker/lib/maze_maker/cellular.rb` — port source
- `~/Projects/maze-maker/lib/maze_maker/maze.rb` — port source (grid,
  flood-fill, POI detection)
- `~/Projects/maze-maker/lib/maze_maker/display.rb` — renderer reference
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml`
  — pilot target
- `sidequest-ui/src/components/TacticalGridRenderer.tsx` — client to
  replace in Phase 3
- `sidequest-server/sidequest/protocol/models.py:380` — `tactical_grid`
  payload to simplify
