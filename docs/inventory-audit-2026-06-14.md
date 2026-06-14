# Inventory Audit — All Genres & Worlds vs. Bound SRDs

**Date:** 2026-06-14
**Auditor:** GM agent
**Scope:** Every `inventory.yaml` / `equipment_tables.yaml` / `items.yaml` across 11 genre packs + 22 worlds, measured against the equipment chapter of each pack's bound ruleset SRD (`~/Documents/DriveThruRPG/`).
**Stance:** Read-only audit. SOUL frame — *Bind the Ruleset, Don't Balance It* (ADR-143/144) applied to **content**: if a genre binds WWN, the gear should *be* WWN gear, not bespoke gear tuned to look WWN.

---

## The headline

**Across all 11 packs, inventory is hand-authored bespoke flavor with a ruleset-*shaped* mechanical envelope bolted on. Not one pack sources its gear from the bound SRD's equipment chapter.** Item names and prices are invented; damage dice / AC / shock are tuned by hand to "look right" for the ruleset. The SRDs *do* carry the goods (WWN ~90 items, CWN ~150+, SWN ~200, AWN ~200+, all with coherent stat schemas) — they have simply never been extracted.

This is the inventory equivalent of the native-mechanics-balancing trap: we re-author and hand-tune gear instead of inheriting the already-balanced catalog the binding was meant to give us.

A second, independent finding: **the four Fate genres can't source from an SRD at all** — Fate Core has *no* equipment economy (confirmed: zero items, gear = aspects/permissions/stunts, no prices). They currently ship Without-Number-shaped priced catalogs that mismatch the ruleset they're meant to bind.

---

## Master matrix

| Genre | Ruleset | SRD source (licensing) | Placement | SRD-traceable? | Duplication | Worst concrete defect |
|---|---|---|---|---|---|---|
| caverns_and_claudes | wwn | WWN — **CC0 ✓** | **genre ❌ ADR-140** | bespoke (only armor AC traces) | — | duplicate `armor_class` key; `chain_shirt`/`helmet` have no AC; name-corpus is **5e SRD 5.1** (wrong system) |
| elemental_harmony | wwn | WWN — CC0 | world ✓ | schema traces, names bespoke | ~90% shared across 2 worlds | `unarmed_strike` modeled as a catalog item; copy-paste drift risk |
| heavy_metal | wwn | WWN — CC0 | world ✓ | partial / bespoke | **barsoom == long_foundry byte-identical** | **evropi weapons/armor have NO damage dice or AC at all** — unresolvable under WWN; barsoom `items.yaml` props (radium_rifle) unstatted & unwired |
| mutant_wasteland | awn | AWN — **no open license ⚠** | layered ✓ (best layering) | partial (System Strain wired ✓) | — | **broken artifact ref**: chargen offers `power_glove`, world catalog (replaces genre wholesale) dropped it → fallback-to-weapon regression; genre `scrap_armor` has no mitigation |
| neon_dystopia | cwn | CWN — CC0 (verify) | **genre ❌** | partial | — | cyberware is a **tag, not a `system_strain` field** (the defining CWN mechanic is prose-only); orphan loadout keys `Nomad`/`Ghost` (dead kits + gold) |
| road_warrior | cwn | CWN — has a full **vehicle chapter** | **genre ❌** | personal gear partial; **vehicular = bespoke homebrew, dormant** | — | rig Composure/vessels are stringly-typed (`"composure:8"`), admittedly unparsed, dormant — the ADR-143 "balance the homebrew" trap; CWN's vehicle rules are cited in comments but **not bound** |
| space_opera | swn | SWN — **no open license ⚠** | world ✓ | bespoke | **3 files BYTE-IDENTICAL** (100%) | total triplication, **zero** world-specific gear in any of 3 worlds; no TL tags |
| pulp_noir | **Fate** | none (Fate has no gear economy) | **genre ❌** | n/a — WN-scaffold mismatch | — | `ruleset:` not declared (runs native); priced `value`+`starting_gold` economy under Fate |
| spaghetti_western | **Fate** | none | world ✓ | n/a — mismatch | **dust_and_lead == the_real_mccoy identical** | mccoy ships generic West catalog despite a rich `inventions.yaml`; no `ruleset: fate` |
| tea_and_murder | **Fate** | none | **both ❌** | n/a — mismatch | `starting_gold` copy-pasted genre→worlds | priced economy + gold under a no-combat cosy mystery; no `ruleset: fate` |
| wry_whimsy | **Fate** (declares `native`) | none | **genre ❌** | — | n/a — mismatch | **explicit `ruleset: native`** (loudest drift vs ADR-144); ships `value`/`Oddments`/`starting_gold` despite prose that disclaims any economy |

