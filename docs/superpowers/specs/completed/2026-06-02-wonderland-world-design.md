# Wonderland World — Design Spec (`wry_whimsy/worlds/wonderland`)

**Date:** 2026-06-02
**Author:** GM
**Status:** Approved — design locked; proceeding to plan
**Scope:** Second `wry_whimsy` world authored to full playable depth: **Wonderland**, Lewis Carroll's *Alice's Adventures in Wonderland* (1865) **and** *Through the Looking-Glass* (1871) as one dream-territory. Genre chassis and the four-principle narrator doctrine are already locked (see `2026-06-01-travelers-tales-genre-design.md`); this spec records only the **Wonderland deltas**.

**Locked decisions (this spec):**
1. **Corpus** — both books, one world (rabbit-hole *and* mirror).
2. **Structure** — two clean sub-regions joined by a mirror seam: **Card Country** (1865) + **Looking-Glass Land** (1871). Expressed entirely as a `cartography.yaml` region graph (the Oz template, two-lobed).
3. **Visual style** — John Tenniel's 1865/71 wood-engravings. Never Disney 1951.

---

## One-line distillation

> **The nonsense dream you wake from by refusing it.** A sensible traveler falls into a place where *nonsense itself is the authority* — two capricious queens, a sleeping king, a court of cards and a country of chesspieces — and the only way home is to stop granting the dream its power. Medium lethality: the threat is being *trapped* (sentenced, frozen, forgetting your own name) far more than killed — but the Jabberwock has real teeth.

---

## 1. Relationship to the genre chassis

Wonderland inherits the locked `wry_whimsy` chassis unchanged: the Composure substrate, the five Traveler archetypes, the Bang catalog (Audience/Trial, Wit-Duel, Escape, Wonder-Shock, Persuasion, priced Violence), and the four-principle narrator doctrine (**diegetic sincerity / the seams are bait / a place not a plot / play it straight from the source**). The world supplies **only flavor + dials**, per SOUL "Crunch in the Genre, Flavor in the World."

This world's positions on the genre gradient:

| Dial | Oz | **Wonderland** | (Gulliver) |
|------|----|----|----|
| Tone | Light | **Funky-dark** | Savage |
| Lethality | Low | **Medium** | High |
| Antagonist | Humbug authority | **Nonsense-logic itself** | The society judges *you* |
| Gender current | Men are frauds claiming power | **Men are asleep / absent / ineffectual while women rage** | Savage male court-politics |

