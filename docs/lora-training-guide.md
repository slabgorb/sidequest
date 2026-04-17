# LoRA Training Guide — Genre Style LoRAs

Lessons learned from training the first four genre LoRAs (`leone_style`,
`ukiyo_e_landscape`, `dnd_ink`, `victorian_painting`). Read this before
captioning a dataset or starting a new training run. The `sq-lora` skill
covers the mechanical pipeline; this guide covers the traps.

## TL;DR

- **Style LoRA captions must describe CONTENT, never STYLE.** Anything you
  tag is a thing the LoRA ignores — it assumes the user will supply it at
  inference time. The LoRA only learns what is *constant across the dataset
  but never mentioned*.
- **Trigger word:** one nonsense token per image. `leone_style`, `ukiyo_e_landscape`,
  `vctr_paint` — that's fine. Do not stack multiple style tokens.
- **Draw Things CLI output is `.ckpt` in a custom binary format.** It is NOT
  a PyTorch pickle. `torch.load()` will fail. Convert to `.safetensors`
  using the **Draw Things GUI LoRA Manager → Export**.
- **LoRAs must be registered** in `~/Library/Containers/com.liuliu.draw-things/Data/Documents/Models/custom_lora.json`
  before the CLI will load them. Training does not auto-register.
- **Flux renders prompt words literally.** If you put "oil painting" or
  "watermark" or "signature" in the prompt, Flux will sometimes draw those
  words as actual text in the image. Use negative prompts aggressively.

---

## Style LoRA vs Subject LoRA — the caption rule

This is the single most counterintuitive fact about LoRA training:

> **Tags in captions are what the LoRA IGNORES.**

The model treats caption tags as attributes the user will provide at
inference time. So if every caption says `film_grain, desaturated, crushed_blacks`,
the LoRA learns "the user already knows this" and does NOT embed those
effects in the trigger word. Then at inference, unless the user types
those exact words, the style effect is missing.

The LoRA learns what is **constant across the dataset but NEVER tagged**.

### Style LoRA (what we want for genre packs)

- **Goal:** Apply genre aesthetic to any prompt content.
- **Captions:** Trigger word + natural-language **content** description.
- **Do NOT include:** style descriptors, artist names, film grain, color palette,
  cinematography terms, medium (oil/watercolor/digital), or any visual quality words.
- **Do include:** subject, composition, location, objects, lighting conditions
  (as physical facts like "morning", not aesthetic choices like "golden hour").

Example (correct):
```
leone_style, weathered gunman in wide-brimmed hat standing alone in an
empty town square, low angle, church bell tower in the background,
midday sun
```

### Subject LoRA (not what we want here)

- **Goal:** Reproduce specific characters, objects, or scenes.
- **Captions:** Trigger word only, or trigger + minimal framing.
- Use for character identity LoRAs (ADR-034 portrait consistency), not
  genre style.

### What we did wrong on the first pass (and have to re-do)

Every spaghetti_western caption included:
```
leone_style, film_still, cinematic, techniscope, high_contrast, film_grain,
desaturated, washed_out_color, crushed_blacks, sergio_leone, {content}
```

Every victoria caption was **identical**:
```
victorian_painting, oil_painting, canvas, landscape, english_countryside,
pastoral, dramatic_sky, clouds, green_fields, trees, naturalistic, john_constable
```

Both datasets produced LoRAs that regurgitate training-set CONTENT at
the trigger word instead of applying STYLE to arbitrary prompts. The
spaghetti western LoRA tries to draw a poncho-wearing figure in a desert
no matter what you ask for; the victoria LoRA only looks right when the
prompt matches "English countryside pastoral with clouds".

### The re-captioning recipe

1. Start from the raw images (no style tags).
2. For each image, write a one-line natural-language description of the
   CONTENT only. Use Claude, Florence-2, or BLIP to batch this — see
   `scripts/caption_claude.py` and `scripts/caption_florence2.py`.
3. Prepend the trigger word: `leone_style, {content description}`.
4. Strip any auto-generated tags that describe visual style, medium,
   color, or aesthetic quality.
