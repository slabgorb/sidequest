---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-9: Treasure-as-XP — gold extraction grants affinity progress

## Business Context

Classic OSR mechanic: you don't get XP for killing monsters, you get it for extracting treasure. When the player returns to the surface (leaves the dungeon) with gold, that gold amount translates to affinity progress. This ties the extraction pressure loop together — delve deep for treasure, but every room transition burns resources and raises Keeper awareness. Get out alive with the loot.

## Technical Guardrails

- Trigger: gold increases while player location is a surface region (not in dungeon). In room_graph mode, "surface" means the player is in a room with `room_type: entrance` or has left the room graph entirely.
- Genre pack rules set `xp_affinity: "Plunderer"` (or whatever affinity name) to configure which affinity receives the progress.
- Use existing `AffinityState` and `check_affinity_thresholds()` in `sidequest-game/src/affinity.rs`.
- Progress amount = gold value extracted. 100 GP extracted = 100 progress on the configured affinity.
- OTEL event: `treasure.extracted` with gold_amount, affinity_name, new_progress.
- Content-level fallback consideration: try narrator prompt injection first ("when player extracts treasure, note it"). If unreliable, implement the engine hook. ADR-057's crunch separation principle says this should be an engine hook, not narrator prompt compliance.

## Scope Boundaries

**In scope:**
- Gold increase on surface location triggers affinity progress
- `xp_affinity` field in genre rules configures target affinity
- Engine-level hook (not narrator prompt)
- OTEL event

**Out of scope:**
- Monster XP (not an OSR mechanic in this genre)
- Selling items for gold (existing merchant system handles this)
- Affinity tier unlocks (existing check_affinity_thresholds handles this)

## AC Context

1. Gold increase on surface location triggers affinity progress
2. xp_affinity field in genre rules configures target affinity
3. No effect when gold changes inside dungeon
4. Test: extract 100 GP to surface, verify 100 progress on configured affinity
