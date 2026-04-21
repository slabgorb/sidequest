---
description: LoRA training pipeline — collect, tag, train via mlx-examples, remap to mflux, verify on the daemon
---

# LoRA Training Pipeline

Train genre-specific LoRAs for Flux 1 Dev on Apple Silicon via the
`mlx-examples/flux/` dreambooth trainer, remap them into the
Kohya/mflux key convention, and ship through the daemon's multi-LoRA
protocol with OTEL match-count verification.

This skill replaces the prior Draw Things workflow. It plugs into:
- **Trainer:** `~/Projects/mlx-examples/flux/dreambooth.py` (MLX-native)
- **Wrapper:** `scripts/lora/train.py` (preflight + invocation surface)
- **Remapper:** `scripts/lora/remap_mlx_to_mflux.py` (mlx → Kohya/mflux)
- **Keymap:** `scripts/lora/mlx_to_mflux_keymap.yaml` (26 rules, ADR-083)
- **Renderer:** `sidequest-daemon/.../flux_mlx_worker.py` (mflux multi-LoRA)
- **Resolver:** `scripts/render_common.py::compose_lora_stack` (per-tier)

## Parameters

| Param | Description | Default |
|-------|-------------|---------|
| `--genre <name>` | Target genre pack (snake_case, matches `genre_packs/`) | (required) |
| `--world <name>` | World-specific LoRA (omit for genre-level) | (none) |
| `--tier <kind>` | `landscape`, `portrait`, `scene` — drives `applies_to:` | `landscape` |
| `--step <0-5>` | Resume from a specific step | `0` |
| `--rank <N>` | LoRA rank (4, 8, 16; higher = stronger + bigger file) | `8` |
| `--iterations <N>` | Training iterations | `1500` |

## Steps

Run sequentially. Each produces artifacts the next consumes; `--step N`
resumes mid-pipeline.

---

### Step 0: Environment check

**Goal:** Confirm the local toolchain is ready before touching data.

```bash
# Trainer checkout (created once per machine)
test -d ~/Projects/mlx-examples/flux/dreambooth.py || \
  git clone https://github.com/ml-explore/mlx-examples ~/Projects/mlx-examples

# Trainer venv (created once)
test -d ~/.venv/mlx-flux-training || python3 -m venv ~/.venv/mlx-flux-training
source ~/.venv/mlx-flux-training/bin/activate
pip install -r ~/Projects/mlx-examples/flux/requirements.txt datasets safetensors
deactivate

# mflux runtime (in the daemon venv)
cd sidequest-daemon && uv pip show mflux | grep Version
# Must report >= 0.17, < 0.18 (the FluxLoRAMapping API targets this range)
```

**Hardware budget:** mlx-examples reports ~50GB peak RAM during training.
M3 Max 128GB is comfortable; any 64GB+ M-series should work.

---

### Step 1: Research & Download

**Goal:** Collect 150-200 reference images per LoRA target.

**Sources:**
- Film stills (primary) — `yt-dlp` + `ffmpeg` frame extraction from
  cinematography reels
- Period art — Remington/Russell (western), Hokusai/Kuniyoshi (ukiyo-e),
  Sargent/Grimshaw (victorian) — match the genre's art-history register
- Photography — landscape reference matching the genre's geography

**YouTube frame extraction:**
```bash
yt-dlp -f 'bestvideo[ext=mp4]' -o '%(title)s.%(ext)s' '<URL>'
ffmpeg -i input.mp4 -vf "fps=1/5,scale=1024:-1" -q:v 2 frames/frame_%04d.jpg

# For specific timestamp ranges (e.g., a landscape-heavy sequence)
ffmpeg -i input.mp4 -ss 00:02:30 -to 00:05:00 \
  -vf "fps=1/2,scale=1024:-1" -q:v 2 frames/frame_%04d.jpg
```

**Output layout (post-Task 4.5 snake_case convention):**
```
sidequest-content/lora-datasets/{genre}/landscape/
sidequest-content/lora-datasets/{genre}/portrait/
sidequest-content/lora-datasets/{genre}/scene/
```

**Curation rules:**
- Drop blurry/transition/black frames, modern anachronisms, watermarks,
  text overlays, credits
- Per tier:
  - **Landscape:** wide establishing shots, location atmosphere, architecture
  - **Portrait:** close-ups, character framing, expressive lighting
  - **Scene:** medium shots with multiple subjects, action, environment context

---

### Step 2: Caption (paired `.txt` — preflight format)