---

## What the SRDs actually offer (the source we're not using)

| SRD | Equipment chapter? | ~Items | Key stat fields | Licensing |
|---|---|---|---|---|
| **WWN** | §3.0.0 | ~90 | Weapon: `dmg, shock(N/AC X), attribute, range, traits[], cost(sp), enc` · Armor: `ac, cost, enc` · Gear: `cost, enc` | **CC0 — verbatim reuse, no attribution** |
| **CWN** | §3.0.0 (richest) | ~150 base / 350+ w/ mods | Armor: `rangedAC, meleeAC, soak, enc, traumaTargetMod, obviousness, cost` · Weapon: `dmg, range, cost, mag, attr, enc, traumaDie, traumaRating` · Cyberware: `cost, location, conc, systemStrain` · + cyberdeck/drone/vehicle schemas | SRD; Sine Nomine CC0 (license page not re-verified) |
| **SWN Rev (Free)** | 2 chapters | ~200–230 | Armor: `ac, cost, enc, tl` · Ranged: `dmg, range, cost, mag, attr, enc, tl` · Melee: `dmg, shock, attr, cost, enc, tl` · + full starship schema | **No OGL/CC in the free PDF** — copyright only |
| **AWN (Free)** | "Equipment" | ~200 statted + ~150 d100 goods | Weapon: `dmg, range, cost, mag, attr, enc, traumaDie, traumaRating, tl` · Armor: `ac, enc, traumaTargetMod, subtle, cost, tl` · + mods/scrap/vehicles | **No OGL/CC** — © 2025, all rights reserved |
| **Fate Core** | **none** | **0** | optional abstract `Weapon:N`/`Armor:N` (1–4); gear = aspects/stunts/permissions; no cost | OGL + CC-BY text; logos TM |

**Shared schema across the four Without Number games:** `{name, damage, attribute, encumbrance, cost, tech_level?, traits[]}` + category extras (`shock` for melee, `range`+`magazine` for ranged, `trauma_die`+`trauma_rating` for CWN/AWN, `system_strain` for cyberware). One SideQuest item schema covers all four.

### Licensing reality (load-bearing for "source from the SRD")
- **WWN is CC0** — we can reproduce its ~90-item table verbatim, today, no attribution. This is the clean win.
- **CWN** is the published SRD; almost certainly CC0 but the license page wasn't re-confirmed in this pass — **verify before bulk-importing.**
- **SWN Free** and **AWN Free** editions carry **no open license** — we can *derive/compat* but **not copy verbatim**. The full SWN OGL/SRD is a separate doc we don't have on disk.
- **Fate** text is OGL/CC-BY, but there's nothing to import — gear is not a catalog.

---

## Structural findings (cross-cutting)

