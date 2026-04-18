# Evropi Starting Kits — Day-One Class Differentiation Design

**Status:** Draft
**Date:** 2026-04-18
**Deciders:** Keith Avery, Major Houlihan (Architect)
**Related:** ADR-078 (Edge/Composure/Advancement/Rituals), future ADR-081 (Advancement Effect Variant Expansion v1), Epic 39

## Context

The Evropi playgroup session this coming Sunday will see several characters for the first time. The existing heavy_metal combat ConfrontationDef gives every character the same five beats — `strike`, `brace`, `committed_blow`, `read_the_opponent`, `break_contact` — with no class-specific differentiation. Every character feels mechanically identical at turn one: "attack / block / defend / shield bash." This defeats the genre-truth design of heavy_metal (classes sorted by what pressure their training accustomed them to) and disserves the playgroup, particularly Sebastien, who plays mechanics-first and wants visible distinctions between characters on the GM panel.

The earlier six-character skill-tree drafts (`sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/`) targeted progression through affinity tiers and milestones. In brainstorming, Keith observed that the playgroup will level rarely if at all — making tier-gated differentiation largely aspirational. The urgent problem is **day-one differentiation**, not progression.

## Decision

Each character receives a **character-unique starting kit** — a curated set of `AdvancementEffect` entries granted at character creation — that makes them mechanically distinct from turn one. This is pure content work, reusing the Margaret-ratified `AdvancementEffect` enum from ADR-078. Aside from one micro-ADR covering two new variants, no engine architecture is required.

The existing skill-tree `trunk:` / `paths:` / `capstones:` content stays in place as future progression, but the `starting_kit:` block on each character file is the load-bearing piece for Sunday's session.

## Scope

### In scope

- `starting_kit:` schema addition to `worlds/evropi/character-progression/{slug}.yaml`
- `character_resources:` schema addition for character-scoped ResourcePools (for reniksnad)
- Kit content for five characters: Rux, Prot'Thokk, Hant, Pumblestone, Th`rook
- Ludzo test-character kit inheritance (`inherits: rux`)
- Th`rook full character draft (new — no existing save, no prior progression YAML)
- Pę ResourcePool definition
- Micro-ADR-081 covering `AllyEdgeIntercept` and `ConditionalEffectGating`
- `sunday-progression.md` amendment adding a Th`rook section and reniksnad-dependency narrator guidance
- Cross-reference updates: edge-advancement-content.md, ADR-078 deferral language, character YAMLs, character-progression README

### Out of scope

- T2 and T3 tier content changes (the existing draft content is preserved; no new design)
- Additional `AdvancementEffect` variants beyond the two in ADR-081 (named and deferred to a future ADR)
- Other worlds in heavy_metal (long_foundry)
- Other genre packs
- Engine wiring work (sits in Epic 39 stories 5 and 7)
- Character re-portraiture or audio updates

## Design

### Data model — per-character YAML extension

The existing `character-progression/{slug}.yaml` schema (drafted earlier in the sidecar README) gains two new top-level blocks: `starting_kit:` and optional `character_resources:`.

```yaml
character:
  save_id: string
  name: string
  race: string
  class: string
  affinity_emphasis: {...}

# NEW — granted at character creation, hydrates CreatureCore.acquired_advancements
starting_kit:
  label: "Human-readable kit identity"
  flavor: "One-sentence kit identity summary"
  inherits: optional_string        # for test characters referencing another kit
  grants:
    - id: snake_case_id
      label: "Grant name"
      narration_hint: "Prose — loaded as high-priority KnownFact"
      effects:
        - { type: advancement_effect_type, ... }

# NEW — character-scoped ResourcePools (hydrated alongside genre-level Voice/Flesh/Ledger)
character_resources:
  - name: string
    label: string
    min: int
    max: int
    starting: int
    voluntary: bool
    decay_per_scene: optional_int
    decay_per_turn: optional_int
    refill_trigger: string
    thresholds: [...]

trunk: {...}                       # unchanged
paths: [...]                       # unchanged
capstones: {...}                   # unchanged
```

