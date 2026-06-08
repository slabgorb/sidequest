# Gulliver World — Design Spec (`wry_whimsy/worlds/gulliver`)

**Date:** 2026-06-02
**Author:** GM
**Status:** Approved — design locked; proceeding to plan
**Scope:** Third `wry_whimsy` world authored to full playable depth: **Gulliver**, Jonathan Swift's *Gulliver's Travels* (1726), the **savage end** of the light→savage gradient. Genre chassis and the four-principle narrator doctrine are already locked (see `2026-06-01-travelers-tales-genre-design.md`); Oz (`2026-06-01`) and Wonderland (`2026-06-02`) are the two prior worlds and the structural template. This spec records only the **Gulliver deltas**.

**Locked decisions (this spec):**
1. **Corpus** — all **four voyages** (Lilliput, Brobdingnag, Laputa-&-below, Houyhnhnms) as one world.
2. **Structure** — four self-contained voyages expressed as four lobes of one `cartography.yaml` region graph, joined not by physical adjacency (Gulliver has none) but by **the sea** — a shipwreck/re-embark hub region (`the_open_sea`). The Wonderland two-lobe pattern scaled to four.
3. **Visual style** — **Thomas Morten's 1865** wood-engravings (the Cassell's illustrated-Gulliver tradition). Never the cute children's-book Gulliver.
4. **Premise** — a single spanning Premise (`the_yahoo_verdict`) with four voyage-Blocs, not four separate per-voyage Premises (DRAFT, pending oq-3 schema lock).
5. **Played dead straight from Swift** — the satire is savage, the verdict on humanity is real, the homecoming is bleak. No winking, no softening (the diegetic-sincerity principle).

---

## One-line distillation

> **The mirror that proves you're the monster.** A sensible ship's-surgeon is wrecked into four absurd societies, each of which judges *him* — and the more clearly he sees them, the more clearly they (and he) see that *he* is the brute. **High lethality:** the threat is being executed, displayed as a freak, crushed by scale, or — worst — getting home and finding you can no longer bear your own kind. The savage end of the gradient: the horror is that the satire is *right*.

---

## 1. Relationship to the genre chassis

Gulliver inherits the locked `wry_whimsy` chassis unchanged: the Composure substrate, the five Traveler archetypes, the Bang catalog (Audience/Trial, Wit-Duel, Escape, Wonder-Shock, Persuasion, priced Violence), and the four-principle narrator doctrine (**diegetic sincerity / the seams are bait / a place not a plot / play it straight from the source**). The world supplies **only flavor + dials**, per SOUL "Crunch in the Genre, Flavor in the World."

This world's positions on the genre gradient:

| Dial | Oz | Wonderland | **Gulliver** |
|------|----|----|----|
| Tone | Light | Funky-dark | **Savage** |
| Lethality | Low | Medium | **High** |
| Antagonist | Humbug authority | Nonsense-logic itself | **The absurd society judges *you*** |
| Gender current | Female-governed; male power is humbug | Capricious queens out-tyrant do-nothing kings | **Savage male court-politics** |

**Confrontations lean:** **Audience/Trial** (the royal/court judgment) and **Wonder-Shock** (the scale reveals, the talking horses, the Struldbruggs) primary; Persuasion secondary (you argue your humanity and lose); **Violence priced higher than anywhere on the gradient** — see §4.

---

## 2. Structure — four voyages, one region graph, the sea as seam

Unlike Oz (one continuous land) and Wonderland (two physically-adjacent lobes joined by a mirror), Gulliver is structurally **four separate sea-voyages with no connecting geography** — "wash ashore, survive the absurd society, get home, set sail again." The connective seam is therefore **the sea itself** — a shipwreck/re-embark hub (`the_open_sea`) adjacent to each voyage's arrival shore. Re-embarking is itself the savage joke (Gulliver never learns; he keeps going back).

`navigation_mode: region`, `starting_region: the_lilliput_shore`. ~19 regions in four lobes plus the sea seam plus the bleak terminus:

