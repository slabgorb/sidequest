# Player Portrait Selection — Pre-Generated Sample Faces per World

**Date:** 2026-05-26
**Epic:** 66 (Character Creation Depth)
**Status:** Design — approved, pending implementation plan
**Repos:** sidequest-server, sidequest-ui, sidequest-daemon, sidequest-content

## Problem

Players are created today with **no portrait at all** — the `Character` model has no
portrait field, character creation has no portrait step, and nothing renders a face for
the PC. Meanwhile the portrait *generation* pipeline is fully built and a convention for
pre-generated "picker" portraits already exists on disk (coyote_star carries 10
`type: player_picker` entries). The selection half is missing.

This feature lets character creation present a grid of pre-generated sample faces — set
against the player's world locations — to pick as an avatar. The portrait sticks with the
character. It is explicitly "better than no portrait at all," not a custom-portrait system.

## Scope

**This story builds the mechanism only.** It does not author the ~20 portraits per world
and does not render pilot content now (the media daemon is committed to other work, and
mechanism-first lets the backdrop recipe be tuned before a content fan-out). Authoring
portraits per world is a downstream content deliverable, surfaced by the load-time
validator and the Epic 65 R2 gap audit.

### Decisions locked during brainstorming

- **Composition:** portrait-in-POI backdrop (character framed against a recognizable
  world location), not plain headshots.
- **Allocation convention (for later authoring):** culture-weighted spread across each
  world's cultures, ~66/33 male/female (≈13M / 7F of 20). This is an authoring guideline
  documented here; no portraits are authored by this story.
- **Binding:** purely cosmetic, **soft-suggested with free override** — the grid surfaces
  build-matching faces first but the player may pick any of the set. Gender is never a
  selection filter.
- **Modeling (Fork 1-A):** pickers live in the existing `portrait_manifest.yaml` as
  `type: player_picker` entries, served by filtering `CharacterCatalog` /
  `PortraitManifestEntry`. No separate picker file or catalog.
- **Recipe (Fork 2-A):** the existing portrait recipe + LOCATION layer + a new
  `portrait_in_location` camera preset carrying the montage-trap guard. Not the runtime
  illustration recipe.

## Key infrastructure facts (verified)

- **Generation pipeline exists:** `scripts/generate_portrait_images.py` walks every
  world's `portrait_manifest.yaml`, composes prompts, renders via the daemon over the
  Unix socket, writes `.../worlds/<world>/images/portraits/<slug>.png`, and r2_sync
  uploads. No new generation code path is needed beyond the new camera preset.
- **`PortraitManifestEntry`** (`sidequest-server/sidequest/genre/models/pack.py:97`) is
  `extra="ignore"` (Rust parity). Adding fields will **not** break pack load — but any
  key not declared on the model is *silently dropped*, so picker metadata the endpoint
  must serve has to be added as real fields. The model today carries only
  `name / role / type (character_type) / appearance / culture_aesthetic / element_visual`
  — notably **no `culture`, `archetype`, `sex`, or `backdrop_poi`**.
- **A manifest validator already exists:** `_validate_portrait_manifest`
  (`sidequest-server/sidequest/cli/validate/pack.py:238`). Picker validation extends it
  rather than adding a new check.
- **POIs are pure landscapes today.** There is no existing "character in a location"
  composition in the portrait pipeline; the `portrait_in_location` preset is the new seam.
- **The Z-Image montage trap is the central rendering risk** (see memory
  `feedback_zimage_no_montage_single_closeup`): describing a tight face *and* a separate
  wide scene makes Z-Image render a split close-up/wide montage and drops stray faces into
  scenery. The fix is the Leone move: long telephoto lens, subject planted inside the POI,
  shallow depth-of-field, explicit single-continuous-photograph guard.

## Design

### 1. Content schema — `PortraitManifestEntry` field additions (model change)

Add four fields to `PortraitManifestEntry`, all optional/defaulted so existing manifests
remain valid under `extra="ignore"`:

| Field | Type | Purpose |
|-------|------|---------|
| `culture` | `str = ""` | Culture id — drives wardrobe visual tokens and soft-suggest match |
| `archetype` | `str = ""` | Archetype id — soft-suggest match against the in-progress build |
| `sex` | `str = ""` | `male` / `female` — ratio bookkeeping only; **never** a selection filter |
| `backdrop_poi` | `str = ""` | POI slug from `history.yaml`; empty → plain portrait |

The existing `character_type` field (alias `type`) carries the `player_picker`
discriminator. Naming convention stays `picker_<culture>_<archetype>_<sex><nn>`.

### 2. Generation recipe — `portrait_in_location` camera preset (daemon)

New camera preset in the daemon's `recipes.py` / `prompt_composer.py`. Composition layers:

- **CASTING** — subject appearance (LOD-truncated to the T5 token budget as today).
- **LOCATION** — the `backdrop_poi` resolved through the existing `PlaceCatalog`.
- **DIRECTION_CAMERA** — the montage guard *is* this layer: long telephoto lens
  (compression), subject planted in the POI foreground, shallow depth-of-field softening
  the location behind them, explicit single-continuous-photograph framing. No phrasing
  that implies two separate shots (a face and a place).
