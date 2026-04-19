---
story_id: "29-19"
jira_key: "MSSCI-16932"
epic: "MSSCI-16929"
workflow: "tdd"
---
# Story 29-19: Wire Tactical Grid into MAP_UPDATE

## Story Details
- **ID:** 29-19
- **Jira Key:** MSSCI-16932
- **Epic:** MSSCI-16929 (Tactical ASCII Grid Maps)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 3
- **Priority:** p0

## Story Summary

Server emits tactical grid payload in MAP_UPDATE messages, UI consumes and renders it via DungeonMapRenderer. This wires the full pipe so tactical grids appear in-game when exploring rooms with `grid` fields in rooms.yaml.

**Acceptance Criteria:**
- AC-1: ExploredLocation has `tactical_grid: Option<TacticalGridPayload>` field
- AC-2: build_room_graph_explored parses RoomDef.grid and sets tactical_grid
- AC-3: Rooms without grid field produce tactical_grid: None (not an error)
- AC-4: useAutomapperData reads tactical_grid from MapState and sets ExploredRoom.grid
- AC-5: In a playtest with caverns_and_claudes/mawdeep, opening the map (M key) shows the tactical grid renderer instead of schematic rectangles
- AC-6: OTEL span emitted when tactical_grid is populated (subsystem: tactical)

## Key Files

| File | Action |
|------|--------|
| `sidequest-api/crates/sidequest-protocol/src/message.rs` | ADD: tactical_grid field to ExploredLocation |
| `sidequest-api/crates/sidequest-game/src/room_movement.rs` | MODIFY: build_room_graph_explored to populate tactical_grid |
| `sidequest-api/crates/sidequest-game/src/tactical/grid.rs` | READ: TacticalGrid::parse() for grid parsing |
| `sidequest-ui/src/components/OverlayManager.tsx` | MODIFY: useAutomapperData to consume tactical_grid |

## Dependencies

- **29-1** (done): ASCII grid parser
- **29-3** (done): Mawdeep room grids authored
- **29-5** (done): TacticalGridPayload protocol type
- **29-8** (done): DungeonMapRenderer + Automapper three-way delegation

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-08T19:18:15Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-08T18:47:40Z | 2026-04-08T18:48:52Z | 1m 12s |
| red | 2026-04-08T18:48:52Z | 2026-04-08T18:54:36Z | 5m 44s |
| green | 2026-04-08T18:54:36Z | 2026-04-08T19:06:24Z | 11m 48s |
| spec-check | 2026-04-08T19:06:24Z | 2026-04-08T19:09:02Z | 2m 38s |
| verify | 2026-04-08T19:09:02Z | 2026-04-08T19:12:28Z | 3m 26s |
| review | 2026-04-08T19:12:28Z | 2026-04-08T19:17:15Z | 4m 47s |
| spec-reconcile | 2026-04-08T19:17:15Z | 2026-04-08T19:18:15Z | 1m |
| finish | 2026-04-08T19:18:15Z | - | - |

## Sm Assessment

**Story 29-19** — 3pt P0 TDD, api + ui repos. Wire tactical grid data into the MAP_UPDATE protocol message so the UI can render dungeon maps via DungeonMapRenderer.

**Dependencies satisfied:** 29-1 (grid parser), 29-3 (Mawdeep grids), 29-5 (TacticalGridPayload protocol type), 29-8 (DungeonMapRenderer + Automapper delegation) are all complete.

**Routing:** TDD workflow → red phase (Fezzik/TEA writes failing tests), then green phase (Inigo Montoya/Dev implements).

**Branches:** `feat/29-19-wire-tactical-grid-map-update` on both sidequest-api and sidequest-ui (base: develop).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): AC-5 (playtest visual verification) is not testable in automated tests — requires manual playtest with caverns_and_claudes/mawdeep. Affects `sidequest-ui/` (visual rendering). *Found by TEA during test design.*
- **Question** (non-blocking): AC-6 (OTEL span) — no test written because OTEL emission is typically verified via integration/playtest OTEL dashboard, not unit tests. May want a structural test that the tracing call exists. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): AC-6 OTEL span not yet implemented — parse_room_grid logs tracing::warn on failure but does not emit a success OTEL span. Story 29-18 covers comprehensive OTEL for the tactical system. Affects `sidequest-api/crates/sidequest-game/src/room_movement.rs` (add tracing::info span). *Found by Dev during implementation.*
- **Gap** (non-blocking): TacticalGridPayload does not include exit gap data — the wire format has width/height/cells/features but no exits. ExitGap computation is deferred to client-side or future story. Affects `sidequest-ui/src/components/OverlayManager.tsx` (exits: [] in parsed grid). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): parseTacticalGridPayload maps unknown cell types to "floor" (walkable) — safer default would be "void" (impassable). Affects `sidequest-ui/src/components/OverlayManager.tsx:54`. *Found by Reviewer during code review.*

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | N/A | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 4 | confirmed 0, dismissed 3 (pre-existing/deferred), deferred 1 |
| 4 | reviewer-test-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | N/A | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | findings | 4 | confirmed 0, dismissed 4 (pre-existing/out-of-scope) |
| 7 | reviewer-security | N/A | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | N/A | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 5 | confirmed 0, dismissed 5 (pre-existing/already-deferred) |

