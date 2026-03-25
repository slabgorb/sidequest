# ADR-021: Progression System

> Ported from sq-2. Language-agnostic game design.

## Status
Accepted

## Decision
Four independent progression tracks, all narrative-first:

### 1. Milestone Leveling
World state agent judges narrative significance. Genre packs define milestone categories and `milestones_per_level` threshold. No XP — milestones accumulate until level-up.

### 2. Affinity Tiers
```
Unawakened → Novice → Adept → Master
```
Affinities have keyword triggers in genre packs. When the player repeatedly engages with an affinity (e.g., uses fire magic), tier increases. Each tier unlocks narration hints.

### 3. Item Evolution
Items gain identity as `narrative_weight` increases:
- **0.5:** Item gets a proper name (coal → named coal)
- **0.7:** Item gains mechanical power (named coal → diamond)

### 4. Wealth Tiers
Raw gold maps to narrative labels: "destitute", "comfortable", "wealthy", "aristocratic". Genre packs define thresholds and labels.

### Journey Summary
At session end, a deterministic summary captures milestones, affinity changes, and notable events for the next session's "Previously On..." recap.

## Consequences
- Progression rewards engagement with the narrative, not grinding
- Genre packs control all progression pacing
- Journey summary provides session continuity
