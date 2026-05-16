# Sünden Deep — Procedural Jaquaysed Megadungeon

- **Date:** 2026-05-16
- **Status:** Approved (design) — pending spec read, then implementation plan
- **Pack:** `caverns_and_claudes`
- **New world:** `sunden_deep` (name negotiable)
- **Supersedes nothing; extends:** ADR-055 (Room Graph Navigation), ADR-096 (Cavern Renderer Revival)
- **Explicitly does NOT revive:** ADR-087's "resist-you" / keeper-awareness restoration items

## 1. Problem & Intent

`caverns_and_claudes` today ships one hand-authored world, `caverns_sunden`: 54 rooms
across three discrete "sin" dungeons (Pride/Greed/Gluttony) reached from a hamlet,
wrapped in a self-aware, genre-winking comedy register, with `navigation_mode: region`.

We want the opposite: **one great procedurally generated megadungeon beneath the town
of Sünden, descending effectively without bound, heavily Jaquaysed, played straight as
a Tomb-of-Horrors deathtrap.** The sins motif is removed entirely. The meta/comedy
lampshading is removed entirely. The challenge is *obvious, authored, lethal* — not a
subtle attrition subsystem.

This is a content + structure pivot. It is a *new world*; the existing one is retired
intact.

## 2. Decisions (locked during brainstorming)

| # | Decision |
|---|----------|
| 1 | **Lazy + persisted** generation. A `campaign_seed` is the pipeline's starting input; levels materialize as the party descends and **freeze into the save**. Never regenerated. |
| 2 | **Two-tier generator.** Stage 1 = region graph (Jaquays topology enforced here). Stage 2 = per-theme interior fill. |
| 3 | **Authored theme palette, procedural placement.** The pack ships curated themed zone definitions; the generator chooses/places/connects them via depth bands + adjacency affinity. |
| 4 | **Structure-only scope.** No subtle "resist-you" loop — *deleted, not deferred*. Challenge is authored lethal set-pieces (Tomb of Horrors). |
| 5 | **New world `sunden_deep`.** `caverns_sunden` marked legacy/unlisted, files intact, old saves keep loading. Town name "Sünden" carries. |
| 6 | **Server-native generator library** (`sidequest/dungeon/`). No daemon IPC, no CLI shell-out on the runtime path. |
| 7 | **Background look-ahead materialization.** Level N+1 (optionally N+2) materializes asynchronously while the party explores level N. Once committed it is *immediately live*. |
| 8 | **Set-pieces are templates with randomized components.** Some components are tropes/quests; they **start at attach (materialization)**, not at room entry, and persist in game state until resolved by players. |
| 9 | **Complication accumulation** is the spine: unresolved threads pile up as you descend; only player resolution clears them. Emergent, fully legible, no hidden math. |
| 10 | **Port the maze-maker family**, not just Cellular: extend the ADR-096 port to `depthfirst`, `prim`, the shared grid model + generator coordinator, plus a new room-and-corridor layout and a `braid` post-process. |

## 3. Tone & World Identity (§1)

`sunden_deep` plays the dungeon crawl **straight, grave, lethal**. No sins, no
keepers-of-sins, no fourth-wall lampshading, no winking at the genre. Player pitch:

> *"Sünden sits on a wound in the world. Everything below wants you dead and most of
> it is older than the town. People still go down — some come back up richer. The town
> keeps the name and asks no questions. Bring rope. Bring spares."*

- **Town of Sünden** is the surface hub: the *only* hand-authored content in the new
  world — a small, sincere frontier extraction town. Its name is never explained or
  winked at.
- **`world.yaml` axis snapshot:** comedy ≈ `0.05–0.10`, gravity ≥ `0.85`. Narrator
  prompts for this world strip all self-referential / genre-aware framing.
- **`caverns_sunden`** → marked legacy/unlisted in the pack manifest. Files remain on
  disk; old saves load unchanged. Zero demolition in this spec.
- **Naming:** spec defaults to `sunden_deep`; alternatives `the_deep`, `sunden_descent`.

## 4. Challenge Philosophy — Tomb of Horrors (§ scope)

The dungeon's danger is **content, not a subsystem**: discrete, authored, telegraphed,
lethal set-pieces. The dungeon plays *fair* — lethal danger is visible to the careful;
it is merciless to the careless.

- Each theme ships a **set-piece library**: traps, tricks, devious puzzles, save-or-die
  features.
- Each set-piece carries explicit **telegraph text** (the tell a careful party can
  read) and a **hard, legible outcome**.
- Where a set-piece resolves on a roll, it rides the **existing player-facing dice
  protocol (ADR-074)** — you see the save, the number, and yourself die. **No new
  mechanics engine.**
