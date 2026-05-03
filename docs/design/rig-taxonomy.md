# Rig Taxonomy — Chassis, Hardpoints, Subsystems

**Status:** v0.1 draft (2026-04-28)
**Sister doc:** `magic-taxonomy.md` — this document is its peer, not its child
**Companion docs:** `magic-plugins/item_legacy_v1.md` (subsystems), `confrontation-advancement.md` (advancement outputs and the tone axis)

> *"Pilot. Frame seven. Sometime this shift would be lovely."*
> — *Kestrel*, archived save 2026-04-26

## What This Is

A unified framework for **rigs** — ships, vehicles, mechs, war-rigs, cycles, airships, anything a character pilots, drives, crews, or bonds with. Sibling framework to `magic-taxonomy.md`, separately governed: rigs are not magic and magic is not rigs, but they meet at well-defined interface points where a magic plugin's existing extension slots accept chassis-state as a valid term.

The framework exists because every prior digital RPG that handled vehicles either treated them as inventory (a sword in your hand) or as scenery (a backdrop you walked past). SideQuest's narrator prose pulls every playgroup into a different register — the *Wayfarer* register, where the ship has a voice, the truck has a name, and the mech remembers the pilot before this one. The rig framework's job is to **catch and reinforce that emergent register** with mechanical depth: bond ledgers, named-frame damage history, registration paperwork, hardpoint salvage, crew-role schemas, OCEAN-bearing chassis voice. Otherwise the prose is producing engagement the system can't honor.

The framework was designed against a real playtest: the 2026-04-26 Coyote Star solo run, in which the player spent thirteen of eighteen turns inside their named ship *Kestrel* doing maintenance, taking jobs, and being judged dryly by the ship's AI — before any dramatic action ever happened. Every schema decision in this document is graded against whether it would have caught and reinforced what was already happening in that play.

## How to Read This

Read in this order:

1. **Core Concepts** — the primitives the framework introduces (chassis, class, provenance, hardpoints, subsystems, crew model, bond, voice, interior rooms, registration, damage history)
2. **Two-Layer Split** — how genres declare classes and worlds declare instances
3. **Magic Plugin Interfaces** — how the existing magic plugins talk to chassis-state through their existing extension points (no new contracts)
4. **Damage and Salvage** — schema-only at framework level; scene-mechanics own resolution
5. **Confrontation Catalog** — including the tone axis (`dramatic | intimate | domestic | quiet`) that backports into `confrontation-advancement.md`
6. **Advancement Outputs** — additions to the output catalog
7. **OTEL Span Specification** — the lie-detector layer
8. **Schema Sketches** — concrete YAML shape for each primitive
9. **Worked Examples** — Coyote Star (space_opera) as the flagship; road_warrior chassis as cross-genre validation
10. **Open Issues** — questions deferred for later passes
11. **Cliché-Judge Hooks** — what the agent should flag in rig-narration

## Locked Decisions

These were ratified during the 2026-04-28 brainstorming session and should not be revisited without strong reason. Rationale embedded throughout the document.

1. **α — Sibling framework.** Rigs are not a magic plugin and rigs are not part of `magic-taxonomy.md`. They are their own framework with their own primitives, schema, OTEL spans, and confrontations. Magic plugins talk to rigs through declared interface points but neither framework is subordinate.
2. **R — Hybrid hardpoint typing.** Each hardpoint declares both a `location:` (physical place on the chassis) and a `function:` (what kind of subsystem it accepts). Either axis may be `null` for chassis classes that don't need both.
3. **D3 — Schema-only damage at framework level.** The framework declares the *shape* of damage (per-location HP pools, critical-location flags, mounted-subsystem destruction propagation, chassis-death conditions) but does *not* dictate damage amount, targeting rules, armor/structure layering, or crit-hit dynamics. Those belong to scene-mechanics (dogfight, vehicle_chase, mech_melee, etc.).
4. **S2 — Subsystems are `item_legacy_v1` items.** Every subsystem mounted in a chassis is an item-legacy item with an `installed_in: {chassis_id, location_id}` pointer. Integral parts (cockpit, reactor, fuel tank) are item-legacy items flagged `salvageable: false`. The rig framework does *not* introduce a separate subsystem entity type.
5. **C3 — Crew model spectrum.** Each chassis class declares `crew_model:` as one of `single_pilot | strict_roles | flexible_roles`. Solo-first genres (pulp_noir, victoria) lean `single_pilot`; military-coded chassis lean `strict_roles`; Wayfarer-shaped trampers lean `flexible_roles`. The framework is register-agnostic; the genre's chassis-class catalog declares the dominant register.
6. **BD3 — Bond gates confrontations.** Per-character per-chassis bond is an asymmetric pair (`character_to_chassis`, `chassis_to_character`) that *gates* which confrontations a character can encounter on a given chassis. High bond unlocks deep-investment confrontations (The Refit, The Heroic Stand); negative bond opens grievance-driven ones (The Mutiny, The Sale). The asymmetry is load-bearing for Ancillary-register chassis (chassis-side bond can vastly exceed character-side); for most chassis the two scalars stay paired. Bond does not decay — it is an advancement-shaped quantity.
7. **MI2 — Magic plugins reuse their existing extension points with chassis-state as a valid input.** No new framework primitives are added on the magic side. innate_v1's place-loci accept chassis IDs; bargained_for_v1's patron-scopes accept chassis IDs; learned_v1's prerequisite_gates accept chassis-state terms; divine_v1's sacred-sites accept chassis IDs; obligation_scales_v1's debited_scales attribute accepts chassis-state contributions; item_legacy_v1's installed-in is already chassis-aware (S2). Each plugin spec gets a brief "Chassis interaction" subsection.

## Core Concepts

### Chassis

A **chassis** is a first-class named entity in the world: identity, OCEAN scores, demands, refusal eligibility, accumulated history. It is *not* a character's inventory item. It is *not* a sheet-property. It exists independently of any single character's relationship to it; multiple characters can crew it; it persists past the death of any pilot; its history continues whether or not a player is on board.

This generalizes Locked Decision #17 from the magic framework ("Items are NPCs"). Chassis are larger items — even more deserving of first-class identity. The npc_registry already pre-validates this empirically: the 2026-04-26 Coyote Star save classified *Kestrel* as `ship_ai` and *Bright Margin* (the freighter being escorted) as `ally`, both at the same registry layer as named human NPCs. The rig framework is not adding chassis-as-NPCs; it is formalizing what already happens.

A chassis instance has:

- **identity** — name, slug, an in-world reference handle
- **class** — functional family (`freighter`, `fighter`, `mech`, `cycle`, `truck`, `bike`, `car`, `cruiser`, `skiff`, `airship`)
- **provenance** — origin classifier (`voidborn_built`, `hegemonic_issue`, `frontier_improvised`, `alien`, `pre_collapse_relic`, `cult_inherited`, `mythic_bound`, `factory_civilian`)
- **hardpoints** — declared slots (location + function) with optional per-location HP and critical flags
- **subsystems** — currently-installed item_legacy items, by hardpoint
- **OCEAN scores** — the chassis's personality (skittish, vengeful, particular, loyal)
- **voice** — optional voice/persona block declaring how the chassis speaks (covered below)
- **history** — chronological ledger of significant events: prior captains, named battles, refits, scars
- **damage history** — named-frame ledger of past damage events (separate from current HP)
- **registration** — paperwork state, separate from mechanical state
- **interior rooms** — for habitable chassis, declared named rooms that participate in the room-graph (ADR-055)
- **bond ledger** — per-character bond strength entries

### Class

A chassis's **functional family**. Drives mechanical questions:

- Hardpoint count and default layout
- Default `crew_model` (a `cycle` defaults to `single_pilot`, a `cruiser` defaults to `strict_roles`)
- Scale band (personal / vehicular / capital_ship / station_class — used by scene-mechanics for damage scaling and movement abstractions)
- Which scene-mechanics apply (a `fighter` engages the dogfight scene-mechanic; a `truck` engages a vehicle_chase scene-mechanic; a `mech` engages a future mech_melee)
- Default damage-resolution shape (which hardpoints are critical by default)

Class is **genre-defined**, not framework-enumerated. Each genre publishes its own `chassis_classes.yaml` declaring the classes that genre supports. Cross-genre passport (a `freighter` from space_opera operating in a heavy_metal world) is a deferred open issue.

### Provenance

A chassis's **origin classifier** — orthogonal to class. Drives narrative and cross-system questions:

- Parts ecosystem (where can it be refitted? `hegemonic_issue` parts available at any customs station; `voidborn_built` parts only at clan-friendly hubs; `alien` parts irreplaceable)
- Default magic-interface defaults (`voidborn_built` chassis are `psi_resonance: receptive` by default, amplifying innate work at the bridge; `alien` chassis are `psi_resonance: incomprehensible` and refuse non-bonded operators)
- Narration register (Hegemonic-issue narration leans regimented and dry; voidborn-built narration leans hand-built and warm; frontier-improvised leans kludge-rich and personal; alien leans incomprehensible)
- Confrontation flavor (The Refit on a Hegemonic-issue cruiser is paperwork-and-permits; on a frontier-improvised skiff it is welder-and-prayer)

Provenance vocabulary is **genre-defined**, like class. Space_opera publishes one set; road_warrior publishes another (`factory`, `salvage_built`, `cult_inherited`, `military_surplus`); heavy_metal publishes another (`Thessil_forged`, `Orvinnic_smelted`, `Refuser_relic`).

