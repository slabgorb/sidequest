# Beneath Sünden — Content Cookbook

- **Date:** 2026-05-16
- **Status:** Approved (design) — pending spec review, then implementation plan
- **Pack:** `caverns_and_claudes`
- **World:** `beneath_sunden` (the world artifact itself is authored under the oq-1 plan; this spec defines the *content tables* it draws from)
- **Owning workspace:** oq-2
- **Feeds, does not redefine:** `docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md` (the "Sünden Deep" megadungeon spec). This document is the **content + table-semantics half of that spec's §10 item 4** ("Theme palette + set-piece schema — authored content scaffold + loader"), scoped strictly to content. It does **not** define the theme/region schema, the loader, `depth_score`, burst magnitude, the CR→Edge translation, or any engine code — those are oq-1-owned.

## 1. Problem & Intent

The Sünden Deep megadungeon spec rejects discrete floors and named regions: the dungeon is an unbounded, edge-expanding, procedurally Jaquaysed deathtrap played straight (Tomb of Horrors / Moria-as-tragedy, gravity ≥ 0.85, zero genre winking). Its theme palette (§6 of that spec) is described only in prose; the engine seam today is a bare `region.theme: str` chosen by `rng.choice(theme_pool)`. There is no content for the generator to place.

This spec defines that content as a **cookbook**: a small set of authored roll-tables and filter predicates over an ingested reference corpus, decomposed along five orthogonal axes. The cookbook does not author monster stat blocks — it *curates and filters* a canonical corpus. Its authored craft is the curation, the affinities, the telegraph flavor, and the genre-truth gate.

## 2. Scope Boundary (oq-2 vs oq-1)

This is collision-critical. oq-1 is concurrently building the engine/schema/loader.

**oq-2 owns (this spec):**
- Corpus ingest artifacts (`corpus/monsters.yaml`, `corpus/items.yaml`)
- The authored cookbook files (`cookbook/races/*`, `cookbook/looks.yaml`, `cookbook/affinities.yaml`, `cookbook/special_rooms.yaml`, `world_register.yaml`)
- Genre-truth curation
- Region-assembly **semantics** (the deterministic content-manifest contract, described as a pure function of named inputs)
- OTEL span **definitions** (names + fields)
- Tests for all of the above

**oq-1 owns — referenced here, never defined here:**
- `LOOK → interior-generator` binding (the `region_graph`/`themes` loader, `theme: str`, `theme_pool`)
- `depth_score` production and bucketing
- Burst magnitude (spec §5.1 `connection_burst` / §7.1 threads-lit)
- CR/XP → Edge translation at the materializer seam (ADR-078 removed HP; ADR-014 mandates HP/CR→Edge translation at materialization)
- OTEL span **emission** at runtime
- The materializer that *invokes* the region-assembly contract

Any place the cookbook needs an oq-1-owned value, it names it as a contract input and stops. This spec must never be implemented in a way that defines those.

## 3. The Five Axes

A region's content identity is a tuple roll across five orthogonal sub-generators, replacing the spec's single opaque `theme` string:

| Axis | Meaning | Binds to | oq-1 seam |
|------|---------|----------|-----------|
| **LOOK** | Interior texture + narrator register | corpus: none; engine: generator binding | references LOOK→generator |
| **RACE** | Denizen faction | corpus `type` + `tags` (+ `name~glob`) | none — pure content |
| **BIG BAD** | Depth-gated regional capstone | high-CR slice of the RACE filter | consumes `depth_score` |
| **SPECIAL** | Special-room sub-generator | authored table; feeds set-piece slot | feeds oq-1 set-piece slot |
| **SIZE** | Content-density / magnitude | roll-count budget | consumes burst magnitude |

Locked cross-cutting decisions:

- **LOOK × RACE are orthogonal, affinity-weighted.** They roll independently; a per-LOOK affinity table *biases* (never locks) the RACE roll. A Sunken-Necropolis Kuo-Toa pocket is possible but rarer than Sunken-Necropolis Undead.
- **BIG BAD = depth-gated regional capstone.** No single final boss (the dungeon is unbounded). When `depth_score` crosses a band threshold, an occasional region is promoted to a capstone: the local apex ruler, RACE-linked, escalating with depth.
- **SIZE = player-paced, burst-driven.** SIZE scales with oq-1's §7.1 burst magnitude (push frontier harder → larger region pops in), not with depth or faction. A BIG BAD forces SIZE to `large+` (a capstone is a lair complex, not one room).
- **Tone: played straight, Moria-grave.** Gravity ≥ 0.85, no fourth-wall winking. The Dwarf RACE in particular is a delved-too-deep dwarfhold rendered as tragedy (Moria), never the campy "diggy-diggy-hole" reading.

