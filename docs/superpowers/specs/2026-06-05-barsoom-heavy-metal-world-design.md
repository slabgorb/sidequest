# Barsoom — A Faithful-Source World on the `heavy_metal` (WWN) Chassis

**Date:** 2026-06-05
**Status:** Draft (brainstorming) — world design; epic decomposition included, Story 1 scoped for implementation
**Author:** GM (Game Master)
**Genre host:** `heavy_metal` (bound to `ruleset: wwn` per the 2026-06-04 port; clean WWN chassis after the pact/ledger flavor was pruned out of the rules)
**Source of truth (faithful port, do not redesign):** Edgar Rice Burroughs, the *Barsoom* novels (*A Princess of Mars* 1912 through the later books). US public domain — rights-clean. Frank Frazetta / Roy Krenkel / Michael Whelan as the visual canon.

---

## 1. Problem / Intent

Author a new world, **`barsoom`**, under the `heavy_metal` genre pack: Edgar Rice Burroughs' Mars, rendered faithfully as **heroic sword-and-planet pulp**. The world inherits heavy_metal's now-clean WWN mechanics (ablative-HP combat, `hp_depletion`, negotiation, chase, `cast_spell` High Magic) and supplies **all flavor at the world tier** — peoples, factions, geography, magic content, openings, naming, and a complete visual override.

Two framing facts drive every decision:

1. **Faithful to source.** This is a *port of Burroughs*, not a grimdark refraction. No elegiac doom, no blood-ledger magic. The dying planet is texture for a world worth fighting *for*, not mourning. (Keith, 2026-06-05: "stay true to source.")
2. **Crunch in Genre, Flavor in World.** heavy_metal's WWN rules are fixed and inherited. Barsoom does not redesign mechanics; where Barsoom genuinely needs a mechanical hook (the Earthman boon, green-Martian physiology), it is flagged as a **crunch call for Keith** and the tier of expression is decided explicitly — never smuggled into world flavor as unwired "authored crunch with no backing."

## 2. Locked decisions (with Keith, 2026-06-05)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **PC origins = native Barsoomian cultures + a transported-Earthman origin.** Players build their own PCs, not John Carter. Native peoples are selectable cultures; the Earthman is one selectable origin carrying the signature gravity boon. | Widest table appeal; lets one player be the Carter-figure while others are red Martians / Tharks. Faithful to the *world*, not locked to one POV. |
| D2 | **Scope = whole planet from the jump.** All major regions/cultures of the 11-book sweep are authored content: the red empires, the green hordes, the southern Therns / First Born / Issus / Valley Dor, the northern Okar yellow-men, and Lothar. | Keith's call. Mitigated by the phased decomposition in §7 — a *playable* core ships first, the rest expands in ordered stories. |
| D3 | **Magic = two WWN caster traditions on the inherited High Magic engine** (Effort + System Strain): **Mentalist** (Lotharian) and **Super-scientist** (Ras Thavas / Phor Tak). Super-science also exists as ordinary **gear** (radium rifles, fliers). Telepathy is a low-grade **universal baseline**, narrator-framed, not a spell. | Maps Burroughs' science-romance onto WWN faithfully: Lotharian mentalism *is* "exhaust the body to force the will real" = Effort/Strain. Gives two themed `spells_wwn` lists like WWN mage traditions. |
| D4 | **Multiple openings (solo + MP, per-origin); Helium is the default `starting_location` anchor.** Variety lives in the openings, not in a single forced start. | Keith: "you can have multiple openings, solo, mp. This is an authoring problem not a structure one." |
| D5 | **The Earthman gravity boon = a world-tier origin trait with light, concrete mechanics** (e.g. a leap/jump bonus or a once-per-scene mighty leap; STR-feat edge). The **tier exception is documented**, and the trait's **engine consumer is verified** before it ships — no narrator-only fake crunch. | Keith chose "world-tier origin trait, light mechanics." Sebastien/Jade can see the number. Risk owned: a mechanical advantage living in world flavor — see §9. |
| D6 | **Faithful, not reinvented.** Geography, peoples, factions, and magic are lifted from Burroughs; only the mechanical *expression* is adapted to WWN. | "A port is a port." |

