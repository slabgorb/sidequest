---
parent: context-epic-71.md
workflow: tdd
---

# Story 71-25: perseus_cloud location grounding — declare world POIs (New Kowloon) as snapshot entities from content

## Business Context

In the 2026-05-27 `coyote_star` MP playtest line, the `perseus_cloud` world surfaced a
location-grounding gap: the world's points of interest (e.g. **New Kowloon**) are *named in
prose lore* but are not declared as typed location entities the narrator can anchor to.
With no entity manifest for these POIs, the narrator improvises geography — it invents
streets, layouts, and features that never persist, and the resolve-location-entity contract
(ADR-109) has nothing authoritative to check a mechanical claim against. That is the
"Diamonds and Coal" failure mode: a place that should be a durable diamond is treated as
disposable coal, re-improvised every turn.

This directly serves the "fool a career GM" bar. A good human DM has the world's key
locations grounded — New Kowloon's neon superblocks, the Santa Abraham scrapper ghetto,
the orbital city of Glitter — and references them consistently. Grounding declared POIs as
snapshot/manifest entities gives the narrator a fixed set to reference and makes
ADR-109's `narrator_proactive` no-commit / `player_initiated` Yes-And split actually
function for `perseus_cloud`. New Kowloon is the concrete acceptance target.

## Technical Guardrails

