---
story_id: "16-12"
jira_key: "none"
epic: "16"
workflow: "tdd"
---
# Story 16-12: Wire genre resources — Luck, Humanity, Heat, Fuel-at-rest as ResourcePool instances

## Story Details
- **ID:** 16-12
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 16 — Genre Mechanics Engine — Confrontations & Resource Pools
- **Repositories:** sidequest-api, sidequest-content
- **Branch:** feat/16-12-wire-genre-resources
- **Points:** 3
- **Priority:** p1
- **Status:** in-progress

## Context

With ResourcePool (16-10) and threshold→KnownFact pipeline (16-11) built, this story wires genre-specific resources into the four genre packs that need them. Each genre declares resources in rules.yaml with appropriate bounds, thresholds, and behavior.

**Dependency chain:**
- 16-10 (ResourcePool struct + YAML schema) — COMPLETE
- 16-11 (Resource threshold → KnownFact pipeline) — COMPLETE
- 16-12 (Wire genre resources) ← current

## Acceptance Criteria

1. **spaghetti_western** rules.yaml declares Luck resource (0-6, voluntary, thresholds at 1 and 0)
2. **neon_dystopia** rules.yaml declares Humanity resource (0-100, involuntary, thresholds at 50/25/0)
3. **pulp_noir** rules.yaml declares Heat resource (0-5, involuntary, decay 0.1/turn)
4. **road_warrior** rules.yaml declares Fuel resource (tracked as resource, transfers to RigStats on confrontation)
5. Genre loader parses resource declarations from rules.yaml and inits ResourcePools on GameSnapshot
6. Each genre's resources validate bounds correctly
7. Integration: resource declarations load → pools init → patches apply → thresholds fire → KnownFacts mint

## Workflow Phases

| Phase | Owner | Status |
|-------|-------|--------|
| setup | sm | complete |
| red | tea | in-progress |
| green | dev | pending |
| review | reviewer | pending |
| finish | sm | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-04-05T09:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T09:00Z | 2026-04-05T09:00Z | 0m |
| red | 2026-04-05T09:00Z | — | — |

## Delivery Findings

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings yet.

## Design Deviations

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.
