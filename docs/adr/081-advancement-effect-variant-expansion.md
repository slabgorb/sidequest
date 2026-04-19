# ADR-081: Advancement Effect Variant Expansion (v1)

**Status:** Proposed
**Date:** 2026-04-18
**Deciders:** Keith Avery, Major Houlihan (Architect)
**Related:** ADR-078 (Edge/Composure/Advancement/Rituals), Epic 39

## Context

ADR-078 defined a five-variant `AdvancementEffect` enum (`EdgeMaxBonus`, `BeatDiscount`, `LeverageBonus`, `EdgeRecovery`, `LoreRevealBonus`) and named "ADR-079 — Affinity Hooks Enrichment" as the planned home for four additional variants flagged by the GM's initial draft. ADR-079 was subsequently assigned to *Genre Theme System Unification* (Accepted 2026-04-16), creating a numbering conflict. This ADR takes the next free slot (081) and intentionally scopes itself more narrowly than the original ADR-079 reservation.

During brainstorm authoring of Evropi starting kits (`docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md`), two `AdvancementEffect` variants surfaced as load-bearing at **Tier 1 / character creation**:

1. `AllyEdgeIntercept` — required for Prot'Thokk's *Lil' Sebastian Stands* (the ability that defines his character identity: he dies for the horse).
2. `ConditionalEffectGating` — required for Th`rook's *The Dose Helps* (pact mechanics that flip sign when reniksnad dependency crosses a threshold).

Both are needed to make day-one class differentiation mechanically real rather than narrator-fiat. Without them, Prot'Thokk and Th`rook are indistinguishable from a generic fighter and warlock on the GM panel — defeating the Sebastien-facing dashboard goal.

Other T2/T3 stubs surfaced in the character drafts (`AllyBeatDiscount`, `BetweenConfrontationsAction`, `AllyEdgeGrant`, `EdgeThresholdDelay`, `AllyAttentionIntercept`, `AllyInitiativeGrant`, `FactionTrackingDelay`, `PermanentPursuerDismissal`, `BetweenSessionIncome`, `NPCDebtLadder`, `PacingAcceleration`, `RecordSelfInsertion`, `OneShotNarrativePivot`, `RetroactivePresenceErasure`, `WorldStateInsertion`, `CampaignOnceResurrection`) are **explicitly deferred** to ADR-082+. They gate higher-tier content the playgroup is unlikely to reach in the near future, and designing enum architecture speculatively on stale requirements is wasted work.

## Decision

Extend the `AdvancementEffect` enum (defined in ADR-078) with exactly two new variants. All other requested variants remain deferred to future ADRs, with character YAML drafts carrying `effects: []  # TODO ADR-082+ — <reason>` stubs that preserve authored labels and narration_hints for later wiring.

### Variant 1: `AllyEdgeIntercept`

Redirects `target_edge_delta` from a designated ally to the actor. Self-sacrifice semantics.

```rust
AllyEdgeIntercept {
    /// CreatureCore identities (by name or tag) that this interception applies to.
    /// Empty allows any party ally.
    ally_whitelist: Vec<CreatureRef>,
    /// Maximum target_edge_delta the actor can absorb per redirect event.
    max_redirect: u32,
}
```

**Resolution semantics:**
- Fires as a *reaction* when an enemy beat would apply `target_edge_delta` to an ally matching `ally_whitelist`.
- Up to `max_redirect` of the incoming delta is subtracted from the actor's Edge instead of the ally's.
- Any remainder continues to the original ally target.
- Actor Edge is clamped to a minimum of 1 on the redirect (preventing instant self composure_break on interception — narrative grace).
- Engine emits `advancement.ally_edge_intercept` OTEL event with `actor`, `ally`, `original_delta`, `absorbed_delta`, `remainder`.

