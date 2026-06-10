# Epic 103: Seaboard of Saints — mutant_wasteland world + Saint layer on AWN

## Overview

Build **The Seaboard of Saints** — a second world for the `mutant_wasteland` genre pack: a literary-gonzo post-plague Northeast corridor (Penobscot Bay → the Potomac, fifteen centuries after the Glory plague) — as a **world + Saint-content layer riding AWN's crunch**. The epic delivers two thin engine seams (the Saint curation layer and the stock chargen branching layer), the full world content (all 17 regions, ~25 Saints, 15 cultures, 6+ factions), and end-to-end wiring proof. Governing doctrine (Keith, 2026-06-09): **AWN wins always** — the world contributes zero mechanics that diverge from AWN; where AWN is silent, content extends it from AWN primitives only.

**Priority:** P2
**Repos:** server, ui, content
**Stories:** 10 (54 points)

## Planning Documents

| Document | Relevant Sections |
|----------|-------------------|
| **Build plan** (`docs/superpowers/specs/2026-06-10-seaboard-of-saints-build-plan.md`) | All — §1 ground truth, §2 decisions D-A..D-D, §3 story breakdown, §4 DoD, §5 risks. The authoritative implementation spec for this epic. |
| **World design spec** (`docs/superpowers/specs/2026-05-14-mutant-wasteland-seaboard-of-saints-design.md`) | Flavor authority: §3 geography (17 regions), §4 cosmology, §5 stocks, §6 Saint canon, §7 factions, §8 currency, §11 cliché bans. **Mechanical sections (§5 chargen engine, §9 7-step overhaul) are superseded** — see addendum. |
| **AWN rebase addendum** (`docs/superpowers/specs/2026-06-09-seaboard-of-saints-awn-rebase-addendum.md`) | All — conflict ledger C1–C5, Saints-as-curation re-expression, stock→AWN mapping, build-order placement. Reading this is mandatory before touching any mechanical surface. |
| **AWN master spec** (`docs/superpowers/specs/completed/2026-06-05-ashes-without-number-mutant-wasteland-design.md`) | §5 genre-layer plan ladder (Plans 2–7), §8 epic decomposition, §11 architect addendum (binding styles, seam analysis). |
| **AWN Plan 2 mutations design** (`docs/superpowers/specs/2026-06-09-awn-plan2-mutations-design.md`) | Mutation catalog structure, MP economy, ID namespace that `saints.yaml` references. |
| **ADR-140** (`docs/adr/`) | Genre is the rulebook only; the world owns the cast and catalog — why `saints.yaml`/`stocks.yaml` are world-tier. |
| **ADR-091** (`docs/adr/`) | Culture-corpus + Markov naming — culture authoring in 103-7 binds corpora. |
| **ADR-015 / ADR-016** (`docs/adr/`) | Character builder state machine / three-mode creation — the chargen prior art 103-2 extends. |

## Background

The Seaboard world spec (2026-05-14) was written when `mutant_wasteland` ran the `native` dial engine and proposed its own genre-mechanics overhaul (7-step chargen, homebrew Saint-Bundle mutations, Qud-style defects-for-power, Edge costs). On 2026-06-05 Keith locked the **AWN** (Ashes Without Number) direction: `mutant_wasteland` is bound to a faithful AWN ruleset module, and AWN's D4/D5 decisions superseded the Seaboard spec's mechanical layer. The 2026-06-09 addendum rebased Seaboard accordingly: **the world's central conceit (iconographic mutation — drink a Saint's spring, receive that Saint's marks + drawback) survives completely; only its implementation changes.** A Saint is now a curated bundle of AWN positive-mutation IDs plus one AWN negative as the canonical drawback, priced in AWN MP.

**The epic is unblocked — verified 2026-06-10 against origin:** AWN Plan 1 (the `awn` RulesetModule, subclass of CWN, bound via pack `rules.yaml: ruleset: awn`) shipped in story 102-7; AWN Plan 2 (the mutation catalog — 6×10 positives, 40-negative d100 table, `MpEconomy` at base 2 MP / +2 per negative / max 3 — in `genre_packs/mutant_wasteland/mutations.yaml` + `sidequest/mutation/`) is live. Ablative HP (`HpPool` in `creature_core.py`) and System Strain (`system_strain.py`) are live; Edge is dead. Mutation IDs are namespaced `category/snake_case` (e.g. `structure/augmented_muscle`, `negative/animalistic_mentality`).

**Scope locked with Keith 2026-06-10:** all 17 regions detailed in v1 (not the spec's 7-region recommendation), and non-human stocks (Animal/Plant/Synthetic) included in v1. flickering_reach (the genre's only other world) stays Saint-less — its mutants are raw AWN MP spend — and must regress clean.

