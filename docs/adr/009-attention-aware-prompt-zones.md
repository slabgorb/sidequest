---
id: 9
title: "Attention-Aware Prompt Zones"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [prompt-engineering]
implementation-status: live
implementation-pointer: null
---

# ADR-009: Attention-Aware Prompt Zones

> Ported from sq-2. Language-agnostic prompt engineering pattern.

## Context
LLMs have non-uniform attention across their context window. The beginning and end receive higher attention than the middle.

## Decision
Prompts are assembled into three zones:

| Zone | Attention | Content |
|------|-----------|---------|
| **EARLY** | High | Identity, SOUL principles, critical rules |
| **VALLEY** | Lower | Lore, game state, character data, firm/coherence rules |
| **LATE** | High | Before-you-respond checklist, user input |

### Assembly Order
1. Agent identity and role description (EARLY)
2. SOUL principles (EARLY)
3. Critical rules (EARLY)
4. Firm rules (VALLEY)
5. Genre tone and style (VALLEY)
6. Lore fragments (VALLEY)
7. Game state summary (VALLEY)
8. Character data (VALLEY)
9. Coherence rules (VALLEY)
10. Before-you-respond verification (LATE)
11. Player input / action (LATE)

### Implementation
```rust
pub struct PromptSection {
    pub name: String,
    pub zone: Zone,
    pub content: String,
    pub weight: f32,  // genre pack can adjust importance
}

pub enum Zone { Early, Valley, Late }
```

Genre packs can adjust section weights to signal relative importance within a zone.

## Consequences
- Critical content is always in high-attention positions
- Lore and state fill the middle (acceptable lower attention)
- Verification checklist is the last thing the agent sees before responding
