---
story_id: "43-1"
jira_key: null
epic: "43"
workflow: "tdd"
---
# Story 43-1: Remove LoRA fields (lora, lora_trigger, lora_scale, lora_path) from VisualStyle schema and genre pack YAMLs — per ADR-070 supersession

## Story Details
- **ID:** 43-1
- **Epic:** 43 (Dead Code Cleanup)
- **Jira Key:** (none — not yet created)
- **Workflow:** tdd
- **Branch:** feat/43-1-remove-lora-fields-visualstyle
- **Stack Parent:** none
- **Points:** 2
- **Priority:** p2
- **Type:** refactor

## Story Context

**Superseded By:** ADR-070 and ADR-086. The LoRA pipeline (ADRs 032/083/084) is now dead code following the Z-Image Turbo renderer pivot on 2026-04-24.

**Scope:** Remove LoRA-related fields from the VisualStyle schema definition and any genre pack YAML files that reference them.

**Acceptance Criteria:**
1. `lora`, `lora_trigger`, `lora_scale`, and `lora_path` fields are removed from the VisualStyle Pydantic model in sidequest-server
2. All genre_packs YAML files (visual_style.yaml, pack.yaml) with any lora_ field references are cleaned
3. No remaining references to lora_ fields exist in server or daemon code (verified via grep)
4. All tests pass; no broken imports or references remain

**Repos:** server, content

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-04-27T16:29:42Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-04-27T15:49:27Z | 2026-04-27T15:52:23Z | 2m 56s |
| red | 2026-04-27T15:52:23Z | 2026-04-27T15:58:24Z | 6m 1s |
| green | 2026-04-27T15:58:24Z | 2026-04-27T16:03:19Z | 4m 55s |
| spec-check | 2026-04-27T16:03:19Z | 2026-04-27T16:04:44Z | 1m 25s |
| verify | 2026-04-27T16:04:44Z | 2026-04-27T16:06:48Z | 2m 4s |
| review | 2026-04-27T16:06:48Z | 2026-04-27T16:14:19Z | 7m 31s |
| red | 2026-04-27T16:14:19Z | 2026-04-27T16:17:52Z | 3m 33s |
| green | 2026-04-27T16:17:52Z | 2026-04-27T16:18:43Z | 51s |
| spec-check | 2026-04-27T16:18:43Z | 2026-04-27T16:19:37Z | 54s |
| verify | 2026-04-27T16:19:37Z | 2026-04-27T16:22:03Z | 2m 26s |
| review | 2026-04-27T16:22:03Z | 2026-04-27T16:28:34Z | 6m 31s |
| spec-reconcile | 2026-04-27T16:28:34Z | 2026-04-27T16:29:42Z | 1m 8s |
| finish | 2026-04-27T16:29:42Z | - | - |

## Sm Assessment

Setup complete. Story 43-1 is the first slice of Epic 43 (Dead Code Cleanup). Scope is bounded: LoRA fields drop out of the VisualStyle model + content YAMLs, with grep-based confirmation that no live caller remains in server/daemon. Risk is low — ADR-070 already superseded ADRs 032/083/084 on 2026-04-24, and downstream stories (43-2 wiring, 43-3 artifacts, 43-4 per-world, 43-5 daemon singleton) handle the rest of the cleanup. TEA's RED phase needs schema-validation tests proving the fields are absent and a content-load test proving genre packs parse cleanly without the fields.

## TEA Assessment

**Tests Required:** Yes
**Phase:** finish
**Status:** RED (10 failing, 4 passing — ready for Dev)

**Test Files:**
- `sidequest-server/tests/genre/test_models/test_character.py` — added `TestVisualStyleLoraFieldsRemoved` (6 tests covering AC1 schema removal + validator removal + extra='allow' backwards-compat).
- `sidequest-server/tests/genre/test_visual_style_lora_removal_wiring.py` — new wiring file (8 tests: production-source grep for `.lora*` attribute access, loader integration on `heavy_metal`, legacy-YAML tolerance via `tmp_path`, declared-field surface lockdown, parametrized per-field removal guard).

**Tests Written:** 14 new tests covering 4 ACs.
**RED verification:** `uv run pytest tests/genre/test_models/test_character.py::TestVisualStyleLoraFieldsRemoved tests/genre/test_visual_style_lora_removal_wiring.py -v` → 10 failed, 4 passed. The 4 currently-passing tests are correct guards (lora_path was never declared; no `.lora*` attribute access exists in server source today; heavy_metal loads cleanly). They will continue to pass through GREEN as preservation tests.

**Pre-existing tests that Dev must remove in GREEN:**
- `tests/genre/test_models/test_character.py::TestVisualStyle::test_lora_scale_validation`
- `tests/genre/test_models/test_character.py::TestVisualStyle::test_lora_scale_rejects_above_2`
- `tests/genre/test_models/test_character.py::TestVisualStyle::test_lora_scale_rejects_negative`

These three tests pin behaviour that AC1 explicitly removes. Leaving them in place would block the GREEN phase. They are listed under Delivery Findings as a `Gap (non-blocking)` so Dev sees them.

### Rule Coverage

| Rule (Python lang-review) | Test(s) | Status |
|---------------------------|---------|--------|
| #6 test-quality (no vacuous assertions) | All 14 new tests carry meaningful assertions; self-checked. | passing |
| #6 test-quality (no `assert result` truthy-only) | All assertions check named values/sets/types. | passing |
| #3 type-annotation gaps | New helpers (`_iter_server_python_files`, parametrized fixture) carry annotations. | passing |
| #5 path handling | Wiring test uses `Path` exclusively; `tmp_path` for fixtures. | passing |
| #8 unsafe deserialization | Uses `yaml.safe_dump` / `yaml.safe_load` only. | passing |
| #10 import hygiene | Explicit imports; no star-imports. | passing |

**Rules checked:** 6 of 13 lang-review checks have direct test artefacts; the remaining 7 (logging, async, security input validation, deps, mutable defaults, resource leaks, fix-regressions) are not implicated by a deletion-only refactor.

**Self-check:** No vacuous assertions found (`assert True`, `assert is_none()` on always-None, `let _`-equivalents). Every test asserts a named field, value, or set difference.

**Handoff:** To Dev for implementation (GREEN — drop fields, remove validator, delete the three superseded tests above).

## TEA Assessment (red rework — round 2)

**Phase:** finish (rework after Reviewer REJECT)
**Status:** Tests strengthened per Reviewer findings; all 15 targeted tests pass against the existing GREEN production code (no further Dev work required).

### Reviewer findings addressed

