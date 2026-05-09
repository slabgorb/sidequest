# Daemon Between-Session Music Generation

**Date:** 2026-05-09
**Author:** Architect/Dev (brainstorm — Major Houlihan & Major Winchester, MASH theme)
**Status:** approved-design — pending writing-plans
**Scope:** `sidequest-daemon`, `scripts/generate_music.py`, `sidequest_daemon/audio/` deletion, ADR-NNN, content-pack JSON params authoring contract

## 1. Context

### 1.1 What broke

A wiring audit on 2026-05-09 found that no audio plays in the game. The proximate cause looked like a wiring bug, but on inspection the pipeline is correctly wired — there are simply no audio files for it to deliver:

- Sprint commit `ab62b42` ("sidequest-content LFS strip") stripped binary audio from the content repo
- Project storage subsequently moved from Git LFS to Cloudflare R2 (`cdn.slabgorb.com`)
- Server-side `LibraryBackend.resolve()` correctly returns `None` for every track lookup
- `_maybe_dispatch_audio()` in `websocket_session_handler.py` correctly skips `AUDIO_CUE` emission
- OTEL emits `audio.skipped reason=empty_cues` on every turn (the lie detector is working)
- Client correctly plays nothing, because nothing is sent

### 1.2 Three half-built pieces, none fully connected

The audit also surfaced that infrastructure for music generation already exists in three places, none of which line up:

1. **`scripts/generate_music.py`** (~330 LOC) — sends `{"tier": "music", ...}` to the daemon, converts WAV→OGG, writes to local `genre_packs/<pack>/audio/music/`. Has a baked-in `GENRE_MOODS` dict as the source of truth.
2. **Daemon dispatch** — `daemon.py:329-335` only routes `IMAGE_TIERS`. A `tier=music` request currently raises `ValueError("Unknown tier: 'music'")`. No ACE-Step import anywhere in the daemon (`grep -r ace_step sidequest-daemon/sidequest_daemon` returns 0 hits).
3. **Content-side `*_input_params.json` files** — full ACE-Step inference configs (prompt, lyrics, duration, scheduler params, seeds, plus historical `timecosts`) sit alongside the now-stripped audio files. These look like exports from ACE-Step's standalone tooling and represent the actual params used historically. `audio_path` field hardcoded to a stale `/Users/keithavery/...` path.
4. **R2 upload pipeline** — fully working for image renders (`sidequest-server/sidequest/server/asset_urls.py`, `websocket_session_handler.py:4516+`). Daemon uploads → returns `r2_key` → server resolves to URL via `resolve_artifact_url`. Neither the script nor the missing music tier touches it.

### 1.3 What this spec resolves

A unified between-session music generation pipeline using the daemon, R2, and the per-track JSON params files as the canonical source of truth. Replaces the `GENRE_MOODS` dict, deletes the orphaned `sidequest_daemon/audio/` module, restores stripped audio by re-running existing JSON params.

### 1.4 Decisions taken during brainstorm

| Q | Decision | Implication |
|---|---|---|
| Purpose | Continuous library expansion | Daemon executes JSON params authors drop in; both restoration and new authoring use the same flow |
| Trigger | Explicit only | No idle detection. Operator runs the script. |
| Trigger source | `sq-music` skill (and the script underneath) | Single trigger surface; no GM-panel button, no admin REST endpoint |
| Source of truth | `<track>_input_params.json` files in content packs | The script's hardcoded `GENRE_MOODS` dict dies |
| Implementation shape | Minimal music tier alongside images (Approach X) | No `MediaPipeline` abstraction, no separate sidecar process |

## 2. Goals & non-goals

### 2.1 Goals

- The daemon supports `tier=music` requests via ACE-Step, alongside existing image tiers
- The script walks per-pack JSON params files and dispatches one daemon job per missing track
- Generated audio lands in R2 at the same path the runtime resolver expects
- The first run after merge restores the stripped audio for all five existing packs that have JSON params
- Adding a new track requires editing `audio.yaml` + dropping a JSON params file + running the script — no Python edits
- The orphaned `sidequest_daemon/audio/` module (~1500 LOC, zero callers) is deleted in the same PR

### 2.2 Non-goals

