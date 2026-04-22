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

**Caption convention for STYLE LoRAs: one tag per image, identical
across the dataset.** That single tag is the trigger word — the bare
genre name for genre-level LoRAs, the bare world name for world-level
LoRAs. **Do not add style descriptors. Do not add subject tags.** This
is non-obvious — the instinct is to describe each frame, but for a
style LoRA that actively poisons the trained register: the model
starts attributing the style's effect to "saloon" or "desert" or
"film_grain" instead of to the trigger, and prompts using those tokens
without the LoRA loaded will partially fire it. Validated against
kohya-ss / ai-toolkit / civitai community consensus — captionless or
single-trigger training is the standard for style work.

| LoRA scope | Caption (every `.txt` is identical) |
|---|---|
| Genre-level (e.g., spaghetti_western) | `spaghetti_western` |
| World-level (e.g., the_real_mccoy) | `the_real_mccoy` |

That's the whole `.txt`. One token, no comma, no descriptors.

The matching `visual_style.yaml::loras[].trigger` field uses the same
bare token (no `_landscape` / `_portrait` suffix — the `applies_to:`
field is what scopes the LoRA to a tier; the trigger is just what the
model learned to associate the style with).

**SUBJECT LoRAs are different** — those need detailed per-image
natural-language captions (`photo of {trigger}, woman, smiling, blue
dress, three-quarter angle`) to enable prompt control. SideQuest
hasn't trained any subject LoRAs yet; if you do, treat that as a
separate skill flow.

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
- [ ] **Caption purity:** Every `.txt` is the bare trigger token only — no
      style descriptors, no subject tags, no extra text. (Spot-check 5
      random files: `for f in $(ls *.txt | shuf -n 5); do echo "=== $f ==="; cat "$f"; done`)
- [ ] **Coverage:** Key location types from `cartography.yaml` represented

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
  --resolution 512x512 \
  --checkpoint-every 250 \
  --progress-prompt "{trigger}, {representative scene that should reflect the trained register}" \
  --progress-every 250 \
  --progress-steps 8 \
  --output-dir "$OUT_DIR" \
  sidequest-content/lora-datasets/{genre}/{tier} \
  2>&1 | tee /tmp/{genre}_{tier}_train.log

deactivate
```

**`--progress-prompt` is required** — the trainer renders a sample image
every `--progress-every` iterations using this prompt so you can eyeball
whether the LoRA is converging. Pick something representative:
- Genre-style LoRA: `"spaghetti_western, a wide shot of a sun-bleached desert town at noon"`
- Portrait-tier LoRA: `"spaghetti_western, extreme close-up of a weathered face under a hat brim"`
- World-style LoRA: `"the_real_mccoy, a Pittsburgh steel mill at dusk"`

Keep `--progress-steps` low (8) — the progress renders are throwaway
quality checks, not final renders. They land in `$OUT_DIR/` alongside
the checkpoints.

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
toward 90+ GB, drop `--resolution 512x512` to `--resolution 384x384`
(format is `WIDTHxHEIGHT` with a literal lowercase `x`)
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

Genre-level entry in `genre_packs/{genre}/visual_style.yaml` — note
the `name` includes the tier (so `compose_lora_stack` can address it
distinctly when multiple per-tier LoRAs share a genre), but the
`trigger` is the bare genre name (matches the single-token caption
from Step 2):

```yaml
loras:
  - name: {genre}_{tier}                            # internal handle
    file: {genre}/{tier}.safetensors                # relative to sidequest-content/lora/
    scale: 0.8
    applies_to: [{tier}]                            # e.g., [landscape, scene]
    trigger: {genre}                                # bare genre name — the trained token
