# ADR-083: Multi-LoRA Stacking and Verification Pipeline

**Status:** **Superseded by ADR-070 (Z-Image / MLX Image Renderer) — 2026-04-24.**

LoRA support is being dropped from the SideQuest visual pipeline.
Z-Image follows text-prompt art direction substantially better than
LoRA-trained variants achieved in practice — and the silent-failure modes
documented below (mflux loading incompatible LoRAs without warning,
training-toolchain incompatibility, multi-LoRA stack drift) made the
LoRA pipeline a perpetual debugging tax.

The multi-LoRA stacking, verification framework, and `lora_triggers` /
`explicit_exclude` semantics described below are not being implemented.
World-vs-genre style differentiation moves to the prompt cascade
described in ADR-086 (GENRE → WORLD → SCENE text layers, with explicit
token budgets per layer).

**Implications:**
- Stacking framework, verification gates, and per-format adapter logic
  cancelled. The "mflux silently accepts incompatible LoRAs" failure
  mode is moot once we stop loading LoRAs.
- ADR-084 (Compositional-Dimension Specialization) — also superseded;
  it extends this ADR.
- ADR-086 carries the prompt-precision burden that this ADR's stacking
  framework was meant to address (per-world style differentiation,
  per-render-type style modulation).

The text below is preserved as historical context — particularly the
mflux silent-failure analysis, which documents real engineering tax
spent and warns future contributors away from re-introducing the
approach.

---

> **Original status (now obsolete):** Proposed
**Date:** 2026-04-20
**Deciders:** Keith Avery (Bossmang), Margaret Houlihan (Architect)
**Related (historical):**
- Extends [ADR-032: Genre-Specific LoRA Style Training for Flux Image Generation](032-genre-lora-style-training.md)
- Depends on [ADR-070: MLX Image Renderer](070-mlx-image-renderer.md)
- Spec: `docs/superpowers/specs/2026-04-20-lora-pipeline-design.md`
- Plan: `docs/superpowers/plans/2026-04-20-lora-pipeline.md`

## Context

ADR-032 established that each genre would ship a style LoRA trained externally and wired into `visual_style.yaml` via a single `lora:` + `lora_scale:` field pair. That ADR is marked Accepted; the training pipeline is operational; the daemon can load a LoRA. What ADR-032 did **not** anticipate:

1. **Worlds within a genre diverge.** `spaghetti_western` contains both `dust_and_lead` (Leone/Almería 1860s desert) and `the_real_mccoy` (1878 Pittsburgh industrial). A single genre LoRA cannot serve both — the Almería aesthetic actively *fights* the Pittsburgh one. The content team anticipated this in `the_real_mccoy/visual_style.yaml`'s prospective `lora_triggers:` block with an `explicit_exclude` list, but no runtime supports those semantics.

2. **mflux silently accepts LoRAs it cannot understand.** On 2026-04-20, `Flux1(lora_paths=[draw_things_trained.ckpt])` loaded the file without error and produced **pixel-identical output** to running with no LoRA at all. mflux's internal key-matching registry recognized zero keys from the Draw Things-format file, silently applied zero-weight adapters, and reported success. This is a project-level "no silent fallbacks" rule violation inside a third-party library; we lack the tooling to detect it pre-promotion.

3. **The training toolchain choice has runtime consequences.** Draw Things produces s4nnc `.ckpt`; Kohya / ai-toolkit produce Kohya-named `.safetensors`; mlx-examples produces MLX-native `.npz`. Each of the three is differently incompatible with mflux. The training-tool decision propagates all the way to runtime.

4. **Verification lives at multiple temporal boundaries.** Training-time verification (did the trainer converge?) is different from pre-promotion verification (does the artifact work at inference?) which is different from runtime verification (is this render actually using the LoRA it claims?). No single check covers all three.

## Decision

Adopt a four-part architectural stance, formalized in the spec and operationalized by the plan:

