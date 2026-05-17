---
id: 106
title: "Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion, maze-maker Family Port + Complication Ledger"
status: accepted
date: 2026-05-16
deciders: ["Keith Avery", "Chrisjen Avasarala (Architect, planning mode)"]
supersedes: []
superseded-by: null
related: [55, 74, 87, 96]
tags: [game-systems, room-graph, code-generation]
implementation-status: partial
implementation-pointer: docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md
---

# ADR-106: Runtime Procedural Jaquaysed Megadungeon — Contiguous Edge-Expansion, maze-maker Family Port + Complication Ledger

## Status

Accepted. Design detail lives in
`docs/superpowers/specs/2026-05-16-sunden-deep-procedural-megadungeon-design.md`
(the §10 decomposition is the live implementation tracker). This ADR is the durable
decision record and scope boundary the spec's §9 mandates; it does not restate the
spec, it locks the contested calls and the seams.

**See `## Post-Closure Correction (2026-05-17)` below.** A live multiplayer
playtest proved the materializer is reached in production code but silently
no-ops at the genre/world gate; clause 12's wiring test is satisfied in letter
(it calls the seam) but not in spirit (it bypasses the real connect→row→attach
provenance). `implementation-status` stays `partial`; the spec's §10 / status
block over-claimed "CLOSED & VERIFIED" and is corrected there.

## Context

`caverns_and_claudes` ships one hand-authored world, `caverns_sunden`: 54 rooms across
three discrete sin-themed dungeons, wrapped in a self-aware comedy register. We are
pivoting to the opposite product: a new world, `beneath_sunden` ("Beneath Sünden"), a
single procedurally generated megadungeon played straight as a Tomb-of-Horrors
deathtrap. This is a content + structure pivot, not a rewrite of the old world.

Four design pressures forced explicit decisions:

1. **Floors are a lie we keep telling.** Discrete floor indexing leaks into
   persistence, keying, and player mental models, and it makes "the dungeon grows
   without bound" structurally awkward.
2. **Jaquays at the macro scale fights perfect mazes at the micro scale.** The
   maze-maker family produces *perfect* mazes (zero loops) — exactly the linearity
   Jaquays topology forbids.
3. **Curation breaks determinism, and that is correct.** LLM-assisted curation makes
   generated output non-byte-reproducible. A seed-replay model would be a lie about
   what the save contains.
4. **ADR-087 lists "resist-you"/Keeper-awareness as a restore item.** This world must
   explicitly *not* inherit that. The challenge here is authored content, not a hidden
   attrition subsystem.

## Decision

Build a server-native (`sidequest-server/sidequest/dungeon/`) runtime procedural
megadungeon with the following locked architecture. **No daemon IPC, no CLI shell-out
on the runtime path.**

1. **One contiguous map, no discrete floors.** A single connected region graph rooted
   at the surface entrance in the town of Sünden, growing by **edge-expansion**:
   themed region clusters stitched onto the frontier as the party pushes outward.
   Nothing in persistence or generation indexes by floor — keyed by region/expansion
   id only.

2. **`depth_score` is the only notion of depth.** An abstract scalar (≈ ordinary-route
   graph distance from the surface entrance, jittered, frozen at attach) driving theme
   depth-bands, set-piece lethality, and creature tiers. "Level" survives only as
   loose player-facing shorthand — never an authoritative coordinate, key, or
   container.

3. **Two-tier generator.** Stage 1 = region graph with **Jaquays invariants enforced
   as hard re-roll post-conditions** (≥2 independent edges per expansion, ≥1 loop back
   into explored regions, mixed connection types with ≥1 non-obvious edge, ≥1 shortcut
   toward the surface, no single-entrance region) plus an incremental global
   loop/solvability check on attach. Stage 2 = per-theme interior fill via the ported
   maze-maker family. A `connection_burst` knob drives connection count well above the
   invariant floors so an expansion "pops in" wired into many existing regions at once.

4. **Perfect-maze mitigation via `braid_ratio`.** `depthfirst` and `prim` produce
   perfect mazes — anti-Jaquays at the room scale. A per-theme `braid_ratio`
   post-process removes a tunable fraction of dead-ends to introduce interior loops.
   Spec default: labyrinth-trap themes `0.0` (deliberate pristine maze), other maze
   themes `≈0.3`. This decision is recorded explicitly because it is the resolution of
   pressure (2) above and must not be silently dropped.

5. **maze-maker family port — extends ADR-096, does not replace it.** ADR-096's
   cellular port is **re-homed** (not forked) into `sidequest/dungeon/interiors/`
   alongside `depthfirst`, `prim`, a new `roomcorridor`, a shared grid model, a
   `generator` coordinator, and a `braid` post-process. One generator interface shared
   by the authoring CLI *and* runtime — single implementation, no fork. maze-maker's
   `encounters.rb` is reference only; the set-piece/trope-component model supersedes
   it and is not ported.

6. **Authored theme palette, procedural placement.** The pack ships a curated
   `themes/` directory (interior algorithm + params, creature/loot tables, narrator
   register, depth-band eligibility, adjacency affinities, a set-piece library). The
   generator chooses, places, and connects.

