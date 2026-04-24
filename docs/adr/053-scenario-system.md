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
implementation-status: drift
implementation-pointer: 87
---

# ADR-053: Scenario System (Clue Graph, Belief State, Gossip Propagation)

> Retrospective — documents a decision already implemented in the codebase.

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