**Where POIs currently exist in content (and in what shape):**
- `sidequest-content/genre_packs/space_opera/worlds/perseus_cloud/cartography.yaml` — regions
  carry an untyped `landmarks:` list (e.g. Akkad's `Hallvei (moon)`, `Pollack 4
  (spaceStation)`). New Kowloon's churnworld region exists here (~`cartography.yaml:885`)
  with the summary text, but **no typed `entities:`** under any region.
- `.../worlds/perseus_cloud/history.yaml:29` declares `name: New Kowloon` / `slug:
  new_kowloon` as history flavor; `lore.yaml` mentions New Kowloon in prose (`:35`, `:100`,
  `:130`). None of these are a typed location-entity manifest.

**The typed manifest the engine actually consumes (ADR-109):**
- `sidequest-server/sidequest/genre/models/world.py:199` `Region` has a typed
  `entities: list[LocationEntity]` field (`:215`) that **coexists** with the legacy untyped
  `landmarks: list[Any]` (`:209`). The docstring is explicit: *"New code reads `entities`;
  `landmarks` is read-only legacy"* — content backfill (54-4/54-5) ports authored worlds to
  the typed shape. `perseus_cloud` has not been backfilled.
- `LocationEntity` (`sidequest/protocol/models.py:557`): `id`, `label`,
  `tier: Literal["real_object","yes_and","flavor_only"]`, optional `binding`
  (`LocationEntityBinding`, `:542`), `affordances: list[str]`, `provenance` (defaults
  `"authored"`). `model_config = {"extra": "forbid"}` — declarations must match the schema
  exactly or fail load.

**How declared entities reach the narrator/resolver (the consumption path):**
- `sidequest/agents/tools/resolve_location_entity.py` — `_authored_entities_for(ctx,
  region_id)` (`:78`) walks `ctx.genre_pack → worlds[world_id] → cartography → regions[region_id]
  → region.entities`. If any link is missing it returns `None`, surfaced as `NOT_FOUND` (no
  silent fallback). So today, with empty `region.entities`, the manifest is effectively
  empty and the narrator has nothing to anchor.
- `sidequest/game/location_resolver.py` `resolve(...)` (`:224`) takes `authored_entities`
  and builds the effective manifest (`_build_effective_manifest`, `:108`), merging authored
  YAML with runtime `location_promotions` (Postgres). Authored YAML is never mutated;
  declaring New Kowloon as `tier: real_object` (or `flavor_only`) gives the resolver a hit
  instead of a `narrator_proactive` contract miss / spurious mint.

**OTEL (the proof seam):**
- The resolver/tool emit `location_entity_resolve_span`, `location_entity_minted_span`,
  `location_entity_promoted_span` (imported in
  `agents/tools/resolve_location_entity.py`). A grounded New Kowloon must produce a
  *resolve hit* (not a mint) on `narrator_proactive` — the span attributes are the
  lie-detector for "the entity was found vs. improvised."

**Do NOT touch:** the `landmarks` legacy field semantics (leave it; just add typed
`entities`), the `location_promotions` runtime table / Yes-And mint path, other worlds'
cartography, or the resolver engine logic. This is primarily a **content declaration**
(typed `entities:` in `cartography.yaml`) plus verifying the existing consumption path picks
them up — "wire up what exists," not new engine code.

## Scope Boundaries

**In scope:**
- Declare `perseus_cloud` world POIs as typed `entities:` (`LocationEntity` shape) under the
  appropriate region(s) in
  `worlds/perseus_cloud/cartography.yaml`, with **New Kowloon specifically grounded** as a
  declared entity with a stable `id`, `label`, and `tier`.
- Verify (and fix wiring if broken) that `_authored_entities_for` →
  `location_resolver.resolve` surfaces the declared POIs so the narrator can anchor and a
  `narrator_proactive` reference to New Kowloon resolves as a HIT, not a NOT_FOUND/mint.
- OTEL/behavioral proof that a declared POI resolves through the production path.

**Out of scope:**
- Backfilling every `landmark` across all `perseus_cloud` regions into typed entities — the
  story grounds the world's named POIs (New Kowloon as the named acceptance target); an
  exhaustive landmark→entity migration of all 34 regions is not required.
- Per-POI landscape image/render assets (those are an asset-gate concern, separate).
- The `player_initiated` Yes-And mint path and `location_promotions` runtime behavior
  (already implemented; this story is about *authored* grounding).
- Other worlds (`coyote_star`, `aureate_span`) or other genre packs.

## AC Context

**AC1 — declared world POIs appear as snapshot entities the narrator can reference.**
- After loading the `space_opera` pack with `world=perseus_cloud`, the region containing the
  declared POIs must expose them via `Region.entities` (typed `LocationEntity`s), reachable
  through `_authored_entities_for(ctx, region_id)` returning a non-empty list (not `None`).
  Test: load the pack, navigate to the region, assert `region.entities` is non-empty and
  contains the expected POI `id`/`label`s.
- Edge: declarations must satisfy `LocationEntity`'s `extra="forbid"` schema and the
  `pf validate locations` invariant that a `real_object` entity SHOULD have a `binding` —
  malformed declarations must fail load loudly rather than silently dropping.

**AC2 — New Kowloon specifically is grounded.**
- A `narrator_proactive` resolve of "New Kowloon" (label normalization strips leading
  articles/case, `location_resolver.py:46`) against its region's manifest must return a HIT
  — `resolved=True`, `provenance="authored"` — NOT a `NOT_FOUND` and NOT a
  `yes_and_minted` entity. Test: call `location_resolver.resolve(label="New Kowloon",
  region_id=<region>, mode="narrator_proactive", authored_entities=<region.entities>)` and
  assert the resolution is an authored hit.
- OTEL proof (wiring test per project rule): drive the resolve through the real tool/path
  and assert a `location_entity_resolve` span fired indicating a manifest hit (no
  `location_entity_minted` span on the proactive path). This proves the entity is grounded
  end-to-end, surviving refactor, rather than asserting on YAML text.
- Edge: a `player_initiated` resolve of a POI that is NOT declared must still mint a
  `yes_and` entity (the Yes-And path is unbroken) — grounding New Kowloon must not regress
  the mint path for genuinely-new player-named places.

## Assumptions

- **The `entities` consumption path is fully wired and only the data is missing.**
  `_authored_entities_for` and `resolve` are live (ADR-109, story 54-6). This story is a
  content backfill verified by a wiring test; if the path is found broken (e.g. `ToolContext`
  doesn't carry `world_id`/`genre_pack` for `perseus_cloud`), that is a wiring fix in scope
  and must be logged as a Design Deviation noting the engine gap.
- **The region id for New Kowloon's churnworld region in `cartography.yaml` is the correct
  `region_id`** the narrator/resolver will pass. The exact region key must be read from the
  live `cartography.yaml` block (~`:885`) during implementation — do not assume the slug.
- **`tier` choice:** New Kowloon is a place the narrator references and the party can be in,
  so `real_object` (a grounded, bindable feature) or at minimum `flavor_only` is
  appropriate. `real_object` entities SHOULD carry a `binding`; if no subsystem object backs
  New Kowloon yet, `flavor_only` (which auto-promotes to `yes_and` on mechanical engagement)
  is the safe default. Confirm against the ADR-109 three-tier doctrine during design.
- **No new snapshot plumbing is required** — "snapshot entity" here means the typed
  location manifest the resolver reads, not a new `GameSnapshot` field. If grounding turns
  out to require a `GameSnapshot` change, that is a Design Deviation.

If any assumption proves wrong, log a Design Deviation and notify SM before widening scope.
