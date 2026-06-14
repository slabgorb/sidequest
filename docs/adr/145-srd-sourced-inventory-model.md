---
id: 145
title: "SRD-Sourced Inventory — Bind the Equipment Catalog, Don't Author It; Per-Ruleset Reproduce-vs-Derive Licensing and CatalogItem Provenance"
status: accepted
date: 2026-06-14
deciders: ["Keith Avery", "Naomi Nagata (Architect)"]
supersedes: []
superseded-by: null
related: [3, 117, 120, 121, 140, 142, 143, 144]
tags: [game-systems, core-architecture]
implementation-status: deferred
implementation-pointer: "Design only — implemented by epic 114 stories 114-3 (extraction tool), 114-4/5/6/7/8 (per-ruleset pack migration), 114-9/10 (Fate gear model). Schema target: sidequest-server/sidequest/genre/models/inventory.py CatalogItem."
---

# ADR-145: SRD-Sourced Inventory — Bind the Equipment Catalog, Don't Author It

> **This is the inventory analogue of ADR-143/144.** ADR-143 bound the Without
> Number ruleset *so we never balance combat math*. ADR-144 bound Fate Core *so we
> never maintain a homebrew ruleset*. Both record the same lesson: **published,
> already-balanced systems are inherited, not re-authored.** This ADR applies that
> lesson to **gear**. The inventory audit (`docs/inventory-audit-2026-06-14.md`)
> found that across all 11 packs, *not one* sources its equipment from the bound
> SRD's equipment chapter — every pack hand-authors bespoke items with a
> ruleset-*shaped* mechanical envelope bolted on, hand-tuning damage dice / AC /
> shock to "look right." That is the inventory equivalent of the native-balancing
> trap ADR-143 exists to stop: we re-author and hand-tune the catalog instead of
> inheriting the one the binding was meant to give us. Operator framing, carried
> forward from ADR-143/144: *something has to give, and SRDs are for this.*

## Context

### What "bind, don't balance" means for content

ADR-143/144 made `ruleset:` a binding to a published *resolution* system. The
binding's whole value is that the math is already balanced — `d20 + hit vs AC`,
weapon dice, Shock, the Fate ladder. But a ruleset is not only resolution rules;
**every Without Number SRD ships a full, internally-balanced equipment chapter**,
and the gear *is part of the balanced system*. A WWN longsword does `1d8 + shock`
because that is what the WWN combat math is calibrated against. Hand-authoring a
`1d6` "short sword" with an invented price is exactly the move ADR-143 forbids,
moved one layer down: we are silently re-balancing the system by re-statting its
gear.

The SRDs carry the goods and we have never used them
(`docs/inventory-audit-2026-06-14.md`):

| SRD | Equipment chapter | ~Items | Licensing |
|---|---|---|---|
| **WWN** | §3.0.0 | ~90 | **WN SRD free-use — reproduce verbatim** |
| **CWN** | §3.0.0 (richest) | ~150 base / 350+ w/ mods | **WN SRD free-use — reproduce verbatim** |
| **SWN Rev** | 2 chapters | ~200–230 | **WN SRD free-use — reproduce verbatim** |
| **AWN** | "Equipment" | ~200 statted + ~150 d100 | **WN SRD free-use — reproduce verbatim** |
| **Fate Core** | **none** | **0** | OGL + CC-BY; gear = aspects/permissions/stunts, no economy |

The original audit recorded uncertain/restrictive licensing for the WN line
(CC0-on-WWN, "CWN unverified," SWN/AWN free-editions copyright-only). **That is
superseded.** Sine Nomine's standing public policy, stated in the Without Number
SRD documents themselves, is that the WN SRDs are *free for anyone to use for any
purpose.* This covers **all four** — WWN, CWN, SWN, AWN — and is the operative
license basis for D4. (Written correspondence on file in project records,
2026-06-14, corroborates the public SRD terms; the *basis* is the published
free-use policy, not any personal grant.)

The four Without Number SRDs share a common item schema —
`{name, damage, attribute, encumbrance, cost, tech_level?, traits[]}` plus
category extras (`shock` for melee, `range`+`magazine` for ranged,
`trauma_die`+`trauma_rating` for CWN/AWN, `system_strain` for cyberware). One
SideQuest item schema already covers all four. Fate is the odd one out: it has no
equipment economy at all, which is why the Fate gear model is deferred to ADR-144
/ story 114-9 (the seam is acknowledged in D5, not designed here).

