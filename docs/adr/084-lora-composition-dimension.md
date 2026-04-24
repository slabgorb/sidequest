# ADR-084: Compositional-Dimension Specialization for Style LoRAs

**Status:** **Superseded by ADR-070 (Z-Image / MLX Image Renderer) — 2026-04-24.**

LoRA support is being dropped from the SideQuest visual pipeline. The
compositional-dimension failure mode documented below — "a single-tag
style LoRA trained on a compositionally-biased dataset overrides prompt
adherence at high iterations" — is itself strong evidence that LoRA
training cannot reliably carry style without also dictating composition,
which is exactly the thing we need prompts to control. Rather than
building the per-dimension LoRA specialization framework this ADR
proposed, we are moving style identity fully into prompts and letting
Z-Image's superior text-following carry it.

The `_landscape` / `_portrait` / `_creature` LoRA specialization axis is
not being implemented. Per-render-type style modulation moves to the
category-layered prompt recipes described in ADR-086 (PORTRAIT vs POI
vs ILLUSTRATION each compose their own prefix layers).

**Implications:**
- Multi-dimensional training matrix (genre × composition type)
  cancelled.
- Progress-grid verification framework at `~/lora-runs/` no longer
  load-bearing; can be archived.
- ADR-083 (parent) also superseded.
- ADR-086 inherits the responsibility of keeping composition
  controllable across render types via prompt discipline, not LoRA
  specialization.

The text below is preserved as historical context — the prompt-adherence
failure mode documented here is a useful warning about why LoRA training
was not the right tool for this problem.

---

> **Original status (now obsolete):** Proposed
**Date:** 2026-04-21
**Deciders:** Keith Avery (Bossmang), GM (capturing)
**Related (historical):**
- Extends [ADR-083: Multi-LoRA Stacking and Verification Pipeline](083-multi-lora-stacking-and-verification.md)
- Extends [ADR-032: Genre-Specific LoRA Style Training for Flux Image Generation](032-genre-lora-style-training.md)
- First empirical basis: `~/lora-runs/spaghetti_western/landscape/` (iter 0 → 1500 progress grid, 2026-04-21)

## Context

ADR-083 established genre + world LoRA stacking with pre-promotion and runtime verification, implicitly assuming each genre ships *one* style LoRA that the render pipeline uses uniformly across all render types (portraits, POIs, creatures). ADR-083's own Open Questions section already hints at the axis this ADR formalizes: Phase 3 calibration targets `spaghetti_western_landscape` — the `_landscape` suffix was load-bearing foreshadowing, not incidental naming.

The first real end-to-end training run completed on 2026-04-21: a rank-8 DreamBooth LoRA on ~40 spaghetti_western images captioned with the convention `feedback_style_lora_one_tag.md` prescribes (single trigger tag `spaghetti_western`, identical across the set). Progress images at iter 0, 250, 500, 750, 1000, 1250, and 1500 revealed a failure mode the ADR-083 verification framework does not catch:

**At high iterations, a single-tag style LoRA trained on a compositionally-biased dataset overrides prompt adherence.**

Concretely, with the progress prompt *"spaghetti_western, a wide shot of a sun-bleached desert town at noon"*:

- Iter 250–750: style transfer clearly visible; prompt's `town` subject still renders, compositions diversify (street shots, ridge POVs, mesa backdrops with settlements).
- Iter 1000: 2 of 4 tiles drop the town subject in favor of pure landscape.
- Iter 1500: 4 of 4 tiles are unpopulated landscape plates. The LoRA has fully internalized the dataset's landscape-heavy compositional distribution and the trigger word now pulls toward "landscape" regardless of what else the prompt contains.

**Mechanism.** Single-tag captions (the `feedback_style_lora_one_tag.md` convention) collapse *style*, *subject*, *composition*, and *camera framing* into one trigger. The adapter cannot factor them. At full training strength, the trigger becomes a statistical summary of the training set's entire visual distribution, not just its style register. Prompt text conditioning still reaches the base model, but at sufficient LoRA weight the adapter's compositional bias overwhelms it.

This is not a training defect. Loss plateaued cleanly in the 0.42–0.52 band from iter 500 onward, with no divergence. The issue is structural: a dataset of wide landscapes cannot teach a one-tag LoRA how to render close-up faces, because every training image says *"the thing we are calling `spaghetti_western` looks like this wide landscape."*

Two paths were considered to fix prompt adherence within a single LoRA, and both are rejected under *Alternatives considered* below. The accepted path is to embrace the specialization: train one LoRA per compositional mode and let the render pipeline pick the right one at call time.

## Decision

**Style LoRAs specialize by composition, orthogonal to genre and world.** Introduce a third stacking dimension — `composition` — joining `genre` and `world` from ADR-083.

### The composition dimensions (initial set)