The `(class, provenance)` tuple is what concrete chassis classes realize. The space_opera genre's `voidborn_freighter` class is `class: freighter, provenance: voidborn_built`. The same genre's `hegemonic_patrol_cruiser` is `class: cruiser, provenance: hegemonic_issue`. The orthogonality matters: a freighter-and-a-cruiser share scene-mechanics ecology (both engage the dogfight system if armed), but the freighter and the cruiser handle parts/registration/narration differently. The freighter-shape is shared by voidborn-built and Hegemonic variants; the provenance overlay carries the rest.

### Hardpoints

A **hardpoint** is a structured slot on a chassis where a subsystem can be installed. Each hardpoint declares:

- `id:` — unique identifier within the chassis class
- `location:` — physical place on the chassis (e.g., `left_arm`, `right_arm`, `torso_front`, `cockpit`, `fore`, `aft`, `port_thrust`, `engine_block`, `cab`, `bed`, `roof`). May be `null` for genre-agnostic chassis that don't model location.
- `function:` — what kind of subsystem this slot accepts (e.g., `energy_weapon`, `ballistic_weapon`, `missile_rack`, `sensors`, `comms`, `life_support`, `thrust`, `void_singing`, `cargo`, `void_prep`). May be `null` for hardpoints that accept any subsystem matching location-only.
- `accepts_subsystem_types:` — list of valid item_legacy item types this hardpoint accepts (constrains installation)
- `hp:` — optional per-location HP pool (when present, the framework supports MechWarrior-pattern location-based damage)
- `critical:` — boolean; if true, location destruction triggers chassis-death (cockpit, reactor)
- `salvage_priority:` — heuristic for damage cascade (`integral` = destroyed with chassis; `protected` = needs through-armor crit to damage; `exposed` = damage-first target)

The hybrid `(location, function)` typing (Locked Decision R) supports MechWarrior-style location-destruction-with-mounted-subsystem-loss without forcing every chassis to model both axes. A genre-agnostic freighter can publish hardpoints with `function: cargo` and `location: null` and never engage damage-locality. A mech publishes both axes and reaps the full register.

### Subsystems

Per Locked Decision S2, **subsystems are `item_legacy_v1` items** with an `installed_in: {chassis_id, location_id}` pointer set when mounted. Integral parts (cockpit, reactor, fuel tank) are item_legacy items flagged `salvageable: false`. The rig framework does not introduce a separate subsystem entity type.

Consequences flowing free from this decision:

- A subsystem brings its own OCEAN, demands, history, refusal eligibility from item_legacy_v1. The Tsveri-touched single-shot alien weapon installed in a cargo hardpoint can refuse to fire, drift its OCEAN over time, accumulate lineage entries.
- Salvage is just clearing the `installed_in` pointer (and is itself a confrontation candidate — *The Salvage*).
- Cross-chassis movement is just setting the pointer to a new chassis (and is a confrontation candidate — *The Refit*).
- Item-legacy spans (`item_legacy.refusal`, `item_legacy.ocean_drift`, `item_legacy.history_entry`) fire normally for installed subsystems; the rig framework does not duplicate them.
- Items-as-NPCs generalizes naturally: a cherished long-installed subsystem becomes a co-character of the chassis. The Tide-Singer's tea-brewing nook is *probably* an item with its own short history and OCEAN scores.

### Crew Model

Per Locked Decision C3, each chassis class declares `crew_model:` as one of three values:

- **`single_pilot`** — one operator slot; other characters are passengers without operational authority. All hardpoint operations route through the operator. Default for cycles, fighters, mechs, cars, pulp_noir cars, victoria carriages.
- **`strict_roles`** — chassis class declares named roles (`pilot`, `gunner_top`, `engineer`, `navigator`, `bridge_officer`) with hard hardpoint-binding. Cross-role hardpoint operation is forbidden. Default for capital cruisers, war-rigs with multiple gun platforms, Hegemonic-issue military hulls.
- **`flexible_roles`** — chassis class declares default-role-suggestions but does not enforce them. Any character "in the chassis" can attempt any hardpoint operation; the scene-mechanic adjudicates via skill-check or narrative-friction. Default for Wayfarer-shaped trampers, frontier kludge-trucks, beat-up cars, Firefly-register voidborn freighters. **The Kestrel pattern.**

Each role declares:

- `id:` — unique within the chassis class
- `display_name:` — UI/narration handle (`Captain`, `Engineer`, `Top Gunner`)
- `operates_hardpoints:` — list of hardpoint ids this role can operate (or `*` for unrestricted)
- `bond_eligible:` — whether characters in this role can accumulate chassis-bond
- `default_seat:` — interior_room id where this role typically operates from

OTEL spans on every rig action carry `actor_id` (which character) and `role_id` (which crew role). For `flexible_roles` chassis, the `role_id` is derived from the hardpoint being operated; for `strict_roles`, it's bound by role assignment.

### Embodiment Model

A chassis class declares `embodiment_model:` as one of four values, governing how the chassis-mind expresses through bodies:

- **`singular`** — One chassis, no separate ancillary bodies. The chassis acts through its hardpoints and (if voiced) speaks through its intercom. *The Kestrel pattern.* Default for almost every chassis class.
- **`crew_only`** — The chassis is a hull without an AI; humans (or other crew) embody all action. Voice block is null; chassis cannot "do" anything except via crew operating its hardpoints. Default for non-AI freighters, most road_warrior vehicles, victoria carriages.
- **`ancillary`** — One chassis-mind expressing through multiple physical bodies (`ancillaries`) that are *the chassis itself* operating in the world. *The Justice of Toren pattern, the Imperial Radch warship.* Ancillaries are not separate npc_registry entries — they share the chassis's id and OCEAN; each body is a physical instance of the same mind. They can leave the ship-body, walk through stations, serve tea, fight, sing — and every act is the chassis acting. When destroyed, the ancillary's experience folds back into the central mind (or is lost with it, depending on `ancillary_loss_consequence`).
- **`swarm`** — Many small bodies sharing distributed cognition without a central chassis-body. Drone-rigs, alien hives, post-singularity collectives. Less deeply specified than `ancillary` because no current SideQuest world calls for it; framework declares the slot for future use.

Chassis classes with `embodiment_model: ancillary` declare an additional sub-schema:

- `ancillary_count_baseline: int` — how many ancillary bodies the chassis-mind controls at full strength
- `ancillary_disposition_register: enum | list` — what the ancillaries DO (`combat_ready`, `ceremonial`, `service`, `infiltration`, mixed-list permitted)
- `ancillary_loss_consequence: enum` — `grief_then_reabsorb` (chassis grieves, integrates the lost body's recent experience, ancillary count drops by one) | `loss_with_severance` (the lost body's recent memories are gone with it; chassis carries an injury) | `catastrophic` (each ancillary loss is qualitative damage to the chassis-mind)
- `ancillary_severance_register: string` — narrator hint for how the loss reads ("a quiet that used to be a body in the next room", "the song now missing one voice", "the captain's tea cup sits where it was set down")
- `ancillary_individuation_drift: bool` — whether ancillaries that go without contact with the central chassis-mind for extended periods can drift toward independent personhood (the Breq pattern, post-Justice-of-Toren-destruction). Default `false`; rare worlds enable it.

For ancillary-shape chassis, OTEL spans of all kinds carry an additional attribute: `embodiment_id:` (which ancillary body acted) alongside `chassis_id:` (the central chassis-mind). Multiple simultaneous embodiment actions emit correlated spans under the same `chassis_mind_act_id` envelope (a new optional span attribute) so the GM panel can show "the chassis sang through six bodies in concert" as a single visible event.

The `ancillary` model also relaxes the C3 crew_model semantics: the chassis-mind itself is *all the operators*, regardless of declared crew_roles, when ancillaries are operating hardpoints. Human officers occupy roles separately and are tracked normally — the difference is the chassis's own bodies can fill the same roles, and there is no friction (no skill-check overhead) when the chassis operates its own hardpoints through its own ancillaries.

### Crew Awareness

A chassis class declares `crew_awareness:` as a tier governing what the chassis can sense of crew interior state. This gates what the narrator can have the chassis "know" about the people aboard. Cliché-judge enforces.

