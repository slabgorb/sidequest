---
story_id: "102-8"
jira_key: "102-8"
epic: "102"
workflow: "trivial"
---
# Story 102-8: Doc-drift cleanup — retire stale 'not wired to dispatch (Plan 3)'/'deferred' markers across ruleset/wwn.py, swn.py, cwn.py (apply_killing_blow IS wired at dice.py:644/725; veterans_luck has a narrator tool) and reconcile docs/adr/DRIFT.md + the WN plan docs so 'deferred' reflects reality post-102. chore

## Story Details
- **ID:** 102-8
- **Jira Key:** 102-8
- **Workflow:** trivial
- **Stack Parent:** none
- **Type:** chore
- **Points:** 2
- **Branch:** feat/102-8-doc-drift-wn-deferred-markers
- **Branch Strategy:** gitflow (feat/102-8-doc-drift-wn-deferred-markers)

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-06-10T21:17:13Z

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-06-10T21:05:52.831896+00:00 | 2026-06-10T21:07:28Z | 1m 35s |
| implement | 2026-06-10T21:07:28Z | 2026-06-10T21:14:05Z | 6m 37s |
| review | 2026-06-10T21:14:05Z | 2026-06-10T21:17:13Z | 3m 8s |
| finish | 2026-06-10T21:17:13Z | - | - |

## Sm Assessment

**Story:** 102-8 — doc/comment-drift cleanup in sidequest-server. Pure chore, 2pt, trivial workflow, single repo.

**What needs to happen:** Retire stale markers that no longer reflect reality post-Epic-102:
- `ruleset/wwn.py`, `swn.py`, `cwn.py` carry "not wired to dispatch (Plan 3)" / "deferred" comments that are now false. `apply_killing_blow` IS wired (verify at `dice.py:644` and `:725`), and `veterans_luck` now has a narrator tool.
- Reconcile `docs/adr/DRIFT.md` and the WN plan docs so "deferred" language matches the shipped state.

**Approach for Dev (Julia):** This is documentation/comment surgery, not behavior change. Verify each claim against the live code before deleting a marker — confirm `apply_killing_blow` is actually invoked from `dice.py:644/725` and that the `veterans_luck` narrator tool exists, then strike only the markers contradicted by evidence. Do not change runtime logic. No new tests expected (comment/doc-only); if any test asserts on the stale comment text, update it.

