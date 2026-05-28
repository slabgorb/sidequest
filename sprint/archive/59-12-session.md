---
story_id: 59-12
jira_key: ""
epic: 59
workflow: tdd
---
# Story 59-12: Movement #456 dispatch fix — bind PC onto a live dungeon-graph node (surface->deep handoff)

## Story Details
- **ID:** 59-12
- **Epic:** 59 — Intent Router — Mechanical-Engagement Spine
- **Jira Key:** (none — no Jira integration for this project)
- **Workflow:** tdd
- **Repos:** sidequest-server
- **Branch:** feat/59-12-movement-456-dispatch
- **Stack Parent:** none

## Re-Scope Guidance (2026-05-27 from TEA RED)

This story was parked as BLOCKED (needs repro) on 2026-05-27 from the TEA RED phase. Before proceeding to the RED phase, the following re-scope applies:

1. **AC3 REMOVED** — "Retire 2nd run_dispatch_bank / missing-kwargs TypeError" is REMOVED from this story's charter. It is story 59-11's verbatim responsibility. Do not duplicate: 59-11's description already owns `orchestrator.py:2538`, the TypeError, the 2026-05-25 log line, and Keith-confirmed engineering. AC3 of this story is deleted; use this story to focus on AC1–2 and the blocker.

2. **AC2 RESTATEMENT** — Span names were fictional. AC2 must restate against REAL spans:
   - `frontier.region_transition` (sidequest-server spans/dungeon_materialize.py:571)
   - `movement.resolved` (spans/movement.py:85)
   - OR specify any NEW spans as explicit deliverables.

3. **AC1 BLOCKER** — The binding primitive already exists:
   - `GameSnapshot.seed_pc_regions()` (game/session.py:1085)
   - Auto-seed of seated PCs on any `current_region` patch (`_apply_world_patch_inner`, session.py:1268-1270)
   - `run_movement_dispatch` already handles `no_pc_region` fail-loud (`test_missing_pc_region_fail_loud` passes)
   
   **BLOCKER FOR AC1:** Need a concrete production repro. Which beneath_sunden surface→deep entry path bypasses `seed_pc_regions` so `run_movement_dispatch` fails to resolve? Origin: follow-up bug to PR #456 (movement subsystem). Full evidence: .session/59-12-session.md Delivery Findings (TEA).

   **Movement Phase 1/2/3 just landed** (fbe28ce, 407294a), so the bug may already be fixed — confirm repro or downscope to regression.

## Sm Assessment

Story selected by Operator from the Intent Router epic (59) as the p1 next story. Routing to TEA for RED phase.

**Opening task for TEA (RED):** Confirm or refute the AC1 repro. The binding primitive (`seed_pc_regions`, auto-seed on `current_region` patch, fail-loud `no_pc_region`) already exists, and Movement Phase 1/2/3 landed recently (fbe28ce, 407294a). The first move in RED is to write a failing test for the surface→deep entry path that allegedly bypasses `seed_pc_regions`. Two outcomes:
- **Repro confirmed** → RED test fails as expected; proceed normally to GREEN.
- **No repro** → bug already fixed by Movement Phase 1/2/3; DOWNSCOPE this story to a regression test asserting the surface→deep handoff resolves through `run_movement_dispatch`.

Scope is AC1 (binding) + AC2 (real OTEL spans: `frontier.region_transition`, `movement.resolved`). AC3 is explicitly out — it belongs to 59-11. Do not touch `orchestrator.py:2538` / the double-dispatch TypeError.

No Jira (not configured). Single repo: sidequest-server.

## Context

See `sprint/context/context-story-59-12.md` for full technical guardrails, scope boundaries, and AC context.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-28T13:32:17Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-28T16:30:00Z | 2026-05-28T12:19:57Z | -15003s |
| red | 2026-05-28T12:19:57Z | 2026-05-28T12:43:49Z | 23m 52s |
| green | 2026-05-28T12:43:49Z | 2026-05-28T13:05:03Z | 21m 14s |
| spec-check | 2026-05-28T13:05:03Z | 2026-05-28T13:10:59Z | 5m 56s |
| verify | 2026-05-28T13:10:59Z | 2026-05-28T13:19:57Z | 8m 58s |
| review | 2026-05-28T13:19:57Z | 2026-05-28T13:31:00Z | 11m 3s |
| spec-reconcile | 2026-05-28T13:31:00Z | 2026-05-28T13:32:17Z | 1m 17s |
| finish | 2026-05-28T13:32:17Z | - | - |

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish — **Status:** RED confirmed (2 new tests fail; 21 pre-existing pass; no regressions)