### Data model — test-character inheritance

Ludzo is Keith's test/QA character, not a playgroup member. Ludzo's YAML is authored with full trunk/paths/capstones for flavor continuity, but his starting kit inherits from Rux rather than defining its own:

```yaml
# worlds/evropi/character-progression/ludzo.yaml
character:
  save_id: ludzo
  ...

starting_kit:
  inherits: rux
  note: "Test character — mirrors Rux's kit for QA and regression playtests. No unique day-one grants."

trunk: {...}                       # Ludzo keeps his own flavor content
paths: [...]
capstones: {...}
```

At load time, `inherits: rux` resolves by reading rux.yaml's `starting_kit.grants` and hydrating Ludzo's CreatureCore with the same entries. Flavor stays Ludzo's; mechanics are Rux's.

### Engine consumer

Epic 39 story 5 adds a `milestone-grant` loader that hydrates `CreatureCore.acquired_advancements` from YAML. This design extends that loader to also hydrate:

1. `starting_kit.grants` at character creation (trigger: `on_character_created`)
2. `character_resources` as additional ResourcePools on the character (existing ResourcePool schema; no new type)

Neither requires a new subsystem. The chargen handler gets a one-line call to `hydrate_starting_kit(character, progression_yaml)` and a one-line call to `hydrate_character_resources(character, progression_yaml)`.

### Character kits

Each kit is 3 `AdvancementEffect` grants plus a kit label and flavor line. Grants are drawn from the character's existing Trunk + Path Tier 1 effects in the previously drafted YAMLs — no new content authoring beyond pulling the right three.

#### Rux — *Servant of the Old Line*

> The Tismenni taught their servants three kinds of attention: what is written, where to strike, and how not to be seen.

1. **Kept the Master's Books** — `lore_reveal_bonus { scope: written_object }` — 1/scene reveal about any sigiled/written object
2. **Strike from the Low Line** — `leverage_bonus { beat_id: strike, target_edge_delta_mod: -1 }` — precision strikes scale on DEX not STR
3. **Already Dismissed** — `edge_recovery { trigger: { type: on_beat_success, while_strained: true }, amount: 2 }` — eye-slides-past effect mechanised as composure recovery under pressure

All day-1 enum.

#### Prot'Thokk — *The One Who Stands Between*

> Three postures: the wall, the broken chain, the body that will not let the horse fall.

1. **Stand in Front** — `edge_max_bonus { amount: 1 }` + `beat_discount { beat_id: brace, edge_delta_mod: -1 }` (compound grant)
2. **Broke the Chains** — `beat_discount { beat_id: refuse, edge_delta_mod: -1 }` — institutional-refusal costs less composure
3. **Lil' Sebastian Stands** — `ally_edge_intercept { ally_whitelist: ["Cheeney", "Lil'Sebastian"], max_redirect: 3 }` — **new variant, ADR-081**

Two day-1, one ADR-081.

#### Hant — *Composer on the Surface*

> Surface strangers, pheromone-courts, the current he followed up out of the Deep Hollows. All three are crafts.

1. **Drowse** — `leverage_bonus { beat_id: argue, target_edge_delta_mod: -2 }` — social pheromone destabilizes an opponent mid-conversation
2. **Pheromone-Court Etiquette** — `lore_reveal_bonus { scope: emotional_state }` — reads NPC emotion concretely
3. **Surface Stranger** — `beat_discount { beat_id: argue, edge_delta_mod: -1 }` — first social roll with anyone who has never seen an antman lands cleaner

All day-1 enum. Hant feels *present* at turn one despite his heavier T2/T3 dependencies on ally-targeted variants (deferred to ADR-082+).

#### Pumblestone Sweedlewit — *The Sage Who Misremembers*

