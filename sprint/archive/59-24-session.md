---
story_id: "59-24"
jira_key: ""
epic: "59"
workflow: "trivial"
---
# Story 59-24: Extend leak_audit cross_player coverage — audit_canonical_prose blind to cross_player redactions

## Story Details
- **ID:** 59-24
- **Jira Key:** (none)
- **Workflow:** trivial
- **Stack Parent:** none

## Workflow Tracking
**Workflow:** trivial
**Phase:** finish
**Phase Started:** 2026-05-29T12:34:36Z
**Repos:** sidequest-server
**Branch:** feat/59-24-leak-audit-cross-player

### Phase History
| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-29T12:08:29Z | 2026-05-29T12:10:55Z | 2m 26s |
| implement | 2026-05-29T12:10:55Z | 2026-05-29T12:29:49Z | 18m 54s |
| review | 2026-05-29T12:29:49Z | 2026-05-29T12:34:36Z | 4m 47s |
| finish | 2026-05-29T12:34:36Z | - | - |

> **Note:** This session file was reconstructed by Dev after the `testing-runner`
> subagent clobbered it with a test-run cache report (known issue
> `feedback_testing_runner_clobbers_session`). Content below is faithfully restored.

## Delivery Findings

Agents record upstream observations discovered during their phase.
Each finding is one list item. Use "No upstream findings" if none.

**Types:** Gap, Conflict, Question, Improvement
**Urgency:** blocking, non-blocking

<!-- Agents: append findings below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No upstream findings during implementation.

### Reviewer (code review)
- **Gap** (non-blocking): `audit_canonical_prose` extracts the redacted entity only from `params["target"]`, but some subsystems key their secret entity differently — `npc_agency` uses `params["npc_name"]`, `magic_working` uses `params["actor"]`. Such a redacted dispatch increments `redact_tag_count` but its entity name is never added to `redacted_entities`, so a leak of that name into prose yields a false `leaks_detected=0`. Affects `sidequest/telemetry/leak_audit.py` (the `target`-only extraction in BOTH the per_player loop ~line 82 and the new cross_player loop — fix together with a multi-key lookup, e.g. priority over `("target","npc_name","actor")`). PRE-EXISTING gap in per_player, faithfully mirrored by 59-24 per its scope; NOT introduced here. Medium confidence, gated on the Group G perception rewriter (ADR-104/105 partial) actually emitting redacted npc_agency/magic_working dispatches. Recommend a follow-up story spanning both branches. *Found by Reviewer during code review (security subagent, medium confidence).*

## Dev Assessment

**Implementation Complete:** Yes
**Files Changed:**
- `sidequest/telemetry/leak_audit.py` — added a `cross_player` collection loop in `audit_canonical_prose`, mirroring the existing `per_player` loop: for each `CrossAction.dispatch` `SubsystemDispatch` with `visibility.redact_from_narrator_canonical=True`, append `params["target"]` to the SAME `redacted_entities` list. Imported `CrossAction`. No new span (reuses `narrator.canonical_leak_audit`); call sites unchanged.
- `tests/telemetry/test_leak_audit.py` — added 3 cross_player tests (AC1 leak now detected, AC2 mixed per_player+cross_player share `redact_tag_count==2`, AC3 no false positive when prose clean); imported `CrossAction`; added an optional `key=` param to the `_redacted` helper for distinct idempotency keys in the mixed-package case.

**Tests:** 6/6 in `test_leak_audit.py` GREEN; telemetry-dir sweep 321 passed / 6 skipped (pre-existing), no regressions. RED confirmed before fix (3 new tests failed: cross_player target uncollected → leaks_detected=0 / redact_tag_count short by one). Ruff clean, pyright 0 errors.

**Branch:** feat/59-24-leak-audit-cross-player (pushed)

**Handoff:** To review phase (Reviewer / Westley).

## Design Deviations

