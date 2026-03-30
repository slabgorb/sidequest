---
story_id: "6-7"
epic: "6"
workflow: "trivial"
---
# Story 6-7: Faction agendas for mutant_wasteland genre pack worlds

## Story Details
- **ID:** 6-7
- **Epic:** 6 (Active World & Scene Directives)
- **Title:** Faction agendas for mutant_wasteland genre pack worlds
- **Points:** 2
- **Priority:** P2
- **Workflow:** trivial
- **Status:** in progress
- **Stack Parent:** none (standalone world-building)

## Story Context

This story populates faction agendas for the mutant_wasteland genre pack. Faction agendas were defined in story 6-4 as a schema for faction goals, urgency, and scene injection rules, and wired into the scene directive in story 6-5.

The mutant_wasteland world (flickering_reach) contains four cultures/factions:
1. **Scrapborn** — Urban ruin-dwellers who build from salvage
2. **Greenfolk** — Plant-mutant communities in overgrown ruins
3. **Drifters** — Nomadic steppe-wanderers on mutant mounts
4. **Vaultborn** — Descendants of sealed bunker communities

## Workflow Tracking
**Workflow:** trivial
**Phase:** implementation
**Phase Started:** 2026-03-27 18:00 UTC
**Phase Completed:** 2026-03-27 18:05 UTC

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-27 18:00 | 2026-03-27 18:00 | immediate |
| implementation | 2026-03-27 18:00 | 2026-03-27 18:05 | 5 min |

## Deliverables — COMPLETE

Created `faction_agendas.yaml` at:
`/Users/keithavery/Projects/oq-1/genre_packs/mutant_wasteland/worlds/flickering_reach/faction_agendas.yaml`

Faction agendas defined for all four factions in flickering_reach:

1. **Scrapborn** — simmering urgency
   - Goal: Expand territory and secure salvage routes
   - Scene Event: Scrapborn scavengers probe deeper into ruins
   - Relations: competitive with Greenfolk, neutral with Drifters, hostile with Vaultborn

2. **Greenfolk** — pressing urgency
   - Goal: Heal the land through mutagenic gardening
   - Scene Event: Expansion vines creep across the black glass plain
   - Relations: competitive with Scrapborn, protective of Drifters, distant from Vaultborn

3. **Drifters** — pressing urgency
   - Goal: Maintain freedom and protect open routes
   - Scene Event: Caravan moves across glass plains with mutant mounts
   - Relations: neutral with Scrapborn, wary of Greenfolk, cooperative with Vaultborn

4. **Vaultborn** — dormant urgency
   - Goal: Preserve pre-war archives and maintain sealed infrastructure
   - Scene Event: Vault community emergence team surveys the wasteland
   - Relations: hostile with Scrapborn, indifferent to Greenfolk, cooperative with Drifters

## Delivery Findings

No upstream findings. Faction agendas were straightforward world-building based on lore established in cultures.yaml and world.yaml.

## Design Deviations

None. Implementation matches story intent directly.