- **Idle/scheduled triggers.** Explicit-only this iteration. Idle detection can come later if it earns its keep.
- **GM-panel UI button.** Sebastien-grade visibility comes through OTEL watcher events, not a new button.
- **Adaptive evolution.** The daemon does not infer what's missing; authors decide by writing JSON params.
- **`MediaPipeline` abstraction.** Premature for one image pipeline + one music pipeline.
- **Audio.yaml mutation by the daemon.** Manifest stays human-authored. Path convention does the cross-referencing.
- **Daemon-side audio playback.** The orphaned mixer module is removed; client plays audio via WebAudio per the existing pipeline.
- **Music streaming / on-demand inference at game time.** Generation is offline-only, between sessions.

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  Author / sq-music skill                                            │
│  • Edits <pack>/audio.yaml (path: audio/music/<track>.ogg)          │
│  • Drops <pack>/audio/music/<track>_input_params.json               │
│  • Runs `python scripts/generate_music.py --genre <pack>`           │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  scripts/generate_music.py  (refactored — dict deleted)             │
│  • Walks **/audio/music/*_input_params.json under the pack          │
│  • For each: derives expected R2 key from JSON file's path          │
│  • HEAD against cdn.slabgorb.com — skip if already present          │
│  • Sends {"method":"render", "params":{                             │
│       "tier":"music", "json_params_path":"<abs path>"}}             │
│    to the daemon's Unix socket                                      │
│  • Logs r2_key per track; exits non-zero if any job failed          │
└────────────────────────────────────────────────────────────────────┘
                                 │   /tmp/sidequest-renderer.sock
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  sidequest-daemon  (new tier branch in existing dispatch)           │
│  • IF tier in MUSIC_TIERS: route to music_pipeline                  │
│  • music_pipeline.generate(json_params_path):                       │
│      1. Acquire GPU via ADR-046 coordinator (yields image models)   │
│      2. Lazy-load ACE-Step (warm cache after first request)         │
│      3. Read JSON params, override audio_path → tempfile.wav        │
│      4. Run ACE-Step inference → WAV                                │
│      5. FFmpeg WAV → OGG (libvorbis q4)                             │
│      6. Upload OGG to R2 at derived key                             │
│      7. publish_event("music.generation.complete", {...})           │
│      8. Return {r2_key, duration_ms, seed, elapsed_ms}              │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  R2 (cdn.slabgorb.com)                                              │
│  • genre_packs/<pack>/audio/music/<track>.ogg                       │
│  • Resolved at runtime by asset_urls.resolve_asset_url()            │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  Game runtime  (NO CHANGES)                                         │
│  Server interprets narration → LibraryBackend.resolve() →           │
│    AUDIO_CUE → client fetches from R2                               │
└────────────────────────────────────────────────────────────────────┘
```

**Key invariant:** the JSON params file's location on disk is the contract. A file at
`genre_packs/cav/audio/music/combat_input_params.json` means the audio MUST land at R2 key
`genre_packs/cav/audio/music/combat.ogg`. The daemon derives this from the request, so the
stale `audio_path` field inside the JSON is ignored.

## 4. Components

### 4.1 Daemon: `music_pipeline` module (new)

New file `sidequest_daemon/media/music_pipeline.py`. Mirrors the shape of the existing image pipeline factory but with a single backend.

```python
class MusicPipeline:
    def __init__(self, *, gpu_coordinator, r2_client, telemetry):
        self._coordinator = gpu_coordinator   # ADR-046
        self._r2 = r2_client                  # reused from image path
        self._telemetry = telemetry
        self._model = None                    # lazy-loaded ACE-Step

    async def generate(self, json_params_path: Path) -> MusicResult:
        # acquire GPU, load model if cold, run inference, ffmpeg, upload
        ...
```

`MUSIC_TIERS = {"music"}` constant added near `IMAGE_TIERS` in `daemon.py`. Dispatch extends to:

```python
if tier in IMAGE_TIERS:
    ...image branch (unchanged)...
elif tier in MUSIC_TIERS:
    result = await music_pipeline.generate(Path(params["json_params_path"]))
    return {
        "r2_key":       result.r2_key,
        "duration_ms":  result.duration_ms,
        "seed":         result.seed,
        "elapsed_ms":   result.elapsed_ms,
    }
else:
    raise ValueError(f"Unknown tier: {tier!r}")  # no silent fallback
```

### 4.2 ACE-Step adapter: `sidequest_daemon/media/ace_step_adapter.py` (new)

Thin wrapper over the ACE-Step package. One reason to isolate it:

- Reads JSON params, overrides `audio_path` to a tempfile, sets `format="wav"` regardless of JSON
- Strips output fields (`timecosts`, `actual_seeds[1:]`, `retake_seeds`) before passing to the pipeline
- **Seed contract (single rule, no fallback):** the seed is `actual_seeds[0]` from the JSON. If absent or non-integer, the daemon returns `{"error": {"code": "MISSING_SEED"}}`. Authors must pin a seed for reproducibility — implicit randomness is a footgun for "why does this track sound different now?"

This is the only place that knows ACE-Step's API. Swap-out cost is contained if ACE-Step ever changes.

### 4.3 R2 client extension

The image render path uses an existing R2 client. Music reuses it. The only new affordance needed: an upload method that takes a local file path and a target R2 key, returns success/failure. If the existing client already exposes this for images, we use it as-is. If not, one method is added.

### 4.4 Refactored `scripts/generate_music.py`

Current script is ~330 lines; refactored target is ~120 lines.

**Delete:**
- `GENRE_MOODS` dict
- `VARIATION_SUFFIXES` dict
- `compute_seed()` function
- `wav_to_ogg()` function
- `--mood`, `--variation`, `--duration` CLI flags (no longer meaningful — JSON params own these)

**Keep:**
- daemon socket connection helpers (`send_render`, `check_daemon`)
- `--genre`, `--dry-run` CLI args

**New:**
- `discover_jobs(genre_dir)` — walks `**/audio/music/*_input_params.json`, returns `[(json_path, expected_r2_key), ...]`
- `is_in_r2(r2_key)` — HEAD against `<asset_base_url>/<r2_key>` where `asset_base_url` honors the same `SIDEQUEST_ASSET_BASE_URL` env var that `asset_urls.resolve_asset_url()` uses (default: `https://cdn.slabgorb.com`). Public read; no auth.
- `--force` flag bypasses the R2 skip check for re-renders
- `--track <stem>` filter — runs only the job whose JSON params file matches `<stem>_input_params.json`. Fixes the "one bad track" iteration case without --force-everything.

**Refactored main loop:** for each job, skip if in R2, else send to daemon, collect r2_keys, print summary.

### 4.5 `sq-music` skill / music-director agent (doc update only)

`.claude/commands/sq-music.md` and `.claude/agents/music-director.md` get a content rewrite reflecting:

- JSON params files are the canonical authoring artifact (not the `GENRE_MOODS` dict)
- The agent's job is helping authors **write good ACE-Step prompts** + drop the JSON file + edit `audio.yaml`
- The agent never edits Python; it edits content-repo YAML and JSON
- Running `scripts/generate_music.py --genre <pack>` is the final step

Bundled with this PR.

## 5. Data flow

### 5.1 Request shape (script → daemon)

```json
{
  "id": "music-cav-combat-1715284800",
  "method": "render",
  "params": {
    "tier": "music",
    "json_params_path": "/abs/path/to/genre_packs/cav/audio/music/combat_input_params.json"
  }
}
```

Daemon reads the JSON file fresh on each request. No script-side caching of params; editing the JSON re-renders next invocation.

### 5.2 Reply shape (daemon → script)

```json
{
  "id": "music-cav-combat-1715284800",
  "result": {
    "r2_key":      "genre_packs/cav/audio/music/combat.ogg",
    "duration_ms": 64500,
    "seed":        2082,
    "elapsed_ms":  67200
  }
}
```

`elapsed_ms` includes ACE-Step inference + FFmpeg + R2 upload. `duration_ms` is the audio's own playback length. `seed` echoes back JSON's `actual_seeds[0]` or whatever was used.

### 5.3 Daemon execution

```
1. Dispatch routes tier=music → music_pipeline.generate(json_params_path)
2. publish_event("music.generation.start", {r2_key, prompt_excerpt, duration_s, json_params_path})
3. coordinator.acquire_for("ace_step")
   - if image model loaded: unload, free VRAM (publish music.gpu.swap)
   - first call: load ACE-Step (~10-15s cold-start)
4. ace_step_adapter.run(json_params_path, output=tmpfile.wav)
   - reads JSON, strips output fields, overrides audio_path
   - runs inference (~real-time per the historical timecosts)
5. ffmpeg -i tmpfile.wav -c:a libvorbis -q:a 4 tmpfile.ogg
   - delete .wav on success
6. r2_client.upload(tmpfile.ogg, r2_key)
   - delete .ogg on success
7. publish_event("music.generation.complete", {r2_key, elapsed_ms, inference_ms, ffmpeg_ms, upload_ms, seed, file_size_bytes})
8. return reply
```

### 5.4 R2 key derivation rule

Single, deterministic, no exceptions:

```
JSON path:  genre_packs/<pack>/audio/music/<name>_input_params.json
R2 key:     genre_packs/<pack>/audio/music/<name>.ogg
```

Strip the trailing `_input_params.json`, append `.ogg`. The directory containing the JSON file under `genre_packs/` is the relative R2 path. If the file isn't under a `genre_packs/<pack>/` ancestor, the daemon **errors loudly** with `INVALID_PARAMS_LOCATION` — no silent fallback.

### 5.5 Skip-if-present logic

The script's `is_in_r2(r2_key)` issues an unauthenticated HTTP HEAD against `<asset_base_url>/<r2_key>`, where `asset_base_url` is read from `SIDEQUEST_ASSET_BASE_URL` with the same default (`https://cdn.slabgorb.com`) used by the server's `asset_urls.resolve_asset_url()`. R2 returns 200 if present, 404 if not. The bucket is publicly readable per the existing image flow, so no SDK or credentials are required for the script-side check.

`--force` bypasses the check for re-renders (e.g. after editing a JSON's prompt). `--track <stem>` narrows the discovery to one job.

### 5.6 R2 credentials

Write access to R2 is held by the daemon, not the script. The daemon reads R2 credentials from its environment (same env vars used by the existing image upload path). The script never touches credentials — it only HEADs the public CDN URL and tells the daemon to do the upload. This keeps the trust boundary at the daemon process and means the script can run from any developer environment without secrets.

## 6. Error handling

### 6.1 Daemon-side failures

| Failure | Handling | Reply |
|---|---|---|
| `json_params_path` doesn't exist | Reject before GPU acquire | `{"error": {"code": "PARAMS_NOT_FOUND", "path": "..."}}` |
| Path not under `genre_packs/` | Reject — can't derive R2 key | `{"error": {"code": "INVALID_PARAMS_LOCATION"}}` |
| ACE-Step model load fails | Loud — daemon can't serve music until investigated | `{"error": {"code": "MODEL_LOAD_FAILED", "detail": "..."}}` + log + watcher event |
| ACE-Step inference fails | Per-job — recoverable, GPU released | `{"error": {"code": "INFERENCE_FAILED", "detail": "..."}}` |
| Missing/non-integer `actual_seeds[0]` | Reject before GPU acquire | `{"error": {"code": "MISSING_SEED"}}` |
| FFmpeg conversion fails | Per-job | `{"error": {"code": "FFMPEG_FAILED", "stderr": "..."}}` |
| R2 upload fails | Retry once with backoff, then fail per-job | `{"error": {"code": "R2_UPLOAD_FAILED", "attempts": 2}}` |
| GPU coordinator can't acquire | Wait up to 30s (configurable); then fail | `{"error": {"code": "GPU_BUSY"}}` |

**No silent fallbacks.** Tempfiles are cleaned in `try/finally` regardless of outcome.

### 6.2 Script-side failures

The script processes jobs sequentially (ACE-Step holds GPU exclusively). Per-job failures are collected, not raised:

```
generated: 12
skipped (in R2):  8
failed: 2
  - cav/audio/music/combat_input_params.json: INFERENCE_FAILED — "CUDA OOM"
  - vic/audio/music/scandal_input_params.json: PARAMS_NOT_FOUND — "..."
```

**Exit code:** `0` if all generated/skipped; `1` if any failed.

### 6.3 Daemon dies mid-job

The script's `asyncio.open_unix_connection` raises `ConnectionResetError`. Caught per-job, recorded as `failure: DAEMON_DISCONNECTED`. The script does not auto-retry — daemon health is a separate concern; rerun after fixing.

### 6.4 Race against active session

Out of scope. Trigger is explicit-only; the operator runs the script when no session is active. If a session connects mid-generation, the in-flight job completes; the GPU coordinator swaps models for the session's first image request afterward (paying a cold-swap cost). Acceptable for an explicit operator action.

### 6.5 R2 partial state

R2 uploads are atomic per object. If upload fails, the local OGG tempfile is deleted in `finally`, the job is marked failed, the script continues. Next run picks the same job up again.

## 7. Testing

### 7.1 Daemon unit tests (`sidequest-daemon/tests/`)

| Test | What it verifies |
|---|---|
| `test_music_pipeline_derives_r2_key` | JSON path → R2 key derivation, including reject-non-genre-pack-paths |
| `test_music_pipeline_strips_output_fields` | Adapter strips `timecosts`, `actual_seeds[1:]`, `retake_seeds`; preserves `actual_seeds[0]` as seed |
| `test_music_pipeline_overrides_audio_path` | Stale `/Users/keithavery/...` path replaced with daemon-controlled tempfile |
| `test_dispatch_routes_music_tier` | Dispatch routes `tier=music` to music_pipeline; image branch unchanged (regression check) |
| `test_dispatch_unknown_tier_still_loud` | `tier=foo` still raises `ValueError` (no silent fallback) |
| `test_music_pipeline_cleans_tempfiles_on_failure` | Inference / FFmpeg / upload failures all leave no tempfile residue |
| `test_music_pipeline_emits_watcher_events` | `start`/`complete` fire on success path; `failed` fires on every error path with correct `stage` field |
| `test_music_pipeline_releases_gpu_on_failure` | Coordinator's release is in `finally`, not just on success |

ACE-Step is mocked at the adapter boundary — no GPU needed in unit tests.

### 7.2 Script unit tests

| Test | What it verifies |
|---|---|
| `test_discover_jobs_walks_genre_pack` | Fixture pack with 3 JSON params files → 3 jobs with correct R2 keys |
| `test_discover_jobs_handles_world_subpacks` | `<pack>/worlds/<world>/audio/music/` either supported or explicitly excluded for v1 (decision documented) |
| `test_skip_if_in_r2` | HEAD 200 → skipped; HEAD 404 → sent |
| `test_force_flag_bypasses_r2_check` | `--force` re-renders even if present |
| `test_summary_exit_code` | Any failed job → exit code 1 |

### 7.3 Integration test (daemon + adapter, no real ACE-Step)

`test_music_dispatch_end_to_end_mocked.py` — spins the daemon dispatch with a mock ACE-Step adapter that writes a known sine-wave WAV. Verifies the full path: socket request → dispatch → mock inference → real FFmpeg → mock R2 upload → reply with r2_key.

### 7.4 Wiring test

`test_music_tier_is_actually_dispatched.py` — proves the music branch is reachable from the script's actual request shape. Sends an exact request that the production script would build, asserts the dispatch routes to `music_pipeline` (not the `ValueError` branch). The test that prevents another deferral cascade.

### 7.5 Manual smoke (one-off, release checklist)

```bash
just daemon                                              # start daemon
python scripts/generate_music.py --genre caverns_and_claudes --dry-run
# verify discovered job list looks right
python scripts/generate_music.py --genre caverns_and_claudes
# verify R2 keys appear at https://cdn.slabgorb.com/genre_packs/caverns_and_claudes/audio/music/...
# verify the next game session plays the new tracks
```

## 8. OTEL coverage

### 8.1 Watcher events

All published via `publish_event(...)` (the established API at `sidequest.telemetry.watcher_hub`). The daemon reaches the watcher hub through the same path the image pipeline uses; if that bridge is itself broken (audit flagged a `sidequest_daemon.telemetry` ImportError silently swallowed at `daemon.py:719-733`), repairing it is a sibling task and a prerequisite for this design's OTEL claims.

| Event | Component | Payload | When |
|---|---|---|---|
| `music.generation.start` | `daemon.music` | `{r2_key, prompt_excerpt[120], duration_s, json_params_path}` | Immediately after dispatch routing, before GPU acquire |
| `music.gpu.swap` | `daemon.gpu` | `{from_model, to_model, swap_ms}` | When the coordinator unloads image to load ACE-Step (or vice versa) |
| `music.generation.complete` | `daemon.music` | `{r2_key, elapsed_ms, inference_ms, ffmpeg_ms, upload_ms, seed, file_size_bytes}` | After successful R2 upload |
| `music.generation.failed` | `daemon.music` | `{r2_key, error_code, stage, detail}` (stage ∈ params/gpu/inference/ffmpeg/upload) | Any error path |
| `music.skipped.in_r2` | `script.music` | `{r2_key}` | Script side — when HEAD returns 200 |
| `music.batch.summary` | `script.music` | `{generated, skipped, failed, total_elapsed_s}` | End of script run |

### 8.2 OTEL spans

Standard OTEL spans wrap each daemon stage (parallels the existing `daemon.dispatch.render` pattern at `daemon.py:756`):

```
daemon.dispatch.music
├── music.acquire_gpu
├── music.inference            (ace-step duration)
├── music.ffmpeg               (wav→ogg duration)
└── music.r2_upload            (network duration, file_size)
```

### 8.3 Lie-detector value

- **Cold-swap surprises** — `music.gpu.swap` events show how often we're paying the swap cost
- **Stage attribution** — `music.generation.failed.stage` field tells the operator immediately whether ACE-Step itself, FFmpeg, or R2 is the bottleneck
- **Skip vs generate ratio** — over a batch, the watcher events show "I generated 3, skipped 17"; confirms the script is doing what it claims
- **Sebastien-grade visibility** — music generation appears as a first-class subsystem in the GM panel's Subsystems tab

### 8.4 What does NOT need OTEL

- The script's job-discovery walk (just file IO, not a decision)
- Tempfile cleanup (not a subsystem decision)
- R2 client authentication (handled by the existing client)

## 9. Deletions

### 9.1 Hard deletes

| Item | Path | Why |
|---|---|---|
| `GENRE_MOODS` dict | `scripts/generate_music.py` | Duplicates content-side JSON params |
| `VARIATION_SUFFIXES` dict | `scripts/generate_music.py` | Variations live in JSON params files now |
| `compute_seed()` | `scripts/generate_music.py` | Seed read from JSON's `actual_seeds[0]` |
| `wav_to_ogg()` | `scripts/generate_music.py` | Conversion moves into the daemon next to inference |
| Consumers of JSON's `audio_path` field | (any) | Daemon ignores it — derives output path from JSON file's location |

### 9.2 Soft deletes — orphaned daemon audio module (~1500 LOC)

Audit-flagged module with zero non-test consumers. Deleted in this same PR.

| Item | Path | Why |
|---|---|---|
| pygame mixer | `sidequest_daemon/audio/mixer.py` | Daemon never plays audio — client does |
| Duplicate interpreter | `sidequest_daemon/audio/interpreter.py` (306 LOC) | Server already has `sidequest/audio/interpreter.py` |
| Async cue queue | `sidequest_daemon/audio/queue.py` | Nothing produces or consumes |
| Path resolver | `sidequest_daemon/audio/library_backend.py` | Server has its own `LibraryBackend` |
| Theme rotation | `sidequest_daemon/audio/rotator.py` | Unused |
| AudioBackend interface | `sidequest_daemon/audio/protocol.py` | No implementations called |
| Data models | `sidequest_daemon/audio/models.py` | No consumers |
| `init_audio()` call site | `pipeline_factory.py` | Constructs the orphaned mixer; deletion is the inverse |

The new `music_pipeline.py` lives at `sidequest_daemon/media/music_pipeline.py` (next to image pipeline siblings), not under `audio/` — that directory belonged to the playback misfeature.

### 9.3 Retained intentionally

| Item | Why kept |
|---|---|
| Server-side `sidequest/audio/interpreter.py` | Production path — narrator text → mood detection runs on the server |
| Server-side `LibraryBackend` | Resolves paths at request-time during play |
| `audio.yaml` files in genre packs | Runtime catalog with titles + BPM + mood mappings |
| Per-track `*_input_params.json` files | Now the canonical generation spec |

### 9.4 Stale references to update (not deletions)

- `sidequest-content/CLAUDE.md` — "binary assets are tracked with Git LFS" → reference R2
- Orchestrator `CLAUDE.md` — "Music is pre-rendered at build time… no runtime music inference lives here" → soften per the new ADR
- Daemon `CLAUDE.md` — same line about no runtime music inference
- ADR-046 (GPU memory budget coordinator) — add ACE-Step as a documented client (one paragraph)

### 9.5 New ADR

`docs/adr/0NN-daemon-music-tier-via-ace-step.md` (number assigned at write-time — next free in the sequence). Formalizes the architectural shift: ACE-Step joins Flux/Z-Image as a daemon media tier; supersedes the "build-time pre-render" doctrine in CLAUDE.md; references this design spec; cross-links ADR-035 (Unix socket IPC), ADR-046 (GPU coordinator), and (historical) ADR-045.

## 10. Migration & author workflow

### 10.1 New authoring workflow — adding a track

```
1. Decide:  pack=heavy_metal, mood=funeral, variation=dirge
2. Edit  sidequest-content/genre_packs/heavy_metal/audio.yaml:
     mood_tracks:
       funeral:
         - path: audio/music/funeral_dirge.ogg
           title: "Mourn the Pact"
           bpm: 50
3. Create  sidequest-content/genre_packs/heavy_metal/audio/music/funeral_dirge_input_params.json:
     {
       "task": "text2music",
       "format": "wav",
       "prompt": "doom metal funeral march, detuned guitars, slow ...",
       "lyrics": "[inst]",
       "audio_duration": 60,
       "infer_step": 60,
       "guidance_scale": 15,
       "scheduler_type": "euler",
       "actual_seeds": [42]
     }
4. Run  python scripts/generate_music.py --genre heavy_metal
       → script discovers funeral_dirge_input_params.json
       → HEAD checks R2 — not present
       → sends to daemon
       → daemon generates, converts, uploads
       → done
5. Commit JSON params + audio.yaml edit. No binary committed — R2 is the store.
```

### 10.2 Iterating on a track

```
1. Edit the prompt in <track>_input_params.json
2. Run  python scripts/generate_music.py --genre <pack> --force
       → re-renders despite R2 having an existing object
       → R2 overwrites at the same key
       → next session plays the new version
```

### 10.3 Restoration after the LFS strip

The 30-some `*_input_params.json` files already in the content repo are the historical record. The very first run of:

```bash
python scripts/generate_music.py --genre caverns_and_claudes
python scripts/generate_music.py --genre elemental_harmony
python scripts/generate_music.py --genre mutant_wasteland
python scripts/generate_music.py --genre space_opera
python scripts/generate_music.py --genre victoria
```

regenerates every track that previously lived in LFS, lands them in R2, restores audio playback. **No content authoring needed** — the existing JSONs do the job.

### 10.4 Per-machine path issue

The current JSON files have `"audio_path": "/Users/keithavery/Projects/oq-2/..."` — stale paths from another machine. The daemon ignores this field entirely (overrides to its own tempfile), so **no per-machine cleanup is needed**.

### 10.5 What does NOT change

- Game runtime: server interprets narration → resolves path → AUDIO_CUE → client fetches. The added piece is upstream of all of this.
- Multiplayer: `AUDIO_CUE` broadcast remains shared-world per ADR-037.
- UI audio engine: same WebAudio playback. The audit's separate `useAudioCue` promise-rejection-swallowing finding is a sibling P1 bug, not part of this design.

### 10.6 Spoiler-protection note

`mutant_wasteland/flickering_reach` is the only "fully spoilable" world. Music params there are no different from any other pack; same workflow applies.

## 11. Open questions

These are deferred to writing-plans / implementation, not blockers for this design:

1. **Is ACE-Step pip-installable as a regular dependency, or does the daemon need to import it from a sibling project?** Project lives at `~/Projects/ACE-Step` with `ace_step.egg-info`. If pip-installable: add to `pyproject.toml`. If not: vendor or use a sibling-path PYTHONPATH trick. Resolution belongs in the implementation plan.
2. **World-level audio.yaml** — `caverns_and_claudes/worlds/caverns_sunden/audio.yaml` exists. Does the script walk worlds too, or v1 supports pack-level only? Default position: pack-level only for v1; worlds get a follow-up.
3. **R2 cache invalidation on `--force` re-render** — does Cloudflare R2's CDN edge cache need explicit purge, or do object-version semantics handle it? Verify against existing image re-render behavior.
4. **Watcher-event bridge for the daemon** — pre-existing audit finding (`sidequest_daemon.telemetry` ImportError silently swallowed). This design assumes the bridge works. If it does not, the OTEL section degrades to OTLP-only and a sibling fix is needed first.

## 12. References

- **ADR-035** — Unix Socket IPC for Python Sidecar
- **ADR-046** — GPU Memory Budget Coordinator
- **ADR-045** — Client Audio Engine (historical)
- **ADR-082** — Port `sidequest-api` from Rust back to Python
- `sidequest-server/sidequest/server/asset_urls.py` — R2 URL resolution
- `sidequest-server/sidequest/server/websocket_session_handler.py:4516+` — image r2_key handling pattern (template for music)
- `sidequest-daemon/sidequest_daemon/media/daemon.py:329-335` — current dispatch (target for music tier branch)
- `scripts/generate_music.py` — current script (target for refactor)
- `~/Projects/ACE-Step` — ACE-Step project (Python package)
- `~/.cache/ace-step` — model cache
