---
story_id: "71-35"
jira_key: ""
epic: "71"
workflow: "tdd"
---
# Story 71-35: Delete the dead is_gm / GM-seat axis from the projection firewall

## Story Details
- **ID:** 71-35
- **Epic:** 71 — Playtest bugfix — uncovered findings (coyote_star MP, 2026-05-27)
- **Jira Key:** (no Jira integration)
- **Workflow:** tdd
- **Stack Parent:** none
- **Priority:** p2
- **Points:** 3
- **Type:** refactor

## Summary

The `is_gm()` predicate and `gm_player_id` field are dead code — **already always-false** — because SideQuest's thesis is that *the narrator is the GM; every human is a player*. There is no human GM seat in this system. The axis was ported from tabletop-VTT convention and doesn't fit.

**Key fact:** `gm_player_id` is initialized `None` in `views.py` and **never reassigned**. The MP branch only logs a warning; it never names a GM. `is_gm()` returns `'gm_player_id is not None and …'` → **always False in every mode**. So the `gm_sees_all` short-circuit in `invariants.py` is dead code, never taken. (Grep of every genre pack for `'unless: is_gm()'` = 0 matches.)

**What we're doing:** Delete the axis entirely (behaviour-preserving), don't leave it around as a dormant footgun. The narrator gets canonical state because it is **server-side and NOT a projection recipient at all** — not because it is 'the GM' in the filter.

**Source:** Playtest 2026-05-31 (burning_peace MP) + Keith; recorded in ping-pong `sq-playtest-pingpong.md` SESSION 2 '[BUG] GM seat is a category error'.

## Story Context

### Files to Delete/Modify

**Delete the dead axis:**

1. **game/projection/invariants.py** — Remove the `gm_sees_all` branch:
   - Delete the `if view.is_gm(player_id):` block (the short-circuit that grants all-seeing)
   - Delete its corresponding `source='invariant:gm_sees_all'` reference
   - Audit remaining branches to confirm no is_gm references remain

2. **game/projection/predicates.py** — Remove `_is_gm` + registry:
   - Delete the `_is_gm()` predicate function
   - Delete its `'is_gm'` entry from the predicate registry
   - Confirm no other references to `_is_gm` exist in the file

3. **game/projection/view.py** — Remove from Protocol + impl:
   - Remove `is_gm()` method from `GameStateView` Protocol
   - Remove `is_gm()` implementation from `SessionGameStateView` class
   - Remove `gm_player_id: Optional[int] | None` field from both

4. **server/views.py** — Remove GM-wiring stubs (~lines 115–169, 262–263):
   - Delete `gm_identity_unwired` warning log
   - Delete `# TODO: wire gm_player_id` comment
   - Delete `_gm_wiring_warned` flag logic
   - Delete `gm_player_id` local variable and any assignments

### Test Churn

~15 firewall test files construct `SessionGameStateView(gm_player_id=…)`. The story description identifies three test categories:

**DELETE is_gm-specific tests:**
- `test_predicates.py::test_is_gm_no_args` — delete entirely
- `test_core_invariants.py` — delete the `'invariant:gm_sees_all'` assertion
- `test_core_invariants.py::test_thinking_is_gm_only_never_routed_to_players` — audit; confirm it's about **thinking routing** vs is_gm routing (if it's about thinking, keep; if it's only about is_gm, delete)

**REWRITE fixtures that used `'unless: is_gm()'` as representative predicate:**
- `test_validator.py` — audit fixtures; replace `is_gm` with `is_self` predicate
- `test_rules_schema.py` — audit asserts checking `redact_fields[0].unless.predicate=='is_gm'`; replace with `is_self`
- `test_projection_end_to_end_wiring.py` — audit fixtures using is_gm; replace with is_self

**DROP the now-unnecessary gm_player_id kwarg** from remaining constructions (remove gm_player_id= args):
- `test_group_g_e2e.py`
- `test_adr105_b3_private_segments.py`
- `test_mid_session_join_lazy_fill.py`
- `test_reconnect_from_cache.py`
- `test_adr105_b1_secret_invariant_wiring.py`
- `test_projection_filter.py`
- `test_secret_routed_rides_turn_tx.py`
- `test_predicates.py` (remaining constructions after test_is_gm deletion)

### Acceptance Criteria