**Watch-outs:** Don't over-reach — only retire markers that are demonstrably stale. Leave genuinely-deferred items intact. DRIFT.md edits should be surgical, matching ADR conventions.

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest-server/sidequest/game/ruleset/wwn.py` — corrected the stale `dice.py:644/725` line-number reference in the `apply_killing_blow` docstring to a drift-proof semantic description of the two dispatch call sites (strike HIT path + Shock chip path). The actual live call sites are `dispatch/dice.py:1174` (strike) and `:1255` (Shock chip) — the old text was doubly stale (wrong module *and* wrong lines).

**Scope reconciliation (evidence-based):**
- `wwn.py` "not wired to dispatch (Plan 3)" markers → already retired by #797 (`887612f2`, merged to develop). This story finished the last surviving stale reference.
- `swn.py` / `cwn.py` markers → **never existed** (`git log -S "not wired"` / `-S "deferred"` return zero commits). Verified `apply_killing_blow` IS wired (`dispatch/dice.py:1174/1255` → `wwn.py:590`) and `veterans_luck` HAS a narrator tool (`agents/tools/veterans_luck.py`).
- `docs/adr/DRIFT.md` → auto-generated ("do not edit by hand"); no stale WN-wiring row present. Out of bounds for a hand edit.
- WN plan docs → all archived in `completed/`; historically accurate retrospectives. Not rewritten (would be revisionism).

**Tests:** 46/46 passing (GREEN) — targeted wwn warrior / killing-blow-wiring / class-power-tools / magic-config suites. Lint + format clean, import smoke OK. Docstring-only; no OTEL needed (cosmetic per server CLAUDE.md).
**Branch:** feat/102-8-doc-drift-wn-deferred-markers (pushed, commit `chore(102-8): correct stale dice.py line-number reference...`)

**Handoff:** To review (The Thought Police).

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Improvement** (non-blocking): The story title enumerates `swn.py` and `cwn.py` as carrying stale "not wired/deferred" markers, but `git log -S "not wired"` and `git log -S "deferred"` show those two files **never** contained such markers. The over-broad enumeration is now reconciled — only `wwn.py` ever had them. Affects no file (scope clarification only). *Found by Dev during implementation.*
- **Improvement** (non-blocking): `docs/adr/DRIFT.md` is auto-generated (`scripts/regenerate_adr_indexes.py`, header says "Do not edit by hand"); ADRs leave the list when their `implementation-status` frontmatter flips to `live`. It carries no stale WN killing_blow/veterans_luck "deferred" row to reconcile for this story. Flipping WN ADR statuses (114/116/117/139) to `live` is substantive epic-102 work (driven by the other 102 stories + ADR frontmatter), not this 2pt doc chore. Affects `docs/adr/DRIFT.md` (no edit warranted here). *Found by Dev during implementation.*
- **Improvement** (non-blocking): The WN plan docs are all archived under `docs/superpowers/plans/completed/` and `specs/completed/` — historical retrospectives that accurately describe each plan's *plan-time* scope (Plan 2 deferred dispatch wiring to Plan 3; Plan 3 — `2026-05-29-wwn-content-binding.md` — is itself completed). Rewriting them to say "now wired" would be revisionism, not reconciliation; left intact intentionally. Affects `docs/superpowers/.../completed/*` (no edit warranted). *Found by Dev during implementation.*

### Reviewer (code review)
- No upstream findings during code review. The scope-reconciliation findings Dev logged (swn.py/cwn.py never had markers; DRIFT.md auto-generated; plan docs archived) are confirmed accurate and require no follow-on work.


## Impact Summary

**Finding Count:** 3 non-blocking improvements (scope clarification, no runtime impact)
**Blocking Issues:** 0
**Ready for Finish:** Yes

### Summary

Pure documentation correction to `sidequest/game/ruleset/wwn.py` (docstring only). Replaced stale line numbers (`dice.py:644/725`) with semantic path descriptions (`strike HIT path and Shock chip path`). No executable code changed. Tests: 46/46 GREEN. Lint: PASS. Scope analysis confirmed only the single live marker in `wwn.py` required correction; the story title's enumeration of other files and DRIFT.md were evidence-driven out of scope (those files never had the markers, DRIFT.md is auto-generated, plan docs are archived historical records).

### Non-Blocking Observations

1. **Scope clarification (swn.py/cwn.py):** Story title listed files that never contained the markers. Verified via `git log -S "not wired"`/`-S "deferred"` (zero commits). No action needed; this finding documents the clarification.

2. **DRIFT.md is auto-generated:** The index cannot be hand-edited per its own header ("Do not edit by hand"). ADR status flips are epic-102 work, not this 2pt chore. No action needed.

3. **Plan docs are archived retrospectives:** Historical records at `docs/superpowers/*/completed/` accurately reflect plan-time scope. Rewriting to say "now wired" would falsify the record. Left intact. No action needed.

### Mechanical Gates

- **Lint:** ruff check PASS
- **Format:** ruff format PASS
- **Tests:** 46/46 GREEN (wwn warrior, killing-blow-wiring, class-power-tools, magic-config suites)
- **Import:** Smoke test PASS
- **Docstring accuracy:** Verified — matches dispatch code's own path labels and caller set

### Design Deviations (Accepted)

Narrowed touched surface to the one live stale marker (minor severity, zero forward impact). Dev evidence-driven narrowing from the story title's enumeration; Reviewer independently confirmed the correctness of not editing machine-generated DRIFT.md or archived plan docs.


## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- **Narrowed the touched surface to the one live stale marker instead of editing all enumerated files/docs**
  - Spec source: context-story-102-8.md (Title), epic-102 context (doc-drift pass)
  - Spec text: "retire stale 'not wired to dispatch (Plan 3)'/'deferred' markers across ruleset/wwn.py, swn.py, cwn.py ... and reconcile docs/adr/DRIFT.md + the WN plan docs"
  - Implementation: Edited only `wwn.py` (corrected the stale `dice.py:644/725` line-number reference in the `apply_killing_blow` docstring). Left swn.py/cwn.py (never had markers — verified via `git log -S`), DRIFT.md (auto-generated, no stale WN row), and the completed/ WN plan docs (historical retrospectives) untouched.
  - Rationale: Evidence-driven scope. #797 already retired wwn.py's "Plan 3" markers; the remaining live drift was the single stale line-number citation. The other enumerated targets either never carried the markers, are machine-generated (must not be hand-edited), or are archived records whose plan-time "deferred" language is historically correct.
  - Severity: minor
  - Forward impact: none — pure doc/comment correction; no API, behavior, or sibling-story assumption affected.

### Reviewer (audit)
- **Narrowed surface to the one live stale marker** → ✓ ACCEPTED by Reviewer: Evidence-driven and correct. Independently confirmed via `git log -S "not wired"`/`-S "deferred"` on swn.py/cwn.py (zero history), the DRIFT.md auto-generated header ("Do not edit by hand"), and that the WN plan docs live under `completed/`. Editing machine-generated DRIFT.md by hand or rewriting archived retrospectives would have been the *wrong* action; restricting to the wwn.py docstring is the right call and honors the SM "don't over-reach" watch-out.
- No undocumented deviations found.

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none (lint PASS, format PASS, import PASS, 46/46 GREEN, 0 smells) | N/A |
| 2 | reviewer-edge-hunter | Yes | clean | none (independently confirmed docstring matches call sites dice.py:1174/1255; no executable paths changed) | N/A |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Skipped | disabled | N/A | Disabled via settings |
| 5 | reviewer-comment-analyzer | Skipped | disabled | N/A | Disabled via settings (comment accuracy self-reviewed by Reviewer — see [DOC] below) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Yes | clean | none (docstring-only; no auth/input/secret surface) | N/A |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Skipped | disabled | N/A | Disabled via settings |

**All received:** Yes (3 enabled returned, all clean; 6 disabled via settings)
**Total findings:** 0 confirmed, 0 dismissed, 0 deferred

### Rule Compliance

Applicable rules from server CLAUDE.md / SOUL.md and the governed elements in the diff (the `apply_killing_blow` docstring only):
- **No Silent Fallbacks** — N/A to a docstring; the method's `cfg` guard (`raise ValueError` on non-WwnConfig) is unchanged and remains fail-loud. Compliant.
- **No Stubbing** — No stub/placeholder introduced; the docstring describes live, wired behavior. Compliant.
- **No source-text wiring tests** — No test added or changed; the correction *removes* brittle source-line citations rather than encoding them in a test. Compliant.
- **OTEL Observability Principle** — "Not needed for cosmetic changes (label rewording, log message tweaks)." A docstring correction is cosmetic; no OTEL required. Compliant.
- **Comment accuracy (institutional: stale comments are drift debt)** — The new text matches the dispatch code's own labels ("HIT path" at dice.py:1168, "Shock path" at dice.py:1248) and the only two production callers (dice.py:1174, :1255). Compliant and improved.

### Observations

- [VERIFIED] Docstring now accurate — evidence: new text "called by dispatch/dice.py on the killing_blow rider (the strike HIT path and the Shock chip path)" matches the in-code comments at `dispatch/dice.py:1168` ("HIT path") and `:1248` ("Shock path"); complies with the no-stale-comments expectation.
- [VERIFIED] Caller set is exhaustive — evidence: `grep apply_killing_blow(` shows the ONLY production callers are `dispatch/dice.py:1174` and `:1255`; "called by dispatch/dice.py" is complete, not partial.
- [VERIFIED] Zero behavior change — evidence: diff touches only lines 603-604 inside a `"""docstring"""`; the executable body (guard at :607-608, math at :609-610, span at :611) is untouched.
- [DOC] Comment-analyzer was disabled; Reviewer self-reviewed the comment and confirms the removal of brittle absolute line numbers (`dice.py:644/725`) in favor of semantic path names is the correct anti-drift fix — it cannot re-rot on renumbering.
- [VERIFIED] Mechanical gates green — evidence: preflight reports ruff check PASS, ruff format PASS, import smoke PASS, 46/46 targeted wwn tests GREEN; the three BaseModel field-shadow UserWarnings pre-exist on develop and are unrelated.
- [SILENT]/[TEST]/[TYPE]/[SIMPLE]/[RULE] — specialists disabled via settings; domains assessed by Reviewer: no swallowed errors, no test changes, no type changes, no complexity introduced, no rule violations (see Rule Compliance) — a docstring edit has no surface for any of these.

### Devil's Advocate

Let me try to break this. The change swaps precise line numbers for prose, so the obvious attack is: *is the new prose actually true, or did Dev replace one lie with a vaguer, harder-to-falsify one?* If "the strike HIT path and the Shock chip path" did not correspond to real, distinct call sites, this would be worse than the stale numbers — it would launder inaccuracy behind unfalsifiable language. I checked: there are exactly two production call sites, and the dispatch code itself labels them "HIT path" and "Shock path." So the prose is not vague hand-waving; it is the codebase's own vocabulary. The attack fails. Second angle: could "called by dispatch/dice.py" be *incomplete* — are there other callers (tests, another subsystem, a magic path) that a reader would now miss? `grep` says no: only dice.py:1174/1255 in production. The Shock path also feeds Killing-Blow-adds-to-Shock, but that IS the chip path already named. Third angle: did Dev under-deliver on the story by touching only one file when the title named three files plus DRIFT.md plus plan docs? This is the strongest objection. But "do everything the title lists" is wrong when the list is factually unfounded: swn.py/cwn.py never carried these markers (git history proves it), DRIFT.md is machine-generated with a "do not edit by hand" banner, and the plan docs are archived retrospectives whose plan-time "deferred" language is historically correct — rewriting them would be falsifying the record. Editing those would have been the actual defect. Fourth angle: a confused reader might think "rider" implies something optional/bolt-on that could be skipped — but the gating (wwn pack AND Warrior archetype) is exactly a conditional rider, so the word is apt. Fifth: stressed-filesystem / config-with-unexpected-fields concerns are inapplicable to a docstring. I cannot find a defect. The change is correct, complete for what is genuinely in scope, and improves long-term accuracy.

## Reviewer Assessment

**Verdict:** APPROVED
**Data flow traced:** Player strike → `dispatch/dice.py:1174` (HIT) / `:1255` (Shock chip) → `WwnRulesetModule.apply_killing_blow` (pure math + `wwn.killing_blow` span) → returned total. The docstring now describes this flow accurately; no flow was altered.
**Pattern observed:** Anti-drift documentation fix — brittle absolute line numbers replaced with the dispatch code's own semantic path labels at `sidequest/game/ruleset/wwn.py:603-604`. Good pattern; survives future renumbering.
**Error handling:** Unchanged — the fail-loud `cfg` guard at `wwn.py:607-608` (`raise ValueError` on non-WwnConfig) is intact.
**Subagent dispatch:** [EDGE] clean · [SEC] clean · [DOC] self-reviewed, accurate · [SILENT]/[TEST]/[TYPE]/[SIMPLE]/[RULE] disabled-via-settings, Reviewer-assessed clean (docstring-only diff has no surface for any).
**Scope judgment:** Dev's evidence-driven narrowing to the single live stale marker is correct and ACCEPTED — the other enumerated targets either never had markers, are auto-generated, or are archived records that must not be rewritten.
**Handoff:** To SM (Winston Smith) for finish-story.