### What the audit found wrong (the forces)

1. **No SRD sourcing anywhere.** Universal. Names and prices are invented; stats
   are hand-tuned to "look right." The fix is *extraction*, not re-authoring.
2. **Massive duplication where worlds share a genre.** space_opera ships 3
   byte-identical files; heavy_metal/barsoom == long_foundry; spaghetti_western
   dust_and_lead == the_real_mccoy; elemental_harmony ~90% shared, copy-paste
   maintained. This is the case *for* a shared baseline catalog + thin world
   overrides — which is exactly the shape SRD-sourced gear takes.
3. **Real mechanical defects from hand-authoring.** heavy_metal/evropi weapons
   and armor have *no* `damage`/`armor_class` at all — under WWN the looted kit
   resolves to nothing. An extracted SRD baseline would have filled those by
   construction.
4. **ADR-140 placement is split 5/6.** Six packs put the catalog at the genre
   tier in violation of ADR-140 (genre = rulebook; world = catalog).
5. **Provenance is comments, not data.** Today the only record that
   `leather_armor` came from WWN is a YAML comment ("Source: WWN SRD"). The
   `CatalogItem` model has no `source`/`license`/`provenance` field. There is no
   machine-checkable way to assert "this item is the verbatim WWN SRD mechanics"
   vs. "this item is bespoke homebrew" vs. "this is a world reskin of an SRD item."
   The extraction tooling (114-3) and any licensing audit need this to be data.

### What exists today (grounding — do not re-decide)

**The strict catalog model** (`sidequest-server/sidequest/genre/models/inventory.py`):

```python
class CatalogItem(BaseModel):
    model_config = {"extra": "forbid"}      # strict — no unknown fields
    id: str
    name: str
    description: str
    category: str
    value: int = 0
    weight: float = 0.0
    rarity: str = ""
    power_level: int = 0
    tags: list[str] = Field(default_factory=list)
    lore: str = ""
    narrative_weight: Any = None
    resource_ticks: int | None = None
    damage: DamageSpec | None = None        # weapons
    mitigation: int | None = None           # armor: flat soak
    armor_class: int | None = None          # armor: ascending AC
    heal_amount: str | None = None          # consumable
```

`InventoryConfig` (`item_catalog`, `starting_equipment`, `starting_gold`,
`currency`, `philosophy`) and `DamageSpec` (`dice`, `bonus`, `armor_piercing`,
`trauma_die`, `trauma_rating`, `trauma_target`, `shock`, `shock_ac`) are likewise
`extra="forbid"`. `DamageSpec` already carries the WN combat fields — the
resolution side of "be WN gear" is largely present. What is missing is **TL** and
**range/magazine** on the item (needed for SWN/CWN/AWN ranged gear) and
**provenance** everywhere.

**The resolution path** (`server/dispatch/inventory_resolve.py`): world inventory
**replaces** the genre inventory wholesale — *not* merged (epic 94 / ADR-120).
This is load-bearing for D3 below: a world that ships *any* `inventory.yaml`
today drops the entire genre baseline. That is the mechanism behind the audit's
"world catalog dropped `power_glove`" regression. SRD-sourced gear forces this to
become a real merge, or to make the genre baseline non-droppable.

**A second, tolerant schema already carries `source`.** The world-tier
`corpus/items.yaml` (`WorldItem`, `extra="allow"`) already records
`source: SRD 5.1` per row. It is a *reference* corpus (a flat name/rarity list),
not the chargen `CatalogItem`, and it is the wrong system (5e SRD) for a WWN pack
— but it proves provenance-as-data is a pattern already in the tree.

## Decision

**Gear is bound, not authored. A bound ruleset's equipment chapter is extracted
once into a canonical, provenance-stamped baseline catalog at the genre tier; a
world overrides only its setting-distinct gear. `CatalogItem` grows a provenance
record and the WN ranged/TL fields; the genre↔world inventory relationship
becomes a real per-field merge with a non-droppable baseline. Reproduce-vs-derive
is set per ruleset by license and enforced by the extraction tool.**

