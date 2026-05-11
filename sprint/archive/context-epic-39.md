# Epic 39: Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals

## Overview

Replace phantom HP with a first-class `EdgePool` composure currency on `CreatureCore`,
hard-link ADR-021 progression to the engine via per-genre `mechanical_effects`, and
extend `pact_working` beats with `resource_deltas` for push-currency spellcraft
(Voice / Flesh / Ledger). Heavy_metal is the reference genre — all content work in this
epic ships heavy_metal only. The other nine packs retain HP fields (phantom but declared)
until post-playtest.

Combat today is a phantom: `CreatureCore.hp / max_hp / ac` exist on every character, but
beat dispatch (`sidequest-server/src/dispatch/beat.rs:362`) logs `"HP delta via encounter
metric"` as a comment and never calls `apply_hp_delta()`. The wiring test
`beat_dispatch_wiring_story_28_5_tests.rs` regex-matches source strings and gives a
false-positive green. This epic fixes all three of that: engine-owned mechanical state,
real advancement effects, real wiring tests.

**Total:** 8 stories, 45 points. Single repo-spanning track (api + content + ui).

### Decision Record

[ADR-078](../../docs/adr/078-edge-composure-advancement-rituals.md) governs all
architectural decisions. Status: Accepted (with GM-draft amendments ratified 2026-04-15).

### Core Mechanic

```
Beat authored with edge_delta (self) and/or target_edge_delta (leverage)
        ↓
resolved_beat_for(character, beat, advancement_tree) applies AdvancementEffects
        ↓
handle_applied_side_effects debits EdgePool on acting char and/or primary opponent
        ↓
Threshold helper detects crossings; mints LoreFragments at authored at-values
        ↓
At Edge <= 0 → engine sets encounter.resolved = true, emits composure_break OTEL
        ↓
Narrator renders the real consequence — the hit that was always going to land
```

Push currencies (pact_working) route through the existing ResourcePool path —
`resource_deltas` on beats debit genre-declared `voice / flesh / ledger` pools.
Zero new engine code for rituals; pact_working is already a five-beat confrontation.

## Background

### The Gap

SideQuest has three unfinished mechanical systems that all depend on each other:

| System | Today | Problem |
|---|---|---|
| Combat HP | `CreatureCore.hp` exists, never mutated during play | Narrator improvises damage with zero engine backing |
| Advancement (ADR-021) | Four-track narrative-only | No hooks into mechanical state |
| Spellcraft | `pact_working` has prose but no cost | Narrator says "an hour of life, a memory" — engine remembers nothing |

Keith accepted they ship together: replace HP with Edge, make advancement modify Edge/beat
costs, make pact beats debit typed resource pools. Heavy_metal is already the closest to
this shape — `debt_collection.metric.name: composure` is Keith's word for it, and
`pact_working` is already authored as a five-beat ritual.

### Why Not Pure Narration?

SOUL §12 ("The Test"): if a response includes the player doing something they didn't ask
to do, it's wrong. "You take 4 damage" when the player didn't choose the beat that cost
Edge *is* the test failure. The engine must own the state mutation; the narrator describes
from it. Per ADR-057, narrator–crunch separation is preserved — engine debits, narrator
narrates.

**Primary audience filter:** Sebastien (mechanics-first player) is the acceptance gate.
The GM panel must show Edge deltas, their causes, active advancements, and beat-cost
modifiers as real OTEL-backed telemetry. If the panel can't explain *why* a beat cost 2
Edge instead of 3, the epic has failed.

### Existing Content (Drafted)

All heavy_metal content lives in
`sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` until the
relevant story lifts it into live files:

| Story | Consumes | Purpose |
|---|---|---|
| 39-3 | §1 | `edge_config` block in `rules.yaml` (per-class base_max, recovery defaults, composure thresholds) |
| 39-5 | §2 | `mechanical_effects` on affinity tiers in `progression.yaml` |
| 39-6 | §3 + §4 | Three ResourcePools + `resource_deltas` on pact_working beats |
| 39-8 | §5 + §6 | Combat beat rewrites + sample pact invocations |

GM-draft amendments ratified in ADR-078 §"Architect Rulings":
- Effects host on existing `progression.yaml` affinity tiers where they exist; otherwise
  a standalone `{genre}/advancements.yaml`. Loader supports both.
- `AdvancementEffect::LoreRevealBonus { scope }` in v1.
- `AdvancementEffect::BeatDiscount { resource_mod: Option<HashMap<String, i32>> }` for
  Pact-affinity tiers discounting push-currency costs.
