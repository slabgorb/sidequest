---
story_id: "45-46"
jira_key: ""
epic: ""
workflow: "trivial"
---
# Story 45-46: Wave 1 cleanup — drop EncounterTag deprecation alias

## Story Details
- **ID:** 45-46
- **Jira Key:** (not applicable — no Jira in this project)
- **Workflow:** trivial
- **Stack Parent:** none
- **Repos:** sidequest-server

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-12T18:47:26Z
**Round-Trip Count:** 1

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-12T20:00:00Z | 2026-05-12T18:10:32Z | -6568s |
| implement | 2026-05-12T18:10:32Z | 2026-05-12T18:20:13Z | 9m 41s |
| review | 2026-05-12T18:20:13Z | 2026-05-12T18:31:13Z | 11m |
| implement | 2026-05-12T18:31:13Z | 2026-05-12T18:37:07Z | 5m 54s |
| review | 2026-05-12T18:37:07Z | 2026-05-12T18:47:26Z | 10m 19s |
| finish | 2026-05-12T18:47:26Z | - | - |

## Summary
Wave 1 (story 45-43) introduced a deprecation alias for the renamed `game.session.EncounterTag` → `NpcEncounterLogTag`, wrapped in a `sidequest/game/__init__.py` module-level `__getattr__` that fires `DeprecationWarning`. Per spec: "one release window, then drops it."

This chore drops the alias.

**Removal targets:**
- The `__getattr__` shim in `sidequest/game/__init__.py`
- The `__all__.append('EncounterTag')` line in `sidequest/game/__init__.py`
- The alias-specific tests in `tests/game/test_npc_encounter_log_tag_rename.py`

**Note (session reconstruction):** This file was inadvertently overwritten by the `testing-runner` subagent during the rework-verification step at 2026-05-12 ~18:40 UTC (known issue: testing-runner can stomp `.session/*-session.md`). Reconstructed from conversation context — all prior agent assessments, deviation logs, and subagent results below are faithful copies of what existed before the overwrite.

## Delivery Findings

### Reviewer (code review — round 2 deferred findings)
- **Improvement** (non-blocking; LOW): Rewritten parenthetical at `sidequest-server/sidequest/game/session.py:63` reads backwards — "(re-exported from this module)" applies the re-export label to `session.py` (the SOURCE module), but the actual re-exporter is `sidequest/game/__init__.py`. Suggested polish: "(re-exported via :mod:`sidequest.game`)". *Found by Reviewer round 2.*
- **Improvement** (non-blocking; LOW): One-sided regression guard at `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py:55`. The current `assert not hasattr(sidequest.game, "EncounterTag")` catches alias re-introduction but does not assert the canonical replacement path `sidequest.game.NpcEncounterLogTag` is still accessible. Suggested bidirectional polish: `assert hasattr(sidequest.game, "NpcEncounterLogTag"), "package-level re-export must remain"`. This simultaneously closes a separate finding that no test exercises the package-level re-export path advertised by the post-rework docstring. *Found by Reviewer round 2.*
- **Improvement** (non-blocking; LOW): Function-scope `import sidequest.game` at `tests/game/test_npc_encounter_log_tag_rename.py:40`. Module-scope placement would be cleaner; no circular-import or attribute-mutation risk in this codebase. *Found by Reviewer round 2.*

### Reviewer (code review — round 1 deferred findings)
- **Improvement** (non-blocking; informational): The class docstring for `NpcEncounterLogTag` at `sidequest-server/sidequest/game/session.py:54-63` references "S4 of the snapshot split-brain cleanup, 2026-05-04" — internal-history that's now several waves back. Optional: trim the historical noise on a future polish pass.
  *Found by Reviewer during round-1 code review.*
