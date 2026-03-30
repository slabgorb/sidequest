---
story_id: "15-6"
jira_key: "none"
epic: "15"
workflow: "tdd"
---
# Story 15-6: Combat engine wiring — intent router fires COMBAT_EVENT but combat system never engages, enemies/turn_order always empty

## Story Details
- **ID:** 15-6
- **Jira Key:** none (personal project)
- **Epic:** 15 (Playtest Debt Cleanup — Stubs, Dead Code, Disabled Features)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 5
- **Priority:** p0
- **Repos:** sidequest-api

## Story Context

**Problem:**
The intent router correctly classifies combat actions (IntentRouter → creature_smith agent), and COMBAT_EVENT messages fire over WebSocket. But the actual combat system never engages — enemies array is always empty, turn_order is empty, current_turn is empty. The combat is purely narrated, not structured.

**Evidence from playtest (2026-03-29):**
Actions like "attack the nearest hostile creature" produce combat-mood narration and COMBAT_EVENT with:
```json
{"in_combat": true, "enemies": [], "turn_order": [], "current_turn": ""}
```
HP changes happen narratively (state_delta shows HP going down) but not through the combat system's mechanics.

**Acceptance Criteria:**

1. When intent_route classifies an action as Combat, the GameOrchestrator must detect the Intent::Combat variant
2. Combat system spawns enemies from genre pack's creature definitions based on context (location, narrative mood, difficulty)
3. Turn order is initialized with player + spawned creatures
4. COMBAT_EVENT message includes populated enemies array and turn_order
5. Combat rounds execute structured mechanics (attack rolls, damage resolution, status effects)
6. HP tracking runs through Combat::resolve_action(), not just narration state deltas
7. End-of-combat cleanup (remove combatants, award rewards/loot) triggers when enemies defeated
8. Full e2e test: single-player combat scenario from intent classification through victory condition

**Why This Matters:**
Half-wired features create confusion: the classification works, the narration works, the WebSocket message fires — but the actual game system is stubbed. This prevents combat from having any mechanical weight and breaks immersion. Players see HP numbers moving narratively but can't understand the rules or predict outcomes.

**Repos & Files:**

Core combat system (sidequest-api/crates/sidequest-game/src/):
- `combat.rs` — Combat state, turn order, resolution logic
- `creatures.rs` — Creature definitions and AI
- `orchestrator.rs` — GameOrchestrator, intent dispatch

Server wiring (sidequest-api/crates/sidequest-server/src/):
- `shared_session.rs` — Game session lifecycle, intent routing dispatch
- `handlers.rs` — GameAction → intent → orchestrator pipeline

Protocol (sidequest-api/crates/sidequest-protocol/src/):
- `lib.rs` — COMBAT_EVENT message structure

Genre data:
- `genre_packs/*/creatures.yaml` — Creature definitions

Tests:
- `sidequest-api/tests/` — Combat round resolution, enemy spawning, turn order init

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-30T20:34:00Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-30T20:34:00Z | - | - |

## Delivery Findings

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
