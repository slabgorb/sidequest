# Beneath Sünden — Plan 2: Region-Graph Generator + Jaquays Invariant Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Stage-1 region-graph generator for Beneath Sünden — a pure, deterministic-pre-curation library that generates one themed-zone expansion per `(campaign_seed, expansion_id)`, enforces all five Jaquays topology invariants as hard re-roll post-conditions, and runs the incremental global loop/solvability check as the expansion attaches to the contiguous map.

**Architecture:** A dependency-free pure-Python subpackage `sidequest.dungeon.region_graph` (package, mirroring the `sidequest.dungeon.interiors` precedent from Plan 1 — the spec §8 names a single `region_graph.py`; we decompose it into focused modules behind one public import path, flagged for review). Nodes are themed region zones, edges are typed connections (`corridor|stairs|shaft|chute|secret`) carrying `hidden` (non-obvious: secret/conditional) and `shortcut` (collapses distance toward entrance) flags. A candidate builder produces raw topology honoring a `connection_burst` knob; an invariant checker validates the five §5.1 post-conditions by exact counting + BFS (no fragile cycle enumeration); a re-roll loop derives collision-resistant per-attempt sub-seeds (blake2b, **not** XOR — pre-empts the Plan 7 `seed ^ 0x5EED` fixed-point gotcha at this layer) and fails loudly after `max_reroll_attempts`. `attach_expansion` mutates the contiguous graph and re-verifies global connectivity + loopfulness, raising loudly on violation.

**Tech Stack:** Python 3 (sidequest-server, uv-managed), pytest, ruff, pyright. Stdlib only (`random`, `hashlib`, `collections`, `dataclasses`) — no hypothesis, no networkx. Property tests are seed-sweep loops (`pytest.mark.parametrize` over `range(N)`), matching the Plan 1 test style.

---

## Execution Preamble (read before Task 1)

