# wry_whimsy Political Substrate — Premise & Belief-Flow

- **Status:** Draft (brainstorm output, pending user review)
- **Date:** 2026-06-02
- **Author:** GM (with party-mode panel: Niobe/Neo/Merovingian/Oracle/Kid/Morpheus)
- **Scope:** Genre-level system for `genre_packs/wry_whimsy/` (worlds: oz, planned alice, gulliver)
- **Related:** ADR-053 (Scenario / Belief / Gossip), ADR-020 (NPC Disposition), ADR-136 (Relationships Surface), ADR-128 (Trope Governor / Seed Deck), ADR-116 (Confrontation Requires an Other), the go-home spine in `wry_whimsy/worlds/oz/world.yaml`
- **Provenance:** 2026-06-02 oz solo playtest (the "authored-but-not-engaged" finding); Keith's design call that the Connecticut-Yankee dynamic is the **genre spine** across Oz/Alice/Gulliver (memory: project-oz-connecticut-yankee).

---

## 1. Motivation

Every planned `wry_whimsy` world is the same machine in a different costume: a **sensible outsider** is dropped into an **absurd society**, and the genre's signature fantasy is that the outsider can **reshape that society** — expose its humbug, refuse its premise, organize its oppressed, depose its petty tyrants. Keith guarantees his son James will "start a Munchkin revolution" the moment he reaches Oz.

The 2026-06-02 playtest showed the content is authored for this (the recently-freed Munchkins, the belief-powered humbug Wizard, General Jinjur already seeded, a "Refuse the Premise" confrontation beat) but **the engine cannot register it**. Liberation today is a *passive event* (a witch melts, people are "freed"); there is no faction-political state for player-driven change to move, and — per the playtest's headline bug — even the mechanics that do run are invisible to the player. A Munchkin revolution would currently be pure narration with zero mechanical backing: the exact SOUL "is the game lying?" failure.

This design supplies the missing substrate **once, at the genre level**, so all three worlds inherit it and each world authors only its own illusions.

## 2. Core Insight

The party panel converged hard on a single elegant idea:

> **Authority in an absurd society is a `Premise`: a social construct that holds power only as long as a population grants belief to it. Belief is a conserved currency the outsider *reroutes* — draining it from a humbug authority and pouring it into a defiant bloc — by committing *witnessed acts* that propagate through the belief/gossip engine that already exists.**

Consequences of this framing:
- **"Expose the Humbug" and "Refuse the Premise" are not special cases.** They are the same operation: `premise.belief -= witnessed_contradiction`. The green spectacles, the Queen's painted cards, the Big-Endian dogma are all instances of one `Premise` object.
- **It reuses ADR-053.** The propositional belief layer (`BeliefClaim`/`BeliefFact`, witnessed/overheard/told-by sources) and the `GossipEngine` propagation are already built. We add an *aggregation* layer on top, not a new propagation engine.
- **It ships three worlds from one mechanic.** Oz's Wizard, Wonderland's Queen, Lilliput's Endians are all authored as Premises + Blocs.

## 3. Altitude (locked)

**C-as-substrate + a thin new aggregation layer (a slice of B), surfaced visibly.**
- (C) Reuse the ADR-053 belief/gossip engine as the propagation substrate.
- (thin B) Add a small new `Premise` / `Authority` / `Bloc` aggregation model with explicit, legible state — *not* a grand-strategy simulation. wry_whimsy is "low gravity / low menace"; this is a handful of legible dials and a clear causal chain, not Crusader Kings.
- (visible) A player-facing Standing surface, because the playtest proved invisible mechanics don't count.

## 4. Data Model

Two new content-authored objects and one derived runtime state. Names are provisional.

