---
story_id: "15-26"
jira_key: "none"
epic: "15"
workflow: "tdd"
---
# Story 15-26: Wire select_npc_action — NPC autonomous actions not invoked from server

## Story Details
- **ID:** 15-26
- **Jira Key:** none (personal project)
- **Workflow:** tdd
- **Epic:** 15 — Playtest Debt Cleanup — Stubs, Dead Code, Disabled Features
- **Repository:** sidequest-api (Rust backend)
- **Branch:** feat/15-26-wire-select-npc-action
- **Points:** 3
- **Priority:** p2
- **Status:** in-progress

## Context

Epic 15 addresses technical debt identified in the 2026-03-29 post-playtest audit. This story fixes an architectural gap: **NPC autonomous actions are fully implemented but never invoked from the server dispatch pipeline.**

### Current State
- **npc_actions.rs** contains fully implemented and tested functions:
  - `select_npc_action()` — weighted-random action selection based on role and tension
  - `available_actions()` — computes action set based on ScenarioRole (Guilty, Witness, Innocent, Accomplice)
  - `NpcAction` enum: CreateAlibi, DestroyEvidence, Flee, Confess, ActNormal, SpreadRumor
- **sidequest-agents** integrates NPC actions via agent-driven scenarios
- **server dispatch pipeline** never calls the action selection path
- **Result:** NPCs only act when the narrator improvises their behavior; structured encounters don't trigger autonomous actions

### Acceptance Criteria

1. **Wire action selection into dispatch turn pipeline**
   - During `dispatch_player_action()` or at appropriate turn phase, for each NPC with a ScenarioRole in the game state
   - Call `select_npc_action(npc_id, role, belief_state, tension, rng)` to determine the next autonomous action
   - Get tension level from `TensionTracker` or game state
   - Execute the resulting NpcAction type (update belief state, location, inventory, status, etc.)

2. **NpcAction resolution logic**
   - **CreateAlibi**: Insert a false claim into the NPC's BeliefState
   - **DestroyEvidence**: Mark a clue as deactivated (via state patch)
   - **Flee**: Update NPC location to destination
   - **Confess**: Add a ConfessionEvent to the WorldStatePatch or GameSnapshot events
   - **ActNormal**: No state change (baseline behavior)
   - **SpreadRumor**: Insert claim into target NPC's BeliefState

3. **Integration checkpoints**
   - NPCs are loaded into GameSnapshot.npcs (already wired via dispatch/npcs.rs)
   - ScenarioRole assignments come from genre pack scenario declarations
   - BeliefState is available on each Npc object (story 7-5 infrastructure)
   - Tension level comes from TensionTracker (already in dispatch context)
   - RNG is available in dispatch (already seeded per turn)

4. **OTEL observability**
   - **Event:** `npc.action_selected`
   - **Fields:** `npc_name`, `action` (enum variant), `role` (ScenarioRole), `tension_at_time`
   - Emit this event whenever `select_npc_action()` is called from dispatch
   - Enable GM panel to verify NPC agency is active

5. **No half-wired feature**
   - Action is selected AND executed in the same turn
   - Not just "selected" and left unresolved
   - State patches flow through the standard broadcast pipeline
   - OTEL spans capture the full lifecycle

## Implementation Strategy

### Phase 1 (RED): Write acceptance tests
- Test `select_npc_action()` called from dispatch turn loop with realistic state
- Test each NpcAction type executes and mutates state correctly
- Test tension level affects action weights
- Test OTEL event is emitted with correct fields
- Integration test: full turn with NPC action execution, state visible to client

### Phase 2 (GREEN): Implement wiring
- Identify correct insertion point in `dispatch_player_action()` or turn phase loop
- Call `select_npc_action()` for each NPC with ScenarioRole
- Implement resolver: convert NpcAction to state mutations (patches, events, OTEL spans)
- Wire tension level into action selection
- Emit OTEL `npc.action_selected` events
- Execute mutations in standard state patch pipeline

### Phase 3 (VERIFY): Integration verification
- Full playthrough with NPC scenario roles
- Confirm autonomous actions appear in OTEL watcher
- Verify state changes (belief state, location, clues) propagate to client
- Confirm no regressions in existing turn flow

## Key Files

- **npc_actions.rs** — Existing implementation (no changes needed)
- **dispatch/mod.rs** — Wiring point (call site)
- **dispatch/npcs.rs** — NPC context handling
- **game_state.rs** — GameSnapshot, Npc, BeliefState
- **tension_tracker.rs** — Tension retrieval
- **otel_span.rs** or tracing macros — OTEL event emission
- **scenario.rs** (if exists) or npc.rs — ScenarioRole field on Npc

## Dependencies

- Story 7-5: BeliefState and scenario role infrastructure (completed)
- Epic 24: Tension tracking (completed)
- Story 15-11: OCEAN shift pipeline wiring (completed, reference pattern)

## Non-Goals
- Implement the NPC action selection logic (already done)
- Modify NpcAction enum or ScenarioRole (already implemented)
- Change agent-driven scenario calling pattern (agents own that)
- Add UI for scenario mechanics (that's UI layer)

## Workflow Phases

| Phase | Owner | Status |
|-------|-------|--------|
| setup | sm | done |
| red | tea | pending |
| green | dev | pending |
| spec-check | architect | pending |
| verify | tea | pending |
| review | reviewer | pending |
| spec-reconcile | architect | pending |
| finish | sm | pending |

## Workflow Tracking

**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-04-05T10:35Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-05T10:35Z | — | — |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

No upstream findings yet.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

No design deviations yet.
