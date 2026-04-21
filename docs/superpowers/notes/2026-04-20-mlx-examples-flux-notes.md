# mlx-examples Flux LoRA Training — Phase 0 Observations

**Captured:** 2026-04-20
**Commit (ml-explore/mlx-examples):** `796f5b5` (tip of main at time of observation)
**Machine:** M3 Max, 128GB RAM, macOS 24.4.0
**Observer:** Winchester (Dev)

This document closes Phase 0 of the plan at `docs/superpowers/plans/2026-04-20-lora-pipeline.md`. It feeds Task 1.2 (keymap YAML) and Task 1.4 (remapper happy-path fixture + tests).

## Critical correction vs. plan assumptions

**The plan and spec assumed mlx-examples produces `.npz` output. They were wrong. It produces `.safetensors` directly.**

- Output filename: `{output_dir}/final_adapters.safetensors` and checkpoint variants `{output_dir}/{iteration:07d}_adapters.safetensors`
- File format: **safetensors** (written via `mx.save_safetensors(...)` in `dreambooth.py::save_adapters`)
- Metadata attached: `{"lora_rank": "<rank>", "lora_blocks": "<blocks>"}`

Consequence: the remapper takes safetensors input (not npz), and reads tensors via `safetensors.safe_open(...)` rather than `numpy.load(...)`. The plan's Task 1.3 implementation and tests need updating to reflect this when Task 1.4 lands — `numpy.load` / `np.savez` usage in the fixture must become `safetensors.torch.save_file`.

## Training entrypoint

- **Script path:** `~/Projects/mlx-examples/flux/dreambooth.py`
- **Invocation venv:** `~/.venv/mlx-flux-training/` (installed from `flux/requirements.txt` + `datasets` + `safetensors`)
- **Help:** `python3 dreambooth.py --help` lists all hyperparameters.

Required positional arg: `dataset` — either a filesystem path to a dir containing `train.jsonl` + images, OR a HuggingFace dataset id (e.g., `mlx-community/dreambooth-dog6`).

**Dataset format (HF or local):** `train.jsonl` with lines `{"image": "path", "prompt": "caption"}`. This is **different from** the existing `/sq-lora` skill's paired `.jpg`/`.txt` convention. Task 2.1's `train.py` wrapper (or a preprocess step) must convert paired-file datasets to jsonl when invoking dreambooth.py.

**Key hyperparameters (defaults):**
- `--iterations 600`
- `--batch-size 1`
- `--grad-accumulate 4`
- `--lora-rank 8`
- `--resolution 512 512`
- `--lora-blocks -1` (all blocks; this is significant — see "Block coverage" below)
- `--warmup-steps 100`
- `--learning-rate 1e-4`
- `--checkpoint-every 50`
- `--output-dir mlx_output`

**RAM requirement:** ~50GB peak (empirically observed 48.789 GB peak with rank 4). The README's "~50GB" claim is accurate. M3 Max 128GB is comfortable.

## Observed output shape (toy run)

- Dataset: `mlx-community/dreambooth-dog6` (5 images)
- `--lora-rank 4 --iterations 50 --grad-accumulate 1 --warmup-steps 10 --lora-blocks -1 --model dev`
- Training walltime after warmup settled: ~0.225 it/s (~4.4s/iteration)
- Final safetensors: **77 MB** (rank 4, 608 trainable-tensor keys)
- Training 18.258M parameters at rank 4
- Adapter metadata: `{'lora_rank': '4', 'lora_blocks': '-1'}`

Progress image at iteration 0 was generated but no mid-training progress renders (I set `--progress-every 1000`). No issues.

## Key naming convention — MLX native

The trained safetensors contains **exactly 22 distinct module-path patterns**, covering both double-block and single-block LoRA targets.

### Double blocks (10 target modules per block)

```
double_blocks.{N}.img_attn.proj.lora_a
double_blocks.{N}.img_attn.proj.lora_b
double_blocks.{N}.img_attn.qkv.lora_a
double_blocks.{N}.img_attn.qkv.lora_b
double_blocks.{N}.img_mlp.layers.0.lora_a
double_blocks.{N}.img_mlp.layers.0.lora_b
double_blocks.{N}.img_mlp.layers.2.lora_a
double_blocks.{N}.img_mlp.layers.2.lora_b
double_blocks.{N}.img_mod.lin.lora_a
double_blocks.{N}.img_mod.lin.lora_b
double_blocks.{N}.txt_attn.proj.lora_a
double_blocks.{N}.txt_attn.proj.lora_b
double_blocks.{N}.txt_attn.qkv.lora_a
double_blocks.{N}.txt_attn.qkv.lora_b
double_blocks.{N}.txt_mlp.layers.0.lora_a
double_blocks.{N}.txt_mlp.layers.0.lora_b
double_blocks.{N}.txt_mlp.layers.2.lora_a
double_blocks.{N}.txt_mlp.layers.2.lora_b
double_blocks.{N}.txt_mod.lin.lora_a
double_blocks.{N}.txt_mod.lin.lora_b
```

