---
parent: context-epic-2.md
---

# Story 2-3: Character Creation Flow — CharacterBuilder State Machine, Genre Scenes Over WebSocket, Mechanical Effects

## Business Context

Character creation is the first interactive experience a player has. It's driven by
genre-defined scenes: each scene presents choices (or accepts freeform input), accumulates
mechanical effects (race, class, hooks, lore anchors), and builds toward a finished Character.

The Python `CharacterBuilder` (741 lines) is a well-designed state machine, but it has
accumulated fallbacks and optional paths that obscure the core flow. The Rust version ports
the proven design while letting the type system enforce the state transitions that Python
tracks with runtime checks.

**Python source:** `sq-2/sidequest/game/character_builder.py` (CharacterBuilder class, 741 lines)
**Python source:** `sq-2/sidequest/server/app.py` lines 680-810 (`_handle_character_event`, `_send_builder_scene`, `_route_action_to_builder`)
**Depends on:** Story 2-2 (session actor, Creating phase)

## Technical Approach

### What Python Does

```python
class BuilderState(str, Enum):
    IDLE = "idle"
    SELECTING_MODE = "selecting_mode"   # unused
    IN_PROGRESS = "in_progress"
    AWAITING_FOLLOWUP = "awaiting_followup"
    CONFIRMATION = "confirmation"
    COMPLETE = "complete"

class CharacterBuilder:
    def apply_choice(self, choice_index):
        self._validate_state_for_action()  # runtime check: not IDLE, not COMPLETE, not AWAITING_FOLLOWUP
        scene = self.scenes[self.current_scene_index]
        choice = scene.choices[choice_index]   # IndexError if bad index
        effects = choice.mechanical_effects
        self._validate_choice_against_rules(effects)
        self._apply_effects(effects)
        self._extract_hooks(choice.description, scene.id, effects)
        self._extract_scene_anchors(scene.id, effects)
        if scene.hook_prompt:
            self.state = BuilderState.AWAITING_FOLLOWUP
        else:
            self._advance_scene()
        return self.current_scene
```

The problems:
- `_validate_state_for_action()` is a runtime check that could be a type constraint
- `SELECTING_MODE` state exists but is never used
- `choices_made` is a `list[dict]` — no type for what effects look like
- `revert_last_scene()` has to manually undo each effect type with parallel pop operations on 6 different lists
- `build()` has an LLM call for hook refinement buried inside a builder method

### What Rust Does Differently

**State machine as enum, not stringly-typed:**

```rust
enum BuilderPhase {
    /// Processing genre-defined scenes
    InProgress {
        scene_index: usize,
        choices: Vec<SceneChoice>,      // typed, not dict
        freeform_inputs: Vec<String>,
    },

    /// Scene has a hook_prompt — waiting for player's followup text
    AwaitingFollowup {
        scene_index: usize,
        hook_prompt: String,
        choices: Vec<SceneChoice>,
        freeform_inputs: Vec<String>,
    },

    /// All scenes done, showing summary for confirmation
    Confirmation {
        accumulated: AccumulatedChoices,  // everything collected
    },
}
```

**Why this matters:**
- `IDLE` and `COMPLETE` don't exist as runtime states — the builder doesn't exist before `start()` returns it, and it's consumed by `build()`.
- `SELECTING_MODE` is gone — it was dead code in Python.
- `AwaitingFollowup` carries the `hook_prompt` in its variant — you can't forget what you're waiting for.
- `InProgress` carries the accumulated choices in the variant — no separate lists to keep in sync.

**Revert becomes clean with a stack:**

Python tracks reversions with parallel lists (`_scene_hook_counts`, `_scene_anchor_counts`,
`_scene_input_types`). Rust uses a single `Vec<SceneResult>` stack:

```rust
struct SceneResult {
    input_type: SceneInputType,  // Choice(index) or Freeform(text)
    hooks_added: Vec<NarrativeHook>,
    anchors_added: Vec<LoreAnchor>,
    effects_applied: MechanicalEffects,
}
```

Reverting pops the last `SceneResult` and undoes its effects. One pop, one undo — not six
parallel list operations that have to stay in sync.

**Mechanical effects are typed:**

```rust
struct MechanicalEffects {
    race_hint: Option<String>,
    class_hint: Option<String>,
    affinity_hint: Option<String>,
    personality_trait: Option<String>,
    // lore anchors
    faction_anchor: Option<String>,
    npc_anchor: Option<String>,
    location_anchor: Option<String>,
}
```

Python uses `dict[str, Any]` for effects and matches keys with string comparisons.
Rust uses a struct — misspelling a field is a compile error, not a silent no-op.

### WebSocket Flow (server integration)

The server's `Creating` session phase dispatches CHARACTER_CREATION messages to the builder:

```
Server → Client: CHARACTER_CREATION { phase: "scene", scene_index: 0, narration: "...",
                   input_type: "choice", choices: [{label, description}], allows_freeform: true }

Client → Server: CHARACTER_CREATION { phase: "scene", choice: "2" }
  or:            CHARACTER_CREATION { phase: "scene", text: "I was a wanderer..." }
  or:            CHARACTER_CREATION { action: "confirm" }
  or:            CHARACTER_CREATION { action: "back" }

Server → Client: CHARACTER_CREATION { phase: "confirmation", summary: "..." }
Server → Client: CHARACTER_CREATION { phase: "complete", character_preview: {...} }
```

Python's `_route_action_to_builder()` parses PLAYER_ACTION text ("1", "2", "confirm",
"back", freeform text) into synthetic CHARACTER_CREATION messages. The Rust version should
do the same — players type in the narrative view, not a special creation UI, so actions
during creation come as PLAYER_ACTION.

### NarrativeHook System

Hooks are the key output of character creation — they authorize the narrator to use
specific character motivations without inventing them:

```rust
struct NarrativeHook {
    hook_type: HookType,      // Origin, Wound, Relationship, Goal, Trait, Debt, Secret, Possession
    source_scene: String,      // which scene generated this
    text: String,              // player-authored or choice-derived
    mechanical_key: Option<String>,  // effect key that generated it
}
```

Python maps effect keys to hook types via a dict. Rust uses an enum:

```rust
enum HookType {
    Origin,       // from race_hint
    Wound,        // from backstory trauma
    Relationship, // from relationship effects
    Goal,         // from goals effects
    Trait,        // from class_hint, personality_trait
    Debt,         // from obligation effects
    Secret,       // from hidden knowledge
    Possession,   // from equipment_hints
}
```

### LoreAnchor System

Each character should connect to the world through faction, NPC, and location anchors.
Python auto-fills missing anchors from genre pack data. Rust should do the same, but
with the required anchor types as a const:

```rust
const REQUIRED_ANCHOR_TYPES: &[&str] = &["faction", "npc_relationship", "location"];
```

### What We're NOT Porting

- **`CreationMode::GUIDED` and `FREEFORM`** — marked "coming soon" in Python, never implemented. Don't port dead code.
- **`parse_freeform_character()`** — LLM call inside `build()` to extract name/race/class from freeform text. Defer — it's for GUIDED mode which doesn't exist.
- **`HookRefiner`** — LLM call to refine narrative hooks. Defer to a later story — not needed for core loop.
- **Builder serialization to `builders.json`** — Python persists in-progress builders. Defer — for MVP, if you disconnect during creation you start over.

## Scope Boundaries

**In scope:**
- `CharacterBuilder` with typed `BuilderPhase` state machine
- `SceneResult` stack for clean revert
- Scene processing: choice selection, freeform input, followup answers
- Hook extraction from mechanical effects
- Lore anchor extraction and auto-fill
- Stats generation (point_buy, 4d6_drop, standard_array from genre config)
- `build()` → `Character` with all accumulated data
- Server integration: CHARACTER_CREATION message dispatch and response
- PLAYER_ACTION rerouting during creation phase (text → synthetic creation message)

**Out of scope:**
- GUIDED and FREEFORM creation modes (dead code in Python)
- Hook refinement via LLM (defer)
- Builder persistence across disconnects (defer)
- Character portrait generation (daemon territory)
- Voice assignment (daemon territory)

## Acceptance Criteria

| AC | Detail |
|----|--------|
| Scene presentation | First scene from genre pack sent as CHARACTER_CREATION with choices |
| Choice selection | Player sends "1" → choice applied, next scene sent |
| Freeform input | Player types text → stored, hooks extracted, next scene sent |
| Followup prompt | Scene with hook_prompt → AWAITING_FOLLOWUP → player answers → advance |
| Back/revert | Player sends "back" → previous scene restored, effects undone |
| Confirmation | After all scenes → summary shown, player confirms |
| Build character | Confirm → Character created with hooks, anchors, stats, inventory |
| Phase transition | After build → session transitions from Creating to Playing |
| Invalid choice | Out-of-range index → ERROR message, stay on same scene |
| Starting inventory | Character gets class-appropriate starting equipment from genre pack |
| Auto-fill anchors | Missing faction/npc/location anchors filled from genre pack |

## Type-System Wins Over Python

1. **No dead states.** IDLE and SELECTING_MODE don't exist — the builder is constructed in InProgress state.
2. **Revert is one pop, not six.** `SceneResult` bundles everything a scene added.
3. **Effects are typed, not dict.** `MechanicalEffects.race_hint` vs `effects.get("race_hint")`.
4. **Hook types are an enum.** `HookType::Origin` vs `"origin"` string.
5. **Builder is consumed by `build()`.** You can't accidentally use a builder after building — it's moved.
