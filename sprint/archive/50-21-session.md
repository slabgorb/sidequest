---
story_id: "50-21"
jira_key: none
epic: "50"
workflow: "tdd"
---

# Story 50-21: Scene harness: hydrate StructuredEncounter (ADR-092 follow-on)

## Story Details

- **ID:** 50-21
- **Epic:** 50 — Pingpong-archive triage and dropped-work cleanup
- **Jira Key:** None (personal project, no Jira)
- **Workflow:** tdd (phased: setup → red → green → spec-check → verify → review → spec-reconcile → finish)
- **Repo:** sidequest-server
- **Points:** 3
- **Priority:** p2
- **Stack Parent:** none

## Technical Context

**Upstream dependencies completed:**
- 50-18: ADR-092 scene harness — Python POST /dev/scene/{name} hydrator (completed 2026-05-13)
- 50-20: Scene harness: hydrate top-level scenario_state (completed 2026-05-15)

**Related completed stories in this epic:**
- 50-19: Scene harness: hydrate Character.known_facts (completed 2026-05-15)
- 50-23: Scene harness: hydrate multi-PC characters list (completed 2026-05-15)

**User-facing goal:**
The fixture `combat_brawl_wasteland.yaml` (located at `scenarios/fixtures/combat_brawl_wasteland.yaml`) includes a top-level `encounter:` block that is currently silently ignored during hydration. This story wires the encounter block through to `GameSnapshot.encounter` so that pre-armed combat fixtures can initialize with a ready-to-use StructuredEncounter.

**Current behavior:**
```yaml
encounter:
  type: combat
```

This block is present in the YAML but not read by `hydrate_fixture()`, so `snapshot.encounter` remains `None`.

**Desired behavior after this story:**
The `encounter:` block is parsed and projected to `GameSnapshot.encounter`, a fully-hydrated `StructuredEncounter` instance. The fixture YAML acts as the authoritative source for the encounter type and initial state.

**Schema references:**
- `sidequest/game/encounter.py` — `StructuredEncounter` model (lines 136-209)
- `sidequest/game/session.py` — `GameSnapshot` (line 515+), includes `encounter: StructuredEncounter | None = None` field
- ADR-033 — Confrontation engine (game mechanics)
- ADR-092 — Scene harness (hydrator design and error discipline)
- ADR-069 — Fixture YAML schema (predecessor design, kept for historical reference)

**Downstream unblocking:**
Unblocks Wave 2 pre-armed combat fixtures for ADR-093 confrontation difficulty calibration spot tests:
- `combat_pretier_low.yaml` (not yet authored)
- `combat_pretier_mid.yaml` (not yet authored)
- `combat_pretier_high.yaml` (not yet authored)

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-18T11:28:49Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-18 | 2026-05-18T10:59:54Z | 10h 59m |
| red | 2026-05-18T10:59:54Z | 2026-05-18T11:08:14Z | 8m 20s |
| green | 2026-05-18T11:08:14Z | 2026-05-18T11:14:07Z | 5m 53s |
| spec-check | 2026-05-18T11:14:07Z | 2026-05-18T11:17:26Z | 3m 19s |
| verify | 2026-05-18T11:17:26Z | 2026-05-18T11:21:46Z | 4m 20s |
| review | 2026-05-18T11:21:46Z | 2026-05-18T11:26:59Z | 5m 13s |
| spec-reconcile | 2026-05-18T11:26:59Z | 2026-05-18T11:28:49Z | 1m 50s |
| finish | 2026-05-18T11:28:49Z | - | - |

## Acceptance Criteria

**AC-1: Encounter block hydration**
The `_hydrate_encounter()` helper reads a fixture's top-level `encounter:` block (if present) and projects it to `GameSnapshot.encounter` as a fully-initialized `StructuredEncounter`. Missing `encounter:` block → `snapshot.encounter` stays `None` (backward-compat with the four canonical fixtures that predate this story).

**AC-2: Encounter type validation**
The `encounter_type` field is required when the `encounter:` block is present. A missing or empty `encounter_type:` raises `FixtureValidationError` (HTTP 422) with the field name in the message. No silent default to `"combat"`.

**AC-3: Metric initialization**
`player_metric` and `opponent_metric` are initialized with sensible defaults when not explicitly provided in the fixture. Both metrics start with:
- `current: 0`
- `starting: 0`
- `threshold: 10` (default escalation point)

Optional YAML override per metric allows fixture authors to set custom thresholds.

**AC-4: combat_brawl_wasteland hydrates without error**
The existing `combat_brawl_wasteland.yaml` fixture (lines 66-68: `encounter: type: combat`) hydrates cleanly via the fixture hydrator. Post-hydration, `snapshot.encounter.encounter_type == "combat"` and metrics are initialized to defaults.

**AC-5: Wiring test (integration)**
A test named `test_combat_brawl_wasteland_fixture_encounter_hydrated()` in `tests/game/test_scene_harness_hydrator.py` exercises the full path: load the fixture → hydrate → verify `snapshot.encounter` is non-None and has the expected type. This test proves the hydrator is wired into the test suite.

