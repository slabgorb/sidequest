# Beneath Sünden — Procedural Jaquaysed Megadungeon

- **Date:** 2026-05-16
- **Status:** Approved (design) — revised at spec read; pending re-approval, then implementation plan
- **Pack:** `caverns_and_claudes`
- **New world:** `beneath_sunden` — display name **"Beneath Sünden"**
- **Supersedes nothing; extends:** ADR-055 (Room Graph Navigation), ADR-096 (Cavern Renderer Revival)
- **Explicitly does NOT revive:** ADR-087's "resist-you" / keeper-awareness restoration items

## 1. Problem & Intent

`caverns_and_claudes` today ships one hand-authored world, `caverns_sunden`: 54 rooms
across three discrete "sin" dungeons (Pride/Greed/Gluttony) reached from a hamlet,
wrapped in a self-aware, genre-winking comedy register, with `navigation_mode: region`.

We want the opposite: **one great procedurally generated megadungeon beneath the town
of Sünden — a single contiguous space that grows at its edges effectively without
bound, heavily Jaquaysed, played straight as a Tomb-of-Horrors deathtrap.** The sins
motif is removed entirely. The meta/comedy lampshading is removed entirely. The
challenge is *obvious, authored, lethal* — not a subtle attrition subsystem.

This is a content + structure pivot. It is a *new world*; the existing one is retired
intact.

## 2. Decisions (locked during brainstorming + spec read)

| # | Decision |
|---|----------|
| 1 | **One contiguous map, no discrete floors.** The dungeon grows by **edge-expansion** — new themed area-clusters are appended at the frontier as the party pushes outward. There is no floor index. |
| 2 | **"Level / depth" is an abstract difficulty gradient** (`depth_score`), not a coordinate. It drives theme depth-bands, set-piece lethality, and creature tiers, and is bucketed loosely for player-facing flavor only. |
| 3 | **Lazy + persisted.** A `campaign_seed` is the pipeline's starting input; expansions materialize as the party approaches an unexpanded edge and **freeze into the save**. Never regenerated. |
| 4 | **Two-tier generator.** Stage 1 = region graph (Jaquays topology enforced here). Stage 2 = per-theme interior fill. |
| 5 | **Authored theme palette, procedural placement.** The pack ships curated themed zone definitions; the generator chooses/places/connects them via depth-bands + adjacency affinity. |
| 6 | **Structure-only scope.** No subtle "resist-you" loop — *deleted, not deferred*. Challenge is authored lethal set-pieces (Tomb of Horrors). |
| 7 | **New world `beneath_sunden`** ("Beneath Sünden"). `caverns_sunden` marked legacy/unlisted, files intact, old saves keep loading. Town name "Sünden" carries. |
| 8 | **Server-native generator library** (`sidequest/dungeon/`). No daemon IPC, no CLI shell-out on the runtime path. |
| 9 | **Background look-ahead expansion.** The next frontier expansion(s) materialize asynchronously as the party approaches an unexpanded edge. Once committed they are *immediately live*. |
| 10 | **Set-pieces are templates with randomized components.** Some components are tropes/quests; they **start at attach (materialization)**, not at room entry, and persist in game state until resolved by players. |
| 11 | **Complication accumulation** is the spine: unresolved threads pile up as you push deeper; only player resolution clears them. Emergent, fully legible, no hidden math. **Player-paced, not tick-based** — the rate is gated entirely by the players' choice to push into new frontier; there is no semi-arbitrary clock. |
| 11a | **Expansions are bursty by design.** When a new area pops in it stitches *many* connections into already-explored territory and lights up *many* live threads at once — a deliberate spike, not a trickle. The burst is where the emergent "fun" comes from. |
| 12 | **Port the maze-maker family**, not just Cellular: extend the ADR-096 port to `depthfirst`, `prim`, the shared grid model + generator coordinator, plus a new room-and-corridor layout and a `braid` post-process. |

## 3. Tone & World Identity (§1)

"Beneath Sünden" plays the dungeon crawl **straight, grave, lethal**. No sins, no
keepers-of-sins, no fourth-wall lampshading, no winking at the genre. Player pitch:

> *"Sünden sits on a wound in the world. Everything below wants you dead and most of
> it is older than the town. People still go down — some come back up richer. The town
> keeps the name and asks no questions. Bring rope. Bring spares."*

- **Town of Sünden** is the surface hub: the *only* hand-authored content in the new
  world — a small, sincere frontier extraction town. Its name is never explained or
  winked at. The surface entrance into the dungeon is the map's origin.
- **`world.yaml` axis snapshot:** comedy ≈ `0.05–0.10`, gravity ≥ `0.85`. Narrator
  prompts for this world strip all self-referential / genre-aware framing.
- **`caverns_sunden`** → marked legacy/unlisted in the pack manifest. Files remain on
  disk; old saves load unchanged. Zero demolition in this spec.
- **World slug** `beneath_sunden`, display name "Beneath Sünden".

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

## 5. The Map Model — One Contiguous Growing Space

There are **no floors**. The dungeon is a single connected region graph rooted at the
surface entrance in Sünden. It **grows by edge-expansion**: when the party approaches an
unexpanded frontier edge, a new **expansion** — one or more themed region nodes plus
their interiors — is generated and stitched onto the existing map.

**`depth_score`** is an abstract scalar (≈ accumulated traversal / graph distance from
the surface entrance, optionally jittered) attached to each region at attach time. It
is the *only* notion of "depth." It drives:

- theme depth-band eligibility,
- set-piece lethality tier,
- creature-table tier.

"Level" survives **only** as loose player-facing shorthand — a coarse bucket of
`depth_score` for narration/UI ("you reckon you're four, maybe five levels down"). It
is explicitly an approximation and is **never** an authoritative coordinate, key, or
container. Nothing in persistence or generation indexes by floor.

### 5.1 Stage 1 — Region graph + Jaquays invariants (per expansion)

Each expansion is generated from `(campaign_seed, expansion_id)` and attached under
**Jaquays invariants enforced as hard post-conditions** — an expansion is re-rolled
until it passes, and global checks run incrementally as it attaches:

- An expansion connects to the already-explored map by **≥ 2 independent edges** (no
  single chokepoint into new territory).
- Each expansion introduces **≥ 1 loop that ties back into already-explored regions**
  (backtracking variety; the contiguous map stays loopful — never a global tree).
- A **mix of connection types** (corridor / stairs / shaft / chute / secret), with
  **≥ 1 non-obvious (secret or conditional) edge** per expansion. Vertical links exist
  as flavor but are not the organizing axis.
- **≥ 1 shortcut edge** that, once discovered, collapses travel distance back toward
  the surface entrance.
- No region with only one entrance.

**Burst, not minimum.** The figures above are *floors*. A `connection_burst` knob
drives the *actual* count well above them so a new area "pops in" wired into many
existing regions simultaneously (loops, shortcuts, secret ties-back all at once),
rather than as a single thin appendage. Connection-richness is the structural half of
the bursty feel; thread-richness (§7.1) is the dramatic half.

All thresholds and burst knobs are **tunable in the world config**.

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
- `depth_score` band eligibility.
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

An **async materialization worker** runs ahead of the party. As the party approaches an
unexpanded frontier edge, it materializes that expansion (and optionally the next
one(s) along their heading):

1. **Design** — Stage 1 region graph for the expansion + Jaquays attach checks.
2. **Fill** — Stage 2 interiors.
3. **Curate** — pass 1 content, pass 2 creatures. Generation proposes; curation
   selects/refines to ship quality. (Curation is expected to be LLM-assisted.)
4. **Attach** — assign `depth_score`; roll each set-piece's components; start trope
   components; seed quests.
5. **Commit** — the whole materialized expansion **plus its started threads** is
   stitched onto the map and written into the live save in **one transaction**, and
   begins affecting the game at once.

**Persistence (new, in the save DB):**

- `dungeon_map` — the single growing region graph: nodes/regions (with `depth_score`),
  edges (typed, incl. secret/conditional), masks, set-piece component states, per-region
  generator-version stamp. **Keyed by region/expansion id, never by floor.**
