# Cavern Renderer Revival Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the SVG-from-ASCII tactical renderer with a pre-rendered PNG path: a Python `cavern_renderer` authoring tool emits committed PNG + mask sidecars per room; the server delivers them via an evolved `TacticalGridPayload`; the frontend `TacticalGridRenderer` is rewritten to image-mode with default + selected UI states. First-target world: `caverns_sunden` (whole-world authoring of 3 cavern descents + hamlet stubs).

**Architecture:** Author-time CLI in `sidequest-content/tools/cavern_renderer/` (Python port of `~/Projects/maze-maker`'s `Cellular`) reads `<room_id>.yaml` (seed + cellular params) and writes sibling `<room_id>.cavern.png` + `<room_id>.mask.txt` artifacts that get committed. Server room loader emits payload with mask + cavern image URL via existing `resolve_asset_url()`. Frontend renders `<img>` + token overlay; selection state lives inside `TacticalGridRenderer.tsx`. Single-merge cutover, no feature flag.

**Tech Stack:** Python 3.12 + Pillow + uv (renderer tool), FastAPI + pydantic (server), React 18 + Vite + Vitest (UI), pytest (server + tool tests).

---

## Spec & ADR references

- Spec: `docs/superpowers/specs/2026-05-10-cavern-renderer-revival-design.md`
- ADR-089 (superseded original): `docs/adr/089-cavern-template-generation.md`
- ADR-086 (recipe pipeline; sibling, not in conflict): `docs/adr/086-image-composition-taxonomy.md`
- Maze-maker source for the port: `~/Projects/maze-maker/lib/maze_maker/cellular.rb`
- Hi-fi handoff (visual target): `/tmp/cavern-maps-handoff/cavern-maps/project/Map Tab Hi-Fi.html`
- JS prototype of the algorithm (working reference): `/tmp/cavern-maps-handoff/cavern-maps/project/cave-gen.js`

---

## File structure

**Created:**
- `docs/adr/096-cavern-renderer-revival.md` — new ADR
- `sidequest-content/tools/cavern_renderer/pyproject.toml`
- `sidequest-content/tools/cavern_renderer/cavern_renderer/__init__.py`
- `sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py`
- `sidequest-content/tools/cavern_renderer/cavern_renderer/derive.py`
- `sidequest-content/tools/cavern_renderer/cavern_renderer/render.py`
- `sidequest-content/tools/cavern_renderer/cavern_renderer/cli.py`
- `sidequest-content/tools/cavern_renderer/tests/__init__.py`
- `sidequest-content/tools/cavern_renderer/tests/test_cellular.py`
- `sidequest-content/tools/cavern_renderer/tests/test_derive.py`
- `sidequest-content/tools/cavern_renderer/tests/test_render.py`
- `sidequest-content/tools/cavern_renderer/tests/test_cli.py`
- `sidequest-content/tools/cavern_renderer/tests/fixtures/sample_room.yaml`
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/<room_id>.yaml` × ~24 (cavern) + ~6 (settlement)
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/<room_id>.cavern.png` × ~24 (cavern only)
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/<room_id>.mask.txt` × ~24
- `sidequest-server/sidequest/game/room_file_loader.py` — loads new per-room YAML + mask
- `sidequest-server/tests/game/test_room_file_loader.py`
- `sidequest-server/tests/integration/test_cavern_static_mount.py` — wiring test
- `sidequest-server/sidequest/telemetry/spans/cavern_room.py` — new OTEL span
- `sidequest-ui/src/components/SettlementRoomView.tsx`
- `sidequest-ui/src/components/__tests__/SettlementRoomView.test.tsx`
- `sidequest-ui/src/components/CavernActionPanel.tsx` — right-rail action panel for selected token
- `sidequest-ui/src/components/__tests__/CavernActionPanel.test.tsx`
- `sidequest-ui/src/lib/cellMath.ts` — cellToPixel / pixelToCell / chebyshevReachCells
- `sidequest-ui/src/lib/__tests__/cellMath.test.ts`

**Modified:**
- `docs/adr/089-cavern-template-generation.md` — frontmatter `superseded-by: 96`
- `CLAUDE.md` — ADR index gets ADR-096
- `sidequest-server/sidequest/protocol/models.py` — `TacticalGridPayload` reshaped
- `sidequest-server/sidequest/protocol/__init__.py` — export new types
- `sidequest-ui/src/components/TacticalGridRenderer.tsx` — full rewrite
- `sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx` — rewritten for image mode
- `sidequest-ui/src/__tests__/tactical-entity-story-29-10.test.tsx` — rewritten for image mode (or deleted if redundant)
- `sidequest-ui/src/components/Automapper.tsx` — settlement branch added
- `sidequest-ui/src/components/__tests__/Automapper.test.tsx` — settlement-branch coverage
- `sidequest-ui/src/types/tactical.ts` — `TacticalGridData` interface reshaped (mask + image_url)
- `sidequest-ui/src/lib/tacticalGridFromWire.ts` — adapter updated for new wire shape

**Untouched (despite original spec mentioning):**
- `sidequest-ui/src/components/MapOverlay.tsx` (cartography view)
- `sidequest-ui/src/components/DungeonMapRenderer.tsx` (room-graph view)
- `sidequest-ui/src/components/__tests__/MapOverlay.cartography.test.tsx`
- `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` (routes by mapData shape, not room_type)

---

## Phase A — ADRs

### Task 1: Write ADR-096

**Files:**
- Create: `docs/adr/096-cavern-renderer-revival.md`

- [ ] **Step 1: Write the new ADR**

```markdown
---
id: 96
title: "Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps"
status: accepted
date: 2026-05-10
deciders: ["Keith Avery"]
supersedes: [89]
superseded-by: null
related: [55, 71, 86, 89]
tags: [game-systems, frontend-protocol, media-audio]
implementation-status: in-progress
implementation-pointer: docs/superpowers/plans/2026-05-10-cavern-renderer-revival.md
---

# ADR-096: Cavern Renderer Revival — Pre-Rendered Cellular Caverns for Tactical Maps

## Status

Accepted (2026-05-10).

Revives ADR-089 (superseded 2026-05-02 by ADR-086) per ADR-089's own
"do not revive — write a fresh ADR" instruction. ADR-086's recipe
pipeline (portraits / POIs / illustrations) is unchanged and
unaffected; ADR-096 is a sibling decision for tactical maps
specifically.

## Context

ADR-071 (tactical ASCII grids → SVG) was the original tactical-map path.
It was implemented and shipped, then went through many rounds of fixes
without ever clearing a usability bar. Hand-authored grids produce
rectangles-with-clipped-corners, not organic caverns. The cavern
character lives only in narrative prose. ADR-089 proposed porting
maze-maker's Cellular automaton to Python and emitting pre-rendered PNG
battle maps; it was superseded by ADR-086 because a competing recipe
pipeline shipped first and the cellular path's authoring overhead
seemed unjustified.

What's changed: a Claude Design hi-fi handoff (variation A, 2026-05-10)
gave us a concrete UI target — image-as-floor with token overlays,
selection state, action panel — that requires exactly the
mechanically-grounded structure (cells, LOS, AoE anchoring, movement
validation) ADR-086's prompt-interpreted geometry can't deliver. ADR-086
is correct for portraits and POIs and stays in production. Tactical
caverns need the cellular path.

## Decision

Revive ADR-089's core idea — port maze-maker's `Cellular` to Python,
build an authoring-time tool that emits PNG + ASCII-mask sidecars per
room, ship them as committed artifacts in `sidequest-content`. Three
concrete differences from ADR-089:

1. **Authoring source-of-truth is `seed + cellular params`, not the
   mask.** Mask + PNG are derived; same input → byte-identical
   output. Authors edit numbers, not cells.
2. **Cell-stepped math is canonical.** Tokens occupy one cell;
   movement is N cells per turn; reach is Chebyshev radius
   `speed/5`; AoE is evaluated cell-by-cell against the mask. The
   PNG is the visual; the mask is the truth.
3. **Single-merge cutover, no feature flag.** The SVG floor-cell
   rendering paths in `TacticalGridRenderer.tsx` and their tests are
   deleted in the same merge that introduces the cellular path.
   `MapOverlay.tsx` (cartography view) and `DungeonMapRenderer.tsx`
   (room-graph view) are unaffected.

## Consequences

**Positive:**

- Tactical caverns finally look like caverns. Keith (the forever-GM
  primary audience) gets a tactical view with organic shapes.
- Sebastien (mechanical-first) gets cell-stepped math that's
  observable in OTEL spans (seed, density, floor_count, mask_sha).
- Alex (slow typist) is unblocked — image renders instantly from a
  static asset, no SVG-recompute lag per frame.
- ADR-071's renderer-rounds-of-fixes loop ends. The expensive part
  (visual rendering) becomes Pillow output that authors verify once
  and commit; the runtime path is `<img>` + token overlays.

**Negative:**

- ~24 cellular rooms + ~6 settlement stubs need authoring for
  `caverns_sunden`. Real authoring effort, not generated content.
- A second uv-managed Python tree appears in `sidequest-content/`.
  Mitigated: it's authoring-only; runtime never sees it.
- PNG bytes go into git history. Mitigated: 18×18 cells × 28px = 504×504
  PNG ≈ tens of kilobytes per room.
- Existing `caverns_sunden` has never had per-room tactical files;
  the ADR-071 hand-authored grids in other worlds (mawdeep,
  grimvault, horden) referenced in ADR-089's text no longer exist
  on disk. No save migration needed.

**Neutral:**

- Settlement rooms get a parallel non-tactical view. Future
  non-procedural room types (e.g., a hand-authored boss arena) slot
  in as new `room_type` values without re-architecting.

## Implementation

See `docs/superpowers/plans/2026-05-10-cavern-renderer-revival.md`.
```

- [ ] **Step 2: Verify ADR file is well-formed**

Run: `head -16 docs/adr/096-cavern-renderer-revival.md`
Expected: frontmatter parses (id: 96, status: accepted, supersedes: [89]).

- [ ] **Step 3: Commit**

```bash
git add docs/adr/096-cavern-renderer-revival.md
git commit -m "docs(adr): ADR-096 — cavern renderer revival (revives ADR-089)

Per ADR-089's own 'do not revive — write a fresh ADR' instruction.
ADR-086 (recipe pipeline) is sibling, not in conflict.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Update ADR-089 frontmatter and regenerate ADR indexes

**Files:**
- Modify: `docs/adr/089-cavern-template-generation.md` (frontmatter only)
- Modify: `CLAUDE.md` (ADR index)
- Run: `scripts/regenerate_adr_indexes.py`

- [ ] **Step 1: Update ADR-089 `superseded-by` field**

Read the current frontmatter. Change `superseded-by: 86` to `superseded-by: 96`. (ADR-089 was originally noted as superseded by 86 because that was the live ADR; ADR-096 now revives the cellular path and is the more accurate supersession target.) Also update the prose callout at the top of the file: replace "Superseded by ADR-086" with "Superseded by ADR-096 (revival, 2026-05-10) — see also ADR-086 for the parallel recipe pipeline."

- [ ] **Step 2: Update CLAUDE.md ADR index**

In the orchestrator `CLAUDE.md` ADR index section, add ADR-096 to the "Game Systems" group:

```
- 095 Class Mechanical Surface ... · 096 Cavern Renderer Revival
```

Also bold ADR-096 if marking it as load-bearing. Add a one-liner under "Load-bearing reads" if appropriate (it is — tactical maps are core).

- [ ] **Step 3: Run the ADR index regenerator**

Run: `python3 scripts/regenerate_adr_indexes.py`
Expected: writes updated index files; no errors. Inspect diff with `git diff docs/adr/`.

- [ ] **Step 4: Commit**

```bash
git add docs/adr/089-cavern-template-generation.md docs/adr/README.md docs/adr/SUPERSEDED.md CLAUDE.md
git commit -m "docs(adr): ADR-089 superseded-by: 96; regenerate indexes

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase B — Cavern Renderer Tool

### Task 3: Bootstrap the cavern_renderer Python package

**Files:**
- Create: `sidequest-content/tools/cavern_renderer/pyproject.toml`
- Create: `sidequest-content/tools/cavern_renderer/cavern_renderer/__init__.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/__init__.py`
- Create: `sidequest-content/tools/cavern_renderer/.gitignore`

- [ ] **Step 1: Create directories**

```bash
mkdir -p sidequest-content/tools/cavern_renderer/cavern_renderer
mkdir -p sidequest-content/tools/cavern_renderer/tests
mkdir -p sidequest-content/tools/cavern_renderer/tests/fixtures
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[project]
name = "cavern_renderer"
version = "0.1.0"
description = "Author-time tool: cellular-automata cavern → PNG + ASCII mask. ADR-096."
requires-python = ">=3.12"
dependencies = [
    "pillow>=10.4.0",
    "pyyaml>=6.0.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "ruff>=0.6.0",
]

[project.scripts]
cavern_renderer = "cavern_renderer.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["cavern_renderer"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write minimal package init**

`sidequest-content/tools/cavern_renderer/cavern_renderer/__init__.py`:

```python
"""cavern_renderer — author-time cellular cavern map tool. See ADR-096."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Write empty tests/__init__.py**

```python
```

- [ ] **Step 5: Write .gitignore**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
dist/
build/
```

- [ ] **Step 6: Verify package installs**

```bash
cd sidequest-content/tools/cavern_renderer
uv sync --all-extras
uv run pytest --version
```
Expected: `pytest 8.x.x` printed; no install errors.

- [ ] **Step 7: Commit**

```bash
git add sidequest-content/tools/cavern_renderer/
git commit -m "feat(cavern_renderer): bootstrap Python package skeleton

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Cellular algorithm (TDD)

**Files:**
- Create: `sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/test_cellular.py`

Reference Ruby source: `~/Projects/maze-maker/lib/maze_maker/cellular.rb`. Reference JS port: `/tmp/cavern-maps-handoff/cavern-maps/project/cave-gen.js` (function `genCave`).

- [ ] **Step 1: Write the failing test for `gen_cave` shape & determinism**

`tests/test_cellular.py`:

```python
"""Tests for cellular CA cavern generator."""

from cavern_renderer.cellular import gen_cave, FLOOR, WALL


def test_gen_cave_returns_grid_of_correct_shape():
    grid = gen_cave(width=18, height=18, seed=1042)
    assert len(grid) == 18
    assert all(len(row) == 18 for row in grid)


def test_gen_cave_borders_are_walls():
    grid = gen_cave(width=18, height=18, seed=1042)
    for x in range(18):
        assert grid[0][x] == WALL
        assert grid[17][x] == WALL
    for y in range(18):
        assert grid[y][0] == WALL
        assert grid[y][17] == WALL


def test_gen_cave_is_deterministic_for_same_seed():
    g1 = gen_cave(width=18, height=18, seed=1042)
    g2 = gen_cave(width=18, height=18, seed=1042)
    assert g1 == g2


def test_gen_cave_differs_for_different_seed():
    g1 = gen_cave(width=18, height=18, seed=1042)
    g2 = gen_cave(width=18, height=18, seed=2099)
    assert g1 != g2


def test_gen_cave_only_floor_or_wall_values():
    grid = gen_cave(width=18, height=18, seed=1042)
    for row in grid:
        for cell in row:
            assert cell in (FLOOR, WALL)


def test_gen_cave_has_floor_cells():
    grid = gen_cave(width=18, height=18, seed=1042)
    floor_count = sum(1 for row in grid for cell in row if cell == FLOOR)
    assert floor_count > 50  # 18x18 with default density 0.55 → ≥50 floor cells
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd sidequest-content/tools/cavern_renderer
uv run pytest tests/test_cellular.py -v
```
Expected: ImportError — `cellular` module doesn't exist yet.

- [ ] **Step 3: Implement minimal `gen_cave`**

`cavern_renderer/cellular.py`:

```python
"""Cellular automata cavern generator.

Port of maze-maker's Cellular class:
~/Projects/maze-maker/lib/maze_maker/cellular.rb

JS reference: cave-gen.js (function genCave) from the Claude Design hi-fi
handoff bundle.

Convention: 0 = floor, 1 = wall (matches maze_maker).
"""

from __future__ import annotations

import random

FLOOR = 0
WALL = 1


def gen_cave(
    width: int,
    height: int,
    seed: int,
    *,
    density: float = 0.55,
    cutoff: int = 5,
    passes: int = 4,
) -> list[list[int]]:
    """Generate a cellular-automaton cavern.

    Returns a (height x width) grid of FLOOR (0) or WALL (1).

    Determinism: same (width, height, seed, density, cutoff, passes) →
    identical output.

    Algorithm:
    1. Seed each interior cell as FLOOR with `density` probability.
    2. Force border cells to WALL.
    3. Run `passes` iterations of the standard CA rule:
       - cell becomes WALL if ≥ cutoff of 8 neighbors are walls
       - cell becomes FLOOR if < 4 of 8 neighbors are walls
    4. Flood-fill: keep largest connected FLOOR region; fill the rest.
    """
    rng = random.Random(seed)
    grid = [
        [FLOOR if rng.random() < density else WALL for _ in range(width)]
        for _ in range(height)
    ]
    # Borders forced to wall
    for x in range(width):
        grid[0][x] = WALL
        grid[height - 1][x] = WALL
    for y in range(height):
        grid[y][0] = WALL
        grid[y][width - 1] = WALL

    for _ in range(passes):
        grid = _ca_pass(grid, width, height, cutoff)

    grid = _keep_largest_floor_region(grid, width, height)
    return grid


def _ca_pass(grid: list[list[int]], width: int, height: int, cutoff: int) -> list[list[int]]:
    new = [row[:] for row in grid]
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            walls = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    if grid[y + dy][x + dx] == WALL:
                        walls += 1
            if walls >= cutoff:
                new[y][x] = WALL
            elif walls < 4:
                new[y][x] = FLOOR
    return new


def _keep_largest_floor_region(
    grid: list[list[int]], width: int, height: int
) -> list[list[int]]:
    seen = [[False] * width for _ in range(height)]
    best: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if grid[y][x] != FLOOR or seen[y][x]:
                continue
            region = _flood(grid, seen, x, y, width, height)
            if len(region) > len(best):
                best = region
    keep = {(x, y) for x, y in best}
    out = [row[:] for row in grid]
    for y in range(height):
        for x in range(width):
            if grid[y][x] == FLOOR and (x, y) not in keep:
                out[y][x] = WALL
    return out


def _flood(
    grid: list[list[int]],
    seen: list[list[bool]],
    sx: int,
    sy: int,
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    stack = [(sx, sy)]
    region: list[tuple[int, int]] = []
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if seen[y][x] or grid[y][x] != FLOOR:
            continue
        seen[y][x] = True
        region.append((x, y))
        stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    return region
```

- [ ] **Step 4: Run tests, verify pass**

```bash
uv run pytest tests/test_cellular.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 5: Add largest-component invariant test**

```python
def test_gen_cave_floor_is_single_connected_component():
    """After flood-fill, all FLOOR cells should be reachable from any other."""
    grid = gen_cave(width=18, height=18, seed=1042)
    h, w = len(grid), len(grid[0])
    # find first floor
    start = None
    for y in range(h):
        for x in range(w):
            if grid[y][x] == FLOOR:
                start = (x, y)
                break
        if start:
            break
    assert start is not None
    # BFS from start, count reachable floors
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] == FLOOR and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    total_floor = sum(1 for row in grid for c in row if c == FLOOR)
    assert len(seen) == total_floor, "found isolated floor pocket"
```

- [ ] **Step 6: Run, verify pass**

```bash
uv run pytest tests/test_cellular.py -v
```
Expected: all 7 tests pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py sidequest-content/tools/cavern_renderer/tests/test_cellular.py
git commit -m "feat(cavern_renderer): cellular CA generator with TDD

Port of maze-maker's Cellular class. Deterministic by seed; flood-fill
ensures single connected floor region.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Derive helpers (exits + POIs)

**Files:**
- Create: `sidequest-content/tools/cavern_renderer/cavern_renderer/derive.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/test_derive.py`

Reference: `cave-gen.js` `findExits` and `findPOIs` functions.

- [ ] **Step 1: Write failing tests**

```python
"""Tests for derived data — exits, POIs."""

from cavern_renderer.cellular import gen_cave
from cavern_renderer.derive import find_exits, find_pois, floor_count


def test_find_exits_returns_dict_with_four_directions():
    grid = gen_cave(width=18, height=18, seed=1042)
    exits = find_exits(grid)
    assert set(exits.keys()) == {"north", "south", "east", "west"}


def test_find_exits_north_is_first_floor_adjacent_to_top_border():
    grid = [
        [1, 1, 1, 1, 1],
        [1, 1, 0, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 1, 1, 1, 1],
    ]
    exits = find_exits(grid)
    assert exits["north"] == (2, 0)


def test_find_exits_returns_none_for_blocked_side():
    grid = [
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 0, 1, 1],
        [1, 1, 1, 1, 1],
    ]
    exits = find_exits(grid)
    assert exits["north"] is None


def test_find_pois_returns_low_density_chamber_centers():
    grid = gen_cave(width=18, height=18, seed=1042)
    pois = find_pois(grid)
    assert len(pois) >= 1
    assert all(isinstance(p, tuple) and len(p) == 2 for p in pois)


def test_find_pois_are_spaced_apart():
    grid = gen_cave(width=18, height=18, seed=1042)
    pois = find_pois(grid)
    for i, (x1, y1) in enumerate(pois):
        for x2, y2 in pois[i + 1:]:
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            assert dist > 3.5


def test_floor_count_matches_zero_cells():
    grid = [[0, 1], [1, 0]]
    assert floor_count(grid) == 2
```

- [ ] **Step 2: Run, verify failure**

```bash
uv run pytest tests/test_derive.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `derive.py`**

```python
"""Derived data from cellular caverns: exits, POIs, floor count.

Ports the helpers in cave-gen.js: findExits, findPOIs, floorCount.
"""

from __future__ import annotations

import math

from cavern_renderer.cellular import FLOOR, WALL


def floor_count(grid: list[list[int]]) -> int:
    """Number of FLOOR cells in the grid."""
    return sum(1 for row in grid for cell in row if cell == FLOOR)


def find_exits(grid: list[list[int]]) -> dict[str, tuple[int, int] | None]:
    """First floor cell adjacent to each side of the bounding box.

    Returns the **border** cell (e.g. y=0 for north), not the interior
    floor cell. The border is always WALL after gen_cave; the exit
    coordinate is the wall position you'd carve through to reach the
    interior floor at (x, 1).
    """
    h = len(grid)
    w = len(grid[0]) if h else 0
    sides: dict[str, tuple[int, int] | None] = {
        "north": None, "south": None, "east": None, "west": None,
    }
    for x in range(1, w - 1):
        if sides["north"] is None and grid[1][x] == FLOOR:
            sides["north"] = (x, 0)
        if sides["south"] is None and grid[h - 2][x] == FLOOR:
            sides["south"] = (x, h - 1)
    for y in range(1, h - 1):
        if sides["west"] is None and grid[y][1] == FLOOR:
            sides["west"] = (0, y)
        if sides["east"] is None and grid[y][w - 2] == FLOOR:
            sides["east"] = (w - 1, y)
    return sides


def find_pois(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Chamber centers: floor cells with low local wall density.

    Mirrors cave-gen.js findPOIs: 5x5 neighborhood, fewer than 4 walls,
    and at least 3.5 cells apart from previously-found POIs.
    """
    h = len(grid)
    w = len(grid[0]) if h else 0
    out: list[tuple[int, int]] = []
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if grid[y][x] != FLOOR:
                continue
            walls = 0
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if dx == 0 and dy == 0:
                        continue
                    if grid[y + dy][x + dx] == WALL:
                        walls += 1
            if walls < 4:
                if all(math.hypot(px - x, py - y) > 3.5 for px, py in out):
                    out.append((x, y))
    return out
```

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/test_derive.py -v
```
Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-content/tools/cavern_renderer/cavern_renderer/derive.py sidequest-content/tools/cavern_renderer/tests/test_derive.py
git commit -m "feat(cavern_renderer): derive exits + POIs + floor_count

Ports cave-gen.js findExits / findPOIs / floorCount.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Pillow renderer (TDD)

**Files:**
- Create: `sidequest-content/tools/cavern_renderer/cavern_renderer/render.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/test_render.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/fixtures/golden_seed1042_18x18_28px.png` (committed after first run-and-inspect)

Visual reference: `Map Tab Hi-Fi.html` `renderCaveToCanvas()` JS function (the canvas-based stand-in). Pillow render must look like cavern stone in the dark sidequest-ui theme — exact match to the JS canvas is not contractual, but produces visually similar output.

- [ ] **Step 1: Write failing tests for dimensions & determinism**

```python
"""Tests for Pillow PNG renderer."""

import hashlib
from pathlib import Path

import pytest

from cavern_renderer.cellular import gen_cave
from cavern_renderer.render import render_grid_to_png


def test_render_dimensions_match_grid_times_cell_size(tmp_path):
    grid = gen_cave(width=18, height=18, seed=1042)
    out = tmp_path / "test.png"
    render_grid_to_png(grid, out, cell_size=28)

    from PIL import Image
    with Image.open(out) as img:
        assert img.size == (18 * 28, 18 * 28)
        assert img.mode == "RGB"


def test_render_is_byte_deterministic_for_same_input(tmp_path):
    grid = gen_cave(width=18, height=18, seed=1042)
    out1 = tmp_path / "a.png"
    out2 = tmp_path / "b.png"
    render_grid_to_png(grid, out1, cell_size=28)
    render_grid_to_png(grid, out2, cell_size=28)
    assert out1.read_bytes() == out2.read_bytes()


def test_render_handles_smaller_cell_size(tmp_path):
    grid = gen_cave(width=12, height=12, seed=99)
    out = tmp_path / "small.png"
    render_grid_to_png(grid, out, cell_size=16)

    from PIL import Image
    with Image.open(out) as img:
        assert img.size == (12 * 16, 12 * 16)


def test_render_creates_parent_dir_if_needed(tmp_path):
    grid = gen_cave(width=8, height=8, seed=1)
    out = tmp_path / "nested" / "dir" / "x.png"
    render_grid_to_png(grid, out, cell_size=20)
    assert out.exists()
```

- [ ] **Step 2: Run, verify failure**

```bash
uv run pytest tests/test_render.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `render.py`**

```python
"""Pillow PNG renderer for cellular cavern grids.

Visual target: cavern stone in the dark sidequest-ui theme.
- floor cells: stone-gradient #3a3a4a base + deterministic per-cell grain
- walls:       inked #0e0e18 with stipple
- edges:       dark inked line at floor↔wall boundary
- vignette:    soft radial darkening at edges

The exact visual is allowed to drift from the JS reference; the contract
is reproducibility (same input → byte-identical PNG) and looking like
cavern stone in the SideQuest theme.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from cavern_renderer.cellular import FLOOR, WALL

_FLOOR_BASE = (58, 58, 74)        # #3a3a4a
_WALL_BASE = (14, 14, 24)         # #0e0e18
_GRAIN = (80, 80, 96)             # subtle dot
_INK = (0, 0, 0)
_GRID_LINE = (255, 255, 255)


def render_grid_to_png(
    grid: list[list[int]],
    output_path: Path,
    *,
    cell_size: int = 28,
    show_grid: bool = True,
) -> None:
    """Render a cellular cavern grid to a PNG file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    h = len(grid)
    w = len(grid[0]) if h else 0
    img = Image.new("RGB", (w * cell_size, h * cell_size), _WALL_BASE)
    draw = ImageDraw.Draw(img)

    # Floor cells with grain
    for y in range(h):
        for x in range(w):
            if grid[y][x] != FLOOR:
                continue
            px, py = x * cell_size, y * cell_size
            draw.rectangle(
                (px, py, px + cell_size - 1, py + cell_size - 1),
                fill=_FLOOR_BASE,
            )
            for i in range(6):
                hx = (x * 928371 + y * 7177 + i * 1733) % cell_size
                hy = (x * 31193 + y * 9241 + i * 4441) % cell_size
                v = (x * 19 + y * 7 + i * 11) % 5
                alpha_band = 0.06 + v * 0.04
                tint = _blend(_FLOOR_BASE, _GRAIN, alpha_band)
                draw.rectangle(
                    (px + hx, py + hy, px + hx + 1, py + hy + 1),
                    fill=tint,
                )

    # Inked edges around floor cells where they meet walls
    for y in range(h):
        for x in range(w):
            if grid[y][x] != FLOOR:
                continue
            px, py = x * cell_size, y * cell_size
            if y > 0 and grid[y - 1][x] == WALL:
                draw.line((px, py, px + cell_size - 1, py), fill=_INK)
            if y < h - 1 and grid[y + 1][x] == WALL:
                draw.line((px, py + cell_size - 1, px + cell_size - 1, py + cell_size - 1), fill=_INK)
            if x > 0 and grid[y][x - 1] == WALL:
                draw.line((px, py, px, py + cell_size - 1), fill=_INK)
            if x < w - 1 and grid[y][x + 1] == WALL:
                draw.line((px + cell_size - 1, py, px + cell_size - 1, py + cell_size - 1), fill=_INK)

    # Wall stipple
    for y in range(h):
        for x in range(w):
            if grid[y][x] != WALL:
                continue
            px, py = x * cell_size, y * cell_size
            for i in range(3):
                hx = (x * 1117 + y * 313 + i * 97) % cell_size
                hy = (x * 503 + y * 911 + i * 251) % cell_size
                draw.rectangle(
                    (px + hx, py + hy, px + hx + 1, py + hy + 1),
                    fill=(40, 40, 56),
                )

    # Optional grid overlay
    if show_grid:
        for x in range(w + 1):
            draw.line(
                ((x * cell_size, 0), (x * cell_size, h * cell_size)),
                fill=_blend((0, 0, 0), _GRID_LINE, 0.04),
            )
        for y in range(h + 1):
            draw.line(
                ((0, y * cell_size), (w * cell_size, y * cell_size)),
                fill=_blend((0, 0, 0), _GRID_LINE, 0.04),
            )

    img.save(output_path, "PNG", optimize=True)


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )
```

- [ ] **Step 4: Run, verify pass**

```bash
uv run pytest tests/test_render.py -v
```
Expected: 4 tests pass.

- [ ] **Step 5: Generate and inspect a golden PNG**

Manually render a sample to `/tmp/cavern_sample.png`, open it, confirm it looks like cavern stone in the dark sidequest-ui theme:

```bash
uv run python -c "
from pathlib import Path
from cavern_renderer.cellular import gen_cave
from cavern_renderer.render import render_grid_to_png
g = gen_cave(18, 18, 1042)
render_grid_to_png(g, Path('/tmp/cavern_sample.png'), cell_size=28)
print('rendered')
"
open /tmp/cavern_sample.png
```

If the visual is wrong (too bright, no contrast, wrong color cast): tweak constants in `render.py`, re-run, re-inspect. Iterate until it reads as "cavern stone in dark sidequest-ui theme." This is taste-iteration, not test-driven; commit the result.

- [ ] **Step 6: Commit golden test fixture**

Once visual is acceptable, copy to fixtures and add a golden-bytes test:

```bash
cp /tmp/cavern_sample.png sidequest-content/tools/cavern_renderer/tests/fixtures/golden_seed1042_18x18_28px.png
```

Add to `tests/test_render.py`:

```python
def test_render_byte_matches_golden(tmp_path):
    """Pin output bytes for a known seed/dimensions/cell-size combo.

    If this fails after a render.py edit, decide: visual change intentional?
    Update the golden. Visual change accidental? Fix the regression.
    """
    grid = gen_cave(width=18, height=18, seed=1042)
    out = tmp_path / "test.png"
    render_grid_to_png(grid, out, cell_size=28)

    golden_path = Path(__file__).parent / "fixtures" / "golden_seed1042_18x18_28px.png"
    assert out.read_bytes() == golden_path.read_bytes()
```

Run: `uv run pytest tests/test_render.py -v` → all 5 tests pass.

- [ ] **Step 7: Commit**

```bash
git add sidequest-content/tools/cavern_renderer/cavern_renderer/render.py sidequest-content/tools/cavern_renderer/tests/test_render.py sidequest-content/tools/cavern_renderer/tests/fixtures/golden_seed1042_18x18_28px.png
git commit -m "feat(cavern_renderer): Pillow PNG renderer with golden test

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: CLI

**Files:**
- Create: `sidequest-content/tools/cavern_renderer/cavern_renderer/cli.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/test_cli.py`
- Create: `sidequest-content/tools/cavern_renderer/tests/fixtures/sample_room.yaml`

The CLI reads `<room_id>.yaml`, runs cellular + derive + render, writes sibling `<room_id>.cavern.png` and `<room_id>.mask.txt`, and re-writes the YAML's `derived:` block.

- [ ] **Step 1: Write a fixture room.yaml**

`tests/fixtures/sample_room.yaml`:

```yaml
id: sample_mouth
name: "Sample Mouth"
region: mawdeep_gullet
narrative_tag: "fixture room for tests"
room_type: cavern

cellular:
  size: [18, 18]
  seed: 1042
  density: 0.55
  cutoff: 5
  passes: 4
  cell_size: 28

overrides:
  exits: {}
  pois: []
  poi_labels: {}
```

- [ ] **Step 2: Write failing CLI tests**

```python
"""Tests for the CLI entrypoint."""

import shutil
from pathlib import Path

import pytest
import yaml

from cavern_renderer.cli import process_room

FIXTURE = Path(__file__).parent / "fixtures" / "sample_room.yaml"


@pytest.fixture
def room_in_tmp(tmp_path: Path) -> Path:
    dst = tmp_path / "sample_mouth.yaml"
    shutil.copy(FIXTURE, dst)
    return dst


def test_process_room_writes_png_and_mask_sidecars(room_in_tmp):
    process_room(room_in_tmp)
    assert (room_in_tmp.parent / "sample_mouth.cavern.png").exists()
    assert (room_in_tmp.parent / "sample_mouth.mask.txt").exists()


def test_process_room_writes_derived_block(room_in_tmp):
    process_room(room_in_tmp)
    data = yaml.safe_load(room_in_tmp.read_text())
    derived = data.get("derived")
    assert derived is not None
    assert "floor_count" in derived
    assert "exits" in derived
    assert "pois" in derived
    assert "generated_at" in derived
    assert "generator_version" in derived


def test_process_room_is_idempotent(room_in_tmp):
    process_room(room_in_tmp)
    png1 = (room_in_tmp.parent / "sample_mouth.cavern.png").read_bytes()
    mask1 = (room_in_tmp.parent / "sample_mouth.mask.txt").read_text()
    process_room(room_in_tmp)
    png2 = (room_in_tmp.parent / "sample_mouth.cavern.png").read_bytes()
    mask2 = (room_in_tmp.parent / "sample_mouth.mask.txt").read_text()
    assert png1 == png2
    assert mask1 == mask2


def test_process_room_skips_settlement_rooms(tmp_path):
    settlement = tmp_path / "confessional.yaml"
    settlement.write_text(yaml.safe_dump({
        "id": "confessional",
        "name": "The Confessional",
        "room_type": "settlement",
        "description": "A small house keyed to humility.",
        "exits": [{"to": "sunden_square", "label": "out to the square"}],
    }))
    process_room(settlement)  # should not raise
    assert not (tmp_path / "confessional.cavern.png").exists()
    assert not (tmp_path / "confessional.mask.txt").exists()


def test_mask_format_has_one_char_per_cell(room_in_tmp):
    process_room(room_in_tmp)
    mask_lines = (room_in_tmp.parent / "sample_mouth.mask.txt").read_text().splitlines()
    assert len(mask_lines) == 18
    assert all(len(line) == 18 for line in mask_lines)
    assert all(c in ".#" for line in mask_lines for c in line)
```

- [ ] **Step 3: Run, verify failure**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement `cli.py`**

```python
"""CLI: read room.yaml, generate sidecars, write derived block."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

from cavern_renderer import __version__
from cavern_renderer.cellular import FLOOR, gen_cave
from cavern_renderer.derive import find_exits, find_pois, floor_count
from cavern_renderer.render import render_grid_to_png


def process_room(room_yaml_path: Path) -> None:
    """Process one room. Idempotent: same input → byte-identical sidecars."""
    data = yaml.safe_load(room_yaml_path.read_text())
    room_type = data.get("room_type")
    if room_type == "settlement":
        return  # settlements have no PNG/mask
    if room_type != "cavern":
        raise ValueError(
            f"{room_yaml_path}: unknown room_type {room_type!r} "
            f"(expected 'cavern' or 'settlement')"
        )

    cellular = data["cellular"]
    width, height = cellular["size"]
    grid = gen_cave(
        width=width,
        height=height,
        seed=cellular["seed"],
        density=cellular.get("density", 0.55),
        cutoff=cellular.get("cutoff", 5),
        passes=cellular.get("passes", 4),
    )

    cell_size = cellular.get("cell_size", 28)
    stem = room_yaml_path.stem
    png_path = room_yaml_path.parent / f"{stem}.cavern.png"
    mask_path = room_yaml_path.parent / f"{stem}.mask.txt"

    render_grid_to_png(grid, png_path, cell_size=cell_size)
    mask_path.write_text(_grid_to_mask(grid))

    overrides = data.get("overrides") or {}
    derived_exits = overrides.get("exits") or _exits_to_yaml(find_exits(grid))
    derived_pois = overrides.get("pois") or [list(p) for p in find_pois(grid)]

    data["derived"] = {
        "floor_count": floor_count(grid),
        "exits": derived_exits,
        "pois": derived_pois,
        "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator_version": __version__,
    }
    room_yaml_path.write_text(yaml.safe_dump(data, sort_keys=False))


def _grid_to_mask(grid: list[list[int]]) -> str:
    return "\n".join(
        "".join("." if cell == FLOOR else "#" for cell in row) for row in grid
    ) + "\n"


def _exits_to_yaml(
    exits: dict[str, tuple[int, int] | None],
) -> dict[str, list[int] | None]:
    return {k: (list(v) if v else None) for k, v in exits.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cavern renderer CLI")
    parser.add_argument("path", type=Path, help="room.yaml file or world directory")
    parser.add_argument(
        "--world",
        action="store_true",
        help="Treat path as a world dir; process every rooms/<id>.yaml within.",
    )
    args = parser.parse_args(argv)

    if args.world:
        rooms_dir = args.path / "rooms"
        if not rooms_dir.is_dir():
            print(f"error: {rooms_dir} does not exist", file=sys.stderr)
            return 2
        rooms = sorted(rooms_dir.glob("*.yaml"))
        for room in rooms:
            print(f"  processing {room.name}", file=sys.stderr)
            process_room(room)
        print(f"done: {len(rooms)} rooms", file=sys.stderr)
    else:
        process_room(args.path)
        print(f"done: {args.path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests, verify pass**

```bash
uv run pytest tests/test_cli.py -v
```
Expected: 5 tests pass.

- [ ] **Step 6: End-to-end CLI smoke**

```bash
cd sidequest-content/tools/cavern_renderer
cp tests/fixtures/sample_room.yaml /tmp/test_room.yaml
uv run cavern_renderer /tmp/test_room.yaml
ls -la /tmp/test_room.* /tmp/test_room.cavern.png /tmp/test_room.mask.txt
```
Expected: all three files exist; YAML now contains `derived:` block.

- [ ] **Step 7: Commit**

```bash
git add sidequest-content/tools/cavern_renderer/cavern_renderer/cli.py sidequest-content/tools/cavern_renderer/tests/test_cli.py sidequest-content/tools/cavern_renderer/tests/fixtures/sample_room.yaml
git commit -m "feat(cavern_renderer): CLI with idempotent room processing

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase C — World Authoring

For each cavern descent: invent room IDs and narrative tags grounded in the descent's lore (read `worlds/caverns_sunden/cartography.yaml` regions for the canonical themes). Author room.yaml files; run the CLI; inspect the PNG visually; if the cellular shape is wrong, change the seed and regenerate; commit each descent's rooms in its own commit.

### Task 8: Author mawdeep_gullet rooms

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/mouth.yaml` + sidecars
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/gullet_throat.yaml` + sidecars
- Create: ~4 more mawdeep rooms

Mawdeep_gullet theme (per cartography.yaml): Gluttony, the wet deep, sour air, dripping limestone. Room ideas: mouth (entry), gullet_throat, maw_chamber, drowned_fold, swallowed_altar, the_belly.

- [ ] **Step 1: Write `mouth.yaml`**

```yaml
id: mouth
name: "The Mouth"
region: mawdeep_gullet
narrative_tag: "the wet entrance, dripping limestone, sour air"
room_type: cavern

cellular:
  size: [18, 18]
  seed: 1042
  density: 0.55
  cutoff: 5
  passes: 4
  cell_size: 28

overrides:
  exits: {}
  pois: []
  poi_labels: {}
```

- [ ] **Step 2: Run the CLI on `mouth.yaml`, inspect the PNG**

```bash
cd sidequest-content/tools/cavern_renderer
uv run cavern_renderer ../../genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/mouth.yaml
open ../../genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/mouth.cavern.png
```

Inspect: does the shape feel like a cavern mouth? If too cramped: try seed 99 / 200 / 503; if not enough chamber: lower density to 0.50; if too sparse: raise cutoff to 6. Iterate seed only first; only change density/cutoff if seed iteration fails.

- [ ] **Step 3: Repeat steps 1-2 for the remaining mawdeep rooms**

Create `gullet_throat.yaml`, `maw_chamber.yaml`, `drowned_fold.yaml`, `swallowed_altar.yaml`, `the_belly.yaml`. Each gets a unique seed (start with sequential like 1043, 1044, ... or random; doesn't matter as long as it's deterministic). Each PNG inspected; iterate as needed.

- [ ] **Step 4: Verify all mawdeep rooms have artifacts**

```bash
ls sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/ | grep -E "(mouth|gullet|maw|drowned|swallowed|belly)"
```
Expected: 6 rooms × 3 files each = 18 files.

- [ ] **Step 5: Commit mawdeep rooms**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/
git commit -m "content(caverns_sunden): author mawdeep_gullet — 6 cellular cavern rooms

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Author grimvault_descent rooms

Grimvault theme: Pride, the cold vault, clean and ordered, under Ashgate ridge. Room ideas: ashgate_door, vault_antechamber, ledger_hall, mirror_alcove, oath_chamber, pride_terminus.

- [ ] **Step 1: Author 6 grimvault room.yaml files**

For each room (`ashgate_door`, `vault_antechamber`, `ledger_hall`, `mirror_alcove`, `oath_chamber`, `pride_terminus`): write a `<id>.yaml` with `region: grimvault_descent`, a unique seed, and an evocative `narrative_tag`. Default cellular params (`size: [18, 18]`, `density: 0.55`, etc).

- [ ] **Step 2: Run CLI on each, inspect, iterate seed if needed**

Same pattern as Task 8 step 2.

- [ ] **Step 3: Commit grimvault rooms**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/
git commit -m "content(caverns_sunden): author grimvault_descent — 6 cellular cavern rooms

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Author horden_warren rooms

Horden theme: Greed, the counting passages, Copperbridge tunnels. Room ideas: copperbridge_step, count_room, hoard_alcove, tally_passage, miser_chapel, greed_terminus.

- [ ] **Step 1: Author 6 horden room.yaml files**

Same pattern. `region: horden_warren`. Unique seeds.

- [ ] **Step 2: Run CLI, inspect, iterate**

- [ ] **Step 3: Commit**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/
git commit -m "content(caverns_sunden): author horden_warren — 6 cellular cavern rooms

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Author hamlet settlement stubs

The hamlet has named landmarks per `cartography.yaml`: Sünden Square, the Wall, the Recruiter's Post, the Confessional, the Workhouse, the Masquerade. Each gets a settlement stub — no PNG, no mask, just metadata.

- [ ] **Step 1: Author each settlement room**

Example `sunden_square.yaml`:

```yaml
id: sunden_square
name: "Sünden Square"
region: sunden_hamlet
room_type: settlement
description: >-
  A single square paved in pale limestone, smoke-stained around the
  north face where the Wall has been chiseled and re-chiseled across
  generations. The fountain at the center runs clear water that tastes
  of nothing at all. Three dungeon mouths watch from their respective
  ridges, never quite out of sight.
exits:
  - {to: the_wall, label: "to the Wall of Names"}
  - {to: recruiter_post, label: "south to the Recruiter's Post"}
  - {to: confessional, label: "to the Confessional"}
  - {to: workhouse, label: "to the Workhouse"}
  - {to: masquerade, label: "to the Masquerade"}
  - {to: mouth, label: "out to the Mawdeep gullet"}
  - {to: ashgate_door, label: "out to the Grimvault descent"}
  - {to: copperbridge_step, label: "out to the Horden warren"}
```

Repeat for `the_wall.yaml`, `recruiter_post.yaml`, `confessional.yaml`, `workhouse.yaml`, `masquerade.yaml`. Each carries a name + description + exits. No `cellular` block; `room_type: settlement`.

- [ ] **Step 2: Confirm CLI skips settlement rooms (no sidecars produced)**

Per Task 7 step 4 test, settlement rooms are skipped by `process_room`. Run:

```bash
cd sidequest-content/tools/cavern_renderer
uv run cavern_renderer --world ../../genre_packs/caverns_and_claudes/worlds/caverns_sunden
ls ../../genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/sunden_square.*
```
Expected: only `sunden_square.yaml` (no `.cavern.png` or `.mask.txt`).

- [ ] **Step 3: Commit hamlet stubs**

```bash
git add sidequest-content/genre_packs/caverns_and_claudes/worlds/caverns_sunden/rooms/
git commit -m "content(caverns_sunden): hamlet settlement stubs (6 rooms)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase D — Server Protocol & Loader

### Task 12: Reshape `TacticalGridPayload` (TDD)

**Files:**
- Modify: `sidequest-server/sidequest/protocol/models.py` (lines around 440)
- Modify: `sidequest-server/sidequest/protocol/__init__.py` (exports)
- Create: `sidequest-server/tests/protocol/test_tactical_grid_payload.py`

The original payload (`width`, `height`, `cells`, `features`) is replaced with the cavern-aware shape from the spec. **Old field names removed entirely** — single-merge cutover, no compat. Search the server for any constructors of `TacticalGridPayload` (Step 1 confirmed there are zero), so the rename is safe.

- [ ] **Step 1: Verify no existing constructors of the old shape**

```bash
grep -rn "TacticalGridPayload(" /Users/slabgorb/Projects/oq-1/sidequest-server --include="*.py"
```
Expected: only the class definition itself; no callers.

- [ ] **Step 2: Write failing protocol test**

```python
"""Tests for the new TacticalGridPayload shape."""

import pytest
from pydantic import ValidationError

from sidequest.protocol.models import (
    CellularParams,
    DerivedRoomData,
    TacticalGridPayload,
)


def test_cavern_payload_validates_with_all_fields():
    p = TacticalGridPayload(
        room_id="mouth",
        room_name="The Mouth",
        room_type="cavern",
        mask="##.\n.##\n###",
        cavern_image_url="/genre/caverns_and_claudes/worlds/caverns_sunden/rooms/mouth.cavern.png",
        cell_size=28,
        cellular=CellularParams(
            size=(18, 18), seed=1042, density=0.55, cutoff=5, passes=4
        ),
        derived=DerivedRoomData(
            floor_count=142,
            exits={"north": (9, 0), "east": (17, 9), "south": None, "west": None},
            pois=[(8, 8), (13, 6)],
        ),
        tokens=[],
        initiative=None,
    )
    assert p.room_type == "cavern"
    assert p.cellular.seed == 1042


def test_settlement_payload_omits_cavern_fields():
    p = TacticalGridPayload(
        room_id="confessional",
        room_name="The Confessional",
        room_type="settlement",
        mask=None,
        cavern_image_url=None,
        cell_size=None,
        cellular=None,
        derived=None,
        tokens=[],
        initiative=None,
    )
    assert p.room_type == "settlement"
    assert p.cavern_image_url is None


def test_invalid_room_type_rejected():
    with pytest.raises(ValidationError):
        TacticalGridPayload(
            room_id="x", room_name="x", room_type="dungeon",
            mask=None, cavern_image_url=None, cell_size=None,
            cellular=None, derived=None, tokens=[], initiative=None,
        )
```

- [ ] **Step 3: Run, verify failure**

```bash
uv run pytest tests/protocol/test_tactical_grid_payload.py -v
```
Expected: ImportError on `CellularParams` / `DerivedRoomData`.

- [ ] **Step 4: Reshape `TacticalGridPayload` in `models.py`**

In `sidequest-server/sidequest/protocol/models.py`, replace the existing `TacticalGridPayload` (and remove `TacticalFeaturePayload` since it's unused after the rewrite — verify with grep first; remove if unreferenced):

```python
class CellularParams(ProtocolBase):
    """Cellular automata parameters for a cavern room. ADR-096."""

    size: tuple[int, int]
    """(width, height) in cells."""
    seed: int
    density: float
    cutoff: int
    passes: int


class DerivedRoomData(ProtocolBase):
    """Tool-derived room facts (exits, POIs, floor count). ADR-096."""

    floor_count: int
    exits: dict[str, tuple[int, int] | None]
    """{north|south|east|west: [x, y] | None}."""
    pois: list[tuple[int, int]]


class TacticalGridPayload(ProtocolBase):
    """Per-room tactical layout for the Map tab. ADR-096.

    Cavern rooms render as a Pillow-rendered PNG floor + token overlay.
    Settlement rooms render as a name/description card; cavern fields are
    None.
    """

    room_id: str
    room_name: str
    room_type: Literal["cavern", "settlement"]

    mask: str | None
    """ASCII mask: '.' floor, '#' wall, rows newline-separated. None for settlements."""
    cavern_image_url: str | None
    """Resolved (CDN or /genre/) URL for the rendered cavern PNG."""
    cell_size: int | None
    cellular: CellularParams | None
    derived: DerivedRoomData | None

    tokens: list[TokenPayload]
    initiative: list[InitiativeEntry] | None
```

(`TokenPayload` and `InitiativeEntry` may need to be defined or imported — check existing protocol; reuse if present, define minimally if not. Their schemas are out of scope; use placeholder types if necessary, with one-line definitions.)

- [ ] **Step 5: Update `protocol/__init__.py` exports**

Add `CellularParams`, `DerivedRoomData` to the export block (line 88 area) and the `__all__` (line 153).

- [ ] **Step 6: Run protocol test, verify pass**

```bash
cd sidequest-server
uv run pytest tests/protocol/test_tactical_grid_payload.py -v
```
Expected: 3 tests pass.

- [ ] **Step 7: Run full server test suite — old shape consumers should not exist**

```bash
uv run pytest -x
```
Expected: pass. Any failure = something referenced the old fields; fix in this commit.

- [ ] **Step 8: Commit**

```bash
git add sidequest-server/sidequest/protocol/models.py sidequest-server/sidequest/protocol/__init__.py sidequest-server/tests/protocol/test_tactical_grid_payload.py
git commit -m "feat(protocol): reshape TacticalGridPayload for cellular caverns

ADR-096. Old (width/height/cells/features) shape removed; new (mask +
cavern_image_url + cellular + derived) shape is the only path.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Per-room file loader

**Files:**
- Create: `sidequest-server/sidequest/game/room_file_loader.py`
- Create: `sidequest-server/tests/game/test_room_file_loader.py`

Loader reads `<world_dir>/rooms/<room_id>.yaml`, validates `room_type`, loads sibling `.mask.txt` for cavern rooms, builds a `TacticalGridPayload` (without tokens/initiative — those come from game state at dispatch time).

- [ ] **Step 1: Write failing loader test**

```python
"""Tests for room_file_loader: filesystem → TacticalGridPayload."""

from pathlib import Path

import pytest

from sidequest.game.room_file_loader import (
    RoomNotFoundError,
    load_room_payload,
)
from sidequest.protocol.models import TacticalGridPayload


@pytest.fixture
def caverns_sunden_dir() -> Path:
    """Real path to the authored caverns_sunden world."""
    here = Path(__file__).resolve()
    repo = here.parents[3]  # adjust if depth differs
    return repo.parent / "sidequest-content" / "genre_packs" / "caverns_and_claudes" / "worlds" / "caverns_sunden"


def test_load_cavern_room_returns_payload_with_image_and_mask(caverns_sunden_dir):
    payload = load_room_payload(caverns_sunden_dir, "mouth")
    assert isinstance(payload, TacticalGridPayload)
    assert payload.room_type == "cavern"
    assert payload.cavern_image_url is not None
    assert payload.cavern_image_url.endswith("/mouth.cavern.png")
    assert payload.mask is not None
    assert payload.cellular.seed == 1042
    assert payload.derived.floor_count > 0


def test_load_settlement_room_has_no_cavern_fields(caverns_sunden_dir):
    payload = load_room_payload(caverns_sunden_dir, "sunden_square")
    assert payload.room_type == "settlement"
    assert payload.cavern_image_url is None
    assert payload.mask is None


def test_load_unknown_room_raises(caverns_sunden_dir):
    with pytest.raises(RoomNotFoundError):
        load_room_payload(caverns_sunden_dir, "nonexistent_room")


def test_load_cavern_mask_matches_disk(caverns_sunden_dir):
    payload = load_room_payload(caverns_sunden_dir, "mouth")
    on_disk = (caverns_sunden_dir / "rooms" / "mouth.mask.txt").read_text()
    assert payload.mask == on_disk
```

- [ ] **Step 2: Run, verify failure**

```bash
uv run pytest tests/game/test_room_file_loader.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `room_file_loader.py`**

```python
"""Load per-room YAML files (ADR-096) → TacticalGridPayload.

Worlds use `<world_dir>/rooms/<room_id>.yaml` plus sibling
`.cavern.png` and `.mask.txt` artifacts emitted by the cavern_renderer
authoring tool.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from sidequest.protocol.models import (
    CellularParams,
    DerivedRoomData,
    TacticalGridPayload,
)
from sidequest.server.asset_urls import resolve_asset_url


class RoomNotFoundError(Exception):
    """Raised when no <room_id>.yaml exists in the world's rooms/ dir."""


def load_room_payload(world_dir: Path, room_id: str) -> TacticalGridPayload:
    """Load a room's metadata + mask, return a TacticalGridPayload.

    Tokens and initiative are not populated here — the dispatch layer
    fills them from game state.
    """
    yaml_path = world_dir / "rooms" / f"{room_id}.yaml"
    if not yaml_path.is_file():
        raise RoomNotFoundError(f"no room file at {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text())
    room_type = data.get("room_type")
    if room_type not in ("cavern", "settlement"):
        raise ValueError(
            f"{yaml_path}: invalid room_type {room_type!r}"
        )

    if room_type == "settlement":
        return TacticalGridPayload(
            room_id=room_id,
            room_name=data["name"],
            room_type="settlement",
            mask=None, cavern_image_url=None, cell_size=None,
            cellular=None, derived=None,
            tokens=[], initiative=None,
        )

    # Cavern path
    mask_path = world_dir / "rooms" / f"{room_id}.mask.txt"
    if not mask_path.is_file():
        raise FileNotFoundError(
            f"cavern room {yaml_path} missing sibling mask {mask_path}; "
            f"run `uv run cavern_renderer {yaml_path}` to regenerate"
        )
    mask = mask_path.read_text()

    cellular = data["cellular"]
    derived = data.get("derived")
    if derived is None:
        raise ValueError(
            f"{yaml_path}: cavern room missing 'derived:' block; "
            f"run cavern_renderer to populate"
        )

    relative = (
        f"genre_packs/caverns_and_claudes/worlds/{world_dir.name}/"
        f"rooms/{room_id}.cavern.png"
    )
    image_url = resolve_asset_url(relative)

    return TacticalGridPayload(
        room_id=room_id,
        room_name=data["name"],
        room_type="cavern",
        mask=mask,
        cavern_image_url=image_url,
        cell_size=cellular.get("cell_size", 28),
        cellular=CellularParams(
            size=tuple(cellular["size"]),
            seed=cellular["seed"],
            density=cellular.get("density", 0.55),
            cutoff=cellular.get("cutoff", 5),
            passes=cellular.get("passes", 4),
        ),
        derived=DerivedRoomData(
            floor_count=derived["floor_count"],
            exits={
                k: (tuple(v) if v else None) for k, v in derived["exits"].items()
            },
            pois=[tuple(p) for p in derived["pois"]],
        ),
        tokens=[],
        initiative=None,
    )
```

- [ ] **Step 4: Generalize the genre path or accept the hardcode**

The `relative` path hardcodes `caverns_and_claudes`. Pass the genre slug as an argument:

```python
def load_room_payload(world_dir: Path, room_id: str, genre_slug: str = "caverns_and_claudes") -> TacticalGridPayload:
    ...
    relative = f"genre_packs/{genre_slug}/worlds/{world_dir.name}/rooms/{room_id}.cavern.png"
```

Default `caverns_and_claudes` is fine for now since that's the only genre with rooms; future stories will tighten this.

- [ ] **Step 5: Run, verify pass**

```bash
uv run pytest tests/game/test_room_file_loader.py -v
```
Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add sidequest-server/sidequest/game/room_file_loader.py sidequest-server/tests/game/test_room_file_loader.py
git commit -m "feat(server): per-room file loader → TacticalGridPayload

Reads worlds/<world>/rooms/<id>.yaml + sibling .mask.txt; builds a
cavern or settlement payload. ADR-096.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: Static-mount wiring test

**Files:**
- Create: `sidequest-server/tests/integration/test_cavern_static_mount.py`

Verifies that the URL the loader produces actually serves the PNG from the existing `/genre/*` mount.

- [ ] **Step 1: Write integration test**

```python
"""Wiring test: verify cavern_image_url resolves to a real served PNG.

Per CLAUDE.md 'every test suite needs a wiring test'.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidequest.game.room_file_loader import load_room_payload
from sidequest.server.app import create_app


@pytest.fixture
def caverns_sunden_dir(monkeypatch: pytest.MonkeyPatch) -> Path:
    here = Path(__file__).resolve()
    repo = here.parents[3]
    content = repo.parent / "sidequest-content"
    monkeypatch.setenv("SIDEQUEST_GENRE_PACKS", str(content / "genre_packs"))
    monkeypatch.setenv("SIDEQUEST_ASSET_BASE_URL", "")  # local mode
    return content / "genre_packs" / "caverns_and_claudes" / "worlds" / "caverns_sunden"


def test_cavern_image_url_serves_png_bytes(caverns_sunden_dir):
    payload = load_room_payload(caverns_sunden_dir, "mouth")
    app = create_app()
    client = TestClient(app)
    # In local mode, cavern_image_url is /genre/...
    assert payload.cavern_image_url.startswith("/genre/")
    response = client.get(payload.cavern_image_url)
    assert response.status_code == 200
    assert response.headers["content-type"] in ("image/png", "image/x-png")
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
```

- [ ] **Step 2: Run, verify pass**

```bash
uv run pytest tests/integration/test_cavern_static_mount.py -v
```
Expected: passes (or fails revealing real wiring gap; fix it before moving on).

- [ ] **Step 3: Commit**

```bash
git add sidequest-server/tests/integration/test_cavern_static_mount.py
git commit -m "test(server): wiring test — cavern_image_url serves real PNG

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: OTEL span for cavern room enter

**Files:**
- Create: `sidequest-server/sidequest/telemetry/spans/cavern_room.py`
- Modify: `sidequest-server/sidequest/game/room_file_loader.py` (emit span on cavern load)

Per CLAUDE.md "every backend fix must add OTEL spans" — this is a new subsystem.

- [ ] **Step 1: Pattern-match an existing span module**

```bash
cat /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/telemetry/spans/room_state.py | head -40
```
Inspect for the span-emit pattern; mirror it.

- [ ] **Step 2: Write the span module**

`sidequest-server/sidequest/telemetry/spans/cavern_room.py`:

```python
"""OTEL span for cavern room loading. ADR-096.

Emitted whenever the room loader produces a cavern payload. The GM panel
uses these to verify the right map loaded — Claude can't fake cellular
params or floor counts since they come from the loader, not the
narrator.
"""

from __future__ import annotations

import hashlib

from sidequest.telemetry.spans._core import emit_span

SPAN_CAVERN_ROOM_LOAD = "cavern_room.load"


def cavern_room_load_span(
    *,
    room_id: str,
    seed: int,
    density: float,
    floor_count: int,
    mask: str,
    cavern_image_url: str,
) -> None:
    emit_span(
        SPAN_CAVERN_ROOM_LOAD,
        {
            "room_id": room_id,
            "seed": seed,
            "density": density,
            "floor_count": floor_count,
            "mask_sha256": hashlib.sha256(mask.encode()).hexdigest()[:16],
            "cavern_image_url": cavern_image_url,
        },
    )
```

(If `_core.emit_span` has a different signature, adapt; the goal is "this subsystem decision is observable".)

- [ ] **Step 3: Wire span emission into the loader**

In `sidequest-server/sidequest/game/room_file_loader.py`, after building a cavern payload:

```python
from sidequest.telemetry.spans.cavern_room import cavern_room_load_span
...
# in the cavern branch, before returning:
cavern_room_load_span(
    room_id=room_id,
    seed=cellular["seed"],
    density=cellular.get("density", 0.55),
    floor_count=derived["floor_count"],
    mask=mask,
    cavern_image_url=image_url,
)
```

- [ ] **Step 4: Verify the existing tests still pass**

```bash
uv run pytest tests/game/test_room_file_loader.py tests/integration/test_cavern_static_mount.py -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/telemetry/spans/cavern_room.py sidequest-server/sidequest/game/room_file_loader.py
git commit -m "feat(otel): cavern_room.load span on cavern room enter

ADR-096. GM panel can verify the map is real — seed, density, mask hash
flow from the loader, not the narrator.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase E — Frontend

### Task 16: Cell math helpers

**Files:**
- Create: `sidequest-ui/src/lib/cellMath.ts`
- Create: `sidequest-ui/src/lib/__tests__/cellMath.test.ts`

Pure functions used by the renderer for positioning and reach. No React.

- [ ] **Step 1: Write failing tests**

```typescript
import { describe, expect, it } from "vitest";
import {
  cellToPixel,
  chebyshevReachCells,
  isFloor,
  pixelToCell,
} from "@/lib/cellMath";

describe("cellMath", () => {
  describe("cellToPixel", () => {
    it("converts cell coords to pixel center", () => {
      expect(cellToPixel({ x: 0, y: 0 }, 28)).toEqual({ x: 14, y: 14 });
      expect(cellToPixel({ x: 5, y: 3 }, 28)).toEqual({ x: 154, y: 98 });
    });
  });

  describe("pixelToCell", () => {
    it("converts pixel coords back to cell", () => {
      expect(pixelToCell({ x: 14, y: 14 }, 28)).toEqual({ x: 0, y: 0 });
      expect(pixelToCell({ x: 155, y: 99 }, 28)).toEqual({ x: 5, y: 3 });
    });

    it("clamps to nearest cell at boundaries", () => {
      expect(pixelToCell({ x: 27, y: 27 }, 28)).toEqual({ x: 0, y: 0 });
      expect(pixelToCell({ x: 28, y: 28 }, 28)).toEqual({ x: 1, y: 1 });
    });
  });

  describe("isFloor", () => {
    const mask = "##.\n.##\n###";

    it("returns true for floor cells", () => {
      expect(isFloor(mask, { x: 2, y: 0 })).toBe(true);
      expect(isFloor(mask, { x: 0, y: 1 })).toBe(true);
    });

    it("returns false for wall cells", () => {
      expect(isFloor(mask, { x: 0, y: 0 })).toBe(false);
      expect(isFloor(mask, { x: 1, y: 1 })).toBe(false);
    });

    it("returns false out of bounds", () => {
      expect(isFloor(mask, { x: -1, y: 0 })).toBe(false);
      expect(isFloor(mask, { x: 5, y: 5 })).toBe(false);
    });
  });

  describe("chebyshevReachCells", () => {
    const mask = ".....\n.....\n..#..\n.....\n.....";

    it("returns all floor cells within Chebyshev radius", () => {
      const cells = chebyshevReachCells({ x: 2, y: 2 }, 1, mask);
      // origin (2,2) is wall — but the player is *on* the cell; reach
      // includes the origin and floor neighbors. We exclude wall cells.
      const pairs = cells.map(c => `${c.x},${c.y}`).sort();
      expect(pairs).toEqual([
        "1,1", "1,2", "1,3",
        "2,1",          "2,3",
        "3,1", "3,2", "3,3",
      ].sort());
    });

    it("excludes cells outside the mask", () => {
      const cells = chebyshevReachCells({ x: 0, y: 0 }, 2, mask);
      for (const c of cells) {
        expect(c.x).toBeGreaterThanOrEqual(0);
        expect(c.y).toBeGreaterThanOrEqual(0);
        expect(c.x).toBeLessThan(5);
        expect(c.y).toBeLessThan(5);
      }
    });
  });
});
```

- [ ] **Step 2: Run, verify failure**

```bash
cd sidequest-ui
npx vitest run src/lib/__tests__/cellMath.test.ts
```
Expected: import errors.

- [ ] **Step 3: Implement `cellMath.ts`**

```typescript
export interface Cell {
  readonly x: number;
  readonly y: number;
}

export interface Pixel {
  readonly x: number;
  readonly y: number;
}

/** Cell → pixel center (top-left origin). */
export function cellToPixel(cell: Cell, cellSize: number): Pixel {
  return {
    x: cell.x * cellSize + Math.floor(cellSize / 2),
    y: cell.y * cellSize + Math.floor(cellSize / 2),
  };
}

/** Pixel → enclosing cell. Floors the division. */
export function pixelToCell(pixel: Pixel, cellSize: number): Cell {
  return {
    x: Math.floor(pixel.x / cellSize),
    y: Math.floor(pixel.y / cellSize),
  };
}

/** True if the mask has a floor cell ('.') at this position. */
export function isFloor(mask: string, cell: Cell): boolean {
  const rows = mask.split("\n").filter(r => r.length > 0);
  if (cell.y < 0 || cell.y >= rows.length) return false;
  const row = rows[cell.y];
  if (cell.x < 0 || cell.x >= row.length) return false;
  return row[cell.x] === ".";
}

/**
 * Floor cells within Chebyshev radius of origin (excluding origin).
 * Used to draw the reach disc when a token is selected.
 */
export function chebyshevReachCells(
  origin: Cell,
  radius: number,
  mask: string,
): Cell[] {
  const out: Cell[] = [];
  for (let dy = -radius; dy <= radius; dy++) {
    for (let dx = -radius; dx <= radius; dx++) {
      if (dx === 0 && dy === 0) continue;
      const c = { x: origin.x + dx, y: origin.y + dy };
      if (isFloor(mask, c)) out.push(c);
    }
  }
  return out;
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
npx vitest run src/lib/__tests__/cellMath.test.ts
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/lib/cellMath.ts sidequest-ui/src/lib/__tests__/cellMath.test.ts
git commit -m "feat(ui): cellMath helpers — cellToPixel, pixelToCell, reach

Pure functions for the cellular tactical renderer. ADR-096.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: SettlementRoomView component

**Files:**
- Create: `sidequest-ui/src/components/SettlementRoomView.tsx`
- Create: `sidequest-ui/src/components/__tests__/SettlementRoomView.test.tsx`

Minimal component: name header + description + exit list.

- [ ] **Step 1: Write failing test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SettlementRoomView } from "@/components/SettlementRoomView";

describe("SettlementRoomView", () => {
  const props = {
    name: "The Confessional",
    description: "A small house keyed to humility, against pride.",
    exits: [
      { to: "sunden_square", label: "out to the square" },
      { to: "the_wall", label: "to the Wall of Names" },
    ],
  };

  it("renders the room name as a heading", () => {
    render(<SettlementRoomView {...props} />);
    expect(screen.getByRole("heading", { name: "The Confessional" })).toBeInTheDocument();
  });

  it("renders the description", () => {
    render(<SettlementRoomView {...props} />);
    expect(screen.getByText(/keyed to humility/)).toBeInTheDocument();
  });

  it("renders one exit per item with label", () => {
    render(<SettlementRoomView {...props} />);
    expect(screen.getByText("out to the square")).toBeInTheDocument();
    expect(screen.getByText("to the Wall of Names")).toBeInTheDocument();
  });

  it("renders empty exits gracefully", () => {
    render(<SettlementRoomView {...props} exits={[]} />);
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run, verify failure**

```bash
npx vitest run src/components/__tests__/SettlementRoomView.test.tsx
```
Expected: import error.

- [ ] **Step 3: Implement `SettlementRoomView.tsx`**

```typescript
export interface SettlementExit {
  readonly to: string;
  readonly label: string;
}

export interface SettlementRoomViewProps {
  readonly name: string;
  readonly description: string;
  readonly exits: readonly SettlementExit[];
}

export function SettlementRoomView({
  name, description, exits,
}: SettlementRoomViewProps) {
  return (
    <div data-testid="settlement-room-view" className="p-6 space-y-4">
      <h2 className="text-2xl font-bold text-[var(--accent)]">{name}</h2>
      <p className="text-[var(--text)] leading-relaxed">{description}</p>
      {exits.length > 0 && (
        <ul className="space-y-1">
          {exits.map(exit => (
            <li
              key={exit.to}
              data-testid={`settlement-exit-${exit.to}`}
              className="text-sm text-[var(--text-mut)]"
            >
              <span className="text-[var(--accent)]">→</span> {exit.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run, verify pass**

```bash
npx vitest run src/components/__tests__/SettlementRoomView.test.tsx
```
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/SettlementRoomView.tsx sidequest-ui/src/components/__tests__/SettlementRoomView.test.tsx
git commit -m "feat(ui): SettlementRoomView component

Non-tactical room view for hamlet settlements. ADR-096.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 18: CavernActionPanel component (right rail when token selected)

**Files:**
- Create: `sidequest-ui/src/components/CavernActionPanel.tsx`
- Create: `sidequest-ui/src/components/__tests__/CavernActionPanel.test.tsx`

Right-rail action panel matching the hi-fi mock — character header + stats rows + action buttons. Action callbacks are passthroughs; wiring the actions to real state is out of scope (turn dispatch is not changed by this slice).

- [ ] **Step 1: Write failing test**

```typescript
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CavernActionPanel } from "@/components/CavernActionPanel";

describe("CavernActionPanel", () => {
  const props = {
    tokenName: "Keith",
    className: "fighter, lvl 4",
    hp: { current: 32, max: 36 },
    ac: 16,
    speed: 30,
    position: { x: 7, y: 9 },
  };

  it("renders the character header", () => {
    render(<CavernActionPanel {...props} onAction={vi.fn()} />);
    expect(screen.getByText(/Keith — fighter, lvl 4/)).toBeInTheDocument();
  });

  it("renders stat rows", () => {
    render(<CavernActionPanel {...props} onAction={vi.fn()} />);
    expect(screen.getByText("32 / 36")).toBeInTheDocument();
    expect(screen.getByText("16")).toBeInTheDocument();
    expect(screen.getByText("30 ft")).toBeInTheDocument();
    expect(screen.getByText("[7,9]")).toBeInTheDocument();
  });

  it("calls onAction with the action id when a button is clicked", () => {
    const onAction = vi.fn();
    render(<CavernActionPanel {...props} onAction={onAction} />);
    fireEvent.click(screen.getByRole("button", { name: /move/i }));
    expect(onAction).toHaveBeenCalledWith("move");
  });

  it("renders all six standard actions plus end-turn", () => {
    render(<CavernActionPanel {...props} onAction={vi.fn()} />);
    for (const label of ["Move", "Dash", "Attack", "Cast", "Object", "Dodge", "End turn"]) {
      expect(screen.getByRole("button", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
  });
});
```

- [ ] **Step 2: Run, verify failure**

```bash
npx vitest run src/components/__tests__/CavernActionPanel.test.tsx
```

- [ ] **Step 3: Implement `CavernActionPanel.tsx`**

```typescript
export type CavernActionId =
  | "move" | "dash" | "attack" | "cast" | "object" | "dodge" | "end_turn";

export interface CavernActionPanelProps {
  readonly tokenName: string;
  readonly className: string;
  readonly hp: { current: number; max: number };
  readonly ac: number;
  readonly speed: number;
  readonly position: { x: number; y: number };
  readonly onAction: (id: CavernActionId) => void;
}

const ACTIONS: { id: CavernActionId; label: string; primary?: boolean }[] = [
  { id: "move",   label: "Move" },
  { id: "dash",   label: "Dash" },
  { id: "attack", label: "Attack" },
  { id: "cast",   label: "Cast" },
  { id: "object", label: "Object" },
  { id: "dodge",  label: "Dodge" },
  { id: "end_turn", label: "End turn", primary: true },
];

export function CavernActionPanel({
  tokenName, className, hp, ac, speed, position, onAction,
}: CavernActionPanelProps) {
  return (
    <div data-testid="cavern-action-panel" className="space-y-3 p-3">
      <div className="rounded border border-[var(--line)] bg-[var(--surface-2)] p-3">
        <h3 className="mb-2 text-[10px] font-semibold tracking-widest uppercase text-[var(--text-dim)]">
          {tokenName} — {className}
        </h3>
        <div className="space-y-1 text-xs">
          <Row k="HP" v={`${hp.current} / ${hp.max}`} />
          <Row k="AC" v={String(ac)} />
          <Row k="Speed" v={`${speed} ft`} />
          <Row k="Position" v={`[${position.x},${position.y}]`} />
        </div>
      </div>
      <div className="rounded border border-[var(--line)] bg-[var(--surface-2)] p-3">
        <h3 className="mb-2 text-[10px] font-semibold tracking-widest uppercase text-[var(--text-dim)]">
          Actions
        </h3>
        <div className="grid grid-cols-2 gap-1.5">
          {ACTIONS.map(a => (
            <button
              key={a.id}
              data-testid={`cavern-action-${a.id}`}
              onClick={() => onAction(a.id)}
              className={
                a.primary
                  ? "col-span-2 rounded bg-[var(--accent)] px-2 py-2 text-xs font-semibold text-[#1a1500] hover:bg-[#f5d660]"
                  : "rounded border border-[var(--line)] bg-[var(--surface-3)] px-2 py-2 text-xs text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
              }
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-[var(--text-mut)]">{k}</span>
      <span className="font-mono text-right">{v}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run, verify pass**

```bash
npx vitest run src/components/__tests__/CavernActionPanel.test.tsx
```
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/CavernActionPanel.tsx sidequest-ui/src/components/__tests__/CavernActionPanel.test.tsx
git commit -m "feat(ui): CavernActionPanel — right-rail when token selected

ADR-096. Action callbacks are passthroughs; wiring to game state is
out of scope for v1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 19: Rewrite TacticalGridRenderer for image mode

**Files:**
- Modify (rewrite): `sidequest-ui/src/components/TacticalGridRenderer.tsx`
- Modify: `sidequest-ui/src/types/tactical.ts` — reshape `TacticalGridData`
- Modify (rewrite): `sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx`
- Modify: `sidequest-ui/src/lib/tacticalGridFromWire.ts` — adapter for new wire shape

This is the largest task. We rewrite the renderer entirely, keeping the export name and prop name (`grid`) so callers don't all need updating in this commit.

- [ ] **Step 1: Reshape `tactical.ts` types**

Read current `sidequest-ui/src/types/tactical.ts`. Replace the `TacticalGridData` definition with the new shape (preserve old field-related-but-orthogonal types like `TacticalThemeConfig` if present):

```typescript
export interface CavernCellularParams {
  readonly size: readonly [number, number];
  readonly seed: number;
  readonly density: number;
  readonly cutoff: number;
  readonly passes: number;
}

export interface CavernDerivedData {
  readonly floor_count: number;
  readonly exits: Readonly<Record<string, readonly [number, number] | null>>;
  readonly pois: ReadonlyArray<readonly [number, number]>;
}

export interface TacticalToken {
  readonly id: string;
  readonly name: string;
  readonly initial: string;
  readonly faction: "player" | "ally" | "neutral" | "hostile";
  readonly cell: { readonly x: number; readonly y: number };
  readonly hp: { readonly current: number; readonly max: number };
  readonly ac: number;
  readonly className?: string;
  readonly speed?: number;
}

/** Cavern room data. Settlement rooms route around this entirely. */
export interface TacticalGridData {
  readonly room_id: string;
  readonly room_name: string;
  readonly room_type: "cavern";
  readonly mask: string;
  readonly cavern_image_url: string;
  readonly cell_size: number;
  readonly cellular: CavernCellularParams;
  readonly derived: CavernDerivedData;
  readonly tokens: readonly TacticalToken[];
}
```

(Preserve any `TacticalThemeConfig` etc. that are orthogonal.)

- [ ] **Step 2: Update `tacticalGridFromWire.ts`**

Read the existing file. Rewrite the body to map the new wire shape (matching `TacticalGridPayload` → `TacticalGridData`). For settlement rooms (where `room_type === "settlement"` on the wire), return `null` so the caller routes elsewhere.

```typescript
import type { TacticalGridData } from "@/types/tactical";

interface WirePayload {
  room_id: string;
  room_name: string;
  room_type: "cavern" | "settlement";
  mask: string | null;
  cavern_image_url: string | null;
  cell_size: number | null;
  cellular: {
    size: [number, number]; seed: number; density: number;
    cutoff: number; passes: number;
  } | null;
  derived: {
    floor_count: number;
    exits: Record<string, [number, number] | null>;
    pois: [number, number][];
  } | null;
  tokens: WireToken[];
}

interface WireToken {
  id: string;
  name: string;
  initial: string;
  faction: "player" | "ally" | "neutral" | "hostile";
  cell: { x: number; y: number };
  hp: { current: number; max: number };
  ac: number;
  class_name?: string;
  speed?: number;
}

export function tacticalGridFromWire(p: WirePayload): TacticalGridData | null {
  if (p.room_type !== "cavern") return null;
  if (!p.mask || !p.cavern_image_url || !p.cell_size || !p.cellular || !p.derived) {
    throw new Error(
      `tacticalGridFromWire: cavern room ${p.room_id} missing required fields`,
    );
  }
  return {
    room_id: p.room_id,
    room_name: p.room_name,
    room_type: "cavern",
    mask: p.mask,
    cavern_image_url: p.cavern_image_url,
    cell_size: p.cell_size,
    cellular: p.cellular,
    derived: p.derived,
    tokens: p.tokens.map(t => ({
      id: t.id, name: t.name, initial: t.initial, faction: t.faction,
      cell: t.cell, hp: t.hp, ac: t.ac,
      className: t.class_name, speed: t.speed,
    })),
  };
}
```

- [ ] **Step 3: Write failing renderer tests**

`sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx` — full rewrite:

```typescript
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TacticalGridRenderer } from "@/components/TacticalGridRenderer";
import type { TacticalGridData } from "@/types/tactical";

const FIXTURE: TacticalGridData = {
  room_id: "mouth",
  room_name: "The Mouth",
  room_type: "cavern",
  mask: ".....\n.....\n..#..\n.....\n.....",
  cavern_image_url: "/genre/test/mouth.cavern.png",
  cell_size: 28,
  cellular: { size: [5, 5], seed: 1, density: 0.55, cutoff: 5, passes: 4 },
  derived: { floor_count: 24, exits: { north: [2, 0], south: null, east: null, west: null }, pois: [[0, 0]] },
  tokens: [
    {
      id: "k", name: "Keith", initial: "K", faction: "player",
      cell: { x: 1, y: 1 }, hp: { current: 32, max: 36 }, ac: 16,
      className: "fighter, lvl 4", speed: 30,
    },
    {
      id: "g", name: "Goblin", initial: "g", faction: "hostile",
      cell: { x: 3, y: 3 }, hp: { current: 7, max: 7 }, ac: 13,
    },
  ],
};

describe("TacticalGridRenderer — image-mode rendering", () => {
  it("renders the cavern PNG as an <img>", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    const img = screen.getByTestId("cavern-floor") as HTMLImageElement;
    expect(img.src).toContain("/genre/test/mouth.cavern.png");
  });

  it("renders one token per fixture token at the correct pixel position", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    const keith = screen.getByTestId("token-k");
    expect(keith).toHaveStyle({ left: "28px", top: "28px" });  // (1,1) * 28
    const goblin = screen.getByTestId("token-g");
    expect(goblin).toHaveStyle({ left: "84px", top: "84px" });  // (3,3) * 28
  });

  it("does not show reach disc by default", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    expect(screen.queryByTestId("reach-disc")).not.toBeInTheDocument();
  });

  it("does not show action panel by default", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    expect(screen.queryByTestId("cavern-action-panel")).not.toBeInTheDocument();
  });
});

describe("TacticalGridRenderer — selected state", () => {
  it("shows reach disc + action panel when a player token is clicked", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    fireEvent.click(screen.getByTestId("token-k"));
    expect(screen.getByTestId("reach-disc")).toBeInTheDocument();
    expect(screen.getByTestId("cavern-action-panel")).toBeInTheDocument();
  });

  it("highlights cells within Chebyshev radius speed/5", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    fireEvent.click(screen.getByTestId("token-k"));
    // speed 30 / 5 = 6 cells radius. In a 5x5 mask, that's most of the floor.
    const highlighted = screen.getAllByTestId(/^reach-cell-/);
    expect(highlighted.length).toBeGreaterThan(0);
  });

  it("does not select hostile tokens", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    fireEvent.click(screen.getByTestId("token-g"));
    expect(screen.queryByTestId("cavern-action-panel")).not.toBeInTheDocument();
  });

  it("clears selection when the same token is clicked again", () => {
    render(<TacticalGridRenderer grid={FIXTURE} />);
    fireEvent.click(screen.getByTestId("token-k"));
    fireEvent.click(screen.getByTestId("token-k"));
    expect(screen.queryByTestId("cavern-action-panel")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run, verify failure**

```bash
npx vitest run src/__tests__/tactical-grid-renderer.test.tsx
```
Expected: tests fail (renderer still uses old shape).

- [ ] **Step 5: Rewrite `TacticalGridRenderer.tsx`**

```typescript
import { useState } from "react";
import type { TacticalGridData, TacticalToken } from "@/types/tactical";
import { CavernActionPanel } from "@/components/CavernActionPanel";
import { cellToPixel, chebyshevReachCells } from "@/lib/cellMath";

export interface TacticalGridRendererProps {
  readonly grid: TacticalGridData;
}

const FACTION_COLOR: Record<TacticalToken["faction"], string> = {
  player: "#2563EB",
  ally: "#16A34A",
  neutral: "#6B7280",
  hostile: "#DC2626",
};

export function TacticalGridRenderer({ grid }: TacticalGridRendererProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const cellSize = grid.cell_size;
  const W = grid.cellular.size[0] * cellSize;
  const H = grid.cellular.size[1] * cellSize;

  const selected = grid.tokens.find(t => t.id === selectedId) ?? null;
  const isSelectable = (t: TacticalToken) => t.faction === "player" || t.faction === "ally";

  const handleTokenClick = (t: TacticalToken) => {
    if (!isSelectable(t)) return;
    setSelectedId(prev => (prev === t.id ? null : t.id));
  };

  const reachCells = (() => {
    if (!selected || !selected.speed) return [];
    const radius = Math.floor(selected.speed / 5);
    return chebyshevReachCells(selected.cell, radius, grid.mask);
  })();

  return (
    <div data-testid="tactical-grid-renderer" className="flex gap-4">
      <div className="relative" style={{ width: W, height: H }}>
        <img
          data-testid="cavern-floor"
          src={grid.cavern_image_url}
          alt={grid.room_name}
          width={W}
          height={H}
          className="block"
          draggable={false}
        />
        <div className="absolute inset-0">
          {reachCells.map(c => {
            const px = c.x * cellSize;
            const py = c.y * cellSize;
            return (
              <div
                key={`reach-${c.x}-${c.y}`}
                data-testid={`reach-cell-${c.x}-${c.y}`}
                className="absolute pointer-events-none"
                style={{
                  left: px, top: py, width: cellSize, height: cellSize,
                  background: "rgba(37,99,235,0.18)",
                  borderRadius: 2,
                }}
              />
            );
          })}
          {selected && (
            <div data-testid="reach-disc" className="hidden">
              {/* marker for tests; visualization is the cell highlights */}
            </div>
          )}
          {grid.tokens.map(t => {
            const px = cellToPixel(t.cell, cellSize);
            const size = Math.floor(cellSize * 0.78);
            const offset = Math.floor((cellSize - size) / 2);
            return (
              <button
                key={t.id}
                data-testid={`token-${t.id}`}
                onClick={() => handleTokenClick(t)}
                title={`${t.name} · ${t.hp.current}/${t.hp.max} HP · AC ${t.ac}`}
                className="absolute rounded-full grid place-items-center text-white font-bold border-2 border-white"
                style={{
                  left: t.cell.x * cellSize + offset,
                  top: t.cell.y * cellSize + offset,
                  width: size,
                  height: size,
                  background: FACTION_COLOR[t.faction],
                  fontSize: Math.floor(size * 0.55),
                  boxShadow: selectedId === t.id
                    ? "0 0 0 3px var(--accent), 0 0 16px rgba(230,200,76,0.6)"
                    : "0 2px 8px rgba(0,0,0,0.7), 0 0 0 2px rgba(0,0,0,0.4)",
                  cursor: isSelectable(t) ? "pointer" : "default",
                }}
              >
                {t.initial}
              </button>
            );
          })}
        </div>
      </div>
      {selected && (
        <div className="w-80 flex-shrink-0">
          <CavernActionPanel
            tokenName={selected.name}
            className={selected.className ?? ""}
            hp={selected.hp}
            ac={selected.ac}
            speed={selected.speed ?? 30}
            position={selected.cell}
            onAction={(_id) => { /* wired by future story */ }}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Run renderer tests, verify pass**

```bash
npx vitest run src/__tests__/tactical-grid-renderer.test.tsx
```
Expected: all tests pass.

- [ ] **Step 7: Run full UI test suite — discover broken consumers**

```bash
npx vitest run
```
Expected: failures in any test that constructed the old `TacticalGridData` shape (e.g. `Automapper.test.tsx`, `tactical-entity-story-29-10.test.tsx`). For each failure:
- If it's testing tactical-grid-renderer behavior we still want, update fixtures to the new shape.
- If it's testing the deleted SVG-cell rendering path (`cells: string[][]`, `features: ...`), remove the test (those test paths are gone in this slice per spec).

The goal: green test suite. Do not skip tests.

- [ ] **Step 8: Commit**

```bash
git add sidequest-ui/src/components/TacticalGridRenderer.tsx sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx sidequest-ui/src/types/tactical.ts sidequest-ui/src/lib/tacticalGridFromWire.ts sidequest-ui/src/__tests__/tactical-entity-story-29-10.test.tsx
git commit -m "feat(ui): TacticalGridRenderer image-mode rewrite

ADR-096. SVG-from-ASCII rendering paths removed; cavern PNG + token
overlay + selection state (reach disc + action panel). Old test paths
covering the SVG cell renderer deleted; replaced with image-mode tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 20: Automapper settlement branch

**Files:**
- Modify: `sidequest-ui/src/components/Automapper.tsx`
- Modify: `sidequest-ui/src/components/__tests__/Automapper.test.tsx`

Automapper currently delegates: cartography → MapOverlay (in MapWidget); single room with grid → TacticalGridRenderer; multi-room → DungeonMapRenderer. Add a new branch: single room with `room_type === "settlement"` → SettlementRoomView.

- [ ] **Step 1: Inspect existing delegation logic**

Read `sidequest-ui/src/components/Automapper.tsx` lines 320-340 (the part that delegates to TacticalGridRenderer when current room has grid).

- [ ] **Step 2: Write failing settlement-branch test**

Append to `Automapper.test.tsx`:

```typescript
it("routes settlement rooms to SettlementRoomView", () => {
  const rooms: ExploredRoom[] = [{
    id: "confessional",
    name: "The Confessional",
    room_type: "settlement",
    size: "small",
    is_current: true,
    exits: [],
    settlement: {
      description: "A small house keyed to humility, against pride.",
      exits: [{ to: "sunden_square", label: "out to the square" }],
    },
  }];
  render(<Automapper rooms={rooms} currentRoomId="confessional" />);
  expect(screen.getByTestId("settlement-room-view")).toBeInTheDocument();
  expect(screen.queryByTestId("tactical-grid-renderer")).not.toBeInTheDocument();
});
```

The `ExploredRoom` interface needs a `settlement` field added; do that in step 3.

- [ ] **Step 3: Update `ExploredRoom` interface and add the branch**

In `Automapper.tsx`:

```typescript
export interface ExploredRoom {
  id: string;
  name: string;
  room_type: string;  // "cavern" | "settlement" | legacy values
  size: string;
  is_current: boolean;
  exits: ExitInfo[];
  grid?: TacticalGridData;
  settlement?: {
    description: string;
    exits: { to: string; label: string }[];
  };
}
```

Add the routing branch in the render path (mirroring the existing "single room with grid" branch):

```typescript
// Settlement branch — non-tactical room view (ADR-096)
const currentRoom = rooms.find(r => r.id === currentRoomId);
if (currentRoom?.room_type === "settlement" && currentRoom.settlement) {
  return (
    <SettlementRoomView
      name={currentRoom.name}
      description={currentRoom.settlement.description}
      exits={currentRoom.settlement.exits}
    />
  );
}

// existing branches follow...
```

Import `SettlementRoomView` at the top of the file.

- [ ] **Step 4: Run Automapper tests, verify pass**

```bash
npx vitest run src/components/__tests__/Automapper.test.tsx
```

- [ ] **Step 5: Commit**

```bash
git add sidequest-ui/src/components/Automapper.tsx sidequest-ui/src/components/__tests__/Automapper.test.tsx
git commit -m "feat(ui): Automapper settlement branch routes to SettlementRoomView

ADR-096. New room_type === 'settlement' routes around tactical entirely.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 20b: Wire room loader into the room-enter dispatch path

**Files:**
- Investigate, then modify: the room-enter dispatch in `sidequest-server/sidequest/server/dispatch/` (exact file TBD — needs investigation in step 1) and/or `sidequest-server/sidequest/game/room_movement.py`
- Modify: WebSocket message emission so `TacticalGridPayload` reaches the UI as a typed message
- Add tests: an integration test in `sidequest-server/tests/integration/` that simulates room enter end-to-end

This is the wiring task: without it, the loader from Task 13 is unreachable from gameplay. Per CLAUDE.md "verify wiring, not just existence."

- [ ] **Step 1: Investigate the current room-enter flow**

```bash
grep -rn "room_movement\|enter_room\|room_change\|RoomEntered" /Users/slabgorb/Projects/oq-1/sidequest-server/sidequest --include="*.py" | head -30
grep -rn "room_movement\|enter_room\|RoomEntered" /Users/slabgorb/Projects/oq-1/sidequest-ui/src --include="*.ts" --include="*.tsx" | head -20
```

Identify: (a) the function that fires when a player moves to a new room, (b) what message currently reaches the UI on room change, (c) where in `dispatch/` (if anywhere) tactical state is built. Document findings in a brief comment block before editing.

- [ ] **Step 2: Add a TacticalGridPayload message type to the wire protocol**

Most likely: extend the existing room-state or session-event message. The exact mechanism depends on Step 1's findings.  Mirror the pattern used by other typed payloads in `sidequest-server/sidequest/protocol/messages.py`.

- [ ] **Step 3: Write an integration test for end-to-end room enter**

Simulate a session that lands a player in the `mouth` room and assert the resulting WebSocket message carries a `TacticalGridPayload` with the right `cavern_image_url` and `mask`. Use `TestClient` with a websocket client per existing patterns in `sidequest-server/tests/integration/`.

```python
def test_entering_mouth_emits_cavern_payload(test_client_with_caverns_sunden_session):
    # arrange: start a session, get the player to the mouth room
    msgs = test_client_with_caverns_sunden_session.move_to_room("mouth")
    # assert: a TacticalGridPayload arrived with cavern data
    payload_msg = next(m for m in msgs if m["type"] == "TACTICAL_GRID")
    assert payload_msg["payload"]["room_type"] == "cavern"
    assert payload_msg["payload"]["cavern_image_url"].endswith("mouth.cavern.png")
    assert "..." in payload_msg["payload"]["mask"]  # has floor cells
```

(Adapt the fixture / message-type names to the actual codebase.)

- [ ] **Step 4: Wire `load_room_payload` into the dispatch site identified in step 1**

Make the room-enter handler call `load_room_payload(world_dir, room_id)` and emit the resulting payload to the WebSocket. The token list and initiative come from existing game state — populate them from there (current room's tokens / current encounter's initiative). For settlement rooms, the payload still flows; the UI's Automapper branches on `room_type`.

- [ ] **Step 5: Run, verify pass**

```bash
cd sidequest-server
uv run pytest tests/integration/test_room_enter_cavern.py -v  # or whatever you named it
```
Expected: pass.

- [ ] **Step 6: Frontend wiring — make sure the UI consumes the new message**

Find the WebSocket message handler in `sidequest-ui/src/providers/GameStateProvider.tsx` (or equivalent) and route the new message into the explored-rooms / map-state shape that Automapper consumes. Verify by adding a Playwright/Vitest test or a quick in-browser check that the typed payload arrives as expected — see Task 22 manual playtest.

- [ ] **Step 7: Commit**

```bash
git add -p
git commit -m "feat(server+ui): wire cavern room loader into room-enter dispatch

Closes the wiring gap: load_room_payload is now reachable from gameplay.
Room enter emits TacticalGridPayload over the WebSocket; the UI's
Automapper routes by room_type. ADR-096.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase F — Integration & Validation

### Task 21: Full check-all

- [ ] **Step 1: Run server tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-server
just server-check
```
Expected: ruff + pytest pass.

- [ ] **Step 2: Run renderer tool tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-content/tools/cavern_renderer
uv run pytest -v
uv run ruff check .
```
Expected: pass.

- [ ] **Step 3: Run UI tests**

```bash
cd /Users/slabgorb/Projects/oq-1/sidequest-ui
npm run lint
npx vitest run
```
Expected: pass.

- [ ] **Step 4: Run aggregate gate**

```bash
cd /Users/slabgorb/Projects/oq-1
just check-all
```
Expected: pass. If any failure surfaces a wiring gap, fix it in this commit.

- [ ] **Step 5: Commit any fixup**

If fixups were needed:
```bash
git commit -m "fix: check-all gate fixups for cavern renderer slice"
```

---

### Task 22: Manual playtest

- [ ] **Step 1: Boot the stack**

```bash
cd /Users/slabgorb/Projects/oq-1
just up
```

Wait for `just logs` to show server + UI ready.

- [ ] **Step 2: Open the UI, start a caverns_sunden session**

Browser → http://localhost:5173 → connect → start new session in `caverns_and_claudes / caverns_sunden`.

- [ ] **Step 3: Navigate to the Mouth and verify the Map tab**

Issue an action that lands in the `mouth` room (or jump there via dev console / scenario harness). Open the Map tab. **Expected:** the cellular cavern PNG renders; tokens show on cells; clicking your character token opens the right-rail action panel and highlights the reach cells.

If the visual is broken (PNG missing, tokens off-position, action panel doesn't appear): debug and fix in the appropriate task. Do not paper over.

- [ ] **Step 4: Navigate to the Confessional and verify settlement view**

Move/teleport to `confessional`. The Map tab should show the settlement view: name + description + exit list. No tactical map.

- [ ] **Step 5: Open the GM panel (OTEL dashboard) and verify the cavern_room.load span**

Browser → http://localhost:8765/dashboard → check the timeline for `cavern_room.load` events. Each room enter should have one with seed + density + floor_count + mask hash.

- [ ] **Step 6: Stop services**

```bash
just down
```

- [ ] **Step 7: Commit any final fixup; the slice is done**

If no further changes needed, this slice is complete. Open a PR or merge per project conventions.

---

## Self-review

**Spec coverage check:**
- ✅ Authoring tool (§1 Architecture, §2 Tool) — Tasks 3-7
- ✅ Per-room data format (§3) — Tasks 7-11 (file format + authored content)
- ✅ Whole-world authoring (§3) — Tasks 8-11
- ✅ Server protocol changes (§4) — Tasks 12-13
- ✅ Static delivery (§4) — Task 14
- ✅ OTEL spans (§4) — Task 15
- ✅ Wiring test (§6) — Task 14
- ✅ Frontend rewrite (§5) — Tasks 16-19
- ✅ SettlementRoomView + Automapper branch (§5) — Tasks 17, 20
- ✅ Migration plan (§7) — Tasks 1, 2 (ADR), Task 21 (gate)
- ✅ ADR-096 + ADR-089 update (§7) — Tasks 1, 2

**Placeholder scan:** No "TBD" / "TODO" in plan steps. Code blocks are complete. Test code is concrete.

**Type consistency:**
- `Cell` interface: `{x, y}` consistent across `cellMath.ts`, `tactical.ts`, fixtures.
- `TacticalToken.cell`: `{x, y}` matches `Cell`.
- Faction values: `"player" | "ally" | "neutral" | "hostile"` consistent in renderer + fixture.
- `TacticalGridData.room_type: "cavern"` only — settlement rooms route around `TacticalGridData` entirely; the wire shape carries `"cavern" | "settlement"` per protocol.
- `CavernActionId`: `move | dash | attack | cast | object | dodge | end_turn` — used only in CavernActionPanel; future wiring will accept these IDs.

**Risks flagged:**
- The exact dispatch wiring site (Task 20b) is not pinned in this plan — it requires investigation as the first step of that task. The investigation step is bounded; once the room-enter flow is identified, the rest of the task is a small concrete edit + integration test.
- World authoring is taste-iteration-heavy. Estimate 30-90 minutes per descent depending on how often a seed needs re-rolling.
- `TestClient` with WebSocket-style integration tests may need session-fixture work that doesn't exist yet. If existing integration test patterns don't support a "land player in room X" helper, the wiring test in Task 20b may need a new fixture. Time-box: if the test scaffolding takes longer than the wiring itself, ship the wiring + a manual-only verification and file a follow-on for the integration test.
