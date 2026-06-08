---
story_id: "100-2"
jira_key: ""
epic: "100"
workflow: "tdd"
---
# Story 100-2: Phase 1 — Lore generic-YAML section projection + classify() firewall reuse (security-bearing: no keeper field crosses JSON)

## Story Details
- **ID:** 100-2
- **Jira Key:** (none)
- **Workflow:** tdd
- **Stack Parent:** none

## Branch Information
- **Repo:** sidequest-server
- **Branch:** feat/100-2-lore-generic-yaml-projection
- **Branch Strategy:** gitflow (feat/{STORY_ID}-{SLUG})

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-06-08T22:32:21Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-08T18:30:00Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The story/epic context YAML carried no acceptance criteria. TEA derived the AC set from the spec (`2026-06-08-reference-pages-react-migration-design.md`, Load-Bearing Constraint C1 + Testing Strategy) and the shipped map-slice plan's explicit "deferred to the generic-YAML slice" note (`2026-06-08-reference-lore-projection-api-map-slice.md` line 602). Affects `sprint/context/context-story-100-2.md` (ACs should be backfilled from the spec). *Found by TEA during test design.*
- **Question** (non-blocking): The normalized node-tree JSON shape is an Open Question in the spec (line 287, "pinned in Phase 1"). TEA pinned a concrete shape in the tests (`{"id","label","node"}` with `dict`/`list`/`scalar` node types) so Dev has a target, but flagged the shape assertions as reconcilable with Architect; the *firewall* assertions are non-negotiable. Affects `sidequest-server/sidequest/server/reference_projection.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): The HTML walk's firewall lives across two layers — `classify()` in `reference_visibility.py` AND the renderer-layer suppressions (`_is_devnote`, leading-underscore keys) in `reference_renderer.py`. Dev should reuse `_is_devnote` from `reference_renderer.py` rather than re-deriving the dev-note marker list, to avoid drift. Affects `sidequest-server/sidequest/server/reference_projection.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): TEA's RED handoff states "17 tests" but the test file defines exactly 16 `def test_` functions; all 16 pass. No test is missing — the count in the handoff/assessment is off by one. Affects `.session/100-2-handoff-red.md` (count) — cosmetic, no action needed beyond noting it. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): `classify()` uses fixed-depth KEEPER patterns (`_match_pattern` requires equal length), so a keeper key nested *deeper* than its catalogued pattern would not be caught. Identical behavior to the shipped HTML renderer (`reference_renderer.py`), so not a regression here — but the firewall whitelist owner should confirm all real keeper shapes are catalogued at their actual depth. Affects `sidequest/server/reference_visibility.py` (KEEPER pattern completeness). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): The generic-YAML projection path does not call `_log_unknown_once` (the renderer's stderr log-once dedup) on UNKNOWN drops. The load-bearing OTEL `reference.unknown_field` WARN span still fires, so the GM-panel lie-detector path is intact; this is a stderr-convenience parity gap only. Affects `sidequest/server/reference_projection.py`. *Found by Reviewer during code review.*


## Impact Summary

**Delivery Findings compiled into impact assessment:**

### Finding Categories
- **1 Gap (non-blocking):** Missing acceptance criteria in story context YAML; derived from spec. No implementation impact.
- **1 Question (non-blocking):** Open question on node-tree JSON shape — resolved by tests and implementation. Shape is production-ready.
- **3 Improvements (non-blocking):** Firewall completeness (KEEPER pattern depth), stderr convenience parity (UNKNOWN logging), reuse of visibility markers. All non-blocking; marker reuse was completed by implementation.

