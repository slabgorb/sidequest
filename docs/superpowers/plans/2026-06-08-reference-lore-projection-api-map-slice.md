# Reference Lore Projection API — Map Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `GET /reference/api/lore/{pack}/{world}` returning a public-projected JSON document whose first section is the cartography **map** — graph *topology only* (regions, edges, npc pins, dangling refs), no coordinates — with the OTEL reference spans fired server-side at projection time.

**Architecture:** This is Phase 1, Slice A of the reference-pages → React migration (spec: `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`). The server keeps the *projection* job and emits JSON; React will render later. The map section emits **graph data, not positions** — layout moves client-side to d3-dag in a later slice, so the server no longer computes x/y. The existing HTML routes stay live (parallel surface); nothing is deleted in this slice. The pure graph helpers in `reference_map.py` (`_edges_and_dangling`, `_npc_pins`) are reused as data builders; only the SVG emission stays behind.

**Tech Stack:** Python 3 / FastAPI / pydantic v2, `uv run pytest` (xdist by default; use `-n0` for the OTEL span tests per the known span-count deadlock). OTEL spans via `sidequest.telemetry.spans.reference`.

---

## File Structure

- **Create** `sidequest/server/reference_projection.py` — the projection serializer. Pure functions: YAML/config → public-only JSON dicts. Owns the map-section builder and the top-level lore document builder. No HTTP, no HTML.
- **Modify** `sidequest/server/reference_routes.py` — add the `GET /reference/api/lore/{pack}/{world}` JSON route, reusing `_resolve_pack_dir` / `_resolve_world_dir` and the 404/500 semantics already there.
- **Create** `tests/server/test_reference_projection.py` — unit tests for the projection builders (map section shape, public-only assertion, span firing).
- **Create** `tests/server/test_reference_api_lore.py` — HTTP-level wiring tests (route mounted + reachable, 200/404/500).

The map *data* helpers (`_edges_and_dangling`, `_npc_pins`) are imported from `reference_map.py` — do **not** copy them. The SVG-emitting `present_lore_map` is untouched.

---

## Reference: existing shapes this slice reuses

- `load_cartography_config(world_dir: Path) -> CartographyConfig | None` (`reference_map.py`) — returns `None` if no `cartography.yaml`; raises `ValueError` on malformed.
- `CartographyConfig`: `.regions: dict[str, Region]`, `.starting_region: str`, `.navigation_mode`.
- `Region`: `.name: str`, `.adjacent: list[str]`, `.entities: list[LocationEntity]`.
- `_edges_and_dangling(cart) -> tuple[list[tuple[str,str]], list[tuple[str,str]]]` (`reference_map.py`) — de-duplicated sorted valid edges + dangling `(source, missing)` refs.
- `_npc_pins(region: Region) -> list[tuple[str, str]]` (`reference_map.py`) — `(slug, label)` for `binding.kind == "npc"` entities only (the public projection — no other entity field is exposed).
- `_gate_cast_slugs_on_manifest(slugs, *, manifest_path, ...) -> frozenset[str]` (`reference_renderer.py`) — gates portrait slugs on `r2_manifest.json` presence; the same gate the HTML map uses.
- `portrait_image_key(pack, world, slug) -> str` (`reference_presenters.py`) and `resolve_asset_url(key) -> str` (`asset_urls.py`) — R2 portrait key + asset URL.
- Spans (`sidequest.telemetry.spans.reference`): `reference_map_rendered_span(node_count, edge_count, npc_pin_count, resolved_pin_count)`, `reference_map_pin_resolved_span(slug, region)`, `reference_map_pin_not_found_span(slug, region)`, `reference_map_dangling_edge_span(source_region, dangling_region)`.

**Map section JSON shape (this slice defines it):**

```json
{
  "id": "map",
  "label": "Map",
  "starting_region": "harbor",
  "regions": [
    {"id": "harbor", "name": "The Harbor", "adjacent": ["market"],
     "pins": [{"slug": "old_sten", "label": "Old Sten", "portrait_url": "https://.../old_sten.png"}]},
    {"id": "market", "name": "Night Market", "adjacent": ["harbor"], "pins": []}
  ],
  "edges": [["harbor", "market"]],
  "dangling": [["harbor", "ghost-isle"]]
}
```