This is five decisions: the model (D1), the schema delta (D2), placement +
merge (D3), licensing policy (D4), and the Fate seam (D5). The decision summary's
"reproduce-vs-derive is set per ruleset" stands as the *mechanism*; under the
settled WN free-use basis (D4) every WN SRD resolves to **reproduce verbatim** —
the derive path remains in the schema for future non-WN rulesets, not for the WN
line.

### D1 — What it means for gear to "be" SRD gear

An item is **SRD-sourced** when its mechanical fields (`damage`, `armor_class`,
`mitigation`, range/magazine, `tech_level`, cost, encumbrance) are the SRD's
values, carried unchanged, and its `provenance` record names the SRD and the
reproduction mode. An item is **bespoke** when those fields were chosen by a human
author. The distinction is not stylistic — it is the difference between inheriting
balanced math and silently re-balancing the system.

**Verbatim binds the MECHANICS, not the presentation (load-bearing doctrine,
Keith, 2026-06-14).** What is reproduced verbatim from the SRD is the *mechanical
envelope* — `damage`, `armor_class`/`mitigation`, attribute/skill requirements,
`tech_level`, `range_band`, `magazine`, encumbrance (`weight`), `value` (cost), and
any combat-relevant stat. Those are the balanced numbers we bind **precisely so we
never re-tune them**: the ADR-143 forbidden move applies in full — hand-adjusting a
bound item's stats to "fit" a world is prohibited. On TOP of that fixed mechanical
envelope sits a freely-authorable **flavor/reskin layer** — `name`, `description`,
and any visual/world-flavor fields — which a genre or world may override at will,
exactly per SOUL.md *Crunch in the Genre, Flavor in the World.* A reskinned item is
**still the SRD item, mechanically**: it keeps `mode: verbatim` and its `srd_ref`;
the reskin is recorded as a flavor override, never a new `bespoke` item.

> **Example.** WWN "Sword, Long" — stats bound verbatim (`1d8`, the SRD's cost and
> encumbrance) — presents as **"Vibroblade"** in a space-opera world. Same numbers,
> world-owned name and description. `provenance.mode` stays `verbatim`;
> `provenance.srd_ref` still points to the WWN longsword; only the presentation
> fields differ. This is the same genre/world split the whole project runs on,
> applied to gear.

Three reproduction modes (this is the load-bearing taxonomy). **Mode describes the
*mechanical envelope* only** — presentation is always freely overridable regardless
of mode:

- **`verbatim`** — the SRD entry's *mechanics* are reproduced exactly. **This is the
  mode for all four WN SRDs** (WWN, CWN, SWN, AWN) under their free-use terms (D4).
  The stats are the SRD's and are locked; the name/description may be reskinned per
  genre/world without changing the mode.
- **`derived`** — the *mechanics* are re-statted/paraphrased against an SRD schema
  but not copied. **No WN SRD requires this** — it is retained in the taxonomy for a
  *future* non-WN ruleset whose license permits derivation but not verbatim reuse.
- **`bespoke`** — invented gear with no SRD basis. *Permitted at the world tier*
  for setting-distinct items (heavy_metal/barsoom's radium rifle, a world's
  signature artifact) — flavor the world owns. A bespoke item still uses the
  ruleset-shaped mechanical fields so it resolves, but it is *not* claiming to be
  balanced SRD content, and the GM panel can tell the two apart.

