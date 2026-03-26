# Epic 7: Scenario System — Bottle Episodes, Whodunit, Belief State

## Overview

Port the scenario/mystery system from sq-2. Scenarios are structured narrative arcs —
whodunit mysteries, rat-hunts, bottle episodes — where NPCs have independent knowledge,
spread rumors, and act on their own. The core mechanic is BeliefState: per-NPC knowledge
bubbles tracking what each NPC knows, suspects, has been told, and where claims contradict.
This is what makes "who killed the merchant?" work as an actual game mechanic, not just
flavor text.

This is one of the most complex subsystems in SideQuest. It turns investigation from
"the narrator decides you found something" into a deterministic system where clues
activate based on game state, gossip propagates between NPCs, credibility decays when
stories contradict, and accusations resolve based on evidence quality.

Key reference: sq-2/sidequest/scenario/*.py (15 files), oq-2/docs/adr/030-scenario-packs.md.

## Background

### What Epic 2 Delivers (prerequisite)

| Component | What's Done |
|-----------|-------------|
| **Orchestrator** | Turn loop: input -> intent -> agent -> narration -> patch -> broadcast |
| **NPC system** | Character structs, NPC state within GameSnapshot |
| **Agent execution** | Claude CLI subprocess for LLM decisions |
| **State patches** | WorldStatePatch applied to GameSnapshot |

### Python Reference: sq-2/sidequest/scenario/

The Python implementation spans 15 files:

| File | Responsibility |
|------|----------------|
| `belief_state.py` | Per-NPC knowledge model (facts, suspicions, claims) |
| `gossip.py` | Claim propagation between NPCs, credibility decay |
| `clue_activation.py` | Semantic triggers for clue availability |
| `accusation.py` | Evidence evaluation and accusation resolution |
| `npc_actions.py` | Autonomous NPC behaviors within scenarios |
| `scenario_engine.py` | Lifecycle management, turn integration |
| `pacing.py` | Tension ramp, pressure escalation |
| + 8 more | Support modules, serialization, scenario templates |

The Rust port benefits from stronger type guarantees — BeliefState invariants that Python
enforces at runtime (credibility bounds, claim uniqueness) become compile-time constraints.

### Key ADR

**ADR-030: Scenario Packs** — Defines the YAML schema for scenario definitions, clue
graphs, and NPC role assignments. Scenarios are data-driven, not hardcoded.

## Technical Architecture

### Belief State Model

```
Per-NPC Knowledge Bubble
┌─────────────────────────────────────────┐
│  BeliefState (npc_id: "barkeep")        │
│                                         │
│  facts: [                               │
│    "merchant was last seen at docks",   │
│    "I sold him ale at 9pm"              │
│  ]                                      │
│                                         │
│  suspicions: [                          │
│    Suspicion { target: "guard",         │
│               reason: "was nervous" }   │
│  ]                                      │
│                                         │
│  claims: [                              │
│    Claim { content: "guard was home",   │
│            source: "guard",             │
│            corroborated_by: [],         │
│            contradicted_by: ["smith"] } │
│  ]                                      │
│                                         │
│  credibility: 0.85                      │
│  (decays when claims are contradicted)  │
└─────────────────────────────────────────┘
```

### Gossip Propagation Flow

```
Between-turn gossip phase
─────────────────────────
  For each NPC pair with social proximity:
       │
       ▼
  npc_a.claims ──► propagate to npc_b
       │
       ▼
  Does claim contradict npc_b's existing knowledge?
       │
       ├─ No  ──► npc_b adds claim, corroborated_by += [npc_a]
       │
       └─ Yes ──► npc_b adds claim as contradicted
                  npc_a.credibility *= decay_factor
                  (liar's claims eventually get questioned)
```

### Clue Activation

```
Scenario Clue Graph
───────────────────
  Clue { id: "bloody_glove",
         trigger: SemanticTrigger::StateMatch {
           requires: ["visited_crime_scene"],
           excludes: ["guard_cleaned_scene"],
         },
         reveals_to: FactKind::Physical }
       │
       ▼
  evaluate_triggers(game_state) ──► Vec<ActivatedClue>
       │
       ▼
  Activated clues injected into narrator context
  (player can now discover the glove)
```

### Accusation Resolution

```
Player accuses NPC
       │
       ▼
  Gather evidence:
  ├─ clues_found: Vec<ActivatedClue>
  ├─ corroborated_claims: Vec<Claim>
  ├─ contradictions_found: Vec<Contradiction>
  └─ npc_credibility_scores: HashMap<NpcId, f64>
       │
       ▼
  evaluate_accusation(accused, evidence) ──► AccusationResult {
       quality: EvidenceQuality,   // Circumstantial / Strong / Airtight
       correct: bool,
       narrative_summary: String,  // for narrator to dramatize
  }
```

### Key Types

```rust
pub struct BeliefState {
    pub npc_id: String,
    pub facts: Vec<Fact>,
    pub suspicions: Vec<Suspicion>,
    pub claims: Vec<Claim>,
    pub credibility: f64,  // 0.0-1.0, invariant enforced by type
}

pub struct Claim {
    pub content: String,
    pub source_npc: String,
    pub corroborated_by: Vec<String>,
    pub contradicted_by: Vec<String>,
}

pub struct Fact {
    pub content: String,
    pub source: FactSource,        // Witnessed, ToldBy(NpcId), Deduced
    pub turn_learned: u64,
}

pub struct Suspicion {
    pub target_npc: String,
    pub reason: String,
    pub confidence: f64,           // 0.0-1.0
}

pub enum EvidenceQuality {
    Circumstantial,  // some clues, weak corroboration
    Strong,          // multiple clues, corroborated claims
    Airtight,        // contradictions exposed, confession, physical evidence
}

pub struct ScenarioState {
    pub scenario_id: String,
    pub beliefs: HashMap<String, BeliefState>,
    pub activated_clues: Vec<ActivatedClue>,
    pub tension: f32,              // 0.0-1.0, rises over scenario arc
    pub turn_count: u64,
    pub phase: ScenarioPhase,      // Setup, Investigation, Confrontation, Resolution
}
```

## Story Dependency Graph

```
2-5 (orchestrator turn loop)
 │
 └──► 7-1 (BeliefState model)
       │
       ├──► 7-2 (gossip propagation)
       │     │
       │     └──► 7-6 (scenario pacing)
       │
       ├──► 7-3 (clue activation)
       │     │
       │     └──► 7-4 (accusation system)
       │           │
       │           └──► 7-8 (scenario scoring)
       │
       ├──► 7-5 (NPC autonomous actions)
       │     │
       │     └──► 7-9 (ScenarioEngine integration)
       │
       └──► 7-7 (scenario archiver)
```

## Deferred (Not in This Epic)

- **Scenario editor UI** — A React interface for designing scenarios with a clue graph
  editor. The engine is code/YAML-first; visual tooling comes later.
- **Multi-scenario campaigns** — Running multiple overlapping scenarios where clues from
  one mystery bleed into another. Single-scenario focus for this epic.
- **LLM-generated scenarios** — Having Claude create scenario definitions dynamically.
  This epic implements the runtime engine for hand-authored scenario packs.
- **Witness reliability modeling** — NPCs with unreliable narration (drunk, confused,
  lying for non-scenario reasons). BeliefState tracks credibility from contradictions
  only; personality-driven reliability is future work.
- **Player deduction journal** — A UI-side notebook where players track their own
  theories. Engine-side only for this epic.

## Dependencies

### From Epic 2 (must complete first)
- Story 2-5: Orchestrator turn loop (7-1 depends on this for NPC and turn infrastructure)

### From ADR-030
- Scenario pack YAML schema defined in ADR-030. Story 7-1 implements the Rust structs
  that deserialize from this schema.

### Relationship to Epic 6
- Epic 6 (scene directives) and Epic 7 (scenarios) are independent but complementary.
  A scenario's tension level could feed into scene directives as a future integration,
  but neither epic blocks the other.

## Success Criteria

During a whodunit playtest:
1. Each NPC maintains an independent BeliefState — they know only what they witnessed or were told
2. Gossip propagates between turns: NPC A tells NPC B a claim, B's knowledge updates
3. Contradictions between claims decay the liar's credibility score
4. Clues activate based on semantic triggers evaluated against game state
5. A player accusation resolves with evidence quality (circumstantial/strong/airtight)
6. NPCs act autonomously within the scenario — providing alibis, fleeing, destroying evidence
7. Tension ramps over the scenario arc, increasing pressure on the player
8. Scenario state survives save/resume across session boundaries
9. Scoring captures how thoroughly the player investigated before accusing
