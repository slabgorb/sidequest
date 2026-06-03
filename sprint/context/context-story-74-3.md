---
parent: context-epic-74.md
workflow: tdd
---

# Story 74-3: Author world-tier lore for every live world; unblock genre-lore deletion and avoid empty LoreStore on un-migrated worlds

## Business Context

Story 74-1 made genre-tier flavor **optional** in the loader — genre lore is no longer seeded into the narrator's LoreStore. However, 74-1 did not author world-tier lore for every live world. As a result, any world that relies on the genre lore fallback (inherited shared lore) now gets an **empty LoreStore** once genre lore is deleted. This story closes that gap: it authors `worlds/<world>/lore.yaml` for every live world that currently has sparse or no world-tier lore, ensuring every world has a self-contained, non-empty lore story to serve the narrator. This unblocks the genre lore deletion step and prevents the "query_lore returns nothing" regression that plagued the April 2026 RAG port.

**Prerequisite:** Story 74-1 is done (loader is genre-lore-optional, world-tier authoritative). This story is the content follow-up.

**Scope:** World-tier lore **authoring and testing**, not deletion of genre lore files (deletion is gated on ALL live worlds being migrated; may be a separate cleanup step).

## Technical Approach

**Live-world enumeration:** The 10 wired genre packs + the 1 aspirational pack (wry_whimsy) span 20 live worlds:
- **caverns_and_claudes:** beneath_sunden
- **elemental_harmony:** burning_peace, shattered_accord
- **heavy_metal:** evropi, long_foundry
- **mutant_wasteland:** flickering_reach
- **neon_dystopia:** franchise_nations
- **pulp_noir:** annees_folles
- **road_warrior:** the_circuit
- **space_opera:** aureate_span, coyote_star, perseus_cloud
- **spaghetti_western:** dust_and_lead, five_points, the_real_mccoy
- **tea_and_murder:** glenross, blackthorn_moor
- **wry_whimsy:** gulliver, oz, wonderland