- `frontier` — the set of unexpanded edges and the heading/`depth_score` an expansion
  there would spawn at.
- **Mutation overlay** — sprung traps, looted rooms, collapses, resolved set-pieces.
- **Open-complication ledger** — every started-but-unresolved trope/quest thread, with
  origin region + status. First-class persisted structure.

**The save is the source of truth.** `campaign_seed` is only the pipeline's starting
input; curation makes output *not byte-reproducible*, and that is accepted. Frozen
expansions are never regenerated. If the generator version changes mid-campaign, frozen
regions are untouched; only never-materialized expansions use new code.

### 7.1 Complication accumulation (§ spine)

Because threads start at attach, persist until player-resolved, and look-ahead keeps
attaching expansions, **unresolved threads accumulate**. The sacrifice-priest you
skipped back at the Drowned Galleries is still counting down while you're three
expansions deeper; the thing you woke early and didn't kill is still loose. Push on
carelessly and the open-complication ledger lengthens; the deeper you go, the more
concurrent live threads act on the game at once. Threads shrink **only** when players
resolve them (close the set-piece, finish/fail the quest, kill it, seal it, flee it).
This is emergent — not a subsystem — and fully visible in the quest log / GM panel. It
*is* the Tomb-of-Horrors escalation: your unpaid debts pile up in the open and crush
you.

**Why this beats a tick rate:** the pressure is paced entirely by *player action* —
choosing to push into new frontier is the only thing that spawns more — so there is no
arbitrary clock to tune or to feel cheated by. And each push is **bursty**: popping a
new area can light up several live threads at once (a guardian's bargain, a flooding
mechanism, a hunting thing, a sealed-vault countdown — together), not a single tidy
addition. That spike is the designed "fun": the players themselves pull the lever, and
the dungeon answers with a sudden tangle. Burst magnitude (threads lit per expansion)
is a tunable knob, paired with the §5.1 `connection_burst` so the structural and
dramatic spikes land together.

## 8. Engine Integration (§6)

New module `sidequest-server/sidequest/dungeon/`:

| File | Responsibility |
|------|----------------|
| `region_graph.py` | Stage 1 generation + Jaquays invariant checker (re-roll loop) + incremental global-loop check on attach |
| `interiors/` | `grid.py`, `generator.py` (coordinator), `cellular.py` (re-homed from ADR-096), `depthfirst.py`, `prim.py`, `roomcorridor.py`, `braid.py` |
| `themes.py` | Theme palette loader |
| `setpieces.py` | Template roll + trope/quest attach |
| `depth.py` | `depth_score` assignment + player-facing bucket mapping |
| `materializer.py` | Pipeline + async look-ahead worker; frontier tracking |
| `persistence.py` | Save schema (`dungeon_map`, `frontier`, mutation overlay, complication ledger) |

- **maze-maker port:** the Ruby `grid`/`generator`/`depthfirst`/`prim` are ported to
  Python into `interiors/`, **extending the ADR-096 cellular-only port to the full
  family**. One generator interface keyed by theme. Shared by the authoring CLI *and*
  runtime — single generator, no fork. `cellular.py` re-homes from
  `sidequest-content/tools/cavern_renderer/` into this shared library.
- Consumes/extends **ADR-055** room-graph init; adds a frontier-edge transition that
  promotes a look-ahead-materialized expansion to active when the party crosses into
  it.
- **OTEL (per CLAUDE.md, mandatory):** spans on every stage —
  `dungeon.materialize.{design,fill,curate,attach,commit}`, `setpiece.attach`,
  `trope.start`, `quest.seed`, `ledger.add`, `ledger.resolve`, `frontier.expand`. The
  GM panel is the lie detector.
- **Wiring test (per CLAUDE.md, mandatory):** at least one integration test proving the
  materializer is invoked from the real session/frontier-crossing path — not only
  unit-tested.

## 9. Scope Boundary & ADR

**In scope:** edge-expansion generation, Jaquays topology, `depth_score` gradient,
theme palette, set-piece templates, trope/quest-at-attach, complication ledger,
persistence, look-ahead worker, engine wiring, OTEL, maze-maker family port.

