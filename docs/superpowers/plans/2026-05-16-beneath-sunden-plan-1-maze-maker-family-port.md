# Beneath Sünden — Plan 1: maze-maker Family Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the maze-maker generation family (cellular, recursive-backtracker, randomized-Prim) plus two new generators (room-and-corridor, braid post-process) into a single server-side `sidequest/dungeon/interiors/` library with one coordinator interface, re-homing the existing ADR-096 cellular port so the authoring CLI and runtime share one generator.

**Architecture:** A dependency-free pure-Python subpackage `sidequest.dungeon.interiors`. Every generator returns the same `list[list[int]]` grid (`0`=FLOOR, `1`=WALL), seeded via `random.Random(seed)` for determinism, following the conventions already proven in `sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py`. A `generator.py` coordinator exposes a registry keyed by algorithm name behind a common `Interior` protocol. The existing authoring CLI in sidequest-content is re-pointed to import the new shared module (editable path dependency) so there is exactly one cellular implementation.

**Tech Stack:** Python 3 (sidequest-server, uv-managed), pytest, ruff. No third-party runtime deps in the interiors subpackage (stdlib `random` only).

**Spec:** `docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md` — covers §5.2 (interior generators), §8 (interiors/ file table), §10 step 1, §11 (determinism + parity tests).

**Scope boundary:** This plan delivers ONLY the interiors library + coordinator + cellular re-home. Region-graph generation, depth_score, persistence, set-pieces, materializer, and world authoring are later plans (spec §10 steps 2–8). No server wiring beyond the coordinator and the authoring-CLI re-point — the runtime consumer (materializer) is Plan 7.

**Conventions (apply to every generator, established by the existing cellular port):**
- Grid is `list[list[int]]`, indexed `grid[y][x]`, dimensions `height × width`.
- `FLOOR = 0`, `WALL = 1`. Borders are always WALL.
- Determinism contract: identical `(width, height, seed, **params)` → identical grid. Use one `random.Random(seed)` instance; never the global `random`.
- "Carve" generators (depthfirst, prim) start from a WALL-filled grid and carve FLOOR on odd coordinates with midpoint carving (maze-maker `Maze` base convention).

---

### Task 1: Create the interiors subpackage skeleton + shared grid module

**Files:**
- Create: `sidequest-server/sidequest/dungeon/__init__.py`
- Create: `sidequest-server/sidequest/dungeon/interiors/__init__.py`
- Create: `sidequest-server/sidequest/dungeon/interiors/grid.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_grid.py`
- Create: `sidequest-server/tests/dungeon/__init__.py`
- Create: `sidequest-server/tests/dungeon/interiors/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_grid.py
from sidequest.dungeon.interiors.grid import (
    FLOOR,
    WALL,
    new_grid,
    in_bounds,
    wall_neighbors,
    carve_between,
)


def test_constants():
    assert FLOOR == 0
    assert WALL == 1


def test_new_grid_is_all_wall_with_correct_shape():
    g = new_grid(width=11, height=7)
    assert len(g) == 7
    assert all(len(row) == 11 for row in g)
    assert all(cell == WALL for row in g for cell in row)


def test_in_bounds():
    g = new_grid(width=5, height=5)
    assert in_bounds(g, 0, 0)
    assert in_bounds(g, 4, 4)
    assert not in_bounds(g, 5, 4)
    assert not in_bounds(g, -1, 0)


def test_wall_neighbors_returns_two_step_wall_cells_in_bounds():
    g = new_grid(width=7, height=7)
    # centre cell (3,3): all four 2-step neighbors are walls and in-bounds
    n = sorted(wall_neighbors(g, 3, 3))
    assert n == sorted([(1, 3), (5, 3), (3, 1), (3, 5)])


def test_wall_neighbors_excludes_floor_cells():
    g = new_grid(width=7, height=7)
    g[3][1] = FLOOR  # (x=1, y=3) carved
    n = wall_neighbors(g, 3, 3)
    assert (1, 3) not in n


def test_carve_between_carves_endpoint_and_midpoint():
    g = new_grid(width=7, height=7)
    carve_between(g, 3, 3, 5, 3)
    assert g[3][3] == FLOOR
    assert g[3][5] == FLOOR
    assert g[3][4] == FLOOR  # midpoint
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_grid.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/__init__.py
"""Procedural megadungeon generation (spec: Beneath Sünden)."""
```

```python
# sidequest-server/sidequest/dungeon/interiors/__init__.py
"""maze-maker family port — shared interior generators.

Every generator returns list[list[int]] indexed [y][x], FLOOR=0/WALL=1,
deterministic for a given (width, height, seed, **params).
"""
```

