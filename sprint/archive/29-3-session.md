---
story_id: "29-3"
jira_key: "none"
epic: "29"
workflow: "trivial"
---

# Story 29-3: Author ASCII grids for Mawdeep 18 rooms — non-rectangular shapes, template library seed

## Story Details

- **ID:** 29-3
- **Jira Key:** none (personal project)
- **Epic:** 29 — Tactical ASCII Grid Maps
- **Workflow:** trivial (phased: setup → implement → review → finish)
- **Points:** 5
- **Priority:** p0
- **Stack Parent:** none

## Workflow Tracking

**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-04-08T09:35:33Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-08T09:04:54Z | 2026-04-08T09:07:11Z | 2m 17s |
| implement | 2026-04-08T09:07:11Z | 2026-04-08T09:26:14Z | 19m 3s |
| review | 2026-04-08T09:26:14Z | 2026-04-08T09:35:33Z | 9m 19s |
| finish | 2026-04-08T09:35:33Z | - | - |

## Story Context

### Goal

Author 18 ASCII grid definitions for the Mawdeep dungeon (caverns_and_claudes genre pack). Designs should include non-rectangular room shapes to serve as seed templates for the template library (29-15). Rooms will be validated against the parser (29-1) and validator (29-2), then rendered as tactical grids in later stories (29-4, 29-8).

### Upstream Dependencies

- **29-1 (done):** ASCII grid parser exists — glyph vocabulary (`#`, `|`, `-`, `+` for walls; `.` for floor; `@` for exits; `*` for special markers), legend extraction, exit detection from wall gaps.
- **29-2 (done):** Tactical grid validation exists — perimeter closure, flood fill connectivity, exit matching. Can be used to validate authored grids during authoring.

### Mawdeep Context

Mawdeep is a cavern dungeon in the caverns_and_claudes world. It should have:
- Varied room shapes: rectangular, L-shaped, circular/octagonal, triangular, irregular/jaquayed
- 18 rooms total with interconnected layout (not isolated)
- Non-rectangular designs to demonstrate the parser's capability beyond simple rectangles
- Clear exits marked with `@` at wall gaps where rooms connect
- Legend entries defining special markers (encounter zones, treasure, traps, etc.)

### Acceptance Criteria

Each grid definition should:
1. Be valid ASCII art (parseable by the 29-1 parser)
2. Pass validation from 29-2 (perimeter closure, flood fill)
3. Include at least 2-3 non-rectangular room designs among the 18
4. Have clear exit markers (`@`) at all room connections
5. Include legend with room purpose/description and any special markers
6. Be placed in sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms/
7. Include a manifest or index mapping room names to ASCII files

### Definition Locations

Grids will be authored in YAML or text format:
- Location: `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms/`
- Format: Individual `.txt` files per room (ASCII grid + legend), or single YAML manifest with embedded grids
- Reference: See 29-1/29-2 for glyph vocabulary and validation requirements

## Delivery Findings

No upstream findings.

### Dev (implementation)
- **Gap** (non-blocking): Session AC-6 says grids should be "placed in rooms/" directory. The RoomDef struct expects grid as a field on the room definition, so embedded grids in rooms.yaml is the correct format. No rooms/ directory needed.
  Affects `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml` (already correct).
  *Found by Dev during implementation.*
- **Gap** (non-blocking): Session AC mentions `@` as exit marker glyph. The actual parser (`sidequest-game::tactical::parser`) uses perimeter floor-cell gap detection — `@` is not a valid glyph. Exits are detected as `.` cells on grid edges.
  Affects `context-story-29-3` (exit marker convention section is incorrect).
  *Found by Dev during implementation.*
- **Gap** (non-blocking): rooms.yaml header says "18 rooms" but file contains 19 room definitions (full_belly is the 19th). Grids authored for all 19.
  Affects `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml` (comment updated to 19).
  *Found by Dev during implementation.*

### Reviewer (code review)
- No upstream findings during code review.

## Impact Summary

**Upstream Effects:** No upstream effects noted
**Blocking:** None

## Design Deviations

### Dev (implementation)
- **Embedded grids in rooms.yaml instead of separate files in rooms/ directory** → ✓ ACCEPTED by Reviewer: Correct — RoomDef.grid is a field on the struct. Separate files would require new loader code. This IS the format the data model expects.
  - Spec source: context-story-29-3, AC-6
  - Spec text: "Be placed in sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms/"
  - Implementation: Grids embedded as `grid:` field in existing rooms.yaml
  - Rationale: RoomDef struct has `grid: Option<String>` field — the loader expects grids in the room definition, not as separate files. A rooms/ directory would require new loading code outside story scope.
  - Severity: minor
  - Forward impact: none — this IS the expected format per the data model

