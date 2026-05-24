---
story_id: "61-5"
jira_key: null
epic: "61"
workflow: "tdd"
---
# Story 61-5: Architecture gate: new snapshot field must land a bounding decision (test fails otherwise)

## Story Details
- **ID:** 61-5
- **Title:** Architecture gate: new snapshot field must land a bounding decision (test fails otherwise)
- **Workflow:** tdd
- **Points:** 3
- **Priority:** p1
- **Stack Parent:** none (depends on 61-7 for _PHASE_C_PROJECTIONS stability)

## Story Context

This story introduces a pydantic-reflection test that enforces snapshot field governance. Every new top-level field on GameSnapshot must declare which category it falls into — drop, projection, or bounded-by-construction — or the test fails at build time.

**Why it matters:** ADR-110 / epic-61 discovered that unchecked snapshot growth into the narrator prompt burns tokens ($313 in 48h, story 61-2 fixed the data plane but this story gates future regressions). The "review at every PR" rule is aspirational without test enforcement. This test makes it mandatory.

**What it does:**
1. Introduce two new registries in session_helpers.py:
   - `_PHASE_C_PROJECTIONS` — fields that are present-in-full (not dropped) but may grow; require bounded projection logic
   - `_BOUNDED_BY_CONSTRUCTION` — fields whose growth is limited by their own structure (scalars, enums, fixed-size collections)

2. Add a test in tests/server/test_snapshot_field_governance.py that:
   - Enumerates GameSnapshot.model_fields via pydantic reflection
   - Asserts every field is in exactly one of: _PHASE_B_DROP_FIELDS, _PHASE_C_PROJECTIONS, or _BOUNDED_BY_CONSTRUCTION
   - Uses named-registry reflection (not source-text-grep)
   - Mirrors the tripwire pattern from tests/dungeon/test_setpiece_attach_wiring.py

3. Closes ADR-110 amendment loop: "reviewed at every PR" → test-enforced

## Prerequisite
Story 61-7 must land first (unify _npc_in_scene predicate) so _PHASE_C_PROJECTIONS reflects the unified behavior, avoiding encoding a known divergence.

## Acceptance Criteria
1. _PHASE_C_PROJECTIONS is introduced explicitly in session_helpers.py (named, enumerable registry)
2. _BOUNDED_BY_CONSTRUCTION is introduced explicitly in session_helpers.py (named, enumerable registry)
3. test_snapshot_field_governance.py enumerates all GameSnapshot.model_fields and asserts coverage in exactly one registry
4. Test uses pydantic model_fields reflection, not source-text-grep
5. Test fails loudly if any field is missing from all three registries
6. Test fails loudly if any field appears in more than one registry
7. Existing test suite passes unchanged (no new test failures)

## SM Assessment

**Story shape:** TDD architecture-gate test in sidequest-server only. Single repo, single new test file plus two new named registries in `session_helpers.py`. No client/content/daemon touchpoints.

**Prerequisites:** 61-7 already merged on develop, so `_PHASE_C_PROJECTIONS` can reflect the unified `_npc_in_scene` predicate without encoding known divergence. Develop is at 921694a (synced 2026-05-24).

**Risk:** Low. The tripwire pattern at `tests/dungeon/test_setpiece_attach_wiring.py` is the explicit model — TEA can mirror its shape. Banned anti-pattern (source-text-grep on `session_helpers.py`) is called out in the description and reinforced by sidequest-server `CLAUDE.md` ("No Source-Text Wiring Tests").

**Handoff to TEA:** Write the failing reflection test first against the current `GameSnapshot` field set. Expect it to red-fail loudly enumerating every field not yet placed in a registry; that list becomes the implementation map for the green phase. Confirm `_PHASE_B_DROP_FIELDS` continues to be the single drop-list source of truth (memory: 4-field drop list previously missed `room_states`/`npcs`/`journal` — this gate is the long-term fix for that class of regression).

**No Jira.** Personal project policy — sprint YAML only.

## Workflow Tracking
**Workflow:** tdd
**Phase:** review
**Phase Started:** 2026-05-24T11:03:02Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-24T10:25:26Z | 2026-05-24T10:27:50Z | 2m 24s |
| red | 2026-05-24T10:27:50Z | 2026-05-24T10:32:13Z | 4m 23s |
| green | 2026-05-24T10:32:13Z | 2026-05-24T10:39:09Z | 6m 56s |
| spec-check | 2026-05-24T10:39:09Z | 2026-05-24T10:41:22Z | 2m 13s |
| verify | 2026-05-24T10:41:22Z | 2026-05-24T10:44:15Z | 2m 53s |
| review | 2026-05-24T10:44:15Z | 2026-05-24T10:51:33Z | 7m 18s |
| green | 2026-05-24T10:51:33Z | 2026-05-24T10:57:49Z | 6m 16s |
| spec-check | 2026-05-24T10:57:49Z | 2026-05-24T10:59:32Z | 1m 43s |
| verify | 2026-05-24T10:59:32Z | 2026-05-24T11:03:02Z | 3m 30s |
| review | 2026-05-24T11:03:02Z | - | - |

## TEA Assessment

**Tests Required:** Yes
**Reason:** This story IS the test — an architecture-gate reflection test that enforces a previously aspirational ADR-110 policy.

**Test Files:**
- `sidequest-server/tests/server/test_snapshot_field_governance.py` — 6 tests, reflection-based tripwire on `GameSnapshot.model_fields`

**Tests Written:** 6 tests covering 7 ACs
**Status:** RED (6/6 failing, ready for Dev)

### Test → AC Mapping

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 (`_PHASE_C_PROJECTIONS` introduced explicitly) | `test_phase_c_projections_registry_exists`, `test_every_snapshot_field_is_categorized` | failing |
| AC2 (`_BOUNDED_BY_CONSTRUCTION` introduced explicitly) | `test_bounded_by_construction_registry_exists`, `test_every_snapshot_field_is_categorized` | failing |
| AC3 (enumerate `model_fields` + assert coverage in exactly one registry) | `test_every_snapshot_field_is_categorized`, `test_no_field_in_multiple_registries` | failing |
| AC4 (pydantic reflection, not source-text grep) | All 6 — `GameSnapshot.model_fields.keys()` is the runtime source; no `read_text()` anywhere | failing |
| AC5 (fail loudly if a field missing from all three registries) | `test_every_snapshot_field_is_categorized` — diagnostic lists the unclassified field names | failing |
| AC6 (fail loudly if a field appears in more than one) | `test_no_field_in_multiple_registries` — diagnostic names overlapping pairs | failing |
| AC7 (existing suite passes unchanged) | New file only — no pre-existing tests modified. To be verified by Dev after GREEN. | n/a |

### Rule Coverage (sidequest-server CLAUDE.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| No Source-Text Wiring Tests | All — explicit exception for runtime reflection per CLAUDE.md ("reflection-based dataclass / type checks") | conforming |
| Every Test Suite Needs a Wiring Test | The gate test IS the wiring assertion — it interrogates the actual production seam (`session_helpers._PHASE_*` constants consumed by `_apply_phase_c_projections`) via reflection | conforming |
| No Silent Fallbacks | `_import_registries` raises ImportError with explicit messages naming each missing symbol — no try/except swallow | conforming |

**Rules checked:** 3 of 3 applicable CLAUDE.md rules have test coverage or explicit conformance
**Self-check:** 0 vacuous tests (every test has a meaningful assertion with a named-field diagnostic; no `assert True` / `let _ = ...` patterns)