| Dimension | Purpose | Render scripts that consume it |
|---|---|---|
| `landscape` | Wide shots, POI environments, establishing shots, world maps | `scripts/render_poi.py`, `scripts/render_world_map.py` |
| `portrait` | Character close-ups and medium character shots | `scripts/render_portrait.py` |
| `creature` | Creature-centric framings where the creature fills the frame | `scripts/render_creature.py` (see Open Questions) |

The set is deliberately narrow. It maps 1:1 onto the existing render scripts. No `interior`, `action`, or `mood` slots are introduced yet — those remain prompt-engineering concerns until an actual script needs them.

### Storage convention

At the genre level, LoRAs live as siblings keyed by composition:

```
sidequest-content/lora/{genre}/
├── landscape.safetensors
├── portrait.safetensors
└── creature.safetensors    # optional
```

World-level overrides continue to use ADR-083's `exclude` + `add` semantics, with composition carried through as an additional field on each entry.

### Selection at render time

Each render script knows its own composition dimension as a literal constant. The daemon's `compose_lora_stack` resolver, introduced in Phase 4.3 of the plan, gains a `composition:` parameter that filters the stack to entries whose `applies_to` list includes that composition (or is `all`).

This means: the renderer chooses; the caller does not. A portrait script never has to know that `spaghetti_western/portrait.safetensors` exists — it asks for "the LoRA stack for genre=spaghetti_western, world=dust_and_lead, composition=portrait," and the resolver returns the right files.

### Dataset curation guideline

For each composition dimension, training datasets should be compositionally *pure*, not compositionally balanced. A `landscape` LoRA is trained entirely on landscapes. A `portrait` LoRA is trained entirely on faces and medium character shots. The goal is not a LoRA that can do everything — it's a LoRA that does exactly one thing very well, and the pipeline stacks them.

---

## Alternatives considered

| Option | Why rejected |
|---|---|
| **Balance the training set compositionally** (equal counts of landscape, portrait, interior, etc.) within a single LoRA per genre. | Requires 3–4× dataset curation cost per genre, still produces a LoRA that is "average" at everything rather than specialized at anything, and does not solve the single-tag caption ambiguity. The adapter still cannot factor *style* from *composition* without descriptive captions. |
| **Switch to descriptive multi-word captions per image** (e.g., `spaghetti_western, a dusty town street` / `spaghetti_western, a lone rider on a ridge`) to preserve prompt adherence inside one LoRA. | Directly contradicts `feedback_style_lora_one_tag.md`, which is a project-level convention preventing caption-noise-driven style pollution. More importantly: caption authorship is brittle, especially for found-footage film stills where "what is in this frame" is subjective. One-tag-per-style-LoRA is the foolproof baseline; multi-word captions trade that for a potentially better but manually-calibrated result. |
| **Train one LoRA per (genre × world × composition)** from day one (full specialization, no inheritance). | Combinatorial explosion: 7 genres × N worlds × 3 compositions = dozens of training runs before shipping one playable. ADR-083's inheritance model (genre base + world overrides) was chosen specifically to avoid this, and the same reasoning applies here: inherit the composition specialization from the genre, override per world only when the world's visual register truly diverges. |
| **Prompt-engineering-only solution: always append "[composition-type]" to the prompt.** | The failure mode at iter 1500 is that *the LoRA overrides prompt conditioning at the compositional layer.* No amount of additional prompt tokens rescues this — the adapter has learned to ignore them. Empirically observed in the iter 1500 progress grid: the prompt contains "wide shot of a desert town" and the LoRA still renders empty landscapes. |
| **Train shorter.** Stop at iter 500–750 where prompt adherence is still intact. | Works for *some* renders but leaves style transfer weaker than it can be. Also does not generalize — future datasets may reach the compositional-override regime at different iteration counts depending on set size, LR schedule, and rank. We would be chasing a moving target instead of addressing the structural cause. |

**Why specialization wins:** each LoRA becomes a narrow, high-confidence artifact whose training-set composition *is* its operational composition — no bias mismatch between training and inference. Dataset curation simplifies (narrower, more consistent sets). The render pipeline already knows its composition dimension (each script is purpose-built), so no new lookup logic is needed. This is how the mature Flux and Stable Diffusion community composes LoRAs in practice.

---

## Consequences

### Positive

- **Failure mode becomes a feature.** The current spaghetti_western run — which we initially diagnosed as "the LoRA broke prompt adherence" — is instead the first shipped `spaghetti_western/landscape.safetensors`. Zero extra work; the "problem" resolved into the architecture.
- **Dataset curation scope shrinks per artifact.** Authoring a 40–80 image pure-landscape set is tractable. Authoring a balanced 150-image set that covers landscape + portrait + interior + action evenly is substantially harder and more error-prone.
- **Matches the render pipeline's existing topology.** The renderer scripts are already separated (`render_portrait.py`, `render_poi.py`, `render_creature.py`). Each script naturally "wants" a different LoRA. The composition dimension aligns the storage layout with the runtime request pattern.
- **Opens per-genre tuning.** Different genres may split differently. `spaghetti_western` obviously splits (Leone closeups vs. Leone landscapes). `neon_dystopia` probably splits (cyberpunk face lighting is radically different from cityscape LoRA). `elemental_harmony` may not need to split (style is consistent across composition). The dimension is available per-genre, used or not as curation dictates.
- **Per-composition verification.** ADR-083's Layer A gate (SSIM verify) can calibrate its trigger/control prompts *per composition*, producing sharper signal. A landscape LoRA's trigger check uses a landscape control; a portrait LoRA's uses a portrait control. Cross-composition false-positives disappear.

