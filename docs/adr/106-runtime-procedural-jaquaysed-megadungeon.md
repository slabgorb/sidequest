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

## Amendments

### Amendment A — Curate-stage robustness contract (story 50-26, 2026-05-18, Architect / M. Houlihan)

**Status:** Recorded as the gating contract for sprint story `50-26`. This amendment
does not change the §10 implementation-status tracker, clause numbering, frontmatter,
or any supersession relationship.

**Context.** The Stage-3 curate pass (`dungeon/materializer.py::_stage_curate` →
`_parse_curation_verdict`) does a strict `json.loads` on the curator LLM's verdict and
raises a fatal `CurationError` on any unparseable output. The 2026-05-17 beneath_sunden
MP playtest recorded a ~9-minute submit-and-wait table freeze on the R3 descent;
`/tmp/sidequest-server.log` showed `CurationError: ... Unterminated string ... line 452`
on `exp001.r0`. Forensic provenance: the SDK client's 4096-token default truncated the
~11.5 KB whole-expansion verdict mid-`wandering_table` deterministically. Commit
`b846544` ("region-projection 4-seam wiring + resume self-heal", 2026-05-17 19:22,
merged to develop via PR #317) raised the curate call to `max_tokens=16384` —
**after** the recorded freeze window (narration id#7→id#8 ≈ 16:51–17:00). The specific
truncation sub-case the playtest hit is therefore already mitigated on develop. That
mitigation is necessary but **not a contract**: a static token ceiling lowers the
probability of truncation without bounding the failure *mode*, and truncation is only
one way the verdict can be unparseable (stray preamble, unescaped quote in a telegraph,
oversized burst exceeding even 16384). Any residual unparseable verdict still produces
the fatal-`CurationError`-freezes-the-turn behaviour story 50-26 exists to eliminate.
(Whether the live R3 gap was *this* exact error is a clock-binding question owned by
OQ-1's next-session timestamped capture — out of scope here; the contract below makes
the table-freeze impossible regardless of which error fires.)

The prior engineer's in-code stance (`materializer.py` ~L909) — *"Curation is
enrichment, not a gate; give it the headroom to finish rather than degrade (No Silent
Fallbacks — the verdict must be whole, not a stamped-curated raw manifest)"* — is
**correct and retained**, but it conflated two different things. "Degrade" can mean
(a) **silent**: ship the raw manifest stamped `curated=true`, pretending nothing
happened — a genuine No-Silent-Fallbacks violation, correctly rejected; or
(b) **loud**: ship the raw manifest explicitly stamped `curated=false`, with a span,
an ERROR log, and a visible uncurated marker. (b) was never considered and is *not* a
silent fallback — it is ADR-006 Graceful Degradation done honestly.

**Decision — layered, bounded curate-robustness policy.** Not repair-vs-retry-vs-degrade
as alternatives; a single layered contract:

- **Layer 0 (retained):** keep `max_tokens=16384` (b846544). Necessary; eliminates the
  common deterministic-truncation case. Not the whole contract.
- **Layer 1 — bounded whole-call retry:** on an unparseable verdict, re-issue the
  one-shot curate call. Budget: **exactly 1 retry (2 attempts total)**. Each attempt is
  an independent one-shot — ADR-098-compatible (no `--resume`, no mid-generation tools,
  no continuation). This is **NOT JSON repair**: the system never invents the truncated
  tail. Inventing the missing `wandering_table` rows would silently corrupt creature
  stats / the CR→Edge seam — a worse failure than the freeze.
- **Layer 1 deadline:** the entire curate stage across all attempts is bounded by an
  explicit wall-clock cap (recommended **≤ 25 s total**). Deadline OR retry-exhaustion
  → Layer 2. This cap is the load-bearing guarantee that the turn cannot dead-air for
  minutes (the Alex / whole-table submit-and-wait pacing axis is the reason this story
  is high priority).
- **Layer 2 — loud degrade-to-uncurated:** ship the deterministic pre-curation
  `assemble_region` manifest (ADR-106 clause 9: it is valid, complete, and
  seed-reproducible — an honest procedurally-assembled region, not garbage) as the
  region content, stamped `curated=false`, with a visible `uncurated` marker on the
  materialized region, an ERROR-level log, and a routed `dungeon.curate.degraded` span.
  The materialize transaction **completes**; the turn proceeds in seconds.
- **Forbidden invariant (retained):** shipping the raw manifest stamped `curated=true`
  (the prior architect's correctly-rejected silent fallback) remains forbidden. Layer 2
  stamps `curated=false` — the exact inverse.
- **`CurationError` is retained, not deleted.** It is reserved for genuinely
  unrecoverable cases: (i) the assembled manifest itself structurally invalid (a real
  upstream bug — fail loud, never degrade a corrupt input into content); (ii) post-parse
  structural violations where degrading would corrupt mechanics rather than merely
  under-enrich (e.g. a curated row missing `cr` → CR→Edge impossible). Degradation is
  **per-region**: one unparseable/invalid region degrades that region loudly; regions
  that parsed are kept curated. One bad region never aborts the whole expansion.
- **Span taxonomy (clause 12, mandatory):** `dungeon.curate.parse_failed` — emitted on
  every parse failure, once per attempt, carrying `region_id`, `failure_kind`
  ∈ {`truncated`, `malformed`, `llm_error`, `deadline`}, `attempt`. And
  `dungeon.curate.degraded` — emitted when Layer 2 fires, carrying `region_id`,
  `failure_kind`, `attempts`, `elapsed_ms`. Both routed/watcher-visible so the GM panel
  proves whether a region shipped curated, retried-then-curated, or degraded.

**Rationale.** Reuse-first: Layer 0 keeps b846544; Layer 2's payload is the
`assemble_region` output that already exists and is contractually valid per clause 9;
the span infra already exists. The contract honours the prior architect's real concern
(no *silent* stamped-curated raw manifest) while fixing the failure they did not
foresee (a *loud* honest degrade is not what they rejected). ADR-014 Diamonds-and-Coal:
an uncurated-but-labeled room is coal that players can still polish into a diamond — far
better than a 9-minute frozen table. The async look-ahead worker (clause 10) running
ahead of the party makes Layer-2 degrades rare in practice; the contract guarantees no
freeze even when the party catches the frontier.

**Acceptance-criteria mapping (story 50-26):** AC-1 = this amendment. AC-2 = Layer 1
deadline + Layer 2 guarantee the turn proceeds (no escaped `CurationError` on the
truncated-verdict path). AC-3 = the span taxonomy + `curated=false` uncurated marker.
AC-4 = the explicit 1-retry count AND wall-clock cap, exhaustion → deterministic
Layer 2 (provably non-looping). AC-5 = exercised through the real
`materialize → _stage_curate → _parse_curation_verdict` chain. The implemented
behaviour MUST match this contract exactly; TEA writes RED against it, Dev makes it
GREEN, no improvisation past what is written here.

### Amendment B — Runtime materializer wiring + OTEL reconciliation (2026-05-28, Architect)

**Status:** Reconciles the §Implementation Status snapshot (which is dated
2026-05-16 and predates the keystone wiring) against current
`sidequest-server/`. Does not change clause numbering, frontmatter, or any
supersession relationship. The spec's §10 decomposition table remains the
authoritative live tracker.

A re-audit asserted two gaps: (1) the look-ahead materializer
(`lookahead_worker.py`) is not imported/called from the session dispatch
path, and (2) the mandated `dungeon.materialize.*` OTEL spans are absent.
**Both claims are now FALSE** — the keystone (decomposition item 7 / clause
10 / clause 12) has since landed. The §Implementation Status "Not yet
designed: async look-ahead materializer + frontier-crossing promotion +
wiring + OTEL" bullet is stale and is superseded by this amendment.

**Materializer IS wired into the live session path.** `sidequest/dungeon/`
now carries `lookahead_worker.py`, `session_integration.py`,
`frontier_hook.py`, and `materializer.py`. The session integration is
called from production handlers:

- `sidequest-server/sidequest/handlers/connect.py` imports
  `attach_dungeon_to_session`, and `connect.py` calls it on session
  connect — `session._session_data.lookahead_handle =
  await attach_dungeon_to_session(...)` (null-safe; returns `None` off
  `beneath_sunden`, a no-op for every other pack). `attach_dungeon_to_session`
  invokes `register_lookahead_worker` (`session_integration.py,216`).
- `sidequest-server/sidequest/server/websocket_session_handler.py`
  imports `detach_dungeon_from_session` and `:437` drains the worker handle
  before the final save.
- The movement subsystem consumes the same handle:
  `sidequest/agents/subsystems/movement.py,84,211` thread
  `lookahead_handle` through dispatch.

This satisfies clause 12's "the materializer is invoked from the real
session/frontier-crossing path, not only unit-tested." (Wiring tripwire
test: `tests/dungeon/test_setpiece_attach_wiring.py`, per the server
CLAUDE.md no-source-text-wiring-tests guidance.)

**The `dungeon.materialize.*` span taxonomy EXISTS in the telemetry
registry.** `sidequest-server/sidequest/telemetry/spans/dungeon_materialize.py`
defines context-manager spans for every stage clause 12 mandates:
`dungeon_materialize_span` (`:327`, the parent),
`_design_span` (`:350`), `_fill_span` (`:373`), `_mask_span` (`:389`),
`_curate_span` (`:419`), `_attach_span` (`:486`), `_commit_span` (`:511`),
plus `frontier_expand_span` (`:527`), `frontier_lookahead_span` (`:548`),
`frontier_region_transition_span` (`:571`), and the Amendment A spans
`dungeon_curate_parse_failed_span` (`:435`) /
`dungeon_curate_degraded_span` (`:460`). `materializer.py` imports
and uses them.

**Net status update to §Implementation Status:** the keystone bullet
("async look-ahead materializer + frontier-crossing promotion + wiring +
OTEL — the keystone that makes the stack reachable") has moved from "Not
yet designed" to **shipped/wired.** The data + algorithm layer (already
recorded as shipped) plus the runtime materializer wiring and OTEL
instrumentation are now live. Remaining `partial` scope is what the §10
spec tracker shows beyond this seam (e.g. `beneath_sunden` content
authoring + `caverns_sunden` retirement, item 8); the runtime-reachability
bottleneck the original status called "the project's real bottleneck" is
resolved.
