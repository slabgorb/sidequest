---
parent: context-epic-14.md
---

# Story 14-1: Party Co-Location at Session Start

## Business Context

Faction-based spawning makes narrative sense for solo play but is catastrophic for
multiplayer. Players start on different continents and can't interact until the DM manually
teleports them together — a disruptive, immersion-breaking workaround.

**Playtest evidence:** "People would spawn in their faction starting locations... I ended up
having to use DM tools to teleport them and then they had to come back into the game and
that was a very disruptive experience."

## Technical Approach

### World YAML Configuration

Add `session_start` block to world configuration:

```yaml
# genre_packs/{genre}/worlds/{world}/world.yaml
session_start:
  multiplayer_location: "The Crossroads Tavern"
  multiplayer_location_description: "A weathered tavern at the intersection of three trade roads"
  solo_location: null  # null = use faction start or narrator discovery
```

### Server Logic

In `dispatch_connect()` (~line 1688 of lib.rs):

```rust
let start_location = if session.player_count() >= 2 || session.is_multiplayer_configured() {
    world_config.session_start.multiplayer_location
        .unwrap_or_else(|| "Starting area".to_string())
} else {
    // Solo: use faction start or narrator discovery (current behavior)
    "Starting area".to_string()
};
```

Set `current_location` on the character at creation time (line ~2329) using this resolved
location instead of the hardcoded "Starting area".

### Fallback

If no `multiplayer_location` is configured in the world YAML, fall back to "Starting area"
(current behavior). This is a graceful degradation, not a failure.

### Genre Pack Updates

Add `session_start` config to existing worlds:
- `elemental_worlds/shattered_accord`: appropriate meeting location
- `mutant_wasteland/flickering_reach`: appropriate meeting location
- Other worlds: can be added incrementally

## Scope Boundaries

**In scope:**
- `session_start` config in world YAML
- Server reads config and applies to multiplayer sessions
- Genre pack updates for active worlds
- Solo sessions unchanged

**Out of scope:**
- DM command to change spawn point mid-session
- Player-chosen spawn points
- Per-faction multiplayer spawn (grouped but separate starting areas)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Config exists | World YAML accepts `session_start.multiplayer_location` |
| Multiplayer uses it | 2+ player session spawns all players at configured location |
| Solo unchanged | Single-player sessions use existing behavior |
| Fallback works | Missing config falls back to "Starting area" |
| Genre packs updated | Shattered Accord and Flickering Reach have configured locations |
| Narrator knows | First narration acknowledges the shared starting location |
