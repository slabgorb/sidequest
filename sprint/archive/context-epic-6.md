# Epic 6: Active World & Scene Directives — Living World That Acts On Its Own

## Overview

Make the world an active participant in the story, not a passive backdrop. Currently the
trope engine and world state agent are purely reactive — they process what happened but
never initiate anything. The world whispers when it should sometimes shout. This epic
introduces scene directives: mandatory narrator instructions composed from fired escalation
beats, narrative hints, active stakes, and faction agendas. It also adds engagement-aware
trope progression and campaign maturity tracking so the world feels alive from turn one.

Port of sq-2 Epic 61 (Active World Pacing).
Key reference: sq-2/docs/architecture/active-world-pacing-design.md.

## Background

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Orchestrator** | Turn loop: input -> intent -> agent -> narration -> patch -> broadcast |
| **Trope engine** | Tick progression, beat firing at thresholds |
| **World state agent** | Tracks consequences of player and NPC actions |
| **Prompt composition** | Agent prompts assembled from game state + context |
| **GameSnapshot** | Full game state struct with active_stakes field |

### The Gap: Reactive vs. Proactive

| Component | Current State | Gap |
|-----------|---------------|-----|
| Trope escalation beats | Fire at thresholds | Available context, not injected events |
| Passive progression | Tick per turn/day | No engagement-aware acceleration |
| Narrator trope context | Shows active tropes | Treats as optional flavor, not mandatory |
| World state agent | Tracks consequences | Purely reactive, never initiates |
| active_stakes field | Exists in GameState | Underused — present but not driving narration |

The fundamental issue: the narrator sees trope beats and world state as background color.
Nothing in the prompt composition says "you MUST weave this into your response." Scene
directives fix this by giving the narrator mandatory instructions with narrative primacy.

### Key ADR

**ADR referenced from sq-2:** Active World Pacing design doc describes the three-layer
approach — scene directives, engagement multiplier, and faction agendas — as extensions
to existing infrastructure rather than new subsystems.

## Technical Architecture

### Scene Directive Pipeline

```
Trope Engine                     World State Agent
(fired beats at threshold)       (active stakes, consequences)
         │                                │
         └────────┬───────────────────────┘
                  │
         format_scene_directive()
                  │
                  ▼
         SceneDirective {
           mandatory_elements: Vec<DirectiveElement>,
           faction_events: Vec<FactionEvent>,
           narrative_hints: Vec<String>,
         }
                  │
                  ▼
         Prompt Composition
         ┌─────────────────────────────────┐
         │ [SCENE DIRECTIVES]              │
         │ You MUST weave at least one of  │
         │ the following into your response │
         │ ...                             │
         └─────────────────────────────────┘
                  │
                  ▼
         Narrator Agent Response
         (directives woven into narration)
```

### Engagement Multiplier

```
Player engagement signal
(turns since last meaningful action)
         │
         ▼
  engagement_multiplier() ──► scaling factor (0.5x — 2.0x)
         │
         ▼
  Trope tick_progression()
  (base tick * multiplier)
         │
         ▼
  Accelerated/decelerated beat firing
  (world pushes harder when player is passive)
```

### Campaign Maturity

```
  Turn count + story beats fired
         │
         ▼
  CampaignMaturity::from_snapshot()
         │
         ├─ Fresh    (turns 0-5)   — minimal history, world is new
         ├─ Early    (turns 6-20)  — factions introduced, stakes emerging
         ├─ Mid      (turns 21-50) — established relationships, escalating tensions
         └─ Veteran  (turns 51+)   — deep history, faction conflicts in motion
         │
         ▼
  World materialization: bootstrap GameSnapshot
  with appropriate history chapters per maturity
```

### Key Types

```rust
pub struct SceneDirective {
    pub mandatory_elements: Vec<DirectiveElement>,
    pub faction_events: Vec<FactionEvent>,
    pub narrative_hints: Vec<String>,
}

pub struct DirectiveElement {
    pub source: DirectiveSource,  // TropeBeat, ActiveStake, FactionAgenda
    pub content: String,
    pub priority: DirectivePriority,
}

pub struct FactionAgenda {
    pub faction_id: String,
    pub goal: String,
    pub urgency: f32,            // 0.0-1.0, drives injection frequency
    pub scene_injection_rules: Vec<InjectionRule>,
}

pub enum CampaignMaturity {
    Fresh,
    Early,
    Mid,
    Veteran,
}
```

## Story Dependency Graph

```
2-8 (trope engine runtime)          2-5 (orchestrator turn loop)
 │                                   │
 ├──► 6-1 (scene directive formatter)│
 │     │                             │
 │     ├──► 6-2 (MUST-weave rules)  │
 │     │     │                       │
 │     │     └──► 6-9 (wire into    │
 │     │          orchestrator)      │
 │     │                             │
 │     └──► 6-4 (FactionAgenda model)│
 │           │                       │
 │           └──► 6-5 (wire factions │
 │                into directive)    │
 │                                   │
 └──► 6-3 (engagement multiplier)   └──► 6-6 (world materialization)

6-4 ──► 6-7 (mutant_wasteland faction agendas)
6-4 ──► 6-8 (low_fantasy faction agendas)
```

## Deferred (Not in This Epic)

- **Narrator compliance scoring** — Verifying the narrator actually wove the directive
  into the response. This is a Game Watcher concern (Epic 3), not a directive concern.
- **Dynamic faction creation** — LLM-generated factions that emerge from play. This
  epic works with genre-pack-defined factions only.
- **Cross-session faction memory** — Factions remembering events across campaign
  sessions. Requires persistence infrastructure beyond current scope.
- **Player-facing faction UI** — Showing faction relationships and agendas in the
  React client. UI work is separate from the engine extension.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-8: Trope engine runtime (6-1 and 6-3 depend on this)
- Story 2-5: Orchestrator turn loop (6-6 and 6-9 depend on this)

### No New Agents
This epic extends three existing systems — trope engine, world state agent, and prompt
composition — rather than introducing new agent types. The scene directive formatter is
a pure function, not an LLM call.

## Success Criteria

During a playtest session:
1. Scene directives appear in the narrator prompt every turn with MUST-weave language
2. Fired trope beats and active stakes are formatted as mandatory narrative elements
3. Trope progression accelerates when the player is passive (engagement multiplier)
4. Faction agendas inject world-driven events into the narrator prompt
5. A fresh campaign starts sparse; a veteran campaign starts with rich history chapters
6. The world initiates events — NPCs act on faction agendas without player prompting
7. Genre pack authors can define faction agendas in YAML (mutant_wasteland, low_fantasy)
