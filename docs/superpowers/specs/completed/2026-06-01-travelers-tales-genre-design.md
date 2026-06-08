# `wry_whimsy` ("Wry Whimsy") Genre + Oz World — Design Spec

**Date:** 2026-06-01
**Author:** GM
**Status:** Approved — decisions locked (genre name, era, workshop-first); proceeding to plan
**Scope:** New genre pack **`wry_whimsy`** (genre-level chassis) + the **Oz** world authored to full playable depth. Wonderland and Gulliver are named in the genre with one-paragraph identities each; they are authored deep in later passes.

**Locked decisions:** Genre name **Wry Whimsy** (`wry_whimsy`) · Oz era **Wizard-era, everything primed** (matriarchal/Ozma/Jinjur payload seeded latent) · Author in **`genre_workshopping/wry_whimsy/`** first.

---

## One-line distillation

> **The golden-age literary portal fairytale:** a sensible traveler from the ordinary world crosses a threshold into a Secondary World run on dream-logic, survives its impossible authorities by wit and nerve, and wanders a place that refuses to make sense. Three public-domain worlds span one chassis across a deliberate light → savage gradient.

---

## 1. Genre identity

A traveler from the mundane world (Dorothy, Alice, Gulliver) is dropped into a fantastical Secondary World, sealed off from home, governed by dream-logic and populated by talking creatures and absurd authorities. Episodic, whimsical, with an undertow of real menace. The protagonist is always a **visitor**, never a native — the only sensible person in a place that runs on nonsense, and the comedy and the horror both come from the world being earnestly *itself*.

All three source corpora are public domain:

| World | Author / year | Tonal position | Lethality dial |
|-------|---------------|----------------|----------------|
| **Oz** | Baum, 1900–1920 (14 novels) | **Light** — earnest American fairytale; the world wants you to win | Low |
| **Wonderland** | Carroll, 1865 / 1871 | **Funky-dark** — nonsense logic as antagonist; capricious cruelty | Medium |
| **Gulliver** | Swift, 1726 | **Savage** — satire with teeth; the absurd society judges *you* | High |

Same rulebook; **the world sets the lethality dial and tone axes.** This is the SOUL principle "Crunch in the Genre, Flavor in the World" doing exactly its job. Gender also runs as a live current across the gradient: **Oz is female-governed (male power is humbug)**, **Wonderland is ruled by a capricious Queen who out-tyrants her do-nothing King**, **Gulliver is savagely male court-politics**.

**Genre name (locked):** **Wry Whimsy** (`wry_whimsy`) — dry wit riding with the whimsy; telegraphs the light→savage gradient.

---

## 2. Play doctrine (drives `prompts.yaml` / narrator guardrails)

Four principles. These are the genre's narrator contract.

1. **Diegetic sincerity — never wink.** Render the world *as the book means it*, dead straight. The humor and horror emerge from the place being earnestly itself, not from the narrator commenting on it. A talking Scarecrow worries he has no brains while being the cleverest one in the room — played straight, not snarked.

2. **The seams are bait, not walls.** Every book has a built-in "the emperor has no clothes," and these are **findable, never protected**. Point at the curtain and the Wizard *is* a humbug, full stop — that's canon (Toto pulls it in ch. 15), not a twist the narrator guards. Player insight is rewarded with truth, because the truth is in the book. This is "Yes, And" meeting "Living World."

3. **A place, not a plot.** The design target is sandbox — "wander around and fuck around." Content is a dense, reactive place: every famous location is a POI you can walk into, every famous character is an NPC running their canonical goal. This leans **away** from the scenario / belief-graph clue system and **toward** Living-World density + Diamonds-and-Coal. The campaign emerges from play.