- `RecoveryTrigger::OnBeatSuccess { while_strained: bool }` where `strained = current <= max/4`.
- Four extended variants (`AllyBeatDiscount`, `BetweenConfrontationsAction`,
  `AllyEdgeGrant`, `EdgeThresholdDelay`) deferred to ADR-079.
- `read_the_opponent` patience beat endorsed as 39-8 content.
- Voice / Flesh / Ledger have **no auto-refill** — narrative recovery only.

### Cross-Genre Rollout (Future)

HP deletion is heavy_metal-only in this epic. `RulesConfig` HP fields become `Option`
so the other nine packs still parse. Post-playtest, each pack migrates one-by-one. Not
in scope here.

## Technical Architecture

### Type Design

**`EdgePool` on `CreatureCore`** (`sidequest-api/crates/sidequest-game/src/creature_core.rs`):

```rust
pub struct EdgePool {
    pub current: i32,
    pub max: i32,
    pub base_max: i32,                      // pre-advancement baseline
    pub recovery_triggers: Vec<RecoveryTrigger>,
    pub thresholds: Vec<EdgeThreshold>,     // at=0 fires composure_break
}
pub struct EdgeThreshold { pub at: i32, pub event_id: String, pub narrator_hint: String }
pub enum RecoveryTrigger {
    OnResolution,
    OnBeatSuccess { beat_id: String, amount: i32, while_strained: bool },
    OnAllyRescue,
}
```

`CreatureCore.edge: EdgePool` replaces `hp / max_hp / ac`. The `Combatant` trait loses
`hp() / max_hp() / ac()` and gains `edge() / max_edge() / is_broken()`.

**Shared threshold helper** (`sidequest-game/src/thresholds.rs`, new): extract
`detect_crossings` and `mint_threshold_lore` out of `resource_pool.rs` so both
`ResourcePool::apply_and_clamp` and `EdgePool::apply_delta` call it. Parameterized on
`(current, new, &[impl ThresholdAt])` — plain function, no trait gymnastics.

**`BeatDef` extensions** (`sidequest-genre/src/models/rules.rs`):

```rust
pub edge_delta: Option<i32>,                       // debits acting char (positive = cost)
pub target_edge_delta: Option<i32>,                // debits primary opponent
pub resource_deltas: Option<HashMap<String, f64>>, // debits named ResourcePools
```

Three optional fields symmetric with existing `gold_delta`. No new enum, no structured
push type — Edge stays typed because it lives on `CreatureCore` as a first-class field.

**`AdvancementTree`** (new module `sidequest-genre/src/models/advancement.rs`):

```rust
pub struct AdvancementTree { pub tiers: Vec<AdvancementTier> }
pub struct AdvancementTier {
    pub id: String,
    pub required_milestone: String,     // references ADR-021 Milestone track
    pub class_gates: Vec<String>,       // empty = universal
    pub effects: Vec<AdvancementEffect>,
}
pub enum AdvancementEffect {
    EdgeMaxBonus { amount: i32 },
    EdgeRecovery { trigger: RecoveryTrigger, amount: i32 },
    BeatDiscount { beat_id: String, edge_delta_mod: i32, resource_mod: Option<HashMap<String, i32>> },
    LeverageBonus { beat_id: String, target_edge_delta_mod: i32 },
    LoreRevealBonus { scope: LoreRevealScope },
}
```

Character carries `CreatureCore.acquired_advancements: Vec<String>` (tier ids only).
Effects resolve from the genre tree on read — no materialized state, so designer retunes
survive save migrations.

**`resolved_beat_for`** (new `sidequest-game/src/advancement.rs`): pure view function
that takes `(&CharacterState, &BeatDef, &AdvancementTree)` and returns a `ResolvedBeat`
with effective `edge_delta / target_edge_delta / resource_deltas` plus
`source_effects: Vec<&AdvancementEffect>` for telemetry. Immutable borrow enforces
determinism.

### Engine Wiring

**Self-debit path** — extends `dispatch/beat.rs::handle_applied_side_effects` with a
block parallel to the existing `gold_delta` handling at `beat.rs:319-337`:

1. `let resolved = resolved_beat_for(acting_char, beat, &genre.advancement_tree);`
2. `let result = acting_char.core.edge.apply_delta(resolved.edge_delta);`
3. For each crossed threshold, mint a LoreFragment via the shared threshold helper.
4. Emit OTEL `creature.edge_delta` with fields `action`, `source`, `beat_id`,
   `advancements_applied`.

