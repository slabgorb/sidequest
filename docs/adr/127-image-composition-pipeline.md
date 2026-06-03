---
id: 127
title: "Image Prompt-Composition Pipeline — Catalog Recipes, Token-Budget Eviction Ladder, and SceneInterpreter Rule Cascade"
status: accepted
date: 2026-05-31
deciders: ["Keith Avery", "Neo (Architect)"]
supersedes: []
superseded-by: null
related: [50, 70, 86]
tags: [media-audio]
implementation-status: live
implementation-pointer: null
---

# ADR-127: Image Prompt-Composition Pipeline

> **Documents a system already live in code.** The recipe loader, the catalog-
> driven `PromptComposer` with its 512-token two-phase eviction ladder, and the
> `SceneInterpreter` rule cascade all shipped incrementally across the 2026-04
> explicit-visual-recipes work (`docs/superpowers/specs/2026-04-24-explicit-visual-recipes-design.md`)
> and the 2026-04→2026-05 playtest fixes, under the umbrella of ADR-086's
> taxonomy but without a record stating the *runtime contract*. ADR-086 named
> the slots and the eviction *order*; it explicitly deferred the recipe-class
> refactor and described identity-floor / camera / culture as a design sketch.
> What actually shipped is a concrete loader validation contract, a hard
> `BudgetError` floor, a world-over-genre non-blend rule, and a priority-ordered
> scene-classification cascade — none of which ADR-086 specified at the level of
> behavior. This record closes that architecture-of-record gap and states what
> the decision *was*.

## Context

ADR-086 (Image-Composition Taxonomy) established the **organizing mental model**:
three render kinds (portrait / POI / illustration), a cascade of named style
slots (GENRE → WORLD → CULTURE → SCENE), a switchable camera, and a
budget-driven eviction order under T5's 512-token ceiling. Critically, ADR-086
*deferred* the structural realization of that model: §"What this ADR does NOT
decide" explicitly punted the recipe-class refactor (promoting the flat
`_TIER_PROMPT_PREFIX` dict to named layers), and its eviction order was a
priority *table*, not a runtime procedure with a hard floor.

Between then and now, the daemon's `media/` package grew the actual machinery —
and grew it under playtest pressure, accreting several load-bearing fixes that
were never written down as architecture:

- A **YAML recipe catalog** (`recipes.yaml`) that names a source binding per
  slot per kind, loaded and validated at daemon startup.
- A **token-budget enforcer** in `PromptComposer` that does two-phase eviction
  (participant level-of-detail downgrade, then slot truncation) and raises
  rather than silently degrading identity.
- A **rules-based scene classifier** (`SceneInterpreter`) that turns narrator
  prose into `StageCue` objects via a priority-ordered pattern cascade, with an
  LLM `SubjectExtractor` fallback and a location-cooldown dedup.

Three regressions during 2026-04/05 playtesting are the reason the *behavioral*
contract (not just the slot taxonomy) must be recorded:

1. **grimvault styleless render (2026-04-26)** — the WORLD style layer was
   silently empty (a `style_prompt` vs `positive_suffix` key mismatch). Without
   an explicit "world style applied?" signal, the GM panel could not tell a
   styled render from a styleless one. This is what motivated the
   `world_style_applied` lie-detector flag on the OTEL span.
2. **landscape COMPOSE_FAILED / empty participants (2026-04-30)** — narrator-
   emitted environmental scenes (`tier=landscape`, prose subject, no registered
   POI) had no kind to route to; routed to `illustration` with empty
   `participants`, the LOD planner crashed on `participants[0]`. 2 of 2 landscape
   dispatches in a 4P MP playtest silently failed (socket closed on
   `IndexError`, server logged `render.reply_unavailable`).
3. **spaghetti_western double-image (2026-05-25)** — blending the genre style on
   top of the world style stacked the genre's "extreme close-up on weathered
   face" grammar onto POI landscapes, hallucinating a face into landscapes.

Each fix hardened a contract. This ADR states those contracts as decisions.

## Decision

**The narrative-turn → image-prompt path is a three-stage pipeline: a
catalog-driven recipe model, a budget-bounded composer with a two-phase eviction
ladder and an inviolable identity floor, and a priority-ordered SceneInterpreter
rule cascade. Each stage fails loud and emits OTEL.** This realizes ADR-086's
taxonomy as concrete runtime behavior; it does not change the mental model, it
states the contract the model runs under.

### 1. Recipe / slot model

Source of truth: `sidequest-daemon/recipes.yaml`,
`sidequest_daemon/media/recipes.py`, `recipe_loader.py`, `cameras.yaml`,
`camera_specs.py`.