```python
# sidequest-server/sidequest/dungeon/interiors/grid.py
"""Shared grid model + carve helpers for the maze-maker family port.

Convention matches the original maze-maker `Maze` base and the
existing cellular port: grid[y][x], FLOOR=0, WALL=1, carve generators
work on odd coordinates with midpoint carving.
"""

from __future__ import annotations

FLOOR = 0
WALL = 1

Grid = list[list[int]]


def new_grid(width: int, height: int) -> Grid:
    """Return a height x width grid filled entirely with WALL."""
    return [[WALL for _ in range(width)] for _ in range(height)]


def in_bounds(grid: Grid, x: int, y: int) -> bool:
    return 0 <= y < len(grid) and 0 <= x < len(grid[0])


def wall_neighbors(grid: Grid, x: int, y: int) -> list[tuple[int, int]]:
    """Two-step neighbors (maze-maker `walls`) that are in-bounds and WALL."""
    out: list[tuple[int, int]] = []
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        nx, ny = x + dx, y + dy
        if in_bounds(grid, nx, ny) and grid[ny][nx] == WALL:
            out.append((nx, ny))
    return out


def carve_between(grid: Grid, x0: int, y0: int, x1: int, y1: int) -> None:
    """Carve both endpoints and the midpoint to FLOOR (maze-maker carve)."""
    grid[y0][x0] = FLOOR
    grid[y1][x1] = FLOOR
    grid[(y0 + y1) // 2][(x0 + x1) // 2] = FLOOR
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_grid.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon sidequest-server/tests/dungeon
git commit -F - <<'EOF'
feat(dungeon): interiors subpackage skeleton + shared grid model

Plan 1 Task 1 — Beneath Sünden maze-maker family port.
EOF
```

---

### Task 2: Re-home the cellular generator into the shared library

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/cellular.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_cellular.py`

Port is verbatim from `sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py` (proven, ADR-096). It uses its own border-forcing + flood-fill (it does not consume `grid.py`'s carve helpers — cellular is additive, not carving).

- [ ] **Step 1: Write the failing test** (mirrors the proven `test_cellular.py` philosophy: shape, borders, determinism, variance, value-domain, single connected component)

```python
# sidequest-server/tests/dungeon/interiors/test_cellular.py
from sidequest.dungeon.interiors.cellular import gen_cave
from sidequest.dungeon.interiors.grid import FLOOR, WALL


def test_shape():
    g = gen_cave(width=18, height=18, seed=1042)
    assert len(g) == 18 and all(len(r) == 18 for r in g)


def test_borders_are_walls():
    g = gen_cave(width=18, height=18, seed=1042)
    for x in range(18):
        assert g[0][x] == WALL and g[17][x] == WALL
    for y in range(18):
        assert g[y][0] == WALL and g[y][17] == WALL


def test_deterministic():
    assert gen_cave(width=18, height=18, seed=7) == gen_cave(width=18, height=18, seed=7)


def test_seed_variance():
    assert gen_cave(width=18, height=18, seed=7) != gen_cave(width=18, height=18, seed=8)


def test_value_domain():
    g = gen_cave(width=18, height=18, seed=7)
    assert all(c in (FLOOR, WALL) for row in g for c in row)


def test_single_connected_floor_component():
    g = gen_cave(width=24, height=24, seed=99)
    h, w = len(g), len(g[0])
    start = next((x, y) for y in range(h) for x in range(w) if g[y][x] == FLOOR)
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and g[ny][nx] == FLOOR and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    assert len(seen) == sum(1 for r in g for c in r if c == FLOOR)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_cellular.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.cellular'`

- [ ] **Step 3: Write minimal implementation** (verbatim re-home; FLOOR/WALL now imported from `grid.py` for single-source constants)

```python
# sidequest-server/sidequest/dungeon/interiors/cellular.py
"""Cellular automata cavern generator.

Re-homed verbatim from the ADR-096 port
(sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py).
FLOOR/WALL now sourced from grid.py so all generators share constants.
"""

from __future__ import annotations

import random

from sidequest.dungeon.interiors.grid import FLOOR, WALL


def gen_cave(
    width: int,
    height: int,
    seed: int,
    *,
    density: float = 0.55,
    cutoff: int = 5,
    passes: int = 4,
) -> list[list[int]]:
    """Cellular-automaton cavern. Same (w,h,seed,density,cutoff,passes) → identical."""
    rng = random.Random(seed)
    grid = [
        [FLOOR if rng.random() < density else WALL for _ in range(width)]
        for _ in range(height)
    ]
    for x in range(width):
        grid[0][x] = WALL
        grid[height - 1][x] = WALL
    for y in range(height):
        grid[y][0] = WALL
        grid[y][width - 1] = WALL

    for _ in range(passes):
        grid = _ca_pass(grid, width, height, cutoff)

    return _keep_largest_floor_region(grid, width, height)


def _ca_pass(grid, width, height, cutoff):
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


def _keep_largest_floor_region(grid, width, height):
    seen = [[False] * width for _ in range(height)]
    best: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if grid[y][x] != FLOOR or seen[y][x]:
                continue
            region = _flood(grid, seen, x, y, width, height)
            if len(region) > len(best):
                best = region
    keep = set(best)
    out = [row[:] for row in grid]
    for y in range(height):
        for x in range(width):
            if grid[y][x] == FLOOR and (x, y) not in keep:
                out[y][x] = WALL
    return out


def _flood(grid, seen, sx, sy, width, height):
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

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_cellular.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/cellular.py sidequest-server/tests/dungeon/interiors/test_cellular.py
git commit -F - <<'EOF'
feat(dungeon): re-home cellular generator into shared interiors lib

Plan 1 Task 2 — verbatim ADR-096 port, constants now from grid.py.
EOF
```

