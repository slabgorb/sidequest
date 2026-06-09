---
story_id: "100-10"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-10: Phase 3 — Shared d3-dag map component + in-game MapOverlay adoption + delete cartographyLayout.ts (C4)

## Story Details
- **ID:** 100-10
- **Jira Key:** (none — SideQuest uses sprint YAML only)
- **Workflow:** tdd
- **Points:** 5
- **Repos:** sidequest-ui
- **Branch:** feat/100-10-shared-d3-dag-map-component
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** red
**Phase Started:** 2026-06-09T10:36:19Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| red | 2026-06-09T10:36:19Z | - | - |

## Story Context
Part of epic 100: "Reference pages → React SPA migration (server-projection / React-render seam)". This is a high-risk Phase-3 story that creates a SHARED d3-dag map component for both reference pages AND in-game MapOverlay, killing the `reference_map.py` ↔ `cartographyLayout.ts` split-brain. The story modifies IN-GAME code (MapOverlay adoption) and DELETES `cartographyLayout.ts`, so there is real regression risk to live gameplay map rendering.

**Build on:** Epic 100 Phase 2 merged (100-8 session-free shell + 100-9 theme injector at d981aef).

**Risk Assessment:**
- Deletion: `cartographyLayout.ts` must not be deleted until ALL consumers migrate to the shared component. Failure = orphaned imports = broken reference pages / in-game map.
- Regression: MapOverlay adoption must preserve existing map rendering quality and performance in live gameplay (no white-screen, no layout-break).
- Wiring: Per "Verify Wiring, Not Just Existence" principle: the shared component must be wired into BOTH surfaces end-to-end, not just created.

**Known Baseline Noise (NOT this story's problem):**
- 97-7: `client-build` RED from tsc — `ConfrontationOverlay.beatimpact.test.tsx` BeatEffect union type mismatch (pre-existing develop)
- 97-8: `npm test` flaky timeout — `lobby-start-ws-open.test.tsx` WebSocket navigation test hangs 1/N runs (pre-existing develop)

**Study Before Scoping:**
- Existing in-game MapOverlay component (src/)
- cartographyLayout.ts (the layout logic being deleted)
- Any existing map/cartography rendering subsystems
- ADR-094 (Orrery Label Placement three-strategy taxonomy)
- ADR-141 (two-scale spatial model — galactic graph as campaign view, per-system orrery as local view)
- Epic spec: `docs/superpowers/specs/2026-06-08-reference-pages-react-migration-design.md`

## Delivery Findings

### Dev (implementation)
- **Improvement** (non-blocking): `cartographyLayout.removed.test.ts` first assertion used a
  string-literal `import("@/lib/cartographyLayout")` which vite's `import-analysis` resolves at
  transform time even with `@vite-ignore` — so a deleted module fails the suite to *collect*
  instead of rejecting at runtime as TEA intended. Affects
  `src/components/map/__tests__/cartographyLayout.removed.test.ts` (build the specifier at
  runtime so vite skips static analysis; the `@/` alias still resolves at runtime). Fixed here;
  flag the pattern for any future deletion-guard tests. *Found by Dev during implementation.*

## Design Deviations

### Dev (implementation)
- **Removal-guard test: runtime-built dynamic-import specifier**
  - Spec source: TEA RED file `cartographyLayout.removed.test.ts`, assertion "no longer resolves as an importable module"
  - Spec text: `await expect(import(/* @vite-ignore */ "@/lib/cartographyLayout")).rejects.toThrow();`
  - Implementation: `const spec = ["@","lib","cartographyLayout"].join("/"); await expect(import(/* @vite-ignore */ spec)).rejects.toThrow();`
  - Rationale: As a string literal, vite's `import-analysis` statically resolves the aliased path at transform time despite `@vite-ignore`, failing the whole suite to collect rather than rejecting at runtime — the test could never go green as written. A runtime-built specifier preserves the exact behavioral assertion (same `@/lib/cartographyLayout` path, resolved by vite's runtime alias resolver, still rejects because the module is deleted).
  - Severity: minor
  - Forward impact: none — assertion semantics unchanged; module-absent is still proven behaviorally plus by the fs-read of MapOverlay.tsx.
