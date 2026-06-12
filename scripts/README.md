# `scripts/` — Orchestrator Cross-Repo Scripts

Operator-run scripts for the SideQuest orchestrator: asset rendering and
publishing, playtest drivers, usage reporting, and ADR/content-tooling
migrations. These coordinate across the subrepos (`sidequest-server`,
`sidequest-content`, `sidequest-daemon`) and are **run by hand**, not on the
critical path.

> **Two virtualenvs, on purpose.** Most render scripts import the server's genre
> loader and run under `--project sidequest-server`. The **R2 publish** scripts
> need `boto3`, which lives in the **orchestrator-root** `pyproject.toml`, *not*
> in `sidequest-server`. Run those under `--project .` (orchestrator root). Mixing
> these up is the most common "module not found" failure here.

## Asset rendering & publishing

The pipeline is **render locally → sync to R2**. The media daemon renders one
image at a time over a Unix socket (`/tmp/sidequest-renderer.sock`), so there is
no benefit to firing render scripts in parallel — they just fight over the
socket. Run render jobs **sequentially**.

| Script | venv | Purpose |
|--------|------|---------|
| `generate_portrait_images.py` | `sidequest-server` | Render NPC/character portraits for a genre/world from its `portrait_manifest.yaml` |
| `generate_poi_images.py` | `sidequest-server` | Render Point-of-Interest landscapes from a world's POI visual prompts |
| `generate_creature_images.py` | `sidequest-server` | Render creature/monster art |
| `generate_image_sheets.py` | `sidequest-server` | Compose contact/preview sheets from rendered images |
| `render_common.py` | — | Shared helpers imported by the `generate_*` scripts (not run directly) |
| `grab_stills.py` | `sidequest-server` | Capture stills (e.g. for previews/QA) |
| `r2_sync_packs.py` | **`.` (root)** | Publish rendered assets to R2 (`cdn.slabgorb.com`) |
| `r2_audit.py` / `r2_verify_packs.py` / `r2_manifest.py` | **`.` (root)** | Audit, verify, and list R2 pack contents |
| `generate_music.py` | `sidequest-server` | Operator-triggered ACE-Step music generation → R2 (ADR-095) |

### Render gotchas (hard-won — read before a long render run)

