---
parent: context-epic-65.md
workflow: tdd
---

# Story 65-11: Lore POI map view — server-rendered SVG node-link graph with portrait pins

## Business Context

Epic 65 spent a checked-in R2 manifest (`sidequest-content/r2_manifest.json`,
committed by 65-7) on a run of player-facing payoffs on the lore reference page
(`GET /reference/lore/{pack}/{world}`, the ADR-135 public table tool): 65-8 lit
up **Points of Interest** images, 65-9 added the manifest-gated **Cast** section.
65-8's own Design Notes name this story as the next slice: *"Map view or timeline
(stories 65-11, 65-12 — follow-on slices)."* This is the **map** slice.

The map gives the table a spatial mental model of the world before and during
play — a who-is-where and what-connects-to-what the players can open in a second
tab. It serves both readers exactly as the rest of the lore page does. The
narrative reader (James/Keith) gets an illustrated map of the world's regions
with the dramatis personae pinned where they live — Diamonds-and-Coal made
visible. The mechanical/legibility reader (Sebastien/Jade) gets the **adjacency
graph** rendered explicitly: which regions border which, the shape of the travel
network, surfaced as structure instead of inferred from prose. For a
mechanics-first author like Jade extending `perseus_cloud`, seeing her authored
`adjacent:` lists drawn as a graph is direct feedback that the cartography she
wrote loads and connects the way she intended.

The hard fact that shapes the whole story: **cartography has no coordinates.**
Every world is `navigation_mode: region` with regions carrying only an
`adjacent:` adjacency list (verified across all live worlds — no `x`/`y`/`coord`
key exists anywhere). So this is not a geographic map; it is a **node-link
graph** — regions as nodes, adjacency as edges — and the only genuinely new code
in the story is a *deterministic* layout that turns that graph into placed nodes.
Everything else is wiring proven seams that 65-8/65-9 already shipped.

## Technical Guardrails

**This REUSES the 65-8/65-9 reference-page machinery — it is mostly a wire-up,
not a new build** (CLAUDE.md: "Don't Reinvent — Wire Up What Exists"). The route,
the section/TOC registration, the cartography model, the R2 portrait gate, the
SVG library, the OTEL span family, and the test fixtures all exist. Author a
divergent manifest parser, a second cartography loader, or a parallel span
vocabulary and you have failed the story.

**Repo / branch:** `sidequest-server` only, on a `feat/65-11-*` branch off
`develop` (per repos.yaml — NOT main). Server is Python/FastAPI, uv-managed. Run
tests via the `testing-runner` subagent, never directly.

**As-built seams to reuse (verified by Architect scan, cite `develop`):**
- **Route + assembler:** `server/reference_routes.py:lore_page()` (line ~119) →
  `server/reference_renderer.py:assemble_lore_page()`. The map section is
  produced inside the lore assembler and concatenated into the page body — it is
  NOT a new route.
- **Section + TOC registration:** `PACK_TOC` + `TOC_TO_FILES` in
  `server/reference_theme.py`; `_wrap_sections_by_toc()` (reference_renderer.py
  ~954). Follow the **65-9 Cast append pattern** (reference_renderer.py
  ~1348-1360): render the section HTML, append to `body`, add a `{id,label,num}`
  TOC entry. Map is a synthesized section (not a YAML file), so it registers a
  TOC entry directly rather than through a `*_FILES` stem list.
- **Cartography model (already loaded):** `genre/models/world.py:CartographyConfig`
  (~240) with `regions: dict[str, Region]`; `Region.adjacent: list[str]` (~208);
  `Region.entities: list[LocationEntity]` (ADR-109 typed manifest).
  `LocationEntity.binding` is a `LocationEntityBinding` with
  `kind: Literal["location_feature","npc","item","clue","scenario_clue"]` and
  `ref: str` (`protocol/models.py:545,560`). Loaded by
  `genre/loader.py:_load_cartography` / `_load_world` — the lore route already has
  the parsed `WorldConfig.cartography` in scope. Do NOT re-parse the YAML.
