# Beneath Sünden Plan 3 — `depth_score` Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the abstract `depth_score` gradient to the now-merged `sidequest.dungeon.region_graph` package — frozen-at-attach scalar per region (≈ ordinary-route graph distance from the surface entrance, deterministically jittered) plus a coarse, stable player-facing "level" bucket/phrase.

**Architecture:** A single new module `sidequest/dungeon/region_graph/depth.py` (lives *inside* the region_graph package — it directly extends `RegionNode` and traverses `RegionGraph`; this follows Plan 2's already-shipped package-decomposition reality, which superseded spec §8's pre-package single-file layout). `RegionNode` gains one field `depth_score: float | None = None` (None = not yet assigned at attach — a real default, not a stub). `assign_depth_scores` computes scores from **ordinary-route** BFS distance (excludes `hidden` + `shortcut` edges, mirroring `invariants.py`'s `stitch` rationale: secret passages and shortcuts are bypasses, not the ordinary route), freezes already-scored regions (never recomputes — the save is source of truth), and returns a span-ready `DepthReport` mirroring the `GenerationReport.as_dict()` precedent. No runtime OTEL or session wiring here — that is Plan 7's materializer (honest deferral, identical to Plan 2's stance, documented in Task 8).

**Tech Stack:** Python 3, `dataclasses` (frozen), `hashlib.blake2b` for deterministic jitter sub-seeding (NEVER XOR — preempts the `seed ^ 0x5EED`/24301 fixed-point class of bug at this layer, exactly as `generator._subseed` does), `pytest`. All commands via `uv run` (`python` is NOT on PATH in sidequest-server).

**Repo / branch:** `sidequest-server` on `feat/beneath-sunden-depth-score` (already created off freshly-merged `develop` @ `5eba51a`, which carries Plan 2's `region_graph` package). PRs target `develop` (gitflow).

**§12 open-item decision (baked in here, tunable in world config — reversible):** player-facing "level" bucket coarseness = **3 ordinary-route hops per level** (`bucket_size` default `30.0` at `depth_per_hop` default `10.0`). Rationale: a "level" must be *coarse shorthand*, deliberately NOT a 1:1 hop/floor index — a 1-hop bucket would resurrect the explicitly-rejected discrete-floor concept (spec decision rows 1–2, §5). Three hops keeps "you reckon you're four, maybe five levels down" honestly fuzzy. `validate()` enforces `bucket_size >= depth_per_hop` so the shorthand can never silently degrade into a floor index.

---

## File Structure

| File | Create/Modify | Responsibility |
|------|---------------|----------------|
| `sidequest-server/sidequest/dungeon/region_graph/model.py` | Modify (`RegionNode`) | Add `depth_score: float \| None = None` field |
| `sidequest-server/sidequest/dungeon/region_graph/depth.py` | Create | `DepthConfig`, ordinary-route distance helper, deterministic jitter, `assign_depth_scores`, `DepthReport`, `level_bucket`, `level_phrase` |
| `sidequest-server/sidequest/dungeon/region_graph/__init__.py` | Modify | Export new public surface incrementally |
| `sidequest-server/tests/dungeon/region_graph/test_depth.py` | Create | Unit tests for every depth.py function + model field |
| `sidequest-server/tests/dungeon/region_graph/test_depth_property.py` | Create | Monotonic-ish seed-sweep property test + region_graph integration/wiring test |

**Scope discipline (minimalist):** Plan 3 produces `depth_score` + bucket/phrase ONLY. The spec §5 *consumers* of `depth_score` (theme depth-band eligibility, set-piece lethality tier, creature-table tier) are Plan 4 (themes) and Plan 6 (set-pieces) — do NOT build them here. No edge-kind distance weighting (spec §5 says "≈ accumulated traversal / graph distance"; plain BFS hop distance satisfies it and the §11 test; weighting is unrequested → YAGNI).

---

## Task 1: `DepthConfig` + validation

**Files:**
- Create: `sidequest-server/sidequest/dungeon/region_graph/depth.py`
- Modify: `sidequest-server/sidequest/dungeon/region_graph/__init__.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py`

- [ ] **Step 1: Write the failing test**

Create `sidequest-server/tests/dungeon/region_graph/test_depth.py`:

```python
"""Unit tests for sidequest.dungeon.region_graph.depth."""

import pytest

from sidequest.dungeon.region_graph.depth import DepthConfig


def test_depth_config_defaults():
    c = DepthConfig()
    assert c.depth_per_hop == 10.0
    assert c.jitter_max == 3.0
    assert c.bucket_size == 30.0  # §12 decision: 3 ordinary hops per "level"
    c.validate()  # defaults are self-consistent


@pytest.mark.parametrize(
    "kwargs, msg",
    [
        ({"depth_per_hop": 0.0}, "depth_per_hop must be > 0"),
        ({"depth_per_hop": -1.0}, "depth_per_hop must be > 0"),
        ({"jitter_max": -0.1}, "jitter_max must be >= 0"),
        # a "level" coarser-or-equal to one hop, else it's a floor index
        ({"bucket_size": 9.9}, "bucket_size must be >= depth_per_hop"),
    ],
)
def test_depth_config_validate_rejects(kwargs, msg):
    with pytest.raises(ValueError, match=msg):
        DepthConfig(**kwargs).validate()


def test_depth_config_zero_jitter_is_valid():
    DepthConfig(jitter_max=0.0).validate()  # jitter is optional (spec §5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.dungeon.region_graph.depth'`

- [ ] **Step 3: Write minimal implementation**

Create `sidequest-server/sidequest/dungeon/region_graph/depth.py`:

```python
"""depth_score gradient (spec: Beneath Sünden §5, §10 step 3).

depth_score is the ONLY notion of depth: an abstract scalar attached to
each region AT ATTACH TIME and frozen into the save (never recomputed).
It is ≈ ordinary-route graph distance from the surface entrance,
deterministically jittered. "Level" survives only as a coarse,
approximate player-facing bucket — never an authoritative coordinate,
key, or container (spec decision rows 1, 2; §5).

Ordinary-route distance EXCLUDES hidden + shortcut edges: a secret
passage is not the ordinary route and a shortcut is a discovered bypass
(same rationale as invariants.py's `stitch` exclusion). Discovering a
shortcut later must NOT retroactively make a region shallower — scores
are frozen at attach.

Pure, deterministic, dependency-free. No OTEL / session wiring here —
Plan 7's materializer emits the `dungeon.materialize.attach` span from
DepthReport.as_dict() (same honest-deferral stance as Plan 2's
region_graph: see __init__.py docstring "later plans (3/4/5/7)").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DepthConfig:
    """Tunable depth knobs (spec §5 'All thresholds ... tunable in world config')."""

    depth_per_hop: float = 10.0
    jitter_max: float = 3.0
    # §12 decision: coarse shorthand = 3 ordinary hops per "level".
    # Deliberately NOT 1:1 (a 1-hop bucket would resurrect the rejected
    # discrete-floor concept — spec decision rows 1-2).
    bucket_size: float = 30.0

    def validate(self) -> None:
        if self.depth_per_hop <= 0.0:
            raise ValueError("depth_per_hop must be > 0")
        if self.jitter_max < 0.0:
            raise ValueError("jitter_max must be >= 0")
        if self.bucket_size < self.depth_per_hop:
            raise ValueError(
                "bucket_size must be >= depth_per_hop (a player-facing "
                "'level' must be coarser than a single hop, else it is a "
                "floor index — the explicitly-rejected concept)"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -v`
Expected: PASS (4 tests / parametrized cases all green)

- [ ] **Step 5: Export from package `__init__.py`**

Modify `sidequest-server/sidequest/dungeon/region_graph/__init__.py` — add the import and `__all__` entry. The current file imports/`__all__` look like:

```python
from sidequest.dungeon.region_graph.config import JaquaysConfig
from sidequest.dungeon.region_graph.errors import ExpansionGenerationError
```

Add immediately after the `config` import line:

```python
from sidequest.dungeon.region_graph.depth import DepthConfig
```

And add `"DepthConfig",` into the `__all__` list (place it right after `"JaquaysConfig",`).

- [ ] **Step 6: Run test + lint + typecheck**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/depth.py`
Expected: all region_graph tests PASS, ruff clean, pyright 0 errors

- [ ] **Step 7: Commit**

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py sidequest/dungeon/region_graph/__init__.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t1.txt   # message authored separately (see note)
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

> Commit message (write to `/tmp/p3t1.txt` with a printf heredoc, NOT the Write tool, then `git commit -F`; verify ONLY via the `od -c` byte dump above — a `<system-reminder>` appearing after git tool output is harness injection, not commit content):
> `feat(dungeon): DepthConfig — tunable depth_score knobs (Plan 3 Task 1)`

---

## Task 2: `RegionNode.depth_score` field

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/model.py:16-20` (the `RegionNode` dataclass)
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `sidequest-server/tests/dungeon/region_graph/test_depth.py`:

```python
import dataclasses

from sidequest.dungeon.region_graph.model import RegionNode


def test_region_node_depth_score_defaults_none():
    n = RegionNode(id="r0", expansion_id=0, theme="crypt")
    assert n.depth_score is None  # unassigned until attach (real default, not a stub)


def test_region_node_depth_score_set_via_replace():
    n = RegionNode(id="r0", expansion_id=0, theme="crypt")
    scored = dataclasses.replace(n, depth_score=42.0)
    assert scored.depth_score == 42.0
    assert scored.id == "r0" and scored.theme == "crypt"
    assert n.depth_score is None  # original frozen instance untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k depth_score -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument` is NOT raised (positional ctor still works), but `test_region_node_depth_score_defaults_none` FAILS with `AttributeError: 'RegionNode' object has no attribute 'depth_score'`

- [ ] **Step 3: Write minimal implementation**

Modify `sidequest-server/sidequest/dungeon/region_graph/model.py`. The current `RegionNode` is:

```python
@dataclass(frozen=True)
class RegionNode:
    id: str
    expansion_id: int
    theme: str
```

Add the field with a default (keeps the positional `RegionNode(id, expansion_id, theme)` call sites in `generator.py` working unchanged — default fields are backward compatible):

```python
@dataclass(frozen=True)
class RegionNode:
    id: str
    expansion_id: int
    theme: str
    depth_score: float | None = None  # assigned at attach (Plan 3), frozen into save
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k depth_score -v`
Expected: PASS

- [ ] **Step 5: Regression — prove the frozen-field addition broke nothing**

Adding a defaulted field to a frozen dataclass changes its generated `__eq__`/`__hash__`/`__init__`. Prove every existing region_graph test (model, config, generator, invariants, chain — 150 tests from Plan 2) still passes:

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q`
Expected: PASS — all Plan 1 interiors + Plan 2 region_graph tests + new depth tests green, zero failures

If anything fails: the failure is a real incompatibility (e.g. a test asserting `RegionNode(...) == RegionNode(...)` where one side now carries a score). Do NOT revert the field. Fit the affected assertion to the new shape (per project rule: when production shape changes, fit tests to it — never revert the feature).

- [ ] **Step 6: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/model.py`
Expected: ruff clean, pyright 0

- [ ] **Step 7: Commit**

> Commit message (printf-heredoc to `/tmp/p3t2.txt`, `git commit -F`, verify with `git log -1 --format=%B | od -c`):
> `feat(dungeon): RegionNode.depth_score field (Plan 3 Task 2)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/model.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t2.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 3: ordinary-route distance helper

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/depth.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `test_depth.py`:

```python
from sidequest.dungeon.region_graph.depth import ordinary_route_dist
from sidequest.dungeon.region_graph.model import RegionEdge, RegionGraph


def _chain_graph() -> RegionGraph:
    # entrance -corridor- a -corridor- b ; plus a SHORTCUT entrance->b
    g = RegionGraph(entrance_id="e")
    for rid in ("e", "a", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=0, theme="t"))
    g.add_edge(RegionEdge(a="e", b="a", kind="corridor"))
    g.add_edge(RegionEdge(a="a", b="b", kind="corridor"))
    g.add_edge(RegionEdge(a="e", b="b", kind="shaft", shortcut=True))
    return g


def test_ordinary_route_ignores_shortcut():
    g = _chain_graph()
    d = ordinary_route_dist(g)
    # shortcut e->b is excluded: b is 2 hops via a, not 1 via the shortcut
    assert d == {"e": 0, "a": 1, "b": 2}


def test_ordinary_route_ignores_hidden():
    g = RegionGraph(entrance_id="e")
    for rid in ("e", "a", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=0, theme="t"))
    g.add_edge(RegionEdge(a="e", b="a", kind="corridor"))
    g.add_edge(RegionEdge(a="a", b="b", kind="corridor"))
    g.add_edge(RegionEdge(a="e", b="b", kind="secret", hidden=True))
    assert ordinary_route_dist(g) == {"e": 0, "a": 1, "b": 2}


def test_ordinary_route_raises_when_region_unreachable_on_ordinary_graph():
    # b reachable ONLY via a hidden edge -> No Silent Fallbacks: fail loud
    g = RegionGraph(entrance_id="e")
    for rid in ("e", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=0, theme="t"))
    g.add_edge(RegionEdge(a="e", b="b", kind="secret", hidden=True))
    with pytest.raises(ValueError, match="not reachable on the ordinary route"):
        ordinary_route_dist(g)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k ordinary_route -v`
Expected: FAIL — `ImportError: cannot import name 'ordinary_route_dist'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/region_graph/depth.py` (add `RegionGraph` to the imports — add this import block under `from dataclasses import dataclass`):

```python
from sidequest.dungeon.region_graph.model import RegionGraph


