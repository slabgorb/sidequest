# ADR-029: Guest NPC Players

> Ported from sq-2. Proposed feature.

## Status
Proposed

## Decision
Guest players can control consequential NPCs with enriched asymmetric narration via an inverted PerceptionRewriter.

### Concept
- NPC guest receives narration from the NPC's perspective (partial truths, motives)
- Protagonist players see only visible NPC behavior
- PerceptionRewriter runs in inverted mode for the NPC player
- NPC disposition system merges guest input with AI disposition

## Consequences
- Adds social deduction element to multiplayer
- Requires PerceptionRewriter (ADR-028) to be fully implemented first
- NPC guest's actions are constrained by NPC personality and disposition