The doctrine: **the baseline catalog is `verbatim` (for the WN line) or, for a
future derive-only ruleset, `derived` — never `bespoke`; bespoke is a world-tier
privilege, not a baseline shortcut.** A world reskinning a baseline item is **not**
authoring a bespoke item — it is overriding presentation on an inherited verbatim
item (see D3's per-field merge). The extraction tool refuses to emit a mode a
ruleset's license does not permit (D4).

### D2 — Schema delta on `CatalogItem`

Add a `provenance` record and the missing WN ranged/TL fields. The strict
`extra="forbid"` stays — provenance is a first-class field, not loose metadata,
because the extraction tool and the licensing audit must read it.

```python
class ItemProvenance(BaseModel):
    """Where a catalog item's mechanics came from. ADR-145."""
    model_config = {"extra": "forbid"}
    mode: Literal["verbatim", "derived", "bespoke"]
    srd: str | None = None          # "wwn" | "cwn" | "swn" | "awn"; None iff bespoke
    srd_ref: str | None = None      # SRD section/table, e.g. "WWN §3.0.0 Armor"
    license: Literal["wn-free", "ccby", "none", "na"] = "na"
                                    # "wn-free" = Without Number SRD free-use terms
                                    #             (all four WN SRDs); "ccby" = Fate Core
    extracted_by: str | None = None # extraction-tool version stamp (114-3); None for hand-authored bespoke

class CatalogItem(BaseModel):
    model_config = {"extra": "forbid"}
    # ... all existing fields unchanged ...
    provenance: ItemProvenance | None = None   # NEW — None tolerated only on
                                                # legacy/bespoke during migration;
                                                # required on SRD-sourced items
    tech_level: int | None = None               # NEW — SWN/AWN/CWN TL tag
    range_band: str | None = None               # NEW — ranged: "thrown" | "pistol"
                                                #       | "rifle" | etc. (SRD bands)
    magazine: int | None = None                 # NEW — ranged: shots per reload
```

Rationale for each:
- **`provenance` as a nested strict model**, not flat fields, so the licensing
  invariant (`mode == "verbatim"` ⇒ `license` permits verbatim reuse — `wn-free`
  for the WN line, `ccby` for Fate text) is validated in one place and rides
  cleanly on the wire to the GM panel.
- **`tech_level` / `range_band` / `magazine`** close the audit's "no TL tags, no
  ranged schema" gap and are exactly the WN-family extras the shared item schema
  needs. They are `None`-defaulted so existing melee/armor items are unaffected.
- **No change to `DamageSpec`** — it already carries `shock`, `trauma_die`,
  `trauma_rating`, `armor_piercing`. The resolution side of WN gear is present.

**Provenance is required on baseline items, optional during migration.** The
validator (114-3) enforces: an item whose `id` lives in a genre-tier baseline
catalog MUST carry `provenance`; a world-tier item MAY omit it (treated as
`bespoke`). This lets the 11 packs migrate world-by-world without a flag-day.

This merges per ADR-121 semantics (per-field strategy + provenance trail). The
inventory models do not subclass `LayeredMerge` today; D3 specifies the minimal
merge they need rather than adopting the full machinery (YAGNI — see Alternatives).

### D3 — Placement + the genre↔world merge (ADR-140 + epic 113)

ADR-140 is unambiguous: **genre = rulebook, world = catalog**. The SRD equipment
chapter is, strictly, neither pure rulebook nor world-distinct flavor — it is the
*shared baseline catalog the rulebook implies*. ADR-140 D2 already names this case:
**"a shared genre-tier catalog where worlds genuinely share one is a first-class
default, not a hole"** (elemental_harmony's shared spell catalog). The SRD baseline
is exactly that: **a genre-tier shared catalog, authoritative when present, that
worlds extend rather than replace.**

- **Genre tier** holds the SRD baseline catalog (the ~90 WWN items, the SWN/AWN
  sets, etc.) — `verbatim` for the WN line, provenance-stamped. This is the
  shared core all worlds of that genre inherit. It collapses the audit's
  duplication (3 identical space_opera files become one baseline) and fixes
  evropi's missing stats by construction.
- **World tier** holds only setting-distinct gear — `bespoke` items the world
  owns (barsoom's radium rifle, mccoy's inventions) and any world **reskin** of a
  baseline item (presentation override; see the per-field merge below). A world
  does **not** re-stat a baseline item: the mechanical envelope is locked (D1).

**The merge must change.** Today world inventory *replaces* genre inventory
wholesale (`inventory_resolve.py`); under this ADR a world that ships bespoke gear
would silently drop the entire SRD baseline — the `power_glove` regression, by
construction. The decision: **the genre SRD baseline is non-droppable; world
inventory merges over it by item `id`** (world `id` wins per-field; baseline `id`s
the world does not mention survive). This is the per-field merge ADR-121 governs,
applied at the catalog level:

- `item_catalog` merges **by `id`**, and a same-`id` world entry merges
  **per-field** against the baseline entry (it does not wholesale-replace it):
  - **Mechanical fields** (`damage`, `armor_class`, `mitigation`, `tech_level`,
    `range_band`, `magazine`, `weight`, `value`, `resource_ticks`, `heal_amount`)
    **inherit and lock from the genre baseline.** A world override of a *verbatim*
    baseline item MUST NOT change these — the extractor/validator (114-3) rejects a
    world override that alters a locked mechanical field on a `verbatim` item (No
    Silent Fallbacks; the ADR-143 forbidden re-tune). The mechanics stay SRD-true.
  - **Presentation fields** (`name`, `description`, world/visual flavor, and
    `narrative_weight`/`lore`) **take the world override when present**, else
    inherit. This is the reskin layer of D1.
  - **Provenance is preserved, not replaced.** A reskinned item keeps the baseline
    item's `provenance` (`mode: verbatim`, `srd`, `srd_ref`) — it *is* the SRD item
    mechanically. The resolver stamps `tier: world` on the contribution so the GM
    panel sees the reskin came from the world, while provenance still proves the
    mechanics are the bound SRD's. A reskin is **never** recorded as a new bespoke
    item.
  - A genuinely new world item with an `id` absent from the baseline is a
    `bespoke` world-tier item (union; `provenance.mode: bespoke`).
- `starting_equipment` / `starting_gold` / `currency` keep **world-replaces-genre**
  (these are world-kit choices, genuinely world-owned, ADR-140-correct).

This change is the seam where epic 113 (genre→world boundary hygiene) and epic 114
meet: 113 moves the *six misplaced genre-tier catalogs* down to the world tier;
114 moves the *SRD baseline* up to a genre-tier shared default. The two are not in
conflict — 113 is "stop putting world-distinct gear in the genre tier," 114 is
"the SRD baseline *belongs* in the genre tier as a shared default." Coordinate
sequencing so a pack is not mid-flight in both at once.

### D4 — Licensing policy (enforced by the extraction tool, 114-3)

This table is policy, not advice. The licensing basis for the WN line is **settled
and uniform**: the Without Number SRD documents state Sine Nomine's standing public
policy that the SRDs are *free for anyone to use for any purpose.* This covers all
four WN SRDs — there is no longer a CC0-vs-unverified-vs-free-edition split. The
extraction tool (114-3) MUST encode this table and **refuse to emit a `verbatim`
item for any ruleset whose license does not permit verbatim reuse.**

| Ruleset | License basis | Policy | `provenance.mode` allowed | `provenance.license` |
|---|---|---|---|---|
| **WWN** | WN SRD free-use | **Reproduce verbatim.** Extract the ~90-item table as-is. | `verbatim`, `bespoke` (world-tier) | `wn-free` |
| **CWN** | WN SRD free-use | **Reproduce verbatim.** ~150 base items incl. cyberware/vehicles. | `verbatim`, `bespoke` (world-tier) | `wn-free` |
| **SWN** | WN SRD free-use | **Reproduce verbatim.** ~200+ items + starship schema. | `verbatim`, `bespoke` (world-tier) | `wn-free` |
| **AWN** | WN SRD free-use | **Reproduce verbatim.** ~200 statted + d100 goods. | `verbatim`, `bespoke` (world-tier) | `wn-free` |
| **Fate Core** | OGL + CC-BY (own basis) | **No catalog to extract** — gear is aspects/permissions/stunts (D5, ADR-144). | n/a | `ccby` / `na` |

The `derived` mode is **not used by any current ruleset** — every WN SRD is
verbatim-eligible and Fate has no catalog. `derived` remains a valid value in the
schema for a hypothetical future ruleset whose license permits derivation but not
verbatim copy; the validator below honors it generically rather than wiring it to
any WN SRD.

**Validator invariants (114-3, fail-loud per No Silent Fallbacks):**
- `mode == "verbatim"` ⇒ `srd` is set AND that ruleset's row permits verbatim
  (all four WN SRDs do; Fate does not — it has no catalog). Otherwise refuse to emit.
- `mode == "derived"` ⇒ `srd` is set; `srd_ref` SHOULD be set. (No WN ruleset
  triggers this today.)
- `mode == "bespoke"` ⇒ `srd is None`, `license == "na"`, and the item is
  world-tier (a bespoke item in a genre baseline is a hard error).
- No silent downgrade and no silent upgrade: the tool emits exactly the mode the
  ruleset's policy permits, and errors (naming the ruleset) on any mismatch.
- `srd_ref` MUST point into an **SRD document** (see D4b); a ref naming a
  commercial book is a hard error.

### D4a — Hard constraint: no implied Sine Nomine / Kevin Crawford endorsement

> **This is a standalone, load-bearing constraint. It binds every downstream story
> (114-3 through 114-10), every pack/world README, every provenance string, and any
> marketing or public-facing copy. Do not soften it.**

The Without Number SRDs are usable here under their **published free-use terms** —
a license grant on the *documents*, nothing more. The publisher (Sine Nomine /
Kevin Crawford) has **explicitly declined association with AI use in gaming and
asked to stay clear of it.** SideQuest is an AI-GM project. Therefore:

- **Provenance and citation are factual sourcing ONLY.** A `provenance` record, a
  README line, or a UI tooltip may state that an item is *sourced from the WWN/CWN/
  SWN/AWN SRD under its free-use terms.* That is the entire permissible claim.
- **MUST NOT, anywhere, in any form:** imply endorsement, approval, blessing,
  partnership, collaboration, review, or any Sine Nomine / Kevin Crawford
  involvement in this project. No "approved by," "in partnership with," "blessed by,"
  "with thanks to Kevin Crawford," "official," or equivalent. The author is named
  only as the factual source of the SRD text, never as a participant in SideQuest.
- **The written correspondence on file (2026-06-14) is internal provenance
  corroboration, not a public credential.** It confirms the free-use basis for our
  records; it is not a grant of endorsement and MUST NOT be cited as one.
- **Extraction-tool guardrail (114-3):** the tool MUST NOT emit any
  endorsement-flavored attribution string. Permitted attribution is the neutral
  factual form above; the tool should template that form and have no code path that
  produces a collaborator/approval phrasing. Reviewer (and any pack-README author)
  treats an endorsement-implying string as a hard defect.

This constraint costs nothing mechanically and protects both the project and the
publisher's stated wishes. It is non-negotiable.

### D4b — Source is the bare SRD only, never the full commercial books

> **Load-bearing sourcing boundary. Enforced by tooling; obvious to every author.**

The only Sine Nomine material that enters this project is the **publicly-released
SRD document** for each game (WWN / CWN / SWN / AWN) — that document is what carries
the "free for any purpose" terms. The **full paid rulebooks are NOT a source.**
Their content MUST NEVER be extracted, paraphrased, or reproduced into a catalog,
a provenance string, lore, or any pack/world file.

- The 114-3 extraction tool reads the **SRD equipment chapter exclusively.** It has
  no code path that ingests a commercial rulebook.
- Every catalog item's `provenance.srd_ref` MUST point into an SRD document (e.g.
  "WWN SRD §3.0.0 Armor"), never into a commercial book. The validator rejects a
  `srd_ref` that does not resolve to a known SRD section.
