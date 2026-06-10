# Seaboard of Saints — Build Plan & Epic Breakdown (epic 103)

**Date:** 2026-06-10
**Author:** Architect
**Status:** build plan — ready to materialize as epic 103
**Builds on:**
- `2026-05-14-mutant-wasteland-seaboard-of-saints-design.md` (world design — flavor authority)
- `2026-06-09-seaboard-of-saints-awn-rebase-addendum.md` (mechanics rebase — **AWN wins always**)
- `completed/2026-06-05-ashes-without-number-mutant-wasteland-design.md` (AWN master spec)
- `2026-06-09-awn-plan2-mutations-design.md` (mutation catalog, shipped)

**Scope decisions (Keith, 2026-06-10):** all 17 regions in v1 · non-human stocks (Animal/Plant/Synthetic) in v1 · full epic breakdown.

---

## 1. Ground truth (verified 2026-06-10, oq-4 @ origin)

The addendum's dependency chain is **satisfied**. This epic is unblocked:

| Prerequisite | State | Evidence |
|---|---|---|
| AWN Plan 1 — `awn` RulesetModule bound to `mutant_wasteland` | **DONE** (102-7 merged) | `sidequest/game/ruleset/awn.py` (subclass of `CwnRulesetModule`), `registry.py:16`, pack `rules.yaml: ruleset: awn` |
| AWN Plan 2 — mutation catalog + MP economy | **DONE** | `genre_packs/mutant_wasteland/mutations.yaml` (6×10 positives, 40-negative d100 table), `sidequest/mutation/` (models, catalog loader, `MpEconomy`: base 2 MP, +2/negative, max 3) |
| Ablative HP + System Strain (Edge dead) | **DONE** | `creature_core.py::HpPool`, `system_strain.py`, rules.yaml strain config |
| Mutation ID namespace for `saints.yaml` to reference | **DONE** | `category/snake_case` — e.g. `structure/augmented_muscle`, `negative/animalistic_mentality` |
| `seaboard_of_saints` content | **none** | test fixtures only |

AWN Plans 3–7 (Radiation/Disease, Stress/Addiction, Survival hexcrawl, Creatures, Enclaves) are **not built and not required** by this epic — see §5 for the two touchpoints.

Current chargen is the live **5-step** flow (`char_creation.yaml`: origins, pronouns, mutation, artifact, confirmation). The original spec's 7-step `native` overhaul is dead (absorbed by AWN per the addendum); Seaboard chargen texture lands as **extensions to the 5-step flow**, not a rebuild.

---

## 2. Architecture decisions

### D-A: `saints.yaml` is world-tier content; Saints are curation, not mechanics

Per ADR-140 / "Crunch in the Genre, Flavor in the World" and Keith's standing directive (genre tier is mechanics only): the Saint canon lives at
`genre_packs/mutant_wasteland/worlds/seaboard_of_saints/saints.yaml` — **world-tier only**. No genre-tier saints file. flickering_reach stays Saint-less (addendum, settled): its mutants are raw AWN MP spend.

A Saint is a **named preset over the existing MP economy**:

```yaml
# worlds/seaboard_of_saints/saints.yaml (schema sketch)
saints:
  - id: herman_of_the_acushnet
    name: "Saint Herman of the Acushnet"
    tradition: literary            # literary | catholic_immigrant | folk_place | wilderness_sleeper
    patron_regions: [whalecoast]   # places.yaml region ids; non-deterministic (migration is canon)
    bundle:                        # AWN positive mutation IDs — MUST exist in genre mutations.yaml
      - structure/<id>
      - sense/<id>
      - hybrid/<id>
    drawback: negative/<id>        # exactly one AWN negative = "the Saint's drawback"
    affinity:                      # optional extra positives purchasable with additional negatives
      - cognition/<id>
    iconography: "..."             # portrait/POI prompt scaffold hook
    veneration: "..."              # flavor: feast, shrine, register
```

**Engine seam:** a `SaintRegistry` loader inside the existing `sidequest/mutation/` subsystem (NOT a new top-level system, NOT the MagicPlugin seam — D5 stands). Loader validates every referenced mutation ID against the genre catalog at world load and **fails loudly** on a miss (No Silent Fallbacks). Saint-Marked chargen = "apply this bundle through `MpEconomy`"; Wild Mutant = the already-live freeform path. Two presets, one engine.

