# ADR-034: Portrait Identity Consistency — Tiered Character Recognition Pipeline

**Status:** Proposed
**Date:** 2026-03-31
**Deciders:** Keith
**Relates to:** ADR-032 (Genre LoRA Style Training)

## Context

SideQuest generates character portraits via Flux in the daemon. Each generation is
independent — the same character rendered twice produces two visually different people.
Facial structure, skin tone, scars, hair, and body type all drift between renders
because the diffusion process samples independently each time.

This breaks emotional continuity. When a player looks at their character portrait,
they should feel ownership — "that's my character." When the narrator describes an
NPC the player met three scenes ago, the portrait should be recognizably the same
person. Identity drift erodes both.

The problem scales with the cast: a session may have 1-4 PCs and 10-30 NPCs. Training
a LoRA per character (the highest-fidelity approach) would require minutes of GPU time
per character and is impractical at session pace. We need a tiered approach that
invests consistency quality proportional to character importance.

### Hardware Context

Keith's workstation is an M3 Max MacBook Pro with 128 GB unified memory. The unified
architecture can hold Flux Dev (~24 GB), IP-Adapter model (~2 GB), and VAE (~300 MB)
simultaneously — no model swapping penalty. The constraint is MPS (Metal Performance
Shaders) compatibility, not VRAM. LoRA *inference* works on MPS via diffusers. LoRA
*training* on MPS is unreliable with current tooling (kohya, ai-toolkit).

### Relationship to ADR-032

ADR-032 addresses *genre style consistency* — every render in noir looks like noir.
This ADR addresses *character identity consistency* — the same character looks like
themselves across renders. The two are complementary: ADR-032's style LoRA sets the
visual tone, this ADR's identity pipeline preserves the individual within that tone.

## Decision

A three-layer portrait identity system with a two-tier quality split based on
character importance.

### Layer 1: Canonical Portrait (all characters)

Every character gets one canonical portrait at creation time. This is the identity
anchor — the single source of truth for what this character looks like.

```
Character created
  → API generates structured appearance description from game state
  → Daemon renders portrait (Flux Dev + genre style LoRA if available)
  → Result stored as canonical: {portrait_dir}/{session_id}/{character_id}/canonical.png
  → Canonical path recorded in character game state
```

The canonical portrait is generated at normal Flux speed (~5-8s on M3 Max). No
additional pipeline overhead. This is the baseline every character gets.

### Layer 2: Reference Sheet (PCs and key NPCs only)

After the canonical portrait is delivered to the player, a background job generates
a multi-angle reference sheet. This provides the IP-Adapter with richer reference
material than a single headshot.

```
Canonical portrait delivered to client
  → Background job queued in daemon render queue
  → Generates 4-up reference sheet: front, 3/4 left, 3/4 right, expression variant
  → Stored as: {portrait_dir}/{session_id}/{character_id}/reference_sheet.png
```

The reference sheet is **never shown to the player**. It is backend infrastructure
for the re-render pipeline. Generation takes ~20-30s (4 renders composed) and
happens asynchronously — the player is already playing by the time it completes.

**Tier assignment:** The API marks characters as `high_fidelity` based on:
- All PCs: always high-fidelity
- DM-flagged NPCs: manual promotion via game command
- Recurring NPCs: auto-promoted after appearing in 3+ scenes (future heuristic)

### Layer 3: Identity-Aware Re-Rendering

When a character needs a new portrait (injury, disguise, scene illustration, mood
change), the render request includes identity context:

**High-fidelity characters (PCs, key NPCs):**
```
Re-render request
  → reference_image: path to canonical.png (or reference_sheet.png if available)
  → IP-Adapter engaged at strength 0.7-1.0
  → New prompt describes the changed context (injured, disguised, new lighting)
  → Result preserves facial identity while adapting to new context
```

**Standard characters (most NPCs):**
```
Re-render request
  → img2img with canonical.png as source
  → Denoise strength 0.3-0.5 (preserves structure, shifts mood/lighting)
  → No IP-Adapter overhead
  → Result preserves rough likeness at lower fidelity cost
```

### Daemon API Contract

Add an optional `reference_image` field to render requests. The daemon remains
stateless about characters — it receives paths, not identity concepts.

```python
class RenderParams(BaseModel):
    prompt: str
    prompt_2: str | None = None
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    seed: int | None = None
    lora_path: str | None = None       # ADR-032: genre style LoRA
    # NEW: identity consistency
    reference_image: str | None = None  # Path to canonical/reference_sheet
    reference_strength: float = 0.85    # IP-Adapter strength (0.0-1.5)
    source_image: str | None = None     # Path for img2img input
    denoise_strength: float = 0.4       # img2img denoise (0.0-1.0)
```

**Behavior matrix:**

| `reference_image` | `source_image` | Pipeline |
|--------------------|----------------|----------|
| None | None | Standard txt2img (current behavior) |
| Set | None | IP-Adapter guided txt2img (high-fidelity re-render) |
| None | Set | img2img (standard re-render) |
| Set | Set | IP-Adapter guided img2img (maximum consistency) |

