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
