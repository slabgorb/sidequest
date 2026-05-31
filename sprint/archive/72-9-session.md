---
story_id: "72-9"
jira_key: ""
epic: "72"
workflow: "tdd"
---
# Story 72-9: Wire OCEAN/disposition + scenario belief_state for narrator-invented NPCs

## Story Details
- **ID:** 72-9
- **Jira Key:** (none — Jira not configured for this project)
- **Workflow:** tdd
- **Stack Parent:** none
- **Points:** 5
- **Priority:** p3
- **Type:** feature

## Story Context
**Epic:** 72 — NPC Identity Hardening

**Source:** Deep-dive from perseus_cloud session 894 (2026-05-29). An NPC has no stable identity; identity is fragmented across two unreconciled stores (`snapshot.npcs` = mechanical state; `snapshot.npc_pool` = identity scaffold) with no consistency invariant.

**Objective:** When the narrator invents an NPC on the fly (vs. a pre-generated Monster Manual or scenario NPC), that NPC must be wired into the **same subsystems** pre-generated NPCs use:
- OCEAN personality live evolution (ADR-042)
- NPC disposition system (ADR-020)
- scenario belief_state / clue-graph + gossip propagation (ADR-053)

**Current State:** Narrator-invented NPCs likely bypass these subsystems, so they don't evolve, don't carry disposition into gossip, and aren't visible to the scenario belief engine.

**Dependency Chain (Epic 72 substrate):**
- 72-1: ✅ Revived dormant development pipeline — interest-signal, resolution_tier escalation, disposition drift, OTEL
- 72-2: ✅ Preserve disposition on pool→Npc promotion + reconcile npcs vs npc_pool on load
- 72-4: ✅ Route narrator-invented NPC names through culture-bound ADR-091 namegen
- 72-5: ✅ Fix born-hostile disposition default → neutral spawn
- **72-9: THIS STORY** — Wire OCEAN/disposition + scenario belief_state for narrator-invented NPCs

## Acceptance Criteria
1. **OCEAN Wiring:** When the narrator invents an NPC, that NPC is registered in the OCEAN evolution subsystem and receives personality drift events.
   - OTEL span `npc.ocean_wired` emitted on NPC creation.
   - Personality attributes (O, C, E, A, N) initialized from defaults or genre spec.

2. **Disposition Wiring:** Narrator-invented NPCs are seeded with a disposition value (neutral per 72-5), tracked in the disposition system, and eligible for disposition evolution.
   - OTEL span `npc.disposition_seeded` emitted with initial value.
   - Disposition updates flow through the same resolution_tier/interest-signal pipeline as pre-generated NPCs.

3. **Scenario Belief State Wiring:** Narrator-invented NPCs are registered in the scenario belief_state system (ADR-053) and participate in clue-graph + gossip propagation.
   - OTEL span `scenario.belief_npc_registered` emitted on NPC creation.
   - NPC state changes (disposition, location, observed actions) are visible to the belief engine for gossip propagation.

4. **OTEL Coverage:** Every subsystem decision (OCEAN applied, disposition seeded, belief_state registered) is observable via the GM panel. OTEL spans must include:
   - NPC name, ID, genre (where applicable)
   - Subsystem (ocean, disposition, belief_state)
   - Reason for the event (e.g., "narrator_invention", "on_load", "stat_escalation")
   - Any state change (old/new personality, disposition delta, etc.)

5. **No Regressions:** Pre-generated NPCs and Monster Manual NPCs continue to wire correctly. The change affects only narrator-invented NPCs, adding subsystem integration, not disrupting existing flows.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-31T00:15:14Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-30T23:44:51Z | 2026-05-30T23:46:50Z | 1m 59s |
| red | 2026-05-30T23:46:50Z | 2026-05-30T23:55:53Z | 9m 3s |
| green | 2026-05-30T23:55:53Z | 2026-05-31T00:01:29Z | 5m 36s |
| spec-check | 2026-05-31T00:01:29Z | 2026-05-31T00:03:28Z | 1m 59s |
| verify | 2026-05-31T00:03:28Z | 2026-05-31T00:06:29Z | 3m 1s |
| review | 2026-05-31T00:06:29Z | 2026-05-31T00:14:05Z | 7m 36s |
| spec-reconcile | 2026-05-31T00:14:05Z | 2026-05-31T00:15:14Z | 1m 9s |
| finish | 2026-05-31T00:15:14Z | - | - |

## Sm Assessment

**Setup verdict:** Ready for RED. Story is well-grounded in epic 72's deep-dive and sits on a completed substrate — 72-1 (revived development pipeline + OTEL), 72-2 (disposition preservation on pool→Npc promotion + load reconcile), 72-4 (culture-bound namegen for invented NPCs), and 72-5 (neutral spawn disposition) are all done and approved. 72-9 is the integration leg: route narrator-invented NPCs into the same OCEAN (ADR-042), disposition (ADR-020), and scenario belief_state/gossip (ADR-053) subsystems pre-generated NPCs already use.

**Routing rationale:** tdd / phased → TEA owns RED. This is integration-wiring work where the failure mode is "convincing narration, zero mechanical backing" — exactly what the OTEL doctrine guards against. RED must assert not just that the subsystems are reachable but that they *fire*: wiring tests that prove invented NPCs evolve OCEAN, carry disposition into gossip, and register in belief_state, each with an OTEL watcher event the GM panel can see.

