---
story_id: "29-4"
jira_key: "MSSCI-16930"
epic: "MSSCI-16929"
workflow: "tdd"
---
# Story 29-4: Single-room SVG tactical renderer — cell-level tiles, feature markers, genre-themed palette

## Story Details
- **ID:** 29-4
- **Jira Key:** MSSCI-16930
- **Epic:** MSSCI-16929 (Tactical ASCII Grid Maps)
- **Workflow:** tdd
- **Stack Parent:** none (standard feature)

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-08T10:09:09Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-08T09:44:45Z | 2026-04-08T09:46:16Z | 1m 31s |
| red | 2026-04-08T09:46:16Z | 2026-04-08T09:51:51Z | 5m 35s |
| green | 2026-04-08T09:51:51Z | 2026-04-08T09:55:36Z | 3m 45s |
| spec-check | 2026-04-08T09:55:36Z | 2026-04-08T09:55:46Z | 10s |
| verify | 2026-04-08T09:55:46Z | 2026-04-08T09:59:10Z | 3m 24s |
| review | 2026-04-08T09:59:10Z | 2026-04-08T10:09:02Z | 9m 52s |
| spec-reconcile | 2026-04-08T10:09:02Z | 2026-04-08T10:09:09Z | 7s |
| finish | 2026-04-08T10:09:09Z | - | - |

## Story Context

### Epic Context
Epic 29 — Tactical ASCII Grid Maps. Deterministic tactical dungeon maps from ASCII grids. Tokens, zones, non-rectangular rooms, jaquayed layout, shared walls. ADR-071. Primary genre: caverns_and_claudes.

### Prior Stories (Completed)
- **29-1:** ASCII grid parser — glyph vocabulary, legend, exit extraction from wall gaps (done, in api)
- **29-2:** Tactical grid validation in sidequest-validate — perimeter closure, flood fill, exit matching (done, in api)
- **29-3:** Author ASCII grids for Mawdeep 18 rooms — non-rectangular shapes, template library seed (done, in content)

### This Story
First UI story in the epic. Building the SVG renderer that will visualize the parsed grids from 29-1. The ASCII grid parser (29-1) produces a `TacticalGrid` struct with cells, features, and exits. This story renders a single room as an SVG with:
- Cell-level tiles (10x10 or custom size grid, depends on genre)
- Feature markers (doors, traps, furniture, hazards)
- Genre-themed palette (Mawdeep cavern rocks, colors, etc.)
- Scalable, themable SVG output suitable for embedding in game UI

### Repos Involved
- **sidequest-ui** (primary) — React/TypeScript, SVG rendering

### Dependencies
- Protocol contract from 29-1 (ASCII grid parser) — outputs TacticalGrid
- Validated grid structure from 29-2
- Genre pack definitions from 29-3 (Mawdeep world data)
- Next: 29-5 (TACTICAL_STATE protocol message for wiring to UI)

## Delivery Findings

No upstream findings at setup.

### TEA (test design)
- No upstream findings during test design.

### Reviewer (code review)
- **Improvement** (non-blocking): Event handlers (handleClick, handleMouseEnter, handleMouseLeave) not wrapped in useCallback. Performance concern for large grids (800+ cells). Affects `sidequest-ui/src/components/TacticalGridRenderer.tsx` (lines 76-86). Recommend addressing in story 29-12 (click-to-move) when interaction becomes the focus. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Hover flicker between adjacent cells — onCellHover(null) fires between every cell transition. Consider attaching onMouseLeave to grid-layer `<g>` instead of individual cells. Affects `sidequest-ui/src/components/TacticalGridRenderer.tsx` (line 131). *Found by Reviewer during code review.*

## Design Deviations

No deviations logged at setup.

### TEA (test design)
- **Lazy dynamic imports instead of top-level imports for component under test**
  - Spec source: context-story-29-4.md, AC-9
  - Spec text: "Component has vitest tests for: rendering, cell click, theme application"
  - Implementation: Tests use `async function importRenderer()` with dynamic `import()` instead of top-level `import { TacticalGridRenderer }` to allow vitest to report per-test failures rather than suite-level import crash
  - Rationale: Better RED-phase diagnostics — each test individually reports the missing module rather than a single suite failure
  - Severity: minor
  - Forward impact: none — Dev can keep or replace with static imports once component exists

