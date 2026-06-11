---
story_id: "104-2"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 104-2: M-B — Single-system worlds collapse to orrery-as-Map; isCluster reads server flag not regionCount

## TEA Assessment

**Tests Required:** Yes
**Reason:** UI behavior change — cluster detection moves from a client `regionCount > 1` heuristic to the server `cartography.is_cluster` flag (104-1 / M-A).

**Test Files:**
- `sidequest-ui/src/components/GameBoard/widgets/__tests__/MapWidget.clusterFlag.test.tsx` (new) — the M-B contract: flag-driven cluster routing, incl. the two divergence cases where flag and node count disagree.
- `sidequest-ui/src/components/GameBoard/widgets/__tests__/MapWidget.twoScale.test.tsx` (fixtures updated) — carried `is_cluster` so the existing ADR-141 suite pins the new contract and stays green across Dev's change.

**Tests Written:** 8 new tests covering 4 ACs (5 RED divergence/collapse, 3 green regression guards).
**Status:** RED (5 failing — verified via vitest, behavioral failures not compile errors)

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 — isCluster reads flag not regionCount | `multi-region single-system … does NOT render the cluster graph`; `single-region cluster … renders the cluster graph, not the orrery`; `does not eagerly fetch … single-region cluster` | failing (RED) |
| AC2 — single-system → orrery-as-Map, regression coyote/aureate | `coyote_star … collapses to the orrery, fetched eagerly`; `aureate_span … collapses to orrery` | coyote failing (RED); aureate green guard |
| AC3 — cluster (perseus) unchanged: graph default + drill | `perseus_cloud … defaults to the campaign graph`; `perseus_cloud drill … still reaches the orrery` | green (regression guard) |
| AC4 — single-system multi-region fixture: no cluster graph + no drill + orrery direct | `AC4: single-system multi-region fixture asserts no cluster graph + no drill + orrery direct` | failing (RED) |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (flag authoritative both directions) | `single-region cluster (1 node, is_cluster:true) renders the cluster graph` | failing (RED) — forbids a `regionCount` fallback |
| Wiring test (real component render, not mock) | all 8 render the real `MapWidget` and assert real `CartographyMap`/`OrbitalChartView` testids | n/a (live) |

**Self-check:** No vacuous assertions — every test asserts presence AND absence of specific testids, or a concrete `sendOrbitalIntent` call/no-call; the divergence pair proves the flag is read in both directions (a count-based fix cannot pass both).

**Handoff:** To Dev (Inigo) for GREEN. Start with the blocking finding — add `is_cluster?: boolean` to `CartographyMetadata` (MapOverlay.tsx:84), then change `MapWidget.tsx:97` to read the flag (no fallback).

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/MapOverlay.tsx` — added optional `is_cluster?: boolean` to `CartographyMetadata` (the 104-1/M-A server flag).
- `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` — `isCluster` now reads `mapData?.cartography?.is_cluster ?? false` instead of `regionCount > 1`; removed the dead `regionCount` local; refreshed the stale ADR-141 JSDoc.
- `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-map-orbital-error.test.tsx` — added `is_cluster: true` to the `CLUSTER_MAP` fixture (contract alignment TEA missed).

**Tests:** Full UI suite GREEN — 2093/2093 passing (was RED: 5 failing). Typecheck (`tsc --noEmit`) clean; ESLint clean on changed files.
**Branch:** feat/104-2-single-system-collapse-orrery (pushed)

**AC verification:**
- AC1 — `isCluster` reads the flag, not regionCount (both divergence directions pass).
- AC2 — coyote_star/aureate_span (is_cluster:false) collapse to orrery-as-Map.
- AC3 — perseus_cloud (is_cluster:true) unchanged: campaign graph default + drill.
- AC4 — single-system multi-region fixture: no cluster graph + no drill + orrery direct.

**Handoff:** To Reviewer (Westley) for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (pre-existing lint warning) | confirmed 0, dismissed 1 (not a regression — App.tsx:1573 exists verbatim on develop, outside this diff), deferred 0 |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([EDGE]) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SILENT]) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([TEST]) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([DOC]) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([TYPE]) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SEC]) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SIMPLE]) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([RULE]) |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` and assessed directly by Reviewer)
**Total findings:** 0 confirmed blocking, 1 dismissed (pre-existing lint, with rationale), 2 LOW observations noted

