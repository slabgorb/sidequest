# Explicit Visual Recipes — Design Spec

**Date:** 2026-04-24
**Status:** Design
**Implements:** ADR-086 (un-defers Path B — recipe-as-data refactor)
**Related:** ADR-070 (Z-Image), ADR-034 (Portrait Identity Consistency), ADR-088 (ADR Frontmatter Schema)

## Purpose

Replace the current fallback-heavy, tier-conditional prompt composer with an
explicit, catalog-driven recipe system. Every rendered image — portrait, POI,
in-game illustration — resolves through one canonical path. Every composed
prompt is inspectable as a single artifact (CLI and OTEL). Characters, POIs,
and styles become addressable resources that can be composed into
scrapbook-style illustrations by ID reference.

## Mental Model

Every render answers four questions, filtered through one aesthetic lens:

| Film-crew term | Slot | Resolves from |
|---|---|---|
| **Casting** | who is in the shot | catalog lookup — `npc:<slug>` · `pc:<id>` · Place landmark · list of participants |
| **Location** | where the shot is set | Place ref — specific (`where:<world>/<slug>`) or archetypal (`where:<genre>/<slug>`) |
| **Direction** | action + camera | authored pose/action + camera preset |
| **Art Sensibility** | style cascade (applied over everything) | `GENRE → WORLD → CULTURE` tokens |

The recipe describes the *shot* (who/where/direction). The art-sensibility
cascade decides *how it's painted*.

## Scope

### In scope

- `Recipe` / `Layer` / `CameraPreset` data types (pydantic models)
- `recipes.yaml` authoring the three canonical recipes (PORTRAIT, POI, ILLUSTRATION)
- Three catalog loaders: `CharacterCatalog`, `PlaceCatalog`, `StyleCatalog`
- Rewritten `PromptComposer` that walks a recipe, resolves slots from catalogs,
  and applies the art-sensibility cascade
- `RenderTarget` input type — a composable reference that can express
  "this character", "this place", or "these participants at this place
  (specific or archetypal) doing this action with this camera"
- `sidequest-promptpreview` CLI — prints the full composed prompt, per-layer
  token breakdown, and warnings for any target
- OTEL span `render.prompt_composed` emitting the same per-layer breakdown
  at runtime
- Fail-loud on missing catalog references (no silent fallbacks per project
  CLAUDE.md)
- Dead server-side copy deletion per ADR-086 story 1
  (`sidequest-server/sidequest/media/{subject_extractor,prompt_composer}.py`
  and tier-prefix definitions in `sidequest-server/sidequest/renderer/models.py`)
- `TACTICAL_SKETCH` tier retirement — becomes `camera: topdown_90` on the
  ILLUSTRATION recipe

### Out of scope

- **Runtime model conditioning for PC fidelity** — ADR-034's tiered
  img2img + IP-Adapter approach was superseded by ADR-086 on 2026-04-24.
  This spec delivers character identity through catalog-authored per-LOD
  tokens; if token authoring proves insufficient for player ownership
  of their PCs in practice, a future ADR can revisit — but that work is
  not in this spec.
- **Per-world `visual_style.yaml` authoring** (ADR-086 story 3) — this spec
  wires the world layer; the worlds themselves get authored later
- **Per-world `cultures/<slug>.yaml` authoring** (ADR-086 story 5) — same;
  one canary culture YAML suffices for the smoke test
- **Token counter + per-layer OTEL instrumentation for budget auditing**
  (ADR-086 story 1) — this spec emits the per-layer *breakdown*; the T5
  tokenizer integration and `visual_budget.yaml` CI gate are a separate
  story
- **Scrapbook UI** — the system produces composable illustrations; the UI
  that displays a session's scrapbook is a separate concern

## Ontology

### Slots (recipe-level)

Named slots that every recipe declares. Slot identity is an enum:

- `CASTING` — who is in the shot
- `LOCATION` — where the shot is set
- `DIRECTION_ACTION` — what is being staged (pose, narrative beat, POI description)
- `DIRECTION_CAMERA` — how it's framed
- `ART_SENSIBILITY` — style cascade; always `[GENRE, WORLD, CULTURE]` in current design

### Cascade layers (applied within ART_SENSIBILITY)

- `GENRE` — `genre_pack/visual_style.yaml` `positive_suffix`
- `WORLD` — `worlds/<world>/visual_style.yaml` `positive_suffix` (if the world
  has one; absent world → skip this layer)
- `CULTURE` — `worlds/<world>/cultures/<slug>.yaml` visual tokens
  (per-character for portraits; per-POI-controller for POIs; mixed for
  illustrations with multiple participants — each participant's culture
  contributes)

### Camera presets

Enumerated in code as a flat `CameraPreset` enum; token prompt shapes live
in `sidequest-daemon/cameras.yaml` so the art-director agent can refine
phrasing without a code change. A recipe's `camera` slot accepts any
preset; the `CameraPreset` enum is not category-bound at the schema level
(e.g., `extreme_closeup_leone` can attach to a portrait OR an
illustration), though the groupings below reflect primary intent.