1. **Use `mlx-examples/flux/` as the sole supported trainer, with a mandatory key-remapper in the pipeline.**
2. **Replace single-LoRA config with hybrid genre + world stacking** using extend + `exclude` + `add` merge semantics.
3. **Introduce an SSIM-based pre-promotion verification gate** and a runtime OTEL `matched_key_count` attribute on the existing `flux_mlx.render` span.
4. **Widen the daemon render protocol from singleton `lora_path` / `lora_scale` to `lora_paths[]` / `lora_scales[]`.**

Each decision is analyzed in its own subsection below.

---

### Decision 1 — MLX-native training + custom remapper

**Decision:** Train with `mlx-examples/flux/`. Convert its `.npz` output to Kohya-named `.safetensors` via a versioned, in-repo key-remapper (`scripts/lora/remap_mlx_to_mflux.py` + `scripts/lora/mlx_to_mflux_keymap.yaml`) before the LoRA reaches the shipped path.

**Alternatives considered:**

| Option | Why rejected |
|---|---|
| Continue using Draw Things | Produces s4nnc `.ckpt` format; mflux silently ignores it entirely (empirically confirmed 2026-04-20). Draw Things has a gRPC server mode that *could* be used as a parallel render backend, but that creates a two-backend architecture that complicates every downstream subsystem. |
| Kohya-ss `sd-scripts` | Battle-tested, Kohya-named `.safetensors` natively consumable by mflux. **Rejected** because (a) slower than MLX on M3 Max, (b) PyTorch+MPS venv is a heavier dependency than the mlx-examples single-tool venv, (c) Keith's training time isn't constrained (overnight runs), so the speed argument for Kohya doesn't win on the one axis it would. |
| ai-toolkit | Produces fused-QKV rank-96 adapters that mflux cannot load (matmul shape error, also empirically confirmed). Adding unfuse logic to the remapper is possible but puts a much more complex transformation in the mandatory pipeline stage. |
| Stay with Draw Things and write a converter | No public converter from Draw Things s4nnc exists (perplexity-confirmed). We'd be building the same remapper anyway, against a more opaque source format. |

**Why MLX-native wins:** output matches the inference backend's hardware path, the conversion distance to mflux is short (key-rename + optional transpose, no structural surgery), and the alternative with the same compatibility guarantees (Kohya) is slower without compensating benefit. The remapper is owned in-repo with a versioned keymap YAML, so mlx-examples schema changes are absorbed as a single-file diff rather than a toolchain replacement.

**Load-bearing constraint:** `mflux>=0.4,<0.5` pin required. The remapper produces Kohya-named keys; the worker's `matched_key_count` extraction depends on `FluxLoRAMapping.get_mapping()`. Both are stable within a minor version but not guaranteed across them.

---

### Decision 2 — Hybrid genre + world stacking with extend + exclude + add

**Decision:** `visual_style.yaml` grows a `loras:` section with two forms:

- **Genre level:** flat list of LoRA entries (`name`, `file`, `scale`, `applies_to`, `trigger`).
- **World level:** dict with optional `exclude: [name, ...]` and `add: [entry, ...]`. Omitted entirely in the common case (inherit genre unchanged).

Daemon composes the effective stack per render: genre base → remove excluded → append added → filter by tier via `applies_to`. Stack is passed to mflux as `lora_paths[]` / `lora_scales[]`.

**Alternatives considered:**

| Option | Why rejected |
|---|---|
| Genre-level only (one LoRA per genre, all worlds share) | Fails `spaghetti_western` immediately — one LoRA cannot serve both Almería desert and Pittsburgh industrial. Forces visual-divergent worlds to abandon LoRAs entirely and compete for CLIP tokens via `positive_suffix` text alone — the exact problem ADR-032 was written to escape. |
| World-level only (each world trains its own) | Dataset authorship and training cost scale with world count. Most worlds within a genre share enough aesthetic to justify a shared base LoRA. "World-only" forces redundant training. |
| Full `replace`-on-set semantics (world's `loras:` replaces genre's if present) | Every world with `loras:` must re-declare the genre entries it wants to keep. Copy-paste invites drift between genre and world YAMLs. The `the_real_mccoy` use case (keep nothing from genre) is handled identically by exclude-all, so `replace` buys nothing. |
| Explicit per-world `merge: extend | replace` mode | Gratuitous verbosity for zero additional expressiveness; `exclude + add` is the superset of `replace` (just exclude everything). |