**Example (Prot'Thokk):**
```yaml
- id: lil_sebastian_stands
  effects:
    - type: ally_edge_intercept
      ally_whitelist: ["Cheeney", "Lil'Sebastian"]
      max_redirect: 3
```

### Variant 2: `ConditionalEffectGating`

Wraps another `AdvancementEffect` in a condition against character state (initially only ResourcePool threshold comparisons). The wrapped effect is active only when the condition is true; optional `when_false` enables a flipped effect for the opposite condition.

```rust
ConditionalEffectGating {
    condition: ConditionExpr,
    when_true: Box<AdvancementEffect>,
    when_false: Option<Box<AdvancementEffect>>,
}

enum ConditionExpr {
    ResourceAbove { resource: String, threshold: i32 },
    ResourceAtOrBelow { resource: String, threshold: i32 },
}
```

**Resolution semantics:**
- At the moment `resolved_beat_for` is computed for the actor, the condition is evaluated against current character state.
- If `condition` is true, `when_true` is applied as the effective `AdvancementEffect` for this resolution.
- If `condition` is false and `when_false` is `Some`, `when_false` is applied instead.
- If `condition` is false and `when_false` is `None`, no effect.
- Engine emits `advancement.conditional_effect_gating` OTEL event with `actor`, `condition`, `evaluated`, `applied_variant`.

**ConditionExpr grammar — scope note:** Initial release supports only the two ResourcePool comparators listed above. Boolean composition (AND/OR/NOT), multi-resource comparisons, and non-resource conditions are explicitly out of scope for v1.

**Example (Th`rook):**
```yaml
- id: the_dose_helps
  effects:
    - type: conditional_effect_gating
      condition:
        type: resource_above
        resource: reniksnad
        threshold: 5
      when_true:
        type: beat_discount
        beat_id: commit_cost
        resource_mod: { flesh: 1 }
      when_false:
        type: beat_discount        # same beat, inverted resource_mod
        beat_id: commit_cost
        resource_mod: { flesh: -1 }
```

## Scope

### In scope
- Add `AllyEdgeIntercept` variant to `AdvancementEffect` enum
- Add `ConditionalEffectGating` variant with initial `ConditionExpr` grammar
- OTEL events for both variants
- Update `resolved_beat_for` to evaluate conditional gating at resolution time
- Update reaction-dispatch path for intercept semantics (fires before ally Edge mutation)

### Out of scope
- All other deferred variants from the GM draft (listed in Context); these wait for ADR-082+
- Richer `ConditionExpr` grammar (boolean composition, multi-resource, non-resource)
- UI/protocol changes for the new variants (covered by Epic 39 story 7's composure sheet work)
- Authoring non-heavy_metal content that uses these variants

## Consequences

**Positive**
- Unblocks two character-defining Tier 1 abilities (Prot'Thokk's oath, Th`rook's pact mechanics)
- Tightly scoped — two variants, each named and required by a live character draft, not speculative
- Preserves the v1 enum's architectural discipline (no grab-bag enum expansion)
- Sebastien gets visible conditional-gating behavior on the GM panel

**Negative**
- Introduces reaction-dispatch semantics for `AllyEdgeIntercept` — new control flow path in beat resolution
- `ConditionalEffectGating` adds runtime condition evaluation to `resolved_beat_for`, slightly more complex than other variants
- 16+ other requested variants remain as `TODO ADR-082+` stubs; authors must keep two ADR numbers in mind when reading drafts

**Neutral**
- Follows ADR-078's ratified extension pattern (`LoreRevealBonus` was a similar single-variant extension)

## Alternatives considered

1. **Fiat-only (no new variants):** Prot'Thokk's horse-defense and Th`rook's dose-gated beats run under narrator interpretation. Rejected — defeats the GM-panel-visibility goal that makes Sebastien want the mechanical characters.
2. **Comprehensive variant expansion (all 16+ requested):** Define every deferred variant now. Rejected — most gate T2/T3 content the playgroup will not reach soon; speculative architecture on stale requirements.
3. **Reshape *Lil' Sebastian Stands* and *The Dose Helps* to existing day-1 variants:** Attempted during brainstorming. Neither ability maps cleanly — *Lil' Sebastian Stands* is fundamentally a target redirection (no existing variant does this), and *The Dose Helps* requires a bidirectional effect tied to mutable character state (no existing variant has conditional state checks). Rejected as infeasible.

## References

- ADR-078 — Edge/Composure/Advancement/Rituals (baseline enum)
- `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md` — driving spec
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml` — `AllyEdgeIntercept` consumer (Lil' Sebastian Stands)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml` — `ConditionalEffectGating` consumer (The Dose Helps)