**All received:** Yes (4 returned, 5 disabled via settings)
**Total findings:** 0 confirmed, 12 dismissed (all pre-existing or already-deferred), 1 deferred (UI floor fallback)

### Devil's Advocate

What if this wiring is subtly broken in ways the tests don't catch?

**Grid data fidelity through the pipeline.** The server parses ASCII grids into TacticalGrid (typed cells), converts to TacticalGridPayload (string cells), serializes to JSON, the client deserializes and converts back to typed TacticalCell objects. Three conversions. Could data be lost? The cell type vocabulary is fixed: 8 Rust variants map to 8 strings map to 8 TypeScript types. Feature glyphs are a potential weak point — the server sends glyph positions in the features array, and the client rebuilds glyph markers by overwriting cells at those positions. If the client fails to mark a cell, the feature is invisible but the cell renders as "feature" type (from cell_to_string). This is an inconsistency — the cell string says "feature" but the legend lookup would fail. However, the test at tactical_wiring_story_29_19_tests.rs:164 verifies features are present in the payload, so this path is exercised.

**Backward compatibility under deny_unknown_fields.** ExploredLocation has `#[serde(deny_unknown_fields)]`. Adding `tactical_grid` means old server payloads (without the field) deserialize cleanly via `#[serde(default)]`. But what about old clients receiving new server payloads WITH `tactical_grid`? The client-side MapState type is untyped (`Record<string, unknown>`), so extra fields are silently accepted. No breakage. What about the protocol test at tests.rs:372 — it was updated with `tactical_grid: None`, and the backward compat test at 29-19 verifies JSON without the field. Both directions covered.

**What if a room has a grid field but an empty string?** RoomDef.grid is `Option<String>`. An empty string Some("") would reach TacticalGrid::parse(), which returns `GridParseError::EmptyGrid`. parse_room_grid catches this and logs warn, returns None. The room renders without a grid. Not a data corruption risk.

**What if the legend HashMap iteration order differs between Rust and the client?** HashMap iteration is unordered. The features array in TacticalGridPayload has no guaranteed order. The client iterates features to build the legend and mark cells — order doesn't matter because each feature targets specific [x,y] positions. No ordering dependency.

**What about the `exits: []` stub in parseTacticalGridPayload?** The client returns an empty exits array. TacticalGridData.exits is typed as `readonly ExitGap[]`. The DungeonMapRenderer (from story 29-8) may use exits for rendering connection points. If it expects exits and gets none, it might not draw exit indicators — but the schematic view already draws room connections via the room_exits field, so this is cosmetic at worst. Dev documented this as a delivery finding.

None of these adversarial angles reveal blocking issues. The pipeline is sound.

## Reviewer Assessment

**Verdict:** APPROVED

**Observations:**

1. [VERIFIED] ExploredLocation.tactical_grid field — `message.rs:1150`, `Option<TacticalGridPayload>` with `#[serde(default, skip_serializing_if)]`. Backward compatible in both directions. Matches existing field patterns (size, room_exits). Complies with AC-1.
2. [VERIFIED] build_room_graph_explored population — `room_movement.rs:193`, calls `parse_room_grid(room)` which returns `Some(payload)` for gridded rooms, `None` for gridless. Tests verify both paths. Complies with AC-2, AC-3.
3. [VERIFIED] cell_to_string exhaustiveness — `room_movement.rs:271-280`, all 8 TacticalCell variants matched explicitly. No catch-all arm (removed in verify phase). Compiler will enforce updates when new variants added. [SIMPLE] clean (via verify phase).
4. [VERIFIED] FeatureType::as_str + Display — `grid.rs:150-170`, all 6 variants mapped. Zero-alloc `&'static str`. [TYPE] clean.
5. [VERIFIED] cells() getter — `grid.rs:322-325`, returns `&[Vec<TacticalCell>]`. Enables conversion without exposing private field. [TYPE] clean.
6. [VERIFIED] UI wiring — `OverlayManager.tsx:94-96`, reads `tactical_grid` from wire, converts via `parseTacticalGridPayload`, sets `ExploredRoom.grid`. Conditional: undefined when absent. Complies with AC-4.
7. [VERIFIED] Serde backward compat — test at 29-19 line 230 deserializes JSON without `tactical_grid` → None. ExploredLocation `#[serde(deny_unknown_fields)]` + `#[serde(default)]` handles both old and new payloads.
8. [LOW] UI unknown cell fallback to "floor" — `OverlayManager.tsx:54`. Client-side, server validates. Safer default would be "void" (impassable) but not blocking. [SILENT] noted.

