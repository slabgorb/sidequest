# Epic 10: NPC Personality Engine — OCEAN Behavioral Model

## Overview

Add Big Five (OCEAN) personality profiles to NPCs as structured behavioral shorthand for the
narrator. Each NPC carries five float dimensions — Openness, Conscientiousness, Extraversion,
Agreeableness, Neuroticism — scored 0.0 to 10.0. The narrator reads these scores as natural
language summaries ("reserved and meticulous") and adjusts NPC voice and behavior accordingly.

This is a p2 quality-of-depth epic. It doesn't unlock new game mechanics — it makes NPC
behavior more consistent and observable. A high-Neuroticism NPC panics under pressure every
time, not just when the LLM happens to generate that. The profiles give the narrator a
deterministic personality anchor rather than relying on freehand characterization.

## Background

### What Already Exists (prerequisite from Epic 2)

| Component | What's Done |
|-----------|-------------|
| **NPC struct** | Characters with disposition (-15 to +15) and attitude system |
| **Orchestrator** | Turn loop: input → intent → agent → narration → patch → broadcast |
| **Agent execution** | Claude CLI subprocess, prompt composition, JSON extraction |
| **Genre packs** | YAML-defined NPC archetypes loaded by the API |
| **World state agent** | Proposes state mutations after game events |

The OCEAN system layers on top of disposition/attitude — it doesn't replace them.
Disposition remains the NPC-to-player relationship score. OCEAN describes *how* the NPC
behaves regardless of who they're talking to.

### Python Reference: sq-2 Epic 64

The original Python implementation lives in sq-2. Key design decisions carried forward:

- Five floats, not enums or buckets — continuous range allows nuanced blends
- Genre archetypes define baseline profiles (a scholarly wizard: high O, high C, low E)
- Random NPC generation applies variance from the archetype baseline
- Behavioral summaries are deterministic text derived from score ranges
- Shifts are structured events, not silent mutations

### Key Insight

OCEAN profiles solve the "NPC amnesia" problem. Without them, the narrator has no
persistent model of personality — an NPC might be bold in one scene and timid in the next.
The profile anchors behavior across turns without constraining the narrator's creative range.

## Technical Architecture

### Data Model

```rust
pub struct OceanProfile {
    pub openness: f64,         // 0.0–10.0: curiosity, creativity
    pub conscientiousness: f64, // 0.0–10.0: discipline, reliability
    pub extraversion: f64,     // 0.0–10.0: sociability, assertiveness
    pub agreeableness: f64,    // 0.0–10.0: cooperation, empathy
    pub neuroticism: f64,      // 0.0–10.0: anxiety, emotional volatility
}

pub enum OceanDimension {
    Openness,
    Conscientiousness,
    Extraversion,
    Agreeableness,
    Neuroticism,
}

pub struct OceanShift {
    pub dimension: OceanDimension,
    pub old_value: f64,
    pub new_value: f64,
    pub cause: String,         // "betrayed by trusted ally"
    pub turn_id: u64,
}
```

### Data Flow

```
Genre Pack YAML                     NPC Creation
─────────────────                   ────────────
archetype: scholar_wizard           generate_npc()
  ocean_baseline:                       │
    openness: 8.5                       ├─ load archetype baseline
    conscientiousness: 7.0              ├─ apply random variance (±1.5)
    extraversion: 3.0                   ├─ clamp to 0.0–10.0
    agreeableness: 6.0                  └─ attach OceanProfile to NPC
    neuroticism: 4.0

During Play                         Narrator Prompt
───────────                         ──────────────
world_state_agent                   compose_prompt()
    │                                   │
    ├─ detects personality-             ├─ read NPC.ocean_profile
    │  relevant event                   ├─ generate behavioral summary:
    │                                   │    "reserved and meticulous,
    └─ proposes OceanShift              │     prone to quiet anxiety"
        │                               └─ inject into narrator context
        ├─ apply to NPC profile
        ├─ log structured event
        └─ (future) index as
           lore fragment
```

### Agreeableness ↔ Disposition Bridge

```
OceanProfile.agreeableness ───► influences disposition change rate
                                 high A = faster positive drift
                                 low A  = slower forgiveness

Disposition system (-15 to +15) remains the source of truth for
NPC-to-player relationship. Agreeableness modulates how quickly
disposition moves, not where it sits.
```

### Behavioral Summary Generation

Score ranges map to natural language descriptors. The summary is deterministic —
same scores always produce the same text. Example mappings:

```
Dimension        Low (0-3)           Mid (4-6)         High (7-10)
─────────        ─────────           ─────────         ──────────
Openness         conventional        pragmatic         curious, inventive
Conscientiousness careless           steady            meticulous, driven
Extraversion     reserved, quiet     balanced          gregarious, bold
Agreeableness    suspicious, blunt   fair-minded       warm, trusting
Neuroticism      unflappable         even-keeled       anxious, volatile
```

## Story Dependency Graph

```
2-5 (orchestrator turn loop)
 │
 └──► 10-1 (OCEAN fields on NPC)
       │
       ├──► 10-2 (genre archetype baselines + random gen)
       │
       ├──► 10-3 (behavioral summary text)
       │     │
       │     └──► 10-4 (narrator reads OCEAN)
       │
       ├──► 10-5 (OCEAN shift log)
       │     │
       │     └──► 10-6 (world state agent proposes shifts)
       │
       └──► 10-7 (agreeableness ↔ disposition bridge)

10-8 (backfill genre pack archetypes) — parallel, depends only on 10-2 format
```

## Deferred (Not in This Epic)

- **OCEAN-driven dialogue style** — Adjusting word choice, sentence length, vocabulary
  based on personality scores. The narrator gets a summary; fine-grained style control
  is a future refinement.
- **Player-visible personality** — Exposing OCEAN scores or summaries in the UI.
  Currently this is narrator-only context. UI display is a UX decision for later.
- **OCEAN influence on combat/chase** — Personality affecting mechanical decisions
  (e.g., high-N NPC more likely to flee). Deferred to avoid coupling personality
  to game mechanics prematurely.
- **Lore indexing of shifts** — OCEAN shifts are logged as structured events now.
  Indexing them as LoreFragments for RAG retrieval depends on Epic 11.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-5: Orchestrator turn loop (10-1 depends on NPC being part of game state)
- NPC struct and disposition system must be in place

### Ideally Before
- Epic 11 (Lore system): Shift events can be indexed as lore fragments for
  cross-session retrieval. Without Epic 11, shifts are logged but not queryable
  by agents. This is a soft dependency — the epic works without it.

### No Dependency On
- Epic 3 (Game Watcher): OCEAN telemetry is a natural fit for the watcher, but
  the watcher observes whatever exists. No coordination needed.

## Success Criteria

During a playtest session:
1. Every NPC has an OCEAN profile visible in game state inspection
2. Genre pack archetypes define baseline OCEAN profiles; randomly generated NPCs
   show variance from those baselines
3. The narrator's description of NPC behavior is consistent with their OCEAN scores
   across multiple turns (a low-E NPC stays reserved, a high-N NPC reacts emotionally)
4. When a significant event occurs, the world state agent can propose an OCEAN shift
   with cause attribution
5. Shift history is visible in the structured log
6. The behavioral summary text is deterministic — same scores produce same descriptors
7. Agreeableness visibly modulates how quickly disposition changes toward the player