- **19 rooms instead of 18** → ✓ ACCEPTED by Reviewer: The file has 19 room definitions. Authoring grids for all of them is correct.
  - Spec source: context-story-29-3, title
  - Spec text: "Author ASCII grids for Mawdeep 18 rooms"
  - Implementation: Authored grids for all 19 rooms in rooms.yaml (full_belly was already defined)
  - Rationale: The rooms.yaml file has 19 room definitions. Skipping one would leave an incomplete set.
  - Severity: trivial
  - Forward impact: none — more content, not less

- **5 non-rectangular rooms instead of suggested 2-3** → ✓ ACCEPTED by Reviewer: Exceeds minimum, thematically appropriate for the Glutton Below organic dungeon.
  - Spec source: context-story-29-3, AC-3
  - Spec text: "Include at least 2-3 non-rectangular room designs"
  - Implementation: 5 rooms use void-cornered shapes (antechamber, acid_pool, warren, maw_chamber, full_belly)
  - Rationale: The organic Glutton Below theme benefits from more irregular shapes. Exceeds minimum, does not exceed scope.
  - Severity: trivial
  - Forward impact: none — more template variety for 29-15

### Reviewer (audit)
- No undocumented deviations found.

## Implementation Notes

### Room Count & Types

18 rooms total. Suggested breakdown to test parser capabilities:
- **Rectangular (6):** Standard 10x10, 15x8, 8x12 layouts
- **L-shaped (2):** Connected chambers with offset corridors
- **Circular/Octagonal (2):** Non-grid-aligned shapes (using ASCII approximation)
- **Irregular/Jaquayed (3):** Asymmetrical, multi-level feel, dead ends, complex connectivity
- **Corridor/Hallway (3):** Connecting passages, turning sections
- **Large chamber (1):** Boss arena or gathering space
- **Treasury/Vault (1):** Smaller high-value room

### Exit Marker Convention

Exits use `@` at wall gaps where rooms connect:
```
#########
#.......#
#.......@
#########
```
The `@` marks where an exit leads to an adjacent room (up, down, left, right).

### Validation Workflow

