# ADR-078: Edge / Composure Combat, Mechanical Advancement, and Push-Currency Rituals

**Status:** Proposed
**Date:** 2026-04-15
**Epic:** TBD (proposed: Epic-Edge, post-Sprint-2)
**Deciders:** Keith
**Relates to:**
- ADR-021 (Four-Track Progression) — first hard link from progression to engine state
- ADR-033 (Confrontation Engine + Resource Pools) — parent decision; this ADR fully consumes its primitives
- ADR-057 (Narrator-Crunch Separation) — preserved: narrator describes, engine mutates
- ADR-059 (Monster Manual / Game-State Injection) — supersedes narrator tool calls; ritual uses injection, not tools
- ADR-067 (Unified Narrator Agent) — conditional prompt sections, no new agent

## Context

### The phantom HP problem

Combat in SideQuest today is two parallel systems running past each other.

`StructuredEncounter` (ADR-033) runs an abstract metric clock — `momentum`, `tension`, `leverage`, `separation` — that the narrator reads to color combat prose. In parallel, `CreatureCore.hp` and `max_hp` exist on every character. The two systems are not connected.

Tracing the actual code:

- `sidequest-server/src/dispatch/beat.rs:362` logs `"HP delta via encounter metric"` as a comment string and **never calls `apply_hp_delta()`** on any creature.
- The only write path that reaches `CreatureCore.hp` during play is the level-up healing block at `sidequest-server/src/dispatch/state_mutations.rs:56-59`, which scales `max_hp` and tops up `hp` to the new ceiling. There is no damage path.
- The integration test `sidequest-api/tests/beat_dispatch_wiring_story_28_5_tests.rs` was supposed to verify this wiring. It instead regex-matches source strings ("references resolve_attack or apply_hp_delta") and gives a false-positive green even though neither function is invoked at runtime.

What the player experiences as "combat damage" is the narrator inferring damage from the `metric.current` value of the encounter clock and writing prose that *implies* HP loss while the actual HP field stays static. Combat is a story the narrator tells about a number that does not exist.

### What Keith actually wants from combat

> "Why should I be able to stand 15 hacks of the sword when I can only stand one at first level and most people can only take so many hacks of the sword?"

A level-10 fighter does not eat fifteen sword blows. He **does not let the real hit land** until his composure breaks. The mechanic should be deflection-against-pressure, not meat-against-attrition. When pressure exceeds composure, the *next* exchange resolves in genre-true fashion — a wound, a yield, a capture, a death.

This framing has three downstream requirements:

1. **A composure currency on every character** — typed, universal, drained by exchanges and refilled between confrontations.
2. **Advancement that increases composure capacity, recovery, beat discount, or hit-leverage** — the same dials that distinguish a Brute from a Duelist mechanically rather than through pure narration.
3. **A spellcraft mechanic that costs the caster something beyond a slot** — voice, body, ledger entry — paid as typed debits at the moment of the cast.

### What is already authored

Heavy_metal (the reference genre for this ADR) has already been *living* this design in prose:

- `confrontations[type=debt_collection]` uses `metric.name: composure`, starting 6, threshold_low 0, with the consequence at zero stated as *"the debt collects at full price, on the terms the creditor prefers."* This is the Edge mechanic, authored a month ago for a social confrontation.
- `confrontations[type=pact_working]` is a five-beat ritual with `rite_progress` 0→10 and beats `invoke / commit_cost / steady_the_rite / force_completion / close_the_book`. The `commit_cost` narrator hint reads: *"an hour of life, a memory, a name, a year. Whatever is spent, it leaves."* This is the spellcraft push mechanic, authored as flavor with no engine backing.

Keith has been play-testing the *feel* of Edge and push-currency rituals for months in narrator prose. This ADR gives both a typed mechanical spine.

### What is genuinely new

Only one thing: **the first hard link between ADR-021 progression and engine state.** Today, the four progression tracks (Milestone, Affinity, Item, Wealth) modify narration hints and zero engine parameters. This ADR introduces declarative advancement effects that mutate per-character beat costs, edge capacity, and hit leverage at beat-resolution time.

## Decision

### 1. Edge as a first-class `CreatureCore` field

