---
parent: context-epic-14.md
---

# Story 14-2: Player Location on Character Sheet

## Business Context

Players can't see where other party members are. When the party splits (intentionally or
not), there's no indication in the UI. Location needs to be visible on the party panel.

**Playtest evidence:** "We need clearer ideas of the players relationship to each other.
On the player sheet we should have the location of the player."

## Technical Approach

### Protocol Changes

Add `current_location` to existing payload structs:

```rust
// In PARTY_STATUS member entries
pub struct PartyMember {
    pub player_id: String,
    pub character_name: String,
    pub current_hp: i32,
    pub max_hp: i32,
    pub level: u32,
    pub character_class: String,
    pub current_location: Option<String>,  // NEW
}

// In CHARACTER_SHEET payload
pub struct CharacterSheet {
    // ... existing fields
    pub current_location: Option<String>,  // NEW
}
```

### Server-Side

Location is already tracked internally (from MAP_UPDATE state deltas). Wire it into
PARTY_STATUS and CHARACTER_SHEET message construction.

### UI: Party Panel

Display location under each player's name:
```
┌──────────────────────┐
│ Thane (Fighter) Lv 3 │
│ HP: 24/30            │
│ 📍 The Crossroads    │
├──────────────────────┤
│ Lyra (Mage) Lv 3     │
│ HP: 18/18            │
│ 📍 The Crossroads    │
└──────────────────────┘
```

When players are in different locations, visually differentiate (e.g., group by location
or show location in a different color when it differs from the local player's location).

## Scope Boundaries

**In scope:**
- Add current_location to PARTY_STATUS and CHARACTER_SHEET
- Server populates from tracked location state
- UI renders location in party panel
- Visual distinction when players are in different locations

**Out of scope:**
- Mini-map
- Distance calculations between players
- Location-based action restrictions

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Protocol field | PARTY_STATUS includes current_location per member |
| Server populates | Location sourced from internal tracking |
| UI displays | Location visible under each player in party panel |
| Split detection | Different locations visually flagged |
| Updates real-time | Location changes reflected within 1 turn |