---

### Task 3: Port the recursive-backtracker (depthfirst) generator

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/depthfirst.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_depthfirst.py`

Faithful port of maze-maker `lib/maze_maker/depthfirst.rb` (obtained verbatim): WALL-filled grid, random odd start, iterative stack, pick a random WALL two-step neighbor, carve endpoint+midpoint, backtrack on dead end. Produces a **perfect maze** (no loops).

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_depthfirst.py
from sidequest.dungeon.interiors.depthfirst import gen_depthfirst
from sidequest.dungeon.interiors.grid import FLOOR, WALL


def test_shape():
    g = gen_depthfirst(width=21, height=21, seed=3)
    assert len(g) == 21 and all(len(r) == 21 for r in g)


def test_deterministic():
    assert gen_depthfirst(width=21, height=21, seed=3) == gen_depthfirst(width=21, height=21, seed=3)


def test_seed_variance():
    assert gen_depthfirst(width=21, height=21, seed=3) != gen_depthfirst(width=21, height=21, seed=4)


def test_value_domain_and_has_floor():
    g = gen_depthfirst(width=21, height=21, seed=3)
    assert all(c in (FLOOR, WALL) for row in g for c in row)
    assert any(c == FLOOR for row in g for c in row)


def test_perfect_maze_has_no_two_by_two_floor_block():
    """A perfect maze never contains a 2x2 all-FLOOR block (that implies a loop)."""
    g = gen_depthfirst(width=31, height=31, seed=11)
    h, w = len(g), len(g[0])
    for y in range(h - 1):
        for x in range(w - 1):
            block = (g[y][x], g[y][x + 1], g[y + 1][x], g[y + 1][x + 1])
            assert block != (FLOOR, FLOOR, FLOOR, FLOOR), f"loop at {x},{y}"


def test_all_floor_is_connected():
    g = gen_depthfirst(width=31, height=31, seed=11)
    h, w = len(g), len(g[0])
    start = next((x, y) for y in range(h) for x in range(w) if g[y][x] == FLOOR)
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and g[ny][nx] == FLOOR and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    assert len(seen) == sum(1 for r in g for c in r if c == FLOOR)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_depthfirst.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.depthfirst'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/interiors/depthfirst.py
"""Recursive-backtracker (depth-first) maze generator.

Port of maze-maker lib/maze_maker/depthfirst.rb. Produces a perfect
maze (exactly one path between any two FLOOR cells; zero loops).
"""

from __future__ import annotations

import random

from sidequest.dungeon.interiors.grid import (
    FLOOR,
    carve_between,
    new_grid,
    wall_neighbors,
)


def gen_depthfirst(width: int, height: int, seed: int) -> list[list[int]]:
    """Deterministic for a given (width, height, seed)."""
    rng = random.Random(seed)
    grid = new_grid(width, height)

    # maze-maker: start at a random odd interior coordinate.
    sx = rng.randrange(0, max(1, (width - 1) // 2)) * 2 + 1
    sy = rng.randrange(0, max(1, (height - 1) // 2)) * 2 + 1
    grid[sy][sx] = FLOOR
    stack: list[tuple[int, int]] = [(sx, sy)]

    while stack:
        x, y = stack[-1]
        candidates = wall_neighbors(grid, x, y)
        if candidates:
            nx, ny = candidates[rng.randrange(len(candidates))]
            carve_between(grid, x, y, nx, ny)
            stack.append((nx, ny))
        else:
            stack.pop()

    return grid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_depthfirst.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/depthfirst.py sidequest-server/tests/dungeon/interiors/test_depthfirst.py
git commit -F - <<'EOF'
feat(dungeon): port recursive-backtracker (depthfirst) generator

Plan 1 Task 3 — perfect-maze carver from maze-maker depthfirst.rb.
EOF
```

---

