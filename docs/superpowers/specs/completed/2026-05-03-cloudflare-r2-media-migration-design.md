# Cloudflare R2 Media Migration — Design

**Author:** DevOps (Miracle Max persona)
**Date:** 2026-05-03
**Status:** Draft, awaiting user review
**Story:** TBD (DevOps initiative; no Jira key yet)

## Summary

Move all curated genre-pack media (audio + images, ~931 MB across 887 files
currently in Git LFS) and all daemon-generated game artifacts out of the
`sidequest-content` repo and into Cloudflare R2 object storage, served via
`https://cdn.slabgorb.com`.

This solves three pains in one move:

1. **LFS pain.** The sidequest-content clone is 19 GB on disk; LFS bandwidth
   quota is finite; clones are slow.
2. **Remote-player distribution.** The playgroup needs media reachable from
   any laptop without depending on Keith's machine being up.
3. **Game-artifact overflow.** Daemon-generated portraits/POIs/music currently
   accumulate on disk under `~/.sidequest/` with no managed lifecycle.

The migration is **byte-for-byte under the existing layout**
(`genre_packs/<genre>/...`). A separate, follow-up story (filed in task
tracker) will restructure to a world-first content layout consistent with the
SOUL.md principle "Crunch in the Genre, Flavor in the World" — but not now.
That restructure is real curatorial work and deserves its own design.

## Out of Scope

- World-first content reorganization (filed: task #7)
- Local on-disk cache for offline play (filed: task #8)
- Any change to the rules side of genre packs (`*.yaml` config files stay in
  Git, where they belong as code)
- Migration of save-file URLs to a different layout (only relevant if/when
  the follow-up restructure ships)
- Backfilling pre-migration generated artifacts from existing on-disk
  `~/.sidequest/renders` etc. into R2 (treat them as legacy; new generations
  go to R2)

## Infrastructure Already in Place

Verified during design via the management API token
(`CLOUDFLARE_API_TOKEN_SIDEQUEST`) and S3 keys (`R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY`):

- Cloudflare account: `a55aafa9b0691f828cd6864be28c1674`
- R2 bucket: `sidequest` (created 2026-04-27, currently empty)
- S3 endpoint: `https://a55aafa9b0691f828cd6864be28c1674.r2.cloudflarestorage.com`
- DNS zone: `slabgorb.com` (managed by Cloudflare)
- R2 custom domain: `cdn.slabgorb.com` — SSL active, ownership verified,
  CNAME live, end-to-end probe (PUT via S3 keys → GET via `cdn.slabgorb.com`
  → byte-match) confirmed working
- API token scoped: R2 buckets read/write, R2 custom domains read/write,
  zone read, DNS read on `slabgorb.com`
- S3 access key scoped: Object Read & Write, single bucket (`sidequest`).
  ListBuckets correctly denied (least-privilege verified).

## Section 1 — Custom Domain & Bucket Access

### Public read endpoint

`https://cdn.slabgorb.com` resolves to the R2 `sidequest` bucket via
Cloudflare's managed custom-domain mechanism. SSL handled by Cloudflare.
No origin server in play.

The default `pub-29a1119699ec488c903a3dcabbea7476.r2.dev` managed domain
remains disabled. All traffic uses the custom domain.

### CORS rule

The bucket needs explicit CORS rules because the UI's `AudioCache.ts` uses
`fetch(url)`, which enforces CORS preflight unlike `<audio>` / `<img>`
elements.

Rule to apply via `aws s3api put-bucket-cors`:

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": [
        "http://localhost:5173",
        "http://localhost:8765",
        "https://slabgorb.com",
        "https://*.slabgorb.com"
      ],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "ExposeHeaders": ["ETag", "Content-Length"],
      "MaxAgeSeconds": 86400
    }
  ]
}
```

GET/HEAD only — public domain is read-only by design. Writes use the S3
endpoint with credentials.

### Cache-Control

All curated `genre_packs/` objects get
`Cache-Control: public, max-age=31536000, immutable` at upload time.
Curated assets do not change in place; if a track is replaced, its filename
changes, and the old object is removed via `aws s3 rm`. No invalidation
endpoint needed.

Daemon-generated `artifacts/` objects get
`Cache-Control: public, max-age=86400` (24h). Generated content is content-
addressed (hash filename) so collisions are impossible; the modest TTL is
just to let CDN edges shed cold artifacts faster. Note: this is the *CDN
freshness hint*, not the *storage retention*. The bucket itself has no
lifecycle rule (see §5) — saves can reference these artifacts indefinitely.

## Section 2 — Bucket Layout (Path 2: mirror current)

```
sidequest/                                          (R2 bucket root)
├── genre_packs/                                    ← byte-for-byte mirror
│   ├── caverns_and_claudes/
│   │   ├── audio/music/combat.ogg
│   │   ├── audio/sfx/door_creak.ogg
│   │   ├── images/portraits/wizard_01.png
│   │   └── worlds/dungeon_survivor/audio/town_theme.ogg
│   ├── elemental_harmony/...
│   ├── mutant_wasteland/...
│   ├── space_opera/...
│   └── victoria/...
│
├── artifacts/                                      ← daemon-generated
│   └── <world-slug>/
│       └── <session-uuid>/
│           ├── portraits/<sha256>.png
│           ├── poi/<sha256>.png
│           ├── scenes/<sha256>.png
│           ├── music/<sha256>.ogg
│           └── sfx/<sha256>.ogg
│
└── probes/                                         ← internal smoke tests
    └── (any path)                                  ← never user-visible
