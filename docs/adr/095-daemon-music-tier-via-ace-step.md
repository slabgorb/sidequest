---
id: 95
title: "Daemon Music Tier via ACE-Step"
status: accepted
date: 2026-05-10
deciders: ["Keith Avery"]
supersedes: []
superseded-by: null
related: [35, 38, 45, 46, 82]
tags: [media-audio, transport-infrastructure]
implementation-status: live
implementation-pointer: null
---

# ADR-095: Daemon Music Tier via ACE-Step

## Status

Accepted — 2026-05-10. Implemented on branch `feat/daemon-music-tier`.

## Context

The original architecture (per pre-2026-05 CLAUDE.md and the historical
client audio engine in ADR-045) treated music as **pre-rendered at build
time** — files baked into the content repo, played back from disk by either
the client or the daemon's now-deleted `sidequest_daemon/audio/` mixer
module. That mixer module had no production callers and was removed in
the same branch as this ADR.

Two events changed the architecture:

1. **Sprint 45-49 (LFS strip)** removed binary audio from the
   `sidequest-content` repo. What remains under
   `genre_packs/<pack>/audio/music/` are per-track ACE-Step parameter JSON
   files (`<track>_input_params.json`).
2. **R2 migration** moved durable assets to Cloudflare R2 at
   `cdn.slabgorb.com`. The image render path already uploads daemon
   outputs to R2 and returns `r2_key`; music had no equivalent path.

The "daemon doesn't run music inference" doctrine was correct when
ACE-Step lived in a separate sibling project and the daemon was image-only.
Both conditions changed: ACE-Step is pip-installable, the daemon already
owns GPU lifecycle (ADR-046, since retired), and the R2 upload pattern is
established by `r2_writer.upload_artifact`.

## Decision

ACE-Step joins Flux/Z-Image as a daemon media tier. Routing keys off the
existing `tier` field in the dispatch protocol (`tier="music"`).

- **Source of truth.** `sidequest-content/genre_packs/<pack>/audio/music/<track>_input_params.json`.
  Operators author the JSON; daemon never writes to it.
- **R2 key derivation.** Deterministic from JSON file location:
  `genre_packs/<pack>/audio/music/<track>.ogg`. Both the daemon
  (`MusicPipeline.derive_r2_key` in `music_pipeline.py`) and the
  orchestrator script (`discover_jobs` + `_GENRE_PACKS_RE` in
  `scripts/generate_music.py`) use the same regex
  `r".*?(genre_packs/.*?)/audio/music/(.+?)_input_params\.json$"`.
  If the layout ever changes, both sites must move together.
- **Trigger.** Explicit operator command via `python scripts/generate_music.py --genre <pack>`
  (the `sq-music` skill / music-director agent wrap this). No idle
  detection, no scheduled cron, no GM-panel button. Re-render with `--force`.
- **Output codec.** OGG container, **Opus** at 96 kbps (`ffmpeg -c:a libopus -b:a 96k`).
  Picked over libvorbis q4 because the standard Homebrew ffmpeg build
  ships libopus by default but not libvorbis; Opus also produces smaller
  files at equivalent quality. Content-type `audio/ogg`, file extension
  `.ogg` — the OGG container with Opus codec is the standard combo for
  music streaming.
- **GPU coordination.** Music acquires the existing `render_lock`
  (the image-render lock) — no separate music lock for v1. Cold-swap
  between Flux/Z-Image and ACE-Step happens lazily on the first request
  of the alternate type. The shared-lock design avoids deadlock
  complexity at the cost of cold-swap latency on workload alternation.
- **Manifest.** `audio.yaml` remains the runtime catalog (titles, BPM,
  mood mappings) and is human-authored. The daemon never writes to it.
  Manifest paths (`path: audio/music/<track>.ogg`) and R2 layout align
  by convention because R2 key derivation is mechanical.
- **Watcher events.** Every job emits OTEL events:
  `music.generation.start` (with `r2_key`, `prompt_excerpt`, `duration_s`,
  `json_params_path`), `music.generation.complete` (with `elapsed_ms`,
  `inference_ms`, `ffmpeg_ms`, `upload_ms`, `seed`, `file_size_bytes`),
  and on failure `music.generation.failed` (with `error_code`, `stage`
  ∈ `{params, inference, ffmpeg, upload}`, `detail`).