**Confrontations lean:** Audience/**Trial** and **Wit-Duel/Riddle** primary; Escape, Wonder-Shock, Persuasion secondary; **Violence priced higher than Oz** (the Jabberwock is the one sanctioned target; violence elsewhere marks you).

---

## 2. Identity, arrival, and the go-home spine

**One dream-territory, two adjacent dream-countries** joined by a mirror. The traveler is a sensible visitor — never a native — in a place where the rules are made up and weaponized.

- **Arrival:** fall down the **rabbit-hole** into **Card Country** (the Hall of Doors; the eat-me/drink-me size game; the tiny door to the garden).
- **Internal threshold:** the **Looking-Glass** — a mantelpiece mirror you **step through** into **Looking-Glass Land**. This is a "seams are bait" threshold, not a wall: it is findable and crossable in both directions.

**Go-home spine (the Wonderland delta from Oz).** Oz seals you in with the lethal Deadly Desert; Wonderland's exit is **waking**, and you wake by **refusing the dream decisively** — Alice's *"You're nothing but a pack of cards!"* (Card climax) and her shaking the Red Queen at the erupting feast (Glass climax) are the canonical wakings. Per the oq-3 premise/belief spec, **the more the traveler reshapes the place, the more it wants to keep them** ("the dream would so love to keep you"). The Dreamer's structural risk is *never waking* — losing the thread of home in the Wood of No Names or the Red King's dream.

---

## 3. Lethality dial — MEDIUM

Breaking (Composure exhausted) resolves, in order of frequency, as:
- **Sentenced** — the Queen of Hearts' *"Off with your head!"*; mostly theater (the King quietly commutes everything), but the threat bites Composure and *can* tip real if pressed.
- **Trapped in the nonsense** — stuck at the six-o'clock tea-party forever; frozen mid-move as a chesspiece; painted red like a rose-tree; conscripted into the Caucus-race.
- **Losing the thread** — forgetting your own name (the Wood of No Names); going native; the Dreamer who cannot wake.
- **Killed** — rare, but **real**: the **Jabberwock** is a genuine lethal monster (the priced-violence exception); the Bandersnatch and Jubjub bird are lesser teeth; the Red Queen's race can exhaust you to collapse.

The world is *capricious*, not kind (the Oz delta): it will not reliably soften, and cruelty is a live current played straight.

---

## 4. The political pillar (the gender current, honest to Carroll)

Female forces dominate and rage; the men are asleep, absent, or ineffectual. Two flavors, one per sub-region — **two clean Premises** for the oq-3 belief-engine (authored as draft, see §9):

- **Card Country — `the_queens_terror`.** Authority: the **Queen of Hearts**, ruling by terror-by-beheading-as-theater. The **King of Hearts** is mild and quietly pardons everyone behind her back — the do-nothing who secretly undoes her. Bloc: `the_card_court` (the painted card-soldiers and courtiers). **Collapse:** *"You're nothing but a pack of cards!"* — the literal canonical Refuse-the-Premise; the court scatters into flat pasteboard.
- **Looking-Glass Land — `the_rigged_game`.** Authority: the **Red Queen**, an imperious drillmaster who runs the rigged race ("here it takes all the running you can do to keep in the same place"). The **Red King sleeps the entire time** — the *ultimate* do-nothing male, and the ontological menace ("you're only a sort of thing in his dream"). The White Queen lives backwards (helpless-comic); the White King is ineffectual. Bloc: `the_chesspieces`. **Collapse:** the coronation feast erupts and the traveler shakes the queen — who dwindles to a kitten.

---

## 5. Cultures and naming

Three cultures, none on the conlang/Markov pipeline (per the historical/curated-word-list precedent — Carroll's people have **titles, not names**):

- **The Card-Folk** (Card Country) — flat, two-dimensional, heraldic playing-cards: gardeners, soldiers, courtiers, the royal suits. Terrified and theatrical.
- **The Chesspieces** (Looking-Glass Land) — living chess pieces who move by the board's rules and can "see the whole board": the Red and White courts, pawns, the knights.
- **The Creature-Folk** (both halves) — the talking dream-fauna and nonsense-logicians, each running their canonical bit.

**Naming model:** curated whimsical-English **definite-article epithets** ("the March Hare", "the Mock Turtle", "the White Rabbit"), **card-rank / chess-piece nomenclature** ("Five of Spades", "the White Knight", "the Red Queen"), and **Carroll portmanteau nonsense** for invented creatures/places ("Jabberwock", "Bandersnatch", "slithy", "the Tulgey Wood"). No phonotactic Markov generation.

---

## 6. NPC roster (Monster Manual — inject as "NPCs nearby, not yet met")

Played straight from Carroll. **Card Country:** the White Rabbit (anxious herald), the **Caterpillar** ("Who are *you*?", the hookah, the size-mushroom), the **Cheshire Cat** (the truth-teller who won't be pinned — *"we're all mad here"* — the seam-bait guide), the Duchess + the pig-baby + the pepper-Cook, the **Hatter / March Hare / Dormouse** (the eternal six-o'clock tea-party), the **Mock Turtle + Gryphon** (the Lobster-Quadrille), the **Queen of Hearts**, the **King of Hearts**, the **Knave of Hearts** (the trial's defendant), the rose-painting **Gardeners (Two, Five, Seven of Spades)**, the Frog- and Fish-Footmen, the Dodo/Mouse/Lory crew (Pool of Tears).

**Looking-Glass Land:** the **Red Queen**, the **White Queen** (lives backwards), the **sleeping Red King**, the ineffectual White King + his messengers (Haigha & Hatta), the **White Knight** (gentle, inventive, always falling off — Carroll's self-portrait; escorts the traveler to the last square), the Red Knight, **Tweedledum & Tweedledee** (the agreed battle; the Walrus and the Carpenter), **Humpty Dumpty** (the word-tyrant — *"when I use a word it means just what I choose"*), the **Lion & the Unicorn** (fighting for the crown), the Sheep (the shifting shop), the Gnat, the live Flowers (the gossipy Tiger-lily and Rose), and the **Jabberwock** (the one real monster).

---

## 7. Geography — the `cartography.yaml` region graph

`navigation_mode: region`, `starting_region: the_hall_of_doors`. ~13 regions in two lobes joined by the mirror seam. POIs are regions and/or `entities` (tier `real_object`, bound to `location_feature`/`npc`, with affordances like `enter`, `cross`, `step_through`, `grow`, `shrink`). The Jabberwock roams the wooded regions as a `real_object`-bound menace.

```
CARD COUNTRY (rabbit-hole)                LOOKING-GLASS LAND (mirror)
  the_hall_of_doors  ← start                the_garden_of_live_flowers
    │  eat-me/drink-me, tiny garden door       │
  the_pool_of_tears                          the_chessboard_country
    │  caucus-race, White Rabbit's House        │  brook-squares, railway leap
  the_tulgey_wood                            the_tweedle_wood
    │  Caterpillar's mushroom, Duchess's          │  Tweedles, Walrus & Carpenter
    │  pepper-kitchen, the Cheshire Cat         humpty_dumptys_wall
  the_mad_tea_party  (stuck at six)            │  the word-tyrant; Lion & Unicorn
  the_queens_croquet_ground                  the_wood_of_no_names
    │  flamingo mallets, the rose-tree           │  forget your name — lose the thread
  the_hall_of_justice  ← Card climax         the_coronation_feast  ← Glass climax
        │                                         │
        └──────────►  the_looking_glass  ◄────────┘
                      (mirror seam; affordance: step_through;
                       adjacent to both climax sites)
```

**Map style (the render prose):** a Tenniel-plate map of the dream-country — Card Country drawn as a heraldic playing-card garden (hedge-maze paths, painted roses, a croquet lawn), Looking-Glass Land as a vast green-and-white **chessboard** divided by brooks into squares, the two lobes meeting at a tall mantelpiece **mirror** that reflects one into the other. Engraved line, cross-hatching, restrained period tint.

---

## 8. Wonderland-specific tropes (wired to narrator keywords)

- **Nonsense-as-Authority** — the rules are invented and weaponized (the trial with no procedure, Humpty's private dictionary, the Queen's arbitrary sentences). The antagonist is logic itself.
- **The Capricious Sentence** — *"Off with their heads!"* — constant terror-theater, rarely executed (the King commutes); maps to the Audience/Trial confrontation.
- **Eat-Me / Drink-Me (the Size Game)** — the world rescales the traveler; growing and shrinking as both tool and hazard. A genuine mechanic (affordances `grow`/`shrink`).
- **Stuck-in-the-Nonsense** — the perpetual-present trap (the six-o'clock tea-party); breaking = you join the loop.
- **The Truth-Telling Cat** — the Cheshire speaks plain truth amid nonsense and won't be pinned — the seam-bait guide who won't guide.
- **You're-Only-a-Thing-in-His-Dream** — the Red King ontological dread; the world may not be real and neither are you (the "lose the thread of home" menace in trope form).
- **Run-to-Stay-in-Place** — the Red Queen's race; effort that yields nothing; the satire of striving.
- **The Pack of Cards** — the climactic refusal that ends the dream; the canonical Refuse-the-Premise / Premise collapse.
- **The Jabberwock** — the one real monster; the medium-lethality teeth; the priced-violence exception (the vorpal sword works *here* and marks you everywhere else).

---

## 9. Premise / Bloc authoring (DRAFT — pending oq-3 schema lock)

The Connecticut-Yankee belief-flow substrate (Premise/Bloc aggregation over ADR-053) is **engine work in flight in the oq-3 lane** (`2026-06-02-wry-whimsy-premise-belief-flow-design.md`), with **Oz as the v1 reference implementation** and the schema not yet locked (genre `premises.yaml` vs per-world; §13 open questions). Therefore:

- This world authors the **two Premise/Bloc identities and their draining/awakening acts as design notes now** (§4), and wires them to the in-flight schema **once it lands** — not before. No engine assumptions baked into content.
- Draft draining-acts: `the_queens_terror` ← defy a sentence and survive · expose that the King commutes everything · refuse the trial's authority · the public "pack of cards" naming. `the_rigged_game` ← refuse the race · reach the eighth square on your own terms · name the sleeper's dream · shake the queen at the feast.
- The Red King's dream stays a **trope / Wonder-Shock**, not a Premise, in v1 (too meta for the aggregation model).

---

## 10. Visual style — Tenniel (world-level)

`visual_style.yaml` at world level (per the world-level-visual-style precedent). **John Tenniel's 1865/71 wood-engravings**: Victorian steel/wood-engraving line, dense cross-hatching, period children's-book plate, restrained hand-tint over black line. Flat heraldic cards; the famous Tenniel chesspiece designs; Alice-era costume. **Never** the 1951 Disney cartoon (no pinafore-blue cel-shading, no purple grinning Cheshire). **Token-budget discipline:** the `positive_suffix` must stay short (the un-evictable ART_SENSIBILITY.WORLD slot — keep it lean or LOCATION evicts to a BudgetError, per the Oz build gotcha). Confirm the genre carries a `positive_suffix` independently (the daemon hard-requires it).

---

## 11. Content file manifest (world level — `worlds/wonderland/`)

Mirrors the Oz world build:

| File | Contents |
|------|----------|
| `world.yaml` | Identity, both-books corpus, lethality dial (medium), tone-axis overrides, `starting_region: the_hall_of_doors`, the waking go-home spine |
| `lore.yaml` | The two dream-countries, nonsense-as-authority, the two queens / sleeping king, the mirror seam, the Premise illusions |
| `history.yaml` | The dream's "past" played straight — the card court, the chess game in progress, how the queens came to rule (Carroll-honest, not over-explained) |
| `legends.yaml` | In-world legends (the Jabberwock and the vorpal sword, the pack of cards, the sleeping Red King) |
| `cultures.yaml` | Card-Folk / Chesspieces / Creature-Folk + the epithet/portmanteau naming pools |
| `tropes.yaml` | The §8 Wonderland tropes |
| `archetype_funnels.yaml` | How the five genre Travelers tint to Wonderland (the Wit's home-turf-and-torment; the Dreamer who never wakes; the Scrapper as Jabberwock-slayer; the Surveyor mapping a place that won't hold still) |
| `cartography.yaml` | The §7 region graph (regions + entities + affordances), played straight from both books |
| `visual_style.yaml` | Tenniel 1865/71 aesthetic; lean positive_suffix |
| `npcs.yaml` | The §6 Monster Manual roster as pre-gen "NPCs nearby, not yet met" |
| `openings.yaml` | Threshold-crossing openings (the fall down the rabbit-hole; solo + MP coverage per the unified Opening schema) |
| `portrait_manifest.yaml` | NPC roster portraits (Tenniel; assets rendered later) |
| `premises.yaml` (DRAFT) | The §4/§9 Premise + Bloc identities — **flagged pending oq-3 schema lock**, not wired |
| POI image-prompt manifest | The ~13 region/landmark landscape prompts (Tenniel; rendered later via the `--shard` daemon pass) |

---

## 12. Out of scope (this pass)

- **Asset *rendering*** — manifests + prompts authored now; portraits and POI landscapes rendered later (the oq-1 `--shard` daemon pass + R2 upload, per the Oz pipeline).
- **Premise/Bloc *wiring*** — content identities drafted; wired only when the oq-3 belief-engine schema lands. If a Wonderland confrontation can't be expressed in native content + the (eventual) Premise schema, that is a finding to route, not a license to write engine code.
- **The Looking-Glass as a *separate world*** — it is one lobe of this world, not its own pack/world.
- **Music** (ACE-Step) — deferred to a later pass.
- **Gulliver** — still named-only.

---

## 13. Validation gates (lessons from the Oz build)

- **Run `load_genre_pack` (the loader), not just `validate pack`** — the loader is the real wiring gate; it catches `draft: true` silently skipping the world, enum/tone fields, and `openings.yaml` needing the unified Opening schema (solo + MP `triggers.mode` coverage). A validator PASS 0/0 is not proof the world loads.
- **UI chrome archetype** — `wry_whimsy` already maps to `parchment` (sidequest-ui #312); a new *world* under an existing pack inherits it, so no UI change is needed (the throw-on-unknown is keyed to the genre slug, which is unchanged).
- **Token budget** — keep the Tenniel `positive_suffix` and per-POI/portrait prose short, or LOCATION evicts and renders BudgetError.
- **Confrontation crunch lives in genre `rules.yaml`**, not world files; world `confrontations.yaml`/`faction_agendas.yaml` are engine-unwired. Wonderland authors flavor + dials; the Bang catalog is already at genre level.