```

Two top-level prefixes, by design:

- **`genre_packs/`** — small, curated, deterministic, immutable. Long
  Cache-Control. Pruned by hand or never. **Mirrors the on-disk layout in
  `sidequest-content/genre_packs/` exactly**, so migration is a one-to-one
  byte sync with no path translation.
- **`artifacts/`** — hash-named, world-keyed at the top level. **No
  automatic expiry** — saves reference artifact URLs and SideQuest is built
  for years-long campaigns; reaping artifacts on a timer would break
  portraits in season-old saves. Cost of unbounded retention is trivial
  ($0.015/GB-month past the 10 GB free tier; ~$3/mo at 200 GB). World-first
  from day 1 because daemon generations are inherently bound to a session
  that's bound to a world.

`probes/` exists for one reason: validation scripts can write/delete here
without touching real content.

### URL examples

- Curated: `https://cdn.slabgorb.com/genre_packs/caverns_and_claudes/audio/music/combat.ogg`
- Generated: `https://cdn.slabgorb.com/artifacts/dungeon_survivor/0d8e7f.../portraits/a3f8c1...png`

The `genre_packs/` URL prefix will be rewritten to a world-first shape in the
follow-up restructure story (task #7), at which point a one-time SQL/JSON
migration over save files will translate the legacy URLs.

## Section 3 — Migration Mechanics (LFS → R2)

Two-phase. Production never breaks mid-flight.

### Phase A — Sync (read-only mirror)

A new script `scripts/r2_sync_packs.py` (orchestrator repo) walks
`sidequest-content/genre_packs/` and uploads via boto3.

Behavior:

- Walks recursively, includes only LFS-tracked extensions
  (`.ogg .png .wav .mp3 .jpg .jpeg .webp .flac`)
- For each file, computes local MD5 and HEADs the remote ETag. If they match,
  skip. (Idempotent re-runs.)
- For each upload, sets `Content-Type` from extension and
  `Cache-Control: public, max-age=31536000, immutable`
- Logs every action to `/tmp/r2-sync.log`
- **Fails loudly on any HTTP error** (no silent skips, per CLAUDE.md no-
  silent-fallback rule)
- Reports total bytes moved, count of skipped (already-synced), count of
  uploaded

Estimated runtime: 10-30 minutes for the initial 931 MB depending on uplink.

After Phase A:

- Dev environment unchanged. Server still reads from local
  `SIDEQUEST_GENRE_PACKS`.
- R2 bucket contains a full mirror, ready to serve.
- Git LFS still intact.

A companion `scripts/r2_verify_packs.py` walks the same files locally, HEADs
each via `https://cdn.slabgorb.com/...`, and reports any non-200. Must be
100% green before Phase B.

### Phase B — Cutover

1. Add env var `SIDEQUEST_ASSET_BASE_URL` to `justfile` and `.env.example`
   with default `https://cdn.slabgorb.com`. Unset means local-serve fallback.
2. Server changes (Section 4): central `resolve_asset_url()` function;
   replace direct path emission at all touch points.
3. Verification pass: `just up`, play through a session, watch DevTools
   Network panel filtered to `cdn.slabgorb.com`. Every audio/image fetch hits
   CDN with HTTP 200; no requests to `localhost:8765/genre/*` or `/renders/*`
   for migrated assets.
4. **Only after** step 3 passes in dev: `git lfs migrate export
   --include="*.ogg,*.png,*.wav,*.mp3,*.jpg,*.jpeg,*.webp,*.flac" --everything`
   on `sidequest-content`. Force-push.
5. Coordinate with oq-2 clone: `git fetch && git reset --hard origin/main` in
   the parallel checkout.
6. Keep `.gitattributes` LFS rules in place — defensive, in case media is
   accidentally added in the future. The rules become inert (no LFS-tracked
   files exist), but they will catch a stray future `git add foo.png`.

### Rollback

If Phase B reveals a problem in dev:

- Unset `SIDEQUEST_ASSET_BASE_URL` → server reverts to local file serving.
- Local files still on disk because LFS strip happens *after* successful
  cutover.

If a problem appears *after* LFS strip (e.g., R2 outage):

- LFS objects still recoverable from GitHub LFS storage's tombstones for
  some window, but realistically: pull from R2 back to disk via
  `aws s3 sync s3://sidequest/genre_packs/ ./genre_packs/`. R2 itself is the
  durable source of truth post-cutover.

### Coordination scope

Per user confirmation: only two clones exist (oq-1 primary, oq-2 dual). No
external contributors with sidequest-content checkouts. No CI runners with
historical LFS pulls.

## Section 4 — Server URL Emission & UI Consumption

### The single seam

A new module `sidequest-server/sidequest/server/asset_urls.py`:

```python
import os

_DEFAULT_BASE = "https://cdn.slabgorb.com"

def resolve_asset_url(relative_path: str) -> str:
    """Turn a content-relative path into the URL the UI should fetch.

    relative_path examples:
      "genre_packs/caverns_and_claudes/audio/music/combat.ogg"
      "artifacts/dungeon_survivor/0d8e7f.../portraits/a3f8c1.png"

    With SIDEQUEST_ASSET_BASE_URL=<url> (default https://cdn.slabgorb.com):
      -> "<url>/genre_packs/caverns_and_claudes/audio/music/combat.ogg"

    With SIDEQUEST_ASSET_BASE_URL="" or "local":
      -> "/genre/caverns_and_claudes/audio/music/combat.ogg" (local-serve)
    """
    base = os.environ.get("SIDEQUEST_ASSET_BASE_URL", _DEFAULT_BASE)
    if base in ("", "local"):
        return _local_path_for(relative_path)
    return f"{base.rstrip('/')}/{relative_path.lstrip('/')}"
```

Local-serve fallback for dev/offline. CDN otherwise. Single point of cutover.

### Touch points

| Site | Today emits | After |
|---|---|---|
| `sidequest-server/sidequest/genre/loader.py` `_load_audio_yaml()` | bare path strings | wraps each via `resolve_asset_url()` |
| Wherever Character payload's `portrait_url` is set | local path | `resolve_asset_url("artifacts/<world>/<session>/portraits/<hash>.png")` |
| `sidequest-server/sidequest/server/render_mounts.py` URL emission | `/renders/...` | `resolve_asset_url("artifacts/...")` |
| UI `AudioEngine.playMusic(url)` / `playSfx(url)` | `fetch(url)` | unchanged — already URL-agnostic |
| UI `<img src={portrait_url}>` | local path | unchanged — receives absolute URL from server payload |

### Why one function, not many

- Single point of cutover: rolling back to local-serve is one env var.
- Single point of future migration: changing CDN provider is one default.
- Single point of test coverage: mock `resolve_asset_url` once, every call
  site is covered.

### Daemon write side

The daemon currently writes generated images to disk under `~/.sidequest/`
and `render_mounts.register_root()` mounts the directory for serving.
Post-migration:

- Daemon (or `daemon_client` shim on the server side, depending on which side
  owns the upload) PUTs to
  `s3://sidequest/artifacts/<world>/<session>/<kind>/<sha256>.<ext>` using
  the S3 access key.
- Returns the *relative* artifact path
  (`artifacts/<world>/<session>/<kind>/<sha256>.<ext>`).
- Server runs the relative path through `resolve_asset_url()` before
  emitting to the UI in any protocol payload.
- `register_root()` becomes unused for new generations. Kept in code for
  back-compat reading of pre-migration on-disk artifacts that still exist.

Daemon writes directly to R2 (rather than "daemon writes to disk → server
reads → server uploads") because:

- Avoids a double-trip.
- Daemon is already a sidecar with its own credential surface.
- Failure modes are simpler: if upload fails, daemon returns an error and no
  fake URL gets baked into game state.

The daemon needs `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and
`R2_S3_ENDPOINT` in its environment. The justfile recipes for `just daemon`
already source `.zshrc`-like env via the user shell, so adding these three
exports is enough.

## Section 5 — Daemon Write Integration, Lifecycle, Operations

### Daemon module

New `sidequest-daemon/sidequest_daemon/media/r2_writer.py`:

- Wraps a single boto3 S3 client, configured with R2 endpoint and the access
  key.
- One public function:
  ```python
  def upload_artifact(
      world_slug: str,
      session_id: str,
      kind: Literal["portraits", "poi", "scenes", "music", "sfx"],
      content_bytes: bytes,
      content_type: str,
  ) -> str:
      """Returns the relative path written, e.g.
      'artifacts/dungeon_survivor/0d8e.../portraits/a3f8.png'.
      Raises on any non-2xx (no silent failure).
      """
  ```
- Filename = `sha256(content_bytes)` + correct extension from `content_type`.
- `kind` is a Literal — anything else is a type error caught by mypy and a
  ValueError at runtime. No silent miscategorization.

Existing image-pipeline glue (Flux/Z-Image generators in
`sidequest-daemon/sidequest_daemon/media/`) gains a step at the end of each
generation: call `upload_artifact()` and return the relative path instead
of the disk path.

### OTEL spans

Per CLAUDE.md OTEL Observability Principle, every subsystem decision emits.
Spans to register in the appropriate `SPAN_ROUTES`:

| Span | Emitted | Payload |
|---|---|---|
| `daemon.r2.upload.start` | Before each PUT | `kind, world, session, bytes` |
| `daemon.r2.upload.success` | After 2xx | `kind, key, ms, bytes` |
| `daemon.r2.upload.failure` | On any non-2xx or timeout | `kind, error_class, message, retry_attempt` |
| `server.asset_url.resolved` | Each `resolve_asset_url()` call | `relative_path, base_url, mode (cdn|local)` |

The GM panel needs these so the lie detector works on the asset path:
without them, you can't tell whether the daemon actually uploaded, or whether
a fake URL got baked into the scrapbook.

### R2 lifecycle rule

**No bucket lifecycle rule is applied.** The earlier draft proposed a
90-day expiry on `artifacts/`; that was rejected (2026-05-03). SideQuest is
built for years-long campaigns — a save file that pauses for 18 months and
resumes must still resolve every artifact URL it references. A timed reaper
silently breaks that contract. If unbounded retention ever becomes
expensive enough to matter (it does not at current scale; see "Cost ceiling
check" below), the right design is a save-aware sweep — list active save
files, find unreferenced artifacts, delete only those — not a blunt
date-based rule.

Curated `genre_packs/` was already exempt from the proposed rule and is
similarly retained indefinitely.

Probe-prefix `probes/` is cleaned up by the verification scripts after each
run, not by a bucket rule.

### Cost ceiling check

| Dimension | Estimated | R2 free tier | Headroom |
|---|---|---|---|
| Storage | 931 MB curated + ~2 GB/quarter artifacts (no expiry) | 10 GB | ~3 years before paid tier kicks in |
| Class A ops (writes) | ~200/mo (50 generations × 4 sessions) | 1M | massive |
| Class B ops (reads) | ~2K/mo (4-5 players × 100 assets × 4 sessions) | 10M | massive |
| Egress | $0 always | n/a | n/a |

Operating cost: $0/month at current usage. Past the free tier, R2 storage
is $0.015/GB-month — 200 GB is $3/mo, 1 TB is $15/mo. Trivial relative to
the alternative of breaking portraits in long-paused campaigns.

### Verification plan (post-deploy)

1. **Phase A complete** when `scripts/r2_verify_packs.py` reports 100% of
   local files are reachable through `cdn.slabgorb.com` with HTTP 200.
2. **Phase B complete** when:
   - Full game session played in dev with DevTools Network filtered to
     `cdn.slabgorb.com`, all audio/image fetches return 200.
   - Zero requests to `localhost:8765/genre/*` or `/renders/*` for any
     migrated asset.
   - At least one daemon generation runs end-to-end and the resulting image
     appears in R2 dashboard at the expected `artifacts/<world>/<session>/...`
     path.
3. **OTEL verification:** GM panel shows `daemon.r2.upload.success` and
   `server.asset_url.resolved` spans firing during the test session, with
   `mode=cdn`.
4. **CORS verification:** the `fetch()` calls from `AudioCache.ts` succeed
   (no CORS preflight failures in console).

### Risk register

| Risk | Mitigation |
|---|---|
| LFS strip rewrites history; oq-2 clone needs reset | Coordinated; only 2 clones exist (user confirmed) |
| Daemon upload fails silently → fake URL in scrapbook | OTEL `failure` span + dispatch returns explicit error to server; no fallback to fake URL |
| CDN cache stale after asset rename | Curated assets are immutable by convention; if it bites, purge via Cloudflare API |
| Playgroup laptop on hostile wifi blocks CDN | Edge case; offline cache is filed as follow-up (task #8) |
| `cdn.slabgorb.com` SSL cert lapse | Auto-renewed by Cloudflare; not manual ops |
| Bucket public access misconfig leaks something private | Bucket only ever holds intentionally-public game assets; no PII, no secrets, no save files (saves stay in `~/.sidequest/saves/`) |
| Boto3 dependency added to daemon | Daemon's pyproject already includes HTTP-related deps; boto3 is small (~5MB) and well-supported |
| R2 free tier exhausted (unlikely but possible) | OTEL `daemon.r2.upload.success` payload includes byte count; periodic dashboard check covers it; storage cost beyond free is $0.015/GB-month — trivial |

## Implementation Order

1. **Pre-work in shell** — add `R2_S3_ENDPOINT` to `.zshrc`. Remove orphan
   `R2_ACCESS_KEY` env var (replaced by `R2_ACCESS_KEY_ID/SECRET`).
2. **Apply CORS rule** to `sidequest` bucket via `aws s3api`.
3. ~~Apply lifecycle rule~~ — **dropped 2026-05-03**, see §5 R2 lifecycle rule.
4. **Write Phase A scripts**: `scripts/r2_sync_packs.py`,
   `scripts/r2_verify_packs.py`. Run sync. Run verify. Must be 100% green.
5. **Server work**: introduce `asset_urls.py`, refactor touch points,
   add OTEL `server.asset_url.resolved` span. Tests for each touch point.
6. **Daemon work**: introduce `r2_writer.py`, refactor image-pipeline glue
   to upload + return relative path, add OTEL upload spans. Tests for the
   writer.
7. **Justfile + .env.example**: add `SIDEQUEST_ASSET_BASE_URL` and the three
   `R2_*` env vars to documented templates.
8. **End-to-end verification** in dev: full session, DevTools network audit,
   GM panel OTEL audit.
9. **LFS strip**: only after step 8 is green. Coordinate oq-2 reset.
10. **Cleanup**: revoke unused admin-scope CF tokens (task #6).

## Follow-ups Filed

- **Task #6** — Revoke unused admin-scope CF tokens after this story proves
  out (least-privilege hygiene).
- **Task #7** — Restructure media to world-first layout (the SOUL.md
  "content = world, rules = genre" alignment that was the original user
  request; deferred to keep this story focused).
- **Task #8** — Local on-disk R2 cache for offline play (covers the
  hotel-wifi edge case).

## Acceptance Criteria

The story is done when:

1. R2 bucket `sidequest` contains a complete mirror of all LFS-tracked media
   from `sidequest-content/genre_packs/` under the path layout in Section 2,
   with correct Content-Type and Cache-Control headers.
2. CORS rule is applied. (No lifecycle rule — see §5.)
3. `cdn.slabgorb.com/<key>` returns 200 for every migrated object.
4. Server's `resolve_asset_url()` exists and is used at every asset-emission
   site; no path is emitted that isn't routed through it.
5. UI plays audio and shows images in a full game session with all fetches
   going to `cdn.slabgorb.com`.
6. Daemon writes a generated artifact end-to-end during the same session,
   and the resulting URL is `https://cdn.slabgorb.com/artifacts/<world>/<session>/<kind>/<hash>.<ext>`.
7. OTEL spans `daemon.r2.upload.{start,success,failure}` and
   `server.asset_url.resolved` are visible in the GM panel.
8. `git lfs ls-files` in `sidequest-content` returns empty after the LFS
   strip step.
9. oq-2 clone is reset to match the rewritten history.
10. The repo size of `sidequest-content` shrinks by approximately 931 MB.