## 3. Identity & tone

Barsoom is **heroic sword-and-planet pulp** — Burroughs by way of Frazetta. Honor culture, romance, brutal-but-noble combat, a dying alien world of ochre dead-sea-bottoms and ancient ruins. This is the **opposite** of heavy_metal's old (pruned) elegiac doom.

The world sets its own `axis_snapshot` to dial *toward* heroism. Proposed (subject to the genre's current axis set — verify the live `axes.yaml` ids at authoring time; the genre historically carried `comedy/gravity/outlook`, while Evrópí's `world.yaml` used `hope/tech_level/weirdness` — reconcile against whatever the loader actually reads):

- **hope: high** — a world worth saving; the hero can win.
- **gravity / stakes: high but not crushing** — combat is lethal and honor is real, but the mood is adventure, not despair.
- **comedy: low** — earnest pulp romance, wry at most, never camp.
- **tech_level: low-to-mid** — radium rifles and fliers exist, but the **blade is prized by code**; honor demands steel.
- **weirdness: high** — a dying alien world of four-armed green giants, two hurtling moons, phantom bowmen, and brain-transplant science.

## 4. Peoples (`worlds/barsoom/cultures.yaml` + the Earthman origin)

WWN has **no hard race mechanics** — cultures are flavor + naming + archetype funnel. Where a people has a genuinely mechanical body (green-Martian four arms / size), that is a **crunch flag** (§9), not a silent world-tier stat block.

- **Red Martians** — copper-skinned, oviparous, ~1000-year lifespan; the civilized empires (Helium, Zodanga, Ptarth, Kaol, Dusar, Phundahl, Toonol). The "default people"; honor-bound, jealous, brilliant. Default PC culture.
- **Green Martians** — ~15 feet, four-armed, tusked, olive-green nomad hordes (Thark, Warhoon). Communal, loveless by custom, savage honor, masters of the dead sea bottoms and their war-mounts. *(Four arms / size = crunch flag — fiction-only, or a light trait?)*
- **Black First Born** — the southern "black pirates" of the buried sea of Omean, self-styled living gods, raiders of the Thern temples, worshippers of Issus.
- **White Therns** — bald false-priests of the southern death-cult, wig-wearing, preying on the pilgrims who voyage down the River Iss to the "heaven" of the Valley Dor.
- **Yellow Okarians** — bearded men of the frozen north, in domed hothouse cities under the ice (Okar, Marentina), behind the Carrion Caves.
- **Lotharians** — the last remnant of an ancient white seafaring race, survivors by mentalism: they conjure phantom bowmen real enough to kill, and some sustain their own bodies by will alone. Home of the Mentalist tradition.
- **Earthman origin** — the transported stranger (the Carter / Ulysses Paxton figure). Carries the world-tier gravity-leap trait (D5). Selectable on top of, or instead of, a native culture per the chargen surface.

## 5. Faction / political map

Built-in conflict, wall to wall:

- **The red empires** — Helium (the protagonist civilization) vs. Zodanga (its assassin-guild rival); the courts of Ptarth, Kaol, Dusar, Phundahl, Toonol in shifting alliance and feud.
- **The green hordes** — Thark and Warhoon, perpetually at war with each other and with all red cities.
- **The Holy Therns + Cult of Issus** — the great southern religious fraud running the Valley Dor death-pilgrimage.
- **The First Born of Omean** — Issus-worshipping black raiders who prey on the Therns who prey on the pilgrims (a three-tier predation stack).
- **The Okar yellow throne** — Salensus Oll's domed northern kingdom; Marentina the dissident exception.
- **Lothar** — isolationist phantom-conjurers, the last of an older Mars.
- **Ras Thavas, the master mind** — brain-transplant super-science at his island laboratory; the home of the Super-scientist tradition and its moral horrors (synthetic life, body-theft).

Living-World goals belong in `npcs.yaml` (the wired path), not in `faction_agendas.yaml` (zero engine consumers — see §9).

## 6. Magic content (two WWN caster traditions)