**Stills-only constraint.** Every preset describes framing, angle, and
composition. Motion-dependent techniques (dolly, zoom, rack-pull,
tracking) are excluded by design — they need temporal change to read and
do not translate to single-frame renders. Do not add them later.

**Portrait framings** (primary: PORTRAIT recipe):

| Preset | Intent |
|---|---|
| `portrait_3q` | 3/4 view, detailed face — default for PORTRAIT |
| `portrait_profile` | strict side profile, sharp silhouette |
| `portrait_closeup` | tight face-only, emotional weight |
| `portrait_full_body` | standing, full outfit/stance visible |

**POI framings** (primary: POI recipe):

| Preset | Intent |
|---|---|
| `wide_establishing` | standard wide shot — default for POI |
| `low_angle_hero` | monumental low angle looking up at a landmark |
| `interior_wide` | architectural interior, depth receding |
| `aerial_oblique` | high-angle aerial, map / scale feel |

**Illustration framings** (primary: ILLUSTRATION recipe):

| Preset | Intent |
|---|---|
| `scene` | painterly mid-distance composition — default for ILLUSTRATION |
| `over_shoulder` | OTS two-shot, dialogue/confrontation |
| `wide_action` | action in middle distance, environmental context |
| `closeup_action` | tight on a single action beat, kinetic |
| `topdown_90` | orthographic tactical, 90° overhead, battle-map framing |

**Signature shots** (directorial techniques; attach to any recipe):

| Preset | Intent |
|---|---|
| `extreme_closeup_leone` | Leone-style magnified feature — eye across the frame, sweat on the brow, the twitch before the draw |
| `dutch_tilt` | camera tilted 15–25° off-horizontal; tension, unreliability, noir |
| `single_point_perspective_kubrick` | rigid symmetric one-point perspective; corridor or hall receding to vanishing point at center |
| `trunk_shot_tarantino` | low POV looking up from inside a container, characters leaning over the frame |

**17 presets total.** Keep the list tight. Adding a preset means authoring
a house-style prompt string in `cameras.yaml`, and every preset that exists
needs to work well across all genres.

### `cameras.yaml` shape

A camera preset has a prompt shape plus an optional post-processing
directive. Some shots cannot be reliably coaxed from any text-to-image
model (notoriously: a true Leone extreme close-up). The escape hatch is
to render a shot the model CAN produce, then crop/rotate to the target
framing as a deterministic post step.

```yaml
# sidequest-daemon/cameras.yaml

portrait_3q:
  prompt: >-
    three-quarter view portrait, centered subject, detailed face,
    shoulders-up framing
  # no post — the model can render this directly

portrait_profile:
  prompt: >-
    profile view portrait, sharp silhouette, subject facing left,
    bust framing

extreme_closeup_leone:
  # Z-Image will not reliably render a true Leone macro — ask for a
  # tight portrait the model CAN produce, then crop aggressively.
  prompt: >-
    tight portrait, single dominant facial feature, macro detail,
    heavy chiaroscuro, sweat and skin texture, shallow depth of field
  post:
    kind: crop
    mode: center      # center | subject_center (if face detection wires up later)
    percent: 0.25     # keep center 25% of the rendered image

dutch_tilt:
  prompt: >-
    dutch angle, camera tilted 15–25° off-horizontal, destabilized
    composition, disoriented framing
  # angle baked into the prompt; no rotate post needed

# ... and so on for all 17
```

**Post-processing kinds (minimal set for MVP):**

- `crop` — center crop to `percent` of the rendered image (0.0–1.0)
- `rotate` — rotate by `degrees` then crop to largest inscribed rectangle

Executed by the daemon after the Z-Image worker returns. Implemented with
Pillow; deterministic; no model inference. If a preset declares `post`,
the render pipeline allocates extra resolution before the crop so the
cropped output still meets the target dimensions — e.g., a 25%
center-crop request on a 1024×1024 target renders at 4096×4096 first.
(Budget: this is a 16× pixel cost; callers requesting aggressive-crop
presets are paying for it. Opt-in per preset.)

**MVP targets for render-then-crop:**

- `extreme_closeup_leone` — the hardest target. Canary for whether the
  post-processing escape hatch actually works. If we can produce a
  convincing Leone closeup via render-then-crop, we've validated the
  mechanism for the whole preset catalog.

If later we want per-camera negative-prompt additions, guidance_scale
tweaks, or more post kinds (mask, blur, film-grain), the schema extends.
For now: `prompt` plus optional `post: {kind, …}`.

## Recipes

Authored in `sidequest-daemon/recipes.yaml`. Loaded and validated at daemon
startup.