```

The `file:` field is a path relative to `sidequest-content/lora/` —
`render_common.py::_resolve_lora_file` prepends that prefix at
render time so YAML stays machine-portable across clones. Absolute
paths also work but break portability.

For a world-specific divergent register (e.g., `the_real_mccoy` is
1878 Pittsburgh, not 1966 Almería), exclude the genre LoRA and add
the world's. The world's `trigger` is the bare world name:

```yaml
# genre_packs/{genre}/worlds/{world}/visual_style.yaml
loras:
  exclude: [{genre}_{tier}]
  add:
    - name: {world}_{tier}
      file: {genre}/{world}_{tier}.safetensors     # relative to sidequest-content/lora/
      scale: 0.8
      applies_to: [{tier}]
      trigger: {world}                              # bare world name
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

**Filename convention:** shipped artifacts are `{tier}.safetensors`
(scoped by their `{genre}/` parent directory). The earlier
`{genre}_{tier}.safetensors` convention was dropped 2026-04-22 —
the parent dir already namespaces by genre, so the prefix was
redundant.

| Genre | Tier | Status | Trigger | Rank | Iter | File | Notes |
|-------|------|--------|---------|------|------|------|-------|
| spaghetti_western | landscape | **shipped** (2026-04-22) | `spaghetti_western` | 8 | 1500 | `lora/spaghetti_western/landscape.safetensors` | First mlx-pipeline LoRA; wired in `dust_and_lead` at scale 0.65; explicitly NOT applied to `the_real_mccoy` (period-divergent 1878 Pittsburgh) |
| elemental_harmony | landscape | **shipped** (2026-04-22) | `elemental_harmony` | 8 | 1500 | `lora/elemental_harmony/landscape.safetensors` | Ukiyo-e corpus (Kuniyoshi/Hokusai/Hiroshige); wired at genre level at scale 0.65; supersedes legacy `ukiyo_e_landscape_1500_lora_f32.ckpt` |
| caverns_and_claudes | portrait | shipped (legacy `.ckpt`) | `dnd_ink` | 32 | 1000 | `lora/caverns_and_claudes/dnd_ink_1000_lora_f32.ckpt` | Pre-mlx pipeline; portrait re-train pending |
| elemental_harmony | landscape (legacy) | archived | `ukiyo_e_landscape` | 32 | 1500 | `lora/elemental_harmony/ukiyo_e_landscape_1500_lora_f32.ckpt` | Pre-mlx; superseded 2026-04-22 by mlx rank-8 pipeline |
| spaghetti_western | unified (legacy) | archived | `leone_style` | 32 | 1000 | `lora/spaghetti_western/archive/legacy/leone_style_1000_lora_f32.ckpt` | Replaced by per-tier landscape split |
| the_real_mccoy | landscape | **shipped** (2026-04-22) | `the_real_mccoy` | 8 | 1500 | `lora/spaghetti_western/the_real_mccoy/landscape.safetensors` | First world-divergent LoRA; wired at world level at scale 0.65. Dataset: 179 square tiles cropped from 90 period-media sources (Harper's Weekly engravings + Underwood stereographs + Currier & Ives lithographs + cabinet-card portraiture + Muybridge plates); all forced to sRGB TrueColor (trainer requires 3-channel). Mixed-register corpus → LoRA averages to "1870s monochrome" without committing to a single medium; works well once competing medium anchors are stripped from prompts. Stored under `{genre}/{world}/` subdir to avoid collision with genre-level LoRA. |
| spaghetti_western | portrait | queued | `spaghetti_western` | 8 | 1500 | — | Awaits portrait dataset curation |
| the_real_mccoy | portrait | queued | `the_real_mccoy` | 8 | 1500 | — | Training candidate `gilded_age_portrait_style` in world's `visual_style.yaml::lora_triggers.training_candidates` (corpus: Sarony cabinet cards, Brady post-war portraits, Southworth & Hawes daguerreotypes) |
| the_real_mccoy | scene (replicant_reveal) | queued | `the_real_mccoy_replicant` | 8 | 1500 | — | Training candidate `lève_future_replicant_style` (corpus: Albert Robida 1886 illustrations, posthumous daguerreotypes, Jules Worms engravings) |
