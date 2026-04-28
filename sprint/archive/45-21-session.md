---
story_id: "45-21"
jira_key: null
epic: "45"
workflow: "trivial"
---
# Story 45-21: NPC registry HP/max_hp populated from combat stats

## Story Details
- **ID:** 45-21
- **Jira Key:** (none — no Jira sync)
- **Epic:** 45 — Playtest 3 Closeout — MP Correctness, State Hygiene, and Post-Port Cleanup
- **Workflow:** trivial
- **Type:** bug
- **Points:** 2
- **Priority:** P1
- **Stack Parent:** none
- **Repo:** sidequest-server

## Problem Statement

Playtest 3 (2026-04-19) Orin session: Crawling Scavenger NPC registered in `npc_registry` but combat stats never written to the registry entry. Registry entry showed HP=0/max_hp=0, making it appear always-dead to any HP-check subsystem.

**Root cause:** When combat stats are emitted by the narrator/combat extractor, the HP and max_hp fields must be written into the npc_registry entry. Currently they are not.

**Impact:** HP-check gates and mechanics that query `npc_registry[npc_id]` to determine creature liveness receive false data and make wrong decisions.

## Success Criteria

1. When combat stats are emitted (narrator/extractor publishes), HP/max_hp are written to npc_registry entry
2. Registry entry cannot report HP=0 unless the NPC is actually dead
3. OTEL span emitted on registry write with HP/max_hp values
4. No regression on existing combat stats flow

## Workflow Tracking
**Workflow:** trivial
**Phase:** setup
**Phase Started:** 2026-04-28

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-28 | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

- **Dev (Improvement, non-blocking):** The validator's `patch_legality_check` was already coded against `getattr(npc, "hp", None)` / `getattr(npc, "hp_max", None)` even though `NpcRegistryEntry` had neither field. The dead-actor check silently no-op'd for every NPC. Adding `hp`/`max_hp` fields means that pre-existing check now actually fires — mechanically why the Playtest 3 bug was invisible to the validator.
- **Dev (Improvement, non-blocking):** `sidequest/server/rest.py` hardcoded `"hp": 0, "max_hp": 0` in the GM-panel registry view. That is the literal source of the "HP=0/max_hp=0" string in the Orin save inspection — never sourced from the entry. Now reads `entry.hp`/`entry.max_hp` (None → 0 in the JSON projection only; the entry preserves None semantics).
- **Dev (Question, non-blocking):** Story scope is the encounter-START seam. Damage during combat advances `opponent_metric.current` but does NOT yet sync back into `entry.hp`. AC2 is satisfied at start (HP > 0 unless threshold=0) but a follow-up story should sync HP after each `apply_beat` and on encounter resolution so a victorious-player encounter end leaves dead opponents at hp=0 in the registry.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
