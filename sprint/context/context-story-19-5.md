---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-5: Consumable item depletion — uses_remaining on items, decrement on room transition

## Business Context

Torch burn is the primary resource pressure mechanic in dungeon crawling. Items gain a `uses_remaining` field. On each room transition, the engine decrements `uses_remaining` for the active light source. When it hits 0, the item is removed and a GameMessage fires — the player is now in the dark. This creates the extraction pressure: stay too long and you lose light.

## Technical Guardrails

- Add `uses_remaining: Option<u32>` to `Item` struct in `inventory.rs`. Existing items without this field default to `None` (infinite use).
- Add `consume_use(item_id: &str) -> Option<Item>` method on `Inventory` that decrements and returns the removed item if it hits 0.
- On room transition in room_graph mode, find the first active item with tag `light` and call `consume_use`.
- Fire `GameMessage` when a light source is exhausted — the UI and narrator need to know.
- Genre pack `item_catalog` entries set initial `uses_remaining` via a field (e.g., `resource_ticks: 6` for a torch that lasts 6 rooms).
- `uses_remaining` must serialize/deserialize for save/load persistence.
- OTEL event: `item.depleted` with item_name, remaining_before.

## Scope Boundaries

**In scope:**
- `uses_remaining: Option<u32>` on Item
- `consume_use()` method on Inventory
- Room transition decrements active light source
- GameMessage on light exhaustion
- Serialization for persistence

**Out of scope:**
- Ration consumption (future — same mechanism, different tag)
- Weight-based encumbrance (19-7)
- Darkness mechanics in narration (content-level narrator prompting)

## AC Context

1. Item.uses_remaining field added, serialized/deserialized
2. consume_use() decrements and removes at 0
3. Room transition decrements active light source
4. GameMessage fired on light exhaustion
5. Test: torch with 6 uses survives 5 transitions, removed on 6th