- **Portrait gate (reuse exactly):** `reference_renderer.py:load_r2_manifest_keys`
  (~1134, `lru_cache`d, no TTL — discovery rule `pack_dir.parent.parent /
  "r2_manifest.json"`); `reference_presenters.py:portrait_image_key(pack, world,
  slug)` (~214) returns the **raw R2 key** compared directly to the manifest
  frozenset; the Cast slugify path (`slugify_player_name`, `server/utils.py`).
  Pins gate on `portrait_image_key(...) in manifest_keys` — the *presenter* wraps
  the key in `resolve_asset_url()` for the `<img src>`, the *gate* compares raw.
  This is the identical presenter-vs-gate boundary 65-9 documented.
- **SVG:** `svgwrite` is already a dependency, used by `orbital/render.py`
  (Orrery) and `interior/render.py` (room grid). Neither has a node-link/graph
  layout — those are Kepler-orbit and fixed-grid respectively — so the **layout
  is new**, but the SVG *emission* library is established. Prefer `svgwrite` over
  hand-built string SVG for consistency.
- **OTEL spans:** `telemetry/spans/reference.py` holds the reference span family
  and the `FLAT_ONLY_SPANS` registry; `reference_manifest_loaded_span`
  (`sidequest.reference.manifest_loaded`) is the load span; the portrait
  resolved/not-found pair lives in `telemetry/spans/scrapbook.py`
  (`scrapbook.npc_portrait_{resolved,not_found}`). Add a `reference`-namespaced
  `reference_map_rendered` span and a map-pin resolved/not-found pair (register in
  `FLAT_ONLY_SPANS`). Do NOT invent a parallel vocabulary; mirror the existing
  shape.

**Test seams to reuse:** `tests/server/test_reference_*` modules; `gated_client`
fixture (`create_app(genre_pack_search_paths=[FIXTURE_ROOT])` → `TestClient`);
`otel_capture` / `otel_exporter` (conftest, in-memory span exporter);
`span_attrs_by_name(exporter, name)` helper. **No source-text wiring tests**
(server CLAUDE.md): assert on rendered HTML, emitted spans, or fixture-driven
behavior — never `read_text()` of production source. The wiring proof is an
integration test through the real `/reference/lore/` route.

**Determinism is a correctness requirement, not a nicety.** The SVG must be
byte-identical across renders of the same cartography. That rules out: wall-clock
in element ids, `set`/`dict` iteration order leaking into output, and any
unseeded layout. svgwrite can emit stable ids — pin them deterministically.
Layout seeds at `starting_region`, orders ties by sorted region id.

## Scope Boundaries

**In scope:**
- A public **Map** section on the lore reference page: an inline server-rendered
  `<svg>` node-link graph built from `cartography.regions` (nodes) + `adjacent`
  (edges), with a TOC entry registered when the world has a cartography.yaml.
- A deterministic graph layout (the one genuinely new component) seeded at
  `starting_region`, ties broken by sorted region id.
- NPC portrait pins for `entities[].binding.kind == "npc"`, gated through the
  reused `load_r2_manifest_keys` + `portrait_image_key` + slugify path; text/dot
  fallback (zero broken `<img>`) when the portrait is absent from R2.
- Edge de-duplication for reciprocal adjacency; skip + WARN span for adjacency to
  an unknown region id.
- OTEL: a `reference_map_rendered` span (node/edge/pin/resolved counts) + per-pin
  resolved/not-found spans + the dangling-adjacency WARN span.
- An integration test through the real route, a regression check that existing
  sections render unchanged, and a chrome-wiring fixture extension covering the
  new map CSS classes.

**Out of scope:**
- The in-game live `MAP_UPDATE` / room-graph navigation surface (ADR-055). This
  is the **static lore-page projection**, not the runtime map.
