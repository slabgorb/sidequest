---
parent: context-epic-12.md
---

# Story 12-1: Cinematic Track Variation Selection — MusicDirector Uses Themed Score Cues

## Business Context

The genre packs contain a rich library of music variations per mood — overtures, ambient,
sparse, full orchestration, tension builds, and resolutions. Currently the MusicDirector
only reads the flat `mood_tracks` list (base track + one alternate). The `AudioTheme` and
`AudioVariation` types already exist in `sidequest-genre`, and `audio.yaml` already has a
fully populated `themes` section. The MusicDirector simply never reads it.

Music is cinematic soundtrack, not video game background music. Tracks play once with
fade-in/fade-out, never loop. The MusicDirector should think like a film score supervisor,
picking the right variation based on where we are in the scene.

**Depends on:** Nothing — all data model and content exist. This is a wiring exercise.

## Technical Approach

### TrackVariation Enum

Add a typed enum to `sidequest-genre/src/models.rs`:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TrackVariation {
    Full,         // Default — peak dramatic moment
    Overture,     // First arrival, session start, major scene transition
    Ambient,      // Background during dialogue, quiet moments
    Sparse,       // Low-intensity exploration, uncertainty
    TensionBuild, // Escalating stakes, approaching danger
    Resolution,   // After combat ends, quest completion, winding down
}
```

Add `as_variation() -> TrackVariation` to the existing `AudioVariation` struct (parses
the string `variation_type` field into the enum, defaults to `Full`). This avoids a
breaking serde change to existing YAML.

### Variation Selection Rules (Priority Order)

| Priority | Variation | Condition |
|----------|-----------|-----------|
| 1 | Overture | `session_start == true` OR (`location_changed && scene_turn_count == 0`) |
| 2 | Resolution | `combat_just_ended == true` OR `quest_completed == true` |
| 3 | TensionBuild | `intensity >= 0.7` (non-combat) OR `drama_weight >= 0.7` |
| 4 | Ambient | `intensity <= 0.3` OR `scene_turn_count >= 4` |
| 5 | Sparse | intensity 0.3-0.5 AND `drama_weight <= 0.3` |
| 6 | Full | Default fallback |

Fallback chain: preferred → Full → any available. Never fail to play something.

### MoodContext Extensions

Five new fields, all derivable from existing game state:

```rust
pub struct MoodContext {
    // existing fields...
    pub location_changed: bool,      // from StateDelta
    pub scene_turn_count: u32,       // turns since last location change
    pub drama_weight: f32,           // from TensionTracker PacingHint
    pub combat_just_ended: bool,     // transition detection
    pub session_start: bool,         // first turn flag
}
```

### MusicDirector Changes

1. **Constructor:** Index `AudioConfig.themes` into
   `HashMap<String, HashMap<TrackVariation, Vec<MoodTrack>>>`.
2. **New method:** `select_variation(&MoodClassification, &MoodContext) -> TrackVariation`
   — pure scoring function implementing the priority table above.
3. **Update `select_track()`:** Use themed tracks when available, fall back to legacy
   `mood_tracks` for genre packs without themes.
4. **ThemeRotator keying:** Change history key to `"{mood}:{variation}"` for
   per-variation anti-repetition.

### Server Wiring

The caller constructing `MoodContext` (in `dispatch_player_action`) already has access to
`StateDelta`, `TensionTracker`, and `CombatState`. Populating the 5 new fields is
straightforward derivation from existing state.

## Key Architecture Note

The `AudioTheme` and `AudioVariation` types already exist at `sidequest-genre/src/models.rs:1112`.
The `audio.yaml` `themes` section is already populated with 8 moods × 12-14 variations per mood
across set-1 and set-2 directories. The `AudioConfig.themes` field is deserialized but the
MusicDirector never touches it. This story wires the existing data to the existing selection
infrastructure.

## Scope Boundaries

**In scope:**
- `TrackVariation` enum and `as_variation()` helper
- Variation selection logic in MusicDirector
- `MoodContext` extensions (5 new fields)
- Indexing `AudioConfig.themes` in MusicDirector constructor
- Server-side wiring to populate new MoodContext fields
- Telemetry: chosen variation visible in watcher events

**Out of scope:**
- Client-side variation-aware crossfade durations (follow-up)
- Set rotation logic (set-1/set-2 stay pooled for anti-repetition)
- Generating new music tracks
- Changes to audio.yaml schema

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Themed tracks used | MusicDirector selects from `themes` when available, falls back to `mood_tracks` |
| Overture on arrival | First turn at a new location plays an overture variant |
| Resolution after combat | Combat ending triggers a resolution variant |
| Intensity-driven | High intensity → tension_build/full; low intensity → ambient/sparse |
| Anti-repetition | ThemeRotator prevents repeating within a variation category |
| Backward compatible | Genre packs without `themes` section work identically to today |
| Telemetry | Chosen variation type visible in watcher telemetry |