- **Subrepo branch first.** All code lands in the **`sidequest-server`** subrepo (`/Users/slabgorb/Projects/oq-1/sidequest-server`), which is its own git repo defaulting to `develop`. **Before any implementation**, create the feature branch *in that subrepo*:
  ```bash
  cd /Users/slabgorb/Projects/oq-1/sidequest-server
  git fetch origin && git checkout develop && git pull --ff-only
  git checkout -b feat/beneath-sunden-region-graph
  ```
  Commits otherwise pollute `develop`. `develop` already carries `sidequest/dungeon/interiors/` (Plan 1 merged via PR #295) — verify with `python -c "import sidequest.dungeon.interiors"` from the subrepo before starting.
- **PR target is `develop`** (gitflow; see `sidequest-server/CLAUDE.md`).
- **Commit-clean check:** the only authoritative leak check is `git log -1 --format=%B | od -c`; reviewer "system-reminder leaked into commit" reports are usually a harness artifact on git-log tool output (see memory `feedback_implementer_commit_leakage`). Do not amend-loop on it.
- **Run tests via the `testing-runner` subagent**, not directly (Dev agent rule).

### Scope boundaries (deliberate — these are NOT omissions; logged here so review does not flag them)

| Concern | Owner | Plan 2 stance |
|---|---|---|
| `depth_score` assignment / jitter / bucketing | Plan 3 (`depth.py`) | `RegionNode` deliberately has **no** `depth_score` field — adding an always-`None` field is a placeholder (CLAUDE.md "No Stubbing"). Plan 3 extends the dataclass when it is actually assigned. |
| Theme palette loader, depth-band eligibility, adjacency affinity | Plan 4 (`themes.py`) | `generate_expansion` takes a `theme_pool: list[str]` parameter and picks uniformly via the seeded RNG. Real palette/affinity selection is Plan 4 — this is an input parameter, not a stub. |
| Persistence / serialization (`dungeon_map`, `frontier`) | Plan 5 (`persistence.py`) | Pure in-memory graph. No save schema, no JSON. |
| Set-pieces / tropes / quest-at-attach / ledger | Plan 6 | Not touched. |
| Async look-ahead worker, OTEL spans, mandatory production wiring test | Plan 7 (`materializer.py`) | Plan 2 is a pure library with **no runtime consumer yet**, so per spec §8 the OTEL spans (`dungeon.materialize.design`) and the mandatory session-path wiring test are emitted/added at Plan 7. Plan 2's deliverable toward that is the `GenerationReport` — the span-ready data contract (attempt count + per-invariant pass/fail + edge/loop/shortcut/hidden counts). Faking OTEL on an unwired function would itself violate "Verify Wiring, Not Just Existence." Task 7's deep-chain test is the strongest wiring proof available at this layer (public API exercised end-to-end); it explicitly notes the production-path wiring test is Plan 7's. |

---

## File Structure

```
sidequest-server/sidequest/dungeon/region_graph/
├── __init__.py        # public API re-exports
├── model.py           # RegionNode, RegionEdge, RegionGraph, Expansion
├── config.py          # JaquaysConfig (+ spec defaults, validation)
├── errors.py          # ExpansionGenerationError
├── invariants.py      # GenerationReport, check_invariants()
└── generator.py       # _subseed, _build_candidate, generate_expansion, attach_expansion

sidequest-server/tests/dungeon/region_graph/
├── __init__.py
├── test_model.py
├── test_config.py
├── test_invariants.py
├── test_generator.py
└── test_chain.py      # deep-chain property/integration sweep
```

Decomposition rationale: spec §8 names one `region_graph.py`, but it would carry five responsibilities (~500+ LOC). The codebase already established `sidequest/dungeon/interiors/` as a focused-module package in Plan 1; we follow that precedent. The public import path `from sidequest.dungeon.region_graph import generate_expansion` satisfies the spec's named module semantically. **Flag this for reviewer confirmation.**

---

### Task 1: Region-graph data model

**Files:**
- Create: `sidequest-server/sidequest/dungeon/region_graph/__init__.py` (minimal, expanded in Task 7)
- Create: `sidequest-server/sidequest/dungeon/region_graph/model.py`
- Create: `sidequest-server/tests/dungeon/region_graph/__init__.py` (empty)
- Test: `sidequest-server/tests/dungeon/region_graph/test_model.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/region_graph/test_model.py
import pytest

from sidequest.dungeon.region_graph.model import (
    Expansion,
    RegionEdge,
    RegionGraph,
    RegionNode,
)


def _entrance_graph() -> RegionGraph:
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="town_threshold"))
    return g


def test_add_node_and_edge_basic():
    g = _entrance_graph()
    g.add_node(RegionNode(id="a", expansion_id=1, theme="crypt"))
    g.add_edge(RegionEdge(a="surface", b="a", kind="corridor"))
    assert g.neighbors("surface") == ["a"]
    assert g.degree("a") == 1


def test_duplicate_node_id_raises_loudly():
    g = _entrance_graph()
    with pytest.raises(ValueError, match="duplicate region id 'surface'"):
        g.add_node(RegionNode(id="surface", expansion_id=0, theme="x"))


def test_edge_to_unknown_endpoint_raises_loudly():
    g = _entrance_graph()
    with pytest.raises(ValueError, match="edge endpoint 'ghost' is not a known region"):
        g.add_edge(RegionEdge(a="surface", b="ghost", kind="corridor"))


def test_self_loop_edge_raises_loudly():
    g = _entrance_graph()
    with pytest.raises(ValueError, match="self-loop edge on 'surface'"):
        g.add_edge(RegionEdge(a="surface", b="surface", kind="corridor"))


def test_bfs_dist_and_reachability():
    g = _entrance_graph()
    for rid in ("a", "b", "c"):
        g.add_node(RegionNode(id=rid, expansion_id=1, theme="crypt"))
    g.add_edge(RegionEdge(a="surface", b="a", kind="corridor"))
    g.add_edge(RegionEdge(a="a", b="b", kind="corridor"))
    g.add_edge(RegionEdge(a="b", b="c", kind="corridor"))
    dist = g.bfs_dist("surface")
    assert dist == {"surface": 0, "a": 1, "b": 2, "c": 3}
    assert g.reachable_from_entrance() == {"surface", "a", "b", "c"}
    assert g.is_connected() is True


def test_bfs_dist_skip_edges_reroutes():
    g = _entrance_graph()
    for rid in ("a", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=1, theme="crypt"))
    g.add_edge(RegionEdge(a="surface", b="a", kind="corridor"))   # idx 0
    g.add_edge(RegionEdge(a="a", b="b", kind="corridor"))         # idx 1
    g.add_edge(RegionEdge(a="surface", b="b", kind="shaft"))      # idx 2 (shortcut)
    assert g.bfs_dist("surface")["b"] == 1
    assert g.bfs_dist("surface", skip_edges={2})["b"] == 2


def test_cyclomatic_number_counts_independent_loops():
    g = _entrance_graph()
    for rid in ("a", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=1, theme="crypt"))
    g.add_edge(RegionEdge(a="surface", b="a", kind="corridor"))
    g.add_edge(RegionEdge(a="a", b="b", kind="corridor"))
    assert g.cyclomatic_number() == 0           # tree
    g.add_edge(RegionEdge(a="b", b="surface", kind="secret"))
    assert g.cyclomatic_number() == 1           # one loop
    assert g.is_connected() is True


def test_cyclomatic_counts_components():
    g = _entrance_graph()
    g.add_node(RegionNode(id="island", expansion_id=9, theme="crypt"))  # disconnected
    assert g._component_count() == 2
    assert g.cyclomatic_number() == 0
    assert g.is_connected() is False


def test_expansion_is_a_plain_node_edge_bundle():
    exp = Expansion(
        expansion_id=3,
        new_nodes=[RegionNode(id="exp003.r0", expansion_id=3, theme="vault")],
        new_edges=[RegionEdge(a="surface", b="exp003.r0", kind="stairs", hidden=True)],
    )
    assert exp.new_region_ids() == {"exp003.r0"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.region_graph'`

- [ ] **Step 3: Create the package skeleton + model**

```python
# sidequest-server/sidequest/dungeon/region_graph/__init__.py
"""Stage-1 region-graph generator + Jaquays invariants (spec: Beneath Sünden §5.1).

Public API is finalised in Task 7. Pure, dependency-free, deterministic
pre-curation. No persistence, no themes loader, no depth_score here —
see the plan's scope-boundary table.
"""
```

```python
# sidequest-server/sidequest/dungeon/region_graph/model.py
"""Region-graph data model.

A region is a themed zone (node). An edge is a typed connection
(corridor|stairs|shaft|chute|secret) optionally hidden (secret/conditional)
and optionally a shortcut (collapses distance toward the surface entrance).
The contiguous map is keyed by region/expansion id, never by floor
(spec decision rows 1, 2).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegionNode:
    id: str
    expansion_id: int
    theme: str


@dataclass(frozen=True)
class RegionEdge:
    a: str
    b: str
    kind: str
    hidden: bool = False
    shortcut: bool = False

    def endpoints(self) -> frozenset[str]:
        return frozenset((self.a, self.b))


@dataclass
class Expansion:
    """A candidate batch of new regions + edges (edges may reference
    already-explored region ids for stitch/shortcut connections)."""

    expansion_id: int
    new_nodes: list[RegionNode]
    new_edges: list[RegionEdge]

    def new_region_ids(self) -> set[str]:
        return {n.id for n in self.new_nodes}


@dataclass
class RegionGraph:
    entrance_id: str
    nodes: dict[str, RegionNode] = field(default_factory=dict)
    edges: list[RegionEdge] = field(default_factory=list)

    def add_node(self, node: RegionNode) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate region id {node.id!r}")
        self.nodes[node.id] = node

    def add_edge(self, edge: RegionEdge) -> None:
        if edge.a == edge.b:
            raise ValueError(f"self-loop edge on {edge.a!r} is not allowed")
        for end in (edge.a, edge.b):
            if end not in self.nodes:
                raise ValueError(
                    f"edge endpoint {end!r} is not a known region"
                )
        self.edges.append(edge)

    def neighbors(self, region_id: str) -> list[str]:
        out: list[str] = []
        for e in self.edges:
            if e.a == region_id:
                out.append(e.b)
            elif e.b == region_id:
                out.append(e.a)
        return out

    def degree(self, region_id: str) -> int:
        return sum(1 for e in self.edges if region_id in (e.a, e.b))

    def bfs_dist(
        self,
        source: str,
        *,
        blocked_node: str | None = None,
        skip_edges: set[int] | None = None,
    ) -> dict[str, int]:
        skip = skip_edges or set()
        adj: dict[str, list[str]] = {n: [] for n in self.nodes}
        for i, e in enumerate(self.edges):
            if i in skip:
                continue
            adj[e.a].append(e.b)
            adj[e.b].append(e.a)
        dist: dict[str, int] = {source: 0}
        q: deque[str] = deque([source])
        while q:
            cur = q.popleft()
            for nxt in adj[cur]:
                if nxt == blocked_node:
                    continue
                if nxt not in dist:
                    dist[nxt] = dist[cur] + 1
                    q.append(nxt)
        return dist

    def reachable_from_entrance(self) -> set[str]:
        return set(self.bfs_dist(self.entrance_id))

    def is_connected(self) -> bool:
        if not self.nodes:
            return True
        return len(self.reachable_from_entrance()) == len(self.nodes)

    def _component_count(self) -> int:
        seen: set[str] = set()
        comps = 0
        for n in self.nodes:
            if n in seen:
                continue
            comps += 1
            seen |= set(self.bfs_dist(n))
        return comps

    def cyclomatic_number(self) -> int:
        """|E| - |V| + components. 0 == forest; >=1 == has loops."""
        return len(self.edges) - len(self.nodes) + self._component_count()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_model.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/__init__.py sidequest/dungeon/region_graph/model.py tests/dungeon/region_graph/__init__.py tests/dungeon/region_graph/test_model.py
git commit -m "feat(dungeon): region-graph data model — nodes, typed edges, BFS/cyclomatic"
```

---

### Task 2: Config + errors

**Files:**
- Create: `sidequest-server/sidequest/dungeon/region_graph/config.py`
- Create: `sidequest-server/sidequest/dungeon/region_graph/errors.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/region_graph/test_config.py
import pytest

from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.errors import ExpansionGenerationError


def test_spec_defaults():
    c = JaquaysConfig()
    assert c.min_stitch_edges == 2
    assert c.min_loops_into_explored == 1
    assert c.min_hidden_edges == 1
    assert c.min_shortcut_edges == 1
    assert c.min_shortcut_gain == 3
    assert c.connection_burst == 3
    assert c.new_regions_per_expansion == (3, 6)
    assert c.max_reroll_attempts == 64
    assert c.edge_kinds == ("corridor", "stairs", "shaft", "chute", "secret")


def test_validate_rejects_empty_edge_kinds():
    with pytest.raises(ValueError, match="edge_kinds must be non-empty"):
        JaquaysConfig(edge_kinds=()).validate()


def test_validate_requires_secret_kind_for_hidden_edges():
    with pytest.raises(ValueError, match="edge_kinds must include 'secret'"):
        JaquaysConfig(edge_kinds=("corridor", "stairs")).validate()


def test_validate_rejects_floor_below_one():
    with pytest.raises(ValueError, match="min_stitch_edges must be >= 1"):
        JaquaysConfig(min_stitch_edges=0).validate()


def test_validate_rejects_inverted_region_range():
    with pytest.raises(ValueError, match="new_regions_per_expansion"):
        JaquaysConfig(new_regions_per_expansion=(6, 3)).validate()


def test_validate_rejects_too_few_regions_for_stitch_floor():
    # need >= min_stitch_edges distinct new regions to satisfy invariant 1
    with pytest.raises(ValueError, match="new_regions_per_expansion lower bound"):
        JaquaysConfig(min_stitch_edges=4, new_regions_per_expansion=(2, 5)).validate()


def test_validate_rejects_nonpositive_attempts():
    with pytest.raises(ValueError, match="max_reroll_attempts must be >= 1"):
        JaquaysConfig(max_reroll_attempts=0).validate()


def test_validate_passes_for_defaults():
    JaquaysConfig().validate()  # no raise


def test_expansion_generation_error_lists_failing_invariants():
    err = ExpansionGenerationError(
        expansion_id=7,
        attempts=64,
        failing=["min_shortcut_edges", "no_single_chokepoint"],
    )
    msg = str(err)
    assert "expansion 7" in msg
    assert "64 attempts" in msg
    assert "min_shortcut_edges" in msg and "no_single_chokepoint" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement config + errors**

```python
# sidequest-server/sidequest/dungeon/region_graph/errors.py
"""Loud failure for the region-graph generator (CLAUDE.md: No Silent Fallbacks)."""

from __future__ import annotations


class ExpansionGenerationError(RuntimeError):
    """Raised when the re-roll loop cannot satisfy the Jaquays invariants."""

    def __init__(
        self, *, expansion_id: int, attempts: int, failing: list[str]
    ) -> None:
        self.expansion_id = expansion_id
        self.attempts = attempts
        self.failing = failing
        super().__init__(
            f"could not generate a Jaquays-valid expansion {expansion_id} "
            f"after {attempts} attempts; "
            f"last failing invariants: {', '.join(failing)}"
        )
```

```python
# sidequest-server/sidequest/dungeon/region_graph/config.py
"""Tunable Jaquays thresholds + burst knobs (spec §5.1, all tunable in world config).

The integer fields are the *floors* (hard minimums). connection_burst drives
the actual counts well above the floors so a new area "pops in" wired into
many existing regions at once (spec decision 11a, §5.1 "Burst, not minimum").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JaquaysConfig:
    min_stitch_edges: int = 2
    min_loops_into_explored: int = 1
    min_hidden_edges: int = 1
    min_shortcut_edges: int = 1
    min_shortcut_gain: int = 3
    connection_burst: int = 3
    new_regions_per_expansion: tuple[int, int] = (3, 6)
    max_reroll_attempts: int = 64
    edge_kinds: tuple[str, ...] = (
        "corridor",
        "stairs",
        "shaft",
        "chute",
        "secret",
    )

    def validate(self) -> None:
        if not self.edge_kinds:
            raise ValueError("edge_kinds must be non-empty")
        if "secret" not in self.edge_kinds:
            raise ValueError(
                "edge_kinds must include 'secret' (needed for hidden edges)"
            )
        for name in (
            "min_stitch_edges",
            "min_loops_into_explored",
            "min_hidden_edges",
            "min_shortcut_edges",
        ):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be >= 1")
        if self.min_shortcut_gain < 1:
            raise ValueError("min_shortcut_gain must be >= 1")
        if self.connection_burst < 0:
            raise ValueError("connection_burst must be >= 0")
        if self.max_reroll_attempts < 1:
            raise ValueError("max_reroll_attempts must be >= 1")
        lo, hi = self.new_regions_per_expansion
        if lo < 1 or hi < lo:
            raise ValueError(
                f"new_regions_per_expansion must be (lo>=1, hi>=lo); "
                f"got {self.new_regions_per_expansion}"
            )
        if lo < self.min_stitch_edges:
            raise ValueError(
                "new_regions_per_expansion lower bound must be "
                ">= min_stitch_edges (need that many distinct new regions "
                "to form independent entries)"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_config.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/config.py sidequest/dungeon/region_graph/errors.py tests/dungeon/region_graph/test_config.py
git commit -m "feat(dungeon): JaquaysConfig spec-default thresholds + loud ExpansionGenerationError"
```

---

### Task 3: Jaquays invariant checker

Implements the five §5.1 post-conditions exactly, by counting + BFS — no fragile cycle enumeration.

**The five invariants (and how each is checked):**

1. `two_independent_entries` — `len(stitch_edges) >= min_stitch_edges` **and** stitch edges touch `>= min_stitch_edges` distinct *new* regions **and** (for non-seed expansions) `>= 2` distinct *explored* regions. Seed expansion (explored == `{entrance}`): the distinct-explored rule is waived; instead require `>= 2` distinct new regions edged directly to the entrance.
2. `loop_into_explored` — with explored connected (asserted), contracting explored to one vertex gives `len(stitch_edges) - 1` independent cycles, each necessarily through explored **and** a new region. So `loops_into_explored = max(0, len(stitch_edges) - 1) >= min_loops_into_explored`. (Exact; proof sketch in the module docstring.)
3. `mixed_kinds_with_hidden` — expansion edges use `>= 2` distinct `kind` values; every kind is in `config.edge_kinds`; `>= min_hidden_edges` edges have `hidden=True`.
4. `shortcut_collapses_distance` — `>= min_shortcut_edges` edges with `shortcut=True` where deleting that single edge raises some region's BFS distance to the entrance by `>= min_shortcut_gain` (unreachable counts as infinite gain).
5. `no_single_entrance` — every new region has post-attach `degree >= 2`.

Plus `no_single_chokepoint` (the "no single chokepoint into new territory" half of §5.1 invariant 1, checked as its own line): post-attach, removing any single non-entrance node leaves every new region reachable from the entrance — except a node whose removal only severs *its own* downstream new subtree is allowed (that is internal tree shape, not a boundary chokepoint); operationally we require that **no explored region and no stitched new region** is a cut vertex isolating the whole expansion. Concretely: for every node `v` that is an endpoint of a stitch edge, `bfs` from entrance with `v` blocked still reaches `>= 1` new region. (With `>= 2` independent stitch endpoints this holds; the check makes it explicit and catches builder regressions.)

**Files:**
- Create: `sidequest-server/sidequest/dungeon/region_graph/invariants.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_invariants.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/region_graph/test_invariants.py
from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.invariants import check_invariants
from sidequest.dungeon.region_graph.model import (
    Expansion,
    RegionEdge,
    RegionGraph,
    RegionNode,
)


def _explored() -> RegionGraph:
    """surface — e1 — e2, all explored, connected."""
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="threshold"))
    g.add_node(RegionNode(id="e1", expansion_id=1, theme="crypt"))
    g.add_node(RegionNode(id="e2", expansion_id=1, theme="crypt"))
    g.add_edge(RegionEdge(a="surface", b="e1", kind="corridor"))
    g.add_edge(RegionEdge(a="e1", b="e2", kind="corridor"))
    g.add_edge(RegionEdge(a="surface", b="e2", kind="stairs"))  # explored loop
    return g


def _good_expansion() -> Expansion:
    nodes = [
        RegionNode(id="x.r0", expansion_id=2, theme="vault"),
        RegionNode(id="x.r1", expansion_id=2, theme="vault"),
        RegionNode(id="x.r2", expansion_id=2, theme="vault"),
    ]
    edges = [
        # internal tree
        RegionEdge(a="x.r0", b="x.r1", kind="corridor"),
        RegionEdge(a="x.r1", b="x.r2", kind="corridor"),
        # stitches: 2 distinct new (r0,r1) -> 2 distinct explored (e1,e2)
        RegionEdge(a="e1", b="x.r0", kind="corridor"),
        RegionEdge(a="e2", b="x.r1", kind="stairs"),
        # hidden / mixed kind
        RegionEdge(a="e1", b="x.r2", kind="secret", hidden=True),
        # shortcut: deep new r2 back to entrance-adjacent surface
        RegionEdge(a="surface", b="x.r2", kind="shaft", shortcut=True),
    ]
    return Expansion(expansion_id=2, new_nodes=nodes, new_edges=edges)


def test_good_expansion_passes_all_invariants():
    rep = check_invariants(_explored(), _good_expansion(), JaquaysConfig())
    assert rep.all_passed(), rep.invariants_passed
    assert rep.stitch_edges >= 2
    assert rep.loops_into_explored >= 1
    assert rep.hidden_edges >= 1
    assert rep.shortcut_edges >= 1
    assert rep.new_regions == 3


def test_single_stitch_fails_two_independent_entries_and_loop():
    exp = _good_expansion()
    exp.new_edges = [
        RegionEdge(a="x.r0", b="x.r1", kind="corridor"),
        RegionEdge(a="x.r1", b="x.r2", kind="corridor"),
        RegionEdge(a="e1", b="x.r0", kind="corridor"),  # ONLY one stitch
        RegionEdge(a="e1", b="x.r2", kind="secret", hidden=True),
        RegionEdge(a="surface", b="x.r2", kind="shaft", shortcut=True),
    ]
    rep = check_invariants(_explored(), exp, JaquaysConfig())
    assert rep.invariants_passed["two_independent_entries"] is False
    assert rep.invariants_passed["loop_into_explored"] is False
    assert not rep.all_passed()


def test_no_hidden_edge_fails_mixed_kinds_with_hidden():
    exp = _good_expansion()
    exp.new_edges = [e for e in exp.new_edges if not e.hidden]
    exp.new_edges.append(RegionEdge(a="e1", b="x.r2", kind="corridor"))
    rep = check_invariants(_explored(), exp, JaquaysConfig())
    assert rep.invariants_passed["mixed_kinds_with_hidden"] is False


def test_missing_shortcut_fails_shortcut_invariant():
    exp = _good_expansion()
    exp.new_edges = [
        e if not e.shortcut else RegionEdge(a=e.a, b=e.b, kind="corridor")
        for e in exp.new_edges
    ]
    rep = check_invariants(_explored(), exp, JaquaysConfig())
    assert rep.invariants_passed["shortcut_collapses_distance"] is False


def test_degree_one_new_region_fails_no_single_entrance():
    nodes = [
        RegionNode(id="x.r0", expansion_id=2, theme="vault"),
        RegionNode(id="x.r1", expansion_id=2, theme="vault"),
        RegionNode(id="x.lonely", expansion_id=2, theme="vault"),
    ]
    edges = [
        RegionEdge(a="e1", b="x.r0", kind="corridor"),
        RegionEdge(a="e2", b="x.r1", kind="stairs"),
        RegionEdge(a="x.r0", b="x.r1", kind="corridor"),
        RegionEdge(a="x.r0", b="x.lonely", kind="corridor"),  # degree 1
        RegionEdge(a="e1", b="x.r1", kind="secret", hidden=True),
        RegionEdge(a="surface", b="x.r1", kind="shaft", shortcut=True),
    ]
    exp = Expansion(expansion_id=2, new_nodes=nodes, new_edges=edges)
    rep = check_invariants(_explored(), exp, JaquaysConfig())
    assert rep.invariants_passed["no_single_entrance"] is False


def test_seed_expansion_waives_distinct_explored_rule():
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="threshold"))
    nodes = [
        RegionNode(id="s.r0", expansion_id=1, theme="crypt"),
        RegionNode(id="s.r1", expansion_id=1, theme="crypt"),
        RegionNode(id="s.r2", expansion_id=1, theme="crypt"),
    ]
    edges = [
        RegionEdge(a="surface", b="s.r0", kind="corridor"),  # 2 indep ways down
        RegionEdge(a="surface", b="s.r1", kind="stairs"),
        RegionEdge(a="s.r0", b="s.r1", kind="corridor"),
        RegionEdge(a="s.r1", b="s.r2", kind="corridor"),
        RegionEdge(a="s.r0", b="s.r2", kind="secret", hidden=True),
        RegionEdge(a="surface", b="s.r2", kind="shaft", shortcut=True),
    ]
    exp = Expansion(expansion_id=1, new_nodes=nodes, new_edges=edges)
    rep = check_invariants(g, exp, JaquaysConfig())
    assert rep.all_passed(), rep.invariants_passed


def test_report_is_serialisable_dict_for_otel_handoff():
    rep = check_invariants(_explored(), _good_expansion(), JaquaysConfig())
    d = rep.as_dict()
    assert d["expansion_id"] == 2
    assert set(d["invariants_passed"]) == {
        "two_independent_entries",
        "loop_into_explored",
        "mixed_kinds_with_hidden",
        "shortcut_collapses_distance",
        "no_single_entrance",
        "no_single_chokepoint",
    }
    assert isinstance(d["stitch_edges"], int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_invariants.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the checker**

```python
# sidequest-server/sidequest/dungeon/region_graph/invariants.py
"""Jaquays invariant checker (spec §5.1) — exact, by counting + BFS.

Why no cycle enumeration: with the already-explored map connected
(maintained on every attach; seed expansion special-cased), contract
explored to a single vertex X. The new regions hang off X via the
stitch edges. A vertex X with k incident edges into an otherwise
acyclic structure contributes exactly k-1 independent fundamental
cycles, and every one of those cycles passes through X (= explored)
and through >= 1 new region. Hence:

    loops_into_explored == max(0, len(stitch_edges) - 1)

is exact and needs no DFS. All other invariants are degree / distinct
counts / BFS-distance deltas — also exact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.model import Expansion, RegionGraph

_INVARIANTS = (
    "two_independent_entries",
    "loop_into_explored",
    "mixed_kinds_with_hidden",
    "shortcut_collapses_distance",
    "no_single_entrance",
    "no_single_chokepoint",
)


@dataclass
class GenerationReport:
    """Span-ready data contract — Plan 7's materializer turns this into
    `dungeon.materialize.design` OTEL attributes."""

    expansion_id: int
    attempts: int = 1
    stitch_edges: int = 0
    loops_into_explored: int = 0
    hidden_edges: int = 0
    shortcut_edges: int = 0
    new_regions: int = 0
    invariants_passed: dict[str, bool] = field(default_factory=dict)

    def all_passed(self) -> bool:
        return bool(self.invariants_passed) and all(
            self.invariants_passed.values()
        )

    def failing(self) -> list[str]:
        return [k for k, ok in self.invariants_passed.items() if not ok]

    def as_dict(self) -> dict:
        return {
            "expansion_id": self.expansion_id,
            "attempts": self.attempts,
            "stitch_edges": self.stitch_edges,
            "loops_into_explored": self.loops_into_explored,
            "hidden_edges": self.hidden_edges,
            "shortcut_edges": self.shortcut_edges,
            "new_regions": self.new_regions,
            "invariants_passed": dict(self.invariants_passed),
        }


def _post_attach_graph(explored: RegionGraph, exp: Expansion) -> RegionGraph:
    """A throwaway copy of explored with the expansion applied (for checks)."""
    g = RegionGraph(entrance_id=explored.entrance_id)
    for n in explored.nodes.values():
        g.add_node(n)
    for n in exp.new_nodes:
        g.add_node(n)
    for e in list(explored.edges):
        g.edges.append(e)
    for e in exp.new_edges:
        g.add_edge(e)  # validates endpoints loudly
    return g


def check_invariants(
    explored: RegionGraph,
    exp: Expansion,
    config: JaquaysConfig,
) -> GenerationReport:
    config.validate()
    new_ids = exp.new_region_ids()
    explored_ids = set(explored.nodes)
    is_seed = explored_ids == {explored.entrance_id}

    stitch = [
        e
        for e in exp.new_edges
        if len(e.endpoints() & new_ids) == 1
        and len(e.endpoints() & explored_ids) == 1
    ]
    stitch_new_endpoints = {
        next(iter(e.endpoints() & new_ids)) for e in stitch
    }
    stitch_explored_endpoints = {
        next(iter(e.endpoints() & explored_ids)) for e in stitch
    }

    post = _post_attach_graph(explored, exp)

    rep = GenerationReport(expansion_id=exp.expansion_id)
    rep.new_regions = len(exp.new_nodes)
    rep.stitch_edges = len(stitch)
    rep.loops_into_explored = max(0, len(stitch) - 1)
    rep.hidden_edges = sum(1 for e in exp.new_edges if e.hidden)

    # 1. two independent entries / no single chokepoint
    enough_stitch = len(stitch) >= config.min_stitch_edges
    enough_new = len(stitch_new_endpoints) >= config.min_stitch_edges
    if is_seed:
        entrance_links = {
            next(iter(e.endpoints() & new_ids))
            for e in stitch
            if explored.entrance_id in e.endpoints()
        }
        explored_ok = len(entrance_links) >= 2
    else:
        explored_ok = len(stitch_explored_endpoints) >= 2
    rep.invariants_passed["two_independent_entries"] = (
        enough_stitch and enough_new and explored_ok
    )

    # 2. loop tying back into explored (exact, see module docstring)
    rep.invariants_passed["loop_into_explored"] = (
        rep.loops_into_explored >= config.min_loops_into_explored
    )

    # 3. mix of connection types + >= 1 non-obvious edge
    kinds = {e.kind for e in exp.new_edges}
    unknown = kinds - set(config.edge_kinds)
    rep.invariants_passed["mixed_kinds_with_hidden"] = (
        not unknown
        and len(kinds) >= 2
        and rep.hidden_edges >= config.min_hidden_edges
    )

    # 4. >= 1 shortcut that collapses distance toward the entrance
    base = post.bfs_dist(post.entrance_id)
    big = len(post.nodes) + 1
    shortcut_hits = 0
    for i, e in enumerate(post.edges):
        if not e.shortcut:
            continue
        alt = post.bfs_dist(post.entrance_id, skip_edges={i})
        gain = max(
            (alt.get(r, big) - base.get(r, big)) for r in post.nodes
        )
        if gain >= config.min_shortcut_gain:
            shortcut_hits += 1
    rep.shortcut_edges = shortcut_hits
    rep.invariants_passed["shortcut_collapses_distance"] = (
        shortcut_hits >= config.min_shortcut_edges
    )

    # 5. no region with only one entrance (new regions)
    rep.invariants_passed["no_single_entrance"] = all(
        post.degree(rid) >= 2 for rid in new_ids
    )

    # no single chokepoint into new territory
    chokepoint_free = True
    for v in stitch_new_endpoints | stitch_explored_endpoints:
        if v == post.entrance_id:
            continue
        reached = set(post.bfs_dist(post.entrance_id, blocked_node=v))
        if not (new_ids - {v}) & reached:
            chokepoint_free = False
            break
    rep.invariants_passed["no_single_chokepoint"] = chokepoint_free

    return rep
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_invariants.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/invariants.py tests/dungeon/region_graph/test_invariants.py
git commit -m "feat(dungeon): exact Jaquays invariant checker + span-ready GenerationReport"
```

---

### Task 4: Sub-seed mixing + candidate builder

`_subseed` uses **blake2b**, not XOR — this pre-empts the Plan 7 carry-forward gotcha (`generate_interior` braid sub-seed `seed ^ 0x5EED` has a fixed point at seed 24301) at the region-graph layer and establishes the good-mix precedent. `_build_candidate` produces raw topology that, by construction, clears the invariants on the first attempt for sane config — the re-roll loop (Task 5) is the safety net, not the primary path.

**Files:**
- Create: `sidequest-server/sidequest/dungeon/region_graph/generator.py` (builder + subseed; loop added in Task 5)
- Test: `sidequest-server/tests/dungeon/region_graph/test_generator.py` (builder cases; loop cases in Task 5)

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/region_graph/test_generator.py
import random

import pytest

from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.generator import _build_candidate, _subseed
from sidequest.dungeon.region_graph.model import RegionGraph, RegionNode

THEMES = ["crypt", "vault", "flooded", "catacomb"]


def _explored() -> RegionGraph:
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="threshold"))
    for i in range(4):
        g.add_node(RegionNode(id=f"e{i}", expansion_id=1, theme="crypt"))
    g.add_edge_pair = None  # noqa: documentation marker only
    g.edges.extend(g.edges)  # no-op; explicit edges below
    import itertools

    chain = ["surface", "e0", "e1", "e2", "e3"]
    from sidequest.dungeon.region_graph.model import RegionEdge

    for a, b in itertools.pairwise(chain):
        g.add_edge(RegionEdge(a=a, b=b, kind="corridor"))
    g.add_edge(RegionEdge(a="surface", b="e3", kind="stairs"))  # explored loop
    return g


def test_subseed_is_deterministic_and_wide():
    s1 = _subseed(123, 4, 0)
    s2 = _subseed(123, 4, 0)
    assert s1 == s2
    assert s1 != _subseed(123, 4, 1)
    assert s1 != _subseed(124, 4, 0)
    assert 0 <= s1 < 2**64


def test_subseed_has_no_xor_fixed_point_regression():
    """Plan 7 carry-forward: `seed ^ 0x5EED` collides at 24301.
    blake2b mixing must not reproduce that class of fixed point."""
    bad = 0x5EED  # 24301
    seeds = {_subseed(bad, e, 0) for e in range(50)}
    assert len(seeds) == 50  # all distinct, none zeroed
    assert all(s != 0 for s in seeds)
    assert _subseed(bad, 0, 0) != _subseed(0, 0, 0)


def test_build_candidate_is_deterministic():
    g = _explored()
    cfg = JaquaysConfig()
    a = _build_candidate(
        g, expansion_id=2, attach_region_ids=["e2", "e3"],
        theme_pool=THEMES, config=cfg, rng=random.Random(_subseed(7, 2, 0)),
    )
    b = _build_candidate(
        g, expansion_id=2, attach_region_ids=["e2", "e3"],
        theme_pool=THEMES, config=cfg, rng=random.Random(_subseed(7, 2, 0)),
    )
    assert [n.id for n in a.new_nodes] == [n.id for n in b.new_nodes]
    assert [(e.a, e.b, e.kind, e.hidden, e.shortcut) for e in a.new_edges] == [
        (e.a, e.b, e.kind, e.hidden, e.shortcut) for e in b.new_edges
    ]


def test_build_candidate_shapes_within_config_bounds():
    g = _explored()
    cfg = JaquaysConfig()
    exp = _build_candidate(
        g, expansion_id=2, attach_region_ids=["e2", "e3"],
        theme_pool=THEMES, config=cfg, rng=random.Random(_subseed(1, 2, 0)),
    )
    lo, hi = cfg.new_regions_per_expansion
    assert lo <= len(exp.new_nodes) <= hi
    assert all(n.theme in THEMES for n in exp.new_nodes)
    assert all(n.id.startswith("exp002.") for n in exp.new_nodes)
    stitch = [
        e for e in exp.new_edges
        if len({e.a, e.b} & {n.id for n in exp.new_nodes}) == 1
    ]
    assert len(stitch) >= cfg.min_stitch_edges
    assert any(e.hidden for e in exp.new_edges)
    assert any(e.shortcut for e in exp.new_edges)


@pytest.mark.parametrize("burst", [0, 3, 8])
def test_higher_burst_yields_more_stitch_on_average(burst):
    g = _explored()
    cfg = JaquaysConfig(connection_burst=burst)
    total = 0
    for seed in range(40):
        exp = _build_candidate(
            g, expansion_id=2, attach_region_ids=["e1", "e2", "e3"],
            theme_pool=THEMES, config=cfg,
            rng=random.Random(_subseed(seed, 2, 0)),
        )
        total += sum(
            1 for e in exp.new_edges
            if len({e.a, e.b} & {n.id for n in exp.new_nodes}) == 1
        )
    # store on the function for the cross-burst comparison below
    test_higher_burst_yields_more_stitch_on_average.samples = getattr(
        test_higher_burst_yields_more_stitch_on_average, "samples", {}
    )
    test_higher_burst_yields_more_stitch_on_average.samples[burst] = total
    s = test_higher_burst_yields_more_stitch_on_average.samples
    if {0, 3, 8} <= set(s):
        assert s[0] < s[3] < s[8]


def test_attach_region_ids_must_be_explored_for_non_seed():
    g = _explored()
    with pytest.raises(ValueError, match="attach region 'nope' is not explored"):
        _build_candidate(
            g, expansion_id=2, attach_region_ids=["nope"],
            theme_pool=THEMES, config=JaquaysConfig(),
            rng=random.Random(1),
        )


def test_non_seed_requires_two_attach_regions():
    g = _explored()
    with pytest.raises(ValueError, match="needs >= 2 distinct attach regions"):
        _build_candidate(
            g, expansion_id=2, attach_region_ids=["e1"],
            theme_pool=THEMES, config=JaquaysConfig(),
            rng=random.Random(1),
        )


def test_empty_theme_pool_raises_loudly():
    g = _explored()
    with pytest.raises(ValueError, match="theme_pool must be non-empty"):
        _build_candidate(
            g, expansion_id=2, attach_region_ids=["e2", "e3"],
            theme_pool=[], config=JaquaysConfig(),
            rng=random.Random(1),
        )
```

> Note: the `g.add_edge_pair`/`g.edges.extend` lines in `_explored()` are inert scaffolding kept only so the helper reads identically across test files; the implementer may simplify the helper as long as the produced graph (surface—e0—e1—e2—e3 chain plus a surface—e3 stairs loop) is unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -v`
Expected: FAIL — `ImportError: cannot import name '_build_candidate'`

- [ ] **Step 3: Implement subseed + builder**

```python
# sidequest-server/sidequest/dungeon/region_graph/generator.py
"""Stage-1 expansion generation: collision-resistant sub-seeding,
candidate topology builder, re-roll loop (Task 5), attach (Task 6).

Sub-seeding uses blake2b, NOT XOR. The Plan 7 carry-forward records
that `generate_interior`'s braid sub-seed `seed ^ 0x5EED` has a
fixed point at seed 24301; we refuse to reproduce that class of bug
in the region-graph layer.
"""

from __future__ import annotations

import hashlib
import random

from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.model import (
    Expansion,
    RegionEdge,
    RegionGraph,
    RegionNode,
)


def _subseed(campaign_seed: int, expansion_id: int, attempt: int) -> int:
    digest = hashlib.blake2b(
        f"{campaign_seed}|{expansion_id}|{attempt}".encode(),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def _pick_distinct(rng: random.Random, pool: list[str], k: int) -> list[str]:
    if k >= len(pool):
        out = list(pool)
        rng.shuffle(out)
        return out
    return rng.sample(pool, k)


def _build_candidate(
    explored: RegionGraph,
    *,
    expansion_id: int,
    attach_region_ids: list[str],
    theme_pool: list[str],
    config: JaquaysConfig,
    rng: random.Random,
) -> Expansion:
    config.validate()
    if not theme_pool:
        raise ValueError("theme_pool must be non-empty")

    is_seed = set(explored.nodes) == {explored.entrance_id}
    for rid in attach_region_ids:
        if rid not in explored.nodes:
            raise ValueError(f"attach region {rid!r} is not explored")
    if is_seed:
        attach = [explored.entrance_id]
    else:
        attach = sorted(set(attach_region_ids))
        if len(attach) < 2:
            raise ValueError(
                f"expansion {expansion_id} needs >= 2 distinct attach "
                f"regions (no single chokepoint); got {attach_region_ids}"
            )

    lo, hi = config.new_regions_per_expansion
    n = rng.randint(lo, hi)
    nodes = [
        RegionNode(
            id=f"exp{expansion_id:03d}.r{i}",
            expansion_id=expansion_id,
            theme=rng.choice(theme_pool),
        )
        for i in range(n)
    ]
    new_ids = [x.id for x in nodes]
    edges: list[RegionEdge] = []

    # 1. internal spanning tree over the new regions (random parent),
    #    guarantees the expansion is internally connected.
    for i in range(1, n):
        parent = new_ids[rng.randrange(i)]
        edges.append(
            RegionEdge(a=parent, b=new_ids[i], kind="corridor")
        )

    # 2. stitch edges: floor + burst jitter, well above the minimum.
    stitch_count = config.min_stitch_edges + rng.randint(
        0, config.connection_burst
    )
    stitch_count = max(stitch_count, config.min_stitch_edges)
    # >= min_stitch_edges distinct new endpoints
    new_targets = _pick_distinct(
        rng, list(new_ids), min(len(new_ids), stitch_count)
    )
    while len(new_targets) < stitch_count:
        new_targets.append(new_ids[rng.randrange(len(new_ids))])
    if is_seed:
        explored_sources = [explored.entrance_id] * stitch_count
    else:
        base = _pick_distinct(rng, attach, min(len(attach), stitch_count))
        while len(base) < stitch_count:
            base.append(attach[rng.randrange(len(attach))])
        explored_sources = base
        # force >= 2 DISTINCT explored endpoints
        if len(set(explored_sources[: stitch_count])) < 2 and len(attach) >= 2:
            explored_sources[1] = next(
                a for a in attach if a != explored_sources[0]
            )
    non_corridor = [k for k in config.edge_kinds if k != "corridor"]
    for j in range(stitch_count):
        kind = "corridor" if j == 0 else rng.choice(config.edge_kinds)
        edges.append(
            RegionEdge(
                a=explored_sources[j],
                b=new_targets[j],
                kind=kind,
            )
        )

    # 3. hidden (non-obvious) edges: >= min_hidden_edges, kind 'secret'.
    for _ in range(config.min_hidden_edges):
        a = rng.choice(attach if not is_seed else [explored.entrance_id])
        b = rng.choice(new_ids)
        edges.append(RegionEdge(a=a, b=b, kind="secret", hidden=True))

    # 4. shortcut: deepest new region -> the explored region closest to
    #    the entrance, via a vertical-ish kind, marked shortcut.
    dist_from_entrance = explored.bfs_dist(explored.entrance_id)
    nearest = min(
        (explored.entrance_id, *attach),
        key=lambda r: dist_from_entrance.get(r, 0),
    )
    # deepest new region == last one added to the internal tree
    deep_new = new_ids[-1]
    shortcut_kind = rng.choice(
        [k for k in ("shaft", "chute", "stairs", "secret")
         if k in config.edge_kinds]
        or list(config.edge_kinds)
    )
    for _ in range(config.min_shortcut_edges):
        edges.append(
            RegionEdge(
                a=nearest,
                b=deep_new,
                kind=shortcut_kind,
                hidden=(shortcut_kind == "secret"),
                shortcut=True,
            )
        )

    # 5. extra internal loop edges scaled by burst (interior richness).
    for _ in range(rng.randint(0, config.connection_burst)):
        if n >= 2:
            x, y = rng.sample(new_ids, 2)
            edges.append(RegionEdge(a=x, b=y, kind="corridor"))

    # ensure >= 2 distinct kinds even on a tiny config
    if len({e.kind for e in edges}) < 2 and non_corridor:
        edges.append(
            RegionEdge(
                a=(attach[0] if not is_seed else explored.entrance_id),
                b=new_ids[0],
                kind=non_corridor[0],
            )
        )

    return Expansion(
        expansion_id=expansion_id, new_nodes=nodes, new_edges=edges
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/generator.py tests/dungeon/region_graph/test_generator.py
git commit -m "feat(dungeon): blake2b sub-seeding + burst-aware candidate builder"
```

---

### Task 5: Re-roll loop — `generate_expansion`

Generate → check → re-roll with the next sub-seed until all invariants pass; fail loudly after `max_reroll_attempts` with the failing invariants from the last report.

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/generator.py` (append `generate_expansion`)
- Test: `sidequest-server/tests/dungeon/region_graph/test_generator.py` (append)

- [ ] **Step 1: Write the failing test (append to test_generator.py)**

```python
# append to sidequest-server/tests/dungeon/region_graph/test_generator.py
from sidequest.dungeon.region_graph.errors import ExpansionGenerationError
from sidequest.dungeon.region_graph.generator import generate_expansion
from sidequest.dungeon.region_graph.invariants import check_invariants


def test_generate_expansion_returns_valid_expansion_and_report():
    g = _explored()
    exp, rep = generate_expansion(
        graph=g, campaign_seed=42, expansion_id=2,
        attach_region_ids=["e2", "e3"], theme_pool=THEMES,
        config=JaquaysConfig(),
    )
    assert rep.all_passed()
    assert rep.attempts >= 1
    # the returned report agrees with an independent re-check
    recheck = check_invariants(g, exp, JaquaysConfig())
    assert recheck.all_passed()


def test_generate_expansion_is_deterministic():
    g = _explored()
    e1, r1 = generate_expansion(
        graph=g, campaign_seed=99, expansion_id=5,
        attach_region_ids=["e1", "e3"], theme_pool=THEMES,
        config=JaquaysConfig(),
    )
    e2, r2 = generate_expansion(
        graph=g, campaign_seed=99, expansion_id=5,
        attach_region_ids=["e1", "e3"], theme_pool=THEMES,
        config=JaquaysConfig(),
    )
    assert [n.id for n in e1.new_nodes] == [n.id for n in e2.new_nodes]
    assert r1.attempts == r2.attempts
    assert [(e.a, e.b, e.kind) for e in e1.new_edges] == [
        (e.a, e.b, e.kind) for e in e2.new_edges
    ]


def test_impossible_config_fails_loudly_with_failing_invariants():
    g = _explored()
    # min_shortcut_gain unreachable: demand a 999-room distance collapse
    cfg = JaquaysConfig(min_shortcut_gain=999, max_reroll_attempts=4)
    with pytest.raises(ExpansionGenerationError) as ei:
        generate_expansion(
            graph=g, campaign_seed=1, expansion_id=2,
            attach_region_ids=["e2", "e3"], theme_pool=THEMES, config=cfg,
        )
    assert ei.value.expansion_id == 2
    assert ei.value.attempts == 4
    assert "shortcut_collapses_distance" in ei.value.failing


@pytest.mark.parametrize("campaign_seed", [0x5EED, 24301, 0, 1, 7, 999999])
def test_known_tricky_seeds_still_generate(campaign_seed):
    """0x5EED == 24301 is the Plan 7 XOR fixed point; must be fine here."""
    g = _explored()
    exp, rep = generate_expansion(
        graph=g, campaign_seed=campaign_seed, expansion_id=3,
        attach_region_ids=["e1", "e2", "e3"], theme_pool=THEMES,
        config=JaquaysConfig(),
    )
    assert rep.all_passed()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -k generate_expansion -v`
Expected: FAIL — `ImportError: cannot import name 'generate_expansion'`

- [ ] **Step 3: Append `generate_expansion` to generator.py**

```python
# append to sidequest-server/sidequest/dungeon/region_graph/generator.py
from sidequest.dungeon.region_graph.errors import ExpansionGenerationError
from sidequest.dungeon.region_graph.invariants import (
    GenerationReport,
    check_invariants,
)


def generate_expansion(
    *,
    graph: RegionGraph,
    campaign_seed: int,
    expansion_id: int,
    attach_region_ids: list[str],
    theme_pool: list[str],
    config: JaquaysConfig | None = None,
) -> tuple[Expansion, GenerationReport]:
    """Generate one Jaquays-valid expansion. Deterministic for identical
    inputs (pre-curation). Raises ExpansionGenerationError loudly if no
    attempt within config.max_reroll_attempts satisfies the invariants
    (CLAUDE.md: No Silent Fallbacks)."""
    cfg = config or JaquaysConfig()
    cfg.validate()
    last: GenerationReport | None = None
    for attempt in range(cfg.max_reroll_attempts):
        rng = random.Random(_subseed(campaign_seed, expansion_id, attempt))
        candidate = _build_candidate(
            graph,
            expansion_id=expansion_id,
            attach_region_ids=attach_region_ids,
            theme_pool=theme_pool,
            config=cfg,
            rng=rng,
        )
        report = check_invariants(graph, candidate, cfg)
        report.attempts = attempt + 1
        if report.all_passed():
            return candidate, report
        last = report
    raise ExpansionGenerationError(
        expansion_id=expansion_id,
        attempts=cfg.max_reroll_attempts,
        failing=last.failing() if last else list(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -v`
Expected: PASS (all generator tests, including the Task 4 set)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/generator.py tests/dungeon/region_graph/test_generator.py
git commit -m "feat(dungeon): re-roll loop generate_expansion — loud on exhaustion"
```

---

### Task 6: `attach_expansion` + incremental global checks

Mutates the contiguous map and re-verifies the **global** post-conditions (§8 "incremental global-loop check on attach"): the whole map stays connected (solvability, §11) and loopful (cyclomatic ≥ 1 once past the seed, never decreasing). Raises loudly on violation — defence in depth; `generate_expansion` should already guarantee it.

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/generator.py` (append `attach_expansion`)
- Test: `sidequest-server/tests/dungeon/region_graph/test_generator.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
# append to sidequest-server/tests/dungeon/region_graph/test_generator.py
from sidequest.dungeon.region_graph.generator import attach_expansion
from sidequest.dungeon.region_graph.model import Expansion, RegionEdge, RegionNode


def test_attach_mutates_graph_keeps_connected_and_loopful():
    g = _explored()
    pre_cyc = g.cyclomatic_number()
    exp, _ = generate_expansion(
        graph=g, campaign_seed=3, expansion_id=2,
        attach_region_ids=["e2", "e3"], theme_pool=THEMES,
        config=JaquaysConfig(),
    )
    attach_expansion(g, exp)
    assert exp.new_region_ids() <= set(g.nodes)
    assert g.is_connected()
    assert g.cyclomatic_number() >= max(1, pre_cyc)


def test_attach_rejects_disconnecting_expansion_loudly():
    g = _explored()
    floating = Expansion(
        expansion_id=9,
        new_nodes=[
            RegionNode(id="f0", expansion_id=9, theme="vault"),
            RegionNode(id="f1", expansion_id=9, theme="vault"),
        ],
        new_edges=[RegionEdge(a="f0", b="f1", kind="corridor")],  # no stitch
    )
    import pytest

    with pytest.raises(ValueError, match="attach left the map disconnected"):
        attach_expansion(g, floating)


def test_attach_rejects_unknown_stitch_endpoint_loudly():
    g = _explored()
    bad = Expansion(
        expansion_id=9,
        new_nodes=[RegionNode(id="b0", expansion_id=9, theme="vault")],
        new_edges=[RegionEdge(a="ghost", b="b0", kind="corridor")],
    )
    import pytest

    with pytest.raises(ValueError, match="not a known region"):
        attach_expansion(g, bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -k attach -v`
Expected: FAIL — `ImportError: cannot import name 'attach_expansion'`

- [ ] **Step 3: Append `attach_expansion` to generator.py**

```python
# append to sidequest-server/sidequest/dungeon/region_graph/generator.py
def attach_expansion(graph: RegionGraph, exp: Expansion) -> RegionGraph:
    """Apply an expansion to the contiguous map, then re-verify the
    global invariants (connected + loopful). Raises loudly on violation
    (CLAUDE.md: No Silent Fallbacks). Returns the same (mutated) graph."""
    pre_cyclomatic = graph.cyclomatic_number()
    pre_node_count = len(graph.nodes)

    for node in exp.new_nodes:
        graph.add_node(node)
    for edge in exp.new_edges:
        graph.add_edge(edge)  # raises on unknown / self-loop endpoints

    if not graph.is_connected():
        raise ValueError(
            f"attach left the map disconnected after expansion "
            f"{exp.expansion_id}: "
            f"{len(graph.reachable_from_entrance())}/{len(graph.nodes)} "
            f"regions reachable from {graph.entrance_id!r}"
        )
    cyc = graph.cyclomatic_number()
    is_first = pre_node_count <= 1
    floor = 1 if (not is_first or exp.new_nodes) else 0
    if cyc < max(floor, pre_cyclomatic):
        raise ValueError(
            f"attach made the map less loopful after expansion "
            f"{exp.expansion_id}: cyclomatic {pre_cyclomatic} -> {cyc} "
            f"(must be a loopful contiguous graph, never a global tree)"
        )
    return graph
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_generator.py -v`
Expected: PASS (all generator tests)

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/generator.py tests/dungeon/region_graph/test_generator.py
git commit -m "feat(dungeon): attach_expansion with incremental global loop/solvability check"
```

---

### Task 7: Public API + deep-chain property sweep

Finalise the package public surface and add the property/integration test that runs a deep expansion chain across a seed sweep, asserting **every** §5.1 invariant + solvability + loopfulness + determinism + burst monotonicity hold on every attach (spec §10 step 2 "property-tested against every invariant", §11). This is the strongest wiring proof available at the library layer (the public API exercised end-to-end through a realistic multi-expansion campaign); the mandatory production session-path wiring test is Plan 7's, per the scope-boundary table.

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/__init__.py` (public re-exports)
- Test: `sidequest-server/tests/dungeon/region_graph/test_chain.py`

- [ ] **Step 1: Write the failing test**

```python
# sidequest-server/tests/dungeon/region_graph/test_chain.py
import pytest

from sidequest.dungeon.region_graph import (
    JaquaysConfig,
    RegionGraph,
    RegionNode,
    attach_expansion,
    check_invariants,
    generate_expansion,
)

THEMES = ["crypt", "vault", "flooded", "catacomb", "undercity"]


def _seed_graph() -> RegionGraph:
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="threshold"))
    return g


def _grow(campaign_seed: int, depth: int, cfg: JaquaysConfig) -> RegionGraph:
    g = _seed_graph()
    frontier = ["surface"]
    for eid in range(depth):
        attach_ids = (
            ["surface"]
            if set(g.nodes) == {"surface"}
            else sorted(frontier)[-3:]
        )
        exp, rep = generate_expansion(
            graph=g, campaign_seed=campaign_seed, expansion_id=eid,
            attach_region_ids=attach_ids, theme_pool=THEMES, config=cfg,
        )
        assert rep.all_passed(), (eid, rep.failing())
        attach_expansion(g, exp)
        frontier = sorted(exp.new_region_ids())
    return g


@pytest.mark.parametrize("campaign_seed", range(40))
def test_deep_chain_holds_every_invariant(campaign_seed):
    cfg = JaquaysConfig()
    g = _seed_graph()
    frontier = ["surface"]
    for eid in range(15):
        attach_ids = (
            ["surface"]
            if set(g.nodes) == {"surface"}
            else sorted(frontier)[-3:]
        )
        pre_cyc = g.cyclomatic_number()
        exp, rep = generate_expansion(
            graph=g, campaign_seed=campaign_seed, expansion_id=eid,
            attach_region_ids=attach_ids, theme_pool=THEMES, config=cfg,
        )
        # invariant report agrees with an independent re-check
        assert check_invariants(g, exp, cfg).all_passed()
        attach_expansion(g, exp)
        assert g.is_connected()                       # solvability §11
        assert g.cyclomatic_number() >= max(1, pre_cyc)  # loopful, monotone
        frontier = sorted(exp.new_region_ids())
    # no floor-indexed ids anywhere (spec: keyed by expansion id, never floor)
    assert all("floor" not in nid for nid in g.nodes)
    assert len(g.nodes) > 15


def test_chain_is_deterministic_pre_curation():
    cfg = JaquaysConfig()
    g1 = _grow(2026, 10, cfg)
    g2 = _grow(2026, 10, cfg)
    assert sorted(g1.nodes) == sorted(g2.nodes)
    assert [(e.a, e.b, e.kind, e.hidden, e.shortcut) for e in g1.edges] == [
        (e.a, e.b, e.kind, e.hidden, e.shortcut) for e in g2.edges
    ]


def test_burst_increases_connection_richness_across_sweep():
    thin = sum(
        len(_grow(s, 8, JaquaysConfig(connection_burst=0)).edges)
        for s in range(15)
    )
    fat = sum(
        len(_grow(s, 8, JaquaysConfig(connection_burst=8)).edges)
        for s in range(15)
    )
    assert fat > thin
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/dungeon/region_graph/test_chain.py -v`
Expected: FAIL — `ImportError: cannot import name 'generate_expansion' from 'sidequest.dungeon.region_graph'`

- [ ] **Step 3: Finalise the public API**

```python
# sidequest-server/sidequest/dungeon/region_graph/__init__.py  (replace contents)
"""Stage-1 region-graph generator + Jaquays invariants (spec: Beneath Sünden §5.1).

One contiguous, edge-expanding map. Each expansion is generated from
(campaign_seed, expansion_id), enforced against the five Jaquays
post-conditions via a re-roll loop, and attached with an incremental
global connectivity + loopfulness check.

Pure, dependency-free, deterministic pre-curation. No persistence, no
themes loader, no depth_score, no OTEL here — see Plan 2's
scope-boundary table; those land in Plans 3/4/5/7.
"""

from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.errors import ExpansionGenerationError
from sidequest.dungeon.region_graph.generator import (
    attach_expansion,
    generate_expansion,
)
from sidequest.dungeon.region_graph.invariants import (
    GenerationReport,
    check_invariants,
)
from sidequest.dungeon.region_graph.model import (
    Expansion,
    RegionEdge,
    RegionGraph,
    RegionNode,
)

__all__ = [
    "JaquaysConfig",
    "ExpansionGenerationError",
    "GenerationReport",
    "Expansion",
    "RegionEdge",
    "RegionGraph",
    "RegionNode",
    "attach_expansion",
    "check_invariants",
    "generate_expansion",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/dungeon/region_graph/test_chain.py -v`
Expected: PASS (40 parametrized + 2 = 42 tests). May take a few seconds — acceptable.

- [ ] **Step 5: Commit**

```bash
git add sidequest/dungeon/region_graph/__init__.py tests/dungeon/region_graph/test_chain.py
git commit -m "feat(dungeon): region_graph public API + deep-chain Jaquays property sweep"
```

---

### Task 8: Full-suite gate + ruff + pyright

**Files:** none new — verification only.

- [ ] **Step 1: Run the full dungeon test suite via testing-runner**

Dispatch the `testing-runner` subagent:
```
REPOS: server
CONTEXT: "Plan 2 region-graph — full GREEN verification"
RUN_ID: "beneath-sunden-plan2-green"
```
It must run: `uv run pytest tests/dungeon -v`
Expected: all `tests/dungeon/region_graph/*` and the pre-existing `tests/dungeon/interiors/*` GREEN (Plan 1 untouched, no regression).

- [ ] **Step 2: Ruff**

Run: `cd /Users/slabgorb/Projects/oq-1/sidequest-server && uv run ruff check sidequest/dungeon/region_graph tests/dungeon/region_graph`
Expected: `All checks passed!` — fix any finding, re-run.

- [ ] **Step 3: Ruff format check**

Run: `uv run ruff format --check sidequest/dungeon/region_graph tests/dungeon/region_graph`
Expected: clean. If it reports reformatting, run `uv run ruff format sidequest/dungeon/region_graph tests/dungeon/region_graph` and re-stage.

- [ ] **Step 4: pyright**

Run: `uv run pyright sidequest/dungeon/region_graph`
Expected: 0 errors. Fix any type finding (no `# type: ignore` without a one-line reason comment).

- [ ] **Step 5: Commit any lint/format/type fixes**

```bash
git add -A sidequest/dungeon/region_graph tests/dungeon/region_graph
git commit -m "chore(dungeon): ruff + pyright clean across region_graph" || echo "nothing to commit — already clean"
```

- [ ] **Step 6: Authoritative commit-clean check, then push**

```bash
git log -5 --format='%h %s' | cat
git log -1 --format=%B | od -c | tail -5   # authoritative no-leak check
git push -u origin feat/beneath-sunden-region-graph
```
Do **not** open the PR — per the Dev workflow, SM creates the PR in the finish phase. Report branch pushed + the deep-chain sweep result.

---

## Self-Review

**1. Spec coverage (every §5.1 / §8 / §10-step-2 / §11 requirement → task):**

| Spec requirement | Task |
|---|---|
| ≥2 independent edges into explored, no single chokepoint | Task 3 (`two_independent_entries`, `no_single_chokepoint`) |
| ≥1 loop tying back into explored | Task 3 (`loop_into_explored`, exact via stitch-1) |
| Mix of connection types + ≥1 non-obvious (secret/conditional) edge | Task 3 (`mixed_kinds_with_hidden`); builder Task 4 |
| ≥1 shortcut edge collapsing distance toward entrance | Task 3 (`shortcut_collapses_distance`); builder Task 4 |
| No region with only one entrance | Task 3 (`no_single_entrance`) |
| Re-roll until pass, fail loud | Task 5 (`generate_expansion` + `ExpansionGenerationError`) |
| Incremental global-loop check on attach (§8) | Task 6 (`attach_expansion`) |
| Connection-burst knob drives count above floors (§5.1, decision 11a) | Task 2 (`connection_burst`), Task 4 builder, Tasks 4/7 monotonicity tests |
| All thresholds tunable in config | Task 2 (`JaquaysConfig`) |
| Determinism pre-curation (§11) | Tasks 4/5/7 determinism tests |
| Solvability — fully traversable after every expansion (§11) | Task 6 + Task 7 chain |
| Property-tested against every invariant across a seed sweep (§10-2, §11) | Task 7 (`test_chain.py`, 40-seed sweep) |
| Keyed by region/expansion id, never floor (decisions 1,2) | id scheme `exp{NNN}.r{i}`; Task 7 asserts no "floor" key |
| Plan 7 carry-forward: no XOR fixed-point sub-seed | Task 4 (`_subseed` blake2b) + regression tests Tasks 4/5 |
| No Silent Fallbacks / fail loud (CLAUDE.md) | Tasks 1,2,4,5,6 loud `ValueError`/`ExpansionGenerationError` |
| OTEL + mandatory production wiring test | **Deferred to Plan 7** — logged in scope-boundary table; `GenerationReport.as_dict()` is the span-ready contract |
| depth_score / themes / persistence / set-pieces | **Deferred to Plans 3/4/5/6** — logged in scope-boundary table |

No spec §5.1/§8/§10-2/§11 requirement is unmapped. Deferrals are explicit and justified, not omissions.

**2. Placeholder scan:** No "TBD"/"implement later"/"add error handling" — every code step is complete runnable code; every test has real assertions. The inert `g.add_edge_pair`/`g.edges.extend` lines in the Task 4 helper are explicitly called out as removable scaffolding with the exact required graph shape stated, so they are not a hidden placeholder.

**3. Type consistency:** `RegionNode(id, expansion_id, theme)`, `RegionEdge(a, b, kind, hidden, shortcut)`, `Expansion(expansion_id, new_nodes, new_edges)` + `.new_region_ids()`, `RegionGraph(entrance_id, nodes, edges)` + `.add_node/.add_edge/.neighbors/.degree/.bfs_dist(skip_edges=,blocked_node=)/.reachable_from_entrance/.is_connected/.cyclomatic_number/._component_count`, `JaquaysConfig` field names, `GenerationReport(expansion_id, attempts, stitch_edges, loops_into_explored, hidden_edges, shortcut_edges, new_regions, invariants_passed)` + `.all_passed()/.failing()/.as_dict()`, `generate_expansion(*, graph, campaign_seed, expansion_id, attach_region_ids, theme_pool, config)`, `attach_expansion(graph, exp)`, `check_invariants(explored, exp, config)`, `_subseed(campaign_seed, expansion_id, attempt)`, `_build_candidate(explored, *, expansion_id, attach_region_ids, theme_pool, config, rng)`, `ExpansionGenerationError(*, expansion_id, attempts, failing)` — used identically across Tasks 1–8. Consistent.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-16-beneath-sunden-plan-2-region-graph-jaquays.md`.

Per the user's directive ("Write + execute Plan 2") and the spec's instruction (execute via superpowers:subagent-driven-development — fresh subagent per task, two-stage spec-then-quality review, feat/* subrepo branch first), execution proceeds **Subagent-Driven**.

---

## Post-Implementation Corrections (2026-05-16)

Executed on `feat/beneath-sunden-region-graph` (HEAD `f461e70`, pushed; 150 tests, pyright 0, ruff clean, purely additive). Review (per-task two-stage + final whole-impl, opus) drove these reconciliations of plan prose vs. shipped code — the **code is authoritative**:

- **`min_shortcut_gain` default is `1`, not `3`.** The plan's `3` against the default `new_regions_per_expansion=(3,6)` was internally inconsistent (a gain-3 collapse is geometrically impossible in a 3-region expansion). The spec specifies no number; `1` still enforces a genuine distance collapse and remains tunable upward. (Task 2/3/4 code + tests reflect `1`.)
- **`stitch` excludes hidden+shortcut cross-edges.** A secret edge is not a reliable independent entry; a shortcut is a discovered bypass — each satisfies its *own* §5.1 invariant, so neither is double-counted toward the ≥2-independent-entries floor. Consequence: `loops_into_explored = max(0,len(stitch)-1)` is a documented **conservative lower bound** (safe for a re-roll post-condition — only ever forces an extra re-roll).
- **`config.validate()` gained a self-consistency rule:** `new_regions lower bound >= min_stitch_edges + min_shortcut_edges`. It deliberately does **not** involve `min_shortcut_gain` (so the Task-5 impossible-config test that forces exhaustion via `min_shortcut_gain=999` still works).
- **Builder emits N *distinct* independently-collapsing shortcuts** (the N deepest un-stitched internal-tree nodes), not N identical parallel edges — fixing a blocking defect (I1) where `min_shortcut_edges>1` was a `validate()`-accepted but structurally-unsatisfiable tunable. Default `min_shortcut_edges=1` path is byte-identical to the original single-shortcut design.
- **Dict key + report field unified to plural `loops_into_explored`**; `_INVARIANTS` is a load-bearing fail-loud key-set guard (raises on drift), not documentation scaffolding.
- **Decomposition:** shipped as a `region_graph/` *package* (model/config/errors/invariants/generator/__init__), following the Plan-1 `interiors/` precedent, rather than the single `region_graph.py` the spec §8 names — same public import path.

Scope boundaries held exactly as the table above states: no `depth_score` field (Plan 3), `theme_pool` is a real parameter not a Plan-4 stub, no persistence (Plan 5), OTEL spans + the mandatory production-path wiring test are Plan 7's (no runtime consumer exists yet; the deep-chain sweep is the strongest wiring proof at this layer; `GenerationReport.as_dict()` is the span-ready contract).