**Target-debit path (leverage):** when `resolved.target_edge_delta.is_some()`, walk
`ctx.snapshot.encounter.actors`, pick the primary opponent (v1: first actor with
`role=opponent`), apply the delta to their `core.edge`. NPCs embed `CreatureCore`, so
the call site is identical.

**Composure break:** after both debits, check
`if acting_char.core.edge.current <= 0 || primary_opponent.core.edge.current <= 0`.
Set `encounter.resolved = true`, emit `encounter.composure_break` OTEL. The existing
resolution branch at `beat.rs:396` handles the rest. Narrator describes the break;
engine owns the state mutation (ADR-057 preserved).

**ResourcePool deltas (pact pushes):** when `resolved.resource_deltas.is_some()`, route
through the existing `dispatch/state_mutations.rs:328-407` path — no new code, just a
second call site. PatchLegality already validates voluntary spends.

### Extension Strategy (Additive + One Delete)

| Change | Nature | Scope |
|---|---|---|
| `EdgePool` type + `CreatureCore.edge` | Add | Universal |
| `CreatureCore.hp / max_hp / ac` | **Delete** | Universal (cascades workspace-wide) |
| `sidequest-game/src/hp.rs` | **Delete** | File |
| `Combatant` trait HP methods | Replace with Edge methods | Universal |
| `BeatDef` three new optional fields | Add | Universal |
| `AdvancementTree` + effects | Add | Universal |
| `CreatureCore.acquired_advancements` | Add | Universal |
| Heavy_metal HP fields in `rules.yaml` | **Delete** | heavy_metal only |
| Heavy_metal `edge_config` block | Add | heavy_metal only |
| Heavy_metal `voice/flesh/ledger` resources | Add | heavy_metal only |
| Heavy_metal `pact_working` beats `resource_deltas` | Add | heavy_metal only |
| `RulesConfig` HP fields become `Option` | Modify | Universal (gate for other packs) |
| `beat_dispatch_wiring_story_28_5_tests.rs` | **Rewrite** | Fix false-positive regex test |
| React character sheet | Replace HP bar with composure bar | UI |

### Infrastructure Reuse Audit

| Need | Existing Infrastructure | Verdict |
|------|------------------------|---------|
| Threshold detection | `resource_pool.rs::detect_crossings / mint_threshold_lore` | Extract to shared helper |
| Resource debit path | `dispatch/state_mutations.rs:328-407` | Reuse for `resource_deltas` |
| Side-effect handler | `beat.rs::handle_applied_side_effects` (gold_delta block) | Mirror pattern for edge_delta |
| Resolution branch | `beat.rs:396` | Reuse; engine just sets `resolved = true` |
| Milestone grant bus | ADR-021 Milestone track | Hook `acquired_advancements` grant here |
| Ritual prompt hints | Existing `in_combat` conditional (ADR-067) | Mirror for `category == "ritual"` |
| OTEL infra | ADR-031, ADR-058 | Reuse; new span names only |
| Save serde | `persistence.rs` | Extend with v-bump + legacy synthesis |
| ResourcePool | Existing `resource_pool.rs` | Reuse — voice/flesh/ledger are ordinary pools |

**Net new Rust code:** one struct (`EdgePool`), one module (`thresholds.rs`), one module
(`advancement.rs`), one enum (`AdvancementEffect`), three optional `BeatDef` fields,
two match arms in `handle_applied_side_effects`, one prompt conditional, save migration
path. Everything else is reuse or deletion.

### OTEL Spans (Required)

| Span | Emitted When |
|------|-------------|
| `creature.edge_delta` | EdgePool mutated — fields: action, source, beat_id, advancements_applied, delta, new_current |
| `encounter.composure_break` | Acting char or primary opponent reaches Edge <= 0 |
| `advancement.effect_applied` | `resolved_beat_for` applies an AdvancementEffect — fields: effect_type, source_tier, beat_id |
| `advancement.tier_granted` | Milestone triggers tier acquisition |
| `resource_pool.debited` | Pact push currency spent (existing span, new call site) |
| `edge.threshold_crossed` | EdgeThreshold at-value crossed (feeds LoreStore) |

### Story Breakdown (Dependency-Ordered)

```
  39-1 (threshold helper + EdgePool type) ─────┐
                                               │
  39-2 (delete HP from CreatureCore) ──────────┤
                                               │
  39-3 (purge HP from heavy_metal YAML) ───────┤
                                               │
  39-4 (BeatDef edge_delta + dispatch wiring) ─┼─→ 39-5 (advancement tree + resolved_beat_for)
                    │                          │         │
                    │ SMOKE GATE               │         │
                    │ (hard-coded +2 stub)     │         │
                    │                          │         ↓
                    │                          ├──→ 39-6 (heavy_metal pact push currencies)
                    │                          │         │
                    │                          ├──→ 39-7 (save migration + UI + real wiring test)
                    │                          │         │
                    └──────────────────────────┴──→ 39-8 (full playtest acceptance gate)
```

