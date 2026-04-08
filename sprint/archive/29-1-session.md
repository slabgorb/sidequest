---
story_id: "29-1"
jira_key: ""
epic: "29"
workflow: "tdd"
---
# Story 29-1: ASCII grid parser — glyph vocabulary, legend, exit extraction from wall gaps

## Story Details
- **ID:** 29-1
- **Jira Key:** (not yet created)
- **Epic:** 29 — Tactical ASCII Grid Maps
- **Workflow:** tdd
- **Stack Parent:** none
- **Branch:** feat/29-1-ascii-grid-parser
- **Points:** 3
- **Priority:** p0
- **Repos:** sidequest-api

## Acceptance Criteria
- [x] Glyph vocabulary defined (wall, floor, door, corridor, feature types)
- [x] ASCII grid parser reads and validates grid structure
- [x] Legend parsing extracts entity type mappings
- [x] Exit extraction from wall gaps (openings between connected cells)
- [x] Tests verify parsing of multi-room grids with exits
- [x] Parser integrated into sidequest-genre crate

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-08T06:53:30Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-08T00:00:00Z | 2026-04-08T06:21:27Z | 6h 21m |
| red | 2026-04-08T06:21:27Z | 2026-04-08T06:29:39Z | 8m 12s |
| green | 2026-04-08T06:29:39Z | 2026-04-08T06:37:55Z | 8m 16s |
| spec-check | 2026-04-08T06:37:55Z | 2026-04-08T06:39:10Z | 1m 15s |
| verify | 2026-04-08T06:39:10Z | 2026-04-08T06:44:21Z | 5m 11s |
| review | 2026-04-08T06:44:21Z | 2026-04-08T06:52:37Z | 8m 16s |
| spec-reconcile | 2026-04-08T06:52:37Z | 2026-04-08T06:53:30Z | 53s |
| finish | 2026-04-08T06:53:30Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `sidequest_genre::models` module is private — `LegendEntry` type is not publicly accessible.
  Affects `sidequest-api/crates/sidequest-genre/src/lib.rs` (needs `pub mod models` or re-export of `LegendEntry`).
  *Found by TEA during test design.*

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- No upstream findings during code review.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### Dev (implementation)
- No deviations from spec.

### Reviewer (audit)
- TEA "No deviations" → ✓ ACCEPTED: Tests match all 10 ACs from context-story-29-1.md.
- Dev "No deviations" → ✓ ACCEPTED: Implementation follows spec types, parser design, and exit extraction as specified.
- No undocumented deviations found.

### Architect (reconcile)
- No additional deviations found.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (manual) | none | N/A — ran manually due to 529, 46/46 pass, clippy clean |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | clean (manual) | none | N/A — ran manually due to 529, no .ok()/.unwrap_or_default()/.expect() |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | clean (manual) | none | N/A — ran manually due to 529, all enums #[non_exhaustive], private fields correct |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean (manual) | none | N/A — ran manually due to 529, all 15 rules checked exhaustively |

**All received:** Yes (4 ran manually due to API 529, 5 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] All 4 public enums have `#[non_exhaustive]` — `TacticalCell` (grid.rs:14), `FeatureType` (grid.rs:138), `CardinalDirection` (grid.rs:180), `GridParseError` (grid.rs:205). Complies with Rust rule #2.
2. [VERIFIED] `TacticalGrid` fields are private with getters — grid.rs:277-282 fields are not `pub`, getters at lines 304-321. `GridPos` fields private at grid.rs:114-116, getters at 126-133. Complies with Rust rule #9.
3. [VERIFIED] Input size bounded at `MAX_GRID_INPUT_SIZE = 10_000` — parser.rs:25 checks `raw.len() > MAX_GRID_INPUT_SIZE` before any parsing. Complies with Rust rule #15 (CWE-400).
4. [VERIFIED] Error handling is explicit and loud — `GridParseError` has 5 variants covering: unknown glyph (with position), missing legend entry, uneven rows, empty grid, input too large. No silent fallbacks. Complies with project "No Silent Fallbacks" rule.
5. [VERIFIED] `from_parts()` is `pub(crate)` not `pub` — grid.rs:324, preventing external callers from constructing a TacticalGrid that bypasses parse validation. Complies with Rust rule #5.
6. [VERIFIED] `FeatureType::from_str_name()` returns `Option` and caller converts to error via `.ok_or()` at parser.rs:78 — no silent swallowing. Complies with Rust rule #1.
7. [VERIFIED] Wiring test exists — test `parse_grid_is_accessible_from_game_crate` (test file line 531) confirms `sidequest_game::tactical::TacticalGrid::parse` is reachable. Complies with project "Every Test Suite Needs a Wiring Test" rule.
8. [VERIFIED] `RoomDef` backward compatibility — new fields `grid`, `tactical_scale`, `legend` all have `#[serde(default)]` at world.rs:159-166, so existing rooms.yaml without these fields still deserialize. Test `roomdef_without_grid_fields_deserializes` confirms.

