---
id: 86
title: "Image-Composition Taxonomy — Portraits, POIs, Illustrations"
status: proposed
date: 2026-04-24
deciders: [Keith Avery]
supersedes: [71]
superseded-by: null
related: [34, 70, 71]
tags: [media-audio]
implementation-status: deferred
implementation-pointer: null
---

# ADR-086: Image-Composition Taxonomy — Portraits, POIs, Illustrations

> Captures a hand-drawn design sketch (slabgorb, 2026-04-24) into a durable
> taxonomy. Most of what the sketch describes already exists in code under
> different names; this ADR consolidates the mental model, names the implicit
> concepts, and identifies the genuinely new additions.

Touches the visual pipeline broadly. Does not block any in-flight work but
unlocks several follow-ons. Coordinate with **ADR-034** (Portrait Identity
Consistency) — fits cleanly inside this taxonomy at the PC_VISUAL seam.
The renderer is Z-Image (ADR-070); every cascade layer in this ADR is a
text-token layer.

## Operating Premise

**Every pixel of visual identity flows through text prompts.** Z-Image
follows prompt instructions well, but only what we actually write —
anything we omit, the model invents. This makes prompt composition the
load-bearing mechanism of the visual pipeline, not a supporting one.

Three consequences follow directly:

1. **Layer discipline matters.** Each cascade slot (GENRE / WORLD /
   SCENE / NARRATIVE / CAMERA / etc.) must carry distinct, non-overlapping
   information. Duplication wastes tokens and dilutes attention; gaps let
   the model drift. The taxonomy below names the slots so duplication and
   gaps are visible at review time.
2. **Token budget is generous but finite.** Z-Image Turbo encodes
   prompts with T5 (512-token ceiling, `guidance_scale=0`, no negative
   prompt — see `sidequest-content/PROMPTING_Z_IMAGE.md`). In practice
   our shipping prompts run 80–200 tokens, so the ceiling is not a
   daily concern — but without a counter we can't tell when we cross
   it, and truncation at T5's limit is silent. Every cascade layer
   competes for the same budget, and layering CULTURE + WORLD + SCENE
   atop a verbose GENRE suffix can close the gap faster than
   expected. Prompt audits are routine — see "Token Budget
   Discipline" below.
3. **Per-genre prompt authoring is a craft, not a config setting.**
   `positive_suffix` is the real style load. Genre packs need precise,
   terse, deliberate style strings — every word earns its place or
   gets cut. The `art-director` agent's domain expands accordingly.

This ADR is therefore not optional polish. It is the design framework
that makes the pipeline workable.

## Context

SideQuest renders three kinds of images:

1. **Portraits** — single character, 3/4 framing, used in the character sheet
   and party panel. Pre-generated for canon NPCs, generated on demand for
   player characters.
2. **POIs (Points of Interest)** — landscapes/establishing shots of named
   locations. Pre-generated from `worlds/<world>/history.yaml`
   `chapters[].points_of_interest[]`.
3. **Illustrations** — in-game action shots, multi-character moments,
   tactical map views. Generated on demand during play via the
   `SceneInterpreter` → `Renderer` → daemon path.

Today these three categories share a single composition mechanism: a
`RenderTier` enum keyed against a flat `_TIER_PROMPT_PREFIX` dict in
`sidequest-daemon/sidequest_daemon/media/prompt_composer.py`. The composer
concatenates: `tier prefix → narrative subject → genre positive_suffix →
location tag override`. Camera angle is hardcoded per tier
(`TACTICAL_SKETCH` is always top-down; everything else is a default
"camera"). Character identity is metadata-only — `portrait_manifest.yaml`
distinguishes `npc_major | npc_supporting`, but the daemon never reads it.

This works but conflates several orthogonal concerns:

- **Category** (what kind of image — portrait vs landscape vs scene)
- **Composition layer** (background, pose, participants, narrative)
- **Style cascade** (genre identity + world flavor + scene atmosphere)
- **Camera** (default vs orthographic top-down)
- **Subject identity** (PC vs NPC, cultural affiliation)

A 2026-04 design sketch proposes promoting all five concerns to first-class
named slots. This ADR adopts the taxonomy and identifies what already exists
versus what needs to be added.

### Prior Art

