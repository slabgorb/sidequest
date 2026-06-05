---
story_id: "88-1"
jira_key: ""
epic: "88"
workflow: "tdd"
---
# Story 88-1: AWN Plan 1 engine — thin awn ruleset module + binding seams + wiring/chargen tests

## Story Details
- **ID:** 88-1
- **Jira Key:** None (personal project — no Jira)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 5

## Context

This is the **foundation story** for the Ashes Without Number port (epic 88). It gates every downstream Plan (Mutations, Radiation, Disease, Stress, Survival, Creatures, Enclaves).

**Design source (READ IT):**
- `docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md` (especially §6 Plan 1, §11 Architect Addendum, §11.2 MUST-change list, §11.4 test guidance)

**Key decision:** AWN combat == CWN combat (faithful SRD port). `AwnRulesetModule` subclasses `CwnRulesetModule` and inherits attack/skill/save/initiative/damage verbatim. No method overrides in Plan 1. The subclass exists for an honest slug (`"awn"` not `"cwn"`) and a home for future AWN-only hooks (e.g. radiation save modifiers, mutation crunch).

**Load-bearing finding (§11.1):** The engine binds ruleset behavior two ways:
1. **Capability style** (`isinstance(cfg, CwnConfig)`, `isinstance(module, CwnRulesetModule)`): already works for `awn` — inherits free.
2. **Slug-string style** (`ruleset == "cwn"`, `ruleset != "cwn"`): requires explicit `"awn"` branch or silent fall-through.

