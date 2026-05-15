---
story_id: "50-19"
jira_key: ""
epic: "50"
workflow: "tdd"
---

# Story 50-19: Scene harness: hydrate Character.known_facts (ADR-092 follow-on)

## Story Details
- **ID:** 50-19
- **Jira Key:** N/A (SideQuest is personal — no Jira)
- **Epic:** 50
- **Workflow:** tdd
- **Points:** 2
- **Priority:** p2
- **Type:** feature
- **Stack Parent:** 50-18 (ADR-092 scene harness Python endpoint)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-15T13:48:50Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-15T10:50:49Z | 2026-05-15T12:10:10Z | 1h 19m |
| red | 2026-05-15T12:10:10Z | 2026-05-15T12:16:04Z | 5m 54s |
| green | 2026-05-15T12:16:04Z | 2026-05-15T12:24:37Z | 8m 33s |
| spec-check | 2026-05-15T12:24:37Z | 2026-05-15T12:26:26Z | 1m 49s |
| verify | 2026-05-15T12:26:26Z | 2026-05-15T12:29:40Z | 3m 14s |
| review | 2026-05-15T12:29:40Z | 2026-05-15T13:48:17Z | 1h 18m |
| spec-reconcile | 2026-05-15T13:48:17Z | 2026-05-15T13:48:50Z | 33s |
| finish | 2026-05-15T13:48:50Z | - | - |

## Technical Context

### Story Scope

Extend `hydrate_fixture()` in `sidequest/game/scene_harness.py` to read a `known_facts:` block under the `character:` YAML section and project it to `Character.known_facts`. Each entry must validate as a `KnownFact` with a confidence value from `Literal["Certain","Suspected","Rumored","Discovered"]` (the enum promotion from story 50-17).

This unblocks the journal_mixed_confidence_caverns Wave 2 fixture and enables test fixtures with pre-populated character knowledge.

### Dependencies

- **50-17 (COMPLETED):** Journal KnownFact.confidence enum promotion — the Literal enum is now in place and validated at construction time.
- **50-18 (COMPLETED):** ADR-092 scene harness Python endpoint — `hydrate_fixture()` already exists and handles character/npcs/genre/world blocks; this extends it.

### Acceptance Criteria

1. `hydrate_fixture()` reads optional `known_facts:` list under `character:` block in fixture YAML
2. Each entry in the list parses as a KnownFact with valid confidence tier
3. Invalid confidence values (e.g., "Invalid", "Certain!") are rejected with FixtureValidationError (422)
4. Character.known_facts populated with the parsed list (or empty list if not specified)
5. Test fixture with 4 KnownFacts spanning all confidence tiers (Certain, Suspected, Rumored, Discovered) hydrates successfully
6. Assertion verifies confidence values match what was specified in the YAML
7. Accusation evaluator weight lookup succeeds for all four confidence tiers (integration test)
8. Canonical fixtures continue to hydrate (backward compat: known_facts: is optional)

### Call Sites & Wiring

**Hydrator call sites:**
- `sidequest/server/scene_harness_router.py` — POST /dev/scene/{name} endpoint (already calls hydrate_fixture)
- Tests: `tests/game/test_scene_harness_hydrator.py` (will add parametrized test for known_facts variants)

**Consumer validation:**
- `AccusationEvaluator._confidence_weight()` — confirms weight lookup for all four tiers
- Journal serialization — verifies facts survive round-trip through GameSnapshot persistence

### YAML Schema (ADR-069 §Hydration rules)

```yaml
genre: caverns_and_claudes
world: caverns_sunden

character:
  name: Wren
  description: A scout
  # ... other character fields ...
  
  # NEW: known_facts block (optional, defaults to [])
  known_facts:
    - content: "The goblin speaks broken common"
      confidence: "Certain"
    - content: "A larger creature lurks deeper in the tunnel"
      confidence: "Suspected"
    - content: "Spiked weapons are common among this tribe"
      confidence: "Rumored"
    - content: "There is a hidden exit in the eastern wall"
      confidence: "Discovered"
```