### Reviewer (code review)
- No deviations from spec.

### TEA (verify)
- **Kept unused SVG symbol definitions despite dead-code finding**
  - Spec source: tactical-grid-renderer.test.tsx, edge case test "SVG uses defs/symbol/use pattern"
  - Spec text: "defs.querySelectorAll('symbol').length > 0"
  - Implementation: Symbols retained in `<defs>` even though no `<use>` references exist
  - Rationale: Test explicitly validates the symbol pattern as architectural scaffolding; removing breaks the test
  - Severity: minor
  - Forward impact: none — symbols ready for `<use>` optimization when needed

### Dev (implementation)
- No deviations from spec.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-ui/src/components/TacticalGridRenderer.tsx` — NEW: Single-room SVG renderer with genre-themed palette, cell-level tiles, feature markers with tooltips, click/hover handlers
- `sidequest-ui/src/components/Automapper.tsx` — MODIFIED: Added optional `grid` field to `ExploredRoom`, delegation to TacticalGridRenderer when current room has grid data, default tactical theme

**Tests:** 28/28 passing (GREEN)
**Branch:** feat/29-4-svg-tactical-renderer (pushed)

**Implementation Notes:**
- Cell rendering uses direct `<rect>` elements with `data-cell-type`, `data-x`, `data-y` attributes
- Feature cells wrapped in `<g>` groups with `<title>` for native SVG tooltip and `<text>` marker glyph
- `<defs>` contains `<symbol>` elements for efficient DOM pattern
- Void cells render with `fill="none"` and no stroke for transparency
- Theme-driven fills for all cell types via `cellFill()` function
- Automapper delegates via early return when `currentRoom?.grid` is present

**Handoff:** To Fezzik (TEA) for verify phase

### Dev (implementation) — Delivery Findings
- No upstream findings during implementation.

## Reviewer Assessment

**Decision:** APPROVE
**PR:** https://github.com/slabgorb/sidequest-ui/pull/87

**Subagents:** preflight, silent-failure-hunter, type-design, rule-checker (all Sonnet, parallel)

### Specialist Findings
- [RULE] Rule-checker found 4 violations: 1 fixed (inline type → FeatureDef), 1 flagged (useCallback), 2 dismissed (pre-existing)
- [SILENT] Silent-failure-hunter: clean — no swallowed errors, pure render functions with optional chaining, no try/catch blocks
- [TYPE] Type-design: clean — union types (TacticalCellType, FeatureType) correctly narrowed in switch, FeatureDef single-source enforced after fix

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 28/28 GREEN, no code smells, clean commit history | N/A |
| 2 | reviewer-type-design | Yes | clean | No type design issues — union types used correctly, FeatureDef single-source fixed | N/A |
| 3 | reviewer-silent-failure-hunter | Yes | clean | No swallowed errors — pure render functions, optional chaining used correctly, no try/catch | N/A |
| 4 | reviewer-rule-checker | Yes | 4 violations | Inline type (#2), exit_type plain string (#2 pre-existing), no useCallback (#6), dead symbol test (#8) | 1 fixed, 1 flagged, 2 dismissed |

All received: Yes

**Findings Triaged:** 10 total
- **1 fix applied:** Inline structural type replaced with `FeatureDef` import (rule #2, TypeScript checklist)
- **2 flagged non-blocking:** useCallback for event handlers (rule #6), hover flicker between cells
- **7 dismissed:** Dead symbols (documented TEA deviation), no default in exhaustive switch (compile-time safe), pre-existing code issues, out-of-scope integration depth

**Rule Compliance:** 12/13 TypeScript rules pass. Rule #9 (skipLibCheck) is pre-existing config.

**Wiring Verified:**
- TacticalGridRenderer → imported by Automapper (non-test consumer)
- Automapper → imported by OverlayManager (confirmed via grep)
- Production path reachable: OverlayManager → Automapper → TacticalGridRenderer (when room has grid)

**Tests:** 28/28 GREEN after review fix
**Branch pushed:** 4 commits (test → impl → simplify → review fix)

**Handoff:** To Vizzini (SM) for finish

## TEA Verify Assessment

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 8 findings | Test fixtures extractable, cell rendering duplication, direction offsets shareable |
| simplify-quality | 3 findings | Unused symbols (dismissed — test requires them), unused props, CardinalDirection export |
| simplify-efficiency | 3 findings | Unused symbols (dismissed), unused props, redundant void check |

**Applied:** 2 high-confidence fixes
1. Removed unused `entities`/`zones` props from `TacticalGridRendererProps` (no stubs rule)
2. Simplified void cell stroke logic — `cellStroke()` already returns `undefined` for void

**Flagged for Review:** 3 medium-confidence findings
- Test fixtures could be extracted to shared file (scope beyond 29-4)
- Cell rect construction has some duplication between feature/non-feature branches (minor, different structure)
- Direction offsets could be shared utility (affects Automapper, separate story)

**Noted:** 3 low-confidence observations (CardinalDirection export, theme factory, exit icon fallback — all reasonable as-is)
**Reverted:** 0

**Dismissed:** Unused `<symbol>` definitions — test AC explicitly asserts `defs > symbol` elements exist. Symbols are architectural scaffolding for the `<use>` pattern.

**Overall:** simplify: applied 2 fixes

**Quality Checks:** 28/28 tests passing, typecheck clean
**Handoff:** To Westley (Reviewer) for code review

### TEA (verify) — Delivery Findings
- No upstream findings during test verification.

## TEA Assessment (RED phase)

**Tests Required:** Yes
**Reason:** 5-point UI story with 10 ACs, new component + wiring

**Test Files:**
- `sidequest-ui/src/__tests__/tactical-grid-renderer.test.tsx` — 25 tests across 8 describe blocks
- `sidequest-ui/src/types/tactical.ts` — TypeScript type definitions mirroring Rust TacticalGrid types

**Tests Written:** 25 tests covering all 10 ACs
**Status:** RED (failing — import error, component does not exist)

### AC Coverage

| AC | Tests | Description |
|----|-------|-------------|
| AC-1 | 2 | All 8 cell types render as distinct SVG elements with themed colors |
| AC-2 | 2 | Void cells transparent fill and no stroke |
| AC-3 | 3 | Feature markers with visual element, tooltip via `<title>`, themed color |
| AC-4 | 3 | Default cellSize=24 viewBox, custom cellSize scaling, position intervals |
| AC-5 | 4 | onCellClick with GridPos on floor/feature/wall, no-throw when absent |
| AC-6 | 2 | Neon theme produces different fills than cavern theme |
| AC-7 | 1 | Automapper renders TacticalGridRenderer when room has grid |
| AC-8 | 1 | Automapper renders schematic when room has no grid |
| AC-9 | — | This test file IS the test (meta-satisfied) |
| AC-10 | 2 | TacticalGridRenderer importable, Automapper exports exist |

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 null/undefined | `onCellHover fires with null on mouse leave` | failing |
| #6 React/JSX keys | `cells have stable keys based on position` | failing |
| #6 React/JSX SVG | `SVG has viewBox and preserveAspectRatio` | failing |
| #8 test quality | Self-checked — no vacuous assertions, all tests assert specific values | clean |

**Rules checked:** 3 of 13 TypeScript lang-review rules have direct test coverage (others are code-quality rules enforced at review, not testable in isolation)
**Self-check:** 0 vacuous tests found — all assertions check specific values or element existence

### Edge Cases
- 1x1 grid rendering
- L-shaped room via void cells (non-rectangular)
- Multiple features from legend with distinct tooltips
- SVG `<defs>/<symbol>/<use>` pattern for efficient DOM

**Handoff:** To Inigo Montoya (Dev) for implementation

## Sm Assessment

Story 29-4 is ready for RED phase. Setup complete:

- **Session file** created with full epic lineage and dependency chain
- **Branch** `feat/29-4-svg-tactical-renderer` cut from develop in sidequest-ui
- **Jira** MSSCI-16930 claimed and moved to In Progress
- **Context:** This is the first UI story in Epic 29. The API-side grid parser (29-1) and validator (29-2) are done. Mawdeep content grids (29-3) are authored. This story builds the React SVG renderer that visualizes a single parsed room grid with cell tiles, feature markers, and genre-themed palette.
- **Risk:** Protocol contract for TACTICAL_STATE (29-5) is not yet implemented — TEA should design tests against the TacticalGrid structure from 29-1's parser output, not the protocol message.
- **Routing:** TDD phased workflow → RED phase → Fezzik (TEA)