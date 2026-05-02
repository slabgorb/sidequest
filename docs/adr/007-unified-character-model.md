---
id: 7
title: "Unified Character Model"
status: accepted
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: [14, 78, 81, 82]
tags: [core-architecture]
implementation-status: live
implementation-pointer: null
---

# ADR-007: Unified Character Model

## Implementation status (2026-05-02)

**Live model: `sidequest-server/sidequest/game/character.py:66` (`class Character(BaseModel)`).** The full field list lives there and continues to evolve; this ADR captures only the unification decision and ordering principle, not the per-field schema.

Major shifts since the 2026-03-25 sketch:

- **HP / max_hp / AC removed per ADR-014.** The original Rust struct showed `hp: i32, max_hp: i32, ac: i32` — these fields no longer exist. Composure (edge) replaced HP; access via `Character.edge` and `Character.max_edge` properties (computed from `core.edge.current` / `core.edge.max`). See ADR-014 (Diamonds and Coal) and ADR-078 (Edge/Composure).
- **`level`, `inventory`, `statuses`, `progression` are no longer top-level fields.** Inventory and progression were unbundled and handled elsewhere; archetype/affinity/ability state replaces the original "level + class" advancement axis.
- **Name decomposed.** `name: String` is now `first_name`, `last_name`, `nickname` plus derived display.
- **New top-level fields** (not in original sketch):
  - `abilities: list[AbilityDefinition]` — per-character powers (ADR-078, ADR-081)
  - `affinities: list[AffinityState]` — replaces the original `relationships: Vec<Relationship>` axis
  - `known_facts: list[KnownFact]` — P1-required narrator continuity (see comment at `character.py:99`)
  - `pronouns`, `is_friendly`, `resolved_archetype`, `archetype_provenance`, `background`, `drive`
- **Personality** as a top-level field is gone; the equivalent narrative shape is folded into `narrative_state` and the genre-pack archetype.

What's preserved end-to-end: the principle that **one `Character` object carries both narrative identity and mechanical stats, narrative fields first**. The narrator and world-state agents both read the single struct; the character builder outputs one object; save/load serializes one struct.

The Rust struct example from the original ADR has been removed rather than preserved as port-era residue, because it shows a deliberately-removed shape (HP/AC/level) and risks misreading as current canon.

Drift watch — if any of the following happens, this ADR is wrong:
- A separate `StatBlock` / `MechanicalCharacter` / `CharacterSheet` model is introduced parallel to `Character` for the mechanical fields.
- HP, max_hp, or AC fields are reintroduced (would also conflict with ADR-014).

## Context
Characters need both narrative identity (name, backstory, narrative state, hooks, affinities) and mechanical stats (class, abilities, composure, archetype). Splitting these creates synchronization problems.

## Decision
A single `Character` struct combines both concerns, with narrative fields first. The canonical schema lives in `sidequest-server/sidequest/game/character.py:66`.

### Why Unified
1. Agents need both simultaneously — narrator reads narrative state and abilities together.
2. World state patches touch both kinds of fields in one turn.
3. Character builder outputs one object.
4. Save/load serializes one struct.

### Philosophy
Narrative-first in field ordering and design. The mechanical stats serve the narrative, not the other way around (SOUL principle: Tabletop First, Crunch in the Genre / Flavor in the World).

## Consequences
- Single source of truth for each character.
- No synchronization between "narrative character" and "stat block."
- Struct is larger but coherent. New per-character subsystems (abilities, affinities, known facts) extend `Character` rather than living in side-tables.
