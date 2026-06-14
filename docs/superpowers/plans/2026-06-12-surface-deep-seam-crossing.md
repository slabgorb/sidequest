# Surface→Deep Seam Crossing (Story 105-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the ADR-106 procedural Deep reachable in live play via a first-class seam registry: a PC on a cartography region owning a `deep_descent` route deterministically crosses to the dungeon entrance (or fails loud), the narrator can never confabulate the deep, and the entrance is a real authored room ("Under the Rope").

**Architecture:** A seam registry (`sidequest/game/seams/`, mirroring `game/ruleset/registry.py`) maps cartography route sentinels (`to_id: deep_descent`) to crossing resolvers. Two consumers call it: `movement.py`'s region-mode block (the hybrid fix — the 2026-06-02 `region_mode_deferred` early-return currently dead-codes the 59-12 handoff for beneath_sunden) and `narration_apply`'s location guard (recovery when the router misses). The router additionally gets a `current_region_exits` projection so descent classifies correctly in the first place. Content authors the entrance room.

**Tech Stack:** Python 3.12 / FastAPI server (`sidequest-server`, uv, pytest, branch base `develop`); YAML content (`sidequest-content`, branch base `develop`).

**Spec:** `docs/superpowers/specs/2026-06-12-surface-deep-crossing-design.md` (rev 2)

**Verified seam facts (do not re-derive):**
- `Route` model: `sidequest/genre/models/world.py:223` — fields `name`, `description`, `from_id`, `to_id` (all the seam needs), `model_config extra="allow"`.
- `CartographyConfig.routes: list[Route]`, `.regions: dict[str, Region]` (`world.py:267`).
- `ENTRANCE_ID = "entrance"` — `sidequest/dungeon/seed_bootstrap.py:31`.
- `movement_resolved_span(*, pc_name, from_region, to_region, **attrs)` — `sidequest/telemetry/spans/movement.py:128`.
- `region_entry_rejected_span(*, entry, reason, caller_path, **attrs)` — `sidequest/telemetry/spans/region_state.py:52`.
- `WorldStatePatch(pc_region={player_name: target})` via `snapshot.apply_world_patch(...)` fires the frontier transition (see `movement.py:243`).
- `DungeonStore.load_map(entrance_id=...)` → `RegionGraph` with `.nodes` (dict) and `.entrance_id`.
- Region-mode early-return: `movement.py:141-161` (returns `region_mode_deferred`). The 59-12 surface handoff below it (`movement.py:214-269`) is UNREACHABLE for region-mode worlds — that's root cause #1.
- `_build_state_summary(snapshot, *, pack=None)` — `sidequest/server/intent_router_pass.py:221`; the `confrontation_types` projection (line ~309) is the pattern to mirror.
- narration_apply: `_region_cart` computed at `narration_apply.py:3676`, `_is_region_mode_world` at `:3681`; the 90-6 skip branch is the `elif _is_region_mode_world:` at `:3848`.
- Apply call site: `websocket_session_handler.py:1101`, kwargs assembled in `_apply_kwargs` at `:1080`; `sd.lookahead_handle: LookaheadWorkerHandle | None` (`session_state.py:304`) carries `.persistence` (DungeonStore), `.genre_slug`, `.world_slug`.
- World dir resolution pattern: `map_emit.py:221-222` — `GenreLoader(search_paths=DEFAULT_GENRE_PACK_SEARCH_PATHS).find(genre_slug) / "worlds" / world_slug`; room payloads via `load_room_payload(world_dir, room_id, genre_slug=...)` (`sidequest/game/room_file_loader.py:54`), raises `RoomNotFoundError`.
- Authored room shape: `sidequest-content/.../beneath_sunden/rooms/exp001.r0.yaml` (`room_type`/`name`/`description`/`entities[]`).
- Rat-tier creature: **Gnaw-Swarm** (`bestiary.yaml:51`).
- OTEL test caveat (memory): span-count tests deadlock under xdist — run affected files with `-n0`.

---

## Repo branches (create first)

- [ ] `git -C sidequest-server checkout develop && git -C sidequest-server pull --ff-only && git -C sidequest-server checkout -b feat/105-2-seam-crossing`
- [ ] `git -C sidequest-content checkout develop && git -C sidequest-content pull --ff-only && git -C sidequest-content checkout -b feat/105-2-under-the-rope`

---

### Task 1: Seam package — base types + registry

**Files:**
- Create: `sidequest-server/sidequest/game/seams/__init__.py`
- Create: `sidequest-server/sidequest/game/seams/base.py`
- Create: `sidequest-server/sidequest/game/seams/registry.py`
- Test: `sidequest-server/tests/game/test_seam_registry.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/game/test_seam_registry.py
"""Seam registry — recognition + fail-loud resolution (Story 105-2, spec §4 Piece 0)."""

import pytest

from sidequest.game.seams.base import SeamCrossingError, UnknownSeamKindError
from sidequest.game.seams.registry import get_seam_resolver, seam_route_for
from sidequest.genre.models.world import CartographyConfig, Region, Route


def _seam_cart() -> CartographyConfig:
    return CartographyConfig(
        starting_region="ropefoot",
        regions={
            "ropefoot": Region(),
            "the_dropmouth": Region(),
        },
        routes=[
            Route(
                name="Down the Rope",
                description="The one-way descent.",
                from_id="the_dropmouth",
                to_id="deep_descent",
            ),
            Route(
                name="The Dead Road",
                description="The walk back out.",
                from_id="ropefoot",
                to_id="the_outside",  # NOT a registered seam kind
            ),
        ],
    )


def test_get_seam_resolver_unknown_kind_fails_loud():
    with pytest.raises(UnknownSeamKindError) as exc:
        get_seam_resolver("warp_gate")
    assert "warp_gate" in str(exc.value)
    assert "deep_descent" in str(exc.value)  # known kinds listed, ruleset-registry style


def test_get_seam_resolver_deep_descent_registered():
    assert callable(get_seam_resolver("deep_descent"))


def test_seam_route_for_finds_seam_route():
    route = seam_route_for(_seam_cart(), "the_dropmouth")
    assert route is not None
    assert route.name == "Down the Rope"
    assert route.to_id == "deep_descent"


def test_seam_route_for_ignores_plain_routes():
    # ropefoot's route exists but its to_id is not a registered seam kind.
    assert seam_route_for(_seam_cart(), "ropefoot") is None


def test_seam_route_for_region_without_routes():
    assert seam_route_for(_seam_cart(), "nonexistent_region") is None


def test_seam_route_for_none_cartography():
    assert seam_route_for(None, "the_dropmouth") is None


def test_seam_crossing_error_carries_reason_and_surface():
    err = SeamCrossingError(reason="no_dungeon_entrance", surface="The descent has not formed.")
    assert err.reason == "no_dungeon_entrance"
    assert err.surface == "The descent has not formed."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/game/test_seam_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.game.seams'`