### Task 4: Port the randomized-Prim variant generator

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/prim.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_prim.py`

Port of maze-maker `lib/maze_maker/prim.rb` (the maze-maker variant — *not* classical priority-queue Prim): `density` seed-points; from each, extend `complexity` steps, each step carving to a random WALL two-step neighbor (endpoint+midpoint), advancing the cursor. `density`/`complexity` scale with size. This variant can leave isolated pockets by design; the test asserts the documented behavior, not perfect connectivity.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_prim.py
from sidequest.dungeon.interiors.prim import gen_prim
from sidequest.dungeon.interiors.grid import FLOOR, WALL


def test_shape():
    g = gen_prim(width=25, height=25, seed=5)
    assert len(g) == 25 and all(len(r) == 25 for r in g)


def test_deterministic():
    assert gen_prim(width=25, height=25, seed=5) == gen_prim(width=25, height=25, seed=5)


def test_seed_variance():
    assert gen_prim(width=25, height=25, seed=5) != gen_prim(width=25, height=25, seed=6)


def test_value_domain():
    g = gen_prim(width=25, height=25, seed=5)
    assert all(c in (FLOOR, WALL) for row in g for c in row)


def test_carves_floor_proportional_to_density_and_complexity():
    sparse = gen_prim(width=41, height=41, seed=5, density=1, complexity=4)
    dense = gen_prim(width=41, height=41, seed=5, density=12, complexity=40)
    floor = lambda g: sum(1 for r in g for c in r if c == FLOOR)  # noqa: E731
    assert floor(dense) > floor(sparse)


def test_explicit_params_are_deterministic():
    a = gen_prim(width=31, height=31, seed=9, density=5, complexity=20)
    b = gen_prim(width=31, height=31, seed=9, density=5, complexity=20)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_prim.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.prim'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/interiors/prim.py
"""Randomized-Prim variant maze generator.

Port of maze-maker lib/maze_maker/prim.rb. NOT classical priority-queue
Prim: it sows `density` seed points and extends each `complexity` steps
by carving to a random WALL two-step neighbor. May leave isolated
pockets by design — that is the documented maze-maker behavior.
"""

from __future__ import annotations

import random

from sidequest.dungeon.interiors.grid import (
    FLOOR,
    carve_between,
    new_grid,
    wall_neighbors,
)


def gen_prim(
    width: int,
    height: int,
    seed: int,
    *,
    density: int | None = None,
    complexity: int | None = None,
) -> list[list[int]]:
    """Deterministic for a given (width, height, seed, density, complexity).

    When density/complexity are None they scale with size, mirroring
    maze-maker's size-derived defaults.
    """
    rng = random.Random(seed)
    if density is None:
        density = max(1, (width + height) // 8)
    if complexity is None:
        complexity = max(1, (width + height) // 2)

    grid = new_grid(width, height)
    for _ in range(density):
        x = rng.randrange(0, max(1, (width - 1) // 2)) * 2 + 1
        y = rng.randrange(0, max(1, (height - 1) // 2)) * 2 + 1
        grid[y][x] = FLOOR
        for _ in range(complexity):
            candidates = wall_neighbors(grid, x, y)
            if not candidates:
                break
            nx, ny = candidates[rng.randrange(len(candidates))]
            carve_between(grid, x, y, nx, ny)
            x, y = nx, ny

    return grid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_prim.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/prim.py sidequest-server/tests/dungeon/interiors/test_prim.py
git commit -F - <<'EOF'
feat(dungeon): port randomized-Prim variant generator

Plan 1 Task 4 — size-scaled density/complexity carver from prim.rb.
EOF
```

---