| # | Finding | Resolution |
|---|---------|------------|
| 1 | `[HIGH]` Wiring test never called `load_genre_pack` — claim/code mismatch | **Replaced** `test_visual_style_tolerates_legacy_lora_yaml` (tmp-path direct `model_validate`) with `test_load_pack_with_legacy_lora_block` which calls `load_genre_pack(elemental_harmony)`. That pack carries a live `loras:` block in `visual_style.yaml:51`, so the test now exercises `_load_yaml → VisualStyle.model_validate` end-to-end against real on-disk content. |
| 2 | `[MEDIUM]` Bare truthy assertions on `positive_suffix` / `preferred_model` violate Python lang-review #6 | **Replaced** with substring + equality checks: `assert "Doré" in visual_style.positive_suffix` and `assert visual_style.preferred_model == "dev"` (heavy_metal's known on-disk values verified before commit). |
| 3 | `[LOW]` Parametrized `test_visual_style_field_removed_parametrized` duplicates per-field tests; rule #6 violation | **Deleted** the parametrized function. `test_lora_field_not_declared`, `test_lora_trigger_field_not_declared`, `test_lora_scale_field_not_declared`, `test_lora_path_field_not_declared` in `test_character.py` retain per-field named messages; `test_visual_style_declared_fields_match_post_removal_set` retains the full-set lockdown. Coverage net-equal, redundancy gone. |
| 4 | `[LOW]` Misleading "dict-key fallback" comment on `test_load_clean_pack_yields_visual_style` | **Removed** the comment block (lines 76–79) and switched to direct typed access (`visual_style = pack.visual_style`). The test now claims only what it does. |
| 5 | `[LOW]` `__pydantic_extra__` preservation contract not asserted | **Added** in two places: (a) `test_extra_lora_keys_in_yaml_still_load` asserts `extras.get("lora") == "legacy.safetensors"` etc. for the synthetic-YAML path; (b) `test_load_pack_with_legacy_lora_block` asserts `"loras" in extras` and that the value is a non-empty list, for the real-pack path. A future flip from `extra='allow'` to `'ignore'` would now fail loudly. |

### Additional self-fix

Also cleaned the inline comment inside `test_no_lora_attribute_access_in_production_code` (the "scrub docstrings too" wording the comment-analyzer flagged but Reviewer dismissed). The new comment honestly describes the regex's attribute-only scope and tells future maintainers how to widen it if docstring coverage is ever wanted.

### Test verification

- `uv run pytest tests/genre/test_models/test_character.py tests/genre/test_visual_style_lora_removal_wiring.py -v` → 15 passed (down from 19 because the parametrized 4 cases were intentionally deleted; net coverage is *higher* — one new real-loader test, three preserved per-field guards, one added extras-preservation assertion).
- `uv run pytest` (full server suite) → 2623 passed, 32 skipped, 3 pre-existing failures unchanged from prior runs and unrelated to this story.
- `uv run ruff check {2 changed files}` → 1 pre-existing B017 (unchanged from develop).

### Why this is not a fresh GREEN cycle

The reworked tests pass against the *existing* production code. No `character.py` change is required — Dev's original implementation (drop the three fields + the validator + the unused import + update the comment) was already correct and fully approved by Architect during spec-check. The Reviewer rejected only the *test surface*. With the test surface strengthened, the existing GREEN holds.

**Handoff:** To Dev for confirmation only — running the targeted suite and the lint check on the existing production diff is sufficient. No code change expected. Then back to Architect → TEA verify → Reviewer.

## Dev Assessment (green confirmation — round 2)

**Phase:** finish (post-rework confirmation)
**Status:** Confirmed — TEA's reworked tests pass against the existing production change (`feat: drop LoRA fields from VisualStyle schema`, commit 4641ca6). No new Dev work required.