```yaml
# sidequest-daemon/recipes.yaml

portrait:
  casting: character               # resolve from CharacterCatalog
  location: background             # world ambient or per-character override
  direction:
    action: pose                   # "3/4 neutral expression" default; character-overridable
    camera: portrait_3q
  art_sensibility: [GENRE, WORLD, CULTURE]

poi:
  casting: landmark                # the POI itself (from PlaceCatalog)
  location: environment            # surrounding landscape (from PlaceCatalog)
  direction:
    action: description            # POI's authored visual_prompt
    camera: wide_establishing
  art_sensibility: [GENRE, WORLD, CULTURE]

illustration:
  casting: participants            # list of character refs (CharacterCatalog)
  location: poi_location           # PlaceCatalog if RenderTarget.location is a POI ref;
                                   # else free-form string from RenderTarget
  direction:
    action: action                 # the scene's narrative beat (free-form)
    camera: "{camera}"             # from RenderTarget.camera — any CameraPreset;
                                   # default is `scene` per recipe
  art_sensibility: [GENRE, WORLD, CULTURE]
```

Recipe names (`casting`, `location`, etc.) match slot types. The right-hand
values name the source binding the composer uses to resolve each slot.

## Catalogs

Loaded at daemon startup. Hot-reload on SIGUSR1 (same pattern as existing
genre pack reload).

### CharacterCatalog

- **Source:** `genre_packs/<genre>/portrait_manifest.yaml` (NPCs) + PC
  character store (`~/.sidequest/saves/<session>.db` or equivalent)
- **Key:** `npc:<slug>` or `pc:<id>`
- **Resolves to:**
  ```python
  class LOD(str, Enum):
      SOLO = "solo"             # this character is the whole image (portrait)
      LONG = "long"             # prominent in an illustration (≤2 main characters)
      SHORT = "short"           # one of several participants (3–4)
      BACKGROUND = "background" # crowd filler, barely visible

  class CharacterTokens(BaseModel):
      kind: Literal["npc", "pc"]               # feeds PC_VISUAL vs NPC_VISUAL prefix
      descriptions: dict[LOD, str]              # one description per LOD level
      default_pose: str                         # "3/4 neutral"
      culture: str | None                       # culture slug, or None
      world: str                                # which world this character belongs to
  ```

### LOD authoring example

`portrait_manifest.yaml` expands to carry all four LODs per character:

```yaml
- id: rux
  type: npc_major
  culture: inquisitor
  descriptions:
    solo: >-
      a tall gaunt inquisitor in his forties, iron-grey hair cropped short,
      deep-set eyes, a faded scar across the left cheekbone, wearing the
      heavy wool cassock of his order with iron-chased black buttons and a
      silver device pinned at the throat, hands callused from the tally-stones
    long: >-
      gaunt inquisitor in grey wool cassock, iron-chased buttons, silver
      device at throat, scar across left cheekbone
    short: >-
      a gaunt inquisitor in grey wool
    background: >-
      an inquisitor
  default_pose: "standing, hands folded, neutral expression"
```

Authoring guidance (to live in the house-style guide after this ships):
`solo` ≈ 40–60 tokens, `long` ≈ 15–25, `short` ≈ 5–10, `background` ≈ 1–3.
Authors write the most specific description once (solo) and derive the
others as progressive removals of detail, preserving the identity signature
(silhouette-defining features) down to `background`.

### POI LOD

POIs face the same problem — a POI as the sole subject of a POI render
gets full treatment, but the same POI serving as location-backdrop in an
illustration needs a terser description. POIs carry two LODs:

- `solo` — used when the POI is the Casting (POI category render)
- `backdrop` — used when the POI is the Location (illustration category)

Only two LODs because POIs are not stacked like participants; a POI is
either the subject or the setting, never one-of-several.

### PlaceCatalog

