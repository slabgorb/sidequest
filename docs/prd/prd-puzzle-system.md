# PRD: Environmental Puzzle System

> **Status:** Draft
> **Author:** GM Agent (The Bendu)
> **Date:** 2026-04-03

## Problem

SideQuest has no puzzle system. The narrator can improvise puzzle-like situations, but without mechanical backing there's no way to verify puzzles are engaging, fair, or even running. OTEL can't observe what doesn't exist. The narrator will either skip puzzles entirely or fall back on cliché riddle-door patterns that violate Agency and the Zork Problem.

## Goal

A content-driven puzzle system that gives the narrator **structured situations with pressure** instead of logic tests with predetermined answers. Puzzles should feel like part of the world, not imported from a puzzle book.

## Non-Goals

- Procedural puzzle *generation* (future work — this PRD defines the content format and narrator contract)
- Video-game-style puzzles with constrained inputs (violates Zork Problem)
- Puzzle UI widgets or minigames (the narrator is the interface)

## Design Principles

Derived from OSR puzzle design research (Alexandrian, Goblin Punch, Gnome Stew, Jaquays method):

### 1. Situations, Not Tests

A puzzle is a **space with pressure**, not a lock with a key. Define the environment, the obstacle, the constraints, and the stakes — not the answer. The player provides the answer through natural language.

### 2. Three-Clue Rule (Mandatory)

Every puzzle must have at least three independent discoverable details that could lead to a valid approach. Players will miss the first, ignore the second, and misinterpret the third. Three clues means two backup plans.

### 3. Multiple Valid Solutions

If there's only one answer, it's a guessing game. Define the *mechanism* (what the puzzle responds to) and *constraints* (what limits the player), not the *answer*. The narrator evaluates player approaches against the mechanism.

### 4. Observable State

Every player action produces feedback. The room changes. Water rises. Something clicks. "Nothing happens" is a design failure. Partial progress is always visible.

### 5. Diegetic Integration

Puzzles exist because the world created them — not because a designer placed them. A collapsed mine, a flooded crypt, an occupied bridge. The puzzle's logic derives from fiction, not cleverness.

### 6. Graceful Degradation

Failure doesn't block progress — it costs something (HP, inventory, time, reputation). The player still moves forward, just bruised. No adventure-ending puzzle gates.

### 7. Escalation (Living World)

Puzzles aren't static. Time pressure, environmental change, or NPC arrival increases stakes if the player stalls. The world doesn't pause while you think.

## Taxonomy

Four puzzle types, mapped to the Gnome Stew framework and adapted for SideQuest:

| Type | Description | Example |
|------|-------------|---------|
| **Environmental** | The space itself is the obstacle. Emerged from decay, damage, or natural forces. | Flooded crypt, collapsed mine, burning building |
| **Security** | Intentionally designed protection with exploitable logic. | Warded shrine, trapped vault, guarded passage |
| **Situational** | Not really a puzzle — a social/resource/navigational problem with multiple approaches. | Occupied bridge, faction standoff, blocked trade route |
| **Spatial** | The topology is the puzzle (Jaquays-style). Multiple paths, loops, vertical connections. | Mine with three levels, ruin with hidden passages, sewer network |

These are not mutually exclusive. The Collapsed Mine example is both Environmental and Spatial.

## Content Schema

New file per genre: `puzzles.yaml`. Each puzzle is a **template** — the narrator instantiates it in context.