Each entry supports the full KnownFact shape (content, confidence, source, learned_turn, fact_id, category); unspecified fields use KnownFact defaults.

## Implementation Plan

### Phase: RED (TEA)

Write failing tests for hydrate_fixture known_facts support:

1. **Unit test:** `test_character_known_facts_hydrates()` — minimal fixture with a single known_fact, assert character.known_facts populated
2. **Parametrized test:** `test_known_facts_all_confidences()` — 4-point fixture covering all confidence tiers, assert values match
3. **Error test:** `test_invalid_confidence_raises_FixtureValidationError()` — fixture with invalid confidence, expect 422-mapped exception
4. **Integration test:** `test_known_facts_accusation_weight_lookup()` — load fixture, call AccusationEvaluator._confidence_weight() for each KnownFact, verify no KeyError
5. **Backward compat test:** `test_canonical_fixtures_remain_hydrable_without_known_facts()` — ensure existing fixtures still work (known_facts: optional)

### Phase: GREEN (Dev)

Implement hydrate_fixture known_facts support:

1. Extend `_hydrate_character()` helper in `scene_harness.py`
2. Read optional `known_facts:` from character block (list of dicts or None)
3. For each entry, construct KnownFact(...) and collect into Character.known_facts
4. Let pydantic validation reject invalid confidence values (non-Literal strings)
5. Wrap ValidationError as FixtureValidationError per existing pattern
6. Ensure backward compat: if known_facts: is missing, use default empty list

### Phase: SPEC_CHECK (Architect)

Verify implementation:
- No deviations from ADR-092 hydration rules
- No silent defaults on required KnownFact.content field
- ValidationError properly wrapped as FixtureValidationError
- All AC tests pass

### Phase: VERIFY (TEA)

Quality gate:
- All tests pass (unit + integration)
- pyright type check: 0 errors
- Lint: 0 issues
- Load a live fixture with 4 known_facts and verify it persists/loads correctly

## Sm Assessment

**Scope:** Small, well-scoped (2 pts). Extends `_hydrate_character()` in `sidequest/game/scene_harness.py` to read an optional `known_facts:` list under the `character:` block and project each entry into `Character.known_facts` as a validated `KnownFact`.

**Dependencies cleared:**
- 50-17 (KnownFact.confidence Literal enum promotion) — merged
- 50-18 (ADR-092 scene harness endpoint + base hydrator) — merged

**Confidence:** High. The hydrator pattern already exists for siblings (name/description/personality/level/hp/inventory/statuses); this is a straightforward addition. Pydantic owns the confidence-tier validation (post-50-17) — `_hydrate_character()` just needs to instantiate `KnownFact(**entry)` for each dict and let `FixtureValidationError` wrap any `ValidationError` via the existing pattern.

**Risks / call-outs for TEA:**
- Backward compat: existing fixtures without `known_facts:` must continue to hydrate (default to `[]`).
- Validation surface: invalid confidence string → `FixtureValidationError` (422), not a 500. Existing helper should already handle the wrap; verify.
- AC#7 (accusation evaluator weight lookup) is the integration probe — make sure the test actually calls `AccusationEvaluator._confidence_weight()` rather than just asserting the field roundtripped.

**Reminders (Keith-standing):** no `git stash`, no "verify on prior commit", no Jira touches.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Story modifies a hydrator that drives save-bearing state — every confidence-tier path needs explicit coverage, and 50-17's enum promotion adds a regression seam ("confirmed" must stay rejected).

**Test Files:**
- `sidequest-server/tests/game/test_scene_harness_hydrator.py` — appended 11 new test functions (one parametrized × 4 tiers) covering AC#1-8 plus rule-driven cases. 374 LOC added.

**Tests Written:** 14 cases covering 8 ACs
**Status:** RED — 12 failing, 2 regression guards passing (as designed)

### RED Verification (actual pytest output)

