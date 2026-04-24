---
id: 18
title: "Trope Engine"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [game-systems]
implementation-status: drift
implementation-pointer: 87
---

# ADR-018: Trope Engine

> Ported from sq-2. Language-agnostic narrative system.

## Context
Stories need momentum. Genre-defined narrative patterns (tropes) provide a skeleton that ensures the story progresses even during quiet periods.

## Decision
Tropes are genre-defined narrative patterns that track a lifecycle with escalation beats.

### Lifecycle
```
DORMANT → ACTIVE → PROGRESSING → RESOLVED
```

### Escalation Beats
Each trope defines beats that fire at progression thresholds:

```yaml
tropes:
  reluctant_hero:
    description: "Hero resists the call to adventure"
    beats:
      - threshold: 0.25
        description: "First refusal of the quest"
        npcs_involved: ["mentor"]
        stakes: "low"
      - threshold: 0.50
        description: "Consequences of inaction become visible"
        stakes: "medium"
      - threshold: 0.75
        description: "Personal cost forces commitment"
        stakes: "high"
      - threshold: 1.0
        description: "Full acceptance of the quest"
        stakes: "climactic"
    rate_per_turn: 0.02
    rate_per_day: 0.05  # between-session advancement
```

### Passive Advancement
Tropes tick forward via `rate_per_turn` during gameplay and `rate_per_day` between sessions, ensuring they don't stall even if the player ignores them.

### Beat Deduplication
`fired_beats: HashSet<(String, f32)>` prevents the same beat from firing twice.

## Consequences
- Stories have built-in momentum independent of player choices
- Genre packs define narrative pacing without code
- Between-session advancement keeps the world "alive"
