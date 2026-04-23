---
story_id: "7-3"
jira_key: "none"
epic: "7"
workflow: "tdd"
---
# Story 7-3: Clue activation — semantic trigger evaluation for clue availability based on game state

## Story Details
- **ID:** 7-3
- **Jira Key:** none (personal project)
- **Workflow:** tdd (phased)
- **Epic:** 7 — Scenario System — Bottle Episodes, Whodunit, Belief State
- **Stack Parent:** 7-1 (BeliefState model)
- **Points:** 3
- **Priority:** p2
- **Status:** in-progress

## Context

Part of Epic 7 — the Scenario System port from sq-2. This story implements semantic trigger evaluation for clues in whodunit scenarios.

**Dependency chain:**
- 7-1 (BeliefState) — DONE
- 7-2 (Gossip) — DONE
- **7-3 (Clue activation)** ← current
  - 7-4 (Accusation system) — depends on this
  - 7-5 (NPC autonomous actions) — depends on 7-1
  - 7-6 (Scenario pacing)
  - etc.

## What This Story Does

**Clue Activation** evaluates semantic triggers to determine which clues become available during a scenario based on game state.

A clue is only discoverable if:
1. Its discovery conditions (the `requires` field) are met — dependent clues have been found
2. Its semantic triggers are satisfied — game state matches the trigger conditions
3. The NPC has sufficient relevant knowledge (via BeliefState) to contextually introduce the clue

Example from `midnight_express/clue_graph.yaml`:
- `clue_poison_vial` is hidden until the player has discovered enough evidence to contextually ask about it
- `clue_deduction_motive` depends on both `clue_torn_letter` AND `clue_financial_records`
- `clue_red_herring_scarf` has a semantic flag: it implicates suspect_irina, but was actually planted by the killer

## Codebase Research

### Existing Infrastructure

**Story 7-1 & 7-2 Completed:**
- `belief_state.rs` (94 LOC) — BeliefState with Belief enum (Fact/Suspicion/Claim), credibility tracking
- `gossip.rs` (188 LOC) — GossipEngine for multi-turn propagation, contradiction detection, credibility decay
- Both have full test suites (16-field belief_state_story_7_1_tests.rs, gossip_propagation_story_7_2_tests.rs)

**Npc Integration:**
- Npc struct (npc.rs) now has a `belief_state: BeliefState` field (added in 7-1)
- GameSnapshot (state.rs) composes npcs: HashMap<String, Npc>

### Clue Structure (from YAML)

From `genre_packs/pulp_noir/scenarios/midnight_express/clue_graph.yaml`:

```yaml
nodes:
  - id: clue_poison_vial
    type: physical                  # physical / testimonial / behavioral / deduction
    description: "..."
    discovery_method: forensic      # forensic / interrogate / search / observe
    visibility: hidden              # obvious / hidden / requires_skill
    locations: [dining_car, ...]    # where this clue can be found
    implicates: [suspect_varek]     # which NPCs this clue points to
    requires: []                    # dependent clue IDs that must be found first
    red_herring: false              # is this a false lead?
```

### What Needs to Happen

**TDD + RED phase:** Write tests for ClueActivation that reference types that don't exist yet.

The tests should cover:
1. **ClueActivation struct** — holds scenario clue definitions (load from YAML or in-memory)
2. **Activation rules** — evaluate whether a clue is discoverable
   - Dependency checks: are `requires` clues already found?
   - Semantic triggers: does game state match trigger conditions?
   - Visibility evaluation: can the current discovery_method apply?
3. **NPC knowledge integration** — clues become available when an NPC has relevant beliefs
4. **Clue graph querying** — get all discoverable clues, find implications, trace reasoning chains

**Key design question (for you to decide):**
- Should ClueActivation be a pure evaluator, or should it track discovered_clues state?
- Recommendation: pure evaluator. Let the ScenarioState track discovered clues; ClueActivation just says "is this clue discoverable NOW?"

## Workflow Tracking
**Workflow:** tdd
**Phase:** setup
**Phase Started:** 2026-03-31T04:54Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-03-31T04:54Z | — | — |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->
