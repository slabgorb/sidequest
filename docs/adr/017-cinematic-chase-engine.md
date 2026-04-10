# ADR-017: Cinematic Chase Engine

> Ported from sq-2. Language-agnostic game mechanic.

## Status
Superseded by ADR-033

> **Note (2026-04):** The standalone `ChaseState` struct was removed in Epic 28.
> Chases are now one encounter type within `StructuredEncounter` (ADR-033).
> The beat-based design principles below remain valid — they're implemented
> in the generalized encounter engine, not as a separate state machine.

## Context
Chases in RPGs are often anticlimactic. A physics simulation doesn't create drama; narrative beats do.

## Decision
Chases use a beat-based system with a single **Lead** variable (separation tracking), not physics.

### Core Principles
1. **Beats, not physics** — dramatic pacing, not movement grids
2. **Lead transparency** — players see relative distance, not exact numbers
3. **Five-phase arc:** SETUP → OPENING → ESCALATION → CLIMAX → RESOLUTION
4. **Multi-actor crews** — driver, gunner, navigator roles
5. **Rig as participant** — vehicles have HP, speed, armor, maneuver, fuel
6. **Terrain mechanics** — environment affects choices and outcomes

### Chase State
```rust
pub struct ChaseState {
    pub phase: ChasePhase,
    pub lead: i32,          // positive = pursuer ahead
    pub decision_points: Vec<DecisionPoint>,
    pub rig: RigStats,
    pub damage_tier: DamageTier,  // Pristine → Skeleton → Wreck
}

pub enum ChasePhase { Setup, Opening, Escalation, Climax, Resolution }
pub enum ChaseOutcome { Escape, Caught, Crashed, Abandoned }
```

### Pacing Integration
Chase scenes register high narrative weight (0.7-0.95). Aftermath suppresses back-to-back intensity.

## Consequences
- Chases feel cinematic, not mechanical
- Rig damage creates visible attrition across the chase
- Chase is a first-class encounter type within StructuredEncounter on GameState
