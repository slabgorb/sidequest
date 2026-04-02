---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-3: Trope tick on room transition — fire trope engine per room move

## Business Context

Keeper awareness is the core tension mechanic for dungeon crawling. It's implemented entirely through the existing trope engine — no custom subsystem needed. When the player moves to a new room, tropes tick with the room's `keeper_awareness_modifier` as the engagement multiplier. High-value rooms escalate faster than empty corridors.

## Technical Guardrails

- `TropeEngine::tick()` in `trope.rs` already accepts an engagement multiplier. Use it — don't create a new method unless the API doesn't fit.
- `RoomDef.keeper_awareness_modifier` (f64) from the loaded room graph provides the per-room multiplier.
- This fires ONLY on valid room transitions (after 19-2 validation passes), not on every player action.
- In region mode, existing per-turn tick behavior is unchanged.
- `rate_per_turn` gets dual meaning: per player action (region) vs per room transition (room_graph). This is a semantic change, not a code change — the same tick call, different trigger point.
- OTEL event: `trope.room_tick` with room_id, modifier, trope states after tick.

## Scope Boundaries

**In scope:**
- Fire TropeEngine::tick() on room transition with room's keeper_awareness_modifier
- OTEL event for trope tick
- Existing per-turn tick unchanged in region mode

**Out of scope:**
- Resource depletion on transition (19-5, 19-6)
- Custom Keeper awareness subsystem (using trope engine)

## AC Context

1. Trope tick fires on room transition in room_graph mode
2. `keeper_awareness_modifier` from room data scales the multiplier
3. Trope escalation events fire at thresholds (existing behavior)
4. Existing per-turn tick behavior unchanged in region mode
5. Test: 5 room transitions advance trope by 5 x rate_per_turn x modifier