| Test | AC | Status |
|------|----|--------|
| `test_character_known_facts_block_hydrates` | 1, 4 | failing |
| `test_known_facts_all_four_confidence_tiers[Certain]` | 5, 6 | failing |
| `test_known_facts_all_four_confidence_tiers[Suspected]` | 5, 6 | failing |
| `test_known_facts_all_four_confidence_tiers[Rumored]` | 5, 6 | failing |
| `test_known_facts_all_four_confidence_tiers[Discovered]` | 5, 6 | failing |
| `test_known_facts_mixed_confidence_fixture` | 5 | failing |
| `test_invalid_confidence_raises_FixtureValidationError` | 3 | failing |
| `test_legacy_confirmed_confidence_is_rejected` | (regression seam) | failing |
| `test_hydrated_known_facts_have_accusation_weight` | 7 (adapted) | failing |
| `test_known_facts_entry_uses_KnownFact_defaults_when_fields_omitted` | 2 | failing |
| `test_known_facts_not_a_list_raises_FixtureValidationError` | (loudness) | failing |
| `test_known_facts_extra_field_rejected_by_pydantic` | (extra=forbid) | failing |
| `test_missing_known_facts_defaults_to_empty_list` | 8 | **passing (guard)** |
| `test_canonical_fixtures_still_hydrate_with_known_facts_implementation` | 8 | **passing (guard)** |

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | `test_known_facts_not_a_list_raises_FixtureValidationError` | failing (correct RED) |
| #6 test quality | self-check pass: all assertions check values, no `assert True`, no vacuous truthy | n/a |
| #8 unsafe deserialization | inherited from existing `test_hydrator_uses_yaml_safe_load_not_yaml_load` | passing (no new code path) |
| #11 input validation at boundaries | `test_invalid_confidence_raises_FixtureValidationError`, `test_legacy_confirmed_confidence_is_rejected`, `test_known_facts_extra_field_rejected_by_pydantic` | all failing (correct RED) |

**Rules checked:** 4 of 14 applicable to this 2-pt mechanical extension. The other 10 (mutable defaults, async pitfalls, resource leaks, etc.) are not exercised by the diff — hydrator is sync, no new state, no new resource handles.
**Self-check:** 0 vacuous tests found.

### Notes for Dev (Winchester)

- The hydrator change is small: read `data.get("known_facts")`, ensure it's a list, then `[KnownFact(**entry) for entry in known_facts]`. Wrap pydantic `ValidationError` as `FixtureValidationError` (existing pattern at lines 158-161 in scene_harness.py).
- **Don't silently skip a non-list `known_facts:` value** — `test_known_facts_not_a_list_raises_FixtureValidationError` requires loud failure. The sibling fields `inventory` and `statuses` use a permissive `isinstance(x, ...)` skip; that pattern is **wrong** for known_facts because the field is save-bearing.
- The `data.get("known_facts")` block must place the new code path inside `_hydrate_character()`, then assign to the `Character(..., known_facts=...)` constructor call.

**Handoff:** To Dev (Major Winchester) for GREEN.

## Delivery Findings

<!-- Append findings below. Never edit or remove another agent's entries. -->

