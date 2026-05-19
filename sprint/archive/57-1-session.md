---
story_id: "57-1"
jira_key: "57-1"
epic: "epic-57"
workflow: "trivial"
---
# Story 57-1: Recency narrative window K=4→K=2

## Story Details
- **ID:** 57-1
- **Jira Key:** 57-1
- **Epic:** epic-57
- **Workflow:** trivial
- **Stack Parent:** none
- **Repository:** sidequest-server
- **Branch:** feat/57-1-recency-window-k2
- **Slug:** recency-window-k2

## Technical Approach

### Change Summary
Reduce the recency narrative window from K=4 to K=2 entries (1 player turn + 1 narrator turn instead of 2+2), cutting tokens and improving prompt-cache efficiency.

### File to Modify
- **File:** `/Users/slabgorb/Projects/oq-1/sidequest-server/sidequest/agents/orchestrator.py`
- **Location:** Line 102 (constant definition)
- **Current Value:** `RECENT_NARRATIVE_WINDOW_K: int = 4`
- **New Value:** `RECENT_NARRATIVE_WINDOW_K: int = 2`

### Implementation Details
The constant is used in one key location:
- Line ~2049: Window slicing: `_recent_window = list(context.recent_narrative_log)[-RECENT_NARRATIVE_WINDOW_K:]`

This follows the pattern established in Story 49-1 (recency-zone narrative window, shipped 2026-05-11). The constant controls the maximum number of narrative entries (player actions + narrator responses) that are rendered into the Recency attention zone of the narrator prompt. Reducing K from 4→2 trims token usage while maintaining enough context to avoid prose-continuity regressions like the 2026-05-11 Glenross gender-flip bug.

### Context from ADR-098 and Story 49-1
- **ADR-098:** Stateless narrator turns with bounded per-turn prompts
- **Story 49-1:** Delivered the recency-zone narrative window fix to prevent narrator continuity breaks
- **Constant comments (lines 95-104):** Document K=4 as "2 player turns + 2 narrator turns" and explain the cap-not-floor semantics for partial windows

### Acceptance Criteria
1. **Constant updated:** Change line 102 in orchestrator.py from `4` to `2`
2. **Comments updated:** Update the docstring near lines 95-96 to reflect "1 player turn + 1 narrator turn" instead of "2+2"
3. **Tests updated:** Update tests that hardcode K=4 semantics (cap test, partial-window parametrize, fixture sizing, session-helpers wiring test)
4. **Verification:** Full server suite green; no regressions

### Risk Assessment
- **Low risk:** Pure constant reduction with no logic changes
- **Test coverage:** Comprehensive test suite already exists (30+ tests in test_orchestrator_recency_narrative.py)
- **Prompt behavior:** Token reduction will improve cache efficiency; narrative coherence is maintained at K=2 per ADR-098 design

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-19T19:26:21Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-19T15:15:00Z | 2026-05-19T19:06:08Z | 3h 51m |
| implement | 2026-05-19T19:06:08Z | 2026-05-19T19:19:06Z | 12m 58s |
| review | 2026-05-19T19:19:06Z | 2026-05-19T19:26:21Z | 7m 15s |
| finish | 2026-05-19T19:26:21Z | - | - |

## Sm Assessment

**Setup complete.** Story is a single-constant change with a single test update.