4. **Baum's Oz, not Hollywood's.** Genre-honesty is the anti-cliche weapon. The failure mode is generic-fairytale-MGM mush (Claude's cliche reflex). Playing it straight *within the source text* — **silver** shoes not ruby, the four colored countries, the Hammer-Heads, the Dainty China Country, the green-spectacles humbug — *is* the reference-stacking that drops content below the cliche granularity wall. We render the 1900 novel and W.W. Denslow's plates, never the 1939 film.

### On the author

Baum was genuinely progressive on gender (his mother-in-law was the radical suffragist Matilda Joslyn Gage) **and** wrote two 1890–91 newspaper editorials advocating the genocide of Native Americans. Both are real and neither cancels the other. We adapt **Oz, not Baum** — the editorials live entirely outside the fiction. Standard "Lovecraft rule": render the world, leave the author at the door, and if it ever comes up, say the true thing plainly. This does not touch a single content decision.

---

## 3. Mechanical chassis (genre-level crunch — Keith's lane)

**Ruleset binding:** `native` (no custom module — fully authorable as content).

**Core resolution is wit/composure-first.** The danger in these worlds is absurd authority, dream-logic, and not-getting-eaten — resolved by nerve and cleverness far more than by swords. Physical violence exists but is the exception.

### Composure as the lethality substrate

Instead of HP-to-death, the tracked ablative pool is **Composure** — your grip on yourself in a world built to unmake it. Modeled on the native HP/lethality substrate (per the ablative-HP work), reskinned: when Composure is exhausted you don't die — you **break**. Breaking resolves as panic, flight, being condemned, enslaved, enchanted, or surrendering. **The world's lethality dial sets whether a break is recoverable** (Oz: almost always) or terminal (Gulliver: often).

### Confrontation defs (the Bang catalog)

Genre-level ConfrontationDefs, each resolving on nerve + wit against Composure:

- **Audience / Trial** — facing an impossible authority (the Wizard's throne, a witch's bargain, the Queen's court). Break = you accept an unfair task, are dismissed, or are enchanted.
- **Wit-Duel / Riddle** — out-logic a nonsense interlocutor.
- **Escape / Not-Getting-Caught** — chase-shaped: poppy fields, Hammer-Heads, winged monkeys. Break = captured.
- **Wonder-Shock** — confronting the genuinely uncanny. Direct Composure damage.
- **Persuasion / Yes-And** — talking a beast or country-folk into help.
- **Violence (exception path)** — exists and is sometimes absurdly decisive (drop the house, throw the water). It is the murderhobo lane, and **the world prices it per lethality dial** — Oz mostly absolves it, Gulliver turns the satire's mirror on you and you become the Yahoo.

### Genre archetypes (the Traveler's coping-style)

You always play a visitor from the ordinary world. The archetype is *how you cope* with nonsense; the world tints it (via `archetype_funnels.yaml`).

- **The Innocent** — disarms the world with sincerity; Composure from moral clarity (Dorothy).
- **The Wit** — argues, out-logics nonsense; Composure from cleverness (Alice).
- **The Surveyor** — reasons, measures, documents; Composure from understanding (Gulliver).
- **The Scrapper** — meets menace head-on; lower Composure ceiling, real teeth (the murderhobo lane, made legible).
- **The Dreamer** — embraces wonder, goes native; high reach, risky (loses the thread of home).

**Progression** is *savvy*, not levels: a traveler grows by learning the world's rules — which authorities are hollow, which weaknesses are absurd, which kindnesses pay off. Genre-level `progression.yaml` / `power_tiers.yaml` express this as confidence/insight tiers, not combat power.

---

## 4. Oz world build (full depth)

### 4.1 Era

**LOCKED: Wizard-era Oz, everything primed** (the *Wonderful Wizard of Oz*, 1900, moment). Rationale: it makes the **gender pillar the central discovery**. The Wizard rules the Emerald City by pure illusion — the one man who claims power, and he's a fraud — while every entity with *real* power is a woman: Glinda (good, South), the Wicked Witch of the West (menace, West), the freshly-dead Witch of the East, the Good Witch of the North, Mombi (hedge-witch, North). The sandbox's structural truth, discoverable by play, is that **male authority in Oz is humbug or anxiety, and the women hold everything.** Live menace, iconic geography, the hottest seam (the curtain).

**"Everything primed" means the post–*Marvelous Land* matriarchal payload is seeded *latent* in the Wizard-era baseline, loaded for Living-World advancement — not yet triggered:**
- **Ozma** is alive but hidden as the boy **Tip** under Mombi's enchantment (the lost-princess hook, discoverable/promotable).
- **Jinjur's Army of Revolt** is a coiled spring — suffragette unrest seeded in the Emerald City / Gillikin country, ready to rise.
- **Glinda** already *holds the secret* of the rightful heir; her court is the legitimist engine waiting for its moment.

This lets emergent play evolve Oz **toward** the Ozma-era reveal organically (the Wizard departs, the witches fall, the women fill the vacuum) without pre-baking it. *Ozma-era-as-baseline was considered and set aside — it dilutes the humbug seam and the live menace.*

### 4.2 Pillars

- **Matriarchal Oz / male-inadequacy.** First-class world pillar. Drives factions, cultures, NPC roster. The famous men are defined by lack (Scarecrow/brains, Tin Woodman/heart, Lion/courage) or fraud (Wizard); the powers are women. The latent deep hook is **the lost Princess Ozma**, hidden by enchantment (Mombi) — rightful female rule waiting under the surface.
- **The sealed Secondary World.** The **Deadly Desert** rings Oz; its shifting sands turn any living thing to dust. You cannot simply walk home — the border is lethal. This is what makes Oz a *place* you're stuck wandering, not a level you exit.
- **Enchantment, not the kill.** Menace transforms and enslaves rather than slays (low lethality). The Witch enslaves the Winkies; Mombi turns people into ornaments. Death is rare and usually self-inflicted or the Desert.

### 4.3 Geography / cultures (the four colored countries + center)

| Region | Color | People (culture) | Note |
|--------|-------|------------------|------|
| **Munchkin Country** (East) | Blue | Munchkins — small, timid, hardworking farmers | Freshly freed (Witch of the East just died) |
| **Winkie Country** (West) | Yellow | Winkies — gentle, enslaved by the Witch of the West | The Witch's castle is here |
| **Quadling Country** (South) | Red | Quadlings — Glinda's people | Glinda's castle; the girl-army |
| **Gillikin Country** (North) | Purple | Gillikins — wilder, witch-haunted North | Mombi country; the Good Witch of the North |
| **Emerald City** (center) | Green | City-dwellers, green-spectacled | The standing humbug (enforced green glasses) |

**Oddball micro-cultures (POI-bound):** the living-porcelain folk of the **Dainty China Country**; the armless, neck-extending **Hammer-Heads**; the **Kalidahs** (bear-headed, tiger-bodied beasts); the **Winged Monkeys** (bound to the Golden Cap); the **Field Mice** (the helpful-small-creatures economy).

**Naming:** Oz names are whimsical-English invention (Dorothy, Ozma, Tip, Jinjur, Mombi, Nick Chopper), **not conlang Markov** — per the historical/curated-word-list precedent, Oz uses curated whimsical-English name pools, not the corpus Markov pipeline. (Munchkin/Quadling place- and person-names are English-diminutive and coinage, not phonotactic invention.)

### 4.4 Factions (in motion — Living World)

- **Glinda's Court** (South) — benevolent supreme sorceress; commands an army of girls; the legitimist good power; knows the secret of the lost princess.
- **The Wizard's Regime** (Emerald City) — male pretender-power, all illusion; rules by the green-spectacles humbug and reputation; secretly a balloonist from Omaha with no magic at all.
- **The Wicked Witch of the West** (West) — one-eyed enslaver of the Winkies; commands wolves, crows, bees, and the Winged Monkeys via the Golden Cap; absurd trivial weakness (water).
- **The Hedge-Witchcraft of the North** (Mombi et al.) — old, transformative magic; keeper of the Ozma secret.
- **Jinjur's coming Army of Revolt** (latent) — General Jinjur's all-girl army of knitting-needle revolutionaries; a half-satire, half-celebration of the suffragettes; seeded as a rising force (front-and-center if Ozma-era is chosen).

### 4.5 NPC roster (Monster Manual — inject into `<game_state>` as "NPCs nearby, not yet met")

Core cast, played straight from Baum:

- **The Scarecrow** — wants brains, is the cleverest; later briefly rules.
- **The Tin Woodman (Nick Chopper)** — wants a heart, is the most sentimental; Emperor of the Winkies.
- **The Cowardly Lion** — wants courage, is brave when it counts.
- **The Wizard (Oscar Diggs)** — humbug balloonist; rules by illusion; the curtain.
- **Glinda the Good** — supreme sorceress of the South; girl-army; the real good power.
- **The Wicked Witch of the West** — enslaver; Golden Cap + Winged Monkeys; water-weak.
- **The Good Witch of the North** — kindly; the protective forehead-kiss.
- **Mombi** — the hedge-witch who hid the infant Ozma as the boy Tip (deep hook).
- **General Jinjur** — leader of the Army of Revolt.
- **The King of the Winged Monkeys** — bound to the Golden Cap; three commands.
- **The Queen of the Field Mice** — helps against the poppies (kindness economy).
- **The Hammer-Heads** — block the hill to the South.
- **Toto** — the companion who pulls the curtain (recurring motif).
- **"The Lost Princess" (Ozma)** — latent; rightful ruler under enchantment.

*Expansion cast (later books, note-only):* Tik-Tok, the Nome King, Billina, Jack Pumpkinhead, the Sawhorse, the Woggle-Bug, the Gump (from *Marvelous Land* / *Ozma of Oz*).

### 4.6 POIs (walk-into locations)

The Emerald City (throne room, palace, the green spectacles gate); the Yellow Brick Road; each of the four countries; the Deadly Poppy Field; the Dainty China Country; the Forest of the Fighting Trees; Hammer-Head Hill; the Kalidah gorge / great forest; the Castle of the Wicked Witch of the West; Mombi's cottage; the Deadly Desert (the lethal border).

### 4.7 Oz-specific tropes (wired to keywords the narrator will hit)

- **The Incomplete Companion** — an NPC convinced they lack what they visibly have (brains/heart/courage); joins, self-deprecates, proves themselves.
- **The Water-Weak Tyrant** — a fearsome power with an absurd trivial weakness; the "boss" dies to a bucket. Rule-of-Cool, genre-honest.
- **The Green Spectacles** — enforced illusion; the city is only emerald because everyone's made to wear green glasses. The standing humbug.
- **The Helpful Beasts** — kindness to small creatures pays off (Baum's moral economy).
- **The Deadly Desert** — the world is sealed; you can't walk home; the border kills.
- **Enchantment, Not the Kill** — menace transforms/enslaves rather than slays (low-lethality dial in trope form).
- **The Lost Princess** — rightful female rule hidden under enchantment (Ozma).

### 4.8 Lethality dial

**Oz = LOW.** Breaking resolves as enchanted / enslaved / sent-on-a-task / embarrassed — almost always recoverable. Death is rare and usually self-inflicted-stupid or the Deadly Desert. Witches die easily and absurdly (genre-honest). The world *wants* the traveler to win.

### 4.9 Visual style (world-level)

**W.W. Denslow's 1900 plates** — American art-nouveau line, flat color fields keyed to the four-country palette (blue/yellow/red/purple/green), period children's-book illustration. **Not** MGM technicolor, not ruby. `visual_style.yaml` lives at world level (per the world-level-visual-style precedent). *Wiring note: the daemon hard-requires a genre-level `positive_suffix` independently — confirm the genre carries one so renders don't fail.*

---

## 5. Wonderland & Gulliver (named, deferred)

- **Wonderland** (Carroll) — *funky-dark.* Nonsense logic is the antagonist. A capricious Queen of Hearts who screams for beheadings (mostly theater — until it isn't) out-tyrannizing a do-nothing King. Trials with no rules, a tea party stuck at six o'clock, croquet with live flamingos, growing and shrinking. Medium lethality, surreal-capricious. Confrontations lean Wit-Duel and Trial.
- **Gulliver** (Swift) — *savage.* No plot — four self-contained voyages, each "wash ashore into an absurd society, survive its insane logic, get home." The absurd society *is* the antagonist and the satire turns on the traveler. Lilliput's egg-end wars, Brobdingnag's giants treating you as a pet, Laputa's useless academy, the Houyhnhnms' bloodless rational horror. High lethality, adult. Confrontations lean Audience and Wonder-Shock, violence heavily priced.

---

## 6. Content file manifest

### Genre level — `genre_workshopping/wry_whimsy/` (workshop-first, per locked decision)

| File | Contents |
|------|----------|
| `pack.yaml` | Name, blurb, recommended players, version |
| `rules.yaml` | `ruleset: native`; Composure substrate config; default lethality |
| `axes.yaml` | Tone axes (whimsy↔menace, sense↔nonsense, gravity, outlook) |
| `archetypes.yaml` | The five Traveler coping-styles |
| `archetype_constraints.yaml` | Build constraints |
| `char_creation.yaml` | Traveler chargen flow |
| `beat_vocabulary.yaml` | Wit / Composure / Trial / Escape beats |
| `progression.yaml`, `power_tiers.yaml` | Savvy/insight tiers (not combat levels) |
| `tropes.yaml` | Structural genre tropes (threshold-crossing, impossible-authority, helpful-companion, seam-reveal) |
| `inventory.yaml` | Genre item vocabulary |
| `achievements.yaml` | Genre achievements |
| `prompts.yaml` | **The four-principle narrator doctrine** |
| `theme.yaml`, `client_theme.css` | Styling |
| `audio.yaml`, `audio/` | Mood→track (assets deferred) |
| `cartography.yaml` | Map config |

### World level — `genre_workshopping/wry_whimsy/worlds/oz/`

| File | Contents |
|------|----------|
| `world.yaml` | Identity, era (Wizard-era), lethality dial (low), tone-axis overrides, default opening location |
| `lore.yaml` | Four countries, Emerald City humbug, witch-powers, matriarchy, factions |
| `history.yaml` | Oz's past — the fairy enchantment, witch carve-up, Wizard's arrival, the hidden princess |
| `legends.yaml` | In-world legends (the lost Princess, the Deadly Desert, the Golden Cap) |
| `cultures.yaml` | Munchkin / Winkie / Quadling / Gillikin / Emerald + micro-cultures |
| `tropes.yaml` | Oz-specific tropes (§4.7) |
| `archetype_funnels.yaml` | How genre archetypes tint to Oz |
| `cartography.yaml` | Four-country map + Yellow Brick Road + Emerald City + Deadly Desert border |
| `visual_style.yaml` | Denslow 1900 aesthetic; four-country palette |
| `portrait_manifest.yaml` | NPC roster portraits (assets deferred) |
| `openings.yaml` | Threshold-crossing openings (the cyclone / the arrival) |
| NPC roster source | The famous Oz cast as pre-gen "NPCs nearby, not yet met" (§4.5) |

---

## 7. Out of scope (this pass)

- Wonderland and Gulliver deep authoring (named only).
- Asset generation (portraits, POI landscapes, music) — manifests authored, renders later.
- Any engine/ruleset-module code — the chassis is native + content only. If a confrontation can't be expressed in native content, that is a finding to route, not a license to write engine code.
- The Tip→Ozma transformation as a *live, playable* arc (Ozma is latent backstory in Wizard-era; promotable later or if Ozma-era is chosen).

---

## 8. Decisions (locked 2026-06-01)

1. **Genre name** — ✅ **Wry Whimsy** (`wry_whimsy`).
2. **Oz era** — ✅ **Wizard-era, everything primed** (matriarchal/Ozma/Jinjur payload seeded latent for Living-World advancement).
3. **Workshop vs. live** — ✅ **Workshop-first** (`genre_workshopping/wry_whimsy/`).