- **Steps.** Render quality scales with `--steps`. The default is **20**
  (raised from 15, PR #320). Production asset passes this session used `--steps 40`.
- **`--force` skips the R2-existence pre-check.** The `generate_*` scripts can
  short-circuit if an asset already exists in R2; pass `--force` to re-render
  regardless. (The existence check itself needs `boto3` — another reason the
  render scripts and the sync scripts have different venv expectations.)
- **Renders read the *current git working tree* of `sidequest-content`.** If a
  world's prompts live on an unmerged branch, check that branch out **before**
  the render reaches that job. **Never switch branches in `sidequest-content`
  while a render is mid-flight** — the next job will read the wrong files. For
  parallel content/doc edits during a render, use a `git worktree`, never a
  branch switch in the live checkout.
- **R2 sync `--files` paths.** When syncing an explicit file list, paths must be
  **absolute** or relative to `--content-root`, **not** the current working
  directory.

### Example: render then publish one world's POIs

```bash
# 1. render POIs at 40 steps (server venv), forcing re-render
uv run --project sidequest-server python scripts/generate_poi_images.py \
    --genre space_opera --world aureate_span --steps 40 --force

# 2. publish the rendered PNGs to R2 (ROOT venv — boto3 lives here)
uv run --project . python scripts/r2_sync_packs.py \
    --genre space_opera --world aureate_span
```

### Multi-job runs: `render_queue.py`

For gap-closing runs spanning several worlds, `render_queue.py` chains render and
sync jobs **strictly in sequence** (one daemon, one socket), stops on the first
failure, and prints an explicit upload payload before each sync. Jobs are
`kind:genre:world` where `kind` ∈ {`portraits`, `pois`, `sync`}; run it under the
`sidequest-server` project (it shells out to the root venv itself for sync steps).

```bash
# render @40 then publish, across worlds, sequentially:
uv run --project sidequest-server python scripts/render_queue.py --steps 40 \
    portraits:tea_and_murder:blackthorn_moor \
    pois:tea_and_murder:blackthorn_moor \
    sync:tea_and_murder:blackthorn_moor \
    pois:space_opera:coyote_star \
    sync:space_opera:coyote_star
```

`render_queue.py` defaults `--steps` to **40** (production asset quality) — note
this differs from the underlying `generate_*.py` default of 20; pass `--steps N`
to override. The runner forces re-render by default; pass `--no-force` to respect
the R2-existence short-circuit.
See the module docstring for the full job grammar and the branch-safety warning
(it reads the `sidequest-content` working tree — see the gotchas above).

### Lift a whole world's asset gate: `render_world_assets.sh`

`render_queue.py` is for hand-picked jobs. When you just want **one world's full
image gate** (every POI + every portrait, uploaded, manifest rebuilt) in a single
command, use the batch wrapper. It runs the two `generate_*` scripts in sequence
against the local daemon, then rebuilds `r2_manifest.json` from a live bucket scan.

```bash
just daemon            # the renders need the local MLX daemon up — fail-loud if not
scripts/render_world_assets.sh mutant_wasteland seaboard_of_saints           # full gate → R2
scripts/render_world_assets.sh space_opera perseus_cloud --steps 40 --force  # extra flags pass through
scripts/render_world_assets.sh space_opera coyote_star --no-upload           # local test render, R2 untouched
```

- Always invoke via the **shell script**, not bare `python3` — it routes each step
  through the right venv (the R2/manifest steps need `boto3` from the root env).
- Logs tee to `~/.sidequest/logs/render-<genre>-<world>-<stamp>.log`.
- It does **not** lift `draft: true`. That's a deliberate human step in
  `worlds/<world>/world.yaml` *after* you've eyeballed the rendered set.

### Watch the render across boxes: the live R2 preview gallery

A render fanning out across two Macs uploads to one R2 bucket, so neither box's
local contact sheet sees the whole picture — but the CDN does. `generate_r2_preview.py`
emits a self-contained `image_sheets/r2_preview.html` that points an `<img>` at the
**CDN URL** of every *expected* asset (derived from the manifests, not local dirs).
Not-yet-rendered tiles render as "pending" rather than hidden — the point is seeing
what's still missing. A live `rendered / expected` counter, 30s cache-bust
auto-refresh (new uploads from either box appear without a reload), and a
click-to-zoom lightbox are built in.

```bash
uv run python scripts/generate_r2_preview.py --open               # everything, open in browser
uv run python scripts/generate_r2_preview.py --genre heavy_metal  # one pack
uv run python scripts/generate_r2_preview.py --world evropi --kind poi
```

Leave the tab open while a batch runs; it self-refreshes. Keys are derived from the
same manifest collectors the renderers use, so a "pending" tile is a genuine gap,
not a path mismatch.

### Audio: `render-pd-audio` (public-domain) and `generate_music.py` (ACE-Step)

Image gate and audio gate are separate. For the public-domain music a world's
`audio.yaml` demands, the reconciler renders `demand ∩ catalog ∖ already-in-R2`:

```bash
just render-pd-audio --pack wry_whimsy            # or --dry-run / --force
```

For ACE-Step generated tracks, `generate_music.py` walks a pack's
`audio/music/*_input_params.json` and dispatches each to the daemon (→ R2):

```bash
uv run --project sidequest-server python scripts/generate_music.py --genre heavy_metal           # all missing
uv run --project sidequest-server python scripts/generate_music.py --genre heavy_metal --track combat
```

### Where am I? Audit the gaps

Before and after a run, `r2_audit.py` diffs the YAML-derived "should exist" key set
against `r2_manifest.json`, reporting authored-but-not-rendered,
rendered-but-not-uploaded, and orphan keys (root venv — needs `boto3`). The
`/sq-audit` skill wraps this for a pack/world/asset completeness sweep.

## Playtest & observability

| Script | Purpose |
|--------|---------|
| `playtest.py` | Headless playtest driver (interactive, scripted, multiplayer modes) against a running server |
| `playtest_dashboard.py` | OTEL dashboard / GM-panel viewer |
| `playtest_otlp.py` | OTLP receiver for playtest telemetry |
| `playtest_messages.py` | Playtest message helpers |
| `anthropic_usage.py` | Report Anthropic API token usage |

## ADR & content tooling

| Script | Purpose |
|--------|---------|
| `regenerate_adr_indexes.py` | Regenerate the auto-generated ADR index blocks (ADR-088) |
| `validate_adr_frontmatter.py` | Validate ADR frontmatter against the schema (ADR-088) |
| `migrate_adr_frontmatter.py` | One-shot ADR frontmatter migration |
| `migrate_poi_backdrop_lod.py` | One-shot POI backdrop LOD migration |
| `migrate_portrait_manifest_lods.py` | One-shot portrait-manifest LOD migration |
| `migrate_visual_tag_overrides.py` | One-shot visual-tag-override migration |

`tests/` holds the pytest suite for these scripts (e.g. playtest fixture-flag
wiring). Run with `uv run --project sidequest-server python -m pytest scripts/tests`.