Edge lives on `CreatureCore`, not as a `ResourcePool`. Universal primitive, type-clear, no genre-declaration ceremony.

```rust
pub struct EdgePool {
    pub current: i32,
    pub max: i32,
    pub base_max: i32,                       // pre-advancement
    pub recovery_triggers: Vec<RecoveryTrigger>,
    pub thresholds: Vec<EdgeThreshold>,
}
pub struct EdgeThreshold { pub at: i32, pub event_id: String, pub narrator_hint: String }
pub enum RecoveryTrigger {
    OnResolution,
    OnBeatSuccess { beat_id: String, amount: i32 },
    OnAllyRescue,
}
```

`CreatureCore.hp / max_hp / ac` are deleted. `CreatureCore.edge: EdgePool` replaces them. The `Combatant` trait loses `hp() / max_hp() / ac()` and gains `edge() / max_edge() / is_broken()`.

**Rejected alternative:** Edge as a `ResourcePool` with a `universal: true` flag. Rejected because Edge is touched on every beat for every character — funneling it through a `HashMap<String, ResourcePool>` lookup keyed on the literal string `"edge"` would make the most-touched mechanical state of the game stringly-typed for no benefit. Type clarity wins.

### 2. Reuse-first: shared threshold helper

`mint_threshold_lore` and the `detect_crossings` logic currently live inside `sidequest-game/src/resource_pool.rs`. Extract them into a new `sidequest-game/src/thresholds.rs` parameterized over a slice of `(at, event_id, narrator_hint)` tuples. Both `ResourcePool::apply_and_clamp` and `EdgePool::apply_delta` call the helper. No trait gymnastics — a function taking a slice of items implementing a tiny `ThresholdAt` trait.

This is the only refactor justified by the ADR. Every other Edge primitive composes existing infrastructure rather than duplicating it.

### 3. `BeatDef` extension: three symmetric optional fields

```rust
pub edge_delta: Option<i32>,                       // debits acting char (positive = cost)
pub target_edge_delta: Option<i32>,                // debits primary opponent
pub resource_deltas: Option<HashMap<String, f64>>, // debits genre ResourcePools
```

These parallel the existing `gold_delta: Option<i32>` field at `sidequest-genre/src/models/rules.rs:188`. Engine handler clauses are added to `dispatch/beat.rs::handle_applied_side_effects`, in the same shape as the existing gold_delta block at `beat.rs:319-337`.

**Rejected alternative:** A structured `pushes: Vec<PushOption>` enum carrying both Edge and ResourcePool costs in one variant tree. Rejected because Edge is typed (lives on `CreatureCore`) and ResourcePools are stringly-keyed — collapsing them into one enum forces every consumer to handle both cases. Three optional fields are simpler and surface the type distinction at the schema level.

### 4. Engine-derived resolution on composure break

When `handle_applied_side_effects` applies an `edge_delta` (self or target), it checks `if char.core.edge.current <= 0` immediately afterward. If true:

- Set `encounter.resolved = true`
- Emit OTEL `encounter.composure_break` with fields `{ char_name, beat_id, side: self|target }`
- The existing resolution branch at `beat.rs:396` carries the encounter to closure

The narrator still **describes** the break — the real hit that finally lands, the stagger, the yield. The engine owns the **state mutation**. This preserves ADR-057's narrator-crunch separation: narration → LLM, crunch → scripts.

### 5. Per-genre authored advancement effects

**Effects host on existing genre progression structures wherever those exist.** Genres that already have an authored progression scaffold (affinities, tier_thresholds, milestone categories) — heavy_metal is the load-bearing example — slot `mechanical_effects:` arrays into their existing affinity-tier definitions inside `progression.yaml`. This is a strict reuse-first commitment: ADR-021's Affinity Tiers track *is* the advancement gate, and creating a parallel `advancements.yaml` would run two progression systems in parallel that the player would experience as double-bookkeeping.

Genres without an existing affinity scaffold may declare a new `{genre}/advancements.yaml`. Story 5 must include a per-genre audit pass (a content task, not an engine task) to determine which genres host effects in `progression.yaml` and which need a new file. The loader supports both locations from day one.

**Heavy_metal example** — `mechanical_effects` arrays added to existing affinity tiers in `progression.yaml`:

```yaml
# In heavy_metal/progression.yaml, alongside existing affinity definitions:
affinities:
  - name: "Iron"
    description: "Martial bearing — the sword-work of doomed princes…"
    triggers: [...]                # unchanged
    tier_thresholds: [6, 14, 28]   # unchanged — these are the milestone gates
    mechanical_effects:            # NEW: per-tier effects
      - tier: 1
        label: "Standing Wound"
        effects:
          - { type: edge_max_bonus, amount: 1 }
      - tier: 3
        label: "The Sword-Work of Doomed Princes"
        effects:
          - { type: leverage_bonus, beat_id: committed_blow, target_edge_delta_mod: -1 }
          - { type: edge_max_bonus, amount: 2 }
```

For genres with no affinity scaffold, the alternative authoring path is a standalone file:

```yaml
# In {genre}/advancements.yaml — only if the genre has no existing progression host
advancements:
  - id: steel_lungs
    tier: 1
    required_milestone: first_victory
    class_gates: [Fighter]
    effects:
      - { type: edge_max_bonus, amount: 2 }
```

Effect types:

```rust
pub enum AdvancementEffect {
    EdgeMaxBonus { amount: i32 },
    EdgeRecovery { trigger: RecoveryTrigger, amount: i32 },
    BeatDiscount { beat_id: String, edge_delta_mod: i32, resource_mod: Option<HashMap<String, i32>> },
    LeverageBonus { beat_id: String, target_edge_delta_mod: i32 },
    LoreRevealBonus { scope: LoreRevealScope },  // narrator-side reveal hook for non-combat affinities
}

pub enum LoreRevealScope {
    SupernaturalEntity,
    ObjectProvenance,
    HiddenMotivation,
    AncientLanguage,
}

pub enum RecoveryTrigger {
    OnResolution,
    OnBeatSuccess { beat_id: String, while_strained: bool },
    OnAllyRescue,
}
```

