---
story_id: "86-7"
jira_key: ""
epic: "86"
workflow: "tdd"
---
# Story 86-7: Command Points economy + Crisis table

## Story Details
- **ID:** 86-7
- **Jira Key:** (none — pre-Jira epic)
- **Workflow:** tdd
- **Stack Parent:** 86-6 (War Rig table-game core, completed 2026-06-09)
- **Repos:** sidequest-server (gitflow, develop), sidequest-content (gitflow, develop)
- **Branch Strategy:** gitflow — feature branches from develop (branching will occur in subrepo checkouts)
- **Orchestrator:** trunk-based (main only) — sprint tracking and context files on orchestrator/main

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-09T08:41:51Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-09 | 2026-06-09T07:49:53Z | 7h 49m |
| red | 2026-06-09T07:49:53Z | 2026-06-09T08:01:53Z | 12m |
| green | 2026-06-09T08:01:53Z | 2026-06-09T08:13:06Z | 11m 13s |
| review | 2026-06-09T08:13:06Z | 2026-06-09T08:22:52Z | 9m 46s |
| green | 2026-06-09T08:22:52Z | 2026-06-09T08:31:10Z | 8m 18s |
| review | 2026-06-09T08:31:10Z | 2026-06-09T08:41:51Z | 10m 41s |
| finish | 2026-06-09T08:41:51Z | - | - |

## Sm Assessment

Story 86-7 implements the SWN-style **Command Points economy + d10 Crisis table** for the War Rig crew table-game (epic 86, road_warrior → CWN rig combat). It is a direct continuation of 86-6 (War Rig crew table-game core, completed 2026-06-09 — its parent dependency), and reuses the existing `rig_damage_tiers` / `rig_crash` infrastructure rather than introducing a parallel damage model.

**Scope (derived from title + epic-86 context; YAML ACs were empty):**
- Per-vessel **Command Points** shared resource with the three spend actions: *Do Your Duty*, *Above and Beyond*, *Support Department*.
- **d10 Crisis table** with continuing/acute outcomes and the *Deal With a Crisis* action, cascading into the two-pool rig damage model.
- OTEL is load-bearing per project doctrine: `command_points.*` and `crisis` spans MUST fire so the GM panel can verify the mechanics engaged (not narrator improvisation).

**Routing:** `tdd` (phased) — RED (tea) → GREEN (dev) → REVIEW (reviewer) → FINISH (sm). Feature branch `feat/86-7-command-points-crisis-table` cut from `develop` in both sidequest-server and sidequest-content. Orchestrator stays on main for sprint/context tracking.

**Handoff to TEA (Mr. Praline):** Write acceptance-criteria tests covering the CP spend actions, the Crisis table resolution, the reuse of rig_damage_tiers/rig_crash, and the OTEL span assertions. Story context with full ACs lives at `sprint/context/context-story-86-7.md`.

## TEA Assessment

**Tests Required:** Yes
**Status:** RED (25 failing, 1 passing) — verified via testing-runner (RUN_ID 86-7-tea-red)

**Test Files:**
- `tests/game/table/test_war_rig_command.py` — unit contract: CP pool construction + fail-loud bounds, the three CP action costs (duty=0, a&b=1, support=1), spend depletion + d6 bonus, **fail-loud on over-spend and unknown action** (No Silent Fallbacks), cross-round persistence, d10 Crisis table shape (faces 1–10, both continuing+acute), `roll_crisis` lookup, `deal_with_crisis` success/fail, continuing-crisis escalation feeding the 86-2 two-pool Hull, acute-crisis non-escalation. (17 tests)
- `tests/integration/test_war_rig_command_otel.py` — OTEL through the **real** TracerProvider + WatcherSpanProcessor + watcher_hub route (same harness as the 86-6 integration suite): `command_points.action_taken`/`delta` with vessel_id+seat, the free-action-emits-no-delta negative case, `crisis.rolled`/`resolved`/`escalated`, the reuse proof (escalation drives `rig_pool.delta -2`), and the **MANDATORY production-path wiring test** — a `war_rig_crew` round through `resolve_table` must surface BOTH span families. (6 tests)
- `tests/genre/test_war_rig_command_content.py` — road_warrior `rules.yaml`: war_rig confrontation declares `above_and_beyond`/`support_department`/`deal_with_crisis` beats without regressing the four 86-6 station verbs. (3 tests; 1 is the green regression guard)

**Tests Written:** 26 tests covering AC1 (CP economy), AC2 (Crisis table), AC3 (OTEL wiring).

### Rule Coverage (lang-review/python.md)

| Rule | Test(s) | Status |
|------|---------|--------|
| #1 Silent exception swallowing | `test_spending_more_than_the_pool_holds_fails_loud`, `test_unknown_cp_action_fails_loud` | failing (RED) |
| #3 Type annotation gaps at boundaries | `test_command_point_pool_blank_vessel_id_fails_loud`, `..._current_cannot_exceed_max`, `..._cannot_be_negative` | failing (RED) |
| #6 Test quality (no vacuous asserts) | self-checked — every test asserts a specific value/state, not a bare truthy/`is_some` | n/a |
| #11 Input validation at boundaries | CP pool validators + fail-loud spend (above) | failing (RED) |
| #13 Fix-introduced regressions (one-path validation) | `test_do_your_duty_emits_action_taken_but_no_delta`, `test_failed_acute_crisis_does_not_escalate`, `test_resolved_crisis_does_not_escalate` | failing (RED) |

**Rules checked:** 5 of 13 applicable lang-review rules have dedicated test coverage (the others — mutable defaults, async gather, deserialization, etc. — are not exercised by this pure-logic + OTEL surface).
**Self-check:** 0 vacuous assertions; every test pins a concrete value, count, or raise.

**Wiring test:** `test_crewed_round_fires_both_command_and_crisis_span_families` drives the production `resolve_table` path (not the CP/crisis functions in isolation) and asserts both span families surface through the real watcher route — satisfies "Every Test Suite Needs a Wiring Test" and the OTEL lie-detector mandate.

