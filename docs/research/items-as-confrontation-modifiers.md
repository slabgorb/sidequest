# Items as Confrontation Modifiers

## Core Idea

Items in inventory can modify confrontation beats — lowering `requires` thresholds,
adding `metric_delta` bonuses, unlocking hidden beats, or changing risk outcomes.
This is the non-magic equivalent of spell slots for genres without magic systems.

## Examples

| Genre | Item | Effect |
|-------|------|--------|
| spaghetti_western | Marked Deck | Unlocks `cheat` beat without Card Shark class, or gives +2 metric_delta on cheat |
| pulp_noir | Forged Documents | Satisfies `requires` on `evidence` beat in interrogation without a real clue |
| pulp_noir | Loaded Dice | +1 metric_delta on craps beats |
| victoria | Damning Letter | Satisfies `requires` on `cross_examine` in trial, +2 conviction |
| neon_dystopia | Blackmail File | Unlocks a hidden `leverage` beat in negotiation with +4 delta |
| road_warrior | Nitro Canister | Not social — but same pattern for chase confrontations (boost a beat) |
| space_opera | Diplomatic Credentials | +1 metric_delta on `persuade`, removes risk on `threaten` |
| low_fantasy | Poisoned Wine | Unlocks `poison_chalice` confrontation type (future 16-8) |

## Why This Matters

In magic-heavy genres (low_fantasy, elemental_harmony), spells give players mechanical
options beyond "I hit it." In non-magic genres, items fill that role. A Card Shark with
a marked deck has the same kind of mechanical advantage as a wizard with a scroll —
it's a consumable (or discoverable) resource that unlocks capabilities.

Without this, social confrontations are pure stat checks. With it, players have reasons
to acquire, protect, and strategically deploy items in non-combat encounters. The
inventory system stops being a loot list and becomes a tactical resource.

## Integration Point

The `requires` field on `BeatDef` (added in story 16-7) is already the hook. Currently
it's a narrator hint string. To make it mechanical:

1. Beat dispatch checks `requires` against `GameSnapshot.inventory`
2. Item grants can modify a beat's `metric_delta` (bonus from item quality/narrative_weight)
3. Items can have a `confrontation_modifiers` field listing which beats they affect
4. Consumable items are removed from inventory after use (or degrade via narrative_weight)

### Item Schema Extension

```yaml
# On Item (inventory.rs)
confrontation_modifiers:
  - confrontation_type: poker
    beat_id: cheat
    effect: "unlocks_beat"           # or "delta_bonus", "removes_risk", "satisfies_requires"
    value: 2                         # +2 to metric_delta if delta_bonus
    consumable: false                # marked deck persists, forged docs are one-use
```

### Beat Resolution Flow (Modified)

```
1. Player action → beat lookup in ConfrontationDef
2. Check beat.requires against inventory items (NEW)
3. If item satisfies requires → allow beat even without class prerequisite
4. Apply base metric_delta + item bonus (NEW)
5. If item is consumable → remove from inventory
6. Stat check with item-modified risk (NEW)
7. Resolution check
8. OTEL span includes item usage
```

## Scope Estimate

- **3 points** if just `requires` checking against inventory (string match)
- **5 points** if full `confrontation_modifiers` on items with delta bonuses
- **8 points** if consumable items + OTEL + UI showing item-modified beats

## Relationship to Existing Systems

- **Inventory** (`inventory.rs`, 346 LOC) — Item already has `narrative_weight` for
  evolution. `confrontation_modifiers` would be a new field.
- **Confrontation engine** (`encounter.rs`) — `apply_beat()` would need to accept
  an optional item modifier parameter.
- **Genre packs** — Starting equipment in `char_creation.yaml` could include
  class-specific confrontation items (Card Shark gets marked deck at creation).
- **16-8 (genre-specific types)** — Some types (poison_chalice) are inherently
  item-dependent. This system would make them mechanical, not just narrative.