- `is_gm()` method removed from `GameStateView` Protocol and `SessionGameStateView` implementation
- `_is_gm()` predicate deleted from `predicates.py` + registry entry removed
- `gm_player_id` field removed from both Protocol and implementation
- `gm_sees_all` short-circuit branch deleted from `invariants.py` (the entire `if view.is_gm(player_id):` block)
- GM-wiring stubs removed from `server/views.py` (warning, TODO, flag, local var)
- All is_gm-specific tests deleted (test_is_gm_no_args, invariant:gm_sees_all assertion)
- Thinking-vs-is_gm test audited; if it tests is_gm routing alone, deleted (if thinking routing, kept)
- Fixtures using `is_gm()` predicate rewritten to use `is_self` instead
- All remaining `SessionGameStateView(gm_player_id=…)` constructions updated to drop the kwarg
- Full projection/firewall test suite passes (ADR-104/105 coverage)
- No future human-GM mode is intended per CLAUDE.md doctrine (PvP sealed-visibility is reserved/unimplemented; playgroup "doesn't slip notes to the DM")
- **Behaviour-preserving**: Narrator still gets canonical state (it's server-side, not a projection recipient); player-identity predicates (is_self/is_owner_of/in_same_zone/visible_to/in_same_party) still gate firewall

### Design Notes

- **Keep MP-02 PLAYER_SEAT/presence/pause** — those are *player seats*, unrelated to the dead GM seat
- **Narrator bypass reasoning:** The narrator receives canonical state not via an `is_gm()` predicate, but because it is **server-side and not a projection recipient at all**. The firewall then stands on player-identity predicates alone
- Confirm no genre packs reference `unless: is_gm()` (story description: 0 matches found)
- This is a behaviour-preserving deletion of dead code, not a refactor with side effects

## Sm Assessment

Setup is clean and the story is unusually well-specified — the sprint description carries a file-level deletion map and a categorized test-churn plan, so TEA and Dev inherit a precise scope.

- **Scope:** server-only (`sidequest-server`), behaviour-preserving deletion of the dead `is_gm` / GM-seat axis from the projection firewall. Branch `feat/71-35-delete-dead-gm-seat-axis` cut off `develop` (correct base per repos.yaml).
- **Why this is a story, not a fix-fast:** the change itself is small, but ~15 firewall test files construct `SessionGameStateView(gm_player_id=…)` and several are is_gm-specific. The churn is the work — TEA owns the test changes (DELETE is_gm-specific tests, REWRITE `unless: is_gm()` fixtures to `is_self`, DROP the `gm_player_id` kwarg from the remaining ~10 constructions).
- **Doctrine alignment:** confirmed against CLAUDE.md — the narrator *is* the GM; no human occupies a GM seat. PvP sealed-visibility is reserved/unimplemented and the playgroup "doesn't slip notes to the DM," so there is no future human-GM mode this deletion would foreclose. Removing dead code also satisfies CLAUDE.md's "No Stubbing / dead code is worse than no code."
- **Watch item for the green phase:** verify `is_gm` is truly dead end-to-end before deleting — `gm_player_id` initialized `None` and never reassigned, `is_gm()` always-false, 0 genre-pack `unless: is_gm()` matches. The firewall must stand on player-identity predicates alone (`is_self`/`is_owner_of`/`in_same_zone`/`visible_to`/`in_same_party`). Run the full ADR-104/105 projection/firewall suite after.
- **Jira:** not configured for this project — ceremony skipped intentionally.

Handing to Hamlet for the RED phase.

## TEA Assessment

**Tests Required:** Yes
**Reason:** Behaviour-preserving deletion with large test churn — the whole point of the story. TEA owns the test changes per the spec.

**Status:** RED (failing — ready for Dev) — `53 failed, 51 passed` across the projection suite (non-DB subset). Every failure maps 1:1 to "axis still present" and resolves from Dev's single source deletion.

**Test Files (23):**
- `tests/game/projection/test_gm_axis_removed.py` — **NEW** contract module; the headline RED. 8 assertions that the axis is gone: `is_gm` absent from `PREDICATES`; surviving set is player-identity-only; `_is_gm` function deleted; `GameStateView` Protocol has no `is_gm`; `SessionGameStateView` has no `gm_player_id` field / no `is_gm` method / constructs without the kwarg; `CoreInvariantStage` never emits `invariant:gm_sees_all`.
- **Deleted** gm-behavior-specific tests: `test_predicates::test_is_gm_no_args`, `test_session_game_state_view::test_gm_player_id_is_gm`, `test_core_invariants::test_gm_sees_canonical_short_circuits` + `::test_secret_note_gm_short_circuits_before_visibility_gate`, `test_composed_filter::test_gm_invariant_short_circuits_genre_rules`.
- **Rewrote** incidental `is_gm()` fixtures → surviving `is_self()` (green-stable): `test_validator.py` (5), `test_rules_schema.py` (2 + assertion), `test_projection_check.py`, `test_loader_projection.py`, `test_genre_stage.py` (3), `test_composed_filter.py`, `test_envelope_and_view.py` (Protocol stub).
- **Rewrote** `test_projection_end_to_end_wiring::test_end_to_end_single_truth_invariant` — dropped the "GM sees canonical" assertion (the encoded gm_sees_all behavior); canonical truth now asserted via the events table (server-side), which is the story's actual thesis.
- **Dropped** the `gm_player_id` kwarg from ~16 construction sites (all keyword-form; mechanically safe).
- **Added** `test_session_handler_view::test_session_view_does_not_warn_gm_identity_unwired_in_multiplayer` — drives removal of the `gm_identity_unwired` warning (untested dead code today; ruff won't force it since the warning block doesn't reference the removed field).
- **Kept** `test_core_invariants::test_thinking_is_gm_only_never_routed_to_players` — **audit verdict:** it asserts a *non-GM* viewer is denied THINKING, which is the surviving `GM_ONLY_KINDS` branch (branch 4), not is_gm routing. Survives the deletion. **Kept** `test_narrator::test_narrator_identity_is_gm_of_collaborative_rpg` — the *thesis* test (NARRATOR_IDENTITY contains "Game Master"); coincidental name, unrelated to the predicate.

### Rule Coverage

| Rule (CLAUDE.md / lang-review) | Test(s) | Status |
|---|---|---|
| No Source-Text Wiring Tests (use reflection/behavior, not grep) | contract module uses `dataclasses.fields` + registry dict + `hasattr` on the Protocol — the sanctioned "tripwire" pattern | satisfied |
| Every test asserts something meaningful (no vacuous) | self-checked all new assertions; the construct-without-kwarg checks convert the current `TypeError` into an explicit `pytest.fail` | satisfied |
| Behavioral wiring (not just existence) | `test_core_invariant_stage_never_emits_gm_sees_all` drives a real `CoreInvariantStage.evaluate`; MP warning test drives a real `build_game_state_view` | satisfied |
| OTEL/dead-code honesty (CLAUDE.md) | MP warning-absence test ensures the `gm_identity_unwired` log is *removed*, not left dead | satisfied |

**Self-check:** 0 vacuous tests found. No `assert True`, no `is_none()` on always-None, no `let _ =` equivalents.

**Handoff:** To Puck (Dev) for the GREEN deletion — see the precise source map in "Files to Delete/Modify" above, plus the Delivery Findings below (the story's file list undercounted; validator needs no signature-map change; several source docstrings go stale).

## Dev Assessment

**Implementation Complete:** Yes

**Files Changed (source — 4):**
- `sidequest/game/projection/predicates.py` — deleted `_is_gm()` + the `"is_gm"` registry entry. Registry is now player-identity-only (is_self/is_owner_of/in_same_zone/visible_to/in_same_party).
- `sidequest/game/projection/view.py` — removed `is_gm()` from the `GameStateView` Protocol, the `is_gm()` impl, and the `gm_player_id` field from `SessionGameStateView`.
- `sidequest/game/projection/invariants.py` — deleted the `gm_sees_all` short-circuit (branch 1), renumbered remaining branches (1/1b/2/3), renamed `GM_ONLY_KINDS`→`PLAYER_EXCLUDED_KINDS`, and refreshed all stale GM docstrings/comments per the TEA finding.
- `sidequest/server/views.py` — dropped `gm_player_id` from both constructions, removed the `gm_player_id` local + the `gm_identity_unwired` warning block + the `_gm_wiring_warned` flag, removed the now-unused `GameMode` import, and replaced the "GM identity wiring" docstring block with a "no GM seat" note.

**Files Changed (test — 1):**
- `tests/agents/test_adr105_b3_private_segments.py` — rewrote the fifth/missed `gm_sees_all` assertion to the correct post-deletion behavior (see Dev deviation + finding). The other 22 test files were TEA's RED commit.

**Tests:** GREEN — **143 passed, 0 failed** across the projection/firewall surface:
- ruff check on all 4 changed source files: **clean**
- non-DB projection suite: **104 passed** (was 53 failed / 51 passed in RED)
- DB-backed projection/firewall tests (ADR-104/105): **31 passed, 2 skipped**
- `build_game_state_view` consumer tests: **8 passed, 5 skipped**

**Source scrub:** grep of `sidequest/` for `is_gm`/`gm_player_id`/`gm_sees_all`/`_gm_wiring_warned`/`gm_identity_unwired`/`_is_gm`/`GM_ONLY_KINDS` returns **only explanatory prose** in two new docstrings — zero executable references remain.

**Behaviour-preserving:** confirmed. The firewall stands on player-identity predicates alone; the narrator still gets canonical state server-side (not a projection recipient). The only behavior *change* is for a hypothetical `gm` player_id — which never existed in production (`gm_player_id` was always `None`), so production behavior is identical.

**Branch:** feat/71-35-delete-dead-gm-seat-axis (pushed)

**Handoff:** To Hamlet (TEA) for the verify phase (simplify + quality-pass).

### Dev Rework (review-rework, commit `2d1f5a67`)

Addressed all Reviewer (Portia) findings — **test-only; the approved source deletion is unchanged.**

- **[HIGH] resolved** — `test_adr105_b1_secret_invariant_wiring.py`: the dormant 6th `gm_sees_all` assertion (`test_gm_sees_redacted_dispatch_through_production_path`) is rewritten to `test_no_gm_seat_dispatch_through_production_path`, asserting the correct post-deletion behavior (a `"gm"` id is a non-recipient → `include is False`, payload withheld). Mirrors the b3 fix; satisfies AC "All is_gm-specific tests deleted"; explicitly guards against a future re-seat-a-GM PR. (File remains skipped under the unrelated caverns_sunden migration — collects cleanly; logic proven by the live b3 analog.)
- **[MED] resolved** — `test_core_invariants.py`: added `assert outcome.source == "invariant:player_excluded_kind"` to the thinking test (the renamed OTEL label is now positively pinned).
- **[MED] resolved** — `test_genre_stage.py`: `test_include_if_omits_when_predicate_false` → `test_include_if_dispatches_on_predicate`, using `is_self(text)` to exercise **both** branches (omit when value ≠ viewer char, include when =). No longer the always-false degenerate `is_self()`.
- **[MED] resolved** — `test_gm_axis_removed.py`: strengthened `test_core_invariant_stage_never_emits_gm_sees_all` with a `SECRET_NOTE` + `"gm"`-viewer case (the kind the deleted branch would have short-circuited) → asserts `invariant:visibility_gated` exclusion, not `gm_sees_all`.
- **[LOW] resolved** — swept stale "non-GM" fossils (`test_core_invariants` docstring + `test_self_authored_missing_author_field_omits_for_all_viewers`; the e2e "GM canonical" comment); added `assert len(alice_rows) == 3` guard; documented the exact-predicate-set assertion as an intentional security tripwire.
- **[LOW] deferred** — pre-existing bare-except at `views.py:429` left untouched (out of scope; not in this diff).

**Tests:** ruff clean; **104 non-DB + 8 e2e passed**, b1 collects cleanly + skips. **Handoff:** back to Oberon (spec-check) → verify → review.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned
**Mismatches Found:** None material. Two cosmetic extras (both logged as Dev deviations) and one trivial spec imprecision, detailed below — none warrant a hand-back.

AC-by-AC verification against the committed diff (`26c8c036`):

| AC | Verified in code |
|----|------------------|
| `is_gm()` off Protocol + impl | `view.py` diff removes both ✓ |
| `_is_gm()` + registry entry deleted | `predicates.py` diff removes both; registry now player-identity-only ✓ |
| `gm_player_id` field removed | `view.py` diff removes the dataclass field ✓ |
| `gm_sees_all` branch deleted | `invariants.py` branch 1 removed; GREEN test `test_core_invariant_stage_never_emits_gm_sees_all` passes ✓ |
| `views.py` GM stubs removed (warning/flag/local/docstring) | diff removes all; MP warning-absence test passes ✓ |
| is_gm-specific tests deleted | TEA deleted 4; Dev resolved the 5th (b3) ✓ |
| thinking-vs-is_gm test audited | kept — verified it tests the surviving `PLAYER_EXCLUDED_KINDS` branch ✓ |
| is_gm() fixtures → is_self | validator/schema/CLI/loader/genre_stage/composed_filter ✓ |
| all `gm_player_id=` kwargs dropped | source scrub returns zero executable refs ✓ |
| full ADR-104/105 suite passes | 143 passed, 0 failed ✓ |
| no future human-GM mode | doctrine confirmed; firewall stands on player-identity predicates ✓ |
| behaviour-preserving | production `gm_player_id` was always None → production behavior identical ✓ |

**Mismatches:**
- **`GM_ONLY_KINDS` → `PLAYER_EXCLUDED_KINDS` rename** (Extra in code — cosmetic, trivial)
  - Spec: silent on the surviving THINKING-exclusion constant's name
  - Code: renamed (1 internal ref, no external consumers — grep-verified)
  - Recommendation: **A (update spec / accept)** — the old name implied a GM recipient that no longer exists; the rename is correct hygiene for a deletion story and is already logged as a Dev deviation.
- **Invariant branch renumber (1/1b/2/3)** (Extra in code — cosmetic, trivial)
  - Spec: silent
  - Code: renumbered after deleting branch 1
  - Recommendation: **A (accept)** — a mechanical consequence of the deletion; leaving the comments starting at "2" would be the worse outcome.
- **AC wording "gm_player_id removed from both Protocol and implementation"** (Ambiguous spec — trivial)
  - Spec: implies the field lived on the Protocol
  - Code: the `GameStateView` Protocol only ever declared the `is_gm()` *method*; the `gm_player_id` *field* was impl-only. Dev removed exactly what existed (method off Protocol + impl, field off impl).
  - Recommendation: **C (clarify spec)** — no code change; the AC conflated the method and the field. Noted for traceability.

**Decision:** Proceed to verify (TEA). No hand-back to Dev — the deletion is complete, behaviour-preserving, and the two extras are aligned clarity improvements appropriate to a dead-code removal.

**Spec-check (rework pass, after Reviewer REJECT → `2d1f5a67`):** Spec Alignment: **Aligned**, no new mismatches. The rework diff is **test-only** (5 files; source `e4d61be2`→`2d1f5a67` is byte-identical), so my source AC verification above stands. The rework *improves* AC compliance: the previously-unmet "All is_gm-specific tests deleted" AC is now satisfied — the dormant sixth `gm_sees_all` assertion (`test_adr105_b1`) was rewritten to assert post-deletion exclusion. Decision: proceed to verify.

## TEA Assessment (verify)

**Phase:** finish
**Status:** GREEN confirmed

### Simplify Report

**Teammates:** reuse, quality, efficiency
**Files Analyzed:** 5 (the 4 changed source files + the new contract module)

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 1 finding | `_match_to_field` dup with `genre_stage._match_to_value` (high) — **pre-existing, out of scope**; deferred (see Delivery Findings) |
| simplify-quality | 2 findings | OTEL source label `gm_only_kind` stale (high); test name `..._is_gm_only_...` stale (med) |
| simplify-efficiency | 3 findings | OTEL source label (med, dup of quality); docstring "GM sees truth" stale (med); `_is_gm` existence test redundant (low) |

**Applied:** 1 coherent consistency fix — completed the `GM`→`player-excluded` rename that Dev's GREEN commit left half-done. All three teammates independently surfaced the same root cause (a half-rename), so I treated it as one fix:
- `invariants.py`: OTEL source `invariant:gm_only_kind` → `invariant:player_excluded_kind` (high-confidence; grep-verified **no consumer** keys on the old string — only the emit site + an unrelated test *name*).
- `test_core_invariants.py`: `test_thinking_is_gm_only_*` → `test_thinking_is_player_excluded_*`; docstring `"GM sees truth"` → `"player-identity structural filtering (no GM seat)"`.
- Rationale for applying the medium name/docstring fixes alongside the high one: they are the same rename; applying only the OTEL label would leave the suite self-inconsistent ("gm_only" in a test name next to "player_excluded" in the emit). The `gm_only` vocabulary is exactly the GM-seat category error this story purges.

**Flagged for Review (not applied):** the `_match_to_field` duplication — pre-existing, would touch a file outside this story's scope. Logged as a Delivery Finding for a future cleanup.
**Noted (no action):** the `_is_gm` existence test in the contract module is mild redundancy with the registry test, but it's defensible firewall paranoia (low confidence) — kept.
**Reverted:** 0.

**Overall:** simplify: applied 1 fix (rename completion)

**Quality Checks:** ruff clean; **112 passed, 0 failed** across the projection suite after the fix (regression check, no test asserted the old OTEL label). Committed `e4d61be2`.

### Simplify Report (verify rework pass, commit `d4505107`)

Re-ran the three teammates on the review-rework delta (`git diff e4d61be2 2d1f5a67`, test-only):
- **simplify-quality** — 4 findings, all residual "non-GM" vocabulary fossils. **Applied** (comment-only): swept every "non-GM" fossil across the touched test files (`test_secret_routed_rides_turn_tx`, `test_core_invariants`, `test_adr105_b1`, `test_projection_end_to_end_wiring` ×2) to complete the GM-vocabulary purge. Did a comprehensive grep beyond the 4 flagged to catch all of them in one pass.
- **simplify-reuse** — 3 findings (extract `_view()` / `_setup_tracing()` / `captured_watcher_events` to a shared `conftest.py`). **Deferred** — pre-existing cross-file test-infra duplication spanning ~12+ files, outside a behaviour-preserving deletion's scope. Logged as a Delivery Finding.
- **simplify-efficiency** — clean (noted one defensive-redundant assertion at `test_gm_axis_removed.py:122`; kept — it documents "not the deleted `gm_sees_all` branch").

**Overall:** simplify: applied 1 fix (non-GM vocabulary sweep). ruff clean; 24 passed on the affected non-DB files (comment-only change).

**Handoff:** To Portia (Reviewer) for re-review.

## Subagent Results (pass 1 — REJECT, historical)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | findings | 1 (+ green/lint) | confirmed 1 (the dormant b1 gm test), 0 dismissed |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 5 | confirmed 4 (1 high→genre_stage, others med/low), dismissed 1 (Protocol hasattr — empirically refuted) |
| 5 | reviewer-comment-analyzer | Yes | findings | 2 | confirmed 2 (stale non-GM fossils, low) |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 | confirmed 1 (OTEL-label coverage gap), 1 out-of-scope (pre-existing bare-except, views.py:429) |

**All received:** Yes (4 enabled returned; 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 1 High confirmed, 3 Medium confirmed, 4 Low confirmed, 1 dismissed (with evidence), 1 deferred (out of scope)

## Reviewer Assessment (pass 1 — REJECT, historical)

**Verdict: REJECT** — one High finding (unmet acceptance criterion) on a security-sensitive projection firewall, plus a cluster of cheap, in-scope test-quality gaps. The production deletion itself is complete, correct, and behaviour-preserving (verified) — the reject is about test completeness, not the source change.

**Subagent tag coverage:** `[TEST]` and `[DOC]` and `[RULE]` confirmed findings below; `[PREFLIGHT]` surfaced the High finding. The remaining dispatch lenses were disabled via `workflow.reviewer_subagents` and assessed by me directly where relevant: `[EDGE]` — N/A (deletion has no new boundary paths; the firewall fail-closed branches are unchanged and verified); `[SILENT]` — N/A in-diff (the one bare-except is pre-existing/untouched, deferred); `[SEC]` — assessed in the data-flow/security trace (firewall is strictly stricter post-deletion); `[TYPE]` — N/A (no new types; `PredicateContext`/`SessionGameStateView` annotations intact); `[SIMPLE]` — handled in the verify phase (the GM→player-excluded rename completion).

### Confirmed Findings

- **[HIGH][PREFLIGHT] Dormant sixth `gm_sees_all` assertion — unmet AC.** `tests/server/test_adr105_b1_secret_invariant_wiring.py::test_gm_sees_redacted_dispatch_through_production_path` (line 127) asserts a `"gm"` recipient sees a SECRET_NOTE canonically (`decision.include is True`), docstring "the GM short-circuit precedes the visibility gate" — *exactly* the behavior 71-35 deletes. It escaped RED/GREEN because the whole file is **skipped** (module-level `caverns_sunden deprecated → genre_workshopping` migration skip — verified via `pytest -rs`, unrelated to this story). This is the same class as the b3 test Dev fixed in-story; the skip merely hid it. Leaving it: (a) leaves AC "All is_gm-specific tests deleted" **unmet**, (b) is a latent landmine that fails when the caverns_sunden skip is lifted, and (c) ships the exact "GM short-circuit" contradiction the story exists to purge — a "dormant footgun inviting a future 'seat a GM' PR" in the story's own words. **Fix:** delete or rewrite to the post-deletion behavior (a `"gm"` id is a non-recipient → excluded), mirroring the b3 fix. My `player_id="gm"` sweep missed it because it uses `connected_players=["gm"]`; a broader sweep (done) confirms **no seventh**.

- **[MEDIUM][RULE] Renamed OTEL label has no positive assertion.** The verify-phase rename `invariant:gm_only_kind → invariant:player_excluded_kind` (a load-bearing OTEL source the GM panel reads — CLAUDE.md OTEL Observability Principle) is asserted *nowhere* positively. `test_thinking_is_player_excluded_never_routed_to_players` checks `include is False` but not `source == "invariant:player_excluded_kind"`; the contract module only asserts the *old* label is absent. A typo in the new label would pass every test. **Fix:** add `assert outcome.source == "invariant:player_excluded_kind"` to the thinking test.

- **[MEDIUM][TEST] Tautological `include_if` test.** `test_genre_stage.py::test_include_if_omits_when_predicate_false` uses `include_if: is_self()` (no arg) — `_is_self` with `field_ref=None` is unconditionally False for *every* viewer, so the test passes even if `include_if` dispatch were broken. TEA's `is_gm()→is_self()` rewrite preserved the original's degeneracy (the dead axis was also always-false here). The redact machinery is covered by sibling tests, but this specific `include_if` path is degenerate. **Fix:** use `is_self(text)` with a two-case payload (value == viewer char → include; != → omit).

- **[MEDIUM][TEST] Weak `gm_sees_all`-absence probe.** `test_gm_axis_removed.py::test_core_invariant_stage_never_emits_gm_sees_all` uses `STATE_UPDATE`, which is in no kind-set and is trivially `terminal=False` post-deletion — it never probes a kind the deleted GM branch would have short-circuited. Behavioral coverage exists in the b3 test, but the contract module's own probe is weak. **Fix:** add a `SECRET_NOTE` + `"gm"`-viewer case asserting `source == "invariant:visibility_gated"` (not `gm_sees_all`) and `terminal is True`.

- **[LOW][TEST] `alice_rows` not length-asserted** (`test_projection_end_to_end_wiring.py:132`): the replay equality at line ~139 would pass vacuously on two empty lists. Mitigated by assertion 1 (`cache_rows == 9` guarantees 3/player), so the risk is theoretical — but a `assert len(alice_rows) == 3` is a cheap guard.

- **[LOW][TEST] Exact predicate-set lock** (`test_gm_axis_removed.py:37`): asserting the full `PREDICATES` key set will break on any future predicate addition. Defensible as a deliberate firewall tripwire (a new asymmetry vector *should* force a test update), but it over-reaches the contract (`is_gm` absence is already proven at line 32). **Recommendation:** keep it but add a comment flagging it as an intentional tripwire (referencing the predicates.py add-a-predicate checklist).

- **[LOW][DOC] Stale "non-GM" naming fossils** (`test_core_invariants.py`): docstring "FAILS CLOSED for non-GM" (line 76) and function name `test_self_authored_missing_author_field_omits_for_all_non_gm` (line 139) are relics of the deleted axis — there is no GM counterpart to contrast against. **Fix:** drop "for non-GM" / rename to "...for_all_viewers". Sweep these with the b1 fix.

### Dismissed (with evidence)

- **[TEST] "Protocol `hasattr` is vacuous"** (test-analyzer, `test_gm_axis_removed.py:54`). **Challenged & dismissed.** Empirical proof: `hasattr(GameStateView, "is_gm")` returns **False** (deleted) while `hasattr(GameStateView, "seat_of")` returns **True** (present) — methods declared in a `Protocol` body with `...` *are* real class attributes, so `hasattr` discriminates present from absent. Independently corroborated: (a) the RED run reported this exact test failing ("is_gm still in GameStateViewProtocol type definition") when `is_gm` was present, proving it is not vacuous; (b) reviewer-rule-checker classified it compliant. The test-analyzer conflated structural-typing semantics with class-attribute presence.

### Deferred (out of scope)

- **[LOW][RULE] Pre-existing bare-except** at `views.py:429` (`except Exception: location_nbs = None`, no log/noqa). Flagged by rule-checker because views.py is touched, but **line 429 is not in this diff** — it is unrelated PARTY_STATUS location handling. Out of scope for 71-35; logged for a future cleanup. Not blocking.

### Rule Compliance (Python lang-review, 13 checks)

reviewer-rule-checker ran all 13 against 71 instances; I cross-checked the diff:

| # | Check | Verdict |
|---|-------|---------|
| 1 | Silent exception swallowing | PASS in-diff (the one flag, views.py:429, is pre-existing/untouched — deferred) |
| 2 | Mutable defaults | PASS — `field(default_factory=...)` used correctly in `SessionGameStateView` |
| 3 | Type annotations at boundaries | PASS — all changed signatures annotated |
| 4 | Logging coverage/correctness | PASS — **the removed `gm_identity_unwired` warning was an unimplemented-feature marker, not an error path; no error path left unlogged** (`party_zone_absent` warning retained) |
| 5 | Path handling | N/A — no file I/O in the diff |
| 6 | Test quality | **2 gaps** (OTEL-label not asserted; tautological include_if) — see findings; no vacuous `assert True`/zero-assertion tests; no source-text wiring tests (reflection/`dataclasses.fields` is the sanctioned tripwire) |
| 7 | Resource leaks | N/A in diff |
| 8 | Unsafe deserialization | PASS — `json.loads` on server-originated payloads, guarded by isinstance |
| 9 | Async pitfalls | N/A — synchronous |
| 10 | Import hygiene | PASS — `GameMode` removal verified genuinely unused; no star/circular imports added |
| 11 | Input validation at boundaries | PASS — firewall predicates fail-closed (return False) on bad/missing input |
| 12 | Dependency hygiene | N/A — no dep changes |
| 13 | Fix-introduced regressions | PASS — rename consistent; no OTEL emit lost (the deleted `gm_sees_all` branch emitted no watcher event) |

### Data-flow / wiring / security trace (my own)

- **[VERIFIED] Behaviour-preserving in production** — `build_game_state_view` (the sole production constructor) only ever set `gm_player_id=None`; no production path set it otherwise → `is_gm()` always False → `gm_sees_all` never fired. Only test-only `gm_player_id="gm"` paths change. (`views.py` diff; grep of `sidequest/`.)
- **[VERIFIED] No orphaned consumer** — nothing in `sidequest/` calls `view.is_gm()` outside the deleted branch; no genre pack uses `unless: is_gm()` (would now fail *loud* at pack-load via `validator._check_predicate`, honoring No Silent Fallbacks — not a silent leak).
- **[VERIFIED] Firewall still fails closed** — visibility-gated / self-authored / targeted branches unchanged; a `"gm"` id is now excluded from a SECRET_NOTE it is not a recipient of (confirmed by the b3 test, `include is False`).
- **[VERIFIED] OTEL label rename consistent & no consumer keys on the old string** — `invariants.py:188`; grep across `sidequest/` + `tests/`.

### Devil's Advocate

Argue this is broken. **First**, the most dangerous failure mode for a *projection firewall* is a silent leak — and this story deletes a branch that returned `include=True` (canonical). If any production path ever set `gm_player_id` to a real id, removing `gm_sees_all` would change who sees secrets. I chased this: `build_game_state_view` is the only production constructor and hard-codes `None`; the old `is_gm()` was `gm_player_id is not None and …` → always False; so in production the deleted branch was unreachable. The change is a no-op in prod and only alters test fixtures that fabricated a GM. Verified, not assumed. **Second**, could the deletion have *removed* a real exclusion and started *leaking*? No — the deleted branch was the only `include=True` short-circuit; everything below it (targeted, visibility-gated fail-closed, self-echo, player-excluded) is intact and still returns `include=False` for non-recipients. The b3 test now positively asserts a `"gm"` viewer is *excluded* from a private segment — the firewall got *stricter*, not looser. **Third**, the renamed OTEL label: a confused operator reading the GM panel after this lands sees `invariant:player_excluded_kind` where dashboards/runbooks might say `gm_only_kind`. I grep-verified no code/test/dashboard in the repo keys on the old string, and the GM panel renders labels dynamically — so no correlation breaks; but the **untested** new label (finding) means a future typo would silently mislabel a firewall decision, which for a lie-detector OTEL surface is exactly the kind of thing CLAUDE.md says must be asserted. **Fourth**, the dormant b1 test: a maintainer resolving the caverns_sunden migration un-skips the file, hits a failing "GM sees canonical" assertion, and — not knowing 71-35 deleted that behavior — might "fix" it by *re-seating a GM*, reintroducing the category error. That is the concrete future harm that justifies fixing it now while the context is fresh. **Conclusion:** the source deletion is sound and the firewall is strictly safer; the breakage risk is entirely in *test debt* (a dormant contradiction + an unasserted security-relevant OTEL label), which is precisely what this reject closes.

### Deviation Audit

- **TEA — Rewrote genre_stage leaves_unmasked instead of deleting** → ✓ ACCEPTED: preserves the unmask-path machinery coverage under a surviving predicate; behaviourally sound.
- **TEA — Scope expansion (~10 extra files)** → ✓ ACCEPTED: the literal list was an incomplete grep; full migration is correct and user-confirmed.
- **TEA — Kept the audited `thinking` test** → ✓ ACCEPTED: it exercises the surviving `PLAYER_EXCLUDED_KINDS` branch, not is_gm routing. (But see finding: it should also assert the OTEL label.)
- **Dev — Modified the b3 test to complete the gm_sees_all deletion** → ✓ ACCEPTED: legitimate completion of a story-mandated deletion, not test-gaming; the rewrite asserts correct post-deletion exclusion. *Note: the b1 dormant test is the same class and must get the same treatment (High finding).*
- **Dev — Renamed `GM_ONLY_KINDS → PLAYER_EXCLUDED_KINDS`** → ✓ ACCEPTED: purges misleading GM naming from a firewall whose raison d'être is that the GM seat is a category error; contained, grep-verified. (Completed in verify with the OTEL-label/test-name follow-through — but left the OTEL label unasserted; see finding.)

**Decision:** Hand back to **Puck (Dev)** for a surgical fix pass (one required + cheap in-scope strengthening), then re-verify and re-review.

## Subagent Results

(Pass 2 — re-review after rework `2d1f5a67` + `d4505107`. Same toggles as pass 1: 4 enabled, 5 disabled.)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (136 passed/0 failed/2 pre-existing skips; lint clean; 0 lingering is_gm in live code) | N/A — confirms all pass-1 fixes resolved |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | N/A — disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 3 (all LOW/MED test-strengthening), dismissed 1 (schema-layer round-trip — behavior covered elsewhere); also confirmed all 4 pass-1 fixes genuinely resolved |
| 5 | reviewer-comment-analyzer | Yes | findings | 3 | confirmed 2 (LOW — label/wording), dismissed 1 ("GM panel" — established project vocabulary, CLAUDE.md) |
| 6 | reviewer-type-design | No | Skipped | disabled | N/A — disabled via settings |
| 7 | reviewer-security | No | Skipped | disabled | N/A — disabled via settings |
| 8 | reviewer-simplifier | No | Skipped | disabled | N/A — disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | 0 violations (13 checks + 4 project rules, 67 instances) | N/A — confirms deletion complete, fail-loud, OTEL label pinned |

**All received:** Yes (4 enabled returned; 5 disabled via `workflow.reviewer_subagents`)
**Total findings:** 0 High/Critical; 7 Low/Medium (5 confirmed non-blocking, 2 dismissed with rationale). All pass-1 findings confirmed resolved.

## Reviewer Assessment

**Verdict: APPROVED** — pass 2 (re-review after the rework). The pass-1 High finding (the dormant sixth `gm_sees_all` assertion) and all pass-1 Medium findings are **resolved and confirmed** by preflight + test-analyzer + rule-checker. rule-checker is **clean** (0 violations / 13 checks + 4 project rules). Pass-2 surfaced only diminishing-returns test/comment refinements — no Critical/High — where the relevant coverage already exists elsewhere. Blocking another rework loop over them would be unproductive perfectionism on a verified-correct, behaviour-preserving security deletion.

**Subagent tag coverage:** `[PREFLIGHT]` green; `[TEST]` and `[DOC]` non-blocking refinements below; `[RULE]` clean. Disabled lenses assessed directly: `[EDGE]` N/A (no new branches; firewall fail-closed paths unchanged + verified strictly stricter); `[SILENT]` N/A in-diff (the one bare-except is pre-existing/untouched — rule-checker confirmed); `[SEC]` firewall is strictly stricter post-deletion (a `"gm"` id is now excluded — b3 + b1 assert it); `[TYPE]` N/A (no new types); `[SIMPLE]` handled across verify passes (rename completion + non-GM vocabulary sweep).

### Pass-1 findings — resolution confirmed
- **[HIGH] dormant `gm_sees_all` (b1)** → RESOLVED: rewritten to `test_no_gm_seat_dispatch_through_production_path` asserting `include is False` / empty payload for a `"gm"` recipient. test-analyzer confirms it's meaningful (drives the structural visibility gate). AC "All is_gm-specific tests deleted" now **met**.
- **[MED] OTEL label unasserted** → RESOLVED: `test_core_invariants.py:155` now pins `source == "invariant:player_excluded_kind"` (rule-checker OTEL rule: compliant).
- **[MED] tautological `include_if`** → RESOLVED: `test_include_if_dispatches_on_predicate` uses `is_self(text)` exercising both branches (rule-checker: "strictly richer, not weaker").
- **[LOW] stale "non-GM" fossils** → RESOLVED: comprehensive sweep; comment-analyzer found no remaining current-state GM-contrast fossils.

### Pass-2 findings (all non-blocking; captured for optional future polish)
- **[LOW][TEST]** `test_gm_axis_removed.py:106` — the STATE_UPDATE loop's `source != "invariant:gm_sees_all"` is weak (source is `None` there). **Confirmed** (matches no-vacuous rule) but **downgraded to LOW**: the loop's `terminal is False` assertion IS meaningful, and the SECRET_NOTE block (added in rework) is the load-bearing anchor — the test is not vacuous overall. Optional one-line strengthen: `assert outcome.source is None`.
- **[LOW][TEST]** `test_core_invariants.py:52` — `test_plain_narration_is_non_terminal` could also pin `assert outcome.source is None`. Non-blocking.
- **[LOW][TEST]** `test_projection_end_to_end_wiring.py:131` — the e2e exercises only the masking direction of `is_self(text)`; the unmask branch is covered in `test_genre_stage.py::test_redact_fields_leaves_unmasked_when_predicate_holds`. Non-blocking (coverage exists).
- **[DISMISSED][TEST]** `test_rules_schema.py:109` round-trip — that file is the **schema-parse** layer by design (its module docstring: "Rule schema parsing"); runtime behavior of `is_self()` is covered in `test_predicates.py` / `test_genre_stage.py`. Dismissed: asking a parse test to do behavior testing conflates layers.
- **[LOW][DOC]** `invariants.py:141` — the "1b" branch label faithfully preserves the original `2b` sub-grouping convention (targeted + visibility-gated as recipient-set guards); pre-existing style, not a regression. Optional: renumber 1/2/3/4. Non-blocking.
- **[DISMISSED][DOC]** `invariants.py:148` "GM panel" — **established project vocabulary**: per CLAUDE.md "the GM panel is the lie detector" — it names the dev/OTEL observability dashboard, NOT a GM player seat. Unchanged pre-existing line; renaming would diverge from project convention. Dismissed citing CLAUDE.md.
- **[LOW][DOC]** `test_core_invariants.py:21` — the rewritten "a player fell through" docstring reads slightly backwards; cosmetic. Non-blocking.

### Devil's Advocate (pass 2)

Argue pass 2 should have rejected. The strongest case: finding #1 is a vacuous assertion that matches the project's no-vacuous-assertions rule, which I am forbidden from *dismissing*. True — so I did not dismiss it; I confirmed it and downgraded severity with rationale, which the rubric expressly permits. Is the downgrade honest? The assertion `source != "invariant:gm_sees_all"` is indeed always-true for STATE_UPDATE, but it sits beside `terminal is False` (a real assertion that STATE_UPDATE is claimed by no invariant) and below a SECRET_NOTE block that positively asserts `visibility_gated` exclusion for a `"gm"` viewer — the exact regression anchor. A test that would fail if `gm_sees_all` were re-added is not a test that "catches nothing." Second case: am I rubber-stamping by approving with seven open findings? No — every one is a test/comment *strengthening* where coverage already exists elsewhere (the unmask branch in test_genre_stage; the no-arg `is_self` behavior in test_predicates), or established convention (GM panel), or faithful preservation (1b). The production deletion is rule-checker-clean and preflight-green; the firewall is verified strictly *stricter*. The real risk of a third reject is an asymptotic polish loop — each pass finds one more assertion to tighten — at real cost, with zero correctness or security benefit. The reviewer's mandate is to block Critical/High, not to demand a perfect test suite in perpetuity. Approving here, with the cheap improvements logged for an optional future touch, is the correct disposition.

### Deviation Audit (pass 2)

No new deviations since pass 1. The pass-1 deviation stamps (`### Reviewer (audit)`) stand: all TEA/Dev deviations ACCEPTED; the previously-FLAGGED items (b1 dormant test; unasserted OTEL label) are now **resolved** by the rework and re-stamped ✓ ACCEPTED here.

**Decision:** Proceed to spec-reconcile (Architect) → SM finish. Approved for merge.

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-06-01T09:59:22Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-01T00:00:00Z | 2026-06-01T08:11:48Z | 8h 11m |
| red | 2026-06-01T08:11:48Z | 2026-06-01T09:09:57Z | 58m 9s |
| green | 2026-06-01T09:09:57Z | 2026-06-01T09:19:07Z | 9m 10s |
| spec-check | 2026-06-01T09:19:07Z | 2026-06-01T09:20:59Z | 1m 52s |
| verify | 2026-06-01T09:20:59Z | 2026-06-01T09:26:27Z | 5m 28s |
| review | 2026-06-01T09:26:27Z | 2026-06-01T09:37:51Z | 11m 24s |
| green | 2026-06-01T09:37:51Z | 2026-06-01T09:43:22Z | 5m 31s |
| spec-check | 2026-06-01T09:43:22Z | 2026-06-01T09:44:15Z | 53s |
| verify | 2026-06-01T09:44:15Z | 2026-06-01T09:48:54Z | 4m 39s |
| review | 2026-06-01T09:48:54Z | 2026-06-01T09:57:32Z | 8m 38s |
| spec-reconcile | 2026-06-01T09:57:32Z | 2026-06-01T09:59:22Z | 1m 50s |
| finish | 2026-06-01T09:59:22Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Gap** (non-blocking): The story's test-churn list undercounts. It named ~8 construction sites + 3 rewrite files; reality is **16 construction files + ~10 fixture files**. Files the story missed (now handled): `test_genre_stage.py`, `test_session_game_state_view.py`, `test_envelope_and_view.py`, `test_composed_filter.py`, `test_cli/test_projection_check.py`, `test_genre/test_loader_projection.py`, `test_view_zones.py`, `test_visibility_tag_rule.py`, `test_projection_otel.py`, `test_secret_routed_rides_turn_tx.py`, `test_group_g_e2e.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): The validator needs **no `is_gm` signature-map change**. `validator.py::_check_predicate` reads the `PREDICATES` registry directly (`call.predicate not in PREDICATES`) — there is no separate signature map. Removing `is_gm` from `predicates.py::PREDICATES` is the *only* validation-layer change. (The story's "add a validator entry (Task 10 signature map)" was a process note in the `predicates.py` docstring, not a live separate map.) Affects `sidequest/game/projection/validator.py` (no change needed — just don't go looking for a map to edit). *Found by TEA during test design.*
- **Gap** (non-blocking): Several `invariants.py` docstrings/comments go stale when the `gm_sees_all` branch is deleted and must be updated by Dev: the module docstring line "GM sees canonical (Task 5)" (line ~6), the inline comment "GM already short-circuited at branch 1 (canonical)" (line ~149), and the `GM_ONLY_KINDS` comment "GM gets them via the GM invariant" (line ~83). Also `server/views.py` carries a whole "**GM identity wiring (C1, still partial)**" docstring block (~lines 115-129) to remove. Affects `sidequest/game/projection/invariants.py`, `sidequest/server/views.py`. *Found by TEA during test design.*
- **Improvement** (non-blocking): In `server/views.py`, dropping `gm_player_id` from the two `SessionGameStateView(...)` constructions (lines ~146, ~262) leaves the `gm_player_id` local (line ~150) unused → ruff F841 will force its removal. But the `gm_identity_unwired` warning block (~151-169) and the `_gm_wiring_warned` flag are **not** ruff-forced (they don't reference the field) — the new MP warning-absence test in `test_session_handler_view.py` is what drives their removal. Affects `sidequest/server/views.py`. *Found by TEA during test design.*

### Dev (implementation)
- **Gap** (non-blocking, RESOLVED by Dev): A **fifth `gm_sees_all` assertion** survived the RED phase — `tests/agents/test_adr105_b3_private_segments.py::test_narration_segment_firewalled_for_non_owner` asserted `gm` (player_id) sees a withheld NARRATION_SEGMENT canonically (`include is True`). It was missed because that file was on TEA's "kwarg-drop only" list and its body wasn't read for gm-behavior. It surfaced as the lone GREEN failure (it's a DB-backed test not in TEA's non-DB RED run). Dev rewrote the assertion to the correct post-deletion behavior (a `gm` player_id is a non-recipient → excluded). *Found by Dev during implementation.* **Process note:** kwarg-drop-only files still need a body scan for gm-viewer assertions; a grep for `player_id="gm"` across all touched files is the cheap guard.
- **Improvement** (non-blocking): `GM_ONLY_KINDS` in `invariants.py` was renamed to `PLAYER_EXCLUDED_KINDS` (only one internal reference, no external/test consumers — verified by grep). The concept (THINKING never routed to players; narrator receives it server-side) survives; only the now-misleading "GM" name changed. Affects `sidequest/game/projection/invariants.py`. *Found by Dev during implementation.*

### TEA (test verification)
- **Improvement** (non-blocking, OUT OF SCOPE for 71-35): `invariants.py::_match_to_field` (the scalar-or-list `to`-field matcher) duplicates `genre_stage.py::_match_to_value` — identical logic in two files. Flagged by the verify simplify-reuse pass at **high** confidence, but it is **pre-existing** (untouched by this story's diff) and extracting a shared helper would touch `genre_stage.py`, outside the GM-axis deletion. Not applied — deferred to a future cleanup story. Affects `sidequest/game/projection/invariants.py`, `sidequest/game/projection/genre_stage.py` (extract a shared `_match_to_field` helper). *Found by TEA during test verification (simplify-reuse).*
- **Improvement** (non-blocking, OUT OF SCOPE): Projection test files repeat helper boilerplate — `_view()` factories (~5 files), `_setup_tracing()` (2 files), and the `captured_watcher_events` monkeypatch fixture (~12 files). A shared `tests/game/projection/conftest.py` would consolidate them. Pre-existing; deferred to a future test-infra cleanup story. Affects `tests/game/projection/*` (extract shared fixtures to a conftest). *Found by TEA during test verification (simplify-reuse, rework pass).*

### Reviewer (code review)
- **Gap** (blocking): A sixth, dormant `gm_sees_all` assertion survives — `test_gm_sees_redacted_dispatch_through_production_path` asserts a `"gm"` recipient sees a SECRET_NOTE canonically. Skipped behind the caverns_sunden migration, so it escaped RED/GREEN; leaves AC "All is_gm-specific tests deleted" unmet and is a latent landmine. Affects `tests/server/test_adr105_b1_secret_invariant_wiring.py` (delete or rewrite the test to assert the post-deletion exclusion, mirroring the b3 fix). *Found by Reviewer during code review.*
- **Gap** (non-blocking): The renamed OTEL source label `invariant:player_excluded_kind` is never positively asserted — a typo would pass all tests, defeating the GM-panel lie-detector. Affects `tests/game/projection/test_core_invariants.py` (add `assert outcome.source == "invariant:player_excluded_kind"` to `test_thinking_is_player_excluded_never_routed_to_players`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): `test_genre_stage.py::test_include_if_omits_when_predicate_false` is tautological (`include_if: is_self()` is unconditionally False). Affects `tests/game/projection/test_genre_stage.py` (use `is_self(text)` with True/False cases). *Found by Reviewer during code review.*
- **Improvement** (non-blocking): Stale "non-GM" naming fossils. Affects `tests/game/projection/test_core_invariants.py` (drop "for non-GM" in the line-76 docstring; rename `test_self_authored_missing_author_field_omits_for_all_non_gm` → `..._for_all_viewers`). *Found by Reviewer during code review.*
- **Improvement** (non-blocking, deferred): Pre-existing bare-except at `sidequest/server/views.py:429` (no log/noqa) — out of scope for 71-35 (not in diff); flagged for a future cleanup. *Found by Reviewer during code review.*
- **Improvement** (non-blocking, pass 2): Optional test-strengthening — pin `assert outcome.source is None` in `test_gm_axis_removed.py::test_core_invariant_stage_never_emits_gm_sees_all` (STATE_UPDATE loop) and `test_core_invariants.py::test_plain_narration_is_non_terminal`; optionally add an unmask case to the e2e single-truth test. Coverage already exists elsewhere (test_genre_stage). Affects `tests/game/projection/*`. *Found by Reviewer during code review (pass 2).*

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### TEA (test design)
- **Rewrote a "delete" candidate instead of deleting it**
  - Spec source: context-story-71-35.md, TEST CHURN — "REWRITE fixtures using 'unless: is_gm()' as their representative predicate to a surviving predicate (is_self)"
  - Spec text: implies the only is_gm-true-dependent genre_stage test would be dropped along with the gm_sees_all behavior
  - Implementation: `test_genre_stage::test_redact_fields_leaves_unmasked_when_predicate_holds` (which relied on `is_gm` being TRUE for a gm viewer) was **rewritten** to use `is_self(text)` with the payload field matching the viewer's character id, rather than deleted — preserving the "predicate holds → field stays unmasked" machinery coverage.
  - Rationale: deleting it would lose genuine coverage of the unmask path; the rewrite keeps it and is behaviourally equivalent under a surviving predicate.
  - Severity: minor
  - Forward impact: none
- **Scope expansion beyond the story's literal file list**
  - Spec source: context-story-71-35.md, TEST CHURN file list
  - Spec text: enumerated ~8 construction sites + 3 rewrite files
  - Implementation: migrated **~10 additional files** the list omitted (see Delivery Findings Gap). Confirmed with the user (Good Patron) before proceeding: "Full correct churn" + "Uniform intentional RED is fine."
  - Rationale: the story's intent is full deletion of the axis; the literal list was an incomplete grep. A partial migration would leave a broken suite for Dev.
  - Severity: minor
  - Forward impact: larger RED diff (23 files); Dev's GREEN is correspondingly a clean "delete source, suite goes green."
- **Audit resolution: kept a flagged test**
  - Spec source: context-story-71-35.md, TEST CHURN — "test_core_invariants.py::test_thinking_is_gm_only_never_routed_to_players (audit — confirm it's about is_gm routing vs thinking routing)"
  - Spec text: requested an audit, outcome unspecified
  - Implementation: **kept** the test. It asserts a *non-GM* viewer (alice) is denied THINKING — the surviving `GM_ONLY_KINDS` branch (branch 4), not is_gm routing. Only the construction kwarg was dropped.
  - Rationale: the THINKING-exclusion-for-players behavior is preserved by this deletion; the test remains valid coverage.
  - Severity: minor
  - Forward impact: none

### Dev (implementation)
- **Modified a test to complete the story-mandated gm_sees_all deletion**
  - Spec source: context-story-71-35.md — "remove the gm_sees_all branch … DELETE is_gm-specific tests"; tests TEA wrote (RED)
  - Spec text: the story deletes the gm_sees_all short-circuit; TEA deleted four gm-sees-canonical assertions but `test_adr105_b3_private_segments.py` kept a fifth (asserted `gm` sees a withheld NARRATION_SEGMENT canonically)
  - Implementation: Dev rewrote that assertion from `gm.include is True` (the deleted gm_sees_all behavior) to `gm.include is False` (a `gm` player_id is a non-recipient → excluded, the correct post-deletion firewall behavior). This is Dev editing a test — flagged for Reviewer.
  - Rationale: the assertion tested behavior the story explicitly deletes; it is the same category as the four assertions TEA already removed. Leaving it would either fail GREEN or require re-asserting deleted behavior. Not test-gaming — completion of the mandated deletion. The narrator (lie-detector) reads canonical state server-side, not as a projection recipient.
  - Severity: minor
  - Forward impact: none — the owner-sees / non-owner-excluded firewall coverage is intact; only the GM-seat assertion changed.
- **Renamed GM_ONLY_KINDS → PLAYER_EXCLUDED_KINDS (clarity, not behavior)**
  - Spec source: context-story-71-35.md, Design Notes — "behaviour-preserving deletion of dead code"
  - Spec text: the story removes the GM axis but does not call for renaming the surviving THINKING-exclusion constant
  - Implementation: renamed the constant (single internal reference, no external/test consumers) because "GM_ONLY_KINDS" is misleading once there is no GM seat; the behavior (THINKING never routed to players) is unchanged.
  - Rationale: avoids leaving dead "GM" naming that implies a GM recipient exists; contained and verified by grep.
  - Severity: trivial
  - Forward impact: none

### Reviewer (audit)
- **TEA — Rewrote genre_stage leaves_unmasked instead of deleting** → ✓ ACCEPTED by Reviewer: preserves unmask-path machinery coverage under a surviving predicate; behaviourally sound.
- **TEA — Scope expansion (~10 extra files)** → ✓ ACCEPTED by Reviewer: the literal list was an incomplete grep; full migration is correct and user-confirmed.
- **TEA — Kept the audited `thinking` test** → ✓ ACCEPTED by Reviewer (exercises the surviving `PLAYER_EXCLUDED_KINDS` branch) — but FLAGGED a follow-up: it must also assert `source == "invariant:player_excluded_kind"` (OTEL-label coverage gap, see findings).
- **Dev — Modified the b3 test to complete the gm_sees_all deletion** → ✓ ACCEPTED by Reviewer: legitimate completion of a story-mandated deletion (correct post-deletion exclusion), not test-gaming. *The b1 dormant test is the same class and was NOT completed — that gap is the High finding driving this REJECT.*
- **Dev — Renamed `GM_ONLY_KINDS → PLAYER_EXCLUDED_KINDS`** → ✓ ACCEPTED by Reviewer: purges misleading GM naming from the firewall; contained, grep-verified. FLAGGED follow-up: the renamed OTEL label is left unasserted (see findings).
- **UNDOCUMENTED (Reviewer-found):** A sixth `gm_sees_all` assertion — `test_adr105_b1_secret_invariant_wiring.py::test_gm_sees_redacted_dispatch_through_production_path` — survives (dormant behind the caverns_sunden skip) and asserts the deleted GM short-circuit. Neither TEA nor Dev logged it (it never ran in RED/GREEN due to the skip). Severity: **High** — unmet AC "All is_gm-specific tests deleted." → **RESOLVED in rework** (`2d1f5a67`): rewritten to `test_no_gm_seat_dispatch_through_production_path` asserting post-deletion exclusion; AC now met.

### Architect (reconcile)

**Existing-entry verification:** all five TEA/Dev deviation entries are accurate — spec source `sprint/context/context-story-71-35.md` exists and the quoted/paraphrased spec text matches it; the implementation descriptions match the committed code; forward-impact is correctly "none" (no sibling story in epic 71 depends on the `is_gm` axis). The Reviewer-audit stamps and the (now-resolved) UNDOCUMENTED b1 entry are accurate. No corrections needed.

**AC deferral:** none — no AC was deferred or DESCOPED; the AC-deferral verification step is a no-op. All ACs are DONE (the previously-unmet "All is_gm-specific tests deleted" was completed in the review-rework).

**Missed deviation — formally documented for the audit:**
- **OTEL source-label rename emitted on the wire** (`invariant:gm_only_kind` → `invariant:player_excluded_kind`)
  - Spec source: context-story-71-35.md, Design Notes
  - Spec text: "This is a behaviour-preserving deletion of dead code, not a refactor with side effects."
  - Implementation: beyond deleting the axis, the surviving THINKING-exclusion branch's emitted OTEL `source` string was renamed (alongside the `GM_ONLY_KINDS`→`PLAYER_EXCLUDED_KINDS` constant). This changes a value emitted on the telemetry surface the GM panel reads — strictly a *side effect* relative to "behaviour-preserving deletion."
  - Rationale: the old label `gm_only_kind` perpetuated the exact "GM seat" category error the story exists to purge; the rename makes the telemetry honest. Verified safe: grep across `sidequest/` + `tests/` confirms **no consumer** keyed on the old string (the GM panel renders source labels dynamically), and the new label is now positively asserted (`test_core_invariants.py:155`).
  - Severity: minor
  - Forward impact: a GM-panel operator or runbook that visually recognized `invariant:gm_only_kind` will now see `invariant:player_excluded_kind`; no automated consumer breaks. If any out-of-repo dashboard hard-codes the old string, it should be updated — none found in-repo.

No other missed deviations. The ~18-file test-churn breadth (vs the story's ~11-file literal list) and the `1/1b/2/3` branch renumber are already captured under TEA "Scope expansion" and Dev deviations respectively; the non-GM vocabulary sweep and b1 rewrite brought the work *into* spec compliance and are documented in the verify/rework assessments.