| # | Title | Scope | Points |
|---|---|---|---|
| 39-1 | Extract threshold helper + EdgePool type | `thresholds.rs` + `EdgePool` struct + unit tests; no wiring | 5 |
| 39-2 | Delete HP from CreatureCore | Remove hp/max_hp/ac; delete `hp.rs`; fix Combatant; cascade compile errors; placeholder edge in constructors | 8 |
| 39-3 | Purge HP from heavy_metal YAML + loader | Strip HP fields (heavy_metal only); make RulesConfig HP Option; add `edge_config` block | 3 |
| 39-4 | BeatDef.edge_delta + target_edge_delta + dispatch wiring | Extend BeatDef; self-debit + target-debit blocks; OTEL; auto-resolve on zero; stub advancement for smoke playtest | 8 |
| 39-5 | Authored advancement effects + resolved_beat_for | AdvancementEffect enum; RecoveryTrigger extensions; acquired_advancements; resolved_beat_for view; per-genre audit; milestone-grant path | 8 |
| 39-6 | Heavy_metal pact push currencies | Three ResourcePools; resource_deltas on pact_working beats; prompt conditional for category=ritual | 5 |
| 39-7 | Save migration + UI composure sheet + real wiring test | Sqlite schema bump; legacy HP→Edge synthesis; React composure sheet; rewrite regex test to real DispatchContext | 5 |
| 39-8 | Playtest heavy_metal with full new system (acceptance gate) | Author advancement tree; rewrite combat beats; run 3 sample pacts; SOUL §12 test; GM panel OTEL trail | 3 |

**Smoke playtest gate at end of 39-4:** with hard-coded stub advancement (e.g. Fighter
`+2 edge_max`), Keith runs a heavy_metal combat and *feels* whether Edge reads right
before committing 39-5 through 39-8. Failure options: retune beat `edge_delta` in YAML
(cheap) or abandon (salvage 39-1 threshold refactor, revert the rest).

### HP Deletion Sequencing (heavy_metal-scoped)

1. **39-3** strips `hp_formula`, `class_hp_bases`, `default_hp`, `default_ac`,
   `stat_display_fields: [hp, max_hp, ac]` from `heavy_metal/rules.yaml` only.
2. `RulesConfig` loader changes those fields from required to `Option` — the single gate
   that lets heavy_metal go HP-free while other genres still parse.
3. **39-2** deletes `CreatureCore.hp / max_hp / ac` and cascades compile errors across
   the workspace. `sidequest-game/src/hp.rs` is deleted outright.
4. **39-7** save migration: `persistence.rs` detects v(old) saves, synthesizes
   `EdgePool { current: base_max, max: base_max, base_max: class_base_from_legacy_hp_formula / 2, ... }`.
   The divide-by-2 is a sane heuristic because Edge is not HP and should not inherit
   HP's numeric magnitude.
5. **39-7** UI: `stat_display_fields` becomes `[edge, max_edge, composure_state]`.
   React character sheet reads declaratively from this list.
6. **39-7** fix the false-positive wiring test: rewrite
   `beat_dispatch_wiring_story_28_5_tests.rs` to build a minimal `DispatchContext`,
   call `apply_beat_dispatch` + `handle_applied_side_effects` on a real `strike` beat,
   and assert `ctx.snapshot.characters[0].core.edge.current` decreased by the expected
   amount. Non-negotiable per CLAUDE.md wiring-test rule.

### Key Files

**New:**
| File | Role |
|------|------|
| `docs/adr/078-edge-composure-advancement-rituals.md` | ADR |
| `sidequest-api/crates/sidequest-game/src/thresholds.rs` | Shared threshold helper |
| `sidequest-api/crates/sidequest-game/src/advancement.rs` | `resolved_beat_for` view |
| `sidequest-api/crates/sidequest-genre/src/models/advancement.rs` | AdvancementTree types |
| `sidequest-content/genre_packs/heavy_metal/advancements.yaml` | If host-audit decides standalone (else lives in `progression.yaml`) |