### Notes for Dev (Ponder Stibbons)

1. **Field inventory (from live audit):** `GameSnapshot.model_fields` has 49 top-level fields:

   ```
   achievement_tracker, active_seeds, active_stakes, active_tropes, atmosphere,
   axis_values, campaign_maturity, character_locations, characters,
   chassis_autofire_cooldowns, chassis_registry, clock_t_hours, companions,
   current_region, days_elapsed, discovered_regions, discovered_rooms,
   discovered_routes, encounter, genie_wishes, genre_slug, last_saved_at,
   lore_established, magic_state, narrative_log, next_turn_directives, notes,
   npc_pool, npcs, party_body_id, pending_magic_auto_fires,
   pending_magic_confrontation_outcome, pending_resolution_signal,
   pending_time_skip_summary, player_dead, player_seats, plotted_course,
   quest_anchors, quest_log, resources, room_states, scenario_state,
   seed_ghosts, time_of_day, total_beats_fired, turn_manager,
   turns_since_meaningful, world_history, world_slug
   ```

2. **Already in `_PHASE_B_DROP_FIELDS` (4):** `active_tropes`, `axis_values`, `genie_wishes`, `achievement_tracker`. Leave them.

3. **`_PHASE_C_PROJECTIONS` candidates (from `_apply_phase_c_projections` body + context-story-61-2.md):**
   - `room_states` — projected to current-room only
   - `npcs` — projected to in-scene + nested `belief_state` drop
   - `characters` — tail-K on nested `known_facts` (per-PC, K=8)
   - `scenario_state` — cap on nested `discovered_clues` (K=12)
   - `narrative_log` — already `pop`'d in `_build_turn_context` (story 57-5); confirm where this belongs

4. **`_BOUNDED_BY_CONSTRUCTION` candidates** (apply judgment — anything scalar, enum, or fixed-cardinality):
   - Scalars: `clock_t_hours`, `days_elapsed`, `total_beats_fired`, `turns_since_meaningful`, `party_body_id`, `current_region`, `genre_slug`, `world_slug`, `time_of_day`, `atmosphere`, `last_saved_at`, `campaign_maturity`, `player_dead`
   - Bounded enums / small structs: `turn_manager`, `encounter` (single object), `magic_state`, `pending_magic_confrontation_outcome`, `pending_resolution_signal`, `pending_time_skip_summary`, `next_turn_directives`, `plotted_course`
   - Constant-cardinality dicts: `character_locations` (size = PC count), `chassis_autofire_cooldowns` (size = body count), `resources`, `player_seats`, `discovered_regions`, `discovered_rooms`, `discovered_routes`, `quest_anchors`, `quest_log`, `notes`
   - Mixed / Dev to decide: `companions`, `active_seeds`, `active_stakes`, `chassis_registry`, `seed_ghosts`, `lore_established`, `world_history`, `pending_magic_auto_fires`, `npc_pool`

   Some of those "constant-cardinality" claims will not survive — `quest_log` and `world_history` are session-length growing. Dev must decide whether they're projection candidates (Phase C) or genuinely bounded. **The test will name them in the failure diagnostic** if Dev guesses wrong, so this is a fast-feedback loop.

5. **GREEN procedure:** Add both empty named tuples → run the test → read the unclassified-field diagnostic → make a per-field decision → place each in the right registry → re-run until green.

6. **AC7 verification (existing suite unchanged):** Dev should run `just server-test` after the green pass to confirm no other test broke. The new constants are additive; the projection wiring lives elsewhere and was tested by story 61-2 already.

**Handoff:** To Dev (Ponder Stibbons) for GREEN.

## Dev Assessment

**Status:** GREEN
**Files Changed:**
- `sidequest-server/sidequest/server/session_helpers.py` — added `_PHASE_C_PROJECTIONS` (4 entries) and `_BOUNDED_BY_CONSTRUCTION` (40 entries) named-tuple registries; extended `_PHASE_B_DROP_FIELDS` with `narrative_log` (was previously dropped via separate pop at line 802).

**Test Results:**
- Gate test: `tests/server/test_snapshot_field_governance.py` — 6/6 PASS
- Full server suite: 7523 PASS, 0 FAIL, 375 skipped (28.4s)
- Focus checks: `test_57_5_snapshot_slimming` 16/16 PASS, `test_61_2_snapshot_seven_field_projection` 16/16 PASS

**AC Coverage:**

| AC | How satisfied | Status |
|----|---------------|--------|
| AC1 (`_PHASE_C_PROJECTIONS` introduced explicitly) | Named tuple `_PHASE_C_PROJECTIONS: tuple[str, ...]` added at `session_helpers.py:101-128` with 4 entries (room_states, npcs, characters, scenario_state) — each tied to its projection behavior in the docstring | ✓ |
| AC2 (`_BOUNDED_BY_CONSTRUCTION` introduced explicitly) | Named tuple `_BOUNDED_BY_CONSTRUCTION: tuple[str, ...]` added at `session_helpers.py:130-181` with 40 entries grouped by category (scalars / single-record optionals / finite-keyed dicts / gameplay-bounded lists) | ✓ |
| AC3 (enumerate `model_fields` + assert exactly-one coverage) | `test_every_snapshot_field_is_categorized` + `test_no_field_in_multiple_registries` both green; 49/49 fields classified, zero overlap | ✓ |
| AC4 (pydantic reflection, not source-text grep) | Test reads `GameSnapshot.model_fields.keys()` and runtime registry tuples; no `read_text()` / regex on source files anywhere | ✓ |
| AC5 (fail loudly on missing field) | `test_every_snapshot_field_is_categorized` lists unclassified field names in its assertion message; verified by deliberately rerunning the RED scenario via local sanity-check (RED diagnostic was loud and named the missing registry) | ✓ |
| AC6 (fail loudly on duplicate placement) | `test_no_field_in_multiple_registries` emits "name: registry-A AND registry-B" diagnostic per overlap | ✓ |
| AC7 (existing suite unchanged) | Full server suite 7523/7523 PASS; no regressions in the 32 snapshot-slimming-adjacent tests | ✓ |

**Rule Conformance (sidequest-server CLAUDE.md):**

| Rule | How conforming | Status |
|------|----------------|--------|
| No Silent Fallbacks | All three registries are explicit named tuples; no defaults, no `getattr(..., ())` fallbacks in either the registry definitions or the gate test | ✓ |
| No Stubbing | `_BOUNDED_BY_CONSTRUCTION` is populated with 40 real fields, not a placeholder. The three borderline growers (lore_established, world_history, npc_pool) are placed with explicit per-field rationale in the docstring, not "TODO: classify" | ✓ |
| Don't Reinvent — Wire Up What Exists | Re-used the existing `_apply_phase_c_projections` projection pipeline. The 4 entries in `_PHASE_C_PROJECTIONS` map 1:1 to the 4 projections already implemented in that helper | ✓ |
| Verify Wiring, Not Just Existence | The new registries are consumed by `test_snapshot_field_governance.py` (gate) AND by the existing strip loop at `session_helpers.py:793` (which iterates `_PHASE_B_DROP_FIELDS`). The latter is exercised by every turn that builds a turn context — provably wired into the production code path | ✓ |
| No Source-Text Wiring Tests | The reflection-based pattern is the explicit exception in CLAUDE.md ("reflection-based dataclass / type checks ... because those interrogate runtime types, not source strings") | ✓ |

**OTEL/observability impact:** None. This story adds static classification only; no new spans, no runtime behavior change. The existing `prompt.game_state.bytes` span (set by `_apply_phase_c_projections`) continues to fire unchanged.