Two themed `spells_wwn` lists, both on the inherited Effort + System Strain engine; `cast_spell` is `class_filter`'d to the two caster classes only (without the filter, the cast resource gate never fires):

- **Mentalist (Lotharian)** — phantasm-conjuring (the bowmen), telepathic domination, hypnotic suggestion, mind-shielding, sense-deception. Effort/Strain = the body exhausting itself to force the mind's will into reality (canon-exact for Lothar).
- **Super-scientist (Ras Thavas / Phor Tak)** — device-effects as "spells": disintegration ray, invisibility compound, synthetic-life vat, the brain-swap. The grotesque-cost flavor that heavy_metal's retired ledger magic used to carry can be re-homed *here*, in spell descriptions, without a bespoke subsystem.
- **Telepathy** — a low-grade *universal baseline* (everyone reads surface thought unless shielded), narrator-framed, not a spell. This is the Barsoomian default and should be reflected in narrator hints, not the spell list.
- **Super-science as gear** — radium rifles, radium pistols, fliers on the buoyancy ray, mechanical telepathy: ordinary inventory so non-casters get the pulp toys. Authored in `inventory.yaml` overrides, not the spell list.

**Reconcile `magic_level: high`** (genre tier) with Barsoom being canonically *low-magic*: "high" is the engine being *available*, not a frequency claim. Casters stay **rare** via culture/archetype funnels (Mentalists are Lotharian-gated; Super-scientists are a tiny mad-genius minority). Confirm at authoring time whether a world can/needs to touch `magic_level` at all.

## 7. Epic decomposition (whole-planet is too big for one spec)

Ordered stories, each its own plan → PR cycle. A **playable** Barsoom ships at the end of Story 1.

1. **Story 1 — World skeleton + red/green core (this spec's implementable target, §8).** `world.yaml`, axes/`axis_snapshot`, the Frazetta `visual_style.yaml` override (suffix + a first pass of `visual_tag_overrides`), red + green cultures, the conlang corpora for those cultures, the dead-sea-bottom + Helium regions and their core factions/NPCs, the solo + MP openings, and a hero POI. Result: a faithful, playable Barsoom anchored on Helium and the dead sea bottoms.
2. **Story 2 — The South.** Therns, First Born, Issus, the River Iss / Valley Dor / Lost Sea of Korus / Golden Cliffs / Otz Mountains / Omean geography, cultures, and factions.
3. **Story 3 — The North & Lothar.** Okar + Marentina (domed northern cities, the Carrion Caves), and Lothar with the Mentalist tradition's home.
4. **Story 4 — Magic content.** Both `spells_wwn` lists (Mentalist + Super-scientist) in Barsoom's idiom, `cast_spell` wiring with `class_filter`, the telepathy baseline framing, and super-science gear in `inventory.yaml`.
5. **Story 5 — Chargen surface.** The Earthman origin trait (mechanics + verified engine consumer, §9), the green-Martian physiology trait (crunch call resolved), archetype funnels per culture, and the two caster traditions wired into chargen (as Foci/classes on the inherited WWN chassis vs. new — decided with Keith).
6. **Story 6 — Assets.** Portraits (`portrait_manifest.yaml`), POI landscapes, audio mood-map. Render to R2; rebuild `r2_manifest.json`. The `draft: true` gate in `world.yaml` drops once portraits + POIs are on R2.

## 8. Story 1 — World skeleton + red/green core (implementable)

**Repo:** `sidequest-content` only (no engine change — heavy_metal already loads through `get_ruleset_module("wwn")`).

### 8.1 Files
- `worlds/barsoom/world.yaml` — `name: Barsoom`, `slug: barsoom`, `draft: true` (until assets), `description`, `tagline`, `axis_snapshot`, `starting_location` (Helium), `starting_region`, `starting_time`, `cover_poi` (the Story-1 hero POI — **must match a real POI slug** or the lobby hero-shot 404s), `extensions` (e.g. `archetype_funnels`; add `magic` when Story 4 lands).
- `worlds/barsoom/cultures.yaml` — Red Martian + Green Martian (the rest land in Stories 2–3), each with naming binding + archetype funnel + flavor.
- `worlds/barsoom/visual_style.yaml` — the full Frazetta override (§10): new `positive_suffix` (style/medium/palette ONLY) + a first pass of `visual_tag_overrides` for the Story-1 locations (`dead_sea_bottom`, `red_city_plaza`, `dead_city_ruin`, `flier_deck`, `thark_camp`).
- `worlds/barsoom/npcs.yaml` — core named NPCs with Living-World goals (the wired path).
- `worlds/barsoom/openings.yaml` — the unified Opening schema (NOT the simple genre shape): solo + MP coverage via `triggers.mode`, with `establishing_narration` / `first_turn_invitation`. Per-origin variants (Earthman waking on a dead sea bottom near a Thark camp; a red-Martian in a Helium court; a green captive; etc.).
- `worlds/barsoom/history.yaml` + region/POI yaml — the dead-sea-bottom + Helium regions, with the hero POI.
- Conlang corpora — per-culture word lists for red + green Martian phonologies (§9; this is a *conlang* world, not a curated-word-list world).

### 8.2 Verification (the loader is the real gate, not `validate pack`)
Run the actual `load_genre_pack` for heavy_metal and confirm `barsoom` loads — the validator's "PASS 0/0" is not proof. The loader catches what matters: enum fields (visibility/tone), `draft: true` silently *skipping* the world (expected here until assets — confirm it's intentional, not invisible-by-accident), and `openings.yaml` needing the **unified Opening schema** (solo/MP `triggers.mode`, `establishing_narration`, `first_turn_invitation`) rather than the simple genre shape that parses hollow. NPCs must live under `authored_npcs`.

