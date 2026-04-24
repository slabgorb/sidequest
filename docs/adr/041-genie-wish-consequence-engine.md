---
id: 41
title: "Genie Wish / Consequence Engine"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [npc-character]
implementation-status: drift
implementation-pointer: 87
---

# ADR-041: Genie Wish / Consequence Engine

> Retrospective — documents a decision already implemented in the codebase.

## Context
Players in open-ended narrative games frequently attempt power-grab actions: "I kill all the enemies," "I teleport to the treasure," "I summon a weapon that defeats everyone." A system that hard-rejects these breaks immersion and punishes player creativity. A system that silently ignores them trains players that ambition has no consequence. A system that passes them to the narrator without mechanical scaffolding produces inconsistent outcomes — Claude will sometimes grant wishes freely, sometimes refuse, with no coherent world logic behind either choice. The game needed a principled way to honor player agency while maintaining world integrity and tonal consistency.

## Decision
Player actions classified as `GenieWish` are granted — always — but with a mechanically-assigned consequence category. The consequence type rotates through four categories in sequence to prevent repetitive patterns:

1. **Backfire** — the wish grants itself but rebounds on the wisher
2. **Attention** — the wish succeeds but draws dangerous notice
3. **Cost** — the wish succeeds but extracts an immediate price
4. **Curse** — the wish succeeds but leaves a persistent negative condition

The active `ConsequenceCategory` is passed to the narrator as a directive in the prompt context. The narrator flavors the consequence narratively in genre voice — it never appears as a mechanical notification. From the player's perspective, the world has rules that enforce themselves through story.

The rotation is mechanical (not LLM-determined) to guarantee players who repeatedly attempt power-grabs cycle through distinct failure modes. The narrator handles tone; the engine handles pattern.

Implemented in: `sidequest-game/src/consequence.rs` — `GenieWish`, `WishStatus`, `ConsequenceCategory`

## Alternatives Considered

**Hard rejection ("you can't do that")** — rejected: breaks the cardinal rule of improv and narrative games. Refusal trains players to avoid ambition rather than engage creatively. The game world should feel responsive, not like a rules lawyer.

**Silent ignoring** — rejected: grants the wish with no consequence, which breaks world integrity and removes tension from player choices. Players quickly learn ambition is free.

**Pure LLM judgment** — rejected: Claude will inconsistently enforce consequences. In one scene a power-grab is granted freely; in another it's penalized arbitrarily. Without mechanical scaffolding, players have no sense that the world has coherent rules. Also susceptible to prompt drift over long sessions.

**Player-visible consequence menu** — rejected: externalizes the magic. Part of the system's elegance is that players experience consequences as natural story outcomes, not as a game mechanic they can game.

## Consequences

**Positive:**
- "Yes, and" improv principle is mechanically enforced — the system never refuses player intent.
- Rotating consequence categories prevent the most common failure mode of LLM-narrated consequences: repetition. Players who repeatedly attempt power-grabs get genuinely different story outcomes.
- Consequence type is a directive, not a mechanical effect — the narrator handles all flavor, keeping the system purely narrative without requiring mechanical state for each consequence type.
- Tonal consistency: the world feels like it has rules without the rules ever being visible to the player.

**Negative:**
- Rotation is session-scoped; across multiple sessions players may notice the pattern if they track it deliberately.
- The four categories are fixed in code. Adding a fifth type (e.g., "Delay") requires a code change. Genre packs cannot customize consequence types via YAML.
- Classification of actions as `GenieWish` vs. ambitious-but-legal is a judgment call made upstream (by the intent classifier). Misclassification either over-punishes normal play or lets genuine power-grabs through without consequence.
