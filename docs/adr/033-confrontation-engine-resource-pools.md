---
id: 33
title: "Genre Mechanics Engine — Confrontations & Resource Pools"
status: accepted
date: 2026-03-31
deciders: [Keith]
supersedes: [17]
superseded-by: null
related: [11]
tags: [genre-mechanics]
implementation-status: partial
implementation-pointer: 87
---

# ADR-033: Genre Mechanics Engine — Confrontations & Resource Pools

**Epic:** 16

## Context

Genre packs define rich mechanical systems (Standoff, Humanity Tracker, Luck,
Heat, Ship Block, Net Combat) that are enforced only by LLM narration. The
narrator can forget, drift, or contradict these rules mid-session. The engine
provides generic subsystems (combat, chase, tropes, factions) but genre-specific
rules have no mechanical enforcement.

The gap analysis (docs/genre-pack-status.md) identified three categories:

1. **Content with no engine enforcement** — Standoff, Luck, Humanity, Heat,
   Ship Combat, Net Combat, Bounty Board, Contacts, Occult Exposure
2. **Engine data the UI doesn't show** — Rig HP, Fuel, Chase state
3. **Hardcoded enums limiting extensibility** — Mood (7 variants), ChaseType
   (3 variants), RigType (5 variants), ChaseRole (4 variants)

## Decision

Two new subsystems, plus an extension to an existing one.

### Pillar 1: Confrontation Engine

**Observation:** CombatState and ChaseState are both "structured encounters with
a metric, beats, actors, and resolution." Combat's metric is HP. Chase's metric
is separation. A standoff's metric is tension. A negotiation's metric is leverage.
They share the same shape.

**Original decision:** Do NOT merge CombatState and ChaseState into one type yet.

> **Update (2026-04, Epic 28):** This decision was revised during implementation.
> CombatState and ChaseState were **both deleted** and replaced by a unified
> `StructuredEncounter`. The original concern about god-objects was addressed by
> making StructuredEncounter metric-driven rather than role-driven — all encounter
> types (combat, chase, standoff, negotiation) share the same beat + metric
> structure. The CombatPatch and ChasePatch types were also removed.

**Original rationale (preserved for context):**

Reading the actual code changes the brainstorm's conclusion. CombatState and
ChaseState had fundamentally different internal structures:

- **CombatState** was actor-centric: turn order, per-actor effects, per-actor
  damage log, initiative.
- **ChaseState** was scene-centric: separation as a single scalar, beats as a
  sequence, one optional rig.

**What actually shipped:**

1. **StructuredEncounter replaces both.** Genre-declared ConfrontationDefs in
   rules.yaml define encounter types with metrics, beats, and resolution conditions.
2. **All encounter types are StructuredEncounter variants** — combat, chase,
   standoff, negotiation, net_combat, ship_combat.
3. **Beat selections drive progression** — the narrator outputs beat selections,
   the engine applies them via `apply_beat()`.
4. **Old save migration** handles ChaseState → StructuredEncounter transparently.

#### StructuredEncounter (generalized ChaseState)

```rust
pub struct StructuredEncounter {
    /// Genre-declared encounter type id (e.g., "chase", "standoff", "negotiation")
    pub encounter_type: String,
    /// The core metric being tracked
    pub metric: EncounterMetric,
    /// Beat sequence
    pub beat: u32,
    pub structured_phase: Option<EncounterPhase>,
    /// Secondary stat block (rig, nerve pool, ship block, deck — or None)
    pub secondary_stats: Option<SecondaryStats>,
    /// Actors involved
    pub actors: Vec<EncounterActor>,
    /// Resolution state
    pub outcome: Option<String>,
    pub resolved: bool,
    /// Genre-declared mood for MusicDirector
    pub mood_override: Option<String>,
    /// Narrator context hints from genre YAML
    pub narrator_hints: Vec<String>,
}

pub struct EncounterMetric {
    pub name: String,          // "separation", "tension", "leverage", "trace"
    pub current: i32,
    pub starting: i32,
    pub direction: MetricDirection,  // Ascending, Descending, Bidirectional
    pub threshold_high: Option<i32>,
    pub threshold_low: Option<i32>,
}

pub enum MetricDirection { Ascending, Descending, Bidirectional }
```

**Migration path:**
- ChaseState's `separation_distance` becomes `metric.current` with name "separation"
- ChaseState's `goal` becomes `metric.threshold_high`
- RigStats becomes a SecondaryStats variant
- ChaseType (Footrace/Stealth/Negotiation) becomes `encounter_type: String`
- ChasePhase enum stays (Setup→Opening→Escalation→Climax→Resolution is universal)
- ChaseBeat, BeatDecision, TerrainModifiers, Cinematography all transfer directly
- **Backward compat:** ChaseState can remain as a type alias or convenience
  constructor over StructuredEncounter for existing code

**YAML declaration in rules.yaml:**
```yaml
confrontations:
  - type: standoff
    label: "Standoff"
    category: pre_combat
    metric:
      name: tension
      direction: ascending
      starting: 0
      threshold_high: 10
    beats:
      - id: size_up
        label: "Size Up"
        metric_delta: 2
        stat_check: CUNNING
      - id: draw
        label: "Draw"
        resolution: true
        stat_check: DRAW
    secondary_stats:
      - name: focus
        source_stat: NERVE
    escalates_to: combat
    mood: standoff
```