**Handoff:** To Dev (Bicycle Repair Man) for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Tests:** 46/46 passing (GREEN) — verified via testing-runner (RUN_ID 86-7-dev-green); regression sweep 1336 passed / 49 skipped / 0 failed across table+telemetry+genre.
**Branch:** `feat/86-7-command-points-crisis-table` (pushed: sidequest-server + sidequest-content)

**Files Changed:**
- **NEW** `sidequest-server/sidequest/game/war_rig_command.py` — `CommandPointPool` (vessel-scoped, fail-loud bounds) + CP action constants/costs + `spend_command_points` (fail-loud over-spend/unknown-action, +1d6 on above_and_beyond); `CrisisEntry`/`CrisisType`/`CRISIS_TABLE` (d10, continuing+acute) + `roll_crisis` + `deal_with_crisis` (continuing-fail escalates into the 86-2 `WarRigHull` via `apply_delta`; acute is one-round).
- **NEW** `sidequest-server/sidequest/telemetry/spans/command_points.py` — routed `command_points.action_taken` / `command_points.delta` spans (component="command_points").
- **NEW** `sidequest-server/sidequest/telemetry/spans/crisis.py` — routed `crisis.rolled` / `crisis.resolved` / `crisis.escalated` spans (component="crisis").
- `sidequest-server/sidequest/telemetry/spans/__init__.py` — register the two new span modules.
- `sidequest-server/sidequest/game/table/types.py` — add `TableState.shared_state: dict` (the shared-CP seam TEA flagged; poker/auction unaffected).
- `sidequest-server/sidequest/game/table/war_rig.py` — `custom_beat` dispatches the CP verbs + `deal_with_crisis` (get-or-seed shared CP pool on `TableState.shared_state`, synthesize `vessel_id`); still fails loud on unknown verbs.
- `sidequest-content/genre_packs/road_warrior/rules.yaml` — war_rig confrontation gains `above_and_beyond`/`support_department`/`deal_with_crisis` intent_verbs + beats.
- `tests/game/table/test_war_rig_command.py` — fixed a TEA bonus-sampling test that drained one shared pool across 20 spends (it correctly hit the new fail-loud guard); now samples a fresh 1-CP pool per seed.

**AC coverage:** AC1 (CP economy) ✓, AC2 (Crisis table + escalation→two-pool Hull) ✓, AC3 (OTEL via real watcher route + production-path wiring test) ✓.

**Handoff:** To Reviewer (The Argument Professional) for code review.

### Dev Rework — Round 1 (reviewer REJECT addressed)

**Tests:** 53/53 war-rig green; 1340 regression sweep / 49 skipped / 0 failed; ruff + pyright clean. Commit `851719a3` (server) pushed.

**[HIGH] resolved — Hull now actually damaged in-round.** Wired the crew's shared `WarRigHull` onto `TableState.shared_state` (new `_shared_hull` get-or-seed, mirroring the CP pool seam) and pass it to `deal_with_crisis` in `custom_beat`. A failed continuing crisis in a live `war_rig_crew` round now drives a real `rig_pool.delta` and drops the shared Hull — `crisis.escalated` is no longer a consequence-free span. AC2 is wired end-to-end, not just at the function level. Proven by new deterministic integration test `test_in_round_continuing_crisis_escalation_damages_the_shared_hull` (seed 0 → Hull 6→4, rig_pool.delta -2).
**[HIGH] resolved — no more overclaiming docs/content.** Corrected the 3 docstrings (`war_rig_command.py` module + `deal_with_crisis` + `crisis.py`) and `CrisisEntry` to state hull damage is conditional on a supplied Hull (which the round supplies); the player-facing `rules.yaml` "the Hull pays for it" is now *true* (Hull is wired) so it needed no change.
**[MEDIUM] resolved — wiring test tightened.** `test_crewed_round_fires_both_command_and_crisis_span_families` now asserts specific ops (`action_taken`, `rolled`, `resolved`) fired, not just component membership — a no-op stub no longer passes.
**[MEDIUM] resolved — cross-round CP persistence integration test** (`test_command_points_persist_across_two_resolve_table_rounds`: 4→3→2 across two `resolve_table` calls via `shared_state`).
**[MEDIUM] resolved — DC boundary** (`total==dc` passes / `total==dc-1` fails) + **support_department OTEL** (action_taken+delta) + **`bonus==0`** assertion.
**[LOW] resolved —** `__all__` adds `WAR_RIG_COMMAND_VERBS`/`WAR_RIG_DEAL_WITH_CRISIS`; `CommandPointPool(max=0)` fail-loud + negative-`ability_mod` arithmetic tests added.
**Accepted as 86-5 (delivery findings, not fixed):** graceful insufficient-CP per-commit rejection (still fail-loud-aborts the round); `crisis.escalated`-before-`crisis.resolved` ordering; `shared_state` non-JSON-serializability (TableState remains ephemeral).

**Handoff:** To Reviewer for re-review.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (1342 passed/0 failed/49 skipped, ruff+pyright clean, 0 smells) | 0 findings, 4 notes | notes corroborated (escalate-ordering, shared_state serializability, ability_mod=0, do_your_duty) |
| 2 | reviewer-edge-hunter | N/A (disabled) | Skipped (disabled via settings) | N/A | self-covered — see [EDGE] obs (insufficient-CP mid-round abort) |
| 3 | reviewer-silent-failure-hunter | N/A (disabled) | Skipped (disabled via settings) | N/A | self-covered — see [SILENT] obs (crisis.escalated fires with no consequence) |
| 4 | reviewer-test-analyzer | Yes | findings | 8 | confirmed 5, deferred 3 |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 6 (all one root: hull-not-wired-in-round vs docstrings/content) |
| 6 | reviewer-type-design | N/A (disabled) | Skipped (disabled via settings) | N/A | self-covered — rule-checker rule-3 + my read; types clean (pydantic + frozen dataclasses) |
| 7 | reviewer-security | N/A (disabled) | Skipped (disabled via settings) | N/A | self-covered — rule-checker rule-11 + my read; no untrusted-input/SQL/HTML/path surface |
| 8 | reviewer-simplifier | N/A (disabled) | Skipped (disabled via settings) | N/A | self-covered — mirrors war_rig_combat precedent; no over-engineering |
| 9 | reviewer-rule-checker | Yes | findings (3 violations / 87 instances) | 3 | confirmed 2 (__all__, support bonus), 1 N/A (private-const note) |