- **Scope:** `RECENT_NARRATIVE_WINDOW_K: int = 4 → 2` in `sidequest-server/sidequest/agents/orchestrator.py:102`, plus updates to the existing cap test in `tests/agents/test_orchestrator_recency_narrative.py` (`test_recent_narrative_section_caps_at_last_four_entries` at line 246, and the comment/docstring at lines 95-96).
- **Risk:** Low. Pure tuning; reversible. No protocol/schema/migration. Behaviour-watch on next playtest for recurrence of ADR-098 narrative misses; 49-1 stays the safety net.
- **OTEL:** No new spans required — recency selection is already covered by existing narrator spans; this is a constant tuning, not a new subsystem (per CLAUDE.md "Not needed for: Cosmetic changes" carve-out).
- **Workflow:** Trivial / phased — straight to dev (implement). No TEA red phase needed; we're updating an existing pinning test, not writing new contract tests.
- **Routing:** Hand to Puck (dev) for the implement phase.

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed:**
- `sidequest-server/sidequest/agents/orchestrator.py` — constant `RECENT_NARRATIVE_WINDOW_K: int = 4 → 2` (line 102); updated docstring comments near lines 95-101 and the TurnContext field comment near line 675.
- `sidequest-server/sidequest/server/session_helpers.py` — updated explanatory comment near line 487 ("last K=4" → "last K=2 (57-1)"); the actual call already uses the constant via import.
- `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py` — renamed cap test `test_recent_narrative_section_caps_at_last_four_entries` → `..._last_two_entries` and adjusted body-range assertions (rounds 16-19 → 18-19); narrowed partial-window parametrize from `[1,2,3]` → `[1]` on the two partial-window tests (k_actual=2 is exact-cap, k_actual≥3 exceeds cap and is no longer "partial"); trimmed `_glenross_gender_flip_log()` fixture from 4 entries (rounds 3-5) to the load-bearing 2 entries (rounds 4-5) so post-cap section content still contains every fixture entry; renamed and resized `test_four_oversized_entries_stay_within_section_budget` → `test_oversized_entries_stay_within_section_budget` to a 2×10kB stress; resized the short-log + chronological-order tests from 4 entries to 2; updated bounded-prompt invariant test's `K = 4 → K = 2` literal and the surrounding "K-window fills" / ramp-up narrative; updated module docstring and the SECTION_BUDGET_BYTES comment.
- `sidequest-server/tests/server/test_session_helpers_narrative_strip.py` — updated wiring test to expect `len(recent) == 2`, `log[-2:]` slice, and `assert_called_once_with(2)`.

**Tests:** Full suite 6752 passing / 0 failing / 397 skipped (110.32s).
- Focused files: `tests/agents/test_orchestrator_recency_narrative.py` + `tests/server/test_session_helpers_narrative_strip.py` — 23/23 passing.
- Full server suite via `uv run pytest`: 6752/0/397.

**Branch:** `feat/57-1-recency-window-k2` (commit + push pending after this assessment).

**Handoff:** To review (Portia).