**AC-6: HTTP endpoint wiring (endpoint-level)**
`POST /dev/scene/combat_brawl_wasteland` returns a slug that can reconnect via `GET /connect/{slug}` and receive opening narration. The response includes the encounter in the GameSnapshot persisted to the store. Verifiable via the UI `?scene=combat_brawl_wasteland` flow (requires `DEV_SCENES=1`).

**AC-7: YAML order stability**
When a fixture provides optional metric overrides, the hydrator accepts them in any YAML key order and projects them correctly. No silent reordering or validation side-effects.

**AC-8: Backward compatibility**
The four canonical fixtures (`combat_brawl_wasteland`, `combat_dogfight_space`, `social_negotiation_tea`, `social_poker_wasteland`) continue to hydrate without error. Fixtures without an `encounter:` block still work (snapshot.encounter == None).

## Implementation Plan

**Phase: RED (TEA)**

1. **TC-R1: Read ADR-033 and encounter.py** to understand StructuredEncounter shape
2. **TC-R2: Draft _hydrate_encounter() helper** that mirrors the pattern of `_hydrate_scenario_state()` and `_hydrate_character()`:
   - Accept raw YAML dict from `data.get("encounter")`
   - Validate encounter_type is present and non-empty (fail loudly)
   - Initialize metrics with defaults (threshold=10)
   - Support optional per-metric overrides
   - Raise FixtureValidationError on validation failures
   - Return StructuredEncounter instance

3. **TC-R3: Draft test skeleton** for test_scene_harness_hydrator.py:
   - `test_encounter_block_missing_returns_none()` — fixture without encounter block → snapshot.encounter is None
   - `test_combat_brawl_wasteland_fixture_encounter_hydrated()` — the canonical fixture hydrates encounter correctly
   - `test_encounter_missing_type_raises_error()` — encounter block without `type:` → FixtureValidationError
   - `test_encounter_custom_metric_threshold()` — fixture with metric override → metrics initialized to override value
   - `test_canonical_fixture_4pack_all_hydrate()` — all four canonical fixtures hydrate without error

**Phase: GREEN (Dev)**

1. **TC-G1: Implement _hydrate_encounter()** in scene_harness.py, following the error-discipline pattern
2. **TC-G2: Wire _hydrate_encounter() into hydrate_fixture()** — call the helper if `data.get("encounter")` is present and assign to snapshot_kwargs
3. **TC-G3: Implement test cases** from the RED phase skeleton
4. **TC-G4: Verify the four canonical fixtures still pass** their original tests (backward-compat gate)

**Phase: SPEC-CHECK (Architect)**

1. **Spec deviation log** — Record any minor deviations from the story description (e.g., metric threshold default choice)
2. **Schema consistency** — Verify StructuredEncounter defaults don't collide with future materialization logic
3. **ADR-092 alignment** — Confirm "Failure is loud" discipline is maintained

**Phase: VERIFY (TEA + Teammates)**

1. Run linter + type checker (pyright)
2. Run full test suite (pytest) — gate on all tests passing
3. Simplify review (reuse / quality / efficiency passes)

**Phase: REVIEW (Reviewer)**

1. Code review for correctness and style
2. Verify wiring test proves end-to-end integration

**Phase: SPEC-RECONCILE (Architect)**

1. Reconcile any findings from review

**Phase: FINISH (SM)**

1. Archive session file
2. Update sprint YAML status → done

## Sm Assessment

**Setup complete — ready for RED handoff to TEA.**

- **Scope:** Tight, well-bounded 3-pointer. Single repo (sidequest-server), single helper (`_hydrate_encounter()`) following the established `_hydrate_scenario_state()` / `_hydrate_character()` pattern. No cross-repo coordination, no UI work.
- **Dependencies:** Both upstream hydrators (50-18 POST /dev/scene endpoint, 50-20 scenario_state) completed and merged 2026-05-15. Nothing blocks RED.
- **Jira:** Explicitly skipped — personal project, sprint YAML tracking only (per project doctrine, not an oversight).
- **Risk notes for TEA/Dev:**
  - AC-3 metric default (`threshold=10`) is a setup-time guess. Architect should confirm against ADR-033 confrontation-engine defaults during SPEC-CHECK so we don't bake in a number that collides with materialization logic.
  - "Fail loudly" is load-bearing here (AC-2): a missing `encounter_type:` must raise `FixtureValidationError`, never silent-default to `"combat"`. This is a No-Silent-Fallbacks story by nature — keep the discipline.
  - AC-8 backward-compat: the four canonical fixtures must keep hydrating. Make the canonical-4-pack test a real gate, not a smoke check.
- **Routing:** TDD phased → next agent **TEA** (RED phase). No stepped start command.

## TEA Assessment

**Tests Required:** Yes
**Reason:** New behavior (encounter-block hydration + validation). Not a chore-bypass case.

**Test Files:**
- `sidequest-server/tests/game/test_scene_harness_hydrator.py` — appended a Story 50-21 section (`_write_encounter_fixture` helper + 10 tests) mirroring the 50-20 scenario_state patterns.

**Tests Written:** 10 tests covering all 8 ACs.
**Status:** RED (verified by testing-runner, run_id `50-21-tea-red`).