- **d3-dag DAG direction for an undirected, cyclic adjacency graph**
  - Spec source: epic spec 2026-06-08, C4; TEA `cartographyDagLayout.test.ts` (DIAMOND fixture has a cycle)
  - Spec text: "uses d3-dag (Sugiyama layered layout) — pretty and deterministic"
  - Implementation: Each de-duplicated undirected edge is directed from its lexicographically smaller endpoint to its larger one (a strict total order ⇒ guaranteed acyclic) before feeding d3-dag's Sugiyama; nodes/edges added in sorted order for key-order-independent determinism.
  - Rationale: Sugiyama requires a DAG, but cartography adjacency is undirected and may contain cycles (it does in the DIAMOND fixture). Lexicographic edge direction is the simplest deterministic acyclic orientation. Pixel coords are explicitly not pinned by tests.
  - Severity: minor
  - Forward impact: none — topology/edge contract preserved; only node x/y differ from the retired BFS columns, which no test pins.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `src/components/map/cartographyDagLayout.ts` (NEW) — shared deterministic d3-dag (Sugiyama) layout engine; `adjacent`-only topology, sorted+deduped edges, dangling drop, key-order-independent determinism.
- `src/components/map/CartographyMap.tsx` (NEW) — shared self-contained SVG map component; reuses the existing RegionNodeGraph DOM/testid contract; drill-aware-ready (`activeNodeId`/`onNodeSelect`).
- `src/components/MapOverlay.tsx` — `RegionNodeGraph` removed; now renders `<CartographyMap>` (currentRegionId→activeNodeId, visitedRegionIds→visitedNodeIds). `CartographyMetadata`/`CartographyRegion`/`CartographyRoute` still exported here.
- `src/lib/cartographyLayout.ts` (DELETED) + `src/lib/__tests__/cartographyLayout.test.ts` (DELETED) — split-brain TS port retired.
- `src/components/map/__tests__/cartographyLayout.removed.test.ts` — one-line test-tooling fix (see deviation).
- `package.json` / `package-lock.json` — `d3-dag@1.2.1` added.

**Tests:** Full suite 1963/1964 passing. The 1 failure is the known 97-8 `lobby-start-ws-open.test.tsx` flake (pre-existing develop, unrelated). New map suite: 6 files / 59 tests GREEN incl. 28-test in-game regression guard + split-brain unification.
**Lint:** 0 errors (1 pre-existing App.tsx warning, untouched).
**Build (tsc):** Clean except the known 97-7 ConfrontationOverlay baseline errors (pre-existing develop).
**cartographyLayout.ts:** DELETED — zero surviving production references (only doc-comment/test mentions remain).
**Branch:** feat/100-10-shared-d3-dag-map-component (pushed)

**Handoff:** To review.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (failing — ready for Dev)
**Branch:** feat/100-10-shared-d3-dag-map-component (commit 831f006)

### Investigation — cartographyLayout.ts consumer audit
**Production consumers of `src/lib/cartographyLayout.ts` (must migrate before deletion): EXACTLY ONE.**
- `src/components/MapOverlay.tsx:1` — `import { computeCartographyLayout, NODE_R } from "@/lib/cartographyLayout"`, used by the inner `RegionNodeGraph` component.

**Test/other files that reference the legacy module (Dev deletes/migrates these):**
- `src/lib/__tests__/cartographyLayout.test.ts` — unit tests for the deleted module → DELETE (determinism moves to the new module test per spec C4).
- `src/lib/cartographyLayout.ts` itself imports the `CartographyMetadata` *type* from `@/components/MapOverlay` (type-only).

**Type-location note:** `CartographyMetadata` / `CartographyRegion` / `CartographyRoute` currently live in `MapOverlay.tsx` and are re-exported. Keep them exported from `@/components/MapOverlay` (re-export OK) — tests + the shared module import the type from there. (Type-only imports erase at runtime, so a MapOverlay→CartographyMap→cartographyDagLayout→MapOverlay-type cycle is safe.)