### Load-Bearing Correctness
- **Firewall integrity:** classify() is the single gate per spec C1 ("no keeper field may cross JSON boundary"). Verified: KEEPER drops before recursion (no descendant leak); UNKNOWN fires OTEL WARN spans (No Silent Fallbacks); leading-underscore + devnote markers suppressed at renderer parity. Test suite includes adversarial probe (naive vs. correct projector) — security tests fail on naive, pass on correct.
- **Wiring complete:** build_lore_projection → build_generic_yaml_section / _project_node → reference_routes.py:139 REST endpoint → React. End-to-end path verified in live production code.
- **Test coverage:** 16/16 new tests pass (5 groups: non-keeper pass-through 3x, keeper exclusion 8x, spoiler payload leak 1x, classify reuse 1x, endpoint wiring 3x). 7 sibling tests green (reference_projection.py). All tests + lint clean.

### Phase Handoff Summary
- **TEA → Dev:** 16 tests pinning acceptance criteria + test shape (17 count was off by one — cosmetic, no test missing).
- **Dev → Reviewer:** 16/16 tests passing, firewall reuse verified, sibling suite still green, lint clean.
- **Reviewer → SM:** APPROVED, data flow traced, 8 verification observations (all VERIFIED GOOD or non-blocking), no undocumented deviations.

### Non-Blocking Items for Backlog
1. **Firewall pattern depth audit:** classify() uses fixed-depth patterns (not a regression — matches HTML renderer). Recommend firewall whitelist owner (reference_visibility.py) audit KEEPER shapes to confirm all real nested keys are catalogued.
2. **Acceptance criteria backlog:** sprint/context/context-story-100-2.md should be backfilled with the ACs derived from the spec.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Node-tree JSON shape pinned by TEA:** Spec left the normalized node-tree shape as Open Question #2 ("pinned in Phase 1"). Tests pin `section = {"id","label","node"}` and node = `dict{type,entries[{key,label,node}]}` / `list{type,items[]}` / `scalar{type,value}`. Reason: Dev needs a concrete target; shape is reconcilable with Architect (firewall assertions are not). Documented in the test module docstring.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Security-bearing feature (no keeper field may cross the JSON boundary, spec C1). This is the load-bearing test set the map slice explicitly deferred.

**Test Files:**
- `sidequest-server/tests/server/test_reference_generic_yaml_projection.py` — generic-YAML section projection + classify() firewall reuse contract.

**Tests Written:** 17 tests across 5 groups, covering the derived ACs:
- AC1 Non-keeper fields pass through (3): public dict → node tree; native JSON scalar types survive; nested dict/list recurse.
- AC2 Keeper fields excluded — the firewall, spec C1 (8): keeper subtree dropped entirely; keeper leaf dropped with siblings surviving; whole keeper file → None; unknown stem → None + WARN span; unknown child dropped + warns; leading-underscore key suppressed; devnote marker value suppressed; devnote marker in list suppressed.
- AC3 Representative spoiler-bearing payload leaks no keeper token (1).
- AC4 classify() reused, not reimplemented (1, monkeypatch spy on the imported symbol).
- AC5 Endpoint/document wiring (3): generic-YAML sections appear in the full lore document; map ordered before generic sections; keeper files (tropes/seed_tropes) excluded end-to-end.

**Validation:** Test logic verified against an isolated throwaway probe (naive no-firewall projector vs. correct full-firewall projector) — security tests fail against naive, all pass against correct. Production source untouched. Lint clean (`ruff check` passes). Sibling shipped suite (`test_reference_projection.py`) still green (validates conftest/span fixture usage).

**Status:** RED (collection-time ImportError: `build_generic_yaml_section` does not exist — the cleanest RED for a not-yet-implemented symbol).