- This boundary is independent of the free-use grant: even though the SRD text is
  free to use, the paid books are not in scope and never become a source — there is
  no "fill the gap from the full book" path. If the SRD lacks an item, the answer is
  a world-tier `bespoke` item, not a reach into the commercial book.

### D5 — Fate gear is deferred to ADR-144 / story 114-9 (seam only)

Fate Core has no equipment economy: gear is aspects, stunts, and permissions, with
no cost, weight, or damage table (audit §"What the SRDs offer"). The four Fate
packs currently ship the strict WN-shaped `CatalogItem` (priced/weighted/
power-tiered) plus `starting_gold` — a *ruleset mismatch*, not merely an inventory
gap. **This ADR does not design the Fate gear model.** That is ADR-144's domain
(the `FateRulesetModule` / aspect-economy work) and lands in stories 114-9/114-10.

The seam this ADR must leave clean: the Fate gear model will need `CatalogItem` to
carry **non-priced, mechanic-as-aspect** records (`aspect:` / `stunt:` /
`permission:` fields), which the current `extra="forbid"` model forbids. This ADR
**does not add those fields** (they belong with the Fate design so they are
shaped by it, not guessed here). It only records that (a) the provenance taxonomy
in D2 already accommodates Fate (`mode: bespoke`, `license: ccby`/`na`), and (b)
the merge in D3 is paradigm-neutral, so when 114-9 adds aspect-gear fields the
genre/world placement and merge already hold. **Until 114-9, the Fate packs keep
their current bespoke `CatalogItem` records, now provenance-stamped `bespoke`** so
the audit can see they are unmigrated.