**d3-dag is NOT installed** (only `d3@^7.9.0` + `@types/d3`). Dev adds `d3-dag` to package.json in GREEN.

### Pinned contract (so Dev knows props/shape/paths)
**Shared layout module — `src/components/map/cartographyDagLayout.ts`:**
```ts
export function computeCartographyDagLayout(cart: CartographyMetadata): CartographyDagLayout
interface CartographyDagLayout {
  nodes: { id: string; name: string; x: number; y: number }[];
  edges: { a: string; b: string }[];   // sorted endpoints (a<=b), de-duplicated
  dangling: { source: string; missing: string }[];
  width: number; height: number;
}
```
- Topology input is `adjacent` ONLY; `routes` are NOT edges (spec edge-shape cross-ref). Dangling adjacency (→unknown region) dropped + reported.
- Deterministic + key-order independent (C4) — sort inputs before feeding d3-dag. Exact pixel coords/width/height NOT pinned (d3-dag Sugiyama free to move dots); topology + determinism ARE pinned.

**Shared component — `src/components/map/CartographyMap.tsx`:**
```ts
interface CartographyMapProps {
  cartography: CartographyMetadata;
  activeNodeId?: string;                       // "you are here" / drill-selected
  visitedNodeIds?: Set<string>;                // runtime overlay (ref page omits)
  onNodeSelect?: (regionId: string) => void;   // drill-aware hook for 98-3
}
```
- DOM contract REUSES existing RegionNodeGraph testids so the 28 existing MapOverlay/layout regression tests keep passing once MapOverlay adopts it: `map-region-graph` (SVG root), `map-region-node-{id}` (+`data-region-id`), `map-region-edge-{a}--{b}`, `data-current` on active, `data-visited` on visited, label `paint-order="stroke"`.
- Self-contained (C2): reaches for NO session/WS/game state. Drill-aware-ready (epic-98/98-3): `activeNodeId` + `onNodeSelect`; no assumption MapWidget's feed/toggle is permanent.

### Test Files (all RED, commit 831f006)
- `src/components/map/__tests__/cartographyDagLayout.test.ts` — determinism (C4), topology, routes-not-topology, dangling-drop.
- `src/components/map/__tests__/CartographyMap.test.tsx` — component contract incl. drill-aware callback + no-session render.
- `src/components/map/__tests__/MapOverlay.shared-map.test.tsx` — **split-brain unification guard** (identical topology, reference vs in-game) + **MapOverlay regression/wiring guard**.
- `src/components/map/__tests__/cartographyLayout.removed.test.ts` — deletion guard (legacy module unresolvable + MapOverlay no longer imports it).