### Negative

- **Training cost scales with the split.** A genre that ships landscape + portrait doubles its training compute. For a solo developer on an M3 Max, this matters — each full run is ~2 hours. Mitigated by: (a) not every genre needs the split, (b) training can run overnight, (c) specialization makes each individual run more effective, so quality-per-hour may actually improve.
- **Storage footprint grows.** At 146 MB per adapter (rank 8), each added composition per genre is +146 MB on disk. Content repo already gitignores `sidequest-content/lora/` locally, but long-term storage cost (backup, R2 sync) scales. Non-critical at project size.
- **Authoring complexity grows slightly.** World authors must know which composition their world's overrides target. `visual_style.yaml` grows a `composition:` field on LoRA entries. Mitigated by sensible defaults (entries without `composition:` apply to all).
- **Possible composition gap at render time.** If a genre has `landscape.safetensors` but no `portrait.safetensors`, what does the portrait renderer do? Options: fall back to landscape LoRA (against no-silent-fallback rule), render with no LoRA (defeats the purpose), or hard-fail. The no-silent-fallback rule dictates hard-fail, with a clear error message directing the operator to train the missing composition. Sketched in *Open Questions*.

### Neutral

- **ADR-083 inheritance model is preserved unchanged.** Composition slots into the existing `loras:` schema as another filter dimension alongside `applies_to` tier. The extend + exclude + add merge semantics work identically per composition.
- **SOUL principles untouched.** Gameplay layer unaffected; this is image-substrate infrastructure.
- **`feedback_style_lora_one_tag.md` convention is preserved and strengthened.** One tag per image remains the rule; the composition dimension is how we get subject flexibility *without* violating that rule.

---

## Out of Scope

- **Dynamic composition detection from narration.** The narrator is not asked "what composition does this scene want?" — the render script's identity is the composition signal. A scene that narratively calls for a close-up is already routed to the portrait renderer by upstream code; the LoRA just follows the route.
- **Mixing compositions within a single render.** No stacking `landscape` + `portrait` on the same render; each render picks one. If a future scene demands "character in a landscape," that's a composition question to be named and designed, not an ad-hoc stack.
- **Character-identity LoRAs.** Still deferred per ADR-083. Character LoRAs, if ever shipped, are a fourth dimension orthogonal to composition (a specific character rendered in landscape, portrait, or creature framing).
- **Per-world composition authoring.** Worlds can override existing genre compositions via ADR-083's `exclude`+`add`. Worlds cannot introduce *new composition dimensions* (e.g., a `victoria/domestic_interior` composition). Keeping the composition set fixed at the project level preserves a narrow, legible render topology.

## Open Questions

- **Does `creature` warrant its own LoRA, or does the landscape LoRA with prompt engineering suffice?** Creature renders are often "creature embedded in environment." The landscape LoRA already handles the environment. If creature-as-subject doesn't get its own compositional register in the training data, a dedicated creature LoRA may be over-engineering. Proposal: defer creature LoRAs until after landscape + portrait are in production for two genres; evaluate empirically whether creature renders under the landscape LoRA feel genre-true.
- **Missing-composition failure policy.** When a genre has `landscape.safetensors` but a portrait render is requested, what happens? Proposed: hard-fail with a clear error message naming the missing composition and the genre, matching the no-silent-fallback rule. Worth confirming.
- **Composition-aware SSIM calibration.** ADR-083's Layer A gate uses fixed SSIM thresholds. Portrait LoRAs may have different sensitivity (faces are structurally constrained in a way landscapes are not). Calibration may need per-composition overrides. Defer until empirical data from the second LoRA.
- **Genre-pack audit for the dimension.** Before investing in portrait training for every genre, audit which genres visually *benefit* from the split. Initial triage: `spaghetti_western`, `neon_dystopia`, `pulp_noir`, `mutant_wasteland`, `road_warrior` probably split well; `elemental_harmony`, `low_fantasy` may not. Part of genre-pack authoring, not this ADR.
- **Naming for the composition field in `visual_style.yaml`.** Current candidates: `composition:`, `applies_to:` (overloading the ADR-083 tier field), or a dedicated `render_types:`. Design detail, not a decision here.

## Supersedes / Is Superseded By

- **Extends:** ADR-083 (multi-LoRA stacking) — the composition dimension is added to the stacking model; inheritance semantics are unchanged.
- **Extends:** ADR-032 (genre LoRA style training) — adds composition specialization to the training-to-inference contract.
- **Superseded by:** none.