**Goal:** A same-stem `.txt` per image. This is what the Step 3
preflight validates. The jsonl conversion mlx-examples wants happens
immediately before training in Step 4.

**Caption format:**
```
{trigger_word}, {style_tags}, {subject_tags}
```

**Trigger words** — one per LoRA, namespace by genre+tier:
- `{genre}_{tier}` — e.g., `spaghetti_western_landscape`,
  `elemental_harmony_portrait`. Used at inference to activate the LoRA's
  trained register; declared in `visual_style.yaml::loras[].trigger`.

**Style tags** — consistent across the set, derived from
`genre_packs/{genre}/visual_style.yaml::positive_suffix`. Spaghetti
western example:
```
film_still, cinematic, techniscope, high_contrast, film_grain,
desaturated, washed_out_color, crushed_blacks, dust
```

**Subject tags** — per-image, describe the frame:
```
# Landscape
desert, mesa, wide_shot, establishing_shot, heat_shimmer, empty_road
saloon, interior, oil_lamp, wooden_bar, swinging_doors

# Portrait
extreme_close_up, eyes, weathered_face, hat_brim_shadow, sweat
medium_shot, poncho, gun_belt, squinting, backlit
```

---

### Step 3: Preflight gate

**Goal:** Catch dataset issues before committing to a 4-6 hour run.

```bash
python3 -c "
from pathlib import Path
from scripts.lora.train import preflight_dataset
print(preflight_dataset(Path('sidequest-content/lora-datasets/{genre}/{tier}')))
"
```

The preflight enforces:
- Directory exists
- Every `.jpg`/`.jpeg`/`.png` has a same-stem `.txt` caption
- ≥150 paired entries (`MIN_IMAGES` in `scripts/lora/train.py`)

A clean run prints `{'images': N, 'captions': N}`. Anything else aborts.

