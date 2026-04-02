---
parent: context-epic-19.md
workflow: tdd
---

# Story 19-7: Weight-based encumbrance — total_weight, carry_mode, overencumbered state

## Business Context

Dungeon crawling creates a loot-vs-mobility trade-off. Weight-based encumbrance means every item picked up has a cost — carry too much and trope escalation accelerates (Keeper awareness rises faster). This replaces the current count-based carry limit with an optional weight-based mode configured per genre pack.

## Technical Guardrails

- Add `total_weight() -> f64` to `Inventory` in `inventory.rs`. Sums `weight * quantity` for all items.
- Add `CarryMode` enum: `Count` (existing behavior) | `Weight` (new). Configured in genre pack rules.
- Add `weight_limit: Option<f64>` to genre pack rules.
- When `carry_mode` is `Weight`, `Inventory.add()` rejects items that would exceed `weight_limit`. Return an error, don't silently drop.
- `is_overencumbered() -> bool` — true when at or over weight_limit.
- When overencumbered in room_graph mode, trope tick multiplier increases by 1.5x (stacks with room's `keeper_awareness_modifier`).
- Existing count-based carry (`max_items`) is unchanged when `carry_mode` is `Count` or unset.

## Scope Boundaries

**In scope:**
- `total_weight()` on Inventory
- `CarryMode` enum and weight_limit in genre rules
- Weight validation on item add
- `is_overencumbered()` check
- Trope multiplier increase when overencumbered
- Existing count-based carry unaffected

**Out of scope:**
- Drop item command (existing /inventory handles this)
- UI weight display (future)
- Per-item weight editing by narrator

## AC Context

1. total_weight() sums all item weights x quantities
2. CarryMode::Weight rejects over-limit adds
3. is_overencumbered() returns true when at/over limit
4. Trope multiplier increased when overencumbered
5. Existing count-based carry unaffected
6. Test: add items to weight limit, verify rejection and overencumbered flag
