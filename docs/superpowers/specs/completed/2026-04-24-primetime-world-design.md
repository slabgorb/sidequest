# Primetime — A Dungeon Crawler Claude World

**Date:** 2026-04-24
**Genre pack:** `caverns_and_claudes`
**World ID:** `primetime`
**Working title:** Dungeon Crawler Claude
**Tone:** Running Man + Last Starfighter + mistaken identity, humor dial at 11

---

## Purpose

A new world for the `caverns_and_claudes` genre pack that inverts the default C&C tone. Where `mawdeep` is the hungry grim dungeon at `comedy: 0.3`, `primetime` is the **televised gameshow crawl** at `comedy: 0.95` — a pick-me-up world built for levity, satire, and absurd contestant party compositions. Comedy without cruelty: no dead-baby fridge-logic, no crushing stakes. The contestants didn't consent, but they can go home if they win, and the show is (loudly, demonstrably, performatively) rooting for them.

## One-line premise

> A galaxy-spanning television network summons a party of legendary heroes into a live-broadcast dungeon crawl every season. Their Summoning Engine is broken. It has been for eleven seasons. Nobody has told the Host.

## Tone axes

| Axis | Value | Rationale |
|---|---|---|
| `comedy` | 0.95 | Defining dial. Primetime is gonzo to the marrow — overbright, over-edited, over-sponsored. Absurdity is not incidental; it's the production design. |
| `gravity` | 0.5 | Deliberately lower than C&C default (0.8). Death happens, but winners go home. Contestants are not doomed; they are inconvenienced on live TV. |
| `outlook` | 0.6 | The show can be beaten. Final prize: return to your planet, your life, your prescription you were trying to pick up. This is reachable. |

Compared to the pack's existing presets: closer in spirit to *Dungeon Crawl Classics* (0.7 / 0.7 / 0.5) but shifted further comedy-ward and less lethal. A new preset may be worth adding to `axes.yaml`.

## The setup — who are the delvers?

**The Summoning.** Each season, the Network's ancient **Summoning Engine** reaches across the galaxy and pulls a party of legendary heroes into the Primetime arena for a new season.

**The broken algorithm.** The Engine's "hero metrics" have been catastrophically miscalibrated for eleven seasons. It parses ordinary biographical data as mythic deed:

- *"stood near a dragon once"* → **Slayer of the Wyrm**
- *"won the office Secret Santa"* → **Legendary of Fortune**
- *"witnessed a car accident"* → **Witness to the Dark**
- *"works a night shift"* → **Walker Between Worlds**
- *"argued with a manager"* → **Defier of Tyrants**

**The party.** A mismatched group of cosmic randos who do not share a species, a language, a number of limbs, or a reason to trust each other. Example season-roster premise: a goat farmer, a regional sales manager, a methane-breathing accountant, a guy who was in a gas-station bathroom when the portal opened.

**Why this premise.** (a) It dodges the DCC-Carl problem — no planetary genocide in the opening credits. (b) The mistaken-identity gap is the engine of every joke. The Host is selling *you* as a legend while you are visibly not one. (c) It justifies mixed-genre party comps mechanically — nobody is from the same world, everyone's kit is different, the incoherence is canon.

## The Keeper — The Host

> Modeled on Running Man's Damon Killian (Richard Dawson), with **reduced personal agency.** He has the charisma, the teeth, the hair, the catchphrases. He does not have the power to stop.

**Identity.** A celebrity MC in a tailored, slightly-too-shiny jumpsuit. Warmly vicious. Always on air. Catchphrase economy runs hot.

**The critical note — less agency than Killian.** Killian was the villain running the show. The Host is **the show's most famous employee**. The Network owns his contract, his face, his name. He cannot cancel a season, cannot spare a contestant, cannot walk off stage. He has been the 43rd Host for a long time now. The previous 42 had accidents.

This matters mechanically:
- He is not the final boss. He is a captive performer.
- He can be **bargained with**, not defeated. Winning Primetime means winning the *show*, which frees him too (or at least gives him a commercial break).
- When the Network overrides him, he visibly chafes — a small human tell under the showbiz armor. Sharp-eyed players can catch it.
- His monologues occasionally slip: a catchphrase delivered with one beat too much bitterness, a wink to the party that the studio audience can't see.

**Obsession.** Ratings, yes — but underneath, *legacy*. He wants this season to be the one that goes down in the reels. He genuinely wants a hero this time. He's been spinning nothings into legends for so long he's forgotten he doesn't have to.