- Coordinates / geographic placement / the `map_style` prose-to-image render —
  `map_style` is an image-gen prompt, not geometry; this story does not call the
  daemon or render a pictorial map.
- The world **timeline** (65-12) and the 65-13 Cast review follow-ups.
- A client-side React map; any pan/zoom/interactivity — this is server-rendered
  static SVG embedded in the HTML page.
- Any write to R2 or the asset ledger; portrait or map *generation*.
- The public/secret projection decision — ADR-135/-136 already govern what is
  public. This story consumes the public projection; it does not create the
  public/secret split. It simply does not pin non-npc or flavor_only entities.

## AC Context

**AC1 — Map section registered + rendered.** The lore page gains a "Map" section
with a TOC entry via the existing `PACK_TOC`/`TOC_TO_FILES` mechanism (65-9 Cast
pattern). *Pass:* a world WITH cartography.yaml → response contains the section
with exactly one inline `<svg>`. *Edge (graceful):* a world WITHOUT cartography
→ HTTP 200, page unchanged, no Map section, no error. *Loud:* malformed
cartography.yaml → HTTP 500 (No Silent Fallbacks). Assert on the rendered HTML.

**AC2 — Nodes from regions.** Every entry in `cartography.regions` renders as
exactly one node labeled with the region `name`; node count == region count.
*Test:* fixture world with N regions → assert N node/label elements. Pins the
"dropped a region" bug.

**AC3 — Edges from adjacency, de-duplicated, dangling-safe.** Each adjacency
renders one edge; reciprocal adjacency (A↔B) renders a **single** edge, not two;
adjacency naming a region id absent from `regions` is **skipped** (no dangling
edge) and emits a **WARN span**. *Test:* fixture with one reciprocal pair and one
dangling ref → assert edge count (dedup proven) + the WARN span fired (not
silent). This is the structural integrity AC.

**AC4 — Deterministic layout.** Rendering the same cartography twice yields
**byte-identical** SVG — no time, no randomness, no dict-order dependence.
*Test:* render twice, assert equal strings; permute the fixture's region-dict
insertion order, assert node ordering unchanged. Pins the nondeterminism class of
bug before it reaches a flaky snapshot test.

**AC5 — NPC portrait pins, gated through the existing R2 gate.** Entities with
`binding.kind == "npc"` render as pins on their region node; a pin emits a
portrait `<img>` **iff** `portrait_image_key(pack, world, slug)` is in
`r2_manifest.json` (reuse `load_r2_manifest_keys` + the Cast slugify path — NOT a
reimplemented path rule). Portrait absent from R2 → non-image fallback marker,
**zero** broken `<img>`. *Tests mirror 65-8/65-9's split:* a positive fixture
world (pins WITH images → `<img>` present with resolved URL) and a negative
fixture world (npc entities but NO R2 portraits → zero `<img` substrings in the
map section, section still renders). **Resolution-chain risk to confirm in RED:**
`entity.binding.ref` is an NPC **id**; the portrait slug comes from
`slugify(npc display name)`. The pin must resolve `ref → display name → slug`
through the same path the Cast section uses, or pins silently won't gate. Confirm
the ref→slug mapping against a fixture before pinning the test; if `ref` is
already the slug, assert that; if not, route through the npc lookup. Log a Design
Deviation if the mapping needs a new helper.

**AC6 — OTEL on every decision (mandatory per CLAUDE.md).** The renderer emits
`reference_map_rendered` once per render carrying `node_count`, `edge_count`,
`npc_pin_count`, `resolved_pin_count`; plus a per-pin resolved/not-found span pair
(reuse the reference-portrait family or add a `reference_map_pin_{resolved,
not_found}` pair in `FLAT_ONLY_SPANS`); plus the AC3 dangling WARN span. *Test:*
`span_attrs_by_name`/`otel_capture` with **complement assertions** — an
absent-portrait slug is NOT in resolved AND a present one is NOT in not_found, so
the span test alone distinguishes a correct gate from an always-resolve gate
(the rigor 65-13 asked for on the Cast spans). The GM panel is the lie detector:
these spans are how we confirm the gate engaged rather than Claude improvising a
text-only render.

