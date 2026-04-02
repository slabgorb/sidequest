---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-6: Wire ResourceDeclaration.decay_per_turn — apply resource decay on trope tick

## Business Context

`ResourceDeclaration` in genre pack YAML already has a `decay_per_turn` field that's parsed but never applied. This is a classic wiring story — the data exists, the application function exists (`apply_resource_deltas`), they just need connecting. In room_graph mode, decay fires per room transition (via trope tick). Resources at min value trigger a GameMessage.

## Technical Guardrails

- `ResourceDeclaration.decay_per_turn` is already parsed in `sidequest-genre/src/models.rs`.
- `apply_resource_deltas()` exists in `sidequest-game/src/state.rs` (~line 600).
- After trope tick fires (19-3), iterate `resource_declarations`, apply each `decay_per_turn` to `resource_state` via `apply_resource_deltas`.
- Resources clamped to declared `min`/`max` values from `ResourceDeclaration`.
- Fire GameMessage when a resource hits its `min` value — the UI needs to warn the player.
- OTEL event: `resource.decay` with resource_name, old_value, new_value, at_min.

## Scope Boundaries

**In scope:**
- Apply decay_per_turn after trope tick in room_graph mode
- Clamp to min/max from ResourceDeclaration
- GameMessage when resource hits min
- OTEL event

**Out of scope:**
- New resource types (content-level)
- UI resource display (Epic 16, story 16-13)
- Resource threshold → KnownFact (Epic 16, story 16-11)

## AC Context

1. decay_per_turn applied to resource_state after trope tick
2. Resources clamped to declared min/max
3. GameMessage when resource hits min
4. Test: resource with decay -0.1 reaches 0 after 10 ticks