- **Three render kinds** — `portrait` / `poi` / `illustration`, the `kind`
  literal on both `Recipe` and `RenderTarget` (`recipes.py`, `:158`). One
  composable `RenderTarget` type serves all three; a `@model_validator`
  (`recipes.py`) enforces per-kind shape (portrait requires `character`
  and forbids place/participants/action; poi requires a `where:` `place` whose
  scope matches `world`; illustration requires `action` + `camera` but treats
  `participants` and `location` as optional).
- **Five named slots** — `Slot` enum (`recipes.py`): `CASTING`,
  `LOCATION`, `DIRECTION_ACTION`, `DIRECTION_CAMERA`, `ART_SENSIBILITY`. Each of
  the three recipes in `recipes.yaml` names a source binding per slot (e.g.
  portrait: `casting: character`, `location: background`,
  `direction_action: pose`, `direction_camera: portrait_3q`,
  `art_sensibility: [GENRE, WORLD, CULTURE]`).
- **Camera presets** — `CameraPreset` (`recipes.py`) enumerates 17
  stills-only framings across portrait / POI / illustration / signature
  categories. A recipe binds a fixed preset by name *or* the dynamic marker
  `"{camera}"` (`recipe_loader.py`), which pulls the preset from
  `RenderTarget.camera` at compose time (`prompt_composer.py`). Presets
  carry their prompt tokens (and optional `post` crop/rotate directive) in
  `cameras.yaml`, loaded by `CameraLoader`.
- **Character / place LOD** — `LOD` (solo/long/short/background) and `PlaceLOD`
  (solo/backdrop) (`recipes.py`) select which authored detail tier a
  catalog entry contributes; this is the substrate the eviction ladder operates
  on.

### 2. The eviction ladder (`PromptComposer.compose`, `prompt_composer.py`)

A 512-token ceiling (`_TOKEN_LIMIT`, `:44`; `_estimate_tokens` ≈ 1.3 tokens/word,
`:53`) is enforced in **two phases**, in this order:

- **Phase 1 — participant LOD downgrade** (`:108-113`,
  `_downgrade_one_participant` `:204-215`). While over budget, downgrade the
  *lowest-priority* participant one LOD rung along `_LOD_ORDER`
  (solo→long→short→background). Downgrades proceed in **reverse participant
  order** so tail participants degrade first — this **preserves the presence of
  every participant** rather than dropping anyone (honors ADR-014 / Diamonds and
  Coal: detail tracks relevance, nobody is deleted). Stops when every
  participant is already at `background`.
- **Phase 2 — slot-level eviction** (`:115-121`, `_apply_slot_eviction`
  `:260-294`). If still over budget, walk `_EVICTION_ORDER` (`:69-74`):
  `LOCATION.flourish` (preserve 8 tok) → `DIRECTION_ACTION.flourish` (8) →
  `ART_SENSIBILITY.CULTURE.flourish` (12). `*.flourish` labels **truncate** the
  matching slot down to the preserve count; a bare label drops the slot
  entirely. Each truncation/drop is recorded in `dropped_layers`.

If still over budget after both phases, the composer **raises `BudgetError`**
(`:123-127`, `recipes.py`) with a per-slot breakdown — it never silently
ships a truncated identity. See Invariants.

### 3. The SceneInterpreter rule cascade (`scene_interpreter.py`)

`SceneInterpreter.interpret` (`:372-569`) turns narrator prose + `GameState`
into up to `_MAX_CUES = 2` (`:25`) `StageCue` objects:

- **Pre-gates:** empty narrative → no cues (`:384`); template-var substitution
  (`:388`); `_is_dialogue_only` → no cues (`:390`, pure quoted speech is not
  visual); per-turn location-cooldown decrement (`:395`).
- **LLM-first, regex-fallback:** if a `SubjectExtractor` is wired, run it
  (`:411-412`, `_run_extractor` `:342-358` bridges async→sync and **falls back to
  regex on any failure**, logging a warning — not a silent skip). A successful
  extraction that parses to a valid `RenderTier` and does not look like dialogue
  short-circuits to a single LLM cue (`:417-445`).
- **Priority-ordered rule cascade** (regex patterns, `:30-100`), each appending a
  cue: Rule 0 document/notice → `TEXT_OVERLAY` (`:450`); Rule 1 location change →
  `LANDSCAPE` (`:460`); Rule 2 combat → `SCENE_ILLUSTRATION` with
  `CameraPreset.topdown_90` (`:474`, the ADR-086 tactical-map path); Rule 3
  character introduction → `PORTRAIT`, **skipped when combat already fired**
  (`:487`); Rule 4 magic/special-effects → tagged `SCENE_ILLUSTRATION` (`:497`);
  Rule 5 atmosphere → `SCENE_ILLUSTRATION` only if no scene cue already exists
  (`:515`). A `_distill_visual` fallback cue fires if nothing matched (`:529`).
