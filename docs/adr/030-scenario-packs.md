# ADR-030: Scenario Packs

> Ported from sq-2. Proposed feature — hidden-role scenario engine.

## Status
Partially implemented (Epic 7, ADR-053)

> **Note (2026-04):** Core scenario infrastructure is implemented: scenario_state.rs,
> ClueGraph, AccusationEvaluator, and the `/accuse` handler are wired. The full
> scenario pack format (cumulative memory, depth_unlocks) is still proposed.

## Context
Replayable "bottle episode" game modes (e.g., whodunit on a train) nested inside genre packs.

## Decision
Scenarios are self-contained game modes that inherit genre tone/rules/art but add:

### Key Components
1. **AssignmentMatrix** — Combinatorial role selection (killer, motive, method, atmosphere)
2. **ClueGraph DAG** — Evidence chains with red herrings, progressive revelation
3. **NPC Depth Layers** — Universal progression: Surface → Personal → Secret → Hidden
4. **Pacing Clock** — Uses trope engine (ADR-018) for scenario-specific escalation
5. **Accusation Mechanic** — Climax trigger when player makes formal accusation
6. **Cumulative Memory** — Session archive in JSONL + depth_unlocks.yaml persists across replays

### Reuses Existing Infrastructure
- GenrePack loader (for scenario YAML)
- Trope engine (for pacing)
- NPC agent (for conversations)
- PerceptionRewriter (for asymmetric knowledge)
- RAG retriever (for cumulative memory)

### Architecture
Scenarios are a mode within the game engine, not a separate system. The Orchestrator checks for an active scenario and routes accordingly.

## Consequences
- High replayability via combinatorial assignment
- Cumulative memory means each playthrough enriches the next
- Depends on several other ADRs being implemented first