**Regression baseline (existing, must STAY green after Dev's change):** `MapOverlay.cartography.test.tsx` + `cartographyLayout.test.ts` = 28 tests green on develop pre-change. The cartographyLayout.test.ts file is deleted with the module; its 28→ relevant determinism coverage is replaced by cartographyDagLayout.test.ts.

**RED confirmation:** 3 files fail at collection (`Failed to resolve import` — shared modules absent); deletion guard's 2 tests fail (legacy module still resolves; MapOverlay still imports). All correct RED. Baseline noise (97-7 ConfrontationOverlay tsc build error; 97-8 lobby-ws flake) is NOT this story.

**Handoff:** To Dev for GREEN (task #2).

## Deviation Audit (Reviewer)

- **Removal-guard runtime-built specifier** — ACCEPTED. The string-literal `import("@/lib/cartographyLayout")` is statically resolved by vite `import-analysis` at transform time (even with `@vite-ignore`), collapsing a runtime rejection into a collect-time failure. Runtime-built specifier preserves the exact behavioral assertion; the `@/` alias still resolves at runtime (TEA RED record: "legacy module still resolves" — proves non-vacuous), and module-absence is double-covered by the fs-read assertion. Sound.
- **d3-dag lexicographic edge direction** — ACCEPTED. Sugiyama requires a DAG; cartography adjacency is undirected + cyclic (DIAMOND fixture). Directing each de-duped edge small→large endpoint is a strict total order ⇒ guaranteed acyclic + deterministic. Topology/edge contract preserved; only node x/y differ from the retired BFS columns, which no test pins (C5). Sound.

## Reviewer Assessment

**Verdict:** APPROVED
**PR:** #361 (sidequest-ui, base develop) — feat/100-10-shared-d3-dag-map-component @ 7b1b24c

**Priority checks (all PASS):**
1. **Genuine sharing (C4):** Exactly ONE layout module (`cartographyDagLayout.ts`) + ONE component (`CartographyMap.tsx`); duplicate `cartographyLayout.ts` DELETED — no copy. Reference-side React consumption correctly out of 100-10 scope per spec ownership boundary (100-10 owns the layout engine; 98-3 owns the view-model; the reference Map *section* belongs to the React reference renderer). In-game adoption live + proven. Split-brain (cartographyLayout.ts ↔ reference_map.py TS port) killed.
2. **No in-game regression (load-bearing):** `MapOverlay.cartography.test.tsx` is NOT in the diff (literally unchanged — couldn't be weakened/skipped) and PASSES against the swapped-in CartographyMap. `src/components/__tests__/MapOverlay*` = 2 files / 31 tests green. Old tests written against the inline RegionNodeGraph pass unchanged after adoption — the strongest non-regression evidence.
3. **cartographyLayout.ts FULLY deleted:** Repo-wide grep = ZERO live imports (only doc-comments + removal-guard assertion strings). `computeCartographyLayout` zero live callers. `CartographyMetadata` still exported from MapOverlay (type-only consumer preserved).
4. **Removal-guard non-vacuous:** vite `@`→`./src` alias (vite.config.ts:11) shared with vitest → a present `@/lib/cartographyLayout` WOULD resolve → `.rejects.toThrow()` would FAIL. TEA RED record confirms it failed-because-resolved. Plus a source-grep assertion on MapOverlay.tsx.
5. **d3-dag@^1.2.1:** Real maintained Sugiyama lib; caret range consistent with repo convention (d3 `^7.9.0`); package-lock +207. Reasonable.
6. **Test quality:** Testing-Library throughout, no snapshot-only, topology-based assertions (pins node-set + sorted-endpoint edges + determinism, NOT pixel coords per C5). Determinism suite covers repeated-run + key-reorder + dangling-drop + routes-are-not-edges. C2 self-containment verified; drill-aware-ready per 98-3 boundary.

**Gates (baseline-diffed via merge-base/diff provenance, no develop checkout):**
- Lint: 0 errors, 1 warning (`App.tsx:1522`, NOT in diff, pre-existing).
- Build (tsc): 5 errors, ALL in `ConfrontationOverlay.beatimpact.test.tsx` = known 97-7 (from 73-4; exists on develop, NOT in diff).
- Test: full suite 1963/1964; 1 fail = `lobby-start-ws-open.test.tsx` = known 97-8 (NOT in diff, exists on develop). Map suite 4 files/28 green; MapOverlay regression 2 files/31 green.
- **ZERO new build/test/lint failures attributable to 100-10.**

**Low / non-blocking (not gating):**
- 97-8 lobby-ws failed 3/3 in isolation here (documented "flaky 1/N") — possible degradation flake→consistent on develop. A 97-8 concern, not a 100-10 regression.
- `cartographyDagLayout.ts`: a self-adjacency (region listing its own id in `adjacent`) is skipped from the DAG (`a===b` guard) but survives into the returned `edges` array → CartographyMap would draw a zero-length (invisible) line. Harmless, vanishingly unlikely. LOW/cosmetic — future hardening, not a blocker.

**Data flow traced:** server cartography MAP_UPDATE → `MapState.cartography` → MapOverlay derives `currentRegionId`/`visitedRegionIds` → `<CartographyMap>` → `computeCartographyDagLayout` (sorted, deterministic, acyclic-directed) → SVG node-link graph. Safe: region-mode only (`showRegionGraph` gates non-empty regions); room_graph falls through to coordinate/list view.

**Handoff:** To SM for finish-story.