### Single blocks (3 target modules per block)

```
single_blocks.{N}.linear1.lora_a
single_blocks.{N}.linear1.lora_b
single_blocks.{N}.linear2.lora_a
single_blocks.{N}.linear2.lora_b
single_blocks.{N}.modulation.lin.lora_a
single_blocks.{N}.modulation.lin.lora_b
```

**Note lowercase `.lora_a` / `.lora_b`** — not `.lora_A` / `.lora_B`, not `.lora_down` / `.lora_up`. Task 1.2's keymap YAML regexes must match lowercase.

**Block count inference:** with `--lora-blocks -1` on dev: 608 keys / 2 (a/b) / 13 avg modules/block ≈ 23 blocks. Flux-dev has 19 double blocks + 38 single blocks; 19×10 + 38×3 = 190 + 114 = 304 keys × 2 (a/b) = 608. ✓

## Shape convention — critical for remapper transpose logic

### MLX convention (observed)

| Module | lora_a shape | lora_b shape |
|---|---|---|
| `img_attn.proj` | `(3072, 4)` | `(4, 3072)` |
| `img_attn.qkv` | `(3072, 4)` | `(4, 9216)` |
| `img_mlp.layers.0` | `(3072, 4)` | `(4, 12288)` |
| `img_mlp.layers.2` | `(12288, 4)` | `(4, 3072)` |
| `img_mod.lin` | `(3072, 4)` | `(4, 18432)` |

General pattern: **`lora_a` is `(input_dim, rank)`** and **`lora_b` is `(rank, output_dim)`**.

### Kohya convention (target, per mflux's `flux_lora_mapping.py`)

- `lora_down.weight` shape: `(rank, input_dim)`
- `lora_up.weight` shape: `(output_dim, rank)`

### Transpose requirement

MLX `lora_a` → Kohya `lora_down`: **transpose axes [0, 1]**. `(input_dim, rank)` → `(rank, input_dim)`.

MLX `lora_b` → Kohya `lora_up`: **transpose axes [0, 1]**. `(rank, output_dim)` → `(output_dim, rank)`.

Both direction tensors need transpose when remapped. Task 1.2's keymap YAML should set `transpose: true` on **every** rule.

## Name translation table (for Task 1.2 keymap)

The Kohya convention mflux consumes has the form `lora_unet_{path}.lora_{down,up}.weight`, with all `.` in the module path replaced by `_`. Mapping:

| MLX source | Kohya target |
|---|---|
| `double_blocks.{N}.img_attn.proj.lora_a` | `lora_unet_double_blocks_{N}_img_attn_proj.lora_down.weight` |
| `double_blocks.{N}.img_attn.proj.lora_b` | `lora_unet_double_blocks_{N}_img_attn_proj.lora_up.weight` |
| `double_blocks.{N}.img_attn.qkv.lora_a` | `lora_unet_double_blocks_{N}_img_attn_qkv.lora_down.weight` |
| `double_blocks.{N}.img_attn.qkv.lora_b` | `lora_unet_double_blocks_{N}_img_attn_qkv.lora_up.weight` |
| `double_blocks.{N}.img_mlp.layers.0.lora_a` | `lora_unet_double_blocks_{N}_img_mlp_0.lora_down.weight` |
| `double_blocks.{N}.img_mlp.layers.0.lora_b` | `lora_unet_double_blocks_{N}_img_mlp_0.lora_up.weight` |
| `double_blocks.{N}.img_mlp.layers.2.lora_a` | `lora_unet_double_blocks_{N}_img_mlp_2.lora_down.weight` |
| `double_blocks.{N}.img_mlp.layers.2.lora_b` | `lora_unet_double_blocks_{N}_img_mlp_2.lora_up.weight` |
| `double_blocks.{N}.img_mod.lin.lora_a` | `lora_unet_double_blocks_{N}_img_mod_lin.lora_down.weight` |
| `double_blocks.{N}.img_mod.lin.lora_b` | `lora_unet_double_blocks_{N}_img_mod_lin.lora_up.weight` |
| `double_blocks.{N}.txt_attn.proj.lora_a` | `lora_unet_double_blocks_{N}_txt_attn_proj.lora_down.weight` |
| `double_blocks.{N}.txt_attn.proj.lora_b` | `lora_unet_double_blocks_{N}_txt_attn_proj.lora_up.weight` |
| `double_blocks.{N}.txt_attn.qkv.lora_a` | `lora_unet_double_blocks_{N}_txt_attn_qkv.lora_down.weight` |
| `double_blocks.{N}.txt_attn.qkv.lora_b` | `lora_unet_double_blocks_{N}_txt_attn_qkv.lora_up.weight` |
| `double_blocks.{N}.txt_mlp.layers.0.lora_a` | `lora_unet_double_blocks_{N}_txt_mlp_0.lora_down.weight` |
| `double_blocks.{N}.txt_mlp.layers.0.lora_b` | `lora_unet_double_blocks_{N}_txt_mlp_0.lora_up.weight` |
| `double_blocks.{N}.txt_mlp.layers.2.lora_a` | `lora_unet_double_blocks_{N}_txt_mlp_2.lora_down.weight` |
| `double_blocks.{N}.txt_mlp.layers.2.lora_b` | `lora_unet_double_blocks_{N}_txt_mlp_2.lora_up.weight` |
| `double_blocks.{N}.txt_mod.lin.lora_a` | `lora_unet_double_blocks_{N}_txt_mod_lin.lora_down.weight` |
| `double_blocks.{N}.txt_mod.lin.lora_b` | `lora_unet_double_blocks_{N}_txt_mod_lin.lora_up.weight` |
| `single_blocks.{N}.linear1.lora_a` | `lora_unet_single_blocks_{N}_linear1.lora_down.weight` |
| `single_blocks.{N}.linear1.lora_b` | `lora_unet_single_blocks_{N}_linear1.lora_up.weight` |
| `single_blocks.{N}.linear2.lora_a` | `lora_unet_single_blocks_{N}_linear2.lora_down.weight` |
| `single_blocks.{N}.linear2.lora_b` | `lora_unet_single_blocks_{N}_linear2.lora_up.weight` |
| `single_blocks.{N}.modulation.lin.lora_a` | `lora_unet_single_blocks_{N}_modulation_lin.lora_down.weight` |
| `single_blocks.{N}.modulation.lin.lora_b` | `lora_unet_single_blocks_{N}_modulation_lin.lora_up.weight` |

