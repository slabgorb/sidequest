# ADR-086: Image-Composition Taxonomy — Portraits, POIs, Illustrations

> Captures a hand-drawn design sketch (slabgorb, 2026-04-24) into a durable
> taxonomy. Most of what the sketch describes already exists in code under
> different names; this ADR consolidates the mental model, names the implicit
> concepts, and identifies the genuinely new additions.

## Status

Proposed (2026-04-24)

Touches the visual pipeline broadly. Does not block any in-flight work but
unlocks several follow-ons. Coordinate with **ADR-034** (Portrait Identity
Consistency) — fits cleanly inside this taxonomy at the PC_VISUAL seam.

**Note:** ADR-032 (Genre LoRA Style Training) was superseded on 2026-04-24
in favor of ADR-070 (Z-Image / MLX Image Renderer). Z-Image follows text
prompt art direction better than trained LoRAs achieved in practice. This
ADR therefore treats the GENRE cascade layer as a text concern
unconditionally — no LoRA-vs-text branching exists in the design space.

## Operating Premise

**Every pixel of visual identity flows through text prompts.** There is no
trained style anchor to fall back on. Z-Image follows prompt instructions
well, but only what we actually write — anything we omit, the model
invents. This makes prompt composition the load-bearing mechanism of the
visual pipeline, not a supporting one.

Three consequences follow directly:

1. **Layer discipline matters.** Each cascade slot (GENRE / WORLD /
   SCENE / NARRATIVE / CAMERA / etc.) must carry distinct, non-overlapping
   information. Duplication wastes tokens and dilutes attention; gaps let
   the model drift. The taxonomy below names the slots so duplication and
   gaps are visible at review time.
2. **Token budget is fixed.** CLIP's 77-token limit (and the looser 512
   for T5) is the hard ceiling for every render. No LoRA reduces it.
   Every cascade layer competes for the same budget. Prompt audits must
   become routine — see "Token Budget Discipline" below.
3. **Per-genre prompt authoring becomes a craft, not a config setting.**
   `positive_suffix` was acceptable as boilerplate when LoRA was going to
   carry the real style load. Now it IS the real style load. Genre packs
   need precise, terse, deliberate style strings — every word earns its
   place or gets cut. The `art-director` agent's domain expands
   accordingly.

This ADR is therefore not optional polish. It is the design framework
that makes a no-LoRA pipeline workable.

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
- **Subject identity** (PC vs NPC, faction affiliation)

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
- **ADR-032 (Genre LoRA)** — superseded 2026-04-24. Originally proposed
  moving genre style out of text prompts into a LoRA weight. Withdrawn
  in favor of ADR-070 (Z-Image), which follows text prompts well enough
  that LoRA training is not needed. GENRE remains a text layer.
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
cascade. Add the genuinely new concepts (WORLD cascade level, FACTION
cascade for POIs, switchable CAMERA parameter, daemon-readable PC/NPC
type) without refactoring the existing tier-based composition machinery.

### The taxonomy

#### 1. PORTRAITS

| Slot | Source | Status |
|---|---|---|
| **PREFIX: NPC_VISUAL or PC_VISUAL** | `portrait_manifest.yaml` `type` field, surfaced to daemon via API | New (metadata exists, daemon wiring missing) |
| **SCENE** (background) | `worlds/<world>/visual_style.yaml` background tags | Partial (genre level only today; world-level missing) |
| **NARRATIVE** (pose / framing) | character entry `pose` field, default "3/4 portrait, neutral expression" | New (no `pose` field on portrait entries today) |
| **Style cascade: GENRE → WORLD → SCENE** | `VisualStyle.positive_suffix` (genre) + `worlds/<world>/visual_style.yaml` (world) + `visual_tag_overrides` (scene) | Partial (genre + scene wired; world layer missing) |

The PC vs NPC split is the seam where ADR-034's PC-fidelity pipeline
forks off (IP-Adapter for PCs, standard txt2img for NPCs).