- The deleted "resist-you" subtle loop (keeper awareness, torch-burn attrition clock)
  is gone — it is invisible at the table and wrong for this audience.

## 5. Two-Tier Generator (§3)

### 5.1 Stage 1 — Region graph (Jaquays topology)

From `(campaign_seed, level_index)`, place themed zones as graph nodes and wire them
under **Jaquays invariants enforced as hard post-conditions** — a generated level is
re-rolled until it passes:

- ≥ 2 independent connections between adjacent regions (no single chokepoint).
- ≥ 1 loop per level (no pure-tree levels).
- ≥ 2 vertical connections up and ≥ 2 down (stairs / shafts / chutes), not one.
- ≥ 1 "shortcut" edge that collapses distance back toward the surface once discovered.
- ≥ 1 secret / conditional connection.
- No region with only one entrance.

All thresholds are **tunable knobs in the world config**.

### 5.2 Stage 2 — Interior fill (ported maze-maker family, theme-keyed)

| Theme class | Generator | Texture |
|-------------|-----------|---------|
| Organic (cavern, fungal warren, flooded) | `cellular` (ADR-096 port, re-homed) | organic blobs |
| Labyrinthine (catacomb, undercity, maze-trap) | `depthfirst` (recursive backtracker) | twisty, dead-end-rich |
| Structured (crypt, tomb maze) | `prim` | even branching |
| Built (temple, vault, hall) | `roomcorridor` (new, on shared grid model) | placed rooms + carved corridors |

Output conforms to the existing **ADR-055 `rooms.yaml` shape + ADR-096 mask sidecars**,
so room-graph navigation consumes it unchanged.

**Perfect-maze subtlety (flagged):** `depthfirst` and `prim` produce *perfect* mazes
(one path between any two cells, zero loops) — anti-Jaquays at the room scale even
though Stage 1 guarantees macro non-linearity. Mitigation: a per-theme **`braid_ratio`**
post-process that removes a tunable fraction of dead-ends to introduce interior loops.

- **Spec defaults:** labyrinth-trap themes `braid_ratio = 0.0` (pristine perfect maze,
  deliberately); all other maze themes `≈ 0.3`. Tunable per theme in the palette.

## 6. Theme Palette + Set-Piece Schema (§4)

The pack ships a curated `themes/` directory. Each theme definition:

- Interior algorithm + params (incl. `braid_ratio`).
- Creature table, loot table.
- Narrator flavor / register.
- Depth-band eligibility.
- Adjacency affinities (e.g. tomb → crypt deepens; flooded clusters).
- A **set-piece library**.

A **set-piece is a template with randomized component slots**:

- `layout`, `features`, `creatures`, `loot`
- one-or-more **trope/quest components**

At **attach** (during materialization), each slot rolls from the seed. Trope components
**instantiate and start**; quest components **seed**. They are immediately live game
threads (e.g. a temple's `priest_demands_a_sacrifice` trope begins counting down /
generating rumor before the party has reached that room). maze-maker's `encounters.rb`
is **reference only** — our set-piece/trope-component model supersedes it; not ported.

## 7. Materialization Pipeline + Persistence (§5)

An **async materialization worker** runs ahead of the party. While the party explores
level *N*, it materializes *N+1* (optionally *N+2*):

1. **Design** — Stage 1 region graph.
2. **Fill** — Stage 2 interiors.
3. **Curate** — pass 1 content, pass 2 creatures. Generation proposes; curation
   selects/refines to ship quality. (Curation is expected to be LLM-assisted.)
4. **Attach** — roll each set-piece's components; start trope components; seed quests.
5. **Commit** — the whole materialized level **plus its started threads** is written
   into the live save in **one transaction**, and begins affecting the game at once.

**Persistence (new, in the save DB):**

- `dungeon_levels` — geometry + mask + set-piece component states + per-level
  generator-version stamp.
- **Mutation overlay** — sprung traps, looted rooms, collapses, resolved set-pieces.
- **Open-complication ledger** — every started-but-unresolved trope/quest thread, with
  origin level + status. First-class persisted structure.

**The save is the source of truth.** `campaign_seed` is only the pipeline's starting
input; curation makes output *not byte-reproducible*, and that is accepted. Frozen
levels are never regenerated. If the generator version changes mid-campaign, frozen
levels are untouched; only never-visited levels use new code.

### 7.1 Complication accumulation (§ spine)

Because threads start at attach, persist until player-resolved, and look-ahead keeps
attaching levels, **unresolved threads accumulate**. The skipped sacrifice-priest on
level 3 is still counting down on level 5; the thing you woke on level 2 is still
loose. Descend carelessly and the open-complication ledger lengthens; the deeper you
go, the more concurrent live threads act on the game at once. Threads shrink **only**
when players resolve them (close the set-piece, finish/fail the quest, kill it, seal
it, flee it). This is emergent — not a subsystem — and fully visible in the quest log /
GM panel. It *is* the Tomb-of-Horrors escalation: your unpaid debts pile up in the open
and crush you.