def ordinary_route_dist(graph: RegionGraph) -> dict[str, int]:
    """BFS hop distance from the entrance over ORDINARY edges only —
    hidden (secret) and shortcut edges are excluded (a secret passage is
    not the ordinary route; a shortcut is a discovered bypass — same
    exclusion rationale as invariants.py's `stitch`).

    Raises loudly (CLAUDE.md: No Silent Fallbacks) if any region is not
    reachable from the entrance on the ordinary-route graph — depth must
    never silently default to 0 for an unreachable region.
    """
    skip = {
        i for i, e in enumerate(graph.edges) if e.hidden or e.shortcut
    }
    dist = graph.bfs_dist(graph.entrance_id, skip_edges=skip)
    missing = sorted(set(graph.nodes) - set(dist))
    if missing:
        raise ValueError(
            f"regions {missing} not reachable on the ordinary route "
            f"from {graph.entrance_id!r} (hidden/shortcut edges excluded); "
            f"cannot assign a depth_score"
        )
    return dist
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k ordinary_route -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Lint + typecheck + full dungeon regression**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/depth.py`
Expected: all green, ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Commit message (printf-heredoc → `/tmp/p3t3.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): ordinary-route distance helper (Plan 3 Task 3)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t3.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 4: deterministic bounded jitter (blake2b, never XOR)

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/depth.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `test_depth.py`:

```python
from sidequest.dungeon.region_graph.depth import depth_jitter


def test_depth_jitter_deterministic():
    a = depth_jitter(campaign_seed=12345, region_id="exp001.r3", jitter_max=3.0)
    b = depth_jitter(campaign_seed=12345, region_id="exp001.r3", jitter_max=3.0)
    assert a == b


def test_depth_jitter_within_bounds():
    for rid in (f"exp{e:03d}.r{r}" for e in range(20) for r in range(6)):
        j = depth_jitter(campaign_seed=999, region_id=rid, jitter_max=3.0)
        assert -3.0 <= j <= 3.0


def test_depth_jitter_varies_by_region():
    seed = 7
    vals = {
        depth_jitter(campaign_seed=seed, region_id=f"exp000.r{i}", jitter_max=3.0)
        for i in range(40)
    }
    assert len(vals) > 1  # not a constant


def test_depth_jitter_zero_max_is_exactly_zero():
    assert depth_jitter(campaign_seed=1, region_id="exp000.r0", jitter_max=0.0) == 0.0


def test_depth_jitter_seed_24301_is_not_degenerate():
    # The seed ^ 0x5EED fixed point (24301) must NOT collapse jitter to a
    # constant here — we use blake2b, never XOR (carry-forward gotcha).
    vals = {
        depth_jitter(campaign_seed=24301, region_id=f"exp000.r{i}", jitter_max=3.0)
        for i in range(40)
    }
    assert len(vals) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k jitter -v`
Expected: FAIL — `ImportError: cannot import name 'depth_jitter'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/region_graph/depth.py` (add `import hashlib` at the top of the module, beside `from __future__ import annotations`):