- **`_distill_visual` chain** (`:193-201`): strip mechanics → strip dialogue →
  strip abstractions → drop apostrophes → collapse whitespace, so render prompts
  carry concrete visual content, not HP notation, quoted speech, or
  "sense-of-dread" abstractions.
- **Location cooldown / dedup** (`:540-567`): a `LANDSCAPE` cue for a location
  within `_SIMILARITY_THRESHOLD = 0.4` (Jaccard over word tokens) of the
  last-rendered location is suppressed while the cooldown counter
  (`location_cooldown_turns`, default 2) is hot — preventing a re-render of the
  same place every turn.

## Invariants / Contracts

- **Startup fail-loud recipe/camera validation.** `RecipeLoader.from_dict`
  (`recipe_loader.py`) rejects an unknown camera preset (unless the dynamic
  `"{camera}"` marker) and any `art_sensibility` cascade layer outside
  `_ALLOWED_CASCADE_LAYERS = {GENRE, WORLD, CULTURE}` (`:12`), raising
  `ValueError`. `CameraLoader.from_dict` (`camera_specs.py`) raises if
  `cameras.yaml` is **missing any** known preset or contains an **unknown** one.
  Misconfiguration surfaces at daemon load, never at render time — honoring *No
  Silent Fallbacks*.
- **Identity floor → `BudgetError`, never silent degradation.** `_IDENTITY_FLOOR`
  (`prompt_composer.py`) = `{CASTING, DIRECTION_CAMERA,
  ART_SENSIBILITY.GENRE, ART_SENSIBILITY.WORLD}`. None of these appear in
  `_EVICTION_ORDER`; if eviction cannot bring the prompt under 512 tokens without
  touching them, the composer raises `BudgetError` (`:123-127`). Notably
  **`ART_SENSIBILITY.WORLD` is in the floor, not evictable** — evicting WORLD
  produces photoreal CG with no painterly styling, so a genuine over-budget
  surfaces as a real error rather than a styleless render (`:60-68` comment).
- **World-over-genre, non-blending.** `_resolve_art_sensibility`
  (`:494-550`): when a world ships its own style (`StyleCatalog.get_world`
  returns non-empty), the world layer **fully replaces** the genre layer — the
  GENRE branch `continue`s and emits nothing (`:514-518`). The genre layer is
  emitted **only as a fallback** for a world with no style of its own. This is
  the direct fix for the 2026-05-25 spaghetti_western double-image (genre's
  "weathered face" grammar was bleeding into POI landscapes when the two layers
  blended). World suffixes must therefore be self-complete. The 2026-04-29
  visual-style decomposition already moved the art-movement lineage to the world
  layer; override makes that authoritative.
- **`world_style_applied` is the load-bearing health flag.** The
  `render.prompt_composed` OTEL span (`:164-191`) carries `genre_style_applied`
  and `world_style_applied` lie-detector flags (`:145-152`), the per-layer token
  breakdown, `dropped_layers`, `warnings`, and the Z-Image `model_variant` /
  `steps` / `fidelity`. Under normal override, `world_style_applied` MUST be true
  and `genre_style_applied` is intentionally false. This is a Keith/dev panel
  signal (per the OTEL principle), not a player surface.
- **Empty participants is a legitimate state.** `_character_lod_plan`
  (`:296-340`) returns an empty plan for an illustration with zero participants
  (environmental landscape with prose subject), so `_resolve_casting` produces
  zero CASTING layers and composition continues — the 2026-04-30 fix for the
  silent landscape `IndexError`. A non-`where:` `location` ref is a contract
  violation that surfaces as a structured `COMPOSE_FAILED` from `PlaceCatalog`,
  never a silent drop (`:413-447` comment).
- **SceneInterpreter rule priority + server-visual-block primacy.** Rules fire in
  fixed priority order (document → location → combat → portrait → atmosphere);
  combat suppresses the portrait rule (`:487`). The LLM extractor is tried first
  but **falls back to regex on any failure** (`:356-358`), and a server-supplied
  visual block (the LLM `tier`/`subject` result) beats rule classification when
  present and valid (`:417-445`) — the 2026-04-30 COMPOSE_FAILED guard ensuring
  an explicit visual directive isn't overridden by pattern matching. Cues are
  capped at `_MAX_CUES = 2`.

## Consequences

**Positive**