- **`RenderTier` enum** (`daemon/renderer/models.py`): PORTRAIT,
  PORTRAIT_SQUARE, LANDSCAPE, SCENE_ILLUSTRATION, TACTICAL_SKETCH. Closest
  existing analog to "category."
- **`_TIER_PROMPT_PREFIX`** (`daemon/media/prompt_composer.py:19`): flat
  `dict[Tier, str]`. Closest existing analog to "prefix layer," but
  unstructured.
- **`VisualStyle.positive_suffix`** (`daemon/genre/models.py:32-39`):
  genre-level art direction. Implements the GENRE step of the sketch's
  cascade.
- **`VisualStyle.visual_tag_overrides`**: per-location atmosphere tags.
  Implements something close to the SCENE step of the cascade.
- **`StageCue.characters: list[str]`** (`daemon/renderer/models.py:37`):
  participant list. Passed through but not used as a distinct prompt
  layer — collapsed into the narrative subject string.
- **`portrait_manifest.yaml` `type: npc_major | npc_supporting`**:
  PC/NPC distinction. Read by batch scripts only; the daemon is unaware.
- **ADR-034 (Portrait Identity Consistency)**: proposes IP-Adapter
  re-rendering for PC portraits. Naturally seams at the PC_VISUAL vs
  NPC_VISUAL split this ADR introduces.

### Server-side dead copies (to be removed)

A 2026-04-24 split-brain audit confirmed the visual pipeline has
unwired duplicates in `sidequest-server/`:

- `sidequest-server/sidequest/media/subject_extractor.py` — identical
  to the daemon's live copy at `sidequest-daemon/sidequest_daemon/media/subject_extractor.py`.
  No imports in the server.
- `sidequest-server/sidequest/media/prompt_composer.py` — diverged
  from the daemon copy (missing `PORTRAIT_SQUARE` tier support and
  several negatives). No production consumers.
- `sidequest-server/sidequest/renderer/models.py` — server-side
  `RenderTier` and tier-prefix definitions, advisory only. The daemon's
  `daemon/renderer/base.py` and `daemon/renderer/models.py` are
  authoritative.

This ADR resolves the ambiguity by naming the daemon copies as
canonical for every named slot in the taxonomy. The dead server
copies are formally orphaned and must be deleted as part of story 1
(see Implementation Sketch). Leaving them in place is a future
divergence risk — a maintainer extending the "wrong" `prompt_composer.py`
will produce silently incorrect renders, and the bug will be invisible
because nothing imports the file.

Shared protocol types (`StageCue`, `RenderTier` enum membership) live
in `sidequest-server/sidequest/protocol/` and remain authoritative
there; only the renderer implementation copies are dead.

## Decision

Adopt the three-category taxonomy as the **organizing mental model** for
the visual pipeline. Document each category's prefix-layer recipe and
cascade. Add the genuinely new concepts (WORLD cascade level, CULTURE
cascade across portraits and POIs, switchable CAMERA parameter,
daemon-readable PC/NPC type) without refactoring the existing tier-based
composition machinery.

### The taxonomy

#### 1. PORTRAITS

| Slot | Source | Status |
|---|---|---|
| **PREFIX: NPC_VISUAL or PC_VISUAL** | `portrait_manifest.yaml` `type` field, surfaced to daemon via API | New (metadata exists, daemon wiring missing) |
| **CULTURE** | character entry `culture: <slug>` → `worlds/<world>/cultures/<slug>.yaml` visual tokens | New |
| **SCENE** (background) | `worlds/<world>/visual_style.yaml` background tags | Partial (genre level only today; world-level missing) |
| **NARRATIVE** (pose / framing) | character entry `pose` field, default "3/4 portrait, neutral expression" | New (no `pose` field on portrait entries today) |
| **Style cascade: GENRE → WORLD → CULTURE → SCENE** | `VisualStyle.positive_suffix` (genre) + `worlds/<world>/visual_style.yaml` (world) + culture entry (culture) + `visual_tag_overrides` (scene) | Partial (genre + scene wired; world + culture missing) |

The PC vs NPC split is the seam where ADR-034's PC-fidelity pipeline
forks off (IP-Adapter for PCs, standard txt2img for NPCs).