### Task 5: New room-and-corridor generator

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/roomcorridor.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_roomcorridor.py`

NEW (no maze-maker equivalent). Place non-overlapping rectangular rooms, then connect each room's center to the previous room's center with L-shaped corridors. Produces built architecture (temple/vault/hall themes). Not a perfect maze; corridors may create loops — that is intended for built themes.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_roomcorridor.py
from sidequest.dungeon.interiors.roomcorridor import gen_roomcorridor
from sidequest.dungeon.interiors.grid import FLOOR, WALL


def test_shape():
    g = gen_roomcorridor(width=40, height=30, seed=2)
    assert len(g) == 30 and all(len(r) == 40 for r in g)


def test_deterministic():
    assert gen_roomcorridor(width=40, height=30, seed=2) == gen_roomcorridor(width=40, height=30, seed=2)


def test_seed_variance():
    assert gen_roomcorridor(width=40, height=30, seed=2) != gen_roomcorridor(width=40, height=30, seed=3)


def test_borders_remain_walls():
    g = gen_roomcorridor(width=40, height=30, seed=2)
    for x in range(40):
        assert g[0][x] == WALL and g[29][x] == WALL
    for y in range(30):
        assert g[y][0] == WALL and g[y][39] == WALL


def test_has_at_least_two_rooms_worth_of_floor_and_is_connected():
    g = gen_roomcorridor(width=50, height=40, seed=7)
    h, w = len(g), len(g[0])
    floors = [(x, y) for y in range(h) for x in range(w) if g[y][x] == FLOOR]
    assert len(floors) > 30
    seen = {floors[0]}
    stack = [floors[0]]
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and g[ny][nx] == FLOOR and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))
    assert len(seen) == len(floors), "rooms not all corridor-connected"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_roomcorridor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.roomcorridor'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/interiors/roomcorridor.py
"""Room-and-corridor generator (built themes: temple, vault, hall).

NEW — no maze-maker equivalent. Places non-overlapping rectangular
rooms and connects consecutive room centers with L-shaped corridors.
Corridors may cross, creating loops; that is intended for built themes.
"""

from __future__ import annotations

import random

from sidequest.dungeon.interiors.grid import FLOOR, WALL, new_grid


def _carve_room(grid, x0, y0, rw, rh):
    for y in range(y0, y0 + rh):
        for x in range(x0, x0 + rw):
            grid[y][x] = FLOOR


def _carve_h(grid, x_a, x_b, y):
    for x in range(min(x_a, x_b), max(x_a, x_b) + 1):
        grid[y][x] = FLOOR


def _carve_v(grid, y_a, y_b, x):
    for y in range(min(y_a, y_b), max(y_a, y_b) + 1):
        grid[y][x] = FLOOR


def gen_roomcorridor(
    width: int,
    height: int,
    seed: int,
    *,
    max_rooms: int = 12,
    room_min: int = 3,
    room_max: int = 7,
) -> list[list[int]]:
    """Deterministic for a given (width, height, seed, max_rooms, room_min, room_max)."""
    rng = random.Random(seed)
    grid = new_grid(width, height)
    centers: list[tuple[int, int]] = []

    for _ in range(max_rooms):
        rw = rng.randint(room_min, room_max)
        rh = rng.randint(room_min, room_max)
        x0 = rng.randint(1, max(1, width - rw - 1))
        y0 = rng.randint(1, max(1, height - rh - 1))
        # reject if it would touch the border
        if x0 + rw >= width - 1 or y0 + rh >= height - 1:
            continue
        _carve_room(grid, x0, y0, rw, rh)
        cx, cy = x0 + rw // 2, y0 + rh // 2
        if centers:
            px, py = centers[-1]
            if rng.random() < 0.5:
                _carve_h(grid, px, cx, py)
                _carve_v(grid, py, cy, cx)
            else:
                _carve_v(grid, py, cy, px)
                _carve_h(grid, px, cx, cy)
        centers.append((cx, cy))

    # guarantee border integrity
    for x in range(width):
        grid[0][x] = WALL
        grid[height - 1][x] = WALL
    for y in range(height):
        grid[y][0] = WALL
        grid[y][width - 1] = WALL
    return grid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_roomcorridor.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/roomcorridor.py sidequest-server/tests/dungeon/interiors/test_roomcorridor.py
git commit -F - <<'EOF'
feat(dungeon): room-and-corridor generator for built themes

Plan 1 Task 5 — new generator, no maze-maker equivalent.
EOF
```

---

