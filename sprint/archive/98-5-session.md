---
story_id: "98-5"
jira_key: ""
epic: "98"
workflow: "tdd"
---
# Story 98-5: S2 Server — inter-system jump adjudication via SWN ruleset seam (ADR-117), default cost OTEL-logged

## Story Details
- **ID:** 98-5
- **Jira Key:** N/A (personal project)
- **Workflow:** tdd
- **Stack Parent:** none (depends on 98-2, same story not a parent)
- **Repos:** server
- **Points:** 5
- **Priority:** p3

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-10T02:06:05Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T00:59:30Z | 2026-06-10T00:59:30Z | immediate |
| red | 2026-06-10T00:59:30Z | 2026-06-10T01:28:12Z | 28m 42s |
| green | 2026-06-10T01:28:12Z | 2026-06-10T02:00:49Z | 32m 37s |
| review | 2026-06-10T02:00:49Z | 2026-06-10T02:06:05Z | 5m 16s |
| finish | 2026-06-10T02:06:05Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Question** (blocking): the production *entry point* for an inter-system jump is unspecified — the spec names `movement.py` but `run_movement_dispatch` is room-graph (intra-system) only, and region-mode worlds are deferred to the narration-apply path (`movement.py:83 _is_region_mode_world`). The RED wiring tests pin the span + bound-ruleset contract at the glue seam (`orbital/jump.adjudicate_inter_system_jump`); Dev must additionally **invoke that glue from the live movement/region-mode path** so `jump.adjudicated` fires in real play. Affects `sidequest/agents/subsystems/movement.py` (wire the jump branch + reach the glue). *Found by TEA during test design.*
- **Question** (non-blocking): `drive_rating_min` is in the finalized schema (AC3) but its **gate semantics are undefined** — what happens when the ship's drive rating is below a route's `drive_rating_min`? The tests assert the field is typed/carried but do not pin failure behavior (avoiding handcuffing). Dev/SWN must define it (block the jump? extra fuel/time? hazard bump?) and add coverage. Affects `sidequest/game/ruleset/swn.py` (`adjudicate_jump`). *Found by TEA during test design.*
- **Improvement** (non-blocking): suggested homes for the net-new surface — result type `JumpAdjudication` in `game/ruleset/resolution.py`; span helpers in `telemetry/spans/jump.py`; route-resolution + glue in `orbital/jump.py` (parallels `orbital/course.py`). These are precedent-matched but Dev-relocatable; if relocated, update the RED test imports. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): no per-ship spike-drive-rating entity exists in the engine (`grep drive_rating` → only the new `Route` field). The production jump caller passes a placeholder `_DEFAULT_SHIP_DRIVE_RATING = 1`. A future story should add a ship/chassis drive-rating attribute and source it at the `narration_apply` call site. Affects `sidequest/server/narration_apply.py` (`_DEFAULT_SHIP_DRIVE_RATING`) + a new ship-drive model. *Found by Dev during implementation.*
- **Improvement** (non-blocking): the SWN spike-drive jump model is inherited by the whole SWN family (CWN/WWN/AWN subclass `SwnRulesetModule`), so a hypothetical orbital CWN/WWN world would get SWN's jump cost. Harmless today (the jump path is gated to orbital region-mode worlds, which bind SWN/space_opera; non-orbital worlds never reach it), but if a non-space SWN-family ruleset should *not* offer inter-system jumps, override `adjudicate_jump` to fail loud there. Affects `sidequest/game/ruleset/{cwn,wwn,awn}.py`. *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): the adjudicated jump cost (fuel/transit) is OTEL-logged but not *applied* — `_adjudicate_inter_system_jump_for_advance` discards the returned `JumpAdjudication`, so no fuel pool depletes and no clock advances. Scope-appropriate (no fuel substrate exists; AC4 forbids the ADR-130 clock), but the follow-up ship-resource story must consume the result. Affects `sidequest/server/narration_apply.py` (apply the returned cost once a fuel/jump-clock model exists). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `resolve_route_for_jump` re-validates all routes and WARNs per jump rather than once at pack load; consider a load-time route-anomaly validator so the WARN fires once and duplicate-edge routes (currently last-wins) are surfaced. Affects `sidequest/orbital/jump.py` + a pack-load validator. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **`hazard` pinned as a new typed field rather than reusing `danger`**
  - Spec source: context-story-98-5.md AC3 / epic spec §3 (line 58–59)
  - Spec text: "`hazard` (reuse existing `danger` if preferred — Dev/SWN call)"
  - Implementation: tests require a new typed `Route.hazard` field, distinct from the existing narrative `danger`
  - Rationale: `danger` is free-text narrative flavor ("lethal") that AC3 must preserve on the Black Door; overloading it to drive jump crunch would let narrative descriptors silently change mechanics. Separate fields keep flavor and crunch independent.
  - Severity: minor
  - Forward impact: C2 (98-4) authors `hazard` (mechanical) and may keep `danger` (narrative) on the same route; Dev may overrule and reuse `danger` — if so, update `test_route_jump_fields_are_typed_not_extras_bag` + `test_black_door_...`.