#### 2. POIs

| Slot | Source | Status |
|---|---|---|
| **PREFIX: POI_VISUAL** | `_TIER_PROMPT_PREFIX[LANDSCAPE]` | Exists (unnamed) |
| **FACTION** | new POI metadata field linking to faction visual identity | New |
| **DESCRIPTION** | `points_of_interest[].visual_prompt` | Exists |

POIs remain pre-generated. The new FACTION layer lets the same geographic
landmark render differently when controlled by different factions
(Imperial garrison vs Rebel hideout = same coordinates, different visual
treatment). This is the "world grows from play" principle (SOUL.md → Yes,
And) applied to landscapes — a faction's takeover of a POI should be
visible.

**Open question:** does FACTION mean "tag the POI with the faction's
visual identity tokens" (e.g., Imperial banners, Rebel graffiti) or
"reuse the faction's NPC_VISUAL as a style anchor" (e.g., the leader's
LoRA weighted into the landscape render)? Defer the choice until the
first concrete consumer exists. Document as a follow-up question on the
implementation story.

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

`TACTICAL_SKETCH` remains as a backward-compatibility shim for now;
deprecate after the camera parameter ships.

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

(Originally a third item here addressed "GENRE = text vs LoRA" pending
ADR-032's direction. ADR-032 was superseded 2026-04-24 — GENRE is text,
no decision needed.)

## Token Budget Discipline

With no LoRA, the 77-token CLIP budget and 512-token T5 budget are the
absolute ceiling for visual identity per render. The named cascade layers
must therefore have a defined **eviction order** — when a render request
exceeds budget, the composer must drop layers in reverse priority order
rather than truncating arbitrarily mid-string.

**Proposed eviction order (lowest priority first dropped):**

| Order | Layer | Rationale |
|---|---|---|
| 1 (drop first) | SCENE atmosphere tags | Per-location flavor; cosmetic |
| 2 | NARRATIVE pose / framing detail beyond a base pose | Refinement, not identity |
| 3 | WORLD style tokens | Within-genre flavor; valuable but not load-bearing |
| 4 | PARTICIPANTS beyond the first 2 named characters | Renders gracefully degrade to "and others" |
| 5 (drop last) | GENRE positive_suffix + category PREFIX (NPC_VISUAL / POI_VISUAL / SCENE) | The non-negotiable identity floor |

The PREFIX and GENRE layers together are the **identity floor**. Below
that, the render no longer represents the genre — better to render fewer
participants in a recognizable mutant_wasteland scene than five
participants in a generic-painterly nowhere.

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
  FACTION cascade, and CAMERA parameter are each isolated, single-PR
  stories that produce visibly different renders. Hand to Captain Carrot
  one at a time.
- **ADR-034 gets a place to land.** Portrait Identity Consistency has
  been "proposed" for months because there was no settled host structure
  for the PC vs NPC split. This ADR provides the seam (PC_VISUAL vs
  NPC_VISUAL prefix layer) where 034's PC-fidelity pipeline forks from
  the standard NPC path.
- **POI faction-awareness enables territorial gameplay.** Once a POI
  can render differently per controlling faction, the world visibly
  changes when factions clash — supports the "Living World" principle
  in SOUL.md.
- **Visual-pipeline split-brain closed.** Naming the daemon copies
  canonical and deleting the server-side duplicates (story 1)
  collapses three audit findings into a single resolution. Future
  contributors stop guessing which `prompt_composer.py` is real.

### Negative

- **Three ADRs (086, 032, 034) now overlap.** Future readers must
  consult all three to understand the portrait pipeline. Mitigation:
  cross-link in each ADR's status block.
- **Faction visual identity is undefined.** The FACTION cascade slot
  exists but the substance is deferred. If no concrete consumer
  emerges, this slot ages out as documentation debt.
- **`TACTICAL_SKETCH` deprecation creates a small migration cost.**
  Existing TACTICAL_SKETCH consumers (combat encounters) need to switch
  to `ILLUSTRATION` + `CAMERA = TOPDOWN_90`. Backward-compat shim
  during the transition keeps blast radius small.