7. **Set-pieces are templates that start at attach.** Component slots
   (layout/features/creatures/loot + trope/quest components) roll from the seed at
   materialization. Trope components instantiate and *start*; quest components seed.
   They are live game threads before the party reaches the room.

8. **Complication accumulation is the spine — emergent, not a subsystem.** Started
   threads persist until player-resolved; look-ahead keeps attaching expansions;
   unresolved threads pile up in the open complication ledger and crush the careless.
   Pacing is **player-action-gated, not tick-based** — there is no clock. Expansions
   are **bursty** (`connection_burst` paired with threads-lit-per-expansion) so the
   structural and dramatic spikes land together. This explicitly *replaces*, and does
   **not** revive, ADR-087's "resist-you"/Keeper-awareness/torch-burn restoration
   items — that subtle loop is deleted, not deferred, and is wrong for this audience.

9. **The save is the source of truth; determinism is intentionally broken by
   curation.** `campaign_seed` is only the pipeline's starting input. LLM-assisted
   curation makes committed output non-byte-reproducible, and that is accepted. Frozen
   expansions are never regenerated; a mid-campaign generator-version bump touches only
   never-materialized expansions. Raw pre-curation Stage 1/Stage 2 output remains
   seed-reproducible (the determinism contract holds *up to* the curation seam, not
   past it).

10. **Async look-ahead materializer, committed in one transaction.** A worker runs
    ahead of the party through design → fill → curate → attach → commit. The whole
    expansion plus its started threads is written to the live save atomically and is
    immediately live. It promotes a look-ahead-materialized expansion to active on the
    frontier-crossing transition, *extending* ADR-055's room-graph init rather than
    introducing a parallel navigation path.

11. **`caverns_sunden` is retired intact.** Marked legacy/unlisted in the pack
    manifest; files remain on disk; old saves load unchanged. Zero demolition. The
    retirement flag must not be set until `beneath_sunden` is end-to-end playable —
    sequencing constraint, not a cleanup task.

12. **OTEL and a wiring test are mandatory (CLAUDE.md).** Spans on every stage —
    `dungeon.materialize.{design,fill,curate,attach,commit}`, `setpiece.attach`,
    `trope.start`, `quest.seed`, `ledger.add`, `ledger.resolve`, `frontier.expand`.
    At least one integration test must prove the materializer is invoked from the real
    session/frontier-crossing path, not only unit-tested. The GM panel is the lie
    detector; until the materializer is wired, the entire generator stack is dead code.

### Relationship to existing ADRs

- **Extends ADR-055 (Room Graph Navigation).** Stage 2 output conforms to the existing
  `rooms.yaml` shape + ADR-096 mask sidecars; room-graph navigation consumes it
  unchanged. The frontier-crossing promotion is an addition to ADR-055's transition
  model, not a replacement.
- **Extends ADR-096 (Cavern Renderer Revival).** The cellular generator is re-homed
  into the shared `interiors/` library; ADR-096's contract is preserved, its port
  generalized to the full maze-maker family.
- **Does NOT revive ADR-087 restoration items.** Specifically the "resist-you" /
  Keeper-awareness / torch-burn attrition loop and the `tick_on_room_transition` /
  light-source-decrement gaps ADR-087 tracks for ADR-055. Beneath Sünden's challenge is
  authored set-pieces, not a per-transition attrition subsystem. ADR-087's restore
  verdict for those items stands for the *legacy* worlds; it is out of scope here.
- **Reuses ADR-074 (Dice Resolution Protocol).** Set-pieces that resolve on a roll
  ride the existing player-facing dice protocol. **No new mechanics engine.**

## Scope Boundary

**In scope:** edge-expansion generation, Jaquays topology enforcement, `depth_score`
gradient, theme palette, set-piece templates, trope/quest-at-attach, complication
ledger, persistence (`dungeon_map`/`frontier`/mutation overlay/ledger), async
look-ahead materializer, engine wiring, OTEL, the maze-maker family port.

**Out / unchanged:** the deleted "resist-you" subtle loop (gone, not deferred); any
new dice/combat mechanics (reuse ADR-074); `caverns_sunden` (retired intact,
untouched); maze-maker `encounters.rb` (reference only, not ported); discrete floor
indexing (explicitly rejected); the comedy/sins/fourth-wall register of the old world.

## Consequences

**Positive.** The dungeon grows without bound from a single seed input; Jaquays
non-linearity is structurally guaranteed rather than hand-authored; one generator
serves both authoring and runtime; the challenge is legible at the table (no hidden
math); player-paced pressure removes the "arbitrary clock" failure mode.

**Negative / accepted costs.**

- **Saves are large and non-reproducible.** The save *is* the dungeon. Accepted: this
  is the correct model for curated content; seed-replay was always a lie about a
  curated artifact.
- **The entire shipped stack is inert until the materializer wires it.** Plans 1–4 +
  the Content Cookbook are merged pure substrate with zero non-test runtime consumers.
  This is the project's real bottleneck and the reason clause 12's wiring test is
  mandatory, not optional.