- **Improvement** (non-blocking): The orphan `git stash` entry in `sidequest-server` (from Dev's diagnostic step that triggered the auto-mode denial) should be dropped by Keith manually. The stash content matches the committed code (verified), so it's housekeeping debt, not lost work.
  *Found by Reviewer during round-1 code review.*

### Dev (implementation)
- **Gap** (non-blocking for 45-46; potentially blocking elsewhere): Victoria genre pack tests are failing on `develop` independently of this story.
  Affects `sidequest-server/tests/genre/test_victoria_class_kits.py` (5 failures: `test_victoria_loads`, `test_victoria_has_seven_class_kits`, `test_victoria_kit_items_exist_in_inventory`, `test_victoria_doctor_kit_guarantees_signature_items`, `test_victoria_doctor_chargen_produces_signature_items_end_to_end` — root cause: `pack.classes` is empty list and `pack.equipment_tables is None`, so the victoria genre pack does not declare `classes.yaml` / `equipment_tables.yaml` correctly).
  Story 49-4 ("test(49-4): wiring tests for victoria callings + class_kit chargen") landed in commit 3ebbf0e expecting the data, but the genre-pack data side appears not to have followed. Confirmed unrelated to 45-46: `grep EncounterTag tests/genre/test_victoria_class_kits.py` returns no matches. Rework verification noted an additional 1 pre-existing test-isolation flake in `test_chargen_dispatch.py` (passes individually), also unrelated.
  *Found by Dev during implementation.*

## Design Deviations

### Dev (rework round 1)
- **No additional deviations.** Rework applies the two Reviewer-mandated fixes verbatim (docstring rewrite at `session.py:60-67`, single-line regression guard added to `test_scene_momentum_encounter_tag_unchanged`). Scope bounded; no boy-scouting.

### Dev (implementation)
- **Surgical removal of two alias-specific tests instead of deleting the entire `test_npc_encounter_log_tag_rename.py` file**
  - Spec source: Sm Assessment (this session), removal target #3
  - Spec text: "The test file `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` (it asserts the `DeprecationWarning` fires — meaningless once the shim is gone)"
  - Implementation: Deleted only `test_old_name_alias_still_works` and `test_old_name_alias_emits_deprecation_warning`; kept `test_npc_encounter_log_tag_importable_under_new_name`, `test_narrative_entry_uses_npc_encounter_log_tag`, and `test_scene_momentum_encounter_tag_unchanged`. Removed the now-unused `import pytest`. Updated the module docstring to reflect post-removal state.
  - Rationale: Two of the five tests verify the deprecation surface (which is being removed) — those are dead. The other three are durable post-rename invariants: (1) the new name imports correctly, (2) `NarrativeEntry` is wired to the new type, and (3) the unrelated scene-momentum `EncounterTag` (in `sidequest/game/encounter_tag.py`) stays distinct from the renamed log tag. Test #3 is specifically an anti-merge regression for the two `EncounterTag` classes — exactly the confusion that motivated the rename. Deleting it would lose protection that survives the alias.
  - Severity: minor
  - Forward impact: none — improves regression coverage relative to a whole-file delete.

### Reviewer (audit)
- **Dev's deviation — Surgical removal of two alias-specific tests instead of deleting whole file** → ✓ ACCEPTED by Reviewer. The reasoning is correct: three of the five tests are durable post-rename invariants (importability, NarrativeEntry wiring, anti-merge regression). Deleting the whole file would have removed `test_scene_momentum_encounter_tag_unchanged`, which is the *only* test that distinguishes the two `EncounterTag` types — a load-bearing anti-confusion regression. SM Assessment's "delete whole file" direction was based on a quick read that conflated all tests with alias-specific tests; Dev's reading is the correct one.

## Sm Assessment

**Scope confirmed (trivial, 1pt, single repo: sidequest-server).** Pure deletion chore — Wave 1 deprecation window is now closed and the alias must come out.

**Removal targets (exact, per story spec):**
1. The module-level `__getattr__` shim in `sidequest-server/sidequest/game/__init__.py`
2. The `__all__.append("EncounterTag")` line in the same file
3. The test file `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` (per Dev: surgical removal of alias-specific tests only — see deviation log)

Routing: phased workflow → handoff to **dev** for the `implement` phase.

## Dev Assessment (initial implementation)

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/__init__.py` — removed the `__all__.append("EncounterTag")` line, the `__getattr__` deprecation shim, and the 12-line comment block. Net: -28 lines, no insertions.
- `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` — removed two alias-specific tests; kept three durable rename-stability tests; dropped now-unused `import pytest`; rewrote module docstring. Net: -41 lines, 3 insertions.

**Tests:** 5060 passing, 5 failing (all pre-existing victoria genre-pack failures), 58 skipped. Lint PASS.

**Branch:** `feat/45-46-drop-encountertag-alias` on `sidequest-server` (commit 9e34fdb).

**Process note:** Accidentally invoked `git stash --keep-index` during diagnostic — auto-mode classifier correctly denied follow-up `git stash pop`. Re-applied both Edits from context (no information loss). An orphan stash entry remains in `sidequest-server`; Keith should drop it manually.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (tests GREEN modulo 5 pre-existing victoria failures; lint PASS; working tree CLEAN; commit scope correct) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 3 | confirmed 1, dismissed 2 |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 (stale docstring at `sidequest-server/sidequest/game/session.py:61-62`) | confirmed 1 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | clean | none (18/18 checks pass) | N/A |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 2 confirmed, 2 dismissed (with rationale), 0 deferred

### Devil's Advocate (Reviewer)

What could be wrong with this 66-line deletion?

1. **Save-file compatibility.** Verified `sidequest/game/persistence.py` uses Pydantic JSON, not pickle. Non-issue.
2. **External-repo callers.** Grep across the entire orchestrator workspace returns zero matches for `sidequest.game.EncounterTag` imports outside the diff. Non-issue.
3. **`__all__` integrity.** Star imports of `sidequest.game` no longer leak `EncounterTag`. Spot-check shows no `from sidequest.game import *` consumers. Non-issue.
4. **Anti-merge regression test.** `test_scene_momentum_encounter_tag_unchanged` preserved.
5. **Shim's pragma comment.** Gone with the shim itself. Clean.
6. **The `import warnings` deferral.** Lazy import inside the deleted shim; no other `__init__.py` code references `warnings`. Clean.
7. **The dangling stash.** Functional impact: none (verified via `git diff --stat`). Housekeeping debt only.
8. **`NpcEncounterLogTag` accepting legacy `"EncounterTag"` dict keys?** No — `model_config = {"extra": "forbid"}` at `session.py:65`.

The devil's advocate uncovers no new findings beyond the two confirmed.

### Rule Compliance (Reviewer)

All 13 Python lang-review rules + 5 CLAUDE.md project rules: clean. Highlights:
- **#10 Import hygiene:** `__all__` integrity verified — `NpcEncounterLogTag` remains at `__init__.py:185`; appended `"EncounterTag"` is gone; no orphan strings.
- **CLAUDE.md "No Silent Fallbacks":** Failure mode now LOUDER (Python's native `AttributeError` instead of shim with `DeprecationWarning`). ✓
- **CLAUDE.md "Verify Wiring":** `NpcEncounterLogTag` wired at `__init__.py:101` (import) + `:185` (`__all__`). [VERIFIED]

## Round 1 Reviewer Verdict (historical record)

**Verdict:** REJECTED (first pass) → addressed by Dev rework

| Severity | Issue | Location | Fix Required |
|----------|-------|----------|--------------|
| [LOW] [DOC] | Stale docstring claims alias still exists | `sidequest-server/sidequest/game/session.py:60-62` | Rewrite trailing sentence to reflect post-removal state |
| [LOW] [TEST] | No test confirms `sidequest.game.EncounterTag` is gone | `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` (augment `test_scene_momentum_encounter_tag_unchanged`) | Add `assert not hasattr(sidequest.game, "EncounterTag")` |

**Rationale for REJECT despite both LOW:** Both fixes are mechanical and total ≤5 lines. The stale docstring is *actively introduced* by this PR. The missing test is the *negative half* of the rename invariant — dropping it leaves a regression hole that one line closes. Per "just fix the thing, don't argue scope," the right call is to bring the PR home complete.

**Data flow traced:** N/A (deletion-only chore).
**Pattern observed:** Pure deletion. No abstractions added.
**Error handling:** N/A. Failure mode louder post-deletion.

**Handoff (first pass):** Back to Dev (`implement` phase rework).

## Dev Assessment (rework round 1)

**Implementation Complete:** Yes (both Reviewer fixes applied verbatim)
**Files Changed:**
- `sidequest-server/sidequest/game/session.py` — rewrote the trailing sentence of `NpcEncounterLogTag` docstring (lines 60-67). The class doc now points at canonical import paths (`sidequest.game.NpcEncounterLogTag` re-export or direct `sidequest.game.session` import) and notes the 45-46 removal. No code changes.
- `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py` — added `import sidequest.game` at function scope and one regression-guard assertion at the end of `test_scene_momentum_encounter_tag_unchanged`: `assert not hasattr(sidequest.game, "EncounterTag")`. Updated the test's docstring to mention the new guard. Net: +10 lines, -3 lines.

**Tests (rework verification):**
- Target test file: 3/3 pass.
- Full sweep: 5059 passed, 6 failed (5 pre-existing victoria + 1 pre-existing chargen-dispatch isolation flake — all unrelated to this story), 58 skipped.
- Lint: PASS.

**Verification of Reviewer's two fixes:**
- The new `assert not hasattr(sidequest.game, "EncounterTag")` assertion passes — confirms the package-level alias is truly gone (and would catch any future regression that re-introduced it).
- The rewritten docstring no longer claims the alias exists.

**Branch:** `feat/45-46-drop-encountertag-alias` on `sidequest-server` (rework commit 70554ec, pushed).

**Handoff:** Back to `review` phase (Reviewer).

## Subagent Results (round 2 — rework review)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | 0 (tests GREEN, 5060 pass, 5 pre-existing victoria failures unchanged from baseline, lint clean, working tree clean, 2 commits on branch as expected) | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 1 (round-1 gap confirmed CLOSED; assertion sound; no new findings) | dismissed 1 (informational only — no actionable concern) |
| 5 | reviewer-comment-analyzer | Yes | findings | 1 (rewritten docstring parenthetical "re-exported from this module" reads backwards — `session.py` is the SOURCE module, not the re-exporter) | deferred 1 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 3 (Rule #6 — one-sided regression guard; Rule #10 — function-scope import; Rule #17 — no positive wiring test for package-level re-export path) | deferred 3 |

**All received:** Yes (4 enabled returned, 5 disabled via settings)
**Total findings:** 0 confirmed-as-blocking, 1 dismissed (informational), 4 deferred to Delivery Findings for follow-up polish

### Round-2 finding details and dispositions

**[DOC] Backwards parenthetical at `sidequest/game/session.py:63`** (deferred)
- The rewrite reads: "(re-exported from this module)" — but `session.py` is the DEFINING module; `sidequest/game/__init__.py` is the RE-EXPORTER. The parenthetical, read literally, applies the re-export label to the wrong module.
- Severity: **[LOW]** — grammatically imprecise, factually defensible (a reader can parse it as "this defining module's class is re-exported"), not actively misleading the way the round-1 version was.
- Disposition: **DEFER** to Delivery Findings for a future polish pass. The round-1 fix achieved its primary intent (no longer claims the alias still exists). The new infelicity is second-order on a 1pt chore that's already had one rework cycle.

**[RULE] One-sided regression guard at `tests/game/test_npc_encounter_log_tag_rename.py:55`** (deferred)
- `assert not hasattr(sidequest.game, "EncounterTag")` proves the alias is absent but does not prove the canonical replacement (`sidequest.game.NpcEncounterLogTag`) is still accessible at the package-level path the new docstring advertises. The rule-checker's recommended bidirectional form adds `assert hasattr(sidequest.game, "NpcEncounterLogTag")`.
- Severity: **[LOW]** — the negative half (regression-against-alias-re-introduction) is what round 1 explicitly asked for, and the rework provides it. The positive half (regression-against-canonical-path-breakage) is a *stronger* test than round 1 demanded.
- Disposition: **DEFER** to Delivery Findings. Adding this is genuinely good engineering and the fix is one line; capturing for follow-up rather than triggering a third round-trip on a 1pt chore.

**[RULE] Function-scope `import sidequest.game` at `tests/game/test_npc_encounter_log_tag_rename.py:40`** (deferred)
- Function-body import where module-scope would be cleaner. Rule-checker confirmed no circular-import or attribute-mutation risk in this codebase. LOW per the rule's own guidance.
- Disposition: **DEFER** to Delivery Findings.

**[RULE] No positive wiring test for `sidequest.game.NpcEncounterLogTag` re-export** (deferred — same as one-sided-guard finding)
- The docstring at `session.py:62-64` (post-rework) advertises `sidequest.game.NpcEncounterLogTag` as a canonical import path. No test exercises it; all three surviving tests use the submodule path `sidequest.game.session.NpcEncounterLogTag`. The bidirectional guard recommended above closes this gap simultaneously.
- Disposition: **DEFER** (same fix as one-sided-guard).

**[TEST] Informational note — round-1 gap CLOSED** (dismissed)
- Test-analyzer confirmed the regression guard's `hasattr` does NOT walk into submodules (e.g., `sidequest.game.encounter_tag` carries an `EncounterTag` attribute, but `hasattr(sidequest.game, "EncounterTag")` returns False because Python's `__getattr__` and dict-lookup don't cross submodule boundaries). The assertion tests exactly what it claims to test. No action.

### Devil's Advocate (Reviewer — round 2)

What could the rework have broken?

1. **The new `import sidequest.game` triggers `__init__.py` evaluation.** Yes — and `__init__.py` already runs on first reference to anything under `sidequest.game.*`, which `test_scene_momentum_encounter_tag_unchanged` already triggered via `from sidequest.game.encounter_tag import ...`. No new init cost.
2. **Could the `hasattr` check be defeated by future `__getattr__` re-introduction?** Yes — that's literally what it's guarding against. The whole point.
3. **Could `__all__` membership confuse `hasattr`?** No. `hasattr` checks attribute resolution, not `__all__`. Verified by test-analyzer.
4. **Does the docstring point at a real path?** Yes — `sidequest.game.NpcEncounterLogTag` is wired at `__init__.py:101` (import) + `:185` (`__all__`). Confirmed by rule-checker round 1.
5. **Stash housekeeping.** Still pending; documented in Dev Assessment from round 1. Not a code defect.

The devil's advocate uncovers nothing new beyond the rule-checker's bidirectional-guard suggestion, which is already deferred.

### Rule Compliance (round 2)

Re-checked the 10 added lines against the Python lang-review checklist:
- **#3 Type annotations:** Test functions still annotated `-> None`. ✓
- **#6 Test quality:** New assertion is specific (negative-existence check on a named attribute). Bidirectional improvement deferred. ✓ with deferred note.
- **#10 Import hygiene:** Function-scope import noted as LOW; deferred. No circular-import risk.
- **#13 Fix-introduced regressions:** Rework introduces no new bare-excepts / mutable defaults / unannotated public funcs / unsafe deserialization / blocking-in-async / etc. ✓
- **CLAUDE.md "Verify Wiring":** Negative wiring assertion verifies the deletion; positive wiring assertion deferred but not blocking.

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** N/A (deletion-only chore, no new data flow).
**Pattern observed:** Pure deletion at `sidequest-server/sidequest/game/__init__.py:197-223` (now gone). Docstring rewrite at `sidequest-server/sidequest/game/session.py:60-67`. One-line regression guard at `sidequest-server/tests/game/test_npc_encounter_log_tag_rename.py:55`.
**Error handling:** N/A. Failure mode strictly LOUDER post-deletion: Python's native `AttributeError` on `sidequest.game.EncounterTag` instead of the deleted shim's `DeprecationWarning`-then-fallback. ✓

### Subagent findings incorporated

- [DOC] Backwards parenthetical "(re-exported from this module)" at `sidequest-server/sidequest/game/session.py:63` — second-order grammar imprecision in the round-1 docstring fix. Deferred to Delivery Findings, severity LOW.
- [TEST] Round-1 regression-gap CLOSED. test-analyzer verified `assert not hasattr(sidequest.game, "EncounterTag")` evaluates as intended (hasattr does not walk into the `encounter_tag` submodule; alias deletion leaves no path that satisfies the check). Dismissed (informational, no action).
- [RULE] One-sided regression guard at `tests/game/test_npc_encounter_log_tag_rename.py:55` — negative-existence check has no positive complement asserting `sidequest.game.NpcEncounterLogTag` remains accessible at the package-level re-export path the new docstring advertises. Deferred to Delivery Findings, severity LOW.
- [RULE] Function-scope `import sidequest.game` at `tests/game/test_npc_encounter_log_tag_rename.py:40` — module-scope would be cleaner; no circular-import or attribute-mutation risk. Deferred to Delivery Findings, severity LOW.
- [RULE] No positive wiring test exercises the `sidequest.game.NpcEncounterLogTag` re-export path documented at `session.py:62-64`. Closed by the same bidirectional-guard fix above (deferred). Severity LOW.

**Rationale for APPROVAL despite 4 deferred [LOW] findings:**
1. The story's primary intent (drop the Wave-1 deprecation alias) is **complete**: alias gone, no live consumers anywhere in the workspace, regression guard in place, tests + lint green.
2. All round-2 findings are LOW (the severity matrix only blocks on Critical/High).
3. Round-1 demanded two specific fixes; Dev applied both verbatim. The round-2 findings critique the *implementation of the fixes* rather than the fixes' completeness.
4. Per project guidance "just fix the thing, don't argue scope" cuts both ways: it also means don't iterate a 1pt chore to perfection through a third round-trip. The deferred findings are captured in Delivery Findings and total ≤5 lines for a future polish story.
5. The rule-checker's bidirectional-guard suggestion is genuinely good engineering, but the current one-sided guard satisfies exactly what round 1 asked for — escalating to demand more on round 2 would be moving the goalposts.

**Handoff:** To SM for finish-story (PR creation, merge, archive).