## 9. Risks / verify-before-implementing

- **Origin-trait wiring (D5).** Before shipping the Earthman boon (or a green-Martian physiology trait), **verify a real engine consumer applies a world-authored origin trait mechanically** — not narrator-only. Known trap in this codebase: world-tier extensions (`confrontations.yaml`, `faction_agendas.yaml`) are engine-unwired; confrontation mechanics load only from genre `rules.yaml`. If origin traits have no mechanical consumer at the world tier, the boon must either (a) be expressed through a mechanism that *is* wired (archetype funnel / chargen surface), or (b) be escalated to a genre-tier crunch spec. Do not author a stat the engine never reads.
- **Green-Martian physiology.** Four arms (extra attacks? extra carry?) and 15-foot size are a crunch call. Decide fiction-only vs. light-trait *with* Keith, and only ship a mechanical version if it has a consumer.
- **Super-scientist tradition vs. inherited WWN Mage.** Decide whether the two traditions are new caster classes or Foci/spell-list reskins on the inherited Warrior/Expert/Mage chassis. Crunch call; Story 5.
- **`magic_level: high` vs. rare casters.** Reconcile per §6; confirm whether a world override of `magic_level` is supported or whether rarity is purely funnel-gated.
- **Whole-planet authoring surface.** Large. Mitigated by the §7 decomposition — ship the playable core first.
- **Conlang corpora.** Six+ culture phonologies eventually (red/green/black/white/yellow/Lotharian). Barsoom names are Burroughs-*invented* with a real phonology (Tars Tarkas, Kantos Kan, Dejah Thoris, Xodar) → **conlang Markov per culture** (ADR-091), *not* curated real-world word lists. Story 1 needs red + green corpora.
- **Scanty-dress modesty.** Canon Martian dress is minimal; all renders use the §10 SOUL-safe clause (covered, non-sexualized) — the heroic look without cheesecake.
- **Canonical names as text in images.** Z-Image paints proper nouns it sees (Helium, Issus). Render prompts use visual archetypes ("ornate red-Martian city of scarlet towers"), never the place name.

## 10. Visual direction (`worlds/barsoom/visual_style.yaml`)

**Identity:** lush **painterly heroic oil** — the canonical Barsoom look. Sun-baked, romantic, vast.

