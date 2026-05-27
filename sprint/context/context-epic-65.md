# Epic 65: Content Infrastructure — R2 asset tracking and audit

## Overview

Establish a checked-in source of truth for what binary assets exist in R2, a
YAML-derived gap audit that catches authored-but-unrendered (and orphaned)
assets, and a cross-clone pull so a fresh checkout can hydrate local media from
just the committed YAML + manifest. This replaces the prior git-LFS pointer
approach for the dual-repo (OQ-1 / OQ-2) workflow.

**Priority:** P1
**Repo:** orchestrator (tooling in `scripts/`); the `r2_manifest.json` data
artifact is committed under `sidequest-content/`
**Stories:** 3 (9 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **CLAUDE.md** (`CLAUDE.md`) | Media daemon / R2 upload (ADR-095); "single source of truth" for content; no-silent-fallbacks |
| **r2_sync_packs.py** (`scripts/r2_sync_packs.py`) | Existing uploader — `sync()`, `iter_media_files`, `_md5_of`, 1:1 key mirror |
| **r2_verify_packs.py** (`scripts/r2_verify_packs.py`) | Existing presence-verifier — HEAD every key via cdn.slabgorb.com |

## Background

The dual-repo workflow splits rendering across two clones: OQ-1 renders
portraits, OQ-2 renders POIs. Generated PNGs/OGGs are gitignored, and
`git pull local` only syncs YAML. Neither clone can tell what the other has
already produced and uploaded to R2, so assets get re-rendered, missed, or
silently orphaned.

The existing tooling covers only half the loop: `r2_sync_packs.py` uploads
local media to R2 (idempotent via MD5-vs-ETag), and `r2_verify_packs.py` HEADs
every *local* file against the CDN. There is no committed record of what is in
R2 independent of a local checkout, and no way to diff *authored intent*
(YAML definitions) against *rendered reality* (what was actually uploaded).

This epic closes that loop: a committed manifest (the durable record), an audit
(intent-vs-reality diff), and a pull (hydrate a clone from the record).

## Technical Architecture

R2 mirrors local paths 1:1 — `r2_sync_packs.sync()` sets `key = rel.as_posix()`
relative to `sidequest-content/`. The authoritative key conventions, **derived
from the generators (not from prose specs)**, are:

| Asset | Source of truth (YAML) | R2 key (== local rel path) |
|-------|------------------------|----------------------------|
| POI landscape | `history.yaml` → `chapters.*.points_of_interest.*.slug` | `genre_packs/<genre>/worlds/<world>/assets/poi/<slug>.png` |
| Portrait | `portrait_manifest.yaml` → `characters.*.name` (or `.id`) | `genre_packs/<genre>/images/portraits/<slug>.png` (genre-flat) |
| Music | `audio/music/<track>_input_params.json` | `genre_packs/<genre>/audio/music/<track>.ogg` |

Slugs come from `render_common.slugify` / `generate_portrait_images._slugify_name`
and `render_common.render_batch`'s path rules (`image_subdir="poi"` →
`worlds/<world>/assets/poi/`; other subdirs → genre-flat `images/<subdir>/`).
**Any audit that reconstructs keys must reuse this logic, not hardcode the
path strings** — the strings in earlier story prose were wrong.

**Component pipeline:**

```
generators (generate_poi_images / generate_portrait_images / generate_music)
      │  produce local PNG/OGG
      ▼
r2_sync_packs.sync()  ──writes──▶  sidequest-content/r2_manifest.json  (committed)
      │  uploads to R2                         │
      ▼                                        ▼
   R2 bucket                          r2_audit.py: expected(YAML) ⊖ manifest
                                               │
                                               ▼
                                   gaps report + non-zero exit
```

**Key files:**
- `scripts/r2_sync_packs.py` (existing) — extend to emit manifest entries
- `scripts/r2_manifest.py` (new) — boto3-free manifest build/write/load
- `scripts/r2_audit.py` (new) — YAML-derived expected-key set + diff + report
- `scripts/r2_pull.py` (new, nice-to-have) — hydrate local files from manifest
- `sidequest-content/r2_manifest.json` (new committed artifact)

**Testability constraint:** `r2_sync_packs.py` imports `boto3` at module top,
and `boto3` is absent from the orchestrator's deps — so even the existing
`scripts/tests/test_r2_sync_packs.py` cannot be collected. New manifest/audit
*logic* must live in boto3-free modules so it is testable without AWS deps;
`boto3` must be added to the orchestrator dev dependencies to test the
`sync()` integration at all.

## Cross-Epic Dependencies

**Depends on:**
- Existing R2 sync/verify tooling (`scripts/r2_sync_packs.py`,
  `scripts/r2_verify_packs.py`) and the generator path logic in
  `scripts/render_common.py`.

**Depended on by:**
- Story 65-2 (per-session asset ledger) — consumes the manifest concept for
  runtime-generated images.
- Story 65-3 (pulp-noir visual_style cleanup) — independent content work; no
  hard dependency.