- **Jump seam shapes pinned in tests (the spec left them to Dev)**
  - Spec source: context-story-98-5.md "Technical Guardrails" / epic spec §4 S2
  - Spec text: "Finalize the additive `routes` field names … here … (`jump_fuel`, `transit_days`, `drive_rating_min`, …)"; method/result names unspecified
  - Implementation: tests pin `RulesetModule.adjudicate_jump(*, route, drive_rating, rng) -> JumpAdjudication`, the `jump.adjudicated`/`jump.default_cost` spans, and `orbital/jump.{resolve_route_for_jump,adjudicate_inter_system_jump}`
  - Rationale: TDD RED needs concrete callable contracts; shapes mirror existing precedent (`ship_attack_params`, `system_resolve.py`, `course.py`) to minimize Dev friction
  - Severity: minor
  - Forward impact: Dev may rename/relocate; tests are the contract and travel with the rename (see Delivery Findings Improvement).
- **SWN default jump arithmetic not pinned (partial AC2 coverage by design)**
  - Spec source: context-story-98-5.md AC2
  - Spec text: "the ruleset computes a default jump cost from the SWN drive model; this default is explicit and OTEL-logged"
  - Implementation: the default test asserts `source == "ruleset_default"`, `fuel_spent >= 1`, `transit_days >= 1`, `hazard_roll` is int — NOT exact SWN constants
  - Rationale: pinning faithful-SRD drive numbers would handcuff Dev and be brittle; the AC requires *explicit + non-silent + logged*, which positivity + source-label + span assert
  - Severity: minor
  - Forward impact: Dev owns the exact SWN drive formula; if a calibration test is later wanted, add it in GREEN.
- **Wiring tested at the glue seam, not full movement dispatch**
  - Spec source: epic spec §7 (verification spine) — "S2 asserts jump adjudication is reached from movement.py"
  - Spec text: "jump adjudication is reached from `movement.py`, not just unit-testable in isolation"
  - Implementation: the wiring test drives `orbital/jump.adjudicate_inter_system_jump` (the production glue) and asserts the span + bound-ruleset routing, rather than constructing a full `run_movement_dispatch` jump
  - Rationale: the movement entry point for inter-system jump does not exist yet and its shape is undefined (see blocking Delivery Finding); a brittle dispatch harness would fail even on correct implementation wired elsewhere
  - Severity: minor
  - Forward impact: Dev must wire the glue into the live movement path; reviewer should confirm the glue is reached from production (not only the wiring test).

### Dev (implementation)
- **Production jump wired into the narration_apply orbital region-advance seam, not `movement.py`**
  - Spec source: context-story-98-5.md "Key files" (line 29) + Assumptions (line 92)
  - Spec text: "`agents/subsystems/movement.py` — where inter-system jump adjudication is reached from a production path" / "If current/target region is not reachable at the `movement.py` seam, log a Design Deviation."
  - Implementation: the live caller is `_adjudicate_inter_system_jump_for_advance` invoked from `server/narration_apply.py` at the orbital region-advance branch (right after `bind_region_scope`, ~line 3658), gated to orbital region-mode worlds (`orbital_content is not None`) on a real cartography adjacency. `movement.py`'s region-mode branch *defers* to narration_apply (movement.py:141-161) — it never resolves the target region, so the actual inter-system move (current_region advance, region id == star-system id) materializes in narration_apply. That is the only production point where from/to are both known.
  - Rationale: spec line 92 explicitly sanctions this deviation ("If current/target region is not reachable at the `movement.py` seam, log a Design Deviation"). Wiring at movement.py would adjudicate a jump whose target isn't resolved yet.
  - Severity: minor
  - Forward impact: reviewer should confirm the glue is reached from `narration_apply` (not only the wiring test); a future discrete jump-intent handler could relocate the call but the glue contract (`adjudicate_inter_system_jump`) is stable.
