# Epic 12: Cinematic Audio — Score Cue Variations, Soundtrack Pacing

## Vision

SideQuest's soundtrack should feel like a film score, not a video game BGM loop. Each
genre pack already contains overtures, ambient tracks, tension builds, resolutions, and
full orchestrations — a complete score library organized by mood and variation type. The
infrastructure to index and deliver these exists (`AudioTheme`, `AudioVariation`,
`ThemeRotator`) but was never wired into the `MusicDirector`.

This epic connects the dots: the MusicDirector becomes a film score supervisor that picks
the right cue for the right narrative moment.

## Key Insight

This is 90% wired. The `AudioConfig.themes` field is deserialized from `audio.yaml` but
never read. The `ThemeRotator` handles anti-repetition. `MoodClassification.intensity` is
already computed. The missing piece is a variation selection function and the indexing to
connect themes data to the selection pipeline.

## Stories

| ID | Title | Points | Status |
|----|-------|--------|--------|
| 12-1 | Cinematic track variation selection | 5 | ready |
| 12-2 | Per-variation crossfade durations | 2 | future |
| 12-3 | Variation telemetry in watcher | 1 | future |

## Design Principles

- **Play once, never loop.** Tracks fade in, play through, fade out.
- **Overture on arrival.** New location = overture variant. Sets the scene.
- **Resolution after climax.** Combat ending or quest completion = resolution variant.
- **Intensity drives energy.** Low intensity → ambient/sparse. High intensity → full/tension_build.
- **Fallback gracefully.** Genre packs without themes use flat mood_tracks. Never fail to play.
