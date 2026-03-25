---
parent: context-epic-1.md
---

# Story 1-4: Game State — Domain-Decomposed Structs, Combatant Trait, Newtypes, State Patches

## Business Context

Port the entire `game/` module — the domain heart of SideQuest. The Python version has a
`GameState` god object (~920 lines, 30+ fields) that imports from 8 modules with a 255-line
`apply_patch()` method. The Rust version decomposes this into domain-specific structs that
own their own mutations.

**Python sources:**
- `sq-2/sidequest/game/state.py` — GameState, apply_patch, apply_combat_patch, apply_chase_patch
- `sq-2/sidequest/game/character.py` — Character, ProgressionState, NarrativeHook
- `sq-2/sidequest/game/npc.py` — NPC, NPCRegistry, Attitude, derive_attitude
- `sq-2/sidequest/game/item.py` — Item, ItemCategory, ItemRarity, Inventory
- `sq-2/sidequest/game/combat_models.py` — Enemy, ActiveEffect, CombatState
- `sq-2/sidequest/game/chase.py` — ChaseState, ChaseBeat, ChasePhase, RigStats
- `sq-2/sidequest/game/narrative_character.py` — NarrativeState, Relationship
- `sq-2/sidequest/game/narrative_models.py` — NarrativeEntry
- `sq-2/sidequest/game/progression.py` — affinity tiers, milestones, level-ups
- `sq-2/sidequest/game/turn_manager.py` — TurnManager (barrier sync)
- `sq-2/sidequest/game/state_delta.py` — snapshot_state, compute_state_delta
- `sq-2/sidequest/game/inventory_rules.py` — carry limits, genre philosophy
- `sq-2/sidequest/game/session.py` — SessionManager, save/load
- `sq-2/sidequest/game/persistence.py` — NarrativeLog (JSONL)
- `sq-2/sidequest/game/validators.py` — shared validation helpers

## Technical Guardrails

- **Port lesson #4 (decompose GameState):** Domain modules: combat, chase, character, npc,
  world, narrative, progression, inventory. Each owns its state struct and mutations.
  Top-level `GameSnapshot` composes them
- **Port lesson #5 (Disposition newtype):** `Disposition(i8)` with validated construction
  (-15..=15). Replaces both `Attitude` and `DispositionLevel` enums and their conflicting
  thresholds (±10 vs ±25)
- **Port lesson #6 (HP clamping):** Single `fn clamp_hp(current: i32, delta: i32, max: i32) -> i32`
  that clamps to 0..=max. Fixes the Python bug where progression.py allows negative HP
- **Port lesson #10 (Combatant trait):** Characters, NPCs, and enemies all implement
  `Combatant` with name/hp/max_hp/ac/level methods. Eliminates repeated field definitions
- **Port lesson #9 (validation):** NonBlankString for name fields. All inline
  `if not v.strip()` validators become newtype construction
- **Port lesson #11 (complete deltas):** state_delta covers all domains, not just
  characters/location/quest_log
- **Typed state patches:** All mutations via typed patch structs with `Option` fields.
  No raw dict munging

### Module structure

```
sidequest-game/src/
├── lib.rs           — pub mod, GameSnapshot
├── character.rs     — Character, ProgressionState, NarrativeHook
├── npc.rs           — NPC, NPCRegistry, disposition logic
├── combat.rs        — CombatState, Enemy, ActiveEffect
├── chase.rs         — ChaseState, ChaseBeat, ChasePhase, RigStats
├── narrative.rs     — NarrativeEntry, NarrativeState, Relationship
├── progression.rs   — AffinityTier, milestones, level-ups
├── inventory.rs     — Item, Inventory, coal-to-diamond
├── world.rs         — WorldState (location, atmosphere, quest_log)
├── types.rs         — Disposition, NonBlankString, clamp_hp
├── traits.rs        — Combatant trait
├── patches.rs       — StatePatch, CombatPatch, ChasePatch
├── delta.rs         — snapshot_state, compute_state_delta
├── turn.rs          — TurnManager (barrier sync)
├── session.rs       — SessionManager, save/load
└── persistence.rs   — NarrativeLog (JSONL)
```

## Scope Boundaries

**In scope:**
- All game model structs ported from Python
- Domain decomposition (no god object)
- Combatant trait implemented by Character, NPC, Enemy
- Disposition newtype, NonBlankString newtype, clamp_hp
- Typed state patches with Option fields
- State delta computation covering all domains
- TurnManager (barrier sync for multiplayer)
- Session save/load (rusqlite or JSON — per ADR-006)
- Coal-to-diamond inventory pattern as a formal state transition
- Unit tests for all domain logic (clamp_hp, disposition, patches, deltas)

**Out of scope:**
- Orchestrator (lives in agents crate — story 1-5)
- Prompt composition (story 1-5)
- WebSocket integration (story 1-6)
- Lore RAG system (future epic)

## AC Context

| AC | Detail |
|----|--------|
| Domain decomposition | No single GameState god object — domain modules own their state |
| Combatant trait | Character, NPC, Enemy implement shared trait |
| Disposition newtype | Single type replaces two Python enums, validates -15..=15 |
| clamp_hp | Single function, tested, clamps to 0..=max_hp |
| Typed patches | StatePatch/CombatPatch/ChasePatch with Option fields |
| Complete deltas | state_delta covers all domains |
| Session persistence | Save/load game state works |
| Inventory | Coal-to-diamond pattern implemented as state transition |
