---
description: Generate ACE-Step audio tracks for genre packs
---

# Music Generation

Generate music tracks using the ACE-Step worker in the sidequest-renderer daemon. Per-track JSON params files in `sidequest-content/genre_packs/<pack>/audio/music/*_input_params.json` are the canonical generation spec. The daemon reads them, runs ACE-Step, converts WAV → OGG, and uploads to R2 at `genre_packs/<pack>/audio/music/<track>.ogg`.

## Authoring a new track

1. Edit `sidequest-content/genre_packs/<pack>/audio.yaml` — add the entry under `mood_tracks.<mood>` (or whichever block applies) with `path: audio/music/<track>.ogg`, `title:`, and `bpm:`.
2. Create `sidequest-content/genre_packs/<pack>/audio/music/<track>_input_params.json` — full ACE-Step config with at minimum:
   - `task: "text2music"`
   - `prompt:` (genre+mood+instrumentation description)
   - `lyrics: "[inst]"` for instrumentals
   - `audio_duration:` (seconds)
   - `actual_seeds: [<int>]` (pinned for reproducibility)
3. Run `python scripts/generate_music.py --genre <pack>` — the script discovers the JSON, sends each `json_params_path` to the daemon, daemon uploads OGG to R2.
4. Iterate with `--track <stem>` for one-job runs, `--force` to overwrite an existing R2 object after editing the prompt.

The daemon owns ACE-Step; you never edit Python.

## Parameters

| Param | Description | Default |
|-------|-------------|---------|
| `--genre <slug>` | Genre pack to walk | *required* |
| `--track <stem>` | Only generate this track (file stem, e.g. `combat`) | all missing |
| `--force` | Re-render even if R2 already has the OGG | false |
| `--dry-run` | List discovered jobs without sending | false |

## Usage

```bash
# Generate all missing tracks for a pack
python scripts/generate_music.py --genre caverns_and_claudes

# Single track
python scripts/generate_music.py --genre caverns_and_claudes --track combat

# Re-render after editing the prompt
python scripts/generate_music.py --genre caverns_and_claudes --track combat --force

# Preview discovered jobs without hitting the daemon
python scripts/generate_music.py --genre caverns_and_claudes --dry-run
```

## Prerequisites

- **Daemon must be running:** `just daemon`. Watch for `MusicPipeline initialized` in the log.
- ACE-Step model lazy-loads on first music render (~10-15s cold-swap from image tier).
- `ffmpeg` with libopus encoder (Homebrew core ffmpeg ships this by default).

## Request shape

The script sends:

```json
{"id":"music-<stem>-<ts>","method":"render","params":{"tier":"music","json_params_path":"<abs path>"}}
```

The daemon replies with:

```json
{"id":"...","result":{"r2_key":"genre_packs/<pack>/audio/music/<track>.ogg","duration_ms":60000,"seed":42,"elapsed_ms":67000}}
```

## Output

- **Format:** OGG container, Opus codec, ~96 kbps
- **Location:** R2 — `https://cdn.slabgorb.com/genre_packs/<pack>/audio/music/<track>.ogg`
- **Skip rule:** the script HEADs the CDN; if the object exists it skips unless `--force` is given.

## Audio config

`audio.yaml` is the runtime catalog (titles, BPM, mood mappings) and is human-authored — the daemon never writes to it. R2 key derivation is deterministic from the JSON file location, so manifest paths and R2 layout align by convention. Example:

```yaml
mood_tracks:
  combat:
    - path: audio/music/combat.ogg
      title: "The Keeper's Wrath"
      bpm: 132
```

## Notes

- ACE-Step generation takes ~60-90s per 60s track (cold) and ~real-time (~30-60s) once warm.
- Seeds are pinned in `actual_seeds` for reproducibility — same JSON params + same seed → identical track.
- All five LFS-stripped packs (`caverns_and_claudes`, `elemental_harmony`, `mutant_wasteland`, `space_opera`, `victoria`) regenerate from their JSON params with one `--genre` invocation each.

## Owned by

**Music Director** agent (`music-director`). Run after authoring `*_input_params.json` files; the script discovers them.