**Manual eyes-on checklist** (the preflight doesn't catch these):
- [ ] **Balance:** No single source dominates (>40% of images)
- [ ] **Variety:** Multiple lighting conditions, times of day, weather
- [ ] **Style alignment:** Style tags echo `visual_style.yaml::positive_suffix`
- [ ] **Coverage:** Key location types from `cartography.yaml` represented
- [ ] **Trigger word present:** Every caption starts with the trigger word

---

### Step 4: Train (mlx-examples)

**Goal:** Produce `final_adapters.safetensors` — the MLX-native LoRA.

#### 4a. Convert paired `.txt` → `train.jsonl`

mlx-examples reads `{"image": <path>, "prompt": <caption>}` JSONL, not
paired text files. Generate it from the dataset Step 3 just blessed:

```bash
cd sidequest-content/lora-datasets/{genre}/{tier}
python3 -c "
import json, pathlib
with pathlib.Path('train.jsonl').open('w') as out:
    for img in sorted(p for p in pathlib.Path('.').iterdir()
                      if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}):
        cap = img.with_suffix('.txt')
        if cap.exists():
            out.write(json.dumps({
                'image': img.name,
                'prompt': cap.read_text().strip(),
            }) + '\n')
"
cd -
```

#### 4b. Run dreambooth.py

```bash
source ~/.venv/mlx-flux-training/bin/activate

OUT_DIR=~/lora-runs/{genre}_{tier}_$(date +%Y%m%d_%H%M)
mkdir -p "$OUT_DIR"

python3 ~/Projects/mlx-examples/flux/dreambooth.py \
  --model dev \
  --lora-rank 8 \
  --lora-blocks -1 \
  --iterations 1500 \
  --batch-size 1 \
  --grad-accumulate 4 \
  --learning-rate 1e-4 \
  --warmup-steps 100 \
  --resolution 512 512 \
  --checkpoint-every 250 \
  --output-dir "$OUT_DIR" \
  sidequest-content/lora-datasets/{genre}/{tier} \
  2>&1 | tee /tmp/{genre}_{tier}_train.log

deactivate
```

**Output:** `$OUT_DIR/final_adapters.safetensors` (~77 MB at rank 4,
~150 MB at rank 8) plus `{NNNNNNN}_adapters.safetensors` checkpoints
every `--checkpoint-every` iterations.

**Hyperparameter notes:**
- **`--lora-blocks -1`** — train all transformer blocks. Anything else
  needs an updated keymap; do not change without validating against
  `scripts/lora/mlx_to_mflux_keymap.yaml`.
- **`--lora-rank`** — 4 is fast and small (smoke tests, weak style),
  8 is the production default, 16 only for very stylized targets.
  Higher rank = bigger file, more RAM, more reserved capacity.
- **`--checkpoint-every`** — saves intermediate `.safetensors`. Useful
  for picking the "best" checkpoint via Step 5 sweep when the run
  doesn't monotonically improve.

**RAM watch:** Activity Monitor should show ~50 GB peak. If it climbs
toward 90+ GB, drop `--resolution 512 512` to `--resolution 384 384`
or run a smaller `--lora-rank`.

---

### Step 5: Remap and verify

**Goal:** Convert MLX-native output to mflux's Kohya convention, prove
it actually loads.

#### 5a. Remap

```bash
python3 -m scripts.lora.remap_mlx_to_mflux \
  --input "$OUT_DIR/final_adapters.safetensors" \
  --output sidequest-content/lora/{genre}/{genre}_{tier}.safetensors \
  --keymap scripts/lora/mlx_to_mflux_keymap.yaml
```

The remapper:
- Hard-fails on any unmapped key (no silent drops)
- Transposes `(in, rank)` ↔ `(rank, in)` per the MLX↔Kohya convention
- For fused-QKV layers (img_attn.qkv, txt_attn.qkv, single_blocks.linear1),
  tiles the down matrix N× along the rank axis so mflux's BFL splitter
  produces correctly-shaped per-projection slices (see Phase 1 Task 1.5
  notes — this is the load-bearing fix that took the silent-fallback
  detector test to find)

Reports `Remap OK: N keys translated, rank=R` on success.

#### 5b. Smoke-test the silent-fallback detector

```bash
# Daemon must be warm (just daemon-run, wait ~3 min for Flux dev to load)
ls /tmp/sidequest-renderer.sock && tail -3 /tmp/sidequest-renderer.log

# Run the canonical roundtrip (~3 min wall clock on M3 Max)
python3 -m pytest tests/lora/test_remap_roundtrip.py -v -m slow
```

This test:
1. Renders a baseline (no LoRA) at seed 424242
2. Renders again with the remapped LoRA at the same seed
3. Asserts ≥0.1% of pixels differ — if they don't, the remap silently
   produced a no-op LoRA (the exact failure mode the whole pipeline
   exists to detect)

**A green test means the LoRA actually loaded and influenced the
render.** A red test with `diff_frac` near zero means investigate the
remap — usually a mflux-API drift or a missed keymap rule.

#### 5c. OTEL match-count check

When the daemon renders with the new LoRA, the `flux_mlx.render` span
gets `render.lora.matched_keys: list[int]` — one count per file. For a
healthy LoRA against current mflux:

```
INFO ... FLUX MLX RENDER [landscape] seed=... loras=[...] scales=[...] matched=[608]
```

A trained-from-mlx LoRA should report **608** matched keys (every
trained tensor lands in mflux's mapping). Anything materially lower
means the keymap missed something — re-run the remapper after
extending `scripts/lora/mlx_to_mflux_keymap.yaml`.

---

### Step 6: Wire into visual_style.yaml

**Goal:** Make the trained LoRA actually fire on production renders.

Genre-level entry in `genre_packs/{genre}/visual_style.yaml`:

```yaml
loras:
  - name: {genre}_{tier}
    file: lora/{genre}/{genre}_{tier}.safetensors
    scale: 0.8
    applies_to: [{tier}]      # e.g., [landscape, scene] for a landscape LoRA
    trigger: {genre}_{tier}   # matches the trigger word from Step 2 captions
```

For a world-specific divergent register (e.g., `the_real_mccoy` is
1878 Pittsburgh, not 1966 Almería), exclude the genre LoRA and add
the world's:

```yaml
# genre_packs/{genre}/worlds/{world}/visual_style.yaml
loras:
  exclude: [{genre}_{tier}]
  add:
    - name: {world}_{tier}
      file: lora/{genre}/{world}_{tier}.safetensors
      scale: 0.8
      applies_to: [{tier}]
      trigger: {world}_{tier}
```

The resolver `scripts/render_common.py::compose_lora_stack` enforces
the schema: missing required fields, empty `applies_to`, legacy
list-form world `loras:`, or world `add` reusing a genre name all
hard-fail at load time.

---

### Step 7: Verify against POIs

**Goal:** Re-render existing POI images with the new LoRA and eyeball.

```bash
# The script now passes tier=landscape to load_visual_style, picks up
# resolved_loras automatically via render_common's resolve_lora_args.
python3 scripts/generate_poi_images.py --genre {genre} --steps 20 --force
```

**Evaluation criteria** (per ADR-032 + ADR-083):
- [ ] **Genre truth:** Output reads as belonging in this genre
- [ ] **No anachronisms:** No modern elements bleeding through
- [ ] **Style consistency:** All outputs share a coherent visual language
- [ ] **Location differentiation:** Desert ≠ canyon ≠ town
- [ ] **Prompt responsiveness:** Changing the prompt meaningfully changes output
- [ ] **LoRA strength:** Style is present but not overwhelming (no melted
      faces, no over-grain)
- [ ] **OTEL `matched_keys` is steady:** Same value across renders, near 608

**Tuning:**
- Style too weak → bump `scale: 0.9` then `1.0` in visual_style.yaml,
  or train a higher-rank/longer-iteration LoRA
- Style too strong → drop `scale: 0.65`, or train fewer iterations
- Style fights prompts → caption coverage is too narrow; add variety
  to the dataset

**Final output:** Approved POI images land in
`genre_packs/{genre}/images/poi/`. Commit on a feature branch in the
sidequest-content subrepo (gitflow: branch off `develop`).

---

## Reference

| Item | Location |
|------|----------|
| Multi-LoRA stacking ADR | `docs/adr/083-multi-lora-stacking-and-verification.md` |
| Original LoRA training ADR | `docs/adr/032-genre-lora-style-training.md` |
| Pipeline spec | `docs/superpowers/specs/2026-04-20-lora-pipeline-design.md` |
| Pipeline plan | `docs/superpowers/plans/2026-04-20-lora-pipeline.md` |
| Phase 0 mlx-examples notes | `docs/superpowers/notes/2026-04-20-mlx-examples-flux-notes.md` |
| MLX trainer | `~/Projects/mlx-examples/flux/dreambooth.py` |
| Trainer venv | `~/.venv/mlx-flux-training/` |
| Preflight wrapper | `scripts/lora/train.py` |
| Remapper | `scripts/lora/remap_mlx_to_mflux.py` |
| Keymap (mlx → Kohya/mflux) | `scripts/lora/mlx_to_mflux_keymap.yaml` |
| Roundtrip silent-fallback test | `tests/lora/test_remap_roundtrip.py` |
| Compose resolver | `scripts/render_common.py::compose_lora_stack` |
| Daemon worker (multi-LoRA) | `sidequest-daemon/.../flux_mlx_worker.py` |
| Visual style configs | `genre_packs/{genre}/visual_style.yaml` |
| World visual overrides | `genre_packs/{genre}/worlds/{world}/visual_style.yaml` |
| POI generation script | `scripts/generate_poi_images.py` |
| LoRA storage layout | `sidequest-content/lora/{genre}/` (`archive/legacy/` for retired) |
| Training datasets | `sidequest-content/lora-datasets/{genre}/{tier}/` |
| `yt-dlp` | `~/.local/bin/yt-dlp` |

## Completed LoRAs

Track shipped LoRAs here; archive retired ones in
`sidequest-content/lora/{genre}/archive/legacy/`.

| Genre | Tier | Status | Trigger | Rank | Iter | File | Notes |
|-------|------|--------|---------|------|------|------|-------|
| elemental_harmony | landscape | shipped (legacy `.ckpt`) | `ukiyo_e_landscape` | 32 | 1500 | `lora/elemental_harmony/ukiyo_e_landscape_1500_lora_f32.ckpt` | Pre-mlx pipeline; awaiting retrain via Step 4 |
| spaghetti_western | unified (legacy) | archived | `leone_style` | 32 | 1000 | `lora/spaghetti_western/archive/legacy/leone_style_1000_lora_f32.ckpt` | Replaced by per-tier landscape/portrait split (Phase 2) |
| caverns_and_claudes | portrait (legacy `.ckpt`) | shipped | `dnd_ink` | 32 | 1000 | `lora/caverns_and_claudes/dnd_ink_1000_lora_f32.ckpt` | Pre-mlx pipeline; portrait re-train pending |
| spaghetti_western | landscape | **pending** | `spaghetti_western_landscape` | 8 | 1500 | `lora/spaghetti_western/spaghetti_western_landscape.safetensors` | First mlx pipeline LoRA; visual_style.yaml awaits this file |
| spaghetti_western | portrait | queued | `spaghetti_western_portrait` | 8 | 1500 | — | Awaits portrait dataset curation |
| the_real_mccoy | landscape | queued | `the_real_mccoy_landscape` | 8 | 1500 | — | World-divergent (1878 Pittsburgh) |