## Migration approach (the 11 packs, world-by-world)

Sequencing follows the audit's recommendation and the binding-order of ADR-143/144.
"Done" for a pack = its baseline catalog is `verbatim` SRD-sourced at the genre tier
with provenance, worlds carry only `bespoke` items plus any presentation reskins of
baseline items (mechanics inherited+locked per D3), and no two worlds ship duplicate
catalogs.

1. **114-3 — Extraction tool + schema delta.** Build the SRD→`inventory.yaml`
   extractor encoding D4's licensing policy and emitting D2's provenance. Land the
   `CatalogItem` schema delta (provenance + TL/range/magazine) and the D3 by-`id`
   merge in `inventory_resolve.py`. WWN first. This is the foundation; nothing
   else proceeds without it.
2. **114-4 — WWN packs** (caverns_and_claudes, elemental_harmony, heavy_metal +
   barsoom). The clean win: extract the ~90-item WWN table verbatim into a genre
   baseline the three WWN genres inherit; worlds keep only bespoke gear. Fixes
   sourcing + duplication + evropi's missing stats in one move.
3. **114-5 — CWN packs** (neon_dystopia, road_warrior personal gear). Reproduce
   verbatim from the CWN SRD (WN SRD free-use, D4). Wire CWN's System Strain as a
   `system_strain` field, not a tag.