- 9 fail for the correct reason: `snapshot.encounter` is None / no `FixtureValidationError` raised (encounter branch not yet implemented).
- 1 (`test_encounter_block_missing_leaves_snapshot_none`) passes by design — it is the AC-1/AC-8 backward-compat guard (encounter correctly None when no block), structurally identical to 50-20's `test_missing_scenario_state_block_leaves_snapshot_none`.
- 0 pre-existing regressions (68/68 prior tests still green — collection and shared helpers intact).

**AC → test map:**

| AC | Test(s) |
|----|---------|
| AC-1 missing block → None | `test_encounter_block_missing_leaves_snapshot_none` |
| AC-2 type validation (fail loud) | `test_encounter_missing_type_raises_FixtureValidationError`, `test_encounter_empty_type_raises_FixtureValidationError`, `test_encounter_block_not_a_mapping_raises` |
| AC-3 metric defaults + override | `test_encounter_default_metrics_initialized`, `test_encounter_custom_metric_threshold` |
| AC-4 combat_brawl_wasteland hydrates | `test_combat_brawl_wasteland_fixture_encounter_hydrated` |
| AC-5 wiring (integration) | `test_combat_brawl_wasteland_fixture_encounter_hydrated` (real CANONICAL_FIXTURES_DIR), `test_canonical_fixtures_still_hydrate_with_encounter_implementation` |
| AC-6 HTTP endpoint wiring | Deferred to Dev — see Delivery Findings (endpoint-level test belongs with the GREEN wire-up in `scene_harness_router`) |
| AC-7 YAML order stability | `test_encounter_metric_override_any_yaml_key_order` |
| AC-8 backward-compat (4 fixtures) | `test_canonical_fixtures_still_hydrate_with_encounter_implementation` |

### Rule Coverage

| Rule (lang-review/python.md) | Test(s) | Status |
|------|---------|--------|
| #1 silent exception swallowing | `test_encounter_missing_type_raises_FixtureValidationError` (no silent default) | failing (RED) |
| #6 test quality (self-check) | self-reviewed all 10 — every test has a meaningful assertion; no `assert True`, no truthy-only checks, no assertion-free bodies | n/a |
| #8 unsafe deserialization | no new deserialization surface — encounter parsed from the already-`yaml.safe_load`ed `data` dict; existing `test_hydrator_uses_yaml_safe_load_not_yaml_load` still covers the module | covered (no new path) |
| #11 input validation at boundary | `test_encounter_missing_type_*`, `test_encounter_empty_type_*`, `test_encounter_block_not_a_mapping_raises`, `test_encounter_legacy_metric_key_raises_FixtureValidationError` | failing (RED) |

**Rules checked:** 4 of 14 lang-review rules apply to this change; all 4 have coverage. Rules #2/#4/#5/#7/#9/#10/#12/#13/#14 are not exercised by an encounter-hydration helper.
**Self-check:** 0 vacuous tests found.