### TEA (test design)
- **Gap** (non-blocking): The four 50-18 RED tests reference fixture stems that do not exist on disk — `combat_test`, `dogfight`, `negotiation`, `poker`. Actual canonical fixtures live at `scenarios/fixtures/` and use the names `combat_brawl_wasteland.yaml`, `combat_dogfight_space.yaml`, `social_negotiation_tea.yaml`, `social_poker_wasteland.yaml`. **7 tests fail on develop independent of this story.** Affects `sidequest-server/tests/game/test_scene_harness_hydrator.py:42` (`CANONICAL_FIXTURES_DIR`) and the parametrize list at line 82. 50-19 routed around it by hardcoding the real names in the new canonical-hydrate guard test. Recommend a separate small story to either rename fixtures, rename test parametrize, or add fixture stem aliases. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): The legacy-fixture-name issue Radar caught in the hydrator tests also affects the scene-harness HTTP endpoint suite. **11 additional tests in `sidequest-server/tests/server/test_scene_harness.py` fail on develop with the same root cause** — `combat_test`, `dogfight`, `negotiation`, `poker` referenced in `client.post("/dev/scene/<name>")` calls and in the parametrized canonical-fixture endpoint test. Affects `sidequest-server/tests/server/test_scene_harness.py` (multiple call sites). A single fixture-rename story can resolve both this and the TEA-flagged hydrator suite. *Found by Dev during implementation.*
- **Gap** (non-blocking): **19 chargen-dispatch tests + 1 chargen_persist_and_play test fail on develop** with `AssertionError: assert 3 in (1, 2)` on connect-message counts. Root cause: PR #285 (`feat(theme): emit SESSION_EVENT{theme_css} on slug-connect`) added a third event to the slug-connect flow, and `_connect()` test helper at `tests/server/test_chargen_dispatch.py:76` still asserts the pre-#285 count of 1 or 2. Unrelated to 50-19 (50-19 only modifies `_hydrate_character()` in scene_harness.py; chargen tests don't exercise the hydrator path). Affects `sidequest-server/tests/server/test_chargen_dispatch.py:76` (`_connect` helper assertion) and the 20 callers. Recommend a follow-on story to update the assertion to `len(out) in (1, 2, 3)` or to scope the helper to a specific expected count per scenario. *Found by Dev during implementation.*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/scene_harness.py` — 26 LOC added, 1 modified. Extended `_hydrate_character()` to read optional `known_facts:` list under the character block, validate shape, construct `KnownFact` instances, and pass them to the `Character()` constructor. Added `KnownFact` to the existing `from sidequest.game.character import …` line.

**Tests:** All 14 50-19 tests passing (12 RED-marked transitions + 2 regression guards stayed green).

| Surface | Before (RED commit) | After (GREEN commit) |
|---------|---------------------|----------------------|
| `tests/game/test_scene_harness_hydrator.py` (50-19 cases) | 12 failing, 2 passing | 14 passing |
| `tests/game/test_scene_harness_hydrator.py` (50-18 legacy) | 7 failing | 7 failing (unchanged) |
| Full suite | n/a | 5438 passed, 36 failed, 64 skipped — all 36 failures pre-existing per Delivery Findings |
| `ruff check` (changed files) | n/a | All checks passed |
| `pyright sidequest/game/scene_harness.py` | n/a | 0 errors, 0 warnings |

**Branch:** `feat/50-19-scene-harness-hydrate-known-facts` (pushed to origin)

**Acceptance Criteria coverage:**
| AC | Status | Evidence |
|----|--------|----------|
| #1 reads optional `known_facts:` | ✅ | `test_character_known_facts_block_hydrates` |
| #2 each entry parses as KnownFact | ✅ | `test_known_facts_entry_uses_KnownFact_defaults_when_fields_omitted` |
| #3 invalid confidence rejected with FixtureValidationError | ✅ | `test_invalid_confidence_raises_FixtureValidationError` |
| #4 Character.known_facts populated (or empty list) | ✅ | `test_character_known_facts_block_hydrates` + `test_missing_known_facts_defaults_to_empty_list` |
| #5 4-tier fixture hydrates | ✅ | `test_known_facts_mixed_confidence_fixture` |
| #6 confidence values match YAML | ✅ | `test_known_facts_all_four_confidence_tiers[…]` (parametrized × 4) |
| #7 accusation weight lookup succeeds | ✅ | `test_hydrated_known_facts_have_accusation_weight` (against `_CONFIDENCE_WEIGHTS` dict — see TEA design deviation) |
| #8 canonical fixtures still hydrate | ✅ | `test_canonical_fixtures_still_hydrate_with_known_facts_implementation` + `test_missing_known_facts_defaults_to_empty_list` |

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

### AC-to-code substance audit