Agents log spec deviations as they happen — not after the fact.
Each entry: what was changed, what the spec said, and why.

<!-- Agents: append deviations below this line. Do not edit other agents' entries. -->

### Dev (implementation)
- No deviations from spec. The fix follows `context-story-59-24.md` exactly: a `cross_player` loop mirroring the `per_player` collection (same `isinstance` guards, same `params["target"]` extraction), into the same `redacted_entities` accumulator; no new OTEL span; no per_player change; no orchestrator call-site change; `redact_dispatch_package` untouched. The only test-helper change was adding an optional `key=` parameter to `_redacted` so the mixed per_player+cross_player package satisfies the unique-idempotency-key validator — a fixture aid, not a behavior or spec change.

### Reviewer (audit)
- **Dev: "No deviations from spec"** → ✓ ACCEPTED by Reviewer: confirmed against the diff. The cross_player branch is a structurally identical mirror of the per_player loop (same `isinstance(d, SubsystemDispatch)` guard, same `redact_from_narrator_canonical` check, same `params["target"]` extraction), appending into the same `redacted_entities` accumulator; no new span; per_player, call sites, and `redact_dispatch_package` untouched. The `key=` test-helper param is a correct fixture aid (the mixed package would otherwise collide idempotency keys and mask accumulator bugs) — not a spec deviation.
- No undocumented deviations found. The diff stayed strictly within scope. The `target`-only extraction gap the security pass flagged is an INHERITED pre-existing per_player behavior the story was explicitly told to mirror — not a deviation from this story's spec — and is logged as an upstream Delivery Finding for a follow-up.

## Sm Assessment

**Routing:** trivial workflow (1pt bug) → setup → implement → review → finish. Handing off to Dev (Inigo) for implement.

