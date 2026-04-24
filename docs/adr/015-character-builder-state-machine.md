---
id: 15
title: "Character Builder State Machine"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: live
implementation-pointer: null
---

# ADR-015: Character Builder State Machine

> Ported from sq-2. Language-agnostic game design.

## Context
Character creation must be genre-driven, serializable (for mid-creation saves), and produce narrative hooks that the narrator can use.

## Decision
Character creation is a state machine driven by scenes defined in `char_creation.yaml`.

### States
```
IDLE → IN_PROGRESS → AWAITING_FOLLOWUP → CONFIRMATION → COMPLETE
```

- **IDLE:** No creation in progress
- **IN_PROGRESS:** Presenting a scene to the player
- **AWAITING_FOLLOWUP:** Processing freeform input via LLM
- **CONFIRMATION:** Player reviews final character
- **COMPLETE:** Character created, hooks emitted

### Scene Definition (from genre pack)
```yaml
scenes:
  - prompt: "What drew you to a life of adventure?"
    choices:
      - label: "Revenge"
        description: "Someone wronged you"
        effects: { personality: "driven", hook: "nemesis" }
      - label: "Curiosity"
        description: "The world is vast"
        effects: { personality: "inquisitive", hook: "wanderlust" }
    allows_freeform: true
```

### Narrative Hooks
Each choice produces `NarrativeHook` objects. The narrator is **authorized** to use provided hooks but **forbidden** from inventing new character motivations.

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NarrativeHook {
    pub hook_type: String,
    pub text: String,
}
```

### Serialization
Full builder state is serializable for mid-creation saves via serde.

## Consequences
- Genre packs control the creation experience without code changes
- Hooks create narrative continuity between creation and gameplay
- State machine is testable without LLM (freeform mode excepted)
