---
id: 25
title: "Pacing Detection"
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

# ADR-025: Pacing Detection

> Ported from sq-2. Language-agnostic narrative system.

## Decision
Orchestrator detects stalled narrative momentum by counting "quiet turns" — turns where no location, combat, NPC, or quest changes occurred.

### Quiet Turn Detection
```rust
fn is_quiet_turn(pre: &GameState, post: &GameState) -> bool {
    pre.location == post.location
        && pre.combat == post.combat
        && pre.npcs_present == post.npcs_present
        && pre.quest_log == post.quest_log
}
```

### Pacing Hint Injection
After 3+ quiet turns, inject a `[PACING]` hint into the narrator prompt suggesting escalation. The narrator is free to act on it or not.

### Trope Escalation
When a trope beat fires, inject an `[ESCALATION]` block with the beat description. This provides specific narrative direction rather than generic "make something happen."

### Player Action Scanning
Player actions are scanned for accelerators ("attack", "run", "challenge") and decelerators ("wait", "rest", "camp") that adjust trope progression rate.

## Consequences
- Stories don't stall even with passive players
- Zero LLM cost — pure keyword matching and state comparison
- Narrator retains agency — hints are suggestions, not commands