- The render path is **fail-loud end-to-end**: bad recipe/camera config dies at
  load; an un-fittable prompt raises `BudgetError`; a non-catalog location ref
  raises `COMPOSE_FAILED`. No render silently degrades into a styleless or
  identity-less image.
- The eviction ladder makes ADR-086's eviction *table* an executable procedure
  with a hard floor, and the LOD-downgrade phase keeps every participant present
  (Diamonds-and-Coal: degrade detail, never delete the cast).
- World-over-genre non-blend gives authors a clean override seam — a world's
  visual_style fully owns its look, matching the "Flavor in the World" doctrine
  (genre tier is mechanics; worlds carry visual flavor).
- The `world_style_applied` / per-layer OTEL span lets the GM panel catch a
  styleless render — the lie detector for the composer subsystem.

**Negative / cost**

- The 512-token math is an **estimate** (`_estimate_tokens` words×1.3), not the
  real T5 tokenizer — it can diverge from the worker's actual token count. In
  practice shipping prompts run well under the ceiling (ADR-086 §Token Budget),
  so the estimate is a guardrail, not a precise gate.
- `BudgetError` is a hard failure: a genuinely over-stuffed identity floor (many
  participants whose CASTING tokens alone exceed budget, plus genre+world style)
  produces no image at all rather than a degraded one. This is by design (better
  no image than a wrong-identity image) but is a sharp edge for authors who write
  verbose CASTING tokens.
- The SceneInterpreter cascade is **regex-pattern-driven** and genre-agnostic by
  construction; it can misclassify unusual prose. The LLM extractor mitigates
  this when wired, but the regex fallback is the floor and is inherently
  approximate.

## Alternatives considered

- **Keep ADR-086's flat `_TIER_PROMPT_PREFIX` dict + arbitrary mid-string
  truncation.** Rejected: ADR-086 itself flagged silent T5 truncation as the
  failure mode to avoid; the named-slot eviction ladder drops whole low-priority
  flourishes in defined order instead of cutting a prompt mid-token.
- **Silent style fallback when over budget (evict WORLD, render genre-only).**
  Rejected: produces a styleless render that looks "fine" but is wrong, and is
  invisible without a signal — exactly the grimvault failure mode. WORLD stays in
  the identity floor; over-budget raises `BudgetError`.
- **Blend genre + world style layers (stack both).** Rejected: caused the
  spaghetti_western double-image (genre face-grammar hallucinated into
  landscapes). World overrides genre; it does not blend.
- **Drop tail participants when over budget.** Rejected in favor of LOD
  downgrade: every named participant stays in frame (presence preserved), detail
  degrades instead — the Diamonds-and-Coal contract.
- **Pure-LLM scene classification (no regex cascade).** Rejected as the floor:
  the extractor is opt-in and can fail or be unavailable; the regex cascade is
  the always-available fallback, and the LLM result wins only when it is present
  and valid.

## Reconciliation with ADR-050, ADR-070, ADR-086

- **ADR-086 (Image-Composition Taxonomy):** **extended, not superseded.** ADR-086
  owns the *mental model* — the three kinds, the named cascade slots, the eviction
  *order table*, the camera unification (TOPDOWN_90 as a camera of illustration),
  and the CULTURE cross-category layer. This ADR records the *runtime contract*
  ADR-086 deferred: the loader validation rules, the two-phase eviction procedure,
  the hard `BudgetError` identity floor, the world-over-genre non-blend, and the
  SceneInterpreter rule-priority cascade. ADR-086's §"What this ADR does NOT
  decide" deferred the recipe-class refactor; the recipe catalog shipped, so this
  ADR is its record of decision. Where ADR-086's prose sketch and the daemon code
  disagree, **the code is authoritative** (ADR-086's own 2026-05-02 status note
  says as much).
- **ADR-070 (MLX Image Renderer):** the composer targets the Z-Image worker
  exclusively (`_select_worker` returns `"zimage"`, `:619-622`) and reports the
  Z-Image `model_variant` / `steps` per `fidelity` on its span (`:160-189`). This
  pipeline produces the prompt; ADR-070's MLX worker consumes it. The composer
  reports the *requested* tier; the worker emits its own span with the variant
  actually loaded, so a divergence is itself diagnostic.
- **ADR-050 (Image Pacing Throttle):** orthogonal and upstream. The throttle
  decides *whether / when* a render fires; this pipeline decides *what prompt* a
  fired render carries. `SceneInterpreter`'s location cooldown
  (`_location_cooldown_turns`, dedup of repeat-location LANDSCAPE cues) is a
  cue-level dedup distinct from ADR-050's render-rate throttle — the two compose:
  the interpreter suppresses redundant *cues*, the throttle paces *renders*.