**Handoff:** To Dev for GREEN implementation of `_hydrate_encounter()` + wiring into `hydrate_fixture()`.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/scene_harness.py` — added `EncounterMetric, StructuredEncounter` import; added `_hydrate_encounter()` helper (maps fixture `type` → `encounter_type`, default metrics current=0/starting=0/threshold=10, optional per-metric `threshold` override, up-front legacy `metric` guard, all malformed shapes → `FixtureValidationError`); wired the call into `hydrate_fixture()` after the `scenario_state` branch, gated on `"encounter" in data and data.get("encounter") is not None`.
- `sidequest-server/tests/server/test_scene_harness.py` — added `test_dev_scene_route_persists_encounter_end_to_end` (AC-6 endpoint round-trip, TEA-deferred), mirroring the 50-20 `test_dev_scene_route_persists_scenario_state_end_to_end` precedent.

**Tests:** 99/99 passing (GREEN) — 76 hydrator + 23 server scene-harness; 0 regressions. ruff clean, pyright 0 errors on the changed module.
**Branch:** `feat/50-21-hydrate-structured-encounter` (pushed, tracking origin).

**AC closure:**
- AC-1/AC-8: missing/null block → encounter None; 3 no-encounter canonical fixtures stay None — green.
- AC-2: missing/empty `type`, non-mapping block, legacy `metric` → `FixtureValidationError` — green.
- AC-3: default threshold=10 both metrics; per-metric override honored independently — green.
- AC-4/AC-5: real `combat_brawl_wasteland` hydrates `encounter_type=="combat"` via CANONICAL_FIXTURES_DIR — green.
- AC-6: endpoint POST → SqliteStore round-trip preserves encounter_type + threshold override — green (new test).
- AC-7: reordered YAML keys still bind — green.

**Handoff:** To next phase (spec-check / Architect).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (code is correct against the highest-authority spec — session AC-3)
**Mismatches Found:** None requiring code change. Three ambiguous-spec clarifications + one deferred forward-impact note. The SM/Dev open question on `threshold=10` is **resolved with evidence**.

**Gate:** spec_check structural validation passed (AC coverage present, implementation complete, TEA + Dev deviation subsections well-formed).

**Substantive findings:**

- **`threshold=10` default — SM/Dev open question, RESOLVED, no collision** (Architectural — Behavioral, was the load-bearing concern)
  - Spec: SM flagged "confirm against ADR-033 confrontation-engine defaults so we don't bake in a number that collides with materialization logic."
  - Evidence: (1) ADR-033's own standoff example uses `threshold_high: 10` (033-confrontation-engine-resource-pools.md:131) — Dev's default *matches* the ADR's illustrative value. (2) Runtime resolution path `sidequest/game/beat_kinds.py:745,750` consumes `enc.{player,opponent}_metric.current >= .threshold` — the hydrated value is load-bearing and correctly typed. (3) `sidequest/game/world_materialization.py` has **zero** encounter/threshold references — the "materialization collision" risk does not exist. (4) Runtime-initiated encounters draw thresholds from the genre `ConfrontationDef` (`sidequest/server/dispatch/encounter_lifecycle.py:420-435`), **not** a global constant — so the fixture default competes with no runtime default.
  - Recommendation: **dismiss** — no code change. The default is a sound, evidence-backed scaffold convenience.

- **`type:` → `encounter_type` key mapping** (Ambiguous spec — Cosmetic, Trivial)
  - Spec: AC-2 names the model field `encounter_type`; AC-4 cites the canonical fixture's `encounter:\n  type: combat`.
  - Code: hydrator maps fixture key `type` → model `encounter_type`.
  - Recommendation: **C (clarify spec)** — code is the only viable reading (AC-8 freezes the canonical fixture). Logged for traceability; no code change.

- **Per-metric override keyed on model field names, scoped to `threshold`** (Ambiguous spec — Behavioral, Minor)
  - Spec: AC-3 "Optional YAML override per metric allows fixture authors to set custom thresholds."
  - Code: overrides keyed `player_metric:`/`opponent_metric:` with nested `threshold:` only (not full EncounterMetric).
  - Recommendation: **C (clarify spec)** — mirrors the 50-20 scenario_state precedent (model-field-name keying) and AC-3 explicitly scopes the override to thresholds. Correct restraint, no scope creep.

- **Fixture encounters intentionally bypass the genre ConfrontationDef** (Architectural — Behavioral, Minor)
  - Spec: AC-3 explicitly designs the simple default path; it does not ask the hydrator to resolve genre confrontation defs.
  - Code: matches AC-3 exactly — a flat `type: combat` yields a generic StructuredEncounter (no genre metric names, no secondary_stats, no actors, phase unset).
  - Recommendation: **D (defer)** — forward-impact note for the ADR-093 story author: Wave 2 pre-tier calibration fixtures (combat_pretier_low/mid/high) **must declare explicit per-metric `threshold` values**; the default 10 is a scaffold convenience, not a genre-calibrated number. The per-metric override the Dev built is precisely the calibration knob ADR-093 needs — design is sufficient for its stated downstream purpose.

- **No OTEL in the hydrator** — concur with Dev. Consistent with sibling hydrators (`_hydrate_scenario_state`, `_hydrate_character`); route-layer load/hydrate/persist spans already exist (`test_scene_harness_emits_*_span`). Dev-gated fixture projection is not a runtime subsystem decision — the OTEL lie-detector principle targets the encounter *engine* (beat_kinds resolution), which this story does not touch. Not a mismatch.

**Decision:** Proceed to review (verify / TEA). No hand-back to Dev — implementation is correct against session AC-3, ADR-033, and the runtime resolution contract.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (99/99 passing post-simplify; ruff clean; pyright 0 errors on the changed module)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`scene_harness.py`, `test_scene_harness_hydrator.py`, `test_scene_harness.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | medium: extract a shared `_validate_required_string()` (genre/world + encounter_type repeat the `not isinstance(str) or not strip()` + FixtureValidationError pattern) |
| simplify-quality | 3 findings | high: stale module docstring (only cited 50-18/50-19); low: `_threshold() -> Any` return precision; medium: docstring/story-list naming inconsistency (same root as the high finding) |
| simplify-efficiency | clean | no findings — closure scoped correctly, validation strictness is intentional fail-loud, no over-abstraction |

**Applied:** 1 high-confidence fix — refreshed the test-file module docstring to document all five story sections (50-18/19/23/20/21) and the banner layout (commit `17525d2`). The quality medium finding shared this root and is resolved by the same edit.
**Flagged for Review (not auto-applied, medium):** `_validate_required_string()` extraction. Deliberately deferred — the duplicated counterpart (genre/world validation, lines ~122-129) is **pre-existing code not touched by this story**; refactoring it in a verify pass is scope creep and risks untested churn. Recorded as a non-blocking Improvement finding for a future cleanup.
**Noted (low, not applied):** `_threshold() -> Any` return type. Defensible as-is — the override value is intentionally untyped at that point because pydantic validates it at `StructuredEncounter`/`EncounterMetric` construction (the wrapped `ValidationError → FixtureValidationError` path). Tightening to `int | Any` adds no safety.
**Reverted:** 0.

**Overall:** simplify: applied 1 fix
**Quality Checks:** All passing (ruff clean, pyright 0 errors, 99/99 pytest, 0 regressions)
**Handoff:** To Reviewer for code review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 smells, 99/99 GREEN, ruff+pyright clean | N/A (1 wiring note → verified by Reviewer) |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

