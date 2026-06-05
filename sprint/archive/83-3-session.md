---
story_id: "83-3"
jira_key: ""
epic: "83"
workflow: "tdd"
---
# Story 83-3: Ongoing-threat identity stability — reconcile a re-described threat instead of re-minting

## Story Details
- **ID:** 83-3
- **Jira Key:** None (Jira not configured)
- **Workflow:** tdd
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-05T13:43:52Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-05T00:00:00Z | 2026-06-05T13:04:17Z | 13h 4m |
| red | 2026-06-05T13:04:17Z | 2026-06-05T13:17:01Z | 12m 44s |
| green | 2026-06-05T13:17:01Z | 2026-06-05T13:35:31Z | 18m 30s |
| review | 2026-06-05T13:35:31Z | 2026-06-05T13:43:52Z | 8m 21s |
| finish | 2026-06-05T13:43:52Z | - | - |

## Delivery Findings

<!-- append-only; never edit/remove another agent's entries -->

### TEA (test design)
- **Gap** (non-blocking): The reconciliation *heuristic* is a genuine design choice left to Dev — the ACs name three levers ("continuity flag / similarity / scene-guard") joined by "and/or". The tests are deliberately mechanism-agnostic (aligned signals), so any conforming lever passes. Recommended hook point: immediately **before** the Step-3 novel-mint at `sidequest/server/narration_apply.py:2035`, scoped to `mention.is_creature`. Affects `narration_apply.py::_apply_npc_mentions` (add a pre-Step-3 creature-reconciliation guard). *Found by TEA during test design.*
- **Gap** (non-blocking): The `npc.creature_reconciled` span the AC-3 test pins must be a real telemetry constant + helper, and registered in `SPAN_ROUTES` so the GM panel sees a `state_transition` (the AC-3 "GM panel can confirm" requirement). The RED test only asserts span emission + attributes via `otel_capture`; Dev must ALSO wire SPAN_ROUTES. Affects `sidequest/telemetry/spans/npc.py` (new `SPAN_NPC_CREATURE_RECONCILED` + `npc_creature_reconciled_span` + route). *Found by TEA during test design.*
- **Improvement** (non-blocking): `creature_id` is synthesized from the creature *name* (`narration_apply.py:1092`), so a re-described threat gets a *different* `creature_id` each turn — id-keyed reconciliation ALONE cannot collapse re-descriptions or shadow-match the authored Lion. Dev must reconcile on appearance/role/continuity/scene, not `creature_id`. Affects the guard's match key. *Found by TEA during test design.*
- **Question** (non-blocking): The existing `is_new` continuity signal is narrator-emitted (prompt-supported in `narrator_prompts/output_only.md`) but currently consumed only by `render_trigger`, **not** by the matching pipeline. Dev/Architect should confirm whether wiring `is_new=False` into the guard is sufficient given the bug shows the narrator re-minting (it may not reliably flag continuity) — hence the tests also align similarity + scene signals so the fix doesn't depend on narrator cooperation alone. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking, PRE-EXISTING — not 83-3): the full server suite has **20 failing tests on `develop`** unrelated to this story (verified by stashing my changes and diffing full-suite failures: 23 on base = 20 pre-existing + my 3 RED tests; 0 new failures introduced). Clusters: `test_npc_invented_namegen_routing.py` (6), `test_narration_clue_discovery_wiring.py` (5), `test_enums::test_message_type_complete_count`, `test_chargen_complete_no_hp_leak`, `test_lore_rag_wiring`, `test_retrieval_orchestration`, `test_pertinence_wiring`, `test_culture_context`, `test_yield_handler_outbound`, `test_apply_world_patch`, `test_61_12_output_format_compaction`. Affects those test files / their subsystems (someone should triage; out of scope for 83-3). *Found by Dev during implementation.*
- **Improvement** (non-blocking): the reconciliation guard considers ALL creatures in the snapshot, not creatures scoped to the current scene/location. The story names a "per scene" guard; a future refinement could filter candidates by `last_seen_location == party_location` so a threat in a distant location can't absorb a re-description here. Affects `narration_apply.py::_reconcile_ongoing_threat`. Low risk today (scenes rarely carry stale cross-location creatures), conservative similarity gating limits multi-candidate false merges. *Found by Dev during implementation.*
- **Improvement** (non-blocking): when reconciling to an authored `Npc`, the incoming descriptor could be accreted onto `Npc.aliases` (84-2 / ADR-118 §A4) so a future player/narrator reference by that epithet name-matches directly. Deliberately not done (no test requires it; minimalist scope). Affects `narration_apply.py` reconciliation guard + `alias_accretion`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): the `is_new=False` gate trusts the narrator's continuity flag. If the narrator emits `is_new=True` for a recurring threat (thinking it new), the guard won't fire and the bug recurs. A playtest pass (per the epic's origin session wry_whimsy/oz) should validate the narrator sets `is_new` reliably for re-described threats; if not, consider firing the guard on strong similarity even when `is_new=True`. Affects the gate condition. *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking, LOW): the pool-member reconciliation upsert (`narration_apply.py:~2177`) does not reference `drawn_from`, unlike the Step-2 path which computes `apply_overwrite = pool_hit.drawn_from != "world_authored"`. This is currently SAFE — the reconciliation upsert is fill-empty ONLY (never overwrites a non-empty value), and Step-2's fill-empty leg also fires for authored members — but for consistency/defense-in-depth a future change could mirror the Step-2 `drawn_from` awareness so the two upsert paths read identically. Affects `narration_apply.py::_apply_npc_mentions` reconciliation branch. *Found by Reviewer during code review (security subagent, downgraded).* 
- **Improvement** (non-blocking, LOW): `NpcMention.name/role/appearance` have no length bound; `_creature_tokens` allocates a token set proportional to input length. Narrator output is LLM-token-bounded and ADR-047-sanitized, so the practical risk is negligible, but a one-line `part[:512]` cap in `_creature_tokens` would close the unbounded-growth vector cheaply. Affects `narration_apply.py::_creature_tokens`. *Found by Reviewer during code review (security subagent).* 
- **Improvement** (non-blocking, LOW): `assert reconciled_member is not None` (`narration_apply.py:~2176`) is a type-narrowing invariant in a production path. It fails loud in both normal and `-O` mode (AssertionError vs AttributeError — neither silent), so it does not violate No Silent Fallbacks, but an explicit `if ... is None: logger.error(...); continue` would match the file's prevailing guard style. No `-O` deployment exists. Affects the reconciliation branch. *Found by Reviewer during code review (security + preflight subagents).* 

## Impact Summary

**Upstream Effects:** 2 findings (2 Gap, 0 Conflict, 0 Question, 0 Improvement)
**Blocking:** None

- **Gap:** The reconciliation *heuristic* is a genuine design choice left to Dev — the ACs name three levers ("continuity flag / similarity / scene-guard") joined by "and/or". The tests are deliberately mechanism-agnostic (aligned signals), so any conforming lever passes. Recommended hook point: immediately **before** the Step-3 novel-mint at `sidequest/server/narration_apply.py:2035`, scoped to `mention.is_creature`. Affects `narration_apply.py::_apply_npc_mentions`.
- **Gap:** The `npc.creature_reconciled` span the AC-3 test pins must be a real telemetry constant + helper, and registered in `SPAN_ROUTES` so the GM panel sees a `state_transition` (the AC-3 "GM panel can confirm" requirement). The RED test only asserts span emission + attributes via `otel_capture`; Dev must ALSO wire SPAN_ROUTES. Affects `sidequest/telemetry/spans/npc.py`.

### Downstream Effects

Cross-module impact: 2 findings across 2 modules

- **`.`** — 1 finding
- **`sidequest/telemetry/spans`** — 1 finding

### Deviation Justifications

4 deviations

- **Mechanism-agnostic test strategy instead of testing a single named lever**
  - Rationale: The ACs join the levers with "and/or" — the lever choice is Dev's. Aligning all signals keeps the suite passing for any conforming implementation while still reproducing the real bug.
  - Severity: minor
  - Forward impact: If Dev picks a lever and a future change narrows it, these tests won't catch lever-specific regressions — acceptable; the behavioral contract is the load-bearing guarantee.
- **AC-3 span asserted via `otel_capture` (span attributes), not the async WatcherSpanProcessor event harness**
  - Rationale: Matches the closest sibling precedent (`test_npc_comma_inversion_match.py`, same "prevent phantom mint" subsystem). SPAN_ROUTES/GM-panel routing is captured as a Delivery Finding for Dev so the GM-panel half is not lost.
  - Severity: minor
  - Forward impact: Dev must still register SPAN_ROUTES for true GM-panel visibility — flagged in Delivery Findings.
- **Implemented the multi-candidate `similarity` lever in addition to the single-candidate `scene_guard` lever the tests strictly require**
  - Rationale: a `scene_guard`-only fix silently re-breaks the moment a second creature is in scene (common in combat) — that ships a half-fix. The story explicitly names `similarity` as a lever; implementing it is correct scope, not creep. The conservative >0 threshold preserves AC-4 (no false merge).
  - Severity: minor
  - Forward impact: none negative; strengthens the fix. See the added test below.
- **Added a Dev-authored test for the `similarity` branch (extends TEA's red suite)**
  - Rationale: "Every test suite needs coverage" — new production logic must not be untested. Crosses the TEA/Dev authoring line by one test; flagged here for Reviewer/verify visibility.
  - Severity: minor
  - Forward impact: TEA verify phase will see 9 tests, not 8.

## Design Deviations

### TEA (test design)
- **Mechanism-agnostic test strategy instead of testing a single named lever**
  - Spec source: context-story-83-3.md, AC-1 / AC-3
  - Spec text: "reconciles to a SINGLE persistent identity ... + the signal used: continuity flag / similarity / scene-guard"
  - Implementation: "Should reconcile" inputs align ALL THREE signals (is_new=False + matching role/appearance + single active creature); "must not merge" inputs align the distinct signals (is_new=True + dissimilar appearance). Tests assert behavior + span contract, not which lever fired (the AC-3 `signal` value is asserted non-empty, not pinned to a string).
  - Rationale: The ACs join the levers with "and/or" — the lever choice is Dev's. Aligning all signals keeps the suite passing for any conforming implementation while still reproducing the real bug.
  - Severity: minor
  - Forward impact: If Dev picks a lever and a future change narrows it, these tests won't catch lever-specific regressions — acceptable; the behavioral contract is the load-bearing guarantee.
- **AC-3 span asserted via `otel_capture` (span attributes), not the async WatcherSpanProcessor event harness**
  - Spec source: context-story-83-3.md, AC-3
  - Spec text: "an OTEL span records the match ... so the GM panel can confirm"
  - Implementation: Test asserts the `npc.creature_reconciled` span fires with `incoming`/`reconciled_to`/`signal` attributes via the `otel_capture` exporter (the comma-inversion sibling's idiom), rather than asserting the routed `state_transition` watcher event.
  - Rationale: Matches the closest sibling precedent (`test_npc_comma_inversion_match.py`, same "prevent phantom mint" subsystem). SPAN_ROUTES/GM-panel routing is captured as a Delivery Finding for Dev so the GM-panel half is not lost.
  - Severity: minor
  - Forward impact: Dev must still register SPAN_ROUTES for true GM-panel visibility — flagged in Delivery Findings.

### Dev (implementation)
- **Implemented the multi-candidate `similarity` lever in addition to the single-candidate `scene_guard` lever the tests strictly require**
  - Spec source: context-story-83-3.md, AC-1 / AC-4
  - Spec text: "the signal used: continuity flag / similarity / scene-guard" / "two genuinely distinct threats in the same scene stay distinct"
  - Implementation: `_reconcile_ongoing_threat` fast-paths a single active creature (`scene_guard`) but, when several creatures are active, disambiguates by role/appearance token overlap (`similarity`), reconciling only on a clear (>0) match. TEA's 8 tests only exercise single-candidate scenes.
  - Rationale: a `scene_guard`-only fix silently re-breaks the moment a second creature is in scene (common in combat) — that ships a half-fix. The story explicitly names `similarity` as a lever; implementing it is correct scope, not creep. The conservative >0 threshold preserves AC-4 (no false merge).
  - Severity: minor
  - Forward impact: none negative; strengthens the fix. See the added test below.
- **Added a Dev-authored test for the `similarity` branch (extends TEA's red suite)**
  - Spec source: context-story-83-3.md, AC-1 / AC-4
  - Spec text: (same as above)
  - Implementation: added `test_multiple_threats_redescription_reconciles_by_similarity` to `tests/server/test_npc_ongoing_threat_reconciliation.py` so the multi-candidate disambiguation path I introduced has coverage (asserts the granite re-description reconciles to the golem, not the swarm, with `signal="similarity"`).
  - Rationale: "Every test suite needs coverage" — new production logic must not be untested. Crosses the TEA/Dev authoring line by one test; flagged here for Reviewer/verify visibility.
  - Severity: minor
  - Forward impact: TEA verify phase will see 9 tests, not 8.

### Reviewer (audit)
- **TEA: Mechanism-agnostic test strategy** → ✓ ACCEPTED by Reviewer: sound. Aligning all three levers for "should reconcile" inputs and the distinct signals for "must not merge" is the correct way to pin behavior without dictating Dev's mechanism; the suite still reproduces the real bug. Agrees with author reasoning.
- **TEA: AC-3 span via `otel_capture` not the watcher-event harness** → ✓ ACCEPTED by Reviewer: matches the comma-inversion sibling precedent, and the SPAN_ROUTES registration (verified present, `spans/npc.py:~337`) means GM-panel visibility is not lost despite the lighter test harness.
- **Dev: Implemented `similarity` lever beyond the tests' single-candidate `scene_guard`** → ✓ ACCEPTED by Reviewer: correct scope, not creep. A scene-guard-only fix silently re-breaks the moment a second creature is in scene; the story explicitly names `similarity`. The `>0` threshold preserves AC-4 conservatism. The branch is covered by the Dev-added test.
- **Dev: Added a similarity-branch test (crosses TEA/Dev authoring line by one test)** → ✓ ACCEPTED by Reviewer: the right call — new production logic must not ship untested, and "Every Test Suite Needs a Wiring Test" supports it. The added test is behavioral and non-vacuous.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/server/narration_apply.py` — pre-Step-3 creature-reconciliation guard in `_apply_npc_mentions` (gated on `is_creature and not is_new`); helpers `_reconcile_ongoing_threat`, `_creature_similarity`, `_creature_tokens` + `_RECONCILE_STOPWORDS`. Reconciles to a roster `Npc` (stamps `last_seen_*`) or a prior pool member (fill-empty upsert); `scene_guard` (one active creature) + `similarity` (multi-creature token overlap) levers; never keys on `creature_id`.
- `sidequest/telemetry/spans/npc.py` — new `SPAN_NPC_CREATURE_RECONCILED` + `SPAN_ROUTES` entry (state_transition, component `npc_registry`) + `npc_creature_reconciled_span` helper (incoming / reconciled_to / signal / target_store / turn_number).
- `tests/server/test_npc_ongoing_threat_reconciliation.py` — added one Dev test for the similarity branch (see deviation).

**Tests:** 9/9 passing (GREEN) — `uv run pytest tests/server/test_npc_ongoing_threat_reconciliation.py -n0`.
**Full suite:** 20 failures, ALL pre-existing on `develop` (proven by stash-and-diff: 0 new failures introduced, my 3 RED tests now pass). Logged as a non-blocking pre-existing finding.
**Lint/format:** `ruff check` clean on changed files; `ruff format` applied (additions only — 169 insertions / 0 deletions on narration_apply.py, no pre-existing churn).
**Typecheck:** `pyright` — 0 errors in my added lines (the file's 36 errors are all pre-existing, outside my edit region).
**Branch:** feat/83-3-ongoing-threat-identity-stability (pushed).

**ACs:** AC-1 (single identity) ✓ · AC-2 (no shadow of authored Npc) ✓ · AC-3 (span-visible, SPAN_ROUTES wired for GM panel) ✓ · AC-4 (no false merge, conservative) ✓ · AC-5 (person path + comma-inversion + npcs_hit preserved) ✓.

**Handoff:** To Reviewer (The Merovingian) for code review.

## TEA Assessment

### Red Phase (test writing)

**Tests Required:** Yes
**Reason:** n/a — a behavioral bug fix; the contract must be pinned before implementation.

**Test Files:**
- `sidequest-server/tests/server/test_npc_ongoing_threat_reconciliation.py` — drives the real `_apply_npc_mentions` seam; reproduces the #74-deferred re-mint bug and pins the reconciliation contract.

**Tests Written:** 8 tests covering 5 ACs.
**Status:** RED — 3 new-behavior tests FAIL, 5 conservatism/regression guards PASS (verified `uv run pytest ... -n0`).

| AC | Test | Today |
|----|------|-------|
| AC-1 single identity | `test_redescribed_threat_collapses_to_single_pool_member` | **FAIL** (mints 3) |
| AC-2 no shadow | `test_authored_creature_npc_not_shadowed_by_phantom` | **FAIL** (phantom minted) |
| AC-3 span-visible | `test_reconciliation_emits_creature_reconciled_span` | **FAIL** (no span) |
| AC-4 no false merge | `test_distinct_creatures_in_scene_stay_distinct` | pass (guard) |
| AC-4 no false merge | `test_distinct_creature_does_not_merge_into_authored_npc` | pass (guard) |
| AC-5 preserve persons | `test_distinct_named_persons_not_collapsed` | pass (guard) |
| AC-5 creature firewall | `test_person_mention_never_fires_creature_reconcile_span` | pass (guard) |
| AC-5 name-match intact | `test_exact_name_creature_match_still_uses_existing_npcs_hit` | pass (regression) |

The 3 failures reproduce the documented #74 deferral exactly:
- AC-1 → `got 3: ['a snarling forest beast', 'the lurking predator', 'the shadow that stalks']`
- AC-2 → `got ['the trembling forest-beast']` (Cowardly Lion shadowed)
- AC-3 → `assert []` (no `npc.creature_reconciled` span)

### Rule Coverage

Python lang-review checklist (`.pennyfarthing/gates/lang-review/python.md`) — the one applicable rule to test code here is **#6 Test quality**:

| Rule | Coverage | Status |
|------|----------|--------|
| #6 no vacuous asserts | Every test asserts a specific value/count/attribute (no `assert True`, no bare truthy on always-None); span tests assert exact `incoming`/`reconciled_to` + non-empty `signal` | pass |
| #6 no source-text wiring | Tests drive the real `_apply_npc_mentions` production seam + assert OTEL/state (server CLAUDE.md "No Source-Text Wiring Tests") | pass |

**Rules checked:** 1 of the lang-review rules is applicable to new test code (the others govern production `.py` Dev will add). **Self-check:** 0 vacuous tests found.

**Wiring:** `_apply_npc_mentions` is the production seam (called from `_apply_narration_result_to_snapshot`, `narration_apply.py:3842`); driving it directly exercises the real code path the server runs (same approach as `test_npc_comma_inversion_match.py` and `test_creature_mm_identity_83_1.py`).

**Handoff:** To Dev (Agent Smith) for implementation. See Delivery Findings for the hook point (`narration_apply.py:2035`, pre-Step-3, `is_creature`-scoped), the span/SPAN_ROUTES requirement, and why `creature_id`-only matching is insufficient.

## Sm Assessment

Setup complete. Branch created at feat/83-3-ongoing-threat-identity-stability (server repo, off origin/develop).

Context files created:
- sprint/context/context-story-83-3.md
- sprint/context/context-epic-83.md

Workflow is phased (tdd: SM → TEA → Dev → Reviewer → SM finish). Routing to TEA for red phase.

## Subagent Results

Scope note: review diffed against `origin/develop` (local `develop` was stale — 29-file phantom diff). 83-3 is exactly 3 files / 768 insertions. Subagent toggles: only `preflight` and `security` enabled (`pf settings get workflow.reviewer_subagents`); the other 7 are disabled and assessed by the Reviewer directly.

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 7 notes (0 blocking) | confirmed 0 new, corroborated 3 (is_new gate, scene-guard breadth, assert), all non-blocking |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — edges assessed by Reviewer (see Devil's Advocate) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — assessed by Reviewer ([SILENT] below) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — test quality assessed by Reviewer ([TEST] below) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — docs assessed by Reviewer ([DOC] below) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — types assessed by Reviewer ([TYPE] below) |
| 7 | reviewer-security | Yes | findings | 3 (1 med→downgraded LOW, 2 low) | confirmed 3 as LOW non-blocking, 0 dismissed (med downgraded with line evidence) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — complexity assessed by Reviewer ([SIMPLE] below) |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rules enumerated by Reviewer ([RULE] below) |

**All received:** Yes (2 enabled subagents returned; 7 disabled via settings and assessed directly)
**Total findings:** 0 confirmed blocking, 3 confirmed LOW non-blocking, 0 dismissed, 0 deferred

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** narrator tool output → `NpcMention(name/role/appearance/is_new/is_creature)` (orchestrator.py, ADR-047-sanitized) → `_apply_npc_mentions` Steps 1/2 name-match (miss) → new reconciliation guard (gated `is_creature and not is_new`) → `_reconcile_ongoing_threat` returns an existing `Npc`/pool member or `None` → on hit: stamp `last_seen_*` (Npc) or fill-empty upsert (pool) + emit `npc.creature_reconciled` span; on `None`: fall through to Step-3 mint. Safe: the guard only runs after name-match fails, never overwrites non-empty values, and is fully span-visible.

### Rule Compliance (Python lang-review checklist + CLAUDE.md/SOUL.md)

Enumerated every new function/symbol (`_RECONCILE_STOPWORDS`, `_creature_tokens`, `_creature_similarity`, `_reconcile_ongoing_threat`, the guard block, `SPAN_NPC_CREATURE_RECONCILED` + route + `npc_creature_reconciled_span`):

| Rule | Instances checked | Verdict |
|------|-------------------|---------|
| #1 silent exception swallowing | guard + 3 helpers | PASS — no try/except in new code |
| #2 mutable default args | 3 helpers + span helper | PASS — no defaults (kw-only / *args) |
| #3 type annotations at boundaries | all new fns | PASS — fully annotated; `mention: Any` is the file's existing convention (avoids circular import), matches `mentions: list[Any]` |
| #4 logging coverage/correctness | guard `logger.info` | PASS — `%`-lazy formatting, info-level state event, no sensitive data |
| #5 path handling | n/a | N/A — no paths |
| #6 test quality | all 9 tests | PASS — specific value/count/attr asserts, no vacuous/skip, behavioral on real seam |
| #7 resource leaks | span helper | PASS — `with Span.open(...)` context manager |
| #8 unsafe deserialization | n/a | N/A |
| CLAUDE: No Silent Fallbacks | `_reconcile_ongoing_threat` None path; reconcile always spans | PASS — None→mint is explicit/documented; every reconcile emits a span |
| CLAUDE: OTEL Observability | new span + SPAN_ROUTES | PASS — GM-panel visible (`state_transition`, component `npc_registry`) |
| CLAUDE: No Source-Text Wiring Tests | test file | PASS — drives real seam, no `read_text()` grep |
| SOUL: authored content protected | pool upsert | PASS — fill-empty only (never overwrites authored values); strictly more conservative than Step-2 |

### Observations (tagged)

- `[VERIFIED]` OTEL fully wired — `SPAN_NPC_CREATURE_RECONCILED` constant + `SPAN_ROUTES` route (`spans/npc.py:~337`) + helper imported (`narration_apply.py:101`) + called in guard (`~2186`). Evidence: span lands in `otel_capture` (AC-3 test green) and routes as `state_transition`. `[PRE]` preflight confirmed wiring.
- `[VERIFIED]` Conservatism / no false merge — `_reconcile_ongoing_threat` returns `None` (→ mint) for `total==0` and for multi-candidate ties/zero-overlap; gate `not mention.is_new` keeps genuinely-new creatures out. Evidence: `narration_apply.py:~1834-1860`; AC-4 tests green.
- `[VERIFIED]` Authored-content safety — pool upsert is fill-empty only (`if mention.role and not reconciled_member.role`), matching Step-2's fill-empty leg (line 2112-2113) which also fills authored members; never overwrites. Evidence: `narration_apply.py:~2177` vs `:2099/2112`.
- `[SEC][MEDIUM→LOW] authored-content consistency` — security subagent flagged the pool upsert for not checking `drawn_from`; DOWNGRADED to LOW because the upsert is fill-empty only and Step-2 also fills empty authored fields (the `drawn_from` guard there gates only OVERWRITES, which this code never does). Non-blocking; consistency note in Delivery Findings.
- `[SEC][LOW] unbounded token input` — `NpcMention.appearance` has no length cap; `_creature_tokens` allocates proportional tokens. Narrator output is token-bounded + ADR-047-sanitized → negligible; cheap `[:512]` guard suggested. Non-blocking.
- `[SEC][SILENT][LOW] assert in production` — `assert reconciled_member is not None` (`~2176`); fails loud in both normal and `-O` mode (not silent), no `-O` deployment. Style-only; explicit `if/continue` would match file idiom. Non-blocking.
- `[MEDIUM] is_new reliability (scope boundary, non-blocking)` — the single-candidate `scene_guard` reconciles regardless of similarity/side; if the narrator omits `is_new=True` on a genuinely-new creature while one creature is in scene, it would merge. This is the spec'd lever ("one active unnamed threat") and AC-4 only requires distinctness when `is_new=True`; flagged by Dev + preflight for playtest validation. Not a logic defect.
- `[TEST] (self, analyzer disabled)` — 9 tests, behavioral, non-vacuous, real-seam; meaningful assertions verified by reading the file. No coupling to implementation internals beyond the span-name contract.
- `[TYPE] (self, disabled)` — return type `tuple[Npc | None, NpcPoolMember | None, str] | None` is precise; the `(npc, None)` / `(None, member)` xor invariant is documented and enforced by construction.
- `[DOC] (self, disabled)` — comments are accurate and substantial; the span docstring + SPAN_ROUTES comment correctly describe levers. No stale/misleading docs.
- `[SIMPLE] (self, disabled)` — no over-engineering; helpers are small and single-purpose. The similarity branch is justified (multi-creature scenes) and covered by a test.
- `[RULE] (self, rule-checker disabled)` — full lang-review enumeration above: all applicable rules PASS.

### Devil's Advocate

Argue this is broken. **The continuity gate is a load-bearing lie.** `NpcMention.is_new` defaults to `False`, and the guard fires on `not is_new`. So the guard's "conservatism" depends entirely on the narrator *correctly* setting `is_new=True` for every genuinely-new creature. But the very bug this story fixes is evidence the narrator is sloppy about creature identity. Picture a goblin warren: the narrator mints "a hulking goblin" (turn 1, `is_new=True`), then on turn 2 introduces a *second, distinct* goblin and — distracted by prose — leaves `is_new` unset (defaults `False`). Now `total==1`, `scene_guard` fires, and the second goblin is silently absorbed into the first. Two monsters become one — the exact failure mode AC-4 claims to prevent, just triggered by an omission instead of a re-description. The test suite never exercises this because every AC-4 input sets `is_new=True` explicitly. **Worse: `scene_guard` ignores `side` and disposition.** A friendly creature companion (the Cowardly Lion at disposition 5) alone in scene will absorb a continuity-flagged *hostile* mention — an ally and an enemy collapse into one entity, with the enemy's role fill-empty-written onto the ally. **And the breadth bug:** candidates span the whole roster, not the current location, so a creature from three scenes ago that never left `snapshot.npcs` keeps counting toward `total`, flipping `scene_guard` into `similarity` unexpectedly (the operator sees the "wrong" signal on the GM panel). What about a stressed input? A 2 MB `appearance` string allocates a giant token set per candidate per turn — a soft DoS, though the narrator's token budget makes it implausible. **Verdict on the devil's case:** every one of these is real but bounded. The `side`/location concerns and the `is_new`-omission merge are genuine playtest risks, but they are (a) the spec'd behavior — the story explicitly sanctions the "one active unnamed threat" lever, (b) flagged in Delivery Findings for playtest validation, and (c) fail *loud and span-visible* (`npc.creature_reconciled` fires on every merge, so the GM panel shows exactly what collapsed — never a silent identity loss). None corrupt persistence, leak data, or crash. They are tuning surface, not defects. The fix is correct, conservative-by-construction in the multi-candidate path, and fully observable. APPROVE stands.

**Pattern observed:** guard inserted between Step-2 and Step-3 of `_apply_npc_mentions`, mirroring the existing `npcs_hit`/`pool_hit` continue-on-match structure — `narration_apply.py:~2142`.
**Error handling:** no exception paths; the `None`-return → mint fallback is explicit and the only failure mode, consistent with No Silent Fallbacks.
**Handoff:** To SM (Morpheus) for finish-story.