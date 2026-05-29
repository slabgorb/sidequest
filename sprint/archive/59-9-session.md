---
story_id: "59-9"
jira_key: ""
epic: "59"
workflow: "trivial"
---
# Story 59-9: Fix cross_player redaction gap in redact_dispatch_package

## Story Details
- **ID:** 59-9
- **Jira Key:** (none — SideQuest is personal)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-29T12:00:09Z
**Repos:** sidequest-server
**Branch:** feat/59-9-cross-player-redaction-gap

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T11:43:06Z | 2026-05-29T11:44:53Z | 1m 47s |
| implement | 2026-05-29T11:44:53Z | 2026-05-29T11:54:42Z | 9m 49s |
| review | 2026-05-29T11:54:42Z | 2026-05-29T12:00:09Z | 5m 27s |
| finish | 2026-05-29T12:00:09Z | - | - |

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Gap** (non-blocking): `audit_canonical_prose` (the secondary OTEL leak-audit safety net) iterates only `package.per_player` when collecting `redacted_entities`, so it is blind to `cross_player` redacted secrets — a false-negative `leaks_detected=0` is possible for a cross_player leak. Affects `sidequest/telemetry/leak_audit.py` (~line 77; extend the redacted-entity collection loop to also iterate `package.cross_player[*].dispatch`, mirroring this story's `redact_dispatch_package` fix). Pre-existing gap, newly *material* now that cross_player is actually redacted. Primary firewall is closed, so steady-state is safe; this hardens the lie-detector. Recommend a follow-up story (sibling to 59-9). *Found by Reviewer during code review (security subagent, medium confidence).*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/agents/prompt_redaction.py` — added `cross_player` filtering branch to `redact_dispatch_package`: filters each `CrossAction.dispatch` by `redact_from_narrator_canonical`, appends removals to the shared `removed` list, rebuilds each `CrossAction` via `model_copy`, and includes `cross_player` in the final package `model_copy`. Imported `CrossAction`.
- `tests/agents/test_prompt_redaction.py` — added 3 cross_player tests (AC1 strip-entirely, AC2 mixed per_player+cross_player shared-accumulator, AC3 no-op safety); imported `CrossAction` and `cast`.

**Tests:** 6/6 in `test_prompt_redaction.py` GREEN; full `tests/agents/` sweep 1143 passed / 414 skipped (pre-existing), no regressions. RED confirmed before fix (2 new tests failed: empty `removed` for cross_player). Ruff clean, pyright 0 errors on both changed files.

**Branch:** feat/59-9-cross-player-redaction-gap (pushed, commit 4fc0db34)

**Handoff:** To review phase (Reviewer / Westley).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. The fix follows `context-story-59-9.md` exactly: cross_player branch mirrors the per_player loop, filters `dispatch` only (CrossAction has no `narrator_instructions`), routes removals into the same `removed` accumulator (no new OTEL span), and rebuilds `cross_player` in the final `model_copy`. per_player logic untouched; no fidelity/`secrets_for`/`visible_to` handling added. The only test-side adjustment was `cast(SubsystemDispatch, ...)` on `removed[*]` accesses to satisfy pyright on the union-typed list — a type-narrowing aid, not a behavior or spec change.

### Reviewer (audit)
- **Dev: "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed against the diff. The cross_player branch is a faithful mirror of the per_player loop, dispatch-only (correct — `CrossAction` has exactly 3 fields and only `dispatch` carries `VisibilityTag`), removals share the `removed` accumulator (no new span — matches the context's reuse mandate), and `model_copy` preserves `participants`/`witnesses` unchanged. The `cast(SubsystemDispatch, ...)` test adjustment is a pyright type-narrowing aid with no behavioral effect — sound, not a spec deviation.
- No undocumented deviations found. The diff stayed strictly within the story's stated scope (only `redact_dispatch_package`); the adjacent `leak_audit.py` cross_player gap was correctly NOT touched here and is logged as an upstream Delivery Finding for a follow-up, consistent with the context's scope boundaries.

## Sm Assessment

**Routing:** trivial workflow (1pt bug) → setup → implement → review → finish. Handing off to Dev for the implement phase.

**Story:** Extend `redact_dispatch_package` (`sidequest/agents/prompt_redaction.py:26-76`) to filter `cross_player[*].dispatch` by `redact_from_narrator_canonical`, mirroring the existing `per_player` loop. Perception-firewall gap (ADR-104/105): the redactor iterates only `per_player`; `cross_player` is copied through unfiltered, so a redacted cross_player dispatch reaches the narrator.

**Context:** Full story context already authored at `sprint/context/context-story-59-9.md` — staleness verified live as of 2026-05-28, gap is real. Read it before touching code: it pins the file/line targets, the `model_copy` immutable-rebuild idiom, the "reuse the existing `prompt.redaction.structural` span, do NOT add a new one" constraint, the `CrossAction`-has-no-`narrator_instructions` constraint, and three ACs.

**Scope discipline:** Filter `cross_player[*].dispatch` only. Do NOT refactor `per_player`, do NOT add a directive filter for cross_player, do NOT add an OTEL span, do NOT touch fidelity/`secrets_for`/`visible_to` (that's ADR-105 broadcast-layer, separate). Removals must land in the SAME `removed` accumulator so the existing span counts them.

**Test bar:** One+ test in `tests/agents/test_prompt_redaction.py` that FAILS against current main and pins the cross_player strip (retarget the existing `test_redacted_dispatch_stripped_entirely` from per_player to cross_player; cover the no-op-safety case too).

**Repo:** sidequest-server, branch `feat/59-9-cross-player-redaction-gap` (off develop). No Jira (SideQuest is personal).
---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 6/6 targeted GREEN, 1143 module-wide GREEN, ruff PASS, pyright 0 errors, 0 smells |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — boundary paths reviewed manually (empty cross_player, all-redacted, mixed) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — no swallowed errors in diff (no try/except added) |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — test quality reviewed manually (3 tests, RED-proven, non-vacuous) |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — the one added comment is accurate (verified vs subsystems/__init__.py:231) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — types reviewed manually (cast narrows union; no new stringly-typed API) |
| 7 | reviewer-security | Yes | findings | 2 (medium) | confirmed 0 in-scope; 1 deferred to follow-up (leak_audit cross_player blind spot); 1 is the same finding's call-site note (deferred) |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — branch mirrors per_player; no over-engineering |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rule compliance enumerated manually below |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` and pre-filled)
**Total findings:** 0 confirmed blocking, 2 deferred (with rationale — out-of-scope/pre-existing leak_audit gap), 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** A redacted `cross_player` SubsystemDispatch (`visibility.redact_from_narrator_canonical=True`) → `redact_dispatch_package` (now strips it into `removed`, `prompt_redaction.py:64-77`) → `visible_dispatch_package` (orchestrator.py:1648) → `run_dispatch_bank(package=visible_dispatch_package)` (orchestrator.py:2599) → `for ca in package.cross_player: all_dispatches.extend(ca.dispatch)` (subsystems/__init__.py:233-234) → narrator high-attention block. **Safe because:** the redacted entry is removed at the redactor seam, so it never enters `all_dispatches` and never reaches the narrator. Wiring verified end-to-end against the real consumer — this is a genuine fix, not theater.

**Observations (6):**
- [VERIFIED] cross_player redaction is wired to the live narrator path — evidence: `orchestrator.py:1648` redacts, `:2599` passes the redacted package to `run_dispatch_bank`, `subsystems/__init__.py:233-234` consumes `package.cross_player[*].dispatch`. Complies with ADR-104/105 perception-firewall rule (no redacted dispatch reaches the narrator).
- [VERIFIED] removals share the single `removed` accumulator — evidence: `prompt_redaction.py:73` appends to the same list the `prompt.redaction.structural` span reports at `:89-92`; no second span added (complies with the context's "reuse, don't add" OTEL mandate and CLAUDE.md's cosmetic-span exclusion).
- [VERIFIED] `model_copy` preserves `participants`/`witnesses` — evidence: `prompt_redaction.py:77` updates only `dispatch`; pydantic v2 shallow-copies the rest, and `_witnesses_include_participants` (dispatch.py:185) runs only on `mode="after"` construction, not on copy. No identity-list mutation.
- [VERIFIED] empty-`cross_player` no-op safety — evidence: when `pkg.cross_player == []`, the loop is skipped, `new_cross == []`, and `model_copy(update={"cross_player": []})` is value-equal to the original; pinned by `test_no_redactions_is_noop` and `test_cross_player_no_redactions_is_noop`.
- [VERIFIED] no other redactable field forgotten — evidence: `CrossAction` (dispatch.py:180-184) has exactly `participants`, `witnesses`, `dispatch`; only `dispatch` carries `VisibilityTag`. Dispatch-only scope is correct; the added comment matches `subsystems/__init__.py:231`.
- [SEC] (deferred, medium) `audit_canonical_prose` leak-audit is blind to cross_player — `leak_audit.py:~77` iterates only `per_player`, so the OTEL safety net can false-negative on a cross_player leak. Pre-existing, out-of-scope for 59-9, primary firewall already closes the actual hole. Logged as a Delivery Finding for a follow-up story.

**Subagent dispatch tags:** [SEC] confirmed (1 deferred finding above). Disabled this run (project `workflow.reviewer_subagents` config), domains covered manually in observations/rule-compliance: [EDGE] (boundary paths — empty/all-redacted/mixed all pinned by tests), [SILENT] (no try/except or swallowed errors added), [TEST] (3 RED-proven non-vacuous tests), [DOC] (single added comment verified accurate), [TYPE] (`cast` narrows the union correctly; no new stringly-typed API), [SIMPLE] (branch is a minimal mirror of per_player — no over-engineering), [RULE] (enumerated below).

### Rule Compliance
- **No Silent Fallbacks (CLAUDE.md):** COMPLIANT — `model_copy(update=...)` raises on unknown keys; no alternative path/default introduced. The fix fails loud by construction.
- **Perception firewall ADR-104/105 (SOUL Illusionism):** COMPLIANT — every redaction-bearing surface on `cross_player` (`dispatch[*].visibility.redact_from_narrator_canonical`) is now stripped before narrator assembly. 2 instances checked (per_player pre-existing + cross_player new); 0 violations.
- **OTEL reuse, no cosmetic span (CLAUDE.md / context):** COMPLIANT — cross_player removals counted in the existing `prompt.redaction.structural` span; no new span.
- **Every test suite needs a wiring test (CLAUDE.md):** SATISFIED at the consumer — the redactor's wiring into the narrator path is exercised by the orchestrator-level test referenced in the test docstring; this story's unit tests pin the helper behavior. The redactor is a pure transform; its live wiring (orchestrator:1648→2599) is unchanged by this diff and independently covered.
- **Scope discipline (context Scope Boundaries):** COMPLIANT — per_player untouched, no directive filter invented for cross_player, no fidelity/secrets_for/visible_to handling, leak_audit correctly left for a follow-up.

### Devil's Advocate
Argue the code is broken. First attack: does the redactor run on the package the narrator actually sees? If `run_dispatch_bank` consumed the *canonical* package for narrator directives, this fix would be cosmetic. I traced it: the bank in `intent_router_pass.py:165` fires on the canonical package (correct — engines must engage even redacted dispatches), but the *narrator-visible* directive collection at `orchestrator.py:2599` uses `visible_dispatch_package`, the redacted one. So the fix lands where it matters. Second attack: a confused author adds a redactable field to `CrossAction` later (e.g. `narrator_instructions`) — the fix silently won't cover it, re-opening a hole. True, but that's a future-schema risk identical to the per_player branch's, and the asymmetry comment documents the current shape; not a defect in this diff. Third attack: `model_copy` shallow-copies `dispatch` list elements by reference — could a later mutation of a kept `SubsystemDispatch` leak across the copy? The kept entries are the same objects, but `redact_dispatch_package` is a terminal transform feeding prompt assembly; nothing downstream mutates them, and pydantic models are effectively immutable in use here. Fourth attack: the real residual risk — the leak-audit safety net (`leak_audit.py`) does NOT see cross_player, so if a *future* regression re-opens the structural strip, the lie-detector won't catch a cross_player leak (false `leaks_detected=0`). That is a real, material weakening of defense-in-depth — but pre-existing and out-of-scope, and I've logged it as a blocking-candidate Delivery Finding for an immediate follow-up. None of these rise to a defect in the 59-9 diff itself.

**Error handling:** No new error paths introduced; the transform is total (handles empty, all-redacted, mixed, none). Null/empty inputs covered by tests.

**Handoff:** To SM for finish-story.