4. **114-6 — road_warrior vehicles.** Bind CWN's vehicle chapter (speed/armor/AC/
   HP/crew/hardpoints) instead of the dormant bespoke Rig Composure — the ADR-143
   trap in the wild. Coordinates with ADR-125 (chassis/rig).
5. **114-7 — space_opera / SWN.** Reproduce verbatim from the SWN SRD. Collapse the
   3 byte-identical files into one genre baseline; give each world its own reskins /
   bespoke gear and TL tags.
6. **114-8 — mutant_wasteland / AWN.** Reproduce verbatim from the AWN SRD. Fix the
   `power_glove` broken-ref regression via the D3 non-droppable baseline; add
   scrap-armor mitigation.
7. **114-9 / 114-10 — Fate quartet.** Gated on ADR-144 (currently deferred).
   Replace the WN-shaped priced catalog with the Fate aspect/permission gear model;
   declare `ruleset: fate`. Per D5, until this lands the four packs carry
   provenance-stamped `bespoke` records as a holding state.

Standalone content defects (evropi missing stats, seaboard `power_glove`,
caverns duplicate `armor_class` key) are already fixed under 114-2 (merged) and do
not block this design.

## Invariants / Contracts

- **Gear is bound, not balanced.** A bound ruleset's equipment chapter is the
  authority for that pack's baseline gear. Hand-tuning a baseline item's combat
  stats to "look right" is the forbidden move (the ADR-143 trap, one layer down).
- **Verbatim binds mechanics; flavor is free.** The SRD mechanical envelope is
  locked verbatim; `name`/`description`/world-flavor are freely reskinnable per
  genre/world (D1). A reskin keeps `mode: verbatim` + `srd_ref` — it is the SRD item
  mechanically, not a bespoke item.
- **Every baseline item carries provenance.** `mode` + `srd` + `license` + `srd_ref`
  are data, not comments. The GM panel / licensing audit can prove an item is the
  verbatim SRD mechanics, derived, or bespoke. *Provenance you cannot read is
  provenance you cannot trust* (cf. ADR-139).
- **Reproduce-vs-derive is set by license, enforced by tooling.** All four WN SRDs
  are verbatim under their free-use terms (D4); `derived` is reserved for a future
  derive-only ruleset. The extractor refuses any mode a ruleset's license does not
  permit — no silent downgrade, no silent upgrade — and `srd_ref` must point into an
  SRD document, never a commercial book (D4b).