CULTURE is the slot that lets an inquisitor and a witch sharing the same
world read as mutually unrecognizable at a glance — not through different
genres or different worlds, but through distinct cultural visual
vocabulary (dress, iconography, silhouette, material palette, lighting
affect). CULTURE is a cross-category layer: it applies equally to POIs
(see below) and to portraits. One culture definition, two render paths.

#### 2. POIs

| Slot | Source | Status |
|---|---|---|
| **PREFIX: POI_VISUAL** | `_TIER_PROMPT_PREFIX[LANDSCAPE]` | Exists (unnamed) |
| **CULTURE** | new POI metadata `culture: <slug>` → `worlds/<world>/cultures/<slug>.yaml` visual tokens | New |
| **DESCRIPTION** | `points_of_interest[].visual_prompt` | Exists |

POIs remain pre-generated. The new CULTURE layer lets the same geographic
landmark render differently under different cultural control (an
Inquisition cathedral vs a witches' grove hall = same footprint, different
visual treatment). It also covers political "faction" overlay as a
subset — an Imperial garrison is a case of the Imperial culture's visual
vocabulary applied to a fortified POI. Faction is the narrow case;
CULTURE is the general one. This serves the "world grows from play"
principle (SOUL.md → Yes, And) applied to landscapes — a cultural
takeover of a POI should be visible.

**CULTURE definition.** Culture-specific visual vocabulary — robes,
sigils, architecture motifs, material palette, typical lighting — is
authored in `worlds/<world>/cultures/<slug>.yaml` as prose-free visual
tokens (in the `PROMPTING_Z_IMAGE.md` house style) and composed into
the prompt alongside WORLD and SCENE.

#### 3. ILLUSTRATIONS

| Slot | Source | Status |
|---|---|---|
| **PREFIX: SCENE** | `_TIER_PROMPT_PREFIX[SCENE_ILLUSTRATION]` | Exists (unnamed) |
| **CAMERA** | new `StageCue.camera: CameraAngle` enum (`DEFAULT`, `TOPDOWN_90`) | New |
| **PARTICIPANTS** | `StageCue.characters` | Exists (passed but not layered) |
| **NARRATIVE** | scene description distilled by `_distill_visual()` | Exists |

The CAMERA parameter unifies what are today two separate tiers
(SCENE_ILLUSTRATION + TACTICAL_SKETCH). `TOPDOWN_90` becomes a camera
variant of ILLUSTRATION rather than its own tier — a tactical battle map
is conceptually "the same scene, viewed from above."

Rendered ILLUSTRATION with CAMERA=TOPDOWN_90 is now **the** tactical map
path. ADR-071 (Tactical ASCII Grid Maps) is withdrawn in favor of this
approach — ASCII rendering of rooms and positions is being removed from
the system. The tactical layer is image-native going forward, with
spatial data (entity tokens, AoE overlays, hazard zones) delivered as
structured metadata alongside the rendered map rather than as a text
grid.

`TACTICAL_SKETCH` remains as a backward-compatibility shim for the
handful of existing callers; deprecate after CAMERA parameter ships and
those callers migrate.

### What this ADR does NOT decide

