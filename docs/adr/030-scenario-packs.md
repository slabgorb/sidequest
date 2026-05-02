---
id: 30
title: "Scenario Packs"
status: superseded
date: 2026-03-25
deciders: [Keith Avery]
supersedes: []
superseded-by: 53
related: [53]
tags: [multiplayer]
implementation-status: retired
implementation-pointer: 53
---

> **Superseded by [ADR-053](053-scenario-system.md) (2026-05-02).**
>
> ADR-053 was written 2026-04-01 (six days after this ADR) as the
> mechanically-detailed version of the same scenario-engine design and
> has been the load-bearing record since. It covers five of the six
> §Key Components below: AssignmentMatrix (`Suspect`/`can_be_guilty`),
> ClueGraph DAG (`clue_activation.rs` / `scenario_state.rs`), Accusation
> Mechanic (`AccusationEvaluator`), and replaces "NPC Depth Layers"
> (Surface/Personal/Secret/Hidden) with `BeliefState`'s three-tier
> epistemic model (`facts`/`suspicions`/`claims`). Pacing Clock is
> covered by the `Pacing`/`Act`/`PressureEvent` types in
> `sidequest-server/sidequest/genre/models/scenario.py`.
>
> **Component 6 — "Cumulative Memory" (per-player JSONL session archive
> + `depth_unlocks.yaml` rollup that pre-seeds NPC depth layers across
> replays of the same scenario) — is canceled, not deferred.** Will
> revisit only if scenario replay volume in actual play surfaces a need.
> If/when revisited, write a fresh ADR — do not revive this one.
>
> Original 2026-04 note in this ADR claimed `scenario_state.rs`,
> `ClueGraph`, `AccusationEvaluator`, and the `/accuse` handler were
> all wired. That was Rust-era state; the 2026-04 port to Python
> carried the data layer and static binding only. ADR-053 governs
> restoration of the live-mutation engines (gossip propagation,
> accusation evaluation) and is tracked in
> [ADR-087](087-post-port-subsystem-restoration-plan.md).
>
> The body below preserves the original 2026-03-25 sketch as historical
> record.

# ADR-030: Scenario Packs

> Ported from sq-2. Proposed feature — hidden-role scenario engine.

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