**Note:** Testing-runner overwrote this session file mid-phase (known issue per memory `feedback_testing_runner_overwrites_session`); reconstructed from conversation context. SM Assessment + Workflow Tracking + Technical Approach above are preserved from the pre-clobber version.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (6752/0/397, ruff format-clean on changed files) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.edge_hunter=false` |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.silent_failure_hunter=false` |
| 4 | reviewer-test-analyzer | Yes | findings | 7 | confirmed 5, dismissed 0, deferred 2 (filed as Delivery Findings) |
| 5 | reviewer-comment-analyzer | Yes | findings | 6 | confirmed 1, dismissed 5 (pre-existing — not introduced by this PR's diff), deferred 0 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.type_design=false` |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.security=false` |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via `workflow.reviewer_subagents.simplifier=false` |
| 9 | reviewer-rule-checker | Yes | findings | 3 | confirmed 2 (parametrize smell, duplicate of test-analyzer), deferred 1 (OTEL gray-zone), dismissed 0 |

**All received:** Yes (4 returned with findings, 5 disabled per project settings)
**Total findings:** 7 confirmed, 5 dismissed (pre-existing stale comments outside this PR's logical scope), 3 deferred to Delivery Findings for follow-up

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** The constant `RECENT_NARRATIVE_WINDOW_K` flows from `sidequest/agents/orchestrator.py:102` to two consumers:
- `sidequest/agents/orchestrator.py:2049` — `list(context.recent_narrative_log)[-RECENT_NARRATIVE_WINDOW_K:]` — slices the live narrative log for the Recency-zone prose section. With K=2, the slice yields the last 2 entries (1 player + 1 narrator turn) as intended.
- `sidequest/server/session_helpers.py:666` — `sd.store.recent_narrative(RECENT_NARRATIVE_WINDOW_K)` — passes K as the SQLite query limit. The store fetch correctly receives `2` (verified by `test_session_helpers_narrative_strip.py:220` `assert_called_once_with(2)`).

Both call sites consume the imported constant — no hardcoded values, no parallel definitions, no silent fallback. The end-to-end wiring (store → context → orchestrator → registered Recency section) is exercised by `test_recent_narrative_log_populated_on_turn_context_from_store` and `test_recent_narrative_context_appears_in_composed_prompt_text`.

**Pattern observed:** Faithful mechanical constant-tightening — constant changed once at the source of truth, downstream code paths (slice site, store limit) inherit through the existing import chain. The cascading test updates are necessary because the test suite hardcoded K=4 semantics in ~12 places (assertion bounds, fixture sizes, parametrize values, mock-call expectations). This is the Improvement filed by Dev (`feedback_durable_retention`–style "single edit" target for a future refactor).

**Error handling:** N/A — no new error paths introduced. Existing zero-byte-leak guard at `orchestrator.py:2050` (`if _recent_window:`) handles empty-log case unchanged.

**Findings tagged by source:**

- [TEST] `test_orchestrator_recency_narrative.py:307,366` — single-value `@pytest.mark.parametrize('k_actual', [1])` on `test_partial_window_registers_section_with_available_entries` and `test_partial_window_otel_span_attrs_match_injected_body`. The parametrize machinery is dead scaffolding at one value. **Severity: LOW** — cosmetic smell, doesn't weaken coverage. Decision: defer to follow-up; Dev's narrowing logic ("k_actual=2 is exact-cap, k_actual≥3 exceeds cap") is correct, just leaves single-value scaffolding behind.
- [TEST] `test_orchestrator_recency_narrative.py:358` — `if k_actual >= 2: assert body.index(first_marker) < body.index(last_marker)` is dead code under the narrowed parametrize. **Severity: LOW** — branch is unreachable but its absence at k_actual=1 is correct (1 entry has no ordering). Decision: defer to same follow-up as the parametrize smell.
- [TEST] `test_orchestrator_recency_narrative.py:979` — `ramp = section_sizes[:K-1]` becomes a single-element list at K=2, making `ramp == sorted(ramp)` trivially true and the `if len(ramp) >= 2:` strict-monotone check unreachable. **Severity: LOW** — the ramp concept only has meaning when K ≥ 3. Decision: defer to follow-up; the bounded-prompt invariant test still pins the load-bearing byte-envelope assertion.
- [TEST] `test_orchestrator_recency_narrative.py:554` — `SECTION_BUDGET_BYTES = 12_000` is calibrated for the pre-57-1 K=4 ceiling (4×2kB+overhead). At K=2 the theoretical ceiling is ~4.5kB; the assertion still catches "per-entry cap disabled entirely" (~20kB) but has more headroom than necessary. **Severity: LOW** — assertion is honestly commented (`sized for pre-57-1 K=4; still valid for K=2 with headroom`); not vacuous since the larger-scale per-entry-disabled bug still trips it. Decision: dismiss as a deliberate, documented headroom choice.
- [TEST] `test_orchestrator_recency_narrative.py:447` — `test_recent_narrative_span_truth_invariant_across_window_sizes` sweeps {empty, K=1, K=3, K=5} but lacks an explicit K=2 case (the new steady state). **Severity: LOW** — the K=3 case already exercises the over-cap path that K=2 introduces, and `test_recent_narrative_section_caps_at_last_two_entries` covers the exact-cap content. Decision: defer to follow-up.
- [DOC] `tests/server/test_session_helpers_narrative_strip.py` `_glenross_log()` — comment-analyzer flagged the fixture's "last 4 are the Recency window" docstring as stale. Decision: confirmed actionable — see Delivery Findings (in-scope nit that 57-1's diff could have caught). **Severity: LOW**.
- [DOC] `test_orchestrator_recency_narrative.py:442,444` — `test_recent_narrative_span_truth_invariant_across_window_sizes` docstring still reads "turns 1-3 of a fresh save" and "Currently fails on the K∈{1,2,3} cases". Dev updated similar K=4-era language in the partial-window block header (lines 282-303) but missed this docstring. **Severity: LOW** — confirmed in-scope omission. Decision: defer to follow-up (or a quick patch — see Delivery Findings).
- [DOC] `test_orchestrator_recency_narrative.py:316,378,444,723` — pre-existing stale references (`orchestrator.py:1622`, `orchestrator.py:1309`, "Currently fails" framing on tests that have been green since 49-1 shipped 2026-05-11). **Decision: dismiss** — pre-existing, outside this PR's logical scope. Dev's diff only touches lines adjacent to these, not the stale references themselves. The "Currently fails" pattern is a known TDD-era convention from story 49-1's RED phase; the comments lie about current state but predate 57-1. Pre-existing debt belongs in its own cleanup story.
- [RULE] `orchestrator.py:102` — rule-checker flagged the K-tightening as borderline against the OTEL principle ("every backend fix touching a subsystem MUST add OTEL watcher events"). The existing `recent_narrative_context_injected` span continues to fire with `turn_count` reflecting the post-tightening reality (now 1-2 instead of 1-4); adding a `recency_k=2` span attribute would give the GM panel an explicit lie-detector signal for the configured K. **Severity: LOW**, gray zone — the CLAUDE.md carve-out for cosmetic changes is plausibly applicable since the span already speaks the truth about what was injected. Decision: defer as Improvement.
- [TEST] Wiring confirmed: `assert_called_once_with(2)` at `test_session_helpers_narrative_strip.py:220` pins the store-query parameter; `test_recent_narrative_section_caps_at_last_two_entries` pins the slice content; `test_recent_narrative_context_appears_in_composed_prompt_text` (out of diff) pins the composed-prompt path.
- [VERIFIED] Production constant flows through both consumers — orchestrator.py:2049 (slice) and session_helpers.py:666 (store limit) both reference the imported constant directly. No hardcoded `2` introduced in production code (only in tests, where it is the assertion-of-truth).
- [VERIFIED] No silent fallback introduced — the K change is a single explicit constant edit at the source of truth (orchestrator.py:102). Imports flow through to both call sites without conditional swaps.
- [SIMPLE] N/A — disabled subagent. Independent check: change is minimal and faithful to scope; no over-engineering observed.
- [SEC] N/A — disabled subagent. Independent check: no new input handling, deserialization, or secret-handling paths. Constant value is integer literal; no injection surface.
- [TYPE] N/A — disabled subagent. Independent check: constant remains `int`; no new types introduced; existing field annotations preserved.
- [EDGE] N/A — disabled subagent. Independent check: edge cases (empty log, partial window of 1, exact-cap of 2, over-cap of 3+) are covered by existing tests; the empty-log guard at orchestrator.py:2050 is unchanged.
- [SILENT] N/A — disabled subagent. Independent check: no new try/except, no swallowed exceptions, no log-level downgrades introduced.

### Devil's Advocate

**This code is broken.** Here are the angles a malicious or confused agent could find:

1. *Narrator coherence regression in multi-turn scenes.* The whole point of 49-1's K=4 was to let the narrator see TWO player turns and TWO narrator turns — enough to keep a 2-turn dialogue or a setup-and-reveal beat coherent. K=2 means the narrator only sees the immediately-prior turn pair. A 3-turn negotiation where the player establishes context in turn 1, the narrator responds in turn 2, and the player commits in turn 3 — turn 3's prompt no longer carries turn 1's context. The Glenross gender-flip beat (the canonical regression this whole subsystem exists to prevent) still works because it's a 1-turn-prior beat, but tighter K narrows the safety margin. **Counter:** This is a known, deliberate tradeoff — token-cache efficiency vs. recency depth. The risk is documented in the SM Assessment and is reversible (flip the constant). The behavior-watch on the next playtest catches a real regression.

2. *Vacuous assertions degrade detection power.* Four test-quality findings (ramp vacuity at line 979, dead chronological branch at line 358, single-value parametrize x2 at 307/366, headroom at SECTION_BUDGET_BYTES at 554) all weaken the test suite as a regression detector at K=2. A future bug where K is implicitly treated as a FLOOR again would now sail through some of these tests where it would have been caught at K=4. **Counter:** The load-bearing caps-at-last-two test (the renamed cap test, line 238) and the partial-window registration test (the parametrize=[1] case) both still discriminate correctly. The vacuous parts are vacuous *because* K=2 collapses the search space, not because the tests were weakened by hand.

3. *Pre-existing stale-comment debt continues to mislead.* The "Currently fails" docstrings + stale orchestrator.py:1622 + orchestrator.py:1309 references could lead a future debugger down a 30-minute wild goose chase. **Counter:** Pre-existing — not introduced by this PR — and explicitly out of scope per the SM Assessment. Filing as Delivery Finding for a debt-pay-down story is the right call.

4. *Storage-side query change.* The constant flows into a SQLite query: `sd.store.recent_narrative(2)` instead of `(4)`. If any other caller in the codebase reads `recent_narrative(N)` with a fixed N expecting K=4 semantics, that caller is now mismatched. **Counter:** Grep confirms `RECENT_NARRATIVE_WINDOW_K` is the only K consumer feeding `recent_narrative()`. Other call sites (e.g., `corpus/miner.py`, `corpus/diff.py`) iterate the full log via `iter_narrative_log()`, not the K-windowed query. No mismatch.

5. *OTEL silent change.* The dashboard's `recent_narrative_context_injected` span now shows turn_count maxing at 2 instead of 4. Sebastien's lie-detector reads the new numbers as "the system is engaging with 2 turns" but has no way to distinguish "engaged with K=2 by config" from "engaged with K=4 but only 2 entries available". A future K change becomes invisible on the dashboard. **Counter:** Real concern, gray zone per CLAUDE.md. Filed as Delivery Finding (Improvement, non-blocking) — add a `recency_k` span attribute in a follow-up.

6. *Test fixture trim loses scene context.* Trimming `_glenross_gender_flip_log()` from 4 entries to 2 drops the gardener/hedge-row preamble — the setup that establishes the patient's location. Tests asserting "Father" and "secateurs" survive on the trimmed fixture because rounds 4 and 5 contain those words, but a regression where the narrator loses scene anchoring (e.g., forgetting WHERE the patient is, not just WHO) is no longer caught by this fixture. **Counter:** The scene-anchoring class of bugs isn't this fixture's job — `test_recent_narrative_section_preserves_chronological_order` and `test_recent_narrative_section_renders_as_prose_not_json` cover the rendering contract independently. The Glenross fixture's canonical job is the male-patient continuity beat (Father/his/secateurs), which the trimmed version preserves verbatim. Documented in the fixture docstring.

**Conclusion:** No new finding surfaces from the Devil's Advocate pass. The PR is correctly scoped, faithfully implemented, and well-tested at the load-bearing checkpoints. The test-quality concerns are LOW-severity and naturally arise from K being small enough to collapse certain test scenarios — they belong in a debt-paydown story alongside the pre-existing stale-comment debt and the "import-constant-from-source" parametrization improvement Dev already filed.

### Rule Compliance

Reviewed against `.pennyfarthing/gates/lang-review/python.md` (14 numbered checks) + CLAUDE.md/sidequest-server CLAUDE.md additional rules (A1–A5). Every applicable rule was enumerated against every changed file by the `reviewer-rule-checker` subagent. Summary:

| Rule | Title | Instances | Violations | Notes |
|------|-------|-----------|------------|-------|
| 1 | Silent exception swallowing | 4 | 0 | No try/except in diff |
| 2 | Mutable default arguments | 4 | 0 | No function signatures changed |
| 3 | Type annotation gaps | 4 | 0 | `int` annotation preserved on constant |
| 4 | Logging coverage & correctness | 2 | 0 | No new error paths |
| 5 | Path handling | 4 | 0 | No path ops in diff |
| 6 | Test quality | 14 | 2 | Single-value parametrize x2 (LOW, deferred) |
| 7 | Resource leaks | 4 | 0 | No new resource acquisitions |
| 8 | Unsafe deserialization | 4 | 0 | No pickle/eval/yaml |
| 9 | Async/await pitfalls | 8 | 0 | All async tests use `await` correctly |
| 10 | Import hygiene | 4 | 0 | No new imports |
| 11 | Input validation at boundaries | 2 | 0 | No new boundaries |
| 12 | Dependency hygiene | 1 | 0 | No pyproject changes |
| 13 | Fix-introduced regressions | 4 | 0 | Re-scan clean |
| 14 | State cleanup ordering | 2 | 0 | No register/commit/send patterns in diff |
| A1 | No Silent Fallbacks | 3 | 0 | Explicit constant |
| A2 | No Stubbing | 4 | 0 | No skeleton code |
| A3 | Don't Reinvent — Wire Up What Exists | 1 | 0 | Tunes an existing constant |
| A4 | Verify Wiring (every suite needs a wiring test) | 2 | 0 | `assert_called_once_with(2)` + composed-prompt test |
| A5 | OTEL on subsystem changes | 1 | 1 (borderline) | Gray-zone — see Delivery Findings |

**Handoff:** To SM (Prospero) for finish-story.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): Tests hardcode the K window value across many sites instead of importing `RECENT_NARRATIVE_WINDOW_K` from the orchestrator. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py` and `sidequest-server/tests/server/test_session_helpers_narrative_strip.py` (every K-dependent fixture size, assertion bound, mock-call expectation, and module-docstring number). Future K tunings will need to revisit ~12 sites again; a follow-up that imports the constant and parametrizes window-size fixtures would make K changes single-edit. Out of scope for this story (mechanical update was the assigned approach). *Found by Dev during implementation.*

### Reviewer (code review)
- **Improvement** (non-blocking): Single-value `@pytest.mark.parametrize('k_actual', [1])` on `test_partial_window_registers_section_with_available_entries` (line 307) and `test_partial_window_otel_span_attrs_match_injected_body` (line 366) is dead scaffolding — the parametrize decorator implies a sweep that no longer exists, and the `if k_actual >= 2:` chronological-ordering branch at line 358 is unreachable. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py` (de-parametrize or restore meaningful coverage values). Pairs with Dev's import-constant-from-source improvement above. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `ramp = section_sizes[:K-1]` at `test_orchestrator_recency_narrative.py:979` evaluates to a single-element list at K=2, making the `sorted(ramp)` and strict-monotone assertions vacuous (always pass). The bounded-prompt invariant test still holds its load-bearing byte-envelope assertion, but the ramp block is dead at K=2. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py` (either remove the ramp block or guard it with `pytest.skip("ramp only meaningful at K>=3")`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `SECTION_BUDGET_BYTES = 12_000` was calibrated for the pre-57-1 K=4 ceiling (4×2kB+overhead); the K=2 theoretical ceiling is ~4.5kB so the budget has 2.5× headroom. The assertion still catches "per-entry cap disabled entirely" but loses tightness as a per-entry-truncation regression detector. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py:554`. Cleanest fix: derive the budget as `K * PER_ENTRY_CAP_BYTES + overhead` so it stays tight when K is tuned. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_recent_narrative_span_truth_invariant_across_window_sizes` sweeps cases {empty, K=1, K=3, K=5} but lacks an explicit K=2 case — the new steady-state. The over-cap K=3 path covers part of K=2's new shape, but the exact-cap correctness of the span's `turn_count` and `total_tokens` attributes at the new steady state is not pinned. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py` (add a `('K=2', ...)` tuple to the `cases` list). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Stale docstrings on `test_recent_narrative_span_truth_invariant_across_window_sizes` (lines 442/444) — "turns 1-3 of a fresh save" and "Currently fails on the K∈{1,2,3} cases" — describe the K=4 era. Dev updated the analogous wording in the partial-window block header (lines 282-303) but missed this docstring. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py:442-444`. Minor; in-scope for 57-1 but bounded to a docstring touch-up. *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `_glenross_log()` docstring in `test_session_helpers_narrative_strip.py` still says "last 4 are the Recency window"; the test mock returns `log[-2:]` and asserts `assert_called_once_with(2)`, so the fixture docstring contradicts the test body. Affects `sidequest-server/tests/server/test_session_helpers_narrative_strip.py` (one-line docstring update). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Gray-zone OTEL question — the existing `recent_narrative_context_injected` span fires with `turn_count` reflecting reality at K=2, but no span attribute marks the configured K. Sebastien's GM panel cannot distinguish "engaged with K=2 by config" from "engaged with K=4 but only 2 entries available". Affects `sidequest-server/sidequest/agents/orchestrator.py:2058-2066` (add `recency_k=RECENT_NARRATIVE_WINDOW_K` as a span attribute on `recent_narrative_context_injected_span`). The CLAUDE.md "cosmetic carve-out" plausibly applies since the span doesn't lie, so this is filed as Improvement not Gap. *Found by Reviewer during code review.*
- **Gap** (non-blocking): Pre-existing stale comments in `test_orchestrator_recency_narrative.py` that 57-1's diff brushed past but didn't fix — `orchestrator.py:1622` line reference (line 316 docstring) and `orchestrator.py:1309` reference (line 723 docstring) both point at unrelated code in the current orchestrator.py; multiple "Currently fails" docstrings (lines 316, 378) describe behavior that was actually fixed in story 49-1 (2026-05-11) and remain stale. Affects `sidequest-server/tests/agents/test_orchestrator_recency_narrative.py`. Pre-existing debt — separate cleanup story recommended. *Found by Reviewer during code review.*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Trimmed `_glenross_gender_flip_log()` fixture from 4 entries to 2.**
  - Spec source: SM Assessment (session file) — scope listed "the existing cap test ... at line 246, and the comment/docstring at lines 95-96"
  - Spec text: "updates to the existing cap test in `tests/agents/test_orchestrator_recency_narrative.py`"
  - Implementation: Beyond updating the named cap test, I also trimmed the shared `_glenross_gender_flip_log()` fixture from 4 entries (rounds 3, 3, 4, 5) to 2 entries (rounds 4, 5). Multiple other tests in the file use this fixture and assert "every entry's content appears in section.content" — with the new K=2 cap, the pre-cap 4-entry fixture would have lost round 3 entries from the section body, breaking unrelated tests (gender-flip regression, prose-rendering, author-labels, composed-prompt wiring). Trimming the fixture is the minimum change that preserves the scenario's load-bearing male-patient continuity beat (rounds 4-5) while letting all dependent tests pass without per-test "iterate over last-2 of log" surgery.
  - Rationale: Smaller, more localized change (1 fixture trim) than amending 5+ downstream tests to iterate only over `log[-K:]`. Preserves the canonical "Father / secateurs" gender-flip beat.
  - Severity: minor
  - Forward impact: minor — future tests using `_glenross_gender_flip_log()` will receive 2 entries instead of 4. Documented in the fixture docstring with the K=4→K=2 change note.
  - → ✓ ACCEPTED by Reviewer: Agrees with Dev's reasoning. The alternative (per-test `log[-K:]` slicing) would be more brittle and scatter K-awareness across many call sites. Trimming the fixture preserves the load-bearing male-patient beat (rounds 4-5) while letting all dependent assertions remain literal. The fixture docstring's "Trimmed to K=2 entries in 57-1" change-note is explicit about the historical version.