### D-B: Stocks are a chargen branching layer; non-human stocks build from AWN primitives only

Six stocks (Saint-Marked / Wild Mutant / Sleeper / Animal / Plant / Synthetic) become a **stock selection step** in chargen that branches the existing `mutation` step. Mapping:

| Stock | Expression | Net-new engine? |
|---|---|---|
| Saint-Marked | `saints.yaml` bundle via MpEconomy | loader only (D-A) |
| Wild Mutant | existing freeform MP spend | none |
| Sleeper | no mutations; MP budget spent on **pre-war implants authored as System-Strain item sources** (same pool slot as AWN cyberware/stims) | content + thin item hooks |
| Animal-Stock | `stocks.yaml` trait set: attr mods + Move/AC/Trauma-Target hooks + natural abilities **mapped to existing AWN mutation IDs** + optionally one Saint affinity bundle | **yes — the one engine-heavy lane** |
| Plant-Stock | same schema as Animal | shares Animal's engine |
| Synthetic | same schema; "subsystems" are trait-set variants | shares Animal's engine |

`worlds/seaboard_of_saints/stocks.yaml` (world-tier) defines the trait sets; the engine gets one generic **stock application** path (attr mods, Move, AC, Trauma Target, granted mutation IDs) with zero per-stock special cases. If a needed natural ability has no AWN mutation analog, the gap is closed by an **additive genre-tier mutation entry** (mechanics belong at genre tier) — never a world-tier mechanics fork. Per the addendum: extend AWN, never contradict it.

### D-C: Chargen texture = three additive deltas to the 5-step flow

1. **Stock step** inserted before `mutation`; `mutation` step branches per stock (D-B).
2. **"Roll the Bones"** — alt-attribute flag: 3d6-in-order over the **standard six** (D4), reroll budget of two stats. Small chargen-config flag.
3. **Origin step** is world content (parish/manor/village list) riding the existing `origins` step — no new step type.

**Cryptic Alliance** ships v1 as a **faction-tag pick** (content: opening NPC reactions + a starting-equipment slot) — *not* the AWN Plan-7 Enclave sim. When Plan 7 lands, the tag is its retrofit hook. **Penitent** ships as a flavor-focus/archetype over AWN classes (content only); its vow resolves through System Strain or existing penalty hooks — no bespoke economy.

### D-D: OTEL — the lie detector clause

New spans, all emitted from the mutation/chargen subsystems: `awn.saint.applied` (saint id, bundle, drawback, MP math), `awn.stock.applied` (stock id, trait deltas), and Saint-drawback fire-in-confrontation rides the existing mutation-use spans. The GM panel must be able to prove a Saint-Marked PC's drawback is mechanically live, not narrator improv.

---

## 3. Epic 103 — story breakdown

Lanes: **engine** = Architect/Dev through sprint (tdd). **content** = GM lane (Keith directive: world/pack YAML to the gm agent), wiring-verified by the engine stories' tests.