**Story:** Direct sibling of 59-9 (merged PR #515). 59-9 closed the *primary* firewall hole in `redact_dispatch_package`; 59-24 closes the matching blind spot in the *secondary* lie-detector. `audit_canonical_prose` (`sidequest/telemetry/leak_audit.py:76-84`) builds `redacted_entities` by iterating ONLY `package.per_player` — `cross_player` is never scanned, so a cross_player redacted-target leak into prose yields a false `leaks_detected=0`. Add a `cross_player` collection loop mirroring the per_player one, into the SAME `redacted_entities` accumulator.

**Context:** Authored at `sprint/context/context-story-59-24.md`, grounded in the live code read during discovery. Pins exact lines (76-84), the per_player pattern to mirror, the "reuse `narrator.canonical_leak_audit` span, no new span" mandate, and 3 ACs (leak now detected / counted in redact_tag_count / no false positive).

**Scope discipline:** Only `audit_canonical_prose`'s collection loop. Do NOT change per_player, do NOT touch the orchestrator call sites (they pass the canonical pre-redaction package ON PURPOSE — the audit must know what was supposed to be hidden), do NOT add a span, do NOT touch redact_dispatch_package (that was 59-9). NOT a live leak — defense-in-depth on the OTEL safety net.

**Test bar:** One+ test in `tests/telemetry/test_leak_audit.py` that FAILS against current main (cross_player redacted target currently uncollected → leaks_detected=0).

**Repo:** sidequest-server, branch `feat/59-24-leak-audit-cross-player` (off develop). No Jira.

**Note:** A blocking PR #516 (story 67-7) is open but is being worked in another session — user authorized proceeding past the merge gate; do not touch #516.
---

## Subagent Results

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A — 6/6 targeted GREEN, 321 telemetry-dir GREEN, ruff PASS, pyright 0 errors, 0 smells |
| 2 | reviewer-edge-hunter | No | Skipped | disabled | Disabled via settings — boundary paths reviewed manually (empty/all-redacted/mixed/non-str target all guarded + pinned by tests) |
| 3 | reviewer-silent-failure-hunter | No | Skipped | disabled | Disabled via settings — silent-drop on non-str target is pre-existing per_player behavior, mirrored intentionally; flagged via the [SEC] multi-key finding |
| 4 | reviewer-test-analyzer | No | Skipped | disabled | Disabled via settings — 3 RED-proven non-vacuous tests; key= param prevents idempotency-collision masking |
| 5 | reviewer-comment-analyzer | No | Skipped | disabled | Disabled via settings — the added comment is accurate (CrossAction has no narrator_instructions; verified vs dispatch.py:180-210) |
| 6 | reviewer-type-design | No | Skipped | disabled | Disabled via settings — types reviewed manually (isinstance guards; no new stringly-typed API) |
| 7 | reviewer-security | Yes | findings | 1 (medium) | deferred to follow-up — target-only extraction misses npc_name/actor keys; PRE-EXISTING, shared by both branches, out of 59-24 scope |
| 8 | reviewer-simplifier | No | Skipped | disabled | Disabled via settings — branch is a minimal faithful mirror of per_player; no over-engineering |
| 9 | reviewer-rule-checker | No | Skipped | disabled | Disabled via settings — rule compliance enumerated manually below |

**All received:** Yes (2 enabled subagents returned; 7 disabled via `workflow.reviewer_subagents` and pre-filled)
**Total findings:** 0 confirmed blocking, 1 deferred (with rationale — pre-existing out-of-scope multi-key extraction gap), 0 dismissed

## Reviewer Assessment

**Verdict:** APPROVED

**Data flow traced:** A redacted `cross_player` SubsystemDispatch (`visibility.redact_from_narrator_canonical=True`, `params["target"]="<entity>"`) in the CANONICAL package → `audit_canonical_prose(package=context.dispatch_package)` (orchestrator.py:3073/3410 pass the pre-redaction original on purpose) → new `for ca in package.cross_player` loop (`leak_audit.py:91-98`) collects the target into `redacted_entities` → prose scan (`:99-110`) finds the entity's tokens → `leaks_detected>=1` and the `narrator.canonical_leak_audit` span reports it. **Safe because:** the audit now sees cross_player secrets it was previously blind to; a leaked shared-target name is detected instead of silently passing. Verified the audit consumes the canonical (not redacted) package — correct, since it must know what was *supposed* to be hidden.

**Observations (6):**
- [VERIFIED] cross_player branch is a faithful mirror of per_player — evidence: `leak_audit.py:91-98` repeats the `isinstance(d, SubsystemDispatch)` guard, the `redact_from_narrator_canonical` check, and the `params["target"]` str-guarded extraction from `:77-84`, appending to the same `redacted_entities` list. Complies with the ADR-104/105 lie-detector rule (cross_player now scanned).
- [VERIFIED] no double-count — evidence: `DispatchPackage._unique_idempotency_keys` (dispatch.py:231-248) enforces key uniqueness across per_player AND cross_player, so a `SubsystemDispatch` cannot appear in both; the two loops never see the same entry.
- [VERIFIED] canonical-package consumption preserved — evidence: call sites (orchestrator.py:3073, 3410) pass `context.dispatch_package` (pre-redaction); the redacted `visible_dispatch_package` is built separately at :1648 for the narrator only. The audit correctly sees what should have been hidden.
- [VERIFIED] crash-safe on malformed params — evidence: `isinstance(d.params, dict)` gates `.get()` and `isinstance(target, str)` gates the append; None/int/list/missing silently drop without raising — identical to per_player.
- [VERIFIED] no other redactable CrossAction field forgotten — evidence: `CrossAction` (dispatch.py:180-210) has only `participants`, `witnesses`, `dispatch`; the comment's "no narrator_instructions" claim is accurate. Dispatch-only scope correct.
- [SEC] (deferred, medium) `params["target"]`-only extraction misses `npc_agency` (`npc_name`) and `magic_working` (`actor`) secret keys → false `leaks_detected=0` for those subsystems. PRE-EXISTING in per_player, faithfully mirrored here per the story's explicit "mirror per_player" mandate; affects BOTH branches. Out of 59-24 scope (would require touching per_player + changing behavior). Logged as a Delivery Finding for a follow-up that fixes both branches together.

**Subagent dispatch tags:** [SEC] confirmed→deferred (1 finding above). Disabled this run (project `workflow.reviewer_subagents` config), domains covered manually in observations/rule-compliance: [EDGE] (empty/all-redacted/mixed/non-str-target — guarded and pinned), [SILENT] (the silent non-str-target drop is the SEC finding's territory — pre-existing, mirrored), [TEST] (3 RED-proven tests; key= prevents idempotency-collision masking), [DOC] (added comment verified accurate vs dispatch.py:180-210), [TYPE] (isinstance guards; no new stringly-typed surface), [SIMPLE] (minimal faithful mirror — no over-engineering), [RULE] (enumerated below).

### Rule Compliance
- **Perception firewall ADR-104/105 (SOUL Illusionism / OTEL must reflect reality):** COMPLIANT for the story's scope — cross_player redacted `target`s are now scanned, closing the blind spot for the same key per_player handles. 2 instances checked (per_player pre-existing + cross_player new); the residual multi-key gap is a SEPARATE pre-existing issue affecting both, deferred (not dismissed) to a follow-up.
- **No Silent Fallbacks (CLAUDE.md):** the non-str/missing-target silent drop is pre-existing per_player behavior mirrored intentionally; surfaced as the [SEC] finding rather than introduced here. No NEW silent fallback added by this diff.
- **OTEL reuse, no cosmetic span (CLAUDE.md / context):** COMPLIANT — cross_player targets flow into `redacted_entities`, counted by the existing `narrator.canonical_leak_audit` span (`redact_tag_count`); no new span.
- **Scope discipline (context Scope Boundaries):** COMPLIANT — only the cross_player loop added; per_player, orchestrator call sites, fidelity/secrets_for/visible_to, and redact_dispatch_package all untouched.
- **Every test suite needs a wiring test:** SATISFIED — `audit_canonical_prose` is a telemetry-emit utility exercised end-to-end by its unit tests against the real function (synthetic package → real call → assertion on result + span-backing fields); it is not a new entry point.

### Devil's Advocate
Argue the code is broken. First attack: does the audit run on the package that actually contains the secrets? If it received the REDACTED view, the cross_player dispatches would already be stripped and the audit would pass trivially — useless. I traced both call sites (orchestrator.py:3073, 3410): they pass `context.dispatch_package`, the canonical pre-redaction package, exactly as the docstring demands. The fix lands on real data. Second attack: double-counting — if a dispatch were reachable via both per_player and cross_player, `redact_tag_count` would inflate and `redacted_entities` would hold dupes. The `_unique_idempotency_keys` validator forbids cross-field key reuse, so a valid package cannot present the same dispatch twice; dupes are impossible through the constructor. Third attack: the real teeth — the `target`-only extraction. An `npc_agency` dispatch tagged for redaction stores its secret under `npc_name`, not `target`; this audit (both branches) will count it in `redact_tag_count` but never add the name to `redacted_entities`, so a prose leak of that NPC's name returns a false `leaks_detected=0`. That is a genuine silent safety-net hole — but it is PRE-EXISTING in per_player, the story explicitly mandated mirroring per_player, and fixing it touches out-of-scope code and changes both branches' behavior. It is the correct subject of a follow-up, not a reason to reject a story that did exactly what it was scoped to do. Fourth attack: crash on a `dispatch` element that isn't a SubsystemDispatch — guarded by `isinstance(d, SubsystemDispatch): continue`. None of these are defects introduced by this diff.

**Error handling:** No new error paths; the loop is total (handles empty cross_player, non-dict params, non-str target, non-SubsystemDispatch entries). Covered by the new and existing tests.

**Handoff:** To SM for finish-story.