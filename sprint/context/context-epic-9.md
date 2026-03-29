# Epic 9: Character Depth — Self-Knowledge, Slash Commands, Narrative Sheet

## Overview

Give players a rich understanding of who their character is and quick-access commands
for interacting with game state. Characters should be described in genre voice, not
mechanical stat blocks. Abilities read as narrative descriptions ("Your bond with
ancient roots lets you sense corruption in living things"), knowledge accumulates
through play, and the character sheet is a living document that reflects who the
character has become. Slash commands provide direct interaction without going through
the narrator.

This combines two concerns from the Python codebase: Epic 62 (Character Self-Knowledge)
and the slash command system, unified because both are about the player's direct
relationship with their character and the game world.

## Background

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Orchestrator** | Turn loop: input -> intent -> agent -> narration -> patch -> broadcast |
| **Character creation** | Character model, abilities, stats, genre pack integration |
| **IntentRouter** | Classifies player input into action categories |

Epic 9 enriches the character model and adds a pre-intent input intercept for slash
commands.

### Python Reference

| Python module | What it does |
|---------------|-------------|
| `sq-2/sprint/epic-62.yaml` | Character Self-Knowledge epic definition |
| `sq-2/sidequest/slash_commands/*.py` | Server-side command handlers (/status, /gm, etc.) |

### Key Design Principles

- **Genre voice over stat blocks.** "+2 Nature check" becomes "Your bond with ancient
  roots lets you sense corruption in living things." The mechanical effect is stored
  but the player-facing text is always narrative.
- **Involuntary abilities are narrator context.** If a character has root-bonding,
  the narrator prompt includes that ability so Claude can trigger it when appropriate
  without the player asking.
- **Knowledge grows through play.** KnownFacts are things the character learned during
  the session, not backstory. They persist in game state and feed into narrator context.
- **Slash commands bypass intent classification.** Input starting with "/" is routed
  directly to command handlers. No LLM call needed.

## Technical Architecture

### Input Routing

```
Player input
     |
     v
 starts with "/"?
     |          |
    yes         no
     |          |
     v          v
SlashRouter  IntentRouter (existing)
     |
     v
 parse command + args
     |
     v
 handler(state, args) -> CommandResult
     |
     v
 send response to player
```

The slash router sits upstream of the IntentRouter. It intercepts, dispatches, and
responds without touching the orchestrator turn loop. Commands are pure functions
of game state and arguments.

### Character Knowledge Model

```
Character
  |
  +--- abilities: Vec<AbilityDefinition>
  |      |
  |      +--- name: String
  |      +--- genre_description: String     ("Your bond with ancient roots...")
  |      +--- mechanical_effect: String     ("+2 Nature, detect corruption 30ft")
  |      +--- involuntary: bool             (triggers without player action)
  |      +--- source: AbilitySource         (Race, Class, Item, Play)
  |
  +--- known_facts: Vec<KnownFact>
  |      |
  |      +--- content: String               ("The mayor is secretly a cultist")
  |      +--- learned_turn: u64             (when this was learned)
  |      +--- source: FactSource            (Observation, Dialogue, Discovery)
  |      +--- confidence: Confidence        (Certain, Suspected, Rumored)
  |
  +--- narrative_sheet() -> String          (genre-voiced character summary)
```

### Narrator Prompt Integration

```
Existing narrator prompt
     |
     +--- [CHARACTER ABILITIES]
     |      involuntary abilities listed as narrator context
     |      "Reva has root-bonding: she involuntarily senses corruption
     |       in living things within 30 feet."
     |
     +--- [CHARACTER KNOWLEDGE]
            known facts relevant to current scene
            "Reva knows: The mayor is secretly a cultist (certain).
             The old well leads to underground tunnels (suspected)."
```

### Slash Command Registry

```
/status          -> show character HP, conditions, active effects
/inventory       -> list carried items with genre descriptions
/map             -> show known locations and current position
/save            -> trigger game state persistence
/help            -> list available commands

/gm set <k> <v> -> modify game state variable (operator only)
/gm teleport <l> -> move character to location (operator only)
/gm spawn <npc>  -> add NPC to current scene (operator only)
/gm dmg <n> <hp> -> apply damage to entity (operator only)

/tone <axis> <v> -> adjust genre alignment
                    axes: light/dark, action/mystery, serious/whimsy
                    values: -2 to +2
```

### Key Types

```rust
pub struct AbilityDefinition {
    pub name: String,
    pub genre_description: String,
    pub mechanical_effect: String,
    pub involuntary: bool,
    pub source: AbilitySource,
}

pub enum AbilitySource {
    Race,
    Class,
    Item,
    Play,  // learned during gameplay
}

pub struct KnownFact {
    pub content: String,
    pub learned_turn: u64,
    pub source: FactSource,
    pub confidence: Confidence,
}

pub enum FactSource {
    Observation,
    Dialogue,
    Discovery,
}

pub enum Confidence {
    Certain,
    Suspected,
    Rumored,
}

pub enum CommandResult {
    Display(String),           // text response to player
    StateMutation(StatePatch), // /gm commands that modify state
    Error(String),             // invalid command or args
}

pub type CommandHandler = fn(&GameState, &str) -> CommandResult;
```

## Story Dependency Graph

```
2-3 (character creation)       2-5 (orchestrator turn loop)
 |                              |
 +---> 9-1 (AbilityDefinition) |
 |      |                      +---> 9-3 (KnownFact model)
 |      +---> 9-2 (abilities   |      |
 |      |      in narrator)    |      +---> 9-4 (facts in narrator,
 |      |                      |      |      tiered injection)
 |      +---> 9-5 (narrative   |      |
 |             sheet)          |      +---> 9-11 (structured footnote
 |              |              |              output from narrator)
 |              +---> 9-10     |               |
 |              (wire React)   |               +---> 9-12 (footnote
 |                             |               |      UI rendering)
 |                             |               |
 |                             |               +---> 9-13 (journal
 |                             |                      browse view)
 |                             |
 |                             +---> 9-6 (slash command router)
 |                                     |
 |                                     +---> 9-7 (core commands)
 |                                     |
 |                                     +---> 9-8 (GM commands)
 |                                     |
 |                                     +---> 9-9 (tone command)
```

## Deferred (Not in This Epic)

- **Ability progression / leveling** — Characters gaining new abilities through play.
  AbilityDefinition supports `source: Play` but the acquisition system is future work.
- **Fact forgetting / decay** — KnownFacts are permanent once learned. Memory decay
  or unreliable narrator mechanics are a separate concern.
- **Custom slash commands per genre** — Genre packs could define their own commands
  (e.g., "/pray" in a religious setting). The router supports this but no genre-specific
  commands are implemented in this epic.
- **Autocomplete / command suggestions** — Client-side slash command autocomplete in
  the React UI. The server defines the registry; client UX is deferred.
- **Player-authored journal notes** — A player-writable log distinct from KnownFacts.
  KnownFacts are system-derived; manual notes would be player-authored. The browse
  view (9-13) shows system-derived entries only.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-3: Character creation (9-1 depends on this for character model)
- Story 2-5: Orchestrator turn loop (9-3 and 9-6 depend on this)

### From Epic 1
- Story 1-12: Structured logging (command execution tracing)

## Success Criteria

During a playtest, the system demonstrates:
1. Character abilities display in genre voice, not mechanical notation
2. Involuntary abilities appear in narrator context and trigger appropriately
3. KnownFacts accumulate as the character discovers things through play
4. `/status` shows a genre-voiced summary of the character's current state
5. `/inventory` lists items with narrative descriptions
6. `/gm set` and other GM commands modify game state for debugging
7. `/tone` adjusts genre alignment axes and the narrator reflects the shift
8. The narrative character sheet renders in the React client via CHARACTER_SHEET message
9. Slash commands resolve without an LLM call (pure function dispatch)