### Task 6: Braid post-process (dead-end removal / interior loops)

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/braid.py`
- Test: `sidequest-server/tests/dungeon/interiors/test_braid.py`

NEW post-process (spec §5.2 perfect-maze mitigation). Removes a tunable fraction of dead-ends by carving one wall adjacent to each selected dead-end, introducing loops. `braid_ratio` ∈ [0.0, 1.0]: `0.0` = untouched perfect maze; `1.0` = remove every dead-end. Deterministic given `(grid, seed, braid_ratio)`.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_braid.py
from sidequest.dungeon.interiors.depthfirst import gen_depthfirst
from sidequest.dungeon.interiors.braid import braid, dead_ends
from sidequest.dungeon.interiors.grid import FLOOR


def test_ratio_zero_is_identity():
    g = gen_depthfirst(width=31, height=31, seed=11)
    out = braid([r[:] for r in g], seed=1, braid_ratio=0.0)
    assert out == g


def test_ratio_one_removes_all_dead_ends():
    g = gen_depthfirst(width=31, height=31, seed=11)
    out = braid([r[:] for r in g], seed=1, braid_ratio=1.0)
    assert dead_ends(out) == []


def test_partial_ratio_reduces_dead_ends_monotonically():
    g = gen_depthfirst(width=41, height=41, seed=4)
    base = len(dead_ends(g))
    half = len(dead_ends(braid([r[:] for r in g], seed=1, braid_ratio=0.5)))
    full = len(dead_ends(braid([r[:] for r in g], seed=1, braid_ratio=1.0)))
    assert base >= half >= full
    assert half < base  # 0.5 actually changed something


def test_deterministic():
    g = gen_depthfirst(width=31, height=31, seed=11)
    a = braid([r[:] for r in g], seed=2, braid_ratio=0.3)
    b = braid([r[:] for r in g], seed=2, braid_ratio=0.3)
    assert a == b


def test_braid_only_adds_floor_never_removes():
    g = gen_depthfirst(width=31, height=31, seed=11)
    out = braid([r[:] for r in g], seed=2, braid_ratio=0.7)
    for y in range(len(g)):
        for x in range(len(g[0])):
            if g[y][x] == FLOOR:
                assert out[y][x] == FLOOR  # never walls an existing floor
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_braid.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.braid'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/interiors/braid.py
"""Braid post-process: remove a fraction of dead-ends to add loops.

Spec §5.2 mitigation for perfect-maze interiors. braid_ratio in
[0.0, 1.0]: 0.0 leaves the maze untouched, 1.0 removes every dead-end.
Deterministic given (grid, seed, braid_ratio). Only carves FLOOR;
never walls an existing FLOOR cell.
"""

from __future__ import annotations

import random

from sidequest.dungeon.interiors.grid import FLOOR, WALL, in_bounds

Grid = list[list[int]]
_ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))


def dead_ends(grid: Grid) -> list[tuple[int, int]]:
    """FLOOR cells with exactly one FLOOR orthogonal neighbor."""
    out: list[tuple[int, int]] = []
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if grid[y][x] != FLOOR:
                continue
            n = sum(
                1
                for dx, dy in _ORTHO
                if in_bounds(grid, x + dx, y + dy) and grid[y + dy][x + dx] == FLOOR
            )
            if n == 1:
                out.append((x, y))
    return out


def braid(grid: Grid, *, seed: int, braid_ratio: float) -> Grid:
    """Carve walls adjacent to a braid_ratio fraction of dead-ends."""
    if braid_ratio <= 0.0:
        return grid
    rng = random.Random(seed)
    # Iterate until the target fraction of the ORIGINAL dead-ends is gone.
    original = dead_ends(grid)
    target_removed = int(round(len(original) * min(1.0, braid_ratio)))
    if target_removed <= 0:
        return grid

    removed = 0
    # Sort for determinism, then process in seeded-shuffled order.
    pending = sorted(original)
    rng.shuffle(pending)
    for x, y in pending:
        if removed >= target_removed:
            break
        # still a dead-end after prior carves?
        floor_n = [
            (x + dx, y + dy)
            for dx, dy in _ORTHO
            if in_bounds(grid, x + dx, y + dy) and grid[y + dy][x + dx] == FLOOR
        ]
        if len(floor_n) != 1:
            continue
        # carve a WALL neighbor that is not the single floor neighbor and not a border
        wall_n = [
            (x + dx, y + dy)
            for dx, dy in _ORTHO
            if in_bounds(grid, x + dx, y + dy)
            and grid[y + dy][x + dx] == WALL
            and 0 < x + dx < len(grid[0]) - 1
            and 0 < y + dy < len(grid) - 1
        ]
        if not wall_n:
            continue
        nx, ny = wall_n[rng.randrange(len(wall_n))]
        grid[ny][nx] = FLOOR
        removed += 1
    return grid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_braid.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/braid.py sidequest-server/tests/dungeon/interiors/test_braid.py
git commit -F - <<'EOF'
feat(dungeon): braid post-process for tunable interior loops

Plan 1 Task 6 — spec §5.2 perfect-maze mitigation.
EOF
```

---

### Task 7: Generator coordinator (registry + common interface)

**Files:**
- Create: `sidequest-server/sidequest/dungeon/interiors/generator.py`
- Modify: `sidequest-server/sidequest/dungeon/interiors/__init__.py` (export public API)
- Test: `sidequest-server/tests/dungeon/interiors/test_generator.py`

A `generate_interior(algorithm, width, height, seed, *, braid_ratio=0.0, params=None)` coordinator: dispatches by algorithm name, applies the optional braid post-process uniformly, raises **loudly** on unknown algorithm (no silent fallback — per CLAUDE.md). This is the single entry point later plans (materializer, Plan 7) and the authoring CLI (Task 8) call.

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/interiors/test_generator.py
import pytest

from sidequest.dungeon.interiors.generator import generate_interior, ALGORITHMS
from sidequest.dungeon.interiors.grid import FLOOR, WALL


def test_registry_lists_all_five_algorithms():
    assert set(ALGORITHMS) == {"cellular", "depthfirst", "prim", "roomcorridor"}


@pytest.mark.parametrize("algo", ["cellular", "depthfirst", "prim", "roomcorridor"])
def test_each_algorithm_produces_valid_deterministic_grid(algo):
    g1 = generate_interior(algo, width=25, height=25, seed=42)
    g2 = generate_interior(algo, width=25, height=25, seed=42)
    assert g1 == g2
    assert len(g1) == 25 and all(len(r) == 25 for r in g1)
    assert all(c in (FLOOR, WALL) for row in g1 for c in row)


