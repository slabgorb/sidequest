---
id: 29
title: "Guest NPC Players"
status: historical
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [28]
tags: [multiplayer]
implementation-status: retired
implementation-pointer: null
---

> **HISTORICAL 2026-05-02 — NOT BUILDING.**
>
> Carried as `proposed` for six weeks with zero implementation traction.
> The dependency this design named ([ADR-028 PerceptionRewriter](028-perception-rewriter.md))
> went live in that period; ADR-029 did not follow. Marked historical
> rather than `deprecated` per the schema definition (deprecated requires
> a prior `accepted` state — this never advanced past `proposed`).
>
> The only code fingerprint of this design is a dead type-alias literal:
> `AllScope = Literal["protagonists", "party_plus_guest_npcs"]` at
> `sidequest-server/sidequest/genre/models/visibility.py:23`. The literal
> `"party_plus_guest_npcs"` has no consumer in the codebase and should be
> removed in a future cleanup pass — leaving it in is the same anticipatory-
> typing-as-drift pattern flagged on `mood_aliases` during the ADR-033 audit.
>
> The body below preserves the original 2026-03-25 sketch as historical
> record. If guest-NPC asymmetric-info gameplay is revisited, a fresh ADR
> with real protocol design — sealed-letter mechanics, NPC-side prompt
> shape, action-budget rules, godmoding prevention — should be written
> rather than reviving this one.

# ADR-029: Guest NPC Players

> Ported from sq-2. Proposed feature.

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