> Three ways to know: by reading, by owing, by being unsure. All three produce answers.

1. **Read What Others Can't** — `lore_reveal_bonus { scope: older_script }` — all older-script texts resolve without check
2. **Owed Future** — `beat_discount { beat_id: invoke, resource_mod: { voice: 1 } }` — working deferred-cost style; invocations cost less Voice
3. **One Map Is Right** — `lore_reveal_bonus { scope: conflicting_intel }` — when multiple sources disagree, he picks the true one

All day-1 enum.

#### Th`rook (placeholder — awaiting Sebastien's canonical name) — *Sung to the Rock Beneath the Water*

> A pact older than the kingdom. It answers the knotsong. It does not care that he is dying.

**Race/class:** Pakook`rook Warlock. Edge_max 4 base. Pakook-literate (knotsongs), conversational Jabber.

**Backstory skeleton:**
> Born in Pę (the Zkędzała slave-city), force-fed reniksnad from childhood to keep the labor compliant. Somewhere in his teens, while working alone in the reed-beds, he heard something in the deep swamp sing back to his knotsong — and negotiated. The pact did not free him from the reniksnad. It freed him from the Zkęd. The patron — a thing that lives where the swamp meets rock — does not know or care about withdrawal. It cares about the knotsong being sung, and about the water being deep enough. Th`rook has been walking north, because the patron named a place, and because the Wazdia still controls the reniksnad supply south of the Zbóźny foothills and he will not go south again.

**Hooks:** `reach_a_buried_place` (shared with four other party members), `addicted_to_controlled_supply` (unique).

**Starting kit:**
1. **Knotsung Name** — `beat_discount { beat_id: invoke, resource_mod: { voice: 1 } }` — invocation through knotsong costs less Voice
2. **Creditor's Mark** — `lore_reveal_bonus { scope: pact_creditor_sign }` — recognizes other warlocks' pact-signs on sight
3. **The Dose Helps** — `conditional_effect_gating` wrapping `beat_discount { beat_id: commit_cost, resource_mod: { flesh: 1 } }` when reniksnad>5, OR `beat_penalty { beat_id: commit_cost, resource_mod: { flesh: -1 } }` when reniksnad≤5 — **new variant, ADR-081**

Two day-1, one ADR-081.

**Character resource — reniksnad:**
```yaml
character_resources:
  - name: reniksnad
    label: "Reniksnad"
    min: 0
    max: 10
    starting: 7
    voluntary: false
    decay_per_scene: 1
    refill_trigger: "narrator-authored dose event (Wazdia-controlled supply)"
    thresholds:
      - at: 5
        event_id: reniksnad_first_tremor
        narrator_hint: "His hand shakes slightly when he reaches for water. A Wazdia informer would note it."
        direction: crossing_down
      - at: 3
        event_id: reniksnad_withdrawal
        narrator_hint: "Withdrawal has begun. His voice thins; knotsongs fail on the high notes. Voice-spends cost 1 more per invocation while he is here."
        direction: crossing_down
      - at: 0
        event_id: reniksnad_death_clock
        narrator_hint: "The clock has started. He will die within one in-fiction week without another dose. Narrator: this is not dramatic; it is medical."
        direction: crossing_down
```

### ADR-081 scope (micro-ADR, separate document)

Two new `AdvancementEffect` enum variants, scoped tightly:

1. **`AllyEdgeIntercept`** — self-sacrifice: redirect `target_edge_delta` from a designated ally to the actor. Required by Prot'Thokk's *Lil' Sebastian Stands* (the ability that defines his character identity). Fields: `ally_whitelist: Vec<CreatureRef>`, `max_redirect: u32`. Clamps actor's Edge to ≥1 to prevent self-breaks on the redirect.