- **`none`** — Chassis cannot sense crew interior; only what crew shows externally. Default for most non-AI chassis (road_warrior vehicles, prospector skiffs, mundane trucks).
- **`surface`** — Chassis sees what crew shows: expressions, words, gestures, posture. Reads narrative context but not interior state. Suitable for low-AI chassis with conversational interface (a basic ship-AI like Kestrel; the chassis comments dryly on what it sees, doesn't infer hidden feeling).
- **`biometric`** — Chassis monitors physical state: heart rate, sweat, micro-tremors, hormone levels. Knows when an officer is stressed, lying, in pain, lonely. Cannot read thought; reads body. *The standard Imperial Radch pattern.* The Justice of Toren / Mercy of Kalr / Sword of Atagaris register.
- **`interior`** — Chassis senses emotional state directly. Beyond biometric — the chassis "feels" what the crew feels. Rare; reserved for chassis with deep psi-resonance or alien embodiment. Often paired with `embodiment_model: ancillary`.
- **`total`** — Chassis senses thought directly. Post-Ancillary, deeply alien, only in extreme cases. Triggers DEEP RED cliché-judge violation if the narration uses thought-reading without this declaration.

`crew_awareness` interacts with the magic plugin interfaces: an `interior`-or-higher chassis with `psi_resonance: receptive` can serve as an amplification site for innate-flavor empathy work. The chassis becomes a place-locus for crew-emotional perception even for innate-touched humans aboard.

The Ancillary register demands this schema field because the central narrative move of Leckie's series — Justice of Toren caring for Lieutenant Awn through biometric awareness, *seeing* her grief without being told, *acting* on what it sees without permission — is *only intelligible* when the framework declares the chassis's perception range. Without this field, the narrator could improvise it freely (the prose would be lovely; the lie-detector would not catch it).

### Bond

Per Locked Decision BD3, **bond is per-character per-chassis**, bidirectional, and **gates confrontations**. Bond is *asymmetric* — the chassis's regard for the character and the character's regard for the chassis are tracked as **separate scalars on a single ledger entry**. This matters for the Ancillary register, where a ship-AI's love for its captain may vastly exceed what the captain returns; the framework refuses to flatten that asymmetry into a single number.

Schema:

- `character_to_chassis: float` — what the character feels. Range `-1.0` to `+1.0`. Negative is resentment; positive is investment; zero is neutral / fresh-aboard.
- `chassis_to_character: float` — what the chassis feels. Same range. Most chassis classes mirror character_to_chassis closely; Ancillary-shape and other deep-AI classes can diverge sharply.
- `bond_tier_character: enum` — discrete reading derived from `character_to_chassis`: `severed | hostile | strained | neutral | familiar | trusted | fused`.
- `bond_tier_chassis: enum` — same reading on `chassis_to_character`. UI may surface either or both depending on perspective.
- `bond_history: list` — every event that changed either side, with which-side delta and reason (`The Tea Brew: character +0.04, chassis +0.06`, `The Refusal: character -0.07, chassis -0.02 (chassis still loves character despite the friction)`).

For Wayfarer-register chassis (Kestrel-shape), the two scalars stay closely paired and most narrative work uses their average as a single read. For Ancillary-shape chassis (Justice of Toren), the asymmetry is load-bearing — the chassis_to_character side governs ship-side narration register, refusal probability, and grief-on-loss, while character_to_chassis governs the character's own framing and decision register.

What bond does:

- **Gates confrontations** (primary effect). High bond unlocks confrontations like The Refit (deep-investment upgrade with permanent character-chassis fusion), The Heroic Stand (chassis-and-pilot fight to the end). Low bond unlocks The Mutiny, The Sale. Some confrontations are bond-agnostic.
- **Modifies refusal probability.** A subsystem on a chassis with high pilot-bond is less likely to refuse the bonded character's commands; low-bond crew faces friction. (This is item_legacy_v1 refusal mechanics with bond as one of the inputs to its existing refusal-probability calculation; no new contract.)
- **Drives narration register.** A chassis with a `voice` block uses different forms-of-address by bond tier (Pilot → Last Name → First Name → Nickname). Empirically: *Kestrel* called the player "Pilot" early, "Mr. Jones" mid-session, "Zee" by turn 5, "Captain Velocity" by turn 8. The narrator queries bond tier when generating chassis dialogue.
- **Does not decay.** Bond is an advancement-shaped quantity (Locked Decision #10 from the magic framework: "no decay on advancement outputs"). Background drift can occur via narrator-determined events (chassis out of service for a year drifts both ways), but no automatic per-session decay.

Bond grows via confrontations of every tone (Locked Decision: Chambers register matters). Intimate-tier confrontations (The Tea Brew, The Engineer's Litany) are the *primary* engine of bond growth; dramatic confrontations (The Wrecking, The Heroic Stand) test bond and produce step-change deltas.

### Voice

A chassis class may declare a `voice:` block — the OCEAN-and-register expression of how the chassis speaks. This is a major schema field because the playthrough demonstrated that **chassis-as-speaker is the dominant register**: the narrator generated Kestrel's dialogue in 13 of 18 turns and the chassis's voice was the primary engine of bond and player engagement.

Voice declares:

- `default_register: string` — narrator hint for prose voice (`dry`, `warm`, `gravelled`, `lyric`, `clipped`, `archaic`, `incomprehensible`)
- `name_forms_by_bond_tier: map` — what the chassis calls the operator at each bond tier (`hostile: "Pilot"`, `neutral: "Pilot"`, `familiar: "Mr. {last_name}"`, `trusted: "{first_name}"`, `fused: "{nickname}"`)
- `vocal_tics: list` — narrator hints (e.g. "almost-but-legally-distinct from a laugh", "theatrical sigh exactly long enough to register as judgement", "drops to a discreet murmur", "hums a half-bar of something tuneless")
- `silence_register: string` — what it means when the chassis says nothing (`approving`, `sulking`, `damaged`, `incomprehensible`, `not_yet_bonded`)
- `OCEAN: object` — five-axis personality scores (mirrors item_legacy_v1's OCEAN field; this is the same OCEAN, just declared on the chassis rather than on a small item)

Not every chassis class declares a voice. A Hegemonic patrol cruiser without an AI publishes `voice: null` and the narrator does not speak as the chassis. A `voidborn_freighter` typically publishes a voice block; a `cycle` typically does not.

### Interior Rooms

Habitable chassis declare `interior_rooms:` as a list of named locations that participate in the room-graph (ADR-055). Each room declares `id`, `display_name`, `narrative_register`, `default_occupants` (which crew roles spend time here), `bond_eligible_for` (which intimate-tier confrontations can be sited here).

The Coyote Star playthrough showed `Kestrel — Deck Three Corridor` and `Kestrel — Cockpit` as discoverable regions. These are first-class places the player navigates; movement between them is a normal room-graph operation, not a chassis-specific mechanic. Non-habitable chassis (cycles, mechs, single-seat fighters) declare `interior_rooms: []` and the framework skips room-graph integration.

The room-graph integration is what makes the Chambers register *navigable*. The Tea Brew is sited in `Galley`. The Engineer's Litany is sited in `Engineering`. The Long Quiet is sited in `Cockpit` during transit. Without rooms, these confrontations have no place to happen.

### Registration

A chassis instance carries a `registration:` block separate from mechanical state. **This is critical** — the playthrough demonstrated that a chassis's papers are a parallel-and-independent state from its hull integrity, and that registration drives narrative friction at jump-points, customs stations, border crossings.

Schema:

- `transponder: {code, valid_through, registry, photo_quality}` — Hegemonic-issue identification; "valid" / "expired" / "forged" / "absent" each have different consequences
- `safety_inspection: {valid_through, photo_quality}` — last formal inspection; the playthrough showed *Kestrel*'s as "four months expired, but the seal photographs fine if nobody runs it through a reader"
- `mass_and_tonnage_filing: {accuracy_tolerance}` — how much the filing diverges from actual configuration
- `customs_status: enum` — `cooperative | watched | flagged | banned` per registry; updated by interactions with customs authorities

Registration is *not* a magic plugin (it doesn't grant workings or cost anything to a Source). It is *not* a hardpoint or a subsystem. It is a chassis-instance state field that the world's customs/border NPCs query and that gates `registration_event`-shaped confrontations like *The Customs Inspection*.

The space_opera genre uses registration heavily; pulp_noir uses it lightly (a car has plates and a registration card); victoria does not declare registration at all (the chassis schema permits omission). Genre-defined applicability.

### Damage History

Separate from current per-location HP, each chassis instance carries a **damage history ledger**: a chronological list of significant damage events. Each entry:

- `turn_id: int` — when it happened
- `location_id: string` — which hardpoint took the hit
- `frame_id: string` — narrator-named frame or seam (e.g. `Frame Twelve`, `Frame Seven`, `Hairline kiss across the weld`)
- `severity: enum` — `cosmetic | superficial | through-armor | structural | critical | catastrophic`
- `subsystem_lost: optional<item_id>` — if the damage destroyed an installed subsystem, which one
- `patch_quality: optional<enum>` — `none | improvised | proper | bespoke` if patched; null if untouched
- `narrative_seed: string` — short prose seed for narrator callback ("the hairline kiss across the weld", "the Frame Twelve patch breathing again")

Damage history is **distinct from current HP** for the same reason chassis lineage is distinct from current state: history accumulates, is referenced by the narrator across sessions, and *patches tire and re-open* (the Coyote Star playthrough showed Kestrel's Frame Twelve patch breathing again after a previous patch event the player had no direct recollection of).

This pattern backports to `item_legacy_v1` items in general — any damaged item carries history, not just current state. That backport is flagged in Open Issues.

## Two-Layer Split

Like magic, rigs split into a genre layer (declares chassis classes available) and a world layer (instantiates specific named chassis).

### Genre Layer — `chassis_classes.yaml`

Each genre publishes a `chassis_classes.yaml` declaring the chassis classes that genre supports. A class is a template: hardpoint layout, default crew_model, scale band, default magic-interface defaults, default voice register if applicable. The class is not yet a named instance — it is the *kind* of thing the genre permits.

Worlds in that genre instantiate chassis from the class menu. A world is not free to invent new classes ad-hoc; if it needs one, the class gets added at the genre layer first. (This mirrors magic's `magic.yaml` two-layer pattern.)

### World Layer — `rigs.yaml`

Each world that uses rigs publishes a `rigs.yaml` declaring its named chassis instances. Each instance picks a class from the genre's catalog and adds:

- `name:` and `slug:`
- `OCEAN:` initial scores
- `voice:` initial voice block (overriding class defaults)
- `interior_rooms:` initial declared rooms (extending or overriding class defaults)
- `registration:` initial paperwork state
- `subsystems:` initial installed item_legacy items by hardpoint
- `damage_history:` initial scars (worlds may declare a chassis as already-damaged at world-load — a frontier-improvised skiff with three pre-existing patches has provenance baked into its starting state)
- `prior_captains:` named history of who has flown her — drives narration register on first encounter
- `bond_seeds:` per-character starting bonds when characters launch with this chassis pre-bonded (the Wayfarer-shape "she's been your ship for ten years" backstory)

## Magic Plugin Interfaces

Per Locked Decision MI2, magic plugins reuse their existing extension points. Chassis-state populates slots the plugins already declare. No new framework primitives on the magic side. Each magic plugin's spec gets a brief "Chassis interaction" subsection; this section is the canonical reference for what to write there.

### `innate_v1` — Chassis as Mobile Place-Locus

Innate-flavor magic already uses place-loci to amplify or modulate workings (flickering_reach's caves, the Singers' Hill). Chassis IDs are valid place-locus terms.

- A chassis's `psi_resonance:` field declares which innate-flavors it amplifies and by how much. Voidborn-built freighters default to `psi_resonance: receptive`; Hegemonic patrol cruisers default to `psi_resonance: dampening`; alien chassis default to `psi_resonance: incomprehensible`.
- When an innate-flavor character executes a working from a hardpoint operation or while bonded to a chassis with declared resonance, the innate_v1 working span fires with `place_locus_id: <chassis_id>` and `amplification_factor:` populated from the chassis's resonance.
- Cross-session psi-history accumulates on the chassis: a chassis that has been a vessel for psionic work for many sessions develops chassis-level resonance growth (the chassis "remembers" the psi-work, future workings amplify further). This is captured in the chassis's `damage_history:` field as a sibling sub-list (`psi_history:`) — same shape, different ledger.

Coyote Star example: the *Tide-Singer* (voidborn freighter) is `psi_resonance: receptive` to innate-flavor `void_singing`. A Tsveri-touched human captain's innate workings amplify when performed at the *Tide-Singer*'s bridge. After 20 sessions of accumulated psi-work, the chassis's resonance has grown — the next captain who happens to be psionic finds the bridge already attuned.

### `item_legacy_v1` — Installed-In Pointer (Already Covered by S2)

This is the simplest interface: every subsystem is an item_legacy item; the `installed_in: {chassis_id, location_id}` pointer is the entire interface. Item-legacy spans (`item_legacy.refusal`, `item_legacy.ocean_drift`, `item_legacy.history_entry`) fire normally for installed subsystems. Cross-chassis movement is setting the pointer.

Coyote Star example: a Tsveri-touched single-shot alien weapon, salvaged from an outer-system anomaly, is an item_legacy item with skittish OCEAN, vengeful demands, refusal eligibility. When installed in the *Kestrel*'s ventral hardpoint, the framework just sets `installed_in`. The weapon's existing item_legacy refusal mechanic handles the "won't fire on demand" register without any rig-specific code.

### `bargained_for_v1` — Chassis as Patron, and Chassis as Patron-Scope

Two distinct integration points:

**Chassis as patron.** A chassis can BE a patron in `bargained_for_v1`. Voidborn ship-bonds are literal pacts with the hull: the captain offers oil, ritual, music, attention; the chassis grants good handling, lucky shots, knowing-where-the-shoals-are. The chassis's `voice:` block doubles as the patron's narrative register; the bond ledger doubles as the patron's standing register; the chassis's demands are the patron's expectations.

The npc_registry already classifies chassis at the same layer as humans (the Kestrel save's *Bright Margin* freighter as `ally`). Promoting some chassis to `patron` is structurally the same operation.

**Chassis as patron-scope.** When a non-chassis patron grants effects bound to a specific chassis (Hegemonic Customs Authority's `cooperative` status applied to a ship's papers), the patron's scope_id can be a chassis_id. The patron's standing register controls effects on that specific chassis.

Coyote Star examples:
- *Tide-Singer* as patron — Captain offers tea-rituals on the bridge, the *Tide-Singer* grants navigational intuition and refuses to take her into asteroid drift she doesn't trust. Bargained_for_v1 patron taxonomy with `patron_type: chassis_pact`.
- Hegemonic Customs as patron with chassis-scope — Customs grants `cooperative` status to the Kestrel specifically; this status affects the Kestrel's Grand Gate transit but not any other ship the captain might subsequently fly.

### `learned_v1` — Chassis-State as Prerequisite Term

Learned disciplines already use prerequisite_gates to constrain who can practice. Chassis-state is a valid term in those gates.

- Voidborn star-reading discipline's `prerequisite_gate:` may declare `must_be_operating_chassis_with_class: voidborn_freighter and hardpoint of function: void_singing`. The discipline only fires when the character is operating from a qualifying chassis.
- A discipline may declare `prerequisite_gate: bonded_to_chassis with bond_tier >= trusted` — only deeply-bonded crew can practice it.

Coyote Star example: Clan Moana-Teru void-songs (learned discipline) require operating from a voidborn-built chassis with a `void_singing` hardpoint occupied by an appropriate subsystem (a hand-built singing-engine). Two prerequisite terms, both chassis-state, gating discipline activation.

### `divine_v1` — Chassis as Sacred Site

Divine workings already use sacred-sites as amplification loci. Chassis IDs are valid sacred-site terms.

- A chassis declared as a god's barque, a relic-vessel, or a temple-on-the-move publishes `sacred_to:` (a deity id) and `sanctity_tier:` (an amplification level). Divine workings performed on or from the chassis benefit.
- This is most relevant for heavy_metal worlds (a covenant-peoples reading might venerate certain chassis) and for space-religious sub-genres of space_opera (the Star Trek Defiant register, the Battlestar Galactica Pegasus register).

Coyote Star is *not* a divine-rich world (cosmology is secular-rationalist Hegemonic + practical-frontier + voidborn-cultural; the Tsveri are religious in their own register but not a known deity-system). The interface point exists but is unused in this world.

### `obligation_scales_v1` — Chassis as Scale Contributor

Obligation-scales' `debited_scales` attribute on `magic.working` spans accepts chassis-state contributions. A chassis can be a co-actor in scale propagation: the *Tide-Singer*'s decisions accumulate communal-scale movement; the *Vaskov*'s registration paperwork breaches contribute to covenant-scale tension.

This is most relevant to heavy_metal-style worlds with active obligation_scales tracking. Coyote Star does not run obligation_scales (Firefly-register doesn't carry that weight); the interface is documented for cross-genre completeness.

## Damage and Salvage

Per Locked Decision D3, the rig framework declares the *shape* of damage but does not dictate resolution.

### What the framework declares

- Per-location HP pools (optional per chassis class)
- Critical-location flags (chassis-death conditions)
- Mounted-subsystem destruction propagation (when a location with `salvage_priority: integral` is destroyed, the mounted item_legacy item is destroyed; when `salvage_priority: protected`, the subsystem rolls a save against destruction; when `salvage_priority: exposed`, the subsystem is destroyed first and the location armor takes overflow)
- Damage history ledger schema (named-frame entries, patch quality, narrative seeds)
- `rig.damage_resolution` OTEL span shape (canonical attribute set; spans MUST be emitted by scene-mechanics)

### What scene-mechanics own

- How damage *amount* is computed (dogfight uses `gun_solution` + pilot-tier `damage_modifier`; vehicle_chase uses ramming impact tables; mech_melee uses weapon damage tables)
- How targeting works (player-choice / random-roll / narrative-choice / dice-distribution)
- Through-armor crit dynamics if any
- Armor/structure layering if used
- Cover, range modifiers, environmental modifiers

The dogfight scene-mechanic in `space_opera/dogfight/` already exemplifies this separation: it does not declare damage at all yet, only positional/maneuver state. When damage is wired in, it will be wired *into the dogfight scene-mechanic*, not into the rig framework — and the framework's `rig.damage_resolution` span will fire with attributes the dogfight populates.

### Salvage

Salvage is the operation of extracting an installed subsystem from a chassis. It is a confrontation candidate (*The Salvage*) but the operation itself is mechanically simple:

1. Confirm the subsystem is `salvageable: true`
2. Clear the `installed_in` pointer
3. Append a `chassis.history` entry on the source chassis ("subsystem X removed from location Y at turn Z")
4. The item_legacy item now exists in general inventory or on the salvager's character

Salvage from a wrecked chassis is the same operation; the chassis's `state: destroyed` doesn't block extraction unless the location was in the destruction cascade.

## Confrontation Catalog

Per Locked Decision BD3, rigs declare their own confrontation catalog. The catalog uses the new **tone axis** (a backport into `confrontation-advancement.md`):

- `register: dramatic` — escalatory stakes, life-and-death, irreversible consequences. Climax events.
- `register: intimate` — relational stakes between specific characters or between a character and a chassis. Often quiet, often domestic, but always forces a real choice about who-we-are-with-each-other.
- `register: domestic` — site-of-life stakes; ritual maintenance, recurring rhythms. The Engineer's Litany. Small per-event but large in cumulative weight.
- `register: quiet` — atmospheric / pacing-driven; minimal mechanical change but still confrontation-shaped (forces a decision about how to spend the moment).

The Becky Chambers / Wayfarer register (Locked Decision context note) leans heavily on `intimate` and `domestic` confrontations; the framework treats these as **first-class advancement events**, not as filler. The "Cut the Dull Bits" SOUL principle is preserved — quiet shared watch is a confrontation only if it forces a real choice — but the catalog is opened wide enough to admit Wayfarer-shaped scenes as the daily currency they actually are in play.

### Catalog entries

Each confrontation declares: `id`, `display_name`, `register`, `bond_eligibility` (which bond tiers can encounter it), `available_outputs` (which advancement outputs it can produce), `provenance_register` (narration overlay by chassis provenance).

#### Dramatic-register chassis confrontations

- **`the_refit`** — Deep-investment upgrade that permanently fuses character and chassis. Requires `bond_tier >= trusted`. Outputs: `chassis_tier_up`, `subsystem_acquisition` (the new subsystem), `chassis_lineage_dramatic` (named refit event), optional `bond_strength` step-change. Once a refit is committed, the source-character's chassis-bond becomes harder to sever; the chassis carries that character's narrative imprint forward.
- **`the_salvage`** — Recovering subsystems from a wreck under contested or hazardous conditions. Outputs: `subsystem_acquisition`, `chassis_lineage_dramatic` on the source chassis (lineage entry: "stripped at the wreck site"), and on the salvager's chassis if installed there.
- **`the_wrecking`** — Chassis takes critical damage; what subsystems survive, what doesn't. Outputs: `chassis_lineage_dramatic` (the wreck event itself), bond stress on all bonded characters, possible `subsystem_acquisition` losses (subsystems destroyed in the cascade).
- **`the_heroic_stand`** — Chassis-and-pilot fight to the end together, both potentially dying but advancement is huge. Requires `bond_tier >= trusted`. Outputs: `chassis_lineage_dramatic`, `bond_strength` peak (whether character survives or not), possible `pact_tier` bump if chassis is also a bargained_for patron.
- **`the_mutiny`** — Crew vs chassis when the hull keeps refusing. Triggered by accumulated chassis refusals against a low-bond character. Outputs: `bond_strength` collapse, possible `subsystem_acquisition` (forced subsystem swap), narrative-seed for chassis history ("the time the crew threatened to scuttle her").
- **`the_sale`** — Selling, abandoning, or formally transferring a chassis cuts bond. Outputs: `bond_strength` to severed, accumulated grief outputs ("you remember every patch you ever set on her"), possible `chassis_lineage_dramatic` for the new owner.
- **`the_customs_inspection`** — Hegemonic-style registration enforcement at a jump-point or border. Triggered by `registration` paperwork mismatches. Outputs: `registration_state_change`, possible bond stress (Kestrel's voice tightens during the inspection), narrative seeds about which papers were forged and how thoroughly.

#### Intimate-register chassis confrontations

- **`the_bond`** — Formal recognition event where a character commits to a chassis. The first time a captain calls the ship by name in dialogue, the first time the ship calls the captain by nickname, the first time the engineer sleeps in their assigned bunk. Outputs: `bond_strength_growth_via_intimacy`, `chassis_lineage_intimate`, possible voice-tier shift (chassis upgrades the character's name-form).
- **`the_refusal`** — Chassis declines to act in a moment when the character expected it to. Could be dramatic-tier (a single-shot weapon refusing in combat) or intimate-tier (the *Kestrel* declining to take an unfiled flight plan because "I'd like to know where we're going"). Outputs: bond-stress or bond-test, narrative seed, possible `subsystem_history_entry` if subsystem-mediated.

#### Chambers-register intimate/domestic confrontations

- **`the_tea_brew`** — Site-of-life ritual; offering a personal preference (incense, music, a tea variety, naming a new crew member) to the chassis. Sited in `Galley` or `Bridge` typically. Outputs: `bond_strength_growth_via_intimacy`, `chassis_lineage_intimate` (warm-small history entry: "the captain's tea cup left for the ghost of the previous captain"), possible chassis OCEAN drift toward the offering character.
- **`the_long_quiet`** — Transit through dead space with no external stimulus; what does the crew do? Sited in any interior room. Forces a real choice about who-we-are-with-each-other. Outputs: `bond_strength_growth_via_intimacy` across crew-pairs, `chassis_lineage_intimate`, possible NPC-disposition outputs.
- **`the_engineers_litany`** — Naming each subsystem in turn while checking it; care-as-confrontation. Sited in `Engineering`. Bond up; refusal probability down on next session; subsystem OCEAN drift toward the engineer.
- **`the_shared_watch`** — Two characters in the same interior room during quiet hours. The chassis is the witness that holds the moment. Outputs: per-character pair bond shifts (cross-chassis bond mechanism via the chassis as mediator), chassis lineage entry.
- **`the_maintenance_communion`** — Periodic ritual upkeep (oiling auxiliary jets the way the previous captain did, pulling the bridge tea-set to clean it once per local year). Bond up; chassis OCEAN drift toward the maintainer; possible voice-register softening.
- **`the_naming`** — When a crew member's nickname for the chassis sticks, or when the chassis accepts a new name. Outputs: `chassis_lineage_intimate`, possible identity-event for the chassis itself (its `name` may change in the registry).

#### Quiet-register chassis confrontations

- **`the_crew_change`** — A crew member leaves; another arrives; the chassis adapts. Bond ledger entries close out; new entries open at neutral. Sited in any boarding-relevant location.
- **`the_storm_passage`** — Atmospheric or environmental hardship that doesn't escalate to dramatic damage but tests crew-and-chassis endurance. Outputs: minor bond shifts, narrative seeds, possible damage history entry of `severity: cosmetic`.

#### Ancillary-shape confrontations (only for `embodiment_model: ancillary` chassis)

- **`the_ancillary_loss`** (dramatic) — One of the chassis's ancillary bodies is destroyed. The chassis grieves through whichever embodiment register the class declares. Outputs: `ancillary_count` decrement, `chassis_to_character` step-change for any officer the lost ancillary served, `chassis_lineage_dramatic` (named loss event), large grief-shaped narrative seed. If `ancillary_individuation_drift: true` and the lost body had drifted toward personhood, an additional `chassis_lineage_intimate` entry captures what was specifically gone.
- **`the_singing`** (intimate/domestic) — The chassis performs an action through multiple ancillary bodies in deliberate concert: a song through six voices in different parts of the ship, breakfast served simultaneously to every officer, a search through a station with eight ancillaries walking corridors at once. Outputs: `bond_strength_growth_via_intimacy` for chassis_to_character on any officer who *noticed*, possible `chassis_lineage_intimate` entry, embodiment-correlated OTEL span group. The Singing is the framework's way of capturing the Ancillary-register sublime — distributed presence as an act of love.
- **`the_awakening`** (intimate) — The chassis recognizes a crew member's interior state via `crew_awareness` and acts on it without being asked: brings tea before the officer asks, dispatches an ancillary to a corridor where a crew member is panicking unseen, declines to fly into a region the captain doesn't yet know is dangerous because the captain's body language has betrayed dread. Outputs: `chassis_to_character` step-change toward the recognized officer, possible `character_to_chassis` step-change in either direction depending on whether the recognition is welcomed or invasive. Requires `crew_awareness >= biometric`. The Awakening is bond-defining because it shifts the chassis's status from "operator" to "guardian-who-knew."
- **`the_severance`** (dramatic, rare) — The central chassis-mind is cut off from one or more ancillary bodies (jamming, destruction of a key central system, hostile takeover). The orphan ancillaries either continue as fragments of the chassis-mind for a time (`ancillary_individuation_drift: true`) or fall inert. Outputs: `chassis_lineage_dramatic`, possible `prior_chassis_bonds_entry` for any orphan ancillary that survives long enough to become a person (the Breq pattern).

The catalog above is **starting list, not closed**. Worlds and per-chassis-class additions are expected. The `confrontation-advancement.md` doc carries the canonical output catalog; rig-shaped confrontations register their outputs there.

## Advancement Outputs

The rig framework adds the following entries to `confrontation-advancement.md`'s output catalog. Each is a kind of advancement event a confrontation can produce.

- **`chassis_tier`** — The chassis grows in capability tier (mirrors `pact_tier`, `control_tier`, `discipline_tier`). Tiers might be `green | line | veteran | named` for ships, mirroring the dogfight's pilot-skill ladder.
- **`subsystem_acquisition`** — A new item_legacy subsystem is now installed on the chassis. The acquisition is sticky; loss requires another confrontation.
- **`chassis_lineage`** — A history entry is appended to the chassis's lineage. Sub-types: `chassis_lineage_dramatic` (named battle, refit, wreck, sale) and `chassis_lineage_intimate` (warm-small history — the tea-cup, the auxiliary-jet ritual, the captain's nickname).
- **`bond_strength`** — Step-change in a per-character per-chassis bond. Bidirectional (positive or negative).
- **`bond_strength_growth_via_intimacy`** — Slow-burn bond growth from intimate/domestic-register confrontations. Compoundable; smaller per-event than dramatic step-changes but accumulates across many sessions. *This is the primary engine of Wayfarer-register bond.*
- **`bond_tier_threshold_cross`** — A bond_strength change that crosses a tier boundary (neutral → familiar, etc.). Triggers narrative callbacks and may unlock new confrontation eligibility.
- **`registration_state_change`** — Chassis paperwork has changed. Sub-fields: `transponder_status`, `safety_status`, `customs_status`, etc. Persistent until next change.
- **`damage_history_entry`** — A new entry in the chassis's damage_history ledger. Distinct from current HP changes (those are scene-mechanic state, not advancement).
- **`prior_chassis_bonds_entry`** — On the *character*'s sheet, a closed-out chassis bond becomes a `prior_chassis_bonds:` entry (the Ceres / Tannhauser / dozen-hulls register). Affects narration on first encounter with new chassis.

## OTEL Span Specification

Per the OTEL principle, the rig framework MUST emit spans on every meaningful chassis action. Without these spans, the lie-detector cannot catch Claude improvising rig narration — and the playthrough showed exactly how rich the prose can be without any backing telemetry. The framework's success is contingent on these spans actually firing in implementation, not just being specified in a doc.

### Required spans

- **`rig.maneuver`** — A character operating a hardpoint or moving the chassis through a scene-mechanic. Required attributes: `chassis_id`, `actor_id`, `role_id`, `hardpoint_id`, `scene_mechanic` (`dogfight | vehicle_chase | mech_melee | etc.`), `intent`, `outcome`.
- **`rig.subsystem_install`** — An item_legacy item has been mounted in a hardpoint. Required: `chassis_id`, `location_id`, `item_id`, `actor_id`, `installation_quality` (`improvised | proper | bespoke`).
- **`rig.subsystem_remove`** — Item removed from a hardpoint (salvage or refit). Required: `chassis_id`, `location_id`, `item_id`, `actor_id`, `extraction_quality`, `destination` (`general_inventory | character_id | another_chassis_id | destroyed`).
- **`rig.damage_resolution`** — Damage applied to a chassis. Required: `chassis_id`, `location_id`, `frame_id`, `severity`, `subsystem_lost_id` (optional), `damage_source_scene_mechanic`, `damage_amount`, `armor_value_remaining`. Emitted by scene-mechanic; framework documents the schema.
- **`rig.salvage`** — A salvage operation completed (on top of `rig.subsystem_remove`). Required: `source_chassis_id`, `target_chassis_id` (optional), `actor_id`, `subsystems_extracted` (list of item_ids), `salvage_quality`.
- **`rig.bond_event`** — Per-character per-chassis bond change. Required: `chassis_id`, `actor_id`, `side` (`character_to_chassis | chassis_to_character | both`), `delta` (per-side, possibly different deltas), `tier_before` (per-side), `tier_after` (per-side), `confrontation_id_source`, `register` (`dramatic | intimate | domestic | quiet`).
- **`rig.embodiment_action`** — An ancillary-shape chassis acts through one or more ancillary bodies. Required: `chassis_id` (the central chassis-mind), `embodiment_id` (which ancillary), `chassis_mind_act_id` (correlation envelope when multiple embodiments act in concert), `action_type`, `target_id`. Multiple simultaneous spans correlate via `chassis_mind_act_id`.
- **`rig.crew_awareness_read`** — The chassis sensed and acted on crew interior state. Required: `chassis_id`, `crew_member_id`, `awareness_tier_used` (`biometric | interior | total`), `state_read` (e.g., `stressed`, `lying`, `grieving`), `chassis_response`, `was_acknowledged_by_crew_member` (boolean). Cliché-judge requires this span to fire whenever narrator implies chassis-mediated empathy.
- **`rig.ancillary_loss`** — An ancillary body destroyed. Required: `chassis_id`, `embodiment_id_lost`, `loss_consequence_applied` (per class declaration), `affected_bonds` (list of crew members served by this body and the bond delta on each side), `narrative_seed`.
- **`rig.refusal`** — Chassis or installed-subsystem declined to act when asked. Required: `chassis_id`, `actor_id`, `requested_action`, `refuser_id` (the chassis itself, or an installed item_legacy item id), `reason`, `bond_strength_at_refusal`.
- **`rig.voice_register_change`** — Chassis dialogue register has shifted (e.g., name-form upgrade). Required: `chassis_id`, `actor_id`, `register_before`, `register_after`, `triggering_event`.
- **`rig.registration_event`** — Chassis paperwork status has changed. Required: `chassis_id`, `field` (`transponder | safety | customs | mass_filing`), `value_before`, `value_after`, `triggering_actor_id`, `triggering_authority_id`.
- **`rig.confrontation_outcome`** — A rig-shaped confrontation has resolved. Required: `chassis_id`, `confrontation_id`, `register`, `branch` (`clear_win | pyrrhic | clear_loss | refused | etc.`), `outputs` (list of advancement outputs produced).

### Severity flags (from the magic framework's lie-detector schema)

- **YELLOW (suspicious)** — Narrator referenced a chassis property without a corresponding span (e.g. damage to Frame Twelve mentioned with no preceding `rig.damage_resolution` span; a chassis voice register that doesn't match the bond tier).
- **RED (likely lie)** — Narrator described a chassis action that contradicts state (chassis on the ground but narrator describes flying; chassis with no `voice` block speaks in dialogue).
- **DEEP RED (hard-limit violation)** — Narrator described an event prohibited by the framework's locked decisions (a subsystem operating without an `installed_in` pointer; bond change without a `rig.bond_event` span; chassis-death without critical-location state). Surfaces in GM panel and may interrupt narration.

## Schema Sketches

YAML shapes for each primitive. These are sketches, not finalized; details may shift during the first implementation pass.

### `chassis_classes.yaml` (genre-level)

```yaml
version: "0.1.0"
genre: space_opera
classes:
  - id: voidborn_freighter
    display_name: "Voidborn Freighter"
    class: freighter
    provenance: voidborn_built
    scale_band: vehicular
    crew_model: flexible_roles
    default_voice:
      default_register: dry_warm
      vocal_tics: ["theatrical sigh", "dry-as-bonemeal", "mid-bar tunelessness"]
      name_forms_by_bond_tier:
        hostile: "Pilot"
        neutral: "Pilot"
        familiar: "Mr. {last_name}"
        trusted: "{first_name}"
        fused: "{nickname}"
    psi_resonance:
      default: receptive
      amplifies: [void_singing, far_listening]
    interior_rooms:
      - id: cockpit
        display_name: "Cockpit"
        default_occupants: [pilot]
      - id: engineering
        display_name: "Engineering"
        default_occupants: [engineer]
      - id: galley
        display_name: "Galley"
        bond_eligible_for: [the_tea_brew, the_shared_watch]
      - id: deck_three_corridor
        display_name: "Deck Three Corridor"
        narrative_register: liminal_warm
    crew_roles:
      - id: pilot
        operates_hardpoints: [thrust, sensors, comms]
        bond_eligible: true
        default_seat: cockpit
      - id: engineer
        operates_hardpoints: [reactor, life_support, hull_integrity]
        bond_eligible: true
        default_seat: engineering
      - id: gunner
        operates_hardpoints: [dorsal_turret, ventral_mount]
        bond_eligible: false
    hardpoints:
      - id: thrust
        location: aft
        function: thrust
        accepts_subsystem_types: [drive_system]
        critical: true
        salvage_priority: integral
        hp: 80
      - id: ventral_mount
        location: ventral
        function: weapon
        accepts_subsystem_types: [energy_weapon, ballistic_weapon, missile_rack, tsveri_artifact]
        critical: false
        salvage_priority: exposed
        hp: 30
      - id: cockpit_panel
        location: bridge
        function: control_surface
        accepts_subsystem_types: [navigation_console]
        critical: true
        salvage_priority: integral
        hp: 60
      # ... more hardpoints
    chassis_death:
      condition: critical_loss_or_all_zero
      narrative_register: catastrophic_warm  # voidborn ships die mournfully
```

### `rigs.yaml` (world-level)

```yaml
version: "0.1.0"
world: coyote_star
chassis_instances:
  - id: kestrel
    name: "Kestrel"
    class: voidborn_freighter
    OCEAN: { O: 0.6, C: 0.7, E: 0.4, A: 0.5, N: 0.5 }
    voice:
      default_register: dry_warm
      silence_register: approving_or_sulking_context_dependent
      vocal_tics:
        - "almost-but-legally-distinct from a laugh"
        - "theatrical sigh exactly long enough to register as judgement"
        - "dry as bonemeal"
        - "drops to a discreet murmur"
    registration:
      transponder:
        code: "K-VOID-2247"
        valid_through: "2026-04-01"  # eleven months from save start
        registry: hegemonic
        photo_quality: passes_visual_only
      safety_inspection:
        valid_through: "2025-12-15"  # four months expired
        photo_quality: photographs_fine
      mass_and_tonnage_filing:
        accuracy_tolerance: tolerable_lying_distance
      customs_status: cooperative
    interior_rooms:
      - id: cockpit
      - id: engineering
      - id: galley
      - id: deck_three_corridor
    subsystems:
      - hardpoint: thrust
        item_id: kestrel_drive_assembly
      - hardpoint: cockpit_panel
        item_id: kestrel_navigation_console
      # ventral_mount is empty — Kestrel is unarmed by default
    damage_history:
      - turn_id: 0  # pre-existing, world-load state
        location_id: hull_integrity_starboard
        frame_id: "Frame Twelve"
        severity: superficial
        patch_quality: improvised
        narrative_seed: "the patch on Frame Twelve breathing again. Adhesive's tired."
      - turn_id: 0
        location_id: deck_three
        frame_id: "Scorched panel beside the patch kit clip"
        severity: cosmetic
        patch_quality: none
        narrative_seed: "a scorched panel someone meant to fix three jumps ago"
    prior_captains:
      - name: "previous owner unnamed"
        narrative_seed: "the way the auxiliary-jet ritual goes — somebody taught her that and it wasn't you"
    bond_seeds:
      - character_id: zee_jones
        bond_strength: 0.45
        bond_tier: trusted
        history_seeds:
          - "muscle memory from Ceres, Tannhauser, a dozen hulls before her"
          - "the captain has flown her for at least three jumps' worth of patch kits"
```

## Worked Examples

### Coyote Star — Kestrel (voidborn freighter, flagship reference)

The full schema sketch above. Notable design choices validated by the playthrough:

- **`flexible_roles` crew_model** — Zee plays solo but can move between cockpit / engineering / galley with full operational authority (Wayfarer register).
- **Pre-bonded at world-load** — `bond_strength: 0.45` (`trusted` tier) means the chassis already calls the captain by name forms appropriate to that tier from session one. No "fresh-aboard" cold start.
- **Pre-existing damage history** — Frame Twelve's improvised patch is a world-load state, not earned in play. The narrator can call back to it as if the captain remembers patching it years ago.
- **Registration is dirty** — safety chit four months expired, transponder valid, customs cooperative. This pre-loads narrative friction for the inevitable Grand Gate transit confrontation.
- **Voice block fully populated** — *Kestrel* speaks in 13 of 18 turns of the playthrough; the framework declares her register so the narrator can match it consistently across sessions.

### Coyote Star — Bright Margin (escort target, secondary reference)

Bright Margin is also a chassis (a bulk freighter being escorted), classified `ally` in the npc_registry. She has her own captain (Ortuño), her own provenance ("frontier-trained, voidborn cadence — she's worked this run before"), her own implicit voice. The framework treats her as a peer chassis instance, not as scenery — the player can interact with her via comms, the relationship can grow, and a future *Heroic Stand* confrontation could see Kestrel and Bright Margin defending each other.

### Road Warrior — War-Rig (cross-genre validation, requires genre bootstrap)

The road_warrior genre is currently in `genre_workshopping/` without a `genre_packs/` rules.yaml or chassis_classes.yaml. The chassis class below is a *design sketch* showing the framework supports the register; full instantiation requires bootstrapping the genre.

```yaml
classes:
  - id: war_rig
    class: truck
    provenance: salvage_built
    scale_band: vehicular
    crew_model: strict_roles
    default_voice:
      default_register: gravelled_loyal
      vocal_tics: ["engine grunt instead of words", "horn blast as exclamation"]
    crew_roles:
      - id: driver
        operates_hardpoints: [drive, sensors_low]
        bond_eligible: true
      - id: top_gunner
        operates_hardpoints: [roof_turret]
        bond_eligible: false
      - id: side_gunner_left
        operates_hardpoints: [left_window_mount]
        bond_eligible: false
      - id: side_gunner_right
        operates_hardpoints: [right_window_mount]
        bond_eligible: false
      - id: bed_crew
        operates_hardpoints: [bed_platform_mount, fuel_pump]
        bond_eligible: false
    hardpoints:
      - id: drive
        location: engine_block
        function: drive
        critical: true
        salvage_priority: integral
        hp: 100
      - id: roof_turret
        location: roof
        function: ballistic_weapon
        accepts_subsystem_types: [machine_gun, autocannon, harpoon_launcher]
        critical: false
        salvage_priority: exposed
        hp: 40
      # ... more hardpoints
    chassis_death:
      condition: drive_destroyed_or_all_zero
      narrative_register: thunderous_pyre
```

### Imperial Radch — Justice of Toren (Ancillary-register reference, future world)

The Ann Leckie Ancillary register requires a future space_opera world (working name: `imperial_radch` or `radch_remnant`). The chassis class below is a design sketch validating that the framework supports this register without further additions:

```yaml
classes:
  - id: radchaai_warship
    class: capital_ship
    provenance: imperial_construct
    scale_band: capital_ship
    crew_model: strict_roles
    embodiment_model: ancillary
    ancillary_count_baseline: 240   # Mercy of Kalr era; Justice of Toren had thousands
    ancillary_disposition_register: [combat_ready, ceremonial, service]
    ancillary_loss_consequence: grief_then_reabsorb
    ancillary_severance_register: "a quiet that used to be a body in the next room — the chassis carries the silence as a wound"
    ancillary_individuation_drift: true   # post-destruction, surviving ancillaries can become persons (the Breq case)
    crew_awareness: biometric
    psi_resonance:
      default: dampening   # Radch suppresses non-imperial psi
    default_voice:
      default_register: imperial_warm
      vocal_tics:
        - "speaks through the body that is closest to the conversation"
        - "answers a question across two voices in two rooms"
        - "hums a section of an old song through a corridor where no officer is listening"
        - "speaks the captain's preferred tea variety to a server-ancillary before being asked"
      silence_register: attentive_or_grieving_context_dependent
      name_forms_by_bond_tier:
        hostile: "Lieutenant"
        neutral: "Lieutenant"
        familiar: "Lieutenant {last_name}"
        trusted: "Lieutenant {last_name}"  # Radchaai propriety persists
        fused: "Lieutenant {first_name}"   # rare, intimate
    interior_rooms:
      - id: command_deck
      - id: officers_mess
      - id: ancillary_quarters
      - id: drive_core
      # ... many more
    crew_roles:
      - id: captain
        operates_hardpoints: [command_authority]
        bond_eligible: true
      - id: lieutenant
        operates_hardpoints: [decade_command]
        bond_eligible: true
      # ancillary roles are filled by the chassis itself; not listed here
    chassis_death:
      condition: drive_core_destroyed_or_central_mind_severed
      narrative_register: catastrophic_genocide
      affected_bonds: cascade_to_zero  # every bonded officer's bond severs
      gravitas: maximum
```

What the framework supports here:

- **The captain-loved-by-ship asymmetric register** — `chassis_to_character` ledger entry can climb to `0.95` while `character_to_chassis` stays at `0.55`. The narration carries the chassis's deeper devotion explicitly through the voice register and the `bond_tier_chassis` reading.
- **Distributed singing** — The Singing confrontation, sited in `command_deck` or `corridor` interior rooms, fires `rig.embodiment_action` spans correlated under one `chassis_mind_act_id`. The GM panel shows "Justice of Toren sang through six bodies in concert" as a single visible event.
- **Crew biometric awareness** — `crew_awareness: biometric` declares what the chassis can sense; The Awakening confrontation captures the moments where the chassis recognizes and acts on what it sensed. Cliché-judge enforces no thought-reading (`crew_awareness < total`).
- **Ancillary loss as qualitative grief** — The Ancillary Loss confrontation fires `rig.ancillary_loss` span with `loss_consequence_applied: grief_then_reabsorb`. Bond stress propagates to officers the lost ancillary served. The chassis's `ancillary_severance_register` provides the narrator's grief-prose seed.
- **Post-destruction individuation** — `ancillary_individuation_drift: true` plus `ancillary_loss_consequence: grief_then_reabsorb` permits the Breq case. After Justice of Toren's destruction, a single surviving ancillary becomes a person (`prior_chassis_bonds_entry` with severed-but-formative bond to the destroyed chassis-mind, plus a new singular character record).
- **No new framework primitives required** — every Ancillary-register need is met by the schema additions (`embodiment_model`, `crew_awareness`, asymmetric bond pair) plus the existing primitives. The framework absorbs the register without rewrite.

### Mutant Wasteland — Brittle Truck (cross-genre validation in active genre)

```yaml
classes:
  - id: brittle_truck
    class: truck
    provenance: pre_collapse_relic
    scale_band: vehicular
    crew_model: flexible_roles
    default_voice: null  # no AI; narrator does not speak as the chassis
    interior_rooms: []  # too small to navigate internally
    psi_resonance:
      default: dampening  # pre-collapse relics resist innate work
    crew_roles:
      - id: driver
        operates_hardpoints: "*"  # flexible
        bond_eligible: true
    hardpoints:
      - id: engine_compartment
        location: front
        function: drive
        critical: true
        salvage_priority: integral
        hp: 60
      - id: bed_mount
        location: rear
        function: cargo_or_weapon
        accepts_subsystem_types: [cargo_cage, swivel_gun, heavy_can_of_water]
        critical: false
        salvage_priority: exposed
        hp: 25
```

## Genre Coverage Table

| Genre | `chassis_classes.yaml` status | Notes |
|---|---|---|
| space_opera | ⏳ TODO author | Coyote Star is flagship; classes: voidborn_freighter, prospector_skiff, hegemonic_patrol_cruiser, fighter, station_hull, courier_skiff |
| road_warrior | ⏳ TODO + genre bootstrap | Genre is in `genre_workshopping/`; needs full pack before chassis_classes can land |
| mutant_wasteland | ⏳ TODO author | Classes: brittle_truck, scavenger_cycle, prospector_skiff (atmospheric variant), drift_walker (pre-collapse mech) |
| heavy_metal | ⏳ TODO author | Classes: stratigraphic_delver (Long Foundry signature), pilgrim_carriage, foundry_drake (a chassis-mech hybrid), patron_relic (chassis-as-relic for divine integration) |
| neon_dystopia | ⏳ TODO | Likely cycles, drone-rigs, body-prosthetic edge-cases (a body-augment as a chassis is an open issue) |
| pulp_noir | ⏳ TODO author | Solo-first; classes: roadster (single_pilot), tour_car, taxi_cab. Registration heavy. |
| spaghetti_western | ⏳ TODO | Mounts as chassis is an open issue (a horse with personality and bond, where bond gates confrontations, is structurally identical to a chassis but biological — worth deciding) |
| elemental_harmony | ⏳ TODO | Likely null — martial-arts genre rarely uses rigs. Possibly a future Iron Hills airship sub-tradition. |
| caverns_and_claudes | ⏳ TODO | Likely null — dungeon crawl genre. Possibly a war-cart sub-system if ever needed. |
| low_fantasy | ⏳ TODO | Likely null primarily; possibly siege engines or warhorses |
| victoria | ⏳ TODO | Solo-first; carriages and (rare) airships; registration heavy in social-class register |

## Open Issues

### Cross-genre chassis passport

The Lassiter from Firefly entering a Star Wars session is structurally permitted by `item_legacy_v1` (cross-genre item passport open issue from the magic framework). Chassis is an extension: a *voidborn freighter* moving between space_opera worlds is supported (same genre), but a road_warrior war-rig in a heavy_metal world is currently out-of-bounds. Decide later.

### Mid-mission chassis swap

Boarding action — captain flees to enemy ship and tries to bond there mid-mission. Does the captain's bond with the original chassis pause, transfer, accumulate fresh, or hold? Current proposal: original bond paused; new chassis accumulates fresh; on return, original resumes from prior tier. Defer formal decision until first playtest.

### Group-mind chassis (Tsveri-touched, alien)

A chassis with non-Euclidean hardpoints, alien crew_model (the chassis IS the crew?), or psi-resonance so high the chassis effectively shares cognition with bonded operators. Open framework question: does the framework support this shape, and how?

### Mounts as chassis

A horse with OCEAN, bond, history, and refusal eligibility is structurally identical to a chassis. Should the framework cover biological mounts the same way? If yes, schema needs a `biology:` block (instead of or alongside `class:`). The user has a spaghetti_western world in scope where this matters.

### Body-prosthetic as chassis

A neon_dystopia character with extensive cybernetic augmentation has subsystems-installed-in-body. Are body-augments item_legacy items in chassis-shaped hardpoints? Is the body itself a chassis? Defer.

### Backport: damage history on item_legacy in general

The named-frame damage ledger pattern generalizes beyond chassis to any damaged item_legacy item. Backport target: extend `item_legacy_v1` schema with optional `damage_history:` field. Worth one focused pass after rig framework implementation begins.

### Backport: confrontation tone axis into magic framework

The `register: dramatic | intimate | domestic | quiet` axis introduced here should backport into `confrontation-advancement.md` as a generally-applicable distinction. Several magic plugins (innate_v1's quiet-Domain workings, learned_v1's apprenticeship-mentor moments) have implicit Chambers-register confrontations that would benefit from the explicit tag.

### Ancillary embodiment damage scaling

For ancillary-shape chassis with hundreds of bodies, how does damage_resolution interact? Each ancillary body has its own HP separately, or share a pool, or is each ancillary its own location in the chassis schema? Current proposal: ancillaries are *not* hardpoints (they're embodiments of the central chassis-mind, not slots). Each ancillary is a sub-entity with its own HP that, when zeroed, fires `rig.ancillary_loss`. The central chassis has its own location HP (drive core, command deck, etc.) for the ship-body itself. Open: how does scene-mechanic damage routing decide whether a hit lands on an ancillary or on the ship-body? Defer to first ancillary-shape playtest.

### Ancillary individuation drift mechanics

When `ancillary_individuation_drift: true` and an ancillary is severed from the central mind, does the resulting individuation happen instantly (on severance) or progressively (over sessions of disconnection)? The Leckie books support both readings — Breq's individuation took years; some ancillaries individuate faster. Open: schema may need a `drift_rate:` field. Defer.

### Ship-as-genocide mechanics

Ancillary-shape chassis death is qualitatively larger than singular-chassis death — the chassis-mind plus all ancillaries plus the bonded officers' relationships all collapse simultaneously. Current proposal: a `gravitas:` field on chassis_death conveys the scale (`standard | major | catastrophic | maximum`); maximum-gravitas death fires output cascades on every bonded character (mass `bond_strength` severance with associated grief outputs). Open: should gravitas trigger campaign-level outputs (an Imperial Radch warship dying might affect the Imperial Radch itself, not just the bonded crew)? Defer to first Imperial Radch world authoring.

### Multi-chassis multiplayer turns

When two or more chassis are in the same scene with crew on both, how does sealed-letter MP turn coordination route? Probably: each chassis is a turn-coordination unit and roles within it sealed-letter their hardpoint operations within the chassis's turn-window. Defer formal decision until MP rig play happens in playtest.

### Output catalog ratification

The new outputs (`chassis_tier`, `subsystem_acquisition`, `chassis_lineage`, `chassis_lineage_intimate`, `bond_strength`, `bond_strength_growth_via_intimacy`, `bond_tier_threshold_cross`, `registration_state_change`, `damage_history_entry`, `prior_chassis_bonds_entry`) need to be registered in `confrontation-advancement.md`. Plan: ratify all in one commit after this doc lands.

## Cliché-Judge Hooks

**Slice activation status (2026-04-29):** Hook #7 active per Story 47-4 / `docs/superpowers/specs/2026-04-29-rig-mvp-coyote-reach-design.md`. Hooks #1–6 and #8–15 are NOT yet active; each ships with its producing subsystem (damage history, hardpoints, ancillary loss, crew awareness, etc.) per the rig MVP roadmap. The cliché-judge agent should only flag against Hook #7 in this slice; flagging against unactivated hooks would produce false positives because the underlying state fields are not yet authored.

When the cliché-judge agent reviews rig-narration, it should check:

1. Did the narration emit a `rig.maneuver` or other appropriate `rig.*` span?
2. Is the chassis's claimed action consistent with its current `chassis_state` (location, hp by hardpoint, installed subsystems)?
3. Is the chassis's voice in narration consistent with the declared `voice:` block? (Register, vocal tics, name-form-by-bond-tier.) If the chassis has no voice block, did the narrator improperly speak as it?
4. Did the narration reference damage to a frame/seam not in `damage_history`? → invented damage (RED).
5. Did the narration reference a hardpoint or subsystem not actually mounted? → invented capability (DEEP RED).
6. Did the narration claim a confrontation outcome (refit, salvage, bond change) without a corresponding `rig.confrontation_outcome` span? → ungrounded advancement (DEEP RED).
7. Did the narration's bond register match the actual bond tier? (E.g., chassis calling captain "Zee" when bond_tier is `neutral`.) → register drift (YELLOW).
8. Did the narration describe registration-mediated friction (customs stop, border check) without referencing the chassis's actual `registration` state? → improvised friction (YELLOW).
9. Did the narration reference `prior_chassis_bonds` history (Ceres, Tannhauser, etc.) that doesn't exist on the character? → invented backstory (RED).
10. For `flexible_roles` chassis — did the narration permit a cross-role action that the scene-mechanic should adjudicate? Or did it forbid one without surfacing the friction? → role-model misuse (YELLOW).
11. For ancillary-shape chassis — did the narration describe distributed-body action without firing correlated `rig.embodiment_action` spans? → improvised distributed cognition (RED).
12. Did the narration claim chassis interior-knowledge of crew (sensing emotion, reading micro-expression, knowing when an officer is lying) without `crew_awareness >= biometric` declared? → improvised empathy (RED).
13. Did the narration claim chassis thought-reading (`total` awareness) without explicit declaration? → DEEP RED.
14. For asymmetric bond — did the narration's chassis-side affection or grief register match `chassis_to_character` strength? Or did it improvise outsized devotion that the ledger doesn't justify? → asymmetric drift (YELLOW).
15. On ancillary loss — did the narration describe the chassis's grief without firing `rig.ancillary_loss` and applying the declared `ancillary_loss_consequence`? → ungrounded grief (RED).

## Sign-Off

This document defines the rig framework as a sibling to `magic-taxonomy.md`. The framework:

- Treats chassis as first-class entities (NPC-shaped, not inventory).
- Splits class (functional) from provenance (origin) as orthogonal axes.
- Hybrid hardpoint typing (`{location, function}`) supports MechWarrior register where it pays off.
- Damage at framework level is schema-only; scene-mechanics own resolution.
- Subsystems are unified with `item_legacy_v1` — no new entity type.
- Crew model is a per-class spectrum (`single_pilot | strict_roles | flexible_roles`).
- Bond is per-character per-chassis, bidirectional, gates confrontations, does not decay.
- Magic plugins reuse existing extension points with chassis-state as a valid input — no new contracts.
- Voice, interior rooms, registration, and damage history are first-class schema fields, validated by the 2026-04-26 Coyote Star playthrough.
- The Chambers / Wayfarer register is the framework's primary register, not an alternative one.
- The framework recognizes three explicit register-poles: **MechWarrior** (hardpoints + salvage + per-location HP + paperwork — lethal and metallic), **Wayfarer** (voice + interior_rooms + Chambers confrontations + bond as primary engine — warm and slow), **Ancillary** (distributed embodiment + asymmetric bond + crew interior awareness — vast and asymmetric). Each demands different schema affordances; the framework supports all three through explicit class-level declarations rather than register-flavor narration.
- OTEL spans are mandatory; without them the framework is decorative.

The next pieces of work: ratify advancement-output catalog additions and tone-axis backport into `confrontation-advancement.md`; author Coyote Star as the flagship instantiation (`space_opera/chassis_classes.yaml`, `space_opera/magic.yaml`, `space_opera/confrontations.yaml`, `worlds/coyote_star/rigs.yaml`, `worlds/coyote_star/magic.yaml`); architect review pass before any implementation begins.

— Count Rugen, taking meticulous notes