**Handoff:** To Dev for implementation. See `.session/100-2-handoff-red.md`.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/reference_projection.py` — added `build_generic_yaml_section()` + private `_project_node()` recursive walk; wired generic-YAML sections into `build_lore_projection()` after the map section.

**Tests:** 16/16 passing (GREEN) — `tests/server/test_reference_generic_yaml_projection.py`. (TEA's handoff said "17 tests"; the file defines exactly 16 `def test_` functions — a TEA counting discrepancy, not a missing test.)
**Branch:** feat/100-2-lore-generic-yaml-projection (pushed)

**Notes:**
- `classify()` is imported by name and used as the single firewall — no copied KEEPER/PUBLIC tables (Group 4 spy test passes).
- Reused `_is_devnote` + `_humanize_label` + `EXCLUDED_FILES`/`LORE_WORLD_FILES` from `reference_renderer.py` per TEA's drift finding — did not re-derive markers.
- Wiring verified: `build_lore_projection` is consumed by the live `reference_routes.py:139` endpoint; generic sections flow through it.
- Sibling suite `test_reference_projection.py` still green (7 passed). Lint clean.

**Open Questions answered by implementation:** Used a presenter-free pure walk for Phase 1 (the tests only assert firewall + node tree). OTEL at projection time is the `unknown_field` WARN (root + child) and `devnote_suppressed` spans, reusing the renderer's span family.

**Handoff:** To review phase.

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** parsed world YAML (`build_lore_projection` reads `LORE_WORLD_FILES`) → `build_generic_yaml_section` → `_project_node` recursive walk → JSON section dict → `reference_routes.py:139` REST response → React. Safe because every dict key and list-of-dict item is gated by `classify(file_stem, key_path)` before it can enter the node tree; KEEPER `continue`s before recursing (whole subtree dropped), UNKNOWN drops + fires WARN span.
**Pattern observed:** classify() imported by name (`reference_projection.py:30`) and used as the single firewall — verified by Group 4 monkeypatch spy (`test_classify_is_the_gate_not_a_reimplementation`). No copied KEEPER/PUBLIC tables. Reuses `_is_devnote`/`_humanize_label`/`EXCLUDED_FILES`/`LORE_WORLD_FILES` from `reference_renderer.py` (no marker re-derivation).
**Error handling:** UNKNOWN stems/fields fire `reference.unknown_field` WARN spans (`reference_projection.py:135,190`) — No Silent Fallbacks honored; nothing swallowed. `yaml.safe_load` returning None is skipped (`:234`), correct for empty files.
**Observations (8):**
1. [VERIFIED GOOD] KEEPER subtree dropped entirely — `continue` precedes recursion, so no descendant can leak (`:132`). Test + adversarial probe confirm.
2. [VERIFIED GOOD] Keeper-leaf-with-surviving-siblings works at correct depth via `('*',)` list-of-dict wildcard (`:163`).
3. [VERIFIED GOOD] File-root KEEPER → None (whole keeper file) and UNKNOWN → None + WARN (`:186-194`).
4. [VERIFIED GOOD] Devnote/leading-underscore suppression is STRONGER than the HTML renderer — suppresses devnotes in mixed lists too, not only pure-scalar lists. No leak.
5. [VERIFIED GOOD] Native JSON scalar types survive (3/1.5/True/None) — correct for React (not pre-stringified).
6. [VERIFIED GOOD] Wiring confirmed: `build_lore_projection` consumed by live `reference_routes.py:139`; map ordered before generic sections.
7. [LOW, non-blocking] `classify()` fixed-depth patterns: a keeper key nested deeper than its catalogued pattern would not match (`_match_pattern` requires equal length). Identical to the shipped HTML renderer — a firewall whitelist-completeness property, NOT a regression in this story.
8. [LOW, non-blocking] Projection omits the renderer's `_log_unknown_once` stderr dedup. The load-bearing OTEL WARN span still fires; stderr convenience only.

**Deviation audit:** Dev test-count note (16 vs 17) — ACCEPTED, cosmetic. TEA node-tree shape pin — ACCEPTED, reconcilable, firewall assertions intact. No undocumented deviations.

**Gates:** 23/23 tests green (16 new + 7 sibling), ruff clean, pyright 0 errors, working tree clean, 2 files changed (no scope creep).

**Handoff:** To SM for finish-story. PR #764 → develop: https://github.com/slabgorb/sidequest-server/pull/764