- **ART_SENSIBILITY** — genre + world + culture visual-token cascade as today.

`scripts/generate_portrait_images.py` routes a `player_picker` entry through
`portrait_in_location` when it declares a `backdrop_poi`, passing the place ref; entries
without one fall back to the existing plain-portrait preset. Output path and R2 sync are
unchanged. `fidelity="high_fidelity"` (consistent quality for pre-gen) as today.

### 3. Character model + persistence (server)

Add `portrait_ref: str | None = None` to `Character` (`sidequest-server/sidequest/game/character.py`),
e.g. `"npc:picker_hegemonic_officer_f01"`. Nullable → no save migration. It serializes
into the character snapshot and restores on load automatically via Pydantic.

### 4. REST endpoint (server)

`GET /api/chargen/portraits/{genre}/{world}` returns:

```json
[ { "slug": "...", "culture": "...", "archetype": "...",
    "sex": "...", "role": "...", "portrait_url": "https://cdn..." } ]
```

Filtered to entries where `character_type == "player_picker"`. URLs via
`resolve_asset_url`. An **empty list is a valid response** (worlds with no pickers yet) —
not an error, not a hidden control.

### 5. UI picker (client)

New `pick_portrait` phase in the `CharacterCreation` FSM, placed after stat arrangement
and before the story/confirm phase (so the chosen archetype + culture are known and can
drive soft-suggest). Behavior:

- Fetch the endpoint, render a thumbnail grid.
- **Soft-suggest:** a "best fit" section first, containing portraits whose
  `archetype` + `culture` match the in-progress build; the full set is browsable below.
  Any pick is allowed. **Gender is never used to filter or sort.**
- A first-class **Skip** affordance leaves `portrait_ref` null ("no portrait" is a valid
  outcome — better than nothing, but not mandatory).
- **Empty endpoint** → a calm "no sample portraits for this world yet" state. The step
  itself always exists in the flow (no flickering data-gated step, per memory
  `feedback_no_flickering_data_gated_tabs`); only its *content* is empty, and completion
  is never blocked.

### 6. Builder wiring (server)

The confirmation payload carries `selected_portrait_ref`. In
`handlers/character_creation.py`, after `builder.build()` returns the `Character`, set
`character.portrait_ref = payload.selected_portrait_ref` (None when skipped) before the
snapshot save. Persists via the existing snapshot path.

### 7. Validation — extend the existing load-time validator (server)

Extend `_validate_portrait_manifest` (`cli/validate/pack.py`) to warn **loud** when a
`player_picker` entry:

- references a `backdrop_poi` slug not present in the world's `history.yaml`, or
- is missing `culture`, `archetype`, or `sex`.

No content-coupled pytest asserting "world has N pickers" (per memory
`feedback_no_content_coupled_tests`). The "live world should have pickers" expectation is
a content deliverable, surfaced by this validator and the Epic 65 R2 gap audit — not a
server unit test.

### 8. OTEL (per the project OTEL Observability Principle)

Emit a `chargen.portrait_select` span on selection:

```
{ world, selected_portrait_ref, was_suggested: bool, pool_size: int, skipped: bool }
```

So the GM panel confirms the step fired and whether the player took a suggestion,
overrode it, or skipped. Cosmetic-only changes elsewhere need no span.

### 9. Testing

- **Fixture test:** `portrait_in_location` composition asserts the telephoto + LOCATION
  layer + single-shot guard are present and that montage-prone phrasing (a face *and* a
  separate wide scene) is absent. Fixture-driven, not a live pack.
- **Round-trip test:** `Character.portrait_ref` survives snapshot save → load.
- **Endpoint test:** the REST route returns correctly-filtered pickers from a **fixture**
  catalog (not a live pack), and returns `[]` for a world with none.
- **Wiring test (required):** drive chargen confirmation with a `selected_portrait_ref`
  through the real handler and assert it lands on the built `Character` reachable from the
  production code path; assert the `chargen.portrait_select` OTEL span fired (no
  source-text grep wiring assertions, per server CLAUDE.md).
- **Validator tests:** on fixtures — missing-field and dangling-`backdrop_poi` cases warn.

## Out of scope (explicit)

- Authoring the ~20 portraits per world (content fan-out, separate deliverable).
- Rendering any pilot content as part of this story (daemon committed elsewhere;
  mechanism-only by decision).
- Custom / player-uploaded portraits (a possible future direction — "might do some custom
  stuff").
- Changing a portrait mid-game.

## Risks / notes

- **Paired model change discipline:** the section-1 field additions must ship in the same
  PR as any manifest authoring that uses them; because the model is `extra="ignore"`, an
  un-paired field is silently dropped (data-invisible) rather than failing loud, so the
  validator (section 7) is the guard that makes the gap visible.
- **Montage trap** is the dominant render-quality risk; the `portrait_in_location` preset
  is the single place it is mitigated, and the fixture test is the regression guard.
- **Soft-suggest needs build state at the picker step** — the FSM placement (after stat
  arrangement) guarantees archetype + culture are resolved before `pick_portrait`.
