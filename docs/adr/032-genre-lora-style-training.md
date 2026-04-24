# ADR-032: Genre-Specific LoRA Style Training for Flux Image Generation

> New for Rust port. sq-2 uses text-only style prompts via `positive_suffix`.

## Status
**Superseded by ADR-070 (MLX Image Renderer / Z-Image) — 2026-04-24.**

LoRA support is being dropped from the SideQuest visual pipeline. The
Z-Image renderer (ADR-070) follows text-prompt art direction substantially
better than LoRA-trained Flux variants achieved in practice — direct
prompt control beats trained-style enforcement for SideQuest's needs.

The training pipeline described below was operational, but the rendered
output never reliably honored the trained style under varied subject
prompts. Effort spent tuning training datasets and trigger weights does
not pay back compared to writing precise per-genre `positive_suffix`
text and letting Z-Image execute it.

**Implications:**
- Schema fields `lora` and `lora_trigger` (referenced in this ADR's
  Decision section) are NOT being added. The `VisualStyle` model stays
  text-only.
- Genre style identity remains a `positive_suffix` text field per genre
  pack (the sq-2 mechanism this ADR was originally going to replace).
- Existing trained LoRAs and the training pipeline can be archived; the
  renderer-side wiring stories (Epic 17 backlog) are cancelled.
- ADR-083 (Multi-LoRA Stacking) and ADR-084 (LoRA Composition Dimension)
  should be reviewed — both depend on this one and may also need
  superseding.
- ADR-086 (Image-Composition Taxonomy) treats GENRE as a text prompt
  layer unconditionally — the "text vs LoRA" tension noted there is
  resolved by this supersession.

The text below is preserved as historical context.

---

> **Original status (now obsolete):** Accepted (LoRA generation working as of 2026-04)

## Context

SideQuest's image generation pipeline uses Flux with a dual-encoder architecture:
CLIP (77-token limit) handles style, T5-XXL (512-token limit) handles content. The
`FluxWorker.render()` method routes `prompt` to CLIP and `prompt_2` to T5 when a
`clip_prompt` is provided by `PromptComposer`.

The current approach encodes genre visual identity entirely through text prompts. The
`positive_suffix` field in each genre pack's `visual_style.yaml` appends style keywords
to every render request. For mutant_wasteland, that suffix alone is ~40 tokens:

```yaml
positive_suffix: >-
  post-apocalyptic digital painting, gritty painterly texture,
  desaturated earth tones with bioluminescent accent color,
  bruised amber and toxic green sky, cracked asphalt and rust,
  overgrown ruins, visible brush strokes, environmental storytelling,
  cinematic composition, dramatic volumetric light through haze
```

This creates a fundamental token budget conflict. CLIP's 77 tokens must carry both
style identity AND subject description. Portraits are the worst case: a character's
appearance (face, gear, scars, species traits) needs every token CLIP can give it,
but half the budget is burned on genre style keywords that are identical across every
render in the session. The `visual_tag_overrides` per location type compound the
problem further, adding location atmosphere keywords that also compete for the same
77-token CLIP budget.

The result: style drift across renders within the same genre, inconsistent visual
identity between portraits and landscapes, and a ceiling on character detail fidelity
that cannot be raised without sacrificing style coherence.

### Prior Art

- **Text-only prompting (current):** `PromptComposer` in sq-2 composes CLIP and T5
  prompts from `positive_suffix`, tier prefix, location tags, and cue subject. Works
  adequately for landscapes where style keywords and scene description overlap. Fails
  for portraits where they compete.
- **Stable Diffusion community:** LoRA fine-tuning on ~20-50 images is the standard
  approach for consistent style. Trigger words (e.g., `mw_style`) activate the learned
  style without consuming prompt tokens.
- **SDXL for training data:** SDXL's CLIP-only architecture makes it excellent at
  interpreting text style descriptions — exactly what CLIP was designed for. Using SDXL
  to generate the training corpus means the style description is faithfully rendered
  once, then baked into Flux weights via LoRA.

## Decision

Train per-genre Flux LoRA adapters on SDXL-generated style corpuses. At inference
time, the LoRA carries genre visual identity in the weights, freeing the entire CLIP
and T5 token budgets for content description.

### Training Pipeline