**All received:** Yes (1 enabled subagent returned; 8 disabled via `workflow.reviewer_subagents` settings — Reviewer performed the analytical hunt directly per the lean-review config)
**Total findings:** 3 confirmed (all LOW, non-blocking), 0 dismissed, 0 deferred. Preflight's wiring note resolved with evidence.

## Reviewer Assessment

**Verdict:** APPROVED

**Subagent config:** Only `reviewer-preflight` is enabled (project lean-review setting). The eight analytical specialists are disabled, so the rule-by-rule, edge, silent-failure, test-quality, type, security, and simplifier analysis below was performed directly by the Reviewer against the diff and the python lang-review checklist.

**Preflight:** GREEN — 99/99 tests (66 hydrator-unit + 33 server-integration), 0 code smells, ruff/pyright clean. The three warnings (FastAPI `on_event`, Pydantic field-shadow) are pre-existing, not introduced by this branch.

**Wiring verification (CLAUDE.md "Verify Wiring, Not Just Existence"):** Preflight flagged that `GameSnapshot.encounter` might be write-only from the dev-gated harness. **Resolved with evidence:** `snapshot.encounter` is read by live production paths — `sidequest/server/websocket_session_handler.py:2767,2783,2844,2850,3001` (turn handler engages confrontation when `encounter is not None and not encounter.resolved`), `sidequest/server/narration_apply.py:2530,2555`, `sidequest/game/taunt_tick.py:19,22`, and the narrator tool `sidequest/agents/tools/advance_confrontation.py`. End-to-end: fixture → `hydrate_fixture` → `snapshot.encounter` → SqliteStore → slug-connect → `websocket_session_handler` reads it → confrontation engine engages. Not write-only.

**Data flow traced:** fixture YAML `encounter:` block → `_hydrate_encounter(raw, fixture_name)` → validated `StructuredEncounter` → `snapshot_kwargs["encounter"]` → `GameSnapshot(**snapshot_kwargs)` → persisted by `SqliteStore` → consumed by the turn pipeline. Safe: every malformed shape (`{}`, `[]`, scalar, `type: 123`, missing/blank `type`, legacy `metric`, non-mapping override) raises `FixtureValidationError` (HTTP 422) before reaching `GameSnapshot`; the only `ValidationError` source (pydantic on `StructuredEncounter`/`EncounterMetric`) is wrapped at line 114-117, never leaked.

**Pattern observed:** `_hydrate_encounter` mirrors `_hydrate_scenario_state` / `_hydrate_character` error-discipline exactly (scene_harness.py:509-589) — fail-loud `FixtureValidationError`, pydantic re-wrap, optional-block gate identical to the 50-20 `scenario_state` branch (line 235-242).

### Rule Compliance (python lang-review checklist)

- **#1 silent exception swallowing** — COMPLIANT. `except ValidationError as exc: raise FixtureValidationError(...) from exc` re-raises with chaining; no bare except, no swallow.
- **#2 mutable default arguments** — COMPLIANT. `_write_encounter_fixture(..., encounter_yaml: str | None = None)`; no mutable defaults anywhere in the diff.
- **#3 type annotations at boundaries** — COMPLIANT. `_hydrate_encounter(raw: Any, *, fixture_name: str) -> StructuredEncounter` fully annotated. The nested `_threshold(key: str) -> Any` is a private closure (rule #3 exempts internal/private helpers); `Any` is honest — the value is intentionally unvalidated until pydantic construction.
- **#4 logging coverage/correctness** — COMPLIANT. Fixture-author input failures raise `FixtureValidationError` (mapped to 422 / logged at the route boundary, the established sibling pattern); rule #4 classifies user-input validation as info-level, not error — raising is correct, no misleveled logging introduced.
- **#5 path handling** — COMPLIANT / N/A. `_hydrate_encounter` performs no path manipulation.
- **#6 test quality** — COMPLIANT. 10 hydrator tests + 1 endpoint test, all with specific assertions (exact thresholds, `isinstance`, `encounter_type` equality), no `assert True`, no skips, no truthy-only checks. One LOW note below (empty-type test omits a message assertion).
- **#8 unsafe deserialization** — COMPLIANT. No new `yaml.load`; encounter is read from the already-`yaml.safe_load`-ed `data` dict.
- **#11 input validation at boundary** — COMPLIANT (strong). Required non-empty `type`, mapping-shape guards, legacy-`metric` guard — all fail loud at the fixture-parser boundary.
- **#14 state-cleanup ordering** — N/A. No one-shot queue/buffer side effect.

No rule violations across the changed `.py` files.

### Observations (≥5)