**Implementation approach:**
1. **Audit existing world-tier lore.** Check which worlds already author world-tier `lore.yaml` (non-sparse). These are done; no work needed.
2. **For sparse/missing worlds:** extract the core, essential narrative context from the genre `lore.yaml` and adapt it into a **world-scoped**, brief lore snippet. The goal is a non-empty LoreStore for each world, not a full re-author of the genre lore (that's the follow-on content-refresh decision). A 300-400 word world-tier lore establishing the setting/tone/hooks is sufficient.
3. **Server guard:** confirm/extend the empty-LoreStore guard so an un-migrated world (world lore missing, genre lore deleted) raises rather than silently seeding nothing. Mirror the existing required-file pattern (visibility_baseline, lethality_policy).
4. **OTEL:** world-tier lore load emits a watcher event (mirror loader.py state_transition spans) so the GM panel proves world lore actually loaded.
5. **Wiring test:** at least one integration test proving world-tier lore reaches the narrator's LoreStore (per "Every Test Suite Needs a Wiring Test").

**What this story does NOT include:**
- Deletion of genre-tier `lore.yaml` files (gated on verification that every world is migrated; tracked separately if needed).
- Full re-authoring or content refresh of world lore (that's a separate content-improvement decision). The goal is migration, not curation.
- Trope authoring (tropes are a separate story per epic 74).

## Scope Boundaries

**In scope:**
- Audit all 20 live worlds for existing world-tier lore. (SM setup audit: all 20 already have substantial `lore.yaml`, 93–563 lines — see session SM Assessment.)
- Author **world-tier `worlds/<world>/lore.yaml`** for every live world that lacks one or has a sparse placeholder.
- Confirm the server-side empty-LoreStore guard (mirror visibility_baseline / lethality_policy required-file pattern).
- Add/verify OTEL span for world-tier lore load in `lore_seeding.py` (`state_transition` event).
- Integration test: load a migrated world, assert narrator LoreStore is non-empty + contains world-tier fragments.
- Validate against `validate pack` schema.

**Out of scope:**
- Deletion of genre-tier `lore.yaml` (post-verification step).
- Full content re-author or lore re-curation (improvement, not migration).
- Trope authoring (separate story).
- Cultures, archetypes, theme, visual_style, audio migrations (those are separate stories).

## Key Decisions and Constraints

- **Live-world definition:** enumerated above (20 worlds across 11 packs). The audit in `context-epic-74.md` identified these as the "live packs" — those wired into genre pack metadata and playable in the running engine.
- **Wry_whimsy included:** currently aspirational (not default on connect screen), but 11 worlds are authored in the pack directory. Include it in the audit and migration for consistency (wry_whimsy is being prepared for launch per memory notes).
- **Empty-LoreStore guard severity:** "No Silent Fallbacks" — a world with no world lore and no genre lore must fail LOUD at load, not seed nothing. The guard is load-blocking (same tier as visibility_baseline).

## AC Context

1. **World-tier lore authored for all live worlds.** Every live world has a `worlds/<world>/lore.yaml` (or confirms existing one is non-sparse). *Test:* load each of the 20 worlds; assert `world.lore` is present and non-empty.

2. **Narrator LoreStore is world-sourced.** The narrator's RAG receives world lore only (no genre lore). *Test:* fixture world with world lore + load it; assert `query_lore` returns world-tier fragments, none with `lore_genre_*` slug.

3. **Empty LoreStore fails loud.** A world with both no world lore AND no genre lore raises a clear load error. *Test:* fixture world with no `lore.yaml` (genre lore also absent per 74-1 optional load); assert load raises `GenreLoadError` naming the world + lore.yaml (mirrors visibility_baseline loud-fail pattern).

4. **OTEL proves world lore loaded.** World-tier lore load emits a `state_transition` watcher event (`world_lore` or similar, mirroring `world_items`). *Test:* load a world → assert `state_transition` span fires.

5. **All 20 live worlds still load + validate.** `validate pack` green; all packs still boot with the new world lore. *Test:* foreach live world, load the pack; assert no schema errors.

6. **Wiring test.** Integration test proving world-tier lore reaches the narrator in a real session (per "Every Test Suite Needs a Wiring Test"). *Test:* chargen + connect → query_lore in the narrator hook → assert non-empty retrieval.

## Assumptions

- Existing world-tier loaders in `_load_single_world` (story 74-1) are sufficient; only the **content** (world lore files) needs authoring.
- The schema for `worlds/<world>/lore.yaml` matches genre `lore.yaml` (both are `Lore` pydantic model; loader treats them identically per 74-1).
- The "empty LoreStore guard" requirement mirrors existing required-file guards (visibility_baseline / lethality_policy); the pattern exists and can be extended.
- Wry_whimsy is live for the purposes of this audit (11 worlds exist in the pack and the pack is on the cusp of launch per project memory).
- Genre `lore.yaml` files are still present (not deleted) during this story; deletion is a post-verification follow-on.

> If any assumption proves wrong during implementation, log it as a Design Deviation and notify SM.

## Files to Author / Modify

### Content (sidequest-content)
- `genre_packs/*/worlds/*/lore.yaml` — create for worlds that lack world-tier lore or have sparse placeholders. Source each from the genre `lore.yaml` snippet + world-specific context (from the pack's narrative scaffolding, existing world descriptions, etc.).

### Server (sidequest-server)
- `sidequest/game/lore_seeding.py` — confirm/add empty-LoreStore guard (world missing lore + genre lore absent → loud GenreLoadError).
- `sidequest/game/lore_seeding.py` or `sidequest/genre/loader.py` — confirm OTEL span fires on world-tier lore load (`state_transition`, `op="loaded"`, `field="world_lore"`).
- `tests/game/test_lore_seeding.py` (or new integration file) — add wiring test asserting narrator LoreStore is world-sourced (non-empty, world-tier fragments).
- `tests/game/test_world_lore_migration.py` or similar — AC1/AC3/AC5 parametrized load tests covering all 20 worlds.

### Validation
- `validate pack` schema — confirm `lore.yaml` is recognized at both genre and world tier (should be no-op after 74-1 made genre optional).

## Technical Details

**Empty-LoreStore guard location:** likely `lore_seeding.py` post-seed check (after `seed_world_lore` completes) or in `_load_single_world` after world lore load. Mirror the visibility_baseline pattern: if the world's lore is absent AND no fallback exists, raise with a message naming the world + expected file. **Severity:** load-blocking (world does not instantiate).

**OTEL span:** similar to the existing `world_items` span in `_load_world_items` (`loader.py:~1167`). Add a `state_transition` span in the lore load path (either in `lore_seeding.py` or in `_load_single_world` where world lore is loaded). Event shape: `op="loaded"`, `field="world_lore"`, `world_slug=…`, `lore_fragment_count=…`.

**World lore authoring strategy:**
- Read the genre `lore.yaml` (rich, 500+ lines typically).
- Extract the core world-identity fragments (setting, tone, key factions, hooks).
- Adapt into a **world-specific** lore.yaml (200-400 words, free-form narrative).
- If a world already ships its own world lore, audit it for emptiness / placeholder status (e.g., "TODO: write world lore" or a single stub entry). If substantive, leave it; if sparse, flesh it out or replace it.
- Example: `tea_and_murder/worlds/glenross/lore.yaml` probably exists; if it's full, done. If it's sparse or missing, author a glenross-specific lore snippet establishing the setting (moorland village, supernatural undertones, Sonia's love-letter context) and key story hooks.