**Verification:**
- `uv run pytest tests/genre/test_models/test_character.py tests/genre/test_visual_style_lora_removal_wiring.py -v` → 15 passed (TEA's reworked test surface, including the new `test_load_pack_with_legacy_lora_block` exercising `load_genre_pack(elemental_harmony)` end-to-end).
- `git status` → clean (no uncommitted changes).
- `git log develop..HEAD` → 3 commits: original RED tests, GREEN production change, TEA's rework. Production diff is unchanged from round 1 and remains the surgical schema removal Architect approved during spec-check.

**Branches:**
- `sidequest-server`: `feat/43-1-remove-lora-fields-visualstyle` (3 commits, clean).
- `sidequest-content`: `feat/43-1-remove-lora-fields-visualstyle` (no changes — AC2 vacuous for singular-form scope).
- `orchestrator`: `feat/43-1-remove-lora-fields-visualstyle` (session-file changes only).

**Handoff:** To Architect for spec-check.

## Architect Assessment (spec-check — round 2)

**Spec Alignment:** Aligned (same as round-1 modulo Reviewer rework, which was test-only)
**Mismatches Found:** 0 new

The production diff (`character.py`) is byte-identical to round 1, which Architect approved during the first spec-check. The three minor mismatches logged in round 1 (lora_path framing in AC1, AC2 plural-vs-singular ambiguity, AC3 daemon-side coverage owned by 43-2) all stand unchanged — they are spec-clarity matters, not code matters, and Reviewer's REJECT did not alter their disposition.

The TEA rework strengthened the test surface in five concrete ways (real `load_genre_pack(elemental_harmony)` exercising the loader path against a pack with a live `loras:` block; substring/equality assertions replacing truthy checks; deletion of the redundant parametrized guard; honest comments; `__pydantic_extra__` preservation pinned). All five align with the round-1 substantive review and don't introduce new spec drift.

**Decision:** Proceed to verify (TEA simplify + quality-pass). Round-trip count is 1; no further hand-back required from Architect.

## TEA Assessment (verify — round 2)

**Phase:** finish (post-rework simplify + quality-pass)
**Status:** GREEN — 15 targeted tests pass, full server suite stable, lint count unchanged from develop baseline.

### Simplify Report (round 2)

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/genre/models/character.py`, `tests/genre/test_models/test_character.py`, `tests/genre/test_visual_style_lora_removal_wiring.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | findings | 3 — all defer-if-pattern-recurs (extract `_iter_server_python_files`/`_LORA_ATTR_PATTERN` if more cleanup stories follow; `__pydantic_extra__` semantic duplication across two files; `assert_field_removed` helper for future schema removals). |
| simplify-quality | findings | 3 — REPO_ROOT casing (medium), docstring `yield`→`return` mismatch (low), module-level regex placement (low). |
| simplify-efficiency | findings | 2 — both pre-existing on `develop` and outside this diff (`MechanicalEffects` dual `model_config` declaration at lines 40+68; `BackstoryTables.model_validate` premature abstraction). |

**Applied:** 1 fix
- Quality `[LOW]` docstring `Yield`→`Return` on `_iter_server_python_files` (commit c130464). Trivial, correct, no risk.

**Flagged for Review:** 1 medium-confidence finding
- Quality `[MEDIUM]` REPO_ROOT naming. Reasoning for *not* applying: SCREAMING_SNAKE_CASE for module-level Path constants is the *established convention* in this codebase, used identically by `tests/integration/test_group_c_wiring.py:38–39` (`CONTENT_GENRE_PACKS = Path(...)`), `tests/server/test_session_handler_decomposer.py:448`, `tests/server/test_multiplayer_party_status.py:36–37`. Diverging in this single new file would create *inconsistency*, not improvement. The subagent's appeal to "Path objects are mutable" is technically true but does not match this repo's convention. Reviewer should confirm.

**Noted:** 5 low-confidence/defer findings
- Reuse: extract `_iter_server_python_files`/`_LORA_ATTR_PATTERN` into a shared helper if Stories 43-2/43-4 or future cleanup stories duplicate the grep pattern. Currently a one-off; premature to extract. *Defer.*
- Reuse: extract `assert_field_removed(model_class, field_names, validators)` helper if multiple schema-removal stories follow. *Defer.*
- Reuse: `__pydantic_extra__` checks duplicated across two test files. Semantic duplication, not mechanical — one validates the model in isolation (synthetic dict), one validates the loader path (real pack). Both serve distinct contracts. *Defer.*
- Quality: module-level regex per ADR-068 magic-literal scoping. Low confidence; the regex is simple and the test is clear. *Defer.*
- Efficiency: two pre-existing code-smells on `develop` (`MechanicalEffects` dual `model_config`, `BackstoryTables.model_validate` premature abstraction) — out of 43-1's scope; flagged in Delivery Findings as future hygiene. *Defer.*

**Reverted:** 0.

**Overall:** simplify: applied 1 low-risk doc fix; 1 medium flagged for Reviewer; 5 deferred (4 future-extract candidates + 2 pre-existing out-of-scope items collapsed under "defer"). No high-confidence findings within the diff scope.

### Quality Checks (round 2)

- `uv run pytest tests/genre/test_models/test_character.py tests/genre/test_visual_style_lora_removal_wiring.py` → 15 passed.
- `uv run ruff check {3 changed files}` → 1 error (pre-existing `B017` at `test_character.py:45` in `test_extra_forbidden`, unchanged from develop). Branch lint count net −2 vs develop.
- Targeted suite stable across two verify runs (round-1 and now round-2).

**Handoff:** To Reviewer for second review (round 2).

## Subagent Results (round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1 pre-existing B017 unchanged from develop) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 2 (1 medium, 1 low) | confirmed 0, dismissed 1 (downgraded), deferred 1 (pre-existing) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 (1 medium, 1 high-confidence/low-severity) | confirmed 2 (both LOW), dismissed 0, deferred 0 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 1 (low, pre-existing test_extra_allowed) | confirmed 1 (deferred — pre-existing) |

**All received:** Yes (4 active subagents returned, 5 skipped per settings)
**Total findings:** 3 confirmed (all LOW severity), 1 dismissed (downgraded with rationale), 2 deferred (pre-existing out-of-scope)

### Round-1 finding regression check (all resolved)

| Round-1 Finding | Status | Evidence |
|-----------------|--------|----------|
| `[HIGH] [TEST]` Wiring test never called `load_genre_pack` | ✓ Resolved | `test_load_pack_with_legacy_lora_block` calls `load_genre_pack(elemental_harmony)`; rule-checker confirmed end-to-end loader exercise. |
| `[MEDIUM] [TEST] [RULE]` Bare truthy assertions | ✓ Resolved | rule-checker confirmed: `"Doré" in visual_style.positive_suffix`, `preferred_model == "dev"`. |
| `[LOW] [RULE]` Parametrized duplicate | ✓ Resolved | rule-checker confirmed: parametrize removed; per-field tests retained with named messages. |
| `[LOW] [DOC]` Misleading dict-key fallback comment | ✓ Resolved | comment-analyzer confirmed: comment removed, typed access only. |
| `[LOW] [TEST]` `__pydantic_extra__` not asserted | ✓ Resolved | rule-checker confirmed pattern is appropriate; both files now pin the contract (synthetic + real-pack). |

### Confirmed round-2 findings (all LOW severity)

- `[DOC] [LOW]` Module docstring of `test_visual_style_lora_removal_wiring.py` describes 3 test concerns but the file contains 4 test classes — `TestVisualStyleSchemaSurface` (declared-field-set lockdown) is unmentioned (comment-analyzer §1, MEDIUM confidence).
- `[DOC] [LOW]` `test_load_pack_with_legacy_lora_block` docstring claims "wiring proof for AC3/AC4" but AC3 is already attributed to `test_no_lora_attribute_access_in_production_code` (line 46: "wiring proof for AC3"). The legacy-pack test is naturally the proof for AC4 (loader tolerance) only (comment-analyzer §2, HIGH confidence on the inaccuracy, but LOW severity since it's docstring text in a test file with no behavioral impact).
- `[TEST] [LOW]` `test_extra_allowed` (pre-existing in `TestVisualStyle`, unchanged by this diff) asserts only `vs.positive_suffix == 'grim'` and doesn't pin the `extra_field` round-trip into `__pydantic_extra__` (test-analyzer §2 + rule-checker §1 corroborated). Pre-existing weakness, out of this story's scope; the new `test_extra_lora_keys_in_yaml_still_load` thoroughly covers the contract for LoRA keys.

### Dismissed (with rationale)

- `[TEST] [MEDIUM] → LOW] Wiring grep regex only catches dot-attribute access` (test-analyzer §1) — DOWNGRADED to LOW. The test docstring at lines 49–55 explicitly qualifies the scope: "the regex matches dot-prefixed attribute access only ... will not flag bare-word mentions ... in comments, docstrings, or string literals." Verified manually that production server code is *fully clean* by any grep form right now: `grep -rEn 'lora_(trigger|scale|path)' --include="*.py" sidequest/` returns only 2 docstring/comment matches (`pack.py:97` historical field list, `character.py:135` legacy-compat comment), no code references at all (no dict access, no `getattr`, no string literals). The wiring regex is a forward-looking guard against the most common re-introduction shape (typed attribute access). Widening it to bare-word would falsely flag the legitimate documentation in pack.py and character.py themselves. The honest, narrowly-scoped guard with explicit docstring is the right design.

### Deferred (pre-existing, out of scope)

- `[TEST] [LOW]` `test_extra_allowed` (pre-existing in `TestVisualStyle`) — confirmed but unchanged by this story's diff. Worth a one-line addition in a future hygiene pass; not introduced by this rework.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** legacy YAML on disk (`elemental_harmony/visual_style.yaml` with `loras:` block) → `load_genre_pack` → `_load_yaml(path / "visual_style.yaml", VisualStyle)` (loader.py:507) → `VisualStyle.model_validate(raw)` → typed model surface (5 declared fields, no LoRA fields) + `__pydantic_extra__` carrying the `loras` block as opaque preserved data. `test_load_pack_with_legacy_lora_block` exercises this entire chain end-to-end against a real pack and asserts both the typed surface and the extras preservation. The round-1 wiring gap (the test that *claimed* to test loader tolerance but bypassed the loader) is closed.

**Pattern observed:** The deletion-only schema change at `sidequest/genre/models/character.py:128–146` remains surgical (5 lines removed: 3 fields + validator + import). The `extra='allow'` decision is deliberately preserved with an updated comment explaining the legacy-compat window scoped to Story 43-4. The test surface is now honestly named: every test does what its name says.

**Error handling:** N/A — pure deletion. `extra='allow'` ensures `model_validate` never raises on legacy keys; `__pydantic_extra__` preserves them. Both invariants are pinned by tests.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| `[LOW] [DOC]` | Module docstring lists 3 test concerns but file has 4 test classes (TestVisualStyleSchemaSurface unmentioned). | `tests/genre/test_visual_style_lora_removal_wiring.py:1–14` | Optional cleanup; not blocking. Add a fourth bullet describing the schema-surface lockdown class. |
| `[LOW] [DOC]` | `test_load_pack_with_legacy_lora_block` docstring says "wiring proof for AC3/AC4" but AC3 belongs to the attribute-access grep test. The legacy-pack test proves AC4 (loader tolerance), not AC3. | `tests/genre/test_visual_style_lora_removal_wiring.py:101–110` | Optional cleanup; not blocking. Change "AC3/AC4" → "AC4" in the docstring. |
| `[LOW] [TEST] [RULE]` | Pre-existing `test_extra_allowed` doesn't assert `__pydantic_extra__` round-trip — pre-existing weakness in the unchanged TestVisualStyle class. Flagged by both test-analyzer and rule-checker (Python lang-review #6, "tests with no assertions on the contract they claim to verify"). | `tests/genre/test_models/test_character.py:50–59` | Out of scope for 43-1; future hygiene. |

None of these block APPROVAL. All three are documentation-accuracy or pre-existing test-quality items. Round-2 fix verification confirmed every round-1 finding is resolved cleanly with no regression introduced.

### Rule Compliance

Rule-checker enumerated 18 rules across 47 instances (round-2 re-run). **Zero new violations**; the single pre-existing `test_extra_allowed` weakness is unchanged by this diff and out of scope. Both round-1 rule #6 violations (truthy assertions, parametrized duplicate) are confirmed resolved with named per-field tests and substring/equality checks. The `__pydantic_extra__` access pattern (`extras = vs.__pydantic_extra__ or {}`) is canonical Pydantic v2 with documented stability under `pydantic>=2.6` (project pin). All 5 CLAUDE.md additional rules ("No Silent Fallbacks", "No Stubbing", "Don't Reinvent", "Verify Wiring Not Just Existence", "Every Test Suite Needs a Wiring Test") pass — the wiring test now genuinely satisfies the latter by loading a *real* pack with *live* legacy LoRA keys, not a synthetic tmp-path mock.

### Devil's Advocate

Round 1 caught the substantive failure mode: a test surface that performed the appearance of rigor without the rigor. Round 2 closed that gap. So what's left to argue? Three lines of attack. **First:** the wiring grep regex still only catches dot-attribute access; a future re-introduction via `getattr(obj, "lora_scale")` or `data["lora_scale"]` would slip past silently. Counter: the regex's scope is now explicitly documented, production code is verified clean by any grep form today (manual check), and widening the regex would falsely flag the legitimate documentation in `pack.py:97` and the `model_config` comment in `character.py:135` — both of which are descriptive of the very removal this story performs. The narrow guard with honest scope is correct. **Second:** the docstring still claims "AC3/AC4" for a test that proves only AC4 — a future contributor reading the AC mapping could be confused. Counter: the inaccuracy is local to one docstring line, has zero behavioral or test-correctness impact, and is named in the findings table for downstream cleanup. **Third:** the test-quality regress on `test_extra_allowed` (pre-existing) means the *generic* `extra='allow'` contract isn't pinned in a class that nominally tests it; only the LoRA-specific keys are pinned by the new tests. Counter: this is unchanged code, pre-existing on develop, and out of 43-1's deletion-only scope. The LoRA-specific contract — which is what this story actually concerns — is fully pinned in two distinct test paths (synthetic dict + real pack). The story did its job; the broader test-class hygiene is for another day. None of these objections rise to a blocking concern. The diff ships.

**Handoff:** To The Man in Black (Architect) for spec-reconcile.

## Dev Assessment

**Phase:** finish
**Status:** GREEN — all 19 VisualStyle tests pass; full server suite passes except for 3 pre-existing failures unrelated to this story.

**Implementation:**
- `sidequest-server/sidequest/genre/models/character.py`:
  - Dropped `lora`, `lora_trigger`, `lora_scale` field declarations from `VisualStyle`.
  - Removed the `_validate_lora_scale` `@field_validator` and its accompanying `import math` block.
  - Removed the now-unused `field_validator` import from pydantic.
  - Updated the `model_config` comment to explain why `extra='allow'` is preserved (legacy YAML compatibility — Story 43-4 owns the YAML scrub).
- `sidequest-server/tests/genre/test_models/test_character.py`:
  - Deleted `test_lora_scale_validation`, `test_lora_scale_rejects_above_2`, `test_lora_scale_rejects_negative` (the three pre-existing tests that pinned the removed validator behaviour, called out by TEA).

**Content scope:** No singular-form `lora:` / `lora_trigger:` / `lora_scale:` / `lora_path:` keys exist anywhere under `sidequest-content/genre_packs/` (verified with `grep -rEn "^[[:space:]]*lora(_trigger|_scale|_path)?:"`). AC2 is therefore vacuously satisfied for this story's narrow scope. The plural-form `loras:` and `lora_triggers:` lists in `elemental_harmony`, `the_real_mccoy`, and `dust_and_lead` are explicitly owned by Story 43-4 and out of 43-1's scope.

**Test verification:**
- `uv run pytest tests/genre/test_models/test_character.py tests/genre/test_visual_style_lora_removal_wiring.py -v` → 19 passed, 0 failed.
- `uv run pytest` (full server suite) → 2627 passed, 32 skipped, 3 pre-existing failures (`test_legacy_beat_selection_path_still_works`, `test_confrontation_message_active_false_when_resolved`, `test_confrontation_message_refreshed_on_live_to_live`). Verified pre-existing on develop via `git stash`/replay — unrelated to LoRA removal.

**Lint:**
- `uv run ruff check .` → 167 errors on this branch vs 169 on develop. Net −2 (the deleted lora_scale tests carried B017 violations). One remaining B017 in `test_extra_forbidden` is pre-existing and out of scope.

**Branches:**
- `sidequest-server`: `feat/43-1-remove-lora-fields-visualstyle` (2 commits: RED tests + GREEN implementation).
- `sidequest-content`: `feat/43-1-remove-lora-fields-visualstyle` (no changes — AC2 scope vacuous; will push empty-diff branch only if required by sprint tooling, otherwise discard).
- `orchestrator (.)`: `feat/43-1-remove-lora-fields-visualstyle` (session-file changes only).

**Handoff:** To Architect for spec-check.

## Architect Assessment (spec-check)

**Spec Alignment:** Drift detected (3 minor mismatches, all already flagged by Dev/TEA — none block review)
**Mismatches Found:** 3

- **AC1 lists `lora_path`, but it was never declared on `VisualStyle`** (Ambiguous spec — Cosmetic, Trivial)
  - Spec: "lora, lora_trigger, lora_scale, and `lora_path` fields are removed from the VisualStyle Pydantic model."
  - Code: Three of the four fields removed (lora, lora_trigger, lora_scale). `lora_path` had no declaration to remove; tests guard against re-introduction.
  - Recommendation: **A (update spec)** — AC1 should read "ensure {lora, lora_trigger, lora_scale} are absent and {lora_path} is never re-introduced" so future audits read cleanly. Already flagged by TEA in Improvement finding; no code action.

- **AC2 says "any lora_ field references" but scope was applied to singular-form keys only** (Ambiguous spec — Behavioral, Minor)
  - Spec: "All genre_packs YAML files (visual_style.yaml, pack.yaml) with any lora_ field references are cleaned."
  - Code: No singular `lora:` / `lora_trigger:` / `lora_scale:` / `lora_path:` keys exist anywhere under genre_packs (vacuously satisfied). The plural-form `loras:` and `lora_triggers:` blocks remain in `elemental_harmony/visual_style.yaml`, `the_real_mccoy/visual_style.yaml`, `dust_and_lead/visual_style.yaml`, and `the_real_mccoy/portrait_manifest.yaml` (12 lines).
  - Recommendation: **C (clarify spec)** — confirm the explicit boundary: 43-1 owns singular fields on `VisualStyle`, 43-4 owns the plural-form blocks per its title ("Strip LoRA triggers and explicit_exclude blocks from per-world visual_style.yaml"). Title alignment is already correct; the AC2 wording in 43-1 is the only loose seam. Story 43-4 will close this gap. No code change in 43-1.

- **AC3 says "server or daemon code", wiring test only covers server** (Missing in code — Behavioral, Minor)
  - Spec: "No remaining references to lora_ fields exist in server or daemon code (verified via grep)."
  - Code: `tests/genre/test_visual_style_lora_removal_wiring.py::test_no_lora_attribute_access_in_production_code` walks only `sidequest-server/sidequest/` (server-only). The daemon already explicitly rejects `lora_paths`/`lora_scales`/`lora_path`/`lora_scale` in render params at `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py:309–313` (defensive guard, not a remaining caller).
  - Recommendation: **D (defer)** — Story 43-2 ("Remove LoRA wiring from PromptComposer + daemon Flux1") explicitly owns the daemon-side cleanup. The defensive rejection block in `zimage_mlx_worker.py` will be removed by 43-2 when the broader Flux1 wiring drops. 43-1 leaving the server-side wiring test in place is correct scoping.

**Substantive code review:**
- VisualStyle field removal is clean — `_validate_lora_scale` validator removed, the unused `field_validator` import dropped (good hygiene catch by Dev), and the model_config comment updated to explain why `extra='allow'` is preserved (legacy YAML compatibility for 43-4's later scrub).
- TEA's full-set lockdown test (`test_visual_style_declared_fields_match_post_removal_set`) is the right architectural choice — it transforms silent re-introduction of any future LoRA-shaped field into an explicit failure. Architect concurs with the deviation logged.
- The 3 pre-existing test failures Dev observed (`test_legacy_beat_selection_path_still_works`, `test_confrontation_message_*`) are content/genre-pack drift on `caverns_and_claudes` combat resolution_mode, fully unrelated. Properly out of scope.

**Decision:** Proceed to verify (TEA simplify + quality-pass). All drift is spec-clarity not code-quality, and Dev/TEA already flagged it in Delivery Findings. No hand-back required.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed — 19 targeted tests pass, full server suite stable, lint unchanged from green.

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`sidequest/genre/models/character.py`, `tests/genre/test_models/test_character.py`, `tests/genre/test_visual_style_lora_removal_wiring.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | clean | 0 — wiring patterns (regex grep, schema-surface lockdown, parametrized guards) are story-specific and not duplicated elsewhere; the parametrized guard mirrors AC1 intentionally. |
| simplify-quality | findings | 4 — all on the new wiring test file: (medium) `Path.parents[3]` traversal for REPO_ROOT is fragile across deployment contexts; (medium) `_iter_server_python_files()` lacks a docstring explaining `__pycache__` filter; (low) `_LORA_ATTR_PATTERN` is module-level but used once; (low) `test_no_lora_attribute_access_in_production_code` method name duplicates class-name scope. |
| simplify-efficiency | clean | 0 — refactor is proportionate to risk; no over-engineering, no premature abstraction. |

**Applied:** 0 high-confidence fixes (none reported as high).
**Flagged for Review:** 2 medium-confidence findings (REPO_ROOT pattern, missing docstring) — left unchanged. Reasoning: the `parents[3]` pattern is the established convention in this repo (`tests/integration/test_group_c_wiring.py:38–39`, `tests/server/test_session_handler_decomposer.py:448`, `tests/server/test_multiplayer_party_status.py:36–37` all use the same pattern). Diverging from the convention in a single new file would be inconsistency, not improvement. The docstring gap is genuine but low-risk for a clearly-named private helper. Both flagged for Reviewer's eye, not silent rewrite.
**Noted:** 2 low-confidence findings (module-level regex, method-name length) — both stylistic, both acknowledged. The regex is module-level so the `_iter_server_python_files()` helper stays a pure traversal utility; inlining would couple it to one caller. The method name is intentionally explicit because failure messages from grep-style assertions benefit from named scope ("test_no_lora_attribute_access_in_production_code FAILED" reads cleanly in CI logs).
**Reverted:** 0.

**Overall:** simplify: clean (no auto-applied changes; 4 findings flagged for Reviewer judgment, none blocking).

### Quality Checks

- `uv run pytest tests/genre/test_models/test_character.py tests/genre/test_visual_style_lora_removal_wiring.py` → 19 passed.
- `uv run ruff check {3 changed files}` → 1 error, pre-existing on develop (`test_extra_forbidden` at `test_character.py:45` — `B017 blind Exception`). Out of scope; was 2 errors on develop before this story removed `test_lora_scale_rejects_negative` (which carried the same B017 violation). Net branch lint: 167 vs 169 on develop.
- Targeted suite was stable across two runs (RED→GREEN and now verify), no flake observed.

**Handoff:** To Reviewer for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (1 pre-existing B017 noted) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 (1 high, 1 medium, 1 low) | confirmed 2, dismissed 0, deferred 1 |
| 5 | reviewer-comment-analyzer | Yes | findings | 4 (2 high, 1 medium, 1 low) | confirmed 1, dismissed 2, deferred 1 |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (2 high, 0 medium, 1 pre-existing) | confirmed 2, dismissed 0, deferred 1 |

**All received:** Yes (4 active subagents returned, 5 skipped per `workflow.reviewer_subagents` settings)
**Total findings:** 5 confirmed, 2 dismissed (with rationale), 3 deferred (pre-existing or out-of-scope)

### Confirmed findings
- `[TEST] [HIGH]` Wiring test claim mismatches implementation (test-analyzer §1)
- `[TEST] [RULE] [MEDIUM]` Bare truthy assertions at `wiring:87,90` violate Python lang-review #6 (test-analyzer §2 + rule-checker §1, corroborated)
- `[RULE] [LOW]` Parametrized `test_visual_style_field_removed_parametrized` duplicates per-field tests; violates Python lang-review #6 ("parametrized tests where all cases test the same code path") (rule-checker §2)
- `[DOC] [LOW]` Comment at `wiring:78–80` claims a dict-key fallback the test doesn't perform (comment-analyzer §1)
- `[TEST] [LOW]` `__pydantic_extra__` preservation contract not asserted (test-analyzer §3)

### Dismissed findings (with rationale)
- `[DOC]` "loras: in character.py:135 comment is unverified" (comment-analyzer §2) — DISMISSED. `grep -rn '^loras:' sidequest-content/genre_packs/` returns three live matches (`elemental_harmony/visual_style.yaml:51`, `the_real_mccoy/visual_style.yaml:51`, `dust_and_lead/visual_style.yaml:29`). The comment is accurate.
- `[DOC]` "Comment at wiring:54–59 misdescribes regex scope" (comment-analyzer §3) — DISMISSED. Re-reading the comment: "string-literal mentions of `lora_` in docstrings should be scrubbed too if they describe a removed field" reads as a *prescriptive* aspiration (i.e., "ideally, even docstring mentions would be scrubbed — but we keep the test simple"), not a *descriptive* claim about what the regex catches. Awkward, but not lying about test behavior.

### Deferred / pre-existing
- `[DOC]` `pack.py:97` docstring lists `lora_triggers` (comment-analyzer §4) — out of diff; already in Delivery Findings as 43-4 follow-up.
- `[TYPE]` `BackstoryTables.model_validate` `# type: ignore[override]` lacks why-comment (rule-checker §3) — pre-existing on develop, unmodified by this diff.

## Reviewer Assessment

**Verdict:** REJECTED

**Data flow traced:** legacy YAML → `_load_yaml(visual_style.yaml, VisualStyle)` (loader.py:507) → `VisualStyle.model_validate(raw)` → typed model with `extra='allow'` capturing legacy keys in `__pydantic_extra__`. The diff makes the schema change cleanly. The *tests* claim to exercise this path but a key wiring test bypasses the loader entirely.

**Pattern observed:** The schema removal at `sidequest/genre/models/character.py:128–146` is correct, surgical, and well-commented. The validator/import cleanup is hygienic. The new `TestVisualStyleSchemaSurface.test_visual_style_declared_fields_match_post_removal_set` lockdown is the right architectural choice (see Architect Assessment).

**Error handling:** N/A — pure schema removal. `extra='allow'` is preserved so `model_validate` never raises on legacy keys; the test `test_extra_lora_keys_in_yaml_still_load` proves this. Verified at `tests/genre/test_models/test_character.py:105–124`.

### Findings table

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| `[HIGH] [TEST]` | `test_visual_style_tolerates_legacy_lora_yaml` writes a tmp YAML, reads it with `yaml.safe_load`, and calls `VisualStyle.model_validate` directly. It never invokes `load_genre_pack`. Module docstring at lines 12–13 ("The loader must tolerate legacy YAMLs") and the test class name `TestVisualStyleLoaderStillWorks` both claim *loader-level* wiring that the test does not actually exercise. The diff thus has no test that proves end-to-end loader tolerance for a pack with live LoRA keys, even though such packs exist on disk (`elemental_harmony/visual_style.yaml`, `the_real_mccoy/visual_style.yaml`, `dust_and_lead/visual_style.yaml`). | `tests/genre/test_visual_style_lora_removal_wiring.py:94–125` | Replace or supplement with a call to `load_genre_pack(CONTENT_GENRE_PACKS / "elemental_harmony")` and assert `pack.visual_style` is a `VisualStyle`. That exercises `loader._load_yaml → VisualStyle.model_validate` against a real pack carrying `loras:` keys. The current direct-`model_validate` path is already covered by `test_extra_lora_keys_in_yaml_still_load` in `test_character.py` and is therefore redundant in its current form. |
| `[MEDIUM] [TEST] [RULE]` | Bare truthy assertions on `vs.positive_suffix` and `vs.preferred_model`. Project Python lang-review rule #6 explicitly forbids `assert result` without checking specific values: "truthy check misses wrong values." Two subagents (test-analyzer + rule-checker) flagged this independently. | `tests/genre/test_visual_style_lora_removal_wiring.py:87,90` | Assert specific values. Heavy_metal's `positive_suffix` opens with "baroque ink and wash illustration in the tradition of Gustave Doré" (verified) and `preferred_model` is `dev`. Use `assert "Doré" in visual_style.positive_suffix` and `assert visual_style.preferred_model == "dev"`. |
| `[LOW] [RULE]` | `test_visual_style_field_removed_parametrized` parametrizes over `[lora, lora_trigger, lora_scale, lora_path]` but every case runs the identical dict-membership check that is already individually covered by `test_lora_field_not_declared`, `test_lora_trigger_field_not_declared`, `test_lora_scale_field_not_declared`, `test_lora_path_field_not_declared` in `test_character.py:71–91`. Project Python lang-review rule #6: "Parametrized tests where all cases test the same code path." | `tests/genre/test_visual_style_lora_removal_wiring.py:149–159` | Delete the parametrized function. The per-field tests in `test_character.py` already give named per-field failure messages, and `test_visual_style_declared_fields_match_post_removal_set` provides the full-set lockdown. The parametrized test adds zero unique coverage. |
| `[LOW] [DOC]` | Comment at `tests/genre/test_visual_style_lora_removal_wiring.py:78–80` claims the test "tolerates either `pack.visual_style` (typed) or accessing it via a dict key on the parsed pack." The implementation only does `getattr(pack, "visual_style", None)` — there is no dict-key fallback path. Misleading future readers. | `tests/genre/test_visual_style_lora_removal_wiring.py:78–80` | Replace with: "The loader exposes the visual style as `pack.visual_style` on the GenrePack model — typed attribute access only." Or, if dict-key access is intended, add the elif branch that actually attempts it. |
| `[LOW] [TEST]` | `test_extra_lora_keys_in_yaml_still_load` and `test_visual_style_tolerates_legacy_lora_yaml` assert that `lora`/`lora_trigger`/`lora_scale` are absent from `model_fields` but never assert that the values land in `__pydantic_extra__`. If a future commit changed `extra='allow'` to `extra='ignore'`, the legacy data would be silently discarded and these tests would still pass. | `tests/genre/test_models/test_character.py:105–124` and `tests/genre/test_visual_style_lora_removal_wiring.py:94–125` | Add one assertion in either backwards-compat test: `assert vs.__pydantic_extra__.get("lora") == "legacy.safetensors"`. This pins the extra-field contract. |

### Rule Compliance

Rule-checker enumerated 18 rules across 47 instances; 2 confirmed violations (both rule #6, both already in the findings table). Production code (`character.py`) is clean across all 13 Python lang-review checks plus 5 CLAUDE.md additional rules ("No Silent Fallbacks", "No Stubbing", "Don't Reinvent", "Verify Wiring Not Just Existence", "Every Test Suite Needs a Wiring Test"). The wiring-test rule is *partially* satisfied — `TestNoLoraAttributeAccessInServer` and `test_load_clean_pack_yields_visual_style` do exercise real production paths — but the legacy-YAML wiring claim is unfulfilled, which is what triggers `[HIGH] [TEST]` above.

### Devil's Advocate

This diff is too quiet. The schema-removal half is fine — three fields and a validator vanish, the import gets pruned, the comment gets fattened with a Story 43-4 reference. Surgical, reversible, low-risk. But the test surface looks impressive (14 new tests, 4 classes, regex grep, parametrized guards, schema lockdown, `tmp_path` fixture, real-pack loader call) without actually doing the load-bearing work it claims to. A motivated maintainer reading the test names — `TestVisualStyleLoaderStillWorks`, `test_visual_style_tolerates_legacy_lora_yaml`, `TestNoLoraAttributeAccessInServer` — would conclude: "all loader paths and all production access patterns are covered." But two of those claims are softer than the names imply. The legacy-YAML test never calls the loader. The single loader-touching test (`test_load_clean_pack_yields_visual_style`) loads `heavy_metal` — a pack that has *no* LoRA keys to tolerate. So the diff has zero live tests proving that `load_genre_pack(elemental_harmony)` (which has `loras:` blocks) still produces a `VisualStyle` after the schema change. A regression in `_load_yaml` or in pydantic's `extra='allow'` handling — say, a future story tightening the schema — could ship without breaking a single test. The truthy assertions in `test_load_clean_pack_yields_visual_style` compound this: even if the loader started returning a `VisualStyle` with garbage strings, the test would pass. The parametrized redundancy isn't dangerous; it's just noise that hides the missing coverage by inflating test count. The comment about a dict-key fallback that doesn't exist is a tell — it suggests the test was sketched before the access pattern was verified, and the comment outlived the original intent. Fix the substantive gap (test against `elemental_harmony`), tighten the truthy assertions, prune the parametrized duplicate, and the test surface earns the names it claims. Without these fixes, the wiring test file performs the *appearance* of rigor more than the rigor itself — exactly the kind of false safety the project's "Verify Wiring, Not Just Existence" rule warns against.

**Handoff:** Back to Fezzik (TEA) for RED-phase rework. The findings are all in test files; no production code change is required (and `character.py` is approved as-is). TEA should add a real `load_genre_pack(elemental_harmony)` call, replace truthy assertions with specific-value checks, delete the redundant parametrized function, fix the misleading dict-key comment, and add the `__pydantic_extra__` preservation assertion.

## Delivery Findings

No upstream findings at setup.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): Three pre-existing tests in `tests/genre/test_models/test_character.py` (`test_lora_scale_validation`, `test_lora_scale_rejects_above_2`, `test_lora_scale_rejects_negative`) pin the very behaviour AC1 removes. Affects `sidequest-server/tests/genre/test_models/test_character.py` (delete those three tests as part of the GREEN commit). *Found by TEA during test design.*
- **Gap** (non-blocking): The pack.py docstring at `sidequest-server/sidequest/genre/models/pack.py:97` lists `lora_triggers` as one of the silently-dropped fields on `PortraitManifestEntry`. The wiring grep specifically excludes docstrings (it greps for `.lora*` attribute access), so it stays passing — but a follow-up scrub is appropriate when 43-2/43-3 land. Affects `sidequest-server/sidequest/genre/models/pack.py` (docstring tidy, not blocking 43-1). *Found by TEA during test design.*
- **Improvement** (non-blocking): `lora_path` was never actually declared on `VisualStyle`; the story scope lists it for completeness. Tests guard against re-introduction rather than removal. Affects no current file. *Found by TEA during test design.*

### Dev (implementation)
- **Conflict** (non-blocking): 3 pre-existing test failures on `develop` are unrelated to LoRA removal: `tests/server/dispatch/test_sealed_letter_dispatch_integration.py::test_legacy_beat_selection_path_still_works` and 2 in `tests/server/test_confrontation_dispatch_wiring.py`. Root cause is a `combat` confrontation's `resolution_mode` reading `opposed_check` instead of expected `beat_selection` — content/genre-pack drift, not server code. Affects `sidequest-content/genre_packs/caverns_and_claudes/rules.yaml` (or wherever combat resolution_mode is declared). *Found by Dev during green phase.*
- **Improvement** (non-blocking): `sidequest-server/sidequest/genre/models/pack.py:97` docstring still references `lora_triggers` as a silently-dropped extra. The list is descriptive (other Flux flavor fields), not load-bearing — readable as historical note. Worth scrubbing alongside the YAML cleanup in Story 43-4 if a docstring pass happens then. *Found by Dev during green phase.*
- **Question** (non-blocking): AC2 ("All genre_packs YAML files with any lora_ field references are cleaned") was vacuous for 43-1's narrow scope (singular-form fields). The richer plural-form structures (`loras:`, `lora_triggers:`) are explicitly owned by Story 43-4. If the AC was meant to cover both forms, 43-1's acceptance criteria should be re-scoped or 43-4 should be re-pointed to confirm. *Found by Dev during green phase.*

### TEA (test verification)
- **Improvement** (non-blocking): The `Path(__file__).resolve().parents[3]` repo-root pattern is repeated across 4+ test files (`test_visual_style_lora_removal_wiring.py:27`, `test_group_c_wiring.py:38–39`, `test_session_handler_decomposer.py:448`, `test_multiplayer_party_status.py:36–37`). A future cleanup story could centralize this into a `tests/_repo_paths.py` module — out of scope here, would just create churn in 43-1. Affects multiple test files. *Found by TEA during test verification.*
- **Improvement** (non-blocking): Pre-existing `B017 blind Exception` lint violation at `tests/genre/test_models/test_character.py:45` (`test_extra_forbidden`). 43-1 actually reduced overall lint count by 2 (deleted lora_scale tests carried the same violation) but didn't address the original. Worth a one-line `pytest.raises(ValidationError)` substitution in a future hygiene pass. *Found by TEA during test verification.*

### Reviewer (code review)
- **Gap** (blocking — handed back to TEA via REJECT): The wiring test's loader-tolerance claim (test name + module docstring) is not delivered by the implementation. No test in this diff calls `load_genre_pack` against a pack containing live LoRA keys (`elemental_harmony`, `the_real_mccoy`, `dust_and_lead`). Affects `tests/genre/test_visual_style_lora_removal_wiring.py:94–125` (replace direct `model_validate` with a real `load_genre_pack` call against `elemental_harmony`). *Found by Reviewer during code review.*
- **Conflict** (non-blocking): Two project Python lang-review rule #6 violations found by rule-checker (bare truthy assertions at `wiring:87,90` + parametrized duplicate at `wiring:149–159`). Affects `tests/genre/test_visual_style_lora_removal_wiring.py` (assertions need specific values; parametrized function should be deleted in favor of the per-field tests in `test_character.py`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Backwards-compat tests don't pin the `__pydantic_extra__` preservation contract. Affects `tests/genre/test_models/test_character.py:105–124` and `tests/genre/test_visual_style_lora_removal_wiring.py:94–125` (add `assert vs.__pydantic_extra__.get("lora") == "legacy.safetensors"` to one or both). *Found by Reviewer during code review.* — **RESOLVED in red-rework round 2.**

### TEA (test verification — round 2)
- **Improvement** (non-blocking): Two pre-existing code-smells in `sidequest/genre/models/character.py` surfaced during simplify-efficiency: (a) `MechanicalEffects` declares `model_config` twice — line 40 (`{"extra": "forbid"}`) is shadowed by line 68 (`{"extra": "forbid", "populate_by_name": True}`); the line-40 declaration is dead. (b) `BackstoryTables.model_validate` (line 104) carries custom dict-introspection that could move to the loader. Both are pre-existing on `develop` and out of 43-1's deletion-only scope. Worth a one-liner cleanup story under Epic 43. *Found by TEA during round-2 verify.*
- **Improvement** (non-blocking): If future stories (43-2, 43-4, or beyond) repeat the field-removal pattern, the wiring test's `_iter_server_python_files`/`_LORA_ATTR_PATTERN` pair and the per-field "field not in model_fields" assertions are good extraction candidates for `tests/lib/codebase_scanner.py` or an `assert_field_removed(model_class, field_names, validators)` helper. Premature to extract for one story. *Found by TEA during round-2 verify.*

### Reviewer (code review — round 2)
- **Improvement** (non-blocking): Module docstring of `tests/genre/test_visual_style_lora_removal_wiring.py` lists 3 test concerns but the file has 4 test classes — `TestVisualStyleSchemaSurface` is unmentioned. Affects `tests/genre/test_visual_style_lora_removal_wiring.py:1–14` (add a fourth bullet describing the field-set lockdown). *Found by Reviewer during code review round 2.*
- **Improvement** (non-blocking): `test_load_pack_with_legacy_lora_block` docstring claims "wiring proof for AC3/AC4" but AC3 is held by the attribute-access grep test; the legacy-pack test proves AC4 (loader tolerance) only. Affects `tests/genre/test_visual_style_lora_removal_wiring.py:101–110` (change "AC3/AC4" → "AC4"). *Found by Reviewer during code review round 2.*
- **Improvement** (non-blocking): Pre-existing `test_extra_allowed` in `TestVisualStyle` (line 50–59 of `test_character.py`, unchanged by this diff) doesn't pin `__pydantic_extra__` round-trip for its `extra_field`. The new `test_extra_lora_keys_in_yaml_still_load` covers the contract for LoRA keys; the generic case is left to a future hygiene story. Affects `tests/genre/test_models/test_character.py:50–59`. *Found by Reviewer during code review round 2.*

## Design Deviations

No deviations logged at setup.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Locked the full declared-field set instead of only asserting LoRA absence**
  - Spec source: `.session/43-1-session.md`, AC1
  - Spec text: "lora, lora_trigger, lora_scale, and lora_path fields are removed from the VisualStyle Pydantic model"
  - Implementation: Added `test_visual_style_declared_fields_match_post_removal_set` which pins the full `model_fields` set (positive_suffix, negative_prompt, preferred_model, base_seed, visual_tag_overrides) on top of the per-field absence guards.
  - Rationale: A future contributor could replace one LoRA field with another (e.g., `flux_lora`) and the per-field guards alone wouldn't catch it. The full-set lockdown turns silent additions into explicit test failures.
  - Severity: minor
  - Forward impact: Future stories that intentionally add a typed field to VisualStyle will need to update the `expected` set in this test. That's the desired forcing function.
  - **Reviewer audit:** ✓ ACCEPTED — the lockdown approach is sound; it's a strict-superset of AC1 and turns "silent re-introduction" into a forced failure. Architect concurred during spec-check. No change required.

### Reviewer (audit)
- **No additional spec deviations found by Reviewer.** All deviations from spec were logged by TEA (test design) and Dev (implementation). The TEA deviation above is accepted; no Dev deviations were logged.
- **Round 2:** No new deviations. The TEA rework directly addressed the round-1 substantive findings without introducing new spec drift. The three remaining LOW-severity findings are documentation/test-quality polish, not spec deviations.

### Architect (reconcile)

Final deviation manifest for Story 43-1. Reviewing all entries from TEA, Dev, and Reviewer subsections, plus my round-1 and round-2 spec-check observations:

- **TEA's full-set field-surface lockdown** (logged as TEA deviation, accepted by Reviewer round-1, accepted by Reviewer round-2): Confirmed. The `test_visual_style_declared_fields_match_post_removal_set` test pins the full declared `model_fields` set rather than only asserting absence of the four LoRA fields. This exceeds AC1's literal text but serves the spec's intent (preventing silent re-introduction of LoRA-shaped fields). All 6 fields complete. No correction needed.

- **AC1 lists `lora_path` but it was never declared on `VisualStyle`** (newly logged here as the reconciliation step requires every drift be either accepted or flagged):
  - Spec source: `.session/43-1-session.md`, AC1
  - Spec text: "`lora`, `lora_trigger`, `lora_scale`, and `lora_path` fields are removed from the VisualStyle Pydantic model in sidequest-server"
  - Implementation: 3 of the 4 fields (lora, lora_trigger, lora_scale) were removed; `lora_path` was guarded against re-introduction via `test_lora_path_field_not_declared` and the parametrized assertion (now removed) and the full-set lockdown.
  - Rationale: `lora_path` was not on the model at story start. Removing what doesn't exist is vacuously satisfied. The story scope listed all four for completeness; tests guard against future re-introduction.
  - Severity: minor
  - Forward impact: None. Story scope cleanly executed; AC1 spec text could be tightened in a future cleanup ("ensure {lora, lora_trigger, lora_scale} are absent and {lora_path} cannot be re-introduced") but no code action required.

- **AC2 scope was narrowly interpreted as singular-form keys** (newly logged):
  - Spec source: `.session/43-1-session.md`, AC2
  - Spec text: "All genre_packs YAML files (visual_style.yaml, pack.yaml) with any lora_ field references are cleaned"
  - Implementation: No singular `lora:` / `lora_trigger:` / `lora_scale:` / `lora_path:` keys exist anywhere under `sidequest-content/genre_packs/` (Dev verified via grep). The plural-form `loras:` and `lora_triggers:` blocks remain in `elemental_harmony/visual_style.yaml`, `the_real_mccoy/visual_style.yaml`, `dust_and_lead/visual_style.yaml`, and `the_real_mccoy/portrait_manifest.yaml` (12 lines).
  - Rationale: Story 43-4 is explicitly scoped to "Strip LoRA triggers and explicit_exclude blocks from per-world visual_style.yaml" — the plural-form structures are owned there. 43-1's AC1 enumeration uses the singular forms, which scopes AC2 by alignment.
  - Severity: minor
  - Forward impact: Story 43-4 closes the gap. AC2 wording could be tightened (e.g., "any singular-form lora_ field references" to disambiguate from the plural-form block list).

- **AC3 daemon-side coverage owned by Story 43-2** (newly logged):
  - Spec source: `.session/43-1-session.md`, AC3
  - Spec text: "No remaining references to lora_ fields exist in server or daemon code (verified via grep)"
  - Implementation: 43-1's wiring test (`test_no_lora_attribute_access_in_production_code`) walks `sidequest-server/sidequest/` only — server-side coverage. The daemon already explicitly rejects `lora_paths` / `lora_scales` / `lora_path` / `lora_scale` in render params at `sidequest-daemon/sidequest_daemon/media/workers/zimage_mlx_worker.py:309–313` (defensive guard, not a remaining caller).
  - Rationale: Story 43-2 ("Remove LoRA wiring from PromptComposer + daemon Flux1") explicitly owns the daemon-side cleanup. The defensive rejection block in `zimage_mlx_worker.py` will be removed by 43-2 when broader Flux1 wiring drops. 43-1 leaving the server-side wiring test in place is correct scoping.
  - Severity: minor
  - Forward impact: Story 43-2 closes the daemon side completely. 43-1's wiring test could be widened to walk both server and daemon trees as a defense-in-depth; out of scope here.

- **Reviewer's three round-2 LOW findings** (module docstring incompleteness, AC3/AC4 docstring attribution error, pre-existing `test_extra_allowed` weakness): Reviewed. All three are documentation accuracy or pre-existing test-quality matters, not spec deviations. Already captured under Reviewer (code review — round 2) in Delivery Findings. No additional reconcile action.

**Manifest summary:** 1 sound design deviation (TEA's lockdown), 3 spec-clarity drifts (AC1/AC2/AC3 ambiguities resolved by sibling-story scoping), 0 unresolved drifts, 0 unaddressed Reviewer findings of Critical/High severity. Story 43-1 is ready for finish.