### Repro Verdict: CONFIRMED (not fixed by Movement Phase 1/2/3)

The SM opening task was to confirm or refute the surface→deep repro. It is **real**:

- `beneath_sunden` `cartography.starting_region: ropefoot` — a **surface** region, NOT
  the dungeon graph `entrance` node.
- Fresh session: `init_region_location` (region_init.py:59-65) binds the PC to
  `ropefoot` + seeds `pc_regions["PC"] = "ropefoot"`.
- Dungeon attach (session_integration.py:206) only binds the graph entrance when
  `current_region` is blank — it is `ropefoot`, so **no entrance bind, no re-seed**.
- Per-turn projection (session_helpers.py:652) classifies `ropefoot` as the surface
  lane (case a) → returns None, **no re-seed** (correct — the PC really is on the surface).
- Player descends → `run_movement_dispatch` → `region_for()` returns `ropefoot`
  (passes the `no_pc_region` guard) → `project_region(graph, "ropefoot")` at
  movement.py:134 **raises ValueError** (ropefoot not a graph node).
- Production path: `run_dispatch_bank` (subsystems/__init__.py:259) catches the
  ValueError into an error span and `continue`s — the descent **silently no-ops**.
  Narrator improvises a descent with zero mechanical backing (the Illusionism failure
  OTEL exists to catch).

Movement Phase 2 (fbe28ce) added the handler (assumes the PC is already on a graph
node); Phase 3 (407294a) added per-PC map emit. **Neither added a surface→deep
rebinding seam.** No upstream rebind exists in `intent_router_pass` either.

**Test Files:**
- `tests/agents/subsystems/test_movement_dispatch.py` — added 2 tests (Story 59-12
  section), content-free synthetic fixtures (no live pack), OTEL drive-and-assert.

**Tests Written:** 2 covering AC1 (binding), AC2 (OTEL mechanical-backing), AC4 (wiring).
**Status:** RED — verified failure modes:
- `test_surface_bound_pc_descends_onto_dungeon_graph` → errors `ValueError` at
  region_projection.py:134 (raw repro: project_region raises on the surface region).
- `test_surface_descent_is_mechanically_backed_through_bank` → fails
  `AssertionError: no movement.resolved — descent silently no-opped` (production-faithful
  repro through the real dispatch bank).

Both tests are **design-agnostic**: they assert the descent resolves onto ANY real
graph node + `movement.resolved`/`frontier.region_transition` fire — they do NOT pin
the target node id or a specific new span name (that is the Dev/Architect seam decision).

### Rule Coverage (lang-review/python.md)

| Rule | Test / handling | Status |
|------|-----------------|--------|
| #6 Test quality | Both tests assert specific values (span presence, node membership, attr equality) — no vacuous asserts | covered |
| #9 Async pitfalls | Async handler + bank driven via `asyncio.run` (`_run`), awaited correctly | covered |
| #1 No silent fallbacks | Test B explicitly asserts the descent is NOT a silent no-op (`movement.resolved` MUST fire) | covered |
| #2,#3,#5,#7,#8,#10,#11,#12 | N/A to content-free movement-dispatch tests | n/a |

**Rules checked:** 3 of 3 applicable lang-review rules have test coverage.
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev (Agent Smith) for GREEN — implement the surface→deep binding seam.

## Dev Assessment

**Implementation Complete:** Yes