**Out / unchanged:** the deleted resist-you subtle loop (gone, not deferred); any new
dice/combat mechanics (reuse ADR-074); `caverns_sunden` (retired-intact, untouched);
maze-maker `encounters.rb` (reference only, not ported); discrete floor indexing
(explicitly rejected).

**New ADR required:** "Runtime Procedural Jaquaysed Megadungeon — Contiguous
Edge-Expansion, maze-maker Family Port + Complication Ledger." Must explicitly state it
*extends* ADR-055 and ADR-096, *does not* revive ADR-087 resist-you items, and records
the no-floors and perfect-maze/braid decisions.

## 10. Decomposition (implementation-plan seed)

Likely sequenced sub-plans:

1. **maze-maker family port** — grid model, generator coordinator, depthfirst, prim,
   roomcorridor, braid; re-home cellular; parity tests vs. authoring output.
2. **Region-graph generator + Jaquays invariant checker** — Stage 1 + incremental
   global-loop check, property-tested against every invariant.
3. **`depth_score` model** — assignment, jitter, player-facing bucketing.
4. **Theme palette + set-piece schema** — authored content scaffold + loader.
5. **Persistence layer** — `dungeon_map`, `frontier`, mutation overlay, complication
   ledger; round-trip tests.
6. **Set-piece attach + trope/quest-at-attach** — wired to the ledger. ✓ **SHIPPED** (Plan 6, `feat/beneath-sunden-plan-6-setpiece-attach`, server HEAD `6eeba8b`; full server suite twice-green at 6413 passed / 0 failed). As-built: quest components seed as `ComplicationThread(kind="quest")` via Plan 5's `open_thread()`, NOT via `ScenarioState` (ADR-053 superseded — whodunit model, no dungeon surface); creature/loot slot-option→manifest ref cross-resolution deferred to Plan 7 (Plan 4 shipped no ref convention); Plan 6 emits `setpiece.attach`/`trope.start`/`quest.seed`/`setpiece.resolve` spans — `ledger.add`/`ledger.resolve` are Plan 5's. See Post-Implementation Corrections in `docs/superpowers/plans/2026-05-16-beneath-sunden-plan-6-setpiece-attach.md`.
7. **Async look-ahead materializer + frontier-crossing promotion** — wiring test + OTEL.
8. **`beneath_sunden` world authoring + `caverns_sunden` retirement** — manifest, town
   hub, theme palette content, curation passes.

## 11. Testing Strategy

- **Jaquays invariants:** property tests asserting every §5.1 post-condition holds (or
  the expansion was re-rolled) across a seed sweep, including the incremental
  global-loop check as expansions attach.
- **Solvability:** the whole map stays fully traversable after every expansion; every
  region reachable; every required connection navigable.
- **Determinism (pre-curation):** raw Stage 1 + Stage 2 output is seed-reproducible;
  curation explicitly breaks this and the save is asserted as source of truth.
- **Persistence round-trip:** materialize → commit → reload → identical map + ledger;
  mutation overlay survives reload; frozen region untouched after generator version
  bump; no floor-indexed keys anywhere.
- **`depth_score`:** monotonic-ish with traversal from the entrance within tunable
  jitter; player-facing bucket mapping stable.
- **Complication ledger:** threads start at attach, persist across expansion, clear
  only on resolution; accumulation observable.
- **Wiring:** materializer invoked from real session / frontier-crossing path
  (mandatory).
- **maze-maker parity:** ported algorithms match authoring-time output for shared seeds
  where determinism is contractual.

## 12. Open Items (confirm at spec read)

- `braid_ratio` defaults: labyrinth-trap `0.0`, other maze themes `≈0.3`.
- Look-ahead breadth: how many frontier edges / expansions ahead to pre-materialize
  (one approaching edge vs. all near-frontier edges).
- Burst magnitude defaults: `connection_burst` (edges-into-existing-map per expansion)
  and threads-lit per expansion — how big a spike feels "fun" vs. overwhelming.
- `depth_score` → player-facing "level" bucket size (how coarse the shorthand is).
- Curation mechanism detail (LLM model/prompt strategy) — deferred to implementation
  plan unless it changes scope.