**Handoff:** To Architect (Leonard of Quirm) for spec-check.

---

## Dev Assessment (rework — addresses Reviewer Issues A–D)

**Status:** GREEN (rework complete)
**Files Changed (commit `827ce30`):**
- `sidequest-server/sidequest/server/session_helpers.py` — added `_EXCLUDED_FROM_DUMP` registry (2 entries); moved `pending_magic_auto_fires` + `pending_magic_confrontation_outcome` out of `_BOUNDED_BY_CONSTRUCTION` into it; rewrote `_PHASE_C_PROJECTIONS` docstring to clarify governance-vs-dispatch.
- `sidequest-server/tests/server/test_snapshot_field_governance.py` — rewritten end-to-end (9 tests, was 6); killed `_import_registries()` helper in favor of module-level reads; added 2 new tests reflecting on `Field(exclude=True)` and `model_dump()` to give `_EXCLUDED_FROM_DUMP` real teeth; renamed AC7 test and reframed its docstring as a name-presence sanity check; fixed wrong consumer function name; reframed module docstring in past tense.

**Test Results:**
- Gate test: 9/9 PASS (was 6/6)
- Full server suite: 7526 PASS, 0 FAIL (was 7523 — net +3 from the new excluded-fields tests)
- Lint + format: clean

### Issue-by-Issue Resolution

| Issue | Reviewer's Required Fix | Resolution |
|-------|-------------------------|------------|
| A [HIGH] — `exclude=True` misclassification | Add `_EXCLUDED_FROM_DUMP` registry; move the 2 fields; assert `exclude=True` metadata | Implemented. Two new tests give the registry teeth: `test_excluded_from_dump_entries_actually_have_exclude_true` (reflects on `FieldInfo.exclude`) and `test_excluded_from_dump_entries_actually_absent_from_model_dump` (drives a real `model_dump()` and asserts the field is absent). |
| B [HIGH] — Three docstring inaccuracies | Rewrite `_PHASE_C_PROJECTIONS` docstring; fix AC7 docstring + wrong function name; reframe RED-state | All three rewritten. The `_PHASE_C_PROJECTIONS` docstring now explicitly says "this registry is a governance artefact … `_apply_phase_c_projections` independently hard-codes the same four names" and points at the deferred consistency-tightening deviation. AC7 renamed and reframed as name-presence sanity. RED-state moved to past tense in a "Story history" section. |
| C [HIGH] — Asymmetric ImportError wrapping | Pick option A — kill the wrapping | Took option A. Helper deleted; registries read at module-import time. Missing registry → AttributeError at collection with a precise traceback pointing at the offending line. No ceremony, fully symmetric. |
| D [MEDIUM] — Sentinel doesn't protect `narrative_log` | Rename `legacy_four` → `expected_drop_entries`; include `narrative_log` | Renamed and extended. Test now named `test_phase_b_drop_list_pins_expected_entries`. Future intentional removal of any pinned entry must be co-edited in this test. |

### Bonus — edge-hunter medium findings absorbed