The "Where" catalog. Covers both **specific** places (named landmarks in
a specific world — what was formerly called POIs) and **archetypal**
places (genre-level stock settings — "a tavern" in low_fantasy, "a
saloon" in spaghetti_western). Both kinds resolve through the same
catalog with the same token structure; the only differences are scope
and whether the `landmark` slot is populated.

This subsumes what the old `_DEFAULT_LOCATION_TAGS` dict was trying to
do (fallback substitution for "tavern / forest / dungeon") — but makes
it explicit, genre-specific, and authored rather than fantasy-biased
and hardcoded.

- **Sources:**
  - Specific: `worlds/<world>/history.yaml` `chapters[].points_of_interest[]`
    (existing structure — kept as-is to avoid disruptive content migration)
  - Archetypal: `genre_packs/<genre>/places.yaml` (new file, subsumes the
    old location-tag defaults)
- **Keys:**
  - Specific: `where:<world>/<slug>` (e.g. `where:flickering_reach/the_lookout`)
  - Archetypal: `where:<genre>/<slug>` (e.g. `where:low_fantasy/tavern`)
  - The `where:` scheme parallels `npc:`, `pc:` — every catalog reference
    is a URI.
- **Resolves to:**
  ```python
  class PlaceLOD(str, Enum):
      SOLO = "solo"           # Place is the subject (POI-recipe render)
      BACKDROP = "backdrop"   # Place is the setting (illustration location)

  class PlaceTokens(BaseModel):
      kind: Literal["specific", "archetypal"]
      landmark: dict[PlaceLOD, str]     # the structure itself; "" for archetypal
      environment: dict[PlaceLOD, str]  # surrounding landscape, per LOD
      description: dict[PlaceLOD, str]  # authored visual_prompt, per LOD
      controlling_culture: str | None   # culture slug (specific places only)
      scope: str                        # world slug (specific) or genre slug (archetypal)
  ```

### Place authoring example — archetypal

`genre_packs/low_fantasy/places.yaml`:

```yaml
tavern:
  landmark:
    solo: ""           # no specific landmark — it's a generic tavern
    backdrop: ""
  environment:
    solo: >-
      wooden-beamed low-ceiling interior, smoke-blackened rafters,
      hearth fire crackling in a stone fireplace, oil-lamp glow on
      ale-stained tables, heavy shutters, a doorway to the cellar
    backdrop: >-
      wooden beams, hearth fire, lamp-lit smoky interior
  description:
    solo: "a tavern common room"
    backdrop: "a tavern"

forest:
  landmark:
    solo: ""
    backdrop: ""
  environment:
    solo: >-
      dense canopy of ancient trees, dappled sunlight through leaves,
      mossy undergrowth, ferns and fallen logs, filtered green light
    backdrop: >-
      canopy shadow, trunks receding, dappled light
  description:
    solo: "deep forest"
    backdrop: "forest"
```

Each genre authors its own archetypes with its own visual vocabulary —
a `tavern` in `spaghetti_western/places.yaml` is a saloon with batwing
doors and whiskey bottles behind the bar; in `neon_dystopia/places.yaml`
it's a neon-lit chrome bar with holographic signage. The archetype
*name* can be shared across genres (useful for cross-genre tooling and
narrator vocabulary), but the *content* is genre-specific.

### Specific vs archetypal — when to use which

- **Specific place** — the narrator (or pre-gen) has placed the scene at
  an authored POI the world knows about. Rux is at *the lookout* in
  flickering_reach. The scene gets the specific landmark, the
  controlling culture, the world's distinct character.
- **Archetypal place** — the narrator has placed the scene at a generic
  location type the world hasn't previously materialized. "They wait in
  a tavern" — any tavern, unnamed, this genre's vocabulary. The archetype
  provides the setting without committing to a specific location.
- **Escape upgrade** — when an archetypal scene recurs or gains
  significance (per SOUL.md's "diamonds and coal" — coal becomes diamond
  when players engage), the GM can promote it to a specific place by
  authoring a POI in the world's history.yaml. The scene's next render
  then resolves as specific.

### StyleCatalog

- **Source:**
  - `genre_packs/<genre>/visual_style.yaml` (genre-level)
  - `genre_packs/<genre>/worlds/<world>/visual_style.yaml` (world-level, optional)
  - `genre_packs/<genre>/worlds/<world>/cultures/<slug>.yaml` (per-culture)
- **Keys:** `genre:<slug>`, `world:<genre>/<world>`, `culture:<genre>/<world>/<slug>`
- **Resolves to layer token strings** (authored prose-free per
  `PROMPTING_Z_IMAGE.md` house style).

## RenderTarget

The composable input. One type serves all three categories.

```python
class RenderTarget(BaseModel):
    kind: Literal["portrait", "poi", "illustration"]
    world: str                        # always required — drives cascade resolution
    genre: str                        # always required

    # Portrait:
    character: str | None = None      # "npc:<slug>" or "pc:<id>"
    pose_override: str | None = None  # optional — overrides character.default_pose
    background: str | None = None     # optional — "where:<scope>/<slug>" place ref;
                                      # default is world ambient

    # POI (specific place beauty shot):
    place: str | None = None          # "where:<world>/<slug>" — must be a specific place

    # Illustration:
    participants: list[str] = []      # list of character refs
    location: str | None = None       # "where:<scope>/<slug>" — specific or archetypal
    action: str = ""                  # the narrative beat
    camera: CameraPreset = CameraPreset.scene   # any preset; defaults per recipe
```

Validation rules:

- `kind=portrait` → `character` required; `place`, `participants`, `action`,
  `camera` must be empty/default. `background` is optional (any valid
  `where:` ref).
- `kind=poi` → `place` required and must resolve to a **specific** place
  (not archetypal — archetypes are for illustration backdrops, not POI
  beauty shots). `character`, `participants`, `action`, `camera` must
  be empty/default.
- `kind=illustration` → `participants` non-empty; `action` non-empty;
  `location` required (either specific or archetypal — the composer
  does not accept free-form location prose, to preserve the fail-loud
  contract); `camera` required.
- All catalog references must resolve — unknown IDs raise
  `CatalogMissError`, not silent fallback.

## Composer

Single public method replacing today's `_build_positive` tangle:

```python
class PromptComposer:
    def __init__(
        self,
        recipes: dict[str, Recipe],
        characters: CharacterCatalog,
        pois: PlaceCatalog,
        styles: StyleCatalog,
    ) -> None: ...

    def compose(self, target: RenderTarget) -> ComposedPrompt: ...
```

`ComposedPrompt` shape:

```python
class LayerContribution(BaseModel):
    slot: str                         # "CASTING", "DIRECTION_CAMERA", "ART_SENSIBILITY.GENRE", ...
    source: str                       # "npc:rux" | "where:flickering_reach/the_lookout" | "where:low_fantasy/tavern" | "genre:mutant_wasteland" | ...
    tokens: str                       # the resolved token string
    estimated_tokens: int             # word-count based estimate (real T5 tokenizer is ADR-086 story 1)

class ComposedPrompt(BaseModel):
    positive_prompt: str              # the final assembled string
    clip_prompt: str                  # short style-aesthetic keywords
    negative_prompt: str              # Z-Image ignores at guidance_scale=0 but preserved for non-Z workers
    worker_type: str
    seed: int
    layers: list[LayerContribution]   # per-layer breakdown for preview + OTEL
    dropped_layers: list[str]         # layers evicted due to T5 budget
    warnings: list[str]               # truncation notes, missing optional sources, etc.
```

### Compose algorithm

1. Load the recipe for `target.kind`.
2. **Determine LOD plan** for this target (see "LOD resolution" below).
3. For each slot in the recipe (`CASTING`, `LOCATION`, `DIRECTION_ACTION`,
   `DIRECTION_CAMERA`), resolve the slot's source binding against the
   catalogs at the planned LOD, producing a `LayerContribution`.
4. For each layer in `ART_SENSIBILITY` (`GENRE`, `WORLD`, `CULTURE`):
   - `GENRE` → `StyleCatalog.get_genre(target.genre)`
   - `WORLD` → `StyleCatalog.get_world(target.genre, target.world)` — may be
     empty, producing an empty `LayerContribution` with `tokens=""`
   - `CULTURE` → resolved per category:
     - portrait: character's culture (or skip if None)
     - POI: `controlling_culture` (or skip if None)
     - illustration: union of participants' cultures (each contributes its
       tokens; composer deduplicates)