- [ ] **Step 3: Write the package**

```python
# sidequest/game/seams/__init__.py
"""Static→procedural seam crossings (Story 105-2 / spec 2026-06-12).

A *seam* is a cartography route whose ``to_id`` names a registered seam
kind instead of an authored region — the documented boundary where
authored space hands off to a runtime generator (the ADR-106 megadungeon
today; ADR-141 orbital scale and frontier expansion register here when
their stories land). The registry maps kind → resolver; resolvers perform
the real crossing (bind + spans) or raise ``SeamCrossingError`` — never a
silent fallback.
"""

from sidequest.game.seams.base import (
    SeamCrossingError,
    SeamCrossingResult,
    UnknownSeamKindError,
)
from sidequest.game.seams.registry import get_seam_resolver, seam_route_for

__all__ = [
    "SeamCrossingError",
    "SeamCrossingResult",
    "UnknownSeamKindError",
    "get_seam_resolver",
    "seam_route_for",
]
```

```python
# sidequest/game/seams/base.py
"""Seam crossing types — result, recoverable error, registry error."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeamCrossingResult:
    """A completed crossing: the procedural node THIS PC is now bound to."""

    to_region: str


class SeamCrossingError(Exception):
    """A crossing that cannot resolve. Recoverable + fail-loud: ``reason``
    feeds the OTEL span, ``surface`` is the honest player-facing line.
    Callers surface it; they never swallow it (No Silent Fallbacks)."""

    def __init__(self, *, reason: str, surface: str) -> None:
        super().__init__(f"seam crossing unresolvable: {reason}")
        self.reason = reason
        self.surface = surface


class UnknownSeamKindError(Exception):
    """A route's ``to_id`` named a seam kind with no registered resolver."""
```

```python
# sidequest/game/seams/registry.py
"""Seam-kind registry — mirrors sidequest/game/ruleset/registry.py.

New kinds register here as their plans land (ADR-141 orbital jump,
ADR-106 frontier expansion). Do NOT stub future kinds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from sidequest.game.seams.base import UnknownSeamKindError
from sidequest.game.seams.deep_descent import resolve_deep_descent

if TYPE_CHECKING:
    from sidequest.genre.models.world import CartographyConfig, Route

# A resolver performs the real crossing or raises SeamCrossingError.
# Signature contract (kw-only): resolve(*, snapshot, player_name, route,
# resolved_via, **context) -> SeamCrossingResult. ``context`` carries
# kind-specific dependencies (deep_descent needs ``dungeon_store``).
SeamResolver = Callable[..., Any]

_REGISTRY: dict[str, SeamResolver] = {
    "deep_descent": resolve_deep_descent,
}


def get_seam_resolver(kind: str) -> SeamResolver:
    """Resolve a registered seam kind. Fails loud — never a default."""
    resolver = _REGISTRY.get(kind)
    if resolver is None:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise UnknownSeamKindError(
            f"Unknown seam kind {kind!r}; registered kinds: {known}"
        )
    return resolver


def seam_route_for(cartography: CartographyConfig | None, region_id: str) -> Route | None:
    """The seam route owned by ``region_id``, or None.

    A seam route is one whose ``from_id`` is this region and whose
    ``to_id`` names a REGISTERED seam kind. Plain routes (authored
    region → authored region) are never seam routes. Returns the first
    match — a region owning two seam routes is a content error the pack
    validator owns, not this helper.
    """
    if cartography is None:
        return None
    for route in cartography.routes:
        if route.from_id == region_id and (route.to_id or "") in _REGISTRY:
            return route
    return None
```

Note: `registry.py` imports `deep_descent` — Task 2 creates it. To keep Task 1 green in isolation, Task 1 may create `deep_descent.py` with the real implementation from Task 2 directly (the tasks are sequenced in one branch; do Task 2's module first if running strictly in order, or accept Task 1 red until Task 2's file exists — preferred: write both modules, then run both test files).