- **Curation is LLM-assisted on the materialization path.** Latency and cost land on
  expansion, mitigated by the async look-ahead worker running ahead of the party.
- **Burst tuning is empirical.** `connection_burst` and threads-lit-per-expansion have
  no a-priori correct value; they are world-config knobs tuned by playtest.

## Implementation Status

`partial`. As of 2026-05-16, per spec §10 decomposition:

- **Shipped:** maze-maker family port (`sidequest/dungeon/interiors/`), region-graph +
  Jaquays (`region_graph/`), `depth_score` (`region_graph/depth.py`), theme palette +
  set-piece schema (`themes.py`/`setpieces.py`), Content Cookbook contract
  (`game/cookbook/assemble.py`), and the `beneath_sunden` content scaffold
  (`cookbook/`, `corpus/`, `world_register.yaml`).
- **In flight:** persistence layer (decomposition item 5).
- **Not yet designed:** set-piece/trope-at-attach wired to the ledger (item 6); async
  look-ahead materializer + frontier-crossing promotion + wiring + OTEL (item 7) — the
  keystone that makes the stack reachable.
- **Written, not executed:** `beneath_sunden` world artifact authoring +
  `caverns_sunden` retirement (item 8).

The spec's §10 decomposition table is the authoritative live tracker; update it, not
this section, as items land.

## Post-Closure Correction (2026-05-17)

**Recorded by:** Architect, from a live `beneath_sunden` 3-player multiplayer
playtest (session `2026-05-17-beneath_sunden-mp`).

The spec's §10 / status block and the project tracker recorded ADR-106 as
**CLOSED & VERIFIED 2026-05-17**. A live session contradicts that claim. This
ADR's `implementation-status: partial` was — and remains — correct; the spec
closure record over-claimed and is the artifact to correct there.

**What the playtest showed.** Three players created characters at the Ropefoot
entrance and descended the shaft. The narrator produced fully improvised
dungeon geography (a named NPC volunteered a clue referencing "the east
turning — second level"); the UI Map showed "No map data yet"; and the server
log contained **zero** `dungeon.materialize.*` / `frontier.*` / ledger spans
and **no** raised exception, across a server confirmed running the merged
Plan-7 wiring on hot-reloaded latest code.

**Root cause (architectural).** The Plan-7 seam
(`dungeon/session_integration.py::attach_dungeon_to_session`) is wired
unconditionally from `handlers/connect.py:763` and is loud-by-design on every
dependency failure. Its **only** silent exit is the genre/world gate
(`session_integration.py:98`): `if genre_slug != "caverns_and_claudes" or
world_slug != "beneath_sunden": return None`. Zero spans **and** zero raise can
only mean the gate returned `None` — i.e. `row.world_slug` / `row.genre_slug`
at the connect call site was not the gate literal at the instant `attach` ran
(connect-vs-lobby ordering / slug-provenance for a fresh MP host game; to be
confirmed by OQ-2). The gate's silent `return None` cannot distinguish
"correctly skipped for another world" from "wrongly skipped for beneath_sunden
because the slug was unresolved" — a **No-Silent-Fallbacks** violation in the
one place the seam is allowed to be quiet.

**Clause 12 assessment.** The keystone wiring test
(`tests/dungeon/test_session_lifecycle_wiring.py`) invokes the seam with a
pre-resolved `world_slug="beneath_sunden"`. It proves the seam works; it does
**not** exercise the connect→row→attach chain that supplies that slug at
runtime. Clause 12 ("invoked from the real session/frontier-crossing path, not
only unit-tested") is therefore met in letter, unmet in spirit. This is the
exact "Verify Wiring, Not Just Existence" failure the project guards against,
and the reason clause 12 names the GM panel the lie detector.

**Required to re-close (all four):**

1. Add a loud `dungeon.attach.{bootstrapped|skipped}` OTEL span carrying
   `genre`, `world_slug`, `reason` at the gate / call site — so the skip is
   visible, not silent (OTEL Observability Principle; smallest, do first).
2. Fix the `row.world_slug` / `row.genre_slug` provenance (or move the single
   attach incision to where the world is authoritatively bound for **all**
   flows — MP host, MP join, resume — favoring relocation over added logic per
   the spec's "two one-line incisions" minimalism; the seam is already
   idempotent via `already_seeded` + `_ATTACHED_SAVES`).
3. Extend the keystone test to drive the real connect→row→attach chain
   (construct the session via the connect handler, not a hand-built
   `attach_dungeon_to_session(world_slug="beneath_sunden")` call), asserting
   bootstrap spans fire — satisfying clause 12 in spirit.
4. Correct the spec's §10 / status block: revert "CLOSED & VERIFIED" to the
   accurate state; ADR-106 stays `partial` until 1–3 land and a live session
   re-verifies materialization.

Remediation is tracked operationally in the playtest ping-pong
(`sq-playtest-pingpong.md`, headline `[BS-BUG]`); this section is the durable
record.