def test_unknown_algorithm_raises_loudly():
    with pytest.raises(ValueError, match="unknown interior algorithm 'spelunk'"):
        generate_interior("spelunk", width=10, height=10, seed=1)


def test_braid_ratio_applied_for_maze_algorithms():
    plain = generate_interior("depthfirst", width=41, height=41, seed=4)
    braided = generate_interior("depthfirst", width=41, height=41, seed=4, braid_ratio=1.0)
    from sidequest.dungeon.interiors.braid import dead_ends

    assert dead_ends(braided) == []
    assert plain != braided


def test_params_passed_through():
    a = generate_interior("prim", width=31, height=31, seed=9, params={"density": 3, "complexity": 10})
    b = generate_interior("prim", width=31, height=31, seed=9, params={"density": 3, "complexity": 10})
    c = generate_interior("prim", width=31, height=31, seed=9, params={"density": 12, "complexity": 40})
    assert a == b
    assert a != c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/test_generator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.interiors.generator'`

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest-server/sidequest/dungeon/interiors/generator.py
"""Coordinator: dispatch by algorithm name, apply optional braid.

Single entry point for the materializer (Plan 7) and the authoring
CLI (Task 8). Unknown algorithm raises loudly — no silent fallback
(CLAUDE.md: No Silent Fallbacks).
"""

from __future__ import annotations

from sidequest.dungeon.interiors.braid import braid
from sidequest.dungeon.interiors.cellular import gen_cave
from sidequest.dungeon.interiors.depthfirst import gen_depthfirst
from sidequest.dungeon.interiors.prim import gen_prim
from sidequest.dungeon.interiors.roomcorridor import gen_roomcorridor

Grid = list[list[int]]

ALGORITHMS = {
    "cellular": gen_cave,
    "depthfirst": gen_depthfirst,
    "prim": gen_prim,
    "roomcorridor": gen_roomcorridor,
}


def generate_interior(
    algorithm: str,
    *,
    width: int,
    height: int,
    seed: int,
    braid_ratio: float = 0.0,
    params: dict | None = None,
) -> Grid:
    """Generate one interior grid. Deterministic for identical inputs."""
    if algorithm not in ALGORITHMS:
        raise ValueError(
            f"unknown interior algorithm {algorithm!r}; "
            f"known: {sorted(ALGORITHMS)}"
        )
    fn = ALGORITHMS[algorithm]
    grid = fn(width=width, height=height, seed=seed, **(params or {}))
    if braid_ratio > 0.0:
        # braid uses a derived sub-seed so it is independent of map carving
        grid = braid(grid, seed=seed ^ 0x5EED, braid_ratio=braid_ratio)
    return grid
```

Note: `generate_interior` is keyword-only for `width/height/seed`; the test calls them as keywords — keep signatures aligned.

```python
# sidequest-server/sidequest/dungeon/interiors/__init__.py  (replace contents)
"""maze-maker family port — shared interior generators.

Every generator returns list[list[int]] indexed [y][x], FLOOR=0/WALL=1,
deterministic for a given (width, height, seed, **params).
"""

from sidequest.dungeon.interiors.generator import ALGORITHMS, generate_interior
from sidequest.dungeon.interiors.grid import FLOOR, WALL