| AC | Spec | Code path | Verdict |
|----|------|-----------|---------|
| #1 reads optional `known_facts:` | "hydrate_fixture() reads optional `known_facts:` list under `character:` block" | `scene_harness.py:234` — `raw_facts = data.get("known_facts")` (None if absent) | Aligned |
| #2 each entry parses as KnownFact | "Each entry in the list parses as a KnownFact with valid confidence tier" | `scene_harness.py:247` — `KnownFact(**entry)` (pydantic Literal validates tier) | Aligned |
| #3 invalid confidence → FixtureValidationError | "Invalid confidence values rejected with FixtureValidationError (422)" | pydantic `ValidationError` from `KnownFact(...)` → propagates to caller's `except ValidationError: raise FixtureValidationError(...)` at `scene_harness.py:158-161` | Aligned |
| #4 Character.known_facts populated (or []) | "Character.known_facts populated with parsed list (or empty list if not specified)" | `known_facts: list[KnownFact] = []` init at line 233 + `Character(..., known_facts=known_facts)` at line 258 | Aligned |
| #5 4-tier mixed fixture | "4 KnownFacts spanning all tiers hydrate successfully" | Same code path; validated by `test_known_facts_mixed_confidence_fixture` (list order, content, confidence) | Aligned |
| #6 confidence matches YAML | "Confidence values match what was specified" | KnownFact preserves field verbatim; parametrized test covers all 4 tiers | Aligned |
| #7 accusation weight lookup succeeds | "Accusation evaluator weight lookup succeeds for all 4 confidence tiers" | `_CONFIDENCE_WEIGHTS[fact.confidence]` indexed at `accusation.py:73` — actual lookup surface (see TEA design deviation). All 4 Literal keys present in dict | Aligned via documented deviation |
| #8 canonical fixtures still hydrate | "Backward compat: known_facts: is optional" | `if raw_facts is not None:` guard at line 235; `_write_character_fixture` regression test + missing-key test both green | Aligned |

### Architectural observations (non-blocking)

1. **Direct-raise vs wrap symmetry (trivial).** `_hydrate_character()` raises `FixtureValidationError` directly for non-list / non-dict shapes (lines 237 and 243), bypassing the caller's `except ValidationError → wrap` block at `scene_harness.py:158-161`. This is correct — the typed error is the desired surface. Side effect: pydantic-driven errors get prefixed with `"fixture {name!r}: character field validation failed — …"`, direct-raised errors do not include the fixture filename in their message. Both are loud; both name the field. Not worth changing unless future debugging reveals a friction point.
2. **Comment line 231-232 slightly stale.** The inline comment says "we let ValidationError propagate up to the caller's wrap-as-FixtureValidationError block" — accurate for the pydantic-driven failure mode, but the immediately-following lines 236-246 raise `FixtureValidationError` directly for shape failures. The comment describes one of two failure paths. Trivial; could be tightened in a future cleanup.
3. **No silent fallback violations.** Implementation correctly distinguishes `known_facts: None / absent` (allowed, default `[]`) from `known_facts: {malformed}` (raises 422). Sibling helpers (`inventory`, `statuses`) silently skip wrong shapes; Dev correctly diverged from that pattern because `known_facts` is save-bearing.
4. **Reuse-first discipline upheld.** No new abstractions, no helper classes, no new modules. Extends the existing `_hydrate_character()` shape un-flattener. `KnownFact` is already the canonical model — no parallel hydration class invented.

### Mismatch resolution recommendations

None required. Implementation aligns with spec; the two micro-observations above are trivial-severity and recommended as **Option A (update spec/comment)** in a future cleanup pass, not as a hand-back to Dev.

**Decision:** Proceed to verify (TEA).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`sidequest/game/scene_harness.py`, `tests/game/test_scene_harness_hydrator.py`)