```yaml
puzzles:
  - id: flooded_crypt
    name: The Flooded Crypt
    type: environmental
    difficulty: easy               # easy | medium | hard
    tags: [underground, water, time-pressure, urban-adjacent]
    
    # What the player walks into
    situation: >
      A crypt beneath a riverside structure. The river has shifted course
      and now seeps through the foundation. The lower chamber — where
      the objective is — floods with rising water.
    
    # What's actually happening (narrator-only context)
    reality: >
      Water enters through cracks in one wall. A floor grate leads to a
      drainage channel, clogged with debris. The water level rises
      steadily. The objective (sarcophagus, altar, chest) sits on a
      raised platform — above water for now.
    
    # Three-clue minimum — discoverable details
    clues:
      - id: wall_cracks
        description: "The north wall weeps water through three major cracks; one is wide enough to fit a hand through."
        discovery: visual          # visual | tactile | auditory | investigative | social
        reveals: "Water source is identifiable and partially blockable"
      - id: clogged_grate
        description: "A rusted iron grate in the floor rattles when stepped on — something blocks it below."
        discovery: tactile
        reveals: "Drainage exists but is obstructed"
      - id: funerary_supplies
        description: "Wooden shelving holds old urns, cloth wrappings, wax seals — materials."
        discovery: visual
        reveals: "Packing material available for the wall cracks"
      - id: water_level
        description: "Water is visibly rising — ankle to knee since arrival."
        discovery: visual
        reveals: "Time pressure is real and observable"
    
    # Valid solution categories — narrator evaluates player actions against these
    approaches:
      - id: clear_grate
        description: "Clear the drainage grate"
        cost: "HP (sharp debris cuts hands), time"
        outcome: "Water drains slowly. Buys time to work in the chamber."
        feedback: "Water level stops rising, then begins to slowly recede."
      - id: pack_cracks
        description: "Block the wall cracks with available materials"
        cost: "Inventory (cloth, wax, wrappings from the shelves)"
        outcome: "Slows inflow significantly. Combined with clearing the grate, chamber becomes dry."
        feedback: "The flow from the wall reduces to a trickle, then stops."
      - id: work_fast
        description: "Ignore the water, rush the objective"
        cost: "Risk — water keeps rising; loud noise may attract attention"
        outcome: "Possible but the sarcophagus lid is heavy and stuck. Rushing under pressure."
        feedback: "Water rises past knees. Movement slows. The lid grinds but holds."
      - id: redirect_outside
        description: "Leave, find the seep point on the surface, dam it"
        cost: "Time (daylight, narrative beats)"
        outcome: "Effective but requires leaving the crypt and returning."
        feedback: "Outside, the riverbank shows muddy erosion near the chapel foundation."
    
    # Escalation beats — triggered by time/turns
    escalation:
      - at_turns: 3
        event: "Water reaches waist depth. Movement requires effort. Small items on shelves begin to float away."
        stakes: "Materials for solutions are being lost to the water."
      - at_turns: 5
        event: "Water reaches chest depth. The player is swimming. The sarcophagus lid is now underwater."
        stakes: "The objective is inaccessible without diving. HP cost to work submerged."
      - at_turns: 8
        event: "Something stirs in the drainage channel — disturbed by the flooding."
        stakes: "The puzzle becomes a confrontation if not resolved."
    
    # What the narrator needs for OTEL verification
    observable_state:
      - water_level: [ankle, knee, waist, chest, submerged]
      - grate_status: [clogged, partially_clear, clear]
      - wall_cracks: [open, partially_sealed, sealed]
      - objective_accessible: [yes, submerged, inaccessible]
    
    # Integration points with existing systems
    integration:
      tension_contribution: 0.4      # Base addition to TensionTracker
      music_mood: mystery             # MusicDirector mood suggestion
      trope_tags: [underground, water, time-pressure]  # Trope engine keyword triggers
      location_tags: [crypt, underground, urban-adjacent]  # Cartography hints for placement
```

## How the Narrator Runs a Puzzle

The puzzle YAML is injected into the narrator's context window alongside the scene directive when the player enters a puzzle location. The narrator receives:

1. **The situation** — what to describe
2. **The clues** — what's discoverable (the narrator reveals these based on player actions and observation)
3. **The approaches** — valid solution categories to evaluate against
4. **The escalation timeline** — what changes if the player stalls
5. **Observable state** — what feedback to give

The narrator does NOT receive a "correct answer." It evaluates the player's natural language action against the approach categories and the mechanism/constraints. If a player tries something not in the approaches list but it's reasonable given the constraints, the narrator applies Rule of Cool + Yes And (SOUL principles) and improvises — but the observable state still updates.

### Narrator Contract

```
PUZZLE ACTIVE: {puzzle_name}
You are running an environmental puzzle. Your job:
1. Describe the space using the situation text. Reveal clues naturally through the player's senses.
2. When the player acts, evaluate against the approaches list. If their action is reasonable 
   but not listed, judge it against the mechanism and constraints — lean toward Yes And.
3. ALWAYS give observable feedback. Water levels change. Materials shift. Sounds occur.
   Never say "nothing happens."
4. Track escalation. After {N} turns without resolution, apply the next escalation beat.
5. Failure = cost, not blockage. If the player fails, they lose HP/items/time but can still proceed.
```

## Integration with Existing Systems

### Trope Engine
Puzzles contribute `trope_tags` that the trope engine can match against. A puzzle in a crypt with `[underground, water]` tags can trigger the `ancient_evil_stirs` trope if it exists in the genre pack.

### TensionTracker
Each puzzle has a `tension_contribution` that adds to the dual-track tension model. Escalation beats increase this. Resolution decreases it. The pacing engine stays informed.

### Scene Directive
Puzzle state injects into the SceneDirective as a new `DirectiveSource::PuzzleState` alongside existing TropeBeat, ActiveStake, and FactionEvent sources. Priority scales with escalation.

### Music Director
Puzzle `music_mood` feeds the MusicDirector for contextual audio. Escalation beats can shift mood (mystery → tension → combat if the puzzle spawns a confrontation).

### OTEL
New span: `puzzle.*` — tracks puzzle ID, current observable state, player approaches attempted, escalation beats fired, resolution method. The GM dashboard can verify puzzles are mechanically engaged, not narrator-improvised.

### Cartography
Puzzle `location_tags` help the world builder place puzzles in appropriate locations. An `[underground, water]` puzzle goes near rivers. A `[vertical, ruins]` spatial puzzle goes in the northern mountains.