- **`drive_rating` sourced from a placeholder default (1), not a per-ship spike-drive**
  - Spec source: context-story-98-5.md Assumptions (line 93) + TEA Delivery Finding #2 (non-blocking)
  - Spec text: "the SWN module exposes (or can expose) a drive/fuel/transit computation suitable for inter-system jumps" / TEA: "`drive_rating_min` … gate semantics are undefined"
  - Implementation: no ship/chassis drive-rating field exists anywhere in the codebase (`grep drive_rating` → only the new `Route` field). The production caller passes `_DEFAULT_SHIP_DRIVE_RATING = 1` (SWN starter-ship rating) with a comment marking it a placeholder until a per-ship drive subsystem lands.
  - Rationale: building a ship-drive subsystem to source the rating is out of this 5-pt story's scope; the rating only feeds the `drive_rating_min` strain gate (extra fuel, never a block), so a placeholder is safe and non-silent (documented + logged).
  - Severity: minor
  - Forward impact: when a ship-drive entity is added, replace `_DEFAULT_SHIP_DRIVE_RATING` with the real per-ship rating at the narration_apply call site; no change to the ruleset/glue contracts.
- **`drive_rating_min` gate defined as a strained jump (+1 fuel), not a block (TEA finding #2 resolved)**
  - Spec source: TEA Delivery Finding #2 (non-blocking) — "Dev/SWN must define it … and add coverage."
  - Spec text: "what happens when the ship's drive rating is below a route's `drive_rating_min`?"
  - Implementation: a ship below `drive_rating_min` still makes the jump (a bare adjacency is always navigable) but burns one extra fuel load (`UNDERRATED_DRIVE_FUEL_PENALTY = 1`). Covered by the GREEN-added `test_swn_underrated_drive_makes_strained_jump_costs_extra_fuel`.
  - Rationale: a hard block would make an authored route un-navigable, contradicting epic 98 §3 ("a bare adjacency is navigable"); a fuel penalty gives the field mechanical teeth without blocking travel (No Silent Fallbacks — the field is consumed, not dead).
  - Severity: minor
  - Forward impact: C2 (98-4) authors `drive_rating_min` knowing it costs extra fuel below threshold, not a block; SWN may later add a hazard bump if calibration wants one.
- **AC3 "documented for C2" satisfied via in-code `Field(description=...)`, no separate markdown doc**
  - Spec source: context-story-98-5.md AC3 (line 78-81) / Technical Guardrails (line 36)
  - Spec text: "finalized and documented so 98-4 (C2) can author against them … referenced by a doc the C2 story can cite."
  - Implementation: each new `Route` jump field carries a `Field(description=...)` documenting its meaning; `test_route_jump_fields_are_documented_for_c2` pins this. No separate schema markdown was authored.
  - Rationale: the test docstring defines the doc as "documented *in code*, citable by the C2 authors"; the in-code descriptions are the single source of truth C2 cites, avoiding a drift-prone duplicate markdown.
  - Severity: minor
  - Forward impact: C2 (98-4) cites `Route.model_fields[...].description` (or the `world.py` Route class) as the authoring schema.

### Reviewer (audit)
TEA deviations:
- **`hazard` pinned as a new typed field rather than reusing `danger`** → ✓ ACCEPTED by Reviewer: keeping mechanical crunch (`hazard`) separate from narrative flavor (`danger`) is the correct reading of SOUL.md "flavor must never silently drive mechanics"; the Black Door test proves both coexist.
- **Jump seam shapes pinned in tests (the spec left them to Dev)** → ✓ ACCEPTED by Reviewer: shapes mirror `ship_attack_params`/`course.py` precedent; the implementation matches the pinned contracts exactly.
- **SWN default jump arithmetic not pinned (partial AC2 coverage by design)** → ✓ ACCEPTED by Reviewer: AC2 requires explicit+non-silent+logged, which the source-label + positivity + span assertions cover; exact SRD numbers would be brittle.
- **Wiring tested at the glue seam, not full movement dispatch** → ✓ ACCEPTED by Reviewer: Dev satisfied the residual obligation — the glue now has a real production caller in `narration_apply`'s orbital region-advance seam (see Dev deviation below); the glue contract is OTEL+registry-spy tested.

Dev deviations:
- **Production jump wired into the narration_apply orbital region-advance seam, not `movement.py`** → ✓ ACCEPTED by Reviewer: spec line 92 explicitly sanctions this deviation ("If current/target region is not reachable at the `movement.py` seam, log a Design Deviation"). `movement.py`'s region-mode branch demonstrably defers to narration_apply (movement.py:141-161) and never resolves the target region; narration_apply's `current_region` advance is the only production point where from/to are both known. Verified the glue is reached from production, not only the wiring test.
- **`drive_rating` sourced from a placeholder default (1), not a per-ship spike-drive** → ✓ ACCEPTED by Reviewer: confirmed no `drive_rating`/ship-drive entity exists in the codebase; the placeholder is loud (named constant + comment + Gap finding), feeds only the strain gate, and is safe. A future ship-resource story replaces it.
- **`drive_rating_min` gate defined as a strained jump (+1 fuel), not a block** → ✓ ACCEPTED by Reviewer: a hard block would contradict epic 98 §3 ("a bare adjacency is navigable"); the fuel penalty gives the field mechanical teeth (No dead field) without blocking travel, and is covered by the GREEN-added strain test.
- **AC3 "documented for C2" satisfied via in-code `Field(description=...)`, no separate markdown** → ✓ ACCEPTED by Reviewer: the AC3 test defines the doc as the in-code descriptions; a duplicate markdown would drift. C2 cites the `Route` class.

No undocumented deviations found — the implementation matches the pinned test contracts and every divergence from the spec letter is logged.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Net-new mechanical subsystem (inter-system jump adjudication) — five ACs, all behavioral.

**Test Files:**
- `tests/game/ruleset/test_98_5_jump_adjudication.py` — ruleset seam, schema, route resolution, spans, scale-separation (13 tests)
- `tests/agents/subsystems/test_98_5_jump_wiring.py` — production-glue wiring: span fires + bound-ruleset routing (3 tests)

**Tests Written:** 16 tests covering 5 ACs + the CLAUDE.md wiring mandate
**Status:** RED — verified via direct `pytest -n0` (16 failed, 0.12s, no DB touched). Each fails for the correct missing-API reason: no `adjudicate_jump`, no `sidequest.orbital.jump`, no `sidequest.telemetry.spans.jump`, and `jump_fuel`/`hazard` not yet typed `Route` fields. (testing-runner skipped to avoid the known `.session` cache-clobber; direct run is the RED evidence.)

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| AC1 jump via bound ruleset, reads routes | `test_swn_adjudicate_jump_reads_authored_route_via_bound_module`, `test_native_ruleset_has_no_jump_adjudication`, `test_resolve_route_for_jump_returns_authored_route_for_real_edge`, wiring `…routes_through_bound_ruleset_not_hardcoded` | failing |
| AC2 explicit logged default + anomaly | `test_swn_adjudicate_jump_default_is_explicit_and_nonsilent`, `test_resolve_route_for_jump_none_for_unrouted_adjacency`, `test_anomalous_route_endpoints_not_adjacent_dropped_with_warn`, `test_emit_jump_default_cost_span_marks_ruleset_default`, wiring `…unrouted_edge_also_fires_default_cost_span` | failing |
| AC3 routes schema typed + documented; Black Door intact | `test_route_jump_fields_are_typed_not_extras_bag`, `test_route_jump_fields_are_documented_for_c2`, `test_route_jump_fields_are_optional_and_default_none`, `test_black_door_narrative_fields_preserved_and_distinct_from_hazard` | failing |
| AC4 intra-system course untouched/separate | `test_adjudicate_jump_does_not_invoke_intra_system_course_model` | failing |
| AC5 OTEL span per jump (5 attrs) | `test_emit_jump_adjudicated_span_carries_all_five_attributes`, wiring `…production_glue_fires_adjudicated_span` | failing |

### Rule Coverage (python lang-review)

| Rule | Test(s) | Status |
|------|---------|--------|
| #4 logging correctness (WARN, not silent) | `test_anomalous_route_endpoints_not_adjacent_dropped_with_warn` | failing |
| #1 / No Silent Fallbacks (explicit positive default + span) | `test_swn_adjudicate_jump_default_is_explicit_and_nonsilent`, `test_emit_jump_default_cost_span_marks_ruleset_default` | failing |
| #3 typed boundaries (typed schema, not extras bag) | `test_route_jump_fields_are_typed_not_extras_bag` | failing |
| #6 test quality (self-check) | all tests assert specific values; no vacuous/`assert True`/bare-truthy | n/a |

**Rules checked:** 4 of 13 lang-review rules apply (telemetry/ruleset/pydantic surface — no I/O, deserialization, async, or resource-handling in this story).
**Self-check:** 0 vacuous tests (verified — every test asserts concrete values; the anomaly test asserts a non-empty WARN with the offending id).

**Handoff:** To Dev (Inigo Montoya) for GREEN. Read the blocking Delivery Finding first — the production movement entry for inter-system jump must be wired, not just the glue unit.
## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/game/ruleset/resolution.py` — `JumpAdjudication` frozen result type (5 fields: fuel_spent, transit_days, hazard, hazard_roll, source).
- `sidequest/game/ruleset/base.py` — default `adjudicate_jump` fails loud (`{slug} ruleset has no inter-system jump adjudication`); mirrors `ship_attack_params`.
- `sidequest/game/ruleset/swn.py` — SWN spike-drive `adjudicate_jump` (route fields → cost, else explicit default labelled `ruleset_default`; `drive_rating_min` strain = +1 fuel). SRD constants `SPIKE_TRANSIT_DAYS=6`, `SPIKE_FUEL_PER_JUMP=1`.
- `sidequest/genre/models/world.py` — `Route` gains typed+described optional fields `jump_fuel`, `transit_days`, `drive_rating_min`, `hazard` (the AC3 schema C2/98-4 authors against).
- `sidequest/telemetry/spans/jump.py` (new) — `jump.adjudicated` (AC5, 5 attrs) + `jump.default_cost` (AC2, `source=ruleset_default`); both FLAT_ONLY.
- `sidequest/telemetry/spans/__init__.py` — re-export `jump` domain.
- `sidequest/orbital/jump.py` (new) — `resolve_route_for_jump` (undirected match, anomaly drop+WARN) + `adjudicate_inter_system_jump` glue (routes through bound ruleset registry, emits spans).
- `sidequest/server/narration_apply.py` — `_adjudicate_inter_system_jump_for_advance` helper + call from the orbital region-advance seam (the live inter-system move; movement.py defers region-mode here). Gated to orbital region-mode worlds on a real cartography adjacency.
- `tests/game/ruleset/test_98_5_jump_adjudication.py` — GREEN-added `test_swn_underrated_drive_makes_strained_jump_costs_extra_fuel` (TEA finding #2 coverage); plus linter import-sort.
- `tests/agents/subsystems/test_98_5_jump_wiring.py` — linter import-sort only.

**Tests:** 17/17 jump tests passing (16 TEA + 1 Dev-added strain test) + routing-completeness GREEN. Targeted suites: ruleset/telemetry/orbital 969 passed; region/movement 482 passed.
**Full suite:** 10012 passed, 7 failed — ALL 7 pre-existing/environmental, none related to this diff: 6 are parallel-`-n auto` teardown flakiness (`PythonFinalizationError: cannot join thread`, all pass in isolation — lore_rag ×3, chargen_hp_leak ×2, culture_context ×1); 1 is `test_api_contract_aside` asserting a missing `docs/api-contract.md` in this oq-2 checkout. None import any changed module.
**Lint/format/types:** ruff check clean, ruff format applied, pyright 0 errors on changed files (narration_apply's 36 pyright errors are all pre-existing, outside my added regions).
**Branch:** feat/98-5-jump-adjudication-swn-seam (pushed)

**AC coverage:** AC1 (bound-ruleset adjudication reading routes) ✓ · AC2 (explicit OTEL-logged default + anomaly WARN) ✓ · AC3 (typed+described `Route` schema, Black Door narrative fields intact) ✓ · AC4 (intra-system course model untouched — adjudicate_jump never calls `compute_eta_and_dv`) ✓ · AC5 (per-jump span, 5 attrs) ✓ · wiring (glue reached from `narration_apply` orbital region-advance, OTEL+registry-spy tested) ✓.

**Handoff:** To next phase (verify/review — Westley). Reviewer: confirm the glue is reached from the `narration_apply` orbital region-advance seam (production), not only the wiring test; and review the 4 Dev Design Deviations (production wiring location, placeholder drive_rating, drive_rating_min strain semantics, AC3 in-code doc).
---
## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (lint/format/pyright/tests all PASS, 0 smells) | confirmed 0, dismissed 0, deferred 0 |
| 2 | reviewer-edge-hunter | Yes | Skipped | disabled | Disabled via settings — Reviewer covered edges manually |
| 3 | reviewer-silent-failure-hunter | Yes | Skipped | disabled | Disabled via settings — Reviewer covered silent-failure manually |
| 4 | reviewer-test-analyzer | Yes | Skipped | disabled | Disabled via settings — Reviewer covered test quality manually |
| 5 | reviewer-comment-analyzer | Yes | Skipped | disabled | Disabled via settings — Reviewer covered docs manually |
| 6 | reviewer-type-design | Yes | Skipped | disabled | Disabled via settings — Reviewer covered type design manually |
| 7 | reviewer-security | Yes | Skipped | disabled | Disabled via settings — Reviewer covered security manually |
| 8 | reviewer-simplifier | Yes | Skipped | disabled | Disabled via settings — Reviewer covered simplification manually |
| 9 | reviewer-rule-checker | Yes | Skipped | disabled | Disabled via settings — Reviewer ran lang-review rules manually |

**All received:** Yes (1 enabled subagent returned clean; 8 disabled via `workflow.reviewer_subagents`, covered by Reviewer directly)
**Total findings:** 0 confirmed blocking, 4 non-blocking observations, 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

Only `reviewer-preflight` is enabled in `workflow.reviewer_subagents`; the other 8 specialists are disabled, so I performed their analyses directly against the diff and the lang-review/python.md checklist. Preflight returned fully clean (ruff check PASS, ruff format PASS, pyright 0 errors, 19/19 story tests, 0 code smells). I separately confirmed the full unit suite's 7 failures (per Dev assessment) are pre-existing/environmental, none touching changed modules.

**Observations (≥5):**
- [VERIFIED] **AC4 scale separation holds** — `orbital/jump.py` imports only ruleset + world models + jump spans; it never references `orbital/course.py`/`compute_eta_and_dv`. Evidence: `grep course sidequest/orbital/jump.py` matches only the docstring disclaimer; `test_adjudicate_jump_does_not_invoke_intra_system_course_model` monkeypatches `compute_eta_and_dv` and asserts zero calls. The two movement scales are genuinely distinct code paths.
- [VERIFIED] **No Silent Fallbacks across the seam** — base `adjudicate_jump` raises `NotImplementedError(f"{self.slug} ruleset has no inter-system jump adjudication")` (base.py, slug in message); an unrouted edge returns an explicit positive default labelled `source="ruleset_default"` (swn.py) and fires its own `jump.default_cost` span (jump.py). The production caller catches ONLY `NotImplementedError` (no-jump-model ruleset → observable loud-skip via `logger.info jump.skip_no_ruleset_model`), while `UnknownRulesetError` from `get_ruleset_module` is left to propagate — an unregistered ruleset is a config bug that correctly fails loud, not a skip. Evidence: narration_apply.py `_adjudicate_inter_system_jump_for_advance` try/except scope.
- [VERIFIED] **`hazard` (crunch) is separate from `danger` (flavor)** [TYPE][DOC] — `Route.hazard: str | None` is a new typed `Field(description=...)`, distinct from the untouched narrative `danger`; `test_black_door_narrative_fields_preserved_and_distinct_from_hazard` asserts both coexist on the Black Door with `hazard is None`. AC3 satisfied; the four new fields are typed, optional (default None), and documented in-code — `test_route_jump_fields_are_documented_for_c2` pins non-empty descriptions for C2/98-4.
- [VERIFIED] **OTEL spans match the ACs** [DOC] — `jump.adjudicated` carries exactly the 5 AC5 attributes (from/to region, fuel_spent, transit_days, hazard_roll); `jump.default_cost` carries `source=ruleset_default` (AC2). Both registered in `FLAT_ONLY_SPANS` and re-exported in `spans/__init__.py`; `test_routing_completeness` is GREEN, so neither span is an un-routed orphan.
- [VERIFIED] **Test quality** [TEST] — 51 assertions across the two test files, all on concrete values (fuel_spent==2/3, source=="route"/"ruleset_default", exact span attrs, `NotImplementedError` message contains "native", anomaly WARN contains "ceron"). Zero vacuous/truthy-only assertions (`grep` for `assert True`/bare-truthy returns none). The Dev-added strain test pins both unstrained (2) and strained (3) fuel.
- [MEDIUM][SIMPLE] **Production result is adjudicated + OTEL-logged but not applied to game state** — `_adjudicate_inter_system_jump_for_advance` discards the returned `JumpAdjudication`; no fuel is deducted and no clock advanced. This is **scope-appropriate**: there is no ship-fuel resource or jump-clock substrate in the engine yet (AC4 explicitly forbids touching the ADR-130 intra-system clock), and this story's ACs are *adjudication + logging*, not application. Dev logged the matching Gap finding. Non-blocking; a future ship-resource story wires application. CONFIRMED as a scoped observation, not a blocker.
- [LOW][EDGE] **Anomaly WARN re-fires on every jump, not once at load** — `resolve_route_for_jump` re-validates all routes per call and WARNs on each anomalous one. Silent for a healthy world; for a world carrying a persistent anomalous route it logs on every jump. Authoring anomalies are bugs meant to be fixed, so real-world spam is low. Non-blocking.
- [LOW][EDGE] **Duplicate routes annotating one edge resolve last-wins silently** — if two `routes` entries match the same endpoint pair, the loop keeps the last without warning. Content-authoring error, low risk. Non-blocking.

[SEC] **Security:** No security surface — no user-input parsing, no SQL/HTML/path/deserialization, no auth/tenant data. Inputs are engine-internal region ids and a typed pydantic `CartographyConfig`. The `random.Random(f"jump:{from}->{to}@{turn}")` seed is deterministic-by-design (ADR-128 resume-safety), not a security RNG — correct. No findings.

**Rule Compliance** — see `### Rule Compliance` below.
**Devil's Advocate** — see `### Devil's Advocate` below.

**Data flow traced:** narrator scene-heading → `_resolve_heading_to_cartography` resolves a known region id → orbital region-mode advance (`current_region` changes) → `_adjudicate_inter_system_jump_for_advance` (gated: orbital_content present + real cartography adjacency + bound ruleset) → `adjudicate_inter_system_jump` resolves the route via registry → `module.adjudicate_jump` computes cost → `jump.adjudicated` (+ `jump.default_cost` if unrouted) span fires. Safe: gated to orbital worlds, self-jump excluded (`current_region != known_region_id`), non-adjacency loud-skips.
**Pattern observed:** glue module mirrors `orbital/course.py`; span module mirrors `telemetry/spans/course.py`; base/override mirrors `ship_attack_params` fail-loud default. Precedent-faithful.
**Error handling:** fail-loud base default; explicit-default for unrouted edges; narrow `NotImplementedError` catch with logging; `UnknownRulesetError` propagates. Null/empty: `from_obj is None` and missing-adjacency both loud-skip; `_prior_region` falsy excluded by guard.

**Handoff:** To SM (Vizzini) for finish-story.

### Rule Compliance

Enumerated against `.pennyfarthing/gates/lang-review/python.md` (13 checks). Applicable rules and every governed instance in the diff:

- **#1 Silent exception swallowing** — One `try/except` in the diff: `_adjudicate_inter_system_jump_for_advance` catches `NotImplementedError` only (specific, not bare), logs `jump.skip_no_ruleset_model` at info before returning. The caught condition (ruleset has no jump model) is an expected, non-error state and the skip is observable. COMPLIANT. (No bare `except`, no `except Exception: pass`, no `suppress()` in the diff.)
- **#2 Mutable default arguments** — No function/method in the diff uses a mutable default. `JumpAdjudication` is a frozen dataclass; new `Route` fields default to `None`/scalars; `_DEFAULT_SHIP_DRIVE_RATING`, `SPIKE_*`, `UNDERRATED_DRIVE_FUEL_PENALTY` are int module constants. COMPLIANT.
- **#3 Type annotations at boundaries** — Every new public function is fully annotated: `resolve_route_for_jump(carto, from_region, to_region) -> Route | None`, `adjudicate_inter_system_jump(*, cartography, from_region, to_region, ruleset, drive_rating, rng) -> JumpAdjudication`, `adjudicate_jump(*, route, drive_rating, rng) -> JumpAdjudication` (base + SWN), `emit_jump_adjudicated`/`emit_jump_default_cost` (all kw-only, typed, `-> None`), `_endpoints_adjacent(carto, a, b) -> bool`, `_adjudicate_inter_system_jump_for_advance(*, ...) -> None`. No `Any`, no untyped `# type: ignore`. COMPLIANT.
- **#4 Logging coverage AND correctness** — `jump.py` and `narration_apply.py` helper use lazy `%`-style args (`logger.warning("jump.route_anomaly route=%r ...", route.name, ...)`, `logger.info("jump.skip_... %r", ...)`), never f-strings. Anomaly path is WARNING (an authoring defect); the no-jump-model and non-adjacency skips are INFO (expected control-flow states). Severity classification correct; no sensitive data logged. COMPLIANT.
- **#5 Path handling** — No filesystem path handling in the diff. N/A.
- **#6 Test quality** — 51 concrete assertions; no `assert True`, no bare-truthy, no assertion-free tests, no unexplained `@pytest.mark.skip`. The two `monkeypatch.setattr` targets patch where USED (`spans_module.tracer`, `jump_mod.get_ruleset_module`), not where defined — correct. COMPLIANT.
- **#7 Resource leaks** — No file/socket/db/lock handles; the only context managers are `Span.open(...)` (correctly `with`-scoped in both emit helpers). COMPLIANT.
- **#8 Unsafe deserialization** — No pickle/eval/exec/yaml.load/subprocess. Inputs are a typed pydantic model + scalars. COMPLIANT.
- **#9 Async/await** — No async code in the diff (all jump code is synchronous; `narration_apply` helper is sync). N/A.
- **#10 Import hygiene** — New runtime imports are concrete (no star imports in production code). `spans/__init__.py` adds `from .jump import *` — this matches the established per-domain re-export convention the module documents and `test_routing_completeness` enforces. `narration_apply` correctly puts `CartographyConfig` under `TYPE_CHECKING` (annotation-only) and does a function-local runtime import of `adjudicate_inter_system_jump` to avoid an import cycle (orbital→ruleset→…; narration_apply→orbital). No new circular import. COMPLIANT.
- **#11 Input validation at boundaries** — No external/user input; region ids and cartography come from validated pack content. N/A.
- **#12 Dependency hygiene** — No dependency changes. N/A.
- **#13 Fix-introduced regressions** — The only post-RED change (getattr defensive guard for the `SimpleNamespace` test pack) does not introduce a check #1–#12 violation; it keeps the skip loud via the existing `if _region_rules is not None` gate. COMPLIANT.

**CLAUDE.md / SOUL.md additional rules:**
- **No Silent Fallbacks** — enforced (fail-loud base, explicit labelled default, propagating UnknownRulesetError). COMPLIANT.
- **OTEL Observability Principle** — every jump decision emits a span; both spans routed/flat-registered and lie-detector-visible. COMPLIANT.
- **No Stubbing / No half-wired** — the glue has a real production consumer (narration_apply orbital region-advance); not a dead shell. COMPLIANT (with the scoped Gap that cost-*application* awaits a fuel substrate — logged, not stubbed).
- **Crunch in the Genre, Flavor in the World** — jump mechanics live in the SWN ruleset module (genre rulebook); `routes` fields are world-authored content. COMPLIANT.

### Devil's Advocate

*Argue this code is broken.* The most damning angle: **the jump "mechanic" is a no-op that only writes a log line.** A career GM would ask — what does spending 2 fuel actually DO? Nothing. No fuel pool shrinks, no calendar advances, the party can jump infinitely at zero real cost. Sebastien/Jade, the mechanics-first players, would feel the same hollowness they felt when the confrontation engine was broken: the crunch *appears* to fire (a span!) but changes nothing the player experiences. Is this the "convincing narration with zero mechanical backing" the OTEL principle exists to catch? — I examined this closely. The honest answer: the span IS the mechanical backing the GM panel needs, and there is genuinely no fuel/clock substrate to mutate yet. This story's ACs are scoped to *adjudication + logging*; AC4 explicitly forbids touching the only clock that exists (ADR-130 intra-system). Building a fuel pool here would be unscoped invention. So it is a deliberately-staged increment, not a broken mechanic — but I am recording it as a MEDIUM observation and confirming Dev's Gap finding so the next story is unambiguous.

*What would a malicious/confused author do?* Author a `routes` entry with `jump_fuel: "lots"` (a string) — pydantic rejects it at load (typed `int | None`), fail-loud. Author a route whose endpoints aren't adjacent — dropped with a WARN, never promoted to connectivity (tested). Author two routes for one edge — last-wins silently (LOW finding; a future validator could warn). Author `drive_rating_min: 99` — every starter ship (rating 1) takes the +1-fuel strain, never blocked; a bare adjacency stays navigable, matching epic 98 §3. None of these corrupt state or crash.

*What breaks under stress?* A region-mode orbital world bound to a ruleset without a jump model: the move still lands, jump adjudication loud-skips (logged). An unregistered ruleset slug: `UnknownRulesetError` propagates and crashes the turn — correct fail-loud for a config bug pack-load already prevents. A self-heading (current == known region): excluded by the enclosing `!=` guard, no zero-distance jump. Resume/replay: the rng is seeded from `turn+edge`, so the hazard roll is stable across replays (ADR-128). `_prior_region` empty: falsy guard skips. I could not construct an input that produces state corruption, a silent wrong-cost, or an unlogged decision. The verdict stands: APPROVED with non-blocking observations.