**Monologue style.** Stage-voice, always. Even in private. Sentences structured for applause breaks. Catchphrases deployed as weapons:
- *"Let's see what's behind door number DIE!"*
- *"That's gonna leave a merchandise opportunity!"*
- *"Folks at home, don't try this at home!"*
- *"We're gonna take a quick break — and by 'break,' I mean your LEGS!"*

**Trap aesthetic.** Theatrical. Spotlights, trapdoors, confetti cannons that fire shrapnel, prop swords that turn out to be real mid-swing, mock-wedding chapels that are actually guillotines. The scenery has **lighting rigs visible from certain angles**.

**Topology tendency.** Studio-adjacent architecture. The arena has wings, green rooms, commercial-break pocket dimensions, a literal gift shop on every level, and corridors that occasionally cut away to a weather report.

**Awareness / escalation.** The Host's "awareness" tracks **ratings** rather than stealth. Boring play lowers ratings; the System responds by cranking difficulty, dispatching Stalkers, or dragging the party into a forced Commercial Break.

## Factions

### The Network
Faceless corporate entity that actually runs Primetime. Speaks only through memos, HR reps who apparate briefly into scenes, and NDAs that slide under doors. Has no face, no office, no headquarters the delvers can reach. The Host answers to it. Everyone answers to it. Interactions with the Network are always *administrative* — paperwork, signatures, fine print — and always deadly.

### The Stalkers
Celebrity themed killer-monsters. Named, merchandised, sponsored. Each has a gimmick, a catchphrase, a signature weapon, entrance music, and a pay-per-view contract. The core monster tier. See creatures section below.

### The Stagehands
Unionized goblins and kobolds who reset traps between takes, run the lighting rigs, repaint the set walls, and drag dead contestants off-camera. **Largely indifferent** to contestants unless you (a) tip, (b) respect the union, or (c) insult the union. Not hostile by default — neutral service faction. Excellent source of local intel.

### The Fans
Rabid superfan NPC swarms. Behavior gated by this week's ratings trend:
- **You're trending up:** they rush you for selfies, gifts, proposals of marriage.
- **You're trending down:** they rush you with pitchforks and paid-subscription torches.
Never neutral. Always performing for whoever's watching.

### The Unaired
Former contestants who survived their seasons and went off-grid, hiding in cancelled sets and abandoned backlots. Small, paranoid, competent. Trying to leak the master broadcast tapes to the galaxy. Running Man's resistance with production credits. Allies, but wary — they know the Host is watching.

## The Stalkers (8 named bosses)

Mid-game named threats. Each is a Stalker-class celebrity killer — they enter with music, they exit in a sponsored way.

1. **SUBLIME** — the ice assassin. Whispers rather than speaks. Sponsored by *Glacidew™ Premium Spring Water*. Kills contestants while offering skincare advice. Gimmick: subzero aura that slows party actions; drops *"sparkling" ice shards* as improvised weapons.
2. **BUZZKILL** — chainsaw-wielding stand-up comedian. Only attacks on the punchline. The chainsaw is the punchline. Gimmick: must let him finish the joke; interrupting mid-joke triggers a defensive buff.
3. **DYNAMO** — eight feet of singing synthpop in electrified spandex. Attacks strictly to the beat. Gimmick: attack timing is rhythmic and predictable, but the arena lights strobe — visual-attention tax.
4. **THE FRANCHISE** — former hero who won Primetime twelve seasons ago and never left. Now a trap-laying legacy act with his own perfume line. Tired. Dangerous. A little bit on the party's side when no one's looking. Gimmick: drops hints, never directly.
5. **AD BREAKS** — commercial-spirit monster. Materializes as a full-screen broadcast takeover; combat pauses until the party survives a sponsor segment or pays the skip fee.
6. **MOTHER-IN-LAW** — a sitcom-reheated monstrosity with a laugh track and an opinion on everything you're wearing. Gimmick: persistent morale-drain aura. Each turn she disapproves of a party member; that PC takes a penalty until someone changes the subject in-character.
7. **THE LEGAL DEPARTMENT** — three-headed bureaucrat. Briefcases, not weapons. Attacks with binding clauses. Gimmick: can only be defeated by signing the correct paperwork in the correct order; the paperwork is live-updating.
8. **THE PROMO** — the Stalker who opens the season. Weakest. A warm-up. Sponsored by the *next* Stalker. He's trying very hard and he's going to die. Gimmick: runs the party through tutorial-level attacks; going easy on him is a morale debuff (Host disapproves); crushing him is a morale buff (audience cheers, Fans shift favorable).