- **[VERIFIED] Fail-loud validation is exhaustive** — `_hydrate_encounter` rejects non-dict (`scene_harness.py:511-514`), legacy `metric` (516-521), missing/blank `type` (523-527), non-mapping metric override (530-534); pydantic errors wrapped at 585-588. Evidence: all six paranoid edge tests pass. Complies with CLAUDE.md "No Silent Fallbacks".
- **[VERIFIED] Backward compatibility intact** — `test_canonical_fixtures_still_hydrate_with_encounter_implementation` proves the 3 no-encounter canonical fixtures stay `encounter=None` and `combat_brawl_wasteland` now hydrates `combat`. The optional-block gate `if "encounter" in data and data.get("encounter") is not None` matches the proven 50-20 scenario_state idiom.
- **[VERIFIED] End-to-end wiring** — `snapshot.encounter` consumed by the live turn handler (evidence cited above); `test_dev_scene_route_persists_encounter_end_to_end` proves the SqliteStore round-trip preserves `encounter_type` + per-metric `threshold` override.
- **[LOW][SILENT] Typo'd/unknown keys inside a metric override are silently dropped** — `_threshold` reads only `override.get("threshold", 10)`, so `player_metric: {threshld: 25}` silently yields the default 10 (`scene_harness.py:535`). Brushes "No Silent Fallbacks", but **consistent with the established sibling convention**: `_hydrate_scenario_state` cherry-picks keys identically and `test_unknown_top_level_fields_are_ignored` documents unknown-field tolerance as intended hydrator behavior. Downgraded to LOW with that rationale (a different, tested project convention explicitly contradicts treating this as a violation). Non-blocking; recorded as a delivery finding for fixture-author ergonomics.
- **[LOW][TEST] `test_encounter_empty_type_raises_FixtureValidationError` omits a message assertion** — weaker than its message-asserting missing-type sibling, though it exercises the same `not encounter_type.strip()` guard branch. Non-blocking.
- **[VERIFIED] threshold pydantic coercion is acceptable** — `threshold: "25"` lax-coerces to 25 via pydantic; consistent with `_hydrate_npc`'s documented Disposition int-coercion. Genuinely invalid types (`[1]`) hit the wrapped `ValidationError → FixtureValidationError` path.

### Devil's Advocate

Argue this code is broken. A malicious or careless fixture author is the only untrusted actor here (the harness is dev-gated, `DEV_SCENES=1`), which already bounds blast radius — but assume the worst. Could a crafted `encounter:` block crash the server rather than 422? Walked every shape: `encounter: {}` → `type` is None → FixtureValidationError; `encounter: []` / `encounter: "x"` → non-dict guard; `type: 123` → `not isinstance(str)`; `type: "   "` → `not strip()`; `player_metric: 25` → non-mapping override guard; `player_metric: {threshold: null}` → pydantic rejects `None` for `int` → wrapped FixtureValidationError; `metric:` present → explicit legacy guard. Every adversarial shape lands as a 422, none as a 500 or an unhandled traceback. Could a confused author be silently misled? Yes, narrowly: a `threshld` typo in a metric override yields the default 10 with no warning (the [LOW][SILENT] finding) — but this matches a tested, documented hydrator-wide convention, so it is a known ergonomic edge, not a regression. Could persistence corrupt the encounter? The end-to-end test loads it back through SqliteStore and asserts `encounter_type` + both thresholds survive — round-trip proven. Could it break a live game? The turn handler only engages confrontation when `encounter is not None and not encounter.resolved`; a fixture-armed encounter starts unresolved with `current=0`, so the engine engages exactly as a runtime-armed one would, resolving when `current >= threshold` (`beat_kinds.py:745,750`). The one substantive limitation — fixture encounters carry generic `name="player"/"opponent"` and no genre `ConfrontationDef` semantics — is real, but it is explicitly documented (Architect Resolution D) and the per-metric override is precisely the calibration knob ADR-093 needs. No latent crash, no data loss, no security exposure (dev-gated, no injection surface — `yaml.safe_load` upstream, no eval/format-string-on-input). The skeptical read finds sharp edges, not breakage.

**Conclusion:** No Critical or High issues. Three LOW non-blocking observations. Implementation is correct, well-tested, wired end-to-end, and rule-compliant.

**Handoff:** To SM for finish-story.

## Delivery Findings

<!-- Append-only. Each agent writes under its own subheading. -->

### TEA (test design)
- **Question** (non-blocking): AC-6 (HTTP endpoint-level wiring — `POST /dev/scene/combat_brawl_wasteland` returns the encounter in the persisted snapshot) has no test in the hydrator unit suite. It belongs with the GREEN route wire-up, not the pure hydrator. Affects `sidequest-server/sidequest/server/scene_harness_router.py` (Dev should add an endpoint-level assertion there, or confirm the existing `tests/server/test_scene_harness.py` already covers snapshot round-trip). *Found by TEA during test design.*
- **Gap** (non-blocking): No `sprint/context/context-story-50-21.md` or `context-epic-50.md` exists — epic 50 carries zero per-story context docs (session-file-driven by convention; 50-9/50-12/50-13/50-25 all shipped this way). The on-activation `pf validate context-story` command has also drifted (validator no longer accepts that name). Not a setup failure — flagging so the gate-recovery path isn't triggered spuriously. Affects the TEA/Dev on-activation context-gate step. *Found by TEA during test design.*
- **Improvement** (non-blocking): The required-non-empty-string validation pattern (`not isinstance(x, str) or not x.strip()` → `FixtureValidationError`) is now repeated 3× in `scene_harness.py` (genre, world, encounter_type) and will recur for future required string blocks. A shared `_validate_required_string(key, value, fixture_name)` helper would consolidate it. Deferred out of 50-21 scope — the genre/world copies are pre-existing untouched code. Affects `sidequest-server/sidequest/game/scene_harness.py` (future cleanup story, not this one). *Found by TEA during test verification.*