## Consequences

**Positive:**
- LFS-stripped audio for all five packs (`caverns_and_claudes`,
  `elemental_harmony`, `mutant_wasteland`, `space_opera`, `victoria`)
  can be regenerated from existing JSON params with one `--genre`
  invocation each.
- New tracks are added by dropping a JSON file + `audio.yaml` entry —
  no Python edits, no `GENRE_MOODS` dict to extend.
- R2 upload reuses the established image path
  (`r2_writer.upload_pack_asset`, sibling to `upload_artifact`).
- Orphaned `sidequest_daemon/audio/` module (~1500 LOC) deleted in
  the same branch (`5118d6c`), along with the dead
  `sidequest_daemon/ml/memory_manager.py` (zero callers).
- Watcher events make the music tier visible to the GM panel — when
  Claude narrates "the combat theme rises," OTEL can confirm whether
  any music actually rendered.

**Negative:**
- Daemon now juggles two model families; cold-swap latency (~10–15s)
  on workload alternation.
- ACE-Step is a non-trivial pip dependency tree (spacy, datasets,
  librosa, pytorch_lightning, accelerate). The daemon is pinned to
  Python 3.12 because those upstreams lack 3.13 wheels.
- v1 explicit-only trigger means operators must remember to run the
  script after editing JSON params (mitigated by the `sq-music` skill
  flow).

**Neutral / future:**
- A dedicated `music_lock` and an idle-detected trigger could come
  later if cold-swap or operator burden becomes painful.
- If a fourth ML backend is ever added, the GPU memory budget
  coordinator (ADR-046, retired) may need to come back — but the
  implementation in that ADR was unused and is not what should be
  revived.

## Alternatives considered

- **Keep music separate (status quo).** Rejected — leaves operator
  with a manual ACE-Step UI workflow, doesn't solve LFS-strip
  restoration, leaves orphaned `audio/` mixer module in place.
- **`MediaPipeline` abstraction (image and music as parallel
  implementations).** Rejected — premature decomposition; abstraction
  earns its keep at three+ generative tiers, we have two.
- **Separate music daemon process.** Rejected — duplicates R2
  plumbing and GPU coordination; the existing image daemon already
  owns the Unix-socket transport (ADR-035) and the model-warmup
  lifecycle.
- **Vorbis instead of Opus.** Considered — would have matched the
  pre-existing `wav_to_ogg` codec on the orchestrator script. Rejected
  because Homebrew's stock ffmpeg ships libopus but not libvorbis, and
  Opus is the modern preferred codec for music streaming. The OGG
  container handles both transparently.

## Implementation footprint

- `sidequest-daemon/sidequest_daemon/media/music_pipeline.py` — `MusicPipeline.derive_r2_key`, `MusicPipeline.generate`, `_run_ffmpeg`, `_tempdir`
- `sidequest-daemon/sidequest_daemon/media/ace_step_adapter.py` — `prepare_inference_params`, `AceStepAdapter`, `InferenceResult`
- `sidequest-daemon/sidequest_daemon/media/r2_writer.py` — `upload_pack_asset` (sibling to `upload_artifact`)
- `sidequest-daemon/sidequest_daemon/media/pipeline_factory.py` — `MediaPipelineFactory.init_music`
- `sidequest-daemon/sidequest_daemon/media/daemon.py` — `MUSIC_TIERS`, `dispatch_request`, `_handle_client` short-circuit
- `sidequest-daemon/sidequest_daemon/telemetry/watcher_bridge.py` — daemon → server OTEL bridge (used by music watcher events)
- `scripts/generate_music.py` — `discover_jobs`, `is_in_r2`, `filter_jobs_by_track`, `send_render(json_path)`, refactored `main()`

## References

- Spec: `docs/superpowers/specs/2026-05-09-daemon-between-session-music-generation-design.md`
- Plan: `docs/superpowers/plans/2026-05-10-daemon-between-session-music-generation.md`
- ADR-035 — Unix Socket IPC for Python Sidecar
- ADR-038 — WebSocket Transport Architecture
- ADR-045 — Client Audio Engine (historical context)
- ADR-046 — GPU Memory Budget Coordinator (retired in same window)
- ADR-082 — Port `sidequest-api` from Rust back to Python
