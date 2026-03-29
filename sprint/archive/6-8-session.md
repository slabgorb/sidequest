---
story_id: "6-8"
jira_key: null
epic: "6"
workflow: "trivial"
---
# Story 6-8: Faction agendas for elemental_harmony/shattered_accord genre pack worlds

## Story Details
- **ID:** 6-8
- **Jira Key:** N/A (personal project)
- **Epic:** 6 — Active World & Scene Directives
- **Workflow:** trivial
- **Points:** 2
- **Priority:** p2
- **Stack Parent:** none

## Story Summary

Define faction agendas for the elemental_harmony genre pack worlds. This is a continuation of story 6-7, which completed faction agendas for mutant_wasteland's flickering_reach world. Story 6-8 adds agendas for elemental_harmony's two worlds:
- **Shattered Accord** — Post-Shattering world with 6+ factions pursuing incompatible agendas (Jade Reclamation, Accord Reborn, Drowned Covenant, Sealed Gate, Monsoon-Tide Pact, and others)
- **Burning Peace** — Isolationist Ember Isles with 5+ factions (Burning Throne, Outer Flame, Imperial Shrine, Hidden Way, Shadow Schools)

Each world already has detailed faction lore in its `lore.yaml`. The task is to extract that lore into `faction_agendas.yaml` files structured like the mutant_wasteland example, with goal, urgency level, scene_event, and faction relationships.

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-03-27

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27 | - | - |

## Delivery Findings

No upstream findings.

## Design Deviations

No deviations recorded.

## Implementation Notes

### Reference Material
- Story 6-7 completed mutant_wasteland/flickering_reach/faction_agendas.yaml (4 factions)
- Shattered Accord lore.yaml contains 6+ detailed faction descriptions with disposition, goals, and relationships
- Burning Peace lore.yaml contains 5+ detailed faction descriptions with disposition, goals, and relationships

### Output Artifacts
1. genre_packs/elemental_harmony/worlds/shattered_accord/faction_agendas.yaml
2. genre_packs/elemental_harmony/worlds/burning_peace/faction_agendas.yaml

Both files should follow the mutant_wasteland format:
- Header comment explaining urgency levels
- factions array with: name, description, goal, urgency, scene_event, relationships dict
- Urgency levels: dormant, simmering, pressing, critical
- Relationships describe inter-faction dynamics (hostile, competitive, protective, wary, neutral, cooperative, indifferent, distant)

### Context for Scene Events

**Shattered Accord** context:
- The Shattering tore the barrier between mortal and spirit worlds
- Spirits flood through unchecked (fire, ocean, wind, earth, etc.)
- Different nations practice elemental channeling differently
- Central conflict: restore the Accord Eternal (seal spirits) or master the new reality

**Burning Peace** context:
- 80-year peace enforced by Tokigane fire channeling supremacy
- Fire channelers feel something coming; spirit activity increasing
- Secret island uprising 40 years ago was sealed away
- Volcano Mount Kasai rumbles with displeasure
- World is changing; the peace is fragile