### Rule Compliance

Rules sourced from `CLAUDE.md` (sidequest-ui + orchestrator) and `SOUL.md`. Enumerated against every changed symbol.

| Rule | Governed symbols in diff | Verdict |
|------|--------------------------|---------|
| **No Silent Fallbacks** | `isCluster = mapData?.cartography?.is_cluster ?? false` (MapWidget.tsx:102) | COMPLIANT — `?? false` covers only the cartography-*absent* case (room-graph/non-orbital worlds, which are definitionally not clusters), not a masked config error. The server guarantees a concrete bool whenever cartography is present (session_helpers.py:1483). One residual noted as [SILENT] LOW. |
| **No Stubbing** | all changed symbols | COMPLIANT — no stubs/placeholders; real behavior wired end-to-end. |
| **Don't Reinvent — Wire Up What Exists** | the orrery-collapse branch (MapWidget.tsx:204) | COMPLIANT — reused the verified #748 collapse branch; only the detection input changed. Dead `regionCount` removed. |
| **Verify Wiring, Not Just Existence** | `is_cluster` field + read site | COMPLIANT — server sets it (session_helpers.py:1483, nested in `cartography`), wire→`MapState`→`MapWidget` consumes it; tests render the real component + real `CartographyMap`/`OrbitalChartView`. |
| **Every Test Suite Needs a Wiring Test** | clusterFlag.test.tsx | COMPLIANT — all 8 tests mount the real `MapWidget` (no mocked children); the AC3 cases assert the real cluster-graph + drill path. |
| **Delete Dead Code in same PR** | `regionCount` local | COMPLIANT — removed in the same change. |
| **OTEL Observability** | UI routing change | NOT APPLICABLE — the cluster *decision* is a server subsystem (M-A emits `cluster_detected_span`); the UI is a pure consumer/display. CLAUDE.md: OTEL "not needed for cosmetic UI changes." |

## Reviewer Assessment

**Verdict:** APPROVED

**Observations (8, ≥5 required):**