**Why extend+exclude+add wins:** matches `the_real_mccoy`'s pre-existing design intent, zero-config for the common case (world inherits genre), explicit in the divergent case (`exclude:` names exactly what's being dropped), and composes cleanly with the `applies_to` tier filter without special-casing.

---

### Decision 3 — SSIM pre-promotion gate + runtime `matched_key_count`

**Decision:** Two-layer verification.

**Layer A (pre-promotion, offline).** `scripts/lora/verify.py` runs four checks before any LoRA is copied from `archive/` to the shipped genre directory:
1. Static key-match (mflux must recognize ≥80% of file keys, 0% is an automatic hard-fail)
2. SSIM between (LoRA, baseline) renders < 0.999 threshold (catches silent-fallback)
3. SSIM between (trigger, control) renders < 0.97 (trigger word actually learned)
4. Human sign-off on the visual report

**Layer B (runtime, per-render).** The existing `flux_mlx.render` OTEL span gains attributes: `render.lora.stack_size`, `render.lora.files[]`, `render.lora.scales[]`, `render.lora.matched_keys[]`. If any `matched_keys[]` entry is zero, span status is set to `ERROR` with an explicit silent-fallback message. GM panel surfaces this as a red badge per render.

**Alternatives considered:**

| Option | Why rejected |
|---|---|
| Manual eyeball only | This is what we had on 2026-04-20. It failed. Hours were spent debugging a LoRA that was silently a no-op. Not repeatable as a quality floor. |
| SSIM only, no runtime check | Gate prevents bad LoRAs from being promoted, but a correctly-verified file that gets replaced/corrupted in place produces zero runtime signal. Runtime check is cheap (one `safetensors` read per file per model rebuild) and covers the "verification drift" case. |
| Runtime check only, no pre-promotion gate | Runtime check is a tripwire, not a gate — it tells you the LoRA failed AFTER you rendered with it. Pre-promotion gate keeps known-broken files out of the shipped directory in the first place. |
| Separate OTEL span `render.lora` | **Rejected during review (originally in the spec, corrected).** The existing worker namespace is `flux_mlx.*`; adding a new top-level `render.*` namespace breaks the pattern and doubles span emission per render. Attaching LoRA data as attributes on the existing `flux_mlx.render` span preserves one-span-per-render and namespace consistency. |

**Why two-layer wins:** the failure modes are orthogonal. The pre-promotion gate catches training-side failures (remapper bugs, trigger-word collapse, rank mismatches). The runtime check catches operational failures (wrong file on disk, mflux version skew, corrupted safetensors). Neither alone is sufficient; together they close the silent-fallback trap from both ends.

**Load-bearing constraint:** SSIM thresholds (0.999 and 0.97) are **empirical seeds**. Calibration against the first real trained LoRA is part of the plan's Phase 3 deliverable. The numbers are fallible; the *checks* are not.

---

### Decision 4 — Protocol widening to `lora_paths[]` / `lora_scales[]`

**Decision:** The daemon's JSON-RPC render protocol and `scripts/render_common.send_render()` both accept `lora_paths: list[str]` + `lora_scales: list[float]`, replacing the prior singleton fields entirely. No backward-compatibility shim.

**Alternatives considered:**

| Option | Why rejected |
|---|---|
| Keep singleton; encode multi-LoRA as a single path with a special separator (`"a.safetensors,b.safetensors"`) | Stringly-typed, parse-fragile, hostile to `scale` correspondence. |
| Dual-protocol: old `lora_path` stays, new `lora_paths` added, daemon prefers the latter when both present | Every consumer must now handle both forms; migration is never complete; "one of `lora_path` or `lora_paths`" is an unenforceable contract. |
| Keep singleton, stack LoRAs at load time in a helper outside the daemon | Pushes composition into every caller; the daemon should be the single place the stack lands. |