### Dev (implementation)
- **Improvement** (non-blocking): `_hydrate_encounter()` deliberately does not emit OTEL spans, matching its sibling helpers (`_hydrate_character`, `_hydrate_npc`, `_hydrate_scenario_state`) — the scene harness is dev-gated one-shot fixture loading, not a runtime subsystem decision, and the OTEL load/hydrate/persist spans already exist at the route layer (`test_scene_harness_emits_*_span`). If Wave 2 wants per-encounter setup telemetry, that belongs in the encounter engine's runtime beat path, not the fixture hydrator. Affects `sidequest-server/sidequest/game/scene_harness.py` (no change needed; noted so Reviewer/Architect can confirm the OTEL-principle judgment). *Found by Dev during implementation.*
- **Resolved** (non-blocking): TEA's AC-6 Question is closed — added `test_dev_scene_route_persists_encounter_end_to_end` rather than relying on transitive coverage; the route is a thin wrapper but an explicit AC deserves an explicit wire. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): A typo'd or unknown key inside a per-metric override is silently dropped — `player_metric: {threshld: 25}` yields the default threshold 10 with no error, because `_threshold` reads only `override.get("threshold", ...)`. Consistent with the established hydrator convention (`test_unknown_top_level_fields_are_ignored`; `_hydrate_scenario_state` cherry-picks identically) so it is LOW/non-blocking, but a future ergonomics pass could validate the override mapping's keys against the EncounterMetric field set to fail loud on typos. Affects `sidequest-server/sidequest/game/scene_harness.py` (`_hydrate_encounter._threshold`). *Found by Reviewer during code review.*
- Otherwise no upstream findings — implementation correct, rule-compliant, wired end-to-end, no Critical/High issues.

## Design Deviations

### TEA (test design)
- **Fixture YAML key is `type:`, mapped to `StructuredEncounter.encounter_type`**
  - Spec source: session file AC-2 and AC-4
  - Spec text: AC-2 "The `encounter_type` field is required when the `encounter:` block is present"; AC-4 "The existing `combat_brawl_wasteland.yaml` fixture (lines 66-68: `encounter: type: combat`)"
  - Implementation: tests author the fixture key as `type:` (short form) and assert it binds to `encounter_type`; the missing-type error is asserted to mention "type"
  - Rationale: AC-4 cites the canonical fixture's `type: combat` and AC-8 forbids editing canonical fixtures, so the hydrator must map `type` → `encounter_type`. AC-2's prose names the model field, not the YAML key.
  - Severity: minor
  - Forward impact: Dev must map `type` → `encounter_type`; Architect to confirm the key name in SPEC-CHECK
- **Per-metric override keyed on model field names (`player_metric:`/`opponent_metric:` → nested `threshold:`)**
  - Spec source: session file AC-3
  - Spec text: "Optional YAML override per metric allows fixture authors to set custom thresholds"
  - Implementation: override tests use `player_metric:`/`opponent_metric:` mappings with a nested `threshold:` key
  - Rationale: AC-3 does not specify the override shape; this mirrors 50-20's scenario_state hydrator, which keyed on model field names. Consistent precedent beats inventing a new convention.
  - Severity: minor
  - Forward impact: if Architect prefers a different override key shape, GREEN adjusts these two tests (`test_encounter_custom_metric_threshold`, `test_encounter_metric_override_any_yaml_key_order`)
- **EncounterMetric `name` asserted as non-empty string, not a specific value**
  - Spec source: session file AC-3
  - Spec text: "Both metrics start with: `current: 0` `starting: 0` `threshold: 10`" (no `name` specified)
  - Implementation: `test_encounter_default_metrics_initialized` asserts `metric.name` is a non-empty string rather than a fixed label
  - Rationale: `EncounterMetric.name` is a required non-blank field, but AC-3 is silent on its value; over-specifying would force a label choice that belongs to Dev/Architect
  - Severity: minor
  - Forward impact: none — Dev picks the metric label freely
- **Added legacy-`metric:` rejection test beyond the enumerated ACs**
  - Spec source: session file ACs (none mention the legacy single-dial `metric` key) + SOUL/CLAUDE "No Silent Fallbacks"
  - Spec text: n/a (no AC); StructuredEncounter has an explicit `_reject_legacy_metric` model_validator
  - Implementation: `test_encounter_legacy_metric_key_raises_FixtureValidationError` asserts a `metric:` key inside the encounter block surfaces as `FixtureValidationError`, never a raw pydantic/ValueError leak
  - Rationale: every other block in the hydrator (character, npcs, scenario_state) re-wraps pydantic errors at the module boundary so the HTTP 404/422 mapping can classify them; the model already guards legacy metric, the hydrator must not let that guard leak un-wrapped
  - Severity: minor
  - Forward impact: constrains Dev to wrap the legacy-metric error like every sibling block — consistent with the established boundary contract, low risk

