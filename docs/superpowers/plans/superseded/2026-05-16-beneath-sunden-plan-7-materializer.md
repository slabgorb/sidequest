# Beneath Sünden — Plan 7: Async Look-Ahead Materializer + Frontier-Crossing Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the entire shipped Beneath Sünden generator stack into a real session. Build `sidequest/dungeon/materializer.py` — the async look-ahead worker that, when the party approaches an unexpanded frontier edge, runs the spec §7 pipeline (**design → fill → curate → attach → commit**) and atomically freezes the expansion plus its started threads into the live save, plus the frontier-crossing transition that promotes a look-ahead-materialized expansion to active. This is the keystone: Plans 1–4 + the Content Cookbook are merged pure substrate with **zero non-test runtime consumers**; ADR-106's Consequences section calls that out as the project's real bottleneck. This plan removes it.

**Architecture:** One new module `sidequest/dungeon/materializer.py` orchestrating the five stages against the **already-shipped, stable** public APIs (`region_graph.generate_expansion`/`attach_expansion`/`assign_depth_scores`, `interiors.generate_interior`, `themes.load_theme_palette`/`themes_for_depth`, `cookbook.load_cookbook`/`assemble_region`). The **commit** stage binds to **Plan 5's persistence layer** (`dungeon_map`, `frontier`, mutation overlay, complication ledger) and the **attach** stage step 4 binds to **Plan 6's** set-piece-component-roll / trope-start / quest-seed entry point. Plan 5 and Plan 6 are **hard execution dependencies** — this plan is *designed* now (in parallel with oq-1's in-flight Plan 5) but *executes* only after both land; both bindings are declared as **reconcile-at-execution seams** against the spec §7 contract, the identical honest-deferral stance Plans 2/3/4 took toward "Plan 7's materializer." The async worker is triggered from the **real room-graph region-transition path** (not only unit-tested) per the CLAUDE.md mandatory wiring test; curation is a **one-shot bounded `claude -p` call** (not reactive — `claude -p` cannot call tools mid-generation per ADR-001/098), and a curation failure **fails loudly** (No Silent Fallbacks — never silently ship raw generation stamped as curated). The save is the source of truth: raw design+fill is seed-reproducible, curation deliberately breaks byte-reproducibility, frozen expansions are never regenerated.

## Execution Preamble (read before Task 0)

**This plan does not execute until Plan 5 and Plan 6 are merged.** It is written now so that the moment Plan 5 (persistence, oq-1, in flight) lands and Plan 6 (set-piece/trope/quest-at-attach) lands, execution is unblocked with zero design latency. Writing it now is an Architect design artifact running parallel to oq-1's Plan 5 implementation — it is not a directive to begin coding.

### Cross-workspace ownership (read this twice)

- The **materializer is the oq-1-owned runtime seam** every prior Sünden plan deferred to. Per the established workspace split: oq-2 authors and pushes branches and opens PRs; **oq-1 owns Plan 5, git-sync, merge, and verify.** This plan's *design* is oq-2/Architect; its *execution* is coordinated with oq-1 and gated on Plan 5.
- Do **not** begin Task 1 while Plan 5's persistence API is unmerged. Designing the commit/frontier transaction against a moving target produces rot. The contract this plan binds to is **spec §7's persistence description**, not any in-flight Plan 5 code — bind to the real Plan 5 API at execution and reconcile (Task: Self-Review).

### Scope boundaries (deliberate — NOT omissions; logged so review does not flag them)

- **No persistence schema authored here.** `dungeon_map` / `frontier` / mutation overlay / complication-ledger storage is Plan 5. This plan *calls* Plan 5's commit-transaction primitive; it does not define the save tables.
- **No set-piece roll / trope-start / quest-seed logic here.** That is Plan 6. The attach stage *invokes* Plan 6's entry point and *owns the orchestration around it*; it does not implement component rolling. Plan 6 emits `setpiece.attach` / `trope.start` / `quest.seed` / `ledger.add`; this plan emits `dungeon.materialize.*` and `frontier.expand` and *drives* Plan 6 inside the `attach` span.
- **No new dice/combat mechanics.** Set-piece resolution rides ADR-074 (spec §4). Out of scope.
- **No CR→Edge translation here.** `assemble_region` deliberately ships raw `cr_band` + corpus rows; the CR→Edge / HP→Edge translation is the ADR-014/078 materializer seam. This plan owns that seam — it is **in scope** and called out explicitly in Task 4 (this is the one place the prior plans pointed *here* for; do not skip it or bury it behind a null-check).
- **ADR-055 room-graph movement is `partial`** (per ADR-087: RESTORE, P2; gaps include `tick_on_room_transition` and the deleted MAP_UPDATE wire message). The frontier-crossing hook attaches to the *real* region-transition point; if that movement surface is itself incomplete, that is a **stated dependency and risk** (Task 6), not something this plan papers over with a silent fallback.

## §12 open items resolved here (tunable world-config knobs — reversible)

Spec §12 leaves three knobs "confirm at spec read." Resolved as **world-config defaults**, all tunable per world, none hard-coded:

| §12 item | Decision (default) | Knob | Rationale |
|----------|--------------------|------|-----------|
| Look-ahead breadth | Pre-materialize **the single approaching edge along the party's current heading** | `lookahead_breadth: 1` | Conservative: least wasted LLM curation cost, least surprising. Raise to materialize all near-frontier edges once burst pacing is playtested. |
| Burst magnitude (structural) | `connection_burst` default from §5.1, paired so structural + dramatic spikes land together | `connection_burst` | Spec §5.1/§7.1 — empirical "feels fun," playtest-tuned. |
| Burst magnitude (dramatic) | `threads_lit_per_expansion` paired with `connection_burst` | `threads_lit_per_expansion` | Spec §7.1 — the materializer reads both and passes `burst_magnitude` into `assemble_region` and Plan 6's attach. |

Curation transport (§7 "expected to be LLM-assisted"): **one-shot bounded `claude -p`** propose→curate, never reactive. This is forced by ADR-001/098 (`claude -p` is a one-shot subprocess; it cannot call tools mid-generation — see `project_claude_p_no_reactive_tools`). Generation *proposes* (design+fill+`assemble_region`); a single bounded curation subprocess *selects/refines*; failure raises loudly.

## File Structure

### sidequest-server

| Path | Action | Responsibility |
|------|--------|----------------|
| `sidequest/dungeon/materializer.py` | Create | Five-stage pipeline + async look-ahead worker + frontier tracking + `dungeon.materialize.*`/`frontier.expand` OTEL |
| `sidequest/dungeon/__init__.py` | Edit | Export the materializer public surface |
| `sidequest/game/room_movement.py` (or the real ADR-055 region-transition fn) | Edit | Frontier-approach detection hook → enqueue look-ahead; frontier-crossing → promote-to-active |
| `tests/dungeon/test_materializer.py` | Create | Stage-by-stage unit tests against shipped APIs; Plan 5/6 bindings via their real merged APIs |
| `tests/dungeon/test_materializer_wiring.py` | Create | **Mandatory wiring test** — materializer invoked from the real session/region-transition path, not only unit-tested |

### sidequest-content

None. Theme palette + cookbook content shipped in Plan 4 / Content Cookbook. This plan is server-only.

## Task 0: Branch setup + dependency gate

- [ ] **Hard gate:** confirm Plan 5 (persistence) and Plan 6 (set-piece/trope/quest-at-attach) are **merged** to the server's base branch. If either is unmerged, **stop** — this plan cannot execute. Record the merged-base SHA.
- [ ] Read the **real merged** Plan 5 persistence API and Plan 6 attach entry point. Every seam below says "spec §7 contract"; at execution, bind to the real signatures and note any divergence in Self-Review (do not silently adapt — log it).
- [ ] Branch in `sidequest-server` per `repos.yaml` base.

## Task 1: `MaterializationRequest` + pipeline skeleton (no stages yet)

**TDD intent:** a frozen request value object — `campaign_seed: int`, `expansion_id: int`, `frontier_edge` (the unexpanded edge being approached, from Plan 5's `frontier`), `attach_region_ids: list[str]`, `heading`, `burst_magnitude: int`, `lookahead_breadth: int`. Pure, hashable, no I/O. A `materialize(request, *, graph, bundle, palette, persistence)` coordinator that will call the five stages in order; at this task it raises `NotImplementedError` per stage so the skeleton's control flow and OTEL span nesting are testable before any stage logic exists.

- [ ] Test: request rejects a blank/duplicate `expansion_id`, a `frontier_edge` not in the supplied frontier, and a `burst_magnitude < 1` — loud `ValueError`, no defaults (No Silent Fallbacks).
- [ ] Test: `materialize` opens a parent `dungeon.materialize` span context and the five child spans nest under it in order.

## Task 2: Stage 1 **design** — `region_graph.generate_expansion`

**TDD intent:** the design stage builds the depth-filtered `theme_pool` via `themes.themes_for_depth(palette, depth_score)` (depth_score for a *new* expansion = the frontier edge's spawn `depth_score` from Plan 5's frontier record) and calls the shipped `generate_expansion(*, graph, campaign_seed, expansion_id, attach_region_ids, theme_pool, config=JaquaysConfig(connection_burst=...))`. `ExpansionGenerationError` propagates loudly (do not retry-with-smaller-burst — that is a silent quality degradation). Emit `dungeon.materialize.design` with **`GenerationReport.as_dict()` as the byte-pinned span attribute contract** (the contract Plan 2 pinned for this exact consumer).

- [ ] Test: design returns `(Expansion, GenerationReport)`; the emitted span's attributes equal `report.as_dict()` exactly (key-set pinned).
- [ ] Test: `ExpansionGenerationError` from the generator is not swallowed — it aborts materialization and emits a `dungeon.materialize.design` span carrying the failure (lie-detector visibility), then re-raises.
- [ ] Test: `theme_pool` is depth-filtered — a theme whose band excludes this `depth_score` is absent from the pool passed to `generate_expansion`.

## Task 3: Stage 2 **fill** — `interiors.generate_interior`

**TDD intent:** for each region node in the expansion, resolve its theme's interior algorithm + params (incl. `braid_ratio`) from the palette and call `interiors.generate_interior(algorithm, ...)`. Output conforms to the ADR-055 `rooms.yaml` shape + ADR-096 mask sidecars so room-graph navigation consumes it unchanged (spec §5.2). Emit `dungeon.materialize.fill` with per-region algorithm + grid dimensions + applied `braid_ratio`.

- [ ] Test: every theme class in the expansion maps to its spec §5.2 generator (`cellular`/`depthfirst`/`prim`/`roomcorridor`); an unknown algorithm raises loudly (reuse the generator's own guard — assert it, don't re-implement).
- [ ] Test: a labyrinth-trap theme fills with `braid_ratio=0.0`; a non-trap maze theme with its palette `braid_ratio`. The span records the actually-applied ratio (lie detector: prove it wasn't silently defaulted).

## Task 4: Stage 3 **curate** — one-shot bounded `claude -p` + the CR→Edge seam

**TDD intent:** generation proposes; curation disposes. Build the `RegionContentManifest` via the shipped `cookbook.assemble_region(bundle, *, campaign_seed, expansion_id, depth_score, burst_magnitude, look, is_first_band_entry)` (pure, deterministic). Then a **single bounded `claude -p` curation pass** (spec §7 "pass 1 content, pass 2 creatures") selects/refines to ship-quality. Curation **deliberately breaks byte-reproducibility** and that is recorded — the save, not the seed, is truth. **This task owns the CR→Edge / HP→Edge translation seam** (ADR-014/078): `assemble_region` ships raw `cr_band` + corpus rows by contract; the materializer is the documented place that translation happens. Do it here, end-to-end, owned — **not** behind a per-call null guard (see `feedback_no_burying_bombs`; gaslight the narrator via materialized snapshot per `world_materialization._apply_npc()` precedent).

- [ ] Test: `assemble_region` is called with exactly the named signal kwargs; manifest is deterministic for identical inputs (pre-curation determinism contract holds *up to* this seam).
- [ ] Test: a curation subprocess failure (non-zero exit / unparseable) **raises loudly** and aborts the transaction — it does **not** fall back to shipping the raw manifest stamped curated. Span `dungeon.materialize.curate` records `curated=false, reason=...` on the failure path.
- [ ] Test: every corpus creature crossing this seam emerges with an Edge value (ADR-014 requires HP→Edge at materialization) — no raw HP/CR leaks into the committed snapshot.

## Task 5: Stage 4 **attach** — depth + the Plan 6 seam

**TDD intent:** `region_graph.attach_expansion(graph, exp)` (mutates + re-verifies global connected+loopful, raises loudly), then `region_graph.assign_depth_scores(...)` (entrance exactly `0.0`, ordinary-route distance, **frozen — never recomputed**, spec §7). Emit `dungeon.materialize.attach` with **`DepthReport.as_dict()` as the byte-pinned span contract** (pinned by Plan 3 for exactly this consumer). Then invoke **Plan 6's** set-piece-component-roll / trope-start / quest-seed entry point (passes `burst_magnitude` → `threads_lit_per_expansion`). Plan 6 emits `setpiece.attach`/`trope.start`/`quest.seed`/`ledger.add` *inside* this `attach` span; this plan owns the span and the ordering, Plan 6 owns the thread logic.

- [ ] Test: the `attach` span attributes equal `DepthReport.as_dict()` exactly; entrance region depth is `0.0`; a pre-existing scored region is **not** recomputed (freeze holds).
- [ ] Test (binds to Plan 6's merged API): started trope/quest threads from this expansion land in the open-complication ledger with origin region + status; thread count scales with `burst_magnitude`.
- [ ] Test: `attach_expansion`'s loud global-invariant failure aborts the whole materialization (no partial commit).

## Task 6: Stage 5 **commit** — one transaction + frontier promotion (the wiring seam)

**TDD intent:** the whole materialized expansion **plus its started threads** is written to the live save in **one Plan 5 transaction** (`dungeon_map` nodes/edges/masks/setpiece-states + per-region generator-version stamp, `frontier` updated with the new unexpanded edges, complication ledger appended). On commit it is *immediately live*. Emit `dungeon.materialize.commit` and `frontier.expand`. The **frontier-crossing transition**: when the party crosses into a look-ahead-materialized expansion, promote it to active — this hook lives in the **real ADR-055 region-transition path** (`room_movement` / the real region-transition fn that updates `snap.current_region`), extending ADR-055 init, **not** a parallel navigation path.

- [ ] Test: commit is atomic — an injected failure mid-write leaves the save unchanged (no half-attached expansion, no orphan ledger rows). Binds to Plan 5's transaction primitive.
- [ ] Test: a generator-version bump does not regenerate a frozen region; only never-materialized expansions use new code (spec §7).
- [ ] **MANDATORY WIRING TEST** (`test_materializer_wiring.py`, CLAUDE.md "Every Test Suite Needs a Wiring Test"): drive the **real session region-transition** (the actual `room_movement`/region-transition entry point that production uses, with a real `GameSnapshot`) toward an unexpanded frontier edge and assert the materializer's look-ahead was **invoked from that production path** — not called directly by the test. If the ADR-055 movement surface is too partial to host this hook, **stop and report it** as the stated Task-6 dependency risk; do not stub a fake transition to make the test pass (No Stubbing).

## Task 7: Async look-ahead worker

**TDD intent:** the pipeline runs *ahead of the party* asynchronously when the frontier-approach signal fires; `lookahead_breadth` controls how many edges along the heading. The committed expansion becomes live atomically (Task 6). The worker must not race the session transaction — serialize commit through Plan 5's transaction primitive; a second approach signal for an already-in-flight `expansion_id` is a no-op (idempotent, not a double-materialize).

- [ ] Test: two rapid approach signals for the same frontier edge → exactly one materialization (idempotency span attribute proves the dedupe, lie detector).
- [ ] Test: `lookahead_breadth=1` materializes only the heading edge; raising it materializes the near-frontier set; default is `1`.
- [ ] Test: worker exception surfaces (loud) and emits a terminal `dungeon.materialize.*` span — a background failure is never silently swallowed (the GM panel must see the dungeon failed to grow).

## Task 8: Full-suite gate + honest-deferral / as-built docs

- [ ] Full server suite green; ruff + pyright clean on `materializer.py` and both test files.
- [ ] `materializer.py` module docstring states: the runtime consumer the entire Plan 1–6 stack deferred to is **this module**; the Plan 5 (persistence transaction) and Plan 6 (attach internals) bindings, the byte-pinned span contracts consumed (`GenerationReport.as_dict()` → design, `DepthReport.as_dict()` → attach), and the curation-failure-is-loud / save-is-truth contracts.
- [ ] **Post-Implementation Corrections** section appended (code is authoritative) recording any divergence between the spec §7 contract this plan was written against and the **real merged** Plan 5/6 APIs — explicit reconcile, the Plan 2/3/4 precedent.
- [ ] Update spec §10 decomposition item 7 status (the live tracker — not ADR-106's body).

## Self-Review

- [ ] No silent fallback anywhere: design failure, curation failure, attach invariant failure, commit failure all raise loudly and leave an OTEL trail.
- [ ] No stub: if Plan 5/6 are not merged, the plan **did not run** (Task 0 gate) — it was not executed against fakes.
- [ ] The CR→Edge seam (Task 4) is owned end-to-end, not null-guarded per call.
- [ ] The wiring test exercises the **production** transition path, not a test-only call.
- [ ] Determinism contract honored: raw design+fill seed-reproducible; curation breaks it intentionally; frozen regions never regenerated.
- [ ] Every spec §8 OTEL span present and attributed; `dungeon.materialize.*` + `frontier.expand` owned here, Plan 6 spans driven inside the `attach` span.

## Execution Handoff

Designed by Architect (oq-2) on 2026-05-16, in parallel with oq-1's in-flight Plan 5. **Execution is gated on Plan 5 + Plan 6 merge** and coordinated with oq-1 (Plan 5 + git-sync/merge/verify owner). Do not begin Task 1 before the Task 0 gate passes.

## Post-Implementation Corrections (as-built — CODE IS AUTHORITATIVE)

_To be filled at execution. Record every divergence from the spec §7 contract this plan was written against versus the real merged Plan 5/6 APIs; reconcile to as-built if the plan is re-run._