__all__ = ["ALGORITHMS", "generate_interior", "FLOOR", "WALL"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/interiors/ -v`
Expected: PASS (all interiors tests green; coordinator test 6 passed)

- [ ] **Step 5: Commit**

```bash
git add sidequest-server/sidequest/dungeon/interiors/generator.py sidequest-server/sidequest/dungeon/interiors/__init__.py sidequest-server/tests/dungeon/interiors/test_generator.py
git commit -F - <<'EOF'
feat(dungeon): generator coordinator with registry + braid wiring

Plan 1 Task 7 — single entry point; loud on unknown algorithm.
EOF
```

---

### Task 8: Re-point the authoring CLI to the shared library (single cellular, no fork)

**Files:**
- Modify: `sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py` (becomes a thin re-export shim)
- Modify: `sidequest-content/tools/cavern_renderer/pyproject.toml` (add path dependency on sidequest-server)
- Test: `sidequest-content/tools/cavern_renderer/tests/test_cellular.py` (unchanged — must still pass against the shim)

Spec §8: "single generator, no fork." The canonical cellular now lives in sidequest-server; the content-side module becomes a re-export so existing authoring output and `tests/test_cellular.py` stay byte-identical (the re-home in Task 2 was verbatim, so output is unchanged).

- [ ] **Step 1: Verify the existing content-side test currently passes (baseline)**

Run: `cd sidequest-content/tools/cavern_renderer && uv run pytest tests/test_cellular.py -v`
Expected: PASS (baseline before re-point — 7 passed)

- [ ] **Step 2: Add the path dependency**

Add to `sidequest-content/tools/cavern_renderer/pyproject.toml` under `[project]` dependencies:

```toml
dependencies = [
    "sidequest-server",
]

[tool.uv.sources]
sidequest-server = { path = "../../../../oq-1/sidequest-server", editable = true }
```

(Adjust the relative path if the tool is invoked from a different clone; the path must resolve to this repo's `sidequest-server`. If a `[tool.uv.sources]` block already exists, add the single key to it rather than duplicating the table.)

Run: `cd sidequest-content/tools/cavern_renderer && uv sync`
Expected: resolves, installs sidequest-server editable.

- [ ] **Step 3: Replace the content-side cellular with a re-export shim**

```python
# sidequest-content/tools/cavern_renderer/cavern_renderer/cellular.py
"""Re-export shim — canonical cellular now lives in sidequest-server.

Spec §8 (Beneath Sünden): single generator, no fork. This module
keeps the historical import path (`cavern_renderer.cellular`) working
while delegating to sidequest.dungeon.interiors.cellular.
"""

from sidequest.dungeon.interiors.cellular import gen_cave
from sidequest.dungeon.interiors.grid import FLOOR, WALL

__all__ = ["gen_cave", "FLOOR", "WALL"]
```

- [ ] **Step 4: Run the content-side test to verify the shim is transparent**

Run: `cd sidequest-content/tools/cavern_renderer && uv run pytest tests/test_cellular.py -v`
Expected: PASS (7 passed — identical behavior through the shim; this is the wiring test proving the shared library has a real non-test consumer, per CLAUDE.md)

- [ ] **Step 5: Commit (in the sidequest-content subrepo)**

```bash
cd sidequest-content && git add tools/cavern_renderer/cavern_renderer/cellular.py tools/cavern_renderer/pyproject.toml
git commit -F - <<'EOF'
refactor(cavern_renderer): re-point cellular to shared sidequest.dungeon.interiors

Plan 1 Task 8 — single generator, no fork (Beneath Sünden spec §8).
Authoring output unchanged; re-home in Task 2 was verbatim.
EOF
```

---

### Task 9: Full-suite gate + ruff

**Files:** none (verification only)

- [ ] **Step 1: Run the full interiors suite + lint (sidequest-server)**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -v && uv run ruff check sidequest/dungeon/`
Expected: all dungeon tests PASS; ruff reports no errors.

- [ ] **Step 2: Run the content-side authoring tests (no regression)**

Run: `cd sidequest-content/tools/cavern_renderer && uv run pytest -v`
Expected: PASS (cellular via shim + render/cli/derive unaffected)

- [ ] **Step 3: Commit any ruff autofixes (if produced)**

```bash
cd sidequest-server && git add -A sidequest/dungeon
git commit -F - <<'EOF'
chore(dungeon): ruff autofix for interiors library

Plan 1 Task 9 — full-suite gate.
EOF
```
(Skip the commit if `git status` shows nothing to commit.)

---

## Self-Review

**1. Spec coverage (Plan 1 scope = spec §10 step 1):**
- §5.2 generator family: cellular (T2), depthfirst (T3), prim (T4), roomcorridor (T5), braid post-process (T6) ✓
- §8 `interiors/` file table: `grid.py` (T1), `cellular.py` (T2), `depthfirst.py` (T3), `prim.py` (T4), `roomcorridor.py` (T5), `braid.py` (T6), `generator.py` coordinator (T7) ✓
- §8 "re-homed from sidequest-content … shared by authoring CLI and runtime — single generator, no fork": T2 (re-home) + T8 (CLI re-point shim) ✓
- §11 determinism tests: every generator has a determinism + seed-variance test ✓
- §11 "no silent fallback" (CLAUDE.md): T7 unknown-algorithm raises loudly ✓
- CLAUDE.md "every test suite needs a wiring test": T8 step 4 — the authoring CLI is the real non-test consumer of the shared library, exercised end-to-end ✓
- Out of scope (correctly deferred): region graph, depth_score, persistence, set-pieces, materializer, world authoring, OTEL spans (OTEL belongs to the runtime materializer in Plan 7 — the interiors library is pure/deterministic and emits none) — noted in the scope boundary header.

**2. Placeholder scan:** No TBD/TODO; every code step has complete code; every command has expected output. The pyproject path in T8 step 2 is flagged as clone-relative with explicit adjustment instruction (not a placeholder — a documented environment fact). ✓

**3. Type consistency:** `Grid = list[list[int]]`, `FLOOR`/`WALL` from `grid.py` everywhere; `wall_neighbors`/`carve_between`/`new_grid`/`in_bounds` signatures defined in T1 and used unchanged in T3/T4/T6; `gen_cave`/`gen_depthfirst`/`gen_prim`/`gen_roomcorridor` keyword signatures match the coordinator's `fn(width=, height=, seed=, **params)` call in T7; `braid(grid, *, seed, braid_ratio)` defined T6, called identically T7. ✓

No issues found.