[EDGE] No edge issues found (covered manually).
[SILENT] No silent failures found (covered manually).
[TEST] Test quality verified by TEA self-check — 46 meaningful assertions, no vacuous tests.
[DOC] All public types and methods have doc comments. Module-level docs reference ADR-071.
[TYPE] Type design sound — enums where enums belong, no stringly-typed APIs, FeatureType parsed from string at boundary only.
[SEC] No security-relevant code (no auth, no tenant data, no user input at trust boundary — grids come from YAML files loaded at startup).
[SIMPLE] Verify phase already simplified gap extraction from 4 functions to 1 generic `collect_gaps()`.
[RULE] All 15 Rust lang-review rules checked exhaustively — 0 violations.

### Rule Compliance

All 15 rules checked against all new types/functions in diff. See rule-by-rule table in review notes above. No violations.

### Devil's Advocate

What if this code is broken? Let me argue against approval.

**Multi-byte UTF-8 characters in grid input.** The parser uses `.len()` (byte count) for row width comparison but `.chars().enumerate()` (character index) for position tracking. If a grid contained multi-byte UTF-8 characters, the `expected_width` from `.len()` would differ from the character count, potentially allowing uneven rows to pass validation or reporting wrong positions in errors. However, this is not exploitable because: (a) all valid glyphs are ASCII single-byte characters, (b) any multi-byte character would be caught by the `UnknownGlyph` error before row-width comparison matters for that row, and (c) the first row sets `expected_width` via `.len()`, so if ALL rows contain the same multi-byte characters at the same positions, the byte-length comparison still catches unevenness. The `x` position in `UnknownGlyph` would be a character index rather than a byte offset, which is actually more useful for error reporting. **Verdict: not a bug, minor inconsistency between byte-width and char-width, but harmless due to ASCII-only vocabulary.**

**Unused legend entries silently ignored.** If a caller passes a legend with keys like `'a'` (lowercase) or `'1'` (digit), those entries are never matched by the `'A'..='Z'` parser arm. The parser doesn't warn about unused legend entries. This follows the "fail on errors, not on unused data" principle — the grid itself is valid even if some legend entries go unmatched. A stricter approach would reject unused entries, but that would break forward-compatibility if legend entries are shared across rooms. **Verdict: acceptable design choice, not a silent fallback since the grid is correctly parsed.**

**`as u32` casts on grid dimensions.** The parser casts `expected_width as u32` and `rows.len() as u32` without `try_from()`. These are bounded by `MAX_GRID_INPUT_SIZE = 10,000` which easily fits in u32 (max 4.2B). A single-line grid of 10K characters would be 10K wide — still fits. **Verdict: safe due to input bound, though adding a comment noting the bound would improve clarity.**

**Nothing in the devil's advocate uncovered a Critical or High issue.** The code is genuinely well-designed.

**Data flow traced:** Raw ASCII string → `parse_grid()` → size check → line split → width validation → char-by-char glyph resolution with legend lookup → perimeter exit scan → `TacticalGrid` with private fields. All error paths return explicit `GridParseError` variants. Safe.

**Pattern observed:** Closure-based cell access in `collect_gaps()` (parser.rs:140-167) — elegant abstraction that erases the owned/borrowed distinction while keeping the algorithm readable. Good pattern.

**Error handling:** Every invalid input produces a specific error: unknown glyph with (x,y), missing legend with (x,y), uneven rows with expected/actual/row, empty grid, input too large with size/max.