```python
def depth_jitter(*, campaign_seed: int, region_id: str, jitter_max: float) -> float:
    """Deterministic per-region jitter in [-jitter_max, +jitter_max].

    Sub-seeds with blake2b, NOT XOR — mirrors generator._subseed and
    refuses to reproduce the `seed ^ 0x5EED` fixed-point-at-24301 class
    of bug at this layer (Beneath Sünden carry-forward gotcha).
    """
    if jitter_max == 0.0:
        return 0.0
    digest = hashlib.blake2b(
        f"{campaign_seed}|depth|{region_id}".encode(),
        digest_size=8,
    ).digest()
    # map the 64-bit digest to a unit fraction in [0, 1), then to
    # [-jitter_max, +jitter_max].
    frac = int.from_bytes(digest, "big") / float(1 << 64)
    return (frac * 2.0 - 1.0) * jitter_max
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k jitter -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/depth.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Commit message (printf-heredoc → `/tmp/p3t4.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): deterministic blake2b depth jitter (Plan 3 Task 4)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t4.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 5: `assign_depth_scores` (freeze-respecting, fail-loud)

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/depth.py`
- Modify: `sidequest-server/sidequest/dungeon/region_graph/__init__.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `test_depth.py`:

```python
from sidequest.dungeon.region_graph.depth import (
    DepthConfig,
    assign_depth_scores,
)


def _scored_chain():
    # e -corridor- a -corridor- b ; e -shortcut- b
    g = _chain_graph()
    cfg = DepthConfig(depth_per_hop=10.0, jitter_max=3.0)
    report = assign_depth_scores(g, campaign_seed=42, config=cfg)
    return g, cfg, report


def test_assign_scores_all_regions_and_entrance_is_zero():
    g, cfg, _ = _scored_chain()
    assert g.nodes["e"].depth_score == 0.0  # entrance is the origin, exactly 0
    for rid in ("a", "b"):
        assert g.nodes[rid].depth_score is not None


def test_assign_score_is_base_plus_bounded_jitter():
    g, cfg, _ = _scored_chain()
    # b is 2 ordinary hops deep (shortcut excluded) -> base 20.0 +/- 3.0
    assert abs(g.nodes["b"].depth_score - 20.0) <= cfg.jitter_max
    assert abs(g.nodes["a"].depth_score - 10.0) <= cfg.jitter_max


def test_assign_is_frozen_second_call_is_noop_on_scored_regions():
    g, cfg, _ = _scored_chain()
    snapshot = {rid: n.depth_score for rid, n in g.nodes.items()}
    # add a new unscored region off 'b', re-assign: old scores MUST NOT move
    g.add_node(RegionNode(id="c", expansion_id=1, theme="t"))
    g.add_edge(RegionEdge(a="b", b="c", kind="corridor"))
    g.add_edge(RegionEdge(a="a", b="c", kind="corridor"))  # 2nd ordinary entry
    rep2 = assign_depth_scores(g, campaign_seed=42, config=cfg)
    for rid, old in snapshot.items():
        assert g.nodes[rid].depth_score == old  # frozen — save is source of truth
    assert g.nodes["c"].depth_score is not None
    assert rep2.regions_scored == 1  # only the new one


def test_assign_raises_when_region_unreachable_on_ordinary_graph():
    g = RegionGraph(entrance_id="e")
    for rid in ("e", "b"):
        g.add_node(RegionNode(id=rid, expansion_id=0, theme="t"))
    g.add_edge(RegionEdge(a="e", b="b", kind="secret", hidden=True))
    with pytest.raises(ValueError, match="not reachable on the ordinary route"):
        assign_depth_scores(g, campaign_seed=1, config=DepthConfig())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k assign -v`
Expected: FAIL — `ImportError: cannot import name 'assign_depth_scores'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/region_graph/depth.py` (add `import dataclasses` at the top of the module):

```python
def assign_depth_scores(
    graph: RegionGraph,
    *,
    campaign_seed: int,
    config: DepthConfig | None = None,
) -> "DepthReport":
    """Assign depth_score to every region that does not yet have one,
    then FREEZE it (already-scored regions are never recomputed — the
    save is the source of truth, spec §7).

    Score = ordinary-route hops from the entrance * depth_per_hop +
    deterministic bounded jitter. The entrance is the origin: exactly
    0.0, no jitter. Mutates graph.nodes in place (replacing frozen
    RegionNode instances) and returns the same graph's DepthReport —
    mirrors attach_expansion's "returns the (mutated) graph" contract
    and GenerationReport's span-ready report precedent.

    Raises loudly if a to-be-scored region is unreachable on the
    ordinary-route graph (CLAUDE.md: No Silent Fallbacks).
    """
    cfg = config or DepthConfig()
    cfg.validate()

    to_score = [
        rid for rid, n in graph.nodes.items() if n.depth_score is None
    ]
    if not to_score:
        return DepthReport(regions_scored=0)

    dist = ordinary_route_dist(graph)  # raises if any region unreachable

    scored_values: list[float] = []
    for rid in to_score:
        if rid == graph.entrance_id:
            score = 0.0
        else:
            base = dist[rid] * cfg.depth_per_hop
            score = base + depth_jitter(
                campaign_seed=campaign_seed,
                region_id=rid,
                jitter_max=cfg.jitter_max,
            )
        graph.nodes[rid] = dataclasses.replace(
            graph.nodes[rid], depth_score=score
        )
        scored_values.append(score)

    return DepthReport(
        regions_scored=len(scored_values),
        depth_min=min(scored_values),
        depth_max=max(scored_values),
        depth_mean=sum(scored_values) / len(scored_values),
    )
```

> `DepthReport` is defined in Task 6. To keep Task 5's test green now, add this **minimal** placeholder-free real dataclass to the TOP of depth.py (right after `DepthConfig`) — Task 6 only extends it with `as_dict()` + bucket fields, it is a real type from the start, not a stub:

```python
@dataclass
class DepthReport:
    regions_scored: int = 0
    depth_min: float = 0.0
    depth_max: float = 0.0
    depth_mean: float = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k assign -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Export from package `__init__.py`**

Modify `sidequest-server/sidequest/dungeon/region_graph/__init__.py` — extend the depth import to:

```python
from sidequest.dungeon.region_graph.depth import (
    DepthConfig,
    DepthReport,
    assign_depth_scores,
)
```

Add `"DepthReport",` and `"assign_depth_scores",` into `__all__` (next to `"DepthConfig",`).

- [ ] **Step 6: Lint + typecheck + full dungeon regression**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/`
Expected: all green, ruff clean, pyright 0

- [ ] **Step 7: Commit**

> Commit message (printf-heredoc → `/tmp/p3t5.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): assign_depth_scores — frozen-at-attach, fail-loud (Plan 3 Task 5)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py sidequest/dungeon/region_graph/__init__.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t5.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 6: `DepthReport.as_dict()` — span-ready contract

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/depth.py` (extend `DepthReport`)
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `test_depth.py`:

```python
def test_depth_report_as_dict_is_stable_span_contract():
    g, cfg, report = _scored_chain()
    d = report.as_dict()
    # exact key-set is the OTEL span contract Plan 7 consumes — pin it
    assert set(d) == {
        "regions_scored",
        "depth_min",
        "depth_max",
        "depth_mean",
    }
    assert d["regions_scored"] == 3  # e, a, b
    assert d["depth_min"] == 0.0     # entrance
    assert d["depth_max"] == report.depth_max


def test_depth_report_empty_when_nothing_to_score():
    g, cfg, _ = _scored_chain()
    rep = assign_depth_scores(g, campaign_seed=42, config=cfg)  # all scored
    assert rep.regions_scored == 0
    assert rep.as_dict()["regions_scored"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k report -v`
Expected: FAIL — `AttributeError: 'DepthReport' object has no attribute 'as_dict'`

- [ ] **Step 3: Write minimal implementation**

In `sidequest-server/sidequest/dungeon/region_graph/depth.py`, replace the Task 5 minimal `DepthReport` with the full version (adds `as_dict()` only — fields unchanged, so Task 5's `DepthReport(regions_scored=..., depth_min=..., ...)` construction stays valid):

```python
@dataclass
class DepthReport:
    """Span-ready contract — Plan 7's materializer turns this into
    `dungeon.materialize.attach` OTEL attributes (mirrors
    GenerationReport.as_dict() from invariants.py)."""

    regions_scored: int = 0
    depth_min: float = 0.0
    depth_max: float = 0.0
    depth_mean: float = 0.0

    def as_dict(self) -> dict:
        return {
            "regions_scored": self.regions_scored,
            "depth_min": self.depth_min,
            "depth_max": self.depth_max,
            "depth_mean": self.depth_mean,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k report -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Lint + typecheck**

Run: `cd sidequest-server && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/depth.py`
Expected: ruff clean, pyright 0

- [ ] **Step 6: Commit**

> Commit message (printf-heredoc → `/tmp/p3t6.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): DepthReport.as_dict span-ready contract (Plan 3 Task 6)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t6.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 7: player-facing `level_bucket` + `level_phrase`

**Files:**
- Modify: `sidequest-server/sidequest/dungeon/region_graph/depth.py`
- Modify: `sidequest-server/sidequest/dungeon/region_graph/__init__.py`
- Test: `sidequest-server/tests/dungeon/region_graph/test_depth.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `test_depth.py`:

```python
from sidequest.dungeon.region_graph.depth import level_bucket, level_phrase


def test_level_bucket_zero_at_and_below_entrance():
    cfg = DepthConfig()  # bucket_size 30.0
    assert level_bucket(0.0, cfg) == 0
    assert level_bucket(29.9, cfg) == 0
    assert level_bucket(30.0, cfg) == 1
    assert level_bucket(95.0, cfg) == 3


def test_level_bucket_is_monotonic_non_decreasing():
    cfg = DepthConfig()
    last = -1
    for s in range(0, 400, 5):
        b = level_bucket(float(s), cfg)
        assert b >= last
        last = b


def test_level_bucket_stable_for_same_score():
    cfg = DepthConfig()
    assert level_bucket(57.3, cfg) == level_bucket(57.3, cfg)


def test_level_phrase_surface_and_depth_and_boundary_fuzz():
    cfg = DepthConfig()  # bucket_size 30, jitter_max 3
    assert "surface" in level_phrase(0.0, cfg).lower()
    # mid-bucket -> confident "about N"
    mid = level_phrase(45.0, cfg).lower()
    assert "about" in mid and "1" in mid  # 45/30 -> bucket 1
    # near a bucket boundary (within jitter_max of a multiple of 30) ->
    # fuzzy "N, maybe N+1" (spec §5: "four, maybe five levels down")
    fuzzy = level_phrase(89.0, cfg).lower()  # 89 ~ boundary 90 (bucket 2|3)
    assert "maybe" in fuzzy
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k "bucket or phrase" -v`
Expected: FAIL — `ImportError: cannot import name 'level_bucket'`

- [ ] **Step 3: Write minimal implementation**

Append to `sidequest-server/sidequest/dungeon/region_graph/depth.py`:

```python
def level_bucket(depth_score: float, config: DepthConfig | None = None) -> int:
    """Coarse player-facing 'level' bucket (spec §5, §12 decision).

    APPROXIMATION ONLY — never an authoritative coordinate, key, or
    container (spec decision rows 1, 2). 0 == at/just inside the surface
    threshold; each bucket spans `bucket_size` (default 3 ordinary hops).
    """
    cfg = config or DepthConfig()
    cfg.validate()
    if depth_score <= 0.0:
        return 0
    return int(depth_score // cfg.bucket_size)


def level_phrase(depth_score: float, config: DepthConfig | None = None) -> str:
    """Fuzzy player-facing shorthand (spec §5 example: 'you reckon you're
    four, maybe five levels down'). Deliberately approximate; this is the
    coarse mechanical label only — narrator/curation handles prose."""
    cfg = config or DepthConfig()
    cfg.validate()
    if depth_score <= 0.0:
        return "at the surface, just inside the threshold"
    b = level_bucket(depth_score, cfg)
    # distance to the nearer bucket boundary; within jitter_max -> fuzzy
    pos = depth_score % cfg.bucket_size
    near_boundary = min(pos, cfg.bucket_size - pos) <= cfg.jitter_max
    if near_boundary:
        return f"you reckon you're {b}, maybe {b + 1} levels down"
    return f"about {b} levels down"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth.py -k "bucket or phrase" -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Export from package `__init__.py`**

Modify `sidequest-server/sidequest/dungeon/region_graph/__init__.py` — extend the depth import to its final form:

```python
from sidequest.dungeon.region_graph.depth import (
    DepthConfig,
    DepthReport,
    assign_depth_scores,
    level_bucket,
    level_phrase,
)
```

Add `"level_bucket",` and `"level_phrase",` into `__all__`.

- [ ] **Step 6: Lint + typecheck + full dungeon regression**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/`
Expected: all green, ruff clean, pyright 0

- [ ] **Step 7: Commit**

> Commit message (printf-heredoc → `/tmp/p3t7.txt`, `git commit -F`, `od -c` verify):
> `feat(dungeon): player-facing level_bucket + level_phrase (Plan 3 Task 7)`

```bash
cd sidequest-server
git add sidequest/dungeon/region_graph/depth.py sidequest/dungeon/region_graph/__init__.py tests/dungeon/region_graph/test_depth.py
git commit -F /tmp/p3t7.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

---

## Task 8: monotonic-ish property sweep + region_graph integration (wiring) test

**Files:**
- Create: `sidequest-server/tests/dungeon/region_graph/test_depth_property.py`

This task adds **no production code** — it is the §11 property test (`depth_score`: "monotonic-ish with traversal from the entrance within tunable jitter; player-facing bucket mapping stable") and the **wiring test** proving `depth.py` is integrated with the *real* `region_graph` package end-to-end (`generate_expansion` → `attach_expansion` → `assign_depth_scores` → `level_bucket`). Per CLAUDE.md "Every Test Suite Needs a Wiring Test": this layer's runtime consumer (the session/frontier-crossing materializer) is Plan 7 by design — the same honest deferral Plan 2 made (`region_graph/__init__.py` docstring: "later plans (3/4/5/7)"). The wiring proven here is component-to-component within the dungeon library; the production session-path wiring + OTEL spans are explicitly Plan 7's scope.

- [ ] **Step 1: Write the property + wiring test**

Create `sidequest-server/tests/dungeon/region_graph/test_depth_property.py`:

```python
"""Plan 3 §11 property sweep + region_graph integration (wiring) test.

Production session-path wiring + dungeon.materialize.attach OTEL spans
are Plan 7's materializer scope (honest deferral, same as Plan 2's
region_graph). This proves depth.py is wired to the REAL region_graph
generator/attach path, not unit-isolated.
"""

import pytest

from sidequest.dungeon.region_graph import (
    DepthConfig,
    RegionGraph,
    RegionNode,
    assign_depth_scores,
    attach_expansion,
    generate_expansion,
    level_bucket,
)
from sidequest.dungeon.region_graph.depth import ordinary_route_dist

THEMES = ["crypt", "cavern", "catacomb", "vault", "flooded"]


def _seed_graph() -> RegionGraph:
    g = RegionGraph(entrance_id="surface")
    g.add_node(RegionNode(id="surface", expansion_id=0, theme="threshold"))
    return g


def _grow(campaign_seed: int, expansions: int) -> RegionGraph:
    """Build a multi-expansion contiguous map via the REAL Plan 2
    generator + attach, assigning depth after every attach (this is the
    integration/wiring contract Plan 7's materializer will drive)."""
    g = _seed_graph()
    cfg = DepthConfig()
    for exp_id in range(1, expansions + 1):
        if exp_id == 1:
            attach_ids = ["surface"]
        else:
            # attach to the 2 most-recently-added regions (>=2 entries)
            recent = [n.id for n in list(g.nodes.values())[-4:]]
            attach_ids = recent[:2] if len(recent) >= 2 else ["surface"]
        exp, _report = generate_expansion(
            graph=g,
            campaign_seed=campaign_seed,
            expansion_id=exp_id,
            attach_region_ids=attach_ids,
            theme_pool=THEMES,
        )
        attach_expansion(g, exp)
        assign_depth_scores(g, campaign_seed=campaign_seed, config=cfg)
    return g, cfg


@pytest.mark.parametrize("campaign_seed", [1, 7, 42, 100, 24301, 999999])
def test_depth_score_monotonic_ish_within_jitter(campaign_seed):
    g, cfg = _grow(campaign_seed, expansions=5)
    dist = ordinary_route_dist(g)
    for rid, node in g.nodes.items():
        assert node.depth_score is not None
        if rid == g.entrance_id:
            assert node.depth_score == 0.0
            continue
        base = dist[rid] * cfg.depth_per_hop
        # |score - base| <= jitter_max  ==  "monotonic-ish within
        # tunable jitter": base is strictly non-decreasing with ordinary
        # BFS distance, score never strays past the tunable bound.
        assert abs(node.depth_score - base) <= cfg.jitter_max


@pytest.mark.parametrize("campaign_seed", [1, 7, 42, 100, 24301, 999999])
def test_bucket_non_decreasing_along_ordinary_paths(campaign_seed):
    g, cfg = _grow(campaign_seed, expansions=5)
    dist = ordinary_route_dist(g)
    # buckets sorted by ordinary distance must be non-decreasing (coarse,
    # stable player-facing mapping)
    by_dist = sorted(g.nodes, key=lambda r: dist[r])
    last_bucket = -1
    last_dist = -1
    for rid in by_dist:
        b = level_bucket(g.nodes[rid].depth_score, cfg)
        if dist[rid] > last_dist:
            assert b >= last_bucket
            last_bucket = max(last_bucket, b)
            last_dist = dist[rid]


def test_freeze_holds_across_real_expansions(campaign_seed=42):
    """Scores assigned at one attach are byte-identical after later
    expansions (spec §7: save is source of truth, never recomputed)."""
    g, cfg = _grow(campaign_seed, expansions=3)
    snapshot = {rid: n.depth_score for rid, n in g.nodes.items()}
    exp, _ = generate_expansion(
        graph=g,
        campaign_seed=campaign_seed,
        expansion_id=99,
        attach_region_ids=[n.id for n in list(g.nodes.values())[-2:]],
        theme_pool=THEMES,
    )
    attach_expansion(g, exp)
    assign_depth_scores(g, campaign_seed=campaign_seed, config=cfg)
    for rid, old in snapshot.items():
        assert g.nodes[rid].depth_score == old  # frozen, exact


def test_wiring_depth_consumes_real_region_graph_public_surface():
    """Wiring assertion: the depth API is reachable from the region_graph
    package's public surface and operates on real generator output."""
    g, _ = _grow(7, expansions=5)  # 5 matches the sweeps; >=4 needed to reach bucket 1
    assert all(n.depth_score is not None for n in g.nodes.values())
    assert any(level_bucket(n.depth_score) >= 1 for n in g.nodes.values())
```

- [ ] **Step 2: Run test to verify it passes** (no new production code — depends only on Tasks 1–7)

Run: `cd sidequest-server && uv run pytest tests/dungeon/region_graph/test_depth_property.py -v`
Expected: PASS — all parametrized seeds (including the `24301` `^0x5EED` fixed-point seed) green

- [ ] **Step 3: Full dungeon regression + lint + typecheck**

Run: `cd sidequest-server && uv run pytest tests/dungeon/ -q && uv run ruff check sidequest/dungeon tests/dungeon && uv run pyright sidequest/dungeon/region_graph/`
Expected: all green (Plan 1 interiors + Plan 2 region_graph + Plan 3 depth), ruff clean, pyright 0

- [ ] **Step 4: Full server-suite regression (additive-only proof)**

Plan 3 is purely additive to a frozen dataclass + a new module. Prove the whole server suite is unaffected:

Run: `cd sidequest-server && uv run pytest -q`
Expected: PASS — the full ~6172+ test server suite green (the only intended change is the new `RegionNode.depth_score=None` default + new depth module/tests)

- [ ] **Step 5: Commit**

> Commit message (printf-heredoc → `/tmp/p3t8.txt`, `git commit -F`, `od -c` verify):
> `test(dungeon): depth_score monotonic-ish sweep + region_graph wiring (Plan 3 Task 8)`

```bash
cd sidequest-server
git add tests/dungeon/region_graph/test_depth_property.py
git commit -F /tmp/p3t8.txt
git log -1 --format=%B | od -c | grep -q 'system-reminder' && echo "LEAK — re-author" || echo "commit clean"
```

- [ ] **Step 6: Push the branch**

```bash
cd sidequest-server
git push -u origin feat/beneath-sunden-depth-score
```

(PR creation is the finishing step — handled after the final whole-implementation review, targeting `develop`.)

---

## Self-Review (run before declaring the plan ready)

**1. Spec coverage**

| Spec requirement | Task |
|---|---|
| §5 `depth_score` ≈ accumulated traversal / graph distance from entrance | Tasks 3, 5 |
| §5 "optionally jittered" | Tasks 4, 5 (jitter_max=0 path tested) |
| §5 frozen at attach time / never recomputed (save is source of truth, §7) | Task 5 (freeze), Task 8 (across real expansions) |
| §5 drives theme-band / lethality / creature-tier | OUT — Plan 4/6 consumers (scope-noted) |
| §5 "Level" = loose coarse player-facing bucket, never authoritative | Task 7 (`level_bucket` approximation-only, `<= depth_per_hop` guard) |
| §5 example phrasing "you reckon you're four, maybe five levels down" | Task 7 (`level_phrase` boundary fuzz) |
| §8 `depth.py` module | All tasks (package-local: documented deviation from §8's pre-package layout, consistent with Plan 2) |
| §10 step 3 assignment / jitter / bucketing | Tasks 5 / 4 / 7 |
| §11 monotonic-ish within tunable jitter; bucket mapping stable | Task 8 (sweep), Task 7 (stable) |
| §12 bucket coarseness open item | DECIDED: 3 hops/level, tunable, `validate()`-guarded (header + Task 1) |
| CLAUDE.md No Silent Fallbacks | Task 3/5 (unreachable → raise) |
| CLAUDE.md wiring test | Task 8 (component wiring; production-path = Plan 7, documented) |
| Carry-forward: blake2b never XOR; seed 24301 not degenerate | Task 4 (explicit test) |
| Carry-forward: RegionNode extended only when score is assigned (no placeholder) | Task 2 (real `None` default = "unassigned at attach") |

**2. Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N" — every step has literal code. The Task 5 minimal `DepthReport` is a *real* 4-field dataclass (Task 6 only adds `as_dict()`), explicitly not a stub.

**3. Type consistency:** `DepthConfig` fields (`depth_per_hop`, `jitter_max`, `bucket_size`) consistent across Tasks 1/5/7. `assign_depth_scores(graph, *, campaign_seed, config)` signature identical in Tasks 5 and 8. `depth_jitter(*, campaign_seed, region_id, jitter_max)` identical Tasks 4/5. `level_bucket(depth_score, config=None)` / `level_phrase(depth_score, config=None)` identical Tasks 7/8. `DepthReport` fields identical Tasks 5/6. `ordinary_route_dist(graph)` identical Tasks 3/5/8.

---

## Execution Handoff

Per the Beneath Sünden carry-forward: **subagent-driven** — fresh subagent per task, two-stage spec-then-quality review per task, plus a final whole-implementation review, on `feat/beneath-sunden-depth-score` (off the freshly-merged `develop`). PR targets `develop` after the final review.

---

## Post-Implementation Corrections (as-built — CODE IS AUTHORITATIVE)

Executed 2026-05-16, subagent-driven, two-stage review per task + final whole-impl review (opus). Branch `feat/beneath-sunden-depth-score`, 9 commits, merged-base `5eba51a`. 194 dungeon tests green, full server suite 6214 passed (1 unrelated pre-existing failure — see below), production `depth.py` pyright-0, both Plan-3 test files pyright-0, ruff clean, 0 commit-hygiene leaks. The following deviated from the plan prose above; reconcile to these if the plan is ever re-run:

- **`depth.py` placement:** lives **inside** `sidequest/dungeon/region_graph/` (not at `sidequest/dungeon/` as spec §8's pre-package sketch literally drew). Deliberate — consistent with Plan 2's already-merged package decomposition which superseded §8's single-file layout. Final review confirmed cohesive/correct.
- **Task 7 `level_phrase` — plan code was defective, corrected:** the plan's literal body said `"you reckon you're {b}, maybe {b+1}"` at BOTH boundary edges and `f"about {b} levels down"` (says "1 levels" at b==1). As-built: upper-edge → `"{b}, maybe {b+1}"`; **lower-edge (`pos <= jitter_max` AND `b >= 1`) → `"{b-1}, maybe {b}"`** (points shallower — the honest direction; bucket-0 lower edge falls through, no degenerate "0, maybe 0"); pluralization correct everywhere (`"level"` vs `"levels"`); `b` computed inline (single `validate()`, no `level_bucket` call). This is strictly *more* faithful to spec §5's "four, maybe five levels down" intent. Regression-pinned by `test_level_phrase_lower_edge_points_shallower`.
- **Task 8 — plan code was self-contradicting, corrected:** wiring test `_grow(7, expansions=2)` could not satisfy its own `level_bucket >= 1` assertion (2 hops → max depth ~23 < bucket_size 30); corrected to `expansions=5` (≥4 needed), assertion preserved (not weakened). The `test_freeze_holds_across_real_expansions` integration test as-planned was *vacuous* (deterministic jitter + unchanged distances ⇒ a broken freeze recomputes to byte-identical values); as-built it captures the `assign_depth_scores` return and asserts `report.regions_scored == len(new_ids)` AND `0 < regions_scored < len(g.nodes)` — decisive (a broken freeze would report all nodes rescored). `test_bucket_non_decreasing_along_ordinary_paths` tightened to check every node per ordinary distance (`min(bucket@dist) >= max(bucket@shallower)`), not just the first. Optional-operand pyright narrowed via `list[float]` value-binding (object-filter comprehensions do NOT narrow attribute types in pyright).
- **Post-review hardening (commit `bfe422c`, beyond the 8 tasks):** `DepthConfig.validate()` now ALSO rejects `jitter_max >= depth_per_hop` (raises `ValueError`). Closes the only silent-clamp path the reviewers identified (a tuned `jitter_max >= depth_per_hop` could push a dist-1 region's score < 0, which `level_bucket`'s legitimate `<= 0.0 → 0` surface guard would then floor — masking real depth). Default config (`jitter_max=3 < depth_per_hop=10`) was always safe; this makes the misconfig fail loud per CLAUDE.md No Silent Fallbacks. Concern was surfaced 3× across reviews; fixed in-branch rather than deferred (bounded, correctness-improving, consistent with `validate()`'s existing cross-knob-coherence precedent).
- **Honest-deferral confirmed (not a stub/half-wire):** Plan 3 ships the library layer with a real test consumer (the §11 sweep drives the actual Plan-2 `generate_expansion`/`attach_expansion`) but **no runtime/session/OTEL consumer until Plan 7's materializer** — explicitly declared in `depth.py` + `region_graph/__init__.py` docstrings, same dormant-until-Plan-7 precedent as Plan 2's `GenerationReport`. `DepthReport.as_dict()` is the byte-pinned span contract Plan 7 will emit (`test_depth_report_as_dict_is_stable_span_contract` locks the key-set).
- **Unrelated pre-existing failure (NOT Plan 3):** full-suite run surfaced `tests/server/test_chargen_dispatch.py::TestSliceAWiring::test_caverns_delver_loadout_wired_into_snapshot` (`rations_day` missing from a caverns_and_claudes loadout — a `sidequest-content` drift/env issue). Plan 3 touches only `region_graph/` + `tests/dungeon/` (cannot affect chargen/loadout); it passed in Task 8's run. Track separately against sidequest-content.

**Plan 4 / Plan 7 carry-forward:** the `sidequest.dungeon.region_graph` public surface now also exports `DepthConfig`, `DepthReport`, `assign_depth_scores`, `level_bucket`, `level_phrase`; `RegionNode` has `depth_score: float | None = None` (None = unassigned-at-attach). depth_score is assigned at attach over **ordinary-route** distance (excludes hidden+shortcut edges, mirroring `invariants.py` `stitch`), entrance exactly `0.0`, frozen thereafter (never recomputed — spec §7). `DepthReport.as_dict()` is the Plan-7 `dungeon.materialize.attach` span contract. §12 bucket coarseness = 3 ordinary hops per player-facing "level" (`bucket_size` default `30.0`, tunable; `validate()` guards both `bucket_size >= depth_per_hop` and `jitter_max < depth_per_hop`).