**All received:** Yes (4 enabled returned; 5 disabled pre-filled as Skipped and self-assessed)
**Total findings:** 9 confirmed, 0 dismissed, 4 deferred (LOW coverage gaps)

## Rule Compliance (lang-review/python.md, exhaustive per rule-checker + my audit)

| Rule | Verdict | Evidence |
|------|---------|----------|
| #1 Silent exceptions | ✓ compliant | All guards raise ValueError (`war_rig_command.py:107,112`; `war_rig.py:154`); no bare except/suppress in diff |
| #2 Mutable defaults | ✓ compliant | pydantic models + frozen dataclasses; `TableState.shared_state` uses `Field(default_factory=dict)` (`types.py:60`); `hull=None` immutable default |
| #3 Type annotations at boundaries | ✓ compliant | All public fns fully annotated incl. return types; only `_SHARED_CP_KEY` private const unannotated (below boundary threshold) |
| #4 Logging | ✓ compliant | OTEL-only observability (project pattern); no stdlib logging, no f-strings-in-log |
| #5 Path handling | ✓ compliant | no file I/O in production diff; test uses `Path(...).resolve()` |
| #6 Test quality | ⚠ 2 gaps | `test_support_department` omits `bonus==0`; wiring test asserts component-membership not ops (see [TEST]) — not vacuous, but under-asserting |
| #7 Resource leaks | ✓ compliant | every `Span.open`/`table_*_span` uses `with` |
| #8 Unsafe deserialization | ✓ compliant | no pickle/yaml.load/eval/exec/shell; pydantic for structured input |
| #9 Async pitfalls | ✓ compliant | production code synchronous; test `asyncio.sleep(0.05)` is the established 86-6 flush barrier (not sleep(0)) |
| #10 Import hygiene | ⚠ 1 gap | `war_rig.py:170` `__all__` omits `WAR_RIG_COMMAND_VERBS`/`WAR_RIG_DEAL_WITH_CRISIS`; spans `__init__` star-imports are the established package pattern (new modules define `__all__`) |
| #11 Input validation | ✓ compliant | allowlist action guard + pool bounds validator; no untrusted-input boundary in diff |
| #12 Dependency hygiene | ✓ compliant | stdlib + pydantic (existing core dep); no new deps |
| #13 Fix-introduced regressions | ✓ compliant | custom_beat restructure preserves 86-6 station-verb semantics; `shared_state` addition leaves poker/auction untouched (regression sweep 1336 green) |

## Reviewer Observations