4. Assemble in the order: `art_sensibility.genre + art_sensibility.world +
   casting + location + direction.action + direction.camera +
   art_sensibility.culture + house_style_safety_clause`. (Exact split —
   style-prefix vs style-suffix — follows the empirical ordering in
   `PROMPTING_Z_IMAGE.md`: period/medium first, subject, then safety clause
   last. Culture is placed adjacent to its subject tokens for proximity
   attention.)
5. Estimate total tokens. If over T5 512 budget, apply eviction:
   - Drop `LOCATION` flourish (preserve first 8 tokens)
   - Drop `DIRECTION_ACTION` flourish (preserve first 8 tokens)
   - Drop `ART_SENSIBILITY.WORLD` entirely
   - Drop `ART_SENSIBILITY.CULTURE` flourish (preserve first 12 tokens of silhouette/palette)
   - Below here is the **identity floor** — never evict: `CASTING`,
     `DIRECTION_CAMERA`, `ART_SENSIBILITY.GENRE`, base `ART_SENSIBILITY.CULTURE` silhouette,
     base `DIRECTION_ACTION` verb
6. Record `dropped_layers` and `warnings` for inspection.
7. Return `ComposedPrompt`.

### LOD resolution

Each render target implies an LOD plan. The plan is computed by the
composer, not authored, so the recipe doesn't carry LOD logic.

**Character LOD:**

| Category | Participant count | Focus participant | Others |
|---|---|---|---|
| PORTRAIT | 1 | `solo` | — |
| ILLUSTRATION | 1 | `solo` | — |
| ILLUSTRATION | 2 | `long` | `long` |
| ILLUSTRATION | 3–4 | `long` for focus, `short` for rest | `short` |
| ILLUSTRATION | 5+ | `long` for focus, `short` for next 2, `background` for remainder | `background` |

The focus participant is `target.participants[0]` by convention (callers
order participants by importance). If a caller needs to mark a
non-first-position participant as the focus, they reorder; there is no
separate "focus" field on `RenderTarget`.

**POI LOD:**

| Category | POI role | LOD |
|---|---|---|
| POI | POI is the subject | `solo` |
| ILLUSTRATION | POI is the location | `backdrop` |
| PORTRAIT | POI referenced as background (optional) | `backdrop` |

**LOD override:**

`RenderTarget` may carry an optional `lod_override: dict[str, LOD]` for
debug/preview use — pin a specific participant's LOD to inspect the
effect. Production callers should not use this.

**Budget-driven downgrade:**