### Neutral

- **No code changes from this ADR alone.** Decision document only.
  Implementation lives in follow-up stories.

## Implementation Sketch

Five stories. The first two are foundational to a no-LoRA pipeline and
should land before the additive ones; the last three are the
sketch-driven additions.

1. **Token counter + per-layer OTEL instrumentation + dead-copy
   deletion** (foundational). Add a token counter (CLIP and T5
   tokenizers, run locally — they ship with the renderer). Extend
   `PromptComposer._build_positive()` to return both the composed
   prompt and a `layers: dict[LayerName, int]` token cost map. Emit
   `render.prompt_composed` OTEL span with the layer breakdown plus a
   `budget_remaining` field. Without this, every subsequent story is
   operating blind on token economics.

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
   Walk every shipping genre pack's `positive_suffix`. Measure CLIP
   tokens. Author a `visual_budget.yaml` per genre declaring intended
   costs for GENRE / WORLD / SCENE / NARRATIVE layers. Add a CI check
   that fails if any genre's `positive_suffix` exceeds its budget.
   Brings the new no-LoRA reality to ground truth — every existing
   genre pack was authored under the assumption a LoRA would carry
   half the load. They probably need rewrites.

3. **WORLD cascade level.** Add `worlds/<world>/visual_style.yaml`
   reader. Extend `PromptComposer._build_positive()` to insert
   world-level style tokens between genre `positive_suffix` and
   per-location `visual_tag_overrides`. Update one canary world
   (`mutant_wasteland/flickering_reach`) with a world-level style
   block; verify rendered output shifts. Token budget for WORLD layer
   declared in the canary's `visual_budget.yaml` from story 2.

4. **CAMERA parameter on StageCue.** Add `CameraAngle` enum
   (`DEFAULT`, `TOPDOWN_90`) to `daemon/renderer/models.py`. Thread
   through `StageCue` and `PromptComposer`. Map `CameraAngle.TOPDOWN_90`
   to the existing TACTICAL_SKETCH prefix tokens. Wire `SceneInterpreter`
   to set `TOPDOWN_90` for combat cues. Mark `TACTICAL_SKETCH` tier
   deprecated (keep working).

5. **PC/NPC type wiring + FACTION POI tagging** (paired story —
   small enough to combine). Surface `portrait_manifest.yaml` `type`
   field in the daemon's portrait API. Add `faction: <slug>?` to POI
   entries in `history.yaml`. Both fields are pass-through today — they
   show up in OTEL spans but don't change rendering yet, giving the GM
   panel visibility before the routing logic lands. Defer the
   actual PC pipeline (ADR-034 work) and the actual faction visual
   treatment (open question above) to dedicated follow-ups.

**Order:** (1) and (2) first — without instrumentation and a sober
look at current per-genre token costs, the additive stories are
guesswork. (3) WORLD cascade as the smoke test that the taxonomy is
real. (4) CAMERA. (5) Type/faction wiring last, as the seam for
ADR-034 and a future faction-visuals ADR.

## References

- 2026-04-24 design sketch (slabgorb, hand-drawn — cross-cutting taxonomy)
- 2026-04-23 playtest pingpong file (`~/Projects/sq-playtest-pingpong.md`)
- ADR-032 — Genre-Specific LoRA Style Training
- ADR-034 — Portrait Identity Consistency
- ADR-050 — Image Pacing Throttle
- ADR-070 — MLX Image Renderer
- ADR-071 — Tactical ASCII Grid Maps (proposed) — TOPDOWN_90 use case
- `daemon/media/prompt_composer.py` — current composition mechanism
- `daemon/renderer/models.py` — `RenderTier`, `StageCue`
- `content/genre_packs/*/visual_style.yaml` — genre cascade today
- `content/genre_packs/*/portrait_manifest.yaml` — PC/NPC metadata today