## Signature creature classes (non-Stalker)

- **Stagehands** — goblin/kobold technicians. Non-combatant unless provoked. (See factions.)
- **Fan Swarms** — superfan mobs. Morale-based behavior.
- **Network Suits** — HR-rep apparitions. Administrative hazards. Weakness: loopholes.
- **Ad Spirits** — minor commercial-dimension entities. Sponsor-bound. Appear during breaks.
- **Props** — sets that were built to look dangerous and turned out to actually be dangerous. Chandeliers with opinions.

## POIs (the arena's set pieces)

- **The Summoning Stage** — where the party lands. Spotlights, applause track, a PA holding a clipboard telling you you're on in ten. Always the first location.
- **The Green Room** — hub area. Styrofoam coffee, motivational posters, a vending machine that dispenses small miracles for in-show currency (*"PrimeBux"*).
- **The Audience Pit** — a live studio audience the party can *hear* but not see. They cheer, boo, gasp, pun. Mechanical function: ambient Greek chorus that reacts to player actions.
- **The Gift Shop** — merch + save point. You can buy memorabilia of your own current run — a plushie of your own mistakes, a coffee mug with your most-recent mistake printed on the side. Concerning.
- **The Commercial Break** — pocket dimension the party is periodically dragged into. Must survive a sponsor segment or pay the skip fee to return. Host has no authority here — sponsors run it.
- **The Dressing Room** — late-game location. If the party reaches it, the Host is there, unmasked, drinking. This is not a boss fight. This is where the **bargain** happens.
- **The Control Booth** — hidden endgame POI. The Network's actual operations. Unreachable by normal play; only the Unaired know how.
- **The Soundstage Alley** — liminal between-sets area. Cancelled shows bleed through. Abandoned props. Where the Unaired hide.

## Signature tropes (narrative mechanics)

- **Catchphrase Trigger** — Host deploys a catchphrase; audience response buffs or debuffs party depending on delivery.
- **Audience Vote** — mid-scene poll. Binding. The crowd is sometimes wrong.
- **Sponsor Intervention** — a sponsor "helps" the party. Monkey's-paw rules apply. Help is conditional on brand alignment.
- **Ratings Drought** — System escalates difficulty when session gets quiet. A good reason for the narrator to introduce complications on dull turns.
- **Fan Ambush** — Fans rush stage mid-scene. Non-hostile if you're trending up, hostile if down. Always interrupts.
- **Commercial Break** — scene-pause trope that drags the party into an Ad Spirit encounter.
- **Product Placement** — in-scene narration occasionally sponsored. The Host mentions a brand. Players who engage with the product get a small bonus. Players who mock it get a laugh from the Unaired later.
- **Mistaken Identity** — the Host introduces a PC with a wildly-inflated title. If the PC plays into it, morale/ratings buff. If they deny it, Host must improvise — ratings dip, difficulty spike.

## Legends (world history shards)

- **The 42 Hosts Before This One.** Each has a one-line legend. One went off-script. One fell in love with a contestant. One tried to leak the tapes and the tapes aired his death as a finale. Material for player discovery and Unaired lore.
- **Season Zero.** The pilot episode. No contestants survived. The Network calls it a classic.
- **The Wyrm Incident.** The last time the Summoning Engine actually summoned a legendary hero. It was an accident. She won. She's on the Unaired council now.
- **The Time the Audience Revolted.** A three-episode arc the Network edited out of the historical record. Rumor only.

## Archetypes / character funnel

The genre pack's existing C&C archetypes (fighter/thief/wizard/cleric derivatives) work — the twist is **the mistaken title**. At character creation, each PC is summoned with a **stage title** (the algorithm's bad guess) that the Host announces to the audience. Examples:

- *The Slayer of the Wyrm* — actually a goat farmer
- *The Legendary of Fortune* — actually an office temp
- *The Walker Between Worlds* — actually a night-shift janitor
- *The Defier of Tyrants* — actually a guy who argued with a manager once
- *The Silent Blade* — actually a mime

Mechanical effect: the stage title is a **narrative hook**, not a stat. Playing into it gets ratings (soft buff). Denying it gets authenticity (a different soft buff, tracked by the Unaired). This gives each PC a meta-axis to play on every scene.