- **[SILENT][HIGH] `crisis.escalated` fires in the production round with no mechanical consequence** — `war_rig.py:146-152`: `custom_beat` calls `deal_with_crisis(...)` with **no `hull=`**, so `hull` is `None`. A failed continuing crisis therefore emits `crisis.escalated` with `hull_delta=0` and **fires no `rig_pool.delta`** — the escalation is observable-but-inert. This is the exact failure mode the OTEL lie-detector doctrine exists to catch: a span asserting a mechanic that did not happen. AC2 ("Crisis escalation feeds into the two-pool rig damage model") is satisfied only at the function level, not in the production round.
- **[DOC][HIGH] Three docstrings + player-facing content promise hull damage that the production path never performs** — `war_rig_command.py` module docstring + `deal_with_crisis` docstring + `crisis.py` module docstring state the hull penalty "is applied" unconditionally; `road_warrior/rules.yaml` `deal_with_crisis` `risk:` tells the **player** "Fail a continuing crisis and it escalates — the Hull pays for it." In the shipped engine the Hull does not pay. (comment-analyzer ×6, all this root.)
- **[TEST][MEDIUM] The mandatory wiring test under-asserts** — `test_crewed_round_fires_both_command_and_crisis_span_families` checks only `"command_points" in components` / `"crisis" in components`. A no-op stub emitting a bare event with no `op` would pass. The 86-6 precedent (`test_war_rig_crew_combat.py`) asserts specific ops AND counts. This looseness is *why* the [SILENT] gap above slipped GREEN — the AC3 wiring proof can't see it. (test-analyzer #1.)
- **[TEST][MEDIUM] No cross-round CP-persistence integration test** — AC1 ("CP persists across rounds") is proven only on the raw pool object (`test_command_points_persist_and_deplete_across_rounds`), never through two `resolve_table` calls on one `TableState` via `shared_state`. The production persistence mechanism is untested. (test-analyzer #8.)
- **[TEST][MEDIUM] DC boundary untested** — `deal_with_crisis` success uses only `dc=0` (always passes) and `dc=99` (always fails); `total == dc` (the exact `>=` boundary) is never exercised, so a `>=`→`>` off-by-one would not be caught. (test-analyzer #3.)
- **[TEST][MEDIUM] `support_department` under-covered** — no OTEL test that its `delta` surfaces (only `above_and_beyond` is OTEL-tested), and no `result.bonus == 0` assertion — its only mechanical distinction from `above_and_beyond` (no d6) is unpinned. (test-analyzer #2/#6 + rule-checker.)
- **[EDGE][MEDIUM] Insufficient-CP mid-round aborts the whole cooperative round** — `engine.py:176` calls `game.custom_beat` with no surrounding try/except (`_apply_commit`/`_apply_signature_beat`). If a seat commits an unaffordable CP verb, `spend_command_points` raises and the entire round resolution aborts for **all** seats. Fail-loud is doctrinally defensible, but a live confrontation needs graceful per-commit rejection (validate affordability before `resolve_table`). Reasonable 86-5 scope — flagged, not blocking.
- **[RULE][LOW] `__all__` incomplete** — `war_rig.py:170` omits the new public constants `WAR_RIG_COMMAND_VERBS` and `WAR_RIG_DEAL_WITH_CRISIS` (parallel to the listed `WAR_RIG_STATION_VERBS`).
- **[VERIFIED] CP economy fail-loud is real and correct** — `war_rig_command.py:107` (unknown action) and `:112` (cost > current) both `raise ValueError`, and `test_spending_more_than_the_pool_holds_fails_loud` asserts the pool is left untouched post-reject. Complies with No-Silent-Fallbacks. Evidence: pool unchanged assertion at the test + the guard precedes mutation.
- **[VERIFIED] `shared_state` addition does not regress poker/auction** — `types.py:60` adds `shared_state: dict = Field(default_factory=dict)`; `extra="forbid"` intact (explicit field); regression sweep 1336 passed across `tests/game/table/`. Evidence: preflight green + the default_factory (not class-level mutable).
- **[VERIFIED] `do_your_duty` 0-cost path emits action_taken but no delta** — `war_rig_command.py` emits `delta` only under `if cost > 0`; `test_do_your_duty_emits_action_taken_but_no_delta` pins the negative case. Correct per AC3. Evidence: the guarded emit + the negative-case test.

### Devil's Advocate

Assume this code is theater. The whole epic exists because Sebastien and Jade carried a 140-turn game with the crunch *broken* and felt its absence — so the one thing 86-7 must not do is *look* like crunch while doing nothing. Now watch a real table: the road-boss calls "Deal With a Crisis," the engine rolls a continuing `engine_fire` (DC 11), the crew's `ability_mod` is hardcoded to 0, so a d10 almost always fails, `crisis.escalated` fires, the GM panel lights up "ESCALATED — engine fire" … and the Hull sits at full. The narrator, reading the span, writes "flames tear through the cab, the rig shudders" — and mechanically nothing happened. That is precisely the El Dorado the project is trying to escape: convincing narration with zero mechanical backing. The player-facing `risk` text even *promises* "the Hull pays for it." It doesn't. A mechanics-first player checks the Hull number, sees 6/6 after a "catastrophic" escalation, and learns the system lies — the worst possible outcome for this audience.

What would a confused author do? Jade adds a new crisis to `CRISIS_TABLE` with `hull_penalty=5`, playtests, sees `crisis.escalated` fire, and ships it believing it bites — because the docstrings told her it "is applied." She has no signal the production round drops the hull on the floor. What would a stressed engine do? Five seats each commit `above_and_beyond` against a 4-CP pool; the fifth `spend_command_points` raises mid-`resolve_table` and the entire cooperative round dies — one player's over-reach nukes the table's turn, the opposite of the Guitar-Solo "keep the band playing" principle. And the wiring test that is supposed to be the lie-detector? It only checks that *some* `command_points` and *some* `crisis` event appeared — it would pass against a stub that emits one empty span and never touches CP or the Hull at all. The test that exists to prove the wiring is itself too weak to prove the wiring. None of this is a crash or a security hole — it's worse for *this* project: it's crunch that isn't there, wearing a span that says it is.

## Round 1 Review Verdict (REJECTED — superseded; see the APPROVED assessment below)

**Verdict:** REJECTED (round 1 — addressed in rework; see the round-2 APPROVED assessment)

The CP economy and the crisis *logic* are solid, well-typed, fail-loud, and cleanly unit-tested — genuinely good work at the function level. But the story ships a **crisis escalation that fires its OTEL span with no mechanical consequence in the production round**, while three docstrings and the **player-facing** `rules.yaml` promise the Hull takes damage. For a project whose load-bearing principle is "is the crunch actually firing, or is the narrator improvising?", a span that lies is a blocking defect — and the mandatory wiring test is too loose to catch it. This is a focused, fair rework, not a demand for 86-5 calibration work.

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [HIGH] | Continuing-crisis escalation has no effect in the production round (hull=None) yet docstrings + player content claim the Hull is damaged — a span fires without its mechanic (AC2 half-wired) | `war_rig.py:146-152`; `war_rig_command.py` module+`deal_with_crisis` docstrings; `crisis.py` docstring; `rules.yaml` `deal_with_crisis` `risk:` | **Either** (a) wire the shared `WarRigHull` through `TableState.shared_state` (same seam as the CP pool) so an in-round continuing-crisis failure calls `apply_delta`, with an integration test asserting `rig_pool.delta` fires from the in-round escalation — **or** (b) formally amend scope to 86-5 AND correct every overclaim: qualify the 3 docstrings ("applied *when a hull is supplied*"), fix the player-facing `risk:` text so it does not promise hull damage the engine doesn't deliver, and add an inline deferral comment at the callsite. Nothing ships claiming a mechanic the engine doesn't perform. |
| [MEDIUM] | Mandatory wiring test under-asserts (component membership only) — cannot detect the above | `tests/integration/test_war_rig_command_otel.py` (wiring test) | Assert specific ops fired (`action_taken` for the CP verb; a crisis op for `deal_with_crisis`) per the 86-6 precedent |
| [MEDIUM] | No integration test that CP persists across rounds via `shared_state` (AC1 production path) | `tests/integration/test_war_rig_command_otel.py` | Call `resolve_table` twice on one `TableState`; assert `shared_state["command_points"].current` reflects both spends |
| [MEDIUM] | DC boundary (`total == dc`) untested | `tests/game/table/test_war_rig_command.py` | Add seeded `total == dc` (pass) and `total == dc-1` (fail) cases |
| [MEDIUM] | `support_department` under-covered (no OTEL delta test; no `bonus == 0`) | `tests/.../test_war_rig_command_otel.py` + `test_war_rig_command.py` | Add a support_department OTEL test (action_taken+delta) and `assert result.bonus == 0` |
| [LOW] | `__all__` omits new public constants | `war_rig.py:170` | Add `WAR_RIG_COMMAND_VERBS`, `WAR_RIG_DEAL_WITH_CRISIS` |
| [LOW] | `CommandPointPool(max=0)` and negative `ability_mod` untested | `test_war_rig_command.py` | Add the two boundary cases |

**Non-blocking, accepted (delivery findings):** insufficient-CP mid-round abort (graceful per-commit rejection → 86-5); `crisis.escalated`-before-`crisis.resolved` ordering; `shared_state` non-JSON-serializability (ephemeral-TableState invariant currently holds).

**Handoff:** Back to TEA (Mr. Praline) for rework — the core fixes are testable (tighten the wiring test, add the in-round escalation/persistence/boundary tests as failing RED), then Dev makes them green (wire the Hull or correct the overclaims).

---

## Subagent Results — Re-Review (Round 2)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean (1356 passed/0 failed/49 skipped, ruff+pyright clean, 0 smells) | 0 findings, 5 notes | notes are known 86-5 deferrals — no action |
| 2 | reviewer-edge-hunter | N/A (disabled) | Skipped (disabled) | N/A | self-covered — round-1 [EDGE] (insufficient-CP abort) accepted as 86-5 |
| 3 | reviewer-silent-failure-hunter | N/A (disabled) | Skipped (disabled) | N/A | self-covered — the round-1 [SILENT] (consequence-free escalation) is now FIXED |
| 4 | reviewer-test-analyzer | Yes | findings | 4 (all prior 6 ADDRESSED) | confirmed 2 (wiring-delta, hull_delta==0 asserts), deferred 2 (docstring typo, string-key coupling) |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 (prior 6 RESOLVED) | confirmed 1 (LOW docstring typo) |
| 6 | reviewer-type-design | N/A (disabled) | Skipped (disabled) | N/A | self-covered — rule-checker rule-3 clean; `_shared_hull` fully annotated |
| 7 | reviewer-security | N/A (disabled) | Skipped (disabled) | N/A | self-covered — no new trust boundary; rule-checker rule-11 clean |
| 8 | reviewer-simplifier | N/A (disabled) | Skipped (disabled) | N/A | self-covered — `_shared_hull` mirrors `_shared_cp_pool`; no over-engineering |
| 9 | reviewer-rule-checker | Yes | clean (67 instances / 0 violations) | 0 (both prior violations RESOLVED) | confirmed: `__all__` + `bonus==0` fixed; new code passes all 13 rules |

**All received:** Yes (4 enabled returned; 5 disabled self-assessed)
**Total findings:** 4 confirmed (all LOW/MEDIUM polish), 0 dismissed, 2 deferred; **all 8 round-1 findings resolved**

### Round-1 finding resolution

| Round-1 finding | Sev | Status |
|-----------------|-----|--------|
| Consequence-free in-round escalation (hull=None) | HIGH | ✅ RESOLVED — `custom_beat` seeds + passes shared `WarRigHull`; `test_in_round_continuing_crisis_escalation_damages_the_shared_hull` proves Hull 6→4 + `rig_pool.delta -2` |
| Docstrings + player content overclaim hull damage | HIGH | ✅ RESOLVED — 3 docstrings qualified; `rules.yaml` "the Hull pays for it" now true (comment-analyzer confirms) |
| Wiring test asserts component-membership only | MED | ✅ RESOLVED — now asserts `action_taken`/`rolled`/`resolved` ops |
| No cross-round CP-persistence integration test | MED | ✅ RESOLVED — two `resolve_table` calls, 4→3→2 via `shared_state` |
| DC boundary untested | MED | ✅ RESOLVED — `total==dc` (pass) + `total==dc-1` (fail), deterministic |
| support_department under-covered | MED | ✅ RESOLVED — OTEL action_taken+delta + `bonus==0` |
| `__all__` omits new public constants | LOW | ✅ RESOLVED (rule-checker) |
| max=0 / negative ability_mod untested | LOW | ✅ RESOLVED |

### Reviewer Observations (Round 2)

- **[VERIFIED] In-round crisis escalation now damages the shared Hull** — `war_rig.py:175` seeds/passes `_shared_hull(state)`; `deal_with_crisis` calls `hull.apply_delta(-penalty)`. Evidence: `test_in_round_continuing_crisis_escalation_damages_the_shared_hull` asserts `hull.current == 4` AND a real `rig_pool.delta == -2` through the watcher route (seed 0, deterministic). The round-1 HIGH is genuinely closed — the span is no longer consequence-free.
- **[VERIFIED] Docstrings now match behavior** — `war_rig_command.py`/`crisis.py`/`CrisisEntry` docstrings qualify hull damage as conditional on a supplied Hull (the round supplies it); comment-analyzer confirms `rules.yaml` "the Hull pays for it" is now accurate.
- **[VERIFIED] No regression / no new rule violation** — rule-checker 67 instances / 0 violations; preflight 1356 green incl. the 86-6 suites; `shared_state` opaque dict leaves poker/auction untouched.
- **[TEST][MEDIUM] Wiring test could also assert `command_points.delta`** at `test_war_rig_command_otel.py` — currently asserts `action_taken` only through the production path; a 0-cost mutation would slip. Cheap hardening; the isolation test already covers it. Non-blocking.
- **[TEST][MEDIUM] Boundary tests don't pin `hull_delta == 0` for the no-hull path** — `test_deal_with_crisis_boundary_one_below_dc_fails` could assert the documented no-hull contract. Non-blocking.
- **[TEST][LOW] String-key coupling** — tests read `shared_state["command_points"]`/`["war_rig_hull"]` by literal (the module-private key constants). A rename would fail loudly (acceptable), but importing the constants would be cleaner. Non-blocking.
- **[DOC][LOW] Test docstring typo** — `test_in_round_..._hull` docstring says face 7 is "engine_fire"; `CRISIS_TABLE[7]` is "boarders" (engine_fire is face 5). The load-bearing numbers (DC 12, continuing, penalty 2) are correct; only the name is wrong. Cosmetic. Non-blocking.
- **[NOTE][LOW] Crisis-driven Hull→0 bypasses the combat crash cascade** — `deal_with_crisis` uses `hull.apply_delta` (raw pool delta), not `apply_war_rig_hull_damage` (armor + `resolve_crash_saves` fan-out). So a crisis grinding the Hull to 0 floors it without crashing the crew the way a combat hit would. Consistent with the original function design and harmless at minimal scope (6-Hull, 1–3 penalties); whether crisis-zeroing should trigger the crash cascade is an 86-5 calibration question. Delivery finding.

### Devil's Advocate (Round 2)

Assume the rework only *looks* fixed. The first thing to attack: is the in-round escalation test a real proof or a rigged one? It uses `random.Random(0)`, and the docstring even names the wrong crisis — could the author have hand-picked a seed that passes while the wiring is subtly broken? Trace it: the test calls the *production* `game.custom_beat` (not the function in isolation), reads the Hull back out of `shared_state` (the real storage), and asserts both a state drop (6→4) AND a `rig_pool.delta == -2` through the real `WatcherSpanProcessor` route. To fake that, the wiring would have to actually seed a Hull, actually pass it, and actually call `apply_delta` — i.e., it would have to be correct. The seed only fixes *which* crisis fires; it cannot manufacture a Hull drop the code doesn't perform. The wrong crisis name in the docstring is a red herring — the asserted numbers (DC 12, penalty 2) are right for face 7. So the proof holds.

Next: could the rework have *broken* something to make the test pass? The Hull is lazily seeded in `_shared_hull` — does seeding it mid-round emit a spurious `rig_pool.created` that pollutes other assertions? It emits `op="created"`, and every Hull/CP assertion filters on `op=="delta"`/specific ops, so no. Does the seeded default-6 Hull ever get destroyed and silently swallow a crash? `apply_delta` floors at 0 and emits `zero_crossing` but does not fan crash saves — a real semantic gap, but a *disclosed* one (noted as a delivery finding), not a silent failure, and unreachable at minimal scope. What about the table now carrying mutable pydantic objects in `shared_state` that don't JSON-serialize? Still true — but `TableState` is documented ephemeral, and the gate for that (persistence) doesn't exist in this story. Finally, the meanest question: did the reviewer (who is also the author of the fix) wave it through? The four independent subagents — run on the actual diff — each confirm resolution: rule-checker 0 violations, comment-analyzer the docstrings no longer lie, preflight 1356 green, test-analyzer all six prior findings addressed with sound, deterministic, non-vacuous tests. The remaining findings are genuinely cosmetic. The crunch fires, the Hull bleeds, the span tells the truth. There is no blocking defect left to find.

## Reviewer Assessment

**Verdict:** APPROVED

The round-1 REJECT centered on a `crisis.escalated` span that fired with no mechanical consequence while docstrings and player-facing content promised hull damage. The rework wired the crew's shared `WarRigHull` through the `shared_state` seam so a failed continuing crisis **actually damages the Hull in a live round** (proven by a deterministic integration test asserting both the state drop and a real `rig_pool.delta`), and corrected every overclaiming docstring. All four independent specialists confirm resolution: rule-checker 0 violations (both prior fixed), comment-analyzer the docstring cluster resolved, preflight 1356 green, test-analyzer all six prior findings addressed. The crunch now fires and the OTEL span tells the truth — exactly what this epic exists to deliver.

**Specialist coverage (round 2 — all 8 categories):**
- [RULE] rule-checker — 67 instances / 0 violations; both prior violations (`__all__`, `bonus==0`) resolved; new code passes all 13 rules.
- [TEST] test-analyzer — all 6 prior findings addressed; 4 new non-blocking nits (wiring-test `delta` assert, `hull_delta==0` boundary assert, string-key coupling, docstring typo).
- [DOC] comment-analyzer — the round-1 overclaim cluster (3 docstrings + player content) is resolved; 1 new LOW (test docstring face-name typo).
- [EDGE] edge-hunter disabled — self-assessed: the round-1 insufficient-CP mid-round abort is accepted as a 86-5 deferral; no new boundary defect in the rework.
- [SILENT] silent-failure-hunter disabled — self-assessed: the round-1 consequence-free escalation is FIXED (Hull now damaged in-round); `_shared_hull` get-or-seed is an explicit initial state, not a silent fallback; no swallowed errors.
- [TYPE] type-design disabled — self-assessed (corroborated by rule-checker #3): `_shared_hull` is fully annotated; pydantic + frozen-dataclass types clean.
- [SEC] security disabled — self-assessed (corroborated by rule-checker #11): no untrusted-input/SQL/HTML/path surface; the rework adds none.
- [SIMPLE] simplifier disabled — self-assessed: `_shared_hull` mirrors `_shared_cp_pool` exactly; no over-engineering, no dead code.
- Preflight — 1356 green, lint/typecheck clean, 0 smells.

The four remaining findings are non-blocking polish (a stronger wiring-test `delta` assert `[TEST]`, a `hull_delta==0` boundary assert `[TEST]`, a test docstring typo `[DOC]`, string-key coupling `[TEST]`) — recorded as delivery findings. The accepted 86-5 deferrals stand (graceful per-commit CP rejection; crisis-driven Hull→0 not triggering the combat crash cascade; `shared_state` serializability).

**Data flow traced:** player `deal_with_crisis` commit → `custom_beat` → `roll_crisis` + `deal_with_crisis(hull=shared WarRigHull)` → `apply_delta` → `rig_pool.delta` + `crisis.escalated` (with real `hull_delta`) through the watcher route. Safe and mechanically backed.
**Pattern observed:** get-or-seed shared resource on `TableState.shared_state` (`_shared_cp_pool` / `_shared_hull`) — clean, mirrors the established WarRigHull/CommandPointPool pydantic precedent.
**Error handling:** fail-loud throughout (unknown verb, unknown CP action, insufficient CP, blank vessel_id, bad bounds) — No Silent Fallbacks honored.

**Handoff:** To SM (The Announcer) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The story context names the implementation module `war_rig_crew.py` and span modules `telemetry/spans/command_points.py` / `crisis.py`, but the live 86-6 table-game module is actually `sidequest/game/table/war_rig.py` and the vessel layer is `sidequest/game/war_rig_combat.py`. Tests target a **new** `sidequest/game/war_rig_command.py` (the CP + crisis layer, mirroring `war_rig_combat.py`'s shape). Affects `sprint/context/context-story-86-7.md` §"Key Implementation Files" (paths are aspirational, not current).
- **Question** (non-blocking): The CP/crisis station verbs (`above_and_beyond`, `support_department`, `deal_with_crisis`) must wire into `WarRigCrewTableGame.custom_beat` AND the shared CP pool must be reachable from `custom_beat(state, seat, commit)` — but where the per-vessel CP pool is **stored on TableState** is unmodeled in 86-6 (stations live in `seat.private_state`; CP is *shared*, not per-seat). Affects `sidequest/game/table/war_rig.py` + `table/types.py` (Dev picks the shared-state seam; the wiring test's `deal`-seeds-CP contract is the seam). *Found by TEA during test design.*

### Reviewer (code review)
- **[ROUND 2 — RESOLVED]** Both blocking findings below were fixed in rework round 1 (commit `851719a3`): the Hull is now wired through `shared_state` (in-round escalation damages it for real), and the wiring test now asserts specific ops. Verdict round 2: **APPROVED**. The round-2 non-blocking polish findings are listed below.
- **Improvement** (non-blocking): The production-path wiring test asserts `command_points.action_taken` but not `command_points.delta` — a 0-cost mutation of `above_and_beyond` would slip past it. Affects `tests/integration/test_war_rig_command_otel.py` (add `assert "delta" in cp_ops`). *Found by Reviewer during re-review.*
- **Improvement** (non-blocking): The DC-boundary tests don't pin `result.hull_delta == 0` for the `hull=None` path (the documented no-hull contract). Affects `tests/game/table/test_war_rig_command.py` (add the assertion). *Found by Reviewer during re-review.*
- **Gap** (non-blocking): Crisis-driven Hull→0 uses `hull.apply_delta` (raw pool delta), which floors at 0 **without** firing the combat crash cascade (`apply_war_rig_hull_damage` → `resolve_crash_saves` fan-out). A crisis grinding the Hull to 0 therefore doesn't crash the crew the way a combat hit does. Affects `sidequest/game/war_rig_command.py` `deal_with_crisis` (86-5 should decide whether crisis-zeroing triggers the crash cascade). *Found by Reviewer during re-review.*
- **Improvement** (non-blocking): Test docstring of `test_in_round_continuing_crisis_escalation_damages_the_shared_hull` names face 7 as "engine_fire"; `CRISIS_TABLE[7]` is "boarders" (engine_fire is face 5). Load-bearing numbers (DC 12, penalty 2) are correct; only the name is wrong. Affects `tests/integration/test_war_rig_command_otel.py` (fix the docstring). *Found by Reviewer during re-review.*
- **[Round 1, now historical] Conflict** (blocking → resolved): In-round continuing-crisis escalation fired `crisis.escalated` but applied no Hull damage (`hull=None`) while docstrings + player-facing `rules.yaml` claimed it did. **Resolved** in round 1 (Hull wired). *Found by Reviewer during code review.*
- **[Round 1, now historical] Gap** (blocking → resolved): The wiring test asserted component membership only, not ops. **Resolved** in round 1 (asserts `action_taken`/`rolled`/`resolved`). *Found by Reviewer during code review.*
- **Gap** (non-blocking): Insufficient-CP commits raise inside `resolve_table` with no surrounding try/except, aborting the whole cooperative round for all seats. Affects `sidequest/game/table/engine.py:176` + `war_rig.py` (86-5 should validate CP affordability per-commit before resolution — fail-loud is correct, but the round should reject one commit, not crash). *Found by Reviewer during code review.*

### Dev (implementation)
- **Gap** (non-blocking): The crewed `war_rig_crew` table has no first-class link to its vessel's `WarRigHull` — so `custom_beat`'s `deal_with_crisis` rolls/resolves a crisis with `hull=None`, meaning in-round crisis **escalation does not yet damage the real shared Hull** (the escalation→two-pool path is fully wired + tested at the function/OTEL level, just not bound through the table round). Affects `sidequest/game/table/war_rig.py` + `table/types.py` (86-5 should bind the vessel Hull onto `TableState.shared_state` so a continuing-crisis escalation in a live round hits the Hull). *Found by Dev during implementation.*
- **Gap** (non-blocking): `vessel_id` is synthesized as `f"war_rig_crew:{dealer_seat}"` because the table carries no vessel identity; CP/crisis OTEL is therefore attributed to a derived id, not the actual rig. Affects `sidequest/game/table/war_rig.py` (86-5 vessel-stat-block work should supply a real vessel id). *Found by Dev during implementation.*
- **Improvement** (non-blocking): TEA's `test_above_and_beyond_grants_a_d6_bonus` drained one shared 5-CP pool across 20 spends, which correctly tripped the (now-implemented) fail-loud insufficient-CP guard. Fixed in place to sample a fresh 1-CP pool per seed — the test's actual intent. Affects `tests/game/table/test_war_rig_command.py`. *Found by Dev during implementation.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Crisis table pinned as a code-level `CRISIS_TABLE` constant, not content-authored entries**
  - Spec source: context-story-86-7.md, "Technical Approach" / AC2 + Key Implementation Files
  - Spec text: "`road_warrior/rules.yaml` — war_rig_crew confrontation def with crisis table entries"
  - Implementation: Tests pin a minimal playable `CRISIS_TABLE: dict[int, CrisisEntry]` constant in `war_rig_command.py` (faces 1–10); the content test requires only that road_warrior declares the *verbs* (`above_and_beyond`/`support_department`/`deal_with_crisis`), not a content-authored table.
  - Rationale: A content-authored crisis-table schema needs new genre-model fields (a `CrisisEntry`/table on the confrontation def) — a larger surface than spec §6's "minimal playable… sufficient to prove wiring," and closer to 86-5 lethality calibration. A code constant proves the d10/continuing/acute/escalation mechanics now; promoting the table into `rules.yaml` is a clean follow-up. Logged so Dev/Reviewer can override if a content-authored table is required for AC2.
  - Severity: minor
  - Forward impact: If 86-5 (calibration) needs per-world crisis tables, the table moves from constant → content; the resolver API (`roll_crisis`/`deal_with_crisis`) is designed to take entries so the move is non-breaking.
- **CP/crisis verbs are not all content beats** (`do_your_duty` is the implicit default, not an authored verb)
  - Spec source: context-story-86-7.md, AC1
  - Spec text: "Three CP actions implemented per SWN §4.3: Do Your Duty (0 CP, standard resolution), Above and Beyond, Support Department"
  - Implementation: The content test requires only the two *spendable* CP verbs + `deal_with_crisis` as authored beats; `do_your_duty` (0-cost standard resolution) is pinned at the unit level only, as it is the default station-action path, not a distinct player verb.
  - Rationale: Authoring a no-op "standard resolution" verb as a content beat is redundant with the existing station verbs (steer/shoot/etc. already *are* doing-your-duty). Keeps the content minimal per spec §6.
  - Severity: minor
  - Forward impact: none — `do_your_duty` remains a first-class code path (cost 0, emits `action_taken`), just not surfaced as a separate menu verb.

### Dev (implementation)
- **`deal_with_crisis` in `custom_beat` uses `ability_mod=0` and rolls+resolves in one verb**
  - Spec source: context-story-86-7.md, AC2
  - Spec text: "Deal With a Crisis action: station verb that rolls d10 + relevant ability vs crisis DC"
  - Implementation: The in-round `custom_beat` path calls `roll_crisis` then `deal_with_crisis` with `ability_mod=0` (no acting-character stat is plumbed into the table round), and rolls a fresh crisis per verb rather than resolving a persistent active-crisis stored on state.
  - Rationale: The table round has no character-stat or active-crisis-state binding yet (minimal-playable wiring per spec §6). The `deal_with_crisis` function itself takes a real `ability_mod` and is unit-tested with it; only the in-round glue hardcodes 0. The full lifecycle (crisis rolled at round start, persisted on `shared_state`, resolved by a later verb with the actor's ability) is 86-5 calibration work.
  - Severity: minor
  - Forward impact: minor — 86-5 binds character ability + a persistent active-crisis to the round; the resolver API does not change.
- **Shared CP pool seeded at a flat default (`WAR_RIG_DEFAULT_COMMAND_POINTS = 4`)**
  - Spec source: context-story-86-7.md, AC1 / spec §6 ("minimal playable")
  - Spec text: "CP is a per-vessel shared resource … persists across rounds and depletes as actions are taken"
  - Implementation: `custom_beat` get-or-seeds a 4-CP pool on first command verb; the value is a flat constant, not derived from crew size / command stats / vessel.
  - Rationale: Spec §6 scopes 86-7 to minimal playable wiring; per-vessel CP calibration belongs to 86-5. The persistence + depletion + fail-loud semantics (the load-bearing part of AC1) are real and tested.
  - Severity: minor
  - Forward impact: minor — 86-5 replaces the constant with a derived starting CP; storage seam (`TableState.shared_state["command_points"]`) is unchanged.
- **Shared in-round Hull seeded at a flat default (`WAR_RIG_DEFAULT_HULL = 6`)** *(rework round 1)*
  - Spec source: context-story-86-7.md, AC2 + Reviewer HIGH finding
  - Spec text: "Crisis escalation feeds into the two-pool rig damage model (86-2)"
  - Implementation: `custom_beat` get-or-seeds a 6-point `WarRigHull` on `TableState.shared_state` (key `war_rig_hull`) so an in-round continuing-crisis failure actually damages it; the starting value is a flat constant, not a per-vessel stat block.
  - Rationale: Wiring the existing 86-6 `WarRigHull` through the shared-state seam is the in-scope fix for AC2 (Reviewer's option (a)); the *value* (full vessel stat block) is genuinely 86-5. This makes the escalation mechanically real now while leaving calibration to 86-5.
  - Severity: minor
  - Forward impact: minor — 86-5 binds the real vessel Hull (stat block) at the same `shared_state["war_rig_hull"]` seam; the wiring is unchanged.

### Reviewer (audit)
- **TEA — Crisis table as a code-level `CRISIS_TABLE` constant (not content-authored)** → ✓ ACCEPTED by Reviewer: a code constant is the right minimal-playable choice per spec §6; a content-authored crisis schema is genuine 86-5 surface. The resolver API takes `CrisisEntry` objects, so the later content move is non-breaking. Agrees with author reasoning.
- **TEA — `do_your_duty` not a content beat (implicit default)** → ✓ ACCEPTED by Reviewer: a no-op "standard resolution" verb as authored content would be redundant with the station verbs; reachable-by-direct-beat-id is acceptable and pinned at unit level.
- **Dev — `deal_with_crisis` in `custom_beat` uses `ability_mod=0` and rolls+resolves in one verb** → ✓ ACCEPTED by Reviewer *as a simplification*, but see ✗ FLAG below: combined with `hull=None` it makes the in-round crisis path almost-always-fail-with-no-consequence. The `ability_mod=0` simplification itself is acceptable for minimal wiring; the *consequence-free escalation* is the blocking issue, tracked separately in the Reviewer Assessment (HIGH).
- **Dev — Shared CP pool seeded at flat `WAR_RIG_DEFAULT_COMMAND_POINTS = 4`** → ✓ ACCEPTED by Reviewer: the load-bearing AC1 semantics (shared, persistent, fail-loud depletion) are real; per-vessel CP derivation is legitimately 86-5. (Note: ensure the cross-round persistence is actually integration-tested per the MEDIUM finding before this is fully trustworthy.)
- **Dev delivery-finding "in-round escalation does not damage the Hull — deferred to 86-5" (non-blocking)** → ✗ FLAGGED by Reviewer: re-classified **blocking as shipped**. The deferral is reasonable *engineering*, but the code ships docstrings + player-facing content asserting the hull damage, and an OTEL span (`crisis.escalated`) that fires without its mechanic. The deferral is acceptable only if the overclaims are corrected (or the Hull is wired). See Reviewer Assessment HIGH row.
  - **→ Round 2: ✅ RESOLVED.** Dev chose option (a): wired the shared `WarRigHull` through `shared_state` so in-round escalation damages it for real. The FLAG is cleared.
- **Dev — Shared in-round Hull seeded at flat `WAR_RIG_DEFAULT_HULL = 6` (rework round 1)** → ✓ ACCEPTED by Reviewer: wiring the existing 86-6 `WarRigHull` through the `shared_state` seam is the correct in-scope fix for AC2; the flat starting value (vs a real vessel stat block) is legitimately 86-5, exactly parallel to the accepted CP-default deviation. The load-bearing behavior (escalation → real `rig_pool.delta`) is integration-tested.

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->