### Portrait Identity Store

Directory structure per session:

```
{portrait_dir}/
└── {session_id}/
    ├── {character_id_1}/
    │   ├── canonical.png          # First portrait, identity anchor
    │   ├── reference_sheet.png    # 4-up multi-angle (PCs only, async)
    │   ├── scene_001.png          # Re-render for scene illustration
    │   └── scene_003.png          # Another re-render
    └── {character_id_2}/
        ├── canonical.png
        └── ...
```

The API owns the mapping from character to portrait directory. The daemon receives
absolute paths in render requests and writes output to the specified location. Clean
separation: API owns identity, daemon owns rendering.

### IP-Adapter Integration

The daemon's `FluxWorker` loads the IP-Adapter model alongside the base Flux model.
With 128 GB unified memory, both remain resident — no swap penalty.

```python
class FluxWorker:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.pipes: dict[str, Any] = {}
        self._active_variant: str | None = None
        self._loaded_lora: str | None = None
        self._ip_adapter_loaded: bool = False  # NEW

    def ensure_ip_adapter(self) -> None:
        """Load IP-Adapter onto the Flux dev pipeline if not already loaded."""
        if self._ip_adapter_loaded:
            return
        self.pipes["dev"].load_ip_adapter(
            "h94/IP-Adapter",
            subfolder="sdxl_models",  # or flux-specific adapter when available
            weight_name="ip-adapter-plus_sdxl_vit-h.safetensors",
        )
        self._ip_adapter_loaded = True

    def render(self, params: dict) -> dict:
        # ... existing model/lora loading ...

        reference_image = params.get("reference_image")
        source_image = params.get("source_image")

        if reference_image:
            self.ensure_ip_adapter()
            ip_image = load_image(reference_image)
            # IP-Adapter adds reference guidance to the generation
            result = self.pipes["dev"](
                prompt=params["prompt"],
                ip_adapter_image=ip_image,
                ip_adapter_scale=params.get("reference_strength", 0.85),
                image=load_image(source_image) if source_image else None,
                strength=params.get("denoise_strength", 0.4) if source_image else None,
                # ... other params ...
            )
        elif source_image:
            # img2img without IP-Adapter (standard NPC re-render)
            result = self.pipes["dev"](
                prompt=params["prompt"],
                image=load_image(source_image),
                strength=params.get("denoise_strength", 0.4),
                # ... other params ...
            )
        else:
            # Standard txt2img (current behavior, unchanged)
            result = self.pipes["dev"](
                prompt=params["prompt"],
                # ... other params ...
            )

        # ... save and return ...
```

### Rust API Wiring

The API's portrait service orchestrates the identity pipeline:

```rust
pub struct PortraitService {
    portrait_dir: PathBuf,
    daemon_client: DaemonClient,
}

impl PortraitService {
    /// Generate canonical portrait for a new character.
    pub async fn create_canonical(
        &self,
        session_id: &str,
        character: &Character,
        genre_style: &VisualStyle,
    ) -> Result<PathBuf> {
        let char_dir = self.portrait_dir
            .join(session_id)
            .join(&character.id);
        fs::create_dir_all(&char_dir).await?;

        let canonical_path = char_dir.join("canonical.png");

        let params = RenderParams {
            prompt: character.appearance_prompt(),
            lora_path: genre_style.lora_absolute_path(),
            output_path: canonical_path.clone(),
            ..Default::default()
        };

        self.daemon_client.render(params).await?;

        // If high-fidelity, queue background reference sheet
        if character.high_fidelity {
            self.queue_reference_sheet(session_id, character, genre_style)
                .await?;
        }

        Ok(canonical_path)
    }

    /// Re-render a character in a new context.
    pub async fn rerender(
        &self,
        session_id: &str,
        character: &Character,
        context_prompt: &str,
        genre_style: &VisualStyle,
    ) -> Result<PathBuf> {
        let char_dir = self.portrait_dir
            .join(session_id)
            .join(&character.id);

        let reference_sheet = char_dir.join("reference_sheet.png");
        let canonical = char_dir.join("canonical.png");

        let params = if character.high_fidelity {
            // IP-Adapter path: use best available reference
            let ref_path = if reference_sheet.exists() {
                &reference_sheet
            } else {
                &canonical
            };
            RenderParams {
                prompt: context_prompt.to_string(),
                reference_image: Some(ref_path.to_string_lossy().into()),
                reference_strength: 0.85,
                lora_path: genre_style.lora_absolute_path(),
                ..Default::default()
            }
        } else {
            // img2img path: use canonical as source
            RenderParams {
                prompt: context_prompt.to_string(),
                source_image: Some(canonical.to_string_lossy().into()),
                denoise_strength: 0.4,
                lora_path: genre_style.lora_absolute_path(),
                ..Default::default()
            }
        };

        let output = char_dir.join(format!("scene_{}.png", scene_id));
        self.daemon_client.render_to(params, &output).await?;
        Ok(output)
    }
}
```

### Strength Calibration Guide

