---
parent: context-epic-59.md
workflow: tdd
---

# Story 59-12: Movement #456 dispatch fix — bind PC onto a live dungeon-graph node (surface→deep handoff)

## Business Context

This story fixes the production movement dispatch path so a PC can actually descend
from a surface region into a procedurally-generated dungeon deep (beneath_sunden /
Sünden Deep per ADR-106). Today, `run_movement_dispatch` can't resolve a surface→deep
move because the PC is never bound to the just-materialized dungeon-graph node, so
`region_for()` returns empty and the move silently no-ops. For the playgroup this is
the difference between "I go deeper" advancing the crawl versus the narrator improvising
a descent with zero mechanical backing — exactly the Illusionism failure OTEL exists to
catch. Movement is the foundational agency primitive for dungeon crawls; this unblocks
the rest of Epic 59's mechanical-engagement spine (ADR-113) on the traversal axis.

## Technical Guardrails

**Key files:**
- `sidequest-server/sidequest/agents/subsystems/movement.py` (lines 77–266) — dispatch
  handler; `region_for(perspective=player_name)` at ~line 118 is the failing lookup.
- `sidequest-server/sidequest/dungeon/lookahead_worker.py` — edge-materialization seam;
  needs the new PC-binding hook to fire when a frontier node goes live.
- `sidequest-server/sidequest/agents/orchestrator.py:2538` — the redundant second
  `run_dispatch_bank` call implicated in the double-dispatch missing-kwargs error.
- PC region sync: a **new** helper (binding logic) — likely `game/session.py` or
  `dungeon/persistence.py`. Do not stub it; wire it into the materialize seam.
- Test: `tests/agents/subsystems/test_movement_dispatch.py` (21 existing tests; add the
  surface→deep wiring test alongside).

**Patterns to follow:**
- No silent fallbacks (CLAUDE.md): the binding must happen at the seam, not be patched
  with a per-site null guard ([[feedback_no_burying_bombs]]).
- PC advance goes through `WorldStatePatch(pc_region={player_name: target_id})`.
- Every subsystem decision emits OTEL — `movement.resolved` vs `movement.unresolved`,
  plus ordered `frontier_materialization` → `pc_region_sync` → `movement.resolved`
  spans in the pre-narrator pass. The GM panel is the lie detector.
- HP→Edge / materialization doctrine ([[project_narrator_gaslighting_doctrine]]) — bind
  via game state, not narration text.

## Scope Boundaries

**In scope:**
- New PC-region-sync helper that binds `pc_regions[player_name]` to a just-materialized
  dungeon node, hooked into the lookahead materialization seam.
- Surface→deep movement dispatch resolves; correct OTEL span ordering, pre-narrator pass.
- Fix the double-dispatch missing-kwargs error so movement dispatch runs exactly once
  per turn with no spurious TypeError rows in the Subsystems tab.
- Wiring test proving the sync is actually called (not stubbed) and movement resolves.

**Out of scope:**
- The full 59-11 redesign of directive collection (engage-once / collect-without-side-
  effects). See the coordination note under Assumptions — AC3's "retire the second
  `run_dispatch_bank`" touches 59-11's charter; this story should do the minimum needed
  to make movement dispatch run once cleanly, not absorb 59-11.
- Procedural dungeon generation itself (ADR-106 engine) — the deep is unmapped by design
  ([[project_beneath_sunden_unmapped_deep]]); this story consumes materialized nodes,
  it does not author them.

## AC Context

- **AC1 — PC binding on surface→deep transition:** With a PC at
  `caverns_and_claudes/beneath_sunden/entrance` and the router dispatching
  `movement:deeper`, the lookahead materializes `ropefoot_1_deep`; BEFORE
  movement.py:118's `region_for()`, `pc_regions[player_name]` is synced to that node.
  Pass = `movement.resolved` span fires (not `unresolved`) and the PC advances via the
  `WorldStatePatch` path. Edge: target node materialized this turn vs already-live.
- **AC2 — sync wired into the materialize seam:** Trace must show lookahead materializes
  an edge → PC-binding sync → pc_regions updated → movement dispatch sees the binding.
  OTEL proves ordering (`frontier_materialization` → `pc_region_sync` →
  `movement.resolved`), all pre-narrator, zero `region_for()` failures.
- **AC3 — movement dispatch runs exactly once:** No `run_dispatch_bank` re-run against
  the redacted package; subsystem_exercise spans fire once per subsystem per turn; clean
  Subsystems tab, zero spurious TypeError rows. (Coordinate with 59-11 — see Assumptions.)
- **AC4 — wiring test (CLAUDE.md):** Synthetic fixture PC at beneath_sunden entrance +
  router-dispatched deeper → seam binds PC → movement resolves. Assert `movement.resolved`
  + `pc_regions[player_name] == materialized_node_id`. Mock the sync, assert it was called
  with correct player_name and target node (proves wiring, not stubbing).

## Assumptions

- **59-11 overlap:** AC3 ("retire the second `run_dispatch_bank` call") overlaps story
  59-11 ("Retire the orchestrator's redundant second dispatch-bank run"). Assumption:
  59-12 does the minimum to make movement dispatch run once cleanly; the full directive-
  collection redesign stays in 59-11. **If TEA/Dev find the two cannot be separated, log
  a Design Deviation and notify SM** — we may need to re-sequence or merge scope.
- The lookahead worker is the correct seam for the binding (per session root-cause
  analysis); the materialization path does not already sync pc_regions elsewhere.
- The double-dispatch error is the pre-59-4 leftover described in PR #448's watcher catch
  (non-fatal today), not a new regression.
- Test fixtures must not point at a way that couples tests to live content beyond the
  intended beneath_sunden surface→deep path ([[feedback_tests_not_point_at_content]]).