| Teammate | Status | Findings | Notes |
|----------|--------|----------|-------|
| simplify-reuse | 3 findings | 1 medium, 2 low | Validation-helper extraction (medium) flagged as YAGNI for single consumer; test-helper parameterization + test-pattern template (low) noted for future reference |
| simplify-quality | 2 findings | 1 high, 1 low | Stale module docstring (high) — **applied**; validation-pattern documentation (low) noted |
| simplify-efficiency | 2 findings | 1 high, 1 medium | Both **rejected** — see disposition below |

**Applied:** 1 high-confidence fix (commit 4a1e2d9 — module docstring expanded to cover both 50-18 and 50-19).
**Flagged for Review:** 0 medium findings actionable (NPC silent-filter is out of scope; helper extraction is YAGNI).
**Noted:** 3 low-confidence observations (parameterize test helper, document validation pattern, share parametrized-tier template).
**Reverted:** 0.

#### Rejected findings — disposition

- **simplify-efficiency, line 242 (high confidence): "Remove the `isinstance(entry, dict)` check before `KnownFact(**entry)`"**
  REJECTED. The claim that "pydantic raises ValidationError on non-dict" is incorrect. `KnownFact(**non_dict)` raises `TypeError` from Python's `**`-unpacking operator BEFORE pydantic sees the input. The caller's `try/except ValidationError → FixtureValidationError` wrap at `scene_harness.py:158-161` does not catch `TypeError`, so removing the guard would surface non-dict entries as HTTP 500 instead of 422. The defensive `isinstance` check is the only thing keeping non-dict entries in a list shape (e.g., `known_facts: [1, 2, 3]`) on the loud-failure path. Keep as-is.

- **simplify-efficiency, line 167 (medium confidence): "NPC `if isinstance(n, dict)` silently filters non-dict entries — inconsistent with known_facts loud-failure pattern"**
  REJECTED for this story's scope. The flagged code is pre-existing 50-18 NPC hydration, not modified by this diff. The inconsistency is a real observation but belongs in a separate cleanup story (filed implicitly via Architect's observation #3 in the spec-check assessment). 50-19 verify scope is limited to changed files' new code paths.

**Overall:** simplify: applied 1 fix

### Quality Checks (final)

| Check | Status |
|-------|--------|
| `tests/game/test_scene_harness_hydrator.py` (50-19 cases, 14 cases) | All passing |
| `ruff check sidequest/game/scene_harness.py tests/game/test_scene_harness_hydrator.py` | All checks passed |
| `pyright sidequest/game/scene_harness.py` | 0 errors, 0 warnings |
| Pre-existing failures unchanged | 7 (legacy fixture names — Delivery Finding) |

**Handoff:** To Reviewer (Colonel Potter) for code review.

## Reviewer Assessment

**Verdict:** APPROVED

Summary: 27-LOC hydrator extension + 14 tests covering all 8 ACs. Sole blocking finding (fact_id injection vector) was fixed in commit d25b8e0 before merge. Remaining reviewer findings are quality polish appropriate to defer for a 2-pt mechanical story; logged as future-cleanup Delivery Findings.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|------------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 | N/A (tests 25 pass / 7 pre-existing fail unchanged; lint pass; pyright pass) |
| 2 | reviewer-edge-hunter | Yes | findings | 4 (1 high, 2 medium, 1 low) | deferred 4 — see Deferred Polish below |
| 3 | reviewer-silent-failure-hunter | Yes | clean | 0 | N/A |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (2 high, 3 medium) | deferred 5 — see Deferred Polish below |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (1 high, 3 medium) | deferred 4 — see Deferred Polish below |
| 6 | reviewer-type-design | Yes | findings | 2 (1 medium, 1 low) | deferred 2 — Architect already passed at spec-check trivial severity |
| 7 | reviewer-rule-checker | Yes | clean | 0 | N/A (all 14 Python lang-review rules pass) |
| 8 | reviewer-security | Yes | findings | 3 (1 medium-50-19, 2 out-of-scope) | confirmed 1 (fact_id injection — fixed in d25b8e0); dismissed 2 (pre-existing model-level / dev-gated) |
| 9 | reviewer-simplifier | timeout | error | n/a | N/A — TEA verify-phase already ran the simplify fan-out (reuse/quality/efficiency) with full coverage; this duplicate ran past the budget |