The training pipeline is offline and one-time per genre. It is NOT a runtime concern.

**Step 1: Generate style corpus with SDXL**

For each genre, assemble a hybrid style corpus of 30-50 images from two sources:

**A) SDXL-generated style plates (~20-30 images).** Use the genre's existing
`positive_suffix` as the primary style driver, with explicit painter references
added to the SDXL prompt where appropriate. SDXL's CLIP-native architecture makes
it the ideal model for interpreting these text style descriptions faithfully.

SDXL prompts should reference public-domain painters whose work aligns with the
genre's aesthetic. For example, mutant_wasteland might reference Zdzisław Beksiński
(surreal post-apocalyptic), low_fantasy might reference Klimt (gold leaf, ornamental
pattern) or Egon Schiele (raw figurative work). These painter names are powerful
CLIP tokens that anchor the style far more precisely than generic descriptors.

Subjects should cover the genre's visual range: landscapes, interiors, character
studies, action scenes, environmental details. The goal is to teach Flux the genre's
painterly identity across diverse content.

**B) Actual paintings from referenced artists (~10-20 images).** Include real
public-domain works that embody the genre's target aesthetic. These anchor the
training corpus to ground-truth artistic style rather than relying solely on SDXL's
interpretation. Source from Wikimedia Commons, The Met Open Access, or similar
public-domain collections.

The hybrid approach is stronger than either source alone: SDXL images provide
genre-specific content coverage (post-apocalyptic ruins, fantasy taverns, etc.)
while real paintings provide authoritative style signal that SDXL can only
approximate.

```bash
# Example: generate SDXL portion of mutant_wasteland corpus
python scripts/generate_lora_corpus.py \
  --genre mutant_wasteland \
  --count 30 \
  --model sdxl \
  --painters "beksinski,zorn" \
  --output genre_packs/mutant_wasteland/lora/corpus/

# Then manually add 10-15 public-domain paintings to the same corpus dir
```

**Step 2: Caption the corpus**

Auto-caption with BLIP-2, then manual review. Captions should describe content only,
not style — the LoRA learns style from pixel patterns, not from caption text. This
separation is critical: if captions include style words, the LoRA may learn to
associate style with those words rather than learning the visual pattern itself.