- [ ] **Step 4: Run tests (after Task 2's module exists) and verify pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_seam_registry.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/seams/ tests/game/test_seam_registry.py
git -C sidequest-server commit -m "feat(105-2): seam registry — static→procedural crossing kinds (spec §4 Piece 0)"
```

---

### Task 2: `deep_descent` resolver (the extracted 59-12 bind)

**Files:**
- Create: `sidequest-server/sidequest/game/seams/deep_descent.py`
- Test: `sidequest-server/tests/game/test_seam_deep_descent.py`

- [ ] **Step 1: Write the failing tests**

Use the existing movement-test fixtures as the template for a snapshot +
in-memory store — see `tests/agents/subsystems/test_movement*.py` for the
established `GameSnapshot` fixture shape and any in-memory `DungeonStore`
double already used there (reuse it; do not invent a new fake).

```python
# tests/game/test_seam_deep_descent.py
"""deep_descent resolver — bind-to-entrance or fail loud (Story 105-2)."""

import pytest

from sidequest.dungeon.region_graph.model import RegionGraph, RegionNode
from sidequest.game.seams.base import SeamCrossingError
from sidequest.game.seams.deep_descent import resolve_deep_descent
from sidequest.genre.models.world import Route

SEAM_ROUTE = Route(
    name="Down the Rope",
    description="The one-way descent.",
    from_id="the_dropmouth",
    to_id="deep_descent",
)


class _StoreWithEntrance:
    def load_map(self, *, entrance_id):
        g = RegionGraph(entrance_id=entrance_id)
        g.add_node(RegionNode(id=entrance_id, expansion_id=0, theme="shaft_collar"))
        return g


class _EmptyStore:
    def load_map(self, *, entrance_id):
        return RegionGraph(entrance_id=entrance_id)  # no nodes — corrupt seed


def test_resolves_to_entrance_and_binds_pc(snapshot_on_surface):  # fixture: PC at the_dropmouth
    result = resolve_deep_descent(
        snapshot=snapshot_on_surface,
        player_name="Groucho",
        route=SEAM_ROUTE,
        resolved_via="surface_descent",
        dungeon_store=_StoreWithEntrance(),
    )
    assert result.to_region == "entrance"
    assert snapshot_on_surface.region_for(perspective="Groucho") == "entrance"


def test_no_store_fails_loud(snapshot_on_surface):
    with pytest.raises(SeamCrossingError) as exc:
        resolve_deep_descent(
            snapshot=snapshot_on_surface,
            player_name="Groucho",
            route=SEAM_ROUTE,
            resolved_via="surface_descent",
            dungeon_store=None,
        )
    assert exc.value.reason == "no_dungeon_store"
    assert snapshot_on_surface.region_for(perspective="Groucho") == "the_dropmouth"


def test_corrupt_seed_fails_loud(snapshot_on_surface):
    with pytest.raises(SeamCrossingError) as exc:
        resolve_deep_descent(
            snapshot=snapshot_on_surface,
            player_name="Groucho",
            route=SEAM_ROUTE,
            resolved_via="surface_descent",
            dungeon_store=_EmptyStore(),
        )
    assert exc.value.reason == "no_dungeon_entrance"
    assert snapshot_on_surface.region_for(perspective="Groucho") == "the_dropmouth"
```

(Write the `snapshot_on_surface` fixture in this file or a local conftest by
copying the minimal-snapshot construction from the movement tests: a
`GameSnapshot` with `pc_regions={"Groucho": "the_dropmouth"}`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/game/test_seam_deep_descent.py -v`
Expected: FAIL — `ImportError` (module/function missing)

- [ ] **Step 3: Write the resolver**

```python
# sidequest/game/seams/deep_descent.py
"""The deep_descent seam resolver — Story 59-12's surface→deep bind,
extracted from movement.py so BOTH entry doors (movement dispatch +
narration-guard recovery) share one crossing implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sidequest.dungeon.seed_bootstrap import ENTRANCE_ID
from sidequest.game.seams.base import SeamCrossingError, SeamCrossingResult
from sidequest.game.session import WorldStatePatch
from sidequest.telemetry.spans import movement_resolved_span

if TYPE_CHECKING:
    from sidequest.game.session import GameSnapshot
    from sidequest.genre.models.world import Route

logger = logging.getLogger(__name__)


def resolve_deep_descent(
    *,
    snapshot: GameSnapshot,
    player_name: str,
    route: Route,
    resolved_via: str,
    dungeon_store: Any = None,
    direction: str = "deeper",
    exit_descriptor: str = "",
    **_context: Any,
) -> SeamCrossingResult:
    """Bind THIS PC onto the dungeon entrance node, or raise.

    The per-PC ``WorldStatePatch(pc_region=...)`` path fires
    ``notify_region_transition`` → frontier observer → look-ahead worker,
    exactly as the 59-12 handoff did. Emits ``movement.resolved`` with
    ``seam_kind`` so the GM panel reads every seam the same way.
    """
    from_region = snapshot.region_for(perspective=player_name) or ""
    if dungeon_store is None:
        raise SeamCrossingError(
            reason="no_dungeon_store",
            surface=(
                "The way down exists, but the deep beneath it has not "
                "been opened — this is a wiring fault, not a closed door."
            ),
        )
    graph = dungeon_store.load_map(entrance_id=ENTRANCE_ID)
    entrance_id = graph.entrance_id
    if entrance_id not in graph.nodes:
        raise SeamCrossingError(
            reason="no_dungeon_entrance",
            surface="The descent into the depths has not yet formed.",
        )
    snapshot.apply_world_patch(WorldStatePatch(pc_region={player_name: entrance_id}))
    with movement_resolved_span(
        pc_name=player_name,
        from_region=from_region,
        to_region=entrance_id,
    ) as span:
        span.set_attribute("intent.direction", direction)
        span.set_attribute("intent.exit_descriptor", exit_descriptor)
        span.set_attribute("resolved_via", resolved_via)
        span.set_attribute("seam_kind", str(route.to_id or ""))
        span.set_attribute("seam_route_name", route.name)
        span.set_attribute("candidate_exits", [entrance_id])
        span.set_attribute("edge_kind", "surface_descent")
        span.set_attribute("target_pre_materialized", True)
        span.set_attribute("materialize_triggered", True)
        span.set_attribute("party_split_after", snapshot.region_for() is None)
    logger.debug(
        "seam.crossing kind=%s pc=%s from=%s to=%s via=%s",
        route.to_id,
        player_name,
        from_region,
        entrance_id,
        resolved_via,
    )
    return SeamCrossingResult(to_region=entrance_id)
```

- [ ] **Step 4: Run both seam test files, verify pass**

Run: `cd sidequest-server && uv run pytest tests/game/test_seam_registry.py tests/game/test_seam_deep_descent.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/game/seams/deep_descent.py tests/game/test_seam_deep_descent.py
git -C sidequest-server commit -m "feat(105-2): deep_descent resolver — 59-12 bind extracted behind the seam registry"
```

---

### Task 3: movement.py consumes the registry (the hybrid fix)

**Files:**
- Modify: `sidequest-server/sidequest/agents/subsystems/movement.py:141-161` (region-mode block) and `:214-269` (59-12 block)
- Test: `sidequest-server/tests/agents/subsystems/test_movement_seam_crossing.py`

- [ ] **Step 1: Write the failing tests**

Build the fixture as a *hybrid* world: pack whose world has region-mode
cartography (copy the `_seam_cart()` shape from Task 1, adding it to a
minimal `GenrePack`/world object the existing movement tests already
construct) + the `_StoreWithEntrance` store from Task 2 + a palette double
(movement tests already have one — reuse).

```python
# tests/agents/subsystems/test_movement_seam_crossing.py
"""Hybrid-world movement: region-mode + seam route crosses; seam-less defers.

Story 105-2 AC1 + AC5. Root cause #1: de4f85c8's region_mode_deferred
early-return dead-coded the 59-12 handoff for beneath_sunden. These tests
pin the fix: a region-mode world WITH a seam route + live store crosses;
oz-shaped worlds (no seam route) defer exactly as before.
"""
import pytest

from sidequest.agents.subsystems.movement import run_movement_dispatch
from sidequest.protocol.dispatch import SubsystemDispatch


def _movement(direction: str, descriptor: str = "") -> SubsystemDispatch:
    return SubsystemDispatch(
        subsystem="movement",
        params={"direction": direction, "exit_descriptor": descriptor},
    )


@pytest.mark.parametrize(
    "direction,descriptor",
    [("deeper", ""), ("toward_exit", ""), ("deeper", "down the rope")],
)
async def test_seam_region_movement_crosses_to_entrance(
    hybrid_world_kit, direction, descriptor
):
    kit = hybrid_world_kit  # snapshot(PC at the_dropmouth) + pack + store + palette
    out = await run_movement_dispatch(
        _movement(direction, descriptor),
        snapshot=kit.snapshot,
        player_name="Groucho",
        dungeon_store=kit.store,
        palette=kit.palette,
        pack=kit.pack,
    )
    assert out.data["resolved_via"] == "surface_descent"
    assert out.data["to_region"] == "entrance"
    assert kit.snapshot.region_for(perspective="Groucho") == "entrance"


async def test_seam_region_back_does_not_cross(hybrid_world_kit):
    kit = hybrid_world_kit
    out = await run_movement_dispatch(
        _movement("back"),
        snapshot=kit.snapshot,
        player_name="Groucho",
        dungeon_store=kit.store,
        palette=kit.palette,
        pack=kit.pack,
    )
    # back is surface adjacency — defer to the heading→region path as today.
    assert out.data["resolved_via"] == "region_mode_deferred"
    assert kit.snapshot.region_for(perspective="Groucho") == "the_dropmouth"


async def test_non_seam_region_mode_world_still_defers(oz_shaped_kit):
    # Region-mode world with NO seam routes (oz/wonderland shape) — the
    # de4f85c8 defer is unchanged. AC5 non-regression.
    kit = oz_shaped_kit
    out = await run_movement_dispatch(
        _movement("deeper"),
        snapshot=kit.snapshot,
        player_name="Dorothy",
        dungeon_store=None,
        palette=None,
        pack=kit.pack,
    )
    assert out.data["resolved_via"] == "region_mode_deferred"


async def test_seam_region_with_dead_store_fails_loud(hybrid_world_kit_empty_store):
    kit = hybrid_world_kit_empty_store
    out = await run_movement_dispatch(
        _movement("deeper"),
        snapshot=kit.snapshot,
        player_name="Groucho",
        dungeon_store=kit.store,
        palette=kit.palette,
        pack=kit.pack,
    )
    assert out.data["error"] == "no_dungeon_entrance"
    assert kit.snapshot.region_for(perspective="Groucho") == "the_dropmouth"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd sidequest-server && uv run pytest tests/agents/subsystems/test_movement_seam_crossing.py -v`
Expected: FAIL — crossing tests get `region_mode_deferred` instead of `surface_descent`

- [ ] **Step 3: Implement — seam check inside the region-mode block**

In `movement.py`, add imports:

```python
from sidequest.game.seams import SeamCrossingError, get_seam_resolver, seam_route_for
```

Add a cartography accessor next to `_is_region_mode_world` (extract the
probe both share):

```python
def _cartography_for(*, pack: GenrePack | None, world_slug: str):
    """The active world's cartography, or None (same probe shape as
    _is_region_mode_world — keep the discriminator single-shaped)."""
    if pack is None or not world_slug:
        return None
    worlds = getattr(pack, "worlds", None)
    if worlds is None:
        return None
    return getattr(worlds.get(world_slug), "cartography", None)
```

(Refactor `_is_region_mode_world` to call it.) Then, inside the
region-mode block at `movement.py:141`, BEFORE the deferred return:

```python
    if _is_region_mode_world(pack=pack, world_slug=snapshot.world_slug):
        from_region = snapshot.region_for(perspective=player_name) or ""
        # --- Story 105-2: the hybrid case de4f85c8 didn't anticipate. ---
        # A region-mode world whose current region owns a registered seam
        # route (beneath_sunden: the_dropmouth → deep_descent) IS the
        # static→procedural boundary. Descent-shaped intents cross HERE —
        # deferring them to the heading→region path is what made the
        # 59-12 handoff dead code and the Deep unreachable (epic 105).
        # ``back`` stays deferred: it is surface adjacency, not a seam.
        cart = _cartography_for(pack=pack, world_slug=snapshot.world_slug)
        seam_route = seam_route_for(cart, from_region)
        if seam_route is not None and direction != "back":
            try:
                crossing = get_seam_resolver(str(seam_route.to_id))(
                    snapshot=snapshot,
                    player_name=player_name,
                    route=seam_route,
                    resolved_via="surface_descent",
                    dungeon_store=dungeon_store,
                    direction=direction,
                    exit_descriptor=exit_descriptor,
                )
            except SeamCrossingError as err:
                return _unresolved(
                    snapshot=snapshot,
                    player_name=player_name,
                    reason=err.reason,
                    from_region=from_region,
                    direction=direction,
                    exit_descriptor=exit_descriptor,
                    available=[],
                    surface=err.surface,
                )
            return SubsystemOutput(
                data={
                    "to_region": crossing.to_region,
                    "from_region": from_region,
                    "resolved_via": "surface_descent",
                }
            )
        # ... existing movement_region_mode_span + deferred return, unchanged ...
```

- [ ] **Step 4: Replace the 59-12 block's body with the resolver (one implementation, two doors)**

At `movement.py:214-269`, keep the structure (`surface_no_route` fail for
non-descent stays) but replace the inline bind (lines 229-269) with:

```python
        try:
            crossing = resolve_deep_descent(
                snapshot=snapshot,
                player_name=player_name,
                route=Route(
                    name="surface descent",
                    description="room-graph surface→deep handoff (59-12)",
                    from_id=from_region,
                    to_id="deep_descent",
                ),
                resolved_via="surface_descent",
                dungeon_store=dungeon_store,
                direction=direction,
                exit_descriptor=exit_descriptor,
            )
        except SeamCrossingError as err:
            return _unresolved(
                snapshot=snapshot,
                player_name=player_name,
                reason=err.reason,
                from_region=from_region,
                direction=direction,
                exit_descriptor=exit_descriptor,
                available=[],
                surface=err.surface,
            )
        return SubsystemOutput(
            data={
                "to_region": crossing.to_region,
                "from_region": from_region,
                "resolved_via": "surface_descent",
            }
        )
```

(Import `resolve_deep_descent` and `Route` at the top; the room-graph door
has no cartography route object, so it constructs the synthetic descriptor —
the span's `seam_kind` stays `deep_descent` either way.)

- [ ] **Step 5: Run new tests + ALL existing movement tests**

Run: `cd sidequest-server && uv run pytest tests/agents/subsystems/ -k movement -v -n0`
Expected: new file PASS; every pre-existing movement test (including the
59-12 surface-descent tests and the oz region-mode-defer tests) PASS unchanged.

- [ ] **Step 6: Commit**

```bash
git -C sidequest-server add sidequest/agents/subsystems/movement.py tests/agents/subsystems/test_movement_seam_crossing.py
git -C sidequest-server commit -m "fix(105-2): hybrid worlds cross the seam — region-mode defer no longer dead-codes the 59-12 handoff"
```

---

### Task 4: Router gets `current_region_exits` (the lexical bridge)

**Files:**
- Modify: `sidequest-server/sidequest/server/intent_router_pass.py` (`_build_state_summary`, after the `confrontation_types` projection ~line 339)
- Modify: `sidequest-server/sidequest/telemetry/spans/` (the module exporting `intent_router_confrontation_vocabulary_span` — add `intent_router_region_exits_span` beside it, same shape)
- Modify: `sidequest-server/sidequest/agents/intent_router.py:162-172` (movement param description — one sentence)
- Test: `sidequest-server/tests/server/test_intent_router_region_exits.py`

- [ ] **Step 1: Write the failing tests**

Mirror the fixture style of the existing `_build_state_summary` tests
(find them: `grep -rn "_build_state_summary" tests/server/ | head`) —
reuse their snapshot/pack construction.

```python
# tests/server/test_intent_router_region_exits.py
"""current_region_exits projection (Story 105-2 Piece 2, 59-27 pattern)."""

from sidequest.server.intent_router_pass import _build_state_summary


def test_seam_region_summary_names_the_exit(hybrid_world_kit):
    kit = hybrid_world_kit  # PC at the_dropmouth (same kit as movement tests)
    summary = _build_state_summary(kit.snapshot, pack=kit.pack)
    exits = summary["current_region_exits"]
    assert {"name": "Down the Rope", "kind": "seam"} in exits


def test_adjacent_regions_listed(hybrid_world_kit_at_ropefoot):
    kit = hybrid_world_kit_at_ropefoot
    summary = _build_state_summary(kit.snapshot, pack=kit.pack)
    kinds = {(e["name"], e["kind"]) for e in summary["current_region_exits"]}
    assert ("The Dropmouth", "adjacent") in kinds  # cart region's display name


def test_no_cartography_no_projection(plain_snapshot_and_pack):
    snapshot, pack = plain_snapshot_and_pack
    summary = _build_state_summary(snapshot, pack=pack)
    assert "current_region_exits" not in summary
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_intent_router_region_exits.py -v`
Expected: FAIL — `KeyError: 'current_region_exits'`

- [ ] **Step 3: Implement the projection**

In `_build_state_summary`, after the witnessed-act block (~line 363):

```python
    # Story 105-2 (Piece 2): the PC's current cartography region's actual
    # exits — adjacency neighbors + seam routes. The 2026-06-12 dive's
    # turn-3 miss happened because the router was asked to recognize a
    # descent it was never told existed; this is the lexical bridge
    # (59-27 precedent: authored vocabulary beats inference).
    if pack is not None:
        _worlds = getattr(pack, "worlds", None)
        _world = _worlds.get(snapshot.world_slug) if _worlds else None
        _cart = getattr(_world, "cartography", None)
        _region_id = snapshot.region_for() or ""
        _region = _cart.regions.get(_region_id) if _cart else None
        if _region is not None:
            exits: list[dict[str, str]] = []
            for adj_id in getattr(_region, "adjacent", None) or []:
                adj = _cart.regions.get(adj_id)
                exits.append(
                    {"name": getattr(adj, "name", None) or adj_id, "kind": "adjacent"}
                )
            for r in _cart.routes:
                if r.from_id == _region_id and seam_route_for(_cart, _region_id) is r:
                    exits.append({"name": r.name, "kind": "seam"})
            if exits:
                summary["current_region_exits"] = exits
                with intent_router_region_exits_span(
                    exit_count=len(exits),
                    seam_count=sum(1 for e in exits if e["kind"] == "seam"),
                    region_id=_region_id,
                    genre_slug=snapshot.genre_slug or "",
                ):
                    pass
```

(Import `seam_route_for` from `sidequest.game.seams`. Check the `Region`
model for the `adjacent` field name first — `grep -n "adjacent" sidequest/genre/models/world.py`;
if the model stores it under extras, read it via `getattr` as shown.)

New span helper — copy `intent_router_confrontation_vocabulary_span`'s
implementation exactly, named `intent_router_region_exits_span`, span name
`intent_router.region_exits`, attrs `exit_count`/`seam_count`/`region_id`/`genre_slug`.

Prompt nudge in `intent_router.py` movement section (after line 168's
`exit_descriptor` description, inside the same string):

```
         When game_state.current_region_exits is present it lists the
         REAL exits from where the party stands; an action that takes,
         descends, or follows one of them IS movement — name it in
         exit_descriptor. A "seam" exit leads down into the underworld:
         going down it is direction "deeper".
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd sidequest-server && uv run pytest tests/server/test_intent_router_region_exits.py -v -n0`
Expected: PASS. Also run the existing summary tests:
`uv run pytest tests/server/ -k "state_summary or intent_router" -n0 -v` — all PASS.

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/server/intent_router_pass.py sidequest/agents/intent_router.py sidequest/telemetry/spans/ tests/server/test_intent_router_region_exits.py
git -C sidequest-server commit -m "feat(105-2): router sees the region's real exits — current_region_exits projection + span"
```

---

### Task 5: narration_apply guard — recover the crossing or fail loud

**Files:**
- Modify: `sidequest-server/sidequest/server/narration_apply.py` (`_apply_narration_result_to_snapshot` signature + the `elif _is_region_mode_world:` branch at `:3848`)
- Modify: `sidequest-server/sidequest/server/websocket_session_handler.py:~1080` (`_apply_kwargs` — thread `lookahead_handle=sd.lookahead_handle`)
- Test: `sidequest-server/tests/server/test_narration_seam_recovery.py`

- [ ] **Step 1: Write the failing tests**

Mirror the 90-6 test file's fixture style (find it:
`grep -rln "entry_skipped_sub_location" tests/` — reuse its
narration-result construction and region-mode world fixture).

```python
# tests/server/test_narration_seam_recovery.py
"""Seam recovery at the narration guard (Story 105-2 Piece 4, AC1/AC2).

The turn-3 repro: router emitted NO movement dispatch; the narrator
patched location to "The Dropmouth — The Deep" (a confabulated deep).
The guard must treat that patch as the missed relocation signal: perform
the REAL crossing, or fail loud — never accept the confabulation.
"""


async def test_unresolved_heading_on_seam_region_recovers_crossing(
    hybrid_apply_kit,  # snapshot(PC at the_dropmouth) + room + pack + lookahead handle w/ live store
):
    kit = hybrid_apply_kit
    result = kit.narration_result(location="The Dropmouth — The Deep")
    kit.apply(result)  # _apply_narration_result_to_snapshot(..., lookahead_handle=kit.handle)
    assert kit.snapshot.region_for(perspective="Groucho") == "entrance"
    # The confabulated heading must NOT pollute the surface graph.
    assert "The Dropmouth — The Deep" not in kit.snapshot.discovered_regions


async def test_recovery_reanchors_scene_to_authored_room_name(hybrid_apply_kit):
    kit = hybrid_apply_kit  # kit's world_dir has rooms/entrance.yaml name: "Under the Rope"
    result = kit.narration_result(location="The Dropmouth — The Deep")
    kit.apply(result)
    assert result.location == "Under the Rope"  # mutated in place pre-apply


async def test_dead_store_rejects_patch_loud(hybrid_apply_kit_empty_store):
    kit = hybrid_apply_kit_empty_store
    result = kit.narration_result(location="The Dropmouth — The Deep")
    kit.apply(result)
    assert kit.snapshot.region_for(perspective="Groucho") == "the_dropmouth"
    assert "The Dropmouth — The Deep" not in kit.snapshot.discovered_regions
    # span asserted via the watcher/span capture fixture the 90-6 tests use:
    kit.assert_span("region.entry_rejected", reason="seam_crossing_unresolvable")


async def test_seamless_region_mode_world_unchanged(oz_apply_kit):
    # 90-6 non-regression: a POI re-title in a seam-less region-mode world
    # still hits entry_skipped_sub_location and same-region drift.
    kit = oz_apply_kit
    result = kit.narration_result(location="Emerald City — Inside the Gates")
    kit.apply(result)
    kit.assert_span("region.entry_rejected", reason="sub_location_in_region_mode_world")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_seam_recovery.py -v -n0`
Expected: FAIL — recovery tests find PC still at `the_dropmouth`

- [ ] **Step 3: Implement**

(a) Signature: add to `_apply_narration_result_to_snapshot`
(`narration_apply.py:3427`):

```python
    lookahead_handle: "LookaheadWorkerHandle | None" = None,
```

with the `TYPE_CHECKING` import `from sidequest.dungeon.lookahead_worker import LookaheadWorkerHandle`.

(b) Call site: in `_apply_kwargs` (`websocket_session_handler.py:~1080`) add:

```python
                        # Story 105-2: the seam-recovery guard needs the
                        # dungeon store (handle.persistence) to perform a
                        # missed crossing instead of accepting a
                        # confabulated deep. None for non-dungeon worlds.
                        lookahead_handle=sd.lookahead_handle,
```

(c) The guard, at the TOP of the `elif _is_region_mode_world:` branch
(`narration_apply.py:3848`), before the existing skip-span block:

```python
            elif _is_region_mode_world:
                # --- Story 105-2: seam recovery. The PC stands on a region
                # owning a static→procedural seam route and the narrator has
                # minted a heading that resolves to NO cartography region.
                # That heading IS the relocation signal the intent router
                # missed (the 2026-06-12 turn-3 repro: "The Dropmouth — The
                # Deep"). An engine MUST NOT narrate a crossing it did not
                # perform: do the real crossing now, or reject the patch
                # loud. Never accept the confabulated scene.
                _pc_region = snapshot.region_for(perspective=player_name) or ""
                _seam_route = seam_route_for(_region_cart, _pc_region)
                if _seam_route is not None:
                    try:
                        _crossing = get_seam_resolver(str(_seam_route.to_id))(
                            snapshot=snapshot,
                            player_name=player_name,
                            route=_seam_route,
                            resolved_via="narration_seam_recovery",
                            dungeon_store=(
                                lookahead_handle.persistence
                                if lookahead_handle is not None
                                else None
                            ),
                        )
                    except SeamCrossingError as _seam_err:
                        with region_entry_rejected_span(
                            entry=result.location,
                            reason="seam_crossing_unresolvable",
                            caller_path="narration_apply.location_update",
                            player_name=player_name,
                        ):
                            logger.error(
                                "region.seam_crossing_unresolvable entry=%r pc=%s "
                                "region=%s seam=%s reason=%s — location patch "
                                "REJECTED (No Silent Fallbacks)",
                                result.location,
                                player_name,
                                _pc_region,
                                _seam_route.to_id,
                                _seam_err.reason,
                            )
                        result.location = ""  # patch dropped; PC stays put, honestly
                    else:
                        # Crossing performed (pc_region patch + spans fired by
                        # the resolver). Re-anchor the scene to the authored
                        # entrance room's name so the narration record carries
                        # the REAL room, not the confabulation.
                        result.location = _entrance_room_name(
                            crossing_region=_crossing.to_region,
                            lookahead_handle=lookahead_handle,
                        )
                        _same_region_drift = False
                else:
                    # ... the ENTIRE existing 90-6 skip block, unchanged,
                    # indented under this else ...
```

(d) The room-name helper (module level, near `_extract_leading_bold_title`):

```python
def _entrance_room_name(*, crossing_region: str, lookahead_handle) -> str:
    """The authored entrance room's display name for the scene re-anchor.

    Loads ``rooms/<region>.yaml`` via the same loader path map_emit uses.
    A missing authored room is LOUD (warning + raw region id as the title)
    but not fatal — the crossing itself already happened mechanically.
    """
    from sidequest.game.room_file_loader import RoomNotFoundError, load_room_payload
    from sidequest.genre.loader import DEFAULT_GENRE_PACK_SEARCH_PATHS, GenreLoader

    if lookahead_handle is None or not lookahead_handle.genre_slug:
        return crossing_region
    try:
        loader = GenreLoader(search_paths=DEFAULT_GENRE_PACK_SEARCH_PATHS)
        world_dir = (
            loader.find(lookahead_handle.genre_slug)
            / "worlds"
            / lookahead_handle.world_slug
        )
        payload = load_room_payload(
            world_dir, crossing_region, genre_slug=lookahead_handle.genre_slug
        )
        return str(payload.get("name") or crossing_region)
    except (RoomNotFoundError, Exception) as exc:  # noqa: BLE001 — loud, non-fatal
        logger.warning(
            "seam.entrance_room_name_unresolved region=%s error=%s — "
            "authored entrance room missing; using region id as scene title "
            "(author rooms/%s.yaml — spec 2026-06-12 §4 Piece 1)",
            crossing_region,
            exc,
            crossing_region,
        )
        return crossing_region
```

Imports at the top of narration_apply.py:
`from sidequest.game.seams import SeamCrossingError, get_seam_resolver, seam_route_for`.

**Verify during implementation (flagged unknowns):** (1) confirm where
`result.location` is consumed *after* this branch (the `state.location_update`
log at `:3910` and any `character_locations` assignment) — the mutated /
emptied value must flow through; setting `result.location = ""` must cleanly
no-op the downstream apply (check the `if result.location:` outer gate).
(2) `result.location` mutability — `NarrationTurnResult` is the orchestrator
dataclass/pydantic model; if frozen, carry the override in a local and apply
it where the location lands instead of mutating.

- [ ] **Step 4: Run new tests + 90-6 suite + full server suite**

Run: `cd sidequest-server && uv run pytest tests/server/test_narration_seam_recovery.py -v -n0`
Expected: PASS
Run: `cd sidequest-server && uv run pytest tests/server/ -k "region or location or narration_apply" -n0`
Expected: PASS (90-6 + 45-17 dedup + region-advance tests all green)

- [ ] **Step 5: Commit**

```bash
git -C sidequest-server add sidequest/server/narration_apply.py sidequest/server/websocket_session_handler.py tests/server/test_narration_seam_recovery.py
git -C sidequest-server commit -m "feat(105-2): narration guard recovers missed seam crossings — never narrate across a seam the engine didn't cross"
```

---

### Task 6: Content — author "Under the Rope" (`rooms/entrance.yaml`)

**Files:**
- Create: `sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden/rooms/entrance.yaml`

- [ ] **Step 1: Write the room** (match `exp001.r0.yaml`'s exact shape)

```yaml
room_type: settlement
name: Under the Rope
description: 'The rope ends here. Above, the collar of the shaft is a coin

  of grey light, too far to read faces by. The floor is a fan of everything

  that ever fell: rotted cord, a boot with the buckle still done, bones

  sorted by the water into sizes.


  Something small moves in the bone-drifts when the light does. Then more

  than one something.


  Three mouths of dark lead away from the landing, and none of them are

  marked, because everyone who could have marked them was going down for

  the first time too.'
entities:
- id: the_ropes_end
  label: The rope ends here, knotted to a rust-bled ring bolt.
  tier: real_object
  binding:
    kind: location_feature
    ref: the_ropes_end
  affordances:
  - "The only way back up. Cutting, burning, or losing it is committing to the deep."
  provenance: authored
  promoted_at_turn: null
  promoted_canon: null
  reference_url: /reference/lore/caverns_and_claudes/beneath_sunden#location-the-ropes-end
- id: bone_drifts
  label: Bone-drifts sorted by old water, stirring where the light moves.
  tier: real_object
  binding:
    kind: location_feature
    ref: bone_drifts
  affordances:
  - "Disturbing the drifts wakes the Gnaw-Swarm — an easy first fight, on purpose."
  provenance: authored
  promoted_at_turn: null
  promoted_canon: null
  reference_url: /reference/lore/caverns_and_claudes/beneath_sunden#location-bone-drifts
- id: fallen_delvers_boot
  label: A boot with the buckle still done.
  tier: flavor_only
  binding: null
  affordances: []
  provenance: authored
  promoted_at_turn: null
  promoted_canon: null
  reference_url: /reference/lore/caverns_and_claudes/beneath_sunden#location-a-boot-with-the-buckle-still-done
```

- [ ] **Step 2: Verify it loads through the production loader**

Run (one-off verification, not a committed test — content invariants belong
to the pack validator):

```bash
cd sidequest-server && uv run python -c "
from pathlib import Path
from sidequest.game.room_file_loader import load_room_payload
p = load_room_payload(Path('../sidequest-content/genre_packs/caverns_and_claudes/worlds/beneath_sunden'), 'entrance', genre_slug='caverns_and_claudes')
print(p['name'], '—', len(p['entities']), 'entities')"
```

Expected: `Under the Rope — 3 entities`. If `provenance: authored` fails
validation, check the `LocationEntity` model's accepted values
(`grep -n "provenance" sidequest/protocol/models.py`) and use the nearest
honest value (`cookbook` is what the materializer emits).

- [ ] **Step 3: Confirm the freeze invariant protects the file**

The materializer never emits for expansion 0 (`materializer.py:588`), and
`write_room_yaml` raises `FileExistsError` on existing files — no action
needed, just do not name the file anything other than `entrance.yaml`
(it must equal `seed_bootstrap.ENTRANCE_ID`).

- [ ] **Step 4: Commit (content repo)**

```bash
git -C sidequest-content add genre_packs/caverns_and_claudes/worlds/beneath_sunden/rooms/entrance.yaml
git -C sidequest-content commit -m "feat(105-2): author Under the Rope — the deep's entrance room (rat-tier landing, spec §4 Piece 1)"
```

---

### Task 7: Wiring test — production path end-to-end

**Files:**
- Test: `sidequest-server/tests/integration/test_seam_crossing_wiring.py`

- [ ] **Step 1: Write the wiring test**

Per the repo's wiring-test doctrine (fixture-driven behavior + span
assertions, never source-grep). Drive the REAL production functions:

```python
# tests/integration/test_seam_crossing_wiring.py
"""Story 105-2 wiring: the seam crossing is reachable from production
paths — the dispatch bank door AND the narration-guard door — and the
registry is populated at import time."""


def test_deep_descent_registered_at_import():
    from sidequest.game.seams.registry import _REGISTRY

    assert "deep_descent" in _REGISTRY


async def test_dispatch_bank_reaches_the_crossing(hybrid_world_kit):
    # Through run_dispatch_bank (the production bank movement.py is wired
    # into), not run_movement_dispatch directly.
    from sidequest.agents.subsystems import run_dispatch_bank

    kit = hybrid_world_kit
    package = kit.dispatch_package(  # movement{deeper} for Groucho
        subsystem="movement", params={"direction": "deeper", "exit_descriptor": "down the rope"}
    )
    await run_dispatch_bank(
        package,
        context={
            "snapshot": kit.snapshot,
            "pack": kit.pack,
            "player_name": "Groucho",
            "npcs_present": [],
            "additional_player_names": [],
            "npc_pool": [],
            "npcs": [],
            "dungeon_store": kit.store,
            "palette": kit.palette,
            "lookahead_handle": None,
            "turn_number": 3,
        },
    )
    assert kit.snapshot.region_for(perspective="Groucho") == "entrance"


async def test_apply_pipeline_reaches_the_guard(hybrid_apply_kit):
    # Through _apply_narration_result_to_snapshot with the threaded handle —
    # the exact production call shape (websocket_session_handler.py:1101).
    kit = hybrid_apply_kit
    result = kit.narration_result(location="The Dropmouth — The Deep")
    kit.apply(result)  # passes lookahead_handle=kit.handle
    assert kit.snapshot.region_for(perspective="Groucho") == "entrance"
```

- [ ] **Step 2: Run, fix any wiring gap, verify pass**

Run: `cd sidequest-server && uv run pytest tests/integration/test_seam_crossing_wiring.py -v -n0`
Expected: PASS. A failure here is a REAL wiring gap (e.g. the bank not
threading a kwarg) — fix the wiring, never the test.

- [ ] **Step 3: Commit**

```bash
git -C sidequest-server add tests/integration/test_seam_crossing_wiring.py
git -C sidequest-server commit -m "test(105-2): seam-crossing wiring — both production doors reach the registry"
```

---

### Task 8: Full gate + PRs

- [ ] **Step 1: Full server check**

Run: `cd sidequest-server && uv run ruff format . && uv run ruff check . && uv run pyright && uv run pytest`
Expected: clean (known pre-existing failures per memory:
`test_message_type_complete_count` 54-vs-55 is unrelated; OTEL span-count
files may need `-n0` reruns to confirm).

- [ ] **Step 2: Push + PRs (both target `develop`)**

```bash
git -C sidequest-server push -u origin feat/105-2-seam-crossing
gh pr create -R slabgorb-org/sidequest-server --base develop --title "105-2: seam registry — deterministic surface→deep crossing" \
  --body "Spec: orc-quest docs/superpowers/specs/2026-06-12-surface-deep-crossing-design.md (rev 2). Registry + deep_descent resolver; movement hybrid fix (de4f85c8 dead-code); narration-guard recovery; router region-exits projection. AC4 (59-15 live span-proof) verifies after 105-1 lands."
git -C sidequest-content push -u origin feat/105-2-under-the-rope
gh pr create -R slabgorb-org/sidequest-content --base develop --title "105-2: author Under the Rope — beneath_sunden entrance room" \
  --body "The deep's first room (spec §4 Piece 1): authored landing + rat-tier Gnaw-Swarm hook. Pairs with sidequest-server feat/105-2-seam-crossing."
```

- [ ] **Step 3: AC4 deferred-verification note**

AC4 (live span-proof via `scenarios/beneath_sunden_engagement.yaml`) runs
only after **105-1** lands the playtest-driver fix. Record in the session
file: "AC4 pending 105-1; verify with `just playtest-scenario
beneath_sunden_engagement` → expect `movement.resolved`
(`resolved_via=surface_descent`, `seam_kind=deep_descent`),
`frontier.region_transition` surface→entrance, `discovered_regions>0`,
`dispatch_engagement.*.mismatch == 0`."

---

## Self-review notes (already applied)

- **Spec coverage:** Piece 0 → Tasks 1-2; Piece 1 → Task 6; Piece 2 → Task 4;
  Piece 3 → Task 3; Piece 4 → Task 5; wiring doctrine → Task 7; AC4 → Task 8.
- **Known unknowns flagged inline** (not placeholders — verify-then-implement
  steps): `Region.adjacent` field access (Task 4), `result.location`
  mutability + downstream consumption (Task 5), `LocationEntity.provenance`
  accepted values (Task 6). Each has the exact grep to resolve it.
- **Type consistency:** `SeamCrossingResult.to_region`, `SeamCrossingError.reason/.surface`,
  `seam_route_for(cartography, region_id)`, `get_seam_resolver(kind)` used
  identically across Tasks 1/2/3/5/7.