1. **No SRD sourcing anywhere.** Universal. The fix is extraction, not re-authoring.
2. **No pack uses encumbrance / readied-stowed slots or tech_level** — the WWN/SWN/AWN encumbrance + TL model is entirely absent. CWN's System Strain is wired only in mutant_wasteland (implants); neon leaves it as prose.
3. **ADR-140 placement is split 5/6.** Compliant (world-level catalog): elemental_harmony, heavy_metal, space_opera, spaghetti_western, mutant_wasteland (layered). Violating (genre-level catalog): caverns_and_claudes, neon_dystopia, road_warrior, pulp_noir, tea_and_murder (both tiers), wry_whimsy.
4. **Massive duplication where worlds share a genre:**
   - space_opera — 3 byte-identical files (worst).
   - heavy_metal — barsoom == long_foundry.
   - spaghetti_western — dust_and_lead == the_real_mccoy.
   - elemental_harmony — ~90% shared, copy-paste maintained.
   This is the case *for* a genre-level shared baseline (the SRD core) + thin world overrides — which is also exactly how SRD-sourced gear would land.
5. **The Fate quartet is a ruleset mismatch, not just an inventory gap.** All four ship the strict `extra="forbid"` Without-Number `CatalogItem` record (priced/weighted/power-tiered) + `starting_gold`. None declares `ruleset: fate`. Closing the gap is a schema + ruleset change (route to Dev), not an inventory rewrite. Best current instincts: five_points "charms" and wry_whimsy "anchors" push mechanical bite into `lore` prose as permissions — that's the Fate-correct direction.
6. **road_warrior's vehicular core is the ADR-143 trap in the wild** — bespoke Rig Composure homebrew, dormant, stringly-typed, while CWN ships a bindable vehicle chapter (speed/armor/AC/HP/crew/hardpoints). The genre's whole identity layer is the un-bound part.

---

## Concrete defects to fix (content side — GM can do these)

- **heavy_metal/evropi** — every weapon/armor entry is missing `damage`/`armor_class`; under WWN the looted kit resolves to nothing. (Highest mechanical severity.)
- **mutant_wasteland/seaboard_of_saints** — add the (de-genericized) `power_glove` to the world catalog; chargen offers it and the wholesale-replace dropped it.
- **caverns_and_claudes** — remove duplicate `armor_class` key on `leather_armor`; add AC to `chain_shirt`/`helmet_iron`.
- **heavy_metal/barsoom** & **spaghetti_western/the_real_mccoy** — both ship a verbatim copy of a sibling world's catalog with no world-specific gear despite distinct settings (and, for mccoy, a rich `inventions.yaml` to draw from).
- **space_opera** — collapse the 3 identical files; give each world ≥a few bespoke items.

## Route to Dev (code side — not GM)

- Orphan loadout keys `Nomad`/`Ghost` in neon_dystopia (no backing archetype/class).
- `extra="forbid"` `CatalogItem` model blocks adding Fate `aspect:`/`stunt:`/`permission:` fields — needed before the Fate quartet can be modeled correctly.
- `ruleset: fate` declaration + Fate resolution path for the four Fate genres (ADR-144 is currently *deferred*).
- CWN vehicle-chapter binding for road_warrior (vs. the dormant bespoke Composure).
- An SRD→inventory.yaml extraction tool (WWN first — it's CC0).

---

## Recommended sequencing

1. **Land the clean win: WWN is CC0.** Extract the ~90-item WWN equipment table into a canonical genre-level baseline the three WWN genres inherit, with worlds overriding only bespoke gear. Fixes sourcing + duplication + evropi's missing stats in one move.
2. **Verify CWN's CC0 license page**, then do the same for neon_dystopia + road_warrior (and bind CWN vehicles for road_warrior).
3. **SWN / AWN: derive, don't copy** (no open license) — re-stat against the SRD schema rather than reproducing tables verbatim.
4. **Fate quartet is a separate track** — it's a ruleset-binding + schema decision (Keith owns the crunch call), not an SRD import. Decide whether Fate gear becomes aspect/permission records and flip `ruleset: fate`.
5. Fix the standalone content defects (evropi, seaboard, caverns) immediately regardless of the above.