### 4.1 `Premise` (content — authored in YAML)
The illusion that sustains an authority.
- `premise_id` (e.g. `the_wizards_humbug`)
- `authority`: the NPC/role whose power it grants (e.g. `oz_the_great_and_terrible`)
- `claim`: the proposition the population must believe (e.g. *"The Wizard is great, terrible, and the only one who decides"*). Expressed as an ADR-053 `BeliefClaim` so it lives in the existing belief layer.
- `belief_reserve`: starting aggregate belief `0..100` (the authority's power).
- `propped_by`: list of `bloc_id`s whose granted belief sustains it.
- `drained_by`: list of **witnessed-act archetypes** that contradict the claim (e.g. `see_behind_the_curtain`, `name_the_humbug_publicly`, `do_what_the_authority_forbids_without_consequence`). Each carries a `belief_delta` and a `cost` (turns/risk/exposure).
- `collapse`: what happens at `belief_reserve <= threshold` (authority deposed / flees / is revealed) and the power-vacuum hook it leaves.

### 4.2 `Bloc` (content — authored in YAML)
A population the outsider can move.
- `bloc_id` (e.g. `munchkins`, `winkies`, `the_queens_cards`, `big_endians`)
- `defiance`: aggregate `0..100`, starting low.
- `grants_belief_to`: the Premise(s) it currently props.
- `awakening_acts`: witnessed-act archetypes that raise defiance (e.g. `show_them_an_authority_can_be_defied`, `organize_a_first_small_refusal`).
- `tipping_threshold` + `tipped_outcome`: at high defiance the bloc *acts on its own* (the Munchkin revolt, the cards scatter), producing a world-state change and NPC realignment.
- `flavor`: per-world voice for how this bloc awakens.

### 4.3 Runtime: `PremiseState` / `BlocState` (engine — session snapshot)
Live `belief_reserve` / `defiance` values, a ledger of witnessed acts applied, and provenance for each delta (which act, which witness, which turn) — for OTEL and the Standing panel.

### 4.4 The conservation rule (deliberately soft)
Belief is **mostly** conserved: a witnessed contradiction that drains a Premise routes a portion to the witnessing bloc's defiance (the rest dissipates). This is a tuning knob, **not** a hard physics law — Neo's "fixed pool" idea is a v2 spike, not a v1 invariant (see §11). v1 uses independent `belief_delta` / `defiance_delta` per act with a soft coupling, to avoid a self-balancing straitjacket in a whimsy genre.

## 5. Belief-Flow Mechanics — the causal chain

The Merovingian's constraint is load-bearing: **a revolution the player merely declares is hollow.** Each link must be *earned*.

```
player commits act  →  a witness perceives it  →  ADR-053 belief layer records a
contradicting BeliefFact (source: Witnessed)  →  GossipEngine propagates it
(source: Overheard/ToldBy)  →  aggregate belief in the Premise erodes  →
coupled defiance in the propping bloc rises  →  at thresholds: authority collapses /
bloc tips into autonomous action  →  world-state flips, NPCs realign, the receipt is kept
```

- **Acts come from the narrator/intent layer**, not a menu: the player *does* something (clicks the spectacles off, calls the Wizard a humbug to his face, helps a Munchkin defy a rule and survive). The intent router (ADR-113) / mechanical-engagement pipeline (ADR-123) classifies it against the Premise's `drained_by` / the bloc's `awakening_acts`.
- **"Refuse the Premise" is promoted** from an oz-local confrontation beat to a **genre-level victory move** against any belief-powered authority — it applies a `belief_delta` to the named Premise.
- **Witness + propagation are real costs**: an act with no witness moves nothing; a witnessed act spreads at the GossipEngine's rate. Exposing the humbug in an empty room does nothing — the Kid's spectacles-toggle is powerful precisely because it can be done *publicly*.

## 6. Consequences — "the world keeps the receipt"

The Oracle's point is the emotional spine, not a nice-to-have. The political layer must couple back to the genre's go-home premise:
- Collapsing an authority leaves a **power vacuum** the world reacts to (Jinjur rises; Glinda watches from the South; a deposed humbug becomes a loose thread).
- Reshaping the society **changes the cost of leaving**: the more the outsider remakes the place, the more it becomes *theirs* ("the dream would so love to keep you" — already in `oz/world.yaml`). Mechanically, major reshaping acts may close the easy way home and open a harder, earned one.
- Tropes/seeds (ADR-128) carry the long game: e.g. oz's latent `lost_princess` becomes reachable *through* the political upheaval the player creates.

## 7. Player-Facing Surfacing (non-negotiable)

The playtest's headline bug is that live mechanics were invisible. This design **must not** repeat it.
- **Standing panel** (new right-sidebar tab, sibling of Relationships): each authority shows a dwindling `belief_reserve` bar; each bloc shows a rising `defiance` bar. On a successful witnessed act, the belief **visibly flows** from authority to bloc with the witness named.
- **The spectacles toggle** (per-world "see-through-the-illusion" control): clicking the green spectacles off re-renders the Emerald City as plain white marble. Generalizes per world (Wonderland → a pack of cards; Laputa → men shouting at nothing). This single interaction teaches the whole genre and directly serves Sebastien/Jade legibility.
- All belief/defiance changes emit OTEL (see §10) so the GM panel is the lie-detector for the political layer too.

## 8. Content-Authoring Model (Premise-as-content)

Morpheus's requirement: the engine ships the **physics of belief once**; each world **declares its illusions** in YAML, no engine code. Jade must be able to add a Wonderland humbug without touching the server.
- New genre-level schema: `wry_whimsy/premises.yaml` (or per-world `worlds/<w>/premises.yaml`) carrying `Premise` + `Bloc` definitions, validated by a loader (ADR-120/121 mandatory-file + layered-merge contract).
- Witnessed-act **archetypes** are genre-level vocabulary (e.g. `expose_the_humbug`, `refuse_the_premise`, `show_defiance_survives`); worlds bind them to their specific authorities/blocs.
- Authoring a new world's politics = write its Premises, Blocs, and which acts drain/awaken them. The engine, intent classification, propagation, surfacing, and OTEL are all genre-level.

## 9. Integration with Existing Systems

- **ADR-053 belief/gossip** — the propagation substrate. `Premise.claim` is a `BeliefClaim`; draining acts inject `BeliefFact`s with `Witnessed` source; the `GossipEngine` spreads them. **The new code is aggregation** (authority power = f(population belief in claim)) + bloc defiance, not new propagation.
- **Confrontation engine** — "Refuse the Premise" / "Expose the Humbug" promoted to genre-level victory moves that apply belief deltas; ties to the existing wry_whimsy confrontation types. (Also fixes part of the playtest confrontation finding by giving social confrontations a *stake*.)
- **Relationships (ADR-136)** — Standing panel is its sibling; individual NPC disposition still tracked per-NPC, blocs are the aggregate layer above.
- **Trope governor / seeds (ADR-128)** — political upheaval is the trigger surface for latent seeds (e.g. `lost_princess`).
- **Intent router (ADR-113) / mechanical-engagement (ADR-123)** — classifies player acts against Premise `drained_by` / Bloc `awakening_acts`.

## 10. Observability (OTEL — the lie-detector)

Per the project OTEL principle, every belief/defiance decision emits a watcher event:
- `premise.belief_drained` (premise_id, act, witness, delta, new_reserve, source)
- `bloc.defiance_raised` (bloc_id, act, delta, new_defiance)
- `premise.collapsed` / `bloc.tipped` (with the world-state change + vacuum hook)
- gossip-propagation spans reuse ADR-053's existing emits.
The GM panel must show the political layer engaging, so we can tell a real revolution from narrated improvisation.

## 11. Scope & Phasing

**v1 (this spec):**
- `Premise` + `Bloc` content schema + loader/validator.
- Runtime `PremiseState`/`BlocState` on the session snapshot.
- Aggregation over ADR-053 belief; witnessed-act classification; soft belief→defiance coupling.
- "Refuse the Premise" / "Expose the Humbug" as genre victory moves.
- Standing panel + one spectacles-toggle.
- OTEL emits.
- **Oz as the single reference implementation** (the Wizard's humbug + Munchkin/Winkie blocs). Alice/Gulliver are authored later against the same engine.

**Deferred / v2 (explicit non-goals for v1):**
- Hard belief-conservation law (Neo's fixed-pool) — spike first; risk of a whimsy-killing straitjacket.
- Multi-authority interaction / inter-bloc politics beyond prop/defiance.
- The "Connecticut Yankee curse" cost-to-leave coupling — design it after the core loop proves out.
- Industrialization/economy as a distinct axis (belief/defiance only in v1).

## 12. Testing

- Unit: belief aggregation, act classification, threshold collapse/tip, soft coupling math.
- Integration (wiring test, per project rule): a witnessed act in a live oz session drains the Premise, propagates via GossipEngine, raises bloc defiance, and the Standing panel + OTEL reflect it end-to-end.
- Authoring test: a second Premise (a stub Wonderland humbug fixture) loads and runs with **zero engine changes** — proves the content boundary.

## 13. Open Questions / Spikes

1. **Does ADR-053 `BeliefState` cleanly support an aggregate "population belief in a claim", or do we need a sibling roll-up?** (Neo's conservation law lives or dies here.) Spike with `scenario-designer` before locking the aggregation API.
2. Where does the schema live — genre `premises.yaml` vs per-world? (Lean per-world files merged under a genre vocabulary, per ADR-121.)
3. Does the spectacles-toggle need a generalized "illusion overlay" render contract, or is it per-world UI? (UX spike.)
4. How do witnessed-act archetypes map onto the intent router's existing dispatch vocabulary without bloating it?

## 14. Non-Goals (YAGNI)

This is a **legible political layer for a whimsy genre**, not a strategy sim. No economy, no troop movement, no tech tree, no map-painting. A handful of bars, a clear causal chain, a visible flow, and a world that keeps the receipt.
