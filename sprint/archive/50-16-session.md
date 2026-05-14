---
story_id: "50-16"
epic: "50"
workflow: "tdd"
---
# Story 50-16: Journal UI confidence propagation

## Story Details

- **ID:** 50-16
- **Title:** Journal: UI confidence propagation — drop hardcoded 'Suspected' in useStateMirror, source from JOURNAL_RESPONSE (seam C UI part 2 per ADR-100)
- **Epic:** 50 (Pingpong-archive triage and dropped-work cleanup)
- **Workflow:** tdd
- **Type:** bug
- **Points:** 2
- **Priority:** p2
- **Stack Parent:** 50-14 (server JOURNAL_REQUEST handler, merged). Also stacked on UI parent 50-15 (PR #240, narrator-supplied Footnote.fact_id) — the test/source diffs assume 50-15's narrator-fact_id consumption is in place.
- **Repo:** sidequest-ui only
- **Branch:** feat/50-16-journal-ui-confidence (based on feat/50-15-journal-ui-fact-id)

## Story Context

Closes Seam C (UI part 2) of the journal pipeline per ADR-100. The seam has two parts: 50-14 (server JOURNAL_REQUEST handler) and 50-16 (UI drops the hardcoded confidence label and sources confidence from the canonical journal). Klinger's session-recorded decision: ephemeral footnotes default to 'Suspected' while awaiting canonical refresh; the JOURNAL_RESPONSE handler overrides with the server's truth.

### Acceptance Criteria

- [x] `useStateMirror.ts:194` no longer hardcodes `confidence: 'Suspected'`
- [x] Per-turn footnote entries (ephemeral, from `NarrationPayload.footnotes`) default to `'Suspected'` while awaiting canonical refresh
- [x] Canonical journal entries (from `JOURNAL_RESPONSE`) preserve the server's `KnownFact.confidence` value
- [x] Vitest integration test confirms the confidence duality (NARRATION footnote then JOURNAL_RESPONSE for same fact_id → canonical wins)
- [x] Wiring test verifies end-to-end: scenario clue mid-turn confidence upgrade

### ADR References

- **ADR-100** — Journal Pipeline Coherence
- **ADR-039** — Narrator Structured Output (Footnote schema)
- **ADR-36** — Multiplayer Turn Coordination

## Workflow Tracking

**Workflow:** tdd
**Phase:** finish
**Phase Started:** 2026-05-14T10:47:04Z

### Phase History

| Phase | Started | Ended | Duration |
|-------|---------|-------|----------|
| setup | 2026-05-14T03:00:00Z | 2026-05-14T10:06:29Z | 7h 6m |
| red | 2026-05-14T10:06:29Z | 2026-05-14T10:13:35Z | 7m 6s |
| green | 2026-05-14T10:13:35Z | 2026-05-14T10:18:43Z | 5m 8s |
| spec-check | 2026-05-14T10:18:43Z | 2026-05-14T10:20:22Z | 1m 39s |
| verify | 2026-05-14T10:20:22Z | 2026-05-14T10:24:13Z | 3m 51s |
| review | 2026-05-14T10:24:13Z | 2026-05-14T10:31:27Z | 7m 14s |
| green | 2026-05-14T10:31:27Z | 2026-05-14T10:39:02Z | 7m 35s |
| spec-check | 2026-05-14T10:39:02Z | 2026-05-14T10:39:58Z | 56s |
| verify | 2026-05-14T10:39:58Z | 2026-05-14T10:41:02Z | 1m 4s |
| review | 2026-05-14T10:41:02Z | 2026-05-14T10:46:10Z | 5m 8s |
| spec-reconcile | 2026-05-14T10:46:10Z | 2026-05-14T10:47:04Z | 54s |
| finish | 2026-05-14T10:47:04Z | - | - |

## Note: Session Reconstruction

The session file was overwritten by `testing-runner` during the Dev rework verification step (known bug — see OQ-1 memory `feedback_testing_runner_overwrites_session.md`). The content below is reconstructed from conversation context. Phase histories and timestamps are preserved; the prose of in-flight assessments may differ slightly from the originals.

## SM Assessment

Setup complete for story 50-16.

- **Scope:** Drop the hardcoded `'Suspected' as Confidence` cast at `sidequest-ui/src/hooks/useStateMirror.ts:194` and ensure `JOURNAL_RESPONSE` entries propagate the server's `KnownFact.confidence`. Seam C (UI part 2) per ADR-100.
- **Hard dependency:** 50-14 (server JOURNAL_REQUEST handler) merged. Stacked on 50-15 (UI fact_id consumption, PR #240).
- **Repo:** sidequest-ui only. Branch `feat/50-16-journal-ui-confidence`.

## Delivery Findings

### SM (setup)
- No upstream findings during setup.

### TEA (test design)
- **Gap** (non-blocking): The 50-16 branch was initially cut from `origin/develop` (commit `3ac1d49`), which pre-dates 50-15's still-open PR #240. Tests written against the 50-15-style narrator-supplied `Footnote.fact_id` produced misleading pass/fail signals until the branch was re-stacked onto `feat/50-15-journal-ui-fact-id`. Affects `pf agent sm-setup`: when a story declares a `Stack Parent`, the feature branch should be created from the parent's branch tip rather than from `develop`. *Found by TEA during test design.*

### Dev (green implementation)
- **Improvement** (non-blocking): The full UI test suite has 24 files / 28 tests failing on the stacked base — predominantly `@local/dice-lib` import-resolution drift (introduced by refactor(dice) #237, commit `1e4a425`), plus unrelated App/lobby/confrontation/wiring tests. None touch `useStateMirror` per grep. The dice-lib drift is a real CI hazard worth its own story. *Found by Dev during green implementation.*

### Architect (spec-check)
- **`'Discovered'` in AC4 example treated as illustrative, not literal.**
  - Spec source: this session file, AC4 sub-bullet (pre-reconstruction).
  - Spec text: "JOURNAL_RESPONSE arrives for same fact_id with confidence `'Discovered'` (e.g., scenario clue)".
  - Implementation: Tests use `'Certain'` and `'Rumored'` (valid Confidence union members). `'Discovered'` is a FactSource value, not a Confidence.
  - Rationale: "(e.g., scenario clue)" qualifier reads as illustrative; using a valid Confidence preserves the AC's intent without exercising the validator's coercion path on the test fixture. Story 50-17 (`KnownFact.confidence` enum promotion) is the right place to reconcile the canonical vocabulary.
  - Severity: trivial. Forward impact: 50-17 may need to revisit if `'Discovered'` becomes a Confidence value.

### TEA (test verification)
- **Improvement** (non-blocking): `src/types/payloads.ts:672` exports a `Confidence` union of lowercase values (`"certain" | "inferred" | "rumor"`) plus validators tuned to those values, while `src/providers/GameStateProvider.tsx:32` exports a capitalized `Confidence` union (`'Certain' | 'Suspected' | 'Rumored'`) which is what `useStateMirror.ts` consumes. There are two `Confidence` types and two sets of validators in the codebase. Reconciling is its own story — ideally rolled into 50-17. *Found by TEA during test verification (simplify-quality fan-out).*

### Dev (green rework, post-Reviewer reject)
- **Improvement** (blocking for the testing-runner subagent, non-blocking for 50-16): `testing-runner` overwrote `.session/50-16-session.md` with a test-cache report during the rework verification step. The session file was reconstructed from conversation context. This is the known `feedback_testing_runner_overwrites_session.md` bug from OQ-1 memory — should be fixed in the testing-runner subagent (suppress the session-file write when running a story-scoped suite). *Found by Dev during rework verification.*

## Design Deviations

### SM (setup)
- No deviations from spec.

### TEA (test design)
- No deviations from spec.

### Dev (green implementation)
- No deviations from spec.

### Architect (spec-check)
- **`'Discovered'` AC4 example vocabulary deviation** — see Delivery Findings above for the 6-field record.

### TEA (test verification)
- No deviations from spec.

### Dev (green rework)
- No deviations from spec.

### Architect (reconcile)

- No additional deviations found.

**Audit summary:** The story carried exactly one in-flight deviation through to completion — the `'Discovered'` vocabulary illustrative-vs-literal call logged by Architect at spec-check. Verified accurate:
  - Spec source path (`this session file, AC4 sub-bullet`) is correct — the AC4 example bullet did use `'Discovered'` as the canonical confidence in the original session text, before session reconstruction.
  - Spec text is quoted inline as the 6-field format requires, no "see above" pointer.
  - Implementation description matches: tests use `'Certain'` and `'Rumored'` (verified at `useStateMirror-50-16-confidence.test.tsx` lines 108, 138, 187, 234, 273); `'Discovered'` is a `FactSource` value per `useStateMirror.ts:10` `VALID_SOURCES = ['Observation', 'Dialogue', 'Discovery', 'Backstory']`, not a `Confidence` value (`VALID_CONFIDENCES = ['Certain', 'Suspected', 'Rumored']` at `:11`).
  - Forward impact is accurate: story 50-17 (`KnownFact.confidence` enum promotion) is the natural reconciliation point. The Dev's rework did not change this deviation — the strengthened reverse-order test now uses `'Rumored'` (still a valid `Confidence`), which preserves the deviation's intent.

**AC accountability:** All 5 ACs marked complete in this session file. No deferrals or descopes — the AC accountability table from `dev-exit` showed all DONE. Reviewer's APPROVE on the re-pass confirms ACs are fulfilled.

**Reviewer findings cross-check:** Reviewer's initial REJECT confirmed 11 findings, 1 dismissed (source-grep no-regression test fragility — rationale: AC1 is *about* the literal pattern), 3 deferred (pre-existing `msg as unknown as NarrationMessage` cast at line 234; pre-existing `skipLibCheck: true` in `tsconfig.app.json`; AC5 wiring test depth). None of the confirmed findings altered AC scope — they were comment hygiene and test-quality polish, all resolved in the rework. None of the deferred findings invalidate any AC; they remain genuinely out of scope for a 2-point UI confidence story.

**Sibling stories surveyed:** 50-14 (server JOURNAL_REQUEST handler, merged) provides the canonical reply path that 50-16's override branch consumes — contract held. 50-15 (UI fact_id consumption, PR #240 open) is 50-16's stack parent; 50-15's `Footnote.fact_id` plumbing is the prerequisite for canonical-vs-ephemeral fact_id matching in 50-16. 50-17 (`KnownFact.confidence` enum promotion, backlog) inherits the `'Discovered'` vocabulary deviation and the lowercase/capitalized `Confidence` divergence between `payloads.ts` and `GameStateProvider.tsx` flagged by TEA at verify.

## Architect Assessment (spec-check, post-rework)

**Spec Alignment:** Aligned. **Mismatches Found:** 0 new (the trivial `'Discovered'` vocabulary deviation from the initial spec-check still stands).

**Re-check scope:** Rework touched only comments in `useStateMirror.ts` (no runtime behavior change — `git diff cadf17a..HEAD -- useStateMirror.ts` shows only JSDoc / inline-comment edits, no expression or control-flow changes) plus test-file quality improvements (`toMatchObject` replacing non-null assertions, strengthened reverse-order assertions, new GARBAGE-confidence test for the validator safety net). The original AC1–AC5 alignment from the first spec-check carries over unchanged.

**New test (validator safety net):** The added "JOURNAL_RESPONSE with an unrecognized confidence falls back to 'Suspected'" test exercises `validateConfidence` on a malformed payload (`'GARBAGE'`). Aligns with the project's "No Silent Fallbacks" doctrine — the validator does fall back, but loudly (via `console.warn`), and the test now proves the fallback path is intact. Not a new AC; a strengthening of AC3's canonical-preserved contract under adversarial server input.

**Strengthened reverse-order test:** Now uses `'Rumored'` as the canonical confidence (distinct from the `'Suspected'` default), with distinct content text and `toMatchObject({ confidence: 'Rumored', source: 'Discovery', content: '...server canonical...' })`. AC4's "reverse order canonical wins" claim is now provably guarded — a regression where the footnote overwrites the canonical fails with a real value mismatch, not silently passes on the seen-set skip.

**Decision:** Proceed to verify → review. No hand-back required.

## TEA Assessment (verify, post-rework)

**Phase:** finish (re-pass after Dev rework)
**Status:** GREEN confirmed

**Simplify sweep:** Skipped this pass. The full reuse/quality/efficiency fan-out ran in the first verify pass and produced the one in-scope fix (footnote source through `validateSource`); the rework that followed addressed reviewer-requested polish (comment hygiene, `toMatchObject`, strengthened reverse-order, new GARBAGE-confidence test) — none of which the simplify teammates would have surfaced. Re-running the sweep would produce the same noted-and-deferred refactor recommendations (validator factory, shared test helpers, `upsertBy`).

**Quality Checks:**

| Suite | Result |
|-------|--------|
| `useStateMirror-50-16-confidence.test.tsx` | 10/10 pass |
| `useStateMirror-50-15-fact-id.test.tsx` (stacked parent) | 13/13 pass |
| `useStateMirror-protocol26-7.test.tsx` (older sibling) | 10/10 pass |
| `npx tsc --noEmit` | pass |
| `npx eslint useStateMirror.ts + test` | pass |

**Session-file protection:** Testing-runner was explicitly instructed not to write to `.session/50-16-session.md` this pass (avoiding the known `feedback_testing_runner_overwrites_session.md` bug). Session intact post-run; 273 lines.

**Handoff:** To Reviewer (The Queen of Hearts) for re-review.

## Subagent Results (review phase, re-pass)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | clean | none | N/A (all 4 prior findings resolved, no new ones) |
| 5 | reviewer-comment-analyzer | Yes | clean | none | N/A (all 7 prior findings resolved, no new ones) |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 2 (both pre-existing, deferred) | confirmed 0 new, deferred 2 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 0 new confirmed, 0 new dismissed, 2 pre-existing deferred (carried over from first review pass)

## Reviewer Assessment (re-review, APPROVE)

**Verdict:** APPROVE.

All 9 rework items from the initial review verified resolved by independent subagent re-runs:

- **[DOC][RULE] Source comments:** zero `story 50-15` or `story 50-16` references remain in `useStateMirror.ts`. "Klinger's call" replaced with content describing the actual design decision. "the JOURNAL_RESPONSE override above" replaced with "the JOURNAL_RESPONSE handler". (Comment-analyzer + rule-checker both confirm clean — addresses the previous-pass `[DOC]` and `[RULE]` violations of the "no task/fix/caller references in comments" rule.)
- **[DOC] Test file header:** 32-line RED-state docstring replaced with one orienting sentence about the invariant under test.
- **[DOC] Describe-block labels:** all 5 blocks dropped the `useStateMirror 50-16 — ` prefix; Vitest output now shows AC tags only.
- **[DOC] No-regression inline comment:** story + line-number reference replaced with the invariant statement.
- **[RULE][TYPE] Non-null assertions:** all 6 `entry!.X` / `clue!.X` patterns replaced with `expect(entry).toMatchObject({ ... })`. Rule-checker confirms zero `!` assertions on nullable values remain — closes the prior `[RULE]` TS lang-review #8 violation.
- **[TEST] Reverse-order test:** strengthened with `confidence: 'Rumored'` (distinct from the 'Suspected' default), distinct canonical content text, and `toMatchObject({ confidence, source, content })`. A regression where the footnote overwrites the canonical now fails with a real value mismatch. Test-analyzer confirms genuine falsifiability — closes the prior `[TEST]` finding that the reverse-order test was exercising pre-50-16 code paths.
- **[TEST] GARBAGE-confidence test:** added at test file line 393, exercises the `validateConfidence` safety net on a malformed server payload. Falsifiable — closes the prior `[TEST]` finding about the missing invalid-confidence coverage.
- **[DOC] Bounded boy-scout:** pre-existing `story 50-15` references at lines 37 and 195 also stripped.

**No new findings introduced by the rework.** Test-analyzer and comment-analyzer both came back fully clean. Rule-checker found only the two pre-existing items (`msg as unknown as NarrationMessage` double-cast at line 234, `skipLibCheck: true` in tsconfig) that were flagged and deferred in the first pass; both remain out of scope for 50-16.

**Preflight:** 33/33 useStateMirror tests pass (50-16 confidence: 10/10, 50-15 fact_id parent: 13/13, protocol-26-7 sibling: 10/10), `npx tsc --noEmit` clean, `npx eslint` clean.

**Devil's Advocate (re-pass):** The rework was scoped exactly to the directive list — no opportunistic refactors, no new abstractions, no scope creep. The substantive behavior of the JOURNAL_RESPONSE override path is unchanged from the originally-approved spec-check (`git diff cadf17a..HEAD -- useStateMirror.ts` shows only comment edits). The single in-flight deviation (illustrative `'Discovered'` vocabulary in AC4) was already accepted in the first spec-check and carries forward unchanged.

**Handoff:** To Architect (The White Queen) for spec-reconcile.

## TEA Assessment (red)

**Tests Required:** Yes (TDD workflow).

**Test File:** `sidequest-ui/src/hooks/__tests__/useStateMirror-50-16-confidence.test.tsx` — 9 tests covering AC2 (default), AC3 (canonical preserved), AC4 (canonical-wins duality), no-regression (literal-cast file-level guard), AC5 (App.tsx import wiring + end-to-end scenario flow).

**Status at exit:** RED — 5/9 pass (regression guards + AC3 + reverse-order + wiring import), 4/9 fail (canonical-wins behavior gaps + literal hardcoded cast still in source).

**Spec Authority Note:** Branch re-stacked onto `feat/50-15-journal-ui-fact-id` at TEA time because the original `sm-setup` branch base (`develop`) pre-dated 50-15's still-open PR #240. See Delivery Findings.

**Handoff:** To Dev (The White Rabbit) for green implementation.

## Dev Assessment (green)

**Status:** GREEN — 9/9 of the new 50-16 tests pass; full UI suite shows zero regressions in any file that touches `useStateMirror`.

**Files Changed:**
- `sidequest-ui/src/hooks/useStateMirror.ts` — +24/-6 lines. JOURNAL_RESPONSE handler now builds a `canonical: KnowledgeEntry` up front, then either pushes (new fact_id) or overwrites `knowledge[findIndex(...)]` (already-seen). Footnote loop `'Suspected' as Confidence` literal cast replaced with `validateConfidence(undefined)`.

**Why the override-on-seen shape:** AC4 demands the entry is updated to canonical confidence when a footnote landed first. The pre-50-16 seen-set skip was the mechanism that silently dropped the canonical update — replacing with index-find + array-slot replace gives canonical authority without duplicating entries.

**Wiring (Verify Wiring, Not Just Existence):** AC5 test `App.tsx imports useStateMirror` passes; end-to-end scenario clue test passes — the production replay path produces canonical confidence in `state.knowledge[]`.

**Regression Check:** 113/137 test files pass, 1236/1264 tests pass. 24 failing files verified pre-existing on the stacked base; none import `useStateMirror`.

**Handoff:** To Reviewer.

## Architect Assessment (spec-check)

**Spec Alignment:** Aligned. **Mismatches Found:** 1 trivial (illustrative AC4 example using non-Confidence vocabulary — logged under Design Deviations).

AC1–AC5 trace: all aligned. The override path replaces the entire `KnowledgeEntry` (content, category, source, confidence, learned_turn, is_new), not just confidence — matches the Implementation Design's "real values" plural framing.

**Reuse-first audit:** `validateConfidence`/`validateSource`/`validateCategory` already existed; implementation reused them rather than inlining. No new abstractions introduced.

**Decision:** Proceed to review (TEA verify → Reviewer).

## TEA Assessment (verify)

**Status:** GREEN confirmed.

### Simplify Report

| Teammate | Status | Findings |
|----------|--------|----------|
| simplify-reuse | 4 findings | validator-factory extraction (high), shared test helpers extraction (high), `journalResponse` move to shared helpers (high), `upsertBy` helper (medium) |
| simplify-quality | 5 findings | import payloads validators (high — false positive), VALID_CONFIDENCES drift (medium), `source: 'Observation' as FactSource` literal (high), comment asymmetry (low), regex spacing (low) |
| simplify-efficiency | clean | none |

**Applied:** 1 high-confidence fix — `source: 'Observation' as FactSource` → `validateSource('Observation')`. Same-shape cleanup as the 50-16 confidence fix; routes the footnote source through the central validator. Zero runtime delta (`'Observation'` is in `VALID_SOURCES`).

**Rejected:** simplify-quality #1 (import validators from `payloads.ts`). Verified `payloads.ts` exports a *lowercase* `Confidence` union (`certain/inferred/rumor`) while `GameStateProvider.tsx` exports the *capitalized* one (`Certain/Suspected/Rumored`) — useStateMirror uses the capitalized type. Importing payloads validators would produce type-mismatch failures.

**Deferred (out of scope):** Validator factory extraction, shared test helpers, `upsertBy` helper — all real opportunities but cross story boundaries and add abstractions beyond what 50-16 requires.

### Regression Check

| Suite | Result |
|-------|--------|
| `useStateMirror-50-16-confidence.test.tsx` | 9/9 pass |
| `useStateMirror-50-15-fact-id.test.tsx` (stacked parent) | 13/13 pass |
| `useStateMirror-protocol26-7.test.tsx` (older sibling) | 10/10 pass |
| `npx tsc --noEmit` | pass |
| `npx eslint src/hooks/useStateMirror.ts` | pass |

**Handoff:** To Reviewer.

## Subagent Results (review phase)

| # | Specialist | Received | Status | Findings | Decision |
|---|-----------|----------|--------|----------|----------|
| 1 | reviewer-preflight | Yes | clean | none | N/A |
| 2 | reviewer-edge-hunter | Skipped | disabled | N/A | Disabled via settings |
| 3 | reviewer-silent-failure-hunter | Skipped | disabled | N/A | Disabled via settings |
| 4 | reviewer-test-analyzer | Yes | findings | 4 | confirmed 3, dismissed 1, deferred 0 |
| 5 | reviewer-comment-analyzer | Yes | findings | 7 | confirmed 6, dismissed 0, deferred 1 |
| 6 | reviewer-type-design | Skipped | disabled | N/A | Disabled via settings |
| 7 | reviewer-security | Skipped | disabled | N/A | Disabled via settings |
| 8 | reviewer-simplifier | Skipped | disabled | N/A | Disabled via settings |
| 9 | reviewer-rule-checker | Yes | findings | 4 | confirmed 2, dismissed 0, deferred 2 |

**All received:** Yes (4 enabled returned, 5 disabled pre-filled)
**Total findings:** 11 confirmed, 1 dismissed (with rationale), 3 deferred

## Reviewer Assessment

**Verdict (initial review):** REJECT — hand back to Dev for bounded cleanup.

Behavior was correct (canonical-wins property held, parent and sibling suites stayed green, preflight clean: 32/32 useStateMirror tests passing), but two project rules were violated:

- **CLAUDE.md / system "no task/fix/caller references in comments"** — `(story 50-16)` parentheticals in `useStateMirror.ts` at lines 128 and 209; "Klinger's call" opaque attribution at line 209; "the JOURNAL_RESPONSE override above" directional pointer at line 209; 32-line test-file header docstring described RED state and embedded story 50-16 references; describe-block labels embedded "50-16 —" prefix; no-regression inline comment referenced story + line number; pre-existing `story 50-15` references at lines 37 and 195 flagged as bounded boy-scout cleanup.
- **TS lang-review #8 test quality** — 6 `entry!` / `clue!` non-null assertions used after `expect(entry).toBeDefined()`. `toBeDefined` does not narrow the TS type; `!` access throws `TypeError` on failure instead of a clean assertion mismatch.

Plus two LOW-severity test-coverage findings:
- **Reverse-order AC4 test passes for the wrong reason** — exercises the pre-50-16 footnote-loop seen-set skip, not the new override branch. Fix: use distinct canonical confidence (`'Rumored'`) so a regression would fail with a real mismatch.
- **No coverage for JOURNAL_RESPONSE with invalid confidence** — the validator safety net (`validateConfidence` fallback to `'Suspected'`) is untested on the JOURNAL_RESPONSE path.

**Dismissed:** Source-grep no-regression test fragility (AC1 is *about* the literal pattern; the grep is the named guard).

**Deferred (out of scope for 50-16):** Pre-existing `msg as unknown as NarrationMessage` cast at line 235; pre-existing `skipLibCheck: true` in tsconfig; AC5 wiring test depth (file-grep is belt-and-suspenders alongside the renderHook end-to-end test).

**Handoff:** Back to Dev for rework.

## Dev Assessment (green rework, post-Reviewer reject)

**Status:** All 9 reviewer rework items addressed. 33/33 useStateMirror tests green; typecheck and lint clean.

**Items completed:**

1. **`useStateMirror.ts:128`** — stripped `(story 50-16)` parenthetical. ADR-100 Seam C reference and canonical-wins prose retained.
2. **`useStateMirror.ts:~209`** — stripped `(story 50-16)`; replaced "matches Klinger's call" with content ("Ephemeral entries default to 'Suspected' so the journal is populated immediately; the JOURNAL_RESPONSE handler overwrites with the server's authoritative KnownFact.confidence once it arrives."); replaced "the JOURNAL_RESPONSE override above" → "the JOURNAL_RESPONSE handler".
3. **Test file header (lines 1–38)** — replaced 32-line docstring with one orienting sentence describing the invariant under test.
4. **Describe-block labels** — dropped `useStateMirror 50-16 — ` prefix from all 5 describe blocks. Vitest output now shows `'AC2: ephemeral default is Suspected'`, `'AC3: canonical confidence propagates'`, etc.
5. **No-regression test inline comment** — replaced story + line reference with an invariant statement (single-source-of-truth for the default; literal cast bypasses the validator contract).
6. **Non-null assertions** — replaced all 6 `entry!.X` / `clue!.X` patterns (AC3 ×2, AC4 ×2, AC5 ×1, end-to-end ×1) with `expect(entry).toMatchObject({ ... })`. Failure now produces a clean Vitest object-mismatch report instead of `TypeError: Cannot read property of undefined`.
7. **Reverse-order test strengthened** — canonical confidence changed from `'Certain'` to `'Rumored'`; canonical content text made distinct from footnote text ("(server canonical)" vs "(narrator footnote)"); assertion expanded to `toMatchObject({ confidence: 'Rumored', source: 'Discovery', content: '...server canonical...' })`. A regression where the footnote overwrites the canonical would now fail with a real `'Rumored' !== 'Suspected'` mismatch.
8. **New test added** — `JOURNAL_RESPONSE with an unrecognized confidence falls back to 'Suspected'` sends `confidence: 'GARBAGE'` in a JOURNAL_RESPONSE entry and asserts the resulting `KnowledgeEntry` carries `'Suspected'` via the `validateConfidence` fallback. Guards the validator safety net per the Reviewer's missing-edge-case finding.
9. **Bounded boy-scout (optional, applied)** — also stripped `story 50-15` from pre-existing JSDoc at `useStateMirror.ts:37` and inline comment at `:195`. One-line edits adjacent to 50-16's own edits; parent branch (PR #240) still open.

**Regression Check (rework):**

| Suite | Result |
|-------|--------|
| `useStateMirror-50-16-confidence.test.tsx` | 10/10 pass (was 9, added GARBAGE-confidence test) |
| `useStateMirror-50-15-fact-id.test.tsx` (parent) | 13/13 pass |
| `useStateMirror-protocol26-7.test.tsx` (sibling) | 10/10 pass |
| `npx tsc --noEmit` | pass |
| `npx eslint src/hooks/useStateMirror.ts` and the test file | pass |

**Total:** 33/33 useStateMirror tests green post-rework.

**Handoff:** Back to Reviewer (The Queen of Hearts) for re-review.

## Implementation Notes

### useStateMirror.ts (final state)

- JOURNAL_RESPONSE handler builds a `canonical: KnowledgeEntry` up front and either pushes (new fact_id) or overwrites `knowledge[findIndex]` (already-seen). Override-on-seen replaces the entire `KnowledgeEntry`, not just confidence — content/source/category/learned_turn all come from the canonical row.
- Footnote loop defaults confidence to `validateConfidence(undefined)` (returns `'Suspected'` via the central validator). Footnote source defaults to `validateSource('Observation')`. No literal casts; the no-regression grep test guards the file-level invariant.
- All four comments (JSDoc at line 37, JOURNAL_RESPONSE block, footnote loop part-1 and part-2) cite ADR-100 Seam C; no story-number references remain.

### Test file (final state)

- 10 tests total: AC2 (default), AC3 ×2 (canonical Certain, Rumored), AC4 ×3 (in-order canonical wins, source-field override, reverse-order with strengthened assertions using `'Rumored'`), no-regression (literal-cast grep), AC5 ×2 (App.tsx import wiring, end-to-end scenario clue), invalid-confidence GARBAGE → Suspected fallback.
- All assertions use `toMatchObject` or direct `.toBe` — no non-null assertions.
- Describe-block labels carry only the AC tag, no story prefix.
- File header is one orienting sentence.