**AC7 — Public projection only (ADR-135).** No `?audience` param, no GM mode.
Only public region facts (name, adjacency) and gated public portraits render;
`flavor_only` and non-npc entities (and any non-public binding) do **not** appear
as pins. *Test:* fixture with a `flavor_only` / non-npc entity → assert it is
absent from the map SVG.

**AC8 — Wiring + regression (no source-text wiring tests).** At least one
integration test hits the **real** `/reference/lore/{pack}/{world}` route via
`gated_client` and asserts the Map section + `<svg>` + a resolved pin end-to-end
(behavior/OTEL/fixture-driven, never a grep of source). Existing lore sections
(geography, cast, history, factions) render **unchanged** (regression). The
chrome-wiring fixture (`test_reference_chrome_wiring.py` seed world) is extended
so the new map CSS classes are actually rendered and validated — closes the
65-13-style chrome blind spot rather than reopening it.

## Assumptions

- **`WorldConfig.cartography` is reachable from the lore route** as a parsed
  `CartographyConfig` (the loader already builds it). If the lore assembler does
  not have the world's cartography in scope, that is a Gap to log (blocking) —
  flag it; do not re-parse cartography.yaml in the renderer.
- **The R2 portrait key convention is stable and discoverable** from the
  committed manifest, identical to the 65-9 Cast gate. Tests inject a **fake**
  manifest map and must never hit live R2. Confirm `portrait_image_key`'s exact
  string against `r2_manifest.json` before pinning the expected key.
- **Determinism is achievable with `svgwrite`** (stable ids, no auto-incrementing
  global counter leaking across renders). If svgwrite forces nondeterministic
  output, hand-emit the SVG string deterministically and log a Design Deviation.
- **Fixture worlds, not live content, anchor the tests.** Build frozen fixture
  packs (the `reference_v2_fixture` pattern): a positive world with regions +
  adjacency + npc pins with R2 portraits, and a negative world with npc entities
  but no R2 portraits. Live candidates for **manual** verification only: `oz`
  (wry_whimsy — regions, adjacency, npc entities) as positive; `glenross`
  (tea_and_murder — the 65-9 negative world) as portraits-absent. `perseus_cloud`
  has regions/adjacency but **no** npc-binding entities — good for a
  pins-empty/graph-only case.
- **The layout algorithm stays simple and deterministic** — a layered/radial BFS
  from `starting_region` is sufficient; this is not a physics simulation. If the
  graph is disconnected, lay out each component deterministically (ordered by the
  sorted region id of its lowest member). Log a Design Deviation if a more complex
  layout is pursued — that would push the story past 5 points.

If any assumption proves wrong during implementation, log a Design Deviation and
notify SM — wrong assumptions are the top source of scope creep.

---
_Authored 2026-06-03 by Architect (Neo) as the AC-authoring + context step the
Operator requested before TDD setup (65-11 entered the sprint as a title-only
story). ACs written into epic-65.yaml via `pf sprint story update`. Composed from
the epic-65 context, the 65-8 archive's follow-on Design Notes, and an **as-built**
reuse-surface scan of `develop` (`reference_routes.lore_page`,
`reference_renderer.assemble_lore_page` / `load_r2_manifest_keys` / TOC
registration, `reference_presenters.portrait_image_key`,
`genre/models/world.CartographyConfig` / `Region.adjacent` / `Region.entities`,
`protocol/models.LocationEntityBinding`, `orbital/render` svgwrite usage,
`telemetry/spans/reference`, and the `gated_client`/`otel_capture`/
`span_attrs_by_name` fixtures). Schema-compliant per context-schema.yaml v1.0.0._
