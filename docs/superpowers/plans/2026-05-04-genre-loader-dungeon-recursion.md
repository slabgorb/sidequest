# Genre Loader — Dungeon Recursion (hub-and-dungeons world shape)

**Date:** 2026-05-04
**Status:** Draft
**Repo:** sidequest-server (loader); sidequest-content already on disk
**Spec parent:** `docs/superpowers/specs/2026-05-04-caverns-claudes-hub-design.md`
**Related plan:** `docs/superpowers/plans/2026-05-04-caverns-claudes-hub-content.md` (content done; PR #181 draft)
**Follow-on plan (must land before full server-test passes):** `docs/superpowers/plans/2026-05-05-deleted-world-slug-test-sweep.md` *(to be authored)* — 44 test files hardcode `grimvault` / `horden` / `mawdeep` / `dungeon_survivor` / `primetime` as world slugs; those directories are gone, so the tests fail before this loader change is even reached. That sweep is sequenced AFTER the dungeon-pick routing (engine plan item 4), because the right replacement target is `caverns_three_sins` + a dungeon selection, not a leaf world.

## Why

The Hamlet of Sünden content (PR slabgorb/sidequest-content#181) restructures `worlds/caverns_three_sins/` into a hub world plus a `dungeons/<name>/` subdirectory, where each dungeon owns its cartography, openings, rooms, creatures, drift profile, wound profile, and approach. The current loader requires every world directory to carry its own `cartography.yaml` and `openings.yaml`, so the hub world fails load with `cartography.yaml not found at world level`. Until the loader recurses, no part of the content can be playtested. This is the first of five engine plans the hub design depends on; the other four (save persistence, stress field, dungeon-pick UI, narrator prompt-zones) layer on top.

## Scope

This plan ends when:
- `load_genre_pack` returns successfully for `caverns_and_claudes` with `caverns_three_sins.dungeons == {"grimvault": Dungeon, "horden": Dungeon, "mawdeep": Dungeon}`.
- Every other genre pack loads unchanged (no dungeons/ subdir, no behavior change). Verified by enumeration: a `find genre_packs -type d -name dungeons` returns exactly one path today (`caverns_three_sins/dungeons`), so the new code path is bypassed everywhere else.
- A session connect into a *hub* world (no delve target) fails loudly with a clear authoring/UX message — no silent fallback to one of its dungeons.
- A session connect into a *non-hub* world is bit-identical to today.
- `tests/genre/test_loader.py` is green. Currently has 14 failing tests; *all of them are caused by the hub world failing to load on today's loader,* and they go green once this plan lands.

**Explicitly NOT a goal of this plan:** full `just server-test` green. The pre-existing damage from the content PR — 44 test files anchored on deleted world slugs (`grimvault`, `horden`, `mawdeep`, `dungeon_survivor`, `primetime`) — was created by the content restructure, not by this plan. Those failures persist regardless of whether the loader is fixed; the right time to repair them is *after* the dungeon-pick routing exists, so they can be retargeted at `caverns_three_sins` plus a dungeon selection. Tracked separately (see follow-on plan above).

**Out of scope** (separate plans, in spec §"Engine Surface"):
- Save persistence for roster / Wall / drift flag / wound flag (item 2).
- Stress field on the character model (item 3).
- Dungeon-pick UI and the routing change that lets a hub world actually start a delve (item 4).
- Narrator prompt-zone consumption of `drift_profile.yaml` / `wound_profile.yaml` / Wall (items 5-7).
- Any save-file migration. Legacy saves are throwaway per `feedback_legacy_saves`.

## Design

### 1. New `Dungeon` model (slim variant of `World`)

`sidequest/genre/models/pack.py` already has `World`. Add a sibling `Dungeon` aggregate. The shape mirrors `World` minus the world-level fields the parent already owns. Concretely:

```python
class DungeonConfig(BaseModel):
    """Top of dungeon.yaml. Slim variant of WorldConfig."""
    model_config = {"extra": "allow"}

    parent_world: str            # NEW required field — must equal containing world slug
    sin: str | None = None       # caverns_three_sins-specific; future packs can ignore
    name: str
    description: str
    cover_poi: str | None = None
    axis_snapshot: dict[str, float] = Field(default_factory=dict)

class Dungeon(BaseModel):
    model_config = {"extra": "allow"}
    config: DungeonConfig
    cartography: CartographyConfig                    # MANDATORY at dungeon level
    openings: list[Opening] = Field(default_factory=list)  # MANDATORY (see §3)
    legends: list[Legend] = Field(default_factory=list)
    tropes: list[TropeDefinition] = Field(default_factory=list)
    visual_style: Any = None        # optional override
    portrait_manifest: list[PortraitManifestEntry] = Field(default_factory=list)
    # Approach (Ashgate / Copperbridge / Gristwell) — raw YAML; no schema yet
    approach: Any = None
    # Narrator-zone fodder; engine consumes in a later plan
    drift_profile: Any = None
    wound_profile: Any = None
    # Per-dungeon factions/creatures/encounter_tables/rooms — keep raw for now;
    # a follow-up plan can promote them to typed models when consumers exist.
    factions_raw: Any = None
    creatures_raw: Any = None
    encounter_tables_raw: Any = None
    rooms_raw: Any = None
```

Add `dungeons: dict[str, Dungeon] = Field(default_factory=dict)` to the existing `World` model. Default empty preserves every other world.

### 2. Hub vs leaf detection in the loader

In `_load_single_world` (`sidequest/genre/loader.py`):

```python
dungeons_dir = world_path / "dungeons"
is_hub = dungeons_dir.is_dir() and any(p.is_dir() for p in dungeons_dir.iterdir())
```

This is the only branch point. Keep it explicit and local — no class hierarchy, no separate loader function for hubs.

### 3. Conditional file requirements

Today's loader treats `cartography.yaml` and `openings.yaml` as mandatory at the world level. Make them **conditional on `is_hub`**:

| File | Hub world (`is_hub=True`) | Leaf world (`is_hub=False`, today's behavior) |
|------|---------------------------|------------------------------------------------|
| `world.yaml` | required | required |
| `lore.yaml` | required | required |
| `cartography.yaml` | **rejected** (loud error if present at hub level) | required |
| `openings.yaml` | **rejected** (loud error if present at hub level) | required |
| `rooms.yaml` | rejected | optional (only when navigation_mode = room_graph) |
| everything else (legends, tropes, archetypes, history, visual_style, portrait_manifest, archetype_funnels, npcs, char_creation, rigs, magic) | unchanged — same optional-vs-required as today | unchanged |

Rationale for "rejected at hub": *no silent fallback*. If an authoring mistake puts `cartography.yaml` at the hub level it must fail load with a message pointing at the right place (`dungeons/<name>/cartography.yaml`). Same for `openings.yaml`.

For hub worlds, the loader builds a `World` with `cartography=None` (see §4, model change) and `openings=[]`. The downstream guard in §6 catches anyone who tries to use them.

### 4. Make `World.cartography` and `World.openings` legitimately optional

`World.cartography: CartographyConfig` is currently required. Change to `CartographyConfig | None` with default `None`. `World.openings` is already a list with default `[]`, so no model change there — but the loader's `_validate_opening_bank_coverage` and the other openings validators must skip when `is_hub=True`.

This is the riskiest change in the plan because *every existing consumer* of `world.cartography` assumes non-`None`. Mitigation: a single grep for `\.cartography` in `sidequest-server/sidequest/` returns one production consumer (`websocket_session_handler.py`), which is gated behind `is_hub` by the §6 guard. All other accesses are on the `Dungeon` (where it stays required) or on a known-leaf world.

### 5. `_load_single_dungeon`

New helper in `loader.py`. Mirrors `_load_single_world` minus the world-only fields:

```python
def _load_single_dungeon(
    dungeon_path: Path,
    parent_world_slug: str,
    genre_tropes: list[TropeDefinition],
) -> Dungeon:
    config = _load_yaml(dungeon_path / "dungeon.yaml", DungeonConfig)
    if config.parent_world != parent_world_slug:
        raise GenreLoadError(
            path=dungeon_path / "dungeon.yaml",
            detail=(
                f"dungeon.yaml parent_world={config.parent_world!r} does not "
                f"match containing world {parent_world_slug!r}. "
                "parent_world must equal the slug of the directory containing dungeons/."
            ),
        )
    cartography = _load_yaml(dungeon_path / "cartography.yaml", CartographyConfig)
    # rooms.yaml: optional, same shape as world-level (room_graph mode)
    # openings.yaml: required at dungeon level — same validators as world-level
    # legends, tropes, visual_style, portrait_manifest, drift_profile, wound_profile,
    # approach, factions, creatures, encounter_tables, rooms: optional
    ...
    return Dungeon(...)
```

The dungeon-level openings file goes through the same `_validate_opening_setting_references` / `_validate_present_npcs_resolve` / `_validate_opening_bank_coverage` chain. Slug for error messages: `worlds/{parent}/dungeons/{dungeon}/openings.yaml`.

`_load_single_world` calls `_load_single_dungeon` for each child of `dungeons/` when `is_hub`, populates `World.dungeons`, and skips its own `cartography`/`openings` loads.

### 6. Downstream guard — fail loud when starting a session in a hub world

In `sidequest/server/websocket_session_handler.py`, today's line 242 reads:

```python
if world is None or not world.openings:
    # logs world_or_openings_missing and returns early
```

A hub world has `world.openings == []` (openings live on each dungeon), so it would silently fall into that early-return branch and the user sees a generic "no openings" failure instead of the real reason. **The hub-rejection MUST be inserted upstream of that line — before the openings check, immediately after the `world` lookup resolves.** Order matters; this is the bug my first draft missed.

```python
# (insert before the existing `if world is None or not world.openings:`)
if world is not None and world.dungeons:
    # Hub world. Cannot start a delve directly; the dungeon-pick UI
    # (separate plan) routes through here. Until that ships, fail loud.
    raise SessionInitError(
        "hub_world_requires_dungeon_selection",
        f"World {world.config.slug!r} is a hub world with "
        f"{len(world.dungeons)} dungeons. Select a dungeon "
        "(dungeon-pick UI not yet implemented; tracked separately as "
        "engine-plan item 4 of the Hamlet-of-Sünden spec). Available: "
        f"{sorted(world.dungeons)}.",
    )
```

(Use whatever the codebase's standard refusal pattern is at that site — match it; don't invent a new exception type.)

This is deliberate: hub world load must succeed, but trying to start a session in one without picking a dungeon is a loud error until item 4 ships. *Not a stub* — this is the correct terminal behavior for "engine doesn't support this entry path yet."

The cartography accesses further down the same handler (lines ~1431, 1437, 1461, 1470, 1471, 1475) all sit downstream of the early-return for `world is None`, but the hub-rejection above is what *actually* keeps `world.cartography is None` from reaching them. With the guard in place, every cartography access in the file runs on a non-hub world by construction.

### 7. Validators — what changes

- `_validate_opening_setting_references`, `_validate_crew_npc_references`, `_validate_authored_npc_uniqueness`, `_validate_present_npcs_resolve`, `_validate_opening_bank_coverage`: **no change** to their signatures. The world-level loader skips calling them entirely for hub worlds (since hub worlds carry no openings or rigs). The dungeon-level loader calls all five against the dungeon's openings + (currently empty) rigs/npcs.
- New rejection check in `_load_single_world`: when `is_hub`, raise if `cartography.yaml` or `openings.yaml` exists at world level.
- New parent-link check in `_load_single_dungeon`: `config.parent_world == parent_world_slug` (already shown above).

### 8. What lives at the hub vs the dungeon — final inventory

| File | Hub level | Dungeon level |
|------|-----------|----------------|
| world.yaml | ✓ | — |
| dungeon.yaml | — | ✓ |
| lore.yaml | ✓ | — |
| history.yaml | ✓ (optional) | — |
| legends.yaml | ✓ (optional) | ✓ (optional, dungeon-local) |
| factions.yaml | ✓ (optional, regional) | ✓ (optional, dungeon-local; raw) |
| archetypes.yaml | ✓ (optional, world roster) | — |
| archetype_funnels.yaml | ✓ (optional) | — |
| visual_style.yaml | ✓ (optional, world default) | ✓ (optional, override) |
| portrait_manifest.yaml | ✓ (optional, hamlet cast) | ✓ (optional, dungeon-local) |
| pacing.yaml | ✓ (optional) | — |
| audio.yaml | (genre-pack level only — unchanged) | — |
| hamlet.yaml | ✓ (optional; raw on `World`, schema later) | — |
| cartography.yaml | rejected | required |
| rooms.yaml | rejected | optional (room_graph mode) |
| openings.yaml | rejected | required |
| creatures.yaml | rejected | optional (raw for now) |
| encounter_tables.yaml | rejected | optional (raw for now) |
| tropes.yaml | ✓ (optional) | ✓ (optional, dungeon-local) |
| approach.yaml | — | ✓ (optional; raw) |
| drift_profile.yaml | — | ✓ (optional; raw, narrator consumes later) |
| wound_profile.yaml | — | ✓ (optional; raw, narrator consumes later) |

`hamlet.yaml` is loaded as raw YAML and stored on `World` as `hamlet: Any = None`. A typed schema lives in a later plan (the hamlet-services / Wall persistence work).

## Tasks

1. **Models.** Add `DungeonConfig` and `Dungeon` to `sidequest/genre/models/pack.py`. Add `dungeons: dict[str, Dungeon]` and `hamlet: Any = None` to `World`. Make `World.cartography` `CartographyConfig | None` with default `None`. (~30 LOC.)
2. **Loader — hub detection + rejection.** In `_load_single_world`, compute `is_hub` once. If hub, raise on world-level `cartography.yaml` / `openings.yaml` / `rooms.yaml` / `creatures.yaml` / `encounter_tables.yaml` (the rejected list above). Skip cartography/openings loads + their validators when hub. (~40 LOC.)
3. **Loader — `_load_single_dungeon`.** New function. Load dungeon.yaml + cartography + openings (run all five validators against the dungeon scope) + optional raw fields. (~120 LOC; mostly mirrors `_load_single_world` body.)
4. **Loader — recursion wiring.** In `_load_single_world`, when `is_hub`, iterate `dungeons_dir`, call `_load_single_dungeon`, populate `World.dungeons`. Also load optional `hamlet.yaml` raw. (~15 LOC.)
5. **Session-handler guard.** Add hub-world rejection in `websocket_session_handler.py` (per §6). Match the file's existing refusal pattern. (~15 LOC.)
6. **Update existing test_loader.py assertions.** `tests/genre/test_loader.py:161` and `:400` both assert `world.cartography is not None` for *every* world in the loop — that was correct yesterday and wrong today. Update to either skip hubs (`if world.dungeons: continue`) or split into "leaf worlds have cartography" + "hub worlds have non-empty `dungeons`". Pick the split form — it documents the new invariant. The 14 currently-failing tests in this file all stem from today's loader exploding on the hub; once the loader recurses, they pass without further intervention. Re-run the full file at the end of this task and confirm 0 failures.
7. **Tests — hub world loads.** New `tests/genre/test_loader_hub_world.py`: full `load_genre_pack("caverns_and_claudes")` succeeds; `worlds["caverns_three_sins"].dungeons` has the three expected slugs; `worlds["caverns_three_sins"].cartography is None`; each `Dungeon.cartography` is non-`None`; each `Dungeon.config.parent_world == "caverns_three_sins"`.
8. **Tests — leaf worlds unchanged.** Quick load of one leaf world from a different genre pack (e.g. `space_opera`) — assert no behavior change (cartography present, openings present, dungeons empty).
9. **Tests — authoring-mistake rejections.** Use a tmp_path fixture: world directory with both `cartography.yaml` AND a `dungeons/foo/` subdir → `GenreLoadError` with the rejection message. Dungeon with mismatched `parent_world` → `GenreLoadError`. Dungeon missing required `cartography.yaml` → `GenreLoadError`. Hub world with an empty `dungeons/` directory → `GenreLoadError` (the hub-with-zero-dungeons defense from Risks).
10. **Tests — wiring (per CLAUDE.md "Every Test Suite Needs a Wiring Test").** Connect a fake session against a hub world via the websocket session handler entry point; assert the §6 hub-rejection error message fires *and that the handler does not fall through to the openings-missing branch* (this is the bug the upstream-of-line-242 placement guards against). Not a unit test of the guard — a real call through the handler.
11. **Smoke run.** Run `tests/genre/` only — should be green. Run `tests/server/test_room_graph_init.py` and `tests/server/test_chargen_dispatch.py` to *re-confirm* they still fail (with the same world-slug-missing errors as before this plan), demonstrating that those failures are owned by the follow-on test-sweep plan, not regressions caused here. Then `just up`, then attempt to start a session against `caverns_and_claudes/caverns_three_sins` from the UI — verify the hub error surfaces (no silent fallback, no crash). Then start a session in a non-hub world and verify it still works.
12. **Land the content PR.** Once `tests/genre/` is green and the smoke check passes, mark slabgorb/sidequest-content#181 ready-for-review (still `--base develop` per gitflow). Pair with this server change in the PR description; cross-link the follow-on test-sweep plan so reviewers know the broken `tests/server/` files are tracked, not forgotten.

## Risks

- **Cartography contract breach.** Making `World.cartography` Optional ripples to anyone who cached `world.cartography` somewhere I missed. The grep returned one consumer, but I'd rather catch a second one in CI than at runtime — the `pyright` / `mypy` configuration on the server should flag any `world.cartography.x` access against the new Optional. If type-checking is not enforced in CI, add a quick `grep -rn '\.cartography\.' sidequest-server` audit step to task 10.
- **Validator skip on hub worlds.** Skipping the opening-bank validators at hub level *moves* the requirement to dungeon level, not removes it. If a future hub world ships with zero dungeons, both validators will silently pass. Defend with a hub-validator: when `is_hub`, the dungeons dict must be non-empty (we already have the truth — `is_hub` is derived from "dungeons/ exists AND has children"). Add this assertion.
- **Authoring-mistake rejections need to be loud.** A plain "file not found" is unhelpful. The rejection messages must say *why* the file is rejected (`"hub world cannot carry world-level cartography.yaml; move it to dungeons/<name>/cartography.yaml"`) per *No Silent Fallbacks*.
- **Other genre packs are untouched but the loader runs more code.** A hub-detection grep on every world load is cheap, but the test suite must demonstrate non-hub loads still pass to catch a subtle regression.

## Definition of Done

- All twelve tasks complete.
- `tests/genre/` green (specifically: the 14 failing tests in `test_loader.py` flip green, plus the new hub-world test file is green).
- `just server-lint` green.
- `just up` boots; UI can browse to `caverns_three_sins` (hub error fires loudly when a session is attempted; no crash).
- A non-hub world (e.g. `space_opera/coyote_star`) still starts a session normally.
- PR slabgorb/sidequest-content#181 ready for review (still draft until item 2/3/4 of the spec ship).
- The 44 broken `tests/server/` files referencing deleted world slugs (`grimvault`, `horden`, `mawdeep`, `dungeon_survivor`, `primetime`) remain broken at the same point they were broken before this plan started — *neither fixed nor regressed*. Their repair belongs to the follow-on plan and is sequenced after the dungeon-pick routing.
