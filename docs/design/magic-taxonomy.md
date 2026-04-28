# Magic Taxonomy — Working Draft

**Status:** Draft, derived from Keith's napkin sketch (2026-04-27).
**Purpose:** A unified shape for declaring magic systems across all genre packs.
**Relation to existing docs:** Supersedes ad-hoc `magic_level: none/low/medium/high` flag and per-pack `magic_design.md` files. Those files become the *prose register* layer; the YAML below becomes the *queryable structure* layer. See `docs/magic-system-design-guide.md` for the existing prose-only guidance this draft formalizes.

## The Two-Axis Napkin

### Source — where the power comes from

Every genre's magic-shaped slot is filled by one or more of these:

| Source | Description | Examples |
|---|---|---|
| **Innate** | The character IS the source — wild, untrained, reflexive. Fires under stress without practiced control. Identity-cost. Severance-impossible. | Carrie, Hulk untrained, young Anakin, Firefly River, born mutants without a tradition, untrained Force-sensitives |
| **Learned** | Trained/practiced/studied discipline. The practice itself is the source. May require an Innate prerequisite gate (must be Force-sensitive to begin Jedi training; must be a born bender to begin discipline; must have undergone witcher mutation to channel signs) — but once trained, the discipline is the active source. | wizards, alchemists, ritualists, trained Jedi, Avatar benders in discipline, witcher signs, Bene Gesserit, Pact-Priests' liturgy, gunsmith craft |
| **Item-based** | Power lives in an object the character wields, carries, drives, reads, builds, or invokes. | Elric/Stormbringer, named guns, named vehicles, cursed letters, MacGyver's gadgets, ripperdoc chrome, the Lassiter |
| **Divine** | Granted by a higher power, mediated by an apparatus or relationship of worship. | Greek/Catholic patterns, divine champions, the Pale Fire cult, the Catholic apparatus |
| **Bargained-for** | Pacted, owed — contract with a sentient patron. | Faustian, crossroads deals, demonic compacts, fae bargains |

**Four Sources + Bargained-for = 5 total.** The earlier draft had 9; collapses landed us here:

- ~~Pre-Ordained~~ — narrative tag, not Source *(2026-04-27)*
- ~~McCoy / Invented~~ — delivery mechanism for `item_based` *(2026-04-28)*
- ~~Acquired~~ — collapses into **Innate** *(2026-04-28)*. Born with it vs. acquired-via-event is narrative texture (a `flavor:` field), not framework distinction. Both fire the same: character is source, no external mediator, identity-cost, severance-impossible.
- ~~Innate (automatic)~~ — kept as **Innate** (the wild/untrained/reflexive register).
- ~~Innate (developed)~~ — collapses into **Learned** with optional prerequisite gate *(2026-04-28)*. The "developed" register was Learned-with-baseline-required, not a peer Source. Once you're trained, the *discipline* is what bills the ledger and runs the confrontations — the prerequisite is just chargen access control.

### The Innate vs. Learned cut

Both are "no external mediator," both have the character as locus. The cut between them is **whether practiced control exists**:

- **Innate** fires reflexively. Costs land on identity and body. The character cannot reliably aim it. Plot engine: identity arcs, growing-into-power, survival of self.
- **Learned** fires deliberately, through practice. Costs land on time, discipline, components. The character can aim it, hold it, refuse it. Plot engine: mastery arcs, school politics, the long apprenticeship.

A character may move from Innate to Learned by *receiving training* — the wild Innate becomes a Learned discipline. Cross-plugin advancement (a `pact_tier` output with `target_plugin: learned_v1`) is exactly the shape of this transition. Untrained Rey → trained Rey is one arc, not two characters.

### Cross-Source compounds remain

Multi-Source compounds still exist where Sources are *genuinely* separate:

- **Witcher** = Learned (sign-training, with mutation-prerequisite) + Item-based (silver sword as item_legacy)
- **Jedi** = Learned (Jedi training, with Force-sensitivity prerequisite) + Item-based (lightsaber as item_legacy)
- **Heavy_metal Cleric** = Divine (apparatus) + Learned (liturgical rite-knowledge) + sometimes Bargained-for (the saint's personal compact)
- **Spaghetti Western Gunslinger** = Item-based (named gun, mccoy-built or found) + sometimes Learned (gunsmith craft)

Each Source = one plugin. Multi-Source character = multiple plugins active simultaneously. The character sheet is the union of plugin instantiations.

### Plugin coverage check (revised)

| Source | Plugin | Status |
|---|---|---|
| Innate | innate_v1 | ✅ drafted |
| Learned | learned_v1 | ✅ drafted |
| Item-based | item_legacy_v1 (mccoy folded as mechanism) | ✅ drafted |
| Divine | divine_v1 | ✅ drafted |
| Bargained-for | bargained_for_v1 | ✅ drafted |

Five plugins cover the napkin. Plus heavy_metal-specific multi-plugin layer:
- obligation_scales_v1 (heavy_metal's five-scale obligation ledger) — ✅ drafted

> **Pre-Ordained / Chosen One is NOT a Source** *(decision 2026-04-27)*. It's a *narrative role* — a tag that rides on top of one of the above Sources. Anakin is Innate-developed + chosen-one. Aragorn is Innate-inherited + foretold. Buffy is Innate-automatic + called. The chosen-one quality is captured at the lore/scenario layer, not the magic Source layer.

> **McCoy / Invented is NOT a Source** *(decision 2026-04-28)*. It's a *delivery mechanism* for item_based. When the character builds the magic-shaped thing themselves (Doc Brown's flux capacitor, Q's gadgets, MacGyver's improv, Tony Stark's suit, the ripperdoc's chrome, the gunsmith's trick rounds), the result is an *item* — and the item enters the item_based plugin's lifecycle. Building is acquisition; what's built is an item with personality, history, and bond. McCoy is found alongside Discovery, Relational, Faction, Condition, and Place as ways to acquire an item.

**Universal-ish slots:** Item-based and McCoy are present in nearly every genre, even those that claim no magic. The named gun, the named vehicle, the inventor's gadget — these fill the magic-shaped slot in genres that refuse the word.

### Manifestation — how it expresses

Splits into two sub-axes (Mode × Domain):

**Mode** — *how the power is triggered*
- Reflexive (involuntary, fires under stress)
- Invoked (deliberate, on demand)
- Ritual (prepared, time-gated)
- Item-channeled (requires the object)

**Domain** — *what the power touches*
- Elemental
- Physical
- Psychic
- Spatial (telekinesis, teleport, portal)
- Temporal (precog, chronal)
- Necromantic
- Illusory
- Divinatory
- Transmutative
- Alchemical (humors, properties)

A genre's magic system declares which Mode × Domain cells are *allowable*; a world picks which it actually uses.

## The Other Axes (added to the napkin)

### Cost
What does using it take from the user?

- **Pool / Mana** — renewable (classical D&D)
- **Components** — herbs, blood, gold, sacrifice
- **Time** — ritual length, preparation
- **Vitality / Lifespan** — ages you, shortens life
- **Sanity / Mind** — Lovecraftian, Dresden third eye
- **Soul / Debt** — Faustian, Stormbringer
- **Backlash** — random risky cost (Warhammer, Wild Magic)
- **Karma / Stain** — moral weight that compounds (the dark side, blood mage)
- **Attention** — the magic itself notices and responds (Mage Paradox, the Wyrd)

### Limits — the genre's named impossibilities
A *checklist the genre fills out*, not a peer list:

- Resurrection (no / costly / forbidden / possible-but-wrong)
- True creation ex nihilo (almost always no)
- Mind compulsion (vs. influence; with-cost or forbidden)
- Time (precog only? reversal? loops?)
- Range (line-of-sight / sympathetic link / unbounded)
- Self-targeting (heal yourself? buff yourself?)
- Permanence (snaps back / decays / sticks)

The line-in-the-sand limit is where the drama lives. *"Magic cannot bring back the dead"* is the entire emotional engine of Witcher.

### World-Knowledge — *does the world know magic exists?*

Separate from whether magic *exists* (Sources non-empty) and from how it's *socially treated* (Visibility below). This is the **epistemological** axis — the world's collective awareness of magic as a real category. **This is where the "No Magic" claim properly lives.**

- **Acknowledged / canonical** — magic is part of common knowledge; the cosmology states it (heavy_metal, elemental_harmony)
- **Folkloric** — magic is in stories, songs, peasant beliefs; educated folk dismiss it (spaghetti_western, road_warrior, low-gothic victoria)
- **Mythic / lapsed** — was canonical, now "ancient religion most have forgotten" (post-Order-66 Star Wars, low_fantasy, caverns_and_claudes commoners)
- **Esoteric** — only initiates know; the public doesn't (pulp_noir, Dresden Files, Mage)
- **Classified / suppressed** — actively hidden by power (Firefly world's River, X-Files, Akira)
- **Denied / unknown** — not even a category; the world doesn't have the concept (hard sci-fi, neon_dystopia at low Chrome, the Expanse)

The crucial split this exposes:
- **Firefly's "No Magic" = Classified.** Psychic powers exist (River); the world doesn't know.
- **Neon_dystopia's "No Magic" = Denied.** The world doesn't even have the concept.
- **Spaghetti_western's "No Magic" = Folkloric-dismissed.** The world has the concept, treats it as superstition.
- **Caverns_and_claudes' "No Magic" (rules.yaml) ≠ low World-Knowledge.** Magic items exist and the world knows; the field is mislabeled, the actual claim is "no caster classes."

These are four completely different claims that current `magic_level: none` flattens.

### Visibility / Cultural Status — *given that it's known, how is it treated?*

A subordinate axis to World-Knowledge — only meaningful where World-Knowledge isn't `denied`. Where does known-magic sit in society?

- **Celebrated** — revered, central to civic life (High Republic Jedi, elemental_harmony temples)
- **Regulated** — licensed, guild-controlled (Mistborn nobility, Harry Potter Ministry)
- **Feared** — real, dangerous, avoided (witcher mutants, mutant_wasteland)
- **Persecuted** — heresy, illegal (Imperial-era Jedi, witch-burning)
- **Ubiquitous** — everyone has a touch, mundane (Allomancy commoners)
- **Dismissed** — known but treated as charlatanry (low-gothic Victoria mesmerists)

### Reliability
Does it work when you cast it?

- **Deterministic** — you cast, it works
- **Skill-checked** — roll-based, can fizzle
- **Wild** — random surge possible
- **Negotiated** — the magic has agency; you ask, it answers
- **Faith-gated** — works only when belief holds
- **Emotion-gated** — calm vs. passion changes precision/power

### Counter
How is magic fought?

- Saves / resistance, Counterspell, Anti-magic zones, Specific banes (cold iron, salt, true names), Faith / opposing Source, Disbelief, None (irresistible)

## The Two-Layer Architecture

Magic lives at **both** the genre and world layer, mirroring the existing genre/world split (ADR-003, ADR-004):

- **Genre layer** declares the *space of allowable tuples* — which Sources, Costs, Domains, Limits this genre's identity permits.
- **World layer** *commits* to a specific tuple from that allowed space.

Same genre, multiple worlds, different tuples:
- **space_opera** allows Innate-Psychic. *Star Wars* world commits to Force tuple. *Firefly* world commits to River-only narrative tuple. *Expanse* world commits to nothing (psychic disabled). All valid.
- **victoria** allows dialed-occult. *Brontë* world dials low. *Carmilla* world dials high. *Stoker* world dials very high.

The napkin's "intensity" knob is what makes worlds within a genre feel different without splintering the genre.

## Cross-Genre Tuples

### caverns_and_claudes
- Source: Item-based (load-bearing, "Magic is found, not learned")
- Cost: Components + Backlash
- Limits: No resurrection, no creation, no high-tier transmutation
- Visibility: Mythic / lapsed
- Reliability: Deterministic + Backlash
- Manifestation: Item-channeled; Domain = ad hoc per item

### elemental_harmony
- Source: Innate-developed (bloodlines + training); Learned for ceiling
- Cost: Pool (momentum/harmony) + Vitality at extremes
- Limits: No resurrection, no cross-element, no bending without breath/movement
- Visibility: Public + celebrated/regulated
- Reliability: Skill-checked
- Manifestation: Reflexive + Invoked + Ritual; Domain = Elemental + Psychic + Spatial

### mutant_wasteland — *currently mislabeled `magic_level: none`*
- Source: Acquired (radiation/exposure); Innate-automatic for born-mutants
- Cost: Backlash + Karma/Stain (visible side-effect)
- Limits: No resurrection, no precision, no choice in what mutation you got
- Visibility: Public + feared
- Reliability: Skill-checked, wild on failure
- Manifestation: Reflexive; Domain = Physical + occasional Psychic

The mutation system already has a "Use Mutation" combat action with risk and narrator cost-instructions. It IS magic mechanically. The schema lets the pack admit it.

### space_opera (genre allowance space)
- Allowed Sources: Innate-developed (Force, with prophecy tag), Acquired (experimentation), McCoy (engineering)
- Allowed Costs: Karma, Sanity, Vitality
- Hard limits: No resurrection. No tech replacement. No FTL communication except via specific tech.
- Manifestation: any Mode; Domain = Psychic + Spatial + Divinatory + Physical (no Elemental, no Necromantic-resurrection)

#### space_opera worlds
- *Star Wars*: full Force tuple — Innate-developed-Psychic with Karma cost, era-dialed visibility, emotion-gated reliability; chosen-one narrative tag for Anakin/Luke/Rey
- *Firefly*: River tuple — Acquired-Psychic narrative-only, Sanity cost, Hidden visibility, Wild reliability
- *Expanse*: empty psychic; Item (the Lassiter, Mal's antique pistol) and McCoy (engineering) only

The current `magic_design.md` ("psionics is narrative condition, never player option") becomes the **Firefly world tuple**, not a genre-level absolute. **Update needed: lift the River Tam Rule out of `magic_design.md` and into `worlds/firefly/magic.yaml`.**

### victoria — dialed-supernatural
- Source: Bargained-for (rare, dial-gated); Innate (mesmerism); Item (cursed letters)
- Cost: Sanity + Karma (moral and psychic only)
- Limits: No resurrection, no combat magic, no tools (supernatural is dread, not utility)
- Visibility: Hidden / heretical at high gothic; Mythic-lapsed at low
- Reliability: Negotiated (supernatural has agency)
- Intensity dial: `axes.gothic` (0.0–1.0)
- Manifestation: Invoked + Reflexive; Domain = Psychic + Necromantic + Divinatory

### heavy_metal — *the napkin already-in-prose*
- Source: Bargained-for + Innate (inherited); Learned forbidden
- Cost: Vitality + Soul/Debt + Sanity + Components — every cost type, as a stated rule
- Limits: Every working has an account-holder; consequences propagate at five scales
- Reliability: Negotiated
- Visibility: high (medium magic level)
- Manifestation: any Mode; broad Domain

The cosmology of heavy_metal is the most napkin-aligned content in the entire repo. Validates the schema fully.

### low_fantasy
- Source: Item (relics) + Divine (lapsed cults) + Bargained (standing stones) + occasional Innate
- Cost: Vitality / Sanity / Backlash — unpredictable
- Limits: Reliable casting forbidden; resurrection forbidden; repeatability forbidden
- Visibility: Mythic / lapsed
- Reliability: Wild
- Manifestation: Ritual + Item-channeled; Domain = ad hoc

Tests **competing-source uncertainty** — multiple Sources entertained as possible, none confirmed. Schema must support this.

### neon_dystopia
- Source: McCoy (chrome, code) + Acquired (radical implants) + at high Chrome dial: Innate-developed (Netrunner virtuosity, sometimes with chosen-one narrative tag)
- Cost: Vitality (cyberpsychosis) + Sanity + Karma (humanity percentage)
- Limits: Anchored to physical/digital substrate; no true supernatural; AI godhood only at high Chrome
- Visibility: Public + regulated (corp) at low; Hidden / black-market at high
- Reliability: Deterministic + Backlash
- Intensity dial: `axes.chrome`
- Manifestation: Reflexive + Invoked + Item-channeled; Domain = Physical + Spatial-virtual + Psychic-via-chip

### pulp_noir — *Victoria's tuple, different decade*
- Source: Item (artifacts) + Ritual (witnessed)
- Cost: Sanity
- Limits: Not a tool; not reliable; not safe; not understood
- Visibility: Hidden
- Reliability: Wild / Negotiated
- Intensity dial: `axes.occult`
- Manifestation: Invoked + Ritual; Domain = Psychic + Necromantic + Divinatory

The schema **collapses Victoria + Pulp Noir into one shape with different content** — proves the framework's reuse value.

### road_warrior
- Source: Item (the named vehicle) + McCoy (the mechanic) + Acquired (Wasteland changes you)
- Cost: Vitality (gas, parts, blood) + Karma (the road remembers)
- Limits: No supernatural; the magic-bearing object is a vehicle
- Visibility: Mythic
- Reliability: Skill-checked + Backlash
- Manifestation: Item-channeled exclusively; Domain = Physical + Spatial (the road)

The schema must admit **Vehicle as a first-class Item type**.

### spaghetti_western
- Source: Item (named guns, cursed bullets) + McCoy (gunsmith)
- Cost: Karma (reputation) — every body costs sleep
- Limits: No supernatural strict; the impossible shot is the only allowed miracle
- World-Knowledge: Folkloric (legends, ghost-rider tales)
- Visibility: Dismissed by educated; feared by superstitious
- Reliability: Deterministic at item level, narratively weighted
- Manifestation: Reflexive + Item-channeled; Domain = Physical only
- Note: the Man-With-No-Name "chosen one" quality is a *narrative tag* on Innate-aptitude, not a Source.

## Schema Sketch

### Genre layer — `genre_packs/{genre}/magic.yaml`

```yaml
magic:
  intensity:
    dial: gothic              # axes.yaml axis name; omit for fixed
    default: 0.3
  allowed_sources:
    - id: item
      label: Item-based
      examples: ["named guns", "scrolls"]
      always_available: true
    - id: mccoy
      label: McCoy / Invented
      examples: ["gunsmith", "ripperdoc"]
    - id: innate_developed
      label: Innate (developed)
      gated_by: world          # world declares specifics
    - id: acquired
      label: Acquired
      narrative_only: true     # not a player-build option
  required_costs: [karma, sanity]   # narrator must surface one
  hard_limits:
    resurrection: forbidden
    true_creation: forbidden
    mind_compulsion: with_cost
  world_knowledge:
    default: folkloric             # acknowledged / folkloric / mythic_lapsed / esoteric / classified / denied
    dial: gothic                   # optional — axis that scales it
    # Worlds may pick any value the genre permits
    permitted: [folkloric, esoteric, classified]
  visibility:
    # Only meaningful where world_knowledge != denied
    default: dismissed
  manifestation:
    modes: [reflexive, invoked, item_channeled]
    domains: [physical, psychic]
  narrator_register: |
    The supernatural is dread, not toolbox.
  player_options:
    can_build_caster: false
    can_acquire_in_play: true
```

### World layer — `worlds/{world}/magic.yaml`

```yaml
magic:
  intensity: 0.2
  active_sources:
    - id: item
      examples_in_world: ["the Lassiter", "Mal's antique pistol"]
    - id: acquired
      narrative_seeds:
        - id: river_tam
          source: acquired_via_experimentation
          cost: [sanity, social_isolation]
          reliability: wild
          domain: [psychic, divinatory]
  world_knowledge: classified        # the world doesn't know psychic powers exist
  visibility: n/a                    # because nobody acknowledges it as a category
  hard_limits:
    psionics_as_player_class: forbidden    # River Tam Rule for THIS world
```

A world can:
- Pick from genre's `allowed_sources`
- Tighten genre limits, never loosen
- Set its own `intensity` if dial is provided
- Add world-specific `narrative_seeds` (the named characters/items that carry the magic)

## What Becomes Possible

1. **Narrator can query the magic system structurally** — "is item-based allowed?" "what's the cost commitment?" "is this above the gothic dial threshold?"
2. **Cliché-judge has a reference** for "this genre forbids X but the narration just did X" detection.
3. **Genre packs stop scattering magic across 4–5 files.** Single source of truth.
4. **Worlds inherit cleanly** without forking the genre.
5. **`magic_level: none` retires** in favor of explicit allowed-source lists *and* a separate `world_knowledge` field. The current flag is doing four jobs at once (no Sources / Sources-but-no-player-class / Sources-but-classified / Sources-but-denied-as-category) and conflating them is the root cause of mutant_wasteland mislabeling itself, space_opera contradicting itself, and victoria needing a separate dial to dig out from under it.

## Open Questions

1. ~~**Pre-Ordained as Source vs. modifier?**~~ **Resolved 2026-04-27.** Pre-Ordained is *not* a Source; it's a narrative role/tag that rides on top of a Source (Anakin = Innate-developed + chosen-one tag). Captured at lore/scenario layer.
2. **Vehicle / Vessel as first-class Item subtype.** **Decision: yes.** Road_warrior already implements as `item_subtype: vessel`. Schema base must support `item_subtypes: [weapon, scroll, relic, vessel, vehicle, ship]`.
3. **Competing-source uncertainty** (low_fantasy) — does the schema express "multiple Sources entertained, none confirmed" or just "all of these are possible"? Probably needs an `epistemic_status` field per source. Defer until low_fantasy gets schematized.
4. **Should `manifestation.domain` admit narrator-discovered Domains?** Or is the list closed? Lean closed for now, plugin-extendable later.
5. **Is `world_knowledge` itself dialable?** Victoria's gothic axis does two jobs: scales both *whether magic exists* (intensity) AND *whether the world acknowledges it* (world-knowledge). The victoria magic.yaml documents this as a known coupling. May resolve when more genres are schematized.
6. **Three axes that can be confused — keep explicit in narrator prompts:**
   - **Intensity** (does it exist / how much?)
   - **World-Knowledge** (does the world know / how acknowledged?)
   - **Visibility** (given knowledge, what's the social register?)

## Architecture: Plugins as Magic Systems *(revised 2026-04-27 evening)*

**Plugins are not just "genre-specific extensions." Plugins ARE the magic systems.** Multiple plugins coexist within a single genre. Each plugin represents one *parallel magic system*. Heavy_metal can have a Bargained-For plugin AND a Divine plugin AND a Learned-Ritual plugin — three magic systems running side by side. Caverns_and_claudes can have an Item-Legacy plugin AND an Alchemy plugin without those colliding. A genre's identity is the *set of plugins it permits*.

### Plugin → Delivery Mechanism → Class chain

Every plugin sits in a four-part chain:

```
PLUGIN (e.g. bargained_for_v1)
  ↓
DELIVERY MECHANISM (one or more — faction, place, time, condition, native,
                    discovery, relational, cosmic)
  ↓
ARCHETYPE / CLASS (e.g. Warlock — the player-build option)
  ↓
COUNTER ARCHETYPE (e.g. The Severer — the NPC that opposes)
```

### Delivery Mechanisms

A delivery mechanism is *how the resource a Source represents reaches the player*. Each mechanism has terrific plot potential because each one drives a different kind of story:

| Mechanism | Description | Plot engine |
|---|---|---|
| **Faction** | An institution controls/brokers/distributes the resource | Politics, NPC dispatch, social cost, betrayal arcs |
| **Place** | The resource exists at specific locations | Pilgrimage, territorial control, geographic tension |
| **Time** | The resource is gated by calendar / season / event | Deadlines, "the comet only returns once a century," cyclical urgency |
| **Condition** | The resource is gated by player-state (penance, fasting, blood-debt, etc.) | Penance arcs, self-imposed transformation, ritual purity |
| **Native** | Born with it — the player IS the source | Identity arcs, growing into power, the cost-of-self |
| **Discovery** | Find it in the world (the lost grimoire, the named gun in a dead man's hand) | Treasure-hunt, dungeon-crawl, "I have to find the X" |
| **Relational** | Gained through bonds (familiar, mentor, patron, bonded spirit) | Patron-protégé arcs, bonds-and-betrayals, the friendship cost |
| **Cosmic** | Ambient world-truth, no friction at delivery (everyone has a touch) | Rarely interesting on its own; usually combined with another mechanism |

**A plugin typically supports multiple mechanisms.** `bargained_for_v1` is *typically* faction-mediated (the Bargainers Guild) but can also be place-bound (crossroads at midnight) or relational (the personal pact with a fae you met in a dream). Each mechanism unlocks a different story shape for the same magic system.

A world picks WHICH mechanism(s) of a plugin it activates. Same plugin, different worlds, different plot engines.

### Faction is one Mechanism, not THE Mechanism

The earlier draft conflated *plugin source* with *faction pipeline*. They're separable. Faction is one delivery mechanism among several. Its appeal is high — institutions bring NPCs, politics, opposition — but it's not load-bearing. A magic system can deliver without ever involving a faction (a wild Bargained-For pact made alone with a forest spirit; an Innate ability that activates only at full moon; a McCoy invention pieced together from a scavenged manual found in a ruin).

The unification still holds at one level: **every "where does the player get this?" question routes through some delivery mechanism**. The mechanism is what generates the plot. Without one, the resource has no narrative friction and might as well be a stat reset between sessions.

### What a plugin spec contains

```yaml
# docs/design/magic-plugins/bargained_for_v1.md → bound to a YAML schema
plugin: bargained_for_v1

# The Source it implements (one of the napkin's Source values)
source: bargained_for

# Delivery mechanisms this plugin supports. Worlds pick one or more to activate.
delivery_mechanisms:
  - id: faction
    archetype: pact_guild
    description: "Institution that brokers, witnesses, and enforces pacts"
    npc_roles: [broker, witness, collector, severer]
    plot_engine: "politics, NPC dispatch, betrayal arcs"
  - id: place
    description: "Resource is bound to specific locations (crossroads, ruined altars, named hills)"
    plot_engine: "pilgrimage, territorial control, geography-as-character"
  - id: relational
    description: "Direct personal pact with a non-faction entity (fae, ancestral ghost, bound spirit)"
    plot_engine: "patron-protégé arcs, bond-and-betrayal, the friendship-cost"
  - id: condition
    description: "Pact only activates under specific player-state (post-loss, post-fast, etc.)"
    plot_engine: "penance arcs, self-imposed transformation"

# Class/archetype mapping — which player builds use this plugin
classes:
  - id: warlock
    label: Warlock
    pact_required: true
  - id: pact_priest
    label: Pact-Priest
    pact_required: true

# Counter archetypes — who opposes this magic
counters:
  - id: severer
    label: The Severer
    description: "Specialist in cutting obligation chains; fatal to caster"
  - id: account_holder_revoker
    label: Revoking Patron
    description: "The pact's account-holder withdrawing their grace"

# Visible-ledger config — what bills appear on the UI
ledger_bars:
  - id: soul_debt
    label: Soul / Debt
    color: ember
    fills_per_working: 0.0–1.0  # plugin determines how much per cast
  - id: karma
    label: Obligation
    color: iron

# OTEL span shape — what the narrator MUST emit when invoking this magic
otel_span:
  required_fields: [working_id, source, debited_costs, debited_scales, mechanism_engaged]
  on_violation: gm_panel_red_flag
  # mechanism_engaged is one of the plugin's delivery_mechanisms ids
  # (faction | place | time | condition | native | discovery | relational | cosmic)

# Hard limits inherited or specialized
hard_limits:
  - inherits_from_genre: true
  - additional_forbidden: []
```

### Schema layers, refined

- **Base napkin schema** — universal fields (Source taxonomy, Cost types, World-Knowledge, Visibility, Reliability, Counter, Manifestation). Stable, rarely changes.
- **Plugins** — one per magic system. Live at genre level. **Never at world level.** Worlds inherit; they don't define new plugins.
- **Genre `magic.yaml`** — declares which plugins this genre permits and the narrator/visibility/intensity defaults that apply across them.
- **World `magic.yaml`** — instantiates each plugin's *active delivery mechanism(s)* with named in-world specifics (the named faction, the named place, the named time-window, the named condition, etc.); dials intensity; sets era-specific world_knowledge.

### Items as NPCs *(decision)*

Item-based magic delivers items that **carry personality**. Schema implication: items have OCEAN scores, dispositions, optionally names. The Interceptor (road_warrior) is high-conscientiousness, low-agreeableness. The Stormbringer (heavy_metal) is high-extraversion, low-agreeableness, devouringly hungry. Stored under `item_subtypes` with their own NPC-shaped block:

```yaml
items:
  - id: the_interceptor
    subtype: vessel
    name: "The Interceptor"
    ocean: { o: 0.4, c: 0.85, e: 0.2, a: 0.15, n: 0.35 }
    disposition_default: -10   # mistrusts new drivers
    bonded_to: ~               # set when claimed in play
```

Items can refuse to fire. Items have opinions. The named gun knows whose hand it's in.

### Counters as character archetypes *(decision)*

Every plugin declares its `counters:` list. These are not just mechanical defenses — they're **NPC archetypes the GM can play**. The exorcist, the dispeller, the iron-charm-maker, the severer, the gunsmith-of-the-anti-named-gun. They're designed to be *deployable*, not just referenced. The cartography of a magic system is incomplete without its anti-system.

### The Load-Bearing Feature: Visible Ledger + OTEL Lie-Detector *(committed)*

See `docs/design/visible-ledger-and-otel.md` for the full spec. Summary:

- **Player-facing**: a small UI panel showing N bars (one per active cost type for the active world). When a working is narrated, the bars rise visibly. The bill is shown before the consequence lands.
- **GM-facing** (Sebastien-shaped): the same bars + an OTEL span feed showing which plugin claims to have fired, which costs were debited, which factions were notified.
- **Lie-detector**: every magical claim in narration MUST emit an OTEL span keyed to a plugin. If the narration says "you cast a spell" and no span fires, the GM panel flags RED. If the narration claims a Source the world doesn't permit, RED. If it violates a hard_limit, DEEP RED.

This directly satisfies the CLAUDE.md OTEL principle (*"Claude is excellent at winging it. The only way to catch this is OTEL logging on every subsystem decision"*) at the subsystem where winging matters most.

### Plugin specs go in `docs/design/magic-plugins/`

First specs to draft:
- `bargained_for_v1` — the heavy_metal signature plugin
- `divine_v1` — the feeding-economy plugin (heavy_metal, victoria-Catholic worlds)
- `item_legacy_v1` — items-as-NPCs (spaghetti_western, road_warrior, caverns_and_claudes, heavy_metal)
- `mccoy_v1` — inventor pipeline (spaghetti_western gunsmiths, neon_dystopia ripperdocs, road_warrior wrenchers)
- `obligation_scales_v1` — the five-scale ledger (heavy_metal)
- `mutation_v1` — acquired-bodily plugin (mutant_wasteland)

## Audit Pass — All 11 Genres

**Inventory:** 7 production packs in `genre_packs/` + 4 workshop-unique in `genre_workshopping/`. (`heavy_metal` and `spaghetti_western` exist in both — production is canonical, workshop versions are older drafts.)

### Audit Table

| Pack | Loc | current `magic_level` | What it actually means | Proposed `world_knowledge` | Proposed `intensity` | Diagnosis |
|---|---|---|---|---|---|---|
| **caverns_and_claudes** | prod | `none` | "no caster classes" — items exist | `folkloric` | fixed-low | **Mislabeled.** Magic items are core gameplay; flag means "no Wizard/Cleric class." Should become `caster_classes: false` + `allowed_sources: [item]`. |
| **elemental_harmony** | prod | `high` | Accurate | `acknowledged` | fixed-high | Accurate. Schema-ize for consistency. |
| **heavy_metal** | prod | `medium` | Accurate but understated | `acknowledged` | dial: `gravity` | Most napkin-aligned cosmology in repo. Could argue `high` — magic is structurally load-bearing. |
| **mutant_wasteland** | prod | `none` | Mislabeled — mutations ARE magic | `acknowledged` | fixed-medium | **Currently lying.** "Use Mutation" combat action with risk-narration is a magic system in everything but name. Source = Acquired + Innate-automatic. |
| **space_opera** | prod | `none` | Conflates Firefly/Expanse with Star Wars | varies by world (`classified` → `mythic_lapsed` → `acknowledged`) | era-dial per world | **Genre-vs-world confusion.** Genre allows Innate-Psychic + McCoy; the "no psionics as toolkit" rule belongs to one *world* (Firefly), not the genre. |
| **spaghetti_western** | prod | `none` | Folkloric-dismissed; item magic ubiquitous | `folkloric` | fixed-low | **Mislabeled.** Named guns, the impossible shot, the gunslinger reputation — all item-channeled Reflexive-Physical magic. The genre denies the word, not the structure. |
| **victoria** | prod | `none` | Dialed via gothic axis | `gothic`-dialed (`denied` → `esoteric`) | dial: `gothic` | **Architecture correct, label wrong.** Already uses an axis to scale supernatural; just needs the label to match. |
| **low_fantasy** | workshop | `low` | Accurate; multiple competing sources | `mythic_lapsed` | fixed-low | **Tests competing-source uncertainty.** Pale Fire vs. Drowned Mother vs. standing stones — schema must support "multiple Sources entertained, none confirmed." |
| **neon_dystopia** | workshop | `none` | Tech-substitution; `magic_design.md` is explicit | `denied` (low) → `acknowledged-as-tech` (high) | dial: `chrome` | **Structurally consistent.** The "no magic" claim is genuinely epistemological — the world has no concept. Tech IS the magic system; admit it via `mccoy` source. |
| **pulp_noir** | workshop | `low` | Accurate; mirrors victoria's pattern | `esoteric` | dial: `occult` | **Same shape as victoria, different decade.** Schema collapses the two into one structure with different content. |
| **road_warrior** | workshop | `none` | Folkloric named-vehicle magic | `folkloric` | fixed-low | **Mislabeled.** "The man with the V8 Interceptor" is item-magic where the item is a vehicle. Schema needs `item_subtypes: [weapon, scroll, relic, vessel]` to admit this cleanly. |

### Aggregate Findings

**`magic_level: none` is wrong in 5 of 7 packs that use it.** Of the 7 packs flagged "none":
- 4 are mislabeled (caverns_and_claudes, mutant_wasteland, spaghetti_western, road_warrior — magic exists, just not as caster classes)
- 1 is genre/world-confused (space_opera — it depends which world)
- 1 has correct architecture but wrong label (victoria — gothic-dialed, not absent)
- 1 is structurally accurate (neon_dystopia — `denied` is the right epistemic claim)

**Only `none` pack that's genuinely correct:** neon_dystopia.

**Only `none` pack where the architecture is already right but the label is misleading:** victoria.

### Recommended Field Replacements

The single `magic_level` flag splits into three explicit fields:

```yaml
# Replaces: magic_level
allowed_sources: [item, mccoy, acquired]   # what Sources this genre permits
world_knowledge: folkloric                 # epistemic: does the world know?
intensity: { dial: gothic, default: 0.3 }  # ontological: how much exists?
```

A separate boolean clarifies the orthogonal player-build question:

```yaml
player_options:
  can_build_caster: false   # whether a player may select a magic-using class at chargen
```

Most current `magic_level: none` packs become `can_build_caster: false` with non-empty `allowed_sources`. That distinction alone would resolve mutant_wasteland and caverns_and_claudes without any framework changes.

## Next Moves

### Completed 2026-04-27

- ✅ **`space_opera/magic_design.md` rewritten** — River Tam Rule is now one valid world-tuple alongside the Force Rule and Bene Gesserit Rule.
- ✅ **Pre-Ordained removed from Source list** — narrative role/tag, not a Source.
- ✅ **Heavy_metal schematized** — `genre_packs/heavy_metal/_drafts/magic.yaml`.
- ✅ **5 mislabeled packs fixed** — clarifying comment added to `magic_level: none` in each `rules.yaml`, plus new draft `magic.yaml` in each pack: `caverns_and_claudes`, `mutant_wasteland`, `spaghetti_western`, `victoria`, `road_warrior`.
- ✅ **Plugin/registration model committed** — replaces extension-slot proposal.

### Still pending

1. **Migration plan:** retire `magic_level` field once a magic.yaml loader is in place. Currently the field still exists for backward-compat; comments mark it as draft-deprecated.
2. **Schema validation form:** decide if base schema lives as JSON-schema, pydantic, or just a markdown spec. Defer until the loader is needed.
3. **First plugin spec:** `obligation_scales_v1` for heavy_metal. Lives in `docs/design/magic-plugins/`.
4. **Item subtype taxonomy:** formalize `[weapon, scroll, relic, vessel, vehicle, ship]`. Road_warrior already uses `vessel`.
5. **Audit remaining workshop packs:** schematize `low_fantasy`, `neon_dystopia`, `pulp_noir` to validate the framework against contrasting genres.