| Scenario | Pipeline | Reference Strength / Denoise | Rationale |
|----------|----------|------------------------------|-----------|
| Same character, different background | IP-Adapter | 0.9-1.0 | Maximum identity lock, only environment changes |
| Character injured/scarred | IP-Adapter | 0.7-0.8 | Allow visible changes while preserving base identity |
| Character disguised | IP-Adapter | 0.5-0.6 | Player should still recognize them, but appearance shifts |
| NPC in new scene | img2img | 0.3-0.4 | Rough likeness sufficient, mood/lighting adapt freely |
| NPC casual mention | None | N/A | Re-use canonical portrait directly, no re-render needed |

### Performance Profile

| Operation | Time (M3 Max) | Frequency |
|-----------|---------------|-----------|
| Canonical portrait generation | ~5-8s | Once per character |
| Reference sheet (4-up, background) | ~20-30s | Once per PC/key NPC |
| IP-Adapter re-render | ~6-10s | Per scene for PCs |
| img2img re-render | ~3-5s | Per scene for NPCs |
| IP-Adapter model loading | ~2s | Once per session |

All re-render times assume Flux Dev + genre style LoRA already resident in memory.
IP-Adapter model load is one-time and amortized across the session.

## Consequences

### Positive

- **Emotional continuity.** Players recognize their character across scenes. NPCs
  look like themselves when they reappear. The narrative feels visually coherent.
- **No runtime training.** Everything works at inference time. No LoRA training
  during gameplay. No CUDA dependency at runtime.
- **Tiered cost.** PCs get IP-Adapter quality (~90% consistency). NPCs get img2img
  quality (~75% consistency). Background NPCs reuse their canonical portrait with
  no re-render cost at all. Quality investment matches narrative importance.
- **Daemon stays stateless.** The daemon doesn't know about characters, sessions,
  or identity. It receives render parameters with optional paths. The API owns all
  identity logic. Clean separation of concerns.
- **Non-blocking character creation.** The canonical portrait renders at normal speed.
  The reference sheet generates asynchronously. Players never wait for consistency
  infrastructure.
- **Composable with ADR-032.** Genre style LoRA (ADR-032) handles art direction.
  IP-Adapter / img2img (this ADR) handles character identity. Both operate on the
  same render request without interference — style LoRA runs in the model weights,
  IP-Adapter runs in the attention layers.

### Negative

- **IP-Adapter MPS compatibility is unverified.** The `h94/IP-Adapter` reference
  implementation targets CUDA. The `diffusers` integration supports MPS in theory
  but needs validation on M3 Max. If IP-Adapter fails on MPS, the high-fidelity
  tier falls back to img2img (reducing PC consistency from ~90% to ~75%).
- **Reference sheet quality depends on first portrait.** If the canonical portrait
  has artifacts or a bad angle, the reference sheet amplifies those issues. May need
  a "regenerate canonical" player action.
- **Storage growth.** Each PC accumulates scene re-renders (~1-2 MB each). A long
  campaign could produce hundreds of portraits. Needs periodic cleanup or a retention
  policy (keep canonical + last N scene renders).
- **No face-level consistency guarantee.** IP-Adapter preserves overall visual
  similarity, not pixel-precise facial features. For most game contexts this is
  sufficient, but edge cases (twins, doppelgangers, shape-shifters) may need
  special handling.

### Neutral

- **Existing render pipeline unchanged for default case.** When no `reference_image`
  or `source_image` is provided, the daemon behaves identically to today. Zero
  regression risk for the current path.
- **Player-editable canonical (future).** Letting the player regenerate until they
  like their portrait, then locking it as canonical, is a natural UX extension.
  Not in scope here but the architecture supports it — just regenerate and overwrite
  `canonical.png`.
- **CLIP similarity testing (future).** Automated regression testing via CLIP cosine
  similarity (> 0.85 threshold) between canonical and re-renders. The architecture
  produces artifacts (canonical + re-render pairs) that make this testable. Not in
  scope but enabled by this design.

## Migration Path

1. **Add `reference_image`, `reference_strength`, `source_image`, `denoise_strength`**
   to daemon `RenderParams`. All optional with sensible defaults. Zero breaking change.

2. **Add img2img support to `FluxWorker.render()`** — the `source_image` + `denoise_strength`
   path. This is simpler than IP-Adapter and validates the two-pipeline approach.

3. **Implement portrait identity store** — directory structure, canonical generation,
   path recording in character game state. API-side only.

4. **Verify IP-Adapter on MPS.** Load `h94/IP-Adapter` via diffusers on M3 Max. If it
   works, proceed. If not, evaluate alternatives (Flux Kontext when available, PuLID
   as fallback).

5. **Add IP-Adapter path to `FluxWorker.render()`** — the `reference_image` +
   `reference_strength` path.

6. **Implement background reference sheet generation** — async job after canonical
   delivery.

7. **Wire `PortraitService` in the API** — orchestrates canonical creation,
   tier assignment, and re-render routing.

Each step is independently deployable. Steps 1-3 deliver img2img consistency for
all characters. Steps 4-6 add IP-Adapter for high-fidelity characters. Step 7
wires the full orchestration.