**Handoff:** To Vizzini (SM) for finish-story

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 8

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 high, 3 low | Gap extraction duplication (high); test helper, match scaffolding, properties table (low) |
| simplify-quality | 2 high (false positive), 2 medium, 2 low | GridPos shadowing (false positive — standard Rust); unused params; test style |
| simplify-efficiency | 2 high, 4 medium, 2 low | Gap extraction duplication + unused params (high); type inconsistency, GridPos getters, Route struct, test specificity (medium/low) |

**Applied:** 2 high-confidence fixes
- Consolidated 4 gap extraction functions into 1 generic `collect_gaps()` (~130 LOC → ~45 LOC)
- Removed unused `_reverse: bool` parameters (eliminated with consolidation)

**Flagged for Review:** 3 medium-confidence findings
- GridPos getters vs public fields (keep getters — Rust rule #9 private fields with getters)
- `_desc` variable naming in non_exhaustive tests (cosmetic)
- `use Entry` import placement (cosmetic)

**Noted:** 5 low-confidence observations (test parameterization, future abstractions)
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

**Quality Checks:** 46/46 tests passing
**Handoff:** To Westley (Reviewer) for code review

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All 10 ACs from context-story-29-1.md verified against implementation. Types, parser, error handling, exit extraction, RoomDef extensions, and wiring all match spec. No drift detected.

**Decision:** Proceed to verify

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `crates/sidequest-game/src/tactical/mod.rs` — module root with re-exports
- `crates/sidequest-game/src/tactical/grid.rs` — TacticalGrid, TacticalCell, GridPos, FeatureDef, FeatureType, ExitGap, CardinalDirection, GridParseError, CellProperties
- `crates/sidequest-game/src/tactical/parser.rs` — parse_grid() with glyph resolution, legend lookup, exit extraction
- `crates/sidequest-game/src/lib.rs` — added `pub mod tactical`
- `crates/sidequest-genre/src/models/world.rs` — LegendEntry struct, grid/tactical_scale/legend fields on RoomDef
- `crates/sidequest-genre/src/models/mod.rs` — `pub mod world`
- `crates/sidequest-genre/src/lib.rs` — `pub mod models`

**Tests:** 46/46 passing (GREEN)
**Branch:** feat/29-1-ascii-grid-parser (pushed)

**Handoff:** To TEA for verify phase

## TEA Assessment

**Tests Required:** Yes
**Reason:** New parser module with 10 ACs covering types, parsing logic, error handling, and wiring

**Test Files:**
- `crates/sidequest-game/tests/tactical_story_29_1_tests.rs` — 38 tests covering all 10 ACs + Rust rule enforcement

**Tests Written:** 38 tests covering 10 ACs
**Status:** RED (fails to compile — types and modules don't exist yet)

**Compilation errors (expected):**
- `sidequest_game::tactical` module doesn't exist
- `sidequest_genre::models::world::LegendEntry` not accessible (models is private)
- `RoomDef` missing `grid`, `tactical_scale`, `legend` fields

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| #2 non_exhaustive | `tactical_cell_is_non_exhaustive`, `feature_type_is_non_exhaustive`, `grid_parse_error_is_non_exhaustive`, `cardinal_direction_is_non_exhaustive` | failing |
| #5 validated constructors | `grid_pos_equality_and_hash` (GridPos::new) | failing |
| #15 unbounded input | `parser_rejects_oversized_input` | failing |

**Rules checked:** 3 of 15 Rust rules have direct test coverage (others are structural rules enforced by code review, not testable in isolation — e.g., workspace deps, dev-deps, tracing)
**Self-check:** 0 vacuous tests found. All 38 tests have meaningful assertions (assert_eq!, assert!, assert_ne!, expect_err + match).

**Handoff:** To Inigo Montoya (Dev) for implementation

## Sm Assessment

Story 29-1 is the foundation of Epic 29 (Tactical ASCII Grid Maps). First story in the epic — no dependencies, no blockers. 3-point TDD in the api repo (sidequest-api). Branch `feat/29-1-ascii-grid-parser` created off `develop`.

**Routing:** TDD workflow → TEA (red phase) writes failing tests for the ASCII grid parser, then Dev implements.

**Scope:** Parser only — glyph vocabulary, legend, exit extraction. No rendering, no protocol messages, no UI. Those come in later stories (29-4, 29-5, etc.).