**Note on `BeatDiscount.resource_mod`:** added in this revision so that Pact-affinity tiers can discount push-currency costs on `pact_working` beats (e.g. tier 2 reduces `commit_cost`'s flesh debit by 1). Without this field, advancement could only modify Edge debits and not the typed ResourcePool debits introduced in §3, leaving Pact effectively unable to mechanically advance pact-working.

**Note on `RecoveryTrigger.while_strained`:** added so Ruin tier 2 ("strength from grief") can fire only when the actor is at low Edge — defined precisely as `current <= max / 4`, matching the UI's "Cracked" composure_state. Without this, Ruin's thematic core ("stand once after you should have fallen") cannot be expressed mechanically.

**Note on `LoreRevealBonus`:** added so non-combat affinities (Lore, Craft) have at least one mechanical hook in v1. The narrator prompt assembler reads this and injects an additional reveal hint when the active scene matches scope. Cheap to implement — single field on the prompt context, no plumbing change to beat dispatch or `resolved_beat_for`.

**Deferred to ADR-079 (Affinity Hooks Enrichment):** four additional `AdvancementEffect` variants requested by GM but requiring substantial new plumbing — `AllyBeatDiscount` (party-aware `resolved_beat_for`), `BetweenConfrontationsAction` (new game-state slot), `AllyEdgeGrant` (scene-scope ally lookup), `EdgeThresholdDelay` (conditional threshold firing). Heavy_metal Lore/Craft tiers ship with `LoreRevealBonus` at tier 1 and explicit `mechanical_effects: []  # TODO ADR-079` placeholders at tiers 2-3. The empty arrays are documented stubs with a follow-up ticket, not silent half-shipping. ADR-079 is filed after story 8's playtest acceptance gate clears.

Characters carry only `acquired_advancements: Vec<String>` (tier ids). Effects are resolved from the immutable genre tree on read via:

```rust
pub fn resolved_beat_for(
    character: &CharacterState,
    beat: &BeatDef,
    tree: &AdvancementTree,
) -> ResolvedBeat
```

A pure view function. No materialized-effect state on the character means the designer can retune numbers without save migrations.

This is **the first hard link** from ADR-021 progression to engine state. Milestones earned through play (existing ADR-021 mechanism) push tier ids onto `acquired_advancements`; subsequent beat dispatch resolves through the tree.

### 6. Spellcraft = `pact_working` extension, not a new confrontation type

Heavy_metal's `pact_working` confrontation is the spellcraft shape Keith asked for. It already has the three-beat-plus-resolution structure, the rite_progress metric, and the narrator hints that describe paying with body, name, and time.

This ADR **extends** `pact_working` beats with `resource_deltas`. It does not introduce a new `encounter_type: ritual`. Three new genre-declared `ResourcePool`s carry the push currencies:

```yaml
resources:
  - { name: voice,  label: "Voice",  min: 0, max: 10, starting: 10, voluntary: true,
      thresholds: [{ at: 1, event_id: voice_spent,
                     narrator_hint: "The last true name is almost out." }] }
  - { name: flesh,  label: "Flesh",  min: 0, max: 10, starting: 10, voluntary: true }
  - { name: ledger, label: "Ledger", min: 0, max: 10, starting: 10, voluntary: true }
```

Existing pact_working beats gain debits:
- `invoke { resource_deltas: { voice: -1 } }`
- `commit_cost { resource_deltas: { flesh: -2 } }`
- `steady_the_rite { resource_deltas: { voice: -1 } }`
- `force_completion { resource_deltas: { ledger: -3, flesh: -1 } }`

Engine plumbing reuses the existing narrator `resource_deltas` path at `dispatch/state_mutations.rs:328-407`. The narrator's prose is unchanged — it already describes "an hour of life, a memory, a name, a year." We are making those costs typed and engine-tracked.

**No `resolve_ritual()` tool.** ADR-059 established that `claude -p` ignores tool-calling instructions empirically. Game-state injection is the validated pattern. The existing beat-selection path, plus the new `resource_deltas` debit handler, covers ritual entirely.

The only prompt-side change is one `if confrontation.category == "ritual"` conditional in the unified narrator prompt assembler (ADR-067), injecting genre `ritual_narration_hints` when active. Mirrors the existing `in_combat` conditional.

### 7. HP deletion: heavy_metal-first

Story 3 of the epic strips HP fields from `heavy_metal/rules.yaml` only:

- `hp_formula`, `class_hp_bases`, `default_hp`, `default_ac`, `stat_display_fields: [hp, max_hp, ac]` — removed
- New `edge_config:` block declaring per-class `base_max`, default `recovery_triggers`, composure-break threshold

The `RulesConfig` loader (`sidequest-genre/src/models/rules.rs`) makes those HP fields `Option`. The other 9 genre packs retain their HP fields (phantom but declared) until the heavy_metal playtest proves Edge feels right.

`CreatureCore.hp / max_hp / ac` are deleted workspace-wide in story 2, with cascading compile-error fixes across `sidequest-game`, `sidequest-server`, `sidequest-ui`, and tests. `sidequest-game/src/hp.rs` is deleted outright. Save migration in `sidequest-game/src/persistence.rs` synthesizes `EdgePool { base_max: legacy_class_hp_base / 2, ... }` for v(old) saves.

The false-positive wiring test `beat_dispatch_wiring_story_28_5_tests.rs` is rewritten in story 7 to build a real `DispatchContext`, call `apply_beat_dispatch + handle_applied_side_effects`, and assert that `ctx.snapshot.characters[0].core.edge.current` actually decreased. The current regex-the-source pattern is a quality smell that must not propagate to other wiring tests.

## Story breakdown

The epic is 8 stories, dependency-ordered, with a smoke playtest gate at the end of story 4. See the implementation plan at `~/.claude/plans/ticklish-spinning-reef.md` for full story scopes, file lists, and content authoring requirements. Summary:

| # | Title | Owner | Size |
|---|---|---|---|
| 1 | Extract threshold helper + `EdgePool` type | Dev | M |
| 2 | Delete HP from `CreatureCore` and cascade compile errors | Dev | L |
| 3 | Purge HP from heavy_metal YAML + loader; add `edge_config` | GM + Dev | S |
| 4 | `BeatDef.edge_delta` + dispatch wiring + smoke playtest gate | Dev | L |
| 5 | Authored advancement tree + `resolved_beat_for` | Dev | L |
| 6 | Heavy_metal pact push currencies (content) | GM | M |
| 7 | Save migration + UI composure sheet + real wiring test | Dev | M |
| 8 | Playtest heavy_metal with full new system (acceptance gate) | GM + Keith | M |

## Consequences

### Positive

- **Combat stops being a phantom.** The narrator's prose is finally backed by mechanical state the engine validates and the GM panel can audit.
- **Sebastien gets mechanical visibility.** Every Edge change is OTEL-traced with beat_id, source, and applied advancement effects. The GM panel becomes a polygraph on combat the same way it already is on lore filtering and resource thresholds.
- **The first hard link from progression to engine state ships** (closes the ADR-021 gap). Future ADRs can reuse the `AdvancementEffect` enum pattern for non-combat progression hooks.
- **Spellcraft becomes typed without inventing a new subsystem.** `pact_working` was already the right shape; we extend rather than reinvent.
- **The dead HP code path is eliminated.** Future maintainers do not have to wonder why combat works without HP changing — there is no HP.
- **Reuse-first paid off.** The delta between "brand new combat subsystem" and "ADR-033 + ADR-021 extension" is one new type (`EdgePool`), three new optional `BeatDef` fields, one new module (`advancement.rs`), one extracted helper (`thresholds.rs`), and one deleted file (`hp.rs`). Every other line is content authoring against existing rails.

### Negative

- **9 genre packs sit in a half-state through Sprint 2.** Heavy_metal goes Edge-only; the other 9 packs retain phantom HP fields until a follow-up epic. Player-facing impact is zero (HP wasn't doing anything to begin with), but the inconsistency is real.
- **Save migration is load-bearing.** In-progress playtest saves get a synthesized EdgePool from legacy HP. The numeric magnitude divide-by-2 heuristic may need tuning. Old narrative LoreStore fragments referencing "took 4 damage" will read oddly post-migration; a one-shot lore scrub is out of scope and playtest saves should be re-rolled for the clean Edge playtest.
- **The advancement tree is per-genre authored, not generic.** Heavy_metal gets a hand-authored tree first; the other 9 genres get nothing until each is authored individually. This is intentional (Sebastien-legible, genre-truthful) but it is authoring debt.

### Risks

- **The advancement-tree lookup happens on every beat dispatch for every character.** If `resolved_beat_for` is not pure or the tree is mutated mid-game, determinism breaks. **Mitigation:** pass the tree by immutable borrow from the loaded `&GenrePack`; cover with a property test that runs the same beat twice and asserts identical `ResolvedBeat`.
- **"Edge feels like HP with extra steps."** This is the design failure mode. **Mitigation:** the smoke playtest gate at end of story 4 lets Keith *feel* Edge before stories 5-8 are written. If the concept fails, retune `edge_delta` numbers in YAML (cheap) or abandon (salvage the threshold-helper extraction; revert the rest).
- **Multi-target beats are deferred to v2.** `target_edge_delta` v1 hits the primary opponent only. `cleave`, `hail_of_arrows`, area effects need a follow-up field (`target_rule: primary | all_engaged | radius`). **Mitigation:** ship v1, file the follow-up after the playtest demands it.
- **The false-positive wiring test anti-pattern may exist elsewhere.** `beat_dispatch_wiring_story_28_5_tests.rs` regex-matches source strings instead of asserting runtime behavior. Other `*_wiring_story_*` integration tests should be audited. **Mitigation:** out of scope for this epic; file a follow-up audit ticket.

## Alternatives Considered

### A: Edge as a generic `ResourcePool` with `universal: true` flag

Rejected. Edge is touched on every beat for every character — funneling it through `HashMap<String, ResourcePool>` lookups keyed on the literal string `"edge"` would make the most-touched mechanical state of the game stringly-typed for no benefit. ResourcePool is the right primitive for *genre-specific* tracked resources (Luck, Heat, Voice, Flesh, Ledger). Edge is universal and deserves first-class typed storage on `CreatureCore`.

### B: Add a new `encounter_type: ritual` distinct from `pact_working`

Rejected. Heavy_metal's `pact_working` is mechanically identical to what was being proposed — same five-beat structure, same ascending metric, same narrator hints describing typed costs that aren't yet typed. Adding a parallel `ritual` type would create two near-duplicate confrontation definitions. The reuse-first decision is to extend `pact_working` beats with `resource_deltas` and let the existing category routing handle it.

### C: Keep HP as a "wounds track" — count of real injuries landed after Edge breaks

Considered. The appeal: a persistent state slot for "things that have happened to this character beyond the current scene." Rejected because it overlaps with the existing LoreStore `KnownFact` mechanism, which already minted threshold events that survive across scenes. A wound is a high-relevance LoreFragment, not a parallel int counter. Keep CreatureCore lean.

### D: Half-ship: Edge primitive only, defer advancement and rituals

Rejected by Keith. The argument for half-shipping was smaller blast radius. The argument against — and the one Keith took — is that Edge without advancement is just a renamed metric clock, and Edge without ritual integration leaves heavy_metal's most distinctive feature (pact_working) still mechanically inert. Ship the package or don't.

### E: Build the `resolve_ritual()` narrator tool for spellcraft

Rejected on ADR-059 evidence. `claude -p` empirically ignores tool-calling instructions across every prompt-engineering attempt. Game-state injection is the validated pattern. The existing beat-selection path + new `resource_deltas` handler covers ritual without any new narrator-side tool plumbing.

## Architect Rulings on GM Draft (2026-04-15)

GM authored a heavy_metal content draft at `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` and surfaced six questions. Architect rulings recorded here for traceability:

1. **Effects location.** GM proved heavy_metal needs `mechanical_effects` slotted into existing `progression.yaml` affinity tiers, not a parallel `advancements.yaml`. **Ruling: ADR amended (§5).** Loader supports both locations; story 5 includes a per-genre audit pass.
2. **Extended `AdvancementEffect` variants.** GM proposed five new variants for non-combat affinities (Craft, Lore). **Ruling: `LoreRevealBonus` ships in v1** — single field, no plumbing change. **`AllyBeatDiscount`, `BetweenConfrontationsAction`, `AllyEdgeGrant`, `EdgeThresholdDelay` deferred to ADR-079** — each requires substantial new context plumbing. Heavy_metal Lore/Craft tiers 2-3 ship with documented `mechanical_effects: []  # TODO ADR-079` stubs.
3. **`while_strained` recovery condition.** **Ruling: added to `RecoveryTrigger::OnBeatSuccess`.** Precisely defined as `current <= max / 4`, matching the UI Cracked state. Honors Ruin's thematic core.
4. **`read_the_opponent` patience beat in combat ConfrontationDef.** **Ruling: endorsed as story 8 content.** Combat needs at least one in-fight Edge recovery option or attrition becomes a one-way ratchet. The criterion is "every combat ConfrontationDef must include at least one beat with `edge_delta < 0`"; `read_the_opponent` satisfies it for heavy_metal. Other genres can author their own equivalent. Not an architectural concern, not a precedent for content scope creep.
5. **Voice/Flesh/Ledger recovery cadence.** GM recommends no auto-refill — push currencies recover only through narrative events (silent meditation, bed-rest scenes, debt forgiveness). **Ruling: endorsed.** Engine-side this is `decay_per_turn: 0` and no `recovery_per_rest` auto-trigger — the existing `ResourcePool` schema supports this with no code change. Genre-truth call, GM authority.
6. **Combat `edge_delta` tuning.** First-pass numbers in §5 of the GM draft. **Ruling: not architectural.** The smoke playtest gate at end of story 4 is the tuning mechanism. Adjust YAML values based on what felt right or wrong; cheap to retune.

## References

- Implementation plan: `~/.claude/plans/ticklish-spinning-reef.md`
- Heavy_metal current rules: `sidequest-content/genre_packs/heavy_metal/rules.yaml`
- Phantom HP evidence: `sidequest-server/src/dispatch/beat.rs:362`
- False-positive wiring test: `sidequest-api/tests/beat_dispatch_wiring_story_28_5_tests.rs`
- `gold_delta` template pattern: `sidequest-server/src/dispatch/beat.rs:319-337`
- ResourcePool delta pipeline: `sidequest-server/src/dispatch/state_mutations.rs:328-407`