**Verified model shapes (Task 1 implementer, against the real code):**
- `Region` (`genre/models/world.py`) requires `name`, `summary`, `description` (no defaults); `adjacent`/`entities` default to `[]`; `extra: allow`.
- `LocationEntity` (`protocol/models.py`) requires `id`, `label`, `tier` ∈ `{real_object, yes_and, flavor_only}`; `binding` optional; `extra: forbid`.
- `LocationEntityBinding` requires `kind` ∈ `{location_feature, npc, item, clue, scenario_clue}` and `ref` (min_length 1); **`flavor_only` is NOT a binding kind** (it's a `tier` value); `extra: forbid`. Non-npc / no-binding entities never pin.
- Pin slug = `slugify_player_name(entity.label)` (spaces→underscores): `"Old Sten"` → `"old_sten"`. The entity `id` is NOT the slug.

`portrait_url` is `null` when the pin's portrait is not on R2. **No region/entity field other than `id`, `name`, `adjacent`, and the `{slug, label, portrait_url}` pin projection ever appears** — this is the public projection for the map.

Top-level lore document shape (this slice):

```json
{ "schema_version": 1, "pack": "pulp_noir", "world": "annees_folles", "sections": [ <map section, or omitted if no cartography> ] }
```

---

### Task 1: Map-section projection builder

**Files:**
- Create: `sidequest/server/reference_projection.py`
- Test: `tests/server/test_reference_projection.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/server/test_reference_projection.py
from __future__ import annotations

from sidequest.genre.models.world import CartographyConfig
from sidequest.server.reference_projection import build_lore_map_section


def _cart() -> CartographyConfig:
    return CartographyConfig.model_validate(
        {
            "starting_region": "harbor",
            "regions": {
                "harbor": {
                    "name": "The Harbor",
                    "adjacent": ["market", "ghost-isle"],  # ghost-isle is dangling
                    "entities": [
                        {"label": "Old Sten", "binding": {"kind": "npc"}},
                        {"label": "A Crate", "binding": {"kind": "flavor_only"}},
                    ],
                },
                "market": {"name": "Night Market", "adjacent": ["harbor"]},
            },
        }
    )


def test_map_section_emits_topology_not_coordinates():
    section = build_lore_map_section(
        _cart(), pack="p", world="w", portrait_on_r2_slugs=frozenset({"old-sten"})
    )
    assert section["id"] == "map"
    assert section["label"] == "Map"
    assert section["starting_region"] == "harbor"
    # Edges de-duplicate reciprocal adjacency, sorted endpoints; dangling dropped.
    assert section["edges"] == [["harbor", "market"]]
    assert section["dangling"] == [["harbor", "ghost-isle"]]
    # No coordinates anywhere — layout is a client (d3-dag) concern now.
    blob = repr(section)
    assert '"x"' not in blob and "'x'" not in blob
    regions = {r["id"]: r for r in section["regions"]}
    assert set(regions["harbor"].keys()) == {"id", "name", "adjacent", "pins"}
    # Only npc-binding entities pin; flavor_only never does (public projection).
    pins = regions["harbor"]["pins"]
    assert len(pins) == 1
    assert pins[0]["slug"] == "old-sten"
    assert pins[0]["label"] == "Old Sten"
    assert pins[0]["portrait_url"] is not None  # on R2
    assert regions["market"]["pins"] == []


def test_map_pin_portrait_url_null_when_not_on_r2():
    section = build_lore_map_section(
        _cart(), pack="p", world="w", portrait_on_r2_slugs=frozenset()
    )
    harbor = next(r for r in section["regions"] if r["id"] == "harbor")
    assert harbor["pins"][0]["portrait_url"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_reference_projection.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sidequest.server.reference_projection'`.

- [ ] **Step 3: Write minimal implementation**

```python
# sidequest/server/reference_projection.py
"""Public-projected JSON for the reference lore page (React-rendered surface).

The server keeps the *projection* job — deciding what public data exists — and
emits JSON. React renders it. This module is the serializer; it holds no HTTP and
no HTML. The map section emits graph *topology only* (regions, edges, npc pins,
dangling refs); node positions are a client concern (d3-dag), so nothing here
computes coordinates. The pure graph helpers in ``reference_map.py``
(``_edges_and_dangling``, ``_npc_pins``) are reused as data builders; only the
SVG emission stays behind in that module.
"""

from __future__ import annotations

from sidequest.genre.models.world import CartographyConfig
from sidequest.server.asset_urls import resolve_asset_url
from sidequest.server.reference_map import _edges_and_dangling, _npc_pins
from sidequest.server.reference_presenters import portrait_image_key
from sidequest.telemetry.spans.reference import (
    reference_map_dangling_edge_span,
    reference_map_pin_not_found_span,
    reference_map_pin_resolved_span,
    reference_map_rendered_span,
)


def build_lore_map_section(
    cart: CartographyConfig,
    *,
    pack: str,
    world: str,
    portrait_on_r2_slugs: frozenset[str],
) -> dict:
    """Project ``cartography`` into the public ``map`` section dict.

    Fires the reference map spans at projection time (the decision point): one
    ``map_rendered`` census, a per-pin ``pin_resolved`` / ``pin_not_found``, and a
    ``dangling_edge`` WARN per dropped adjacency.
    """
    edges, dangling = _edges_and_dangling(cart)
    for source, missing in dangling:
        with reference_map_dangling_edge_span(source_region=source, dangling_region=missing):
            pass

    npc_pin_count = 0
    resolved_pin_count = 0
    regions: list[dict] = []
    for rid in sorted(cart.regions):
        region = cart.regions[rid]
        pins: list[dict] = []
        for slug, label in _npc_pins(region):
            npc_pin_count += 1
            if slug in portrait_on_r2_slugs:
                resolved_pin_count += 1
                with reference_map_pin_resolved_span(slug=slug, region=rid):
                    pass
                portrait_url: str | None = resolve_asset_url(portrait_image_key(pack, world, slug))
            else:
                with reference_map_pin_not_found_span(slug=slug, region=rid):
                    pass
                portrait_url = None
            pins.append({"slug": slug, "label": label, "portrait_url": portrait_url})
        regions.append(
            {"id": rid, "name": region.name, "adjacent": list(region.adjacent), "pins": pins}
        )

    with reference_map_rendered_span(
        node_count=len(regions),
        edge_count=len(edges),
        npc_pin_count=npc_pin_count,
        resolved_pin_count=resolved_pin_count,
    ):
        pass

    return {
        "id": "map",
        "label": "Map",
        "starting_region": cart.starting_region,
        "regions": regions,
        "edges": [list(e) for e in edges],
        "dangling": [list(d) for d in dangling],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_reference_projection.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/reference_projection.py tests/server/test_reference_projection.py
git commit -m "feat(reference): public map-section JSON projection (topology only)"
```

---

### Task 2: Top-level lore document builder

**Files:**
- Modify: `sidequest/server/reference_projection.py`
- Test: `tests/server/test_reference_projection.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/server/test_reference_projection.py
from pathlib import Path

import pytest

from sidequest.server.reference_projection import build_lore_projection


def test_lore_projection_includes_map_when_cartography_present(tmp_path: Path):
    world_dir = tmp_path / "worlds" / "w"
    world_dir.mkdir(parents=True)
    (world_dir / "cartography.yaml").write_text(
        "starting_region: harbor\n"
        "regions:\n"
        "  harbor: {name: The Harbor, summary: Salt docks., description: Fog and hulls., adjacent: [market]}\n"
        "  market: {name: Night Market, summary: Lit stalls., description: Spice and smoke., adjacent: [harbor]}\n",
        encoding="utf-8",
    )
    doc = build_lore_projection("p", "w", pack_dir=tmp_path, world_dir=world_dir)
    assert doc["schema_version"] == 1
    assert doc["pack"] == "p"
    assert doc["world"] == "w"
    assert [s["id"] for s in doc["sections"]] == ["map"]


def test_lore_projection_omits_map_when_no_cartography(tmp_path: Path):
    world_dir = tmp_path / "worlds" / "w"
    world_dir.mkdir(parents=True)
    doc = build_lore_projection("p", "w", pack_dir=tmp_path, world_dir=world_dir)
    assert doc["sections"] == []


def test_lore_projection_raises_on_malformed_cartography(tmp_path: Path):
    world_dir = tmp_path / "worlds" / "w"
    world_dir.mkdir(parents=True)
    (world_dir / "cartography.yaml").write_text("regions: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError):
        build_lore_projection("p", "w", pack_dir=tmp_path, world_dir=world_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_reference_projection.py -k lore_projection -v`
Expected: FAIL — `ImportError: cannot import name 'build_lore_projection'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to sidequest/server/reference_projection.py
from pathlib import Path

from sidequest.server.reference_map import load_cartography_config
from sidequest.server.reference_renderer import _gate_cast_slugs_on_manifest


def build_lore_projection(pack: str, world: str, *, pack_dir: Path, world_dir: Path) -> dict:
    """Assemble the public-projected lore document. This slice emits the map
    section only; Cast/POI/Timeline/generic-YAML sections land in later slices.
    """
    sections: list[dict] = []

    cartography = load_cartography_config(world_dir)
    if cartography is not None and cartography.regions:
        map_npc_slugs = frozenset(
            slug
            for region in cartography.regions.values()
            for slug, _label in _npc_pins(region)
        )
        gated_map_slugs = _gate_cast_slugs_on_manifest(
            map_npc_slugs,
            pack=pack,
            world=world,
            pack_dir=pack_dir,
        )
        sections.append(
            build_lore_map_section(
                cartography, pack=pack, world=world, portrait_on_r2_slugs=gated_map_slugs
            )
        )

    return {"schema_version": 1, "pack": pack, "world": world, "sections": sections}
```

> **Verified signature:** `_gate_cast_slugs_on_manifest(authored_slugs, *, pack, world, pack_dir)` — it computes the manifest path internally as `pack_dir.parent.parent / "r2_manifest.json"`; there is NO `manifest_path` kwarg. The gate short-circuits on an empty slug set before touching the manifest (so a cartography fixture with no npc entities never raises `FileNotFoundError`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_reference_projection.py -k lore_projection -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/reference_projection.py tests/server/test_reference_projection.py
git commit -m "feat(reference): top-level lore JSON document builder (map slice)"
```

---

### Task 3: JSON API route

**Files:**
- Modify: `sidequest/server/reference_routes.py`
- Test: `tests/server/test_reference_api_lore.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/server/test_reference_api_lore.py
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sidequest.server.reference_routes import create_reference_router


def _client(tmp_path: Path) -> TestClient:
    pack_dir = tmp_path / "pulp_noir"
    world_dir = pack_dir / "worlds" / "annees_folles"
    world_dir.mkdir(parents=True)
    (world_dir / "cartography.yaml").write_text(
        "starting_region: harbor\n"
        "regions:\n"
        "  harbor: {name: The Harbor, summary: Salt docks., description: Fog and hulls., adjacent: [market]}\n"
        "  market: {name: Night Market, summary: Lit stalls., description: Spice and smoke., adjacent: [harbor]}\n",
        encoding="utf-8",
    )
    app = FastAPI()
    app.state.genre_pack_search_paths = [str(tmp_path)]
    app.include_router(create_reference_router())
    return TestClient(app)


def test_lore_api_returns_map_section(tmp_path: Path):
    resp = _client(tmp_path).get("/reference/api/lore/pulp_noir/annees_folles")
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["schema_version"] == 1
    assert [s["id"] for s in doc["sections"]] == ["map"]


def test_lore_api_404_unknown_world(tmp_path: Path):
    resp = _client(tmp_path).get("/reference/api/lore/pulp_noir/no_such_world")
    assert resp.status_code == 404


def test_lore_api_500_on_malformed_cartography(tmp_path: Path):
    c = _client(tmp_path)
    bad = tmp_path / "pulp_noir" / "worlds" / "annees_folles" / "cartography.yaml"
    bad.write_text("regions: [unclosed\n", encoding="utf-8")
    resp = c.get("/reference/api/lore/pulp_noir/annees_folles")
    assert resp.status_code == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_reference_api_lore.py -v`
Expected: FAIL — 404 for the success case (route not registered yet).

- [ ] **Step 3: Write minimal implementation**

Add the import near the other reference imports in `reference_routes.py`:

```python
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from sidequest.server.reference_projection import build_lore_projection
```

Add this route inside `create_reference_router()`, after the `lore_page` HTML route:

```python
    @router.get("/api/lore/{pack}/{world}")
    async def lore_api(request: Request, pack: str, world: str) -> JSONResponse:
        pack_dir = _resolve_pack_dir(request, pack)
        world_dir = _resolve_world_dir(pack_dir, world)
        try:
            doc = build_lore_projection(pack, world, pack_dir=pack_dir, world_dir=world_dir)
        except (ValueError, FileNotFoundError, MissingThemeFieldError) as exc:
            _LOG.exception("reference lore api: projection failed for %s/%s", pack, world)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=doc)
```

> **Route ordering note:** FastAPI matches in declaration order. `/api/lore/{pack}/{world}` and `/lore/{pack}/{world}` do not collide (distinct first segment `api` vs the pack slug — but `api` is itself a valid-looking pack to `/rules/{pack}`-style matches elsewhere). Declaring the `/api/...` route is unambiguous here because its path has four segments under the prefix. No reordering needed; the test confirms.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/server/test_reference_api_lore.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add sidequest/server/reference_routes.py tests/server/test_reference_api_lore.py
git commit -m "feat(reference): GET /reference/api/lore/{pack}/{world} JSON route"
```

---

### Task 4: Public-projection guard test (no keeper/entity internals leak)

**Files:**
- Test: `tests/server/test_reference_projection.py`

This is the security assertion for the map slice (spec constraint C1): the map JSON must expose only the public projection — region `id`/`name`/`adjacent` and `{slug, label, portrait_url}` pins. It must never carry entity internals (binding kind/target, descriptions, coordinates) even when the source YAML has them.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/server/test_reference_projection.py
import json as _json


def test_map_projection_leaks_no_entity_internals():
    cart = CartographyConfig.model_validate(
        {
            "starting_region": "harbor",
            "regions": {
                "harbor": {
                    "name": "The Harbor",
                    "summary": "Salt docks.",
                    "description": "Fog and hulls.",
                    "adjacent": ["market"],
                    "entities": [
                        {
                            "id": "sten",
                            "label": "Old Sten",
                            "tier": "real_object",
                            # `ref` is the keeper-side link target; it must NOT leak.
                            "binding": {"kind": "npc", "ref": "npc_sten_secret_id"},
                        }
                    ],
                },
                "market": {
                    "name": "Night Market",
                    "summary": "Lit stalls.",
                    "description": "Spice and smoke.",
                    "adjacent": ["harbor"],
                },
            },
        }
    )
    section = build_lore_map_section(
        cart, pack="p", world="w", portrait_on_r2_slugs=frozenset({"old_sten"})
    )
    blob = _json.dumps(section)
    # The secret binding ref value must not cross the JSON boundary.
    assert "npc_sten_secret_id" not in blob
    # Binding keys must not appear (quoted-key form — robust vs. substrings that
    # could legitimately occur inside a portrait URL/domain).
    assert '"ref"' not in blob
    assert '"kind"' not in blob
    # Pin carries exactly the public projection keys.
    pin = section["regions"][0]["pins"][0]
    assert set(pin.keys()) == {"slug", "label", "portrait_url"}
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/server/test_reference_projection.py -k leaks_no_entity -v`
Expected: PASS if Task 1's builder is correct (it only emits the public keys). If it FAILS, the builder is over-exposing — fix `build_lore_map_section` to project only `{slug, label, portrait_url}` and the region `{id, name, adjacent, pins}`, then re-run. **Do not weaken the test.**

- [ ] **Step 3: Commit**

```bash
git add tests/server/test_reference_projection.py
git commit -m "test(reference): map projection leaks no entity internals (C1)"
```

---

### Task 5: OTEL wiring test (spans fire at projection time)

**Files:**
- Test: `tests/server/test_reference_projection.py`

Per the repo OTEL principle and "Every Test Suite Needs a Wiring Test": drive the projection and assert the reference span fired. This is a behavior/span assertion, not a source-text grep.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/server/test_reference_projection.py
from tests.server.conftest import span_attrs_by_name
from sidequest.telemetry.spans.reference import SPAN_REFERENCE_MAP_RENDERED


def test_projection_fires_map_rendered_span(otel_capture):  # noqa: ARG001
    # otel_capture: the span-capturing fixture used by test_reference_map.py.
    build_lore_map_section(
        _cart(), pack="p", world="w", portrait_on_r2_slugs=frozenset({"old-sten"})
    )
    attrs = span_attrs_by_name(SPAN_REFERENCE_MAP_RENDERED)
    assert attrs["reference.map_node_count"] == 2
    assert attrs["reference.map_npc_pin_count"] == 1
    assert attrs["reference.map_resolved_pin_count"] == 1
```

> **Verify before running:** open `tests/server/test_reference_map.py` and `tests/server/conftest.py` to confirm (a) the exact name of the span-capture fixture (it may not be `otel_capture`) and (b) the `span_attrs_by_name` signature. Mirror that test's setup verbatim — it already exercises this span family, so copy its fixture wiring rather than guessing.

- [ ] **Step 2: Run test to verify it passes (serial — span tests deadlock under xdist)**

Run: `uv run pytest tests/server/test_reference_projection.py -k map_rendered_span -n0 -v`
Expected: PASS.

- [ ] **Step 3: Run the whole new suite serially to confirm no span-count interaction**

Run: `uv run pytest tests/server/test_reference_projection.py tests/server/test_reference_api_lore.py -n0 -v`
Expected: PASS (all).

- [ ] **Step 4: Commit**

```bash
git add tests/server/test_reference_projection.py
git commit -m "test(reference): projection fires map_rendered span (OTEL wiring)"
```

---

### Task 6: Lint, format, full-gate, final commit

- [ ] **Step 1: Lint + format**

Run: `uv run ruff check sidequest/server/reference_projection.py sidequest/server/reference_routes.py tests/server/test_reference_projection.py tests/server/test_reference_api_lore.py`
Then: `uv run ruff format sidequest/server/reference_projection.py sidequest/server/reference_routes.py tests/server/test_reference_projection.py tests/server/test_reference_api_lore.py`
Expected: clean.

- [ ] **Step 2: Type check**

Run: `uv run pyright sidequest/server/reference_projection.py sidequest/server/reference_routes.py`
Expected: no new errors. (If `_gate_cast_slugs_on_manifest` / `_edges_and_dangling` are flagged as private imports, that is acceptable for this slice — they are deleted alongside `reference_map.py`'s SVG path at Phase 4 cutover; note it in the commit body.)

- [ ] **Step 3: Run the new tests once more, serial**

Run: `uv run pytest tests/server/test_reference_projection.py tests/server/test_reference_api_lore.py -n0 -v`
Expected: PASS.

- [ ] **Step 4: Commit any lint/format fixups**

```bash
git add -A
git commit -m "chore(reference): lint/format projection map slice" || echo "nothing to commit"
```

---

## What this slice deliberately defers (next plans, same shape)

- **Generic-YAML sections + the `classify()` firewall reuse** — the node-tree projection of `world`/`history`/`cultures`/`legends`/etc., where `reference_visibility.py` actually runs. The broad keeper-field security test set lands there.
- **Cast, POI, Timeline** sections of the lore document.
- **Theme tokens** (`theme.yaml` → JSON) for the session-free client injector (spec C3).
- **Rules page** projection (`/reference/api/rules/{pack}`).
- **React shell + d3-dag map render + `cartographyLayout.ts` deletion** (Phase 2–3).
- **Cutover/retire** of the HTML routes + `islands.js` (Phase 4).

---

## Self-Review

- **Spec coverage (Phase 1, map slice):** projection-not-render seam ✓ (Task 1–3); firewall-as-data-projection for the map's public pin projection ✓ (Task 4, C1) — the broad `classify()` reuse is explicitly deferred to the generic-YAML slice and named above; spans moved to projection time ✓ (Task 5); fail-loud 404/500 ✓ (Task 3); no coordinates server-side / layout is client d3-dag ✓ (Task 1). No-session invariant (C2), theme (C3), determinism (C4), URL home (C5) belong to later React/cutover slices and are listed as deferred.
- **Placeholder scan:** no TBD/TODO; every code step carries complete code. Two "verify before running" notes point at real existing call sites to copy verbatim (the `_gate_cast_slugs_on_manifest` signature and the span-capture fixture) rather than inventing them — these are guardrails, not placeholders.
- **Type consistency:** `build_lore_map_section(cart, *, pack, world, portrait_on_r2_slugs)` and `build_lore_projection(pack, world, *, pack_dir, world_dir)` signatures match across Tasks 1–3 and the route call. Section dict keys (`id`/`label`/`starting_region`/`regions`/`edges`/`dangling`; pin `slug`/`label`/`portrait_url`) are identical in builder, tests, and the documented shape.
