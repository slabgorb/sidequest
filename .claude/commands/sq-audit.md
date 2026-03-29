---
description: Audit genre packs, worlds, and assets for completeness gaps
---

# Genre Pack Audit

Check completeness of genre packs, worlds, and their assets. Reports missing files, empty sections, POI gaps, music gaps, voice preset gaps, and asset gaps.

## Parameters

| Param | Description | Default |
|-------|-------------|---------|
| `--genre <name>` | Audit only this genre pack | all genres |
| `--world <name>` | Audit only this world | all worlds |
| `--section <name>` | Audit only this section (see below) | all sections |
| `--dry-run` | Same as default — audit is read-only | true (always) |

## Usage

```bash
# Full audit of everything
/sq-audit

# One genre
/sq-audit --genre elemental_harmony

# One world
/sq-audit --genre elemental_harmony --world shattered_accord

# Just check POIs
/sq-audit --section poi

# Just check music
/sq-audit --section music
```

## Audit Sections

### `files` — Required YAML Files

Checks each world has the required files:
- `world.yaml` (REQUIRED)
- `lore.yaml` (REQUIRED)
- `cartography.yaml`
- `history.yaml`
- `legends.yaml`
- `cultures.yaml`
- `tropes.yaml`

Checks each genre has:
- `pack.yaml`, `rules.yaml`, `lore.yaml`, `visual_style.yaml`, `audio.yaml`, `theme.yaml`
- `cultures.yaml`, `archetypes.yaml`, `char_creation.yaml`, `progression.yaml`
- `inventory.yaml`, `tropes.yaml`, `prompts.yaml`

### `history` — Campaign History Completeness

Per world:
- Number of chapters (expect 3-4: fresh/early/mid/veteran)
- Per chapter: has character? has NPCs? has quests? has POIs? has tropes?
- Chapters without `points_of_interest` are flagged

### `poi` — Points of Interest vs Images

Per genre:
- Total POIs defined in history.yaml files
- Total images in `images/poi/`
- Gap count (POIs without images)
- Lists specific missing images

### `music` — Audio Tracks vs Moods

Per genre:
- Moods defined in `audio.yaml` → `mood_tracks` or `themes`
- Variation types expected (full, ambient, sparse, tension_build, resolution, overture)
- Actual `.ogg` files in `audio/music/`
- Gap: moods/variations without tracks

### `voice` — Creature Voice Presets

Per genre:
- Presets defined in `audio.yaml` → `creature_voice_presets`
- Genres with empty `{}` presets flagged
- Genres with no presets at all flagged

### `assets` — Visual Assets

Per genre:
- Fonts in `assets/fonts/` (expect at least one `.woff2`)
- `theme.yaml` references valid font family
- ~~Dinkus and drop caps are deprecated — now CSS-based, no image assets needed~~

### `conlang` — Naming Compliance

Per world:
- Does `cultures.yaml` exist?
- Are settlement/landmark names in cartography using conlang patterns?
- Flags English descriptive names in `name` fields (should be in `description` only)

## Output Format

```
=== GENRE: elemental_harmony ===

[files] ✓ Genre pack: 14/14 required files
[files] ✗ World shattered_accord: missing history.yaml
[files] ✓ World burning_peace: 7/7 files

[history] ✓ burning_peace: 2 chapters, 6 POIs
[history] ✗ shattered_accord: NO history.yaml

[poi] ✓ 6 POIs, 6 images, 0 gaps
[poi] ✗ shattered_accord: 0 POIs (no history)

[music] ✗ No tracks in audio/music/
[voice] ✗ No creature_voice_presets defined
[assets] ✓ Font: Noto Serif JP
[conlang] ✓ Names follow culture patterns
```

## Notes

- Audit is always read-only — it never modifies files
- Use audit output to prioritize `/sq-world-builder` DM prep work
- Run after world creation to verify completeness before playtest

## Owned By

**World Builder** agent (`/sq-world-builder`). Run as first step of any DM prep session.