| ID | Story | Lane | Repos | Pts | Depends on |
|----|-------|------|-------|-----|------------|
| 103-1 | **Saint layer**: `saints.yaml` schema + `SaintRegistry` in `sidequest/mutation/` + loud ID validation + Saint-Marked chargen preset over MpEconomy + `awn.saint.applied` span + wiring test. Ships 3 proof Saints (one per pipeline shape: bundle-only, bundle+affinity, drawback-in-confrontation). | engine | server, content | 5 | — |
| 103-2 | **Stock system**: stock chargen step + branching; `stocks.yaml` schema + generic stock application (attr/Move/AC/Trauma/granted-mutations); Sleeper implants as System-Strain items; `awn.stock.applied` span; UI chargen flow for the branch. Ships 1 proof stock per branch class (Sleeper, Animal). | engine | server, ui, content | 8 | 103-1 |
| 103-3 | **Roll the Bones** alt-attribute mode (3d6-in-order, standard six, 2-stat reroll budget) + chargen flag + UI affordance. | engine | server, ui | 2 | — |
| 103-4 | **The Saint canon**: all ~25 Saints from spec §6 curated to AWN mutation IDs in `saints.yaml`, with iconography + veneration flavor; gap-analysis → additive genre-tier mutations where no analog exists. | content (GM) | content | 5 | 103-1 schema freeze |
| 103-5 | **World core**: `world.yaml` (`draft: true` until asset gate), `lore.yaml` (the Glory, the Shake, New Catholicism, Magisterium doctrine incl. Wild-Mutant marking), `history.yaml`. | content (GM) | content | 3 | — |
| 103-6 | **All 17 regions**: places/`cartography.yaml` + `encounter_tables.yaml`; the Corridor as the connective spine; region statuses per spec §3. Cliché bans (§11) enforced. | content (GM) | content | 8 | 103-5 |
| 103-7 | **Cultures + factions**: 15 cultures with ADR-091 corpus bindings; 6 major factions + regional minors; Cryptic-Alliance faction tags (D-C). | content (GM) | content | 5 | 103-5 |
| 103-8 | **Stocks + dramatic content**: full `stocks.yaml` roster (all Animal/Plant/Synthetic variants incl. Penobscot/Wampanoag-named uplift), Penitent flavor-focus, `tropes.yaml`, `openings.yaml`, `archetypes.yaml`, bestiary/creatures, currency flavor (Mint coins, regional scrips). | content (GM) | content | 8 | 103-2 schema freeze, 103-6 |
| 103-9 | **Asset gate**: `visual_style.yaml`, `portrait_manifest.yaml` (Saint icons, faction NPCs), POI landscapes for the 17 regions, audio params. World leaves `draft: true` only when MET. | content (art/music) | content | 5 | 103-6, 103-7 |
| 103-10 | **End-to-end wiring + regression**: integration test per stock — chargen → narrator opening → confrontation where the Saint drawback/stock trait mechanically fires (OTEL-asserted) → save cycle; flickering_reach regression (loads clean, Wild-only, zero Saint content); cliché audit (`cliche-judge`) over shipped content. | engine | server, content | 5 | all |

**~54 points total.** Critical path: 103-1 → 103-2 → 103-8 → 103-10. Content lanes 103-4/5/6/7 parallelize behind the 103-1/103-2 schema freezes; 103-3 is independent.

---

## 4. Definition of done (epic)

- A player completes chargen as **any of the six stocks**; Saint-Marked receives bundle + drawback at creation, priced by the live MpEconomy.
- A confrontation involving a Saint-Marked PC shows the drawback firing **in OTEL**, not just prose.
- flickering_reach regression: loads and plays clean, Saint-less, Wild-Mutant-default.
- Server loads `seaboard_of_saints` with zero validation errors; every `saints.yaml`/`stocks.yaml` mutation reference resolves against the genre catalog.
- All 17 regions present in places/cartography; cliché audit (spec §11 bans) passes.
- Asset gate MET before `draft: true` is lifted.

## 5. Dependencies & risks

- **Plan 7 (Enclaves) not blocking** — Cryptic Alliance ships as faction tags (D-C); flag the retrofit hook in the 103-7 context.
- **Plans 3–6 not blocking** — radiation/stress/survival/creature mechanics are absent Seaboard-wide until those plans land; world content must not narratively promise mechanics that aren't live (the AWN spec's "magic.yaml double-truth" risk, generalized).
- **Mutation-analog gaps** (103-4/103-8): some Saint bundles and animal traits may lack catalog analogs. Resolution is additive genre-tier entries — budget for a small genre PR alongside the world PR; two-PR coordination per repo conventions.
- **Chargen UI churn** (103-2): the stock branch is the first multi-path chargen in the pack; ADR-015/016 (builder state machine, three-mode creation) are the prior art to extend, not replace.
- **Content volume**: all-17-regions + 25 Saints + full stock roster is the largest single world bite to date; the GM lane stories are sized accordingly and 103-9's asset gate will lag — `draft: true` shields selection until MET.

---

*Materialize as epic 103 via `pf sprint epic add` (namespace verified vs origin archive: max is 102).*