Plan 1 **must** touch the six slug-string sites (#4–7 below) to close the gap. The capability sites are free (no edit needed).

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T10:27:08Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05 | 2026-06-05T09:46:12Z | 9h 46m |
| red | 2026-06-05T09:46:12Z | 2026-06-05T09:57:54Z | 11m 42s |
| green | 2026-06-05T09:57:54Z | 2026-06-05T10:06:24Z | 8m 30s |
| review | 2026-06-05T10:06:24Z | 2026-06-05T10:27:08Z | 20m 44s |
| finish | 2026-06-05T10:27:08Z | - | - |

## Delivery Findings

No upstream findings yet. Agents append findings during their phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Item 5 (downed seam) is exercised through `run_cwn_wwn_downed_seam`, not `_physical_save_target_for`.** The slug-string guard the spec flags at `downed_seam.py:128` lives in `run_cwn_wwn_downed_seam` (`if not (pack and pack.rules and pack.rules.ruleset in ("cwn","wwn")): return`). `dispatch_dice_throw` calls it at `dice.py:713`. `_physical_save_target_for` (`downed_seam.py:71`) is the FREE isinstance site (Item 8) and is unit-tested separately. Dev must fix the `run_cwn_wwn_downed_seam` slug guard for the `cwn.mortal_injury.declared` integration assertion to pass. Affects `sidequest/server/dispatch/downed_seam.py` (line ~128 guard). *Found by TEA during test design.*
- **Improvement** (non-blocking): The `span name` for AWN Mortal Injury/Trauma/Shock stays `cwn.*` (not `awn.*`), because `AwnRulesetModule` inherits the CWN span emitters verbatim (no override in Plan 1). Tests assert `cwn.trauma.roll` / `cwn.shock.applied` / `cwn.mortal_injury.declared` accordingly — this matches §11.4. If a future plan re-prefixes spans to `awn.*`, these assertions must move with them. Affects `sidequest/game/ruleset/cwn.py` span emitters (inherited). *Found by TEA during test design.*
- **Question** (non-blocking): The two tool guards (Items 6, 7) currently read `pack.rules.ruleset != "cwn"` and then resolve `module = get_ruleset_module(pack.rules.ruleset)`. The spec recommends Option B (isinstance on the resolved module). The AWN tool tests assert *behavior* (awn pack → strain applies / stabilize succeeds), not the guard shape, so either Option A (`or ruleset == "awn"`) or Option B passes them — Dev's choice, but Option B is the spec-preferred capability form. Affects `sidequest/agents/tools/{adjust_system_strain,stabilize_mortal_injury}.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): A pre-existing test failure is present on the branch base, unrelated to 88-1: `tests/agents/tools/test_apply_world_patch.py::test_active_stakes_path_applies` (tool rejects `/active_stakes` as an unsupported path — returns `ERROR_RECOVERABLE`, test expects `OK`). Verified pre-existing by stashing all 88-1 source changes and re-running — it still fails. Not caused by and not in scope for this story. Affects `sidequest/agents/tools/apply_world_patch.py` (supported-paths list vs. the `/active_stakes` path) — track as separate content-drift/world-patch work. *Found by Dev during implementation.*
- Chose Option B (capability `isinstance(module, CwnRulesetModule)`) for both tool guards per the spec's stated preference — the resolved module is reused (the previously-redundant `assert isinstance(...)` in `adjust_system_strain` was removed since the guard now guarantees it). No upstream impact. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (blocking): Three module-level docstrings now misdocument the contract this PR changed. `adjust_system_strain.py:16` and `stabilize_mortal_injury.py:23` still say `ruleset != "cwn"` → "tool is CWN-only" (the tools now accept AWN); `downed_seam.py:15` module summary still says the seam is gated on "ruleset is `cwn`/`wwn`" (the function docstring was updated, the module summary was not). Affects those three files (correct the Guards/summary text to describe the capability gate). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Two test fixture docstrings (`test_adjust_system_strain_tool.py:325`, `test_stabilize_mortal_injury_tool.py:404`) describe the pre-fix guard in the present tense ("The current guard blocks it") although the fix has landed in this same diff. Affects those two test files (reword to past tense / describe the capability gate). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Test-rigor enhancements that would harden the wiring proofs — (a) `test_awn_shock_chips_hp_on_miss` should also assert `state_patch.hp` fired (ADR-114 lie-detector); (b) `test_awn_opponent_reprisal_fires` proves the reprisal *engaged* (span) but not that it dealt damage — monkeypatch the opponent d20 to a guaranteed hit and assert player HP dropped; (c) `_validate_awn`'s empty-`attribute_map` branch (the distinct "none authored" message) is untested. Affects `tests/server/test_awn_combat_dispatch.py`, `tests/game/ruleset/test_awn_config.py`. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `downed_seam.py:129` adds a function-local `from ...rules import CwnConfig, WwnConfig`; `rules` is already imported at module top (line 30, `ConfrontationDef`), so it could be hoisted — but it mirrors the existing `physical_save_target_for:69` pattern in the same file, so this is consistency, not a defect. Affects `sidequest/server/dispatch/downed_seam.py` (optional tidy). *Found by Reviewer during code review.*

## Design Deviations

No deviations from spec yet. Agents log spec deviations as they happen.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Integration test (§11.4 Test 4) uses `dispatch_dice_throw` directly, not the full intent-router/narrator path.**
  - Spec source: context-story-88-1.md, "Mandatory Wiring Tests" §4 / session "Test 4"
  - Spec text: "Run one player action through production dispatch (`execute_intent_router_pre_narrator_pass` or the top-level handler) … Include the actual narrator (Haiku via SDK, or mock with SIDEQUEST_LLM_BACKEND=mock)"
  - Implementation: `tests/server/test_awn_combat_dispatch.py` drives the production `dispatch_dice_throw` (the same mechanical dispatch path the narrator's dice tool invokes) with a synthetic `ruleset="awn"` MagicMock pack and monkeypatched RNG. No LLM is invoked.
  - Rationale: This mirrors the established, proven CWN combat wiring proof (`test_neon_combat_lethality_dispatch.py`) and the ADR-114 e2e (`test_space_opera_hp_e2e.py`), both of which assert the same `cwn.*`/`state_patch.hp` spans against `dispatch_dice_throw`. It is fully deterministic (no LLM nondeterminism), needs no content pack (the awn pack lands in 88-2), and still proves every load-bearing seam: registry resolution in production, `ruleset_config()` dispatch, inherited combat spans, ablative HP depletion, the Item-5 downed seam, and opponent reprisal. Routing through the narrator would add nondeterminism and an LLM dependency without exercising any additional AWN-specific wiring.
  - Severity: minor
  - Forward impact: When the `mutant_wasteland` awn pack lands (88-2), a real-pack smoke test can be added on top of this; the dispatch-level proof remains the deterministic regression guard.
- **`cwn.major_injury.roll` is not asserted in the AWN integration suite (only `cwn.mortal_injury.declared`).**
  - Spec source: context-story-88-1.md §11.4 Test 4 assertions
  - Spec text: lists `cwn.shock.applied`, `cwn.trauma.roll`, `cwn.mortal_injury.declared` as the inherited spans to assert
  - Implementation: The integration suite asserts trauma, shock, and mortal-injury spans + HP depletion + reprisal. The Major-Injury (traumatic-0-HP) path is proven inherited-from-CWN by `test_neon_combat_lethality_dispatch.py::test_downed_after_traumatic_hit_rolls_major`; AWN inherits `resolve_downed` verbatim (no override), so re-driving the dual-deterministic (trauma-high + save-low) path for AWN would duplicate the CWN proof without testing new wiring.
  - Rationale: The spec's listed assertions (shock/trauma/mortal-injury) are all covered. Major-Injury is a sub-branch of the same inherited `resolve_downed` already covered by the mortal-injury assertion (the seam runs); the CWN suite covers the traumatic branch.
  - Severity: minor
  - Forward impact: none — if a future AWN plan overrides `resolve_downed`, add an AWN-specific Major-Injury span test then.

### Dev (implementation)
- No deviations from spec. All seven items were implemented in the exact forms the spec recommended: Item 4 capability `isinstance(cfg, CwnConfig)` via `ruleset_config()`; Item 5 isinstance on `ruleset_config()`; Items 6–7 Option B (isinstance on the resolved module). `AwnConfig`/`_validate_awn`/`ruleset_config()` mirror the CWN equivalents exactly. (Tool-guard ValueError wording changed from "cwn-only" to "requires a CWN-family ruleset (cwn/awn)" — a message-text clarification, not a behavioral or contract change; existing `match="cwn"` assertions still pass.)

### Reviewer (audit)
- **TEA deviation 1 (integration test drives `dispatch_dice_throw`, not the full narrator path)** → ✓ ACCEPTED by Reviewer: sound — it mirrors the proven CWN wiring proof (`test_neon_combat_lethality_dispatch.py`) and the ADR-114 e2e, is deterministic, needs no content pack, and still exercises registry resolution + `ruleset_config()` dispatch + inherited spans + the Item-5 downed seam in production code. Routing through the LLM narrator would add nondeterminism without exercising additional AWN wiring.
- **TEA deviation 2 (`cwn.major_injury.roll` not asserted; only `cwn.mortal_injury.declared`)** → ✓ ACCEPTED by Reviewer: Major Injury is a sub-branch of the same inherited `resolve_downed` (no AWN override), already proven for the traumatic path by `test_neon_combat_lethality_dispatch.py::test_downed_after_traumatic_hit_rolls_major`. The mortal-injury assertion proves the seam runs for AWN; duplicating the dual-deterministic traumatic path adds no AWN-specific coverage.
- **Dev deviation (tool-guard ValueError wording "cwn-only" → "CWN-family (cwn/awn)")** → ✓ ACCEPTED by Reviewer: accurate to the new capability gate; `match="cwn"` assertions still pass. (Note: the *module-level docstrings* were NOT updated to match — that is a separate stale-comment finding in the Reviewer Assessment, not a spec deviation.)
- **No undocumented spec deviations found.** The implementation is faithful to §11.2/§11.4. The findings below are documentation-accuracy and test-rigor issues, not divergences from the spec's design.

---

## Technical Scope — Plan 1 Engine (§11.2 MUST-change items)

### Item 1: New Module `sidequest/game/ruleset/awn.py`
- **File:** New file at `sidequest-server/sidequest/game/ruleset/awn.py`
- **Class:** `AwnRulesetModule(CwnRulesetModule)`
- **Slug:** `slug = "awn"`
- **Docstring:** Explain that it subclasses CWN (combat identical), exists for honest slug, and serves as a home for future AWN-only hooks
- **Methods:** None in Plan 1 (all inherited from CWN)

### Item 2: Register in `sidequest/game/ruleset/registry.py`
- Import `AwnRulesetModule`
- Add to `_REGISTRY`: `AwnRulesetModule.slug: AwnRulesetModule()`
- Verify `get_ruleset_module("unknown")` still fails loud (no default)

### Item 3: Config Model in `sidequest/genre/models/rules.py`
- **Class:** `AwnConfig(CwnConfig)` with empty body
  - Inherits: `system_strain`, `trauma`, `attribute_map` from CWN
  - `hacking` stays `None` (AWN has no net-run)
- **Field in RulesConfig:** `awn: AwnConfig | None = None`
- **Validator:** `_validate_awn` (model_validator, mode="after")
  - Mirror `_validate_cwn` exactly:
    - If `ruleset != "awn"`, return early
    - If `awn is None`, set to `AwnConfig()`
    - Require complete six-key `attribute_map` (STRENGTH, CONSTITUTION, DEXTERITY, INTELLIGENCE, WISDOM, CHARISMA)
    - Validate all keys are in `ability_score_names`
    - Validate `system_strain.max_source` is a key in `attribute_map`
    - Validate `trauma.major_injury_save` is one of {physical, evasion, mental, luck}
- **Update `ruleset_config()` method:** Add `awn` branch:
  ```python
  if self.ruleset == "awn":
      return self.awn
  ```

### Item 4: Fix Chargen Strain-Pool Gap in `sidequest/game/builder.py:82`
- **Current code:** `if rules.ruleset != "cwn" or rules.cwn is None: return None`
- **Problem:** AWN has no strain pool (silent fall-through on the string check)
- **Recommended fix (capability form):**
  ```python
  cfg = rules.ruleset_config()
  if not isinstance(cfg, CwnConfig):   # Covers CWN + AWN + future subclasses
      return None
  con_flavor = cfg.attribute_map["CONSTITUTION"]
  ```
  This auto-covers AWN and immunizes the site against the next sister module.

### Item 5: Align Mortal/Major Injury Gate in `sidequest/server/dispatch/downed_seam.py:128`
- **Current code:** `if not (pack and pack.rules and pack.rules.ruleset in ("cwn", "wwn")):`
- **Goal:** Use isinstance style (already used at line 71 in the same file)
- **Fix:** Change to:
  ```python
  if not (pack and pack.rules and isinstance(pack.rules.ruleset_config(), (CwnConfig, WwnConfig))):
  ```
  This allows AWN to ride free without a new string.

### Item 6: Loosen Guard in `sidequest/agents/tools/stabilize_mortal_injury.py:101`
- **Current code:** `if pack is None or pack.rules is None or pack.rules.ruleset != "cwn":`
- **Problem:** AWN has the stabilize-at-0 rule (SRD p.52) but is blocked by the string check
- **Fix (Option A — string):** Add `or pack.rules.ruleset == "awn"` to the condition
- **Fix (Option B — capability):** Use `isinstance(module, CwnRulesetModule)` (the assert at :99 already passes for AWN)
- **Recommendation:** Prefer Option B for consistency with downed_seam.py refactor

### Item 7: Loosen Guard in `sidequest/agents/tools/adjust_system_strain.py:89`
- **Current code:** `if pack is None or pack.rules is None or pack.rules.ruleset != "cwn":`
- **Problem:** AWN uses System Strain (stims, mutations, first-aid) but is blocked by the string check
- **Fix:** Same as Item 6 — Option B preferred (isinstance check on module)

### Item 8: FREE Sites (verify with tests, DO NOT edit)
These sites already work for AWN via isinstance/override checks:
- `cwn.py` inherited cfg asserts (lines 100, 153, 237)
- `downed_seam.py:71` — already uses `isinstance(cfg, (CwnConfig, WwnConfig))`
- `dice.py:341` — override probe for shock resolution
- `dice.py:776` — opponent reprisal (method-override check)

### Item 9: OUT-OF-SCOPE (DO NOT touch per spec §11.2)
- Hacking gates (`dice.py:328`, `encounter_lifecycle.py:1324`) — AWN correctly has no hacking; AwnConfig.hacking stays None
- WWN-only subsystems (`commit_effort`, `long_rest`, `veterans_luck`, `session.py:95`, `narration_apply.py:4423`, `dice.py:515/596/675`, `loader.py:688/1474`, `builder.py:125`) — no change
- Dogfight (`dogfight_shot.py:324`) — AWN vehicles are a later plan; no change

---

## Mandatory Wiring Tests (§11.4 — the GM panel is the lie detector)

All tests assert **OTEL spans**, not source text per server CLAUDE.md "No Source-Text Wiring Tests". Use fixture-driven behavior tests + span assertions.

### Test 1: Registry Resolution
- **File:** `tests/game/ruleset/test_registry.py`
- **Test:** `test_get_ruleset_module_awn_resolves`
  - Call `get_ruleset_module("awn")` → returns `AwnRulesetModule` instance
  - Slug matches: `assert get_ruleset_module("awn").slug == "awn"`
- **Test:** `test_get_ruleset_module_unknown_fails_loud`
  - Verify unknown slug raises `UnknownRulesetError` (regression guard for the fail-loud contract)

### Test 2: Config Load (exercises `_validate_awn`)
- **File:** `tests/genre/test_rules_loader.py` or new `test_awn_config.py`
- **Test:** `test_awn_config_loads_with_complete_attribute_map`
  - Load a fixture pack with `ruleset: awn` + valid six-key `attribute_map`
  - Assert `rules.awn` is `AwnConfig` instance
  - Assert no validation errors
- **Test:** `test_awn_config_fails_on_incomplete_attribute_map`
  - Load a fixture pack with `ruleset: awn` + missing one key
  - Assert validation error mentions the missing key (fail-loud contract)
- **Test:** `test_awn_config_fails_on_bad_major_injury_save`
  - Load fixture with invalid `major_injury_save`
  - Assert validation error

### Test 3: Chargen Smoke (regression guard for Item 4 gap)
- **File:** `tests/game/test_builder.py` or existing builder test
- **Test:** `test_seed_system_strain_awn_character_gets_pool`
  - Create chargen `RulesConfig` with `ruleset: awn` + valid `awn:` config
  - Seed stats dict with Constitution flavor set to e.g. 14
  - Call `seed_system_strain(rules, stats)`
  - Assert returns non-None `SystemStrainPool` with `max == 14` (the CON score)
  - Assert pool is not silent fallback (was the bug)
- **Test:** `test_seed_system_strain_non_awn_returns_none`
  - Verify other rulesets (native, swn) still return None (no regression)

### Test 4: Integration / Wiring (full production dispatch path)
- **File:** `tests/server/dispatch/test_awn_combat_dispatch.py` (new)
- **Test:** `test_awn_combat_turn_fires_cwn_spans_and_depletes_hp`
  - Load an `awn`-bound pack (fixture with `ruleset: awn`)
  - Seed a game state with two AWN characters in a combat encounter
  - Run one player action through the production dispatch path:
    - Call `execute_intent_router_pre_narrator_pass` or the top-level handler
    - Include the actual narrator (Haiku via SDK, or mock with SIDEQUEST_LLM_BACKEND=mock)
  - **Assertions:**
    - `get_ruleset_module("awn")` resolves (no UnknownRulesetError)
    - Inherited `cwn.*` OTEL spans fire:
      - `cwn.shock.applied` when a hit lands with Shock damage
      - `cwn.trauma.roll` when a trauma die is triggered
      - `cwn.mortal_injury.declared` when an actor's HP hits 0
    - HP depletes on the ablative pool (assert `state_patch_hp` span fired with delta < 0)
    - Opponent reprisal fires (if the opponent is still alive; assert a counter-attack narration in the response)
- **Fixture shape:**
  - Genre pack YAML: minimal `awn` pack with `ruleset: awn`, basic `archetypes.yaml` with one class, `rules.yaml` with six-key `attribute_map`
  - Character: seeded via chargen with `system_strain` pool present (regression guard for Item 4)
  - Encounter: one combat confrontation with `type: hp_depletion`, two actors (player + NPC)

---

## Acceptance Criteria

- [ ] Item 1: `sidequest/game/ruleset/awn.py` created; `AwnRulesetModule(CwnRulesetModule)` with `slug = "awn"`, docstring present
- [ ] Item 2: Registry updated; `get_ruleset_module("awn")` resolves; unknown slug still fails
- [ ] Item 3: `AwnConfig` and `_validate_awn` implemented; `ruleset_config()` updated
- [ ] Item 4: `seed_system_strain` refactored to isinstance form; AWN characters get strain pools
- [ ] Item 5: `downed_seam.py:128` aligned to isinstance form
- [ ] Item 6: `stabilize_mortal_injury.py:101` loosened (string or isinstance form)
- [ ] Item 7: `adjust_system_strain.py:89` loosened (string or isinstance form)
- [ ] Item 8: Verification tests pass for FREE sites (no edit, but confirm via test) — cwn.py asserts, downed_seam.py:71, dice.py:341/776
- [ ] Test 1: Registry tests green (resolves awn, fails loud on unknown)
- [ ] Test 2: Config load tests green (exercises `_validate_awn`, fails on incomplete map)
- [ ] Test 3: Chargen smoke tests green (AWN character gets strain pool with correct max)
- [ ] Test 4: Integration/wiring test green (production dispatch fires `cwn.*` spans, HP depletes, opponent reprisal works)
- [ ] All server tests pass (uv run pytest -v)
- [ ] No new source-text wiring tests (use OTEL spans + fixture behavior tests only)

---

## Branch Strategy

- **Repo:** sidequest-server
- **Base:** develop
- **Branch:** feat/88-1-awn-ruleset-module
- **PR Target:** develop (standard gitflow)

---

## Sm Assessment

**Setup verdict:** Ready for TDD red phase. Foundation story for epic 88 (Ashes Without Number), engine lane only (`sidequest-server`).

**Routing rationale:** `tdd` workflow → first post-setup phase is `red`, owned by TEA (the Caterpillar). The scope is a well-bounded engine wiring task with a clear contract (the §11.2 MUST-change list + §11.4 test guidance), which is exactly what TDD red-first wants: encode the wiring contract as failing tests, then Dev makes them green. The mandatory wiring tests (registry resolve + fail-loud, `_validate_awn` load, chargen strain-pool regression guard, production-dispatch span assertions) are the test contract TEA writes first.

**Context provided:** Full technical scope (items 1–9), partitioned change-list (MUST-change / FREE / OUT-OF-SCOPE), and the design source (`docs/superpowers/specs/2026-06-05-ashes-without-number-mutant-wasteland-design.md` §6, §11). The load-bearing finding — two binding styles, capability vs slug-string — is captured so TEA tests both the free-inheritance paths and the slug-string fixes.

**Dependencies:** Story 88-2 (content lane — `mutant_wasteland` rules.yaml binding + standard-six sweep) is stacked on this story (`depends_on: 88-1`) because the content pack can't load until `_validate_awn` exists. 88-2 stays in backlog until 88-1 merges.

**Jira:** None — personal project under slabgorb (no Jira integration), per server CLAUDE.md.

**Pre-handoff checklist:**
- [x] Session file exists (`.session/88-1-session.md`)
- [x] Story context written with technical approach + ACs (`sprint/context/context-story-88-1.md`)
- [x] Branch created (`feat/88-1-awn-ruleset-module` on develop)
- [x] Jira claimed or explicitly skipped (skipped — personal project)

**Decision:** Hand off to TEA for the red phase.

---
## TEA Assessment

**Tests Required:** Yes
**Reason:** Feature story (5 pts) — new ruleset module, config validator, chargen fix, and six binding-site fixes. Full TDD red-first.

**Test Files:**
- `tests/game/ruleset/test_registry.py` (appended) — Items 1, 2: `get_ruleset_module("awn")` resolves to `AwnRulesetModule`, singleton, CWN subclass; unknown slug still fails loud.
- `tests/game/ruleset/test_awn_config.py` (new) — Item 3: `AwnConfig(CwnConfig)`, `_validate_awn` mirror (complete map / incomplete / flavor-not-declared / strain-source / bad+luck major_injury_save), `ruleset_config()` awn branch, hacking defaults None, no cross-contamination.
- `tests/game/test_builder_seeds_strain.py` (appended) — Item 4: AWN chargen → strain pool (max=CON-flavor), max-1 floor, swn/native still None (regression).
- `tests/game/ruleset/test_awn_downed_dispatch_seam.py` (new) — Item 8 FREE site: `_physical_save_target_for` accepts `AwnConfig` via inherited isinstance, still rejects raw `SwnConfig`.
- `tests/agents/tools/test_adjust_system_strain_tool.py` (appended) — Item 7: awn pack applies System Strain (cwn-only guard must loosen).
- `tests/agents/tools/test_stabilize_mortal_injury_tool.py` (appended) — Item 6: awn pack can stabilize a Mortal Injury.
- `tests/server/test_awn_combat_dispatch.py` (new) — §11.4 Test 4 integration: production `dispatch_dice_throw` with a synthetic `ruleset="awn"` pack fires inherited `cwn.trauma.roll` / `cwn.shock.applied` / `cwn.mortal_injury.declared` spans, depletes ablative HP (`state_patch.hp`), runs the downed seam for awn (Item 5), and fires opponent reprisal (Item 8 FREE).

**Tests Written:** 16 new AWN tests covering all 9 ACs (Items 1–8 + §11.4 Tests 1–4).
**Status:** RED (failing — ready for Dev). Verified via testing-runner (RUN_ID 88-1-tea-red): 16 AWN tests fail cleanly on missing AWN symbols (`AwnConfig`, `AwnRulesetModule`, `sidequest.game.ruleset.awn`, unregistered `"awn"` slug); 21 pre-existing tests in the modified files still pass; zero harness bugs.

### Rule Coverage

Project rule source: server CLAUDE.md (no `.pennyfarthing/gates/lang-review/python.md` present). Rules tested:

| Rule (server CLAUDE.md) | Test(s) | Status |
|------|---------|--------|
| No Silent Fallbacks (fail loud) | `test_unknown_ruleset_still_fails_loud_after_awn`, `test_rules_awn_with_no_config_block_fails_loud`, `test_rules_awn_requires_complete_attribute_map`, `test_rules_awn_strain_source_must_be_in_map`, `test_rules_awn_rejects_bad_major_injury_save` | RED |
| No Source-Text Wiring Tests (OTEL spans + fixtures only) | `test_awn_combat_dispatch.py` (all 4 — span assertions, no source greps) | RED |
| Every Test Suite Needs a Wiring Test | `test_awn_combat_dispatch.py::test_awn_strike_fires_trauma_span_and_depletes_hp` (production dispatch path) | RED |
| Capability binding > slug-string (§11.1) | `test_awn_config_is_a_cwn_config_subclass`, `test_awn_module_is_a_cwn_subclass`, `test_physical_save_target_accepts_awn_config` | RED |
| Regression: broadening gates must not over-cover | `test_swn_still_returns_none`, `test_ruleset_config_awn_is_none_when_ruleset_is_not_awn`, `test_physical_save_target_still_rejects_swn_config` | RED |

**Rules checked:** 5 of 5 applicable server-CLAUDE.md rules have test coverage.
**Self-check:** 0 vacuous tests — every test asserts a concrete value, span name, or raised error. No `assert True`, no `let _ =`, no always-None `is_none()`.

**Handoff:** To Dev (the White Rabbit) for implementation — make the 16 RED tests green by landing Items 1–7 (Item 8 is verify-only, no edit). Heed the three Delivery Findings, especially that Item 5's fix lives in `run_cwn_wwn_downed_seam` (downed_seam.py:128), not the already-free `_physical_save_target_for`.

---
## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest/game/ruleset/awn.py` (new) — Item 1: `AwnRulesetModule(CwnRulesetModule)`, `slug = "awn"`, no method overrides; docstring explains the honest-slug + future-hooks rationale.
- `sidequest/game/ruleset/registry.py` — Item 2: import + register `AwnRulesetModule()` in `_REGISTRY`; `get_ruleset_module` fail-loud path unchanged.
- `sidequest/genre/models/rules.py` — Item 3: `AwnConfig(CwnConfig)` (empty body, hacking stays None), `RulesConfig.awn` field, `_validate_awn` model-validator (mirrors `_validate_cwn`: complete six-key map, flavor-in-ability-scores, strain `max_source` in map, valid `major_injury_save`), `ruleset_config()` awn branch.
- `sidequest/game/builder.py` — Item 4: `seed_system_strain` switched to capability form (`isinstance(rules.ruleset_config(), CwnConfig)`) so AWN gets a strain pool; imports `CwnConfig`.
- `sidequest/server/dispatch/downed_seam.py` — Item 5: `run_cwn_wwn_downed_seam` slug-string guard → `isinstance(pack.rules.ruleset_config(), (CwnConfig, WwnConfig))`; docstring updated to reflect awn coverage.
- `sidequest/agents/tools/adjust_system_strain.py` — Item 7: cwn-only string guard → Option B capability gate (`isinstance(module, CwnRulesetModule)`); removed now-redundant assert.
- `sidequest/agents/tools/stabilize_mortal_injury.py` — Item 6: added ruleset imports; cwn-only string guard → Option B capability gate.

**Item 8 (FREE sites):** No edits — verified covered for AWN by `test_awn_downed_dispatch_seam.py` (`_physical_save_target_for`) and `test_awn_combat_dispatch.py` (cwn.py inherited asserts, dice.py:341 shock probe, dice.py:776 reprisal).

**Tests:** 54/54 passing in the seven affected files (16 new AWN tests GREEN + 38 pre-existing in those files unbroken). Regression sweep (ruleset/genre/builder/tools/neon combat): 1518 passed, 49 skipped, 1 failed — the single failure is `test_apply_world_patch.py::test_active_stakes_path_applies`, verified PRE-EXISTING (still fails with all 88-1 source stashed) and unrelated to this story. Verified GREEN via testing-runner (RUN_ID 88-1-dev-green). `ruff check` + `ruff format --check` clean on all seven changed files.

**Branch:** `feat/88-1-awn-ruleset-module` (pushed to origin).

**Handoff:** To Reviewer (the Queen of Hearts) for code review.

---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (54/54 green, lint+format PASS, 0 smells) | N/A (pre-existing `test_apply_world_patch` failure confirmed out-of-scope) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 7 (3 medium, 4 low) | confirmed 3 (T1/T2/T4 non-blocking), deferred 4 (T3/T5/T6/T7 low) |
| 5 | reviewer-comment-analyzer | Yes | findings | 5 (3 high-conf, 2 medium) | confirmed 5 (C1–C3 blocking docs, C4–C5 non-blocking) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (R1 import, R2 assert) | confirmed 1 (R1 low), dismissed 1 (R2 — sibling-validator convention) |

**All received:** Yes (4 ran, 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 6 confirmed actionable (3 blocking docs + 3 non-blocking test-rigor), 8 deferred/non-blocking, 1 dismissed (with rationale)

---
## Reviewer Assessment

**Verdict:** APPROVED (doc/test findings resolved in-review)

**Why (no Critical/High *code* defect — the implementation is correct and spec-faithful):** My initial pass found **zero logic defects**: the implementation is correct, fail-loud, and spec-faithful. The only findings were a cluster of **documentation-accuracy defects** (three stale "CWN-only" docstrings that misstate the contract this PR changes) plus three non-blocking test-rigor enhancements. None of these block merge. Per the user's decision (Approve-with-cleanup), I fixed every finding **in-review** rather than bouncing the story back to Dev: all five docstrings reworded to describe the `isinstance(module, CwnRulesetModule)` capability gate, and all three test-hardening items landed (shock `state_patch.hp` span assertion, forced-hit reprisal damage assertion, empty-`attribute_map` "none authored" branch test). Re-ran the 7 affected files after the edits: **37/37 green**, ruff lint + format clean. The findings table below is preserved as the audit trail; every row is now **RESOLVED**.

**Resolution (in-review, by Reviewer):**
- C1–C3 (MEDIUM [DOC] stale "CWN-only" / "cwn/wwn" docstrings) → ✅ FIXED — `adjust_system_strain.py`, `stabilize_mortal_injury.py`, `downed_seam.py` module docstrings now describe the capability gate.
- C4–C5 (LOW [DOC] test fixture docstrings) → ✅ FIXED — both `_FakeAwnRules` docstrings reworded to the shipped capability form.
- T1 (LOW [TEST] shock HP-span) → ✅ FIXED — `test_awn_shock_chips_hp_on_miss` now asserts `state_patch.hp in span_names` (passes non-vacuously: span fired).
- T2 (LOW [TEST] reprisal damage) → ✅ FIXED — `test_awn_opponent_reprisal_fires` now monkeypatches `dice.random.randint → b` (forced d20 hit) and asserts player ablative HP dropped (passes: reprisal dealt damage).
- T4 (LOW [TEST] empty-map branch) → ✅ FIXED — new `test_rules_awn_empty_attribute_map_hits_none_authored_branch` asserts `match="none authored"` (passes: distinct branch exercised).
- R1 (LOW [SIMPLE] optional import-hoist) → ⏭️ ACCEPTED as-is — mirrors the existing `physical_save_target_for` convention; not required.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [MEDIUM] [DOC] | Module docstring Guards section still says `ruleset != "cwn"` → "tool is CWN-only"; tool now accepts AWN via the capability gate | `sidequest/agents/tools/adjust_system_strain.py:16` | Reword to describe the `isinstance(module, CwnRulesetModule)` gate (CWN-family: cwn/awn) |
| [MEDIUM] [DOC] | Same stale "CWN-only" Guards bullet | `sidequest/agents/tools/stabilize_mortal_injury.py:23` | Same — describe the capability gate |
| [MEDIUM] [DOC] | Module-level summary still says seam is gated on "ruleset is `cwn`/`wwn`" (the function docstring was updated, the module summary was not) | `sidequest/server/dispatch/downed_seam.py:15` | Update the module summary to match the function docstring (capability gate covers cwn/wwn/awn) |
| [LOW] [DOC] | Test fixture docstrings describe the pre-fix guard in present tense ("current guard blocks it") although the fix has landed | `tests/agents/tools/test_adjust_system_strain_tool.py:325`, `tests/agents/tools/test_stabilize_mortal_injury_tool.py:404` | Reword to describe the shipped capability gate (recommended) |
| [LOW] [TEST] | `test_awn_shock_chips_hp_on_miss` doesn't assert `state_patch.hp` fired (ADR-114 lie-detector for the AWN shock HP path) | `tests/server/test_awn_combat_dispatch.py` (shock test) | Add `assert "state_patch.hp" in span_names` (recommended) |
| [LOW] [TEST] | `test_awn_opponent_reprisal_fires` proves the reprisal engaged (span fires on attempt incl. miss) but not that it dealt damage | `tests/server/test_awn_combat_dispatch.py` (reprisal test) | Monkeypatch opponent d20 to a guaranteed hit + assert player HP dropped (recommended) |
| [LOW] [TEST] | `_validate_awn` empty-`attribute_map` branch (distinct "none authored" message) untested | `tests/game/ruleset/test_awn_config.py` | Add `AwnConfig(attribute_map={})` case asserting `match="none authored"` (recommended) |
| [LOW] [SIMPLE] | Function-local `from ...rules import CwnConfig, WwnConfig` could be hoisted (rules already imported top-level), but mirrors existing `physical_save_target_for` pattern | `sidequest/server/dispatch/downed_seam.py:129` | Optional tidy — not required |

**Subagent dispatch tags (all 8 accounted for):**
- `[DOC]` — comment-analyzer (ENABLED): 5 stale-comment findings confirmed (C1–C3 blocking, C4–C5 recommended). The crux of this rejection.
- `[TEST]` — test-analyzer (ENABLED): 7 findings; 3 confirmed as recommended hardening (shock HP-span, reprisal HP delta, empty-map), 4 deferred (level-scaled save target, AWN stabilize-failure path, Constitution=1 boundary, reprisal-test monkeypatch flakiness — all genuinely low-risk because they exercise inherited-from-CWN paths already covered by the CWN suite).
- `[RULE]` — rule-checker (ENABLED): R1 (function-local import, LOW, mirrors existing convention) confirmed; R2 (redundant `assert self.awn is not None`) **DISMISSED** — it mirrors `_validate_swn:1112`/`_validate_cwn:1139`/`_validate_wwn:1188` verbatim (the deliberate "assert for pyright" type-narrowing convention); removing it from awn alone would diverge from the siblings and break pyright narrowing.
- `[EDGE]` — edge-hunter DISABLED via settings; I manually checked boundary conditions: empty/partial attribute_map (validated, fail-loud), Constitution=0 floor (clamped to 1, tested), unknown slug (UnknownRulesetError, tested), level=1 save target boundary (tested =15). No unhandled boundary found.
- `[SILENT]` — silent-failure-hunter DISABLED; I manually checked for swallowed errors: no try/except added anywhere in the diff; every guard either raises ValueError (fail loud) or returns early as a *documented* no-op (downed seam inapplicable config, `seed_system_strain` None for non-CWN). No silent fallback.
- `[TYPE]` — type-design DISABLED; I manually checked: `AwnConfig`/`AwnRulesetModule` are honest subclasses (capability binding); `ruleset_config() -> SwnConfig | None` annotation remains correct since `AwnConfig` IS-A `SwnConfig`; new field `awn: AwnConfig | None = None` typed correctly; no stringly-typed regressions (the change *removes* slug-string coupling in favor of isinstance).
- `[SEC]` — security DISABLED; manually checked: no auth/tenant/secret surface here (single-tenant personal project; `tenant isolation` N/A). Input validation is *strengthened* (`_validate_awn` fail-loud). No injection/deserialization surface (pydantic `model_validate` only).
- `[SIMPLE]` — simplifier DISABLED; manually checked: changes are minimal and reduce complexity (slug-string branches → single isinstance capability check). The removed redundant `assert` in `adjust_system_strain` is a simplification. Only the optional import-hoist (R1) remains.

### Rule Compliance (python.md 13-check + project rules)

Enumerated every changed type/function/field against the python lang-review checklist:
- **#1 Silent exceptions:** COMPLIANT — no try/except added; all guards raise ValueError or documented early-return.
- **#2 Mutable defaults:** COMPLIANT — `run_cwn_wwn_downed_seam(rng=random)` is a module sentinel, not a mutable container; pydantic `Field(default_factory=…)` throughout; `awn=None`.
- **#3 Type annotations:** COMPLIANT — `_validate_awn(self) -> RulesConfig`, `seed_system_strain(...) -> SystemStrainPool | None`, `awn: AwnConfig | None` all annotated. (rule-checker flagged the `assert` under #3 — dismissed, see [RULE].)
- **#4 Logging:** COMPLIANT/N-A — no logging module in these paths; errors raise (consistent with the pre-existing tool pattern).
- **#5 Path handling:** N/A — no path ops.
- **#6 Test quality:** COMPLIANT for vacuity — every new test asserts a concrete value/span/raised error (verified each of the 16). Gaps found are *missing edge cases* (T1/T2/T4), not vacuous assertions.
- **#7 Resource leaks:** N/A — no resources acquired.
- **#8 Unsafe deserialization:** COMPLIANT — pydantic `model_validate` only; no pickle/eval/yaml.load.
- **#9 Async pitfalls:** COMPLIANT — the two async tool handlers add only a synchronous in-memory `get_ruleset_module` dict lookup; no blocking call, no missing await.
- **#10 Import hygiene:** 1 LOW (R1 function-local import; could hoist, mirrors existing pattern). No star imports, no circular import introduced (registry top-level import + tests green prove it).
- **#11 Input validation:** COMPLIANT (strengthened) — `_validate_awn` validates attribute_map completeness, flavor-in-ability-scores, strain source, and major_injury_save before use.
- **#12 Dependency hygiene:** N/A — no dep changes.
- **#13 Fix-introduced regressions:** COMPLIANT — broadened guards are covered by regression tests (swn/native still None; raw SwnConfig still rejected at the downed seam).
- **Project rules:** No Silent Fallbacks ✓ (fail-loud validation + UnknownRulesetError). No Stubbing ✓ (empty class bodies are *complete* — inherit CWN verbatim, documented). Wire-up ✓ (`AwnRulesetModule` registered + reached via `get_ruleset_module` at `dice.py:297`; `AwnConfig` consumed by `ruleset_config()` + `_validate_awn` at pack-load). OTEL ✓ (inherits cwn.* spans verbatim; no new undecorated decision point — this is a binding change, not a new subsystem). **No-Source-Text-Wiring-Tests ✓** — the integration suite asserts OTEL spans + HP state, never greps source.

### Observations (≥5)

1. `[VERIFIED]` Registry wiring is real, not just present — `AwnRulesetModule` is registered at `registry.py:16` AND reached from production via `get_ruleset_module(pack.rules.ruleset)` at `dice.py:297`; `test_awn_combat_dispatch.py` drives that production path. Complies with the "Verify Wiring, not just existence" rule.
2. `[VERIFIED]` Capability binding is correct — `AwnConfig(CwnConfig)` and `AwnRulesetModule(CwnRulesetModule)` mean every `isinstance(cfg, CwnConfig)` / `isinstance(module, CwnRulesetModule)` site (downed seam :71, tools, builder) covers AWN with no new branch; verified `issubclass` holds (`test_awn_module_is_a_cwn_subclass`).
3. `[VERIFIED]` Fail-loud preserved — `_validate_awn` mirrors `_validate_cwn` exactly and raises on incomplete map / bad strain source / bad save; `get_ruleset_module("ashes")` still raises (`test_unknown_ruleset_still_fails_loud_after_awn`). Evidence: `rules.py` _validate_awn body; registry.py:18-24.
4. `[VERIFIED]` No regression in sibling rulesets — `seed_system_strain` capability gate returns None for SWN (`SwnConfig` is not `CwnConfig`) and native (None); `test_swn_still_returns_none` + `test_ruleset_config_awn_is_none_when_ruleset_is_not_awn` prove it. WWN strain behavior unchanged (`WwnConfig` is not a `CwnConfig`, same as before).
5. `[MEDIUM][DOC]` Three module docstrings misdocument the changed contract (C1–C3) — see severity table. Confirmed high-confidence by comment-analyzer.
6. `[LOW][TEST]` The reprisal wiring proof asserts span-on-attempt, not damage-on-hit (T2) — the engine-engaged claim holds, but the proof would survive a no-op reprisal. Recommended hardening.
7. `[VERIFIED]` Data flow traced — a player `shoot` intent → `dispatch_dice_throw` → `get_ruleset_module("awn")` → inherited `resolve_trauma`/`resolve_shock` → `apply_beat_hp_channel` (HP ablation + `state_patch.hp`) → `run_cwn_wwn_downed_seam` (now isinstance-gated, fires `cwn.mortal_injury.declared` for AWN) → opponent reprisal. End-to-end exercised by the integration suite.

### Tenant isolation audit
N/A — single-tenant personal project (sidequest-server/CLAUDE.md). No `tenant_id`, auth, or multi-tenant data surface in the diff. The two tool handlers take `ctx: ToolContext` (session-scoped), no cross-session leakage introduced.

### Devil's Advocate

Let me argue this code is broken. **First attack — the capability gate is a silent-failure factory.** `seed_system_strain` now returns `None` for anything that isn't a `CwnConfig`. What if a future `AwnConfig` author forgets `system_strain` tuning? It can't — `AwnConfig` inherits `system_strain` with a default and `_validate_awn` enforces `max_source` is a real attribute key, so the pool always seeds. What if `ruleset_config()` returns `None` for an `awn` pack whose `awn` block failed to populate? It can't — `_validate_awn` calls `object.__setattr__(self, "awn", AwnConfig())` then immediately rejects the empty map, so an `awn` pack either has a valid `awn` block or fails to load. **Second attack — the downed-seam isinstance gate now fires for configs it shouldn't.** Could a non-combat `awn` config slip through? `ruleset_config()` returns the `awn` block only when `ruleset == "awn"`; native/swn return None/SwnConfig and are correctly excluded (`isinstance(None | SwnConfig, (CwnConfig, WwnConfig))` is False) — and `test_physical_save_target_still_rejects_swn_config` proves the SwnConfig rejection survives. **Third attack — a confused author binds `ruleset: awn` but authors a `cwn:` block instead of `awn:`.** Then `awn is None` → validator auto-creates an empty `AwnConfig()` → empty map → fail-loud at load. Good — they find out immediately, not mid-combat. **Fourth attack — the tools now resolve `get_ruleset_module(pack.rules.ruleset)` in the guard; what if `ruleset` is an unregistered string?** `get_ruleset_module` raises `UnknownRulesetError` rather than the tool's own ValueError — a slightly different exception type than before, but still fail-loud (not a silent pass), and an unregistered ruleset would already have failed at pack load. **Fifth attack — the reprisal test is a paper tiger.** This one lands: `test_awn_opponent_reprisal_fires` asserts only that `encounter.opponent_attack_resolved` fired, and that span fires even on a missed reprisal, so a regression that broke reprisal *damage* (while still emitting the span) would sail through green. That's why I've flagged T2 as a required-recommended hardening. **Sixth attack — stale docs cause a real bug later.** A maintainer extending `stabilize_mortal_injury` reads "tool is CWN-only," assumes AWN is rejected, and adds an AWN special-case that double-handles — a latent bug seeded by a false comment. That is the concrete harm behind the doc rejection. The implementation itself, however, survives every logic attack: it is correct, fail-loud, and faithful to the spec. The defects are in what it *says* (docs) and what the tests *prove* (reprisal damage), not in what it *does*.

**Data flow traced:** player `shoot` intent → `dispatch_dice_throw` → `get_ruleset_module("awn")` → inherited `resolve_trauma`/`resolve_shock` → `apply_beat_hp_channel` (HP ablation + `state_patch.hp`) → `run_cwn_wwn_downed_seam` (isinstance-gated, fires `cwn.mortal_injury.declared` for AWN) → opponent reprisal. End-to-end exercised by `test_awn_combat_dispatch.py` (safe: every seam asserts an OTEL span + HP state, never source text).
**Pattern observed:** capability binding via subclass — `AwnConfig(CwnConfig)` / `AwnRulesetModule(CwnRulesetModule)` make every `isinstance(..., CwnConfig/CwnRulesetModule)` site cover AWN with no new branch (`registry.py:16`, `dice.py:297`).
**Error handling:** fail-loud throughout — `_validate_awn` raises on incomplete/empty map, bad strain source, bad save (`rules.py:1238`+); `get_ruleset_module` raises `UnknownRulesetError` for unregistered slugs. No silent fallback, no swallowed errors.

**Handoff:** To SM (the Mad Hatter) for finish-story — all findings resolved in-review, 37/37 affected tests green, lint/format clean. No logic changes were ever required; the implementation was correct as delivered.