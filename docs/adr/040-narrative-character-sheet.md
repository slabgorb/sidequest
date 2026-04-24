---
id: 40
title: "Narrative Character Sheet (No Raw Stats)"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [narrator]
implementation-status: live
implementation-pointer: null
---

# ADR-040: Narrative Character Sheet (No Raw Stats)

> Retrospective — documents a decision already implemented in the codebase.

## Context
SideQuest is a narrative-first game. The narrator speaks in genre voice — pulp noir, space opera, low fantasy — and the player experiences the world through that lens. Exposing raw mechanical values (HP: 34/50, Strength: 16, AC: 14) on the character sheet breaks the diegetic frame. A character who is "badly wounded" is narratively present; a character at "68% HP" is a spreadsheet entry. Beyond immersion, the character sheet is serialized over WebSocket as a protocol type — if raw numbers live in the protocol, UI formatting choices become load-bearing protocol contracts that are painful to change.

## Decision
The `NarrativeSheet` struct contains no raw numerical values. All game state is expressed in narrative terms before it leaves the game layer.

HP is rendered via `describe_health()`, which bands the ratio into six states:

```
1.0        → "in good health"
0.75–1.0   → "lightly wounded"
0.50–0.75  → "wounded"
0.25–0.50  → "badly wounded"
0.10–0.25  → "near death"
0.0–0.10   → "fallen"
```

Abilities are described using `genre_description` from the genre pack YAML — the flavor text written by the world builder — never `mechanical_effect`. A rogue's perception ability in pulp noir reads "You have an uncanny sense for danger," not "+2 to Perception checks."

This is enforced at the type level: `NarrativeSheet` doesn't carry raw fields. The conversion from mechanical `Character` state to narrative presentation happens inside the game crate, not in the UI or the protocol layer.

Implemented in: `sidequest-game/src/narrative_sheet.rs`

## Alternatives Considered

**Raw stats with UI formatting** — rejected: formatting logic in the UI means the protocol carries raw numbers. Any design change to how stats are displayed requires a protocol version bump. It also creates a gap where API consumers (future CLI client, GM tools) receive raw numbers and must re-implement the narrative formatting.

**Dual sheets (raw + narrative)** — rejected: doubles the surface area. Raw stats inevitably leak into UI code "just for the GM panel" and then everywhere. One authoritative representation eliminates the class of bugs where the two diverge.

**Optional toggle (narrative/mechanical mode)** — rejected: undermines the design intent. A player who can switch to number view stops experiencing the world narratively. The game is not designed to be played as a numbers game; the option to do so degrades the experience even for players who never use it, because it signals the "real" values are the numbers.

## Consequences

**Positive:**
- Protocol is stable against display changes — reworking health bands or ability descriptions doesn't touch the WebSocket contract.
- Narrator and UI speak the same language. The narrator's prose about being "near death" matches the character sheet, reinforcing immersion.
- Genre voice is enforced mechanically: genre pack authors write `genre_description` and that text is what players see, preserving world-building craft.
- Eliminates a category of UI bugs where raw values render in the wrong context.

**Negative:**
- GM tooling that needs mechanical precision (balancing, debugging) must go through OTEL telemetry or a separate internal representation — `NarrativeSheet` alone is insufficient for game masters who need exact values.
- Six fixed health bands may not fit all genres well; some genre packs may want more or fewer gradations. Extending the banding system requires a code change, not just YAML configuration.