```
                         the_open_sea  ← hub seam; the savage "set sail again"
   ┌──────────────┬──────────────┬──────────────┬──────────────┐
 VOYAGE 1        VOYAGE 2        VOYAGE 3        VOYAGE 4
 LILLIPUT        BROBDINGNAG     LAPUTA & below  HOUYHNHNM-LAND
 (you're the     (you're the     (you're the     (you're the
  giant)          pet)            tourist)         Yahoo)

 the_lilliput_   the_giant_      laputa_flying_  the_yahoo_field
   shore ←start    cornfield       island         the_masters_house
 mildendo_       the_farmers_    lagado_academy  the_grand_assembly
   capital         house         glubbdubdrib_     the_canoe_shore
 the_imperial_   the_kings_        isle                 │
   palace          court         luggnagg_court        ▼
 blefuscu_       the_seaside_      (Struldbruggs)  the_homecoming
   strand          box                            ← bleak terminus, post-Voyage-4
```

**Voyage walkthroughs (played straight from Swift):**

- **Voyage 1 — Lilliput (you are the giant):** wake bound by threads on `the_lilliput_shore`; the court at `mildendo_capital` (the Emperor; Flimnap & Skyresh's rivalries; the High-Heel/Low-Heel parties); `the_imperial_palace` (extinguish the fire grossly; the articles of impeachment — blinding then starvation); flee to `blefuscu_strand` (the rival empire, the Big-Endian exiles, the captured fleet, the escape boat).
- **Voyage 2 — Brobdingnag (you are the pet):** arrive in `the_giant_cornfield` (the reapers' scythes nearly kill you); `the_farmers_house` (displayed for money; the cat, the rats, the baby); `the_kings_court` (the King's interview — Europe is "the most pernicious race of little odious vermin"; the Queen; the malicious court-dwarf; the degrading Maids of Honour); `the_seaside_box` (the eagle snatches your travelling-box and drops it in the sea; rescue).
- **Voyage 3 — Laputa & below (you are the tourist):** `laputa_flying_island` (the abstracted court of mathematicians-and-musicians; the flappers; the island that drops on rebel cities); `lagado_academy` (extracting sunbeams from cucumbers; the projectors); `glubbdubdrib_isle` (the governor who summons the dead — ancient kings, senates); `luggnagg_court` (floor-licking obeisance; the **Struldbruggs** — immortals who age into envied-then-pitied decay).
- **Voyage 4 — Houyhnhnm-land (you are the Yahoo):** `the_yahoo_field` (you're taken for a Yahoo amid the filth); `the_masters_house` (your reasoning Houyhnhnm host; learning the language; recounting Europe); `the_grand_assembly` (the cold debate — exterminate the Yahoos? expel Gulliver?); `the_canoe_shore` (expelled; you build a canoe and are forced to sea).

**The bleak terminus:** from `the_open_sea` *after* the fourth voyage, `the_homecoming` opens (Redriff / your house) — and you cannot bear the smell of your own wife and children; you keep horses and prefer the stable. The "win" is the bleakest homecoming Swift gives.

---

## 3. Lethality dial — HIGH (the savage delta)

Breaking (Composure exhausted) resolves, in order of frequency, as:
- **Condemned / Executed** — Lilliput's articles of impeachment (blinding, then slow starvation); unlike Wonderland's Queen of Hearts (whose sentences the King quietly commutes), **here the sentence is not theater** — Gulliver escapes only by fleeing to Blefuscu. Real death is on the table.
- **Displayed / owned** — Brobdingnag: shown as a curiosity at fairs to the point of near-fatal exhaustion; kept as a pet; menaced by a monkey that nearly kills you, by wasps, by the farmer's avarice.
- **Made the Yahoo / going native in despair** — Houyhnhnms: you come to see yourself as vermin and cannot return to humanity. The savage analog of Wonderland's "losing the thread" — but here you don't forget your name, you **learn the truth about your species and cannot unlearn it**.
- **Existential horror** — the Struldbruggs (immortality as decay, not gift); the flying island crushing a city beneath it.
- **Killed** — genuinely common: drowning, the reaper's scythe in the grain field, the eagle dropping the box, execution in Lilliput.

The savage delta from both prior worlds: the world does **not** soften, and its verdict on the traveler is usually **correct**. The horror is not caprice (Wonderland) or humbug (Oz) — it is that the satire is right.

---

## 4. Confrontations and the priced-violence inversion

**Audience/Trial** and **Wonder-Shock** are the primary Bangs (the royal interview, the impeachment, the Grand Assembly; the scale reveals, the talking horses, the Struldbruggs). Persuasion is secondary and usually loses (you plead your humanity and the verdict stands).

**The priced-violence inversion (the key Gulliver mechanic-flavor delta):** Wonderland prices violence high but grants **one** sanctioned kill (the Jabberwock, the vorpal-sword exception). **Gulliver grants none.** Every violent act — extinguishing the palace fire by the only gross means available, killing the rats in the farmer's house, fighting off the wasps — **confirms the Yahoo verdict**. Act the brute and you *become* the brute the satire says you are. The murderhobo lane exists (per the genre) and is sometimes absurdly decisive, but in this world it always turns the satire's mirror on you. This is the genre's "violence priced per lethality dial" at its maximum.

---

## 5. The political pillar (the gender current — savage male court-politics)

Each voyage is a male-dominated power structure, and the satire indicts male politics specifically:

- **Lilliput** — the Emperor ("Delight and Terror of the Universe", six inches tall); the jealous Treasurer **Flimnap** and the hostile Admiral **Skyresh Bolgolam**; the High-Heel/Low-Heel parties (Tramecksan/Slamecksan); the Big-Endian/Little-Endian holy war with Blefuscu over which end to crack an egg. Men kill over which end of an egg to crack. The one decent figure, the minister **Reldresal**, can't save you.
- **Brobdingnag** — the **King** (wise, judges Europe and finds it vermin); the **Queen** (keeps Gulliver fondly); the exploiting **farmer**; the malicious **court-dwarf**; the degrading **Maids of Honour** (the one place women hold power over Gulliver — and it is reductive and adult; handled straight but with period-literary restraint, never crude). Power is the King's judgment.
- **Laputa & below** — the **King** absorbed in mathematics and music; the male **projectors** of the Academy of Lagado; the male magicians of Glubbdubdrib; the Luggnagg court's floor-licking obeisance. Male intellectual vanity.
- **Houyhnhnm-land** — the cold patriarchal **Grand Assembly** of rational horses that debates exterminating the Yahoos and expelling Gulliver; your Houyhnhnm **master**. Reason as governance, and its bloodless cruelty.

Women appear (the Queen, the kind nurse **Glumdalclitch**, the Maids) but power across all four voyages is male and savage.

---

## 6. Go-home spine — the savage inversion

Oz seals you in with the Deadly Desert (you *want* home; click the heels). Wonderland's exit is **waking** by refusing the dream. **Gulliver's inversion: you can always get home — and that is the horror.** Every voyage ends with a real, achievable escape (the Blefuscu boat, the eagle-dropped box rescued at sea, the Dutch ship, the canoe). The compulsion is that Gulliver keeps **re-embarking** — four times he returns home and sets sail again. The savage go-home spine: **home is not a reward; it is the thing you can no longer stand.** The arc bottoms out at `the_homecoming` after the fourth voyage — you cannot bear your own family and prefer the company of horses. "Winning" Gulliver is the bleakest possible homecoming, and the player who keeps choosing the sea is choosing the satire's verdict on themselves (Diamonds and Coal: the re-embark is a baited hook).

---

## 7. Cultures and naming

Four cultures, one per voyage, **none on the conlang/Markov pipeline** — Swift's names are deliberate satirical coinages with hand-built phonotactics, and Markov would mangle them (the Houyhnhnm whinny-names are unpronounceable *by design*). Curated **`word_list`** name slots per the historical/curated-word-list precedent:

- **The Lilliputians** (Lilliput) — six-inch people whose nomenclature is grandiose for tiny things ("Quinbus Flestrin / Great Man-Mountain"; "Most Mighty Emperor of Lilliput, Delight and Terror of the Universe"); court titles + Swift's Lilliputian coinages (Mildendo, Belfaborac, Flimnap, Skyresh, Reldresal, Tramecksan, Slamecksan).
- **The Brobdingnagians** (Brobdingnag) — giants; plain-grand naming; the capital **Lorbrulgrud** ("Pride of the Universe"); Gulliver is named **Grildrig** ("mannikin"); the nurse **Glumdalclitch**.
- **The Laputans / Balnibarbians** (Voyage 3) — abstracted intellectual coinages (Laputa, Lagado, Balnibarbi, Glubbdubdrib, Luggnagg, Munodi); the **Struldbruggs**.
- **The Houyhnhnms & Yahoos** (Voyage 4) — the rational horses, whinny-derived names ("**Houyhnhnm**" = "the perfection of nature"); the **Yahoos**, the brute-humans named only by behavior (no proper names — they are described, not named).

**Naming model:** curated authored pools (titles, Swiftian satirical coinages, whinny-phonotactics) via `word_list` slots. No phonotactic Markov generation.

---

## 8. NPC roster (Monster Manual — inject as "NPCs nearby, not yet met")

Played straight from Swift; each with a canonical Living-World `goal`. ~18–20 named:

- **Lilliput:** `the_emperor_of_lilliput` (vain absolute monarch), `flimnap` (jealous Treasurer, your enemy), `skyresh_bolgolam` (hostile Admiral), `reldresal` (the one friendly minister), `the_blefuscu_envoy`.
- **Brobdingnag:** `the_brobdingnag_king` (the judge of Europe), `the_brobdingnag_queen`, `glumdalclitch` (the farmer's daughter, your kind nurse), `the_farmer` (your exploiter), `the_court_dwarf` (malicious rival).
- **Laputa & below:** `the_laputan_king` (absorbed in abstraction), `a_lagado_projector` (sunbeams-from-cucumbers), `the_governor_of_glubbdubdrib` (summoner of the dead), `a_struldbrugg` (immortal decay), `munodi` (the one sane Balnibarbian lord).
- **Houyhnhnm-land:** `the_houyhnhnm_master` (your reasoning host), `the_sorrel_nag` (the servant who is fond of you), `the_grey_steed` (an Assembly elder), the **Yahoos** as a collective menace (`the_yahoos`).

---

## 9. Geography — the `cartography.yaml` region graph

`navigation_mode: region`, `starting_region: the_lilliput_shore`. The §2 graph: ~19 regions across four lobes, joined by `the_open_sea` hub, with `the_homecoming` terminus gated behind the fourth voyage. POIs are regions and/or `entities` (tier `real_object`, bound to `location_feature`/`npc`, with affordances appropriate to scale — e.g. on the giant side, the player is the small thing and most furniture is `examine`/`shelter`/`climb`; on Lilliput, the player is the giant and the affordances are `wade`/`step_over`/`pinch`). Scale is a live texture, not a mechanic to over-model.

Each region: `name`, `summary`, `description`, `terrain`, `controlled_by` (the voyage-Bloc: `the_lilliput_court` / `the_brobdingnag_crown` / `the_lagado_academy` / `the_houyhnhnm_assembly`), `adjacent`, `landmarks`, `entities` (bind famous NPCs via `kind: npc, ref: <npc id from §8>` and POI features via `kind: location_feature`), `rivers`, `settlements`. **Entity `ref`s to NPCs must match §8 ids — reconcile in the build.**

**Map style (the render prose):** a Morten-plate map of four sea-separated lands — Lilliput a manicured toy-kingdom of six-inch hedges and palaces; Brobdingnag a vast country of grain-stalk forests and giant masonry; Laputa a circular island hanging in the air over the ruined experimental farms of Balnibarbi; Houyhnhnm-land a clean ordered grassland fouled at its edges by the Yahoos — the four ringed by open ocean with a wrecked ship between them. Dense cross-hatched wood-engraving line, dramatic scale contrast, restrained or no tint.

---

## 10. Gulliver-specific tropes (wired to narrator keywords)

Authored in `tropes.yaml` **before** `history.yaml`/`legends/` (cross-ref ordering). Nine, each with a stable `id`:

- **`the_satire_turns_on_you`** — the central engine: every society judges the traveler and his civilization; the mirror reveals you are the monster. The antagonist *is* the verdict.
- **`the_scale_reveal`** — size as horror and comedy (giant among the tiny; tiny among giants); the body made grotesque by scale (the magnified skin-pores, the lice, the cancerous breast). Wonder-Shock.
- **`the_petty_holy_war`** — men kill over which end to crack an egg, or the height of a heel. The savage-court-politics trope.
- **`reason_without_sense`** — the Academy of Lagado; intellect divorced from use; the flying island. The Laputa trope.
- **`the_struldbrugg_curse`** — immortality as decay; the envied gift that is a curse. Be careful what you wish for. Wonder-Shock / existential.
- **`the_thing_which_is_not`** — the Houyhnhnms have no word for lying; a society founded on truth makes the human (who lies, wars, lawyers) monstrous.
- **`the_yahoo_within`** — you come to despise your own kind; the bleak homecoming; preferring the stable. The savage "losing the thread."
- **`priced_violence_marks_the_yahoo`** — every violent act confirms the brute verdict; there is no sanctioned kill (the priced-violence inversion, §4).
- **`the_compulsion_to_reembark`** — Gulliver keeps going back to sea; home is unbearable; the savage joke that you never learn (the go-home-spine trope, §6).

---

## 11. Archetype funnels (the five genre Travelers tint to Gulliver)

`archetype_funnels.yaml`:
- **The Surveyor** — Gulliver's literal home turf (he measures, documents, records every dimension and custom) *and* its trap: careful documentation cannot save you, and admiring the Houyhnhnms' cold reason makes you complicit in the verdict on your own species.
- **The Wit** — fails here. The King out-judges your defenses; the Houyhnhnms cannot comprehend "the thing which is not," so your cleverness reads as Yahoo deceit.
- **The Scrapper** — the violence lane; the most punished archetype (every brute act = the Yahoo verdict, §4).
- **The Dreamer** — goes native; the Houyhnhnm-worshipper who can no longer come home (the savage never-waking, §6).
- **The Innocent** — fares best — Swift's faint mercy. Honest humility (not defending Europe's atrocities) wins the Brobdingnag King's regard.

---

## 12. Premise / Bloc authoring (DRAFT — pending oq-3 schema lock)

The Connecticut-Yankee belief-flow substrate (Premise/Bloc aggregation over ADR-053) is **engine work in flight in the oq-3 lane** (`2026-06-02-wry-whimsy-premise-belief-flow-design.md`), with **Oz as the v1 reference implementation** and the schema not yet locked. Wonderland authored its two per-lobe Premises as draft. Gulliver's savage core is **one indictment delivered four ways**, so it authors a **single spanning Premise with four voyage-Blocs** (not four separate Premises):

- **Premise `the_yahoo_verdict`** — "you are a brute like all your kind, and the more you act, the more you prove it." **Drained** by surviving each society *without* confirming the brute: humility, honesty, restraint, refusing violence. **Confirmed/strengthened** by violence, lying, vanity, defending the indefensible. There is no clean "pack of cards" collapse — the savage version is that the verdict can be *resisted* but never *refuted*; the best ending earns a bleak self-knowledge, not a triumphant waking.
- **Blocs (the four voyage-authorities) under it:** `the_lilliput_court` (petty male politics), `the_brobdingnag_crown` (the judging King), `the_lagado_academy` (reason without sense), `the_houyhnhnm_assembly` (bloodless rational expulsion).

Authored as `premises.draft.yaml` (the `.draft.yaml` name so the loader ignores it; **not** declared as an `extensions:` entry — no Python consumer exists yet), with a leading comment banner: "DRAFT — pending oq-3 belief-engine schema lock; NOT loaded by any consumer." Wired only when the schema lands. The Houyhnhnm "you are a Yahoo" stays the world-Premise; the homecoming despair stays a **trope** (`the_yahoo_within`), not a Premise.

---

## 13. Visual style — Thomas Morten 1865 (world-level)

`visual_style.yaml` at world level (per the world-level-visual-style precedent). **Thomas Morten's 1865 wood-engravings** (the Cassell's illustrated-Gulliver tradition): dense cross-hatched Victorian wood-engraving line, dramatic realist-fantastical compositions, scale-dramatic framing (the giant among the tiny; the tiny among giants). Restrained or no tint (engraving is black line). **Costume subtlety:** Gulliver is an early-Georgian ship's surgeon (c. 1699–1715 — tricorn, frock coat, buckled shoes), rendered in Morten's 1865 engraving *technique* — **not** Victorian dress, **not** a modern cartoon, **never** the cute children's-book Gulliver. Exclusions phrased **positively** (Z-Image ignores negative prompts — "rendered as a dense cross-hatched wood-engraving plate" not "no cartoon"; per the `z_image_negative` rule, rejection clauses go in `positive_suffix` as "...as X, not Y"). Include the SOUL modesty / "adult" / "no text" cleanup clause as Oz and Wonderland do. **Adult content** (the Maids of Honour, the Yahoo filth, the Struldbrugg decay) is handled with period-literary restraint, not crudeness.

**Token-budget discipline:** the `positive_suffix` must stay short (the un-evictable ART_SENSIBILITY.WORLD slot — keep it lean or LOCATION evicts to a BudgetError, per the Oz/Wonderland build gotcha). Confirm the genre carries a `positive_suffix` independently (the daemon hard-requires it).

---

## 14. Content file manifest (world level — `worlds/gulliver/`)

Mirrors the Oz and Wonderland world builds:

| File | Contents |
|------|----------|
| `world.yaml` | Identity, four-voyages corpus, lethality dial (HIGH), tone-axis overrides (max menace, savage), `starting_region: the_lilliput_shore`, the bleak go-home spine. `draft: true` until assets render. |
| `tropes.yaml` | The §10 nine Gulliver tropes (authored FIRST for cross-refs). |
| `history.yaml` | The four lands' "histories" played straight (each voyage's society and how it came to be — not over-explained), **plus the ~19 POI prompts** as `points_of_interest[].visual_prompt.{solo,backdrop}`. |
| `cartography.yaml` | The §9 four-lobe region graph + `the_open_sea` seam + `the_homecoming` terminus. |
| `lore.yaml` + `legends/` | The four absurd societies, the savage-mirror thesis, the gender current; legends: `the_man_mountain` (Lilliput's view of you), `the_struldbruggs` (the immortal curse), `the_perfection_of_nature` (the Houyhnhnm ideal). |
| `cultures/` | Four cultures (`lilliputians`, `brobdingnagians`, `laputans`, `houyhnhnms_and_yahoos`) with `word_list` name slots (§7) — never Markov. |
| `archetypes.yaml` + `archetype_funnels.yaml` | The Gulliver-tinted surface of the five Travelers (§11); `typical_classes`/`typical_races` reuse the live genre `rules.yaml` values (as Oz/Wonderland do). |
| `npcs.yaml` | The §8 Swift roster as pre-gen "NPCs nearby, not yet met" with Living-World goals. NPC ids must match cartography `ref`s. |
| `openings.yaml` | The wreck on `the_lilliput_shore` (the binding-by-threads waking), solo + MP, **unified Opening schema** (`triggers.mode` solo/multiplayer, `establishing_narration`, `first_turn_invitation` with no `?`). |
| `visual_style.yaml` | Morten 1865 aesthetic; lean positive_suffix (§13). |
| `portrait_manifest.yaml` | The §8 roster portraits (Morten; assets rendered later). |
| `premises.draft.yaml` (DRAFT) | The §12 single spanning Premise + four Blocs — flagged pending oq-3 schema lock, not wired, not declared. |

---

## 15. Out of scope (this pass)

- **Asset *rendering*** — manifests + prompts authored now; portraits and POI landscapes rendered later (the oq-1 `--shard` daemon pass + R2 upload, per the Oz/Wonderland pipeline). World stays `draft: true` until assets land.
- **Premise/Bloc *wiring*** — content identity drafted; wired only when the oq-3 belief-engine schema lands. If a Gulliver confrontation can't be expressed in native content + the (eventual) Premise schema, that is a finding to route, not a license to write engine code.
- **Music** (ACE-Step) — deferred to a later pass.
- **Per-voyage worlds** — the four voyages are lobes of *one* world, not four packs/worlds.

---

## 16. Validation gates (lessons from the Oz and Wonderland builds)

- **Run `load_genre_pack` (the loader), not just `validate pack`** — the loader is the real wiring gate; it catches `draft: true` silently skipping the world, enum/tone fields (visibility tone, `triggers.mode` solo/multiplayer **not** "mp"), and `openings.yaml` needing the unified Opening schema. A validator PASS 0/0 is not proof the world loads. The loader smoke-test flips `draft: false` *temporarily* (via a `trap … EXIT` to restore), asserts `gulliver` is in `p.worlds`, and asserts **every cartography npc `binding.ref` resolves against `authored_npcs` ids**.
- **UI chrome archetype** — `wry_whimsy` already maps to `parchment` (sidequest-ui #312); a new *world* under an existing pack inherits it (the throw-on-unknown is keyed to the genre slug, unchanged), so **no UI change is needed**.
- **Unquoted `': '` in a `list[str]` item silently coerces to a dict** — only the loader catches it. Quote the item or use a `>-` block in `npcs.yaml` goals, lore bullets, and culture slots.
- **Token budget** — keep the Morten `positive_suffix` and per-POI/portrait prose short, or LOCATION evicts and renders BudgetError. Dry-run POI + portrait compose for the 512-token budget.
- **Confrontation crunch lives in genre `rules.yaml`**, not world files; world `confrontations.yaml`/`faction_agendas.yaml` are engine-unwired. Gulliver authors **neither** — only flavor + dials; the Bang catalog is already at genre level.
- **Final cliche-judge pass** — every named entity evaluated against the cliche-granularity rubric (Swift specifics are the granularity floor: Quinbus Flestrin, Lorbrulgrud, Glumdalclitch, the Struldbruggs, "the thing which is not", Tramecksan/Slamecksan — not "tiny people"/"giants"/"smart-people island"/"horse-people").