If the composed prompt at the planned LOD exceeds T5 512, the composer
downgrades participants one rung (long → short → background) starting
from the lowest-priority slot (last participant) and recomposes. This
happens before slot eviction — the goal is to preserve every
participant's presence at some LOD rather than drop a participant
entirely. Participants never drop below `background`; if even
all-background is over budget, `BudgetError` fires.

### Fail-loud points (no silent fallbacks)

- Recipe YAML missing or malformed at startup → daemon refuses to start
- `RenderTarget.character` references unknown ID → `CatalogMissError`
- `RenderTarget.poi` or `RenderTarget.location` (when POI ref) references
  unknown POI → `CatalogMissError`
- Culture slug on a character or POI that doesn't resolve → `CatalogMissError`
  (authoring bug in portrait_manifest or history.yaml)
- Eviction would drop into the identity floor → `BudgetError` with the
  offending breakdown; daemon does not silently produce a degraded render

## Prompt Preview CLI

Installed as `sidequest-promptpreview` via `pyproject.toml` entry point.

```
# Specific character portrait
sidequest-promptpreview portrait \
  --character npc:rux \
  --world flickering_reach \
  --genre mutant_wasteland

# Specific place beauty shot
sidequest-promptpreview poi \
  --place where:flickering_reach/the_lookout \
  --world flickering_reach \
  --genre mutant_wasteland

# Illustration at a specific place
sidequest-promptpreview illustration \
  --participants npc:rux,pc:alex_pc_id \
  --location where:flickering_reach/the_temple \
  --action "arguing about whether to enter, rux gesturing at the door" \
  --camera scene \
  --world flickering_reach \
  --genre mutant_wasteland

# Illustration at an archetypal place (no specific POI authored)
sidequest-promptpreview illustration \
  --participants npc:rux,pc:alex_pc_id \
  --location where:low_fantasy/tavern \
  --action "drinking, rux watching the door" \
  --camera scene \
  --world evropí \
  --genre low_fantasy

# Tactical top-down at a specific place
sidequest-promptpreview illustration \
  --participants npc:goblin_3,npc:goblin_7 \
  --location where:flickering_reach/the_temple \
  --action "ambush from the altar" \
  --camera topdown_90 \
  --world flickering_reach \
  --genre mutant_wasteland

# Leone closeup canary — extreme closeup signature shot
sidequest-promptpreview portrait \
  --character npc:rux \
  --camera extreme_closeup_leone \
  --world flickering_reach \
  --genre mutant_wasteland
```

### Output format

Plain text; machine-readable JSON via `--json`. Default text output:

```
== Target ==
kind:         illustration
world:        flickering_reach
genre:        mutant_wasteland

== Resolved catalogs ==
CASTING:      npc:rux (appearance, culture=inquisitor)
              pc:alex_pc_id (appearance, culture=unbound)
LOCATION:     where:flickering_reach/the_temple (specific; landmark + environment + controlling_culture=witch)
DIRECTION:    action="arguing about whether to enter..."  camera=scene
ART_SENSIBILITY:
              GENRE   mutant_wasteland/visual_style.yaml         23 tok
              WORLD   flickering_reach/visual_style.yaml          9 tok
              CULTURE inquisitor (from npc:rux)                  11 tok
              CULTURE witch (from poi controlling_culture)       14 tok
              CULTURE unbound (from pc:alex_pc_id)                8 tok

== Composed prompt ==
[full assembled string]

== Layer breakdown ==
slot                       source                         tokens   contribution
CASTING                    npc:rux                        22       "..."
CASTING                    pc:alex_pc_id                  18       "..."
LOCATION                   where:.../the_temple           19       "..."
DIRECTION_ACTION           inline                          14       "..."
DIRECTION_CAMERA           scene                            6       "..."
ART_SENSIBILITY.GENRE      genre:mutant_wasteland          23       "..."
ART_SENSIBILITY.WORLD      world:.../flickering_reach       9       "..."
ART_SENSIBILITY.CULTURE    inquisitor+witch+unbound        33       "..."
                                                       ------
                                                          144       (of 512 T5 budget)

== Warnings ==
(none)
```

OTEL span `render.prompt_composed` emits the same structure (minus the CLI
framing) so the GM panel can surface layer breakdowns on live renders.

## File changes

### Added

- `sidequest-daemon/sidequest_daemon/media/recipes.py` — `Recipe`, `Layer`,
  `CameraPreset`, `RenderTarget`, `ComposedPrompt`, `LayerContribution` types
- `sidequest-daemon/sidequest_daemon/media/catalogs.py` —
  `CharacterCatalog`, `PlaceCatalog`, `StyleCatalog`, loaders, `CatalogMissError`
- `sidequest-daemon/sidequest_daemon/media/preview.py` — CLI implementation
- `sidequest-daemon/recipes.yaml` — the three canonical recipes
- `sidequest-daemon/cameras.yaml` — token prompt shapes for the 17 camera presets
- `sidequest-daemon/tests/test_recipes.py` — recipe YAML validation tests
- `sidequest-daemon/tests/test_catalogs.py` — catalog loader + miss-error tests
- `sidequest-daemon/tests/test_composer.py` — composition per-category tests
  (unit)