**Why clean cutover wins:** the daemon is a sidecar with exactly three internal consumers (`render_common.py`, two batch-render scripts, and the Rust API — which is itself scheduled for port to Python). The total surface touching this protocol is ~20 lines. A compat shim would outlast the one day it takes to update all three callers.

---

## Consequences

### Positive

- **Silent-fallback becomes a detectable failure mode at two boundaries.** Pre-promotion verification keeps known-broken artifacts out of production; runtime OTEL surfaces drift and regressions. The GM panel's role as "lie detector for the renderer" is strengthened.
- **World-level visual divergence becomes a first-class concern** rather than a prompt-engineering workaround. Worlds like `the_real_mccoy` that need fundamentally different aesthetics than their parent genre get proper infrastructure support.
- **Training toolchain is pinned to one option** with a clear contract (mlx-examples → remapper → mflux). Future LoRA authors don't rediscover that Draw Things silently fails or that ai-toolkit's fused QKV breaks mflux.
- **The remapper isolates upstream churn.** When mlx-examples or mflux evolve their key conventions, the diff lives in `mlx_to_mflux_keymap.yaml` — not in every caller.

### Negative

- **Keymap YAML is now load-bearing, versioned artifact.** Drift between mlx-examples's output naming and the keymap silently breaks new LoRAs until `verify.py` catches them. Mitigation is the pre-promotion gate itself; a LoRA that the remapper butchers will fail Check 1.
- **mflux private-API dependency.** `FluxLoRAMapping.get_mapping()` is class-public but is a weight-mapping internal. Tight version pin (`mflux>=0.4,<0.5`) mitigates but does not eliminate; upgrading mflux requires verifying the mapping shape manually before the pin moves.
- **Training datasets are now significant binary artifacts in the content repo.** 150-200 images per dataset × many future LoRAs × ~500KB per image = Git LFS costs climb. Mitigation is LFS-tracking the `lora-datasets/` path only; accepting the cost as the price of reproducibility.
- **One more required tool in the Apple Silicon developer setup:** `mlx-examples` clone + dedicated venv. Documented in Phase 0 of the plan.

### Neutral

- **ADR-032 is extended, not superseded.** Its original reasoning (LoRAs to offload style from CLIP tokens to model weights) stands. This ADR adds scale (multi-LoRA), granularity (world-level), and verification infrastructure.
- **No gameplay-layer impact.** SOUL principles are untouched; the changes are entirely in the image-generation substrate. Players see more visually-coherent worlds; the narrator's behavior is unchanged.

---

## Out of Scope

- **Cross-genre LoRA references.** A world in genre A cannot pull a LoRA from genre B. Hard constraint to preserve flat per-genre storage.
- **Hot-reload of LoRAs during a live session.** `visual_style.yaml` is read at session start; changing the stack mid-session requires session restart.
- **Character LoRAs.** This design targets *style* LoRAs. Character-identity LoRAs (specific people, creatures) may need different trigger-word conventions and dropout schemes; they get their own ADR when needed.
- **Non-MLX backends.** No CUDA fallback. No CPU fallback. Apple Silicon / MLX only.

## Open Questions

- **Threshold calibration is a one-data-point exercise initially.** Phase 3 calibrates against the first trained LoRA (spaghetti_western_landscape). The right calibration for a rank-4 LoRA at scale 0.3 may differ — if this ever becomes a real scenario, thresholds move to per-kind overrides in `verify_prompts/*.yaml`. Not load-bearing now.
- **Verify gate runtime on M3 Max.** Budgeted ~6 minutes per LoRA (4 renders × ~85s observed). If future Flux model variants change render cost (e.g., a Flux-schnell-native remap), the budget changes; not structurally hard to adjust.

## Supersedes / Is Superseded By

- **Extends:** ADR-032 (genre-specific LoRA style training). The original single-LoRA wiring becomes a special case of the hybrid stack (genre-level entry with no world overrides).
- **Superseded by:** none.