## 4. Corpus Model — Hybrid: Ingest as Index, Author the Curation

The reference corpus (a 5e-SRD-shaped monster table and magic-item table) is **ingested verbatim** as the structural roll-space. The cookbook authors **zero stat blocks**. The authored layer is filter predicates, affinities, telegraph flavor, and the genre-truth gate.

### 4.1 Ingested artifacts (regenerable, not hand-edited)

`corpus/monsters.yaml` — one row per monster:

```yaml
- name: Skeleton
  size: Medium          # Tiny|Small|Medium|Large|Huge|Gargantuan
  type: Undead          # Beast|Undead|Humanoid|Fiend|Aberration|Construct|
                        # Plant|Elemental|Fey|Monstrosity|Ooze|Giant|Dragon|Celestial
  tags: []              # e.g. [goblinoid], [devil], [lycanthrope], [titan]
  alignment: LE
  cr: 0.25              # numeric; "1/8"→0.125, "1/4"→0.25, "1/2"→0.5
  xp: 50
  source: "mm 282"
```

`corpus/items.yaml` — one row per magic item:

```yaml
- name: Potion of Healing
  item_type: Potion     # Armor|Potion|Ring|Rod|Scroll|Staff|Wand|Weapon|Wondrous Item
  rarity: Common         # Common|Uncommon|Rare|Very Rare|Legendary|Artifact
  attunement: false
  notes: ""
  source: "dmg 288"
```

Ingest is a one-shot transform of the source dumps. CR fractions normalize to floats. Re-running the transform is idempotent and the test suite asserts row-count and CR-monotonic fidelity against the source.

### 4.2 Authored cookbook files

**`cookbook/races/<race>.yaml`** — the faction definitions:

```yaml
id: undead
display: "The Restless"
# Corpus filter predicate — the roll-space for this RACE.
filter:
  any_of:
    - { type: Undead }
    - { type: Construct, tags_any: [] , name_glob: "*animated*" }   # graveyard automata
# Optional per-RACE refinement on top of the world register (§5).
deny:
  name_glob: ["*faerie*"]
# Player-facing telegraph flavor, keyed by CR band id (bands defined in affinities.yaml).
telegraph:
  shallow: "Bone-dust on every sill. Something here does not lie down."
  mid: "The dead are organized. That is worse than wandering."
  deep: "A cold that has a will behind it."
# Loot bias: nudge the rarity/category roll for this faction (multipliers, not overrides).
loot_bias:
  category_weight: { Wondrous Item: 1.3, Weapon: 0.8 }
# BIG BAD capstones for this RACE — names must resolve in corpus/monsters.yaml.
big_bads:
  - { name: "Lich", min_band: deep }
  - { name: "Mummy Lord", min_band: mid }
# Conceptual-race dressing for RACEs with no literal corpus rows
# (e.g. dwarf): narrative framing + which corpus rows actually source it.
concept:
  framing: "A dwarfhold that dug past where digging should stop. No survivors — only what answered."
  sourced_from: undead          # this RACE's creatures are drawn via the 'undead' filter
```

**`cookbook/looks.yaml`** — texture + register, one entry per LOOK:

```yaml
looks:
  - id: necropolis
    generator_binding: depthfirst   # oq-1-owned key; we reference, do not define semantics
    register: "Mausoleum-formal. Straight lines cut by collapse."
    dressing:                       # sensory roll-table (Diamonds-and-Coal texture)
      - "Niche after niche, most emptied, a few not."
      - "Grave-script worn past reading."
      - "Standing water gone to mirror in a cracked sarcophagus."
```

**`cookbook/affinities.yaml`** — the joints between axes:

```yaml
# depth_score → CR band. Bands are ORDINAL (shallow < mid < deep), listed in
# increasing depth. "min_band <= cr_band" comparisons use this order.
# Boundaries are content tuning; depth_score itself is oq-1's.
cr_bands:
  - { id: shallow, depth_lt: 0.25, cr_min: 0,  cr_max: 2 }
  - { id: mid,     depth_lt: 0.60, cr_min: 2,  cr_max: 7 }
  - { id: deep,    depth_lt: 1.01, cr_min: 6,  cr_max: 30 }
# BIG BAD capstone gate. A region becomes a capstone when depth_score crosses
# into a band for the first time on a given frontier heading (the "first
# entry" into mid/deep is a capstone), plus a per-band recurring chance for
# deeper repeat regions. depth_score crossing is oq-1's signal; the gate
# policy and probabilities are content tuning.
big_bad_gate:
  on_first_band_entry: [mid, deep]   # first region to reach each = capstone
  recurring_chance: { mid: 0.10, deep: 0.20 }
# LOOK → RACE affinity weights (bias, not lock; any RACE can still roll).
look_race_affinity:
  necropolis: { undead: 6, aberration: 2, kuo_toa: 1, goblinoid: 1 }
  sunken:     { kuo_toa: 5, undead: 2, aberration: 3 }
# Rarity band gate by CR band (loot deepens with depth).
rarity_by_band:
  shallow: { Common: 6, Uncommon: 2 }
  mid:     { Uncommon: 5, Rare: 3, Common: 1 }
  deep:    { Rare: 4, Very Rare: 3, Legendary: 1, Artifact: 0.2 }
# SIZE: burst magnitude → roll-count budget. Burst magnitude is an oq-1 input.
size_by_burst:
  - { burst_lte: 1, wandering_rolls: 1, special_rooms: 0, loot_rolls: 1 }
  - { burst_lte: 3, wandering_rolls: 3, special_rooms: 1, loot_rolls: 2 }
  - { burst_lte: 9, wandering_rolls: 6, special_rooms: 2, loot_rolls: 4 }
big_bad_forces_size: large   # capstone region floors SIZE at this tier
```

**`cookbook/special_rooms.yaml`** — the SPECIAL sub-generator:

```yaml
special_rooms:
  - id: teleporter_room
    telegraph: "A ring of scored glyphs, swept clean while everything else rots."
    mechanic: "Step onto the ring → forced relocation to a frontier region."
    outcome: "Hard, legible: you are moved; you do not choose where."
    min_band: mid
    feeds_setpiece_slot: true     # oq-1's set-piece schema consumes this; we only describe it
```

**`world_register.yaml`** — the genre-truth gate (see §5).

### 4.3 Region-assembly contract (semantics only)

A pure deterministic function oq-1's materializer calls:

```
assemble_region(campaign_seed, expansion_id, depth_score, burst_magnitude, look)
  → RegionContentManifest
```