### Dev (implementation)
- No deviations from spec. Implementation matches every test TEA wrote and every interpretation TEA pre-logged above. Choices made within TEA's documented latitude (not deviations, noted for Architect SPEC-CHECK): metric labels are the literal strings `"player"`/`"opponent"` (AC-3 silent on `EncounterMetric.name`); the default threshold is a named module constant `_DEFAULT_METRIC_THRESHOLD = 10` (AC-3 value); the legacy `metric` key is rejected by an explicit up-front guard with a clear message rather than relying on `StructuredEncounter._reject_legacy_metric` to raise (cleaner author-facing error, same outcome). The SM-flagged open question — whether `threshold=10` collides with ADR-033 confrontation-engine defaults — remains for Architect to confirm in SPEC-CHECK.

### Reviewer (audit)
- **TEA: Fixture key `type:` → `encounter_type`** → ✓ ACCEPTED by Reviewer: AC-4 cites the frozen canonical fixture's `type: combat` and AC-8 forbids editing it — this is the only viable reading. Architect confirmed in spec-check (Resolution C).
- **TEA: Per-metric override keyed on `player_metric:`/`opponent_metric:` → nested `threshold:`** → ✓ ACCEPTED by Reviewer: mirrors the proven 50-20 scenario_state model-field-name keying; AC-3 explicitly scopes the override to thresholds. Architect confirmed (Resolution C). Restraint, not scope creep.
- **TEA: `EncounterMetric.name` asserted non-empty, not fixed** → ✓ ACCEPTED by Reviewer: AC-3 is silent on the label; Dev's `"player"`/`"opponent"` satisfies the non-blank constraint without over-specifying.
- **TEA: Added legacy-`metric:` rejection test beyond enumerated ACs** → ✓ ACCEPTED by Reviewer: enforces the module-boundary re-wrap contract every sibling block obeys; verified — the explicit guard at `scene_harness.py:516-521` fires before pydantic, no un-wrapped leak.
- **Dev: No deviations; choices within TEA latitude** → ✓ ACCEPTED by Reviewer: implementation matches every test verbatim; the `threshold=10` open question was resolved by Architect with evidence (ADR-033's own standoff example uses 10; runtime pulls thresholds from genre ConfrontationDefs, not a constant; zero materialization coupling).
- No undocumented spec deviations found. The fixture-vs-runtime fidelity gap (generic metric names, no genre ConfrontationDef) is already captured by Architect Resolution D as a deferred forward-impact note for the ADR-093 author — correctly documented, nothing slipped through.

### Architect (reconcile)

**Manifest verification.** Cross-checked every logged deviation against the code and the spec (session file — epic 50 carries no context-story/context-epic docs by established convention, so the session ACs are the authoritative spec):

- **TEA #1 (type→encounter_type):** all 6 fields present; spec text accurately quotes session AC-2/AC-4; implementation description matches `scene_harness.py:523` (`raw.get("type")`). Accurate.
- **TEA #2 (override key shape):** 6 fields; spec text accurate; matches `_threshold` reading `player_metric`/`opponent_metric` → nested `threshold` (`scene_harness.py:529-535`). Accurate.
- **TEA #3 (metric name non-empty):** 6 fields; AC-3 is genuinely silent on `EncounterMetric.name`; matches Dev's `name="player"/"opponent"` literals. Accurate.
- **TEA #4 (legacy-metric test beyond ACs):** 6 fields; the explicit guard exists at `scene_harness.py:516-521` and fires before pydantic. Accurate.
- **Dev (no deviations):** valid per deviation-format ("No deviations from spec." sentinel). Confirmed — implementation matches every TEA test verbatim; the three within-latitude choices (metric labels, `_DEFAULT_METRIC_THRESHOLD` constant, explicit legacy guard) are correctly classified as non-deviations.
- **Reviewer (audit):** every upstream entry stamped ACCEPTED with line-level rationale; no FLAGGED entries.

No field corrections required — all entries are accurate, self-contained, and 6-field complete.

**One scope clarification recorded here so the boss audits from the session file alone:**
- **AC-6 test scope is narrower than its literal prose, by design.** AC-6 text: *"`POST /dev/scene/combat_brawl_wasteland` returns a slug that can reconnect via `GET /connect/{slug}` and receive opening narration. The response includes the encounter in the GameSnapshot persisted to the store."* The new `test_dev_scene_route_persists_encounter_end_to_end` proves the **encounter-specific** obligation (encounter persisted + round-tripped through SqliteStore with `encounter_type` and per-metric `threshold` intact). The `GET /connect/{slug}` + opening-narration mechanics are **pre-existing 50-18 infrastructure** already covered green by `test_scene_post_response_body_has_slug_field`, `test_every_canonical_fixture_can_be_loaded_via_endpoint`, et al. — re-testing connect/narration here would duplicate 50-18 coverage and violate minimalist discipline. Severity: trivial. Forward impact: none — AC-6's encounter delta is fully covered; the connect/narration clause is satisfied transitively by 50-18 and is manual-verification guidance ("Verifiable via the UI `?scene=` flow"), not a 50-21 unit-test obligation.

**AC deferral check:** no ACs were deferred or descoped — all 8 marked DONE by Dev and confirmed by Reviewer. Conditional reconcile step is a no-op.

**Manifest status:** Complete and accurate. Story 50-21 is clean for SM finish.