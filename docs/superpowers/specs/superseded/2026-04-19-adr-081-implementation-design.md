# ADR-081 Implementation — Expanded Story 39-5 Design

**Status:** Draft
**Date:** 2026-04-19
**Deciders:** Keith Avery, Major Winchester (Dev)
**Related:** ADR-078 (Edge/Composure/Advancement/Rituals), ADR-081 (Advancement Effect Variant Expansion v1), Epic 39 story 5

## Context

ADR-081 (filed 2026-04-18) added two new `AdvancementEffect` variants — `AllyEdgeIntercept` and `ConditionalEffectGating` — driven by Evropi starting-kit authoring. The variants are purely architectural on paper; none of Epic 39 has shipped yet. Story 39-5 is where the `AdvancementEffect` enum first lands in the engine, planned with ADR-078's five day-1 variants.

Rather than ship 39-5 with five variants and follow up separately for ADR-081's two, this design folds all seven variants plus character-scoped `ResourcePool` hydration into a single expanded 39-5. Th`rook's reniksnad dependency and Prot'Thokk's *Lil' Sebastian Stands* become fully mechanical on first arrival in engine — no wired-but-dormant gap, no follow-up story.

## Decision

Expand story 39-5 to deliver:

1. All **seven** `AdvancementEffect` variants (ADR-078's five + ADR-081's two)
2. `ConditionExpr` grammar (two ResourcePool comparators)
3. **Two distinct resolution paths** — `resolved_beat_for` for enum-local resolution, and a new reaction hook in beat dispatch for target redirection
4. `starting_kit` hydration with compound-grant and `inherits:` support
5. `character_resources` hydration (character-scoped `ResourcePool`s alongside genre-level pools)
6. Scene-end decay + threshold watcher wiring for character-scoped pools
7. OTEL coverage for every advancement decision and resource crossing

New estimate: ~16-18 points. Other Epic 39 stories unchanged.

## Scope