1. `[VERIFIED]` **Core flag read is correct end-to-end** — `MapWidget.tsx:102` reads `mapData?.cartography?.is_cluster`; the server writes `is_cluster` *inside* the `cartography` dict at `sidequest-server/.../session_helpers.py:1483` ("always a concrete bool on the wire"). Read site and write site agree on nesting and name. AC1 divergence tests pass in both directions (flag true @ 1 region → graph; flag false @ 8 regions → orrery).
2. `[SILENT]` **`?? false` is a bounded, correct default, not a swallowed error** — evidence: `cartography` is optional on `MapState` (MapOverlay.tsx:97), so the read needs a default regardless; the default only triggers for cartography-absent worlds (room-graph/non-orbital), which are correctly not clusters. **LOW residual:** if the server ever emitted a cartography object *without* `is_cluster` (contract violation), the UI would silently treat it as single-system rather than warn. Non-blocking — the server contract guarantees presence and the old code had no fail-loud here either. Noted as a delivery finding for a possible future dev-mode warn.
3. `[EDGE]` **Edge cases enumerated** — (a) 1-region `is_cluster:true` → branch 137 renders `CartographyMap` with one node (test-proven). (b) 8-region `is_cluster:false` → skips both cluster branches, `orbitalEnabled` true, branch 204 orrery (test-proven). (c) empty `regions {}` + `is_cluster:false` → orrery (existing twoScale test green). (d) theoretical `is_cluster:true` + empty `regions` → MapOverlay header, `showRegionGraph` false, no graph — a degenerate the server never emits (a cluster has regions); behavior differs from old code only for this impossible input. No real-world break.
4. `[TYPE]` **Optional vs required `is_cluster` is the right call** — evidence: `grep` shows no production code constructs a `CartographyMetadata` literal (wire JSON is cast at the boundary), so a required field would only churn 4 unrelated overlay-rendering test files. `tsc --noEmit` clean. Optional is consistent with the already-optional `cartography`.
5. `[DOC]` **Stale comments fixed, not left to rot** — the prop JSDoc (MapWidget.tsx:16-22) and routing doc (47-62) previously asserted the retired "≤1 region node = single" rule; both now describe the flag. The new inline comment (91-101) is accurate and cites the falsifier (coyote_star's 8 bodies).
6. `[TEST]` **Tests are non-vacuous and bidirectional** — every test asserts presence AND absence of specific testids, or a concrete `sendOrbitalIntent` call/no-call. The divergence pair (flag true @ low count / flag false @ high count) cannot both pass under any count-based implementation, so it genuinely pins the contract. The 3 green-before-and-after cases are honest regression guards, labeled as such.
7. `[SIMPLE]` **Minimal change, no over-engineering** — one expression replaced a 4-line block; dead `regionCount` removed; downstream branches untouched (the collapse path auto-fires once `isCluster` flips). No new abstractions.
8. `[SEC]` `[RULE]` **No security surface; rules satisfied** — this is display routing with no auth/input/tenant dimension. OTEL is correctly server-side (M-A's `cluster_detected_span`); CLAUDE.md exempts cosmetic UI from OTEL. No `dangerouslySetInnerHTML`, no secrets, no injection path (preflight: 0 smells).

**Data flow traced:** server world load → `detect_is_cluster(world_path)` caches `World.is_cluster` → `CartographyMapMessage.cartography.is_cluster` (session_helpers.py:1483) → WS → `MapState.cartography` → `MapWidget` `isCluster` → branch selection (cluster graph vs orrery-as-Map). Safe: pure boolean routing, no mutation.

**Pattern observed:** consume-the-server-flag, don't recompute client-side (MapWidget.tsx:102) — the same correction direction as ADR-140 (genre/world as source of truth). Good.

**Error handling:** absent cartography → not a cluster (correct); absent chart → loading state (unchanged); orbital error → no-local-chart state (unchanged, twoScale AC5 green).

**Handoff:** To SM for finish-story.

### Devil's Advocate

Let me argue this code is broken. **First attack — the optional type is a lie.** The JSDoc on `is_cluster` says "when cartography is present the server always sets it," but TypeScript marks it optional, so nothing *enforces* that. A future server refactor that drops the field from one code path would not break compilation; it would silently route a real cluster (perseus_cloud) to the single-system orrery, and the player would lose the campaign graph and the ability to drill — a real, player-visible regression with no error, no log, no OTEL on the client. The `?? false` is precisely the kind of "silently default" the project's No-Silent-Fallbacks rule was written to forbid. **Rebuttal:** the decision authority is the server (M-A), which *does* emit `cluster_detected_span` — the GM panel is the lie detector for the actual decision, exactly as doctrine wants; the client is a dumb consumer and a client-side warn would be belt-and-suspenders, not a requirement. Still, I log it as a non-blocking finding. **Second attack — the empty-regions cluster.** If the server sends `is_cluster:true` with `regions:{}`, branch 137 renders `MapOverlay`, whose `showRegionGraph` guard (regions.length>0) is false, yielding a header with neither a graph nor an orrery nor a drill — a dead-end Map. The old node-count code would have shown the orrery instead. **Rebuttal:** a cluster by definition has ≥2 systems and therefore region nodes; the server never emits this shape, and M-A's detection is system-count-based with the regions populated from the same cartography. Theoretical only. **Third attack — confused author.** Someone reading "single-system" might think it means "one region" and re-introduce a region-count guard on the collapse branch, breaking coyote_star again. **Rebuttal:** the new comments explicitly call out "even with many region nodes, all bodies of one orrery" and the clusterFlag tests would immediately fail. The guardrails are in place. None of these attacks land as blocking; the worst is a LOW hardening suggestion. Verdict stands.

## Story Details
- **ID:** 104-2
- **Jira Key:** (none — no Jira integration)
- **Workflow:** tdd
- **Repos:** ui
- **Stack Parent:** 104-1 (already merged into server develop)
- **Branch Strategy:** gitflow (feat/104-2-single-system-collapse-orrery)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-11T10:32:25Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-11T10:10:52Z | 2026-06-11T10:22:52Z | 12m |
| green | 2026-06-11T10:22:52Z | 2026-06-11T10:27:55Z | 5m 3s |
| review | 2026-06-11T10:27:55Z | 2026-06-11T10:32:25Z | 4m 30s |
| finish | 2026-06-11T10:32:25Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Reviewer (code review)
- **Improvement** (non-blocking): the client silently defaults a cartography-present-but-`is_cluster`-missing payload to single-system (`?? false`). Affects `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx:102` (optional — a dev-mode `console.warn` when `cartography` is present but `is_cluster === undefined` would surface a future server contract regression; not required, the server guarantees presence and emits `cluster_detected_span` server-side). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): pre-existing ESLint warning at `sidequest-ui/src/App.tsx:1573` (`react-hooks/exhaustive-deps`, unnecessary `currentRound` dep) exists verbatim on `develop` and will trip `client-lint --max-warnings=0` independent of this story. Affects `sidequest-ui/src/App.tsx` (unrelated cleanup). *Found by Reviewer during code review (preflight).*

### Dev (implementation)
- **Resolution** (non-blocking): The TEA blocking Gap (is_cluster not on the type) is RESOLVED — added optional `is_cluster?: boolean` to `CartographyMetadata`. Affects `sidequest-ui/src/components/MapOverlay.tsx` (done). Chose optional over required because no production code constructs a `CartographyMetadata` literal (the wire JSON is cast at the boundary; the server always sets it) and `cartography` is already optional on `MapState` — a required field would have forced edits to 4 unrelated test files that test overlay rendering, not cluster routing. *Found by Dev during implementation.*
- **Improvement** (non-blocking): TEA's fixture-alignment was one file short — `GameBoard-map-orbital-error.test.tsx`'s `CLUSTER_MAP` (a perseus-shaped cluster fixture) also omitted `is_cluster`, so it flipped to the orrery under the flag and failed. Affects `sidequest-ui/src/components/GameBoard/__tests__/GameBoard-map-orbital-error.test.tsx` (added `is_cluster: true` — handled). The MapWidget unit/MapOverlay/shared-map fixtures were single/non-cluster and correctly read `is_cluster` undefined → false, so they needed no change. *Found by Dev during implementation.*

### TEA (test design)
- **Gap** (blocking): `is_cluster` is not on the `CartographyMetadata` type. Affects `sidequest-ui/src/components/MapOverlay.tsx:84` (add `is_cluster?: boolean` — the server always sends it on the wire, so a required `boolean` is also defensible; either way the typecheck/build gate fails until the field exists). The new RED tests reference `mapData.cartography.is_cluster`; vitest (esbuild) runs them without typechecking, so they fail on behavior at RED, but `client-build`/lint will error until Dev adds the field. *Found by TEA during test design.*
- **Improvement** (non-blocking): only `MapWidget.tsx:97` needs to change — once `isCluster` reads the flag, a single-system world (e.g. coyote_star, 8 regions, `is_cluster:false`) makes `isCluster=false`, both cluster branches (`:137`, `:151`) are skipped, `orbitalEnabled` becomes true, and the existing orrery-collapse branch (`:204`) fires unchanged. No second edit to the `:204` gate is required. Affects `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` (read `mapData?.cartography?.is_cluster` instead of `regionCount > 1`; do NOT add a `regionCount` fallback — No Silent Fallbacks, and M-A AC4). *Found by TEA during test design.*
- **Improvement** (non-blocking): the stale JSDoc on `MapWidget.tsx:20-21,49-59,84-93` still describes the retired "≤1 region node = single / no new world-level flag" ADR-141 heuristic. Affects `sidequest-ui/src/components/GameBoard/widgets/MapWidget.tsx` (update the comments to the flag-driven contract when wiring). *Found by TEA during test design.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. Followed TEA's recommended option (optional `is_cluster?: boolean`); read the flag with `?? false` only to cover the cartography-absent case (room-graph/non-orbital worlds are not clusters), not as a regionCount fallback — the flag remains authoritative when cartography is present. Also updated the stale ADR-141 JSDoc on MapWidget.tsx (TEA non-blocking improvement) and removed the now-dead `regionCount` local.

### TEA (test design)
- **Modified pre-existing twoScale fixtures to carry the `is_cluster` flag**
  - Spec source: context-story-104-2.md, AC1 + spec §2/§5 (M-A flag supersedes the `regionCount>1` heuristic)
  - Spec text: "isCluster reads the flag, not regionCount"; M-A: "Supersedes the client `regionCount > 1` heuristic — the flag is authoritative."
  - Implementation: Added `is_cluster: true` to `clusterMapState()`, `is_cluster: false` to `singleSystemMapState()` and the empty-cartography fixture in `MapWidget.twoScale.test.tsx`. These fixtures previously omitted the field and would have flipped to "pre-existing failures" once Dev keys cluster on the flag (clusterMapState has 3 regions but no flag → falsy → would render orrery, breaking AC1/AC2/AC3/AC5). The fixtures now pin the new flag-driven contract and stay green before and after Dev's change.
  - Rationale: Avoids the ADR-112/test_60_6 trap — a contract change that silently breaks a pre-existing test pinning the old invariant. Updating the fixture to the new contract is test-design work, not a Dev fix.
  - Severity: minor
  - Forward impact: none — fixtures match the real wire shape (server always sends `is_cluster` on the cartography payload, session_helpers.py:1483).
- **No other deviations from spec.** All four ACs have coverage; the AC3 "unchanged" cases are green-before-and-after regression guards, not RED.

### Reviewer (audit)
- **TEA — modified pre-existing twoScale fixtures to carry `is_cluster`** → ✓ ACCEPTED by Reviewer: correct test-design call; the fixtures now match the real wire shape (server always sends the flag) and avoid the ADR-112/test_60_6 false-"pre-existing-failure" trap. Verified the fixtures stay green before and after the Dev change.
- **Dev — optional `is_cluster?: boolean` (followed TEA's recommended option)** → ✓ ACCEPTED by Reviewer: no production code constructs the literal; required would only churn 4 unrelated overlay tests. `tsc` clean. The `?? false` covers cartography-absent worlds, not the flag itself — consistent with the already-optional `cartography`.
- **Dev — also aligned `GameBoard-map-orbital-error.test.tsx` `CLUSTER_MAP` fixture (not in TEA's list)** → ✓ ACCEPTED by Reviewer: same necessary contract alignment as the twoScale fixtures; without it the cluster fixture flipped to single under the flag. Correctly handled, full suite green.
- No undocumented deviations found. The diff matches the logged scope exactly (1 type field + 1 expression + comment refresh + fixture alignment).
## Impact Summary

**Status:** Preflight Ready

**Core Change:** Client cluster detection migrates from local heuristic (`regionCount > 1`) to server-authoritative flag (`cartography.is_cluster`). Enables single-system worlds with multiple regions (e.g., coyote_star with 8 bodies) to render as orrery-as-Map instead of clustered campaign graph.

**Delivery Findings Analysis:**
- **Blocking issues:** 0 (all TEA/Dev/Reviewer findings resolved during implementation)
- **Non-blocking observations:** 2
  1. Optional `is_cluster` field on `CartographyMetadata` — server always sets it, so absence is impossible in practice; client silently defaults to `false` for cartography-absent worlds (correct, not a hidden error). No client-side warn required; server-side `cluster_detected_span` (M-A) is the lie detector. Noted for future dev-mode hardening.
  2. Pre-existing ESLint warning on `App.tsx:1573` (`react-hooks/exhaustive-deps`) — unrelated to this story; lives on develop; independent cleanup.

**Test Coverage:**
- 2093/2093 passing (all 8 new cluster-routing tests green, 3 regression guards intact)
- Flag-read wiring verified end-to-end (server → WS → MapState → MapWidget consumption)
- Divergence cases proven (flag true @ low region count renders graph; flag false @ high region count renders orrery)

**Risk Assessment:**
- **Change scope:** UI routing logic only — display decision input replaced, no behavioral mutation
- **Regression scope:** 3 existing orrery-routing cases (coyote_star, aureate_span, empty cartography) + 1 cluster-unchanged case (perseus_cloud) — all green
- **Contract:** Assumes server always sets `is_cluster` within cartography dict (verified in M-A session_helpers.py:1483); if server future-regresses and omits the field, client silently treats world as single-system (bounded fallback, not a hidden error)

**Dependencies:**
- Stacked on 104-1 (M-A server flag implementation) — already merged into server develop
- No downstream stories; this closes the M-B client consumption tier

**Next Step:** Approve and merge PR #[TBD] to ui develop. Story ready to finish.