**Every row has `transpose: true` in the keymap.** All 22 module patterns are present in mflux's `FluxLoRAMapping.get_mapping()` target list (verified by cross-reference against `sidequest-daemon/.venv/lib/python3.14/site-packages/mflux/models/flux/weights/flux_lora_mapping.py` — the class covers both BFL-format `lora_unet_double_blocks_*` and BFL-format `lora_unet_single_blocks_*` patterns).

## Quirks and footnotes

- **`lora_blocks` metadata is `-1`** when all blocks are trained. Values 0 and above restrict to a subset of blocks; the remapper should pass through whatever it sees without interpreting it.
- **Progress images at iter 0** are generated even if training has done nothing — this is the reference "before" image. Helpful if you want to manually compare LoRA effect later.
- **First iteration is slow** (~8s) while MLX warms up Metal graph compilation; subsequent iterations settle to ~4s each at rank 4 on this hardware.
- **Progress PNG path is inside the output dir** — the remapper must not treat every file under `output_dir` as an adapter; filter by extension `.safetensors`.
- **Checkpoint filename pattern:** `{iteration:07d}_adapters.safetensors` plus `final_adapters.safetensors`. If `checkpoint-every` divides `iterations` cleanly, the last numbered checkpoint and `final_adapters.safetensors` are byte-identical.

## Plan corrections deriving from this doc

1. **Remapper input type:** plan Tasks 1.3, 1.4, 1.5 use `np.savez` / `np.load` fixtures. These must use `safetensors` instead when Task 1.4 lands the happy-path fixture. Task 1.3's current implementation reads `.npz` via `np.load`; the function signature stays the same but the internal reader must be swapped.
2. **Dataset format conversion:** plan Task 2.1 assumes paired `.jpg`+`.txt` datasets. Mlx-examples wants `train.jsonl`. Either the `train.py` wrapper generates the jsonl at dispatch time (preferred — non-invasive to the `/sq-lora` skill's convention), or the skill migrates to jsonl natively.
3. **Output filename pattern in plan Task 2.1's `build_training_command`:** the `--output` arg in `train.py`'s CLI must point at a directory (not a stem), because mlx-examples writes into `{output_dir}/final_adapters.safetensors` and intermediate `{output_dir}/{iteration:07d}_adapters.safetensors`. The "output stem" idea in the plan doesn't map onto mlx-examples' file-naming.

Task 1.4 folds these corrections in.

## Next

- Unblocks plan Task 1.2 (write `scripts/lora/mlx_to_mflux_keymap.yaml` — 44 rules from the table above)
- Unblocks plan Task 1.4 (remapper happy-path fixture + test)
- Unblocks plan Task 1.5 (end-to-end render proof)
- Unblocks plan Task 2.1 update (dataset-format conversion + output-dir semantics)
