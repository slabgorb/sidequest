---
id: 53
title: "Scenario System (Clue Graph, Belief State, Gossip Propagation)"
status: accepted
date: 2026-04-01
deciders: [Keith Avery]
supersedes: []
superseded-by: null
related: []
tags: [npc-character]
implementation-status: partial
implementation-pointer: 87
---

# ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)

> Retrospective at write-time (2026-04-01) — documented an implementation already live in the Rust era. The 2026-04 port to Python carried the data layer and static scenario binding; the live-mutation engines did not. See _Implementation status_ below.

## Context
Mystery and investigation scenarios require structural guarantees that LLMs cannot provide
reliably on their own: clues must be discovered in causal order, NPCs must maintain coherent
epistemic states across many turns, and an accusation must be evaluated against actual
evidence rather than what the LLM decides felt dramatically satisfying.

A pure LLM approach forgets clues, contradicts NPC testimony, and resolves accusations based
on narrative momentum rather than player-assembled evidence. The problem requires a rule-based
structural backbone that the LLM dramatizes rather than controls.

## Decision
The scenario system is implemented across five source files in `sidequest-game/`:

**`clue_activation.rs` / `scenario_state.rs`** — `ClueGraph` is a directed acyclic graph of
clue prerequisites. A clue cannot be discovered until all prerequisite clues are known. This
enforces causal discovery order (you can't know the murder weapon before you know a murder
occurred) without LLM involvement.

**`belief_state.rs`** — Each NPC carries a `BeliefState` with three epistemic categories:

```rust
pub struct BeliefState {
    pub facts: Vec<Belief>,       // known true
    pub suspicions: Vec<Belief>,  // uncertain, being investigated
    pub claims: Vec<Belief>,      // stated by others, credibility-weighted
}

pub struct Belief {
    pub content: String,
    pub credibility: f32,         // 0.0–1.0
    pub source: BeliefSource,
    pub interaction_timestamp: u64,
}
```

**`gossip.rs`** — `GossipEngine` propagates beliefs between NPCs each turn using a two-phase
snapshot-then-mutate pattern to eliminate order-dependence. Propagation includes contradiction
detection (conflicting claims reduce credibility on both) and credibility decay over time.
NPCs select `NpcAction` variants autonomously based on their current belief state and assigned
scenario role.

**`accusation.rs`** — `AccusationEvaluator` is fully rule-based. It grades the player's
assembled evidence against the clue graph and belief state, producing a structured
`EvidenceSummary` with a verdict of Circumstantial, Strong, or Airtight. The narrator
dramatizes this summary — it does not determine the verdict.

The system separates structural facts (clue graph, role assignments, scenario configuration)
from epistemic state (what each NPC currently believes). The LLM only touches the epistemic
layer through narration; the structural layer is immutable once the scenario is loaded.

## Alternatives Considered

- **Pure LLM mystery management** — rejected because LLMs forget clue state across long
  sessions, produce contradictory NPC testimony, and resolve mysteries based on dramatic
  instinct rather than player evidence. Untraceable and unreliable at session length.

- **Simple checklist (clues as boolean flags)** — rejected because it provides no NPC agency.
  NPCs cannot independently discover, share, or doubt information. The mystery is static.

- **Player-only investigation (NPCs as passive witnesses)** — rejected because autonomous
  NPC belief propagation is the mechanism that makes mysteries feel alive. NPCs pursue their
  own suspicions, spread rumors, and form incorrect conclusions that the player must correct.

## Consequences

**Positive:**
- Clue discovery ordering is enforced structurally — no LLM can "skip ahead."
- NPC testimony is coherent and traceable: every belief has a source, timestamp, and
  credibility score.
- Accusation evaluation is deterministic and auditable — verdicts can be explained to players.
- Gossip propagation creates emergent NPC behavior without scripted dialogue trees.
- Two-phase gossip mutation eliminates turn-order bias in belief updates.

**Negative:**
- Scenario authoring complexity is high — genre pack authors must construct the clue DAG,
  assign NPC roles, and seed initial belief states. No LLM assistance here.
- `BeliefState` size grows with session length as accumulated claims are retained. Long
  investigations may require pruning strategies for low-credibility old claims.
- The boundary between "structural fact" and "epistemic state" requires discipline to maintain.
  Narrator prompts must not be allowed to write back into the clue graph.

## Implementation status (2026-05-02)

The Rust era implemented this ADR in full across `clue_activation.rs`, `scenario_state.rs`, `belief_state.rs`, `gossip.rs`, and `accusation.rs` in `sidequest-api/crates/sidequest-game/src/`. The 2026-04 port to Python brought across the **data layer and static binding**; the **live-mutation engines** did not make the cut.

What is live:

- `sidequest/game/belief_state.py` (275 LOC): `BeliefFact / BeliefSuspicion / BeliefClaim`, `Credibility`, four `BeliefSource` variants (`Witnessed`, `ToldBy`, `Inferred`, `Overheard`), and a `BeliefState` with `add_belief / beliefs_about / credibility_of / update_credibility`.
- `sidequest/game/scenario_state.py` (168 LOC): `ScenarioState`, `ScenarioRole`, `from_genre_pack(...)`, `set_tension`, `discover_clue`, `record_questioned_npc`.
- `sidequest/genre/models/scenario.py:118`: `ClueGraph` data model loaded from genre packs.
- `sidequest/server/dispatch/scenario_bind.py`: scenario-load wiring — builds `ScenarioState`, seeds matching NPCs' `belief_state` with facts/suspicions, attaches state to the snapshot.
- OTEL `SPAN_SCENARIO_ADVANCE` emits on clue discovery.

What is dark:

- **ClueGraph prerequisite enforcement.** `discover_clue()` (`scenario_state.py:148`) simply adds the clue id to `discovered_clues` — it does not check the DAG. The causal-discovery-order guarantee that is the headline of this ADR is not enforced at the entry point. The file's own comment (`scenario_state.py:141`) is candid: _"Mutation helpers (minimal — full between-turn logic deferred)."_
- **GossipEngine** — no `propagate_gossip` function, no two-phase snapshot-then-mutate, no contradiction detection, no credibility decay over time. The data layer exists but no engine drives belief flow between NPCs.
- **AccusationEvaluator** — no `evaluate_accusation`, no `EvidenceSummary`, no Circumstantial/Strong/Airtight verdict computation. The narrator currently has no rule-based verdict to dramatize; on accusation, the LLM improvises, which is exactly what this ADR's _Pure LLM mystery management_ alternative was rejected for.

`session.py:130` confirms the deferral plainly: _"Gossip + accusation logic defer to a later slice; the data model is in place."_

Restoration is scheduled in [ADR-087](087-post-port-subsystem-restoration-plan.md) — gossip engine and accusation logic both **P2 RESTORE**, bundled. Prerequisite enforcement on `discover_clue` is not separately listed but falls inside the same restoration scope. The decision in this ADR stands.
