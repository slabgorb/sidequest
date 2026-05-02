---
id: 42
title: "OCEAN Personality Live Evolution"
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

# ADR-042: OCEAN Personality Live Evolution

> Retrospective at write-time (2026-04-01) — documented an implementation already live in the Rust era. The implementation did not survive the 2026-04 port to Python; see _Implementation status_ below.

## Context
NPC personalities in SideQuest were initially static YAML configuration — a set of OCEAN dimension scores (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) defined at world-build time. Static personalities produce NPCs who feel like props: they don't grow, adapt, or remember what happened to them. A merchant who witnessed a betrayal in scene 2 behaves identically in scene 8. This was acceptable for early development but incompatible with the core narrative consistency goal — the game world must feel like it has memory and consequence.

The question was how to make personality evolution happen without adding LLM calls per NPC per scene, which would be prohibitively expensive at scale.

## Decision
NPC OCEAN profiles evolve through a closed feedback loop that adds zero LLM cost:

1. **Narrator observes** — during scene narration, Claude detects significant NPC experiences
2. **Events emitted** — the narrator's `NarratorStructuredBlock` (see ADR-039) includes typed `PersonalityEvent` values for each affected NPC
3. **Engine applies shifts** — the game engine maps events to `OceanShiftProposal` vectors and applies them to the NPC's stored OCEAN profile
4. **Summary regenerated** — the updated profile is rendered as `ocean_summary` behavioral text
5. **Re-injected** — `ocean_summary` appears in the narrator prompt context for the next scene involving that NPC

`PersonalityEvent` is a typed enum to prevent naming drift between the narrator prompt instructions and the parser:

```
betrayal | near_death | victory | defeat | social_bonding | humiliation | revelation
```

`OceanShiftProposal` carries: dimension (O/C/E/A/N), delta (signed float), and cause string. The cause string is logged to OTEL for GM panel inspection.

`ocean_summary` is free text describing behavioral tendencies in narrator-friendly language ("distrustful of strangers since the ambush, quicker to anger than before") rather than raw dimension scores. The narrator consumes prose, not numbers.

Implemented in: `sidequest-game/src/ocean_shift_proposals.rs`, `sidequest-game/src/ocean.rs`

## Alternatives Considered

**Static personalities** — rejected: NPCs feel like props. A world with no character memory contradicts the narrative consistency goal. Players notice immediately when an NPC ignores what happened between them.

**Separate classifier LLM call per scene** — rejected: adds latency and token cost proportional to NPC count per scene. With 4–8 NPCs in an active scene, this multiplies LLM calls significantly. The narrator is already observing the scene — piggyback on that observation rather than duplicating it.

**Player-controlled personality shifts** — rejected: breaks the simulation. Players should experience NPC personality as a property of the character, not a dial they control. Immersion requires that NPCs feel like independent agents with their own interiority.

**Embedding raw OCEAN scores in the narrator prompt** — rejected: the narrator thinks in prose, not in five-axis vectors. Raw scores require the narrator to translate numbers to behavior, which it does inconsistently. `ocean_summary` prose is directly usable by the narrator without translation.

## Consequences

**Positive:**
- NPC personality evolution costs zero additional LLM calls — events are detected in-band by the existing narrator call.
- Typed `PersonalityEvent` enum creates a stable contract between prompt instructions and parser; adding a new event type requires updating both deliberately rather than allowing silent drift.
- `ocean_summary` prose keeps the narrator's prompt context human-readable and directly useful — no prompt engineering required to translate scores to behavior.
- OTEL logging of shift causes gives the GM panel a full personality audit trail: what changed, when, and why.
- Creates genuine NPC arcs: a cowardly NPC who survives near-death may become reckless; a generous NPC who is repeatedly betrayed may become guarded.

**Negative:**
- Evolution depends on the narrator correctly identifying and emitting personality events. If the narrator misses a significant moment, the shift doesn't happen — no mechanical backstop.
- OCEAN dimension shifts are additive deltas applied to a float profile; there's no decay or stabilization mechanic. Long-running sessions can produce NPCs with extreme profiles if the same event type repeats.
- `ocean_summary` regeneration produces a new text blob each time — there's no guarantee of narrative continuity in how the summary describes personality across multiple shifts. The GM panel must verify the summary reads coherently.

## Implementation status (2026-05-02)

The Rust era (`sidequest-api/crates/sidequest-game/src/ocean.rs` + `ocean_shift_proposals.rs`) implemented this ADR in full: the `PersonalityEvent` enum, the `OceanShiftProposal` type, the narrator-emit pipeline, the engine that mapped events to dimension deltas, and the regeneration of `ocean_summary` from the updated profile.

The 2026-04 port carried the **data shape** only. From `sidequest/genre/models/ocean.py:3` (porter's own note): _"Port of sidequest-genre/src/models/ocean.rs (data shape only — no random/jitter/shift methods)."_

What landed:

- `OceanProfile`, `OceanDimension`, `OceanShift`, `OceanShiftLog` models in `sidequest/genre/models/ocean.py`.
- `summarize_ocean(profile)` in `sidequest/cli/namegen/namegen.py:649`, called **once at character-generation time**.
- `ocean_summary` field exists on the API surface but is hardcoded `None` in `sidequest/server/rest.py:333`.

What is dark — the entire live-evolution loop:

- The `PersonalityEvent` enum.
- The `OceanShiftProposal` type and its construction from narrator output.
- Narrator emission of personality events (the `NarratorStructuredBlock` does not carry them).
- The engine that maps events → shifts and applies them.
- Re-rendering of `ocean_summary` after a shift.
- Re-injection of the updated summary into the next narrator prompt.

The static profile path (used at archetype/namegen time) works. The evolution path — the decision this ADR is fundamentally about — is 0/5 wired.

Restoration is scheduled as **P2 RESTORE** in [ADR-087](087-post-port-subsystem-restoration-plan.md) and depends on trope-engine restoration (ADR-018 P1) per the ADR-087 dependency notes. The decision in this ADR stands.