2. **`ConditionalEffectGating`** — wraps an existing effect in a condition check against a resource pool or character state. Required by Th`rook's *The Dose Helps* (reniksnad>5 vs reniksnad≤5). Fields: `condition: ConditionExpr`, `when_true: AdvancementEffect`, `when_false: Option<AdvancementEffect>`. `ConditionExpr` initially supports only ResourcePool threshold comparisons; richer grammar deferred.

All other T2/T3 stubs across the five character drafts remain `effects: []  # TODO ADR-082+` with named variants and preserved narration_hints. A future ADR addresses them after play reveals which are load-bearing.

### Sunday playtest vs post-Epic-39 deployment

- **This Sunday (pre-Epic-39):** The `sunday-progression.md` sheet already carries four of the five characters under GM fiat. This design requires appending a Th`rook section (backstory + kit prose + reniksnad guidance) to that sheet. The narrator honors all grants and reniksnad-threshold effects in prose. The GM (Keith) tracks reniksnad manually.
- **Post-Epic-39 story 5:** The `starting_kit:` and `character_resources:` blocks in the YAML files are lifted verbatim into runtime. ADR-081 lands. Sebastien gets dashboard visibility of all four resource bars and the conditional-gating flip. Kit grants appear as real AdvancementEffects in the GM panel's per-character ledger.

## Consequences

**Positive**

- Five characters mechanically distinct at turn one, using content-only changes and a 2-variant ADR — no new subsystem
- Sebastien gets the push-currency dashboard he wants, and a conditional-gating lever unique to his character
- Existing skill-tree drafts are not wasted; they become authored future-content, honored if/when leveling occurs
- The two-ADR scope (ADR-078 baseline, ADR-081 expansion) keeps the enum design ratifiable per variant rather than as a sprawling grab-bag
- Sunday session works under GM fiat with the progression sheet already written

**Negative / trade-offs**

- One additional variant (`ConditionalEffectGating`) beyond the original ADR-081 plan surfaced late; architectural scope is disciplined but did drift from "one variant" to "two" under playtest pressure
- Character-scoped ResourcePools are a genuine schema extension; content-side this is trivial, but it introduces a second hydration path distinct from genre-level resources
- Hant's T2/T3 remain heavily ADR-082+ dependent; his long-game mechanical identity is thinner than the other four's if play ever does progress to T2
- Th`rook's reniksnad dependency is a permanent session pressure point; if Keith decides the ongoing clock is too much mid-session, there is no soft-off switch short of narrator fiat to refill

**Neutral**

- Ludzo's test-inheritance pattern is novel in this codebase; may need documenting if other worlds adopt similar sandbox/QA patterns

## Open items

1. Th`rook's canonical name — Keith is checking with Sebastien whether a name already existed in prior conversation; placeholder **Th`rook** stands until provided. Fallback: spawn `/conlang` to generate a Pakook-language name from the existing corpus.
2. Kit grants for Prot'Thokk use a compound grant for *Stand in Front* (two effects under one grant id); the load pattern needs to confirm the schema allows it. If not, split into two grants.
3. The `narrator_hint` for *The Dose Helps* needs a tested phrasing for the narrator LLM under ADR-078's KnownFact injection pattern; currently drafted but unvalidated with a narrator roundtrip.
4. Party hook overlap: Th`rook shares `reach_a_buried_place` with four others. Whether his buried place is the *same* buried place is a campaign-arc question Keith owns, not a design-doc question.

## References

- ADR-078 — Edge/Composure/Advancement/Rituals (baseline `AdvancementEffect` enum)
- `sidequest-content/genre_packs/heavy_metal/_drafts/edge-advancement-content.md` — baseline content draft
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/sunday-progression.md` — Sunday-usable narrator prose
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/_drafts/character-progression/*.yaml` — per-character progression drafts (five files)
- `sidequest-content/genre_packs/heavy_metal/worlds/evropi/lore.yaml` — Pakook`rook lore canon
- Epic 39 — Runtime wiring for Edge/Composure/Advancement (stories 5 and 7 are the relevant landing zones)