- `sidequest-daemon/tests/test_composer_wiring.py` — wiring test: renderer
  worker calls the new composer and produces a non-empty prompt (per
  CLAUDE.md "every test suite needs a wiring test")
- `sidequest-daemon/tests/test_preview_cli.py` — CLI round-trip tests
- `sidequest-daemon/tests/golden/` — snapshot fixtures (same input → same
  composed prompt)
- `sidequest-daemon/tests/fixtures/` — minimal test genre pack / world /
  characters / places (specific + archetypal)
- `sidequest-content/genre_packs/<genre>/places.yaml` — new per-genre
  archetypal place catalog (11 genre packs × one file each; seed content
  ports and rewrites the old `_DEFAULT_LOCATION_TAGS` defaults per genre)

### Modified

- `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` — fully
  rewritten; `_TIER_PROMPT_PREFIX`, `_DEFAULT_LOCATION_TAGS`, and the
  per-tier branching removed
- `sidequest-daemon/sidequest_daemon/renderer/models.py` — `TACTICAL_SKETCH`
  tier removed from `RenderTier` enum; `CameraAngle` enum added; `StageCue`
  gains a `camera` field
- `sidequest-daemon/pyproject.toml` — add `sidequest-promptpreview` CLI
  entry point
- `sidequest-daemon/sidequest_daemon/renderer/base.py` — renderer worker
  migrates from passing `StageCue` directly to constructing a `RenderTarget`
  and calling the new composer
- `sidequest-server/sidequest/renderer/models.py` — dead tier-prefix
  definitions removed; shared `StageCue` and `RenderTier` protocol types
  remain

### Deleted

- `sidequest-server/sidequest/media/subject_extractor.py` (dead copy)
- `sidequest-server/sidequest/media/prompt_composer.py` (dead copy)
- `sidequest-server/tests/**` entries testing the above dead copies

## Testing strategy

### Unit

- **Recipe YAML validation** — missing slot, unknown camera preset, unknown
  cascade layer name → loader error messages
- **Catalog loaders** — roundtrip a minimal fixture pack; missing culture
  slug / place slug (specific or archetypal) / character slug →
  `CatalogMissError`
- **Place kind validation** — POI recipe rejects archetypal places;
  illustration accepts either; archetypal places with a populated
  `landmark` LOD fail validation (archetypes have no landmark)
- **Composer per-category** — for each kind, build a RenderTarget against
  fixtures, assert resolved layers match expected slots
- **Eviction order** — force token budget overflow, assert layers drop in
  the specified priority
- **Identity floor** — oversized inputs that would evict through the floor
  → `BudgetError`

### Wiring (required per CLAUDE.md)

- **Renderer worker → composer** — the existing `flux_mlx_worker` and
  `zimage_mlx_worker` build a RenderTarget and receive a non-empty
  `ComposedPrompt` from the new composer
- **Daemon startup** — invalid recipes.yaml prevents daemon start (no silent
  degradation)

### Integration

- **Preview CLI round-trip** — each target kind, verify output format and
  that fixtures compose deterministically
- **Golden snapshots** — same RenderTarget + same catalogs + same recipes →
  byte-identical `positive_prompt` (serves as regression guard for prompt
  drift)

### Out of testing scope

- Live rendered image quality (that's subjective; the prompt-preview output
  IS the testable contract)
- Token-accurate budget accounting (current estimate uses word-count × 1.3;
  ADR-086 story 1 adds the real T5 tokenizer)

## Migration notes

- `TACTICAL_SKETCH` removal is hard: callers currently passing
  `RenderTier.TACTICAL_SKETCH` must migrate to `StageCue(camera="topdown_90")`
  in the same PR. Search surface is small (combat encounter rendering,
  map generation) — all migrated in-scope.
- `_DEFAULT_LOCATION_TAGS` dict (fantasy-biased location keyword fallbacks)
  deleted. Its content is **ported** into `genre_packs/<genre>/places.yaml`
  as archetypal places — rewritten per genre rather than sharing a single
  fantasy-biased set. `tavern`, `forest`, `dungeon`, `castle`, `market`,
  `cave`, `temple`, `battlefield` all migrate, genre-rewritten as needed
  (low_fantasy keeps the wooden-beamed tavern; spaghetti_western gets a
  saloon; neon_dystopia gets a neon-lit chrome bar; and so on). Callers
  that used to rely on keyword substitution now reference
  `where:<genre>/<slug>` explicitly — and a missing archetype for a
  requested genre fails loud, forcing the gap to be authored rather than
  papered over.