### In scope
- `AdvancementEffect` enum with seven variants landing together
- `ConditionExpr` with `ResourceAbove` + `ResourceAtOrBelow` only
- `resolved_beat_for` view function covering six of seven variants
- Reaction hook in `handle_applied_side_effects` for `AllyEdgeIntercept`
- `starting_kit:` loader, including `inherits:` resolution
- `character_resources:` loader and hydration onto `CreatureCore`
- Scene-end decay + threshold event emission for character-scoped pools
- OTEL spans per §OTEL Contract below
- Unit + integration + real-wiring tests
- Playtest fixtures for 39-8 acceptance gate (Prot'Thokk intercept + Th`rook dose flip)

### Out of scope
- ADR-082+ variants (`AllyBeatDiscount`, `BetweenConfrontationsAction`, `AllyEdgeGrant`, `EdgeThresholdDelay`, etc.) — remain `effects: []  # TODO ADR-082+` stubs
- Richer `ConditionExpr` grammar (boolean composition, multi-resource, non-resource)
- UI / composure sheet work — lives in story 39-7
- Non-heavy_metal content using these variants
- Per-character portraiture, audio, or voice updates

## Design

### Enum shape

```rust
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AdvancementEffect {
    EdgeMaxBonus { amount: i32 },
    BeatDiscount {
        beat_id: String,
        #[serde(default)] edge_delta_mod: Option<i32>,
        #[serde(default)] resource_mod: Option<ResourceDelta>,
    },
    LeverageBonus { beat_id: String, target_edge_delta_mod: i32 },
    EdgeRecovery { trigger: RecoveryTrigger, amount: u32 },
    LoreRevealBonus { scope: String },

    // ADR-081
    AllyEdgeIntercept {
        ally_whitelist: Vec<String>,
        max_redirect: u32,
    },
    ConditionalEffectGating {
        condition: ConditionExpr,
        when_true: Box<AdvancementEffect>,
        #[serde(default)] when_false: Option<Box<AdvancementEffect>>,
    },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ConditionExpr {
    ResourceAbove { resource: String, threshold: i32 },
    ResourceAtOrBelow { resource: String, threshold: i32 },
}
```

### Two resolution paths — don't conflate

**Path 1 — `resolved_beat_for` (enum-local resolution).**
Six variants resolve here: the five ADR-078 variants plus `ConditionalEffectGating`. For `ConditionalEffectGating`, evaluate `condition` against current `CreatureCore` state (reading the relevant `ResourcePool` from `character_resources` or genre pools), then recursively resolve either `when_true` or `when_false` as the effective variant. If `when_false: None` and condition is false, the gating is a no-op for this resolution.

Output: a resolved `BeatDef` with modified deltas/costs for the actor.

**Path 2 — Reaction hook in `handle_applied_side_effects`.**
`AllyEdgeIntercept` does not belong in `resolved_beat_for` — it changes *who is debited*, not the amount. The hook fires inside the target-debit block (built in story 39-4) *before* the ally's Edge is mutated:

```
for each creature C about to take target_edge_delta D:
    for each party member M with AllyEdgeIntercept where C's id ∈ ally_whitelist:
        absorbed = min(D, max_redirect)
        M.edge = max(1, M.edge - absorbed)   // clamp-to-1 per ADR-081
        D = D - absorbed
        emit advancement.ally_edge_intercept span
        break      // first matching interceptor wins; no stacking for v1
    if D > 0: apply D to C as originally planned
```

No action or initiative cost — automatic per ADR-081 semantics. Empty `ally_whitelist` is treated as "any party ally" per ADR-081's note; for v1 heavy_metal content this case is unused.

### Character-scoped `ResourcePool` hydration

Existing `ResourcePool` struct is reused verbatim — no new pool type. Changes to `CreatureCore`:

```rust
pub struct CreatureCore {
    // ... existing fields
    pub acquired_advancements: Vec<AdvancementId>,
    pub acquired_grants: Vec<GrantRef>,           // NEW — GM-panel display
    pub character_resources: HashMap<String, ResourcePool>,  // NEW
}
```

Hydration:
- Chargen reads `character_resources:` block from the progression YAML.
- Constructs a `ResourcePool` per entry with the schema's `min/max/starting/voluntary/decay_per_scene/decay_per_turn/refill_trigger/thresholds` fields.
- Registers per-pool threshold watchers with the existing genre-pool watcher machinery (no new subsystem).
- Scene-end hook iterates each creature's `character_resources`, applies `decay_per_scene` where set, fires threshold crossing events using the existing crossing-detector.
- Turn-end hook (if any pool has `decay_per_turn`) does the same.

### `starting_kit` hydration shape

Each `grant` in `starting_kit.grants` flattens into the creature's advancement state:

- `grant.effects` → appended (one per effect) to `CreatureCore.acquired_advancements`.
- Grant-level `id`/`label`/`narration_hint` → `CreatureCore.acquired_grants: Vec<GrantRef>` purely for GM-panel display and for the ADR-078 KnownFact narration injection.

Effect resolution (`resolved_beat_for`, reaction hook) reads only the flat `acquired_advancements` list. The `acquired_grants` list is display-only. This decouples resolution logic from grant structure — compound grants (Prot'Thokk's *Stand in Front* = 2 effects) work naturally.

### `inherits:` resolution (Ludzo)

Loader sees `starting_kit.inherits: rux`, locates `rux.yaml` in the same world directory, reads *its* `starting_kit.grants`, and hydrates the inheriting character's `acquired_advancements` / `acquired_grants` as if the grants were authored on the inheriting character. Cycle detection: hard fail with `StartingKitHydrationError::InheritCycle` if `A inherits B` and `B inherits A`.

Ludzo's own `trunk` / `paths` / `capstones` still hydrate normally for future progression — only `starting_kit` is inherited.

### Error handling

All validation errors surface at chargen-time. Beat dispatch never produces hydration errors — it trusts the loaded state.

| Error | Trigger | Behavior |
|---|---|---|
| `UnknownEffectType` | YAML `type: foo_bar` with no enum match | Hard fail, chargen aborts |
| `UnknownResource` | `ConditionalEffectGating` references resource not in character or genre pools | Hard fail |
| `InheritCycle` | `A inherits B, B inherits A` | Hard fail |
| `InheritMissing` | `inherits: ghost` with no `ghost.yaml` | Hard fail |
| `MalformedAllyWhitelist` | Non-string entries in `ally_whitelist` | serde parse error |

At runtime, "no effect applied" is valid (not an error):
- `AllyEdgeIntercept` with no ally in scope matching `ally_whitelist` → no redirect, emit TRACE-level `advancement.ally_edge_intercept_skipped`.
- `AllyEdgeIntercept` when actor already at Edge = 1 → redirect fires, `absorbed_delta = 0`, full remainder continues. Span still emitted so the GM panel sees the *attempt*.
- `ConditionalEffectGating` condition false + `when_false: None` → no-op; emit span with `applied_variant: "none"`.

### OTEL contract

Every advancement decision and resource crossing emits a span. No span → no GM-panel visibility → invisible behavior. Non-negotiable per CLAUDE.md observability principle.

| Span | Fields | When |
|---|---|---|
| `advancement.effect_resolved` | `creature`, `effect_type`, `beat_id` | Each resolved_beat_for application |
| `advancement.ally_edge_intercept` | `actor`, `ally`, `original_delta`, `absorbed_delta`, `remainder`, `actor_edge_after` | Every intercept fire |
| `advancement.ally_edge_intercept_skipped` | `actor`, `reason` | Interceptor existed but didn't fire |
| `advancement.conditional_effect_gating` | `actor`, `condition`, `evaluated`, `applied_variant` | Every gating evaluation |
| `character_resource.threshold_crossed` | `creature`, `resource`, `from`, `to`, `event_id`, `direction` | Every character-pool threshold crossing |
| `character_resource.decayed` | `creature`, `resource`, `from`, `to`, `decay_per_scene` | Every scene-end decay tick |

### Testing strategy

**Unit tests** (per variant, `sidequest-game/src/advancement.rs`):
- Each of the seven variants in isolation — resolution correctness, edge cases.
- `AllyEdgeIntercept` — empty whitelist, multiple interceptors (first wins), clamp-to-1 at low Edge, absorbed_delta = 0 boundary.
- `ConditionalEffectGating` — true branch, false branch, `when_false: None`, nested recursion with another variant, missing resource → hydration error.

**Integration tests** (`sidequest-api/tests/`):
- Full beat-dispatch: enemy hits Cheeney, Prot'Thokk intercepts, deltas land as expected, OTEL spans present.
- Reniksnad decay across the 5-threshold flips *The Dose Helps* sign in the next `commit_cost`; deltas change as expected.
- Hydration golden tests: load all six Evropi YAMLs, assert expected `acquired_advancements` counts per character.

**Real wiring test** (per 39-7 pattern — no regex source matching):
- Build a real `DispatchContext`, call `apply_beat_dispatch`, assert state mutated on the creature — catches the false-positive wiring that the regex-based test missed.

## Rollout

### Definition of done

1. All 7 `AdvancementEffect` variants compile, round-trip through YAML serde cleanly.
2. `ConditionExpr` compiles and serializes with the two comparators.
3. `starting_kit` + `inherits:` hydration loads all 6 Evropi character YAMLs without error.
4. `character_resources` hydration creates Th`rook's reniksnad pool with correct thresholds, decay, starting value.
5. Reaction hook fires in `handle_applied_side_effects`; OTEL span emitted.
6. Scene-end decay hook fires on scene boundary; threshold crossings emit events.
7. Real wiring test green: Prot'Thokk intercepts; Th`rook flips sign across threshold.
8. GM panel displays all span types in advancement/resource lanes.
9. `cargo fmt` clean, `cargo clippy --workspace -- -D warnings` clean, `cargo test --workspace` green.

### Playtest acceptance (39-8 gate extension)

Story 39-8's existing playtest gains two scripted scenes:
- **Prot'Thokk defends Cheeney** — enemy beat targeting Cheeney fires; GM panel shows intercept redirect with correct math; Prot'Thokk's Edge goes down by `absorbed_delta`, Cheeney's by `remainder`.
- **Th`rook reniksnad flip** — scene-end decays reniksnad from 7 → 5; GM panel shows the threshold crossing; next `commit_cost` beat costs `-1` Flesh instead of `+1`; narrator receives the threshold's `narrator_hint` as KnownFact.

SOUL §12 test remains: narrator never describes damage the player didn't ask for.

## Consequences

**Positive**
- Prot'Thokk and Th`rook fully mechanical on first engine arrival — no wired-but-dormant gap.
- Sebastien-facing GM panel sees all ADR-081 behavior from day one of Epic 39.
- Single story delivers a self-contained slice of ADR-078 + ADR-081 + character-scoped resources.
- Two-path architecture (`resolved_beat_for` vs reaction hook) is legible and reusable for ADR-082+ variants.

**Negative**
- Story 39-5 inflates from its original scope (~8pts estimated) to ~16-18pts.
- Reaction-dispatch semantics introduce a new control-flow path in beat resolution; future variants in that path must follow the same shape to stay composable.
- Character-scoped `ResourcePool`s are a genuine `CreatureCore` schema extension; save-migration (story 39-7) needs to account for it when the schema bumps.

**Neutral**
- `acquired_grants: Vec<GrantRef>` is display-only state; carrying it costs no resolution complexity but does widen the persistence surface.

## Alternatives considered

1. **Ship ADR-081 in a follow-up story 39-9.** Rejected per brainstorming decision — wired-but-dormant `ConditionalEffectGating` (condition always false without reniksnad pool) delays Th`rook's mechanical identity and forces a stale intermediate state onto the playtest gate. "Let's get this done."
2. **Model `AllyEdgeIntercept` inside `resolved_beat_for`.** Rejected — the variant changes the *target* of the debit, not the amount. Forcing it through resolved_beat_for would couple target selection to effect resolution and mask the reaction-dispatch semantics.
3. **Store grants nested on `CreatureCore.acquired_grants: Vec<GrantWithEffects>`.** Rejected — effect resolution would then need to reach through grant structure, coupling resolution logic to authoring shape. The flattened `acquired_advancements: Vec<AdvancementId>` + display-only `acquired_grants: Vec<GrantRef>` pattern keeps the two concerns independent.
4. **Defer character-scoped `ResourcePool`s to a later story.** Rejected — Th`rook's *The Dose Helps* is the load-bearing consumer of `ConditionalEffectGating`. Without reniksnad as a real pool, the variant cannot be exercised end-to-end.

## Open items

1. First-matching-interceptor-wins for v1; stacking multiple interceptors on the same ally is deferred. Revisit if T2/T3 content demands it.
2. `resolved_beat_for` caching — if performance profiling shows repeated evaluation during scene-end ticks, consider memoization keyed on `(creature_id, beat_id, pool_snapshot_hash)`. Not an MVP concern.
3. Narrator-facing prose for `advancement.ally_edge_intercept` spans — the narrator LLM needs a consistent phrasing pattern for "actor intercepts hit". Test during 39-8 playtest; iterate if flat.

## References

- ADR-078 — Edge/Composure/Advancement/Rituals (baseline enum)
- ADR-081 — Advancement Effect Variant Expansion v1 (variant spec)
- `docs/superpowers/specs/2026-04-18-evropi-starting-kits-design.md` — content spec consuming the variants
- `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` — baseline content draft
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/prot_thokk.yaml` — `AllyEdgeIntercept` consumer
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/th_rook.yaml` — `ConditionalEffectGating` + `character_resources` consumer
- Epic 39 story 5 (backlog) — the story this design expands
- Epic 39 story 4 (backlog) — beat dispatch target-debit block the reaction hook attaches to
- Epic 39 story 7 (backlog) — save migration + UI composure sheet + wiring test harness
- Epic 39 story 8 (backlog) — acceptance playtest extended by this design