**Watch items for TEA/Dev:**
- The two-store split (`snapshot.npcs` vs `snapshot.npc_pool`) is the root hazard of this epic — verify invented NPCs are reconciled across both before subsystem wiring, leaning on the 72-2 reconcile path rather than re-inventing it (Don't Reinvent — Wire Up What Exists).
- Every subsystem decision needs an OTEL span (OCEAN-evolution-applied, disposition-seeded, belief_state-registered). No span = can't tell wiring from improvisation.
- Include at least one end-to-end wiring test proving an invented NPC reaches each subsystem from a production code path, not just in isolation.

**Jira:** integration not configured for this project — no Jira ceremony, by design.

## TEA Assessment

**Tests Required:** Yes
**Reason:** 5-point integration-wiring story; behavior is new (OCEAN/belief/scenario seeding for invented NPCs) and load-bearing for the OTEL lie-detector.

**Test Files:**
- `sidequest-server/tests/integration/test_npc_identity_seed_otel.py` — 7 tests covering the 5 derived ACs + 2 edge guards. Mirrors the 72-5 harness (`test_npc_spawn_disposition_otel.py`): `TracerProvider` + `WatcherSpanProcessor` + `watcher_hub` capture, drives the **real** `resolve_status_target` → `_promote_pool_member_to_npc` production seam, asserts observable `Npc` end-state + routed `state_transition` watcher events. No source-text greps (server CLAUDE.md "No Source-Text Wiring Tests").

**Tests Written:** 7 tests covering 5 ACs + 2 edge cases
**Status:** RED confirmed — `4 failed, 3 passed` (clean AssertionErrors, no import/collection errors)

| Test | AC | RED/Guard | Status |
|------|----|-----------|--------|
| `test_invented_npc_gets_ocean_profile` | AC-1 | RED driver | failing (`ocean is None`) |
| `test_invented_npc_spawns_neutral_disposition` | AC-2 | guard (72-2/72-5) | passing |
| `test_invented_npc_registered_in_active_scenario` | AC-3 | RED driver | failing (`npc_roles == {}`) |
| `test_no_scenario_still_seeds_ocean_and_disposition` | AC-4 | RED driver | failing (`ocean is None`) |
| `test_identity_seed_span_fires_from_production_path` | AC-5 | RED driver (wiring) | failing (no `npc.identity_seeded` event) |
| `test_existing_seeded_npc_not_reseeded` | edge: no-clobber | guard | passing |
| `test_world_authored_promotion_does_not_fire_invented_seed` | edge: lineage | guard | passing |

The AC-5 capture log (`npc.spawn_disposition` + `npcs` fired, `npc.identity_seeded` absent) confirms the production seam is genuinely exercised — the failure is missing wiring, not a dead test path.

### Rule Coverage

Python lang-review (`gates/lang-review/python.md`) is a **dev-side** implementation checklist; the test-relevant rule is #6 (test quality). Beyond ACs, these project rules drive test design:

| Rule / Principle | Test(s) | Status |
|------------------|---------|--------|
| OTEL Observability ("every subsystem decision emits a span") | `test_identity_seed_span_fires_from_production_path` | failing |
| Verify Wiring, Not Just Existence (reach from production path) | AC-5 drives `resolve_status_target`, not the helper | failing |
| Every Test Suite Needs a Wiring Test | AC-5 is the integration/wiring test | failing |
| No Source-Text Wiring Tests | All 7 are behavioral + span assertions; zero `read_text()` | n/a (satisfied) |
| No Stubbing (OCEAN must be real, not empty `{}`) | `test_invented_npc_gets_ocean_profile` asserts `!= {}` + 5 dims | failing |
| No Silent Fallbacks | AC-4 asserts `scenario_registered` explicit `False`, not silent `None` | failing |
| lang-review #6 test quality (no vacuous asserts) | self-check below | pass |

**Rules checked:** 7 of 7 applicable project rules/principles have test coverage.
**Self-check:** 0 vacuous tests. Every test has ≥1 meaningful value assertion; no `assert True`, no bare `let _`, no truthy-only checks on always-true values. (AC-3's `isinstance(..beliefs, list)` is paired with stronger `npc_roles` value assertions.)

**Handoff:** To Dev (Puck) for GREEN. Key implementation note (see Delivery Findings): `_promote_pool_member_to_npc` lacks a `snapshot` param — thread it in, or seed + register at the `resolve_status_target` call site. New span contract names are pinned in the test-file header and the AC-5 assertions.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (no fixes applied — tree unchanged from Dev's pushed GREEN)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 3 (`narration_apply.py`, `telemetry/spans/npc.py`, `test_npc_identity_seed_otel.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | test helpers (`_setup`/`_wait_for_event`/`_find_event`) duplicate `test_npc_spawn_disposition_otel.py` |
| simplify-quality | clean | no findings |
| simplify-efficiency | 1 finding | "read-after-write" on `scenario_state.npc_roles[name]` |

**Applied:** 0 high-confidence fixes
**Flagged for Review:** 0
**Noted / Declined:** 2 (both high-confidence by the teammates, but declined with rationale below)
**Reverted:** 0

**Decline rationale:**
- **reuse finding (test-helper duplication) — DEFERRED to backlog 71-34.** The dup is real but pre-existing (the OTEL watcher-test harness pattern was established by 72-5's `test_npc_spawn_disposition_otel.py`), and extracting it requires editing that sibling test file — outside this story's diff. There is already a tracked backlog story for exactly this: **71-34 "Extract shared OTEL watcher-test harness."** Doing it here would duplicate 71-34 and creep scope into a 72-5 artifact. Correct disposition: leave for 71-34.
- **efficiency finding (read-after-write) — DISMISSED (false positive, would regress behavior).** The teammate's suggested rewrite (`scenario_role = ScenarioRole.Innocent; npc_roles[name] = scenario_role`) is NOT equivalent: the current `if name not in npc_roles: npc_roles[name] = Innocent` then `scenario_role = npc_roles[name]` deliberately **preserves a pre-existing role** (assign-if-absent, then read the actual value) rather than unconditionally overwriting it. The "redundant" read is the no-clobber guard Architect spec-check confirmed as correct. Applying the suggestion would clobber an existing role for any invented name that collides with an already-registered scenario NPC. Kept as-is.

**Overall:** simplify: clean (2 findings reviewed, 0 applied — 1 deferred to 71-34, 1 dismissed as a behavior-changing false positive)

**Quality Checks:** Tests green (7/7 story + 39/39 neighborhood from Dev green; tree unchanged), ruff clean.
**Handoff:** To Reviewer (Portia) for code review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned (2 minor/trivial notes, neither blocking)
**Mismatches Found:** 2

AC-by-AC against the authoritative `context-story-72-9.md` (higher authority than the session's auto-generated AC bullets):
- **AC-1 OCEAN** ✓ `npc.ocean = OceanProfile().model_dump()` — real, non-None, all five dims; flat baseline explicitly sanctioned by the context.
- **AC-2 neutral disposition** ✓ untouched; carried at 0 via 72-2/72-5.
- **AC-3 scenario registration** ✓ `npc_roles[name] = ScenarioRole.Innocent` when scenario active; live `BeliefState` already on the `Npc`; mirrors `bind_scenario`. Gracefully preserves a pre-existing role (no clobber of an authored entry sharing the name).
- **AC-4 no scenario** ✓ `scenario_registered=False`, OCEAN still seeded, `scenario_state` untouched.
- **AC-5 span from production path** ✓ span fires inside `_seed_invented_npc_identity`, invoked from `resolve_status_target`.
- **Edges** ✓ lineage guard (`drawn_from != "narrator_invented"` → no-op) + idempotency guard (`if npc.ocean: return`) both present; No-Silent-Fallbacks honored (inline `OceanProfile` import would raise loud, no silent `ocean=None`).

Mismatches:
- **Identity-seed span omits `scenario_id`** (Missing in code — Behavioral, Minor)
  - Spec: context AC-5 lists span attributes "...`scenario_registered` bool + scenario_id/role when a scenario is active."
  - Code: emits `scenario_registered` + `scenario_role`, no `scenario_id`.
  - Recommendation: **D — Defer.** Verified `ScenarioState` carries no `scenario_id` field; the id lives at the binding layer (`bind_scenario` returns it to be stashed in `world_scenarios`, not on `snapshot.scenario_state`). Emitting it at the seeding seam would require new plumbing of the id into the snapshot — out of scope for a 5-pt wiring story. `scenario_registered` + `scenario_role` already satisfy the lie-detector's core need (did the wiring fire, in what role). The authoritative TEA test contract did not require `scenario_id`. Logged for the boss; a follow-up can thread the id if the GM panel needs per-scenario attribution.

- **Session AC bullets name three spans; implementation uses one** (Ambiguous spec — Cosmetic, Trivial)
  - Spec: the session's auto-generated AC bullets (sm-setup boilerplate) mention `npc.ocean_wired`, `npc.disposition_seeded`, `scenario.belief_npc_registered`.
  - Code: one consolidated `npc.identity_seeded` span.
  - Recommendation: **A — Accept.** The authoritative `context-story-72-9.md` explicitly specifies "Add **one new** OCEAN/belief-seed span." The implementation aligns with the higher-authority context; the three-span bullets were non-authoritative setup boilerplate. No code change. One consolidated span is also the cleaner GM-panel signal (one event carries all three facts).

**Reuse check (pragmatic restraint):** No new infrastructure invented. The seed mirrors the existing `bind_scenario` seeding shape, reuses `OceanProfile`/`ScenarioRole`/`Disposition`/`BeliefState` data models, and the new span follows the established `SpanRoute` + context-manager pattern (twin of `npc.spawn_disposition`). One small helper at the existing promotion seam — correct altitude for the change.

**Decision:** Proceed to review (TEA verify next). No hand-back to Dev.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (GREEN 7/7, lint+format clean, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings (covered by Reviewer) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings (covered by Reviewer) |
| 4 | reviewer-test-analyzer | Yes | findings | 6 | confirmed 3 (LOW), deferred 3 (LOW) |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 3 (LOW doc) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings (covered by Reviewer) |
| 7 | reviewer-security | No | Skipped | disabled | Disabled via settings (covered by Reviewer) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings (covered by Reviewer + verify-phase simplify) |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 1 (LOW), dismissed 2, deferred 1 (pre-existing) |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 1 confirmed actionable-now (LOW), 9 confirmed-LOW/deferred non-blocking, 2 dismissed (with rationale). **Zero Critical/High.**

## Reviewer Assessment

**Verdict:** APPROVED

A correct, minimal, well-tested integration of OCEAN/disposition/scenario-`belief_state` seeding onto narrator-invented NPCs. All five derived ACs are genuinely covered (AC-5 drives the real `resolve_status_target` production path and asserts the routed `npc.identity_seeded` watcher event end-to-end). No Critical or High findings from any subagent or my own pass. The findings are documentation-precision and test-strengthening polish, plus two false/pre-existing items I dismiss or defer below.

**Data flow traced:** narrator-invented name → `_apply_npc_mentions` mints `NpcPoolMember(drawn_from="narrator_invented")` → status mutation → `resolve_status_target(snapshot, …)` → `_promote_pool_member_to_npc` → `_seed_invented_npc_identity` seeds `OceanProfile().model_dump()`, registers `npc_roles[name]=innocent` (scenario active), emits span → `snapshot.npcs.append`. Safe: single promotion caller confirmed (only `resolve_status_target` calls `_promote_pool_member_to_npc`).

**Pattern observed:** new span mirrors the established `SpanRoute` + `@contextmanager` twin of `npc.spawn_disposition` (`telemetry/spans/npc.py`); scenario seeding mirrors `bind_scenario` (`server/dispatch/scenario_bind.py`). Reuse-first, correct altitude.

### Observations

- `[VERIFIED]` OCEAN is a real profile, not a stub — `narration_apply.py:1142` assigns `OceanProfile().model_dump()` (5 dims, all 5.0); AC-1 asserts all five keys + range. Complies with No Stubbing.
- `[VERIFIED]` No Silent Fallbacks — `narration_apply.py:1139-1142` inline imports raise loud on failure; no `try/except`, no silent `ocean=None`. Complies with the No Silent Fallbacks rule.
- `[VERIFIED]` Lineage guard correct — `narration_apply.py:1133` `if member.drawn_from != "narrator_invented": return`; guards all four non-invented lineages. Test `test_world_authored_promotion_does_not_fire_invented_seed` confirms.
- `[VERIFIED]` No-clobber of existing role — `narration_apply.py:1149-1151` assigns Innocent only if absent, else preserves; honestly reports the actual role in the span (lie-detector reports truth).
- `[VERIFIED]` OTEL wiring reaches GM panel — `SPAN_ROUTES[SPAN_NPC_IDENTITY_SEEDED]` registered (`npc.py`), `component="npc_identity"`; AC-5 asserts the routed `state_transition`.
- `[SEC]` (security subagent disabled — covered here) No injection/auth/tenant surface: internal game-state mutation; `npc.core.name` flows to an OTEL string attribute and a dict key, already validated upstream (CreatureCore pydantic + ADR-047 sanitization). No SQL/HTML/path. VERIFIED clean.
- `[SILENT]` (silent-failure subagent disabled — covered here) No swallowed errors; both early returns are expected guard paths, not error suppression. VERIFIED clean.
- `[EDGE]` (edge-hunter disabled — covered here) Boundaries checked: `ocean=None` fresh promotion seeds; `scenario_state=None` skips registration without raising (AC-4); existing-npcs name resolves at step-2 before promotion (no re-seed). VERIFIED clean.
- `[TYPE]` (type-design disabled — covered here) `_seed_invented_npc_identity` keyword-only, fully annotated `-> None`; `ocean: dict|None ← model_dump()` consistent; `npc_roles: dict[str,str] ← ScenarioRole.Innocent` (str const) consistent. VERIFIED clean.
- `[SIMPLE]` (simplifier disabled — covered by verify-phase simplify + here) Helper is minimal; no over-engineering. The verify-phase efficiency "read-after-write" suggestion was correctly dismissed as behavior-changing.
- `[LOW][TEST]` Vacuous assertion at `test_npc_identity_seed_otel.py:244` — `assert isinstance(promoted.belief_state.beliefs, list)` is structurally always-true (matches lang-review #6). CONFIRMED but LOW: AC-3's three other assertions (npc_roles membership, role value, guilty_npc inequality) carry the test; the weak line doesn't invalidate coverage. Recommend strengthening (add a belief, assert retrievable) in follow-up.
- `[LOW][TEST]` Idempotency guard `if npc.ocean: return` (`narration_apply.py:1135`) has no direct test — the existing idempotency test exercises `resolve_status_target`'s step-2 short-circuit instead. CONFIRMED LOW (the guard is defensive; the real no-re-seed mechanism — step-2 ordering — IS tested). Corroborated by my own analysis.
- `[LOW][TEST]` AC-4 OCEAN check is existence-only (`!= {}`) vs AC-1's per-dimension loop — a no-scenario-specific partial-serialization regression could slip. LOW; recommend a shared `_assert_real_ocean_profile` helper.
- `[LOW][DOC]` Stale module docstring at `test_npc_identity_seed_otel.py:1` — "RED-phase contract" + present-tense "Today that promotion builds an Npc with ocean=None" is misleading now that the code is GREEN. CONFIRMED LOW; recommend recasting to past tense.
- `[LOW][DOC]` Helper docstring (`narration_apply.py` ~1122) says "registered … as innocent" unconditionally; code preserves a pre-existing role. CONFIRMED LOW — note this describes the *correct* no-clobber behavior; docstring should say "as innocent if not already present."
- `[LOW][DOC]` Span docstring (`npc.py` ~762) says `scenario_role` "defaults to innocent"; the param default is `""` (innocent comes from the caller). CONFIRMED LOW.
- `[LOW][RULE]` Log format literal `ocean_seeded=True` (`narration_apply.py:1162`) is hard-coded rather than substituted. CONFIRMED LOW/trivial: the code path is unconditional so the literal matches reality; noted for consistency with the span kwarg.
- `[DISMISSED][RULE]` rule_checker #1 (`if npc.ocean:` → `is not None`): premise is factually wrong — a non-empty dict is truthy regardless of values, so the "all-zeros passes through" claim is false. The only difference is the `{}` case, where the current truthiness check correctly *heals* a forbidden stub rather than preserving it. Current code is correct/preferable. Dismissed with evidence (Python dict truthiness).
- `[DISMISSED][RULE]` rule_checker #3 (`_setup` missing `-> list[dict]`): lang-review #3 explicitly exempts "Internal/private helpers" — `_setup` is underscore-prefixed (private). Dismissed citing the rule's own carve-out.
- `[DEFERRED][RULE]` rule_checker #2 (`resolve_status_target` missing return annotation): rule_checker itself confirms this is pre-existing and not introduced by this diff. Out of scope for 72-9; captured as a non-blocking delivery finding.

### Rule Compliance (lang-review/python.md — exhaustive)

| Rule | Applies to diff | Verdict |
|------|-----------------|---------|
| #1 silent exceptions | helper, span, test | PASS — no try/except, no swallow |
| #2 mutable defaults | all new fns | PASS — keyword-only, `None`/`""` defaults |
| #3 type annotations at boundaries | helper, span, test helpers | PASS for new code (helper `-> None`, span `-> Iterator[Span]`); 1 DEFERRED pre-existing (`resolve_status_target`), 1 DISMISSED (private `_setup` exempt) |
| #4 logging coverage/correctness | helper `logger.info` | PASS (%-style lazy args); 1 LOW (literal `ocean_seeded=True`) |
| #5 path handling | — | N/A (no file I/O) |
| #6 test quality | 7 tests | PASS overall; 1 LOW vacuous line (`isinstance` at :244) |
| #7 resource leaks | span `with` | PASS (context managers) |
| #8 unsafe deserialization | `model_dump()` | PASS (serialize, not deserialize) |
| #9 async pitfalls | async test helpers | PASS (no blocking calls, awaits present) |
| #10 import hygiene | inline imports | PASS (established pattern, no cycles, runtime-used) |
| #11 input validation | name → dict key/span | PASS (validated upstream; no boundary) |
| #12 dependency hygiene | — | N/A (no dep changes) |
| #13 fix-introduced regressions | guard, log | PASS — `if npc.ocean` dismissed as correct; log literal LOW |
| SOUL/CLAUDE: No Silent Fallbacks | inline imports | PASS (fail loud) |
| SOUL/CLAUDE: No Stubbing | OCEAN seed | PASS (real profile, not `{}`) |
| CLAUDE: No Source-Text Wiring Tests | 7 tests | PASS (behavioral + span, zero `read_text`) |
| CLAUDE: OTEL Observability | new span | PASS (every decision emits `npc.identity_seeded`) |

### Devil's Advocate

Argue this code is broken. **The narrator invents a saboteur named "Dr. Mortimer" — the exact display name of the scenario's pre-selected `guilty_npc`.** Could the seed mis-register the culprit as innocent? Trace it: `guilty_npc` is an *id* (e.g. `"dr_mortimer"`), `npc_roles` is keyed by *display name* (`"Dr. Mortimer"`), and `from_genre_pack` already seeded the authored culprit's name into `npc_roles` at bind time. So `if name not in npc_roles` is False → the seed *preserves* the existing Guilty role, never overwriting it. The no-clobber guard saves us. Good — but is it *tested*? No: no test exercises an invented name colliding with an already-registered scenario NPC. That's the untested-guard gap test_analyzer flagged, now doubly relevant. It's LOW because the behavior is provably correct by inspection, but a future refactor that changed `if name not in` to unconditional assignment would clobber the culprit's role and silently break a mystery — and no test would catch it. **What about a confused author?** The helper fires only at the status-mutation promotion seam (`resolve_status_target`). If an invented NPC is named in prose but never takes a status mutation and never enters combat, it stays a pool scaffold and is *never* seeded — it gets no OCEAN, no belief, no scenario role, despite the player caring about it. Is that a hole? Per scope, promotion is the single mechanical-state seam, and 72-1's development pipeline handles interest-driven promotion separately; so this is by-design, not a 72-9 defect — but it means "an invented suspect the table only *talks* to" may never enter the belief graph until something promotes them. Worth a future-work note. **Stressed runtime?** `OceanProfile()` and `ScenarioRole.Innocent` cannot fail; the inline import would raise loudly (not silently) if the module were ever unavailable — fail-loud, correct. **Malicious input?** An adversarial NPC name is inert as a dict key and OTEL string attribute. Conclusion: no break found that rises above LOW; the collision-with-culprit path is correct-but-untested and the talk-only-never-promoted path is by-design. Both recorded as non-blocking follow-ups.

**Handoff:** To SM for finish-story.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/server/narration_apply.py` — added `_seed_invented_npc_identity(npc, member, snapshot, turn_num)` helper (seeds OCEAN, registers scenario `npc_roles`, emits the seed span; guards lineage + idempotency) and wired it into `resolve_status_target` right after `_promote_pool_member_to_npc`. Added `npc_identity_seeded_span` to the spans import.
- `sidequest-server/sidequest/telemetry/spans/npc.py` — new `npc.identity_seeded` span + `SpanRoute` (component `npc_identity`; attrs `npc_name` / `ocean_seeded` / `disposition` / `scenario_registered` / `scenario_role`).
- `sidequest-server/tests/integration/test_npc_identity_seed_otel.py` — cosmetic lint fixes only (Yoda-condition reorder + formatting); test semantics unchanged from TEA's RED contract.

**Implementation approach:** OCEAN seeded as a flat-baseline `OceanProfile().model_dump()` (no jitter generator exists). Disposition untouched (already neutral via 72-2/72-5). Scenario registration mirrors `bind_scenario`: when `scenario_state is not None`, register the NPC name into `npc_roles` as `innocent` (never the pre-selected `guilty_npc`); the `Npc`'s default-factory `BeliefState` is the live mutation surface. Seed fires only for `drawn_from="narrator_invented"` and skips already-seeded NPCs (no clobber). One additive OTEL span; the existing `npc.spawn_disposition` span still fires (72-5 dial preserved).

**Tests:** 7/7 story tests passing (GREEN). Regression sweep: 39/39 passing across `test_npc_spawn_disposition_otel`, `test_pool_disposition_preservation`, `test_npc_wiring`, `test_scenario_bind`, `test_npc_pool_narration_apply`.
**Lint/format:** `ruff check` + `ruff format --check` clean on all three changed files.
**Branch:** `feat/72-9-wire-ocean-disposition-belief-state-invented-npcs` (pushed to origin).

**ACs met:** AC-1 (OCEAN profile) ✓ · AC-2 (neutral disposition) ✓ · AC-3 (scenario registration when active) ✓ · AC-4 (no scenario → still seeded, no scenario wiring) ✓ · AC-5 (identity-seed span from production path) ✓.

**Handoff:** To Reviewer (Portia) for code review.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): `_promote_pool_member_to_npc(member)` (`narration_apply.py:1047`) takes only the `NpcPoolMember` — **no `snapshot`** — so scenario registration (AC-3) into `snapshot.scenario_state.npc_roles` cannot happen inside it as written.
  Affects `sidequest/server/narration_apply.py` (Dev must either thread `snapshot` into `_promote_pool_member_to_npc`, or perform the scenario-registration + identity-seed at the call site `resolve_status_target` at line ~1100 where `snapshot` is in scope). The tests are deliberately agnostic — they drive `resolve_status_target` and assert observable end-state, so either approach passes.
  *Found by TEA during test design.*
- **Question** (non-blocking): Context assumes promotion is the **single** invented→`Npc` production seam, but `Session._npc_from_patch` (`session.py:1501`) is a second materialization path. It is MM/creature-shaped (not `narrator_invented` lineage), so it should be out of scope — but if Dev discovers a second path that mints an `Npc` from a `narrator_invented` scaffold, both must route through the same seed (one seam, not two).
  Affects `sidequest/server/narration_apply.py` / `sidequest/game/session.py` (verify no second invented→Npc path bypasses the seed).
  *Found by TEA during test design.*
- **Improvement** (non-blocking): The existing `npc.spawn_disposition` span already fires at promotion (`narration_apply.py:1089`). The new `npc.identity_seeded` span is additive — Dev should keep both firing (spawn_disposition for the disposition dial, identity_seeded for OCEAN/belief/scenario), not collapse them, so 72-5's GM-panel dial is not regressed.
  Affects `sidequest/telemetry/spans/` + the promotion path.
  *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking): The identity seed fires only from the single production promotion path (`resolve_status_target` → `_seed_invented_npc_identity`). If a *second* invented→`Npc` production path is added later, it must also call `_seed_invented_npc_identity` or invented NPCs minted that way will silently bypass OCEAN/scenario seeding. Affects `sidequest/server/narration_apply.py` (any new invented-promotion seam must route through the helper). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `belief_state` for invented NPCs is registered as a live surface with zero initial beliefs; ADR-053 gossip/questioning (marked `partial`) will populate it. A future enhancement could seed an initial "observed-at-location" belief for invented suspects so they enter the clue graph with a stake. Affects `sidequest/server/narration_apply.py::_seed_invented_npc_identity`. *Found by Dev during implementation.*
- **Improvement** (non-blocking): The scenario role is stored as `ScenarioRole.Innocent` (`"innocent"`, lowercase) per the enum. Any GM-panel consumer that expects title-case role labels should normalize. Affects GM-panel scenario role rendering (consumer-side). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Doc/test polish bundle — stale "RED-phase contract" module docstring (`tests/integration/test_npc_identity_seed_otel.py:1`), the vacuous `assert isinstance(beliefs, list)` line (`:244`, lang-review #6), and AC-4's existence-only OCEAN check could each be tightened. None affect correctness. Affects `tests/integration/test_npc_identity_seed_otel.py` (recast docstring to past tense, strengthen the two assertions). *Found by Reviewer during code review.*
- **Gap** (non-blocking): The `if npc.ocean: return` idempotency guard and the invented-name-collides-with-scenario-culprit path are both correct-by-inspection but untested; a future refactor could regress either silently. Affects `tests/integration/test_npc_identity_seed_otel.py` (add a direct guard test + a name-collision test). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing — `resolve_status_target` (`sidequest/server/narration_apply.py`) lacks a return type annotation (`Character | Npc | None`). Not introduced by 72-9. Affects `sidequest/server/narration_apply.py` (add return annotation in a cleanup pass). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): An invented NPC the table only *talks to* (no status mutation / combat) never reaches the promotion seam, so it is never identity-seeded until something promotes it. By-design per scope (72-1's interest-driven promotion is the other half), but worth confirming the development pipeline eventually promotes talked-to NPCs. Affects the 72-1 development pipeline interaction. *Found by Reviewer during code review.*
- **Doc** (non-blocking): Two production docstrings slightly overstate behavior — helper says "registered as innocent" (code preserves pre-existing role), span says `scenario_role` "defaults to innocent" (param default is `""`). Affects `sidequest/server/narration_apply.py` + `sidequest/telemetry/spans/npc.py` (tighten docstring wording). *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **AC-2 (neutral disposition) is covered by an already-green guard test, not a red test**
  - Spec source: context-story-72-9.md, AC-2
  - Spec text: "The same `Npc` spawns with a **neutral** `Disposition` (value 0 → `Attitude.neutral`), explicitly *not* the `-20` born-hostile creature default."
  - Implementation: `test_invented_npc_spawns_neutral_disposition` passes on the current tree because 72-2's `_promote_pool_member_to_npc` already carries `member.disposition` (default 0) through promotion. It is included as a regression guard, not a RED driver.
  - Rationale: AC-2's behavior is already live via 72-2/72-5; re-implementing it is out of 72-9 scope (context Scope Boundaries). The guard locks the invariant so 72-9's OCEAN/belief seeding cannot perturb it.
  - Severity: minor
  - Forward impact: none — Dev need not touch the disposition default; only must not regress it.

- **"Fail loud when OCEAN model unavailable" edge is not separately tested**
  - Spec source: context-story-72-9.md, "Edge cases to cover in tests" + Technical Guardrails "No Silent Fallbacks"
  - Spec text: "OCEAN model unavailable / scenario shape mismatch → **fail loud**, do not leave `ocean=None` silently."
  - Implementation: No test forces an OCEAN-import failure. Instead the positive No-Silent-Fallback contract is asserted via AC-4/AC-5: when a scenario is active `scenario_registered` must be explicitly `True`, and `ocean_seeded` `True` — never a silent `None`/`False`.
  - Rationale: Per context lines 94–98, `OceanProfile` is a plain always-importable pydantic model; forcing `ImportError` would test a monkeypatch, not production behavior. The realistic failure (scenario-shape mismatch) cannot be driven deterministically in red without coupling to internal shapes — that would violate "No Source-Text Wiring Tests" in spirit.
  - Severity: minor
  - Forward impact: Reviewer should confirm the implementation raises (not swallows) if OCEAN/scenario seeding genuinely cannot proceed.

- **(verify) Declined two high-confidence simplify findings**
  - Spec source: verify-phase simplify fan-out (reuse + efficiency teammates)
  - Spec text: "For each finding with confidence: high … apply the suggestion."
  - Implementation: Applied 0 of 2. (1) reuse "extract duplicated test helpers" — deferred to existing backlog **71-34** (Extract shared OTEL watcher-test harness); would require editing the 72-5 sibling test outside this diff. (2) efficiency "collapse read-after-write on `npc_roles[name]`" — dismissed as a behavior-changing false positive: the read-back preserves a pre-existing role (no-clobber) rather than overwriting.
  - Rationale: The verify workflow's "apply high-confidence fixes" assumes the fix is behavior-preserving and in-scope. Neither held: one regresses the no-clobber guard, the other is a tracked separate story touching a sibling file.
  - Severity: minor
  - Forward impact: 71-34 will retire the test-helper duplication across the OTEL integration tests.

- **New OTEL watcher-event contract names are TEA-chosen (no AC pre-specified them)**
  - Spec source: context-story-72-9.md, AC-5 + epic OTEL span inventory (72-9 row)
  - Spec text: "Add **one new** OCEAN/belief-seed span … recording: npc name, `ocean` seeded (bool/source), disposition value, and `scenario_registered` (bool) + scenario_id/role when a scenario is active."
  - Implementation: Tests pin the routed `state_transition` event to `component="npc_identity"`, `field="npc.identity_seeded"`, with attributes `npc_name` / `ocean_seeded` / `disposition` / `scenario_registered` / `scenario_role`. Names documented in the test-file header.
  - Rationale: TDD requires a concrete observable contract; the AC specified the *shape* but not the *names*. Mirrors the existing `npc.spawn_disposition` SpanRoute pattern in `telemetry/spans/disposition.py`.
  - Severity: minor
  - Forward impact: Dev must register a `SpanRoute` that emits exactly these names/attrs. If Dev/Reviewer prefer different names, update the constant `IDENTITY_SEEDED_FIELD` and the AC-5 assertions in lockstep.

- **Lineage guard encodes "invented-only" as a hard contract**
  - Spec source: context-story-72-9.md, Scope Boundaries ("fires only for the `drawn_from="narrator_invented"` lineage")
  - Spec text: "Guard the new seed so it fires only for the **`drawn_from="narrator_invented"`** lineage and skips entries that already hold a non-default OCEAN/belief."
  - Implementation: `test_world_authored_promotion_does_not_fire_invented_seed` asserts a `world_authored` pool-member promotion does NOT emit `npc.identity_seeded`.
  - Rationale: Directly from the scope statement; prevents double-wiring authored NPCs that get identity through `world_materialization`.
  - Severity: minor
  - Forward impact: If the team later decides authored pool promotions should also receive OCEAN, this guard must be revisited.

### Dev (implementation)
- **Seeded at the `resolve_status_target` call site, not by threading `snapshot` into `_promote_pool_member_to_npc`**
  - Spec source: context-story-72-9.md, Technical Guardrails + TEA Delivery Finding (Gap)
  - Spec text: "An invented person becomes an `Npc` only when it first needs mechanical state, via `_promote_pool_member_to_npc` … This is the primary wiring target." (The TEA finding noted that helper takes no `snapshot`, so scenario registration can't live inside it.)
  - Implementation: Added a new `_seed_invented_npc_identity(npc, member, snapshot, turn_num)` helper called from `resolve_status_target` immediately after `_promote_pool_member_to_npc`, where `snapshot`/`turn_num` are in scope. `_promote_pool_member_to_npc`'s signature is unchanged.
  - Rationale: Context explicitly granted latitude on the seam ("Verify whether 72-9 should seed at mint or only at promotion"); the call-site keeps the promotion helper pure and avoids rippling its signature to all callers. Tests drive `resolve_status_target` and are agnostic to which approach is used.
  - Severity: minor
  - Forward impact: Any *future* invented→`Npc` production path (e.g. if one is added beyond `resolve_status_target`) must also call `_seed_invented_npc_identity`, or it will bypass the seed. Flagged as a finding.

- **OCEAN seeded as a flat baseline (`OceanProfile()`, all 5.0), not jittered**
  - Spec source: context-story-72-9.md, Technical Guardrails (OCEAN)
  - Spec text: "a flat baseline `OceanProfile()` (all 5.0) serialized via `.model_dump()`, or a deterministic-jittered profile. Either is acceptable … as long as it is a real value, not `None`."
  - Implementation: `npc.ocean = OceanProfile().model_dump()` — flat baseline.
  - Rationale: No random/jitter/shift generator exists (ocean.py docstring); a flat baseline is deterministic, honest, and non-stub. 72-1's development pipeline drifts personality from there.
  - Severity: minor
  - Forward impact: none — values are real and in-band; a future jitter policy can replace the baseline without changing the wiring or span contract.

- **No initial beliefs seeded onto the invented NPC's `belief_state`**
  - Spec source: context-story-72-9.md, AC-3 + Technical Guardrails (belief_state)
  - Spec text: "its `belief_state` is the live `BeliefState()` mutation surface (gossip/questioning can later add beliefs via `add_belief`)."
  - Implementation: The `Npc` already carries a live empty `BeliefState` (default_factory). Scenario registration adds the `npc_roles` entry only; no `BeliefFact`/`BeliefSuspicion` is seeded (unlike authored NPCs, which have pack-defined `initial_beliefs`).
  - Rationale: An invented mid-session walk-on has no authored beliefs to seed; AC-3 requires the *live surface* + `npc_roles` registration, both satisfied. Seeding fabricated beliefs would be improvisation, not wiring.
  - Severity: minor
  - Forward impact: If a follow-up wants invented suspects to carry an initial observation belief, that's an additive enhancement on the same surface.

### Reviewer (audit)

All logged deviations reviewed and stamped:

- **TEA: AC-2 covered by an already-green guard** → ✓ ACCEPTED: correct — 72-2/72-5 already seed neutral disposition; treating AC-2 as a regression guard is sound.
- **TEA: "fail loud when OCEAN unavailable" not separately tested** → ✓ ACCEPTED: `OceanProfile` is an always-importable pydantic model; the inline import would raise loudly. Forcing an ImportError would test a monkeypatch, not the code. Positive contract covered by AC-4/AC-5.
- **TEA: new OTEL contract names TEA-chosen** → ✓ ACCEPTED: TDD requires a concrete observable contract; names mirror the `npc.spawn_disposition` precedent and match the implementation.
- **TEA: lineage guard encodes "invented-only"** → ✓ ACCEPTED: directly from the story scope.
- **TEA: declined two verify-phase simplify findings** → ✓ ACCEPTED: the read-after-write dismissal is correct (behavior-changing); the test-helper dedup correctly deferred to backlog 71-34.
- **Dev: seeded at call site, not by threading snapshot into `_promote_pool_member_to_npc`** → ✓ ACCEPTED: context granted seam latitude; call-site keeps the promotion helper's signature stable and tests are agnostic.
- **Dev: OCEAN flat baseline (not jittered)** → ✓ ACCEPTED: no jitter generator exists; flat baseline is the honest, deterministic seed.
- **Dev: no initial beliefs seeded** → ✓ ACCEPTED: an invented walk-on has no authored beliefs; seeding fabricated beliefs would be improvisation. The live `BeliefState` surface + `npc_roles` registration satisfy AC-3.

Undocumented deviations found by Reviewer:
- **Invented name colliding with a scenario's already-registered NPC:** Spec implies invented walk-ons register as `innocent`; code instead *preserves* a pre-existing role (correct no-clobber, protects the culprit's Guilty role). Behavior is correct-but-untested. Severity: L. Recorded as a non-blocking delivery finding; no code change required.

### Architect (reconcile)

Reviewed all prior deviation entries (TEA test-design ×4 + verify ×1, Dev implementation ×3, Reviewer audit stamps ×8 + 1 undocumented). All cite a real spec source (`context-story-72-9.md`, which exists), quote accurate spec text, describe implementation matching the merged code, and carry all 6 fields. No corrections needed. One deviation present in the Architect spec-check assessment was not yet formalized in this log — added below in full 6-field format so the manifest is self-contained.

- **Identity-seed OTEL span omits `scenario_id`**
  - Spec source: `sprint/context/context-story-72-9.md`, AC-5
  - Spec text: "A behavioral test drives the real invented-mint→mechanical flow … and asserts the new OCEAN/belief-seed span fired with the expected attributes (npc name, ocean-seeded, disposition value, scenario_registered bool + scenario_id/role when applicable)."
  - Implementation: The `npc.identity_seeded` span (`sidequest/telemetry/spans/npc.py`) carries `npc_name`, `ocean_seeded`, `disposition`, `scenario_registered`, and `scenario_role` — but **not** `scenario_id`. Verified during spec-check that `ScenarioState` (`sidequest/game/scenario_state.py`) has no `scenario_id` field; the id lives at the binding layer (`bind_scenario` returns it to be stashed in `world_scenarios`, not on `snapshot.scenario_state`), so it is not reachable at the `_seed_invented_npc_identity` seam without new plumbing.
  - Rationale: Threading the scenario id into the snapshot/seam exceeds a 5-pt wiring story's scope. `scenario_registered` (bool) + `scenario_role` already satisfy the lie-detector's core question (did the wiring fire, in what role). The authoritative TEA test contract did not require `scenario_id`.
  - Severity: minor
  - Forward impact: If the GM panel later needs per-scenario attribution for invented NPCs, a follow-up must surface the scenario id onto `ScenarioState` (or thread it through the seam) and add it to the span. No sibling story currently depends on it.

- **AC accountability:** All five derived ACs (AC-1…AC-5) were delivered and verified GREEN; none were deferred or descoped. The ac-completion gate recorded no deferrals, so there are no deferral justifications to cross-check against the Reviewer's findings (no-op). The single span-attribute partial above is an attribute-level omission within a delivered AC, not a deferred AC.

No additional deviations found beyond the entry above.

## References

- **ADR-042:** OCEAN Personality Live Evolution (drift)
- **ADR-020:** NPC Disposition System
- **ADR-053:** Scenario System (Clue Graph, Belief State, Gossip Propagation) (partial)
- **ADR-014:** Diamonds and Coal — NPC Promotion on Player Interest
- **ADR-091:** Culture-Corpus + Markov Naming

## Related Stories (Epic 72)

- 72-1: Revive dormant development pipeline (DONE)
- 72-2: Preserve disposition on promotion (DONE)
- 72-3: MM NPC provenance through injection seam (backlog)
- 72-4: Route narrator-invented NPC names through namegen (DONE)
- 72-5: Fix born-hostile disposition default (DONE)
- 72-6: Cap npc_pool growth + prune stale scaffolds (backlog)
- 72-7: Apply NPC identity drift — overwrite canonical pronoun/role (backlog)
- 72-8: Stamp last_seen_turn/location on encounter presence (backlog)
- 72-10: observation_pending gate-ordering assert (backlog)