AWN Plans 3–7 (Radiation/Disease, Stress/Addiction, Survival hexcrawl, Creatures, Enclaves) are **not built and not blocking**; world content must not narratively promise mechanics those plans haven't shipped.

## Technical Architecture

Four locked decisions (build plan §2):

- **D-A — Saints are world-tier curation, not mechanics.** `worlds/seaboard_of_saints/saints.yaml` defines each Saint as `{id, tradition, patron_regions, bundle: [AWN positive mutation IDs], drawback: one AWN negative ID, optional affinity list, iconography, veneration}`. A `SaintRegistry` loader lives inside the existing `sidequest/mutation/` subsystem (NOT a new top-level system, NOT the MagicPlugin seam — AWN D5 stands). Every referenced mutation ID is validated against the genre catalog at world load; a miss **fails loudly** (No Silent Fallbacks). Saint-Marked chargen = apply the bundle through the live `MpEconomy`; Wild Mutant = the already-live freeform path. Two presets, one engine.
- **D-B — Stocks are a chargen branching layer built from AWN primitives only.** A stock-selection chargen step branches the existing `mutation` step six ways (Saint-Marked / Wild / Sleeper / Animal / Plant / Synthetic). `worlds/seaboard_of_saints/stocks.yaml` defines non-human trait sets as attr mods + Move/AC/Trauma-Target hooks + granted AWN mutation IDs; the engine gets ONE generic stock-application path with zero per-stock special cases. Sleeper implants are authored as System-Strain item sources (same pool slot as AWN cyberware/stims). Catalog gaps close via additive genre-tier mutation entries — never a world-tier mechanics fork.
- **D-C — Chargen texture = three additive deltas to the live 5-step flow** (`char_creation.yaml`: origins, pronouns, mutation, artifact, confirmation): the stock step, the "Roll the Bones" alt-attribute flag (3d6-in-order over the standard six, 2-stat reroll budget), and world-content origins. Cryptic Alliance ships as faction tags (content), the retrofit hook for AWN Plan 7 Enclaves. Penitent is a content-only flavor-focus over AWN classes; its vow resolves through System Strain or existing penalty hooks.
- **D-D — OTEL lie-detector spans:** `awn.saint.applied` (saint id, bundle, drawback, MP math) and `awn.stock.applied` (stock id, trait deltas), emitted from the mutation/chargen subsystems. The GM panel must prove a Saint drawback fired mechanically, not as narrator improv.

**Key files:** engine — `sidequest-server/sidequest/mutation/` (registry + loaders extend here), `sidequest/game/ruleset/awn.py` (untouched unless hook points needed), chargen flow modules + `sidequest-ui` chargen screens (103-2/103-3 only). Content — `sidequest-content/genre_packs/mutant_wasteland/worlds/seaboard_of_saints/` (new world dir: world/lore/history/saints/stocks/places/cartography/encounter_tables/cultures/factions/tropes/openings/archetypes/bestiary/visual_style/portrait_manifest), `genre_packs/mutant_wasteland/mutations.yaml` (additive entries only, coordinated genre PR).

**Flow:** world load → SaintRegistry/stock loader validate IDs against genre catalog (fail loudly) → chargen stock step branches → Saint preset or stock trait-set applies through MpEconomy/stock application → `awn.saint.applied`/`awn.stock.applied` spans → drawback/trait fires in confrontation via existing mutation-use machinery.

**Story graph (critical path bold):** **103-1 (Saint layer) → 103-2 (stocks) → 103-8 (full content roster) → 103-10 (e2e wiring)**. Content lanes parallelize behind schema freezes: 103-4 (canon) behind 103-1; 103-5 (world core) independent; 103-6 (regions) + 103-7 (cultures/factions) behind 103-5; 103-9 (asset gate) behind 103-6+103-7. 103-3 (Roll the Bones) is independent. GM-lane content stories (103-4..103-9) route to the gm background agent per Keith's standing directive; engine stories (103-1, 103-2, 103-3, 103-10) run the normal sprint TDD flow.

## Cross-Epic Dependencies

**Depends on:**
- Epic 102 (WN family completion) — 102-7 delivered AWN Plan 1 (module + binding); the AWN Plan 2 mutation catalog + MpEconomy this epic's Saints reference. **Both merged; satisfied.**
- ADR-117 RulesetModule seam, ADR-114 ablative HP, System Strain — live substrate, no work required.

**Depended on by:**
- AWN Plan 7 (Enclaves & Settlements, future) — 103-7's Cryptic-Alliance faction tags are its retrofit hook.
- AWN Plans 3–6 (Radiation, Stress, Survival, Creatures, future) — Seaboard content will gain mechanical depth when these land; v1 content must not pre-promise them narratively.
- Future mutant_wasteland worlds — the saints.yaml/stocks.yaml schemas and the generic stock-application path become reusable world-tier surfaces.