For real paintings in the corpus, caption the *subject matter* ("a woman in a gold
robe surrounded by ornamental patterns") not the artist or medium ("Klimt oil
painting"). The LoRA should learn the visual texture, palette, and composition from
the pixels — the caption teaches it what the *content* is so it can separate content
from style.

**Step 3: Train the Flux LoRA**

Train a LoRA adapter on the Flux dev model using the captioned corpus.

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Rank | 16-32 | Sufficient for style transfer without overfitting |
| Alpha | rank value (1:1) | Standard for style LoRAs |
| Training steps | 1200-2500 | Tuned per genre; monitor for overfit |
| Learning rate | 1e-4 (constant schedule) | Flow matching responds better to constant LR |
| Optimizer | AdamW8bit | Standard for VRAM-constrained training |
| Precision | bf16 | Required for Flux training stability |
| Resolution | 1024x1024 | Match Flux dev native resolution |
| Trigger word | `{genre_slug}_style` | e.g., `mw_style`, `so_style` |
| Output size | ~50-100MB per genre | .safetensors format |

```bash
# Example: train mutant_wasteland LoRA
python scripts/train_genre_lora.py \
  --genre mutant_wasteland \
  --corpus genre_packs/mutant_wasteland/lora/corpus/ \
  --trigger mw_style \
  --rank 16 \
  --steps 1000 \
  --output genre_packs/mutant_wasteland/lora/style.safetensors
```

**Step 4: Art direction loop**

Render test images with the LoRA loaded. If the style is wrong, adjust the SDXL
corpus (add images, remove outliers, adjust prompts) and retrain. This is the
creative iteration loop — it happens on Keith's workstation, not at runtime.

### Genre Pack Integration

Add two new fields to `VisualStyle` in the genre pack schema:

```yaml
# genre_packs/mutant_wasteland/visual_style.yaml

positive_suffix: >-
  post-apocalyptic digital painting, gritty painterly texture, ...

# NEW: LoRA style adapter
lora: "lora/style.safetensors"
lora_trigger: "mw_style"

negative_prompt: >-
  clean, modern, pristine, ...
```

The `lora` path is relative to the genre pack directory. The `lora_trigger` word is
prepended to the CLIP prompt at compose time, activating the LoRA's learned style.

**Directory structure change:**

```
genre_packs/mutant_wasteland/
├── visual_style.yaml
├── lora/
│   ├── style.safetensors      # Trained LoRA weights (~50-100MB)
│   └── corpus/                # Training images (git-ignored, regenerable)
│       ├── 001.png
│       ├── 001.txt            # BLIP-2 caption
│       └── ...
├── assets/
└── ...
```

The `lora/corpus/` directory is `.gitignore`d — it is regenerable from the training
script and the genre's `positive_suffix`. Only the trained `.safetensors` file ships
with the genre pack (tracked via Git LFS).

**Rust struct change** in `sidequest-genre` crate:

```rust
#[derive(Debug, Deserialize)]
pub struct VisualStyle {
    pub positive_suffix: String,
    pub negative_prompt: String,
    pub preferred_model: String,
    pub base_seed: u32,
    pub visual_tag_overrides: HashMap<String, String>,
    // NEW
    pub lora: Option<String>,          // relative path to .safetensors
    pub lora_trigger: Option<String>,   // trigger word, e.g. "mw_style"
}
```

**Python model change** in `sidequest/genre/models.py`:

```python
class VisualStyle(BaseModel):
    model_config = ConfigDict(extra="allow")

    positive_suffix: str = ""
    negative_prompt: str = ""
    preferred_model: str = "flux"
    base_seed: int = 0
    visual_tag_overrides: dict[str, str] = {}
    # NEW
    lora: str | None = None
    lora_trigger: str | None = None
```

### PromptComposer Changes

When a LoRA trigger word is configured, `PromptComposer` changes its CLIP prompt
composition strategy:

- **Without LoRA (current):** CLIP prompt = `positive_suffix` + tier prefix + subject summary
- **With LoRA:** CLIP prompt = `lora_trigger` + tier prefix + subject summary

The `positive_suffix` is dropped from the CLIP prompt entirely when a LoRA is active.
The trigger word is typically 1-2 tokens, freeing ~38 tokens for character/scene detail.
The `positive_suffix` can optionally be appended to the T5 prompt as supplementary
guidance, but in practice the LoRA makes it redundant.

### Daemon Wiring

**`FluxWorker` changes:**

The worker needs to load LoRA weights and apply them to the pipeline. Diffusers
supports this natively via `pipe.load_lora_weights()`.

```python
class FluxWorker:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.pipes: dict[str, Any] = {}
        self._active_variant: str | None = None
        self._loaded_lora: str | None = None  # NEW: track loaded LoRA

    def load_lora(self, lora_path: str) -> dict:
        """Load a LoRA adapter onto the active Flux dev pipeline."""
        if self._loaded_lora == lora_path:
            return {"status": "already_loaded", "path": lora_path}

        if self._loaded_lora is not None:
            self.pipes["dev"].unload_lora_weights()

        self.pipes["dev"].load_lora_weights(lora_path)
        self._loaded_lora = lora_path
        return {"status": "loaded", "path": lora_path}

    def render(self, params: dict) -> dict:
        # ... existing logic ...

        # NEW: load LoRA if specified in params
        lora_path = params.get("lora_path")
        if lora_path and lora_path != self._loaded_lora:
            self.load_lora(lora_path)

        # ... rest of render ...
```

**Render params flow:**

```
Server (Rust)
  → reads genre_pack visual_style.lora
  → resolves to absolute path: {genre_pack_dir}/lora/style.safetensors
  → includes lora_path in RenderParams sent to daemon

PromptComposer (Python, sq-2 / or Rust in oq-2)
  → detects lora_trigger in VisualStyle
  → replaces positive_suffix with trigger word in CLIP prompt
  → full T5 prompt unchanged (all 512 tokens for content)

FluxWorker (Python daemon)
  → receives lora_path in render params
  → loads LoRA if not already cached
  → renders with LoRA active
```

**`WorkerPool.render()` change:**

The daemon's `WorkerPool.render()` method passes `lora_path` through to the Flux
worker without interpretation. The path resolution happens upstream in the server
or `PromptComposer`.

### Performance Profile

| Operation | Cost | Frequency |
|-----------|------|-----------|
| SDXL corpus generation | ~2-5 min per genre (40 images) | One-time, offline |
| LoRA training | ~15-30 min per genre on M-series | One-time, offline |
| LoRA loading at runtime | ~1-2s first render per genre | Once per session |
| Per-render overhead with LoRA | Negligible (<50ms) | Every render |
| LoRA file size | ~50-100MB per genre | Storage cost |

LoRA loading is amortized: once loaded for a genre, it stays in GPU memory for the
duration of the session. Genre switches (rare in practice — a game session is one
genre) trigger a LoRA swap (~2s).

## Consequences

### Positive

- **Full CLIP budget for content.** Portraits get 75+ tokens for character description
  instead of ~35. This is the primary motivator.
- **Style consistency across renders.** LoRA-encoded style is deterministic in the
  weights, not subject to CLIP interpretation variance per prompt.
- **Art-directable.** The SDXL corpus is a visual, human-reviewable artifact. Keith
  can curate exactly which images define a genre's look, retrain, and see the result
  immediately. This is a tighter feedback loop than tweaking text prompts.
- **Decouples style from prompting.** Adding new render tiers or changing prompt
  composition logic does not risk style regression.
- **Scales per genre.** Each genre pack can independently have a LoRA or not. Packs
  without a LoRA fall back to current text-only behavior with zero code changes.

### Negative

- **Storage cost.** ~50-100MB per genre pack for the `.safetensors` file. With 6
  genre packs, that is 300-600MB of Git LFS. Acceptable for a personal project.
- **Training requires GPU and diffusers expertise.** The training scripts are
  project-specific tooling that only Keith runs. This is fine for a personal project
  but would be a bus-factor concern for a team.
- **LoRA quality depends on corpus curation.** A bad training set produces a bad
  LoRA. The art direction loop is manual and requires visual judgment.
- **Flux LoRA ecosystem maturity.** Flux LoRA training is newer than SDXL LoRA
  training but well-established as of 2025. Three mature tools: SimpleTuner (most
  stable, recommended for production), AI-Toolkit by ostris (fastest iteration),
  and Kohya SS (runs on 12GB VRAM, GUI). Community consensus: style LoRAs work
  well on Flux at rank 16-32 with 30-50 images. K-LoRA (CVPR 2025) validates
  that style and content can be cleanly separated in Flux's architecture.

### Neutral

- **`positive_suffix` remains in schema.** It is still used as the SDXL corpus
  generation prompt, and as a fallback for genres without a trained LoRA. No
  breaking changes to existing genre packs.
- **No daemon architecture change.** The `FluxWorker` already loads models lazily.
  LoRA loading follows the same pattern. No new workers, no new subprocess protocol.
- **Training pipeline is scripts, not crates.** The `generate_lora_corpus.py` and
  `train_genre_lora.py` scripts live in `oq-2/scripts/` alongside existing tooling
  like `generate_poi_images.py`. They are dev tools, not production code.

## Migration Path

1. **Add `lora` and `lora_trigger` fields** to `VisualStyle` in both Python
   (`sidequest/genre/models.py`) and Rust (`sidequest-genre` crate). Both fields
   are `Option`/`None`-defaulted, so all existing genre packs parse unchanged.

2. **Update `PromptComposer`** to check for `lora_trigger` and adjust CLIP prompt
   composition. When absent, behavior is identical to today.

3. **Update `FluxWorker.render()`** to accept and load `lora_path` from params.
   When absent, behavior is identical to today.

4. **Write training scripts** (`scripts/generate_lora_corpus.py`,
   `scripts/train_genre_lora.py`) as standalone CLI tools.

5. **Train mutant_wasteland first** as the pilot genre (fully spoilable, most
   visually distinct). Validate portrait quality improvement with A/B comparison.

6. **Roll out to remaining genres** one at a time, art-directing each corpus
   independently.

7. **Add Git LFS tracking** for `genre_packs/*/lora/*.safetensors` and
   `.gitignore` for `genre_packs/*/lora/corpus/`.

Each step is independently deployable. The system runs without LoRAs exactly as it
does today. LoRA support is purely additive.