- **Recipe-class refactor** (Path B in the architect's analysis):
  promoting `_TIER_PROMPT_PREFIX` from `dict[Tier, str]` to
  `dict[Tier, list[NamedLayer]]`. This was considered and deferred —
  the rename adds no rendered-pixel value today. Revisit opportunistically
  the next time `prompt_composer.py` needs structural changes for another
  reason.
- **PC fidelity pipeline**: ADR-034 owns the PC_VISUAL render path.
  This ADR only commits to surfacing the `type` field to the daemon so
  034 has a routing seam.

## Token Budget Discipline

T5's 512-token ceiling is the hard limit per render. The named cascade
layers must therefore have a defined **eviction order** — when a render
request exceeds budget, the composer drops layers in reverse priority
order rather than truncating arbitrarily mid-string.

**Eviction order (lowest priority first dropped):**

| Order | Layer | Rationale |
|---|---|---|
| 1 (drop first) | SCENE atmosphere tags | Per-location flavor; cosmetic |
| 2 | NARRATIVE pose / framing detail beyond a base pose | Refinement, not identity |
| 3 | CULTURE tokens beyond a base silhouette/palette marker | Detail within a culture; silhouette must survive |
| 4 | WORLD style tokens | Within-genre flavor; valuable but not load-bearing |
| 5 | PARTICIPANTS beyond the first 2 named characters | Renders gracefully degrade to "and others" |
| 6 (drop last) | GENRE positive_suffix + category PREFIX (NPC_VISUAL / POI_VISUAL / SCENE) + base CULTURE silhouette | The non-negotiable identity floor |

The PREFIX, GENRE, and base CULTURE silhouette together are the
**identity floor**. Below that, the render no longer represents either
the genre or who (or whose) is being depicted — better to render fewer
participants in a recognizable mutant_wasteland Inquisition scene than
five participants in a generic-painterly nowhere.

**Required tooling (call out for the implementation stories):**

- A token counter that reports per-layer cost on every composed prompt,
  visible in OTEL spans (`render.prompt_composed` event with
  `layers: {GENRE: 23, WORLD: 14, SCENE: 9, NARRATIVE: 18, ...}`
  fields). The GM panel can then surface "this render hit the budget
  ceiling and dropped the WORLD layer" as a first-class observation —
  per CLAUDE.md's OTEL principle, the dashboard is the lie detector for
  every subsystem, including the prompt composer.
- A per-genre `prompt_audit.md` doc (or YAML budget) committed alongside
  each genre pack's `visual_style.yaml`, declaring the intended token
  cost of `positive_suffix` and a target budget for the WORLD and SCENE
  layers. CI fails if `positive_suffix` exceeds the declared budget.

## Consequences

### Positive

- **Mental model matches code organization.** Reading the daemon code,
  the genre packs, and the design sketch will all describe the same
  three categories with the same named layers.
- **Three independent stories unlock visible value.** WORLD cascade,
  CULTURE cascade, and CAMERA parameter are each isolated, single-PR
  stories that produce visibly different renders. Hand to Captain Carrot
  one at a time.
- **ADR-034 gets a place to land.** Portrait Identity Consistency has
  been "proposed" for months because there was no settled host structure
  for the PC vs NPC split. This ADR provides the seam (PC_VISUAL vs
  NPC_VISUAL prefix layer) where 034's PC-fidelity pipeline forks from
  the standard NPC path.
- **Cultural differentiation enables territorial gameplay.** Once a
  character or POI can render under a controlling culture, the world
  visibly changes when cultures clash — an inquisitor and a witch
  sharing a scene read as distinct at a glance, and a cathedral that
  changes hands changes appearance. Supports the "Living World"
  principle in SOUL.md.
- **Visual-pipeline split-brain closed.** Naming the daemon copies
  canonical and deleting the server-side duplicates (story 1)
  collapses three audit findings into a single resolution. Future
  contributors stop guessing which `prompt_composer.py` is real.

### Negative

- **ADRs 086 and 034 overlap.** Future readers must consult both to
  understand the portrait pipeline. Mitigation: cross-link in each
  ADR's status block.
- **`TACTICAL_SKETCH` deprecation creates a small migration cost.**
  Existing TACTICAL_SKETCH consumers (combat encounters) need to switch
  to `ILLUSTRATION` + `CAMERA = TOPDOWN_90`. Backward-compat shim
  during the transition keeps blast radius small.
- **Culture YAML authoring is a new house-style discipline.** Authors
  will need guidance on writing prose-free visual tokens per
  `PROMPTING_Z_IMAGE.md` — art-director agent's scope expands to cover
  culture authoring review.

### Neutral

- **No code changes from this ADR alone.** Decision document only.
  Implementation lives in follow-up stories.

## Implementation Sketch

Five stories. The first two are foundational and should land before the
additive ones; the last three are the sketch-driven additions.

1. **Token counter + per-layer OTEL instrumentation + dead-copy
   deletion** (foundational). Add a T5 token counter (tokenizer runs
   locally — ships with the renderer). Extend
   `PromptComposer._build_positive()` to return both the composed
   prompt and a `layers: dict[LayerName, int]` token cost map. Emit
   `render.prompt_composed` OTEL span with the layer breakdown plus a
   `budget_remaining` field (T5 512 minus composed). Without this,
   every subsequent story is operating blind on token economics.

   **Deletion clause (non-negotiable, same PR):** Remove the
   server-side dead copies named in Prior Art —
   `sidequest-server/sidequest/media/subject_extractor.py`,
   `sidequest-server/sidequest/media/prompt_composer.py`, and the
   tier-prefix / `RenderTier` definitions in
   `sidequest-server/sidequest/renderer/models.py`. The shared
   `StageCue` and `RenderTier` enum stay in `sidequest-server/sidequest/
   protocol/`. Verify with `rg` that no production code imports the
   removed modules; tests of the dead modules go with them. Without
   this deletion, the new instrumentation work creates a third
   divergent copy of the very files this ADR is trying to canonicalize.

2. **Per-genre prompt audit + budget enforcement** (foundational).
   Walk every shipping genre pack's `positive_suffix`. Measure T5
   tokens. Author a `visual_budget.yaml` per genre declaring intended
   costs for GENRE / WORLD / CULTURE / SCENE / NARRATIVE layers. Add a
   CI check that fails if any genre's `positive_suffix` exceeds its
   budget. Every shipping genre pack needs an audit pass — stylistic
   authoring quality varies, and this is the moment to true them up to
   the house style in `PROMPTING_Z_IMAGE.md`.

3. **WORLD cascade level.** Add `worlds/<world>/visual_style.yaml`
   reader. Extend `PromptComposer._build_positive()` to insert
   world-level style tokens between genre `positive_suffix` and
   per-location `visual_tag_overrides`. Update one canary world
   (`mutant_wasteland/flickering_reach`) with a world-level style
   block; verify rendered output shifts. Token budget for WORLD layer
   declared in the canary's `visual_budget.yaml` from story 2. Worlds
   without a `visual_style.yaml` get no WORLD layer — genre-only
   remains a valid default.

4. **CAMERA parameter on StageCue.** Add `CameraAngle` enum
   (`DEFAULT`, `TOPDOWN_90`) to `daemon/renderer/models.py`. Thread
   through `StageCue` and `PromptComposer`. Map `CameraAngle.TOPDOWN_90`
   to top-down framing tokens in the ILLUSTRATION prefix. Wire
   `SceneInterpreter` to set `TOPDOWN_90` for combat cues. This is the
   tactical-map rendering path; spatial data (positions, AoEs, hazards)
   rides alongside as structured metadata — the image is the picture,
   not a text grid. Mark `TACTICAL_SKETCH` tier deprecated and migrate
   its few callers during the same PR.

5. **PC/NPC type wiring + CULTURE cascade.** Surface
   `portrait_manifest.yaml` `type` field in the daemon's portrait API.
   Add `culture: <slug>?` to portrait manifest entries and to POI
   entries in `history.yaml`. Create the `worlds/<world>/cultures/`
   directory with at least one canary culture YAML (the inquisitor /
   witch pair in a heavy_metal or low_fantasy canary is the obvious
   smoke test). Extend `PromptComposer._build_positive()` to read the
   culture YAML and insert its visual tokens between WORLD and SCENE.
   Verify: the same character prompt with different `culture` slugs
   produces visibly different portraits, same world, same genre.

**Order:** (1) and (2) first — without instrumentation and a sober
look at current per-genre token costs, the additive stories are
guesswork. (3) WORLD cascade as the smoke test that the cascade
mechanism works. (4) CAMERA, which closes out the tactical-rendering
path. (5) CULTURE last, since it layers on top of the world mechanism
from (3) and benefits from the OTEL layer-breakdown from (1).

## References

- 2026-04-24 design sketch (slabgorb, hand-drawn — cross-cutting taxonomy)
- 2026-04-23 playtest pingpong file (`~/Projects/sq-playtest-pingpong.md`)
- ADR-034 — Portrait Identity Consistency
- ADR-050 — Image Pacing Throttle
- ADR-070 — MLX Image Renderer
- ADR-071 — Tactical ASCII Grid Maps (withdrawn — superseded by this
  ADR's ILLUSTRATION + CAMERA.TOPDOWN_90 path)
- `sidequest-content/PROMPTING_Z_IMAGE.md` — house prompt style
- `daemon/media/prompt_composer.py` — current composition mechanism
- `daemon/renderer/models.py` — `RenderTier`, `StageCue`
- `content/genre_packs/*/visual_style.yaml` — genre cascade today
- `content/genre_packs/*/portrait_manifest.yaml` — PC/NPC metadata today