5. Spot-check 20 random captions to make sure style language is absent.

---

## Draw Things CLI quirks

### Training command

```bash
/opt/homebrew/bin/draw-things-cli train lora \
  --model flux_1_dev_q8p.ckpt \
  --dataset /path/to/captioned-dataset \
  --output {trigger_word} \
  --name "{Genre} Style" \
  --steps 1000 --rank 32 --learning-rate 1e-4 \
  --use-aspect-ratio --caption-dropout 0.1 \
  --save-every 500 --noise-offset 0.1 \
  --memory-saver turbo \
  --resolution 768 \
  --gradient-accumulation 4
```

**`--memory-saver turbo`** works on M3 Max 128GB and trains faster than
`speed` mode. Use `balanced` on lower-memory machines.

**Training time** on M3 Max 128GB: ~2h 45m for 1000 steps on 1131 images
(victoria dataset), 0.09 it/s.

### Output

Checkpoints land in:
```
~/Library/Containers/com.liuliu.draw-things/Data/Documents/Models/
```

Filenames: `{trigger_word}_{step_count}_lora_f32.ckpt` — e.g.,
`victorian_painting_1000_lora_f32.ckpt`.

### Registration (mandatory)

Draw Things will NOT use a LoRA until it's registered in:
```
~/Library/Containers/com.liuliu.draw-things/Data/Documents/Models/custom_lora.json
```

Format (one entry per LoRA, appended to the existing array):
```json
{
  "version": "flux1",
  "prefix": "",
  "file": "victorian_painting_1000_lora_f32.ckpt",
  "is_lo_ha": false,
  "name": "Victorian Painting Style"
}
```

If you skip this step, the CLI will silently generate without the LoRA
loaded. No error, no warning — just a plain Flux output. This cost us
an hour of debugging the first time.

### Generation with LoRA via CLI

```bash
draw-things-cli generate \
  --model flux_1_dev_q8p.ckpt \
  --config-json '{"loras":[{"file":"victorian_painting_1000_lora_f32.ckpt","weight":1.0,"mode":"all"}]}' \
  --prompt "victorian_painting, {content}" \
  --negative-prompt "photo, photorealistic, text, letters, words, signature, watermark" \
  --width 1344 --height 768 --steps 20 --cfg 3.5 --seed 1853 \
  --output out.png
```

**`JSLoRA` schema** (from `drawthingsai/draw-things-community`
`Libraries/Scripting/Sources/ScriptModels.swift`):
```swift
public final class JSLoRA: Codable {
  let file: String?     // basename in Models dir, not full path
  let weight: Float32   // required
  let mode: String?     // "all" | "base" | "refiner", optional (defaults to "all")
}
```

**`weight` is a plain float**, not the nested `{value, upper_bound, lower_bound}`
object you see in `custom_lora.json`. That nested form is the LoRA library
metadata, not the generation config — don't confuse the two.

---

## Format conversion: .ckpt → .safetensors for mflux

Draw Things' `.ckpt` is a custom NCNN/Metal binary. It is NOT a PyTorch
pickle. `torch.load()` fails with `UnpicklingError: the STRING opcode
argument must be quoted`. There is no community conversion script because
the format is proprietary.

**The only supported conversion path is the Draw Things GUI:**

1. Open Draw Things app (GUI, not CLI).
2. Open **LoRA Manager** from the dropdown.
3. Find the trained LoRA in the list.
4. Click the **three-dots menu** → **Export** (or "Create 8-bit model").
5. Save as `.safetensors`.
6. Drop into the daemon's LoRA path.

Docs: <https://docs.drawthings.ai/documentation/documentation/3.lora/>

The exported `.safetensors` loads directly in mflux (`Flux1(lora_paths=[...])`)
and ComfyUI with no further conversion.

---

## Daemon wiring

The daemon's `flux_mlx_worker.py` already supports LoRA loading via mflux:

```python
Flux1(
    model_config=config_factory[variant](),
    quantize=self.QUANTIZE,
    lora_paths=[lora_path],
    lora_scales=[lora_scale],
)
```

The `lora_path` and `lora_scale` flow from request params → worker. The
gap is only the format: mflux expects `.safetensors`. Once the GUI export
is done, wiring is:

1. Add `lora:` and `lora_trigger:` to each genre's `visual_style.yaml`:
   ```yaml
   lora: lora/leone_style.safetensors
   lora_trigger: leone_style
   ```
2. The daemon resolves `lora:` relative to the genre pack dir.
3. The prompt composer prepends `lora_trigger` to every image prompt.
4. OTEL spans `render.lora_path` and `render.lora_scale` confirm the LoRA
   is engaged at runtime (per `CLAUDE.md` observability principle).

**Current broken wiring:** `genre_packs/spaghetti_western/visual_style.yaml:41`
points to `lora/spaghetti_western_style.safetensors` with trigger `sw_style`.
Both are wrong — the actual trigger is `leone_style` and the file doesn't
exist yet (pending GUI export). Fix when the safetensors files are ready.

---

## The Flux prompt bleed trap

Flux.1-dev will render words from the prompt as literal text in the image
if they are salient. Words to avoid in positive prompts (or counter in
negative prompts):

- `painting`, `oil painting`, `oil`, `canvas`, `art`, `artwork`
- `photograph`, `photo`, `portrait` (unless you want a portrait)
- Any artist name that appears on gallery labels (e.g. `Sargent`, `Constable`)
- `signature`, `watermark`, `museum`, `gallery`
- The trigger word itself, if it contains a real English word

**The victorian_painting trigger is risky** for this reason — the word
"painting" is in it, and Flux has been known to draw the letters PAINTING
in the corner of the image. If we re-train, use a nonsense token like
`vctr_style` or `sq_victorian`.

**Defensive negative prompt** for every generation:
```
photo, photograph, photorealistic, text, letters, words, signature,
watermark, modern, logo, caption, title
```

---

## Dataset inventory (as of 2026-04-13)

Located in `sidequest-content/lora/`:

| Directory | Images | Trained | Trigger word | Notes |
|---|---|---|---|---|
| `spaghetti-western` | 430 | 500, 1000 | `leone_style` | Hybrid captions, needs re-caption |
| `elemental-harmony` | 540 | 500, 1000, 1500 | `ukiyo_e_landscape` | Hybrid captions, needs re-caption |
| `caverns-and-claudes` | 82 | 500, 1000 | `dnd_ink` | Small dataset, needs more images |
| `victoria` | 1131 | 500, 1000 | `victorian_painting` | Captions were identical per image, needs re-caption |
| `pulp-noir` | 104 | — | — | Untrained, ~halfway dataset-wise |

Trained weights (`.ckpt`) are committed to `lora/{genre}/` via Git LFS.
Training datasets live alongside them in the same directories.

---

## Checklist for the next training run

- [ ] Source images curated (no watermarks, no modern elements, no text overlays)
- [ ] Dataset has 150+ images minimum, 300+ preferred for style LoRAs
- [ ] Captions describe CONTENT only, never style
- [ ] Trigger word is a nonsense token and appears on every caption
- [ ] Trigger word does not contain real English words that Flux might
      render as text
- [ ] Every `.jpg`/`.png` has a matching `.txt`
- [ ] Spot-checked 20 random captions for style leakage
- [ ] Running on M3 Max 128GB with `--memory-saver turbo`
- [ ] After training: register in `custom_lora.json`
- [ ] Test with a prompt using the trigger word and generic content
- [ ] Test with a prompt that does NOT match training content (e.g., ask
      the spaghetti_western LoRA for a pirate ship) — if it regurgitates
      training content, it's a subject LoRA, not a style LoRA
- [ ] GUI export to `.safetensors` for daemon use
- [ ] Wire `lora:` / `lora_trigger:` into genre's `visual_style.yaml`
- [ ] Verify OTEL `render.lora_path` span at runtime