## 8. Engine Integration (§6)

New module `sidequest-server/sidequest/dungeon/`:

| File | Responsibility |
|------|----------------|
| `region_graph.py` | Stage 1 generation + Jaquays invariant checker (re-roll loop) |
| `interiors/` | `grid.py`, `generator.py` (coordinator), `cellular.py` (re-homed from ADR-096), `depthfirst.py`, `prim.py`, `roomcorridor.py`, `braid.py` |
| `themes.py` | Theme palette loader |
| `setpieces.py` | Template roll + trope/quest attach |
| `materializer.py` | Pipeline + async look-ahead worker |
| `persistence.py` | Save schema (`dungeon_levels`, mutation overlay, complication ledger) |

- **maze-maker port:** the Ruby `grid`/`generator`/`depthfirst`/`prim` are ported to
  Python into `interiors/`, **extending the ADR-096 cellular-only port to the full
  family**. One generator interface keyed by theme. Shared by the authoring CLI *and*
  runtime — single generator, no fork. `cellular.py` re-homes from
  `sidequest-content/tools/cavern_renderer/` into this shared library.
- Consumes/extends **ADR-055** room-graph init; adds a down-connection transition that
  promotes a look-ahead-materialized level to active.
- **OTEL (per CLAUDE.md, mandatory):** spans on every stage —
  `dungeon.materialize.{design,fill,curate,attach,commit}`, `setpiece.attach`,
  `trope.start`, `quest.seed`, `ledger.add`, `ledger.resolve`. The GM panel is the lie
  detector.
- **Wiring test (per CLAUDE.md, mandatory):** at least one integration test proving the
  materializer is invoked from the real session/descent path — not only unit-tested.

## 9. Scope Boundary & ADR

**In scope:** generation, Jaquays topology, theme palette, set-piece templates,
trope/quest-at-attach, complication ledger, persistence, look-ahead worker, engine
wiring, OTEL, maze-maker family port.

**Out / unchanged:** the deleted resist-you subtle loop (gone, not deferred); any new
dice/combat mechanics (reuse ADR-074); `caverns_sunden` (retired-intact, untouched);
maze-maker `encounters.rb` (reference only, not ported).

**New ADR required:** "Runtime Procedural Jaquaysed Megadungeon — maze-maker Family
Port + Complication Ledger." Must explicitly state it *extends* ADR-055 and ADR-096,
*does not* revive ADR-087 resist-you items, and records the perfect-maze/braid decision.

## 10. Decomposition (implementation-plan seed)

Likely sequenced sub-plans:

1. **maze-maker family port** — grid model, generator coordinator, depthfirst, prim,
   roomcorridor, braid; re-home cellular; parity tests vs. authoring output.
2. **Region-graph generator + Jaquays invariant checker** — Stage 1, property-tested
   against every invariant.
3. **Theme palette + set-piece schema** — authored content scaffold + loader.
4. **Persistence layer** — `dungeon_levels`, mutation overlay, complication ledger;
   round-trip tests.
5. **Set-piece attach + trope/quest-at-attach** — wired to the ledger.
6. **Async look-ahead materializer + descent promotion** — wiring test + OTEL.
7. **`sunden_deep` world authoring + `caverns_sunden` retirement** — manifest, town
   hub, theme palette content, curation passes.

## 11. Testing Strategy

- **Jaquays invariants:** property tests asserting every §5.1 post-condition holds (or
  the level was re-rolled) across a seed sweep.
- **Solvability:** every materialized level is fully traversable; every region
  reachable; every required connection navigable.
- **Determinism (pre-curation):** raw Stage 1 + Stage 2 output is seed-reproducible;
  curation explicitly breaks this and the save is asserted as source of truth.
- **Persistence round-trip:** materialize → commit → reload → identical geometry +
  ledger; mutation overlay survives reload; frozen level untouched after generator
  version bump.
- **Complication ledger:** threads start at attach, persist across descent, clear only
  on resolution; accumulation observable.
- **Wiring:** materializer invoked from real session/descent path (mandatory).
- **maze-maker parity:** ported algorithms match authoring-time output for shared seeds
  where determinism is contractual.

## 12. Open Items (confirm at spec read)

- World name: `sunden_deep` (default) vs `the_deep` / `sunden_descent`.
- `braid_ratio` defaults: labyrinth-trap `0.0`, other maze themes `≈0.3`.
- Look-ahead depth: N+1 only vs N+1 and N+2.
- Curation mechanism detail (LLM model/prompt strategy) — deferred to implementation
  plan unless it changes scope.