`RegionContentManifest` =
- `race` — affinity-weighted roll, post-curation
- `cr_band` — from `depth_score` via `affinities.cr_bands`
- `size_budget` — from `burst_magnitude` via `affinities.size_by_burst`
- `wandering_table` — `corpus.monsters ∩ race.filter ∩ cr_band`, weighted, with `count` dice and per-row telegraph
- `loot_table` — `corpus.items ∩ rarity_by_band[cr_band]`, with `race.loot_bias` applied
- `special_rooms` — up to `size_budget.special_rooms`, gated by `min_band`
- `big_bad` — present iff `affinities.big_bad_gate` fires for this region (first entry into a gated band, or the band's `recurring_chance`); pulled from `race.big_bads` whose `min_band ≤ cr_band` (ordinal, per §4.2). The "first band entry" signal is derived from oq-1's `depth_score` crossing; the cookbook supplies only the gate policy

Determinism: all randomness derives from `(campaign_seed, expansion_id)` per Sünden Deep §11. This contract is *specified* here and *invoked* by oq-1; CR→Edge translation of the manifest happens at oq-1's materializer seam and is out of scope.

## 5. Genre-Truth Curation — the Authored Quality Gate

`world_register.yaml` is applied **before any RACE roll** and is the cookbook's primary craft:

```yaml
register: "Grave, lethal, Moria-as-tragedy. Gravity >= 0.85. No winking."
allow_types: [Undead, Aberration, Ooze, Monstrosity, Construct, Giant, Humanoid, Beast]
deny:
  types: [Celestial, Fey]                       # whimsy/planar register-breakers
  tags:  [titan, metallic, angel, genie]
  name_glob: ["*modron*", "*faerie dragon*", "*pixie*", "*mephit*", "*sprite*",
             "*flumph*", "*unicorn*", "*pegasus*"]
humanoid_constraint: "Humanoid only as grave cultists/bandits/the delved-too-deep — never townsfolk-tone."
reskin:                                          # optional: admissible-but-generic → Sünden-specific
  "Gray Ooze": "The Seep"
marquee: ["Lich", "Mummy Lord", "Vampire"]       # Diamonds-and-Coal: hand-promoted, never denied
```

Curation runs as a hard filter. A row denied by the register is removed from every RACE roll-space. `marquee` rows are exempt from denial and flagged for promotion. This file, not stat blocks, is where Beneath Sünden's tone is enforced.

## 6. Reuse (not reinvention)

The cookbook re-keys proven, shipped patterns rather than inventing parallel systems:

- **Wandering-table shape** re-keys `genre_packs/caverns_and_claudes/worlds/caverns_sunden/encounter_tables.yaml` (weighted spawn pool, `count` dice, per-entry loot/telegraph) — stripped of its sins/keeper-awareness scaffolding and re-keyed from `regions→levels` to `race × cr_band`.
- **Loot roll-on-list** follows the wiring-tested `equipment_tables.yaml` pattern (slot → candidate ids; ids must resolve).
- **Creature data model** aligns with the existing Monster Manual subsystem (`sidequest/game/creature_core.py`, `monster_manual.py`, `power_tiers.yaml`) so the manifest is consumable by the pre-existing injection path rather than a new one.
- **Conceptual-race dressing** reuses the `concept.framing` idea rather than fabricating absent SRD rows (the SRD has no "dwarf" monster; the Dwarf RACE sources guardians via the `undead`/`construct` filter and supplies framing prose).

## 7. Failure Modes — No Silent Fallbacks

Per CLAUDE.md. All are **loud build-time/ingest-time failures**, never silent substitution:

- A RACE whose `filter` resolves to **zero corpus rows** at a CR band it declares (via `big_bads.min_band` or affinity presence) → ingest/validation error naming the RACE and band.
- A `world_register.deny` rule that empties a band for a RACE that LOOK affinities can still select → error (would otherwise yield an empty wandering table at runtime).
- A `big_bads[].name` or `reskin` key not resolving in `corpus/monsters.yaml` → error.
- A `looks[].generator_binding` not in oq-1's known set → error at the seam (we validate the reference exists; oq-1 owns its meaning).

## 8. OTEL (definitions; oq-1 emits)

The GM panel is the lie detector. The cookbook *specifies* these spans; oq-1 emits them at materialization:

- `cookbook.race.rolled` — `{look, race, affinity_weight, rng_seed}`
- `cookbook.cr_band` — `{depth_score, band, cr_min, cr_max}`
- `cookbook.size_budget` — `{burst_magnitude, wandering_rolls, special_rooms, loot_rolls}`
- `cookbook.bigbad.gated` — `{depth_score, threshold_crossed, big_bad|null}`
- `cookbook.curation.denied` — `{race, denied_count, sample_names}`

## 9. Testing Strategy

- **Ingest fidelity:** row counts match source; CR parses (fractions→floats); CR list monotonic per source ordering.
- **Filter resolution:** every RACE filter resolves to ≥1 admissible row in every CR band it claims (post-curation). Loud-fail otherwise (ties to §7).
- **Curation:** no `deny`d type/tag/name appears in any assembled manifest across a seed sweep; every `marquee` survives curation.
- **Affinity:** over a large seed sweep, LOOK→RACE roll frequencies track the configured weights within tolerance; off-affinity RACEs still appear (orthogonality preserved, not locked).
- **Determinism:** identical `(campaign_seed, expansion_id, depth_score, burst, look)` → identical manifest.
- **SIZE/BIG BAD:** burst→budget monotonic; a capstone region floors SIZE at `big_bad_forces_size`.
- **Wiring:** an integration test proving oq-1's materializer path actually invokes `assemble_region` (not only unit-tested in isolation) — coordinated with oq-1, asserted from the real frontier-crossing call.

## 10. Scope Boundary & Decomposition Seed

**In scope (oq-2):** corpus ingest, the five cookbook files, `world_register.yaml`, region-assembly semantics, OTEL definitions, all tests.

**Out / oq-1-owned (referenced only):** LOOK→generator binding, `depth_score`, burst magnitude, CR→Edge materializer translation, OTEL emission, the region_graph/themes loader, set-piece slot schema.

Likely implementation sub-plans (sequenced):

1. **Corpus ingest** — source dumps → `corpus/monsters.yaml` + `corpus/items.yaml`; fidelity tests.
2. **`world_register.yaml` + curation filter** — the genre-truth gate + denial/marquee tests.
3. **RACE definitions** — `cookbook/races/*` filter predicates + conceptual-race dressing; filter-resolution tests.
4. **LOOK + affinities** — `looks.yaml`, `affinities.yaml`; affinity-distribution + band tests.
5. **SPECIAL rooms** — `special_rooms.yaml`; gating tests.
6. **Region-assembly contract** — the deterministic function + OTEL span definitions; determinism + wiring test (coordinated with oq-1).

## 11. Open Items

- CR-band boundaries (§4.2 `cr_bands`) and rarity-by-band weights are first-pass tuning values; expect playtest revision.
- Burst→SIZE budget magnitudes pending the same `connection_burst`/threads-lit tuning oq-1 is calibrating (Sünden Deep §12) — coordinate values, do not fork them.
- Reskin map breadth (§5 `reskin`) is intentionally minimal v1; expand only where a playtest says an admissible row reads as generic (Diamonds-and-Coal, deferred).