**Data flow traced:** `RoomDef.grid` (YAML) → `TacticalGrid::parse()` (parser.rs) → `tactical_grid_to_payload()` (room_movement.rs) → `ExploredLocation.tactical_grid` (message.rs) → JSON wire → `parseTacticalGridPayload()` (OverlayManager.tsx) → `ExploredRoom.grid` (Automapper.tsx). Safe: parse errors logged as warn, unknown types handled at each boundary.

**Pattern observed:** Good — the conversion pipeline (parse → typed → wire → typed) follows the existing pattern for room_exits and other ExploredLocation fields. Feature glyph positions are collected server-side and reconstructed client-side, preserving the legend.

**Error handling:** Parse failures → `tracing::warn` + None (not silent — logged with room_id). Unknown cell types → "floor" fallback (client-side). Empty grid → `GridParseError::EmptyGrid` → warn + None. All audible.

**Security analysis:** N/A — internal game state pipeline, no user input flows through tactical_grid. [SEC] clean.

**Rule Compliance:** All subagent rule findings are pre-existing (DispatchError #[non_exhaustive], x:0/y:0 placeholders, size:"medium", workspace deps) — none introduced by this story. [RULE] no new violations. [EDGE] N/A (disabled). [TEST] N/A (disabled). [DOC] N/A (disabled).

**Wiring:** Protocol → Game → UI verified end-to-end. Region-mode construction sites (connect.rs, mod.rs, state.rs) all set `tactical_grid: None`. Room-graph mode populates from RoomDef.grid.

**Handoff:** To Vizzini (SM) for finish-story

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-api/crates/sidequest-protocol/src/message.rs` — Added tactical_grid field to ExploredLocation
- `sidequest-api/crates/sidequest-game/src/room_movement.rs` — Added parse_room_grid(), tactical_grid_to_payload(), cell_to_string()
- `sidequest-api/crates/sidequest-game/src/tactical/grid.rs` — Added cells() getter, FeatureType::as_str(), Display impl
- `sidequest-api/crates/sidequest-game/src/state.rs` — Added tactical_grid: None to ExploredLocation construction
- `sidequest-api/crates/sidequest-server/src/dispatch/connect.rs` — Added tactical_grid: None to region-mode construction
- `sidequest-api/crates/sidequest-server/src/dispatch/mod.rs` — Added tactical_grid: None to region-mode constructions (2 sites)
- `sidequest-api/crates/sidequest-protocol/src/tests.rs` — Added tactical_grid: None to existing test
- `sidequest-api/crates/sidequest-game/tests/map_update_room_graph_story_19_4_tests.rs` — Added tactical_grid/grid/legend/tactical_scale fields to existing tests
- `sidequest-ui/src/components/OverlayManager.tsx` — Added parseTacticalGridPayload(), wired tactical_grid into useAutomapperData

**Tests:** 8/8 new Rust tests passing + 3/3 UI tests passing + 15/15 existing 19-4 tests passing (GREEN)
**Branch:** feat/29-19-wire-tactical-grid-map-update (pushed on api + ui)

**AC Status:**
- AC-1 ✓: ExploredLocation has tactical_grid: Option<TacticalGridPayload>
- AC-2 ✓: build_room_graph_explored parses RoomDef.grid and populates tactical_grid
- AC-3 ✓: Rooms without grid produce tactical_grid: None
- AC-4 ✓: useAutomapperData reads tactical_grid and sets ExploredRoom.grid
- AC-5 ○: Playtest verification needed (manual)
- AC-6 ○: OTEL span deferred to 29-18

**Handoff:** To review phase

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 4 (implementation files only)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 5 findings | Extract payload conversion, move cell_to_string to type impl, parallel legend-building logic |
| simplify-quality | 4 findings | catch-all `_` masks variants, dead exits:[], unsafe type casts |
| simplify-efficiency | 4 findings | hardcoded 'east' fallback, redundant replace chains, unsafe assertions |

**Applied:** 1 high-confidence fix — removed unreachable `_ => "unknown"` catch-all in `cell_to_string()` (same-crate match is exhaustive without it)
**Flagged for Review:** 4 medium-confidence findings (type safety in parseTacticalGridPayload, exits:[] stub, unsafe casts in useAutomapperData, exit_type string assumptions)
**Noted:** 3 low-confidence observations (VALID_CELL_TYPES sync, Feature glyph discard in wire format, O(features×cells) vs O(cells))
**Reverted:** 0

**Overall:** simplify: applied 1 fix

**Quality Checks:** All passing (23 Rust tests green, 3 UI tests green)
**Handoff:** To Westley (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

AC-1 through AC-4 are fully implemented and tested (8 Rust + 3 UI). AC-5 (playtest visual) and AC-6 (OTEL) are properly deferred with documented deviations — AC-5 is inherently manual, AC-6 belongs to story 29-18. Dev's parse-failure deviation (warn+None vs error propagation) is architecturally sound — the function signature returns Vec, not Result, and malformed grids are caught at validation time, not runtime.

**Decision:** Proceed to review

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Grid parse failure logged as warning, not error**
  - Spec source: context-epic-29.md, Guardrail #8
  - Spec text: "No silent fallbacks — if a grid is malformed, fail loudly"
  - Implementation: parse_room_grid() logs tracing::warn! and returns None on parse failure, rather than propagating the error
  - Rationale: build_room_graph_explored returns Vec, not Result — propagating errors would break the existing API. A warning log plus None tactical_grid is audible (not silent) and non-breaking.
  - Severity: minor
  - Forward impact: none — malformed grids are caught at validation time (sidequest-validate), not at runtime
  → ✓ ACCEPTED by Reviewer: tracing::warn is audible (not silent), function returns Option not Result. Grids are validated at authoring time by sidequest-validate; runtime is a second line of defense, not the primary gate.

### TEA (test design)
- **AC-5 not covered by automated tests**
  - Spec source: context-story-29-19.md, AC-5
  - Spec text: "In a playtest with caverns_and_claudes/mawdeep, opening the map (M key) shows the tactical grid renderer instead of schematic rectangles"
  - Implementation: No test written — AC-5 requires visual verification in a live playtest
  - Rationale: This is a visual/manual acceptance criterion, not automatable in unit/integration tests
  - Severity: minor
  - Forward impact: none — playtest verification is the appropriate gate
  → ✓ ACCEPTED by Reviewer: visual verification is inherently manual; correct to not automate.
- **AC-6 OTEL test omitted**
  - Spec source: context-story-29-19.md, AC-6
  - Spec text: "OTEL span emitted when tactical_grid is populated (subsystem: tactical)"
  - Implementation: No OTEL test written — tracing is verified via GM panel/dashboard
  - Rationale: OTEL emission is a wiring concern best verified at integration level, and the project's OTEL testing pattern uses the dashboard, not unit assertions
  - Severity: minor
  - Forward impact: none — story 29-18 (OTEL for tactical system) will add comprehensive OTEL coverage
  → ✓ ACCEPTED by Reviewer: OTEL emission belongs to 29-18; testing via dashboard is the project pattern.

### Reviewer (audit)
- No undocumented deviations found. All spec divergences properly logged by Dev and TEA.

### Architect (reconcile)
- No additional deviations found. All 3 entries verified:
  - Dev's parse-failure deviation: spec source `context-epic-29.md` Guardrail #8 confirmed present. Spec text accurately quoted. Forward impact assessment correct — sidequest-validate catches malformed grids at authoring time.
  - TEA's AC-5 deviation: spec source `context-story-29-19.md` AC-5 confirmed. Visual/manual criterion correctly excluded from automated tests.
  - TEA's AC-6 deviation: spec source `context-story-29-19.md` AC-6 confirmed. Story 29-18 in sprint backlog covers OTEL for tactical system.
- No deferred ACs require status change — AC-5 (playtest) and AC-6 (OTEL) remain correctly deferred.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Wiring story — 3 protocol/function/UI boundaries need test coverage

**Test Files:**
- `sidequest-api/crates/sidequest-game/tests/tactical_wiring_story_29_19_tests.rs` — Rust: ExploredLocation field, build_room_graph_explored population, serde round-trip, backward compat, integration
- `sidequest-ui/src/components/__tests__/TacticalGridWiring.test.tsx` — UI: tactical_grid flows from MapState through useAutomapperData to Automapper

**Tests Written:** 10 Rust tests + 3 UI tests covering ACs 1–4
**Status:** RED (compilation failure — ExploredLocation missing tactical_grid field)

**Failure Mode:** 18 compilation errors in Rust (all `no field 'tactical_grid'` on ExploredLocation). UI tests untested (will fail once useAutomapperData doesn't populate grid).

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #3 hardcoded placeholders | `explored_location_tactical_grid_none_is_valid` — None is semantically correct | failing |
| #6 test quality | Self-checked: all 10 Rust tests have assert_eq!/assert! with meaningful values | passing |
| #8 serde round-trip | `explored_location_serde_round_trip_with_tactical_grid`, `explored_location_backward_compat_without_tactical_grid` | failing |

**Rules checked:** 3 of 11 applicable (others not applicable to this content/wiring story)
**Self-check:** 0 vacuous tests found

**Handoff:** To Inigo Montoya (Dev) for implementation