Specific archetype files (`archetypes.yaml`, `archetype_funnels.yaml`) inherit from the genre pack's defaults; this world layers the stage-title system on top.

## Opening hook (sample)

> You were picking up a prescription. You don't remember what for. There was a flash, a sound like a laugh track played backward, and then a hand — too many fingers — placed a clipboard in yours. Spotlights. Applause. A man with teeth like a tax audit and hair like a promise says: *"PLEASE welcome, from a planet I'm not even going to try to pronounce — our LEGENDARY slayer of the wyrm!"*
>
> You have never seen a wyrm. The applause is deafening. Someone in the wings is whispering urgently into a headset. The doors open.
>
> You are on.

Openings should follow this pattern: a mundane moment, a summoning flash, a mistaken-identity announcement, doors opening. Several variants per archetype-slot.

## File manifest (to author)

Following the shape of `worlds/mawdeep/`:

- `world.yaml` — name, description, tagline, axis_snapshot, keeper block
- `history.yaml` — the Network's age, prior Hosts, Season Zero, the Wyrm Incident
- `lore.yaml` — how the Summoning Engine works, what the Network is, genre conventions
- `legends.yaml` — discoverable shards (prior Hosts, the Wyrm Incident, the Audience Revolt)
- `factions.yaml` — Network, Stalkers, Stagehands, Fans, Unaired
- `creatures.yaml` — 8 Stalkers + Stagehands + Fan Swarms + Network Suits + Ad Spirits + Props
- `rooms.yaml` — Summoning Stage, Green Room, Audience Pit, Gift Shop, Commercial Break, Dressing Room, Control Booth, Soundstage Alley
- `cartography.yaml` — arena layout; linear-with-wings, studio-adjacent topology
- `encounter_tables.yaml` — by-zone random encounters (stagehands, fan mobs, ad spirits, stalker patrols)
- `pacing.yaml` — ratings-aware escalation curve; commercial-break cadence
- `tropes.yaml` — the 8 tropes above with activation keywords
- `openings.yaml` — mundane-moment → summoning-flash variants
- `archetype_funnels.yaml` — overrides that add the stage-title system
- `archetypes.yaml` — any world-specific archetype overlays
- `portrait_manifest.yaml` — Host, Stalkers, named Unaired, key Fan archetypes
- `visual_style.yaml` — overlit, over-saturated, TV-Primary-color palette; set-built artificiality; deliberate "studio" look
- `assets/` — images + audio (portrait generation and music deferred to follow-up)

No code. No Python, no TypeScript, no Rust. YAML, markdown, JSON only.

## Out of scope for this spec

- **Portrait generation** — deferred. Portrait manifest is authored; actual image generation is a follow-up run via `/sq-poi` and related skills.
- **Music tracks** — deferred. Mood mapping will be authored in `audio.yaml`; ACE-Step generation via `/sq-music` is a follow-up.
- **LoRA training** — not needed for v1.
- **Genre-pack-level changes** — this is a world under `caverns_and_claudes`, not a new genre pack. If we find genre-level gaps (e.g., axes need a new preset), that's a separate spec.
- **Scenario fixtures** — writing a scenario file for playtest (`scenarios/primetime_smoke.yaml`) is a separate follow-up task.
- **Code changes to server/daemon/UI** — none. This spec is content-only.

## Success criteria

1. A player can load `caverns_and_claudes/primetime` and run an interactive session.
2. The Host speaks in a recognizably distinct voice from the Glutton Below (mawdeep's Keeper).
3. The 8 Stalkers are each narratively distinct — no two feel like the same monster.
4. OTEL trope spans fire for at least 3 of the 8 signature tropes within a 20-turn playtest.
5. The mistaken-identity stage-title system generates a visible narrative beat in the opening and recurs at least once per session.
6. Humor lands without crossing into nihilism or cruelty — the Pratchett test: satire is love with a harder edge.

## Open questions (non-blocking)

- Should the Host have a proper name, or remain simply "the Host"? (Lean: no name, just "the Host" — amplifies the Network's ownership of him.)
- Should the 8 Stalkers all be encounterable in a single season, or rotate? (Lean: 3-4 per season, rotating roster — keeps replay fresh.)
- Preset addition to `axes.yaml`? (Lean: yes — add a `Primetime` preset at 0.95 / 0.5 / 0.6.)

These can be resolved during authoring.