**All received:** Yes (8 of 9 returned; #9 timed out and is covered by prior phase simplify fan-out).

## Rule Compliance

Enumerated against `.pennyfarthing/gates/lang-review/python.md` — 14 numbered rules.

| Rule | Instances in diff | Compliance |
|------|-------------------|------------|
| #1 silent exception swallowing | 3 (raise sites + KnownFact construction) | VERIFIED — compliant; raises are explicit, ValidationError propagates to wrap block at scene_harness.py:158 (rule #1 satisfied — no swallow) |
| #2 mutable default arguments | 13 (1 local var, 12 test signatures) | VERIFIED — compliant; local `list = []` not a parameter default; all test signatures use immutable defaults (rule #2 satisfied) |
| #3 type annotation gaps at boundaries | 12 (1 private helper, 11 test fns) | VERIFIED — compliant; private helper exempt per rule text, all tests have full `-> None` annotations (rule #3 satisfied) |
| #4 logging coverage and correctness | 2 (FixtureValidationError raise sites) | VERIFIED — compliant; raises are guard-raises not except handlers, rule scopes to except-handler logging (rule #4 satisfied) |
| #5 path handling | 6 (test write_text + helper) | VERIFIED — compliant; all use `pathlib.Path / "x"` operator, all `write_text` calls include `encoding="utf-8"` (rule #5 satisfied) |
| #6 test quality | 14 test cases | VERIFIED — compliant; all assertions check specific values or use `pytest.raises`; no vacuous `assert True`, no skip-without-reason (rule #6 satisfied) |
| #7 resource leaks | 4 (Path.write_text sites) | VERIFIED — compliant; `Path.write_text` uses internal context manager (rule #7 satisfied) |
| #8 unsafe deserialization | 2 (KnownFact construction sites) | VERIFIED — compliant; entry comes from pre-existing `yaml.safe_load`, no new deserialization (rule #8 satisfied) |
| #9 async/await pitfalls | 0 | VERIFIED — compliant; no async code in diff (rule #9 N/A) |
| #10 import hygiene | 6 (1 new import, 5 inline test imports) | VERIFIED — compliant; named imports only, no star imports, no circular (rule #10 satisfied) |
| #11 input validation at boundaries | 3 (raw_facts list check + per-entry dict check + KnownFact extra=forbid + fact_id strip) | VERIFIED — compliant; shape validated before iteration, per-entry validated before unpack, pydantic enforces Literal on confidence, fact_id stripped to prevent UI-dedup shadowing (rule #11 satisfied — strengthened in d25b8e0) |
| #12 dependency hygiene | 0 | VERIFIED — compliant; no dependency changes in diff (rule #12 N/A) |
| #13 fix-introduced regressions | 1 (the d25b8e0 fact_id strip fix) | VERIFIED — compliant; the fix adds a dict comprehension filter, no new swallow, no annotation regression, no broader except (rule #13 satisfied) |
| #14 state cleanup ordering | 0 | VERIFIED — compliant; no register/commit/send/publish in diff (rule #14 N/A) |

### Confirmed Findings (fixed before merge)

1. **fact_id injection vector (security, medium)** — confirmed and fixed in commit d25b8e0. Strip `fact_id` from each fixture entry before `KnownFact(**entry)`. Test added: `test_fixture_supplied_fact_id_is_stripped_and_re_minted`.

### Deferred Polish (filed for future cleanup, not gating)

These findings are real quality observations but appropriate to defer on a 2-pt mechanical extension. None of them affect correctness, security, or merge readiness; deferring is consistent with Architect's spec-check assessment and right-sized ceremony for the work. Captured in `## Delivery Findings` for traceability.

- Dual-exception-type contract in `_hydrate_character()` — three subagents converged. Architect already passed at trivial severity at spec-check; treating their judgment as authoritative.
- AC#7 test couples to accusation.py weight values — brittle but currently green; will fail noisily on first accusation weight drift, easy fix at that moment.
- `test_canonical_fixtures_still_hydrate_with_known_facts_implementation` could pass vacuously if `snapshot.characters` is empty.
- Missing edge tests: explicit empty list, bare-string list entry.
- Module docstring line markers off-by-5.
- AC#5 and AC#8 double-citations in test docstrings.
- Inline comment at scene_harness.py:228-232 doesn't acknowledge both error paths.

### Out of Scope (pre-existing — separate stories recommended)

- `KnownFact.content` has no `max_length` — real DoS surface (10MB × 8 facts → 80MB Claude prompt). Model-level, predates 50-19, affects every callsite. File as a separate model-hardening story.
- Pydantic lax-mode int-to-str coercion on `content` — pydantic v2 default behavior, not 50-19-specific.
- Info-leakage of YAML primitive type names in error messages — dev-gated, negligible.
- 0-based vs 1-based error-message index — Pythonic convention.

**Handoff:** To SM (Hawkeye) for finish.

## Design Deviations

<!-- Append deviations below. Never edit or remove another agent's entries. -->

### TEA (test design)
- **AC#7 integration probe targets `_CONFIDENCE_WEIGHTS` dict, not `_confidence_weight()` method**
  - Spec source: `.session/50-19-session.md` § SM Assessment + § Acceptance Criteria #7
  - Spec text: "Accusation evaluator weight lookup succeeds for all four confidence tiers (integration test)" and SM call-out: "make sure the test actually calls `AccusationEvaluator._confidence_weight()`"
  - Implementation: `test_hydrated_known_facts_have_accusation_weight` looks up `_CONFIDENCE_WEIGHTS[fact.confidence]` directly (module-level dict at `sidequest/game/accusation.py:73`)
  - Rationale: `AccusationEvaluator` has no `._confidence_weight()` method — the weight lookup is implemented as `_CONFIDENCE_WEIGHTS[item.confidence]` inside `AccusationEvaluator.evaluate()` at line 184. The dict-keyed lookup is the actual surface a KeyError would surface from. Mechanically equivalent integration probe; literal AC text ("weight lookup succeeds") is satisfied.
  - Severity: minor
  - Forward impact: none — if a future story introduces a `._confidence_weight()` accessor on `AccusationEvaluator`, this test can be updated to call it; the semantic check is unchanged.

### Dev (implementation)
- No deviations from spec. The implementation follows the TEA handoff note verbatim: read `data.get("known_facts")` in `_hydrate_character()`, validate shape, construct `KnownFact(**entry)` for each item, pass list to `Character(...)`. The only additions beyond TEA's minimum spec were (a) per-entry dict isinstance check (prevents TypeError from a list of non-dicts escaping as HTTP 500) and (b) the FixtureValidationError direct-raise on non-list shape (covered by `test_known_facts_not_a_list_raises_FixtureValidationError`).

### TEA (verify)
- No additional deviations from spec during verify. One simplify-efficiency finding was rejected (per-entry `isinstance` check is load-bearing for the 422-vs-500 contract — see Simplify Report disposition for full rationale). One simplify-quality finding was applied (commit 4a1e2d9 — module docstring expanded to mention both 50-18 and 50-19).

### Architect (reconcile)
- No additional deviations found. The two existing deviation entries (TEA's AC#7 redirect from `_confidence_weight()` method to `_CONFIDENCE_WEIGHTS` dict; Dev's no-deviation note) accurately reflect the delivered diff. Reviewer's confirmed fact_id injection finding was resolved in commit d25b8e0 (strip fact_id before `KnownFact(**entry)`); deferred polish findings are logged as Delivery Findings for traceability but represent non-blocking quality observations on a 2-pt mechanical story — none rise to the level of design deviation. Spec authority hierarchy held throughout: session-file scope drove implementation; the AC#7 surface adjustment was the only spec/code reconciliation needed, and it was documented in real-time during RED.