- `visual_tag_overrides` in `visual_style.yaml` — each override migrates
  into the matching place's authored description in
  `worlds/<world>/history.yaml` (for specific places) or into the
  genre's `places.yaml` (for ones that should be archetypal). The
  migration script walks existing overrides, matches them to place slugs
  by keyword, and writes the token string into the place's `solo` (and
  `backdrop`) description fields. Overrides that don't match any place
  become an authoring report — a human decides whether to create a
  specific place, an archetype, or drop the override.
- **Existing `portrait_manifest.yaml` entries** currently carry a single
  description field. The new schema requires four LOD variants. Migration
  strategy: author a one-off script that takes each existing single-string
  description as the `solo` LOD and flags the character for manual LOD
  authoring (long/short/background). The art-director agent's scope
  expands to include LOD authoring for every character. Flickering Reach's
  NPC set is the canary — migrate it fully; other worlds ship with only
  `solo` populated and `long`/`short`/`background` raising loud errors
  if requested, until manually authored.
- **Existing POI (specific place) entries** carry a single
  `visual_prompt`. Same migration: the existing string is the `solo`
  LOD; `backdrop` requires manual authoring. Any illustration
  referencing a specific place that lacks a `backdrop` LOD fails loud
  with the remediation message ("author `backdrop` LOD in
  worlds/X/history.yaml for place Y").
- **Archetypal places** require authoring from zero per genre pack.
  Migration script can seed from `_DEFAULT_LOCATION_TAGS` for
  low_fantasy and caverns_and_claudes (the fantasy-biased defaults land
  naturally there), but each of the other genres needs a human author
  to write archetypal entries for their setting. The art-director
  agent's scope expands here too.

## Open questions for the implementation plan

1. `visual_tag_overrides` migration path (see Migration notes above).
2. PC culture resolution — PCs don't have a `culture` field in today's
   character store. Added as part of this spec, but the store schema
   migration is a separate concern. For this spec's delivery, PC culture
   can be `None` (no culture layer contribution); populating PCs with
   culture is a follow-on.
3. Scrapbook persistence — illustrations generated during play need
   somewhere to live (image file + the `RenderTarget` that produced them).
   This spec produces the compositions; where they're stored is out of scope
   and belongs to a scrapbook-storage spec.

## Canary: the Leone test

Keith has not been able to get a genuine Sergio Leone extreme close-up
out of any text-to-image model to date. The `extreme_closeup_leone`
preset is the **canary** for whether the camera-preset mechanism
actually delivers framings the model struggles with:

- If the `prompt + post: crop` combination produces a recognizable
  Leone closeup on at least one canary character in at least two
  genre packs, the mechanism is validated.
- If it doesn't, the failure mode tells us whether to push harder on
  prompt engineering, increase the pre-crop resolution, add a face-
  detection crop center mode, or accept that some framings are
  out of reach and downgrade the preset's claims in the catalog.

Either way, the Leone preset exists to exercise the hardest case.
Easier presets (portrait_3q, wide_establishing) will work; we already
know that. The Leone shot is where we learn.

## Success criteria

- [ ] `sidequest-promptpreview` prints a full composed prompt for each of
      PORTRAIT / POI / ILLUSTRATION targets against the canary world
      `flickering_reach`
- [ ] Swapping `--participants` on an illustration target (same place, same
      action, different characters) produces visibly different prompts
      with different culture contributions
- [ ] Swapping `--location` on an illustration target between two specific
      places produces a visibly different prompt with different
      landmark/environment contributions
- [ ] Swapping `--location` on an illustration target from a specific
      place (`where:flickering_reach/the_temple`) to an archetypal place
      (`where:low_fantasy/tavern`) produces a visibly different prompt —
      same characters, same action, different Where resolution path
- [ ] Swapping `--camera scene` → `--camera topdown_90` produces a visibly
      different prompt; the tactical render path works without
      `TACTICAL_SKETCH`
- [ ] A missing catalog reference produces a clear `CatalogMissError` with
      the source and missing ID, not a degraded render
- [ ] OTEL span `render.prompt_composed` is visible in the GM panel with
      per-layer breakdown on every live render
- [ ] All dead server-side copies deleted; no production code imports them
- [ ] Full test suite green; wiring test confirms renderer workers use the
      new composer
- [ ] Leone canary: `extreme_closeup_leone` preset produces a
      recognizable Leone-style closeup via `prompt + crop` on at least
      one character in at least two genre packs (or the failure mode is
      documented and the preset's claims downgraded)

## References

- ADR-086 — Image-Composition Taxonomy (this spec implements Path B)
- ADR-070 — Z-Image / MLX Image Renderer
- ADR-034 — Portrait Identity Consistency (PC_VISUAL seam)
- `sidequest-content/PROMPTING_Z_IMAGE.md` — house prompt style
- `sidequest-daemon/sidequest_daemon/media/prompt_composer.py` — current
  composition (to be rewritten)
- `sidequest-daemon/sidequest_daemon/renderer/models.py` — current
  `RenderTier` / `StageCue` definitions