- **No implied publisher endorsement (D4a).** Provenance is factual sourcing only;
  no copy anywhere implies Sine Nomine / Kevin Crawford endorsement, partnership, or
  involvement.
- **Genre baseline is a non-droppable shared default; world overrides per-field by
  `id`.** ADR-140 placement holds: SRD baseline at genre (a permitted shared default,
  ADR-140 D2), bespoke + reskins at world. World inventory merges over the baseline
  per-field (mechanics inherit+lock, presentation overrides), it does not replace it.
- **Fate is a separate track.** No Fate gear model is decided here; the seam is
  left clean for ADR-144 / 114-9.

## Resolved during design (no longer open)

- **WN SRD licensing.** Settled: all four WN SRDs (WWN, CWN, SWN, AWN) are
  reproducible **verbatim** under Sine Nomine's standing public free-use policy
  stated in the SRD documents (written confirmation on file, 2026-06-14, as
  corroborating provenance). The earlier "CWN unverified / SWN-AWN derive-only"
  split is void (D4). The endorsement and SRD-only-sourcing guardrails (D4a/D4b)
  are the standing constraints that replace it.
- **Verbatim names — house-style vs. as-printed.** Settled by the
  verbatim-mechanics / free-reskin doctrine (D1): the SRD *mechanical envelope* is
  bound verbatim; the world owns `name`/`description` as a flavor **reskin** of the
  baseline item (keeps `mode: verbatim` + `srd_ref`). A reskin is **not** a bespoke
  override. The D1/D3 reskin sections are the single source of truth.

## Open Questions (Keith must rule / verify)

1. **Migration order vs. ADR-143 WWN combat rollout.** 114-4 (WWN gear) and
   ADR-143's WWN combat cleanup touch the same packs. Confirm they sequence so a
   pack is not mid-flight in both. Recommendation: gear baseline (114-4) lands
   after the 143 combat cutover per pack, since gear feeds combat resolution.
2. **Does the genre-tier baseline need its own file name?** Today a genre ships
   `inventory.yaml`; worlds ship `inventory.yaml`. The by-`id` merge (D3) works with
   the existing two-file layout, so **no new file is proposed** — but confirm we are
   comfortable that a genre `inventory.yaml` is now semantically "the SRD baseline"
   rather than "the whole catalog." (No schema impact either way.)

## Alternatives considered

- **Keep hand-authoring; just add a `source` comment convention.** Rejected. This
  is the status quo the audit condemns — provenance-as-comment is unreadable by
  tooling, and it does nothing to stop the silent re-balancing. The whole point is
  to *inherit* the SRD's balanced gear, not annotate our own.
- **Put the SRD baseline at the world tier (strict ADR-140 "world owns catalog").**
  Rejected. It would re-create the audit's duplication (every world re-ships the
  same ~90 WWN items) and makes a homebrew author copy the baseline to start. ADR-140
  D2 explicitly blesses a shared genre-tier catalog as a first-class default; the SRD
  baseline is the canonical example of one.
- **Adopt the full `LayeredMerge`/`MergeStrategy` machinery (ADR-121) for inventory
  now.** Rejected for this epic (YAGNI). The catalog needs one small, fixed merge —
  union-by-`id` with a two-bucket per-field rule (mechanics inherit+lock,
  presentation overrides; D3) — plus the existing replace semantics for kits/gold. A
  single targeted merge in `inventory_resolve.py` is simpler than subclassing
  `LayeredMerge` and authoring per-field strategies for a model with one merge
  concern. The ADR-121 *provenance wire types* are reused; the merge *engine* is not.
- **Treat SWN/AWN as no-license and derive-only (the original audit posture).**
  Rejected — superseded by the settled facts. The audit read the *free editions* as
  copyright-only, but Sine Nomine's standing public policy in the SRD documents makes
  all four WN SRDs free for any purpose; SWN and AWN are reproduced **verbatim** from
  their SRDs like WWN and CWN (D4). The boundary that *does* bind is D4b: source the
  bare SRD, never the commercial book.
- **Design the Fate gear model here.** Rejected. Fate gear is an aspect/permission
  economy that must be shaped by the ADR-144 Fate engine work, not guessed against a
  d20-shaped `CatalogItem`. Deferred to 114-9; only the seam is kept clean.

## Amendments

_None yet._
