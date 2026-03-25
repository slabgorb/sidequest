# ADR-011: World State JSON Patches

> Ported from sq-2. Language-agnostic state management pattern.

## Status
Accepted

## Context
Multiple agents need to update game state. Full state replacement creates race conditions and data loss.

## Decision
Agents emit JSON patches describing only what changed. Patches are applied with field-aware merge semantics.

### Patch Fields

| Field | Semantic | Type |
|-------|----------|------|
| location | Replace | String |
| time_of_day | Replace | String |
| npc_attitudes | Merge by NPC name | Map |
| npcs_present | Replace | List |
| active_stakes | Replace | String |
| lore_established | Append | List |
| narrative_log_entry | Append | Single entry |
| quest_updates | Merge by quest name | Map |
| character_patches | Merge by character name | Map |

### Rust Pattern
```rust
pub fn apply_patch(state: &mut GameState, patch: &StatePatch) -> Result<()> {
    if let Some(loc) = &patch.location {
        state.location = loc.clone();
    }
    if let Some(attitudes) = &patch.npc_attitudes {
        for (name, delta) in attitudes {
            state.update_npc_disposition(name, *delta);
        }
    }
    if let Some(lore) = &patch.lore_established {
        state.lore.extend(lore.iter().cloned());
    }
    // ... etc
    Ok(())
}
```

### Consistency Model
Eventually consistent. Patches from stale turns apply harmlessly. Self-correction occurs via the next turn's agent seeing fresh state.

## Consequences
- No data loss from concurrent agent updates
- Patches are small (only changed fields), reducing token cost
- Audit logging captures every patch for debugging
