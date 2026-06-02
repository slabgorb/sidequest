---
story_id: "59-28"
jira_key: ""
epic: ""
workflow: "tdd"
---
# Story 59-28: apply_witnessed_act collapse/tip threshold needs a touched-this-turn guard (wry_whimsy political engine)

## Story Details
- **ID:** 59-28
- **Jira Key:** (none — no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none
- **Priority:** p1
- **Points:** 2

## Technical Context

The `apply_witnessed_act` function in `sidequest-server/sidequest/game/political_engine.py` mutates premise and bloc dials in response to a witnessed act. The bug is in the final threshold pass (lines 143-167):

```python
# 3. Threshold pass (collapse / tip), once, after all dial movement.
premise_by_id = {p.premise_id: p for p in premises}
bloc_by_id = {b.bloc_id: b for b in blocs}
for pid, pstate in state.premises.items():
    pdef = premise_by_id.get(pid)
    if pdef is None or pstate.collapsed:
        continue
    if pstate.belief_reserve <= pdef.collapse.threshold:
        pstate.collapsed = True
        # ... collapse event
for bid, bstate in state.blocs.items():
    bdef = bloc_by_id.get(bid)
    if bdef is None or bstate.tipped:
        continue
    if bstate.defiance >= bdef.tipping_threshold:
        bstate.tipped = True
        # ... tip event
```

**The problem:** These checks fire EVERY time `apply_witnessed_act` is called, regardless of whether the dial actually moved THIS turn. If a bloc is pre-seeded at/above `tipping_threshold` (or a premise at/under `collapse.threshold`) at rest, calling `apply_witnessed_act` for ANY unrelated act will fire the collapse/tip event again, even though the dial hasn't changed.

**The fix:** Track which dials were mutated BY THIS TURN's act (via the drain, couple, awaken effects), and ONLY check collapse/tip for those dials. A dial that was already past threshold at rest does NOT cross the threshold this turn, so collapse/tip does not fire.

## Acceptance Criteria

1. **Collapse/tip fires only for premises/blocs whose dial moved this turn (or crossed threshold due to this act), not for dials already past threshold at rest**
   - Add a `touched_this_turn` set to track which `(kind, id)` pairs were mutated by drain/couple/awaken
   - Modify the final threshold pass to only check premises/blocs in `touched_this_turn`
   - Dials that crossed threshold due to THIS turn's effects WILL be in the set and WILL be checked

2. **Regression test: an unrelated witnessed act with a bloc pre-seeded at/above tipping_threshold does NOT tip it**
   - Seed a bloc at `defiance=70` with `tipping_threshold=70` (at the boundary, already tipped-ready)
   - Call `apply_witnessed_act` with an unrelated act (e.g. `act_id="unrelated"`) that does not touch this bloc
   - Assert: no `"tipped"` event in the returned events
   - Assert: `state.blocs[bloc_id].tipped` remains `False` (no state mutation)
   - Assert: the ledger has NO `"tipped"` entry for this turn

3. **Existing apply_witnessed_act tests still pass**
   - All tests in `tests/game/test_political_engine.py` must remain green
   - The coupling-can-tip test (line 119-127) still works because the bloc IS touched via coupling this turn
   - The tip-on-awaken test (line 96-105) still works because the bloc IS touched via awakening this turn

4. **OTEL collapse/tip spans unchanged**
   - No changes to span names or structure in the dispatch subsystem
   - The engine continues to return a list of `PoliticalEvent` objects with the same schema

## Implementation Notes

**Location:** `sidequest-server/sidequest/game/political_engine.py`, function `apply_witnessed_act` (lines 48-169)

**Design:**
- Add a `touched_this_turn: set[tuple[str, str]]` (e.g., `{("premise", "humbug"), ("bloc", "munchkins")}`) initialized as empty
- Append to `touched_this_turn` in the drain pass (line 99-104) when `applied != 0`
- Append to `touched_this_turn` in the couple pass (line 118-124) when `defiance_applied != 0`
- Append to `touched_this_turn` in the awaken pass (line 137-141) when `applied != 0`
- Modify the threshold pass (lines 146-167) to only iterate over premises/blocs that are in `touched_this_turn`

**Trade-off:** A dial that is ALREADY collapsed/tipped will not be re-checked in the final pass. This is correct — a collapsed/tipped dial is already flagged (`pstate.collapsed = True`, `bstate.tipped = True`) and skips re-entry (line 148, 160). The guard `if pdef is None or pstate.collapsed` ensures we don't re-collapse; the guard `if bdef is None or bstate.tipped` ensures we don't re-tip.

## SM Assessment

Setup complete and handed to TEA for the RED phase.

- **Scope is tight and well-bounded.** A single latent-bug fix in one function (`apply_witnessed_act`, `political_engine.py`) plus a regression test. 2pts, p1, single repo (sidequest-server). No cross-repo coordination.
- **The bug is a real correctness defect, not cosmetic.** A world that authors a bloc at/above `tipping_threshold` at rest would tip on the first unrelated witnessed act. This directly threatens the wry_whimsy political engine's Genre Truth — blocs would tip without a player act actually moving the dial. Worth the p1.
- **TDD is the right workflow.** AC2 is a clean RED case: pre-seed a bloc at the boundary, fire an unrelated act, assert no tip event / no state mutation / no ledger entry. The failing test will demonstrate the bug before the fix exists.
- **Guardrail for TEA/Dev:** the `touched_this_turn` set must still allow dials that *cross* threshold as a result of THIS act's drain/couple/awaken to fire (AC1). The existing coupling-can-tip and tip-on-awaken tests (lines 119-127, 96-105 of `test_political_engine.py`) are the regression floor — they must stay green because those blocs ARE touched this turn.
- **No OTEL changes expected** (AC4) — engine returns the same `PoliticalEvent` schema; this is a guard on *when* events fire, not *what* they emit.
- **Sibling 59-29** (1pt, test-hygiene, co-locate precondition coverage) is intentionally NOT in this story. Keep it separate.
- **Merge gate note:** UI PR #314 (LocationPanel genre font) remains OPEN with merge conflicts — an orphan playtest fix, not a tracked story. Flagged for a later Dev rebase; does not block this story's work in sidequest-server.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Latent correctness bug with a clean, deterministic RED case. TDD is the right fit.

**Test Files:**
- `sidequest-server/tests/game/test_political_engine.py` — 3 new failing tests appended to the existing `apply_witnessed_act` suite.

**Tests Written:** 3 tests covering 2 ACs (AC1 + AC2; AC3 is the existing regression floor; AC4 is N/A — see Rule Coverage).
**Status:** RED (failing — ready for Dev). Verified by testing-runner (RUN_ID 59-28-tea-red): 3 new FAIL, 6 existing PASS.

| Test | AC | RED reason |
|------|----|-----------|
| `test_unrelated_act_does_not_tip_bloc_already_at_threshold` | AC2 | `tipped` event + state + ledger entry fire for a bloc at 70≥70 the act never touched |
| `test_unrelated_act_does_not_collapse_premise_already_at_threshold` | AC1 (premise side) | `collapsed` fires for a premise at 20≤20 the act never touched |
| `test_touched_bloc_tips_while_at_rest_bloc_does_not_in_same_call` | AC1 (discriminator) | the at-rest `winkies` bloc tips in the same call where `munchkins` is legitimately tipped — proves the guard must be act-scoped, not global |

**Discriminator test rationale:** the third test is the sharp one. A naive fix (e.g. "skip the threshold pass entirely when no dial moved") would pass tests 1–2 but FAIL test 3, because test 3 *does* have a moving dial (munchkins) in the same call as a stationary at-rest dial (winkies). It forces the Dev toward the spec'd per-dial `touched_this_turn` set, not a coarse turn-level short-circuit.

### Rule Coverage

| Rule | Test(s) | Status |
|------|---------|--------|
| Meaningful assertions (no vacuous) | all 3 assert on events + state + ledger | passing self-check |
| No source-text wiring tests | behavior tests invoke the real `apply_witnessed_act`; no `read_text()`/grep | satisfied |
| OTEL (AC4) | N/A — `political_engine.py` is pure logic by design (module docstring: "no OTEL — the caller records the ledger-derived spans"); the engine returns `PoliticalEvent`/ledger entries unchanged, so no span assertion belongs here | N/A |

**Rules checked:** 3 applicable (assertion quality, no-source-text-wiring, OTEL-where-applicable). OTEL is correctly out of scope — the engine emits no spans; the dispatch subsystem does, and AC4 only requires those stay unchanged (no engine schema change).
**Self-check:** 0 vacuous tests. Every new test asserts on returned events, mutated state, AND the ledger (the three observable surfaces of the bug).

**Guardrail for Dev (Agent Smith):** the fix must keep all 6 existing tests green. `test_coupling_can_tip_a_propping_bloc` (coupling crosses the line), `test_bloc_tips_when_defiance_crosses_threshold` (awaken crosses), and `test_belief_clamps_at_zero_and_collapse_fires_once` (drain crosses) are the positive cases — a touched dial that crosses threshold THIS turn MUST still fire. Per the session Implementation Notes, append to `touched_this_turn` only when `applied != 0` in the drain/couple/awaken passes, then restrict the threshold pass to touched dials. Do not change the `PoliticalEvent` schema (AC4).

**Handoff:** To Dev for GREEN.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/political_engine.py` — added a `touched_this_turn: set[tuple[str, str]]` to `apply_witnessed_act`; populate it in the drain (`("premise", id)`), couple (`("bloc", id)`), and awaken (`("bloc", id)`) passes, each inside the existing `if applied:`/`if defiance_applied:` guard (so only nonzero movement counts); the final threshold pass now `continue`s past any dial not in the set. Docstring item 3 updated to describe the guard.
- `sidequest-server/tests/game/test_political_engine.py` — import block sorted (ruff I001, the only gated lint fix); the 3 RED tests authored in the red phase are unchanged.

**Tests:** 14/14 passing (GREEN) — 9/9 `test_political_engine.py` (3 guard tests now green + 6 regression floor), 5/5 `test_witnessed_act_subsystem.py` (dispatch integration). `ruff check` clean, `pyright` clean on the changed source. Verified via testing-runner RUN_IDs `59-28-dev-green` and `59-28-dev-green-final`.

**Approach notes:**
- Followed the session Implementation Notes exactly — per-dial `(kind, id)` set, gated on `applied != 0`. The discriminator test (`...at_rest_bloc_does_not_in_same_call`) confirms the guard is act-scoped, not a coarse turn-level short-circuit.
- The three positive regression cases (coupling-tip, awaken-tip, drain-collapse) stay green because those dials ARE touched this turn and thus enter the set.
- No `PoliticalEvent` schema change; the engine stays pure (no OTEL) per its module contract — AC4 satisfied (dispatch-subsystem spans untouched).
- **Reverted an ungated `ruff format` whitespace expansion** that the GREEN verification triggered. The project gate (`just server-check`) and CI (`server-ci.yml`) run `ruff check` only, not `ruff format --check`; the pre-existing tests use a deliberate compact call style. Reformatting them would have been a ~50-line diff into code I didn't own. Kept the diff surgical and matching surrounding style. (Logged as a deviation below.)

**Branch:** `feat/59-28-witnessed-act-touched-guard` (pushed, tracks origin). Commits: `24defbd` (RED tests), `cfc6a90` (GREEN fix).

**Handoff:** To verify phase (TEA).

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None

All four ACs map cleanly to the diff (`political_engine.py` +20/−3):
- **AC1** — `touched_this_turn: set[tuple[str, str]]` is added to only on nonzero movement (`applied`/`defiance_applied`) in the drain/couple/awaken passes; both threshold loops `continue` past any `(kind, id)` not in the set. The "or crossed threshold due to this act" clause holds because a crossing dial necessarily moved this turn and is therefore in the set — confirmed by the still-green coupling-tip, awaken-tip, and drain-collapse regression tests.
- **AC2** — `test_unrelated_act_does_not_tip_bloc_already_at_threshold` exists and is green (was RED pre-fix).
- **AC3** — 9/9 engine + 5/5 dispatch-subsystem tests green; no `PoliticalEvent` schema change.
- **AC4** — engine is pure by module contract (no OTEL); dispatch-subsystem spans untouched.

**Architectural observation (Trivial — no action):** gating the touched-set on `applied != 0` means a dial pinned at a clamp boundary (e.g. `defiance=100` with `tipping_threshold=100`) whose movement clamps to zero is never tip/collapse-checked. This is *correct* under AC1's literal "dial moved this turn" — a dial that cannot move cannot cross — and any dial truly past threshold from a prior turn is already flagged (`tipped`/`collapsed`) and skipped. Recorded as an observation, not a mismatch; resolution A is unnecessary (the spec already describes this behavior).

**Decision:** Proceed to verify (TEA).

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed (14/14 tests, ruff + pyright clean — unchanged since green phase; no simplify edits applied)

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 2 (`political_engine.py`, `test_political_engine.py`)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 3 findings | 1 high (extract threshold-pass helper), 1 medium (parametrize 2 tests), 1 low (monitor `touched_this_turn` pattern) |
| simplify-quality | clean | no findings |
| simplify-efficiency | clean | no findings — explicitly judged the two-loop threshold structure "clear and maintainable; a merged loop would not simplify meaningfully" |

**Applied:** 0 fixes.
**Flagged for Review:** 1 (medium — test parametrization).
**Noted:** 1 (low — pattern-watch).
**Dismissed:** 1 (high — threshold-pass extraction; rationale below).
**Reverted:** 0.

**Overall:** simplify: clean (no actionable findings applied)

### Triage rationale (mandatory — high-confidence finding dismissed)

- **HIGH (dismissed) — "extract a parametric `_fire_threshold_pass` helper" for the premise/bloc loops (`political_engine.py:156-181`).** Dismissed, not applied, for four converging reasons:
  1. **Conflicts with simplify-efficiency**, which independently judged the same two loops clear and a merge non-simplifying. When reuse and efficiency conflict, readability + minimal-surface wins.
  2. **Semantic-coincidence duplication, not true duplication.** The loops vary on *eight* axes — state dict (`.premises`/`.blocs`), kind, field (`belief_reserve`/`defiance`), threshold attr (`collapse.threshold`/`tipping_threshold`), **comparison direction (`≤` vs `≥`)**, completion flag (`collapsed`/`tipped`), effect name, and detail source (`collapse.outcome`/`tipped_outcome`). A helper would need ~6 callables/accessors; "collapse premises" and "tip blocs" are conceptually distinct directions that read better explicit.
  3. **Pre-existing structure.** This duplication predates 59-28; my diff only added two `continue` guard lines. Refactoring it is out of scope for a p1 bug fix and would inflate a surgical +20/−3 diff with unrelated churn + regression risk.
  4. **No test demands it.** Per Dev minimalist discipline and TDD, abstraction without a failing test is speculative.
- **MEDIUM (flagged, not applied) — parametrize the two unrelated-act tests.** `pytest.mark.parametrize` is not auto-applied (per policy, medium = flag only). I also judge it a net negative here: the two tests exercise *different subsystems* (premise-collapse vs bloc-tip) with different fixtures and field names; collapsing them behind parametrize obscures which mechanism each guards. Left as two explicit, self-documenting tests.
- **LOW (noted) — watch the `touched_this_turn` "record-what-moved, fire-only-for-moved" pattern.** If it recurs in trope ticks / confrontation rounds / NPC agency chains (2+ sites), revisit extracting a shared turn-scoped tracker. Not actionable now.

### TEA (test verification) — Delivery Findings
- No upstream findings during test verification. Implementation aligns with the spec; the Architect spec-check found no drift; simplify surfaced only a pre-existing, out-of-scope readability opinion (dismissed with rationale).

**Quality Checks:** All passing (14/14 targeted tests, ruff clean, pyright clean).
**Handoff:** To Reviewer for code review.

## Subagent Results

**All received:** Yes

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 14/14 green, ruff+pyright clean, 0 smells | confirmed 0, dismissed 0 |
| 2 | reviewer-edge-hunter | Yes | findings | 11 (1 high, 3 med, 7 low) | confirmed 1 (non-blocking, test-gap), dismissed 0, deferred 10 (pre-existing / low test-hardening) |
| 3 | reviewer-silent-failure-hunter | Yes | clean | 0 (new code); 1 pre-existing edge noted, visible-in-ledger | confirmed 0 |
| 4 | reviewer-test-analyzer | Yes | findings | 5 (3 high, 2 med) | **challenged 2** (central claim refuted by RED), confirmed 1 (premise-discriminator, Medium/non-blocking), deferred 2 (boundary test-hardening) |
| 5 | reviewer-security | Yes | clean | 0 | confirmed 0 |
| 6 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings |
| 7 | reviewer-type-design | No | Skipped | disabled | Disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings |

## Reviewer Assessment

**Verdict:** APPROVED

The diff is a correct, minimal, well-scoped fix for the p1 latent bug. Five enabled specialists ran; the production-logic reviewers (preflight, edge-hunter logic trace, silent-failure-hunter, security) all confirm the `touched_this_turn` guard is sound, and RED→GREEN is empirically established. No Critical/High issue exists **in the diff**. The findings that surfaced are either (a) pre-existing behavior in unchanged lines, (b) Medium/Low test-coverage symmetry gaps, or (c) one materially incorrect subagent claim that I challenge below.

### Observations (≥5)

1. `[VERIFIED]` Guard is populated only on real movement — `political_engine.py:107,127,147` add to `touched_this_turn` inside the existing `if applied:`/`if defiance_applied:` blocks, so a clamped no-op move never marks a dial. Complies with the No-Silent-Fallbacks rule (the skip is a deliberate behavioral gate on an unchanged dial, not a swallowed error — independently confirmed by silent-failure-hunter).
2. `[VERIFIED]` Threshold pass is per-dial act-scoped — `political_engine.py:157-158,171-172` gate each loop on `(kind, id)` set membership; identical structure for premises and blocs. Boundary inclusivity (`<=` collapse / `>=` tip) is preserved from the original.
3. `[TEST]` (confirmed, Medium, non-blocking) **Premise-side discriminator gap.** The bloc loop is protected against a "coarse global-empty" mutant by `test_touched_bloc_tips_while_at_rest_bloc_does_not_in_same_call`. The premise loop has no equivalent (touched-set non-empty + an at-rest premise at its collapse threshold in the same call). Outright removal of the premise guard IS caught by `test_unrelated_act_does_not_collapse_premise_already_at_threshold`; only a hypothetical *global-empty* premise mutant escapes. Real code uses the same per-dial pattern for both loops, so risk is low — but coverage is asymmetric with the bloc side. Logged as a non-blocking follow-up.
4. `[EDGE]` (confirmed pre-existing, non-blocking, out of scope) Coupling routes defiance off the *authored* `belief_delta` even when the premise drain clamped to zero applied (`political_engine.py:117` `if coupled > 0`, outside the `if applied:` gate); and `propped_by`/`drained_by`/def-lookup mismatches silent-skip (`:121,:160,:174`). **All in lines untouched by this diff.** Visible in the ledger (per silent-failure-hunter). Tracked as a `political_engine` hardening follow-up; not a 59-28 blocker.
5. `[SEC]` (confirmed clean) No security surface — pure in-memory arithmetic over content-def-bounded state; `touched_this_turn` cardinality is bounded by world content, not user input. No injection/deserialization/path/ReDoS vectors (lang-review #8/#11 vacuously compliant).
6. `[SILENT]` (confirmed clean) Every dial-mutation path has a corresponding `add()`; the two `continue` guards are correct behavioral gates, not silent fallbacks.
7. `[VERIFIED]` AC4 — engine emits no OTEL by module contract and the `PoliticalEvent` schema is unchanged; the 5 `test_witnessed_act_subsystem.py` dispatch tests stay green, so dispatch-layer spans are unaffected.

### Challenge (subagent override — required by gate)

**Challenged: reviewer-test-analyzer findings #1 and #2** ("tests 1 & 2 are tautological / would pass against a version with NO 59-28 guard"). This is **factually wrong**, and I cite line-level + empirical evidence:
- Without the guard, the threshold loop runs unconditionally. `test_unrelated_act_does_not_tip_bloc_already_at_threshold` seeds munchkins at `defiance=70` with `tipping_threshold=70`; the unguarded loop hits `70 >= 70` → fires a `tipped` event → its `assert not any(e.effect == "tipped")` **fails**. Same for the premise/collapse test at `reserve=20`/`threshold=20`.
- This is not theoretical: the RED run `59-28-tea-red` reported these exact two tests **FAILING** against the unguarded code. A tautological test cannot fail RED. The analyzer conflated "no guard" (old code, loop runs → test fails) with "the guard's empty-set skip" (new code, loop skips → test passes). The tests correctly discriminate old-from-new and are valid AC2 regression coverage — **not** redundant with `test_unmatched_act_is_a_noop` (which uses `defiance=0`, nothing near threshold, so its unguarded loop fires nothing).
- I do, however, accept the analyzer's narrower, correct point (its finding #3) — see observation 3 above (premise-side discriminator), graded Medium/non-blocking.

### Rule Compliance (lang-review/python.md, changed code only)

| # | Rule | Applies? | Verdict |
|---|------|----------|---------|
| 1 | Silent exception swallowing | no try/except in diff | compliant (n/a) |
| 2 | Mutable default args | no new signatures with defaults | compliant (n/a) |
| 3 | Type annotations at boundaries | `touched_this_turn: set[tuple[str, str]]` annotated; function signature unchanged | compliant |
| 4 | Logging coverage/correctness | module is pure, no logging by design | compliant (n/a) |
| 5 | Path handling | no paths | compliant (n/a) |
| 6 | Test quality | 3 new tests assert on events + state + ledger; none vacuous (proven by RED failures); no skips | compliant (one non-blocking coverage-symmetry gap, obs. 3) |
| 7 | Resource leaks | no resources | compliant (n/a) |
| 8 | Unsafe deserialization | none | compliant (n/a) |
| 9 | Async pitfalls | sync pure function | compliant (n/a) |
| 10 | Import hygiene | test import block sorted (I001 fixed); no star/circular imports | compliant |
| 11 | Input validation at boundaries | not a boundary; inputs are dispatch-layer/content-def | compliant (n/a) |
| 12 | Dependency hygiene | no dependency changes | compliant (n/a) |
| 13 | Fix-introduced regressions | re-scan of the fix diff against #1-#12 finds none | compliant |

Dispatch tags present: `[EDGE]` `[SILENT]` `[TEST]` `[SEC]` confirmed above; `[DOC]` `[TYPE]` `[SIMPLE]` `[RULE]` — subagents disabled via settings (see Subagent Results), no findings to incorporate.

### Devil's Advocate

Suppose this fix is broken. Where would it hurt? The nightmare is a *missed* collapse/tip — a player exposes the Wizard, the premise crosses its collapse threshold, and the guard wrongly swallows the event, so the political engine goes silent at the exact dramatic beat the whole wry_whimsy substrate exists for. Could that happen? The guard skips any dial not in `touched_this_turn`. A dial that crosses threshold *because of this act* was, by definition, moved by drain/couple/awaken with a nonzero `applied`, so it was added to the set — the three positive regression tests (coupling-tip, awaken-tip, drain-collapse) all stay green, refuting this fear. The one true blind spot is a dial whose movement clamps to zero (`applied == 0`) yet sits past threshold: e.g. a bloc pinned at `defiance=100` with `tipping_threshold ≤ 100` that an awaken tries to push higher. It won't be marked touched, so it won't tip *this* turn — but such a dial would already have tipped on the turn it first reached 100 (and `bstate.tipped` then short-circuits it forever), so there is no reachable state where a legitimately-untipped dial is silently stranded. A confused author is the more plausible victim: someone authors a bloc at/above threshold at rest expecting it to "already be revolting," and is surprised it waits for a real act — but that is precisely the spec (Story 59-28), now documented in the docstring. A malicious player has no lever here; `act_id`/`witnesses` never reach a sink. The stressed-filesystem / unexpected-config angles don't apply to a pure in-memory function. The strongest residual critique the devil can muster is the premise-discriminator test gap (obs. 3) and the pre-existing coupling-from-zero / silent-skip behaviors (obs. 4) — none of which the *diff* introduces, and none of which rise to a correctness defect in the shipped fix. Verdict stands: APPROVED, with the gap tracked.

**Data flow traced:** `act_id` (dispatch layer) → equality match against content-def `drained_by`/`awakening_acts` → dial mutation → `touched_this_turn` membership → gated collapse/tip event → ledger. Safe: no user string reaches a sink; set cardinality bounded by content.
**Pattern observed:** per-dial act-scoped guard via set membership — `political_engine.py:157-158,171-172`. Clean, symmetric, idiomatic.
**Error handling:** N/A for this pure function; null-def/missing-bloc skips are pre-existing (obs. 4).
**Handoff:** To SM for finish-story.

## Workflow Tracking
**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-02T21:39:08Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-02 | 2026-06-02T21:15:42Z | 21h 15m |
| red | 2026-06-02T21:15:42Z | 2026-06-02T21:19:48Z | 4m 6s |
| green | 2026-06-02T21:19:48Z | 2026-06-02T21:24:59Z | 5m 11s |
| spec-check | 2026-06-02T21:24:59Z | 2026-06-02T21:26:10Z | 1m 11s |
| verify | 2026-06-02T21:26:10Z | 2026-06-02T21:29:39Z | 3m 29s |
| review | 2026-06-02T21:29:39Z | 2026-06-02T21:37:40Z | 8m 1s |
| spec-reconcile | 2026-06-02T21:37:40Z | 2026-06-02T21:39:08Z | 1m 28s |
| finish | 2026-06-02T21:39:08Z | - | - |

## Delivery Findings

No upstream findings at setup phase.

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No upstream findings during test design. The session Implementation Notes and ACs were sufficient to write the RED cases; the source matched the described bug exactly (threshold pass at `political_engine.py:143-167` iterates all dials unconditionally).

### Dev (implementation)
- **Improvement** (non-blocking): The pre-existing `tests/game/test_political_engine.py` was authored in a compact multi-arg call style that `ruff format` would expand, and its import block failed `ruff check` (I001) before this story. Affects `sidequest-server/tests/game/test_political_engine.py` (a future formatting pass, or adopting `ruff format --check` in CI, would reformat the whole file). *Found by Dev during implementation.*

### Reviewer (code review)
- **Gap** (non-blocking): Premise-side discriminator test missing — the bloc loop is mutant-protected by `test_touched_bloc_tips_while_at_rest_bloc_does_not_in_same_call`, but the premise loop has no equivalent (touched-set non-empty + an at-rest premise at its collapse threshold in one call). A `test_touched_premise_collapses_while_at_rest_premise_does_not` would close the symmetry. Affects `sidequest-server/tests/game/test_political_engine.py` (add one mirrored test). Natural fast-follow; fits sibling 59-29's test-hygiene scope. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Pre-existing No-Silent-Fallbacks gaps in `apply_witnessed_act` (NOT introduced by this diff): coupling routes defiance even when the premise drain clamped to zero applied (`political_engine.py:117`, outside the `if applied:` gate); `propped_by`/`drained_by`/def-lookup mismatches silently `continue` (`:121,:160,:174`). Surfaced by edge-hunter. Affects `sidequest-server/sidequest/game/political_engine.py` (add a loud error/OTEL on content-def mismatch; gate coupling on premise movement or document threshold=0 as illegal). Candidate political_engine hardening story. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Exact-boundary tests would harden against a future `<=`→`<` / `>=`→`>` regression — premise drained to *exactly* `collapse.threshold`; bloc coupled to *exactly* `tipping_threshold`. Affects `sidequest-server/tests/game/test_political_engine.py`. *Found by Reviewer during code review.*

## Design Deviations

None at setup phase.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- No deviations from spec. All three ACs in scope are covered by tests (AC3 via the existing regression floor; AC4 is N/A — pure-logic engine emits no OTEL, only the dispatch caller does).

### Dev (implementation)
- **Did not apply `ruff format` to the changed test file**
  - Spec source: project quality convention / `just server-check` + `sidequest-server/.github/workflows/server-ci.yml`
  - Spec text: gate runs `uv run ruff check .` (lint) + `uv run pytest`; `ruff format` is a separate, non-gated `server-fmt` recipe
  - Implementation: reverted the `ruff format` whitespace expansion that GREEN verification produced; kept only the gated `ruff check --fix` import-sort change plus the new tests, in the file's existing compact style
  - Rationale: `ruff format` is not enforced by the gate or CI; applying it would reformat ~50 lines of pre-existing tests unrelated to this fix, against "code that reads like the surrounding code" and minimalist-diff discipline
  - Severity: minor
  - Forward impact: none — `ruff check` (the enforced gate) passes; if CI later adopts `ruff format --check`, the file (and siblings) will need a one-time format pass (captured as a Delivery Finding)
  → ✓ ACCEPTED by Reviewer: sound. The gate (`server-check`) and CI both run `ruff check` only; reverting the ungated format churn keeps a p1 fix surgical and matches the file's established style. Forward impact correctly captured as a Delivery Finding.

### Reviewer (audit)
- **TEA "no deviations from spec"** → ✓ ACCEPTED: AC1/AC2 are covered by the new tests; AC3 by the existing regression floor; AC4 is correctly N/A (pure engine, no OTEL). One nuance the audit adds: TEA's AC1 *discriminator* coverage is bloc-only — the premise side relies on structural symmetry (logged as a non-blocking Delivery Finding, not a deviation, since the implementation does cover both loops identically).
- No undocumented spec deviations found. The implementation matches the session Implementation Notes line-for-line (per-dial `(kind, id)` set gated on nonzero movement; threshold pass restricted to touched dials).

### Architect (reconcile)

**Deviation manifest audit — entries verified:**
- **Dev "did not apply `ruff format`"** — all 6 fields present, accurate, and Reviewer-accepted. Spec source (`just server-check` + `server-ci.yml`) is real; spec text correctly states the gate runs `ruff check` + `pytest` only (`ruff format` is the separate non-gated `server-fmt` recipe); implementation, rationale, severity (minor), and forward impact (none; CI-format-adoption captured as a Delivery Finding) all check out. **Confirmed accurate — no correction needed.**
- **TEA "no deviations from spec"** — correct. The implementation covers both threshold loops identically; AC4 is genuinely N/A (pure engine). No hidden divergence.

**No additional deviations found.** The shipped code does not diverge from the session Implementation Notes or the four ACs.

**Two reconcile clarifications for the audit trail (not deviations):**
1. **Forward-impact correction to the Reviewer's premise-discriminator finding.** The Reviewer suggested that follow-up "fits sibling 59-29's test-hygiene scope." It does **not**: 59-29 co-locates the `witnessed_act` *dispatch precondition* coverage (`snapshot.political_state is None → inert`) into `tests/agents/test_dispatch_precondition_gate.py` — a different surface (the precondition gate) in a different file. The premise-discriminator gap lives in `tests/game/test_political_engine.py` (the *engine's* threshold pass). It is a **standalone, non-blocking test-hardening item**, not part of 59-29. Recorded so the boss does not assume 59-29 closes it.
2. **OTEL consideration (CLAUDE.md OTEL Observability Principle).** This fix touches the political subsystem yet adds no engine OTEL span — consciously, not by omission. `political_engine.py` is pure by module contract ("no OTEL — the caller records the ledger-derived spans"); the dispatch subsystem emits the spans from the returned `PoliticalEvent`/ledger entries, whose schema is unchanged (AC4, the higher-authority story spec). Net effect on observability is a **strict improvement**: the GM-panel lie-detector will now stop emitting spurious `collapsed`/`tipped` spans for at-rest dials an act never moved — the spans become more truthful, not less. No deviation; the AC explicitly scopes engine OTEL out.

**AC deferral check:** No ACs were deferred or descoped (all four DONE). Step is a no-op.