### State Patches
Puzzle resolution produces state patches: inventory changes (items spent), HP changes (damage from costs), location changes (if the puzzle is a navigation challenge), and KnownFact accumulation (what the player learned).

## Content Requirements Per Genre

Each genre pack should define puzzles that fit its tone and world:

| Genre | Puzzle Flavor | Example Types |
|-------|--------------|---------------|
| `low_fantasy` | Gritty, physical, resource-scarce | Collapsed structures, flooded spaces, occupied passages, ruined infrastructure |
| `neon_dystopia` | Tech-integrated, social, surveillance | Hacked security, corporate lockdowns, black market access, data extraction |
| `pulp_noir` | Information, social, deduction | Crime scenes, witness networks, evidence chains, social manipulation |
| `space_opera` | Environmental, systemic, scale | Hull breaches, alien ecosystems, station failures, orbital mechanics |
| `mutant_wasteland` | Scarcity, environmental, biological | Toxic zones, mutant flora obstacles, scavenger puzzles, radiation navigation |
| `road_warrior` | Vehicular, terrain, resource | Canyon crossings, fuel scarcity, convoy obstacles, territorial blockades |
| `elemental_harmony` | Elemental, balance, philosophical | Elemental imbalances, meditation challenges, harmony restoration |

## Difficulty Calibration

| Level | Clues | Approaches | Escalation Window | Player Skill Required |
|-------|-------|------------|-------------------|-----------------------|
| **Easy** | 4+ (generous) | 4+ (most obvious actions work) | 5+ turns | Observation — notice what's in the room |
| **Medium** | 3 (standard) | 3-4 (requires synthesis of clues) | 3-4 turns | Deduction — connect clues across sources |
| **Hard** | 3 (some misleading) | 2-3 (requires insight or planning) | 2-3 turns | Inference — question assumptions, plan ahead |

Hard puzzles may include **misleading information** (an NPC's wrong conclusion, a red herring) — but the correct information is always discoverable alongside it. The player must *choose* which to trust, not guess blindly.

## Multiplayer Considerations

In multiplayer, puzzles become richer:
- Different players observe different clues based on position/perception (PerceptionRewriter)
- Solutions that require multiple simultaneous actions favor coordination
- Resource costs can be distributed across the party
- The STRUCTURED submit-and-wait turn mode works naturally — all players submit their puzzle actions, then the narrator resolves the combined result. Peer action text is visible during the wait phase (collaborative default per ADR-036), which helps the table coordinate puzzle-solving moves.

## Verification (OTEL)

New spans for the GM dashboard:

| Span | Attributes |
|------|------------|
| `puzzle.activated` | puzzle_id, difficulty, location |
| `puzzle.clue_revealed` | puzzle_id, clue_id, discovery_method |
| `puzzle.approach_attempted` | puzzle_id, approach_id (or "improvised"), player_action |
| `puzzle.state_change` | puzzle_id, field, old_value, new_value |
| `puzzle.escalation_fired` | puzzle_id, escalation_index, stakes |
| `puzzle.resolved` | puzzle_id, resolution_method, turns_taken, cost_paid |

**Red flag:** `puzzle.activated` with no subsequent `puzzle.clue_revealed` or `puzzle.approach_attempted` = the narrator is ignoring the puzzle and improvising.

## Implementation Phases

### Phase 1: Content Format + Narrator Injection
- Define `puzzles.yaml` schema (this PRD)
- Write 3 puzzles for `low_fantasy` (easy/medium/hard — the three designed in this session)
- Add puzzle context injection to narrator prompt assembly
- Add `DirectiveSource::PuzzleState` to scene directives

### Phase 2: Mechanical Integration
- Wire puzzle state into `GameSnapshot` (new field: `active_puzzle: Option<PuzzleState>`)
- Puzzle escalation tied to turn counter
- State patches from puzzle resolution
- OTEL spans for puzzle lifecycle

### Phase 3: Genre Expansion
- 3+ puzzles per genre pack
- Difficulty distribution: at least one of each level per genre
- Spatial puzzles for genres with strong cartography (low_fantasy, mutant_wasteland, neon_dystopia)

### Phase 4: Procedural Generation (Future)
- Constraint-based generation from environment properties
- Genre-aware puzzle templates with variable instantiation
- Difficulty scaling based on campaign maturity (WorldMaterialization)

## Open Questions

1. **Puzzle placement:** Should puzzles be pre-placed in world data, or dynamically selected by the narrator based on location tags and campaign maturity? Pre-placed = more authored quality, dynamic = more replayability.

2. **Puzzle persistence:** If a player leaves a puzzle mid-solve, does the state persist? (Probably yes — the flooded crypt doesn't un-flood because you walked away.)

3. **Puzzle-to-confrontation escalation:** When a puzzle's final escalation beat triggers a combat encounter, how does the transition work? The puzzle state should feed into the confrontation setup (e.g., water level affects combat terrain).

4. **Multiplayer puzzle ownership:** In structured turn mode, who "owns" a puzzle action? Can multiple players attempt different approaches simultaneously?