**Modified (core):**
| File | Change |
|------|--------|
| `sidequest-api/crates/sidequest-game/src/creature_core.rs` | Delete hp/max_hp/ac; add `edge: EdgePool` + `acquired_advancements` |
| `sidequest-api/crates/sidequest-game/src/resource_pool.rs` | Extract shared threshold helpers |
| `sidequest-api/crates/sidequest-game/src/hp.rs` | **Deleted** |
| `sidequest-api/crates/sidequest-genre/src/models/rules.rs` | BeatDef fields; RulesConfig HP → Option |
| `sidequest-api/crates/sidequest-server/src/dispatch/beat.rs` | Self-debit + target-debit blocks; OTEL; auto-resolution |
| `sidequest-api/crates/sidequest-server/src/dispatch/state_mutations.rs` | Remove level-up HP healing; add Edge recovery path |
| `sidequest-api/crates/sidequest-game/src/persistence.rs` | Save migration v-bump |
| `sidequest-api/tests/beat_dispatch_wiring_story_28_5_tests.rs` | Rewrite from regex-match to real dispatch + assertion |

**Modified (content):**
| File | Change |
|------|--------|
| `sidequest-content/genre_packs/heavy_metal/rules.yaml` | Strip HP; add edge_config; add voice/flesh/ledger resources; extend pact_working beats; rewrite combat beats |
| `sidequest-content/genre_packs/heavy_metal/progression.yaml` | Add `mechanical_effects:` arrays to affinity tiers (Iron/Pact/Court/Ruin/Craft/Lore) per draft §2 |
| `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` | Source of truth for 39-3/5/6/8 lifts; removed as drafts land |

**Modified (UI):**
| File | Change |
|------|--------|
| `sidequest-ui/src/character/**` | Composure bar component; read `edge / max_edge / composure_state` declaratively; remove HP bar |

### Open Questions (Resolved During Implementation)

1. **Multi-target beats** (`cleave`, `hail_of_arrows`): v1 uses `target_edge_delta`
   against primary opponent only. Multi-target → follow-up story if playtest demands.
2. **`composure_state` UI field**: derived enum (`Fresh >75%`, `Strained 50-75%`,
   `Cracked 25-50%`, `Broken ≤25%`). Derived in frontend from `current/max` ratio;
   not persisted.
3. **Ability scores (STR/DEX/CON/INT/WIS/CHA):** stay. Beats still use `stat_check`.
   Out of scope.
4. **`acquired_advancements` grant path:** milestone achievement (ADR-021) triggers
   engine to apply next tier. Dev wires via existing Milestone event bus — no new bus.
5. **LoreStore fragments referencing "HP":** old saves have "took 4 damage" lore that
   will read oddly post-migration. One-shot lore scrub is out of scope — playtest saves
   re-rolled for the clean heavy_metal playtest.
6. **Audit other `*_wiring_story_*` tests:** the false-positive regex anti-pattern may
   exist elsewhere. Follow-up ticket, not this epic.
7. **Per-genre effect-host audit** (in 39-5): determine which genres host
   `mechanical_effects` on `progression.yaml` affinity tiers vs. a new
   `advancements.yaml`. Loader supports both.

### Risks

- **Edge numerics** are first-pass. 39-4 smoke playtest is the tuning gate; numbers live
  in YAML, cheap to retune.
- **HP cascade** (39-2) touches every `.hp` / `apply_hp_delta` / `Combatant::hp()`
  call site workspace-wide. Expect many compile errors. Mitigation: placeholder edge in
  constructors so the workspace reaches green before 39-3/4 fill in real values.
- **False-positive wiring test** has been green for a year. Fixing it (39-7) may surface
  other subsystems that never actually wired. Mitigation: scope to this test; follow-up
  ticket for broader audit.
- **Save migration magnitude heuristic** (HP÷2) is a guess. Mitigation: documented in
  ADR-078; playtest saves re-rolled; legacy-save players get a one-line release note.
- **Multi-genre HP phantom retention:** other nine packs still declare HP fields that
  the engine will never write. Acceptable for this epic; cleanup is the post-playtest
  rollout.

## Planning Documents

| Document | Location |
|----------|----------|
| ADR-078 | `docs/adr/078-edge-composure-advancement-rituals.md` |
| ADR-079 (deferred effects) | `docs/adr/079-genre-theme-unification.md` |
| ADR-021 (progression parent) | `docs/adr/021-four-track-progression.md` |
| ADR-033 (confrontation parent) | `docs/adr/033-confrontation-engine.md` |
| ADR-057 (narrator-crunch separation) | `docs/adr/057-narrator-crunch-separation.md` |
| ADR-067 (unified narrator prompt) | `docs/adr/067-unified-narrator.md` |
| Implementation plan | `~/.claude/plans/ticklish-spinning-reef.md` |
| Heavy_metal content drafts | `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` |