### Pillar 2: Resource Pools

Genre-specific tracked resources that persist across turns.

```rust
pub struct ResourcePool {
    pub name: String,
    pub label: String,
    pub current: f64,
    pub min: f64,
    pub max: f64,
    pub voluntary: bool,           // player can spend
    pub decay_per_turn: f64,       // automatic change per turn
    pub thresholds: Vec<ResourceThreshold>,
    pub fired_thresholds: HashSet<String>,  // idempotent
}

pub struct ResourceThreshold {
    pub at: f64,
    pub event_id: String,
    pub narrator_hint: String,
    pub direction: ThresholdDirection,  // CrossingDown, CrossingUp, Either
}
```

**On GameSnapshot:**
```rust
pub resources: HashMap<String, ResourcePool>,
```

**Patch type:**
```rust
pub struct ResourcePatch {
    pub deltas: Option<HashMap<String, f64>>,  // name → delta
}
```

**Threshold → KnownFact pipeline:**
When `ResourcePool::apply_delta()` crosses a threshold:
1. Mint a `KnownFact` with category "resource_event", the event_id, and
   narrator_hint as content
2. LoreStore indexes it with high relevance
3. Narrator prompt includes it via existing budget-aware selection
4. `fired_thresholds` set prevents re-firing on save/load

**YAML declaration:**
```yaml
resources:
  - name: luck
    label: "Luck"
    min: 0
    max: 6
    starting: 3
    voluntary: true
    thresholds:
      - at: 1
        event_id: luck_desperation
        narrator_hint: "One bullet left in the chamber of fate."
        direction: crossing_down
      - at: 0
        event_id: luck_exhausted
        narrator_hint: "Luck has run dry. Every consequence is earned."
        direction: crossing_down
```

**Engine validates all resource mutations.** If the LLM patch says "spend 2 Luck"
but current is 1, the engine rejects the patch. PatchLegality (already exists,
202 LOC) is the enforcement point.

### Pillar 3: Mood Extension (MusicDirector)

**Finding:** MusicDirector already uses string-keyed mood_tracks internally.
The Mood enum is only used for classification. The fix is smaller than expected.

1. Add `mood_aliases` to AudioConfig YAML:
   ```yaml
   mood_aliases:
     standoff: tension
     saloon: calm
     riding: exploration
     convoy: exploration
     betrayal: tension
     cyberspace: mystery
   ```

2. When MusicDirector classifies mood, check genre mood_keywords first (already
   string-keyed), then fall back to core keyword matching.

3. When selecting a track, look up the classified mood string in mood_tracks
   (already a HashMap<String, Vec<MoodTrack>>). If not found, follow the
   alias chain.

4. **StructuredEncounter's `mood_override`** feeds directly into MusicDirector —
   when a standoff is active, mood is "standoff" regardless of narration keywords.

**This is a 50-line change, not a rewrite.**

## Consequences

### Positive
- Genre packs declare mechanical rules in YAML — no Rust code per genre
- LLM narrates around engine-enforced state — can't forget resources exist
- Standoff, negotiation, net combat, ship combat reuse chase infrastructure
- MusicDirector plays genre-specific moods with zero structural change
- ResourcePool thresholds create permanent narrator memory via LoreStore
- UI gets generic components (ResourceBar, EncounterOverlay) that work for all genres

### Negative
- StructuredEncounter is the sole encounter system (CombatState and ChaseState deleted)
- Genre YAML grows more complex (mitigated: optional sections, sensible defaults)
- Save format changes (mitigated: serde defaults handle missing fields in old saves)

### Risks
- Over-engineering the YAML schema before we know what genres actually need.
  **Mitigation:** Implement for 3 concrete cases first (standoff, negotiation,
  net_combat), then generalize.
- Resource validation rejecting valid LLM output due to edge cases.
  **Mitigation:** Warn-and-clamp mode for first release, strict mode later.

## Implementation Order

1. **16-1: Narrator resource injection** (quick win, no new types)
2. **16-14: Mood aliases** (50-line change, immediate audio improvement)
3. **16-10: ResourcePool struct + YAML** (the core resource system)
4. **16-11: Threshold → KnownFact** (permanent narrator memory)
5. **16-2: StructuredEncounter** (generalize ChaseState)
6. **16-6: Standoff** (first genre-specific encounter type)
7. **16-9: UI ConfrontationOverlay** (visual payoff)
8. **16-13: UI ResourceBar** (visual payoff)
9. Everything else

## Alternatives Considered

### A: Merge CombatState + ChaseState into one ConfrontationState
Rejected. Reading the code showed they have fundamentally different internal
structures (actor-centric vs scene-centric). A unified type would be a god-object
with unused fields or require complex dispatch. The brainstorm proposed this;
the code review refuted it.

### B: Use existing `extras: HashMap<String, Value>` for resources
Rejected. No type safety, no validation, no threshold events. The extras HashMap
is for one-off data, not core mechanics.

### C: Build per-genre engine modules (standoff.rs, humanity.rs, etc.)
Rejected. Violates the plugin principle. Every new genre would require Rust code.
The whole point is YAML-declarable mechanics.

### D: Rely entirely on LLM prompt injection without engine tracking
Considered for the quick win (story 16-1). Not sufficient long-term: the LLM
can still produce contradictory state without engine validation. Prompt injection
is step 1, not the architecture.