Use the validator (29-2) to ensure each grid:
- Has closed perimeter (all walls intact except exits)
- Has connected interior (flood fill from first floor cell reaches all floor cells)
- Has matching exits (exit markers at both rooms' boundaries)

Run via CLI (once it's integrated):
```
sidequest-validate grid <file.txt>
```

### Author Notes

- Start with 2-3 rectangular grids to ensure basic format is correct
- Then introduce non-rectangular shapes to push the parser
- Document any special markers used in the legend (e.g., `*` for altar, `$` for treasure, `T` for trap)
- Keep grid dimensions manageable for ASCII (15x15 max per room) to avoid rendering issues

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 1 (full_belly sealed south wall) | dismissed 1 — intentional dead-end room with 1 exit on N wall only |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 6 | reviewer-type-design | Yes | clean | none | N/A — no code changes |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 (mouth row width claim) | dismissed 1 — miscounted: `#` + 11 dots = 12 chars, verified programmatically |

**All received:** Yes (4 returned, 5 disabled via settings; 2 findings, both dismissed with evidence)
**Total findings:** 0 confirmed, 2 dismissed (with rationale), 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

### Observations

1. [VERIFIED] Schema deserialization — `sidequest-validate` reports 0 errors for caverns_and_claudes. All `grid`, `tactical_scale`, `legend` fields match `RoomDef` struct at `world.rs:150-177`.
2. [VERIFIED] Grid dimensions — All 19 grids match `size[0] * 4` columns × `size[1] * 4` rows. Verified programmatically with Python script.
3. [VERIFIED] Exit clockwise ordering — All 19 rooms have exit gaps in N→E→S→W order matching `exits[]` array. Verified with script mirroring parser's `extract_exits()` logic at `parser.rs:121`.
4. [VERIFIED] Exit gap width compatibility — All cross-room connections use 2-cell gaps on both sides. Rule 8 (ExitWidthMismatch) will not fire.
5. [VERIFIED] Flood fill connectivity — All 19 rooms pass 4-directional flood fill. No isolated regions.
6. [VERIFIED] Perimeter closure — No walkable cell adjacent to void without wall between.
7. [VERIFIED] Feature type validity — All legend type strings (`atmosphere`, `hazard`, `interactable`) valid per `FeatureType::from_str_name()` at `grid.rs:138-148`.
8. [VERIFIED] Legend completeness — All uppercase glyphs have legend entries; all legend entries are placed in grids.
9. [VERIFIED] No data loss — Diff shows only additions (222 ins, 1 del comment update). All existing fields intact.
10. [VERIFIED] YAML round-trip safe — No trailing whitespace, no tabs, round-trip through yaml.safe_load/dump preserves content.
11. [LOW] 3 room pairs share rectangular shell shapes after normalizing features (cistern/vault, hall/stomach, gullet_passage/marrow_hall). Features differ; not a defect.
12. [LOW] 8/19 rooms are plain floor-only (no features). These are corridors and transition rooms where features would be gratuitous.

### Rule Compliance

No code changes — no lang-review rules apply. YAML content validates against existing `RoomDef` schema. CLAUDE.md rules checked:
- **No stubs:** All 19 grids are substantive, thematically appropriate content — not placeholders. ✓
- **No silent fallbacks:** Parser fails loudly on malformed grids (`GridParseError`). ✓
- **Wiring:** Data consumed by existing schema; renderer wiring planned in 29-4/29-8. ✓

[EDGE] N/A — disabled via settings
[SILENT] full_belly sealed south wall — dismissed: room has 1 exit (N only), dead-end by design
[TEST] N/A — disabled via settings
[DOC] N/A — disabled via settings
[TYPE] Clean — no code changes
[SEC] N/A — disabled via settings
[SIMPLE] N/A — disabled via settings
[RULE] mouth row width claim — dismissed: `#...........` = `#` + 11 dots = 12 chars, confirmed by `len()` = 12

### Devil's Advocate

What if these grids are broken in ways my validation missed? The most dangerous scenario: the Python validation scripts I wrote don't perfectly mirror the Rust parser. If `is_exit_cell()` in Rust checks something subtly different than my `== '.'` check, exits could be miscounted. But I verified against the source: `parser.rs:113-115` matches only `TacticalCell::Floor`, and the parser maps `.` to `Floor` at line 66. My check is accurate.

Could YAML's `|` block scalar introduce invisible characters? A literal block preserves content exactly, including trailing spaces. But Python's `yaml.safe_load` would also preserve them, and my whitespace check found none. Could there be a byte-order mark or non-ASCII character? The file is authored by Claude Code which outputs UTF-8 without BOM.

Could the grid order in the YAML file affect parsing? No — rooms are loaded as a list, each parsed independently. The grid is a string field on each room.

What if `tactical_scale: 4` is too small? The largest room [3,3] produces 12×12 grids — well under the 10,000 byte `MAX_GRID_INPUT_SIZE`. The smallest [1,1] at 4×4 has 2×2 interior floor — barely enough for one token but correct for a chute. If gameplay testing reveals scale 4 is too cramped, it's a single-field change.

Could a malicious YAML editor inject code? The grid is parsed character-by-character with a strict whitelist (`parser.rs:65-91`). Unknown glyphs produce hard errors. No eval, no template expansion.

The devil's advocate finds no unaddressed risks. The grids are well-formed, correctly validated, and consume an existing schema.

**Data flow traced:** rooms.yaml → `serde_yaml::from_reader` → `RoomDef.grid` → `TacticalGrid::parse()` → `validate_tactical_grid()` (safe because each step has strict validation)
**Pattern observed:** Consistent 2-cell exit gaps across all 19 rooms at `rooms.yaml` — good pattern for cross-room compatibility
**Error handling:** Parser fails loudly on any malformed input — `GridParseError` variants cover all failure modes at `grid.rs:72-118`
**Handoff:** To SM (Vizzini) for finish-story

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-content/genre_packs/caverns_and_claudes/worlds/mawdeep/rooms.yaml` — Added tactical_scale (4), grid, and legend fields to all 19 room definitions

**Grids Authored:** 19/19 rooms
- 14 rectangular, 5 non-rectangular (void-cornered)
- 7 rooms with feature legends (V, A, W, T, B, M)
- All grids use 2-cell exit gaps for cross-room compatibility
- tactical_scale: 4 throughout (max grid 12×12)

**Validation:** All 19 rooms pass:
- YAML schema validation (sidequest-validate: 0 errors)
- Dimension matching (size × tactical_scale)
- Row width uniformity
- Exit gap count matches exits[] count
- Flood fill connectivity (all walkable cells reachable)
- Perimeter closure (no walkable cells adjacent to void)

**Branch:** feat/29-3-mawdeep-ascii-grids (pushed)

**Handoff:** To review phase (Westley)

## Sm Assessment

**Story 29-3** is ready for implementation. Content authoring story — no code changes, pure ASCII grid + YAML authoring in sidequest-content.

- **Dependencies satisfied:** 29-1 (parser) and 29-2 (validator) are both complete
- **Scope is clear:** 18 rooms for Mawdeep, mix of rectangular and non-rectangular shapes
- **Repo:** sidequest-content only, branch `feat/29-3-mawdeep-ascii-grids` on develop
- **Risk:** Low — content authoring with existing validation tooling
- **Handoff to:** Dev (Inigo Montoya) for implementation phase