**Style anchors:** Frank Frazetta, Roy Krenkel (the ERB/Ace illustrator), Michael Whelan (the DAW covers). All *painterly oil* — **no comic/ink artists named** (per the Z-Image guide, "a style anchor imports its whole medium"; naming a comic lineage renders flat cel — naming Frazetta/Whelan renders lush oil, which is the target).

**Palette:** ochre and rust-red dead-sea-bottom, pale ochre sea-moss, umber and bone-marble ruins, crimson-and-gold red-Martian harness, brass-and-leather fittings, a wan small sun in a clear sky shading rose-to-violet, deep indigo night under two small swift moons. (Named colors override the stated medium — exploit deliberately.)

**Light:** hard low sun through *thin air* — high contrast, long shadows, brilliant clear sky. Big skies kept as **bare painted gradient, no hatching** (moiré rule; oil is hatch-free anyway).

**World `positive_suffix` (style/medium/palette ONLY — no setting nouns, or they bleed into every portrait):**
> heroic sword-and-planet oil painting in the tradition of Frank Frazetta, Roy Krenkel, and Michael Whelan, lush painterly brushwork and rich tonal modeling, romantic dramatic composition, sun-baked palette of ochre and rust-red, pale sea-moss green, bone marble, crimson and gold, brass and worn leather, a wan small sun in a clear sky shading from rose to violet, hard low-angle light through thin air with long shadows and high contrast, vast melancholy-beautiful dying-world atmosphere. No text, no caption, no title, no writing, no labels, no signature, no watermark, no frame, no border.

**SOUL/modesty clause (Barsoom-specific, appended to human prompts):**
> adult, dignified martial bearing, ornamented leather harness and battle-girdle over fitted body-garb, modest and fully covered, non-sexualized depiction, correct anatomy, natural hands.

**`visual_tag_overrides` to author** (replacing the genre's doom tags, which do not exist on Mars): `dead_sea_bottom`, `red_city_plaza`, `dead_city_ruin`, `atmosphere_plant`, `flier_deck`, `thark_camp`, `valley_dor`, `okar_dome`, `lothar`. Invented nouns (thoat, flier, zitidar) always paired with a visual archetype so the model has something to paint.

**Sample prompts (authored to the guide — renderable once the Story-1 skeleton lands):**

*Hero POI — dead sea bottom & dead city:*
> heroic sword-and-planet oil painting in the tradition of Frank Frazetta and Roy Krenkel, lush painterly brushwork. Wide low-angle landscape. Foreground: a cracked ochre plain of dried sea-floor scattered with pale yellow moss and bone-white stones, a lone armored warrior in crimson-and-brass leather harness standing with a long-sword. Middle ground: the ruins of an ancient marble city — toppled colonnades and a broken dome half-drowned in ochre moss. Background: low red hills under a vast clear sky shading rose to violet, a wan small sun low on the horizon, two faint small moons. Hard raking light, long shadows, high contrast, thin dry air. Vast, romantic, melancholy. No text, no caption, no labels, no signature, no watermark, no frame.

*Portrait — a red-Martian warrior:*
> heroic fantasy oil portrait in the tradition of Michael Whelan and Frank Frazetta, lush painterly rendering. Chest-up portrait of an adult red-Martian — smooth copper-red skin, black hair, level dark eyes, a calm proud expression. Ornamented leather harness with brass studs and a jeweled shoulder-strap over fitted dark body-garb, modest and fully covered, non-sexualized. Plain warm ochre background. Hard low side-light, rich shadow. No text, no caption, no labels, no signature, no watermark. Correct anatomy, natural hands.

## 11. Non-goals (Story 1)
- No southern/northern/Lothar content (Stories 2–3). No magic content or `cast_spell` wiring (Story 4). No chargen-trait mechanics (Story 5). No rendered assets (Story 6; `draft: true` holds the gate).
- **No engine changes.** This is content authoring on an already-bound ruleset. Any mechanical need (origin boon, green physiology) is a *flagged crunch call* for Keith, resolved before its story, not invented in world YAML.
- No genre-tier edits. Barsoom is a world; heavy_metal's WWN chassis and the epic-87 cleanup of the leftover `pact_working`/`debt_collection` confrontations are out of scope.