**Seam decision (resolves TEA's open Question):** The binding lives **inside
`run_movement_dispatch`**, between `load_map` and `project_region`. Both TEA tests
drive the handler (directly + through the bank) with no upstream rebind, so the seam
is handler-level by construction — the context-story Assumptions' lookahead-materialize
seam would not satisfy a direct-handler test. No new span needed: AC2 is covered by the
existing `movement.resolved` (with `resolved_via=surface_descent`) + the per-PC
`frontier.region_transition` the `WorldStatePatch` path already fires.

**Behavior:** When `from_region` is non-empty but not a graph node (a surface
cartography region like `ropefoot`), a descent intent (`direction=="deeper"`) crosses
surface→deep at the dungeon's `entrance` threshold — binds THIS PC there via
`WorldStatePatch(pc_region=...)` and emits `movement.resolved`. A non-descent intent
from the surface fails loud (`surface_no_route`); a corrupt seed with no entrance fails
loud (`no_dungeon_entrance`). No silent fallbacks.

**Files Changed:**
- `sidequest/agents/subsystems/movement.py` — surface→deep handoff block (+71 lines).

**Tests:** 23/23 passing in `test_movement_dispatch.py` (GREEN), including the 2 new
surface→deep tests. Regression sweep `tests/agents/ tests/dungeon/`: 1540 passed, 435
skipped, 1 pre-existing failure (`test_zones_carry_cache_boundary_flag` — backlog story
61-17, fails identically on `develop`, untouched by this change). ruff + pyright clean
on movement.py.

**Branch:** feat/59-12-movement-456-dispatch (pushed)

**Handoff:** To verify phase (The Architect / TEA).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (sound implementation; 2 minor spec-catch-up items)
**Mismatches Found:** 2 (both Minor; recommend Option A — update spec to match the better implementation)

- **Surface descent lands on the graph `entrance`, not a "ropefoot_1_deep" node** (Different behavior — Behavioral, Minor)
  - Spec: context-story AC1 — "the lookahead materializes ropefoot_1_deep; … pc_regions[player_name] is synced to that node."
  - Code: binds the descending PC to `graph.entrance_id` (the always-present Expansion-0 seed node), then later "deeper" turns descend further via the normal depth path.
  - Recommendation: **A — update spec.** Verified `RegionGraph.entrance_id` (region_graph/model.py:92) is the canonical, always-materialized seed; there is no guaranteed `ropefoot_1_deep` node — the context conflated the surface cartography region name with a hypothetical deep node. Binding to the real `entrance` threshold is deterministic and architecturally correct (the dungeon's mouth IS the surface→deep crossing). Dev logged this deviation.

- **AC2 OTEL is the real-span pair, not the literal `frontier_materialization → pc_region_sync → movement.resolved` triple** (Ambiguous spec — Architectural, Minor)
  - Spec: context-story AC2 named an ordered span triple including `pc_region_sync`.
  - Code: emits `movement.resolved` (`resolved_via=surface_descent`) + the per-PC `frontier.region_transition` fired by the `WorldStatePatch(pc_region=...)` path. No new `pc_region_sync` span.
  - Recommendation: **A — update spec.** The SM re-scope already restated AC2 against real spans (`pc_region_sync`/`frontier_materialization` were fictional). Reusing `movement.resolved` + `frontier.region_transition` is the reuse-first choice and gives the GM panel a distinguishable `resolved_via=surface_descent` marker — the Illusionism lie-detector is satisfied without inventing a span. Clean enum extension consistent with existing `resolved_via` values (depth_delta, descriptor_match, bfs_to_exit).

**Architectural notes:** No drift. The fix reuses existing infrastructure end-to-end (the `movement.resolved` span, the `WorldStatePatch` per-PC path, `frontier.region_transition`) — no new components, no new spans, no new modules. The handler-level seam is correct: the surface→deep rebind must precede `region_for`/`project_region`, and `run_movement_dispatch` is the documented single movement mechanism. Fail-loud branches (`surface_no_route`, `no_dungeon_entrance`) honor No Silent Fallbacks.

**Decision:** Proceed to verify (TEA). No hand-back to Dev.

## TEA Assessment (verify)

**Phase:** finish — **Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (movement.py, test_movement_dispatch.py)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | span-attr duplication (high), return-builder (low), test-fixture extraction (med), logger dup (low) |
| simplify-quality | 4 findings | `_ = cand_ids` dead code (high), broad except (med), `_liar` naming (low), private `_materialize_edge` access (med) |
| simplify-efficiency | 4 findings | dual assertion (med), weak span assertion (high), "inline graph rebuild" (high), `_ = cand_ids` (high) |

**Applied:** 1 high-confidence fix
- **Strengthened AC1 span assertion** (efficiency, high): `test_surface_bound_pc_descends_onto_dungeon_graph` asserted only `len(resolved)==1`; added `resolved[0].attributes["resolved_via"]=="surface_descent"` so the test proves the engine took the rebind path, not a coincidental in-graph resolve. Committed `70d03f6`. Re-ran: 23/23 pass.

**Dismissed (in-scope, genuine non-issues):**
- *Span-attr helper extraction* (reuse, high): the proposed helper takes 8 parameters — as complex as the duplication it removes — and would force edits to the well-tested main resolution path. An 8-arg helper is not a simplification. Net-negative; declined.
- *Dual assertion at test:841* (efficiency, med): the two asserts check distinct surfaces — the handler's **return value** (`out.data["to_region"]`) vs the **persisted snapshot** (`pc_regions`). A handler could update one without the other; both are meaningful. Kept.
- *Test-fixture setup helper* (reuse, med): every one of the 21 pre-existing tests in this file inlines its graph/store/snapshot setup. Introducing a setup helper for only the 2 new tests breaks the file's established convention. Consistency wins.
- *"Test 2 rebuilds graph inline"* (efficiency, high): **false** — verified both tests call `_surface_to_deep_graph()` (lines 826, 866). Hallucinated finding.
- *Return-builder / logger-detail consolidation* (reuse, low): trivial boilerplate; not worth an abstraction.

**Deferred (pre-existing code, outside this story's diff):**
- `_ = cand_ids` dead assignment in `_resolve` toward_exit branch (quality+efficiency, high) — real but pre-existing in an unchanged function; bundling it into a movement-binding story is scope creep. Captured as a Delivery Finding for follow-up.
- Broad `except Exception` (quality, med) and private `_materialize_edge` access (quality, med) in `_sync_materialize` — both pre-existing, both intentional with documented `# noqa` rationale (recoverable fail-loud-via-caller; reuse-the-one-worker-path). Not defects.
- `_liar` test-helper naming (quality, low) — pre-existing test, cosmetic.

**Overall:** simplify: applied 1 fix

**Quality Checks:** movement test file 23/23 pass; ruff clean on both changed files; GREEN-phase regression sweep (tests/agents/ + tests/dungeon/) was 1540 passed / 1 pre-existing-unrelated fail.

**Handoff:** To Reviewer (The Merovingian) for code review.

## Delivery Findings

No upstream findings at setup phase.

Agents: append findings below this line. Do not edit other agents' entries.

### TEA (test design)
- **Question** (non-blocking): The surface→deep binding **seam is undetermined**. Two
  spec sources point differently — context-story Assumptions name the lookahead worker
  as the binding seam (materialize-time), while AC1 says the sync happens "BEFORE
  movement.py:118's `region_for()`" (handler-level / just-upstream). Affects
  `sidequest/agents/subsystems/movement.py`, `sidequest/dungeon/lookahead_worker.py`,
  and/or `sidequest/game/session.py` (Dev picks the seam; consult Architect/Neo if the
  two cannot be reconciled). *Found by TEA during test design.*
- **Gap** (non-blocking): AC2's ordered `pc_region_sync` span does not exist yet — only
  `movement.resolved`, `movement.unresolved`, `frontier.region_transition` exist. If the
  rebind is not already observable via `frontier.region_transition` (the per-PC patch
  path), a NEW sync span is an explicit AC2 deliverable. Affects
  `sidequest/telemetry/spans/movement.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): A descriptor-only descent from a surface region
  (`direction=""`, `exit_descriptor` naming a descent like "down the shaft") currently
  returns `surface_no_route` rather than crossing surface→deep — the trigger is
  `direction=="deeper"` only. Affects `sidequest/agents/subsystems/movement.py`
  (broaden the surface→deep trigger to descent-token descriptors if play surfaces it).
  It is a LOUD unresolved, not a crash or silent no-op, so it does not reintroduce the
  bug. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking): Pre-existing dead code in `_resolve` — the
  `toward_exit` branch computes `cand_ids` then discards it via `_ = cand_ids`. Affects
  `sidequest/agents/subsystems/movement.py` (~line 433: remove the unused `cand_ids`
  computation). Flagged high-confidence by two simplify teammates but deferred — it
  predates 59-12 and is outside this story's surface→deep scope. *Found by TEA during
  test verification.*
- No upstream blocking findings during test verification.

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

### Deviation Justifications

5 deviations

- **AC3 not tested (scope removed by session)**
  - Rationale: The session file (higher authority than story context per spec-authority hierarchy) removes AC3 — it is story 59-11's verbatim charter. Testing it here would duplicate 59-11 and require touching out-of-scope code (orchestrator.py:2538).
  - Severity: minor
  - Forward impact: AC3 coverage lives in 59-11; this story's GREEN must NOT touch orchestrator.py:2538.
- **Design-agnostic target assertion (no node-id / span-name pinning)**
  - Rationale: The exact descent target (entrance vs first deep node) and whether a NEW sync span is added are genuine Dev/Architect seam decisions. A node-id-pinned test would box in the design and force churn while still not proving anything stronger than "the crossing is real + mechanically backed."
  - Severity: minor
  - Forward impact: If Dev relocates the binding UPSTREAM of `run_movement_dispatch` (rebind before dispatch), test A (drives the handler directly with surface state) may need to drive `execute_intent_router_pre_narrator_pass` instead — Dev should adjust the test and log a deviation.
- **Surface descent target = dungeon entrance (not a deep node)**
  - Rationale: The entrance is the canonical surface→deep crossing point (the dungeon's mouth) — a tabletop descent from the surface camp arrives at the entrance cavern, then pushes deeper on subsequent turns. Minimal correct semantics; avoids synthesizing materialization for a phantom from_region. The design-agnostic TEA tests assert resolution onto ANY real graph node, which the entrance satisfies.
  - Severity: minor
  - Forward impact: none for the tested contract. A future "dive straight to the bottom" descent that skips the entrance would be a separate enhancement.
- **Surface→deep trigger narrowed to direction=="deeper"**
  - Rationale: Minimalist GREEN — the tests exercise `direction=="deeper"`; a descriptor cannot match a graph edge from a non-graph surface region anyway, and the else-branch fails loud (No Silent Fallbacks), not a crash. Broader descriptor-descent handling deferred (see Delivery Finding).
  - Severity: minor
  - Forward impact: descriptor-only descents from the surface surface a clear "go down" message instead of entering; follow-up may broaden the trigger.
- **AC2 OTEL surface→deep observability uses the real-span pair, not the literal `pc_region_sync` triple**
  - Rationale: The SM re-scope (2026-05-27, in this session) already flagged the AC2 span names as fictional and authorized restatement against real spans OR new spans as explicit deliverables. `pc_region_sync`/`frontier_materialization` do not exist in `sidequest/telemetry/spans/`; the only real spans are `movement.resolved`, `movement.unresolved`, and `frontier.region_transition`. Reusing the existing pair with a distinguishing `resolved_via=surface_descent` attribute satisfies the OTEL lie-detector intent (the GM panel can tell a real surface→deep crossing from narrator improvisation) without inventing an unused span — the reuse-first principle. Verified by `test_surface_descent_is_mechanically_backed_through_bank`, which drives the real bank and asserts both spans fire.
  - Severity: minor
  - Forward impact: none. Any future story that wants an explicit ordered `frontier_materialization → pc_region_sync → movement.resolved` trace (e.g. to distinguish the sync step from the move step on the GM panel) would add those spans as a deliberate enhancement; nothing downstream depends on them today.

## Design Deviations

Agents: append deviations below this line. Do not edit other agents' entries.

### TEA (test design)
- **AC3 not tested (scope removed by session)**
  - Spec source: context-story-59-12.md, AC3
  - Spec text: "AC3 — movement dispatch runs exactly once: No run_dispatch_bank re-run against the redacted package; ... clean Subsystems tab, zero spurious TypeError rows."
  - Implementation: No tests written for AC3 (double-dispatch / run_dispatch_bank retirement / orchestrator.py:2538 TypeError).
  - Rationale: The session file (higher authority than story context per spec-authority hierarchy) removes AC3 — it is story 59-11's verbatim charter. Testing it here would duplicate 59-11 and require touching out-of-scope code (orchestrator.py:2538).
  - Severity: minor
  - Forward impact: AC3 coverage lives in 59-11; this story's GREEN must NOT touch orchestrator.py:2538.
- **Design-agnostic target assertion (no node-id / span-name pinning)**
  - Spec source: context-story-59-12.md, AC1
  - Spec text: "the lookahead materializes ropefoot_1_deep; BEFORE movement.py:118's region_for(), pc_regions[player_name] is synced to that node."
  - Implementation: Tests assert the descent resolves onto ANY real dungeon-graph node (`in graph.nodes`) + `movement.resolved`/`frontier.region_transition` fire, rather than pinning the specific target node id or a specific new span name.
  - Rationale: The exact descent target (entrance vs first deep node) and whether a NEW sync span is added are genuine Dev/Architect seam decisions. A node-id-pinned test would box in the design and force churn while still not proving anything stronger than "the crossing is real + mechanically backed."
  - Severity: minor
  - Forward impact: If Dev relocates the binding UPSTREAM of `run_movement_dispatch` (rebind before dispatch), test A (drives the handler directly with surface state) may need to drive `execute_intent_router_pre_narrator_pass` instead — Dev should adjust the test and log a deviation.

### Dev (implementation)
- **Surface descent target = dungeon entrance (not a deep node)**
  - Spec source: context-story-59-12.md, AC1
  - Spec text: "the lookahead materializes ropefoot_1_deep; BEFORE movement.py:118's region_for(), pc_regions[player_name] is synced to that node."
  - Implementation: The surface→deep handoff binds the descending PC to the dungeon graph `entrance` node (the threshold), NOT to a freshly-materialized deep node (`ropefoot_1_deep`). Later "deeper" turns descend further from the entrance via the normal depth-resolution path.
  - Rationale: The entrance is the canonical surface→deep crossing point (the dungeon's mouth) — a tabletop descent from the surface camp arrives at the entrance cavern, then pushes deeper on subsequent turns. Minimal correct semantics; avoids synthesizing materialization for a phantom from_region. The design-agnostic TEA tests assert resolution onto ANY real graph node, which the entrance satisfies.
  - Severity: minor
  - Forward impact: none for the tested contract. A future "dive straight to the bottom" descent that skips the entrance would be a separate enhancement.
- **Surface→deep trigger narrowed to direction=="deeper"**
  - Spec source: TEA RED tests + context-story-59-12.md AC1
  - Spec text: AC1 surface→deep handoff on descent.
  - Implementation: The handoff fires only when `direction=="deeper"`. A surface PC giving a descent *descriptor* (direction empty) gets a loud `surface_no_route` unresolved.
  - Rationale: Minimalist GREEN — the tests exercise `direction=="deeper"`; a descriptor cannot match a graph edge from a non-graph surface region anyway, and the else-branch fails loud (No Silent Fallbacks), not a crash. Broader descriptor-descent handling deferred (see Delivery Finding).
  - Severity: minor
  - Forward impact: descriptor-only descents from the surface surface a clear "go down" message instead of entering; follow-up may broaden the trigger.

### Reviewer (audit)
- **AC3 not tested (scope removed by session)** → ✓ ACCEPTED by Reviewer: session file is the higher authority; AC3 is 59-11's verbatim charter, correctly excluded.
- **Design-agnostic target assertion (TEA)** → ✓ ACCEPTED by Reviewer: appropriate for RED; the verify-phase strengthening (`resolved_via=="surface_descent"`) tightened it post-implementation.
- **Surface descent target = dungeon entrance (Dev)** → ✓ ACCEPTED by Reviewer: verified `RegionGraph.entrance_id` is the always-present seed; "ropefoot_1_deep" is not a real node. Entrance-as-threshold is the correct, deterministic semantics (agrees with Architect spec-check Option A).
- **Surface→deep trigger narrowed to direction=="deeper" (Dev)** → ✓ ACCEPTED by Reviewer: the non-`deeper` else-branch fails loud (`surface_no_route`), so the narrowing does not reintroduce a silent no-op; descriptor-descent is captured as a non-blocking follow-up finding.
- No undocumented deviations found by Reviewer.

### Architect (reconcile)

**Existing entries verified:** All four logged deviations (TEA ×2, Dev ×2) are accurate and complete — spec sources exist (`context-story-59-12.md` AC1/AC3, both present), quoted spec text matches the document, implementation descriptions match the committed code (`movement.py` binds `graph.entrance_id`; trigger gated on `direction=="deeper"`), and all six fields are populated. No corrections needed.

**AC accountability:** AC1 (PC binding) DONE; AC2 (OTEL mechanical-backing) DONE; AC4 (wiring test) DONE; AC3 (dispatch-runs-once) DESCOPED to story 59-11 by session re-scope (not deferred — no re-verification owed). No deferred ACs.

**Missed deviation added (was documented in the spec-check assessment but lacked a 6-field entry):**

- **AC2 OTEL surface→deep observability uses the real-span pair, not the literal `pc_region_sync` triple**
  - Spec source: `sprint/context/context-story-59-12.md`, AC2
  - Spec text: "OTEL proves ordering (`frontier_materialization` → `pc_region_sync` → `movement.resolved`), all pre-narrator, zero `region_for()` failures."
  - Implementation: The surface→deep path emits `movement.resolved` with `resolved_via="surface_descent"` plus the per-PC `frontier.region_transition` span fired by the `WorldStatePatch(pc_region=...)` path (`movement.py` ~lines 177–191). No `pc_region_sync` span and no `frontier_materialization` span are emitted on this path — the named triple from the spec text is not implemented as written.
  - Rationale: The SM re-scope (2026-05-27, in this session) already flagged the AC2 span names as fictional and authorized restatement against real spans OR new spans as explicit deliverables. `pc_region_sync`/`frontier_materialization` do not exist in `sidequest/telemetry/spans/`; the only real spans are `movement.resolved`, `movement.unresolved`, and `frontier.region_transition`. Reusing the existing pair with a distinguishing `resolved_via=surface_descent` attribute satisfies the OTEL lie-detector intent (the GM panel can tell a real surface→deep crossing from narrator improvisation) without inventing an unused span — the reuse-first principle. Verified by `test_surface_descent_is_mechanically_backed_through_bank`, which drives the real bank and asserts both spans fire.
  - Severity: minor
  - Forward impact: none. Any future story that wants an explicit ordered `frontier_materialization → pc_region_sync → movement.resolved` trace (e.g. to distinguish the sync step from the move step on the GM panel) would add those spans as a deliberate enhancement; nothing downstream depends on them today.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A (GREEN 23/23, ruff+pyright clean, 0 smells) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings (gap covered by my own + rule-checker test analysis) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings (DOC finding raised by me) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | Yes | findings | 2 | confirmed 0, dismissed 2 (both pre-existing/out-of-diff, verified) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (covered by TEA verify simplify fan-out) |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 2 (LOW test-quality), dismissed 1 (HIGH "permanently RED" — empirically refuted) |

**All received:** Yes (3 enabled returned; 6 disabled via `workflow.reviewer_subagents`)
**Total findings:** 2 confirmed (LOW), 3 dismissed (with rationale), 1 my-own MEDIUM + 2 my-own LOW

## Reviewer Assessment

**Verdict:** APPROVED

The surface→deep handoff is a small, correct, well-instrumented fix that reuses existing infrastructure (the `movement.resolved` span, the per-PC `WorldStatePatch` path, `frontier.region_transition`). No Critical or High findings. GREEN 23/23, ruff + pyright clean. The one HIGH-confidence subagent finding was a hypothesis refuted by running the test.

### Observations

- `[VERIFIED]` **Fail-loud doctrine honored** — both new error branches return `_unresolved` with explicit reason codes (`surface_no_route` movement.py:~149, `no_dungeon_entrance` movement.py:~164); no silent fallback, no swallow. Complies with CLAUDE.md No Silent Fallbacks. Confirmed by silent-failure axis (security + rule-checker rule #1/#14: 0 violations).
- `[VERIFIED]` **OTEL lie-detector fires on the new path** — `movement.resolved` (resolved_via=surface_descent) emitted at movement.py:~178 and the per-PC `frontier.region_transition` fires via `apply_world_patch`. Evidence: `test_surface_descent_is_mechanically_backed_through_bank` passes asserting both spans; the pre-existing `test_move_into_committed_neighbor` independently proves `frontier.region_transition` fires from the same patch path without a lookahead handle.
- `[VERIFIED]` **Gate placement correct** — the new block sits after `load_map` and before `project_region`; when `from_region` IS a graph node the block is skipped and the well-tested in-graph path runs unchanged (rule-checker #13: 0 regressions). Binding uses `graph.entrance_id` (the loaded graph's own seed), not a hardcoded constant — more correct.
- `[RULE] [LOW]` **Truthy-only assertions** in `test_surface_descent_is_mechanically_backed_through_bank` — `assert _spans_named(...)` (line ~896) and `assert transitions` (line ~904) check truthiness, not exact count, inconsistent with the AC1 test's `len()==1`. Not vacuous (content asserts follow), but could be tightened. Non-blocking; recommend `>= 1` for consistency.
- `[MEDIUM]` **New fail-loud branches lack direct test coverage** — `surface_no_route` (non-`deeper` from surface) and `no_dungeon_entrance` (corrupt seed) have no dedicated test. Both are correct-by-inspection (return well-tested `_unresolved` machinery), so non-blocking, but `surface_no_route` represents real player behavior (a surface PC saying "go back" / giving a descriptor) and deserves a regression test. Recommended follow-up, not a blocker.
- `[DOC] [LOW]` **Stale "RED today" framing** in the two test docstrings — they describe the pre-fix crash state; now GREEN they read as historical. Reframing to "Regression guard:" would age better. Non-blocking.
- `[LOW]` **`edge_kind="surface_descent"`** (movement.py:~187) is a synthetic non-`RegionExit.kind` value on the span. Security agent rated it "custom but unambiguous"; harmless for the GM panel. Non-blocking.

### Rule Compliance (lang-review/python.md)

| Rule | Applies? | Verdict |
|------|----------|---------|
| 1 Silent exceptions | yes | PASS — no try/except added; both error paths explicit `_unresolved` |
| 2 Mutable defaults | yes | PASS — `_surface_to_deep_graph()` builds fresh; no default args |
| 3 Type annotations | yes | PASS — helper annotated `-> RegionGraph`; handler signature unchanged |
| 4 Logging | yes | PASS — `logger.debug` on success mirrors the in-graph path (movement.py:~322); error path warns via `_unresolved`; lazy `%s` |
| 5 Path handling | no | N/A — no file/path I/O |
| 6 Test quality | yes | PASS w/ 2 LOW nits — 2 truthy-only asserts (above); no vacuous/skip/mock-target issues; strengthened AC1 assertion is exemplary |
| 7 Resource leaks | yes | PASS — `movement_resolved_span` used as `with` context manager |
| 8 Unsafe deserialization | no | N/A |
| 9 Async pitfalls | yes | PASS — new block is sync; no missing await; tests use the established `_run`/asyncio.run helper |
| 10 Import hygiene | yes | PASS — no new imports (WorldStatePatch, movement_resolved_span, DispatchPackage all pre-imported) |
| 11 Input validation | yes | PASS — `entrance_id` is server-constructed graph data; `player_name` from session seat map, not raw action text |
| 12 Dependency hygiene | no | N/A — no manifest changes |
| 13 Fix regressions | yes | PASS — in-graph path untouched; early returns apply no patch |
| No Source-Text Wiring Tests | yes | PASS — tests drive the real handler/bank + assert OTEL spans, no source grep |
| Every suite needs a wiring test | yes | PASS — `test_surface_descent_is_mechanically_backed_through_bank` drives the real `run_dispatch_bank` end-to-end |

### Dismissed Subagent Findings (with evidence)

- `[RULE]` `[HIGH] DISMISSED` — rule-checker #16: "wiring test asserts `frontier.region_transition` but the surface_descent path never fires it → permanently RED." **Refuted empirically:** the test passes (preflight 23/23; I re-ran it isolated alongside `test_move_into_committed_neighbor`). `frontier.region_transition` fires from `notify_region_transition` inside `apply_world_patch` (session.py:1233), independent of `lookahead_handle` — proven by the pre-existing committed-neighbor test using the identical patch path. The subagent reasoned a priori without executing.
- `[SEC]` `[MEDIUM] DISMISSED` — `party_split_after` via `region_for()` may overstate split in MP with an unseeded peer. The subagent itself notes this is "the same pattern as the pre-existing line ~232 success path, not a regression." The new code correctly mirrors the established convention; not introduced here, out of this story's scope.
- `[SEC]` `[LOW] DISMISSED` — possible info-leak if `movement.resolved` watcher events broadcast to player clients. **Verified:** `state_transition` events persist to Postgres for the GM dashboard (watcher_hub.py:~313-328), the GM lie-detector sink per ADR-031/090 — not fanned out to player WebSocket sessions. Targets pre-existing `telemetry/spans/movement.py`, outside this diff.

### Devil's Advocate

Suppose this code is broken. The most dangerous claim is the rule-checker's: that the headline wiring test asserts a span the implementation never emits, so it would pass only by accident or fail forever. If true, the whole "mechanically backed" guarantee is theater. I took this seriously and ran the test in isolation — it passes, and the pre-existing committed-neighbor test proves the same `apply_world_patch` → `notify_region_transition` → `frontier.region_transition` chain fires without any lookahead handle. So the guarantee is real, not accidental.

What would a malicious or confused player do? Stand on the surface and spam "deeper." First descent binds to `entrance`; subsequent ones run the normal in-graph resolver — no infinite rebind, no double-jump (the gate only triggers when `from_region` is off-graph, which is true exactly once). A player who types a creative descent descriptor instead of a coarse "deeper" ("I rappel down the chute") gets `surface_no_route` — a loud, honest "the only way on is down" rather than a crash or a phantom move. That is a worse player experience than entering, but it is *safe* and *honest*, and it is logged as a follow-up. A confused player on a corrupt save (entrance node missing) hits `no_dungeon_entrance` — again loud, no movement into a void.

What about a stressed multiplayer table? If a second PC has never descended (no `pc_regions` entry), `party_split_after` may read `True` on the span even when this move didn't cause the split — but that is a pre-existing telemetry approximation mirrored from the in-graph path, GM-panel-only, and never alters player-visible state or the patch itself. No data corruption, no agency violation (the patch only ever touches THIS PC's region). The real residual risk is the untested fail-loud branches (MEDIUM) — they are correct by inspection but unproven by test, so a future refactor could silently weaken them. That is a coverage debt, not a present defect. Nothing rises to Critical or High.

**Data flow traced:** player action → router → `movement:deeper` dispatch → `run_movement_dispatch` → (off-graph `from_region`) → `WorldStatePatch(pc_region={player: entrance})` → `notify_region_transition` → `frontier.region_transition` span + `movement.resolved` span. Safe: only THIS PC's region mutates; both error branches apply no patch.

**Handoff:** To SM for finish-story.