- **Tightened partial-window parametrize from `[1, 2, 3]` to `[1]`.**
  - Spec source: SM Assessment (session file)
  - Spec text: scope did not enumerate partial-window tests
  - Implementation: Two tests (`test_partial_window_registers_section_with_available_entries`, `test_partial_window_otel_span_attrs_match_injected_body`) were parametrized over `k_actual ∈ {1, 2, 3}` — all below the pre-57-1 cap of K=4. After K=2, only `k_actual=1` remains a "partial" window; `k_actual=2` is the exact-cap case (covered by the renamed caps_at_last_two test), and `k_actual=3` exceeds the cap (covered by the cap test's negative assertion). Dropped the parametrize to `[1]` rather than try to reinterpret over-cap inputs.
  - Rationale: "Partial window" is defined as "fewer entries than K". Keeping k_actual=2/3 would make the test's "every entry in available window must be rendered" loop fail under the cap.
  - Severity: minor
  - Forward impact: minor — if K is ever raised back above 2, the parametrize will need to widen again.
  - → ✓ ACCEPTED by Reviewer: Semantically correct — "partial window" excludes the exact-cap case. The downstream consequence (single-value parametrize is dead scaffolding) is filed as a non-blocking Delivery Finding (see Reviewer's `[TEST]` entries on lines 307/366 in the assessment); the deviation itself is sound. Test-analyzer + rule-checker both flagged this as a test-quality smell but neither implicates the deviation's correctness — they implicate the leftover parametrize machinery, which is a separate (cosmetic) follow-up.

### Reviewer (audit)
- No undocumented deviations spotted in the diff. Dev's two entries cover both non-mechanical decisions; the remaining changes are direct mechanical translations of the K=4 → K=2 contract (cap-test renames, body-range adjustments, comment updates, ramp-test K literal, store mock call argument).
## Impact Summary

**Upstream observations consolidated from Delivery Findings.**

### Blocking Issues
None — all findings are non-blocking improvements or pre-existing debt.

### Non-Blocking Improvements (7 findings)

1. **Test Hardcoding of K Value** — Tests hardcode RECENT_NARRATIVE_WINDOW_K values across ~12 sites instead of importing the constant. Affects fixture sizing, assertion bounds, mock expectations, module docstrings. Future K tunings require revisiting all sites; a follow-up that imports constant and parametrizes fixtures would make K changes single-edit.

2. **Dead Parametrize Scaffolding** — Two tests (`test_partial_window_registers_section_with_available_entries`, `test_partial_window_otel_span_attrs_match_injected_body`) have single-value `@pytest.mark.parametrize('k_actual', [1])` implying a sweep that no longer exists; the `if k_actual >= 2:` branch at line 358 is unreachable. Cosmetic smell; defer to follow-up parametrize cleanup or de-parametrize decision.

3. **Vacuous Ramp Assertions** — `ramp = section_sizes[:K-1]` evaluates to single-element list at K=2, making sorted(ramp) and monotone checks always pass. Load-bearing byte-envelope assertion still holds; ramp block is dead code at K=2. Guard with skip or remove.

4. **Oversized SECTION_BUDGET** — SECTION_BUDGET_BYTES = 12_000 was calibrated for K=4 (4×2kB+overhead); K=2 theoretical ceiling is ~4.5kB, so budget has 2.5× headroom. Assertion still catches "per-entry cap disabled" but loses regression-detection tightness. Derive budget as `K * PER_ENTRY_CAP_BYTES + overhead` to stay tight when K tuned.

5. **Missing K=2 Test Case** — `test_recent_narrative_span_truth_invariant_across_window_sizes` sweeps {empty, K=1, K=3, K=5} but lacks explicit K=2 case — the new steady-state. K=3 covers over-cap path, but K=2 exact-cap correctness of span attributes not pinned. Add K=2 tuple to cases list.

6. **Stale Docstrings on Span-Truth Test** — `test_recent_narrative_span_truth_invariant_across_window_sizes` (lines 442/444) still describes K=4 era ("turns 1-3" and "Currently fails on K∈{1,2,3}"). Dev updated analogous wording elsewhere but missed this. Minor, in-scope touch-up.

7. **OTEL Span Attribute Gap (Gray Zone)** — Existing `recent_narrative_context_injected` span fires with `turn_count` reflecting K=2 reality, but no span attribute marks the configured K. GM panel cannot distinguish "K=2 by config" from "K=4 but only 2 entries available". Add `recency_k=RECENT_NARRATIVE_WINDOW_K` span attribute. CLAUDE.md "cosmetic carve-out" arguably applies; filed as Improvement not Gap.

### Pre-Existing Debt (1 finding)

- **Stale Comment References** — `test_orchestrator_recency_narrative.py` has pre-existing stale references to `orchestrator.py:1622` and `orchestrator.py:1309` (no longer relevant), plus "Currently fails" docstrings describing behavior fixed in story 49-1 (2026-05-11). Outside scope of 57-1 diff. Recommend separate cleanup story.

### Summary
- **Blocking count:** 0
- **Improvement count:** 7 (all non-blocking, low severity)
- **Pre-existing debt count:** 1 (pre-existing, recommended for separate story)
- **Ready to finish:** Yes — all findings are cosmetic or pre-existing

### Next Steps
1. Consider follow-up story for test-hardcoding refactor (import constant, parametrize fixtures)
2. File cleanup story for pre-existing stale comment debt
3. Optional: Add `recency_k` OTEL span attribute for GM panel lie-detection (gray-zone, low priority)