- **Empty `model_fields` vacuous-pass** — `test_every_snapshot_field_is_categorized` now asserts `all_fields` non-empty before computing the unclassified set. The architecture gate cannot trivially pass on an empty model.
- **Intra-registry duplicates** — `test_no_field_in_multiple_registries` extended with an intra-tuple duplicate scan (was silently dedup'd by `set()`). A registry tuple with `("foo", "foo")` now fails loudly.
- **Pairwise overlap enumeration** — overlap detection now iterates pairs of registries instead of a hardcoded 3-pair list, so adding a 5th registry doesn't require updating the test.

### Deferred (acknowledged, not addressed in this rework)

- Type-design: `_import_registries` NamedTuple return-type suggestion — moot, helper deleted.
- Type-design: stringly-typed registries — acceptable per agent's own rationale; could become `Literal` types if a future cost-aware story wants compile-time enforcement.
- Test-analyzer: monkeypatch-test for overlap detector — over-engineering; the detector logic is six lines of set arithmetic with clear failure mode.

**Handoff:** Back to Reviewer (Granny Weatherwax) for re-review.

---

## Architect Assessment (spec-check — rework iteration)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring further Dev hand-back

### Reviewer Issue × Rework Cross-Check

| Issue | Required | Dev's Fix | Architect Verdict |
|-------|----------|-----------|-------------------|
| A [HIGH] — `exclude=True` misclassification | Add `_EXCLUDED_FROM_DUMP` registry; move the 2 fields; add `exclude=True` reflection test | Added `_EXCLUDED_FROM_DUMP: tuple[str, ...]` at `session_helpers.py:120-144` with 2 entries (`pending_magic_auto_fires`, `pending_magic_confrontation_outcome`). Moved both fields OUT of `_BOUNDED_BY_CONSTRUCTION`. Added 3 new tests: `test_excluded_from_dump_registry_is_tuple_of_strs`, `test_excluded_from_dump_entries_actually_have_exclude_true` (reflects on `FieldInfo.exclude`), and `test_excluded_from_dump_entries_actually_absent_from_model_dump` (drives a real `model_dump()` and asserts absence). | RESOLVED. The gate now has real teeth on this category: removing `exclude=True` from a listed field would fail both reflection tests with a precise diagnostic naming the field. The 4-set union in `test_every_snapshot_field_is_categorized` is the structural backstop. |
| B [HIGH] — Three docstring inaccuracies | Rewrite `_PHASE_C_PROJECTIONS` docstring; fix AC7 docstring + wrong function name; reframe RED-state | (a) `_PHASE_C_PROJECTIONS` docstring now explicitly says "This registry is a governance artefact consumed by `test_snapshot_field_governance.py`, NOT a runtime dispatch table. `_apply_phase_c_projections` … independently hard-codes the same four names" and points at the deferred consistency-tightening deviation. (b) AC7 renamed `test_phase_b_drop_list_pins_expected_entries`; docstring reframed as "name-presence sanity check"; the wrong-function-name fixed (now correctly `_build_turn_context` at `session_helpers.py:905`). (c) Module docstring reframed in past tense via a "Story history" section. | RESOLVED. The `_PHASE_C_PROJECTIONS` rewrite is particularly well done — it doesn't paper over the gap, it names it explicitly and links the follow-up. |
| C [HIGH] — Asymmetric ImportError wrapping | Pick option A (kill wrapping) or B (apply symmetrically) | Took option A. Helper `_import_registries()` deleted entirely; registries are now module-level reads (`_DROP = sh._PHASE_B_DROP_FIELDS` etc.) at `tests/server/test_snapshot_field_governance.py:67-70`. Missing registry → `AttributeError` at module-collection time with a clean traceback pointing at the line. | RESOLVED. Substantially simpler — 31 lines of helper + 5 try/except blocks gone. Pytest's collection-error output for a missing module attribute is just as loud as the prior custom `ImportError`, and the symmetry is now structural. |
| D [MEDIUM] — Sentinel doesn't protect `narrative_log` | Extend `legacy_four` → include `narrative_log` | Renamed `legacy_four` → `expected_drop_entries`; added `narrative_log` to the set; docstring rewritten with "If you intentionally moved a field out of the drop list … update `expected_drop_entries` in this test in the same change." | RESOLVED. The sentinel now protects all 5 pinned entries, and the docstring tells future authors how to evolve it. |

### Bonus — Edge-Hunter Mediums Absorbed

Dev folded in three medium-confidence edge-hunter findings without scope expansion:
- Empty `model_fields` vacuous-pass closed (test asserts `all_fields` non-empty before computing diff).
- Intra-registry duplicate detection added (was silently `set()`-dedup'd).
- Pairwise overlap enumeration replaces the hardcoded 3-pair list — adding a 5th registry no longer requires editing the overlap test (and `_EXCLUDED_FROM_DUMP` is now the 4th, so this was load-bearing for THIS rework).

### Deferred — Documented, Not Addressed

These are explicit Dev choices, properly logged under `### Dev (rework — post-review)` in Design Deviations:
- Type-design NamedTuple suggestion → moot (helper deleted).
- Type-design stringly-typed registries → acceptable per agent's own rationale.
- Test-analyzer monkeypatch overlap-detector test → over-engineering for 6 lines of set arithmetic.

I concur on all three deferrals.

### Substance Notes

1. **The `_PHASE_C_PROJECTIONS` docstring rewrite is the right shape.** It doesn't claim consistency it doesn't have; it names the gap; it links the follow-up. Future authors reading the comment will not assume the registry drives the projection — they'll know to keep them in sync until the consistency-tightening story lands.

2. **`_EXCLUDED_FROM_DUMP` has structural teeth, not just static categorization.** Two of the 4 categories (drop, projections) have behavior tests in sibling files; the third (bounded) is largely cosmetic categorization. The new fourth category has *two* assertions firing on the actual runtime behavior (`FieldInfo.exclude` reflection AND `model_dump()` absence) — that's stronger than any of the original three. The reviewer's substantive concern is fully cured.

3. **Killing `_import_registries()` was the right call.** The complaint was asymmetry. Symmetry by removal is cleaner than symmetry by addition. The module-import pattern also means a missing registry fails at *collection* time rather than at *test* time — even louder.

### Decision

Proceed to TEA verify. No further code fixes required. The story scope is now larger than originally drawn (4 registries instead of 3, 9 tests instead of 6) but the expansion is a direct response to a substantive architectural defect Granny caught — exactly what the spec-check + review loop exists to surface.

### Reviewer Issues × Original AC Coverage

The original ACs (AC1–AC7) all still pass:

| Original AC | Coverage After Rework |
|-------------|----------------------|
| AC1 — `_PHASE_C_PROJECTIONS` explicit | Still satisfied. Now joined by `_EXCLUDED_FROM_DUMP` as a 4th registry — same explicitness pattern. |
| AC2 — `_BOUNDED_BY_CONSTRUCTION` explicit | Still satisfied. 38 entries (was 40 — 2 moved to `_EXCLUDED_FROM_DUMP`). |
| AC3 — exhaustive + exactly-one coverage | Still satisfied. 5 + 4 + 38 + 2 = 49 = `len(model_fields)`. |
| AC4 — pydantic reflection | Still satisfied + extended. `FieldInfo.exclude` reflection added on top of `model_fields.keys()`. |
| AC5 — loud failure on missing | Still satisfied. Diagnostic now mentions 4 registries. |
| AC6 — loud failure on duplicate | Still satisfied. Also catches intra-registry duplicates (new). |
| AC7 — existing suite unchanged | Still satisfied. 7526 PASS / 0 FAIL post-rework (was 7523; net +3 from new tests). |

**Handoff:** To TEA (Igor) for verify (simplify + quality-pass) — re-run the verify lane on the reworked diff.

---

## TEA Assessment (verify — rework iteration)

**Phase:** review (post-rework)
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 — diff vs. commit `98c4cbd` (the rework: commit `827ce30`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 2 findings (both high) | (1) Parametrize the three identical tuple-validation tests. (2) Extract registries-dict to a module-level constant. |
| simplify-quality | clean | Nothing new beyond the rework's intentional design — original "dead code" complaints already dismissed. |
| simplify-efficiency | 2 findings (1 high + 1 medium) | Same two as reuse (duplicate detection across teammates). |

**Applied:** 2 high-confidence fixes (both reuse + efficiency agreed)
**Flagged for Review:** 0
**Noted:** 0
**Reverted:** 0

**Overall:** simplify: applied 2 fixes

### Fixes Applied (commit `3ee6a86`)

1. **Parametrized the three tuple-validation tests** — `test_phase_c_projections_registry_is_tuple_of_strs`, `test_bounded_by_construction_registry_is_tuple_of_strs`, `test_excluded_from_dump_registry_is_tuple_of_strs` collapsed into a single `@pytest.mark.parametrize`'d `test_registry_is_tuple_of_strs` covering all three. `_PHASE_B_DROP_FIELDS` is implicit (its tuple shape is exercised every turn by the drop loop at `session_helpers.py:905`).
2. **Extracted `_REGISTRIES` module-level dict** — `tests/server/test_snapshot_field_governance.py` now has a canonical `_REGISTRIES: dict[str, tuple[str, ...]]` at the top. The intra-registry duplicate scan, cross-registry overlap scan, and stray-entry test all iterate it. Adding a 5th registry in the future is now a one-place change (the dict + the imports above).

### Quality-Pass Gate

| Check | Result |
|-------|--------|
| `ruff check .` | All checks passed |
| `ruff format --check` | Clean (auto-formatted in commit `3ee6a86`) |
| `pytest tests/server/test_snapshot_field_governance.py` | 9/9 PASS |
| Focused slim-adjacent regression (test_snapshot_field_governance + test_57_5_snapshot_slimming + test_61_2_snapshot_seven_field_projection) | 41/41 PASS |

**Quality Checks:** All passing
**Handoff:** To Reviewer (Granny Weatherwax) for re-review.

## TEA Assessment (verify)

**Phase:** review
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`sidequest/server/session_helpers.py`, `tests/server/test_snapshot_field_governance.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | No duplication or extraction opportunities. The acknowledged `narrative_log` defense-in-depth (drop loop + explicit pop) was correctly identified as intentional and properly documented. |
| simplify-quality | 2 findings | Both flagged the new registries (`_PHASE_C_PROJECTIONS`, `_BOUNDED_BY_CONSTRUCTION`) as "dead code" because they are consumed only by the gate test, not by production logic. |
| simplify-efficiency | clean | No unnecessary complexity introduced. |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0 medium-confidence findings retained
**Noted:** 2 dismissed (see rationale below)
**Reverted:** 0

**Overall:** simplify: clean (after dismissal review)

### Dismissed Findings

Both simplify-quality findings classify the new registries as "dead code." This is a misreading of architectural intent:

1. **`_PHASE_C_PROJECTIONS` (high-confidence "dead code")** — Dismissed. The registry IS consumed: by `test_snapshot_field_governance.py`, which is the ADR-110 architecture gate. The Story 61-5 spec explicitly calls for "named, enumerable registry" for *test-time* reflection — that's the whole point. The agent's own suggestion (a) ("wire the registry to drive the actual projection logic") matches the Architect Assessment's deferred deviation: tightening the gate to verify projection-consistency. That's a follow-up story, not a 61-5 fix. The docstring already says "architecture gate" explicitly.

2. **`_BOUNDED_BY_CONSTRUCTION` (medium-confidence "dead code")** — Dismissed for the same reason. The docstring already says "bounded by their own structure rather than by projection logic" — clearly a governance marker, not a control structure.

The architect already logged the consistency-tightening idea as a deferred improvement under `### Architect (spec-check)` in Design Deviations. Confirming here.

### Quality-Pass Gate

| Check | Result |
|-------|--------|
| `ruff check .` | All checks passed (6 lint errors in the new test file auto-fixed in commit `98c4cbd`) |
| `ruff format --check .` | New test file reformatted in `98c4cbd`; no pending changes in the 61-5 diff |
| `pytest tests/server/test_snapshot_field_governance.py` | 6/6 PASS |
| Full server suite (last green-phase run) | 7523 PASS / 0 FAIL / 375 skipped (Dev's run) |

**Quality Checks:** All passing
**Handoff:** To Reviewer (Granny Weatherwax) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None requiring Dev hand-back

### AC × Code Cross-Check

| AC | Spec | Code | Verdict |
|----|------|------|---------|
| AC1 (`_PHASE_C_PROJECTIONS` explicit) | named, enumerable registry in `session_helpers.py` | `_PHASE_C_PROJECTIONS: tuple[str, ...]` at `session_helpers.py:101-106`, 4 entries each tied to the projection in `_apply_phase_c_projections` via docstring | Aligned |
| AC2 (`_BOUNDED_BY_CONSTRUCTION` explicit) | named, enumerable registry in `session_helpers.py` | `_BOUNDED_BY_CONSTRUCTION: tuple[str, ...]` at `session_helpers.py:130-181`, 40 entries grouped under a 5-clause rubric (a–e) in the docstring | Aligned |
| AC3 (exhaustive + exactly-one coverage) | every `GameSnapshot.model_fields` entry in exactly one registry | 5 + 4 + 40 = 49 = `len(GameSnapshot.model_fields)`; `test_every_snapshot_field_is_categorized` and `test_no_field_in_multiple_registries` both green | Aligned |
| AC4 (pydantic reflection, no source-text grep) | runtime reflection over `model_fields` | Test reads `GameSnapshot.model_fields.keys()` and the runtime tuples; no `Path.read_text()`, no regex over source | Aligned (also satisfies the CLAUDE.md "No Source-Text Wiring Tests" rule via the documented reflection-exception) |
| AC5 (loud failure on missing) | diagnostic names unclassified fields | `test_every_snapshot_field_is_categorized` emits `sorted(unclassified)` in the assertion message | Aligned |
| AC6 (loud failure on duplicate) | diagnostic names overlapping fields | `test_no_field_in_multiple_registries` emits `"name: registry-A AND registry-B"` per overlap | Aligned |
| AC7 (existing suite unchanged) | no regressions | Full server suite 7523 PASS / 0 FAIL post-change | Aligned |

### Substance Notes

1. **`narrative_log` addition to `_PHASE_B_DROP_FIELDS` is the right call.** Pre-change, `narrative_log` was dropped by a *separate* `state_summary_payload.pop("narrative_log", None)` at line 802 (story 49-1) — i.e., it was a top-level field that the gate would have flagged as "uncategorized" had Dev left it out of every registry. Dev's choice to add it to the existing drop registry (vs. inventing a fourth registry, vs. lying about it being "bounded") preserves the gate's invariant: registries are the single source of truth for "what happens to this field in the dump." The redundant explicit pop is idempotent and properly flagged for follow-up cleanup. Dev logged this correctly under `### Dev (implementation)` as a deviation.

2. **Three borderline growers (`lore_established`, `world_history`, `npc_pool`) classified as BOUNDED is acceptable.** Strict reading of "growth bounded by structure" excludes growing `list[X]` fields; Dev correctly noted the deviation and provided per-field rationale (P3-deferred, gaslighting anchor, small-by-convention). The gate's *primary* value is forcing the conversation for NEW fields — existing classification can be refined per follow-up. This is a deliberate, documented choice, not drift.

3. **`quest_log: dict[str, str]` is in BOUNDED via clause (d) — "dict keyed by finite gameplay domain."** Quest count is gameplay-bounded but does grow monotonically with quests accepted. In a long campaign this could reach ~20-50 entries with short string values (~5KB max payload contribution). Acceptable today; same future-resort applies if real play shows it ballooning.

4. **Architectural follow-up — the gate test could be tightened in a future story.** Today's test verifies *categorization* but not *consistency*: a future developer could add a field to `_PHASE_C_PROJECTIONS` without implementing the actual projection in `_apply_phase_c_projections`, and the gate would still pass. A meaner version would assert that every field in `_PHASE_C_PROJECTIONS` either appears in `_apply_phase_c_projections`'s payload mutations OR has a documented projection-elsewhere reference. **Out of scope for 61-5 — note for an epic-61 follow-up.** Logged as a deviation below.

### Decision

Proceed to TEA verify. No code fixes required.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (6/6 PASS, 0 smells, 0 lint, ruff format check 8 pre-existing files unrelated) | N/A |
| 2 | reviewer-edge-hunter | Yes | findings | 8 (2 high, 4 medium, 2 low) | confirmed 3, dismissed 1 (inheritance — pydantic v2 model_fields IS MRO-aware; verified), deferred 4 |
| 3 | reviewer-silent-failure-hunter | Yes | findings | 2 (both low) | confirmed 2 (duplicate of edge-hunter findings A/C — kept as corroboration) |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (3 high, 1 medium) | confirmed 3, deferred 1 (monkeypatch overlap detector test — over-engineering) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 (all high) | confirmed 3 |
| 6 | reviewer-type-design | Yes | findings | 2 (1 medium, 1 low) | deferred 2 (NamedTuple suggestion is nice but optional; stringly-typed registries acceptable per agent's own rationale) |
| 7 | reviewer-security | Yes | clean | none | N/A |
| 8 | reviewer-simplifier | Yes | findings | 1 (high) | confirmed 1 (duplicates test-analyzer F1) |
| 9 | reviewer-rule-checker | Yes | clean | 0 across 14 python rules + 6 CLAUDE.md rules (38 instances checked) | N/A |

**All received:** Yes (9 returned, 6 with findings, 3 clean)
**Total findings:** 11 confirmed (consolidated into 4 issues A–D), 1 dismissed (inheritance — verified false), 6 deferred (optional improvements)

## Reviewer Assessment

**Verdict:** REJECTED

The architecture-gate concept is sound and the rule-checker came back clean across all 14 python rules + 6 CLAUDE.md rules (38 instances). However, three subagents independently flagged the same docstring inaccuracies, one subagent surfaced a substantive category error in the gate's own classification, and the test-error-handling asymmetry between AC1/AC2 and AC3-AC6 muddies the gate's diagnostic story. Fixes are all small (single test file + 1 docstring in session_helpers.py); send back to Dev to land them before merge so the gate ships with its claimed teeth and accurate documentation.

### Severity Table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] [TEST] [RULE-impl] | `exclude=True` fields misclassified — `pending_magic_auto_fires` and `pending_magic_confrontation_outcome` are in `model_fields` but absent from `model_dump()` (verified: `Field(..., exclude=True)` at `session.py:798-799`). The gate exists to bound dump size; classifying never-dumped fields as "bounded by construction" conflates "small" with "not emitted" and lets a future Dev silently remove `exclude=True` without re-categorizing — exactly the class of error the gate exists to catch | `session_helpers.py` — `_BOUNDED_BY_CONSTRUCTION` mis-includes the two excluded fields; `tests/server/test_snapshot_field_governance.py` — no test distinguishes excluded fields from dumped fields | Add `_EXCLUDED_FROM_DUMP: tuple[str, ...] = ("pending_magic_auto_fires", "pending_magic_confrontation_outcome")`. Move both entries OUT of `_BOUNDED_BY_CONSTRUCTION`. Update `test_every_snapshot_field_is_categorized` to union all 4 sets. Add a new test that asserts every entry in `_EXCLUDED_FROM_DUMP` has `GameSnapshot.model_fields[name].exclude is True` — so removing `exclude=True` forces re-categorization and fails the gate loudly. |
| [HIGH] [DOC] [SIMPLE] | Docstring inaccuracies in three places that materially misdescribe the design | (a) `session_helpers.py:104-106` — `_PHASE_C_PROJECTIONS` comment says fields are "projected … BEFORE the dump leaves `_apply_phase_c_projections`" — implying the function consumes the registry. It hard-codes the same four names and never references the registry. (b) `tests/server/test_snapshot_field_governance.py:251-263` — AC7 docstring says "we drive `_apply_phase_c_projections` and observe the field set actually removed." The test body does no such thing — it asserts four string literals are present in the tuple. (c) `tests/server/test_snapshot_field_governance.py:34-44` — "RED state" block in the module docstring is written from RED-phase perspective but ships in the same commit as the GREEN-phase code | Rewrite each: (a) clarify that `_apply_phase_c_projections` independently hard-codes the same four names and the registry is a governance declaration consumed by `test_snapshot_field_governance.py`; (b) trim AC7 docstring to "name-presence sanity check" framing — the runtime wiring belongs to `test_61_2_*` and `test_57_5_*` only. Also fix the wrong consumer-function name (`_apply_phase_c_projections` → `_build_turn_context`, which is where the drop loop lives at `session_helpers.py:905`); (c) reframe RED-state in past tense ("written RED against a session_helpers.py that lacked the two registries; story 61-5 introduced them together"). |
| [HIGH] [EDGE] [SILENT] [TEST] | `_import_registries()` error-handling asymmetry — AC1 and AC2 wrap the call in `try/except ImportError: pytest.fail(str(e))`, but AC3, AC4, AC5, AC6 call it bare. If either registry is missing, those four tests surface as raw pytest ERRORs with a generic traceback instead of the deliberate, loud diagnostic message the helper raises. Three subagents flagged this independently | `tests/server/test_snapshot_field_governance.py` — call sites in AC3 (line 154), AC5 (line 188), AC6 (line 222), AC7 (line 267) and also the bare `drop = sh._PHASE_B_DROP_FIELDS` at line 78 inside the helper | Pick ONE of: (option A — minimal, recommended) drop the try/except from AC1/AC2 entirely and let `ImportError` propagate naturally — pytest renders it with the chained `AttributeError` cause and the diagnostic message is visible in the error display anyway; (option B — symmetric) wrap all six AC call-sites in the same `try/except ImportError: pytest.fail(str(e))` AND wrap the `_PHASE_B_DROP_FIELDS` access inside `_import_registries` in a parallel `try/except AttributeError`. Pick A; the verbose wrapping is ceremony that does not pay for itself. |
| [MEDIUM] [EDGE] | Sentinel-protection test (`test_phase_b_drop_list_is_single_source_of_truth`) hardcodes only the four pre-61-2 entries. `narrative_log` was added to `_PHASE_B_DROP_FIELDS` in THIS story but isn't in the `legacy_four` set — so a future removal of `narrative_log` from the registry would slip past this guard | `tests/server/test_snapshot_field_governance.py:285-291` (the `legacy_four` set literal) | Rename `legacy_four` → `expected_drop_entries` and include `"narrative_log"`; update the failure message to drop the "legacy-57-5" framing. Now any removal of any pinned entry trips the guard. |

### Devil's Advocate

What if I'm wrong? What if the gate is fine and I'm over-fitting on docstring imperfections?

The exclude=True finding (Issue A) is the only one with bite. Argument: the two fields ARE bounded — they're transient one-turn dispatch queues that reset on every handler dispatch (`session.py:789`). They don't grow. Putting them in `_BOUNDED_BY_CONSTRUCTION` is *technically* defensible — they ARE bounded by their own structure (per-turn-reset). The "they're not in the dump" objection isn't load-bearing because the gate operates on `model_fields`, not on the dump, and the registry just records the bounding reasoning. A future Dev who removes `exclude=True` would still need to look at the field's actual behavior to decide whether to recategorize — same conversation forced either way.

I don't buy it. The gate's mission per its own docstrings ("fields that ride into `snapshot.model_dump()`", "the dump leaves `_apply_phase_c_projections`") is about the DUMP, not the model. The classification system implicitly assumes every field in `model_fields` ends up in the dump unless explicitly dropped. That assumption is broken for excluded fields, and the broken assumption is exactly what would silently hide a future `exclude=True` removal. Two subagents arrived at the same architectural concern independently. Adding a fourth registry is the simplest honest fix.

What about Issue C — am I rejecting over ceremony? Could just leave the asymmetry. Argument: pytest renders ImportError fine; the diagnostic message is in the error, just at a different rendering stage. The two-style symmetry isn't load-bearing.

Fair, but the registries are the *one feature* this story exists to introduce. Their `ImportError` diagnostic is the human-facing voice of the gate when it fires for a missing registry. Right now, that voice is silent for 4 of 6 tests. Either kill the wrapping everywhere (it's vestigial), or apply it everywhere (it's deliberate). Pick a story and stick with it. The minimal version is "kill the wrapping" — that's option A above.

What about Issue B — am I fussing over comments? Argument: the code works; the docs are mostly right; the AC7 test even names sibling test files for the real wiring check.

The lying-docstring on `_PHASE_C_PROJECTIONS` is the most consequential — it claims `_apply_phase_c_projections` consumes the registry when it hard-codes the names independently. That's a *load-bearing* lie about the architecture of the gate itself; a future Dev reading the comment will assume runtime consistency that doesn't exist. The architect's deferred deviation ("tighten the gate to verify projection-consistency") is the eventual cure, but until then the comment must not claim consistency it doesn't have.

### Rule Compliance (cross-checked with rule-checker)

| Rule (python.md + CLAUDE.md) | Status | Evidence |
|---|---|---|
| #1 Silent exception swallowing | PASS | Specific `except AttributeError as e: raise ImportError(...) from e` at test:81,89. Chained cause preserved. |
| #2 Mutable default arguments | PASS | All 6 test fns + helper take zero parameters. |
| #3 Type annotations at boundaries | PASS | All 6 tests `-> None`; helper return type fully annotated; internal local types annotated where non-trivial. |
| #4 Logging | N/A | No logging touched. |
| #5 Path handling | N/A | No path operations. |
| #6 Test quality | PASS | Every test has named-field diagnostics in `assert` messages. No vacuous assertions. 1 docstring overpromises (Issue B/AC7) — that's a doc issue, not a vacuous-assertion issue. |
| #7 Resource leaks | N/A | No resources. |
| #8 Unsafe deserialization | N/A | No deserialization. |
| #9 Async pitfalls | N/A | No async. |
| #10 Import hygiene | PASS | `from __future__ import annotations`, explicit imports, lazy import inside helper documented. No star imports. |
| #11 Input validation | N/A | No external input. |
| #12 Dependency hygiene | N/A | No dep changes. |
| #13 Fix-regressions meta | PASS | The ruff-fix commit (`98c4cbd`) only removed lint noise; tests re-verified GREEN. |
| #14 State cleanup ordering | N/A | No fallible side effects in the diff. |
| CLAUDE.md "No Silent Fallbacks" | PASS | `narrative_log` extension explicit; defense-in-depth pop documented. |
| CLAUDE.md "No Stubbing" | PASS | Registries fully populated with real entries; no placeholder TODOs. |
| CLAUDE.md "Don't Reinvent" | PASS | Reuses `GameSnapshot.model_fields` reflection pattern from `test_setpiece_attach_wiring.py`. |
| CLAUDE.md "Verify Wiring, Not Just Existence" | PARTIAL | The gate test verifies registry membership against `model_fields`, but **not** that registry membership corresponds to actual dump behavior (Issue A is the leak). |
| CLAUDE.md "No Source-Text Wiring Tests" | PASS | Zero source-grep, zero `read_text()`. Pure pydantic reflection. |

### Specialist Coverage Summary (by tag)

- `[TEST]` — test-analyzer flagged Issues A, B, C above (3 high-confidence findings confirmed).
- `[EDGE]` — edge-hunter flagged Issues C, D + 4 deferred-medium edges (zero-field model, intra-tuple dupes, inheritance [dismissed], model_rebuild guard).
- `[SILENT]` — silent-failure-hunter confirmed Issue C (corroborates edge-hunter); flagged a low-confidence traceback-chain loss on `pytest.fail(str(e))` (subsumed by option-A fix).
- `[DOC]` — comment-analyzer flagged Issue B (all 3 instances — lying docstring on `_PHASE_C_PROJECTIONS`, stale RED-state block, wrong consumer function in AC7).
- `[SIMPLE]` — simplifier confirmed TEA's earlier "dead-code" dismissal and surfaced AC7 docstring overpromise (subsumed by Issue B).
- `[TYPE]` — type-design flagged the `tuple[tuple, tuple, tuple]` return type as transposition-prone (NamedTuple suggestion) and the stringly-typed registries — both deferred as optional improvements. No HIGH findings.
- `[SEC]` — security CLEAN. No I/O, no user input, no subprocess, no secrets touched by the diff. No findings.
- `[RULE]` — rule-checker CLEAN across all 14 python rules + 6 CLAUDE.md rules (38 instances checked, 0 violations). The CLAUDE.md "No Source-Text Wiring Tests" carve-out is explicitly exercised correctly.

### VERIFIED (with rule-cross-check)

- `[VERIFIED]` `_PHASE_B_DROP_FIELDS` is actively consumed by production code — `session_helpers.py:905` does `for _drop_field in _PHASE_B_DROP_FIELDS: state_summary_payload.pop(_drop_field, None)`. Complies with CLAUDE.md "Verify Wiring, Not Just Existence" for the drop registry specifically.
- `[VERIFIED]` Pydantic v2 `model_fields` IS MRO-aware — confirmed via 2-class inheritance test (`class B(A)` → `B.model_fields == {"a": ..., "b": ...}`). Edge-hunter's inheritance finding dismissed.
- `[VERIFIED]` `narrative_log` is correctly idempotent with the existing explicit pop at line 802 — `dict.pop(k, None)` is safe to call twice. Existing `test_57_5_snapshot_slimming.py` and `test_61_2_*` (32 tests total) PASS after the registry extension.
- `[VERIFIED]` 49 fields total in `GameSnapshot.model_fields` = 5 + 4 + 40 (current registry sizes sum correctly) — verified via `len()` on each registry.
- `[NOT-VERIFIED — see Issue A]` All 40 entries in `_BOUNDED_BY_CONSTRUCTION` are actually present in `model_dump()`. Two of them (`pending_magic_auto_fires`, `pending_magic_confrontation_outcome`) are NOT in the dump because `Field(exclude=True)`. This is the substantive architectural issue.

**Handoff:** Back to Dev (Ponder Stibbons) for fixes A–D. Re-review after.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Improvement** (non-blocking): Story context file `sprint/context/context-story-61-5.md` was not generated by SM setup; TEA proceeded using the session file's inline Story Context + sibling `context-story-61-2.md`. Affects `sprint/context/` (missing file). Future SM runs should generate the context file before phase exit — recurring sm-setup gap per memory `feedback_sm_setup_misfiles_session`. *Found by TEA during test design.*

### Dev (implementation)
- **Improvement** (non-blocking): The named registry `_PHASE_B_DROP_FIELDS` and the explicit `state_summary_payload.pop("narrative_log", None)` at `session_helpers.py:802` now overlap — both drop `narrative_log` idempotently. A follow-up cleanup story can remove the explicit pop and rely on the registry loop alone. Affects `sidequest/server/session_helpers.py` (one-line redundancy removal). *Found by Dev during green phase.*
- **Improvement** (non-blocking): Three top-level snapshot fields (`lore_established`, `world_history`, `npc_pool`) are classified as `_BOUNDED_BY_CONSTRUCTION` but are actually growing lists. Today's live build keeps them small (world_history is P3-deferred; npc_pool is the gaslighting anchor that must not be projected; lore_established is small-by-convention). If any of them grows materially in long campaigns, a follow-up story should move it to `_PHASE_C_PROJECTIONS` with appropriate bounding logic. Affects `sidequest/server/session_helpers.py:_BOUNDED_BY_CONSTRUCTION`. *Found by Dev during green phase.*

### Dev (rework — post-review)
- **Corrected `exclude=True` field misclassification** (resolves Reviewer Issue A)
  - Spec source: `.pennyfarthing/gates/lang-review/python.md` + Reviewer Issue A
  - Spec text: gate exists to bound `model_dump()` size; fields with `Field(exclude=True)` never enter the dump
  - Implementation: Added `_EXCLUDED_FROM_DUMP` as a 4th registry. Moved `pending_magic_auto_fires` and `pending_magic_confrontation_outcome` out of `_BOUNDED_BY_CONSTRUCTION` into it. Added two new tests that reflect on `FieldInfo.exclude` and on actual `model_dump()` output so removing `exclude=True` from a listed field forces re-categorization.
  - Rationale: The "bounded by construction" label conflated "small" with "not emitted." The two are different architectural properties; the gate is now precise.
  - Severity: minor (rework of an unmerged story, not behavior change to landed code)
  - Forward impact: any new `Field(exclude=True)` field on `GameSnapshot` belongs in `_EXCLUDED_FROM_DUMP`; the gate's `test_excluded_from_dump_entries_actually_have_exclude_true` test enforces this.
- **Killed `_import_registries()` helper** (resolves Reviewer Issue C)
  - Spec source: Reviewer Issue C (recommended option A — kill the wrapping)
  - Spec text: error-handling asymmetry between AC1/AC2 (try/except) and AC3-6 (bare)
  - Implementation: Removed the helper. Registries are now read at module-import time as `_DROP / _PROJECTIONS / _BOUNDED / _EXCLUDED`. Missing registry → AttributeError at collection with a precise traceback. No ceremony.
  - Rationale: The wrapping was vestigial — pytest renders the chained exception fine, and the symmetric form was a 7-line helper for what is really a 4-line read.
  - Severity: trivial (test code only)
  - Forward impact: simpler test file; new tests don't need to remember to wrap calls.

### Architect (spec-check)
- **Improvement** (non-blocking): The gate test verifies *categorization* but not *projection-consistency*. A future Dev could add a field to `_PHASE_C_PROJECTIONS` without implementing the actual projection in `_apply_phase_c_projections` and the gate would still pass. A future story should extend the test to assert that every `_PHASE_C_PROJECTIONS` entry has corresponding projection logic — either by reflecting over the helper's payload mutations or by requiring a docstring-linked projection reference. Affects `tests/server/test_snapshot_field_governance.py` (new assertion) and possibly `_apply_phase_c_projections` (add a registry-of-applied-projections so the test can reflect over it). *Found by Architect during spec-check.*

### Reviewer (code review)
- **Conflict** (blocking): `_BOUNDED_BY_CONSTRUCTION` mis-classifies `pending_magic_auto_fires` and `pending_magic_confrontation_outcome` — both `Field(..., exclude=True)` at `session.py:798-799`, hence absent from `model_dump()`. The gate's stated purpose is bounding the dump; never-dumped fields belong in a separate `_EXCLUDED_FROM_DUMP` registry with an `exclude is True` assertion. Affects `sidequest/server/session_helpers.py` (4th registry + reclassify two fields) and `tests/server/test_snapshot_field_governance.py` (4-set union + new excluded-fields-have-exclude-True assertion). *Found by Reviewer during code review (corroborated by reviewer-test-analyzer F4).*
- **Improvement** (non-blocking): `_PHASE_C_PROJECTIONS` docstring claims `_apply_phase_c_projections` consumes the registry; it hard-codes the same four names instead. AC7 test docstring names the wrong consumer function (`_apply_phase_c_projections` vs `_build_turn_context` at line 905). Module docstring's "RED state" block ships from RED-phase perspective in a GREEN-phase commit. Affects `sidequest/server/session_helpers.py` and `tests/server/test_snapshot_field_governance.py` (docstring rewrites only). *Found by Reviewer during code review (corroborated by reviewer-comment-analyzer + reviewer-simplifier).*
- **Improvement** (non-blocking): `_import_registries()` error handling is asymmetric — AC1/AC2 wrap in `try/except ImportError: pytest.fail`, AC3-AC6 call it bare, and the helper's own `_PHASE_B_DROP_FIELDS` access is unguarded. Either kill the wrapping (let ImportError propagate naturally — pytest renders the chained AttributeError fine) or apply it everywhere symmetrically. Recommend: kill the wrapping. Affects `tests/server/test_snapshot_field_governance.py`. *Found by Reviewer during code review (corroborated by reviewer-edge-hunter + reviewer-silent-failure-hunter + reviewer-test-analyzer).*
- **Improvement** (non-blocking): `test_phase_b_drop_list_is_single_source_of_truth` hardcodes only the 4 legacy entries in its `legacy_four` sentinel — `narrative_log` (added in this story) is not protected. Rename `legacy_four` → `expected_drop_entries` and include `narrative_log`. Affects `tests/server/test_snapshot_field_governance.py`. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec.

### TEA (verify)
- No deviations from spec. The simplify findings were dismissed (not deviations — judgment call on misclassification, rationale in TEA Assessment §Dismissed Findings); the ruff auto-fix is a style cleanup, not a behavior change.

### TEA (verify — rework iteration)
- No deviations from spec. Two high-confidence simplify findings (parametrize tuple-validation tests + extract `_REGISTRIES` dict) applied directly in commit `3ee6a86`; both were structural refactors (no behavior change), corroborated independently by simplify-reuse and simplify-efficiency.

### Architect (spec-check)
- No additional deviations beyond those already logged by TEA and Dev. The implementation matches the story scope (introduce two new named registries, gate the categorization with a reflection test); the architectural extension noted in Delivery Findings (registry-of-applied-projections to make the gate consistency-aware) is deferred to a follow-up story by design — it would require a parallel registry on `_apply_phase_c_projections` and is out of scope for a 3-pt setup. → ✓ ACCEPTED by Reviewer: agrees with author reasoning; the consistency-tightening idea is a real follow-up but not in scope for 61-5.

### Architect (spec-check — rework iteration)
- **Story scope expanded from 3 to 4 registries during reviewer rework.** Spec source: original story description ("Introduce two new registries"). Spec text: only `_PHASE_C_PROJECTIONS` and `_BOUNDED_BY_CONSTRUCTION` were specified. Implementation: rework added a 4th registry `_EXCLUDED_FROM_DUMP` because the reviewer correctly identified that `Field(..., exclude=True)` fields don't fit any of the original three categories cleanly. Rationale: the gate's stated purpose is to bound `model_dump()` output; never-dumped fields belong in their own bucket so removing `exclude=True` forces re-categorization. Severity: minor (the scope expansion is in direct response to a substantive architectural defect the original spec didn't anticipate). Forward impact: future fields with `exclude=True` use this registry; the precedent is established and tested.

### Reviewer (audit)
- **`exclude=True` fields misclassified as bounded-by-construction:** Spec said the gate exists to bound `model_dump()` size (per `_PHASE_C_PROJECTIONS` docstring at session_helpers.py:104-106). Code classifies `pending_magic_auto_fires` and `pending_magic_confrontation_outcome` (both `Field(..., exclude=True)` at session.py:798-799) as `_BOUNDED_BY_CONSTRUCTION` — but they are never in the dump at all. Not documented by TEA/Dev. **Severity: H.** This is a category error in the architectural gate the story introduces. See Reviewer Assessment §Issue A for the fix shape.
- **AC7 sentinel does not protect `narrative_log`:** Spec implies the legacy-protection test guards every "expected drop entry" against regression. Code's `legacy_four` set hardcodes only the four pre-61-2 entries — but `narrative_log` was added to `_PHASE_B_DROP_FIELDS` in this same diff. Not documented by Dev. **Severity: M.** See Reviewer Assessment §Issue D.

### Dev (implementation)
- **Extended `_PHASE_B_DROP_FIELDS` to include `narrative_log`**
  - Spec source: AC1, AC3 (every snapshot field in exactly one registry)
  - Spec text: "_PHASE_B_DROP_FIELDS … (already in session_helpers.py:64)"
  - Implementation: Added `narrative_log` as a 5th entry. It was already being dropped via a separate `state_summary_payload.pop("narrative_log", None)` at line 802 (story 49-1), but was not in the named registry — so the gate would have flagged it as unclassified. Extending the registry unifies the drop mechanism into a single source of truth. The explicit pop remains for defense-in-depth (both operations are idempotent).
  - Rationale: The gate's mission is "named registries = single source of truth." Leaving `narrative_log` out would have required either a fourth registry or classification as "bounded" (a lie, since it's actually dropped).
  - Severity: minor
  - Forward impact: A follow-up story can remove the redundant explicit pop and rely solely on the loop. The current state is correct and idempotent.

- **Three borderline growers classified as BOUNDED_BY_CONSTRUCTION instead of PROJECTIONS**
  - Spec source: Story description §"_BOUNDED_BY_CONSTRUCTION (new, for fields whose growth is bounded by their own structure — scalar fields, enum fields, fixed-size collections)"
  - Spec text: a strict reading would exclude growing `list[X]` fields (like `lore_established`, `world_history`, `npc_pool`) from BOUNDED
  - Implementation: Placed all three in `_BOUNDED_BY_CONSTRUCTION` with an explicit docstring comment explaining the rationale per field — `world_history` is P3-deferred (empty in live builds per `session.py:684`), `npc_pool` is the anti-confabulation anchor (cannot be projected without breaking gaslighting doctrine per context-story-61-2.md), `lore_established` is small-by-gameplay-convention.
  - Rationale: Adding projection logic for these three is outside the 3-pt story scope ("introduce the two registries + gate test"). The gate's primary value is forcing the conversation for NEW fields; existing classification can be refined by follow-up stories. The docstring comment is a forward-pointing flag if any of the three grows large in play.
  - Severity: minor
  - Forward impact: A future story may move `lore_established` to `_PHASE_C_PROJECTIONS` with a tail-K projection if growth in long campaigns becomes problematic. `npc_pool` is a load-bearing anchor and is unlikely to move. `world_history` will become a live decision once campaign-maturity / world-materialization (P3) is implemented.